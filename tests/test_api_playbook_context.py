"""Offline contracts for the separate API playbook instruction axis (#4014)."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, api_playbook as policy
from data_sheets_schema import prompt_registry, resources, runs
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external, snapshot
from tests.test_download.test_api_runner import FakeClient


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("network is forbidden in API playbook tests")
    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 1)


@pytest.mark.parametrize("condition", list(api.CONDITION_PROMPTS))
def test_actual_requests_deliver_policy_and_keep_selected_rules(external, condition):
    spec = replace(external, condition=condition, api_playbook_version=1)
    original = replace(external, condition=condition)
    raw = api.prompt_body(spec.base_prompt)
    rules = raw[raw.index("UNIFORM DECISION RULES —"):raw.index("RETURN:")].strip()
    instruction = spec.instruction
    assert rules in instruction
    assert policy.policy_text() in instruction
    assert instruction.count("## API factual and phase policy v1") == 1
    for unavailable in ("READ FIRST", ".claude/", "poetry run", "VALIDATE both files",
                        "OUTPUTS —", "CORE HEADER BLOCK", "RETURN: full slot count",
                        "Generation Method: schema-grounded agentic", "four-phase project agent"):
        assert unavailable not in instruction
    assert "schema-grounded API, full generation" in instruction
    if condition == "tuned":
        assert "API phase controller, tuned prompt" in instruction
    carry = {"Completed full record": "id: x\ndescription: Bundle-grounded draft\n"}
    for phase in ("full", "audit", "reconcile_full", "report"):
        old = api.build_phase(original, phase, carry=carry)
        request = api.build_phase(spec, phase, carry=carry)
        assert request.system == old.system
        assert request.cached_blocks == old.cached_blocks
        blocks = request.messages[0]["content"]
        texts = [block["text"] for block in blocks]
        assert instruction in texts
        assert texts[-1] == old.messages[0]["content"][-1]["text"]
        assert api.phase_instruction(phase, 8) in texts[-1]
        assert "Bundle-grounded draft" in "\n".join(texts[:-1])


def test_template_adaptation_never_scrubs_tuned_evidence(external, tmp_path, monkeypatch):
    components = tmp_path / "components"
    components.mkdir()
    evidence = "A source quotes `RETURN:` and `.claude/commands/example.md`; preserve evidence text."
    (components / f"{external.project}.md").write_text(evidence)
    monkeypatch.setattr(api, "COMPONENTS", components)
    spec = replace(external, condition="tuned", api_playbook_version=1)
    assert evidence in spec.instruction
    assert "PROJECT-SPECIFIC EVIDENCE" in spec.instruction
    assert "# Mode: API phase controller, tuned prompt" in spec.instruction


@pytest.mark.parametrize("value", [True, False, None, "1", 1.0, -1, 2])
def test_version_is_an_exact_closed_integer(external, value):
    with pytest.raises(ValueError, match="api_playbook_version"):
        replace(external, api_playbook_version=value)


@pytest.mark.parametrize("runtime,renderer", [("Claude Code", 8), ("Codex CLI", 8),
    ("Claude Code (direct)", 7), (api.RUNTIME, 1), (api.RUNTIME, 7),
    (api.RUNTIME, 9), (api.RUNTIME, 19), (api.RUNTIME, 23)])
def test_unsupported_combinations_refuse_before_execution(external, runtime, renderer):
    with pytest.raises(ValueError, match="only API renderer 8"):
        replace(external, runtime=runtime, render_version=renderer, api_playbook_version=1)


def test_spec_replay_pin_and_default_identity(external):
    assert "api_playbook_version" not in external.render_spec()
    assert replace(external, api_playbook_version=0).instruction == external.instruction
    spec = replace(external, api_playbook_version=1)
    recorded = spec.render_spec()
    assert recorded["api_playbook_version"] == 1
    assert recorded["api_playbook_sha256"] == policy.POLICY_SHA256
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project,
                                        method=spec.method, label=spec.label)
    assert replay.render_spec() == recorded
    assert replay.instruction == spec.instruction
    assert spec.input_identity() != external.input_identity()
    assert policy.POLICY_PATH in spec.prompt_files
    assert policy.POLICY_PATH not in external.prompt_files
    assert policy.POLICY_PATH in prompt_registry.prompt_files()
    assert prompt_registry.disk_status(policy.POLICY_PATH)[0] == prompt_registry.CANONICAL


@pytest.mark.parametrize("change", [{"api_playbook_sha256": "0" * 64},
    {"api_playbook_sha256": None}, {"api_playbook_version": 0},
    {"api_playbook_version": False}, {"api_playbook_version": 2}])
def test_malformed_recorded_policy_cannot_replay(external, change):
    recorded = replace(external, api_playbook_version=1).render_spec() | change
    with pytest.raises(ValueError, match="playbook"):
        api.RunSpec.from_render_spec(recorded, project=external.project,
                                    method=external.method, label=external.label)


def test_changed_policy_refuses_cached_plan_execution_and_replay(external, tmp_path, monkeypatch):
    spec = replace(external, api_playbook_version=1)
    saved = spec.render_spec()
    _ = spec.instruction  # Freeze instruction first: cached text cannot bypass the pin.
    altered = tmp_path / "changed-policy.md"
    altered.write_bytes(resources.resource_path(policy.POLICY_PATH).read_bytes() + b"\nchanged")
    resolve = resources.resource_path
    monkeypatch.setattr(resources, "resource_path", lambda p: altered if p == policy.POLICY_PATH else resolve(p))
    client = FakeClient()
    with pytest.raises(ValueError, match="frozen SHA256"):
        api.plan(spec)
    with pytest.raises(ValueError, match="frozen SHA256"):
        api.execute(spec, client=client, resume=False)
    with pytest.raises(ValueError, match="frozen SHA256"):
        api.RunSpec.from_render_spec(saved, project=spec.project,
                                    method=spec.method, label=spec.label).instruction
    assert client.messages.calls == []
    assert not spec.full_path.exists()


def test_new_policy_refuses_changed_registered_template_shape():
    body = api.prompt_body(api.GENERIC_PROMPT)
    for changed in (body.replace("UNIFORM DECISION RULES —", "Other rules —"),
                    body + "\nRun a new command.",
                    body.replace("RETURN:", "RETURN:\nRETURN:")):
        with pytest.raises(ValueError, match="cannot adapt"):
            policy.adapt_template(changed)


def test_executed_provenance_and_comparison_name_changed_instrument(external):
    spec = replace(external, api_playbook_version=1)
    client = FakeClient()
    api.execute(spec, client=client, resume=False)
    assert len(client.messages.calls) == 4
    assert all(policy.policy_text() in "\n".join(b["text"] for b in call["messages"][0]["content"])
               for call in client.messages.calls)
    record = yaml.safe_load(spec.provenance_path.read_text())
    request = record["prompts"]["request"]
    assert request["spec"] == spec.render_spec()
    assert request["sha256"] == hashlib.sha256(spec.instruction.encode()).hexdigest()
    files = {f["path"]: f for f in record["prompts"]["files"]}
    assert files[str(policy.POLICY_PATH)]["sha256"] == policy.POLICY_SHA256
    expected = api.assembly_digest(8, api_playbook_version=1)
    assert record["prompts"]["assembly"] == expected
    assert expected != api.assembly_digest(8)
    assert api.condition_delta(spec.condition, spec.condition,
                               api.assembly_digest(8), expected) == ["assembly"]
    facts_old = {"prefix": "old", "values": {"assembly digest": [api.assembly_digest(8)["sha256"]]}}
    facts_new = {"prefix": "new", "values": {"assembly digest": [expected["sha256"]]}}
    assert runs.arm_confounds(facts_old, facts_new)[0]["field"] == "assembly digest"
    from data_sheets_schema.provenance import record_path_for
    corpus = external.out_dir.parent / "verification-corpus"
    recorded_path = record_path_for(spec.project, spec.method, spec.label, corpus)
    recorded_path.parent.mkdir(parents=True)
    recorded_path.write_text(spec.provenance_path.read_text())
    assert runs.verify_request(spec.method, spec.label, spec.project, corpus)[0] == "match"
    # Existing agentic files must not be attested as consumed by an API runtime.
    assert record["playbooks"]["consumed"] is False


def test_changed_axis_cannot_resume_or_overwrite_prior_evidence(external):
    client = FakeClient()
    client.messages.fail_on = "audit"
    with pytest.raises(RuntimeError, match="boom"):
        api.execute(external, client=client)
    before = snapshot(external.out_dir)
    attempted = FakeClient()
    with pytest.raises(api.UsageLedgerError, match="input identity changed"):
        api.execute(replace(external, api_playbook_version=1), client=attempted)
    assert attempted.messages.calls == []
    assert snapshot(external.out_dir) == before


def args(external):
    return ["--project", external.project, "--label", external.label,
            "--condition", "generic_v6", "--bundle", str(external.bundle),
            "--manifest", str(external.manifest), "--api-playbook-version", "1"]


def test_cli_render_and_plan_use_explicit_axis(external):
    rendered = CliRunner().invoke(cli, ["api", "render-prompt", *args(external),
                                       "--runtime", api.RUNTIME])
    assert rendered.exit_code == 0, rendered.output
    assert policy.policy_text() in rendered.output
    incompatible = CliRunner().invoke(cli, ["api", "render-prompt", *args(external)])
    assert incompatible.exit_code != 0
    assert "only API renderer 8" in incompatible.output
    planned = CliRunner().invoke(cli, ["api", "plan", *args(external), "--json"])
    assert planned.exit_code == 0, planned.output
    result = json.loads(planned.output)
    assert result["api_playbook_version"] == 1
    assert str(policy.POLICY_PATH) in result["prompt_files"]


def test_cli_run_and_batch_propagate_axis_before_spend(external, monkeypatch):
    captured = []
    def execute(spec):
        captured.append(spec)
        raise RuntimeError("offline execution boundary")
    monkeypatch.setattr(api, "execute", execute)
    run = CliRunner().invoke(cli, ["api", "run", *args(external),
        "--out-dir", str(external.out_dir), "--yes"])
    assert isinstance(run.exception, RuntimeError), run.output
    assert str(run.exception) == "offline execution boundary"
    assert captured[0].api_playbook_version == 1
    original_plan = api.plan
    plans = []
    def plan(spec):
        plans.append(spec)
        return original_plan(spec)
    monkeypatch.setattr(api, "plan", plan)
    batch = CliRunner().invoke(cli, ["api", "batch", "--project-bundle",
        f"{external.project}={external.bundle}", "--manifest", str(external.manifest),
        "--label-prefix", "offline", "--condition", "generic_v6", "--replicates", "1",
        "--api-playbook-version", "1", "--dry-run"])
    assert batch.exit_code == 0, batch.output
    assert len(plans) == 1 and plans[0].api_playbook_version == 1
    assert len(captured) == 1


@pytest.mark.parametrize("renderer", [1, 8, 23])
def test_historical_replay_does_not_require_new_policy_module(external, monkeypatch, renderer):
    # Frozen support closures may include api_runner without this new opt-in
    # dependency. A default rendering must keep working in that environment.
    import builtins
    real_import = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name == "data_sheets_schema.api_playbook":
            raise ImportError("new policy module absent from historical closure")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    spec = replace(external, render_version=renderer, manifest=None,
                   manifest_line=api.RunSpec.header_for_manifest(None))
    recorded = spec.render_spec()
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project,
                                        method=spec.method, label=spec.label)
    assert replay.render_spec() == recorded
    assert replay.instruction == spec.instruction
    if renderer == 8:
        with pytest.raises(ImportError, match="historical closure"):
            replace(external, api_playbook_version=1).render_spec()
