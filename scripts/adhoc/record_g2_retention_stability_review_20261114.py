#!/usr/bin/env python3
"""Retain G2-REVIEW-RETENTION-STABILITY-F1 evidence, 2026-11-14.

Inputs: completed final-engine-lifecycles command, outcome, JUnit, log, failed
fixture declarations and current source. Outputs: exclusive scratch ledger
review-retention-stability.json and retention-stability-review-20261114 snapshots.
This producer reads Git and files only; no project imports, probes, tests, process
inspection, signals, guard changes or changes to original evidence.
"""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
COHORT = SCRATCH / 'final-engine-lifecycles'
OUTPUT = SCRATCH / 'retention-stability-review-20261114'
LEDGER = SCRATCH / 'review-retention-stability.json'
IDENTITY = 'G2-REVIEW-RETENTION-STABILITY-F1'
ORIGINAL_HEAD = '1c1de9272fda49d537760e7de3205932686fb653'
BASELINE = 'f8604be5a'
FILE = 'tests/test_native_incomplete_retention.py'
MODULE = FILE[:-3].replace('/', '.')
REFUSAL = 'native authority changed before capture completed'
SOURCE_SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')
SELECTED = ('tests/test_native_admission_failure.py', FILE,
            'tests/test_native_failure_publication.py')
SOURCES = (FILE, 'tests/test_native_shared_execution.py', 'tests/native_shared_fixture.py',
           'src/data_sheets_schema/native_shared_selection.py',
           'tests/test_native_execution_registration_v2.py',
           'tests/test_native_shared_selection.py')
METADATA_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size',
                   'st_mtime_ns', 'st_ctime_ns')
CASES = (
    ('test_public_failed_attempt_retains_records_and_reads_back_exactly[True]',
     'gw1', 'test_public_failed_attempt_ret0', 'retained-runtime-failure', 171),
    ('test_public_failed_attempt_retains_records_and_reads_back_exactly[False]',
     'gw3', 'test_public_failed_attempt_ret0', 'retained-runtime-failure', 171),
    ('test_public_finalization_after_injected_final_floor_failure',
     'gw2', 'test_public_finalization_after0', 'public-final-floor', 257),
)
FIXTURE_FILES = ('authority/selection.json', 'authority/chunks.json',
                 'authority/context.json', 'authority/receipt-policy.json',
                 'authority/bundle.txt', 'sources.yaml')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'missing or aliased evidence: ' + str(path))
    raw = path.read_bytes()
    require(bool(raw), 'empty evidence: ' + str(path))
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    require(result.returncode == 0, 'Git check failed: ' + repr(args) + ': ' + result.stderr.decode())
    return result.stdout


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)
    require(path.read_bytes() == raw, 'saved evidence readback differs: ' + str(path))
    return pin(path)


def snapshot(path, destination, originals):
    original = pin(path)
    raw = Path(path).read_bytes()
    require(pin(path) == original, 'input changed while read: ' + str(path))
    saved = save(destination, raw)
    require(all(saved[key] == original[key] for key in ('bytes', 'sha256')),
            'snapshot differs from original: ' + str(path))
    originals.append(original)
    return {'original': original, 'snapshot': saved}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def row_status(node):
    states = [name for name in ('failure', 'error', 'skipped') if node.find(name) is not None]
    require(len(states) <= 1, 'ambiguous JUnit outcome')
    return {'failure': 'failed', 'error': 'error', 'skipped': 'skipped'}.get(
        states[0] if states else '', 'passed')


