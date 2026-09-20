#[cfg(target_os = "windows")]
use super::memory::{ModuleInfo, ProcessReader};
#[cfg(target_os = "windows")]
use std::collections::{HashMap, HashSet};

#[derive(Debug)]
pub(crate) struct PatternParseError;

#[derive(Debug)]
pub(crate) struct ScanError {
    message: String,
}

impl ScanError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl std::fmt::Display for ScanError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.message)
    }
}

pub(crate) fn parse_pattern(pattern: &str) -> Result<Vec<Option<u8>>, PatternParseError> {
    pattern
        .split_whitespace()
        .map(|token| {
            if token == "??" || token == "?" {
                Ok(None)
            } else {
                u8::from_str_radix(token, 16)
                    .map(Some)
                    .map_err(|_| PatternParseError)
            }
        })
        .collect()
}

#[cfg(target_os = "windows")]
pub(crate) fn scan_module(
    reader: &mut ProcessReader,
    module: ModuleInfo,
    pattern: &[Option<u8>],
) -> Result<Vec<u64>, ScanError> {
    if pattern.is_empty() || module.size < pattern.len() {
        return Err(ScanError::new(
            "The manager signature is empty or larger than the game module.",
        ));
    }
    const CHUNK_SIZE: usize = 4 * 1024 * 1024;
    let overlap = pattern.len().saturating_sub(1);
    let mut hits = Vec::new();
    let mut offset = 0_usize;
    while offset < module.size {
        let read_start = offset.saturating_sub(if offset == 0 { 0 } else { overlap });
        let read_size = CHUNK_SIZE
            .saturating_add(if offset == 0 { 0 } else { overlap })
            .min(module.size - read_start);
        let bytes = reader
            .read_bytes(module.base + read_start as u64, read_size)
            .ok_or_else(|| {
                ScanError::new("The FM26 game module could not be scanned with read-only access.")
            })?;
        for position in 0..=bytes.len().saturating_sub(pattern.len()) {
            let absolute_offset = read_start + position;
            if offset != 0 && absolute_offset < offset {
                continue;
            }
            if pattern.iter().enumerate().all(|(index, expected)| {
                expected.is_none_or(|value| bytes[position + index] == value)
            }) {
                hits.push(module.base + absolute_offset as u64);
            }
        }
        offset = offset.saturating_add(CHUNK_SIZE);
    }
    Ok(hits)
}

#[cfg(target_os = "windows")]
pub(crate) fn scan_private_memory_for_pointers(
    reader: &mut ProcessReader,
    pointers: &[u64],
) -> Result<HashMap<u64, Vec<u64>>, ScanError> {
    scan_private_memory_for_pointers_within(reader, pointers, 8 * 1024 * 1024 * 1024)
}

/// Lighter heap scan for RE probes (`fmt-probe`) — avoids multi-minute 8GB walks.
#[cfg(target_os = "windows")]
pub(crate) fn scan_private_memory_for_pointers_within(
    reader: &mut ProcessReader,
    pointers: &[u64],
    max_scan_bytes: usize,
) -> Result<HashMap<u64, Vec<u64>>, ScanError> {
    const CHUNK_SIZE: usize = 8 * 1024 * 1024;

    let regions = reader.readable_private_regions(max_scan_bytes);
    if regions.is_empty() {
        return Err(ScanError::new(
            "No readable FM26 private-memory regions were available for player indexing.",
        ));
    }

    let needles: HashSet<u64> = pointers.iter().copied().collect();
    let mut hits: HashMap<u64, Vec<u64>> = pointers
        .iter()
        .copied()
        .map(|pointer| (pointer, Vec::new()))
        .collect();
    for region in regions {
        let mut offset = 0_usize;
        while offset < region.size {
            let size = CHUNK_SIZE.min(region.size - offset);
            let Some(bytes) = reader.read_bytes(region.base + offset as u64, size) else {
                offset = offset.saturating_add(size);
                continue;
            };
            let base = region.base + offset as u64;
            let first_aligned = ((8 - (base as usize & 7)) & 7).min(bytes.len());
            let mut position = first_aligned;
            while position + 8 <= bytes.len() {
                let value = u64::from_le_bytes(
                    bytes[position..position + 8]
                        .try_into()
                        .expect("eight-byte aligned memory candidate"),
                );
                if needles.contains(&value) {
                    hits.entry(value).or_default().push(base + position as u64);
                }
                position += 8;
            }
            offset = offset.saturating_add(size);
        }
    }
    Ok(hits)
}

