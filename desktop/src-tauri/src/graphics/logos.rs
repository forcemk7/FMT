//! Logo serving model (keep the shell light):
//! 1. Serve from local logo-cache only on the hot path (O(1) disk).
//! 2. Never walk/parse FM logo packs from UI invokes or Load Active Save.
//! 3. Optional: `warm_logos_for_clubs` queues IDs and may start a one-shot background
//!    index — call that only from an explicit Settings action, never on load.

use std::{
    collections::{HashMap, HashSet, VecDeque},
    fs,
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicBool, Ordering},
        Mutex, OnceLock,
    },
    thread,
};

use super::{
    config_xml::{attribute_value, safe_relative_asset_path, MAX_GRAPHICS_CONFIG_BYTES},
    faces::{active_graphics_roots, app_data_dir, image_mime, FaceWarmResult, MAX_IMAGE_BYTES},
    packs::{copy_into_asset_cache, resolve_cached_asset},
};

const LOGO_CACHE_DIR: &str = "logo-cache-trim";
const MAX_INDEX_DEPTH: usize = 12;

#[derive(Default)]
struct LogoServeState {
    /// club_id → source path inside a graphics pack
    index: Option<HashMap<String, PathBuf>>,
    building: bool,
    /// Needs waiting until index is ready
    pending: VecDeque<String>,
    /// IDs already known missing after index build
    missing: HashSet<String>,
}

static STATE: OnceLock<Mutex<LogoServeState>> = OnceLock::new();
static INDEX_STARTED: AtomicBool = AtomicBool::new(false);

fn state() -> &'static Mutex<LogoServeState> {
    STATE.get_or_init(|| Mutex::new(LogoServeState::default()))
}

