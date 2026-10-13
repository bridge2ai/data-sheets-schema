"""Captured synthetic ratings exercise the offline analysis contract, not science.

Every integration rating passes the ordinary saved-result acceptor.  The data
and declared identities below are invented and confer no execution permission.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from data_sheets_schema import cross_family_panel as panels
from data_sheets_schema import cross_family_panel_results as accepted
from data_sheets_schema import cross_family_panel_analysis as analysis
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.support_plan import canonical, sha256
from tests.test_evaluation.test_cross_family_panel import build_fixture, write_declaration
from tests.test_evaluation.test_cross_family_panel_results_adversarial import synthetic_rating, snapshot
from tests.test_evaluation.test_semantic_evidence import _groups, _rescore


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("offline paired analysis attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def _item(value, key):
    return next(item for _, items in _groups(value) for item in items
                if (item.get("item_id") if value["rubric"] == "rubric10-semantic"
                    else "Q" + str(item["id"])) == key)


def _score(value, key, scores):
    """Set real resource scores and recompute the existing instrument summary."""
    item = _item(value, key)
    scores = [scores] * len(item["unit_scores"]) if type(scores) is int else scores
    assert len(scores) == len(item["unit_scores"])
    assert item["applicable"] is True
    for row, score in zip(item["unit_scores"], scores):
        row["score"] = score
    item["score"] = min(scores)
    item["no_issue_reason"] = "Deliberately varied synthetic software-control score."
    _rescore(value)


def make_case(tmp_path, *, count=1, collection=False, same_input=False,
              contexts=None, change_declaration=None, change_rating=None):
    """Use original prepare/accept boundaries, with explicit rater declarations."""
    root, declaration, path = build_fixture(tmp_path)
    record_template = deepcopy(declaration["records"][0])
    slot_templates = deepcopy(declaration["slots"])
    declaration["records"], declaration["slots"] = [], []
    for index in range(count):
        record_id = "record-" + str(index)
        name = record_id + ".yaml"
        identity = "shared" if same_input else record_id
        text = ("CoreDatasetCollection:\n  resources:\n  - id: example:" + identity + "-a\n"
                "  - id: example:" + identity + "-b\n") if collection else (
                "CoreDataset:\n  id: example:" + identity + "\n  description: Synthetic fixture.\n")
        (root / name).write_text(text, encoding="utf-8")
        record = deepcopy(record_template)
        record.update(record_id=record_id, replicate=index + 1,
                      input={"path": name, "sha256": sha256(text.encode())})
        if contexts is not None and contexts[index] is None:
            record["context"]["source"] = None
        declaration["records"].append(record)
        for template in slot_templates:
            slot = deepcopy(template)
            slot.update(record_id=record_id,
                        attempt_id=record_id + "-" + slot["attempt_id"],
                        rater="synthetic-" + slot["role"], route="offline-fixture")
            declaration["slots"].append(slot)
    if change_declaration:
        change_declaration(declaration)
    write_declaration(path, declaration)
    panel_dir = tmp_path / "panel"
    registered = panels.prepare_panel(path, panel_dir, root=root)
    ratings_dir = tmp_path / "ratings"
    ratings_dir.mkdir()
    submissions, rating_values = [], {}
    for slot in registered["slots"]:
        if slot["attempt_id"] is None:
            continue
        value = synthetic_rating(panel_dir, registered, slot)
        if change_rating:
            change_rating(value, slot)
        name = slot["attempt_id"] + ".json"
        raw = canonical(value)
        (ratings_dir / name).write_bytes(raw)
        rating_values[(slot["record_id"], slot["rubric"], slot["role"])] = value
        submissions.append({**{key: slot[key] for key in accepted.IDENTITY if key != "version"},
                            "version": slot["binding"]["instrument"]["version"],
                            "result": {"path": name, "sha256": sha256(raw)}})
    submission = {"format": accepted.SUBMISSIONS_FORMAT,
                  "panel_sha256": sha256((panel_dir / "panel.json").read_bytes()),
                  "submissions": submissions}
    return SimpleNamespace(tmp=tmp_path, root=root, declaration=declaration, path=path,
                           panel_dir=panel_dir, registered=registered, ratings_dir=ratings_dir,
                           submission=submission, rating_values=rating_values)


def policy(case, *, unit="record_item", scale="raw_total_points", blocks=None, strata=None):
    ids = [row["record_id"] for row in case.registered["records"]]
    return {"format": "cross_family_panel_analysis_declaration_v1", "analysis_id": "synthetic-analysis",
            "panel_sha256": sha256((case.panel_dir / "panel.json").read_bytes()),
            "record_ids": ids,
            "instruments": [{"rubric": row["rubric"], "version": row["version"]}
                            for row in case.registered["instruments"]],
            "agreement": {"unit": unit, "weighting": "equal_observation"},
            "gap": {"scale": scale, "weighting": "equal_record"},
            "grouping": "instrument_domain_ordered_rater_pair",
            "uncertainty": {"method": "paired_cluster_percentile_v1", "confidence": 0.9,
                            "resamples": 16, "seed": 7, "quantile": "linear_n_minus_one",
                            "blocks": blocks if blocks is not None else [
                                {"block_id": "b" + str(i), "record_ids": [name]}
                                for i, name in enumerate(ids)],
                            "strata": strata if strata is not None else [
                                {"stratum_id": "all", "record_ids": ids}]}}


def prepare(case, declaration=None, *, name="spec"):
    path = case.tmp / (name + "-declaration.json")
    path.write_bytes(canonical(policy(case) if declaration is None else declaration))
    directory = case.tmp / name
    result = analysis.prepare_analysis_spec(case.panel_dir, path, directory)
    return directory, result


def accept(case, *, name="results"):
    path = case.tmp / (name + "-submission.json")
    path.write_bytes(canonical(case.submission))
    directory = case.tmp / name
    report = accepted.accept_panel_results(case.panel_dir, path, directory, root=case.ratings_dir)
    return directory, report


def run_analysis(case, declaration=None, *, name="analysis"):
    specification, spec = prepare(case, declaration, name=name + "-spec")
    results, receipt = accept(case, name=name + "-results")
    directory = case.tmp / name
    report = analysis.analyze_panel_results(specification, results, directory)
    return directory, report, receipt, specification, results


def pair(report, record="record-0", rubric="rubric10"):
    return next(row for row in report["pairs"] if row["record_id"] == record and row["rubric"] == rubric)


def test_real_cli_chain_relocates_without_original_paths_or_network(tmp_path, monkeypatch):
    case = make_case(tmp_path)
    results, receipt = accept(case)
    declaration = tmp_path / "analysis-declaration.json"
    declaration.write_bytes(canonical(policy(case)))
    runner = CliRunner()
    specification = tmp_path / "spec"
    prepared = runner.invoke(evaluate, ["cross-family-panel", "prepare-analysis", "--panel",
        str(case.panel_dir), "--declaration", str(declaration), "--output", str(specification)])
    assert prepared.exit_code == 0, prepared.output
    expected_spec = json.loads(prepared.output)
    checked = runner.invoke(evaluate, ["cross-family-panel", "recheck-analysis-spec",
                                      "--specification", str(specification)])
    assert checked.exit_code == 0 and json.loads(checked.output) == expected_spec
    directory = tmp_path / "analysis"
    analyzed = runner.invoke(evaluate, ["cross-family-panel", "analyze", "--specification",
        str(specification), "--results", str(results), "--output", str(directory)])
    assert analyzed.exit_code == 0, analyzed.output
    expected = json.loads(analyzed.output)
    assert receipt["counts"]["accepted"] == 4
    assert len(expected["slots"]) == 4 and len(expected["pairs"]) == 2
    assert all(row["score_pair_complete"] and row["attributed_role_pair"] for row in expected["pairs"])
    assert expected["scientific_eligibility"] is False and expected["execution_authorized"] is False
    assert expected["readiness"] == receipt["readiness"]
    moved = tmp_path / "relocated-analysis"
    directory.rename(moved)
    for old in (case.root, case.panel_dir, case.ratings_dir, results, specification):
        shutil.rmtree(old)
    for old in (case.path, declaration, tmp_path / "results-submission.json"):
        old.unlink()
    from data_sheets_schema import semantic_scope, semantic_evidence, semantic_evidence_authority
    from data_sheets_schema.evaluation import validate
    def forbidden(*args, **kwargs):
        pytest.fail("relocated analysis consulted an ambient instrument")
    for module in (semantic_scope, semantic_evidence, semantic_evidence_authority, validate):
        monkeypatch.setattr(module, "resource_path", forbidden)
    before = snapshot(moved)
    rechecked = runner.invoke(evaluate, ["cross-family-panel", "recheck-analysis", "--analysis", str(moved)])
    assert rechecked.exit_code == 0, rechecked.output
    assert json.loads(rechecked.output) == expected and snapshot(moved) == before


def test_equal_totals_do_not_hide_item_disagreements_or_follow_array_positions(tmp_path):
    def change(value, slot):
        if slot["rubric"] == "rubric10":
            _score(value, "E1.1" if slot["role"] == "same_family" else "E1.2", 0)
        if slot["role"] == "cross_family":
            groups = value["elements" if slot["rubric"] == "rubric10" else "categories"]
            groups.reverse()
            for _, items in _groups(value):
                items.reverse()
                for item in items:
                    item["unit_scores"].reverse()
    case = make_case(tmp_path, change_rating=change)
    _, report, receipt, _, _ = run_analysis(case)
    assert receipt["counts"]["accepted"] == 4, receipt["rows"]
    row = pair(report)
    assert row["gap"] == 0
    values = {row["item_id"]: row for row in report["observations"] if row["rubric"] == "rubric10"}
    assert (values["E1.1"]["same_score"], values["E1.1"]["cross_score"]) == (0, 1)
    assert (values["E1.2"]["same_score"], values["E1.2"]["cross_score"]) == (1, 0)
    assert {key for key, row in values.items() if row["agrees"] is False} == {"E1.1", "E1.2"}
    group = next(row for row in report["agreement_groups"] if row["identity"]["rubric"] == "rubric10")
    assert group["metrics"]["agreeing"] == group["metrics"]["n"] - 2
    assert group["metrics"]["kappa"] < 1


@pytest.mark.parametrize("scale", ["fixed_percentage_points", "adjusted_percentage_points"])
def test_percentages_come_from_exact_captured_maxima_not_accepted_rounded_payload(tmp_path, scale):
    def change(value, slot):
        _score(value, "E1.1" if slot["rubric"] == "rubric10" else "Q1", 0)
        total = value["overall_score"]["total_points"]
        cap = value["overall_score"]["adjusted_max_points"]
        value["overall_score"]["normalized_percentage"] = 100 * total / cap + (
            0.05 if slot["role"] == "same_family" else -0.05)
    case = make_case(tmp_path, change_rating=change)
    _, report, receipt, _, _ = run_analysis(case, policy(case, scale=scale))
    assert receipt["counts"]["accepted"] == 4, receipt["rows"]
    for row in report["pairs"]:
        assert row["gap"] == 0
        same, cross = (row["scores"][role] for role in panels.ROLES)
        assert same == cross
        for score in (same, cross):
            assert score["fixed_percentage"] == pytest.approx(100 * score["total_points"] / score["max_points"])
            assert score["adjusted_percentage"] == pytest.approx(100 * score["total_points"] / score["adjusted_max_points"])
        original = [case.rating_values[(row["record_id"], row["rubric"], role)]["overall_score"]["normalized_percentage"]
                    for role in panels.ROLES]
        assert original[0] - original[1] == pytest.approx(0.1)


def test_record_minimum_and_resource_observations_are_explicit_distinct_units(tmp_path):
    def change(value, slot):
        if slot["rubric"] == "rubric10":
            _score(value, "E1.1", [0, 1] if slot["role"] == "same_family" else [1, 0])
    case = make_case(tmp_path, collection=True, change_rating=change)
    _, record, accepted_record, _, _ = run_analysis(case, name="record-analysis")
    _, resource, accepted_resource, _, _ = run_analysis(case, policy(case, unit="resource_item"), name="resource-analysis")
    assert accepted_record["counts"]["accepted"] == accepted_resource["counts"]["accepted"] == 4
    a = [row for row in record["observations"] if row["rubric"] == "rubric10" and row["item_id"] == "E1.1"]
    b = [row for row in resource["observations"] if row["rubric"] == "rubric10" and row["item_id"] == "E1.1"]
    assert len(a) == 1 and a[0]["same_score"] == a[0]["cross_score"] == 0 and a[0]["agrees"] is True
    assert {row["resource_path"] for row in b} == {"#/resources/0", "#/resources/1"}
    assert [(row["same_score"], row["cross_score"]) for row in sorted(b, key=lambda row: row["resource_path"])] == [(0, 1), (1, 0)]
    assert all(row["agrees"] is False for row in b)
    assert len(resource["observations"]) == 2 * len(record["observations"])


def test_false_context_missing_context_and_excluded_items_remain_distinct(tmp_path):
    case = make_case(tmp_path, count=2, contexts=[False, None])
    _, report, receipt, _, _ = run_analysis(case)
    assert receipt["counts"]["accepted"] == 8
    records = case.registered["records"]
    assert records[0]["context"]["normalized"]["human_subjects"]["value"] is False
    assert records[1]["context"]["normalized"] == {}
    false_pair, unknown_pair = pair(report, rubric="rubric20"), pair(report, "record-1", "rubric20")
    assert "Q8" in false_pair["scores"]["same_family"]["excluded_items"]
    assert "Q8" not in unknown_pair["scores"]["same_family"]["excluded_items"]
    excluded = next(row for row in report["observations"] if row["record_id"] == "record-0"
                    and row["rubric"] == "rubric20" and row["item_id"] == "Q8")
    assert excluded["applicable"] is False
    assert excluded["same_score"] is excluded["cross_score"] is excluded["agrees"] is None
    assert report["readiness"] == receipt["readiness"]


def test_full_roster_keeps_rejected_missing_unregistered_and_unselected_pairs(tmp_path):
    def declaration(value):
        value["slots"] = [row for row in value["slots"] if not (
            row["record_id"] == "record-1" and row["rubric"] == "rubric10" and row["role"] == "same_family")]
    case = make_case(tmp_path, count=2, change_declaration=declaration)
    case.submission["submissions"] = [row for row in case.submission["submissions"] if not (
        row["record_id"] == "record-0" and row["rubric"] == "rubric20" and row["role"] == "cross_family")]
    bad = case.submission["submissions"][0]
    (case.ratings_dir / bad["result"]["path"]).write_bytes(b"not-json\n")
    bad["result"]["sha256"] = sha256(b"not-json\n")
    declaration = policy(case)
    declaration["record_ids"] = ["record-0"]
    declaration["uncertainty"]["blocks"] = [{"block_id": "b0", "record_ids": ["record-0"]}]
    declaration["uncertainty"]["strata"] = [{"stratum_id": "all", "record_ids": ["record-0"]}]
    _, report, receipt, _, _ = run_analysis(case, declaration)
    assert receipt["counts"] == {"selected": 8, "accepted": 5, "rejected": 1, "missing": 2, "unsupported": 0}
    assert len(report["slots"]) == 8 and len(report["pairs"]) == 4
    assert [row["state"] for row in report["slots"]] == [row["state"] for row in receipt["rows"]]
    assert not pair(report)["score_pair_complete"]
    assert not pair(report, rubric="rubric20")["score_pair_complete"]
    assert not pair(report, "record-1")["selected"]
    assert not pair(report, "record-1")["score_pair_complete"]
    assert pair(report, "record-1", "rubric20")["score_pair_complete"]
    assert all(row["record_id"] == "record-0" for row in report["observations"])


def test_all_missing_ratings_keep_registered_groups_and_zero_denominators(tmp_path):
    case = make_case(tmp_path, count=2)
    case.submission["submissions"] = []
    _, report, receipt, _, _ = run_analysis(case)
    assert receipt["counts"]["missing"] == receipt["counts"]["selected"] == 8
    assert len(report["pairs"]) == 4 and len(report["slots"]) == 8
    assert not any(row["score_pair_complete"] for row in report["pairs"])
    assert report["agreement_groups"] and report["gap_groups"]
    for group in report["agreement_groups"]:
        assert group["metrics"]["n"] == group["metrics"]["agreeing"] == 0
        assert group["metrics"]["observed_agreement"] is group["metrics"]["kappa"] is None
        assert group["metrics"]["agreement_reason"] and group["metrics"]["kappa_reason"]
    for group in report["gap_groups"]:
        assert group["metrics"]["n"] == 0 and group["metrics"]["mean"] is None
        assert group["metrics"]["reason"]


def test_unsupported_saved_slot_is_retained_without_reinterpreting_its_payload(tmp_path):
    def unknown_model(value):
        value["slots"][0].update(model=None, family=None)
    case = make_case(tmp_path, change_declaration=unknown_model)
    _, report, receipt, _, _ = run_analysis(case)
    assert receipt["counts"] == {"selected": 4, "accepted": 3, "rejected": 0, "missing": 0, "unsupported": 1}
    assert len(report["slots"]) == 4 and report["slots"][0]["state"] == "unsupported"
    assert pair(report)["score_pair_complete"] is False and pair(report)["gap"] is None
    assert pair(report)["scores"]["same_family"] is None
    assert pair(report)["gap_unavailable_reasons"]


@pytest.mark.parametrize("missing_identity", ["generator", "rater", "route"])
def test_complete_raw_pairs_do_not_get_family_attribution_from_role_labels_alone(tmp_path, missing_identity):
    def change(value):
        if missing_identity == "generator":
            value["records"][0]["generator"] = {"model": "unknown-generator", "family": None}
        else:
            for slot in value["slots"]:
                slot[missing_identity] = None
    case = make_case(tmp_path, change_declaration=change)
    _, report, receipt, _, _ = run_analysis(case)
    assert receipt["counts"]["accepted"] == 4
    for row in report["pairs"]:
        assert row["score_pair_complete"] is True and row["attributed_role_pair"] is False
        assert row["attribution_reasons"] and row["gap"] is None and row["gap_unavailable_reasons"]


def test_registered_role_mislabel_is_refused_before_any_analysis(tmp_path):
    def wrong(value):
        value["slots"][0].update(model="openai:gpt-5", family="gpt")
    with pytest.raises(ValueError, match="role contradicts"):
        make_case(tmp_path, change_declaration=wrong)
    assert not (tmp_path / "panel").exists()


def test_actual_ordered_rater_declarations_split_groups_even_with_same_role_labels(tmp_path):
    def change(value):
        for row in value["slots"]:
            if row["record_id"] == "record-1":
                row["rater"] += "-second"
                row["route"] = "other-offline-route"
    case = make_case(tmp_path, count=2, change_declaration=change)
    _, report, receipt, _, _ = run_analysis(case)
    assert receipt["counts"]["accepted"] == 8
    groups = [row for row in report["gap_groups"] if row["identity"]["rubric"] == "rubric10"]
    assert len(groups) == 2 and {tuple(row["record_ids"]) for row in groups} == {("record-0",), ("record-1",)}
    assert {row["identity"]["raters"]["same_family"]["route"] for row in groups} == {"offline-fixture", "other-offline-route"}


@pytest.mark.parametrize("mutation", ["unknown_key", "missing_seed", "duplicate_record", "missing_partition", "split_identical_inputs"])
def test_closed_spec_and_known_dependence_refuse_without_output(tmp_path, mutation):
    case = make_case(tmp_path, count=2, same_input=mutation == "split_identical_inputs")
    declaration = policy(case)
    if mutation == "unknown_key":
        declaration["default_policy"] = True
    elif mutation == "missing_seed":
        del declaration["uncertainty"]["seed"]
    elif mutation == "duplicate_record":
        declaration["record_ids"].append("record-0")
    elif mutation == "missing_partition":
        declaration["uncertainty"]["blocks"].pop()
    before = snapshot(case.panel_dir), snapshot(case.root)
    with pytest.raises(ValueError):
        prepare(case, declaration)
    assert not (tmp_path / "spec").exists()
    assert before == (snapshot(case.panel_dir), snapshot(case.root))


def test_identical_input_block_and_cross_stratum_conflict_preserve_point_rows(tmp_path):
    case = make_case(tmp_path, count=2, same_input=True)
    declaration = policy(case, blocks=[{"block_id": "shared", "record_ids": ["record-0", "record-1"]}],
                         strata=[{"stratum_id": "a", "record_ids": ["record-0"]},
                                 {"stratum_id": "b", "record_ids": ["record-1"]}])
    _, report, receipt, _, _ = run_analysis(case, declaration)
    assert receipt["counts"]["accepted"] == 8
    assert all(row["gap"] == 0 for row in report["pairs"])
    assert len(report["pairs"]) == 4
    for group in report["agreement_groups"] + report["gap_groups"]:
        assert group["metrics"]["n"] > 0
        uncertainty = group["uncertainty"]
        assert uncertainty["unavailable_reasons"]
        assert all(row["lower"] is None and row["upper"] is None for row in uncertainty["intervals"].values())


@pytest.mark.parametrize("target", ["analysis_metric", "authority_flag", "captured_input", "saved_acceptance"])
def test_recheck_reconstructs_claims_and_refuses_tampering(tmp_path, target):
    case = make_case(tmp_path)
    directory, _, _, _, _ = run_analysis(case)
    manifest = directory / "analysis.json"
    value = json.loads(manifest.read_bytes())
    if target == "analysis_metric":
        value["gap_groups"][0]["metrics"]["mean"] = 37
    elif target == "authority_flag":
        value["scientific_eligibility"] = True
    else:
        pin = (case.registered["records"][0]["input"] if target == "captured_input" else value["results"])
        artifact = directory / "artifacts" / pin["sha256"]
        assert artifact.is_file()
        artifact.write_bytes(artifact.read_bytes() + b" ")
    if target in ("analysis_metric", "authority_flag"):
        manifest.write_bytes(canonical(value))
    before = snapshot(directory)
    with pytest.raises(ValueError):
        analysis.recheck_panel_analysis(directory)
    assert snapshot(directory) == before


@pytest.mark.parametrize("operation", ["specification", "analysis"])
def test_mid_artifact_failure_is_atomic_and_preserves_all_inputs(tmp_path, monkeypatch, operation):
    case = make_case(tmp_path)
    results, _ = accept(case)
    specification, _ = prepare(case)
    declaration = tmp_path / "another-declaration.json"
    declaration.write_bytes(canonical(policy(case)))
    before = snapshot(tmp_path)
    original = analysis._write_bytes
    sentinel = OSError("synthetic second artifact write failure")
    artifacts = []
    def fail(path, raw):
        if Path(path).parent.name == "artifacts":
            artifacts.append(str(path))
            if len(artifacts) == 2:
                raise sentinel
        return original(path, raw)
    monkeypatch.setattr(analysis, "_write_bytes", fail)
    output = tmp_path / "never-visible"
    with pytest.raises(OSError) as caught:
        if operation == "specification":
            analysis.prepare_analysis_spec(case.panel_dir, declaration, output)
        else:
            analysis.analyze_panel_results(specification, results, output)
    assert caught.value is sentinel and len(artifacts) == 2
    assert not output.exists() and snapshot(tmp_path) == before


@pytest.mark.parametrize("winner_has_content", [False, True], ids=["empty-winner", "nonempty-winner"])
def test_concurrent_existing_output_is_not_overwritten_after_staging(tmp_path, monkeypatch, winner_has_content):
    case = make_case(tmp_path)
    results, _ = accept(case)
    specification, _ = prepare(case)
    before = snapshot(case.panel_dir), snapshot(results), snapshot(specification)
    original = analysis._rename_new
    output = tmp_path / "winner"
    def raced(source, destination):
        Path(destination).mkdir()
        if winner_has_content:
            (Path(destination) / "unrelated.txt").write_bytes(b"concurrent winner\n")
        return original(source, destination)
    monkeypatch.setattr(analysis, "_rename_new", raced)
    with pytest.raises((ValueError, OSError)):
        analysis.analyze_panel_results(specification, results, output)
    assert output.is_dir()
    assert snapshot(output) == ({"unrelated.txt": b"concurrent winner\n"} if winner_has_content else {})
    assert before == (snapshot(case.panel_dir), snapshot(results), snapshot(specification))


def test_bootstrap_work_bound_refuses_real_complete_inputs_before_publication(tmp_path, monkeypatch):
    case = make_case(tmp_path, count=2)
    specification, _ = prepare(case)
    results, receipt = accept(case)
    assert receipt["counts"]["accepted"] == 8
    before = snapshot(tmp_path)
    monkeypatch.setattr(analysis, "MAX_BOOTSTRAP_WORK", 1)
    output = tmp_path / "too-much-work"
    with pytest.raises(ValueError, match="work bound"):
        analysis.analyze_panel_results(specification, results, output)
    assert not output.exists() and snapshot(tmp_path) == before


def test_actual_analysis_output_byte_bound_is_checked_before_publication(tmp_path, monkeypatch):
    case = make_case(tmp_path, count=2)
    directory, _, _, specification, results = run_analysis(case)
    size = len((directory / "analysis.json").read_bytes())
    before = snapshot(tmp_path)
    original = analysis._publish_new
    def bounded(output, capture, filename, document, **kwargs):
        # Restrict the actual final publisher, after ordinary complete input
        # reconstruction, so this cannot pass on an unrelated input-read bound.
        monkeypatch.setattr(analysis, "MAX_BYTES", size - 1)
        return original(output, capture, filename, document, **kwargs)
    monkeypatch.setattr(analysis, "_publish_new", bounded)
    output = tmp_path / "too-large"
    with pytest.raises(ValueError, match="manifest byte bound"):
        analysis.analyze_panel_results(specification, results, output)
    assert not output.exists() and snapshot(tmp_path) == before


def test_real_captured_rubric_preserves_numeric_score_keys_and_runs_complete_analysis(tmp_path):
    case = make_case(tmp_path)
    instrument = next(row for row in case.registered["instruments"] if row["rubric"] == "rubric20")
    raw = (case.panel_dir / "artifacts" / instrument["resources"]["rubric"]["sha256"]).read_bytes()
    parsed = analysis._instrument_yaml(raw)
    question = next(row for row in parsed["d4d_evaluation_rubric"]["rubric"] if row["id"] == 1)
    assert list(question["scoring"]) == [0, 3, 5]
    assert all(type(key) is int for key in question["scoring"])
    before = snapshot(case.panel_dir)
    _, report, receipt, _, _ = run_analysis(case)
    assert receipt["counts"]["accepted"] == 4
    assert all(row["score_pair_complete"] for row in report["pairs"])
    assert {tuple(row["identity"]["domain"]) for row in report["agreement_groups"]} == {(0, 1), (0, 3, 5)}
    assert snapshot(case.panel_dir) == before


def test_instrument_scalar_key_types_are_preserved_without_string_coercion():
    raw = b"0: integer\n'0': string\n3.5: finite-float\ntrue: boolean\nnull: null-key\n"
    value = analysis._instrument_yaml(raw)
    assert [(type(key), key, item) for key, item in value.items()] == [
        (int, 0, "integer"), (str, "0", "string"), (float, 3.5, "finite-float"),
        (bool, True, "boolean"), (type(None), None, "null-key")]


@pytest.mark.parametrize("raw", [
    b"a: first\na: second\n",
    b"0: first\n0: second\n",
    b"1: first\n1.0: second\n",
    b"true: first\n1: second\n",
    b"a: [unterminated\n",
    b"!!python/tuple [1, 2]\n",
    b"a: &shared [1]\nb: *shared\n",
    b"a: {<<: {x: 1}}\n",
    b"? [1, 2]\n: unhashable\n",
    b"a: .inf\n",
    b"a: .nan\n",
    b"\xff\n",
], ids=["duplicate-text", "duplicate-int", "int-float-collision", "bool-int-collision",
        "malformed", "unsafe-tag", "alias", "merge", "unhashable-key", "infinity", "nan", "invalid-utf8"])
def test_instrument_yaml_refuses_ambiguous_or_unsafe_data(raw):
    with pytest.raises(ValueError):
        analysis._instrument_yaml(raw)


@pytest.mark.parametrize("bound", ["bytes", "nodes", "depth"])
def test_instrument_yaml_enforces_each_bound_on_actual_input(monkeypatch, bound):
    raw = b"a:\n  b:\n    c: [1, 2, 3, 4]\n"
    if bound == "bytes":
        monkeypatch.setattr(analysis, "MAX_BYTES", len(raw) - 1)
    elif bound == "nodes":
        monkeypatch.setattr(analysis, "MAX_INSTRUMENT_NODES", 3)
    else:
        monkeypatch.setattr(analysis, "MAX_INSTRUMENT_DEPTH", 2)
    with pytest.raises(ValueError):
        analysis._instrument_yaml(raw)


@pytest.mark.parametrize("operation", ["prepare", "analyze"])
def test_public_output_nul_is_rejected_before_staging_or_truncated_publication(tmp_path, monkeypatch, operation):
    case = make_case(tmp_path)
    results, _ = accept(case)
    specification, _ = prepare(case)
    declaration = tmp_path / "nul-declaration.json"
    declaration.write_bytes(canonical(policy(case)))
    before = snapshot(tmp_path)
    original = analysis.tempfile.mkdtemp
    staging = []
    def record_stage(*args, **kwargs):
        staging.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(analysis.tempfile, "mkdtemp", record_stage)
    output = tmp_path / "truncated\0suffix"
    with pytest.raises(ValueError, match="NUL"):
        if operation == "prepare":
            analysis.prepare_analysis_spec(case.panel_dir, declaration, output)
        else:
            analysis.analyze_panel_results(specification, results, output)
    assert not staging
    assert not (tmp_path / "truncated").exists()
    assert not list(tmp_path.glob(".cross-family-analysis-*"))
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("argument", ["source", "destination"])
def test_native_no_replace_boundary_rejects_nul_in_either_argument(tmp_path, monkeypatch, argument):
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    (source / "sentinel").write_bytes(b"original source\n")
    before = snapshot(tmp_path)
    native_calls = []
    original = analysis.ctypes.CDLL
    def record_native(*args, **kwargs):
        native_calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(analysis.ctypes, "CDLL", record_native)
    args = [source, destination]
    index = 0 if argument == "source" else 1
    args[index] = Path(str(args[index]) + "\0suffix")
    with pytest.raises(ValueError, match="NUL"):
        analysis._rename_new(*args)
    assert not native_calls and source.is_dir() and not destination.exists()
    assert snapshot(tmp_path) == before


def test_historical_v2_slots_remain_unsupported_in_analysis(tmp_path):
    def historical(value):
        for instrument in value["instruments"]:
            instrument["version"] = "2.0"
    case = make_case(tmp_path, change_declaration=historical)
    _, report, receipt, _, _ = run_analysis(case)
    assert receipt["counts"] == {"selected": 4, "accepted": 0, "rejected": 0, "missing": 0, "unsupported": 4}
    assert len(report["slots"]) == 4 and all(row["state"] == "unsupported" for row in report["slots"])
    assert all(row["version"] == "2.0" and not row["score_pair_complete"] and row["gap"] is None
               for row in report["pairs"])
    assert all(row["metrics"]["n"] == 0 for row in report["agreement_groups"] + report["gap_groups"])


def test_empty_selected_subset_preserves_original_roster_without_metrics(tmp_path):
    case = make_case(tmp_path)
    declaration = policy(case)
    declaration["record_ids"] = []
    declaration["uncertainty"].update(blocks=[], strata=[])
    _, report, receipt, _, _ = run_analysis(case, declaration)
    assert receipt["counts"]["accepted"] == 4
    assert len(report["slots"]) == 4 and len(report["pairs"]) == 2
    assert all(row["score_pair_complete"] and not row["selected"] and row["gap"] is None for row in report["pairs"])
    assert report["observations"] == report["agreement_groups"] == report["gap_groups"] == []
    assert report["counts"]["selected_pairs"] == 0 and report["counts"]["unselected_pairs"] == 2
    assert report["scientific_eligibility"] is report["execution_authorized"] is False
