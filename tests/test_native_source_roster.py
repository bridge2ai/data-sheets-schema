"""Actual named Git roster proof in copied sources; no native/provider launch."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from data_sheets_schema import native_attribution_controller as inherited
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_supervisor_authority as supervisor
from data_sheets_schema.resources import git_env


def _git(root, *args):
    env = git_env()
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args],
                          cwd=root, env=env, capture_output=True, check=True,
                          text=True, timeout=30)


@pytest.fixture(scope='module')
def source_template(tmp_path_factory):
    """Copy exact files once, then give every case its own Git database/tree."""
    root = authority.ROOT
    package = root / authority.PACKAGE
    files = {str(path.relative_to(root)) for path in package.rglob('*')
             if path.is_file() and path.suffix in authority.SOURCE_SUFFIXES}
    manifest = json.loads((root / inherited.SOURCES_PATH).read_bytes())
    files.update(pin['path'] for pin in manifest['modules'].values())
    files.update(pin['path'] for pin in supervisor.ADDITIONAL.values())
    files.update(pin['path'] for pin in authority.ADDITIONAL.values())
    files.add('pyproject.toml')
    destination = tmp_path_factory.mktemp('source-roster-template')
    original = {}
    for relative in sorted(files):
        source, target = root / relative, destination / relative
        assert source.is_file() and not source.is_symlink()
        raw = source.read_bytes()
        original[relative] = hashlib.sha256(raw).hexdigest()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert target.read_bytes() == raw
        assert target.stat().st_ino != source.stat().st_ino or target.stat().st_dev != source.stat().st_dev
    # Valid directory suffix, literal whitespace/Unicode, and ignored tracked
    # inputs all participate in the actual source-discovery/Git comparison.
    fixtures = {
        'fixtures.py/a space.json': b'{"fixture": true}\n',
        'fixtures.py/tab\tand-é.py': b'# Literal path fixture.\n',
        'fixture-resource.yaml': b'fixture: true\n',
        '.retained.json': b'{"hidden": true}\n',
    }
    for relative, raw in fixtures.items():
        target = destination / authority.PACKAGE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (destination / '.gitignore').write_text('src/data_sheets_schema/.retained.json\n')
    _git(destination, 'init', '-q')
    _git(destination, 'add', '--', '.')
    _git(destination, 'add', '-f', '--', authority.PACKAGE + '/.retained.json')
    _git(destination, '-c', 'user.name=Software fixture', '-c', 'user.email=fixture@example.invalid',
         '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Copied exact fixture authority')
    original_head = _git(root, 'rev-parse', 'HEAD').stdout.strip()
    original_status = _git(root, 'status', '--porcelain=v1', '-z').stdout
    yield destination
    # Every destructive control ran in copies, not this implementation tree.
    assert _git(root, 'rev-parse', 'HEAD').stdout.strip() == original_head
    assert _git(root, 'status', '--porcelain=v1', '-z').stdout == original_status
    assert {relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in original} == original


CHILD = r'''
import hashlib, json, os, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1]).resolve()
mode = sys.argv[2]
sys.path.insert(0, str(root / 'src'))
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema.resources import git_env
assert authority.ROOT == root
assert pathlib.Path(authority.__file__).resolve().is_relative_to(root)
assert pathlib.Path(draft.__file__).resolve().is_relative_to(root)

def git(*args):
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=root,
        env=git_env(), capture_output=True, text=True, timeout=30, check=True).stdout.strip()

def commit():
    git('-c', 'user.name=Software fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Fixture-only transition')

identity = authority.dependency_identity()
assert identity['version'] == 1 and set(identity) == {'version', 'base', 'additional_modules'}
authority.require_committed(identity)
package = root / authority.PACKAGE
resource = package / 'fixture-resource.yaml'
assert str(package / 'fixtures.py/a space.json') in [str(root / p) for p in identity['base']['package_sources']]
expected = None
changed_path = None
if mode == 'missing_imported':
    path = pathlib.Path(draft.__file__)
    changed_path = str(path.relative_to(root))
    path.unlink()
    assert sys.modules['data_sheets_schema.native_attribution_registration'] is draft
    assert not path.exists()
    expected = 'committed package source roster differs: missing='
elif mode == 'missing_resource':
    changed_path = str(resource.relative_to(root))
    resource.unlink()
    expected = 'committed package source roster differs: missing='
elif mode in ('extra_untracked', 'extra_staged', 'extra_ignored'):
    filename = '.new-ignored.json' if mode == 'extra_ignored' else 'unreviewed.py'
    path = package / filename
    path.write_bytes(b'{}\n' if filename.endswith('.json') else b'# Unreviewed source.\n')
    changed_path = str(path.relative_to(root))
    if mode == 'extra_staged': git('add', '--', changed_path)
    if mode == 'extra_ignored':
        with (root / '.gitignore').open('a') as stream: stream.write(changed_path + '\n')
    expected = 'committed package source roster differs:'
elif mode == 'changed_blob':
    changed_path = str(resource.relative_to(root))
    resource.write_bytes(b'fixture: changed\n')
    expected = 'consumed source differs from the reviewed commit:'
elif mode == 'commit_replacement':
    changed_path = str(resource.relative_to(root))
    claimed = identity['base']['source_commit']
    resource.unlink()
    git('add', '-u', '--', changed_path)
    commit()
    replacement = git('rev-parse', 'HEAD')
    # Return only the reference to A, leaving the deliberately shortened
    # working tree and index at B. This mutation is wholly fixture-owned.
    git('update-ref', 'HEAD', claimed)
    git('replace', claimed, replacement)
    assert git('rev-parse', 'HEAD') == claimed
    assert git('ls-tree', '-r', claimed, '--', changed_path) == ''
    assert git('--no-replace-objects', 'ls-tree', '-r', claimed, '--', changed_path)
    expected = 'committed package source roster differs: missing='
elif mode == 'blob_replacement':
    changed_path = str(resource.relative_to(root))
    claimed_blob = git('rev-parse', 'HEAD:' + changed_path)
    resource.write_bytes(b'fixture: substituted-blob\n')
    replacement_blob = git('hash-object', '-w', '--', changed_path)
    git('replace', claimed_blob, replacement_blob)
    assert git('cat-file', 'blob', claimed_blob) == resource.read_text().strip()
    assert git('--no-replace-objects', 'cat-file', 'blob', claimed_blob) != resource.read_text().strip()
    expected = 'consumed source differs from the reviewed commit:'
elif mode == 'stale_commit':
    identity['base']['source_commit'] = '0' * 40
    expected = 'native execution dependency identity changed'
elif mode == 'index_deleted':
    git('rm', '--cached', '--', str(resource.relative_to(root)))
    assert resource.is_file()
elif mode == 'committed_deletion':
    resource.unlink()
    git('add', '-u', '--', str(resource.relative_to(root)))
    commit()
elif mode == 'executable_source':
    relative = str(resource.relative_to(root))
    oid = git('rev-parse', 'HEAD:' + relative)
    git('update-index', '--cacheinfo', '100755,' + oid + ',' + relative)
    commit()
elif mode == 'source_symlink':
    # Working discovery reads target bytes; the named tree stores a symlink.
    raw = resource.read_bytes()
    outside = root / 'resource-target'
    outside.write_bytes(raw)
    resource.unlink()
    resource.symlink_to(outside)
    git('add', '--', str(resource.relative_to(root)))
    commit()
    expected = 'committed package source is not a regular blob:'
elif mode == 'gitlink':
    relative = authority.PACKAGE + '/opaque-member'
    (root / relative).mkdir()
    git('update-index', '--add', '--cacheinfo', '160000,' + git('rev-parse', 'HEAD') + ',' + relative)
    commit()
    expected = 'committed package contains a non-tree boundary or Gitlink'
elif mode == 'linebreak_path':
    path = package / 'line\nbreak.py'
    path.write_bytes(b'# No query injection.\n')
    git('add', '--', str(path.relative_to(root)))
    commit()
    expected = 'committed package source has an unsupported line-break path'
elif mode == 'unrelated_asset':
    path = package / 'ignored.txt'
    path.write_bytes(b'Not in the declared source domain.\n')
    git('add', '--', str(path.relative_to(root)))
    commit()
    path.unlink()
elif mode == 'hostile_git_overrides':
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
        decoy = root / ('invalid-' + name.lower())
        if name == 'GIT_INDEX_FILE': decoy.write_bytes(b'not an index')
        else: decoy.mkdir()
        os.environ[name] = str(decoy)
elif mode != 'unchanged':
    raise AssertionError(mode)

changed = identity if mode == 'stale_commit' else authority.dependency_identity()
if mode.startswith('missing_'):
    assert changed['base']['source_commit'] == identity['base']['source_commit']
    assert changed_path not in changed['base']['package_sources']
    assert changed_path in identity['base']['package_sources']
if mode in ('extra_untracked', 'extra_staged', 'extra_ignored'):
    assert changed_path in changed['base']['package_sources']
    assert changed_path not in identity['base']['package_sources']
if mode == 'changed_blob':
    assert set(changed['base']['package_sources']) == set(identity['base']['package_sources'])
if expected is None:
    authority.require_committed(changed)
else:
    try: authority.require_committed(changed)
    except ValueError as error:
        assert expected in str(error), (mode, str(error))
        if changed_path is not None: assert changed_path in str(error), str(error)
    else: raise AssertionError('actual source boundary was accepted: ' + mode)
print(json.dumps({'mode': mode, 'initial_actual_proof': True, 'boundary_verified': True}))
'''


@pytest.mark.parametrize('mode', [
    'unchanged', 'missing_imported', 'missing_resource', 'extra_untracked',
    'extra_staged', 'extra_ignored', 'changed_blob', 'commit_replacement', 'blob_replacement',
    'stale_commit', 'index_deleted',
    'committed_deletion', 'executable_source', 'source_symlink', 'gitlink',
    'linebreak_path', 'unrelated_asset', 'hostile_git_overrides',
])
def test_real_named_commit_roster_and_blobs_in_fixture_owned_repository(source_template, tmp_path, mode):
    fixture = tmp_path / 'source'
    shutil.copytree(source_template, fixture)
    env = git_env()
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    # Replacement controls must witness ordinary Git's redirection even when
    # the coordinator's shell disables it globally. Production uses a fixed
    # command-line refusal, independent of this fixture-only environment.
    env.pop('GIT_NO_REPLACE_OBJECTS', None)
    result = subprocess.run([sys.executable, '-I', '-B', '-c', CHILD, str(fixture), mode],
                            cwd=fixture, env=env, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {
        'mode': mode, 'initial_actual_proof': True, 'boundary_verified': True}


def _entry(path, mode=b'100644', kind=b'blob', oid=b'a' * 40):
    return mode + b' ' + kind + b' ' + oid + b'\t' + path + b'\0'


ROOTS = _entry(b'src', b'040000', b'tree') + _entry(b'src/data_sheets_schema', b'040000', b'tree')


def test_literal_tree_paths_are_not_shell_quoted_or_split_on_whitespace():
    paths = ['src/data_sheets_schema/a space.py', 'src/data_sheets_schema/tab\tand-é.json']
    raw = ROOTS + b''.join(_entry(path.encode()) for path in paths)
    assert authority._package_roster(raw) == set(paths)


@pytest.mark.parametrize('raw', [
    b'', ROOTS[:-1], ROOTS + b'\0',
    ROOTS + _entry(b'src/data_sheets_schema/a.py') * 2,
    ROOTS + _entry(b'src/data_sheets_schema/../a.py'),
    ROOTS + _entry(b'src/data_sheets_schema//a.py'),
    ROOTS + _entry(b'/src/data_sheets_schema/a.py'),
    ROOTS + _entry(b'src/data_sheets_schema-other/a.py'),
    ROOTS + _entry(b'src/data_sheets_schema/\xff.py'),
    ROOTS + _entry(b'src/data_sheets_schema/a.py', oid=b'not-an-object'),
    ROOTS + _entry(b'src/data_sheets_schema/a.py', mode=b'100600'),
    ROOTS + _entry(b'src/data_sheets_schema/a.py', mode=b'120000'),
    ROOTS + _entry(b'src/data_sheets_schema/a.py', mode=b'160000', kind=b'commit'),
    ROOTS + _entry(b'src/data_sheets_schema/a.py', kind=b'tree'),
    ROOTS + _entry(b'src/data_sheets_schema/a\rb.py'),
    ROOTS + _entry(b'src/data_sheets_schema/a\nb.py'),
    _entry(b'src') + _entry(b'src/data_sheets_schema/a.py'),
    ROOTS + _entry(b'src/data_sheets_schema/link', mode=b'160000', kind=b'commit'),
])
def test_malformed_duplicate_or_nonregular_tree_records_refuse(raw):
    with pytest.raises(ValueError):
        authority._package_roster(raw)


def test_directory_suffix_and_unrelated_asset_are_not_source_entries():
    raw = (ROOTS + _entry(b'src/data_sheets_schema/sub.py', b'040000', b'tree')
           + _entry(b'src/data_sheets_schema/sub.py/actual.json', b'100755')
           + _entry(b'src/data_sheets_schema/asset.txt')
           + _entry(b'src/data_sheets_schema/asset-link', b'120000'))
    assert authority._package_roster(raw) == {'src/data_sheets_schema/sub.py/actual.json'}
