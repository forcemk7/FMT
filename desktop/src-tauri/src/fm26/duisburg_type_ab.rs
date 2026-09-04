//! FM runtime A/B: dump managed↔Duisburg windows for affiliation type lock.
//! Run once on Feeder career, once on Likely Friendly, then diff JSON hex.

use serde_json::{json, Value};

#[cfg(target_os = "windows")]
use super::{
    memory::{ModuleInfo, ProcessReader},
    offsets::EntityMapProfile,
    scanner::scan_private_memory_for_u32_in_range,
};

#[cfg(target_os = "windows")]
const DUISBURG: u32 = 933;
#[cfg(target_os = "windows")]
const AARAU: u32 = 1848;
#[cfg(target_os = "windows")]
const AHLEN: u32 = 121197;
#[cfg(target_os = "windows")]
const VENLO: u32 = 1044;
#[cfg(target_os = "windows")]
const TEPECIK: u32 = 455003;
#[cfg(target_os = "windows")]
const TWENTE: u32 = 1009;
#[cfg(target_os = "windows")]
const II: u32 = 3609393;
/// SV Rödinghausen — likely the "Ried"-class Normal still on board in walk dumps.
#[cfg(target_os = "windows")]
const RODINGHAUSEN: u32 = 35_116_978;
#[cfg(target_os = "windows")]
const RIED: u32 = 159;
#[cfg(target_os = "windows")]
const WINDOW: usize = 192;
#[cfg(target_os = "windows")]
const SCAN_RADIUS: u64 = 64 * 1024 * 1024;
/// Club-local slots previously hot for Relationship / mid-size / II-only vectors.
#[cfg(target_os = "windows")]
const WATCH_SLOTS: &[u64] = &[0xE8, 0x158, 0x198, 0x8E8, 0x2B68];
#[cfg(target_os = "windows")]
const VECTOR_STRIDES: &[usize] = &[8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x40];
#[cfg(target_os = "windows")]
const CLUB_VECTOR_SCAN: usize = 0x4000;

#[cfg(target_os = "windows")]
fn find_u32(blob: &[u8], needle: u32) -> Vec<usize> {
    let bytes = needle.to_le_bytes();
    let mut out = Vec::new();
    let mut i = 0usize;
    while i + 4 <= blob.len() {
        if blob[i..i + 4] == bytes {
            out.push(i);
        }
        i += 1;
    }
    out
}

#[cfg(target_os = "windows")]
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect::<Vec<_>>().join("")
}

#[cfg(target_os = "windows")]
fn hash_hex(bytes: &[u8]) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let h = hex(bytes);
    let mut hasher = DefaultHasher::new();
    h.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

#[cfg(target_os = "windows")]
fn read_u64_le(blob: &[u8], off: usize) -> Option<u64> {
    if off + 8 > blob.len() {
        return None;
    }
    Some(u64::from_le_bytes(blob[off..off + 8].try_into().ok()?))
}

#[cfg(target_os = "windows")]
fn looks_heap_ptr(p: u64) -> bool {
    p >= 0x10_000 && p < 0x0000_7FFF_FFFF_FFFF
}

#[cfg(target_os = "windows")]
fn partner_board() -> &'static [(u32, &'static str)] {
    &[
        (DUISBURG, "Duisburg"),
        (AARAU, "Aarau"),
        (AHLEN, "Ahlen"),
        (VENLO, "Venlo"),
        (TEPECIK, "Tepecik"),
        (TWENTE, "Twente"),
        (II, "II"),
        (RODINGHAUSEN, "Rodinghausen"),
        (RIED, "Ried"),
    ]
}

#[cfg(target_os = "windows")]
fn count_partners_in(blob: &[u8]) -> (usize, Vec<Value>) {
    let mut hits = Vec::new();
    let mut total = 0usize;
    for &(uid, name) in partner_board() {
        let n = find_u32(blob, uid).len();
        if n > 0 {
            total += n;
            hits.push(json!({ "partner": name, "uid": uid, "count": n }));
        }
    }
    (total, hits)
}

