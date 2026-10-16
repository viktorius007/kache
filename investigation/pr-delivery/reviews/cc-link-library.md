PASS
SHA: 2fd65704731782ebdcda6d099ea044ad1690a5ee (read-only checkout, clean tree; matches delivery.json and gate-repaired-sha.txt).
Scope: re-review of the sole forwarded-response blocker, preserving previous source/body findings; reused saved proofs without repeating the audit or workspace gate.
Red: red.log reproduces named-archive stale exit11 versus23 before repair; red-forwarded-response.log reproduces wl-rsp/changed exit11 versus23 against old8c0cd723, as documented in the delivery record.
Green: green-repaired.log records all10 cc_passthrough_args_test tests passing, including real -Wl,@file and -Xlinker @file archive mutation.
Gate: fresh just check completed exit0; delivery.json, gate-repaired-exit.txt and gate-repaired-sha.txt bind gate-repaired.log to this exact final tip. Named-library/response refusal units and real regression pass within it.
Commits: test-only0824639eac73fdc7c9895af1c0d63093f7e70706 followed by production-only2fd65704731782ebdcda6d099ea044ad1690a5ee; three source/test files, clean diff check and no generated artifacts.

Findings: none blocking; previous forwarded-response finding is repaired.
- src/compiler/cc.rs:6824 now produces the same top-level and -Wl comma-forwarded token stream for both refusal predicates. At6831 it checks response tokens before named-library selection. Thus direct @file, -Wl,@file, grouped -Wl tokens and -Xlinker @file all reach the exact response refusal without parsing the file contents.
- The response unit table asserts the single expected Unsupported reason for all four spellings. The real-compiler regression executes four independent11/23 phases for both forwarded response forms, retaining runtime assertions before telemetry. The old failure occurs at actual executable content, rather than a bookkeeping assertion.
- Explicit positional archives retain miss/hit/miss/hit across replacement. Every untracked-selection/default case requires four passthrough events and zero indexed artifact entries when an index exists. Gathering event results until after all runtime phases strengthens the behavioral red without changing these exact control oracles.
- Joined/separate -l, -Wl,-l/--library and -Xlinker selections retain the original refusal coverage. Positive controls preserve explicit .a/.o, comma-containing object filenames, uppercase -L and -Wl,-rpath admission. Default link passthrough is unchanged.
- Wrapper refusal remains before key lookup/publication at wrapper.rs:1933, so existing entries cannot bypass the repaired guard; explicit-input keying behavior is unchanged.
- The49-word PR body links the actual defective baseline cc_link_file_inputs lines and states cause, refusal tradeoff, retained explicit-file caching and validation. Two-commit separation and exact-tip full gate meet delivery requirements.
- Repair uses the existing method and lazy token iteration, without new APIs/types/helpers, platform-specific calls or global environment mutation. Runtime proof covers macOS Apple Clang/ld/ar in the Unix integration suite; broader linker discovery and unexecuted platforms remain explicitly scoped outside this confirmed named-library defect.
