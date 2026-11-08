//! The self-hosted CI Macs that run this suite carry a real
//! `/etc/kache/config.toml`. A kache a test spawns must see only the config
//! the test writes, so the shared harness turns the host layer off, the
//! repository's cargo `[env]` turns it off for every child that inherits the
//! test process's environment, and a test opts back in by naming a host file
//! on its own command.

#[allow(dead_code)]
mod common;

use common::{DaemonGuard, hermetic_command, kache_binary};
use std::ffi::OsString;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::{Mutex, MutexGuard};
use tempfile::TempDir;

/// The tests below read or change this process's `KACHE_HOST_CONFIG`.
static ENV_LOCK: Mutex<()> = Mutex::new(());

/// Holds [`ENV_LOCK`] and puts `KACHE_HOST_CONFIG` back when dropped, so a
/// failing assertion cannot leak a changed value into the next test.
struct HostConfigEnv {
    previous: Option<OsString>,
    _lock: MutexGuard<'static, ()>,
}

impl HostConfigEnv {
    fn lock() -> Self {
        let lock = ENV_LOCK.lock().unwrap_or_else(|error| error.into_inner());
        Self {
            previous: std::env::var_os("KACHE_HOST_CONFIG"),
            _lock: lock,
        }
    }

    fn set(&self, value: &Path) {
        // SAFETY: every test here holds ENV_LOCK while it touches the
        // variable, and nothing else in this binary reads it concurrently.
        unsafe { std::env::set_var("KACHE_HOST_CONFIG", value) };
    }
}

impl Drop for HostConfigEnv {
    fn drop(&mut self) {
        // SAFETY: as in `set`; ENV_LOCK is still held while this runs.
        unsafe {
            match self.previous.take() {
                Some(value) => std::env::set_var("KACHE_HOST_CONFIG", value),
                None => std::env::remove_var("KACHE_HOST_CONFIG"),
            }
        }
    }
}

/// One test's cache dir, and the guard that stops any daemon a kache spawned
/// against it. `kache doctor` can start one: it asks the C driver on `PATH`
/// to place the linker, and a kache `cc` shim there is a compile that
/// auto-starts a daemon in the child's cache dir. Fields drop in order, so the
/// guard stops that daemon before the directory goes, on a panic too.
struct Fixture {
    _daemon: DaemonGuard,
    dir: TempDir,
    cache: PathBuf,
}

impl Fixture {
    fn new() -> Self {
        let dir = tempfile::tempdir().unwrap();
        let cache = dir.path().join("cache");
        Self {
            _daemon: DaemonGuard::new(kache_binary(), &cache),
            dir,
            cache,
        }
    }

    /// A kache built without the harness: it inherits this process's
    /// environment, `PATH` included.
    fn direct_command(&self) -> Command {
        let mut command = Command::new(kache_binary());
        command
            .env("KACHE_CACHE_DIR", &self.cache)
            .env("KACHE_CONFIG", self.cache.join("config.toml"));
        command
    }
}

fn write_host_file(dir: &Path) -> PathBuf {
    let path = dir.join("host.toml");
    std::fs::write(&path, "[cache]\ninput_predictions = true\n").unwrap();
    path
}

