use anyhow::{Context, Result};
use std::ffi::OsString;
use std::process::Command;

#[cfg(windows)]
#[path = "frontend_windows.rs"]
mod windows;

/// Run the thin compiler client, or replace it with the companion CLI engine.
pub fn run(version: &str) -> Result<i32> {
    let started_at = std::time::Instant::now();
    let args = std::env::args_os().collect::<Vec<_>>();
    anyhow::ensure!(
        args.get(1)
            .is_none_or(|arg| arg != crate::FORWARDED_ARGV_FLAG),
        "kache-engine points to the client; reinstall both Kache binaries together"
    );
    let executable = std::env::current_exe().context("locating the Kache client")?;
    let executable = if executable.is_absolute() {
        executable
    } else {
        std::env::current_dir()?.join(executable)
    };
    if let Some(runner_args) = test_runner_args(&args) {
        return run_test_runner(&executable, runner_args);
    }
    #[cfg(target_os = "linux")]
    if fronts_a_job(&args) {
        crate::enter_dev_slice();
    }
    if engine_only(&args)
        || std::env::var_os("KACHE_FAMILY_PROBE_ACTIVE").is_some()
        || std::env::var_os("KACHE_BUILD_SCRIPT_PATH").is_some()
    {
        return forward_engine(&executable, version, &args, started_at);
    }
    #[cfg(any(unix, windows))]
    {
        let env = kache_config::InvocationEnv::capture();
        if env
            .var_os("KACHE_ACTIVE")
            .is_none_or(|value| value.is_empty())
        {
            let prepared = (|| -> Result<_> {
                let config = kache_config::Config::load_for(&env)?;
                #[cfg(unix)]
                let (files, terminal) = crate::Stdio::capture()?.into_files();
                #[cfg(windows)]
                let (files, terminal) = (Vec::new(), false);
                Ok((config, files, terminal))
            })();
            if let Ok((config, files, terminal)) = prepared {
                let execution = crate::Execution {
                    entry: kache_protocol::execution::ExecutionEntry::Original,
                    args: &args,
                    env: &env,
                    started_at,
                    executable: &executable,
                    files: &files,
                    terminal,
                    client_version: version,
                };
                let socket = config.socket_path();
                if let Some(exit) =
                    execution.try_execute_with_trust(&socket, config.trust_daemon_execution)?
                {
                    return Ok(exit);
                }
                #[cfg(windows)]
                if let Some(exit) = windows::try_bootstrap(
                    &execution,
                    &socket,
                    config.disabled,
                    config.trust_daemon_execution,
                )? {
                    return Ok(exit);
                }
            }
        }
    }
    forward_engine(&executable, version, &args, started_at)
}

/// The arguments after `test-runner` when the frontend was asked to run a
/// test binary. Behind a compiler-name shim argv[1] is a compiler argument,
/// so `cc test-runner` stays a compile.
fn test_runner_args(args: &[OsString]) -> Option<&[OsString]> {
    let arg0 = args.first()?.to_string_lossy();
    if kache_shims::is_compiler_shim_name(&arg0) || args.get(1)? != "test-runner" {
        return None;
    }
    Some(&args[2..])
}

/// Replace the frontend with the installed `kache-test-runner`: a test
/// starts a 3 MiB binary, not the engine.
fn run_test_runner(executable: &std::path::Path, args: &[OsString]) -> Result<i32> {
    let runner = kache_shims::test_runner_for(executable)
        .context("locating kache-test-runner; reinstall all Kache binaries together")?;
    let mut command = Command::new(runner);
    command.args(args);
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        Err(command.exec()).context("starting the Kache test runner")
    }
    #[cfg(not(unix))]
    {
        let status = command.status().context("starting the Kache test runner")?;
        Ok(status.code().unwrap_or(1))
    }
}

