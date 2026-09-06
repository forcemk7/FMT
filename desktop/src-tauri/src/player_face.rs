use base64::{engine::general_purpose::STANDARD, Engine};
use serde::Serialize;
use std::fs;

use crate::graphics::{
    faces::{
        faces_status as read_faces_status, graphics_status as read_graphics_status,
        image_mime, resolve_face_path, warm_faces_for_players, FaceWarmResult, FacesStatus,
        GraphicsStatus, MAX_IMAGE_BYTES,
    },
    flags::{resolve_flag_path, warm_flags_for_nations},
    logos::{resolve_logo_lookup, warm_logos_for_clubs, LogoLookup},
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
    /// True while logo pack index / cache fill may still resolve this UniqueID.
    pending: bool,
    club_id: String,
    data_url: Option<String>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct NationFlagResult {
    found: bool,
    nation_id: String,
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
            pending: false,
            club_id,
            data_url: None,
        };
    }
    match resolve_logo_lookup(&club_id) {
        (LogoLookup::Found, Some(path)) => {
            if let (Some(mime), Ok(bytes)) = (image_mime(&path), fs::read(&path)) {
                return ClubLogoResult {
                    found: true,
                    pending: false,
                    club_id,
                    data_url: Some(format!("data:{mime};base64,{}", STANDARD.encode(bytes))),
                };
            }
            ClubLogoResult {
                found: false,
                pending: true,
                club_id,
                data_url: None,
            }
        }
        (LogoLookup::Pending, _) => ClubLogoResult {
            found: false,
            pending: true,
            club_id,
            data_url: None,
        },
        (LogoLookup::Missing, _) | (LogoLookup::Found, None) => ClubLogoResult {
            found: false,
            pending: false,
            club_id,
            data_url: None,
        },
    }
}

#[tauri::command]
pub fn nation_flag_data(nation_id: String) -> NationFlagResult {
    let nation_id = nation_id.trim().to_string();
    if nation_id.is_empty() || !nation_id.bytes().all(|byte| byte.is_ascii_digit()) {
        return NationFlagResult {
            found: false,
            nation_id,
            data_url: None,
        };
    }
    if let Some(path) = resolve_flag_path(&nation_id) {
        if let (Some(mime), Ok(bytes)) = (image_mime(&path), fs::read(&path)) {
            return NationFlagResult {
                found: true,
                nation_id,
                data_url: Some(format!("data:{mime};base64,{}", STANDARD.encode(bytes))),
            };
        }
    }
    NationFlagResult {
        found: false,
        nation_id,
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
pub fn faces_status() -> FacesStatus {
    read_faces_status()
}

#[tauri::command]
pub fn graphics_status() -> GraphicsStatus {
    read_graphics_status()
}

#[tauri::command]
pub fn faces_update_cache(player_ids: Vec<String>) -> FaceWarmResult {
    warm_faces_for_players(&player_ids, false)
}

#[tauri::command]
pub fn logos_update_cache(club_ids: Vec<String>) -> FaceWarmResult {
    warm_logos_for_clubs(&club_ids)
}

#[tauri::command]
pub fn flags_update_cache(nation_ids: Vec<String>) -> FaceWarmResult {
    warm_flags_for_nations(&nation_ids)
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
