"""Exact native-shared helper commands composed with frozen ordinary lookups.

The selected composition derives this complete command table from the pinned
renderer. This adapter does not widen the historical helper argument grammar.
"""
from __future__ import annotations

import shlex
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_attribution_controller as inherited

HELPERS = frozenset(('chunk_check','source_scope','full_schema','full_terms','phase1_receipts',
    'advance','derive_core','core_schema','pair','original_source_inventory','final_source_inventory',
    'draft','audit_evidence','final_evidence','derive_final_core','final_scope','recorder'))
_HELPER_TOKEN_CACHE_ENTRIES = 32
_HELPER_TOKEN_CACHE_BYTES = 32_768


@lru_cache(maxsize=_HELPER_TOKEN_CACHE_ENTRIES)
def _cached_helper_tokens(command):
    # Immutable parse data only. Even direct private calls cannot retain a
    # larger spelling; exceptions are not cached by lru_cache.
    if type(command) is not str or len(command.encode('utf-8')) > _HELPER_TOKEN_CACHE_BYTES:
        raise ValueError('helper token cache requires a bounded exact string')
    return tuple(shlex.split(command))


def _helper_tokens(command):
    if len(command.encode('utf-8')) <= _HELPER_TOKEN_CACHE_BYTES:
        return _cached_helper_tokens(command)
    return tuple(shlex.split(command))


def command_policy(spec, instruction_path, controls=None):
    """Derive every new helper from the selected renderer, without old guards.

    The fixed inherited file controller still enforces the static envelope.
    The new observer separately restricts stage paths to the current cursor.
    No caller-supplied command or file-write allowlist is accepted here.
    """
    from . import native_shared_render as render
    from .agentic_runtime import validate_toolchain
    controls = inherited.load_controls() if controls is None else controls
    grammar = controls['native_command_policy']
    cap = spec._native_shared_generation_capture
    if type(cap) is not c.NativeSelectionCapture:
        raise ValueError('native policy requires an actual captured selection')
    environment = validate_toolchain(spec._agentic_toolchain)
    python = environment['python']
    path = c.canonical_path(str(instruction_path), 'instruction path')
    from .native_shared_evidence import read_regular
    if read_regular(path, 'instruction', max_bytes=c.HARD_LIMITS['request_bytes']).captured.raw != spec.instruction.encode('utf-8'):
        raise ValueError('selected instruction differs from the exact native request')
    commands = {}
    rendered_words = {}
    for name, argv in render.commands(spec).items():
        commands[name] = shlex.join(argv)
        # Retain only immutable words from this rendering. Other iterables
        # keep the original parse of the joined spelling, at its original use.
        if type(argv) is tuple and all(type(word) is str for word in argv):
            rendered_words[name] = (commands[name], argv)

    def tokens(name):
        saved = rendered_words.get(name)
        if saved is not None and commands[name] == saved[0]:
            # Match shlex.split's list indexing, including short-argv errors.
            return list(saved[1])
        return shlex.split(commands[name])

    c.exact(commands, HELPERS, 'source-derived native helper table')
    artifacts = spec._agentic_artifact_paths
    inputs = {a.pin.path for a in (cap.registration, cap.receipt_policy, *cap.authority,
              *(source for schema in cap.schemas for source in schema.sources),
              spec._native_shared_runtime_capture)} | {path}
    repository = str(Path.cwd().resolve())
    outputs = {str(Path(artifacts[k]).parent.resolve()) for k in ('full', 'core', 'report')}
    outputs.add(cap.role('stage_root'))
    destination = str(Path(artifacts['core']).parent / (spec.project + '_provenance.yaml'))
    if destination in inputs or destination in artifacts.values():
        raise ValueError('native recorder destination overlaps a protected artifact')
    rules = ['Read', 'Write']
    rules += [grammar._literal_rule('sed -n' if name == 'sed' else name, arguments=True)
              for name in controls['native_readonly'].PROGRAMS]
    rules += [grammar._literal_rule(text) for text in sorted(set(commands.values()))]
    programs = sorted({tokens(name)[2] for name in commands if tokens(name)[1] == '-c'})
    helper_view = {'version': controls['native_phase_history'].HELPER_ARGUMENTS,
        'repository': repository, 'python': python, 'method': spec.method, 'label': spec.label,
        'project': spec.project, 'bundle': str(spec.bundle), 'chunk_manifest': str(spec.chunk_manifest),
        'manifest': str(spec.manifest), 'manifest_used': bool(spec.manifest_used),
        'render_version': 26, 'artifact_paths': dict(artifacts), 'protocol_version': 7,
        'spellings': {name: [text] for name, text in sorted(commands.items())}}
    policy = {'version': grammar.POLICY_VERSION, 'literal_admission': grammar.LITERAL_ADMISSION,
        'pretool_control': deepcopy(controls['native_control'].HISTORY_CONTRACT), 'python': python,
        'manifest_paths': [str(spec.manifest)], 'programs': [{'code': code, 'arguments': True} for code in programs],
        'command_examples': sorted(commands[name] for name in commands if tokens(name)[1] == '-c'),
        'allowed_tools': rules, 'readonly_lookups': {'version': 1, 'repository': repository,
            'inputs': sorted(inputs), 'output_directories': sorted(outputs)},
        'lookup_literal_admission': grammar.LOOKUP_LITERAL_ADMISSION, 'helper_arguments': helper_view,
        'native_shared_generation_version': 1, 'native_shared_helpers': commands,
        'attribution_composition_version': 1, 'attribution_command': commands['draft'],
        'post_final_recorder': {'command': commands['recorder'], 'destination': destination,
            'scope': 'Only the exact selected provenance record after final evidence; no dataset/report mutation'}}
    for command in commands.values():
        if classify_bash(command, python, set(), policy, controls)[0] != 'prescribed':
            raise ValueError('source-derived native helper is not admitted by its literal policy')
    return policy


