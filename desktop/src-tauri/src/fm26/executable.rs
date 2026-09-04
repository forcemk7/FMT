fn version_part_count(value: &str) -> usize {
    normalize_version_string(value)
        .split('.')
        .filter(|part| !part.is_empty())
        .count()
}

/// PowerShell/.NET accept comma or dot separated version strings.
fn normalize_version_string(value: &str) -> String {
    if value.contains(',') {
        value
            .split(',')
            .map(str::trim)
            .filter(|part| !part.is_empty())
            .collect::<Vec<_>>()
            .join(".")
    } else {
        value.trim().to_string()
    }
}

pub(crate) fn versions_match_entity_map_expectation(
    file_version: &str,
    product_version: &str,
) -> bool {
    version_part_count(file_version) >= 4 && product_version.to_ascii_lowercase().contains("fm26")
}

/// Read FileVersion and ProductVersion from a PE on disk — no shell subprocess.
/// Matches PowerShell `(Get-Item fm.exe).VersionInfo` (StringFileInfo), not VS_FIXEDFILEINFO quad.
#[cfg(target_os = "windows")]
pub(crate) fn read_string_file_info_versions(path: &str) -> Option<(String, String)> {
    use std::ffi::c_void;
    use std::os::windows::ffi::OsStrExt;
    use std::path::Path;

    #[link(name = "version")]
    unsafe extern "system" {
        fn GetFileVersionInfoSizeW(
            lptstr_filename: *const u16,
            lpdw_handle: *mut u32,
        ) -> u32;
        fn GetFileVersionInfoW(
            lptstr_filename: *const u16,
            dw_handle: u32,
            dw_len: u32,
            lp_data: *mut c_void,
        ) -> i32;
        fn VerQueryValueW(
            p_block: *const c_void,
            lp_sub_block: *const u16,
            lplp_buffer: *mut *mut c_void,
            pu_len: *mut u32,
        ) -> i32;
    }

    #[derive(Clone)]
    struct VersionPair {
        file_version: String,
        product_version: String,
        parts: usize,
    }

    fn wide_null(path: &str) -> Vec<u16> {
        Path::new(path)
            .as_os_str()
            .encode_wide()
            .chain(std::iter::once(0))
            .collect()
    }

    fn wide_literal(value: &str) -> Vec<u16> {
        value.encode_utf16().chain(std::iter::once(0)).collect()
    }

    unsafe fn query_string(
        data: &[u8],
        sub_block: &[u16],
    ) -> Option<String> {
        let mut value_ptr: *mut c_void = std::ptr::null_mut();
        let mut value_len = 0u32;
        if VerQueryValueW(
            data.as_ptr() as *const c_void,
            sub_block.as_ptr(),
            &mut value_ptr,
            &mut value_len,
        ) == 0
            || value_ptr.is_null()
            || value_len < 2
        {
            return None;
        }
        let units = value_len as usize / 2;
        let slice = std::slice::from_raw_parts(value_ptr as *const u16, units);
        let text = String::from_utf16_lossy(slice)
            .trim_end_matches('\0')
            .trim()
            .to_string();
        (!text.is_empty()).then_some(text)
    }

    unsafe fn translation_pairs(data: &[u8]) -> Vec<(u16, u16)> {
        let translation_key = wide_literal("\\VarFileInfo\\Translation");
        let mut trans_ptr: *mut c_void = std::ptr::null_mut();
        let mut trans_len = 0u32;
        if VerQueryValueW(
            data.as_ptr() as *const c_void,
            translation_key.as_ptr(),
            &mut trans_ptr,
            &mut trans_len,
        ) == 0
            || trans_ptr.is_null()
            || trans_len < 4
        {
            return Vec::new();
        }
        let entries = trans_len as usize / 4;
        let trans = trans_ptr as *const u16;
        (0..entries)
            .map(|index| (*trans.add(index * 2), *trans.add(index * 2 + 1)))
            .collect()
    }

    unsafe fn collect_version_pairs(data: &[u8]) -> Vec<VersionPair> {
        let mut pairs = Vec::new();
        for (lang, codepage) in translation_pairs(data) {
            let prefix = format!("\\StringFileInfo\\{lang:04x}{codepage:04x}\\");
            let Some(raw_file_version) =
                query_string(data, &wide_literal(&format!("{prefix}FileVersion")))
            else {
                continue;
            };
            let file_version = normalize_version_string(&raw_file_version);
            let product_version = query_string(data, &wide_literal(&format!("{prefix}ProductVersion")))
                .map(|value| normalize_version_string(&value))
                .unwrap_or_else(|| file_version.clone());
            let parts = version_part_count(&file_version);
            pairs.push(VersionPair {
                file_version,
                product_version,
                parts,
            });
        }
        pairs
    }

    fn pick_best_pair(mut pairs: Vec<VersionPair>) -> Option<VersionPair> {
        pairs.sort_by(|left, right| {
            right
                .parts
                .cmp(&left.parts)
                .then_with(|| right.file_version.len().cmp(&left.file_version.len()))
        });
        pairs.into_iter().next()
    }

    let path_wide = wide_null(path);
    unsafe {
        let mut handle = 0u32;
        let size = GetFileVersionInfoSizeW(path_wide.as_ptr(), &mut handle);
        if size == 0 {
            return None;
        }
        let mut data = vec![0_u8; size as usize];
        if GetFileVersionInfoW(
            path_wide.as_ptr(),
            0,
            size,
            data.as_mut_ptr() as *mut c_void,
        ) == 0
        {
            return None;
        }

        let best = pick_best_pair(collect_version_pairs(&data))?;
        Some((best.file_version, best.product_version))
    }
}

