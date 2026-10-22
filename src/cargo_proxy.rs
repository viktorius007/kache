//! Guarded Cargo front-end for canonical duplicate config files (#766).
//!
//! Cargo merges array-valued configuration every time a config path is
//! discovered.  An ancestor `.cargo` symlink to `$CARGO_HOME` therefore reads
//! one physical `build.rustflags` array twice.  `RUSTC_WRAPPER` runs too late to
//! repair Cargo's unit identities, so `kache cargo -- ...` removes only that
//! duplicate source before Cargo computes them.

use anyhow::{Context, Result, bail};
use std::ffi::{OsStr, OsString};
use std::io::{self, BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{ChildStdout, Command, ExitStatus, Stdio};
use std::sync::mpsc::{self, Receiver, SyncSender};
use std::time::{Duration, Instant};

const ENCODED_SEPARATOR: char = '\x1f';
const WORKTREE_BUILD_DIR_CONFIG: &str = "build.build-dir=\"{workspace-root}/target\"";
/// Where the collapsed flags go. `--config` arrays append to config-file
/// arrays, so `build.rustflags` cannot be replaced from the command line.
/// Cargo uses matching `target.*.rustflags` instead of `build.rustflags`, and
/// `cfg(all())` matches every target. No plan is made when target rustflags or
/// a rustflags environment variable exist, so nothing else is shadowed.
/// Cargo's first target-info probe runs before `cfg` keys match, so it still
/// passes the duplicated flags to rustc. Only flags rustc accepts twice take
/// this route; see [`rustflags_repeat_safely`].
const ALL_TARGETS_RUSTFLAGS_KEY: &str = "target.\"cfg(all())\".rustflags";

/// Cargo `major.minor`.
type CargoVersion = (u64, u64);
/// Older Cargo rejects `--config` on stable.
const CONFIG_ARGUMENT_CARGO: CargoVersion = (1, 63);
/// Older Cargo has no stable `build.build-dir`. Some versions warn about the
/// unknown key, and none of them isolate anything with it.
const BUILD_DIR_CARGO: CargoVersion = (1, 91);

/// rustc options that may be given more than once, checked against rustc 1.85
/// and 1.98. Single-use options such as `--sysroot`, `--color` or `--target`
/// make rustc fail when repeated.
const REPEATABLE_RUSTC_FLAGS: &[&str] = &["-O", "-g"];
const REPEATABLE_RUSTC_SHORT_OPTIONS: &[char] = &['A', 'C', 'D', 'F', 'L', 'W', 'Z', 'l'];
const REPEATABLE_RUSTC_LONG_OPTIONS: &[&str] = &[
    "allow",
    "cfg",
    "check-cfg",
    "codegen",
    "deny",
    "forbid",
    "force-warn",
    "remap-path-prefix",
    "warn",
];

#[derive(Debug, Clone)]
struct ConfigSource {
    logical_path: PathBuf,
    canonical_path: PathBuf,
    content_hash: blake3::Hash,
    value: toml::Value,
    cargo_home: bool,
}

#[derive(Debug)]
struct NormalizationPlan {
    rustflags: Vec<String>,
    snapshots: Vec<ConfigSource>,
    cwd: PathBuf,
    cargo_home: PathBuf,
    candidate_paths: Vec<PathBuf>,
    duplicate_paths: Vec<PathBuf>,
}

#[derive(Debug)]
struct BuildDirIsolationPlan {
    snapshots: Vec<ConfigSource>,
    cwd: PathBuf,
    cargo_home: PathBuf,
    candidate_paths: Vec<PathBuf>,
}

#[derive(Debug)]
enum PlanDecision {
    Apply(NormalizationPlan),
    Passthrough,
    Refused(String),
}

/// Run Cargo with canonical duplicate `$CARGO_HOME` rustflags collapsed once.
///
/// Every ambiguous case fails closed by launching Cargo unchanged. That keeps
/// this command a conservative convenience rather than a second, incomplete
/// Cargo config implementation.
pub(crate) fn run(cargo_args: Vec<OsString>) -> Result<()> {
    let level = ProxyLevel::current();
    if level.reentered() {
        return run_reentered(&cargo_args, &level);
    }
    run_with_source(cargo_args)
}

/// Cargo reached through the `cargo` link in Kache's shim directory.
pub(crate) fn run_shim(cargo_args: Vec<OsString>) -> Result<()> {
    let level = ProxyLevel::current();
    if level.reentered() {
        return run_reentered(&cargo_args, &level);
    }
    let cargo = real_cargo_program(CargoRoute::Shim)?;
    let mut command = Command::new(&cargo);
    command.args(&cargo_args);
    level.mark(&mut command, &argv0(), &cargo);
    crate::target_seed::configure_cargo_seed(&mut command, &cargo_args, false);
    run_cargo_with_target_protection(command, &cargo)
}

fn run_with_source(cargo_args: Vec<OsString>) -> Result<()> {
    let cwd = std::env::current_dir().context("resolving the Cargo working directory")?;
    let cargo = real_cargo_program(CargoRoute::Command)?;

    // Cargo owns freshness before RUSTC_WRAPPER runs. Sharing its intermediate
    // fingerprint directory across worktrees can therefore declare the wrong
    // worktree Fresh without invoking Kache at all (#760). Cargo 1.91+'s
    // build-dir split keeps intermediates local while leaving final artifacts
    // in the caller's target-dir. Explicit environment or Cargo-config
    // build-dir policies retain precedence.
    let build_dir_plan = match worktree_build_dir_isolation_plan(
        &cwd,
        &cargo_args,
        std::env::var_os("CARGO_BUILD_BUILD_DIR").as_deref(),
    ) {
        Ok(plan) => plan,
        Err(reason) => {
            eprintln!(
                "kache: cannot safely isolate Cargo's build directory: {reason}; \
                 retaining Cargo's configured layout"
            );
            None
        }
    };

    let mut rustflags = None;
    match normalization_plan(&cwd, &cargo_args) {
        PlanDecision::Apply(plan) => {
            if !plan_is_current(&plan) {
                eprintln!(
                    "kache: Cargo config changed while it was being inspected; \
                     running Cargo unchanged"
                );
            } else {
                tracing::info!(
                    aliases = ?plan.duplicate_paths,
                    "collapsing canonical duplicate Cargo rustflags source"
                );
                rustflags = Some(plan.rustflags);
            }
        }
        PlanDecision::Refused(reason) => {
            eprintln!(
                "kache: safe Cargo config normalization is unavailable: \
                 {reason}; running Cargo unchanged"
            );
        }
        PlanDecision::Passthrough => {}
    }

    // Revalidate immediately before launch. If a config file or candidate set
    // changed after inspection, leave Cargo's layout untouched rather than
    // override a newly configured build-dir policy with stale information.
    let mut isolate_build_dir = false;
    if let Some(plan) = build_dir_plan {
        if build_dir_plan_is_current(&plan) {
            isolate_build_dir = true;
        } else {
            eprintln!(
                "kache: Cargo config changed while build-dir isolation was being inspected; \
                 retaining Cargo's configured layout"
            );
        }
    }

    let overrides = cargo_overrides(rustflags.as_deref(), isolate_build_dir, || {
        cargo_version(&cargo, &cargo_args, &cwd)
    });
    let mut command = Command::new(&cargo);
    command
        .args(cargo_invocation_args(&cargo_args, &overrides.config))
        .current_dir(&cwd);
    mark_started_cargo(&mut command, &cargo);
    if let Some(flags) = &overrides.encoded_rustflags {
        command.env("CARGO_ENCODED_RUSTFLAGS", flags);
    }

    crate::target_seed::configure_cargo_seed(
        &mut command,
        &cargo_args,
        overrides
            .config
            .iter()
            .any(|value| value == WORKTREE_BUILD_DIR_CONFIG),
    );

    run_cargo_with_target_protection(command, &cargo)
}

fn run_cargo_with_target_protection(command: Command, cargo: &Path) -> Result<()> {
    let config = crate::config::Config::load().context("loading the cache configuration")?;
    let what = cargo_command_label(command.get_args());
    let target_use = crate::target_use::shared_for(&config.cache_dir, &what, command.get_args())
        .context("protecting target directories while Cargo runs")?;
    run_cargo_guarded(command, cargo, target_use, &config)
}

/// `cargo <subcommand>`, for a cleanup that has to wait for this command.
fn cargo_command_label<'a>(args: impl IntoIterator<Item = &'a OsStr>) -> String {
    let mut args = args.into_iter().map(OsStr::to_string_lossy);
    let mut subcommand = None;
    while let Some(arg) = args.next() {
        // Cargo's global options that take a separate value.
        if matches!(&*arg, "--config" | "-Z" | "-C" | "--color" | "--explain") {
            args.next();
        } else if !arg.starts_with('-') && !arg.starts_with('+') {
            subcommand = Some(arg);
            break;
        }
    }
    match subcommand {
        Some(subcommand) => format!("cargo {subcommand}"),
        None => "cargo".to_owned(),
    }
}

/// Set in the environment of every Cargo a proxy starts: how many proxies
/// are above it.
const PROXY_DEPTH_ENV: &str = "KACHE_CARGO_PROXY_DEPTH";
/// One `<argv[0]> ran <cargo>` entry per proxy above, joined by
/// [`PROXY_CHAIN_SEPARATOR`], for the error that ends a loop.
const PROXY_CHAIN_ENV: &str = "KACHE_CARGO_PROXY_CHAIN";
const PROXY_CHAIN_SEPARATOR: &str = "\x1f";
/// Proxies above this one that are still tolerated. A build script or test
/// that runs `cargo` through PATH, inside a build a proxy started, re-enters
/// once per level of nesting; a `cargo` wrapper that forwards back to Kache
/// re-enters on every hop.
const MAX_PROXY_DEPTH: u32 = 2;

/// Where this proxy sits in a chain of proxies, from its environment.
#[derive(Debug, Default, PartialEq, Eq)]
struct ProxyLevel {
    /// Proxies above this one. Zero when no proxy started this process's
    /// Cargo tree.
    depth: u32,
    chain: Vec<String>,
}

impl ProxyLevel {
    fn current() -> Self {
        Self::from_env(
            std::env::var_os(PROXY_DEPTH_ENV).as_deref(),
            std::env::var_os(PROXY_CHAIN_ENV).as_deref(),
        )
    }

