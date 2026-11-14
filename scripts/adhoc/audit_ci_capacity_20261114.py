"""Inventory run 43536007079 timings for CI capacity; inputs: artifacts/job summary.
Outputs: JSON/Markdown inventory and shard-8 module list in external scratch.
Serves the 2026-11-14 Claude lead assignment and CL196-F2 / #6230.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('jobs', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(args.jobs.read_text())
    modules = {p[:-3].replace('/', '.'): p for p in subprocess.check_output(
        ['git', 'ls-files', 'tests'], cwd=ROOT, text=True).splitlines() if p.endswith('.py')}
    def file_for(case):
        cls = case.attrib['classname']
        return modules[max((m for m in modules if cls == m or cls.startswith(m + '.')), key=len)]
    rows, artifacts, missing = [], [], []
    for job in jobs['jobs']:
        match = re.fullmatch(r'Python 3.12 / shard (\d+)', job['name'])
        if not match:
            continue
        shard = int(match[1])
        xml = args.artifacts / f'tests-py3.12-shard{shard}' / 'pytest.xml'
        if not xml.exists():
            missing.append({'shard': shard, 'conclusion': job['conclusion'], 'path': str(xml)})
            continue
        raw = xml.read_bytes()
        cases = list(ET.fromstring(raw).iter('testcase'))
        artifacts.append({'shard': shard, 'job_id': job['id'], 'conclusion': job['conclusion'],
            'path': str(xml), 'sha256': hashlib.sha256(raw).hexdigest(), 'cases': len(cases)})
        if shard == 8:
            files = list(dict.fromkeys(file_for(c) for c in cases))
            (args.output / 'shard8-modules.txt').write_text('\n'.join(files) + '\n')
        for case in cases:
            duration = Decimal(case.attrib['time'])
            if duration > 120:
                rows.append({'shard': shard, 'file': file_for(case), 'name': case.attrib['name'],
                    'nodeid': file_for(case) + '::' + case.attrib['name'], 'seconds': float(duration),
                    'outcome': next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')})
    rows.sort(key=lambda r: (-r['seconds'], r['nodeid']))
    native = sorted(r['nodeid'] for r in rows if r['file'].startswith('tests/test_native_')
                    and r['file'] != 'tests/test_native_u3l_review_fixtures.py')
    lanes = {f'native-capacity-{i:02d}': node for i, node in enumerate(native, 1)}
    retention = 'tests/test_native_incomplete_retention.py::'
    lanes.update({
        'native-retention-stable': retention + 'test_public_failed_attempt_retains_records_and_reads_back_exactly[False]',
        'native-retention-changing': retention + 'test_public_failed_attempt_retains_records_and_reads_back_exactly[True]',
        'native-retention-final-floor': retention + 'test_public_finalization_after_injected_final_floor_failure',
    })
    lane_for = {node: lane for lane, node in lanes.items()}
    for row in rows:
        row['disposition'] = lane_for.get(row['nodeid'], 'ordinary')
        row['reason'] = (
            'Isolate measured native runtime/setup cost and remove competing shard workers.'
            if row['nodeid'] in lane_for else
            'Scanner-only fixture; no native lifetime/freshness window. Keep module together for file balancing.'
            if row['file'] == 'tests/test_native_u3l_review_fixtures.py' else
            'Non-native case; owning shard completed within 45 minutes. Preserve module fixture reuse and balance by file weight.'
        )
    report = {'run_id': jobs['run_id'], 'head': jobs['head'], 'artifacts': sorted(artifacts, key=lambda r:r['shard']),
        'missing': missing, 'slow_cases': rows, 'proposed_lanes': lanes}
    (args.output / 'capacity-inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['| Shard | Seconds | Test case | Disposition | Reason |', '| --- | ---: | --- | --- | --- |']
    lines.extend(f"| {r['shard']} | {r['seconds']:.3f} | `{r['nodeid']}` | {r['disposition']} | {r['reason']} |" for r in rows)
    (args.output / 'capacity-inventory.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'slow_cases': len(rows), 'artifacts': len(artifacts), 'missing': missing,
        'moved_measured_cases': len(native), 'retained_ordinary_cases': len(rows)-len(native),
        'new_lanes': len(lanes), 'lanes': lanes}, indent=2))


if __name__ == '__main__':
    main()
