"""The registered thinking display in audits: registration, preparation, stages and the runtime (#2464).

Invented ancestry, a synthetic child and injected clients only; nothing is sent to a provider."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import batch_native, native, prepare, registration
from audit_controls.test_batch_runtime import batch  # noqa: F401  (fixture)
from audit_controls.test_context_preparation import ancestry, save  # noqa: F401  (fixture)
from audit_controls.test_native import native_case, configure_execution, response_events  # noqa: F401
from audit_controls.test_response_buffer_selection import CLI_REQUIRED, ProxyBoundary, forbidden, snapshot
from audit_controls.test_upstream_timeout import generation_manifest
from budgeted_cborg import BudgetStop
from evaluation_controls import registration as evaluation_registration
from finalization_controls import native as final_native
from native_proxy import THINKING_DISPLAY
import run_api_canary

KEY = 'native_thinking_display'
VERSION = '2.1.272 (Claude Code)'


def manifest(**changes):
    return {'kind': 'd4d_native_audit_continuation', KEY: dict(THINKING_DISPLAY),
            'native_runtime': {'version': VERSION}, **changes}


# --- the registration --------------------------------------------------------------------------

def test_absence_is_legacy_and_the_exact_selection_is_returned():
    assert registration.native_thinking_display({'kind': 'd4d_native_audit_continuation'}) is None
    assert registration.native_thinking_display(manifest()) == THINKING_DISPLAY


@pytest.mark.parametrize('change, match', [
    ({KEY: None}, 'audit-only'),
    ({'kind': 'd4d_native_finalization'}, 'audit-only'),
    ({KEY: {**THINKING_DISPLAY, 'delivery': 'cli_flag'}}, 'thinking_display_v1'),
    ({KEY: 'summarized'}, 'thinking_display_v1'),
    ({'native_runtime': {'version': '2.1.273 (Claude Code)'}}, '2.1.272'),
    ({'native_runtime': None}, '2.1.272'),
])
def test_the_registration_refuses_anything_but_the_exact_audit_selection(change, match):
    with pytest.raises(BudgetStop, match=match):
        registration.native_thinking_display(manifest(**change))


# --- preparation --------------------------------------------------------------------------------

@pytest.mark.parametrize('value, match', [({**THINKING_DISPLAY, 'display': 'omitted'}, 'thinking_display_v1'),
                                          (dict(THINKING_DISPLAY), '2.1.272')])
def test_preparation_refuses_before_the_destination_exists(ancestry, tmp_path, value, match):
    """The fixture's runtime is not 2.1.272, so even the exact selection is refused there."""
    with pytest.raises(BudgetStop, match=match):
        prepare.prepare(**ancestry[0], destination=tmp_path / 'selected', native_thinking_display=value)
    assert not (tmp_path / 'selected').exists()


@pytest.mark.parametrize('selected', [False, True])
def test_the_cli_delivers_the_exact_selection_or_none(selected, tmp_path, monkeypatch, capsys):
    path = tmp_path / 'registration.json'; save(path, {})
    calls = []
    def collect(**kwargs): calls.append(kwargs); return path
    monkeypatch.setattr(prepare, 'prepare', collect)
    monkeypatch.setattr(sys, 'argv', ['prepare', *CLI_REQUIRED, *(['--native-thinking-display', 'summarized'] if selected else [])])
    prepare.main()
    assert calls[0][KEY] == (THINKING_DISPLAY if selected else None)


def test_real_preparation_pins_the_selection_and_changes_nothing_the_model_reads(ancestry, tmp_path, monkeypatch):
    monkeypatch.setattr(registration, 'THINKING_DISPLAY_RUNTIMES', frozenset({'synthetic-native-version'}))
    legacy = prepare.prepare(**ancestry[0], destination=tmp_path / 'legacy__')
    selected = prepare.prepare(**ancestry[0], destination=tmp_path / 'selected', native_thinking_display=THINKING_DISPLAY)
    before, after = registration.validate_registration(legacy), registration.validate_registration(selected)
    assert KEY not in before and after[KEY] == THINKING_DISPLAY
    for key in ('instruction', 'system_prompt'):
        assert (Path(after['job'][key]).read_text().replace(str(selected.parent), str(legacy.parent))
                == Path(before['job'][key]).read_text())
    assert json.loads((selected.parent / 'offline_plan.json').read_text())[KEY] == THINKING_DISPLAY
    assert KEY not in json.loads((legacy.parent / 'offline_plan.json').read_text())


