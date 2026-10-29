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
