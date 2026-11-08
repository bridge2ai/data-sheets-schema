"""Same-tool U5 before/after scanner evidence, including incomplete derivation."""
import hashlib
import json
import os
import subprocess
import sys

import pytest

from scripts.adhoc import native_u5_inputs_20261108 as inputs


BASE_COMMIT = inputs.BASE
REQUIRED_ROOTS = ('src', 'notes', 'scripts', 'tests', '.claude', '.github', 'utils', 'configs', 'project')
REQUIRED_FILES = ('CLAUDE.md', 'data/preprocessed/source_manifest.yaml',
                  'src/data_sheets_schema/api_runner.py', '.claude/commands/d4d-full-core.md',
                  'src/data_sheets_schema/schema/data_sheets_schema.yaml',
                  'tests/test_neutral_generation_schema.py', 'pyproject.toml', 'Makefile')


def require_scanner_inventory(manifest):
    """Missing optional scanner surfaces must not masquerade as a smaller pass."""
    if manifest.get('path_mask') != list(inputs.BASE_SCAN_PATHS):
        raise ValueError('scanner mask must include the complete committed comparison scope')
    files = manifest['files']
    missing = [name for name in REQUIRED_FILES if name not in files]
    empty = [name for name in REQUIRED_ROOTS if not any(p.startswith(name + '/') for p in files)]
    python_empty = [name for name in ('src', 'notes', 'scripts')
                    if not any(p.startswith(name + '/') and p.endswith('.py') for p in files)]
    if missing or empty or python_empty:
        raise ValueError('scanner inputs are incomplete: ' + repr((missing, empty, python_empty)))


def scanner_inputs(candidate_head):
    before, old = inputs.checked_scanner_input('scanner-baseline-' + BASE_COMMIT[:9], BASE_COMMIT)
    after, new = inputs.checked_scanner_input('scanner-candidate-' + candidate_head[:9], candidate_head)
    require_scanner_inventory(old)
    require_scanner_inventory(new)
    if old['path_mask'] != new['path_mask']:
        raise ValueError('scanner before/after input scopes differ')
    return before, after, old, new


def test_scanner_before_after_retains_complete_arrays_or_explicit_blocker(tmp_path):
    candidate_head = inputs.git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    baseline, candidate, old, new = scanner_inputs(candidate_head)
    # The exact same committed candidate scanner/config runs over both exports;
    # no ignored controller, local session settings or working-tree file enters.
    tool = candidate / '.claude/skills/d4d-generation-specificity-audit/scan.py'
    tokens, exceptions = tool.with_name('tokens.yaml'), tool.with_name('exceptions.yaml')
    identity = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tool, tokens, exceptions)}
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'VIRTUAL_ENV') if k in os.environ}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    evidence = {}
    arrays = {}
    for label, source, manifest in (('before', baseline, old), ('after', candidate, new)):
        output = tmp_path / label
        output.mkdir()
        command = [sys.executable, '-P', '-B', str(tool), '--root', str(source),
                   '--report', str(output / 'scan.md'), '--json', str(output / 'scan.json'),
                   '--tokens', str(tokens), '--exceptions', str(exceptions), '--full-json']
        completed = subprocess.run(command, cwd=source, env=env, capture_output=True, timeout=600)
        (output / 'stdout.txt').write_bytes(completed.stdout)
        (output / 'stderr.txt').write_bytes(completed.stderr)
        value = None
        if completed.returncode in (0, 1):
            value = json.loads((output / 'scan.json').read_bytes())
            assert isinstance(value['hits'], list) and isinstance(value['violations'], list)
            arrays[label] = {k: value[k] for k in ('hits', 'violations', 'test_dependencies')}
        evidence[label] = {'root': str(source), 'returncode': completed.returncode,
                           'derivation_complete': value is not None,
                           'finding_arrays_available': value is not None,
                           'tool_identities': identity,
                           'commit': manifest['commit'], 'commit_tree': manifest['commit_tree'],
                           'input_path_mask': manifest['path_mask'],
                           'input_entry_count': manifest['entry_count'],
                           'input_total_blob_bytes': manifest['total_blob_bytes'],
                           'stderr': completed.stderr.decode(errors='replace')}
    complete = len(arrays) == 2
    result = {'before_base': BASE_COMMIT, 'candidate_head': candidate_head, 'runs': evidence,
              'status': 'complete' if complete else 'blocked_incomplete_derivation',
              # Null is deliberate: absent derivation is not zero findings.
              'exact_arrays_equal': arrays['before'] == arrays['after'] if complete else None,
              'finding_arrays': arrays if complete else None,
              'scope': 'Complete committed files under the identical declared scanner mask; '
                       'no live ignored inputs, installed-package or native acceptance'}
    (tmp_path / 'scanner-comparison.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tool, tokens, exceptions)} == identity
    scanner_inputs(candidate_head)
    assert inputs.git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip() == candidate_head
    assert complete, json.dumps(evidence, indent=2)
    assert result['exact_arrays_equal'], 'full finding arrays differ; explicit disposition required'


def synthetic_export(tmp_path, monkeypatch):
    """Small invented input for integrity refusals, never scanner acceptance."""
    monkeypatch.setattr(inputs, 'SCRATCH', tmp_path)
    directory = tmp_path / 'scanner-candidate'
    tree = directory / 'tree'
    tree.mkdir(parents=True)
    raw = b'# invented committed controller\n'
    relative = 'notes/controller.py'
    path = tree / relative
    path.parent.mkdir()
    path.write_bytes(raw)
    path.chmod(0o644)
    oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    expected = {relative: ('100644', oid, len(raw))}
    monkeypatch.setattr(inputs, 'committed_inventory', lambda commit, mask: (expected, len(raw)))
    monkeypatch.setattr(inputs, 'git', lambda *args: b'b' * 40 + b'\n')
    manifest = {'commit': 'a' * 40, 'commit_tree': 'b' * 40,
                'path_mask': list(inputs.BASE_SCAN_PATHS), 'tree': str(tree),
                'entry_count': 1, 'total_blob_bytes': len(raw), 'files': {
                    relative: {'mode': '100644', 'git_blob': oid,
                               'sha256': inputs.sha(raw), 'bytes': len(raw)}}}
    manifest_path = directory / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest))
    return tree, manifest_path, manifest


