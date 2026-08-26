//! Nation flag / federation badge serving (keep the shell light):
//! 1. Serve from local flag-cache only on the hot path (O(1) disk).
//! 2. Never walk/parse FM packs from UI invokes or Load Active Save.
//! 3. UID → one-shot background XML index → copy into cache (same model as club logos).

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

const FLAG_CACHE_DIR: &str = "flag-cache";
const MAX_INDEX_DEPTH: usize = 12;

#[derive(Default)]
struct FlagServeState {
    /// nation_id → source path inside a graphics pack
    index: Option<HashMap<String, PathBuf>>,
    building: bool,
    pending: VecDeque<String>,
    missing: HashSet<String>,
}

static STATE: OnceLock<Mutex<FlagServeState>> = OnceLock::new();
static INDEX_STARTED: AtomicBool = AtomicBool::new(false);

fn state() -> &'static Mutex<FlagServeState> {
    STATE.get_or_init(|| Mutex::new(FlagServeState::default()))
}

pub fn flag_cache_dir() -> PathBuf {
    app_data_dir().join(FLAG_CACHE_DIR)
}

/// Queue nation IDs and start a one-shot background index. Do not call from Load Active Save sync path.
pub fn warm_flags_for_nations(nation_ids: &[String]) -> FaceWarmResult {
    let cache = flag_cache_dir();
    let _ = fs::create_dir_all(&cache);
    let ids: Vec<String> = nation_ids
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

pub fn resolve_flag_path(nation_id: &str) -> Option<PathBuf> {
    let id = nation_id.trim();
    if id.is_empty() || !id.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    if let Some(cached) = resolve_cached_asset(&flag_cache_dir(), id) {
        return Some(cached);
    }
    let mut state = state().lock().ok()?;
    if state.missing.contains(id) {
        return None;
    }
    if let Some(index) = state.index.as_ref() {
        let source = index.get(id).cloned();
        drop(state);
        let Some(source) = source else {
            return None;
        };
        return copy_into_asset_cache(&flag_cache_dir(), id, &source, MAX_IMAGE_BYTES).or(Some(source));
    }
    if !state.pending.iter().any(|pending| pending == id) {
        state.pending.push_back(id.to_string());
    }
    drop(state);
    // Background only — never walk packs on the invoke thread.
    ensure_index_building();
    None
}

fn queue_needs(ids: &[String]) {
    if let Ok(mut state) = state().lock() {
        for id in ids {
            if state.missing.contains(id) {
                continue;
            }
            if resolve_cached_asset(&flag_cache_dir(), id).is_some() {
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
        return;
    }
    if let Ok(mut guard) = state().lock() {
        guard.building = true;
    }
    thread::spawn(|| {
        let index = build_flag_index();
        let pending = {
            let mut guard = state().lock().unwrap_or_else(|e| e.into_inner());
            guard.index = Some(index);
            guard.building = false;
            std::mem::take(&mut guard.pending)
        };
        let cache = flag_cache_dir();
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

fn flag_pack_roots() -> Vec<PathBuf> {
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
                let flagish = name.contains("logo")
                    || name.contains("flag")
                    || name.contains("nation")
                    || name.contains("badge")
                    || path.join("Men").is_dir()
                    || path.join("flags").is_dir()
                    || path.join("nations").is_dir();
                if flagish {
                    packs.push(path);
                }
            }
        }
        for directory in [
            root.join("flags"),
            root.join("nations"),
            root.join("pictures").join("flags"),
            root.join("pictures").join("nation"),
        ] {
            if directory.is_dir() {
                packs.push(directory);
            }
        }
    }
    packs
}

fn build_flag_index() -> HashMap<String, PathBuf> {
    let mut by_nation_id = HashMap::new();
    for pack in flag_pack_roots() {
        index_flag_tree(&pack, 0, &mut by_nation_id);
    }
    by_nation_id
}

fn index_flag_tree(directory: &Path, depth: usize, by_nation_id: &mut HashMap<String, PathBuf>) {
    if depth > MAX_INDEX_DEPTH || !directory.is_dir() {
        return;
    }
    let config = directory.join("config.xml");
    if config.is_file() {
        index_flag_config(&config, directory, by_nation_id);
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
        // Club trees are huge; nation badges live under Federations / Nations / flags.
        if name.contains("kit")
            || name.contains("instruction")
            || name == "clubs"
            || name == "competitions"
        {
            continue;
        }
        index_flag_tree(&path, depth + 1, by_nation_id);
    }
}

fn index_flag_config(config: &Path, directory: &Path, by_nation_id: &mut HashMap<String, PathBuf>) {
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
        let Some(to) = attribute_value(&line, "to") else {
            continue;
        };
        let Some(nation_id) = nation_id_from_flag_to(to) else {
            continue;
        };
        if by_nation_id.contains_key(&nation_id) {
            continue;
        }
        let Some(from) = attribute_value(&line, "from") else {
            continue;
        };
        let Some(relative) = safe_relative_asset_path(from) else {
            continue;
        };
        if let Some(path) = resolve_image_beside(directory, &relative) {
            by_nation_id.insert(nation_id, path);
        }
    }
}

/// TCM federations use `nation/{id}/logo`; classic packs use `flags/{id}/flag`.
fn nation_id_from_flag_to(to: &str) -> Option<String> {
    for marker in [
        "graphics/pictures/flags/",
        "graphics/pictures/nation/",
        "pictures/flags/",
        "pictures/nation/",
        "flags/",
        "nation/",
    ] {
        let Some(rest) = to.strip_prefix(marker) else {
            continue;
        };
        let mut parts = rest.split('/');
        let id = parts.next()?.trim().trim_start_matches("r-");
        let kind = parts.next().unwrap_or("");
        if !id.is_empty()
            && id.bytes().all(|b| b.is_ascii_digit())
            && (kind.is_empty() || kind == "flag" || kind == "logo" || kind == "icon")
        {
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

    fn temp_flag_dir() -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time")
            .as_nanos();
        std::env::temp_dir().join(format!("fmt-flag-serve-test-{stamp}"))
    }

    #[test]
    fn indexes_tcm_style_nation_logo_mapping() {
        let root = temp_flag_dir();
        let feds = root.join("Men").join("Others").join("Federations");
        fs::create_dir_all(&feds).expect("dirs");
        fs::write(feds.join("TCM3_794.png"), b"not-empty").expect("image");
        fs::write(
            feds.join("config.xml"),
            r#"<record from="TCM3_794" to="graphics/pictures/nation/794/logo"/>"#,
        )
        .expect("config");

        let mut map = HashMap::new();
        index_flag_tree(&root, 0, &mut map);
        assert_eq!(map.get("794"), Some(&feds.join("TCM3_794.png")));

        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn nation_id_accepts_logo_and_flag_suffix() {
        assert_eq!(
            nation_id_from_flag_to("graphics/pictures/nation/10/logo"),
            Some("10".into())
        );
        assert_eq!(
            nation_id_from_flag_to("graphics/pictures/flags/10/flag"),
            Some("10".into())
        );
        assert_eq!(nation_id_from_flag_to("graphics/pictures/club/10/logo"), None);
    }
}
