"""Closed U4b review/owner terms bound by the unchanged v2 coded word.

This validates declared identities and byte bindings, not human authentication,
CI or registration reconstruction. Callers still run those independent gates.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import re
import subprocess

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
MAX_REVIEW_DOCUMENT_BYTES = 16 * 1024 * 1024


def _review_document(document):
    """Re-read the declared review, including on saved-result validation."""
    _exact(document, {'path', 'bytes', 'sha256'}, 'review document')
    _text(document['path'], 'review document path')
    if (type(document['bytes']) is not int
            or not 0 < document['bytes'] <= MAX_REVIEW_DOCUMENT_BYTES
            or type(document['sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', document['sha256']) is None):
        raise ValueError('review document requires bounded bytes and lowercase sha256')
    try:
        raw = wire.read_regular(document['path'], limit=MAX_REVIEW_DOCUMENT_BYTES)
    except (OSError, ValueError) as exc:
        raise ValueError('review document is missing or is not a stable regular file') from exc
    if len(raw) != document['bytes'] or wire.sha(raw) != document['sha256']:
        raise ValueError('review document differs from its pinned bytes')


def _git_read(repository, *arguments):
    """Read local Git objects without replacements, hooks, lazy fetch or prompts."""
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/nonexistent',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0',
           'GIT_OPTIONAL_LOCKS': '0', 'GIT_NO_REPLACE_OBJECTS': '1',
           'GIT_LITERAL_PATHSPECS': '1', 'GIT_ALLOW_PROTOCOL': ''}
    try:
        result = subprocess.run(['/usr/bin/git', '--no-replace-objects',
                                 '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
                                 '-c', 'protocol.allow=never', '-C', str(repository),
                                 *arguments], env=env, capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('registration commit local object read failed') from exc
    if result.returncode:
        raise ValueError('registration commit local object is unavailable')
    return result.stdout


def _registration_commit(evidence, registration_raw, runtime):
    """Bind N1.8 validity to the commit that adds these registration bytes.

    The commit pin belongs to the later review bundle, avoiding a registration
    self-reference. The local repository and objects must remain for readback.
    """
    _exact(evidence, {'repository', 'path', 'commit'}, 'registration commit evidence')
    _text(evidence['repository'], 'registration commit repository')
    _text(evidence['path'], 'registration commit path')
    repository = Path(evidence['repository'])
    relative = PurePosixPath(evidence['path'])
    commit = evidence['commit']
    try:
        physical = repository.resolve(strict=True)
    except OSError as exc:
        raise ValueError('registration commit repository is unavailable') from exc
    if (not repository.is_absolute() or physical != repository
            or not repository.is_dir() or str(repository) != evidence['repository']
            or relative.is_absolute() or str(relative) != evidence['path']
            or any(part in ('.', '..', '.git') for part in relative.parts)
            or '\\' in evidence['path'] or ':' in evidence['path']
            or type(commit) is not str or re.fullmatch('[0-9a-f]{40}', commit) is None):
        raise ValueError('registration commit requires an exact local repository, relative path and full SHA')
    if _git_read(repository, 'rev-parse', '--show-toplevel').decode().strip() != str(repository):
        raise ValueError('registration commit repository must be its exact Git root')
    if _git_read(repository, 'cat-file', '-t', commit).strip() != b'commit':
        raise ValueError('registration commit must name a commit object')
    size = _git_read(repository, 'cat-file', '-s', commit).strip()
    if not size.isdigit() or not 0 < int(size) <= 1024 * 1024:
        raise ValueError('registration commit object exceeds its bound')
    headers = _git_read(repository, 'cat-file', 'commit', commit).split(b'\n\n', 1)[0].splitlines()
    authors = [line for line in headers if line.startswith(b'author ')]
    parents = [line.removeprefix(b'parent ') for line in headers if line.startswith(b'parent ')]
    if len(authors) != 1 or len(parents) > 1:
        raise ValueError('registration commit requires one author and an unambiguous non-merge addition')
    author = re.fullmatch(rb'author .+ ([0-9]+) ([+-])([0-9]{2})([0-9]{2})', authors[0])
    if author is None or int(author[3]) > 23 or int(author[4]) > 59:
        raise ValueError('registration commit has a malformed author date')
    try:
        author_time = datetime.fromtimestamp(int(author[1]), timezone.utc).timestamp()
    except (OverflowError, ValueError, OSError) as exc:
        raise ValueError('registration commit author date is outside the supported range') from exc
    entry = _git_read(repository, 'ls-tree', '-z', commit, '--', str(relative))
    if entry.count(b'\x00') != 1 or b'\t' not in entry:
        raise ValueError('registration commit path must be one regular file')
    header, named_path = entry[:-1].split(b'\t', 1)
    fields = header.split(b' ')
    if (len(fields) != 3 or fields[0] not in (b'100644', b'100755')
            or fields[1] != b'blob' or re.fullmatch(rb'[0-9a-f]{40}', fields[2]) is None
            or named_path != str(relative).encode()):
        raise ValueError('registration commit path must be one regular file')
    blob = fields[2].decode()
    if _git_read(repository, 'cat-file', '-s', blob).strip() != str(len(registration_raw)).encode():
        raise ValueError('registration commit does not contain these registration bytes')
    if _git_read(repository, 'cat-file', 'blob', blob) != registration_raw:
        raise ValueError('registration commit does not contain these registration bytes')
    for parent in parents:
        if re.fullmatch(rb'[0-9a-f]{40}', parent) is None:
            raise ValueError('registration commit has a malformed parent')
        # ls-tree succeeds with no rows only when this path was absent; an
        # unavailable parent is an error, not proof of a newly added file.
        if _git_read(repository, 'ls-tree', '-z', parent.decode(), '--', str(relative)):
            raise ValueError('registration commit must add the reviewed registration path')
    from .native_u4b_policy import registered_policy, timestamp
    policy = registered_policy(runtime)
    if timestamp(policy['valid_from'], 'valid_from') != author_time:
        raise ValueError('registered validity must start at the registration commit author date')


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
    if (type(deadline) is not int or deadline != 21600
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
    if (awake['policy'] != 'macos_iokit_ims_v1' or awake['host_platform'] != 'darwin'
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
                                 'owner_statement', 'registration_commit'}, 'review bundle')
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
    seen, kinds = set(), set()
    for review in reviews:
        _exact(review, {'reviewer', 'reviewer_kind', 'author', 'operator', 'independent', 'decision',
                        'reviewed_at', 'document'}, 'independent review')
        for key in ('reviewer', 'author', 'operator'):
            _text(review[key], 'review ' + key)
        if (review['author'] != bundle['author'] or review['operator'] != bundle['operator']
                or review['independent'] is not True or review['decision'] != 'approved'):
            raise ValueError('review independence, roles or decision differs')
        identity = review['reviewer'].casefold()
        if identity in excluded or identity in seen:
            raise ValueError('reviewers must differ from author, operator and each other')
        seen.add(identity)
        if (type(review['reviewer_kind']) is not str
                or review['reviewer_kind'] not in ('claude', 'codex_cli')
                or review['reviewer_kind'] in kinds):
            raise ValueError('reviews require exactly one claude and one codex_cli reviewer_kind')
        kinds.add(review['reviewer_kind'])
        if _timestamp(review['reviewed_at'], 'review reviewed_at') > authorized_at:
            raise ValueError('owner word precedes an independent review')
        _review_document(review['document'])
    statement = validate_terms(bundle['owner_statement'], runtime, word_owner=word['owner'])
    _registration_commit(bundle['registration_commit'], registration_raw, runtime)
    capture = Path(statement['quota_capture']['directory'])
    for key in ('attempt_directory', 'evidence_directory'):
        if key in value:
            other = Path(value[key]).resolve()
            from .native_path_identity import overlaps
            if overlaps(capture, other):
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
