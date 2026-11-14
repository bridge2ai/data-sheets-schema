"""Original seals must name the bytes checked by the observed receipt helper."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_capture_orchestration as host
from data_sheets_schema import native_shared_contract as c
from tests.test_native_shared_observations import artifact, events, trace
from tests.test_native_shared_phase import _initial_check_ready


def checked_run(tmp_path, identity=None):
    full = artifact('phase1_full', str(tmp_path / 'full.yaml'), b'name: checked A\n')
    receipt = artifact('phase1_receipt', str(tmp_path / 'receipt.yaml'), b'checked receipt A\n')
    selection = SimpleNamespace(registration=artifact('selection', str(tmp_path / 'selection.json'), b'{}'),
        bounds=lambda: {'max_input_bytes': 10000})
    inputs = {'selection_sha256': selection.registration.pin.sha256,
        'full_sha256': full.pin.sha256, 'receipt_sha256': receipt.pin.sha256}
    result = {'native_initial_inputs': inputs if identity is None else identity}
    rows, parents, _ = events()
    command = {'command': '/neutral/python -m receipt_helper'}
    rows[0]['message']['content'][0].update(name='Bash', input=command)
    rows[1]['request']['input'].update(tool_name='Bash', tool_input=command)
    parents[0]['request'] = deepcopy(rows[1])
    raw = c.canonical(result).decode()
    rows[-1]['message']['content'][0].update(content=raw, is_error=False)
    rows[-1]['tool_use_result'] = {'exitCode': 0, 'stdout': raw}
    observed = trace(rows, parents)
    run = SimpleNamespace(selection=selection, trace=lambda: observed,
        transcript=observed.transcript, phase1=None,
        spec=SimpleNamespace(_agentic_artifact_paths={'full': full.pin.path, 'receipt': receipt.pin.path}))
    report = {'checks': [{'helper': 'phase1_receipts', 'exit_code': 0, 'tool_use_id': 'tool-1'}]}
    return run, report, full, receipt


def test_checked_bytes_match_in_saved_identity_check(tmp_path):
    run, report, full, receipt = checked_run(tmp_path)
    capture._require_initial_seal_identity(run, report, full, receipt)


@pytest.mark.parametrize('changed', ['full', 'receipt', 'selection'])
def test_saved_identity_refuses_another_checked_input(tmp_path, changed):
    run, report, full, receipt = checked_run(tmp_path)
    if changed == 'full':
        full = artifact('phase1_full', full.pin.path, b'name: replacement B\n')
    elif changed == 'receipt':
        receipt = artifact('phase1_receipt', receipt.pin.path, b'replacement B\n')
    else:
        run.selection.registration = artifact('selection', run.selection.registration.pin.path, b'{"changed":true}')
    with pytest.raises(ValueError, match='differ from checked'):
        capture._require_initial_seal_identity(run, report, full, receipt)


def test_replacement_before_first_seal_read_refuses_before_publication(tmp_path, monkeypatch):
    from pathlib import Path
    run, report, full, receipt = checked_run(tmp_path)
    Path(full.pin.path).write_bytes(b'name: replacement B\n')
    Path(receipt.pin.path).write_bytes(b'replacement receipt B\n')
    monkeypatch.setattr(host, 'phase_replay', lambda _: (report,
        {run.transcript.lines: (('seal_phase1',), report)}))
    monkeypatch.setattr(host, '_create', lambda *a, **k: pytest.fail('published unchecked bytes'))
    with pytest.raises(ValueError, match='differ from checked'):
        host.seal_originals(run, 'seal_phase1')
    assert sorted(p.name for p in tmp_path.iterdir()) == ['full.yaml', 'receipt.yaml']


@pytest.mark.parametrize('identity', [None, {}, {'selection_sha256': 'a' * 64},
    {'selection_sha256': 'a' * 64, 'full_sha256': True, 'receipt_sha256': 'c' * 64},
    {'selection_sha256': 'a' * 64, 'full_sha256': 'b' * 64, 'receipt_sha256': 'invalid'}])
def test_phase_rejects_incomplete_or_untyped_initial_identity(identity):
    state = _initial_check_ready()
    value = {'mode': 'initial_structure', 'structure_passed': True,
        'floors': 'pending', 'floor_acceptance_claimed': False,
        'summary': None, 'reason': None, 'findings': [], 'structural_checks': {},
        'native_initial_inputs': identity, 'receipt_completion_policy': None}
    with pytest.raises(ValueError, match='initial receipt input identity'):
        state.helper('phase1_receipts', value=value)
    assert state.state.report()['problems']