@pytest.mark.parametrize('value', [None, {**THINKING_DISPLAY, 'delivery': 'cli_flag'}], ids=['null', 'cli_flag'])
def test_validate_registration_refuses_a_changed_selection(ancestry, tmp_path, monkeypatch, value):
    """#2554: the registration check itself, not only preparation or launch."""
    monkeypatch.setattr(registration, 'THINKING_DISPLAY_RUNTIMES', frozenset({'synthetic-native-version'}))
    path = prepare.prepare(**ancestry[0], destination=tmp_path / 'selected', native_thinking_display=THINKING_DISPLAY)
    changed = registration.read_json(path); changed[KEY] = value
    save(path, changed)
    with pytest.raises(BudgetStop, match='thinking'):
        registration.validate_registration(path)


def test_a_worker_checkpoint_cannot_drop_or_adopt_the_display(metadata_ancestry, tmp_path, monkeypatch):
    """The successor must restate its source's display exactly; it is refused before its destination exists."""
    from audit_controls.test_stall_allowance_checkpoint import build
    monkeypatch.setattr(registration, 'THINKING_DISPLAY_RUNTIMES', frozenset({'synthetic-native-version'}))
    args = build(metadata_ancestry, tmp_path, monkeypatch, with_stalls=False,
                 source_extra={KEY: dict(THINKING_DISPLAY)})
    with pytest.raises(BudgetStop, match='scientific/runtime settings'):
        prepare.prepare(**args, destination=tmp_path / 'next')
    assert not (tmp_path / 'next').exists()
    assert prepare.prepare(**args, destination=tmp_path / 'next', **{KEY: dict(THINKING_DISPLAY)}).exists()


from audit_controls.test_source_metadata_upgrade import metadata_ancestry  # noqa: E402,F401  (fixture)


# --- later stages and generation never carry it ------------------------------------------------

@pytest.mark.parametrize('stage, value, match', [
    ('evaluation', THINKING_DISPLAY, 'audit and Phase 4 key'), ('evaluation', None, 'audit and Phase 4 key'),
    # Phase 4 selects its own display now (#2541), but never a null one.
    ('phase4', None, 'thinking_display_v1')], ids=['evaluation-selection', 'evaluation-null', 'phase4-null'])
def test_later_stages_refuse_the_audit_key_or_a_null_before_ownership(stage, value, match, tmp_path, monkeypatch):
    m = {'kind': 'd4d_native_finalization' if stage == 'phase4' else 'd4d_evaluation_registration', KEY: value}
    path, review = tmp_path / 'registration.json', tmp_path / 'review.json'
    save(path, m); save(review, {})
    before = snapshot(tmp_path)
    if stage == 'phase4':
        monkeypatch.setattr(final_native, 'owned_sequence', forbidden)
        monkeypatch.setattr(final_native, 'build_policy', forbidden)
        with pytest.raises(BudgetStop, match=match): final_native.run_job(path, review, adapter=forbidden)
    else:
        spec = importlib.util.spec_from_file_location('thinking_display_evaluation_entry', BASE / 'evaluation_controls/run_evaluation.py')
        run_evaluation = importlib.util.module_from_spec(spec)
        with monkeypatch.context() as imports:
            imports.setitem(sys.modules, 'registration', evaluation_registration)
            spec.loader.exec_module(run_evaluation)
        monkeypatch.setattr(run_evaluation, 'accounting_owner', forbidden)
        monkeypatch.setattr(run_evaluation, 'verify_dependencies', forbidden)
        with pytest.raises(BudgetStop, match=match): run_evaluation.run_job(path, review, 'synthetic', adapter=forbidden)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('value', [THINKING_DISPLAY, None], ids=['selection', 'null'])
