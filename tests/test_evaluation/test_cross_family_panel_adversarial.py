"""Independent, synthetic controls for a closed offline panel declaration.

These fixtures are registration bookkeeping, not scientific labels or evidence
of rater independence. They never dispatch a rating or authenticate a reviewer.
"""
from copy import deepcopy
import hashlib
import json
import shutil
import socket
from types import SimpleNamespace

import pytest

from data_sheets_schema import cross_family_panel as panel
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.support_plan import canonical
from tests.test_evaluation.test_cross_family_panel import build_fixture


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def snapshot(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


@pytest.fixture
def case(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("offline panel registration attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    root, declaration, path = build_fixture(tmp_path)

    def prepare(changed=None, name="adversarial-panel"):
        path.write_bytes(canonical(declaration if changed is None else changed))
        destination = tmp_path / name
        return destination, panel.prepare_panel(path, destination, root=root)

    return SimpleNamespace(root=root, declaration=declaration, path=path,
                           prepare=prepare, tmp=tmp_path)


@pytest.mark.parametrize("mutation", ["attempt", "slot", "record_identity", "record_id", "unknown_record"])
def test_duplicate_and_unregistered_rating_selections_refused(case, mutation):
    declared = deepcopy(case.declaration)
    if mutation == "attempt":
        declared["slots"][1]["attempt_id"] = declared["slots"][0]["attempt_id"]
    elif mutation == "slot":
        duplicate = deepcopy(declared["slots"][0])
        duplicate["attempt_id"] = "apparently-new-retry"
        declared["slots"].append(duplicate)
    elif mutation in {"record_identity", "record_id"}:
        duplicate = deepcopy(declared["records"][0])
        if mutation == "record_identity":
            duplicate["record_id"] = "apparently-new-record"
        else:
            duplicate["label"] = "apparently-new-label"
            duplicate["replicate"] += 1
        declared["records"].append(duplicate)
    else:
        declared["slots"][0]["record_id"] = "outside-the-registered-roster"
    before = snapshot(case.root)
    with pytest.raises(ValueError):
        case.prepare(declared)
    assert not (case.tmp / "adversarial-panel").exists()
    # The declaration itself is caller input and is written by the fixture;
    # prepare must preserve every captured source asset.
    after = snapshot(case.root)
    for name, raw in before.items():
        if case.root / name != case.path:
            assert after[name] == raw


@pytest.mark.parametrize("mutation", ["wrong_input_hash", "unsupported_rubric_version", "unknown_field",
                                     "contradictory_generator_family", "contradictory_slot_family"])
def test_conflicting_authority_cannot_produce_a_package(case, mutation):
    declared = deepcopy(case.declaration)
    if mutation == "wrong_input_hash":
        declared["records"][0]["input"]["sha256"] = "0" * 64
    elif mutation == "unsupported_rubric_version":
        next(row for row in declared["instruments"] if row["rubric"] == "rubric10")["version"] = "4.0"
    elif mutation == "unknown_field":
        declared["execution_authorized"] = True
    elif mutation == "contradictory_generator_family":
        declared["records"][0]["generator"] = {"model": "claude-invented-fixture", "family": "gpt"}
    else:
        declared["slots"][0].update(model="gpt-invented-fixture", family="claude")
    with pytest.raises(ValueError):
        case.prepare(declared)
    assert not (case.tmp / "adversarial-panel").exists()


def test_missing_matrix_cell_and_rating_slot_remain_visible(case):
    declared = deepcopy(case.declaration)
    declared["matrix"]["projects"].append("MISSING_SYNTHETIC_PROJECT")
    removed = declared["slots"].pop()
    destination, registered = case.prepare(declared)
    assert "MISSING_SYNTHETIC_PROJECT" in json.dumps(registered["missing_cells"])
    assert len(registered["missing_slots"]) >= 1
    missing = json.dumps(registered["missing_slots"])
    assert removed["record_id"] in missing
    assert removed["rubric"] in missing
    assert removed["role"] in missing
    assert registered["execution_authorized"] is False
    assert registered["scientific_eligibility"] is False
    assert panel.recheck_panel(destination) == registered


def test_renaming_identical_input_does_not_hide_duplicate_content(case):
    declared = deepcopy(case.declaration)
    first = declared["records"][0]
    duplicate = deepcopy(first)
    duplicate.update(record_id="synthetic-duplicate-content", label=first["label"] + "-copy",
                     replicate=first["replicate"] + 1)
    declared["records"].append(duplicate)
    for slot in list(declared["slots"]):
        if slot["record_id"] == first["record_id"]:
            declared["slots"].append({**slot, "record_id": duplicate["record_id"],
                                      "attempt_id": slot["attempt_id"] + "-copy"})
    _, registered = case.prepare(declared)
    clusters = registered["duplicate_content_clusters"]
    assert clusters
    encoded = json.dumps(clusters)
    assert first["record_id"] in encoded and duplicate["record_id"] in encoded
    assert first["input"]["sha256"] in encoded
    assert registered["counts"]["selected_records"] == 2
    assert registered["counts"]["distinct_input_artifacts"] == 1
    assert len(clusters) == 1 and len(clusters[0]["record_ids"]) == 2
    assert registered["execution_authorized"] is False


def test_relocated_recheck_uses_captured_sources_only(case):
    destination, expected = case.prepare()
    relocated = case.tmp / "relocated-registration"
    shutil.copytree(destination, relocated)
    before = snapshot(relocated)
    case.root.rename(case.tmp / "original-root-preserved")
    if case.path.exists():
        case.path.rename(case.tmp / "original-declaration-preserved.json")
    destination.rename(case.tmp / "original-registration-preserved")
    assert panel.recheck_panel(relocated) == expected
    assert snapshot(relocated) == before


@pytest.mark.parametrize("field", ["execution_authorized", "scientific_eligibility", "missing_cells",
                                   "pending_decisions"])
def test_cached_readiness_and_completeness_do_not_override_declaration(case, field):
    declared = deepcopy(case.declaration)
    declared["matrix"]["projects"].append("MISSING_SYNTHETIC_PROJECT")
    destination, _ = case.prepare(declared)
    path = destination / "panel.json"
    stored = json.loads(path.read_bytes())
    if field in {"execution_authorized", "scientific_eligibility"}:
        stored[field] = True
    elif field == "missing_cells":
        stored[field] = []
    else:
        stored[field] = {} if isinstance(stored[field], dict) else []
    path.write_bytes(canonical(stored) + b"\n")
    before = snapshot(destination)
    with pytest.raises(ValueError):
        panel.recheck_panel(destination)
    assert snapshot(destination) == before


@pytest.mark.parametrize("artifact", ["record", "context", "definition", "schema"])
def test_changed_captured_authority_refused_without_reopening_original(case, artifact):
    destination, registered = case.prepare()
    if artifact == "record":
        pin = registered["records"][0]["input"]
    elif artifact == "context":
        pin = registered["records"][0]["context"]["source"]
    else:
        pin = registered["instruments"][0]["resources"][artifact]
    captured = destination / "artifacts" / pin["sha256"]
    captured.write_bytes(captured.read_bytes() + b"\n# changed captured bytes\n")
    before = snapshot(destination)
    with pytest.raises(ValueError):
        panel.recheck_panel(destination)
    assert snapshot(destination) == before


def test_missing_context_is_unknown_even_with_record_claims_and_review_reference(case):
    declared = deepcopy(case.declaration)
    record = declared["records"][0]
    source = case.root / record["input"]["path"]
    source.write_bytes(source.read_bytes() + b"  human_subjects: false\n")
    record["input"]["sha256"] = digest(source.read_bytes())
    record["context"].update(source=None, review_status="declared_reviewed",
                              review_reference="synthetic://review-of-unknown-context-declaration")
    _, registered = case.prepare(declared)
    context = registered["records"][0]["context"]
    assert context["normalized"] == {}
    assert set(context["unknown_predicates"]) == set(panel.PREDICATES)
    assert context["review_subject"] == "unknown_context_declaration"
    assert context["review_status"] == "declared_reviewed"
    assert context["approval_authenticated"] is False
    assert registered["execution_authorized"] is False
    assert registered["scientific_eligibility"] is False


def test_explicit_false_context_is_preserved_as_pending_without_becoming_approval(case):
    _, with_source = case.prepare(name="with-pending-context")
    false_context = with_source["records"][0]["context"]
    assert false_context["normalized"]["human_subjects"]["value"] is False
    assert "human_subjects" not in false_context["unknown_predicates"]
    assert false_context["review_status"] == "pending"
    assert false_context["approval_authenticated"] is False
    declared = deepcopy(case.declaration)
    declared["records"][0]["context"]["source"] = None
    _, without_source = case.prepare(declared, name="without-context")
    unknown_context = without_source["records"][0]["context"]
    assert unknown_context["normalized"] == {}
    assert false_context["sha256"] != unknown_context["sha256"]
    for registered in (with_source, without_source):
        by_rubric = {rubric: [s for s in registered["slots"] if s["rubric"] == rubric]
                     for rubric in panel.RUBRICS}
        for pair in by_rubric.values():
            assert pair[0]["binding"] == pair[1]["binding"]
        assert registered["execution_authorized"] is False
        assert registered["scientific_eligibility"] is False


def test_provenance_is_captured_unverified_and_does_not_infer_a_generator(case):
    declared = deepcopy(case.declaration)
    record = declared["records"][0]
    provenance = case.root / record["provenance"]["path"]
    provenance.write_bytes(canonical({"model": {"model": "claude-invented-fixture"},
                                     "outputs": {"full": {"path": "different-record.yaml",
                                                           "sha256": "0" * 64}}}))
    record["provenance"]["sha256"] = digest(provenance.read_bytes())
    record["generator"] = {"model": None, "family": None}
    destination, registered = case.prepare(declared)
    observed = registered["records"][0]
    assert observed["provenance_association"] == "unverified_declaration"
    assert observed["generator"] == {"model": None, "family": None}
    assert (destination / "artifacts" / record["provenance"]["sha256"]).read_bytes() == provenance.read_bytes()
    assert all(row["family_relation"] == "unknown" for row in registered["slots"])
    assert any(row["subject"].endswith(".generator") for row in registered["pending_decisions"])
    assert registered["execution_authorized"] is False
    assert registered["scientific_eligibility"] is False


def test_unknown_model_is_not_silently_classified_as_an_independent_family(case):
    declared = deepcopy(case.declaration)
    selected = next(slot for slot in declared["slots"] if slot["role"] == "cross_family")
    selected.update(model="unrecognized-provider-model", family=None)
    _, registered = case.prepare(declared)
    observed = next(slot for slot in registered["slots"] if slot["attempt_id"] == selected["attempt_id"])
    assert observed["family"] is None and observed["family_relation"] == "unknown"
    assert any(row["subject"] == f"slots.{selected['attempt_id']}.family_relation"
               for row in registered["pending_decisions"])


def test_all_caller_declarations_still_do_not_authorize_or_authenticate(case):
    declared = deepcopy(case.declaration)
    for decision in declared["decisions"].values():
        decision.update(status="declared", reference="synthetic://caller-reference")
    for record in declared["records"]:
        record["context"].update(review_status="declared_reviewed", review_reference="synthetic://caller-review")
    for slot in declared["slots"]:
        slot.update(rater="synthetic-declared-rater", route="synthetic-declared-route")
    destination, registered = case.prepare(declared)
    assert registered["missing_cells"] == [] and registered["missing_slots"] == []
    assert registered["pending_decisions"] == []
    assert registered["execution_authorized"] is False
    assert registered["scientific_eligibility"] is False
    assert registered["records"][0]["context"]["approval_authenticated"] is False
    assert panel.recheck_panel(destination) == registered


def test_returned_registration_mutation_cannot_change_pair_or_recheck_authority(case):
    destination, registered = case.prepare()
    expected = deepcopy(registered)
    registered["slots"][0]["binding"]["context_sha256"] = "0" * 64
    assert registered["slots"][1]["binding"] == expected["slots"][1]["binding"]
    registered["limitations"].clear()
    registered["records"][0]["context"]["normalized"].clear()
    registered["instruments"][0]["resources"]["definition"]["sha256"] = "0" * 64
    assert panel.recheck_panel(destination) == expected


@pytest.mark.parametrize("resource", ["definition_path", "rubric_path", "schema_path", "evidence_authority_path"])
def test_caller_root_cannot_substitute_a_selected_released_resource(case, resource):
    instrument = select_semantic_instrument("rubric20", "4.0")
    path = case.root / getattr(instrument, resource)
    # Even a semantics-preserving byte edit is a different instrument asset.
    path.write_bytes(path.read_bytes() + b"\n ")
    before = snapshot(case.root)
    with pytest.raises(ValueError):
        case.prepare()
    assert not (case.tmp / "adversarial-panel").exists()
    assert snapshot(case.root) == before


def test_historical_v2_keeps_acceptance_blocker_even_when_all_decisions_declared(case):
    declared = deepcopy(case.declaration)
    for instrument in declared["instruments"]:
        instrument["version"] = "2.0"
    for decision in declared["decisions"].values():
        decision.update(status="declared", reference="synthetic://caller-reference")
    for record in declared["records"]:
        record["context"].update(review_status="declared_reviewed", review_reference="synthetic://caller-review")
    for slot in declared["slots"]:
        slot.update(rater="synthetic-declared-rater", route="synthetic-declared-route")
    destination, registered = case.prepare(declared)
    assert registered["missing_cells"] == [] and registered["missing_slots"] == []
    assert registered["pending_decisions"]
    assert all("historical_classification_only" in json.dumps(instrument)
               for instrument in registered["instruments"])
    assert registered["execution_authorized"] is False
    assert registered["scientific_eligibility"] is False
    assert panel.recheck_panel(destination) == registered


def test_existing_output_and_original_sources_are_preserved(case):
    case.path.write_bytes(canonical(case.declaration))
    destination = case.tmp / "existing-output"
    destination.mkdir()
    (destination / "panel.json").write_bytes(b"preserved previous registration\n")
    before_output, before_root = snapshot(destination), snapshot(case.root)
    with pytest.raises(ValueError):
        panel.prepare_panel(case.path, destination, root=case.root)
    assert snapshot(destination) == before_output
    assert snapshot(case.root) == before_root
