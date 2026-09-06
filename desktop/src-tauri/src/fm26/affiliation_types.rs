//! Club affiliation type enum on managed `club+0x118` wrappers (`+0x30`).
//!
//! Locked T214 layout:
//! - Vector begin/end at club `+0x118` / `+0x120`
//! - Wrapper `+0x00` = managed club ptr, `+0x08` = nested record
//! - Nested `+0x0C` / `+0x10` = partner club UniqueID
//! - Wrapper `+0x30` = Affiliation Type byte (PGE dropdown)

use serde_json::{json, Value};

#[cfg(target_os = "windows")]
use super::{
    memory::{ModuleInfo, ProcessReader},
    offsets::EntityMapProfile,
    validator,
};

/// Affiliation pointer vector on the club object.
pub(crate) const AFFILIATION_VECTOR_OFFSET: u64 = 0x118;
/// Affiliation Type enum on each wrapper object.
pub(crate) const AFFILIATION_TYPE_OFFSET: usize = 0x30;
/// Partner club UniqueID on the nested record (duplicated at +0x10).
pub(crate) const NESTED_PARTNER_UID_OFFSET: usize = 0x0C;

#[cfg(target_os = "windows")]
const MAX_AFFILIATION_SLOTS: usize = 48;
#[cfg(target_os = "windows")]
const CLUB_TABLE_SLOT: u64 = 0xF8;
#[cfg(target_os = "windows")]
const OFFSET_TABLE_RVA: u64 = 0x4E4_9490;

/// Known PGE Affiliation Type labels for wrapper `+0x30`.
pub(crate) fn affiliation_type_label(type_byte: u8) -> Option<&'static str> {
    match type_byte {
        0x01 => Some("Normal Affiliated Club"),
        // 0x03: Schalke feeders (Legia / Kaiserslautern / …) — PGE label not locked yet.
        0x08 => Some("II Club"),
        0x10 => Some("Good Relations"),
        0x11 => Some("Likely Friendly"),
        _ => None,
    }
}

/// Types that become FMT Squad tabs (separate-club reserves). Expand as bytes are mapped.
pub(crate) fn is_squad_tab_affiliation_type(type_byte: u8) -> bool {
    matches!(type_byte, 0x08) // II Club — Sub/B/C/2/3 when discovered
}

/// Match-experience feeders (not Squad tabs): Normal `0x01` + Schalke feeder byte `0x03`.
pub(crate) fn is_match_experience_feeder_type(type_byte: u8) -> bool {
    matches!(type_byte, 0x01 | 0x03)
}

/// Types whose club teams are loaded for Match experience (and Squad when also squad-tab).
pub(crate) fn is_roster_load_affiliation_type(type_byte: u8) -> bool {
    matches!(type_byte, 0x01 | 0x03 | 0x08) // Normal | feeder 0x03 | II Club
}

/// Reminder string for UI / Diagnostics (mirrors TeamType “Map …” pattern).
pub(crate) fn affiliation_type_map_reminder(type_byte: u8) -> String {
    if let Some(label) = affiliation_type_label(type_byte) {
        label.to_string()
    } else {
        format!("Map AffiliationType 0x{type_byte:02X}")
    }
}

#[derive(Debug, Clone)]
pub(crate) struct AffiliationLinkSighting {
    pub partner_uid: u32,
    pub type_byte: u8,
    pub wrapper: u64,
    pub nested: u64,
    pub squad_tab: bool,
    pub mapped_label: Option<&'static str>,
    /// Wrapper object bytes (for flag diffs: loan / Main / Permanent / …).
    pub wrapper_bytes: Vec<u8>,
    /// Nested agreement record bytes when readable.
    pub nested_bytes: Vec<u8>,
}

#[derive(Debug, Clone)]
pub(crate) struct AffiliationTypeWalk {
    pub links: Vec<AffiliationLinkSighting>,
    pub unmapped_type_bytes: Vec<u8>,
}

/// Bytes read from each affiliation wrapper for flag hunting.
pub(crate) const AFFILIATION_WRAPPER_PROBE_BYTES: usize = 0x80;
/// Bytes read from nested partner/agreement record.
pub(crate) const AFFILIATION_NESTED_PROBE_BYTES: usize = 0x40;

/// Offsets where every `loan_on` blob shares one u8 value and every `loan_off`
/// blob shares a different u8 — candidates for “Players Go On Loan”.
pub(crate) fn find_stable_u8_separators(
    loan_on: &[Vec<u8>],
    loan_off: &[Vec<u8>],
) -> Vec<(usize, u8, u8)> {
    if loan_on.is_empty() || loan_off.is_empty() {
        return Vec::new();
    }
    let min_len = loan_on
        .iter()
        .chain(loan_off.iter())
        .map(|b| b.len())
        .min()
        .unwrap_or(0);
    let mut out = Vec::new();
    for offset in 0..min_len {
        let Some(on_val) = shared_u8_at(loan_on, offset) else {
            continue;
        };
        let Some(off_val) = shared_u8_at(loan_off, offset) else {
            continue;
        };
        if on_val != off_val {
            out.push((offset, on_val, off_val));
        }
    }
    out
}