def test_generation_refuses_it_even_null(value, tmp_path, monkeypatch):
    m = generation_manifest(tmp_path, monkeypatch)
    m[KEY] = value
    # Refused before any pin or path is read, for both generation arms (the native arm calls this verify).
    with pytest.raises(BudgetStop, match='audit-only; generation'):
        run_api_canary.verify(m, tmp_path / 'unread.json', '0' * 64)


# --- the audit runtime --------------------------------------------------------------------------

@pytest.mark.parametrize('selected', [False, True])
def test_the_audit_proxy_gets_the_display_only_when_registered(native_case, monkeypatch, selected):
    c = native_case
    context, sdk = configure_execution(c, monkeypatch)
    c.manifest.update(kind='d4d_native_audit_continuation')
    c.manifest['native_runtime']['version'] = VERSION
    if selected: c.manifest[KEY] = dict(THINKING_DISPLAY)
    calls = []
    def proxy(**kwargs): calls.append(kwargs); raise ProxyBoundary()
    monkeypatch.setattr(native, 'AuditProxy', proxy)
    monkeypatch.setattr(native, 'execute_child', forbidden)
    with pytest.raises(ProxyBoundary): native.execute_job(context, client=sdk, upstream=object())
    assert ('thinking_display' in calls[0]) is selected
    if selected: assert calls[0]['thinking_display'] == THINKING_DISPLAY


def test_a_protocol_stage_cannot_run_with_the_display(native_case, monkeypatch):
    c = native_case
    context, sdk = configure_execution(c, monkeypatch)
    c.manifest.update(kind='d4d_native_audit_continuation', **{KEY: dict(THINKING_DISPLAY)})
    c.manifest['native_runtime']['version'] = VERSION
    monkeypatch.setattr(native, 'AuditProxy', forbidden)
    with pytest.raises(BudgetStop, match='restricted to the native audit controller'):
        native.execute_job(context, client=sdk, upstream=object(), protocol=SimpleNamespace())


@pytest.mark.parametrize('selected', [False, True])
def test_a_batch_child_proxy_gets_the_display_only_when_registered(batch, monkeypatch, selected):
    m = batch.m
    m.update(provider_base_url='https://api.cborg.lbl.gov')
    m['budget']['prices_per_token'] = {'input': '0.000005', 'output': '0.000025'}
    m['native_runtime']['version'] = VERSION
    if selected: m[KEY] = dict(THINKING_DISPLAY)
    context = SimpleNamespace(manifest=m, manifest_sha256=batch.identity, job=m['job'],
                              registration_path=batch.reg, ledger=batch.ledger, verify=lambda: None)
    calls = []
    def proxy(**kwargs): calls.append(kwargs); raise ProxyBoundary()
    monkeypatch.setattr(batch_native, 'BatchProxy', proxy)
    monkeypatch.setattr(native, 'execute_child', forbidden)
    with pytest.raises(ProxyBoundary):
        batch_native._execute_child(context, m['audit_batches']['children'][0], 100, clock=lambda: 0,
                                    client=object(), upstream=object())
    assert ('thinking_display' in calls[0]) is selected


def _run(c, monkeypatch, thinking, *, compact=True):
    c.case.update(thinking=thinking, compact=compact) if thinking is not None else c.case.update(compact=compact)
    context, sdk = configure_execution(c, monkeypatch)
    c.manifest.update(kind='d4d_native_audit_continuation', **{KEY: dict(THINKING_DISPLAY)})
    c.manifest['native_runtime']['version'] = VERSION
    sent = []
    def respond(request):
        sent.append(request.content)
        return httpx.Response(200, content=response_events(), headers={'content-type': 'text/event-stream'})
    return context, sdk, sent, httpx.Client(transport=httpx.MockTransport(respond))


