"""Build H3 handoff from saved offline evidence, 2026-11-12.

Inputs: H3 scratch JSON/JUnit/logs and lead failure ledger. Outputs: requested
Markdown and JSON in report worktree. Serves helper3 CI origin/timing assignment.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
E = ROOT.parent
S = E / 'scratch-h3-ci-20261112'
H = E / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs'
DEST = H / 'codex-h3-ci-origin-and-shard-time-20261112'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    ledger = json.loads((H / 'lead-ci-run-42976790438-failures-20261112.json').read_text())
    expected = sorted({r['file'] + '::' + r['node'] for r in ledger['failures'] if r['class'].startswith('import origin:')})
    result = {'branch_head': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'expected_origin_ids': expected, 'tests': {}, 'weights': json.loads((S / 'weights-analysis.json').read_text())}
    for folder in sorted((S / 'tests').iterdir()):
        xml = folder / 'pytest.xml'
        if not xml.exists():
            continue
        rows = []
        for case in ET.parse(xml).iter('testcase'):
            node = case.attrib.get('classname', '').replace('.', '/') + '.py::' + case.attrib.get('name', '<interrupted>')
            failed = case.find('failure')
            error = case.find('error')
            outcome = 'failed' if failed is not None else 'error' if error is not None else 'skipped' if case.find('skipped') is not None else 'passed'
            message = '' if outcome == 'passed' else (failed if failed is not None else error).attrib.get('message', '') if outcome != 'skipped' else 'skipped'
            if 'name' not in case.attrib:
                outcome, message = 'interrupted', 'Unnamed case emitted on interruption; not a pass.'
            rows.append({'node': node, 'outcome': outcome, 'message': message})
        present = {r['node']: r for r in rows}
        result['tests'][folder.name] = {'xml': str(xml), 'sha256': sha(xml),
            'counts': {v: sum(r['outcome'] == v for r in rows) for v in ('passed', 'failed', 'error', 'skipped')},
            'assigned_ids': {n: present.get(n, {'outcome': 'not_run'})['outcome'] for n in expected},
            'nonpassing': [r for r in rows if r['outcome'] != 'passed'],
            'origin_error_count': sum('imported from another origin' in r['message'] for r in rows),
            'outcome': json.loads((folder / 'outcome.json').read_text()) if (folder / 'outcome.json').exists() else None}
    for name in ('scanner-profile', 'original-ci-scanner-profile', 'collection-origins'):
        if (S / f'{name}.json').exists():
            result[name] = json.loads((S / f'{name}.json').read_text())
    result['evidence_hashes'] = {str(p): sha(p) for p in sorted(S.glob('*.json'))}
    result['source_searches'] = {p.name: {'sha256': sha(p), 'text': p.read_text()}
        for p in sorted(S.glob('*references.txt'))}
    text = json.dumps(result, indent=2).replace(chr(64), '[at]') + '\n'
    DEST.with_suffix('.json').write_text(text)
    narrative = (S / 'handoff-narrative.md').read_text() if (S / 'handoff-narrative.md').exists() else 'Draft: evidence gathered; conclusions pending.\n'
    lines = [narrative, '\n## Test evidence\n', 'Exit 2 marks interrupted runs; they are not completed acceptance checks. The assigned-ID column applies only to the import-origin cohorts.\n', '| Cohort | Exit | Passed | Failed | Errors | Assigned IDs passed | Origin errors |', '|---|---:|---:|---:|---:|---:|---:|']
    for name, row in result['tests'].items():
        counts = row['counts']
        code = row['outcome']['returncode'] if row['outcome'] else 'pending'
        lines.append(f"| {name} | {code} | {counts['passed']} | {counts['failed']} | {counts['error']} | {sum(v == 'passed' for v in row['assigned_ids'].values())}/{len(expected)} | {row['origin_error_count']} |")
    if 'collection-origins' in result:
        trace = result['collection-origins']
        lines += ['\n## Bare aliases left after full collection attempt\n', '| Alias | Loaded source | Test modules on importing stack |', '|---|---|---|']
        for name, path in sorted(trace['final'].items()):
            callers = sorted({Path(frame).name for event in trace['events'] if name in event['changed'] for frame in event['test_stack']})
            lines.append(f"| {name} | {path} | {', '.join(callers)} |")
    lines += ['\n## Partition scenarios\n', 'Values use the current branch partition function. Seconds are summed scheduling weights; minutes divide the evaluated total by four workers and sixty seconds. They are not elapsed-job predictions. Unmeasured files retain prior weights or the current median fallback.\n', '| Model | Shards | Largest scheduled seconds | Largest evaluated seconds | Ideal four-worker minutes |', '|---|---:|---:|---:|---:|']
    for model, rows in result['weights']['predictions'].items():
        for n, row in rows.items():
            lines.append(f"| {model} | {n} | {row['largest_predicted_scheduled_seconds']:.3f} | {row['largest_evaluated_measured_seconds']:.3f} | {row['largest_evaluated_measured_ideal_4worker_minutes']:.2f} |")
    lines += ['\n## Native files without measurements\n', '| File | Scheduled seconds | Median fallback |', '|---|---:|---|']
    for row in result['weights']['native_without_measurement']:
        lines.append(f"| {row['file']} | {row['weight']:.4f} | {row['uses_fallback']} |")
    if 'scanner-profile' in result:
        lines += ['\n## Local scanner profile\n', '| Operation | Profiled seconds | Error |', '|---|---:|---|']
        for row in result['scanner-profile']['measurements']:
            lines.append(f"| {row['label']} | {row['seconds']:.6f} | {row['error']} |")
    if 'original-ci-scanner-profile' in result:
        lines += ['\n## Exact CI scanner profile\n', '| Operation | Profiled seconds | Cache after call | Error |', '|---|---:|---|---|']
        for row in result['original-ci-scanner-profile']['measurements']:
            lines.append(f"| {row['label']} | {row['seconds']:.6f} | {row['cache_info']} | {row['error']} |")
        lines += ['\n## Largest scanner class intervals in cancelled CI log\n', 'These are completion intervals, including possible scheduling gaps; they are not isolated CPU measurements.\n', '| Class | Seconds | Outcomes |', '|---|---:|---|']
        for name, row in list(result['weights']['scanner_ci_classes'].items())[:12]:
            lines.append(f"| {name} | {row['seconds']:.3f} | {json.dumps(row['outcomes'], sort_keys=True)} |")
    lines += ['\n## Artifacts\n', f"Code branch head: `{result['branch_head']}`. JSON: `{DEST.with_suffix('.json')}` (SHA-256 `{sha(DEST.with_suffix('.json'))}`).", f"Scratch evidence: `{S}`. Scripts: `{ROOT / 'scripts/adhoc'}` with the `h3_` prefix and `run_h3_ci_tests_20261112.py`. No push, GitHub write, workflow edit, scanner edit, provider call or native-program call."]
    markdown = '\n'.join(lines) + '\n'
    assert chr(64) not in markdown
    DEST.with_suffix('.md').write_text(markdown)
    print(str(DEST.with_suffix('.md')))
    print(sha(DEST.with_suffix('.md')))
    print(json.dumps({name: {'counts': row['counts'], 'assigned_passed': sum(v == 'passed' for v in row['assigned_ids'].values()), 'nonpassing': row['nonpassing'][:2]} for name, row in result['tests'].items()}, indent=2))
if __name__ == '__main__':
    main()
