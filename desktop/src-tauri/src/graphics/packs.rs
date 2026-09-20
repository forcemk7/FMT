use std::{
    fs,
    path::{Path, PathBuf},
};

use image::{ImageFormat, RgbaImage};

use super::faces::default_graphics_root;

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GraphicsPackEntry {
    pub name: String,
    /// "Faces" or "Logos"
    pub kind: &'static str,
    pub path: String,
}

fn skip_pack(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    lower.contains("kit")
        || lower.contains("wallpaper")
        || lower.contains("background")
}

fn is_face_pack(path: &Path, name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    path.join("faces").is_dir()
        || lower.contains("face")
        || lower.contains("cutout")
        || lower.contains("newgen")
        || lower.contains("portrait")
}

fn is_logo_pack(path: &Path, name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    lower.contains("logo")
        || lower.contains("badge")
        || lower.contains("crest")
        || path.join("Men").is_dir()
        || path.join("Women").is_dir()
        || path.join("logos").is_dir()
        || path.join("clubs").is_dir()
        || path.join("badges").is_dir()
}

/// Top-level graphics folders only — no config XML reads.
pub fn discover_graphics_packs() -> Vec<GraphicsPackEntry> {
    let root = default_graphics_root();
    if !root.is_dir() {
        return Vec::new();
    }

    let mut packs = Vec::new();
    let Ok(entries) = fs::read_dir(&root) else {
        return packs;
    };
    for entry in entries.flatten() {
        if !entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        let name = entry.file_name().to_string_lossy().into_owned();
        if skip_pack(&name) {
            continue;
        }
        let path = entry.path();
        let faces = is_face_pack(&path, &name);
        let logos = is_logo_pack(&path, &name);
        let path_display = path.display().to_string();
        if faces {
            packs.push(GraphicsPackEntry {
                name: name.clone(),
                kind: "Faces",
                path: path_display.clone(),
            });
        }
        if logos {
            packs.push(GraphicsPackEntry {
                name,
                kind: "Logos",
                path: path_display,
            });
        }
    }
    packs.sort_by(|a, b| a.name.cmp(&b.name).then_with(|| a.kind.cmp(b.kind)));
    packs
}

pub(crate) fn resolve_cached_asset(cache_dir: &Path, id: &str) -> Option<PathBuf> {
    for extension in ["png", "jpg", "jpeg", "webp"] {
        let path = cache_dir.join(format!("{id}.{extension}"));
        if path.is_file() {
            return Some(path);
        }
    }
    None
}

/// Copy badge into cache, trimming empty padding so contain-fill looks even across assets.
pub(crate) fn copy_into_asset_cache(
    cache_dir: &Path,
    id: &str,
    source: &Path,
    max_bytes: u64,
) -> Option<PathBuf> {
    let meta = source.metadata().ok()?;
    if !meta.is_file() || meta.len() == 0 || meta.len() > max_bytes {
        return None;
    }
    let ext = source
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("png")
        .to_ascii_lowercase();
    if !matches!(ext.as_str(), "png" | "jpg" | "jpeg" | "webp") {
        return None;
    }
    fs::create_dir_all(cache_dir).ok()?;

    if let Some(dest) = write_trimmed_png(cache_dir, id, source) {
        return Some(dest);
    }

    let dest = cache_dir.join(format!("{id}.{ext}"));
    fs::copy(source, &dest).ok()?;
    Some(dest)
}

fn write_trimmed_png(cache_dir: &Path, id: &str, source: &Path) -> Option<PathBuf> {
    let img = image::open(source).ok()?.to_rgba8();
    let (x, y, w, h) = content_bounds(&img)?;
    let cropped = if w == img.width() && h == img.height() && x == 0 && y == 0 {
        img
    } else {
        image::imageops::crop_imm(&img, x, y, w, h).to_image()
    };
    let dest = cache_dir.join(format!("{id}.png"));
    cropped
        .save_with_format(&dest, ImageFormat::Png)
        .ok()
        .map(|_| dest)
}

/// Opaque (or near-opaque) bounding box. Returns None if the image is fully empty.
pub(crate) fn content_bounds(img: &RgbaImage) -> Option<(u32, u32, u32, u32)> {
    const ALPHA_MIN: u8 = 12;
    let (width, height) = img.dimensions();
    if width == 0 || height == 0 {
        return None;
    }

    let mut min_x = width;
    let mut min_y = height;
    let mut max_x = 0u32;
    let mut max_y = 0u32;
    let mut found = false;

    for (x, y, pixel) in img.enumerate_pixels() {
        if pixel[3] < ALPHA_MIN {
            continue;
        }
        found = true;
        min_x = min_x.min(x);
        min_y = min_y.min(y);
        max_x = max_x.max(x);
        max_y = max_y.max(y);
    }

    if !found {
        return None;
    }

    Some((min_x, min_y, max_x - min_x + 1, max_y - min_y + 1))
}

#[cfg(test)]
mod tests {
    use super::*;
    use image::{Rgba, RgbaImage};

    #[test]
    fn content_bounds_trims_transparent_padding() {
        let mut img = RgbaImage::from_pixel(40, 30, Rgba([0, 0, 0, 0]));
        for y in 8..18 {
            for x in 10..22 {
                img.put_pixel(x, y, Rgba([200, 20, 20, 255]));
            }
        }
        assert_eq!(content_bounds(&img), Some((10, 8, 12, 10)));
    }

    #[test]
    fn content_bounds_keeps_full_opaque_square() {
        let img = RgbaImage::from_pixel(20, 20, Rgba([10, 80, 200, 255]));
        assert_eq!(content_bounds(&img), Some((0, 0, 20, 20)));
    }
}
