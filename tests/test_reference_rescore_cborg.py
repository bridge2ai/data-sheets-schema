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
        "CLAUDE_CODE_SIMPLE": "1",
        "CLAUDE_CONFIG_DIR": "/inherited/config",
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
    assert all("/reference_2026-09-12_cborg_runtime/" in j["output"] for j in jobs)
    assert runner.PLAN.name == "reference_rescore_2026-09-12_cborg_runtime"
    assert all((ROOT / j["input"]).is_file() for j in jobs)


def test_execution_metadata_preserves_scoring_prompt_and_stays_outside_record():
    import json
    import reference_rescore as original

    manifest = json.loads((ROOT / "notes/reference_rescore_2026-09-12_cborg/manifest.json").read_bytes())
    manifest["transport"] = adapter.TRANSPORT
    runner = adapter.load_runner()
    for job in runner.cohort_jobs():
        prompt = runner.job_prompt(manifest, job)
        prefix = original.job_prompt(manifest, job)
        assert prompt.startswith(prefix)
        suffix = prompt[len(prefix):]
        assert prefix.rstrip().endswith("</record>")
        assert '"model.name": "claude-opus-5"' in suffix
        assert '"model.evaluator_model": "claude-opus-5"' in suffix
        assert "independently check" in suffix
        assert prompt.startswith(manifest["instruments"][job["rubric"]]["preamble"])


def test_identity_metadata_comes_from_registration_not_record_contents():
    import json

    manifest = json.loads((ROOT / "notes/reference_rescore_2026-09-12_cborg/manifest.json").read_bytes())
    manifest["transport"] = {**adapter.TRANSPORT, "runtime_model_identifier": "test-configured-identifier"}
    runner = adapter.load_runner()
    prompt = runner.job_prompt(manifest, runner.cohort_jobs()[0])
    assert '"model.name": "test-configured-identifier"' in prompt.split("Execution metadata supplied by the launcher", 1)[1]


def test_actual_launcher_preserves_write_tool_and_uses_fresh_config(tmp_path, monkeypatch):
    import os
    import subprocess

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CBORG_API_KEY", "test-cborg-key")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/inherited/config")
    monkeypatch.setenv("CLAUDE_CODE_SIMPLE", "1")
    monkeypatch.setattr(adapter.shutil, "which", lambda _: "/fake/claude")
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: adapter.TRANSPORT["runtime_version"])
    launched = {}

    def capture(executable, args, env):
        launched.update(executable=executable, args=args, env=env)
        raise SystemExit(0)

    monkeypatch.setattr(os, "execve", capture)
    with pytest.raises(SystemExit):
        adapter.route_evaluator(["--print", "--safe-mode", "--restricted", "--tools", "Read,Write,Bash"])
    assert "--bare" not in launched["args"]
    assert launched["args"][-1] == "Read,Write,Bash"
    assert "CLAUDE_CODE_SIMPLE" not in launched["env"]
    config = Path(launched["env"]["CLAUDE_CONFIG_DIR"])
    assert config.parent == tmp_path and config.is_dir()
    assert config.stat().st_mode & 0o077 == 0
    assert launched["env"]["ANTHROPIC_API_KEY"] == "test-cborg-key"
    assert launched["env"]["ANTHROPIC_BASE_URL"] == "https://api.cborg.lbl.gov"


@pytest.mark.parametrize("change", [
    {"tools": ["Bash", "Read"]},
    {"apiKeySource": "oauth"},
    {"claude_code_version": "different"},
])
def test_initialization_rejects_missing_write_or_wrong_auth_or_version(change):
    init = {"type": "system", "subtype": "init", "tools": ["Bash", "Read", "Write"],
            "apiKeySource": "ANTHROPIC_API_KEY", "claude_code_version": "2.1.269"}
    adapter.verify_runtime_transport([init])
    with pytest.raises(ValueError):
        adapter.verify_runtime_transport([{**init, **change}])
