Independent branch: fix/ephemeral-ci-002 from 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. Queue dispatch recorded before execution. E1 commits are absent and its tested tip/artifacts remain unchanged.

Every compile/test/gate invokes the included run-check.py, then coordinator build-slot.py. Its private CARGO_TARGET_DIR is /Users/viktor/Developer/github/kache-prs/ephemeral-ci-001/target, owned exclusively by this agent and reused sequentially after E1 completed. Original red/green runs used global isolated HOME/config/cache/TMPDIR under the lexical /tmp alias outside Cargo workspaces (run-check-isolated.py). Final gate retains normal toolchain HOME/TMPDIR per the updated common brief, with isolated Kache config/cache and per-CLI fixtures; KACHE_PR_TEST_THREADS=1 bounds libtest concurrency. No profile overrides are added; build-slot clears self-wrapping and reuses the Cargo integration binary.

Red, untouched production: run-check-isolated.py red.log cargo test --locked --test filesystem_remote_test concurrent_bulk_sync_clients_hydrate_shared_store_without_errors -- --exact
Green: run-check-isolated.py green.log cargo test --locked --test filesystem_remote_test concurrent_bulk_sync_clients_hydrate_shared_store_without_errors -- --exact
Final full gate: run-check.py gate.log just check
Six unchanged native controls: run-check.py sandbox-control.log cargo test --locked --test fallback_recovery_test

Driver-only first gate failure and temporary adapter trace are preserved in gate-sandbox-preflight.log, sandbox-control-cold.log, sandbox-control-retry.log, sandbox-diagnostic.log, diagnostic-adapter.patch and lsof-latency.json. Diagnosis and confirmed normal-environment control are recorded in gate-environment.md. The adapter was restored to exact HEAD before the passing six-test control and final full rerun.

Regression oracle: seed 24 independently keyed real rustc artifacts with deterministic incompressible payload, populate authentic filesystem remote packs, drain producer daemon; clean and warm syncs each commit 24 entries. Three trials start four real CLI processes at a barrier, sharing one node-local store with distinct runtimes. Every process must exit 0 and each fresh shared store must have 24 committed index entries. Baseline fails at the nonzero command-exit assertion after import move/missing-file/size-mismatch errors. The fix passes all 12 overlapping commands. No mock replaces extraction/import and no test oracle was weakened.

Exclusive final rerun: unchanged e8df9b2a6e6165de82592d73c711ddf1219c768f, run-check.py gate.log just check; KACHE_PR_EXCLUSIVE_GATE=1 and KACHE_PR_TEST_THREADS=1 in driver environment. Normal HOME/TMPDIR retained, runtime unset. See exclusive-gate.txt.
