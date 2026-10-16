import hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).resolve().parent
worktree=pathlib.Path('/Users/viktor/Developer/github/kache-prs/restoration-literal-marker')
binary=worktree/'target/debug/kache';baseline=pathlib.Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')
runner=worktree/'target/debug/deps/fallback_recovery_test-f38743893dd34a55'
assert hashlib.sha256(baseline.read_bytes()).hexdigest()=='45840941809ca7c45622027f84d2c653c737e7ff35d375cfbf355b619456120f'
backup=worktree/'target/sandbox-control-final-kache';assert not backup.exists()
shutil.copy2(binary,backup);digest=hashlib.sha256(binary.read_bytes()).hexdigest();results=[]
try:
 shutil.copy2(baseline,binary)
 out=subprocess.run([runner,'--exact','sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server','--nocapture'],capture_output=True,text=True,timeout=60,cwd=worktree)
 results.append(dict(binary='proven baseline',exit=out.returncode,stdout=out.stdout,stderr=out.stderr))
finally:
 shutil.copy2(backup,binary);backup.unlink();assert hashlib.sha256(binary.read_bytes()).hexdigest()==digest
out=subprocess.run([runner,'--exact','sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server','--nocapture'],capture_output=True,text=True,timeout=60,cwd=worktree)
results.append(dict(binary='restored final',sha256=digest,exit=out.returncode,stdout=out.stdout,stderr=out.stderr))
(root/'logs/sandbox-exact-baseline-control.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