/// Hidden PowerShell fallback — same strings as 0.1.22, no visible console (`CREATE_NO_WINDOW`).
#[cfg(target_os = "windows")]
pub(crate) fn read_windows_file_versions_powershell_hidden(path: &str) -> Option<(String, String)> {
    use std::os::windows::process::CommandExt;

    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    let escaped_path = path.replace('\'', "''");
    let script = format!(
        "$v=(Get-Item -LiteralPath '{escaped_path}').VersionInfo; [Console]::Write($v.FileVersion+'|'+$v.ProductVersion)"
    );
    let output = std::process::Command::new("powershell")
        .args(["-NoProfile", "-NonInteractive", "-Command", &script])
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let value = String::from_utf8_lossy(&output.stdout);
    let mut parts = value.splitn(2, '|');
    let file_version = parts
        .next()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)?;
    let product_version = parts
        .next()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)?;
    Some((file_version, product_version))
}

#[cfg(target_os = "windows")]
pub(crate) fn read_windows_file_versions(path: &str) -> Option<(String, String)> {
    // 0.1.22 used PowerShell VersionInfo; native VerQueryValueW returns truncated FM26 strings.
    read_windows_file_versions_powershell_hidden(path)
        .or_else(|| read_string_file_info_versions(path))
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn read_windows_file_versions(_path: &str) -> Option<(String, String)> {
    None
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn read_windows_file_versions_powershell_hidden(_path: &str) -> Option<(String, String)> {
    None
}

#[cfg(test)]
mod tests {
    use super::read_windows_file_versions;

    fn normalize_version_string(value: &str) -> String {
        if value.contains(',') {
            value
                .split(',')
                .map(str::trim)
                .filter(|part| !part.is_empty())
                .collect::<Vec<_>>()
                .join(".")
        } else {
            value.trim().to_string()
        }
    }

    #[test]
    fn normalize_comma_separated_file_version() {
        assert_eq!(
            normalize_version_string("6000, 0, 52, 8888375"),
            "6000.0.52.8888375"
        );
    }

    fn fm_exe_candidates() -> Vec<String> {
        let mut paths = Vec::new();
        if let Ok(path) = std::env::var("FM26_EXE") {
            paths.push(path);
        }
        for key in ["ProgramFiles(x86)", "ProgramFiles"] {
            if let Ok(root) = std::env::var(key) {
                paths.push(format!(
                    "{root}\\Steam\\steamapps\\common\\Football Manager 2026\\fm.exe"
                ));
            }
        }
        if let Ok(home) = std::env::var("USERPROFILE") {
            paths.push(format!(
                "{home}\\Documents\\Sports Interactive\\Football Manager 26\\fm.exe"
            ));
        }
        paths
    }

    #[test]
    #[cfg(target_os = "windows")]
    fn read_windows_file_versions_matches_locked_entity_map_when_fm_present() {
        let Some(path) = fm_exe_candidates()
            .into_iter()
            .find(|path| std::path::Path::new(path).is_file())
        else {
            return;
        };
        let Some((file_version, product_version)) = read_windows_file_versions(&path) else {
            panic!("could not read version info from {path}");
        };
        assert_eq!(
            file_version, "6000.0.52.8888375",
            "FileVersion must match PowerShell/.NET StringFileInfo (entity map fingerprint)"
        );
        assert!(
            product_version.contains("fm26"),
            "expected FM product version string, got {product_version}"
        );
    }
}
