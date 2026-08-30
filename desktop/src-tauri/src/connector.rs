use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::{HashMap, HashSet},
    fs::File,
    io::Read,
    path::Path,
    sync::{Mutex, OnceLock, RwLock},
    time::SystemTime,
};
use tauri::Emitter;

use crate::{
    data::players::{IndexedPlayerRecord, LiveMemoryAnchors, PlayerDatabaseIndex},
        fm26::{
        memory::{ModuleInfo, ProcessReader},
        offsets::{
            executable_sha256_for_versions, find_entity_map, mapping_coverage, EntityMapProfile,
            MappingCoverage,
        },
        parser::{
            classify_player_positions, display_attribute, goalkeeper_rating_from_positions,
            hidden_attribute_map, personality_attribute_map, preferred_foot_label,
            visible_attribute_map,
        },
        permissions::{can_write_memory, READ_ONLY_PROCESS_ACCESS_LABEL},
        process::find_fm26_process,
        roles::{
            decode_role_duty_mask, duty_definition_for_mask,
            role_catalogue_status, role_definition_for_mask, role_supports_slot,
        },
        scanner::{parse_pattern, scan_module, scan_private_memory_for_pointers},
        structs::{FmDate, PLAYER_ATTRIBUTE_NAMES, POSITION_NAMES},
        tactics::tactic_formation_template,
        validator,
    },
    fm_dossier,
};

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ReadPipelineStage {
    key: &'static str,
    label: &'static str,
    state: &'static str,
    detail: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ConnectorStatus {
    process_detected: bool,
    process_id: Option<u32>,
    process_path: Option<String>,
    save_detected: Option<bool>,
    memory_access: &'static str,
    parser_status: &'static str,
    state: &'static str,
    players_loaded: u32,
    managed_squad_players: u32,
    club_employees: u32,
    database_players_indexed: u32,
    background_players_indexed: u32,
    visible_players_loaded: u32,
    fully_scouted_players: u32,
    partial_scout_reports: u32,
    database_index_status: &'static str,
    database_scope: &'static str,
    clubs_loaded: u32,
    last_sync: Option<String>,
    bytes_read: usize,
    executable_header_valid: bool,
    can_write_memory: bool,
    game_build: Option<String>,
    product_version: Option<String>,
    executable_sha256: Option<String>,
    architecture: Option<String>,
    module_base: Option<String>,
    entity_map_status: &'static str,
    entity_map_profile_id: Option<String>,
    mapping_schema_version: u32,
    mapping_coverage: Vec<MappingCoverage>,
    pointer_validation: &'static str,
    handle_access_flags: &'static str,
    entity_root: Option<String>,
    save_pointer: Option<String>,
    managed_club_pointer: Option<String>,
    player_collection_pointer: Option<String>,
    live_memory_tactic_read: &'static str,
    tactic_manager_pointer: Option<String>,
    failure_stage: Option<String>,
    last_successful_read: Option<String>,
    windows_error_code: Option<u32>,
    read_pipeline: Vec<ReadPipelineStage>,
    message: String,
    warnings: Vec<String>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ConnectorSnapshot {
    status: ConnectorStatus,
    managed_club_id: Option<String>,
    manager_name: Option<String>,
    season: Option<String>,
    clubs: Vec<Value>,
    club_teams: Vec<Value>,
    players: Vec<Value>,
    tactic: Option<Value>,
    tactic_source: &'static str,
    data_error: Option<String>,
    data_source: &'static str,
    data_warnings: Vec<String>,
}

#[derive(Clone, Default)]
struct ExecutableIdentity {
    file_version: Option<String>,
    product_version: Option<String>,
    sha256: Option<String>,
    architecture: Option<String>,
}

struct CachedExecutableIdentity {
    path: String,
    len: u64,
    modified: SystemTime,
    identity: ExecutableIdentity,
}

fn identity_cache() -> &'static Mutex<Option<CachedExecutableIdentity>> {
    static CACHE: OnceLock<Mutex<Option<CachedExecutableIdentity>>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(None))
}

#[derive(Clone, Copy)]
struct CachedManagerSignature {
    process_id: u32,
    module_base: u64,
    signature_address: u64,
}

fn manager_signature_cache() -> &'static Mutex<Option<CachedManagerSignature>> {
    static CACHE: OnceLock<Mutex<Option<CachedManagerSignature>>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(None))
}

#[derive(Default)]
struct ExtractionDiagnostics {
    entity_root: Option<u64>,
    save_pointer: Option<u64>,
    managed_club_pointer: Option<u64>,
    player_collection_pointer: Option<u64>,
    last_successful_read: Option<String>,
}

struct LiveData {
    managed_club_id: String,
    manager_name: String,
    season: Option<String>,
    clubs: Vec<Value>,
    club_teams: Vec<Value>,
    players: Vec<Value>,
    tactic: Option<Value>,
    database_players_indexed: u32,
    background_players_indexed: u32,
    database_index_status: &'static str,
    database_scope: &'static str,
    database_index_error: Option<String>,
    warnings: Vec<String>,
    tactic_manager_pointer: Option<u64>,
    club_employees: u32,
}

static PLAYER_DATABASE_INDEX: OnceLock<RwLock<PlayerDatabaseIndex>> = OnceLock::new();

struct ExtractionFailure {
    stage: &'static str,
    message: String,
    windows_error_code: Option<u32>,
}

impl ExtractionFailure {
    fn new(stage: &'static str, message: impl Into<String>) -> Self {
        Self {
            stage,
            message: message.into(),
            windows_error_code: None,
        }
    }
}

#[tauri::command]
pub fn connector_status() -> ConnectorStatus {
    collect_snapshot(false, None).status
}

#[tauri::command]
pub fn connector_snapshot() -> ConnectorSnapshot {
    collect_snapshot(false, None)
}

#[tauri::command]
pub async fn load_active_save(app: tauri::AppHandle) -> ConnectorSnapshot {
    let app_emit = app.clone();
    match tauri::async_runtime::spawn_blocking(move || {
        crate::fmt_log::load_begin("load_active_save", true);
        let progress = |stage: &'static str| {
            crate::fmt_log::load_progress(stage);
            let _ = app_emit.emit("fmt-load-progress", stage);
        };
        // Fast path: managed squad only — no full-save memory scan or dossier merge.
        collect_snapshot(false, Some(&progress))
    })
    .await
    {
        Ok(snapshot) => snapshot,
        Err(error) => {
            crate::fmt_log::load_detail(format!("load worker panicked: {error}"));
            let mut status = empty_status();
            status.message = "FMT load failed unexpectedly.".to_string();
            empty_snapshot(status.clone(), status.message)
        }
    }
}

/// Live RAM probe: managed club affiliate graph (forward/back club links + affiliate teams).
#[tauri::command]
pub fn debug_scan_club_affiliates() -> Result<Value, String> {
    #[cfg(not(target_os = "windows"))]
    {
        return Err("Club affiliate scan requires the Windows FM26 connector.".to_string());
    }
    #[cfg(target_os = "windows")]
    debug_scan_club_affiliates_impl()
}

/// Live RAM probe: club-linked teams with roster player UID/name samples.
#[tauri::command]
pub fn debug_scan_club_teams() -> Result<Value, String> {
    #[cfg(not(target_os = "windows"))]
    {
        return Err("Club team scan requires the Windows FM26 connector.".to_string());
    }
    #[cfg(target_os = "windows")]
    debug_scan_club_teams_impl()
}

/// Background pass: heap-scan club satellite teams (U19 etc.) after the fast first load.
#[tauri::command]
pub async fn load_club_satellite_squads() -> Result<Value, String> {
    #[cfg(not(target_os = "windows"))]
    {
        return Err("Club satellite squad load requires the Windows FM26 connector.".to_string());
    }
    #[cfg(target_os = "windows")]
    {
        tauri::async_runtime::spawn_blocking(load_club_satellite_squads_impl)
            .await
            .map_err(|error| format!("Satellite squad worker failed: {error}"))
            .and_then(|result| result)
    }
}

/// Compare person/player bytes between database and high-UID managed squad samples.
#[tauri::command]
pub fn debug_probe_player_origin() -> Result<Value, String> {
    #[cfg(not(target_os = "windows"))]
    {
        return Err("Player origin probe requires the Windows FM26 connector.".to_string());
    }
    #[cfg(target_os = "windows")]
    debug_probe_player_origin_impl()
}

#[cfg(target_os = "windows")]
fn load_club_satellite_squads_impl() -> Result<Value, String> {
    let Some((process_id, _)) = find_fm26_process() else {
        return Err("FM26 process not found.".to_string());
    };
    let mut reader = ProcessReader::open(process_id)
        .map_err(|code| format!("Could not open FM26 read-only handle (Windows error {code})."))?;
    let identity = reader
        .process_path()
        .as_deref()
        .map(read_executable_identity)
        .unwrap_or_default();
    let Some(profile) = find_entity_map(
        identity.file_version.as_deref(),
        identity.product_version.as_deref(),
        identity.sha256.as_deref(),
        identity.architecture.as_deref(),
    ) else {
        return Err("FM26 build is not supported.".to_string());
    };
    let Some(module) = reader.module(&profile.module) else {
        return Err("The FM26 game module was not available.".to_string());
    };
    let mut diagnostics = ExtractionDiagnostics::default();
    let (selected, _) =
        resolve_active_human_manager(&mut reader, module, profile, process_id, &mut diagnostics)
            .map_err(|failure| failure.message)?;
    let club_id = selected.club_uid.to_string();
    let mut squad_game_date = None;
    if let (Some(start), Some(end)) = (
        reader
            .read_pointer(selected.team + profile.constants.team_players_start_offset)
            .filter(|value| *value != 0),
        reader
            .read_pointer(selected.team + profile.constants.team_players_end_offset)
            .filter(|value| *value != 0),
    ) {
        let count = ((end.saturating_sub(start)) / 8) as usize;
        for index in 0..count {
            let Some(raw_player) = reader
                .read_pointer(start + (index as u64 * 8))
                .filter(|value| *value != 0)
            else {
                continue;
            };
            if let Some(date) =
                read_fm_date(&mut reader, raw_player + profile.constants.player_current_date_offset)
            {
                squad_game_date = Some(date);
                break;
            }
        }
    }
    let seeds = HashSet::from([selected.team]);
    let discovered = discover_managed_club_teams(
        &mut reader,
        module,
        profile,
        selected.club,
        selected.club_uid,
        selected.team,
        &seeds,
        true,
    );
    let club_teams = club_teams_json(&discovered, selected.team);
    let mut players = Vec::new();
    let mut managed_player_ids = HashSet::new();
    let mut managed_index_records = Vec::new();
    let mut player_vtable = None;
    let mut skipped_squad_slots = 0u32;
    let mut skipped_squad_details = Vec::new();
    let mut name_fallback_details = Vec::new();
    let mut promoted = 0usize;
    for entry in discovered {
        if entry.team == selected.team || entry.squad_unit == "firstTeam" {
            continue;
        }
        promoted += load_team_roster(
            &mut reader,
            module,
            profile,
            entry.team,
            &entry.name,
            entry.squad_unit,
            entry.team_uid,
            &club_id,
            selected.club_uid,
            squad_game_date,
            &mut managed_player_ids,
            &mut managed_index_records,
            &mut players,
            &mut skipped_squad_slots,
            &mut skipped_squad_details,
            &mut name_fallback_details,
            &mut player_vtable,
        );
    }
    Ok(json!({
        "clubTeams": club_teams,
        "players": players,
        "promotedRosterPlayers": promoted,
        "skippedSlots": skipped_squad_slots,
        "bytesRead": reader.bytes_read,
    }))
}

#[cfg(target_os = "windows")]
fn debug_probe_player_origin_impl() -> Result<Value, String> {
    use crate::fm26::player_origin::probe_player_origin_fields;

    let Some((process_id, _)) = find_fm26_process() else {
        return Err("FM26 process not found.".to_string());
    };
    let mut reader = ProcessReader::open(process_id)
        .map_err(|code| format!("Could not open FM26 read-only handle (Windows error {code})."))?;
    let identity = reader
        .process_path()
        .as_deref()
        .map(read_executable_identity)
        .unwrap_or_default();
    let Some(profile) = find_entity_map(
        identity.file_version.as_deref(),
        identity.product_version.as_deref(),
        identity.sha256.as_deref(),
        identity.architecture.as_deref(),
    ) else {
        return Err("FM26 build is not supported.".to_string());
    };
    let Some(module) = reader.module(&profile.module) else {
        return Err("The FM26 game module was not available.".to_string());
    };
    let mut diagnostics = ExtractionDiagnostics::default();
    let (selected, _) =
        resolve_active_human_manager(&mut reader, module, profile, process_id, &mut diagnostics)
            .map_err(|failure| failure.message)?;
    let players_start = reader
        .read_pointer(selected.team + profile.constants.team_players_start_offset)
        .ok_or_else(|| "Managed squad collection was not readable.".to_string())?;
    let players_end = reader
        .read_pointer(selected.team + profile.constants.team_players_end_offset)
        .ok_or_else(|| "Managed squad collection end was not readable.".to_string())?;
    let player_count = ((players_end.saturating_sub(players_start)) / 8) as usize;
    let player_vtable = module.base + profile.constants.team_vtable_rva;
    let _ = player_vtable;
    let mut samples = Vec::new();
    for index in 0..player_count.min(80) {
        let Some(raw_player) = reader
            .read_pointer(players_start + (index as u64 * 8))
            .filter(|value| *value != 0)
        else {
            continue;
        };
        let Some(person) = reader
            .read_pointer(raw_player + profile.constants.player_person_offset)
            .filter(|value| *value != 0)
        else {
            continue;
        };
        let Some(uid) = reader
            .read_u32(person + profile.constants.entity_uid_offset)
            .filter(|uid| is_plausible_fm_unique_id(*uid))
        else {
            continue;
        };
        samples.push((raw_player, uid, person, 0));
    }
    Ok(probe_player_origin_fields(&mut reader, profile, &samples))
}

#[tauri::command]
pub fn search_indexed_players(query: String) -> Vec<Value> {
    let dossier_results = fm_dossier::search_players(&query, 500);
    if !dossier_results.is_empty() {
        return dossier_results;
    }
    let normalized = query.trim().to_lowercase();
    let Some(index) = PLAYER_DATABASE_INDEX.get() else {
        return Vec::new();
    };
    let Ok(index) = index.read() else {
        return Vec::new();
    };
    let _identity = (index.process_id, index.save_pointer);
    let mut results: Vec<Value> = index
        .records
        .values()
        .filter(|record| {
            normalized.is_empty()
                || record.name.to_lowercase().contains(&normalized)
                || record
                    .positions
                    .iter()
                    .any(|position| position.to_lowercase().contains(&normalized))
        })
        .map(indexed_player_json)
        .collect();
    results.sort_by(|left, right| {
        left["name"]
            .as_str()
            .unwrap_or_default()
            .cmp(right["name"].as_str().unwrap_or_default())
    });
    results.truncate(500);
    results
}

#[tauri::command]
pub fn indexed_players_by_ids(player_ids: Vec<String>) -> Vec<Value> {
    let dossier_results = fm_dossier::players_by_ids(&player_ids);
    if !dossier_results.is_empty() {
        return dossier_results;
    }
    let Some(index) = PLAYER_DATABASE_INDEX.get() else {
        return Vec::new();
    };
    let Ok(index) = index.read() else {
        return Vec::new();
    };
    player_ids
        .iter()
        .filter_map(|id| index.records.get(id))
        .map(indexed_player_json)
        .collect()
}

#[tauri::command]
pub fn indexed_player_profile(player_id: String) -> Option<Value> {
    fm_dossier::player_profile(&player_id)
}

