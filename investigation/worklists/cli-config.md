# CLI dispatch, configuration, shims and installed services

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 28; bytes: 1663496.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- configuration: 5 paths, 13532 text lines; subdivide into the listed contiguous file sections when needed.
- dispatch-commands-installed-services-and-contracts: 23 paths, 30398 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace main dispatch for CLI, compiler shim, build-script launcher, Cargo shim and test runner; command parsing, environment/config precedence, defaults, migration and path derivation must compose with owning domains.
- Review init/doctor/clean/sync/reporting/service-install operations for isolated fixture correctness, machine-readable output/schema consistency, failure exit status and handling of stale/missing installed binaries.
- Trace event/timeline/stat aggregation, TUI and report behavior against actual emitted semantics; investigate only external consequences relevant to integrity, reuse, resources and operations.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- dispatch-compiler: consult rust-wrapper; src/main.rs dispatch → compiler detection/wrapper.run; disabled/reentrant/direct invocation and exit propagation
- dispatch-cargo-launcher: consult cargo-build; src/main.rs dispatch → cargo_proxy/build_script/test_runner; argv/environment ownership
- telemetry-schema: consult planner-service; events/report/timeline ↔ kache-core timeline and timeline_client/server ingest; schema, counters, bounded retention

## Sampling declarations

- Use isolated HOME/config/runtime paths. Actual launchd/systemd/Task Scheduler modifications are unauthorized; review generated service artifacts and source.
- Terminal interactivity and unsupported platform branches require explicit read-vs-executed reporting.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `docs/compatibility.mdx` (contract-doc-or-ci; 1628 bytes; 16 text lines)
- `docs/getting-started/comparison.mdx` (contract-doc-or-ci; 6010 bytes; 96 text lines)
- `docs/getting-started/configuration.mdx` (contract-doc-or-ci; 65826 bytes; 637 text lines)
- `docs/getting-started/installation.mdx` (contract-doc-or-ci; 5680 bytes; 154 text lines)
- `docs/getting-started/meta.json` (contract-doc-or-ci; 215 bytes; 14 text lines)
- `docs/getting-started/quick-start.mdx` (contract-doc-or-ci; 8701 bytes; 126 text lines)
- `docs/getting-started/troubleshooting.mdx` (contract-doc-or-ci; 5666 bytes; 131 text lines)
- `docs/how-it-works/architecture.mdx` (contract-doc-or-ci; 7560 bytes; 95 text lines)
- `docs/how-it-works/meta.json` (contract-doc-or-ci; 119 bytes; 9 text lines)
- `docs/index.mdx` (contract-doc-or-ci; 4003 bytes; 78 text lines)
- `docs/meta.json` (contract-doc-or-ci; 259 bytes; 17 text lines)
- `src/cli.rs` (source-or-script; 377863 bytes; 10293 text lines)
- `src/cli/login.rs` (source-or-script; 15103 bytes; 412 text lines)
- `src/cli/miss_diagnosis.rs` (source-or-script; 7101 bytes; 178 text lines)
- `src/cli/tests.rs` (test-or-fixture; 295356 bytes; 8350 text lines)
- `src/config.rs` (source-or-script; 186209 bytes; 4324 text lines)
- `src/config/tests.rs` (test-or-fixture; 189931 bytes; 5364 text lines)
- `src/config_tui.rs` (source-or-script; 99971 bytes; 2857 text lines)
- `src/init_shell.rs` (source-or-script; 25067 bytes; 642 text lines)
- `src/main.rs` (source-or-script; 98342 bytes; 2711 text lines)
- `src/notice.rs` (source-or-script; 4000 bytes; 131 text lines)
- `src/platform.rs` (source-or-script; 22615 bytes; 584 text lines)
- `src/service.rs` (source-or-script; 64535 bytes; 1867 text lines)
- `src/wrapper_config.rs` (source-or-script; 11498 bytes; 350 text lines)
- `tests/cli_commands_test.rs` (test-or-fixture; 151749 bytes; 4237 text lines)
- `tests/fixtures/config_editor_legacy.toml` (test-or-fixture; 1816 bytes; 73 text lines)
- `tests/host_config_test.rs` (test-or-fixture; 5186 bytes; 149 text lines)
- `tests/macos_local_network_metadata_test.rs` (test-or-fixture; 1487 bytes; 35 text lines)
