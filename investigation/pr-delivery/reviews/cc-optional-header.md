PASS
Verified SHA: `7d2905f91fb72b8fec610771df13670cbe427c72` (clean checkout, exact delivered fix commit).
Read-only checks: `git rev-parse HEAD`, `git status --short`, `git diff --check 4ee0f9e..HEAD` — expected SHA, clean tree, no whitespace errors.
Proofs reused: red.log — newly created header still returned 11 rather than fixture-owned 23; green.log — 10 passed; ordinary-control.log — 1 passed.
Final gate: delivery.json binds build-slot-wrapped `just check` exit 0 to this SHA; gate-final.log records the regression passing and all 42 integration tests passing. No repeated investigation or gate execution.
| Acceptance criterion | Proof checked |
| --- | --- |
| Separate test/fix commits and source-only scope | Test-only `6df09ef9e67e4481ac83f83a9aa6176f7457f7e8` followed by the delivered fix; only cc.rs and two test files changed. |
| Source, transitive, continued probes; both discovery modes | `tests/cc_passthrough_args_test.rs:193`: real compiler and linked exit-code oracle, source versus included-header CRLF continuation, discovery 0/1, absent/warm/created fixtures. |
| Stale records cannot bypass guard; ordinary caching remains | `src/compiler/cc.rs:6259`, `:7275`, `:7374`; `src/wrapper.rs:2120`; `tests/integration_test.rs:3342` retains exact miss/hit and preprocess-count controls. |
| Portability and explicit tradeoff in concise PR body | New regression remains within the Unix-gated test file; production scan uses raw bytes; the 50-word body links baseline cc_shadowing_names and explicitly states compilation without caching. |
Findings: none blocking within the assigned bounded repair and acceptance criteria.

Checked and found correct:

- `src/compiler/cc.rs`: the small raw-input guard scans every positive read-set path, including the source and transitively included headers. Removing backslash/CR/LF conservatively recognizes continued spellings; matching the `__has_include` prefix covers `__has_include_next`. Memo hits, fresh captures, and compile-first captures all pass through the guard before a key is returned. Existing pre-fix memos therefore cannot authorize object restoration. The wrapper returns on key failure before cache lookup or publication; a pending memo cannot be committed on this path. Ordinary read-set behavior is unchanged.
- `tests/cc_passthrough_args_test.rs`: independent fixture expectations 11 and 23 pin compiler-visible behavior after optional.h appears. The baseline execution fails at that behavioral assertion; the repaired full gate passes. The test exercises both discovery settings and continued probes in included headers, removes objects between invocations, and keeps HOME/config/cache/runtime in temporary fixture state. It introduces no test visibility hooks or process-global environment changes.
- `tests/integration_test.rs`: the ordinary control now uses a local macro-built asm alias instead of host stdio.h, which can itself contain an availability probe. It retains the original real-compiler macro-operand safety purpose and all exact cold-miss, warm-hit, changed-header, restored-header, and preprocessor-count assertions. The targeted control and final full suite pass; its oracle was not weakened.
- Production shape: one small concrete guard, one call, no new type/trait/error variant/suppression, shallow nesting, and comments explain the conservative policy. The recorded reuse query was rerun against the coordinator baseline index: `search_code __has_include` returned 0, scoped `search_graph` returned 28 existing symbols. Existing positive include-shadowing helpers cannot model absent headers; direct delivered-source reads confirm the new helper and caller. That baseline index has partial Rust semantics and does not index this tip, so no completeness claim is made.
- The approved repair trades caching for correctness for read-set units with detected availability probes. Comment/string matches can conservatively cost caching. Broader negative-dependency modelling and arbitrarily synthesized operator tokens remain outside this bounded fix, as recorded in design-assessment.md. When dependency capture is unavailable, the existing fresh expansion hash path remains authoritative rather than reusing a positive read-set digest.
- Portability was reviewed in source; the recorded gate ran on macOS. Windows execution and mutation coverage are unclaimed; repository AGENTS.md assigns changed-line mutation testing to draft-PR CI.

Evidence directory: `/Users/viktor/Developer/github/kache-investigations/audit-cc-cuda-adapters/investigation/pr-delivery/cc-optional-header`.
