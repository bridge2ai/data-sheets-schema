"""Independent fixed-profile authority and lease controls; no native launch.

Real loader contexts and ordinary pipes exercise the selected class. A small
fixture-owned Git tree exercises actual named-blob proof in an isolated Python
process; it never edits this checkout or runs a provider/helper/renderer.
"""
from contextlib import contextmanager
from contextvars import copy_context
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from types import ModuleType, SimpleNamespace

import pytest

from data_sheets_schema import native_attribution_controller as inherited
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_supervisor_authority as supervisor
from data_sheets_schema.resources import git_env
from .test_native_owner_control_adversarial import _loader_state
from .test_native_shared_controller import bound, native_spec, declaration
from .test_native_shared_registration import execution


@pytest.mark.parametrize('selector', [False, True, None, -1, 2, 0.0, 1.0, '0', '1', [], {}])
def test_selector_is_exact_not_truthy_or_integer_equivalent(selector):
    with pytest.raises(ValueError, match='exact integer 0 or 1'):
        profile.source_profile(selector)
    with pytest.raises(ValueError, match='exact integer 0 or 1'):
        authority.dependency_identity(stream_snapshot_profile=selector)


@pytest.mark.parametrize('mutation', [
    'profile_bool', 'profile_float', 'profile_string', 'format', 'base_pin',
    'extra', 'missing', 'role_missing', 'role_extra', 'path', 'path_alias',
    'hash', 'role_extra_field', 'role_wrong_shape',
])
def test_closed_profile_rejects_aliased_forged_and_missing_source_declarations(mutation):
    identity = authority.dependency_identity(stream_snapshot_profile=1)
    value = deepcopy(identity['stream_snapshot_profile'])
    control = value['implementations']['control']
    if mutation.startswith('profile_'):
        value['profile'] = {'profile_bool': True, 'profile_float': 1.0,
                            'profile_string': '1'}[mutation]
    elif mutation == 'format': value['format'] += '_unknown'
    elif mutation == 'base_pin': value['base_controller_sources_sha256'] = '0' * 64
    elif mutation == 'extra': value['execution_authorized'] = True
    elif mutation == 'missing': value.pop('base_controller_sources_sha256')
    elif mutation == 'role_missing': value['implementations'].pop('coordination')
    elif mutation == 'role_extra': value['implementations']['another'] = deepcopy(control)
    elif mutation == 'path': control['path'] = 'src/data_sheets_schema/native_control.py'
    elif mutation == 'path_alias': control['path'] = './' + control['path']
    elif mutation == 'hash': control['sha256'] = '0' * 64
    elif mutation == 'role_extra_field': control['reviewed'] = True
    else: value['implementations']['control'] = [control]
    with pytest.raises(ValueError):
        profile.verify_profile(value, identity['base']['package_sources'])


@pytest.mark.parametrize('mutation', [
    'version_bool', 'version_float', 'version_unknown', 'missing_profile',
    'v1_with_profile', 'extra', 'missing_base', 'rehash_both_pins',
])
def test_loader_refuses_changed_identity_before_import_or_cache_changes(mutation):
    with _loader_state(prefilled=False) as (_, names):
        identity = authority.dependency_identity(stream_snapshot_profile=1)
        changed = deepcopy(identity)
        if mutation == 'version_bool': changed['version'] = True
        elif mutation == 'version_float': changed['version'] = 2.0
        elif mutation == 'version_unknown': changed['version'] = 3
        elif mutation == 'missing_profile': changed.pop('stream_snapshot_profile')
        elif mutation == 'v1_with_profile': changed['version'] = 1
        elif mutation == 'extra': changed['caller_loader'] = 'arbitrary'
        elif mutation == 'missing_base': changed.pop('base')
        else:
            pin = changed['stream_snapshot_profile']['implementations']['control']
            pin['sha256'] = '0' * 64
            changed['base']['package_sources'][pin['path']] = pin['sha256']
        before = {name: sys.modules.get(name) for name in names}
        path = sys.path[:]
        with pytest.raises(ValueError):
            with authority.loaded_dependencies(changed):
                pytest.fail('changed authority entered its loader')
        assert {name: sys.modules.get(name) for name in names} == before
        assert sys.path == path


