"""Phase 4 selects its own thinking display (#2541); invented ancestry and stubs only."""
from contextlib import contextmanager
from decimal import Decimal
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import native, registration as audit_registration
from audit_controls.test_context_preparation import ancestry, accepted_audit, save  # noqa: F401  (fixtures)
from audit_controls.test_native import native_case, configure_execution  # noqa: F401  (fixture)
from audit_controls.test_response_buffer_selection import ProxyBoundary, forbidden
from budgeted_cborg import BudgetStop, Ledger
from finalization_controls import native as final_native, prepare as final_prepare
from finalization_controls import registration as final_registration
from native_proxy import THINKING_DISPLAY

KEY = 'native_thinking_display'


def test_the_phase4_validator_accepts_only_the_exact_selection_on_its_runtime():
    runtime = {'version': '2.1.272 (Claude Code)'}
    assert final_registration.finalization_thinking_display({'native_runtime': runtime}) is None
    assert final_registration.finalization_thinking_display({KEY: dict(THINKING_DISPLAY), 'native_runtime': runtime}) == THINKING_DISPLAY
    for value, runtime_version in ((None, runtime['version']), ({**THINKING_DISPLAY, 'display': 'omitted'}, runtime['version']),
                                   (dict(THINKING_DISPLAY), '2.1.273 (Claude Code)')):
        with pytest.raises(BudgetStop):
            final_registration.finalization_thinking_display({KEY: value, 'native_runtime': {'version': runtime_version}})


@pytest.mark.parametrize('selected', [False, True])
def test_phase4_selects_its_own_display_and_never_inherits_the_audits(ancestry, tmp_path, monkeypatch, selected):
    """The accepted audit carries a display; Phase 4 has one only when it selects it itself."""
    monkeypatch.setattr(audit_registration, 'THINKING_DISPLAY_RUNTIMES', frozenset({'synthetic-native-version'}))
    audited = ({**ancestry[0], KEY: dict(THINKING_DISPLAY)}, *ancestry[1:])
    accepted, acceptance = accepted_audit(audited, tmp_path / 'accepted')
    assert audit_registration.read_json(accepted)[KEY] == THINKING_DISPLAY
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=tmp_path / 'phase4', job_id='synthetic_final', repository=ancestry[0]['repository'],
        **({KEY: dict(THINKING_DISPLAY)} if selected else {}))
    m = final_registration.validate_registration(path)
    assert (KEY in m) is selected
    if selected:
        assert m[KEY] == THINKING_DISPLAY and final_native.thinking_display(m) == THINKING_DISPLAY


def test_phase4_preparation_refuses_before_its_destination_exists(ancestry, tmp_path):
    """The fixture's runtime is not 2.1.272, so the exact selection is refused there too."""
    accepted, acceptance = accepted_audit(ancestry, tmp_path / 'accepted')
    for value in (dict(THINKING_DISPLAY), {**THINKING_DISPLAY, 'extra': 1}):
        with pytest.raises(BudgetStop):
            final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
                destination=tmp_path / 'phase4', job_id='synthetic_final', repository=ancestry[0]['repository'],
                **{KEY: value})
        assert not (tmp_path / 'phase4').exists()


def test_the_shared_controller_forwards_a_protocol_stages_own_display(native_case, monkeypatch):
    c = native_case
    context, sdk = configure_execution(c, monkeypatch)
    c.manifest.update(kind='d4d_native_finalization', **{KEY: dict(THINKING_DISPLAY)})
    c.manifest['native_runtime']['version'] = '2.1.272 (Claude Code)'
    calls = []
    def proxy(**kwargs): calls.append(kwargs); raise ProxyBoundary()
    monkeypatch.setattr(native, 'AuditProxy', proxy)
    monkeypatch.setattr(native, 'execute_child', forbidden)
    protocol = SimpleNamespace(build_policy=lambda manifest, path: c.policy, AuditHistory=native.AuditHistory,
                               thinking_display=final_native.thinking_display)
    with pytest.raises(ProxyBoundary):
        native.execute_job(context, client=sdk, upstream=object(), protocol=protocol)
    assert calls[0]['thinking_display'] == THINKING_DISPLAY


def test_the_phase4_receipt_reports_the_display(tmp_path, monkeypatch):
    """Stubs stand in for registration, review and ownership; the receipt code is the real one."""
    from finalization_controls import registration as final_reg
    attempt = tmp_path / 'attempts' / 'synthetic_final'
    manifest = {'job': {'id': 'synthetic_final', 'attempt_dir': str(attempt), 'output_dir': str(attempt / 'output')},
                'repository_commit': 'a' * 40, KEY: dict(THINKING_DISPLAY)}
    path, review = tmp_path / 'registration.json', tmp_path / 'review.json'
    save(path, manifest)
    save(review, {'verdict': 'approve', 'registration_sha256': final_reg.sha(path), 'repository_commit': 'a' * 40,
                  'ci_conclusion': 'success', 'allowed_jobs': ['synthetic_final']})
    ledger = Ledger(tmp_path / 'billing.json', manifest_sha256=final_reg.sha(path), total_cap=400)
    @contextmanager
    def owned(*args):
        yield SimpleNamespace(ledger=ledger, verify_admission=lambda: None)
    monkeypatch.setattr(final_reg, 'validate_registration', lambda p: json.loads(Path(p).read_text()))
    monkeypatch.setattr(final_reg, 'verify', lambda *args: None)
    monkeypatch.setattr(final_native, 'build_policy', lambda *args: None)
    monkeypatch.setattr(native, 'verify_runtime', lambda *args: None)
    monkeypatch.setattr(final_native, 'owned_sequence', owned)
    def stops(context):
        raise BudgetStop('synthetic Phase 4 stop')
    with pytest.raises(BudgetStop):
        final_native.run_job(path, review, adapter=stops)
    report = json.loads((attempt / 'result.json').read_text())['thinking_display']
    assert report['kind'] == 'thinking_display_summary_v1' and report['registered'] == THINKING_DISPLAY
