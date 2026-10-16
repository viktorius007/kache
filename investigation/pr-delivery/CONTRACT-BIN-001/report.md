STATUS: READY FOR INDEPENDENT REVIEW
COMMIT: 44d79666bacc71d75eb52c342f42aed8e5b776f6
CHANGED: src/args.rs; tests/adaptive_incremental_test.rs
OPEN: CI changed-line mutation testing and independent review
BLOCKERS: none
---

Authority: saved CONTRACT-BIN-001 reproduction and compiler-policy fallback contract.

Regression oracle: the configured shell fallback writes a marker only when it receives the fixture rustc invocation. A successful compilation cannot manufacture this marker. The existing Cargo explicit-bin call is the positive control; deleting that marker before the direct omitted-type call prevents stale evidence. The event must separately report intentional user-facing passthrough and fallback=true.

Gap search: `rg -n 'fallback|cache_executables|user_facing' tests src/args.rs justfile`. Nearest test: tests/adaptive_incremental_test.rs:853; previously it only drove Cargo, which passes --crate-type bin. New input: direct rustc omits --crate-type.

Graph lookup: check_index_coverage for src/args.rs and tests/adaptive_incremental_test.rs reports metadata_match and semantic_partial (bindings, expanded calls, impl relationships); source reads close this bounded predicate/fixture scope. search_graph `.*user_facing_executable.*` returned the existing predicate and explicit-bin fallback test; both are reused. No helper or new indirection.

Test cost: one additional real rustc compilation and event/marker checks inside the existing integration test; no sleep, extra Cargo workspace build, or persistent process introduced.

Executed regression: red command `CARGO_TARGET_DIR=$PWD/target python3 <coordinator>/investigation/pr-delivery/build-slot.py cargo test --test adaptive_incremental_test user_facing_executable_preserves_configured_fallback_contract -- --exact` exited 101 at tests/adaptive_incremental_test.rs:940 with `default-bin invocation bypassed the configured fallback`. Same command after repair exited 0: 1 passed, 0 failed. The baseline is also the hand-applied deletion mutant for the newly added empty-type alternative.

Commits: ba54810fce5d6461a6927e4884cbfbd4420a0952 (test-only red); 44d79666bacc71d75eb52c342f42aed8e5b776f6 (production repair). Source comment deliberately says potentially binary: source crate-type attributes are not scanned, so omitted CLI type conservatively bypasses caching when executable caching is disabled.

Shape: one existing boolean predicate change and one added input class in the existing fallback test; no new helper, duplication layer, or scanning logic. New comment explains the absent CLI type boundary. Existing fixture setup, hermetic command, event helper, and explicit-bin control are reused.

Exact-tip gate: `CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/contract-bin-001/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check` exited 0 at 44d79666bacc71d75eb52c342f42aed8e5b776f6. Summaries: {"completed_suites": 76, "passed": 5891, "failed": 0, "ignored": 16}. Formatting, clippy -D warnings, test-resource guards, workspace unit/integration/doc tests passed. The regression and explicit lib/proc-macro predicate tests passed within this full gate.

Diff check: git diff --check baseline HEAD passed. Only src/args.rs and tests/adaptive_incremental_test.rs are committed; investigation artifacts remain untracked. No production installation or user cache/config changes. Parent owns fresh independent review and CI mutation shards; no local cargo-mutants run per AGENTS.md.
