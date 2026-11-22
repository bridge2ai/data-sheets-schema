#!/usr/bin/env python3
"""Run PR6302 round2 mocked tests on a committed archive, 2026-11-21.

Inputs: this feature branch HEAD, selected local venv, output path and pytest args.
Outputs: retained archive, independent Git metadata, logs, import witness and pins.
No native binary or production source is executed by this helper.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import threading

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python')
SUBMODULE_SOURCE = PYTHON.parent.parent.parent / 'fairscape_models'
BASE = '5581d57f2476ac1d02270b39e3e4234f0403cff6'
PLUGIN = 'scripts.adhoc.test_pr6302_round2_20261121'
CI_REPOSITORY_URL = 'https://github.com/bridge2ai/data-sheets-schema'
TARGETED = ['tests/test_native_permission_probe.py', 'tests/test_native_shared_permissions.py',
            'tests/test_native_permission_source_read_variants.py', 'tests/test_native_model_aliases.py',
            'tests/test_native_permission_projection_derivation.py',
            'tests/test_native_permission_probe_stop_record.py', 'tests/test_native_u4b_probe_sequence.py',
            'tests/test_native_generation_frontdoor.py', 'tests/test_native_stage_root_grant.py',
            'tests/test_native_stage_root_diagnostic.py', 'tests/test_native_stage_root_boundary.py',
            'tests/test_native_permission_wire_profile.py', 'tests/test_native_shared_permission_protocol.py',
            'tests/test_native_shared_permission_split.py', 'tests/test_native_shared_registration.py',
            'tests/test_native_h1_scanner_authority.py']


class AgentGitObserver:
    """Optional bounded observation; never supplies a Git result or authority.

    Fixture wrappers may intervene between _git and the guarded run function.
    Only an exact source/function match within eight caller frames is observed.
    Replacements that bypass this wrapper and deeper chains are unobserved.
    Text hashes describe returned text encoded as UTF-8, not raw pipe bytes.
    """
    MAX_FRAMES = 8
    STDERR_BYTES = 8192

    def __init__(self, directory, *, root=ROOT):
        self.path = directory / 'agent-pin-git.jsonl'
        self.source = str(root / 'src/data_sheets_schema/agent_pin.py')
        self.problems, self.attempts, self.records = [], 0, 0
        self.installed = False
        self._lock = threading.Lock()

    def _problem(self, operation, error):
        # Exception strings can include caller data; retain only their class.
        if len(self.problems) < 32:
            self.problems.append(operation + ': ' + type(error).__name__)

    def _context(self, frame):
        try:
            for depth in range(self.MAX_FRAMES):
                if frame is None:
                    break
                if frame.f_code.co_filename == self.source and frame.f_code.co_name == '_git':
                    values = frame.f_locals
                    root, kind = values.get('root'), values.get('kind')
                    return {'source': self.source, 'function': '_git', 'caller_depth': depth,
                        'resource_root': None if root is None else os.fspath(root),
                        'resource_kind': kind if type(kind) is str else None}
                frame = frame.f_back
            return None
        finally:
            del frame

    def _output(self, value, *, stderr=False):
        if value is None:
            return {'type': 'none', 'bytes': None, 'sha256': None}
        if type(value) is str:
            raw, basis = value.encode('utf-8', errors='surrogatepass'), 'returned_text_utf8_surrogatepass'
        elif type(value) is bytes:
            raw, basis = value, 'returned_bytes'
        else:
            raise TypeError('unexpected captured output type')
        result = {'type': type(value).__name__, 'basis': basis,
                  'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if stderr:
            text = raw[:self.STDERR_BYTES].decode('utf-8', errors='replace').encode('utf-8')
            result.update(text=text[:self.STDERR_BYTES].decode('utf-8', errors='ignore'),
                          truncated=len(raw) > self.STDERR_BYTES or len(text) > self.STDERR_BYTES)
        return result

    def _append(self, record):
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + '\n')

    def _record(self, record, result=None, error=None):
        try:
            with self._lock:
                self.attempts += 1
                record['sequence'] = self.attempts
                record['outcome'] = 'exception' if error is not None else 'returned'
                record['exception_type'] = type(error).__name__ if error is not None else None
                value = error if error is not None else result
                record['returncode'] = getattr(value, 'returncode', None)
                record['stdout'] = self._output(getattr(value, 'stdout', None))
                record['stderr'] = self._output(getattr(value, 'stderr', None), stderr=True)
                self._append(record)
                self.records += 1
        except Exception as recording_error:
            self._problem('record', recording_error)

    def install(self):
        if self.installed:
            raise ValueError('agent Git observer already installed')
        original = subprocess.run

        def observed(*args, **kwargs):
            record = None
            try:
                context = self._context(sys._getframe(1))
                if context is not None:
                    argv = args[0] if args else kwargs.get('args')
                    if (type(argv) not in (list, tuple) or not argv or argv[0] != 'git'
                            or any(type(part) is not str for part in argv)):
                        raise ValueError('unexpected agent Git argv')
                    cwd = kwargs.get('cwd')
                    record = {'argv': list(argv), 'cwd': None if cwd is None else os.fspath(cwd),
                              'context': context}
            except Exception as recording_error:
                self._problem('context', recording_error)
            try:
                result = original(*args, **kwargs)
            except BaseException as error:
                if record is not None:
                    self._record(record, error=error)
                raise
            if record is not None:
                self._record(record, result=result)
            return result

        subprocess.run = observed
        self.installed = True

    def report(self):
        raw = b''
        try:
            raw = self.path.read_bytes() if self.path.is_file() else b''
            rows = [json.loads(line) for line in raw.splitlines()]
            if (len(rows) != self.records or self.records != self.attempts
                    or [row.get('sequence') for row in rows] != list(range(1, self.records + 1))):
                raise ValueError('agent Git record count differs from observed calls')
        except Exception as error:
            self._problem('finish', error)
        return {'installed': self.installed, 'max_caller_frames': self.MAX_FRAMES,
            'attempts': self.attempts, 'records': self.records,
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'problems': list(self.problems)}


class SourceProofFailureCapture:
    """Retain a failing Git proof without modifying the verifier or its inputs."""
    def __init__(self, directory):
        self.directory, self.captured = directory, False

    def pytest_exception_interact(self, node, call, report):
        if self.captured or call.excinfo is None:
            return
        error = call.excinfo.value
        if not str(error).startswith('consumed source is not committed at the reviewed head:'):
            return
        self.captured = True
        try:
            trace = error.__traceback__
            while trace is not None:
                frame, trace = trace.tb_frame, trace.tb_next
                if frame.f_code.co_name != 'require_committed':
                    continue
                values = frame.f_locals
                proc = values['proc']
                output = self.directory / 'source-proof-failure'
                output.mkdir(exist_ok=False)
                for name, raw in (('stdout', proc.stdout), ('stderr', proc.stderr), ('query', values['query'])):
                    if type(raw) is not bytes or len(raw) > 64 * 1024 * 1024:
                        raise ValueError('unexpected source-proof capture size or type')
                    (output / (name + '.bin')).write_bytes(raw)
                record = {'nodeid': node.nodeid, 'error': str(error),
                    'offset': values['offset'], 'path': values['path'],
                    'header_hex': [part.hex() for part in values['header']],
                    'stdout_bytes': len(proc.stdout), 'stderr_sha256': hashlib.sha256(proc.stderr).hexdigest(),
                    'query_sha256': hashlib.sha256(values['query']).hexdigest(),
                    'source_commit': values['base']['source_commit'], 'root': str(frame.f_globals['ROOT']),
                    'fullmatch': repr(frame.f_globals['re'].fullmatch),
                    'subprocess_run': repr(frame.f_globals['subprocess'].run),
                    'subprocess_popen': repr(frame.f_globals['subprocess'].Popen)}
                (output / 'failure.json').write_text(json.dumps(record, indent=2) + '\n')
                return
        except Exception as exc:
            (self.directory / 'proof-capture-error.txt').write_text(type(exc).__name__ + ': ' + str(exc) + '\n')


def _new_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def _archive_imports(tree, *, prepare):
    if prepare:
        selected_paths = {tree, tree / 'src', tree / 'fairscape_models'}
        sys.path[:] = [value for value in sys.path
            if Path(value).resolve() not in selected_paths
            and (not (Path(value) / 'data_sheets_schema').is_dir()
                or Path(value).resolve() == tree / 'src')
            and (not (Path(value) / 'fairscape_models/__init__.py').is_file()
                or Path(value).resolve() == tree / 'fairscape_models')]
        for path in (tree, tree / 'src', tree / 'fairscape_models'):
            sys.path.insert(0, str(path))
    import data_sheets_schema
    roots = [str(Path(value).resolve()) for value in data_sheets_schema.__path__]
    if set(roots) != {str(tree / 'src/data_sheets_schema')}:
        raise RuntimeError('test project namespace differs from selected archive')
    import fairscape_models
    fairscape_roots = [str(Path(value).resolve()) for value in fairscape_models.__path__]
    if set(fairscape_roots) != {str(tree / 'fairscape_models/fairscape_models')}:
        raise RuntimeError('test Fairscape namespace differs from the selected archive submodule')
    return {'python': sys.executable, 'version': sys.version,
        'package_roots': roots, 'fairscape_roots': fairscape_roots,
        'plugin_path': str(Path(__file__).resolve())}


def pytest_addoption(parser):
    parser.addoption('--pr6302-evidence-root', type=str,
        help='Fresh archive-run evidence root for process-local import and guard records.')
    parser.addoption('--pr6302-observe-agent-git', action='store_true', default=False,
        help='Retain bounded predecessor Git diagnostics without changing results.')


def pytest_configure(config):
    import pytest
    selected = config.getoption('pr6302_evidence_root')
    if not selected:
        raise pytest.UsageError('PR6302 archive plugin requires --pr6302-evidence-root')
    root = Path(selected).resolve(strict=True)
    if root != ROOT.parent or Path(config.rootpath).resolve() != ROOT:
        raise pytest.UsageError('PR6302 evidence and pytest roots differ from the plugin archive')
    worker = getattr(config, 'workerinput', {}).get('workerid', 'controller')
    if worker != 'controller' and re.fullmatch(r'gw[0-9]+', worker) is None:
        raise pytest.UsageError('PR6302 archive plugin requires a local xdist worker identity')
    count = config.getoption('numprocesses', default=0) or 0
    if type(count) is not int or not 0 <= count <= 4:
        raise pytest.UsageError('PR6302 archive runs require an explicit zero-to-four worker count')
    directory = root / 'workers' / (worker + '-' + str(os.getpid()))
    directory.mkdir(parents=True, exist_ok=False)
    state = {'root': root, 'directory': directory, 'worker_id': worker,
        'pid': os.getpid(), 'denials': [], 'guard_installed': False, 'agent_git_observer': None}
    config._pr6302_evidence = state
    _new_json(directory / 'start.json', {'worker_id': worker, 'pid': state['pid'],
        'requested_workers': count, 'archive_root': str(ROOT),
        'agent_git_observer_requested': config.getoption('pr6302_observe_agent_git')})
    witness = _archive_imports(ROOT, prepare=True)
    witness.update(worker_id=worker, pid=state['pid'])
    _new_json(directory / 'imports.json', witness)
    if worker == 'controller':
        _new_json(root / 'imports.json', witness)
    from tests.utils import isolated_pytest as isolation
    if Path(isolation.__file__).resolve() != ROOT / 'tests/utils/isolated_pytest.py':
        raise RuntimeError('offline guard was not imported from the selected archive')
    # The guard's root also bounds permitted test-owned executables. Preserve
    # the whole run root, including pytest basetemp; process-specific snapshots
    # below disambiguate its legacy append-only guard-denials.jsonl file.
    isolation.install_offline_guard(root, state['denials'])
    state['guard_installed'] = True
    if config.getoption('pr6302_observe_agent_git'):
        observer = AgentGitObserver(directory)
        observer.install()
        state['agent_git_observer'] = observer
    config.pluginmanager.register(SourceProofFailureCapture(
        root if worker == 'controller' else directory), 'pr6302-source-proof')


def pytest_configure_node(node):
    """Record every requested worker, including one that dies before configure."""
    state = node.config._pr6302_evidence
    worker = node.gateway.id
    if state['worker_id'] != 'controller' or re.fullmatch(r'gw[0-9]+', worker) is None:
        raise RuntimeError('unexpected PR6302 worker configuration')
    expected = state['root'] / 'expected-workers'
    expected.mkdir(exist_ok=True)
    _new_json(expected / (worker + '.json'), {'worker_id': worker,
        'controller_pid': state['pid']})


def pytest_sessionfinish(session, exitstatus):
    state = getattr(session.config, '_pr6302_evidence', None)
    if state is None:
        return
    namespace_error = None
    try:
        _archive_imports(ROOT, prepare=False)
    except Exception as error:
        namespace_error = type(error).__name__ + ': ' + str(error)
    denials = list(state['denials'])
    observer = state.get('agent_git_observer')
    observation = observer.report() if observer is not None else None
    passed = (int(exitstatus) == 0 and state['guard_installed']
        and not denials and namespace_error is None
        and (observation is None or observation['installed'] and not observation['problems']))
    _new_json(state['directory'] / 'offline-guard.json', {
        'worker_id': state['worker_id'], 'pid': state['pid'], 'session_finished': True,
        'pytest_exit_code': int(exitstatus), 'guard_installed': state['guard_installed'],
        'denials': denials, 'zero_guard_denials': not denials,
        'namespace_valid': namespace_error is None, 'namespace_error': namespace_error,
        'agent_git_observer': observation, 'passed': passed})
    if not passed and session.exitstatus == 0:
        session.exitstatus = 1


# Importing as a pytest plugin supplies hook metadata without making the outer
# standard-library archive preparation depend on importing pytest itself.
if __name__ != '__main__':
    import pytest
    pytest_configure = pytest.hookimpl(tryfirst=True)(pytest_configure)
    pytest_configure_node = pytest.hookimpl(optionalhook=True)(pytest_configure_node)
    pytest_sessionfinish = pytest.hookimpl(trylast=True)(pytest_sessionfinish)


def _guard_results(root):
    """Fail closed if any configured process lacks its complete final witness."""
    problems, processes, denials, missing_end = [], [], [], []
    expected = {}
    for path in sorted((root / 'expected-workers').glob('*.json')):
        value = json.loads(path.read_bytes())
        worker = value.get('worker_id')
        if type(worker) is not str or re.fullmatch(r'gw[0-9]+', worker) is None or path.stem != worker:
            problems.append('invalid expected-worker record: ' + path.name)
        else:
            expected[worker] = value
    for directory in sorted((root / 'workers').glob('*')):
        if not directory.is_dir():
            problems.append('unexpected process evidence member: ' + directory.name)
            continue
        start_path, imports_path, end_path = (directory / name for name in (
            'start.json', 'imports.json', 'offline-guard.json'))
        if not start_path.is_file():
            problems.append('missing process start: ' + directory.name)
            continue
        start = json.loads(start_path.read_bytes())
        worker, pid = start.get('worker_id'), start.get('pid')
        if (type(worker) is not str or type(pid) is not int or pid <= 0
                or directory.name != worker + '-' + str(pid)
                or start.get('archive_root') != str(root / 'tree')):
            problems.append('invalid process start: ' + directory.name)
        row = {'worker_id': worker, 'pid': pid, 'directory': str(directory),
               'requested_workers': start.get('requested_workers'),
               'agent_git_observer_requested': start.get('agent_git_observer_requested', False)}
        processes.append(row)
        if not imports_path.is_file():
            problems.append('missing import witness: ' + directory.name)
        else:
            witness = json.loads(imports_path.read_bytes())
            if (witness.get('worker_id') != worker or witness.get('pid') != pid
                    or witness.get('package_roots') != [str(root / 'tree/src/data_sheets_schema')]
                    or witness.get('fairscape_roots') != [str(root / 'tree/fairscape_models/fairscape_models')]
                    or witness.get('plugin_path') != str(root / 'tree/scripts/adhoc' / Path(__file__).name)):
                problems.append('import witness differs from archive: ' + directory.name)
        if not end_path.is_file():
            missing_end.append(directory.name)
            problems.append('missing process finish: ' + directory.name)
            continue
        end = json.loads(end_path.read_bytes())
        row['pytest_exit_code'] = end.get('pytest_exit_code')
        if (end.get('worker_id') != worker or end.get('pid') != pid
                or type(end.get('pytest_exit_code')) is not int or end['pytest_exit_code'] != 0
                or end.get('session_finished') is not True or end.get('guard_installed') is not True
                or end.get('namespace_valid') is not True or end.get('namespace_error') is not None
                or end.get('zero_guard_denials') is not True or end.get('passed') is not True
                or end.get('denials') != []):
            problems.append('process guard or namespace failed: ' + directory.name)
        requested = start.get('agent_git_observer_requested', False)
        observation = end.get('agent_git_observer')
        if type(requested) is not bool or (not requested and observation is not None):
            problems.append('agent Git observer selection differs: ' + directory.name)
        elif requested:
            log_path = directory / 'agent-pin-git.jsonl'
            raw = log_path.read_bytes() if log_path.is_file() else b''
            if (type(observation) is not dict or observation.get('installed') is not True
                    or observation.get('problems') != []
                    or type(observation.get('max_caller_frames')) is not int
                    or observation.get('max_caller_frames') != AgentGitObserver.MAX_FRAMES
                    or type(observation.get('records')) is not int or observation['records'] < 0
                    or type(observation.get('attempts')) is not int
                    or observation.get('attempts') != observation['records']
                    or type(observation.get('bytes')) is not int
                    or observation.get('bytes') != len(raw)
                    or observation.get('sha256') != hashlib.sha256(raw).hexdigest()
                    or len(raw.splitlines()) != observation['records']):
                problems.append('agent Git observer failed: ' + directory.name)
        if type(end.get('denials')) is list:
            denials.extend({'worker_id': worker, 'pid': pid, 'event': event} for event in end['denials'])
    controllers = [row for row in processes if row['worker_id'] == 'controller']
    workers = [row for row in processes if row['worker_id'] != 'controller']
    if len(controllers) != 1:
        problems.append('missing or duplicate pytest controller')
    else:
        count = controllers[0]['requested_workers']
        if type(count) is not int or not 0 <= count <= 4:
            problems.append('invalid requested worker count')
        elif not {f'gw{index}' for index in range(count)} <= set(expected):
            problems.append('requested workers lack configuration records')
        elif count == 0 and expected:
            problems.append('serial run unexpectedly configured workers')
        if any(value.get('controller_pid') != controllers[0]['pid'] for value in expected.values()):
            problems.append('worker configuration belongs to another controller')
        if any(row['agent_git_observer_requested'] != controllers[0]['agent_git_observer_requested']
                for row in workers):
            problems.append('worker agent Git observer selection differs from controller')
    for worker in sorted(set(expected) | {row['worker_id'] for row in workers}):
        matches = [row for row in workers if row['worker_id'] == worker]
        if worker not in expected or len(matches) != 1:
            problems.append('configured worker lacks one process witness: ' + str(worker))
        if not matches:
            missing_end.append(worker)
    log = root / 'guard-denials.jsonl'
    if log.is_file() and log.stat().st_size:
        problems.append('offline guard retained denial events')
    return {'checked': True, 'passed': not problems, 'zero_guard_denials': not denials
        and not (log.is_file() and log.stat().st_size), 'denials': denials,
        'expected_worker_ids': sorted(expected), 'processes': processes,
        'missing_process_finish': missing_end, 'problems': problems}


def isolated_pytest():
    tree = Path(sys.argv[2]).resolve()
    if tree != ROOT or Path(sys.argv[3]).resolve() != ROOT.parent / 'imports.json':
        raise RuntimeError('archive pytest arguments differ from this runner location')
    import pytest
    return pytest.main(sys.argv[4:])


def _source_repository_identity():
    """Verify local source identity before configuring the independent archive."""
    allowed = {CI_REPOSITORY_URL, CI_REPOSITORY_URL + '.git'}
    for prefix in ('git' + chr(64) + 'github.com:', 'ssh://git' + chr(64) + 'github.com/'):
        allowed.update({prefix + 'bridge2ai/data-sheets-schema',
                        prefix + 'bridge2ai/data-sheets-schema.git'})
    for key in ('d4d.ciRepositoryUrl', 'remote.origin.url'):
        result = subprocess.run(['git', '-C', str(ROOT), 'config', '--local', '--no-includes',
                                 '--get-all', key], capture_output=True)
        if result.returncode == 1:
            continue
        if result.returncode != 0:
            raise ValueError('cannot verify the source repository local identity')
        if result.stdout not in {value.encode('utf-8') + b'\n' for value in allowed}:
            raise ValueError('source repository local identity is not the canonical PR6302 repository')
        return {'canonical_url': CI_REPOSITORY_URL, 'source_config_key': key,
            'source_config_value_sha256': hashlib.sha256(result.stdout).hexdigest(),
            'source_identity_verified': True,
            'basis': 'Exact local source repository identity; canonical archive-local configuration only. '
                     'No remote is created, no CI result is supplied, and no network request is made.'}
    raise ValueError('source repository lacks an explicit local CI repository URL or origin')


def main():
    arguments = sys.argv[1:]
    selected = 'HEAD'
    environment_audit = environment_audit_sha256 = None
    options = set()
    while arguments and arguments[0] in {'--source-commit', '--disposable-environment'}:
        option = arguments[0]
        if option in options:
            raise ValueError('archive setup option is repeated')
        options.add(option)
        if option == '--source-commit':
            selected, arguments = arguments[1], arguments[2:]
        else:
            environment_audit, environment_audit_sha256 = Path(arguments[1]), arguments[2]
            arguments = arguments[3:]
            if (not environment_audit.is_absolute() or environment_audit.resolve(strict=True) != environment_audit
                    or re.fullmatch('[0-9a-f]{64}', environment_audit_sha256) is None
                    or hashlib.sha256(environment_audit.read_bytes()).hexdigest() != environment_audit_sha256):
                raise ValueError('disposable environment requires its exact physical audit and SHA256')
    repository_identity = _source_repository_identity()
    out = Path(arguments[0]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--verify', selected + '^{commit}'],
                                   text=True).strip()
    archive, tree = out / 'source.tar', out / 'tree'
    subprocess.run(['git', '-C', str(ROOT), 'archive', '--output', str(archive), head], check=True)
    tree.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(tree, filter='data')
    gitlink = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', head, 'fairscape_models'],
                                     text=True).split()
    if len(gitlink) != 4 or gitlink[0:2] != ['160000', 'commit'] or gitlink[3] != 'fairscape_models':
        raise ValueError('archive lacks its exact Fairscape gitlink')
    submodule_archive = out / 'fairscape_models.tar'
    subprocess.run(['git', '-C', str(SUBMODULE_SOURCE), 'archive', '--output',
                    str(submodule_archive), gitlink[2]], check=True)
    with tarfile.open(submodule_archive) as bundle:
        bundle.extractall(tree / 'fairscape_models', filter='data')
    common = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', '--path-format=absolute', '--git-common-dir'], text=True).strip()
    subprocess.run(['git', '-C', str(tree), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(tree), 'config', '--local', 'd4d.ciRepositoryUrl',
                    repository_identity['canonical_url']], check=True)
    configured_url = subprocess.check_output(['git', '-C', str(tree), 'config', '--local',
                                             '--no-includes', '--get-all', 'd4d.ciRepositoryUrl'])
    if configured_url != (CI_REPOSITORY_URL + '\n').encode('utf-8'):
        raise ValueError('archive-local CI repository URL did not persist exactly')
    repository_identity.update(archive_config_key='d4d.ciRepositoryUrl',
                               archive_config_scope='local', archive_readback_verified=True)
    (tree / '.git/objects/info/alternates').write_text(str(Path(common) / 'objects') + '\n')
    subprocess.run(['git', '-C', str(tree), 'update-ref', 'refs/heads/archive-test', head], check=True)
    subprocess.run(['git', '-C', str(tree), 'symbolic-ref', 'HEAD', 'refs/heads/archive-test'], check=True)
    subprocess.run(['git', '-C', str(tree), 'read-tree', head], check=True)
    paths = subprocess.check_output(
        ['git', '-C', str(ROOT), 'diff', '--name-only', BASE, head], text=True).splitlines()
    pins = {name: hashlib.sha256((tree / name).read_bytes()).hexdigest() for name in paths}
    helper = tree / 'scripts/adhoc' / Path(__file__).name
    python, disposable_environment = PYTHON, None
    if environment_audit is not None:
        environment_helper = tree / 'scripts/adhoc/pr6302_archive_environment_20261122.py'
        setup_root = out / 'environment'
        setup_command = [str(PYTHON), '-I', '-B', str(environment_helper), 'setup',
            '--source-venv', str(PYTHON.parent.parent), '--tree', str(tree),
            '--audit', str(environment_audit), '--audit-sha256', environment_audit_sha256,
            '--output', str(setup_root)]
        setup_env = {'HOME': str(out), 'TMPDIR': str(out), 'LANG': 'en_US.UTF-8',
                     'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'PYTHONDONTWRITEBYTECODE': '1'}
        _new_json(out / 'environment-setup-request.json', {'source_commit': head, 'tree': str(tree),
            'command': setup_command, 'audit_path': str(environment_audit),
            'audit_sha256': environment_audit_sha256,
            'helper_sha256': hashlib.sha256(environment_helper.read_bytes()).hexdigest()})
        with (out / 'environment-setup.log').open('xb') as log:
            setup_result = subprocess.run(setup_command, cwd=tree, env=setup_env,
                                          stdout=log, stderr=subprocess.STDOUT)
        if setup_result.returncode != 0:
            raise ValueError('disposable environment setup refused; see environment-setup.log')
        environment_path = setup_root / 'environment.json'
        environment_raw = environment_path.read_bytes()
        prepared_environment = json.loads(environment_raw)
        python = setup_root / 'venv/bin/python'
        if (prepared_environment.get('passed') is not True
                or prepared_environment.get('source_commit') != head
                or prepared_environment.get('tree') != str(tree)
                or prepared_environment.get('python') != str(python)
                or prepared_environment.get('source_venv') != str(PYTHON.parent.parent)
                or prepared_environment.get('source_environment_unchanged') is not True
                or prepared_environment.get('archive_unchanged') is not True):
            raise ValueError('disposable environment result does not bind this archive')
        disposable_environment = {'path': str(environment_path),
            'sha256': hashlib.sha256(environment_raw).hexdigest(), 'bytes': len(environment_raw),
            'audit_sha256': environment_audit_sha256, 'python': str(python)}
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(tree), str(tree / 'src'), str(tree / 'fairscape_models'))),
               PYTHONDONTWRITEBYTECODE='1')
    for key in tuple(env):
        if key.endswith('_API_KEY') or key in {'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
                'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL', 'D4D_INSTALL_TESTS', 'PYTEST_ADDOPTS'}:
            env.pop(key)
    if disposable_environment is not None:
        env = {'HOME': str(setup_root / 'home'), 'TMPDIR': str(setup_root / 'tmp'),
            'PATH': str(python.parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
            'VIRTUAL_ENV': str(python.parent.parent), 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
            'PYTHONPATH': env['PYTHONPATH'], 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
            'PIP_NO_INDEX': '1', 'PIP_CONFIG_FILE': '/dev/null', 'UV_OFFLINE': '1',
            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
        if 'CI' in os.environ:
            env['CI'] = os.environ['CI']
    command = [str(python), '-P', '-s', '-B', str(helper), '--pytest', str(tree), str(out / 'imports.json'),
               '-q', '-p', 'no:cacheprovider', '-p', PLUGIN,
               '--pr6302-evidence-root', str(out), '--basetemp', str(out / 'pytest')]
    command += arguments[1:] or TARGETED
    record = {'source_commit': head, 'cwd': str(tree), 'command': command,
              'ci_repository_identity': repository_identity,
              'environment': {'PYTHONPATH': env['PYTHONPATH'], 'PYTHONDONTWRITEBYTECODE': '1',
                              'CI': env.get('CI')},
              'fairscape_submodule': {'commit': gitlink[2],
                  'archive_sha256': hashlib.sha256(submodule_archive.read_bytes()).hexdigest()},
              'started_utc': subprocess.check_output(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'], text=True).strip(),
              'changed_file_sha256': pins}
    if disposable_environment is not None:
        record['disposable_environment'] = disposable_environment
    (out / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    with (out / 'pytest.log').open('xb') as log:
        run = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        guard = _guard_results(out)
    except Exception as error:
        guard = {'checked': False, 'passed': False, 'zero_guard_denials': False,
            'problems': ['guard aggregation failed: ' + type(error).__name__ + ': ' + str(error)]}
    _new_json(out / 'offline-guard.json', guard)
    record['pytest_exit_code'] = run.returncode
    record['exit_code'] = run.returncode or int(guard['passed'] is not True)
    record['offline_guard'] = guard
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    print((out / 'pytest.log').read_text()[-7000:], flush=True)
    if guard['passed'] is not True:
        print('Offline guard verification failed: ' + '; '.join(guard['problems']), flush=True)
    return record['exit_code']


if __name__ == '__main__':
    raise SystemExit(isolated_pytest() if sys.argv[1] == '--pytest' else main())