_VERIFIED_HELPER_TABLES: set[tuple[str, tuple[tuple[str, str], ...]]] = set()


def helper_commands(policy):
    if (type(policy) is not dict or type(policy.get('native_shared_generation_version')) is not int
            or policy['native_shared_generation_version'] != 1):
        raise ValueError('not the explicitly selected native shared command policy')
    commands=policy.get('native_shared_helpers')
    c.exact(commands,HELPERS,'native shared helper command table')
    python=c.canonical_path(policy.get('python'),'registered Python')
    table_key = ((python, tuple(sorted(commands.items())))
                 if all(type(v) is str for v in commands.values()) else None)
    if table_key is None or table_key not in _VERIFIED_HELPER_TABLES:
        for name,command in commands.items():
            if type(command) is not str or not command or len(command.encode('utf-8'))>1_000_000:
                raise ValueError('native helper spelling is absent or oversized')
            try:words=_helper_tokens(command)
            except ValueError as exc:raise ValueError('native helper spelling is malformed') from exc
            if (len(words)<3 or words[0]!=python or words[1] not in ('-m','-c')
                    or shlex.join(words)!=command):
                raise ValueError('native helper must retain exact selected Python argv spelling')
        if table_key is not None and len(_VERIFIED_HELPER_TABLES) < 64:
            _VERIFIED_HELPER_TABLES.add(table_key)
    if (policy.get('attribution_command')!=commands['draft']
            or policy.get('post_final_recorder',{}).get('command')!=commands['recorder']):
        raise ValueError('native helper roles disagree with draft/recorder authority')
    return dict(commands)


