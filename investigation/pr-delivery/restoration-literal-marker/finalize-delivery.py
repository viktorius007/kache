import json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
worktree=pathlib.Path('/Users/viktor/Developer/github/kache-prs/restoration-literal-marker')
def git(*args):return subprocess.check_output(['git',*args],cwd=worktree,text=True).strip()
assert sys.argv[1:] == ['0'], 'Only finalize after the full gate exits zero'
assert not git('status','--porcelain'), 'Do not declare a dirty tip ready'
fix=git('rev-parse','HEAD');test=git('rev-parse','HEAD~1');base=git('rev-parse','HEAD~2')
files=git('diff','--name-only',base,'HEAD').splitlines()
gate=f'env CARGO_TARGET_DIR={worktree}/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check'
body='''In [`rewrite_depinfo_content_with_prefixes_and_sentinel`](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/crates/kache-store/src/link.rs#L1993-L2080), literal `__kache_*` dependency names were mistaken for cached root markers, so Cargo and Make could skip input changes. Encode generated markers with a NUL prefix that filenames cannot contain, and bump the cache-key version to discard ambiguous entries. Regressions `depinfo_rewrite_preserves_literal_marker_dependencies`, `rustc_depinfo_rewrite_preserves_literal_marker_dependencies` and `v3_extract_rejects_ambiguous_v32_depinfo` pass; `just check` passes.
'''
assert len(body.split())<=75
(root/'pr-body.md').write_text(body)
record=dict(id='restoration-literal-marker',branch=git('branch','--show-current'),worktree=str(worktree),test_commit=test,fix_commit=fix,title='Preserve literal dependency paths in cached dep-info',body_file=str(root/'pr-body.md'),base_sha=base,gate_command=gate,gate_exit=0,red_log=str(root/'logs/red.log'),green_log=str(root/'logs/green.log'),gate_log=str(root/'logs/gate.log'),changed_files=files)
(root/'delivery.json').write_text(json.dumps(record,indent=2)+'\n')
report=f'''STATUS: READY
COMMIT: {fix}
CHANGED: {len(files)} files
OPEN: 0
BLOCKERS: none
---

Test-only commit: {test}. Production fix commit: {fix}. Both branch directly from {base}; no sibling change is included. The owned worktree is clean. The production commit adds four lines to the existing shared dep-info prefix transform and bumps CACHE_KEY_VERSION 32→33. Generated markers now carry a NUL prefix unavailable to real filenames; expansion removes it before compiler-facing dep-info is materialized. Existing ambiguous entries get different cache keys.

The two focused regression tests failed at exact restored-dependency assertions on untouched baseline production source (logs/red.log). After repair, the store suite passed: 570 unit tests, 2 pre-existing ignored; 5 property tests; two one-test integration suites; one isolated telemetry child. The full workspace gate `{gate}` exited 0 at the final tip (logs/gate.log), including formatting, clippy, resource-guard checks and all workspace tests. The legacy-v32 pack test also failed with baseline production, then passed with the precise incompatible-schema error and no published output (logs/schema-red.log and logs/schema-green.log). CI owns mutation testing; no local cargo-mutants run was performed.

The previous full gate (logs/gate-second.log) and its exact sandbox integration retry (logs/fallback-retry.log) failed in an existing denied-server fallback assertion outside this diff. The native policy control passed. A subsequent exact compiled test passed unchanged against both the proven baseline binary and the restored final binary, including denied and allowed assertions (logs/sandbox-exact-baseline-control.json). The final binary bytes were restored in finally and its SHA-256 was rechecked. Standalone lsof and CLI diagnostic results are in logs/sandbox-discovery-diagnostic.json; they do not establish the cause of the intermittent failures. No timeout, oracle or unrelated source change was made. The final full gate result above was obtained after these controls.

The regression oracle preserves literal dependency tokens and environment values exactly while independently relocating actual producer roots to consumer roots. Exact restored text also excludes private NUL bytes. Existing encoded-fixture tests were updated to the new private representation without weakening their compiler-facing behavior assertions. Details are in verification-notes.md. No new helper, abstraction, visibility change, test hook, suppression or unrelated cleanup was introduced. Root independently reviews and publishes; no PR has been pushed by this agent.

Original investigation source, fixtures and red evidence remain unchanged. delivery.json contains the branch, both commits, baseline, commands, logs, changed files and short PR title/body for root publication.
'''
(root/'report.md').write_text(report)
print('READY',root/'delivery.json')
