STATUS: DONE
COMMIT: none
CHANGED: 19 files
OPEN: 2 unresolved items
BLOCKERS: none
CONFIRMED: 2
LIMITS: Production text fully reviewed; dedicated and inline test suites sampled; runtime probes on macOS only; real service managers, terminal interaction and live credentials not exercised.
---

Audit baseline: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. No production or committed test source was changed. The unchanged coordinator CLI SHA-256 is 45840941809ca7c45622027f84d2c653c737e7ff35d375cfbf355b619456120f. Audit artifacts are uncommitted in this permanent worktree; COMMIT is therefore none.

**Two persistent Cargo setup failures are confirmed.** Both have executable red tests, before/after configuration snapshots, real Cargo consequences, and an unchanged baseline CLI. The red assertions are successful audit evidence, not failed audit work.

**cli-config-001 — Unix init corrupts a Cargo build table with a trailing comment.** A valid Cargo config containing [build] # Existing compiler configuration and rustc-wrapper="kache" is accepted before setup. With native env settings already complete and rustdoc unset, init --yes --no-service exits 0, says cargo doc is configured and Ready for Cargo builds, and appends a duplicate [build]. Real Cargo metadata exits 101 afterward with duplicate key. The plain [build] control stays valid and usable. The initial input and output are independently parsed with Python tomllib as well.

The source route is main.rs:1119 -> cli.rs:9319 init -> cli.rs:9442 configure_cargo_rustdoc -> cli.rs:9082 exact header recognition -> cli.rs:9129 appended table -> cli.rs:9245 unvalidated write. Every Cargo project using that Cargo home is blocked until the user restores the backup or edits the duplicate table. The proof targets ordinary Unix setup on macOS; it does not make a Windows claim. The backup limits recovery cost but does not prevent the reported-success breakage.

Evidence: [full red test](repro_rustdoc_config.py), [raw command evidence](rustdoc-config-evidence.json), [assertion output](rustdoc-config-output.txt). Replay entry cli-config-001 in [replay-cases.json](replay-cases.json) exits 1 with RUSTDOC_CONFIG_CORRUPTED; the failed Cargo command exits 101. Both fixture daemons were stopped successfully and disposable homes/runtime directories were removed.

**cli-config-002 — Doctor migration rewrites an absolute wrapper path to a missing executable.** A dependency-free library compiles through an existing absolute old-wrapper/sccache passthrough wrapper. Kache is available separately on PATH. doctor --fix exits 0 and globally replaces sccache with kache in the Cargo home config; the resulting old-wrapper/kache path does not exist. The next Cargo check exits 101 before rustc executes, with No such file or directory (os error 2).

The source route is main.rs:1133 doctor -> cli.rs:7171 migrate -> cli.rs:7318 content.replace("sccache", "kache") -> cli.rs:7319 in-place write. This breaks all projects sharing that Cargo config and creates no migration backup. The proof is deliberately limited to a working absolute executable path: other strings can also be rewritten, but no additional integrity claim is admitted from that alone. The test masks pgrep with a fixture executable returning no processes, so no user sccache server is observed or stopped.

Evidence: [full red test](repro_migration_path.py), [raw command evidence](migration-path-evidence.json), [assertion output](migration-path-output.txt). Replay entry cli-config-002 in [replay-cases.json](replay-cases.json) exits 1 with MIGRATION_WRAPPER_BROKEN. The control Cargo check exits 0 and the post-migration Cargo check exits 101. The only compile was a tiny dependency-free fixture; no repository/dependency build was performed.

**Dismissals and controls.** The ordinary Rust wrapper editor validates updated TOML before saving. An executed init --no-shell control with a commented table and no wrapper exits 1 for duplicate key while preserving every original config byte. This guards that editor and distinguishes it from the rustdoc write path. See [control script](probe_config_guards.py), [control output](config-guards-output.txt), and [control observations](config-guards-evidence.json). Documented compiler-prefixed preprocessing (kache cc -E) also passes with KACHE_DISABLED=0 and =1. Bare family-probe dispatch observations are preserved only as a narrow consultation artifact; no actual native-build consequence is asserted here.

Wrong-typed or invalid Kache config dropping the entire chosen/host layer was source-reviewed and reconciled with the explicit current contract at docs/getting-started/configuration.mdx:33. That dismissal closes an undisclosed precedence-regression claim, not the safety of every policy workload. Local-only daemon-start semantics and emitted telemetry were referred to their owning audit slices.

**Coverage and boundaries.** Every assigned production path and all assigned documentation were read in full. The source review traced CLI, shim, wrapper, Cargo/build-script/test-runner entry dispatch; config precedence/pinning and persistence; setup/migration/cleanup/verify/sync/report operations; and installed-service generation, ownership, bounded manager calls and status. Config TUI production code was read through line 1370, init_shell through 287, main through 1834, platform through 328 and service through 1284. Their subsequent inline tests were sampled. This is source review plus the named runtime probes, not an executed platform or whole-program integrity certification.

[coverage.json](coverage.json) records every one of the 28 primary paths, exact reviewed ranges, omissions, evidence and reopening conditions. The large suites and remaining inline test ranges were omitted exactly as follows:

- src/cli/tests.rs: omitted 1-2779, 3126-7809, 8011-8350
- src/config/tests.rs: omitted 1-1232, 1476-5364
- src/config_tui.rs: omitted 1501-2857
- src/init_shell.rs: omitted 391-642
- src/main.rs: omitted 2206-2711
- src/platform.rs: omitted 441-584
- src/service.rs: omitted 1501-1867
- tests/cli_commands_test.rs: omitted 76-1249, 1412-1655, 1716-2689, 2761-4237

The sampled dedicated tests include setup/rustdoc/editor cases in src/cli/tests.rs:2780-3125, cache cleanup cases at 7810-8010, host config precedence/isolation at src/config/tests.rs:1233-1475, and integration fixture/cleanup/migration/rustdoc cases at the ranges in coverage.json. Existing migration tests assert bare textual replacement, while existing rustdoc edit tests use plain build table headers; neither sample establishes the failing shapes are covered elsewhere.

The codebase-memory baseline graph mapped the main entry point and supplied bounded config/dispatch snippets. Its Rust semantics are partial because binding, expanded calls, and implementation relationships are unavailable; .cargo is intentionally excluded. Source reads were used as fallback, and missing graph edges were never treated as caller absence. See [graph coverage evidence](graph-index-status.txt).

Real launchd, systemd and Task Scheduler state was not changed. Linux/Windows branches and generated service artifacts were source-reviewed only. No interactive terminal run, live login/logout, real remote transfer, full repository test suite or load-sensitive benchmark was attempted. Reports, timeline/event interpretation, cache internals, compiler correctness, daemon lifecycle and auth were treated as consulted seams with their separate primary owners. The audit admits no additional defect based solely on an unexecuted source hypothesis or a green existing test.

Machine-readable admitted findings, full embedded red source and evidence-cited dismissals: [findings.json](findings.json). Runtime/tool/source provenance: [runtime-provenance.json](runtime-provenance.json).
