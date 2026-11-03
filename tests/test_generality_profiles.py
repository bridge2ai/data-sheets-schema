"""F18: explicit declarations outrank historical compatibility."""
import pytest
from data_sheets_schema.profiles import for_record, NEUTRAL, BRIDGE2AI


@pytest.mark.parametrize('when', [None, 'not-a-date', '2026-09-12not-a-timestamp',
                                 '2026-09-12T99:00:00Z'])
def test_undated_missing_profile_refuses(when, monkeypatch):
    monkeypatch.setenv('D4D_PROFILE', 'bridge2ai')
    with pytest.raises(ValueError, match='profile absent: a valid record_generated_at is required'):
        for_record({'record_generated_at': when})


@pytest.mark.parametrize('when', ['2026-09-13', '2026-10-29'])
def test_contemporary_missing_profile_is_neutral(when, monkeypatch):
    monkeypatch.setenv('D4D_PROFILE', 'bridge2ai')
    assert for_record({'record_generated_at': when}) is NEUTRAL


def test_historical_fallback_is_dated_and_stated():
    with pytest.warns(RuntimeWarning, match='predates profiles'):
        assert for_record({'record_generated_at': '2026-09-12T12:00:00Z'}) is BRIDGE2AI
    assert for_record({'record_generated_at': '2026-09-12', 'schema': {'profile': 'neutral'}}) is NEUTRAL
    with pytest.raises(ValueError, match='unknown profile'):
        for_record({'record_generated_at': '2026-09-12', 'schema': {'profile': 'unknown'}})


@pytest.mark.parametrize('when,profile,basis', [
    ('2026-09-01T00:00:00+00:00', BRIDGE2AI, 'historical study fallback'),
    ('2026-10-29T00:00:00+00:00', NEUTRAL, 'contemporary neutral fallback'),
])
def test_identity_capture_preserves_the_record_date(when, profile, basis):
    # N3: the reviewer's dated, profile-less record must match its own digest.
    from data_sheets_schema import schema_digest
    from data_sheets_schema.profile_identity import capture
    from data_sheets_schema.provenance import profile_assessment
    digest = schema_digest.fingerprint(schema_digest.digest_text('Dataset', profile=profile))
    record = {'record_generated_at': when, 'schema': {'digest_md5': digest}}
    context = capture(record)
    assert context['status'] == 'match'
    assert context['effective_profile'] == profile.name
    assert context['profile_basis'] == basis
    assert profile_assessment(record)[0] == []


def test_identity_capture_reports_an_undated_profile_refusal():
    from data_sheets_schema.provenance import profile_assessment
    findings, context = profile_assessment({'schema': {'digest_md5': 'unrecognized'}})
    assert context['effective_profile'] is None
    assert context['profile_basis'] == 'could not select one'
    assert findings and 'record_generated_at is required' in findings[0]


@pytest.fixture
def profile_history(tmp_path, monkeypatch):
    """A complete local history keeps ancestry tests usable in shallow CI."""
    import subprocess
    from data_sheets_schema import profiles
    root = tmp_path / 'history'
    root.mkdir()

    def git(*args):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null',
                               '-c', 'user.name=Profile test',
                               '-c', 'user.email=profile-test.invalid', *args],
                              cwd=root, capture_output=True, text=True, check=True).stdout.strip()

    git('init')
    git('commit', '--allow-empty', '-m', 'Historical code')
    old = git('rev-parse', 'HEAD')
    witness = root / 'data' / 'historical_provenance.yaml'
    witness.parent.mkdir()
    witness.write_text('record_type: d4d_generation_provenance\n'
                       'repo:\n  commit: ' + 'd' * 40 + '\n'
                       'schema: {}\n'
                       'note: ' + 'c' * 40 + '\n')
    (witness.parent / 'derived_provenance.yaml').write_text(
        'record_type: d4d_derived_provenance\nrepo:\n  commit: ' + 'b' * 40 + '\n')
    git('add', 'data/historical_provenance.yaml', 'data/derived_provenance.yaml')
    git('commit', '-m', 'Retain a historical provenance witness')
    git('commit', '--allow-empty', '-m', 'Introduce profiles')
    introduction = git('rev-parse', 'HEAD')
    git('commit', '--allow-empty', '-m', 'Profile-aware code')
    new = git('rev-parse', 'HEAD')
    monkeypatch.setattr(profiles, '_CHECKOUT_ROOT', root)
    monkeypatch.setattr(profiles, 'PROFILES_INTRODUCED_COMMIT', introduction)
    return old, introduction, new


