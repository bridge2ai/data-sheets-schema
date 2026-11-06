"""U0 pair admission regressions; diagnostic isolation only, 2026-11-06."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/adhoc' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('target', ['pair-control', 'pair-treatment'])
def test_pair_mode_admits_only_its_declared_diagnostic_targets(target):
    driver = load('native_recorder_measure_20261026')
    driver.require_mode_target('cpu-pair', target)
    for mode in ('idle', 'load-diagnostic', 'cpu-profile'):
        with pytest.raises(ValueError, match='exact diagnostic target'):
            driver.require_mode_target(mode, target)
    with pytest.raises(ValueError, match='idle-only'):
        driver.require_mode_target('cpu-pair', target, True)


@pytest.mark.parametrize('target', ['current', 'original', 'delivery', 'cpu-profile'])
def test_pair_never_reuses_previous_baseline_or_failed_profile(target):
    driver = load('native_recorder_measure_20261026')
    with pytest.raises(ValueError, match='exact diagnostic target'):
        driver.require_mode_target('cpu-pair', target)
    wrapper = load('native_u0_run_20261106')
    with pytest.raises(ValueError, match='exact diagnostic target'):
        wrapper.resolve_arguments(SimpleNamespace(mode='cpu-pair', target=target, idle_only=False))


def test_pair_authority_does_not_authorize_campaign_or_wall_acceptance():
    driver = load('native_recorder_measure_20261026')
    wrapper = load('native_u0_run_20261106')
    for module in (driver, wrapper):
        assert 'no n=10' in module.CAUSAL_PAIR_AUTHORITY.lower()
        assert 'production fix' in module.CAUSAL_PAIR_AUTHORITY
    assert driver.NODE.endswith('test_actual_public_correction_three_workers_and_saved_completion')
