use serde_json::{json, Value};

use super::blob_scan::diff_hex_blobs;

#[cfg(target_os = "windows")]
use super::{
    blob_scan::{find_u32_hits_in_blob, pointer_hits_in_bytes, relationship_candidates_wide, u8_grid_around},
    memory::{ModuleInfo, ProcessReader},
    offsets::EntityMapProfile,
    scanner::scan_private_memory_for_pointers_in_range,
    validator,
};

/// Club object bytes to harvest embedded team pointers from (FM club blobs can span MBs).
pub(crate) const CLUB_OBJECT_PROBE_BYTES: usize = 512 * 1024;

/// Per-anchor local heap window for team vtable hits (single combined scan per load).
pub(crate) const CLUB_TEAM_HEAP_WINDOW_BYTES: u64 = 64 * 1024 * 1024;

/// Schalke 04 RE lock (2026-08-30): feeder/friendly link pointer vector on managed club.
///
/// Slots 0–2 on Schalke are **feeder catalogs** (many club pointers at +0x0,+0x10,…). B-team is
/// **not** reliably at club @ +0x160 in these slots on current saves (`lockedLayoutStillValid=false`).
/// Kept for forward-compatible graph walks and RE probes — production B-team uses satellite team scan.
pub(crate) const MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET: u64 = 0x8E8;

/// Walk all link-vector slots until relationship-type field locks feeder/friendly semantics.
pub(crate) const BTEAM_LINK_POINTER_SLOTS: usize = 8;

/// Heap affiliate-link struct: club object pointer offset (validated Schalke II @ 0x160).
pub(crate) const AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET: u64 = 0x160;

/// Bytes to read from each heap link struct when resolving the club pointer.
pub(crate) const AFFILIATE_LINK_STRUCT_PROBE_BYTES: usize = 512;

/// Feeder affiliates embed club UID inline ~this region (not pointer-indirected).
pub(crate) const FEEDER_INLINE_UID_SCAN_BYTES: usize = 64 * 1024;

/// Production B-team (German II): satellite team roster band locked on Schalke II @ 33 players.
pub(crate) const BTEAM_SATELLITE_ROSTER_MIN: usize = 28;
pub(crate) const BTEAM_SATELLITE_ROSTER_MAX: usize = 38;

/// Returns true when a heap satellite team looks like the managed club's II / reserves squad.
pub(crate) fn bteam_satellite_team_matches(
    managed_club_name: &str,
    team_name: &str,
    roster_len: usize,
) -> bool {
    if roster_len < BTEAM_SATELLITE_ROSTER_MIN || roster_len > BTEAM_SATELLITE_ROSTER_MAX {
        return false;
    }
    let managed_key = managed_club_name.trim().to_ascii_lowercase();
    let team_key = team_name.trim().to_ascii_lowercase();
    if managed_key.is_empty() || !team_key.contains(&managed_key) {
        return false;
    }
    team_key.contains(" ii") || team_key.ends_with("ii")
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum AffiliateLinkKind {
    BTeam,
    Feeder,
}

#[derive(Debug, Clone)]
pub(crate) struct AffiliateClubDiscovery {
    pub club: u64,
    pub club_uid: u32,
    pub club_name: String,
    pub link_kind: AffiliateLinkKind,
    pub link_struct_pointer: Option<u64>,
}

#[derive(Debug, Clone)]
pub(crate) struct AffiliateTeamDiscovery {
    pub team: u64,
    pub team_uid: u32,
    pub name: String,
    pub roster_len: usize,
    /// Raw TeamType byte when read from the team object (`None` on heap-fallback path).
    pub team_type: Option<u8>,
}

#[cfg(target_os = "windows")]
fn read_club_identity(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    club: u64,
) -> Option<(u32, String)> {
    validator::validate_vtable(reader, club, module.base + profile.constants.club_vtable_rva).ok()?;
    let uid = reader
        .read_u32(club + profile.constants.entity_uid_offset)
        .filter(|uid| *uid > 0)?;
    let name = reader
        .read_fm_string_pointer(club + profile.constants.club_name_offset)
        .unwrap_or_default();
    Some((uid, name))
}

#[cfg(target_os = "windows")]
fn team_roster_len(reader: &mut ProcessReader, profile: &EntityMapProfile, team: u64) -> Option<usize> {
    let start = reader
        .read_pointer(team + profile.constants.team_players_start_offset)
        .filter(|value| *value != 0)?;
    let end = reader
        .read_pointer(team + profile.constants.team_players_end_offset)
        .filter(|value| *value != 0)?;
    if end <= start || (end - start) % 8 != 0 {
        return None;
    }
    let count = ((end - start) / 8) as usize;
    (1..=200).contains(&count).then_some(count)
}

/// Map FM TeamType enum (FMScout / FM22+ layout) to FMT squad unit labels.
///
/// Unknown values return `None` so callers can fall back to name/roster heuristics.
pub(crate) fn squad_unit_from_team_type(team_type: u8) -> Option<&'static str> {
    match team_type {
        0 => Some("firstTeam"),
        // Reserves / A / B / C / Amateur / II / Team2 / Team3 / DutchReserves
        1 | 2 | 3 | 13 | 14 | 15 | 16 | 17 | 30 => Some("reserves"),
        // U23 / U21 / U19 / U18 / U20
        9 | 10 | 11 | 12 | 18 => Some("under19s"),
        // Youth evaluation / intake shells
        22 => Some("reserves"),
        _ => None,
    }
}

/// Fine-grained FMScout TeamType → UI label (tabs / Settings).
///
/// Only used when the team display string is empty or equals the club name.
/// Real distinct FM strings (e.g. `FC Schalke 04 U19`) win over these labels.
pub(crate) fn team_type_display_label(team_type: u8) -> Option<&'static str> {
    match team_type {
        0 => Some("First Team"),
        1 => Some("Reserves"),
        2 => Some("A"),
        3 => Some("B"),
        9 => Some("U23"),
        10 => Some("U21"),
        11 => Some("U19"),
        12 => Some("U18"),
        13 => Some("C"),
        14 => Some("Amateur"),
        15 => Some("II"),
        16 => Some("Team 2"),
        17 => Some("Team 3"),
        18 => Some("U20"),
        22 => Some("Youth"),
        30 => Some("Dutch Reserves"),
        _ => None,
    }
}

/// Squad tab / Settings label: prefer a distinct FM team string; otherwise TeamType.
pub(crate) fn resolve_team_tab_label(
    raw_name: &str,
    club_name: &str,
    team_type: Option<u8>,
    team_uid: u32,
) -> String {
    let trimmed = raw_name.trim();
    let club = club_name.trim();
    let collides =
        trimmed.is_empty() || (!club.is_empty() && trimmed.eq_ignore_ascii_case(club));
    if !collides {
        return trimmed.to_string();
    }
    if let Some(label) = team_type.and_then(team_type_display_label) {
        return label.to_string();
    }
    if !trimmed.is_empty() {
        return trimmed.to_string();
    }
    format!("team-uid-{team_uid}")
}