def test_new_run_of_historical_code_keeps_study_identity(profile_history):
    # D64 item 14(d): v8 output records old code with today's execution time.
    from datetime import datetime, timezone
    from data_sheets_schema import schema_digest
    from data_sheets_schema.provenance import profile_assessment
    record = {
        'repo': {'commit': profile_history[0]},
        'record_generated_at': datetime.now(timezone.utc).isoformat(),
        'schema': {'digest_md5': schema_digest.fingerprint(
            schema_digest.digest_text('Dataset', profile=BRIDGE2AI))},
    }
    with pytest.warns(RuntimeWarning, match='predates profiles'):
        assert for_record(record) is BRIDGE2AI
        problems, context = profile_assessment(record)
    assert problems == []
    assert context['status'] == 'match'
    assert context['effective_profile'] == 'bridge2ai'
    assert context['profile_basis'] == 'historical study fallback'


@pytest.mark.parametrize('index', [1, 2])
def test_profile_aware_code_outranks_historical_date(profile_history, index):
    assert for_record({'repo': {'commit': profile_history[index]},
                       'record_generated_at': '2026-09-01'}) is NEUTRAL


def test_historical_commit_needs_no_date(profile_history):
    with pytest.warns(RuntimeWarning, match='predates profiles'):
        assert for_record({'repo': {'commit': profile_history[0]}}) is BRIDGE2AI


@pytest.mark.parametrize('commit', ['d' * 40, 'b' * 40])
def test_missing_object_requires_pre_profile_provenance_witness(profile_history, commit):
    with pytest.warns(RuntimeWarning, match='predates profiles'):
        assert for_record({'repo': {'commit': commit},
                           'record_generated_at': '2026-10-30'}) is BRIDGE2AI
    # Merely mentioning a hash in that old blob is not a code attestation.
    with pytest.raises(ValueError, match='cannot be resolved locally'):
        for_record({'repo': {'commit': 'c' * 40},
                    'record_generated_at': '2026-09-01'})


@pytest.mark.parametrize('commit', ['', 'HEAD', '--help', 'f' * 40, 123])
def test_unprovable_commit_does_not_fall_back_to_date(profile_history, commit):
    with pytest.raises(ValueError, match='profile absent:'):
        for_record({'repo': {'commit': commit}, 'record_generated_at': '2026-09-01'})


def test_shallow_negative_ancestry_refuses(profile_history, monkeypatch):
    from data_sheets_schema import profiles
    (profiles._CHECKOUT_ROOT / '.git' / 'shallow').write_text(profile_history[2] + '\n')
    monkeypatch.setattr(profiles, 'PROFILES_INTRODUCED_COMMIT', profile_history[2])
    with pytest.raises(ValueError, match='incomplete repo.commit ancestry'):
        for_record({'repo': {'commit': profile_history[0]},
                    'record_generated_at': '2026-09-01'})


def test_explicit_profile_does_not_require_git(monkeypatch):
    from data_sheets_schema import profiles
    monkeypatch.setattr(profiles, '_CHECKOUT_ROOT', None)
    assert for_record({'schema': {'profile': 'neutral'},
                       'repo': {'commit': 'unavailable'}}) is NEUTRAL
    with pytest.raises(ValueError, match='local checkout'):
        for_record({'repo': {'commit': 'a2a3e157b'}})
