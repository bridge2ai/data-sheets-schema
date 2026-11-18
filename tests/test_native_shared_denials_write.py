"""Issue 6214: synthetic runtime refusals through the public lifetime and replay."""
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from tests.test_native_shared_execution import make_case, launch_case, authority, execute, c
from tests.test_native_shared_execution import _native_helper_import_environment  # noqa: F401
from tests.test_native_execution_registration_v2 import isolated_modules


@pytest.mark.parametrize(('denied_tool', 'classification'), [
    ('Write', 'not_prescribed')])
def test_denial_live_and_saved(tmp_path, monkeypatch, classification, denied_tool, isolated_modules):
    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / classification)
    composition = c.strict_json(case['value']['composition_raw_json'].encode())
    seeds = Path(composition['instruction_path']).parent / 'synthetic-seeds.json'
    seeds.write_bytes(c.canonical({**c.strict_json(seeds.read_bytes()), 'denial': classification,
                                  'denied_tool': denied_tool}))
    result = launch_case(case, monkeypatch)
    if classification == 'not_prescribed':
        assert result['runtime_gates_passed'], json.dumps({
            'first_stop': result.get('first_stop'),
            'child_exit_code': result.get('child_exit_code'),
            'capture_problems': result.get('capture_problems', []),
            'failing_gates': {name: row for name, row in result.get('gates', {}).items()
                              if row.get('checked') is not True or row.get('passed') is not True},
        }, indent=2, sort_keys=True)
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

