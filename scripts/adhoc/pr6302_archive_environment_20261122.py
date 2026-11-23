"""Build a disposable offline interpreter for one PR6302 archive, 2026-11-22.

Inputs: pinned local environment audit, read-only source venv/cache, fresh archive.
Outputs: independent CoW environment, installer logs, inventories and origin probes.
Only explicit setup mode mutates the clone; probes write fresh evidence only.
Never edits the live environment,
changes production startup, downloads dependencies or runs tests/native providers.
"""

import argparse
import base64
import csv
import ctypes
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import zipfile


BUILD = {'poetry-core': '2.5.0', 'poetry-dynamic-versioning': '1.10.1', 'dunamai': '1.26.3'}
BUILD_INSTALLED = {'jinja2': '3.1.6', 'markupsafe': '2.1.3', 'packaging': '23.2', 'tomlkit': '0.13.3'}
SCRIPT_HELPER = 'pr6302_archive_environment_scripts_20261122.py'
SANDBOX = Path('/usr/bin/sandbox-exec')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def read(path):
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and path.resolve(strict=True) == path, 'physical regular file required: ' + str(path))
    raw = path.read_bytes()
    after = path.lstat()
    need(identity(before) == identity(after) and len(raw) == before.st_size, 'file changed while read: ' + str(path))
    return raw


def identity(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def fresh(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    need(read(path) == raw, 'output readback differs')


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
           .replace(chr(64), '\\u0040') + '\n').encode()
    fresh(path, raw)
    return pin(path)


def physical_directory(path):
    need(path.is_absolute() and path.resolve(strict=True) == path
         and stat.S_ISDIR(path.lstat().st_mode), 'physical canonical directory required')


def fresh_directory_target(source, target):
    physical_directory(source)
    physical_directory(target.parent)
    need(target.is_absolute() and not target.exists() and not target.is_symlink()
         and not target.is_relative_to(source), 'fresh independent directory target required')


def boundaries(source, tree, output):
    physical_directory(source)
    physical_directory(tree)
    fresh_directory_target(source, output)
    project = source.parent
    need(not tree.is_relative_to(project) and not source.is_relative_to(tree),
         'archive and live project/environment must be disjoint')
    need(not output.is_relative_to(project) and not project.is_relative_to(output)
         and not output.is_relative_to(tree) and not tree.is_relative_to(output),
         'setup output must be disjoint from archive and live project')


def record_targets(source, record, raw):
    """An installer must never follow a copied third-party RECORD outside it."""
    physical_directory(source)
    need(record.is_relative_to(source), 'RECORD is outside the selected environment')
    site = record.parent.parent
    targets = []
    for row in csv.reader(io.StringIO(raw.decode('utf-8'), newline='')):
        need(len(row) == 3 and row[0] and not Path(row[0]).is_absolute()
             and not any(character in row[0] for character in ('\0', '\r', '\n')),
             'third-party RECORD requires relative paths')
        target = (site / row[0]).resolve(strict=False)
        need(target.is_relative_to(source), 'third-party RECORD escapes environment')
        need(target not in targets, 'third-party RECORD repeats a target')
        targets.append(target)
    return targets


def inventory(root, *, archive=False):
    rows = {}
    def failed(error):
        raise error
    for directory, folders, files in os.walk(root, followlinks=False, onerror=failed):
        if archive:
            folders[:] = [name for name in folders if name != '.git']
            files = [name for name in files if name != '.git']
        for name in sorted(folders + files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            row = {'mode': stat.S_IMODE(info.st_mode)}
            if stat.S_ISDIR(info.st_mode):
                row['kind'] = 'directory'
            elif stat.S_ISLNK(info.st_mode):
                row.update(kind='symlink', target=os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                raw = read(path)
                row.update(kind='file', bytes=len(raw), sha256=sha(raw))
            else:
                raise ValueError('special filesystem entry refused: ' + str(path))
            rows[relative] = row
    return rows


def require_unchanged(root, expected, label, *, archive=False):
    need(inventory(root, archive=archive) == expected, label + ' changed')


def clone(source, target, rows):
    fresh_directory_target(source, target)
    need(sys.platform == 'darwin', 'this reviewed copy method requires macOS')
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    clonefile = library.clonefile
    clonefile.argtypes, clonefile.restype = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int], ctypes.c_int
    target.mkdir()
    for name, row in sorted(rows.items(), key=lambda item: (len(Path(item[0]).parts), item[0])):
        original, copied = source / name, target / name
        if row['kind'] == 'directory':
            copied.mkdir(mode=row['mode'])
            copied.chmod(row['mode'])
        elif row['kind'] == 'symlink':
            need(name in {'bin/python', 'bin/python3', 'bin/python3.13'}, 'unexpected environment alias: ' + name)
            copied.symlink_to(row['target'])
            need(copied.resolve(strict=True) == original.resolve(strict=True), 'interpreter alias changed')
        else:
            if clonefile(os.fsencode(original), os.fsencode(copied), 0):
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error), str(copied))
            need((original.stat().st_dev, original.stat().st_ino)
                 != (copied.stat().st_dev, copied.stat().st_ino), 'copy shares a live source inode')
    need(inventory(target) == rows, 'cloned bytes/modes/entry roster differ from source')


