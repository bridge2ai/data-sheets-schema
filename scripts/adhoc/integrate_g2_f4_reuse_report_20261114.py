#!/usr/bin/env python3
# Integrate exact legacy reuse and F4 correction into G2 report, 2026-11-14.
# Inputs: corrected report/closure evidence and immutable prior helper proofs.
# Outputs: bounded reporter edits and immutable before/proof-resolution index.
# No pytest, project imports, final handoff, source/test edits or commits.
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUTPUT = SCRATCH / 'report-f4-reuse-integration-20261114'
REPORT = ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'
CLOSURE = ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def replace(body, old, new):
    assert body.count(old) == 1, old
    return body.replace(old, new)


def main():
    assert not OUTPUT.exists(), 'retain earlier revision evidence'
    assert (SCRATCH / 'review-6217-f4-confirmed.json').is_file()
    before = REPORT.read_bytes()
    body = before.decode()
    body = replace(body, "'review-bytecode.json', 'review-report-f3.json')",
                   "'review-bytecode.json', 'review-report-f3.json', 'review-6217-f4-confirmed.json')")
    body = replace(body,
        "    'G2-REVIEW-6217-F2': REGRESSIONS[6217]['tests/test_native_publication_signals.py'],",
        "    'G2-REVIEW-6217-F2': REGRESSIONS[6217]['tests/test_native_publication_signals.py'],\n"
        "    'G2-REVIEW-6217-F4': ('test_public_first_signal_during_publication_keeps_exact_readback',),")
    body = replace(body, "        if identity == 'G2-REVIEW-6218-F2':",
        "        if identity == 'G2-REVIEW-6217-F4':\n"
        "            proof.append(coverage['tests/test_native_publication_signals.py'])\n"
        "        if identity == 'G2-REVIEW-6218-F2':")
    body = replace(body, 'report-closure-pin-verification-after-bytecode-pin-review/result.json',
                   'report-closure-pin-verification-after-f4-reuse/result.json')
    old = "    row['source_equivalence'] = equivalence_cache[recorded_head]\n"
    new = '''    row['source_equivalence'] = dict(equivalence_cache[recorded_head])
    # This overlay belongs only to the exact retained invocation. Never put it
    # in the head-keyed cache or grant it to another cohort at the same HEAD.
    if directory == SCRATCH / 'legacy-full-serial' and not row['source_equivalence']['passed']:
        import runpy
        helper = ROOT / 'scripts/adhoc/g2_legacy_leaf_reuse_6217_f4_20261114.py'
        try:
            validate = runpy.run_path(str(helper))['validate_reuse']
            proofs = [validate(ROOT, SCRATCH, recorded_head, final, file, directory) for file in (
                'tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py')]
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            row['source_equivalence']['reuse_refused'] = str(error)
        else:
            row['source_equivalence'].update(passed=True, strict_source_equality=False,
                basis='Exact legacy149 invocation reused across the reviewed F4 leaf-test correction only.',
                legacy_reuse=proofs)
'''
    body = replace(body, old, new)
    anchor = "    proposals[6207]['review'] = {'record': proposal_review, 'evidence': pin(proposal_review_path)}\n"
    extra = '''    # Proposal applicability is a source/patch check, never test acceptance.
    import runpy
    reuse_helper = ROOT / 'scripts/adhoc/g2_legacy_leaf_reuse_6217_f4_20261114.py'
    leaf_scope = runpy.run_path(str(reuse_helper))['scope_proof'](head)
    assert proposal['head'] == '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'
    production_scope = tuple(name for name in SOURCE_SCOPE if name != 'tests')
    assert not git('diff', '--name-only', proposal['head'], head, '--', *production_scope)
    current_sources = [checked_pin(row) for row in proposal_review['current_sources']]
    apply_command = ['git', 'apply', '--check', proposal['patch']['path']]
    apply_result = subprocess.run(apply_command, cwd=ROOT, capture_output=True, check=False)
    assert apply_result.returncode == 0, apply_result.stderr.decode()
    proposals[6207]['current_applicability'] = {
        'passed': True, 'proposal_head': proposal['head'], 'current_head': head,
        'production_scope': list(production_scope), 'current_sources': current_sources,
        'reviewed_leaf_test_drift': leaf_scope, 'scope_validator': pin(reuse_helper),
        'apply_check': {'command': apply_command, 'returncode': apply_result.returncode,
                        'stdout': apply_result.stdout.decode(), 'stderr': apply_result.stderr.decode()},
        'basis': 'Exact proposal base bytes and production scope remain unchanged; the F4 leaf-test drift is recorded separately. No proposed code or test was executed.'}
'''
    body = replace(body, anchor, anchor + extra)
    anchor = "    assert interruption['safe_to_release_source_freeze'] is True\n"
    extra = '''    oracle_cleanup_path = SCRATCH / 'final-regressions-interruption-6217-oracle/cleanup-1794637161740208000.json'
    oracle_cleanup = read_json(oracle_cleanup_path)
    check_nested_pins(oracle_cleanup)
    assert oracle_cleanup['status'] == 'cleanup-confirmed' and oracle_cleanup['safe_to_release_source_freeze'] is True
    assert all(row['original_reaped'] is True for row in (
        oracle_cleanup['coordinator'], oracle_cleanup['runner'], *oracle_cleanup['workers'],
        *oracle_cleanup['observed_descendants']))
'''
    body = replace(body, anchor, anchor + extra)
    body = replace(body,
        "        'interrupted_cohort_cleanup': {'record': interruption, 'evidence': pin(interruption_path)},",
        "        'interrupted_cohort_cleanup': {'record': interruption, 'evidence': pin(interruption_path)},\n"
        "        'publication_oracle_interruption': {'record': oracle_cleanup, 'evidence': pin(oracle_cleanup_path)},")
    anchor = "        if row['interrupted']:\n            log_summary = row.get('pytest_summary')\n"
    body = replace(body, anchor,
        "        if row['source_equivalence'].get('legacy_reuse'):\n"
        "            lines.append('  Reused exact legacy149 evidence from HEAD 2070a2116 across only the reviewed publication-test oracle correction 21367471; all shared source, fixtures and selected nodes remain unchanged.')\n"
        + anchor)
    ast.parse(body, filename=str(REPORT))
    assert 'report-closure-pin-verification-after-f4-reuse/result.json' in CLOSURE.read_text()
    assert 'report-cohort-discovery-after-f4-reuse/result.json' in CLOSURE.read_text()
    OUTPUT.mkdir()
    snapshot = OUTPUT / 'before-report.py'
    save(snapshot, before)
    historical = []
    for name, resolutions in (
        ('report-closure-pin-verification-after-bytecode-pin-review/result.json', {
            'reporter': SCRATCH / 'report-closure-pin-verification-after-bytecode-pin-review/reviewed-report-source.py'}),
        ('report-cohort-discovery-after-bytecode-pin-review/result.json', {
            'reporter': SCRATCH / 'report-cohort-discovery-after-bytecode-pin-review/reviewed-report_g2_launch_fixes_20261114.py',
            'closure': SCRATCH / 'report-cohort-discovery-after-bytecode-pin-review/reviewed-record_g2_final_review_20261114.py'})):
        path = SCRATCH / name
        value = json.loads(path.read_bytes())
        rows = []
        for key, frozen in resolutions.items():
            recorded, actual = value[key], pin(frozen)
            assert all(recorded[field] == actual[field] for field in ('bytes', 'sha256'))
            rows.append({'key': key, 'source_name': recorded['path'], 'snapshot': actual})
        historical.append({'artifact': pin(path), 'source_resolutions': rows})
    assert REPORT.read_bytes() == before
    REPORT.write_text(body)
    assert REPORT.read_bytes() == body.encode()
    result = {'finding_id': 'G2-REVIEW-6217-F4',
        'before_helpers': [{'source_name': str(REPORT), 'snapshot': pin(snapshot)}],
        'historical_proofs': historical, 'current_helpers': [pin(REPORT), pin(CLOSURE)],
        'reuse_record': pin(SCRATCH / 'legacy-leaf-reuse-6217-f4/reuse.json'),
        'original_review': pin(SCRATCH / 'review-6217-f4.json'),
        'confirmed_review': pin(SCRATCH / 'review-6217-f4-confirmed.json'),
        'producer': pin(Path(__file__).resolve()),
        'scope': 'Exact legacy149 invocation/census reuse, fresh F4 publication proof still required; proposal applicability is not test proof.'}
    save(OUTPUT / 'index.json', (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'index': pin(OUTPUT / 'index.json'), 'helpers': result['current_helpers']}))


if __name__ == '__main__':
    main()
