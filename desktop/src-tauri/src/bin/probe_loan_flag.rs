//! Live RE: dump nested Players-Go-On-Loan bytes for the managed club.
//!
//! ```text
//! cargo run -p fmt --features fm-probe --bin probe-loan-flag
//! ```

fn main() {
    match glassscout_fm26_lib::connector::probe_players_go_on_loan_dump() {
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
