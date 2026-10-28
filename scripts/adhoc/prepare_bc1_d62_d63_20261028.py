"""D62/D63 offline evidence, 2026-10-28.

Inputs: read-only CHORUS 10-22a intermediate/root records and git 8f83d6cb3.
Outputs: A21 registration/sidecar/roster, one fixed worker payload and measurements
under notes/reviews. Uses production CLI and renderers; blocks all network I/O.
Never imports or runs d63_count_tokens_20261028.py. Run with project Python -S -B.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# Reuse retained read-only rendering/provenance helpers and their network guard.
from scripts.adhoc import measure_bc1_d59_20261028 as h

h.BASE = '8f83d6cb3'
OUT = ROOT / 'notes/reviews'
A21 = OUT / 'a21_chorus_d62_2026-10-28'
LABEL = '2026-10-28a_claude-opus-5-api-bc1-a21_rep1'
REGISTRATION = A21 / f'registration_chorus_{LABEL}.json'
REQUEST = OUT / 'd63_count_tokens_request_2026-10-28.json'
INTERMEDIATE = h.LAUNCH / h.LABELS['CHORUS'] / 'intermediate'


def parity_snapshot(baseline):
    """Separate-process byte identities; restore only modified legacy functions."""
    options = dict(project='CHORUS', label='offline_d62_parity', partition='chorus',
                   registration_path=OUT / 'UNWRITTEN_d62_parity.json')
    prepare = h.original(h.builder, 'prepare_registration') if baseline else h.builder.prepare_registration
    build = h.original(h.api, 'build_phase') if baseline else h.api.build_phase
    parent, outputs, _ = prepare(**options)
    files = h.builder.SizingRecord.in_directory(INTERMEDIATE, 'CHORUS', effective_receipt=True)
    wires = h.downstream(parent, files, build, h.context.schema_context,
                         bounded=False, scenario='empty_future_floor')
    return {
        'registration': {'bytes': len(h.sg.canonical(parent)), 'sha256': h.sg.sha(h.sg.canonical(parent))},
        'outputs': {str(path): {'bytes': len(raw), 'sha256': h.sg.sha(raw)} for path, raw in outputs},
        'requests': {key: h.metrics(value) for key, value in wires.items()}}


def main():
    if sys.argv[1:] == ['--verify']:
        report = json.loads((OUT / 'bc1_d62_d63_measurements_2026-10-28.json').read_bytes())
        registration = REGISTRATION.read_bytes()
        h.builder.check_registration_sizing(REGISTRATION, registration)
        assert h.sg.sha(registration) == report['registration_sha256']
        raw = REQUEST.read_bytes()
        assert len(raw) == report['d63_request']['bytes']
        assert h.sg.sha(raw) == report['d63_request']['sha256']
        # Parse only: never import or execute the provider script.
        tree = ast.parse((ROOT / 'scripts/adhoc/d63_count_tokens_20261028.py').read_text())
        pin = next(node.value.value for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'EXPECTED_SHA256' for t in node.targets))
        assert pin == h.sg.sha(raw)
        calls = [node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
        assert calls.count('_measure_context') == 1
        assert not {'create', 'stream', '_call_with_usage', '_call_with_retry', '_count_context'} & set(calls)
        for path, expected in report['source_pins'].items():
            data = Path(path).read_bytes()
            assert expected == {'bytes': len(data), 'sha256': h.sg.sha(data)}, path
        protected = ROOT / 'src/data_sheets_schema/shared_generation.py'
        assert h.sg.sha(protected.read_bytes()) == report['protected_shared_generation_sha256']
        print('Saved registration, source pins and D63 checksum/AST verified offline; D63 not executed.')
        return
    if len(sys.argv) == 3 and sys.argv[1] == '--parity-snapshot':
        print(json.dumps(parity_snapshot(sys.argv[2] == 'baseline'), sort_keys=True))
        return
    snapshots = []
    for mode in ('baseline', 'current'):
        raw = subprocess.check_output([sys.executable, '-S', '-B', str(Path(__file__).resolve()),
                                       '--parity-snapshot', mode], cwd=ROOT)
        snapshots.append(json.loads(raw))
    assert snapshots[0] == snapshots[1], 'Non-BC1 registration/request parity changed'
    print('Non-BC1 registration, outputs and ten requests are byte-identical.', flush=True)

    cli_args = ['-p', 'CHORUS', '-l', LABEL, '--partition', 'chorus',
                '--bounded-carry-version', '1', '--aggregate-input-tokens', '4500000',
                '--sizing-record', f'CHORUS={INTERMEDIATE}', '-o', str(A21)]
    h.builder.cli.main(args=cli_args, standalone_mode=False)
    raw_registration = REGISTRATION.read_bytes()
    registration = json.loads(raw_registration)
    sidecar = h.builder.check_registration_sizing(REGISTRATION, raw_registration)
    files = h.builder.SizingRecord.in_directory(INTERMEDIATE, 'CHORUS', effective_receipt=True)
    captured = h.captured(registration)
    wires = []
    sizing = h.sizing.size_inputs(registration, sizing_record=files,
        context_raw=h.read(registration['inputs']['context']['path']), schema_snapshot=captured.full_schema,
        payload_sink=lambda row, raw: wires.append((row, raw)))
    assert sizing == sidecar['sizing'], 'Saved CLI sidecar differs from fresh production sizing'
    h.sizing.check_sizing_record(registration, sizing)
    fixed = [(row, raw) for row, raw in wires if row['stage'].get('worker_id') == 'worker_0001']
    assert len(fixed) == 1
    worker, request = fixed[0]
    payload = json.loads(request)
    assert {'model', 'system', 'messages'} <= set(payload)
    assert not {'tools', 'cache_control'} & set(payload)
    assert h.sg.canonical(payload) == request
    REQUEST.write_bytes(request)
    assert REQUEST.read_bytes() == request and REQUEST.stat().st_size > 0
    request_pin = {'path': str(REQUEST), 'sha256': h.sg.sha(request), 'bytes': len(request),
                   'stage': worker['stage'], 'registration_sha256': h.sg.sha(raw_registration),
                   'counting': 'receipt_completion._measure_context; max_tokens is not sent to count_tokens',
                   'actual_provider_input_tokens': None}
    REQUEST.with_suffix('.sha256').write_text(request_pin['sha256'] + '  ' + REQUEST.name + '\n')
    table = []
    for row in sizing['rows']:
        if row['scenario'] not in ('captured_record', h.sizing.CAPS):
            continue
        stage = row['stage']
        room = min(registration['audit_limits']['max_input_tokens_per_call'],
                   registration['audit_limits']['context_limit_tokens'] - row['output_token_reserve'])
        floor = next((r for r in sizing['rows'] if r['stage'] == stage and r['scenario'] == h.sizing.FLOOR), row)
        table.append({'call': stage.get('worker_id', stage.get('stage_id', 'omission')), 'room': room,
                      'request_tokens': floor['estimated_input_tokens'], 'caps_tokens': row['estimated_input_tokens'],
                      'caps_fraction': row['estimated_input_tokens'] / room})
    protected = ROOT / 'src/data_sheets_schema/shared_generation.py'
    assert protected.read_bytes() == subprocess.check_output(['git', 'show', f'{h.BASE}:{protected.relative_to(ROOT)}'])
    for path in (files.full, files.core, files.receipt, files.receipt_result):
        h.read(path)
    for path, pin in h.SOURCE_PINS.items():
        raw = Path(path).read_bytes()
        assert pin == {'bytes': len(raw), 'sha256': h.sg.sha(raw)}, path
    report = {'baseline': h.BASE, 'cli_args': cli_args, 'gate': 'PASS', 'calibration': h.sizing.calibration(),
              'registration_path': str(REGISTRATION), 'registration_sha256': h.sg.sha(raw_registration),
              'table': table, 'scenarios': sizing['own_plan_scenarios'], 'd63_request': request_pin,
              'non_bc1_parity': snapshots[1], 'source_pins': h.SOURCE_PINS,
              'protected_shared_generation_sha256': h.sg.sha(protected.read_bytes()),
              'limitations': ['Historical CHORUS record; future record size and provider counts unverified.',
                              'Fixed production worker request uses the sizing generation UUID placeholder.',
                              'D63 script not executed; no provider or count_tokens calls.']}
    destination = OUT / 'bc1_d62_d63_measurements_2026-10-28.json'
    destination.write_bytes(h.sg.canonical(report) + b'\n')
    assert json.loads(destination.read_bytes()) == report
    print(json.dumps({'table': table, 'scenarios': report['scenarios'], 'd63_request': request_pin}, indent=2))


if __name__ == '__main__':
    main()
