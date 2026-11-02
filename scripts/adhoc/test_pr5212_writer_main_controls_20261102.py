"""#5212 round 7, 2026-11-02: one actual artifact from each writer versus main.

Input: PR5212_WRITER_CENSUS, a completed census basetemp with writer-control.json.
Output: five pytest comparisons plus per-node probe.json in scratch. Immutable
source bytes are independently SHA-256 checked; no controller or guard is mocked.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest
from data_sheets_schema import api_runner as api, output_ownership
from tests.test_download.test_api_runner import FakeClient, spec


def tree(root):
    result = {}
    for path in [root, *root.rglob('*')]:
        info = path.lstat()
        raw = str(path.readlink()) if path.is_symlink() else 'dir' if path.is_dir() else path.read_bytes()
        result[str(path.relative_to(root))] = (info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ino, raw)
    return result


@pytest.mark.parametrize('writer', ['plain', 'shared_v1_typed_audit_regate', 'shared_v2',
    'receipt_completion_readdress', 'removal_repair_after_repair'])
def test_actual_writer_artifact_with_owner_guard_passing(tmp_path, monkeypatch, writer):
    root = Path(os.environ['PR5212_WRITER_CENSUS'])
    controls = [json.loads(p.read_text()) for p in root.rglob('writer-control.json')]
    rows = [row for row in controls if row['writer'] == writer]
    assert len(rows) == 1, rows
    row, = rows
    raw = Path(row['source']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    current = spec(project=row['project'], out_dir=tmp_path / 'outputs')
    artifact = current.out_dir / row['artifact']
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(raw)
    output_ownership.require_selected_resume_owner(current, resume=True)
    reached, client = [], FakeClient()
    def lock(*args):
        reached.append('lock')
        raise RuntimeError('main reached lock boundary')
    monkeypatch.setattr(api, '_exclusive_run', lock)
    before = tree(current.out_dir)
    with pytest.raises(Exception) as caught:
        api.execute(current, client=client)
    guarded = hasattr(api, '_prelock_checks')
    assert ('inspection only' if guarded else 'main reached lock boundary') in str(caught.value)
    assert reached == ([] if guarded else ['lock'])
    assert client.messages.calls == [] and tree(current.out_dir) == before
    (tmp_path / 'probe.json').write_text(json.dumps({**row, 'reached': reached,
        'owner_guard_passed': True, 'tree_equal': True, 'calls': 0,
        'message': str(caught.value)}, indent=2))
