#!/usr/bin/env python3
# Refresh REPORT-F4 after scheduled-runner integration, 2026-11-14. Inputs: actual
# report/closure functions and immutable preservation evidence. Outputs: eight
# pure cases/fixtures/snapshots. No project imports, pytest, final report or
# mutation of the actual auxiliary files; corrupt/missing pins are injected.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUT = SCRATCH / 'report-auxiliary-discovery-verification-after-scheduled-runner'
AUX = SCRATCH / 'source-bytecode'
REPORTER = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def require(value, reason):
    if not value:
        raise ValueError(reason)


def functions(source):
    tree = ast.parse(source.read_bytes(), filename=str(source))
    names = {'classify_auxiliary', 'classify_cohort', 'discover_cohorts', 'cohort_directories'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    namespace = {'ROOT': ROOT, 'Path': Path, 'hashlib': hashlib, 'json': json, 'pin': pin, 'require': require}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


def refuses_selection(namespace, rows):
    try:
        namespace['cohort_directories'](rows)
    except (ValueError, AssertionError):
        return
    raise AssertionError('invalid artifacts were accepted for cohort selection')


def main():
    assert not OUT.exists(), 'retain prior verification'
    OUT.mkdir()
    namespaces = [functions(path) for path in (REPORTER, CLOSURE)]
    reviewed = []
    for source in (REPORTER, CLOSURE):
        snapshot = OUT / ('reviewed-' + source.name)
        save(snapshot, source.read_bytes())
        reviewed.append(pin(snapshot))
    raw = (AUX / 'outcome.json').read_bytes()
    actual = json.loads(raw)
    retained = [pin(AUX / 'outcome.json'), pin(Path(actual['plan']['path'])), pin(Path(actual['preserved']['path']))]
    cases = []
    for namespace in namespaces:
        rows = namespace['discover_cohorts'](SCRATCH)
        auxiliary, = [row for row in rows if row['directory'] == str(AUX)]
        assert auxiliary['classification'] == 'auxiliary'
        assert auxiliary['evidence'] == retained
        assert AUX not in namespace['cohort_directories'](rows)
    cases.append({'case': 'known_auxiliary_retained', 'passed': True, 'retained_artifacts': 3})
    for name, marker in (('unknown_outcome_only_invalid', None), ('known_with_junit_invalid', 'pytest.xml'),
                         ('known_with_log_invalid', 'pytest.log'), ('known_with_command_invalid', 'command.json')):
        parent = OUT / name
        directory = parent / 'isolated-copy'
        directory.mkdir(parents=True)
        save(directory / 'outcome.json', raw)
        if marker is not None:
            save(directory / marker, b'{}\n' if marker == 'command.json' else b'isolated pytest marker\n')
        for namespace in namespaces:
            # Even at the known path, extra pytest markers cannot qualify for
            # the auxiliary exception; no actual marker file is added there.
            if marker is not None:
                assert namespace['classify_auxiliary'](AUX, ['outcome.json', marker], raw) is None
            rows = namespace['discover_cohorts'](parent)
            assert len(rows) == 1 and rows[0]['classification'] == 'invalid'
            refuses_selection(namespace, rows)
        cases.append({'case': name, 'passed': True, 'scope': 'known outcome bytes in isolated copied directory; extra-marker gate also checked at exact known path'})
    for namespace in namespaces:
        assert namespace['classify_auxiliary'](AUX, ['outcome.json'], raw + b'\n') is None
    cases.append({'case': 'changed_known_hash_invalid', 'passed': True, 'scope': 'changed raw bytes refused by exact-path classifier; actual file unchanged'})
    plan_path = Path(actual['plan']['path'])
    for name, missing in (('changed_provenance_invalid', False), ('missing_provenance_invalid', True)):
        for namespace in namespaces:
            def injected_pin(path):
                if Path(path) == plan_path:
                    if missing:
                        raise FileNotFoundError(str(path))
                    return {**pin(path), 'sha256': '0' * 64}
                return pin(path)
            namespace['pin'] = injected_pin
            try:
                rows = namespace['discover_cohorts'](SCRATCH)
            finally:
                namespace['pin'] = pin
            auxiliary, = [row for row in rows if row['directory'] == str(AUX)]
            assert auxiliary['classification'] == 'invalid'
            refuses_selection(namespace, rows)
        cases.append({'case': name, 'passed': True, 'scope': 'injected changed/missing plan pin; actual artifacts unchanged'})
    assert all(pin(Path(record['path'])) == record for record in retained)
    result = {'finding_id': 'G2-REVIEW-REPORT-F4', 'status': 'verified',
        'reporter': pin(REPORTER), 'closure': pin(CLOSURE), 'producer': pin(Path(__file__).resolve()),
        'reviewed_sources': reviewed, 'ledger': pin(SCRATCH / 'review-report-f4.json'),
        'auxiliary_outcome': pin(AUX / 'outcome.json'), 'auxiliary_artifacts_unchanged': retained,
        'cases': cases, 'passed': 8, 'failed': 0,
        'scope': 'Actual helper classifier/discovery/selection functions; exact one auxiliary outcome only. Synthetic copies and injected pin failures; no project imports or pytest.'}
    save(OUT / 'result.json', (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'output': pin(OUT / 'result.json'), 'passed': 8, 'failed': 0}, indent=2))


if __name__ == '__main__':
    main()