@pytest.mark.parametrize('role,module_name', [
    ('control', 'data_sheets_schema.native_owner_control_v1'),
    ('coordination', 'data_sheets_schema.native_stream_coordination_v1'),
])
def test_qualified_role_requires_exact_file_not_merely_package_ancestry(role, module_name, monkeypatch):
    impostor = ModuleType(module_name)
    # A sibling in the correct package is still not the fixed role's origin.
    impostor.__file__ = str(authority.ROOT / 'src/data_sheets_schema/native_execution_authority.py')
    monkeypatch.setitem(sys.modules, module_name, impostor)
    with pytest.raises(ValueError, match='foreign qualified origin'):
        profile.source_profile(1)


def _new(cls, controls, directory, *, deadline=None):
    policy = {'pretool_control': deepcopy(controls['native_control'].HISTORY_CONTRACT),
              'python': 'synthetic-python',
              'readonly_lookups': {'repository': str(directory), 'inputs': [],
                                   'output_directories': []}}
    return cls(policy, lambda *unused: ('prescribed', 'unused synthetic classifier'),
               attempt_deadline_ns=(time.monotonic_ns() + 30_000_000_000
                                    if deadline is None else deadline),
               stop_event=threading.Event())


@contextmanager
def _pipes(directory):
    """Real ordinary descriptors, no child executable or worker dispatch."""
    directory.mkdir()
    parent_read, peer_write = os.pipe()
    peer_read, parent_write = os.pipe()
    process = SimpleNamespace(stdout=os.fdopen(parent_read, 'rb', buffering=0),
                              stdin=os.fdopen(parent_write, 'wb', buffering=0))
    transcript = (directory / 'transcript').open('xb', buffering=0)
    journal = (directory / 'control').open('xb', buffering=0)
    try:
        yield process, transcript, journal
    finally:
        os.close(peer_write)
        os.close(peer_read)
        for stream in (process.stdout, process.stdin, transcript, journal):
            if not stream.closed:
                stream.close()


class _Leave(Exception):
    pass


@pytest.mark.parametrize('prefilled', [False, True])
@pytest.mark.parametrize('exceptional', [False, True])
def test_escaped_classes_and_copied_contexts_expire_even_with_restored_caches(
        tmp_path, prefilled, exceptional):
    with _loader_state(prefilled=prefilled) as (_, names):
        before = {name: sys.modules.get(name) for name in names}
        path = sys.path[:]
        identity = authority.dependency_identity(stream_snapshot_profile=1)
        declared = identity['stream_snapshot_profile']
        saved = []
        def enter():
            with authority.loaded_dependencies(identity) as controls:
                cls = profile.bind_control(declared, controls)
                channel = _new(cls, controls, tmp_path)
                saved.append((controls, cls, channel, copy_context()))
                if exceptional:
                    raise _Leave('invented exceptional loader exit')
        if exceptional:
            with pytest.raises(_Leave): enter()
        else:
            enter()
        controls, cls, channel, copied = saved[0]
        try:
            assert {name: sys.modules.get(name) for name in names} == before
            assert sys.path == path
            with pytest.raises(ValueError, match='selected loader scope'):
                profile.bind_control(declared, controls)
            with pytest.raises(ValueError, match='loader lifetime'):
                _new(cls, controls, tmp_path)
            with pytest.raises(ValueError, match='loader lifetime'):
                copied.run(_new, cls, controls, tmp_path)
            with pytest.raises(ValueError, match='loader lifetime'):
                copied.run(profile.bind_control, declared, controls)
            # Cleanup/getters remain available; lease exit itself is not a
            # claim that a hypothetical worker was joined automatically.
            channel.close()
            assert channel.close_report()['worker_shutdown_complete'] is True
            assert channel.failed_members()['transcript_suffix'] == b''
            channel.close()
        finally:
            channel.close()


