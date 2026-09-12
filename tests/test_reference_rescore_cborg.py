"""Offline checks of provider selection and separation from the earlier ratings."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reference_rescore_cborg", ROOT / "scripts/reference_rescore_cborg.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_provider_selection_ignores_inherited_direct_credentials():
    original = {
        "CBORG_API_KEY": "test-cborg-key",
        "ANTHROPIC_API_KEY": "test-direct-key",
        "ANTHROPIC_AUTH_TOKEN": "test-other-token",
        "ANTHROPIC_BASE_URL": "https://example.invalid",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "different-model",
        "CLAUDE_CODE_USE_VERTEX": "1",
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "CLAUDE_CODE_USE_FOUNDRY": "1",
        "CLAUDE_CODE_OAUTH_TOKEN": "test-oauth-token",
        "PATH": "/test/bin",
    }
    selected = adapter.cborg_environment(original)
    assert selected["ANTHROPIC_API_KEY"] == "test-cborg-key"
    assert selected["ANTHROPIC_BASE_URL"] == "https://api.cborg.lbl.gov"
    assert selected["PATH"] == original["PATH"]
    for name in original.keys() - {"CBORG_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "PATH"}:
        assert name not in selected
    assert original["ANTHROPIC_API_KEY"] == "test-direct-key"


def test_missing_cborg_key_never_falls_back_to_direct_provider():
    with pytest.raises(ValueError, match="no provider fallback"):
        adapter.cborg_environment({"ANTHROPIC_API_KEY": "test-direct-key"})


def test_new_provider_preserves_cohort_and_uses_new_output_locations():
    runner = adapter.load_runner()
    jobs = runner.cohort_jobs()
    assert len(jobs) == 56
    assert len({j["input"] for j in jobs}) == 24
    assert sum(j["purpose"] == "primary" for j in jobs) == 48
    assert jobs[0]["id"] == "CHORUS_v7_rep1_r10_rating1"
    assert all("/reference_2026-09-12_cborg/" in j["output"] for j in jobs)
    assert runner.PLAN.name == "reference_rescore_2026-09-12_cborg"
    assert all((ROOT / j["input"]).is_file() for j in jobs)
