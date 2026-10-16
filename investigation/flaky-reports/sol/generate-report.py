from pathlib import Path
import json,re,shlex
root=Path('/private/tmp/kache-flaky/sol')
rows=[json.loads(line) for line in (root/'runs.jsonl').read_text().splitlines()]
rows.sort(key=lambda r:r['start'])
s=(root/'report-body.md').read_text()
for label in ['R01','R05','R07','R08','R09','R11','R12','R20','R21','R27','R29']:
 log=(root/'logs'/f'{label}.log').read_text()
 # Preserve the original panic/diagnostic block verbatim, excluding libtest footer.
 if label=='R01':
  a=log.index("thread 'compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes'")
  b=log.find('\n\n',a)
 else:
  a=log.index("thread '")
  b=log.find('\nFAILED',a)
  if b<0:b=log.find('\n\n\nfailures:',a)
  if b<0:b=log.find('\n\nfailures:',a)
 block=log[a:b].rstrip()
 s=s.replace(f'@@FAIL_{label}@@','```text\n'+block+'\n```')
for n,name in [(1,'instrumentation-phase1.patch'),(2,'instrumentation.patch'),(3,'instrumentation-phase3.patch'),(4,'instrumentation-phase4.patch'),(5,'instrumentation-phase5.patch')]:
 s=s.replace(f'@@PATCH{n}@@',(root/name).read_text().rstrip())
hits=json.loads((root/'sweep.json').read_text())
# Exclude implementation of the requested common env helper and its paired restore.
hits=[r for r in hits if not (r['file']=='src/config/tests.rs' and 98<=r['line']<=123)]
files=sorted(set(r['file'] for r in hits))
table=['| File | Clock, sleep, elapsed, timeout lines | Direct process-mutation lines | Observed direct-site timing/state failure |','|---|---|---|---|']
for f in files:
 clocks=[];state=[]
 for r in hits:
  if r['file']!=f:continue
  mut=bool(re.search(r'\b(?:set_var|remove_var|set_current_dir|setrlimit|sigaction|set_global_default|try_init|set_max_level)\(',r['code']))
  (state if mut else clocks).append(str(r['line']))
 observed='F6 forced upper bound; otherwise no' if f=='src/daemon/tests.rs' else 'No; indirect F7 described above' if f=='tests/fallback_recovery_test.rs' else 'No; indirect F1 described above' if f=='src/compiler/cc/tests.rs' else 'F2/F3 forced; no unforced failure' if f=='src/scheduler.rs' else 'F4 forced; no unforced failure' if f=='src/wrapper/tests.rs' else 'No; indirect F5 described above' if f=='src/cli/tests.rs' else 'No direct test-site failure; F7 production deadline above' if f=='src/fallback/macos.rs' else 'No'
 table.append('| `'+f+'` | '+(', '.join(clocks) or '—')+' | '+(', '.join(state) or '—')+' | '+observed+' |')
s=s.replace('@@SWEEP@@','\n'.join(table))
findings=[
 ('F1','compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes',{'R05','R07'}, {'R03','R06'}),
 ('F2','scheduler::tests::permit_pool_blocks_until_a_slot_is_free',{'R08'},set()),
 ('F3','scheduler::tests::waiter_rechecks_after_owner_completes',{'R09'},set()),
 ('F4','wrapper::tests::admit_scheduler_miss_recheck_returns_accepted_meta',{'R12'},set()),
 ('F5','cli::tests::test_is_macos_protected',{'R11'},set()),
 ('F6','daemon::tests::test_wait_for_warming_blocks_then_signals',{'R20'},{'R10'}),
 ('F7','sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server',{'R27'},set())]
counts=['| Finding | Unforced full commands: failures/reached | Valid forced probes: failures/runs | Other isolated controls: failures/runs |','|---|---|---|---|']
observations={}
for fid,name,forced,special in findings:
 buckets={'full':[],'forced':[],'controls':[],'special':[]}
 for row in rows:
  log=(root/'logs'/f"{row['id']}.log").read_text()
  if not re.search(r'test '+re.escape(name)+r' \.\.\.',log):continue
  failed=bool(re.search(r'^    '+re.escape(name)+r'$',log,re.M))
  category='forced' if row['id'] in forced else 'special' if row['id'] in special else 'full' if '--workspace' in row['command'] else 'controls'
  buckets[category].append({'run':row['id'],'failed':failed})
 def total(cat):return str(sum(x['failed'] for x in buckets[cat]))+'/'+str(len(buckets[cat]))
 counts.append('| '+fid+' | '+total('full')+' | '+total('forced')+' | '+total('controls')+' |')
 observations[fid]=buckets
