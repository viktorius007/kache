"""Record one published draft; confirmed bugs remain open until upstream merge."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('published',type=Path);a=p.parse_args()
x=json.loads(a.published.read_text());root=Path(__file__).resolve().parent
queue=root/'queue.json';rows=json.loads(queue.read_text())
r=next(r for r in rows if r['id']==x['id']);r.update(status='draft-pr',pr=x['url'],fix_commit=x['fix_commit'])
queue.write_text(json.dumps(rows,indent=2)+'\n')
register=root.parent/'findings-register.json';rows=json.loads(register.read_text())
r=next(r for r in rows if r['finding']['id']==x['id']);r['tracking'].update(pr=x['url'],delivery_status='draft-pr',resolution='open')
register.write_text(json.dumps(rows,indent=2)+'\n')
tracker=root.parent/'issue-tracker.md';lines=tracker.read_text().splitlines()
for i,line in enumerate(lines):
 if line.startswith('| '+x['id']+' |'):
  cols=line.split(' | ');cols[2]='[Draft PR #'+x['url'].rsplit('/',1)[1]+']('+x['url']+'); awaiting CI/merge';lines[i]=' | '.join(cols)
tracker.write_text('\n'.join(lines)+'\n')
print(x['url'])
