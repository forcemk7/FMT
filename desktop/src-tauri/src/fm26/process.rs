#[cfg(target_os = "windows")]
pub(crate) fn find_fm26_process() -> Option<(u32, Option<String>)> {
    find_process_by_exe_names(&["fm.exe"]).map(|(pid, name)| (pid, Some(name)))
}

#[cfg(target_os = "windows")]
pub(crate) fn find_fmle_process() -> Option<(u32, String)> {
    find_process_by_exe_names(&[
        "fmle26.exe",
        "FM26 Live Editor.exe",
        "fmle.exe",
        "FMLE.exe",
        "FM Live Editor.exe",
    ])
}

#[cfg(target_os = "windows")]
pub(crate) fn find_process_by_exe_names(names: &[&str]) -> Option<(u32, String)> {
    use std::ffi::c_void;
    use std::mem::MaybeUninit;

    type Handle = *mut c_void;
    const TH32CS_SNAPPROCESS: u32 = 0x0000_0002;
    const INVALID_HANDLE_VALUE: Handle = -1isize as Handle;

    #[repr(C)]
    struct ProcessEntry32W {
        dw_size: u32,
        cnt_usage: u32,
        th32_process_id: u32,
        th32_default_heap_id: usize,
        th32_module_id: u32,
        cnt_threads: u32,
        th32_parent_process_id: u32,
        pc_pri_class_base: i32,
        dw_flags: u32,
        sz_exe_file: [u16; 260],
    }

    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn CreateToolhelp32Snapshot(dw_flags: u32, th32_process_id: u32) -> Handle;
        fn Process32FirstW(snapshot: Handle, entry: *mut ProcessEntry32W) -> i32;
        fn Process32NextW(snapshot: Handle, entry: *mut ProcessEntry32W) -> i32;
        fn CloseHandle(handle: Handle) -> i32;
    }

    unsafe {
        let snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if snapshot == INVALID_HANDLE_VALUE {
            return None;
        }

        let mut entry = MaybeUninit::<ProcessEntry32W>::zeroed();
        (*entry.as_mut_ptr()).dw_size = std::mem::size_of::<ProcessEntry32W>() as u32;

        let mut found = None;
        if Process32FirstW(snapshot, entry.as_mut_ptr()) != 0 {
            loop {
                let current = entry.assume_init_ref();
                let name_end = current
                    .sz_exe_file
                    .iter()
                    .position(|&unit| unit == 0)
                    .unwrap_or(current.sz_exe_file.len());
                let name = String::from_utf16_lossy(&current.sz_exe_file[..name_end]);
                if names.iter().any(|wanted| name.eq_ignore_ascii_case(wanted)) {
                    found = Some((current.th32_process_id, name));
                    break;
                }
                if Process32NextW(snapshot, entry.as_mut_ptr()) == 0 {
                    break;
                }
            }
        }

        CloseHandle(snapshot);
        found
    }
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn find_fm26_process() -> Option<(u32, Option<String>)> {
    None
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn find_fmle_process() -> Option<(u32, String)> {
    None
}
