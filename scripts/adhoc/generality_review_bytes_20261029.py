#!/usr/bin/env python3
# Purpose: exact offline G1 N5/N7 proof, extending claude's capture_request.py.
# Inputs: current checkout; argv[1] output JSON, argv[2] stable external fixture.
# Outputs: full/reconcile/report/typed omission payloads and identities, 2026-10-29.
import hashlib
import json
from pathlib import Path
import sys

from scripts import build_api_registrations as builder
from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import receipt_completion as rc, typed_audit_runtime as runtime

out, fixture = map(Path, sys.argv[1:])
fixture.mkdir(parents=True, exist_ok=True)
carry_dir = Path('data/ATTIC/d4d_concatenated_archived/claudecode_api_core/'
                 '2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate')
reg = builder.build_registration('CHORUS', '2026-10-29_g1-review-proof',
    registration_path=fixture / 'registration.json', partition='chorus', write_to_disk=False)
raw = sg.canonical(reg)
Path(reg['registration_path']).write_bytes(raw)
inputs = reg['inputs']
spec = api.RunSpec(**reg['run'], bundle=Path(inputs['bundle']['path']),
    chunk_manifest=Path(inputs['chunk_manifest']['path']), manifest=Path(inputs['source_manifest']['path']),
    condition='generic_v10', render_version=25, shared_generation_version=1,
    shared_generation_registration=raw.decode(), api_playbook_version=2,
    receipt_completion_version=2, receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
    profile=inputs['profile']['name'], profile_basis=inputs['profile']['basis'],
    run_date='2026-10-29', out_dir=fixture / 'unused-output', provider=reg['runtime']['provider'])
settings = api._model_settings(spec.condition)
spec.bind_api_header_values(settings)

def read(name):
    return (carry_dir / ('CHORUS_' + name)).read_text()

carries = {
    'full': {},
    'reconcile_full': {'Completed full record': read('full.yaml'), 'Audit findings': read('audit.json')},
    'report': {'Audit findings': read('audit.json'), 'Original full record': read('full.yaml'),
               'Original core record': read('core.yaml'), 'Reconciled full record': read('reconcile_full.yaml'),
               'Completed core record': read('reconcile_core.yaml')},
}
doc = {'registration': reg, 'payloads': {}}
for phase, carry in carries.items():
    request = api.build_phase(spec, phase, carry=carry)
    cap = api.phase_max_tokens(spec, phase, 128000)
    doc['payloads'][phase] = rc.request_payload(request, settings, {'max_output_tokens': cap})

# Exercise the exact pure constructors used by runtime, with the archived
# originals/effective receipt. No ledger, run directory or provider is written.
captured = sg.assert_current(spec)
originals = {'original_full': read('full.yaml').encode(), 'original_core': read('core.yaml').encode()}
result_raw = (carry_dir / 'CHORUS_receipt_completion_result.json').read_bytes()
outcome = json.loads(result_raw)
receipt_raw = outcome['receipt_yaml'].encode() if 'receipt_yaml' in outcome else (
    carry_dir.parent / 'CHORUS_coverage_receipt.yaml').read_bytes()
outcome['journal'] = {'result': {'path': str(carry_dir / 'CHORUS_receipt_completion_result.json'),
                                'sha256': hashlib.sha256(result_raw).hexdigest(), 'bytes': len(result_raw)}}
packet = runtime._prepare_packet_bytes(spec, captured, originals, receipt_raw)
_, payload, _ = runtime._build_request_bytes(spec, captured, packet,
    {'phase': runtime.OMISSION_PHASE}, {}, None, settings,
    generation='offline-byte-proof', receipt_carry=rc._audit_carry(outcome))
doc['payloads']['typed_audit_omission'] = payload
doc['packet_sha256'] = packet['sha256']
out.write_bytes(sg.canonical(doc))
assert out.stat().st_size and not spec.out_dir.exists()
for phase, payload in doc['payloads'].items():
    wire = sg.canonical(payload)
    print(phase, len(wire), sg.sha(wire), flush=True)