def test_scanner_export_checks_exact_bytes_modes_and_inventory_on_positive_control(tmp_path, monkeypatch):
    tree, _, manifest = synthetic_export(tmp_path, monkeypatch)
    assert inputs.checked_scanner_input('scanner-candidate', 'a' * 40) == (tree, manifest)


@pytest.mark.parametrize('change', ['missing_inventory_member', 'missing_file', 'changed_bytes', 'extra_ignored_file',
                                  'file_alias', 'mode', 'narrow_mask', 'wrong_head', 'byte_total'])
def test_scanner_export_refuses_incomplete_or_changed_committed_inputs(tmp_path, monkeypatch, change):
    tree, path, manifest = synthetic_export(tmp_path, monkeypatch)
    expected_commit = 'a' * 40
    controller = tree / 'notes/controller.py'
    if change == 'missing_inventory_member':
        manifest['files'] = {}
        manifest['entry_count'] = 0
    elif change == 'missing_file':
        controller.unlink()
    elif change == 'changed_bytes':
        controller.write_bytes(b'# changed\n')
    elif change == 'extra_ignored_file':
        (tree / 'notes/ignored.py').write_text('# must not enter scanner\n')
    elif change == 'file_alias':
        outside = tmp_path / 'outside.py'
        outside.write_bytes(controller.read_bytes())
        controller.unlink()
        controller.symlink_to(outside)
    elif change == 'mode':
        controller.chmod(0o755)
    elif change == 'narrow_mask':
        manifest['path_mask'].remove('notes')
    elif change == 'wrong_head':
        expected_commit = 'c' * 40
    else:
        manifest['total_blob_bytes'] += 1
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        inputs.checked_scanner_input('scanner-candidate', expected_commit)


@pytest.mark.parametrize('missing', ['CLAUDE.md', 'data/preprocessed/source_manifest.yaml', 'notes', 'scripts'])
def test_scanner_scope_requires_session_manifest_and_all_python_roots(missing):
    files = dict.fromkeys(REQUIRED_FILES)
    files.update({root + '/sentinel.py': None for root in REQUIRED_ROOTS})
    if missing in REQUIRED_FILES:
        files.pop(missing)
    else:
        files = {path: row for path, row in files.items() if not path.startswith(missing + '/')}
    with pytest.raises(ValueError, match='incomplete'):
        require_scanner_inventory({'path_mask': list(inputs.BASE_SCAN_PATHS), 'files': files})


@pytest.mark.parametrize('bound', ['MAX_EXPORT_FILES', 'MAX_EXPORT_BYTES'])
def test_scanner_export_preflight_refuses_before_archiving_or_writing(tmp_path, monkeypatch, bound):
    monkeypatch.setattr(inputs, 'SCRATCH', tmp_path)
    monkeypatch.setattr(inputs, bound, 0)
    calls = []

    def metadata(*args):
        calls.append(args[0])
        assert args[0] == 'ls-tree', 'preflight refusal reached archive or other Git command'
        return b'100644 blob ' + b'a' * 40 + b' 1\tnotes/controller.py\0'

    monkeypatch.setattr(inputs, 'git', metadata)
    with pytest.raises(ValueError, match='bound'):
        inputs.materialize('scanner-candidate', 'a' * 40, inputs.BASE_SCAN_PATHS)
    assert calls == ['ls-tree']
    assert not (tmp_path / 'scanner-candidate').exists()


@pytest.mark.parametrize('metadata', [b'120000 blob ' + b'a' * 40 + b' 1',
                                    b'160000 commit ' + b'a' * 40 + b' -'])
def test_scanner_export_preflight_refuses_symlinks_and_gitlinks(tmp_path, monkeypatch, metadata):
    monkeypatch.setattr(inputs, 'SCRATCH', tmp_path)

    def listed(*args):
        assert args[0] == 'ls-tree', 'nonregular input reached archive'
        return metadata + b'\tnotes/controller.py\0'

    monkeypatch.setattr(inputs, 'git', listed)
    with pytest.raises(ValueError, match='ordinary committed'):
        inputs.materialize('scanner-candidate', 'a' * 40, inputs.BASE_SCAN_PATHS)
    assert not (tmp_path / 'scanner-candidate').exists()
