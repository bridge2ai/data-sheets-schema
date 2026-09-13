"""Backfill must preserve a generated run, its receipt expectation and resume."""
from dataclasses import replace
import importlib
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, provenance as pv, runs
from data_sheets_schema import snapshot_store
from data_sheets_schema.cli import cli
from tests.test_download.test_api_runner import FakeClient
from tests.test_download.test_receipt_readdress import _ReceiptFake
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.fixture
def generated(external, monkeypatch):
    selected = external.bundle.parent / "selected-for-run.yaml"
    selected.write_text(chunking.dump_manifest(chunking.build_manifest(
        external.bundle, {**chunking.DEFAULT_RULE, "max_lines": 3})))
    spec = replace(external, condition="generic_v7", chunk_manifest=selected)
    client = FakeClient()
    client.messages = _ReceiptFake(bad_slot="keywords[0]")
    # The test exercises runtime provenance, not the fake's deliberately
    # minimal D4D payload. All accounting and snapshot paths remain real.
    monkeypatch.setattr(api, "_validator_lines", lambda *args: ([], None))
    api.execute(spec, client=client)
    original = yaml.safe_load(spec.provenance_path.read_text())
    assert original["run"]["generation_id"] and original["api_usage"]
    assert original["intermediates"] and original["inputs"]["receipt_expected"]
    assert original["inputs"]["chunks"]["chunk_count"] == 4
    monkeypatch.setattr(pv, "record_path_for", lambda *args, **kwargs: spec.provenance_path)
    monkeypatch.setattr(runs, "discover", lambda: [SimpleNamespace(
        is_core=False, deterministic=False, projects=[spec.project],
        method=spec.method, label=spec.label)])
    receipt_cli = importlib.import_module("data_sheets_schema.cli.receipts")
    monkeypatch.setattr(receipt_cli, "_run_paths", lambda *args: {
        "full": spec.full_path, "core_dir": spec.core_path.parent,
        "provenance": spec.provenance_path})
    return spec


@pytest.mark.parametrize("check", ["all-evidence", "portable-snapshot", "receipt-gate", "resume"])
def test_backfill_keeps_a_real_generated_runs_evidence_and_behavior(generated, check):
    spec = generated
    original = spec.provenance_path.read_bytes()
    runner = CliRunner()
    receipt_args = ["receipts", "check", "--project", spec.project,
                    "--method", spec.method, "--label", spec.label, "--strict"]
    if check == "receipt-gate":
        api._receipt_path(spec).unlink()
        assert runner.invoke(cli, receipt_args).exit_code == 1
    result = runner.invoke(cli, ["provenance", "backfill", "--verified-label", spec.label])
    assert result.exit_code == 0, result.output
    after = yaml.safe_load(spec.provenance_path.read_text())
    if check == "portable-snapshot":
        identified, snapshot = snapshot_store.read_latest(
            spec.metadata_dir, spec.project, f"{spec.project}_full.yaml", record=after)
        assert identified and snapshot is not None
    elif check == "receipt-gate":
        result = runner.invoke(cli, receipt_args)
        assert result.exit_code == 1, result.output
        assert "this run's procedure wrote none" not in result.output
    elif check == "resume":
        client = FakeClient()
        api.execute(replace(spec), client=client)
        assert client.messages.calls == []
    assert spec.provenance_path.read_bytes() == original
