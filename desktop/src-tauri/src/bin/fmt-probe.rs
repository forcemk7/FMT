//! RE / QA probe CLI.

use std::{env, io::Write, process::ExitCode};

fn main() -> ExitCode {
    let usage = "Usage: fmt-probe <command> [args]\n  affiliate-flags\n  club-teams\n  club-affiliates\n  affiliate-containers\n  agreement-table\n  pge-sign\n  editor-affiliations\n  duisburg-ab [feeder|likely]\n  affil-types";
    let Some(command) = env::args().nth(1) else {
        eprintln!("{usage}");
        return ExitCode::from(2);
    };

    let _ = writeln!(std::io::stderr(), "fmt-probe {command}");

    let result = match command.as_str() {
        "affiliate-flags" => glassscout_fm26_lib::connector::run_debug_probe_affiliate_flags(),
        "club-teams" => glassscout_fm26_lib::connector::run_debug_scan_club_teams(),
        "club-affiliates" => glassscout_fm26_lib::connector::run_debug_scan_club_affiliates(),
        "affiliate-containers" => {
            glassscout_fm26_lib::connector::run_debug_probe_affiliate_containers()
        }
        "agreement-table" => glassscout_fm26_lib::connector::run_debug_probe_agreement_table(),
        "pge-sign" => glassscout_fm26_lib::connector::run_debug_probe_pge_affiliation_sign(),
        "editor-affiliations" => {
            glassscout_fm26_lib::connector::run_debug_probe_editor_affiliations()
        }
        "duisburg-ab" => {
            let label = env::args().nth(2).unwrap_or_else(|| "feeder".into());
            glassscout_fm26_lib::connector::run_debug_probe_duisburg_type_ab(&label)
        }
        "affil-types" => glassscout_fm26_lib::connector::run_debug_probe_affiliation_type_census(),
        other => {
            eprintln!("Unknown command '{other}'.\n{usage}");
            return ExitCode::from(2);
        }
    };

    match result {
        Ok(value) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&value).unwrap_or_else(|err| err.to_string())
            );
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("{message}");
            ExitCode::from(1)
        }
    }
}
