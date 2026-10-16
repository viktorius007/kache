"""Publish one reviewed, gated delivery as a draft PR; never merges."""
import argparse,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('delivery',type=Path);p.add_argument('review',type=Path);a=p.parse_args()
d=json.loads(a.delivery.read_text());review=a.review.read_text()
assert review.splitlines()[0]=='PASS','independent review must pass'
assert d['gate_exit']==0,'just check must pass'
if d.get('gate_command_record'):
 execution=json.loads(Path(d['gate_command_record']).read_text())
 assert execution['argv'][-2:]==['just','check'],'wrong gate argv'
 assert execution['workdir']==d['worktree'] and execution['exit_code']==0,'wrong gate execution'
else:assert re.search(r'\bjust check\b',d['gate_command']),'wrong gate'
body=Path(d['body_file']).read_text();assert len(body.split())<=75,'PR body too long'
assert re.search(r'https://github.com/kunobi-ninja/kache/blob/[0-9a-f]{40}/[^\s)]+#L[0-9]+',body),'missing source permalink'
wd=d['worktree']
def command(args):return subprocess.check_output(args,cwd=wd,text=True).strip()
assert command(['git','rev-parse','HEAD'])==d['fix_commit'],'tip changed'
assert not command(['git','status','--porcelain','--untracked-files=no']),'tracked checkout dirty'
commits=command(['git','rev-list','--reverse',d['base_sha']+'..HEAD']).splitlines()
pairs=d.get('commit_pairs',[{'test':d['test_commit'],'fix':d['fix_commit']}])
assert 1 <= len(pairs) <= 2,'expected one regression/fix pair plus optional reviewed repair pair'
expected=[sha for pair in pairs for sha in (pair['test'],pair['fix'])]
assert expected[0]==d['test_commit'] and expected[-1]==d['fix_commit'],'delivery endpoints differ'
assert commits==expected,'expected separate test and fix commits'
assert d['fix_commit'] in review,'review is not bound to delivered tip'
command(['git','push','https://github.com/viktorius007/kache.git',d['fix_commit']+':refs/heads/'+d['branch']])
existing=json.loads(command(['gh','api','repos/kunobi-ninja/kache/pulls?head=viktorius007:'+d['branch']+'&state=open']))
if existing:url=existing[0]['html_url']
else:url=command(['gh','pr','create','--repo','kunobi-ninja/kache','--base','main','--head','viktorius007:'+d['branch'],'--draft','--title',d['title'],'--body-file',d['body_file']])
result={'id':d['id'],'url':url,'branch':d['branch'],'fix_commit':d['fix_commit'],'state':'draft','review':str(a.review)}
a.delivery.with_name('published.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