def test_a_completed_audit_forwards_the_display_and_proves_it(native_case, monkeypatch):
    c = native_case
    context, sdk, sent, upstream = _run(c, monkeypatch, {'type': 'adaptive'})
    checks, real = [], native.thinking_display_evidence
    def spy(root, value, *, strict):
        checks.append((Path(root), strict)); return real(root, value, strict=strict)
    monkeypatch.setattr(native, 'thinking_display_evidence', spy)
    result = native.execute_job(context, client=sdk, upstream=upstream)
    # The launcher re-reads every admitted request strictly before accepting the run.
    assert checks == [(c.attempt / 'requests', True)]
    assert result['validation']['passed']
    assert sent and all(json.loads(body)['thinking'] == {'type': 'adaptive', 'display': 'summarized'} for body in sent)
    folders = [p for p in (c.attempt / 'requests').iterdir() if p.is_dir()]
    assert folders and all((f / 'forwarded_request.json').is_file() and (f / 'stream_timing.json').is_file() for f in folders)
    # The retained initial context is still the child's own request.
    assert result['evidence']['initial_context']['complete_inline_context_observed']


@pytest.mark.parametrize('thinking, compact', [(None, True), ({'type': 'adaptive'}, False)], ids=['absent', 'not_compact'])
def test_a_child_request_the_display_cannot_cover_stops_at_no_cost(native_case, monkeypatch, thinking, compact):
    c = native_case
    context, sdk, sent, upstream = _run(c, monkeypatch, thinking, compact=compact)
    with pytest.raises(BudgetStop):
        native.execute_job(context, client=sdk, upstream=upstream)
    assert sent == []
    state = json.loads(c.ledger.path.read_text()) if c.ledger.path.exists() else {'requests': []}
    assert state['requests'] == []
    assert len(list((c.attempt / 'thinking_refusals').iterdir())) == 1


def test_the_run_job_receipt_reports_the_display(accounting, monkeypatch):
    from audit_controls.test_stop_reconciliation_run import stopping_adapter
    from audit_controls import reconcile_stopped as tool
    import copy
    m, _, _, _, reg = accounting
    first = copy.deepcopy(m)
    first.update(kind='d4d_native_audit_continuation', repository=str(reg.parent), repository_commit='a' * 40,
                 **{KEY: dict(THINKING_DISPLAY)})
    first['job']['attempt_dir'] = str(reg.parent / 'attempts' / first['job']['id'])
    first['job']['output_dir'] = str(reg.parent / 'attempts' / first['job']['id'] / 'output')
    save(reg, first)
    review = reg.parent.parent / 'review.json'
    save(review, {'verdict': 'approve', 'registration_sha256': registration.sha(reg), 'ci_conclusion': 'success',
                  'repository_commit': 'a' * 40, 'allowed_jobs': [first['job']['id']]})
    monkeypatch.setattr(registration, 'validate_registration', lambda _: copy.deepcopy(first))
    monkeypatch.setattr(registration, 'verify', lambda *_: None)
    monkeypatch.setattr(native, 'build_policy', lambda *_: None)
    monkeypatch.setattr(native, 'verify_runtime', lambda *_: None)
    with pytest.raises(BudgetStop):
        native.run_job(reg, review, adapter=stopping_adapter())
    receipt = json.loads((Path(first['job']['attempt_dir']) / 'result.json').read_text())
    report = receipt['thinking_display']
    assert report['kind'] == 'thinking_display_summary_v1' and report['registered'] == THINKING_DISPLAY
    # The synthetic stop admitted a request with no thinking record: reported, never raised.
    assert len(report['problems']) == 1


from audit_controls.test_registration import accounting  # noqa: E402,F401  (fixture)


