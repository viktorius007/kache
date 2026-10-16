STATUS: READY
COMMIT: 1e43f94a21eef0a773dd9382881ca22321909441
CHANGED: 2
OPEN: 0
BLOCKERS: none
---

Regression commit: 4fc08c5f8d4eee122fba79bf2a293f7a7ae156fb (test-only, deliberately red). Repair commit: 1e43f94a21eef0a773dd9382881ca22321909441. Branch fix/benchmark-guardrails-001 starts independently at origin/main 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9.

The existing exception cleanup already stops the measurement group. A nonzero leader exit raised its error outside that scope. The fix moves that error into the existing scope; it introduces no production helper, policy copy or new abstraction and leaves successful measurements and timeout/grace sequencing intact. Graph reuse query run_measurement returned the existing owner (one hit), which is reused.

Gap search executed: rg -n 'run_measurement|process.*cleanup|child.*process|killpg|failed.measurement' scripts/bench/tests. Nearest existing test: scripts/bench/tests/test_short.py:93-123. It checks a childless failing command and mocked timeout cleanup, leaving real surviving workers after a nonzero exit uncovered. No repeated audit was performed.

Oracle: test_failed_measurement_stops_child_processes starts a real worker that holds the test pipe open until it stops. The worker signals readiness before its leader exits 4. After the helper raises, the test closes its own write handle and requires pipe EOF while the test process remains alive. This observes the actual resource release, not a killpg mock or a marker-delay correlation. No boundary doubles; real pipe, process, process group and subprocess error are used. Cleanup in finally stops a baseline survivor.

Discriminator: a leader exiting 4 while its ready worker holds the pipe. Red run fails at 'failed measurement left its child alive holding the pipe' (red.log). Green: all 59 benchmark Python tests pass (green.log). The same suite's successful-exit, childless error, timeout and grace controls remain green.

Targets/obligations: the public helper must retain CalledProcessError with exit 4 while releasing surviving group members on failure; success remains accepted, and timeout/grace cleanup remains unchanged. Actors: instrument failure and surviving workers. Invariant: no measurement worker keeps this fixture pipe open after failure. Boundary: successful zero exit versus failed nonzero exit. Never obligation: do not let failed-cell workers retain resources into subsequent subject cells. Audience: benchmark operators/release confidence; failure cost: lingering CPU/memory/I/O work or late writes. Specific regression: nonzero error raised outside the cleanup scope.

Vacuity checks: the baseline reaches the exact dangerous state and fails at the resource-release assertion; error code is pinned independently; readiness prevents an unstarted worker from providing incidental EOF; EOF cannot occur while the live worker retains its inherited writer; successful/failed/timeout cases are represented across the existing suite. Self-check KEEP, pending independent root review and CI. No local cargo-mutants; mutation ownership remains in CI.

Full gate uses build-slot.py just check with private COW target under this delivery directory and RUSTC_WRAPPER cleared. Runtime remains unset so fixture cache overrides control runtime isolation. Only scripts/bench/engine.py and scripts/bench/tests/test_short.py are committed. Root owns publishing and independent review; agent retains CI follow-up.

Final tip verification: just check completed with exit 0 (runtime completion for session 10129; gate.log). After that completion, all 59 Python benchmark tests passed again at unchanged final tip 1e43f94 (green.log). Working tree clean; only the requested two commits above origin/main.