/// Pointer backref scan bounded by VA range (for club-name strings far from low heap).
#[cfg(target_os = "windows")]
pub(crate) fn scan_private_memory_for_pointers_in_range(
    reader: &mut ProcessReader,
    pointers: &[u64],
    min_base: u64,
    max_base: u64,
) -> Result<HashMap<u64, Vec<u64>>, ScanError> {
    const CHUNK_SIZE: usize = 8 * 1024 * 1024;
    let span = max_base.saturating_sub(min_base) as usize;
    let max_range_bytes = span.saturating_add(64 * 1024 * 1024).min(4 * 1024 * 1024 * 1024);

    let regions =
        reader.readable_private_regions_filtered(max_range_bytes, Some(min_base), Some(max_base));
    if regions.is_empty() {
        return Err(ScanError::new(
            "No readable FM26 private-memory regions matched the pointer scan window.",
        ));
    }

    let needles: HashSet<u64> = pointers.iter().copied().collect();
    let mut hits: HashMap<u64, Vec<u64>> = pointers
        .iter()
        .copied()
        .map(|pointer| (pointer, Vec::new()))
        .collect();
    for region in regions {
        let region_end = region.base.saturating_add(region.size as u64);
        let chunk_lo = min_base.max(region.base);
        let chunk_hi = max_base.min(region_end);
        if chunk_lo >= chunk_hi {
            continue;
        }
        let mut offset = chunk_lo.saturating_sub(region.base) as usize;
        let limit = (chunk_hi - region.base) as usize;
        while offset < limit {
            let size = CHUNK_SIZE.min(limit - offset);
            let read_base = region.base + offset as u64;
            let Some(bytes) = reader.read_bytes(read_base, size) else {
                offset = offset.saturating_add(size);
                continue;
            };
            let base = read_base;
            let first_aligned = ((8 - (base as usize & 7)) & 7).min(bytes.len());
            let mut position = first_aligned;
            while position + 8 <= bytes.len() {
                let value = u64::from_le_bytes(
                    bytes[position..position + 8]
                        .try_into()
                        .expect("eight-byte aligned memory candidate"),
                );
                if needles.contains(&value) {
                    hits.entry(value).or_default().push(base + position as u64);
                }
                position += 8;
            }
            offset = offset.saturating_add(size);
        }
    }
    Ok(hits)
}

/// Find length-prefixed UTF-8 strings whose payload contains one of `needles`.
#[cfg(target_os = "windows")]
pub(crate) fn scan_private_memory_for_lp32_needles(
    reader: &mut ProcessReader,
    needles: &[&str],
    max_scan_bytes: usize,
    max_hits_per_needle: usize,
) -> Result<Vec<(String, u64, String)>, ScanError> {
    const CHUNK_SIZE: usize = 8 * 1024 * 1024;

    let regions = reader.readable_private_regions(max_scan_bytes);
    if regions.is_empty() {
        return Err(ScanError::new(
            "No readable FM26 private-memory regions were available for string indexing.",
        ));
    }

    let needle_bytes: Vec<(&str, &[u8])> = needles
        .iter()
        .map(|needle| (*needle, needle.as_bytes()))
        .collect();
    let mut hits: Vec<(String, u64, String)> = Vec::new();
    let mut counts: HashMap<String, usize> = HashMap::new();
    let mut seen_headers = HashSet::new();

    for region in regions {
        let mut offset = 0_usize;
        while offset < region.size {
            let size = CHUNK_SIZE.min(region.size - offset);
            let Some(bytes) = reader.read_bytes(region.base + offset as u64, size) else {
                offset = offset.saturating_add(size);
                continue;
            };
            let base = region.base + offset as u64;
            for (needle, bytes_needle) in &needle_bytes {
                if counts.get(*needle).copied().unwrap_or(0) >= max_hits_per_needle {
                    continue;
                }
                let first = bytes_needle[0];
                let mut position = 4usize;
                while position + bytes_needle.len() <= bytes.len() {
                    if bytes[position] != first {
                        position += 1;
                        continue;
                    }
                    if &bytes[position..position + bytes_needle.len()] != *bytes_needle {
                        position += 1;
                        continue;
                    }
                    let header = base + position as u64 - 4;
                    if seen_headers.contains(&header) {
                        position += 1;
                        continue;
                    }
                    let Some(full) = reader.read_length_prefixed_string(header) else {
                        position += 1;
                        continue;
                    };
                    if !full.contains(needle) {
                        position += 1;
                        continue;
                    }
                    seen_headers.insert(header);
                    counts
                        .entry(needle.to_string())
                        .and_modify(|count| *count += 1)
                        .or_insert(1);
                    hits.push((needle.to_string(), header, full));
                    position += 1;
                }
            }
            offset = offset.saturating_add(size);
        }
    }
    Ok(hits)
}

