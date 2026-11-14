"""D109 pending-floor public completion, using only synthetic Python authority.

This selects pending before minting any registration. The ordinary public
lifetime and saved gate reconstruction run unchanged; no native/provider call
or scientific acceptance is claimed.
"""
from tests import test_native_shared_execution as public


def test_pending_floor_public_completion_retains_diagnostic_reading(tmp_path, monkeypatch):
    pending = {'state': 'pending', 'mode': 'diagnostic_pilot'}
    original_builder = public.build_native_fixture

    def build_pending_fixture(root, *, registered_python):
        data = original_builder(root, registered_python=registered_python,
                                coverage_floor=pending)
        assert data['synthetic_parameters']['coverage_floor'] == pending
        assert data['synthetic_parameters']['coverage_floor'] is not pending
        return data

    monkeypatch.chdir(public.authority.ROOT)
    monkeypatch.setattr(public, 'build_native_fixture', build_pending_fixture)
    case = public.make_case(tmp_path / 'native26-pending')
    selected = public.c.strict_json(case['selection'].receipt_policy.raw)
    assert selected['coverage_floor'] == pending

    result = public.launch_case(case, monkeypatch)
    public.assert_completed_case(case, result)

    assert result['state'] == 'completed_pending_independent_review'
    assert all(row['checked'] is True and row['passed'] is True
               for row in result['gates'].values())
    receipts_gate = result['gates']['receipts']
    reading = receipts_gate['receipts']['coverage_floor']
    assert reading['state'] == 'pending'
    assert reading['passed'] is False
    assert reading['floor'] == pending
    assert 'registered receipt coverage' not in receipts_gate['floors']
    assert receipts_gate['floors'] and not any(receipts_gate['floors'].values())

    saved = public.execute.read_final(case['raw'])
    assert saved == result
    assert saved['gates']['receipts']['receipts']['coverage_floor'] == reading
    assert saved['gates']['receipts']['receipts']['coverage_floor']['passed'] is False
    assert saved['scientific_acceptance'] == 'not_assessed'


# Match the v1/v2 import-origin isolation used by the other public native cases.
# Deliberate foreign-origin changes inside a test body still reach the guard.
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: E402,F401
import pytest as _origin_pytest  # noqa: E402

pytestmark = _origin_pytest.mark.usefixtures("isolated_modules")
