"""Safety boundaries for second diagnostic pair preparation, U0/D92, 2026-11-06."""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/adhoc' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preparation(tmp_path, monkeypatch):
    helper = load('prepare_native_u0_second_pair_20261106')
    monkeypatch.setattr(helper, 'EXEC', tmp_path)
    monkeypatch.setattr(helper, 'DESTINATIONS', {
        arm: tmp_path / ('new-' + arm) for arm in ('control', 'treatment')})
    evidence = tmp_path / 'native-u0-20261106'
    evidence.mkdir()
    monkeypatch.setattr(sys, 'argv', ['prepare', '--manifest', str(evidence / 'manifest.json')])
    def forbidden_git(*args):
        raise AssertionError('Git must not run before path refusals')
    monkeypatch.setattr(helper.base, 'git', forbidden_git)
    return helper, evidence


def test_existing_tree_refused_before_git_or_source_changes(tmp_path, monkeypatch):
    helper, evidence = preparation(tmp_path, monkeypatch)
    tree = helper.DESTINATIONS['control']
    tree.mkdir()
    sentinel = tree / 'owner-work'
    sentinel.write_bytes(b'preserved')
    with pytest.raises(ValueError, match='new direct execution children'):
        helper.main()
    assert sentinel.read_bytes() == b'preserved'
    assert not (evidence / 'manifest.json').exists()
    assert not helper.DESTINATIONS['treatment'].exists()


def test_manifest_inside_worktree_is_refused(tmp_path, monkeypatch):
    helper, _ = preparation(tmp_path, monkeypatch)
    source = tmp_path / 'some-existing-worktree'
    source.mkdir()
    monkeypatch.setattr(sys, 'argv', ['prepare', '--manifest', str(source / 'new.json')])
    with pytest.raises(ValueError, match='external execution evidence'):
        helper.main()
    assert not (source / 'new.json').exists()


def test_existing_manifest_and_quiet_lock_preserved(tmp_path, monkeypatch):
    helper, evidence = preparation(tmp_path, monkeypatch)
    manifest = evidence / 'manifest.json'
    manifest.write_bytes(b'previous evidence')
    with pytest.raises(ValueError, match='external execution evidence'):
        helper.main()
    assert manifest.read_bytes() == b'previous evidence'
    monkeypatch.setattr(sys, 'argv', ['prepare', '--manifest', str(evidence / 'new.json')])
    plans = tmp_path / 'plans'
    plans.mkdir()
    lock = plans / 'native_quiet_window.lock'
    lock.write_bytes(b'owned elsewhere')
    with pytest.raises(ValueError, match='quiet lock'):
        helper.main()
    assert lock.read_bytes() == b'owned elsewhere'
    assert not (evidence / 'new.json').exists()


@pytest.mark.parametrize('target', ['second-control', 'second-treatment'])
def test_second_targets_cannot_enter_baselines_or_accept_old_head(target):
    driver = load('native_recorder_measure_20261026')
    driver.require_mode_target('cpu-pair', target)
    for mode in ('idle', 'load-diagnostic', 'cpu-profile'):
        with pytest.raises(ValueError, match='exact diagnostic target'):
            driver.require_mode_target(mode, target)
    with pytest.raises(ValueError, match='idle-only'):
        driver.require_mode_target('cpu-pair', target, True)
    for old in ('current', 'pair-control', 'pair-treatment'):
        with pytest.raises(ValueError, match='pristine at its exact declared commit'):
            driver.require_source({'head': driver.HEADS[old], 'pristine': True}, target)


def test_second_bootstrap_preserves_original_cli_bytes_and_exact_helper_binding():
    helper = load('prepare_native_u0_second_pair_20261106')
    original = b'"""Original command package."""\nfrom pathlib import Path\nVALUE = 3\n'
    bindings = {'scripts/adhoc/observer.py': 'a' * 64}
    patched = helper.cli_bootstrap(original, bindings)
    assert patched.startswith(original.splitlines(keepends=True)[0])
    assert patched.endswith(b'from pathlib import Path\nVALUE = 3\n')
    assert patched.count(b'install_from_config') == 1
    assert b'provenance' in patched and b'record' in patched
    assert repr(bindings).encode() in patched
    compile(patched, '<diagnostic-bootstrap>', 'exec')
    assert helper.FIRST_TREATMENT == '2747e86c3f0521c1ef5c455d9be82428e4ca5be7'
    assert 'src/download/prompts/canonical_hashes.yaml' in helper.PROTECTED


@pytest.mark.parametrize('target,head', [
    ('second-control', 'b3285903de8d6ca9389627a3515c6de430216338'),
    ('second-treatment', 'b1b50887068ca2672961833d7a4029c4e7ad2e4e')])
def test_second_pair_requires_frozen_clean_head(target, head):
    driver = load('native_recorder_measure_20261026')
    assert driver.HEADS[target] == head
    driver.require_source({'head': head, 'pristine': True}, target)
    with pytest.raises(ValueError, match='pristine at its exact declared commit'):
        driver.require_source({'head': head, 'pristine': False}, target)
