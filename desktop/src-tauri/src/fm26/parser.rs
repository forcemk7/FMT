use std::collections::HashMap;

use super::structs::{HIDDEN_ATTRIBUTE_INDEXES, PLAYER_ATTRIBUTE_NAMES, POSITION_NAMES};

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

/// Prefer foot label from **display** left/right strengths (1–20).
/// Equal → Either; otherwise the stronger side.
pub(crate) fn preferred_foot_label(left: u8, right: u8) -> &'static str {
    if left == right {
        "Either"
    } else if left > right {
        "Left"
    } else {
        "Right"
    }
}

/// FM outfield desk "Goalkeeper Rating x / 10" — GK position familiarity (0–20), capped at 10.
/// `POSITION_NAMES[0] == "GK"`. Returns `None` when the positions blob is missing/invalid.
pub(crate) fn goalkeeper_rating_from_positions(position_bytes: &[u8]) -> Option<u8> {
    let gk = *position_bytes.first()?;
    if gk > 20 {
        return None;
    }
    Some(gk.min(10))
}

/// Split the 15-byte familiarity map into primary (max score, ties kept) and
/// secondary (familiarity ≥ 15 but below that max). Empty primary when the blob is empty.
pub(crate) fn classify_player_positions(position_bytes: &[u8]) -> (Vec<String>, Vec<String>) {
    let Some(max) = position_bytes.iter().copied().max().filter(|value| *value > 0) else {
        return (Vec::new(), Vec::new());
    };
    let primary: Vec<String> = position_bytes
        .iter()
        .enumerate()
        .filter(|(_, rating)| **rating == max)
        .filter_map(|(index, _)| POSITION_NAMES.get(index).map(|name| (*name).to_string()))
        .collect();
    let secondary: Vec<String> = position_bytes
        .iter()
        .enumerate()
        .filter(|(_, rating)| **rating >= 15 && **rating < max)
        .filter_map(|(index, _)| POSITION_NAMES.get(index).map(|name| (*name).to_string()))
        .collect();
    (primary, secondary)
}

#[cfg(test)]
mod tests {
    use super::{
        classify_player_positions, display_attribute, goalkeeper_rating_from_positions,
        preferred_foot_label,
    };

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

    #[test]
    fn preferred_foot_label_uses_equality_not_threshold() {
        assert_eq!(preferred_foot_label(15, 15), "Either");
        assert_eq!(preferred_foot_label(18, 12), "Left");
        assert_eq!(preferred_foot_label(10, 14), "Right");
        assert_eq!(preferred_foot_label(20, 19), "Left");
    }

    #[test]
    fn goalkeeper_rating_is_gk_familiarity_capped_at_10() {
        assert_eq!(goalkeeper_rating_from_positions(&[3]), Some(3));
        assert_eq!(goalkeeper_rating_from_positions(&[4]), Some(4));
        assert_eq!(goalkeeper_rating_from_positions(&[1]), Some(1));
        assert_eq!(goalkeeper_rating_from_positions(&[15]), Some(10));
        assert_eq!(goalkeeper_rating_from_positions(&[20]), Some(10));
        assert_eq!(goalkeeper_rating_from_positions(&[]), None);
        assert_eq!(goalkeeper_rating_from_positions(&[21]), None);
    }

    #[test]
    fn classify_positions_keeps_max_primary_and_strong_secondaries() {
        // GK SW DL DC DR DM ML MC MR AML AMC AMR ST WBL WBR
        let mut bytes = [1_u8; 15];
        bytes[3] = 20; // DC
        bytes[5] = 18; // DM
        bytes[7] = 15; // MC
        bytes[12] = 12; // ST — below secondary threshold
        let (primary, secondary) = classify_player_positions(&bytes);
        assert_eq!(primary, vec!["DC"]);
        assert_eq!(secondary, vec!["DM", "MC"]);
    }

    #[test]
    fn classify_positions_ties_for_best_are_all_primary() {
        let mut bytes = [1_u8; 15];
        bytes[2] = 20; // DL
        bytes[4] = 20; // DR
        bytes[7] = 16; // MC
        let (primary, secondary) = classify_player_positions(&bytes);
        assert_eq!(primary, vec!["DL", "DR"]);
        assert_eq!(secondary, vec!["MC"]);
    }
}
