#![recursion_limit = "256"]
// Product builds: silence RE leftover dead_code. Research: --features fm-probe.
#![cfg_attr(not(feature = "fm-probe"), allow(dead_code))]

mod commands;
pub mod connector;
mod fm26;
mod fmt_log;
mod graphics;
mod player_face;

use tauri_plugin_sql::{Migration, MigrationKind};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // First line, on purpose: every boot-diagnostic timestamp downstream (window
    // creation, page compile/serve, React mount, first poll, first heartbeat, first
    // load) is relative to this, so the whole boot sequence lands on one comparable
    // clock instead of scattered, un-anchored numbers.
    fmt_log::mark_boot_start();
    eprintln!("[fmt] +0ms  run() start");
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
            commands::open_external,
            connector::connector_status,
            connector::connector_snapshot,
            connector::connector_heartbeat,
            connector::load_active_save,
            player_face::club_logo_data,
            player_face::faces_status,
            player_face::faces_update_cache,
            player_face::flags_update_cache,
            player_face::graphics_status,
            player_face::logos_update_cache,
            player_face::nation_flag_data,
            player_face::player_face_data,
        ])
        .run(tauri::generate_context!())
        .expect("error while running FMT");
}
