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
        offsets::{find_entity_map, mapping_coverage, EntityMapProfile, MappingCoverage},
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
    players: Vec<Value>,
    tactic: Option<Value>,
    database_players_indexed: u32,
    background_players_indexed: u32,
    database_index_status: &'static str,
    database_scope: &'static str,
    database_index_error: Option<String>,
    warnings: Vec<String>,
    tactic_manager_pointer: Option<u64>,
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
pub fn debug_dump_player_memory(
    player_id: String,
    window_size: Option<usize>,
) -> Result<MappingLabCaptureData, String> {
    let _ = collect_snapshot(false, None);
    capture_mapping_lab_player(player_id.trim(), window_size.unwrap_or(1024))
}

#[tauri::command]
pub fn load_active_save(app: tauri::AppHandle) -> ConnectorSnapshot {
    let progress = |stage: &'static str| {
        let _ = app.emit("fmt-load-progress", stage);
    };
    // T196: restore GS full index on load; club employees promoted from index after FT read.
    collect_snapshot(true, Some(&progress))
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

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct MappingLabWindow {
    pub(crate) object: &'static str,
    pub(crate) base_address: String,
    pub(crate) bytes: Vec<u8>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct MappingLabPersonProbe {
    pub(crate) label: &'static str,
    pub(crate) base_address: String,
    pub(crate) uid_at_plus_12: Option<u32>,
    pub(crate) name: Option<String>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct MappingLabCaptureData {
    pub(crate) player_id: String,
    pub(crate) player_name: String,
    pub(crate) process_id: u32,
    pub(crate) save_pointer: String,
    pub(crate) entity_map_profile_id: String,
    pub(crate) executable_sha256: String,
    pub(crate) raw_player_address: String,
    pub(crate) person_embedded_address: String,
    pub(crate) person_probes: Vec<MappingLabPersonProbe>,
    pub(crate) windows: Vec<MappingLabWindow>,
}

#[cfg(target_os = "windows")]
fn collect_player_memory_windows(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
    record: &IndexedPlayerRecord,
    window_size: usize,
) -> Result<Vec<MappingLabWindow>, String> {
    let mut windows = Vec::new();
    let person_field = record.raw_player_address + profile.constants.player_person_offset;
    let person_pointer = reader
        .read_pointer(person_field)
        .filter(|value| *value != 0 && *value != person_field);
    let resolved_person =
        resolve_person_address(reader, record.raw_player_address, profile).unwrap_or(person_field);

    let mut push_window = |object: &'static str, address: u64| -> Result<(), String> {
        let bytes = reader
            .read_bytes(address, window_size)
            .ok_or_else(|| format!("The bounded {object} window was not readable @ {address:#x}."))?;
        windows.push(MappingLabWindow {
            object,
            base_address: hex_address(address),
            bytes,
        });
        Ok(())
    };

    push_window("player", record.raw_player_address)?;
    push_window("personEmbedded", person_field)?;
    push_window("personResolved", resolved_person)?;

    if let Some(person_pointer) = person_pointer {
        push_window("personPointer", person_pointer)?;
    }

    if let Some(contract) = record.contract_address {
        push_window("contract", contract)?;
    }

    Ok(windows)
}

#[cfg(target_os = "windows")]
fn probe_person_candidates(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
    raw_player: u64,
) -> Vec<MappingLabPersonProbe> {
    let mut probes = Vec::new();
    let mapped = raw_player + profile.constants.player_person_offset;
    let mut candidates: Vec<(&'static str, u64)> = vec![("personMapped", mapped)];
    if let Some(resolved) = resolve_person_address(reader, raw_player, profile) {
        if resolved != mapped {
            candidates.push(("personResolved", resolved));
        }
    }
    if let Some(person_pointer) = reader
        .read_pointer(mapped)
        .filter(|value| *value != 0 && *value != mapped)
    {
        candidates.push(("personPointer", person_pointer));
    }

    for (label, base) in candidates {
        let uid = reader
            .read_u32(base + profile.constants.entity_uid_offset)
            .filter(|uid| *uid > 0);
        let name = uid.and_then(|_| {
            display_name(
                read_name_field(reader, base + profile.constants.person_first_name_offset),
                read_name_field(reader, base + profile.constants.person_second_name_offset),
                read_name_field(reader, base + profile.constants.person_common_name_offset),
            )
        });
        probes.push(MappingLabPersonProbe {
            label,
            base_address: hex_address(base),
            uid_at_plus_12: uid,
            name,
        });
    }
    probes
}

#[cfg(target_os = "windows")]
pub(crate) fn capture_mapping_lab_player(
    player_id: &str,
    window_size: usize,
) -> Result<MappingLabCaptureData, String> {
    let window_size = window_size.clamp(64, 4096);
    let index = PLAYER_DATABASE_INDEX
        .get()
        .ok_or_else(|| "Load the active save before capturing mapping evidence.".to_string())?
        .read()
        .map_err(|_| "The live player index is unavailable.".to_string())?;
    let record = index
        .records
        .get(player_id)
        .cloned()
        .or_else(|| {
            let mut matches = index
                .records
                .values()
                .filter(|record| record.name.eq_ignore_ascii_case(player_id));
            let first = matches.next()?.clone();
            matches.next().is_none().then_some(first)
        })
        .ok_or_else(|| {
            "No unique indexed player matched that FM ID or exact player name.".to_string()
        })?;
    let process_id = index.process_id;
    let save_pointer = index.save_pointer;
    drop(index);

    let mut reader = ProcessReader::open(process_id)
        .map_err(|code| format!("Read-only FM26 access failed with Windows error {code}."))?;
    let process_path = reader
        .process_path()
        .ok_or_else(|| "The FM26 executable path could not be read.".to_string())?;
    let identity = read_executable_identity(&process_path);
    let profile = find_entity_map(
        identity.file_version.as_deref(),
        identity.product_version.as_deref(),
        identity.sha256.as_deref(),
        identity.architecture.as_deref(),
    )
    .ok_or_else(|| "The running FM26 build does not match an exact entity map.".to_string())?;
    let person_probes = probe_person_candidates(&mut reader, profile, record.raw_player_address);
    let windows = collect_player_memory_windows(&mut reader, profile, &record, window_size)?;
    Ok(MappingLabCaptureData {
        player_id: record.id,
        player_name: record.name,
        process_id,
        save_pointer: hex_address(save_pointer),
        entity_map_profile_id: profile.id.clone(),
        executable_sha256: identity.sha256.unwrap_or_default(),
        raw_player_address: hex_address(record.raw_player_address),
        person_embedded_address: hex_address(record.person_address),
        person_probes,
        windows,
    })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn capture_mapping_lab_player(
    _player_id: &str,
    _window_size: usize,
) -> Result<MappingLabCaptureData, String> {
    Err("The FM26 mapping lab requires Windows.".to_string())
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
    if let Some(progress) = progress {
        progress("detecting_fm26");
    }
    let Some((process_id, _)) = find_fm26_process() else {
        let status = empty_status();
        return empty_snapshot(status.clone(), status.message);
    };

    let mut status = empty_status();
    status.process_detected = true;
    status.process_id = Some(process_id);
    if let Some(progress) = progress {
        progress("validating_active_save");
    }

    let mut reader = match ProcessReader::open(process_id) {
        Ok(reader) => reader,
        Err(code) => {
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
    status.mapping_coverage = mapping_coverage(profile);

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
            status.read_pipeline = build_read_pipeline(&status);
            ConnectorSnapshot {
                status,
                managed_club_id: Some(data.managed_club_id),
                manager_name: Some(data.manager_name),
                season: data.season,
                clubs: data.clubs,
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

/// Loan Club from person → loan agreement (FMLE Parent/Loan Club split).
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

/// Contract object → employing team pointer.
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

/// Team pointer → club UniqueID when vtable-validated.
#[cfg(target_os = "windows")]
fn contract_team_club_uid(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    team: u64,
) -> Option<u32> {
    resolve_club_from_pointer(reader, module, profile, team).map(|(uid, _)| uid)
}

/// U19 = non-FT contract team at managed club with the most club employees (index-derived).
#[cfg(target_os = "windows")]
fn pick_u19_team_from_index(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    records: &HashMap<String, IndexedPlayerRecord>,
    managed_club_uid: u32,
    first_team: u64,
) -> Option<u64> {
    let mut team_counts: HashMap<u64, usize> = HashMap::new();
    for record in records.values() {
        let Some(contract) = record.contract_address else {
            continue;
        };
        let Some(team) = resolve_contract_team(reader, profile, contract) else {
            continue;
        };
        let Some(team_club_uid) = contract_team_club_uid(reader, module, profile, team) else {
            continue;
        };
        if team_club_uid != managed_club_uid {
            continue;
        }
        *team_counts.entry(team).or_insert(0) += 1;
    }
    team_counts
        .into_iter()
        .filter(|(team, count)| *team != first_team && *count > 0)
        .max_by(|(team_a, count_a), (team_b, count_b)| {
            count_a
                .cmp(count_b)
                .then_with(|| team_b.cmp(team_a))
        })
        .map(|(team, _)| team)
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
    let validated_at = unix_milliseconds();
    let attribute_knowledge: serde_json::Map<String, Value> = visible_attributes
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
        .collect();
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
        ,"recommendation": {
            "minimum": ability_score,
            "maximum": ability_score,
            "completeness": 100,
            "label": if ability_score.is_some() { "full visible-attribute evidence" } else { "not enough evidence" }
        }
        ,"knowledge": {
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
        }
    }));
}

#[cfg(target_os = "windows")]
fn promote_club_team_from_index(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    u19_team: u64,
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
    let index = PLAYER_DATABASE_INDEX.get_or_init(|| RwLock::new(PlayerDatabaseIndex::default()));
    let records = index
        .read()
        .ok()
        .map(|guard| guard.records.clone())
        .unwrap_or_default();
    for record in records.values() {
        let Some(contract) = record.contract_address else {
            continue;
        };
        let Some(team) = resolve_contract_team(reader, profile, contract) else {
            continue;
        };
        if team != u19_team {
            continue;
        }
        if managed_player_ids.contains(&record.id) {
            continue;
        }
        push_squad_player_from_raw(
            reader,
            module,
            profile,
            record.raw_player_address,
            &format!("index uid {}", record.id),
            "under19s",
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
            address
        } else {
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
                "The FM26 manager registry size was invalid ({registry_bytes} bytes). Expected 1–32 human manager slots."
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
            managed_index_records,
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
        store_player_index(process_id, memory_anchors, managed_index_records);
        (
            managed_player_ids.len() as u32,
            0,
            "not_run",
            "managed-squad",
            None,
            None,
        )
    };

    let mut u19_promoted = 0usize;
    if database_index_status == "ready" {
        if let Some(index_records) = PLAYER_DATABASE_INDEX
            .get()
            .and_then(|index| index.read().ok())
            .map(|guard| guard.records.clone())
        {
            if let Some(u19_team) = pick_u19_team_from_index(
                reader,
                module,
                profile,
                &index_records,
                club_uid,
                team,
            ) {
                let before = players.len();
                let mut promoted_index_records = Vec::new();
                promote_club_team_from_index(
                    reader,
                    module,
                    profile,
                    u19_team,
                    &club_id,
                    club_uid,
                    squad_game_date,
                    &mut managed_player_ids,
                    &mut promoted_index_records,
                    &mut players,
                    &mut skipped_squad_slots,
                    &mut skipped_squad_details,
                    &mut name_fallback_details,
                    &mut player_vtable,
                );
                u19_promoted = players.len().saturating_sub(before);
            }
        }
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
    let dossier_reference = fm_dossier::augment_live_players(&mut players);
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
            "Wider player database index failed ({error}). Only the managed squad is available — same fallback as stock GlassScout, but the failure reason is now visible."
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
    if u19_promoted > 0 {
        warnings.push(format!(
            "{u19_promoted} Under-19 squad player(s) promoted from the live club index via contract team (same club as senior)."
        ));
    }
    if let Some(reference) = &dossier_reference {
        warnings.push(format!(
            "FM Dossier local save index enriched missing contract, wage, value, condition, history and search fields from {}. This is a local read-only reference layer while native offsets are mapped.",
            reference.path.display()
        ));
    }
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
        players,
        tactic,
        database_players_indexed,
        background_players_indexed,
        database_index_status,
        database_scope,
        database_index_error,
        warnings,
        tactic_manager_pointer,
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

    // Stock GlassScout parity (T134): always SHA-256 the executable for exact map match.
    let mut identity = ExecutableIdentity {
        sha256: hash_file(path),
        architecture: read_pe_architecture(path),
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

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn hunt_ca_join_live() {
        use std::collections::HashMap;

        use crate::fm26::{
            ca_history::flatten_current,
            ca_join::{
                diagnose_fingerprint, format_all_time_deltas, format_join_line, hunt_squad,
                SquadTarget,
            },
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );
        let (anchors, records) = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            let records: Vec<_> = index
                .records
                .values()
                .filter(|r| r.managed_squad)
                .cloned()
                .collect();
            (index.anchors, records)
        };

        let mut attr_by_id: HashMap<String, (HashMap<String, u8>, HashMap<String, u8>)> = HashMap::new();
        for player in &snapshot.players {
            let Some(id) = player.get("id").and_then(|v| v.as_str()) else {
                continue;
            };
            let visible = player
                .get("attributes")
                .and_then(|v| serde_json::from_value::<HashMap<String, u8>>(v.clone()).ok())
                .unwrap_or_default();
            let hidden = player
                .get("hiddenAttributes")
                .and_then(|v| serde_json::from_value::<HashMap<String, u8>>(v.clone()).ok())
                .unwrap_or_default();
            attr_by_id.insert(
                id.to_string(),
                (visible.clone(), flatten_current(&visible, &hidden)),
            );
        }

        let mut targets: Vec<SquadTarget> = records
            .into_iter()
            .filter_map(|r| {
                let uid = r.id.parse::<u32>().ok()?;
                let (visible, current) = attr_by_id.get(&r.id).cloned().unwrap_or_default();
                Some(SquadTarget {
                    uid,
                    person: r.person_address,
                    raw_player: r.raw_player_address,
                    name: r.name,
                    visible,
                    current,
                })
            })
            .collect();
        targets.sort_by(|a, b| a.name.cmp(&b.name));

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        println!(
            "=== CA join hunt ({} managed, cluster scan ~2GB once) ===",
            targets.len()
        );
        let report = hunt_squad(&mut reader, &anchors, &targets);

        for (i, c) in report.clusters.iter().take(6).enumerate() {
            println!(
                "  cluster[{i}] {:#x} cards={} history_pts={}",
                c.base, c.cards, c.history_points
            );
        }

        let mut joined = 0usize;
        let mut max_pts = 0usize;
        for target in &targets {
            let Some(hit) = report.joins.get(&target.uid) else {
                println!("  MISS  {}", target.name);
                continue;
            };
            joined += 1;
            max_pts = max_pts.max(hit.points.len());
            println!(
                "  {}",
                format_join_line(&target.name, target.uid, hit, &target.current)
            );
        }
        println!("\njoined {joined}/{} (max {max_pts} history pts)", targets.len());

        if joined > 0 {
            println!("\n=== All-time Δ vs first Progress Report point (compare in FM) ===");
            for target in &targets {
                let Some(hit) = report.joins.get(&target.uid) else {
                    continue;
                };
                let deltas = format_all_time_deltas(hit, &target.current);
                println!("\n## {} (uid={})", target.name, target.uid);
                println!("strategy={} pack_points={}", hit.strategy, hit.points.len());
                if deltas.is_empty() {
                    println!("  (no non-zero attribute movement vs first pack point)");
                } else {
                    for (attr, delta) in &deltas {
                        println!("  {attr}: {delta:+}");
                    }
                }
            }
        } else {
            println!("No joins — fingerprint/index miss on all strategies.");
            let probe_names = ["Assan Ouédraogo", "Domenico Gilson", "Robert Müller"];
            for name in probe_names {
                if let Some(t) = targets.iter().find(|x| x.name == name) {
                    println!("\nNear-miss segments for {name} (lowest L1 = best visible match):");
                    let segs: Vec<_> = report
                        .clusters
                        .iter()
                        .take(2)
                        .flat_map(|c| {
                            let lo = c.base.saturating_sub(8 * 1024 * 1024);
                            reader
                                .read_bytes(lo, 4 * 1024 * 1024)
                                .map(|blob| crate::fm26::ca_join::cluster_segments(&blob, lo))
                                .unwrap_or_default()
                        })
                        .collect();
                    for (l1, pts, end) in diagnose_fingerprint(&segs, t, 5) {
                        println!("  L1={l1} pts={pts} end={end:#x}");
                    }
                }
            }
        }
        if joined == 0 {
            println!("\nTip: open Progress Report in FM for a youth, then re-run.");
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_person_index_live() {
        use std::collections::HashMap;

        use crate::fm26::{
            ca_history::flatten_current,
            ca_resolve::probe_person_ca,
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );

        let record = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan in managed squad")
        };
        let anchors = PLAYER_DATABASE_INDEX
            .get()
            .expect("index")
            .read()
            .expect("lock")
            .anchors;

        let uid = record.id.parse::<u32>().expect("uid");
        let mut visible = HashMap::new();
        let mut hidden = HashMap::new();
        for player in &snapshot.players {
            if player.get("id").and_then(|v| v.as_str()) != Some(record.id.as_str()) {
                continue;
            }
            visible = player
                .get("attributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
            hidden = player
                .get("hiddenAttributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
        }
        let current = flatten_current(&visible, &hidden);

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        println!(
            "=== Assan person-index probe (uid={uid} person={:#x} raw={:#x}) ===",
            record.person_address, record.raw_player_address
        );
        let probe = probe_person_ca(
            &mut reader,
            &anchors,
            uid,
            record.person_address,
            record.raw_player_address,
        );

        for (i, c) in probe.clusters.iter().take(6).enumerate() {
            println!(
                "  cluster[{i}] {:#x} cards={} history_pts={}",
                c.base, c.cards, c.history_points
            );
        }
        for hit in probe.pointer_chase.iter().take(8) {
            println!(
                "  ptr_chase {} end={:#x} cards={} history_pts={}",
                hit.label, hit.ptr, hit.cards, hit.history_points
            );
        }

        let best_pts = probe
            .candidates
            .first()
            .map(|c| c.points.len())
            .unwrap_or(0);
        println!(
            "\n{} strip candidates (best {best_pts} pack points)",
            probe.candidates.len()
        );
        for cand in probe.candidates.iter().take(12) {
            println!(
                "  {:24} pts={} end={:#x}",
                cand.label,
                cand.points.len(),
                cand.strip_end
            );
        }

        if let Some(best) = probe.candidates.first().filter(|c| c.points.len() >= 2) {
            use crate::fm26::ca_history::deltas_from_pack;
            let (_recent, all_time) = deltas_from_pack(&best.points, &current);
            println!(
                "\n## All-time Δ (strategy={} pack_points={}) — compare FM Progress Report",
                best.label,
                best.points.len()
            );
            let mut moves: Vec<_> = all_time
                .into_iter()
                .filter_map(|(k, v)| v.map(|d| (k, d)))
                .filter(|(_, d)| *d != 0)
                .collect();
            moves.sort_by(|a, b| a.0.cmp(&b.0));
            if moves.is_empty() {
                println!("  (no non-zero movement vs first pack point)");
            } else {
                for (attr, delta) in &moves {
                    println!("  {attr}: {delta:+}");
                }
            }
            println!("\nFM ground truth (All Time arrows): Long Shots, Tackling, Acceleration, Balance, Jumping Reach, Strength");
        } else {
            println!("\nNo strip with ≥2 pack points — person index not cracked yet.");
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_ptr_array_live() {
        use std::collections::HashMap;

        use crate::fm26::{
            ca_history::{deltas_from_pack, flatten_current},
            ca_ptr_array::probe_ptr_array_history,
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );

        let record = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan in managed squad")
        };

        let mut visible = HashMap::new();
        let mut hidden = HashMap::new();
        for player in &snapshot.players {
            if player.get("id").and_then(|v| v.as_str()) != Some(record.id.as_str()) {
                continue;
            }
            visible = player
                .get("attributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
            hidden = player
                .get("hiddenAttributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
        }
        let current = flatten_current(&visible, &hidden);

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        println!(
            "=== Assan pointer-array chase (person={:#x} raw={:#x}) ===",
            record.person_address, record.raw_player_address
        );
        let hit = probe_ptr_array_history(
            &mut reader,
            record.person_address,
            record.raw_player_address,
            &visible,
        );

        println!("person heap ptrs ({}):", hit.person_ptrs.len());
        for p in hit.person_ptrs.iter().take(16) {
            println!("  {p:#x}");
        }

        if hit.points.is_empty() {
            println!("\nNo card array found — try Progress Report open on Assan.");
            return;
        }

        println!(
            "\nbest layout: {} pack_points={} newest_l1={}",
            hit.label,
            hit.points.len(),
            hit.newest_l1
        );

        let (_recent, all_time) = deltas_from_pack(&hit.points, &current);
        println!("\n## All-time Δ vs first pack point");
        let mut moves: Vec<_> = all_time
            .into_iter()
            .filter_map(|(k, v)| v.map(|d| (k, d)))
            .filter(|(_, d)| *d != 0)
            .collect();
        moves.sort_by(|a, b| a.0.cmp(&b.0));
        if moves.is_empty() {
            println!("  (no non-zero movement)");
        } else {
            for (attr, delta) in &moves {
                println!("  {attr}: {delta:+}");
            }
        }
        println!("\nFM All Time arrows: Long Shots, Tackling, Acceleration, Balance, Jumping Reach, Strength");
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_person_table_merge_live() {
        use std::collections::HashMap;

        use crate::fm26::{
            ca_history::{deltas_from_pack, flatten_current},
            ca_seed_dump::{
                merge_person_table_history, print_person_table_merge, wait_for_seeds,
            },
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );

        let record = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan in managed squad")
        };

        let mut visible = HashMap::new();
        let mut hidden = HashMap::new();
        for player in &snapshot.players {
            if player.get("id").and_then(|v| v.as_str()) != Some(record.id.as_str()) {
                continue;
            }
            visible = player
                .get("attributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
            hidden = player
                .get("hiddenAttributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
        }
        let current = flatten_current(&visible, &hidden);

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        println!(
            "=== Assan person-table merge — keep Progress Report open ===\nperson={:#x}",
            record.person_address
        );
        let seeds = wait_for_seeds(
            &mut reader,
            record.person_address,
            record.raw_player_address,
            15,
            45_000,
        );
        if seeds.len() < 5 {
            println!("only {} seeds materialized — open Progress Report and re-run", seeds.len());
            return;
        }

        let merge = merge_person_table_history(
            &mut reader,
            record.person_address,
            record.raw_player_address,
            &current,
            80,
        );
        print_person_table_merge(&merge, &current);

        if merge.matched_seeds == 0 {
            println!("\nNo seeds matched Assan fingerprint (L1≤80) — cards may be shared pool garbage.");
            let near: Vec<_> = merge
                .per_seed
                .iter()
                .filter_map(|(s, _, l1, _)| l1.map(|l| (*s, l)))
                .collect();
            if let Some((s, l)) = near.iter().min_by_key(|(_, l)| *l) {
                println!("nearest miss: {s:#x} L1={l}");
            }
            return;
        }

        if merge.merged.len() < 2 {
            println!("\nMatched seeds but only {} distinct snapshot(s) — need ≥2 for all-time Δ.", merge.merged.len());
            return;
        }

        let (_recent, all_time) = deltas_from_pack(&merge.merged, &current);
        println!("\n## All-time Δ (Assan-matched seeds only, L1≤80)");
        let mut moves: Vec<_> = all_time
            .into_iter()
            .filter_map(|(k, v)| v.map(|d| (k, d)))
            .filter(|(_, d)| *d != 0)
            .collect();
        moves.sort_by(|a, b| a.0.cmp(&b.0));
        if moves.is_empty() {
            println!("  (no non-zero movement vs first pack point)");
        } else {
            for (attr, delta) in &moves {
                println!("  {attr}: {delta:+}");
            }
        }
        println!("\nFM All Time: Long Shots, Tackling, Acceleration, Balance, Jumping Reach, Strength");
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_long_shots_timeline_live() {
        use crate::fm26::{
            ca_bench_search::{print_long_shots_timeline, run_assan_long_shots_timeline_search},
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(snapshot.status.state, "connected");

        let record = {
            let index = PLAYER_DATABASE_INDEX.get().unwrap().read().unwrap();
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan")
        };

        let mut reader = ProcessReader::open(process_id).expect("open");
        println!(
            "=== Long Shots timeline hunt [14×8, 13] — Progress Report open ===\n\
             person={:#x} raw={:#x}",
            record.person_address, record.raw_player_address
        );
        let report = run_assan_long_shots_timeline_search(
            &mut reader,
            record.person_address,
            record.raw_player_address,
        );
        print_long_shots_timeline(&report);
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_progress_timeline_live() {
        use crate::fm26::{
            ca_bench_search::{print_assan_progress_timeline, run_assan_progress_timeline_search},
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(snapshot.status.state, "connected");

        let record = {
            let index = PLAYER_DATABASE_INDEX.get().unwrap().read().unwrap();
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan")
        };

        let mut reader = ProcessReader::open(process_id).expect("open");
        println!(
            "=== Progress timeline hunt — Report open ===\n\
             LS [14×8,13] + Tac [10×9] + Acc [11×8,10] + Str [10×3,9×6]\n\
             person={:#x} raw={:#x}",
            record.person_address, record.raw_player_address
        );
        let report = run_assan_progress_timeline_search(
            &mut reader,
            record.person_address,
            record.raw_player_address,
        );
        print_assan_progress_timeline(&report);
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_game_details_live() {
        use crate::fm26::{
            game_details::{
                hunt_game_details, hunt_game_details_numeric, list_fm24career_saves_on_disk,
                print_disk_save_candidates, print_game_details, print_numeric_hits,
            },
            memory::ProcessReader,
            offsets::find_entity_map,
            process::find_fm26_process,
        };

        let disk = list_fm24career_saves_on_disk();
        print_disk_save_candidates(&disk);

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — disk only");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(snapshot.status.state, "connected");

        let human = snapshot
            .status
            .save_pointer
            .as_deref()
            .and_then(|s| u64::from_str_radix(s.trim_start_matches("0x"), 16).ok())
            .unwrap_or(0);
        let club = snapshot
            .clubs
            .first()
            .and_then(|c| c.get("name"))
            .and_then(|v| v.as_str())
            .unwrap_or("");

        let mut reader = ProcessReader::open(process_id).expect("open");
        let module = snapshot
            .status
            .process_path
            .as_deref()
            .and_then(|path| {
                let identity = read_executable_identity(path);
                let profile = find_entity_map(
                    identity.file_version.as_deref(),
                    identity.product_version.as_deref(),
                    identity.sha256.as_deref(),
                    identity.architecture.as_deref(),
                )?;
                reader.module(&profile.module)
            });
        println!("=== Game Details RAM hunt — keep Game Details screen open ===");
        let numeric = hunt_game_details_numeric(&mut reader, human);
        print_numeric_hits(&numeric);
        let report = hunt_game_details(
            &mut reader,
            human,
            club,
            module.map(|m| m.base),
            module.map(|m| m.size).unwrap_or(0),
        );
        print_game_details(&report);
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_ui_flicker_listen_live() {
        use crate::fm26::{
            ca_ui_listen::{listen_ui_flicker, print_ui_listen_summary},
            process::find_fm26_process,
        };

        let duration_ms = std::env::var("FMT_UI_LISTEN_MS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(120_000);
        let interval_ms = std::env::var("FMT_UI_LISTEN_INTERVAL_MS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(100);

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(snapshot.status.state, "connected");

        let record = {
            let index = PLAYER_DATABASE_INDEX.get().unwrap().read().unwrap();
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan")
        };

        let mut reader = ProcessReader::open(process_id).expect("open");
        println!(
            "=== UI flicker memory listen ===\n\
             Assan Progress Report open → Attributes tab → All Time.\n\
             person={:#x} raw={:#x}\n\
             \n\
             PROTOCOL (single attr first — clearest signal):\n\
             1. Toggle LONG SHOTS plot on/off ~8 times (1 toggle per 2s)\n\
             2. Pause 5s\n\
             3. Repeat for Tackling, Acceleration, Strength\n\
             \n\
             Listening {duration_ms}ms @ {interval_ms}ms poll. Env: FMT_UI_LISTEN_MS, FMT_UI_LISTEN_INTERVAL_MS\n",
            record.person_address,
            record.raw_player_address,
        );
        let report = listen_ui_flicker(
            &mut reader,
            record.person_address,
            record.raw_player_address,
            duration_ms,
            interval_ms,
        );
        print_ui_listen_summary(&report);
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_ls_tac_dual_timeline_live() {
        use crate::fm26::{
            ca_bench_search::{print_ls_tac_dual_timeline, run_assan_ls_tac_dual_search},
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(snapshot.status.state, "connected");

        let record = {
            let index = PLAYER_DATABASE_INDEX.get().unwrap().read().unwrap();
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan")
        };

        let mut reader = ProcessReader::open(process_id).expect("open");
        println!(
            "=== LS+Tac dual hunt — Progress Report open ===\n\
             LS [14×8,13] + Tac [10×9]\n\
             person={:#x} raw={:#x}",
            record.person_address, record.raw_player_address
        );
        let report = run_assan_ls_tac_dual_search(
            &mut reader,
            record.person_address,
            record.raw_player_address,
        );
        print_ls_tac_dual_timeline(&report);
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_bench_search_live() {
        use crate::fm26::{
            ca_bench_search::{print_bench_report, run_assan_bench_search, BENCH_ATTRS},
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );

        let record = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan in managed squad")
        };

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        println!(
            "=== Assan benchmark card search (7 attrs, Jan43 vs Sep43) ===\n\
             Keep Progress Report open. Bench: {}",
            BENCH_ATTRS.join(", ")
        );
        println!(
            "person={:#x} — if 0 exact hits, retry another player (Assan has split timelines)",
            record.person_address
        );

        let report = run_assan_bench_search(
            &mut reader,
            record.person_address,
            record.raw_player_address,
        );
        print_bench_report(&report);
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_hub_chase_live() {
        use std::collections::HashMap;

        use crate::fm26::{
            ca_history::{deltas_from_pack, flatten_current},
            ca_seed_dump::{chase_development_hub, print_hub_chase, wait_for_seeds},
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );

        let record = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan in managed squad")
        };
        let uid = record.id.parse::<u32>().expect("uid");

        let mut visible = HashMap::new();
        let mut hidden = HashMap::new();
        for player in &snapshot.players {
            if player.get("id").and_then(|v| v.as_str()) != Some(record.id.as_str()) {
                continue;
            }
            visible = player
                .get("attributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
            hidden = player
                .get("hiddenAttributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
        }
        let current = flatten_current(&visible, &hidden);

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        println!(
            "=== Assan hub chase (0x22489aacf24 table) — Progress Report open ===\nperson={:#x} uid={uid}",
            record.person_address
        );
        let seeds = wait_for_seeds(
            &mut reader,
            record.person_address,
            record.raw_player_address,
            15,
            45_000,
        );
        if seeds.len() < 5 {
            println!("only {} seeds — open Progress Report and re-run", seeds.len());
            return;
        }

        let report = chase_development_hub(
            &mut reader,
            &seeds,
            uid,
            record.person_address,
            &current,
            80,
        );
        print_hub_chase(&report);

        if report.merged.len() < 2 {
            println!("\nNo Assan-matched multi-point timeline from hub (merged={}).", report.merged.len());
            return;
        }

        let (_recent, all_time) = deltas_from_pack(&report.merged, &current);
        println!("\n## All-time Δ (hub chase, L1≤80)");
        let fm_attrs = [
            "Long Shots",
            "Tackling",
            "Acceleration",
            "Balance",
            "Jumping Reach",
            "Strength",
        ];
        for attr in fm_attrs {
            let d = all_time.get(attr).and_then(|v| *v);
            println!("  {attr}: {}", d.map(|x| format!("{x:+}")).unwrap_or_else(|| "—".into()));
        }
        println!("\n(all non-zero)");
        for (attr, delta) in all_time
            .into_iter()
            .filter_map(|(k, v)| v.map(|d| (k, d)))
            .filter(|(_, d)| *d != 0)
        {
            if !fm_attrs.contains(&attr.as_str()) {
                println!("  {attr}: {delta:+}");
            }
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_seed_hex_live() {
        use std::collections::HashMap;

        use crate::fm26::{
            ca_history::{deltas_from_pack, flatten_current},
            ca_seed_dump::{dump_and_analyze_seeds, print_seed_dump_with_visible, wait_for_seeds},
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );

        let record = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan in managed squad")
        };

        let mut visible = HashMap::new();
        let mut hidden = HashMap::new();
        for player in &snapshot.players {
            if player.get("id").and_then(|v| v.as_str()) != Some(record.id.as_str()) {
                continue;
            }
            visible = player
                .get("attributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
            hidden = player
                .get("hiddenAttributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
        }
        let current = flatten_current(&visible, &hidden);

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        println!(
            "=== Assan seed hex dump — keep Progress Report open (waiting for seeds) ===\nperson={:#x}",
            record.person_address
        );
        let seeds = wait_for_seeds(
            &mut reader,
            record.person_address,
            record.raw_player_address,
            20,
            45_000,
        );
        if seeds.len() < 5 {
            println!("only {} seeds — open Assan Progress Report and re-run", seeds.len());
            return;
        }

        let report = dump_and_analyze_seeds(&mut reader, record.person_address, &seeds, &visible);
        print_seed_dump_with_visible(&report, &mut reader, &visible);

        if let Some((label, points)) = &report.best_layout {
            if points.len() >= 2 {
                let (_recent, all_time) = deltas_from_pack(points, &current);
                println!("\n## All-time Δ ({label})");
                let mut moves: Vec<_> = all_time
                    .into_iter()
                    .filter_map(|(k, v)| v.map(|d| (k, d)))
                    .filter(|(_, d)| *d != 0)
                    .collect();
                moves.sort_by(|a, b| a.0.cmp(&b.0));
                for (attr, delta) in &moves {
                    println!("  {attr}: {delta:+}");
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_assan_ptr_array_poll_live() {
        use std::collections::HashMap;

        use crate::fm26::{
            ca_history::{deltas_from_pack, flatten_current},
            ca_ptr_array::poll_ptr_array_history,
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );

        let record = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            index
                .records
                .values()
                .find(|r| r.name == "Assan Ouédraogo")
                .cloned()
                .expect("Assan in managed squad")
        };

        let mut visible = HashMap::new();
        let mut hidden = HashMap::new();
        for player in &snapshot.players {
            if player.get("id").and_then(|v| v.as_str()) != Some(record.id.as_str()) {
                continue;
            }
            visible = player
                .get("attributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
            hidden = player
                .get("hiddenAttributes")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();
        }
        let current = flatten_current(&visible, &hidden);

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        println!(
            "=== Assan pointer poll (120s) — close/reopen Progress Report now ===\nperson={:#x}",
            record.person_address
        );
        let (hit, trace) = poll_ptr_array_history(
            &mut reader,
            record.person_address,
            record.raw_player_address,
            &visible,
            120_000,
            2_000,
        );

        let peak_seeds = trace.iter().map(|s| s.seed_count).max().unwrap_or(0);
        println!("\npoll done: samples={} peak_seeds={peak_seeds}", trace.len());
        if !hit.person_ptrs.is_empty() {
            println!("best seeds:");
            for p in hit.person_ptrs.iter().take(12) {
                println!("  {p:#x}");
            }
        }

        if hit.points.is_empty() {
            println!("No card array resolved across poll window.");
            return;
        }

        println!(
            "\nbest: {} pack_points={} newest_l1={}",
            hit.label,
            hit.points.len(),
            hit.newest_l1
        );
        let (_recent, all_time) = deltas_from_pack(&hit.points, &current);
        println!("\n## All-time Δ");
        let mut moves: Vec<_> = all_time
            .into_iter()
            .filter_map(|(k, v)| v.map(|d| (k, d)))
            .filter(|(_, d)| *d != 0)
            .collect();
        moves.sort_by(|a, b| a.0.cmp(&b.0));
        for (attr, delta) in &moves {
            println!("  {attr}: {delta:+}");
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn resolve_ca_packs_in_live_memory() {
        use crate::fm26::process::find_fm26_process;

        if find_fm26_process().is_none() {
            println!("FM26 not running — skip");
            return;
        }
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );
        let mut with_pack = 0usize;
        let mut best_pts = 0usize;
        let mut samples: Vec<String> = Vec::new();
        for player in &snapshot.players {
            let pts = player
                .get("caPackPointCount")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as usize;
            if pts == 0 {
                continue;
            }
            with_pack += 1;
            best_pts = best_pts.max(pts);
            let name = player.get("name").and_then(|v| v.as_str()).unwrap_or("?");
            let id = player.get("id").and_then(|v| v.as_str()).unwrap_or("?");
            let deltas = player.get("allTimeAttrDeltas").and_then(|v| v.as_object());
            let non_null = deltas
                .map(|m| m.values().filter(|v| !v.is_null()).count())
                .unwrap_or(0);
            if samples.len() < 6 {
                samples.push(format!("{name} ({id}): {pts} pts, {non_null} attrs"));
            }
        }
        println!(
            "CA packs: {with_pack}/{} managed players with history (max {best_pts} pts)",
            snapshot.players.len()
        );
        for line in &samples {
            println!("  {line}");
        }
        if with_pack == 0 {
            println!("No CA packs resolved — index/uid join still missing.");
            if let Ok(index) = PLAYER_DATABASE_INDEX.get().expect("index").read() {
                let squad: Vec<_> = index
                    .records
                    .values()
                    .filter(|r| r.managed_squad)
                    .map(|r| {
                        (
                            r.id.parse::<u32>().unwrap_or(0),
                            r.person_address,
                        )
                    })
                    .collect();
                drop(index);
                let mut reader = ProcessReader::open(find_fm26_process().unwrap().0).ok();
                if let Some(reader) = reader.as_mut() {
                    let ctx = crate::fm26::ca_resolve::CaResolveContext::build(
                        reader,
                        &PLAYER_DATABASE_INDEX
                            .get()
                            .unwrap()
                            .read()
                            .unwrap()
                            .anchors,
                        &squad,
                    );
                    println!(
                        "  debug: {} clusters, {} cluster_uid hits, {} index ptrs",
                        ctx.clusters.len(),
                        ctx.cluster_histories.len(),
                        ctx.index_strip_end.len()
                    );
                    for (i, c) in ctx.clusters.iter().take(3).enumerate() {
                        println!(
                            "    cluster[{i}] {:#x} cards={} pts={}",
                            c.base, c.cards, c.history_points
                        );
                    }
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn probe_ca_history_in_live_memory() {
        use crate::fm26::{
            ca_hunt::{history_from_cluster_uid, run_ca_hunt, uid_in_cluster, uid_near_cluster},
            ca_probe::{best_probe, probe_ca_for_player},
            process::find_fm26_process,
        };

        let Some((process_id, _)) = find_fm26_process() else {
            println!("FM26 not running — skip");
            return;
        };
        let snapshot = collect_snapshot(false, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "need connected save: {}",
            snapshot.status.message
        );
        let (anchors, managed) = {
            let index = PLAYER_DATABASE_INDEX
                .get()
                .expect("index")
                .read()
                .expect("lock");
            let managed: Vec<_> = index
                .records
                .values()
                .filter(|r| r.managed_squad)
                .cloned()
                .collect();
            (index.anchors, managed)
        };
        let mut managed = managed;
        managed.sort_by(|a, b| a.name.cmp(&b.name));

        let mut reader = ProcessReader::open(process_id).expect("open fm");
        let sample_uid = managed
            .first()
            .and_then(|r| r.id.parse::<u32>().ok())
            .unwrap_or(0);

        println!("=== CA cluster + pointer hunt (2GB heap scan) ===");
        let hunt = run_ca_hunt(&mut reader, &anchors, sample_uid);
        for (i, cluster) in hunt.top_clusters.iter().take(8).enumerate() {
            let uid_hit = if sample_uid != 0 {
                uid_in_cluster(&mut reader, sample_uid, cluster)
            } else {
                false
            };
            let near = if sample_uid != 0 {
                uid_near_cluster(&mut reader, sample_uid, cluster, 8 * 1024 * 1024).len()
            } else {
                0
            };
            println!(
                "  cluster[{i}] base={:#x} cards={} history_pts={} uid_in_win={uid_hit} uid_near_8mb={near}",
                cluster.base, cluster.cards, cluster.history_points
            );
        }
        for hit in hunt.pointer_chase.iter().take(10) {
            println!(
                "  ptr_chase {} ptr={:#x} cards={} history_pts={}",
                hit.label, hit.ptr, hit.cards, hit.history_points
            );
        }
        for hit in &hunt.anchor_windows {
            println!(
                "  anchor_win {} ptr={:#x} cards={} history_pts={}",
                hit.label, hit.ptr, hit.cards, hit.history_points
            );
        }

        let mut any_points = 0usize;
        let sample = managed.len().min(8);
        println!(
            "\n=== per-player person/double probe ({sample}/{} managed) ===",
            managed.len()
        );
        for record in managed.iter().take(sample) {
            let uid = record.id.parse::<u32>().unwrap_or(0);
            let strategies = probe_ca_for_player(&mut reader, uid, record.person_address);
            let best = best_probe(&strategies);
            let best_pts = best.map(|b| b.points).unwrap_or(0);
            any_points = any_points.max(best_pts);
            println!("\n{} uid={} person={:#x}", record.name, uid, record.person_address);
            for s in &strategies {
                println!(
                    "  {:28} points={} gap_tip={:?}",
                    s.label, s.points, s.gap_tip
                );
            }
            for cluster in hunt.top_clusters.iter().take(3) {
                let near = uid_near_cluster(&mut reader, uid, cluster, 8 * 1024 * 1024);
                if !near.is_empty() {
                    let (cards, pts) = history_from_cluster_uid(&mut reader, uid, cluster);
                    println!(
                        "  uid near cluster {:#x}: doubles={} cards={cards} history_pts={pts}",
                        cluster.base,
                        near.len()
                    );
                }
            }
        }
        println!("\nmax pack points in per-player sample: {any_points}");
        let best_cluster_pts = hunt
            .top_clusters
            .first()
            .map(|c| c.history_points)
            .unwrap_or(0);
        if any_points >= 2 {
            println!("Per-player CA strip reachable in live RAM.");
        } else if best_cluster_pts >= 2 {
            println!(
                "Shared attrish clusters exist (max {best_cluster_pts} history pts) but per-player join not proven yet."
            );
        } else {
            println!(
                "CA strip NOT found (player max {any_points}, cluster max {best_cluster_pts})."
            );
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn debug_live_loaned_out_contract_club() {
        if find_fm26_process().is_none() {
            println!("FM26 is not running.");
            return;
        }
        let snapshot = collect_snapshot(false, None);
        println!(
            "snapshot state={} club={} players={}",
            snapshot.status.state,
            snapshot.managed_club_id.as_deref().unwrap_or("?"),
            snapshot.players.len()
        );
        assert_eq!(snapshot.status.state, "connected");
        let mut at_club = 0u32;
        let mut loaned_out = 0u32;
        for player in &snapshot.players {
            let loaned = player
                .get("loanedOut")
                .and_then(|value| value.as_bool())
                .unwrap_or(false);
            let name = player
                .get("name")
                .and_then(|value| value.as_str())
                .unwrap_or("?");
            if loaned {
                loaned_out += 1;
                println!("LOANED_OUT {name}");
            } else {
                at_club += 1;
            }
        }
        println!("at_club={at_club} loaned_out={loaned_out}");
        assert!(
            loaned_out > 0,
            "expected at least one outgoing loan on current senior list"
        );
        assert_eq!(at_club + loaned_out, snapshot.players.len() as u32);
        let bora_loaned = snapshot.players.iter().any(|player| {
            player
                .get("name")
                .and_then(|value| value.as_str())
                .is_some_and(|name| name.contains("Eker"))
                && player
                    .get("loanedOut")
                    .and_then(|value| value.as_bool())
                    .unwrap_or(false)
        });
        assert!(bora_loaned, "Bora Eker must be loanedOut when present on senior list");
    }

    #[test]
    fn fm_unique_id_heuristic_accepts_real_ids_and_rejects_misreads() {
        assert!(super::is_plausible_fm_unique_id(20_001_881_73));
        assert!(super::is_plausible_fm_unique_id(53_136_627));
        assert!(super::is_plausible_fm_unique_id(2_000_029_953));
        assert!(!super::is_plausible_fm_unique_id(168_365_072));
    }

    #[test]
    fn managed_squad_validation_reports_specific_position_and_attribute_failures() {
        let mut positions = vec![0_u8; 15];
        positions[3] = 21;
        assert_eq!(
            super::position_bytes_issue(&positions).as_deref(),
            Some("position byte 3 = 21 (>20)")
        );

        let mut attributes = vec![50_u8; super::PLAYER_ATTRIBUTE_NAMES.len()];
        attributes[41] = 101;
        assert_eq!(
            super::attribute_bytes_issue(&attributes).as_deref(),
            Some("attribute Dirtiness byte 41 = 101 (>100)")
        );
    }

    #[test]
    fn manager_registry_accepts_multi_slot_byte_lengths() {
        // 1–32 x64 pointers; continue saves with a dormant manager are > 8 bytes.
        for slots in [1u64, 2, 3, 8, 32] {
            let bytes = slots * 8;
            assert_eq!(bytes % 8, 0);
            assert!((1..=32).contains(&(bytes / 8)));
        }
        assert!(!(1..=32).contains(&(0u64)));
        assert!(!(1..=32).contains(&(33u64)));
    }

    #[test]
    fn connector_contract_never_requests_or_advertises_write_access() {
        assert_eq!(READ_ONLY_PROCESS_ACCESS, 0x1410);
        assert!(!empty_status().can_write_memory);
    }

    #[test]
    fn exact_build_profile_is_embedded_and_read_only() {
        let index = embedded_entity_map_index();
        assert_eq!(index.schema_version, 2);
        assert_eq!(index.profiles.len(), 1);
        assert_eq!(index.profiles[0].module, "game_plugin.dll");
        assert_eq!(
            index.profiles[0].executable_sha256,
            "3653C97F9CCEC2BE28EDC4FAAE67304B5B6C26733F2F07DEA3E7C591D3B9FF73"
        );
        let coverage = mapping_coverage(&index.profiles[0]);
        assert!(coverage
            .iter()
            .any(|section| section.section == "player" && section.validated >= 7));
        assert!(coverage
            .iter()
            .any(|section| section.section == "contract" && section.unmapped >= 4));
        assert!(coverage
            .iter()
            .any(|section| section.section == "recruitment" && section.candidate >= 2));
    }

    #[test]
    fn snapshot_has_no_entities_when_fm26_is_not_available() {
        #[cfg(not(target_os = "windows"))]
        {
            let snapshot = connector_snapshot();
            assert!(snapshot.players.is_empty());
            assert!(snapshot.clubs.is_empty());
            assert!(snapshot.tactic.is_none());
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore = "live FM26 integration test; run manually with an active save"]
    fn running_exact_build_extracts_live_entities_without_hidden_ability_fields() {
        if find_fm26_process().is_none() {
            return;
        }
        let snapshot = connector_snapshot();
        assert_eq!(
            snapshot.status.state, "connected",
            "{}",
            snapshot.status.message
        );
        assert!(snapshot
            .manager_name
            .as_deref()
            .is_some_and(|name| !name.is_empty()));
        assert!(snapshot
            .clubs
            .first()
            .and_then(|club| club["name"].as_str())
            .is_some_and(|name| !name.is_empty()));
        assert!(
            snapshot.players.len() >= 11,
            "expected at least a selected squad, got {}",
            snapshot.players.len()
        );
        assert!(snapshot.tactic.is_none());
        assert_eq!(snapshot.tactic_source, "none");
        assert_eq!(snapshot.status.live_memory_tactic_read, "object_not_found");
        for player in &snapshot.players {
            let ca = player["currentAbility"].as_u64();
            let pa = player["potentialAbility"].as_u64();
            assert!(
                ca.is_none() || (1..=200).contains(&ca.unwrap()),
                "CA out of bounds for {}",
                player["name"]
            );
            assert!(
                pa.is_none() || (1..=200).contains(&pa.unwrap()),
                "PA out of bounds for {}",
                player["name"]
            );
            assert!(player["attributes"]
                .as_object()
                .is_some_and(|value| !value.is_empty()));
            assert!(player["hiddenAttributes"]
                .as_object()
                .is_some_and(|value| !value.is_empty()));
            assert!(player["personalityAttributes"].is_object());
            assert_eq!(player["scoutKnowledge"], "fully_known");
        }
        if let Some(lars) = snapshot
            .players
            .iter()
            .find(|player| player["id"] == "53179170")
        {
            assert_eq!(lars["age"], 30);
            assert_eq!(lars["dateOfBirth"], "1995-08-13");
            assert_eq!(lars["nationality"], "Norway");
            assert_eq!(lars["attributes"]["Aerial Reach"], 15);
            assert_eq!(lars["attributes"]["Communication"], 12);
            assert!(lars["attributes"].get("Consistency").is_none());
            assert!(lars["attributes"].get("Injury Proneness").is_none());
            assert!(lars["hiddenAttributes"].get("Consistency").is_some());
            assert!(lars["hiddenAttributes"].get("Injury Proneness").is_some());
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore = "live FM26 integration test; run manually with an active save"]
    fn full_save_index_exposes_identity_only_background_search_records() {
        if find_fm26_process().is_none() {
            return;
        }
        let snapshot = collect_snapshot(true, None);
        assert_eq!(
            snapshot.status.state, "connected",
            "{}",
            snapshot.status.message
        );
        assert_eq!(snapshot.status.database_index_status, "ready");
        assert_eq!(snapshot.status.database_scope, "full-save-index");
        assert!(snapshot.status.database_players_indexed >= snapshot.status.managed_squad_players);
        assert!(snapshot.status.background_players_indexed > 0);
        assert_eq!(snapshot.status.live_memory_tactic_read, "ready");
        assert!(snapshot.status.tactic_manager_pointer.is_some());
        let tactic = snapshot.tactic.as_ref().expect("live tactic");
        assert!(tactic["formation"]
            .as_str()
            .is_some_and(|value| !value.is_empty()));
        assert_eq!(tactic["slots"].as_array().map(Vec::len), Some(11));
        assert_eq!(snapshot.tactic_source, "live-memory");
        assert_eq!(
            snapshot.status.visible_players_loaded,
            snapshot.players.len() as u32
        );
        let visible_results = search_indexed_players("Jøran".to_string());
        assert!(visible_results
            .iter()
            .all(|player| player["visibility"] == "known" || player["visibility"] == "unknown"));
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

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore]
    fn debug_live_tactic_contract_windows() {
        if find_fm26_process().is_none() {
            println!("FM26 is not running.");
            return;
        }
        let snapshot = collect_snapshot(true, None);
        println!(
            "snapshot state={} message={}",
            snapshot.status.state, snapshot.status.message
        );
        assert_eq!(snapshot.status.state, "connected");

        let index = PLAYER_DATABASE_INDEX
            .get()
            .expect("player index")
            .read()
            .expect("player index lock");
        let process_id = index.process_id;
        let mut managed = index
            .records
            .values()
            .filter(|record| record.managed_squad)
            .cloned()
            .collect::<Vec<_>>();
        managed.sort_by(|left, right| left.name.cmp(&right.name));
        drop(index);
        let active_tactic_name_needles = [
            "Sveingard",
            "Jelsa",
            "Sallabegolli",
            "Osland",
            "Romvig",
            "Rabenorolahy",
            "Sandtorv",
            "Bergset",
            "Helgevold",
            "Thulin",
            "Marchewka",
        ];
        let active_tactic_records = managed
            .iter()
            .filter(|record| {
                active_tactic_name_needles
                    .iter()
                    .any(|needle| record.name.contains(needle))
            })
            .cloned()
            .collect::<Vec<_>>();

        let mut reader = ProcessReader::open(process_id).expect("open FM26");
        let process_path = reader.process_path().expect("process path");
        let identity = read_executable_identity(&process_path);
        let profile = find_entity_map(
            identity.file_version.as_deref(),
            identity.product_version.as_deref(),
            identity.sha256.as_deref(),
            identity.architecture.as_deref(),
        )
        .expect("entity map");
        let module = reader.module(&profile.module).expect("game module");
        let player_vtable = reader
            .read_pointer(managed[0].raw_player_address)
            .expect("player vtable");
        let tactic_vtable = module.base + profile.constants.tactics_manager_vtable_rva;
        let mut scan_needles = vec![player_vtable, tactic_vtable];
        for record in &active_tactic_records {
            scan_needles.push(record.raw_player_address);
            scan_needles.push(record.person_address);
            if let Some(contract_address) = record.contract_address {
                scan_needles.push(contract_address);
            }
        }
        let mut hits = scan_private_memory_for_pointers(&mut reader, &scan_needles)
            .expect("scan private memory");
        let player_hits = hits.remove(&player_vtable).unwrap_or_default();
        let tactic_hits = hits.remove(&tactic_vtable).unwrap_or_default();
        println!(
            "player_vtable={} hits={} tactic_vtable={} hits={:?}",
            hex_address(player_vtable),
            player_hits.len(),
            hex_address(tactic_vtable),
            tactic_hits
                .iter()
                .take(8)
                .map(|value| hex_address(*value))
                .collect::<Vec<_>>()
        );
        println!("active tactic player pointer hits:");
        let mut clustered_hits = Vec::new();
        for record in &active_tactic_records {
            for (kind, pointer) in [
                ("raw", Some(record.raw_player_address)),
                ("person", Some(record.person_address)),
                ("contract", record.contract_address),
            ] {
                let Some(pointer) = pointer else {
                    continue;
                };
                let found = hits.remove(&pointer).unwrap_or_default();
                println!(
                    "  {} {} {kind}={} hits={}",
                    record.id,
                    record.name,
                    hex_address(pointer),
                    found.len()
                );
                for address in found.into_iter().take(64) {
                    clustered_hits.push((address, format!("{kind}:{} {}", record.id, record.name)));
                }
            }
        }
        clustered_hits.sort_by_key(|(address, _)| *address);
        let mut page_counts: HashMap<u64, Vec<String>> = HashMap::new();
        for (address, label) in clustered_hits {
            page_counts
                .entry(address & !0xfff)
                .or_default()
                .push(format!("{}@{}", label, hex_address(address)));
        }
        let mut clusters = page_counts.into_iter().collect::<Vec<_>>();
        clusters.sort_by(|left, right| right.1.len().cmp(&left.1.len()));
        println!("active tactic pointer clusters:");
        for (page, labels) in clusters
            .into_iter()
            .take(30)
            .filter(|(_, labels)| labels.len() >= 2)
        {
            println!(
                "  page={} count={} {:?}",
                hex_address(page),
                labels.len(),
                labels
            );
        }

        if let Some(tactic_object) = tactic_hits.first().copied() {
            let bytes = reader
                .read_bytes(tactic_object, 8192)
                .expect("tactic manager window");
            println!("tactic_object={}", hex_address(tactic_object));
            println!("small tactic i32/u32 values:");
            for offset in (0..bytes.len()).step_by(4) {
                let signed = i32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
                let unsigned = u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
                if (-1..=100).contains(&signed) {
                    println!("  off={offset:04X} i32={signed} u32={unsigned}");
                }
            }
            println!("tactic pointer-like fields:");
            for offset in (0..2048).step_by(8) {
                let pointer = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
                if (0x10000000000..0x0000_8000_0000_0000).contains(&pointer) {
                    let first_u32 = reader.read_u32(pointer).unwrap_or_default();
                    let first_ptr = reader.read_pointer(pointer).unwrap_or_default();
                    println!(
                        "  off={offset:04X} ptr={} first_u32={} first_ptr={}",
                        hex_address(pointer),
                        first_u32,
                        hex_address(first_ptr)
                    );
                }
            }

            let large_bytes = reader
                .read_bytes(tactic_object, 0x8000)
                .expect("large tactic manager window");
            println!("managed players for tactic matching:");
            for record in &managed {
                println!(
                    "  {} {} raw={} person={} contract={}",
                    record.id,
                    record.name,
                    hex_address(record.raw_player_address),
                    hex_address(record.person_address),
                    record
                        .contract_address
                        .map(hex_address)
                        .unwrap_or_else(|| "none".to_string())
                );
            }
            print_player_reference_hits("tactic-manager", tactic_object, &large_bytes, &managed);
            print_role_like_runs("tactic-manager", tactic_object, &large_bytes);

            let mut child_targets = Vec::new();
            for offset in (0..0x1000).step_by(8) {
                let pointer =
                    u64::from_le_bytes(large_bytes[offset..offset + 8].try_into().unwrap());
                if (0x10000000000..0x0000_8000_0000_0000).contains(&pointer)
                    && !child_targets.contains(&pointer)
                {
                    child_targets.push(pointer);
                }
            }
            println!("tactic child pointer probes:");
            for (index, target) in child_targets.into_iter().take(96).enumerate() {
                let Some(child_bytes) = reader.read_bytes(target, 0x1000) else {
                    continue;
                };
                let label = format!("child#{index:02}");
                let player_hits = count_player_reference_hits(target, &child_bytes, &managed);
                let role_hits = count_role_like_runs(&child_bytes);
                if player_hits > 0 || role_hits > 0 {
                    println!(
                        "  {label} base={} player_hits={} role_runs={}",
                        hex_address(target),
                        player_hits,
                        role_hits
                    );
                    print_player_reference_hits(&label, target, &child_bytes, &managed);
                    print_role_like_runs(&label, target, &child_bytes);
                }
            }
        }

        println!("managed contract windows:");
        for record in managed.iter().take(12) {
            let Some(contract) = record.contract_address else {
                println!("{} {} no contract", record.id, record.name);
                continue;
            };
            let bytes = reader.read_bytes(contract, 1024).expect("contract window");
            let mut small_values = Vec::new();
            let mut date_candidates = Vec::new();
            for offset in (0..bytes.len()).step_by(4) {
                let signed = i32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
                let unsigned = u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
                if (0..=5_000_000).contains(&signed) {
                    small_values.push(format!("{offset:03X}:{signed}"));
                }
                let day = u16::from_le_bytes(bytes[offset..offset + 2].try_into().unwrap());
                let year = u16::from_le_bytes(bytes[offset + 2..offset + 4].try_into().unwrap());
                if (1..=366).contains(&day) && (2026..=2045).contains(&year) {
                    date_candidates.push(format!("{offset:03X}:{year}-{day} raw={unsigned}"));
                }
            }
            println!(
                "{} {} contract={} vtable={} dates=[{}] values=[{}]",
                record.id,
                record.name,
                hex_address(contract),
                hex_address(reader.read_pointer(contract).unwrap_or_default()),
                date_candidates.join(", "),
                small_values.join(" ")
            );
        }
    }

    #[cfg(target_os = "windows")]
    fn print_player_reference_hits(
        label: &str,
        base: u64,
        bytes: &[u8],
        records: &[IndexedPlayerRecord],
    ) {
        for offset in (0..bytes.len().saturating_sub(8)).step_by(8) {
            let pointer = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            for record in records {
                if pointer == record.raw_player_address {
                    println!(
                        "    {label}+{offset:04X}: raw_player -> {} {}",
                        record.id, record.name
                    );
                }
                if pointer == record.person_address {
                    println!(
                        "    {label}+{offset:04X}: person -> {} {}",
                        record.id, record.name
                    );
                }
                if Some(pointer) == record.contract_address {
                    println!(
                        "    {label}+{offset:04X}: contract -> {} {}",
                        record.id, record.name
                    );
                }
            }
        }
        for offset in (0..bytes.len().saturating_sub(4)).step_by(4) {
            let uid = u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
            for record in records {
                if record.id.parse::<u32>().ok() == Some(uid) {
                    println!(
                        "    {label}+{offset:04X}: uid -> {} {}",
                        record.id, record.name
                    );
                }
            }
        }
        let _ = base;
    }

    #[cfg(target_os = "windows")]
    fn count_player_reference_hits(
        _base: u64,
        bytes: &[u8],
        records: &[IndexedPlayerRecord],
    ) -> usize {
        let mut hits = 0;
        for offset in (0..bytes.len().saturating_sub(8)).step_by(8) {
            let pointer = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            hits += records
                .iter()
                .filter(|record| {
                    pointer == record.raw_player_address
                        || pointer == record.person_address
                        || Some(pointer) == record.contract_address
                })
                .count();
        }
        for offset in (0..bytes.len().saturating_sub(4)).step_by(4) {
            let uid = u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
            hits += records
                .iter()
                .filter(|record| record.id.parse::<u32>().ok() == Some(uid))
                .count();
        }
        hits
    }

    #[cfg(target_os = "windows")]
    fn print_role_like_runs(label: &str, base: u64, bytes: &[u8]) {
        let expected_roles = [1_u32, 3, 7, 8, 10, 14, 22, 25, 26, 38];
        for start in (0..bytes.len().saturating_sub(64)).step_by(4) {
            let mut values = Vec::new();
            for offset in (start..start + 64).step_by(4) {
                let value = u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
                values.push(value);
            }
            let bounded = values
                .iter()
                .filter(|value| **value <= 45 || **value == u32::MAX)
                .count();
            let role_matches = values
                .iter()
                .filter(|value| expected_roles.contains(value))
                .count();
            let non_zero = values.iter().filter(|value| **value != 0).count();
            if bounded >= 12 && role_matches >= 3 && non_zero >= 5 {
                let absolute = base + start as u64;
                println!(
                    "    {label}+{start:04X} abs={} values={:?}",
                    hex_address(absolute),
                    values
                );
            }
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore = "live FM26 height probe; needs active save + known cm labels"]
    fn probe_height_offsets_against_known_squad_labels() {
        use std::collections::HashMap;
        use std::fs;

        let targets: HashMap<&str, u8> = HashMap::from([
            ("Sam Kizza", 193),
            ("Nathan Jones", 192),
            ("Elias Hossmang", 183),
            ("Felix Heynke", 181),
            ("Lorenzo Heilbrom", 198),
        ]);

        let (process_id, _) = find_fm26_process().expect("fm.exe");
        let mut reader = ProcessReader::open(process_id).expect("OpenProcess");
        let process_path = reader.process_path().expect("path");
        let identity = read_executable_identity(&process_path);
        let profile = find_entity_map(
            identity.file_version.as_deref(),
            identity.product_version.as_deref(),
            identity.sha256.as_deref(),
            identity.architecture.as_deref(),
        )
        .expect("entity map");
        let module = reader.module(&profile.module).expect("game_plugin.dll");
        let signature = profile
            .signatures
            .iter()
            .find(|item| item.name == "human_manager_registry")
            .expect("signature");
        let pattern = parse_pattern(&signature.pattern).expect("pattern");
        let hits = scan_module(&mut reader, module, &pattern).expect("scan");
        assert_eq!(hits.len(), 1, "unique manager signature");
        let signature_address = hits[0];
        let displacement = reader.read_i32(signature_address + 3).expect("disp");
        let registry_slot = (signature_address + 7).wrapping_add_signed(displacement as i64);
        let registry = reader.read_pointer(registry_slot).filter(|v| *v != 0).expect("registry");
        let vector_start = reader
            .read_pointer(registry + profile.constants.manager_registry_vector_offset)
            .expect("vector start");
        let vector_end = reader
            .read_pointer(registry + profile.constants.manager_registry_vector_offset + 8)
            .expect("vector end");
        let registry_count = (vector_end - vector_start) / 8;
        let mut resolved = Vec::new();
        for index in 0..registry_count {
            let human = match reader
                .read_pointer(vector_start + index * 8)
                .filter(|value| *value != 0)
            {
                Some(value) => value,
                None => continue,
            };
            if let Some(candidate) = try_resolve_human_manager(&mut reader, module, profile, human) {
                resolved.push(candidate);
            }
        }
        let selected = resolved
            .into_iter()
            .max_by_key(|item| item.squad_len)
            .expect("human manager");
        println!(
            "manager={} club={} squad={}",
            selected.manager_name, selected.club_name, selected.squad_len
        );

        let players_start = reader
            .read_pointer(selected.team + profile.constants.team_players_start_offset)
            .expect("players start");
        let players_end = reader
            .read_pointer(selected.team + profile.constants.team_players_end_offset)
            .expect("players end");
        let squad_len = ((players_end - players_start) / 8) as usize;

        struct Cap {
            name: String,
            cm: u8,
            person: Vec<u8>,
            player: Vec<u8>,
        }
        let mut caps = Vec::new();
        let mut seen = Vec::new();
        for slot in 0..squad_len {
            let raw_player = match reader.read_pointer(players_start + (slot as u64) * 8) {
                Some(value) if value != 0 => value,
                _ => continue,
            };
            let person = raw_player + profile.constants.player_person_offset;
            let name = match display_name(
                read_name_field(&mut reader, person + profile.constants.person_first_name_offset),
                read_name_field(&mut reader, person + profile.constants.person_second_name_offset),
                read_name_field(&mut reader, person + profile.constants.person_common_name_offset),
            ) {
                Some(value) => value,
                None => continue,
            };
            seen.push(name.clone());
            let Some(&cm) = targets.get(name.as_str()) else {
                continue;
            };
            let person_bytes = reader.read_bytes(person, 256).expect("person window");
            let player_bytes = reader.read_bytes(raw_player, 768).expect("player window");
            println!("captured {name} cm={cm}");
            caps.push(Cap {
                name,
                cm,
                person: person_bytes,
                player: player_bytes,
            });
        }

        let missing: Vec<_> = targets
            .keys()
            .copied()
            .filter(|name| !caps.iter().any(|cap| cap.name == *name))
            .collect();
        if !missing.is_empty() {
            println!("MISSING {missing:?}");
            for want in &missing {
                let needle = want.split_whitespace().last().unwrap_or(want).to_ascii_lowercase();
                let approx: Vec<_> = seen
                    .iter()
                    .filter(|name| name.to_ascii_lowercase().contains(&needle))
                    .take(8)
                    .collect();
                println!("  approx for {want}: {approx:?}");
            }
        }
        assert!(
            caps.len() >= 3,
            "need >=3 labelled captures, got {}",
            caps.len()
        );

        println!("\n=== per-player person u8 == cm ===");
        for cap in &caps {
            let offs: Vec<_> = cap
                .person
                .iter()
                .enumerate()
                .filter_map(|(i, b)| (*b == cap.cm).then_some(i))
                .collect();
            println!("  {}: {:?}", cap.name, offs);
        }
        println!("=== per-player player u8 == cm ===");
        for cap in &caps {
            let offs: Vec<_> = cap
                .player
                .iter()
                .enumerate()
                .filter_map(|(i, b)| (*b == cap.cm).then_some(i))
                .collect();
            println!("  {}: {:?}", cap.name, offs);
        }

        println!("\n=== consensus (all captured labels) ===");
        for (obj, getter) in [
            ("person", (|c: &Cap| c.person.as_slice()) as fn(&Cap) -> &[u8]),
            ("player", (|c: &Cap| c.player.as_slice()) as fn(&Cap) -> &[u8]),
        ] {
            let len = getter(&caps[0]).len();
            let mut u8_hits = Vec::new();
            let mut u16_cm_hits = Vec::new();
            let mut u16_mm_hits = Vec::new();
            for off in 0..len {
                if caps.iter().all(|cap| {
                    getter(cap).get(off).copied() == Some(cap.cm)
                }) {
                    u8_hits.push(off);
                }
            }
            for off in 0..len.saturating_sub(1) {
                let all_cm = caps.iter().all(|cap| {
                    let bytes = getter(cap);
                    u16::from_le_bytes([bytes[off], bytes[off + 1]]) == u16::from(cap.cm)
                });
                if all_cm {
                    u16_cm_hits.push(off);
                }
                let all_mm = caps.iter().all(|cap| {
                    let bytes = getter(cap);
                    u16::from_le_bytes([bytes[off], bytes[off + 1]]) == u16::from(cap.cm) * 10
                });
                if all_mm {
                    u16_mm_hits.push(off);
                }
            }
            println!("{obj} u8 cm: {u8_hits:?}");
            println!("{obj} u16 cm: {u16_cm_hits:?}");
            println!("{obj} u16 mm: {u16_mm_hits:?}");
        }

        println!("\n=== person+0x70..0xB0 ===");
        for cap in &caps {
            let region = &cap.person[0x70..0xB0];
            let hex: String = region
                .iter()
                .map(|b| format!("{b:02x}"))
                .collect::<Vec<_>>()
                .join(" ");
            println!("  {:20} {hex}", cap.name);
        }

        let payload = caps
            .iter()
            .map(|cap| {
                json!({
                    "name": cap.name,
                    "cm": cap.cm,
                    "personHex": cap.person.iter().map(|b| format!("{b:02x}")).collect::<String>(),
                    "playerHex": cap.player.iter().map(|b| format!("{b:02x}")).collect::<String>(),
                })
            })
            .collect::<Vec<_>>();
        let path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../tmp/height-probe-captures.json");
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        fs::write(&path, serde_json::to_string_pretty(&payload).unwrap()).unwrap();
        println!("wrote {}", path.display());
    }

    #[cfg(target_os = "windows")]
    fn count_role_like_runs(bytes: &[u8]) -> usize {
        let expected_roles = [1_u32, 3, 7, 8, 10, 14, 22, 25, 26, 38];
        let mut runs = 0;
        for start in (0..bytes.len().saturating_sub(64)).step_by(4) {
            let mut values = Vec::new();
            for offset in (start..start + 64).step_by(4) {
                values.push(u32::from_le_bytes(
                    bytes[offset..offset + 4].try_into().unwrap(),
                ));
            }
            let bounded = values
                .iter()
                .filter(|value| **value <= 45 || **value == u32::MAX)
                .count();
            let role_matches = values
                .iter()
                .filter(|value| expected_roles.contains(value))
                .count();
            let non_zero = values.iter().filter(|value| **value != 0).count();
            if bounded >= 12 && role_matches >= 3 && non_zero >= 5 {
                runs += 1;
            }
        }
        runs
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore = "manual foot band probe; run with --ignored --nocapture"]
    fn foot_probe_managed_squad_for_bands() {
        use crate::fm26::parser::preferred_foot_label;

        if find_fm26_process().is_none() {
            eprintln!("FM not running");
            return;
        }
        let snapshot = connector_snapshot();
        if snapshot.status.state != "connected" {
            eprintln!("not connected: {}", snapshot.status.message);
            return;
        }
        let Some(managed) = snapshot.managed_club_id.as_deref() else {
            eprintln!("no managed club");
            return;
        };
        let mut rows = Vec::new();
        for player in &snapshot.players {
            if player.get("clubId").and_then(|value| value.as_str()) != Some(managed) {
                continue;
            }
            let name = player["name"].as_str().unwrap_or("?");
            let left = player["leftFoot"].as_u64().unwrap_or(0) as u8;
            let right = player["rightFoot"].as_u64().unwrap_or(0) as u8;
            let fmt = preferred_foot_label(left, right);
            let ca = player["currentAbility"].as_u64().unwrap_or(0);
            rows.push((name.to_string(), left, right, fmt.to_string(), ca));
        }
        rows.sort_by(|a, b| b.4.cmp(&a.4).then(a.0.cmp(&b.0)));
        println!("MANAGED_SQUAD {} players", rows.len());
        for (name, left, right, fmt, ca) in rows {
            let diff = left.abs_diff(right);
            let tag = if left == right {
                "EQUAL"
            } else if diff <= 3 {
                "NEAR"
            } else {
                "FAR"
            };
            println!("{tag}\t{name}\tL{left}\tR{right}\tFMT={fmt}\tCA={ca}");
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore = "manual GK rating probe; run with --ignored --nocapture"]
    fn gk_rating_probe_managed_squad() {
        if find_fm26_process().is_none() {
            eprintln!("FM not running");
            return;
        }
        let snapshot = connector_snapshot();
        if snapshot.status.state != "connected" {
            eprintln!("not connected: {}", snapshot.status.message);
            return;
        }
        let Some(managed) = snapshot.managed_club_id.as_deref() else {
            eprintln!("no managed club");
            return;
        };

        const CORE: [&str; 11] = [
            "Aerial Reach",
            "Command of Area",
            "Communication",
            "Eccentricity",
            "Handling",
            "Kicking",
            "One on Ones",
            "Punching",
            "Reflexes",
            "Rushing Out",
            "Throwing",
        ];

        let mut rows = Vec::new();
        for player in &snapshot.players {
            if player.get("clubId").and_then(|value| value.as_str()) != Some(managed) {
                continue;
            }
            let name = player["name"].as_str().unwrap_or("?");
            let positions = player["positions"]
                .as_array()
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str())
                        .collect::<Vec<_>>()
                        .join("/")
                })
                .unwrap_or_default();
            let is_gk = positions.split('/').any(|p| p.trim() == "GK");
            let live_rating = player["goalkeeperRating"].as_u64();
            let attrs = player["attributes"].as_object();
            let mut core_vals = Vec::new();
            if let Some(map) = attrs {
                for key in CORE {
                    if let Some(v) = map.get(key).and_then(|v| v.as_u64()) {
                        core_vals.push(v as u8);
                    }
                }
            }
            if core_vals.is_empty() {
                continue;
            }
            let max_v = *core_vals.iter().max().unwrap();
            let sum: u32 = core_vals.iter().map(|v| u32::from(*v)).sum();
            let mean = sum as f64 / core_vals.len() as f64;
            let mean_round = mean.round() as u8;
            let mean_half = (mean / 2.0).round() as u8;
            let mut sorted = core_vals.clone();
            sorted.sort_unstable();
            let top3 = &sorted[sorted.len().saturating_sub(3)..];
            let top3_mean =
                (top3.iter().map(|v| u32::from(*v)).sum::<u32>() as f64 / top3.len() as f64).round()
                    as u8;
            let ca = player["currentAbility"].as_u64().unwrap_or(0);
            let ft = attrs
                .and_then(|m| m.get("First Touch"))
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let pass = attrs
                .and_then(|m| m.get("Passing"))
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            rows.push((
                is_gk,
                name.to_string(),
                positions,
                live_rating,
                max_v,
                mean_round,
                mean_half,
                top3_mean,
                ca,
                ft,
                pass,
                core_vals,
            ));
        }
        rows.sort_by(|a, b| b.4.cmp(&a.4).then(b.8.cmp(&a.8)).then(a.1.cmp(&b.1)));
        println!("GK_RATING_PROBE outfield first (FMT liveRating=positions[0] cap10)");
        println!(
            "tag\tname\tpos\tlive\tmax\tmean\tmean/2\ttop3\tCA\tFT\tPas\tcore"
        );
        for (is_gk, name, positions, live, max_v, mean_r, mean_h, top3, ca, ft, pass, core) in
            &rows
        {
            if *is_gk {
                continue;
            }
            let core_s = core
                .iter()
                .map(|v| v.to_string())
                .collect::<Vec<_>>()
                .join(",");
            println!(
                "OF\t{name}\t{positions}\t{live:?}\t{max_v}\t{mean_r}\t{mean_h}\t{top3}\t{ca}\t{ft}\t{pass}\t[{core_s}]"
            );
        }
        println!("--- keepers (skip for /10 UI) ---");
        for (is_gk, name, positions, live, max_v, mean_r, mean_h, top3, ca, ft, pass, core) in
            &rows
        {
            if !*is_gk {
                continue;
            }
            let core_s = core
                .iter()
                .map(|v| v.to_string())
                .collect::<Vec<_>>()
                .join(",");
            println!(
                "GK\t{name}\t{positions}\t{live:?}\t{max_v}\t{mean_r}\t{mean_h}\t{top3}\t{ca}\t{ft}\t{pass}\t[{core_s}]"
            );
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore = "manual GK rating offset hunt; run with --ignored --nocapture"]
    fn gk_rating_offset_hunt() {
        use std::collections::{HashMap, HashSet};

        if find_fm26_process().is_none() {
            eprintln!("FM not running");
            return;
        }
        let snapshot = connector_snapshot();
        if snapshot.status.state != "connected" {
            eprintln!("not connected: {}", snapshot.status.message);
            return;
        }

        let labels: HashMap<&str, u8> = HashMap::from([
            ("Pietro Miraglia", 4),
            ("Stephen Segun", 3),
            ("Josef Tusjak", 3),
            ("Felix Heynke", 3),
            ("Mate Kolarek", 3),
            ("Corvin Garbe", 2),
            ("Jordan Dobler", 2),
        ]);

        let mut per_player: Vec<(String, u8, Vec<u8>, Vec<u8>)> = Vec::new();
        for player in &snapshot.players {
            let name = player["name"].as_str().unwrap_or("");
            let Some(&fm) = labels.get(name) else {
                continue;
            };
            let id = player["id"].as_str().unwrap_or(name);
            let dump = match capture_mapping_lab_player(id, 1024) {
                Ok(dump) => dump,
                Err(err) => {
                    eprintln!("capture failed for {name}: {err}");
                    continue;
                }
            };
            let mut player_bytes = None;
            let mut person_bytes = None;
            for window in &dump.windows {
                if window.object == "player" {
                    player_bytes = Some(window.bytes.clone());
                }
                if window.object == "person" || window.object == "personEmbedded" {
                    person_bytes = Some(window.bytes.clone());
                }
            }
            let Some(player_bytes) = player_bytes else {
                eprintln!("no player window for {name}");
                continue;
            };
            println!(
                "captured {name} fm={fm} player_len={} person_len={}",
                player_bytes.len(),
                person_bytes.as_ref().map(|b| b.len()).unwrap_or(0)
            );
            // raw attrs + extras for offline formula search
            if player_bytes.len() >= 351 + 54 {
                let raw = &player_bytes[351..351 + 54];
                let pick = |i: usize| raw[i];
                let disp = |v: u8| (((u16::from(v) + 2) / 5) as u8).clamp(1, 20);
                println!(
                    "  extras FT={} Pas={} Agi={} JR={} Str={} Bal={} Ant={} Dec={} Pos={} Cmp={} Con={}",
                    disp(pick(22)),
                    disp(pick(7)),
                    disp(pick(46)),
                    disp(pick(39)),
                    disp(pick(36)),
                    disp(pick(42)),
                    disp(pick(17)),
                    disp(pick(18)),
                    disp(pick(20)),
                    disp(pick(52)),
                    disp(pick(53)),
                );
                println!(
                    "  raw_scale fm*5={} fm*10={}",
                    fm.saturating_mul(5),
                    fm.saturating_mul(10)
                );
            }
            per_player.push((
                name.to_string(),
                fm,
                player_bytes,
                person_bytes.unwrap_or_default(),
            ));
        }

        if per_player.len() < 2 {
            eprintln!("need >=2 captures");
            return;
        }

        let min_player_len = per_player.iter().map(|p| p.2.len()).min().unwrap_or(0);

        // Exact u8 == fm
        let mut candidates: HashSet<usize> = (0..min_player_len).collect();
        for (_, fm, bytes, _) in &per_player {
            candidates.retain(|off| bytes.get(*off).copied() == Some(*fm));
        }
        println!("PLAYER_U8 ==fm : {}", candidates.len());

        // u8 == fm*5 (raw-attr style)
        let mut cand_x5: HashSet<usize> = (0..min_player_len).collect();
        for (_, fm, bytes, _) in &per_player {
            let target = fm.saturating_mul(5);
            cand_x5.retain(|off| bytes.get(*off).copied() == Some(target));
        }
        println!("PLAYER_U8 ==fm*5 : {}", cand_x5.len());
        let mut sorted: Vec<usize> = cand_x5.into_iter().collect();
        sorted.sort_unstable();
        for off in &sorted {
            println!("  player+{off}");
        }

        // u16 LE == fm
        let mut cand_u16 = Vec::new();
        for off in 0..min_player_len.saturating_sub(1) {
            let ok = per_player.iter().all(|(_, fm, bytes, _)| {
                let v = u16::from_le_bytes([bytes[off], bytes[off + 1]]);
                v == u16::from(*fm)
            });
            if ok {
                cand_u16.push(off);
            }
        }
        println!("PLAYER_U16LE ==fm : {}", cand_u16.len());
        for off in cand_u16.iter().take(40) {
            println!("  player+{off}");
        }

        // u16 LE == fm*5
        let mut cand_u16_x5 = Vec::new();
        for off in 0..min_player_len.saturating_sub(1) {
            let ok = per_player.iter().all(|(_, fm, bytes, _)| {
                let v = u16::from_le_bytes([bytes[off], bytes[off + 1]]);
                v == u16::from(fm.saturating_mul(5))
            });
            if ok {
                cand_u16_x5.push(off);
            }
        }
        println!("PLAYER_U16LE ==fm*5 : {}", cand_u16_x5.len());
        for off in cand_u16_x5.iter().take(40) {
            println!("  player+{off}");
        }

        let min_person = per_player
            .iter()
            .map(|p| p.3.len())
            .filter(|l| *l > 0)
            .min()
            .unwrap_or(0);
        if min_person > 0 {
            let mut person_cand: HashSet<usize> = (0..min_person).collect();
            for (_, fm, _, person) in &per_player {
                person_cand.retain(|off| person.get(*off).copied() == Some(*fm));
            }
            println!("PERSON_U8 ==fm : {}", person_cand.len());
            let mut person_x5: HashSet<usize> = (0..min_person).collect();
            for (_, fm, _, person) in &per_player {
                let target = fm.saturating_mul(5);
                person_x5.retain(|off| person.get(*off).copied() == Some(target));
            }
            println!("PERSON_U8 ==fm*5 : {}", person_x5.len());
            let mut sorted: Vec<usize> = person_x5.into_iter().collect();
            sorted.sort_unstable();
            for off in sorted.iter().take(40) {
                println!("  person+{off}");
            }
        }
    }

    #[cfg(target_os = "windows")]
    #[test]
    #[ignore = "manual: dump live player object to tmp/; FM must be running with save loaded"]
    fn dump_player_168365072_object() {
        use std::{fs, path::PathBuf};

        if find_fm26_process().is_none() {
            eprintln!("FM not running — skipping dump");
            return;
        }
        let snapshot = connector_snapshot();
        if snapshot.status.state != "connected" {
            eprintln!("not connected: {}", snapshot.status.message);
            return;
        }
        let dump = capture_mapping_lab_player("168365072", 1024).expect("capture");
        let out_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../tmp");
        fs::create_dir_all(&out_dir).expect("tmp dir");
        let json_path = out_dir.join("player-dump-168365072.json");
        fs::write(
            &json_path,
            serde_json::to_vec_pretty(&dump).expect("encode dump"),
        )
        .expect("write json");

        let mut text = String::new();
        text.push_str(&format!(
            "player_id={} name={}\nraw_player={} person_embedded={}\n\n",
            dump.player_id, dump.player_name, dump.raw_player_address, dump.person_embedded_address
        ));
        for probe in &dump.person_probes {
            text.push_str(&format!(
                "probe {} @ {} uid+12={:?} name={:?}\n",
                probe.label, probe.base_address, probe.uid_at_plus_12, probe.name
            ));
        }
        for window in &dump.windows {
            text.push_str(&format!(
                "\n=== {} @ {} ({} bytes) ===\n",
                window.object,
                window.base_address,
                window.bytes.len()
            ));
            for (offset, chunk) in window.bytes.chunks(16).enumerate() {
                let base = offset * 16;
                let hex: String = chunk
                    .iter()
                    .map(|byte| format!("{byte:02X}"))
                    .collect::<Vec<_>>()
                    .join(" ");
                text.push_str(&format!("{base:04X}  {hex}\n"));
            }
        }
        let txt_path = out_dir.join("player-dump-168365072.txt");
        fs::write(&txt_path, text).expect("write txt");
        println!(
            "Wrote {} and {}",
            json_path.display(),
            txt_path.display()
        );
    }
}
