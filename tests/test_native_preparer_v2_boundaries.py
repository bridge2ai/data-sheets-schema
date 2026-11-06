"""Structural version boundaries, refusals and source reachability (#5508)."""
import json
from pathlib import Path
import subprocess
import sys
import pytest
from tests.test_native_authority_v2 import isolated, selected, case, inputs, API_ARGS, DIRECT_ARGS
from data_sheets_schema import native_supervisor_authority_v2 as authority
from data_sheets_schema import native_attribution_controller_v2 as controller


def test_source_commit_bytes(isolated):
    manifest = controller.controller_sources()
    for pin in manifest['modules'].values():
        raw = subprocess.check_output(['git', 'show', f"{manifest['source_commit']}:{pin['path']}"], cwd=controller.ROOT)
        assert authority.sha256(raw) == pin['sha256']


@pytest.mark.parametrize('change,reason', [
    (['--projects', 'UNDECLARED'], 'every project must be declared'),
    (['--projects', 'CHORUS,CHORUS'], 'projects must name unique'),
    (['--canary-order', 'missing'], 'outside the selected registered roster'),
    (['--canary-order', 'a,a'], 'canary order must name unique'),
    (['--external-sources', '/nonexistent-u2-evidence'], 'external evidence directory must exist'),
])
def test_preparer_refusals(isolated, monkeypatch, tmp_path, capsys, change, reason):
    with authority.loaded_dependencies(authority.dependency_identity()) as modules:
        monkeypatch.setattr(sys, 'argv', ['prepare', '--render-only', '--output', str(tmp_path/'out'), '--projects', 'CHORUS', '--canary-order', 'CHORUS_api_rep1', *API_ARGS, *change])
        with pytest.raises(SystemExit) as error:
            modules['prepare_registration'].main()
        assert error.value.code == 2
        assert reason in capsys.readouterr().err
        assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('project,profile,reason', [('CHORUS', 'neutral', 'declared and distinct'), ('UNDECLARED', 'neutral', 'declared and distinct'), ('KIDS_FIRST', 'wrong', 'profile differs')])
def test_external_refusals(isolated, monkeypatch, tmp_path, capsys, project, profile, reason):
    with authority.loaded_dependencies(authority.dependency_identity()) as modules:
        base=controller.ROOT/'notes/matched_cborg_2026-09-13/kids_first'
        meta=tmp_path/'external.json'
        meta.write_text(json.dumps({'project': project, 'profile': profile, 'source_manifest': str(base/'manifest.yaml'), 'chunks': str(base/'chunks.yaml')}))
        monkeypatch.setattr(sys, 'argv', ['prepare', '--render-only', '--output', str(tmp_path/'out'), '--projects', 'CHORUS', '--canary-order', 'CHORUS_api_rep1', *API_ARGS, '--external-canary', str(meta)])
        with pytest.raises(SystemExit):
            modules['prepare_registration'].main()
        assert reason in capsys.readouterr().err


def test_direct_declares(isolated, monkeypatch, tmp_path):
    with authority.loaded_dependencies(authority.dependency_identity()) as modules:
        direct=modules['prepare_direct']
        monkeypatch.setattr(direct.subprocess, 'check_output', lambda *a, **k: 'offline')
        args=direct.parser().parse_args(['--output', str(tmp_path/'out'), '--project', 'UNDECLARED', *DIRECT_ARGS, '--claude-executable', sys.executable])
        with pytest.raises(direct.DirectStop, match='project must be declared'):
            direct.build(args)
        assert not (tmp_path/'out').exists()


def test_api_preparation_serializes_envelope(isolated, monkeypatch, tmp_path):
    with authority.loaded_dependencies(authority.dependency_identity()) as modules:
        prep = modules['prepare_registration']
        (tmp_path/'api_initial_admission.json').write_text('{}')
        original = subprocess.check_output
        def offline(command, *args, **kwargs):
            if command == ['/unused', '--version']:
                return 'synthetic offline version'
            assert command[0] == 'git'
            return original(command, *args, **kwargs)
        monkeypatch.setattr(subprocess, 'check_output', offline)
        monkeypatch.setattr(sys, 'argv', ['prepare', '--output', str(tmp_path), '--projects', 'CHORUS', '--canary-order', 'CHORUS_api_rep1', *API_ARGS])
        prep.main()
        path = tmp_path/'registration.json'
        value = json.loads(path.read_bytes())
        inner = prep.require_envelope(value)
        assert inner['status'] == 'awaiting_preflight_review'
        assert inner['budget']['authorization'] == 'user: +$200, 2026-09-13'
        assert inner['pinned_files'][str(Path(prep.__file__))] == prep.sha(prep.__file__)
        with pytest.raises(KeyError) as error:
            modules['run_api_canary'].verify(value, path, prep.sha(path))
        assert error.value.args == ('repository',)


def test_frozen_verifiers_and_launchers_refuse_envelope(isolated, monkeypatch, tmp_path):
    with authority.loaded_dependencies(authority.dependency_identity()) as modules:
        prep=modules['prepare_registration']
        record=prep.envelope({'schema_version': 2})
        assert prep.require_envelope(record) == {'schema_version': 2}
        for invalid in (None, [], {'schema_version': 1}, {**record, 'authority_version': 1}, {**record, 'registration': {'schema_version': 2.0}}, {**record, 'controller_sources_sha256': '0'*64}):
            with pytest.raises(ValueError, match='exact v2 authority envelope'):
                prep.require_envelope(invalid)
        path=tmp_path/'registration.json'; path.write_text(json.dumps(record))
        api=modules['run_api_canary']; direct=modules['run_direct_canary']; native=modules['run_native_canary']
        def forbidden(*a, **k):
            pytest.fail('launch side effect reached')
        for module in (api, direct, native):
            monkeypatch.setattr(module, 'open_ledger', forbidden, raising=False)
            monkeypatch.setattr(module, 'cborg_client', forbidden, raising=False)
        monkeypatch.setattr(subprocess, 'Popen', forbidden)
        with pytest.raises(KeyError) as error:
            api.verify(record, path, api.sha(path))
        assert error.value.args == ('repository',)
        assert native.verify is api.verify
        with pytest.raises(KeyError) as error:
            native.verify(record, path, api.sha(path))
        assert error.value.args == ('repository',)
        with pytest.raises(direct.BudgetStop, match='not a direct-arm registration'):
            direct.verify_registration(record, path)
        review=tmp_path/'review.json'
        review.write_text(json.dumps({'verdict':'approve', 'ci_conclusion':'success', 'registration_sha256':api.sha(path), 'allowed_jobs':['job']}))
        monkeypatch.setattr(sys, 'argv', ['api', '--registration', str(path), '--review', str(review), '--job', 'job'])
        with pytest.raises(api.BudgetStop, match='external source registration is incomplete'):
            api.main()
        with pytest.raises(direct.BudgetStop, match="CI evidence is not on the registered code commit"):
            direct.main(['--registration',str(path),'--review',str(review),'--job','job','--launch-word',str(review)])
        overlay=tmp_path/'overlay.json'
        overlay.write_text(json.dumps({'registration':str(path),'registration_sha256':api.sha(path),'allowed_jobs':['job']}))
        value=json.loads(review.read_text()); value['overlay_sha256']=api.sha(overlay); review.write_text(json.dumps(value))
        monkeypatch.setattr(sys, 'argv', ['native','--overlay',str(overlay),'--review',str(review),'--job','job'])
        with pytest.raises(KeyError) as error:
            native.main()
        assert error.value.args == ('repository',)
        assert not (tmp_path/'attempts').exists()
