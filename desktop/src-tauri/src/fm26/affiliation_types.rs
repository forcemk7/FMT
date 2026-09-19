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
/// FMLE “Players Go On Loan” on nested agreement (`nested+0x65`).
///
/// **Superseded by T287 — see `PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET` below.**
/// Kept only as the historical record; `nested_players_go_on_loan` is no
/// longer called from production. Proven wrong 2026-09-20: Legia has a live,
/// confirmed-active loan agreement (real loaned players there) and reads
/// `0x00` at `nested+0x65` — identical to the true-off control clubs.
///
/// History (kept as enum-ish, not a bool):
/// - T245 (2026-09-06): Schalke Legia/Sparta/KL=`1`, Daegu/Melbourne=`0` → production kept `==1`.
/// - T286 (2026-09-11): same clubs live, loan-on=`2`, loan-off=`0` → kept any **non-zero**.
/// - T287 (2026-09-20): field does not live here at all — moved to the wrapper record.
pub(crate) const PLAYERS_GO_ON_LOAN_NESTED_OFFSET: usize = 0x65;
/// Historical T245 sample on-value (do not use as sole keep check — see T286).
pub(crate) const PLAYERS_GO_ON_LOAN_ON_T245: u8 = 1;
/// Live Schalke 2026-09-11 observed on-value (Legia / Sparta / KL).
pub(crate) const PLAYERS_GO_ON_LOAN_ON_OBSERVED_2026_09_11: u8 = 2;
pub(crate) const PLAYERS_GO_ON_LOAN_OFF: u8 = 0;

/// True when nested agreement has Players-Go-On-Loan (non-zero at `+0x65`).
/// **Historical only — see `wrapper_players_go_on_loan` (T287).**
pub(crate) fn nested_players_go_on_loan(nested_bytes: &[u8]) -> bool {
    nested_bytes
        .get(PLAYERS_GO_ON_LOAN_NESTED_OFFSET)
        .copied()
        .is_some_and(|b| b != PLAYERS_GO_ON_LOAN_OFF)
}

/// FMLE "Players Go On Loan" — **locked T287 (2026-09-20)**, on the
/// **wrapper** record (one hop up from nested), not nested+0x65.
///
/// Cross-validated against FMLE's own labeled checkbox for all 6 named
/// Schalke feeders on the live save: reads `0xFE` for Kaiserslautern, Legia,
/// Sparta Praha (FMLE: Players Go On Loan = True for exactly these three)
/// and `0x6C` for Daegu, Melbourne, Schalke II (FMLE: absent/False) — 7/7
/// links including two (Schalke II 0x08, Sevilla 0x11) that aren't even the
/// same affiliation type as Legia, ruling out a type-byte confound.
///
/// Keep rule mirrors the nested-byte lesson: anchor on the **off** value
/// (stable across two independent checks so far) rather than the on value
/// (`0xFE` here is a single sample — could drift the way nested+0x65's
/// on-value drifted `1→2` between T245 and T286). If a future session
/// contradicts this, re-diff via `probe-loan-flag`'s `wrapperSeparators`
/// before re-hardening either value.
pub(crate) const PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET: usize = 0x2E;
pub(crate) const PLAYERS_GO_ON_LOAN_WRAPPER_OFF_T287: u8 = 0x6C;

/// True when the wrapper record has Players-Go-On-Loan set (T287 lock).
pub(crate) fn wrapper_players_go_on_loan(wrapper_bytes: &[u8]) -> bool {
    wrapper_bytes
        .get(PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET)
        .copied()
        .is_some_and(|b| b != PLAYERS_GO_ON_LOAN_WRAPPER_OFF_T287)
}

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
        0x04 => Some("B Club"), // Barcelona save 2026-09-18: PGE-confirmed (Barcelona B).
        0x08 => Some("II Club"),
        0x10 => Some("Good Relations"),
        0x11 => Some("Likely Friendly"),
        _ => None,
    }
}

/// Types that become FMT Squad tabs (separate-club reserves). Expand as bytes are mapped.
pub(crate) fn is_squad_tab_affiliation_type(type_byte: u8) -> bool {
    matches!(type_byte, 0x08 | 0x04) // II Club, B Club — Sub/C/2/3 when discovered
}

