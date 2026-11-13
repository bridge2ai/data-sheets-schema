"""Draft RF17 fixed offline packet stages, 2026-11-13; transfer to G before use.

Inputs: immutable source/host/config pins and a closed eight-role data plan.
Outputs: one immutable stage result and original synthetic packet artifacts in
the owned cohort. No gate launch, native/model/probe/capture/reservation call.
Final path: G/scripts/adhoc/h3_gate_stage_worker_20261113.py. This N draft refuses
execution because the actual reference root and filename must match that path.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from types import ModuleType, SimpleNamespace

G = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-pin-comparison-20261113')
S = G.parent / 'scratch-h3-gate-refinements-20261113'
FINAL = 'scripts/adhoc/h3_gate_stage_worker_20261113.py'
PLAN = 'scripts/adhoc/h3_gate_stage_roles_20261113.json'
DATA_FILES = {PLAN, 'scripts/adhoc/h3_refinement_cases_20261113.json', 'scripts/native_registration_fields_v1.json'}
ROLES = ('reference', 'later', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC', 'registered', 'expired')
PROJECTS = ('CHORUS', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC')
COUNTERS = {'native_executions': 0, 'model_calls': 0, 'probes_executed': 0, 'captures': 0, 'reservations': 0}
GIT = Path('/Library/Developer/CommandLineTools/usr/bin/git')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def parse(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate stage input key: ' + key)
            value[key] = item
        return value
    def invalid(value):
        raise ValueError('nonfinite stage input: ' + value)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)


def exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError('closed ' + label + ' fields differ')


def physical(value, *, directory=False):
    if type(value) is not str:
        raise ValueError('stage path must be text')
    path = Path(value)
    if (not path.is_absolute() or str(path) != value or '..' in path.parts
            or path.resolve(strict=True) != path or directory and not path.is_dir()):
        raise ValueError('stage path requires its physical absolute identity: ' + value)
    return path


def read(path):
    path = physical(str(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 256_000_000:
            raise ValueError('stage input must be a bounded regular file')
        raw = stream.read(256_000_001)
        after = os.fstat(stream.fileno())
    identity = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                             info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if (len(raw) != before.st_size or identity(before) != identity(after)
            or identity(after) != identity(path.lstat()) or path.resolve(strict=True) != path):
        raise ValueError('stage input changed during stable read')
    return raw


def pin(path, raw=None):
    raw = read(path) if raw is None else raw
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked(value):
    exact(value, ('path', 'bytes', 'sha256'), 'file pin')
    if type(value['bytes']) is not int or value['bytes'] < 0 or re.fullmatch('[0-9a-f]{64}', value['sha256']) is None:
        raise ValueError('invalid stage file pin values')
    raw = read(value['path'])
    if pin(value['path'], raw) != value:
        raise ValueError('stage file differs from its immutable pin: ' + value['path'])
    return raw


def save(path, value):
    path = Path(path)
    physical(str(path.parent), directory=True)
    raw = canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if read(path) != raw:
        raise ValueError('stage output readback differs')
    return pin(path, raw)


def git(*args):
    physical(str(GIT))
    return subprocess.check_output([str(GIT), '--no-replace-objects', '-C', str(G), *args],
        env={'PATH': '/Library/Developer/CommandLineTools/usr/bin:/usr/bin:/bin', 'HOME': '/var/empty',
             'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0',
             'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0'})


def source_roster(commit):
    roster = {}
    for item in git('ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not item:
            continue
        header, raw_name = item.split(b'\t', 1)
        mode, kind, identity = header.decode().split()
        name = raw_name.decode('utf-8')
        if name.endswith('.py') or name in DATA_FILES:
            if mode not in ('100644', '100755') or kind != 'blob':
                raise ValueError('tracked stage source is not an ordinary source file')
            roster[name] = (mode, identity)
    if FINAL not in roster or not DATA_FILES <= set(roster):
        raise ValueError('fixed stage source/data must be committed before execution')
    return roster


def validate_plan(value):
    exact(value, ('kind', 'version', 'scope_projects', 'synthetic_probe_branch', 'roles'), 'role plan')
    if (value['kind'] != 'SYNTHETIC-native-gate-stage-roles' or type(value['version']) is not int
            or value['version'] != 1 or value['scope_projects'] != list(PROJECTS)
            or value['synthetic_probe_branch'] != 'i' or type(value['roles']) is not list
            or len(value['roles']) != len(ROLES)):
        raise ValueError('stage plan differs from the closed eight-role format')
    projects = ('CHORUS', 'CHORUS', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC', 'AI_READI', 'CHORUS')
    for expected, project, row in zip(ROLES, projects, value['roles']):
        exact(row, ('role', 'project', 'run_date', 'valid_from', 'coverage_floor'), 'role specification')
        if row['role'] != expected or row['project'] != project:
            raise ValueError('stage role order/project differs')
        date.fromisoformat(row['run_date'])
        if not row['valid_from'].endswith('Z'):
            raise ValueError('stage validity timestamp must use UTC Z')
        datetime.fromisoformat(row['valid_from'].replace('Z', '+00:00'))
        wanted = {'state': 'registered', 'numerator': 1, 'denominator': 2, 'basis': 'receipted_part'} if expected == 'registered' else None
        if row['coverage_floor'] != wanted:
            raise ValueError('stage role has another floor')
    return value


def validate_config(value):
    exact(value, ('kind', 'version', 'source_root', 'source_commit', 'cohort', 'python', 'dependency_prefix',
        'dependency_roots', 'packet_root', 'peer_root', 'home', 'bounds', 'code_inputs', 'plan', 'bootstrap'), 'stage config')
    if value['kind'] != 'SYNTHETIC-native-gate-stage-config' or type(value['version']) is not int or value['version'] != 1:
        raise ValueError('unknown stage config version')
    if value['source_root'] != str(G) or Path(__file__) != G / FINAL or Path.cwd() != G:
        raise ValueError('stage worker requires its exact committed G source and working directory')
    cohort = physical(value['cohort'], directory=True)
    if cohort.parent != S / 'tests' or re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', cohort.name) is None:
        raise ValueError('stage cohort escaped the fixed sibling scratch')
    expected = {'dependency_prefix': cohort / 'venv', 'packet_root': cohort / 'cases/test_final_format_registration0',
                'python': cohort / 'venv/bin/python'}
    expected['peer_root'] = expected['packet_root'] / 'SYNTHETIC-shared-peer'
    expected['home'] = expected['peer_root'] / 'synthetic-home'
    if any(value[name] != str(path) for name, path in expected.items()) or sys.executable != value['python']:
        raise ValueError('stage runtime/output identities differ from the fixed cohort layout')
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError('stage interpreter requires -I -S -B')
    physical(value['dependency_prefix'], directory=True)
    sites = list((cohort / 'venv/lib').glob('python*/site-packages'))
    if (len(sites) != 1 or type(value['dependency_roots']) is not list or len(value['dependency_roots']) != 2
            or value['dependency_roots'][0] != str(sites[0])):
        raise ValueError('stage requires the one cohort site and one pinned dependency site')
    for path in value['dependency_roots']:
        physical(path, directory=True)
    if (value['bootstrap']['path'] != str(cohort / 'bootstrap.json')
            or value['bounds']['path'] != str(G.parent / 'codex-native-environment-manifest-20261113/scripts/adhoc/h3_gate_bounds_20261113.json')):
        raise ValueError('stage bootstrap/bounds path differs from its fixed role')
    bootstrap = parse(checked(value['bootstrap']))
    if (bootstrap['test_python'] != value['python'] or bootstrap['dependency_site'] != value['dependency_roots'][1]
            or bootstrap['underlying_python'] != str(Path(sys.executable).resolve(strict=True))
            or pin(Path(sys.executable).resolve(strict=True))['sha256'] != bootstrap['underlying_python_sha256']):
        raise ValueError('stage interpreter/dependencies differ from the bootstrap proof')
    for path, digest in bootstrap['files'].items():
        if pin(path)['sha256'] != digest:
            raise ValueError('stage bootstrap installed bytes changed')
    for path, identity in bootstrap['controlled_distribution']['files'].items():
        if {key: pin(path)[key] for key in ('bytes', 'sha256')} != identity:
            raise ValueError('controlled environment baseline has not been restored')
    checked(value['bounds'])
    if git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip() != value['source_commit']:
        raise ValueError('stage source HEAD differs from its frozen config')
    roster = source_roster(value['source_commit'])
    if set(value['code_inputs']) != set(roster):
        raise ValueError('stage source pin roster is incomplete or has extra entries')
    sources = {}
    for name, (mode, blob) in roster.items():
        identity = value['code_inputs'][name]
        if identity['path'] != str(G / name):
            raise ValueError('stage source path differs from its exact relative role')
        raw = checked(identity)
        algorithm = hashlib.sha1 if len(blob) == 40 else hashlib.sha256
        if (algorithm(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != blob
                or bool((G / name).lstat().st_mode & 0o111) != (mode == '100755')):
            raise ValueError('stage source bytes/mode differ from the committed tree')
        sources[name] = raw
    if value['plan'] != value['code_inputs'][PLAN]:
        raise ValueError('stage plan is not its committed data pin')
    return sources, validate_plan(parse(sources[PLAN]))


def fixed_module(relative, sources):
    path = G / relative
    module = ModuleType('fixed_stage_' + path.stem)
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(sources[relative], str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def stage_result(config, action, role=None):
    name = action + ('-' + role if role is not None else '')
    return Path(config['cohort']) / 'stages' / name / 'result.json'


def predecessor(config, config_pin, action, role=None):
    path = stage_result(config, action, role)
    if path.lstat().st_mode & 0o222:
        raise ValueError('predecessor stage proof is writable')
    value = parse(read(path))
    if (value.get('status') != 'passed' or value.get('action') != action or value.get('role') != role
            or value.get('config') != config_pin or value.get('side_effects') != COUNTERS):
        raise ValueError('predecessor stage did not pass with the same config')
    for identity in value['outputs'].values():
        checked(identity)
    return value, pin(path)


def verify_report(config, role, identity):
    value = parse(checked(identity))
    root = Path(config['packet_root'])
    if (identity['path'] != str(root / (role + '-report.json'))
            or value.get('status') != 'SYNTHETIC-registration-verified'
            or any(type(value.get(key)) is not int or value[key] != 0 for key in COUNTERS)
            or value['source_commit'] != config['source_commit']
            or value['registration']['path'] != str(root / (role + '-packet/registration.json'))):
        raise ValueError('original packet report differs from its closed role/source')
    body = parse(checked(value['registration']))['registration']
    if (body['dependencies']['base']['source_commit'] != config['source_commit']
            or body['runtime']['environment']['HOME'] != config['home']):
        raise ValueError('original registration has different frozen host/source identity')
    checked(value['byte_inventory'])
    return value


def canary(config, config_pin, sources):
    previous, previous_pin = predecessor(config, config_pin, 'build', 'reference')
    reference = verify_report(config, 'reference', previous['outputs']['report'])
    path = S / 'demonstrations' / (Path(config['cohort']).name + '-self-canary/demonstration-results.json')
    value = parse(read(path))
    if (value.get('status') != 'canary_passed' or value.get('mode') != 'canary_only'
            or value.get('positive_reuse') is not False or len(value.get('cases', [])) != 1
            or value['original_registrations'] != {'reference': reference['registration']}):
        raise ValueError('later stages require this cohort original reference self-canary')
    row = value['cases'][0]
    if row['name'] != '01-self' or row['expected'] != 'equal' or row['status'] != 'equal':
        raise ValueError('reference canary is not its one complete equal comparison')
    driver = fixed_module('scripts/adhoc/run_h3_refinement_demonstration_20261113.py', sources)
    for mapping, declared in ((driver.CODE_INPUTS, value['code_inputs']), (driver.TOOLS, value['tools'])):
        if set(mapping) != set(declared):
            raise ValueError('reference canary tool roster differs')
        for name, source in mapping.items():
            if declared[name] != config['code_inputs'][str(source.relative_to(G))]:
                raise ValueError('reference canary used another frozen source')
            checked(declared[name])
    result = parse(checked(row['result']))
    command = parse(checked(row['command_result']))
    driver.verify_result(result, {'expected': 'equal'}, command)
    return {'reference_stage': previous_pin, 'reference_canary': pin(path)}


def install_audit(config, action, role, sources, output):
    root = Path(config['packet_root'])
    allowed = [output.parent]
    if action == 'setup-peer':
        allowed += [Path(config['peer_root'])]
    elif action == 'build':
        allowed += [root / (role + '-packet'), root / (role + '-report.json')]
    elif action == 'snapshots':
        allowed += [root / 'distribution_version', root / 'installed_file', root / 'environment-variants.json']
        site = Path(config['dependency_roots'][0])
        allowed += [site / 'h3_gate_evidence_dependency.py', site / 'h3_gate_evidence_dependency-1.dist-info/METADATA',
                    site / 'h3_gate_evidence_dependency-1.dist-info/RECORD']
    else:
        allowed += [root / 'expanded-project-report.json']
    def audit(event, arguments):
        if event.startswith('socket.') or event in {'os.system', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.exec', 'pty.spawn', 'os.symlink'}:
            raise RuntimeError('fixed stage forbids native/network execution or path aliases')
        if event == 'subprocess.Popen':
            executable, command, _, environment = arguments
            search_path = (os.environ if environment is None else environment).get('PATH', '').split(os.pathsep)
            fixed_git = Path(executable) == GIT or executable == 'git' and search_path[0] == str(GIT.parent)
            if (not fixed_git or type(command) not in (list, tuple)
                    or not any(item in ('rev-parse', 'ls-tree', 'cat-file', 'diff', 'status', 'log', 'show') for item in command)):
                raise RuntimeError('fixed stage permits only read-only local Git children')
        if event == 'compile':
            raw, filename = arguments
            if isinstance(filename, str) and Path(filename).is_absolute() and Path(filename).is_relative_to(G):
                relative = str(Path(filename).relative_to(G))
                if isinstance(raw, str):
                    raw = raw.encode('utf-8')
                if not isinstance(raw, bytes) or sources.get(relative) != raw:
                    raise RuntimeError('compiled stage source differs from captured committed bytes')
        paths = []
        if event == 'open':
            path, mode, flags = arguments
            if (isinstance(mode, str) and any(char in mode for char in 'wax+')
                    or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                paths = [path]
        elif event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.truncate', 'os.utime'}:
            paths = [arguments[0]]
        elif event in {'os.rename', 'os.link'}:
            paths = list(arguments[:2])
        for path in paths:
            if isinstance(path, int):
                continue
            target = Path(os.fsdecode(path)).absolute().resolve()
            if not any(target == item or target.is_relative_to(item) for item in allowed):
                raise RuntimeError('fixed stage write escaped its named artifact roots: ' + str(target))
    sys.addaudithook(audit)


def execute(config, config_pin, sources, plan, action, role, output):
    bootstrap = fixed_module('scripts/native_registration_validation_worker.py', sources)
    origins = bootstrap.bootstrap(SimpleNamespace(reference_root=str(G), dependency_root=config['dependency_roots'],
        dependency_prefix=config['dependency_prefix']), G)
    finder = bootstrap.ReferenceSourceFinder(G, {name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()
        if name.endswith('.py')}, config['dependency_roots'])
    sys.meta_path.insert(0, finder)
    install_audit(config, action, role, sources, output)
    inputs, outputs = {}, {}
    root = Path(config['packet_root'])
    if action == 'setup-peer':
        from tests.utils.native_synthetic_evidence import prepare_shared_peer
        home = prepare_shared_peer(Path(config['peer_root']))
        if str(home) != config['home']:
            raise ValueError('shared peer returned another HOME')
        outputs = {'peer': pin(home.parent / 'ordinary-python-test-peer'), 'updater': pin(home.parent / 'updater/current')}
    elif action == 'build':
        _, inputs['setup_peer'] = predecessor(config, config_pin, 'setup-peer')
        index = ROLES.index(role)
        if index:
            _, inputs['previous_build'] = predecessor(config, config_pin, 'build', ROLES[index - 1])
            inputs.update(canary(config, config_pin, sources))
        builder = fixed_module('scripts/adhoc/build_h3_gate_rehearsal_20261113.py', sources)
        spec = plan['roles'][index]
        report = builder.build(root / (role + '-packet'), project=spec['project'],
            identity='SYNTHETIC-refinement-' + role, run_date=spec['run_date'], valid_from=spec['valid_from'],
            coverage_floor=spec['coverage_floor'], host_home=Path(config['home']), bounds_path=Path(config['bounds']['path']))
        outputs['report'] = save(root / (role + '-report.json'), report)
        verified = verify_report(config, role, outputs['report'])
        outputs.update(registration=verified['registration'], byte_inventory=verified['byte_inventory'])
    elif action == 'snapshots':
        reports = {}
        for name in ROLES:
            previous, inputs[name] = predecessor(config, config_pin, 'build', name)
            reports[name] = verify_report(config, name, previous['outputs']['report'])
        inputs.update(canary(config, config_pin, sources))
        body = parse(checked(reports['reference']['registration']))['registration']
        environment_pin = parse(body['preparation_raw_json'].encode())['registration']['environment_manifest']
        helper = fixed_module('scripts/adhoc/h3_environment_snapshots_20261113.py', sources)
        values = helper.build_snapshots(root, environment_pin)
        outputs['environment_variants'] = save(root / 'environment-variants.json', values)
        for name, row in values.items():
            outputs[name + '_manifest'] = row['manifest']
            outputs[name + '_provenance'] = row['provenance']
    else:
        reports = {}
        for name in ROLES:
            previous, inputs[name] = predecessor(config, config_pin, 'build', name)
            reports[name] = verify_report(config, name, previous['outputs']['report'])
        previous, inputs['snapshots'] = predecessor(config, config_pin, 'snapshots')
        environment = parse(checked(previous['outputs']['environment_variants']))
        control_path = Path(config['cohort']) / 'source-commit-controls.json'
        inputs['source_commit_controls'] = pin(control_path)
        controls = parse(checked(inputs['source_commit_controls']))
        document = parse(checked(controls['manifest']))
        export = parse(checked(controls['export']))
        if ({key: value for key, value in controls.items() if key != 'manifest'} != document
                or controls['status'] != 'SYNTHETIC-controls-built' or controls['trusted_root'] != str(G)
                or export['trusted_commit'] != config['source_commit']):
            raise ValueError('private controls differ from this frozen source stratum')
        for key in ('reference', 'candidate', 'reference_report', 'candidate_report', 'self_gate', 'tuple', 'floor'):
            checked(controls[key])
        values = {'kind': 'SYNTHETIC-native-gate-refinement-rehearsals', 'version': 1,
            'scope_projects': list(PROJECTS), 'synthetic_probe_branch': 'i', 'packets': reports,
            'environment_variants': environment, 'source_commit_controls': controls}
        outputs['report'] = save(root / 'expanded-project-report.json', values)
    return {'status': 'passed', 'action': action, 'role': role, 'config': config_pin,
            'inputs': inputs, 'outputs': outputs, 'origins': origins, 'side_effects': dict(COUNTERS)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--config-bytes', type=int, required=True)
    parser.add_argument('--action', required=True, choices=('setup-peer', 'build', 'snapshots', 'assemble-report'))
    parser.add_argument('--role', choices=ROLES)
    args = parser.parse_args()
    if (args.action == 'build') != (args.role is not None):
        parser.error('exactly build requires one closed role')
    config_pin = {'path': str(args.config), 'bytes': args.config_bytes, 'sha256': args.config_sha256}
    config = parse(checked(config_pin))
    sources, plan = validate_config(config)
    if args.config != Path(config['cohort']) / 'stage-config.json' or args.config.lstat().st_mode & 0o222:
        raise ValueError('stage config must be the immutable fixed cohort declaration')
    output = stage_result(config, args.action, args.role)
    physical(str(output.parent), directory=True)
    if output.exists() or output.is_symlink():
        raise ValueError('stage result must be fresh')
    result = None
    try:
        result = execute(config, config_pin, sources, plan, args.action, args.role, output)
        validate_config(config)
        checked(config_pin)
        for identity in (*result['inputs'].values(), *result['outputs'].values()):
            checked(identity)
    except Exception as error:
        result = {'status': 'held', 'action': args.action, 'role': args.role, 'config': config_pin,
                  'error': type(error).__name__ + ': ' + str(error), 'outputs': {}, 'side_effects': dict(COUNTERS)}
    result_pin = save(output, result)
    print(json.dumps({'status': result['status'], 'result': result_pin}, sort_keys=True))
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
