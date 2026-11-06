"""U0 split-observer failure and sampling contracts, 2026-11-06."""
import importlib.util
import json
import os
from pathlib import Path
import signal
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('u0_host_observer',
    Path(__file__).parents[1] / 'scripts/adhoc/native_u0_host_observer_20261106.py')
observer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observer)


@pytest.mark.parametrize('value', ['', 'invalid', '1 0 nan launchd', '2 1 0 child',
    '1 0 0 launchd\n1 0 0 duplicate'])
def test_process_visibility_refuses_empty_malformed_or_incomplete(value):
    with pytest.raises(ValueError):
        observer.processes(value)


def test_process_table_keeps_names_and_multicore_cpu():
    table = observer.processes('1 0 0 launchd\n' + str(os.getpid()) + ' 1 150.2 observer name')
    assert table[-1]['cpu_percent'] == 150.2
    assert table[-1]['name'] == 'observer name'


@pytest.mark.parametrize('value', ['', '1 2 3', '{ nan 2 3 }', '{ -1 2 3 }', '{ 1 2 }'])
def test_invalid_loads_refuse(value):
    with pytest.raises(ValueError):
        observer.loads(value)


def test_sysctl_loads():
    assert observer.loads('{ 1.50 2.00 3.25 }') == [1.5, 2, 3.25]


def test_observer_primes_and_records_one_complete_sample(tmp_path, monkeypatch):
    output = tmp_path / 'samples.jsonl'
    binary = tmp_path / 'ps'
    binary.write_bytes(b'fake sampler for test')
    monkeypatch.setattr(observer, 'PS', binary)
    commands, cpu_calls, sleeps = [], [], []

    def command(argv):
        commands.append(argv)
        return ('8' if argv == observer.CPU_COMMAND else '{ 1 2 3 }'
                if argv == observer.LOAD_COMMAND else '1 0 0 launchd\n' + str(os.getpid()) + ' 1 0 observer')

    def cpu(interval):
        cpu_calls.append(interval)
        return 9.5

    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

    monkeypatch.setattr(observer, 'command_text', command)
    monkeypatch.setattr(observer.time, 'sleep', sleep)
    assert observer.observe(output, 30, SimpleNamespace(cpu_percent=cpu)) == 0
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert [row['kind'] for row in rows] == ['observer_start', 'sample', 'observer_end']
    assert rows[1]['sequence'] == 1 and rows[1]['cpu_percent'] == 9.5
    assert rows[-1]['reason'] == 'signal' and rows[-1]['ps_unchanged']
    assert cpu_calls == [None, None]
    assert commands == [observer.CPU_COMMAND, observer.PS_COMMAND, observer.LOAD_COMMAND]
    with pytest.raises(FileExistsError):
        observer.observe(output, 30, SimpleNamespace(cpu_percent=cpu))


def test_command_failure_is_retained_not_empty_quiet_sample(tmp_path, monkeypatch):
    output = tmp_path / 'samples.jsonl'
    monkeypatch.setattr(observer, 'command_text', lambda _: (_ for _ in ()).throw(PermissionError('denied')))
    assert observer.observe(output, 30, SimpleNamespace()) == 1
    row = json.loads(output.read_text())
    assert row['kind'] == 'observer_error'
    assert row['error'] == 'PermissionError: denied'