fn indexed_player_json(record: &IndexedPlayerRecord) -> Value {
    json!({
        "id": record.id,
        "name": record.name,
        "positions": record.positions,
        "managedSquad": record.managed_squad,
        "visibility": if record.visibility_safe { "known" } else { "unknown" },
        "scoutKnowledge": if record.visibility_safe { "fully_known" } else { "unknown" },
        "scoutConfidence": if record.visibility_safe { 100 } else { 0 }
    })
}

fn empty_status() -> ConnectorStatus {
    ConnectorStatus {
        process_detected: false,
        process_id: None,
        process_path: None,
        save_detected: None,
        memory_access: "not_checked",
        parser_status: "unverified",
        state: "process_not_found",
        players_loaded: 0,
        managed_squad_players: 0,
        club_employees: 0,
        database_players_indexed: 0,
        background_players_indexed: 0,
        visible_players_loaded: 0,
        fully_scouted_players: 0,
        partial_scout_reports: 0,
        database_index_status: "not_run",
        database_scope: "none",
        clubs_loaded: 0,
        last_sync: None,
        bytes_read: 0,
        executable_header_valid: false,
        can_write_memory: can_write_memory(),
        game_build: None,
        product_version: None,
        executable_sha256: None,
        architecture: None,
        module_base: None,
        entity_map_status: "not_checked",
        entity_map_profile_id: None,
        mapping_schema_version: 2,
        mapping_coverage: Vec::new(),
        pointer_validation: "not_run",
        handle_access_flags: READ_ONLY_PROCESS_ACCESS_LABEL,
        entity_root: None,
        save_pointer: None,
        managed_club_pointer: None,
        player_collection_pointer: None,
        live_memory_tactic_read: "not_run",
        tactic_manager_pointer: None,
        failure_stage: None,
        last_successful_read: None,
        windows_error_code: None,
        read_pipeline: Vec::new(),
        message: "FM26 is not running. Open FM26 and load your save to begin.".to_string(),
        warnings: Vec::new(),
    }
}

fn empty_snapshot(mut status: ConnectorStatus, error: String) -> ConnectorSnapshot {
    status.read_pipeline = build_read_pipeline(&status);
    ConnectorSnapshot {
        status,
        managed_club_id: None,
        manager_name: None,
        season: None,
        clubs: Vec::new(),
        club_teams: Vec::new(),
        players: Vec::new(),
        tactic: None,
        tactic_source: "none",
        data_error: Some(error),
        data_source: "none",
        data_warnings: Vec::new(),
    }
}

fn pipeline_stage(
    key: &'static str,
    label: &'static str,
    state: &'static str,
    detail: impl Into<String>,
) -> ReadPipelineStage {
    ReadPipelineStage {
        key,
        label,
        state,
        detail: detail.into(),
    }
}

fn build_read_pipeline(status: &ConnectorStatus) -> Vec<ReadPipelineStage> {
    let mut stages = Vec::new();

    stages.push(pipeline_stage(
        "process",
        "FM26 process",
        if status.process_detected {
            "passed"
        } else {
            "blocked"
        },
        status
            .process_id
            .map(|pid| format!("Detected fm.exe process {pid}."))
            .unwrap_or_else(|| "FM26 is not running or was not found by process scan.".to_string()),
    ));

    stages.push(pipeline_stage(
        "read_only_access",
        "Read-only memory access",
        match status.memory_access {
            "read_only_handle_open" => "passed",
            "denied" => "blocked",
            _ => "pending",
        },
        match status.memory_access {
            "read_only_handle_open" => format!(
                "Handle opened with read-only flags: {}.",
                status.handle_access_flags
            ),
            "denied" => "Windows denied the read-only process handle.".to_string(),
            _ => "Read-only handle has not been opened yet.".to_string(),
        },
    ));

    stages.push(pipeline_stage(
        "exact_build",
        "Exact FM26 build map",
        if status.entity_map_status == "matched" {
            "passed"
        } else if status.process_detected {
            "blocked"
        } else {
            "pending"
        },
        status
            .entity_map_profile_id
            .as_ref()
            .map(|id| format!("Matched entity-map profile {id}."))
            .unwrap_or_else(|| {
                format!(
                    "No safe entity map matched build {} / {}.",
                    status.game_build.as_deref().unwrap_or("unknown"),
                    status.product_version.as_deref().unwrap_or("unknown")
                )
            }),
    ));

    stages.push(pipeline_stage(
        "module_validation",
        "Game module validation",
        if status.executable_header_valid {
            "passed"
        } else if status.entity_map_status == "matched" {
            "blocked"
        } else {
            "pending"
        },
        status
            .module_base
            .as_ref()
            .map(|base| {
                format!(
                    "Validated FM26 module at {base}; {} bytes read.",
                    status.bytes_read
                )
            })
            .unwrap_or_else(|| "FM26 module base was not available.".to_string()),
    ));

    stages.push(pipeline_stage(
        "active_save",
        "Active save and manager",
        if status.save_detected == Some(true) || status.save_pointer.is_some() {
            "passed"
        } else if status.failure_stage.is_some() {
            "blocked"
        } else {
            "pending"
        },
        status
            .save_pointer
            .as_ref()
            .map(|pointer| format!("Active human manager pointer resolved at {pointer}."))
            .unwrap_or_else(|| {
                "Active save / human manager pointer has not been resolved.".to_string()
            }),
    ));

    stages.push(pipeline_stage(
        "managed_club",
        "Managed club",
        if status.managed_club_pointer.is_some() {
            "passed"
        } else if status.failure_stage.as_deref() == Some("managed_club") {
            "blocked"
        } else {
            "pending"
        },
        status
            .managed_club_pointer
            .as_ref()
            .map(|pointer| format!("Managed club object validated at {pointer}."))
            .unwrap_or_else(|| "Managed club object is not validated yet.".to_string()),
    ));

    stages.push(pipeline_stage(
        "managed_squad",
        "Managed squad memory",
        if status.managed_squad_players > 0 {
            "passed"
        } else if status.failure_stage.as_deref() == Some("player_collection") {
            "blocked"
        } else {
            "pending"
        },
        if status.managed_squad_players > 0 {
            format!(
                "{} squad players read from FM26 memory; {} visible player profiles loaded.",
                status.managed_squad_players, status.visible_players_loaded
            )
        } else {
            "Managed squad collection has not produced readable players yet.".to_string()
        },
    ));

    stages.push(pipeline_stage(
        "full_player_index",
        "Player database index",
        match status.database_index_status {
            "ready" => "passed",
            "partial" => "warning",
            "failed" => "failed",
            _ => "pending",
        },
        format!(
            "{} indexed records; {} background records gated by scout knowledge; scope {}.",
            status.database_players_indexed,
            status.background_players_indexed,
            status.database_scope
        ),
    ));

    stages.push(pipeline_stage(
        "live_tactic",
        "Live tactic memory",
        match status.live_memory_tactic_read {
            "ready" => "passed",
            "object_detected_unmapped" => "warning",
            "object_not_found" => "warning",
            _ => "pending",
        },
        match status.live_memory_tactic_read {
            "ready" => "Active tactic manager, formation and selected XI validated.".to_string(),
            "object_detected_unmapped" => {
                "Tactic manager found, but selected-slot block did not validate for this read."
                    .to_string()
            }
            "object_not_found" => {
                "No active tactic manager object was found in the current read.".to_string()
            }
            _ => "Tactic memory read has not run yet.".to_string(),
        },
    ));

    let validated: u32 = status
        .mapping_coverage
        .iter()
        .map(|item| item.validated)
        .sum();
    let candidate: u32 = status
        .mapping_coverage
        .iter()
        .map(|item| item.candidate)
        .sum();
    let unmapped: u32 = status
        .mapping_coverage
        .iter()
        .map(|item| item.unmapped)
        .sum();
    stages.push(pipeline_stage(
        "field_mapping",
        "Field mapping coverage",
        if status.entity_map_status != "matched" {
            "pending"
        } else if unmapped > 0 || candidate > 0 {
            "warning"
        } else {
            "passed"
        },
        format!(
            "{validated} validated fields, {candidate} candidate fields and {unmapped} unmapped fields for this exact build."
        ),
    ));

    stages
}

