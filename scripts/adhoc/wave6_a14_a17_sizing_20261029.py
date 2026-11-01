"""PR #5162 x #5211, F1, 2026-10-29: measure sizing against current runtime wires.

Inputs: retained CHORUS sizing fixture, current resources, external scratch dir.
Outputs: compact JSON measurements, optionally paired with a before-fix JSON.
All stage requests use the production formatter and synthetic structural replies;
no provider, accounting, generation execution, or scientific judgment is involved.
"""
from copy import deepcopy
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_api_registrations as builder
from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import receipt_completion as rc, typed_audit as typed
from data_sheets_schema import typed_audit_runtime as runtime
from data_sheets_schema import audit_omissions as omissions


def normalized(value):
    """Only fixed-width digests differ in the retained sizing stand-ins."""
    return re.sub(rb'[0-9a-f]{64}', b'0' * 64, sg.canonical(value))


def integration_base(inner):
    """Remove exactly the response-dependent fields that sizing budgets separately."""
    base = deepcopy(inner)
    base['omission_check'] = {}
    payload = base['integration_request']['payload']
    payload['workers'] = {key: '' for key in payload['workers']}
    payload['omission_response'] = ''
    payload['omission_check'] = {}
    for index in (base['index'], payload['proposal_index']):
        index['findings'] = []
        for worker in index['workers']:
            worker['bytes'] = 0
    return base


def synthetic_workers(packet):
    """Explicit revise declarations exercise the real structural index builder."""
    inventory = {row['path']: row for row in packet['plan']['inventory']['values']}
    workers = {}
    for worker in packet['plan']['workers']:
        values, findings = [], []
        for path in worker['paths']:
            row = inventory[path]
            if row['record_metadata_allowed']:
                values.append({'path': path, 'metadata_reason': 'Synthetic byte-parity fixture.'})
                continue
            values.append({'path': path, 'claims': [{'text': row['text'], 'verdict': 'revise',
                'attributed_to': [], 'claim_status': 'fact', 'source_status': 'unstated',
                'evidence': [], 'reason': 'Synthetic byte-parity declaration; no scientific support assessed.'}]})
            findings.append({'severity': 'low', 'record': 'full', 'slot': path.split('/')[1],
                'issue': 'Synthetic byte-parity revision only.', 'review_paths': [path],
                'evidence': [{'artifact': 'original_full', 'path': path, 'op': 'contains', 'quote': row['text']}]})
        response = sg.canonical({'findings': findings, 'summary': 'Offline byte parity only.',
            'source_review': {'artifact': 'original_full', 'sha256': packet['plan']['original_full_sha256'],
                              'values': values}})
        workers[worker['id']] = typed.capture_response(typed.worker_request(packet, worker['id']), response)
    return workers


