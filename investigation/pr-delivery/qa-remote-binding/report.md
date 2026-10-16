STATUS: DONE
COMMIT: b06aba292b0cabb5d47fa0ad6a7c0a77b31206a1
CHANGED: 1 file
OPEN: CI mutation testing and independent root review
BLOCKERS: none
---

Exact remote restore now binds an otherwise valid pack to the requested cache key and crate before publication. `download_entry_observed` supplies the existing `ExpectedEntryBinding`; the shared extractor checks identity before renaming the entry into place. The digest is optional for exact restores and remains required by packed-prefetch callers. The mismatch diagnostic names expected and actual identities. No Store migration or cross-shard change is included.

The deliberately red test-only commit is `8abea96f17c48f425d733da01d51803b3c817fa8`. The production fix commit is `b06aba292b0cabb5d47fa0ad6a7c0a77b31206a1`. Only `src/remote_layout.rs` changed, and the worktree is clean. [delivery.json](delivery.json) carries exact commit, source, body and gate references for root publication.

| Criterion | Executed proof |
| --- | --- |
| Reject a valid pack under another requested key | [red.log](red.log): named acceptance assertion failed on untouched production; 0 passed, 1 failed |
| Preserve correct exact restores and independently reject key/crate mismatches | [green.log](green.log): new request-table regression passed with matching, key-only and crate-only fixtures |
| Preserve packed-prefetch digest enforcement | [green.log](green.log): matching digest, valid-format wrong digest, key/crate mismatch and malformed digest controls passed |
| Full local gate at fixed tip | [gate.log](gate.log): `CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check` exited 0 at `b06aba292b0cabb5d47fa0ad6a7c0a77b31206a1` |

The targeted layout suite passed all 27 tests. Full workspace suite summaries are in [gate-summary.txt](gate-summary.txt). The final gate includes workspace/fuzz formatting checks, workspace/all-targets clippy with warnings denied, test-resource guard checks and workspace tests. Build-slot.py used a private target with two Cargo/test threads. CI owns mutation testing; no local mutants invocation or publication occurred.

[oracle-notes.md](oracle-notes.md) records the request-table and digest discriminators. The network double preserves wrong-object routing; production archive extraction, identity validation and publication remain exercised. Independent expectations come from test-owned request identities and fixture bytes. The saved original compiler proof established the real wrong-result consequence and was reused without repeating the audit. Fixtures use temporary stores and introduce no process-global state, host configuration, visibility hooks or live cloud calls.

Shape review: reuse search found existing `ExpectedEntryBinding` and `extract_entry_pack_until` and both are reused; there is no new production function, trait, variant, module or duplicate validator. The production diff is limited to the expected binding, optional prefetch digest and mismatch diagnostic; no unrelated cleanup. The new test stays below 100 lines and within the module's existing privacy boundary. Existing extraction's prior size is not broadened into a refactor. Root's independent review and CI mutation lanes remain required before landing.
