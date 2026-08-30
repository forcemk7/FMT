#![recursion_limit = "256"]

mod commands;
mod connector;
mod data;
mod fm26;
mod fm_dossier;
mod fmt_log;
mod graphics;
mod player_face;
mod visibility;

use tauri_plugin_sql::{Migration, MigrationKind};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let _registered_commands = commands::registered_commands();
    let migrations = vec![Migration {
        version: 1,
        description: "initial_revealed_data_schema",
        sql: include_str!("../migrations/001_initial.sql"),
        kind: MigrationKind::Up,
    }];

    tauri::Builder::default()
        .plugin(
            tauri_plugin_sql::Builder::default()
                .add_migrations("sqlite:fmt.db", migrations)
                .build(),
        )
        .invoke_handler(tauri::generate_handler![
            fmt_log::fmt_terminal_log,
            connector::connector_status,
            connector::connector_snapshot,
            connector::load_active_save,
            connector::load_club_satellite_squads,
            connector::debug_scan_club_teams,
            connector::debug_scan_club_affiliates,
            connector::debug_probe_player_origin,
            connector::search_indexed_players,
            connector::indexed_players_by_ids,
            connector::indexed_player_profile,
            player_face::club_logo_data,
            player_face::faces_status,
            player_face::faces_update_cache,
            player_face::flags_update_cache,
            player_face::graphics_status,
            player_face::logos_update_cache,
            player_face::nation_flag_data,
            player_face::player_face_data,
            visibility::filter_observations
        ])
        .run(tauri::generate_context!())
        .expect("error while running FMT");
}
