"""Inventory actual guarded controller output; every singleton must refuse.

The set under test comes from files written by the real runner, never from
the ownership implementation. Only endpoint replies/counts are synthetic.
"""
from dataclasses import replace
from copy import copy
from pathlib import Path
import os
import json
import re

import pytest

from data_sheets_schema import api_runner as api, usage_ledger as ledger, latch_journal as journal
from tests.test_download.test_api_runner import FakeClient, spec
from tests.test_d68_legacy_readonly import tree
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_source_heading_runtime_api import draft_files  # noqa: F401


def assert_writer_completeness(selected, tmp_path):
    """Independent census of persistent writes against production output records.

    Inputs/dependencies and a sibling's namespace never count as output pins.
    Atomic temporaries are separately tested by the unchanged singleton census.
    """
    import yaml
    paths = {p for folder in {selected.metadata_dir, selected.full_path.parent,
                              selected.core_path.parent} for p in folder.rglob('*') if p.is_file()}
    bound = set()
    # Derive independently from writer destinations, not ownership helpers or
    # the file's suffix. A new writer cannot authorize itself with run_identity.
    canonical = {selected.provenance_path.resolve(), ledger.ledger_path(selected).resolve(),
        (selected.metadata_dir / 'intermediate' / f'{selected.project}_snapshot_index.json').resolve(),
        (selected.metadata_dir / f'{selected.project}_routing_completed.json').resolve()}
    archive_stems = {ledger.ledger_path(selected).resolve().with_suffix(''),
        (selected.metadata_dir / 'intermediate' / f'{selected.project}_snapshot_index').resolve()}

    def canonical_record(path):
        resolved = path.resolve()
        return resolved in canonical or any(resolved.parent == stem.parent and re.fullmatch(
            re.escape(stem.name) + r'\.previous-[0-9a-f]{32}\.json', resolved.name) for stem in archive_stems)

    def pins(value):
        if isinstance(value, dict):
            if isinstance(value.get('path'), str):
                bound.add(Path(value['path']).resolve())
            for child in value.values():
                pins(child)
        elif isinstance(value, list):
            for child in value:
                pins(child)

    for path in paths:
        if path == journal.journal_path(selected):
            bound.add(path.resolve())
            for event in journal._events(selected):
                pins(event['payload'].get('outputs', []))
            continue
        try:
            value = yaml.safe_load(path.read_bytes())
        except (ValueError, UnicodeError, yaml.YAMLError):
            continue
        if not isinstance(value, dict):
            continue
        owner = value.get('identity', value.get('run_identity', value.get('run')))
        if value.get('format') == 'source_heading_completed_v1':
            owner = value['selection']['run']
        if not isinstance(owner, dict) or any(owner.get(key) != value
                for key, value in ledger.run_identity(selected).items()):
            continue
        if not canonical_record(path):
            continue
        bound.add(path.resolve())
        for key in ('outputs', 'snapshots', 'intermediates'):
            pins(value.get(key))
        pins(value.get('validation', {}).get('artifacts'))
        pins(value.get('companions', {}).get('reasoning_log'))
        pins(value.get('receipts', {}).get('artifacts', {}).get('receipt'))
    missing = sorted(str(p) for p in paths if p.resolve() not in bound)
    (tmp_path / 'writer-census.json').write_text(json.dumps({
        'files': sorted(map(str, paths)), 'count': len(paths), 'unbound': missing}, indent=2))
    assert not missing, missing
    # Inventory-only view, never executed: rebuilding a shared RunSpec would
    # correctly reject its registration as belonging to the original label.
    # Retain the actual output directories and vary only the reader identity.
    foreign_selection = copy(selected)
    foreign_selection.label = 'writer-census-other-label'
    assert journal.owned_artifacts(foreign_selection) == []


def assert_singletons_refuse(selected, artifacts, tmp_path):
    assert artifacts
    (tmp_path / "artifact-census.json").write_text(json.dumps({
        "files": sorted(artifacts), "singletons": len(artifacts),
        "refusal_checks": 2 * len(artifacts)}, indent=2) + "\n")
    # Rebuild the output layout under a fresh isolated label directory while
    # retaining the same selected identity and input files.
    for ordinal, (relative, raw) in enumerate(sorted(artifacts.items())):
        for resume in (True, False):
            root = tmp_path / f"singleton-{ordinal}-{resume}"
            root.mkdir()
            # Keep the actual run's pinned inputs; only relocate its output
            # properties. Reconstructing registration for every singleton is
            # unnecessary: the public read-only guard precedes registration
            # checks and must refuse before either can mutate this tree.
            fresh = copy(selected)
            fresh.out_dir = root
            assert fresh.metadata_dir == root
            assert all(path.parent == root for path in
                       (fresh.full_path, fresh.core_path, fresh.report_path))
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            before, client = tree(root), FakeClient()
            with pytest.raises(ledger.UsageLedgerError, match="inspection only") as caught:
                api.execute(fresh, resume=resume, client=client)
            assert path.name in str(caught.value)
            assert client.messages.calls == [], relative
            assert tree(root) == before, relative


@pytest.mark.parametrize("controller", ["plain", "shared_v1_typed_audit_regate", "shared_v2",
    "receipt_completion_readdress", "removal_repair_after_repair"])
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
    elif controller == "shared_v1_typed_audit_regate":
        base = specification(tmp_path)
        selected = selection.selected_spec(base, selection.registration_for(base))
        client = shared.client(selected, bad_report=True)
    elif controller == "shared_v2":
        selected = routing.selected_spec(tmp_path, draft_files)
        client = routing.client(selected)
    elif controller == "receipt_completion_readdress":
        selected = replace(external, condition="generic_v8", receipt_completion_version=1,
                           receipt_completion_registration=completion.registration())
        client = completion.client(selected, mode="receipted", bad_address=True)
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
    expected = {
        "plain": {"full", "audit", "reconcile_full", "report"},
        "shared_v1_typed_audit_regate": {"full", "full_receipt_completion", "typed_audit_worker",
            "typed_audit_omission", "typed_audit_integration", "reconcile_full", "report", "report_regate"},
        "shared_v2": {"full", "typed_audit_integration", "reconcile_full", "report"},
        "receipt_completion_readdress": {"full_receipt_completion", "full_readdress"},
        "removal_repair_after_repair": {"removal_repair_full", "report_after_repair"},
    }[controller]
    assert expected <= phases
    # execute and offline writers expose the same non-gating age field.
    import yaml
    record = yaml.safe_load(selected.provenance_path.read_bytes())
    assert result["checks"]["record_age"] == canary.checks_from_record(record)["record_age"]
    assert_writer_completeness(selected, tmp_path)
    removed = {ledger.ledger_path(selected), journal.journal_path(selected),
               api._progress_path(selected), selected.provenance_path}
    artifacts = {str(p.relative_to(selected.metadata_dir)): p.read_bytes()
                 for p in selected.metadata_dir.rglob("*") if p.is_file() and p not in removed}
    artifacts.update(temporaries)
    if controller == "shared_v2":
        assert selected.project + "_routing_completed.json" in artifacts
        assert any(Path(name).name.startswith("." + selected.project + "_routing_completed.json")
                   for name in temporaries)
        assert any("_routing_request_" in name for name in artifacts)
        assert any("_routing_response" in name for name in artifacts)
    if controller == "receipt_completion_readdress":
        assert any(Path(name).name.startswith("." + selected.project + "_coverage_receipt.")
                   for name in temporaries)
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
