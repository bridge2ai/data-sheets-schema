#!/usr/bin/env python3
# Refresh REPORT-F2 after the exact REPORT-F4 auxiliary gate, 2026-11-14. Inputs: report and
# closure sources, retained original/archive commands. Outputs: exclusive pure
# harness evidence under report-cohort-discovery-20261114/verification. No pytest,
# project imports, process signals, source/test changes, or report generation.
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
DEST = OUT / 'report-cohort-discovery-after-f4-reuse-auxiliary'
REPORTER = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def document(path, value):
    save(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def require(value, reason):
    if not value:
        raise ValueError(reason)


def functions(source):
    tree = ast.parse(source.read_bytes(), filename=str(source))
    names = {'classify_cohort', 'classify_auxiliary', 'discover_cohorts', 'cohort_directories'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    main, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main']
    invoked = {node.func.id for node in ast.walk(main)
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert {'discover_cohorts', 'cohort_directories'} <= invoked, 'main must use verified discovery'
    namespace = {'Path': Path, 'json': json, 'pin': pin, 'require': require, 'hashlib': hashlib, 'ROOT': ROOT}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


def main():
    assert not DEST.exists(), 'retain prior verification'
    DEST.mkdir()
    report, closure = functions(REPORTER), functions(CLOSURE)
    namespaces = (report, closure)
    snapshots = []
    for source in (REPORTER, CLOSURE):
        target = DEST / ('reviewed-' + source.name)
        save(target, source.read_bytes())
        snapshots.append(pin(target))
    fixture = DEST / 'fixture'
    fixture.mkdir()
    real, archive = fixture / 'real', fixture / 'archive'
    real.mkdir()
    archive.mkdir()
    argv = ['python', '-m', 'pytest', '--basetemp=' + str(real / 'cases'),
            '--junitxml=' + str(real / 'pytest.xml')]
    command = {'command': argv, 'cwd': str(ROOT)}
    document(real / 'command.json', command)
    document(archive / 'command.json', command)
    cases = []

    def check(name, directory, value, expected):
        results = [ns['classify_cohort'](directory, value) for ns in namespaces]
        assert all(row['classification'] == expected for row in results), (name, results)
        cases.append({'case': name, 'passed': True, 'classification': expected,
                      'helpers_checked': ['reporter', 'closure']})

    check('real_equals', real, command, 'cohort')
    check('real_split', real, {'cwd': str(ROOT), 'command': ['python', '-m', 'pytest',
          '--basetemp', str(real / 'cases'), '--junitxml', str(real / 'pytest.xml')]}, 'cohort')
    check('relative_outputs', real, {'cwd': str(fixture), 'command': ['python', '-m', 'pytest',
          '--basetemp=real/cases', '--junitxml=real/pytest.xml']}, 'cohort')
    check('copied_archive', archive, command, 'archive')
    check('missing_basetemp', real, {'cwd': str(ROOT), 'command': argv[:3] + argv[4:]}, 'invalid')
    check('missing_junitxml', real, {'cwd': str(ROOT), 'command': argv[:-1]}, 'invalid')
    check('duplicate_destination', real, {'cwd': str(ROOT), 'command': argv + [argv[-1]]}, 'invalid')
    check('mixed_destinations', real, {'cwd': str(ROOT), 'command': argv[:-1] + [
          '--junitxml=' + str(archive / 'pytest.xml')]}, 'invalid')
    check('malformed_argv', real, {'cwd': str(ROOT), 'command': 'pytest'}, 'invalid')
    # Deliberately make the archive newer: neither actual discovery entrypoint
    # may return it as another invocation or allow its mtime to supersede real.
    os.utime(real / 'command.json', ns=(1_000_000_000, 1_000_000_000))
    os.utime(archive / 'command.json', ns=(2_000_000_000, 2_000_000_000))
    for ns in namespaces:
        found = ns['discover_cohorts'](fixture)
        assert {row['classification'] for row in found} == {'cohort', 'archive'}
        assert ns['cohort_directories'](found) == [real]
    cases.append({'case': 'newer_archive_excluded', 'passed': True,
                  'helpers_checked': ['reporter', 'closure']})
    for name, payload in (('missing_command', None), ('invalid_json', b'{malformed')):
        parent = DEST / name
        child = parent / 'candidate'
        child.mkdir(parents=True)
        save(child / 'pytest.xml', b'<testsuites/>\n')
        if payload is not None:
            save(child / 'command.json', payload)
        for ns in namespaces:
            found = ns['discover_cohorts'](parent)
            assert len(found) == 1 and found[0]['classification'] == 'invalid'
            try:
                ns['cohort_directories'](found)
            except (AssertionError, ValueError):
                pass
            else:
                raise AssertionError('malformed discovery did not refuse: ' + name)
        cases.append({'case': name, 'passed': True, 'helpers_checked': ['reporter', 'closure']})
    for name, dirname, expected in (
        ('actual_saved_original', 'final-components', 'cohort'),
        ('actual_saved_archive', 'legacy-component-failures-20261114', 'archive')):
        directory = OUT / dirname
        check(name, directory, json.loads((directory / 'command.json').read_bytes()), expected)
    # Read current discovery without retaining volatile active log pins; this
    # inventory asserts classification, not completion or success of any cohort.
    observed = report['discover_cohorts'](OUT)
    assert all(row['classification'] != 'invalid' for row in observed), observed
    assert report['cohort_directories'](observed) == [Path(row['directory']) for row in observed
                                                    if row['classification'] == 'cohort']
    result = {'finding_id': 'G2-REVIEW-REPORT-F2', 'status': 'verified',
        'reporter': pin(REPORTER), 'closure': pin(CLOSURE), 'producer': pin(Path(__file__).resolve()),
        'ledger': pin(OUT / 'review-report-f2.json'), 'reviewed_sources': snapshots,
        'cases': cases, 'passed': len(cases), 'failed': 0,
        'saved_commands': [pin(OUT / name / 'command.json') for name in (
            'final-components', 'legacy-component-failures-20261114')],
        'current_discovery': [{key: value for key, value in row.items() if key != 'evidence'} for row in observed],
        'scope': 'Pure actual helper discovery/selection functions; no pytest, project imports or completion claims.',
        'observed_false_acceptance': False}
    assert len(cases) == 14
    document(DEST / 'result.json', result)
    print(json.dumps({'output': pin(DEST / 'result.json'), 'passed': len(cases), 'failed': 0}, indent=2))


if __name__ == '__main__':
    main()