/// Scan a VA window for aligned u32 values (club UID needles).
#[cfg(target_os = "windows")]
pub(crate) fn scan_private_memory_for_u32_in_range(
    reader: &mut ProcessReader,
    values: &[u32],
    min_base: u64,
    max_base: u64,
    max_hits_per_value: usize,
) -> Result<HashMap<u32, Vec<u64>>, ScanError> {
    const CHUNK_SIZE: usize = 8 * 1024 * 1024;
    let span = max_base.saturating_sub(min_base) as usize;
    let max_range_bytes = span.saturating_add(64 * 1024 * 1024).min(4 * 1024 * 1024 * 1024);
    let regions =
        reader.readable_private_regions_filtered(max_range_bytes, Some(min_base), Some(max_base));
    if regions.is_empty() {
        return Err(ScanError::new(
            "No readable FM26 private-memory regions matched the u32 scan window.",
        ));
    }
    let needles: HashSet<u32> = values.iter().copied().collect();
    let mut hits: HashMap<u32, Vec<u64>> = values
        .iter()
        .copied()
        .map(|value| (value, Vec::new()))
        .collect();
    let mut counts: HashMap<u32, usize> = HashMap::new();
    for region in regions {
        let mut offset = 0_usize;
        while offset < region.size {
            let size = CHUNK_SIZE.min(region.size - offset);
            let Some(bytes) = reader.read_bytes(region.base + offset as u64, size) else {
                offset = offset.saturating_add(size);
                continue;
            };
            let base = region.base + offset as u64;
            let first_aligned = ((4 - (base as usize & 3)) & 3).min(bytes.len());
            let mut position = first_aligned;
            while position + 4 <= bytes.len() {
                let value = u32::from_le_bytes(
                    bytes[position..position + 4]
                        .try_into()
                        .expect("four-byte aligned memory candidate"),
                );
                if needles.contains(&value) && counts.get(&value).copied().unwrap_or(0) < max_hits_per_value
                {
                    hits.entry(value).or_default().push(base + position as u64);
                    *counts.entry(value).or_insert(0) += 1;
                }
                position += 4;
            }
            offset = offset.saturating_add(size);
        }
    }
    Ok(hits)
}

const LP32_MAX_BYTES: usize = 192;

pub(crate) fn lp32_payload_matches_needle(
    header_and_payload: &[u8],
    payload_offset: usize,
    needle: &str,
) -> Option<String> {
    if payload_offset < 4 || payload_offset + needle.len() > header_and_payload.len() {
        return None;
    }
    let length = u32::from_le_bytes(
        header_and_payload[payload_offset - 4..payload_offset]
            .try_into()
            .ok()?,
    ) as usize;
    if length == 0 || length > LP32_MAX_BYTES {
        return None;
    }
    if payload_offset + length > header_and_payload.len() {
        return None;
    }
    let payload = &header_and_payload[payload_offset..payload_offset + length];
    let full = std::str::from_utf8(payload).ok()?;
    if full.contains(needle) && !full.chars().any(char::is_control) {
        Some(full.to_string())
    } else {
        None
    }
}
