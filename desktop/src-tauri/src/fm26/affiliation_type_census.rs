//! Walk every club's `+0x118` affiliation vector; census wrapper `+0x30` type bytes.
//! Report clubs that carry unmapped types so the human can label them in PGE.

use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

#[cfg(target_os = "windows")]
use super::{
    memory::{ModuleInfo, ProcessReader},
    offsets::EntityMapProfile,
};

/// Locked so far (T214).
#[cfg(target_os = "windows")]
const MAPPED: &[(u8, &str)] = &[
    (0x01, "Normal Affiliated Club"),
    (0x08, "II Club"),
    (0x10, "Good Relations"),
    (0x11, "Likely Friendly"),
];

#[cfg(target_os = "windows")]
const AFFIL_VEC_OFF: u64 = 0x118;
#[cfg(target_os = "windows")]
const TYPE_OFF: usize = 0x30;
#[cfg(target_os = "windows")]
const PARTNER_UID_OFF: usize = 0x0C;
#[cfg(target_os = "windows")]
const MAX_SLOTS: usize = 48;
#[cfg(target_os = "windows")]
const CLUB_TABLE_SLOT: u64 = 0xF8;
#[cfg(target_os = "windows")]
const OFFSET_TABLE_RVA: u64 = 0x4E4_9490;

#[cfg(target_os = "windows")]
fn looks_heap(p: u64) -> bool {
    p >= 0x10_000 && p < 0x0000_7FFF_FFFF_FFFF
}

#[cfg(target_os = "windows")]
fn mapped_label(b: u8) -> Option<&'static str> {
    MAPPED.iter().find(|(v, _)| *v == b).map(|(_, n)| *n)
}

#[cfg(target_os = "windows")]
fn club_table_bounds(reader: &mut ProcessReader, module: ModuleInfo) -> Option<(u64, u64)> {
    let table = module.base.saturating_add(OFFSET_TABLE_RVA);
    let slot_ptr = reader.read_pointer(table + CLUB_TABLE_SLOT)?;
    let offset_value = reader.read_pointer(slot_ptr + 0x80)?;
    let begin = reader.read_pointer(offset_value)?;
    let end = reader.read_pointer(offset_value + 8)?;
    if end <= begin || (end - begin) % 8 != 0 {
        return None;
    }
    Some((begin, end))
}