pub fn logo_cache_dir() -> PathBuf {
    app_data_dir().join(LOGO_CACHE_DIR)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum LogoLookup {
    Found,
    Pending,
    Missing,
}

/// Queue club IDs and start a one-shot background index. Do not call from Load Active Save.
pub fn warm_logos_for_clubs(club_ids: &[String]) -> FaceWarmResult {
    let cache = logo_cache_dir();
    let _ = fs::create_dir_all(&cache);
    let ids: Vec<String> = club_ids
        .iter()
        .map(|id| id.trim().to_string())
        .filter(|id| !id.is_empty() && id.bytes().all(|b| b.is_ascii_digit()))
        .collect();
    let requested = ids.len();
    let cache_dir = cache.display().to_string();
    queue_needs(&ids);
    ensure_index_building();
    FaceWarmResult {
        requested,
        cached: 0,
        copied: 0,
        missing: 0,
        cache_dir,
    }
}

pub(crate) fn resolve_logo_path(club_id: &str) -> Option<PathBuf> {
    match resolve_logo_lookup(club_id) {
        (LogoLookup::Found, Some(path)) => Some(path),
        _ => None,
    }
}

/// UniqueID → logo-cache / pack index. `Pending` while the one-shot index still builds
/// or a post-index fill is queued — UI must not permanent-cache a miss.
pub(crate) fn resolve_logo_lookup(club_id: &str) -> (LogoLookup, Option<PathBuf>) {
    let id = club_id.trim();
    if id.is_empty() || !id.bytes().all(|b| b.is_ascii_digit()) {
        return (LogoLookup::Missing, None);
    }
    // Hot path: local cache only. Never start pack walks from club_logo_data.
    if let Some(cached) = resolve_cached_asset(&logo_cache_dir(), id) {
        return (LogoLookup::Found, Some(cached));
    }
    let Ok(mut guard) = state().lock() else {
        return (LogoLookup::Pending, None);
    };
    if guard.missing.contains(id) {
        return (LogoLookup::Missing, None);
    }
    if let Some(index) = guard.index.as_ref() {
        let source = index.get(id).cloned();
        drop(guard);
        let Some(source) = source else {
            if let Ok(mut missing_guard) = state().lock() {
                missing_guard.missing.insert(id.to_string());
            }
            return (LogoLookup::Missing, None);
        };
        let path =
            copy_into_asset_cache(&logo_cache_dir(), id, &source, MAX_IMAGE_BYTES).or(Some(source));
        return (LogoLookup::Found, path);
    }
    if !guard.pending.iter().any(|pending| pending == id) {
        guard.pending.push_back(id.to_string());
    }
    drop(guard);
    // Background only — never walk packs on the invoke thread.
    ensure_index_building();
    (LogoLookup::Pending, None)
}

fn queue_needs(ids: &[String]) {
    if let Ok(mut state) = state().lock() {
        for id in ids {
            if state.missing.contains(id) {
                continue;
            }
            if resolve_cached_asset(&logo_cache_dir(), id).is_some() {
                continue;
            }
            if !state.pending.iter().any(|pending| pending == id) {
                state.pending.push_back(id.clone());
            }
        }
    }
}

fn ensure_index_building() {
    if INDEX_STARTED.swap(true, Ordering::SeqCst) {
        // Index thread already ran (or is running). Drain any IDs queued after first build.
        drain_pending_if_index_ready();
        return;
    }
    if let Ok(mut guard) = state().lock() {
        guard.building = true;
    }
    thread::spawn(|| {
        let index = build_logo_index();
        let pending = {
            let mut guard = state().lock().unwrap_or_else(|e| e.into_inner());
            guard.index = Some(index);
            guard.building = false;
            std::mem::take(&mut guard.pending)
        };
        let cache = logo_cache_dir();
        let _ = fs::create_dir_all(&cache);
        for id in pending {
            fill_cache_for_id(&cache, &id);
        }
        // Warm may enqueue more IDs while we filled the first batch.
        drain_pending_if_index_ready();
    });
}

fn drain_pending_if_index_ready() {
    let pending = {
        let Ok(mut guard) = state().lock() else {
            return;
        };
        if guard.index.is_none() || guard.building {
            return;
        }
        if guard.pending.is_empty() {
            return;
        }
        std::mem::take(&mut guard.pending)
    };
    thread::spawn(move || {
        let cache = logo_cache_dir();
        let _ = fs::create_dir_all(&cache);
        for id in pending {
            fill_cache_for_id(&cache, &id);
        }
    });
}

fn fill_cache_for_id(cache: &Path, id: &str) {
    if resolve_cached_asset(cache, id).is_some() {
        return;
    }
    let source = {
        let guard = state().lock().unwrap_or_else(|e| e.into_inner());
        guard.index.as_ref().and_then(|index| index.get(id).cloned())
    };
    match source {
        Some(path) => {
            let _ = copy_into_asset_cache(cache, id, &path, MAX_IMAGE_BYTES);
        }
        None => {
            if let Ok(mut guard) = state().lock() {
                guard.missing.insert(id.to_string());
            }
        }
    }
}

fn logo_pack_roots() -> Vec<PathBuf> {
    let mut packs = Vec::new();
    for root in active_graphics_roots() {
        if !root.is_dir() {
            continue;
        }
        if let Ok(entries) = fs::read_dir(&root) {
            for entry in entries.flatten() {
                if !entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                    continue;
                }
                let path = entry.path();
                let name = path
                    .file_name()
                    .map(|n| n.to_string_lossy().to_ascii_lowercase())
                    .unwrap_or_default();
                if name.contains("kit") || name.contains("wallpaper") || name.contains("background")
                {
                    continue;
                }
                let logoish = name.contains("logo")
                    || name.contains("badge")
                    || name.contains("crest")
                    || path.join("Men").is_dir()
                    || path.join("logos").is_dir()
                    || path.join("clubs").is_dir();
                if logoish {
                    packs.push(path);
                }
            }
        }
        for directory in [root.join("logos"), root.join("clubs"), root.join("badges")] {
            if directory.is_dir() {
                packs.push(directory);
            }
        }
    }
    packs
}

fn build_logo_index() -> HashMap<String, PathBuf> {
    let mut by_club_id = HashMap::new();
    for pack in logo_pack_roots() {
        index_logo_tree(&pack, 0, &mut by_club_id);
    }
    by_club_id
}

