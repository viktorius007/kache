#!/usr/bin/env python3
"""Aggregate paired samples; profiler durations overlap and are not wall savings."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
import statistics

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'scripts'))
from bench.stats import paired_change


def duration(value):
    amount, unit = value.split()
    return float(amount) * {'ns':1e-9,'µs':1e-6,'us':1e-6,'ms':1e-3,'s':1}[unit]


def comparison(records, workload, base, head):
    samples = defaultdict(dict)
    for record in records:
        if record.get('workload') == workload:
            samples[record['sample']][record['arm']] = record
    pairs = [value for value in samples.values() if base in value and head in value]
    ratios = [(pair[head]['seconds']/pair[base]['seconds']-1)*100 for pair in pairs]
    gate = paired_change([p[base]['seconds']*1000 for p in pairs], [p[head]['seconds']*1000 for p in pairs])
    return {'pairs':len(pairs), 'base_median_seconds':statistics.median(p[base]['seconds'] for p in pairs), 'head_median_seconds':statistics.median(p[head]['seconds'] for p in pairs), 'median_paired_percent':statistics.median(ratios), 'bootstrap_95_percent':gate['interval_95_pct'], 'repo_gate':gate['outcome'], 'paired_percent':ratios}


def phases():
    summary = {}
    for folder in sorted((ROOT/'raw').glob('*-traces')):
        totals = defaultdict(float)
        counts = Counter()
        decisions = Counter()
        dropped = []
        for path in sorted(folder.glob('*.json')):
            for event in json.loads(path.read_text())['traceEvents']:
                lost = event.get('args', {}).get('dropped_events', 0)
                if lost:
                    dropped.append({'file': path.name, 'count': lost})
                if event.get('ph') == 'X':
                    totals[event['name']] += event.get('dur', 0) / 1000
                    counts[event['name']] += 1
                elif event.get('ph') == 'i' and 'outcome' in event.get('args', {}):
                    decisions[event['name'] + '=' + event['args']['outcome']] += 1
        summary[folder.name] = {'totals_ms': dict(totals), 'counts': dict(counts),
                                'decisions': dict(decisions), 'dropped': dropped}
    (ROOT/'phase-summary.json').write_text(json.dumps(summary, indent=2))


def main():
    summary = {}
    for path in sorted((ROOT/'raw').glob('paired-*.json')):
        raw=json.loads(path.read_text())
        records=raw['records']
        output={'comparisons':{},'samples':[],'hotpath':{}}
        for workload in ['unchanged','documentation-edit']:
            output['comparisons'][workload]=comparison(records,workload,'v1','main-disabled')
        output['comparisons']['overhead']=comparison(records,'overhead','main-disabled','main-enabled')
        for record in records:
            output['samples'].append({key: record.get(key) for key in ['label','arm','seconds','sample','workload','loadavg']} | {'results':dict(Counter(event.get('result') for event in record['events'])), 'key_ms':sum(event.get('key_ms',0) for event in record['events']), 'startup_ms':sum(event.get('startup_ms',0) for event in record['events']), 'restore_ms':sum(event.get('restore_ms',0) for event in record['events'])})
        prefix=path.stem.split('-')[1]
        for folder in sorted((ROOT/'raw').glob(f'{prefix}-*-hotpath')):
            functions=defaultdict(lambda:{'calls':0,'seconds':0,'reports':0})
            reports=list(folder.glob('*.json'))
            for report in reports:
                data=json.loads(report.read_text())
                if not data.get('functions_timing'): continue
                for function in data['functions_timing']['data']:
                    entry=functions[function['name']]
                    entry['calls']+=function['calls']
                    entry['seconds']+=duration(function['total'])
                    entry['reports']+=1
            output['hotpath'][folder.name]={'report_files':len(reports),'functions':dict(functions)}
        summary[path.stem]=output
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2))
    phases()
    print('DONE',ROOT/'summary.json')
    for label,output in summary.items():
        print(label,json.dumps(output['comparisons']))


if __name__=='__main__':
    main()
