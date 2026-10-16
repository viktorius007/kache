STATUS: DONE
COMMIT: 31f6ac2747887dd9184dfab36f14e80a76e5008f
CHANGED: 2 files
OPEN: 0
BLOCKERS: none
---

The branch is independent from cli-config-001 and based directly on 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. It contains test-only commit 47949f8d0f635161769fcd24326ecf1b6cc8e855, followed by production repair 31f6ac2747887dd9184dfab36f14e80a76e5008f. The worktree is clean. Original CLI investigation and proof artifacts remain unchanged; queue dispatch records the handoff to this author.

`migrate` now uses the existing Cargo wrapper plan, wrapper editor and sccache program detector. It changes the complete configured sccache executable value to PATH `kache` rather than replacing a substring inside an absolute executable path or unrelated values. The four-line production addition introduces no function, type, indirection or suppression. A graph reuse query returned the three existing helper definitions, with partial Rust graph coverage acknowledged and source confirmation recorded in oracle-notes.md. Function signatures and other callers remain unchanged.

The real Cargo regression first builds through a working absolute pass-through sccache script, invokes the actual `doctor --fix`, then builds again through the configuration it wrote. The test places the authoritative Kache binary on the disposable PATH, and independently parses the resulting wrapper setting. Only process discovery is stubbed, preventing host sccache observation or shutdown while preserving executable selection. Baseline red.log shows the first build succeeded and the second failed because old-wrapper/kache did not exist. The configuration control also failed because global replacement changed an unrelated env value. After repair, all five doctor-fix tests passed (green.log), including the existing bare-name and custom-CARGO_HOME controls and new other-wrapper/no-wrapper cases.

Full `just check` exited 0 at the final fix SHA through gate.sh and the coordinated build-slot wrapper using this agent's exclusive reused target. Formatting, clippy with warnings denied, resource-guard checks and all workspace tests passed (gate.log). The binary suite passed 4,381 tests with 14 ignored, and the full CLI integration suite passed 118 tests. The saved gate-command.json records underlying argv, workdir, completed exit and exact-tip provenance for publication.

The original external real Cargo proof was replayed at the committed candidate binary under short lexical /tmp fixtures with isolated HOME/CARGO_HOME/config/cache and disabled host configuration. Cargo check before and after migration and doctor all exited 0; the selected wrapper is kache and the fixture executable exists (migration-path-evidence.json). Disposable daemon cleanup follows the repository lifetime-lock rule. oracle-notes.md records the initial unconditional stop timeout and the corrected fixture ownership check; both executions kept the Cargo oracle intact.

The PR body is 42 words and links the defective baseline function. Independent review, cross-platform and mutation validation remain with the coordinator and CI. No local mutation or installation command was run, and no user home/config/cache/service was edited.
