"""Captured-resource and command boundaries; all ratings are synthetic fixtures."""
from copy import deepcopy
import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from data_sheets_schema import cross_family_panel as panels
from data_sheets_schema import cross_family_panel_results as results
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema.cli.cross_family_panel import cross_family_panel
from data_sheets_schema.evaluation import validate
from data_sheets_schema.support_plan import canonical, sha256
from tests.test_evaluation.test_cross_family_panel import build_fixture
from tests.test_evaluation.test_cross_family_panel_results_adversarial import synthetic_rating

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def prepared(tmp_path):
    root, declaration, path = build_fixture(tmp_path)
    panel_dir = tmp_path / "panel"
    panel = panels.prepare_panel(path, panel_dir, root=root)
    submitted = tmp_path / "ratings"
    submitted.mkdir()
    return root, declaration, path, panel_dir, panel, submitted


def submission_for(panel_dir, panel, slot, submitted):
    rating = synthetic_rating(panel_dir, panel, slot)
    raw = canonical(rating)
    path = submitted / "rating.json"
    path.write_bytes(raw)
    value = {"format": results.SUBMISSIONS_FORMAT,
             "panel_sha256": sha256((panel_dir / "panel.json").read_bytes()),
             "submissions": [{**{key: slot[key] for key in results.IDENTITY if key != "version"},
                              "version": slot["binding"]["instrument"]["version"],
                              "result": {"path": path.name, "sha256": sha256(raw)}}]}
    return rating, value


def test_actual_cli_accepts_and_rechecks_saved_partial_panel(prepared, tmp_path):
    _, _, _, panel_dir, panel, submitted = prepared
    _, value = submission_for(panel_dir, panel, panel["slots"][0], submitted)
    path = tmp_path / "submissions.json"
    path.write_bytes(canonical(value))
    output = tmp_path / "results"
    runner = CliRunner()
    accepted = runner.invoke(cross_family_panel, ["accept-results", "--panel", str(panel_dir),
                            "--submissions", str(path), "--root", str(submitted), "--output", str(output)])
    assert accepted.exit_code == 0, accepted.output
    report = json.loads(accepted.output)
    assert report["counts"] == {"selected": 4, "accepted": 1, "rejected": 0, "missing": 3, "unsupported": 0}
    checked = runner.invoke(cross_family_panel, ["recheck-results", "--results", str(output)])
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output) == report
    sentinel = (output / "results.json").read_bytes()
    repeated = runner.invoke(cross_family_panel, ["accept-results", "--panel", str(panel_dir),
                            "--submissions", str(path), "--root", str(submitted), "--output", str(output)])
    assert repeated.exit_code != 0 and (output / "results.json").read_bytes() == sentinel


@pytest.mark.parametrize("rubric,version", [("rubric10", "3.0"), ("rubric20", "4.0")])
def test_existing_historical_cli_routes_remain_callable(prepared, tmp_path, rubric, version, capsys):
    """#4652: exercise both existing main() routes without a resource_reader local."""
    _, _, _, panel_dir, panel, _ = prepared
    slot = next(row for row in panel["slots"] if row["rubric"] == rubric)
    rating = synthetic_rating(panel_dir, panel, slot)
    assert rating["version"] == version
    corpus = tmp_path / "historical"
    corpus.mkdir()
    (corpus / "sample_evaluation.json").write_bytes(canonical(rating))
    assert validate.main(corpus, ROOT / "src/download/prompts") == 0
    assert "valid    1" in capsys.readouterr().out


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_explicit_resource_seam_reaches_classification_and_input_evidence(prepared, monkeypatch, rubric):
    _, _, _, panel_dir, panel, _ = prepared
    slot = next(row for row in panel["slots"] if row["rubric"] == rubric)
    rating = synthetic_rating(panel_dir, panel, slot)
    instrument = slot["binding"]["instrument"]
    assets = {pin["path"]: (panel_dir / "artifacts" / pin["sha256"]).read_bytes()
              for pin in instrument["resources"].values() if pin is not None}
    used = []

    def reader(path):
        used.append(path)
        return assets[path]

    def forbidden(*args, **kwargs):
        pytest.fail("explicit captured resources fell back to an ambient instrument")

    from data_sheets_schema import semantic_scope, semantic_evidence, semantic_evidence_authority
    from data_sheets_schema.evaluation_context import unwrap_document
    for module in (validate, semantic_scope, semantic_evidence, semantic_evidence_authority):
        monkeypatch.setattr(module, "resource_path", forbidden)
    schema = json.loads(assets[instrument["resources"]["schema"]["path"]])
    assert validate.validate_evaluation(rating, schema, resource_reader=reader) == (True, [])
    record = panel["records"][0]
    raw = (panel_dir / "artifacts" / record["input"]["sha256"]).read_bytes()
    document = unwrap_document(saved._read(raw, "fixture", yaml_allowed=True))
    report = semantic_scope.validate_scope(rating, document=document, input_sha256=sha256(raw),
                                          expected_context=record["context"]["normalized"], resource_reader=reader)
    assert report.passed
    assert used.count(instrument["resources"]["rubric"]["path"]) >= 3
    assert used.count(instrument["resources"]["evidence_authority"]["path"]) >= 3


