"""Synthetic DATA ONLY for ordinary-Python native26 integration tests.

No native, auth, provider, stage, observer, or accounting process is executed.
Returned answers are mechanical declarations, not scientific support labels.
Call from the pinned repository root with the explicit registered interpreter.
The fresh root is consumed once; failed preparation is retained, never removed.
"""
from pathlib import Path
import hashlib
import json
import sys
import yaml


def _pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)
    return _pin(path, raw)


class _Answers:
    """Answer exact current outer requests; perform no file or runtime effects."""
    def __init__(self, selection, full_raw, quote):
        self.selection = selection
        self.full_raw = full_raw
        self.quote = quote

    def __call__(self, request_raw):
        from data_sheets_schema import native_shared_contract as c
        value = c.strict_json(request_raw, max_bytes=self.selection.bounds()['max_request_bytes'])
        c.exact(value, {'request_sha256', 'payload'}, 'fixture outer request')
        payload = value['payload']
        c.exact(payload, c.OUTER_REQUEST_KEYS, 'fixture outer payload')
        if value['request_sha256'] != c.sha(c.canonical(payload)):
            raise ValueError('fixture outer request hash differs')
        if payload['selection']['sha256'] != self.selection.registration.pin.sha256:
            raise ValueError('fixture request selected a different authority')
        if payload['owner_context']['original_full_yaml'].encode() != self.full_raw:
            raise ValueError('fixture request selected different full bytes')
        if payload['generation_context'] != self.selection.generation_context():
            raise ValueError('fixture request selected different generation context')
        return self.answer_inner(payload['cursor']['kind'], payload['inner_request'])

    def answer_inner(self, kind, inner):
        """Pure reply construction, separately usable by data conformance checks."""
        from data_sheets_schema import native_shared_contract as c
        if kind == 'receipt':
            return c.canonical({'rereceipt': [
                {'path': path, 'unsupported': True,
                 'reason': 'Synthetic receipt uncertainty; independent review required.'}
                for path in inner['requested_paths']]})
        if kind == 'worker':
            shared = json.loads(inner['payload']['shared_context'])
            stage = json.loads(inner['payload']['stage'])
            if shared['original_full'].encode() != self.full_raw:
                raise ValueError('fixture worker full differs')
            paths = stage['assignment']['paths']
            values = []
            for row in stage['inventory']['values']:
                if row['path'] not in paths:
                    continue
                values.append({'path': row['path'], 'claims': [{
                    'text': row['text'], 'verdict': 'supported', 'attributed_to': [],
                    'claim_status': 'fact', 'source_status': 'fact',
                    'evidence': [dict(self.quote)],
                    'reason': 'The fictional source explicitly declares this value and relationship; this is not scientific scoring.'}]})
            return c.canonical({'findings': [], 'summary': 'Synthetic declared review only.',
                'source_review': {'artifact': 'original_full', 'sha256': c.sha(self.full_raw), 'values': values}})
        if kind == 'omission':
            return c.canonical({'format': 'omission_inventory_v1',
                'request_sha256': inner['request_sha256'], 'chunks': [
                    {'chunk': row['chunk'], 'status': 'no_omission',
                     'reason': 'No additional synthetic candidate declared.', 'candidates': []}
                    for row in inner['payload']['chunks']]})
        if kind == 'integration':
            return c.canonical({'kind': 'audit_integration_v2',
                'proposal_index_sha256': inner['index']['sha256'],
                'retain_other_rows_from_index_sha256': inner['index']['sha256'],
                'row_replacements': [], 'finding_decisions': [], 'new_findings': [],
                'summary': 'Synthetic declared integration only.', 'omission_dispositions': []})
        raise ValueError('fixture has no answer for cursor kind ' + str(kind))


