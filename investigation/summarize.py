import json
import re
import statistics
import sys
from pathlib import Path


def summarize(path):
    groups = {}
    for line in Path(path).read_text().splitlines():
        match = re.search(r"\b(D5_NATURAL|D5) ", line)
        if match is None:
            continue
        line = line[match.start():]
        row = dict(re.findall(r"(\w+)=([^ ]+)", line))
        workload = "uncontended_200_entries" if line.startswith("D5_NATURAL") else "writer_250ms"
        key = (workload, int(row["workers"]), row["path"])
        groups.setdefault(key, []).append(row)
    result = []
    for (workload, workers, path), rows in sorted(groups.items()):
        health = [float(row["health_ms"]) for row in rows]
        result.append({
            "workload": workload,
            "workers": workers,
            "path": path,
            "runs": len(rows),
            "health_median_ms": statistics.median(health),
            "health_min_ms": min(health),
            "health_max_ms": max(health),
            "request_median_ms": statistics.median(float(row["upload_ms"]) for row in rows),
            "gc_median_ms": statistics.median(int(row["gc_ms"]) for row in rows),
            "health_before_writer_release": sum(row.get("health_before_release") == "true" for row in rows),
        })
    return result


if __name__ == "__main__":
    print(json.dumps(summarize(sys.argv[1]), indent=2))
