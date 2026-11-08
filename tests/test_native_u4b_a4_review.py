"""A4 review bytes, reviewer kinds and N1.8 pins; no execution or provider.

The parser fixture contains deliberately incomplete execution-registration
fields, but document reads, local Git objects and policy validators are real.
These cases do not claim full-chain registration or real launch acceptance.
"""
from copy import deepcopy
from pathlib import Path
import subprocess

import pytest

from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard as wire
from data_sheets_schema import native_u4b_policy as policy
from tests.test_native_launch_review import evidence
from tests.utils.native_u4b_fixtures import bundle_for, registration_commit_for


def changed_bundle(evidence, mutate):
    raw, bundle_raw, word_raw = evidence
    bundle, word = wire.strict_json(bundle_raw), wire.strict_json(word_raw)
    mutate(bundle)
    bundle_raw = wire.canonical(bundle)
    word['review_sha256'] = wire.sha(bundle_raw)
    return raw, bundle_raw, wire.canonical(word)


def test_real_documents_and_registration_commit_rechecked_on_each_validation(evidence):
    raw, bundle_raw, word_raw = evidence
    body = wire.strict_json(bundle_raw)
    assert {row['reviewer_kind'] for row in body['reviews']} == {'claude', 'codex_cli'}
    assert review.validate_bundle(raw, bundle_raw, word_raw)['deadline_seconds'] == 21600
    assert review.validate_bundle(raw, bundle_raw, word_raw)['deadline_seconds'] == 21600
    # The immutable bundle and coded word have not changed; the external
    # document did. A subsequent saved-readback validator must re-read it.
    document = Path(body['reviews'][1]['document']['path'])
    original = document.read_bytes()
    document.write_bytes(original.replace(b'Synthetic', b'Changed!!'))
    assert len(document.read_bytes()) == len(original)
    with pytest.raises(ValueError, match='review document differs'):
        review.validate_bundle(raw, bundle_raw, word_raw)


@pytest.mark.parametrize('kind', ['claude', 'codex', 'codex-cli', 'Claude', '', None, True, [], {}])
def test_exact_two_distinct_review_kinds(evidence, kind):
    values = changed_bundle(evidence, lambda body: body['reviews'][1].update(reviewer_kind=kind))
    with pytest.raises(ValueError, match='reviewer_kind'):
        review.validate_bundle(*values)


@pytest.mark.parametrize('field,value', [
    ('bytes', True), ('bytes', 0), ('bytes', -1), ('bytes', 16 * 1024 * 1024 + 1),
    ('sha256', 'f' * 64), ('sha256', 'A' * 64), ('sha256', None),
    ('path', 'relative.md'), ('extra', 'unknown'),
])
def test_pinned_document_mutations_fail_even_with_rehashed_word(evidence, field, value):
    values = changed_bundle(evidence, lambda body: body['reviews'][0]['document'].update({field: value}))
    with pytest.raises(ValueError):
        review.validate_bundle(*values)


@pytest.mark.parametrize('mutation', ['missing', 'directory', 'symlink', 'old_text_only'])
def test_missing_or_unsupported_document_refuses(evidence, mutation):
    original = wire.strict_json(evidence[1])['reviews'][0]['document']
    path = Path(original['path'])
    if mutation == 'missing':
        path.unlink()
        values = evidence
    elif mutation == 'directory':
        values = changed_bundle(evidence, lambda body: body['reviews'][0]['document'].update(path=str(path.parent)))
    elif mutation == 'symlink':
        alias = path.with_name('review-alias.md')
        alias.symlink_to(path)
        values = changed_bundle(evidence, lambda body: body['reviews'][0]['document'].update(path=str(alias)))
    else:
        def old(body):
            body['reviews'][0].pop('document')
            body['reviews'][0]['evidence'] = 'Claims approval without review bytes'
        values = changed_bundle(evidence, old)
    with pytest.raises(ValueError):
        review.validate_bundle(*values)