fn index_logo_tree(directory: &Path, depth: usize, by_club_id: &mut HashMap<String, PathBuf>) {
    if depth > MAX_INDEX_DEPTH || !directory.is_dir() {
        return;
    }
    let config = directory.join("config.xml");
    if config.is_file() {
        index_logo_config(&config, directory, by_club_id);
    }
    let Ok(entries) = fs::read_dir(directory) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let name = path
            .file_name()
            .map(|n| n.to_string_lossy().to_ascii_lowercase())
            .unwrap_or_default();
        if name.contains("kit") || name.contains("instruction") || name.contains("comp") {
            continue;
        }
        index_logo_tree(&path, depth + 1, by_club_id);
    }
}

fn index_logo_config(config: &Path, directory: &Path, by_club_id: &mut HashMap<String, PathBuf>) {
    let Ok(metadata) = config.metadata() else {
        return;
    };
    if metadata.len() == 0 || metadata.len() > MAX_GRAPHICS_CONFIG_BYTES {
        return;
    }
    let Ok(file) = fs::File::open(config) else {
        return;
    };
    for line in BufReader::new(file).lines().map_while(Result::ok) {
        if !line.contains("from=\"") || !line.contains("to=\"") {
            continue;
        }
        if !line.contains("/logo") && !line.contains("/icon") {
            continue;
        }
        let Some(to) = attribute_value(&line, "to") else {
            continue;
        };
        let Some(club_id) = club_id_from_logo_to(to) else {
            continue;
        };
        if by_club_id.contains_key(&club_id) {
            continue;
        }
        let Some(from) = attribute_value(&line, "from") else {
            continue;
        };
        let Some(relative) = safe_relative_asset_path(from) else {
            continue;
        };
        if let Some(path) = resolve_image_beside(directory, &relative) {
            by_club_id.insert(club_id, path);
        }
    }
}

fn club_id_from_logo_to(to: &str) -> Option<String> {
    for marker in [
        "graphics/pictures/club/",
        "graphics/pictures/team/",
        "pictures/club/",
        "pictures/team/",
        "club/",
        "team/",
    ] {
        let Some(rest) = to.strip_prefix(marker) else {
            continue;
        };
        let id = rest.split('/').next()?.trim().trim_start_matches("r-");
        if !id.is_empty() && id.bytes().all(|b| b.is_ascii_digit()) {
            return Some(id.to_string());
        }
    }
    None
}

fn resolve_image_beside(directory: &Path, relative: &Path) -> Option<PathBuf> {
    let direct = directory.join(relative);
    if valid_image_file(&direct) {
        return Some(direct);
    }
    if relative.extension().is_some() {
        return None;
    }
    for extension in ["png", "jpg", "jpeg", "webp"] {
        let path = directory.join(relative.with_extension(extension));
        if valid_image_file(&path) {
            return Some(path);
        }
    }
    None
}

fn valid_image_file(path: &Path) -> bool {
    image_mime(path).is_some()
        && path.metadata().is_ok_and(|metadata| {
            metadata.is_file() && metadata.len() > 0 && metadata.len() <= MAX_IMAGE_BYTES
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_logo_dir() -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time")
            .as_nanos();
        std::env::temp_dir().join(format!("fmt-logo-serve-test-{stamp}"))
    }

    #[test]
    fn indexes_tcm_style_club_logo_mapping() {
        let root = temp_logo_dir();
        let clubs = root.join("Men").join("Europe").join("Germany").join("Clubs");
        fs::create_dir_all(&clubs).expect("dirs");
        fs::write(clubs.join("TCM1_920.png"), b"not-empty").expect("image");
        fs::write(
            clubs.join("config.xml"),
            r#"<record from="TCM1_920" to="graphics/pictures/club/920/logo"/>"#,
        )
        .expect("config");

        let mut map = HashMap::new();
        index_logo_tree(&root, 0, &mut map);
        assert_eq!(map.get("920"), Some(&clubs.join("TCM1_920.png")));

        let _ = fs::remove_dir_all(root);
    }
}