@pytest.mark.parametrize('operation', ['service', 'finish', 'start'])
def test_escaped_instance_failure_is_latched_and_cleanup_remains_available(tmp_path, operation):
    with _loader_state(prefilled=True):
        identity = authority.dependency_identity(stream_snapshot_profile=1)
        with _pipes(tmp_path / 'streams') as args:
            with authority.loaded_dependencies(identity) as controls:
                channel = _new(profile.bind_control(identity['stream_snapshot_profile'], controls),
                               controls, tmp_path)
                channel.start(*args, 'invented instruction')
                assert channel.outgoing
            try:
                before = tuple(Path(s.name).read_bytes() for s in args[1:])
                with pytest.raises(ValueError, match='loader lifetime'):
                    if operation == 'start': channel.start(*args, 'invented instruction')
                    else: getattr(channel, operation)()
                assert channel._stopped.is_set() and channel.outgoing == b''
                snapshot = channel.failure_snapshot()
                assert 'loader lifetime' in snapshot['first_stop']
                assert tuple(Path(s.name).read_bytes() for s in args[1:]) == before
                channel.close()
                assert channel.failure_snapshot() == snapshot
                assert channel.close_report()['operation_failed'] is True
            finally:
                channel.close()


@pytest.mark.parametrize('prefilled', [False, True])
def test_reentry_cannot_reuse_old_map_or_class_even_if_same_source_objects_survive(tmp_path, prefilled):
    with _loader_state(prefilled=prefilled):
        identity = authority.dependency_identity(stream_snapshot_profile=1)
        declared = identity['stream_snapshot_profile']
        with authority.loaded_dependencies(identity) as old:
            old_class = profile.bind_control(declared, old)
        with authority.loaded_dependencies(identity) as current:
            current_class = profile.bind_control(declared, current)
            assert current is not old and current_class is not old_class
            if prefilled:
                assert current['native_control'] is old['native_control']
            else:
                assert current['native_control'] is not old['native_control']
            with pytest.raises(ValueError, match='selected loader scope'):
                profile.bind_control(declared, old)
            with pytest.raises(ValueError, match='loader lifetime'):
                _new(old_class, current, tmp_path)
            good = _new(current_class, current, tmp_path)
            good.close()


def test_nested_scope_restores_unused_outer_but_never_revives_failed_outer_instance(tmp_path):
    with _loader_state(prefilled=True):
        identity = authority.dependency_identity(stream_snapshot_profile=1)
        declared = identity['stream_snapshot_profile']
        with _pipes(tmp_path / 'streams') as args:
            with authority.loaded_dependencies(identity) as outer:
                outer_class = profile.bind_control(declared, outer)
                failed = _new(outer_class, outer, tmp_path)
                failed.start(*args, 'invented instruction')
                try:
                    with authority.loaded_dependencies(identity) as inner:
                        inner_class = profile.bind_control(declared, inner)
                        active = _new(inner_class, inner, tmp_path)
                        active.close()
                        with pytest.raises(ValueError, match='selected loader scope'):
                            profile.bind_control(declared, outer)
                        with pytest.raises(ValueError, match='loader lifetime'):
                            failed.service()
                        assert failed._stopped.is_set() and failed.outgoing == b''
                    snapshot = failed.failure_snapshot()
                    # Restoration does permit a fresh, unused outer binding.
                    fresh = _new(outer_class, outer, tmp_path)
                    fresh.close()
                    with pytest.raises(outer['budgeted_cborg'].BudgetStop, match='stopped'):
                        failed.service()
                    assert failed.failure_snapshot() == snapshot
                    with pytest.raises(ValueError, match='loader lifetime'):
                        _new(inner_class, inner, tmp_path)
                finally:
                    failed.close()


def test_mutating_yielded_full_map_stops_existing_instance_even_outside_frozen_subset(tmp_path):
    with _loader_state(prefilled=True):
        identity = authority.dependency_identity(stream_snapshot_profile=1)
        with authority.loaded_dependencies(identity) as controls:
            with _pipes(tmp_path / 'streams') as args:
                cls = profile.bind_control(identity['stream_snapshot_profile'], controls)
                channel = _new(cls, controls, tmp_path)
                channel.start(*args, 'invented instruction')
                saved = controls.pop('run_direct_canary_awake')
                try:
                    with pytest.raises(ValueError, match='loader lifetime'):
                        channel.service()
                finally:
                    controls['run_direct_canary_awake'] = saved
                try:
                    snapshot = channel.failure_snapshot()
                    assert channel._stopped.is_set() and channel.outgoing == b''
                    with pytest.raises(controls['budgeted_cborg'].BudgetStop, match='stopped'):
                        channel.service()
                    assert channel.failure_snapshot() == snapshot
                finally:
                    channel.close()


