"""Issue 6214: synthetic runtime refusals through the public lifetime and replay."""
from pathlib import Path

import pytest

from tests.test_native_shared_execution import make_case, launch_case, authority, execute, c


@pytest.mark.parametrize('classification', ['not_prescribed', 'prescribed', 'unclassifiable'])
def test_denial_live_and_saved(tmp_path, monkeypatch, classification):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / classification)
    composition = c.strict_json(case['value']['composition_raw_json'].encode())
    seeds = Path(composition['instruction_path']).parent / 'synthetic-seeds.json'
    seeds.write_bytes(c.canonical({**c.strict_json(seeds.read_bytes()), 'denial': classification}))
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
