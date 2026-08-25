use std::collections::HashMap;

use super::structs::{HIDDEN_ATTRIBUTE_INDEXES, PLAYER_ATTRIBUTE_NAMES};

pub(crate) const PERSONALITY_ATTRIBUTE_NAMES: [&str; 8] = [
    "Adaptability",
    "Ambition",
    "Loyalty",
    "Pressure",
    "Professionalism",
    "Sportsmanship",
    "Temperament",
    "Controversy",
];

/// Convert FM internal attribute storage (0–100, typically ×5) to the 1–20 UI value.
/// Matches in-game / FMLE / FMSuperScout: `floor(raw/5 + 0.5)` ≡ integer `(raw + 2) / 5`.
/// The old `(raw + 4) / 5` rounded up too aggressively and showed +1 vs FM on some values.
pub(crate) fn display_attribute(raw: u8) -> u8 {
    (((u16::from(raw) + 2) / 5) as u8).clamp(1, 20)
}

pub(crate) fn visible_attribute_map(raw: &[u8]) -> HashMap<String, u8> {
    PLAYER_ATTRIBUTE_NAMES
        .iter()
        .enumerate()
        .filter(|(index, _)| {
            !HIDDEN_ATTRIBUTE_INDEXES.contains(index) && !matches!(*index, 24 | 25)
        })
        .filter_map(|(index, name)| {
            raw.get(index)
                .copied()
                .map(|value| ((*name).to_string(), display_attribute(value)))
        })
        .collect()
}

/// FM hidden attribute row (Consistency, Dirtiness, …) — same 54-byte blob, previously gated.
pub(crate) fn hidden_attribute_map(raw: &[u8]) -> HashMap<String, u8> {
    HIDDEN_ATTRIBUTE_INDEXES
        .iter()
        .filter_map(|index| {
            let name = PLAYER_ATTRIBUTE_NAMES.get(*index)?;
            let value = raw.get(*index).copied()?;
            Some(((*name).to_string(), display_attribute(value)))
        })
        .collect()
}

/// Personality pack on the person object (1–20 bytes). Invalid bytes → omitted.
pub(crate) fn personality_attribute_map(raw: &[u8]) -> HashMap<String, u8> {
    PERSONALITY_ATTRIBUTE_NAMES
        .iter()
        .enumerate()
        .filter_map(|(index, name)| {
            let value = *raw.get(index)?;
            (1..=20)
                .contains(&value)
                .then(|| ((*name).to_string(), value))
        })
        .collect()
}

pub(crate) fn preferred_foot_label(left: u8, right: u8) -> &'static str {
    let difference = i16::from(left) - i16::from(right);
    if difference >= 20 {
        "Left"
    } else if difference <= -20 {
        "Right"
    } else {
        "Both"
    }
}

#[cfg(test)]
mod tests {
    use super::display_attribute;

    #[test]
    fn display_attribute_matches_fm_and_fss_rounding() {
        // Floor(raw/5 + 0.5). Old (raw+4)/5 returned 17 for raw=81.
        assert_eq!(display_attribute(81), 16);
        assert_eq!(display_attribute(82), 16);
        assert_eq!(display_attribute(83), 17);
        assert_eq!(display_attribute(50), 10);
        assert_eq!(display_attribute(0), 1);
        assert_eq!(display_attribute(100), 20);
    }
}