/// Dump fixed club pointer slots + any club-local begin/end vectors that contain board UIDs.
#[cfg(target_os = "windows")]
fn watch_club_pointers(reader: &mut ProcessReader, managed_club: u64) -> Value {
    let Some(blob) = reader.read_bytes(managed_club, CLUB_VECTOR_SCAN) else {
        return json!({ "error": "managed club unreadable" });
    };

    let mut fixed = Vec::new();
    for &off in WATCH_SLOTS {
        let off_usize = off as usize;
        let Some(begin) = read_u64_le(&blob, off_usize) else {
            continue;
        };
        let end = read_u64_le(&blob, off_usize + 8).unwrap_or(0);
        let cap = read_u64_le(&blob, off_usize + 16).unwrap_or(0);
        let mut entry = json!({
            "offset": format!("0x{off:X}"),
            "qword0": format!("0x{begin:X}"),
            "qword1": format!("0x{end:X}"),
            "qword2": format!("0x{cap:X}"),
        });
        if looks_heap_ptr(begin) && end > begin && (end - begin) <= 0x100_000 {
            let span = (end - begin) as usize;
            if let Some(payload) = reader.read_bytes(begin, span) {
                let (partner_hits, partners) = count_partners_in(&payload);
                let mut followed = Vec::new();
                // Stride-8 pointer vector: hash each object head + partner hits.
                if span % 8 == 0 && span / 8 <= 64 {
                    for i in 0..(span / 8) {
                        let Some(ptr) = read_u64_le(&payload, i * 8) else {
                            continue;
                        };
                        if !looks_heap_ptr(ptr) {
                            continue;
                        }
                        if let Some(obj) = reader.read_bytes(ptr, 128) {
                            let (ph, _) = count_partners_in(&obj);
                            if ph > 0 || i < 8 {
                                followed.push(json!({
                                    "i": i,
                                    "ptr": format!("0x{ptr:X}"),
                                    "hash": hash_hex(&obj),
                                    "partnerHits": ph,
                                    "hexHead": hex(&obj[..obj.len().min(64)]),
                                }));
                            }
                        }
                    }
                }
                entry["asVector"] = json!({
                    "span": span,
                    "slotGuess": if span % 8 == 0 { Some(span / 8) } else { None },
                    "hash": hash_hex(&payload),
                    "partnerHits": partner_hits,
                    "partners": partners,
                    "followed": followed,
                });
            }
        } else if looks_heap_ptr(begin) {
            if let Some(obj) = reader.read_bytes(begin, 4096) {
                let (partner_hits, partners) = count_partners_in(&obj);
                entry["asSinglePtr"] = json!({
                    "hash4k": hash_hex(&obj),
                    "partnerHits": partner_hits,
                    "partners": partners,
                });
            }
        }
        fixed.push(entry);
    }

    let mut vectors = Vec::new();
    let mut offset = 0usize;
    while offset + 16 <= blob.len() {
        let begin = match read_u64_le(&blob, offset) {
            Some(v) => v,
            None => break,
        };
        let end = match read_u64_le(&blob, offset + 8) {
            Some(v) => v,
            None => break,
        };
        offset += 8;
        if !looks_heap_ptr(begin) || end <= begin {
            continue;
        }
        let span = (end - begin) as usize;
        if span == 0 || span > 0x40_000 {
            continue;
        }
        for &stride in VECTOR_STRIDES {
            if span % stride != 0 {
                continue;
            }
            let slots = span / stride;
            if !(1..=48).contains(&slots) {
                continue;
            }
            let Some(payload) = reader.read_bytes(begin, span) else {
                continue;
            };
            let (mut partner_hits, mut partners) = count_partners_in(&payload);
            let mut followed_partner = 0usize;
            if stride == 8 {
                for i in 0..slots {
                    let Some(ptr) = read_u64_le(&payload, i * 8) else {
                        continue;
                    };
                    if !looks_heap_ptr(ptr) {
                        continue;
                    }
                    if let Some(obj) = reader.read_bytes(ptr, 160) {
                        let (ph, phits) = count_partners_in(&obj);
                        if ph > 0 {
                            followed_partner += ph;
                            partner_hits += ph;
                            for p in phits {
                                partners.push(p);
                            }
                        }
                    }
                }
            }
            if partner_hits == 0 && followed_partner == 0 {
                // Keep mid-size empties only at known watch-ish counts (affiliates ~6–20).
                if !(6..=24).contains(&slots) {
                    continue;
                }
            }
            // Always follow stride-8 mid-size vectors — cancel A/B may shrink without
            // known partner UIDs in the pointer array itself.
            let mut followed = Vec::new();
            if stride == 8 && (6..=48).contains(&slots) {
                for i in 0..slots {
                    let Some(ptr) = read_u64_le(&payload, i * 8) else {
                        continue;
                    };
                    if !looks_heap_ptr(ptr) {
                        followed.push(json!({ "i": i, "ptr": format!("0x{ptr:X}"), "heap": false }));
                        continue;
                    }
                    let Some(obj) = reader.read_bytes(ptr, 512) else {
                        followed.push(json!({ "i": i, "ptr": format!("0x{ptr:X}"), "unreadable": true }));
                        continue;
                    };
                    let (ph, phits) = count_partners_in(&obj);
                    let nested_ptr = read_u64_le(&obj, 8).unwrap_or(0);
                    let mut nested = Value::Null;
                    if looks_heap_ptr(nested_ptr) {
                        if let Some(nobj) = reader.read_bytes(nested_ptr, 512) {
                            let (nph, nphits) = count_partners_in(&nobj);
                            let mut n_uids = Vec::new();
                            let mut o = 0usize;
                            while o + 4 <= nobj.len() && n_uids.len() < 16 {
                                let v = u32::from_le_bytes(nobj[o..o + 4].try_into().unwrap());
                                let is_known = partner_board().iter().any(|(u, _)| *u == v) || v == 920;
                                if is_known
                                    || ((100..30_000).contains(&v) && ![518, 520, 521, 522].contains(&v))
                                {
                                    n_uids.push(json!({ "off": o, "u32": v, "known": is_known }));
                                }
                                o += 4;
                            }
                            nested = json!({
                                "ptr": format!("0x{nested_ptr:X}"),
                                "hash": hash_hex(&nobj),
                                "partnerHits": nph,
                                "partners": nphits,
                                "uidGuess": n_uids,
                                "hexHead": hex(&nobj[..nobj.len().min(128)]),
                            });
                        }
                    }
                    let mut uid_guess = Vec::new();
                    let mut o = 0usize;
                    while o + 4 <= obj.len() && uid_guess.len() < 16 {
                        let v = u32::from_le_bytes(obj[o..o + 4].try_into().unwrap());
                        let is_known = partner_board().iter().any(|(u, _)| *u == v) || v == 920;
                        if is_known
                            || ((100..30_000).contains(&v) && ![518, 520, 521, 522].contains(&v))
                        {
                            uid_guess.push(json!({ "off": o, "u32": v, "known": is_known }));
                        }
                        o += 4;
                    }
                    followed.push(json!({
                        "i": i,
                        "ptr": format!("0x{ptr:X}"),
                        "hash": hash_hex(&obj),
                        "partnerHits": ph,
                        "partners": phits,
                        "uidGuess": uid_guess,
                        "hexHead": hex(&obj[..obj.len().min(128)]),
                        "nestedAt8": nested,
                    }));
                }
            }
            vectors.push(json!({
                "vectorBeginOffsetInClub": offset.saturating_sub(8),
                "offsetHex": format!("0x{:X}", offset.saturating_sub(8)),
                "begin": format!("0x{begin:X}"),
                "end": format!("0x{end:X}"),
                "stride": stride,
                "slots": slots,
                "hash": hash_hex(&payload),
                "partnerHits": partner_hits,
                "followedPartnerHits": followed_partner,
                "partners": partners,
                "followed": followed,
                "payloadHex": if slots <= 24 && stride == 8 { Some(hex(&payload)) } else { None },
            }));
            break; // one stride per begin/end pair
        }
    }
    vectors.sort_by(|a, b| {
        b["partnerHits"]
            .as_u64()
            .unwrap_or(0)
            .cmp(&a["partnerHits"].as_u64().unwrap_or(0))
            .then(
                a["vectorBeginOffsetInClub"]
                    .as_u64()
                    .unwrap_or(0)
                    .cmp(&b["vectorBeginOffsetInClub"].as_u64().unwrap_or(0)),
            )
    });
    vectors.truncate(40);

    let with_partners = vectors
        .iter()
        .filter(|v| v["partnerHits"].as_u64().unwrap_or(0) > 0)
        .count();
    let fixed_with = fixed
        .iter()
        .filter(|v| {
            v["asVector"]["partnerHits"].as_u64().unwrap_or(0) > 0
                || v["asSinglePtr"]["partnerHits"].as_u64().unwrap_or(0) > 0
        })
        .count();

    eprintln!(
        "duisburg-ab: clubPtrWatch fixed={} (withPartners={}) vectors={} (withPartners={})",
        fixed.len(),
        fixed_with,
        vectors.len(),
        with_partners
    );

    json!({
        "fixedSlots": fixed,
        "candidateVectors": vectors,
        "summary": {
            "fixedWithPartnerHits": fixed_with,
            "vectorsWithPartnerHits": with_partners,
            "vectorsKept": vectors.len(),
        },
    })
}

