"""Independent saved-rating controls; synthetic scores are not scientific labels.

These tests use captured panel inputs and complete semantic shapes. They never
dispatch a rater or treat caller identities as authenticated execution.
"""
from copy import deepcopy
import json
import socket
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import cross_family_panel as panel
from data_sheets_schema import cross_family_panel_results as results
from data_sheets_schema.evaluation_context import context_digest, unwrap_document
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.support_plan import canonical, sha256
from tests.test_evaluation.test_cross_family_panel import build_fixture
from tests.test_evaluation.test_semantic_evaluation_contract import (
    _rubric10_record, _rubric20_record,
)
from tests.test_evaluation.test_semantic_evidence import _groups, _rescore


def snapshot(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def synthetic_rating(directory, registration, slot, *, context_override=None):
    """Build a complete full-score software fixture from captured instruments."""
    def raw(pin):
        return (directory / "artifacts" / pin["sha256"]).read_bytes()

    record = next(row for row in registration["records"] if row["record_id"] == slot["record_id"])
    instrument = next(row for row in registration["instruments"] if row["rubric"] == slot["rubric"])
    rubric = slot["rubric"]
    assets = instrument["resources"]
    document = unwrap_document(yaml.safe_load(raw(record["input"])))
    specification = yaml.safe_load(raw(assets["rubric"]))
    context = record["context"]["normalized"] if context_override is None else context_override
    contract = evaluation_contract(rubric, specification, context, document)
    result = _rubric10_record() if rubric == "rubric10" else _rubric20_record()
    result.update(version=instrument["version"], project=record["project"], method=record["method"],
                  d4d_file=record["input"]["path"], applicability_context=deepcopy(context),
                  evaluation_scope=contract["scope"],
                  metadata={"context_sha256": context_digest(context),
                            "input_sha256": record["input"]["sha256"],
                            "rubric_sha256": assets["rubric"]["sha256"],
                            "instrument_sha256": assets["definition"]["sha256"]})
    result["model"]["name"] = slot["model"]
    if slot["rater"] is not None:
        result["metadata"]["evaluator_id"] = slot["rater"]
    if assets["evidence_authority"] is not None:
        result["metadata"]["evidence_authority_sha256"] = assets["evidence_authority"]["sha256"]
    result["semantic_analysis"]["issues_detected"] = []
    for group, items in _groups(result):
        for index, item in enumerate(items, 1):
            key = f"E{group['id']}.{index}" if rubric == "rubric10" else f"Q{item['id']}"
            rule = contract["items"][key]
            score = rule["fixed_max_score"] if rule["applicable"] else None
            item.update(name=rule["name"], score=score, applicable=rule["applicable"],
                        applicability_status=rule["status"], applicability_evidence=rule["evidence"],
                        unit_scores=[{"path": unit["path"], "score": score,
                                      "evidence": "Synthetic software acceptance fixture.",
                                      "cited": [{"path": "id"}] if score is not None else [],
                                      "absent": [], "counts": [], "considered": []}
                                     for unit in contract["scope"]["units"]])
            if rubric == "rubric10":
                item["item_id"] = key
            else:
                item["max_score"] = rule["fixed_max_score"]
    _rescore(result)
    return result


@pytest.fixture
def case(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("offline saved-result acceptance attempted network access")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    root, declaration, declaration_path = build_fixture(tmp_path)
    panel_dir = tmp_path / "registered-panel"
    registered = panel.prepare_panel(declaration_path, panel_dir, root=root)
    submitted = tmp_path / "submitted"
    submitted.mkdir()
    associations = []
    for slot in registered["slots"]:
        rating_path = submitted / (slot["attempt_id"] + ".json")
        rating_path.write_bytes(canonical(synthetic_rating(panel_dir, registered, slot)))
        associations.append({**{key: slot[key] for key in (
            "record_id", "rubric", "role", "attempt_id", "model", "family", "rater", "route", "binding_sha256")},
            "version": slot["binding"]["instrument"]["version"],
            "result": {"path": rating_path.name, "sha256": sha256(rating_path.read_bytes())}})
    submission = {"format": "cross_family_panel_submissions_v1",
                  "panel_sha256": sha256((panel_dir / "panel.json").read_bytes()),
                  "submissions": associations}
    path = tmp_path / "submissions.json"

    def accept(value=None, name="accepted-package"):
        path.write_bytes(canonical(submission if value is None else value))
        destination = tmp_path / name
        report = results.accept_panel_results(panel_dir, path, destination, root=submitted)
        return destination, report

    return SimpleNamespace(root=root, declaration=declaration, declaration_path=declaration_path,
                           panel_dir=panel_dir, registered=registered, submitted=submitted,
                           submission=submission, path=path, accept=accept, tmp=tmp_path)


def alter_rating(case, declaration, index, mutation):
    ref = declaration["submissions"][index]["result"]
    path = case.submitted / ref["path"]
    value = json.loads(path.read_bytes())
    mutation(value)
    path.write_bytes(canonical(value))
    ref["sha256"] = sha256(path.read_bytes())


def selected_row(report, association):
    return next(row for row in report["rows"] if all(row[key] == association[key]
                for key in ("record_id", "rubric", "role")))


def test_full_registered_denominator_accepts_only_structural_fixture_and_keeps_holds(case):
    before = snapshot(case.root), snapshot(case.panel_dir), snapshot(case.submitted)
    destination, report = case.accept()
    assert report["counts"] == {"selected": 4, "accepted": 4, "rejected": 0, "missing": 0, "unsupported": 0}
    assert len(report["rows"]) == 4
    assert all(row["state"] == "accepted" for row in report["rows"])
    assert report["execution_authorized"] is False and report["scientific_eligibility"] is False
    assert "pending" in json.dumps(report["readiness"])
    assert "scientific_review" in json.dumps(report["readiness"])
    assert results.recheck_panel_results(destination) == report
    assert before == (snapshot(case.root), snapshot(case.panel_dir), snapshot(case.submitted))


@pytest.mark.parametrize("field,replacement", [
    ("attempt_id", "unregistered-retry"), ("model", "openai:gpt-5"),
    ("family", "gpt"), ("rater", "invented-reviewer"), ("route", "invented-route"),
    ("version", "4.0"), ("binding_sha256", "f" * 64),
])
def test_known_slot_binding_mismatches_retain_rejected_denominator(case, field, replacement):
    declared = deepcopy(case.submission)
    changed = declared["submissions"][0]
    changed[field] = replacement
    _, report = case.accept(declared)
    assert selected_row(report, changed)["state"] == "rejected"
    assert selected_row(report, changed)["errors"]
    assert report["counts"] == {"selected": 4, "accepted": 3, "rejected": 1, "missing": 0, "unsupported": 0}


def test_shared_binding_digest_cannot_reassign_role_payload(case):
    same, cross = case.registered["slots"][:2]
    assert same["rubric"] == cross["rubric"] and same["binding_sha256"] == cross["binding_sha256"]
    declared = deepcopy(case.submission)
    # Keep each declared slot/attempt intact while exchanging the actual output.
    declared["submissions"][0]["result"], declared["submissions"][1]["result"] = (
        declared["submissions"][1]["result"], declared["submissions"][0]["result"])
    _, report = case.accept(declared)
    assert [row["state"] for row in report["rows"][:2]] == ["rejected", "rejected"]
    assert report["counts"]["selected"] == 4 and report["counts"]["accepted"] == 2


@pytest.mark.parametrize("mutation", ["duplicate_slot", "unknown_record", "unknown_role", "wrong_panel", "extra"])
def test_unregistered_or_ambiguous_submission_selection_refuses_without_output(case, mutation):
    declared = deepcopy(case.submission)
    if mutation == "duplicate_slot":
        declared["submissions"].pop()
        declared["submissions"].append(deepcopy(declared["submissions"][0]))
    elif mutation == "unknown_record":
        declared["submissions"][0]["record_id"] = "unselected-record"
    elif mutation == "unknown_role":
        declared["submissions"][0]["role"] = "preferred-retry"
    elif mutation == "wrong_panel":
        declared["panel_sha256"] = "f" * 64
    else:
        declared["execution_authorized"] = True
    before = snapshot(case.panel_dir), snapshot(case.submitted)
    with pytest.raises(ValueError):
        case.accept(declared)
    assert not (case.tmp / "accepted-package").exists()
    assert before == (snapshot(case.panel_dir), snapshot(case.submitted))


@pytest.mark.parametrize("mutation", ["model", "instrument", "input", "rubric", "context_missing", "context_true", "quote"])
def test_payload_conflicts_rejected_without_relabelling_registered_slot(case, mutation):
    declared = deepcopy(case.submission)

    def change(value):
        if mutation == "model":
            value["model"]["name"] = "openai:gpt-5"
        elif mutation in ("instrument", "input", "rubric"):
            value["metadata"][mutation + "_sha256"] = "e" * 64
        elif mutation in ("context_missing", "context_true"):
            changed = deepcopy(value["applicability_context"])
            if mutation == "context_missing":
                changed.pop("human_subjects")
            else:
                changed["human_subjects"]["value"] = True
            slot = case.registered["slots"][0]
            rebuilt = synthetic_rating(case.panel_dir, case.registered, slot, context_override=changed)
            value.clear()
            value.update(rebuilt)
            # It is coherent under the invented context, so rejection must
            # depend on the captured caller context rather than stale totals.
            from data_sheets_schema.evaluation import validate
            schema_pin = slot["binding"]["instrument"]["resources"]["schema"]
            schema = json.loads((case.panel_dir / "artifacts" / schema_pin["sha256"]).read_bytes())
            assert validate.validate_evaluation(value, schema) == (True, [])
        else:
            first = next(_groups(value))[1][0]
            first["unit_scores"][0]["cited"] = [{"path": "id", "quote": "never present in the source"}]

    alter_rating(case, declared, 0, change)
    _, report = case.accept(declared)
    row = selected_row(report, declared["submissions"][0])
    assert row["state"] == "rejected" and row["errors"]
    assert row["attempt_id"] == case.registered["slots"][0]["attempt_id"]
    assert report["counts"]["selected"] == 4 and report["counts"]["accepted"] == 3


def test_missing_and_invalid_results_do_not_shrink_selected_denominator(case):
    declared = deepcopy(case.submission)
    declared["submissions"].pop()
    malformed = case.submitted / declared["submissions"][1]["result"]["path"]
    malformed.write_bytes(b'{"rubric": invalid JSON}\n')
    declared["submissions"][1]["result"]["sha256"] = sha256(malformed.read_bytes())
    _, report = case.accept(declared)
    assert report["counts"] == {"selected": 4, "accepted": 2, "rejected": 1, "missing": 1, "unsupported": 0}
    assert len(report["rows"]) == 4
    assert report["execution_authorized"] is False and report["scientific_eligibility"] is False


def test_relocated_recheck_uses_only_captured_bytes(case, monkeypatch):
    destination, report = case.accept()
    relocated = case.tmp / "relocated"
    destination.rename(relocated)
    case.root.rename(case.tmp / "original-corpus-retained")
    case.panel_dir.rename(case.tmp / "original-panel-retained")
    case.submitted.rename(case.tmp / "original-submissions-retained")
    case.path.rename(case.tmp / "original-associations-retained.json")
    case.declaration_path.rename(case.tmp / "original-declaration-retained.json")
    before = snapshot(relocated)

    def forbidden(*args, **kwargs):
        pytest.fail("captured acceptance consulted ambient instrument resources")

    from data_sheets_schema import semantic_scope, semantic_evidence, semantic_evidence_authority
    from data_sheets_schema.evaluation import validate
    for module in (semantic_scope, semantic_evidence, semantic_evidence_authority, validate):
        monkeypatch.setattr(module, "resource_path", forbidden)
    assert results.recheck_panel_results(relocated) == report
    assert snapshot(relocated) == before


@pytest.mark.parametrize("field", ["counts", "accepted_row", "execution_authorized", "scientific_eligibility"])
def test_saved_acceptance_claims_are_reconstructed_not_trusted(case, field):
    destination, _ = case.accept()
    path = destination / "results.json"
    value = json.loads(path.read_bytes())
    if field == "counts":
        value["counts"]["accepted"] = 0
    elif field == "accepted_row":
        value["rows"][0]["state"] = "missing"
    else:
        value[field] = True
    path.write_bytes(canonical(value) + b"\n")
    before = snapshot(destination)
    with pytest.raises(ValueError):
        results.recheck_panel_results(destination)
    assert snapshot(destination) == before


@pytest.mark.parametrize("asset", ["record", "original_context", "rating", "schema", "definition", "validator_code"])
def test_changed_captured_bytes_refuse_without_running_captured_code(case, asset):
    destination, _ = case.accept()
    if asset == "record":
        pin = case.registered["records"][0]["input"]
    elif asset == "original_context":
        pin = case.registered["records"][0]["context"]["source"]
    elif asset == "rating":
        pin = case.submission["submissions"][0]["result"]
    elif asset == "validator_code":
        pin = next(row for row in case.registered["validator_authority"]
                   if row["path"].endswith("/semantic_scope.py"))
    else:
        pin = case.registered["instruments"][0]["resources"][asset]
    path = destination / "artifacts" / pin["sha256"]
    sentinel = case.tmp / "captured-code-must-not-run"
    if asset == "validator_code":
        path.write_bytes(f"open({str(sentinel)!r}, 'w').write('executed')\n".encode())
    else:
        path.write_bytes(path.read_bytes() + b"\nchanged bytes\n")
    before = snapshot(destination)
    with pytest.raises(ValueError):
        results.recheck_panel_results(destination)
    assert snapshot(destination) == before and not sentinel.exists()


def test_original_false_context_is_retained_separately_from_normalization(case):
    destination, report = case.accept()
    context = case.registered["records"][0]["context"]
    original = (case.root / context["source"]["path"]).read_bytes()
    assert original == b"human_subjects: false\n"
    assert (destination / "artifacts" / context["source"]["sha256"]).read_bytes() == original
    registered = json.loads((destination / "artifacts" / report["panel"]["sha256"]).read_bytes())
    assert registered["records"][0]["context"]["normalized"]["human_subjects"]["value"] is False
    assert "shared_dataset" not in registered["records"][0]["context"]["normalized"]
    assert registered["records"][0]["context"]["review_status"] == "pending"


def test_payload_rater_cannot_replace_missing_registered_rater(case):
    declared = deepcopy(case.submission)
    alter_rating(case, declared, 0, lambda value: value["metadata"].update(evaluator_id="not-the-declared-rater"))
    # The slot has rater=None; this extra payload identity still contradicts it.
    _, report = case.accept(declared)
    assert report["rows"][0]["state"] == "rejected"


def test_duplicate_attempt_cannot_be_reassigned_to_another_registered_slot(case):
    declared = deepcopy(case.submission)
    declared["submissions"][1]["attempt_id"] = declared["submissions"][0]["attempt_id"]
    # Duplicate attempt declarations must not select a replacement output.
    with pytest.raises(ValueError):
        case.accept(declared, name="duplicate-attempt")
    assert not (case.tmp / "duplicate-attempt").exists()


def test_historical_instrument_remains_unsupported_with_full_selected_denominator(case):
    historical = deepcopy(case.declaration)
    for instrument in historical["instruments"]:
        instrument["version"] = "2.0"
    declaration_path = case.tmp / "historical-declaration.json"
    declaration_path.write_bytes(canonical(historical))
    directory = case.tmp / "historical-panel"
    registered = panel.prepare_panel(declaration_path, directory, root=case.root)
    submissions = deepcopy(case.submission)
    submissions["panel_sha256"] = sha256((directory / "panel.json").read_bytes())
    for row, slot in zip(submissions["submissions"], registered["slots"]):
        row.update(version="2.0", binding_sha256=slot["binding_sha256"])
        raw = canonical(synthetic_rating(directory, registered, slot))
        (case.submitted / row["result"]["path"]).write_bytes(raw)
        row["result"]["sha256"] = sha256(raw)
    submission_path = case.tmp / "historical-submission.json"
    submission_path.write_bytes(canonical(submissions))
    destination = case.tmp / "historical-acceptance"
    report = results.accept_panel_results(directory, submission_path, destination, root=case.submitted)
    assert report["counts"] == {"selected": 4, "accepted": 0, "rejected": 0, "missing": 0, "unsupported": 4}
    assert all(row["state"] == "unsupported" for row in report["rows"])
    assert report["scientific_eligibility"] is False and report["execution_authorized"] is False
    assert results.recheck_panel_results(destination) == report


def test_self_consistent_captured_foreign_validator_is_unsupported_and_never_executed(case):
    path = "src/data_sheets_schema/semantic_scope.py"
    sentinel = case.tmp / "captured-validator-executed"
    raw = f"open({str(sentinel)!r}, 'w').write('executed')\n".encode()
    new_pin = {"sha256": sha256(raw), "bytes": len(raw)}
    (case.panel_dir / "artifacts" / new_pin["sha256"]).write_bytes(raw)
    stored = deepcopy(case.registered)
    stored["captured_files"][path] = new_pin
    index = next(i for i, row in enumerate(stored["validator_authority"]) if row["path"] == path)
    stored["validator_authority"][index] = {"path": path, **new_pin}
    panel_path = case.panel_dir / "panel.json"
    panel_path.write_bytes(canonical(stored) + b"\n")
    # This is internally consistent captured registration, not just a bad hash.
    assert panel.recheck_panel(case.panel_dir) == stored
    declaration = deepcopy(case.submission)
    declaration["panel_sha256"] = sha256(panel_path.read_bytes())
    destination, report = case.accept(declaration)
    assert report["counts"] == {"selected": 4, "accepted": 0, "rejected": 0, "missing": 0, "unsupported": 4}
    assert not sentinel.exists()
    assert results.recheck_panel_results(destination) == report
    assert not sentinel.exists()


def test_submission_cannot_fill_an_undeclared_slot_or_missing_matrix_cell(case):
    declaration = deepcopy(case.declaration)
    removed = declaration["slots"].pop()
    declaration["matrix"]["cohorts"].append("not-selected")
    case.declaration_path.write_bytes(canonical(declaration))
    directory = case.tmp / "panel-with-missing-declarations"
    registered = panel.prepare_panel(case.declaration_path, directory, root=case.root)
    submissions = deepcopy(case.submission)
    submissions["panel_sha256"] = sha256((directory / "panel.json").read_bytes())
    case.path.write_bytes(canonical(submissions))
    destination = case.tmp / "missing-slot-results"
    report = results.accept_panel_results(directory, case.path, destination, root=case.submitted)
    row = selected_row(report, removed)
    assert row["state"] == "missing" and row["attempt_id"] is None and row["errors"]
    assert report["counts"] == {"selected": 4, "accepted": 3, "rejected": 0, "missing": 1, "unsupported": 0}
    assert registered["missing_cells"]
    assert "not-selected" in json.dumps(report["readiness"])
    assert results.recheck_panel_results(destination) == report
