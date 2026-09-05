//! Player origin (DB vs regen/newgen) RE probe.
//!
//! Ground truth is **owner-labelled**, not UID band:
//! - DB: known real-player UIDs (may sit in the ~2.0B range — same as many regens)
//! - Regen: managed U19 roster samples
//!
//! Face-pack `r-{uid}` paths are graphics only. Do not treat UID ≥ 1.9B as newgen law.

use serde_json::{json, Value};

use super::{
    memory::ProcessReader,
    offsets::EntityMapProfile,
    scanner::scan_private_memory_for_u32_in_range,
};

/// Owner-confirmed database players for T216 origin RE (current game / save era).
pub(crate) const DB_ORIGIN_GROUND_TRUTH: &[(u32, &str)] = &[
    (2_000_256_231, "Lamine Yamal"),
    (2_000_257_651, "Noah Darvich"),
    (2_000_295_603, "Marc Bernal"),
    (2_000_251_840, "Gonzalo Escudero"),
    (2_000_190_785, "Sultan Saleem"),
];

const PERSON_SCAN_LEN: usize = 512;
const PLAYER_SCAN_LEN: usize = 768;
/// FSS Fields.cs: person+0x18 bit 0x08 noted as jeugd/youth — not proven = newgen.
const FSS_YOUTH_BYTE_OFFSET: usize = 0x18;
const FSS_YOUTH_BIT: u8 = 0x08;

#[derive(Clone, Debug)]
pub(crate) struct OriginSample {
    pub uid: u32,
    pub name: String,
    pub person: u64,
    pub player_base: u64,
    pub bucket: &'static str,
}

fn is_heap_ptr(value: u64) -> bool {
    (0x10_000..0x0000_7FF0_0000_0000).contains(&value) && value.is_multiple_of(8)
}

