//! Live RE: dump in-game current-date / birth-date bytes for the managed squad.
//!
//! ```text
//! cargo run -p fmt --features fm-probe --bin probe-game-date
//! ```

fn main() {
    match glassscout_fm26_lib::connector::probe_game_date_dump() {
        Ok(value) => match serde_json::to_string_pretty(&value) {
            Ok(text) => println!("{text}"),
            Err(error) => {
                eprintln!("json encode failed: {error}");
                std::process::exit(2);
            }
        },
        Err(error) => {
            eprintln!("probe failed: {error}");
            std::process::exit(1);
        }
    }
}
