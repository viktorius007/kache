import json,pathlib,re,subprocess
D=pathlib.Path(__file__).resolve().parent
W=pathlib.Path('/Users/viktor/Developer/github/kache-prs/qa-remote-binding')
base='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
def git(*args):return subprocess.check_output(['git',*args],cwd=W,text=True).strip()
assert (D/'gate-exit.txt').read_text().strip()=='0','just check must complete successfully before READY'
fix=git('rev-parse','HEAD');test=git('rev-parse','HEAD^')
assert fix==(D/'fix-sha.txt').read_text().strip(),'gate must refer to final fixed tip'
assert git('rev-parse','HEAD^^')==base,'delivery must have separate test and fix commits from baseline'
assert not git('status','--porcelain'),'PR worktree must be clean'
red=(D/'red.log').read_text();green=(D/'green.log').read_text();gate=(D/'gate.log').read_text()
assert 'a valid pack for another entry must be rejected' in red
assert 'test result: FAILED. 0 passed; 1 failed;' in red
assert 'test result: ok. 27 passed; 0 failed;' in green
assert 'error: test failed' not in gate and 'test result: FAILED' not in gate
files=git('diff','--name-only',base,fix).splitlines();assert files==['src/remote_layout.rs']
body=(D/'pr-body.md').read_text();assert len(body.split())<=75
command='CARGO_TARGET_DIR='+str(W/'target')+' python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check'
delivery={'id':'qa-remote-binding','status':'READY','branch':git('branch','--show-current'),'worktree':str(W),'test_commit':test,'fix_commit':fix,'title':'Validate exact remote packs against the requested entry','body_file':str(D/'pr-body.md'),'base_sha':base,'gate_command':command,'gate_exit':0,'gate_head':fix,'red_log':str(D/'red.log'),'green_log':str(D/'green.log'),'gate_log':str(D/'gate.log'),'changed_files':files,'oracle_notes':str(D/'oracle-notes.md'),'mutation_testing':'CI only; not run locally'}
commands=json.loads((D/'commands.json').read_text())
commands[-1]['observed_exit']=0
commands[-1]['state']='completed successfully at final tip'
(D/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
(D/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
summary='\n'.join(line for line in gate.splitlines() if line.startswith('test result:'))
(D/'gate-summary.txt').write_text(summary+'\n')
report=f'''STATUS: DONE
COMMIT: {fix}
CHANGED: 1 file
OPEN: CI mutation testing and independent root review
BLOCKERS: none
---

Exact remote restore now binds an otherwise valid pack to the requested cache key and crate before publication. `download_entry_observed` supplies the existing `ExpectedEntryBinding`; the shared extractor checks identity before renaming the entry into place. The digest is optional for exact restores and remains required by packed-prefetch callers. The mismatch diagnostic names expected and actual identities. No Store migration or cross-shard change is included.

The deliberately red test-only commit is `{test}`. The production fix commit is `{fix}`. Only `src/remote_layout.rs` changed, and the worktree is clean. [delivery.json](delivery.json) carries exact commit, source, body and gate references for root publication.

| Criterion | Executed proof |
| --- | --- |
| Reject a valid pack under another requested key | [red.log](red.log): named acceptance assertion failed on untouched production; 0 passed, 1 failed |
| Preserve correct exact restores and independently reject key/crate mismatches | [green.log](green.log): new request-table regression passed with matching, key-only and crate-only fixtures |
| Preserve packed-prefetch digest enforcement | [green.log](green.log): matching digest, valid-format wrong digest, key/crate mismatch and malformed digest controls passed |
| Full local gate at fixed tip | [gate.log](gate.log): `{command}` exited 0 at `{fix}` |

The targeted layout suite passed all 27 tests. Full workspace suite summaries are in [gate-summary.txt](gate-summary.txt). The final gate includes workspace/fuzz formatting checks, workspace/all-targets clippy with warnings denied, test-resource guard checks and workspace tests. Build-slot.py used a private target with two Cargo/test threads. CI owns mutation testing; no local mutants invocation or publication occurred.

[oracle-notes.md](oracle-notes.md) records the request-table and digest discriminators. The network double preserves wrong-object routing; production archive extraction, identity validation and publication remain exercised. Independent expectations come from test-owned request identities and fixture bytes. The saved original compiler proof established the real wrong-result consequence and was reused without repeating the audit. Fixtures use temporary stores and introduce no process-global state, host configuration, visibility hooks or live cloud calls.

Shape review: reuse search found existing `ExpectedEntryBinding` and `extract_entry_pack_until` and both are reused; there is no new production function, trait, variant, module or duplicate validator. The production diff is limited to the expected binding, optional prefetch digest and mismatch diagnostic; no unrelated cleanup. The new test stays below 100 lines and within the module's existing privacy boundary. Existing extraction's prior size is not broadened into a refactor. Root's independent review and CI mutation lanes remain required before landing.
'''
(D/'report.md').write_text(report)
print('READY',D/'delivery.json')
