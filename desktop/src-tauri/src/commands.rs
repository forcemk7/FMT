pub(crate) const REGISTERED_COMMANDS: &[&str] = &[
    "fmt_terminal_log",
    "open_external",
    "connector_status",
    "connector_snapshot",
    "connector_heartbeat",
    "load_active_save",
    "club_logo_data",
    "nation_flag_data",
    "player_face_data",
    "faces_status",
    "graphics_status",
    "faces_update_cache",
    "logos_update_cache",
    "flags_update_cache",
];

pub(crate) fn registered_commands() -> &'static [&'static str] {
    REGISTERED_COMMANDS
}

/// Open a URL in the OS default browser. Routed through `explorer.exe` rather than
/// `cmd /C start` so the URL is passed as a literal argument, never parsed by a shell
/// (no `&`/`|` command-injection surface) — see T291 BMC-link-in-Tauri follow-up.
#[tauri::command]
pub(crate) fn open_external(url: String) -> Result<(), String> {
    if !url.starts_with("https://") {
        return Err("only https URLs may be opened".to_string());
    }
    std::process::Command::new("explorer")
        .arg(url)
        .spawn()
        .map(|_| ())
        .map_err(|err| err.to_string())
}
