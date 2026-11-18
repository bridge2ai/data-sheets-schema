"""Issue 6214: synthetic runtime refusals through the public lifetime and replay."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_native_shared_execution import make_case, launch_case, authority, execute, c
from tests.test_native_execution_registration_v2 import isolated_modules


@pytest.mark.parametrize(('denied_tool', 'classification'), [
    ('Bash', 'unclassifiable')])
def test_denial_live_and_saved(tmp_path, monkeypatch, classification, denied_tool, isolated_modules):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / classification)
    composition = c.strict_json(case['value']['composition_raw_json'].encode())
    seeds = Path(composition['instruction_path']).parent / 'synthetic-seeds.json'
    seeds.write_bytes(c.canonical({**c.strict_json(seeds.read_bytes()), 'denial': classification,
                                  'denied_tool': denied_tool}))
    result = launch_case(case, monkeypatch)
    if classification == 'not_prescribed':
        assert result['runtime_gates_passed'], result
        assert result['state'] == 'completed_pending_independent_review'
    else:
        assert result['state'] == 'failed'
        assert not result['runtime_gates_passed']
        assert 'denied ' + classification + ' call' in str(result['first_stop']), result
        transcript = Path(case['value']['attempt_directory']) / 'transcript.jsonl'
        assert 'chunk_check' not in transcript.read_text()
    assert execute.read_final(case['raw']) == result
    if denied_tool != 'Bash':
        assert not (seeds.parent / 'never-accessed.txt').exists()


@pytest.mark.parametrize('tool', ['Read', 'Write'])
def test_denied_file_replay_never_resolves_or_reads_target(monkeypatch, tool):
    from tests.test_native_shared_observations import events, trace
    from data_sheets_schema.native_shared_results import Snapshot
    from data_sheets_schema.native_shared_results_orchestration import _CapturedFiles

    native, parent, _ = events(tool)
    basis = 'a path outside the registered inputs and outputs'
    parent[0].update(classification='not_prescribed', basis=basis)
    parent[0]['response']['response']['response'] = {'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
        'permissionDecisionReason': 'Outside the registered tool policy: ' + basis}}
    native[-1].pop('tool_use_result')
    native[-1]['message']['content'][0].update(
        is_error=True, content='Outside the registered tool policy: ' + basis)
    observed = trace(native, parent)
    payload = observed.calls['tool-1'][2]['input']
    policy = {'readonly_lookups': {'repository': '/neutral', 'inputs': [],
                                  'output_directories': ['/neutral/output']}}
    snapshot = Snapshot('/neutral')
    def forbidden(*args, **kwargs):
        pytest.fail('denied target must never be resolved or read during replay')
    monkeypatch.setattr(Path, 'resolve', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    files = _CapturedFiles(snapshot, policy,
        {'budgeted_cborg': SimpleNamespace(BudgetStop=RuntimeError)}, observed)
    assert files.classify(tool, payload) == ('not_prescribed', basis)
    assert files.matches(tool, payload, dict(payload))
    assert not files.matches(tool, payload, {**payload, 'file_path': '/neutral/other'})
    assert snapshot.raw == snapshot.metadata == snapshot.aliases == {}
    # An unobserved request cannot borrow the denied request's exemption.
    with pytest.raises(RuntimeError, match='could not be resolved'):
        files.classify(tool, {**payload, 'file_path': '/neutral/other'})
