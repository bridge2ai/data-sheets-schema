"""Summarize saved JUnit and the actual interpreter namespace for D148.

Inputs: assigned scratch logs/XML and this checkout. Outputs: JSON and generated
Markdown per-test failure ledger and counts; namespace witness when requested.
Serves the Codex 196 integration handoff, 2026-11-14. No gates are patched.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ('manifest', 'manifest-boundaries', 'registration', 'builder', 'retention', 'scanner')


def classify(detail):
    if 'own distribution exclusion requires the exact pinned project namespace' in detail:
        return 'mixed project namespace; manifest refuses before later validation'
    if 'unsupported v2 render producer: prepare' in detail:
        return 'scanner v2 producer AST rejects v3 preparation; not a pin-only failure'
    if 'unsupported v2 render CLI' in detail:
        return 'scanner v2 CLI AST rejects v3 CLI; not a pin-only failure'
    if 'v2 envelope authority source changed' in detail:
        return 'scanner source pin refusal; later checks unverified'
    if '00b0f717' in detail and 'f865fea7' in detail:
        return 'direct H1 authority hash assertion; unapplied pin rotation, later scanner proof unverified'
    return 'inspect saved traceback; not attributed solely to pins'


def namespace(scratch):
    import data_sheets_schema
    from data_sheets_schema import native_environment_manifest as manifest
    pth = Path(sys.prefix) / ('lib/python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor)) / 'site-packages/data_sheets_schema.pth'
    try:
        manifest._own_source_authority()
        outcome = {'accepted': True}
    except ValueError as exc:
        outcome = {'accepted': False, 'exception': type(exc).__name__, 'message': str(exc)}
    result = {'python': sys.executable, 'prefix': sys.prefix,
        'package_paths': list(data_sheets_schema.__path__), 'expected_package_path': str(ROOT / 'src/data_sheets_schema'),
        'manifest_module': manifest.__file__, 'pth': {'path': str(pth), 'content': pth.read_text(),
            'sha256': hashlib.sha256(pth.read_bytes()).hexdigest()}, 'check': outcome,
        'scope': 'Read-only inspection; no import path repair or production check bypass.'}
    (scratch / 'namespace-witness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


def summarize(scratch):
    cases, groups = [], []
    for stage in REQUIRED:
        path = scratch / (stage + '.xml')
        if not path.is_file():
            continue
        document = ET.parse(path)
        counts = Counter()
        for case in document.iter('testcase'):
            failure = case.find('failure')
            error = case.find('error')
            skip = case.find('skipped')
            state = 'failed' if failure is not None else 'error' if error is not None else 'skipped' if skip is not None else 'passed'
            detail = ''.join((entry.text or '') for entry in (failure, error) if entry is not None)
            row = {'stage': stage, 'node': case.get('classname', '') + '::' + case.get('name', ''),
                'status': state, 'seconds': float(case.get('time', 0)), 'detail': detail,
                'attribution': classify(detail) if detail else None, 'junit': str(path)}
            counts[state] += 1
            cases.append(row)
        invocation = json.loads((scratch / (stage + '-invocation.json')).read_bytes())
        groups.append({'stage': stage, 'seconds': invocation.get('seconds'), 'returncode': invocation.get('returncode'),
            **{key: counts[key] for key in ('passed', 'failed', 'error', 'skipped')}, 'cases': sum(counts.values())})
    report = {'groups': groups, 'cases': cases,
        'totals': dict(Counter(row['status'] for row in cases)),
        'failure_reasons': dict(Counter(row['attribution'] for row in cases if row['detail'])),
        'missing_stages': [name for name in REQUIRED if name not in {group['stage'] for group in groups}]}
    (scratch / 'test-results.json').write_text(json.dumps(report, indent=2) + '\n')
    summary = ['| Stage | Passed | Failed | Errors | Skipped | Seconds |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for group in groups:
        summary.append('| ' + ' | '.join(str(group[name]) for name in ('stage', 'passed', 'failed', 'error', 'skipped', 'seconds')) + ' |')
    (scratch / 'test-summary.md').write_text('\n'.join(summary) + '\n')
    failures = ['| Test | Result | Attribution |', '| --- | --- | --- |']
    for row in cases:
        if row['detail']:
            failures.append('| ' + row['node'].replace('|', '\\|') + ' | ' + row['status'] + ' | ' + row['attribution'] + ' |')
    (scratch / 'test-failures.md').write_text('\n'.join(failures) + '\n')
    print(json.dumps({key: report[key] for key in ('groups', 'totals', 'failure_reasons', 'missing_stages')}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--namespace', action='store_true')
    args = parser.parse_args()
    if args.namespace:
        namespace(args.scratch.resolve(strict=True))
    else:
        summarize(args.scratch.resolve(strict=True))


if __name__ == '__main__':
    main()
