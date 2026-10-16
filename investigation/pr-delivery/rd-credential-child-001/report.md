STATUS: DONE
COMMIT: 52f94c5059975855621037381721032dc23537f9
CHANGED: 1 file
OPEN: CI mutation testing and independent root review
BLOCKERS: none
---

`KacheCommandExecute::command_execute` now enables Tokio's termination-on-drop flag on the credential helper command. Dropping a timed-out or cancelled output future therefore stops the helper and releases its resources. Successful command parsing, profile selection and output handling retain their existing behavior. The production repair is one line in `src/remote_backend.rs`.

The deliberately red test-only commit is `3fec813d36446717b746217b2f660dc022420f7f`; the production fix commit is `52f94c5059975855621037381721032dc23537f9`. Both start from `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. The worktree is clean. [delivery.json](delivery.json) carries the exact commits, PR body and gate references for root publication.

| Criterion | Executed proof |
| --- | --- |
| Cancellation must release helper resources while the caller runtime remains alive | [red.log](red.log): the named cancellation assertion failed on untouched production, after the ordinary-completion control passed; 0 passed, 1 failed |
| Correct cancellation and successful helper behavior | [green.log](green.log): the real subprocess resource test, quoted-argument control and configured-profile control passed; 3 passed, 0 failed, 1 ignored helper fixture |
| Full local gate at the fixed tip | [gate.log](gate.log): `CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check` exited 0 at `52f94c5059975855621037381721032dc23537f9` |

The full gate includes workspace and fuzz formatting, workspace/all-targets clippy with warnings denied, test-resource guard checks and workspace tests. Full test summaries are in [gate-summary.txt](gate-summary.txt). The build wrapper used an exclusive private target, two Cargo/test threads and no installed Kache wrapper. CI owns mutation testing; no local mutants invocation or publication occurred.

[oracle-notes.md](oracle-notes.md) describes the independent file-lock oracle, readiness handshake, ordinary completion control and failure cleanup. The child is the real Rust test executable, invoked through the production executor. A separately opened file handle proves cross-process ownership before cancellation and resource release after cancellation; no process-global environment mutation or production visibility hook is needed. The ignored helper fixture is explicitly selected by the ordinary regression and executes on every run of that regression. Standard cross-platform file locks avoid shell and PID assumptions; Windows execution remains a CI responsibility.

The saved original [credential-child.case.json](../../credential-child.case.json), [probe_credentials.py](../../probe_credentials.py), execution transcript and daemon log remain unchanged. They proved the configured S3 credential helper survived a one-second remote request deadline and later wrote a marker while the daemon remained alive. This repair reused that proof without repeating the audit or using live cloud credentials.

Shape review: existing credential command/profile tests were reused as controls. Existing store/scheduler subprocess fixtures require unrelated contracts and environment injection, so a private fixture and resource-probe helper were added inside the existing test module. No production type, function, module, trait, error variant or duplicate parser was added; no unrelated refactor is included. The new regular regression is below 100 lines. The gate completed at the final committed tip. Root's independent review and CI mutation lanes remain required before landing.