def classify_bash(command,python,programs,policy,controls=None):
    """Same fixed function for production callbacks and saved probe replay.

    Only exact source-derived new helper spellings bypass the old helper-path
    parser. All other commands still use the pinned old ordinary classifier.
    """
    commands=helper_commands(policy)
    if python!=policy['python'] or type(command) is not str:
        return 'not_prescribed','native command differs from selected interpreter/text'
    controls=inherited.load_controls() if controls is None else controls
    roles=sorted(name for name,text in commands.items() if command==text)
    if roles:
        problem=controls['native_command_policy'].runtime_literal_problem(command,policy)
        if problem:return 'not_prescribed',problem
        return 'prescribed','exact selected native shared helper: '+','.join(roles)
    try:words=shlex.split(command)
    except ValueError:words=[]
    if words[:1]==[python] and len(words)>2:
        if words[1]=='-m' and words[2].startswith('data_sheets_schema.'):
            return 'not_prescribed','native shared helper differs from its exact selected arguments'
        selected_programs={shlex.split(text)[2] for text in commands.values() if shlex.split(text)[1]=='-c'}
        if words[1]=='-c' and words[2] in selected_programs:
            return 'not_prescribed','native shared inline helper differs from its exact selected arguments'
    return controls['run_native_canary']._classify_command(command,python,programs,policy)


# One exact-byte digest, only during a saved trace's synchronous replay. This
# stores no parsed policy, permission result, source check or admission.
_TRACE_POLICY_DIGEST = ContextVar('native_shared_trace_policy_digest', default=None)
_TRACE_POLICY_DIGEST_BYTES = 4 * 1024 * 1024


@contextmanager
def _policy_digest_scope():
    token = _TRACE_POLICY_DIGEST.set(())
    try:
        yield
    finally:
        _TRACE_POLICY_DIGEST.reset(token)


def _stage_policy_sha(policy):
    # Canonicalize the current policy on EVERY call, including cache hits.
    # Mutation, malformed values and encoding errors cannot hide behind an
    # earlier digest. Keep the current hash implementation in the exact key.
    raw = c.canonical(policy)
    memo = _TRACE_POLICY_DIGEST.get()
    implementation, constructor = c.sha, c.hashlib.sha256
    if (memo and memo[1] is implementation and memo[2] is constructor
            and memo[0] == raw):
        return memo[3]
    digest = implementation(raw)
    if memo is not None:
        # Oversized input keeps the original behavior without retaining it.
        _TRACE_POLICY_DIGEST.set(
            (raw, implementation, constructor, digest)
            if len(raw) <= _TRACE_POLICY_DIGEST_BYTES else ())
    return digest


def stage_overlay_governs(view, *, tool_name, tool_input, policy):
    """Route exact selected helpers after the independent phase check.

    This is routing, not permission: a helper routed outside the stage
    overlay still needs the fixed command classifier. File effects retain
    the unchanged restrictive overlay and real FileAccess checks.
    """
    from . import native_shared_effects as effects
    governed = effects.governs_stage_effect(view, tool_name=tool_name, tool_input=tool_input)
    commands = helper_commands(policy)
    if (view.static_policy_sha256 != _stage_policy_sha(policy)
            or view.stage_command != commands['advance']):
        raise ValueError('stage routing policy differs from the selected view')
    if governed and tool_name == 'Bash':
        command = tool_input['command']
        if command != commands['advance'] and command in commands.values():
            return False
    return governed


def command_guidance(policy):
    """Truthful new helper guidance, without the old copy/freeze instruction."""
    commands = helper_commands(policy)
    controls = inherited.load_controls()
    return _command_guidance(commands, controls)


def _command_guidance_in_scope(policy, profile):
    """Keep exact guidance text without reopening the selected global loader."""
    from . import native_owner_profile_v1 as owner_profile
    with owner_profile._reconstruction_controls(profile) as controls:
        return _command_guidance(helper_commands(policy), controls)


def _command_guidance(commands, controls):
    return ('\n\n## Exact native shared helper spellings\n\n'
        'Use each command exactly as written, only when its selected phase permits it. '
        'The fixed advance helper alone publishes stage requests, first-response records, '
        'receipts, seals and checked assembly. Helper permission is not evidence of stage completion.\n\n'
        + '\n\n'.join('```bash\n' + commands[name] + '\n```' for name in sorted(commands))
        + controls['native_readonly'].lookup_guidance()
        + '\nRead only registered inputs, current complete stage requests, observed sealed outputs '
          'and ordinary run outputs. Write only ordinary run outputs when their phase allows, '
          'or the exact current stage response after its complete observed Read. Never write '
          'a sealed, future, stale, consumed, helper-owned or immutable input path.\n')
