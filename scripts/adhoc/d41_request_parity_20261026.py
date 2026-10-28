#!/usr/bin/env python3
"""D41 offline wire parity, 2026-10-26; refs #5138, #5142.

Inputs: current package source with/without the D41 transport callback, real CHORUS inputs,
synthetic records/replies and a fresh scratch directory. Outputs: exact SDK
HTTP request bodies and a JSON parity report. MockTransport handles every
request; no provider, token-count endpoint, generation or scoring is used.
This checks request construction/transport, not complete run acceptance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
from importlib.metadata import version as package_version
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

PACKAGE = 'src/data_sheets_schema'
FULL = 'id: urn:d41:offline\nname: D41 offline parity fixture\n'
GENERATION = 'd41-offline-fixed-generation'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode()


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
    return pin(path)


def _offline():
    attempts = []
    def refuse(*args, **kwargs):
        attempts.append('socket connection attempted')
        raise AssertionError('D41 parity forbids network access')
    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse
    socket.create_connection = refuse
    return attempts


def _resource_authority(root, registration):
    """Pin the same current resources for both sides; no historical refs."""
    from data_sheets_schema import shared_generation as sg
    from data_sheets_schema.resources import resource_path
    paths = {resource_path(name).resolve() for name in sg.ASSET_HASHES}
    paths.add(root / 'scripts/build_api_registrations.py')

    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
                path = Path(value['path']).resolve()
                if sha(path.read_bytes()) != value['sha256']:
                    raise ValueError('common resource differs from captured pin: ' + str(path))
                paths.add(path)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(registration['inputs'])
    visit(registration['runtime']['config'])
    owned, external = {}, []
    for path in sorted(paths):
        selected = pin(path)
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            external.append(selected)
            continue
        owned[relative] = selected
    return {'same_tree_repo_resources': owned, 'external_dependency_pins': external,
            'scope': 'Both captures use identical current resource bytes and paired external dependencies.'}


def _module_authority(root, code_root, *, modules=None):
    """Refuse mixed package origins, including recalculated namespace paths."""
    selected = {}
    for name, module in list((sys.modules if modules is None else modules).items()):
        if name != 'data_sheets_schema' and not name.startswith('data_sheets_schema.'):
            continue
        expected = code_root / 'src' / Path(*name.split('.'))
        filename = getattr(module, '__file__', None)
        if filename is None:
            paths = getattr(module, '__path__', None)
            if paths is None or [Path(path).resolve() for path in paths] != [expected]:
                raise ValueError('foreign package namespace origin: ' + name)
            spec = getattr(module, '__spec__', None)
            locations = getattr(spec, 'submodule_search_locations', None)
            if locations is None or [Path(path).resolve() for path in locations] != [expected]:
                raise ValueError('foreign package namespace spec: ' + name)
            selected[name] = {'namespace_paths': [str(expected)]}
            continue
        path = Path(filename).resolve()
        if path not in (expected.with_suffix('.py'), expected / '__init__.py'):
            raise ValueError('foreign package module origin: ' + name + ': ' + str(path))
        entry = pin(path)
        selected[name] = entry
    if not selected:
        raise ValueError('no package modules available to attest')
    return selected


def _fixture(root, fixture, registration_snapshot):
    from data_sheets_schema import api_runner as api, shared_generation as sg
    from scripts.build_api_registrations import build_registration
    reg_path = fixture / 'registration.json'
    reg = build_registration('CHORUS', '2026-10-26_d41-offline-parity_rep1',
        registration_path=reg_path, registration_id='d41-offline-request-fixture',
        context_path=root / 'data/omission_contexts/chorus_omission_context.json',
        profile_name='bridge2ai', partition='chorus', write_to_disk=False)
    # A synthetic route declaration, never a registration for provider execution.
    reg['runtime']['provider'] = 'D41 offline MockTransport'
    reg['runtime']['base_url'] = 'https://offline.invalid'
    raw = sg.canonical(reg)
    save(registration_snapshot, raw)
    if reg_path.exists():
        if reg_path.read_bytes() != raw:
            raise ValueError('baseline/candidate fixture registration differs')
    else:
        save(reg_path, raw)
    spec = api.RunSpec(**reg['run'], bundle=Path(reg['inputs']['bundle']['path']),
        chunk_manifest=Path(reg['inputs']['chunk_manifest']['path']),
        manifest=Path(reg['inputs']['source_manifest']['path']),
        condition='generic_v10', render_version=25, shared_generation_version=1,
        shared_generation_registration=raw.decode(), api_playbook_version=2,
        receipt_completion_version=2, receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
        profile=reg['inputs']['profile']['name'], profile_basis=reg['inputs']['profile']['basis'],
        run_date='2026-10-26', out_dir=fixture / 'unused-output', provider=reg['runtime']['provider'])
    settings = api._model_settings(spec.condition)
    spec.bind_api_header_values(settings)
    return spec, reg, settings


def _requests(spec, reg, settings):
    """Use real builders with explicit synthetic capture inputs, no live state."""
    import yaml
    from data_sheets_schema import api_runner as api, shared_generation as sg
    from data_sheets_schema import receipt_completion as rc, typed_audit_runtime as runtime
    from data_sheets_schema import typed_audit as typed
    requests = {}
    carry = {'Completed full record': FULL, 'Completed core record': FULL,
        'Original full record': FULL, 'Original core record': FULL,
        'Reconciled full record': FULL, 'Audit findings': '{"findings": [], "summary": "Offline fixture"}'}
    for phase in ('full', 'reconcile_full', 'report'):
        req = api.build_phase(spec, phase, carry={name: carry[name] for name in api.PHASE_NEEDS[phase] if name in carry})
        requests[phase] = (req, api.phase_max_tokens(spec, phase, settings['max_tokens'], model=settings['name']))
    regate = copy.deepcopy(requests['report'][0])
    api._append_regate(regate, spec, '# Rejected synthetic report\nOffline parity only.\n',
        [{'kind': 'unsupported_claim', 'slot': 'name', 'record': 'full',
          'detail': 'Synthetic contradiction for exact regate construction.'}])
    requests['report_regate'] = (regate, requests['report'][1])
    capture = sg.assert_current(spec)
    inputs = reg['inputs']
    manifest = yaml.safe_load(capture.raw(inputs['chunk_manifest']['path']))
    receipt = {'bundle_md5': manifest['bundle_md5'], 'chunks': [
        {'id': row['id'], 'status': 'nothing_relevant', 'reason': 'Synthetic request parity only.'}
        for row in manifest['chunks']]}
    receipt_raw = yaml.safe_dump(receipt).encode()
    full_request = requests['full'][0]
    receipt_inputs = {'record': FULL, 'receipt': receipt_raw.decode(),
        'manifest': capture.raw(inputs['chunk_manifest']['path']).decode(),
        'bundle': capture.raw(inputs['bundle']['path']).decode(),
        'schema': rc.schema_capture(spec), 'policy': rc.policy_identity(version=2),
        'registration': reg['receipt'], 'max_output_tokens': reg['receipt']['max_output_tokens'],
        'transcript': {'system': full_request.system, 'cached_blocks': full_request.cached_blocks,
            'messages': full_request.messages, 'response': FULL + '\n' + api.RECEIPT_MARK + '\n' + receipt_raw.decode()}}
    receipt_request, _ = rc.build_request(receipt_inputs)
    requests[rc.PHASE] = (receipt_request, reg['receipt']['max_output_tokens'])
    packet = runtime._prepare_packet_bytes(spec, capture,
        {'original_full': FULL.encode(), 'original_core': FULL.encode()}, receipt_raw)
    workers, worker_checks = {}, {}
    inventory = {row['path']: row for row in packet['plan']['inventory']['values']}
    for worker in packet['plan']['workers']:
        inner = typed.worker_request(packet, worker['id'])
        values, findings = [], []
        for path in worker['paths']:
            row = inventory[path]
            if row['record_metadata_allowed']:
                values.append({'path': path, 'metadata_reason': 'Synthetic parity fixture metadata.'})
                continue
            # These invented record values are not facts about CHORUS. Mark
            # them for revision, with a finding on the actual fixture value.
            values.append({'path': path, 'claims': [{'text': row['text'],
                'verdict': 'revise', 'attributed_to': [], 'claim_status': 'fact',
                'source_status': 'unstated', 'evidence': [],
                'reason': 'Invented parity-fixture value; not established by the supplied sources.'}]})
            findings.append({'severity': 'low', 'record': 'full', 'slot': path.split('/')[1],
                'issue': 'Synthetic fixture value requires revision; no CHORUS factual claim is made.',
                'review_paths': [path], 'evidence': [{'artifact': 'original_full',
                    'path': path, 'op': 'contains', 'quote': row['text']}]})
        answer = {'findings': findings, 'summary': 'Offline wire parity only.', 'source_review': {
            'artifact': 'original_full', 'sha256': packet['plan']['original_full_sha256'],
            'values': values}}
        workers[worker['id']] = typed.capture_response(inner, canonical(answer))
        checked = typed.check_worker(packet, worker['id'], workers[worker['id']])
        if not checked['passed']:
            raise ValueError('invalid synthetic worker: ' + json.dumps(checked, sort_keys=True))
        worker_checks[worker['id']] = checked
    omission = canonical({'format': 'omission_inventory_v1',
        'request_sha256': packet['omission_request']['request_sha256'],
        'chunks': [{'chunk': row['chunk'], 'status': 'no_omission', 'reason': 'Synthetic parity only.', 'candidates': []}
                   for row in packet['omission_request']['payload']['chunks']]})
    for stage in runtime.roster(packet):
        req, payload, _ = runtime._build_request_bytes(spec, capture, packet, stage,
            workers=workers, omission=omission, settings=settings,
            generation=GENERATION, receipt_carry=rc.AUDIT_HEADER + 'Synthetic parity fixture; no accepted completion claimed.')
        key = stage['phase'] + (':' + stage['worker_id'] if 'worker_id' in stage else '')
        requests[key] = (req, payload['max_tokens'])
    return requests, worker_checks


def _transport(api, req, settings, cap, *, guarded, deny=False):
    """Capture actual SDK serialization, not a reconstructed dictionary."""
    import anthropic
    import httpx
    bodies, callback_calls = [], []
    def before_attempt():
        callback_calls.append('checked')
        if deny:
            raise RuntimeError('offline latch refusal before dispatch')
    def respond(request):
        if request.url.path != '/v1/messages':
            raise AssertionError('unexpected mock endpoint')
        bodies.append(request.content)
        events = [
            {'type': 'message_start', 'message': {'id': 'offline', 'type': 'message', 'role': 'assistant',
             'model': settings['name'], 'content': [], 'stop_reason': None, 'stop_sequence': None,
             'usage': {'input_tokens': 1, 'output_tokens': 0}}},
            {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}},
            {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'offline'}},
            {'type': 'content_block_stop', 'index': 0},
            {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None},
             'usage': {'output_tokens': 1}}, {'type': 'message_stop'}]
        text = ''.join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events)
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, text=text)
    with anthropic.Anthropic(api_key='offline-fixture', base_url='https://offline.invalid', max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        extra = {'before_attempt': before_attempt} if guarded else {}
        try:
            result = api._call_with_retry(client, model=settings['name'], max_tokens=cap,
                temperature=settings['temperature'], thinking=settings.get('thinking'), effort=settings.get('effort'),
                system=req.system, messages=req.messages, transport_attempts=1, **extra)
        except RuntimeError as exc:
            if not (deny and str(exc) == 'offline latch refusal before dispatch'):
                raise
        else:
            if deny or result.stop_reason != 'end_turn':
                raise AssertionError('unexpected mock transport result')
    if callback_calls != (['checked'] if guarded else []):
        raise AssertionError('internal callback count differs')
    if len(bodies) != (0 if deny else 1):
        raise AssertionError('unexpected number of dispatched request bodies')
    return bodies, callback_calls


def capture(root, code_root, fixture, output, mode):
    root, code_root = root.resolve(), code_root.resolve()
    os.chdir(root)
    sys.path[:0] = [str(code_root / 'src'), str(root)]
    attempts = _offline()
    for key in ('D4D_PROFILE', 'D4D_RECEIPT_FULL_MAX_TOKENS'):
        os.environ.pop(key, None)
    # The namespace package otherwise recalculates its search path when the
    # registration builder adds its own current checkout to sys.path. Fix the
    # selected package root BEFORE importing any of its submodules.
    import data_sheets_schema
    package_path = [str(code_root / PACKAGE)]
    data_sheets_schema.__path__ = package_path
    data_sheets_schema.__spec__.submodule_search_locations = package_path
    from data_sheets_schema import api_runner as api, shared_generation as sg, resources
    if Path(api.__file__).resolve() != code_root / PACKAGE / 'api_runner.py':
        raise ValueError('wrong API implementation imported')
    if resources.resource_root()[0].resolve() != root:
        raise ValueError('wrong common resource root')
    if 'before_attempt' not in inspect.signature(api._call_with_retry).parameters:
        raise ValueError('candidate lacks the per-attempt latch callback')
    # The only counterfactual is omission of the guard callback at the physical
    # transport boundary. Builders, descriptors, resources and SDK stay identical.
    guarded = mode == 'candidate'
    spec, reg, settings = _fixture(root, fixture, output / 'registration.json')
    origins_after_fixture = _module_authority(root, code_root)
    common_resources = _resource_authority(root, reg)
    requests, worker_checks = _requests(spec, reg, settings)
    origins_after_requests = _module_authority(root, code_root)
    rows = {}
    for phase, (req, cap) in requests.items():
        bodies, calls = _transport(api, req, settings, cap, guarded=guarded)
        rows[phase] = {'body': save(output / (phase.replace(':', '-') + '.http.json'), bodies[0]),
            'callback_count': len(calls), 'max_tokens': cap}
    if guarded:
        req, cap = requests['full']
        _transport(api, req, settings, cap, guarded=True, deny=True)
    if attempts:
        raise AssertionError('a network connection was attempted')
    origins_after_transport = _module_authority(root, code_root)
    result = {'mode': mode, 'api_module': pin(api.__file__), 'registration': pin(fixture / 'registration.json'),
        'selection': sg.descriptor(), 'rows': rows, 'network_attempts': attempts,
        'callback_refusal_prevented_dispatch': guarded,
        'builder': pin(root / 'scripts/build_api_registrations.py'),
        'input_pins': reg['inputs'], 'runtime': reg['runtime'],
        'fixture_selection': {'profile': 'bridge2ai', 'basis': 'stated by the caller',
            'scope': 'Identical explicit fixture input; automatic checkout-dependent profile-basis formatting is outside this comparison.'},
        'common_resources': common_resources,
        'worker_fixture_checks': worker_checks,
        'package_origins': {'after_fixture': origins_after_fixture,
            'after_requests': origins_after_requests, 'after_transport': origins_after_transport},
        'environment': {'python': sys.version, 'executable': sys.executable,
            'packages': {name: package_version(name) for name in ('anthropic', 'httpx')}}}
    save(output / 'capture.json', canonical(result))
    return result


def compare(root, workdir):
    root, workdir = root.resolve(), workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=False)
    baseline = {'scope': PACKAGE, 'counterfactual': 'same tree, before_attempt callback omitted'}
    fixture = workdir / 'common-fixture'
    fixture.mkdir()
    helper_before = pin(__file__)
    production_before = {str(p.relative_to(root)): pin(p) for p in (root / PACKAGE).rglob('*.py')}
    captures = {}
    for mode in ('baseline', 'candidate'):
        code_root = root
        out = workdir / mode
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
               'PYTHONPATH': str(code_root / 'src') + os.pathsep + str(root)}
        command = [sys.executable, str(Path(__file__).resolve()), '--capture', mode, '--root', str(root),
                   '--code-root', str(code_root), '--fixture', str(fixture), '--out', str(out)]
        completed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=300)
        save(workdir / (mode + '.log'), (completed.stdout + completed.stderr).encode())
        if completed.returncode:
            raise RuntimeError(f'{mode} capture failed; see {workdir / (mode + ".log")}')
        captures[mode] = json.loads((out / 'capture.json').read_bytes())
    left, right = captures['baseline'], captures['candidate']
    if (left['registration'] != right['registration'] or left['selection'] != right['selection']
            or left['environment'] != right['environment']
            or left['common_resources'] != right['common_resources']):
        raise AssertionError('v1 authority differs; request identities must not be normalized')
    if left['rows'].keys() != right['rows'].keys():
        raise AssertionError('request roster differs')
    if left['package_origins'] != right['package_origins']:
        raise AssertionError('package source changed between captures')
    rows = {}
    for phase in left['rows']:
        if (left['rows'][phase]['callback_count'], right['rows'][phase]['callback_count']) != (0, 1):
            raise AssertionError('guard counterfactual did not change callback execution')
        before, after = left['rows'][phase]['body'], right['rows'][phase]['body']
        if Path(before['path']).read_bytes() != Path(after['path']).read_bytes():
            raise AssertionError(f'exact SDK HTTP bytes differ: {phase}')
        rows[phase] = {'identical': True, 'bytes': before['bytes'], 'sha256': before['sha256'],
                       'baseline': before, 'candidate': after}
    if helper_before != pin(__file__) or production_before != {str(p.relative_to(root)): pin(p) for p in (root / PACKAGE).rglob('*.py')}:
        raise RuntimeError('source changed during request comparison')
    result = {'format': 'd41_chorus_request_parity_v1', 'passed': True, 'baseline': baseline,
        'helper': helper_before, 'production_sources': production_before, 'rows': rows,
        'environment': right['environment'],
        'common_resources': right['common_resources'],
        'fixture_selection': right['fixture_selection'],
        'excluded_request_branches': ['full readdress and receipt after readdress', 'schema repair'],
        'captures': {mode: pin(workdir / mode / 'capture.json') for mode in captures},
        'scope': 'Exact generic_v10/shared-v1 CHORUS request construction with explicitly selected bridge2ai profile and real SDK serialization; synthetic records/replies, no run admission or acceptance claim.',
        'shared_v2': 'Controller code identity and registration SHA must change; no normalization or shared-v2 byte-parity claim. Journal is included in ROUTING_CODE since db88ca68c.'}
    save(workdir / 'summary.json', json.dumps(result, indent=2, sort_keys=True).encode() + b'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--workdir', type=Path)
    parser.add_argument('--capture', choices=('baseline', 'candidate'))
    parser.add_argument('--code-root', type=Path)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.capture:
        capture(args.root, args.code_root, args.fixture, args.out, args.capture)
    else:
        result = compare(args.root, args.workdir)
        print(json.dumps({'passed': result['passed'], 'requests': len(result['rows']), 'summary': str(args.workdir / 'summary.json')}))


if __name__ == '__main__':
    main()
