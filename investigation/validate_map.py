#!/usr/bin/env python3
"""Validate inventory closure and demonstrate that omission/overlap gates reject."""
import collections
import copy
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'investigation'
x=json.loads((OUT/'audit-map.json').read_text())
expected={}
for record in subprocess.check_output(['git','ls-tree','-rz','--long',x['baseline_commit']],cwd=ROOT).split(b'\0'):
 if record:
  head,path=record.split(b'\t'); mode,kind,blob,size=head.decode().split()
  expected[path.decode()]={'blob':blob,'mode':mode,'bytes':int(size)}

def validate(data):
 actual=[p['path'] for p in data['inventory']]
 assert len(actual)==len(set(actual)), 'inventory overlap'
 assert set(actual)==set(expected), 'uncovered or untracked path'
 owners=collections.Counter(p for s in data['slices'] for p in s['paths'])
 assert set(owners)==set(expected) and all(v==1 for v in owners.values()), 'primary overlap or omission'
 by_slice={s['id']:s for s in data['slices']}
 for p in data['inventory']:
  assert p['primary_slice'] in by_slice and p['path'] in by_slice[p['primary_slice']]['paths'], 'owner mismatch'
  assert all(p[k]==v for k,v in expected[p['path']].items()), 'blob or mode mismatch'
  sections=p['reading_sections']
  if sections:
   assert sections[0]['start_line']==1 and sections[-1]['end_line']==p['text_lines'], 'reading gap'
   assert all(a['end_line']+1==b['start_line'] for a,b in zip(sections,sections[1:])), 'reading gap or overlap'
 for s in data['slices']:
  assert s['path_count']==len(s['paths']), 'slice count mismatch'
  assert set(p for b in s['reading_batches'] for p in b['paths'])==set(s['paths']), 'batch omission'
 for seam in data['interactions']:
  assert seam['primary_slice'] in by_slice and seam['consult_slice'] in [*by_slice,'all'], 'seam has no owner'
 frontier=json.loads((OUT/'raw/frontier-input.json').read_text())['frontier']
 assert len(data['frontier_ownership'])==len(frontier)==2530, 'frontier omission'
 assert {r['input_index'] for r in data['frontier_ownership']}==set(range(len(frontier))), 'frontier duplication'
 for c in data['repository_contracts']:
  lines=(ROOT/c['path']).read_text().splitlines()
  assert lines[c['line']-1].startswith(c['quote']), 'contract citation mismatch'
 return True

validate(x)
checks=[]
for name, mutate in [('missing-path',lambda d:d['inventory'].pop()), ('duplicate-path',lambda d:d['inventory'].append(d['inventory'][0])), ('duplicate-primary',lambda d:d['slices'][1]['paths'].append(d['slices'][0]['paths'][0])), ('missing-seam-owner',lambda d:d['interactions'][0].update(primary_slice='unowned'))]:
 bad=copy.deepcopy(x); mutate(bad)
 try: validate(bad)
 except AssertionError as exc: checks.append({'discriminator':name,'result':'rejected','reason':str(exc)})
 else: raise AssertionError(f'vacuous validator: accepted {name}')
for s in x['slices']:
 work=json.loads((OUT/f'worklists/{s["id"]}.json').read_text())
 assert {p['path'] for p in work['primary_paths']}==set(s['paths'])
 assert all(p['executed_depth']=='none' for p in work['primary_paths'])
print('PASS: exact pinned inventory, unique primary worklists, owned seams, citations and frontier closure; four malformed discriminators rejected')
result={'status':'PASS','baseline_commit':x['baseline_commit'],'tracked_paths':len(expected),'slices':len(x['slices']),'uncovered':0,'overlaps':0,'frontier_rows':2530,'discriminators':checks,'production_modified':False,'semantic_review_claimed':False}
(OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'raw/pinned-inventory.json').write_text(json.dumps(expected,indent=2)+'\n')