@pytest.mark.parametrize("reference", ["$ref", "$dynamicRef", "$recursiveRef"])
def test_captured_schema_never_resolves_external_references(monkeypatch, reference):
    import socket
    import urllib.request

    def forbidden(*args, **kwargs):
        pytest.fail("a captured schema attempted network or URI access")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    schema = {"$schema": "http://json-schema.org/draft-07/schema#", reference: "https://example.invalid/schema"}
    accepted, errors = validate.validate_evaluation({}, schema, resource_reader=forbidden)
    assert not accepted and any("external reference" in error for error in errors)


def test_old_validator_panel_is_preserved_unsupported_then_fresh_predecessor_registration(prepared, tmp_path):
    root, declaration, declaration_path, panel_dir, original_panel, submitted = prepared
    # A coherent historical package, not a corrupt artifact under an old hash.
    capture = saved.Capture(panel_dir)
    old_path = "src/data_sheets_schema/semantic_scope.py"
    old_raw = b"# historical validator code; never executed\nraise RuntimeError('captured code executed')\n"
    original_files = original_panel["captured_files"]

    def reader(name):
        return old_raw if name == old_path else capture.get(original_files[name])

    old = panels._registration(capture, declaration_path.read_bytes(), reader)
    historical = tmp_path / "historical-panel"
    panels._write_panel(historical, capture, old)
    rating, submission = submission_for(historical, old, old["slots"][0], submitted)
    submission_path = tmp_path / "old-submission.json"
    submission_path.write_bytes(canonical(submission))
    before = {str(path.relative_to(historical)): path.read_bytes() for path in historical.rglob("*") if path.is_file()}
    report = results.accept_panel_results(historical, submission_path, tmp_path / "old-results", root=submitted)
    assert report["counts"] == {"selected": 4, "accepted": 0, "rejected": 0, "missing": 3, "unsupported": 1}
    assert report["validator_source_mismatches"] == [old_path]
    assert results.recheck_panel_results(tmp_path / "old-results") == report
    assert before == {str(path.relative_to(historical)): path.read_bytes() for path in historical.rglob("*") if path.is_file()}
    fresh = deepcopy(declaration)
    fresh["predecessor_sha256"] = sha256((historical / "panel.json").read_bytes())
    declaration_path.write_bytes(canonical(fresh))
    current = panels.prepare_panel(declaration_path, tmp_path / "fresh-panel", root=root)
    assert current["predecessor_sha256"] == fresh["predecessor_sha256"]
    assert current["records"] == original_panel["records"]
    assert current["slots"] == original_panel["slots"]
    assert not current["execution_authorized"] and not current["scientific_eligibility"]


def test_result_publication_preflight_and_detachment(prepared, tmp_path, monkeypatch):
    _, _, _, panel_dir, panel, submitted = prepared
    _, submission = submission_for(panel_dir, panel, panel["slots"][0], submitted)
    path = tmp_path / "submissions.json"
    path.write_bytes(canonical(submission))
    first = tmp_path / "first"
    value = results.accept_panel_results(panel_dir, path, first, root=submitted)
    raw = (first / "results.json").read_bytes()
    value["limitations"].clear()
    value["rows"][0]["submission"]["model"] = "changed"
    assert results.recheck_panel_results(first)["rows"][0]["state"] == "accepted"
    monkeypatch.setattr(results, "MAX_RESULTS_BYTES", len(raw) - 1)
    destination = tmp_path / "too-small"
    with pytest.raises(ValueError, match="output exceeds manifest byte bound"):
        results.accept_panel_results(panel_dir, path, destination, root=submitted)
    assert not destination.exists() and (first / "results.json").read_bytes() == raw
