"""Inventory actual guarded controller output; every singleton must refuse.

The set under test comes from files written by the real runner, never from
the ownership implementation. Only endpoint replies/counts are synthetic.
"""
from dataclasses import replace
from pathlib import Path
import os

import pytest

from data_sheets_schema import api_runner as api, usage_ledger as ledger, latch_journal as journal
from tests.test_download.test_api_runner import FakeClient, spec
from tests.test_d68_legacy_readonly import tree
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_source_heading_runtime_api import draft_files  # noqa: F401


def assert_singletons_refuse(selected, artifacts, tmp_path):
    assert artifacts
    # Rebuild the output layout under a fresh isolated label directory while
    # retaining the same selected identity and input files.
    for ordinal, (relative, raw) in enumerate(sorted(artifacts.items())):
        for resume in (True, False):
            root = tmp_path / f"singleton-{ordinal}-{resume}"
            root.mkdir()
            fresh = replace(selected, out_dir=root)
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            before, client = tree(root), FakeClient()
            with pytest.raises(ledger.UsageLedgerError, match="inspection only") as caught:
                api.execute(fresh, resume=resume, client=client)
            assert path.name in str(caught.value)
            assert client.messages.calls == [], relative
            assert tree(root) == before, relative


@pytest.mark.parametrize("controller", ["plain", "shared_v1", "shared_v2", "receipt_completion",
    "readdress", "removal_repair", "typed_audit", "report_regate", "after_repair"])
def test_every_emitted_artifact_alone_refuses(controller, external, tmp_path, draft_files, monkeypatch):
    from tests import test_shared_generation_runtime as shared
    from tests import test_shared_generation_selection as selection
    from tests import test_source_heading_runtime_api as routing
    from tests import test_receipt_completion_runtime as completion
    from tests.test_evidence_generation_gate import specification
    from tests.test_removal_repair import GeneratingMessages
    from data_sheets_schema import canary
    if controller == "plain":
        selected, client = external, FakeClient()
    elif controller in ("shared_v1", "typed_audit", "report_regate"):
        base = specification(tmp_path)
        selected = selection.selected_spec(base, selection.registration_for(base))
        client = shared.client(selected, bad_report=controller == "report_regate")
    elif controller == "shared_v2":
        selected = routing.selected_spec(tmp_path, draft_files)
        client = routing.client(selected)
    elif controller in ("receipt_completion", "readdress"):
        selected = replace(external, condition="generic_v8", receipt_completion_version=1,
                           receipt_completion_registration=completion.registration())
        client = completion.client(selected, bad_address=controller == "readdress")
    else:
        selected = replace(external, condition="generic", removal_repair_version=1)
        client = FakeClient()
        client.messages = GeneratingMessages(True)
    temporaries = {}
    original_replace = os.replace

    def capture_before_publication(source, target):
        path = Path(source)
        if path.is_file() and path.is_relative_to(selected.metadata_dir):
            temporaries[str(path.relative_to(selected.metadata_dir))] = path.read_bytes()
        return original_replace(source, target)

    with monkeypatch.context() as publication:
        publication.setattr(os, "replace", capture_before_publication)
        result = api.execute(selected, client=client)
    assert client.messages.calls
    phases = {row["phase"] for row in result["usage"]}
    expected = {"shared_v2": "typed_audit_integration", "typed_audit": "typed_audit_worker",
        "receipt_completion": "full_receipt_completion", "readdress": "full_readdress",
        "removal_repair": "removal_repair_full", "after_repair": "report_after_repair",
        "report_regate": "report_regate"}.get(controller, "full")
    assert expected in phases
    # execute and offline writers expose the same non-gating age field.
    import yaml
    record = yaml.safe_load(selected.provenance_path.read_bytes())
    assert result["checks"]["record_age"] == canary.checks_from_record(record)["record_age"]
    removed = {ledger.ledger_path(selected), journal.journal_path(selected),
               api._progress_path(selected), selected.provenance_path}
    artifacts = {str(p.relative_to(selected.metadata_dir)): p.read_bytes()
                 for p in selected.metadata_dir.rglob("*") if p.is_file() and p not in removed}
    artifacts.update(temporaries)
    assert_singletons_refuse(selected, artifacts, tmp_path)


def test_snapshot_index_temporary_before_publication_is_residue(tmp_path, monkeypatch):
    from data_sheets_schema import snapshot_store
    selected = spec(project="P", out_dir=tmp_path / "source")
    ledger.prepare_usage(selected, resume=True)
    observed = {}
    original = snapshot_store.os.replace
    destination = snapshot_store.index_path(selected.metadata_dir, selected.project)

    def interrupt(source, target):
        if Path(target) == destination:
            path = Path(source)
            observed[str(path.relative_to(selected.metadata_dir))] = path.read_bytes()
            raise OSError("interrupted before index publication")
        return original(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(snapshot_store.os, "replace", interrupt)
        with pytest.raises(OSError, match="before index publication"):
            snapshot_store._write(destination, {"captured": "actual atomic writer"})
    assert_singletons_refuse(selected, observed, tmp_path)


@pytest.mark.parametrize("phase", ["reconcile_full", "report", "report_regate", "report_after_repair"])
def test_context_writers_include_admitted_refused_and_collision_artifacts(tmp_path, phase):
    from tests.test_evidence_generation_gate import specification
    from tests.test_shared_generation_selection import registration_for, selected_spec
    from tests.test_shared_generation_runtime import client as shared_client
    from types import SimpleNamespace
    base = specification(tmp_path)
    selected = selected_spec(base, registration_for(base))
    ledger.prepare_usage(selected, resume=True)
    client = shared_client(selected)
    settings = api._model_settings(selected.condition)
    kwargs = dict(model=settings["name"], temperature=settings["temperature"],
                  thinking=settings.get("thinking"), effort=settings.get("effort"),
                  max_tokens=1024, system="Synthetic admission control", messages=[{
                      "role": "user", "content": [{"type": "text", "text": "Complete synthetic request"}]}])
    for _ in range(2):  # Exercise the real numeric collision writer too.
        api._admit_shared_context(selected, phase, 1, client, kwargs)
    client.messages.count_tokens = lambda **kw: SimpleNamespace(input_tokens=10**12)
    for _ in range(2):
        with pytest.raises(api.ContextNotAdmitted, match="not admitted"):
            api._admit_shared_context(selected, phase, 1, client, kwargs)
    artifacts = {str(p.relative_to(selected.metadata_dir)): p.read_bytes()
                 for p in selected.metadata_dir.rglob("*") if p.is_file()
                 and "context" in p.name}
    assert len(artifacts) == 4
    assert_singletons_refuse(selected, artifacts, tmp_path)


def test_incomplete_completion_writer_is_residue(tmp_path):
    from data_sheets_schema import receipt_completion
    selected = spec(project="P", out_dir=tmp_path / "source")
    ledger.prepare_usage(selected, resume=True)
    api._record_incomplete_stream(selected, receipt_completion.PHASE, 1, "2026-10-31T00:00:00Z",
        {"incomplete": 1, "tail": "interrupted receipt body", "events": 2,
         "usage": {"input_tokens": 1, "output_tokens": 1}}, [], max_tokens=1024)
    artifacts = {str(p.relative_to(selected.metadata_dir)): p.read_bytes()
                 for p in selected.metadata_dir.rglob("*") if p.is_file() and "incomplete_attempt" in p.name}
    assert len(artifacts) == 1
    assert_singletons_refuse(selected, artifacts, tmp_path)