#[cfg(target_os = "windows")]
fn near_small_ints(blob: &[u8], rel: usize) -> Value {
    let mut u8s = Vec::new();
    let mut u32s = Vec::new();
    for delta in [-16isize, -12, -8, -4, 0, 4, 8, 12, 16, 20, 24, 28, 32] {
        let off = rel as isize + delta;
        if off < 0 || off as usize >= blob.len() {
            continue;
        }
        let o = off as usize;
        u8s.push(json!({ "rel": delta, "u8": blob[o] }));
        if o + 4 <= blob.len() {
            let v = u32::from_le_bytes(blob[o..o + 4].try_into().unwrap());
            if v <= 64 {
                u32s.push(json!({ "rel": delta, "u32": v }));
            }
        }
    }
    json!({ "u8": u8s, "u32Leq64": u32s })
}

#[cfg(target_os = "windows")]
fn dump_uid_windows(
    reader: &mut ProcessReader,
    centers: &[(u64, &str)],
    partner_uid: u32,
    partner_name: &str,
    managed_uid: u32,
    max_windows: usize,
) -> Vec<Value> {
    let mut out = Vec::new();
    for &(center, label) in centers {
        let lo = center.saturating_sub(SCAN_RADIUS);
        let hi = center.saturating_add(SCAN_RADIUS);
        let Ok(hits) = scan_private_memory_for_u32_in_range(reader, &[partner_uid], lo, hi, 120)
        else {
            continue;
        };
        let Some(addrs) = hits.get(&partner_uid) else {
            continue;
        };
        for &at in addrs.iter().take(40) {
            let start = at.saturating_sub(WINDOW as u64 / 2);
            let Some(blob) = reader.read_bytes(start, WINDOW) else {
                continue;
            };
            let has_managed = !find_u32(&blob, managed_uid).is_empty();
            let has_ii = !find_u32(&blob, II).is_empty();
            let partner_offs = find_u32(&blob, partner_uid);
            let Some(&rel) = partner_offs.first() else {
                continue;
            };
            let score = (if has_managed { 10 } else { 0 }) + (if has_ii { 3 } else { 0 });
            out.push(json!({
                "center": label,
                "partner": partner_name,
                "partnerAt": format!("0x{at:X}"),
                "score": score,
                "hasManagedUid": has_managed,
                "hasIiUid": has_ii,
                "near": near_small_ints(&blob, rel),
                "hex": hex(&blob),
            }));
        }
    }
    out.sort_by_key(|w| std::cmp::Reverse(w["score"].as_u64().unwrap_or(0)));
    out.truncate(max_windows);
    out
}