@pytest.mark.parametrize('stamp', ['2026-11-08', '2026-11-08 00:00:00Z',
    '2026-11-08T00:00:00', '2026-11-08T00:00:00+00:00', '2026-11-08T00:00:00+01:00',
    '2026-11-08T00:00:00z', '2026-11-08T00:00:00.1234567Z',
    '2026-11-08T00:00:60Z', '2026-02-30T00:00:00Z', True, None])
def test_reviewed_at_uses_strict_utc_grammar(evidence, stamp):
    values = changed_bundle(evidence, lambda body: body['reviews'][0].update(reviewed_at=stamp))
    with pytest.raises(ValueError, match='review reviewed_at'):
        review.validate_bundle(*values)


def test_reviewed_at_fraction_and_order(evidence):
    raw, bundle_raw, word_raw = changed_bundle(evidence,
        lambda body: body['reviews'][0].update(reviewed_at='2026-11-08T00:00:00.000001Z'))
    word = wire.strict_json(word_raw)
    with pytest.raises(ValueError, match='precedes'):
        review.validate_bundle(raw, bundle_raw, word_raw)
    word['authorized_at'] = '2026-11-08T00:00:00.000001Z'
    assert review.validate_bundle(raw, bundle_raw, wire.canonical(word))


@pytest.mark.parametrize('deadline', [True, 0, 60, 900, 21599, 21601, 86400, 21600.0])
def test_n1_deadline_is_not_merely_owner_equality(evidence, deadline):
    runtime = deepcopy(review.registration_fields(evidence[0])['runtime'])
    runtime['deadline_seconds'] = deadline
    terms = wire.strict_json(evidence[1])['owner_statement']
    terms['deadline_seconds'] = deadline
    with pytest.raises(ValueError, match='deadline'):
        review.validate_terms(terms, runtime, word_owner=terms['owner'])
    with pytest.raises(ValueError, match='21600'):
        policy.registered_policy(runtime)


@pytest.mark.parametrize('awake', [
    {'policy': 'not_applicable', 'host_platform': 'darwin', 'basis': 'invented exemption'},
    {'policy': 'macos_iokit_ims_v1', 'host_platform': 'linux', 'basis': 'invented host'},
    {'policy': 'caffeinate', 'host_platform': 'darwin', 'basis': 'legacy alternative'},
])
def test_n1_keep_awake_is_required_even_when_owner_matches(evidence, awake):
    runtime = deepcopy(review.registration_fields(evidence[0])['runtime'])
    runtime['keep_awake'] = awake
    terms = wire.strict_json(evidence[1])['owner_statement']
    terms['keep_awake'] = awake
    with pytest.raises(ValueError, match='keep-awake'):
        review.validate_terms(terms, runtime, word_owner=terms['owner'])
    with pytest.raises(ValueError, match='keep-awake'):
        policy.registered_policy(runtime)


@pytest.mark.parametrize('end', ['2026-11-07T00:00:00Z', '2026-11-08T00:00:00Z',
    '2026-11-09T00:00:00Z', '2026-11-21T23:59:59Z', '2026-11-22T00:00:01Z',
    '2030-01-01T00:00:00Z'])
def test_n1_validity_requires_exact_fourteen_days(evidence, end):
    runtime = review.registration_fields(evidence[0])['runtime']
    admission = wire.strict_json(runtime['limits_basis'].encode())['admission']
    admission['valid_until'] = end
    with pytest.raises(ValueError, match='fourteen days'):
        policy.validate_policy(admission)


@pytest.mark.parametrize('mutation', ['missing', 'wrong_blob', 'wrong_author', 'unknown_field',
                                     'short_commit', 'relative_repository', 'parent_path'])
