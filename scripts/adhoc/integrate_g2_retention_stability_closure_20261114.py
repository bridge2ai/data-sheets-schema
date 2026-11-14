#!/usr/bin/env python3
"""Retain open G2 selection-stability failure and parser-only closure, 2026-11-14.

Inputs: immutable retention review ledger and current closure/proof producers.
Outputs: exclusive before/after snapshots, bounded helper-only closure edits,
and newly authored F3/F4 proof wrappers. This producer does not run the wrappers,
tests, diagnostics, project imports, final closure/report, or Git mutations.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUT = SCRATCH / 'retention-stability-closure-20261114'
TARGET = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'
LEDGER = SCRATCH / 'review-retention-stability.json'
LEDGER_SHA = 'a4a88048b816e0f69fecb61a803cb3d6f054cb93e9d15677be38e9f457a16a40'

ADDITION = r'''def _retention_review(evidence):
    identity = 'G2-REVIEW-RETENTION-STABILITY-F1'
    original = ledger(identity, 'review-retention-stability.json', evidence)
    require(pin(OUT / 'review-retention-stability.json')['sha256']
            == 'a4a88048b816e0f69fecb61a803cb3d6f054cb93e9d15677be38e9f457a16a40',
            'original retention ledger differs')
    finding, = [row for row in original['findings'] if row['finding_id'] == identity]
    require(original['cohort'] == 'final-engine-lifecycles'
            and original['normal_completed_session'] is True and original['interrupted'] is False
            and original['outcome']['returncode'] == 1
            and original['outcome']['counts'] == {'total': 29, 'failed': 3, 'error': 0, 'skipped': 0}
            and original['junit_counts'] == {'total': 29, 'passed': 26, 'failed': 3, 'error': 0, 'skipped': 0}
            and finding['status'] == 'unresolved' and finding['cause_established'] is False
            and finding['source_correction_claimed'] is False,
            'retained normal completed failure identity/status differs')
    for key in ('producer', 'producer_snapshot', 'source_equivalence_evidence'):
        checked_pin(original[key], evidence)
    require(all(original['producer'][key] == original['producer_snapshot'][key]
                for key in ('bytes', 'sha256')),
            'retention producer differs from its immutable snapshot')
    for pair in original['artifacts'].values():
        for key in ('original', 'snapshot'):
            checked_pin(pair[key], evidence)
    for pair in original['reviewed_sources'].values():
        checked_pin(pair['snapshot'], evidence)
        require(all(pair['original'][key] == pair['snapshot'][key] for key in ('bytes', 'sha256')),
                'historical retention source snapshot differs')
    expected = {
        'test_public_failed_attempt_retains_records_and_reads_back_exactly[True]',
        'test_public_failed_attempt_retains_records_and_reads_back_exactly[False]',
        'test_public_finalization_after_injected_final_floor_failure',
    }
    rows = finding['cases']
    require(len(rows) == 3 and {row['name'] for row in rows} == expected
            and finding['required_clean_full_file'] == 'tests/test_native_incomplete_retention.py',
            'exact retention failure identities differ')
    for row in rows:
        checked_pin(row['traceback'], evidence)
        for pair in row['evidence'].values():
            checked_pin(pair['original'], evidence)
            checked_pin(pair['snapshot'], evidence)
        require(row['offending_path_known'] is False and row['changed_metadata_field_known'] is False,
                'original metadata uncertainty differs')
    return original, finding


def retain_retention_stability(evidence, details):
    original, finding = _retention_review(evidence)
    details.append({'original_cohort': original['cohort'], 'returncode': 1,
        'cases': 29, 'failed': 3, 'passed': 26, 'interrupted': False,
        'required_clean_full_file': finding['required_clean_full_file'],
        'cause_established': False, 'source_correction_claimed': False,
        'diagnostic_can_close': False, 'lead_filing_required': True})
    raise ValueError('Open retention stability finding: original normal completed cohort '
        'retains 3 failures and 26 passes (exit 1); offending path/metadata field and cause '
        'remain unknown. A one-node diagnostic is not acceptance and cannot close this finding; '
        'lead filing required.')


def close_retention_ledger(evidence, details):
    identity = 'G2-REVIEW-RETENTION-LEDGER-F1'
    original, finding = _retention_review(evidence)
    row, = [item for item in original['producer_review_findings'] if item['finding_id'] == identity]
    require(row['original_producer_sha256']
            == '6eaf18c8358f0d66e346c6b2cf27a199270c1fcdd34e4c5e7a19f724b86ee0b0'
            and row['original_delimiter'] == '_{4,}' and row['corrected_delimiter'] == '_{3,}'
            and row['lead_filing_required'] is True,
            'retained parser finding differs')
    producer = original['producer']
    require(Path(producer['path']) == ROOT / 'scripts/adhoc/record_g2_retention_stability_review_20261114.py'
            and producer['sha256'] == 'a11db2db417cbb9a272278327cd4728a50fee555b1edf88675d0e37f7ec4c6c2'
            and producer['bytes'] == 16479,
            'exact reviewed retention producer differs')
    source = Path(original['producer_snapshot']['path']).read_bytes()
    tree = ast.parse(source)
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
        and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == 'section']
    expected = ast.parse("section = re.search(r'^_{3,}\\s+' + re.escape(name) + r'\\s+_{3,}\\n(.*?)(?=^_{3,}\\s|^=+)', log, re.M | re.S)").body[0]
    require(len(assignments) == 1
            and ast.dump(assignments[0], include_attributes=False) == ast.dump(expected, include_attributes=False),
            'reviewed producer header parser differs')
    parser = compile(ast.Module(body=assignments, type_ignores=[]), producer['path'], 'exec')
    log = Path(original['artifacts']['pytest.log']['snapshot']['path']).read_text()
    validated = []
    for case in finding['cases']:
        namespace = {'re': re, 'name': case['name'], 'log': log}
        exec(parser, namespace)
        section = namespace['section']
        require(section is not None, 'retained header not recognized: ' + case['name'])
        text = section.group(1)
        require(text.encode() == Path(case['traceback']['path']).read_bytes()
                and '[' + case['worker'] + ']' in text
                and str(Path(case['fixture_root']).parent) in text
                and 'tests/test_native_incomplete_retention.py:' + str(case['setup_line']) + ':' in text
                and 'tests/test_native_shared_execution.py:35' in text
                and 'tests/native_shared_fixture.py:194' in text
                and 'native_shared_selection.py:528' in text
                and 'native_shared_selection.py:467' in text,
                'retained header/worker/fixture/traceback correspondence differs')
        validated.append(case['name'])
    require(validated == row['validated_case_headings_in_this_production'],
            'producer heading-validation identities differ')
    details.append({'cases': 3, 'passed': 3, 'validated_headings': validated,
        'scope': 'Exact corrected producer header assignment on the retained original log only; no project tests.',
        'original_defective_producer_hash_retained': row['original_producer_sha256'],
        'original_defective_producer_executed': False,
        'retention_stability_closed': False, 'lead_filing_required': True})
    return ('Parser-only repair verified: the exact corrected producer and immutable snapshot '
            'validate all three original traceback headings. Original producer hash retained without '
            'claiming execution of its unavailable pre-fix bytes. Retention stability remains open; '
            'lead filing required.')


'''


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as handle:
        handle.write(raw)
    assert path.read_bytes() == raw


def main():
    assert not OUT.exists(), 'preserve prior closure revision'
    assert pin(LEDGER)['sha256'] == LEDGER_SHA
    before = TARGET.read_bytes()
    source = before.decode()
    assert source.count('import json\n') == 1
    source = source.replace('import json\n', 'import json\nimport re\n')
    old = "    rows = value.get('findings', [value])\n"
    new = "    rows = [*value.get('findings', [value]), *value.get('producer_review_findings', [])]\n"
    assert source.count(old) == 1
    source = source.replace(old, new)
    anchor = 'def close_engine_freshness(directories, head, evidence, details):'
    assert source.count(anchor) == 1 and 'def retain_retention_stability(' not in source
    source = source.replace(anchor, ADDITION + anchor)
    old = "                             ('G2-REVIEW-BYTECODE-F1', close_bytecode)):"
    new = """                             ('G2-REVIEW-RETENTION-STABILITY-F1', retain_retention_stability),
                             ('G2-REVIEW-RETENTION-LEDGER-F1', close_retention_ledger),
