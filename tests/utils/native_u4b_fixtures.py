"""Invented offline owner/review records for U4b refusal tests; never authority."""
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard as wire


def admission_policy(directory):
    """Invented dates for offline fixtures, never defaults for registration."""
    from data_sheets_schema.native_u4b_policy import TERM_VALUES
    return {**TERM_VALUES, 'capture_state_directory': str(directory),
            'valid_from': '2026-01-01T00:00:00Z', 'valid_until': '2030-01-01T00:00:00Z'}


def bundle_for(registration_raw, directory, now='2026-11-08T00:00:00Z'):
    value = review.registration_fields(registration_raw)
    runtime = value['runtime']
    from data_sheets_schema.native_u4b_policy import admission_terms
    binding = {'registration_sha256': wire.sha(registration_raw), 'attempt_id': value['attempt_id'],
        'source_commit': value['dependencies']['base']['source_commit'],
        'dependencies_sha256': wire.sha(wire.canonical(value['dependencies']))}
    terms = {'kind': review.TERMS_KIND, 'version': 1, 'owner': 'fixture owner',
        'budget_guard_usd': '90', 'deadline_seconds': runtime['deadline_seconds'],
        **admission_terms(runtime),
        'overage': 'disabled', 'keep_awake': runtime['keep_awake'], 'context_mode': '1m',
        'quota_capture': {'kind': review.CAPTURE_KIND, 'version': 3, 'count': 3,
            'directory': str(directory), 'deadline_seconds': min(30, runtime['deadline_seconds']),
            'prompt_sha256': wire.sha(review.PROMPT.encode()),
            'max_stdout_bytes': 1048576, 'max_stderr_bytes': 1048576}}
    bundle = {**binding, 'kind': review.KIND, 'version': 2, 'author': 'fixture author',
        'operator': 'fixture owner', 'owner_statement': terms,
        'reviews': [{'reviewer': name, 'author': 'fixture author', 'operator': 'fixture owner',
            'independent': True, 'decision': 'approved', 'reviewed_at': now,
            'evidence': 'Synthetic component review, not actual launch approval.'}
            for name in ('fixture reviewer one', 'fixture reviewer two')]}
    raw = wire.canonical(bundle)
    word = {**binding, 'kind': 'd4d_native_execution_launch_authorization_v2', 'version': 2,
        'owner': 'fixture owner', 'authorized_at': now, 'word': 'AUTHORIZE_ONE_NATIVE_ATTEMPT',
        'review_sha256': wire.sha(raw), 'ci_sha256': '1' * 64,
        'permission_probe_sha256': value['permission_probe_sha256']}
    return raw, wire.canonical(word)
