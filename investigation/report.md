STATUS: DONE
COMMIT: none
CHANGED: 41
OPEN: 3
BLOCKERS: none
CONFIRMED: 3
LIMITS: macOS isolated fixtures; no live PTY/OTLP/load soak, unsupported platforms, or complete large-test review.
---

Audited untouched baseline `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. All assigned production and contract text was read. Large test suites were sampled deliberately. No production code, main clone, user config, installed service or real cache changed. The parent supplied the baseline CLI; no Kache rebuild was required. Each production fixture used an isolated temporary HOME/config/cache/runtime and a real rustc invocation whose rlib output was verified before the report assertion.

The priority finding is the root-redaction contract breach. Skip-reason loss is a lower-priority observability issue, not an integrity finding. The interrupted UTF-8 recovery probe, if present below, establishes report failure after a real valid append; timing of an actual killed writer and rotation failure were not independently measured.

**observability-001 — Redacted JSON reports expose workspace roots in bypass.slowest rows.**

A real successful Rust compile is skipped from retention by configured min_store_compile_ms=60000; stats --format json --redact redacts trace args.root but emits the private workspace path in bypass.slowest[0].root.

Privacy/operational defect: explicitly sanitized shareable JSON leaks typed workspace root, which can reveal user/customer/project naming. Ordinary skipped/passthrough activity is reachable. Requires sharing the report; no artifact corruption or secrets beyond the recorded path established. Medium priority relative to observability slice.

Production trace: actual kache/rustc compile → wrapper admission gate → schema26 Skipped root → build_bypass_analysis/to_bypass_detail → CLI redact_report omits bypass → JSON stdout retains root.

Decisive source: src/report.rs:1888-1903 — to_bypass_detail copies e.root into BypassDetail.root.; src/report.rs:2785-2821 — redact_report visits meta, trace, event details, errors and transfers but never report.bypass.slowest.; src/cli.rs:1738-1744 — Production CLI calls redact_report before JSON serialization.; docs/commands/reference.mdx:337-355 — Roots must be replaced with redacted; --redact applies to every format.

Red test: `python3 investigation/probes/real_compile_report.py redact-root` (expected exit 1 on baseline). Full test source, replay JSON and unedited stdout/stderr are persisted under `investigation/`. The dedicated assertion follows a successful actual compilation and positive semantic control.

```text
CONTROL rustc produced rlib; production event records admission-threshold
OBSERVED report bypass root = /private/tmp/obs-1ae59xvg/customer-secret-workspace
Traceback (most recent call last):
  File "/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/probes/real_compile_report.py", line 91, in <module>
    main()
  File "/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/probes/real_compile_report.py", line 88, in main
    assert row['root'] == 'redacted', 'REDACT_BYPASS_ROOT_LEAK: production root survives --redact'
AssertionError: REDACT_BYPASS_ROOT_LEAK: production root survives --redact
```

**observability-002 — Report bypass reasons discard the dedicated skip_reason recorded by successful Rust skip gates.**

The same real compile records result=skipped and skip_reason=admission-threshold while passthrough_reason is empty; report bypass.slowest.reason and grouped reasons become unknown.

Lower-priority diagnosis gap. Hides why retention was declined and merges distinct safeguards/admission policies into unknown. No evidence of integrity failure, wrong reuse or compiler result change. Only report consumer proven; other diagnostics not independently asserted.

Production trace: actual compiler succeeds → wrapper emits admission-threshold skip_reason → report skipped route → bypass_reason ignores field → unknown row and grouping.

Decisive source: src/report.rs:1943-1950 — bypass_reason reads only e.passthrough_reason, returning unknown for empty.; src/wrapper.rs:4733-4752 — Production put-side admission gate emits EventResult::Skipped with skip_reason(admission-threshold).; src/report/tests.rs:3018-3031 — Skipped test fixture populates passthrough_reason rather than dedicated skip_reason.

Red test: `python3 investigation/probes/real_compile_report.py skip-reason` (expected exit 1 on baseline). Full test source, replay JSON and unedited stdout/stderr are persisted under `investigation/`. The dedicated assertion follows a successful actual compilation and positive semantic control.

```text
CONTROL rustc produced rlib; production event records admission-threshold
OBSERVED report reason = unknown
Traceback (most recent call last):
  File "/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/probes/real_compile_report.py", line 91, in <module>
    main()
  File "/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/probes/real_compile_report.py", line 84, in main
    assert row['reason'] == 'admission-threshold', 'SKIP_REASON_LOST: production skip became unknown in report'
