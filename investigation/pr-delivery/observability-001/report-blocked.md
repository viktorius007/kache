STATUS: BLOCKED
COMMIT: bbe72d7a4f0f219dc6a7c6a0ba59311510b79563
CHANGED: 2 source/test files; 2 separate commits
OPEN: 1 gate control
BLOCKERS: unchanged macOS sandbox fallback integration assertion keeps required full gate nonzero
---

The regression and minimum redaction fix are complete on independent pinned main. The test-only commit is 17ec179fc72c9acfc4b94ee58f19fc5ed2ec3f87; the production fix is bbe72d7a4f0f219dc6a7c6a0ba59311510b79563. The corrected baseline assertion demonstrates leaked skipped/passthrough roots specifically; all 100 report tests pass. The fixture-only discriminator fails on empty versus sensitive roots, and the restored regression passes. The real compiler proof confirms bypass and trace roots are redacted, an ordinary report retains its root, and summary fields remain identical.

The full just check gate passed formatting/clippy, root tests and 116 CLI integration tests before failing sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server. Both focused retries failed the same direct-versus-fallback assertion. Original logs are preserved. The optional PID probe has a 200 ms deadline; isolated listener measurements and native policy checks expose a concrete cold-start timeout path, but no instrumentation of the failed production run established its exact cause. See sandbox-gate-diagnosis.md, evidence/sandbox-diagnostic.json and evidence/lsof-timing.json. No unrelated source repair or test weakening is included.

The contract requires full just check exit 0 at the final PR tip before publication (coordinator/investigation/pr-delivery/common-brief.md); this handoff is explicitly not READY. Parent coordination of a quieter interval or fallback-owner diagnosis is pending. No PR was published. observability-003 source, tip and evidence remain unchanged; only its same-owner private target was reused sequentially.

All scripts, proof JSON, stdout/stderr and candidate short description are persisted. The worktree is clean. Once the gate passes, the prepared finalize script /Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/pr-delivery/observability-001/finalize.py writes the final READY report and metadata without a source change.
