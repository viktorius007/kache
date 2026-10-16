import json,pathlib,subprocess
D=pathlib.Path(__file__).resolve().parent
W=pathlib.Path('/Users/viktor/Developer/github/kache-prs/qa-cross-shard-singleflight')
base='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
def git(*args):return subprocess.check_output(['git',*args],cwd=W,text=True).strip()
assert (D/'gate-exit.txt').read_text().strip()=='0','just check must complete successfully before READY'
fix=git('rev-parse','HEAD');test=git('rev-parse','HEAD^')
assert fix==(D/'fix-sha.txt').read_text().strip(),'gate must refer to final fixed tip'
assert git('rev-parse','HEAD^^')==base,'separate test/fix commits required'
assert not git('status','--porcelain'),'PR worktree must be clean'
red=(D/'red.log').read_text();green=(D/'green.log').read_text();gate=(D/'gate.log').read_text()
assert 'same-key remote hit must commit to every requested store' in red
assert 'test result: FAILED. 0 passed; 1 failed;' in red
assert 'test result: ok. 3 passed; 0 failed;' in green
assert 'error: test failed' not in gate and 'test result: FAILED' not in gate
files=git('diff','--name-only',base,fix).splitlines();assert files==['src/daemon.rs','src/daemon/tests.rs','src/remote_resilience.rs']
assert git('diff','--name-only',test,fix).splitlines()==['src/daemon.rs','src/remote_resilience.rs']
assert git('diff','--name-only',base,test)=='src/daemon/tests.rs'
body=(D/'pr-body.md').read_text();assert len(body.split())<=75
prefix='CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py '
command=prefix+'just check'
commands=[{'command':command,'observed_exit':101,'head':fix,'log':str(D/'gate-attempt1.log'),'failure':'unchanged macOS sandbox preflight fixture; exact cause unconfirmed'},{'command':prefix+'cargo test --test fallback_recovery_test sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server -- --exact','observed_exit':0,'head':fix,'log':str(D/'sandbox-focused.log')},{'command':prefix+'cargo test --bin kache daemon::tests::direct_restore_same_key_commits_to_each_requested_store -- --exact','observed_exit':101,'head':base,'tracked_tests':'uncommitted regression','log':str(D/'red.log')},{'command':prefix+'cargo test --bin kache daemon::tests::direct_restore','observed_exit':0,'head':test,'tracked_fix':'uncommitted destination-key repair','log':str(D/'green.log')},{'command':command,'observed_exit':0,'head':fix,'log':str(D/'gate.log')}]
(D/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
delivery={'id':'qa-cross-shard-singleflight','status':'READY','branch':git('branch','--show-current'),'worktree':str(W),'test_commit':test,'fix_commit':fix,'title':'Publish same-key remote restores into each requested store','body_file':str(D/'pr-body.md'),'base_sha':base,'gate_command':command,'gate_exit':0,'gate_head':fix,'red_log':str(D/'red.log'),'green_log':str(D/'green.log'),'gate_log':str(D/'gate.log'),'changed_files':files,'oracle_notes':str(D/'oracle-notes.md'),'original_proof':str(D.parent.parent/'cross-shard-singleflight.case.json'),'mutation_testing':'CI only; not run locally'}
(D/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
summary='\n'.join(line for line in gate.splitlines() if line.startswith('test result:'))
(D/'gate-summary.txt').write_text(summary+'\n')
(D/'report.md').write_text(f"""STATUS: DONE
COMMIT: {fix}
CHANGED: 3 files
OPEN: CI mutation testing and independent root review
BLOCKERS: none
---

`handle_remote_check_started_at` now scopes the existing singleflight coordinator to the validated expected entry directory. A same-key hit includes publication into the requesting store, so another configured store runs its own import instead of receiving the first store's answer. Equivalent requests for the same store still coalesce. The bounded coordinator, inner download guard, request deadlines and import path are retained.

The deliberately red test-only commit is `{test}`; the production fix commit is `{fix}`. Both start from `{base}`. Only `src/daemon.rs`, `src/daemon/tests.rs` and `src/remote_resilience.rs` changed, and the worktree is clean. [delivery.json](delivery.json) carries exact commit, body and gate references for root publication.

| Criterion | Executed proof |
| --- | --- |
| Each same-key remote hit must commit to its own requested store | [red.log](red.log): hit responses occurred but the follower store had no committed row; the named assertion failed on unchanged production, 0 passed/1 failed |
| Main and shard destinations publish regardless of leader order | [green.log](green.log): the new two-store regression passed both orders and checked committed rows plus exact fixture artifact bytes |
| Same-store singleflight survives equivalent wire requests | [green.log](green.log): the strengthened one-GET coalescing control passed with explicit main shard_dir and a dot-component entry-directory alias |
| Direct restore without remote listing remains correct | [green.log](green.log): existing unknown/positive/stale-miss knowledge controls passed |
| Full local gate at fixed tip | [gate.log](gate.log): `{command}` exited 0 at `{fix}` |

The targeted direct-restore suite passed all 3 tests. Full workspace summaries are in [gate-summary.txt](gate-summary.txt). The final gate includes workspace/fuzz formatting, workspace/all-targets clippy with warnings denied, test-resource guard checks and workspace tests. The bounded build wrapper used two Cargo/test threads and an exclusive private target. CI owns mutation testing; no local mutants invocation or publication occurred.

[oracle-notes.md](oracle-notes.md) records overlap, independent expectations, alias controls and reuse searches. The existing network double blocks a real in-flight GET; production validation, singleflight, download joining, extraction and Store publication remain exercised. The readiness handshake and one follower poll make the overlap deterministic. Store rows and exact artifact bytes establish the publication contract independently of response booleans, meta.json files or GET counts. Fixtures introduce no process-global state, live cloud calls, host configuration or new production visibility.

The saved original [cross-shard-singleflight.case.json](../../cross-shard-singleflight.case.json), [probe_remote_validation.py](../../probe_remote_validation.py), concurrent/reverse/socket execution transcripts and sequential/same-store controls remain unchanged. They proved the false hit through real socket requests, including reversed leadership. This delivery reused that evidence without repeating the audit. Fixture setup corrections are preserved in [fixture-compile-error.log](fixture-compile-error.log) and [fixture-artifact-path-error.log](fixture-artifact-path-error.log); neither is counted as the behavioral red proof.

Shape review: graph search found existing direct-restore tests and backend helpers and they are reused. No new production function, type, trait, variant, module or duplicate validator is introduced. The production diff changes the coordinator key from String to native PathBuf with a borrowed Path claim parameter, adapts its existing primitive tests mechanically, and passes the validated destination without lossy conversion. It documents the publication invariant; no unrelated refactor. The new regression remains below 100 lines inside the existing private test module. Path validation precedes the claim, so identity is based on the daemon's destination rather than raw wire spelling. Windows execution and mutation discrimination remain CI responsibilities. The first full gate failed in the unchanged macOS sandbox-preflight fixture; the focused test passed and the required full gate was rerun without source changes. [gate-attempt1.log](gate-attempt1.log), [sandbox-focused.log](sandbox-focused.log) and [gate-diagnostics.md](gate-diagnostics.md) preserve the failure and the unconfirmed precise cause. Root's independent review and CI lanes remain required before landing.
""")
(D/'checkpoint.md').write_text(f'STATUS: READY\nCOMMIT: {fix}\nCHANGED: 3 files\nOPEN: root publication and CI\nBLOCKERS: none\n---\n\nTest commit: {test}\nFix commit: {fix}\nOriginal proof: ../../cross-shard-singleflight.case.json (preserved).\nDeliberate red, targeted green and final just check recorded.\nOwnership retained for CI follow-up.\n')
print('READY',D/'delivery.json')
