#!/usr/bin/env python3
"""take.py FILE SIDES  -- SIDES is a string like 'uuo' : per conflict hunk, o=ours(HEAD), u=upstream(theirs), b=ours then theirs, s=skip(leave)."""
import re,sys
p,sides=sys.argv[1],sys.argv[2]
s=open(p).read()
pat=re.compile(r'<<<<<<< HEAD\n(.*?)\|\|\|\|\|\|\| [0-9a-f]+\n(.*?)=======\n(.*?)>>>>>>> upstream/main\n',re.S)
it=iter(sides)
def rep(m):
    c=next(it)
    if c=='o': return m.group(1)
    if c=='u': return m.group(3)
    if c=='b': return m.group(1)+m.group(3)
    return m.group(0)
s2=pat.sub(rep,s)
rest=list(it)
if rest: sys.exit(f"too many sides: {len(rest)} left")
open(p,'w').write(s2)
print(p, 'remaining hunks:', len(pat.findall(s2)))
