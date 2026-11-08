"""Closed U4b review/owner terms bound by the unchanged v2 coded word.

This validates declared identities and byte bindings, not human authentication,
CI or registration reconstruction. Callers still run those independent gates.
"""
from __future__ import annotations

from pathlib import Path

from . import native_subscription_guard as wire

KIND = 'd4d_native_execution_review_bundle_v2'
TERMS_KIND = 'd4d_native_owner_launch_terms_v1'
CAPTURE_KIND = 'd4d_native_subscription_capture_request_v3'
PREVIOUS_CAPTURE_KIND = 'd4d_native_subscription_capture_request_v2'
LEGACY_CAPTURE_KIND = 'd4d_native_subscription_capture_request_v1'
PROMPT = 'Reply with OK.'
BINDING_KEYS = {'registration_sha256', 'attempt_id', 'source_commit', 'dependencies_sha256'}
WORD_KEYS = BINDING_KEYS | {'kind', 'version', 'owner', 'authorized_at', 'word',
                          'review_sha256', 'ci_sha256', 'permission_probe_sha256'}
TERMS_KEYS = {'kind', 'version', 'owner', 'budget_guard_usd', 'deadline_seconds',
              'max_starting_weekly_utilization', 'max_starting_five_hour_utilization',
              'max_age_seconds', 'pre_reservation_margin_seconds', 'overage',
              'keep_awake', 'context_mode', 'quota_capture'}


def _exact(value, keys, label):
    if type(value) is not dict or set(value) != keys:
        raise ValueError(label + ' has missing or unknown fields')


def _text(value, label, limit=4096):
    if (type(value) is not str or not value or value != value.strip()
            or len(value) > limit or any(x in value for x in ('\0', '\r', '\n'))):
        raise ValueError(label + ' requires bounded explicit text')


def _version(value, kind, version):
    if value['kind'] != kind or type(value['version']) is not int or value['version'] != version:
        raise ValueError('unknown native authorization kind/version')


def validate_terms(statement, runtime, *, word_owner):
    """Validate exact declared terms; raw bundle/word joining is separate."""
    _exact(statement, TERMS_KEYS, 'owner launch terms')
    _version(statement, TERMS_KIND, 1)
    _text(statement['owner'], 'owner')
    if statement['owner'] != word_owner:
        raise ValueError('owner statement differs from coded word owner')
    if statement['budget_guard_usd'] != '90' or runtime.get('budget_guard_usd') != '90':
        raise ValueError('owner/runtime budget must equal the D110 string 90')
    deadline = statement['deadline_seconds']
    if (type(deadline) is not int or not 1 <= deadline <= 86400
            or type(runtime.get('deadline_seconds')) is not int
            or runtime['deadline_seconds'] != deadline):
        raise ValueError('owner/runtime deadline differs')
    from .native_u4b_policy import admission_terms
    admission = admission_terms(runtime)
    for key in ('max_starting_weekly_utilization', 'max_starting_five_hour_utilization'):
        wire._fraction(statement[key], 'owner ' + key)
        if statement[key] != admission[key]:
            raise ValueError('owner/runtime subscription admission differs: ' + key)
    for key in ('max_age_seconds', 'pre_reservation_margin_seconds'):
        if type(statement[key]) is not int or statement[key] != admission[key]:
            raise ValueError('owner/runtime subscription admission differs: ' + key)
    if statement['overage'] != 'disabled':
        raise ValueError('owner must explicitly disable overage')
    awake = statement['keep_awake']
    _exact(awake, {'policy', 'host_platform', 'basis'}, 'owner keep-awake')
    for key in awake:
        _text(awake[key], 'keep-awake ' + key)
    if (awake['policy'] not in ('macos_iokit_ims_v1', 'not_applicable')
            or (awake['policy'] == 'macos_iokit_ims_v1' and awake['host_platform'] != 'darwin')
            or wire.canonical(awake) != wire.canonical(runtime.get('keep_awake'))):
        raise ValueError('owner/runtime keep-awake policy differs')
    if (statement['context_mode'] != '1m'
            or runtime.get('environment', {}).get('CLAUDE_CODE_DISABLE_1M_CONTEXT') != '0'
            or runtime.get('model') != 'claude-opus-5[1m]'):
        raise ValueError('owner/runtime context mode differs from D112')
    request = statement['quota_capture']
    _exact(request, {'kind', 'version', 'count', 'directory', 'deadline_seconds',
                    'prompt_sha256', 'max_stdout_bytes', 'max_stderr_bytes'}, 'quota capture request')
    # Historical one-shot and three-slot evidence retains its explicit version;
    # only the current producer determines whether it can authorize a new capture.
    if type(request['version']) is not int or (
            request['kind'], request['version']) not in (
                (LEGACY_CAPTURE_KIND, 1), (PREVIOUS_CAPTURE_KIND, 2), (CAPTURE_KIND, 3)):
        raise ValueError('unknown quota capture request kind/version')
    count = 1 if request['version'] == 1 else 3
    if type(request['count']) is not int or request['count'] != count:
        raise ValueError('word-bound statement differs from its closed capture allowance')
    if (type(request['deadline_seconds']) is not int
            or not 1 <= request['deadline_seconds'] <= min(60, deadline)):
        raise ValueError('quota capture deadline must be explicit and bounded')
    if request['prompt_sha256'] != wire.sha(PROMPT.encode()):
        raise ValueError('quota capture prompt differs from the fixed trivial prompt')
    for key in ('max_stdout_bytes', 'max_stderr_bytes'):
        if type(request[key]) is not int or request[key] != 1048576:
            raise ValueError('quota capture output bounds differ')
    _text(request['directory'], 'quota capture directory')
    directory = Path(request['directory'])
    if (not directory.is_absolute() or str(directory) != request['directory']
            or directory != directory.resolve()):
        raise ValueError('quota capture directory must be canonical and absolute')
    if request['version'] == 3:
        from .native_u4b_policy import registered_policy
        if request['directory'] != registered_policy(runtime)['capture_state_directory']:
            raise ValueError('quota capture directory differs from registered capture state directory')
    return wire.strict_json(wire.canonical(statement))


