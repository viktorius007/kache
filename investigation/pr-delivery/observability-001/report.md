STATUS: DONE
COMMIT: bbe72d7a4f0f219dc6a7c6a0ba59311510b79563
CHANGED: 2 source/test files; 2 separate commits
OPEN: 0
BLOCKERS: none
---

Ready for independent review at the exact final SHA. Independent branch starts at pinned main 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. No sibling fixes, investigation files or profiling changes are in the diff.

Commits: test-only `17ec179fc72c9acfc4b94ee58f19fc5ed2ec3f87`; production fix `bbe72d7a4f0f219dc6a7c6a0ba59311510b79563`. The fix applies existing redact_owned to the bypass.slowest root collection, adding no API, helper or alternate policy.

Checks:

- Corrected baseline regression: 0 passed, 1 failed at the dedicated bypass workspace-root assertion before repair (`red.log`).
- Report suite after repair: test result: ok. 100 passed; 0 failed; 0 ignored; 0 measured; 4295 filtered out; finished in 0.77s (`green.log`).
- Fixture-only discriminator: replacing a nonempty test root with empty, while the expected redacted value stays fixed, fails the same exact-vector assertion (`discriminator.log`). Restored fixture: 1 passed, 0 failed (`restored-green.log`).
- Complete local gate at exact final SHA: `python3 /Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/pr-delivery/observability-001/run.py gate.log just check` exited 0 (`gate.log`): formatting, denied-warning clippy, resource guard and workspace tests.
- Reused actual Rust compiler proof: compiler succeeds and produces rlib; --redact hides the actual bypass root and trace root; an ordinary report retains its actual root and identical summary (`production-green.log` and saved report JSON).

| Acceptance criterion | Evidence |
| --- | --- |
| Skipped and passthrough bypass roots redact | Existing redaction regression now includes two nonempty roots and exact expected redacted values |
| Empty fields retain semantics | Empty bypass root stays empty, with existing error/transfer empty-field controls |
| Ordinary report fields preserved | Known result/crate/elapsed assertions and actual unredacted root/summary controls |
| Existing redaction remains intact | Original trace/root/cache-key/object-path assertions remain; free-form store error preserved |
| Test and fix remain separate | Test commit touches only report/tests.rs; fix commit adds the missing root traversal only |
| Gate passes before publication | just check exit 0 at bbe72d7a4f0f219dc6a7c6a0ba59311510b79563 |

Oracle: `oracle.md`. Expected roots are independent literal policy outputs. The selected three rows are added after the preexisting fixture rows so the oracle does not assume the fixture collection was empty. Initial cardinality-assumption failure is preserved in fixture-cardinality-correction.log; only the corrected leak assertion earns the committed regression red. The fixture-only discriminator proves empty-versus-sensitive roots vary the result. Fixtures are isolated; no production hook or global state is added.

Shape: redact_report remains below size limits; no new production function, type, indirection or suppression. Existing redact_owned is the single redaction policy. Only the omitted bypass collection is touched. Tests preserve the existing contract assertions and add explicit bypass row checks.

The private target is sequentially reused from observability-003 after its gate ended. Its branch tip remains 106ea8bb3352b78d2e09d01d7fbc8228478003ad and its source/evidence were not modified. The runner retains normal toolchain HOME/TMPDIR, isolates the kache config/cache and disables the host-config layer. Per-CLI fixtures retain their own isolation. It clears self-wrapping and runs all tests with one test thread. Earlier full-gate and focused-control failures are preserved. The coordinated cargo-agent controls isolated globally temporary HOME or TMPDIR as sufficient to trigger the unrelated sandbox-control failure; environment-diagnosis.json records the corrected gate context. No source changes, skips, or warming were used. The previous blocked report is preserved in report-blocked.md.

Limits: no local cargo-mutants; changed-line mutation testing is CI work. No unsupported-platform runtime claim. No skip-reason fix is included. Parent owns independent review and publishing; no PR was created here.

Workspace test summaries:
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4394 filtered out; finished in 0.31s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4394 filtered out; finished in 0.22s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4394 filtered out; finished in 0.23s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4394 filtered out; finished in 0.23s
- test result: ok. 4381 passed; 0 failed; 14 ignored; 0 measured; 0 filtered out; finished in 99.25s
- test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 10.64s
- test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 8.66s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 5.05s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 4.14s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.47s
- test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 13.07s
- test result: ok. 18 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 25.99s
- test result: ok. 24 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 19.21s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s
- test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.00s
- test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 15.75s
- test result: ok. 116 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 56.40s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.63s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 7.84s
- test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.36s
- test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 9.78s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.30s
- test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.34s
- test result: ok. 37 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 15.06s
- test result: ok. 42 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 16.24s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.44s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.07s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.32s
- test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 14.12s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.46s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.57s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.35s
- test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 16.87s
- test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 4.01s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 10.12s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.05s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.58s
- test result: ok. 41 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s
- test result: ok. 280 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.11s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s
- test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 57 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.37s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 102 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.56s
- test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.01s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.01s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s
- test result: ok. 39 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.13s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 569 filtered out; finished in 0.05s
- test result: ok. 568 passed; 0 failed; 2 ignored; 0 measured; 0 filtered out; finished in 66.06s
- test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
