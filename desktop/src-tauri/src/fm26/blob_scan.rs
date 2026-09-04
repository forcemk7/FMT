use serde_json::{json, Value};

const LINK_ENTRY_CONTEXT_BYTES: i32 = 64;

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
#[allow(dead_code)]
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

/// Wider u32 sweep around a UID hit — affiliate link structs are often >16B from the clubId.
pub(crate) fn relationship_candidates_wide(blob: &[u8], anchor_offset: usize) -> Vec<Value> {
    let mut out = Vec::new();
    let mut delta = -LINK_ENTRY_CONTEXT_BYTES;
    while delta <= LINK_ENTRY_CONTEXT_BYTES {
        let offset = anchor_offset as i32 + delta;
        if offset < 0 {
            delta += 4;
            continue;
        }
        let offset = offset as usize;
        if offset + 4 > blob.len() {
            delta += 4;
            continue;
        }
        let value = u32::from_le_bytes(blob[offset..offset + 4].try_into().expect("u32"));
        out.push(json!({
            "fieldOffset": offset,
            "deltaFromUid": delta,
            "u32": value,
            "hex": format!("0x{value:X}"),
        }));
        delta += 4;
    }
    out
}

pub(crate) fn find_u32_hits_in_blob(blob: &[u8], uid: u32) -> Vec<usize> {
    let mut hits = Vec::new();
    for offset in (0..blob.len().saturating_sub(3)).step_by(4) {
        let value = u32::from_le_bytes(blob[offset..offset + 4].try_into().expect("u32"));
        if value == uid {
            hits.push(offset);
        }
    }
    hits
}

/// Compact u8 window for FMLE A/B (toggle one editable affiliate field → which byte flips).
pub(crate) fn u8_grid_around(blob: &[u8], anchor_offset: usize, radius: usize) -> Vec<Value> {
    let start = anchor_offset.saturating_sub(radius);
    let end = (anchor_offset + radius + 1).min(blob.len());
    (start..end)
        .map(|offset| {
            json!({
                "offset": offset,
                "deltaFromAnchor": offset as i32 - anchor_offset as i32,
                "u8": blob[offset],
                "hex": format!("0x{:02X}", blob[offset]),
            })
        })
        .collect()
}

/// Diff two equal-length hex strings (no spaces). Returns changed byte offsets.
pub(crate) fn diff_hex_blobs(before_hex: &str, after_hex: &str) -> Vec<Value> {
    let before = decode_hex_bytes(before_hex);
    let after = decode_hex_bytes(after_hex);
    let len = before.len().min(after.len());
    let mut changes = Vec::new();
    for offset in 0..len {
        if before[offset] != after[offset] {
            changes.push(json!({
                "offset": offset,
                "offsetHex": format!("0x{offset:X}"),
                "before": before[offset],
                "after": after[offset],
                "beforeHex": format!("0x{:02X}", before[offset]),
                "afterHex": format!("0x{:02X}", after[offset]),
            }));
        }
    }
    if before.len() != after.len() {
        changes.push(json!({
            "offset": null,
            "note": "lengthMismatch",
            "beforeLen": before.len(),
            "afterLen": after.len(),
        }));
    }
    changes
}

fn decode_hex_bytes(hex: &str) -> Vec<u8> {
    let cleaned: String = hex
        .chars()
        .filter(|ch| ch.is_ascii_hexdigit())
        .collect();
    let mut out = Vec::with_capacity(cleaned.len() / 2);
    let bytes = cleaned.as_bytes();
    let mut index = 0;
    while index + 1 < bytes.len() {
        let hi = hex_nibble(bytes[index]);
        let lo = hex_nibble(bytes[index + 1]);
        if let (Some(hi), Some(lo)) = (hi, lo) {
            out.push((hi << 4) | lo);
        }
        index += 2;
    }
    out
}

fn hex_nibble(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::{diff_hex_blobs, u8_grid_around};

    #[test]
    fn u8_grid_includes_anchor_and_neighbors() {
        let blob = [0u8, 1, 2, 3, 4, 5, 6, 7];
        let grid = u8_grid_around(&blob, 4, 2);
        assert_eq!(grid.len(), 5);
        assert_eq!(grid[0]["offset"], 2);
        assert_eq!(grid[2]["u8"], 4);
        assert_eq!(grid[2]["deltaFromAnchor"], 0);
    }

    #[test]
    fn diff_hex_blobs_lists_changed_offsets() {
        let before = "001122334455";
        let after = "0011AA3344FF";
        let changes = diff_hex_blobs(before, after);
        assert_eq!(changes.len(), 2);
        assert_eq!(changes[0]["offset"], 2);
        assert_eq!(changes[0]["before"], 0x22);
        assert_eq!(changes[0]["after"], 0xAA);
        assert_eq!(changes[1]["offset"], 5);
        assert_eq!(changes[1]["after"], 0xFF);
    }
}
