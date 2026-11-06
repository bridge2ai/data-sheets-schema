"""Focused offline R8 tests; synthetic code only, never a recorder/native run."""
import importlib.util
import json
from pathlib import Path
import signal
import sys
import threading
import time

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/adhoc/native_recorder_thread_cpu_20261106.py'
SPEC = importlib.util.spec_from_file_location('r8_thread_observer', SCRIPT)
observer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observer)


def load(path, name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, monkeypatch, *, interval=5, phases=None, checker=None):
    if not hasattr(sys, 'monitoring'):
        pytest.skip('requires sys.monitoring')
    root = tmp_path / 'source'
    path = root / 'src/data_sheets_schema/provenance.py'
    path.parent.mkdir(parents=True)
    path.write_text('''import time
def work(seconds, background_done=None, refuse=False):
    before = time.thread_time()
    if background_done is not None:
        background_done.wait(timeout=3)
    while time.thread_time() - before < seconds:
        sum(i * i for i in range(200))
    if refuse:
        raise ValueError("unchanged synthetic refusal")
    return time.thread_time() - before
def recursive(depth):
    return 1 + recursive(depth - 1) if depth else 0
''')
    parser = tmp_path / 'yaml_fixture.py'
    parser.write_text('''class SafeLoader: pass
def parse(stream, Loader=SafeLoader):
    for character in stream:
        yield character
''')
    monkeypatch.setattr(observer.base.Observer, '_origins', lambda self: [])
    monkeypatch.setattr(observer.base, 'process_age', lambda: {'seconds': 0, 'method': 'synthetic'})
    seen = observer.ThreadCPUObserver(root, tmp_path / 'evidence',
        phases=phases or {'provenance': {'work': 'work', 'recursive': 'recursion'}},
        cache_targets={}, parser_path=parser, checkpoint_seconds=interval,
        closure_checker=checker or (lambda root: {'verified': True, 'root': str(root)}))
    return seen, path, parser


def events(seen):
    return [json.loads(line) for line in (seen.output / 'observer.jsonl').read_text().splitlines()]


def test_late_exec_binds_without_eager_import_global_calls_or_replacement(tmp_path, monkeypatch):
    seen, path, _ = fixture(tmp_path, monkeypatch)
    before_tools = [sys.monitoring.get_tool(i) for i in range(6)]
    try:
        seen.start(arm_trace=False, periodic=False)
        assert not seen.bound_targets
        assert sys.monitoring.get_events(seen.tool) == sys.monitoring.events.PY_UNWIND
        module = load(path, 'r8_late', monkeypatch)
        original = module.work
        assert module.work(0.002) > 0
        assert module.work is original
        assert module.recursive(4) == 4
        with pytest.raises(ValueError, match='unchanged synthetic refusal'):
            module.work(0.001, refuse=True)
    finally:
        seen.close()
    assert seen.valid
    assert seen.stats['provenance:work']['calls'] == 2
    assert seen.stats['provenance:work']['returns'] == 1
    assert seen.stats['provenance:work']['unwinds'] == 1
    assert seen.stats['provenance:recursive']['calls'] == 5
    assert not seen.active
    assert [sys.monitoring.get_tool(i) for i in range(6)] == before_tools
    rows = events(seen)
    assert rows[0]['source_closure']['verified']
    assert rows[-1]['event'] == 'observer_end' and rows[-1]['valid']


def test_owner_thread_clock_excludes_background_cpu_and_monitored_foreign_calls(tmp_path, monkeypatch):
    seen, path, _ = fixture(tmp_path, monkeypatch, interval=0.01)
    background_done = threading.Event()
    background_cpu = []
    thread = None
    try:
        seen.start(arm_trace=False)
        module = load(path, 'r8_threads', monkeypatch)
        def background():
            before = time.thread_time()
            module.work(0.08)
            background_cpu.append(time.thread_time() - before)
            background_done.set()
        thread = threading.Thread(target=background)
        thread.start()
        outer = time.thread_time_ns()
        measured_body = module.work(0.02, background_done)
        outer = time.thread_time_ns() - outer
        thread.join(timeout=3)
        assert not thread.is_alive()
        assert background_cpu[0] >= 0.08
        assert measured_body >= 0.02
    finally:
        if thread is not None:
            thread.join(timeout=3)
        seen.close()
    assert seen.valid
    stats = seen.stats['provenance:work']
    assert stats['calls'] == stats['returns'] == 1
    assert 15_000_000 <= stats['inclusive_thread_cpu_ns'] <= outer + 5_000_000
    assert stats['inclusive_thread_cpu_ns'] < 70_000_000
    assert seen.non_owner_events['start:provenance:work'] == 1
    rows = events(seen)
    checkpoints = [row for row in rows if row['event'] == 'thread_cpu_checkpoint' and row['reason'] == 'owner_timer']
    assert checkpoints and all(row['owner_thread'] == seen.owner_thread for row in checkpoints)
    assert any(row['active_phases'] for row in checkpoints)
    assert signal.getsignal(signal.SIGALRM) is signal.SIG_DFL
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)