fn shared_u8_at(blobs: &[Vec<u8>], offset: usize) -> Option<u8> {
    let first = *blobs.first()?.get(offset)?;
    if blobs.iter().all(|b| b.get(offset).copied() == Some(first)) {
        Some(first)
    } else {
        None
    }
}

/// Schalke ground-truth needles for loan-agreement static diff (case-insensitive contains).
pub(crate) fn schalke_loan_on_name(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    lower.contains("legia") || lower.contains("kaiserslautern") || lower.contains("sparta")
}

pub(crate) fn schalke_loan_off_name(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    lower.contains("daegu") || lower.contains("melbourne")
}

#[cfg(target_os = "windows")]
fn looks_heap(p: u64) -> bool {
    p >= 0x10_000 && p < 0x0000_7FFF_FFFF_FFFF
}

#[cfg(target_os = "windows")]
fn club_table_array(reader: &mut ProcessReader, module: ModuleInfo) -> Option<(u64, usize)> {
    let table = module.base.saturating_add(OFFSET_TABLE_RVA);
    let slot_ptr = reader.read_pointer(table + CLUB_TABLE_SLOT)?;
    let offset_value = reader.read_pointer(slot_ptr + 0x80)?;
    let begin = reader.read_pointer(offset_value)?;
    let end = reader.read_pointer(offset_value + 8)?;
    if end <= begin || (end - begin) % 8 != 0 {
        return None;
    }
    Some((begin, ((end - begin) / 8) as usize))
}

/// Resolve a club object pointer from UniqueID via the world club table.
#[cfg(target_os = "windows")]
pub(crate) fn resolve_club_ptr_by_uid(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    uid: u32,
) -> Option<(u64, String)> {
    if uid == 0 {
        return None;
    }
    let (begin, count) = club_table_array(reader, module)?;
    let Some(array) = reader.read_bytes(begin, count * 8) else {
        return None;
    };
    let uid_off = profile.constants.entity_uid_offset;
    let name_off = profile.constants.club_name_offset;
    let club_vtable = module.base + profile.constants.club_vtable_rva;
    for index in 0..count {
        let club = u64::from_le_bytes(array[index * 8..index * 8 + 8].try_into().ok()?);
        if !looks_heap(club) {
            continue;
        }
        if validator::validate_vtable(reader, club, club_vtable).is_err() {
            continue;
        }
        let Some(got) = reader.read_u32(club + uid_off) else {
            continue;
        };
        if got != uid {
            continue;
        }
        let name = reader
            .read_fm_string_pointer(club + name_off)
            .unwrap_or_default();
        return Some((club, name));
    }
    None
}

/// Walk `club+0x118` affiliation wrappers; does not resolve partner club objects.
#[cfg(target_os = "windows")]
pub(crate) fn walk_club_affiliation_links(
    reader: &mut ProcessReader,
    club: u64,
) -> AffiliationTypeWalk {
    let mut links = Vec::new();
    let mut unmapped = Vec::new();

    let Some(vec_begin) = reader.read_pointer(club + AFFILIATION_VECTOR_OFFSET) else {
        return AffiliationTypeWalk {
            links,
            unmapped_type_bytes: unmapped,
        };
    };
    let Some(vec_end) = reader.read_pointer(club + AFFILIATION_VECTOR_OFFSET + 8) else {
        return AffiliationTypeWalk {
            links,
            unmapped_type_bytes: unmapped,
        };
    };
    if !looks_heap(vec_begin) || vec_end <= vec_begin {
        return AffiliationTypeWalk {
            links,
            unmapped_type_bytes: unmapped,
        };
    }
    let span = (vec_end - vec_begin) as usize;
    if span % 8 != 0 {
        return AffiliationTypeWalk {
            links,
            unmapped_type_bytes: unmapped,
        };
    }
    let slots = span / 8;
    if !(1..=MAX_AFFILIATION_SLOTS).contains(&slots) {
        return AffiliationTypeWalk {
            links,
            unmapped_type_bytes: unmapped,
        };
    }
    let Some(payload) = reader.read_bytes(vec_begin, span) else {
        return AffiliationTypeWalk {
            links,
            unmapped_type_bytes: unmapped,
        };
    };

    for slot in 0..slots {
        let wrapper = u64::from_le_bytes(payload[slot * 8..slot * 8 + 8].try_into().unwrap());
        if !looks_heap(wrapper) {
            continue;
        }
        let Some(wrap) = reader.read_bytes(wrapper, AFFILIATION_WRAPPER_PROBE_BYTES) else {
            continue;
        };
        let type_byte = wrap[AFFILIATION_TYPE_OFFSET];
        let nested = u64::from_le_bytes(wrap[8..16].try_into().unwrap());
        let mut partner_uid = 0u32;
        let mut nested_bytes = Vec::new();
        if looks_heap(nested) {
            if let Some(nobj) = reader.read_bytes(nested, AFFILIATION_NESTED_PROBE_BYTES) {
                partner_uid = u32::from_le_bytes(
                    nobj[NESTED_PARTNER_UID_OFFSET..NESTED_PARTNER_UID_OFFSET + 4]
                        .try_into()
                        .unwrap(),
                );
                nested_bytes = nobj;
            }
        }
        // Skip self / empty partner noise on Likely Friendly filler slots.
        if partner_uid == 0 {
            continue;
        }
        let mapped_label = affiliation_type_label(type_byte);
        if mapped_label.is_none() && !unmapped.contains(&type_byte) {
            unmapped.push(type_byte);
        }
        links.push(AffiliationLinkSighting {
            partner_uid,
            type_byte,
            wrapper,
            nested,
            squad_tab: is_squad_tab_affiliation_type(type_byte),
            mapped_label,
            wrapper_bytes: wrap,
            nested_bytes,
        });
    }

    unmapped.sort_unstable();
    AffiliationTypeWalk {
        links,
        unmapped_type_bytes: unmapped,
    }
}

