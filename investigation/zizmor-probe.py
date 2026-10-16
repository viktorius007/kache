import json, subprocess, pathlib, sys
root=pathlib.Path(__file__).resolve().parent
binary=next(root.glob('uv-cache/archive-v0/*/bin/zizmor'))
file=sys.argv[1] if len(sys.argv)>1 else 'kache-publish.yml'
p=subprocess.run([str(binary),'--offline','--no-config','--cache-dir',str(root/'fixtures/zizmor-cache'),'--format','json',str(root/'fixtures'/file)],capture_output=True,text=True)
assert p.returncode in [0,10,11,12,13,14], p.stderr
findings=json.loads(p.stdout)
count=sum(x['ident']=='cache-poisoning' for x in findings)
print(f'{file}: cache-poisoning count={count}; scanner exit={p.returncode}')
expected=0 if 'disabled' in file else 1
assert count==expected, f'expected {expected} cache-poisoning finding, got {count}'