def cache_payload(candidate):
    if candidate['kind'] == 'original_cached_wheel':
        path = Path(candidate['artifact']['path'])
        raw = read(path)
        need(sha(raw) == candidate['artifact']['sha256'], 'cached wheel digest changed')
        with zipfile.ZipFile(io.BytesIO(raw)) as wheel:
            names = [member.filename for member in wheel.infolist() if not member.is_dir()]
            need(len(names) == len(set(names)), 'duplicate wheel members')
            bodies = {name: wheel.read(name) for name in names}
    else:
        need(candidate['kind'] == 'original_uv_unpacked_wheel', 'unknown cache input kind')
        root = Path(candidate['path'])
        physical_directory(root)
        bodies = {}
        for directory, folders, files in os.walk(root, followlinks=False):
            need(not any((Path(directory) / name).is_symlink() for name in folders), 'cached directory alias')
            for name in files:
                path = Path(directory) / name
                if path.suffix != '.pyc':
                    bodies[path.relative_to(root).as_posix()] = read(path)
    metas = [name for name in bodies if name.endswith('.dist-info/METADATA')]
    need(len(metas) == 1, 'cached package metadata is ambiguous')
    dist_info = metas[0].rsplit('/', 1)[0]
    metadata = BytesParser().parsebytes(bodies[metas[0]])
    need(re.sub('[-_.]+', '-', metadata['Name']).lower() == candidate['name']
         and metadata['Version'] == candidate['version'], 'cached package identity differs')
    record = bodies[dist_info + '/RECORD']
    need(sha(record) == candidate['record_sha256'], 'cached RECORD changed')
    declared, rows = set(), []
    for entry in csv.reader(io.StringIO(record.decode(), newline='')):
        need(len(entry) == 3, 'malformed cached RECORD')
        path = PurePosixPath(entry[0])
        need(not path.is_absolute() and '..' not in path.parts and str(path) == entry[0]
             and entry[0] not in declared, 'invalid cached RECORD path')
        declared.add(entry[0])
        body = bodies[entry[0]]
        if entry[1]:
            algorithm, separator, expected = entry[1].partition('=')
            need(separator and algorithm in {'sha256', 'sha384', 'sha512'}, 'unsupported cached hash')
            actual = base64.urlsafe_b64encode(hashlib.new(algorithm, body).digest()).rstrip(b'=').decode()
            need(actual == expected and entry[2] == str(len(body)), 'cached payload differs from RECORD')
        else:
            need(entry[0] == dist_info + '/RECORD' and not entry[2], 'unhashed cached payload')
        rows.append({'path': entry[0], 'bytes': len(body), 'sha256': sha(body)})
    need(declared == set(bodies) and sha(encoded(sorted(rows, key=lambda row: row['path'])))
         == candidate['payload_roster_sha256'], 'cached payload roster differs')
    wheel_metadata = bodies[dist_info + '/WHEEL']
    need(sha(wheel_metadata) == candidate['wheel_metadata_sha256'], 'cached WHEEL changed')
    wheel = BytesParser().parsebytes(wheel_metadata)
    need(wheel.get('Root-Is-Purelib') == 'true' and wheel.get_all('Tag') == ['py3-none-any'],
         'only the reviewed universal build dependency wheels are supported')
    return bodies


