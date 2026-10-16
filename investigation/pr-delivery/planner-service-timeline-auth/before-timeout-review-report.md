STATUS: DONE
COMMIT: 657bf608c3fb91105ba86d5010a4b2bf95f68422
CHANGED: 2 files
OPEN: independent root review and CI mutation testing
BLOCKERS: none
---

Timeline uploads now resolve credentials through the existing planner_auth::bearer function. Previously push_timeline read only PlannerConfig.token, omitting available workload and trusted-session credentials. Explicit-token priority, safe transport and trust rules remain owned by the shared resolver. Authentication has the existing upload timeout as its deadline; the established upload client timeout remains unchanged. No new authentication design, API or production helper was added.

The test-only commit is `251d8c744b89c455b2531d98c8bc29953a9dc8c2` and the fix commit is `657bf608c3fb91105ba86d5010a4b2bf95f68422`, independently based on `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. The production repair adds two resolver lines and switches the existing bearer attachment to their result. The worktree is clean; [delivery.json](delivery.json) and [dispatch.json](dispatch.json) record exact ownership, commits and gate evidence.

| Criterion | Executed evidence |
| --- | --- |
| Ordinary automatic credentials reach actual timeline uploads | [red.log](red.log) fails on a null Authorization header despite available synthetic Actions credentials; [green.log](green.log) verifies the exact obtained bearer and stored-session report |
| Explicit bearer wins over available automatic credentials | The CLI control posts a distinct explicit bearer with zero Actions requests, before the red assertion and after the fix |
| Missing credentials retain advisory behavior | The CLI control posts no bearer, reports the fixture 401, exits 0 and never reports a stored session |
| Correct Actions token request and production body | Fixture checks runtime bearer, API version and planner-base audience; decodes received zstd body and verifies the independent session ID |
| Preserve service-refusal and existing auth rules | Relevant timeline-client and planner-auth suites pass, including compressed upload, 413 reporting and existing trusted-session/workload controls |
| Required full workspace gate | [gate.log](gate.log): `CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check` exits 0 at `657bf608c3fb91105ba86d5010a4b2bf95f68422` |

Targeted summaries: `test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.14s
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 4388 filtered out; finished in 0.01s
test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 4378 filtered out; finished in 0.17s`. [gate-summary.txt](gate-summary.txt) records workspace test summaries. The required gate runs formatting, workspace/all-targets clippy with warnings denied, test-resource checks and workspace tests. The initial shared-module dead-code compile diagnostic is preserved in [fixture-compile-error.log](fixture-compile-error.log); it is not the behavioral red.

[oracle-notes.md](oracle-notes.md) records independent expectations, fixture discriminators, process isolation, reuse queries and cleanup. Each CLI child gets a cleared environment and fixture-only HOME/config/cache/Kunobi state. HTTP fixtures bind loopback only, use synthetic tokens and enforce exact headers; no real credentials, external service calls, installed config or live caches are used. No process-global environment is mutated. Servers and children have scoped teardown and the child execution is bounded.

The saved [timeline-auth-replay.json](../../timeline-auth-replay.json), [timeline_auth_red.json](../../timeline_auth_red.json), [timeline_auth_control.json](../../timeline_auth_control.json) and [timeline_workload_auth.py](../../probes/timeline_workload_auth.py) remain unchanged. This delivery ports their transport proof, without repeating the audit. The new CLI regression directly proves Actions auth plus explicit/missing controls; trusted-session authentication is reused through the established resolver and existing unit suite, without claiming a newly executed end-to-end login flow.

Shape review: existing shared resolver and CLI fixture command are reused; local test handlers model the Actions and timeline HTTP contracts. No production function/type/trait/module or visibility is added. New regular regression stays within 100 lines. Local mutation testing was not run; root's independent review and CI mutation/cross-platform lanes remain required before landing.