fn read_name_field(reader: &mut ProcessReader, field: u64) -> Option<String> {
    reader.read_fm_string_pointer(field)
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

fn person_name(reader: &mut ProcessReader, person: u64, profile: &EntityMapProfile) -> Option<String> {
    display_name(
        read_name_field(reader, person + profile.constants.person_first_name_offset),
        read_name_field(reader, person + profile.constants.person_second_name_offset),
        read_name_field(reader, person + profile.constants.person_common_name_offset),
    )
}

fn person_looks_valid(
    reader: &mut ProcessReader,
    person: u64,
    profile: &EntityMapProfile,
    expect_uid: Option<u32>,
) -> Option<(u32, String)> {
    let uid = reader.read_u32(person + profile.constants.entity_uid_offset)?;
    if uid == 0 {
        return None;
    }
    if let Some(expected) = expect_uid {
        if uid != expected {
            return None;
        }
    }
    let name = person_name(reader, person, profile)?;
    Some((uid, name))
}

fn player_base_from_person(
    reader: &mut ProcessReader,
    person: u64,
    profile: &EntityMapProfile,
) -> Option<u64> {
    let class_offsets = [
        profile.constants.player_person_offset,
        0x288,
        0x380,
    ];
    for &class_offset in &class_offsets {
        let player_base = person.saturating_sub(class_offset);
        if player_base == 0 || !is_heap_ptr(player_base) {
            continue;
        }
        // CA-ish u16 in PLAO band — loose readability check.
        if reader
            .read_u16(player_base + profile.constants.player_ca_offset)
            .is_some()
        {
            return Some(player_base);
        }
    }
    // Fallback: roster-style person pointer at player+playerPersonOffset.
    None
}

/// Resolve person (+ PLAO) from a UID u32 hit address (`hit` points at the UID dword).
pub(crate) fn person_from_uid_hit(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
    hit: u64,
    expect_uid: u32,
) -> Option<(u64, u64, String)> {
    let person = hit.saturating_sub(profile.constants.entity_uid_offset);
    if !is_heap_ptr(person) {
        return None;
    }
    let (uid, name) = person_looks_valid(reader, person, profile, Some(expect_uid))?;
    let _ = uid;
    let player_base = player_base_from_person(reader, person, profile).unwrap_or(person);
    Some((person, player_base, name))
}

/// Heap-hunt known DB UIDs and return validated origin samples.
#[cfg(target_os = "windows")]
pub(crate) fn resolve_db_origin_samples(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
) -> (Vec<OriginSample>, Value) {
    let uids: Vec<u32> = DB_ORIGIN_GROUND_TRUTH.iter().map(|(uid, _)| *uid).collect();
    let scan = scan_private_memory_for_u32_in_range(
        reader,
        &uids,
        0,
        0x0000_7FF0_0000_0000,
        48,
    );
    let mut diagnostics = Vec::new();
    let mut samples = Vec::new();
    let Ok(hits) = scan else {
        return (
            samples,
            json!({
                "status": "scan_failed",
                "message": "Private-memory u32 scan for DB UIDs failed.",
            }),
        );
    };

    for &(uid, expected_name) in DB_ORIGIN_GROUND_TRUTH {
        let addrs = hits.get(&uid).cloned().unwrap_or_default();
        let mut resolved = None;
        let mut tried = 0usize;
        for hit in addrs.iter().copied() {
            tried += 1;
            if let Some((person, player_base, name)) =
                person_from_uid_hit(reader, profile, hit, uid)
            {
                resolved = Some((person, player_base, name, hit));
                break;
            }
        }
        match resolved {
            Some((person, player_base, name, hit)) => {
                diagnostics.push(json!({
                    "uid": uid,
                    "expectedName": expected_name,
                    "status": "resolved",
                    "name": name,
                    "person": format!("0x{person:X}"),
                    "playerBase": format!("0x{player_base:X}"),
                    "uidHit": format!("0x{hit:X}"),
                    "hitCount": addrs.len(),
                    "triedHits": tried,
                }));
                samples.push(OriginSample {
                    uid,
                    name,
                    person,
                    player_base,
                    bucket: "database",
                });
            }
            None => {
                diagnostics.push(json!({
                    "uid": uid,
                    "expectedName": expected_name,
                    "status": "unresolved",
                    "hitCount": addrs.len(),
                    "triedHits": tried,
                }));
            }
        }
    }

    (
        samples,
        json!({
            "status": "ok",
            "resolved": diagnostics.iter().filter(|d| d["status"] == "resolved").count(),
            "players": diagnostics,
        }),
    )
}

#[cfg(target_os = "windows")]
fn read_window(reader: &mut ProcessReader, base: u64, len: usize) -> Option<Vec<u8>> {
    reader.read_bytes(base, len)
}

#[cfg(target_os = "windows")]
fn uniform_value(values: &[u8]) -> Option<u8> {
    let first = *values.first()?;
    values.iter().all(|v| *v == first).then_some(first)
}

/// Diff person/player bytes between database and regen samples.
/// Returns candidate offsets where each bucket is uniform and the values differ.
#[cfg(target_os = "windows")]
pub(crate) fn probe_origin_byte_split(
    reader: &mut ProcessReader,
    database: &[OriginSample],
    regen: &[OriginSample],
) -> Value {
    if database.is_empty() || regen.is_empty() {
        return json!({
            "status": "insufficient_samples",
            "databaseSamples": database.len(),
            "regenSamples": regen.len(),
            "message": "Need ≥1 DB and ≥1 regen sample with resolved person/player bases.",
        });
    }

    let mut person_candidates = Vec::new();
    let mut player_candidates = Vec::new();
    let mut bit_candidates = Vec::new();

    for offset in 0..PERSON_SCAN_LEN {
        let db_vals: Vec<u8> = database
            .iter()
            .filter_map(|s| reader.read_bytes(s.person + offset as u64, 1))
            .filter_map(|b| b.first().copied())
            .collect();
        let regen_vals: Vec<u8> = regen
            .iter()
            .filter_map(|s| reader.read_bytes(s.person + offset as u64, 1))
            .filter_map(|b| b.first().copied())
            .collect();
        if db_vals.len() != database.len() || regen_vals.len() != regen.len() {
            continue;
        }
        let Some(db_u) = uniform_value(&db_vals) else {
            continue;
        };
        let Some(regen_u) = uniform_value(&regen_vals) else {
            continue;
        };
        if db_u == regen_u {
            continue;
        }
        person_candidates.push(json!({
            "object": "person",
            "offset": offset,
            "offsetHex": format!("0x{offset:X}"),
            "databaseValue": db_u,
            "regenValue": regen_u,
            "databaseSamples": db_vals.len(),
            "regenSamples": regen_vals.len(),
        }));
        let xor = db_u ^ regen_u;
        for bit in 0..8u8 {
            let mask = 1u8 << bit;
            if xor & mask == 0 {
                continue;
            }
            bit_candidates.push(json!({
                "object": "person",
                "offset": offset,
                "offsetHex": format!("0x{offset:X}"),
                "bit": bit,
                "mask": mask,
                "databaseBit": (db_u & mask) != 0,
                "regenBit": (regen_u & mask) != 0,
            }));
        }
    }

    for offset in 0..PLAYER_SCAN_LEN {
        let db_vals: Vec<u8> = database
            .iter()
            .filter_map(|s| reader.read_bytes(s.player_base + offset as u64, 1))
            .filter_map(|b| b.first().copied())
            .collect();
        let regen_vals: Vec<u8> = regen
            .iter()
            .filter_map(|s| reader.read_bytes(s.player_base + offset as u64, 1))
            .filter_map(|b| b.first().copied())
            .collect();
        if db_vals.len() != database.len() || regen_vals.len() != regen.len() {
            continue;
        }
        let Some(db_u) = uniform_value(&db_vals) else {
            continue;
        };
        let Some(regen_u) = uniform_value(&regen_vals) else {
            continue;
        };
        if db_u == regen_u {
            continue;
        }
        player_candidates.push(json!({
            "object": "player",
            "offset": offset,
            "offsetHex": format!("0x{offset:X}"),
            "databaseValue": db_u,
            "regenValue": regen_u,
            "databaseSamples": db_vals.len(),
            "regenSamples": regen_vals.len(),
        }));
    }

    // Explicit FSS youth-bit readout (do not ship as isRegen without proof).
    let fss_youth = {
        let db_bits: Vec<bool> = database
            .iter()
            .filter_map(|s| reader.read_bytes(s.person + FSS_YOUTH_BYTE_OFFSET as u64, 1))
            .filter_map(|b| b.first().copied())
            .map(|v| (v & FSS_YOUTH_BIT) != 0)
            .collect();
        let regen_bits: Vec<bool> = regen
            .iter()
            .filter_map(|s| reader.read_bytes(s.person + FSS_YOUTH_BYTE_OFFSET as u64, 1))
            .filter_map(|b| b.first().copied())
            .map(|v| (v & FSS_YOUTH_BIT) != 0)
            .collect();
        json!({
            "offset": FSS_YOUTH_BYTE_OFFSET,
            "offsetHex": "0x18",
            "bitMask": FSS_YOUTH_BIT,
            "note": "FSS jeugd/youth bit — may track youth-team membership, not DB vs regen",
            "databaseBitsSet": db_bits.iter().filter(|b| **b).count(),
            "databaseSamples": db_bits.len(),
            "regenBitsSet": regen_bits.iter().filter(|b| **b).count(),
            "regenSamples": regen_bits.len(),
            "uniformDatabase": db_bits.first().copied().filter(|_| db_bits.iter().all(|b| *b == db_bits[0])),
            "uniformRegen": regen_bits.first().copied().filter(|_| regen_bits.iter().all(|b| *b == regen_bits[0])),
        })
    };

    let _ = read_window; // keep helper available for future dumps

    json!({
        "status": if person_candidates.is_empty() && player_candidates.is_empty() {
            "no_uniform_split"
        } else {
            "candidates"
        },
        "mappedOriginField": null,
        "message": if person_candidates.is_empty() && player_candidates.is_empty() {
            "No uniform person/player byte split between DB ground truth and U19 regen samples."
        } else {
            "Candidate bytes differ uniformly DB vs regen. Validate before wiring LivePlayer.isRegen — do not use UID band."
        },
        "databaseSamples": database.iter().map(|s| json!({
            "uid": s.uid,
            "name": s.name,
            "person": format!("0x{:X}", s.person),
            "playerBase": format!("0x{:X}", s.player_base),
        })).collect::<Vec<_>>(),
        "regenSamples": regen.iter().map(|s| json!({
            "uid": s.uid,
            "name": s.name,
            "person": format!("0x{:X}", s.person),
            "playerBase": format!("0x{:X}", s.player_base),
        })).collect::<Vec<_>>(),
        "personCandidates": person_candidates,
        "playerCandidates": player_candidates,
        "personBitCandidates": bit_candidates,
        "fssYouthBit0x18": fss_youth,
        "law": "UID band and face r- prefix are not origin law. Prefer a durable person/player flag.",
    })
}

/// Legacy entry used by older probe feature — kept for compile; prefer ground-truth path.
#[cfg(target_os = "windows")]
pub(crate) fn probe_player_origin_fields(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
    samples: &[(u64, u32, u64, u64)], // (raw_player, uid, person, _vtable)
) -> Value {
    let _ = (reader, profile, samples);
    json!({
        "status": "deprecated",
        "message": "UID-band managed-squad origin probe retired (T216). Use probe_origin_byte_split with DB UIDs + U19 samples.",
        "entityMapNote": "player.isGameGenerated remains unmapped until T216 locks a field.",
    })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn resolve_db_origin_samples(
    _reader: &mut ProcessReader,
    _profile: &EntityMapProfile,
) -> (Vec<OriginSample>, Value) {
    (
        Vec::new(),
        json!({ "status": "unsupported", "message": "Windows only." }),
    )
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn probe_origin_byte_split(
    _reader: &mut ProcessReader,
    _database: &[OriginSample],
    _regen: &[OriginSample],
) -> Value {
    json!({ "status": "unsupported", "message": "Windows only." })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn probe_player_origin_fields(
    _reader: &mut ProcessReader,
    _profile: &EntityMapProfile,
    _samples: &[(u64, u32, u64, u64)],
) -> Value {
    json!({ "status": "unsupported", "message": "Windows only." })
}
