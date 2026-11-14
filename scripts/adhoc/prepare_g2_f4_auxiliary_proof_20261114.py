#!/usr/bin/env python3
# Prepare retained pure verification revisions after REPORT-F4, 2026-11-14.
# Inputs: earlier standalone F2/F4 verifiers. Outputs: new verifier files only.
# Retains every earlier producer and partial proof; no project/tests execution.
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'scripts/adhoc'


def save(name, source):
    path = SCRIPTS / name
    ast.parse(source, filename=str(path))
    with path.open('x') as stream:
        stream.write(source)
    assert path.read_text() == source


def main():
    source = (SCRIPTS / 'verify_g2_cohort_discovery_20261114.py').read_text()
    source = source.replace('# Verify REPORT-F2 with actual helper functions, 2026-11-14.',
        '# Refresh REPORT-F2 after the exact REPORT-F4 auxiliary gate, 2026-11-14.')
    old = "names = {'classify_cohort', 'discover_cohorts', 'cohort_directories'}"
    assert source.count(old) == 1
    source = source.replace(old, "names = {'classify_cohort', 'classify_auxiliary', 'discover_cohorts', 'cohort_directories'}")
    old = "namespace = {'Path': Path, 'json': json, 'pin': pin, 'require': require}"
    assert source.count(old) == 1
    source = source.replace(old, "namespace = {'Path': Path, 'json': json, 'pin': pin, 'require': require, 'hashlib': hashlib, 'ROOT': ROOT}")
    source = source.replace("DEST = OUT / 'report-cohort-discovery-20261114/verification'",
                            "DEST = OUT / 'report-cohort-discovery-after-f4-reuse-auxiliary'")
    save('verify_g2_cohort_discovery_auxiliary_20261114.py', source)
    source = (SCRIPTS / 'verify_g2_f4_reuse_report_20261114.py').read_text()
    source = source.replace('# Verify exact legacy reuse plus refreshed report proof after F4, 2026-11-14.',
        '# Verify exact legacy reuse and report proof after REPORT-F4 auxiliary fix, 2026-11-14.')
    source = source.replace("DRIVER = ROOT / 'scripts/adhoc/verify_g2_report_bytecode_pin_review_20261114.py'",
                            "DRIVER = ROOT / 'scripts/adhoc/verify_g2_report_bytecode_review_20261114.py'")
    source = source.replace("F1 = SCRATCH / 'report-closure-pin-verification-after-f4-reuse'",
                            "F1 = SCRATCH / 'report-closure-pin-verification-after-f4-reuse-auxiliary'")
    source = source.replace("F2 = SCRATCH / 'report-cohort-discovery-after-f4-reuse'",
                            "F2 = SCRATCH / 'report-cohort-discovery-after-f4-reuse-auxiliary'")
    start = source.index('def main():\n')
    end = source.index("    helper = ROOT / 'scripts/adhoc/g2_legacy_leaf_reuse_6217_f4_20261114.py'", start)
    prefix = '''def main():
    integration = SCRATCH / 'report-f4-reuse-auxiliary-integration-20261114'
    assert not integration.exists() and not F1.exists() and not F2.exists()
    previous_path = SCRATCH / 'report-f4-reuse-integration-20261114/index.json'
    previous = json.loads(previous_path.read_bytes())
    partial = SCRATCH / 'report-cohort-discovery-after-f4-reuse'
    assert not (partial / 'result.json').exists(), 'earlier refresh unexpectedly completed'
    before = []
    for record in previous['current_helpers']:
        snapshot = partial / ('reviewed-' + Path(record['path']).name)
        actual = pin(snapshot)
        assert all(actual[key] == record[key] for key in ('bytes', 'sha256'))
        before.append({'source_name': record['path'], 'snapshot': actual})
    integration.mkdir()
    index = {'finding_id': 'G2-REVIEW-REPORT-F4', 'before_helpers': before,
        'historical_proofs': previous['historical_proofs'],
        'current_helpers': [pin(ROOT / 'scripts/adhoc/report_g2_launch_fixes_20261114.py'),
                            pin(ROOT / 'scripts/adhoc/record_g2_final_review_20261114.py')],
        'previous_integration': pin(previous_path),
        'failed_refresh_producer': pin(ROOT / 'scripts/adhoc/verify_g2_f4_reuse_report_20261114.py'),
        'auxiliary_review': pin(SCRATCH / 'review-report-f4.json'),
        'producer': pin(Path(__file__).resolve()),
        'scope': 'Retains the partial refresh which refused the known preservation outcome; current companions bind the narrowly corrected auxiliary classification.'}
    document(integration / 'index.json', index)
    source = DRIVER.read_text()
    replacements = (
        ("'scripts/adhoc/verify_g2_cohort_discovery_20261114.py'",
         "'scripts/adhoc/verify_g2_cohort_discovery_auxiliary_20261114.py'"),
        ("'report-cohort-discovery-after-bytecode-review/result.json'",
         "'report-cohort-discovery-after-f4-reuse-auxiliary/result.json'"))
    for old, new in replacements:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    namespace = {'__name__': 'retained_reporting_driver', '__file__': str(Path(__file__).resolve())}
    exec(compile(source, str(DRIVER), 'exec'), namespace)
    namespace.update(INTEGRATION=integration / 'index.json', F1=F1, F2=F2)
    namespace['main']()
'''
    source = source[:start] + prefix + source[end:]
    save('verify_g2_f4_reuse_auxiliary_20261114.py', source)
    source = (SCRIPTS / 'verify_g2_f4_closure_bindings_20261114.py').read_text()
    source = source.replace('# Verify G2 F4/legacy/proposal closure bindings without final closure, 2026-11-14.',
        '# Verify G2 F4/legacy/proposal bindings after REPORT-F4, 2026-11-14.')
    source = source.replace('report-closure-pin-verification-after-f4-reuse/closure-bindings.json',
                            'report-closure-pin-verification-after-f4-reuse-auxiliary/closure-bindings.json')
    save('verify_g2_f4_auxiliary_closure_bindings_20261114.py', source)
    print('Saved three standalone pure-verification revisions; no verification executed.')


if __name__ == '__main__':
    main()
