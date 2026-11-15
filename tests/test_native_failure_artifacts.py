"""CI diagnostics remain bounded and exclude configs, caches and symlinks."""
import importlib.util
from pathlib import Path


def test_failure_artifacts_keep_tail_and_relative_paths(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / 'scripts/adhoc/collect_native_failure_evidence.py'
    spec = importlib.util.spec_from_file_location('failure_evidence', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = tmp_path / 'base'
    attempt = base / 'test_case' / 'native-attempt'
    attempt.mkdir(parents=True)
    (attempt / 'stderr.txt').write_bytes(b'x' * 100 + b'helper_timing')
    (attempt / 'control.jsonl').write_bytes(b'control')
    (attempt / 'transcript.jsonl').write_bytes(b'transcript')
    (attempt / 'host-clock-stage-a.json').write_bytes(b'{}')
    (attempt / 'secret.json').write_bytes(b'never upload')
    (attempt / 'helper-cache').mkdir()
    (attempt / 'helper-cache' / 'stderr.txt').symlink_to(attempt / 'secret.json')
    (attempt / 'helper-cache' / 'control.jsonl').write_bytes(b'cache must stay private')
    monkeypatch.setattr(module, 'FILE_LIMIT', 20)
    monkeypatch.setattr(module, 'TOTAL_LIMIT', 40)
    output = tmp_path / 'output'
    result = module.collect(base, output)
    assert result['saved_bytes'] <= 40
    assert all(not Path(row['path']).is_absolute() for row in result['files'])
    assert not list(output.rglob('secret.json'))
    assert not list(output.rglob('helper-cache'))
    assert (output / 'test_case/native-attempt/stderr.txt').read_bytes().endswith(b'helper_timing')
    assert any(row['tail_truncated'] for row in result['files'])
    assert (output / 'manifest.json').stat().st_size > 0
