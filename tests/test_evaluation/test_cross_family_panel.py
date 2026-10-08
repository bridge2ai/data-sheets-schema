"""Offline registration fixtures; these are not scientific evaluation labels."""
import copy
import json
from pathlib import Path
import shutil

import pytest

from data_sheets_schema import cross_family_panel as panel
from data_sheets_schema.evaluation_context import context_digest
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.support_plan import sha256


ROOT = Path(__file__).resolve().parents[2]


def write_declaration(path, declaration):
    path.write_text(json.dumps(declaration, indent=2) + "\n", encoding="utf-8")


def build_fixture(tmp_path):
    """Return corpus root, mutable declaration, declaration file; no evaluation."""
    root = tmp_path / "corpus"
    root.mkdir()
    assets = set(panel.VALIDATOR_SUPPORT) | {panel.V4_PREDECESSOR}
    for rubric, version in (("rubric10", "3.0"), ("rubric20", "3.0"), ("rubric20", "4.0")):
        selected = select_semantic_instrument(rubric, version)
        assets.update([selected.rubric_path, selected.definition_path, selected.schema_path])
        if selected.evidence_authority_path:
            assets.add(selected.evidence_authority_path)
    for asset in assets:
        target = root / asset
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / asset).read_bytes())
    (root / "record.yaml").write_text("CoreDataset:\n  id: example:fixture\n  description: Synthetic fixture.\n", encoding="utf-8")
    (root / "context.yaml").write_text("human_subjects: false\n", encoding="utf-8")
    (root / "provenance.json").write_text('{"fixture": "unverified caller-supplied artifact"}\n', encoding="utf-8")

    def ref(name):
        return {"path": name, "sha256": sha256((root / name).read_bytes())}

    declaration = {
        "format": panel.DECLARATION_FORMAT, "panel_id": "fixture-panel", "predecessor_sha256": None,
        "matrix": {"projects": ["PROJECT_A"], "cohorts": ["baseline"]},
        "records": [{"record_id": "record-a", "project": "PROJECT_A", "cohort": "baseline",
                     "label": "fixture", "method": "synthetic", "replicate": 1,
                     "input": ref("record.yaml"), "provenance": ref("provenance.json"),
                     "generator": {"model": "google/claude-opus-5-high", "family": "claude"},
                     "context": {"source": ref("context.yaml"), "review_status": "pending", "review_reference": None}}],
        "instruments": [{"rubric": "rubric10", "version": "3.0"}, {"rubric": "rubric20", "version": "4.0"}],
        "slots": [{"record_id": "record-a", "rubric": rubric, "role": role,
                   "attempt_id": f"{rubric}-{role}", "model": "claude-sonnet-4-5" if role == "same_family" else "openai:gpt-5",
                   "family": "claude" if role == "same_family" else "gpt", "rater": None, "route": None}
                  for rubric in panel.RUBRICS for role in panel.ROLES],
        "decisions": {name: {"status": "pending", "reference": None} for name in panel.DECISIONS},
    }
    path = tmp_path / "declaration.json"
    write_declaration(path, declaration)
    return root, declaration, path


