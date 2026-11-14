"""Invented offline owner/review records for U4b refusal tests; never authority."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess

from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard as wire


def admission_policy(directory):
    """Invented dates for offline fixtures, never defaults for registration."""
    from data_sheets_schema.native_u4b_policy import TERM_VALUES
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    return {**TERM_VALUES, 'capture_state_directory': str(directory),
            'valid_from': start.isoformat().replace('+00:00', 'Z'),
            'valid_until': (start + timedelta(days=14)).isoformat().replace('+00:00', 'Z')}


def registration_commit_for(raw, directory, *, author_date):
    """Commit exact invented registration bytes in a tiny test-only Git repo."""
    repository = Path(directory).resolve() / 'synthetic-registration-commits'
    repository.mkdir(parents=True, exist_ok=True)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/nonexistent',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1',
           'GIT_AUTHOR_NAME': 'Synthetic fixture', 'GIT_AUTHOR_EMAIL': 'fixture@invalid.example',
           'GIT_COMMITTER_NAME': 'Synthetic fixture', 'GIT_COMMITTER_EMAIL': 'fixture@invalid.example',
           'GIT_AUTHOR_DATE': author_date, 'GIT_COMMITTER_DATE': author_date}

    def git(*args):
        return subprocess.check_output(['/usr/bin/git', '-c', 'core.hooksPath=/dev/null',
            '-C', str(repository), *args], env=env, stderr=subprocess.PIPE, timeout=10)

    if not (repository / '.git').exists():
        git('init', '-b', 'synthetic-evidence')
    relative = 'registration-' + wire.sha(raw) + '.json'
    path = repository / relative
    if path.exists():
        assert path.read_bytes() == raw, 'synthetic registration evidence changed'
    else:
        path.write_bytes(raw)
        git('add', '--', relative)
        git('commit', '-m', 'Add invented registration for offline validation')
    commit = git('log', '-1', '--format=%H', '--', relative).decode().strip()
    return {'repository': str(repository), 'path': relative, 'commit': commit}


def bundle_for(registration_raw, directory, now='2026-11-08T00:00:00Z'):
    value = review.registration_fields(registration_raw)
    runtime = value['runtime']
    from data_sheets_schema.native_runtime_profiles import profile_name, SYNTHETIC_PROFILE
    synthetic = profile_name(runtime) == SYNTHETIC_PROFILE
    from data_sheets_schema.native_u4b_policy import admission_terms, registered_policy
    policy = registered_policy(runtime)
    binding = {'registration_sha256': wire.sha(registration_raw), 'attempt_id': value['attempt_id'],
        'source_commit': value['dependencies']['base']['source_commit'],
        'dependencies_sha256': wire.sha(wire.canonical(value['dependencies']))}
    terms = {'kind': review.TERMS_KIND, 'version': 1, 'owner': 'fixture owner',
        'budget_guard_usd': runtime['budget_guard_usd'], 'deadline_seconds': runtime['deadline_seconds'],
        **admission_terms(runtime),
        'overage': 'disabled', 'keep_awake': runtime['keep_awake'],
        'context_mode': SYNTHETIC_PROFILE if synthetic else '1m',
        'quota_capture': {'kind': review.CAPTURE_KIND, 'version': 3, 'count': 3,
            'directory': str(directory), 'deadline_seconds': min(30, runtime['deadline_seconds']),
            'prompt_sha256': wire.sha(review.PROMPT.encode()),
            'max_stdout_bytes': 1048576, 'max_stderr_bytes': 1048576}}
    bundle = {**binding, 'kind': review.KIND, 'version': 2, 'author': 'fixture author',
        'operator': 'fixture owner', 'owner_statement': terms,
        'registration_commit': registration_commit_for(registration_raw, directory.parent,
                                                       author_date=policy['valid_from']),
        'reviews': []}
    documents = directory.parent / 'synthetic-review-documents'
    documents.mkdir(exist_ok=True)
    for kind in ('claude', 'codex_cli'):
        body = ('Synthetic ' + kind + ' component review, not actual launch approval.\n').encode()
        path = documents / (kind + '.md')
        if path.exists():
            assert path.read_bytes() == body, 'synthetic review evidence changed'
        else:
            path.write_bytes(body)
        bundle['reviews'].append({'reviewer': 'fixture reviewer ' + kind, 'reviewer_kind': kind,
            'author': 'fixture author', 'operator': 'fixture owner', 'independent': True,
            'decision': 'approved', 'reviewed_at': now,
            'document': {'path': str(path), 'bytes': len(body), 'sha256': wire.sha(body)}})
    raw = wire.canonical(bundle)
    word = {**binding, 'kind': 'd4d_native_execution_launch_authorization_v2', 'version': 2,
        'owner': 'fixture owner', 'authorized_at': now, 'word': 'AUTHORIZE_ONE_NATIVE_ATTEMPT',
        'review_sha256': wire.sha(raw), 'ci_sha256': '1' * 64,
        'permission_probe_sha256': value['permission_probe_sha256']}
    return raw, wire.canonical(word)
