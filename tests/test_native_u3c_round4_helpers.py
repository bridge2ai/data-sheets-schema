"""C4 launcher routing and actual composite import census; no admission claim."""
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def helper(name):
    path = ROOT / 'scripts/adhoc' / name
    spec = importlib.util.spec_from_file_location(name.removesuffix('.py'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parent_worker_and_subprocess_reenter_c4_wrapper():
    module = helper('run_native_u3c_round4_20261107.py')
    assert module.runner.SCRATCH == ROOT.parent / 'scratch-native-u3c-r4'
    assert module.runner.ROOT == ROOT
    assert Path(module.runner.__file__) == Path(module.__file__)
    assert module.runner.LOCK == ROOT.parent / 'plans/native_quiet_window.lock'
    assert module.runner.DEADLINE == 3600
    env = module.runner.clean_environment(module.SCRATCH / 'synthetic', ROOT / 'venv/bin')
    assert env['PYTHONPATH'] == str(ROOT / 'src') + ':' + str(ROOT)
    assert not any('TOKEN' in name or 'KEY' in name or 'SECRET' in name for name in env)
    assert '(deny network*)' in module.runner.PROFILE
    assert '(deny file-write*' in module.runner.PROFILE
    assert module.smoke_evidence()['destination'] == 'pytest tmp_path/cpu-smoke*.json'


def test_actual_c_and_overlay_d_graphs_are_accepted(pytestconfig, record_property):
    module = helper('census_native_u3c_round4_20261107.py')
    bootstrap = Path(pytestconfig.option.basetemp).parent / 'bootstrap.json'
    dependencies = Path(json.loads(bootstrap.read_bytes())['dependency_site'])
    # Keep source/graph evidence outside transient pytest fixture cleanup.
    out = Path(pytestconfig.option.basetemp).parent / 'graph-census'
    plan = json.loads((bootstrap.parent / 'plan.json').read_bytes())
    result = module.build_and_inspect(out, dependencies, scratch_root=plan['scratch_root'])
    record_property('census_artifact', str(out / 'census.json'))
    expected = set(module.C_CONSUMERS) | set(module.D_CONSUMERS) | set(module.D_SUPPORT)
    assert set(result['outcomes']) == expected
    assert len(result['outcomes']) == 28
    assert result['rosters'] == {'C': list(module.C_CONSUMERS),
                                'D': list(module.D_CONSUMERS), 'D_support': list(module.D_SUPPORT)}
    assert len(result['old_D8_refusals']) == 7
    # A real remaining refusal stays a failure and is retained in census.json.
    # Passing graph checks alone still establish neither admission nor lifetime.
    assert result['remaining_refusals'] == {}, result['remaining_refusals']
