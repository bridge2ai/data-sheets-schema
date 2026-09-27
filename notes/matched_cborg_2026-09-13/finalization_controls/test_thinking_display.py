"""Phase 4 selects its own thinking display (#2541); invented ancestry and stubs only."""
from contextlib import contextmanager
from decimal import Decimal
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import native, registration as audit_registration
from audit_controls.test_context_preparation import ancestry, accepted_audit, save  # noqa: F401  (fixtures)
from audit_controls.test_native import native_case, configure_execution, response_events  # noqa: F401  (fixture)
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


@pytest.mark.parametrize('change, match', [
    ('malformed', 'must be thinking_display_v1, summarized, proxy_substitution'),
    ('unregistered_runtime', 'registered only for Claude Code 2.1.272'),
])
def test_the_phase4_registration_check_itself_refuses_a_changed_display(ancestry, tmp_path, monkeypatch, change, match):
    """#2647: a registration prepared with the display, then edited by hand or read on a runtime
    the display is not registered for, is refused by validate_registration itself, before
    run_job takes ownership and uses up Phase 4's one attempt."""
    monkeypatch.setattr(audit_registration, 'THINKING_DISPLAY_RUNTIMES', frozenset({'synthetic-native-version'}))
    accepted, acceptance = accepted_audit(ancestry, tmp_path / 'accepted')
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=tmp_path / 'phase4', job_id='synthetic_final', repository=ancestry[0]['repository'],
        **{KEY: dict(THINKING_DISPLAY)})
    assert final_registration.validate_registration(path)[KEY] == THINKING_DISPLAY
    if change == 'malformed':
        manifest = json.loads(Path(path).read_text())
        manifest[KEY] = {**THINKING_DISPLAY, 'delivery': 'cli_flag'}
        Path(path).write_text(json.dumps(manifest, indent=2) + '\n')
    else:
        monkeypatch.setattr(audit_registration, 'THINKING_DISPLAY_RUNTIMES', frozenset({'2.1.272 (Claude Code)'}))
    with pytest.raises(BudgetStop, match=match):
        final_registration.validate_registration(path)


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


def _phase4_protocol(c, completed):
    """A Phase 4 stand-in for the shared controller: the real display selector, the audit's
    history and transcript checks, and a completion that records it was reached."""
    def complete(context, evidence, runtime):
        completed.append(runtime)
        return {'completed': True}
    return SimpleNamespace(build_policy=lambda manifest, path: c.policy, AuditHistory=native.AuditHistory,
                           classify_command=native.classify_command, inspect_transcript=native.inspect_transcript,
                           thinking_display=final_native.thinking_display, complete=complete)


@pytest.mark.parametrize('proven', [True, False], ids=['proven', 'unproven'])
def test_a_completed_phase4_run_passes_the_strict_gate_before_it_completes(native_case, monkeypatch, proven):
    """#2593: a protocol stage's run reaches the shared controller's strict gate, and a failed
    proof stops it before the stage's completion."""
    c = native_case
    c.case.update(thinking={'type': 'adaptive'}, compact=True)
    context, sdk = configure_execution(c, monkeypatch)
    c.manifest.update(kind='d4d_native_finalization', **{KEY: dict(THINKING_DISPLAY)})
    sent = []
    def respond(request):
        sent.append(request.content)
        return httpx.Response(200, content=response_events(), headers={'content-type': 'text/event-stream'})
    checks, real = [], native.thinking_display_evidence
    def gate(root, value, *, strict):
        checks.append((Path(root), value, strict))
        if not proven:
            # The proof the gate re-reads fails: a request folder with no thinking record.
            (Path(root) / 'unproven-request').mkdir()
        return real(root, value, strict=strict)
    monkeypatch.setattr(native, 'thinking_display_evidence', gate)
    completed = []
    protocol = _phase4_protocol(c, completed)
    upstream = httpx.Client(transport=httpx.MockTransport(respond))
    if proven:
        assert native.execute_job(context, client=sdk, upstream=upstream, protocol=protocol) == {'completed': True}
        assert len(completed) == 1
    else:
        with pytest.raises(BudgetStop, match='thinking display of request unproven-request is not proven'):
            native.execute_job(context, client=sdk, upstream=upstream, protocol=protocol)
        assert completed == []
    assert checks == [(c.attempt / 'requests', THINKING_DISPLAY, True)]
    assert sent and all(json.loads(body)['thinking'] == {'type': 'adaptive', 'display': 'summarized'} for body in sent)


@pytest.mark.parametrize('selected', [False, True])
def test_the_phase4_cli_delivers_the_exact_selection_or_none(selected, tmp_path, monkeypatch, capsys):
    """#2596: the documented route, `prepare --native-thinking-display summarized`."""
    calls = []
    monkeypatch.setattr(final_prepare, 'prepare', lambda **kwargs: calls.append(kwargs) or tmp_path / 'registration.json')
    argv = ['prepare', '--accepted-audit-registration', 'a.json', '--acceptance', 'b.json',
            '--destination', str(tmp_path / 'phase4'), '--job-id', 'synthetic_final']
    monkeypatch.setattr(sys, 'argv', argv + (['--native-thinking-display', 'summarized'] if selected else []))
    final_prepare.main()
    assert calls[0][KEY] == (THINKING_DISPLAY if selected else None)


def test_the_phase4_cli_refuses_any_other_display(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(final_prepare, 'prepare', forbidden)
    monkeypatch.setattr(sys, 'argv', ['prepare', '--accepted-audit-registration', 'a.json', '--acceptance', 'b.json',
                                      '--destination', str(tmp_path / 'phase4'), '--job-id', 'synthetic_final',
                                      '--native-thinking-display', 'omitted'])
    with pytest.raises(SystemExit) as stop:
        final_prepare.main()
    assert stop.value.code == 2 and 'invalid choice' in capsys.readouterr().err


@pytest.mark.parametrize('registered', [True, False], ids=['registered', 'not_registered'])
@pytest.mark.parametrize('admitted', [False, True], ids=['nothing_admitted', 'unproven_request'])
def test_the_phase4_receipt_reports_the_display(tmp_path, monkeypatch, admitted, registered):
    """Stubs stand in for registration, review and ownership; the receipt code is the real one.

    #2595: a stop after a request was admitted whose display is not proven still writes its
    receipt, reports the problem and keeps the stop's own reason. #2649: a run registered
    without a display writes no report at all."""
    from finalization_controls import registration as final_reg
    attempt = tmp_path / 'attempts' / 'synthetic_final'
    manifest = {'job': {'id': 'synthetic_final', 'attempt_dir': str(attempt), 'output_dir': str(attempt / 'output')},
                'repository_commit': 'a' * 40, **({KEY: dict(THINKING_DISPLAY)} if registered else {})}
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
        if admitted:
            folder = context.attempt / 'requests' / 'synthetic-request'
            folder.mkdir(parents=True)
            (folder / 'request.json').write_text('{"synthetic": true}\n')
        raise BudgetStop('synthetic Phase 4 stop')
    with pytest.raises(BudgetStop, match='synthetic Phase 4 stop'):
        final_native.run_job(path, review, adapter=stops)
    receipt = json.loads((attempt / 'result.json').read_text())
    assert receipt['status'] == 'stopped' and receipt['reason'] == 'synthetic Phase 4 stop'
    if not registered:
        assert 'thinking_display' not in receipt
        return
    report = receipt['thinking_display']
    assert report['kind'] == 'thinking_display_summary_v1' and report['registered'] == THINKING_DISPLAY
    assert [problem['id'] for problem in report['problems']] == (['synthetic-request'] if admitted else [])
