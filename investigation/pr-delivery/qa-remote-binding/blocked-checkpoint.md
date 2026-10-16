STATUS: BLOCKED
COMMIT: none (baseline HEAD only)
CHANGED: 0 PR files
OPEN: test-only regression commit, narrow production fix commit, red/green tests, full just check, delivery metadata and PR body
BLOCKERS: root reported a second runtime content-filter error and explicitly directed checkpoint-only work and ownership relinquishment
---

Write ownership of `/Users/viktor/Developer/github/kache-prs/qa-remote-binding` is relinquished to root. This checkpoint is the only file written during the repair dispatch. No production/test edit, patch, test/fix commit, compile, cargo test, just check, or new experiment was performed before root stopped this dispatch. No content-filter error was visible in this agent's own tool results; the blocker is root's reported runtime error and explicit stop instruction.

Current checkout state (read-only commands executed for this checkpoint):

```
$ git rev-parse HEAD
exit: 0
4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9

$ git branch --show-current
exit: 0
fix/qa-remote-binding

$ git status --short
exit: 0

$ git diff --stat
exit: 0

$ git log -3 --oneline
exit: 0
4ee0f9e perf: seed adaptive incremental state from emitted dep-info (#1497)
b0c77d4 fix: prevent native-library false hits and repair build-script pins (#1496)
d21afcc fix(predictions): find a tree memo by its full stamp on Windows (#1495)

```

Preserved proof: `/Users/viktor/Developer/github/kache-investigations/qa-remote-validation/investigation/report.md`, `findings.json`, `remote-binding.case.json`, `binding-swap.execution.txt`, `binding-valid.execution.txt`, `binding-corrupt.execution.txt`, `probe_support.py`, and `probe_remote_validation.py`. These establish exact GET of requested key A serving a complete generated valid key B pack, Kache accepting/importing B under A, and a directly compiled consumer returning 29 instead of source-owned expected 11. Correct-object and malformed-object controls pass. Source baseline is `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9` and no reinvestigation is needed.

Existing causal source context: `src/remote_layout.rs:216` calls `extract_entry_pack_until(..., None)`. `ExpectedEntryBinding` at lines 85-89 already owns expected key/crate/digest. The extractor at lines 727-740 checks key/crate only if that binding is supplied. Packed-prefetch supplies its expected binding at lines 432-440. `Store.import_downloaded_entry` verifies artifact content and commits under the requested key without identity comparison, so validation must happen before extractor publication/import.

Unimplemented narrow continuation approach: make the binding's metadata digest optional, supply expected key/crate with no digest for exact downloads, retain a digest for packed-prefetch, and keep both identity checks before destination publication. This reuses the existing validator; the graph query found `ExpectedEntryBinding` and `extract_entry_pack_until` rather than an unrelated duplicate validator. Do not broaden into Store migration or the separate cross-shard defect. Preserve packed-prefetch digest enforcement with a valid-format wrong-digest control.

Repository regression context: `src/remote_layout.rs` has `populated_entry()` (lines 1767-1789), `populated_cc_entry(cache_key, crate_name)` (1791-1818; supports valid generated key/crate identities), `memory_backend()`, and `create_entry_pack_zstd()`. Existing `download_entry_extracts_a_stored_pack` at 1849-1873 tests matching identity; existing CC download fixture around 2012-2044 exercises a valid key and crate containing a period. A minimal regression can generate a valid pack and place it under another requested object key, then require the exact downloader's identity-mismatch error and absent destination. Independently vary only key and only crate to cover both sides of the rejection; do not use a corrupt payload as the mismatch oracle. Existing packed-prefetch binding table at 1215-1294 checks key and crate independently, and its diagnostics currently use the `packed-prefetch cache-key or crate binding mismatch` wording. Any shared diagnostic change needs the test expectations adjusted coherently.

Required unfinished steps: test-only regression commit that fails at its identity assertion on baseline, narrow repair commit, targeted green tests/control checks, final `just check`, then delivery.json/report.md/pr-body.md and READY to root. Every compile/test/gate must use `python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py <command>` and a private target. No private target exists from this agent. Proposed path was `/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target`; root was informed required builds would create several GiB. No local mutation runs, installs, publication, real-cache fixtures, or changes to original investigation evidence are authorized here.

Read delivery common brief and repository AGENTS.md. Coding/testing/verification/codebase-memory skills were loaded in the preserved context. The plain `/Users/Shared/.claude/skills/commit-standards/SKILL.md` path is absent; the listed installed package was read at `/Users/Shared/.claude/skills/skill-standards/evals/files/references-point-up/commit-standards/SKILL.md`. Its green-before-commit rule is overridden specifically by the user's requested red test-only commit; final PR tip must be green. No commit has been attempted.