/// The detail line of `kache doctor`'s "Host config" check.
fn host_config_detail(mut command: Command) -> String {
    let output = command
        .args(["--json", "doctor"])
        .output()
        .expect("run kache doctor");
    // Doctor may report unrelated failing checks on a given machine; only its
    // JSON document matters here.
    let doc: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap_or_else(|error| {
        panic!(
            "kache --json doctor: {error}\nstdout: {}\nstderr: {}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        )
    });
    // The machine-readable envelope flattens the body next to `command`.
    let checks = doc["checks"]
        .as_array()
        .unwrap_or_else(|| panic!("doctor lists no checks: {doc}"));
    checks
        .iter()
        .find(|check| check["label"] == "Host config")
        .unwrap_or_else(|| panic!("doctor has no Host config check: {doc}"))["detail"]
        .as_str()
        .expect("the check has a detail line")
        .to_string()
}

/// A machine-wide `KACHE_HOST_CONFIG` naming a real file stands in for the
/// default `/etc` path, which a test cannot write: a child the harness builds
/// must still see no host layer.
#[test]
fn a_harness_spawned_kache_ignores_the_host_file() {
    let env = HostConfigEnv::lock();
    let fixture = Fixture::new();
    let cache = &fixture.cache;
    let host = write_host_file(fixture.dir.path());

    env.set(&host);
    let detail = host_config_detail(hermetic_command(
        kache_binary(),
        cache,
        Some(&cache.join("config.toml")),
    ));

    assert_eq!(detail, "off (KACHE_HOST_CONFIG is empty)");
}

/// Most integration tests build their own `Command` rather than going through
/// the harness. The cargo `[env]` in `.cargo/config.toml` turns the layer off
/// for the test process, so those children inherit it off too.
#[test]
fn a_directly_spawned_kache_inherits_the_host_layer_off() {
    let _env = HostConfigEnv::lock();
    assert_eq!(
        std::env::var("KACHE_HOST_CONFIG").as_deref(),
        Ok(""),
        "run through cargo test or nextest, which apply .cargo/config.toml [env]"
    );
    let fixture = Fixture::new();
    assert_eq!(
        host_config_detail(fixture.direct_command()),
        "off (KACHE_HOST_CONFIG is empty)"
    );
}

/// A host with kache's shims on `PATH` turns the doctor run above into a
/// daemon in the test's cache dir. Unstopped, it outlived the test, held the
/// deleted directory open, and piled up across runs. A kache `cc` shim on the
/// child's `PATH` starts one on any host; the fixture must stop it while the
/// test unwinds.
#[cfg(target_os = "linux")]
#[test]
fn a_failing_test_still_stops_the_daemon_its_doctor_started() {
    let _env = HostConfigEnv::lock();
    let (lock_tx, lock_rx) = std::sync::mpsc::channel();
    let failed = std::thread::spawn(move || {
        let fixture = Fixture::new();
        let shims = fixture.dir.path().join("shims");
        std::fs::create_dir(&shims).unwrap();
        std::fs::write(shims.join(kache_shims::farm::MARKER), "").unwrap();
        std::os::unix::fs::symlink(kache_binary(), shims.join("cc")).unwrap();
        let path = std::env::var_os("PATH").unwrap_or_default();
        let path = std::env::join_paths(std::iter::once(shims).chain(std::env::split_paths(&path)))
            .unwrap();
        let mut command = fixture.direct_command();
        command.env("PATH", path);
        host_config_detail(command);

        let run_lock = std::fs::OpenOptions::new()
            .write(true)
            .open(fixture.cache.join("daemon.run.lock"))
            .expect("the doctor's shim compile started no daemon");
        assert!(
            matches!(run_lock.try_lock(), Err(std::fs::TryLockError::WouldBlock)),
            "the running daemon must hold its lifetime lock"
        );
        lock_tx.send(run_lock).unwrap();
        panic!("simulated test failure while the daemon runs");
    })
    .join();
    assert!(failed.is_err(), "the fixture thread must have panicked");

    let run_lock = lock_rx
        .recv()
        .expect("the daemon never started; see the fixture's panic above");
    run_lock
        .try_lock()
        .expect("the fixture's Drop must stop the daemon while the test unwinds");
    run_lock.unlock().unwrap();
}

#[test]
fn a_test_can_opt_into_a_host_file() {
    let _env = HostConfigEnv::lock();
    let fixture = Fixture::new();
    let cache = &fixture.cache;
    let host = write_host_file(fixture.dir.path());

    let mut command = hermetic_command(kache_binary(), cache, Some(&cache.join("config.toml")));
    command.env("KACHE_HOST_CONFIG", &host);
    let detail = host_config_detail(command);

    assert!(
        detail.starts_with(&host.display().to_string()),
        "the host file is in effect: {detail}"
    );
    assert!(detail.contains("cache.input_predictions"), "{detail}");
}
