"""N4: offline test evidence must include newly added source and test bytes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess


def test_source_snapshot_binds_tracked_and_untracked_bytes(tmp_path):
    source = Path(__file__).resolve().parents[1] / 'scripts/adhoc/run_native_u3d_tests_20261107.py'
    spec = importlib.util.spec_from_file_location('u3d_runner', source)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    root = tmp_path / 'repo'; root.mkdir()
    out = tmp_path / 'evidence'; out.mkdir()

    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root)

    git('init', '-q')
    (root / 'tracked.py').write_text('old\n')
    (root / '.gitignore').write_text('ignored.cache\n')
    git('add', '.')
    git('-c', 'user.name=Offline test', '-c', 'user.email=test@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic baseline')
    (root / 'tracked.py').write_text('new\n')
    (root / 'new test\nfile.py').write_bytes(b'new test\x00bytes\n')
    (root / 'new-link').symlink_to('tracked.py')
    (root / 'ignored.cache').write_bytes(b'regenerable')
    hashes = runner.source_evidence(root, out, os.environ.copy())
    assert b'-old\n+new' in (out / 'tested.diff').read_bytes()
    assert b'??' in (out / 'tested.status').read_bytes()
    manifest = json.loads((out / 'tested-untracked.json').read_bytes())
    entries = {item['path']: item for item in manifest['files']}
    assert set(entries) == {'new test\nfile.py', 'new-link'}
    assert entries['new test\nfile.py'] == {
        'path': 'new test\nfile.py', 'kind': 'file', 'size': 15,
        'sha256': hashlib.sha256(b'new test\x00bytes\n').hexdigest()}
    assert entries['new-link']['kind'] == 'symlink'
    assert entries['new-link']['sha256'] == hashlib.sha256(b'tracked.py').hexdigest()
    for key, name in [('tested_diff_sha256', 'tested.diff'),
                      ('tested_status_sha256', 'tested.status'),
                      ('tested_untracked_sha256', 'tested-untracked.json')]:
        assert hashes[key] == hashlib.sha256((out / name).read_bytes()).hexdigest()
    # Taking evidence must not stage files or rewrite the caller's index.
    assert not git('diff', '--cached', '--name-only')
