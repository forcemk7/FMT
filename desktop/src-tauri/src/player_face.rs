use base64::{engine::general_purpose::STANDARD, Engine};
use serde::Serialize;
use std::fs;

use crate::graphics::{
    faces::{
        image_mime, load_graphics_settings, resolve_face_path, save_graphics_settings,
        warm_faces_for_players, FaceWarmResult, GraphicsSettings, MAX_IMAGE_BYTES,
        active_graphics_root, default_graphics_root, face_cache_dir,
    },
    logos::resolve_logo_path,
};

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PlayerFaceResult {
    found: bool,
    player_id: String,
    data_url: Option<String>,
    source: &'static str,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ClubLogoResult {
    found: bool,
    club_id: String,
    data_url: Option<String>,
}

#[tauri::command]
pub fn player_face_data(player_id: String, icon: bool) -> PlayerFaceResult {
    let player_id = player_id.trim().to_string();
    if player_id.is_empty() || !player_id.bytes().all(|byte| byte.is_ascii_digit()) {
        return missing(player_id);
    }

    let Some(path) = resolve_face_path(&player_id, icon) else {
        return missing(player_id);
    };
    let Ok(metadata) = path.metadata() else {
        return missing(player_id);
    };
    if !metadata.is_file() || metadata.len() == 0 || metadata.len() > MAX_IMAGE_BYTES {
        return missing(player_id);
    }
    let Some(mime) = image_mime(&path) else {
        return missing(player_id);
    };
    let Ok(bytes) = fs::read(path) else {
        return missing(player_id);
    };

    PlayerFaceResult {
        found: true,
        player_id,
        data_url: Some(format!("data:{mime};base64,{}", STANDARD.encode(bytes))),
        source: "fm-unique-id",
    }
}

#[tauri::command]
pub fn club_logo_data(club_id: String) -> ClubLogoResult {
    let club_id = club_id.trim().to_string();
    if club_id.is_empty() || !club_id.bytes().all(|byte| byte.is_ascii_digit()) {
        return ClubLogoResult {
            found: false,
            club_id,
            data_url: None,
        };
    }
    if let Some(path) = resolve_logo_path(&club_id) {
        if let (Some(mime), Ok(bytes)) = (image_mime(&path), fs::read(path)) {
            return ClubLogoResult {
                found: true,
                club_id,
                data_url: Some(format!("data:{mime};base64,{}", STANDARD.encode(bytes))),
            };
        }
    }
    ClubLogoResult {
        found: false,
        club_id,
        data_url: None,
    }
}

fn missing(player_id: String) -> PlayerFaceResult {
    PlayerFaceResult {
        found: false,
        player_id,
        data_url: None,
        source: "fallback",
    }
}

#[tauri::command]
pub fn graphics_settings_get() -> GraphicsSettings {
    let mut settings = load_graphics_settings();
    if settings.graphics_root.as_ref().map(|s| s.trim().is_empty()).unwrap_or(true) {
        settings.graphics_root = Some(default_graphics_root().display().to_string());
    }
    settings
}

#[tauri::command]
pub fn graphics_settings_set(graphics_root: String) -> Result<GraphicsSettings, String> {
    let trimmed = graphics_root.trim().to_string();
    let settings = GraphicsSettings {
        graphics_root: if trimmed.is_empty() {
            None
        } else {
            Some(trimmed)
        },
    };
    save_graphics_settings(&settings)?;
    Ok(graphics_settings_get())
}

#[tauri::command]
pub fn faces_update_cache(player_ids: Vec<String>) -> FaceWarmResult {
    warm_faces_for_players(&player_ids, false)
}

#[tauri::command]
pub fn faces_cache_status() -> serde_json::Value {
    let root = active_graphics_root();
    let cache = face_cache_dir();
    let cached_files = fs::read_dir(&cache)
        .map(|entries| entries.filter_map(|e| e.ok()).count())
        .unwrap_or(0);
    serde_json::json!({
        "graphicsRoot": root.display().to_string(),
        "graphicsRootExists": root.is_dir(),
        "cacheDir": cache.display().to_string(),
        "cachedFiles": cached_files,
    })
}

#[cfg(test)]
mod tests {
    #[test]
    fn player_face_command_rejects_non_numeric_ids() {
        let result = super::player_face_data("../bad".to_string(), false);
        assert!(!result.found);
        assert_eq!(result.source, "fallback");
    }
}
