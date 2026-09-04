use std::cell::Cell;
use std::time::Instant;

thread_local! {
    static LOAD_START: Cell<Option<Instant>> = const { Cell::new(None) };
    static COMPACT_PAYLOAD: Cell<bool> = const { Cell::new(false) };
}

fn elapsed_ms() -> u128 {
    LOAD_START
        .with(|start| start.get().map(|instant| instant.elapsed().as_millis()))
        .unwrap_or(0)
}

fn verbose() -> bool {
    LOAD_START.with(|start| start.get().is_some())
}

fn stage_label(stage: &str) -> &str {
    match stage {
        "detecting_fm26" => "Detecting FM26…",
        "validating_active_save" => "Validating active save…",
        "reading_managed_club" => "Reading managed club…",
        "loading_managed_squad" => "Loading managed squad…",
        "building_visibility_index" => "Building scouting-knowledge index…",
        "loading_club_teams" => "Loading club teams…",
        "ready" => "Ready",
        "collect_snapshot" => "Collecting live snapshot…",
        _ => stage,
    }
}

pub fn load_begin(label: &str, compact: bool) {
    LOAD_START.with(|start| start.set(Some(Instant::now())));
    set_compact(compact);
    eprintln!("[fmt] {label} — start (compact={compact})");
}

pub fn load_stage(stage: &str) {
    if !verbose() {
        return;
    }
    eprintln!("[fmt] +{}ms  {stage}", elapsed_ms());
}

/// User-facing load step — matches the FMT app button / status copy.
pub fn load_progress(stage: &str) {
    let label = stage_label(stage);
    if verbose() {
        eprintln!("[fmt] +{}ms  {label}", elapsed_ms());
    } else {
        eprintln!("[fmt] {label}");
    }
}

pub fn load_detail(detail: impl AsRef<str>) {
    if !verbose() {
        return;
    }
    eprintln!("[fmt] +{}ms  {}", elapsed_ms(), detail.as_ref());
}

pub fn load_done(summary: impl AsRef<str>) {
    eprintln!("[fmt] +{}ms  done — {}", elapsed_ms(), summary.as_ref());
    LOAD_START.with(|start| start.set(None));
}

/// Mirror UI-only status lines from the frontend into the dev terminal.
pub fn app_line(message: impl AsRef<str>) {
    eprintln!("[fmt] {}", message.as_ref());
}

#[tauri::command]
pub fn fmt_terminal_log(message: String) {
    app_line(message);
}

pub fn set_compact(compact: bool) {
    COMPACT_PAYLOAD.with(|flag| flag.set(compact));
}

pub fn compact_payload() -> bool {
    COMPACT_PAYLOAD.with(|flag| flag.get())
}