#[cfg(target_os = "windows")]
fn collect_snapshot(
    include_database_index: bool,
    progress: Option<&dyn Fn(&'static str)>,
) -> ConnectorSnapshot {
    let compact = !include_database_index;
    crate::fmt_log::set_compact(compact);
    if progress.is_some() {
        crate::fmt_log::load_stage("collect_snapshot");
    }
    if let Some(progress) = progress {
        progress("detecting_fm26");
    }
    let Some((process_id, _)) = find_fm26_process() else {
        crate::fmt_log::load_detail("FM26 process not found");
        let status = empty_status();
        return empty_snapshot(status.clone(), status.message);
    };
    crate::fmt_log::load_detail(format!("FM26 pid={process_id}"));

    let mut status = empty_status();
    status.process_detected = true;
    status.process_id = Some(process_id);
    if let Some(progress) = progress {
        progress("validating_active_save");
    }

    let mut reader = match ProcessReader::open(process_id) {
        Ok(reader) => reader,
        Err(code) => {
            crate::fmt_log::load_detail(format!("OpenProcess denied (win32 {code})"));
            status.state = "access_denied";
            status.memory_access = "denied";
            status.windows_error_code = Some(code);
            status.failure_stage = Some("open_read_only_process".to_string());
            status.message =
                "FM26 is running, but FMT could not open its read-only connection."
                    .to_string();
            return empty_snapshot(status.clone(), status.message);
        }
    };
    status.memory_access = "read_only_handle_open";
    status.process_path = reader.process_path();

    crate::fmt_log::load_detail("reading FM executable identity (version match; hash only if needed)");
    let identity = status
        .process_path
        .as_deref()
        .map(read_executable_identity)
        .unwrap_or_default();
    status.game_build = identity.file_version.clone();
    status.product_version = identity.product_version.clone();
    status.executable_sha256 = identity.sha256.clone();
    status.architecture = identity.architecture.clone();

    let Some(profile) = find_entity_map(
        identity.file_version.as_deref(),
        identity.product_version.as_deref(),
        identity.sha256.as_deref(),
        identity.architecture.as_deref(),
    ) else {
        crate::fmt_log::load_detail(format!(
            "entity map miss build={} product={} arch={:?} sha={:?}",
            identity.file_version.as_deref().unwrap_or("?"),
            identity.product_version.as_deref().unwrap_or("?"),
            identity.architecture,
            identity.sha256.as_deref().map(|s| &s[..16.min(s.len())])
        ));
        status.state = "parser_unverified";
        status.entity_map_status = "missing";
        status.failure_stage = Some("exact_build_match".to_string());
        status.last_successful_read = Some("read_executable_identity".to_string());
        status.bytes_read = reader.bytes_read;
        status.message = format!(
            "FM26 build {} is not supported safely yet. No game data was shown.",
            identity.file_version.as_deref().unwrap_or("unknown")
        );
        return empty_snapshot(status.clone(), status.message);
    };
    status.entity_map_status = "matched";
    status.entity_map_profile_id = Some(profile.id.clone());
    status.mapping_coverage = if include_database_index {
        mapping_coverage(profile)
    } else {
        Vec::new()
    };
    crate::fmt_log::load_detail(format!("entity map matched profile={}", profile.id));

    let Some(module) = reader.module(&profile.module) else {
        status.state = "parser_unverified";
        status.pointer_validation = "failed";
        status.failure_stage = Some("locate_game_module".to_string());
        status.last_successful_read = Some("match_exact_build".to_string());
        status.windows_error_code = reader.last_error;
        status.bytes_read = reader.bytes_read;
        status.message =
            "The FM26 game module was not available. No game data was shown.".to_string();
        return empty_snapshot(status.clone(), status.message);
    };
    status.module_base = Some(hex_address(module.base));
    let header = reader.read_bytes(module.base, 2);
    status.executable_header_valid = header.as_deref() == Some(b"MZ");
    if !status.executable_header_valid {
        status.state = "parser_unverified";
        status.pointer_validation = "failed";
        status.failure_stage = Some("validate_game_module".to_string());
        status.last_successful_read = Some("locate_game_module".to_string());
        status.bytes_read = reader.bytes_read;
        status.message =
            "The FM26 game module could not be validated. No game data was shown.".to_string();
        return empty_snapshot(status.clone(), status.message);
    }

    if let Some(progress) = progress {
        progress("reading_managed_club");
    }
    let mut diagnostics = ExtractionDiagnostics::default();
    let extracted = extract_live_data(
        &mut reader,
        module,
        profile,
        &mut diagnostics,
        process_id,
        include_database_index,
        progress,
    );
    status.bytes_read = reader.bytes_read;
    status.entity_root = diagnostics.entity_root.map(hex_address);
    status.save_pointer = diagnostics.save_pointer.map(hex_address);
    status.managed_club_pointer = diagnostics.managed_club_pointer.map(hex_address);
    status.player_collection_pointer = diagnostics.player_collection_pointer.map(hex_address);
    status.last_successful_read = diagnostics.last_successful_read;

    match extracted {
        Ok(data) => {
            if let Some(progress) = progress {
                progress("ready");
            }
            status.save_detected = Some(true);
            status.parser_status = "ready";
            status.state = "connected";
            status.players_loaded = data.players.len() as u32;
            status.managed_squad_players = data.players.len() as u32;
            status.club_employees = data.club_employees;
            status.database_players_indexed = data.database_players_indexed;
            status.background_players_indexed = data.background_players_indexed;
            status.visible_players_loaded = data.players.len() as u32;
            status.fully_scouted_players = data.players.len() as u32;
            status.partial_scout_reports = 0;
            status.database_index_status = data.database_index_status;
            status.database_scope = data.database_scope;
            status.clubs_loaded = data.clubs.len() as u32;
            status.pointer_validation = "passed";
            status.live_memory_tactic_read = if data.tactic.is_some() {
                "ready"
            } else if data.tactic_manager_pointer.is_some() {
                "object_detected_unmapped"
            } else {
                "object_not_found"
            };
            status.tactic_manager_pointer = data.tactic_manager_pointer.map(hex_address);
            status.last_sync = Some(unix_milliseconds());
            status.message = format!(
                "Live FM26 read connected: active club {}, {} managed-squad players from memory, {} indexed player records. See the data pipeline for mapped and unmapped fields.",
                data.clubs
                    .first()
                    .and_then(|club| club.get("name"))
                    .and_then(Value::as_str)
                    .unwrap_or("the managed club"),
                data.players.len(),
                data.database_players_indexed
            );
            status.warnings = data.warnings.clone();
            status.read_pipeline = if include_database_index {
                build_read_pipeline(&status)
            } else {
                Vec::new()
            };
            let summary = format!(
                "{} players, {} bytes read, scope={}",
                data.players.len(),
                reader.bytes_read,
                data.database_scope
            );
            crate::fmt_log::load_done(summary);
            ConnectorSnapshot {
                status,
                managed_club_id: Some(data.managed_club_id),
                manager_name: Some(data.manager_name),
                season: data.season,
                clubs: data.clubs,
                club_teams: data.club_teams,
                players: data.players,
                tactic_source: if data.tactic.is_some() {
                    "live-memory"
                } else {
                    "none"
                },
                tactic: data.tactic,
                data_error: data.database_index_error,
                data_source: "live-memory",
                data_warnings: data.warnings,
            }
        }
        Err(failure) => {
            status.save_detected = Some(false);
            status.parser_status = "error";
            status.state = "parser_unverified";
            status.pointer_validation = "failed";
            status.failure_stage = Some(failure.stage.to_string());
            status.windows_error_code = failure.windows_error_code.or(reader.last_error);
            status.message = failure.message;
            empty_snapshot(status.clone(), status.message)
        }
    }
}

#[cfg(not(target_os = "windows"))]
fn collect_snapshot(
    _include_database_index: bool,
    _progress: Option<&dyn Fn(&'static str)>,
) -> ConnectorSnapshot {
    let mut status = empty_status();
    status.message = "The live FM26 connector requires the installed Windows app.".to_string();
    empty_snapshot(status.clone(), status.message)
}

#[cfg(target_os = "windows")]
struct ResolvedHumanManager {
    human: u64,
    manager_name: String,
    team: u64,
    club: u64,
    club_uid: u32,
    club_name: String,
    squad_len: u64,
}

/// Validate one human-manager pointer from the registry vector.
/// Dormant / holiday entries typically fail name, contract, team, or club checks.
#[cfg(target_os = "windows")]
fn try_resolve_human_manager(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    human: u64,
) -> Option<ResolvedHumanManager> {
    let person = human + profile.constants.human_person_offset;
    let first_name = read_name_field(reader, person + profile.constants.person_first_name_offset);
    let second_name = read_name_field(reader, person + profile.constants.person_second_name_offset);
    let common_name = read_name_field(reader, person + profile.constants.person_common_name_offset);
    let manager_name = display_name(first_name, second_name, common_name)?;

    let contract = reader
        .read_pointer(person + profile.constants.person_contract_offset)
        .filter(|value| *value != 0)?;
    let team = reader
        .read_pointer(contract + profile.constants.contract_team_offset)
        .filter(|value| *value != 0)?;
    validator::validate_vtable(reader, team, module.base + profile.constants.team_vtable_rva)
        .ok()?;
    let club = reader
        .read_pointer(team + profile.constants.team_club_offset)
        .filter(|value| *value != 0)?;
    validator::validate_vtable(reader, club, module.base + profile.constants.club_vtable_rva)
        .ok()?;

    let team_uid = reader
        .read_u32(team + profile.constants.entity_uid_offset)
        .filter(|uid| *uid > 0)?;
    let club_uid = reader
        .read_u32(club + profile.constants.entity_uid_offset)
        .filter(|uid| *uid == team_uid)?;
    let club_name_pointer = reader
        .read_pointer(club + profile.constants.club_name_offset)
        .filter(|value| *value != 0)?;
    let club_name = reader.read_length_prefixed_string(club_name_pointer)?;

    // Require a plausible squad so empty/dormant shells lose to the playable career.
    let players_start = reader.read_pointer(team + profile.constants.team_players_start_offset)?;
    let players_end = reader.read_pointer(team + profile.constants.team_players_end_offset)?;
    if players_end <= players_start
        || (players_end - players_start) % 8 != 0
        || !(1..=200).contains(&((players_end - players_start) / 8))
    {
        return None;
    }
    let squad_len = (players_end - players_start) / 8;

    Some(ResolvedHumanManager {
        human,
        manager_name,
        team,
        club,
        club_uid,
        club_name,
        squad_len,
    })
}

/// Resolve the active human manager from the FM26 registry (largest squad wins).
#[cfg(target_os = "windows")]
fn resolve_active_human_manager(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    process_id: u32,
    diagnostics: &mut ExtractionDiagnostics,
) -> Result<(ResolvedHumanManager, Option<String>), ExtractionFailure> {
    let signature = profile
        .signatures
        .iter()
        .find(|item| item.name == "human_manager_registry")
        .ok_or_else(|| {
            ExtractionFailure::new("manager_signature", "The exact build map is incomplete.")
        })?;
    let pattern = parse_pattern(&signature.pattern).map_err(|_| {
        ExtractionFailure::new("entity_map", "The embedded signature pattern is invalid.")
    })?;
    let signature_address = {
        let cached = manager_signature_cache()
            .lock()
            .ok()
            .and_then(|guard| {
                guard.as_ref().copied().filter(|hit| {
                    hit.process_id == process_id && hit.module_base == module.base
                })
            })
            .map(|hit| hit.signature_address);
        if let Some(address) = cached {
            address
        } else {
            let hits = scan_module(reader, module, &pattern)
                .map_err(|error| ExtractionFailure::new("manager_signature", error.to_string()))?;
            if hits.len() != 1 {
                return Err(ExtractionFailure::new(
                    "manager_signature",
                    format!(
                        "The FM26 manager root did not validate uniquely ({} matches).",
                        hits.len()
                    ),
                ));
            }
            let address = hits[0];
            if let Ok(mut guard) = manager_signature_cache().lock() {
                *guard = Some(CachedManagerSignature {
                    process_id,
                    module_base: module.base,
                    signature_address: address,
                });
            }
            address
        }
    };
    let displacement = reader.read_i32(signature_address + 3).ok_or_else(|| {
        ExtractionFailure::new(
            "manager_signature",
            "The FM26 manager signature could not be read.",
        )
    })?;
    let registry_slot = (signature_address + 7).wrapping_add_signed(displacement as i64);
    let registry = reader
        .read_pointer(registry_slot)
        .filter(|value| *value != 0)
        .ok_or_else(|| {
            ExtractionFailure::new(
                "manager_registry",
                "No active FM26 manager registry was available.",
            )
        })?;
    diagnostics.entity_root = Some(registry);

    let vector_start = reader
        .read_pointer(registry + profile.constants.manager_registry_vector_offset)
        .ok_or_else(|| {
            ExtractionFailure::new(
                "manager_registry",
                "The active manager collection could not be read.",
            )
        })?;
    let vector_end = reader
        .read_pointer(registry + profile.constants.manager_registry_vector_offset + 8)
        .ok_or_else(|| {
            ExtractionFailure::new(
                "manager_registry",
                "The active manager collection end could not be read.",
            )
        })?;
    let registry_bytes = vector_end.saturating_sub(vector_start);
    let registry_count = registry_bytes / 8;
    if vector_end <= vector_start || registry_bytes % 8 != 0 || !(1..=32).contains(&registry_count)
    {
        return Err(ExtractionFailure::new(
            "manager_registry",
            format!(
                "The FM26 manager registry size was invalid ({registry_bytes} bytes)."
            ),
        ));
    }

    let mut resolved = Vec::new();
    for index in 0..registry_count {
        let Some(human) = reader
            .read_pointer(vector_start + index * 8)
            .filter(|value| *value != 0)
        else {
            continue;
        };
        if let Some(candidate) = try_resolve_human_manager(reader, module, profile, human) {
            resolved.push(candidate);
        }
    }
    if resolved.is_empty() {
        return Err(ExtractionFailure::new(
            "manager_registry",
            "No playable human manager validated in the registry.".to_string(),
        ));
    }
    let manager_pick_warning = if resolved.len() == 1 {
        None
    } else {
        let candidates = resolved
            .iter()
            .map(|item| {
                format!(
                    "{} @ {} ({} squad)",
                    item.manager_name, item.club_name, item.squad_len
                )
            })
            .collect::<Vec<_>>()
            .join("; ");
        let best_index = resolved
            .iter()
            .enumerate()
            .max_by_key(|(_, item)| item.squad_len)
            .map(|(index, _)| index)
            .unwrap_or(0);
        Some(format!(
            "Multiple managers [{candidates}]; selected {} @ {}.",
            resolved[best_index].manager_name, resolved[best_index].club_name
        ))
    };
    let best_index = resolved
        .iter()
        .enumerate()
        .max_by_key(|(_, item)| item.squad_len)
        .map(|(index, _)| index)
        .unwrap_or(0);
    Ok((resolved.swap_remove(best_index), manager_pick_warning))
}

#[cfg(target_os = "windows")]
fn debug_scan_club_teams_impl() -> Result<Value, String> {
    let Some((process_id, _)) = find_fm26_process() else {
        return Err("FM26 process not found.".to_string());
    };
    let mut reader = ProcessReader::open(process_id)
        .map_err(|code| format!("Could not open FM26 read-only handle (Windows error {code})."))?;
    let identity = reader
        .process_path()
        .as_deref()
        .map(read_executable_identity)
        .unwrap_or_default();
    let Some(profile) = find_entity_map(
        identity.file_version.as_deref(),
        identity.product_version.as_deref(),
        identity.sha256.as_deref(),
        identity.architecture.as_deref(),
    ) else {
        return Err("FM26 build is not supported.".to_string());
    };
    let Some(module) = reader.module(&profile.module) else {
        return Err("The FM26 game module was not available.".to_string());
    };
    let mut diagnostics = ExtractionDiagnostics::default();
    let (selected, manager_pick_warning) =
        resolve_active_human_manager(&mut reader, module, profile, process_id, &mut diagnostics)
            .map_err(|failure| failure.message)?;
    let seeds = HashSet::from([selected.team]);
    let discovered = discover_managed_club_teams(
        &mut reader,
        module,
        profile,
        selected.club,
        selected.club_uid,
        selected.team,
        &seeds,
        true,
    );
    let teams: Vec<Value> = discovered
        .into_iter()
        .map(|entry| {
            json!({
                "teamPointer": hex_address(entry.team),
                "teamUid": entry.team_uid,
                "label": club_team_label(&entry.name, entry.team_uid),
                "nameAtClubNameOffset": entry.name,
                "rosterLen": entry.roster_len,
                "classifiedUnit": entry.squad_unit,
                "isManagerFirstTeam": entry.team == selected.team,
                "rosterPlayers": probe_team_roster_identities(&mut reader, profile, entry.team),
            })
        })
        .collect();
    Ok(json!({
        "managedClubUid": selected.club_uid,
        "managedClubName": selected.club_name,
        "managerName": selected.manager_name,
        "managerPickWarning": manager_pick_warning,
        "bytesRead": reader.bytes_read,
        "teams": teams,
    }))
}

#[cfg(target_os = "windows")]
fn debug_scan_club_affiliates_impl() -> Result<Value, String> {
    use crate::fm26::club_affiliates::probe_managed_club_affiliate_graph;

    let Some((process_id, _)) = find_fm26_process() else {
        return Err("FM26 process not found.".to_string());
    };
    let mut reader = ProcessReader::open(process_id)
        .map_err(|code| format!("Could not open FM26 read-only handle (Windows error {code})."))?;
    let identity = reader
        .process_path()
        .as_deref()
        .map(read_executable_identity)
        .unwrap_or_default();
    let Some(profile) = find_entity_map(
        identity.file_version.as_deref(),
        identity.product_version.as_deref(),
        identity.sha256.as_deref(),
        identity.architecture.as_deref(),
    ) else {
        return Err("FM26 build is not supported.".to_string());
    };
    let Some(module) = reader.module(&profile.module) else {
        return Err("The FM26 game module was not available.".to_string());
    };
    let mut diagnostics = ExtractionDiagnostics::default();
    let (selected, manager_pick_warning) =
        resolve_active_human_manager(&mut reader, module, profile, process_id, &mut diagnostics)
            .map_err(|failure| failure.message)?;
    let seeds = HashSet::from([selected.team]);
    let discovered = discover_managed_club_teams(
        &mut reader,
        module,
        profile,
        selected.club,
        selected.club_uid,
        selected.team,
        &seeds,
        true,
    );
    let same_club_teams: Vec<Value> = discovered
        .iter()
        .map(|entry| {
            json!({
                "teamUid": entry.team_uid,
                "name": entry.name,
                "rosterLen": entry.roster_len,
                "classifiedUnit": entry.squad_unit,
            })
        })
        .collect();
    let mut graph = probe_managed_club_affiliate_graph(
        &mut reader,
        module,
        profile,
        selected.club,
        selected.club_uid,
        &selected.club_name,
        &same_club_teams,
    );
    if let Some(object) = graph.as_object_mut() {
        object.insert("managerName".to_string(), json!(selected.manager_name));
        object.insert("managerPickWarning".to_string(), json!(manager_pick_warning));
        object.insert("bytesRead".to_string(), json!(reader.bytes_read));
    }
    Ok(graph)
}

/// Club UniqueID + name from a team or club pointer (vtable-validated).
#[cfg(target_os = "windows")]
fn resolve_club_from_pointer(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    pointer: u64,
) -> Option<(u32, String)> {
    if pointer == 0 {
        return None;
    }
    let club = if validator::validate_vtable(
        reader,
        pointer,
        module.base + profile.constants.club_vtable_rva,
    )
    .is_ok()
    {
        pointer
    } else if validator::validate_vtable(
        reader,
        pointer,
        module.base + profile.constants.team_vtable_rva,
    )
    .is_ok()
    {
        let club = reader
            .read_pointer(pointer + profile.constants.team_club_offset)
            .filter(|value| *value != 0)?;
        validator::validate_vtable(reader, club, module.base + profile.constants.club_vtable_rva)
            .ok()?;
        club
    } else {
        return None;
    };
    let uid = reader
        .read_u32(club + profile.constants.entity_uid_offset)
        .filter(|uid| *uid > 0)?;
    let name = reader
        .read_pointer(club + profile.constants.club_name_offset)
        .and_then(|pointer| reader.read_length_prefixed_string(pointer))?;
    Some((uid, name))
}

/// Loan Club from person â†’ loan agreement (FMLE Parent/Loan Club split).
#[cfg(target_os = "windows")]
fn read_person_loan_club(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    person: u64,
) -> Option<(u32, String)> {
    let loan = reader
        .read_pointer(person + profile.constants.person_loan_offset)
        .filter(|value| *value != 0)?;
    if let Some(primary) = reader.read_pointer(loan).filter(|value| *value != 0) {
        if let Some(club) = resolve_club_from_pointer(reader, module, profile, primary) {
            return Some(club);
        }
        for offset in [0x10u64, 0x18] {
            if let Some(pointer) = reader
                .read_pointer(primary + offset)
                .filter(|value| *value != 0)
            {
                if let Some(club) = resolve_club_from_pointer(reader, module, profile, pointer) {
                    return Some(club);
                }
            }
        }
    }
    let bytes = reader.read_bytes(loan, 128)?;
    for offset in (0..bytes.len().saturating_sub(8)).step_by(8) {
        let pointer = u64::from_le_bytes(bytes[offset..offset + 8].try_into().ok()?);
        if let Some(club) = resolve_club_from_pointer(reader, module, profile, pointer) {
            return Some(club);
        }
        if pointer < 0x10000 {
            continue;
        }
        let Some(inner) = reader.read_bytes(pointer, 64) else {
            continue;
        };
        for inner_offset in (0..inner.len().saturating_sub(8)).step_by(8) {
            let child = u64::from_le_bytes(inner[inner_offset..inner_offset + 8].try_into().ok()?);
            if let Some(club) = resolve_club_from_pointer(reader, module, profile, child) {
                return Some(club);
            }
        }
    }
    None
}

/// True when person has an active loan agreement pointing at another club.
fn is_loaned_out_from_loan_club(loan_club_uid: Option<u32>, managed_club_uid: u32) -> bool {
    loan_club_uid
        .map(|uid| uid != managed_club_uid)
        .unwrap_or(false)
}

/// Contract object â†’ employing team pointer.
#[cfg(target_os = "windows")]
fn resolve_contract_team(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
    contract: u64,
) -> Option<u64> {
    reader
        .read_pointer(contract + profile.constants.contract_team_offset)
        .filter(|value| *value != 0)
}

/// Team pointer â†’ club UniqueID when vtable-validated.
#[cfg(target_os = "windows")]
fn contract_team_club_uid(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    team: u64,
) -> Option<u32> {
    resolve_club_from_pointer(reader, module, profile, team).map(|(uid, _)| uid)
}

/// Team display name â€” shares club name string layout until a dedicated offset locks.
#[cfg(target_os = "windows")]
fn read_team_display_name(
    reader: &mut ProcessReader,
    team: u64,
    profile: &EntityMapProfile,
) -> Option<String> {
    let name_pointer = reader
        .read_pointer(team + profile.constants.club_name_offset)
        .filter(|value| *value != 0)?;
    reader.read_length_prefixed_string(name_pointer)
}

/// FMLE-style squad unit from team object label (Senior / U19 / …), not contract counts.
#[cfg(target_os = "windows")]
fn classify_team_squad_unit(
    team_name: &str,
    team: u64,
    first_team: u64,
    team_uid: u32,
    club_uid: u32,
) -> Option<&'static str> {
    if team == first_team || team_uid == club_uid {
        return Some("firstTeam");
    }
    let normalized = team_name.trim().to_ascii_lowercase();
    if normalized.contains(" u19") || normalized.ends_with("u19") {
        return Some("under19s");
    }
    if normalized.contains(" u18") || normalized.ends_with("u18") {
        return Some("under19s");
    }
    if normalized.contains(" u17") || normalized.ends_with("u17") {
        return Some("under19s");
    }
    if normalized.contains(" ii") || normalized.ends_with(" ii") {
        return Some("reserves");
    }
    if normalized.contains("senior") {
        return Some("firstTeam");
    }
    None
}

/// Classify club team when FM labels are missing — satellite teams carry their own entity UID.
#[cfg(target_os = "windows")]
fn classify_club_team_squad_unit(
    team_name: Option<&str>,
    team: u64,
    first_team: u64,
    team_uid: u32,
    club_uid: u32,
    roster_len: usize,
) -> Option<&'static str> {
    if team == first_team || team_uid == club_uid {
        return Some("firstTeam");
    }
    if let Some(name) = team_name.filter(|value| !value.trim().is_empty()) {
        if let Some(unit) = classify_team_squad_unit(name, team, first_team, team_uid, club_uid) {
            return Some(unit);
        }
    }
    if team_uid != club_uid {
        if roster_len >= 5 {
            return Some("under19s");
        }
        return Some("reserves");
    }
    None
}

