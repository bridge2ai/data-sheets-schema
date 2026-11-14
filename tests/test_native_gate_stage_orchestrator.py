"""H3-RF17 fixed-stage controls; no packet, gate, capture or native launch."""
import json
import os
from pathlib import Path
import signal
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/adhoc/run_h3_gate_stages_20261113.py'
stage = {'__name__': 'fixed_stage_orchestrator_unit', '__file__': str(SCRIPT)}
exec(compile(SCRIPT.read_bytes(), str(SCRIPT), 'exec'), stage)


@pytest.fixture
def cohort(tmp_path, monkeypatch):
    scratch = tmp_path / 'scratch'; (scratch / 'tests/unit/stages').mkdir(parents=True)
    root = scratch / 'tests/unit'
    stage['save'](root / 'stage-config.json', {'SYNTHETIC': 'immutable config'})
    monkeypatch.setitem(stage, 'S', scratch)
    return root


def record(cohort, name, *, status='passed', configuration=None):
    directory = cohort / 'stages' / name; directory.mkdir()
    action, role = ('build', name[6:]) if name.startswith('build-') else (name, None)
    artifact = stage['save'](directory / 'artifact.json', {'SYNTHETIC': name})
    result = stage['save'](directory / 'result.json', {'status': status, 'action': action, 'role': role,
        'config': configuration or stage['pin'](cohort / 'stage-config.json'),
        'outputs': {'artifact': artifact}, 'side_effects': stage['COUNTERS']})
    stage['save'](directory / 'outcome.json', {'status': status, 'cleanup_verified': True, 'result': result})
    return artifact


@pytest.mark.parametrize('role', stage['ROLES'][1:])
def test_every_later_build_requires_same_cohort_canary(role):
    assert 'canary' in stage['predecessors']('build', role)


def test_reference_build_precedes_canary_and_no_later_build_can_skip_it(cohort):
    record(cohort, 'setup-peer')
    assert set(stage['verify_predecessors'](cohort, 'build', 'reference')) == {'setup-peer'}
    record(cohort, 'build-reference')
    with pytest.raises(FileNotFoundError): stage['verify_predecessors'](cohort, 'build', 'later')
    record(cohort, 'canary')
    assert set(stage['verify_predecessors'](cohort, 'build', 'later')) == {'canary', 'build-reference'}


def test_private_controls_require_canary_before_any_launch_or_output(cohort, monkeypatch):
    record(cohort, 'setup-peer')
    record(cohort, 'build-reference')
    monkeypatch.setitem(stage, 'load_cohort', lambda *args: ({'cohort': str(cohort)}, {}))
    monkeypatch.setitem(stage, 'source_module', lambda *args: pytest.fail('pre-canary refusal must precede source loading'))
    monkeypatch.setattr(stage['subprocess'], 'Popen', lambda *args, **kwargs: pytest.fail('pre-canary refusal must precede launch'))
    with pytest.raises(FileNotFoundError):
        stage['run_stage'](cohort, '0' * 40, 'private-controls', None, 60)
    assert not (cohort / 'stages/private-controls').exists()


def test_private_controls_follow_clean_canary_without_later_packets_or_snapshots(cohort):
    for name in ('setup-peer', 'build-reference', 'canary'):
        record(cohort, name)
    assert set(stage['verify_predecessors'](cohort, 'private-controls')) == {'canary'}
    assert {path.name for path in (cohort / 'stages').iterdir()} == {'setup-peer', 'build-reference', 'canary'}


@pytest.mark.parametrize('defect', ['held', 'foreign_config', 'changed_artifact'])
def test_early_private_controls_still_require_valid_same_cohort_canary(cohort, defect):
    other = stage['save'](cohort / 'foreign-config.json', {'SYNTHETIC': 'other'})
    artifact = record(cohort, 'canary', status='held' if defect == 'held' else 'passed',
                      configuration=other if defect == 'foreign_config' else None)
    if defect == 'changed_artifact':
        path = Path(artifact['path']); path.chmod(0o644); path.write_text('changed')
    with pytest.raises(ValueError):
        stage['verify_predecessors'](cohort, 'private-controls')


@pytest.mark.parametrize('role,previous', [
    ('later', 'reference'), ('AI_READI', 'later'), ('CM4AI', 'AI_READI'),
    ('VOICE', 'CM4AI'), ('VOICE_PEDIATRIC', 'VOICE'),
    ('registered', 'VOICE_PEDIATRIC'), ('expired', 'registered')])
def test_private_controls_cannot_skip_any_later_main_build(cohort, role, previous):
    record(cohort, 'canary')
    record(cohort, 'private-controls')
    with pytest.raises(FileNotFoundError):
        stage['verify_predecessors'](cohort, 'build', role)
    record(cohort, 'build-' + previous)
    assert set(stage['verify_predecessors'](cohort, 'build', role)) == {'canary', 'build-' + previous}