/// Max teams in a club Teams vector (First + youth sides; not world table).
const MAX_CLUB_TEAMS_VECTOR: usize = 32;

#[cfg(target_os = "windows")]
fn resolve_linked_team(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    team: u64,
    link_clubs: &[(u64, u32)],
) -> Option<AffiliateTeamDiscovery> {
    if team < 0x10000 {
        return None;
    }
    let team_vtable = module.base + profile.constants.team_vtable_rva;
    validator::validate_vtable(reader, team, team_vtable).ok()?;
    let linked_club = reader
        .read_pointer(team + profile.constants.team_club_offset)
        .filter(|value| *value != 0)?;
    if !team_links_any_club(reader, profile, linked_club, link_clubs) {
        return None;
    }
    let roster_len = team_roster_len(reader, profile, team)?;
    let team_uid = reader
        .read_u32(team + profile.constants.entity_uid_offset)
        .unwrap_or(0);
    let name = read_team_display_name(reader, team, profile);
    let team_type = reader.read_u8(team + profile.constants.team_type_offset);
    Some(AffiliateTeamDiscovery {
        team,
        team_uid,
        name,
        roster_len,
        team_type,
    })
}

/// Primary path: Club.Teams MSVC vector at club+start/end.
#[cfg(target_os = "windows")]
fn teams_from_club_teams_vector(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    club: u64,
    link_clubs: &[(u64, u32)],
) -> Vec<AffiliateTeamDiscovery> {
    let Some(start) = reader
        .read_pointer(club + profile.constants.club_teams_start_offset)
        .filter(|value| *value != 0)
    else {
        return Vec::new();
    };
    let Some(end) = reader
        .read_pointer(club + profile.constants.club_teams_end_offset)
        .filter(|value| *value != 0)
    else {
        return Vec::new();
    };
    if end <= start || (end - start) % 8 != 0 {
        return Vec::new();
    }
    let slot_count = ((end - start) / 8) as usize;
    if !(1..=MAX_CLUB_TEAMS_VECTOR).contains(&slot_count) {
        return Vec::new();
    }
    let mut teams = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for index in 0..slot_count {
        let slot = start + (index as u64 * 8);
        let Some(team) = reader.read_pointer(slot).filter(|value| *value != 0) else {
            continue;
        };
        if !seen.insert(team) {
            continue;
        }
        if let Some(resolved) = resolve_linked_team(reader, module, profile, team, link_clubs) {
            teams.push(resolved);
        }
    }
    teams
}

/// Schalke RE lock (2026-08-31): fm-string display name on team object.
pub(crate) const TEAM_NAME_OFFSET: u64 = 0x18;

/// Short display name (e.g. "Schalke 04 U19") — optional fallback after full name @ +0x18.
pub(crate) const TEAM_SHORT_NAME_OFFSET: u64 = 0x20;