#[cfg(target_os = "windows")]
fn club_team_label(name: &str, team_uid: u32) -> String {
    if name.trim().is_empty() {
        format!("team-uid-{team_uid}")
    } else {
        name.to_string()
    }
}

#[cfg(target_os = "windows")]
fn probe_team_roster_identities(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
    team: u64,
) -> Vec<Value> {
    let Some(players_start) = reader
        .read_pointer(team + profile.constants.team_players_start_offset)
        .filter(|value| *value != 0)
    else {
        return Vec::new();
    };
    let Some(players_end) = reader
        .read_pointer(team + profile.constants.team_players_end_offset)
        .filter(|value| *value != 0)
    else {
        return Vec::new();
    };
    if players_end <= players_start || (players_end - players_start) % 8 != 0 {
        return Vec::new();
    }
    let player_count = ((players_end - players_start) / 8) as usize;
    let mut entries = Vec::with_capacity(player_count);
    for index in 0..player_count {
        let slot = players_start + (index as u64 * 8);
        let Some(raw_player) = reader.read_pointer(slot).filter(|value| *value != 0) else {
            entries.push(json!({ "slot": index, "reject": "empty_player_pointer" }));
            continue;
        };
        let Some(person) = resolve_person_address(reader, raw_player, profile) else {
            let mut fallback = json!({
                "slot": index,
                "rawPlayerPointer": hex_address(raw_player),
                "reject": "person_unresolved",
            });
            if let Some(uid) = reader
                .read_u32(raw_player + profile.constants.entity_uid_offset)
                .filter(|uid| is_plausible_fm_unique_id(*uid))
            {
                fallback["playerUidDirect"] = json!(uid);
                let (name, name_source) = resolve_managed_squad_name(reader, raw_player, profile, uid);
                fallback["name"] = json!(name);
                fallback["nameSource"] = json!(name_source);
            } else if let Some(name) = fm_dossier::player_display_name(
                &reader
                    .read_u32(raw_player + profile.constants.entity_uid_offset)
                    .unwrap_or(0)
                    .to_string(),
            ) {
                fallback["name"] = json!(name);
                fallback["nameSource"] = json!("dossier-uid-only");
            }
            entries.push(fallback);
            continue;
        };
        let uid = reader
            .read_u32(person + profile.constants.entity_uid_offset)
            .filter(|uid| is_plausible_fm_unique_id(*uid));
        let (name, name_source) = uid
            .map(|player_uid| resolve_managed_squad_name(reader, person, profile, player_uid))
            .unwrap_or_else(|| ("unknown".to_string(), "missing-uid"));
        entries.push(json!({
            "slot": index,
            "rawPlayerPointer": hex_address(raw_player),
            "playerUid": uid,
            "name": name,
            "nameSource": name_source,
        }));
    }
    entries
}

#[cfg(target_os = "windows")]
fn team_roster_len(reader: &mut ProcessReader, profile: &EntityMapProfile, team: u64) -> Option<usize> {
    let players_start = reader
        .read_pointer(team + profile.constants.team_players_start_offset)
        .filter(|value| *value != 0)?;
    let players_end = reader
        .read_pointer(team + profile.constants.team_players_end_offset)
        .filter(|value| *value != 0)?;
    if players_end <= players_start || (players_end - players_start) % 8 != 0 {
        return None;
    }
    let slots = ((players_end - players_start) / 8) as usize;
    (1..=200).contains(&slots).then_some(slots)
}

#[cfg(target_os = "windows")]
struct DiscoveredClubTeam {
    team: u64,
    team_uid: u32,
    name: String,
    squad_unit: &'static str,
    roster_len: usize,
}

/// Club → Teams: validated team objects linked to the managed club (FMLE tree parity).
#[cfg(target_os = "windows")]
fn discover_managed_club_teams(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    first_team: u64,
    index_team_seeds: &HashSet<u64>,
    scan_heap: bool,
) -> Vec<DiscoveredClubTeam> {
    let team_vtable = module.base + profile.constants.team_vtable_rva;
    let mut candidate_teams: HashSet<u64> = index_team_seeds.clone();
    if scan_heap {
        if let Ok(hits) = scan_private_memory_for_pointers(reader, &[team_vtable]) {
            if let Some(addresses) = hits.get(&team_vtable) {
                candidate_teams.extend(addresses.iter().copied());
            }
        }
    }

    let mut seen = HashSet::new();
    let mut discovered = Vec::new();
    for team in candidate_teams {
        if team == 0 || !seen.insert(team) {
            continue;
        }
        if validator::validate_vtable(reader, team, team_vtable).is_err() {
            continue;
        }
        let Some(linked_club) = reader
            .read_pointer(team + profile.constants.team_club_offset)
            .filter(|value| *value != 0)
        else {
            continue;
        };
        let club_matches = if linked_club == managed_club {
            true
        } else {
            reader
                .read_u32(linked_club + profile.constants.entity_uid_offset)
                .is_some_and(|uid| uid == managed_club_uid)
        };
        if !club_matches {
            continue;
        }
        let Some(roster_len) = team_roster_len(reader, profile, team) else {
            continue;
        };
        let name = read_team_display_name(reader, team, profile).unwrap_or_default();
        let team_uid = reader
            .read_u32(team + profile.constants.entity_uid_offset)
            .unwrap_or(0);
        let Some(squad_unit) = classify_club_team_squad_unit(
            Some(name.as_str()).filter(|value| !value.trim().is_empty()),
            team,
            first_team,
            team_uid,
            managed_club_uid,
            roster_len,
        ) else {
            continue;
        };
        discovered.push(DiscoveredClubTeam {
            team,
            team_uid,
            name,
            squad_unit,
            roster_len,
        });
    }
    discovered.sort_by(|left, right| {
        right
            .roster_len
            .cmp(&left.roster_len)
            .then_with(|| left.name.cmp(&right.name))
    });
    discovered
}

fn club_teams_json(discovered: &[DiscoveredClubTeam], manager_team: u64) -> Vec<Value> {
    discovered
        .iter()
        .map(|entry| {
            json!({
                "teamUid": entry.team_uid.to_string(),
                "name": entry.name,
                "rosterLen": entry.roster_len,
                "squadUnit": entry.squad_unit,
                "isManagerTeam": entry.team == manager_team,
            })
        })
        .collect()
}

fn collect_index_club_team_pointers(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    records: &HashMap<String, IndexedPlayerRecord>,
    managed_club_uid: u32,
) -> HashSet<u64> {
    let mut teams = HashSet::new();
    for record in records.values() {
        let Some(contract) = record.contract_address else {
            continue;
        };
        let Some(team) = resolve_contract_team(reader, profile, contract) else {
            continue;
        };
        if contract_team_club_uid(reader, module, profile, team).is_some_and(|uid| uid == managed_club_uid)
        {
            teams.insert(team);
        }
    }
    teams
}

#[cfg(target_os = "windows")]
#[allow(clippy::too_many_arguments)]
fn load_team_roster(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    squad_team: u64,
    team_label: &str,
    squad_unit: &'static str,
    squad_team_uid: u32,
    club_id: &str,
    club_uid: u32,
    squad_game_date: Option<FmDate>,
    managed_player_ids: &mut HashSet<String>,
    managed_index_records: &mut Vec<IndexedPlayerRecord>,
    players: &mut Vec<Value>,
    skipped_squad_slots: &mut u32,
    skipped_squad_details: &mut Vec<String>,
    name_fallback_details: &mut Vec<String>,
    player_vtable: &mut Option<u64>,
) -> usize {
    let Some(players_start) = reader
        .read_pointer(squad_team + profile.constants.team_players_start_offset)
        .filter(|value| *value != 0)
    else {
        return 0;
    };
    let Some(players_end) = reader
        .read_pointer(squad_team + profile.constants.team_players_end_offset)
        .filter(|value| *value != 0)
    else {
        return 0;
    };
    if players_end <= players_start
        || (players_end - players_start) % 8 != 0
        || !((1..=200).contains(&((players_end - players_start) / 8)))
    {
        return 0;
    }
    let player_count = ((players_end - players_start) / 8) as usize;
    let before = players.len();
    for index in 0..player_count {
        let Some(raw_player) = reader
            .read_pointer(players_start + (index as u64 * 8))
            .filter(|value| *value != 0)
        else {
            *skipped_squad_slots += 1;
            skipped_squad_details.push(format!("{team_label} slot {index}: empty player pointer"));
            continue;
        };
        push_squad_player_from_raw(
            reader,
            module,
            profile,
            raw_player,
            &format!("{team_label} slot {index}"),
            squad_unit,
            squad_team_uid,
            club_id,
            club_uid,
            squad_game_date,
            managed_player_ids,
            managed_index_records,
            players,
            skipped_squad_slots,
            skipped_squad_details,
            name_fallback_details,
            player_vtable,
        );
    }
    players.len().saturating_sub(before)
}

/// Indexed records whose active contract employs them at `managed_club_uid`.
#[cfg(target_os = "windows")]
fn count_managed_club_employees(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    records: &HashMap<String, IndexedPlayerRecord>,
    managed_club_uid: u32,
) -> u32 {
    records
        .values()
        .filter(|record| {
            let Some(contract) = record.contract_address else {
                return false;
            };
            let Some(team) = resolve_contract_team(reader, profile, contract) else {
                return false;
            };
            contract_team_club_uid(reader, module, profile, team)
                .is_some_and(|uid| uid == managed_club_uid)
        })
        .count() as u32
}

#[cfg(target_os = "windows")]
fn snapshot_club_employee_count(players: &[Value], managed_club_id: &str) -> u32 {
    players
        .iter()
        .filter(|player| {
            player
                .get("clubId")
                .and_then(Value::as_str)
                .is_some_and(|club_id| club_id == managed_club_id)
        })
        .count() as u32
}