AssertionError: SKIP_REASON_LOST: production skip became unknown in report
```

**observability-003 — An interrupted event record inside a UTF-8 character poisons reporting even after the next valid event is appended.**

First compile successfully in a Unicode workspace so the baseline emits a genuine event. Truncate that actual serialized record immediately after the first byte of its workspace-root multibyte character, modeling an interrupted write. A real successful compiler appends a complete event after newline repair. stats --format json then exits 1 with invalid UTF-8 instead of skipping the abandoned fragment and reporting the valid event.

Operational recovery defect after interrupted logging of unicode data. A single fragment blocks reports for subsequent valid compiles until log repair/replacement. Fixture executes actual producer and report consumer on macOS; it injects the interrupted byte state rather than timing a kill/disk-full event. Cache artifacts compile correctly; no cache integrity failure proven. Rotation consequence source-only.

Production trace: short write/process interruption in unicode JSON root → next ordinary wrapper append repairs newline → good compiler event preserved → stats/read_events_and decodes abandoned fragment → I/O invalid UTF-8 aborts report.

Decisive source: src/events.rs:684-705 — append_log_line terminates an abandoned byte fragment with newline but preserves incomplete UTF-8.; src/events.rs:824-843 — read_events_and uses reader.lines(); line? aborts before invalid JSON skip logic when UTF-8 decoding fails.; src/events.rs:1234-1242 — Rotation also reads entire log as UTF-8 text, so source indicates ordinary rotation cannot clear invalid bytes; rotation consequence not separately executed.

Red test: `python3 investigation/probes/real_compile_report.py torn-utf8` (expected exit 1 on baseline). Full test source, replay JSON and unedited stdout/stderr are persisted under `investigation/`. The dedicated assertion follows a successful actual compilation and positive semantic control.

```text
CONTROL rustc produced rlib; next valid event retained after repaired newline
OBSERVED stats exit = 1; stderr = error: stream did not contain valid UTF-8
Traceback (most recent call last):
  File "/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/probes/real_compile_report.py", line 91, in <module>
    main()
  File "/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/probes/real_compile_report.py", line 74, in main
    assert reported.returncode == 0, 'TORN_UTF8_POISONS_REPORT: valid production event unavailable after interrupted unicode log record'
AssertionError: TORN_UTF8_POISONS_REPORT: valid production event unavailable after interrupted unicode log record
```

Useful dismissals:
- False eviction after a nonpublished admission/safety skip. Examined stored_or_served Miss predicate against actual emitters and actual admission compile. Closed by src/tui_sessions.rs:647-653; src/wrapper.rs:4560-4756; evidence/real-skip-reason.events.json Reopen if A producer labels a successful nonpublished result Miss with empty store_error instead of Skipped, or history starts treating Skipped as stored.
- Transfer ambiguity causing cross-session attribution. Read complete production attribution and usefulness logic. Closed by src/timeline.rs:260-297,393-515; explicit prefetch session, unique eligible key/window only; ambiguity returns None. Reopen if Origin session is mutated/omitted unexpectedly or ambiguous candidates become selected. Remote runtime lifecycle remains a consult limitation.
- Unbounded causal-chain walk and mixed-unit roots. Reviewed complete production walk and identity filters. Closed by src/miss_chain.rs:83-87,377-520; MAX_DEPTH=12 and MAX_NODES=64 with explicit truncation, stable unit/root boundaries. Reopen if Walk branches bypass limits or identity gates change.
- Savings ledger rotation crash loss treated as a durability violation. Closed by docs/commands/reference.mdx:310; src/events.rs:1194-1290; ledger fold after rotation is best effort and documentation qualifies crash durability. Reopen if Published contract guarantees durable all-time savings across crash or implementation double-counts under synchronized read.

Coverage is machine-readable in `coverage.json`: every primary path has exact reviewed and omitted ranges, state, evidence and reopening conditions. Full production reads do not establish exhaustive runtime correctness. Omitted ranges from sampled paths:

- `src/events.rs`: 1891-3219
- `src/miss_chain.rs`: 1001-2284
- `src/otel.rs`: 821-1145
- `src/report/tests.rs`: 1-913, 1141-1224, 1302-1683, 1722-2957, 3047-3871, 3936-4243
- `src/timeline.rs`: 861-1919
- `src/tui/tests.rs`: 1-1373, 1420-1717, 1772-2888
- `src/tui_sessions.rs`: 901-1629

Graph scope: baseline coordinator graph was ready but Rust semantic coverage was partial (`binding_oracle_unavailable`, `expanded_calls_unavailable`, `impl_relationships_unavailable`). Architecture, symbol snippets and positive inbound traces guided reading; consequential producer/consumer logic was checked directly in source. No negative graph result was accepted as a reachability proof. Current CLI rejected the skill’s max-response-bytes option, so supported default snippet retrieval was used.

Execution limits: standalone green suite, cargo-mutants, interactive terminal, Windows/Linux terminal paths, long-running monitor resource growth, live collector export and remote network faults were not run here. Read findings cover owned events/report paths; daemon lifecycle proof is coordinated with the remote-daemon agent. No measurements are claimed as general performance results.

Raw source-only leads are not admitted as proven findings. Summary/transfer torn-tail append is under coordinated investigation until an ordinary daemon lifecycle produces executed evidence. OTLP atomic snapshot and long-monitor memory behavior remain unmeasured risk surfaces, without admitted defect claims.

Artifact validation: audit Python source parses, replay files have argv/workdir/timeout/failure markers, red output markers match expected assertions, all primary paths are represented, and tracked baseline diff is empty.