/// Match-experience feeders (not Squad tabs): Normal `0x01` + Schalke feeder byte `0x03`.
pub(crate) fn is_match_experience_feeder_type(type_byte: u8) -> bool {
    matches!(type_byte, 0x01 | 0x03)
}

/// Types whose club teams are loaded for Match experience (and Squad when also squad-tab).
pub(crate) fn is_roster_load_affiliation_type(type_byte: u8) -> bool {
    matches!(type_byte, 0x01 | 0x03 | 0x08 | 0x04) // Normal | feeder 0x03 | II Club | B Club
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
    /// Nested partner/UID record bytes when readable.
    pub nested_bytes: Vec<u8>,
}

#[derive(Debug, Clone)]
pub(crate) struct AffiliationTypeWalk {
    pub links: Vec<AffiliationLinkSighting>,
    pub unmapped_type_bytes: Vec<u8>,
}

/// Bytes read from each affiliation wrapper for flag hunting.
pub(crate) const AFFILIATION_WRAPPER_PROBE_BYTES: usize = 0x80;
/// Bytes read from nested partner record (must cover Players-Go-On-Loan @ +0x65).
pub(crate) const AFFILIATION_NESTED_PROBE_BYTES: usize = 0x80;

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

/// Bit positions where loan-on clubs share bit=1 and loan-off share bit=0 (or reverse).
/// Returns (byte_offset, bit_index_0_7, loan_on_bit_is_one).
pub(crate) fn find_stable_bit_separators(
    loan_on: &[Vec<u8>],
    loan_off: &[Vec<u8>],
) -> Vec<(usize, u8, bool)> {
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
        for bit in 0u8..8 {
            let mask = 1u8 << bit;
            let on_set = loan_on
                .iter()
                .map(|b| b[offset] & mask != 0)
                .collect::<Vec<_>>();
            let off_set = loan_off
                .iter()
                .map(|b| b[offset] & mask != 0)
                .collect::<Vec<_>>();
            if on_set.is_empty() || off_set.is_empty() {
                continue;
            }
            let on_all = on_set.iter().all(|&v| v);
            let on_none = on_set.iter().all(|&v| !v);
            let off_all = off_set.iter().all(|&v| v);
            let off_none = off_set.iter().all(|&v| !v);
            if on_all && off_none {
                out.push((offset, bit, true));
            } else if on_none && off_all {
                out.push((offset, bit, false));
            }
        }
    }
    out
}