def main():
    require(not OUTPUT.exists() and not LEDGER.exists(), 'preserve all existing output artifacts')
    inputs = {name: pin(COHORT / name) for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log')}
    command = json.loads((COHORT / 'command.json').read_bytes())
    outcome = json.loads((COHORT / 'outcome.json').read_bytes())
    log = (COHORT / 'pytest.log').read_text()
    require(command['head'] == ORIGINAL_HEAD and command['cwd'] == str(ROOT), 'original source identity differs')
    expected_command = [str(ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'),
                        '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *SELECTED,
                        '-n', '4', '--dist', 'load', '--maxschedchunk=1',
                        '--basetemp=' + str(COHORT / 'cases'),
                        '--junitxml=' + str(COHORT / 'pytest.xml')]
    require(command['command'] == expected_command, 'actual whole-file scheduled invocation differs')
    require(command['environment']['PYTHONPATH'] == str(ROOT / 'src')
            and command['environment']['PYTHONDONTWRITEBYTECODE'] == '1', 'recorded environment differs')
    require(command['source_inventory']['ignored_and_hidden_files_included'] is True
            and command['source_inventory']['selected_paths'] == list(SELECTED), 'selected source inventory differs')
    expected_counts = {'total': 29, 'failed': 3, 'error': 0, 'skipped': 0}
    require(outcome['returncode'] == 1 and outcome['counts'] == expected_counts,
            'expected normal completed failure outcome differs')
    require(isinstance(outcome['seconds'], (int, float)) and outcome['seconds'] > 0,
            'runner duration is absent or invalid')
    summaries = re.findall(r'^3 failed, 26 passed(?:, \d+ warnings)? in .+$', log, re.M)
    require(len(summaries) == 1 and 'KeyboardInterrupt' not in log, 'completed pytest summary differs')
    tree = ET.parse(COHORT / 'pytest.xml')
    nodes = list(tree.iter('testcase'))
    identities = [(node.get('classname'), node.get('name')) for node in nodes]
    require(len(set(identities)) == len(nodes) == 29, 'duplicate or missing JUnit identity')
    counts = Counter(row_status(node) for node in nodes)
    require(counts == Counter({'passed': 26, 'failed': 3}), 'JUnit outcomes differ')
    suites = list(tree.iter('testsuite'))
    require(len(suites) == 1 and all(int(suites[0].get(key, '-1')) == value
            for key, value in {'tests': 29, 'failures': 3, 'errors': 0, 'skipped': 0}.items()),
            'JUnit suite totals differ')
    expected_names = {row[0] for row in CASES}
    failed = {node.get('name'): node for node in nodes if row_status(node) == 'failed'}
    require(set(failed) == expected_names and all(node.get('classname') == MODULE for node in failed.values()),
            'exact failed identities differ')
    logged = re.findall(r'^FAILED (\S+)', log, re.M)
    require(len(logged) == 3 and set(logged) == {FILE + '::' + name for name in expected_names},
            'log failed identities differ from JUnit')
    head = git('rev-parse', 'HEAD').decode().strip()
    baseline = git('rev-parse', BASELINE + '^{commit}').decode().strip()
    git('merge-base', '--is-ancestor', ORIGINAL_HEAD, head)
    git('diff', '--exit-code', ORIGINAL_HEAD, head, '--', *SOURCE_SCOPE)
    git('diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE)
    source_raw = {name: (ROOT / name).read_bytes() for name in SOURCES}
    for name, raw in source_raw.items():
        require(raw == git('show', baseline + ':' + name), 'relevant source differs from candidate: ' + name)
    selection_tree = ast.parse(source_raw['src/data_sheets_schema/native_shared_selection.py'])
    metadata, = [node for node in selection_tree.body if isinstance(node, ast.FunctionDef) and node.name == '_metadata']
    returned, = [node for node in metadata.body if isinstance(node, ast.Return)]
    require(isinstance(returned.value, ast.Tuple)
            and tuple(node.attr for node in returned.value.elts if isinstance(node, ast.Attribute)) == METADATA_FIELDS
            and len(returned.value.elts) == len(METADATA_FIELDS), 'metadata comparison fields differ')
    cases = []
    for name, worker, leaf, fixture_leaf, line in CASES:
        section = re.search(r'^_{3,}\s+' + re.escape(name) + r'\s+_{3,}\n(.*?)(?=^_{3,}\s|^=+)', log, re.M | re.S)
        require(section is not None, 'missing failed case traceback: ' + name)
        text = section.group(1)
        case_root = COHORT / 'cases' / ('popen-' + worker) / leaf
        fixture = case_root / fixture_leaf
        require('[' + worker + ']' in text and str(case_root) in text, 'worker/fixture mapping differs')
        require(FILE + ':' + str(line) + ':' in text
                and 'tests/test_native_shared_execution.py:35' in text
                and 'tests/native_shared_fixture.py:194' in text
                and 'native_shared_selection.py:528' in text
                and 'native_shared_selection.py:467' in text, 'traceback boundary differs')
        require(source_raw[FILE].decode().splitlines()[line - 1].strip()
                == "fixture = make_case(tmp_path / '" + fixture_leaf + "')", 'source setup line differs')
        failure = failed[name].find('failure')
        require(failure.get('message') == 'ValueError: ' + REFUSAL
                and REFUSAL in (failure.text or ''), 'JUnit refusal differs')
        declaration = json.loads((fixture / 'authority/selection.json').read_bytes())
        require(declaration['registration_path'] == str(fixture / 'authority/selection.json')
                and declaration['stage_root'] == str(fixture / 'fresh-attempt/stages'), 'fixture declaration paths differ')
        for relative in FIXTURE_FILES:
            pin(fixture / relative)
            if relative.endswith('.json'):
                json.loads((fixture / relative).read_bytes())
        cases.append({'name': name, 'nodeid': FILE + '::' + name, 'classname': MODULE,
                      'worker': worker, 'fixture_root': str(fixture), 'setup_line': line,
                      'failure': {'message': failure.get('message'), 'text': failure.text or ''},
                      'traceback_text': text})
    for name, expected in inputs.items():
        require(pin(COHORT / name) == expected, 'cohort evidence changed during validation')
    OUTPUT.mkdir(parents=False, exist_ok=False)
    originals = []
    artifacts = {name: snapshot(COHORT / name, OUTPUT / 'cohort' / name, originals) for name in inputs}
    sources = {name: snapshot(ROOT / name, OUTPUT / 'sources' / name, originals) for name in SOURCES}
    for row in cases:
        fixture = Path(row['fixture_root'])
        target = OUTPUT / 'cases' / row['worker']
        row['evidence'] = {name: snapshot(fixture / name, target / name, originals) for name in FIXTURE_FILES}
        row['traceback'] = save(target / 'traceback.txt', row.pop('traceback_text').encode())
        row['boundary'] = 'Fixture selection capture failed before intended retention/runtime injections and before launch.'
        row['offending_path_known'] = False
        row['changed_metadata_field_known'] = False
    producer = snapshot(Path(__file__).resolve(), OUTPUT / 'producer.py', originals)
    scope = {
        'recorded_head': ORIGINAL_HEAD, 'current_head': head, 'source_scope': list(SOURCE_SCOPE),
        'recorded_head_is_ancestor': True, 'source_scope_diff_empty': True, 'tracked_source_scope_clean': True,
        'baseline_head': baseline, 'unchanged_relevant_files': list(SOURCES),
        'limitation': 'Relevant source equality is not a baseline failure reproduction and does not establish a cause.'}
    scope_pin = save(OUTPUT / 'source-equivalence.json', json_bytes(scope))
    result = {
        'finding_id': IDENTITY, 'status': 'unresolved', 'lead_filing_required': True,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'producer': producer['original'],
        'producer_snapshot': producer['snapshot'], 'current_head': head, 'source_head': ORIGINAL_HEAD,
        'cohort': COHORT.name, 'artifacts': artifacts, 'reviewed_sources': sources,
        'source_equivalence': scope, 'source_equivalence_evidence': scope_pin,
        'outcome': outcome, 'junit_counts': {'total': 29, 'passed': 26, 'failed': 3, 'error': 0, 'skipped': 0},
        'log_summary': summaries[0], 'normal_completed_session': True, 'interrupted': False,
        "producer_review_findings": [{
            "finding_id": "G2-REVIEW-RETENTION-LEDGER-F1",
            "status": "confirmed; narrow delimiter correction authored and separately reviewed before production",
            "lead_filing_required": True,
            "original_producer_sha256": "6eaf18c8358f0d66e346c6b2cf27a199270c1fcdd34e4c5e7a19f724b86ee0b0",
            "defect": "The original four-or-more underscore heading regex refused the saved three-underscore parameterized failure headings before any output was written.",
            "correction": "Accept three-or-more underscores on both sides and at the next-heading boundary; preserve exact escaped case identity, worker, fixture path and source-frame checks.",
            "original_delimiter": "_{4,}", "corrected_delimiter": "_{3,}",
            "consequence": "Original producer would refuse evidence production; no original cohort evidence or acceptance result was changed.",
            "validated_case_headings_in_this_production": [row[0] for row in CASES],
            "verification_scope": "This production must successfully validate all three original tracebacks before saving any ledger; no project test or broader runtime claim."}],
        'acceptance': {'completed_passing_assertions': 26, 'whole_invocation_accepted': False,
                       'reason': 'The three-file invocation returned 1; its 26 completed passing cases do not provide clean whole-file acceptance.'},
        'findings': [{'finding_id': IDENTITY, 'status': 'unresolved', 'lead_filing_required': True,
                      'required_clean_full_file': FILE, 'cases': cases,
                      'proven': ['All three exact failures occurred at the final selection-capture stability check during fixture construction.',
                                 'The intended retention/runtime injections and launch calls were not reached.',
                                 'The metadata comparison includes device, inode, mode, link count, size, mtime and ctime; it excludes atime.',
                                 'Relevant source and fixture bytes are unchanged from the candidate baseline.'],
                      'unknown': ['The saved traceback does not name the offending path or changed metadata field.',
                                  'No baseline failure reproduction, G2 causation, host cause or concurrency cause is established.',
                                  'Current retained declaration bytes do not reconstruct the metadata at the failing comparison.'],
                      'metadata_fields': list(METADATA_FIELDS), 'atime_compared': False,
                      'source_correction_claimed': False, 'cause_established': False}],
        'actions': {'project_imports': False, 'tests_executed': False, 'probes': False,
                    'process_inspection': False, 'signals_sent': False, 'interruption_created': False,
                    'source_changes': [], 'test_changes': [], 'guard_changes': [], 'clock_changes': [],
                    'limit_changes': [], 'original_evidence_changes': [], 'commits': False}}
    for expected in originals:
        require(pin(expected['path']) == expected, 'original changed before ledger publication')
    require(git('rev-parse', 'HEAD').decode().strip() == head, 'HEAD changed during provenance capture')
    git('diff', '--exit-code', ORIGINAL_HEAD, 'HEAD', '--', *SOURCE_SCOPE)
    git('diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE)
    ledger_pin = save(LEDGER, json_bytes(result))
    require(json.loads(LEDGER.read_bytes()) == result, 'ledger JSON readback differs')
    print(json.dumps({'ledger': ledger_pin, 'snapshots': str(OUTPUT),
                      'finding_id': IDENTITY, 'status': result['status']}, sort_keys=True))


if __name__ == '__main__':
    main()
