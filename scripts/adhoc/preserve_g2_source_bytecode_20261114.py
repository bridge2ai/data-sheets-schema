#!/usr/bin/env python3
# Preserve exactly one G2 helper cache file after source-bound tests are idle,
# 2026-11-14. Inputs: literal cache/source identities and ignored-inclusive
# src/tests/notes/scripts inventory. Outputs: exclusive S2/source-bytecode file,
# plan and outcome. One file is both canary and full scope; no content deletion,
# directory removal, project import, test execution, or Git mutation.
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from datetime import datetime, timezone

ROOT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-h2-integration-fixes-20261113')
OUT = ROOT.parent / 'scratch-g2-20261114/source-bytecode'
RELATIVE = Path('scripts/adhoc/__pycache__/propose_g2_dispatch_boundary_6207_20261114.cpython-313.pyc')
SOURCE_RELATIVE = Path('scripts/adhoc/propose_g2_dispatch_boundary_6207_20261114.py')
EXPECTED_CACHE = {'bytes': 30228, 'sha256': '3f2edc32a7f813ff3795ad0b384af2b93df0526b3cd5f16f217c1dc4589602a7'}
EXPECTED_SOURCE = {'bytes': 23639, 'sha256': '5403fd013483ed9997ea47680f70da0d0c293807ff0df37a793e83acdaa30e01'}
INVENTORY = ['rg', '--files', '--hidden', '--no-ignore', '--null', 'src', 'tests', 'notes', 'scripts',
             '-g', '*.pyc', '-g', '*.pyo']


def fingerprint(path):
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, 'require a regular single-link file'
    raw = path.read_bytes()
    after = path.lstat()
    assert (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'file changed during read'
    assert len(raw) == metadata.st_size
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'device': metadata.st_dev, 'inode': metadata.st_ino, 'mode': stat.S_IMODE(metadata.st_mode)}


def expected(path, identity):
    value = fingerprint(path)
    assert {key: value[key] for key in identity} == identity, 'unexpected file content: ' + str(path)
    return value


