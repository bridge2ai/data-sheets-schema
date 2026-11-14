"""G13 offline packet prefix: real repository inputs; no native/provider calls."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/build_native_canary_packet.py'
spec = importlib.util.spec_from_file_location('packet_builder', SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def command(out):
    paths = {'checkout': ROOT, 'output': out,
        'source-manifest': ROOT/'data/preprocessed/source_manifest.yaml',
        'bundle': ROOT/'data/preprocessed/concatenated/CHORUS_preprocessed.txt',
        'chunk-manifest': ROOT/'data/preprocessed/chunks/CHORUS_chunks.yaml',
        'context': ROOT/'data/omission_contexts/chorus_omission_context.json',
        'full-schema': ROOT/'src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        'core-schema': ROOT/'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml',
        'stage-root': out.parent/'never-reserved-attempt'/'stages',
        'project': 'CHORUS', 'profile': 'bridge2ai',
        'registration-id': 'DRAFT-OFFLINE-CHORUS-NOT-AUTHORITY', 'label': 'DRAFT-OFFLINE-NOT-AUTHORITY'}
    return [sys.executable, '-P', '-B', str(SCRIPT), *(s for k,v in paths.items() for s in ('--'+k,str(v)))]


def invoke(out):
    args = command(out)
    env = dict(os.environ, D4D_PROFILE='neutral')  # Must not affect explicit declaration.
    run = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    (out.parent/'builder-command.json').write_text(json.dumps(args, indent=2)+'\n')
    (out.parent/'builder.stdout').write_text(run.stdout)
    (out.parent/'builder.stderr').write_text(run.stderr)
    return run


def test_real_chorus_prefix(tmp_path):
    out = tmp_path/'packet'
    run = invoke(out)
    assert run.returncode == 2, run.stdout + run.stderr
    status = json.loads((out/'status.json').read_bytes())
    assert status['status'] == 'dependency_stop'
    from data_sheets_schema import native_shared_selection as selection
    captured = selection.capture(out/'selection.json')
    assert captured.project == 'CHORUS'
    declaration = json.loads((out/'selection.json').read_bytes())
    assert declaration['inputs']['profile']['name'] == 'bridge2ai'
    assert declaration['bounds']=={
        'max_workers':64,'max_populated_paths':32768,'max_paths_per_worker':8192,
        'max_submissions':128,'max_history_records':1024,'max_inventory_bytes':2000000,
        'max_input_bytes':4000000,'max_authority_bytes':16000000,
        'max_evidence_bytes':256000000,'max_history_bytes':48000000,
        'max_request_bytes':32000000,'max_response_bytes':4000000}
    assert 'AUTHORIZE_TWO_SCRIPTED_NATIVE_PROBES' in status['producer_authorization']
    assert not (tmp_path/'never-reserved-attempt').exists()
    assert all((out/name).stat().st_size for name in status['completed'])


def test_existing_output_is_never_overwritten(tmp_path):
    out=tmp_path/'packet'; out.mkdir()
    sentinel=out/'selection.json'; sentinel.write_bytes(b'original')
    run=invoke(out)
    assert run.returncode != 0
    assert 'refusing existing output' in run.stderr
    assert sentinel.read_bytes() == b'original'
    assert set(out.iterdir()) == {sentinel}


def test_output_symlink_is_refused(tmp_path):
    target=tmp_path/'target'; target.mkdir()
    out=tmp_path/'link'; out.symlink_to(target, target_is_directory=True)
    run=invoke(out)
    assert run.returncode != 0
    assert 'absolute and physical' in run.stderr
    assert not list(target.iterdir())


def test_changed_chunk_manifest_refuses_before_selection(tmp_path):
    out=tmp_path/'packet'
    args=command(out)
    chunks=tmp_path/'bad-chunks.yaml'
    chunks.write_text('bundle: forged\n')
    args[args.index('--chunk-manifest')+1]=str(chunks)
    run=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=180)
    assert run.returncode == 1
    assert json.loads((out/'status.json').read_bytes())['status']=='production_refusal'
    assert not (out/'selection.json').exists()


@pytest.mark.parametrize('action', ['process', 'network', 'write', 'symlink'])
def test_audit_barrier_denies_effects(tmp_path, action):
    # The helper is a durable test source, never an inline shell/python program.
    helper=ROOT/'tests/utils/native_packet_audit_probe.py'
    out=tmp_path/'out'; out.mkdir()
    run=subprocess.run([sys.executable,'-P','-B',str(helper),str(out),action],cwd=ROOT,capture_output=True,text=True)
    assert run.returncode == 0, run.stdout+run.stderr
    assert 'DENIED' in run.stdout
    assert not (tmp_path/'outside').exists()


def test_stage_root_cannot_overlap_packet(tmp_path):
    out=tmp_path/'packet'; args=command(out)
    args[args.index('--stage-root')+1]=str(out/'stages')
    run=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=180)
    assert run.returncode!=0
    assert 'fresh and disjoint' in run.stderr
    assert not out.exists()
