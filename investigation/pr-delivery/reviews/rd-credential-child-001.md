PASS
Verified SHA: 52f94c5059975855621037381721032dc23537f9; clean worktree and git diff --check.
Evidence directory: /Users/viktor/Developer/github/kache-investigations/audit-remote-daemon/investigation/pr-delivery/rd-credential-child-001.
Commit split: test-only 3fec813d36446717b746217b2f660dc022420f7f followed by production-only 52f94c5059975855621037381721032dc23537f9; only src/remote_backend.rs changes, no generated artifacts.
Old red: red.log records cancellation leaving the helper resource locked, 0 passed/1 failed; saved probe_credentials.execution.txt records a helper surviving the remote deadline while the daemon lives.
New green: green.log has 3 passed/0 failed/1 ignored subprocess fixture; cancellation, ordinary completion, quoted arguments and configured-profile controls pass.
Gate: delivery.json records build-slot.py just check gate_exit=0 and gate_head equal to this SHA; gate.log:5252 has 4382 passed/0 failed/15 ignored and completes workspace checks; no gate rerun by reviewer.
Ownership fix: KacheCommandExecute::command_execute src/remote_backend.rs:1069 enables kill_on_drop on the Child held by output().await; parsing, profile forwarding and output conversion remain unchanged.
Oracle: :2780 child holds an actual lock; :2843 establishes WouldBlock, :2849 aborts/joins the task, :2855 probes release while caller runtime lives; :2856 cleanup happens only after the verdict is captured.
Portability/shape: std file locks are available below the repo's Rust 1.95 MSRV; fixture uses current_exe, quoted path and per-child environment, no shell/global mutation; existing shell controls retain cfg(unix). No new production abstraction or duplicate policy.
PR: 39-word body links baseline executor lines 1053–1076 and states cancellation/resource-release behavior. Tokio 1.53.1 source confirms child drop kills and Unix Reaper queues unreaped children; background reaping is best effort, immediate reaping was not independently tested.
Findings: none blocking. CI mutation testing remains required before landing; not run locally.