def _displayed_request(session, display):
    """One settled worker request as the proxy leaves it: child bytes, forwarded bytes and the record."""
    import hashlib
    from decimal import Decimal
    from native_proxy import ADAPTIVE_THINKING, DISPLAYED_THINKING
    from audit_controls import batch_native as runtime
    b, row, root = session.batch, session.row, session.c.attempt
    child = {'model': 'claude-opus-5', 'system': Path(row['system_prompt']).read_text(),
             'messages': [{'role': 'user', 'content': Path(row['instruction']).read_text()}],
             'thinking': {'type': 'adaptive'}}
    raw = json.dumps(child, separators=(',', ':'), ensure_ascii=False).encode()
    forwarded = raw.replace(ADAPTIVE_THINKING, DISPLAYED_THINKING)
    canonical = (json.dumps(json.loads(forwarded), sort_keys=True, ensure_ascii=False) + '\n').encode()
    ticket = b.ledger.reserve(b.owner, Decimal('1'), hashlib.sha256(canonical).hexdigest(), stage_cap='24')
    folder = root / 'requests' / ticket; folder.mkdir(parents=True)
    (folder / 'request.json').write_bytes(canonical); (folder / 'native_request.json').write_bytes(raw)
    (folder / 'forwarded_request.json').write_bytes(forwarded)
    (folder / 'thinking_request.json').write_text(json.dumps({'kind': 'thinking_display_request_v1',
        'registered': display, 'disposition': 'substituted', 'native_request_sha256': hashlib.sha256(raw).hexdigest(),
        'forwarded_request_sha256': hashlib.sha256(forwarded).hexdigest()}))
    response = b'{"synthetic_accounting_only":true}\n'; (folder / 'response.json').write_bytes(response)
    b.ledger.settle(ticket, Decimal('1'), response_sha256=hashlib.sha256(response).hexdigest(), usage={})
    return [r for r in runtime._own_rows(b.m, b.identity) if r['id'] == ticket]