def validate_bundle(registration_raw, review_bundle_raw, launch_word_raw):
    """Join two independent declared reviews and terms to unchanged word bytes.

    Does not reconstruct a registration or validate the separately bound CI.
    Every production caller must perform its complete admission chain too.
    """
    value = registration_fields(registration_raw)
    bundle = wire.strict_json(review_bundle_raw)
    word = wire.strict_json(launch_word_raw)
    try:
        binding = {'registration_sha256': wire.sha(registration_raw), 'attempt_id': value['attempt_id'],
                   'source_commit': value['dependencies']['base']['source_commit'],
                   'dependencies_sha256': wire.sha(wire.canonical(value['dependencies']))}
        runtime = value['runtime']
    except (KeyError, TypeError) as exc:
        raise ValueError('review bundle requires a bound execution registration') from exc
    _exact(word, WORD_KEYS, 'coded word')
    _version(word, 'd4d_native_execution_launch_authorization_v2', 2)
    if word['word'] != 'AUTHORIZE_ONE_NATIVE_ATTEMPT':
        raise ValueError('coded word must authorize exactly one native attempt')
    _text(word['owner'], 'coded word owner')
    from .native_subscription_guard_v2 import _timestamp
    authorized_at = _timestamp(word['authorized_at'], 'coded word authorized_at')
    if (any(word[key] != expected for key, expected in binding.items())
            or word['review_sha256'] != wire.sha(review_bundle_raw)
            or word['permission_probe_sha256'] != value.get('permission_probe_sha256')):
        raise ValueError('coded word differs from exact review/registration/probe bytes')
    if (type(word['ci_sha256']) is not str or len(word['ci_sha256']) != 64
            or any(ch not in '0123456789abcdef' for ch in word['ci_sha256'])):
        raise ValueError('coded word requires its separately validated CI digest')
    _exact(bundle, BINDING_KEYS | {'kind', 'version', 'author', 'operator', 'reviews',
                                 'owner_statement'}, 'review bundle')
    _version(bundle, KIND, 2)
    if any(bundle[key] != expected for key, expected in binding.items()):
        raise ValueError('review bundle differs from exact registration/source')
    for key in ('author', 'operator'):
        _text(bundle[key], 'bundle ' + key)
    if bundle['operator'] != word['owner']:
        raise ValueError('D107 requires the owner to be the declared operator')
    reviews = bundle['reviews']
    if type(reviews) is not list or len(reviews) != 2:
        raise ValueError('bundle requires exactly two independent reviews')
    excluded = {bundle['author'].casefold(), bundle['operator'].casefold()}
    seen = set()
    for review in reviews:
        _exact(review, {'reviewer', 'author', 'operator', 'independent', 'decision',
                        'reviewed_at', 'evidence'}, 'independent review')
        for key in ('reviewer', 'author', 'operator', 'reviewed_at', 'evidence'):
            _text(review[key], 'review ' + key)
        if (review['author'] != bundle['author'] or review['operator'] != bundle['operator']
                or review['independent'] is not True or review['decision'] != 'approved'):
            raise ValueError('review independence, roles or decision differs')
        identity = review['reviewer'].casefold()
        if identity in excluded or identity in seen:
            raise ValueError('reviewers must differ from author, operator and each other')
        seen.add(identity)
        if wire._timestamp(review['reviewed_at']) > authorized_at:
            raise ValueError('owner word precedes an independent review')
    statement = validate_terms(bundle['owner_statement'], runtime, word_owner=word['owner'])
    capture = Path(statement['quota_capture']['directory'])
    for key in ('attempt_directory', 'evidence_directory'):
        if key in value:
            other = Path(value[key]).resolve()
            if capture == other or capture in other.parents or other in capture.parents:
                raise ValueError('quota capture must be separate from attempt/evidence directories')
    return statement


def registration_fields(raw):
    """Read binding fields from the outer wire; NOT full body verification."""
    outer = wire.strict_json(raw)
    _exact(outer, {'authority_version', 'controller_sources_sha256', 'registration'},
           'v2 registration envelope')
    if (type(outer['authority_version']) is not int or outer['authority_version'] != 2
            or type(outer['controller_sources_sha256']) is not str
            or len(outer['controller_sources_sha256']) != 64
            or any(ch not in '0123456789abcdef' for ch in outer['controller_sources_sha256'])
            or type(outer['registration']) is not dict):
        raise ValueError('review requires a v2 registration envelope')
    return outer['registration']
