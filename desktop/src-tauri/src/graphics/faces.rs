use std::{
    collections::{HashMap, HashSet},
    env, fs,
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
    sync::OnceLock,
    thread,
    time::SystemTime,
};

use super::config_xml::{attribute_value, safe_relative_asset_path};

pub(crate) const MAX_IMAGE_BYTES: u64 = 8 * 1024 * 1024;

const CACHE_DIRNAME: &str = "face-cache";
/// Megapack face folders: skip XML parse, resolve `face_{uid}.png` on demand.
const HUGE_FACE_CONFIG_BYTES: u64 = 2 * 1024 * 1024;

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FaceWarmResult {
    pub requested: usize,
    pub cached: usize,
    pub copied: usize,
    pub missing: usize,
    pub cache_dir: String,
}

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FacesStatus {
    pub graphics_path: String,
    pub graphics_exists: bool,
    pub face_packs_found: usize,
    pub face_pack_names: Vec<String>,
    pub cached_files: usize,
    pub cache_dir: String,
}

pub(crate) fn app_data_dir() -> PathBuf {
    env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|| env::temp_dir())
        .join("com.fmt.fm26")
}

pub(crate) fn face_cache_dir() -> PathBuf {
    app_data_dir().join(CACHE_DIRNAME)
}

pub fn default_graphics_root() -> PathBuf {
    env::var_os("USERPROFILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
        .join("Documents")
        .join("Sports Interactive")
        .join("Football Manager 26")
        .join("graphics")
}

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GraphicsStatus {
    pub graphics_path: String,
    pub graphics_exists: bool,
    pub packs: Vec<super::packs::GraphicsPackEntry>,
}

pub fn graphics_status() -> GraphicsStatus {
    let root = default_graphics_root();
    GraphicsStatus {
        graphics_path: root.display().to_string(),
        graphics_exists: root.is_dir(),
        packs: super::packs::discover_graphics_packs(),
    }
}

pub fn faces_status() -> FacesStatus {
    let root = default_graphics_root();
    let packs = discover_face_packs();
    let cache = face_cache_dir();
    let cached_files = fs::read_dir(&cache)
        .map(|entries| entries.filter_map(|e| e.ok()).count())
        .unwrap_or(0);
    FacesStatus {
        graphics_path: root.display().to_string(),
        graphics_exists: root.is_dir(),
        face_packs_found: packs.len(),
        face_pack_names: packs,
        cached_files,
        cache_dir: cache.display().to_string(),
    }
}

fn should_skip_pack(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    lower.contains("kit")
        || lower.contains("logo")
        || lower.contains("badge")
        || lower.contains("wallpaper")
        || lower.contains("background")
        || lower.contains("icon")
}

fn is_portrait_config(config_path: &Path) -> bool {
    let lower = config_path.to_string_lossy().to_ascii_lowercase();
    !lower.contains("/iconfaces/") && !lower.contains("/icons/")
}

/// Legacy FMT shallow config discovery (see shared/faces/face-index.ts).
#[cfg(test)]
pub fn find_facepack_configs(graphics_root: &Path) -> Vec<PathBuf> {
    let mut configs = Vec::new();
    let mut seen = HashSet::new();
    let mut add = |path: PathBuf| {
        if !path.is_file() || !is_portrait_config(&path) {
            return;
        }
        if seen.insert(path.clone()) {
            configs.push(path);
        }
    };

    let Ok(packs) = fs::read_dir(graphics_root) else {
        return configs;
    };
    for pack in packs.flatten() {
        if !pack.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        if should_skip_pack(&pack.file_name().to_string_lossy()) {
            continue;
        }
        let pack_path = pack.path();
        add(pack_path.join("faces").join("config.xml"));
        add(pack_path.join("config.xml"));
        add(pack_path.join("_config.xml"));

        let Ok(subs) = fs::read_dir(&pack_path) else {
            continue;
        };
        for sub in subs.flatten() {
            if !sub.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                continue;
            }
            let sub_path = sub.path();
            add(sub_path.join("config.xml"));
            add(sub_path.join("faces").join("config.xml"));
        }
    }
    configs
}

