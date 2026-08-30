use serde_json::{json, Value};

#[cfg(target_os = "windows")]
use super::{
    memory::{ModuleInfo, ProcessReader},
    offsets::EntityMapProfile,
    scanner::scan_private_memory_for_pointers,
    validator,
};

/// Scan an object blob for aligned u64 pointers equal to `target`.
pub(crate) fn pointer_hits_in_bytes(blob: &[u8], target: u64) -> Vec<usize> {
    let mut hits = Vec::new();
    for offset in (0..blob.len().saturating_sub(7)).step_by(8) {
        let value = u64::from_le_bytes(blob[offset..offset + 8].try_into().expect("aligned"));
        if value == target {
            hits.push(offset);
        }
    }
    hits
}

/// u32 values adjacent to a pointer hit — relationship-type RE candidates.
pub(crate) fn relationship_candidates(blob: &[u8], pointer_offset: usize) -> Vec<Value> {
    let mut out = Vec::new();
    for delta in [-16_i32, -12, -8, -4, 4, 8, 12, 16] {
        let offset = pointer_offset as i32 + delta;
        if offset < 0 {
            continue;
        }
        let offset = offset as usize;
        if offset + 4 > blob.len() {
            continue;
        }
        let value = u32::from_le_bytes(blob[offset..offset + 4].try_into().expect("u32"));
        out.push(json!({
            "fieldOffset": offset,
            "deltaFromPointer": delta,
            "u32": value,
            "hex": format!("0x{value:X}"),
        }));
    }
    out
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
        .read_pointer(club + profile.constants.club_name_offset)
        .and_then(|pointer| reader.read_length_prefixed_string(pointer))
        .unwrap_or_default();
    Some((uid, name))
}

