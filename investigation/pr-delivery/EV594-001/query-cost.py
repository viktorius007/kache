import json,sqlite3,statistics,time
# One generated population; compare selection work only, without metadata I/O.
db=sqlite3.connect(":memory:")
db.execute("CREATE TABLE entries(cache_key TEXT PRIMARY KEY, compile_time_ms INTEGER NOT NULL DEFAULT 0, committed INTEGER NOT NULL DEFAULT 1)")
db.executemany("INSERT INTO entries(cache_key) VALUES(?)", ((f"{i:064x}",) for i in range(100000)))
base="SELECT cache_key FROM entries WHERE compile_time_ms = 0 AND committed = 1"
results={"sqlite_version":sqlite3.sqlite_version,"population":100000,"limit":10000,"scope":"generated in-memory selection only; no metadata I/O or production timing claim","queries":{}}
for name,sql in [("baseline",base+" LIMIT ?"),("randomized",base+" ORDER BY RANDOM() LIMIT ?")]:
 plan=list(db.execute("EXPLAIN QUERY PLAN "+sql,(10000,)))
 db.execute(sql,(10000,)).fetchall()
 samples=[]
 for _ in range(3):
  start=time.perf_counter();rows=db.execute(sql,(10000,)).fetchall();samples.append((time.perf_counter()-start)*1000)
 assert len(rows)==10000
 results["queries"][name]={"plan":plan,"returned":len(rows),"samples_ms":samples,"median_ms":statistics.median(samples)}
print(json.dumps(results,indent=2))
