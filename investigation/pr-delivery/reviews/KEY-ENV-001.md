PASS
Verified SHA: `0bf475d9f614217b973deddd842e023403e9ba06` (clean checkout, exact delivered fix commit).
Read-only checks: `git rev-parse HEAD`, `git status --short`, `git diff --check 4ee0f9e..HEAD` — expected SHA, clean tree, no whitespace errors.
Recorded proofs reused: `red.log` exit 101 (cached `unset` versus direct-rustc `empty`); `green.log` — 410 cache-key, 11 sharing, 12 integration tests passed; `record-green.log` — 3 passed.
Final gate: delivery.json binds the exact SHA to build-slot-wrapped `just check`, `gate_exit: 0`; gate.log contains all five added tests passing. No gate or investigation rerun.
| Acceptance criterion | Proof checked |
| --- | --- |
| One bug; separate test and fix commits; clean source-only diff | `f55e7983962f3aa6ca7fe4884b417f98aafeb410` changes tests only; the delivered fix follows it; four source/test paths only. |
| Behavioral red/green; stable-hit controls; no weakened oracle | `tests/cache_key_underkeying_test.rs:961` compares compiled behavior against direct rustc across absent/empty/value/absent with predictions on/off and verifies unchanged local hits. |
| Presence, transport, and cache upgrade correctness | `src/cache_key.rs:3211`, `:6108`, `:6155`, `:6230`, `:6293`, `:6559`, `:6772`, `:7425`, `:7473`, `:8632`; `src/prediction_share.rs:91`, `:115`, `:147`, `:166`. |
| Portable fixture and short source-linked PR body | Hermetic children, temporary HOME/cache, preserved RUSTUP_HOME, Windows executable suffix; pr-body.md is 43 words and links defective baseline `parse_env_dep_info` lines 8607–8621. |
Findings: none blocking within the assigned diff and acceptance criteria.

Checked and found correct:

- `src/cache_key.rs`: rustc dep-info distinguishes absence from a present empty value; prediction validation compares raw `OsString` presence; hashing adds a tagged presence field for every reported variable. Old ambiguous records fail schemas 2/102 at persisted and remote read boundaries, and pre-fix artifact keys cannot satisfy the repaired encoding. Existing normalization applies to present values as before. No new production helper, indirection, suppression, or unrelated cleanup was introduced; changed branches remain shallow.
- `src/cache_key/tests.rs`: parser and validation regressions have recorded behavioral reds; the three-state validation matrix covers accepted and rejected transitions. Portable round-trip controls retain presence. Existing fixtures were adapted to the new representation without weakening their asserted behavior.
- `src/prediction_share.rs`: plain and portable remote conversion and plain resolution preserve `None` separately from `Some(Portable::Literal(""))`; nested schema checks reject incompatible records. Existing transport/refusal tests remain green.
- `tests/cache_key_underkeying_test.rs`: the direct-rustc oracle is independent of key generation; the real compiler, cache restore, predictions, and child environment remain exercised. Fixture state varies the named property and the saved red demonstrates the distinction. Temporary state is isolated and process-global environment is not mutated by the new test.
- Portability was checked in source; the gate ran on macOS. Windows execution and CI mutation testing remain unclaimed; repository AGENTS.md assigns mutation testing to draft-PR CI.
- Codebase-memory `list_projects` showed no index for the delivered checkout. Bounded direct source reads of known changed paths were used; no graph completeness claim or new repository index was made.

Evidence directory: `/Users/viktor/Developer/github/kache-investigations/audit-key-native-inputs/investigation/pr-delivery/KEY-ENV-001`.
