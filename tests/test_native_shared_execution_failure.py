"""Actual public failed publication; runtime observation fails before dispatch."""
from pathlib import Path
import socket
import subprocess
import pytest
from tests.test_native_shared_execution import make_case
from data_sheets_schema import native_shared_execution as execute
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_execution_authority as authority


def test_public_pre_dispatch_failure_is_readable_and_cannot_resume(tmp_path, monkeypatch):
    original = subprocess.Popen
    calls = []
    def git_only(argv, *args, **kwargs):
        assert isinstance(argv, (list, tuple)) and argv[0] == 'git', 'unexpected child dispatch'
        return original(argv, *args, **kwargs)
    def forbidden(*args, **kwargs):
        pytest.fail('pre-dispatch failure made a network connection')
    monkeypatch.setattr(subprocess, 'Popen', git_only)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'case')
    def observation_failure(value):
        calls.append(value['attempt_id'])
        raise RuntimeError('intentional software-test observation failure; no auth executed')
    monkeypatch.setattr(execute, '_probe_runtime', observation_failure)
    result = execute.launch(case['raw'], **case['kwargs'])
    (case['root'] / 'actual-failed-result.json').write_bytes(c.canonical(result))
    assert result['state'] == 'failed' and result['runtime_gates_passed'] is False
    assert result['first_stop'] is not None
    assert result['gates']['runtime_authority']['passed'] is False
    assert calls == [case['value']['attempt_id']]
    reread = execute.read_final(case['raw'])
    assert reread == result
    with pytest.raises(ValueError, match='new|resume'):
        execute.launch(case['raw'], **case['kwargs'])
    assert calls == [case['value']['attempt_id']]
    attempt = Path(case['value']['attempt_directory'])
    assert (attempt / 'started.json').is_file()
    assert not (attempt / 'transcript.jsonl').exists()
    assert result['scientific_acceptance'] == 'not_assessed'
