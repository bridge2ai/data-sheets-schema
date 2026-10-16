"""GitHub shared-generation admission and prompt parity (#2088), entirely offline."""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, shared_generation as shared
from data_sheets_schema import evidence_assertions as evidence
from data_sheets_schema.cli import cli
from data_sheets_schema.cli import api as api_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "src/github"
BUNDLE_SPEC = importlib.util.spec_from_file_location("assistant_bundle", SCRIPT_DIR / "assistant_bundle.py")
bundle = importlib.util.module_from_spec(BUNDLE_SPEC)
sys.modules[BUNDLE_SPEC.name] = bundle
BUNDLE_SPEC.loader.exec_module(bundle)
SPEC = importlib.util.spec_from_file_location("assistant_generation", SCRIPT_DIR / "assistant_generation.py")
assistant = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assistant)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("network forbidden"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CBORG_API_KEY", raising=False)
    monkeypatch.delenv("D4D_PROFILE", raising=False)
    monkeypatch.chdir(ROOT)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout.decode().strip()


@pytest.fixture
def prepared_inputs(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    directory = source / "inputs/External"
    directory.mkdir(parents=True)
    (directory / "protocol.txt").write_text("Example source protocol. This release contains ten synthetic samples.\n")
    (directory / ".hidden.md").write_text("# Governance\nNo individual-level information is included.\n")
    git(source, "init", "-q")
    git(source, "add", "inputs")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Synthetic fixture")
    bounds = {"format": "d4d_assistant_limits_v1", "max_bundle_bytes": 100000,
        "audit_limits": {"max_paths": 96, "max_inventory_bytes": 16384, "max_workers": 16,
            "max_request_bytes": 8000000, "max_input_tokens_per_call": 180000,
            "worker_output_tokens": 4000, "omission_output_tokens": 4000, "integration_output_tokens": 4000,
            "aggregate_input_tokens": 2000000, "aggregate_output_tokens": 100000,
            "max_calls": 18, "context_limit_tokens": 200000, "context_limit_basis": "Synthetic fixture"},
        "receipt_limits": {"max_output_tokens": 4000, "max_request_bytes": 8000000,
            "context_limit_tokens": 200000, "context_limit_basis": "Synthetic fixture"}}
    limits = tmp_path / "limits.json"
    limits.write_bytes(shared.canonical(bounds))
    return {"inputs_root": str(directory.parent), "source_checkout": str(source), "dataset": "External",
        "source_commit": git(source, "rev-parse", "HEAD"), "trusted_commit": git(ROOT, "rev-parse", "HEAD"),
        "attempt_id": "12345-1", "attempt_dir": str(tmp_path / "attempt"), "provider": "cborg", "limits": str(limits)}


def selected(outputs, dataset="External"):
    capture = api_module._capture_shared_registration(outputs["registration"])
    return api_module._shared_spec(dataset, "baseline", outputs["label"], "generic_v10", None,
        outputs["output-dir"], None, None, api_module._UNSET, None, 0, 0, 0, None, capture)


def test_preparation_uses_current_api_prompt_schema_and_complete_input(prepared_inputs):
    outputs = assistant.prepare(**prepared_inputs)
    attempt = Path(outputs["attempt-dir"])
    raw = Path(outputs["registration"]).read_bytes()
    registration = shared.parse_registration(raw)
    assert registration["selection"] == shared.descriptor()
    assert registration["inputs"]["source_manifest"] is None
    assert registration["inputs"]["profile"] == {"name": "neutral", "basis": "stated by the caller", "vocabulary": None}
    assert registration["receipt"]["coverage_floor"] == {"state": "pending", "mode": "diagnostic_pilot"}
    context = json.loads(Path(registration["inputs"]["context"]["path"]).read_bytes())
    assert context["scopes"][0]["release"] is None and context["source_policy"]["priority"] == []
    manifest = json.loads(Path(outputs["input-manifest"]).read_bytes())
    assert [member["path"] for member in manifest["members"]] == [".hidden.md", "protocol.txt"]
    spec = selected(outputs)
    spec.bind_api_header_values(api._model_settings())
    shared.preflight(spec, api._model_settings())
    actual = api.build_phase(spec, "full", carry={})
    assert json.loads((attempt / "prepared_full_request.json").read_bytes()) == asdict(actual)
    assert (attempt / "rendered_instruction.txt").read_text() == spec.instruction
    assert "Shared generation rules v1" in spec.instruction
    assert "Role relationship review v1" in spec.instruction
    chunks, _ = evidence.source_chunks_from_bytes(spec.bundle.read_bytes(), spec.chunk_manifest.read_bytes())
    assert chunks
    archive = json.loads((attempt / "captured_authority/index.json").read_bytes())
    originals = {row["original_path"] for row in archive}
    for key in ("full_schema", "core_schema"):
        for pin in registration["inputs"][key]["sources"]:
            assert pin["path"] in originals
    assert set(shared.ASSET_HASHES) <= originals
    for row in archive:
        archived = (attempt / row["archive_path"]).read_bytes()
        assert shared.sha(archived) == row["sha256"] and len(archived) == row["bytes"]
    result = CliRunner().invoke(cli, ["api", "plan", "--project", "External", "--label", outputs["label"],
        "--out-dir", outputs["output-dir"], "--shared-generation-version", "1",
        "--shared-generation-registration", outputs["registration"]])
    assert result.exit_code == 0, result.output
    assert "dynamic total unavailable" in result.output


@pytest.mark.parametrize("mutation", ["changed", "untracked", "ignored", "removed", "symlink"])
def test_source_commit_is_actual_authority_including_ignored_files(prepared_inputs, mutation):
    directory = Path(prepared_inputs["inputs_root"]) / "External"
    target = directory / "protocol.txt"
    if mutation == "changed":
        target.write_text("Modified after the declared commit\n")
    elif mutation == "removed":
        target.unlink()
    elif mutation == "symlink":
        target.unlink()
        target.symlink_to(directory / ".hidden.md")
    else:
        (directory / "extra.txt").write_text("Uncommitted file\n")
        if mutation == "ignored":
            (Path(prepared_inputs["source_checkout"]) / ".git/info/exclude").write_text("extra.txt\n")
    with pytest.raises((assistant.PreparationError, bundle.PreparationError)):
        assistant.prepare(**prepared_inputs)
    assert not (Path(prepared_inputs["attempt_dir"]) / "preparation.json").exists()


@pytest.mark.parametrize("key", ["trusted_commit", "source_commit"])
def test_wrong_checkout_sha_refuses_before_attempt(prepared_inputs, key):
    prepared_inputs[key] = "a" * 40
    with pytest.raises(assistant.PreparationError, match="checkout HEAD"):
        assistant.prepare(**prepared_inputs)
    assert not Path(prepared_inputs["attempt_dir"]).exists()


def test_attempt_reuse_never_overwrites_authority(prepared_inputs):
    outputs = assistant.prepare(**prepared_inputs)
    before = Path(outputs["registration"]).read_bytes()
    with pytest.raises(assistant.PreparationError, match="must be new"):
        assistant.prepare(**prepared_inputs)
    assert Path(outputs["registration"]).read_bytes() == before


def test_changed_bundle_cannot_reach_api_plan(prepared_inputs):
    outputs = assistant.prepare(**prepared_inputs)
    registration = json.loads(Path(outputs["registration"]).read_bytes())
    Path(registration["inputs"]["bundle"]["path"]).write_text("Changed authority")
    result = CliRunner().invoke(cli, ["api", "plan", "--project", "External", "--label", outputs["label"],
        "--out-dir", outputs["output-dir"], "--shared-generation-version", "1",
        "--shared-generation-registration", outputs["registration"]])
    assert result.exit_code == 1 and "hash/size differs" in result.output


def test_embedded_file_labels_cannot_absorb_a_sibling_document(prepared_inputs):
    from data_sheets_schema import chunking
    source = Path(prepared_inputs["source_checkout"])
    directory = Path(prepared_inputs["inputs_root"]) / "External"
    documents = {
        "protocol.txt": b'FILE: internal-paper.txt\nPATH: inner/file.txt\nInternal source with CR\rLF\r\n',
        "z_crate.json": b'{"marker":"this belongs only to the crate"}\n',
        "zz_nested.txt": b'FILE: internal-paper.txt\nPATH: same/label.txt\nDistinct physical source\n',
    }
    for name, raw in documents.items():
        (directory / name).write_bytes(raw)
    git(source, "add", "inputs")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Nested source labels")
    prepared_inputs["source_commit"] = git(source, "rev-parse", "HEAD")
    outputs = assistant.prepare(**prepared_inputs)
    manifest = json.loads(Path(outputs["input-manifest"]).read_bytes())
    spec = selected(outputs)
    bundled = spec.bundle.read_bytes()
    for member in manifest["members"]:
        raw = (directory / member["path"]).read_bytes()
        assert bundled[member["content_start"]:member["content_end"]] == raw
    chunks = json.loads(spec.chunk_manifest.read_bytes())
    bodies = chunking.chunk_texts(bundled.decode(), chunks["chunks"])
    assert "".join(bodies).encode() == bundled
    reg = json.loads(Path(outputs["registration"]).read_bytes())
    scope = json.loads(Path(reg["inputs"]["context"]["path"]).read_bytes())
    origins = {row["chunk"]: row["member"] for row in scope["source_policy"]["chunk_origins"]}
    seen = set()
    for chunk, body in zip(chunks["chunks"], bodies):
        if "this belongs only to the crate" in body:
            assert chunk["source"] == '"z_crate.json"'
            assert origins[chunk["id"]] == "z_crate.json"
            seen.add("crate")
        if "Distinct physical source" in body:
            assert origins[chunk["id"]] == "zz_nested.txt"
            seen.add("nested")
    assert seen == {"crate", "nested"}


@pytest.mark.parametrize("mutation", ["duplicate", "boolean", "oversize", "zero_audit", "extra_receipt"])
def test_invalid_or_exceeded_limits_refuse(prepared_inputs, mutation):
    path = Path(prepared_inputs["limits"])
    data = json.loads(path.read_bytes())
    if mutation == "duplicate":
        path.write_bytes(path.read_bytes()[:-1] + b',"max_bundle_bytes":1}')
    else:
        if mutation == "boolean": data["max_bundle_bytes"] = True
        elif mutation == "oversize": data["max_bundle_bytes"] = 1
        elif mutation == "zero_audit": data["audit_limits"]["max_calls"] = 0
        else: data["receipt_limits"]["ignored_cap"] = 123
        path.write_bytes(shared.canonical(data))
    with pytest.raises(ValueError):
        assistant.prepare(**prepared_inputs)
    assert not (Path(prepared_inputs["attempt_dir"]) / "preparation.json").exists()


def test_provider_selection_does_not_silently_fall_back(monkeypatch):
    assert assistant.provider_selection("cborg")["key_env"] == "CBORG_API_KEY"
    with pytest.raises(assistant.PreparationError, match="missing"):
        assistant.provider_selection("cborg", require_credential=True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-secret-do-not-log")
    with pytest.raises(assistant.PreparationError, match="conflicts"):
        assistant.provider_selection("cborg")
    monkeypatch.setenv("CBORG_API_KEY", "second-synthetic-secret")
    with pytest.raises(assistant.PreparationError, match="conflicts"):
        assistant.provider_selection("anthropic")


def test_cli_emits_only_complete_success_outputs(prepared_inputs, tmp_path):
    output = tmp_path / "github-output"
    args = [part for key, value in prepared_inputs.items() for part in ("--" + key.replace("_", "-"), value)]
    assert assistant.main([*args, "--github-output", str(output)]) == 0
    assert "registration=" in output.read_text() and "label=assistant-12345-1-generic_v10" in output.read_text()
    before = output.read_bytes()
    assert assistant.main([*args, "--github-output", str(output)]) == 1
    assert output.read_bytes() == before

