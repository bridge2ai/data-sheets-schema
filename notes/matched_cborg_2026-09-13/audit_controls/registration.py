"""Identity, ancestry and accounting for a separately registered native audit."""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys

from filelock import Timeout

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CONTROLS = BASE / 'native_controls'
for directory in (BASE, CONTROLS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from budgeted_cborg import (BudgetStop, LEGACY_UPSTREAM_READ_SECONDS, Ledger, POLICY_COUNT_PAUSE_SECONDS,
                            POLICY_COUNT_TRY_SECONDS, UPSTREAM_CONNECT_SECONDS, attempt_identity)

TRANSITION = 'scientific_contract_transition'
TRANSITION_KIND = 'frozen_pair_protocol_v4'
SOURCE_METADATA_TRANSITION_KIND = 'frozen_pair_protocol_v5'
CLAIM_CLARIFICATION_TRANSITION_KIND = 'frozen_pair_claim_clarification_v1'
DRAFT_GRAMMAR_TRANSITION_KIND = 'frozen_pair_draft_grammar_v1'
SCHEMA_SEMANTICS_TRANSITION_KIND = 'frozen_pair_schema_semantics_v1'
BATCH_TRANSITION_KIND = 'frozen_pair_integrated_batches_v1'
BATCH_FORMAT_TRANSITION_KIND = 'frozen_pair_batch_format_v1'
BATCH_NAVIGATION_TRANSITION_KIND = 'frozen_pair_batch_navigation_v1'
BATCH_NAVIGATION_KIND = 'explicit_row_reads_v1'
BATCH_CHILD_NAVIGATION_TRANSITION_KIND = 'frozen_pair_child_navigation_v1'
BATCH_CHILD_NAVIGATION_KIND = 'explicit_child_reads_v1'
VERSIONED_SCIENTIFIC_FILES = frozenset({'api_runner.py', 'evidence_assertions.py'})


def scientific_contract(manifest):
    """An explicit new audit instrument, never a relabelled parent generation."""
    upgraded = TRANSITION in manifest
    pair = (manifest.get('protocol_version'), manifest.get('render_version'))
    transitions = {(4, 15): {'kind': TRANSITION_KIND},
                   (5, 16): {'kind': SOURCE_METADATA_TRANSITION_KIND},
                   (5, 17): {'kind': CLAIM_CLARIFICATION_TRANSITION_KIND},
                   (6, 18): {'kind': DRAFT_GRAMMAR_TRANSITION_KIND},
                   (6, 19): {'kind': SCHEMA_SEMANTICS_TRANSITION_KIND},
                   (7, 20): {'kind': BATCH_TRANSITION_KIND},
                   (7, 21): {'kind': BATCH_FORMAT_TRANSITION_KIND},
                   (7, 22): {'kind': BATCH_NAVIGATION_TRANSITION_KIND},
                   (7, 23): {'kind': BATCH_CHILD_NAVIGATION_TRANSITION_KIND}}
    if (any(type(value) is not int for value in pair) or
            (pair not in transitions if upgraded else pair != (3, 14)) or
            (upgraded and (type(manifest[TRANSITION]) is not dict or
                          manifest[TRANSITION] != transitions[pair]))):
        raise BudgetStop('unsupported scientific contract transition: require unchanged 3/14 '
                         'or explicit frozen_pair_protocol_v4 with 4/15 or '
                         'frozen_pair_protocol_v5 with 5/16 or '
                         'frozen_pair_claim_clarification_v1 with 5/17 or '
                         'frozen_pair_draft_grammar_v1 with 6/18 or '
                         'frozen_pair_schema_semantics_v1 with 6/19 or '
                         'frozen_pair_integrated_batches_v1 with 7/20 or '
                         'frozen_pair_batch_format_v1 with 7/21 or '
                         'frozen_pair_batch_navigation_v1 with 7/22 or '
                         'frozen_pair_child_navigation_v1 with 7/23')
    return upgraded


def audit_batch_navigation(manifest):
    """Audit-only opt-in; omission preserves every legacy navigation byte."""
    selected = 'audit_batch_navigation' in manifest
    version = manifest.get('render_version')
    if version in (22, 23):
        kind, transition = ((BATCH_NAVIGATION_KIND, BATCH_NAVIGATION_TRANSITION_KIND)
                            if version == 22 else
                            (BATCH_CHILD_NAVIGATION_KIND, BATCH_CHILD_NAVIGATION_TRANSITION_KIND))
        if (manifest.get('kind') != 'd4d_native_audit_continuation'
                or type(manifest.get('protocol_version')) is not int or manifest['protocol_version'] != 7
                or type(manifest.get('render_version')) is not int
                or manifest.get(TRANSITION) != {'kind': transition}
                or not selected or type(manifest['audit_batch_navigation']) is not dict
                or manifest['audit_batch_navigation'] != {'kind': kind}):
            raise BudgetStop(f'renderer {version} requires exact explicit audit batch navigation')
        return kind
    if selected:
        raise BudgetStop('audit_batch_navigation requires explicit audit renderer 22 or 23')
    return None


def schema_semantic_context(manifest):
    """Only the exact selected scientific transition executes the new helper."""
    scientific_contract(manifest)
    return manifest['render_version'] in (19, 20, 21, 22, 23)


def versioned_scientific_files(manifest):
    """Only an explicit protocol-5 transition changes source-review semantics."""
    scientific_contract(manifest)
    return (VERSIONED_SCIENTIFIC_FILES | {'source_review.py'}
            if manifest['protocol_version'] >= 5 else VERSIONED_SCIENTIFIC_FILES)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.keys()); pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError('nonfinite JSON')
        elif isinstance(item, str):
            item.encode('utf-8')
    return value