/// Huge cutout megapacks: direct `face_{uid}.png` lookup, no XML parse.
pub fn discover_face_dirs(graphics_root: &Path) -> Vec<PathBuf> {
    let mut dirs = Vec::new();
    let Ok(packs) = fs::read_dir(graphics_root) else {
        return dirs;
    };
    for pack in packs.flatten() {
        if !pack.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        if should_skip_pack(&pack.file_name().to_string_lossy()) {
            continue;
        }
        let faces_dir = pack.path().join("faces");
        let config = faces_dir.join("config.xml");
        if !config.is_file() {
            continue;
        }
        if config
            .metadata()
            .map(|meta| meta.len() > HUGE_FACE_CONFIG_BYTES)
            .unwrap_or(false)
        {
            dirs.push(faces_dir);
        }
    }
    dirs
}

/// Pack-root configs for newgen/regen maps (`_config.xml`), not Cutout `faces/config.xml`.
fn discover_mapped_face_configs(graphics_root: &Path) -> Vec<(PathBuf, PathBuf)> {
    let mut out = Vec::new();
    let Ok(packs) = fs::read_dir(graphics_root) else {
        return out;
    };
    for pack in packs.flatten() {
        if !pack.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        if should_skip_pack(&pack.file_name().to_string_lossy()) {
            continue;
        }
        let pack_root = pack.path();
        for name in ["_config.xml", "config.xml"] {
            let config = pack_root.join(name);
            if !config.is_file() || !is_portrait_config(&config) {
                continue;
            }
            // Skip empty; allow large newgen maps (scanned once off UI thread for squad UIDs only).
            if config.metadata().map(|meta| meta.len() == 0).unwrap_or(true) {
                continue;
            }
            out.push((config, pack_root.clone()));
        }
    }
    out
}

pub fn discover_face_packs() -> Vec<String> {
    let root = default_graphics_root();
    if !root.is_dir() {
        return Vec::new();
    }

    let mut packs = HashSet::new();
    for faces_dir in discover_face_dirs(&root) {
        if let Some(pack) = faces_dir.parent().and_then(|p| p.file_name()) {
            packs.insert(pack.to_string_lossy().into_owned());
        }
    }
    for (_, pack_root) in discover_mapped_face_configs(&root) {
        if let Some(pack) = pack_root.file_name() {
            packs.insert(pack.to_string_lossy().into_owned());
        }
    }
    let mut out: Vec<String> = packs.into_iter().collect();
    out.sort();
    out
}

pub fn active_graphics_roots() -> Vec<PathBuf> {
    vec![default_graphics_root()]
}

pub(crate) fn resolve_face_path(player_id: &str, icon: bool) -> Option<PathBuf> {
    if let Some(cached) = resolve_cached_face(player_id, icon) {
        return Some(cached);
    }
    let source = resolve_live_face_path(player_id, icon)
        .or_else(|| resolve_live_face_path(player_id, !icon))?;
    copy_into_cache(player_id, icon, &source).or(Some(source))
}

fn cache_stem(player_id: &str, icon: bool) -> String {
    if icon {
        format!("icon_{player_id}")
    } else {
        player_id.to_string()
    }
}

fn resolve_cached_face(player_id: &str, icon: bool) -> Option<PathBuf> {
    let dir = face_cache_dir();
    let stems = if icon {
        vec![cache_stem(player_id, true), cache_stem(player_id, false)]
    } else {
        vec![cache_stem(player_id, false), cache_stem(player_id, true)]
    };
    for stem in stems {
        for extension in ["png", "jpg", "jpeg", "webp"] {
            let path = dir.join(format!("{stem}.{extension}"));
            if path.is_file() {
                return Some(path);
            }
        }
    }
    None
}

fn face_sidecar_path(cache_dir: &Path, stem: &str) -> PathBuf {
    cache_dir.join(format!("{stem}.src"))
}