def test_a_batch_child_closure_binds_the_display_evidence(batch):
    from audit_controls import batch_native as runtime
    from audit_controls.test_batch_runtime import BatchSession, proposal
    from native_proxy import thinking_display_evidence
    batch.m[KEY] = dict(THINKING_DISPLAY); batch.m['native_runtime']['version'] = VERSION
    worker = batch.plan['workers'][0]['id']
    s = BatchSession(batch, worker); s.write(json.dumps(proposal(batch, worker))); s.check(); s.seal()
    evidence = s.finish()
    selected = _displayed_request(s, THINKING_DISPLAY)
    root, row = s.c.attempt, s.row
    receipt = {'schema_version': 1, 'job_id': batch.m['job']['id'], 'registration_sha256': batch.identity,
        'billing_attempt': batch.owner, 'child_id': row['id'], 'status': 'completed_proposal',
        'runtime': {'exit_code': 0, 'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0},
        'policy_sha256': runtime._digest(s.c.policy), 'request_rows': selected,
        'initial_context': native.verify_initial_context(SimpleNamespace(attempt=root, job=row), selected),
        'evidence': evidence, 'thinking_display': thinking_display_evidence(root / 'requests', THINKING_DISPLAY, strict=True),
        'frozen_evidence': runtime._tree(root)}
    (root / 'closed.json').write_text(json.dumps(receipt))
    assert runtime.verify_child_closure(batch.m, batch.identity, row['id'])
    # A receipt whose evidence says something else is refused, not only one that drops it (#2550).
    changed = json.loads(json.dumps(receipt))
    changed['thinking_display']['requests'][0]['disposition'] = 'disabled_forwarded'
    (root / 'closed.json').write_text(json.dumps(changed))
    with pytest.raises(BudgetStop, match='thinking display evidence differs'):
        runtime.verify_child_closure(batch.m, batch.identity, row['id'])
    (root / 'closed.json').write_text(json.dumps({k: v for k, v in receipt.items() if k != 'thinking_display'}))
    with pytest.raises(BudgetStop, match='thinking display evidence differs'):
        runtime.verify_child_closure(batch.m, batch.identity, row['id'])
    # And a legacy registration cannot adopt a closure that claims it.
    (root / 'closed.json').write_text(json.dumps(receipt))
    del batch.m[KEY]
    with pytest.raises(BudgetStop, match='thinking display evidence differs'):
        runtime.verify_child_closure(batch.m, batch.identity, row['id'])


@pytest.mark.parametrize('stops', [False, True], ids=['closes', 'stops'])
def test_a_real_child_controller_closes_with_the_display_evidence(batch, monkeypatch, stops):
    """The batch controller's wiring and closure with the display (#2555).

    Only the external process and network are replaced; ledger, history and
    closure replay are real. The proxy is a stand-in, so the request folder is
    written by the fixture: the proxy's own substitution is tested in
    native_controls/test_native_thinking_display.py.
    """
    import threading
    from contextlib import contextmanager
    from audit_controls import batch_native as runtime
    from audit_controls.test_batch_runtime import BatchSession, proposal
    from budgeted_cborg import Ledger, attempt_identity
    batch.m.update(provider_base_url='https://api.cborg.lbl.gov', **{KEY: dict(THINKING_DISPLAY)})
    batch.m['native_runtime']['version'] = VERSION
    batch.m['budget']['prices_per_token'] = {'input': '1', 'output': '1', 'cache_write': '1', 'cache_read': '1'}
    batch.reg.write_text(json.dumps(batch.m)); batch.identity = native.sha(batch.reg)
    batch.owner = attempt_identity(batch.identity, batch.m['job']['id'])
    batch.ledger.path.unlink()
    batch.ledger = Ledger(batch.m['budget']['ledger_path'], manifest_sha256=batch.identity, total_cap=400,
                          attempt_cap=40, attempt_caps_usd={batch.owner: 40})
    batch.ledger.require_resolved(batch.owner)
    proxies = []
    class Client:
        def close(self): pass
    class Proxy:
        def __init__(self, **kwargs):
            self.kw = kwargs; self.token = 'synthetic'; self.failed = threading.Event()
            self.frozen = False; self.unfinished_handlers = None; proxies.append(self)
        @contextmanager
        def running(self):
            try: yield 'http://synthetic.invalid'
            finally: self.frozen = True; self.unfinished_handlers = 0
    monkeypatch.setenv('CBORG_API_KEY', 'synthetic')
    monkeypatch.setattr(runtime, 'provider_clients', lambda manifest, key: (Client(), Client()))
    monkeypatch.setattr(runtime, 'BatchProxy', Proxy)
    monkeypatch.setattr(native, 'verify_runtime', lambda m: Path('/synthetic/claude'))
    def execute(argv, **kwargs):
        row = next(r for r in batch.m['audit_batches']['children'] if Path(r['attempt_dir']) == kwargs['attempt'])
        s = BatchSession(batch, row['id'], existing=True, history=kwargs['event_observer'].__self__)
        kwargs['verify_launch']()
        _displayed_request(s, THINKING_DISPLAY)
        s.write(json.dumps(proposal(batch, row['id']))); s.check(); s.seal(); s.finish()
        return 0
    monkeypatch.setattr(native, 'execute_child', execute)
    context = SimpleNamespace(manifest=batch.m, manifest_sha256=batch.identity, job=batch.m['job'],
                              registration_path=batch.reg, ledger=batch.ledger, verify=lambda: None)
    row = batch.m['audit_batches']['children'][0]
    if stops:
        # A child that fails after its paid request: stopped.json reports the display, never raises (#2551).
        def failing(argv, **kwargs):
            execute(argv, **kwargs)
            # A later request was refused, as a thinking refusal stops a child (#2561).
            refusals = Path(row['attempt_dir']) / 'thinking_refusals'; refusals.mkdir()
            (refusals / 'synthetic.json').write_text(json.dumps({'paid_request': False}))
            raise BudgetStop('synthetic child failure after its request')
        monkeypatch.setattr(native, 'execute_child', failing)
        with pytest.raises(BudgetStop):
            runtime._execute_child(context, row, 21600, clock=lambda: 0)
        stopped = json.loads((Path(row['attempt_dir']) / 'stopped.json').read_text())
        report = stopped['thinking_display']
        # The report form: a refusal is counted, where the strict form would raise and lose stopped.json.
        assert report['kind'] == 'thinking_display_summary_v1' and report['problems'] == [] and report['refusals'] == 1
        assert [r['disposition'] for r in report['requests']] == ['substituted']
        return
    runtime._execute_child(context, row, 21600, clock=lambda: 0)
    assert proxies[0].kw['thinking_display'] == THINKING_DISPLAY
    closed = json.loads((Path(row['attempt_dir']) / 'closed.json').read_text())
    assert [r['disposition'] for r in closed['thinking_display']['requests']] == ['substituted']
