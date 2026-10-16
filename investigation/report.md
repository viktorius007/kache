STATUS: DONE
COMMIT: none
CHANGED: 315
OPEN: 0
BLOCKERS: none
CONFIRMED: 2
LIMITS: Exact 16-path audit; full production review, two inline Rust test suites sampled; no Rust unit-suite, Linux contention workload, real network timing or broad performance measurement; partial Rust graph semantics corroborated from source.
---

The benchmark audit confirms two baseline guardrail defects. Neither production source nor production tests were changed. [findings.json](findings.json) contains the two admitted findings with complete proof sources and six meaningful dismissals. [coverage.json](coverage.json) accounts for every assigned primary path: 14 fully reviewed files, two sampled files whose production portions were fully reviewed, no unreviewed primary paths. The sampled portions are the large inline test suites in bench_profile.rs and bench_otlp.rs, with exact read ranges recorded.

1. **benchmark-guardrails-001: unsuccessful measurements can leave worker processes alive.** scripts/bench/engine.py:23-41 cleans the process group only when process.wait raises. A nonzero exit becomes CalledProcessError after that cleanup scope. The executed fixture launches a real child, exits its leader with status 4, and observes the child write an artifact after run_measurement returns. The real timeout control kills the same type of child before it can write. The existing exit-failure test starts no children, and the timeout cleanup test mocks killpg, so both existing checks stay green.

   The actual short driver invokes this helper for its selected scenario instrument; the local gate proceeds to other selected projects after a failed measurement. This is a resource-isolation defect for failing instruments/build helpers with surviving same-group children. The proof establishes a late write and process survival, not measured CPU contamination, data loss, or a false release verdict. Its finally block kills its isolated child. A childless failed build is unaffected.

2. **benchmark-guardrails-002: the timed dependency-fetch guard ignores stderr.** crates/kache-e2e/src/bench_runner.rs:1573-1620 sends stderr straight to the build log, while FetchCount observes only lines read from stdout. The guard's source explains why network work inside a timed cache comparison is invalid. Cargo's current primary [Shell source](https://raw.githubusercontent.com/rust-lang/cargo/master/crates/cargo-util-terminal/src/shell.rs) routes status messages through message_stderr.

   The paired proof executes the actual untouched baseline kache-scenario CLI and its complete clone/build/report path. A recognized download line on stdout produces exit 1, a fetch refusal and no result. The identical line on stderr produces exit 0 and a written result with verdict.ok=true. Both actual build-cold.log files contain the message. Local Git subject and cache-report CLI are explicit fixture adapters: there are no real compiles, downloads, cache restores or measured performance conclusions. The claim is limited to the ineffective unconditional stream guard. Shipped Cargo profiles run untimed cargo fetch --locked first, reducing ordinary exposure; that preparation does not make the fallback detector work.

Both proofs passed the coordinator's admission gate by failing with their specified behavioral assertion on pinned baseline 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. Replay cases are [nonzero-orphan-case.json](proofs/nonzero-orphan-case.json) and [timed-fetch-stderr-case.json](proofs/timed-fetch-stderr-case.json). Exact assertion output and admission verdicts are saved in raw/nonzero-orphan-replay.log, raw/nonzero-orphan-admission.json, raw/timed-fetch-stderr-replay.log and raw/timed-fetch-stderr-admission.json. Fixture source, actual CLI logs, result JSON and per-stream observations remain under investigation/.

Replay either case from this worktree with:

```sh
/opt/homebrew/bin/python3.14 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/replay-gate.py investigation/proofs/nonzero-orphan-case.json --output investigation/raw/nonzero-orphan-recheck.log
/opt/homebrew/bin/python3.14 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/replay-gate.py investigation/proofs/timed-fetch-stderr-case.json --output investigation/raw/timed-fetch-stderr-recheck.log
```

The second case reuses the read-only baseline binary built by audit_guardrails at /Users/viktor/Developer/github/kache-investigations/audit-guardrails/investigation/target/debug/kache-scenario. Its SHA-256 and all 16 matching production blob hashes are recorded in raw/source-identity.json. Each fetch replay creates a fresh isolated fixture under investigation/. The red assertions are expected evidence, and the admission gate returns success only when it recognizes them.

Existing verification passed using supported /opt/homebrew/bin/python3.14: all 58 scripts/bench/tests tests and all 28 scripts/test-bench-contention.py tests. Commands were PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts /opt/homebrew/bin/python3.14 -m unittest discover -s scripts/bench/tests and PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.14 scripts/test-bench-contention.py. Their logs are raw/python-bench-tests-py314.log and raw/contention-tests-py314.log. Earlier runs using the system Python 3.9 failed on unavailable zip(strict=...) and tomllib; these are preserved as environment mismatch evidence and are not admitted findings.

Dismissals address phase-result validation, independent paired samples and deadline completeness, staging a baseline instrument as the comparison ruler, independent contention warm snapshots/error rejection, current single-thread trace nesting, and unknown host/telemetry readings. Green suites support those specific checks; they do not prove benchmark integrity generally. The direct Rust CLI intentionally reports some invalid_reasons as advisory, while the Python comparison rejects them; the scope of that dismissal is explicit.

Structural exploration used the installed codebase-memory skill and shared project Users-viktor-Developer-github-kache-investigations-coordinator, generation 2026-10-11T05:36:35Z. The exact 16 paths report metadata_match/no_recorded_issue, without pagination. This is a best-effort signal. Rust binding-oracle, expanded-call and impl relationships remain unavailable, so all consequential claims were corroborated from source and no exhaustive graph caller claim is made. The audit did not repair production, run cargo-mutants, execute a real benchmark workload, install mbx or alter real homes, config, launchd or caches. OPEN counts unresolved investigations; the two confirmed finding records remain open for owner disposition.
