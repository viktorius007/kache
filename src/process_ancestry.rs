//! The parent and executable of a running process, so the cargo proxy can
//! tell whether a real Cargo ran between it and the proxy above it.
//!
//! Linux reads `/proc`, macOS asks `proc_pidinfo` and `proc_pidpath`, Windows
//! takes a Toolhelp snapshot and `QueryFullProcessImageNameW`. Elsewhere
//! nothing is known and callers fall back.

use std::path::PathBuf;

/// `pid`'s parent and its executable, or `None` once `pid` cannot be read.
/// The executable is `None` when only it is unreadable, for example a process
/// of another user.
pub(crate) fn process(pid: u32) -> Option<(u32, Option<PathBuf>)> {
    Some((parent(pid)?, executable(pid)))
}

#[cfg(target_os = "linux")]
fn parent(pid: u32) -> Option<u32> {
    // The comm field may contain spaces and parentheses; the state and ppid
    // follow the last ')'.
    let stat = std::fs::read_to_string(format!("/proc/{pid}/stat")).ok()?;
    let mut fields = stat[stat.rfind(')')? + 1..].split_ascii_whitespace();
    fields.nth(1)?.parse().ok()
}

#[cfg(target_os = "linux")]
fn executable(pid: u32) -> Option<PathBuf> {
    std::fs::read_link(format!("/proc/{pid}/exe")).ok()
}

#[cfg(target_os = "macos")]
fn parent(pid: u32) -> Option<u32> {
    let mut info: libc::proc_bsdinfo = unsafe { std::mem::zeroed() };
    let size = std::mem::size_of::<libc::proc_bsdinfo>() as libc::c_int;
    let got = unsafe {
        libc::proc_pidinfo(
            pid as libc::c_int,
            libc::PROC_PIDTBSDINFO,
            0,
            (&mut info as *mut libc::proc_bsdinfo).cast(),
            size,
        )
    };
    (got == size).then_some(info.pbi_ppid)
}

#[cfg(target_os = "macos")]
fn executable(pid: u32) -> Option<PathBuf> {
    crate::fallback::macos::process_path(pid as i32)
}

#[cfg(windows)]
fn parent(pid: u32) -> Option<u32> {
    use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle};
    use windows_sys::Win32::Foundation::INVALID_HANDLE_VALUE;
    use windows_sys::Win32::System::Diagnostics::ToolHelp::{
        CreateToolhelp32Snapshot, PROCESSENTRY32W, Process32FirstW, Process32NextW,
        TH32CS_SNAPPROCESS,
    };
    let raw = unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0) };
    if raw == INVALID_HANDLE_VALUE {
        return None;
    }
    let snapshot = unsafe { OwnedHandle::from_raw_handle(raw) };
    let mut entry: PROCESSENTRY32W = unsafe { std::mem::zeroed() };
    entry.dwSize = std::mem::size_of::<PROCESSENTRY32W>() as u32;
    if unsafe { Process32FirstW(snapshot.as_raw_handle(), &mut entry) } == 0 {
        return None;
    }
    loop {
        if entry.th32ProcessID == pid {
            return Some(entry.th32ParentProcessID);
        }
        if unsafe { Process32NextW(snapshot.as_raw_handle(), &mut entry) } == 0 {
            return None;
        }
    }
}

#[cfg(windows)]
fn executable(pid: u32) -> Option<PathBuf> {
    use std::os::windows::ffi::OsStringExt;
    use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle};
    use windows_sys::Win32::System::Threading::{
        OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION, QueryFullProcessImageNameW,
    };
    let raw = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid) };
    if raw.is_null() {
        return None;
    }
    let process = unsafe { OwnedHandle::from_raw_handle(raw) };
    let mut buffer = [0u16; 32 * 1024];
    let mut length = buffer.len() as u32;
    let ok = unsafe {
        QueryFullProcessImageNameW(process.as_raw_handle(), 0, buffer.as_mut_ptr(), &mut length)
    };
    (ok != 0).then(|| PathBuf::from(std::ffi::OsString::from_wide(&buffer[..length as usize])))
}

#[cfg(not(any(target_os = "linux", target_os = "macos", windows)))]
fn parent(_pid: u32) -> Option<u32> {
    None
}

#[cfg(not(any(target_os = "linux", target_os = "macos", windows)))]
fn executable(_pid: u32) -> Option<PathBuf> {
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    #[test]
    fn this_process_has_its_parent_and_its_own_executable() {
        let (parent, executable) = process(std::process::id()).expect("this process is readable");
        assert_eq!(parent, unsafe { libc::getppid() } as u32);
        assert_eq!(
            executable.and_then(|path| path.canonicalize().ok()),
            std::env::current_exe().unwrap().canonicalize().ok()
        );
    }
}