fn forward_engine(
    executable: &std::path::Path,
    version: &str,
    args: &[OsString],
    started_at: std::time::Instant,
) -> Result<i32> {
    let (mut command, _argv_file) =
        forwarded_command(executable, version, args, started_at, cfg!(windows))?;
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        Err(command.exec()).context("starting the Kache engine")
    }
    #[cfg(not(unix))]
    {
        let status = command.status().context("starting the Kache engine")?;
        Ok(status.code().unwrap_or(1))
    }
}

fn forwarded_command(
    executable: &std::path::Path,
    version: &str,
    args: &[OsString],
    started_at: std::time::Instant,
    _windows: bool,
) -> Result<(Command, Option<crate::argv_file::ArgvFile>)> {
    let mut command = engine_command(executable, version, &[], started_at)?;
    #[cfg(any(windows, test))]
    if _windows && crate::argv_file::command_too_long(&command, args) {
        let file = crate::argv_file::ArgvFile::new(args)?;
        let mut prefix: Vec<_> = command.get_args().map(OsString::from).collect();
        prefix[2] = startup_micros(started_at).into();
        let mut compact = Command::new(command.get_program());
        compact
            .args(prefix)
            .arg(crate::argv_file::FLAG)
            .arg(file.path());
        return Ok((compact, Some(file)));
    }
    command.args(args);
    Ok((command, None))
}

fn startup_micros(started_at: std::time::Instant) -> String {
    started_at
        .elapsed()
        .as_micros()
        .min(u128::from(u64::MAX))
        .to_string()
}

fn engine_command(
    executable: &std::path::Path,
    version: &str,
    args: &[OsString],
    started_at: std::time::Instant,
) -> Result<Command> {
    let engine = kache_shims::engine_for(executable)
        .context("locating kache-engine; reinstall both Kache binaries together")?;
    let mut command = Command::new(engine);
    command
        .arg(crate::FORWARDED_ARGV_FLAG)
        .arg(version)
        .arg(startup_micros(started_at))
        .arg(executable)
        .arg(
            kache_shims::running_identity()
                .map(|identity| format!("{}:{}", identity.dev, identity.ino))
                .unwrap_or_else(|| "-".to_owned()),
        )
        .args(args);
    #[cfg(target_os = "macos")]
    crate::restore_dyld_env(&mut command);
    Ok(command)
}

/// A build or a compile, as opposed to a `kache` command such as `gc`.
#[cfg(target_os = "linux")]
fn fronts_a_job(args: &[OsString]) -> bool {
    invoked_as_cargo(args) || !engine_only(args)
}

fn invoked_as_cargo(args: &[OsString]) -> bool {
    args.first()
        .and_then(|arg0| std::path::Path::new(arg0).file_stem())
        .is_some_and(|name| name == "cargo")
}

