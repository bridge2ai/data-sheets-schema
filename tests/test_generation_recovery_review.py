"""Offline behavior for the round-4 continuation findings (#1408–1413)."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, chunking, provenance as pv, receipts
from data_sheets_schema import snapshot_store, usage_ledger as ledger
from data_sheets_schema.cli import cli
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("explicit", [False, True])
def test_review_and_backfill_reproduce_the_recorded_instruction(external, monkeypatch, version, explicit):
    from data_sheets_schema.review_pack import instruction_text
    from data_sheets_schema.runs import verify_request
    spec = replace(external, runtime="Claude Code", render_version=version,
                   chunk_manifest=external.chunk_manifest if explicit else None)
    body = api.resolve_prompt(spec)
    render = spec.render_spec()
    if version == 1:
        del render["render_version"]
    data = {"run": {"project": spec.project, "method": spec.method, "label": spec.label},
            "model": {"provider": render["provider"]}, "record_generated_at": spec.run_date,
            "inputs": {"bundle_path": str(spec.bundle),
                       "source_manifest": {"path": str(spec.manifest)},
                       "chunks": {"path": str(external.chunk_manifest)}},
            "prompts": {"request": {"sha256": hashlib.sha256(body.encode()).hexdigest(), "spec": render}}}
    replayed, basis = instruction_text(data, None)
    assert replayed == body and "sha256 matches" in basis
    del data["prompts"]["request"]["spec"]
    monkeypatch.setattr(pv, "CONCAT_DIR", spec.out_dir)
    path = pv.record_path_for(spec.project, spec.method, spec.label, spec.out_dir)
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data))
    result = CliRunner().invoke(cli, [
        "provenance", "backfill-spec", "--project", spec.project, "--method", spec.method,
        "--label", spec.label, "--condition", spec.condition, "--execute"])
    assert result.exit_code == 0, result.output
    assert verify_request(spec.method, spec.label, spec.project, spec.out_dir)[0] == "match"
    recovered = yaml.safe_load(path.read_text())["prompts"]["request"]["spec"]
    assert recovered["render_version"] == version
    if version == 2:
        assert recovered["chunk_manifest"] == (str(spec.chunk_manifest) if explicit else None)


def test_cli_custom_chunk_rule_reaches_request_and_provenance(external):
    result = CliRunner().invoke(cli, [
        "bundle", "chunk", "--bundle", str(external.bundle), "--max-lines", "2", "--max-bytes", "500"])
    assert result.exit_code == 0, result.output
    manifest = yaml.safe_load(external.chunk_manifest.read_text())
    assert manifest["rule"]["version"] == "2-custom" and manifest["chunk_count"] > 1
    spec = replace(external, condition="generic_v9")
    request = api.build_phase(spec, "full", carry={})
    text = "\n".join(p["text"] for p in request.cached_blocks)
    for chunk in manifest["chunks"]:
        assert chunk["id"] in text
    record = pv.build_record(spec.project, spec.method, spec.label, mode="live",
                             input_bundle=spec.bundle, input_verified=True, manifest=spec.manifest,
                             chunk_manifest=spec.chunk_manifest, concat_dir=spec.out_dir)
    assert record.data["inputs"]["chunks"]["rule"] == manifest["rule"]
    assert record.data["inputs"]["chunks"]["sha256"] == chunking.file_sha256(spec.chunk_manifest)


@pytest.mark.parametrize("flag", ["--max-lines", "--max-bytes"])
def test_chunk_cli_refuses_nonpositive_bounds_before_writing(external, flag):
    before = external.chunk_manifest.read_bytes()
    result = CliRunner().invoke(cli, ["bundle", "chunk", "--bundle", str(external.bundle), flag, "0"])
    assert result.exit_code != 0
    assert external.chunk_manifest.read_bytes() == before


def client_named(marker, fail_on=None):
    client = FakeClient()
    client.messages.fail_on = fail_on
    create = client.messages.create
    def named(**kwargs):
        result = create(**kwargs)
        for block in result.content:
            block.text = block.text.replace("title: T", f"title: {marker}")
        return result
    client.messages.create = named
    return client


def test_changed_input_restart_recovers_only_its_own_snapshots(external):
    api.execute(external, client=client_named("GENERATION_A_EVIDENCE"))
    old_record = yaml.safe_load(external.provenance_path.read_text())
    old = {entry["path"]: Path(entry["path"]).read_bytes() for entry in old_record["intermediates"]}
    old_index = snapshot_store.index_path(external.metadata_dir, external.project).read_bytes()
    external.bundle.write_text(external.bundle.read_text() + "A new cohort release.\n")
    chunking.write_manifest_for(external.bundle)
    with pytest.raises(RuntimeError, match="boom"):
        api.execute(replace(external), resume=False, client=client_named("GENERATION_B_EVIDENCE", "audit"))
    current = client_named("GENERATION_B_EVIDENCE")
    result = api.execute(replace(external), client=current)
    report_request = next(call for call in current.messages.calls
                          if any(api.PHASE_INSTRUCTIONS["report"] in part.get("text", "")
                                     for part in call["messages"][0]["content"]))
    assert "GENERATION_B_EVIDENCE" in json.dumps(report_request)
    assert "GENERATION_A_EVIDENCE" not in json.dumps(report_request)
    assert {"full", "core"} <= set(result["skipped"])
    record = yaml.safe_load(external.provenance_path.read_text())
    assert set(old).isdisjoint(entry["path"] for entry in record["intermediates"])
    assert all(Path(path).read_bytes() == body for path, body in old.items())
    archives = snapshot_store.index_path(external.metadata_dir, external.project).parent.glob(
        f"{external.project}_snapshot_index.previous-*.json")
    assert any(path.read_bytes() == old_index for path in archives)
    # An unregistered newer filename cannot replace the active phase evidence.
    stray = external.metadata_dir / "intermediate" / f"{external.project}_full_999.yaml"
    stray.write_text("id: x\ntitle: UNREGISTERED_GENERATION\n")
    phase1 = receipts.phase1_snapshot_path(api._receipt_path(external))
    assert "GENERATION_B_EVIDENCE" in phase1.read_text()
    checked = api.report_claims_block(external)
    assert checked["artifacts"]["phase1_snapshot"]["path"] == str(phase1)
    # Hash drift in the selected snapshot is refused before any further calls.
    api._save_progress(external, ["full", "core"], None)
    saved_progress = api._progress_path(external).read_bytes()
    phase1.write_text(phase1.read_text() + "\n# tampered\n")
    refused = client_named("GENERATION_B_EVIDENCE")
    assert receipts.phase1_snapshot_state(api._receipt_path(external))[0] == "unusable"
    assert api.report_claims_block(external)["checked"] is False
    with pytest.raises(ledger.UsageLedgerError, match="snapshot bytes changed"):
        api._save_progress(external, ["full", "core"], None)
    assert api._progress_path(external).read_bytes() == saved_progress
    with pytest.raises(ledger.UsageLedgerError, match="snapshot bytes changed"):
        api.execute(replace(external), client=refused)
    assert refused.messages.calls == []


def test_drift_before_receipt_readdressing_keeps_delivered_response(external):
    from tests.test_download.test_receipt_readdress import _ReceiptFake
    spec = replace(external, condition="generic_v9")
    client = FakeClient()
    client.messages = _ReceiptFake()
    create = client.messages.create
    delivered = []
    def drifting(**kwargs):
        response = create(**kwargs)
        delivered.append("".join(block.text for block in response.content))
        spec.manifest.write_text(spec.manifest.read_text() + "\n# changed during response\n")
        return response
    client.messages.create = drifting
    with pytest.raises(ledger.UsageLedgerError, match="input identity changed"):
        api.execute(spec, client=client)
    assert len(client.messages.calls) == 1
    rows = ledger.merge_usage(spec, [])
    assert len(rows) == 1 and rows[0]["phase"] == "full"
    index = json.loads(snapshot_store.index_path(spec.metadata_dir, spec.project).read_text())
    entry = next(entry for entry in index["snapshots"] if entry.get("usage_id") == rows[0]["usage_id"])
    assert Path(entry["path"]).read_text() == delivered[0]
    assert hashlib.sha256(delivered[0].encode()).hexdigest() == entry["sha256"]
    assert index["generation_id"] == ledger.generation_id(spec)
    assert not spec.full_path.exists() and not spec.provenance_path.exists()


def test_explicit_restart_preserves_an_unreadable_snapshot_index(external):
    path = snapshot_store.index_path(external.metadata_dir, external.project)
    path.parent.mkdir(parents=True)
    original = b"incomplete prior index bytes\n"
    path.write_bytes(original)
    refused = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="cannot recover generation snapshots"):
        api.execute(external, client=refused)
    assert refused.messages.calls == [] and path.read_bytes() == original
    api.execute(external, resume=False, client=FakeClient())
    assert json.loads(path.read_text())["generation_id"] == ledger.generation_id(external)
    assert any(archive.read_bytes() == original
               for archive in path.parent.glob(f"{path.stem}.previous-*.json"))


@pytest.mark.parametrize("damage", [None, "custom", "unsupported-rule", "bundle", "missing-bundle", "chunks", "missing-chunks", "sources"])
def test_registry_bundle_audit_checks_external_destinations(tmp_path, damage):
    source = tmp_path / "selected-sources"
    source.mkdir()
    (source / "overview.txt").write_text("Synthetic public cohort overview.\n" * 4)
    bundle = tmp_path / "release" / "cohort.txt"
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump({"projects": {"EXTERNAL": {
        "source_dir": str(source), "bundle": str(bundle), "sources": [
            {"id": "overview", "processed_file": "overview.txt", "source_type": "documentation"}]}}}))
    runner = CliRunner()
    made = runner.invoke(cli, ["download", "concatenate", "--manifest", str(manifest), "--project", "EXTERNAL"])
    assert made.exit_code == 0, made.output
    chunks, _ = chunking.write_manifest_for(bundle)
    if damage in ("custom", "unsupported-rule"):
        rule = {**chunking.DEFAULT_RULE, "max_lines": 2,
                "version": "2-custom" if damage == "custom" else "unknown"}
        chunking.write_manifest_for(bundle, rule)
    elif damage == "bundle":
        bundle.write_text(bundle.read_text() + "\nchanged\n")
    elif damage == "missing-bundle":
        bundle.unlink()
    elif damage == "chunks":
        chunks.write_text(chunks.read_text() + "\nchanged: true\n")
    elif damage == "missing-chunks":
        chunks.unlink()
    elif damage == "sources":
        (source / "overview.txt").unlink()
    before = {str(path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    audit = runner.invoke(cli, ["download", "audit-bundles", "--manifest", str(manifest), "--strict"])
    assert audit.exit_code == (0 if damage in (None, "custom") else 1), audit.output
    if damage in (None, "custom"):
        assert "1 derived bundle(s)" in audit.output and "1 chunk manifest(s)" in audit.output
    else:
        assert str(bundle if damage in ("bundle", "missing-bundle", "sources") else chunks) in audit.output
    assert {str(path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before