def build_native_fixture(root: Path, *, registered_python: str) -> dict:
    """Create S/R/instruction/C authority only; return untouched output seeds.

    Numbers are explicit synthetic test choices. The dummy executable is never
    invoked. Stage/output directories remain absent for the actual consumer.
    """
    from data_sheets_schema import api_runner as api
    from data_sheets_schema import native_shared_contract as c
    from data_sheets_schema import native_shared_selection as selected
    from data_sheets_schema import native_shared_controller as controller
    from data_sheets_schema import native_shared_receipts as nr
    from data_sheets_schema.chunking import manifest_from_bytes
    from data_sheets_schema.schema_snapshot import capture_schema
    from data_sheets_schema.native_execution_registration import ROUTE
    from data_sheets_schema.derive_core import derive_core
    from data_sheets_schema.d4d_pair_consistency import pair_schema_from_views
    from data_sheets_schema.schema_view import captured_view

    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    if str(Path(registered_python).resolve()) != str(Path(sys.executable).resolve()):
        raise ValueError('fixture interpreter must equal the explicitly registered helper interpreter')
    authority = root / 'authority'
    authority.mkdir()
    full = {
        'id': 'https://example.org/offline-neutral', 'name': 'offline-neutral',
        'title': 'Offline Neutral Dataset',
        'description': 'This fictional dataset supports offline software verification.',
        'version': '1.0', 'keywords': ['synthetic'],
        'creators': [{'name': 'Offline Author'}],
    }
    source_text = (
        'This source describes a fictional dataset used only for software tests.\n'
        'Dataset id: https://example.org/offline-neutral\n'
        'Dataset name: offline-neutral\n'
        'Dataset title: Offline Neutral Dataset\n'
        'Dataset description: This fictional dataset supports offline software verification.\n'
        'Dataset version: 1.0\n'
        'Dataset keyword: synthetic\n'
        'Offline Author is the creator of Offline Neutral Dataset.\n')
    bundle = ('FILE: neutral.txt\nPATH: neutral.txt\n' + source_text).encode()
    bundle_path = authority / 'bundle.txt'
    bundle_pin = _save(bundle_path, bundle)
    chunks = manifest_from_bytes(bundle, str(bundle_path))
    chunk_pin = _save(authority / 'chunks.json', c.canonical(chunks))
    relevant = [row for row in chunks['chunks'] if row.get('source') == 'neutral.txt']
    if len(relevant) != 1:
        raise ValueError('fixture expected one real neutral chunk')
    chunk_id = relevant[0]['id']
    receipt = {'bundle_md5': hashlib.md5(bundle).hexdigest(), 'chunks': [
        ({'id': row['id'], 'status': 'extracted',
          'extracted': [{'slot': 'name', 'snippet': 'Dataset name: offline-neutral'}]}
         if row['id'] == chunk_id else
         {'id': row['id'], 'status': 'nothing_relevant', 'reason': 'Synthetic delimiter only.'})
        for row in chunks['chunks']]}
    receipt_raw = yaml.safe_dump(receipt, sort_keys=False).encode()
    source_manifest = {'profile': 'neutral', 'projects': {'SYNTHETIC': {
        'bundle': str(bundle_path), 'sources': [{'id': 'neutral', 'source_type': 'documentation',
            'priority': 1, 'processed_file': 'neutral.txt'}]}},
        'naming': {'SYNTHETIC': {'canonical_label': 'Offline Neutral Dataset'}}}
    source_manifest_path = root / 'sources.yaml'
    source_pin = _save(source_manifest_path, yaml.safe_dump(source_manifest, sort_keys=False).encode())
    context = {'format': 'omission_context_v1', 'root_class': 'Dataset',
        'scopes': [{'owner': '', 'referent': 'Offline Neutral Dataset', 'release': '1.0',
                   'scope': 'Only the explicitly fictional supplied dataset.'}],
        'source_policy': {'priority': ['neutral.txt'], 'basis': 'Synthetic fixture declaration.'},
        'vocabulary': {}}
    context_pin = _save(authority / 'context.json', c.canonical(context))
    schemas = {}
    for kind, cls, path in [('full', 'Dataset', api.FULL_SCHEMA_PATH),
                            ('core', 'CoreDataset', api.CORE_SCHEMA_PATH)]:
        snapshot = capture_schema(Path(path).resolve(), strict=True)
        schemas[kind + '_schema'] = {'root': str(snapshot.sources[0][1]), 'root_class': cls,
            'sources': [{'name': str(name), **_pin(path, raw)} for name, path, raw in snapshot.sources]}
    synthetic = {'purpose': 'ordinary-Python software fixture; no scientific or execution acceptance',
        'coverage_floor': {'state': 'registered', 'numerator': 0, 'denominator': 1},
        'max_draft_checks': 3, 'runtime_limits': {'contextWindow': 900000, 'maxOutputTokens': 4000},
        'bounds': {**dict(c.BOUND_CEILINGS), 'max_paths_per_worker': 3, 'max_workers': 16}}
    receipt_policy = {'kind': c.KINDS['receipt_policy'], 'version': 1,
        'registration_id': 'synthetic-explicit-receipt-policy', 'condition': c.CONDITION,
        'runtime_policy_sha256': selected.RECEIPT_POLICY_SHA256,
        'receipt_instrument_version': 4, 'coverage_floor': synthetic['coverage_floor']}
    receipt_pin = _save(authority / 'receipt-policy.json', c.canonical(receipt_policy))
    assets = selected.capture_assets()
    axes = {key: value for key, value in selected.descriptor().items()
            if key not in {'typed_protocol', 'projection', 'receipt_policy', 'assets'}}
    document = {'kind': c.KINDS['selection'], 'version': 1,
        'registration_id': 'synthetic-native-neutral', 'registration_path': str(authority / 'selection.json'),
        'run': {'project': 'SYNTHETIC', 'arm': 'BASELINE (input documents only)',
                'method': 'claudecode_direct', 'label': 'offline-neutral'},
        'selection': {**axes, 'descriptor_sha256': selected.descriptor_capture().sha256,
            'assets': {item.pin.role[len('asset:'):]: _pin(item.pin.path, item.raw) for item in assets}},
        'inputs': {'project': 'SYNTHETIC', 'bundle': bundle_pin, 'chunk_manifest': chunk_pin,
            'context': context_pin, 'source_manifest': source_pin,
            'profile': {'name': 'neutral', 'basis': 'explicit caller', 'vocabulary': None}, **schemas},
        'receipt_policy': receipt_pin, 'bounds': synthetic['bounds'],
        'stage_root': str(root / 'fresh-attempt' / 'stages')}
    _save(Path(document['registration_path']), c.canonical(document))
    selection = selected.capture(document['registration_path'])
    dummy = root / 'declared-never-invoked'
    dummy_pin = _save(dummy, b'#!/bin/sh\nexit 99\n')
    dummy.chmod(0o700)
    runtime = {'route': ROUTE,
        'executable': {'path': str(dummy), 'sha256': dummy_pin['sha256'],
                       'version': 'synthetic-never-invoked', 'init_version': 'synthetic-never-invoked'},
        'model': 'synthetic-native-model', 'auxiliary_models': [], 'effort': 'high',
        'limits': synthetic['runtime_limits'], 'limits_basis': 'synthetic declared limits, not an observation',
        'provider': 'synthetic provider',
        'auth': {'loggedIn': True, 'authMethod': 'claude.ai', 'apiProvider': 'firstParty',
            'subscriptionType': 'synthetic-software-test', 'expected_api_key_source': 'none'},
        'environment': {'PATH': '/usr/bin:/bin', 'HOME': str(root),
            'CLAUDE_SECURESTORAGE_CONFIG_DIR': '', 'CLAUDE_CODE_DISABLE_1M_CONTEXT': '1'},
        'deadline_seconds': 120, 'budget_guard_usd': '1.0',
        'keep_awake': {'policy': 'not_applicable', 'host_platform': 'synthetic',
                       'basis': 'offline fixture, never invoked as native'}}
    runtime_path = authority / 'runtime.json'
    _save(runtime_path, c.canonical(runtime))
    spec = api.RunSpec(**document['run'], bundle=bundle_path, manifest=source_manifest_path,
        chunk_manifest=Path(chunk_pin['path']), condition=c.CONDITION, render_version=c.RENDERER,
        runtime=c.RUNTIME, profile='neutral', profile_basis='explicit caller',
        provider=runtime['provider'], reasoning_effort=runtime['effort'], prompt_text_env=True,
        run_date='2026-10-05', native_shared_generation_version=1,
        native_shared_generation_registration=c.canonical(document).decode())
    controller.bind_runtime(spec, runtime_path, synthetic['max_draft_checks'])
    instruction_path = authority / 'instruction.md'
    _save(instruction_path, spec.instruction.encode())
    composition = controller.compose(spec, runtime_path=runtime_path,
        instruction_path=instruction_path, max_draft_checks=synthetic['max_draft_checks'])
    composition_path = authority / 'composition.json'
    _save(composition_path, c.canonical(composition))
    full_raw = yaml.safe_dump(full, sort_keys=False, allow_unicode=True).encode()
    with captured_view(nr.schema_snapshot(selection, 'full')) as fv, \
            captured_view(nr.schema_snapshot(selection, 'core')) as cv:
        core = derive_core(full, pair_schema_from_views(fv, cv),
                           core_schema_identity=document['inputs']['core_schema']['root'])
    core_raw = yaml.safe_dump(core, sort_keys=False, allow_unicode=True).encode()
    response_for = _Answers(selection, full_raw,
        {'source': 'neutral.txt', 'chunk': chunk_id, 'quote': source_text.strip()})
    files = [_pin(path, path.read_bytes()) for path in sorted(root.rglob('*')) if path.is_file()]
    return {'spec': spec, 'selection': selection, 'runtime_path': runtime_path,
        'instruction_path': instruction_path, 'composition_path': composition_path,
        'full_raw': full_raw, 'core_raw': core_raw, 'receipt_raw': receipt_raw,
        'response_for': response_for, 'synthetic_parameters': synthetic,
        'fixture_files': files, 'source_text': source_text, 'chunk_id': chunk_id,
        'limitations': ['Data preparation only: no observed native permission, phase, runtime, accounting or completion.',
                       'Core bytes are pure derived seed data, not evidence of an observed helper.',
                       'Supported/unsupported replies are invented software declarations, not scientific labels.']}
