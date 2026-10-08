"""Closed profiling parent boundaries with fabricated child replies, no launch.

These tests do not profile retained data or execute the fake interpreter file.
The subprocess seam records its exact invocation and returns software fixtures.
"""
from copy import deepcopy
from pathlib import Path
import subprocess
from types import ModuleType, SimpleNamespace

import pytest


DRIVER = Path(__file__).resolve().parents[1] / 'notes/native_profile_recovery_2026-10-07/trace_prefix_profile.py'


@pytest.fixture
def profile():
    module = ModuleType('_trace_profile_runtime_test')
    module.__file__ = str(DRIVER)
    exec(compile(DRIVER.read_bytes(), str(DRIVER), 'exec'), module.__dict__)
    return module


@pytest.fixture
def parent_case(profile, tmp_path, monkeypatch):
    source, recovery = tmp_path / 'source', tmp_path / 'recovery'
    source.mkdir()
    recovery.mkdir()
    (source / 'retained.py').write_bytes(b'original pinned source fixture\n')
    (recovery / 'retained.json').write_bytes(b'{"fixture":true}\n')
    interpreter = tmp_path / 'not-an-executed-interpreter'
    interpreter.write_bytes(b'EXPLICIT SOFTWARE FIXTURE, NEVER EXECUTED\n')
    interpreter.chmod(0o700)
    alias = tmp_path / 'interpreter-alias'
    alias.symlink_to(interpreter)
    monkeypatch.setattr(profile, 'sys', SimpleNamespace(
        executable=str(alias), flags=SimpleNamespace(isolated=1, no_site=1), dont_write_bytecode=True))
    provenance = {'source_commit': 'synthetic-fixture', 'input_sha256': 'a' * 64}
    verifications = []

    def verify(selected_source, selected_recovery):
        assert selected_source == source and selected_recovery == recovery
        verifications.append(True)
        return {'provenance': deepcopy(provenance)}

    monkeypatch.setattr(profile, 'verify_inputs', verify)
    selected = profile.executable_identity(interpreter)
    worker = {'format': profile.FORMAT, 'scope': profile.SCOPE, 'status': 'measured',
        'parity_passed': True, 'scientific_eligibility': False, 'native_acceptance_passed': False,
        'historical_capture_complete': False,
        'provenance': provenance, 'driver_sha256': profile.sha(DRIVER.read_bytes()),
        'environment': {'interpreter': selected,
            'startup_flags': {'isolated': 1, 'no_site': 1, 'dont_write_bytecode': True}}}
    return SimpleNamespace(source=source, recovery=recovery, interpreter=interpreter, alias=alias,
        selected=selected, worker=worker, verifications=verifications, output=tmp_path / 'new-report')


def _returned(profile, worker, *, code=0, stderr=b''):
    return subprocess.CompletedProcess([], code, profile.canonical(worker), stderr)


def test_exact_resolved_interpreter_fixed_bound_and_flags_are_published(profile, parent_case, monkeypatch):
    case = parent_case
    calls = []

    def child(argv, **kwargs):
        calls.append((argv, kwargs))
        return _returned(profile, case.worker)

    monkeypatch.setattr(profile.subprocess, 'run', child)
    result = profile.run_profile(case.source, case.recovery, case.output)
    assert calls == [([str(case.interpreter), '-I', '-B', '-S', str(DRIVER), '--worker',
                      '--source', str(case.source), '--recovery', str(case.recovery)],
                     {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE, 'timeout': 120, 'check': False})]
    assert len(case.verifications) == 2
    assert result['selected_interpreter'] == case.selected
    assert result['environment']['interpreter'] == case.selected
    assert result['isolated_child'] is True
    assert result['child_elapsed_wall_ns'] >= 0
    assert profile.strict_json((case.output / 'report.json').read_bytes()) == result
    assert (case.source / 'retained.py').read_bytes() == b'original pinned source fixture\n'
    assert (case.recovery / 'retained.json').read_bytes() == b'{"fixture":true}\n'
    assert not list(case.source.rglob('__pycache__'))
    assert not list(case.recovery.rglob('__pycache__'))


@pytest.mark.parametrize('field', ['interpreter', 'driver', 'no_site', 'isolated', 'bytecode'])
def test_foreign_child_runtime_or_startup_identity_refuses_before_output(profile, parent_case, monkeypatch, field):
    case = parent_case
    changed = deepcopy(case.worker)
    if field == 'interpreter':
        changed['environment']['interpreter']['sha256'] = '0' * 64
    elif field == 'driver':
        changed['driver_sha256'] = '0' * 64
    else:
        key = {'no_site': 'no_site', 'isolated': 'isolated', 'bytecode': 'dont_write_bytecode'}[field]
        changed['environment']['startup_flags'][key] = False
    monkeypatch.setattr(profile.subprocess, 'run', lambda *a, **k: _returned(profile, changed))
    with pytest.raises(profile.ProfileError, match='interpreter, driver or startup identity'):
        profile.run_profile(case.source, case.recovery, case.output)
    assert not case.output.exists()


