//! `kache-test-runner`, the runner as its own binary: the same runner as
//! `kache test-runner`, started without the frontend or the engine.

#![cfg(unix)]

use std::path::Path;
use std::process::{Command, Stdio};

#[allow(dead_code)]
mod common;
use common::hermetic_command;

const RUNNER: &str = env!("CARGO_BIN_EXE_kache-test-runner");
const PROBE: &str = "probe-0123456789abcdef";

fn runner(dir: &Path) -> Command {
    let config = dir.join("kache.toml");
    std::fs::write(&config, "[cache]\nscheduler=false\n").unwrap();
    let mut command = hermetic_command(RUNNER, &dir.join("cache"), Some(&config));
    command
        .env("PROBE_DIR", dir)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    command
}

#[test]
fn the_binary_runs_the_test_and_hands_back_its_exit_code() {
    let dir = tempfile::tempdir().unwrap();
    kache_fs::testutil::write_executable(
        &dir.path().join(PROBE),
        "#!/bin/sh\nprintf 'probe-out %s\\n' \"$*\"\nexit 7\n",
    );
    let output = runner(dir.path())
        .arg(dir.path().join(PROBE))
        .args(["--exact", "t_0"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(7), "{output:?}");
    assert_eq!(output.stdout, b"probe-out --exact t_0\n");
}

/// `kache test-runner` through the frontend starts this binary, not the
/// engine: the test's parent is `kache-test-runner`.
#[cfg(target_os = "linux")]
#[test]
fn the_frontend_starts_the_binary_in_place_of_the_engine() {
    let dir = tempfile::tempdir().unwrap();
    kache_fs::testutil::write_executable(
        &dir.path().join(PROBE),
        "#!/bin/sh\nreadlink /proc/$PPID/exe > \"$PROBE_DIR/parent\"\n",
    );
    let mut command = runner(dir.path());
    command.arg("test-runner");
    let mut frontend = Command::new(env!("CARGO_BIN_EXE_kache"));
    frontend.args(command.get_args()).envs(
        command
            .get_envs()
            .filter_map(|(name, value)| value.map(|value| (name, value))),
    );
    let output = frontend
        .arg(dir.path().join(PROBE))
        .stdin(Stdio::null())
        .output()
        .unwrap();
    assert!(output.status.success(), "{output:?}");
    let parent = std::fs::read_to_string(dir.path().join("parent")).unwrap();
    assert_eq!(
        Path::new(parent.trim()).file_name().unwrap(),
        "kache-test-runner",
        "{parent}"
    );
}

/// A frontend without the runner beside it refuses `test-runner` instead
/// of compiling or starting the engine.
#[test]
fn a_frontend_without_the_runner_beside_it_says_what_to_reinstall() {
    let dir = tempfile::tempdir().unwrap();
    for (name, built) in [
        ("kache", env!("CARGO_BIN_EXE_kache")),
        ("kache-engine", env!("CARGO_BIN_EXE_kache-engine")),
    ] {
        std::fs::copy(built, dir.path().join(name)).unwrap();
    }
    kache_fs::testutil::write_executable(&dir.path().join(PROBE), "#!/bin/sh\nexit 0\n");
    let config = dir.path().join("kache.toml");
    std::fs::write(&config, "[cache]\nscheduler=false\n").unwrap();
    let output = hermetic_command(
        dir.path().join("kache"),
        &dir.path().join("cache"),
        Some(&config),
    )
    .arg("test-runner")
    .arg(dir.path().join(PROBE))
    .stdin(Stdio::null())
    .output()
    .unwrap();
    assert_eq!(output.status.code(), Some(1), "{output:?}");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("locating kache-test-runner"), "{stderr}");
    assert!(
        stderr.contains("reinstall all Kache binaries together"),
        "{stderr}"
    );
}

#[test]
fn the_binary_explains_itself_and_refuses_to_run_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let help = runner(dir.path()).arg("--help").output().unwrap();
    assert_eq!(help.status.code(), Some(0), "{help:?}");
    let stdout = String::from_utf8(help.stdout).unwrap();
    assert!(stdout.contains("Usage: kache test-runner"), "{stdout}");
    let none = runner(dir.path()).output().unwrap();
    assert_eq!(none.status.code(), Some(101), "{none:?}");
    let stderr = String::from_utf8(none.stderr).unwrap();
    assert!(stderr.contains("expected a test binary to run"), "{stderr}");
}
