"""Capture BC1 canonical requests for P4a1, 2026-10-31.

Inputs: before/after argument; scratch schema/code, archived 2026-10-22a CHORUS.
Outputs: .bc1-byte-evidence/<condition>/ canonical payloads, registration, sizing,
catalogs, identities and errors. Provider/ledger-free; future responses explicitly
marked as sizing scenarios. Run via offline.py with the existing project Python.
"""
from contextlib import ExitStack
from copy import deepcopy
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

from scripts import build_api_registrations as builder
from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import receipt_completion as rc, bc1_runtime as runtime
from data_sheets_schema import bc1_registration as sizing, bc1_context as context
from data_sheets_schema.resources import resource_root

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / '.bc1-byte-evidence'
# G2 / 2026-11-01: preserve the reviewed capture path, accepting an explicit
# read-only historical archive because validation lives under scratch-g2.
ARCHIVE = Path(os.environ['G2_BC1_ARCHIVE'])
condition = sys.argv[1]
DOWNSTREAM_ONLY = '--downstream-only' in sys.argv[2:]
OUT = EVIDENCE / condition
OUT.mkdir(parents=True, exist_ok=True)
FIXTURE = EVIDENCE / 'fixture'
FIXTURE.mkdir(exist_ok=True)
doc = {'condition': condition, 'payloads': {}, 'errors': {}, 'source_pins': {},
       'python': sys.version, 'packages': {name: version(name) for name in
        ('linkml', 'linkml-runtime', 'PyYAML', 'jsonschema', 'referencing')}}
if DOWNSTREAM_ONLY:
    doc = json.loads((OUT / 'capture.json').read_bytes())
    assert not doc['errors']

def pin(path):
    raw = path.read_bytes()
    doc['source_pins'][str(path)] = {'bytes': len(raw), 'sha256': sg.sha(raw)}
    return raw

def text(name):
    return pin(ARCHIVE / ('CHORUS_' + name)).decode()

def save(name, payload, **metadata):
    raw = sg.canonical(payload)
    path = OUT / (name.replace(':', '__') + '.json')
    path.write_bytes(raw)
    assert path.read_bytes() == raw and raw
    doc['payloads'][name] = {'path': str(path.relative_to(ROOT)), 'bytes': len(raw),
                             'sha256': sg.sha(raw), **metadata}
    print(name, len(raw), sg.sha(raw), flush=True)

def sink(row, raw):
    stage = row['stage']
    name = stage['phase']
    for key in ('worker_id', 'stage_id'):
        if key in stage:
            name += ':' + stage[key]
    if row['scenario'] != 'captured_record':
        name += ':' + row['scenario']
    save(name, json.loads(raw), stage=stage, scenario=row['scenario'],
         future_placeholders=row['future_placeholders'])

