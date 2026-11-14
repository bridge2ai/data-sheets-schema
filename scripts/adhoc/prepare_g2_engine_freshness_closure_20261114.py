#!/usr/bin/env python3
"""Preserve/extend G2 freshness review closure, 2026-11-14.

Inputs: current closure, immutable ENGINE-FRESHNESS-F1 ledger, prior F3/F4
verifiers. Outputs: before/after closure snapshots, bounded closure integration,
new standalone verifier producers and revision record. No project imports,
pytest, final closure/report execution, source/test changes or commits.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUT = SCRATCH / 'engine-freshness-closure-20261114'
TARGET = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'

ACTION = '''def close_engine_freshness(directories, head, evidence, details):
    identity = 'G2-REVIEW-ENGINE-FRESHNESS-F1'
    original = ledger(identity, 'review-engine-freshness.json', evidence)
    finding, = [row for row in original['findings'] if row['finding_id'] == identity]
    file = 'tests/test_native_shared_execution_failure.py'
    expected = {
        'test_v2_publication_failure_preserves_first_error[published.json]',
        'test_v2_injected_transport_timeout_keeps_registered_limit_and_failure',
        'test_v2_publication_failure_preserves_first_error[final.json]',
    }
    module = file[:-3].replace('/', '.')
    require(original['cohort'] == 'final-engine-dependents'
            and original['outcome']['returncode'] == 2
            and original['outcome']['counts'] == {'total': 241, 'failed': 3, 'error': 0, 'skipped': 0}
            and finding['required_clean_full_file'] == file,
            'original interrupted freshness finding differs')
    checked_pin(original['producer'], evidence)
    for pair in [*original['artifacts'].values(), original['cleanup']]:
        for key in ('original', 'snapshot'):
            checked_pin(pair[key], evidence)
    for pair in original['reviewed_sources'].values():
        checked_pin(pair['snapshot'], evidence)
        require(all(pair['snapshot'][key] == pair['original'][key] for key in ('bytes', 'sha256')),
                'historical source snapshot differs from its recorded original')
    cleanup = document(original['cleanup']['snapshot']['path'], evidence)
    require(cleanup['status'] == 'cleanup-confirmed'
            and cleanup['safe_to_release_source_freeze'] is True
            and all(row['original_reaped'] for row in [cleanup['runner'], cleanup['coordinator'],
                    *cleanup['workers'], *cleanup['observed_descendants']]),
            'original cohort cleanup is unconfirmed')
    recorded_cases = finding['cases']
    require(len(recorded_cases) == 3 and {row['name'] for row in recorded_cases} == expected
            and all(row['classname'] == module and row['nodeid'] == file + '::' + row['name']
                    for row in recorded_cases), 'original exact failed identities differ')
    for row in recorded_cases:
        for key, artifact in row['evidence'].items():
            if key == 'artifact_inventory':
                checked_pin(artifact, evidence)
            else:
                checked_pin(artifact['original'], evidence)
                checked_pin(artifact['snapshot'], evidence)
    proof = test_proof(file, None, directories, head, evidence)
    rows = cases(OUT / proof['cohort'] / 'pytest.xml')
    exact = [row for row in rows if row['classname'] == module and row['name'] in expected]
    require(len(exact) == 3 and {row['name'] for row in exact} == expected
            and all(row['status'] == 'passed' for row in exact),
            'the three exact failed parameter identities did not all pass')
    details.extend([proof, {'exact_failed_identities_passed': sorted(expected),
        'original_interrupted_cohort': original['cohort'], 'original_source_head': original['source_head'],
        'original_returncode': 2, 'original_junit_entries': 241,
        'original_log_passes': 237, 'original_failures': 3,
        'cause_established': False, 'source_correction_claimed': False}])
    return ('Required clean whole-file rerun verified in its recorded execution mode; '
            'original parallel failures and interrupted evidence retained, latency cause unresolved, '
            'no code correction claimed; lead filing remains required.')


'''


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not OUT.exists(), 'retain prior closure revision'
    ledger = SCRATCH / 'review-engine-freshness.json'
    value = json.loads(ledger.read_bytes())
    assert value['findings'][0]['finding_id'] == 'G2-REVIEW-ENGINE-FRESHNESS-F1'
    before = TARGET.read_bytes()
    source = before.decode()
    anchor = 'def close_legacy_rerun(identity, directories, head, evidence, details):'
    assert source.count(anchor) == 1 and 'def close_engine_freshness(' not in source
    source = source.replace(anchor, ACTION + anchor)
    old = "    for identity in ('G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2'):"
    new = """    identity = 'G2-REVIEW-ENGINE-FRESHNESS-F1'
    row, details = close(identity, lambda evidence, details: close_engine_freshness(
        directories, head, evidence, details))
    findings.append(row)
    proofs[identity] = details
""" + old
    assert source.count(old) == 1
    source = source.replace(old, new)
    assert source.count('after-scheduled-runner/result.json') == 4
    source = source.replace('after-scheduled-runner/result.json', 'after-engine-freshness/result.json')
    ast.parse(source, filename=str(TARGET))
    producers = []
    for name in ('bytecode_closure', 'auxiliary_discovery'):
        old_path = ROOT / 'scripts/adhoc' / ('verify_g2_' + name + '_after_scheduled_runner_20261114.py')
        new_path = ROOT / 'scripts/adhoc' / ('verify_g2_' + name + '_after_engine_freshness_20261114.py')
        assert not new_path.exists(), 'retain prior verifier producer'
        content = old_path.read_text().replace('scheduled-runner', 'engine-freshness')
        ast.parse(content, filename=str(new_path))
        producers.append((old_path, new_path, content.encode()))
    OUT.mkdir()
    snapshot = OUT / 'before-closure.py'
    save(snapshot, before)
    assert TARGET.read_bytes() == before
    TARGET.write_bytes(source.encode())
    assert TARGET.read_bytes() == source.encode()
    reviewed = OUT / 'after-closure.py'
    save(reviewed, TARGET.read_bytes())
    copied = []
    for old_path, new_path, content in producers:
        save(new_path, content)
        copied.append({'prior_producer': pin(old_path), 'new_producer': pin(new_path)})
    record = {'producer': pin(Path(__file__).resolve()), 'ledger': pin(ledger),
        'before_closure': pin(snapshot), 'after_closure': pin(reviewed),
        'current_closure': pin(TARGET), 'fresh_verifiers': copied,
        'scope': 'Freshness finding closure requires generic whole-file exit-0/source-equivalent full census plus exact three previously failed identities. Original evidence and unknown cause retained; no test acceptance is claimed here.'}
    target = OUT / 'revision.json'
    save(target, (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'revision': pin(target), 'closure': pin(TARGET),
                      'action': 'close_engine_freshness(directories, head, evidence, details)'}, indent=2))


if __name__ == '__main__':
    main()
