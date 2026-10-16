STATUS: READY
COMMIT: 40695fbd03cb626fbb5c0391a7757d5da4b7ffc3
CHANGED: 5 files
OPEN: 0 confirmed defects; independent review and CI mutation lane follow
BLOCKERS: none
---

Diagnostic presentation now participates in Rust cache keys. The parser canonicalizes attached and separated value flags and keeps their occurrence order; the key always folds a diagnostic version tag so legacy entries cannot serve implicit-default requests. The production change is confined to `src/args.rs` and `src/cache_key.rs`.

The regression warms human diagnostics, requests JSON, checks every stderr line is JSON and finds the expected warning, then requires a repeated JSON local hit with the same key. A direct rustc control independently produces that warning as JSON. Its discriminator is the format switch with unchanged source: baseline production failed at `JSON request replayed human diagnostics` (exit 101), while the repaired suite passes. Empty stderr cannot satisfy the warning assertion. The red test blob is unchanged by the later prediction-control corrections.

`cargo test --test input_prediction_test --test metadata_streaming_test` passed at this commit: 37 input-prediction tests and 2 metadata tests, zero failures. Key tests exercise all four diagnostic options, distinct values, attached/separated equivalence, opposite repeated-option order and unchanged verbose behavior. Two existing prediction controls now hold diagnostic argv constant and select pre-pass discovery through fixture configuration; their key-comparison assertions remain intact.

The full `just check` gate passed (exit 0) through the bounded build wrapper at this commit; `gate-exit.txt` and `gate.log` record the result. The final working tree is clean. The first gate exposed the second outdated format-sharing control; `gate-first.log` preserves that failure. Local mutation testing is excluded by the common brief; CI owns that evidence. No mutation-coverage verdict is claimed.

Shape review: no new production function or indirection; diagnostic flag names have one definition, key folding reuses `fold_field`, and fixture files/config/HOME/cache/output are isolated. Rust toolchain identity is preserved. Codebase-memory reuse search `diagnostic format cache key` returned five ranked hits with partial/saturated coverage; existing key helpers are reused, while the prior integration helper filters JSON and cannot observe the raw human stream. Independent review remains the next handoff.

Delivery metadata includes runnable red/green/gate commands and per-path evidence. The deliberately red test commit is 34bcd792cea2ab8e5c78d3e8a25696a1e4caf616; the separate production fix commit is 40695fbd03cb626fbb5c0391a7757d5da4b7ffc3. Root owns independent review and publication.
