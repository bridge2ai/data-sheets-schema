"""Offline E1 causal tests; no scientific approval, calibration or provider calls.

Use real registered generation capture, released instrument challenges and
semantic evidence validation; mock only the external evaluator process.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import agent_pin, shared_generation as shared
from data_sheets_schema.evaluation import registered_eval_runner as runner
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from tests.test_generation_manifest_identity import external
from tests.test_reference_rescore import current_record
from tests.test_shared_generation_selection import registration_for


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture(autouse=True)
def no_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "LOCK_DIR", tmp_path / ".registered_eval_locks")
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **kw: pytest.fail("network forbidden"))
    actual = subprocess.run

    def local_git_only(command, **kwargs):
        if command[0] == "git":
            return actual(command, **kwargs)
        pytest.fail(f"unmocked subprocess forbidden: {command[0]}")

    monkeypatch.setattr(subprocess, "run", local_git_only)


@pytest.fixture(scope="module")
def registration(tmp_path_factory):
    directory = tmp_path_factory.mktemp("registered-eval")
    base = external.__wrapped__(directory)
    base = replace(base, label="concealed-v10-rep17", method="claudecode_api")
    reg = registration_for(base)
    Path(reg["registration_path"]).write_bytes(shared.canonical(reg))
    record = directory / "concealed-v10-rep17.yaml"
    record.write_text(
        "# Label: concealed-v10-rep17\n# Source: /private/secret/generation.yaml\n"
        "run_label: concealed-v10-rep17\ninput_path: /private/secret/generation.yaml\n"
        "conforms_to_class: Dataset\nid: example:dataset\nname: Fictional scientific dataset\n"
        "description: Source text must be retained exactly.\n"
        "resources:\n- id: example:child\n  name: Child dataset\n"
    )
    context = directory / "applicability.json"
    context.write_text('{"human_subjects":{"value":null,"evidence":"Synthetic unresolved predicate"}}')
    runtime = directory / "synthetic-runtime"
    runtime.write_bytes(b"synthetic runtime bytes, never executed\n")
    inputs = reg["inputs"]
    pins = [inputs[key] for key in ("bundle", "chunk_manifest", "source_manifest", "context")
            if inputs[key] is not None]
    pins.extend(inputs["full_schema"]["sources"] + inputs["core_schema"]["sources"])
    pins.extend(pin for pin in (inputs["profile"]["vocabulary"], reg["runtime"]["config"]) if pin)
    files = {pin["path"]: Path(pin["path"]).read_bytes() for pin in pins}
    files[reg["registration_path"]] = Path(reg["registration_path"]).read_bytes()
    captured = shared._capture_bytes(files[reg["registration_path"]], reg, files)
    provenance = directory / "generation-provenance.yaml"
    provenance.write_text(yaml.safe_dump({
        "record_type": "d4d_generation_provenance", "run": reg["run"],
        "shared_generation": {"authority": captured.identity()},
        "validation": {"artifacts": {"full": {
            "path": str(record), "md5": hashlib.md5(record.read_bytes()).hexdigest(),
        }}},
    }))
    return dict(
        registration=Path(reg["registration_path"]), record=record, context=context,
        context_sha256=sha(context.read_bytes()), rubric="rubric20", instrument_version="3.0",
        model="claude-opus-5", base_url=runner.CBORG_BASE_URL, runtime=runtime,
        canonical_model="claude-opus-5", context_window=1_000_000,
        runtime_sha256=sha(runtime.read_bytes()), runtime_version="2.1.269", max_cost_dollars="5",
        provenance=provenance, provenance_sha256=sha(provenance.read_bytes()),
    )


@pytest.fixture(scope="module")
def prepared(registration):
    return runner.prepare(**registration)


def document_for(prepared):
    plan = prepared.document()
    number = 10 if plan["instrument"]["rubric"] == "rubric10-semantic" else 20
    context = json.loads(prepared.context)
    doc = current_record(Path(plan["record"]["path"]), number, context)
    instrument = plan["instrument"]
    doc.update(
        version=instrument["version"], project="blinded-record", method="blinded", d4d_file="record.yaml",
    )
    doc["metadata"].update(
        instrument_sha256=instrument["definition_sha256"], instrument_kind="agent_definition",
        instrument_version=instrument["version"], rubric_sha256=instrument["rubric_sha256"],
        input_sha256=sha(prepared.blinded),
        execution_adapter_sha256=plan["execution_adapter"]["sha256"],
        effective_system_sha256=plan["execution_adapter"]["effective_system_sha256"],
    )
    doc["model"].update(name=plan["runtime"]["canonical_model"],
                        evaluator_model=plan["runtime"]["canonical_model"], temperature=None)
    if instrument["version"] == "4.0":
        selected = select_semantic_instrument("rubric20", "4.0")
        rubric = yaml.safe_load(dict(prepared.resources)[selected.rubric_path])
        q19 = rubric["d4d_evaluation_rubric"]["rubric"][18]["name"]
        for group in doc["categories"]:
            for question in group["questions"]:
                if question["id"] == 19:
                    question["name"] = q19
    return doc


def trace_for(prepared, *, cost=0.75, session="synthetic-session"):
    runtime, instrument = prepared.document()["runtime"], prepared.document()["instrument"]
    echo = agent_pin.challenge(instrument["agent"], predecessor_text=prepared.predecessor)["expected"]
    envelope = {"definition_echo": echo, "evaluation": document_for(prepared)}
    text = json.dumps(envelope)
    return [
        {"type": "system", "subtype": "init", "apiKeySource": "ANTHROPIC_API_KEY",
         "claude_code_version": runtime["version"], "model": runtime["model"], "tools": [],
         "session_id": session},
        {"type": "assistant", "session_id": session, "message": {"model": runtime["canonical_model"],
                                         "content": [{"type": "text", "text": text}]}},
        {"type": "result", "subtype": "success", "is_error": False, "result": text,
         "session_id": session, "total_cost_usd": cost,
         "modelUsage": {runtime["model"]: {"costUSD": cost, "canonicalModel": runtime["canonical_model"],
                                          "contextWindow": runtime["context_window"]}}},
    ]


def install_cli(monkeypatch, prepared, *, mutation=None, error=False, timeout=False):
    calls = []

    def fake(command, **kwargs):
        calls.append((command, kwargs))
        if timeout:
            raise subprocess.TimeoutExpired(command, 900)
        trace = trace_for(prepared, session=f"synthetic-session-{len(calls)}")
        if mutation:
            mutation(trace)
        kwargs["stdout"].write("\n".join(json.dumps(event) for event in trace) + "\n")
        kwargs["stderr"].write("synthetic stderr")
        return SimpleNamespace(returncode=1 if error else 0)

    monkeypatch.setattr(subprocess, "run", fake)
    return calls


def change_reply(events, callback):
    envelope = json.loads(events[-1]["result"])
    callback(envelope)
    events[-1]["result"] = json.dumps(envelope)
    events[1]["message"]["content"][0]["text"] = events[-1]["result"]


def test_preparation_validates_real_registration_and_separate_context(prepared, registration):
    plan = prepared.document()
    reg = json.loads(registration["registration"].read_bytes())
    assert plan["generation_registration"]["sha256"] == sha(registration["registration"].read_bytes())
    assert plan["omission_context"] == reg["inputs"]["context"]
    assert plan["applicability_context"]["sha256"] == registration["context_sha256"]
    assert plan["omission_context"]["sha256"] != plan["applicability_context"]["sha256"]
    assert plan["instrument"]["version"] == "3.0"
    assert plan["scientific_review_verified"] is False
    assert plan["generation_acceptance_verified"] is False
    assert dict(prepared.authorities)[str(registration["record"])] == prepared.original


@pytest.mark.parametrize("integrity", [None, {}, {
    "format": "d4d_latch_guard_v1", "verified": True, "assisted": True,
    "evidence_only": True, "overrides": [{"authorization": "synthetic acknowledgement"}],
    "journal": {"path": "journal.jsonl", "sha256": "a" * 64,
                "head_sha256": "b" * 64, "line_count": 1}}])
def test_d41_ineligible_record_refuses_before_rating_preparation(registration, tmp_path, integrity):
    prior = yaml.safe_load(registration["provenance"].read_bytes())
    prior["model"] = {"runtime_integrity": integrity}
    path = tmp_path / "d41-provenance.yaml"
    path.write_text(yaml.safe_dump(prior))
    with pytest.raises(ValueError, match="runtime integrity is ineligible"):
        runner.prepare(**{**registration, "provenance": path,
                          "provenance_sha256": sha(path.read_bytes())})


def test_blinding_removes_headers_without_dropping_scientific_content(prepared):
    text = runner.rating_prompt(prepared)
    assert "concealed-v10-rep17" not in text
    assert "/private/secret/generation.yaml" not in text
    assert "Source text must be retained exactly." in text
    assert yaml.safe_load(prepared.blinded)["resources"] == [{"id": "example:child", "name": "Child dataset"}]
    assert b"concealed-v10-rep17" in prepared.original
    assert "version='3.0'" in text
    assert "independent applicability context" in text
    assert "run_label" not in prepared.blinded.decode()


def test_system_adapter_resolves_procedure_without_editing_frozen_instrument(prepared):
    instrument = prepared.document()["instrument"]
    selected = select_semantic_instrument(instrument["rubric"], instrument["version"])
    assert prepared.definition == dict(prepared.resources)[selected.definition_path]
    assert sha(prepared.definition) == instrument["definition_sha256"]
    assert prepared.system_prompt == prepared.definition + b"\n\n" + runner.EXECUTION_ADAPTER.encode()
    adapter = prepared.document()["execution_adapter"]
    assert adapter["effective_system_sha256"] == sha(prepared.system_prompt)
    assert adapter["sha256"] == sha(runner.EXECUTION_ADAPTER.encode())
    assert adapter["runtime_canary_verified"] is False
    assert b"Instructions above to write a file or run a validator are delegated" in prepared.system_prompt
    assert b"do not attempt those operations or claim you ran" in prepared.system_prompt


def test_blinding_preserves_false_lists_source_paths_and_real_provenance():
    raw = (
        b"# provenance /tmp/run\nDataset:\n  label: Scientific label\n"
        b"  description: |\n    Preserve /data/files and v8 in quoted source text.\n"
        b"    # This is scientific source text, not a YAML header.\n"
        b"  provenance: actual source lineage\n  is_deidentified: false\n"
        b"  created_on: 2026-01-02\n  values: [0, false, null]\n"
    )
    clean = runner.blind_record(raw)
    parsed = yaml.safe_load(clean)["Dataset"]
    assert parsed["is_deidentified"] is False
    assert parsed["label"] == "Scientific label"
    assert parsed["values"] == [0, False, None]
    assert parsed["created_on"] == "2026-01-02"
    assert parsed["provenance"] == "actual source lineage"
    assert "# This is scientific source text" in parsed["description"]
    assert b"# provenance /tmp/run" not in clean


@pytest.mark.parametrize("raw", [
    b"name: first\nname: second\n", b"name: [unfinished\n", b"[]\n",
    b"name: .nan\n", b"1: bad-key\n", b"root: &a [*a]\n",
])
def test_ambiguous_or_unserializable_yaml_refused(raw):
    with pytest.raises(ValueError):
        runner.blind_record(raw)


def test_scientific_text_containing_run_identity_requires_review():
    with pytest.raises(ValueError, match="scientific content"):
        runner.blind_record(b"description: generated under concealed-arm7\n", forbidden=("concealed-arm7",))


def test_dry_run_has_no_runtime_credential_or_output_side_effect(prepared, tmp_path):
    out = tmp_path / "not-created"
    result = runner.execute(prepared, out, dry_run=True, environ={})
    assert result["status"] == "dry-run" and result["model_calls"] == 0
    assert result["plan_sha256"] == prepared.digest
    assert not out.exists()


def test_cli_dry_run_calls_real_preparation_without_execution(registration, tmp_path, capsys):
    args = []
    for key, value in registration.items():
        args.extend(["--" + key.replace("_", "-"), str(value)])
    output = tmp_path / "no-output"
    assert runner.main([*args, "--output", str(output), "--dry-run"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "dry-run" and result["plan"]["max_cost_dollars"] == "5"
    assert not output.exists()


@pytest.mark.parametrize("changes,match", [
    ({"instrument_version": "2.0"}, "select rubric"),
    ({"rubric": "rubric10", "instrument_version": "4.0"}, "select rubric"),
    ({"rubric": "rubric10", "repeat_count": 3}, "rubric20 only"),
    ({"repeat_count": 0}, "repeat_count"),
    ({"repeat_count": True}, "repeat_count"),
    ({"repeat_count": 101}, "repeat_count"),
    ({"max_cost_dollars": "NaN"}, "finite"),
    ({"max_cost_dollars": "-1"}, "positive"),
    ({"max_cost_dollars": True}, "positive"),
    ({"max_cost_dollars": "0.00000001", "repeat_count": 3}, "reserve"),
    ({"base_url": "https://api.anthropic.com"}, "CBORG"),
    ({"model": "opus"}, "explicit"),
    ({"model": "latest"}, "explicit"),
    ({"model": "claude-opus-5[2m]"}, "explicit"),
    ({"model": "claude-opus-5[1m]", "context_window": 200_000}, "1m mapping"),
    ({"canonical_model": "another-model"}, "1m mapping"),
    ({"context_window": True}, "positive integer"),
    ({"effort": "automatic"}, "effort"),
    ({"context_sha256": "0" * 64}, "SHA256"),
    ({"context_sha256": ""}, "SHA256"),
    ({"registration_sha256": "0" * 64}, "SHA256"),
    ({"record_sha256": "0" * 64}, "SHA256"),
    ({"runtime_sha256": "0" * 64}, "runtime SHA256"),
    ({"runtime_version": "latest"}, "exact CLI version"),
])
def test_admission_refuses_causal_selection_errors(registration, changes, match):
    with pytest.raises(ValueError, match=match):
        runner.prepare(**{**registration, **changes})


@pytest.mark.parametrize("field", ["model", "base_url", "runtime_sha256", "runtime_version",
                                  "canonical_model", "context_window"])
def test_unpinned_runtime_is_draft_only(registration, tmp_path, field):
    draft = runner.prepare(**{**registration, field: None})
    assert runner.execute(draft, tmp_path / "out", dry_run=True)["status"] == "dry-run"
    with pytest.raises(ValueError, match="explicit CBORG"):
        runner.execute(draft, tmp_path / "out", plan_sha256=draft.digest, environ={"CBORG_API_KEY": "fake"})
    assert not (tmp_path / "out").exists()


def test_unknown_context_cannot_be_substituted_for_omission_context(registration, tmp_path):
    path = tmp_path / "omission-as-applicability.json"
    path.write_text('{"format":"omission_context_v1","scopes":[]}')
    with pytest.raises(ValueError, match="unknown applicability"):
        runner.prepare(**{**registration, "context": path, "context_sha256": sha(path.read_bytes())})


def test_registration_context_hash_and_shape_are_actually_checked(registration, tmp_path):
    reg = json.loads(registration["registration"].read_bytes())
    context = tmp_path / "bad-omission.json"
    context.write_text('{"format":"omission_context_v1"}')
    reg["inputs"]["context"] = shared.file_pin(context)
    path = tmp_path / "new-registration.json"
    reg["registration_path"] = str(path)
    path.write_bytes(shared.canonical(reg))
    with pytest.raises(ValueError, match="omission_context_v1"):
        runner.prepare(**{**registration, "registration": path})
    reg["inputs"]["context"]["sha256"] = "0" * 64
    path.write_bytes(shared.canonical(reg))
    with pytest.raises(ValueError, match="SHA256"):
        runner.prepare(**{**registration, "registration": path})


def test_changed_schema_closure_is_not_a_cosmetic_registration(registration, tmp_path):
    reg = json.loads(registration["registration"].read_bytes())
    reg["inputs"]["full_schema"]["sources"].append(reg["inputs"]["bundle"])
    path = tmp_path / "incomplete-schema-registration.json"
    reg["registration_path"] = str(path)
    path.write_bytes(shared.canonical(reg))
    with pytest.raises(ValueError, match="schema closure"):
        runner.prepare(**{**registration, "registration": path})


@pytest.mark.parametrize("number,version", [(10, "3.0"), (20, "3.0"), (20, "4.0")])
def test_real_instruments_echo_and_semantic_acceptance(registration, number, version):
    selected = runner.prepare(**{**registration, "rubric": f"rubric{number}", "instrument_version": version})
    doc, cost = runner._accept(selected, trace_for(selected))
    assert doc["version"] == doc["metadata"]["instrument_version"] == version
    assert cost == runner.Decimal("0.75")
    if version == "4.0":
        assert selected.predecessor == Path(agent_pin.agent_path("d4d-rubric20-semantic")).read_text()


def test_stale_preamble_cannot_pass_by_reciting_its_hash(prepared):
    events = trace_for(prepared)
    change_reply(events, lambda e: e.update(definition_echo=prepared.preamble))
    with pytest.raises(agent_pin.StaleAgentDefinition):
        runner._accept(prepared, events)


@pytest.mark.parametrize("mutation,match", [
    (lambda e: e[0].update(apiKeySource="subscription"), "auth"),
    (lambda e: e[0].update(apiKeySource=None), "auth"),
    (lambda e: e.insert(0, deepcopy(e[0])), "auth"),
    (lambda e: e[0].update(claude_code_version="9.9.9"), "version"),
    (lambda e: e[0].update(model="unregistered"), "model/tools"),
    (lambda e: e[0].update(tools=["Read"]), "model/tools"),
    (lambda e: e[0].update(mcp_servers=[{"name": "inherited"}]), "model/tools"),
    (lambda e: e[1]["message"].update(model="unregistered"), "assistant model"),
    (lambda e: e[1].update(message=None), "assistant model"),
    (lambda e: e[1]["message"].update(content=None), "block list"),
    (lambda e: e[1]["message"]["content"][0].update(text=None), "text blocks"),
    (lambda e: e[1]["message"]["content"].append({"type": "tool_use"}), "tool call"),
    (lambda e: e[0].update(session_id=None), "session"),
    (lambda e: e[1].update(session_id="foreign"), "session"),
    (lambda e: e[-1].update(session_id="foreign"), "session"),
    (lambda e: e.insert(0, e.pop()), "chronology"),
    (lambda e: e[-1].update(is_error=True), "successful"),
    (lambda e: e[-1].update(subtype="error_max_budget_usd"), "successful"),
    (lambda e: e.append(deepcopy(e[-1])), "chronology"),
    (lambda e: e[-1].update(modelUsage={"fallback": {}}), "modelUsage"),
    (lambda e: e[-1]["modelUsage"]["claude-opus-5"].update(canonicalModel="unregistered"), "canonical"),
    (lambda e: e[-1]["modelUsage"]["claude-opus-5"].update(contextWindow=200_000), "context window"),
    (lambda e: e[-1].update(total_cost_usd=None), "cost"),
    (lambda e: e[-1].update(total_cost_usd=float("nan")), "cost"),
    (lambda e: e[-1].update(total_cost_usd=True), "cost"),
    (lambda e: e[-1].update(total_cost_usd=5.01), "reserved cap"),
    (lambda e: e[-1].update(result='{"definition_echo":"fake","evaluation":{}}'), "actual JSON"),
    (lambda e: e[-1].update(result=None), "JSON text"),
])
def test_runtime_attestation_mutations_reject(prepared, mutation, match):
    events = trace_for(prepared)
    mutation(events)
    with pytest.raises(ValueError, match=match):
        runner._accept(prepared, events)


@pytest.mark.parametrize("mutation,match", [
    (lambda d: d.update(version="4.0"), "version"),
    (lambda d: d.update(project="unblinded-project"), "project"),
    (lambda d: d["metadata"].update(instrument_version="4.0"), "instrument_version"),
    (lambda d: d["metadata"].update(input_sha256="0" * 64), "input_sha256"),
    (lambda d: d["metadata"].update(context_sha256="0" * 64), "context_sha256"),
    (lambda d: d["metadata"].update(instrument_sha256="0" * 64), "instrument_sha256"),
    (lambda d: d["metadata"].update(rubric_sha256="0" * 64), "rubric_sha256"),
    (lambda d: d["metadata"].update(evidence_authority_sha256="0" * 64), "evidence_authority_sha256"),
    (lambda d: d["metadata"].update(effective_system_sha256="0" * 64), "effective_system_sha256"),
    (lambda d: d["model"].update(name="other"), "model identity"),
    (lambda d: d.update(model=None), "model identity"),
    (lambda d: d["model"].update(temperature=0), "model identity"),
    (lambda d: d["overall_score"].update(total_points=0), "contract"),
    (lambda d: d["overall_score"].update(fixed_percentage=0), "fixed_percentage"),
    (lambda d: d["evaluation_scope"]["units"][0].update(id="another-dataset"), "resource identities"),
    (lambda d: d["categories"][0]["questions"][0]["unit_scores"][0].update(
        cited=[{"path": "/not_real", "quote": "invented"}]), "not_real"),
])
def test_score_context_identity_and_evidence_mutations_reject(prepared, mutation, match):
    events = trace_for(prepared)
    change_reply(events, lambda e: mutation(e["evaluation"]))
    with pytest.raises(ValueError, match=match):
        runner._accept(prepared, events)


def test_cborg_environment_blocks_all_inherited_alternative_routes():
    env = runner.cborg_environment({
        "PATH": "/safe/path", "HOME": "/private/real-home", "CBORG_API_KEY": "fake-key",
        "ANTHROPIC_API_KEY": "bad", "ANTHROPIC_AUTH_TOKEN": "bad",
        "ANTHROPIC_BASE_URL": "https://wrong.invalid", "CLAUDE_CODE_OAUTH_TOKEN": "subscription",
        "CLAUDE_CODE_USE_BEDROCK": "1", "CLAUDE_CODE_USE_VERTEX": "1",
        "CLAUDE_CODE_SUBAGENT_MODEL": "other", "CLAUDE_CONFIG_DIR": "/private/login",
        "HTTP_PROXY": "https://unreviewed-proxy.invalid",
    }, Path("/neutral/config"), "claude-opus-5")
    assert env["ANTHROPIC_API_KEY"] == "fake-key"
    assert env["ANTHROPIC_BASE_URL"] == runner.CBORG_BASE_URL
    assert env["HOME"] == env["CLAUDE_CONFIG_DIR"] == "/neutral/config"
    assert env["ANTHROPIC_MODEL"] == "claude-opus-5"
    assert not any(key in env for key in (
        "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "HTTP_PROXY", "CBORG_API_KEY",
        "CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
    ))


def test_missing_credentials_and_missing_plan_pin_refuse_before_writes(prepared, tmp_path):
    with pytest.raises(ValueError, match="plan SHA256"):
        runner.execute(prepared, tmp_path / "out", environ={"CBORG_API_KEY": "fake"})
    with pytest.raises(ValueError, match="CBORG_API_KEY"):
        runner.execute(prepared, tmp_path / "out", plan_sha256=prepared.digest,
                       environ={"ANTHROPIC_API_KEY": "direct", "CLAUDE_CODE_OAUTH_TOKEN": "login"})
    assert not (tmp_path / "out").exists()


def test_repeat_panel_independent_processes_reserved_aggregate_cap_and_no_overwrite(registration, tmp_path, monkeypatch):
    selected = runner.prepare(**{**registration, "repeat_count": 3})
    calls = install_cli(monkeypatch, selected)
    out = tmp_path / "run"
    receipt = runner.execute(selected, out, plan_sha256=selected.digest, environ={"CBORG_API_KEY": "fake"})
    assert receipt["status"] == "validated", receipt
    assert receipt["runtime_attempts"] == 3 and receipt["model_calls"] is None
    assert receipt["total_cost_usd"] == "2.25"
    assert receipt["cost_accounting_complete"] is True
    assert [rating["purpose"] for rating in receipt["ratings"]] == ["primary", "repeatability", "repeatability"]
    assert len({str(call[1]["cwd"]) for call in calls}) == 3
    assert len({call[1]["input"] for call in calls}) == 1
    assert (out / "original.yaml").read_bytes() == selected.original
    assert (out / "record.yaml").read_bytes() == selected.blinded
    assert (out / "effective_system.txt").read_bytes() == selected.system_prompt
    for command, kwargs in calls:
        assert command[command.index("--max-budget-usd") + 1] == "1.666666"
        assert command[command.index("--tools") + 1] == ""
        assert command[command.index("--effort") + 1] == "high"
        assert command[command.index("--system-prompt") + 1].encode() == selected.system_prompt
        assert "--strict-mcp-config" in command and "--no-session-persistence" in command
        assert "concealed-v10-rep17" not in kwargs["input"]
        assert kwargs["env"]["ANTHROPIC_BASE_URL"] == runner.CBORG_BASE_URL
        assert not kwargs["cwd"].exists()
    with pytest.raises(FileExistsError):
        runner.execute(selected, out, plan_sha256=selected.digest, environ={"CBORG_API_KEY": "fake"})
    assert len(calls) == 3


@pytest.mark.parametrize("failure", ["auth", "exit", "timeout", "overbudget", "invalidscore", "stale_echo"])
def test_failed_first_rating_is_retained_without_retries_or_fanout(registration, tmp_path, monkeypatch, failure):
    selected = runner.prepare(**{**registration, "repeat_count": 3})
    mutations = {
        "auth": lambda e: e[0].update(apiKeySource="subscription"),
        "overbudget": lambda e: e[-1].update(total_cost_usd=2),
        "invalidscore": lambda e: change_reply(e, lambda v: v["evaluation"].update(version="2.0")),
        "stale_echo": lambda e: change_reply(e, lambda v: v.update(definition_echo="wrong old definition")),
    }
    calls = install_cli(monkeypatch, selected, mutation=mutations.get(failure),
                        error=failure == "exit", timeout=failure == "timeout")
    out = tmp_path / "run"
    receipt = runner.execute(selected, out, plan_sha256=selected.digest, environ={"CBORG_API_KEY": "fake"})
    assert receipt["status"] == "incomplete", receipt
    assert len(calls) == receipt["runtime_attempts"] == 1
    assert receipt["cost_accounting_complete"] is False
    assert receipt["ratings"] == []
    assert (out / "rating-001/transcript.jsonl").exists()
    assert (out / "receipt.json").exists()
    assert not (out / "rating-001/evaluation.json").exists()
    assert not (out / "rating-002").exists()
    expected_cost = "0" if failure == "timeout" else "2" if failure == "overbudget" else "0.75"
    assert receipt["total_cost_usd"] == expected_cost
    assert receipt["attempts"][0]["status"] == "failed"


def test_changed_input_refuses_before_delivery(registration, tmp_path):
    record = tmp_path / "new-record.yaml"
    record.write_bytes(registration["record"].read_bytes())
    prior = yaml.safe_load(registration["provenance"].read_bytes())
    prior["validation"]["artifacts"]["full"]["path"] = str(record)
    provenance = tmp_path / "provenance.yaml"
    provenance.write_text(yaml.safe_dump(prior))
    selected = runner.prepare(**{**registration, "record": record, "provenance": provenance,
                                 "provenance_sha256": sha(provenance.read_bytes())})
    record.write_text("id: changed\n")
    with pytest.raises(ValueError, match="authority changed"):
        runner.execute(selected, tmp_path / "out", plan_sha256=selected.digest, environ={"CBORG_API_KEY": "fake"})
    assert not (tmp_path / "out").exists()


def test_post_delivery_drift_never_publishes_an_accepted_rating(registration, tmp_path, monkeypatch):
    context = tmp_path / "context.json"
    context.write_bytes(registration["context"].read_bytes())
    selected = runner.prepare(**{**registration, "context": context})

    def drift(_):
        context.write_text("{}")

    calls = install_cli(monkeypatch, selected, mutation=drift)
    out = tmp_path / "run"
    receipt = runner.execute(selected, out, plan_sha256=selected.digest, environ={"CBORG_API_KEY": "fake"})
    assert receipt["status"] == "incomplete" and "authority changed" in receipt["error"]
    assert len(calls) == 1
    assert not (out / "rating-001/evaluation.json").exists()


def test_changed_runtime_refuses_before_delivery(registration, tmp_path):
    runtime = tmp_path / "runtime"
    runtime.write_bytes(registration["runtime"].read_bytes())
    selected = runner.prepare(**{**registration, "runtime": runtime})
    runtime.write_text("changed binary")
    with pytest.raises(ValueError, match="runtime binary changed"):
        runner.execute(selected, tmp_path / "out", plan_sha256=selected.digest, environ={"CBORG_API_KEY": "fake"})
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("mutation,match", [
    (lambda p: p["run"].update(project="OTHER"), "another registered run"),
    (lambda p: p.update(run=None), "another registered run"),
    (lambda p: p.update(shared_generation=None), "not bound"),
    (lambda p: p.update(validation=None), "selected full/core"),
    (lambda p: p["shared_generation"]["authority"]["registration"].update(sha256="0" * 64), "not bound"),
    (lambda p: p["shared_generation"]["authority"]["registration"].update(raw_json="{}"), "not bound"),
    (lambda p: p["validation"]["artifacts"]["full"].update(md5="0" * 32), "output hash"),
    (lambda p: p["validation"]["artifacts"].pop("full"), "selected full/core"),
    (lambda p: p["validation"]["artifacts"]["full"].update(path="/another/record.yaml"), "output path"),
])
def test_record_cannot_borrow_another_run_registration(registration, tmp_path, mutation, match):
    prior = yaml.safe_load(registration["provenance"].read_bytes())
    mutation(prior)
    path = tmp_path / "wrong-provenance.yaml"
    path.write_text(yaml.safe_dump(prior))
    with pytest.raises(ValueError, match=match):
        runner.prepare(**{**registration, "provenance": path, "provenance_sha256": sha(path.read_bytes())})


def test_even_identical_record_copy_needs_its_own_output_binding(registration, tmp_path):
    path = tmp_path / "unrelated-v8.yaml"
    path.write_bytes(registration["record"].read_bytes())
    with pytest.raises(ValueError, match="output path"):
        runner.prepare(**{**registration, "record": path})


def test_result_cannot_change_scores_after_the_assistant_reply(prepared):
    events = trace_for(prepared)
    envelope = json.loads(events[-1]["result"])
    envelope["evaluation"]["overall_score"]["total_points"] = 0
    events[-1]["result"] = json.dumps(envelope)
    with pytest.raises(ValueError, match="actual JSON"):
        runner._accept(prepared, events)


@pytest.mark.parametrize("value", [True, False, None])
def test_pinned_context_preserves_false_true_and_unknown(registration, tmp_path, value):
    context = tmp_path / "context.json"
    context.write_text(json.dumps({"human_subjects": {"value": value, "evidence": "Synthetic test declaration"}}))
    selected = runner.prepare(**{**registration, "context": context, "context_sha256": sha(context.read_bytes())})
    doc, _ = runner._accept(selected, trace_for(selected))
    assert doc["applicability_context"]["human_subjects"]["value"] is value
    assert selected.document()["scientific_review_verified"] is False


def test_retained_cborg_selector_canonical_context_identity_is_supported(registration):
    # Reuse actual transport identities, not its historical score or tool use.
    # This is a compatibility regression, never a new scientific rating.
    root = Path(__file__).resolve().parents[1]
    path = root / (
        "notes/reference_rescore_2026-09-12_cborg_runtime/attempts/"
        "CHORUS_v7_rep1_r10_rating1/2026-09-12T20-15-31.516182+00-00/transcript.jsonl"
    )
    saved = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    init = next(event for event in saved if event.get("subtype") == "init")
    result = next(event for event in saved if event.get("type") == "result")
    assistant = next(event for event in saved if event.get("type") == "assistant")
    usage = result["modelUsage"][init["model"]]
    assert init["model"] == "claude-opus-5[1m]"
    assert assistant["message"]["model"] == usage["canonicalModel"] == "claude-opus-5"
    assert usage["contextWindow"] == 1_000_000
    selected = runner.prepare(**{
        **registration, "model": init["model"], "canonical_model": usage["canonicalModel"],
        "context_window": usage["contextWindow"],
    })
    events = trace_for(selected, cost=result["total_cost_usd"], session=init["session_id"])
    for key in ("model", "apiKeySource", "claude_code_version"):
        events[0][key] = init[key]
    events[1]["message"]["model"] = assistant["message"]["model"]
    events[-1]["modelUsage"] = deepcopy(result["modelUsage"])
    doc, _ = runner._accept(selected, events)
    assert doc["model"]["name"] == "claude-opus-5"
    assert selected.document()["runtime"]["model"] == "claude-opus-5[1m]"
    for field in ("canonicalModel", "contextWindow"):
        changed = deepcopy(events)
        del changed[-1]["modelUsage"][init["model"]][field]
        with pytest.raises(ValueError, match="attest"):
            runner._accept(selected, changed)


def test_auxiliary_events_do_not_break_one_session_chronology(prepared):
    events = trace_for(prepared)
    events.insert(1, {"type": "system", "subtype": "status", "status": "running"})
    assert runner._accept(prepared, events)[0]["version"] == "3.0"


def test_repeat_cannot_reuse_a_previous_session(registration, tmp_path, monkeypatch):
    selected = runner.prepare(**{**registration, "repeat_count": 3})

    def reuse(events):
        for event in events:
            event["session_id"] = "reused-session"

    calls = install_cli(monkeypatch, selected, mutation=reuse)
    receipt = runner.execute(selected, tmp_path / "run", plan_sha256=selected.digest,
                             environ={"CBORG_API_KEY": "fake"})
    assert receipt["status"] == "incomplete" and "distinct fresh sessions" in receipt["error"]
    assert len(calls) == 2 and len(receipt["ratings"]) == 1
    assert receipt["total_cost_usd"] == "1.50"


def test_reexecution_lock_refuses_without_prior_receipt_and_records_overshoot(prepared, tmp_path, monkeypatch):
    install_cli(monkeypatch, prepared)
    first_dir = tmp_path / "parent_a" / "run1"
    receipt1 = runner.execute(prepared, first_dir, plan_sha256=prepared.digest,
                              environ={"CBORG_API_KEY": "fake"})
    assert receipt1["status"] == "validated"
    assert receipt1["max_overshoot_calls"] == 1
    assert receipt1["unaccounted_reserved_usd"] == "0"

    # Different output parent directory still hits the fixed plan lock (R4 F7)
    second_dir = tmp_path / "parent_b" / "run2"
    with pytest.raises(FileExistsError, match="was already executed"):
        runner.execute(prepared, second_dir, plan_sha256=prepared.digest,
                       environ={"CBORG_API_KEY": "fake"})

    # Fake JSON with matching plan_sha256 is refused (R4 F7)
    fake_receipt = tmp_path / "fake_receipt.json"
    fake_receipt.write_text(json.dumps({"plan_sha256": prepared.digest}), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match the receipt path and sha256"):
        runner.execute(
            prepared,
            second_dir,
            plan_sha256=prepared.digest,
            environ={"CBORG_API_KEY": "fake"},
            prior_receipt=fake_receipt,
            authorization_basis="owner-reauth-test",
        )

    # Real prior receipt without authorization_basis is refused (R4 F7, D22)
    with pytest.raises(ValueError, match="requires a non-empty authorization_basis"):
        runner.execute(
            prepared,
            second_dir,
            plan_sha256=prepared.digest,
            environ={"CBORG_API_KEY": "fake"},
            prior_receipt=first_dir / "receipt.json",
        )

    receipt2 = runner.execute(
        prepared,
        second_dir,
        plan_sha256=prepared.digest,
        environ={"CBORG_API_KEY": "fake"},
        prior_receipt=first_dir / "receipt.json",
        authorization_basis="owner-reauth-test",
    )
    assert receipt2["status"] == "validated"
    assert receipt2["prior_receipt"] == str((first_dir / "receipt.json").resolve())
    assert receipt2["authorization_basis"] == "owner-reauth-test"

    # Consumed prior receipt cannot authorize a second re-run (R4 F7)
    third_dir = tmp_path / "parent_c" / "run3"
    with pytest.raises(ValueError, match="does not match the receipt path and sha256"):
        runner.execute(
            prepared,
            third_dir,
            plan_sha256=prepared.digest,
            environ={"CBORG_API_KEY": "fake"},
            prior_receipt=first_dir / "receipt.json",
            authorization_basis="owner-reauth-test-2",
        )


def test_pre_attempt_failure_still_writes_receipt_and_allows_recovery(prepared, tmp_path, monkeypatch):
    """R4 F7: failure during rating_prompt writes an incomplete receipt and updates the lock."""
    install_cli(monkeypatch, prepared)
    crash_dir = tmp_path / "crash_run"
    real_prompt = runner.rating_prompt
    monkeypatch.setattr(runner, "rating_prompt", lambda _p: (_ for _ in ()).throw(ValueError("simulated prompt failure")))
    receipt1 = runner.execute(prepared, crash_dir, plan_sha256=prepared.digest,
                              environ={"CBORG_API_KEY": "fake"})
    assert receipt1["status"] == "incomplete"
    assert "simulated prompt failure" in receipt1["error"]
    assert (crash_dir / "receipt.json").is_file()

    # Recover using the incomplete receipt written by the crashed run
    monkeypatch.setattr(runner, "rating_prompt", real_prompt)
    recover_dir = tmp_path / "recover_run"
    receipt2 = runner.execute(
        prepared,
        recover_dir,
        plan_sha256=prepared.digest,
        environ={"CBORG_API_KEY": "fake"},
        prior_receipt=crash_dir / "receipt.json",
        authorization_basis="owner-crash-recovery",
    )
    assert receipt2["status"] == "validated"


def test_timeout_records_unaccounted_reserved_usd(registration, tmp_path, monkeypatch):
    selected = runner.prepare(**{**registration, "repeat_count": 3, "max_cost_dollars": "5"})
    install_cli(monkeypatch, selected, timeout=True)
    receipt = runner.execute(selected, tmp_path / "timeout_run", plan_sha256=selected.digest,
                             environ={"CBORG_API_KEY": "fake"})
    assert receipt["status"] == "incomplete"
    assert receipt["total_cost_usd"] == "0"
    assert receipt["unaccounted_reserved_usd"] == "1.666666"


def test_lock_race_loser_does_not_overwrite_winner_lock_file(prepared, tmp_path, monkeypatch):
    """N4: a concurrent run losing the O_EXCL lock race writes its own incomplete receipt without clobbering the winner's lock."""
    install_cli(monkeypatch, prepared)
    winner_dir = tmp_path / "winner_run"
    winner_receipt = runner.execute(
        prepared,
        winner_dir,
        plan_sha256=prepared.digest,
        environ={"CBORG_API_KEY": "fake"},
    )
    assert winner_receipt["status"] == "validated"
    lock_file = Path(runner.LOCK_DIR) / f"{prepared.digest}.json"
    assert lock_file.is_file()
    winner_lock_bytes = lock_file.read_bytes()

    # Simulate a concurrent run that passed the pre-check before lock_file existed
    # and then hit FileExistsError at os.open(lock_file, O_CREAT | O_EXCL).
    orig_exists = Path.exists

    def _hide_lock_once(self: Path) -> bool:
        if self == lock_file:
            monkeypatch.setattr(Path, "exists", orig_exists)
            return False
        return orig_exists(self)

    monkeypatch.setattr(Path, "exists", _hide_lock_once)
    loser_dir = tmp_path / "loser_run"
    loser_receipt = runner.execute(
        prepared,
        loser_dir,
        plan_sha256=prepared.digest,
        environ={"CBORG_API_KEY": "fake"},
    )
    assert loser_receipt["status"] == "incomplete"
    assert "FileExistsError" in loser_receipt["error"]
    assert (loser_dir / "receipt.json").is_file()
    # Winner's lock file MUST remain intact and point to winner_dir!
    assert lock_file.read_bytes() == winner_lock_bytes


def test_default_lock_dir_uses_git_common_dir_and_is_gitignored():
    """N4: _default_lock_dir resolves via git-common-dir and .registered_eval_locks/ is in .gitignore."""
    repo_root = Path(__file__).resolve().parents[1]
    gitignore_lines = (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".registered_eval_locks/" in gitignore_lines
    resolved_lock_dir = runner._default_lock_dir(repo_root)
    assert resolved_lock_dir.name == ".registered_eval_locks"


