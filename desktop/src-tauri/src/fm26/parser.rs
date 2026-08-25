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

pub(crate) fn display_attribute(raw: u8) -> u8 {
    ((raw.saturating_add(4)) / 5).clamp(1, 20)
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
