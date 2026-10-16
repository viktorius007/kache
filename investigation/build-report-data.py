import json,pathlib,datetime
root=pathlib.Path(__file__).resolve().parent; base=root.resolve()
baseline='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
run={'ts':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':baseline,'model':'inherited Codex subagent','mode':'production-readiness','slice':'rust-wrapper'}
findings=[]
for c in json.loads((root/'finding-data.json').read_text()):
 argv=['python3',str(base/'probes'/c['script'])]+c['args']
 if c['script']=='rustdoc_inputs.py': argv=['/usr/bin/env','AUDIT_RUSTDOC_TOOLCHAIN=1.98.1']+argv
 replay={'id':c['id'],'argv':argv,'workdir':str(base.parent),'timeout_seconds':100,'expected_failure_regex':'AssertionError: '+c['message'],'assertion_regex':c['message']}
 (root/'replay-cases'/f"{c['slug']}.json").write_text(json.dumps(replay,indent=2)+'\n')
 log=c['slug']+('-1.98-red.log' if c['script']=='rustdoc_inputs.py' else '-red.log')
 findings.append({'id':c['id'],'kind':'finding','run':run,'category':'defect','domain':'code','summary':c['summary'],'scenario':c['scenario'],'evidence':[{'path':p,'lines':lines,'point':point} for p,lines,point in c['evidence']]+[{'path':f'investigation/evidence/{log}','lines':'full','point':c['message']},{'path':f"investigation/{c['fixture']}/cache/events.jsonl",'lines':'1-2','point':'Miss then local_hit with identical cache_key after the changed input.'}],'trace':c['trace'],'authority':{'source':'failure-mode; investigation/worklist.json obligations; independent real compiler execution','quote':'preserve compiler exit status and diagnostic/artifact behavior.'},'proof':{'red_test':(root/'probes'/c['script']).read_text(),'name':c['script']+' '+(' '.join(c['args']))+'; replay '+str(base/'replay-cases'/f"{c['slug']}.json"),'fails_on':baseline,'output':(root/'evidence'/log).read_text()},'severity':c['severity'],'status':'open'})
 f=root/c['fixture']
 events=[json.loads(line) for line in (f/'cache/events.jsonl').read_text().splitlines()]
 obs={'fixture':str(f.resolve()),'events':[{'result':e['result'],'cache_key':e['cache_key'],'compiler_runs':e.get('compiler_runs'),'dep_info_runs':e.get('dep_info_runs')} for e in events]}
 if c['script']=='rustdoc_inputs.py': obs['markers']={label:json.loads((f/(label+'.markers.json')).read_text()) for label in ['cold','warm','direct']}
 else: obs['invocation']=json.loads((f/'invocation.json').read_text())
 (root/'evidence'/f"{c['slug']}-observations.json").write_text(json.dumps(obs,indent=2)+'\n')
findings.append({'id':'rust-wrapper-control-001','kind':'dismissal','run':run,'category':'defect','domain':'code','summary':'Inner crate documentation include_str! invalidates correctly in the sampled case.','checked':'Cold #![doc = include_str!("README.md")] with OLD_MARKER, then edit README to NEW_MARKER and remove output/parts. Wrapped warm invocation misses under a different key and emits NEW_MARKER, matching direct rustdoc. Executed untouched baseline using rustdoc1.99.','closed_by':{'tier':'executed compiler control','citation':'investigation/rustdoc-doc_include-gvpj0yqu/cold.markers.json, warm.markers.json, direct.markers.json and cache/events.jsonl; investigation/evidence/rustdoc-inner-include-control-observations.json','result':'Wrapped changed-input output matches direct compiler; cache key differs.'},'reopens_if':'Change include syntax/attribute placement, path literal, toolchain or dependency shape. Outer item attributes are separately confirmed defective.','status':'dismissed'})
(root/'findings.json').write_text(json.dumps(findings,indent=2)+'\n')