def wheel_file(candidate, bodies, target):
    filename = candidate['name'].replace('-', '_') + '-' + candidate['version'] + '-py3-none-any.whl'
    path = target / filename
    if candidate['kind'] == 'original_cached_wheel':
        fresh(path, read(Path(candidate['artifact']['path'])))
    else:
        with path.open('xb') as stream:
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as wheel:
                for name, raw in sorted(bodies.items()):
                    info = zipfile.ZipInfo(name, date_time=(2026, 11, 22, 0, 0, 0))
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    wheel.writestr(info, raw)
    with zipfile.ZipFile(path) as wheel:
        need({name: wheel.read(name) for name in wheel.namelist()} == bodies, 'staged wheel payload changed')
    return path


def environment(output, cloned):
    return {'HOME': str(output / 'home'), 'TMPDIR': str(output / 'tmp'),
        'PATH': str(cloned / 'bin') + ':/usr/bin:/bin:/usr/sbin:/sbin',
        'VIRTUAL_ENV': str(cloned), 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
        'PIP_CONFIG_FILE': '/dev/null', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
        'XDG_CACHE_HOME': str(output / 'cache'), 'UV_OFFLINE': '1'}


def run(command, *, tree, output, cloned, label, seconds=600, allow_source_write=False):
    roots = [output] + ([tree] if allow_source_write else [])
    profile = '(version 1)(allow default)(deny network*)(deny file-write*)' + \
        '(allow file-write* (literal "/dev/null") ' + ' '.join('(subpath ' + json.dumps(str(path)) + ')' for path in roots) + ')'
    wrapped = [str(SANDBOX), '-p', profile, *map(str, command)]
    logfile = output / (label + '.log')
    child = None
    code = None
    try:
        with logfile.open('xb') as stream:
            child = subprocess.Popen(wrapped, cwd=tree, env=environment(output, cloned),
                                     stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            code = child.wait(timeout=seconds)
    except BaseException as error:
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                child.wait()
                code = child.returncode
        try:
            save(output / (label + '-command.json'), {'command': list(map(str, command)),
                'cwd': str(tree), 'returncode': code, 'sandbox_profile': profile,
                'timeout_seconds': seconds, 'error_type': type(error).__name__, 'log': pin(logfile)})
        except Exception:
            pass
        raise
    record = {'command': list(map(str, command)), 'cwd': str(tree), 'returncode': code,
              'sandbox_profile': profile, 'log': pin(logfile)}
    save(output / (label + '-command.json'), record)
    need(code == 0, 'offline environment step failed: ' + label + '; retained ' + str(logfile))
    return record


def archive_head(tree):
    physical_directory(tree / '.git')
    raw = subprocess.check_output(['git', '-C', str(tree), 'rev-parse', '--verify', 'HEAD^{commit}'],
        env={'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_CONFIG_NOSYSTEM': '1',
             'GIT_CONFIG_GLOBAL': '/dev/null'})
    need(re.fullmatch(b'[0-9a-f]{40}\n', raw), 'archive requires one exact committed HEAD')
    return raw.decode().strip()


def quarantine(source, cloned, audit, output):
    rows = [row for row in audit['distributions'] if row['name'] == 'data-sheets-schema']
    need(len(rows) == 1, 'exactly one copied own distribution required')
    site = Path(audit['site_packages']).relative_to(source)
    metadata = Path(rows[0]['dist_info']).relative_to(source)
    need(metadata.parent == site and metadata.name.endswith('.dist-info'), 'own metadata path differs')
    paths = [metadata, site / 'data_sheets_schema.pth', Path('bin/d4d'), Path('bin/fairscape-cli')]
    destination = output / 'quarantine'
    destination.mkdir()
    records = []
    for relative in paths:
        original, moved = cloned / relative, destination / relative.name
        need(original.exists() and not original.is_symlink(), 'expected copied own artifact missing')
        original.rename(moved)
        records.append({'original': str(original), 'retained': str(moved),
                        'tree': inventory(moved) if moved.is_dir() else pin(moved)})
    return records


def probe(args):
    import importlib
    from importlib import metadata
    tree, cloned = args.tree, args.clone_venv
    need(Path(sys.prefix) == cloned and Path(sys.executable) == cloned / 'bin/python', 'probe interpreter differs')
    package = importlib.import_module('data_sheets_schema')
    need({Path(path).resolve() for path in package.__path__} == {tree / 'src/data_sheets_schema'},
         'installed project namespace differs from archive')
    verifier = importlib.import_module('data_sheets_schema.native_prepared_verifier')
    expected = tree / 'src/data_sheets_schema/native_prepared_verifier.py'
    need(Path(verifier.__file__).resolve() == expected, 'isolated verifier resolves outside archive')
    old_project = args.source_venv.parent
    for value in sys.path:
        if value:
            path = Path(value).resolve()
            need(not path.is_relative_to(old_project), 'probe borrowed original project/environment path')
    site = next(cloned.glob('lib/python*/site-packages'))
    distributions = list(metadata.distributions(path=[str(site)]))
    names = [re.sub('[-_.]+', '-', row.metadata['Name']).lower() for row in distributions]
    need(len(names) == len(set(names)) and names.count('data-sheets-schema') == 1, 'duplicate installed metadata')
    dependencies = {}
    for name in ('linkml', 'linkml_runtime', 'jinja2', 'packaging', 'tomlkit', 'poetry.core',
                 'poetry_dynamic_versioning', 'dunamai'):
        module = importlib.import_module(name)
        origin = Path(module.__file__).resolve()
        need(origin.is_relative_to(site), 'dependency resolves outside cloned environment: ' + name)
        dependencies[name] = pin(origin)
    own = distributions[names.index('data-sheets-schema')]
    direct = json.loads(own.read_text('direct_url.json'))
    need(direct.get('dir_info') == {'editable': True} and direct.get('url') == tree.as_uri(),
         'editable installation does not bind this archive')
    value = {'passed': True, 'isolated': bool(sys.flags.isolated), 'sys_executable': sys.executable,
        'sys_prefix': sys.prefix, 'sys_base_prefix': sys.base_prefix, 'sys_path': list(sys.path),
        'project_roots': list(package.__path__), 'verifier': pin(expected),
        'dependencies': dependencies, 'own_direct_url': direct, 'distribution_count': len(names)}
    save(args.output, value)


def _setup(args, state):
    source, tree, output = args.source_venv, args.tree, args.output
    boundaries(source, tree, output)
    source_commit = archive_head(tree)
    need(SANDBOX.is_file(), 'macOS offline setup sandbox is unavailable')
    audit_raw = read(args.audit)
    need(sha(audit_raw) == args.audit_sha256, 'environment audit digest differs')
    audit = json.loads(audit_raw)
    need(audit['kind'] == 'pr6302_offline_install_input_audit' and audit['venv'] == str(source)
         and not audit['duplicate_distribution_names'], 'audit identity differs')
    installed = {row['name']: row for row in audit['distributions']}
    for name, version in BUILD_INSTALLED.items():
        need(installed[name]['version'] == version, 'installed backend dependency version differs')
    for row in audit['distributions']:
        need(pin(Path(row['record']['path'])) == row['record'], 'installed RECORD changed since audit')
        need(sha(read(Path(row['dist_info']) / 'METADATA')) == row['metadata_sha256'], 'installed metadata changed since audit')
        if row['name'] != 'data-sheets-schema':
            record_targets(source, Path(row['record']['path']), read(Path(row['record']['path'])))
    chosen = []
    for name, version in BUILD.items():
        candidates = [row for row in audit['cache_inputs'] if row['name'] == name and row['version'] == version
                      and row['record_verified'] is True]
        need(candidates, 'required exact offline build dependency unavailable: ' + name)
        candidate = sorted(candidates, key=lambda row: (row['kind'], row.get('path', row.get('artifact', {}).get('path', ''))))[0]
        chosen.append((candidate, cache_payload(candidate)))
    before_source, before_tree = inventory(source), inventory(tree, archive=True)
    state.update(source=source, tree=tree, output=output,
                 before_source=before_source, before_tree=before_tree)
    output.mkdir()
    state['output_created'] = True
    for name in ('home', 'tmp', 'cache', 'wheels'):
        (output / name).mkdir()
    save(output / 'source-environment-before.json', before_source)
    save(output / 'archive-before.json', before_tree)
    fresh(output / 'input-audit.json', audit_raw)
    script = Path(__file__).with_name(SCRIPT_HELPER)
    save(output / 'setup-request.json', {'source_commit': source_commit, 'tree': str(tree),
        'source_venv': str(source), 'output': str(output), 'audit': pin(args.audit),
        'helper': pin(Path(__file__)), 'script_helper': pin(script),
        'selected_build_inputs': [candidate for candidate, _ in chosen]})
    plan = output / 'launcher-plan.json'
    cloned = output / 'venv'
    commands = [run([source / 'bin/python', '-I', '-B', script, 'plan', '--source-venv', source,
        '--audit', args.audit, '--audit-sha256', args.audit_sha256, '--output', plan],
        tree=tree, output=output, cloned=cloned, label='launcher-plan')]
    clone(source, cloned, before_source)
    require_unchanged(source, before_source, 'live environment during clone')
    quarantined = quarantine(source, cloned, audit, output)
    save(output / 'quarantine.json', quarantined)
    commands.append(run([cloned / 'bin/python', '-I', '-B', script, 'relocate', '--source-venv', source,
        '--clone-venv', cloned, '--plan', plan, '--plan-sha256', pin(plan)['sha256'],
        '--output', output / 'launcher-relocation.json'], tree=tree, output=output,
        cloned=cloned, label='launcher-relocation'))
    wheels = [wheel_file(candidate, bodies, output / 'wheels') for candidate, bodies in chosen]
    pip = [cloned / 'bin/python', '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check',
           'install', '--no-index', '--no-deps', '--no-build-isolation', '--no-cache-dir', '--no-compile']
    commands.append(run([*pip, *wheels], tree=tree, output=output, cloned=cloned, label='backend-install'))
    try:
        commands.append(run([*pip, '--editable', tree], tree=tree, output=output, cloned=cloned,
                            label='editable-install', allow_source_write=True))
    except BaseException:
        try:
            after_tree = inventory(tree, archive=True)
            receipt = save(output / 'archive-after-install.json', after_tree)
            state['editable_archive_check'] = {'unchanged': after_tree == before_tree, 'inventory': receipt}
        except Exception as check_error:
            state['editable_archive_check'] = {'unchanged': None, 'error_type': type(check_error).__name__}
        raise
    else:
        after_tree = inventory(tree, archive=True)
        save(output / 'archive-after-install.json', after_tree)
        need(after_tree == before_tree, 'editable backend left changed archive bytes or entries')
    commands.append(run([cloned / 'bin/python', '-I', '-B', script, 'verify', '--clone-venv', cloned,
        '--source-venv', source, '--plan', plan, '--plan-sha256', pin(plan)['sha256'],
        '--output', output / 'installed-launcher-verification.json'], tree=tree, output=output,
        cloned=cloned, label='installed-launcher-verification'))
    for name, flags in [('normal', ['-P', '-s', '-B']), ('isolated', ['-I', '-B'])]:
        commands.append(run([cloned / 'bin/python', *flags, Path(__file__), 'probe', '--source-venv', source,
            '--clone-venv', cloned, '--tree', tree, '--output', output / (name + '-origins.json')],
            tree=tree, output=output, cloned=cloned, label=name + '-origins'))
    require_unchanged(source, before_source, 'live environment during setup')
    require_unchanged(tree, before_tree, 'archive during setup', archive=True)
    need(archive_head(tree) == source_commit, 'archive HEAD changed during setup')
    for candidate, bodies in chosen:
        need(cache_payload(candidate) == bodies, 'original build cache changed during setup')
    result = {'kind': 'pr6302_disposable_archive_environment', 'version': 1, 'passed': True,
        'tree': str(tree), 'source_commit': source_commit,
        'source_venv': str(source), 'python': str(cloned / 'bin/python'),
        'clone_venv': str(cloned), 'audit': pin(args.audit), 'helper': pin(Path(__file__)),
        'script_helper': pin(script), 'copy_method': 'macOS clonefile; distinct regular-file inodes',
        'source_environment_unchanged': True, 'archive_unchanged': True, 'cache_inputs_unchanged': True,
        'build_inputs': [candidate for candidate, _ in chosen], 'wheels': [pin(path) for path in wheels],
        'commands': commands, 'launcher_plan': pin(plan),
        'launcher_relocation': pin(output / 'launcher-relocation.json'),
        'installed_launcher_verification': pin(output / 'installed-launcher-verification.json'),
        'normal_origins': pin(output / 'normal-origins.json'), 'isolated_origins': pin(output / 'isolated-origins.json'),
        'limits': 'One archive environment; setup sandbox only. No tests or native generation qualification.'}
    save(output / 'environment.json', result)
    print(json.dumps({'python': result['python'], 'environment': pin(output / 'environment.json')}, sort_keys=True))


def setup(args):
    state = {}
    try:
        _setup(args, state)
    except BaseException as error:
        if state.get('output_created'):
            failure = {'kind': 'pr6302_disposable_environment_failure', 'version': 1,
                       'passed': False, 'error_type': type(error).__name__,
                       'error': str(error)[:2048], 'checks': {},
                       'editable_archive_check': state.get('editable_archive_check')}
            for label, path, before, archive in (
                    ('source_environment', state['source'], state['before_source'], False),
                    ('archive', state['tree'], state['before_tree'], True)):
                try:
                    after = inventory(path, archive=archive)
                    receipt = save(state['output'] / (label + '-after-failure.json'), after)
                    failure['checks'][label] = {'unchanged': after == before, 'inventory': receipt}
                except Exception as check_error:
                    failure['checks'][label] = {'unchanged': None, 'error_type': type(check_error).__name__}
            try:
                save(state['output'] / 'failure.json', failure)
            except Exception:
                pass
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('setup', 'probe'))
    parser.add_argument('--source-venv', type=Path, required=True)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--audit-sha256')
    parser.add_argument('--clone-venv', type=Path)
    args = parser.parse_args()
    need(bytes([64]) not in read(Path(__file__)), 'helper contains a prohibited literal character')
    if args.mode == 'setup':
        need(args.audit is not None and re.fullmatch('[0-9a-f]{64}', args.audit_sha256 or ''), 'pinned audit required')
        setup(args)
    else:
        need(args.clone_venv is not None, 'probe clone identity required')
        probe(args)


if __name__ == '__main__':
    main()
