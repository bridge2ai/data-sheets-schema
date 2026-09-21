"""Real preparers, synthetic ancestry; the selector never changes the instrument."""
from pathlib import Path

import pytest

from audit_controls import prepare, registration, transport
from audit_controls.test_context_preparation import ancestry, accepted_audit, save
from audit_controls.test_staged_preparation import actual_renderer_history_root
from finalization_controls import prepare as final_prepare, registration as final_registration

KEY = 'native_upstream_read_timeout_seconds'


@pytest.mark.parametrize('staged', [False, True])
def test_fresh_selector_is_registered_pinned_and_scientifically_inert(ancestry, tmp_path, staged):
    common = dict(ancestry[0], native_api_timeout_ms=3600000, staged_audit_output=staged,
                  context_recovery=True)
    legacy = prepare.prepare(**common, destination=tmp_path / 'legacy')
    selected = prepare.prepare(**common, destination=tmp_path / 'selected',
                               native_upstream_read_timeout_seconds=2700)
    before = registration.validate_registration(legacy)
    after = registration.validate_registration(selected)
    assert KEY not in before and after[KEY] == 2700
    assert registration.native_upstream_read_timeout(after) == 2700
    assert after['native_runtime'] == before['native_runtime']
    for key in ('model', 'profile', 'provider_base_url', 'provider_context_policy'):
        assert after[key] == before[key]
    for key in ('instruction', 'system_prompt'):
        assert Path(after['job'][key]).read_text().replace(str(selected.parent), str(legacy.parent)).replace(
            after['context_recovery']['index']['sha256'], before['context_recovery']['index']['sha256']) == Path(before['job'][key]).read_text()
    assert set(after['inputs']) == set(before['inputs'])
    for role, path in after['inputs'].items():
        assert Path(path).read_bytes() == Path(before['inputs'][role]).read_bytes()
    for path in registration.required_paths(after):
        assert after['pinned_files'][str(path)] == registration.sha(path)
    assert not Path(after['job']['attempt_dir']).exists()
    assert not Path(after['budget']['ledger_path']).exists()
    assert ancestry[2] == {name: Path(name).read_bytes() for name in ancestry[2]}


@pytest.mark.parametrize('value,sdk', [(True,3600000), (0,3600000), (-1,3600000), (1.5,3600000),
    ('2700',3600000), (2700,None), (3600,3600000), (1,10800001)])
def test_invalid_selector_refused_before_destination_creation(tmp_path, value, sdk):
    destination = tmp_path / 'uncreated'
    with pytest.raises(registration.BudgetStop):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, native_api_timeout_ms=sdk,
            native_upstream_read_timeout_seconds=value)
    assert not destination.exists()


def test_real_phase4_preparation_keeps_accepted_selector_as_evidence_only(ancestry, tmp_path):
    with_selector = ({**ancestry[0], 'native_api_timeout_ms':3600000,
                      'native_upstream_read_timeout_seconds':2700}, *ancestry[1:])
    accepted, acceptance = accepted_audit(with_selector, tmp_path / 'accepted')
    accepted_bytes = accepted.read_bytes()
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=tmp_path / 'phase4', job_id='synthetic_final', repository=ancestry[0]['repository'])
    phase4 = final_registration.validate_registration(path)
    assert KEY not in phase4
    assert registration.read_json(accepted)[KEY] == 2700 and accepted.read_bytes() == accepted_bytes
    assert phase4['pinned_files'][str(accepted)] == registration.sha(accepted)
    assert registration.native_upstream_read_timeout(phase4) is None
    assert KEY not in phase4['native_runtime'] and KEY not in phase4.get('provider_transport', {})
    # An injected selector is rejected by actual Phase4 registration validation,
    # not merely omitted by the preparer's copy list.
    phase4[KEY] = 2700; save(path, phase4)
    with pytest.raises(registration.BudgetStop, match='audit-only'):
        final_registration.validate_registration(path)
    assert not Path(phase4['job']['attempt_dir']).exists()
    assert not Path(phase4['budget']['ledger_path']).exists()