@pytest.mark.parametrize('completed', [(), ('private-controls',), ('snapshots',)])
def test_assembly_cannot_start_with_either_branch_missing(cohort, completed):
    for name in completed:
        record(cohort, name)
    with pytest.raises(FileNotFoundError):
        stage['verify_predecessors'](cohort, 'assemble-report')


def test_assembly_requires_both_completed_snapshot_and_private_branches(cohort):
    record(cohort, 'private-controls')
    record(cohort, 'snapshots')
    assert set(stage['verify_predecessors'](cohort, 'assemble-report')) == {'snapshots', 'private-controls'}
    assert stage['predecessors']('snapshots') == ['build-expired']
    assert stage['predecessors']('full') == ['assemble-report']


@pytest.mark.parametrize('held', ['private-controls', 'snapshots'])
def test_assembly_refuses_either_held_branch(cohort, held):
    for name in ('private-controls', 'snapshots'):
        record(cohort, name, status='held' if name == held else 'passed')
    with pytest.raises(ValueError, match='did not complete cleanly'):
        stage['verify_predecessors'](cohort, 'assemble-report')


def test_held_predecessor_cannot_become_acceptance(cohort):
    record(cohort, 'build-reference', status='held')
    with pytest.raises(ValueError, match='did not complete cleanly'):
        stage['verify_predecessors'](cohort, 'canary')


def test_foreign_configuration_cannot_relabel_passed_predecessor(cohort):
    other = stage['save'](cohort / 'foreign-config.json', {'SYNTHETIC': 'other'})
    record(cohort, 'build-reference', configuration=other)
    with pytest.raises(ValueError, match='persisted result'):
        stage['verify_predecessors'](cohort, 'canary')


def test_changed_predecessor_artifact_refuses(cohort):
    artifact = record(cohort, 'build-reference')
    path = Path(artifact['path']); path.chmod(0o644); path.write_text('changed')
    with pytest.raises(ValueError, match='pinned bytes'):
        stage['verify_predecessors'](cohort, 'canary')


def test_symlink_cohort_refuses_before_any_stage_directory(cohort):
    link = cohort.parent / 'alias'; link.symlink_to(cohort, target_is_directory=True)
    with pytest.raises(ValueError, match='physical'):
        stage['cohort_path'](link)
    assert list((cohort / 'stages').iterdir()) == []


@pytest.mark.parametrize('action,role', [('unknown', None), ('build', 'OTHER'), ('full', 'reference'), ('canary', '')])
def test_closed_stage_and_role_reject_unplanned_work(action, role):
    with pytest.raises(ValueError): stage['stage_name'](action, role)


def test_supervisor_audit_allows_only_planned_command_and_owned_output(cohort, monkeypatch):
    hooks = []; monkeypatch.setattr(sys, 'addaudithook', hooks.append)
    command = ['/SYNTHETIC/python', '-I', '-S', '-B', '-']
    stage['install_orchestrator_audit'](command, [cohort])
    audit = hooks[0]
    audit('subprocess.Popen', (command[0], command, str(stage['G']), {}))
    with pytest.raises(PermissionError):
        audit('subprocess.Popen', ('/bin/sh', ['/bin/sh', '-c', 'bad'], str(stage['G']), {}))
    with pytest.raises(PermissionError): audit('socket.bind', (None, ('127.0.0.1', 0)))
    with pytest.raises(PermissionError): audit('ctypes.dlopen', ('bad.dylib',))
    audit('open', (str(cohort / 'result.json'), 'w', os.O_WRONLY | os.O_CREAT))
    with pytest.raises(PermissionError):
        audit('open', (str(stage['G'] / 'changed.py'), 'w', os.O_WRONLY | os.O_CREAT))


def test_builder_profile_keeps_source_and_network_denials(cohort):
    value = stage['sandbox_profile']({'sandbox_profile': lambda: '(version 1)\n(deny network*)\n'}, cohort, cohort / 'stages/build-reference')
    assert '(deny network*)' in value
    assert '(deny file-write* (subpath ' + json.dumps(str(stage['G'])) in value
    assert '(deny file-write* (subpath ' + json.dumps(str(stage['N'])) in value