#[cfg(target_os = "windows")]
pub(crate) fn read_team_display_name(
    reader: &mut ProcessReader,
    team: u64,
    profile: &EntityMapProfile,
) -> String {
    for offset in [
        profile.constants.team_name_offset,
        profile.constants.team_short_name_offset,
    ] {
        if let Some(name) = reader
            .read_fm_string_pointer(team + offset)
            .filter(|value| !value.trim().is_empty())
        {
            return name;
        }
        if let Some(pointer) = reader
            .read_pointer(team + offset)
            .filter(|value| *value != 0)
        {
            if let Some(name) = reader
                .read_fm_string_at(pointer)
                .filter(|value| !value.trim().is_empty())
            {
                return name;
            }
        }
    }
    if let Some(club) = reader
        .read_pointer(team + profile.constants.team_club_offset)
        .filter(|value| *value != 0)
    {
        if let Some(name) = reader
            .read_fm_string_pointer(club + profile.constants.club_name_offset)
            .filter(|value| !value.trim().is_empty())
        {
            return name;
        }
    }
    String::new()
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn read_team_display_name(
    _reader: &mut super::memory::ProcessReader,
    _team: u64,
    _profile: &EntityMapProfile,
) -> String {
    String::new()
}

#[cfg(target_os = "windows")]
fn seed_team_candidates_from_club_blob(
    reader: &mut ProcessReader,
    club: u64,
    candidate_teams: &mut std::collections::HashSet<u64>,
) {
    let Some(blob) = reader.read_bytes(club, CLUB_OBJECT_PROBE_BYTES) else {
        return;
    };
    for offset in (0..blob.len().saturating_sub(7)).step_by(8) {
        let team = u64::from_le_bytes(blob[offset..offset + 8].try_into().expect("aligned"));
        if team != 0 {
            candidate_teams.insert(team);
        }
    }
}

#[cfg(target_os = "windows")]
fn seed_team_candidates_near_anchors(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    anchors: &[u64],
    candidate_teams: &mut std::collections::HashSet<u64>,
) {
    if anchors.is_empty() {
        return;
    }
    let team_vtable = module.base + profile.constants.team_vtable_rva;
    let window = CLUB_TEAM_HEAP_WINDOW_BYTES;
    let mut scan_min = u64::MAX;
    let mut scan_max = 0_u64;
    for anchor in anchors {
        if *anchor == 0 {
            continue;
        }
        scan_min = scan_min.min(anchor.saturating_sub(window));
        scan_max = scan_max.max(anchor.saturating_add(window));
    }
    if scan_min == u64::MAX {
        return;
    }
    if let Ok(hits) = scan_private_memory_for_pointers_in_range(
        reader,
        &[team_vtable],
        scan_min,
        scan_max,
    ) {
        if let Some(addresses) = hits.get(&team_vtable) {
            candidate_teams.extend(addresses.iter().copied());
        }
    }
}

#[cfg(target_os = "windows")]
fn team_links_any_club(
    reader: &mut ProcessReader,
    profile: &EntityMapProfile,
    linked_club: u64,
    clubs: &[(u64, u32)],
) -> bool {
    clubs.iter().any(|(club, club_uid)| {
        linked_club == *club
            || reader
                .read_u32(linked_club + profile.constants.entity_uid_offset)
                .is_some_and(|uid| uid == *club_uid)
    })
}

#[cfg(target_os = "windows")]
fn teams_for_club(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    club: u64,
    club_uid: u32,
    _heap_anchors: &[u64],
    _extra_team_seeds: &[u64],
    alternate_link_clubs: &[(u64, u32)],
) -> Vec<AffiliateTeamDiscovery> {
    let mut link_clubs = vec![(club, club_uid)];
    for entry in alternate_link_clubs {
        if !link_clubs.iter().any(|(existing, _)| existing == &entry.0) {
            link_clubs.push(*entry);
        }
    }

    // Locked path only (T200/T201): Club.Teams MSVC vector. No heap-window fallback.
    let mut teams = teams_from_club_teams_vector(reader, module, profile, club, &link_clubs);
    teams.sort_by(|left, right| {
        right
            .roster_len
            .cmp(&left.roster_len)
            .then_with(|| left.name.cmp(&right.name))
    });
    teams
}

#[cfg(target_os = "windows")]
fn club_uid_is_inline_on_managed_blob(
    reader: &mut ProcessReader,
    managed_club: u64,
    club_uid: u32,
) -> bool {
    let blob = reader
        .read_bytes(managed_club, FEEDER_INLINE_UID_SCAN_BYTES)
        .unwrap_or_default();
    !find_u32_hits_in_blob(&blob, club_uid).is_empty()
}

/// FM sentinel / misread UIDs from non-club pointers at +0x160.
#[cfg(target_os = "windows")]
fn is_plausible_affiliate_club_uid(club_uid: u32, managed_club_uid: u32) -> bool {
    club_uid > 0 && club_uid != 32_767 && club_uid != managed_club_uid
}

/// B-team club objects reference the managed parent; feeder catalog entries do not.
#[cfg(target_os = "windows")]
fn affiliate_club_has_parent_pointer(
    reader: &mut ProcessReader,
    affiliate_club: u64,
    managed_club: u64,
) -> bool {
    let Some(blob) = reader.read_bytes(affiliate_club, CLUB_OBJECT_PROBE_BYTES) else {
        return false;
    };
    !pointer_hits_in_bytes(&blob, managed_club).is_empty()
}

#[cfg(target_os = "windows")]
fn affiliate_club_links_to_managed_parent(
    reader: &mut ProcessReader,
    affiliate_club: u64,
    managed_club: u64,
    managed_club_uid: u32,
) -> bool {
    if affiliate_club_has_parent_pointer(reader, affiliate_club, managed_club) {
        return true;
    }
    let Some(blob) = reader.read_bytes(affiliate_club, CLUB_OBJECT_PROBE_BYTES) else {
        return false;
    };
    !find_u32_hits_in_blob(&blob, managed_club_uid).is_empty()
}

#[cfg(target_os = "windows")]
fn count_club_pointers_in_blob(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    blob: &[u8],
) -> usize {
    club_pointers_in_object_blob(reader, module, profile, blob).len()
}

/// Feeder/friendly catalogs pack many club pointers at +0x0,+0x10,…; B-team link structs hold one club.
#[cfg(target_os = "windows")]
fn link_struct_is_feeder_catalog(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    link_blob: &[u8],
) -> bool {
    count_club_pointers_in_blob(reader, module, profile, link_blob) > 1
}

#[cfg(target_os = "windows")]
fn try_push_bteam_affiliate(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    affiliate_club: u64,
    club_uid: u32,
    club_name: String,
    link_struct_pointer: Option<u64>,
    link_struct_proves_edge: bool,
    seen_uids: &mut std::collections::HashSet<u32>,
    found: &mut Vec<AffiliateClubDiscovery>,
    log_label: &str,
) {
    if !is_plausible_affiliate_club_uid(club_uid, managed_club_uid) || !seen_uids.insert(club_uid) {
        return;
    }
    if club_uid_is_inline_on_managed_blob(reader, managed_club, club_uid) {
        return;
    }
    if !link_struct_proves_edge
        && !affiliate_club_links_to_managed_parent(
            reader,
            affiliate_club,
            managed_club,
            managed_club_uid,
        )
    {
        return;
    }
    crate::fmt_log::load_detail(format!(
        "b-team {log_label} → club uid {club_uid} ({})",
        club_name.trim()
    ));
    found.push(AffiliateClubDiscovery {
        club: affiliate_club,
        club_uid,
        club_name,
        link_kind: AffiliateLinkKind::BTeam,
        link_struct_pointer,
    });
}

#[cfg(target_os = "windows")]
fn club_pointers_in_object_blob(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    blob: &[u8],
) -> Vec<(usize, u64, u32, String)> {
    let club_vtable = module.base + profile.constants.club_vtable_rva;
    let mut hits = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for offset in (0..blob.len().saturating_sub(7)).step_by(8) {
        let pointer = u64::from_le_bytes(blob[offset..offset + 8].try_into().expect("aligned"));
        if pointer == 0 || !seen.insert(pointer) {
            continue;
        }
        if validator::validate_vtable(reader, pointer, club_vtable).is_err() {
            continue;
        }
        let Some((club_uid, club_name)) = read_club_identity(reader, module, profile, pointer) else {
            continue;
        };
        hits.push((offset, pointer, club_uid, club_name));
    }
    hits
}

/// Extended managed-club scan for indirect affiliate link structs (matches club_affiliates RE).
const MANAGED_CLUB_EXTENDED_SCAN_BYTES: usize = 4 * 1024 * 1024;

/// Max indirect heap structs to probe per load (managed club blob → link struct → club).
const MAX_INDIRECT_LINK_STRUCT_PROBES: usize = 512;

/// B-team club objects usually sit within a few MB of the managed club (not full 64MB team window).
const BTEAM_CLUB_HEAP_WINDOW_BYTES: u64 = 8 * 1024 * 1024;

/// Bytes before a managed-club pointer hit when treating heap slices as affiliate link structs.
const HEAP_LINK_POINTER_CONTEXT_BYTES: usize = 128;

#[cfg(target_os = "windows")]
fn discover_bteam_from_heap_managed_pointer_backrefs(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    seen_uids: &mut std::collections::HashSet<u32>,
) -> Vec<AffiliateClubDiscovery> {
    let scan_min = managed_club.saturating_sub(BTEAM_CLUB_HEAP_WINDOW_BYTES);
    let scan_max = managed_club.saturating_add(BTEAM_CLUB_HEAP_WINDOW_BYTES);
    let Ok(hits) = scan_private_memory_for_pointers_in_range(
        reader,
        &[managed_club],
        scan_min,
        scan_max,
    ) else {
        return Vec::new();
    };
    let Some(ref_addrs) = hits.get(&managed_club) else {
        return Vec::new();
    };
    let mut found = Vec::new();
    let mut seen_struct_starts = std::collections::HashSet::new();
    for ref_addr in ref_addrs {
        if *ref_addr < scan_min || *ref_addr > scan_max {
            continue;
        }
        let struct_start = ref_addr.saturating_sub(HEAP_LINK_POINTER_CONTEXT_BYTES as u64);
        if !seen_struct_starts.insert(struct_start) {
            continue;
        }
        let Some(link_blob) = reader.read_bytes(struct_start, AFFILIATE_LINK_STRUCT_PROBE_BYTES) else {
            continue;
        };
        push_bteam_clubs_from_link_struct(
            reader,
            module,
            profile,
            managed_club,
            managed_club_uid,
            struct_start,
            &link_blob,
            seen_uids,
            &mut found,
            &format!("heap backref link struct @0x{struct_start:X}"),
        );
    }
    found
}

#[cfg(target_os = "windows")]
fn push_bteam_clubs_from_link_struct(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    link_struct: u64,
    link_blob: &[u8],
    seen_uids: &mut std::collections::HashSet<u32>,
    found: &mut Vec<AffiliateClubDiscovery>,
    log_label: &str,
) {
    if link_struct_is_feeder_catalog(reader, module, profile, link_blob) {
        return;
    }
    let struct_proves_edge = !find_u32_hits_in_blob(link_blob, managed_club_uid).is_empty()
        || !pointer_hits_in_bytes(link_blob, managed_club).is_empty();
    let clubs = club_pointers_in_object_blob(reader, module, profile, link_blob);
    if struct_proves_edge {
        for (_club_offset, affiliate_club, club_uid, club_name) in clubs {
            try_push_bteam_affiliate(
                reader,
                module,
                profile,
                managed_club,
                managed_club_uid,
                affiliate_club,
                club_uid,
                club_name,
                Some(link_struct),
                true,
                seen_uids,
                found,
                log_label,
            );
        }
        return;
    }
    let Some(affiliate_club) = reader
        .read_pointer(link_struct + AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET)
        .filter(|value| *value != 0)
    else {
        return;
    };
    let Some((club_uid, club_name)) =
        read_club_identity(reader, module, profile, affiliate_club)
    else {
        return;
    };
    try_push_bteam_affiliate(
        reader,
        module,
        profile,
        managed_club,
        managed_club_uid,
        affiliate_club,
        club_uid,
        club_name,
        Some(link_struct),
        false,
        seen_uids,
        found,
        log_label,
    );
}

/// Managed club blob → heap link struct that embeds managed UID + a single affiliate club pointer.
#[cfg(target_os = "windows")]
fn discover_bteam_from_affiliate_link_structs(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    seen_uids: &mut std::collections::HashSet<u32>,
) -> Vec<AffiliateClubDiscovery> {
    let Some(managed_blob) = reader.read_bytes(managed_club, MANAGED_CLUB_EXTENDED_SCAN_BYTES) else {
        return Vec::new();
    };
    let mut found = Vec::new();
    let mut probed = 0usize;
    for offset in (0..managed_blob.len().saturating_sub(7)).step_by(8) {
        if probed >= MAX_INDIRECT_LINK_STRUCT_PROBES {
            break;
        }
        let link_struct = u64::from_le_bytes(
            managed_blob[offset..offset + 8]
                .try_into()
                .expect("aligned"),
        );
        if link_struct < 0x10_000 || link_struct == managed_club {
            continue;
        }
        probed += 1;
        let Some(link_blob) = reader.read_bytes(link_struct, AFFILIATE_LINK_STRUCT_PROBE_BYTES) else {
            continue;
        };
        if find_u32_hits_in_blob(&link_blob, managed_club_uid).is_empty()
            && pointer_hits_in_bytes(&link_blob, managed_club).is_empty()
        {
            continue;
        }
        push_bteam_clubs_from_link_struct(
            reader,
            module,
            profile,
            managed_club,
            managed_club_uid,
            link_struct,
            &link_blob,
            seen_uids,
            &mut found,
            &format!("affiliate link struct (managed+0x{offset:X})"),
        );
    }
    found
}

#[cfg(target_os = "windows")]
fn discover_bteam_via_indirect_managed_pointers(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    seen_uids: &mut std::collections::HashSet<u32>,
) -> Vec<AffiliateClubDiscovery> {
    discover_bteam_from_affiliate_link_structs(
        reader,
        module,
        profile,
        managed_club,
        managed_club_uid,
        seen_uids,
    )
}

#[cfg(target_os = "windows")]
fn clubs_share_affiliate_graph_edge(
    reader: &mut ProcessReader,
    managed_club: u64,
    affiliate_club: u64,
    managed_blob: &[u8],
) -> bool {
    if !pointer_hits_in_bytes(managed_blob, affiliate_club).is_empty() {
        return true;
    }
    let Some(affiliate_blob) = reader.read_bytes(affiliate_club, CLUB_OBJECT_PROBE_BYTES) else {
        return false;
    };
    !pointer_hits_in_bytes(&affiliate_blob, managed_club).is_empty()
}

#[cfg(target_os = "windows")]
fn discover_bteam_from_managed_club_blob(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    seen_uids: &mut std::collections::HashSet<u32>,
) -> Vec<AffiliateClubDiscovery> {
    let Some(blob) = reader.read_bytes(managed_club, CLUB_OBJECT_PROBE_BYTES) else {
        return Vec::new();
    };
    let mut found = Vec::new();
    for (_offset, club, club_uid, club_name) in
        club_pointers_in_object_blob(reader, module, profile, &blob)
    {
        if club == managed_club
            || club_uid == managed_club_uid
            || !seen_uids.insert(club_uid)
        {
            continue;
        }
        if club_uid_is_inline_on_managed_blob(reader, managed_club, club_uid) {
            continue;
        }
        if !affiliate_club_links_to_managed_parent(reader, club, managed_club, managed_club_uid) {
            continue;
        }
        if !clubs_share_affiliate_graph_edge(reader, managed_club, club, &blob) {
            continue;
        }
        found.push(AffiliateClubDiscovery {
            club,
            club_uid,
            club_name,
            link_kind: AffiliateLinkKind::BTeam,
            link_struct_pointer: None,
        });
    }
    found
}

#[cfg(target_os = "windows")]
fn discover_bteam_from_link_vector(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    seen_uids: &mut std::collections::HashSet<u32>,
) -> Vec<AffiliateClubDiscovery> {
    let mut found = Vec::new();
    for slot in 0..BTEAM_LINK_POINTER_SLOTS {
        let field = MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET + (slot as u64 * 8);
        let Some(link_struct) = reader
            .read_pointer(managed_club + field)
            .filter(|value| *value != 0)
        else {
            continue;
        };
        let link_blob = reader
            .read_bytes(link_struct, AFFILIATE_LINK_STRUCT_PROBE_BYTES)
            .unwrap_or_default();
        if let Some(affiliate_club) = reader
            .read_pointer(link_struct + AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET)
            .filter(|value| *value != 0)
        {
            if let Some((club_uid, club_name)) =
                read_club_identity(reader, module, profile, affiliate_club)
            {
                try_push_bteam_affiliate(
                    reader,
                    module,
                    profile,
                    managed_club,
                    managed_club_uid,
                    affiliate_club,
                    club_uid,
                    club_name,
                    Some(link_struct),
                    !find_u32_hits_in_blob(&link_blob, managed_club_uid).is_empty()
                        || !pointer_hits_in_bytes(&link_blob, managed_club).is_empty(),
                    seen_uids,
                    &mut found,
                    &format!("link vector slot {slot} @+0x160"),
                );
            }
        }
        if link_struct_is_feeder_catalog(reader, module, profile, &link_blob) {
            continue;
        }
        push_bteam_clubs_from_link_struct(
            reader,
            module,
            profile,
            managed_club,
            managed_club_uid,
            link_struct,
            &link_blob,
            seen_uids,
            &mut found,
            &format!("link vector slot {slot}"),
        );
    }
    found
}

/// Heap team scan: teams linked to a separate club entity (German II / B-team), not inline feeders.
#[cfg(target_os = "windows")]
fn discover_bteam_from_heap_satellite_teams(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    first_team: u64,
    seen_uids: &mut std::collections::HashSet<u32>,
) -> Vec<AffiliateClubDiscovery> {
    let managed_club_name = read_club_identity(reader, module, profile, managed_club)
        .map(|(_, name)| name)
        .unwrap_or_default();
    let team_vtable = module.base + profile.constants.team_vtable_rva;
    let window = CLUB_TEAM_HEAP_WINDOW_BYTES;
    let mut scan_min = managed_club.saturating_sub(window);
    let mut scan_max = managed_club.saturating_add(window);
    if first_team != 0 {
        scan_min = scan_min.min(first_team.saturating_sub(window));
        scan_max = scan_max.max(first_team.saturating_add(window));
    }
    let Ok(hits) = scan_private_memory_for_pointers_in_range(
        reader,
        &[team_vtable],
        scan_min,
        scan_max,
    ) else {
        return Vec::new();
    };
    let Some(team_addresses) = hits.get(&team_vtable) else {
        return Vec::new();
    };
    let mut found = Vec::new();
    let mut seen_clubs = std::collections::HashSet::new();
    for team in team_addresses {
        if *team == 0 || *team == first_team {
            continue;
        }
        if validator::validate_vtable(reader, *team, team_vtable).is_err() {
            continue;
        }
        let Some(roster_len) = team_roster_len(reader, profile, *team) else {
            continue;
        };
        if roster_len < 10 {
            continue;
        }
        let Some(linked_club) = reader
            .read_pointer(*team + profile.constants.team_club_offset)
            .filter(|value| *value != 0 && *value != managed_club)
        else {
            continue;
        };
        if !seen_clubs.insert(linked_club) {
            continue;
        }
        let Some((club_uid, club_name)) =
            read_club_identity(reader, module, profile, linked_club)
        else {
            continue;
        };
        if roster_len < BTEAM_SATELLITE_ROSTER_MIN || roster_len > BTEAM_SATELLITE_ROSTER_MAX {
            continue;
        }
        let team_name = read_team_display_name(reader, *team, profile);
        if !bteam_satellite_team_matches(&managed_club_name, &team_name, roster_len) {
            continue;
        }
        try_push_bteam_affiliate(
            reader,
            module,
            profile,
            managed_club,
            managed_club_uid,
            linked_club,
            club_uid,
            club_name,
            None,
            true,
            seen_uids,
            &mut found,
            &format!(
                "satellite team {} (roster {roster_len})",
                team_name.trim()
            ),
        );
        if !found.is_empty() {
            break;
        }
    }
    found
}

/// B-team affiliate discovery (German reserves / separate club entity).
///
/// **Production ladder** (Schalke 04 validated 2026-08-31):
/// 1. Link vector @ +0x8E8 — graph walk; skips feeder catalogs (>1 club pointer / struct).
/// 2. **Satellite team heap scan** — primary path on Schalke: team vtable window anchored on
///    managed club + first team → team links to affiliate club → `bteam_satellite_team_matches`.
/// 3. Indirect managed-club pointers → link struct with managed UID/pointer + single club.
/// 4. Heap backrefs to managed club pointer inside link structs.
/// 5. Managed club blob direct club pointers with parent edge.
///
/// Feeders/friendlies excluded via inline UID on managed blob (64KB). No save-specific UID needles.
#[cfg(target_os = "windows")]
pub(crate) fn discover_bteam_affiliate_clubs(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    first_team: u64,
) -> Vec<AffiliateClubDiscovery> {
    let mut seen_uids = std::collections::HashSet::new();
    let mut found = discover_bteam_from_link_vector(
        reader,
        module,
        profile,
        managed_club,
        managed_club_uid,
        &mut seen_uids,
    );
    if found.is_empty() {
        found = discover_bteam_from_heap_satellite_teams(
            reader,
            module,
            profile,
            managed_club,
            managed_club_uid,
            first_team,
            &mut seen_uids,
        );
    }
    if found.is_empty() {
        found = discover_bteam_via_indirect_managed_pointers(
            reader,
            module,
            profile,
            managed_club,
            managed_club_uid,
            &mut seen_uids,
        );
    }
    if found.is_empty() {
        found = discover_bteam_from_heap_managed_pointer_backrefs(
            reader,
            module,
            profile,
            managed_club,
            managed_club_uid,
            &mut seen_uids,
        );
    }
    if found.is_empty() {
        found = discover_bteam_from_managed_club_blob(
            reader,
            module,
            profile,
            managed_club,
            managed_club_uid,
            &mut seen_uids,
        );
    }
    found
}

/// RE-only: dump every managed-club link-vector slot (`@0x8E8`) for FMLE affiliate-flag A/B.
///
/// FMLE UI labels (Main / Permanent / Players Move Freely, …) are editable fields — not proven
/// memory names. Toggle **one** LE control on an affiliate, re-run this probe, diff `structBytesHex`
/// (or use `diff_hex_blobs`) to lock the byte(s) that mark squad-tab reserves.
#[cfg(target_os = "windows")]
pub(crate) fn probe_affiliate_squad_flag_slots(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
) -> Value {
    let mut slots = Vec::new();
    for slot in 0..BTEAM_LINK_POINTER_SLOTS as u64 {
        let field = MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET + slot * 8;
        let link_struct = reader.read_pointer(managed_club + field).unwrap_or(0);
        if link_struct == 0 {
            slots.push(json!({
                "slot": slot,
                "fieldOffsetHex": format!("0x{field:X}"),
                "linkStructPointer": "0x0",
                "empty": true,
            }));
            continue;
        }
        let blob = reader
            .read_bytes(link_struct, AFFILIATE_LINK_STRUCT_PROBE_BYTES)
            .unwrap_or_default();
        let club_at_locked = reader
            .read_pointer(link_struct + AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET)
            .unwrap_or(0);
        let club_identity = (club_at_locked != 0)
            .then(|| read_club_identity(reader, module, profile, club_at_locked))
            .flatten();
        let club_ptr_hits = if club_at_locked != 0 {
            pointer_hits_in_bytes(&blob, club_at_locked)
        } else {
            Vec::new()
        };
        let anchor = club_ptr_hits
            .first()
            .copied()
            .unwrap_or(AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET as usize);
        let feeder_catalog = link_struct_is_feeder_catalog(reader, module, profile, &blob);
        slots.push(json!({
            "slot": slot,
            "fieldOffsetHex": format!("0x{field:X}"),
            "linkStructPointer": format!("0x{link_struct:X}"),
            "clubPointerAtLocked0x160": format!("0x{club_at_locked:X}"),
            "clubUid": club_identity.as_ref().map(|(uid, _)| *uid),
            "clubName": club_identity.as_ref().map(|(_, name)| name.clone()),
            "feederCatalogMultiClub": feeder_catalog,
            "clubPointerHitsInStruct": club_ptr_hits,
            "flagGridAnchorOffset": anchor,
            "u8GridAroundClubPointer": u8_grid_around(&blob, anchor, 64),
            "u32GridAroundClubPointer": relationship_candidates_wide(&blob, anchor),
            "structBytesHex": blob
                .iter()
                .map(|byte| format!("{byte:02x}"))
                .collect::<String>(),
            "structBytesLen": blob.len(),
        }));
    }
    json!({
        "status": "affiliate-squad-flag-slots",
        "purpose": "FMLE A/B: toggle one editable affiliate field, re-probe, diff structBytesHex",
        "hypothesis": "Squad-tab separate-club reserves are affiliate link structs whose flag bytes FMLE edits as Main/Permanent/Players Move Freely (UI labels only — lock bytes, not strings)",
        "managedClubPointer": format!("0x{managed_club:X}"),
        "managedClubUid": managed_club_uid,
        "linkVectorOffset": format!("0x{MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET:X}"),
        "lockedClubPointerOffset": format!("0x{AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET:X}"),
        "slots": slots,
        "humanProtocol": [
            "1. npm run probe:affiliate-flags > before.json (FM save loaded)",
            "2. FMLE: open one affiliate (prefer Schalke II); toggle ONE checkbox only",
            "3. npm run probe:affiliate-flags > after.json",
            "4. python desktop/scripts/diff-affiliate-flag-dumps.py before.json after.json",
            "5. Lock offset(s) that flip on squad-tab affiliates and stay off on feeders",
        ],
        "bytesRead": reader.bytes_read,
    })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn probe_affiliate_squad_flag_slots(
    _reader: &mut super::memory::ProcessReader,
    _module: super::memory::ModuleInfo,
    _profile: &super::offsets::EntityMapProfile,
    _managed_club: u64,
    _managed_club_uid: u32,
) -> Value {
    json!({ "status": "windows_only" })
}

/// Offline helper for unit tests / scripts — re-export blob_scan diff.
pub(crate) fn diff_affiliate_struct_hex(before_hex: &str, after_hex: &str) -> Value {
    json!({
        "changes": diff_hex_blobs(before_hex, after_hex),
        "changeCount": diff_hex_blobs(before_hex, after_hex).len(),
    })
}

/// RE-only: given a verified B-team club object (from Board / FMLE / prior lock), find every
/// structural edge from the managed club that points at it — direct fields, link-vector
/// slots, and club-pointer offsets inside those link structs. No production use.
#[cfg(target_os = "windows")]
pub(crate) fn probe_bteam_link_graph_relock(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    bteam_club: u64,
    bteam_club_uid: u32,
) -> Value {
    let managed_blob = reader
        .read_bytes(managed_club, CLUB_OBJECT_PROBE_BYTES)
        .unwrap_or_default();
    let direct_hits = pointer_hits_in_bytes(&managed_blob, bteam_club);
    let uid_hits = find_u32_hits_in_blob(&managed_blob, bteam_club_uid);

    let mut vector_slots = Vec::new();
    for slot in 0..8u64 {
        let field = MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET + slot * 8;
        let link_struct = reader.read_pointer(managed_club + field).unwrap_or(0);
        if link_struct == 0 {
            vector_slots.push(json!({
                "slot": slot,
                "fieldOffsetHex": format!("0x{field:X}"),
                "linkStructPointer": "0x0",
            }));
            continue;
        }
        let link_blob = reader
            .read_bytes(link_struct, AFFILIATE_LINK_STRUCT_PROBE_BYTES)
            .unwrap_or_default();
        let club_ptr_hits = pointer_hits_in_bytes(&link_blob, bteam_club);
        let locked_at_0x160 = reader
            .read_pointer(link_struct + AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET)
            .unwrap_or(0);
        vector_slots.push(json!({
            "slot": slot,
            "fieldOffsetHex": format!("0x{field:X}"),
            "linkStructPointer": format!("0x{link_struct:X}"),
            "clubPointerAtLocked0x160": format!("0x{locked_at_0x160:X}"),
            "bteamClubPointerOffsetsInStruct": club_ptr_hits.iter().map(|offset| json!({
                "offset": offset,
                "offsetHex": format!("0x{offset:X}"),
                "relationshipCandidates": relationship_candidates_wide(&link_blob, *offset),
            })).collect::<Vec<_>>(),
        }));
    }

    // Any aligned pointer in the managed club blob that is a heap object containing bteam_club.
    let mut indirect_link_structs = Vec::new();
    for offset in (0..managed_blob.len().saturating_sub(7)).step_by(8) {
        let candidate = u64::from_le_bytes(
            managed_blob[offset..offset + 8]
                .try_into()
                .expect("aligned"),
        );
        if candidate == 0 || candidate == managed_club || candidate == bteam_club {
            continue;
        }
        let Some(blob) = reader.read_bytes(candidate, AFFILIATE_LINK_STRUCT_PROBE_BYTES) else {
            continue;
        };
        let hits = pointer_hits_in_bytes(&blob, bteam_club);
        if hits.is_empty() {
            continue;
        }
        if indirect_link_structs.len() >= 24 {
            break;
        }
        indirect_link_structs.push(json!({
            "managedClubFieldOffset": offset,
            "managedClubFieldOffsetHex": format!("0x{offset:X}"),
            "linkStructPointer": format!("0x{candidate:X}"),
            "bteamClubPointerOffsetsInStruct": hits.iter().map(|hit| json!({
                "offset": hit,
                "offsetHex": format!("0x{hit:X}"),
                "relationshipCandidates": relationship_candidates_wide(&blob, *hit),
            })).collect::<Vec<_>>(),
        }));
    }

    let bteam_identity = read_club_identity(reader, module, profile, bteam_club);
    json!({
        "status": "bteam-link-graph-relock",
        "managedClubPointer": format!("0x{managed_club:X}"),
        "managedClubUid": managed_club_uid,
        "bteamClubPointer": format!("0x{bteam_club:X}"),
        "bteamClubUid": bteam_club_uid,
        "bteamClubName": bteam_identity.as_ref().map(|(_, name)| name.clone()),
        "directBteamPointersInManagedClub": direct_hits.iter().map(|offset| json!({
            "offset": offset,
            "offsetHex": format!("0x{offset:X}"),
        })).collect::<Vec<_>>(),
        "inlineBteamUidHitsInManagedClub": uid_hits,
        "vectorSlotsFrom0x8E8": vector_slots,
        "indirectLinkStructsFromManagedClubFields": indirect_link_structs,
        "lockedLayoutStillValid": vector_slots.iter().any(|slot| {
            slot.get("clubPointerAtLocked0x160")
                .and_then(Value::as_str)
                .is_some_and(|value| value.eq_ignore_ascii_case(&format!("0x{bteam_club:X}")))
        }),
        "nextStep": "Pick the smallest stable edge (direct field, or managed→linkStruct→club@offset) that reaches bteam without name/UID needles; update MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET / AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET.",
        "bytesRead": reader.bytes_read,
    })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn probe_bteam_link_graph_relock(
    _reader: &mut super::memory::ProcessReader,
    _module: ModuleInfo,
    _profile: &EntityMapProfile,
    _managed_club: u64,
    _managed_club_uid: u32,
    _bteam_club: u64,
    _bteam_club_uid: u32,
) -> Value {
    json!({ "status": "windows_only" })
}

#[cfg(target_os = "windows")]
pub(crate) fn discover_teams_for_affiliate_club(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    club: u64,
    club_uid: u32,
    heap_anchors: &[u64],
    parent_club: Option<(u64, u32)>,
) -> Vec<AffiliateTeamDiscovery> {
    let alternates = parent_club.map(|entry| vec![entry]).unwrap_or_default();
    teams_for_club(
        reader,
        module,
        profile,
        club,
        club_uid,
        heap_anchors,
        &[],
        &alternates,
    )
}

#[cfg(target_os = "windows")]
pub(crate) fn discover_teams_for_club(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    club: u64,
    club_uid: u32,
    heap_anchors: &[u64],
    extra_team_seeds: &[u64],
) -> Vec<AffiliateTeamDiscovery> {
    teams_for_club(
        reader,
        module,
        profile,
        club,
        club_uid,
        heap_anchors,
        extra_team_seeds,
        &[],
    )
}

#[cfg(target_os = "windows")]
fn feeder_uid_hits_in_managed_club(
    reader: &mut ProcessReader,
    managed_club: u64,
    feeder_uids: &[u32],
) -> Vec<Value> {
    let blob = reader
        .read_bytes(managed_club, FEEDER_INLINE_UID_SCAN_BYTES)
        .unwrap_or_default();
    let mut hits = Vec::new();
    for uid in feeder_uids {
        for offset in find_u32_hits_in_blob(&blob, *uid) {
            hits.push(json!({
                "clubUid": uid,
                "offsetInManagedClub": offset,
                "offsetHex": format!("0x{offset:X}"),
                "relationshipCandidatesWide": relationship_candidates_wide(&blob, offset),
            }));
        }
    }
    hits.sort_by_key(|entry| {
        entry
            .get("offsetInManagedClub")
            .and_then(Value::as_u64)
            .unwrap_or(0)
    });
    hits
}

#[cfg(target_os = "windows")]
pub(crate) fn probe_lock_affiliate_link_layout(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    feeder_uids: &[u32],
) -> Value {
    let bteam_clubs =
        discover_bteam_affiliate_clubs(reader, module, profile, managed_club, managed_club_uid, 0);
    let mut bteam_struct_dumps = Vec::new();
    for affiliate in &bteam_clubs {
        let Some(link_struct) = affiliate.link_struct_pointer else {
            continue;
        };
        let blob = reader
            .read_bytes(link_struct, AFFILIATE_LINK_STRUCT_PROBE_BYTES)
            .unwrap_or_default();
        let club_pointer_hits = pointer_hits_in_bytes(&blob, affiliate.club);
        bteam_struct_dumps.push(json!({
            "clubUid": affiliate.club_uid,
            "clubName": affiliate.club_name,
            "clubPointer": format!("0x{:X}", affiliate.club),
            "linkStructPointer": format!("0x{link_struct:X}"),
            "clubPointerHitsInStruct": club_pointer_hits,
            "lockedClubPointerOffset": AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET,
            "relationshipAtLockedClubPointer": club_pointer_hits.first().map(|offset| {
                relationship_candidates_wide(&blob, *offset)
            }),
            "structBytesHex": blob[..blob.len().min(192)]
                .iter()
                .map(|byte| format!("{byte:02x}"))
                .collect::<String>(),
        }));
    }

    let feeder_hits = feeder_uid_hits_in_managed_club(reader, managed_club, feeder_uids);
    let mut relationship_deltas: std::collections::HashMap<i32, Vec<u32>> =
        std::collections::HashMap::new();
    for hit in &feeder_hits {
        let Some(candidates) = hit
            .get("relationshipCandidatesWide")
            .and_then(Value::as_array)
        else {
            continue;
        };
        for candidate in candidates {
            let delta = candidate
                .get("deltaFromUid")
                .and_then(Value::as_i64)
                .unwrap_or(0) as i32;
            let value = candidate
                .get("u32")
                .and_then(Value::as_u64)
                .unwrap_or(0) as u32;
            relationship_deltas.entry(delta).or_default().push(value);
        }
    }
    let feeder_relationship_field_candidates: Vec<Value> = relationship_deltas
        .into_iter()
        .filter_map(|(delta, values)| {
            let unique: std::collections::HashSet<u32> = values.into_iter().collect();
            if unique.len() == 1 {
                Some(json!({
                    "deltaFromClubUid": delta,
                    "uniformFeederU32": unique.iter().next().copied().unwrap_or(0),
                    "feederOnly": true,
                }))
            } else {
                None
            }
        })
        .collect();

    json!({
        "status": "layout_lock_probe",
        "layout": "affiliate-link-layout-v1-schalke",
        "managedClubPointer": format!("0x{managed_club:X}"),
        "managedClubUid": managed_club_uid,
        "locked": {
            "bteam": {
                "linkVectorOffset": format!("0x{MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET:X}"),
                "linkPointerStrideBytes": 8,
                "linkPointerSlots": BTEAM_LINK_POINTER_SLOTS,
                "heapLinkStructClubPointerOffset": format!("0x{AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET:X}"),
                "resolution": "managedClub + vector → heap struct → club @ +0x160",
            },
            "feeder": {
                "inlineUidMaxScanBytes": FEEDER_INLINE_UID_SCAN_BYTES,
                "resolution": "club UID embedded in managed club blob ~0x1700 (not pointer vector @ 0x8E8)",
                "uniformRelationshipFieldCandidates": feeder_relationship_field_candidates,
            },
        },
        "bteamAffiliatesResolved": bteam_clubs.iter().map(|entry| json!({
            "clubUid": entry.club_uid,
            "clubName": entry.club_name,
            "clubPointer": format!("0x{:X}", entry.club),
            "linkStructPointer": entry.link_struct_pointer.map(|pointer| format!("0x{pointer:X}")),
        })).collect::<Vec<_>>(),
        "bteamLinkStructDumps": bteam_struct_dumps,
        "feederInlineUidHits": feeder_hits,
        "productionPath": "discover_bteam_affiliate_clubs (link-vector → satellite-team → indirect-struct → backref → managed-blob) → discover_teams_for_affiliate_club → load_team_roster(reserves); satellite-team primary on Schalke",
        "satelliteTeamLock": {
            "rosterMin": BTEAM_SATELLITE_ROSTER_MIN,
            "rosterMax": BTEAM_SATELLITE_ROSTER_MAX,
            "teamNameRule": "contains managed club name + ' II'",
            "heapWindowBytes": CLUB_TEAM_HEAP_WINDOW_BYTES,
            "validated": "Schalke 04 II uid 3609393 roster 33",
        },
    })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn discover_bteam_affiliate_clubs(
    _reader: &mut super::memory::ProcessReader,
    _module: ModuleInfo,
    _profile: &EntityMapProfile,
    _managed_club: u64,
    _managed_club_uid: u32,
    _first_team: u64,
) -> Vec<AffiliateClubDiscovery> {
    Vec::new()
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn discover_teams_for_affiliate_club(
    _reader: &mut super::memory::ProcessReader,
    _module: ModuleInfo,
    _profile: &EntityMapProfile,
    _club: u64,
    _club_uid: u32,
    _heap_anchors: &[u64],
    _parent_club: Option<(u64, u32)>,
) -> Vec<AffiliateTeamDiscovery> {
    Vec::new()
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn discover_teams_for_club(
    _reader: &mut super::memory::ProcessReader,
    _module: ModuleInfo,
    _profile: &EntityMapProfile,
    _club: u64,
    _club_uid: u32,
    _heap_anchors: &[u64],
    _extra_team_seeds: &[u64],
) -> Vec<AffiliateTeamDiscovery> {
    Vec::new()
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn probe_lock_affiliate_link_layout(
    _reader: &mut super::memory::ProcessReader,
    _module: ModuleInfo,
    _profile: &EntityMapProfile,
    _managed_club: u64,
    _managed_club_uid: u32,
    _feeder_uids: &[u32],
) -> Value {
    json!({ "status": "windows_only" })
}

#[cfg(test)]
mod tests {
    use super::{
        bteam_satellite_team_matches, diff_affiliate_struct_hex, resolve_team_tab_label,
        squad_unit_from_team_type, team_type_display_label,
        AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET, BTEAM_LINK_POINTER_SLOTS,
        BTEAM_SATELLITE_ROSTER_MAX, BTEAM_SATELLITE_ROSTER_MIN,
        MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET, TEAM_NAME_OFFSET, TEAM_SHORT_NAME_OFFSET,
    };

    #[test]
    fn bteam_satellite_filter_locks_schalke_ii() {
        assert!(bteam_satellite_team_matches(
            "FC Schalke 04",
            "FC Schalke 04 II",
            33,
        ));
        assert!(!bteam_satellite_team_matches(
            "FC Schalke 04",
            "FC Bayern München II",
            36,
        ));
        assert!(!bteam_satellite_team_matches(
            "FC Schalke 04",
            "FC Schalke 04 U19",
            17,
        ));
        assert!(!bteam_satellite_team_matches(
            "FC Schalke 04",
            "FC Schalke 04 II",
            BTEAM_SATELLITE_ROSTER_MIN - 1,
        ));
        assert!(!bteam_satellite_team_matches(
            "FC Schalke 04",
            "FC Schalke 04 II",
            BTEAM_SATELLITE_ROSTER_MAX + 1,
        ));
    }

    #[test]
    fn bteam_satellite_roster_band_matches_entity_map() {
        assert_eq!(BTEAM_SATELLITE_ROSTER_MIN, 28);
        assert_eq!(BTEAM_SATELLITE_ROSTER_MAX, 38);
    }

    #[test]
    fn team_name_offsets_match_entity_map() {
        assert_eq!(TEAM_NAME_OFFSET, 0x18);
        assert_eq!(TEAM_SHORT_NAME_OFFSET, 0x20);
    }

    #[test]
    fn bteam_vector_offsets_are_aligned() {
        assert_eq!(MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET, 0x8E8);
        assert_eq!(AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET, 0x160);
        for slot in 0..BTEAM_LINK_POINTER_SLOTS {
            let offset = MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET + slot as u64 * 8;
            assert_eq!(offset % 8, 0);
        }
    }

    #[test]
    fn team_type_maps_fmscout_enum_to_squad_units() {
        assert_eq!(squad_unit_from_team_type(0), Some("firstTeam"));
        assert_eq!(squad_unit_from_team_type(11), Some("under19s"));
        assert_eq!(squad_unit_from_team_type(12), Some("under19s"));
        assert_eq!(squad_unit_from_team_type(1), Some("reserves"));
        assert_eq!(squad_unit_from_team_type(15), Some("reserves"));
        assert_eq!(squad_unit_from_team_type(22), Some("reserves"));
        assert_eq!(squad_unit_from_team_type(255), None);
    }

    #[test]
    fn team_type_display_labels_match_fmscout_enum() {
        assert_eq!(team_type_display_label(0), Some("First Team"));
        assert_eq!(team_type_display_label(10), Some("U21"));
        assert_eq!(team_type_display_label(11), Some("U19"));
        assert_eq!(team_type_display_label(12), Some("U18"));
        assert_eq!(team_type_display_label(15), Some("II"));
        assert_eq!(team_type_display_label(255), None);
    }

    #[test]
    fn resolve_team_tab_label_prefers_distinct_fm_string() {
        assert_eq!(
            resolve_team_tab_label("FC Schalke 04 U19", "FC Schalke 04", Some(11), 1),
            "FC Schalke 04 U19"
        );
        assert_eq!(
            resolve_team_tab_label("Liverpool", "Liverpool", Some(0), 676),
            "First Team"
        );
        assert_eq!(
            resolve_team_tab_label("Liverpool", "Liverpool", Some(10), 2),
            "U21"
        );
        assert_eq!(
            resolve_team_tab_label("liverpool", "Liverpool", Some(12), 3),
            "U18"
        );
        assert_eq!(
            resolve_team_tab_label("", "Leicester City", Some(11), 99),
            "U19"
        );
        assert_eq!(
            resolve_team_tab_label("", "", None, 42),
            "team-uid-42"
        );
    }

    #[test]
    fn club_teams_and_team_type_offsets_match_entity_map() {
        let profile = crate::fm26::offsets::embedded_entity_map_index()
            .profiles
            .first()
            .expect("profile");
        assert_eq!(profile.constants.club_teams_start_offset, 0x18);
        assert_eq!(profile.constants.club_teams_end_offset, 0x20);
        assert_eq!(profile.constants.team_type_offset, 0x28);
        // Layout adjacency: TeamType sits before Club@0x30 / Players@0x38 (FM22→FM26).
        assert_eq!(profile.constants.team_club_offset, 0x30);
        assert_eq!(profile.constants.team_players_start_offset, 0x38);
    }

    #[test]
    fn affiliate_struct_hex_diff_lists_flips() {
        let report = diff_affiliate_struct_hex("00ff11", "00aa11");
        assert_eq!(report["changeCount"], 1);
        assert_eq!(report["changes"][0]["offset"], 1);
        assert_eq!(report["changes"][0]["before"], 0xff);
        assert_eq!(report["changes"][0]["after"], 0xaa);
    }
}