def test_parser_generator_counts_started_calls_once_not_resumptions_or_other_threads(tmp_path, monkeypatch):
    seen, _, parser = fixture(tmp_path, monkeypatch)
    try:
        seen.start(arm_trace=False, periodic=False)
        module = load(parser, 'yaml', monkeypatch)
        assert list(module.parse('abcd', Loader=module.SafeLoader)) == list('abcd')
        thread = threading.Thread(target=lambda: list(module.parse('xyz')))
        thread.start(); thread.join(timeout=3)
        assert not thread.is_alive()
        generator = module.parse('unfinished')
        next(generator)
        generator.close()
    finally:
        seen.close()
    assert seen.valid
    stats = seen.stats['yaml:parse']
    assert stats['calls'] == 2 and stats['returns'] == 1 and stats['unwinds'] == 1
    assert stats['inclusive_thread_cpu_ns'] == 0
    assert stats['counters']['safe_loader_started'] == 2
    assert seen.document_counts['yaml:parse_started']['calls'] == 2
    assert seen.non_owner_events['start:yaml:parse'] == 1


def test_loaded_code_binds_and_foreign_filename_never_enters_roster(tmp_path, monkeypatch):
    seen, path, _ = fixture(tmp_path, monkeypatch)
    module = load(path, 'r8_preloaded', monkeypatch)
    foreign = {}
    exec(compile(path.read_bytes(), str(tmp_path / 'foreign.py'), 'exec'), foreign)
    try:
        seen.start(arm_trace=False, periodic=False)
        module.work(0.001)
        foreign['work'](0.001)
        with pytest.raises(ValueError, match='unchanged synthetic refusal'):
            foreign['work'](0.001, refuse=True)
    finally:
        seen.close()
    assert seen.valid and seen.stats['provenance:work']['calls'] == 1
    assert seen.stats['provenance:work']['unwinds'] == 0


def test_changed_code_using_pinned_filename_is_refused(tmp_path, monkeypatch):
    seen, path, _ = fixture(tmp_path, monkeypatch)
    try:
        seen.start(arm_trace=False, periodic=False)
        with pytest.raises(RuntimeError, match='differs from pinned source'):
            exec(compile(path.read_text().replace('return time.thread_time() - before', 'return 999'), str(path), 'exec'), {})
    finally:
        # Expected invalid diagnostic still closes its monitoring registrations.
        seen.close()
    assert not seen.valid


def test_foreign_source_closure_refuses_before_monitoring(tmp_path, monkeypatch):
    def reject(root):
        raise RuntimeError('foreign project namespace')
    seen, _, _ = fixture(tmp_path, monkeypatch, checker=reject)
    with pytest.raises(RuntimeError, match='foreign project namespace'):
        seen.start(arm_trace=False, periodic=False)
    assert seen.tool is None and not seen.started
    assert seen.closed and not seen.valid


def test_existing_timer_or_handler_is_not_replaced(tmp_path, monkeypatch):
    seen, _, _ = fixture(tmp_path, monkeypatch)
    old = signal.getsignal(signal.SIGALRM)
    sentinel = lambda *_: None
    try:
        signal.signal(signal.SIGALRM, sentinel)
        with pytest.raises(RuntimeError, match='existing alarm'):
            seen.start(arm_trace=False)
        assert signal.getsignal(signal.SIGALRM) is sentinel
    finally:
        signal.signal(signal.SIGALRM, old)
        seen.close()


def test_default_phase_roster_excludes_generators_and_includes_causal_targets():
    assert 'captured_view' not in observer.PHASES.get('schema_view', {})
    assert 'RecordValidationPlugin.process' not in observer.PHASES.get('record_schema', {})
    assert {'_rebuild', '_schemas'} <= set(observer.PHASES['native_shared_selection'])
    assert '_capture_native_schema' in observer.PHASES['schema_snapshot']
    assert {'_mapping', '_load_yaml', '_schema_yaml'} <= set(observer.PHASES['audit_omissions'])


def test_treatment_counters_are_passive_source_bound_primitive_reads(tmp_path, monkeypatch):
    seen, _, _ = fixture(tmp_path, monkeypatch)
    path = seen.root / 'src/data_sheets_schema/native_schema_event_reuse.py'
    path.write_text('from collections import OrderedDict\n_COUNTERS = {"documents": 3, "hits": 2}\n_CACHE = OrderedDict()\n_BYTES = 7\n_EVENTS = 9\n')
    seen.optional_treatment_pin = observer.base._pin(path)
    assert seen._treatment_counters() == {'state': 'not_loaded', 'present_in_source': True}
    module = load(path, 'data_sheets_schema.native_schema_event_reuse', monkeypatch)
    try:
        result = seen._treatment_counters()
        assert result['state'] == 'loaded' and result['counters'] == {'documents': 3, 'hits': 2}
        assert result['entries'] == 0 and result['_BYTES'] == 7 and result['_EVENTS'] == 9
        assert module._COUNTERS == {'documents': 3, 'hits': 2} and not module._CACHE
        module._BYTES = 'wrong'
        with pytest.raises(RuntimeError, match='bound counter changed shape'):
            seen._treatment_counters()
        module._BYTES = 7
        monkeypatch.setattr(module, '__file__', str(tmp_path / 'foreign.py'))
        with pytest.raises(RuntimeError, match='not the pinned diagnostic source'):
            seen._treatment_counters()
        monkeypatch.setattr(module, '__file__', str(path))
    finally:
        seen.close()
    assert seen.closed