def test_quiet_pause_is_not_counted_as_active_deadline():
    times = iter((0, 10, 20, 30, 40, 50))
    class Child:
        count = 0
        def poll(self): self.count += 1; return None if self.count <= 4 else 0
        def wait(self, timeout): return 0
    class Owned:
        errors = []; known = {(123, 1)}
        def observe(self): pass
        def live(self): return []
        def signal(self, number): raise AssertionError('completed child must not be signaled')
    class Quiet:
        paused = False; count = 0
        def update(self, owned): self.count += 1; self.paused = self.count in (1, 2)
    proof = stage['supervise'](Child(), Owned(), Quiet(), seconds=25,
        clock=lambda: next(times), sleep=lambda seconds: None)
    assert proof['active_seconds'] == 20 and proof['wall_seconds'] == 50
    assert proof['interrupted'] is None and proof['forced_cleanup'] is False


def test_source_fifo_never_uses_blocking_open(cohort, monkeypatch):
    path = cohort / 'SYNTHETIC-fifo'; os.mkfifo(path)
    original = os.open
    def guarded_open(value, flags, *args, **kwargs):
        assert flags & os.O_NONBLOCK
        return original(value, flags, *args, **kwargs)
    monkeypatch.setattr(os, 'open', guarded_open)
    with pytest.raises(ValueError, match='bounded regular file'): stage['read'](path)


@pytest.mark.parametrize('proof', ['missing', 'malformed', 'wrong-status'])
def test_zero_exit_invalid_driver_proof_preserves_held_outcome(cohort, monkeypatch, proof):
    directory = cohort / 'stages/canary'; directory.mkdir()
    destination = cohort / 'SYNTHETIC-demonstration'; destination.mkdir()
    if proof == 'malformed': stage['save'](destination / 'demonstration-results.json', b'{')
    if proof == 'wrong-status': stage['save'](destination / 'demonstration-results.json', {'status': 'held', 'cases': []})
    monkeypatch.setitem(stage, 'load_cohort', lambda *args: None)
    declaration = stage['finalize_stage'](directory, cohort=cohort, commit='0' * 40,
        action='canary', role=None, envelope={'config': stage['pin'](cohort / 'stage-config.json')},
        prior={}, outcome={'interrupted': None, 'forced_cleanup': False,
            'observed_surviving_pids': [], 'observation_errors': []}, returncode=0, destination=destination)
    result = json.loads(stage['checked'](declaration))
    assert result['status'] == 'held' and result['returncode'] == 0 and result['cleanup_verified'] is True
    assert result['proof_error'] and Path(declaration['path']).lstat().st_mode & 0o222 == 0


@pytest.mark.parametrize('raw', [b'{', b'[]', b'null', b'1'])
def test_malformed_child_result_preserves_held_outcome(cohort, monkeypatch, raw):
    directory = cohort / 'stages/setup-peer'; directory.mkdir()
    proof = stage['save'](directory / 'result.json', raw)
    monkeypatch.setitem(stage, 'load_cohort', lambda *args: None)
    declaration = stage['finalize_stage'](directory, cohort=cohort, commit='0' * 40,
        action='setup-peer', role=None, envelope={'config': stage['pin'](cohort / 'stage-config.json')},
        prior={}, outcome={'interrupted': None, 'forced_cleanup': False,
            'observed_surviving_pids': [], 'observation_errors': []}, returncode=0)
    result = json.loads(stage['checked'](declaration))
    assert result['status'] == 'held' and result['result'] == proof and result['proof_error']


def test_foreign_valid_cohort_envelope_cannot_redirect_stage(tmp_path, monkeypatch):
    scratch = tmp_path / 'scratch'; (scratch / 'tests').mkdir(parents=True)
    monkeypatch.setitem(stage, 'S', scratch)
    monkeypatch.setitem(stage, 'capture_sources', lambda commit: {})
    dependency = scratch / 'dependency'; dependency.mkdir()
    bounds = stage['save'](scratch / 'bounds.json', {'SYNTHETIC': 'bounds'})
    envelopes = []
    for name in ('one', 'two'):
        root = scratch / 'tests' / name; root.mkdir()
        (root / 'venv/bin').mkdir(parents=True)
        installed = root / 'venv/lib/python3.13/site-packages'; installed.mkdir(parents=True)
        python = root / 'venv/bin/python'; python.write_text('SYNTHETIC never executed')
        venv = stage['save'](root / 'venv/pyvenv.cfg', b'SYNTHETIC\n')
        bootstrap = stage['save'](root / 'bootstrap.json', {'test_python': str(python),
            'dependency_site': str(dependency), 'files': {}, 'controlled_distribution': {'files': {}}})
        packet = root / 'cases/test_final_format_registration0'
        config = {'cohort': str(root), 'source_root': str(stage['G']), 'source_commit': '0' * 40,
            'python': str(python), 'dependency_prefix': str(root / 'venv'), 'packet_root': str(packet),
            'peer_root': str(packet / 'SYNTHETIC-shared-peer'), 'home': str(packet / 'SYNTHETIC-shared-peer/synthetic-home'),
            'code_inputs': {}, 'bounds': bounds, 'bootstrap': bootstrap,
            'dependency_roots': [str(installed), str(dependency)]}
        configuration = stage['save'](root / 'stage-config.json', config)
        envelope = {'source_commit': '0' * 40, 'config': configuration, 'sources': {},
            'launcher': stage['pin'](SCRIPT), 'interpreter': stage['pin'](python), 'venv_config': venv}
        stage['save'](root / 'orchestration-inputs.json', envelope)
        assert stage['load_cohort'](root, '0' * 40)[0] == config
        envelopes.append((root, envelope))
    target = envelopes[1][0] / 'orchestration-inputs.json'
    target.chmod(0o644); target.write_text(json.dumps(envelopes[0][1])); target.chmod(0o444)
    with pytest.raises(ValueError, match='another cohort configuration'):
        stage['load_cohort'](envelopes[1][0], '0' * 40)
    assert not (envelopes[0][0] / 'stages').exists() and not (envelopes[1][0] / 'stages').exists()