@pytest.mark.parametrize('mutation', ['bytes', 'same_bytes_replacement'])
def test_interpreter_drift_after_dispatch_is_not_attributed_to_new_bytes(profile, parent_case, monkeypatch, mutation):
    case = parent_case
    original = case.interpreter.read_bytes()

    def child(*args, **kwargs):
        if mutation == 'bytes':
            case.interpreter.write_bytes(original + b'changed\n')
        else:
            replacement = case.interpreter.with_name('replacement')
            replacement.write_bytes(original)
            replacement.chmod(0o700)
            replacement.replace(case.interpreter)
        return _returned(profile, case.worker)

    monkeypatch.setattr(profile.subprocess, 'run', child)
    with pytest.raises(profile.ProfileError, match='selected interpreter changed'):
        profile.run_profile(case.source, case.recovery, case.output)
    assert not case.output.exists()


def test_timeout_is_bounded_failed_diagnostic_without_partial_measurements(profile, parent_case, monkeypatch):
    case = parent_case
    calls = []

    def timeout(argv, **kwargs):
        calls.append(kwargs)
        raise subprocess.TimeoutExpired(argv, kwargs['timeout'], output=b'partial unaccepted measurement')

    monkeypatch.setattr(profile.subprocess, 'run', timeout)
    result = profile.run_profile(case.source, case.recovery, case.output)
    assert calls[0]['timeout'] == 120
    assert len(case.verifications) == 2
    assert result['status'] == 'diagnostic_timeout' and result['parity_passed'] is False
    assert result['scientific_eligibility'] is False and result['native_acceptance_passed'] is False
    assert result['historical_capture_complete'] is False
    assert result['selected_interpreter'] == case.selected
    assert 'prefixes' not in result and 'environment' not in result
    assert b'partial unaccepted' not in (case.output / 'report.json').read_bytes()


@pytest.mark.parametrize('problem', ['nonzero', 'stderr', 'excess_output', 'invalid_json', 'source_drift'])
def test_worker_or_input_failure_preserves_existing_content_and_no_output(profile, parent_case, monkeypatch, problem):
    case = parent_case

    def child(*args, **kwargs):
        if problem == 'nonzero':
            return _returned(profile, case.worker, code=1)
        if problem == 'stderr':
            return _returned(profile, case.worker, stderr=b'unexpected stderr')
        if problem == 'excess_output':
            return subprocess.CompletedProcess([], 0, b'x' * (profile.MAX_REPORT_BYTES + 1), b'')
        if problem == 'invalid_json':
            return subprocess.CompletedProcess([], 0, b'{', b'')
        monkeypatch.setattr(profile, 'verify_inputs', lambda *a: {'provenance': {'changed': True}})
        return _returned(profile, case.worker)

    monkeypatch.setattr(profile.subprocess, 'run', child)
    with pytest.raises((profile.ProfileError, ValueError)):
        profile.run_profile(case.source, case.recovery, case.output)
    assert not case.output.exists()
    assert (case.source / 'retained.py').read_bytes() == b'original pinned source fixture\n'
    assert (case.recovery / 'retained.json').read_bytes() == b'{"fixture":true}\n'


@pytest.mark.parametrize('destination', ['existing', 'source_child', 'recovery_child', 'symlink_parent'])
def test_output_refusals_happen_before_dispatch(profile, parent_case, tmp_path, monkeypatch, destination):
    case = parent_case
    if destination == 'existing':
        case.output.mkdir()
        (case.output / 'keep').write_bytes(b'original output')
        output = case.output
    elif destination == 'source_child':
        output = case.source / 'new'
    elif destination == 'recovery_child':
        output = case.recovery / 'new'
    else:
        alias = tmp_path / 'parent-alias'
        alias.symlink_to(tmp_path, target_is_directory=True)
        output = alias / 'new'

    def forbidden(*args, **kwargs):
        pytest.fail('invalid output dispatched a child')

    monkeypatch.setattr(profile.subprocess, 'run', forbidden)
    with pytest.raises(profile.ProfileError):
        profile.run_profile(case.source, case.recovery, output)
    if destination == 'existing':
        assert (case.output / 'keep').read_bytes() == b'original output'


@pytest.mark.parametrize('field', ['isolated', 'no_site', 'dont_write_bytecode'])
def test_unisolated_parent_refuses_before_input_verification(profile, parent_case, field):
    if field == 'dont_write_bytecode':
        profile.sys.dont_write_bytecode = False
    else:
        setattr(profile.sys.flags, field, 0)
    with pytest.raises(profile.ProfileError, match='parent requires'):
        profile.run_profile(parent_case.source, parent_case.recovery, parent_case.output)
    assert not parent_case.verifications and not parent_case.output.exists()


@pytest.mark.parametrize('event', ['socket.__new__', 'socket.connect', 'subprocess.Popen', 'os.exec',
    'os.posix_spawn', 'os.system', 'os.fork', 'ctypes.dlopen', 'os.mkdir', 'os.remove', 'os.rename', 'os.symlink'])
def test_effect_guard_refuses_process_network_and_write_events(profile, event):
    with pytest.raises(RuntimeError, match='forbids'):
        profile.effect_guard(event, ())


def test_effect_guard_distinguishes_read_only_open_from_write_flags(profile):
    assert profile.effect_guard('open', ('retained', 'r', profile.os.O_RDONLY)) is None
    for mode, flags in [('wb', profile.os.O_WRONLY), ('r+', profile.os.O_RDWR),
                        (None, profile.os.O_RDONLY | profile.os.O_CREAT)]:
        with pytest.raises(RuntimeError, match='filesystem writes'):
            profile.effect_guard('open', ('retained', mode, flags))