/// Offsets where every loan_on blob is non-zero and every loan_off blob is
/// exactly zero (or the reverse). Different criterion than
/// `find_stable_u8_separators` — catches a presence/absence field (e.g. a
/// pointer to a sub-record that only exists when set) whose *value* differs
/// per club (so no single shared on-value exists) but whose *zero-ness*
/// doesn't. Returns (byte_offset, on_side_is_nonzero).
pub(crate) fn find_stable_nonzero_separators(
    loan_on: &[Vec<u8>],
    loan_off: &[Vec<u8>],
) -> Vec<(usize, bool)> {
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
        let on_all_nonzero = loan_on.iter().all(|b| b[offset] != 0);
        let on_all_zero = loan_on.iter().all(|b| b[offset] == 0);
        let off_all_nonzero = loan_off.iter().all(|b| b[offset] != 0);
        let off_all_zero = loan_off.iter().all(|b| b[offset] == 0);
        if on_all_nonzero && off_all_zero {
            out.push((offset, true));
        } else if on_all_zero && off_all_nonzero {
            out.push((offset, false));
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
            "nestedLen": l.nested_bytes.len(),
            "playersGoOnLoanByte": l.nested_bytes.get(PLAYERS_GO_ON_LOAN_NESTED_OFFSET).copied(),
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
        affiliation_type_label, find_stable_bit_separators, find_stable_nonzero_separators,
        find_stable_u8_separators, is_match_experience_feeder_type,
        is_roster_load_affiliation_type, is_squad_tab_affiliation_type,
        nested_players_go_on_loan, schalke_loan_off_name, schalke_loan_on_name,
        wrapper_players_go_on_loan, PLAYERS_GO_ON_LOAN_NESTED_OFFSET,
        PLAYERS_GO_ON_LOAN_ON_OBSERVED_2026_09_11, PLAYERS_GO_ON_LOAN_ON_T245,
        PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET, PLAYERS_GO_ON_LOAN_WRAPPER_OFF_T287,
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
    fn b_club_byte_0x04_loads_roster_and_shows_as_squad_tab() {
        assert!(is_roster_load_affiliation_type(0x04));
        assert!(is_squad_tab_affiliation_type(0x04));
        assert!(!is_match_experience_feeder_type(0x04));
        assert_eq!(affiliation_type_label(0x04), Some("B Club"));
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

    #[test]
    fn stable_bit_separator_finds_flag_bit() {
        let on = vec![vec![0b0000_0100], vec![0b0000_0100]];
        let off = vec![vec![0b0000_0000], vec![0b0000_0001]];
        let bits = find_stable_bit_separators(&on, &off);
        assert!(bits.contains(&(0, 2, true)));
    }

    #[test]
    fn stable_nonzero_separator_finds_presence_field_with_differing_on_values() {
        // T287 Legia case: "on" clubs share no single value at this offset
        // (0x30 vs 0x90) so find_stable_u8_separators misses it entirely —
        // but both are non-zero while every "off" club is exactly zero.
        let on = vec![vec![0u8, 0x30, 0x02], vec![0u8, 0x90, 0x02]];
        let off = vec![vec![0u8, 0x00, 0x02], vec![0u8, 0x00, 0x02]];
        let seps = find_stable_nonzero_separators(&on, &off);
        assert!(seps.contains(&(1, true)));
        // Offset 2 is non-zero on both sides — not a separator.
        assert!(!seps.iter().any(|(o, _)| *o == 2));
    }

    #[test]
    fn nested_players_go_on_loan_keeps_any_nonzero() {
        let mut t245 = vec![0u8; PLAYERS_GO_ON_LOAN_NESTED_OFFSET + 1];
        t245[PLAYERS_GO_ON_LOAN_NESTED_OFFSET] = PLAYERS_GO_ON_LOAN_ON_T245;
        let mut observed = vec![0u8; PLAYERS_GO_ON_LOAN_NESTED_OFFSET + 1];
        observed[PLAYERS_GO_ON_LOAN_NESTED_OFFSET] = PLAYERS_GO_ON_LOAN_ON_OBSERVED_2026_09_11;
        let off = vec![0u8; PLAYERS_GO_ON_LOAN_NESTED_OFFSET + 1];
        assert!(nested_players_go_on_loan(&t245));
        assert!(nested_players_go_on_loan(&observed));
        assert!(!nested_players_go_on_loan(&off));
        assert!(!nested_players_go_on_loan(&[]));
    }

    #[test]
    fn wrapper_players_go_on_loan_matches_fmle_live_schalke_save() {
        // T287 (2026-09-20): wrapper+0x2E, cross-validated against FMLE's
        // own "Players Go On Loan" checkbox — True for exactly these three,
        // False for Daegu/Melbourne/Schalke II on the same save.
        let mut kaiserslautern = vec![0u8; PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET + 1];
        kaiserslautern[PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET] = 0xFE;
        let mut legia = vec![0u8; PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET + 1];
        legia[PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET] = 0xFE;
        let mut sparta = vec![0u8; PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET + 1];
        sparta[PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET] = 0xFE;
        let mut daegu = vec![0u8; PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET + 1];
        daegu[PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET] = PLAYERS_GO_ON_LOAN_WRAPPER_OFF_T287;
        let mut melbourne = vec![0u8; PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET + 1];
        melbourne[PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET] = PLAYERS_GO_ON_LOAN_WRAPPER_OFF_T287;
        let mut schalke_ii = vec![0u8; PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET + 1];
        schalke_ii[PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET] = PLAYERS_GO_ON_LOAN_WRAPPER_OFF_T287;

        assert!(wrapper_players_go_on_loan(&kaiserslautern));
        assert!(wrapper_players_go_on_loan(&legia));
        assert!(wrapper_players_go_on_loan(&sparta));
        assert!(!wrapper_players_go_on_loan(&daegu));
        assert!(!wrapper_players_go_on_loan(&melbourne));
        assert!(!wrapper_players_go_on_loan(&schalke_ii));
        assert!(!wrapper_players_go_on_loan(&[]));
    }
}
