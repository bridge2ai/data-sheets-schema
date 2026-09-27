"""Evaluation's own thinking display (#2541): one per registration, never inherited; stubs only."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native
import prepare_evaluation as prepare
import registration as reg
import run_evaluation as runner
from budgeted_cborg import BudgetStop
from native_proxy import THINKING_DISPLAY
from test_prepare_evaluation import accepted_fixture  # noqa: F401  (fixture)
from test_registration import registered  # noqa: F401  (fixture)

VERSION = '2.1.272 (Claude Code)'


def test_the_runtime_selection_is_exact_and_version_pinned():
    runtime = {'version': VERSION}
    prepare._select_thinking_display(runtime, None)
    assert 'thinking_display' not in runtime
    prepare._select_thinking_display(runtime, dict(THINKING_DISPLAY))
    assert runtime['thinking_display'] == THINKING_DISPLAY
    for value, version in ((None, VERSION), ({**THINKING_DISPLAY, 'delivery': 'cli_flag'}, VERSION),
                           (dict(THINKING_DISPLAY), '2.1.273 (Claude Code)')):
        with pytest.raises(BudgetStop):
            reg.evaluation_thinking_display({'native_runtime': {'version': version, 'thinking_display': value}})


@pytest.mark.parametrize('selected', [False, True])
def test_every_native_job_carries_the_one_selected_display(accepted_fixture, selected):
    if selected:
        accepted_fixture['native_thinking_display'] = dict(THINKING_DISPLAY)
    result = prepare.build_registration(**accepted_fixture)
    manifest = reg.read_json(result['registration'])
    native_jobs = [job for job in manifest['evaluation_jobs'] if job['style'] in reg.NATIVE_STYLES]
    assert native_jobs and all(('thinking_display' in job['native_runtime']) is selected for job in native_jobs)
    assert all('thinking_display' not in job.get('native_runtime', {}) for job in manifest['evaluation_jobs']
               if job['style'] not in reg.NATIVE_STYLES)
    reg.verify_manifest(manifest, result['registration'], reg.sha(result['registration']))


def test_a_malformed_selection_is_refused_before_the_destination_exists(accepted_fixture):
    accepted_fixture['native_thinking_display'] = {**THINKING_DISPLAY, 'display': 'omitted'}
    with pytest.raises(BudgetStop, match='thinking_display_v1'):
        prepare.build_registration(**accepted_fixture)
    assert not accepted_fixture['destination'].exists()


@pytest.mark.parametrize('change, match', [('drop_one', 'different thinking displays'), ('null', 'thinking_display_v1'),
                                           ('drop_field_agent', 'different thinking displays')])
def test_registration_refuses_mixed_or_null_displays(accepted_fixture, change, match):
    """Every native style counts: a field_agent job that differs from the semantic_agent jobs
    is one registration carrying two conditions (#2684)."""
    accepted_fixture['native_thinking_display'] = dict(THINKING_DISPLAY)
    result = prepare.build_registration(**accepted_fixture)
    manifest = reg.read_json(result['registration'])
    native_jobs = [job for job in manifest['evaluation_jobs'] if job['style'] in reg.NATIVE_STYLES]
    if change == 'drop_one':
        del native_jobs[-1]['native_runtime']['thinking_display']
    elif change == 'drop_field_agent':
        field = [job for job in native_jobs if job['style'] == 'field_agent']
        assert field and any(job['style'] == 'semantic_agent' for job in native_jobs)
        del field[0]['native_runtime']['thinking_display']
    else:
        native_jobs[0]['native_runtime']['thinking_display'] = None
    with pytest.raises(BudgetStop, match=match):
        reg.verify_manifest(manifest, result['registration'], reg.sha(result['registration']))


@pytest.mark.parametrize('change, match', [
    ('malformed', 'must be thinking_display_v1, summarized, proxy_substitution'),
    ('unregistered_runtime', 'registered only for Claude Code 2.1.272'),
])
def test_registration_refuses_one_bad_display_shared_by_every_native_job(accepted_fixture, change, match):
    """#2648: verify_manifest validates the display itself, not only that the jobs agree:
    every native job carrying the same malformed display, or a valid one on a runtime it is
    not registered for, is refused before any attempt exists."""
    accepted_fixture['native_thinking_display'] = dict(THINKING_DISPLAY)
    result = prepare.build_registration(**accepted_fixture)
    manifest = reg.read_json(result['registration'])
    native_jobs = [job for job in manifest['evaluation_jobs'] if job['style'] in reg.NATIVE_STYLES]
    assert native_jobs
    for job in native_jobs:
        if change == 'malformed':
            job['native_runtime']['thinking_display'] = {**THINKING_DISPLAY, 'delivery': 'cli_flag'}
        else:
            job['native_runtime']['version'] = '2.1.273 (Claude Code)'
    with pytest.raises(BudgetStop, match=match):
        reg.verify_manifest(manifest, result['registration'], reg.sha(result['registration']))


def write_proven(evidence, name='proven-request'):
    """What the real proxy retains for one admitted adaptive request it gave the display."""
    import hashlib
    from native_proxy import ADAPTIVE_THINKING, DISPLAYED_THINKING
    child = {'model': 'claude-opus-5', 'messages': [{'role': 'user', 'content': 'synthetic'}],
             'thinking': {'type': 'adaptive'}}
    raw = json.dumps(child, separators=(',', ':')).encode()
    forwarded = raw.replace(ADAPTIVE_THINKING, DISPLAYED_THINKING)
    folder = Path(evidence) / name
    folder.mkdir(parents=True)
    (folder / 'native_request.json').write_bytes(raw)
    (folder / 'forwarded_request.json').write_bytes(forwarded)
    (folder / 'request.json').write_text(json.dumps(json.loads(forwarded), sort_keys=True) + '\n')
    (folder / 'thinking_request.json').write_text(json.dumps({'kind': 'thinking_display_request_v1',
        'registered': THINKING_DISPLAY, 'disposition': 'substituted',
        'native_request_sha256': hashlib.sha256(raw).hexdigest(),
        'forwarded_request_sha256': hashlib.sha256(forwarded).hexdigest()}))


def _launch(manifest, job, tmp_path, monkeypatch, writes=lambda evidence: None):
    """Past the launch checks, a stand-in proxy that makes the real NativeProxy's construction
    check (#2650) and a stand-in child that leaves its evidence where the proxy was told to
    keep it (#2686). Returns the proxies built, the gate calls and their results, the context,
    and the exception raised once the gate has run."""
    monkeypatch.setattr(native, 'build_policy', lambda m, j: {})
    monkeypatch.setattr(native, 'permission_arguments', lambda policy: [])
    import instructions
    monkeypatch.setattr(instructions, 'verify_instruction', lambda m, j: None)
    monkeypatch.setattr(native, 'pinned', lambda m, p: Path(p))
    monkeypatch.setattr(native.subprocess, 'check_output', lambda *a, **kw: job['native_runtime']['version'] + '\n')
    import data_sheets_schema.agent_pin as agent_pin
    monkeypatch.setattr(agent_pin, 'spawn_preamble', lambda name: '')
    monkeypatch.setattr(native, 'provider_clients', lambda *a, **kw: (SimpleNamespace(close=lambda: None),) * 2)
    import native_proxy
    proxies, gates, proofs = [], [], []
    class Proxy:
        def __init__(self, **kwargs):
            native_proxy.validated_thinking_display(kwargs.get('thinking_display'))
            proxies.append(kwargs); self.token = 'offline'; self.unfinished_handlers = 0
            import threading; self.failed = threading.Event()
        @contextmanager
        def running(self):
            yield 'http://offline.invalid'
    monkeypatch.setattr(native, 'NativeProxy', Proxy)
    def child(*args, **kwargs):
        writes(Path(proxies[0]['evidence']))
        return 0
    monkeypatch.setattr(native, 'execute_child', child)
    real = native_proxy.thinking_display_evidence
    def gate(root, value, *, strict):
        gates.append((Path(root), strict))
        proofs.append(real(root, value, strict=strict))
        return proofs[-1]
    monkeypatch.setattr(native_proxy, 'thinking_display_evidence', gate)
    class AfterGate(Exception):
        pass
    def after(path): raise AfterGate()
    monkeypatch.setattr(native, 'load_native_events', after)
    monkeypatch.setenv('CBORG_API_KEY', 'offline-test-key')
    context = SimpleNamespace(manifest=manifest, job=job, attempt=tmp_path / 'attempt', ledger=SimpleNamespace(),
                              manifest_sha256='synthetic', verify=lambda: None)
    (tmp_path / 'attempt').mkdir()
    return proxies, gates, proofs, context, AfterGate


@pytest.mark.parametrize('selected, outcome', [(False, 'proven'), (True, 'proven'), (True, 'unproven'), (True, 'refused')])
def test_the_evaluator_proxy_gets_the_display_and_the_gate_runs(accepted_fixture, tmp_path, monkeypatch, selected, outcome):
    """Past the launch checks, a stand-in proxy and child; the strict gate must run on completion,
    and a proof it cannot make stops the job before its transcript is read (#2594). The gate
    reads the directory the proxy keeps its evidence in, and a proven request is proven (#2686)."""
    if selected:
        accepted_fixture['native_thinking_display'] = dict(THINKING_DISPLAY)
    result = prepare.build_registration(**accepted_fixture)
    manifest = reg.read_json(result['registration'])
    job = next(j for j in manifest['evaluation_jobs'] if j['style'] == 'semantic_agent')
    def writes(evidence):
        # What a real run leaves: an admitted request proven or not, or a refusal beside them.
        if outcome == 'proven' and selected:
            write_proven(evidence)
        elif outcome == 'unproven':
            (evidence / 'unproven-request').mkdir(parents=True)
        elif outcome == 'refused':
            (evidence.parent / 'thinking_refusals').mkdir()
            (evidence.parent / 'thinking_refusals' / 'synthetic.json').write_text('{}\n')
    proxies, gates, proofs, context, AfterGate = _launch(manifest, job, tmp_path, monkeypatch, writes)
    if outcome == 'proven':
        with pytest.raises(AfterGate):
            native.execute_job(context)
    else:
        match = 'unproven-request is not proven' if outcome == 'unproven' else 'refused thinking setting'
        with pytest.raises(BudgetStop, match=match):
            native.execute_job(context)
    assert ('thinking_display' in proxies[0]) is selected
    assert proxies[0].get('thinking_display') == (THINKING_DISPLAY if selected else None)       # #2650
    assert gates == ([(tmp_path / 'attempt' / 'requests', True)] if selected else [])
    if selected:
        assert Path(proxies[0]['evidence']) == gates[0][0]                                          # #2686
    if selected and outcome == 'proven':
        assert [request['id'] for request in proofs[0]['requests']] == ['proven-request']


@pytest.mark.parametrize('composite', ['displayed'], indirect=True)
@pytest.mark.parametrize('selected', [False, True])
def test_the_composite_evaluator_launches_with_only_its_own_selection(composite, tmp_path, monkeypatch, selected):
    """#2683: at run time, not only in the registration, the evaluator of a pair whose Phase 4
    selected a display gets one only when evaluation selects it."""
    from test_source_pair import build
    assert reg.read_json(composite['finalization_registration'])['native_thinking_display'] == THINKING_DISPLAY
    if selected:
        composite['native_thinking_display'] = dict(THINKING_DISPLAY)
    manifest = reg.read_json(build(composite)['registration'])
    assert manifest.get('schema_version') == 2 and 'source_pair' in manifest
    job = next(j for j in manifest['evaluation_jobs'] if j['style'] == 'semantic_agent')
    proxies, gates, proofs, context, AfterGate = _launch(manifest, job, tmp_path, monkeypatch)
    with pytest.raises(AfterGate):
        native.execute_job(context)
    assert ('thinking_display' in proxies[0]) is selected
    assert proxies[0].get('thinking_display') == (THINKING_DISPLAY if selected else None)
    assert len(gates) == int(selected)


@pytest.mark.parametrize('style, displayed, admitted', [
    ('semantic_agent', True, False), ('semantic_agent', True, True),
    ('semantic_agent', False, True), ('grounding', True, True), ('field_agent', True, True)],
    ids=['native-nothing-admitted', 'native-unproven-request', 'native-no-display', 'api-job', 'field-agent'])
def test_the_evaluation_receipt_reports_a_native_jobs_display(registered, monkeypatch, style, displayed, admitted):
    """Validation stubs hand back the job; the receipt code is the real one.

    Only a native job's own display is reported (#2599). A stop after a request whose display
    is not proven still writes the receipt, reports it and keeps the stop's reason (#2595)."""
    manifest, path, review, _ = registered
    job = deepcopy(manifest['evaluation_jobs'][0])
    job.update(style=style, native_runtime={'version': VERSION,
                                            **({'thinking_display': dict(THINKING_DISPLAY)} if displayed else {})})
    monkeypatch.setattr(runner, 'verify_manifest', lambda *args: {job['id']: job})
    monkeypatch.setattr(runner, 'verify_dependencies', lambda *args: (job, {}))
    def stops(context):
        if admitted:
            folder = context.attempt / 'requests' / 'synthetic-request'
            folder.mkdir(parents=True)
            (folder / 'request.json').write_text('{"synthetic": true}\n')
        raise BudgetStop('synthetic evaluator stop')
    with pytest.raises(BudgetStop, match='synthetic evaluator stop'):
        runner.run_job(path, review, job['id'], adapter=stops)
    receipt = reg.read_json(Path(manifest['attempts_dir']) / job['id'] / 'result.json')
    assert receipt['status'] == 'stopped' and receipt['reason'] == 'synthetic evaluator stop'
    if style not in reg.NATIVE_STYLES or not displayed:
        assert 'thinking_display' not in receipt
        return
    assert receipt['thinking_display']['kind'] == 'thinking_display_summary_v1'
    assert receipt['thinking_display']['registered'] == THINKING_DISPLAY
    assert [p['id'] for p in receipt['thinking_display']['problems']] == (['synthetic-request'] if admitted else [])


@pytest.mark.parametrize('style', ['semantic_agent', 'field_agent'])
def test_a_completed_evaluation_receipt_reports_the_display(registered, monkeypatch, style):
    """#2685: the summary is written for a completed run too, not only for a stop; for every
    native style (#2684)."""
    from test_registration import fake_adapter
    manifest, path, review, _ = registered
    job = deepcopy(manifest['evaluation_jobs'][0])
    job.update(style=style, native_runtime={'version': VERSION, 'thinking_display': dict(THINKING_DISPLAY)})
    monkeypatch.setattr(runner, 'verify_manifest', lambda *args: {job['id']: job})
    monkeypatch.setattr(runner, 'verify_dependencies', lambda *args: (job, {}))
    receipt = runner.run_job(path, review, job['id'], adapter=fake_adapter)
    stored = reg.read_json(Path(manifest['attempts_dir']) / job['id'] / 'result.json')
    assert receipt['status'] == stored['status'] == 'completed_pending_independent_review'
    assert stored['thinking_display'] == {'kind': 'thinking_display_summary_v1', 'registered': THINKING_DISPLAY,
                                          'requests': [], 'problems': [], 'refusals': 0}


@pytest.mark.parametrize('composite', ['displayed'], indirect=True)
@pytest.mark.parametrize('selected', [False, True])
def test_the_composite_path_carries_only_its_own_selection(composite, selected):
    """The path the accepted native pair takes: evaluation prepared from a Phase 4 that selected
    a display. Evaluation's jobs carry one only when evaluation selects it (#2541, #2592)."""
    from test_source_pair import build
    assert reg.read_json(composite['finalization_registration'])['native_thinking_display'] == THINKING_DISPLAY
    if selected:
        composite['native_thinking_display'] = dict(THINKING_DISPLAY)
    result = build(composite)
    m = reg.read_json(result['registration'])
    native_jobs = [job for job in m['evaluation_jobs'] if job['style'] in reg.NATIVE_STYLES]
    assert native_jobs
    for job in native_jobs:
        assert ('thinking_display' in job['native_runtime']) is selected
        if selected:
            assert job['native_runtime']['thinking_display'] == THINKING_DISPLAY
    assert 'native_thinking_display' not in m
    reg.verify_manifest(m, result['registration'], reg.sha(result['registration']))


@pytest.mark.parametrize('value, runtimes, match', [
    ({**THINKING_DISPLAY, 'display': 'omitted'}, None, 'thinking_display_v1'),
    (None, frozenset({'another-native-version'}), '2.1.272')], ids=['malformed', 'unregistered_runtime'])
def test_the_composite_preparer_refuses_before_the_destination_exists(composite, monkeypatch, value, runtimes, match):
    """#2598: as the legacy preparer does."""
    from test_source_pair import build
    from audit_controls import registration as audit_registration
    if runtimes is not None:
        monkeypatch.setattr(audit_registration, 'THINKING_DISPLAY_RUNTIMES', runtimes)
    composite['native_thinking_display'] = value or dict(THINKING_DISPLAY)
    with pytest.raises(BudgetStop, match=match):
        build(composite)
    assert not composite['destination'].exists()


def test_the_legacy_preparer_refuses_an_unregistered_runtime_before_the_destination_exists(accepted_fixture, monkeypatch):
    """The version checked is the snapshot's own: an unregistered one is refused before anything is written."""
    real = prepare.runtime_snapshot
    monkeypatch.setattr(prepare, 'runtime_snapshot', lambda executable=None: {**real(executable),
                                                                               'version': '2.1.273 (Claude Code)'})
    accepted_fixture['native_thinking_display'] = dict(THINKING_DISPLAY)
    with pytest.raises(BudgetStop, match='2.1.272'):
        prepare.build_registration(**accepted_fixture)
    assert not accepted_fixture['destination'].exists()


LEGACY_CLI = ['--generation-registration', 'g.json', '--generation-acceptance', 'a.json', '--generation-job-id', 'job',
              '--billing-checkpoint', 'b.json']
COMPOSITE_CLI = ['--finalization-registration', 'f.json', '--finalization-acceptance', 'a.json']


@pytest.mark.parametrize('route', ['legacy', 'composite'])
@pytest.mark.parametrize('selected', [False, True])
def test_the_evaluation_cli_delivers_the_exact_selection_or_none(route, selected, tmp_path, monkeypatch, capsys):
    """#2596: both documented routes, `prepare_evaluation --native-thinking-display summarized`."""
    calls = []
    def collect(*args, **kwargs):
        calls.append(kwargs); return {'registration': tmp_path / 'registration.json', 'report': {}}
    monkeypatch.setattr(prepare, 'build_registration' if route == 'legacy' else 'build_composite_registration', collect)
    monkeypatch.setattr(prepare, 'build_composite_registration' if route == 'legacy' else 'build_registration',
                        lambda *a, **k: pytest.fail('the other route was taken'))
    argv = ['prepare_evaluation', '--destination', str(tmp_path / 'evaluation'), '--context-path', 'c.json',
            *(LEGACY_CLI if route == 'legacy' else COMPOSITE_CLI)]
    monkeypatch.setattr(sys, 'argv', argv + (['--native-thinking-display', 'summarized'] if selected else []))
    assert prepare.main() == 0
    assert calls[0]['native_thinking_display'] == (THINKING_DISPLAY if selected else None)


@pytest.mark.parametrize('route', ['legacy', 'composite'])
def test_the_evaluation_cli_refuses_any_other_display(route, tmp_path, monkeypatch, capsys):
    for name in ('build_registration', 'build_composite_registration'):
        monkeypatch.setattr(prepare, name, lambda *a, **k: pytest.fail('prepared with an unregistered display'))
    monkeypatch.setattr(sys, 'argv', ['prepare_evaluation', '--destination', str(tmp_path / 'evaluation'),
                                      '--context-path', 'c.json', *(LEGACY_CLI if route == 'legacy' else COMPOSITE_CLI),
                                      '--native-thinking-display', 'omitted'])
    with pytest.raises(SystemExit) as stop:
        prepare.main()
    assert stop.value.code == 2 and 'invalid choice' in capsys.readouterr().err


from test_source_pair import composite  # noqa: E402,F401  (fixture)