#[cfg(target_os = "windows")]
#[allow(clippy::too_many_arguments)]
fn push_squad_player_from_raw(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    raw_player: u64,
    slot_label: &str,
    squad_unit: &'static str,
    squad_team_uid: u32,
    club_id: &str,
    club_uid: u32,
    squad_game_date: Option<FmDate>,
    managed_player_ids: &mut HashSet<String>,
    managed_index_records: &mut Vec<IndexedPlayerRecord>,
    players: &mut Vec<Value>,
    skipped_squad_slots: &mut u32,
    skipped_squad_details: &mut Vec<String>,
    name_fallback_details: &mut Vec<String>,
    player_vtable: &mut Option<u64>,
) {
    let vtable = match reader
        .read_pointer(raw_player)
        .filter(|value| *value != 0)
    {
        Some(value) => value,
        None => {
            *skipped_squad_slots += 1;
            skipped_squad_details.push(format!(
                "{slot_label}: unreadable vtable @ {raw_player:#x}"
            ));
            return;
        }
    };
    player_vtable.get_or_insert(vtable);
    let person = match resolve_person_address(reader, raw_player, profile) {
        Some(value) => value,
        None => {
            *skipped_squad_slots += 1;
            skipped_squad_details.push(format!(
                "{slot_label}: person object not resolved @ {raw_player:#x}"
            ));
            return;
        }
    };
    let uid = match reader
        .read_u32(person + profile.constants.entity_uid_offset)
        .filter(|uid| is_plausible_fm_unique_id(*uid))
    {
        Some(value) => value,
        None => {
            *skipped_squad_slots += 1;
            skipped_squad_details.push(format!(
                "{slot_label}: missing plausible UniqueID (person @ {person:#x})"
            ));
            return;
        }
    };
    let position_bytes = match reader.read_bytes(
        raw_player + profile.constants.player_positions_offset,
        POSITION_NAMES.len(),
    ) {
        Some(bytes) => bytes,
        None => {
            *skipped_squad_slots += 1;
            skipped_squad_details.push(format!("{slot_label} uid {uid}: unreadable position blob"));
            return;
        }
    };
    if let Some(issue) = position_bytes_issue(&position_bytes) {
        *skipped_squad_slots += 1;
        skipped_squad_details.push(format!("{slot_label} uid {uid}: {issue}"));
        return;
    }
    let (positions, secondary_positions) = classify_player_positions(&position_bytes);
    if positions.is_empty() {
        *skipped_squad_slots += 1;
        skipped_squad_details.push(format!(
            "{slot_label} uid {uid}: no primary position after classification"
        ));
        return;
    }
    let attribute_bytes = match reader.read_bytes(
        raw_player + profile.constants.player_attributes_offset,
        PLAYER_ATTRIBUTE_NAMES.len(),
    ) {
        Some(bytes) => bytes,
        None => {
            *skipped_squad_slots += 1;
            skipped_squad_details.push(format!("{slot_label} uid {uid}: unreadable attribute blob"));
            return;
        }
    };
    if let Some(issue) = attribute_bytes_issue(&attribute_bytes) {
        *skipped_squad_slots += 1;
        skipped_squad_details.push(format!("{slot_label} uid {uid}: {issue}"));
        return;
    }
    let (name, name_source) = resolve_managed_squad_name(reader, person, profile, uid);
    if name_source != "own-squad" {
        name_fallback_details.push(format!("uid {uid} ({name_source})"));
    }
    let calculated_position = position_bytes
        .iter()
        .enumerate()
        .max_by_key(|(_, rating)| **rating)
        .map(|(position, _)| POSITION_NAMES[position].to_string());
    let goalkeeper_rating = goalkeeper_rating_from_positions(&position_bytes);
    let birth_date = read_fm_date(reader, person + profile.constants.person_birth_date_offset);
    let own_current_date =
        read_fm_date(reader, raw_player + profile.constants.player_current_date_offset);
    let current_date = own_current_date.or(squad_game_date);
    let age = birth_date
        .zip(current_date)
        .and_then(|(birth, current)| calculate_age(birth, current));
    let date_of_birth = birth_date.and_then(format_fm_date);
    let season = current_date.map(|date| {
        let next_year = date.year.saturating_add(1);
        format!("{}/{}", date.year, next_year % 100)
    });
    let nationality = read_nationality(reader, person, profile);
    let nationality_id = read_nation_id(reader, person, profile);
    let visible_attributes = visible_attribute_map(&attribute_bytes);
    let hidden_attributes = hidden_attribute_map(&attribute_bytes);
    let all_time_attr_deltas = Value::Object(serde_json::Map::new());
    let ca_pack_point_count = 0usize;
    let recent_attr_deltas = Value::Object(serde_json::Map::new());
    let personality_bytes = reader
        .read_bytes(person + profile.constants.person_personality_offset, 8)
        .unwrap_or_default();
    let personality_attributes = personality_attribute_map(&personality_bytes);
    let current_ability = reader
        .read_u16(raw_player + profile.constants.player_ca_offset)
        .filter(|value| (1..=200).contains(value));
    let potential_ability = reader
        .read_u16(raw_player + profile.constants.player_pa_offset)
        .filter(|value| (1..=200).contains(value));
    let left_foot = display_attribute(attribute_bytes[24]);
    let right_foot = display_attribute(attribute_bytes[25]);
    let preferred_foot = preferred_foot_label(left_foot, right_foot);
    let height_cm = reader
        .read_bytes(raw_player + profile.constants.player_height_offset, 1)
        .and_then(|bytes| bytes.first().copied())
        .filter(|value| (140..=220).contains(value));
    let ability_score = calculated_position
        .as_deref()
        .and_then(|position| visible_ability_score(position, &visible_attributes));
    let best_role: Option<String> = None;
    let playable_roles: Vec<Value> = Vec::new();
    let other_roles: Vec<Value> = Vec::new();
    let role_reasoning = vec![
        "Role catalogue scoring is deferred on load for speed; open the player after roles are re-enabled or use attributes/CA/PA/HA.".to_string(),
    ];
    let (strengths, weaknesses) = attribute_evidence(&visible_attributes);
    let compact = crate::fmt_log::compact_payload();
    let validated_at = unix_milliseconds();
    let attribute_knowledge: serde_json::Map<String, Value> = if compact {
        serde_json::Map::new()
    } else {
        visible_attributes
            .iter()
            .map(|(name, value)| {
                (
                    name.clone(),
                    json!({
                        "value": value,
                        "visibility": "known",
                        "source": "own-squad",
                        "confidence": 100,
                        "lastValidated": validated_at
                    }),
                )
            })
            .collect()
    };
    let player_id = uid.to_string();
    if managed_player_ids.contains(&player_id) {
        return;
    }
    let contract_address = reader
        .read_pointer(person + profile.constants.person_contract_offset)
        .filter(|value| *value != 0);
    let loan_club = read_person_loan_club(reader, module, profile, person);
    let loan_club_uid = loan_club.as_ref().map(|(uid, _)| *uid);
    let loaned_out = is_loaned_out_from_loan_club(loan_club_uid, club_uid);
    let (loan_club_id, loan_club_name) = if loaned_out {
        match loan_club {
            Some((uid, name)) => (Some(uid.to_string()), Some(name)),
            None => (None, None),
        }
    } else {
        (None, None)
    };
    managed_player_ids.insert(player_id.clone());
    managed_index_records.push(IndexedPlayerRecord {
        id: player_id.clone(),
        name: name.clone(),
        positions: positions.clone(),
        managed_squad: true,
        visibility_safe: true,
        raw_player_address: raw_player,
        person_address: person,
        contract_address,
    });
    players.push(json!({
        "id": player_id,
        "name": name.clone(),
        "_season": season,
        "age": age,
        "dateOfBirth": date_of_birth,
        "nationality": nationality.clone(),
        "nationalityId": nationality_id.clone(),
        "secondNationality": null,
        "positions": positions.clone(),
        "secondaryPositions": secondary_positions.clone(),
        "goalkeeperRating": goalkeeper_rating,
        "bestRole": best_role,
        "currentAbility": current_ability,
        "potentialAbility": potential_ability,
        "abilityScore": ability_score,
        "form": null,
        "averageRating": null,
        "minutesPlayed": null,
        "goals": null,
        "assists": null,
        "contractStatus": null,
        "value": null,
        "wage": null,
        "squadImportance": null,
        "developmentTrend": null,
        "tacticalFit": null,
        "roleFit": ability_score,
        "playableRoles": playable_roles,
        "otherRoles": other_roles,
        "preferredFoot": preferred_foot,
        "leftFoot": left_foot,
        "rightFoot": right_foot,
        "heightCm": height_cm,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "clubId": club_id,
        "squadUnit": squad_unit,
        "squadTeamUid": squad_team_uid.to_string(),
        "loanedOut": loaned_out,
        "loanClubId": loan_club_id,
        "loanClubName": loan_club_name,
        "transferInterest": null,
        "loanInterest": null,
        "transferAvailable": null,
        "loanAvailable": null,
        "attributes": visible_attributes,
        "hiddenAttributes": hidden_attributes,
        "personalityAttributes": personality_attributes,
        "recentAttrDeltas": recent_attr_deltas,
        "allTimeAttrDeltas": all_time_attr_deltas,
        "caPackPointCount": ca_pack_point_count,
        "per90": {},
        "scoutKnowledge": "fully_known",
        "scoutConfidence": 100,
        "lastScoutedDate": null,
        "reportReliability": null,
        "bestCalculatedPosition": calculated_position,
        "truePrice": null,
        "fairPriceRange": null,
        "valuationLabel": "unavailable",
        "valuationReasoning": ["FM26 valuation fields are not mapped for this exact build."],
        "retrainingSuggestion": null,
        "roleReasoning": role_reasoning,
        "riskLevel": "unknown",
        "marketValueAmount": null
        ,"personality": null
        ,"condition": null
    }));
    if !compact {
        if let Some(object) = players.last_mut().and_then(Value::as_object_mut) {
            object.insert(
                "recommendation".to_string(),
                json!({
                    "minimum": ability_score,
                    "maximum": ability_score,
                    "completeness": 100,
                    "label": if ability_score.is_some() { "full visible-attribute evidence" } else { "not enough evidence" }
                }),
            );
            object.insert(
                "knowledge".to_string(),
                json!({
                    "name": { "value": name, "visibility": "known", "source": name_source, "confidence": if name_source == "own-squad" { 100 } else { 85 }, "lastValidated": validated_at },
                    "age": { "value": age, "visibility": "known", "source": "own-squad", "confidence": 100, "lastValidated": validated_at },
                    "nationality": { "value": nationality, "visibility": "known", "source": "own-squad", "confidence": 100, "lastValidated": validated_at },
                    "positions": { "value": positions, "visibility": "known", "source": "own-squad", "confidence": 100, "lastValidated": validated_at },
                    "attributes": attribute_knowledge,
                    "form": { "value": null, "visibility": "unknown", "source": "memory-raw", "confidence": 0, "lastValidated": null },
                    "contract": { "value": null, "visibility": "unknown", "source": "memory-raw", "confidence": 0, "lastValidated": null },
                    "wage": { "value": null, "visibility": "unknown", "source": "memory-raw", "confidence": 0, "lastValidated": null },
                    "value": { "value": null, "visibility": "unknown", "source": "memory-raw", "confidence": 0, "lastValidated": null },
                    "interest": { "value": null, "visibility": "unknown", "source": "memory-raw", "confidence": 0, "lastValidated": null }
                }),
            );
        }
    }
}