#[cfg(target_os = "windows")]
pub(crate) fn probe_affiliation_type_census(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
) -> Value {
    let uid_off = profile.constants.entity_uid_offset;
    let name_off = profile.constants.club_name_offset;

    let Some((begin, end)) = club_table_bounds(reader, module) else {
        return json!({ "error": "club table not resolved" });
    };
    let count = ((end - begin) / 8) as usize;
    eprintln!("affil-type-census: clubTable count={count}");

    let Some(array) = reader.read_bytes(begin, count * 8) else {
        return json!({ "error": "club table unreadable" });
    };

    let mut type_counts: BTreeMap<u8, u32> = BTreeMap::new();
    let mut unmapped: BTreeMap<u8, Vec<Value>> = BTreeMap::new();
    let mut feeder_hunts: Vec<Value> = Vec::new(); // partner 933 anywhere
    let mut clubs_with_vec = 0u32;
    let mut links_total = 0u32;

    for index in 0..count {
        let club_ptr = u64::from_le_bytes(array[index * 8..index * 8 + 8].try_into().unwrap());
        if !looks_heap(club_ptr) {
            continue;
        }
        let Some(vec_begin) = reader.read_pointer(club_ptr + AFFIL_VEC_OFF) else {
            continue;
        };
        let Some(vec_end) = reader.read_pointer(club_ptr + AFFIL_VEC_OFF + 8) else {
            continue;
        };
        if !looks_heap(vec_begin) || vec_end <= vec_begin {
            continue;
        }
        let span = (vec_end - vec_begin) as usize;
        if span % 8 != 0 {
            continue;
        }
        let slots = span / 8;
        if !(1..=MAX_SLOTS).contains(&slots) {
            continue;
        }
        let Some(payload) = reader.read_bytes(vec_begin, span) else {
            continue;
        };
        clubs_with_vec += 1;

        let club_uid = reader.read_u32(club_ptr + uid_off).unwrap_or(0);
        let club_name = reader
            .read_fm_string_pointer(club_ptr + name_off)
            .unwrap_or_default();

        for slot in 0..slots {
            let wrapper = u64::from_le_bytes(payload[slot * 8..slot * 8 + 8].try_into().unwrap());
            if !looks_heap(wrapper) {
                continue;
            }
            let Some(wrap) = reader.read_bytes(wrapper, 0x40) else {
                continue;
            };
            let type_b = wrap[TYPE_OFF];
            *type_counts.entry(type_b).or_insert(0) += 1;
            links_total += 1;

            let nested = u64::from_le_bytes(wrap[8..16].try_into().unwrap());
            let mut partner_uid = 0u32;
            if looks_heap(nested) {
                if let Some(nobj) = reader.read_bytes(nested, 0x20) {
                    partner_uid = u32::from_le_bytes(nobj[PARTNER_UID_OFF..PARTNER_UID_OFF + 4].try_into().unwrap());
                }
            }

            if partner_uid == 933 {
                feeder_hunts.push(json!({
                    "clubUid": club_uid,
                    "clubName": club_name,
                    "slot": slot,
                    "type": type_b,
                    "typeHex": format!("0x{type_b:02X}"),
                    "mapped": mapped_label(type_b),
                    "wrapper": format!("0x{wrapper:X}"),
                }));
            }

            if mapped_label(type_b).is_some() {
                continue;
            }

            let list = unmapped.entry(type_b).or_default();
            if list.len() >= 12 {
                continue;
            }
            // Dedup same club+partner
            let dup = list.iter().any(|row| {
                row["clubUid"].as_u64() == Some(club_uid as u64)
                    && row["partnerUid"].as_u64() == Some(partner_uid as u64)
            });
            if dup {
                continue;
            }
            list.push(json!({
                "clubUid": club_uid,
                "clubName": club_name,
                "slot": slot,
                "partnerUid": partner_uid,
                "wrapper": format!("0x{wrapper:X}"),
                "nested": format!("0x{nested:X}"),
            }));
        }
    }

    let mut unmapped_summary = Vec::new();
    for (type_b, samples) in &unmapped {
        unmapped_summary.push(json!({
            "type": type_b,
            "typeHex": format!("0x{type_b:02X}"),
            "sampleCount": samples.len(),
            "totalSeen": type_counts.get(type_b).copied().unwrap_or(0),
            "samples": samples,
            "askUser": format!(
                "Open club '{}' (uid {}) in PGE → Current Affiliations → partner uid {} → read Affiliation Type",
                samples.first().and_then(|s| s["clubName"].as_str()).unwrap_or("?"),
                samples.first().and_then(|s| s["clubUid"].as_u64()).unwrap_or(0),
                samples.first().and_then(|s| s["partnerUid"].as_u64()).unwrap_or(0),
            ),
        }));
    }

    let mapped_set: BTreeSet<u8> = MAPPED.iter().map(|(b, _)| *b).collect();
    let type_histogram: Vec<Value> = type_counts
        .iter()
        .map(|(b, n)| {
            json!({
                "type": b,
                "typeHex": format!("0x{b:02X}"),
                "count": n,
                "mapped": mapped_label(*b),
                "unmapped": !mapped_set.contains(b),
            })
        })
        .collect();

    eprintln!(
        "affil-type-census: clubsWithVec={clubs_with_vec} links={links_total} distinctTypes={} unmappedTypes={} duisburgAsPartner={}",
        type_counts.len(),
        unmapped.len(),
        feeder_hunts.len()
    );

    json!({
        "probe": "affiliation-type-census",
        "clubTableCount": count,
        "clubsWithAffilVec": clubs_with_vec,
        "linksTotal": links_total,
        "mappedTypes": MAPPED.iter().map(|(b, n)| json!({ "typeHex": format!("0x{b:02X}"), "label": n })).collect::<Vec<_>>(),
        "typeHistogram": type_histogram,
        "unmappedTypes": unmapped_summary,
        "duisburg933AsPartner": feeder_hunts,
        "purpose": "Find clubs whose +0x118 wrappers use type bytes not yet labeled; user confirms in PGE",
    })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn probe_affiliation_type_census(
    _reader: &mut (),
    _module: (),
    _profile: &(),
) -> Value {
    json!({ "error": "windows only" })
}
