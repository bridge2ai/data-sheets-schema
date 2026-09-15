"""API instructions must not ask an audit to undo accurate metadata (#1807)."""
from dataclasses import replace
import hashlib
import re

import pytest

from data_sheets_schema import api_runner as api
from tests.test_generation_manifest_identity import external


@pytest.mark.parametrize("applies,temperature", [(False, 0.0), (True, 0.0), (True, 0.65)])
def test_phase_instructions_and_carried_headers_agree(external, monkeypatch, applies, temperature):
    settings = {"name": "synthetic-model", "temperature": temperature,
                "temperature_applies": applies, "effort": "high"}
    monkeypatch.setattr(api, "_model_settings", lambda: settings)
    spec = replace(external, condition="generic_v9", render_version=api.AUTO)
    assert spec.render_version == 8
    instruction = spec.instruction
    expected = str(temperature) if applies else (
        "not sent (synthetic-model rejects the parameter; the config's value did not reach the request)")
    assert re.findall(r"(?m)^[ \t]*# Temperature: (.*)$", instruction) == [expected, expected]
    assert "dataset assertions against the declared source bundle" in instruction
    assert "does not establish an effective sampling value or deterministic generation" in instruction
    carried = api.stamp_provenance_header(
        "# Model: obsolete\n# Temperature: 0.0\n# Reasoning effort: default\nid: example\n", settings)
    for phase in ("full", "audit", "reconcile_full", "report"):
        request = api.build_phase(spec, phase, carry={"Completed full record": carried})
        text = "\n".join(block["text"] for block in request.messages[0]["content"])
        # This is the real assembled request, including the carried record.
        assert set(re.findall(r"(?m)^[ \t]*# Temperature: (.*)$", text)) == {expected}
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
        method=spec.method, label=spec.label)
    assert replay.instruction == instruction


def test_renderer5_replays_the_original_api_bytes(monkeypatch):
    monkeypatch.setattr(api, "_model_settings", lambda: {
        "name": "synthetic-model", "temperature": 0.0, "temperature_applies": False})
    recorded = {"condition": "generic_v9", "arm": "baseline", "bundle": "/input/demo.txt",
        "manifest": None, "manifest_line": "# Source manifest: not used", "chunk_manifest": None,
        "run_date": "2026-09-15", "runtime": api.RUNTIME, "provider": "offline",
        "profile": "neutral", "profile_basis": "explicit", "render_version": 5}
    replay = api.RunSpec.from_render_spec(recorded, project="EXTERNAL",
        method="external_api", label="synthetic")
    assert hashlib.sha256(replay.instruction.encode()).hexdigest() == (
        "e8d3024c6cc79fa16926da0a0b9c2a4a04fced4845d820ec0c53f304b161f0eb")


def test_all_request_header_fields_use_the_writer_rules():
    text = "    # Model: obsolete\n    # Temperature: 0.0\n    # Reasoning effort: default\n"
    settings = {"name": "synthetic-model", "temperature": 0.65,
                "temperature_applies": True, "effort": "high"}
    rendered = api.api_header_instructions(text, api.request_header_values(settings))
    assert rendered.startswith("    # Model: synthetic-model\n    # Temperature: 0.65\n"
                               "    # Reasoning effort: high\n")


def test_replay_does_not_read_changed_live_request_settings(external, monkeypatch):
    settings = {"name": "synthetic-model", "temperature": 0.65,
                "temperature_applies": True, "effort": "high"}
    monkeypatch.setattr(api, "_model_settings", lambda: settings)
    spec = replace(external, condition="generic_v9", render_version=api.AUTO)
    original = spec.instruction
    recorded = spec.render_spec()
    assert recorded["api_header_values"]["Temperature"] == "0.65"
    assert recorded["api_header_values"]["Reasoning effort"] == "high"
    monkeypatch.setattr(api, "_model_settings", lambda: {
        "name": "another-model", "temperature": 0.2, "temperature_applies": True, "effort": "low"})
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project,
        method=spec.method, label=spec.label)
    assert replay.instruction == original
    # Reading the replay never needs even a working live configuration.
    def unavailable():
        raise AssertionError("historical replay consulted live model settings")
    monkeypatch.setattr(api, "_model_settings", unavailable)
    assert api.resolve_prompt(replay) == original
    assert replay.render_spec()["api_header_values"] == recorded["api_header_values"]


@pytest.mark.parametrize("values", [None, {}, {"Model": "x"},
    {"Model": "x", "Temperature": 0.0, "Reasoning effort": "high"},
    {"Model": "x\n# injected", "Temperature": "0.0", "Reasoning effort": "high"}])
def test_v8_replay_refuses_missing_or_malformed_settings(external, values):
    recorded = external.render_spec()
    recorded["api_header_values"] = values
    with pytest.raises(ValueError, match="recorded API header values"):
        api.RunSpec.from_render_spec(recorded, project=external.project,
            method=external.method, label=external.label)


def test_changed_request_settings_stop_before_any_model_call(external, monkeypatch):
    from tests.test_download.test_api_runner import FakeClient
    original = external.instruction
    current = api._model_settings()
    monkeypatch.setattr(api, "_model_settings", lambda: {**current, "effort": "new-effort"})
    client = FakeClient()
    with pytest.raises(ValueError, match="request settings differ"):
        api.execute(external, client=client, resume=False)
    assert client.messages.calls == []
    assert external.instruction == original
    assert not external.full_path.exists()


@pytest.mark.parametrize("temperature,effort", [(None, None), (0.65, "high")])
def test_backfill_recovers_v8_headers_from_recorded_execution(external, monkeypatch, temperature, effort):
    import yaml
    from click.testing import CliRunner
    from data_sheets_schema import provenance as pv
    from data_sheets_schema.cli import cli
    from data_sheets_schema.runs import verify_request
    settings = {"name": "recorded-model", "temperature": temperature,
                "temperature_applies": temperature is not None, "effort": effort}
    monkeypatch.setattr(api, "_model_settings", lambda: settings)
    body = external.instruction
    data = {"run": {"project": external.project, "method": external.method, "label": external.label},
            "model": {"provider": external.render_spec()["provider"], "model": "recorded-model",
                      "temperature": temperature, "reasoning_effort": effort},
            "record_generated_at": external.run_date,
            "schema": {"profile": external.profile},
            "inputs": {"bundle_path": str(external.bundle),
                       "source_manifest": {"path": str(external.manifest)},
                       "chunks": {"path": str(external.chunk_manifest)}},
            "prompts": {"request": {"sha256": hashlib.sha256(body.encode()).hexdigest()}}}
    monkeypatch.setattr(pv, "CONCAT_DIR", external.out_dir)
    path = pv.record_path_for(external.project, external.method, external.label, external.out_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))
    monkeypatch.setattr(api, "_model_settings", lambda: {
        "name": "different-model", "temperature": 0.2, "temperature_applies": True, "effort": "low"})
    result = CliRunner().invoke(cli, ["provenance", "backfill-spec", "--project", external.project,
        "--method", external.method, "--label", external.label, "--condition", external.condition,
        "--runtime", external.runtime, "--execute"])
    assert result.exit_code == 0, result.output
    recovered = yaml.safe_load(path.read_text())["prompts"]["request"]["spec"]
    assert recovered["render_version"] == 8
    assert recovered["api_header_values"] == external.render_spec()["api_header_values"]
    assert verify_request(external.method, external.label, external.project, external.out_dir) == ("match", None)
