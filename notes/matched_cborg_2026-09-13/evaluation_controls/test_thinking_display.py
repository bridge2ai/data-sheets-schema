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


@pytest.mark.parametrize('change, match', [('drop_one', 'different thinking displays'), ('null', 'thinking_display_v1')])
def test_registration_refuses_mixed_or_null_displays(accepted_fixture, change, match):
    accepted_fixture['native_thinking_display'] = dict(THINKING_DISPLAY)
    result = prepare.build_registration(**accepted_fixture)
    manifest = reg.read_json(result['registration'])
    native_jobs = [job for job in manifest['evaluation_jobs'] if job['style'] in reg.NATIVE_STYLES]
    if change == 'drop_one':
        del native_jobs[-1]['native_runtime']['thinking_display']
    else:
        native_jobs[0]['native_runtime']['thinking_display'] = None
    with pytest.raises(BudgetStop, match=match):
        reg.verify_manifest(manifest, result['registration'], reg.sha(result['registration']))


@pytest.mark.parametrize('selected', [False, True])
def test_the_evaluator_proxy_gets_the_display_and_the_gate_runs(accepted_fixture, tmp_path, monkeypatch, selected):
    """Past the launch checks, a stand-in proxy and child; the strict gate must run on completion."""
    if selected:
        accepted_fixture['native_thinking_display'] = dict(THINKING_DISPLAY)
    result = prepare.build_registration(**accepted_fixture)
    manifest = reg.read_json(result['registration'])
    job = next(j for j in manifest['evaluation_jobs'] if j['style'] == 'semantic_agent')
    monkeypatch.setattr(native, 'build_policy', lambda m, j: {})
    monkeypatch.setattr(native, 'permission_arguments', lambda policy: [])
    import instructions
    monkeypatch.setattr(instructions, 'verify_instruction', lambda m, j: None)
    monkeypatch.setattr(native, 'pinned', lambda m, p: Path(p))
    monkeypatch.setattr(native.subprocess, 'check_output', lambda *a, **kw: job['native_runtime']['version'] + '\n')
    import data_sheets_schema.agent_pin as agent_pin
    monkeypatch.setattr(agent_pin, 'spawn_preamble', lambda name: '')
    monkeypatch.setattr(native, 'provider_clients', lambda *a, **kw: (SimpleNamespace(close=lambda: None),) * 2)
    proxies, gates = [], []
    class Proxy:
        def __init__(self, **kwargs):
            proxies.append(kwargs); self.token = 'offline'; self.unfinished_handlers = 0
            import threading; self.failed = threading.Event()
        @contextmanager
        def running(self):
            yield 'http://offline.invalid'
    monkeypatch.setattr(native, 'NativeProxy', Proxy)
    monkeypatch.setattr(native, 'execute_child', lambda *a, **kw: 0)
    import native_proxy
    monkeypatch.setattr(native_proxy, 'thinking_display_evidence',
                        lambda root, value, *, strict: gates.append((Path(root), strict)))
    class AfterGate(Exception):
        pass
    def after(path): raise AfterGate()
    monkeypatch.setattr(native, 'load_native_events', after)
    monkeypatch.setenv('CBORG_API_KEY', 'offline-test-key')
    context = SimpleNamespace(manifest=manifest, job=job, attempt=tmp_path / 'attempt', ledger=SimpleNamespace(),
                              manifest_sha256='synthetic', verify=lambda: None)
    (tmp_path / 'attempt').mkdir()
    with pytest.raises(AfterGate):
        native.execute_job(context)
    assert ('thinking_display' in proxies[0]) is selected
    assert gates == ([(tmp_path / 'attempt' / 'requests', True)] if selected else [])


def test_the_evaluation_receipt_reports_a_native_jobs_display(registered, monkeypatch):
    """Validation stubs hand back a native job with a display; the receipt code is the real one."""
    manifest, path, review, _ = registered
    job = deepcopy(manifest['evaluation_jobs'][0])
    job.update(style='semantic_agent', native_runtime={'version': VERSION, 'thinking_display': dict(THINKING_DISPLAY)})
    monkeypatch.setattr(runner, 'verify_manifest', lambda *args: {job['id']: job})
    monkeypatch.setattr(runner, 'verify_dependencies', lambda *args: (job, {}))
    def stops(context):
        raise BudgetStop('synthetic evaluator stop')
    with pytest.raises(BudgetStop):
        runner.run_job(path, review, job['id'], adapter=stops)
    receipt = reg.read_json(Path(manifest['attempts_dir']) / job['id'] / 'result.json')
    assert receipt['thinking_display']['kind'] == 'thinking_display_summary_v1'
    assert receipt['thinking_display']['registered'] == THINKING_DISPLAY


def test_the_composite_path_carries_the_selection_to_every_native_job(composite, monkeypatch):
    """The path the accepted native pair takes: evaluation prepared from Phase 4 (#2541)."""
    from test_source_pair import build
    from audit_controls import registration as audit_registration
    version = composite['phase']['native_runtime']['version']
    monkeypatch.setattr(audit_registration, 'THINKING_DISPLAY_RUNTIMES', frozenset({version}))
    composite['native_thinking_display'] = dict(THINKING_DISPLAY)
    result = build(composite)
    m = reg.read_json(result['registration'])
    native_jobs = [job for job in m['evaluation_jobs'] if job['style'] in reg.NATIVE_STYLES]
    assert native_jobs and all(job['native_runtime']['thinking_display'] == THINKING_DISPLAY for job in native_jobs)
    reg.verify_manifest(m, result['registration'], reg.sha(result['registration']))
    # Phase 4's own display, if any, is not what selects this one: absent here unless selected.
    assert 'thinking_display' not in composite['phase']['native_runtime']


from test_source_pair import composite  # noqa: E402,F401  (fixture)