def test_full_stage_uses_frozen_plan_count_instead_of_historical_28(cohort, monkeypatch):
    directory = cohort / 'stages/full'; directory.mkdir()
    destination = cohort / 'SYNTHETIC-full'; destination.mkdir()
    plan = stage['save'](cohort / 'SYNTHETIC-case-plan.json', {'cases': [{'SYNTHETIC': number} for number in range(35)]})
    stage['save'](destination / 'demonstration-results.json', {
        'status': 'all_requested_demonstrations_passed', 'cases': [{'SYNTHETIC': number} for number in range(28)]})
    monkeypatch.setitem(stage, 'load_cohort', lambda *args: None)
    declaration = stage['finalize_stage'](directory, cohort=cohort, commit='0' * 40,
        action='full', role=None, envelope={'config': stage['pin'](cohort / 'stage-config.json'),
            'sources': {'scripts/adhoc/h3_refinement_cases_20261113.json': plan}}, prior={},
        outcome={'interrupted': None, 'forced_cleanup': False, 'observed_surviving_pids': [], 'observation_errors': []},
        returncode=0, destination=destination)
    result = json.loads(stage['checked'](declaration))
    assert result['status'] == 'held' and 'complete comparison proof' in result['proof_error']


def test_over_bound_builder_persists_measurement_and_blocks_canary(cohort, monkeypatch):
    directory = cohort / 'stages/build-reference'; directory.mkdir()
    configuration = stage['pin'](cohort / 'stage-config.json')
    stage['save'](directory / 'result.json', dict(status='passed', action='build', role='reference',
        config=configuration, outputs={}, side_effects=stage['COUNTERS']))
    monkeypatch.setitem(stage, 'load_cohort', lambda *args: ({}, {}))
    monkeypatch.setitem(stage, 'authority_bounds_barrier', lambda *args:
        dict(total_bytes=8_000_001, threshold_bytes=8_000_000, within_threshold=False))
    saved = stage['finalize_stage'](directory, cohort=cohort, commit='0' * 40,
        action='build', role='reference', envelope={'config': configuration}, prior={},
        outcome=dict(interrupted=None, forced_cleanup=False, observed_surviving_pids=[], observation_errors=[]), returncode=0)
    outcome = json.loads(stage['checked'](saved))
    assert outcome['status'] == 'held'
    assert '8000000-byte' in outcome['postflight_error']
    assert json.loads(stage['checked'](outcome['authority_bounds']))['total_bytes'] == 8_000_001
    with pytest.raises(ValueError, match='did not complete cleanly'):
        stage['verify_predecessors'](cohort, 'canary')


def test_failed_bounds_readback_blocks_builder_acceptance(cohort, monkeypatch):
    directory = cohort / 'stages/build-reference'; directory.mkdir()
    configuration = stage['pin'](cohort / 'stage-config.json')
    stage['save'](directory / 'result.json', dict(status='passed', action='build', role='reference',
        config=configuration, outputs={}, side_effects=stage['COUNTERS']))
    monkeypatch.setitem(stage, 'load_cohort', lambda *args: ({}, {}))
    def failed(*args):
        raise ValueError('authority pin changed')
    monkeypatch.setitem(stage, 'authority_bounds_barrier', failed)
    saved = stage['finalize_stage'](directory, cohort=cohort, commit='0' * 40,
        action='build', role='reference', envelope={'config': configuration}, prior={},
        outcome=dict(interrupted=None, forced_cleanup=False, observed_surviving_pids=[], observation_errors=[]), returncode=0)
    outcome = json.loads(stage['checked'](saved))
    assert outcome['status'] == 'held' and 'authority pin changed' in outcome['postflight_error']
