import json,pathlib,subprocess
D=pathlib.Path(__file__).resolve().parent
W=pathlib.Path('/Users/viktor/Developer/github/kache-prs/planner-service-stale-lease')
base='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
def git(*args):return subprocess.check_output(['git',*args],cwd=W,text=True).strip()
assert (D/'gate-exit.txt').read_text().strip()=='0','just check must complete successfully before READY'
fix=git('rev-parse','HEAD');test=git('rev-parse','HEAD^')
assert fix==(D/'fix-sha.txt').read_text().strip(),'gate must refer to final fixed tip'
assert git('rev-parse','HEAD^^')==base,'separate test/fix commits required'
assert not git('status','--porcelain'),'PR worktree must be clean'
red=(D/'red.log').read_text();green=(D/'green.log').read_text();gate=(D/'gate.log').read_text()
assert 'stale inherited lease must restore keyless compile admission after owner exit' in red
assert 'test result: FAILED. 0 passed; 1 failed;' in red
assert 'exited_test_lease_owner_restores_admission ... ok' in green
assert 'test result: FAILED' not in green and 'error: test failed' not in green
assert 'error: test failed' not in gate and 'test result: FAILED' not in gate
files=git('diff','--name-only',base,fix).splitlines();assert files==['src/scheduler.rs','src/test_runner.rs']
assert git('diff','--name-only',test,fix)=='src/scheduler.rs'
body=(D/'pr-body.md').read_text();assert len(body.split())<=75
prefix='CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py '
command=prefix+'just check'
commands=[{'command':prefix+'cargo test --bin kache scheduler::tests::exited_test_lease_owner_restores_admission -- --exact','observed_exit':101,'head':base,'tracked_tests':'uncommitted regression/positive controls','log':str(D/'red.log')},{'command':prefix+'cargo test --bin kache scheduler::tests','observed_exit':0,'head':test,'tracked_fix':'uncommitted live-marker check','log':str(D/'green.log')},{'command':prefix+'cargo test --bin kache test_runner::tests','observed_exit':0,'head':test,'tracked_fix':'uncommitted live-marker check','log':str(D/'green.log')},{'command':command,'observed_exit':0,'head':fix,'log':str(D/'gate.log')}]
(D/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
delivery={'id':'planner-service-stale-lease','status':'READY','branch':git('branch','--show-current'),'worktree':str(W),'test_commit':test,'fix_commit':fix,'title':'Restore scheduler admission after inherited test leases expire','body_file':str(D/'pr-body.md'),'base_sha':base,'gate_command':command,'gate_exit':0,'gate_head':fix,'red_log':str(D/'red.log'),'green_log':str(D/'green.log'),'gate_log':str(D/'gate.log'),'changed_files':files,'oracle_notes':str(D/'oracle-notes.md'),'original_proof':str(D.parent.parent/'stale-lease-replay.json'),'dispatch':str(D/'dispatch.json'),'mutation_testing':'CI only; not run locally'}
(D/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
summary='\n'.join(line for line in gate.splitlines() if line.startswith('test result:'))
(D/'gate-summary.txt').write_text(summary+'\n')
focused='\n'.join(line for line in green.splitlines() if line.startswith('test result:'))
(D/'report.md').write_text(f"""STATUS: DONE
COMMIT: {fix}
CHANGED: 2 files
OPEN: CI mutation testing and independent root review
BLOCKERS: none
---

`lease_covers` now requires an exclusively held marker lock in this scheduler's canonical test directory. The existing `slot_is_held` probe supplies the native lock observation. An inherited path from an exited test owner therefore takes ordinary admission after its marker and slots are released. Missing or unprobeable markers also take ordinary admission. Active leases retain nested test and compiler reuse; scheduling limits and the lease format are unchanged.

The deliberately red test-only commit is `{test}`; the production fix commit is `{fix}`. Both start from `{base}`. Only `src/scheduler.rs` and `src/test_runner.rs` changed, and the worktree is clean. [delivery.json](delivery.json) carries exact commits, body and gate references; [dispatch.json](dispatch.json) records the author handoff from the unavailable original investigator.

| Criterion | Executed proof |
| --- | --- |
| Admission resumes after the inherited lease owner exits | [red.log](red.log): after live-owner controls and independent proof of marker release, the stale keyless request held zero slots where one was required; named assertion failed on untouched production |
| Preserve live nested reuse | [green.log](green.log): real child-held lease keeps two slots while parent keyed/keyless requests add none and runner planning is Exec |
| Restore each consumer's admission | [green.log](green.log): stale keyless and keyed guards each hold one real permit; runner planning is exactly Schedule with Fixed(1) |
| Preserve scheduler directory and symlink boundaries | [green.log](green.log): existing path controls now use actually held marker locks and continue to pass |
| Preserve admitted limits and ordinary runner plans | [green.log](green.log): scheduler and test-runner unit suites pass; [gate.log](gate.log) includes existing nested CLI integration and bounded-pool controls |
| Full gate at fixed tip | [gate.log](gate.log): `{command}` exited 0 at `{fix}` |

Targeted suite summaries: `{focused}`. Full workspace test summaries are in [gate-summary.txt](gate-summary.txt). The final gate includes workspace/fuzz formatting, workspace/all-targets clippy with warnings denied, test-resource guard checks and workspace tests. The build wrapper used an exclusive private target and two Cargo/test threads. CI owns mutation testing; no local mutants invocation or publication occurred.

[oracle-notes.md](oracle-notes.md) records independent expectations, the real process/OS-lock seam, live observations saved before owner exit, and cleanup. The ignored fixture is explicitly selected and runs under the ordinary regression on every platform; the regular test uses a fixed pool and avoids host-CPU skip conditions. New tests share no process-global state, live cloud, host config, new production visibility or mutable live cache. The owner has exited and all slots are independently free before stale assertions, so the red test leaves no helper running.

The original [stale-lease-replay.json](../../stale-lease-replay.json), [stale_lease_red.json](../../stale_lease_red.json), [stale_lease_control.json](../../stale_lease_control.json) and [stale_test_lease.py](../../probes/stale_test_lease.py) remain unchanged. They proved the bypass through the real baseline CLI test-runner; this delivery ports that process-lifetime behavior to the existing scheduler/runner seams without repeating the audit.

Shape review: graph queries found existing slot_is_held and process fixture helpers, which are reused. The repair adds no production function, type, trait, variant, module or duplicate validator and makes no unrelated lease redesign. The existing lease predicate stays below 100 lines; the new regular regression is 83 lines. Existing tests that previously named unlocked/nonexistent markers now acquire marker locks to establish their live-lease premise, retaining their original outcome assertions. Root's independent review, cross-platform execution and CI mutation lanes remain required before landing.
""")
(D/'checkpoint.md').write_text(f'STATUS: READY\nCOMMIT: {fix}\nCHANGED: 2 files\nOPEN: root publication and CI\nBLOCKERS: none\n---\n\nTest commit: {test}\nFix commit: {fix}\nOriginal proof: ../../stale-lease-replay.json (preserved).\nDeliberate red, scheduler/runner green and full just check recorded.\nOwnership retained for CI follow-up.\n')
print('READY',D/'delivery.json')