""" + old
    assert source.count(old) == 1
    source = source.replace(old, new)
    assert source.count('after-engine-freshness/result.json') == 4
    source = source.replace('after-engine-freshness/result.json', 'after-retention-stability/result.json')
    ast.parse(source, filename=str(TARGET))
    wrappers = []
    for name in ('bytecode_closure', 'auxiliary_discovery'):
        prior = ROOT / 'scripts/adhoc' / ('verify_g2_' + name + '_after_engine_freshness_20261114.py')
        target = ROOT / 'scripts/adhoc' / ('verify_g2_' + name + '_after_retention_stability_20261114.py')
        assert not target.exists(), 'preserve prior verifier producer'
        content = prior.read_text().replace('engine-freshness', 'retention-stability')
        ast.parse(content, filename=str(target))
        wrappers.append((prior, target, content.encode()))
    OUT.mkdir()
    snapshot = OUT / 'before-closure.py'
    save(snapshot, before)
    assert TARGET.read_bytes() == before
    TARGET.write_bytes(source.encode())
    assert TARGET.read_bytes() == source.encode()
    after = OUT / 'after-closure.py'
    save(after, TARGET.read_bytes())
    authored = []
    for prior, target, content in wrappers:
        save(target, content)
        authored.append({'prior_producer': pin(prior), 'new_producer': pin(target), 'executed': False})
    record = {'producer': pin(Path(__file__).resolve()), 'ledger': pin(LEDGER),
        'before_closure': pin(snapshot), 'after_closure': pin(after), 'current_closure': pin(TARGET),
        'authored_verifiers': authored,
        'scope': 'Always-open retention stability finding and separate exact three-heading parser-only validation. Existing source-equivalence, reuse and test acceptance unchanged. No proof wrapper, project test, diagnostic or final report/closure executed.'}
    destination = OUT / 'revision.json'
    save(destination, (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'revision': pin(destination), 'closure': pin(TARGET),
        'actions': ['retain_retention_stability(evidence, details)', 'close_retention_ledger(evidence, details)'],
        'proof_wrappers_executed': False}, indent=2))


if __name__ == '__main__':
    main()
