import pathlib,re,json
root=pathlib.Path.cwd(); rows=[]
pat=re.compile(r'\bsleep\(|\b(?:Instant|SystemTime|Utc|Local)::now\(|\.elapsed\(|\b(?:recv_)?timeout\(|\bset_(?:var|current_dir|rlimit)\(|\bremove_var\(|\b(?:sigaction|signal)\(|\bset_global_default\(|\btry_init\(|\bset_max_level\(|\bstamp_clock_ns\(')
def mask(s):
 p=re.compile(r'//[^\n]*|/\*.*?\*/|r(\#*)".*?"\1|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])\'',re.S)
 return p.sub(lambda m: ''.join('\n' if c=='\n' else ' ' for c in m[0]),s)
for base in ['src','crates','tests']:
 for p in root.joinpath(base).rglob('*.rs'):
  rel=str(p.relative_to(root)); src=p.read_text(); clean=mask(src);lines=src.splitlines(); testfile=('tests' in p.parts or p.name in ('tests.rs','test_support.rs') or '/test_support' in rel)
  stack=[];pairs={}
  for i,c in enumerate(clean):
   if c=='{':stack.append(i)
   elif c=='}' and stack:pairs[stack.pop()]=i
  spans=[]
  for m in re.finditer(r'#\[\s*(?:[\w:]*test(?:\([^\]]*\))?|cfg\([^\]]*\btest\b[^\]]*\))\s*\]',clean):
   tail=clean[m.end():];nextsep=re.search(r'[;{]',tail)
   if nextsep:
    start=m.end()+nextsep.start();end=pairs.get(start,start)
    spans.append((m.start(),end))
  name='';pos=0
  for n,line in enumerate(lines,1):
   m=re.search(r'\bfn\s+(\w+)',clean[pos:pos+len(line)])
   if m:name=m[1]
   if (testfile or any(a<=pos<=b for a,b in spans)) and pat.search(clean[pos:pos+len(line)]) and not line.strip().startswith('//'):
    rows.append({'file':rel,'line':n,'fn':name,'code':line.strip()})
   pos+=len(line)+1
pathlib.Path('/private/tmp/kache-flaky/sol/sweep.json').write_text(json.dumps(rows,indent=2))
for f in sorted(set(r['file'] for r in rows)):
 print(f+': '+', '.join(str(r['line']) for r in rows if r['file']==f))
print('SITES',len(rows))