#[cfg(target_os = "windows")]
fn extract_live_data(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    diagnostics: &mut ExtractionDiagnostics,
    process_id: u32,
    include_database_index: bool,
    progress: Option<&dyn Fn(&'static str)>,
) -> Result<LiveData, ExtractionFailure> {
    let signature = profile
        .signatures
        .iter()
        .find(|item| item.name == "human_manager_registry")
        .ok_or_else(|| {
            ExtractionFailure::new("manager_signature", "The exact build map is incomplete.")
        })?;
    let pattern = parse_pattern(&signature.pattern).map_err(|_| {
        ExtractionFailure::new("entity_map", "The embedded signature pattern is invalid.")
    })?;
    let signature_address = {
        let cached = manager_signature_cache()
            .lock()
            .ok()
            .and_then(|guard| {
                guard.as_ref().copied().filter(|hit| {
                    hit.process_id == process_id && hit.module_base == module.base
                })
            })
            .map(|hit| hit.signature_address);
        if let Some(address) = cached {
            crate::fmt_log::load_detail("manager signature: cache hit");
            address
        } else {
            crate::fmt_log::load_detail(format!(
                "manager signature: scanning {} ({} bytes)",
                profile.module, module.size
            ));
            let hits = scan_module(reader, module, &pattern)
                .map_err(|error| ExtractionFailure::new("manager_signature", error.to_string()))?;
            if hits.len() != 1 {
                return Err(ExtractionFailure::new(
                    "manager_signature",
                    format!(
                        "The FM26 manager root did not validate uniquely ({} matches). No game data was shown.",
                        hits.len()
                    ),
                ));
            }
            let address = hits[0];
            crate::fmt_log::load_detail(format!("manager signature: hit @ {address:#x}"));
            if let Ok(mut guard) = manager_signature_cache().lock() {
                *guard = Some(CachedManagerSignature {
                    process_id,
                    module_base: module.base,
                    signature_address: address,
                });
            }
            address
        }
    };
    let displacement = reader.read_i32(signature_address + 3).ok_or_else(|| {
        ExtractionFailure::new(
            "manager_signature",
            "The FM26 manager signature could not be read.",
        )
    })?;
    let registry_slot = (signature_address + 7).wrapping_add_signed(displacement as i64);
    let registry = reader
        .read_pointer(registry_slot)
        .filter(|value| *value != 0)
        .ok_or_else(|| {
            ExtractionFailure::new(
                "manager_registry",
                "No active FM26 manager registry was available.",
            )
        })?;
    diagnostics.entity_root = Some(registry);
    diagnostics.last_successful_read = Some("resolve_manager_registry".to_string());

    let vector_start = reader
        .read_pointer(registry + profile.constants.manager_registry_vector_offset)
        .ok_or_else(|| {
            ExtractionFailure::new(
                "manager_registry",
                "The active manager collection could not be read.",
            )
        })?;
    let vector_end = reader
        .read_pointer(registry + profile.constants.manager_registry_vector_offset + 8)
        .ok_or_else(|| {
            ExtractionFailure::new(
                "manager_registry",
                "The active manager collection end could not be read.",
            )
        })?;
    let registry_bytes = vector_end.saturating_sub(vector_start);
    let registry_count = registry_bytes / 8;
    if vector_end <= vector_start || registry_bytes % 8 != 0 || !(1..=32).contains(&registry_count)
    {
        return Err(ExtractionFailure::new(
            "manager_registry",
            format!(
                "The FM26 manager registry size was invalid ({registry_bytes} bytes). Expected 1â€“32 human manager slots."
            ),
        ));
    }

    // Continue / NewGAN saves can keep an inactive past manager in the same registry
    // vector. Stock GlassScout requires exactly one slot (size == 8) and fails otherwise.
    // FMT validates every slot and picks the active career by largest squad (T135).
    let mut resolved = Vec::new();
    for index in 0..registry_count {
        let human = match reader
            .read_pointer(vector_start + index * 8)
            .filter(|value| *value != 0)
        {
            Some(value) => value,
            None => continue,
        };
        if let Some(candidate) = try_resolve_human_manager(reader, module, profile, human) {
            resolved.push(candidate);
        }
    }
    let mut manager_pick_warning: Option<String> = None;
    let selected = match resolved.len() {
        0 => {
            return Err(ExtractionFailure::new(
                "manager_registry",
                format!(
                    "No playable human manager validated in the registry ({registry_count} slot{}).",
                    if registry_count == 1 { "" } else { "s" }
                ),
            ));
        }
        1 => resolved.remove(0),
        _ => {
            let candidates = resolved
                .iter()
                .map(|item| {
                    format!(
                        "{} @ {} ({} squad)",
                        item.manager_name, item.club_name, item.squad_len
                    )
                })
                .collect::<Vec<_>>()
                .join("; ");
            let best_index = resolved
                .iter()
                .enumerate()
                .max_by_key(|(_, item)| item.squad_len)
                .map(|(index, _)| index)
                .unwrap_or(0);
            let selected = resolved.swap_remove(best_index);
            manager_pick_warning = Some(format!(
                "Multiple human managers validated [{candidates}]. Selected {} @ {} ({} squad) as the active career.",
                selected.manager_name, selected.club_name, selected.squad_len
            ));
            selected
        }
    };
    let human = selected.human;
    let manager_name = selected.manager_name;
    let team = selected.team;
    let club = selected.club;
    let club_uid = selected.club_uid;
    let club_name = selected.club_name;
    diagnostics.save_pointer = Some(human);
    diagnostics.last_successful_read = Some("resolve_human_manager".to_string());
    diagnostics.managed_club_pointer = Some(club);
    diagnostics.last_successful_read = Some("validate_managed_club".to_string());
    if let Some(progress) = progress {
        progress("loading_managed_squad");
    }

    let club_id = club_uid.to_string();

    let memory_anchors = LiveMemoryAnchors {
        save_pointer: human,
        human_pointer: human,
        team_pointer: team,
        club_pointer: club,
        players_collection_start: 0,
        tactic_manager_pointer: None,
    };

    // Loaned player objects often lack a readable current-date; borrow one from the squad.
    let mut squad_game_date = None;
    if let Some(players_start) = reader
        .read_pointer(team + profile.constants.team_players_start_offset)
        .filter(|value| *value != 0)
    {
        if let Some(players_end) = reader
            .read_pointer(team + profile.constants.team_players_end_offset)
            .filter(|value| *value != 0)
        {
            let player_count = ((players_end.saturating_sub(players_start)) / 8) as usize;
            for index in 0..player_count {
                let Some(raw_player) = reader
                    .read_pointer(players_start + (index as u64 * 8))
                    .filter(|value| *value != 0)
                else {
                    continue;
                };
                if let Some(date) =
                    read_fm_date(reader, raw_player + profile.constants.player_current_date_offset)
                {
                    squad_game_date = Some(date);
                    break;
                }
            }
        }
    }

    let players_start = reader
        .read_pointer(team + profile.constants.team_players_start_offset)
        .ok_or_else(|| {
            ExtractionFailure::new(
                "player_collection",
                "The managed squad collection was not readable.",
            )
        })?;
    let players_end = reader
        .read_pointer(team + profile.constants.team_players_end_offset)
        .ok_or_else(|| {
            ExtractionFailure::new(
                "player_collection",
                "The managed squad collection end was not readable.",
            )
        })?;
    if players_end <= players_start
        || (players_end - players_start) % 8 != 0
        || !(1..=200).contains(&((players_end - players_start) / 8))
    {
        return Err(ExtractionFailure::new(
            "player_collection",
            "The managed squad collection failed its size and alignment checks.",
        ));
    }
    diagnostics.player_collection_pointer = Some(players_start);
    let player_count = ((players_end - players_start) / 8) as usize;

    let mut players = Vec::new();
    let mut managed_player_ids = HashSet::new();
    let mut managed_index_records = Vec::new();
    let mut player_vtable = None;
    let mut skipped_squad_slots = 0u32;
    let mut skipped_squad_details: Vec<String> = Vec::new();
    let mut name_fallback_details: Vec<String> = Vec::new();
    let manager_team_uid = reader
        .read_u32(team + profile.constants.entity_uid_offset)
        .filter(|uid| *uid > 0)
        .unwrap_or(club_uid);

    for index in 0..player_count {
        let Some(raw_player) = reader
            .read_pointer(players_start + (index as u64 * 8))
            .filter(|value| *value != 0)
        else {
            skipped_squad_slots += 1;
            skipped_squad_details.push(format!("slot {index}: empty player pointer"));
            continue;
        };
        push_squad_player_from_raw(
            reader,
            module,
            profile,
            raw_player,
            &format!("slot {index}"),
            "firstTeam",
            manager_team_uid,
            &club_id,
            club_uid,
            squad_game_date,
            &mut managed_player_ids,
            &mut managed_index_records,
            &mut players,
            &mut skipped_squad_slots,
            &mut skipped_squad_details,
            &mut name_fallback_details,
            &mut player_vtable,
        );
    }

    let mut memory_anchors = memory_anchors;
    memory_anchors.players_collection_start = players_start;

    if players.is_empty() {
        return Err(ExtractionFailure::new(
            "player_identity",
            "No managed squad players could be read (all slots failed identity checks).",
        ));
    }
    diagnostics.last_successful_read = Some("extract_managed_squad".to_string());
    crate::fmt_log::load_detail(format!(
        "managed squad: {} players validated ({} slots scanned, {} skipped)",
        players.len(),
        player_count,
        skipped_squad_slots
    ));
    let managed_tactic_records = managed_index_records.clone();
    let skipped_squad_warning = if skipped_squad_slots > 0 {
        let mut message = format!(
            "Managed squad memory skipped {skipped_squad_slots} slot(s); {} players passed validation.",
            players.len(),
        );
        for detail in skipped_squad_details.iter().take(8) {
            message.push_str("\n- ");
            message.push_str(detail);
        }
        if skipped_squad_details.len() > 8 {
            message.push_str(&format!(
                "\n- â€¦ and {} more skipped slot(s)",
                skipped_squad_details.len() - 8
            ));
        }
        Some(message)
    } else {
        None
    };
    let name_fallback_warning = (!name_fallback_details.is_empty()).then(|| {
        format!(
            "{} managed-squad name(s) used save-index fallback because live FM name strings were unreadable: {}",
            name_fallback_details.len(),
            name_fallback_details.join("; ")
        )
    });

    let (
        database_players_indexed,
        background_players_indexed,
        database_index_status,
        database_scope,
        tactic_manager_pointer,
        database_index_error,
    ) = if include_database_index {
        if let Some(progress) = progress {
            progress("indexing_player_database");
        }
        let seed_vtable = player_vtable.ok_or_else(|| {
            ExtractionFailure::new(
                "player_database",
                "The live squad did not provide a player type signature.",
            )
        })?;
        match index_full_player_database(
            reader,
            profile,
            process_id,
            memory_anchors,
            seed_vtable,
            module,
            &managed_player_ids,
            managed_index_records.clone(),
        ) {
            Ok(indexed) => {
                if let Some(progress) = progress {
                    progress("building_visibility_index");
                }
                diagnostics.last_successful_read = Some("index_full_player_database".to_string());
                (
                    indexed.total,
                    indexed.background,
                    "ready",
                    "full-save-index",
                    indexed.tactic_manager_pointer,
                    None,
                )
            }
            Err(failure) => (
                managed_player_ids.len() as u32,
                0,
                "failed",
                "managed-squad",
                None,
                Some(format!("{}: {}", failure.stage, failure.message)),
            ),
        }
    } else {
        store_player_index(process_id, memory_anchors, managed_index_records.clone());
        (
            managed_player_ids.len() as u32,
            0,
            "not_run",
            "managed-squad",
            None,
            None,
        )
    };

    let mut club_squad_promoted = 0usize;
    let mut discovered_team_labels: Vec<String> = Vec::new();
    if let Some(progress) = progress {
        progress("loading_club_teams");
    }
    let mut index_team_seeds = if include_database_index {
        PLAYER_DATABASE_INDEX
            .get()
            .and_then(|index| index.read().ok())
            .map(|guard| {
                collect_index_club_team_pointers(
                    reader,
                    module,
                    profile,
                    &guard.records,
                    club_uid,
                )
            })
            .unwrap_or_default()
    } else {
        HashSet::new()
    };
    index_team_seeds.insert(team);
    let discovered_teams = discover_managed_club_teams(
        reader,
        module,
        profile,
        club,
        club_uid,
        team,
        &index_team_seeds,
        true,
    );
    for entry in &discovered_teams {
        discovered_team_labels.push(format!(
            "{} uid {} ({}, {} roster)",
            entry.name.trim(),
            entry.team_uid,
            entry.squad_unit,
            entry.roster_len
        ));
    }
    let club_teams = club_teams_json(&discovered_teams, team);
    for entry in discovered_teams {
        if entry.team == team || entry.squad_unit == "firstTeam" {
            continue;
        }
        let label = entry.name.clone();
        club_squad_promoted += load_team_roster(
            reader,
            module,
            profile,
            entry.team,
            &label,
            entry.squad_unit,
            entry.team_uid,
            &club_id,
            club_uid,
            squad_game_date,
            &mut managed_player_ids,
            &mut managed_index_records,
            &mut players,
            &mut skipped_squad_slots,
            &mut skipped_squad_details,
            &mut name_fallback_details,
            &mut player_vtable,
        );
    }

    let season = players
        .first()
        .and_then(|player| player.get("_season"))
        .and_then(Value::as_str)
        .map(str::to_string);
    for player in &mut players {
        if let Some(object) = player.as_object_mut() {
            object.remove("_season");
        }
    }
    let dossier_reference = if include_database_index {
        fm_dossier::augment_live_players(&mut players)
    } else {
        None
    };
    // Do not let Dossier mask a failed/missing memory world index (stock GS load truth).
    let database_players_indexed = if database_index_status == "ready" {
        dossier_reference
            .as_ref()
            .map(|reference| database_players_indexed.max(reference.player_count))
            .unwrap_or(database_players_indexed)
    } else {
        database_players_indexed
    };
    let background_players_indexed = if database_index_status == "ready" {
        dossier_reference
            .as_ref()
            .map(|reference| {
                reference
                    .player_count
                    .saturating_sub(players.len().try_into().unwrap_or_default())
                    .max(background_players_indexed)
            })
            .unwrap_or(background_players_indexed)
    } else {
        background_players_indexed
    };
    let tactic = tactic_manager_pointer
        .and_then(|pointer| extract_live_tactic(reader, pointer, &managed_tactic_records));
    let mut warnings = vec![
        "Managed-squad IDs, names, dates of birth, ages, nationality, positions, preferred foot, visible attributes, and mapped CA/PA/hidden/personality are validated for this FM26 build.".to_string(),
        "FM26 role, duty and out-of-possession role catalogues are mapped from the current build metadata. Player playable-role scoring now uses mapped role metadata plus live attributes and position familiarity.".to_string(),
        "Form, match ratings, contract, wage, valuation, fitness and squad-status relationships are not yet validated for this build and remain Unknown.".to_string(),
        if tactic.is_some() {
            "Live FM26 tactic formation and selected XI slots are mapped from the active tactic manager. Role/duty slot packets are published only if their FM26 masks validate against the live formation.".to_string()
        } else {
            "The live FM26 tactic manager is detected with read-only access, but the selected-slot block did not validate for this read. No tactic is guessed.".to_string()
        },
            "The FM26 shortlist collection is not mapped safely. FMT Favorites remains a local list resolved against live players.".to_string(),
    ];
    if let Some(warning) = skipped_squad_warning {
        warnings.push(warning);
    }
    if let Some(warning) = name_fallback_warning {
        warnings.push(warning);
    }
    if let Some(warning) = manager_pick_warning {
        warnings.push(warning);
    }
    if let Some(error) = &database_index_error {
        warnings.push(format!(
            "Wider player database index failed ({error}). Only the managed squad is available â€” same fallback as stock GlassScout, but the failure reason is now visible."
        ));
    } else if include_database_index && database_index_status == "ready" {
        if dossier_reference.is_some() {
            warnings.push(format!(
                "{background_players_indexed} wider-save player records were indexed in memory; FM Dossier also enriched contract/search fields from a local save index."
            ));
        } else {
            warnings.push(format!(
                "{background_players_indexed} wider-save player records were indexed in memory (stock GlassScout full-save path). They remain hidden from the UI until FM scout-knowledge visibility can be validated."
            ));
        }
    } else if include_database_index {
        warnings.push(
            "The wider player database could not be indexed safely; only the managed squad is available."
                .to_string(),
        );
    }
    if club_squad_promoted > 0 {
        warnings.push(format!(
            "{club_squad_promoted} player(s) loaded from satellite club team rosters (UID-classified youth/reserve squads)."
        ));
    } else if !discovered_team_labels.is_empty() {
        warnings.push(format!(
            "Club team objects discovered ({}) but no satellite roster loaded.",
            discovered_team_labels.join("; ")
        ));
    }
    if let Some(reference) = &dossier_reference {
        warnings.push(format!(
            "FM Dossier local save index enriched missing contract, wage, value, condition, history and search fields from {}. This is a local read-only reference layer while native offsets are mapped.",
            reference.path.display()
        ));
    }
    let club_employees = if database_index_status == "ready" {
        PLAYER_DATABASE_INDEX
            .get()
            .and_then(|index| index.read().ok())
            .map(|guard| {
                count_managed_club_employees(
                    reader,
                    module,
                    profile,
                    &guard.records,
                    club_uid,
                )
            })
            .filter(|count| *count > 0)
            .unwrap_or_else(|| snapshot_club_employee_count(&players, &club_id))
    } else {
        snapshot_club_employee_count(&players, &club_id)
    };
    let clubs = vec![json!({
        "id": club_id,
        "name": club_name,
        "nation": null,
        "league": null
    })];
    Ok(LiveData {
        managed_club_id: club_uid.to_string(),
        manager_name,
        season,
        clubs,
        club_teams,
        players,
        tactic,
        database_players_indexed,
        background_players_indexed,
        database_index_status,
        database_scope,
        database_index_error,
        warnings,
        tactic_manager_pointer,
        club_employees,
    })
}

#[cfg(target_os = "windows")]
const TACTIC_FORMATION_CODE_OFFSET: u64 = 0x03D4;
#[cfg(target_os = "windows")]
const TACTIC_SELECTION_POINTER_OFFSETS: [u64; 3] = [0x41B8, 0x41C0, 0x41C8];

#[cfg(target_os = "windows")]
fn extract_live_tactic(
    reader: &mut ProcessReader,
    tactic_manager_pointer: u64,
    managed_records: &[IndexedPlayerRecord],
) -> Option<Value> {
    let formation_code = reader.read_u32(tactic_manager_pointer + TACTIC_FORMATION_CODE_OFFSET)?;
    let template = tactic_formation_template(formation_code)?;
    let selection = find_live_tactic_selection(
        reader,
        tactic_manager_pointer,
        managed_records,
        template.positions.len(),
    )?;
    let managed_by_person = managed_records
        .iter()
        .map(|record| (record.person_address, record))
        .collect::<HashMap<_, _>>();
    let mut slots = Vec::with_capacity(template.positions.len());
    let role_packet = find_live_tactic_role_packet(
        reader,
        tactic_manager_pointer,
        &selection,
        template.positions,
    );

    for (index, position) in template.positions.iter().enumerate() {
        let person_pointer = selection.person_pointers[index];
        let record = managed_by_person.get(&person_pointer).copied();
        let role_slot = role_packet
            .as_ref()
            .and_then(|packet| packet.slots.get(index))
            .copied();
        slots.push(json!({
            "playerId": record.map(|record| record.id.clone()),
            "position": position,
            "role": role_slot.and_then(|slot| slot.role_label),
            "roleShort": role_slot.and_then(|slot| slot.role_short_label),
            "roleMask": role_slot.and_then(|slot| slot.role_mask).map(|mask| format!("0x{mask:X}")),
            "duty": role_slot.and_then(|slot| slot.duty_label),
            "dutyShort": role_slot.and_then(|slot| slot.duty_short_label),
            "dutyMask": role_slot.and_then(|slot| slot.duty_mask).map(|mask| format!("0x{mask:X}")),
            "personPointer": if person_pointer == 0 { None } else { Some(hex_address(person_pointer)) },
            "decoderStatus": match (record.is_some(), role_slot.and_then(|slot| slot.role_label).is_some(), role_slot.and_then(|slot| slot.duty_label).is_some()) {
                (true, true, true) => "player-role-duty-validated",
                (true, true, false) => "player-role-validated-duty-pending",
                (true, false, _) => "player-slot-validated-role-pending",
                _ => "player-slot-unresolved"
            }
        }));
    }

    let role_warning = match &role_packet {
        Some(packet) if packet.duties_resolved == template.positions.len() => {
            "Packed FM26 role and duty masks validated against the active tactic slots."
        }
        Some(_) => {
            "Packed FM26 role masks validated against the active tactic slots; duty masks remain pending for this read."
        }
        None => {
            "Packed role, duty, phase-layout and instruction codes did not validate on this read, so GlassScout does not invent them."
        }
    };
    let warnings = if template.exact_shape {
        vec![
            "Formation and selected XI slots are decoded from live FM26 memory.",
            role_warning,
        ]
    } else {
        vec![
            "The FM26 formation code is known, but this formation's exact pitch slot template is not validated yet.",
            "Selected XI is decoded from live FM26 memory; pitch placement uses neutral slot labels until the formation template is mapped.",
            role_warning,
        ]
    };
    Some(json!({
        "name": null,
        "formation": template.label,
        "formationEnum": template.enum_name,
        "formationCode": formation_code,
        "slots": slots,
        "teamInstructions": [],
        "playerInstructionsReadable": false,
        "decoderStatus": match (&role_packet, template.exact_shape) {
            (Some(packet), true) if packet.duties_resolved == template.positions.len() => "formation-selected-xi-role-duty-validated",
            (Some(_), true) => "formation-selected-xi-role-validated",
            (None, true) => "formation-shape-and-selected-xi-validated",
            (Some(_), false) => "selected-xi-role-validated-template-pending",
            (None, false) => "selected-xi-validated-template-pending",
        },
        "layoutStatus": if template.exact_shape { "exact-template" } else { "formation-name-only" },
        "selectionPointer": hex_address(selection.base_address + selection.offset),
        "selectionStride": selection.stride,
        "selectionResolvedPlayers": selection.resolved_players,
        "roleDutyDecoderStatus": role_packet.as_ref().map(|packet| packet.status).unwrap_or("packet-not-validated"),
        "rolePacketPointer": role_packet.as_ref().map(|packet| hex_address(packet.base_address + packet.offset)),
        "rolePacketStride": role_packet.as_ref().map(|packet| packet.stride),
        "rolePacketWidth": role_packet.as_ref().map(|packet| packet.width),
        "rolesResolved": role_packet.as_ref().map(|packet| packet.roles_resolved).unwrap_or_default(),
        "dutiesResolved": role_packet.as_ref().map(|packet| packet.duties_resolved).unwrap_or_default(),
        "roleCatalogue": role_catalogue_status(),
        "warnings": warnings
    }))
}

#[cfg(target_os = "windows")]
struct TacticSelection {
    base_address: u64,
    offset: u64,
    stride: u64,
    person_pointers: Vec<u64>,
    resolved_players: usize,
}

#[cfg(target_os = "windows")]
#[derive(Clone, Copy)]
struct TacticRoleSlot {
    role_label: Option<&'static str>,
    role_short_label: Option<&'static str>,
    role_mask: Option<u64>,
    duty_label: Option<&'static str>,
    duty_short_label: Option<&'static str>,
    duty_mask: Option<u64>,
}

#[cfg(target_os = "windows")]
struct TacticRolePacket {
    base_address: u64,
    offset: u64,
    stride: u64,
    width: u64,
    status: &'static str,
    slots: Vec<TacticRoleSlot>,
    roles_resolved: usize,
    duties_resolved: usize,
    compatible_roles: usize,
}

#[cfg(target_os = "windows")]
fn find_live_tactic_role_packet(
    reader: &mut ProcessReader,
    tactic_manager_pointer: u64,
    selection: &TacticSelection,
    positions: &[&str],
) -> Option<TacticRolePacket> {
    let mut candidates = vec![tactic_manager_pointer, selection.base_address];
    if let Some(bytes) = reader.read_bytes(tactic_manager_pointer, 0x2000) {
        for offset in (0..bytes.len().saturating_sub(8)).step_by(8) {
            let pointer = u64::from_le_bytes(bytes[offset..offset + 8].try_into().ok()?);
            if plausible_process_pointer(pointer) {
                candidates.push(pointer);
            }
        }
    }
    candidates.sort_unstable();
    candidates.dedup();

    let mut best: Option<TacticRolePacket> = None;
    for base_address in candidates {
        let Some(bytes) = read_bounded_window(reader, base_address) else {
            continue;
        };
        for width in [8_u64, 4_u64] {
            for stride in [width, 8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x48, 0x50] {
                if stride < width {
                    continue;
                }
                let needed = (positions.len().saturating_sub(1) as u64)
                    .saturating_mul(stride)
                    .saturating_add(width) as usize;
                if bytes.len() < needed {
                    continue;
                }
                let max_start = bytes.len().saturating_sub(needed);
                for start in (0..=max_start).step_by(4) {
                    let Some(packet) = decode_role_packet_at(
                        base_address,
                        &bytes,
                        start,
                        stride,
                        width,
                        positions,
                    ) else {
                        continue;
                    };
                    let replace = best.as_ref().is_none_or(|current| {
                        packet.roles_resolved > current.roles_resolved
                            || (packet.roles_resolved == current.roles_resolved
                                && packet.duties_resolved > current.duties_resolved)
                            || (packet.roles_resolved == current.roles_resolved
                                && packet.duties_resolved == current.duties_resolved
                                && packet.compatible_roles > current.compatible_roles)
                    });
                    if replace {
                        best = Some(packet);
                    }
                }
            }
        }
    }
    best
}

#[cfg(target_os = "windows")]
fn decode_role_packet_at(
    base_address: u64,
    bytes: &[u8],
    start: usize,
    stride: u64,
    width: u64,
    positions: &[&str],
) -> Option<TacticRolePacket> {
    let mut slots = Vec::with_capacity(positions.len());
    let mut roles_resolved = 0_usize;
    let mut duties_resolved = 0_usize;
    let mut compatible_roles = 0_usize;
    let mut distinct_roles = HashSet::new();
    let mut distinct_duties = HashSet::new();

    for (index, position) in positions.iter().enumerate() {
        let offset = start + (index as u64 * stride) as usize;
        let value = read_packet_value(bytes, offset, width)?;
        let decoded = decode_role_duty_mask(value);
        if decoded.unknown_bits != 0 {
            return None;
        }
        let role = decoded
            .role
            .or_else(|| role_definition_for_mask(value & u64::from(u32::MAX)));
        let duty = decoded
            .duty
            .or_else(|| duty_definition_for_mask(value & u64::from(u32::MAX)));
        if let Some(role) = role {
            roles_resolved += 1;
            distinct_roles.insert(role.key);
            if role_supports_slot(role, position) {
                compatible_roles += 1;
            }
        }
        if let Some(duty) = duty {
            duties_resolved += 1;
            distinct_duties.insert(duty.key);
        }
        if role.is_none() && duty.is_none() {
            return None;
        }
        slots.push(TacticRoleSlot {
            role_label: role.map(|definition| definition.label),
            role_short_label: role.map(|definition| definition.short_label),
            role_mask: role.map(|definition| definition.mask),
            duty_label: duty.map(|definition| definition.label),
            duty_short_label: duty.map(|definition| definition.short_label),
            duty_mask: duty.map(|definition| definition.mask),
        });
    }

    if roles_resolved < positions.len() || compatible_roles < 7 || distinct_roles.len() < 3 {
        return None;
    }
    let status = if duties_resolved == positions.len() && distinct_duties.len() >= 2 {
        "role-duty-packet-validated"
    } else if duties_resolved == 0 {
        "role-packet-validated-duty-pending"
    } else {
        "role-packet-validated-partial-duty"
    };
    Some(TacticRolePacket {
        base_address,
        offset: start as u64,
        stride,
        width,
        status,
        slots,
        roles_resolved,
        duties_resolved,
        compatible_roles,
    })
}

#[cfg(target_os = "windows")]
fn read_packet_value(bytes: &[u8], offset: usize, width: u64) -> Option<u64> {
    match width {
        4 => bytes
            .get(offset..offset + 4)
            .and_then(|slice| slice.try_into().ok())
            .map(u32::from_le_bytes)
            .map(u64::from),
        8 => bytes
            .get(offset..offset + 8)
            .and_then(|slice| slice.try_into().ok())
            .map(u64::from_le_bytes),
        _ => None,
    }
}

#[cfg(target_os = "windows")]
fn find_live_tactic_selection(
    reader: &mut ProcessReader,
    tactic_manager_pointer: u64,
    managed_records: &[IndexedPlayerRecord],
    slot_count: usize,
) -> Option<TacticSelection> {
    let managed_people = managed_records
        .iter()
        .map(|record| record.person_address)
        .collect::<HashSet<_>>();
    let mut candidates = Vec::new();
    candidates.push(tactic_manager_pointer);
    for pointer_offset in TACTIC_SELECTION_POINTER_OFFSETS {
        if let Some(pointer) = reader
            .read_pointer(tactic_manager_pointer + pointer_offset)
            .filter(|pointer| plausible_process_pointer(*pointer))
        {
            candidates.push(pointer);
        }
    }
    if let Some(bytes) = reader.read_bytes(tactic_manager_pointer, 0x6000) {
        for offset in (0..bytes.len().saturating_sub(8)).step_by(8) {
            let pointer = u64::from_le_bytes(bytes[offset..offset + 8].try_into().ok()?);
            if plausible_process_pointer(pointer) {
                candidates.push(pointer);
            }
        }
    }
    candidates.sort_unstable();
    candidates.dedup();

    let mut best: Option<TacticSelection> = None;
    for base_address in candidates {
        let Some(bytes) = read_bounded_window(reader, base_address) else {
            continue;
        };
        for stride in [8_u64, 0x48] {
            let needed = (slot_count.saturating_sub(1) as u64)
                .saturating_mul(stride)
                .saturating_add(8) as usize;
            if bytes.len() < needed {
                continue;
            }
            let max_start = bytes.len().saturating_sub(needed);
            for start in (0..=max_start).step_by(8) {
                let mut pointers = Vec::with_capacity(slot_count);
                let mut resolved = 0_usize;
                let mut plausible = 0_usize;
                for index in 0..slot_count {
                    let offset = start + (index as u64 * stride) as usize;
                    let pointer = u64::from_le_bytes(bytes[offset..offset + 8].try_into().ok()?);
                    if plausible_process_pointer(pointer) {
                        plausible += 1;
                    }
                    if managed_people.contains(&pointer) {
                        resolved += 1;
                    }
                    pointers.push(pointer);
                }
                if resolved < 8 || plausible < 10 {
                    continue;
                }
                let replace = best
                    .as_ref()
                    .is_none_or(|current| resolved > current.resolved_players);
                if replace {
                    best = Some(TacticSelection {
                        base_address,
                        offset: start as u64,
                        stride,
                        person_pointers: pointers,
                        resolved_players: resolved,
                    });
                    if resolved == slot_count {
                        return best;
                    }
                }
            }
        }
    }
    best
}

#[cfg(target_os = "windows")]
fn read_bounded_window(reader: &mut ProcessReader, base_address: u64) -> Option<Vec<u8>> {
    for size in [0x4000_usize, 0x2000, 0x1000] {
        if let Some(bytes) = reader.read_bytes(base_address, size) {
            return Some(bytes);
        }
    }
    None
}

#[cfg(target_os = "windows")]
fn plausible_process_pointer(pointer: u64) -> bool {
    (0x10000000000..0x0000_8000_0000_0000).contains(&pointer)
}

#[cfg(target_os = "windows")]
struct IndexSummary {
    total: u32,
    background: u32,
    tactic_manager_pointer: Option<u64>,
}

#[cfg(target_os = "windows")]
fn store_player_index(
    process_id: u32,
    anchors: LiveMemoryAnchors,
    records: Vec<IndexedPlayerRecord>,
) {
    let save_pointer = anchors.save_pointer;
    let records = records
        .into_iter()
        .map(|record| (record.id.clone(), record))
        .collect();
    let index = PLAYER_DATABASE_INDEX.get_or_init(|| RwLock::new(PlayerDatabaseIndex::default()));
    if let Ok(mut index) = index.write() {
        *index = PlayerDatabaseIndex {
            process_id,
            save_pointer,
            anchors,
            records,
        };
    }
}

#[cfg(target_os = "windows")]
fn index_full_player_database(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
    process_id: u32,
    mut anchors: LiveMemoryAnchors,
    player_vtable: u64,
    module: ModuleInfo,
    managed_player_ids: &HashSet<String>,
    managed_records: Vec<IndexedPlayerRecord>,
) -> Result<IndexSummary, ExtractionFailure> {
    let mut records: HashMap<String, IndexedPlayerRecord> = managed_records
        .into_iter()
        .map(|record| (record.id.clone(), record))
        .collect();
    let tactics_manager_vtable = module.base + profile.constants.tactics_manager_vtable_rva;
    let mut object_hits =
        scan_private_memory_for_pointers(reader, &[player_vtable, tactics_manager_vtable])
            .map_err(|error| ExtractionFailure::new("player_database", error.to_string()))?;
    let candidate_addresses = object_hits.remove(&player_vtable).unwrap_or_default();
    let tactic_manager_hits = object_hits
        .remove(&tactics_manager_vtable)
        .unwrap_or_default();
    let tactic_manager_pointer = (tactic_manager_hits.len() == 1).then_some(tactic_manager_hits[0]);

    for address in candidate_addresses {
        if records.len() >= 250_000 {
            break;
        }
        let Some(mut record) = read_indexed_player_candidate(reader, address, profile) else {
            continue;
        };
        if managed_player_ids.contains(&record.id) {
            continue;
        }
        record.managed_squad = false;
        record.visibility_safe = false;
        records.entry(record.id.clone()).or_insert(record);
    }

    if records.len() < managed_player_ids.len() {
        return Err(ExtractionFailure::new(
            "player_database",
            "The wider player index failed its managed-squad integrity check.",
        ));
    }

    let total = records.len() as u32;
    let background = records
        .values()
        .filter(|record| !record.managed_squad)
        .count() as u32;
    anchors.tactic_manager_pointer = tactic_manager_pointer;
    let save_pointer = anchors.save_pointer;
    let index = PLAYER_DATABASE_INDEX.get_or_init(|| RwLock::new(PlayerDatabaseIndex::default()));
    if let Ok(mut index) = index.write() {
        *index = PlayerDatabaseIndex {
            process_id,
            save_pointer,
            anchors,
            records,
        };
    }
    Ok(IndexSummary {
        total,
        background,
        tactic_manager_pointer,
    })
}

#[cfg(target_os = "windows")]
fn read_indexed_player_candidate(
    reader: &mut ProcessReader,
    raw_player: u64,
    profile: &EntityMapProfile,
) -> Option<IndexedPlayerRecord> {
    let person = resolve_person_address(reader, raw_player, profile)?;
    let uid = reader
        .read_u32(person.checked_add(profile.constants.entity_uid_offset)?)
        .filter(|uid| is_plausible_fm_unique_id(*uid))?;
    let name = display_name(
        read_name_field(
            reader,
            person.checked_add(profile.constants.person_first_name_offset)?,
        ),
        read_name_field(
            reader,
            person.checked_add(profile.constants.person_second_name_offset)?,
        ),
        read_name_field(
            reader,
            person.checked_add(profile.constants.person_common_name_offset)?,
        ),
    )?;
    let position_bytes = reader.read_bytes(
        raw_player.checked_add(profile.constants.player_positions_offset)?,
        POSITION_NAMES.len(),
    )?;
    if position_bytes.iter().any(|rating| *rating > 20)
        || position_bytes.iter().all(|rating| *rating == 0)
    {
        return None;
    }
    let (positions, _secondary_positions) = classify_player_positions(&position_bytes);
    if positions.is_empty() {
        return None;
    }
    Some(IndexedPlayerRecord {
        id: uid.to_string(),
        name,
        positions,
        managed_squad: false,
        visibility_safe: false,
        raw_player_address: raw_player,
        person_address: person,
        contract_address: reader
            .read_pointer(person.checked_add(profile.constants.person_contract_offset)?)
            .filter(|value| *value != 0),
    })
}

fn visible_ability_score(position: &str, attributes: &HashMap<String, u8>) -> Option<u8> {
    let keys: &[&str] = match position {
        "GK" => &[
            "Aerial Reach",
            "Command of Area",
            "Communication",
            "Handling",
            "One on Ones",
            "Reflexes",
            "Positioning",
            "Decisions",
        ],
        "DC" | "SW" => &[
            "Marking",
            "Tackling",
            "Heading",
            "Positioning",
            "Anticipation",
            "Decisions",
            "Jumping Reach",
            "Strength",
        ],
        "DL" | "DR" | "WBL" | "WBR" => &[
            "Marking",
            "Tackling",
            "Positioning",
            "Crossing",
            "Pace",
            "Acceleration",
            "Stamina",
            "Work Rate",
        ],
        "DM" => &[
            "Tackling",
            "Positioning",
            "Anticipation",
            "Decisions",
            "Passing",
            "Teamwork",
            "Work Rate",
            "Stamina",
        ],
        "ML" | "MR" | "AML" | "AMR" => &[
            "Crossing",
            "Dribbling",
            "First Touch",
            "Off the Ball",
            "Pace",
            "Acceleration",
            "Agility",
            "Technique",
        ],
        "MC" | "AMC" => &[
            "Passing",
            "Vision",
            "First Touch",
            "Technique",
            "Decisions",
            "Anticipation",
            "Teamwork",
            "Work Rate",
        ],
        "ST" => &[
            "Finishing",
            "First Touch",
            "Off the Ball",
            "Anticipation",
            "Composure",
            "Acceleration",
            "Pace",
            "Technique",
        ],
        _ => &["Decisions", "Teamwork", "Work Rate", "Natural Fitness"],
    };
    let values = keys
        .iter()
        .filter_map(|key| attributes.get(*key).copied())
        .map(u32::from)
        .collect::<Vec<_>>();
    (!values.is_empty()).then(|| {
        let average = values.iter().sum::<u32>() as f32 / values.len() as f32;
        ((average / 20.0) * 100.0).round().clamp(0.0, 100.0) as u8
    })
}

fn attribute_evidence(attributes: &HashMap<String, u8>) -> (Vec<String>, Vec<String>) {
    let mut values = attributes
        .iter()
        .map(|(name, value)| (name.clone(), *value))
        .collect::<Vec<_>>();
    values.sort_by(|left, right| right.1.cmp(&left.1).then_with(|| left.0.cmp(&right.0)));
    let strengths = values
        .iter()
        .take(3)
        .map(|(name, value)| format!("{name} {value}"))
        .collect();
    let weaknesses = values
        .iter()
        .rev()
        .take(3)
        .map(|(name, value)| format!("{name} {value}"))
        .collect();
    (strengths, weaknesses)
}

fn is_leap_year(year: u16) -> bool {
    year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
}

fn month_day(date: FmDate) -> Option<(u8, u8)> {
    let mut remaining = u32::from(date.day_of_year);
    if remaining == 0 {
        return None;
    }
    let month_lengths = [
        31_u32,
        if is_leap_year(date.year) { 29 } else { 28 },
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ];
    for (index, length) in month_lengths.iter().enumerate() {
        if remaining <= *length {
            return Some(((index + 1) as u8, remaining as u8));
        }
        remaining -= length;
    }
    None
}

fn format_fm_date(date: FmDate) -> Option<String> {
    let (month, day) = month_day(date)?;
    Some(format!("{:04}-{month:02}-{day:02}", date.year))
}

fn calculate_age(birth: FmDate, current: FmDate) -> Option<u8> {
    if current.year < birth.year {
        return None;
    }
    let birthday_passed = current.day_of_year >= birth.day_of_year;
    let years = current.year - birth.year - u16::from(!birthday_passed);
    u8::try_from(years).ok().filter(|age| *age <= 100)
}

#[cfg(target_os = "windows")]
fn read_fm_date(reader: &mut ProcessReader, address: u64) -> Option<FmDate> {
    let bytes = reader.read_bytes(address, 4)?;
    let day_of_year = u16::from_le_bytes([bytes[0], bytes[1]]);
    let year = u16::from_le_bytes([bytes[2], bytes[3]]);
    let max_day = if is_leap_year(year) { 366 } else { 365 };
    (year >= 1900 && day_of_year > 0 && day_of_year <= max_day)
        .then_some(FmDate { year, day_of_year })
}

#[cfg(target_os = "windows")]
fn read_nationality(
    reader: &mut ProcessReader,
    person: u64,
    profile: &EntityMapProfile,
) -> Option<String> {
    let nation = reader.read_pointer(person + profile.constants.person_nationality_offset)?;
    let name = (nation != 0)
        .then(|| reader.read_pointer(nation + profile.constants.nation_name_offset))
        .flatten()?;
    (name != 0)
        .then(|| reader.read_length_prefixed_string(name))
        .flatten()
}

#[cfg(target_os = "windows")]
fn read_nation_id(
    reader: &mut ProcessReader,
    person: u64,
    profile: &EntityMapProfile,
) -> Option<String> {
    let nation = reader.read_pointer(person + profile.constants.person_nationality_offset)?;
    if nation == 0 {
        return None;
    }
    reader
        .read_u32(nation + profile.constants.entity_uid_offset)
        .filter(|id| *id > 0)
        .map(|id| id.to_string())
}

fn display_name(
    first_name: Option<String>,
    second_name: Option<String>,
    common_name: Option<String>,
) -> Option<String> {
    if let Some(common) = common_name.filter(|value| !value.trim().is_empty()) {
        return Some(common);
    }
    let full = [first_name, second_name]
        .into_iter()
        .flatten()
        .filter(|value| !value.trim().is_empty())
        .collect::<Vec<_>>()
        .join(" ");
    (!full.is_empty()).then_some(full)
}

fn is_plausible_fm_unique_id(uid: u32) -> bool {
    (20_000_000..=99_999_999).contains(&uid) || (1_900_000_000..=2_200_000_000).contains(&uid)
}

#[cfg(target_os = "windows")]
fn is_heap_person_pointer(value: u64) -> bool {
    (0x10_000..0x0000_7FF0_0000_0000).contains(&value) && value.is_multiple_of(8)
}

#[cfg(target_os = "windows")]
fn person_identity_valid(
    reader: &mut ProcessReader,
    person: u64,
    profile: &EntityMapProfile,
) -> bool {
    let Some(uid) = reader
        .read_u32(person + profile.constants.entity_uid_offset)
        .filter(|uid| is_plausible_fm_unique_id(*uid))
    else {
        return false;
    };
    if display_name(
        read_name_field(
            reader,
            person + profile.constants.person_first_name_offset,
        ),
        read_name_field(
            reader,
            person + profile.constants.person_second_name_offset,
        ),
        read_name_field(
            reader,
            person + profile.constants.person_common_name_offset,
        ),
    )
    .is_some()
    {
        return true;
    }
    fm_dossier::player_display_name(&uid.to_string()).is_some()
}

#[cfg(target_os = "windows")]
fn resolve_person_address(
    reader: &mut ProcessReader,
    raw_player: u64,
    profile: &EntityMapProfile,
) -> Option<u64> {
    let mapped = raw_player + profile.constants.player_person_offset;
    if person_identity_valid(reader, mapped, profile) {
        return Some(mapped);
    }
    if let Some(person_pointer) = reader
        .read_pointer(mapped)
        .filter(|value| is_heap_person_pointer(*value))
    {
        if person_identity_valid(reader, person_pointer, profile) {
            return Some(person_pointer);
        }
    }
    let scan_end = 1024u64.saturating_sub(16);
    let mut offset = profile.constants.player_person_offset;
    while offset <= scan_end {
        let candidate = raw_player + offset;
        if candidate != mapped && person_identity_valid(reader, candidate, profile) {
            return Some(candidate);
        }
        offset += 8;
    }
    None
}

#[cfg(target_os = "windows")]
fn read_name_field(reader: &mut ProcessReader, field: u64) -> Option<String> {
    reader.read_fm_string_pointer(field)
}

fn position_bytes_issue(bytes: &[u8]) -> Option<String> {
    if bytes.is_empty() {
        return Some("position blob unreadable".to_string());
    }
    if let Some((index, value)) = bytes.iter().copied().enumerate().find(|(_, rating)| *rating > 20)
    {
        return Some(format!("position byte {index} = {value} (>20)"));
    }
    if bytes.iter().all(|rating| *rating == 0) {
        return Some("all position familiarities are zero".to_string());
    }
    None
}

fn attribute_bytes_issue(bytes: &[u8]) -> Option<String> {
    if bytes.len() < PLAYER_ATTRIBUTE_NAMES.len() {
        return Some(format!(
            "attribute blob unreadable (expected {} bytes)",
            PLAYER_ATTRIBUTE_NAMES.len()
        ));
    }
    if let Some((index, value)) = bytes
        .iter()
        .copied()
        .enumerate()
        .find(|(_, rating)| *rating > 100)
    {
        let label = PLAYER_ATTRIBUTE_NAMES
            .get(index)
            .copied()
            .unwrap_or("unknown");
        return Some(format!("attribute {label} byte {index} = {value} (>100)"));
    }
    None
}

fn resolve_managed_squad_name(
    reader: &mut ProcessReader,
    person: u64,
    profile: &EntityMapProfile,
    uid: u32,
) -> (String, &'static str) {
    if let Some(name) = display_name(
        read_name_field(reader, person + profile.constants.person_first_name_offset),
        read_name_field(reader, person + profile.constants.person_second_name_offset),
        read_name_field(reader, person + profile.constants.person_common_name_offset),
    ) {
        return (name, "own-squad");
    }
    if let Some(name) = fm_dossier::player_display_name(&uid.to_string()) {
        return (name, "dossier-fallback");
    }
    (format!("Player {uid}"), "uid-fallback")
}

#[cfg(test)]
fn checked_currency_transform(raw: i64, scale: u64, maximum: u64) -> Option<u64> {
    let value = u64::try_from(raw).ok()?.checked_mul(scale)?;
    (value <= maximum).then_some(value)
}

#[cfg(test)]
fn validated_enum<'a>(raw: usize, values: &'a [&'a str]) -> Option<&'a str> {
    values.get(raw).copied()
}

fn read_executable_identity(path: &str) -> ExecutableIdentity {
    let metadata = std::fs::metadata(path).ok();
    let len = metadata.as_ref().map(|meta| meta.len()).unwrap_or(0);
    let modified = metadata
        .as_ref()
        .and_then(|meta| meta.modified().ok())
        .unwrap_or(SystemTime::UNIX_EPOCH);
    if let Ok(cache) = identity_cache().lock() {
        if let Some(hit) = cache.as_ref() {
            if hit.path == path && hit.len == len && hit.modified == modified {
                return hit.identity.clone();
            }
        }
    }

    let architecture = read_pe_architecture(path);
    let mut identity = ExecutableIdentity {
        architecture: architecture.clone(),
        ..ExecutableIdentity::default()
    };

    #[cfg(target_os = "windows")]
    {
        let escaped_path = path.replace('\'', "''");
        let script = format!(
            "$v=(Get-Item -LiteralPath '{escaped_path}').VersionInfo; [Console]::Write($v.FileVersion+'|'+$v.ProductVersion)"
        );
        if let Ok(output) = std::process::Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &script])
            .output()
        {
            if output.status.success() {
                let value = String::from_utf8_lossy(&output.stdout);
                let mut parts = value.splitn(2, '|');
                identity.file_version = parts
                    .next()
                    .map(str::trim)
                    .filter(|value| !value.is_empty())
                    .map(str::to_string);
                identity.product_version = parts
                    .next()
                    .map(str::trim)
                    .filter(|value| !value.is_empty())
                    .map(str::to_string);
            }
        }
    }

    if let Some(known_sha) = executable_sha256_for_versions(
        identity.file_version.as_deref(),
        identity.product_version.as_deref(),
        identity.architecture.as_deref(),
    ) {
        identity.sha256 = Some(known_sha.to_string());
        crate::fmt_log::load_detail("executable identity: version match (skipped full-file SHA-256)");
    } else {
        crate::fmt_log::load_detail("executable identity: hashing FM executable for exact map match");
        identity.sha256 = hash_file(path);
    }

    if let Ok(mut cache) = identity_cache().lock() {
        *cache = Some(CachedExecutableIdentity {
            path: path.to_string(),
            len,
            modified,
            identity: identity.clone(),
        });
    }
    identity
}

