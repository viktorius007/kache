PASS
Verified SHA: d46894130adb5033ba91c2a8fd69b0748c6f75ee; clean worktree and git diff --check; root READY binds completed gate to unchanged tip.
Evidence directory: /Users/viktor/Developer/github/kache-investigations/qa-store-transactions/investigation/pr-delivery/store-publication-rollback-001.
Commit split: test-only f60f84a6b06b5c8665c3b4e8e19c6787033170a8 then production-only d46894130adb5033ba91c2a8fd69b0748c6f75ee; only store.rs and store/tests.rs, no generated artifacts.
Old red: red.log has 2 passed/1 failed at peer-blob survival after exact INSERT-ABORT; amendment removes only two needless setup borrows, leaving trigger and behavioral oracle unchanged.
New green: green.log has 3 passed/0 failed: failed republication, successful stranded replacement and existing republication/removal-cleanup race control.
Gate: delivery.json and gate-command.json record run-gate.py → build-slot.py just check exit 0; gate.log:5232 root suite 4381 passed/0 failed/14 ignored; :7231 store suite 570 passed/0 failed/2 ignored; completed workspace checks.
Ordering: put_with_compile_time_policy store.rs:2871–2924 holds one transaction across reference/mapping updates, final entries INSERT, metadata replacement and commit; SQL statement errors occur before filesystem metadata replacement.
Cleanup: existing removal write-lock/republication and per-blob adoption guards remain intact; targeted cleanup race passes. Peer survival plus mapping/refcount equality is asserted at tests.rs:3007–3022; successful replacement/removal control at :3027–3050 passes.
Oracle/portability: tests.rs:2954 varies missing/existing metadata; real generated SQLite trigger owns the observed error, independent old/peer payloads expose wrong-generation removal; metadata equality and stranded cache miss strengthen it. Temporary stores, no host/global mutation or new platform-specific code.
Shape/PR: narrow statement reordering plus WHY comment, no new production abstraction/API/schema/migration; test/fix scopes preserved; 52-word body links defective baseline and limits claim to SQL statement failure before commit.
Findings: none blocking. Manufactured stranded-state provenance and unproven commit/crash/I/O recovery remain documented outside the PR; no broad recovery claim. CI mutation testing remains required before landing, not run locally.
