"""Explicit native26 rendering; no API configuration or model discovery."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shlex

from . import native_shared_contract as c
from . import native_shared_selection as selection

METADATA_KEYS = frozenset({
    'native_shared_generation_version', 'native_shared_generation_descriptor',
    'native_shared_generation_registration', 'native_shared_generation_context',
    'native_shared_receipt_policy', 'native_shared_runtime_declaration',
    'native_shared_max_draft_checks'})


def validate_spec(spec):
    version = getattr(spec, 'native_shared_generation_version', 0)
    registration = getattr(spec, 'native_shared_generation_registration', None)
    if type(version) is not int or version not in (0, 1):
        raise ValueError('native_shared_generation_version must be integer 0 or 1')
    if not version:
        if registration is not None or spec.render_version == 26:
            raise ValueError('native renderer26 requires explicit native shared selection')
        return None
    if (spec.condition != c.CONDITION or type(spec.render_version) is not int
            or spec.render_version != c.RENDERER or spec.runtime != c.RUNTIME
            or spec.method != 'claudecode_direct' or spec.out_dir is not None
            or spec.prompt_text_env is not True):
        raise ValueError('native shared selection requires generic_v10/direct26 and recorded prompt environment')
    for key in ('native_source_attribution_version', 'shared_generation_version',
                'api_playbook_version', 'receipt_completion_version', 'removal_repair_version'):
        if type(getattr(spec, key)) is not int or getattr(spec, key) != 0:
            raise ValueError('native shared selection cannot mix old/API axes')
    if (spec.native_source_attribution_max_checks is not None
            or spec.receipt_completion_registration is not None
            or spec.shared_generation_registration is not None):
        raise ValueError('native shared selection cannot reuse old/API registrations')
    for key in ('provider', 'reasoning_effort', 'profile', 'profile_basis'):
        value = getattr(spec, key)
        if type(value) is not str or not value.strip() or any(x in value for x in ('\n', '\r', '\x00')):
            raise ValueError('native shared selection requires explicit ' + key)
    if spec.chunk_manifest is None or (not spec._replay_only and not isinstance(spec.manifest, (str, Path))):
        raise ValueError('native shared selection requires explicit source and chunk manifests')
    if type(registration) is not str:
        raise ValueError('native shared selection requires captured registration JSON')
    doc = c.parse_selection(registration.encode('utf-8'))
    if doc['run'] != {key: getattr(spec, key) for key in ('project', 'arm', 'method', 'label')}:
        raise ValueError('native shared registration belongs to another run')
    return doc


def bind_selection(spec):
    doc = validate_spec(spec)
    if doc is None or spec._replay_only:
        return
    cap = selection.capture(doc['registration_path'])
    if cap.registration.raw != spec.native_shared_generation_registration.encode('utf-8'):
        raise ValueError('native selection differs from the actual supplied file')
    _same_spec_inputs(spec, doc)
    spec._native_shared_generation_capture = cap


def _same_spec_inputs(spec, doc):
    for field, key in (('bundle', 'bundle'), ('chunk_manifest', 'chunk_manifest'), ('manifest', 'source_manifest')):
        actual = getattr(spec, field)
        declared = doc['inputs'][key]
        if actual is None or declared is None:
            raise ValueError('native render input differs from selected ' + key)
        path = (c.canonical_path(str(actual), 'recorded native ' + key) if spec._replay_only
                else str(Path(actual).absolute()))
        if path != declared['path']:
            raise ValueError('native render input differs from selected ' + key)
    if not spec.manifest_used:
        raise ValueError('native render cannot declare its source manifest unused')
    profile = doc['inputs']['profile']
    if (spec.profile, spec.profile_basis) != (profile['name'], profile['basis']):
        raise ValueError('native render profile differs from selected profile')


def _raw_identity(artifact):
    return {'path': artifact.pin.path, 'sha256': artifact.pin.sha256,
            'raw_json': artifact.raw.decode('utf-8')}


def _read_identity(value, label):
    c.exact(value, {'path', 'sha256', 'raw_json'}, label)
    if type(value['raw_json']) is not str:
        raise ValueError(label + ' requires exact captured JSON text')
    raw = value['raw_json'].encode('utf-8')
    if not raw or len(raw) > c.HARD_LIMITS['input_bytes'] or c.sha(raw) != value['sha256']:
        raise ValueError(label + ' raw identity differs')
    return c.CapturedArtifact(c.ArtifactPin(label, value['path'], len(raw), value['sha256']), raw)


def _runtime(raw, provider, effort):
    from .native_execution_registration import RUNTIME_KEYS, ROUTE
    value = c.strict_json(raw, 'sole runtime declaration', c.HARD_LIMITS['input_bytes'])
    c.exact(value, RUNTIME_KEYS, 'sole runtime declaration')
    if value['route'] != ROUTE:
        raise ValueError('native renderer requires the selected direct runtime route')
    model = value.get('model')
    if type(model) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:+/@\[\]-]{0,255}', model):
        raise ValueError('native rendering requires an explicit literal runtime model')
    if value.get('provider') != provider or value.get('effort') != effort:
        raise ValueError('rendered provider or effort differs from the sole runtime declaration')
    limits = c.exact(value.get('limits'), {'contextWindow', 'maxOutputTokens'}, 'runtime limits')
    for key, item in limits.items():
        c.positive_int(item, key)
    if limits['maxOutputTokens'] > limits['contextWindow']:
        raise ValueError('runtime output ceiling exceeds the context declaration')
    return value


def _context(doc, recorded):
    c.exact(recorded, {'context', 'profile', 'source_manifest', 'scope'}, 'native generation context')
    c.exact(recorded['context'], {'identity', 'raw_json'}, 'native context capture')
    raw = recorded['context']['raw_json']
    expected = doc['inputs']['context']
    if (type(raw) is not str or recorded['context']['identity'] != expected
            or len(raw.encode('utf-8')) != expected['bytes'] or c.sha(raw.encode('utf-8')) != expected['sha256']):
        raise ValueError('recorded native generation context differs from S')
    c.strict_json(raw.encode('utf-8'), 'generation context', doc['bounds']['max_input_bytes'])
    profile = dict(doc['inputs']['profile'])
    if profile['vocabulary'] is not None:
        actual = recorded['profile'].get('vocabulary') if type(recorded['profile']) is dict else None
        c.exact(actual, {'identity', 'raw_text'}, 'native vocabulary capture')
        text, pin = actual['raw_text'], profile['vocabulary']
        if (type(text) is not str or actual['identity'] != pin
                or len(text.encode('utf-8')) != pin['bytes'] or c.sha(text.encode('utf-8')) != pin['sha256']):
            raise ValueError('recorded native vocabulary differs from S')
        profile['vocabulary'] = actual
    expected_context = {'context': {'identity': expected, 'raw_json': raw},
                        'profile': profile, 'source_manifest': doc['inputs']['source_manifest'],
                        'scope': 'Caller-declared generation scope, source policy and vocabulary; '
                                 'not a scientific applicability or support verdict.'}
    if recorded != expected_context:
        raise ValueError('recorded native generation context has substituted authority')


def validate_metadata(recorded):
    keys = {k for k in recorded if k.startswith('native_shared_')}
    if keys != METADATA_KEYS or type(recorded['native_shared_generation_version']) is not int or recorded['native_shared_generation_version'] != 1:
        raise ValueError('native recorded metadata requires its complete exact selected fields')
    descriptor = recorded['native_shared_generation_descriptor']
    if c.canonical(descriptor) != selection.descriptor_capture().raw:
        raise ValueError('native recorded descriptor differs from selected software')
    identity = c.exact(recorded['native_shared_generation_registration'], {'sha256', 'raw_json'}, 'native registration capture')
    if type(identity['raw_json']) is not str:
        raise ValueError('native registration requires captured JSON text')
    raw = identity['raw_json'].encode('utf-8')
    if c.sha(raw) != identity['sha256']:
        raise ValueError('native registration hash differs from its captured bytes')
    doc = c.parse_selection(raw)
    if doc['selection']['descriptor_sha256'] != selection.descriptor_capture().sha256:
        raise ValueError('S descriptor differs from the native render descriptor')
    if {name: pin['sha256'] for name, pin in doc['selection']['assets'].items()} != dict(selection.ASSET_HASHES):
        raise ValueError('native recorded asset closure differs from selected software')
    _context(doc, recorded['native_shared_generation_context'])
    receipt = _read_identity(recorded['native_shared_receipt_policy'], 'receipt_policy')
    if {key: getattr(receipt.pin, key) for key in ('path', 'bytes', 'sha256')} != doc['receipt_policy']:
        raise ValueError('native receipt policy differs from its S pin')
    c.parse_receipt_policy(receipt.raw, selection.RECEIPT_POLICY_SHA256)
    runtime = _read_identity(recorded['native_shared_runtime_declaration'], 'runtime_declaration')
    _runtime(runtime.raw, recorded.get('provider'), recorded.get('reasoning_effort'))
    c.positive_int(recorded['native_shared_max_draft_checks'], 'native draft-check allowance')
    return doc


def metadata(spec):
    validate_spec(spec)
    saved = getattr(spec, '_native_shared_generation_metadata', None)
    if spec._replay_only:
        if type(saved) is not bytes:
            raise ValueError('native replay requires recorded immutable metadata')
        result = c.strict_json(saved, 'native recorded metadata', c.HARD_LIMITS['request_bytes'])
    else:
        cap = spec._native_shared_generation_capture
        if type(cap) is not c.NativeSelectionCapture:
            raise ValueError('native renderer requires its current captured selection')
        runtime = spec._native_shared_runtime_capture
        if type(runtime) is not c.CapturedArtifact:
            raise ValueError('native renderer requires the sole captured runtime declaration before composition')
        result = {'native_shared_generation_version': 1,
            'native_shared_generation_descriptor': selection.descriptor(),
            'native_shared_generation_registration': {
                'sha256': cap.registration.pin.sha256, 'raw_json': cap.registration.raw.decode('utf-8')},
            'native_shared_generation_context': cap.generation_context(),
            'native_shared_receipt_policy': _raw_identity(cap.receipt_policy),
            'native_shared_runtime_declaration': _raw_identity(runtime),
            'native_shared_max_draft_checks': spec._native_shared_max_draft_checks}
    validate_metadata({**result, 'provider': spec.provider, 'reasoning_effort': spec.reasoning_effort})
    return result


def restore(spec, recorded):
    doc = validate_metadata(recorded)
    _same_spec_inputs(spec, doc)
    spec._native_shared_generation_metadata = c.canonical({k: recorded[k] for k in METADATA_KEYS})
    spec._native_shared_runtime_capture = _read_identity(recorded['native_shared_runtime_declaration'], 'runtime_declaration')
    spec._native_shared_max_draft_checks = recorded['native_shared_max_draft_checks']


def commands(spec):
    """Exact helper spellings shared by rendering and the native controller."""
    doc = validate_spec(spec)
    paths, toolchain = spec._agentic_artifact_paths, spec._agentic_toolchain
    if type(paths) is not dict or type(toolchain) is not dict:
        raise ValueError('native commands require recorded artifact paths and toolchain')
    py = toolchain['python']
    c.canonical_path(py, 'registered Python')
    roles = {r.role: r.path for r in c.role_paths(doc['registration_path'], doc['stage_root'])}
    full_schema, core_schema = (doc['inputs'][k]['root'] for k in ('full_schema', 'core_schema'))
    pair_schemas = ('--full-schema', full_schema, '--core-schema', core_schema)
    cli = (py, '-m', 'data_sheets_schema.cli')
    source = ('--source-manifest', str(spec.manifest), '--project', spec.project)
    evidence = (py, '-m', 'data_sheets_schema.evidence_assertions', '--audit', roles['audit'],
        '--bundle', str(spec.bundle), '--manifest', str(spec.chunk_manifest),
        '--original-full', roles['phase1_full'], '--original-core', roles['phase1_core'],
        '--protocol-version', '7', *source)
    result = {
        'chunk_check': (*cli, 'bundle', 'chunk', '--bundle', str(spec.bundle),
            '--chunk-manifest', str(spec.chunk_manifest), '--manifest', str(spec.manifest), '--check', '--strict'),
        'source_scope': (*cli, 'download', 'scope', '--manifest', str(spec.manifest), '--project', spec.project),
        'full_schema': (py, '-c', 'from linkml.validator.cli import cli; cli()', '-s', full_schema, '-C', 'Dataset', paths['full']),
        'full_terms': (py, '-c', 'from linkml_term_validator.cli import main; main()', 'validate-data', paths['full'],
                       '--schema', full_schema, '--target-class', 'Dataset'),
        'phase1_receipts': (*cli, '--manifest', str(spec.manifest), 'receipts', 'check',
            '--method', spec.method, '--label', spec.label, '--project', spec.project,
            '--bundle', str(spec.bundle), '--chunk-manifest', str(spec.chunk_manifest),
            '--native-shared-selection', doc['registration_path'], '--strict'),
        'advance': (py, '-m', 'data_sheets_schema.native_shared_stage', 'advance', '--registration', doc['registration_path']),
        'derive_core': (*cli, 'derive', 'core', '--full', paths['full'], '--out', paths['core'], *pair_schemas),
        'core_schema': (py, '-c', 'from linkml.validator.cli import cli; cli()', '-s', core_schema, '-C', 'CoreDataset', paths['core']),
        'pair': (py, '-m', 'data_sheets_schema.d4d_pair_consistency', '--full', paths['full'], '--core', paths['core'], *pair_schemas),
        'original_source_inventory': (py, '-m', 'data_sheets_schema.source_review', '--record', roles['phase1_full'], '--artifact', 'original_full'),
        'final_source_inventory': (py, '-m', 'data_sheets_schema.source_review', '--record', paths['full'], '--artifact', 'final_full'),
        'draft': (py, '-m', 'data_sheets_schema.source_attribution_preflight', '--report', paths['report'],
            '--record', paths['full'], '--bundle', str(spec.bundle), '--chunk-manifest', str(spec.chunk_manifest),
            '--protocol-version', '7', *source),
        'audit_evidence': evidence,
        'final_evidence': (*evidence, '--final-full', paths['full'], '--final-core', paths['core'], '--report', paths['report']),
        'derive_final_core': (*cli, 'derive', 'core', '--full', paths['full'], '--out', paths['core'],
                              *pair_schemas, '--phase4-complete'),
        'final_scope': (*cli, 'download', 'scope', '--manifest', str(spec.manifest), '--project', spec.project,
            '--check', '--record', paths['full'], '--record', paths['core'], '--strict'),
    }
    result['recorder'] = (*cli, 'provenance', 'record', '--project', spec.project, '--method', spec.method,
        '--label', spec.label, '--input-bundle', str(spec.bundle), '--manifest', str(spec.manifest),
        '--profile', spec.profile, '--chunk-manifest', str(spec.chunk_manifest),
        '--reasoning-effort', spec.reasoning_effort,
        *(item for path in selection.ASSET_HASHES for item in ('--prompt', path)),
        '--render-spec-json', json.dumps(spec.render_spec(), sort_keys=True, separators=(',', ':')),
        '--prompt-text-env', 'D4D_LAUNCH_INSTRUCTION')
    return result


def _scientific_evidence(assets):
    from .api_runner import NATIVE_SOURCE_STOP
    raw = assets['src/download/prompts/evidence_protocol_v7.md'].decode('utf-8')
    marker = '### Relationships and document attribution'
    if raw.count(marker) != 1:
        raise ValueError('native shared evidence projection cannot find its scientific rules')
    text = raw[raw.index(marker):]
    for old, new in (
        ('For Phase 3, return an audit object with findings, summary and source_review.',
         'The checked helper-assembled audit has findings, summary and source_review. Each response uses its current stage contract.'),
        ('Add `source_review` to the audit object.', 'The checked assembled audit includes `source_review`.'),
        ('results and confirm the agent stopped on any failed check, as well as verifying\n'
         'the original-freeze hashes and final artifacts. Current-file validation alone\n'
         'cannot establish that tool-history requirement.', NATIVE_SOURCE_STOP),
    ):
        if text.count(old) != 1:
            raise ValueError('native evidence projection cannot adapt changed output wording')
        text = text.replace(old, new)
    return '## Scientific evidence rules from protocol 7\n\n' + text


def instruction(spec):
    from . import api_runner as api
    doc = validate_spec(spec)
    data = metadata(spec)
    assets = selection.capture_assets()
    by_name = {a.pin.role[len('asset:'):]: a.raw for a in assets}
    runtime = _runtime(_read_identity(data['native_shared_runtime_declaration'], 'runtime_declaration').raw,
                       spec.provider, spec.reasoning_effort)
    helpers = commands(spec)
    paths = spec._agentic_artifact_paths
    header = '\n'.join((f'# D4D Datasheet for {spec.project} Dataset',
        '# Generation Method: schema-grounded agentic, phase 1', f'# Agent runtime: {c.RUNTIME}',
        f'# Provider: {spec.provider}', f'# Model: {runtime["model"]}',
        '# Model basis: caller runtime declaration; actual runtime must be verified',
        f'# Reasoning effort: {spec.reasoning_effort}',
        '# Mode: native shared generation v1, generic-v10 prompt', f'# Prompt: {selection.PROMPT}',
        f'# Arm: {spec.arm}', f'# Source bundle: {spec.bundle}', spec.manifest_line,
        f'# Schema: {doc["inputs"]["full_schema"]["root"]}', '# Prior D4D factual reuse: prohibited',
        '# Temperature: unknown (not observed from the agent runtime)', f'# Generated: {spec.run_date}'))
    receipt = api.PHASE_INSTRUCTIONS['full_receipt'].split('per the arm prompt\'s receipt rule: ', 1)
    if len(receipt) != 2:
        raise ValueError('native receipt projection cannot adapt changed shape instructions')
    text = (f'Generate the full/core D4D pair for {spec.project}, label {spec.label}.\n'
        f'<!-- D4D prompt renderer version {c.RENDERER} -->\n\n'
        + selection.rules_from_assets(assets) + '\n' + _scientific_evidence(by_name)
        + '\n\n## Complete selected generation context\n\n'
        + json.dumps(data['native_shared_generation_context'], sort_keys=True, ensure_ascii=False, indent=2)
        + '\n\n## Initial outputs and immutable stage roles\n\n'
        + json.dumps({'model_files': paths, 'helper_owned': {r.role: r.path for r in c.role_paths(doc['registration_path'], doc['stage_root'])}}, sort_keys=True, indent=2)
        + '\n\nRead the complete selected bundle and its chunk manifest, the selected source manifest, '
          'and the complete captured full/core schema imports before using them. Use only those declared inputs. '
          'Run chunk_check and source_scope before generation. Write the full and original receipt as separate files. '
          'The full begins with this exact header:\n\n```yaml\n' + header + '\n```\n\n'
        + 'The separate original receipt has this shape: ' + receipt[1]
        + '\n\nRun full_schema, full_terms and phase1_receipts on the current originals before advance. '
          'Fix initial source-grounded full/receipt defects and repeat their checks before sealing. '
          'After sealing, keep the original receipt at its model_files receipt path unchanged. '
          'The helper owns the completed effective receipt at the effective_receipt role; '
          'do not copy it over the original receipt. The selected final receipt check verifies the original '
          'against its seal and assesses the helper-owned effective receipt against the reconciled full record. '
          'After the receipt stage reports await_core, run derive_core, core_schema and pair; advance then binds the genuine core. '
          'Read original_source_inventory before completing typed audit stages. After assembly_complete, run audit_evidence '
          'before applying recommendations. Reconcile full, derive_final_core, validate full/core and pair, '
          'repeat the selected receipt check and final_scope, and read final_source_inventory before each report rewrite. '
          'Run draft before final_evidence; run recorder last. Never use a stage or helper success as overall completion.\n\n'
        + f'Registered maximum draft checks: {data["native_shared_max_draft_checks"]}.\n\n'
        + '## Reconciliation and report contracts\n\n'
        + api.evidence_phase_contract('reconcile_full', 26, _include_shared=False) + '\n\n'
        + api.evidence_phase_contract('report', 26, _include_shared=False) + '\n\n'
        + api.shared_evidence_contract() + '\n\n## Exact registered helper commands\n\n')
    for name, argv in helpers.items():
        text += name + ':\n\n```bash\n' + shlex.join(argv) + '\n```\n\n'
    text += ('The launcher supplies the exact saved instruction in D4D_LAUNCH_INSTRUCTION. '
             'The recorder reads that environment variable itself; execute its command exactly. '
             'Return the recorded checks and outcome, without claiming scientific approval.\n')
    if len(text.encode('utf-8')) > doc['bounds']['max_request_bytes']:
        raise ValueError('complete native instruction exceeds the selected request-byte limit')
    return text


def assembly_digest():
    from . import api_runner as api
    layout = ('native_shared_generation_v1: captured S and sole R; original full/receipt seal; '
              'preserved original receipt and separately assessed helper-owned effective receipt; '
              'one receipt answer or verified zero work; genuine core seal; all workers, omission and integration; '
              'fresh assembly replay; reconciliation, source draft, final checks and live recorder')
    assets = selection.capture_assets()
    parts = {'layout': layout, 'descriptor': selection.descriptor(),
             'rules': selection.rules_from_assets(assets),
             'scientific_evidence': _scientific_evidence({a.pin.role[len('asset:'):]: a.raw for a in assets}),
             'receipt_shape_source': api.PHASE_INSTRUCTIONS['full_receipt'],
             'reconcile': api.evidence_phase_contract('reconcile_full', 26, _include_shared=False),
             'report': api.evidence_phase_contract('report', 26, _include_shared=False),
             'shared_evidence': api.shared_evidence_contract()}
    return {'sha256': c.sha(c.canonical(parts)), 'layout': layout}
