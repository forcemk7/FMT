use std::{
    env, fs,
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
    sync::Mutex,
};

use super::config_xml::{attribute_value, safe_single_component_stem, MAX_GRAPHICS_CONFIG_BYTES};

pub(crate) const MAX_IMAGE_BYTES: u64 = 8 * 1024 * 1024;

const SETTINGS_FILE: &str = "graphics-settings.json";
const CACHE_DIRNAME: &str = "face-cache";

static GRAPHICS_ROOT_OVERRIDE: Mutex<Option<PathBuf>> = Mutex::new(None);

#[derive(serde::Serialize, serde::Deserialize, Clone, Default)]
#[serde(rename_all = "camelCase")]
pub struct GraphicsSettings {
    pub graphics_root: Option<String>,
}

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FaceWarmResult {
    pub requested: usize,
    pub cached: usize,
    pub copied: usize,
    pub missing: usize,
    pub graphics_root: String,
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

pub fn load_graphics_settings() -> GraphicsSettings {
    let path = app_data_dir().join(SETTINGS_FILE);
    let Ok(bytes) = fs::read(&path) else {
        return GraphicsSettings::default();
    };
    serde_json::from_slice(&bytes).unwrap_or_default()
}

pub fn save_graphics_settings(settings: &GraphicsSettings) -> Result<(), String> {
    let dir = app_data_dir();
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let path = dir.join(SETTINGS_FILE);
    let bytes = serde_json::to_vec_pretty(settings).map_err(|e| e.to_string())?;
    fs::write(path, bytes).map_err(|e| e.to_string())?;
    if let Ok(mut guard) = GRAPHICS_ROOT_OVERRIDE.lock() {
        *guard = settings
            .graphics_root
            .as_ref()
            .map(|s| PathBuf::from(s.trim()))
            .filter(|p| !p.as_os_str().is_empty());
    }
    Ok(())
}

pub fn active_graphics_root() -> PathBuf {
    if let Ok(guard) = GRAPHICS_ROOT_OVERRIDE.lock() {
        if let Some(path) = guard.as_ref() {
            return path.clone();
        }
    }
    let settings = load_graphics_settings();
    if let Some(root) = settings.graphics_root.as_ref() {
        let trimmed = root.trim();
        if !trimmed.is_empty() {
            return PathBuf::from(trimmed);
        }
    }
    default_graphics_root()
}

pub(crate) fn resolve_face_path(player_id: &str, icon: bool) -> Option<PathBuf> {
    if let Some(cached) = resolve_cached_face(player_id, icon) {
        return Some(cached);
    }
    let source = resolve_live_face_path(player_id, icon)?;
    copy_into_cache(player_id, icon, &source).or(Some(source))
}

fn resolve_cached_face(player_id: &str, icon: bool) -> Option<PathBuf> {
    let dir = face_cache_dir();
    let stem = if icon {
        format!("icon_{player_id}")
    } else {
        player_id.to_string()
    };
    for extension in ["png", "jpg", "jpeg", "webp"] {
        let path = dir.join(format!("{stem}.{extension}"));
        if path.is_file() {
            return Some(path);
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
    let root = active_graphics_root();
    if !root.is_dir() {
        return None;
    }
    for directory in face_search_dirs(&root, icon) {
        for stem in [
            format!("face_{player_id}"),
            player_id.to_string(),
            format!("iconface_{player_id}"),
        ] {
            for extension in ["png", "jpg", "jpeg", "webp"] {
                let path = directory.join(format!("{stem}.{extension}"));
                if path.is_file() {
                    return Some(path);
                }
            }
        }
        let config = directory.join("config.xml");
        if let Some(path) = resolve_face_from_config(&config, &directory, player_id) {
            return Some(path);
        }
    }
    None
}

/// Shallow pack discovery — do not walk entire megapack trees.
fn face_search_dirs(graphics_root: &Path, icon: bool) -> Vec<PathBuf> {
    let folder = if icon { "iconfaces" } else { "faces" };
    let mut dirs = Vec::new();
    let mut push = |path: PathBuf| {
        if path.is_dir() && !dirs.iter().any(|existing| existing == &path) {
            dirs.push(path);
        }
    };

    push(graphics_root.join(folder));

    let Ok(entries) = fs::read_dir(graphics_root) else {
        return dirs;
    };
    for entry in entries.flatten() {
        let Ok(file_type) = entry.file_type() else {
            continue;
        };
        if !file_type.is_dir() {
            continue;
        }
        let name = entry.file_name().to_string_lossy().to_ascii_lowercase();
        if name.contains("kit")
            || name.contains("logo")
            || name.contains("badge")
            || name.contains("wallpaper")
            || name.contains("background")
        {
            continue;
        }
        let pack = entry.path();
        push(pack.join(folder));
        push(pack.clone());
        if let Ok(subs) = fs::read_dir(&pack) {
            for sub in subs.flatten() {
                if sub.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                    let sub_path = sub.path();
                    let sub_name = sub.file_name().to_string_lossy().to_ascii_lowercase();
                    if sub_name == folder || sub_name == "faces" || sub_name == "iconfaces" {
                        push(sub_path);
                    } else {
                        push(sub_path.join(folder));
                    }
                }
            }
        }
    }
    dirs
}

pub fn warm_faces_for_players(player_ids: &[String], icon: bool) -> FaceWarmResult {
    let root = active_graphics_root();
    let cache = face_cache_dir();
    let _ = fs::create_dir_all(&cache);
    let mut cached = 0usize;
    let mut copied = 0usize;
    let mut missing = 0usize;
    for player_id in player_ids {
        let id = player_id.trim();
        if id.is_empty() || !id.bytes().all(|b| b.is_ascii_digit()) {
            missing += 1;
            continue;
        }
        if resolve_cached_face(id, icon).is_some() {
            cached += 1;
            continue;
        }
        match resolve_live_face_path(id, icon) {
            Some(source) => {
                if copy_into_cache(id, icon, &source).is_some() {
                    copied += 1;
                } else {
                    missing += 1;
                }
            }
            None => missing += 1,
        }
    }
    FaceWarmResult {
        requested: player_ids.len(),
        cached,
        copied,
        missing,
        graphics_root: root.display().to_string(),
        cache_dir: cache.display().to_string(),
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

fn resolve_face_from_config(config: &Path, directory: &Path, player_id: &str) -> Option<PathBuf> {
    let metadata = config.metadata().ok()?;
    if metadata.len() > MAX_GRAPHICS_CONFIG_BYTES {
        return None;
    }
    let file = fs::File::open(config).ok()?;
    let reader = BufReader::new(file);
    let marker = format!("person/{player_id}/");
    for line in reader.lines().map_while(Result::ok) {
        if !line.contains(&marker) {
            continue;
        }
        let from = safe_single_component_stem(attribute_value(&line, "from")?)?;
        for extension in ["png", "jpg", "jpeg", "webp"] {
            let path = directory.join(format!("{from}.{extension}"));
            if path.is_file() {
                return Some(path);
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_supported_image_types_receive_a_mime() {
        assert_eq!(image_mime(Path::new("face_1.png")), Some("image/png"));
        assert_eq!(image_mime(Path::new("face_1.svg")), None);
    }
}