(root/'observations.json').write_text(json.dumps(observations,indent=2))
risks={'WARM':'daemon::tests::test_wait_for_warming_already_signaled','PUBLISH':'daemon_publish::tests::handing_off_without_a_socket_declines_at_once','EVENTS':'events::tests::choosing_what_to_keep_stays_linear_in_the_log','TUI':'tui::tests::background_work_is_due_only_when_unpaused_idle_and_on_schedule','STAMP':'tree_stamp::tests::a_stamp_settles_one_window_after_its_newest_write','PRESSURE':'scheduler::pressure::tests::a_forced_answer_replaces_the_machine_until_cleared','EVICT':'store::tests::eviction_pauses_between_write_slices'}
for marker,name in risks.items():
 reached=failed=0
 for row in rows:
  if '--workspace' not in row['command']:continue
  log=(root/'logs'/f"{row['id']}.log").read_text()
  if not re.search(r'test '+re.escape(name)+r' \.\.\.',log):continue
  reached+=1;failed+=bool(re.search(r'^    '+re.escape(name)+r'$',log,re.M))
 s=s.replace('@@RISK_'+marker+'@@',str(failed)+'/'+str(reached))

full=sum('--workspace' in r['command'] for r in rows)
s=s.replace('@@COUNTS@@',f'{full} full-workspace test commands were run (maximum 10). No single test approached 300 invocations. The investigation stopped test work at the full-run budget, before the three-hour wall limit. Counts below count each top-level invocation that actually reached the test; aborted targets do not contribute an invented pass. Full-command counts include the explicitly identified scratch-path setup runs. F1\'s R03/R06 negative discriminators and F6\'s invalid R10 probe are excluded from these categories. F7\'s controls include the diagnostic, unpaused R29 run.\n\n'+'\n'.join(counts))
ledger=['| Run / log | Command | Test threads | Load average | Result |','|---|---|---:|---|---|']
for row in rows:
 args=row['command'][:]
 k=['./scripts/with-test-resources.sh','cargo','test','-p','kache','--bin','kache'];w=['./scripts/with-test-resources.sh','cargo','test','--workspace']
 cmd=shlex.join(args)
 cmd=cmd.replace(shlex.join(k),'K').replace(shlex.join(w),'W')
 thread='1 (inner)' if row['id']=='R20' else '16 (default)' if row['threads']=='default' else row['threads']
 log=(root/'logs'/f"{row['id']}.log").read_text()
 names=re.findall(r'^    ((?:\w+::)*\w+)\s*$',log,re.M)
 # Only names appearing in a libtest failure list; non-failure words do not appear here in these logs.
 names=list(dict.fromkeys(n for n in names if re.search(r"(?:test |thread ')"+re.escape(n),log)))
 if row['exit']==0:result='PASS'
 else:result='FAIL (exit '+str(row['exit'])+')'+(': '+', '.join(names) if names else '')
 if row['id']=='R10':result+='; rejected probe'
 if row['id'] in ['R01','R02']:result+='; two `/private` discovery setup failures'
 if row['id']=='R18':result='FAIL (exit 101): 19 scratch-path/setup failures; see log'
 ledger.append(f"| [{row['id']}]({root}/logs/{row['id']}.log) | `{cmd}` | {thread} | `{row['load']}` | {result} |")
s=s.replace('@@RUNS@@','\n'.join(ledger))
assert '@@' not in s.replace('@@ -','DIFF') or not re.search(r'@@[A-Z_0-9]+@@',s)
if full<10:s='Draft: remaining budgeted runs are in progress.\n\n'+s.replace('The investigation stopped test work at the full-run budget, before the three-hour wall limit.', 'The final budget/stop statement will be updated after the remaining commands complete.')
(root/'report.md').write_text(s)
print('Report words:',len(s.split()),'characters:',len(s),'full runs:',full,'static sites:',len(hits),'files:',len(files))
print('\n'.join(counts))
