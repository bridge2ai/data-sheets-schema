"""Manifest choices remain true from request assembly through replay (#1402–1407)."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shlex
import socket

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, chunking, provenance as pv, receipts
from data_sheets_schema import usage_ledger as ledger
from data_sheets_schema.cli import cli
from tests.test_download.test_api_runner import FakeClient


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("network is forbidden in manifest regression tests")
    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 1)


@pytest.fixture
def external(tmp_path):
    bundle = tmp_path / "cohort source.txt"
    bundle.write_text("External cohort protocol. Shared synthetic observations.\n" * 12)
    manifest = tmp_path / "source manifest.yaml"
    manifest.write_text(yaml.safe_dump({
        "projects": {"EXTERNAL": {"bundle": str(bundle), "sources": [
            {"id": "protocol", "source_type": "documentation", "priority": 1}]}},
        "naming": {"EXTERNAL": {"canonical_label": "External Cohort"}},
    }))
    chunks, _ = chunking.write_manifest_for(bundle)
    return api.RunSpec(project="EXTERNAL", arm="BASELINE (input documents only)",
                       method="custom", bundle=bundle, label="synthetic", condition="generic_v6",
                       manifest=manifest, chunk_manifest=chunks, out_dir=tmp_path / "outputs")


def snapshot(folder):
    # Includes ignored and hidden evidence; lock files are retained too.
    return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


@pytest.mark.parametrize("change", ["source-path", "source-bytes", "chunk-path", "chunk-bytes", "bundle-bytes"])
@pytest.mark.parametrize("completed", [False, True])
def test_changed_inputs_refuse_resume_without_spending_or_restamping(external, change, completed):
    first = FakeClient()
    if not completed:
        first.messages.fail_on = "audit"
        with pytest.raises(RuntimeError, match="boom"):
            api.execute(external, client=first)
        progress = json.loads(api._progress_path(external).read_text())
        assert "full" in progress["completed"]
        assert "core" in progress["completed"]
    else:
        api.execute(external, client=first)
        assert external.provenance_path.is_file()
    before = snapshot(external.out_dir)
    changed = replace(external)
    if change.endswith("path"):
        attr = "manifest" if change.startswith("source") else "chunk_manifest"
        previous = getattr(external, attr)
        other = previous.with_name("other-" + previous.name)
        other.write_bytes(previous.read_bytes())
        setattr(changed, attr, other)
    else:
        path = {"source-bytes": external.manifest, "chunk-bytes": external.chunk_manifest,
                "bundle-bytes": external.bundle}[change]
        path.write_text(path.read_text() + "\n# changed after the run\n")
    second = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="input identity changed"):
        api.execute(changed, client=second)
    assert second.messages.calls == []
    assert snapshot(external.out_dir) == before


def test_same_inputs_resume_keeps_charges_and_completed_phases(external):
    first = FakeClient()
    first.messages.fail_on = "audit"
    with pytest.raises(RuntimeError, match="boom"):
        api.execute(external, client=first)
    second = FakeClient()
    result = api.execute(replace(external), client=second)
    assert "full" in result["skipped"]
    assert len(result["usage"]) == 4
    assert result["usage"][0]["phase"] == "full"
    assert len(second.messages.calls) == 3


def test_manifest_drift_during_response_retains_charge_and_refuses_publication(external, monkeypatch):
    client = FakeClient()
    create = client.messages.create
    def mutate(**kwargs):
        response = create(**kwargs)
        external.manifest.write_text(external.manifest.read_text() + "\n# concurrent edit\n")
        return response
    monkeypatch.setattr(client.messages, "create", mutate)
    with pytest.raises(ledger.UsageLedgerError, match="input identity changed"):
        api.execute(external, client=client)
    assert len(client.messages.calls) == 1
    assert len(ledger.merge_usage(external, [])) == 1
    assert not external.provenance_path.exists()


@pytest.mark.parametrize("mode", ["command", "header", "none"])
def test_agentic_render_to_record_preserves_selected_inputs(external, tmp_path, monkeypatch, mode):
    import importlib
    command_module = importlib.import_module("data_sheets_schema.cli.provenance")
    selected = None if mode == "none" else external.manifest
    spec = replace(external, method="claudecode_agent", condition="generic_v9", manifest=selected,
                   manifest_line=api.RunSpec.__dataclass_fields__["manifest_line"].default)
    body = api.resolve_prompt(spec)
    line = next(line.strip() for line in body.splitlines() if line.strip().startswith("poetry run d4d provenance record"))
    args = shlex.split(line)[3:]
    assert args[args.index("--manifest") + 1] == ("none" if selected is None else str(selected))
    assert args[args.index("--chunk-manifest") + 1] == str(spec.chunk_manifest)
    root = tmp_path / "records"
    full = root / spec.method / spec.label / "EXTERNAL_d4d.yaml"
    full.parent.mkdir(parents=True)
    full.write_text(f"# Source bundle: {spec.bundle}\n{spec.manifest_line}\nid: https://example.org/cohort\n")
    monkeypatch.setattr(pv, "CONCAT_DIR", root)
    destination = root / "saved-provenance.yaml"
    monkeypatch.setattr(pv, "record_path_for", lambda project, method, label, *a: destination)
    monkeypatch.setattr(command_module, "_inline_checks", lambda path: None)
    if mode == "header":
        index = args.index("--manifest")
        del args[index:index + 2]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    record = yaml.safe_load(destination.read_text())
    assert record["inputs"]["source_manifest"]["path"] == (str(selected) if selected else None)
    assert record["inputs"]["chunks"]["path"] == str(spec.chunk_manifest)
    assert record["inputs"]["chunks"]["sha256"] == chunking.file_sha256(spec.chunk_manifest)


def test_historical_render_keeps_original_command_and_current_render_is_named(external):
    old = replace(external, render_version=1)
    new = replace(external, render_version=2)
    old_command = next(line for line in api.resolve_prompt(old).splitlines() if "d4d provenance record" in line)
    new_command = next(line for line in api.resolve_prompt(new).splitlines() if "d4d provenance record" in line)
    assert "--manifest" not in old_command
    assert "--manifest" in new_command
    assert old.render_spec()["render_version"] == 1
    assert new.render_spec()["render_version"] == 2


def test_noncanonical_chunk_ids_are_refused_and_cannot_be_recredited(tmp_path):
    from tests.test_receipts import BUNDLE, FULL, _receipt
    bundle = tmp_path / "cohort.txt"
    bundle.write_text(BUNDLE)
    canonical = chunking.build_manifest(bundle)
    altered = json.loads(json.dumps(canonical))
    altered["chunks"][0]["id"], altered["chunks"][1]["id"] = altered["chunks"][1]["id"], altered["chunks"][0]["id"]
    path = tmp_path / "selected.yaml"
    path.write_text(chunking.dump_manifest(altered))
    stored = {"path": str(path), "sha256": chunking.file_sha256(path),
              "rule": altered["rule"], "chunk_count": altered["chunk_count"]}
    with pytest.raises(RuntimeError, match="canonical chunk identities"):
        api.chunk_marked_bundle(bundle, path)
    assert chunking.chunks_input(bundle, canonical["bundle_md5"], manifest=path) is None
    full, receipt = tmp_path / "full.yaml", tmp_path / "receipt.yaml"
    full.write_text(yaml.safe_dump(FULL))
    receipt.write_text(yaml.safe_dump(_receipt(canonical["bundle_md5"])))
    path.write_text(chunking.dump_manifest(canonical))
    result = receipts.block_for(full, receipt, bundle, canonical["bundle_md5"], True,
                                manifest=path, record_chunks=stored)
    assert result["checked"] is False
    assert "does not reproduce inputs.chunks.sha256" in result["reason"]
    stored["sha256"] = chunking.file_sha256(path)
    path.unlink()
    recovered = receipts.block_for(full, receipt, bundle, canonical["bundle_md5"], True,
                                   manifest=path, record_chunks=stored)
    assert recovered["checked"] is True
    assert recovered["findings"] == []


@pytest.mark.parametrize("damage", ["priority", "table", "naming", "scope", "sources"])
def test_invalid_selected_context_fails_before_plan_or_call(external, damage):
    data = yaml.safe_load(external.manifest.read_text())
    if damage == "priority":
        data["projects"]["EXTERNAL"]["sources"][0]["priority"] = "first"
    elif damage == "table":
        data["source_priority"] = {1: "documentation"}
    elif damage == "naming":
        data["naming"]["EXTERNAL"]["canonical_label"] = ["not text"]
    elif damage == "scope":
        data["scope"] = {"EXTERNAL": {"referent": "cohort", "related_but_distinct": ["bad"]}}
    else:
        data["projects"]["EXTERNAL"]["sources"] = {"bad": "shape"}
    external.manifest.write_text(yaml.safe_dump(data))
    import click
    with pytest.raises(click.ClickException, match="invalid source manifest"):
        replace(external)
    # Editing after construction also fails request assembly.
    with pytest.raises(click.ClickException, match="invalid source manifest"):
        api.build_phase(external, "full", carry={})


@pytest.mark.parametrize("selected", [None, "EXTERNAL"])
@pytest.mark.parametrize("found", [False, True])
def test_canonical_gaps_follow_selected_registry(external, monkeypatch, selected, found):
    import data_sheets_schema.runs as runs
    monkeypatch.setattr(runs, "canonical_runs", lambda **kwargs: {"EXTERNAL": {}} if found else {})
    args = ["--manifest", str(external.manifest), "runs", "canonical", "--missing"]
    if selected:
        args += ["--project", selected]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert ("EXTERNAL" in result.output) is not found
    assert ("Every project" in result.output) is found
    assert "CHORUS" not in result.output


def test_changed_inputs_in_portable_record_are_refused_without_a_ledger(external):
    api.execute(external, client=FakeClient())
    ledger.ledger_path(external).unlink()
    before = external.provenance_path.read_bytes()
    alternate = external.manifest.with_name("alternate.yaml")
    alternate.write_bytes(external.manifest.read_bytes())
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="input identity changed for source_manifest"):
        api.execute(replace(external, manifest=alternate), client=client)
    assert client.messages.calls == []
    assert external.provenance_path.read_bytes() == before


def test_legacy_progress_without_input_evidence_requires_explicit_restart(external):
    path = api._progress_path(external)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"label": external.label, "completed": ["full", "core"]}))
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="no recorded generation input identity"):
        api.execute(external, client=client)
    assert client.messages.calls == []
    assert json.loads(path.read_text())["completed"] == ["full", "core"]


def test_current_and_legacy_prompt_specs_both_verify_against_their_own_hash(external):
    import data_sheets_schema.runs as runs
    for version in (1, 2):
        spec = replace(external, render_version=version)
        recorded = spec.render_spec()
        if version == 1:
            del recorded["render_version"]
        request = {"sha256": hashlib.sha256(api.resolve_prompt(spec).encode()).hexdigest(), "spec": recorded}
        record = {"prompts": {"request": request}}
        # Exercise the public record-path route so constructor compatibility is tested.
        path = pv.record_path_for(spec.project, spec.method, spec.label, external.out_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(record))
        status, detail = runs.verify_request(spec.method, spec.label, spec.project, concat_dir=external.out_dir)
        assert status == "match", detail