def main():
    # An observer records the exact production renderings already required by
    # registration sizing; it changes neither inputs, results nor acceptance.
    original_size = sizing.size_inputs
    def observed(*args, **kwargs):
        return original_size(*args, **kwargs, payload_sink=sink)
    files = builder.SizingRecord.in_directory(ARCHIVE, 'CHORUS', effective_receipt=True)
    for key in ('full', 'core', 'receipt', 'receipt_result'):
        pin(Path(getattr(files, key)))
    if DOWNSTREAM_ONLY:
        reg = json.loads((OUT / 'registration.json').read_bytes())
        sized = json.loads((OUT / 'sizing.json').read_bytes())
    else:
        with patch.object(sizing, 'size_inputs', observed):
            reg, outputs, sized = builder.prepare_registration('CHORUS',
                '2026-10-31_bc1-byte-proof', registration_path=FIXTURE / 'registration.json',
                partition='chorus', bounded_carry_version=1, bc1_fan_in=2,
                audit_limits={'aggregate_input_tokens': 4500000}, sizing_record=files)
    raw = sg.canonical(reg)
    # Keep the absolute registration path identical in both conditions.
    (FIXTURE / 'registration.json').write_bytes(raw)
    (OUT / 'registration.json').write_bytes(raw)
    (OUT / 'sizing.json').write_bytes(sg.canonical(sized))
    doc.update(registration_sha256=sg.sha(raw), audit_limits=reg['audit_limits'],
               calibration=sized['calibration'], sizing_totals=sized['own_plan_scenarios'])
    inputs = reg['inputs']
    spec = api.RunSpec(**reg['run'], bundle=Path(inputs['bundle']['path']),
        chunk_manifest=Path(inputs['chunk_manifest']['path']),
        manifest=Path(inputs['source_manifest']['path']),
        condition='generic_v10', render_version=25, shared_generation_version=1,
        shared_generation_registration=raw.decode(), bounded_carry_version=1,
        api_playbook_version=2, receipt_completion_version=2,
        receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
        profile=inputs['profile']['name'], profile_basis=inputs['profile']['basis'],
        run_date='2026-10-31', out_dir=FIXTURE / 'unused-output', provider=reg['runtime']['provider'])
    settings = api._model_settings(spec.condition)
    spec.bind_api_header_values(settings)
    captured = sg.assert_current(spec)
    for snapshot in (captured.full_schema, captured.core_schema):
        for _, path, raw in snapshot.sources:
            assert pin(path) == raw
    for name in ('shared_generation.py', 'schema_digest.py', 'bc1_context.py',
                 'bc1_runtime.py', 'bc1_registration.py', 'api_runner.py'):
        pin(ROOT / 'src/data_sheets_schema' / name)
    full, core = text('full.yaml'), text('core.yaml')
    catalog_text = context.schema_context(captured, full)
    (OUT / 'schema_context.json').write_bytes(sg.canonical(json.loads(catalog_text[len(context.SCHEMA_HEADER):])))
    outcome = json.loads(text('receipt_completion_result.json'))
    result_path = ARCHIVE / 'CHORUS_receipt_completion_result.json'
    outcome['journal'] = {'result': {'path': str(result_path), 'sha256': sg.sha(result_path.read_bytes())}}
    carries = {
        'full': {},
        'reconcile_full': {'Completed full record': full, 'Audit findings': text('audit.json')},
        'report': {'Audit findings': text('audit.json'), 'Original full record': full,
            'Original core record': core, 'Reconciled full record': text('reconcile_full.yaml'),
            'Completed core record': text('reconcile_core.yaml')},
    }
    # The historical audit is shared-v1, not an accepted BC1 output. Use the
    # existing D59 empty-future downstream scenario and explicitly label it.
    with ExitStack() as stack:
        stack.enter_context(patch.object(rc, 'recover', lambda *_: deepcopy(outcome)))
        stack.enter_context(patch.object(runtime, 'model_carry', lambda *_: ''))
        for phase, carry in carries.items():
            assert tuple(carry) == api.PHASE_NEEDS[phase]
            request = api.build_phase(spec, phase, carry=carry)
            cap = api.phase_max_tokens(spec, phase, 128000)
            save(phase, rc.request_payload(request, settings, {'max_output_tokens': cap}),
                 scenario='captured_record' if phase == 'full' else 'empty_future_bc1_audit_carry')
            if phase == 'full':
                receipt_inputs = json.loads(text('receipt_completion_inputs.json'))
                receipt_inputs['transcript'].update(system=request.system,
                    cached_blocks=deepcopy(request.cached_blocks), messages=deepcopy(request.messages))
                receipt_inputs['schema'] = rc.schema_capture(spec)
                receipt_inputs['registration'] = rc.registration_identity(spec)
                receipt_inputs['max_output_tokens'] = reg['receipt']['max_output_tokens']
                continuation, _ = rc.build_request(receipt_inputs)
                save(rc.PHASE, rc.request_payload(continuation, settings, reg['receipt']),
                     scenario='captured_assistant_response_rebuilt_current_initial_request')
    assert not spec.out_dir.exists()
    doc['unused_output_absent'] = True

try:
    assert resource_root()[0] == ROOT
    main()
except Exception as exc:
    import traceback
    doc['errors']['capture'] = traceback.format_exc()
    print(doc['errors']['capture'], flush=True)
finally:
    (OUT / 'capture.json').write_bytes(sg.canonical(doc))
if doc['errors']:
    raise SystemExit(1)