    /// An unreadable depth still means a proxy set it.
    fn from_env(depth: Option<&OsStr>, chain: Option<&OsStr>) -> Self {
        let Some(depth) = depth else {
            return Self::default();
        };
        let chain = chain.map(OsStr::to_string_lossy).unwrap_or_default();
        Self {
            depth: depth.to_str().and_then(|d| d.parse().ok()).unwrap_or(1),
            chain: chain
                .split(PROXY_CHAIN_SEPARATOR)
                .filter(|entry| !entry.is_empty())
                .map(str::to_owned)
                .collect(),
        }
    }

    /// Reached from inside a Cargo tree a proxy started, through something
    /// that is not Cargo: a `cargo` wrapper, or Cargo's descendants running
    /// `cargo` through PATH.
    fn reentered(&self) -> bool {
        self.depth > 0
    }

    /// Mark `command`, which runs `cargo`, as started by this proxy.
    fn mark(&self, command: &mut Command, argv0: &str, cargo: &Path) {
        let mut chain = self.chain.clone();
        chain.push(format!("{argv0} ran {}", cargo.display()));
        command
            .env(PROXY_DEPTH_ENV, self.depth.saturating_add(1).to_string())
            .env(PROXY_CHAIN_ENV, chain.join(PROXY_CHAIN_SEPARATOR));
    }

    /// Refuse past [`MAX_PROXY_DEPTH`], naming every hop of the loop.
    fn check(&self, argv0: &str) -> Result<()> {
        if self.depth <= MAX_PROXY_DEPTH {
            return Ok(());
        }
        let mut hops = String::new();
        for entry in &self.chain {
            hops.push_str(&format!("\n  {entry}"));
        }
        bail!(
            "kache's cargo proxy was re-entered {depth} times ({PROXY_DEPTH_ENV}={depth}, \
             limit {MAX_PROXY_DEPTH}): a `cargo` that is not Cargo leads back to kache.{hops}\n  \
             {argv0} refused\nSet KACHE_REAL_CARGO to the real Cargo, or remove the \
             wrapper that forwards to kache",
            depth = self.depth,
        )
    }
}

/// How this process was started, for [`ProxyLevel`]'s chain.
fn argv0() -> String {
    std::env::args_os()
        .next()
        .unwrap_or_default()
        .to_string_lossy()
        .into_owned()
}

/// Mark `command`, which runs `cargo`, as started from this process, so a
/// `cargo` wrapper it reaches cannot bring the proxy back for long.
pub(crate) fn mark_started_cargo(command: &mut Command, cargo: &Path) {
    ProxyLevel::current().mark(command, &argv0(), cargo);
}

/// Run Cargo for a proxy that another proxy's Cargo tree reached. Nothing
/// that could start Cargo again runs first: no PATH lookup, no config
/// inspection, no target protection.
fn run_reentered(cargo_args: &[OsString], level: &ProxyLevel) -> Result<()> {
    level.check(&argv0())?;
    let cargo = real_cargo_program(CargoRoute::WithoutPath)?;
    let mut command = Command::new(&cargo);
    command.args(cargo_args);
    level.mark(&mut command, &argv0(), &cargo);
    exec_cargo(command, &cargo)
}

/// Become Cargo. Windows has no exec, so Cargo's exit code is passed on.
fn exec_cargo(mut command: Command, cargo: &Path) -> Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        let error = command.exec();
        Err(error).with_context(|| format!("running Cargo {}", cargo.display()))
    }
    #[cfg(not(unix))]
    {
        let status = command
            .status()
            .with_context(|| format!("running Cargo {}", cargo.display()))?;
        std::process::exit(status.code().unwrap_or(1));
    }
}

/// Which sources may name the real Cargo.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum CargoRoute {
    /// `kache cargo`.
    Command,
    /// The `cargo` link in Kache's shim directory. `CARGO` there is the
    /// toolchain binary of an enclosing build, which would ignore a
    /// `+toolchain` argument and the project's toolchain file.
    Shim,
    /// Where a `cargo` found on PATH could lead back to Kache: a re-entered
    /// proxy, and workspace discovery under the rustc wrapper.
    WithoutPath,
}

/// What the environment says about where the real Cargo is.
#[derive(Debug, Default)]
struct CargoEnvironment {
    real_cargo: Option<OsString>,
    cargo: Option<PathBuf>,
    cargo_home: Option<PathBuf>,
    home: Option<PathBuf>,
}

impl CargoEnvironment {
    fn current() -> Self {
        Self {
            real_cargo: std::env::var_os("KACHE_REAL_CARGO"),
            cargo: std::env::var_os("CARGO").map(PathBuf::from),
            cargo_home: std::env::var_os("CARGO_HOME").map(PathBuf::from),
            home: dirs::home_dir(),
        }
    }
}

/// The program to run as Cargo, before [`resolve_cargo_program`] checks it:
/// `KACHE_REAL_CARGO`; `CARGO` as Cargo sets it for its children; the
/// toolchain proxy in Cargo's home, which selects a toolchain without PATH;
/// and only then `search_path`. `is_kache` rejects a candidate that is this
/// executable under another name.
fn real_cargo_candidate(
    env: &CargoEnvironment,
    route: CargoRoute,
    is_kache: impl Fn(&Path) -> bool,
    search_path: impl FnOnce() -> Option<PathBuf>,
) -> Option<OsString> {
    if let Some(program) = &env.real_cargo {
        return Some(program.clone());
    }
    let from_cargo = env
        .cargo
        .clone()
        .filter(|cargo| route != CargoRoute::Shim && cargo.is_absolute() && !is_kache(cargo));
    let from_cargo_home = || {
        let home = env
            .cargo_home
            .clone()
            .or_else(|| env.home.as_ref().map(|home| home.join(".cargo")))?;
        let cargo = home
            .join("bin")
            .join(format!("cargo{}", std::env::consts::EXE_SUFFIX));
        (cargo.is_file() && !is_kache(&cargo)).then_some(cargo)
    };
    from_cargo
        .or_else(from_cargo_home)
        .or_else(|| {
            (route != CargoRoute::WithoutPath)
                .then(search_path)
                .flatten()
        })
        .map(PathBuf::into_os_string)
}

/// The real Cargo for `route`, never this executable.
pub(crate) fn real_cargo_program(route: CargoRoute) -> Result<PathBuf> {
    let kache = kache_identity();
    let program = real_cargo_candidate(
        &CargoEnvironment::current(),
        route,
        |path| is_kache(path, kache.as_deref()),
        || crate::compiler::shim::resolve_real_compiler_from_env("cargo"),
    )
    .context("finding the real Cargo; set KACHE_REAL_CARGO to its path")?;
    let cwd = std::env::current_dir().context("resolving the Cargo working directory")?;
    resolve_cargo_program(&program, &cwd)
}

fn kache_identity() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()
        .and_then(|path| path.canonicalize().ok())
}

/// Whether `path` is the executable `kache` canonicalises to.
fn is_kache(path: &Path, kache: Option<&Path>) -> bool {
    kache.is_some() && path.canonicalize().ok().as_deref() == kache
}

/// Maximum retained Cargo protocol line. Longer stdout still reaches the user,
/// but cannot establish a complete artifact receipt.
const MAX_CARGO_PROTOCOL_LINE: usize = 4 * 1024 * 1024;
const INVALID_CARGO_STREAM: &[u8] = b"\0kache-invalid-cargo-stream\n";
const CARGO_DRAIN_TIMEOUT: Duration = Duration::from_secs(2);

/// Stay alive with the lease until Cargo and everything it runs has exited.
fn run_cargo_guarded(
    mut command: Command,
    cargo: &Path,
    _lease: crate::target_use::Lease,
    config: &crate::config::Config,
) -> Result<()> {
    let mut capture = crate::target_liveness::Capture::prepare(&command, cargo, config);
    // Start the reader before changing Cargo's stdout mode. If the OS cannot
    // create a thread, Cargo retains its ordinary output and execution path.
    let reader = if capture.is_some() {
        match start_cargo_stdout_reader() {
            Ok(reader) => Some(reader),
            Err(error) => {
                tracing::warn!(%error, "target liveness stdout capture unavailable");
                capture = None;
                None
            }
        }
    } else {
        None
    };
    if let Some(capture) = &capture {
        if capture.human_output() {
            command.arg("--message-format=json-render-diagnostics");
        }
        command.stdout(Stdio::piped());
    }
    let mut child = command
        .spawn()
        .with_context(|| format!("running Cargo program {cargo:?}"))?;
    crate::test_runner::signals::forward_to(child.id());
    let status = match (capture.as_mut(), reader) {
        (Some(capture), Some((ready, messages))) => match child.stdout.take() {
            Some(stdout) => {
                if ready.send(stdout).is_ok() {
                    drain_cargo_stdout(&mut child, capture, messages)?
                } else {
                    capture.observe(INVALID_CARGO_STREAM);
                    child.wait().context("waiting for Cargo")?
                }
            }
            None => {
                capture.observe(INVALID_CARGO_STREAM);
                child.wait().context("waiting for Cargo")?
            }
        },
        _ => child.wait().context("waiting for Cargo")?,
    };
    if let Some(capture) = capture
        && let Err(error) = capture.finish(status.success())
    {
        tracing::warn!(%error, "target liveness receipt not recorded");
    }
    std::process::exit(crate::test_runner::finish(
        crate::test_runner::exit_disposition(
            status.code(),
            crate::test_runner::signals::of(&status),
        ),
    ));
}

enum CargoStdoutMessage {
    Bytes(Vec<u8>),
    Finished,
    Failed(io::Error),
}

/// Both channels and the reader buffer are bounded. Dropping the receiver
/// releases a blocked send; a descendant retaining the pipe never delays the
/// Cargo exit path because the reader is not joined.
fn start_cargo_stdout_reader() -> io::Result<(SyncSender<ChildStdout>, Receiver<CargoStdoutMessage>)>
{
    let (ready, input) = mpsc::sync_channel::<ChildStdout>(1);
    let (sender, messages) = mpsc::sync_channel(8);
    let _reader = std::thread::Builder::new()
        .name("cargo-stdout".into())
        .spawn(move || {
            let Ok(stdout) = input.recv() else {
                return;
            };
            read_cargo_stdout(BufReader::with_capacity(8192, stdout), sender);
        })?;
    Ok((ready, messages))
}