@pytest.mark.parametrize('reason', ['stale_graph', 'expired_deadline'])
def test_selected_start_refusal_cannot_be_retried_after_restoring_graph_or_clock(
        tmp_path, monkeypatch, reason):
    # #4702: the selected wrapper's delegation used to be outside its
    # latch/stop try: both failures occur before base.start assigns handles.
    with _loader_state(prefilled=True):
        identity = authority.dependency_identity(stream_snapshot_profile=1)
        with authority.loaded_dependencies(identity) as controls:
            with _pipes(tmp_path / 'streams') as args:
                deadline = time.monotonic_ns() + 30_000_000_000
                channel = _new(profile.bind_control(identity['stream_snapshot_profile'], controls),
                               controls, tmp_path, deadline=deadline)
                try:
                    with monkeypatch.context() as change:
                        if reason == 'stale_graph':
                            change.setitem(sys.modules, 'native_control', ModuleType('native_control'))
                            error, message = ValueError, 'stale or foreign'
                        else:
                            from data_sheets_schema import native_stream_coordination_v1 as coordination
                            change.setattr(coordination, 'time', SimpleNamespace(monotonic_ns=lambda: deadline))
                            error, message = controls['budgeted_cborg'].BudgetStop, 'deadline elapsed'
                        with pytest.raises(error, match=message):
                            channel.start(*args, 'invented instruction')
                    assert channel._stopped.is_set()
                    snapshot = channel.failure_snapshot()
                    assert message.split(' or ')[0] in snapshot['first_stop']
                    assert [Path(s.name).read_bytes() for s in args[1:]] == [b'', b'']
                    with pytest.raises(controls['budgeted_cborg'].BudgetStop, match='stopped'):
                        channel.start(*args, 'invented instruction')
                    assert channel.failure_snapshot() == snapshot
                    assert channel.outgoing == b''
                finally:
                    channel.close()


def _fixture_git_tree(directory):
    """Copy real source bytes, never link or mutate the shared checkout."""
    root = authority.ROOT
    package = root / 'src/data_sheets_schema'
    files = {str(path.relative_to(root)) for path in package.rglob('*')
             if path.is_file() and path.suffix in {'.py', '.yaml', '.json'}}
    manifest = json.loads((root / inherited.SOURCES_PATH).read_bytes())
    files.update(pin['path'] for pin in manifest['modules'].values())
    files.update(pin['path'] for pin in supervisor.ADDITIONAL.values())
    files.update(pin['path'] for pin in authority.ADDITIONAL.values())
    files.add('pyproject.toml')
    for relative in sorted(files):
        source, target = root / relative, directory / relative
        assert source.is_file() and not source.is_symlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
    env = git_env()
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    def git(*args):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=directory,
                              env=env, check=True, capture_output=True, text=True, timeout=30)
    git('init', '-q')
    git('add', '--', '.')
    git('-c', 'user.name=Isolated software fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Fixture-owned exact source closure')
    return env


