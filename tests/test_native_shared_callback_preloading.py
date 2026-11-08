"""R7 historical worker scheduling, with no native process or admitted run.

The observer/classifier worker is real; minimal adapter state isolates C's
classifier body. This deliberately does not claim full observer admission.
"""
from dataclasses import FrozenInstanceError
from contextlib import ExitStack
import importlib
import queue
import sys
import threading

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_callback_orchestration as preload
from data_sheets_schema import native_shared_capture_orchestration as capture
from data_sheets_schema import native_shared_controls_orchestration as controls
from data_sheets_schema.native_shared_controller_orchestration import CallbackAdapter
from data_sheets_schema import native_shared_controller_orchestration as controller
from tests.test_native_shared_controller import (
    bound, declaration, inputs, isolated_modules, native_spec, synthetic_declaration,
)


def test_immutable_render_view_matches_real_composition(bound):
    from data_sheets_schema.native_shared_callback_capture import FrozenSpec
    _, _, raw, instruction = bound
    composition = controller.compose(raw, instruction_path=instruction)
    _, spec, _ = controller.reconstruct_composition(controller.c.canonical(composition))
    frozen = FrozenSpec.capture(spec)
    expected = controller.render.commands(spec)
    with authority.loaded_verified_package_module('data_sheets_schema.native_shared_callback_capture',
            package_sources=composition['dependencies']['base']['package_sources']) as verified:
        captured = verified.FrozenSpec(frozen.fields_json, frozen.rendered_json)
        # Deferred pure imports are loaded on the main thread, too.
        with authority.loaded_verified_package_module('data_sheets_schema.native_shared_render',
                package_sources=composition['dependencies']['base']['package_sources']) as render:
            assert render.commands(captured) == expected
        assert captured.render_spec() == composition['render_spec']
        copied = captured._agentic_artifact_paths
        copied['full'] = '/forged'
        assert captured._agentic_artifact_paths != copied
        with pytest.raises(FrozenInstanceError):
            captured.fields_json = b'{}'


def test_source_loaded_capture_worker_refuses_unminted_interface_without_loading(isolated_modules):
    """A caller-created interface cannot supply even a refusing reconstruction."""
    dependencies = authority.dependency_identity()
    pins = dependencies['base']['package_sources']
    seen = []
    def refuse(**kwargs):
        seen.append(threading.current_thread() is not threading.main_thread())
        raise ValueError('captured reconstruction deliberately refused')
    with ExitStack() as stack:
        stack.enter_context(preload.preloaded_classifier(dependencies))
        pure = stack.enter_context(authority.loaded_verified_package_module(
            'data_sheets_schema.native_shared_callback_capture', package_sources=pins))
        name = 'data_sheets_schema.native_shared_capture_orchestration'
        relative = 'src/' + name.replace('.', '/') + '.py'
        path = authority.ROOT / relative
        loaded = stack.enter_context(authority.verified_source_module(name, path=path,
            raw=authority._verified_source_bytes(path, pins[relative]), sha256=pins[relative]))
        # Frozen synthetic selection identity only: refusal precedes all reads.
        from types import SimpleNamespace
        selected = SimpleNamespace(registration=SimpleNamespace(pin=SimpleNamespace(path='/never/read')))
        admitted = pure.Admission(b'', b'', b'', b'', b'{}', selected,
            pure.FrozenSpec(b'{}', b'{}'), refuse, object(), lambda: None)
        historical = sys.modules['native_control']
        result = work(historical, 'observer', lambda: loaded._base('/never/read', _admission=admitted))
        assert type(result) is ValueError
        assert str(result) == 'callback capture was not minted by the active admission loader'
        assert seen == []
        with pytest.raises(FrozenInstanceError):
            admitted.rebuild = lambda **kwargs: {}


def test_callback_create_once_matches_existing_writer_and_never_overwrites(tmp_path):
    from data_sheets_schema import native_shared_callback_io as current
    from data_sheets_schema.native_attempt_supervisor import durable_new
    from data_sheets_schema.native_execution import _mkdir_durable
    for name, mkdir, write in (('old', _mkdir_durable, durable_new),
                               ('new', current._mkdir_durable, current.durable_new)):
        folder = tmp_path / name / 'nested'
        mkdir(folder)
        target = folder / 'evidence.json'
        write(target, b'{"fixed":true}')
        with pytest.raises(FileExistsError):
            write(target, b'changed')
        assert target.read_bytes() == b'{"fixed":true}'
        assert folder.stat().st_mode & 0o777 == 0o700


