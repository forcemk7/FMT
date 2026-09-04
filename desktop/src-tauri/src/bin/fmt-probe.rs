//! RE / QA probe CLI.

use std::{env, io::Write, process::ExitCode};

fn main() -> ExitCode {
    let usage = "Usage: fmt-probe <command>\n  affiliate-flags\n  club-teams";
    let Some(command) = env::args().nth(1) else {
        eprintln!("{usage}");
        return ExitCode::from(2);
    };

    let _ = writeln!(std::io::stderr(), "fmt-probe {command}");

    let result = match command.as_str() {
        "affiliate-flags" => glassscout_fm26_lib::connector::run_debug_probe_affiliate_flags(),
        "club-teams" => glassscout_fm26_lib::connector::run_debug_scan_club_teams(),
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
