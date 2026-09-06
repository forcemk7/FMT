use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::{HashMap, HashSet},
    fs::File,
    io::Read,
    path::Path,
    sync::{Mutex, OnceLock},
    time::SystemTime,
};
use tauri::Emitter;

use crate::fm26::{
    affiliate_links::{
        discover_bteam_affiliate_clubs, discover_teams_for_affiliate_club, discover_teams_for_club,
        AffiliateClubDiscovery,
    },
    memory::{ModuleInfo, ProcessReader},
    offsets::{
        executable_sha256_for_versions, find_entity_map, EntityMapProfile,
        MappingCoverage,
    },
    parser::{
        classify_player_positions, display_attribute, goalkeeper_rating_from_positions,
        hidden_attribute_map, personality_attribute_map, preferred_foot_label,
        visible_attribute_map,
    },
    permissions::{can_write_memory, READ_ONLY_PROCESS_ACCESS_LABEL},
    process::find_fm26_process,
    scanner::{parse_pattern, scan_module},
    structs::{FmDate, PLAYER_ATTRIBUTE_NAMES, POSITION_NAMES},
    validator,
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
    /// Calendar date used for age (YYYY-MM-DD) from player/squad current-date.
    game_date: Option<String>,
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
    game_date: Option<String>,
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
    /// Managed club+0x118 affiliation type census (Diagnostics).
    affiliation_types: Option<Value>,
}

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
    collect_snapshot(None).status
}

