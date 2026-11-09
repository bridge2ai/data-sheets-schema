"""Historical C4 wrapper routing and current integrated graph census; no admission claim."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401


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


def test_current_integrated_c_and_d_graphs_are_accepted(tmp_path, isolated_modules, record_property):
    """U3-F2 replaces the retired D8-overlay node without launcher-only fixtures."""
    module = helper('census_native_u3c_round4_20261107.py')
    out = tmp_path.resolve() / 'graph-census'
    result = module.inspect_current(out)
    record_property('census_artifact', str(out / 'census.json'))
    assert json.loads((out / 'census.json').read_bytes()) == result
    manifest = json.loads((out / 'manifest.json').read_bytes())
    stability = json.loads((out / 'source-stability.json').read_bytes())
    assert manifest['root'] == str(ROOT)
    assert manifest['source_overlay'] is False
    assert manifest['historical_overlay_retired']['D8_head'] == module.HISTORICAL_D8_HEAD
    assert manifest['helper_sha256'] == hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
    assert manifest['files']
    assert {path: item['sha256'] for path, item in manifest['files'].items()} == (
        manifest['dependency_identity']['base']['package_sources'])
    for relative, item in manifest['files'].items():
        raw = (ROOT / relative).read_bytes()
        assert item == {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    assert result['source_stability'] == stability == {
        'package_sources_unchanged': True,
        'helper_source_unchanged': True,
        'consumer_modules_unchanged': True,
    }
    expected = set(module.C_CONSUMERS) | set(module.D_CONSUMERS) | set(module.D_SUPPORT)
    assert set(result['outcomes']) == expected
    assert len(result['outcomes']) == 28
    assert set(result['A_closed_owned_roster']) == {'data_sheets_schema.' + name for name in expected}
    assert result['rosters'] == {'C': list(module.C_CONSUMERS),
                                'D': list(module.D_CONSUMERS), 'D_support': list(module.D_SUPPORT)}
    assert len(result['historical_D8_refusals']) == 7
    # A real remaining refusal stays a failure and is retained in census.json.
    # Passing graph checks alone still establish neither admission nor lifetime.
    assert result['remaining_refusals'] == {}, result['remaining_refusals']
    for short, row in result['outcomes'].items():
        name = 'data_sheets_schema.' + short
        assert row['status'] == 'accepted'
        stem = 'src/data_sheets_schema/' + short
        relative, = (path for path in (stem + '.py', stem + '/__init__.py')
                     if path in manifest['files'])
        assert row['graph'][name] == manifest['files'][relative]['sha256']


def test_current_census_refuses_existing_output_without_overwriting(tmp_path):
    module = helper('census_native_u3c_round4_20261107.py')
    out = tmp_path.resolve() / 'graph-census'
    out.mkdir()
    witness = out / 'retained.json'
    witness.write_bytes(b'{"prior_evidence": true}\n')
    with pytest.raises(FileExistsError):
        module.inspect_current(out)
    assert list(out.iterdir()) == [witness]
    assert witness.read_bytes() == b'{"prior_evidence": true}\n'
