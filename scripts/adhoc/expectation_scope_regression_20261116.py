"""Offline saved expectation regression for PR 5968, 2026-11-16.
Derived from codex 196 Step 5e producers. Inputs: project and scratch directory.
Outputs: prefix through expectation, foreign-origin refusal, byte evidence.
Invented saved runtime observations only; no native executable or provider call.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)
b = sys.modules[__name__]

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def load(path):
    return json.loads(path.read_bytes())


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def inputs(project):
    return dict(source_manifest=ROOT / 'data/preprocessed/source_manifest.yaml',
        bundle=ROOT / 'data/preprocessed/concatenated' / (project + '_preprocessed.txt'),
        chunk_manifest=ROOT / 'data/preprocessed/chunks' / (project + '_chunks.yaml'),
        context=ROOT / 'data/omission_contexts' / (project.lower() + '_omission_context.json'),
        full_schema=ROOT / 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        core_schema=ROOT / 'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml')


def prefix(project):
    packet = SCRATCH / 'packets' / project
    packet.mkdir(parents=True, exist_ok=True)
    paths = inputs(project)
    for path in paths.values():
        assert path.is_file() and path == path.resolve()
    stage = SCRATCH / 'never-launched-attempts' / project / 'stages'
    command = [str(PYTHON), '-P', '-B', str(ROOT / 'scripts/build_native_canary_packet.py'),
        '--checkout', str(ROOT), '--output', str(packet / 'input-prefix'),
        '--stage-root', str(stage), '--project', project, '--profile', 'bridge2ai',
        '--registration-id', 'OFFLINE-STEP5E-' + project,
        '--label', 'OFFLINE-STEP5E-NOT-LAUNCH-AUTHORITY']
    for name, path in paths.items():
        command += ['--' + name.replace('_', '-'), str(path)]
    save(packet / 'prefix-command.json', dict(command=command, inputs={name: pin(path) for name, path in paths.items()}))
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=1500)
    (packet / 'prefix.stdout').write_bytes(result.stdout)
    (packet / 'prefix.stderr').write_bytes(result.stderr)
    status = load(packet / 'input-prefix/status.json')
    artifact_names = ('receipt-policy.json', 'selection.json', 'environment-manifest.json', 'input-inventory.json', 'status.json')
    artifacts = {name: pin(packet / 'input-prefix' / name) for name in artifact_names
                 if (packet / 'input-prefix' / name).is_file()}
    record = dict(returncode=result.returncode, status=status, artifacts=artifacts, stage_root_exists=stage.exists())
    save(packet / 'prefix-result.json', record)
    assert not stage.exists()
    if result.returncode == 2:
        assert status['status'] == 'dependency_stop' and len(artifacts) == len(artifact_names)
        assert all(row['bytes'] > 0 for row in artifacts.values())
    else:
        assert result.returncode == 1 and status['status'] == 'production_refusal'
    print(json.dumps(dict(project=project, returncode=result.returncode, status=status['status'],
        message=status.get('message'), artifact_bytes={name: row['bytes'] for name, row in artifacts.items()})), flush=True)


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def saved(packet, step, inputs):
    source = packet / (step + '-inputs.json')
    b.save(source, inputs)
    target = packet / step
    command = [str(b.PYTHON), '-P', '-B', str(ROOT / 'scripts/native_canary_saved_step.py'),
        '--checkout', str(ROOT), '--step', step, '--inputs', str(source), '--output', str(target)]
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=1500)
    write(packet / (step + '.stdout'), result.stdout)
    write(packet / (step + '.stderr'), result.stderr)
    evidence = dict(command=command, returncode=result.returncode,
        seconds=time.monotonic() - started, inputs=b.pin(source),
        artifacts={p.name:b.pin(p) for p in target.iterdir()} if target.exists() else {})
    b.save(packet / (step + '-result.json'), evidence)
    print(json.dumps(dict(step=step, project=packet.name, returncode=result.returncode,
        bytes={k:v['bytes'] for k,v in evidence['artifacts'].items()})), flush=True)
    if result.returncode:
        raise RuntimeError(step + ' refused: ' + result.stderr.decode(errors='replace')[-2200:])
    assert evidence['artifacts'] and all(v['bytes'] for v in evidence['artifacts'].values())
    return target


def chain(project):
    if not (SCRATCH / 'packets' / project / 'prefix-result.json').exists():
        b.prefix(project)
    packet = SCRATCH / 'packets' / project
    prefix = packet / 'input-prefix'
    if b.load(packet / 'prefix-result.json')['returncode'] != 2:
        raise RuntimeError('Offline prefix refused before saved steps')
    sys.path.insert(0, str(ROOT))
    from data_sheets_schema import native_shared_contract as c
    from tests.test_native_u4b_runtime import runtime_inputs
    from tests.utils.native_u4b_observation import mint_observation
    from tests.utils.native_synthetic_evidence import bound_permission_for
    common = SCRATCH / 'OFFLINE-PLACEHOLDERS'
    common.mkdir(exist_ok=True)
    inert = b'OFFLINE STEP5E INERT FINGERPRINT PLACEHOLDER. NEVER EXECUTE.\n'
    for path in (common / 'updater/current', common / 'inert-copy'):
        if not path.exists():
            write(path, inert)
            path.chmod(0o700)
        assert path.read_bytes() == inert
    system = common / 'system.md'
    if not system.exists():
        write(system, b'OFFLINE STEP5E PLACEHOLDER SYSTEM. No actual native run is authorized.\n')
    fixtures = packet / 'OFFLINE-SAVED-PROBE-PLACEHOLDERS'
    fixtures.mkdir()
    runtime, arguments = runtime_inputs(fixtures, binary_bytes=inert)
    attempt_id = 'OFFLINE-STEP5E-' + project
    attempt_parent = SCRATCH / 'never-launched-attempts' / project
    attempt_parent.mkdir(parents=True, exist_ok=True)
    attempt = attempt_parent / attempt_id
    evidence_parent = SCRATCH / 'never-launched-evidence' / project
    evidence_parent.mkdir(parents=True, exist_ok=True)
    runtime['executable']['path'] = str(common / 'inert-copy')
    runtime['environment']['PYSTOW_HOME'] = str(attempt / 'helper-cache')
    runtime['environment']['HOME'] = str(common / 'unused-home')
    runtime['provider'] = 'OFFLINE-PLACEHOLDER-first-party-selection'
    arguments.update(updater_source=str(common / 'updater/current'), updater_root=str(common / 'updater'),
        thinking_basis='OFFLINE PLACEHOLDER: adaptive thinking, not a live observation.')
    arguments['admission_policy'].update(valid_from='2026-11-16T00:00:00Z', valid_until='2026-11-30T00:00:00Z')
    arguments['observation_probe_path'] = str(mint_observation(runtime,
        Path(arguments['probe_init_path']), Path(arguments['native_request_path'])))
    raw_runtime = packet / 'OFFLINE-runtime-input.json'
    write(raw_runtime, c.canonical(runtime))
    b.save(packet / 'PLACEHOLDERS.json', dict(scope='Explicit invented offline sizing fixtures, never observed evidence or launch authority.',
        placeholders={'binary_identity':'Same inert text file for every project; never executed.',
            'binary_version':'local fixture / fixture-1', 'model_aliases':'claude-opus-5[1m] / claude-opus-5',
            'contextWindow':1000000, 'maxOutputTokens':64000, 'thinking':{'type':'adaptive'},
            'authentication':'Invented Max firstParty declaration; no account inspected.',
            'observation_and_probe_word':'Invented offline fixture identity in test utility; no human authorization.',
            'observation_process':'Saved fabricated spawn/cleanup declarations; no process launched.',
            'permission_traces':'Seven fabricated software-test traces made after expectation, no probe executed.',
            'admission_dates':arguments['admission_policy'], 'system':b.pin(system),
            'runtime_home':runtime['environment']['HOME'], 'attempt':str(attempt),
            'receipt_floor':'pending diagnostic_pilot', 'draft_checks':2,
            'job_id':'OFFLINE-STEP5E-' + project, 'run_date':'2026-11-16'},
        fixture_producers={str(p.relative_to(ROOT)):b.pin(p) for p in (
            ROOT / 'tests/test_native_u4b_runtime.py', ROOT / 'tests/utils/native_u4b_observation.py',
            ROOT / 'tests/utils/native_synthetic_evidence.py', ROOT / 'tests/test_native_shared_permissions.py')}))
    runtime_dir = saved(packet, 'runtime', dict(runtime_path=str(raw_runtime), arguments=arguments))
    preparation = saved(packet, 'preparation', dict(selection_path=str(prefix / 'selection.json'),
        runtime_path=str(runtime_dir / 'runtime.json'), environment_manifest_path=str(prefix / 'environment-manifest.json'),
        job_id='OFFLINE-STEP5E-' + project, run_date='2026-11-16', max_draft_checks=2))
    composition = saved(packet, 'composition', dict(preparation_path=str(preparation / 'preparation.json'),
        instruction_path=str(preparation / 'instruction.md')))
    expectation = saved(packet, 'expectation', dict(composition_path=str(composition / 'composition.json'),
        system_path=str(system), config_directory=str(attempt / 'cli_config')))
    expected = b.load(expectation / 'expectation.json')
    assert expected and (expectation / 'expectation.json').stat().st_size > 0
    # Run the original invalid handoff against the genuine verified consumer.
    from data_sheets_schema.native_shared_controller_orchestration import reconstruct_composition
    from data_sheets_schema.native_shared_permission_orchestration import loaded_permission_inputs
    from data_sheets_schema import native_execution_authority_v2 as authority
    raw = (composition / 'composition.json').read_bytes()
    composed, foreign, _ = reconstruct_composition(raw)
    dependencies = composed['dependencies']
    with loaded_permission_inputs(dependencies) as (controls, _), authority.loaded_verified_package_module(
            'data_sheets_schema.native_shared_registration',
            package_sources=dependencies['base']['package_sources']) as consumer:
        effective = system.read_bytes().decode('utf-8') + consumer.policy.command_guidance(
            composed['policy'], classifier_projection=controls)
        try:
            consumer.permission_expectation(c.strict_json(composed['runtime_raw_json'].encode()),
                composed, foreign, effective, attempt / 'cli_config', dependencies)
        except ValueError as exc:
            assert 'registered inputs have no construction origin' in str(exc), str(exc)
            refusal = str(exc)
        else:
            raise AssertionError('foreign-origin RunSpec accepted')
        selected, own, _, runtime = consumer._selection(raw,
            preparation_raw=composed['preparation_raw_json'].encode('utf-8'),
            classifier_projection=controls)
        actual = consumer.permission_expectation(runtime, selected, own, effective,
            attempt / 'cli_config', dependencies)
        assert c.canonical(actual) == c.canonical(expected)
    assert not attempt.exists() and not Path(b.load(prefix / 'selection.json')['stage_root']).exists()
    b.save(packet / 'regression-result.json', dict(project=project,
        saved_expectation=b.pin(expectation / 'expectation.json'), foreign_origin_refusal=refusal,
        verified_consumer_matches_cli=True, native_execution=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', choices=('CHORUS', 'AI_READI'), required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    SCRATCH = args.scratch.resolve()
    assert not SCRATCH.is_relative_to(ROOT)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    chain(args.project)
