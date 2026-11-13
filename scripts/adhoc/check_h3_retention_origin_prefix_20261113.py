"""Explicit offline retention-origin preparation control, 2026-11-13; H3-RF6.

Inputs: isolated-module pytest fixtures and synthetic preparation inputs.
Outputs: caller-owned scratch only, ending before capture authority setup.
Relocated unchanged after its original tests/test_native_incomplete_retention.py
node reached the 1200-second deadline in refinements-retention-prefix-01.
The original test module SHA256 was
2f610dd578d3cced86c8d0ac5e1c98e3896e583111c56ac84304524d5b5998a3.
This new location has not been executed; the bounded runner permits tests/ nodes
only. Normal CI does not collect this expensive ad hoc control. No assertion was
relaxed, and the three original public retention tests remain in the CI module.
"""
import pytest

from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401

pytestmark = pytest.mark.usefixtures('isolated_modules')


def test_public_fixture_preparation_stops_before_capture_authority(tmp_path, monkeypatch):
    """Exercise the CI origin failure without capture words or reservations."""
    from tests import test_native_shared_execution as fixture_module
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_subscription_capture as subscription_capture

    class PreparationComplete(Exception):
        pass

    def forbidden(*args, **kwargs):
        pytest.fail('preparation-only fixture reached capture authority')

    completed = []
    def stop_before_authority(raw, ci_path, directory):
        completed.append((raw, ci_path, directory))
        raise PreparationComplete

    monkeypatch.chdir(authority.ROOT)
    monkeypatch.setattr(fixture_module, 'authority_for', stop_before_authority)
    monkeypatch.setattr(subscription_capture, 'activate_capture_word', forbidden)
    monkeypatch.setattr(subscription_capture, 'capture_subscription', forbidden)
    monkeypatch.setattr(subscription_capture, '_reservation_raw', forbidden)
    root = tmp_path / 'preparation-only'
    with pytest.raises(PreparationComplete):
        fixture_module.make_case(root)
    assert len(completed) == 1
    assert completed[0][1].is_file(), 'preparation did not reach its offline CI declaration'
    assert not (root / 'synthetic-capture').exists()
    assert not (root / 'native-attempt').exists()
    assert not (root / 'native-evidence').exists()
