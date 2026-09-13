"""Repository maintenance cannot replace unfinished API generation evidence."""
from dataclasses import replace
import json

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner as api, provenance as pv, runs, usage_ledger as ledger
from data_sheets_schema.cli import cli
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.fixture
def layout(external, tmp_path, monkeypatch):
    root = tmp_path / "corpus"
    for module in (api, pv, runs):
        monkeypatch.setattr(module, "CONCAT_DIR", root)
    discover = runs.discover
    monkeypatch.setattr(runs, "discover", lambda: discover(root))
    path_for = pv.record_path_for
    monkeypatch.setattr(pv, "record_path_for",
        lambda project, method, label, concat_dir=root: path_for(project, method, label, concat_dir))
    return replace(external, out_dir=None)


def client_for(spec, *, interrupt=False):
    client = FakeClient()
    if interrupt:
        client.messages.fail_on = "audit"
        client.messages.exc = RuntimeError("interrupted before audit")
    return client


@pytest.fixture
def interrupted(layout):
    first = client_for(layout, interrupt=True)
    with pytest.raises(RuntimeError, match="interrupted before audit"):
        api.execute(layout, client=first)
    progress = json.loads(api._progress_path(layout).read_text())
    assert set(progress["completed"]) == {"full", "core"}
    assert not layout.provenance_path.exists()
    assert len(ledger.merge_usage(layout, [])) == 1  # core is derived in this condition
    return layout


@pytest.mark.parametrize("extra", [[], ["--dry-run"], ["--verified-label", "synthetic"]])
def test_default_backfill_defers_an_unfinished_api_generation_and_resume_reuses_paid_phases(interrupted, extra):
    spec = interrupted
    progress = api._progress_path(spec).read_bytes()
    usage = ledger.ledger_path(spec).read_bytes()
    result = CliRunner().invoke(cli, ["provenance", "backfill", *extra])
    assert result.exit_code == 0, result.output
    assert "deferred" in result.output and "API" in result.output, result.output
    assert not spec.provenance_path.exists()
    assert api._progress_path(spec).read_bytes() == progress
    assert ledger.ledger_path(spec).read_bytes() == usage
    client = client_for(spec)
    completed = api.execute(replace(spec), client=client)
    assert {"full", "core"} <= set(completed["skipped"])
    assert len(client.messages.calls) == 3
    assert len(completed["usage"]) == 4


@pytest.mark.parametrize("drift", [None, "progress", "bundle", "legacy-ledger", "unbound", "progress-subset"])
def test_an_old_generationless_reconstruction_cannot_override_bound_resume_evidence(interrupted, drift):
    spec = interrupted
    reconstruction = pv.build_record(spec.project, spec.method, spec.label,
                                      mode="reconstructed", input_verified=False)
    reconstruction.write(spec.provenance_path)
    prior = yaml.safe_load(spec.provenance_path.read_bytes())
    assert not prior["run"].get("generation_id")
    assert not prior["inputs"].get("bundle_sha256")
    if drift == "progress":
        progress = json.loads(api._progress_path(spec).read_text())
        progress["input_identity"]["bundle"]["sha256"] = "0" * 64
        api._progress_path(spec).write_text(json.dumps(progress))
    elif drift == "bundle":
        spec.bundle.write_text(spec.bundle.read_text() + "Changed input\n")
    elif drift in {"legacy-ledger", "unbound"}:
        usage = json.loads(ledger.ledger_path(spec).read_text())
        del usage["input_identity"]
        ledger.ledger_path(spec).write_text(json.dumps(usage))
        if drift == "unbound":
            progress = json.loads(api._progress_path(spec).read_text())
            del progress["input_identity"]
            api._progress_path(spec).write_text(json.dumps(progress))
    elif drift == "progress-subset":
        # Optional render-spec metadata can be absent while the original
        # bundle/source-manifest/chunk file pins and instrument evidence stay
        # complete (#1749). Raw equality would fail to bind this generation
        # and adopt the reconstruction instead (#1629, #1704).
        usage = json.loads(ledger.ledger_path(spec).read_text())
        del usage["input_identity"]["instruction"]["spec"]["chunk_manifest"]
        ledger.ledger_path(spec).write_text(json.dumps(usage))
        progress = json.loads(api._progress_path(spec).read_text())
        del progress["input_identity"]["instruction"]["spec"]["chunk_manifest"]
        api._progress_path(spec).write_text(json.dumps(progress))
        # The snapshot index was written by the same run and carries the same
        # shape as its owner's pin: strip the key there too.
        for index in spec.provenance_path.parent.rglob("*.json"):
            try:
                doc = json.loads(index.read_text())
            except ValueError:
                continue
            if isinstance(doc, dict) and isinstance(doc.get("input_identity"), dict) and "snapshots" in doc:
                del doc["input_identity"]["instruction"]["spec"]["chunk_manifest"]
                index.write_text(json.dumps(doc))
    client = client_for(spec)
    if drift in {"progress", "bundle", "unbound"}:
        reason = "no recorded generation input hash" if drift == "unbound" else "input identity changed"
        with pytest.raises(ledger.UsageLedgerError, match=reason):
            api.execute(replace(spec), client=client)
        assert not client.messages.calls
        assert yaml.safe_load(spec.provenance_path.read_bytes()) == prior
    else:
        completed = api.execute(replace(spec), client=client)
        assert {"full", "core"} <= set(completed["skipped"])
        assert len(client.messages.calls) == 3
        assert len(completed["usage"]) == 4
        assert yaml.safe_load(spec.provenance_path.read_bytes())["run"]["generation_id"]


def test_backfill_does_not_publish_while_an_api_writer_holds_the_output_lock(layout):
    spec = layout
    spec.full_path.parent.mkdir(parents=True)
    spec.full_path.write_text("id: example:cohort\ntitle: Synthetic cohort\n")
    with ledger.exclusive_run(spec):
        result = CliRunner().invoke(cli, ["provenance", "backfill"])
    assert result.exit_code == 0, result.output
    assert "deferred" in result.output and "active" in result.output, result.output
    assert not spec.provenance_path.exists()