#[tauri::command]
pub fn connector_snapshot() -> ConnectorSnapshot {
    collect_snapshot(None)
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
        // Managed club / satellite squads only. Full-save player index is Loop D — parked.
        collect_snapshot(Some(&progress))
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
        game_date: None,
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
fn collect_snapshot(progress: Option<&dyn Fn(&'static str)>) -> ConnectorSnapshot {
    let compact = true;
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
    status.mapping_coverage = Vec::new();
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
                "Live FM26 read connected: active club {}, {} squad players, {} database players indexed ({} bytes read).",
                data.clubs
                    .first()
                    .and_then(|club| club.get("name"))
                    .and_then(Value::as_str)
                    .unwrap_or("the managed club"),
                data.players.len(),
                data.database_players_indexed,
                reader.bytes_read
            );
            status.warnings = data.warnings.clone();
            if let Some(report) = data.affiliation_types.as_ref() {
                let mapped = report
                    .get("mappedLinkCount")
                    .and_then(Value::as_u64)
                    .unwrap_or(0) as u32;
                let unmapped = report
                    .get("unmappedTypeBytes")
                    .and_then(Value::as_array)
                    .map(|a| a.len() as u32)
                    .unwrap_or(0);
                status.mapping_coverage.push(MappingCoverage {
                    section: "affiliationTypes".to_string(),
                    validated: mapped,
                    candidate: 0,
                    unmapped,
                });
                if let Some(lock) = report.get("loanFlagLock") {
                    if let (Some(region), Some(off), Some(on), Some(offv)) = (
                        lock.get("region").and_then(Value::as_str),
                        lock.get("offsetHex").and_then(Value::as_str),
                        lock.get("loanOnValue").and_then(Value::as_u64),
                        lock.get("loanOffValue").and_then(Value::as_u64),
                    ) {
                        status.warnings.push(format!(
                            "Affiliation Players-Go-On-Loan filter: {region}{off} on={on} off={offv} (hardcoded; feeders without loan-on skipped)."
                        ));
                    }
                }
            }
            let data_warnings = status.warnings.clone();
            status.read_pipeline = Vec::new();
            let bytes_per_player = if data.players.is_empty() {
                reader.bytes_read
            } else {
                reader.bytes_read / data.players.len()
            };
            let summary = format!(
                "{} players, {} bytes read (~{} B/player), scope={}",
                data.players.len(),
                reader.bytes_read,
                bytes_per_player,
                data.database_scope
            );
            crate::fmt_log::load_done(summary);
            ConnectorSnapshot {
                status,
                managed_club_id: Some(data.managed_club_id),
                manager_name: Some(data.manager_name),
                game_date: data.game_date,
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
                data_warnings,
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
fn collect_snapshot(_progress: Option<&dyn Fn(&'static str)>) -> ConnectorSnapshot {
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
    is_outgoing_external_loan(loan_club_uid, managed_club_uid, &HashSet::new())
}

/// Outgoing loan to an external club — not parent→B-team affiliate (pointer-graph club UIDs).
fn is_outgoing_external_loan(
    loan_club_uid: Option<u32>,
    managed_club_uid: u32,
    bteam_affiliate_club_uids: &HashSet<u32>,
) -> bool {
    match loan_club_uid {
        None => false,
        Some(uid) if uid == managed_club_uid => false,
        Some(uid) if bteam_affiliate_club_uids.contains(&uid) => false,
        Some(_) => true,
    }
}

/// Contract object ???????? employing team pointer.
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

/// Contract ??? employing club (uid + name).
#[cfg(target_os = "windows")]
fn resolve_employment_club_from_contract(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    contract: u64,
) -> Option<(u32, String)> {
    let team = resolve_contract_team(reader, profile, contract)?;
    resolve_club_from_pointer(reader, module, profile, team)
}

/// Team pointer ???????? club UniqueID when vtable-validated.
#[cfg(target_os = "windows")]
fn contract_team_club_uid(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    team: u64,
) -> Option<u32> {
    resolve_club_from_pointer(reader, module, profile, team).map(|(uid, _)| uid)
}


/// Classify same-club team from locked identity only (T201).
///
/// - Managed first team pointer / UID == club UID → `firstTeam`
/// - TeamType byte (FMScout enum @ team+0x28) → `firstTeam` / `under19s` / `reserves`
/// - Missing/unmapped TeamType → still load as `reserves` (tab label reminds to map)
#[cfg(target_os = "windows")]
fn classify_club_team_squad_unit(
    _team_name: Option<&str>,
    team: u64,
    first_team: u64,
    team_uid: u32,
    club_uid: u32,
    _roster_len: usize,
    team_type: Option<u8>,
) -> Option<&'static str> {
    if team == first_team || team_uid == club_uid {
        return Some("firstTeam");
    }
    Some(
        team_type
            .and_then(crate::fm26::affiliate_links::squad_unit_from_team_type)
            .unwrap_or("reserves"),
    )
}

#[cfg(target_os = "windows")]
fn club_team_label(
    name: &str,
    club_name: &str,
    team_type: Option<u8>,
    team_uid: u32,
) -> String {
    crate::fm26::affiliate_links::resolve_team_tab_label(name, club_name, team_type, team_uid)
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
        let Some(resolved) = resolve_person_and_player_base(reader, raw_player, profile) else {
            entries.push(json!({
                "slot": index,
                "rawPlayerPointer": hex_address(raw_player),
                "vtable": reader.read_pointer(raw_player).map(hex_address),
                "reject": "person_unresolved",
            }));
            continue;
        };
        let person = resolved.person;
        let uid = reader
            .read_u32(person + profile.constants.entity_uid_offset)
            .filter(|uid| is_plausible_fm_unique_id(*uid));
        let (name, name_source) = uid
            .map(|player_uid| resolve_managed_squad_name(reader, person, profile, player_uid))
            .unwrap_or_else(|| ("unknown".to_string(), "missing-uid"));
        entries.push(json!({
            "slot": index,
            "rawPlayerPointer": hex_address(raw_player),
            "personPointer": hex_address(person),
            "playerBasePointer": hex_address(resolved.player_base),
            "personClassDelta": person.wrapping_sub(resolved.player_base),
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
    short_name: String,
    squad_unit: &'static str,
    roster_len: usize,
    team_type: Option<u8>,
    affiliation_type: Option<u8>,
    affiliation_type_label: Option<String>,
    /// Owning club UniqueID (II/feeder may differ from player clubId stamp).
    club_id: String,
    /// Owning club display name for ME / desk chrome.
    club_name: String,
}

/// Club → Teams: validated team objects linked to the managed club (FMLE tree parity).
#[cfg(target_os = "windows")]
fn discover_managed_club_teams(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    managed_club_name: &str,
    first_team: u64,
    index_team_seeds: &HashSet<u64>,
) -> Vec<DiscoveredClubTeam> {
    let seeds: Vec<u64> = index_team_seeds.iter().copied().collect();
    let heap_anchors = [managed_club, first_team];
    let mut discovered = Vec::new();
    let managed_club_id = managed_club_uid.to_string();
    for team in discover_teams_for_club(
        reader,
        module,
        profile,
        managed_club,
        managed_club_uid,
        &heap_anchors,
        &seeds,
    ) {
        let Some(squad_unit) = classify_club_team_squad_unit(
            Some(team.name.as_str()).filter(|value| !value.trim().is_empty()),
            team.team,
            first_team,
            team.team_uid,
            managed_club_uid,
            team.roster_len,
            team.team_type,
        ) else {
            continue;
        };
        discovered.push(DiscoveredClubTeam {
            team: team.team,
            team_uid: team.team_uid,
            name: team.name.clone(),
            short_name: team.short_name.clone(),
            squad_unit,
            roster_len: team.roster_len,
            team_type: team.team_type,
            affiliation_type: None,
            affiliation_type_label: None,
            club_id: managed_club_id.clone(),
            club_name: managed_club_name.to_string(),
        });
    }
    discovered
}

fn club_teams_json(discovered: &[DiscoveredClubTeam], manager_team: u64) -> Vec<Value> {
    discovered
        .iter()
        .map(|entry| {
            json!({
                "teamUid": entry.team_uid.to_string(),
                "name": entry.name,
                "shortName": entry.short_name,
                "rosterLen": entry.roster_len,
                "squadUnit": entry.squad_unit,
                "teamType": entry.team_type,
                "affiliationType": entry.affiliation_type,
                "affiliationTypeLabel": entry.affiliation_type_label,
                "clubId": entry.club_id,
                "clubName": entry.club_name,
                "isManagerTeam": entry.team == manager_team,
            })
        })
        .collect()
}

fn merge_satellite_club_teams_json(mut base: Vec<Value>, extra: Vec<Value>) -> Vec<Value> {
    for team in extra {
        let team_uid = team.get("teamUid").and_then(Value::as_str);
        if team_uid.is_some_and(|uid| {
            base.iter()
                .any(|entry| entry.get("teamUid").and_then(Value::as_str) == Some(uid))
        }) {
            continue;
        }
        base.push(team);
    }
    base
}

/// Squad-tab separate-club reserves (II) plus Match-experience feeders (0x01 / 0x03).
///
/// II Club (0x08): keep First / largest roster only (Squad-tab reserve).
/// Feeders (0x01 Normal, 0x03 Schalke feeder byte): First + Reserves + Under-N / Youth (Match experience).
#[cfg(target_os = "windows")]
#[allow(clippy::too_many_arguments)]
fn load_bteam_affiliate_rosters(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    _managed_club_name: &str,
    first_team: u64,
    club_id: &str,
    squad_game_date: Option<FmDate>,
    affiliates: &[AffiliateClubDiscovery],
    bteam_affiliate_club_uids: &HashSet<u32>,
    managed_player_ids: &mut HashSet<String>,
    players: &mut Vec<Value>,
    skipped_squad_slots: &mut u32,
    skipped_squad_details: &mut Vec<String>,
    name_fallback_details: &mut Vec<String>,
    player_vtable: &mut Option<u64>,
) -> (usize, Vec<String>, Vec<DiscoveredClubTeam>) {
    let mut promoted = 0usize;
    let mut labels = Vec::new();
    let mut discovered_teams = Vec::new();
    crate::fmt_log::load_detail(format!(
        "affiliate clubs for roster load: {} resolved",
        affiliates.len()
    ));
    let heap_anchors = [managed_club, first_team];
    for affiliate in affiliates {
        let teams = discover_teams_for_affiliate_club(
            reader,
            module,
            profile,
            affiliate.club,
            affiliate.club_uid,
            &heap_anchors,
            Some((managed_club, managed_club_uid)),
        );
        crate::fmt_log::load_detail(format!(
            "affiliate club uid {} ({}) — {} team(s)",
            affiliate.club_uid,
            affiliate.club_name.trim(),
            teams.len()
        ));
        if teams.is_empty() {
            continue;
        }
        let mut linked_teams: Vec<_> = teams
            .into_iter()
            .filter(|team| {
                if team.team == first_team {
                    return false;
                }
                let linked_to_affiliate = reader
                    .read_pointer(team.team + profile.constants.team_club_offset)
                    .is_some_and(|linked| {
                        linked == affiliate.club
                            || reader
                                .read_u32(linked + profile.constants.entity_uid_offset)
                                .is_some_and(|uid| uid == affiliate.club_uid)
                    });
                linked_to_affiliate || team.team_uid == affiliate.club_uid
            })
            .collect();
        if linked_teams.is_empty() {
            continue;
        }

        let feeder_affiliate = matches!(affiliate.affiliation_type, Some(0x01) | Some(0x03));
        // Same Club.Teams path for II (0x08) vs feeders (0x01 / 0x03):
        // II → First only; feeders → First + Reserves + Under-N / Youth.
        if feeder_affiliate {
            linked_teams.retain(|team| {
                team.roster_len > 0
                    && matches!(
                        team
                            .team_type
                            .and_then(crate::fm26::affiliate_links::squad_unit_from_team_type),
                        Some("firstTeam") | Some("reserves") | Some("under19s")
                    )
            });
        } else if linked_teams.iter().any(|team| team.team_type == Some(0)) {
            linked_teams.retain(|team| team.team_type == Some(0));
        } else if linked_teams.len() > 1 {
            let max_roster = linked_teams
                .iter()
                .map(|team| team.roster_len)
                .max()
                .unwrap_or(0);
            linked_teams.retain(|team| team.roster_len == max_roster);
        }
        // II / satellite: force reserves unit for Squad band (2nd side).
        // Feeders: use real TeamType → firstTeam / reserves / under19s.
        for team in linked_teams {
            let squad_unit = if feeder_affiliate {
                team
                    .team_type
                    .and_then(crate::fm26::affiliate_links::squad_unit_from_team_type)
                    .unwrap_or("firstTeam")
            } else {
                "reserves"
            };
            let short = team.short_name.trim();
            let full = team.name.trim();
            // Affiliate tab/log: full FM team name (shortName is U19-only in live evidence).
            let team_label = if !full.is_empty() {
                full.to_string()
            } else if !short.is_empty() {
                short.to_string()
            } else {
                format!("Map team name (?): uid-{}", team.team_uid)
            };
            crate::fmt_log::load_detail(format!(
                "affiliate roster: {} uid {} ({}, {} players)",
                team_label.trim(),
                team.team_uid,
                squad_unit,
                team.roster_len
            ));
            discovered_teams.push(DiscoveredClubTeam {
                team: team.team,
                team_uid: team.team_uid,
                name: full.to_string(),
                short_name: short.to_string(),
                squad_unit,
                roster_len: team.roster_len,
                team_type: team.team_type,
                affiliation_type: affiliate.affiliation_type,
                affiliation_type_label: affiliate.affiliation_type_label.clone(),
                club_id: affiliate.club_uid.to_string(),
                club_name: affiliate.club_name.trim().to_string(),
            });
            labels.push(format!(
                "{} (affiliate) uid {} ({}, {} roster)",
                team_label.trim(),
                team.team_uid,
                squad_unit,
                team.roster_len
            ));
            // II / satellite stay under managed club_id (Squad structure).
            // Feeders (0x01 / 0x03) use their own club uid so HoYD/GM/Squad don't treat them as employees.
            let (roster_club_id, roster_club_uid) = if feeder_affiliate {
                (affiliate.club_uid.to_string(), affiliate.club_uid)
            } else {
                (club_id.to_string(), managed_club_uid)
            };
            promoted += load_team_roster(
                reader,
                module,
                profile,
                team.team,
                &team_label,
                squad_unit,
                team.team_uid,
                &roster_club_id,
                roster_club_uid,
                squad_game_date,
                bteam_affiliate_club_uids,
                managed_player_ids,
                players,
                skipped_squad_slots,
                skipped_squad_details,
                name_fallback_details,
                player_vtable,
            );
        }
    }
    (promoted, labels, discovered_teams)
}

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
    bteam_affiliate_club_uids: &HashSet<u32>,
    managed_player_ids: &mut HashSet<String>,
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
            bteam_affiliate_club_uids,
            managed_player_ids,
            players,
            skipped_squad_slots,
            skipped_squad_details,
            name_fallback_details,
            player_vtable,
        );
    }
    players.len().saturating_sub(before)
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
    bteam_affiliate_club_uids: &HashSet<u32>,
    managed_player_ids: &mut HashSet<String>,
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
    let resolved = match resolve_person_and_player_base(reader, raw_player, profile) {
        Some(value) => value,
        None => {
            *skipped_squad_slots += 1;
            let vtable = reader
                .read_pointer(raw_player)
                .map(hex_address)
                .unwrap_or_else(|| "unreadable".to_string());
            skipped_squad_details.push(format!(
                "{slot_label}: person unresolved @ {raw_player:#x} (vtable {vtable})"
            ));
            return;
        }
    };
    let person = resolved.person;
    let player_base = resolved.player_base;
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
        player_base + profile.constants.player_positions_offset,
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
        player_base + profile.constants.player_attributes_offset,
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
        read_fm_date(reader, player_base + profile.constants.player_current_date_offset);
    let current_date = own_current_date.or(squad_game_date);
    let age = birth_date
        .zip(current_date)
        .and_then(|(birth, current)| calculate_age(birth, current));
    let date_of_birth = birth_date.and_then(format_fm_date);
    // Season and calendar date are one pair — never emit season alone.
    let (game_date, season) = match current_date.and_then(calendar_pair) {
        Some((game_date, season)) => (Some(game_date), Some(season)),
        None => (None, None),
    };
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
    let is_regen = reader
        .read_bytes(
            person + profile.constants.person_database_origin_offset,
            1,
        )
        .and_then(|b| b.first().copied())
        .map(|byte| byte == 0);
    let current_ability = reader
        .read_u16(player_base + profile.constants.player_ca_offset)
        .filter(|value| (1..=200).contains(value));
    let potential_ability = reader
        .read_u16(player_base + profile.constants.player_pa_offset)
        .filter(|value| (1..=200).contains(value));
    let left_foot = display_attribute(attribute_bytes[24]);
    let right_foot = display_attribute(attribute_bytes[25]);
    let preferred_foot = preferred_foot_label(left_foot, right_foot);
    let height_cm = reader
        .read_bytes(player_base + profile.constants.player_height_offset, 1)
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
    let loaned_out =
        is_outgoing_external_loan(loan_club_uid, club_uid, bteam_affiliate_club_uids);
    let employment_club = contract_address
        .and_then(|contract| resolve_employment_club_from_contract(reader, module, profile, contract));
    let employment_club_uid = employment_club.as_ref().map(|(uid, _)| *uid);
    // Incoming loan: agreement lists managed club as destination, or contract employer is elsewhere.
    let loaned_in = !loaned_out
        && loan_club.is_some()
        && (loan_club_uid == Some(club_uid)
            || employment_club_uid.is_some_and(|employer_uid| employer_uid != club_uid));
    let (employer_club_id, employer_club_name) = if loaned_in {
        match employment_club {
            Some((uid, name)) if uid != club_uid => (Some(uid.to_string()), Some(name)),
            _ => (None, None),
        }
    } else {
        (None, None)
    };
    let (loan_club_id, loan_club_name) = match loan_club {
        Some((uid, name)) if uid != club_uid => (Some(uid.to_string()), Some(name)),
        _ => (None, None),
    };
    managed_player_ids.insert(player_id.clone());
    players.push(json!({
        "id": player_id,
        "name": name.clone(),
        "_season": season,
        "_gameDate": game_date,
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
        "loanedIn": loaned_in,
        "employerClubId": employer_club_id,
        "employerClubName": employer_club_name,
        "loanClubId": loan_club_id,
        "loanClubName": loan_club_name,
        "transferInterest": null,
        "loanInterest": null,
        "transferAvailable": null,
        "loanAvailable": null,
        "attributes": visible_attributes,
        "hiddenAttributes": hidden_attributes,
        "personalityAttributes": personality_attributes,
        "isRegen": is_regen,
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

    let club_id = club_uid.to_string();
    // Squad-tab separate-club reserves (II / NPL): club+0x118 type filter + T212 satellite bridge.
    let bteam_discovery =
        discover_bteam_affiliate_clubs(reader, module, profile, club, club_uid, team);
    let bteam_affiliates = &bteam_discovery.affiliates;
    let affiliate_reserve_club_uids: HashSet<u32> =
        bteam_affiliates.iter().map(|entry| entry.club_uid).collect();

    if let Some(progress) = progress {
        progress("loading_club_teams");
    }
    let mut index_team_seeds = HashSet::new();
    index_team_seeds.insert(team);
    let discovered_teams = discover_managed_club_teams(
        reader,
        module,
        profile,
        club,
        club_uid,
        &club_name,
        team,
        &index_team_seeds,
    );
    crate::fmt_log::load_detail(format!(
        "Club.Teams vector: {} same-club team(s); {} squad-tab affiliate club(s)",
        discovered_teams.len(),
        bteam_affiliates.len()
    ));
    let mut discovered_team_labels: Vec<String> = Vec::new();
    for entry in &discovered_teams {
        discovered_team_labels.push(format!(
            "{} uid {} (short={}, {}, {} roster, type={:?})",
            entry.name.trim(),
            entry.team_uid,
            if entry.short_name.trim().is_empty() {
                "—"
            } else {
                entry.short_name.trim()
            },
            entry.squad_unit,
            entry.roster_len,
            entry.team_type
        ));
    }
    let mut club_teams = club_teams_json(&discovered_teams, team);

    if let Some(progress) = progress {
        progress("loading_managed_squad");
    }

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
                if let Some(resolved) =
                    resolve_person_and_player_base(reader, raw_player, profile)
                {
                    if let Some(date) = read_fm_date(
                        reader,
                        resolved.player_base + profile.constants.player_current_date_offset,
                    ) {
                        squad_game_date = Some(date);
                        break;
                    }
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
            &affiliate_reserve_club_uids,
            &mut managed_player_ids,
            &mut players,
            &mut skipped_squad_slots,
            &mut skipped_squad_details,
            &mut name_fallback_details,
            &mut player_vtable,
        );
    }

    let skipped_squad_warning = if skipped_squad_slots > 0 {
        let mut message = format!(
            "{skipped_squad_slots} managed-squad slot(s) were skipped because identity fields were unreadable."
        );
        for detail in skipped_squad_details.iter().take(8) {
            message.push_str("\n- ");
            message.push_str(detail);
        }
        if skipped_squad_details.len() > 8 {
            message.push_str(&format!(
                "\n- … and {} more skipped slot(s)",
                skipped_squad_details.len() - 8
            ));
        }
        Some(message)
    } else {
        None
    };
    let name_fallback_warning = (!name_fallback_details.is_empty()).then(|| {
        format!(
            "{} managed-squad name(s) fell back to UID labels because live FM name strings were unreadable: {}",
            name_fallback_details.len(),
            name_fallback_details.join("; ")
        )
    });

    let mut club_squad_promoted = 0usize;
    if let Some(progress) = progress {
        progress("loading_youth_squads");
    }
    for entry in &discovered_teams {
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
            &affiliate_reserve_club_uids,
            &mut managed_player_ids,
            &mut players,
            &mut skipped_squad_slots,
            &mut skipped_squad_details,
            &mut name_fallback_details,
            &mut player_vtable,
        );
    }

    if let Some(progress) = progress {
        progress("loading_affiliate_squads");
    }
    let (bteam_promoted, bteam_labels, bteam_teams) = load_bteam_affiliate_rosters(
        reader,
        module,
        profile,
        club,
        club_uid,
        &club_name,
        team,
        &club_id,
        squad_game_date,
        &bteam_affiliates,
        &affiliate_reserve_club_uids,
        &mut managed_player_ids,
        &mut players,
        &mut skipped_squad_slots,
        &mut skipped_squad_details,
        &mut name_fallback_details,
        &mut player_vtable,
    );
    club_squad_promoted += bteam_promoted;
    for label in bteam_labels {
        discovered_team_labels.push(label);
    }
    club_teams = merge_satellite_club_teams_json(club_teams, club_teams_json(&bteam_teams, team));

    // Full-save (~235k) index is Loop D — not in production until a fast, cross-save path exists.
    let _ = (reader, module, profile, process_id, team, progress, player_vtable);
    let database_players_indexed = managed_player_ids.len() as u32;
    let background_players_indexed = 0u32;
    let database_index_status = "not_run";
    let database_scope = "managed-squad";
    let database_index_error: Option<String> = None;

    let (game_date, season) = squad_game_date
        .and_then(calendar_pair)
        .or_else(|| {
            players.iter().find_map(|player| {
                let game_date = player.get("_gameDate")?.as_str()?.to_string();
                let season = player.get("_season")?.as_str()?.to_string();
                Some((game_date, season))
            })
        })
        .map(|(game_date, season)| (Some(game_date), Some(season)))
        .unwrap_or((None, None));
    for player in &mut players {
        if let Some(object) = player.as_object_mut() {
            object.remove("_season");
            object.remove("_gameDate");
        }
    }
    let tactic: Option<Value> = None;
    let mut warnings = vec![
        "Managed-squad IDs, names, dates of birth, ages, nationality, positions, preferred foot, visible attributes, and mapped CA/PA/hidden/personality are validated for this FM26 build.".to_string(),
        "Form, match ratings, contract, wage, valuation, fitness and squad-status relationships are not yet validated for this build and remain Unknown.".to_string(),
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
    if !bteam_affiliates.is_empty() {
        warnings.push(format!(
            "{} squad-tab affiliate club(s) resolved (separate-club reserves / NPL); {} player(s) promoted from those rosters.",
            bteam_affiliates.len(),
            bteam_promoted
        ));
    }
    if let Some(report) = bteam_discovery.affiliation_type_report.as_ref() {
        if let Some(reminders) = report.get("unmappedReminders").and_then(Value::as_array) {
            for reminder in reminders {
                if let Some(text) = reminder.as_str() {
                    warnings.push(format!(
                        "{text} — seen on managed club+0x118; label in PGE when you find the partner."
                    ));
                }
            }
        }
        let mapped = report
            .get("mappedLinkCount")
            .and_then(Value::as_u64)
            .unwrap_or(0);
        let links = report.get("linkCount").and_then(Value::as_u64).unwrap_or(0);
        if links > 0 {
            warnings.push(format!(
                "Affiliation types on club+0x118: {mapped}/{links} links mapped (roster load: II 0x08 + Normal 0x01 + feeder 0x03; Good Relations/Likely Friendly excluded)."
            ));
        }
    }
    if club_squad_promoted > 0 {
        warnings.push(format!(
            "{club_squad_promoted} player(s) loaded from Club.Teams + squad-tab affiliate rosters."
        ));
    } else if discovered_team_labels.len() > 1 {
        warnings.push(format!(
            "Club.Teams discovered ({}) but no additional same-club roster loaded.",
            discovered_team_labels.join("; ")
        ));
    }
    let club_employees = snapshot_club_employee_count(&players, &club_id);
    let clubs = vec![json!({
        "id": club_id,
        "name": club_name,
        "nation": null,
        "league": null
    })];
    Ok(LiveData {
        managed_club_id: club_uid.to_string(),
        manager_name,
        game_date,
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
        tactic_manager_pointer: None,
        club_employees,
        affiliation_types: bteam_discovery.affiliation_type_report,
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

fn season_label(date: FmDate) -> String {
    let next_year = date.year.saturating_add(1);
    format!("{}/{}", date.year, next_year % 100)
}

/// Calendar YYYY-MM-DD + season label, or None if the day-of-year cannot be mapped.
/// Callers must not emit season without a formatted game date.
fn calendar_pair(date: FmDate) -> Option<(String, String)> {
    let game_date = format_fm_date(date)?;
    Some((game_date, season_label(date)))
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
    // FM DB IDs often sit below 20M (e.g. Szoboszlai 16202373). Newgens use ~2.0B.
    // Keep a floor so heap noise (0, 32762, …) stays out; person_identity_valid also requires a name.
    (1_000_000..=99_999_999).contains(&uid) || (1_900_000_000..=2_200_000_000).contains(&uid)
}

/// FSS / AppCake person-class dynamic offsets. Player block (entity-map player_*) = PLAO =
/// `person − class_offset`. `playerPersonOffset` (648 / 0x288) is the Player class value.
#[cfg(target_os = "windows")]
const PERSON_CLASS_OFFSETS_FSS: &[u64] = &[
    0x288, // Player
    0x380, // PlayerStaff
    0x100, // Staff
    0x450, // HumanManager
];

#[cfg(target_os = "windows")]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct ResolvedSquadPerson {
    person: u64,
    /// Base for entity-map `player_*` offsets (FSS PLAO).
    player_base: u64,
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
    let Some(_uid) = reader
        .read_u32(person + profile.constants.entity_uid_offset)
        .filter(|uid| is_plausible_fm_unique_id(*uid))
    else {
        return false;
    };
    display_name(
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
}

#[cfg(target_os = "windows")]
fn player_block_looks_readable(
    reader: &mut ProcessReader,
    player_base: u64,
    profile: &EntityMapProfile,
) -> bool {
    if reader
        .read_u16(player_base + profile.constants.player_ca_offset)
        .is_some_and(|ca| (1..=200).contains(&ca))
    {
        return true;
    }
    if let Some(bytes) = reader.read_bytes(
        player_base + profile.constants.player_positions_offset,
        POSITION_NAMES.len(),
    ) {
        return position_bytes_issue(&bytes).is_none();
    }
    false
}

#[cfg(target_os = "windows")]
fn person_class_offsets(profile: &EntityMapProfile) -> Vec<u64> {
    let mut offsets = Vec::with_capacity(PERSON_CLASS_OFFSETS_FSS.len() + 1);
    offsets.push(profile.constants.player_person_offset);
    for &offset in PERSON_CLASS_OFFSETS_FSS {
        if !offsets.contains(&offset) {
            offsets.push(offset);
        }
    }
    offsets
}

#[cfg(target_os = "windows")]
fn try_resolve_from_plao(
    reader: &mut ProcessReader,
    player_base: u64,
    class_offset: u64,
    profile: &EntityMapProfile,
) -> Option<ResolvedSquadPerson> {
    let person = player_base.saturating_add(class_offset);
    if person_identity_valid(reader, person, profile) {
        return Some(ResolvedSquadPerson {
            person,
            player_base,
        });
    }
    if let Some(person_pointer) = reader
        .read_pointer(person)
        .filter(|value| is_heap_person_pointer(*value))
    {
        if person_identity_valid(reader, person_pointer, profile) {
            return Some(ResolvedSquadPerson {
                person: person_pointer,
                player_base,
            });
        }
    }
    None
}

/// Resolve roster `raw_player` → person + PLAO using FSS person-class offsets.
///
/// Team player vectors usually store PLAO (Player @ +0x288). Some slots store Person
/// or PlayerStaff PLAO (+0x380); the old resolver only tried `raw + playerPersonOffset`
/// and a scan that started at that offset, so First XI PlayerStaff / person pointers
/// became silent `person_unresolved` drops.
#[cfg(target_os = "windows")]
fn resolve_person_and_player_base(
    reader: &mut ProcessReader,
    raw_player: u64,
    profile: &EntityMapProfile,
) -> Option<ResolvedSquadPerson> {
    let class_offsets = person_class_offsets(profile);

    for &class_offset in &class_offsets {
        if let Some(resolved) = try_resolve_from_plao(reader, raw_player, class_offset, profile) {
            return Some(resolved);
        }
    }

    if person_identity_valid(reader, raw_player, profile) {
        for &class_offset in &class_offsets {
            let player_base = raw_player.saturating_sub(class_offset);
            if player_base == 0 || !is_heap_person_pointer(player_base) {
                continue;
            }
            if player_block_looks_readable(reader, player_base, profile) {
                return Some(ResolvedSquadPerson {
                    person: raw_player,
                    player_base,
                });
            }
        }
        if player_block_looks_readable(reader, raw_player, profile) {
            return Some(ResolvedSquadPerson {
                person: raw_player,
                player_base: raw_player,
            });
        }
    }

    let scan_end = 1024u64.saturating_sub(16);
    let mut offset = 0u64;
    while offset <= scan_end {
        let candidate = raw_player.saturating_add(offset);
        if person_identity_valid(reader, candidate, profile) {
            if class_offsets.contains(&offset) {
                return Some(ResolvedSquadPerson {
                    person: candidate,
                    player_base: raw_player,
                });
            }
            for &class_offset in &class_offsets {
                let player_base = candidate.saturating_sub(class_offset);
                if player_base != 0
                    && is_heap_person_pointer(player_base)
                    && player_block_looks_readable(reader, player_base, profile)
                {
                    return Some(ResolvedSquadPerson {
                        person: candidate,
                        player_base,
                    });
                }
            }
            return Some(ResolvedSquadPerson {
                person: candidate,
                player_base: raw_player,
            });
        }
        if let Some(person_pointer) = reader
            .read_pointer(candidate)
            .filter(|value| is_heap_person_pointer(*value))
        {
            if person_identity_valid(reader, person_pointer, profile) {
                return Some(ResolvedSquadPerson {
                    person: person_pointer,
                    player_base: raw_player,
                });
            }
            // Nested PLAO: roster slot points at a wrapper; inner pointer is the real player block.
            for &class_offset in &class_offsets {
                if let Some(resolved) =
                    try_resolve_from_plao(reader, person_pointer, class_offset, profile)
                {
                    return Some(resolved);
                }
            }
        }
        offset += 8;
    }
    None
}

#[cfg(target_os = "windows")]
fn resolve_person_address(
    reader: &mut ProcessReader,
    raw_player: u64,
    profile: &EntityMapProfile,
) -> Option<u64> {
    resolve_person_and_player_base(reader, raw_player, profile).map(|resolved| resolved.person)
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
        if let Some((file_version, product_version)) =
            crate::fm26::executable::read_windows_file_versions(path)
        {
            crate::fmt_log::load_detail(format!(
                "executable versions: file={file_version} product={product_version}"
            ));
            identity.file_version = Some(file_version);
            identity.product_version = Some(product_version);
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
    fn bteam_affiliate_loan_is_not_outgoing_external_loan() {
        let bteam = HashSet::from([3_609_393_u32]);
        assert!(!super::is_outgoing_external_loan(Some(3_609_393), 920, &bteam));
        assert!(super::is_outgoing_external_loan(Some(1150), 920, &bteam));
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
        assert_eq!(
            calendar_pair(current),
            Some(("2026-05-30".to_string(), "2026/27".to_string()))
        );
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
            super::classify_club_team_squad_unit(None, 100, 100, 920, 920, 28, None),
            Some("firstTeam")
        );
        // Missing/unmapped TeamType still loads (reserves bucket; label reminds to map).
        assert_eq!(
            super::classify_club_team_squad_unit(None, 200, 100, 2_000_069_496, 920, 18, None),
            Some("reserves")
        );
        assert_eq!(
            super::classify_club_team_squad_unit(None, 200, 100, 2_000_069_496, 920, 18, Some(55)),
            Some("reserves")
        );
        assert_eq!(
            super::classify_club_team_squad_unit(
                Some("Leicester City"),
                200,
                100,
                2_000_778_719,
                673,
                36,
                Some(11),
            ),
            Some("under19s")
        );
    }

    #[test]
    #[cfg(target_os = "windows")]
    fn fss_person_class_offsets_match_entity_map_player_person() {
        // FSS Player class dynamic offset == entity-map playerPersonOffset (PLAO = person − 0x288).
        assert_eq!(super::PERSON_CLASS_OFFSETS_FSS[0], 0x288);
        assert_eq!(super::PERSON_CLASS_OFFSETS_FSS[1], 0x380);
        let profile = crate::fm26::offsets::embedded_entity_map_index()
            .profiles
            .first()
            .expect("profile");
        assert_eq!(profile.constants.player_person_offset, 0x288);
        assert!(super::PERSON_CLASS_OFFSETS_FSS.contains(&profile.constants.player_person_offset));
    }

    #[test]
    fn plausible_uid_accepts_sub_20m_db_ids() {
        // Liverpool First Team slot that failed T205/T207: Dominik Szoboszlai @ 16202373.
        assert!(super::is_plausible_fm_unique_id(16_202_373));
        assert!(super::is_plausible_fm_unique_id(28_091_347));
        assert!(super::is_plausible_fm_unique_id(2_000_011_147));
        assert!(!super::is_plausible_fm_unique_id(0));
        assert!(!super::is_plausible_fm_unique_id(32_762));
        assert!(!super::is_plausible_fm_unique_id(999_999));
    }
}