def test_prepare_and_relocated_recheck_pin_inputs_without_authorizing(tmp_path):
    root, declaration, path = build_fixture(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    original = path.read_bytes()
    output = tmp_path / "panel"
    result = panel.prepare_panel(path, output, root=root)
    assert result["format"] == panel.FORMAT
    assert result["execution_authorized"] is False and result["scientific_eligibility"] is False
    assert result["missing_cells"] == [] and result["missing_slots"] == []
    assert result["counts"] == {"required_cells": 1, "selected_records": 1,
                                "distinct_input_artifacts": 1, "required_slots": 4, "declared_slots": 4}
    record = result["records"][0]
    assert record["input"]["sha256"] == declaration["records"][0]["input"]["sha256"]
    assert record["provenance_association"] == "unverified_declaration"
    assert record["context"]["normalized"]["human_subjects"]["value"] is False
    assert record["context"]["review_status"] == "pending"
    assert record["evaluation_scope"] == {"collection_metadata_inherited": False, "policy": "single_dataset",
                                           "units": [{"path": "#", "id": "example:fixture"}]}
    for rubric in panel.RUBRICS:
        a, b = [slot for slot in result["slots"] if slot["rubric"] == rubric]
        assert a["binding"] == b["binding"] and a["binding_sha256"] == b["binding_sha256"]
    assert {p: p.read_bytes() for p in before} == before and path.read_bytes() == original
    moved = tmp_path / "relocated"
    output.rename(moved)
    shutil.rmtree(root)
    path.unlink()
    assert panel.recheck_panel(moved) == result


def test_missing_cells_slots_models_and_context_remain_visible(tmp_path):
    root, declaration, path = build_fixture(tmp_path)
    declaration["matrix"]["cohorts"].append("candidate")
    declaration["records"][0]["context"]["source"] = None
    declaration["slots"] = declaration["slots"][:1]
    declaration["slots"][0].update(model="unrecognized-model", family=None)
    write_declaration(path, declaration)
    result = panel.prepare_panel(path, tmp_path / "panel", root=root)
    assert result["missing_cells"] == [{"project": "PROJECT_A", "cohort": "candidate"}]
    assert len(result["missing_slots"]) == 3 and len(result["slots"]) == 4
    assert result["counts"]["required_slots"] == 4
    assert result["records"][0]["context"]["normalized"] == {}
    assert result["records"][0]["context"]["sha256"] == context_digest({})
    assert len(result["records"][0]["context"]["unknown_predicates"]) == 7
    assert all(slot["family_relation"] == "unknown" for slot in result["slots"])
    assert any(row["subject"].endswith("family_relation") for row in result["pending_decisions"])
    assert not result["execution_authorized"] and not result["scientific_eligibility"]


@pytest.mark.parametrize("version10,version20", [("2.0", "2.0"), ("3.0", "3.0"), ("3.0", "4.0")])
def test_versions_select_exact_resources_and_v4_real_predecessor(tmp_path, version10, version20):
    root, declaration, path = build_fixture(tmp_path)
    for row, version in zip(declaration["instruments"], (version10, version20)):
        row["version"] = version
    write_declaration(path, declaration)
    result = panel.prepare_panel(path, tmp_path / "panel", root=root)
    for instrument in result["instruments"]:
        selected = select_semantic_instrument(instrument["rubric"], instrument["version"])
        assets = instrument["resources"]
        assert assets["definition"]["path"] == selected.definition_path
        assert assets["schema"]["path"] == selected.schema_path
        assert (assets["evidence_authority"] is None) == (instrument["version"] == "2.0")
        if instrument["version"] == "4.0":
            assert assets["predecessor_definition"]["sha256"] == panel.V4_PREDECESSOR_SHA256
        else:
            assert assets["predecessor_definition"] is None
        assert instrument["acceptance_contract"] == (
            "historical_classification_only" if instrument["version"] == "2.0" else "current_new_output_validator")


@pytest.mark.parametrize("mutation,reason", [
    ("record_id", "duplicate record_id"), ("logical", "duplicate logical record"),
    ("slot", "duplicate rating slot"), ("attempt", "duplicate attempt_id"),
    ("family", "family differs"), ("role", "role contradicts"),
    ("version", "unsupported semantic instrument"), ("rubric", "both rubric10 and rubric20"),
    ("extra", "panel declaration requires exactly"), ("extra_slot", "rating slot requires exactly"),
    ("hash", "artifact hash differs"), ("path", "normalized relative POSIX path"),
    ("review", "context review_reference"), ("predecessor", "caller authority differs from trusted package asset"),
])
def test_invalid_declarations_refuse_before_creating_output(tmp_path, mutation, reason):
    root, declaration, path = build_fixture(tmp_path)
    if mutation in ("record_id", "logical"):
        added = copy.deepcopy(declaration["records"][0])
        if mutation == "logical":
            added["record_id"] = "another"
        declaration["records"].append(added)
    elif mutation == "slot":
        declaration["slots"].append(copy.deepcopy(declaration["slots"][0]))
    elif mutation == "attempt":
        declaration["slots"][1]["attempt_id"] = declaration["slots"][0]["attempt_id"]
    elif mutation == "family":
        declaration["slots"][0]["family"] = "gpt"
    elif mutation == "role":
        declaration["slots"][0].update(model="openai:gpt-5", family="gpt")
    elif mutation == "version":
        declaration["instruments"][0]["version"] = "4.0"
    elif mutation == "rubric":
        declaration["instruments"].pop()
    elif mutation == "extra":
        declaration["execution_authorized"] = True
    elif mutation == "extra_slot":
        declaration["slots"][0]["score"] = 1
    elif mutation == "hash":
        declaration["records"][0]["input"]["sha256"] = "0" * 64
    elif mutation == "path":
        declaration["records"][0]["input"]["path"] = "../record.yaml"
    elif mutation == "review":
        declaration["records"][0]["context"]["review_status"] = "declared_reviewed"
    elif mutation == "predecessor":
        (root / panel.V4_PREDECESSOR).write_text("Not the released predecessor.\n", encoding="utf-8")
    write_declaration(path, declaration)
    output = tmp_path / "panel"
    with pytest.raises(panel.PanelError, match=reason):
        panel.prepare_panel(path, output, root=root)
    assert not output.exists()


@pytest.mark.parametrize("document", [
    "CoreDatasetCollection:\n  resources:\n  - id: example:a\n  - id: example:b\n",
    "CoreDataset:\n  id: example:parent\n  resources:\n  - id: example:child\n",
])
def test_scope_uses_existing_collection_and_explicit_dataset_contract(tmp_path, document):
    root, declaration, path = build_fixture(tmp_path)
    (root / "record.yaml").write_text(document, encoding="utf-8")
    declaration["records"][0]["input"]["sha256"] = sha256(document.encode())
    write_declaration(path, declaration)
    scope = panel.prepare_panel(path, tmp_path / "panel", root=root)["records"][0]["evaluation_scope"]
    if document.startswith("CoreDatasetCollection"):
        assert scope["policy"] == "minimum_per_item_across_all_resource_datasets_v1"
        assert [unit["path"] for unit in scope["units"]] == ["#/resources/0", "#/resources/1"]
    else:
        assert scope["policy"] == "single_dataset" and scope["units"] == [{"path": "#", "id": "example:parent"}]
    assert scope["collection_metadata_inherited"] is False


def test_publication_size_preflight_preserves_inputs_and_no_directory(tmp_path, monkeypatch):
    root, _, path = build_fixture(tmp_path)
    baseline = tmp_path / "baseline"
    panel.prepare_panel(path, baseline, root=root)
    raw = (baseline / "panel.json").read_bytes()
    before = path.read_bytes()
    monkeypatch.setattr(panel, "MAX_PANEL_BYTES", len(raw) - 1)
    output = tmp_path / "too-small"
    with pytest.raises(panel.PanelError, match="panel output exceeds manifest byte bound"):
        panel.prepare_panel(path, output, root=root)
    assert not output.exists() and path.read_bytes() == before


def test_existing_output_is_never_replaced_and_new_nested_output_preserves_inputs(tmp_path):
    root, _, path = build_fixture(tmp_path)
    output = tmp_path / "panel"
    panel.prepare_panel(path, output, root=root)
    before = (output / "panel.json").read_bytes()
    with pytest.raises(panel.PanelError, match="already exists"):
        panel.prepare_panel(path, output, root=root)
    assert (output / "panel.json").read_bytes() == before
    inputs = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    nested = root / "nested-output"
    result = panel.prepare_panel(path, nested, root=root)
    assert panel.recheck_panel(nested) == result
    assert {p: p.read_bytes() for p in inputs} == inputs


def test_plain_corpus_needs_no_resource_copies_or_working_directory_authority(tmp_path, monkeypatch):
    root, _, path = build_fixture(tmp_path)
    for name in ("data", "src", ".claude"):
        shutil.rmtree(root / name)
    monkeypatch.chdir(root)
    result = panel.prepare_panel(path, tmp_path / "panel", root=root)
    assert result["instruments"][1]["resources"]["predecessor_definition"]["sha256"] == panel.V4_PREDECESSOR_SHA256
    assert panel.recheck_panel(tmp_path / "panel") == result


def test_empty_selection_does_not_satisfy_required_matrix(tmp_path):
    root, declaration, path = build_fixture(tmp_path)
    declaration["records"] = []
    declaration["slots"] = []
    write_declaration(path, declaration)
    result = panel.prepare_panel(path, tmp_path / "panel", root=root)
    assert result["missing_cells"] == [{"project": "PROJECT_A", "cohort": "baseline"}]
    assert result["counts"]["selected_records"] == result["counts"]["distinct_input_artifacts"] == 0
    assert result["cells"][0]["record_ids"] == []
    assert result["execution_authorized"] is False and result["scientific_eligibility"] is False


def test_returned_bindings_are_detached_and_do_not_change_recheck(tmp_path):
    root, _, path = build_fixture(tmp_path)
    output = tmp_path / "panel"
    result = panel.prepare_panel(path, output, root=root)
    saved = copy.deepcopy(result)
    result["slots"][0]["binding"]["evaluation_scope"]["units"][0]["id"] = "changed"
    result["instruments"][0]["resources"]["definition"]["sha256"] = "0" * 64
    result["limitations"].clear()
    assert result["slots"][1]["binding"]["evaluation_scope"]["units"][0]["id"] == "example:fixture"
    assert result["records"][0]["evaluation_scope"]["units"][0]["id"] == "example:fixture"
    assert panel.recheck_panel(output) == saved
