//! RE probe CLI. T203 ships `affiliate-flags` only (FMLE A/B on link-vector structs).

use std::{env, io::Write, process::ExitCode};

fn main() -> ExitCode {
    let usage = "Usage: fmt-probe affiliate-flags\n  Dump managed-club @0x8E8 link structs for FMLE flag A/B.";
    let Some(command) = env::args().nth(1) else {
        eprintln!("{usage}");
        return ExitCode::from(2);
    };

    let _ = writeln!(std::io::stderr(), "fmt-probe {command}");

    let result = match command.as_str() {
        "affiliate-flags" => glassscout_fm26_lib::connector::run_debug_probe_affiliate_flags(),
        other => {
            eprintln!("Unknown command '{other}'.\n{usage}");
            return ExitCode::from(2);
        }
    };

    match result {
        Ok(value) => {
            println!("{}", serde_json::to_string_pretty(&value).unwrap_or_else(|err| err.to_string()));
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("{message}");
            ExitCode::from(1)
        }
    }
}