fn read_cargo_stdout(mut reader: impl BufRead, sender: SyncSender<CargoStdoutMessage>) {
    loop {
        match reader.fill_buf() {
            Ok([]) => {
                let _ = sender.send(CargoStdoutMessage::Finished);
                return;
            }
            Ok(bytes) => {
                let count = bytes.len();
                if sender
                    .send(CargoStdoutMessage::Bytes(bytes.to_vec()))
                    .is_err()
                {
                    return;
                }
                reader.consume(count);
            }
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            Err(error) => {
                let _ = sender.send(CargoStdoutMessage::Failed(error));
                return;
            }
        }
    }
}

fn cargo_drain_expired(exited_at: Option<Instant>, now: Instant) -> bool {
    exited_at.is_some_and(|at| now.saturating_duration_since(at) >= CARGO_DRAIN_TIMEOUT)
}

fn drain_cargo_stdout(
    child: &mut std::process::Child,
    capture: &mut crate::target_liveness::Capture,
    messages: Receiver<CargoStdoutMessage>,
) -> Result<ExitStatus> {
    let mut status = None;
    let mut exited_at = None;
    let mut output = CargoOutput::new(capture.human_output());
    let stdout = io::stdout();
    let mut writer = stdout.lock();
    loop {
        if status.is_none()
            && let Some(exited) = child.try_wait().context("checking Cargo status")?
        {
            status = Some(exited);
            exited_at = Some(Instant::now());
        }
        match messages.recv_timeout(Duration::from_millis(25)) {
            Ok(CargoStdoutMessage::Bytes(bytes)) => {
                if let Err(error) =
                    output.push(&bytes, &mut |line| capture.observe(line), &mut writer)
                {
                    capture.observe(INVALID_CARGO_STREAM);
                    tracing::debug!(%error, "forwarding Cargo stdout failed");
                }
            }
            Ok(CargoStdoutMessage::Finished) => {
                if let Err(error) = output.finish(&mut |line| capture.observe(line), &mut writer) {
                    capture.observe(INVALID_CARGO_STREAM);
                    tracing::debug!(%error, "forwarding Cargo stdout tail failed");
                }
                break;
            }
            Ok(CargoStdoutMessage::Failed(error)) => {
                capture.observe(INVALID_CARGO_STREAM);
                tracing::warn!(%error, "reading Cargo stdout failed");
                break;
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                capture.observe(INVALID_CARGO_STREAM);
                break;
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {}
        }
        if cargo_drain_expired(exited_at, Instant::now()) {
            capture.observe(INVALID_CARGO_STREAM);
            // Preserve the nonprotocol tail, but do not certify a partial stream.
            if let Err(error) = writer.write_all(&output.line) {
                tracing::debug!(%error, "forwarding incomplete Cargo stdout failed");
            }
            tracing::warn!(
                "Cargo exited while a descendant retained its stdout; receipt not recorded"
            );
            break;
        }
    }
    match status {
        Some(status) => Ok(status),
        None => child.wait().context("waiting for Cargo"),
    }
}

struct CargoOutput {
    line: Vec<u8>,
    oversized: bool,
    human: bool,
}

impl CargoOutput {
    fn new(human: bool) -> Self {
        Self {
            line: Vec::new(),
            oversized: false,
            human,
        }
    }

    /// Incremental bounded framing. An oversized line is streamed unchanged
    /// until its newline, then framing resumes for subsequent records.
    fn push(
        &mut self,
        bytes: &[u8],
        observe: &mut impl FnMut(&[u8]) -> bool,
        writer: &mut impl Write,
    ) -> io::Result<()> {
        let mut error = None;
        for part in bytes.split_inclusive(|byte| *byte == b'\n') {
            let result = if self.oversized {
                self.oversized = !part.ends_with(b"\n");
                writer.write_all(part)
            } else if part.len() > MAX_CARGO_PROTOCOL_LINE.saturating_sub(self.line.len()) {
                observe(INVALID_CARGO_STREAM);
                let result = writer
                    .write_all(&self.line)
                    .and_then(|_| writer.write_all(part));
                self.line.clear();
                self.oversized = !part.ends_with(b"\n");
                result
            } else {
                self.line.extend_from_slice(part);
                if part.ends_with(b"\n") {
                    self.emit(observe, writer)
                } else {
                    Ok(())
                }
            };
            if let Err(failed) = result {
                error.get_or_insert(failed);
            }
        }
        match error {
            Some(error) => Err(error),
            None => Ok(()),
        }
    }

    fn finish(
        &mut self,
        observe: &mut impl FnMut(&[u8]) -> bool,
        writer: &mut impl Write,
    ) -> io::Result<()> {
        if self.line.is_empty() {
            Ok(())
        } else {
            self.emit(observe, writer)
        }
    }

    fn emit(
        &mut self,
        observe: &mut impl FnMut(&[u8]) -> bool,
        writer: &mut impl Write,
    ) -> io::Result<()> {
        let protocol = observe(&self.line);
        let result = if self.human && protocol {
            replay_rendered_cargo_diagnostic(&self.line);
            Ok(())
        } else {
            writer.write_all(&self.line)
        };
        self.line.clear();
        result
    }
}

fn rendered_cargo_diagnostic(line: &[u8]) -> Option<String> {
    let message = serde_json::from_slice::<serde_json::Value>(line).ok()?;
    if message["reason"] != "compiler-message" {
        return None;
    }
    message["message"]["rendered"].as_str().map(str::to_string)
}

fn replay_rendered_cargo_diagnostic(line: &[u8]) {
    if let Some(rendered) = rendered_cargo_diagnostic(line)
        && let Err(error) = io::stderr().lock().write_all(rendered.as_bytes())
    {
        tracing::debug!(%error, "forwarding rendered Cargo diagnostic failed");
    }
}

fn resolve_cargo_program(program: &OsStr, cwd: &Path) -> Result<PathBuf> {
    let path = Path::new(program);
    let executable = match program.to_str() {
        Some(program) => crate::compiler::resolve_program_on_path(program),
        None => Some(path.to_path_buf()),
    }
    .with_context(|| format!("resolving Cargo program {program:?}"))?;
    let executable = if executable.is_absolute() {
        executable
    } else {
        cwd.join(executable)
    };
    executable
        .canonicalize()
        .with_context(|| format!("resolving Cargo program {program:?}"))?;
    if is_kache(&executable, kache_identity().as_deref()) {
        bail!(
            "resolved Cargo program {:?} points back to kache; set KACHE_REAL_CARGO to the real Cargo binary",
            program
        );
    }
    // Preserve the launcher path. In a rustup installation `cargo` is a symlink
    // to the shared rustup binary, whose behavior depends on argv[0]. Executing
    // its canonical target would launch `rustup`, not the Cargo proxy.
    Ok(executable)
}

fn normalization_plan(cwd: &Path, cargo_args: &[OsString]) -> PlanDecision {
    if rustflags_environment_is_explicit() {
        return PlanDecision::Passthrough;
    }
    if supported_cargo_command(cargo_args).is_err() {
        return PlanDecision::Passthrough;
    }

    let cargo_home = match cargo_home(cwd) {
        Ok(cargo_home) => cargo_home,
        Err(reason) => return PlanDecision::Refused(reason),
    };
    let candidates = cargo_config_candidates(cwd, &cargo_home);
    let mut sources = Vec::with_capacity(candidates.len());
    let candidate_paths = candidates.iter().map(|(path, _)| path.clone()).collect();
    for (logical_path, cargo_home) in candidates {
        match read_source(logical_path, cargo_home) {
            Ok(source) => sources.push(source),
            Err(reason) => return PlanDecision::Refused(reason),
        }
    }

    let Some(home_source) = sources.iter().find(|source| source.cargo_home) else {
        return PlanDecision::Passthrough;
    };
    let home_canonical = home_source.canonical_path.clone();
    let duplicate_paths: Vec<PathBuf> = sources
        .iter()
        .filter(|source| is_cargo_home_alias(source, &home_canonical))
        .map(|source| source.logical_path.clone())
        .collect();
    if duplicate_paths.is_empty() {
        return PlanDecision::Passthrough;
    }

    let mut rustflags = Vec::new();
    for source in &sources {
        if is_cargo_home_alias(source, &home_canonical) {
            continue;
        }
        match source_rustflags(&source.value, &source.logical_path) {
            Ok(Some(flags)) => rustflags.extend(flags),
            Ok(None) => {}
            Err(reason) => return PlanDecision::Refused(reason),
        }
    }
    if rustflags.is_empty() {
        return PlanDecision::Refused(
            "the canonical duplicate has no array-valued build.rustflags".into(),
        );
    }
    PlanDecision::Apply(NormalizationPlan {
        rustflags,
        snapshots: sources,
        cwd: cwd.to_path_buf(),
        cargo_home,
        candidate_paths,
        duplicate_paths,
    })
}

fn is_cargo_home_alias(source: &ConfigSource, home_canonical: &Path) -> bool {
    !source.cargo_home && source.canonical_path == home_canonical
}

fn rustflags_environment_is_explicit() -> bool {
    std::env::vars_os().any(|(key, _)| {
        let Some(key) = key.to_str() else {
            return false;
        };
        rustflags_env_name(key, cfg!(windows))
    })
}

fn rustflags_env_name(key: &str, case_insensitive: bool) -> bool {
    let key = if case_insensitive {
        key.to_ascii_uppercase()
    } else {
        key.to_string()
    };
    key == "RUSTFLAGS"
        || key == "CARGO_ENCODED_RUSTFLAGS"
        || (key.starts_with("CARGO_") && key.ends_with("RUSTFLAGS"))
}

fn supported_cargo_command(args: &[OsString]) -> std::result::Result<(), String> {
    let Some((first, remaining)) = args.split_first() else {
        return Err("no Cargo build/check command was provided".into());
    };
    let (command, trailing) = if is_toolchain_selector(first) {
        remaining
            .split_first()
            .ok_or_else(|| "no Cargo build/check command was provided".to_string())?
    } else {
        (first, remaining)
    };
    let Some(command) = command.to_str() else {
        return Err("the Cargo command is not UTF-8".into());
    };
    if !matches!(command, "build" | "check") {
        return Err("only Cargo's built-in build/check commands are normalized".into());
    }
    if trailing
        .iter()
        .any(|arg| arg.to_str().is_none_or(cargo_arg_may_change_config))
    {
        return Err("Cargo -C/-Z/--config arguments are not normalized".into());
    }
    Ok(())
}

/// rustup reads a `+toolchain` selector only as Cargo's first argument.
fn is_toolchain_selector(arg: &OsStr) -> bool {
    arg.to_str().is_some_and(|arg| arg.starts_with('+'))
}

/// Split Cargo's arguments into a leading `+toolchain` selector, if any, and
/// the rest.
fn split_toolchain_selector(args: &[OsString]) -> (&[OsString], &[OsString]) {
    let selector = args.first().is_some_and(|arg| is_toolchain_selector(arg));
    args.split_at(usize::from(selector))
}

/// Insert `--config` overrides ahead of the Cargo command, after any
/// toolchain selector.
fn cargo_invocation_args(args: &[OsString], overrides: &[String]) -> Vec<OsString> {
    let (selector, rest) = split_toolchain_selector(args);
    let mut invocation = selector.to_vec();
    for value in overrides {
        invocation.push("--config".into());
        invocation.push(value.into());
    }
    invocation.extend_from_slice(rest);
    invocation
}

fn rustflags_config_override(flags: &[String]) -> String {
    let flags = toml::Value::Array(flags.iter().cloned().map(toml::Value::String).collect());
    format!("{ALL_TARGETS_RUSTFLAGS_KEY}={flags}")
}

/// What the launched Cargo receives on top of the caller's arguments.
#[derive(Debug, Default, PartialEq)]
struct CargoOverrides {
    /// `--config` values. Only the launched Cargo reads them.
    config: Vec<String>,
    /// `CARGO_ENCODED_RUSTFLAGS`, for collapsed flags `--config` cannot carry.
    /// Every process Cargo starts inherits it, nested Cargo builds included.
    encoded_rustflags: Option<String>,
}

/// Choose how each applicable plan reaches Cargo. `cargo_version` runs only
/// when a plan applies.
fn cargo_overrides(
    rustflags: Option<&[String]>,
    isolate_build_dir: bool,
    cargo_version: impl FnOnce() -> Option<CargoVersion>,
) -> CargoOverrides {
    let mut overrides = CargoOverrides::default();
    if rustflags.is_none() && !isolate_build_dir {
        return overrides;
    }
    let version = cargo_version();
    if let Some(flags) = rustflags {
        if cargo_at_least(version, CONFIG_ARGUMENT_CARGO) && rustflags_repeat_safely(flags) {
            overrides.config.push(rustflags_config_override(flags));
        } else {
            overrides.encoded_rustflags = Some(flags.join("\x1f"));
        }
    }
    if isolate_build_dir && cargo_at_least(version, BUILD_DIR_CARGO) {
        overrides.config.push(WORKTREE_BUILD_DIR_CONFIG.to_string());
    }
    overrides
}

fn cargo_at_least(version: Option<CargoVersion>, minimum: CargoVersion) -> bool {
    version.is_some_and(|version| version >= minimum)
}

/// Ask the Cargo that will run the build for its version, through the same
/// launcher and toolchain selector.
fn cargo_version(cargo: &Path, cargo_args: &[OsString], cwd: &Path) -> Option<CargoVersion> {
    let (selector, _) = split_toolchain_selector(cargo_args);
    let mut command = Command::new(cargo);
    mark_started_cargo(&mut command, cargo);
    let output = command
        .args(selector)
        .arg("-V")
        .current_dir(cwd)
        .stdin(Stdio::null())
        .stderr(Stdio::null())
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    parse_cargo_version(std::str::from_utf8(&output.stdout).ok()?)
}

/// Read `major.minor` from `cargo -V` output such as
/// `cargo 1.91.0 (ea2d97820 2025-10-10)`.
fn parse_cargo_version(output: &str) -> Option<CargoVersion> {
    let version = output.strip_prefix("cargo ")?.split_whitespace().next()?;
    let mut parts = version.split('.');
    let major = parts.next()?.parse().ok()?;
    let minor = parts.next()?.parse().ok()?;
    Some((major, minor))
}

/// Whether rustc accepts every option in `flags` twice, as Cargo's first
/// target-info probe passes them. Unknown options count as single-use.
fn rustflags_repeat_safely(flags: &[String]) -> bool {
    let mut flags = flags.iter();
    while let Some(flag) = flags.next() {
        match repeatable_rustc_option(flag) {
            Some(true) => {
                // The option's value.
                flags.next();
            }
            Some(false) => {}
            None => return false,
        }
    }
    true
}

/// `Some(true)` for a repeatable option whose value is the next argument,
/// `Some(false)` for one that is complete on its own, `None` otherwise.
fn repeatable_rustc_option(arg: &str) -> Option<bool> {
    if REPEATABLE_RUSTC_FLAGS.contains(&arg) {
        return Some(false);
    }
    if let Some(long) = arg.strip_prefix("--") {
        let name = long.split_once('=').map_or(long, |(name, _)| name);
        return REPEATABLE_RUSTC_LONG_OPTIONS
            .contains(&name)
            .then_some(name.len() == long.len());
    }
    let mut short = arg.strip_prefix('-')?.chars();
    let option = short.next()?;
    REPEATABLE_RUSTC_SHORT_OPTIONS
        .contains(&option)
        .then_some(short.as_str().is_empty())
}

fn worktree_build_dir_isolation_plan(
    cwd: &Path,
    args: &[OsString],
    explicit: Option<&OsStr>,
) -> std::result::Result<Option<BuildDirIsolationPlan>, String> {
    if !worktree_build_dir_isolation_enabled(args, explicit, false) {
        return Ok(None);
    }
    let cargo_home = cargo_home(cwd)?;
    build_dir_isolation_plan_from_sources(cwd, cargo_home)
}

fn build_dir_isolation_plan_from_sources(
    cwd: &Path,
    cargo_home: PathBuf,
) -> std::result::Result<Option<BuildDirIsolationPlan>, String> {
    let candidates = cargo_config_candidates(cwd, &cargo_home);
    let candidate_paths = candidates.iter().map(|(path, _)| path.clone()).collect();
    let mut snapshots = Vec::with_capacity(candidates.len());
    for (path, cargo_home_source) in candidates {
        snapshots.push(read_source(path, cargo_home_source)?);
    }
    if configured_build_dir_in_sources(&snapshots)? {
        return Ok(None);
    }
    Ok(Some(BuildDirIsolationPlan {
        snapshots,
        cwd: cwd.to_path_buf(),
        cargo_home,
        candidate_paths,
    }))
}

fn worktree_build_dir_isolation_enabled(
    args: &[OsString],
    explicit: Option<&OsStr>,
    configured: bool,
) -> bool {
    explicit.is_none() && !configured && supported_cargo_command(args).is_ok()
}

fn cargo_arg_may_change_config(arg: &str) -> bool {
    arg == "--config"
        || arg.starts_with("--config=")
        || arg.starts_with("-C")
        || arg.starts_with("-Z")
}

fn cargo_config_candidates(cwd: &Path, cargo_home: &Path) -> Vec<(PathBuf, bool)> {
    let mut candidates = Vec::new();
    if let Some(path) = selected_config(cargo_home) {
        candidates.push((path, true));
    }

    let mut ancestors: Vec<&Path> = cwd.ancestors().collect();
    ancestors.reverse();
    for ancestor in ancestors {
        let Some(path) = selected_config(&ancestor.join(".cargo")) else {
            continue;
        };
        if !candidates.iter().any(|(candidate, _)| candidate == &path) {
            candidates.push((path, false));
        }
    }
    candidates
}

fn configured_build_dir_in_sources(sources: &[ConfigSource]) -> std::result::Result<bool, String> {
    for source in sources {
        let table = source
            .value
            .as_table()
            .ok_or_else(|| format!("{} is not a TOML table", source.logical_path.display()))?;
        if table.contains_key("include") {
            return Err(format!(
                "{} uses Cargo config include",
                source.logical_path.display()
            ));
        }
        if let Some(build) = table.get("build") {
            let build = build
                .as_table()
                .ok_or_else(|| format!("{}.build is not a table", source.logical_path.display()))?;
            if build.contains_key("build-dir") {
                return Ok(true);
            }
        }
        if let Some(env) = table.get("env") {
            let env = env
                .as_table()
                .ok_or_else(|| format!("{}.env is not a table", source.logical_path.display()))?;
            if env.keys().any(|key| {
                if cfg!(windows) {
                    key.eq_ignore_ascii_case("CARGO_BUILD_BUILD_DIR")
                } else {
                    key == "CARGO_BUILD_BUILD_DIR"
                }
            }) {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

fn cargo_home(cwd: &Path) -> std::result::Result<PathBuf, String> {
    home::cargo_home_with_cwd(cwd)
        .map_err(|error| format!("cannot resolve Cargo's home directory: {error}"))
}

/// Cargo retains the extensionless file for backwards compatibility when both
/// names exist (and emits its own warning).
fn selected_config(config_dir: &Path) -> Option<PathBuf> {
    let legacy = config_dir.join("config");
    if legacy.is_file() {
        return Some(legacy);
    }
    let modern = config_dir.join("config.toml");
    modern.is_file().then_some(modern)
}

fn read_source(path: PathBuf, cargo_home: bool) -> std::result::Result<ConfigSource, String> {
    let canonical_path = path
        .canonicalize()
        .map_err(|error| format!("cannot canonicalize {}: {error}", path.display()))?;
    let bytes =
        std::fs::read(&path).map_err(|error| format!("cannot read {}: {error}", path.display()))?;
    let text = std::str::from_utf8(&bytes)
        .map_err(|error| format!("{} is not UTF-8: {error}", path.display()))?;
    let value = toml::from_str(text)
        .map_err(|error| format!("cannot parse {}: {error}", path.display()))?;
    Ok(ConfigSource {
        logical_path: path,
        canonical_path,
        content_hash: blake3::hash(&bytes),
        value,
        cargo_home,
    })
}

fn source_rustflags(
    value: &toml::Value,
    path: &Path,
) -> std::result::Result<Option<Vec<String>>, String> {
    let table = value
        .as_table()
        .ok_or_else(|| format!("{} is not a TOML table", path.display()))?;
    if table.contains_key("include") {
        return Err(format!("{} uses Cargo config include", path.display()));
    }
    if target_rustflags_present(table) {
        return Err(format!(
            "{} defines target-specific rustflags",
            path.display()
        ));
    }
    if config_env_rustflags_present(table) {
        return Err(format!(
            "{} defines rustflags through [env]",
            path.display()
        ));
    }

    let Some(build) = table.get("build") else {
        return Ok(None);
    };
    let build = build
        .as_table()
        .ok_or_else(|| format!("{}.build is not a table", path.display()))?;
    let Some(rustflags) = build.get("rustflags") else {
        return Ok(None);
    };
    let array = rustflags.as_array().ok_or_else(|| {
        format!(
            "{}.build.rustflags uses string form instead of an argument array",
            path.display()
        )
    })?;
    let mut flags = Vec::with_capacity(array.len());
    for flag in array {
        let Some(flag) = flag.as_str() else {
            return Err(format!(
                "{}.build.rustflags contains a non-string value",
                path.display()
            ));
        };
        if flag.is_empty() || flag.contains(ENCODED_SEPARATOR) {
            return Err(format!(
                "{}.build.rustflags contains an empty argument or Cargo's encoded-argument separator",
                path.display()
            ));
        }
        flags.push(flag.to_string());
    }
    Ok(Some(flags))
}

fn target_rustflags_present(table: &toml::map::Map<String, toml::Value>) -> bool {
    table
        .get("target")
        .and_then(toml::Value::as_table)
        .is_some_and(|targets| {
            targets.values().any(|target| {
                target
                    .as_table()
                    .is_some_and(|target| target.contains_key("rustflags"))
            })
        })
}

fn config_env_rustflags_present(table: &toml::map::Map<String, toml::Value>) -> bool {
    table
        .get("env")
        .and_then(toml::Value::as_table)
        .is_some_and(|env| env.keys().any(|key| rustflags_env_name(key, cfg!(windows))))
}

fn plan_is_current(plan: &NormalizationPlan) -> bool {
    let rescanned: Vec<PathBuf> = cargo_config_candidates(&plan.cwd, &plan.cargo_home)
        .into_iter()
        .map(|(path, _)| path)
        .collect();
    if rescanned != plan.candidate_paths {
        return false;
    }
    revalidate_sources(&plan.snapshots).is_ok()
}

fn build_dir_plan_is_current(plan: &BuildDirIsolationPlan) -> bool {
    let rescanned: Vec<PathBuf> = cargo_config_candidates(&plan.cwd, &plan.cargo_home)
        .into_iter()
        .map(|(path, _)| path)
        .collect();
    rescanned == plan.candidate_paths && revalidate_sources(&plan.snapshots).is_ok()
}

fn revalidate_sources(sources: &[ConfigSource]) -> std::result::Result<(), String> {
    for source in sources {
        let canonical = source.logical_path.canonicalize().map_err(|error| {
            format!(
                "cannot re-canonicalize {}: {error}",
                source.logical_path.display()
            )
        })?;
        let bytes = std::fs::read(&source.logical_path).map_err(|error| {
            format!("cannot re-read {}: {error}", source.logical_path.display())
        })?;
        if canonical != source.canonical_path || blake3::hash(&bytes) != source.content_hash {
            return Err(format!("{} changed", source.logical_path.display()));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn known_protocol(line: &[u8]) -> bool {
        serde_json::from_slice::<serde_json::Value>(line)
            .ok()
            .is_some_and(|value| {
                matches!(
                    value["reason"].as_str(),
                    Some("compiler-artifact" | "build-finished" | "compiler-message")
                )
            })
    }

    #[test]
    fn cargo_command_label_names_the_subcommand() {
        let label = |args: &[&str]| cargo_command_label(args.iter().map(OsStr::new));
        assert_eq!(label(&["run", "--features", "x"]), "cargo run");
        assert_eq!(
            label(&["+nightly", "-q", "test", "--", "--nocapture"]),
            "cargo test"
        );
        assert_eq!(label(&["--version"]), "cargo");
        assert_eq!(
            label(&[
                "--config",
                "build.build-dir=\"{workspace-root}/target\"",
                "build"
            ]),
            "cargo build"
        );
    }

    #[test]
    fn cargo_stdout_reader_retries_interruption_and_reports_other_errors() {
        struct FaultingReader {
            next: usize,
            bytes: Vec<u8>,
        }
        impl io::Read for FaultingReader {
            fn read(&mut self, _: &mut [u8]) -> io::Result<usize> {
                unreachable!("the reader uses BufRead")
            }
        }
        impl BufRead for FaultingReader {
            fn fill_buf(&mut self) -> io::Result<&[u8]> {
                let phase = self.next;
                self.next += 1;
                match phase {
                    0 => Err(io::ErrorKind::Interrupted.into()),
                    1 => Ok(&self.bytes),
                    2 => Err(io::ErrorKind::BrokenPipe.into()),
                    _ => Ok(&[]),
                }
            }
            fn consume(&mut self, amount: usize) {
                assert_eq!(amount, self.bytes.len());
            }
        }
        let (sender, messages) = mpsc::sync_channel(8);
        read_cargo_stdout(
            FaultingReader {
                next: 0,
                bytes: b"one\n".to_vec(),
            },
            sender,
        );
        assert!(
            matches!(messages.try_recv().unwrap(), CargoStdoutMessage::Bytes(bytes) if bytes == b"one\n")
        );
        assert!(
            matches!(messages.try_recv().unwrap(), CargoStdoutMessage::Failed(error) if error.kind() == io::ErrorKind::BrokenPipe)
        );
        assert!(matches!(
            messages.try_recv(),
            Err(mpsc::TryRecvError::Disconnected)
        ));
        let (sender, messages) = mpsc::sync_channel(8);
        read_cargo_stdout(io::Cursor::new(b"complete\n"), sender);
        assert!(
            matches!(messages.try_recv().unwrap(), CargoStdoutMessage::Bytes(bytes) if bytes == b"complete\n")
        );
        assert!(matches!(
            messages.try_recv().unwrap(),
            CargoStdoutMessage::Finished
        ));
    }

    #[test]
    fn cargo_stdout_drain_waits_until_two_seconds_after_exit() {
        let at = Instant::now();
        assert!(!cargo_drain_expired(None, at + Duration::from_secs(10)));
        assert!(!cargo_drain_expired(Some(at), at));
        assert!(!cargo_drain_expired(
            Some(at),
            at + Duration::from_secs(2) - Duration::from_nanos(1)
        ));
        assert!(cargo_drain_expired(Some(at), at + Duration::from_secs(2)));
        assert!(cargo_drain_expired(
            Some(at),
            at + Duration::from_secs(2) + Duration::from_nanos(1)
        ));
    }

    #[test]
    fn cargo_human_output_replays_rendered_diagnostics_on_stderr() {
        const CHILD: &str = "KACHE_TEST_RENDERED_DIAGNOSTIC_CHILD";
        if std::env::var_os(CHILD).is_some() {
            let mut output = CargoOutput::new(true);
            let mut forwarded = Vec::new();
            output.push(
                b"{\"reason\":\"compiler-message\",\"message\":{\"rendered\":\"error: receipt diagnostic\\n\"}}\n",
                &mut known_protocol,
                &mut forwarded,
            ).unwrap();
            assert!(forwarded.is_empty());
            return;
        }
        let child = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "cargo_proxy::tests::cargo_human_output_replays_rendered_diagnostics_on_stderr",
                "--nocapture",
            ])
            .env(CHILD, "1")
            .output()
            .unwrap();
        assert!(
            child.status.success(),
            "{}",
            String::from_utf8_lossy(&child.stdout)
        );
        assert_eq!(child.stderr, b"error: receipt diagnostic\n");
    }

    #[test]
    fn cargo_stdout_explicit_json_remains_byte_identical_across_chunk_boundaries() {
        let original = b"{\"reason\":\"compiler-artifact\",\"filenames\":[\"a.rlib\"]}\r\nplain stdout\n{\"reason\":\"build-finished\",\"success\":true}\nunterminated\xff";
        let mut output = CargoOutput::new(false);
        let mut forwarded = Vec::new();
        let mut observed = Vec::new();
        let mut observe = |line: &[u8]| {
            observed.push(line.to_vec());
            known_protocol(line)
        };
        for chunk in original.chunks(7) {
            output.push(chunk, &mut observe, &mut forwarded).unwrap();
        }
        output.finish(&mut observe, &mut forwarded).unwrap();
        assert_eq!(forwarded, original);
        assert_eq!(observed.len(), 4);
        assert_eq!(observed.last().unwrap(), b"unterminated\xff");
        assert!(output.line.is_empty());
    }

    #[test]
    fn cargo_stdout_injected_human_mode_suppresses_only_recognized_protocol() {
        let original = b"ordinary stdout\n{\"reason\":\"compiler-artifact\"}\n{\"reason\":\"future-reason\"}\n{\"reason\":\"compiler-message\",\"message\":{\"rendered\":null}}\n{\"reason\":\"build-finished\"}";
        let mut output = CargoOutput::new(true);
        let mut forwarded = Vec::new();
        let mut observed = Vec::new();
        let mut observe = |line: &[u8]| {
            observed.push(line.to_vec());
            known_protocol(line)
        };
        for chunk in original.chunks(3) {
            output.push(chunk, &mut observe, &mut forwarded).unwrap();
        }
        output.finish(&mut observe, &mut forwarded).unwrap();
        assert_eq!(
            forwarded,
            b"ordinary stdout\n{\"reason\":\"future-reason\"}\n"
        );
        assert_eq!(observed.len(), 5);
        assert!(output.line.is_empty());
    }

    #[test]
    fn cargo_stdout_oversized_line_is_bounded_forwarded_and_invalidates_once() {
        for (human, length) in [false, true]
            .into_iter()
            .flat_map(|human| [4_194_335, 4_202_527].map(|length| (human, length)))
        {
            let mut original = vec![b'x'; length];
            original.extend_from_slice(b"\n{\"reason\":\"build-finished\"}\n");
            let mut output = CargoOutput::new(human);
            let mut forwarded = Vec::new();
            let mut invalidations = 0;
            let mut protocol_lines = 0;
            let mut observe = |line: &[u8]| {
                if line == INVALID_CARGO_STREAM {
                    invalidations += 1;
                    return false;
                }
                protocol_lines += 1;
                known_protocol(line)
            };
            for chunk in original.chunks(8192) {
                output.push(chunk, &mut observe, &mut forwarded).unwrap();
                assert!(output.line.len() <= 4_194_304);
            }
            output.finish(&mut observe, &mut forwarded).unwrap();
            assert_eq!(invalidations, 1);
            assert_eq!(protocol_lines, 1);
            assert!(!output.oversized);
            if human {
                assert_eq!(forwarded, original[..length + 1]);
            } else {
                assert_eq!(forwarded, original);
            }
        }
    }

    #[test]
    fn cargo_stdout_exact_line_limit_is_observed_without_invalidation() {
        let mut bytes = vec![b'x'; 4_194_303];
        bytes.push(b'\n');
        let mut output = CargoOutput::new(false);
        let mut forwarded = Vec::new();
        let mut observations = 0;
        let mut observe = |line: &[u8]| {
            assert_ne!(line, INVALID_CARGO_STREAM);
            assert_eq!(line.len(), 4_194_304);
            observations += 1;
            false
        };
        for chunk in bytes.chunks(8192) {
            output.push(chunk, &mut observe, &mut forwarded).unwrap();
        }
        output.finish(&mut observe, &mut forwarded).unwrap();
        assert_eq!(forwarded, bytes);
        assert_eq!(observations, 1);
    }

    #[test]
    fn cargo_stdout_write_failure_still_observes_and_drains_remaining_records() {
        struct BrokenOutput;
        impl io::Write for BrokenOutput {
            fn write(&mut self, _: &[u8]) -> io::Result<usize> {
                Err(io::Error::new(io::ErrorKind::BrokenPipe, "closed"))
            }
            fn flush(&mut self) -> io::Result<()> {
                Ok(())
            }
        }
        let mut output = CargoOutput::new(false);
        let mut observed = Vec::new();
        let mut observe = |line: &[u8]| {
            observed.push(line.to_vec());
            false
        };
        assert!(
            output
                .push(b"one\ntwo\n", &mut observe, &mut BrokenOutput)
                .is_err()
        );
        assert!(output.line.is_empty());
        assert!(output.finish(&mut observe, &mut BrokenOutput).is_ok());
        assert_eq!(observed, vec![b"one\n".to_vec(), b"two\n".to_vec()]);
    }

    #[test]
    fn cargo_rendered_diagnostic_requires_compiler_message_and_string() {
        assert_eq!(
            rendered_cargo_diagnostic(
                br#"{"reason":"compiler-message","message":{"rendered":"error: failure\n"}}"#
            )
            .as_deref(),
            Some("error: failure\n")
        );
        for bytes in [
            br#"{"reason":"compiler-message","message":{"rendered":null}}"#.as_slice(),
            br#"{"reason":"compiler-artifact","message":{"rendered":"do not render"}}"#.as_slice(),
            b"plain stdout".as_slice(),
            b"\xff".as_slice(),
        ] {
            assert!(rendered_cargo_diagnostic(bytes).is_none());
        }
    }

    #[test]
    fn command_gate_accepts_only_unambiguous_builtin_build_and_check() {
        for args in [
            vec!["build"],
            vec!["build", "--workspace"],
            vec!["+nightly", "check", "--locked"],
            vec!["check", "--color=always"],
        ] {
            let args: Vec<OsString> = args.into_iter().map(OsString::from).collect();
            assert!(supported_cargo_command(&args).is_ok(), "args: {args:?}");
        }

        for args in [
            vec!["install", "demo"],
            vec!["xtask", "check"],
            vec!["b"],
            vec!["--locked", "check"],
            vec!["-C", "elsewhere", "check"],
            vec!["check", "--config", "build.rustflags=[]"],
            vec!["check", "--config=build.rustflags=[]"],
            vec!["check", "-Celsewhere"],
            vec!["-Zunstable-options", "check"],
            vec!["check", "-Zunstable-options"],
        ] {
            let args: Vec<OsString> = args.into_iter().map(OsString::from).collect();
            assert!(supported_cargo_command(&args).is_err(), "args: {args:?}");
        }
        assert!(supported_cargo_command(&[]).is_err());

        #[cfg(unix)]
        {
            use std::os::unix::ffi::OsStringExt;
            let args = [OsString::from("check"), OsString::from_vec(vec![0x80])];
            assert!(supported_cargo_command(&args).is_err());
        }
    }

    #[test]
    fn config_overrides_follow_a_toolchain_selector() {
        let args = |args: &[&str]| args.iter().map(OsString::from).collect::<Vec<_>>();
        let overrides = ["a=1".to_string(), "b=2".to_string()];
        assert_eq!(
            cargo_invocation_args(&args(&["build", "--quiet"]), &overrides),
            args(&["--config", "a=1", "--config", "b=2", "build", "--quiet"])
        );
        assert_eq!(
            cargo_invocation_args(&args(&["+nightly", "check"]), &overrides),
            args(&["+nightly", "--config", "a=1", "--config", "b=2", "check"])
        );
        assert_eq!(
            cargo_invocation_args(&args(&["+nightly", "check"]), &[]),
            args(&["+nightly", "check"])
        );
        assert_eq!(
            cargo_invocation_args(&[], &overrides[..1]),
            args(&["--config", "a=1"])
        );
    }

    #[test]
    fn config_overrides_name_the_intended_cargo_keys() {
        let flags = [
            "--cfg".to_string(),
            "a=\"b c\"".to_string(),
            "-Clink-arg=C:\\lib".to_string(),
        ];
        let parsed: toml::Table = toml::from_str(&rustflags_config_override(&flags)).unwrap();
        assert_eq!(parsed.len(), 1, "one dotted key: {parsed:?}");
        let expected: Vec<toml::Value> = flags.iter().cloned().map(toml::Value::String).collect();
        assert_eq!(
            parsed["target"]["cfg(all())"]["rustflags"],
            toml::Value::Array(expected)
        );

        let parsed: toml::Table = toml::from_str(WORKTREE_BUILD_DIR_CONFIG).unwrap();
        assert_eq!(
            parsed["build"]["build-dir"].as_str(),
            Some("{workspace-root}/target")
        );
    }

    #[test]
    fn overrides_follow_the_cargo_version_and_the_collapsed_flags() {
        let safe = ["--cfg".to_string(), "kache".to_string()];
        let single_use = ["--sysroot".to_string(), "/opt/sysroot".to_string()];
        let rustflags_config = || rustflags_config_override(&safe);
        let build_dir = || WORKTREE_BUILD_DIR_CONFIG.to_string();
        let modern = || Some((1, 91));
        let expect = |config: Vec<String>, encoded: Option<&str>| CargoOverrides {
            config,
            encoded_rustflags: encoded.map(str::to_string),
        };

        assert_eq!(
            cargo_overrides(None, false, || unreachable!("probed Cargo without a plan")),
            expect(Vec::new(), None)
        );
        assert_eq!(
            cargo_overrides(Some(&safe), false, modern),
            expect(vec![rustflags_config()], None)
        );
        assert_eq!(
            cargo_overrides(None, true, modern),
            expect(vec![build_dir()], None)
        );
        assert_eq!(
            cargo_overrides(Some(&safe), true, modern),
            expect(vec![rustflags_config(), build_dir()], None)
        );
        // Cargo's first target-info probe would pass `--sysroot` twice.
        assert_eq!(
            cargo_overrides(Some(&single_use), true, modern),
            expect(vec![build_dir()], Some("--sysroot\x1f/opt/sysroot"))
        );
        // Cargo 1.62 rejects `--config`, and 1.90 has no build-dir.
        assert_eq!(
            cargo_overrides(Some(&safe), true, || Some((1, 62))),
            expect(Vec::new(), Some("--cfg\x1fkache"))
        );
        assert_eq!(
            cargo_overrides(Some(&safe), true, || Some((1, 90))),
            expect(vec![rustflags_config()], None)
        );
        assert_eq!(
            cargo_overrides(Some(&safe), true, || None),
            expect(Vec::new(), Some("--cfg\x1fkache"))
        );
    }

    #[test]
    fn cargo_version_thresholds_include_the_first_supporting_release() {
        assert!(cargo_at_least(Some((1, 63)), CONFIG_ARGUMENT_CARGO));
        assert!(!cargo_at_least(Some((1, 62)), CONFIG_ARGUMENT_CARGO));
        assert!(cargo_at_least(Some((1, 91)), BUILD_DIR_CARGO));
        assert!(!cargo_at_least(Some((1, 90)), BUILD_DIR_CARGO));
        assert!(cargo_at_least(Some((2, 0)), BUILD_DIR_CARGO));
        assert!(!cargo_at_least(None, (0, 0)));
    }

    #[test]
    fn cargo_version_output_yields_major_and_minor() {
        assert_eq!(
            parse_cargo_version("cargo 1.98.0 (797e8a9bc 2026-08-05)\n"),
            Some((1, 98))
        );
        assert_eq!(
            parse_cargo_version("cargo 1.93.0-nightly (1d8c8b5f7 2025-11-20)\n"),
            Some((1, 93))
        );
        assert_eq!(parse_cargo_version("cargo 2.3"), Some((2, 3)));
        for output in [
            "",
            "rustup 1.28.2",
            "cargo unknown",
            "cargo 1",
            "cargo 1.x.0",
        ] {
            assert_eq!(parse_cargo_version(output), None, "output: {output:?}");
        }
    }

    #[test]
    fn only_options_rustc_accepts_twice_repeat_safely() {
        let flags = |flags: &[&str]| {
            flags
                .iter()
                .map(|flag| flag.to_string())
                .collect::<Vec<_>>()
        };
        for safe in [
            &[
                "--cfg",
                "kache",
                "--cfg=other",
                "-C",
                "opt-level=2",
                "-Ctarget-cpu=native",
            ][..],
            &[
                "-O",
                "-g",
                "-D",
                "warnings",
                "-Wunused",
                "--remap-path-prefix",
                "/a=/b",
            ],
            &[
                "-L",
                "native=/lib",
                "-lfoo",
                "-Z",
                "share-generics",
                "--check-cfg",
                "cfg(a)",
            ],
            &[],
        ] {
            assert!(rustflags_repeat_safely(&flags(safe)), "flags: {safe:?}");
        }
        for single_use in [
            &["--sysroot", "/opt/sysroot"][..],
            &["--cfg", "kache", "--color=never"],
            &["--target", "x86_64-unknown-linux-gnu"],
            &["-o", "out"],
            &["stray"],
        ] {
            assert!(
                !rustflags_repeat_safely(&flags(single_use)),
                "flags: {single_use:?}"
            );
        }
    }

    #[test]
    fn repeatable_options_know_whether_the_next_argument_is_their_value() {
        for (arg, expected) in [
            ("-O", Some(false)),
            ("-g", Some(false)),
            ("--cfg", Some(true)),
            ("--cfg=kache", Some(false)),
            ("--codegen=opt-level=2", Some(false)),
            ("-C", Some(true)),
            ("-Copt-level=2", Some(false)),
            ("--sysroot", None),
            ("--sysroot=/opt", None),
            ("-Ofast", None),
            ("-o", None),
            ("-", None),
            ("--", None),
            ("value", None),
        ] {
            assert_eq!(repeatable_rustc_option(arg), expected, "arg: {arg}");
        }
    }

    #[test]
    fn worktree_build_dir_is_scoped_and_respects_explicit_env() {
        let build = [OsString::from("build")];
        let check = [OsString::from("check"), OsString::from("--workspace")];
        let install = [OsString::from("install"), OsString::from("demo")];

        assert!(worktree_build_dir_isolation_enabled(&build, None, false));
        assert!(worktree_build_dir_isolation_enabled(&check, None, false));
        assert!(!worktree_build_dir_isolation_enabled(
            &build,
            Some(OsStr::new("/explicit/build-dir")),
            false,
        ));
        assert!(!worktree_build_dir_isolation_enabled(&build, None, true,));
        assert!(!worktree_build_dir_isolation_enabled(&install, None, false,));
    }

    #[test]
    fn configured_build_dir_policy_is_never_overridden() {
        let dir = tempfile::tempdir().unwrap();
        let cargo_home = dir.path().join("cargo-home");
        let cwd = dir.path().join("project");
        let config_dir = cwd.join(".cargo");
        std::fs::create_dir_all(&cargo_home).unwrap();
        std::fs::create_dir_all(&config_dir).unwrap();

        assert!(
            build_dir_isolation_plan_from_sources(&cwd, cargo_home.clone())
                .unwrap()
                .is_some()
        );
        std::fs::write(
            config_dir.join("config.toml"),
            "[build]\nbuild-dir = \"custom-build\"\n",
        )
        .unwrap();
        assert!(
            build_dir_isolation_plan_from_sources(&cwd, cargo_home.clone())
                .unwrap()
                .is_none()
        );

        std::fs::write(
            config_dir.join("config.toml"),
            "[env]\nCARGO_BUILD_BUILD_DIR = \"custom-build\"\n",
        )
        .unwrap();
        assert!(
            build_dir_isolation_plan_from_sources(&cwd, cargo_home.clone())
                .unwrap()
                .is_none()
        );

        std::fs::write(config_dir.join("config.toml"), "include = \"other.toml\"\n").unwrap();
        assert!(build_dir_isolation_plan_from_sources(&cwd, cargo_home).is_err());
    }

    #[test]
    fn build_dir_plan_revalidation_detects_content_and_candidate_changes() {
        let dir = tempfile::tempdir().unwrap();
        let cargo_home = dir.path().join("cargo-home");
        let root = dir.path().join("root");
        let cwd = root.join("project");
        let project_config_dir = cwd.join(".cargo");
        std::fs::create_dir_all(&cargo_home).unwrap();
        std::fs::create_dir_all(&project_config_dir).unwrap();
        let project_config = project_config_dir.join("config.toml");
        std::fs::write(&project_config, "[net]\noffline = true\n").unwrap();

        let content_plan = build_dir_isolation_plan_from_sources(&cwd, cargo_home.clone())
            .unwrap()
            .unwrap();
        assert!(build_dir_plan_is_current(&content_plan));
        std::fs::write(&project_config, "[net]\noffline = false\n").unwrap();
        assert!(
            !build_dir_plan_is_current(&content_plan),
            "changed content with the same candidate set must invalidate the plan"
        );

        let candidate_plan = build_dir_isolation_plan_from_sources(&cwd, cargo_home.clone())
            .unwrap()
            .unwrap();
        let ancestor_config_dir = root.join(".cargo");
        std::fs::create_dir_all(&ancestor_config_dir).unwrap();
        std::fs::write(
            ancestor_config_dir.join("config.toml"),
            "[net]\ngit-fetch-with-cli = true\n",
        )
        .unwrap();
        assert!(
            !build_dir_plan_is_current(&candidate_plan),
            "a new config candidate with unchanged snapshots must invalidate the plan"
        );
    }

    #[test]
    fn only_config_affecting_cargo_arguments_are_ambiguous() {
        for arg in [
            "--config",
            "--config=build.rustflags=[]",
            "-C",
            "-Celsewhere",
            "-Zunstable-options",
        ] {
            assert!(cargo_arg_may_change_config(arg), "arg: {arg}");
        }
        for arg in ["--color=always", "--target", "--locked"] {
            assert!(!cargo_arg_may_change_config(arg), "arg: {arg}");
        }
    }

    #[test]
    fn windows_rustflags_environment_names_are_case_insensitive() {
        assert!(rustflags_env_name("RUSTFLAGS", false));
        assert!(!rustflags_env_name("rustflags", false));
        assert!(rustflags_env_name("rustflags", true));
        assert!(rustflags_env_name(
            "cargo_target_x86_64_unknown_linux_gnu_rustflags",
            true
        ));
        assert!(!rustflags_env_name("CARGO_BUILD_TARGET", false));
        assert!(!rustflags_env_name("MY_RUSTFLAGS", false));
        assert!(!rustflags_env_name("CARGO_RUSTFLAGS_EXTRA", false));
    }

    #[test]
    fn source_flags_preserve_repeated_additive_arguments() {
        let value: toml::Value =
            toml::from_str("[build]\nrustflags = [\"-Clink-arg=-lfoo\", \"-Clink-arg=-lfoo\"]\n")
                .unwrap();
        assert_eq!(
            source_rustflags(&value, Path::new("config.toml")).unwrap(),
            Some(vec!["-Clink-arg=-lfoo".into(), "-Clink-arg=-lfoo".into()])
        );
    }

    #[test]
    fn only_non_home_sources_with_the_same_identity_are_aliases() {
        let canonical = PathBuf::from("/physical/config.toml");
        let mut source = ConfigSource {
            logical_path: PathBuf::from("/cargo-home/config.toml"),
            canonical_path: canonical.clone(),
            content_hash: blake3::hash(b""),
            value: toml::Value::Table(Default::default()),
            cargo_home: true,
        };
        assert!(!is_cargo_home_alias(&source, &canonical));

        source.cargo_home = false;
        assert!(is_cargo_home_alias(&source, &canonical));

        source.canonical_path = PathBuf::from("/different/config.toml");
        assert!(!is_cargo_home_alias(&source, &canonical));
    }

    #[test]
    fn target_include_string_empty_and_env_forms_fail_closed() {
        for source in [
            "include = \"other.toml\"\n[build]\nrustflags = [\"-Copt-level=2\"]\n",
            "[build]\nrustflags = \"-Copt-level=2\"\n",
            "[build]\nrustflags = [\"\"]\n",
            "[build]\nrustflags = [\"\\u001f\"]\n",
            "[target.x86_64-unknown-linux-gnu]\nrustflags = [\"-Copt-level=2\"]\n",
            "[env]\nRUSTFLAGS = \"-Copt-level=2\"\n",
        ] {
            let value: toml::Value = toml::from_str(source).unwrap();
            assert!(source_rustflags(&value, Path::new("config.toml")).is_err());
        }
    }

    #[test]
    fn extensionless_config_has_cargo_compatibility_precedence() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("config.toml"), "[build]\n").unwrap();
        std::fs::write(dir.path().join("config"), "[build]\n").unwrap();
        assert_eq!(selected_config(dir.path()), Some(dir.path().join("config")));
    }

    #[cfg(unix)]
    #[test]
    fn cargo_resolution_preserves_a_launcher_symlink() {
        let dir = tempfile::tempdir().unwrap();
        let target = dir.path().join("rustup");
        let launcher = dir.path().join("cargo");
        std::fs::write(&target, "#!/bin/sh\nexit 0\n").unwrap();
        std::os::unix::fs::symlink(&target, &launcher).unwrap();

        assert_eq!(
            resolve_cargo_program(launcher.as_os_str(), dir.path()).unwrap(),
            launcher
        );
    }

    /// Create `<cargo_home>/bin/cargo` and return its path.
    fn cargo_in(cargo_home: &Path) -> PathBuf {
        let cargo = cargo_home
            .join("bin")
            .join(format!("cargo{}", std::env::consts::EXE_SUFFIX));
        std::fs::create_dir_all(cargo.parent().unwrap()).unwrap();
        std::fs::write(&cargo, "").unwrap();
        cargo
    }

    fn candidate(env: &CargoEnvironment, route: CargoRoute) -> Option<OsString> {
        real_cargo_candidate(env, route, |_| false, || Some("/path/cargo".into()))
    }

    #[test]
    fn kache_real_cargo_names_the_cargo_on_every_route() {
        let dir = tempfile::tempdir().unwrap();
        cargo_in(dir.path());
        let env = CargoEnvironment {
            real_cargo: Some("chosen".into()),
            cargo: Some("/toolchain/cargo".into()),
            cargo_home: Some(dir.path().to_path_buf()),
            home: None,
        };
        for route in [
            CargoRoute::Command,
            CargoRoute::Shim,
            CargoRoute::WithoutPath,
        ] {
            assert_eq!(candidate(&env, route), Some("chosen".into()), "{route:?}");
        }
    }

    #[test]
    fn cargo_from_cargo_comes_before_cargo_home_except_in_the_shim() {
        let dir = tempfile::tempdir().unwrap();
        let home_cargo = cargo_in(dir.path());
        let env = CargoEnvironment {
            cargo: Some("/toolchain/cargo".into()),
            cargo_home: Some(dir.path().to_path_buf()),
            ..CargoEnvironment::default()
        };
        assert_eq!(
            candidate(&env, CargoRoute::Command),
            Some("/toolchain/cargo".into())
        );
        assert_eq!(
            candidate(&env, CargoRoute::WithoutPath),
            Some("/toolchain/cargo".into())
        );
        assert_eq!(
            candidate(&env, CargoRoute::Shim),
            Some(home_cargo.into_os_string())
        );
    }

    #[test]
    fn a_relative_or_kache_cargo_variable_is_passed_over() {
        let dir = tempfile::tempdir().unwrap();
        let home_cargo = cargo_in(dir.path());
        let relative = CargoEnvironment {
            cargo: Some("cargo".into()),
            cargo_home: Some(dir.path().to_path_buf()),
            ..CargoEnvironment::default()
        };
        assert_eq!(
            candidate(&relative, CargoRoute::Command),
            Some(home_cargo.clone().into_os_string())
        );

        let kache = CargoEnvironment {
            cargo: Some("/kache".into()),
            cargo_home: Some(dir.path().to_path_buf()),
            ..CargoEnvironment::default()
        };
        let found = real_cargo_candidate(
            &kache,
            CargoRoute::Command,
            |path| path == Path::new("/kache"),
            || None,
        );
        assert_eq!(found, Some(home_cargo.into_os_string()));
    }

    #[test]
    fn cargo_home_wins_over_home() {
        let dir = tempfile::tempdir().unwrap();
        let home_cargo = cargo_in(&dir.path().join("cargo-home"));
        cargo_in(&dir.path().join("user/.cargo"));
        let env = CargoEnvironment {
            cargo_home: Some(dir.path().join("cargo-home")),
            home: Some(dir.path().join("user")),
            ..CargoEnvironment::default()
        };
        assert_eq!(
            candidate(&env, CargoRoute::Shim),
            Some(home_cargo.into_os_string())
        );
    }

    #[test]
    fn the_home_cargo_directory_is_used_without_cargo_home() {
        let dir = tempfile::tempdir().unwrap();
        let user_cargo = cargo_in(&dir.path().join(".cargo"));
        let env = CargoEnvironment {
            home: Some(dir.path().to_path_buf()),
            ..CargoEnvironment::default()
        };
        assert_eq!(
            candidate(&env, CargoRoute::Shim),
            Some(user_cargo.into_os_string())
        );
    }

    #[test]
    fn cargo_home_without_cargo_falls_through_to_path() {
        let dir = tempfile::tempdir().unwrap();
        // `~/.cargo` is not consulted once CARGO_HOME is set, as Cargo would not.
        cargo_in(&dir.path().join(".cargo"));
        let env = CargoEnvironment {
            cargo_home: Some(dir.path().join("empty")),
            home: Some(dir.path().to_path_buf()),
            ..CargoEnvironment::default()
        };
        assert_eq!(
            candidate(&env, CargoRoute::Command),
            Some("/path/cargo".into())
        );
    }

    #[test]
    fn a_kache_cargo_home_cargo_falls_through_to_path() {
        let dir = tempfile::tempdir().unwrap();
        let home_cargo = cargo_in(dir.path());
        let env = CargoEnvironment {
            cargo_home: Some(dir.path().to_path_buf()),
            ..CargoEnvironment::default()
        };
        let found = real_cargo_candidate(
            &env,
            CargoRoute::Shim,
            |path| path == home_cargo,
            || Some("/path/cargo".into()),
        );
        assert_eq!(found, Some("/path/cargo".into()));
    }

    #[test]
    fn path_is_searched_last_and_never_without_path() {
        let env = CargoEnvironment {
            cargo_home: Some("/no/such/cargo-home".into()),
            ..CargoEnvironment::default()
        };
        assert_eq!(
            candidate(&env, CargoRoute::Shim),
            Some("/path/cargo".into())
        );
        assert_eq!(
            candidate(&env, CargoRoute::Command),
            Some("/path/cargo".into())
        );
        let searched = std::cell::Cell::new(false);
        let found = real_cargo_candidate(
            &env,
            CargoRoute::WithoutPath,
            |_| false,
            || {
                searched.set(true);
                Some("/path/cargo".into())
            },
        );
        assert_eq!(found, None);
        assert!(!searched.get(), "PATH was searched");
    }

    #[cfg(unix)]
    #[test]
    fn kache_identity_follows_links_and_needs_a_kache() {
        let dir = tempfile::tempdir().unwrap();
        let kache = dir.path().join("kache");
        let other = dir.path().join("other");
        std::fs::write(&kache, "").unwrap();
        std::fs::write(&other, "").unwrap();
        std::os::unix::fs::symlink(&kache, dir.path().join("cargo")).unwrap();
        let identity = kache.canonicalize().unwrap();

        assert!(is_kache(&dir.path().join("cargo"), Some(&identity)));
        assert!(!is_kache(&other, Some(&identity)));
        assert!(!is_kache(&dir.path().join("missing"), None));
    }

    #[test]
    fn a_proxy_without_the_marker_is_the_first() {
        let level = ProxyLevel::from_env(None, Some(OsStr::new("stale")));
        assert_eq!(level, ProxyLevel::default());
        assert!(!level.reentered());
    }

    #[test]
    fn the_marker_carries_depth_and_chain() {
        let level = ProxyLevel::from_env(Some(OsStr::new("2")), Some(OsStr::new("a\x1fb")));
        assert_eq!(level.depth, 2);
        assert_eq!(level.chain, ["a", "b"]);
        assert!(level.reentered());
    }

    #[test]
    fn an_unreadable_marker_still_means_reentry() {
        let level = ProxyLevel::from_env(Some(OsStr::new("x")), None);
        assert_eq!(level.depth, 1);
        assert!(level.chain.is_empty());
    }

    fn marker(command: &Command, name: &str) -> Option<String> {
        command
            .get_envs()
            .find(|(key, _)| *key == name)
            .and_then(|(_, value)| value)
            .map(|value| value.to_string_lossy().into_owned())
    }

    #[test]
    fn a_started_cargo_is_one_level_deeper() {
        let mut first = Command::new("cargo");
        ProxyLevel::default().mark(&mut first, "/bin/kache", Path::new("/c"));
        assert_eq!(marker(&first, PROXY_DEPTH_ENV).as_deref(), Some("1"));
        assert_eq!(
            marker(&first, PROXY_CHAIN_ENV).as_deref(),
            Some("/bin/kache ran /c")
        );

        let level = ProxyLevel {
            depth: 2,
            chain: vec!["a".into(), "b".into()],
        };
        let mut nested = Command::new("cargo");
        level.mark(&mut nested, "/bin/kache", Path::new("/c"));
        assert_eq!(marker(&nested, PROXY_DEPTH_ENV).as_deref(), Some("3"));
        assert_eq!(
            marker(&nested, PROXY_CHAIN_ENV).as_deref(),
            Some("a\x1fb\x1f/bin/kache ran /c")
        );
    }

    #[test]
    fn depth_past_the_bound_is_refused_with_the_chain() {
        let at_bound = ProxyLevel {
            depth: 2,
            chain: vec!["a ran w".into(), "b ran w".into()],
        };
        assert!(at_bound.check("k").is_ok());

        let past = ProxyLevel {
            depth: 3,
            chain: vec!["a ran w".into(), "b ran w".into(), "c ran w".into()],
        };
        let error = past.check("/bin/kache").unwrap_err().to_string();
        assert!(error.contains("KACHE_CARGO_PROXY_DEPTH=3"), "{error}");
        assert!(
            error.contains("\n  a ran w\n  b ran w\n  c ran w\n  /bin/kache refused"),
            "{error}"
        );
    }

    #[test]
    fn bare_cargo_program_resolves_through_path() {
        let resolved = resolve_cargo_program(OsStr::new("cargo"), Path::new(".")).unwrap();
        assert!(resolved.is_absolute(), "resolved Cargo path: {resolved:?}");
        assert!(resolved.is_file(), "resolved Cargo path: {resolved:?}");
    }

    #[test]
    fn revalidation_rejects_changed_config_content() {
        let dir = tempfile::tempdir().unwrap();
        let config = dir.path().join("config.toml");
        std::fs::write(&config, "[build]\nrustflags = [\"--cfg=a\"]\n").unwrap();
        let source = read_source(config.clone(), true).unwrap();
        std::fs::write(&config, "[build]\nrustflags = [\"--cfg=b\"]\n").unwrap();
        assert!(revalidate_sources(&[source]).is_err());
    }

    #[test]
    fn revalidation_rejects_a_changed_candidate_set() {
        let dir = tempfile::tempdir().unwrap();
        let cargo_home = dir.path().join("home/.cargo");
        let cwd = dir.path().join("work/project");
        std::fs::create_dir_all(&cargo_home).unwrap();
        std::fs::create_dir_all(&cwd).unwrap();
        let home_config = cargo_home.join("config.toml");
        std::fs::write(&home_config, "[build]\nrustflags = [\"--cfg=home\"]\n").unwrap();
        let candidate_paths = cargo_config_candidates(&cwd, &cargo_home)
            .into_iter()
            .map(|(path, _)| path)
            .collect();
        let plan = NormalizationPlan {
            rustflags: vec!["--cfg=home".into()],
            snapshots: vec![read_source(home_config, true).unwrap()],
            cwd: cwd.clone(),
            cargo_home,
            candidate_paths,
            duplicate_paths: Vec::new(),
        };
        assert!(plan_is_current(&plan));

        std::fs::create_dir_all(dir.path().join("work/.cargo")).unwrap();
        std::fs::write(
            dir.path().join("work/.cargo/config.toml"),
            "[build]\nrustflags = [\"--cfg=project\"]\n",
        )
        .unwrap();
        assert!(!plan_is_current(&plan));
    }

    #[cfg(unix)]
    #[test]
    fn revalidation_rejects_retargeted_symlink_even_with_same_content() {
        let dir = tempfile::tempdir().unwrap();
        let first = dir.path().join("first.toml");
        let second = dir.path().join("second.toml");
        let alias = dir.path().join("config.toml");
        let content = "[build]\nrustflags = [\"--cfg=same\"]\n";
        std::fs::write(&first, content).unwrap();
        std::fs::write(&second, content).unwrap();
        std::os::unix::fs::symlink(&first, &alias).unwrap();
        let source = read_source(alias.clone(), false).unwrap();
        std::fs::remove_file(&alias).unwrap();
        std::os::unix::fs::symlink(&second, &alias).unwrap();
        assert!(revalidate_sources(&[source]).is_err());
    }
}
