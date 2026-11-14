#!/usr/bin/env python3
# Retain G2-REVIEW-6217-F4 before the running cohort traceback, 2026-11-14.
# Inputs: frozen test/encoder/engine sources and completed case publication bytes.
# Outputs: immutable source/artifact snapshots and review-6217-f4.json.
# Pure stdlib inspection only; no project imports, tests, signals or source edits.
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OUTPUT = SCRATCH / 'publication-encoding-review-6217'
LEDGER = SCRATCH / 'review-6217-f4.json'
CASE = SCRATCH / 'final-regressions/cases/popen-gw1/test_public_first_signal_durin0/publication-signals'
SOURCES = (
    'tests/test_native_publication_signals.py',
    'src/data_sheets_schema/native_shared_contract.py',
    'src/data_sheets_schema/native_attribution_registration.py',
    'src/data_sheets_schema/native_execution_orchestration.py',
)


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def source_row(name, token):
    original = ROOT / name
    raw = original.read_bytes()
    lines = raw.decode().splitlines()
    found = [number for number, line in enumerate(lines, 1) if token in line]
    assert len(found) == 1, (name, token)
    return {'source_name': str(original), 'snapshot': pin(OUTPUT / 'sources' / name),
            'line': found[0], 'text': lines[found[0] - 1]}


def main():
    assert not OUTPUT.exists() and not LEDGER.exists(), 'retain earlier F4 evidence'
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    assert head == '49cba53ab97f066c7d37750bb490afec2b95268d', 'source freeze changed'
    source_raw = {name: (ROOT / name).read_bytes() for name in SOURCES}
    final_path, marker_path = CASE / 'native-evidence/final.json', CASE / 'native-evidence/published.json'
    final_raw, marker_raw = final_path.read_bytes(), marker_path.read_bytes()
    cleanup_raw = (CASE / 'native-attempt/keep-awake.json').read_bytes()
    value, marker, cleanup = json.loads(final_raw), json.loads(marker_raw), json.loads(cleanup_raw)
    compact = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
    publication = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                              allow_nan=False) + '\n').encode()
    assert final_raw == publication and final_raw != compact
    assert marker['final_sha256'] == hashlib.sha256(final_raw).hexdigest()
    assert value['keep_awake'] == cleanup
    assert value['state'] == 'failed' and value['runtime_gates_passed'] is False
    assert value['first_stop'] == 'launch or runtime failed: RuntimeError'
    OUTPUT.mkdir()
    for name, raw in source_raw.items():
        save(OUTPUT / 'sources' / name, raw)
    artifacts = []
    for original, raw in ((final_path, final_raw), (marker_path, marker_raw),
                          (CASE / 'native-attempt/keep-awake.json', cleanup_raw)):
        destination = OUTPUT / 'artifacts' / original.name
        save(destination, raw)
        artifacts.append({'source_name': str(original), 'snapshot': pin(destination)})
    log = SCRATCH / 'final-regressions/pytest.log'
    save(OUTPUT / 'partial-pytest.log', log.read_bytes())
    save(OUTPUT / 'publication-reencoded.json', publication)
    save(OUTPUT / 'compact-test-oracle.json', compact)
    trace = [
        source_row(SOURCES[0], "from data_sheets_schema import native_shared_contract as c"),
        source_row(SOURCES[0], "assert (evidence / 'final.json').read_bytes() == c.canonical(result)"),
        source_row(SOURCES[1], 'separators=(",", ":")).encode("utf-8")'),
        source_row(SOURCES[2], "return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)"),
        source_row(SOURCES[3], 'from data_sheets_schema import native_attribution_registration as draft'),
        source_row(SOURCES[3], 'final_raw = draft._encoded(final)'),
        source_row(SOURCES[3], "durable_new(evidence/'final.json', final_raw)"),
        source_row(SOURCES[0], "assert marker['final_sha256'] == c.sha((evidence / 'final.json').read_bytes())"),
        source_row(SOURCES[0], "assert execute.read_final(case['raw']) == result"),
    ]
    result = {'finding_id': 'G2-REVIEW-6217-F4', 'priority': 'P2',
        'status': 'confirmed test oracle defect; correction and complete regression proof pending',
        'finding': 'Public signal witnesses compare the published final bytes with a different JSON encoding than the engine writes.',
        'head': head, 'test_function': 'test_public_first_signal_during_publication_keeps_exact_readback',
        'source_trace': trace, 'retained_artifacts': artifacts,
        'encoding_proof': {'actual_matches_established_publication_encoder': True,
            'actual_matches_test_compact_encoder': False,
            'actual_prefix_hex': final_raw[:24].hex(), 'compact_prefix_hex': compact[:24].hex(),
            'publication_reencoding': pin(OUTPUT / 'publication-reencoded.json'),
            'compact_test_oracle': pin(OUTPUT / 'compact-test-oracle.json'),
            'publication_marker_hash_matches': True, 'cleanup_object_matches_saved_bytes': True,
            'saved_state': value['state'], 'saved_first_stop': value['first_stop'],
            'method': 'Stdlib json encodings copied exactly from the frozen source definitions; no project code executed.'},
        'pytest_failure_attribution': {'status': 'provisional; cohort still active and no traceback saved',
            'partial_log_snapshot': pin(OUTPUT / 'partial-pytest.log'),
            'case_directory_is_not_pytest_node_identity': True,
            'claim': 'The mismatched byte assertion must fail if reached with the ordinary final result. The displayed F is not assigned to this assertion until saved traceback/JUnit confirms it.'},
        'required_repair': 'Use the established publication encoding for the exact-byte oracle; preserve exact-byte, marker-hash, cleanup and independent read_final assertions. No production change is established as necessary.',
        'lead_filing_required': True, 'github_write_performed': False,
        'source_or_tests_edited': False, 'tests_executed': False,
        'producer': pin(Path(__file__).resolve())}
    save(LEDGER, (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    for name, raw in source_raw.items():
        assert (ROOT / name).read_bytes() == raw
    assert final_path.read_bytes() == final_raw and marker_path.read_bytes() == marker_raw
    print(json.dumps({'ledger': pin(LEDGER), 'actual_final': pin(OUTPUT / 'artifacts/final.json'),
        'publication_encoder_matches': True, 'compact_encoder_matches': False,
        'pytest_failure_cause': 'provisional until saved traceback'}))


if __name__ == '__main__':
    main()
