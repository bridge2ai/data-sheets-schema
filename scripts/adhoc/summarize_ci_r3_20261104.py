#!/usr/bin/env python3
"""#5485, 2026-11-04: summarize pinned R3 test and profiling evidence.

Inputs: scratch JUnit/execution/environment and paired cProfile JSON files.
Outputs: committed validation/profile summaries and Markdown report tables.
No tests, production changes, network or provider calls.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-bc1g2-timing'
NOTE = ROOT / 'notes/ci_timing_refresh_2026-11-04'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert json.loads(path.read_text()) == value


def validation(complete=False):
    results = []
    totals = {'r3-failing-first': 1, 'r3-fix-canary': 1, 'r3-fixture-contracts': 148,
              'r3-collection': 0, 'r3-weights-canary': 1, 'r3-weights-contracts': 61}
    for label, expected_total in totals.items():
        folder = SCRATCH / label
        if not (folder / 'execution.json').exists():
            continue
        execution = json.loads((folder / 'execution.json').read_text())
        by_file = defaultdict(Counter)
        for case in ET.parse(folder / 'junit.xml').iter('testcase'):
            outcome = next((k for k in ('failure', 'error', 'skipped') if case.find(k) is not None), 'passed')
            by_file[case.attrib['classname']][outcome] += 1
        env = json.loads((folder / 'environment.json').read_text())
        counts = sum(by_file.values(), Counter())
        assert sum(counts.values()) == expected_total
        if label.startswith('r3-weights-'):
            assert env['timings_sha256'] == sha(ROOT / 'utils/ci_test_durations.json')
        if label == 'r3-weights-contracts':
            assert by_file == {'tests.test_ci_sharding': {'passed': 48},
                               'tests.test_ci_timing_update': {'passed': 13}}
        if label == 'r3-failing-first':
            assert execution['exit_code'] == 1 and counts == {'failure': 1}
        else:
            assert execution['exit_code'] == 0 and not (counts['failure'] or counts['error'] or counts['skipped'])
            origins = json.loads((folder / 'module-origins.json').read_text())
            assert all(sha(Path(row['path'])) == row['sha256'] for row in origins.values())
        results.append(dict(label=label, **execution, counts=dict(counts),
            by_module={k: dict(v) for k, v in by_file.items()},
            python=env['python'], head=env['head'], weights_sha256=env['timings_sha256'],
            artifacts={name: sha(folder / name) for name in
                       ('junit.xml', 'execution.json', 'environment.json', 'collection.json',
                        'module-origins.json')}))
    if complete:
        assert {r['label'] for r in results} == set(totals)
    save(NOTE / 'validation.json', results)
    for r in results:
        print(r['label'], r['counts'], r['wall_seconds'], r['by_module'])


def grouped(profile):
    files, functions = defaultdict(float), defaultdict(lambda: [0, 0.0, 0.0])
    for row in profile['functions']:
        file, _, function = row['function'].rsplit(':', 2)
        files[file] += row['self_seconds']
        key = file + ':' + function  # line numbers move between commits
        values = functions[key]
        values[0] += row['calls']
        values[1] += row['self_seconds']
        values[2] += row['cumulative_seconds']
    return files, functions


def profiles():
    evidence, values = {}, {}
    for label in ('g1', 'bc1g2'):
        directory = SCRATCH / f'r3-profile-{label}'
        profile = json.loads((directory / 'profile.json').read_text())
        execution = json.loads((directory / 'execution.json').read_text())
        assert profile['exit_code'] == execution['exit_code'] == 0
        cases = list(ET.parse(directory / 'junit.xml').iter('testcase'))
        assert len(cases) == 1 and not list(cases[0])
        evidence[label] = {k: v for k, v in profile.items() if k != 'functions'}
        evidence[label].update(junit_seconds=float(cases[0].attrib['time']),
            artifacts={name: sha(directory / name) for name in
                ('profile.json', 'profile.pstats', 'junit.xml', 'execution.json',
                 'environment.json', 'snapshot.json', 'module-origins.json')})
        values[label] = grouped(profile)
    a_files, a_functions = values['g1']
    b_files, b_functions = values['bc1g2']
    files = [dict(file=k, g1_self=a_files[k], bc1g2_self=b_files[k],
                  delta_self=b_files[k] - a_files[k]) for k in a_files.keys() | b_files.keys()]
    files.sort(key=lambda r: -r['delta_self'])
    functions = [dict(function=k, g1_calls=a_functions[k][0], bc1g2_calls=b_functions[k][0],
        g1_self=a_functions[k][1], bc1g2_self=b_functions[k][1],
        g1_cumulative=a_functions[k][2], bc1g2_cumulative=b_functions[k][2],
        delta_cumulative=b_functions[k][2] - a_functions[k][2])
        for k in a_functions.keys() | b_functions.keys()]
    functions.sort(key=lambda r: -r['delta_cumulative'])
    targets = [
        'src/data_sheets_schema/bc1_selection.py:validate_spec_mode',
        'src/data_sheets_schema/bc1_selection.py:enabled',
        'src/data_sheets_schema/bc1_selection.py:_pairs',
        'src/data_sheets_schema/typed_audit_runtime.py:_bc1',
        'scripts/build_api_registrations.py:partition_profiles',
        'scripts/build_api_registrations.py:size_typed_audit_input',
        'src/data_sheets_schema/bc1_registration.py:size_inputs',
        'src/data_sheets_schema/schema_cache.py:load_yaml',
        'src/data_sheets_schema/schema_snapshot.py:capture_schema',
        'src/data_sheets_schema/audit_omissions.py:_schema',
        'src/data_sheets_schema/audit_omissions.py:_read',
        'src/data_sheets_schema/duplicate_keys.py:nesting_exceeds',
        'src/data_sheets_schema/shared_generation.py:capture',
        'src/data_sheets_schema/shared_generation.py:assert_current',
        'src/data_sheets_schema/shared_generation.py:_contracts_digest',
        'src/data_sheets_schema/typed_audit_runtime.py:recover',
        'src/data_sheets_schema/typed_audit_runtime.py:_rebuild',
    ]
    focus = []
    for target in targets:
        key = '<tree>/' + target
        found = next((r for r in functions if r['function'] == key), None)
        focus.append(found or dict(function=key, g1_calls=0, bc1g2_calls=0,
            g1_self=0.0, bc1g2_self=0.0, g1_cumulative=0.0,
            bc1g2_cumulative=0.0, delta_cumulative=0.0))
    comparison = dict(
        local_junit_ratio=evidence['bc1g2']['junit_seconds'] / evidence['g1']['junit_seconds'],
        local_cpu_ratio=evidence['bc1g2']['cpu_seconds'] / evidence['g1']['cpu_seconds'],
        local_call_ratio=evidence['bc1g2']['total_calls'] / evidence['g1']['total_calls'],
        yaml_self_seconds={label: sum(v for k, v in values[label][0].items()
                                    if '/site-packages/yaml/' in k) for label in values},
        bc1_module_self_seconds={label: sum(v for k, v in values[label][0].items()
                                 if k.startswith('<tree>/src/data_sheets_schema/bc1_')) for label in values})
    ci = {r['run']: r for r in json.loads((NOTE / 'measurement.json').read_text())['admission_ci']}
    comparison['ci_file_ratio'] = ci['41707437114']['seconds'] / ci['41700664435']['seconds']
    a_case = next(r for r in ci['41700664435']['slowest'] if r['nodeid'] == evidence['g1']['case'])
    b_case = next(r for r in ci['41707437114']['slowest'] if r['nodeid'] == evidence['bc1g2']['case'])
    comparison['ci_case_ratio'] = float(b_case['seconds']) / float(a_case['seconds'])
    save(NOTE / 'profile-summary.json', dict(evidence=evidence,
        comparison=comparison, requested_categories=focus,
        module_self_times=files[:40],
        function_times=[r for r in functions if r['function'].startswith('<tree>/src/')][:60],
        note='Module self time is additive. Cumulative function times overlap; do not add them. '
             'Same-file/name functions are grouped across moved line numbers. cProfile perturbs runtime. '
             'Leading 40 module increases and 60 project-function cumulative increases are retained here; '
             'the hash-pinned scratch profiles retain every function and caller.'))
    lines = ['| Profile | Case JUnit s | Process wall s | Process CPU s | Calls |',
             '| --- | ---: | ---: | ---: | ---: |']
    for label, row in evidence.items():
        lines.append(f"| {label} | {row['junit_seconds']:.3f} | {row['wall_seconds']:.3f} | "
                     f"{row['cpu_seconds']:.3f} | {row['total_calls']} |")
    lines += ['', '| Module | G1 self s | BC1+G2 self s | Delta self s |',
              '| --- | ---: | ---: | ---: |']
    for row in files[:15]:
        name = row['file']
        if '/site-packages/' in name:
            name = 'site-packages/' + name.split('/site-packages/', 1)[1]
        elif '/lib/python3.13/' in name:
            name = 'stdlib/' + name.split('/lib/python3.13/', 1)[1]
        lines.append(f"| `{name}` | {row['g1_self']:.3f} | {row['bc1g2_self']:.3f} | {row['delta_self']:+.3f} |")
    lines += ['', '| Function | G1 calls | BC1+G2 calls | G1 cumulative s | BC1+G2 cumulative s |',
              '| --- | ---: | ---: | ---: | ---: |']
    chosen = focus
    for row in chosen:
        lines.append(f"| `{row['function']}` | {row['g1_calls']} | {row['bc1g2_calls']} | "
                     f"{row['g1_cumulative']:.3f} | {row['bc1g2_cumulative']:.3f} |")
    (NOTE / 'profile-tables.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('Comparison:', json.dumps(comparison))


def report_tables():
    report = ROOT.parent / 'plans/reviews/bc1_g2_ci_r3_2026-11-04.md'
    text = report.read_text()
    for name, heading in [('tables.md', '## Admission slowdown investigation'),
                          ('profile-tables.md', '## Offline review and handoff')]:
        source = NOTE / name
        marker = f'<!-- generated {name} -->'
        end = f'<!-- end generated {name} -->'
        if source.exists() and heading in text:
            block = marker + '\n\n' + source.read_text() + '\n' + end + '\n\n'
            if marker in text:
                start, rest = text.split(marker, 1)
                _, tail = rest.split(end + '\n\n', 1)
                text = start + block + tail
            else:
                text = text.replace(heading, block + heading, 1)
    report.write_text(text)
    assert report.read_text() == text


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('validation', 'profiles', 'report-tables'))
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    if args.mode == 'validation':
        validation(args.complete)
    elif args.mode == 'profiles':
        profiles()
    else:
        report_tables()
