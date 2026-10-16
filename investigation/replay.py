import json,pathlib,re,subprocess
root=pathlib.Path(__file__).resolve().parent
results=[]
for path in sorted((root/'replay-cases').glob('*.json')):
 case=json.loads(path.read_text())
 process=subprocess.run(case['argv'],cwd=case['workdir'],capture_output=True,text=True,timeout=case['timeout_seconds'])
 output=process.stdout+process.stderr
 (root/'evidence'/(path.stem+'-replay.log')).write_text(output)
 result={'id':case['id'],'manifest':str(path),'exit_code':process.returncode,'expected_failure_matched':bool(re.search(case['expected_failure_regex'],output)),'assertion_matched':bool(re.search(case['assertion_regex'],output))}
 results.append(result)
 print(json.dumps(result))
 assert process.returncode==1 and result['expected_failure_matched'] and result['assertion_matched'], 'replay did not reproduce the named baseline defect: '+str(path)
(root/'evidence'/'replay-results.json').write_text(json.dumps(results,indent=2)+'\n')