def inventory():
    result = subprocess.run(INVENTORY, cwd=ROOT, capture_output=True, check=False)
    assert result.returncode in (0, 1) and not result.stderr, 'bytecode inventory failed'
    return sorted(os.fsdecode(name) for name in result.stdout.split(b'\0') if name)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def document(name, value):
    path = OUT / name
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def observe_location(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return {'state': 'absent'}
    except BaseException as error:
        return {'state': 'unknown', 'error_type': type(error).__name__, 'reason': str(error)}
    try:
        return {'state': 'regular_file', 'fingerprint': fingerprint(path)}
    except BaseException as error:
        return {'state': 'unknown', 'error_type': type(error).__name__, 'reason': str(error)}


def reconcile_rename(original, preserved, before_cache):
    old, new = observe_location(original), observe_location(preserved)
    state = 'unknown'
    if old['state'] == 'absent' and new.get('fingerprint') == before_cache:
        state = 'observed_at_preserved_path'
    elif new['state'] == 'absent' and old.get('fingerprint') == before_cache:
        state = 'observed_at_original_path'
    return {'state': state, 'original': old, 'preserved': new,
            'basis': 'Fresh location and identity observations after failure; no remembered rename-completion flag.'}


def rename_and_verify(original, preserved, source, before_cache, before_source,
                      before_inventory, head, tracked, plan):
    try:
        # Recheck the complete scope and identities immediately before the one
        # rename. Any unexpected cache file refuses the operation.
        assert inventory() == before_inventory
        assert expected(original, EXPECTED_CACHE) == before_cache
        assert expected(source, EXPECTED_SOURCE) == before_source
        assert not preserved.exists() and not preserved.is_symlink()
        os.rename(original, preserved)
        after_cache = expected(preserved, EXPECTED_CACHE)
        assert after_cache == before_cache, 'rename changed file identity or bytes'
        assert not original.exists() and not original.is_symlink()
        after_inventory = inventory()
        assert after_inventory == [], 'unexpected bytecode appeared; do not move additional files'
        assert expected(source, EXPECTED_SOURCE) == before_source
        assert git('rev-parse', 'HEAD') == head and git('diff', '--name-only', 'HEAD') == tracked
        return {'status': 'preserved-and-verified', 'plan': plan,
            'preserved': {'path': str(preserved), **EXPECTED_CACHE}, 'after_cache': after_cache,
            'after_inventory': after_inventory, 'source_unchanged': True, 'head_unchanged': True,
            'one_file_canary_and_full_scope': True, 'content_deleted': False, 'directories_removed': False}
    except BaseException as error:
        document('outcome.json', {'status': 'verification-failed; inspect retained evidence',
            'plan': plan, 'rename_observation': reconcile_rename(original, preserved, before_cache),
            'preserved_path': str(preserved), 'original_path': str(original),
            'error_type': type(error).__name__, 'reason': str(error)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tests-idle-confirmed', action='store_true', required=True,
                        help='Root confirms session 1073 and all source-bound test workers have finished.')
    args = parser.parse_args()
    assert args.tests_idle_confirmed
    assert Path(__file__).absolute().parents[2] == ROOT and ROOT.resolve() == ROOT, 'wrong checkout'
    original, source = ROOT / RELATIVE, ROOT / SOURCE_RELATIVE
    for path in (original.parent, original.parent.parent, source.parent, OUT.parent):
        assert path.resolve() == path and path.is_dir(), 'unexpected symlink or parent'
    assert not OUT.exists() and not OUT.is_symlink(), 'preserve existing evidence; output must be exclusive'
    assert git('rev-parse', '--show-toplevel') == str(ROOT)
    assert git('branch', '--show-current') == 'codex/native-h2-integration-fixes-20261113'
    for operation in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'BISECT_LOG', 'rebase-merge', 'rebase-apply'):
        operation_path = Path(git('rev-parse', '--git-path', operation))
        assert not (operation_path if operation_path.is_absolute() else ROOT / operation_path).exists(), 'Git operation in progress'
    assert not git('ls-files', '--', str(RELATIVE)), 'cache unexpectedly tracked'
    subprocess.check_call(['git', 'check-ignore', '-q', '--', str(RELATIVE)], cwd=ROOT)
    before_inventory = inventory()
    assert before_inventory == [RELATIVE.as_posix()], 'unexpected additional or missing bytecode; move nothing'
    before_cache = expected(original, EXPECTED_CACHE)
    before_source = expected(source, EXPECTED_SOURCE)
    assert original.stat().st_dev == OUT.parent.stat().st_dev, 'require same filesystem rename'
    head = git('rev-parse', 'HEAD')
    tracked = git('diff', '--name-only', 'HEAD')
    OUT.mkdir(exist_ok=False)
    preserved = OUT / original.name
    plan = document('plan.json', {
        'status': 'prepared; operation outcome is separate', 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'One exact task-generated cache file; canary is the entire operation.',
        'original_path': str(original), 'preserved_path': str(preserved), 'before_cache': before_cache,
        'source_path': str(source), 'source_fingerprint': before_source,
        'inventory_command': INVENTORY, 'ignored_and_hidden_files_included': True,
        'before_inventory': before_inventory, 'head': head, 'tracked_diff_before': tracked,
        'test_idle_basis': 'Root supplied --tests-idle-confirmed after session 1073; helper does not infer process liveness.',
        'producer_path': str(Path(__file__)), 'producer_fingerprint': fingerprint(Path(__file__)),
        'undo': {'restore_path': str(original), 'preserved_path': str(preserved),
                 'expected_content': EXPECTED_CACHE,
                 'steps': ['Wait until source-bound tests are idle.',
                           'Require the restore path to be absent and preserved content to match the recorded size/hash.',
                           'Rename only the preserved file back to the restore path; original directories are retained.']},
        'content_deleted': False, 'directories_removed': False, 'space_freed_claimed': False})
    outcome = rename_and_verify(original, preserved, source, before_cache, before_source,
                                before_inventory, head, tracked, plan)
    result = document('outcome.json', outcome)
    print(json.dumps({'outcome': result, 'preserved': outcome['preserved'], 'undo_path': str(original)}, indent=2))


if __name__ == '__main__':
    main()