_GIT_PROOF_CHILD = r'''
import hashlib, json, os, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
mode = sys.argv[2]
sys.path.insert(0, str(root / 'src'))
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_owner_profile_v1 as profile
assert authority.ROOT == profile.ROOT == root
assert pathlib.Path(authority.__file__).resolve().is_relative_to(root)
assert pathlib.Path(profile.__file__).resolve().is_relative_to(root)
identity = authority.dependency_identity(stream_snapshot_profile=1)
authority.require_committed(identity)
control = root / profile.IMPLEMENTATIONS['control']
resolver = pathlib.Path(profile.__file__)
if mode == 'changed_control':
    control.write_bytes(control.read_bytes() + b'\n# Fixture-only source drift.\n')
    changed = authority.dependency_identity(stream_snapshot_profile=1)
    assert changed['base']['source_commit'] == identity['base']['source_commit']
    assert changed['stream_snapshot_profile'] != identity['stream_snapshot_profile']
    assert changed['base']['package_sources'][str(control.relative_to(root))] == hashlib.sha256(control.read_bytes()).hexdigest()
    try:
        authority.require_committed(changed)
    except ValueError as exc:
        assert 'differs from the reviewed commit' in str(exc), str(exc)
        assert str(control.relative_to(root)) in str(exc), str(exc)
    else:
        raise AssertionError('actual changed named blob was accepted')
elif mode == 'untracked_package':
    target = root / 'src/data_sheets_schema/untracked_profile_fixture.py'
    target.write_bytes(b'# Fixture-owned untracked source.\n')
    changed = authority.dependency_identity(stream_snapshot_profile=1)
    assert str(target.relative_to(root)) in changed['base']['package_sources']
    try:
        authority.require_committed(changed)
    except ValueError as exc:
        expected = 'committed package source roster differs: missing=[]; extra=' + repr([str(target.relative_to(root))])
        assert str(exc) == expected, str(exc)
    else:
        raise AssertionError('actual missing named blob was accepted')
elif mode == 'removed_resolver':
    resolver.unlink()
    # Frozen v1 behavior is unchanged; the new selected profile must require
    # its resolver even though recursive enumeration now omits that file.
    assert authority.dependency_identity()['version'] == 1
    try:
        authority.dependency_identity(stream_snapshot_profile=1)
    except ValueError as exc:
        assert str(resolver.relative_to(root)) in str(exc), str(exc)
    else:
        raise AssertionError('already-imported missing profile resolver was accepted')
elif mode == 'hostile_git_overrides':
    # Only this child's environment changes. All decoys are owned by the
    # fixture, and none is a repository; each actual Git call must strip them.
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
        decoy = root / ('not-a-repository-' + name.lower())
        if name == 'GIT_INDEX_FILE':
            decoy.write_bytes(b'not an index')
        else:
            decoy.mkdir()
        os.environ[name] = str(decoy)
    repeated = authority.dependency_identity(stream_snapshot_profile=1)
    assert repeated == identity
    authority.require_committed(repeated)
elif mode == 'role_symlink':
    exact = control.read_bytes()
    saved = root / 'fixture-role-source.py'
    saved.write_bytes(exact)
    control.unlink()
    control.symlink_to(saved)
    assert hashlib.sha256(control.read_bytes()).hexdigest() == identity['stream_snapshot_profile']['implementations']['control']['sha256']
    try:
        authority.dependency_identity(stream_snapshot_profile=1)
    except ValueError as exc:
        assert 'fixed regular source file' in str(exc), str(exc)
    else:
        raise AssertionError('symlink role was accepted despite correct source bytes')
else:
    raise AssertionError(mode)
print(json.dumps({'mode': mode, 'actual_git_blob_proof': True, 'expected_boundary_verified': True}))
'''


@pytest.mark.parametrize('mode', ['changed_control', 'untracked_package', 'removed_resolver',
                                  'role_symlink', 'hostile_git_overrides'])
def test_actual_named_blob_and_missing_resolver_proof_uses_only_fixture_owned_sources(tmp_path, mode):
    fixture = tmp_path / 'source'
    fixture.mkdir()
    env = _fixture_git_tree(fixture)
    # This is a fixed ordinary Python program for local source/Git proof. It
    # does not import a runner, load controls, launch a helper or call a provider.
    result = subprocess.run([sys.executable, '-I', '-B', '-c', _GIT_PROOF_CHILD,
                             str(fixture), mode], cwd=fixture, env=env,
                            text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {
        'mode': mode, 'actual_git_blob_proof': True, 'expected_boundary_verified': True}


def test_real_v1_execution_reconstruction_rejects_every_private_profile_injection(execution):
    from data_sheets_schema import native_shared_contract as contract
    from data_sheets_schema import native_shared_registration as registration
    args, selected, _ = execution
    original = registration.registration(**args)
    assert registration.verified(contract.canonical(original)) == original
    selected_identity = authority.dependency_identity(stream_snapshot_profile=1)
    mutants = []
    with_v2 = deepcopy(original)
    with_v2['dependencies'] = selected_identity
    mutants.append(with_v2)
    with_top = deepcopy(original)
    with_top['stream_snapshot_profile'] = 1
    mutants.append(with_top)
    with_nested = deepcopy(original)
    with_nested['dependencies']['stream_snapshot_profile'] = selected_identity['stream_snapshot_profile']
    mutants.append(with_nested)
    for changed in mutants:
        with pytest.raises(ValueError):
            registration.verified(contract.canonical(changed))
        assert not args['attempt_directory'].exists()
        assert not args['evidence_directory'].exists()
        assert not Path(contract.parse_selection(selected['selection_raw_json'].encode())['stage_root']).exists()