fn engine_only(args: &[OsString]) -> bool {
    let arg0 = args
        .first()
        .map(|arg| arg.to_string_lossy())
        .unwrap_or_default();
    if kache_shims::is_compiler_shim_name(&arg0) {
        return false;
    }
    if invoked_as_cargo(args) {
        return true;
    }
    let Some(first) = args.get(1) else {
        return true;
    };
    let Some(first) = first.to_str() else {
        return false;
    };
    crate::engine_command_names().contains(&first)
        || (first.starts_with('-') && !(first == "-E" && args.len() >= 3))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_runner_args_follow_the_subcommand_except_behind_a_compiler_shim() {
        let argv = |words: &[&str]| words.iter().map(OsString::from).collect::<Vec<_>>();
        assert_eq!(
            test_runner_args(&argv(&["kache", "test-runner", "bin", "--x"])),
            Some(&argv(&["bin", "--x"])[..])
        );
        assert_eq!(
            test_runner_args(&argv(&["/opt/kache", "test-runner"])),
            Some(&[][..])
        );
        assert_eq!(test_runner_args(&argv(&["cc", "test-runner", "bin"])), None);
        assert_eq!(test_runner_args(&argv(&["kache", "gc"])), None);
        assert_eq!(test_runner_args(&argv(&["kache"])), None);
        assert_eq!(test_runner_args(&argv(&[])), None);
    }

    #[test]
    fn long_windows_handoff_uses_a_file_and_preserves_the_versioned_envelope() {
        let root = tempfile::tempdir().unwrap();
        let frontend = root
            .path()
            .join(if cfg!(windows) { "kache.exe" } else { "kache" });
        let engine = root.path().join(if cfg!(windows) {
            "kache-engine.exe"
        } else {
            "kache-engine"
        });
        for path in [&frontend, &engine] {
            std::fs::write(path, "image").unwrap();
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o755)).unwrap();
            }
        }
        let frontend = frontend.canonicalize().unwrap();
        let args = vec!["kache".into(), "rustc".into(), "x".repeat(32_750).into()];
        let started = std::time::Instant::now();
        for windows in [false, true] {
            let (mut command, file) =
                forwarded_command(&frontend, "fixture", &args, started, windows).unwrap();
            let argv: Vec<_> = std::iter::once(command.get_program().to_owned())
                .chain(command.get_args().map(OsString::from))
                .collect();
            assert_eq!(argv[1], crate::FORWARDED_ARGV_FLAG);
            assert_eq!(argv[2], "fixture");
            assert_eq!(
                crate::engine_entry(argv.clone(), "fixture").unwrap().args,
                args
            );
            assert_eq!(
                crate::engine_entry(argv.clone(), "fixture").unwrap().args,
                args,
                "CLI command_args must be able to read the same envelope again"
            );
            assert!(
                crate::engine_entry(argv, "old-version")
                    .err()
                    .unwrap()
                    .to_string()
                    .contains("releases differ")
            );
            assert_eq!(file.is_some(), windows);
            assert_eq!(crate::argv_file::command_too_long(&command, &[]), !windows);
            if let Some(file) = file {
                let path = file.path().to_owned();
                std::fs::remove_file(&engine).unwrap();
                assert!(command.status().is_err());
                drop(file);
                assert!(
                    !path.exists(),
                    "failed engine spawn must clean its argv file"
                );
            }
        }
        std::fs::write(&engine, "image").unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&engine, std::fs::Permissions::from_mode(0o755)).unwrap();
        }
        let (_, file) = forwarded_command(
            &frontend,
            "fixture",
            &["kache".into(), "--help".into()],
            started,
            true,
        )
        .unwrap();
        assert!(file.is_none(), "short invocations stay inline");
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn builds_and_compiles_are_jobs_and_kache_commands_are_not() {
        let argv = |words: &[&str]| words.iter().map(OsString::from).collect::<Vec<_>>();
        for job in [
            &["cargo", "build"][..],
            &["/home/u/.local/lib/kache/shims/cargo"],
            &["cc", "-c", "a.c"],
            &["rustdoc", "--test", "lib.rs"],
            &["kache", "rustc", "lib.rs"],
        ] {
            assert!(fronts_a_job(&argv(job)), "{job:?}");
        }
        for command in [
            &["kache", "daemon", "run"][..],
            &["kache", "gc"],
            &["kache", "--help"],
            &["kache"],
        ] {
            assert!(!fronts_a_job(&argv(command)), "{command:?}");
        }
    }

    #[test]
    fn commands_flags_and_cargo_go_to_the_engine_before_configuration() {
        for args in [
            vec!["kache", "init"],
            vec!["kache", "help"],
            vec!["kache", "-E"],
            vec!["kache", "status"],
            vec!["renamed-kache", "--help"],
            vec!["cargo", "build"],
            vec!["kache"],
        ] {
            assert!(engine_only(
                &args.into_iter().map(OsString::from).collect::<Vec<_>>()
            ));
        }
        for args in [
            vec!["cc", "init"],
            vec!["x86_64-linux-gnu-gcc-13", "--help"],
            vec!["kache", "-E", "probe.c"],
            vec!["kache", "rustc", "lib.rs"],
        ] {
            assert!(!engine_only(
                &args.into_iter().map(OsString::from).collect::<Vec<_>>()
            ));
        }
    }
}

#[cfg(all(test, unix))]
#[path = "frontend/tests.rs"]
mod boundary_tests;
