"""Neutral fixed completion checks, copied from the released native gates.

U3-D r8, 2026-11-07; source commit 9687dea189faa92cba1b30bdb0c6ee2f476ec747.
Only already-bound command maps and captured values are accepted. This module
does not load authority, reconstruct a launch, or import frozen execution code.
Parity with the unedited originals is tested independently.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import shlex

GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution', 'saved_attribution',
         'phase_history', 'tool_history', 'schema', 'pair', 'receipts', 'evidence',
         'observation', 'accounting', 'runtime_authority', 'keep_awake')
RUNTIME_OBSERVATION_BASIS = 'captured_runtime_observation_v1'
CLEANUP_BASIS = 'captured_native_cleanup_v1'
IOKIT_ASSERTIONS = ('PreventUserIdleSystemSleep', 'PreventDiskIdle', 'PreventSystemSleep')
DRAFT_MODULE = 'data_sheets_schema.source_attribution_preflight'

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f'duplicate JSON key: {key}')
            out[key] = value
        return out
    def invalid(value):
        raise ValueError(f'nonfinite JSON number: {value}')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def command_kind(command, spec, *, expected):
    """The extra adapter admits only exact bound helper spellings.

    RunSpec boundary: validated-caller

    RunSpec precondition: The caller supplies the unchanged spec from verified
    registration/state and the matching expected command set; this command classifier is not
    an execution entry.
    """
    if not isinstance(command, str):
        raise ValueError('helper command must be text')
    if type(expected) is not dict:
        raise ValueError('helper command map must be explicit')
    if command in expected:
        return expected[command]
    try:
        words = shlex.split(command)
    except ValueError as exc:
        raise ValueError('malformed helper command') from exc
    if any(module in words for module in (DRAFT_MODULE, 'data_sheets_schema.evidence_assertions',
                                         'data_sheets_schema.source_review')):
        raise ValueError('helper command differs from the registered exact arguments')
    return None  # other commands are outside this adapter's permission scope


def tool_history(prepared):
    """Require settled, typed helper results while allowing usable corrections.

    The composed saved checker owns admission, lifecycle, mutation epochs and
    the exact preflight result. This additional check preserves explicit Bash
    result metadata; it does not replace that check or require a fixed recipe.
    """
    spec = prepared['state'].spec
    calls, pending, checks = {}, {}, []
    initialized = terminal = False
    for event in prepared['events']:
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            if initialized or terminal or calls:
                raise ValueError('native initialization is out of order')
            initialized = True
        if event.get('type') == 'result':
            if not initialized or terminal or pending:
                raise ValueError('native terminal precedes settled tool history')
            terminal = True
        content = event.get('message', {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get('type') not in ('tool_use', 'tool_result'):
                continue
            if not initialized or terminal:
                raise ValueError('native tool history lies outside initialization and terminal')
            if block['type'] == 'tool_use':
                identity = block.get('id')
                if event.get('type') != 'assistant' or not isinstance(identity, str) or not identity or identity in calls:
                    raise ValueError('native call lacks a unique assistant identity')
                calls[identity] = block
                pending[identity] = block
                continue
            identity = block.get('tool_use_id')
            if event.get('type') != 'user' or identity not in pending:
                raise ValueError('native result lacks a unique pending call')
            call = pending.pop(identity)
            if call.get('name') != 'Bash':
                continue
            metadata = event.get('tool_use_result')
            if not isinstance(metadata, dict):
                raise ValueError('native Bash result lacks explicit exit metadata')
            codes = [metadata[k] for k in ('exitCode', 'exit_code') if k in metadata]
            if not codes or any(type(code) is not int or code != codes[0] for code in codes):
                raise ValueError('native Bash exit aliases are missing, untyped or contradictory')
            if (type(block.get('is_error')) is not bool or block['is_error'] is not bool(codes[0])
                    or any(metadata.get(k) for k in ('interrupted', 'backgroundTaskId', 'background_task_id'))):
                raise ValueError('native Bash result is contradictory, interrupted or pending')
            command = call.get('input', {}).get('command')
            kind = command_kind(command, spec, expected=prepared['state'].commands)
            if kind == 'draft' and codes[0] not in (0, 1):
                raise ValueError('draft checker returned an unusable result')
            if kind in ('evidence', 'final_evidence', 'source_inventory') and codes[0] != 0:
                raise ValueError('terminal evidence or source inventory failed')
            if 'stdout' in metadata:
                content = block.get('content')
                if not isinstance(content, str) or type(metadata['stdout']) is not str:
                    raise ValueError('native Bash stdout/content is not explicit text')
                if kind == 'draft':
                    if _encoded(_json(content)) != _encoded(_json(metadata['stdout'])):
                        raise ValueError('draft stdout and tool content disagree')
                elif content != metadata['stdout']:
                    raise ValueError('native Bash stdout and tool content disagree')
            checks.append({'tool_use_id': identity, 'helper_kind': kind, 'exit_code': codes[0]})
    if not initialized or not terminal or pending:
        raise ValueError('native history is incomplete')
    return {'passed': True, 'bash_results': checks,
            'scope': 'Typed settled native results, including usable exit-one draft corrections; no fixed recipe.'}


def runtime_observation_result(raw, admitted, selected_identity):
    """Bind approval to the exact admitted bytes, including failed drift evidence."""
    if (type(raw) is not bytes or type(admitted) is not dict
            or type(admitted.get('checked')) is not bool or type(admitted.get('passed')) is not bool
            or type(selected_identity) is not dict
            or set(selected_identity) != {'binary', 'version', 'auth', 'environment_sha256'}):
        raise ValueError('runtime observation lacks explicit captured bytes and typed admission')
    expected_raw = _encoded(admitted)
    matches = raw == expected_raw
    identity_matches = _encoded({key: admitted.get(key) for key in selected_identity}) == _encoded(selected_identity)
    return {'checked': True, 'passed': admitted['checked'] and admitted['passed'] and matches and identity_matches,
            'basis': RUNTIME_OBSERVATION_BASIS, 'admitted_observation': deepcopy(admitted),
            'admitted_sha256': _sha(expected_raw), 'captured_sha256': _sha(raw),
            'matches_admitted': matches, 'selected_runtime_identity': deepcopy(selected_identity),
            'matches_selected_identity': identity_matches}


def _released_assertions(observed, registered_policy):
    acquisition, releases = observed.get('acquisition'), observed.get('releases')
    if (type(acquisition) is not dict or acquisition.get('policy') != registered_policy['policy']
            or set(acquisition) != {'policy', 'pid', 'acquired_at', 'status', 'assertions', 'limitations', 'cleanup_receipt'}
            or acquisition.get('status') != 'acquired'
            or type(acquisition.get('pid')) is not int or acquisition['pid'] <= 0
            or type(acquisition.get('acquired_at')) is not str or not acquisition['acquired_at'].strip()
            or type(observed.get('released_at')) is not str or not observed['released_at'].strip()):
        return False
    assertions = acquisition.get('assertions')
    if (type(assertions) is not list or len(assertions) != len(IOKIT_ASSERTIONS)
            or any(type(row) is not dict or set(row) != {'type', 'id'}
                or type(row['id']) is not int or not 0 < row['id'] < 2**32 for row in assertions)
            or tuple(row['type'] for row in assertions) != IOKIT_ASSERTIONS
            or len({row['id'] for row in assertions}) != len(assertions)):
        return False
    if (type(releases) is not list or len(releases) != len(assertions)
            or any(type(row) is not dict or set(row) != {'type', 'id', 'return_code'}
                or type(row['id']) is not int or type(row['return_code']) is not int
                or row['return_code'] != 0 for row in releases)):
        return False
    return [(row['type'], row['id']) for row in releases] == [
        (row['type'], row['id']) for row in reversed(assertions)]


def cleanup_result(raw, observed, registered_policy):
    """Bind actual cleanup bytes, release outcome and the selected policy."""
    if (type(raw) is not bytes or type(observed) is not dict
            or type(observed.get('passed')) is not bool or type(registered_policy) is not dict):
        raise ValueError('cleanup lacks captured bytes, a typed outcome or selected policy')
    expected_raw = _encoded(observed)
    matches = raw == expected_raw
    policy_matches = _encoded(observed.get('policy')) == _encoded(registered_policy)
    releases = observed.get('releases', [])
    if registered_policy.get('policy') == 'not_applicable':
        outcome_matches = (observed.get('state') == 'explicitly_not_applicable' and releases == []
            and 'acquisition' not in observed and 'released_at' not in observed)
    else:
        outcome_matches = (registered_policy.get('policy') == 'macos_iokit_ims_v1'
            and observed.get('state') == 'released' and _released_assertions(observed, registered_policy))
    return {'checked': True, 'passed': observed['passed'] and matches and policy_matches and outcome_matches,
            'basis': CLEANUP_BASIS, 'observed_cleanup': deepcopy(observed),
            'registered_policy': deepcopy(registered_policy), 'policy_matches': policy_matches,
            'outcome_matches': outcome_matches, 'matches_observed': matches,
            'observed_sha256': _sha(expected_raw), 'captured_sha256': _sha(raw)}