def measure(fixture):
    fixture = Path(fixture).resolve()
    fixture.mkdir(parents=True, exist_ok=True)
    record_dir = ROOT / 'tests/fixtures/audit_batches/chorus_v10_2026-10-22a'
    raw = {key: (record_dir / f'CHORUS_{name}.yaml').read_bytes()
           for key, name in (('full', 'full'), ('core', 'core'), ('receipt', 'coverage_receipt'))}
    reg = builder.build_registration('CHORUS', '2026-10-29_wave6-sizing_rep1',
        registration_path=fixture / 'registration.json', registration_id='wave6-sizing-parity',
        context_path=ROOT / 'data/omission_contexts/chorus_omission_context.json',
        profile_name='bridge2ai', partition='chorus', write_to_disk=False)
    reg['runtime'].update(provider='Offline sizing parity fixture', base_url='https://offline.invalid')
    registration = sg.canonical(reg)
    Path(reg['registration_path']).write_bytes(registration)
    inputs = reg['inputs']
    spec = api.RunSpec(**reg['run'], bundle=Path(inputs['bundle']['path']),
        chunk_manifest=Path(inputs['chunk_manifest']['path']), manifest=Path(inputs['source_manifest']['path']),
        condition='generic_v10', render_version=25, shared_generation_version=1,
        shared_generation_registration=registration.decode(), api_playbook_version=2,
        receipt_completion_version=2, receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
        profile=inputs['profile']['name'], profile_basis=inputs['profile']['basis'],
        run_date='2026-10-29', out_dir=fixture / 'unused-output', provider=reg['runtime']['provider'])
    settings = api._model_settings(spec.condition)
    spec.bind_api_header_values(settings)
    captured = sg.assert_current(spec)
    context = captured.raw(inputs['context']['path'])
    packet = runtime._prepare_packet_bytes(spec, captured,
        {'original_full': raw['full'], 'original_core': raw['core']}, raw['receipt'])
    rendered = builder.render_typed_audit_inputs('CHORUS', reg['audit_limits'], reg,
        record=raw['full'], core=raw['core'], receipt=raw['receipt'], context=context,
        schema_snapshot=captured.full_schema)
    workers = synthetic_workers(packet)
    omission_request = typed.omission_wire_request(packet)
    omission = sg.canonical({'format': 'omission_inventory_v1',
        'request_sha256': omission_request['request_sha256'],
        'chunks': [{'chunk': row['chunk'], 'status': 'no_omission',
                    'reason': 'Synthetic byte parity only.', 'candidates': []}
                   for row in omission_request['payload']['chunks']]})
    carry = rc.AUDIT_HEADER + 'Offline sizing parity; no accepted completion claimed.'
    schema_bytes = len(sg._schema_context(captured, raw['full'].decode()).encode())
    sized_workers = {row['payload']['worker_id']: row for row in rendered['requests']['workers']}
    largest_inner = max(len(sg.canonical(row)) for row in sized_workers.values())
    # The legacy instrument returns a maximum, with common outer text and
    # fixed-width worker IDs. Recover each individual call without padding it.
    assert len({len(key) for key in sized_workers}) == 1
    rows = []
    for stage in runtime.roster(packet):
        req, payload, _ = runtime._build_request_bytes(spec, captured, packet, stage,
            workers, omission, settings, generation='0' * 32, receipt_carry=carry)
        parts = [part['text'] for message in payload['messages'] for part in message['content']
                 if part.get('type') == 'text']
        wire_inner = json.loads(next(text for text in parts
            if text.startswith('# Exact typed stage request\n\n')).split('\n\n', 1)[1])
        wire_bytes = len(req.system.encode()) + sum(len(text.encode()) for text in parts)
        schema_allowance = schema_bytes - len(next(text for text in parts
            if text.startswith(sg.SCHEMA_CONTEXT_HEADER)).encode())
        carry_allowance = rendered['carry_allowance_bytes'] - len(carry.encode())
        response_bytes = 0
        if stage['phase'] == runtime.WORKER_PHASE:
            mine = sized_workers[stage['worker_id']]
            size = rendered['worker_bytes'] - largest_inner + len(sg.canonical(mine))
            inner_matches = normalized(mine) == normalized(wire_inner)
        elif stage['phase'] == runtime.OMISSION_PHASE:
            size = rendered['omission_bytes']
            inner_matches = rendered['requests']['omission'] == wire_inner
        else:
            base = integration_base(wire_inner)
            size = rendered['integration_base_bytes']
            response_bytes = len(sg.canonical(wire_inner)) - len(sg.canonical(base))
            inner_matches = normalized(base) == normalized(rendered['requests']['integration'])
        expected = wire_bytes + carry_allowance + schema_allowance - response_bytes
        rows.append({'stage': stage, 'sized_text_bytes': size, 'current_wire_text_bytes': wire_bytes,
            'expected_sized_text_bytes': expected, 'carry_allowance_bytes': carry_allowance,
            'schema_allowance_bytes': schema_allowance, 'response_bytes': response_bytes,
            'inner_matches': inner_matches, 'parity': size == expected and inner_matches,
            'canonical_payload_bytes': len(sg.canonical(payload)),
            'canonical_payload_sha256': sg.sha(sg.canonical(payload))})
    omission_row = next(row for row in rows if row['stage']['phase'] == runtime.OMISSION_PHASE)
    return {'format': 'wave6_a14_a17_sizing_parity_v1', 'python': sys.version,
        'registration_sha256': sg.sha(registration), 'packet_sha256': packet['sha256'],
        'inputs_sha256': {**{key: sg.sha(value) for key, value in raw.items()},
            'context': sg.sha(context), 'bundle': inputs['bundle']['sha256'],
            'manifest': inputs['chunk_manifest']['sha256'], 'schema': sg.sha(sg.canonical(inputs['full_schema']))},
        'source_sha256': {str(Path(module.__file__).relative_to(ROOT)):
            hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for module in (builder, runtime, typed, omissions, sg)},
        'plan_workers': len(packet['plan']['workers']), 'rows': rows, 'passed': all(row['parity'] for row in rows),
        'omission_sized_text_bytes': omission_row['sized_text_bytes'],
        'omission_current_wire_text_bytes': omission_row['current_wire_text_bytes'],
        'omission_wire_inner_bytes': len(sg.canonical(omission_request)),
        'omission_sizing_inner_bytes': len(sg.canonical(rendered['requests']['omission'])),
        'omission_wire_schema_bytes': len(sg.canonical(omission_request['payload']['schema'])),
        'scope': 'Text-byte sizing, with explicit carry/schema allowances and response contribution; '
                 'canonical payload sizes are also recorded, not equated with text-byte estimates.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--before', type=Path)
    args = parser.parse_args()
    result = measure(args.fixture_dir)
    if args.before:
        before = json.loads(args.before.read_bytes())
        assert before['inputs_sha256'] == result['inputs_sha256']
        assert before['registration_sha256'] == result['registration_sha256']
        assert [row['canonical_payload_sha256'] for row in before['rows']] == [
            row['canonical_payload_sha256'] for row in result['rows']]
        assert not before['passed'] and result['passed']
        delta = result['omission_sized_text_bytes'] - before['omission_sized_text_bytes']
        result = {'before': before, 'after': result, 'actual_payloads_unchanged': True,
            'omission_sizing_delta_bytes': delta, 'd62_bytes_per_token': 2.48,
            'd62_delta_tokens': delta / 2.48,
            'd62_ceil_delta_tokens': math.ceil(result['omission_sized_text_bytes'] / 2.48)
                - math.ceil(before['omission_sized_text_bytes'] / 2.48)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('before', 'after', 'rows')}, indent=2))


if __name__ == '__main__':
    main()