#[cfg(target_os = "windows")]
fn club_pointers_in_blob(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    blob: &[u8],
    source_label: &str,
    skip_club: u64,
) -> Vec<Value> {
    let mut links = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for offset in (0..blob.len().saturating_sub(7)).step_by(8) {
        let pointer = u64::from_le_bytes(blob[offset..offset + 8].try_into().expect("aligned"));
        if pointer == 0 || pointer == skip_club || !seen.insert(pointer) {
            continue;
        }
        let Some((uid, name)) = read_club_identity(reader, module, profile, pointer) else {
            continue;
        };
        links.push(json!({
            "source": source_label,
            "pointerOffset": offset,
            "pointerOffsetHex": format!("0x{offset:X}"),
            "clubPointer": format!("0x{pointer:X}"),
            "clubUid": uid,
            "clubName": name,
            "relationshipCandidates": relationship_candidates(blob, offset),
        }));
    }
    links
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

#[cfg(target_os = "windows")]
fn teams_for_club(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    club: u64,
    club_uid: u32,
) -> Vec<Value> {
    let team_vtable = module.base + profile.constants.team_vtable_rva;
    let Ok(hits) = scan_private_memory_for_pointers(reader, &[team_vtable]) else {
        return Vec::new();
    };
    let mut teams = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for team in hits.into_values().flatten() {
        if !seen.insert(team) {
            continue;
        }
        if validator::validate_vtable(reader, team, team_vtable).is_err() {
            continue;
        }
        let linked = reader
            .read_pointer(team + profile.constants.team_club_offset)
            .filter(|value| *value != 0);
        let matches = linked.is_some_and(|linked_club| {
            linked_club == club
                || reader
                    .read_u32(linked_club + profile.constants.entity_uid_offset)
                    .is_some_and(|uid| uid == club_uid)
        });
        if !matches {
            continue;
        }
        let Some(roster_len) = team_roster_len(reader, profile, team) else {
            continue;
        };
        let team_uid = reader
            .read_u32(team + profile.constants.entity_uid_offset)
            .unwrap_or(0);
        let name = reader
            .read_pointer(team + profile.constants.club_name_offset)
            .and_then(|pointer| reader.read_length_prefixed_string(pointer))
            .unwrap_or_default();
        teams.push(json!({
            "teamPointer": format!("0x{team:X}"),
            "teamUid": team_uid,
            "name": name,
            "rosterLen": roster_len,
        }));
    }
    teams.sort_by(|left, right| {
        right
            .get("rosterLen")
            .and_then(Value::as_u64)
            .cmp(&left.get("rosterLen").and_then(Value::as_u64))
    });
    teams
}

#[cfg(target_os = "windows")]
const CLUB_OBJECT_PROBE_BYTES: usize = 8192;

#[cfg(target_os = "windows")]
pub(crate) fn probe_managed_club_affiliate_graph(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    managed_club_name: &str,
    same_club_teams: &[Value],
) -> Value {
    let managed_blob = reader
        .read_bytes(managed_club, CLUB_OBJECT_PROBE_BYTES)
        .unwrap_or_default();

    let forward_links =
        club_pointers_in_blob(reader, module, profile, &managed_blob, "managedClubForward", managed_club);

    let club_vtable = module.base + profile.constants.club_vtable_rva;
    let mut back_links = Vec::new();
    let mut affiliate_clubs = Vec::new();

    if let Ok(hits) = scan_private_memory_for_pointers(reader, &[club_vtable]) {
        let mut seen = std::collections::HashSet::new();
        for club in hits.into_values().flatten() {
            if club == managed_club || !seen.insert(club) {
                continue;
            }
            if validator::validate_vtable(reader, club, club_vtable).is_err() {
                continue;
            }
            let Some((uid, name)) = read_club_identity(reader, module, profile, club) else {
                continue;
            };
            let blob = reader
                .read_bytes(club, CLUB_OBJECT_PROBE_BYTES)
                .unwrap_or_default();
            let parent_hits = pointer_hits_in_bytes(&blob, managed_club);
            if parent_hits.is_empty() {
                continue;
            }
            let teams = teams_for_club(reader, module, profile, club, uid);
            let link_entries: Vec<Value> = parent_hits
                .iter()
                .map(|offset| {
                    json!({
                        "parentPointerOffset": offset,
                        "parentPointerOffsetHex": format!("0x{offset:X}"),
                        "relationshipCandidates": relationship_candidates(&blob, *offset),
                    })
                })
                .collect();
            back_links.push(json!({
                "clubPointer": format!("0x{club:X}"),
                "clubUid": uid,
                "clubName": name,
                "parentLinks": link_entries,
                "teams": teams,
            }));
            affiliate_clubs.push(json!({
                "clubUid": uid,
                "clubName": name,
                "linkDirection": "childToManagedClub",
                "teams": teams,
            }));
        }
    }

    let same_club_reserves: Vec<_> = same_club_teams
        .iter()
        .filter(|team| team.get("classifiedUnit").and_then(Value::as_str) == Some("reserves"))
        .cloned()
        .collect();

    json!({
        "status": "probe_complete",
        "managedClubUid": managed_club_uid,
        "managedClubPointer": format!("0x{managed_club:X}"),
        "managedClubName": managed_club_name,
        "probeBytesPerClubObject": CLUB_OBJECT_PROBE_BYTES,
        "compareWithFm": "Board → Affiliated Clubs: match clubName + relationship label to relationshipCandidates u32 values",
        "forwardLinksFromManagedClub": forward_links,
        "backLinksToManagedClub": back_links,
        "affiliateClubsWithParentPointer": affiliate_clubs,
        "sameClubReserveTeams": same_club_reserves,
        "notes": [
            "forwardLinks: other club objects referenced directly on the managed club blob",
            "backLinks: separate club objects whose blob contains a pointer to the managed club (B-team / feeder candidates)",
            "Discriminate B-team vs feeder using FM relationship type — not name heuristics alone",
            "sameClubReserveTeams: team.club == managed club (Spain U21 / England reserve team object under one club)",
        ],
    })
}

#[cfg(test)]
mod tests {
    use super::{pointer_hits_in_bytes, relationship_candidates};

    #[test]
    fn pointer_hits_finds_aligned_parent_reference() {
        let mut blob = vec![0_u8; 64];
        let parent: u64 = 0x0000_0001_2345_6789;
        blob[24..32].copy_from_slice(&parent.to_le_bytes());
        assert_eq!(pointer_hits_in_bytes(&blob, parent), vec![24]);
    }

    #[test]
    fn relationship_candidates_surround_pointer() {
        let mut blob = vec![0_u8; 64];
        blob[20..24].copy_from_slice(&7_u32.to_le_bytes());
        blob[28..32].copy_from_slice(&9_u32.to_le_bytes());
        let parent: u64 = 0xABCD;
        blob[32..40].copy_from_slice(&parent.to_le_bytes());
        let candidates = relationship_candidates(&blob, 32);
        assert!(candidates.iter().any(|entry| entry["u32"] == 7));
        assert!(candidates.iter().any(|entry| entry["u32"] == 9));
    }
}
