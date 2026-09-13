"""Incomplete instrument pins and malformed prompts cannot pass an audit."""
from copy import deepcopy
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner, chunking, snapshot_store, usage_ledger
from data_sheets_schema.cli.runs import runs


@pytest.fixture
def generation(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    monkeypatch.delenv("D4D_PROFILE", raising=False)
    monkeypatch.delenv("D4D_MANIFEST", raising=False)
    bundle = tmp_path / "evidence.txt"
    bundle.write_text("Synthetic clinical evidence.\n")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("projects:\n  SYNTHETIC:\n    sources: []\n")
    chunks = tmp_path / "chunks.yaml"
    chunks.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    spec = api_runner.RunSpec(project="SYNTHETIC", arm="BASELINE (input documents only)",
        method="external", label="run", condition="generic", bundle=bundle,
        manifest=manifest, chunk_manifest=chunks, profile="neutral", out_dir=tmp_path / "out")
    usage_ledger.prepare_usage(spec, resume=False)
    snapshot_store.activate(spec, fresh=True, completed=False, prior_record={})
    return spec


@pytest.mark.parametrize("block,field", [
    ("bundle", "sha256"), ("source_manifest", "sha256"), ("chunks", "sha256"),
    ("profile", "digest_md5"), ("profile", "name"),
])
@pytest.mark.parametrize("consumer", ["ledger", "phase", "snapshot"])
def test_partial_pins_refuse_drift_at_every_resume_consumer(generation, monkeypatch, block, field, consumer):
    spec = generation
    pin = deepcopy(spec.input_identity())
    current = deepcopy(pin)
    del pin[block][field]
    current[block][field] = "changed instrument identity"
    monkeypatch.setattr(spec, "input_identity", lambda: current)
    account_path = usage_ledger.ledger_path(spec)
    account = json.loads(account_path.read_text())
    account["input_identity"] = pin
    account_path.write_text(json.dumps(account))
    index_path = snapshot_store.index_path(spec.metadata_dir, spec.project)
    index = json.loads(index_path.read_text())
    index["input_identity"] = pin
    index_path.write_text(json.dumps(index))
    before = (account_path.read_bytes(), index_path.read_bytes())
    if consumer == "ledger":
        with pytest.raises(usage_ledger.UsageLedgerError, match="input identity changed"):
            usage_ledger.require_resolved(spec)
    elif consumer == "phase":
        progress = {"generation_id": account["generation_id"],
                    "run_identity": account["identity"], "input_identity": pin}
        assert not api_runner._generation_bound_inputs_observed(
            spec, progress, account["generation_id"], pin, current)
    else:
        with pytest.raises(usage_ledger.UsageLedgerError, match="identity"):
            snapshot_store.activate(spec, fresh=False, completed=False, prior_record={})
    assert (account_path.read_bytes(), index_path.read_bytes()) == before


def test_legacy_profile_omission_and_explicit_missing_file_hash_remain_comparable(generation):
    current = generation.input_identity()
    older = {k: v for k, v in current.items() if k != "profile"}
    assert not usage_ledger._identity_differs(older, current)
    missing_file = deepcopy(current)
    missing_file["chunks"]["sha256"] = None
    assert not usage_ledger._identity_differs(missing_file, missing_file)
    assert usage_ledger._identity_differs(missing_file, current)
    no_bundle = dict(current, bundle=None)
    assert not usage_ledger._identity_differs(no_bundle, no_bundle)
    for required in ("source_manifest", "chunks"):
        partial = {k: v for k, v in current.items() if k != required}
        assert usage_ledger._identity_differs(partial, current)


@pytest.mark.parametrize("has_good", [False, True])
@pytest.mark.parametrize("prompts,field", [
    ("text", "prompts"), (["text"], "prompts"),
    ("text", "schema"), (["text"], "schema"),
    ({"request": "text"}, "prompts.request"),
    ({"request": {"spec": ["text"]}}, "prompts.request.spec"),
])
def test_strict_check_reports_malformed_prompts_and_continues(tmp_path, monkeypatch, prompts, field, has_good):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("D4D_PROFILE", raising=False)
    records = [("2000-01-01_bad", prompts)]
    if has_good:
        records.append(("2000-01-02_good", None))
    for label, value in records:
        full = Path("data/d4d_concatenated/external") / label / "SYNTHETIC_d4d.yaml"
        core = Path("data/d4d_concatenated/external_core") / label / "SYNTHETIC_d4d_core.yaml"
        full.parent.mkdir(parents=True)
        core.parent.mkdir(parents=True)
        for path in (full, core):
            path.write_text("id: https://example.org/synthetic\n")
        core.with_name("SYNTHETIC_reconciliation.md").write_text("Synthetic report.\n")
        core.with_name("SYNTHETIC_provenance.yaml").write_text(yaml.safe_dump({
            "record_mode": "reconstructed", ("schema" if field == "schema" else "prompts"): value,
            "run": {"project": "SYNTHETIC", "method": "external", "label": label}}))
    result = CliRunner().invoke(runs, ["check", "--strict", "--method", "external"])
    assert result.exit_code == 1, (result.output, result.exception)
    assert isinstance(result.exception, SystemExit), repr(result.exception)
    assert "malformed" in result.output and field in result.output
    assert "2000-01-01_bad/SYNTHETIC" in result.output
    assert f"{int(has_good)} run(s) checked" in result.output

