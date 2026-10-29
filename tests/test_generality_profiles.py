"""F18: explicit declarations outrank historical compatibility."""
import pytest
from data_sheets_schema.profiles import for_record, NEUTRAL, BRIDGE2AI


@pytest.mark.parametrize('when', [None, 'not-a-date', '2026-09-12not-a-timestamp',
                                 '2026-09-12T99:00:00Z', '2026-09-13', '2026-10-29'])
def test_undated_or_contemporary_missing_profile_is_neutral(when, monkeypatch):
    monkeypatch.setenv('D4D_PROFILE', 'bridge2ai')
    assert for_record({'record_generated_at': when}) is NEUTRAL


def test_historical_fallback_is_dated_and_stated():
    with pytest.warns(RuntimeWarning, match='predates profiles'):
        assert for_record({'record_generated_at': '2026-09-12T12:00:00Z'}) is BRIDGE2AI
    assert for_record({'record_generated_at': '2026-09-12', 'schema': {'profile': 'neutral'}}) is NEUTRAL
    with pytest.raises(ValueError, match='unknown profile'):
        for_record({'record_generated_at': '2026-09-12', 'schema': {'profile': 'unknown'}})