fn read_face_identity(cache_dir: &Path, stem: &str) -> Option<String> {
    let raw = fs::read_to_string(face_sidecar_path(cache_dir, stem)).ok()?;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

fn write_face_identity(cache_dir: &Path, stem: &str, identity: &str) {
    let _ = fs::write(face_sidecar_path(cache_dir, stem), identity);
}

fn clear_cached_face_variants(cache_dir: &Path, stem: &str) {
    for extension in ["png", "jpg", "jpeg", "webp"] {
        let _ = fs::remove_file(cache_dir.join(format!("{stem}.{extension}")));
    }
}

fn cutout_source_identity(source: &Path) -> String {
    format!("file:{}", source.to_string_lossy())
}

fn mapped_source_identity(from: &str) -> String {
    format!("map:{from}")
}

/// Cache is stale when missing, identity changed (recycled UID remap), or source bytes differ.
fn face_needs_refresh(
    cache_len: Option<u64>,
    cache_modified: Option<SystemTime>,
    source_len: u64,
    source_modified: Option<SystemTime>,
    stored_identity: Option<&str>,
    live_identity: &str,
) -> bool {
    if cache_len.is_none() {
        return true;
    }
    if stored_identity != Some(live_identity) {
        return true;
    }
    if cache_len != Some(source_len) {
        return true;
    }
    match (source_modified, cache_modified) {
        (Some(src), Some(cached)) if src > cached => true,
        (Some(_), None) => true,
        _ => false,
    }
}

fn sync_face_into_cache(
    player_id: &str,
    icon: bool,
    source: &Path,
    identity: &str,
) -> Option<PathBuf> {
    let meta = source.metadata().ok()?;
    if !meta.is_file() || meta.len() == 0 || meta.len() > MAX_IMAGE_BYTES {
        return None;
    }
    let ext = source
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("png")
        .to_ascii_lowercase();
    if !matches!(ext.as_str(), "png" | "jpg" | "jpeg" | "webp") {
        return None;
    }
    let dir = face_cache_dir();
    fs::create_dir_all(&dir).ok()?;
    let stem = cache_stem(player_id, icon);
    let dest = dir.join(format!("{stem}.{ext}"));
    let stored = read_face_identity(&dir, &stem);
    let cache_meta = dest.metadata().ok().filter(|m| m.is_file());
    let stale = face_needs_refresh(
        cache_meta.as_ref().map(|m| m.len()),
        cache_meta.as_ref().and_then(|m| m.modified().ok()),
        meta.len(),
        meta.modified().ok(),
        stored.as_deref(),
        identity,
    );
    // Other extension may still be the hit `resolve_cached_face` returns.
    let other_hit = resolve_cached_face(player_id, icon).filter(|p| p != &dest);
    if !stale && other_hit.is_none() {
        return Some(dest);
    }
    clear_cached_face_variants(&dir, &stem);
    fs::copy(source, &dest).ok()?;
    write_face_identity(&dir, &stem, identity);
    Some(dest)
}

fn copy_into_cache(player_id: &str, icon: bool, source: &Path) -> Option<PathBuf> {
    sync_face_into_cache(player_id, icon, source, &cutout_source_identity(source))
}

fn pack_path_is_newgen(path: &Path) -> bool {
    path.to_string_lossy()
        .to_ascii_lowercase()
        .contains("newgen")
}

#[derive(Clone)]
struct FaceDirBuckets {
    main: Vec<PathBuf>,
    newgen: Vec<PathBuf>,
}

fn cached_face_dir_buckets() -> FaceDirBuckets {
    static BUCKETS: OnceLock<FaceDirBuckets> = OnceLock::new();
    BUCKETS
        .get_or_init(|| {
            let mut main = Vec::new();
            let mut newgen = Vec::new();
            for dir in discover_face_dirs(&default_graphics_root()) {
                if pack_path_is_newgen(&dir) {
                    newgen.push(dir);
                } else {
                    main.push(dir);
                }
            }
            FaceDirBuckets { main, newgen }
        })
        .clone()
}

fn resolve_live_face_path_in_dirs(player_id: &str, icon: bool, dirs: &[PathBuf]) -> Option<PathBuf> {
    if icon {
        return None;
    }
    for dir in dirs {
        for stem in [
            format!("face_{player_id}"),
            format!("iconface_{player_id}"),
            player_id.to_string(),
        ] {
            for extension in ["png", "jpg", "jpeg", "webp"] {
                let path = dir.join(format!("{stem}.{extension}"));
                if path.is_file() {
                    return Some(path);
                }
            }
        }
    }
    None
}

/// Search cutout dirs in install order: main face packs first, then newgen-named packs.
/// Player origin (database vs game-generated) is not guessed from UID — pack search only.
fn resolve_live_face_path(player_id: &str, icon: bool) -> Option<PathBuf> {
    let buckets = cached_face_dir_buckets();
    resolve_live_face_path_in_dirs(player_id, icon, &buckets.main)
        .or_else(|| resolve_live_face_path_in_dirs(player_id, icon, &buckets.newgen))
}

fn parse_person_portrait_record(line: &str) -> Option<(String, String)> {
    if !line.contains("from=\"") || !line.contains("to=\"") {
        return None;
    }
    if !line.contains("graphics/pictures/person/") || !line.contains("/portrait") {
        return None;
    }
    let from = attribute_value(line, "from")?;
    let to = attribute_value(line, "to")?;
    let marker = "graphics/pictures/person/";
    let start = to.find(marker)? + marker.len();
    let rest = &to[start..];
    let end = rest.find("/portrait")?;
    let uid = rest[..end].trim_start_matches("r-").to_string();
    if uid.is_empty() || !uid.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    Some((from.to_string(), uid))
}

fn resolve_mapped_image(pack_root: &Path, relative: &Path) -> Option<PathBuf> {
    let direct = pack_root.join(relative);
    if valid_image_file(&direct) {
        return Some(direct);
    }
    if relative.extension().is_some() {
        return None;
    }
    for extension in ["png", "jpg", "jpeg", "webp"] {
        let path = pack_root.join(relative.with_extension(extension));
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

struct MappedFaceSource {
    from: String,
    path: PathBuf,
}

/// One-pass scan of pack-root maps for the requested UIDs only (background warm).
fn scan_mapped_face_configs(wanted: &HashSet<String>) -> HashMap<String, MappedFaceSource> {
    let mut found = HashMap::new();
    if wanted.is_empty() {
        return found;
    }
    for (config, pack_root) in discover_mapped_face_configs(&default_graphics_root()) {
        if found.len() == wanted.len() {
            break;
        }
        let Ok(file) = fs::File::open(&config) else {
            continue;
        };
        for line in BufReader::new(file).lines().map_while(Result::ok) {
            if found.len() == wanted.len() {
                break;
            }
            let Some((from, uid)) = parse_person_portrait_record(&line) else {
                continue;
            };
            if !wanted.contains(&uid) || found.contains_key(&uid) {
                continue;
            }
            let Some(relative) = safe_relative_asset_path(&from) else {
                continue;
            };
            if let Some(path) = resolve_mapped_image(&pack_root, &relative) {
                found.insert(
                    uid,
                    MappedFaceSource {
                        from,
                        path,
                    },
                );
            }
        }
    }
    found
}

pub fn warm_faces_for_players(player_ids: &[String], icon: bool) -> FaceWarmResult {
    let cache = face_cache_dir();
    let _ = fs::create_dir_all(&cache);
    let ids: Vec<String> = player_ids
        .iter()
        .map(|id| id.trim().to_string())
        .filter(|id| !id.is_empty() && id.bytes().all(|b| b.is_ascii_digit()))
        .collect();
    let requested = ids.len();
    let cache_dir = cache.display().to_string();
    let icon_flag = icon;
    if !ids.is_empty() {
        thread::spawn(move || {
            let mut pending = Vec::new();
            for id in ids {
                if let Some(source) = resolve_live_face_path(&id, icon_flag) {
                    let identity = cutout_source_identity(&source);
                    let _ = sync_face_into_cache(&id, icon_flag, &source, &identity);
                } else if !icon_flag {
                    // Re-check mapped packs even when cache already has a UID hit
                    // (recycled newgen remaps change `from=` under the same id).
                    pending.push(id);
                }
            }
            if pending.is_empty() {
                return;
            }
            let wanted: HashSet<String> = pending.iter().cloned().collect();
            let mapped = scan_mapped_face_configs(&wanted);
            for id in pending {
                if let Some(hit) = mapped.get(&id) {
                    let identity = mapped_source_identity(&hit.from);
                    let _ = sync_face_into_cache(&id, false, &hit.path, &identity);
                }
            }
        });
    }
    FaceWarmResult {
        requested,
        cached: 0,
        copied: 0,
        missing: 0,
        cache_dir,
    }
}

pub(crate) fn image_mime(path: &Path) -> Option<&'static str> {
    match path.extension()?.to_str()?.to_ascii_lowercase().as_str() {
        "png" => Some("image/png"),
        "jpg" | "jpeg" => Some("image/jpeg"),
        "webp" => Some("image/webp"),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn only_supported_image_types_receive_a_mime() {
        assert_eq!(image_mime(Path::new("face_1.png")), Some("image/png"));
        assert_eq!(image_mime(Path::new("face_1.svg")), None);
    }

    #[test]
    fn parse_person_portrait_record_handles_cutout_and_regen_ids() {
        let cutout = r#"<record from="face_2000370823" to="graphics/pictures/person/2000370823/portrait"/>"#;
        let regen = r#"<record from="CentralEurope/PP12CentralEurope0853" to="graphics/pictures/person/r-100679936/portrait"/>"#;
        assert_eq!(
            parse_person_portrait_record(cutout),
            Some(("face_2000370823".into(), "2000370823".into()))
        );
        assert_eq!(
            parse_person_portrait_record(regen),
            Some(("CentralEurope/PP12CentralEurope0853".into(), "100679936".into()))
        );
    }

    #[test]
    fn face_needs_refresh_when_mapped_identity_changes() {
        let now = SystemTime::now();
        assert!(face_needs_refresh(
            Some(100),
            Some(now),
            100,
            Some(now),
            Some("map:CentralEurope/OldFace"),
            "map:CentralEurope/NewFace",
        ));
        assert!(!face_needs_refresh(
            Some(100),
            Some(now),
            100,
            Some(now),
            Some("map:CentralEurope/SameFace"),
            "map:CentralEurope/SameFace",
        ));
    }

    #[test]
    fn face_needs_refresh_when_source_newer_or_size_differs() {
        let older = SystemTime::now() - Duration::from_secs(60);
        let newer = SystemTime::now();
        assert!(face_needs_refresh(
            Some(100),
            Some(older),
            100,
            Some(newer),
            Some("file:C:/faces/face_1.png"),
            "file:C:/faces/face_1.png",
        ));
        assert!(face_needs_refresh(
            Some(100),
            Some(newer),
            120,
            Some(newer),
            Some("file:C:/faces/face_1.png"),
            "file:C:/faces/face_1.png",
        ));
        assert!(!face_needs_refresh(
            Some(100),
            Some(newer),
            100,
            Some(older),
            Some("file:C:/faces/face_1.png"),
            "file:C:/faces/face_1.png",
        ));
        assert!(face_needs_refresh(
            None,
            None,
            100,
            Some(newer),
            None,
            "map:CentralEurope/PP12",
        ));
    }

    #[test]
    fn mapped_source_identity_prefixes_from_path() {
        assert_eq!(
            mapped_source_identity("CentralEurope/PP12CentralEurope0853"),
            "map:CentralEurope/PP12CentralEurope0853"
        );
    }

    #[test]
    fn find_facepack_configs_includes_regional_newgan_configs() {
        let root = default_graphics_root();
        if !root.is_dir() {
            return;
        }
        let configs = find_facepack_configs(&root);
        let mapped = discover_mapped_face_configs(&root);
        let newgan = root.join("NGRegens_Newgens_Megapack");
        if newgan.is_dir() {
            assert!(
                configs.iter().any(|path| {
                    path.to_string_lossy().contains("NGRegens_Newgens_Megapack")
                        && (path.ends_with("config.xml") || path.ends_with("_config.xml"))
                }) || mapped.iter().any(|(path, _)| {
                    path.to_string_lossy().contains("NGRegens_Newgens_Megapack")
                })
            );
        }
    }

    #[test]
    fn mapped_scan_resolves_known_regen_uid_when_pack_present() {
        let root = default_graphics_root();
        let sample = root
            .join("NGRegens_Newgens_Megapack")
            .join("CentralEurope")
            .join("PP12CentralEurope0853.png");
        if !sample.is_file() {
            return;
        }
        let wanted = HashSet::from(["100679936".to_string()]);
        let found = scan_mapped_face_configs(&wanted);
        let hit = found.get("100679936").expect("mapped face for sample uid");
        assert_eq!(hit.path, sample);
        assert_eq!(hit.from, "CentralEurope/PP12CentralEurope0853");
        assert_eq!(
            mapped_source_identity(&hit.from),
            "map:CentralEurope/PP12CentralEurope0853"
        );
    }
}
