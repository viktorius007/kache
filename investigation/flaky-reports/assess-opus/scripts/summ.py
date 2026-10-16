import sys,re,collections
d=collections.defaultdict(list)
for l in sys.stdin:
    for k,pat in [('permit_elapsed',r'MEASURE permit elapsed_ms=(-?[\d.]+)'),('flight_margin',r'MEASURE flight margin_ms=(-?[\d.]+)'),('wrapper_margin',r'MEASURE wrapper margin_ms=(-?[\d.]+)'),('wrapper_setup',r'setup_ms=(-?[\d.]+)'),('warming_elapsed',r'MEASURE warming elapsed_ms=(-?[\d.]+)')]:
        for m in re.finditer(pat,l): d[k].append(float(m[1]))
for k,v in sorted(d.items()):
    v.sort(); print(f"{k}: n={len(v)} min={v[0]:.1f} p50={v[len(v)//2]:.1f} max={v[-1]:.1f}")
