import json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
w=json.loads((root/'investigation/worklist.json').read_text())
transfer=set(json.loads(Path('/Users/viktor/Developer/github/kache-investigations/coordinator/investigation/coverage-transfers.json').read_text())['benchmark-guardrails']['paths'])
sampled={'scripts/prefetch-qualification-test.py':[[1,190],[1000,1252]],'tests/integration_test.rs':[[1,230],[3390,3534]],'crates/kache-e2e/src/bench_runner/tests.rs':[[1,140]],'scripts/bench/tests/test_short.py':[[1,100]]}
full_tests={'.github/tests/.gitignore','.github/tests/package.json','.github/tests/perf-gate-authorization.test.mjs','.github/tests/workflow-policy.mjs','.github/tests/workflow-policy.test.mjs','crates/kache-e2e/tests/skip_summary.rs','crates/kache-e2e/tests/strict_gate.rs','scripts/bench/tests/__init__.py','scripts/bench/tests/test_contention_counts.py','scripts/bench/tests/test_gate_local.py','scripts/bench/tests/test_job_telemetry.py','scripts/bench/tests/test_phases.py','tests/binstall_metadata_test.rs','tests/common/mod.rs'}
scenario_read={'scenarios/README.md','scenarios/COVERAGE.md','scenarios/e2e-c-hello/scenario.toml','scenarios/e2e-rust-workspace/scenario.toml','scenarios/e2e-cc-parallel/scenario.toml'}
rows=[]
for item in w['primary_paths']:
 p=item['path'];k=item['kind'];row={'path':p,'state':'unreviewed','evidence':'Inventoried at pinned baseline; no semantic review or execution claimed.','reopen_conditions':'Review this workload or test when its domain becomes a release concern.'}
 if p in transfer:
  row.update(owner='benchmark-guardrails',evidence='Primary ownership transferred by coordinator; authoritative coverage is in audit-benchmark-guardrails/investigation/coverage.json.',reopen_conditions='Follow benchmark-guardrails owner findings and limits.')
 elif p in sampled:
  row.update(state='sampled',reviewed_ranges=sampled[p],evidence='Explicit source sampling of harness isolation, validity, policy, artifact or termination assertions; production framework read in full. Full prefetch suite executed: 96 tests; workflow bridge executed contention oracles.',reopen_conditions='Review remaining test bodies before claiming whole-suite oracle adequacy.')
 elif k in ('source-or-script','config-or-delivery-collateral','contract-doc-or-ci') or p in full_tests or p in scenario_read or (k in ('scenario-fixture','benchmark-fixture') and p.endswith('scenario.toml')):
  row.update(state='reviewed',evidence='Read complete file at baseline; traced relevant guardrail wiring and failure behavior. Execution evidence where applicable is under investigation/evidence/.',reopen_conditions='Behavior, toolchain, selection, publication or isolation contract changes.')
 elif k in ('license-or-lock-collateral','binary-collateral','demo-or-visual-collateral','symlink-collateral'):
  row.update(state='collateral',evidence='Inventory classification: '+k+'; no production repair or content-quality review. Generated locks are package inputs checked structurally through manifests, not dependency-by-dependency.',reopen_conditions='Artifact parsing, dependency supply chain, legal terms, visual fidelity or demo script execution becomes task scope.')
 elif k in ('scenario-fixture','benchmark-fixture') and not p.endswith('scenario.toml'):
  row.update(state='collateral',evidence='Repeated workload source, helper manifests or patch payload inventoried as '+k+'; scenario definition and framework reviewed, payload not individually read or executed.',reopen_conditions='Reproduce a domain-specific integrity/cache failure using this workload; pinned upstream patch drift.')
 rows.append(row)
(root/'investigation/coverage.json').write_text(json.dumps(rows,indent=2)+'\n')
print('coverage',len(rows),{s:sum(x['state']==s for x in rows) for s in ('reviewed','sampled','unreviewed','collateral')})
print('retained unreviewed production',[x['path'] for x in rows if x['state']=='unreviewed' and x['path'] not in transfer and next(p['kind'] for p in w['primary_paths'] if p['path']==x['path'])=='source-or-script'])
