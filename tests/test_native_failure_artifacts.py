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
    (attempt / 'stderr.txt').write_bytes(b'x' * 100 + b'\nhelper_timing')
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


def load_collector():
    source = Path(__file__).resolve().parents[1] / 'scripts/adhoc/collect_native_failure_evidence.py'
    spec = importlib.util.spec_from_file_location('failure_evidence', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_redacts_stderr_and_json_transcript(tmp_path, monkeypatch):
    import json
    module = load_collector()
    monkeypatch.setenv('GITHUB_WORKSPACE', '/runner/work/project')
    monkeypatch.setenv('HOME', '/runner/home')
    monkeypatch.setenv('EXAMPLE_SECRET', 'sensitive-environment-value')
    secrets = ['/runner/work/project/private/data', '/runner/home/private/key',
               'sensitive-environment-value', 'Bearer opaque-value', 'ghp_private',
               'gho_private', 'ghs_private', 'github_pat_private', 'sk-private-key',
               'AKIAABCDEFGHIJKLMNOP', 'person' + chr(64) + 'example.org']
    attempt = tmp_path / 'base/native-attempt'
    attempt.mkdir(parents=True)
    content = ' '.join(secrets)
    (attempt / 'stderr.txt').write_text(content)
    (attempt / 'transcript.jsonl').write_text(json.dumps({'content': content}) + '\n')
    result = module.collect(tmp_path / 'base', tmp_path / 'out')
    assert len(result['files']) == 2
    for row in result['files']:
        saved = (tmp_path / 'out' / row['path']).read_text()
        assert all(secret not in saved for secret in secrets)
        assert all(row['redactions'][label] > 0 for label in
                   ('workspace', 'runner_home', 'environment', 'bearer', 'github', 'api_key', 'aws', 'email'))
        assert '[RUNNER_HOME]' in row['placeholders']


def test_replacement_races(tmp_path, monkeypatch):
    import os
    for component in ('stderr.txt', 'native-attempt'):
        for symlink in (False, True):
            module = load_collector()
            base = tmp_path / (component + str(symlink))
            attempt = base / 'native-attempt'
            attempt.mkdir(parents=True)
            (attempt / 'stderr.txt').write_text('original')
            outside = tmp_path / ('outside' + component + str(symlink))
            outside.mkdir()
            (outside / 'stderr.txt').write_text('outside secret')
            original_open = os.open
            replaced = []

            def race_open(path, flags, *args, **kwargs):
                if path == component and not replaced:
                    replaced.append(True)
                    victim = attempt if component == 'native-attempt' else attempt / component
                    victim.rename(victim.with_name(victim.name + '.old'))
                    if symlink:
                        victim.symlink_to(outside if component == 'native-attempt' else outside / component)
                    elif component == 'native-attempt':
                        victim.mkdir()
                        (victim / 'stderr.txt').write_text('outside secret')
                    else:
                        victim.write_text('outside secret')
                return original_open(path, flags, *args, **kwargs)

            with monkeypatch.context() as patch:
                patch.setattr(module.os, 'open', race_open)
                result = module.collect(base, base / 'out')
            assert replaced
            assert result['files'] == []


def test_partial_line_and_invalid_encoding_are_not_published(tmp_path, monkeypatch):
    module = load_collector()
    attempt = tmp_path / 'base/native-attempt'
    attempt.mkdir(parents=True)
    (attempt / 'stderr.txt').write_bytes(b'ghp_' + b'a' * 100 + b'\nsafe\n')
    (attempt / 'transcript.jsonl').write_bytes(b'\xffprivate')
    monkeypatch.setattr(module, 'FILE_LIMIT', 20)
    result = module.collect(tmp_path / 'base', tmp_path / 'out')
    assert len(result['files']) == 1
    assert result['omitted']['unsafe_encoding'] == 1
    assert (tmp_path / 'out/native-attempt/stderr.txt').read_bytes() == b'safe\n'


def test_redaction_expansion_and_count_remain_bounded(tmp_path, monkeypatch):
    module = load_collector()
    attempt = tmp_path / 'base/native-attempt'
    attempt.mkdir(parents=True)
    (attempt / 'stderr.txt').write_text('sk-a')
    monkeypatch.setattr(module, 'FILE_LIMIT', 5)
    result = module.collect(tmp_path / 'base', tmp_path / 'expanded')
    assert result['files'] == []
    assert result['omitted']['redaction_expansion'] == 1
    (attempt / 'stderr.txt').write_text('safe')
    (attempt / 'control.jsonl').write_text('safe')
    monkeypatch.setattr(module, 'COUNT_LIMIT', 1)
    result = module.collect(tmp_path / 'base', tmp_path / 'bounded')
    assert len(result['files']) == 1
    assert result['saved_bytes'] == 4