def test_registration_commit_anchor_refusals(evidence, tmp_path, mutation):
    raw = evidence[0]
    def alter(body):
        anchor = body['registration_commit']
        if mutation == 'missing':
            body.pop('registration_commit')
        elif mutation == 'wrong_blob':
            body['registration_commit'] = registration_commit_for(b'other bytes\n', tmp_path / 'wrong-blob',
                                                                  author_date='2026-11-08T00:00:00Z')
        elif mutation == 'wrong_author':
            body['registration_commit'] = registration_commit_for(raw, tmp_path / 'wrong-author',
                                                                  author_date='2026-11-07T00:00:00Z')
        elif mutation == 'unknown_field': anchor['author_date'] = '2026-11-08T00:00:00Z'
        elif mutation == 'short_commit': anchor['commit'] = anchor['commit'][:9]
        elif mutation == 'relative_repository': anchor['repository'] = 'relative'
        elif mutation == 'parent_path': anchor['path'] = '../registration.json'
    with pytest.raises(ValueError):
        review.validate_bundle(*changed_bundle(evidence, alter))


def test_registered_commit_must_add_path_not_restate_unchanged_blob(evidence):
    body = wire.strict_json(evidence[1])
    anchor = body['registration_commit']
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_NAME': 'Synthetic fixture',
           'GIT_AUTHOR_EMAIL': 'fixture@invalid.example', 'GIT_COMMITTER_NAME': 'Synthetic fixture',
           'GIT_COMMITTER_EMAIL': 'fixture@invalid.example',
           'GIT_AUTHOR_DATE': '2026-11-08T00:00:00Z', 'GIT_COMMITTER_DATE': '2026-11-08T00:00:00Z'}
    subprocess.run(['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-C', anchor['repository'],
        'commit', '--allow-empty', '-m', 'Synthetic later commit does not add registration'],
        env=env, check=True, capture_output=True, timeout=10)
    new_head = subprocess.check_output(['/usr/bin/git', '-C', anchor['repository'],
        'rev-parse', 'HEAD'], env=env, timeout=10).decode().strip()
    values = changed_bundle(evidence, lambda value: value['registration_commit'].update(commit=new_head))
    with pytest.raises(ValueError, match='must add'):
        review.validate_bundle(*values)


def test_registration_anchor_reads_objects_not_mutable_worktree_file(evidence):
    body = wire.strict_json(evidence[1])
    anchor = body['registration_commit']
    path = Path(anchor['repository']) / anchor['path']
    path.write_bytes(b'uncommitted and not used as the registration anchor\n')
    assert review.validate_bundle(*evidence)['deadline_seconds'] == 21600


def test_capture_cannot_alias_attempt_directory_case(evidence):
    outer = wire.strict_json(evidence[0])
    body = outer['registration']
    original_bundle = wire.strict_json(evidence[1])
    capture = Path(original_bundle['owner_statement']['quota_capture']['directory'])
    capture.mkdir()
    alias = capture.with_name(capture.name.upper())
    if not alias.exists():
        pytest.skip('requires a case-insensitive filesystem for a genuine alias')
    assert alias.samefile(capture) and str(alias) != str(capture)
    body['attempt_directory'] = str(alias / 'future-attempt')
    raw = wire.canonical(outer)
    bundle, word = bundle_for(raw, capture)
    with pytest.raises(ValueError, match='separate from attempt/evidence'):
        review.validate_bundle(raw, bundle, word)


def test_object_reads_disable_network_replacements_and_inherited_configuration(evidence, monkeypatch):
    original = review.subprocess.run
    seen = []
    def checked(command, **kwargs):
        env = kwargs['env']
        assert env['GIT_NO_LAZY_FETCH'] == '1'
        assert env['GIT_NO_REPLACE_OBJECTS'] == '1'
        assert env['GIT_CONFIG_GLOBAL'] == '/dev/null'
        assert env['GIT_TERMINAL_PROMPT'] == '0'
        assert 'ANTHROPIC_API_KEY' not in env and 'GIT_CONFIG_COUNT' not in env
        assert '--no-replace-objects' in command
        seen.append(command)
        return original(command, **kwargs)
    monkeypatch.setattr(review.subprocess, 'run', checked)
    assert review.validate_bundle(*evidence)
    assert seen
