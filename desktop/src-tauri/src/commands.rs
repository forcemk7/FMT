pub(crate) const REGISTERED_COMMANDS: &[&str] = &[
    "fmt_terminal_log",
    "connector_status",
    "connector_snapshot",
    "load_active_save",
    "load_club_satellite_squads",
    "debug_scan_club_teams",
    "debug_scan_club_affiliates",
    "debug_probe_player_origin",
    "search_indexed_players",
    "indexed_players_by_ids",
    "club_logo_data",
    "nation_flag_data",
    "player_face_data",
    "faces_status",
    "graphics_status",
    "faces_update_cache",
    "logos_update_cache",
    "flags_update_cache",
    "filter_observations",
];

pub(crate) fn registered_commands() -> &'static [&'static str] {
    REGISTERED_COMMANDS
}
