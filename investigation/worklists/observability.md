# Events, timelines, statistics, diagnostics, reports and terminal UI

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 23; bytes: 1112110.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- dispatch-commands-installed-services-and-contracts: 5 paths, 1347 text lines; subdivide into the listed contiguous file sections when needed.
- events-reports-and-terminal: 18 paths, 27665 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace main dispatch for CLI, compiler shim, build-script launcher, Cargo shim and test runner; command parsing, environment/config precedence, defaults, migration and path derivation must compose with owning domains.
- Review init/doctor/clean/sync/reporting/service-install operations for isolated fixture correctness, machine-readable output/schema consistency, failure exit status and handling of stale/missing installed binaries.
- Trace event/timeline/stat aggregation, TUI and report behavior against actual emitted semantics; investigate only external consequences relevant to integrity, reuse, resources and operations.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- cli-observable-contract: consult cli-config; CLI flags/config and command dispatch ↔ events, reports, explain, statistics, schemas and terminal output

## Sampling declarations

- Use isolated HOME/config/runtime paths. Actual launchd/systemd/Task Scheduler modifications are unauthorized; review generated service artifacts and source.
- Terminal interactivity and unsupported platform branches require explicit read-vs-executed reporting.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `docs/commands/cli.schema.json` (contract-doc-or-ci; 1397 bytes; 39 text lines)
- `docs/commands/meta.json` (contract-doc-or-ci; 52 bytes; 4 text lines)
- `docs/commands/reference.mdx` (contract-doc-or-ci; 44951 bytes; 557 text lines)
- `docs/commands/report.schema.json` (contract-doc-or-ci; 28381 bytes; 663 text lines)
- `docs/monitor.mdx` (contract-doc-or-ci; 8344 bytes; 84 text lines)
- `src/events.rs` (source-or-script; 128589 bytes; 3219 text lines)
- `src/explain.rs` (source-or-script; 26798 bytes; 700 text lines)
- `src/miss_chain.rs` (source-or-script; 93226 bytes; 2284 text lines)
- `src/otel.rs` (source-or-script; 39527 bytes; 1145 text lines)
- `src/phase_trace.rs` (source-or-script; 8070 bytes; 230 text lines)
- `src/report.rs` (source-or-script; 158103 bytes; 4302 text lines)
- `src/report/eviction_evidence.rs` (source-or-script; 4009 bytes; 94 text lines)
- `src/report/eviction_evidence/tests.rs` (test-or-fixture; 4763 bytes; 113 text lines)
- `src/report/tests.rs` (test-or-fixture; 155192 bytes; 4243 text lines)
- `src/run_diff.rs` (source-or-script; 13552 bytes; 404 text lines)
- `src/savings.rs` (source-or-script; 9038 bytes; 254 text lines)
- `src/savings/tests.rs` (test-or-fixture; 13278 bytes; 353 text lines)
- `src/since.rs` (source-or-script; 8804 bytes; 247 text lines)
- `src/term.rs` (source-or-script; 17098 bytes; 538 text lines)
- `src/timeline.rs` (source-or-script; 72192 bytes; 1919 text lines)
- `src/tui.rs` (source-or-script; 112291 bytes; 3103 text lines)
- `src/tui/tests.rs` (test-or-fixture; 100194 bytes; 2888 text lines)
- `src/tui_sessions.rs` (source-or-script; 64261 bytes; 1629 text lines)
