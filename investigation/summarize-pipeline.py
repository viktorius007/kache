#!/usr/bin/env python3
"""Summarize the saved controlled D5 upload-worker observations."""
import json
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent
samples = []
for line in (root / 'pipeline-measurements.log').read_text().splitlines():
    marker = line.find('D5_PIPELINE ')
    if marker == -1:
        continue
    fields = dict(field.split('=', 1) for field in line[marker:].split()[1:])
    row = {key: (value == 'true' if key == 'health_before_release'
                 else float(value) if key == 'health_ms' else int(value))
           for key, value in fields.items()}
    samples.append(row)
assert len(samples) == 18, f'Expected 18 samples, observed {len(samples)}'
groups = {}
for row in samples:
    key = (row['async_workers'], row['upload_workers'], row['stores'])
    groups.setdefault(key, []).append(row)
summary = []
for (async_workers, upload_workers, stores), rows in groups.items():
    latency = [row['health_ms'] for row in rows]
    peers = [row['peers_before_release'] for row in rows]
    summary.append({
        'async_workers': async_workers, 'upload_workers': upload_workers, 'stores': stores,
        'samples': len(rows), 'health_before_release': sum(row['health_before_release'] for row in rows),
        'health_median_ms': statistics.median(latency), 'health_range_ms': [min(latency), max(latency)],
        'peers_before_release_range': [min(peers), max(peers)],
        'finished_total': [row['finished_total'] for row in rows],
    })
result = {'profile': 'debug', 'controlled_writer_observation_ms': 400,
          'durable_jobs_per_sample': 32, 'samples': samples, 'summary': summary}
(root / 'pipeline-summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(summary, indent=2))
