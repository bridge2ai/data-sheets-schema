"""Root-only byte-exact evidence transfer; no project imports or producer run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from verify import LIMIT, encoded, hash_fields, verify_release


def pin(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), **hash_fields(raw)}


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write('\n')


def inventory(root):
    rows = {}
    for parent, dirs, files in os.walk(root, followlinks=False):
        if Path(parent) == root and '.git' in dirs:
            dirs.remove('.git')
        for name in dirs + files:
            path = Path(parent) / name
            info = path.lstat()
            row = {'mode': stat.S_IMODE(info.st_mode)}
            if stat.S_ISLNK(info.st_mode):
                row.update(kind='symlink', target=os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                row['kind'] = 'directory'
            elif stat.S_ISREG(info.st_mode):
                row.update(kind='file', **hash_fields(path.read_bytes()))
            else:
                raise ValueError('Unsupported source inventory type: ' + str(path))
            rows[str(path.relative_to(root))] = row
    return rows


def git_state(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    return {'head': git('rev-parse', 'HEAD'), 'tree': git('rev-parse', 'HEAD^{tree}'),
            'tracked_changes': git('diff', '--name-only', 'HEAD').splitlines(),
            'untracked': git('ls-files', '--others', '--exclude-standard').splitlines()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    if not parser.parse_args().run:
        raise SystemExit('Disabled: root must approve, activate and supply --run')
    template = json.loads((HERE / 'configuration.disabled.json').read_text())
    config = json.loads((HERE / 'configuration.enabled.json').read_text())
    assert template['enabled'] is False and template['review_pins'] == []
    assert config == dict(template, enabled=True, review_pins=config['review_pins'])
    assert config['enabled'] is True and config['review_pins']
    watched = [*config['pins'], *config['review_pins'], pin(HERE / 'configuration.disabled.json'),
               pin(HERE / 'configuration.enabled.json'), pin(HERE / 'controls-result.json')]
    for row in watched:
        assert pin(row['path']) == row, row['path']
    controls = json.loads((HERE / 'controls-result.json').read_text())
    assert controls['passed'] is True and controls['error'] is None and controls['preserved'] is True
    assert [row['name'] for row in controls['cases']] == config['control_cases']
    assert all(row['passed'] is True for row in controls['cases'])
    for row in controls['watched_pins']:
        assert pin(row['path']) == row
    root = Path(config['checkout']).resolve()
    assert str(root) == config['checkout']
    release = config['release_root']
    assert release.startswith('notes/') and all(p not in ('', '.', '..') for p in release.split('/'))
    destination = root / release
    assert not os.path.lexists(destination)
    output = Path(config['results'])
    assert not os.path.lexists(output) and not output.is_relative_to(root)
    start_git = git_state(root)
    assert start_git == {'head': config['head'], 'tree': config['tree'], 'tracked_changes': [], 'untracked': []}
    before = inventory(root)
    output.mkdir()
    write(output / 'source-before.json', before)
    error, verification = None, None
    declared_files = []
    try:
        destination.mkdir(parents=True)
        artifacts, entries = [], []
        copies = list(config['copies'])
        for item in config['runtime_metadata_copies']:
            copies.append(dict(item, source=pin(HERE / item['source_name'])))
        for item in copies:
            source = item['source']
            assert pin(source['path']) == source
            relative = item['destination']
            assert relative.startswith(release + '/') and all(p not in ('', '.', '..') for p in relative.split('/'))
            path = root / relative
            assert source['bytes'] <= LIMIT and path.resolve() == path
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(Path(source['path']).read_bytes())
            actual = pin(path)
            assert {k: actual[k] for k in ('bytes', 'sha256')} == {k: source[k] for k in ('bytes', 'sha256')}
            row = {'path': relative, 'path_base': 'repository_root', 'role': item['role'],
                   'bytes': source['bytes'], 'sha256': source['sha256']}
            artifacts.append(row)
            entries.append(dict(row, historical_path=source['path'], historical_path_base='external_absolute',
                                historical_aliases=item.get('historical_aliases', [])))
            declared_files.append(relative)
        index_relative = release + '/relocation-index.json'
        index = {'format': 'legacy_evidence_relocation_index_v1',
            'path_bases': {'repository_root': 'Resolve from the checkout root after relocation.',
                          'external_absolute': 'Historical acquisition/execution locator; do not dereference for current verification.'},
            'entries': entries}
        write(root / index_relative, index)
        artifacts.append({'path': index_relative, 'path_base': 'repository_root', 'role': 'relocation_index',
                          **hash_fields((root / index_relative).read_bytes())})
        declared_files.append(index_relative)
        manifest = {'format': 'legacy_semantic_evidence_release_v1', 'state': 'prepared',
            'release_root': release, 'label': config['label'], 'method': 'legacy_semantic_tsv',
            'policy': 'root_default_route_dispositions_v1', 'producer': config['producer'],
            'artifacts': artifacts, 'forms': config['forms'],
            'publication_receipt': config['publication_receipt'],
            'schema_snapshot': config['schema_snapshot'], 'mapping_snapshot': config['mapping_snapshot'],
            'relocation_index': index_relative, 'relocated_artifacts': [r['path'] for r in entries],
            'limitations': config['limitations']}
        verification = verify_release(root, release, manifest=manifest, expected_state='prepared')
        validation_relative = release + '/validation.json'
        write(root / validation_relative, dict(verification,
            publication_completed=config['publication_completed'],
            publication_independent_audit=config['publication_independent_audit'],
            scope='Metadata check of the complete copied artifacts before final manifest; product publication and schema acceptance remain the bound historical actual05 results.'))
        artifacts.append({'path': validation_relative, 'path_base': 'repository_root', 'role': 'metadata_validation',
                          **hash_fields((root / validation_relative).read_bytes())})
        declared_files.append(validation_relative)
        manifest['state'] = 'complete'
        write(destination / 'manifest.json', manifest)
        declared_files.append(release + '/manifest.json')
        verification = verify_release(root, release)
        # The same current artifacts must be verifiable when acquisition paths
        # are treated solely as retrospective metadata in a relocated copy.
        relocated = output / 'relocated-repository'
        (relocated / release).parent.mkdir(parents=True)
        shutil.copytree(destination, relocated / release)
        relocated_verification = verify_release(relocated, release)
        assert relocated_verification == verification
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        preservation_errors = []
        after = end_git = None
        changed = added = []
        try:
            after = inventory(root)
            write(output / 'source-after.json', after)
            changed = [p for p in before if after.get(p) != before[p]]
            added = sorted(set(after) - set(before))
            assert not changed
            assert all(p == release or p.startswith(release + '/') for p in added)
            end_git = git_state(root)
            assert end_git['head'] == start_git['head'] and end_git['tree'] == start_git['tree']
            assert end_git['tracked_changes'] == []
            if error is None:
                assert sorted(p for p in added if after[p]['kind'] == 'file') == sorted(declared_files)
                assert end_git['untracked'] == sorted(declared_files), 'Some declared package files are ignored or unexpected files appeared'
        except BaseException as exc:
            preservation_errors.append({'type': type(exc).__name__, 'message': str(exc)})
        changed_pins = []
        for row in watched:
            try:
                assert pin(row['path']) == row
            except BaseException as exc:
                changed_pins.append({'path': row['path'], 'error': type(exc).__name__})
        passed = error is None and verification is not None and not preservation_errors and not changed_pins
        receipt = {'passed': passed, 'error': error, 'verification': verification,
            'git_before': start_git, 'git_after': end_git, 'old_source_entries': len(before),
            'changed_original_entries': changed, 'added_entries': added, 'declared_files': declared_files,
            'preservation_errors': preservation_errors, 'changed_pins': changed_pins,
            'scope': 'Byte-exact evidence transfer and metadata verification only; no product run, Git commit or public publication.'}
        write(output / ('completed.json' if passed else 'failure.json'), receipt)
        print(json.dumps({'passed': passed, 'files': len(declared_files), 'error': error,
                          'preservation_errors': preservation_errors}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