#[cfg(target_os = "windows")]
pub(crate) fn probe_duisburg_type_ab(
    reader: &mut ProcessReader,
    _module: ModuleInfo,
    _profile: &EntityMapProfile,
    managed_club: u64,
    managed_club_uid: u32,
    managed_club_name: &str,
    save_label: &str,
) -> Value {
    eprintln!(
        "duisburg-ab: label={save_label} managed={managed_club_name} uid={managed_club_uid} ptr=0x{managed_club:X}"
    );

    // Resolve II via club table if possible — soft fail.
    let centers = vec![
        (managed_club, "managedClub"),
        (managed_club.saturating_add(0x100000), "managed+1MB"),
        (managed_club.saturating_sub(0x100000), "managed-1MB"),
    ];

    let mut duisburg = dump_uid_windows(
        reader,
        &centers,
        DUISBURG,
        "MSV Duisburg",
        managed_club_uid,
        20,
    );
    let ii = dump_uid_windows(
        reader,
        &centers,
        II,
        "Schalke 04 II",
        managed_club_uid,
        12,
    );

    // Wide joint: any private hit of Duisburg, keep windows that also contain managed UID.
    eprintln!("duisburg-ab: wide joint scan for 933 near managed uid");
    let wide_lo = managed_club.saturating_sub(256 * 1024 * 1024);
    let wide_hi = managed_club.saturating_add(256 * 1024 * 1024);
    let mut joint = Vec::new();
    if let Ok(hits) =
        scan_private_memory_for_u32_in_range(reader, &[DUISBURG, managed_club_uid, II], wide_lo, wide_hi, 200)
    {
        let d_addrs = hits.get(&DUISBURG).cloned().unwrap_or_default();
        for &at in d_addrs.iter().take(200) {
            let start = at.saturating_sub(256);
            let Some(blob) = reader.read_bytes(start, 512) else {
                continue;
            };
            if find_u32(&blob, managed_club_uid).is_empty() {
                continue;
            }
            let has_ii = !find_u32(&blob, II).is_empty();
            let rel = find_u32(&blob, DUISBURG).into_iter().next().unwrap_or(256);
            joint.push(json!({
                "partnerAt": format!("0x{at:X}"),
                "hasIiUid": has_ii,
                "near": near_small_ints(&blob, rel),
                "hex": hex(&blob),
            }));
        }
    }
    eprintln!("duisburg-ab: jointManagedPlusDuisburg={}", joint.len());

    let managed_plus_duisburg = joint.len();

    eprintln!(
        "duisburg-ab: duisburgWindows={} jointWithManaged={} iiWindows={}",
        duisburg.len(),
        managed_plus_duisburg,
        ii.len()
    );

    // Merge joint into front of duisburg list for compareHint consumers.
    for w in joint.iter().rev() {
        duisburg.insert(
            0,
            json!({
                "center": "wideJoint",
                "partner": "MSV Duisburg",
                "partnerAt": w["partnerAt"],
                "score": 100,
                "hasManagedUid": true,
                "hasIiUid": w["hasIiUid"],
                "near": w["near"],
                "hex": w["hex"],
            }),
        );
    }
    duisburg.truncate(25);

    // Census: Duisburg + Aarau (in-game negotiate target) windows hashed for flip-diff.
    // Managed-club local blob — cancel/request A/B without partner+parent UID co-occur.
    let club_blob_len = 0x40000usize; // 256KB — affiliations not in first 16KB
    let club_blob = reader
        .read_bytes(managed_club, club_blob_len)
        .map(|bytes| {
            use std::collections::hash_map::DefaultHasher;
            use std::hash::{Hash, Hasher};
            let h = hex(&bytes);
            let mut hasher = DefaultHasher::new();
            h.hash(&mut hasher);
            json!({
                "len": bytes.len(),
                "hash": format!("{:016x}", hasher.finish()),
                "hex": h,
            })
        });
    eprintln!(
        "duisburg-ab: managedClubBlob hash={:?}",
        club_blob.as_ref().and_then(|v| v["hash"].as_str())
    );

    eprintln!("duisburg-ab: watching club pointer / vector slots");
    let club_ptr_watch = watch_club_pointers(reader, managed_club);

    // Revisit objects removed from club+0x118 on prior inbox A/B (may be freed).
    let mut revisit_removed = Vec::new();
    if save_label.contains("inbox") || save_label.contains("revisit") {
        const REMOVED: &[u64] = &[
            0x2092FAD35B0,
            0x205472EEC58,
            0x20547311638,
            0x205472D9520,
            0x2092FAD34D0,
        ];
        for &ptr in REMOVED {
            let Some(obj) = reader.read_bytes(ptr, 512) else {
                revisit_removed.push(json!({ "ptr": format!("0x{ptr:X}"), "unreadable": true }));
                continue;
            };
            let (ph, phits) = count_partners_in(&obj);
            let nested_ptr = read_u64_le(&obj, 8).unwrap_or(0);
            let mut nested = Value::Null;
            if looks_heap_ptr(nested_ptr) {
                if let Some(nobj) = reader.read_bytes(nested_ptr, 512) {
                    let (nph, nphits) = count_partners_in(&nobj);
                    nested = json!({
                        "ptr": format!("0x{nested_ptr:X}"),
                        "partnerHits": nph,
                        "partners": nphits,
                        "hexHead": hex(&nobj[..nobj.len().min(160)]),
                    });
                }
            }
            revisit_removed.push(json!({
                "ptr": format!("0x{ptr:X}"),
                "hash": hash_hex(&obj),
                "partnerHits": ph,
                "partners": phits,
                "hexHead": hex(&obj[..obj.len().min(160)]),
                "nestedAt8": nested,
            }));
        }
        eprintln!("duisburg-ab: revisitRemoved={}", revisit_removed.len());
    }

    eprintln!("duisburg-ab: census partners windows for flip-diff");
    let mut census = Vec::new();
    let mut census_hashes = std::collections::BTreeSet::new();
    let census_uids: &[(u32, &str)] = &[
        (DUISBURG, "Duisburg"),
        (AARAU, "Aarau"),
        (AHLEN, "Ahlen"),
        (VENLO, "Venlo"),
        (TEPECIK, "Tepecik"),
        (RODINGHAUSEN, "Rodinghausen"),
    ];
    let census_uid_values: Vec<u32> = census_uids.iter().map(|(u, _)| *u).collect();
    if let Ok(hits) =
        scan_private_memory_for_u32_in_range(reader, &census_uid_values, wide_lo, wide_hi, 400)
    {
        for &(uid, name) in census_uids {
            let d_addrs = hits.get(&uid).cloned().unwrap_or_default();
            for &at in d_addrs.iter().take(300) {
                let start = at.saturating_sub(64);
                let Some(blob) = reader.read_bytes(start, 128) else {
                    continue;
                };
                let h = hex(&blob);
                let hash = {
                    use std::collections::hash_map::DefaultHasher;
                    use std::hash::{Hash, Hasher};
                    let mut hasher = DefaultHasher::new();
                    h.hash(&mut hasher);
                    format!("{:016x}", hasher.finish())
                };
                census_hashes.insert(hash.clone());
                let has_managed = !find_u32(&blob, managed_club_uid).is_empty();
                let has_ii = !find_u32(&blob, II).is_empty();
                let has_other_partner = census_uids
                    .iter()
                    .any(|(other, _)| *other != uid && !find_u32(&blob, *other).is_empty());
                let rel = find_u32(&blob, uid).into_iter().next().unwrap_or(64);
                if census.len() < 120 || has_managed {
                    census.push(json!({
                        "partner": name,
                        "uid": uid,
                        "at": format!("0x{at:X}"),
                        "hash": hash,
                        "hasManagedUid": has_managed,
                        "hasIiUid": has_ii,
                        "hasOtherPartnerUid": has_other_partner,
                        "near": near_small_ints(&blob, rel),
                        "hex": h,
                    }));
                }
            }
        }
    }
    let count_partner = |name: &str| {
        census
            .iter()
            .filter(|w| {
                w["partner"].as_str() == Some(name) && w["hasManagedUid"].as_bool().unwrap_or(false)
            })
            .count()
    };
    let aarau_with_managed = count_partner("Aarau");
    let ahlen_with_managed = count_partner("Ahlen");
    let venlo_with_managed = count_partner("Venlo");
    let tepecik_with_managed = count_partner("Tepecik");
    let rodinghausen_with_managed = count_partner("Rodinghausen");
    eprintln!(
        "duisburg-ab: censusStored={} uniqueHashes={} aarauM={} ahlenM={} venloM={} tepecikM={} rodingM={}",
        census.len(),
        census_hashes.len(),
        aarau_with_managed,
        ahlen_with_managed,
        venlo_with_managed,
        tepecik_with_managed,
        rodinghausen_with_managed
    );

    json!({
        "probe": "duisburg-type-ab",
        "saveLabel": save_label,
        "managedClub": format!("0x{managed_club:X}"),
        "managedUid": managed_club_uid,
        "managedName": managed_club_name,
        "duisburgWindows": duisburg,
        "iiWindows": ii,
        "jointWindows": joint,
        "managedPlusDuisburgCount": managed_plus_duisburg,
        "census": census,
        "censusUniqueHashes": census_hashes.len(),
        "censusHashList": census_hashes.into_iter().collect::<Vec<_>>(),
        "aarauWithManagedCount": aarau_with_managed,
        "ahlenWithManagedCount": ahlen_with_managed,
        "venloWithManagedCount": venlo_with_managed,
        "tepecikWithManagedCount": tepecik_with_managed,
        "rodinghausenWithManagedCount": rodinghausen_with_managed,
        "managedClubBlob": club_blob,
        "clubPtrWatch": club_ptr_watch,
        "revisitRemoved": revisit_removed,
        "compareHint": "Cancel A/B (same session, no reload): clubPtrWatch fixedSlots/candidateVectors hash+partnerHits; cancel-all amplifies vector slot/hash flip. Club blob first 256KB was blind until inbox processing; club+0x118 end shrinks by N cancels.",
    })
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn probe_duisburg_type_ab(
    _reader: &mut (),
    _module: (),
    _profile: &(),
    _managed_club: u64,
    _managed_club_uid: u32,
    _managed_club_name: &str,
    _save_label: &str,
) -> Value {
    json!({ "error": "windows only" })
}
