//! The host's development tier: every job kache fronts runs inside the
//! systemd user slice `KACHE_SLICE` (default `dev.slice`; empty disables)
//! with `oom_score_adj` 1000.
//!
//! The kernel places a new process in its parent's cgroup, so a job started
//! by an agent harness would otherwise share the harness's tier. A job
//! outside the slice asks the user manager for a transient scope holding its
//! own PID (`org.freedesktop.systemd1.Manager.StartTransientUnit`, the call
//! `systemd-run --user --scope` makes), waits for the start job, and raises
//! its `oom_score_adj` once `/proc/self/cgroup` shows the slice. Children
//! inherit both, so a nested invocation reads `/proc/self/cgroup`, finds the
//! slice, and does nothing else.
//!
//! The call goes straight to the bus rather than re-executing through
//! `systemd-run`: no extra process or exec, and a refusal stays a value this
//! process can ignore. `systemd-run` execs the job in place, so after its
//! failure there would be no job left to run. Every failure — no bus, no
//! manager, a refused unit, a deadline — leaves the job where it started.

use std::ffi::OsStr;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

mod dbus;

const DEFAULT_SLICE: &str = "dev.slice";
/// The manager answers in about a millisecond; a stalled one must not stall
/// the build behind it.
const DEADLINE: Duration = Duration::from_secs(2);
const JOB_REMOVED: &str = "type='signal',sender='org.freedesktop.systemd1',\
    interface='org.freedesktop.systemd1.Manager',member='JobRemoved',\
    path='/org/freedesktop/systemd1'";

/// Move this process into the development slice unless it is already
/// there. Never fails: a job that cannot be moved runs where it is.
pub fn enter() {
    let configured = std::env::var_os("KACHE_SLICE");
    let Some(slice) = slice_name(configured.as_deref()) else {
        return;
    };
    if in_slice(&own_cgroup(), slice) != Some(false) {
        return;
    }
    let Some(bus) = bus_socket(
        std::env::var_os("DBUS_SESSION_BUS_ADDRESS").as_deref(),
        std::env::var_os("XDG_RUNTIME_DIR").as_deref(),
    ) else {
        return;
    };
    if start_scope(&bus, slice).is_err() {
        return;
    }
    if in_slice(&own_cgroup(), slice) == Some(true) {
        let _ = std::fs::write("/proc/self/oom_score_adj", "1000");
    }
}

/// The slice `KACHE_SLICE` names: the default when unset, `None` when empty
/// or not a slice unit name.
fn slice_name(value: Option<&OsStr>) -> Option<&str> {
    match value {
        None => Some(DEFAULT_SLICE),
        Some(value) => value.to_str().filter(|name| name.ends_with(".slice")),
    }
}

fn own_cgroup() -> String {
    std::fs::read_to_string("/proc/self/cgroup").unwrap_or_default()
}

/// Whether a `/proc/self/cgroup` text places the process under `slice`;
/// `None` without a cgroup v2 path. A nested slice (`dev-x.slice`) sits
/// under its parent's directory, so any path component may match.
fn in_slice(cgroup: &str, slice: &str) -> Option<bool> {
    let path = crate::cgroup_v2_path(cgroup)?;
    Some(path.split('/').any(|component| component == slice))
}

/// The user bus socket the way sd-bus finds it: `DBUS_SESSION_BUS_ADDRESS`
/// when set (its first address, `unix:path=` only), else
/// `$XDG_RUNTIME_DIR/bus`.
fn bus_socket(address: Option<&OsStr>, runtime_dir: Option<&OsStr>) -> Option<PathBuf> {
    match address {
        Some(address) => address
            .to_str()?
            .split(';')
            .next()?
            .strip_prefix("unix:")?
            .split(',')
            .find_map(|key| key.strip_prefix("path="))
            .map(PathBuf::from),
        None => runtime_dir
            .filter(|dir| !dir.is_empty())
            .map(|dir| Path::new(dir).join("bus")),
    }
}

/// Ask the user manager for a scope in `slice` holding this process, and
/// wait until its start job is finished.
fn start_scope(bus: &Path, slice: &str) -> std::io::Result<()> {
    let pid = std::process::id();
    let unit = scope_name(pid);
    let mut connection = dbus::Connection::open(bus, Instant::now() + DEADLINE)?;
    let mut rule = dbus::Writer::default();
    rule.string(JOB_REMOVED);
    connection.call(&dbus::Call {
        destination: "org.freedesktop.DBus",
        path: "/org/freedesktop/DBus",
        interface: "org.freedesktop.DBus",
        member: "AddMatch",
        signature: "s",
        body: &rule.into_bytes(),
    })?;
    connection.call(&dbus::Call {
        destination: "org.freedesktop.systemd1",
        path: "/org/freedesktop/systemd1",
        interface: "org.freedesktop.systemd1.Manager",
        member: "StartTransientUnit",
        signature: "ssa(sv)a(sa(sv))",
        body: &transient_scope(&unit, slice, pid),
    })?;
    loop {
        let message = connection.next()?;
        if message.kind == dbus::ERROR {
            return Err(std::io::Error::other("the user manager refused the scope"));
        }
        if message.member.as_deref() == Some("JobRemoved")
            && job_removed_unit(&message.body) == Some(unit.as_str())
        {
            return Ok(());
        }
    }
}

/// Unique among live scopes: the PID is, and the clock separates a reused
/// PID from a scope that outlived its first process.
fn scope_name(pid: u32) -> String {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("kache-{pid}-{nanos}.scope")
}

/// `StartTransientUnit(name, "fail", properties, [])` for a scope in `slice`
/// owning `pid`, collected once it stops even if it failed.
fn transient_scope(unit: &str, slice: &str, pid: u32) -> Vec<u8> {
    let mut body = dbus::Writer::default();
    body.string(unit).string("fail");
    body.array(8, |properties| {
        properties.align(8).string("PIDs").signature("au");
        properties.array(4, |pids| {
            pids.u32(pid);
        });
        properties
            .align(8)
            .string("Slice")
            .signature("s")
            .string(slice);
        properties
            .align(8)
            .string("CollectMode")
            .signature("s")
            .string("inactive-or-failed");
    });
    body.array(8, |_| {});
    body.into_bytes()
}

/// The unit named by a `JobRemoved(u id, o job, s unit, s result)` body.
fn job_removed_unit(body: &[u8]) -> Option<&str> {
    let mut reader = dbus::Reader::new(body);
    reader.u32()?;
    reader.string()?;
    reader.string()
}

#[cfg(test)]
#[path = "dev_slice/tests.rs"]
pub(crate) mod tests;