#[cfg(target_os = "windows")]
pub(crate) fn affiliation_walk_to_json(walk: &AffiliationTypeWalk) -> Value {
    let mapped = walk
        .links
        .iter()
        .filter(|l| l.mapped_label.is_some())
        .count();
    let unmapped_links = walk
        .links
        .iter()
        .filter(|l| l.mapped_label.is_none())
        .count();
    json!({
        "linkCount": walk.links.len(),
        "mappedLinkCount": mapped,
        "unmappedLinkCount": unmapped_links,
        "unmappedTypeBytes": walk.unmapped_type_bytes.iter().map(|b| format!("0x{b:02X}")).collect::<Vec<_>>(),
        "unmappedReminders": walk.unmapped_type_bytes.iter().map(|b| affiliation_type_map_reminder(*b)).collect::<Vec<_>>(),
        "links": walk.links.iter().map(|l| json!({
            "partnerUid": l.partner_uid,
            "type": l.type_byte,
            "typeHex": format!("0x{:02X}", l.type_byte),
            "label": l.mapped_label.unwrap_or("unmapped"),
            "reminder": affiliation_type_map_reminder(l.type_byte),
            "squadTab": l.squad_tab,
            "wrapper": format!("0x{:X}", l.wrapper),
            "wrapperBytesHex": l.wrapper_bytes.iter().map(|b| format!("{b:02x}")).collect::<String>(),
            "nestedBytesHex": l.nested_bytes.iter().map(|b| format!("{b:02x}")).collect::<String>(),
        })).collect::<Vec<_>>(),
    })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn walk_club_affiliation_links(
    _reader: &mut (),
    _club: u64,
) -> AffiliationTypeWalk {
    AffiliationTypeWalk {
        links: Vec::new(),
        unmapped_type_bytes: Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        affiliation_type_label, find_stable_u8_separators, is_match_experience_feeder_type,
        is_roster_load_affiliation_type, is_squad_tab_affiliation_type, schalke_loan_off_name,
        schalke_loan_on_name,
    };

    #[test]
    fn roster_load_types_include_normal_feeder_and_ii_not_friendly() {
        assert!(is_roster_load_affiliation_type(0x01));
        assert!(is_roster_load_affiliation_type(0x03));
        assert!(is_roster_load_affiliation_type(0x08));
        assert!(!is_roster_load_affiliation_type(0x10));
        assert!(!is_roster_load_affiliation_type(0x11));
        assert!(!is_squad_tab_affiliation_type(0x01));
        assert!(!is_squad_tab_affiliation_type(0x03));
        assert!(is_squad_tab_affiliation_type(0x08));
        assert!(is_match_experience_feeder_type(0x03));
        assert_eq!(
            affiliation_type_label(0x01),
            Some("Normal Affiliated Club")
        );
    }

    #[test]
    fn schalke_loan_needles() {
        assert!(schalke_loan_on_name("Legia Warszawa"));
        assert!(schalke_loan_on_name("1. FC Kaiserslautern"));
        assert!(schalke_loan_on_name("AC Sparta Praha"));
        assert!(schalke_loan_off_name("Daegu FC"));
        assert!(schalke_loan_off_name("Melbourne Victory"));
        assert!(!schalke_loan_on_name("Daegu FC"));
    }

    #[test]
    fn stable_u8_separator_finds_loan_flag() {
        let on = vec![vec![0u8, 1, 9], vec![0u8, 1, 7]];
        let off = vec![vec![0u8, 0, 3], vec![0u8, 0, 4]];
        let seps = find_stable_u8_separators(&on, &off);
        assert!(seps.contains(&(1, 1, 0)));
        assert!(!seps.iter().any(|(o, _, _)| *o == 0));
    }
}
