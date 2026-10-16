STATUS: DONE
COMMIT: 106ea8bb3352b78d2e09d01d7fbc8228478003ad
CHANGED: 1 source file; 2 separate commits
OPEN: 0
BLOCKERS: none
---

Final tip is ready for independent review. The branch starts at pinned upstream main 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9; no sibling PR changes or investigation artifacts are committed.

Commits: test-only `ccd7e177237ac2228ec01dba806a5dd1e461f6a4`, followed by production fix `106ea8bb3352b78d2e09d01d7fbc8228478003ad`. `read_events_and` reads byte-delimited records and uses the existing JSON parser; it skips a damaged record while retaining genuine I/O errors and shared-lock behavior. Its separate empty-record guard is unnecessary because the parser already rejects those records.

Checks:

- Baseline regression: 0 passed, 1 failed at the named interrupted-UTF8 recovery expectation (`red.log`), before production repair.
- Relevant suite with repair: 44 passed, 0 failed (`green.log`).
- Fixture-only discriminator: making the abandoned serialized event complete causes the exact retained-events assertion to fail; no production hand mutation (`discriminator.log`). Restored interrupted fixture: 1 passed, 0 failed (`restored-green.log`).
- Full gate at exact final SHA: `python3 /Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/pr-delivery/observability-003/run.py gate.log just check` exited 0; formatting, clippy with denied warnings, resource-guard checks and workspace tests ran (`gate.log`).
- Saved real compiler/report proof rerun against the final Cargo-built binary: actual rlib produced, independent valid event parsed, stats exit 0 (`production-green.log`).

| Acceptance criterion | Evidence |
| --- | --- |
| Later valid records remain readable | events.rs regression case append_next=true; original production proof now green |
| Earlier valid records survive malformed EOF | regression append_next=false; exact full-event equality, valid Unicode root retained |
| Real I/O errors keep propagating | line? is unchanged; parser failures remain per-record skips |
| Tests and fix stay separately committed | test commit contains only added test; fix commit is 2 insertions and 5 deletions in reader |
| Complete local gate passes before publication | gate exit 0 at 106ea8bb3352b78d2e09d01d7fbc8228478003ad |

Oracle: see `oracle.md`. The expected side is the complete test-owned first/next events; exact equality also checks order and valid Unicode. The damaged bytes are a prefix of an actual serialized event, in a temporary filesystem fixture with no host config or cache. The discriminator demonstrates that successful parsing of an extra valid record cannot satisfy this expected result.

Shape checks: no new production function, validator, type, trait or indirection; existing BufRead and serde_json parsing are reused. No suppression or unrelated refactor. The changed reader stays below size limits. The isolated test adds no process-global state or production hooks. Direct diff/status checks show exactly src/events.rs changed and a clean worktree. No local cargo-mutants was run; changed-line mutation testing remains CI work.

Limits: this repair is scoped to report/compiler event reading. Summary/transfer logs and UTF-8 rotation behavior were not repaired, because those were source-only leads outside this confirmed reader defect. No unsupported-platform runtime execution or broad integrity/performance claim. Parent handles independent review and publication; no PR was created here.

Gate environment note: the first run failed two baseline tests because HOME was under the protected /private prefix and an explicitly present empty host-config file changed provenance. The isolated runner now uses the same temporary HOME via /tmp and explicitly disables the host layer with KACHE_HOST_CONFIG="". Both controls then passed (2/0), and the complete rerun passed with no PR source or commit change. The initial log and source-based diagnosis are preserved in gate-environment-failed.log and environment-correction.md.

Workspace test summaries:
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4395 filtered out; finished in 0.31s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4395 filtered out; finished in 0.22s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4395 filtered out; finished in 0.22s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4395 filtered out; finished in 0.22s
- test result: ok. 4382 passed; 0 failed; 14 ignored; 0 measured; 0 filtered out; finished in 62.45s
- test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 5.83s
- test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 5.84s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 4.10s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.65s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.20s
- test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 5.34s
- test result: ok. 18 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 13.62s
- test result: ok. 24 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 11.12s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s
- test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.45s
- test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 9.14s
- test result: ok. 116 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 42.31s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.58s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 6.19s
- test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.40s
- test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 4.78s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.30s
- test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.17s
- test result: ok. 37 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 6.54s
- test result: ok. 42 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 6.73s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.07s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.52s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.28s
- test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 10.76s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.42s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.98s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.30s
- test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 7.84s
- test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.00s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 5.06s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.63s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.57s
- test result: ok. 41 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s
- test result: ok. 280 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.95s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s
- test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s
- test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 57 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.15s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 102 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.38s
- test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.00s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.01s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.02s
- test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.07s
- test result: ok. 39 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.28s
- test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 569 filtered out; finished in 0.00s
- test result: ok. 568 passed; 0 failed; 2 ignored; 0 measured; 0 filtered out; finished in 32.03s
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
