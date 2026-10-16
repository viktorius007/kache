FAIL
SHA: 657bf608c3fb91105ba86d5010a4b2bf95f68422 (read-only clean checkout, matches author checkpoint/fix-sha).
Scope: independent bounded credential/timeout review; no source edits, repeated audit or gate.
Red: red.log earns missing Actions bearer on the actual production POST after explicit/missing controls have passed.
Green: green.log passes integration1, timeline7 and planner-auth17 tests, preserving explicit-token and advisory missing-auth controls.
Gate: exact-tip READY was pending when the concrete blocker was returned; no PASS claimed.
Commits: test-only251d8c744b89c455b2531d98c8bc29953a9dc8c2 followed by fix657bf608; two source/test files, clean diff check, no generated artifacts in diff.

Finding: auth resolution and the timeline POST receive separate full time allowances.
- src/timeline_client.rs:61 creates an auth deadline using push_timeout(config), but request creation/send at63/72 still uses the client's fresh full timeout set at57. No remaining-budget calculation or exhausted-deadline guard follows bearer resolution.
- Concrete failing condition: automatic credential resolution stalls until its30s upload deadline. bearer returns None at expiry, then the timeline POST starts with another30s allowance. Larger configured timeouts likewise permit two full allowances. This newly extends the advisory post-step beyond the existing upload budget and can admit a POST after the chosen deadline has already elapsed.
- planner_auth.rs:47 explicitly documents a deadline shared with the request. Existing planner_client.rs:44-53 implements that contract by subtracting auth time, refusing exhausted budgets and using request.timeout(remaining); reuse that pattern for the existing larger timeline allowance.
- Current controls check timeout arithmetic and fast auth only. A focused delayed/exhausted-auth discriminator should retain automatic/explicit/missing behavior while proving no fresh upload budget after auth; no slow runtime proof was rerun in this read-only review.

Found correct:
- Timeline upload now reuses shared planner_auth::bearer, preserving explicit token first, workload credentials next, trusted session fallback and no-prompt behavior without new auth design/API/type.
- The integration test drives fresh real CLI processes and production assembly/compression/HTTP against a local issuer/service. It checks issuer runtime bearer and base-URL audience, exact timeline Authorization, decoded session identity and service acceptance. Explicit token avoids issuer GET; missing auth preserves unauthenticated401 reporting and advisory exit0 without sent-session output.
- Controls execute before the Actions baseline red. Child environments are cleared and fixture-owned HOME/config/Kunobi/cache/runtime are explicit; synthetic unsigned token is used only locally. Servers abort after children, child timeout is bounded and kill-on-drop applies. Existing413 refusal test receives an explicit fixture token to avoid discovery traffic while keeping its refusal oracle.
- Saved17 auth controls cover transport/trust, workload priority and session refresh. The change itself does not claim a new end-to-end session-login fixture. Existing upload timeout floor/value calculations remain unchanged, but do not resolve the finding above.
- Short PR body links the actual defective baseline timeline lines and states cause, reuse and controls. Test/fix separation and portability are sound; the new test uses portable HTTP/child APIs without shell fixtures or global environment mutation.
- Baseline graph coverage is partial Rust semantics; known production files are metadata_match and the new integration file is absent from the baseline index. Exact-tip source reads establish this bounded review; no exhaustive graph claim is made.
