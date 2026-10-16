PASS
Reviewed exact clean tip f58c9ed2fee7338a6a1af9e53ef13152d1dd37ae; no source edits or repeated audit/gate.
Evidence: /Users/viktor/Developer/github/kache-investigations/audit-planner-service/investigation/pr-delivery/planner-service-stale-lease/{delivery.json,red.log,green.log,gate.log,oracle-notes.md}.
Test-only 3a17e158873fbe875e7e348adff989e01d4f3b9d precedes fix; only scheduler.rs and test_runner.rs changed; 52-word body links pinned baseline predicate.
Baseline regression earns red after real child exit and independent marker-release proof: zero keyless permits where one is required.
Targeted green: 85 scheduler tests and 16 runner tests; live child-held two-slot reuse plus stale keyed/keyless admission and exact runner Schedule all pass.
Delivered exact-tip just check exits 0; 77 summaries, root 4382 passes/zero failures/15 ignored, nested_runners_and_compiles_do_not_deadlock passes.
Source scheduler.rs:687 retains canonical-parent equality and requires slot_is_held == Some(true); missing/error/free markers cannot bypass admission.
Source scheduler.rs:788 uses existing nonblocking shared OS probe without creating markers; transient shared probes do not identify each other as owners.
All consumers reviewed: keyed begin_miss, keyless_compile and test_runner::plan; keyed flight joining and existing reserve/pressure behavior retained.
Foreign live markers remain excluded, same-store symlink aliases retain coverage; portable process fixture uses actual locks and exits before stale assertions.
Findings: none. Unsupported-platform runtime not independently exercised; CI mutation checks remain a landing requirement.
