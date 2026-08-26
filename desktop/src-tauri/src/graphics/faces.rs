use std::{
    collections::HashSet,
    env, fs,
    path::{Path, PathBuf},
    sync::OnceLock,
    thread,
};

#[cfg(test)]
use super::config_xml::attribute_value;

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

#[cfg(test)]
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

fn resolve_cached_face(player_id: &str, icon: bool) -> Option<PathBuf> {
    let dir = face_cache_dir();
    let stems = if icon {
        vec![format!("icon_{player_id}"), player_id.to_string()]
    } else {
        vec![player_id.to_string(), format!("icon_{player_id}")]
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

fn copy_into_cache(player_id: &str, icon: bool, source: &Path) -> Option<PathBuf> {
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
    let stem = if icon {
        format!("icon_{player_id}")
    } else {
        player_id.to_string()
    };
    let dest = dir.join(format!("{stem}.{ext}"));
    fs::copy(source, &dest).ok()?;
    Some(dest)
}

fn resolve_live_face_path(player_id: &str, icon: bool) -> Option<PathBuf> {
    // Hot path: O(1) open face_{id}.* in known megapack dirs only.
    // Never build/parse config.xml indexes here — that froze the UI on first miss.
    if icon {
        return None;
    }
    for dir in cached_face_dirs() {
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

fn cached_face_dirs() -> Vec<PathBuf> {
    static FACE_DIRS: OnceLock<Vec<PathBuf>> = OnceLock::new();
    FACE_DIRS
        .get_or_init(|| discover_face_dirs(&default_graphics_root()))
        .clone()
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
            for id in ids {
                if resolve_cached_face(&id, icon_flag).is_some() {
                    continue;
                }
                if let Some(source) = resolve_live_face_path(&id, icon_flag) {
                    let _ = copy_into_cache(&id, icon_flag, &source);
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_supported_image_types_receive_a_mime() {
        assert_eq!(image_mime(Path::new("face_1.png")), Some("image/png"));
        assert_eq!(image_mime(Path::new("face_1.svg")), None);
    }

    #[test]
    fn parse_person_portrait_record_handles_cutout_and_regen_ids() {
        let cutout = r#"<record from="face_2000370823" to="graphics/pictures/person/2000370823/portrait"/>"#;
        let regen = r#"<record from="PP12CentralEurope0853" to="graphics/pictures/person/r-100679936/portrait"/>"#;
        assert_eq!(
            parse_person_portrait_record(cutout),
            Some(("face_2000370823".into(), "2000370823".into()))
        );
        assert_eq!(
            parse_person_portrait_record(regen),
            Some(("PP12CentralEurope0853".into(), "100679936".into()))
        );
    }

    #[test]
    fn find_facepack_configs_includes_regional_newgan_configs() {
        let root = default_graphics_root();
        if !root.is_dir() {
            return;
        }
        let configs = find_facepack_configs(&root);
        let newgan = root.join("NGRegens_Newgens_Megapack");
        if newgan.is_dir() {
            assert!(configs.iter().any(|path| {
                path.to_string_lossy().contains("NGRegens_Newgens_Megapack")
                    && path.ends_with("config.xml")
            }));
        }
    }
}
