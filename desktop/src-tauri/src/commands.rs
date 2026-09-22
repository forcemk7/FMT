pub(crate) const REGISTERED_COMMANDS: &[&str] = &[
    "fmt_terminal_log",
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