def test_callback_journal_cas_checks_actual_bytes_before_replacement(tmp_path):
    from data_sheets_schema import native_shared_callback_io as io
    from data_sheets_schema import native_shared_contract as c
    from data_sheets_schema.native_shared_evidence import read_regular
    target = tmp_path / 'journal.json'
    target.write_bytes(b'old')
    before = read_regular(str(target), 'journal', max_bytes=100).captured
    raw = b'new'
    after = c.CapturedArtifact(c.ArtifactPin('journal', str(target), len(raw), c.sha(raw)), raw)
    assert io._replace_journal(target, before, after).captured == after
    with pytest.raises(ValueError, match='journal changed before'):
        io._replace_journal(target, before, after)
    assert target.read_bytes() == raw


def test_worker_late_package_import_is_refused_by_capture_guard(isolated_modules):
    dependencies = authority.dependency_identity()
    with preload.preloaded_classifier(dependencies):
        result = work(sys.modules['native_control'], 'observer',
            lambda: importlib.import_module('data_sheets_schema.not_preloaded_r7_probe'))
        assert type(result) is ValueError
        assert str(result) == ('native callback cannot load module '
            'data_sheets_schema.not_preloaded_r7_probe; preload on the main thread at admission')


def test_captured_input_pin_is_rechecked_before_reconstruction(tmp_path):
    path = tmp_path / 'input'
    path.write_bytes(b'admitted')
    check = preload._SourceCheck(((str(path), controller.c.sha(b'admitted')),), ())
    check()
    path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='differ from their pin'):
        check()


def work(historical, kind, callback):
    worker = object.__new__(historical.NativeControl)
    worker._stopped = threading.Event()
    worker._publication_lock = threading.Lock()
    worker._active_work = None
    worker._work_replies = queue.Queue(maxsize=1)
    worker._start_work(kind, None, callback)
    worker._work_thread.join(timeout=10)
    assert not worker._work_thread.is_alive()
    _, result = worker._work_replies.get_nowait()
    return result


@pytest.mark.parametrize('kind', ['observer', 'classifier'])
def test_historical_worker_runs_preloaded_c_classifier(kind, bound):
    _, _, raw, instruction = bound
    composition = controller.compose(raw, instruction_path=instruction)
    dependencies = composition['dependencies']
    with preload.preloaded_classifier(dependencies) as selected:
        historical = sys.modules['native_control']
        adapter = object.__new__(CallbackAdapter)
        adapter.failure = None
        adapter.policy = composition['policy']
        adapter._classifier = selected
        expected = adapter.classify('pwd', sys.executable, set(), adapter.policy)
        actual = work(historical, kind,
            lambda: adapter.classify('pwd', sys.executable, set(), adapter.policy))
        assert not isinstance(actual, BaseException), repr(actual)
        assert actual == expected
        assert actual[0] == 'not_prescribed'


@pytest.mark.parametrize('kind', ['observer', 'classifier'])
@pytest.mark.parametrize('operation', ['controls', 'captures', 'preload'])
def test_worker_load_refused_before_dependency_or_capture_effects(kind, operation, monkeypatch, isolated_modules):
    dependencies = authority.dependency_identity()
    with authority.loaded_dependencies(dependencies):
        historical = sys.modules['native_control']
        def forbidden(*args, **kwargs):
            pytest.fail('worker refusal occurred after an effect')
        with monkeypatch.context() as patch:
            patch.setattr(authority, 'dependency_identity', forbidden)
            patch.setattr(capture, '_Reader', forbidden)
            if operation == 'controls':
                def invoke():
                    with controls.loaded_controls():
                        forbidden()
            elif operation == 'captures':
                invoke = lambda: capture._base('/never/read')
            else:
                def invoke():
                    with preload.preloaded_classifier(dependencies):
                        forbidden()
            result = work(historical, kind, invoke)
        assert type(result) is ValueError
        noun = 'controls' if operation == 'controls' else 'captures'
        assert str(result) == f'native callback cannot load {noun}; preload on the main thread at admission'


def test_preloaded_identity_cannot_be_rebound_and_expires(isolated_modules):
    with preload.preloaded_classifier(authority.dependency_identity()) as selected:
        adapter = object.__new__(CallbackAdapter)
        adapter._classifier = selected
        with pytest.raises(AttributeError, match='cannot be replaced'):
            adapter._classifier = object()
        with pytest.raises(AttributeError, match='cannot be removed'):
            del adapter._classifier
        with pytest.raises(FrozenInstanceError):
            selected._controls = {}
        with pytest.raises(FrozenInstanceError):
            selected._classify.function = lambda *args: ('prescribed', 'forged')
        module = selected._classify.module
        original = module.classify_bash
        try:
            module.classify_bash = lambda *args, **kwargs: ('prescribed', 'forged')
            with pytest.raises(ValueError, match='callable code changed'):
                selected.classify('pwd', sys.executable, set(), {'python': sys.executable})
        finally:
            module.classify_bash = original
    with pytest.raises(ValueError, match='active loader'):
        selected.classify('pwd', sys.executable, set(), {'python': sys.executable})