def canonical_json(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def read_json(path):
    return strict_json(Path(path).read_bytes())


def canonical_path(value, *, exists=False):
    if not isinstance(value, str) or not value:
        raise BudgetStop('a nonempty canonical path is required')
    path = Path(value)
    if not path.is_absolute() or path.resolve(strict=exists) != path:
        raise BudgetStop('registered path is not absolute and canonical')
    return path


def pinned(manifest, value, expected=None):
    path = canonical_path(value, exists=True)
    recorded = manifest['pinned_files'].get(str(path))
    if (not path.is_file() or not recorded or
            (expected is not None and recorded != expected) or sha(path) != recorded):
        raise BudgetStop('registered input or implementation changed: ' + str(path))
    return path


@contextmanager
def working_directory(path):
    """Only used for offline replay, before starting any provider threads."""
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


def parent_path(parent, value):
    path = Path(value)
    return path if path.is_absolute() else Path(parent['repository']) / path


def parent_job(manifest):
    generation = read_json(manifest['parent']['registration'])
    jobs = [job for job in generation['generation']['jobs']
            if job['id'] == manifest['parent']['job_id']]
    if len(jobs) != 1:
        raise BudgetStop('parent generation job is missing or ambiguous')
    return generation, jobs[0]


def inspect_parent(manifest):
    """Replay actual parent history; never synthesize events for this session."""
    from data_sheets_schema.api_runner import RunSpec
    from native_control import check_control_history, load_native_events
    from native_phase_history import phase_history
    from run_native_canary import _classify_command, prescribed_programs

    upgraded = scientific_contract(manifest)
    parent = manifest['parent']
    generation, job = parent_job(manifest)
    if generation['repository'] != parent['repository']:
        raise BudgetStop('parent repository differs from its registration')
    expected_attempt = Path(parent['registration']).parent / 'attempts' / parent['job_id']
    for key, name in (('result', 'result.json'), ('transcript', 'transcript.jsonl'), ('control', 'control.jsonl')):
        if canonical_path(parent[key]) != expected_attempt / name:
            raise BudgetStop('parent terminal evidence path differs from its attempt')
    overlay = read_json(parent['overlay'])
    result = read_json(parent['result'])
    if (overlay['registration_sha256'] != sha(parent['registration']) or
            result.get('registration_sha256') != sha(parent['registration']) or
            result.get('overlay_sha256') != sha(parent['overlay']) or
            result.get('job') != parent['job_id']):
        raise BudgetStop('parent execution identities differ')
    if (job.get('execution_arm') != 'agentic' or job['render_spec'].get('condition') != 'generic_v9' or
            job['render_spec'].get('render_version') != 14 or result.get('status') != 'stopped' or
            result.get('unfinished_handlers_at_freeze') != 0 or result.get('reason_source') != 'proxy'):
        raise BudgetStop('parent is not a frozen native transport stop with renderer 14')
    if result.get('disqualifying_denials'):
        raise BudgetStop('parent has disqualifying tool denials')
    paths = job['render_spec']['agentic_artifact_paths']
    evidence = parent_path(parent, paths['core']).parent / 'evidence'
    for key in ('audit.json',):
        if (evidence / key).exists():
            raise BudgetStop('parent already has an audit; do not silently replace it')
    expected = {
        'original_full': evidence / 'original_full.yaml',
        'original_core': evidence / 'original_core.yaml',
        'receipt': parent_path(parent, paths['receipt']),
        'bundle': Path(job['input_identity']['bundle']['path']),
        'chunk_manifest': Path(job['input_identity']['chunks']['path']),
        'source_manifest': Path(job['input_identity']['source_manifest']['path']),
        'parent_instruction': Path(job['instruction']),
        'protocol': ((Path(manifest['repository']) / f"src/download/prompts/evidence_protocol_v{manifest['protocol_version']}.md")
                     if upgraded else Path(parent['repository']) / 'src/download/prompts/evidence_protocol_v3.md'),
    }
    resources = job['render_spec']['agentic_toolchain']['resources']
    expected.update(full_schema=Path(resources['src/data_sheets_schema/schema/data_sheets_schema_all.yaml']),
                    core_schema=Path(resources['src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml']))
    for key, path in expected.items():
        if canonical_path(manifest['inputs'][key], exists=True) != path:
            raise BudgetStop('audit input is not the exact inherited ' + key)
    for key, old_key in (('bundle', 'bundle'), ('chunk_manifest', 'chunks'), ('source_manifest', 'source_manifest')):
        if sha(expected[key]) != job['input_identity'][old_key]['sha256']:
            raise BudgetStop('inherited source bytes differ')
    for key in ('original_full', 'original_core', 'receipt'):
        path = expected[key]
        relative = str(path.relative_to(parent['repository']))
        if result['artifacts'].get(relative, result['artifacts'].get(str(path))) != sha(path):
            raise BudgetStop('inherited artifact differs from the frozen result')
    for kind in ('full', 'core'):
        if sha(parent_path(parent, paths[kind])) != sha(expected['original_' + kind]):
            raise BudgetStop('parent record changed after its original snapshot')
    events = load_native_events(Path(parent['transcript']))
    policy = overlay['per_job_command_policy'][parent['job_id']]
    control = check_control_history(events, Path(parent['control']), policy, _classify_command,
                                    expected_attempt / 'cli_config')
    with working_directory(parent['repository']):
        spec = RunSpec.from_render_spec(job['render_spec'], project=job['project'],
                                       method=job['method'], label=job['label'])
        if spec.instruction != Path(job['instruction']).read_text(encoding='utf-8'):
            raise BudgetStop('shared parent instruction no longer replays exactly')
        history = phase_history(events, spec, complete=False, repository=parent['repository'], command_policy=policy)
    if (not control.get('checked') or control.get('problems') or history['problems'] or
            history['terminal_failures'] or history['pending_tool_ids'] or
            not history['phase2_completed'] or not history['receipt_gate_current']):
        raise BudgetStop('parent does not establish clean inherited Phase 1/2 boundaries')
    freeze_programs = [program for program in prescribed_programs(
        Path(job['instruction']).read_text(encoding='utf-8'), generation['python'])
        if 'original_sha256' in program]
    if len(freeze_programs) != 1:
        raise BudgetStop('parent original-freeze command is ambiguous')
    calls, freezes = {}, []
    expected_hashes = {str(expected['original_full'].relative_to(parent['repository'])): sha(expected['original_full']),
                       str(expected['original_core'].relative_to(parent['repository'])): sha(expected['original_core'])}
    for line, event in enumerate(events, 1):
        message = event.get('message')
        for block in (message.get('content', []) if isinstance(message, dict) else []):
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                command = block.get('input', {}).get('command', '')
                try:
                    tokens = shlex.split(command)
                except ValueError:
                    continue
                if len(tokens) == 3 and tokens[:2] == [generation['python'], '-c'] and tokens[2].strip() == freeze_programs[0]:
                    calls[block['id']] = line
            if block.get('type') == 'tool_result' and block.get('tool_use_id') in calls:
                metadata = event.get('tool_use_result') or {}
                try:
                    value = strict_json(metadata.get('stdout', ''))
                except (ValueError, TypeError):
                    continue
                if (block.get('is_error') is False and metadata.get('interrupted') is False and
                        value == {'original_sha256': expected_hashes}):
                    freezes.append({'call_line': calls[block['tool_use_id']], 'result_line': line,
                                    'original_sha256': expected_hashes})
    if len(freezes) != 1 or freezes[0]['result_line'] <= history['phase1_receipt_checks'][-1]['result_event']:
        raise BudgetStop('parent exact original freeze lacks successful ordered evidence')
    with working_directory(parent['repository']):
        before_freeze = phase_history(events[:freezes[0]['call_line'] - 1], spec, complete=False,
            repository=parent['repository'], command_policy=policy)
    if not before_freeze['phase2_completed'] or before_freeze['pending_tool_ids']:
        raise BudgetStop('original freeze precedes completed core derivation')
    return {'kind': 'inherited_native_phase12', 'registration_sha256': sha(parent['registration']),
        'overlay_sha256': sha(parent['overlay']), 'result_sha256': sha(parent['result']),
        'transcript_sha256': sha(parent['transcript']), 'control_sha256': sha(parent['control']),
        'phase_history': history, 'original_freeze': freezes[0],
        'source_reads_basis': 'Preserved parent transcript; the new auditor receives complete inputs inline.',
        'new_generation_claimed': False}


def implementation_paths(manifest):
    repository = canonical_path(manifest['repository'], exists=True)
    paths = set((repository / 'src/data_sheets_schema').rglob('*.py'))
    if manifest.get('render_version') not in (21, 22, 23):
        paths.discard(repository / 'src/data_sheets_schema/audit_batch_format.py')
    if manifest.get('render_version') not in (20, 21, 22, 23):
        paths.difference_update(repository / 'src/data_sheets_schema' / name
                                for name in ('audit_batches.py', 'audit_batch_context.py'))
    if schema_semantic_context(manifest):
        paths.add(repository / 'src/data_sheets_schema/schema_semantics.py')
    else:
        paths.discard(repository / 'src/data_sheets_schema/schema_semantics.py')
    paths.update((repository / 'src/data_sheets_schema').rglob('*.yaml'))
    paths.update((repository / 'src/data_sheets_schema').rglob('*.json'))
    paths.update(path for path in (repository / 'src/download/prompts').rglob('*') if path.is_file())
    paths.update(HERE.glob('*.py'))
    if manifest.get('render_version') not in (20, 21, 22, 23):
        paths.difference_update(HERE / name for name in
            ('batch_registration.py', 'batch_native.py', 'batch_history.py', 'batch_output.py'))
    if 'audit_output' not in manifest and 'audit_drafting' not in manifest and manifest.get('render_version') not in (20, 21, 22, 23):
        paths.discard(HERE / 'output_parts.py')
    if 'audit_drafting' not in manifest and manifest.get('render_version') not in (20, 21, 22, 23):
        paths.discard(HERE / 'draft_output.py')
        paths.discard(HERE / 'draft_history.py')
    if 'audit_contract_context' not in manifest:
        paths.discard(HERE / 'contract_context.py')
    paths.update(CONTROLS.glob('*.py'))
    paths.update(BASE / name for name in ('budgeted_cborg.py', 'run_api_canary.py', 'prepare_registration.py'))
    if 'budget_amendment' in manifest:
        paths.add(BASE / 'budget_amendment.py')
    paths.update(repository / name for name in ('pyproject.toml', 'poetry.lock'))
    if 'context_recovery' in manifest:
        paths.update(BASE / name for name in ('native_context.py', 'native_context_control.py'))
    if 'sequence_claim' in manifest:
        from sequence_claim import enabled, IMPLEMENTATIONS
        enabled(manifest)
        paths.update(IMPLEMENTATIONS)
    return paths


def required_paths(manifest):
    from .transport import transport_paths
    paths = implementation_paths(manifest)
    if 'budget_amendment' in manifest:
        from budget_amendment import paths as amendment_paths
        paths.update(amendment_paths(manifest))
        paths.add(budget_amendment_predecessor_path(manifest))
    if 'audit_worker_checkpoint' in manifest:
        from .worker_checkpoint import proof_paths
        paths.update(proof_paths(manifest))
    if 'audit_batches' in manifest:
        from .batch_output import required_paths as batch_paths
        paths.update(batch_paths(manifest))
        paths.update(batch_authority_paths(manifest))
    if 'context_recovery' in manifest:
        from native_context_control import paths as recovery_paths
        paths.update(Path(name) for name in recovery_paths(manifest))
    paths.update(transport_paths(manifest))
    paths.add(canonical_path(manifest['python_identity']['resolved_path'], exists=True))
    config = Path(manifest['python']).parent.parent / 'pyvenv.cfg'
    if config.exists():
        paths.add(config.resolve())
    paths.add(canonical_path(manifest['native_runtime']['executable'], exists=True))
    paths.update(canonical_path(value, exists=True) for value in manifest['inputs'].values())
    if schema_semantic_context(manifest):
        paths.update(schema_semantic_paths(manifest))
    paths.update(canonical_path(manifest['job'][key], exists=True) for key in ('instruction', 'system_prompt'))
    parent = manifest['parent']
    if TRANSITION in manifest:
        scientific_contract(manifest)
        paths.add(canonical_path(str(Path(parent['repository']) /
                      'src/download/prompts/evidence_protocol_v3.md'), exists=True))
        for filename in versioned_scientific_files(manifest):
            paths.add(canonical_path(str(Path(parent['repository']) /
                          'src/data_sheets_schema' / filename), exists=True))
    paths.update(canonical_path(parent[key], exists=True) for key in
                 ('registration', 'overlay', 'result', 'transcript', 'control', 'phase2_proof',
                  'reconciliation_receipt', 'reconciled_checkpoint'))
    for record in (read_json(parent['registration']), read_json(parent['overlay'])):
        paths.update(canonical_path(str(parent_path(parent, name).resolve()), exists=True) for name in record['pinned_files'])
    paths.update(continuation_paths(manifest))
    return paths


def continuation_paths(manifest):
    """The predecessor evidence an audit pins: its checkpoint, a probe link, a reconciliation bridge."""
    paths = {canonical_path(manifest['budget']['continuation']['checkpoint'], exists=True)}
    from .probe_predecessor import paths as probe_paths
    paths.update(probe_paths(manifest))
    bridge = manifest['budget']['continuation'].get('reconciliation')
    if bridge is not None:
        if not isinstance(bridge, dict) or set(bridge) != {'source_registration', 'source_ledger', 'receipt', 'result'}:
            raise BudgetStop('invalid audit reconciliation identity fields')
        paths.update(canonical_path(value, exists=True) for value in bridge.values())
        from .runtime_closure import closure_paths
        paths.update(closure_paths(read_json(bridge['receipt'])))
        source = read_json(bridge['source_registration'])
        if 'audit_batches' in source:
            from .batch_native import require_closed_batch_runtime
            paths.update(Path(name) for name in source['pinned_files'])
            paths.update(require_closed_batch_runtime(source, read_json(bridge['result'])))
    return paths


def schema_semantic_paths(manifest):
    """Pin the exact schema closure consumed by the selected pure renderer."""
    if not schema_semantic_context(manifest):
        return set()
    from data_sheets_schema.schema_snapshot import capture_schema
    paths = set()
    for role in ('full_schema', 'core_schema'):
        snapshot = capture_schema(canonical_path(manifest['inputs'][role], exists=True), strict=True)
        for _, path, raw in snapshot.sources:
            if not isinstance(raw, bytes):
                raise BudgetStop('schema semantics has an unavailable schema dependency')
            paths.add(canonical_path(str(path), exists=True))
    return paths


def registered_profile(manifest):
    """Resolve a local profile against its registration, never replay cwd (#2396).

    Relative declarations belong to the registered repository. Explicit absolute
    profile overrides remain absolute, including external authorities. Callers
    retain their existing pin/hash gates; offline preparation can discover the
    authority before constructing its pin map. No global profile or cwd changes.
    """
    from dataclasses import replace
    from data_sheets_schema.profiles import profile_named
    profile = profile_named(manifest['profile'])
    if profile.vocabulary_pin is None:
        return profile
    if profile.tracks_digest_pin:
        from data_sheets_schema import schema_digest
        declared = Path(schema_digest.VOCABULARY_PIN)
    else:
        declared = Path(profile.vocabulary_pin)
    if not declared.is_absolute():
        declared = canonical_path(manifest['repository'], exists=True) / declared
    authority = canonical_path(str(declared), exists=True)
    return replace(profile, vocabulary_pin=authority, tracks_digest_pin=False)


def batch_authority_paths(manifest):
    """Exact complete schema imports and the selected profile vocabulary only."""
    scientific_contract(manifest)
    if manifest['render_version'] not in (20, 21, 22, 23):
        return set()
    from data_sheets_schema.profiles import vocabulary_bytes
    profile = registered_profile(manifest)
    vocabulary_bytes(profile)  # Declared-but-missing vocabularies fail closed.
    paths = schema_semantic_paths(manifest)
    if profile.pin_path is not None:
        paths.add(canonical_path(str(profile.pin_path.absolute()), exists=True))
    return paths


def validate_scientific_identity(manifest):
    upgraded = scientific_contract(manifest)
    parent = manifest['parent']
    for filename in ('api_runner.py', 'evidence_assertions.py', 'source_review.py', 'profiles.py', 'schema_digest.py'):
        relative = Path('src/data_sheets_schema') / filename
        if upgraded and filename in versioned_scientific_files(manifest):
            # The selected transition records both exact implementations;
            # unrelated scientific components retain their equality gate.
            pinned(manifest, str(Path(parent['repository']) / relative))
            pinned(manifest, str(Path(manifest['repository']) / relative))
            continue
        if sha(Path(manifest['repository']) / relative) != sha(Path(parent['repository']) / relative):
            raise BudgetStop('shared scientific instrument changed: ' + filename)


def verify(manifest, path, expected_sha):
    if sha(path) != expected_sha:
        raise BudgetStop('audit continuation registration changed')
    repository = canonical_path(manifest['repository'], exists=True)
    if Path.cwd() != repository:
        raise BudgetStop('audit controller is running from another repository')
    head = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip()
    if head != manifest['repository_commit']:
        raise BudgetStop('audit continuation code commit changed')
    code = sorted(str(value.relative_to(repository)) for value in implementation_paths(manifest))
    for command in (['git', 'ls-files', '--error-unmatch', '--', *code],
                    ['git', 'diff', '--quiet', 'HEAD', '--', *code]):
        if subprocess.run(command, cwd=repository, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            raise BudgetStop('audit implementation files differ from the registered committed code')
    if (sys.executable != manifest['python'] or sys.version != manifest['python_version'] or
            str(Path(sys.executable).resolve()) != manifest['python_identity']['resolved_path'] or
            sys.prefix != manifest['python_identity']['prefix']):
        raise BudgetStop('audit Python interpreter or environment changed')
    from data_sheets_schema import api_runner
    if Path(api_runner.__file__).resolve() != repository / 'src/data_sheets_schema/api_runner.py':
        raise BudgetStop('audit implementation imported from another checkout')
    for value in manifest['pinned_files']:
        pinned(manifest, value)
    failure = Path(manifest['job']['attempt_dir']) / 'validation_failure.json'
    if failure.exists():
        raise BudgetStop('audit validation failed; no further paid request is permitted')
    if 'audit_output' in manifest:
        from .output_parts import configuration, receipt_paths
        configuration(manifest, path)
        if os.path.lexists(receipt_paths(manifest)[1]):
            raise BudgetStop('audit assembly failed; no further paid request is permitted')
    if 'audit_drafting' in manifest:
        from .draft_output import configuration, verify_open
        configuration(manifest, path)
        verify_open(manifest)
    if 'audit_batches' in manifest:
        from .batch_output import configuration, verify_open
        configuration(manifest, path)
        verify_open(manifest)


def validate_registration(path):
    path = canonical_path(str(Path(path).absolute()), exists=True)
    manifest = read_json(path)
    if (manifest.get('kind') != 'd4d_native_audit_continuation' or type(manifest.get('schema_version')) is not int or manifest.get('schema_version') != 1):
        raise BudgetStop('unsupported native audit-continuation contract')
    scientific_contract(manifest)
    audit_batch_navigation(manifest)
    if manifest['protocol_version'] == 6 and 'audit_drafting' not in manifest:
        raise BudgetStop('protocol-6 audit requires its explicit bounded drafting registration')
    if 'audit_worker_checkpoint' in manifest:
        from .worker_checkpoint import validate as validate_worker_checkpoint
        checkpoint_source = validate_worker_checkpoint(manifest)
    if manifest['protocol_version'] == 7 and 'audit_batches' not in manifest:
        raise BudgetStop('protocol-7 audit requires its explicit batch registration')
    if 'audit_batches' in manifest:
        from .batch_registration import validate_selection
        validate_selection(manifest, path)
    if 'audit_contract_context' in manifest:
        from .contract_context import enabled
        enabled(manifest)
    from .transport import verified_context
    verified_context(manifest)
    verify(manifest, path, sha(path))
    missing = {str(value) for value in required_paths(manifest)} - set(manifest['pinned_files'])
    if missing:
        raise BudgetStop('audit implementation/input closure is not fully pinned')
    parent = manifest['parent']
    generation, parent_record = parent_job(manifest)
    for record in (generation, read_json(parent['overlay'])):
        for filename, digest in record['pinned_files'].items():
            pinned(manifest, str(parent_path(parent, filename).resolve()), digest)
    overlay = read_json(parent['overlay'])
    if (manifest['native_runtime']['executable'] != overlay['claude_executable'] or
            manifest.get('provider_context_policy') != generation.get('provider_context_policy')):
        raise BudgetStop('audit changes inherited native executable or provider policy')
    if (manifest['model'] != generation['model'] or manifest['profile'] != parent_record['profile'] or
            manifest['native_runtime']['version'] != generation['claude_version'] or
            manifest['native_runtime'].get('effort') != 'native_default'):
        raise BudgetStop('audit changes the inherited model, profile or native effort')
    validate_scientific_identity(manifest)
    proof = inspect_parent(manifest)
    if read_json(parent['phase2_proof']) != proof:
        raise BudgetStop('inherited phase proof differs from actual parent history')
    job = manifest['job']
    if not isinstance(job.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,150}', job['id']):
        raise BudgetStop('invalid audit job identity')
    attempt, output = canonical_path(job['attempt_dir']), canonical_path(job['output_dir'])
    if (attempt != path.parent / 'attempts' / job['id'] or output != attempt / 'output' or
            canonical_path(job['audit_path']) != output / 'audit.json'):
        raise BudgetStop('audit destinations differ from the exclusive registered layout')
    if any(output == Path(name) or output in Path(name).parents or attempt == Path(name) or attempt in Path(name).parents
           for name in manifest['pinned_files']):
        raise BudgetStop('audit writable destinations overlap immutable inputs')
    expected_argv = [manifest['python'], '-m', 'audit_controls.contract', '--registration', str(path)]
    if job['validator_argv'] != expected_argv:
        raise BudgetStop('audit validator arguments differ from registration')
    if 'audit_output' in manifest:
        from .output_parts import configuration
        configuration(manifest, path)
    if 'audit_drafting' in manifest:
        from .draft_output import configuration
        configuration(manifest, path)
    if 'audit_batches' in manifest:
        from .batch_output import configuration
        configuration(manifest, path)
    readable = set(manifest['inputs'].values()) | {job['instruction'], job['system_prompt']}
    if 'context_recovery' in manifest:
        from native_context_control import paths as recovery_paths, validate as validate_recovery
        validate_recovery(manifest, path)
        readable.update(recovery_paths(manifest))
    if set(job['readable_inputs']) != readable:
        raise BudgetStop('audit readable input roster differs')
    if type(job['deadline_seconds']) is not int or job['deadline_seconds'] <= 0:
        raise BudgetStop('audit deadline must be positive whole seconds')
    native_api_timeout(manifest)
    native_api_force_idle_timeout(manifest)
    native_stall_policy(manifest)
    native_response_buffer(manifest)
    native_history_control(manifest)
    budget = manifest['budget']
    previous = read_json(budget['continuation']['checkpoint'])
    costs = [Decimal(str(row.get('cost_usd', 'NaN'))) for row in previous['requests']]
    ids = [row.get('id') for row in previous['requests']]
    if (any(row.get('status') != 'settled' for row in previous['requests']) or
            any(not value.is_finite() or value < 0 for value in costs) or len(ids) != len(set(ids)) or
            any(not isinstance(value, str) or not value for value in ids) or
            sum(costs, Decimal(0)) != Decimal(str(budget['continuation']['cost_usd']))):
        raise BudgetStop('audit billing predecessor is unresolved or inconsistent')
    if 'budget_amendment' in manifest:
        from budget_amendment import effective_total, validate_predecessor
        effective_total(manifest, generation)
        validate_predecessor(manifest, previous, checkpoint_sha256=budget['continuation']['sha256'])
    else:
        for key, old_key in (('additional_usd', 'additional_cap_usd'), ('per_attempt_usd', 'attempt_cap_usd')):
            if Decimal(str(budget[key])) != Decimal(str(previous[old_key])) or budget[key] != generation['budget'][key]:
                raise BudgetStop('audit changes the approved allocation or default cap')
    validate_budget_amendment_predecessor(manifest, previous)
    cap = budget.get('per_job_attempt_usd', {}).get(job['id'])
    approved = generation['budget'].get('per_job_attempt_usd', {}).get(parent['job_id'], generation['budget']['per_attempt_usd'])
    if (set(budget.get('per_job_attempt_usd', {})) != {job['id']} or cap is None or
            not Decimal(str(cap)).is_finite() or not Decimal(0) < Decimal(str(cap)) <= Decimal(str(approved)) or
            budget['prices_per_token'] != generation['budget']['prices_per_token'] or
            canonical_path(budget['ledger_path']) != path.parent / 'billing.json'):
        raise BudgetStop('audit budget cap, pricing or ledger location differs')
    pinned(manifest, budget['continuation']['checkpoint'], budget['continuation']['sha256'])
    validate_audit_reconciliation(manifest)
    # A settled, unamended probe link is checked here too, not only at launch (#2505).
    from .probe_predecessor import validate_predecessor
    validate_predecessor(manifest)
    checkpoint = validate_reconciliation(manifest)
    if canonical_json(previous['requests'][:len(checkpoint['requests'])]) != canonical_json(checkpoint['requests']):
        raise BudgetStop('audit predecessor does not preserve reconciled source charges')
    from .contract import render_instruction
    from .prepare import render_system
    if Path(job['system_prompt']).read_text(encoding='utf-8') != render_system(manifest):
        raise BudgetStop('audit system prompt differs from its registered contract')
    if Path(job['instruction']).read_text(encoding='utf-8') != render_instruction(manifest):
        raise BudgetStop('audit instruction does not match its deterministic registered rendering')
    if 'audit_batches' in manifest:
        from .batch_registration import verify_rendered_inputs
        verify_rendered_inputs(manifest, path)
    if 'audit_worker_checkpoint' in manifest:
        from .batch_native import verify_checkpoint_context
        verify_checkpoint_context(manifest, checkpoint_source)
    return manifest


def native_api_timeout(manifest):
    """Optional local native SDK timeout; omission preserves its historical default."""
    runtime = manifest['native_runtime']
    if 'api_timeout_ms' not in runtime:
        return None
    value = runtime['api_timeout_ms']
    deadline = manifest['job']['deadline_seconds']
    if (type(value) is not int or value <= 0 or
            type(deadline) is not int or deadline <= 0 or value > deadline * 1000):
        raise BudgetStop('native API timeout must be positive whole milliseconds within the audit deadline')
    return value


def native_upstream_read_timeout(manifest):
    """Audit-only raw-stream read limit; absence preserves legacy transport (#2147)."""
    key = 'native_upstream_read_timeout_seconds'
    if key not in manifest:
        return None
    value = manifest[key]
    if (manifest.get('kind') != 'd4d_native_audit_continuation' or
            type(value) is not int or value <= 0):
        raise BudgetStop('upstream read timeout requires a positive whole-second audit-only setting')
    outer = native_api_timeout(manifest)
    if outer is None or value * 1000 >= outer:
        raise BudgetStop('upstream read timeout requires a larger explicit native SDK timeout within the job deadline')
    return value


def stall_policy_minimum_api_timeout_ms(manifest, count_attempts):
    """The least native SDK timeout under which the proxy, not the child,
    sees a stall first (#2152). The child's timer also covers what the proxy
    does before it sends: the bounded token-count tries with their pauses and
    the connect allowance. One minute of margin covers the reply itself."""
    bound = native_upstream_read_timeout(manifest) or LEGACY_UPSTREAM_READ_SECONDS
    before_send = count_attempts * (POLICY_COUNT_TRY_SECONDS + POLICY_COUNT_PAUSE_SECONDS) + UPSTREAM_CONNECT_SECONDS
    return (bound + before_send + 60) * 1000


def native_stall_policy(manifest):
    """Audit-only bounded in-attempt stall policy; absence preserves the
    historical stop on the first stall (#2150).

    A paid request that stalls after it was sent and before any byte reaches
    the child is counted at its whole reservation, with the provider fee left
    unknown, and the child's own retry continues the session. That debit is
    the maintainer's to authorize, so a policy that allows any must quote the
    authorization and the number of debits it covers. The proxy has to see
    the stall before the child gives up, so the native SDK timeout must cover
    the total pre-header bound in force plus the bounded token-count tries,
    and the native fetch idle timer must be registered off. Under the policy,
    killable I/O workers enforce these total bounds (#2159)."""
    key = 'native_stall_policy'
    if key not in manifest:
        return None
    value = manifest[key]
    if (manifest.get('kind') != 'd4d_native_audit_continuation' or not isinstance(value, dict) or
            set(value) != {'kind', 'count_attempts', 'max_stall_debits', 'authorization'} or
            value['kind'] != 'bounded_in_attempt_v1' or
            type(value['count_attempts']) is not int or not 1 <= value['count_attempts'] <= 5 or
            type(value['max_stall_debits']) is not int or not 0 <= value['max_stall_debits'] <= 10):
        raise BudgetStop('native stall policy is audit-only: bounded_in_attempt_v1, count_attempts 1-5, max_stall_debits 0-10')
    if not isinstance(manifest.get('native_runtime'), dict) or not isinstance(manifest.get('job'), dict):
        raise BudgetStop('native stall policy needs the registered native runtime and job')
    authorization = value['authorization']
    if value['max_stall_debits'] == 0:
        if authorization is not None:
            raise BudgetStop('a stall policy without debits carries no debit authorization')
    else:
        texts = ('exact_response', 'quoted_request', 'recorded_at')
        if (not isinstance(authorization, dict) or
                set(authorization) != {*texts, 'authorized_max_stall_debits'} or
                any(not isinstance(authorization[name], str) or not authorization[name].strip() for name in texts) or
                type(authorization['authorized_max_stall_debits']) is not int or
                authorization['authorized_max_stall_debits'] != value['max_stall_debits']):
            raise BudgetStop('stall debits need the maintainer\'s quoted standing authorization for exactly this many debits')
        outer = native_api_timeout(manifest)
        if outer is None or outer < stall_policy_minimum_api_timeout_ms(manifest, value['count_attempts']):
            raise BudgetStop('stall debits need a native SDK timeout covering the upstream read bound, '
                             'the token-count tries and the connect allowance')
        if native_api_force_idle_timeout(manifest) is not False:
            raise BudgetStop('stall debits need the native fetch idle timer registered off')
    return {'count_attempts': value['count_attempts'], 'max_stall_debits': value['max_stall_debits']}


def native_history_control(manifest):
    """Explicit responsive control for batch integration; historical workers stay v2."""
    key = 'native_history_control'
    if key not in manifest:
        return None
    value = manifest[key]
    if (manifest.get('kind') != 'd4d_native_audit_continuation' or
            'audit_batches' not in manifest or type(value) is not dict or
            value != {'kind': 'responsive_history_v1'}):
        raise BudgetStop('native history control is audit-batch-only: responsive_history_v1')
    return dict(value)


def native_response_buffer(manifest):
    """Opt-in complete-response delivery; never expose an incomplete turn (#2304)."""
    key = 'native_response_buffer'
    if key not in manifest:
        return None
    value = manifest[key]
    if (manifest.get('kind') != 'd4d_native_audit_continuation' or
            not isinstance(value, dict) or set(value) != {'kind', 'max_bytes', 'total_seconds'} or
            value['kind'] != 'complete_response_v1' or
            type(value['max_bytes']) is not int or not 1 <= value['max_bytes'] <= 64 * 1024 * 1024 or
            type(value['total_seconds']) is not int or value['total_seconds'] <= 0):
        raise BudgetStop('native response buffering is audit-only: complete_response_v1 with bounded bytes and time')
    policy = native_stall_policy(manifest)
    if policy is None:
        raise BudgetStop('native response buffering requires the registered stall policy')
    read_bound = native_upstream_read_timeout(manifest) or LEGACY_UPSTREAM_READ_SECONDS
    if value['total_seconds'] > read_bound:
        raise BudgetStop('complete-response deadline must not exceed the registered upstream read bound')
    outer = native_api_timeout(manifest)
    if (outer is None or outer < stall_policy_minimum_api_timeout_ms(manifest, policy['count_attempts']) or
            native_api_force_idle_timeout(manifest) is not False):
        raise BudgetStop('native response buffering needs bounded SDK timeout margin and the idle timer off')
    return dict(value)


def native_api_force_idle_timeout(manifest):
    """Optional native fetch idle policy, independent of the SDK request deadline."""
    runtime = manifest['native_runtime']
    if 'api_force_idle_timeout' not in runtime:
        return None
    value = runtime['api_force_idle_timeout']
    if value is not False:
        raise BudgetStop('native API force-idle-timeout override must be explicit false')
    if native_api_timeout(manifest) is None:
        raise BudgetStop('disabling native fetch idle timeout requires a registered bounded native API timeout')
    return value


class SequenceLock:
    """Same flock namespace as FileLock, without its pre-flock truncation."""
    def __init__(self, path):
        self.path = canonical_path(str(path))
        if self.path.is_symlink():
            raise BudgetStop('sequence lock path is symlinked')
        self.descriptor = None

    def _check(self, descriptor):
        info = os.fstat(descriptor)
        current = os.stat(self.path, follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or
                (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)):
            raise BudgetStop('sequence lock is aliased, foreign or replaced')

    @property
    def is_locked(self):
        if self.descriptor is None:
            return False
        self._check(self.descriptor)
        return True

    def acquire(self, timeout=0):
        if timeout != 0 or self.descriptor is not None:
            raise BudgetStop('sequence lock requires one nonblocking acquisition')
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            self._check(descriptor)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise Timeout(str(self.path)) from error
            self._check(descriptor)
        except BaseException:
            os.close(descriptor)
            raise
        self.descriptor = descriptor
        return self

    def __enter__(self):
        return self if self.descriptor is not None else self.acquire()

    def __exit__(self, *args):
        descriptor, self.descriptor = self.descriptor, None
        if descriptor is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


@contextmanager
def sequence_guard(manifest, registration_sha):
    """Serialize descendants of the same confirmed source charge checkpoint."""
    generation, _ = parent_job(manifest)
    path = parent_path(manifest['parent'], generation['budget']['ledger_path']).with_name('audit_sequence.json')
    expected = canonical_path(manifest['sequence_state'])
    if expected != path:
        raise BudgetStop('audit sequence state is not derived from its immutable source ledger')
    claim = None
    if 'sequence_claim' in manifest:
        import sequence_claim
        claim = sequence_claim.context(manifest, Path(manifest['budget']['ledger_path']).parent / 'registration.json',
            registration_sha, path, {'registration_sha256': sha(manifest['parent']['registration']),
                'ledger_path': str(parent_path(manifest['parent'], generation['budget']['ledger_path']))}, 'audit')
    lock = SequenceLock(str(path) + '.lock')
    with lock.acquire(timeout=0):
        previous_raw = path.read_bytes() if path.exists() else None
        previous = strict_json(previous_raw) if previous_raw is not None else None
        checkpoint = manifest['budget']['continuation']
        if previous is None:
            if checkpoint['checkpoint'] != manifest['parent']['reconciled_checkpoint']:
                raise BudgetStop('first audit does not continue the confirmed source checkpoint')
        elif previous['registration_sha256'] == registration_sha:
            raise BudgetStop('audit continuation identity is already consumed')
        else:
            reconciled = validate_audit_reconciliation(manifest)
            if reconciled is None:
                if (checkpoint['checkpoint'] != previous['ledger_path'] or
                        sha(previous['ledger_path']) != checkpoint['sha256']):
                    raise BudgetStop('audit billing fork: predecessor is not the current sequence tip')
                state = read_json(previous['ledger_path'])
                from .probe_predecessor import validate_predecessor
                validate_predecessor(manifest)
            else:
                bridge = checkpoint['reconciliation']
                if (bridge['source_ledger'] != previous['ledger_path'] or
                        sha(bridge['source_registration']) != previous['registration_sha256']):
                    raise BudgetStop('audit reconciliation does not belong to the current sequence tip')
                state = reconciled
            if (state.get('manifest_sha256') != previous['registration_sha256'] or
                    previous.get('source_registration_sha256') != sha(manifest['parent']['registration'])):
                raise BudgetStop('audit predecessor identity differs from sequence tip')
            if any(row.get('status') != 'settled' for row in state['requests']):
                raise BudgetStop('audit sequence has an unresolved predecessor charge')
        value = {'schema_version': 1, 'registration_sha256': registration_sha,
                 'ledger_path': manifest['budget']['ledger_path'],
                 'parent_checkpoint_sha256': checkpoint['sha256'],
                 'source_registration_sha256': sha(manifest['parent']['registration'])}
        temporary = path.with_name(path.name + '.tmp')
        with temporary.open('x') as handle:
            json.dump(value, handle, indent=2)
            handle.write('\n')
        temporary.replace(path)
        if claim is not None:
            sequence_claim.record(claim, value, previous_raw)
        yield


def validate_reconciliation(manifest):
    """Only the explicitly confirmed source request may change its accounting."""
    parent = manifest['parent']
    generation, _ = parent_job(manifest)
    source = parent_path(parent, generation['budget']['ledger_path'])
    old = read_json(source)
    receipt = read_json(parent['reconciliation_receipt'])
    checkpoint = read_json(parent['reconciled_checkpoint'])
    digest = sha(parent['reconciliation_receipt'])
    if (receipt.get('kind') != 'user_confirmed_provider_charge_reconciliation' or
            receipt.get('source_registration_sha256') != sha(parent['registration']) or
            receipt.get('source_ledger_sha256') != sha(source) or
            receipt.get('stopped_result_sha256') != sha(parent['result']) or
            not receipt.get('user_confirmation', {}).get('exact_response') or
            not receipt.get('user_confirmation', {}).get('quoted_request') or
            checkpoint.get('manifest_sha256') != sha(parent['registration'])):
        raise BudgetStop('audit reconciliation does not bind the stopped source accounting')
    expected = strict_json(json.dumps(old))
    pending = [row for row in expected['requests'] if row.get('status') != 'settled']
    if len(pending) != 1 or pending[0].get('status') != 'pending':
        raise BudgetStop('reconciliation must resolve exactly one pending source request')
    row = pending[0]
    cost = Decimal(str(receipt['confirmed_complete_charge_usd']))
    if (row['id'] != receipt['request_id'] or row['attempt'] != receipt['attempt'] or
            row['attempt'] != attempt_identity(sha(parent['registration']), parent['job_id']) or
            row['reserved_usd'] != receipt['previous_reservation_usd'] or
            not cost.is_finite() or not Decimal(0) <= cost <= Decimal(row['reserved_usd'])):
        raise BudgetStop('confirmed request identity or charge differs from source reservation')
    row.update(status='settled', cost_usd=str(cost), settled_at=receipt['recorded_at'],
        settlement_basis='user_confirmed_provider_accounting',
        reconciliation_receipt_sha256=digest,
        provider_observation_sha256=receipt['provider_observation_sha256'],
        provider_usage_is_final=False, generation_outcome='stopped')
    expected['reconciled_from'] = {'checkpoint_sha256': sha(source), 'receipt_sha256': digest,
        'request_id': receipt['request_id'], 'previous_status': 'pending',
        'confirmed_charge_usd': str(cost), 'generation_completed': False}
    if canonical_json(checkpoint) != canonical_json(expected):
        raise BudgetStop('reconciled checkpoint changes unconfirmed source accounting')
    return checkpoint


def budget_amendment_predecessor_path(manifest, *, exists=True):
    """Locate the immediate audit, including an explicitly reconciled ledger."""
    continuation = manifest['budget']['continuation']
    checkpoint = canonical_path(continuation['checkpoint'], exists=True)
    bridge = continuation.get('reconciliation')
    if bridge is None:
        target = checkpoint.with_name('registration.json')
    else:
        if type(bridge) is not dict or set(bridge) != {'source_registration', 'source_ledger', 'receipt', 'result'}:
            raise BudgetStop('invalid audit reconciliation identity fields')
        target = canonical_path(bridge['source_registration'], exists=exists)
    return canonical_path(str(target), exists=exists)


def validate_budget_amendment_predecessor(manifest, previous, *, require_pins=True):
    """Bind the exact immediate predecessor's authority before new state writes.

    Legacy checkpoints need no new sibling registration. An existing amended
    audit predecessor cannot become an unamended successor by dropping proof.
    """
    selected = 'budget_amendment' in manifest
    source_path = budget_amendment_predecessor_path(manifest, exists=selected)
    if not selected:
        if source_path.is_file() and 'budget_amendment' in read_json(source_path):
            raise BudgetStop('audit successor drops its inherited budget amendment')
        return None
    from budget_amendment import selection
    proof = selection(manifest['budget_amendment'])
    continuation = manifest['budget']['continuation']
    checkpoint = canonical_path(continuation['checkpoint'], exists=True)
    bridge = continuation.get('reconciliation')
    if require_pins:
        pinned(manifest, str(source_path))
        pinned(manifest, str(checkpoint), continuation['sha256'])
    if sha(checkpoint) != continuation['sha256'] or canonical_json(read_json(checkpoint)) != canonical_json(previous):
        raise BudgetStop('amended audit checkpoint differs from its exact registered predecessor')
    source = read_json(source_path)
    expected_ledger = checkpoint if bridge is None else canonical_path(bridge['source_ledger'], exists=True)
    from .probe_predecessor import KIND as PROBE_KIND, validate_link
    if source.get('kind') == PROBE_KIND:
        # A probe is a link too (#2469): its checkpoint is checked through to the audit before it.
        validate_link(manifest, require_pins=require_pins)
    if (source.get('kind') not in ('d4d_native_audit_continuation', PROBE_KIND)
            or sha(source_path) != previous.get('manifest_sha256')
            or canonical_path(source['budget']['ledger_path']) != expected_ledger
            or source.get('parent', {}).get('registration') != manifest['parent']['registration']
            or Decimal(str(source['budget']['additional_usd'])) != Decimal(str(previous['additional_cap_usd']))):
        raise BudgetStop('amended audit checkpoint names another immediate predecessor or origin')
    if Decimal(str(previous['additional_cap_usd'])) == Decimal(proof['prior_total_usd']):
        reference = proof['predecessor_registration']
        if str(source_path) != reference['path'] or sha(source_path) != reference['sha256']:
            raise BudgetStop('first amended audit differs from its authorized predecessor')
    elif ('budget_amendment' not in source
            or canonical_json(selection(source['budget_amendment'])) != canonical_json(proof)):
        raise BudgetStop('audit successor changes its inherited budget amendment')
    return source_path


def open_audit_ledger(manifest, registration_path, manifest_sha256):
    budget, job = manifest['budget'], manifest['job']
    location = canonical_path(budget['ledger_path'])
    if location != Path(registration_path).parent / 'billing.json':
        raise BudgetStop('audit ledger differs from the registered condition')
    if set(budget['per_job_attempt_usd']) != {job['id']}:
        raise BudgetStop('audit cap does not bind its sole job')
    prior = budget['continuation']
    pinned(manifest, prior['checkpoint'], prior['sha256'])
    previous = read_json(prior['checkpoint'])
    validate_budget_amendment_predecessor(manifest, previous)
    bridge = {}
    if 'budget_amendment' in manifest:
        from budget_amendment import ledger_bridge
        bridge = ledger_bridge(manifest, previous, checkpoint_sha256=prior['sha256'])
    ledger = Ledger(location, manifest_sha256=manifest_sha256,
        total_cap=budget['additional_usd'], attempt_cap=budget['per_attempt_usd'],
        attempt_caps_usd={attempt_identity(manifest_sha256, job['id']): budget['per_job_attempt_usd'][job['id']]})
    ledger.continue_from(prior['checkpoint'], expected_sha256=prior['sha256'], expected_cost_usd=prior['cost_usd'], **bridge)
    return ledger


def _full_reservation_debit(receipt, row):
    """An explicit budget debit does not establish a provider charge or usage."""
    contradictory = {'confirmed_complete_charge_usd', 'confirmed_charge_usd',
                     'user_confirmation', 'provider_observation_sha256'}
    if (contradictory.intersection(receipt) or
            receipt.get('provider_charge_confirmed') is not False or
            receipt.get('provider_charge_usd', 'missing') is not None or
            receipt.get('provider_usage_is_final') is not False or
            any(receipt[key] is not False for key in ('source_attempt_completed', 'scientific_acceptance') if key in receipt)):
        raise BudgetStop('full reservation debit needs an explicitly unknown provider charge')
    for key in ('request_sha256', 'accounting_observation_sha256'):
        if not isinstance(receipt.get(key), str) or not re.fullmatch(r'[0-9a-f]{64}', receipt[key]):
            raise BudgetStop('full reservation debit lacks exact request and accounting evidence hashes')
    if receipt['request_sha256'] != row.get('request_sha256'):
        raise BudgetStop('full reservation debit names another request payload')
    if not isinstance(receipt.get('recorded_at'), str) or not receipt['recorded_at'].strip():
        raise BudgetStop('full reservation debit lacks its recorded authorization time')
    try:
        cost = Decimal(str(receipt['budget_debit_usd']))
        reservation = Decimal(str(row['reserved_usd']))
        released = Decimal(str(receipt['released_excess_reservation_usd']))
    except (InvalidOperation, ValueError, TypeError, KeyError) as error:
        raise BudgetStop('full reservation debit has invalid amounts') from error
    if (not cost.is_finite() or not reservation.is_finite() or not released.is_finite() or
            cost <= 0 or cost != reservation or released != 0):
        raise BudgetStop('budget exception must debit the full reservation without releasing any excess')
    return cost


def validate_audit_reconciliation(manifest):
    """A separately authorized copy can succeed stopped accounting without rewriting it."""
    continuation = manifest['budget']['continuation']
    bridge = continuation.get('reconciliation')
    if bridge is None:
        return None
    keys = {'source_registration', 'source_ledger', 'receipt', 'result'}
    if not isinstance(bridge, dict) or set(bridge) != keys:
        raise BudgetStop('invalid audit reconciliation identity fields')
    paths = {key: pinned(manifest, bridge[key]) for key in keys}
    checkpoint_path = pinned(manifest, continuation['checkpoint'], continuation['sha256'])
    source_reg = read_json(paths['source_registration'])
    from .probe_predecessor import KIND as PROBE_KIND, validate_link
    if source_reg.get('kind') == PROBE_KIND:
        # The probe's own debit, recomputed from its ledger and receipt (#2469).
        return validate_link(manifest)
    if source_reg.get('kind') != 'd4d_native_audit_continuation':
        raise BudgetStop('reconciled audit predecessor must be a native audit registration')
    source_sha = sha(paths['source_registration'])
    job = source_reg['job']
    if (paths['source_ledger'] != paths['source_registration'].parent / 'billing.json' or
            paths['source_ledger'] != canonical_path(source_reg['budget']['ledger_path']) or
            checkpoint_path == paths['source_ledger'] or
            Path(job['attempt_dir']) != paths['source_registration'].parent / 'attempts' / job['id'] or
            paths['result'] != Path(job['attempt_dir']) / 'result.json' or
            sha(source_reg['parent']['registration']) != sha(manifest['parent']['registration'])):
        raise BudgetStop('reconciled audit predecessor paths or generation lineage differ')
    source = read_json(paths['source_ledger'])
    result, receipt = read_json(paths['result']), read_json(paths['receipt'])
    exception = receipt.get('kind') == 'user_authorized_full_reservation_debit'
    if (source.get('manifest_sha256') != source_sha or
            result.get('registration_sha256') != source_sha or result.get('job_id') != job['id'] or
            result.get('scope') != 'phase3_audit_only' or result.get('status') != 'stopped' or
            receipt.get('kind') not in ('user_confirmed_provider_charge_reconciliation', 'user_authorized_full_reservation_debit') or
            receipt.get('source_attempt_kind') != 'phase3_audit_only' or
            receipt.get('source_registration_sha256') != source_sha or
            receipt.get('source_ledger_sha256') != sha(paths['source_ledger']) or
            receipt.get('stopped_result_sha256') != sha(paths['result'])):
        raise BudgetStop('reconciliation does not bind the stopped audit accounting')
    confirmation = receipt.get('user_authorization' if exception else 'user_confirmation', {})
    if not isinstance(confirmation, dict) or any(not isinstance(confirmation.get(key), str) or not confirmation[key].strip()
           for key in ('exact_response', 'quoted_request')):
        raise BudgetStop('audit reconciliation lacks explicit confirmation evidence')
    expected = strict_json(canonical_json(source))
    pending = [row for row in expected['requests'] if row.get('status') != 'settled']
    if len(pending) != 1 or pending[0].get('status') != 'pending':
        raise BudgetStop('audit reconciliation must resolve exactly one pending source request')
    row = pending[0]
    from .runtime_closure import require_closed_runtime
    closure_sha = require_closed_runtime(manifest, paths, source_reg, result, receipt)
    cost = (_full_reservation_debit(receipt, row) if exception
            else Decimal(str(receipt['confirmed_complete_charge_usd'])))
    if (row['id'] != receipt['request_id'] or row['attempt'] != receipt['attempt'] or
            row['attempt'] != attempt_identity(source_sha, job['id']) or
            row['reserved_usd'] != receipt['previous_reservation_usd'] or
            result.get('unresolved_requests') != [row['id']] or
            not cost.is_finite() or not Decimal(0) <= cost <= Decimal(row['reserved_usd'])):
        raise BudgetStop('audit confirmation differs from the source request or reservation')
    if exception:
        row.update(status='settled', cost_usd=str(cost), settled_at=receipt['recorded_at'],
            settlement_basis='user_authorized_full_reservation_debit',
            reconciliation_receipt_sha256=sha(paths['receipt']),
            accounting_observation_sha256=receipt['accounting_observation_sha256'],
            provider_charge_confirmed=False, provider_charge_usd=None, provider_usage_is_final=False,
            released_excess_reservation_usd='0',
            source_attempt_kind='phase3_audit_only', source_attempt_outcome='stopped')
        expected['reconciled_from'] = {'checkpoint_sha256': sha(paths['source_ledger']),
            'receipt_sha256': sha(paths['receipt']), 'request_id': receipt['request_id'],
            'previous_status': 'pending', 'budget_debit_usd': str(cost),
            'settlement_basis': 'user_authorized_full_reservation_debit',
            'provider_charge_confirmed': False, 'source_attempt_completed': False}
    else:
        row.update(status='settled', cost_usd=str(cost), settled_at=receipt['recorded_at'],
            settlement_basis='user_confirmed_provider_accounting',
            reconciliation_receipt_sha256=sha(paths['receipt']),
            provider_observation_sha256=receipt['provider_observation_sha256'], provider_usage_is_final=False,
            source_attempt_kind='phase3_audit_only', source_attempt_outcome='stopped')
        expected['reconciled_from'] = {'checkpoint_sha256': sha(paths['source_ledger']),
            'receipt_sha256': sha(paths['receipt']), 'request_id': receipt['request_id'],
            'previous_status': 'pending', 'confirmed_charge_usd': str(cost), 'source_attempt_completed': False}
    if closure_sha is not None:
        row['runtime_closure_sha256'] = closure_sha
        expected['reconciled_from']['runtime_closure_sha256'] = closure_sha
    checkpoint = read_json(checkpoint_path)
    if canonical_json(checkpoint) != canonical_json(expected):
        raise BudgetStop('reconciled audit checkpoint changes unconfirmed history')
    return checkpoint