fn hash_file(path: &str) -> Option<String> {
    let mut file = File::open(path).ok()?;
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer).ok()?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Some(format!("{:X}", hasher.finalize()))
}

fn read_pe_architecture(path: &str) -> Option<String> {
    let mut file = File::open(Path::new(path)).ok()?;
    let mut dos_header = [0_u8; 64];
    file.read_exact(&mut dos_header).ok()?;
    if &dos_header[..2] != b"MZ" {
        return None;
    }
    let pe_offset = u32::from_le_bytes(dos_header[0x3c..0x40].try_into().ok()?) as u64;
    use std::io::{Seek, SeekFrom};
    file.seek(SeekFrom::Start(pe_offset + 4)).ok()?;
    let mut machine = [0_u8; 2];
    file.read_exact(&mut machine).ok()?;
    match u16::from_le_bytes(machine) {
        0x8664 => Some("x64".to_string()),
        0x014c => Some("x86".to_string()),
        _ => Some("unknown".to_string()),
    }
}

fn hex_address(value: u64) -> String {
    format!("0x{value:X}")
}

fn unix_milliseconds() -> String {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| duration.as_millis().to_string())
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fm26::{
        offsets::{embedded_entity_map_index, field_is_publishable, FieldDefinition},
        permissions::READ_ONLY_PROCESS_ACCESS,
    };

    #[test]
    fn active_manager_pick_prefers_largest_squad() {
        let candidates = [(12u64, "ghost"), (34u64, "active"), (8u64, "tiny")];
        let best = candidates
            .iter()
            .max_by_key(|(squad_len, _)| *squad_len)
            .map(|(_, name)| *name);
        assert_eq!(best, Some("active"));
    }

    #[test]
    fn loaned_out_flag_uses_loan_club_mismatch() {
        assert!(super::is_loaned_out_from_loan_club(Some(1150), 920));
        assert!(!super::is_loaned_out_from_loan_club(Some(920), 920));
        assert!(!super::is_loaned_out_from_loan_club(None, 920));
    }
    #[test]
    fn fm_dates_and_age_match_the_current_save_calendar() {
        let birth = FmDate {
            year: 1995,
            day_of_year: 225,
        };
        let current = FmDate {
            year: 2026,
            day_of_year: 150,
        };
        assert_eq!(format_fm_date(birth).as_deref(), Some("1995-08-13"));
        assert_eq!(format_fm_date(current).as_deref(), Some("2026-05-30"));
        assert_eq!(calculate_age(birth, current), Some(30));
    }

    #[test]
    fn hidden_and_foot_storage_values_never_enter_visible_attributes() {
        let raw = vec![50_u8; PLAYER_ATTRIBUTE_NAMES.len()];
        let attributes = visible_attribute_map(&raw);
        assert_eq!(attributes.get("Crossing"), Some(&10));
        for hidden in [
            "Dirtiness",
            "Consistency",
            "Important Matches",
            "Injury Proneness",
            "Versatility",
            "Left Foot",
            "Right Foot",
        ] {
            assert!(!attributes.contains_key(hidden));
        }
        let hidden = hidden_attribute_map(&raw);
        assert_eq!(hidden.get("Consistency"), Some(&10));
        assert_eq!(hidden.get("Injury Proneness"), Some(&10));
        assert_eq!(hidden.len(), 5);
    }

    #[test]
    fn personality_attribute_map_keeps_only_in_range_bytes() {
        let raw = [12_u8, 0, 21, 8, 15, 1, 20, 99];
        let map = personality_attribute_map(&raw);
        assert_eq!(map.get("Adaptability"), Some(&12));
        assert!(!map.contains_key("Ambition"));
        assert!(!map.contains_key("Loyalty"));
        assert_eq!(map.get("Pressure"), Some(&8));
        assert_eq!(map.get("Professionalism"), Some(&15));
        assert_eq!(map.get("Sportsmanship"), Some(&1));
        assert_eq!(map.get("Temperament"), Some(&20));
        assert!(!map.contains_key("Controversy"));
    }

    #[test]
    fn currency_and_enum_transforms_reject_invalid_values() {
        assert_eq!(
            checked_currency_transform(125_000, 1, 1_000_000_000),
            Some(125_000)
        );
        assert_eq!(checked_currency_transform(-1, 1, 1_000_000_000), None);
        assert_eq!(
            checked_currency_transform(2_000_000, 1_000, 1_000_000_000),
            None
        );
        assert_eq!(
            validated_enum(1, &["unknown", "interested", "not_interested"]),
            Some("interested")
        );
        assert_eq!(validated_enum(4, &["unknown", "interested"]), None);
    }

    #[test]
    fn candidates_cannot_cross_the_publication_confidence_gate() {
        let candidate = FieldDefinition {
            offset: Some(32),
            source: "contract".to_string(),
            value_type: "currency".to_string(),
            transform: Some("identity".to_string()),
            status: "candidate".to_string(),
            confidence: 0.94,
            validations: vec!["one observation".to_string()],
        };
        assert!(!field_is_publishable(&candidate));
        let validated = FieldDefinition {
            status: "validated".to_string(),
            confidence: 0.97,
            validations: vec!["100 players".to_string(), "two saves".to_string()],
            ..candidate
        };
        assert!(field_is_publishable(&validated));
    }

    #[test]
    fn classify_club_team_by_uid_when_name_missing() {
        assert_eq!(
            super::classify_club_team_squad_unit(None, 100, 100, 920, 920, 28),
            Some("firstTeam")
        );
        assert_eq!(
            super::classify_club_team_squad_unit(None, 200, 100, 2_000_069_496, 920, 18),
            Some("under19s")
        );
        assert_eq!(
            super::classify_club_team_squad_unit(None, 300, 100, 2_000_394_357, 920, 1),
            Some("reserves")
        );
    }

    #[test]
    #[ignore = "live FM26 RAM probe"]
    #[cfg(target_os = "windows")]
    fn debug_scan_club_teams_live() {
        let result = super::debug_scan_club_teams_impl();
        if let Ok(value) = &result {
            eprintln!("{}", serde_json::to_string_pretty(value).unwrap_or_default());
        }
        let value = result.expect("debug_scan_club_teams failed");
        assert!(!value["teams"].as_array().unwrap_or(&vec![]).is_empty());
    }
}

