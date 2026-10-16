import json,pathlib,subprocess
D=pathlib.Path(__file__).resolve().parent
W=pathlib.Path('/Users/viktor/Developer/github/kache-prs/planner-service-timeline-auth')
base='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
def git(*args):return subprocess.check_output(['git',*args],cwd=W,text=True).strip()
assert (D/'gate-exit.txt').read_text().strip()=='0','full just check must pass before READY'
fix=git('rev-parse','HEAD');test=git('rev-parse','HEAD^')
assert fix==(D/'fix-sha.txt').read_text().strip(),'gate must belong to final fixed tip'
assert git('rev-parse','HEAD^^')==base,'separate test/fix commits required'
assert not git('status','--porcelain'),'assigned worktree must be clean'
red=(D/'red.log').read_text();green=(D/'green.log').read_text();gate=(D/'gate.log').read_text()
assert 'available Actions credential must authenticate the production timeline upload' in red and 'left: Null' in red
assert 'test result: FAILED. 0 passed; 1 failed;' in red
timeout_red=(D/'timeout-red.log').read_text()
assert timeout_red.count('auth and upload must end within one 30-second budget: Pending')==2
assert 'test result: FAILED. 7 passed; 2 failed; 1 ignored;' in timeout_red
assert 'telemetry_push_uses_automatic_auth_and_preserves_explicit_and_missing_controls ... ok' in green
assert 'auth_and_timeline_share_one_timeout ... ok' in green
assert 'exhausted_auth_does_not_dispatch_a_timeline ... ok' in green
assert 'test result: FAILED' not in green and 'error: test failed' not in green
assert 'test result: FAILED' not in gate and 'error: test failed' not in gate
files=git('diff','--name-only',base,fix).splitlines();assert files==['Cargo.toml','src/timeline_client.rs','tests/timeline_auth_test.rs']
assert git('diff','--name-only',test,fix)=='src/timeline_client.rs'
assert git('show','--format=','--numstat',fix)=='8\t1\tsrc/timeline_client.rs'
body=(D/'pr-body.md').read_text();assert len(body.split())<=75
prefix='CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py '
command=prefix+'just check'
commands=[{'command':prefix+'cargo test --bin kache timeline_client::tests','observed_exit':101,'head':'657bf608c3fb91105ba86d5010a4b2bf95f68422','tracked_tests':'uncommitted paused-clock deadline controls','log':str(D/'timeout-red.log')},{'command':prefix+'cargo test --test timeline_auth_test telemetry_push_uses_automatic_auth_and_preserves_explicit_and_missing_controls -- --exact','observed_exit':101,'head':base,'tracked_tests':'uncommitted regression and refusal fixture adaptation','log':str(D/'red.log')},{'command':prefix+'cargo test --test timeline_auth_test','observed_exit':0,'head':test,'tracked_fix':'uncommitted shared bearer resolution','log':str(D/'green.log')},{'command':prefix+'cargo test --bin kache timeline_client::tests','observed_exit':0,'head':test,'tracked_fix':'uncommitted shared bearer resolution','log':str(D/'green.log')},{'command':prefix+'cargo test --bin kache planner_auth::tests','observed_exit':0,'head':test,'tracked_fix':'uncommitted shared bearer resolution','log':str(D/'green.log')},{'command':command,'observed_exit':0,'head':fix,'log':str(D/'gate.log')}]
(D/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
delivery={'id':'planner-service-timeline-auth','status':'READY','branch':git('branch','--show-current'),'worktree':str(W),'test_commit':test,'fix_commit':fix,'title':'Authenticate timeline uploads with automatic planner credentials','body_file':str(D/'pr-body.md'),'base_sha':base,'gate_command':command,'gate_exit':0,'gate_head':fix,'red_log':str(D/'red.log'),'green_log':str(D/'green.log'),'gate_log':str(D/'gate.log'),'changed_files':files,'oracle_notes':str(D/'oracle-notes.md'),'original_proof':str(D.parent.parent/'timeline-auth-replay.json'),'dispatch':str(D/'dispatch.json'),'timeout_red_log':str(D/'timeout-red.log'),'review_correction':'Shared deadline and remaining POST budget; old gate and READY archived under before-timeout-review prefix','mutation_testing':'CI only; not run locally'}
(D/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
summary='\n'.join(line for line in gate.splitlines() if line.startswith('test result:'))
(D/'gate-summary.txt').write_text(summary+'\n')
focused='\n'.join(line for line in green.splitlines() if line.startswith('test result:'))
(D/'report.md').write_text(f"""STATUS: DONE
COMMIT: {fix}
CHANGED: 3 files
OPEN: independent root review and CI mutation testing
BLOCKERS: none
---

Timeline uploads now resolve credentials through the existing planner_auth::bearer function. Previously push_timeline read only PlannerConfig.token, omitting available workload and trusted-session credentials. Explicit-token priority, safe transport and trust rules remain owned by the shared resolver. One shared deadline covers authentication and the POST. The remaining-budget pattern from planner_client rejects an exhausted deadline before dispatch and gives the request only the remaining allowance. The established upload timeout floor and configured larger limits remain unchanged. No new authentication design, API or production helper was added.

The test-only commit is `{test}` and the fix commit is `{fix}`, independently based on `{base}`. The production repair resolves the shared bearer, rejects exhausted auth budgets, limits the POST to its remaining allowance and attaches the resolved token. The worktree is clean; [delivery.json](delivery.json) and [dispatch.json](dispatch.json) record exact ownership, commits and gate evidence.

| Criterion | Executed evidence |
| --- | --- |
| Ordinary automatic credentials reach actual timeline uploads | [red.log](red.log) fails on a null Authorization header despite available synthetic Actions credentials; [green.log](green.log) verifies the exact obtained bearer and stored-session report |
| Explicit bearer wins over available automatic credentials | The CLI control posts a distinct explicit bearer with zero Actions requests, before the red assertion and after the fix |
| Missing credentials retain advisory behavior | The CLI control posts no bearer, reports the fixture 401, exits 0 and never reports a stored session |
| Correct Actions token request and production body | Fixture checks runtime bearer, API version and planner-base audience; decodes received zstd body and verifies the independent session ID |
| Authentication and POST share one budget | [timeout-red.log](timeout-red.log): both partial/exhausted-auth inputs leave the original repair Pending after31 simulated seconds; [green.log](green.log): delayed POST times out within the shared allowance and exhausted auth rejects dispatch |
| Preserve service-refusal and existing auth rules | Relevant timeline-client and planner-auth suites pass, including compressed upload, 413 reporting and existing trusted-session/workload controls |
| Required full workspace gate | [gate.log](gate.log): `{command}` exits 0 at `{fix}` |

Targeted summaries: `{focused}`. [gate-summary.txt](gate-summary.txt) records workspace test summaries. The required gate runs formatting, workspace/all-targets clippy with warnings denied, test-resource checks and workspace tests. Fixture compile diagnostics are preserved in [fixture-compile-error.log](fixture-compile-error.log) and [deadline-fixture-compile-error.log](deadline-fixture-compile-error.log); neither is counted as a behavioral red. The superseded initial gate/READY and command records are retained under before-timeout-review prefixes. The review-requested timeout discriminator failed before its repair; only the subsequent final-tip full gate establishes readiness.

[oracle-notes.md](oracle-notes.md) records independent expectations, fixture discriminators, process isolation, reuse queries and cleanup. Each CLI child gets a cleared environment and fixture-only HOME/config/cache/Kunobi state. HTTP fixtures bind loopback only, use synthetic tokens and enforce exact headers; no real credentials, external service calls, installed config or live caches are used. The ordinary regression does not mutate process-global state. The deadline fixture changes synthetic auth environment only inside its separately selected child, before production reads it; no sibling tests share that child or its paused clock. Servers and children have scoped teardown and the child execution is bounded.

The saved [timeline-auth-replay.json](../../timeline-auth-replay.json), [timeline_auth_red.json](../../timeline_auth_red.json), [timeline_auth_control.json](../../timeline_auth_control.json) and [timeline_workload_auth.py](../../probes/timeline_workload_auth.py) remain unchanged. This delivery ports their transport proof, without repeating the audit. The new CLI regression directly proves Actions auth plus explicit/missing controls; trusted-session authentication is reused through the established resolver and existing unit suite, without claiming a newly executed end-to-end login flow.

Shape review: existing shared resolver and CLI fixture command are reused; local test handlers model the Actions and timeline HTTP contracts. No production function/type/trait/module or visibility is added. Each new test/fixture stays within 100 lines. Dev-only Tokio test-util permits explicit time advances while actual loopback requests and admission notifications retain the production I/O seam. Local mutation testing was not run; root's independent review and CI mutation/cross-platform lanes remain required before landing.
""")
(D/'checkpoint.md').write_text(f'STATUS: READY\nCOMMIT: {fix}\nCHANGED: 3 files\nOPEN: root publication and CI\nBLOCKERS: none\n---\n\nTest commit: {test}\nFix commit: {fix}\nSaved proof preserved at ../../timeline-auth-replay.json.\nBehavioral red, relevant green and full just check recorded.\nOwnership retained for CI follow-up.\n')
print('READY',D/'delivery.json')
