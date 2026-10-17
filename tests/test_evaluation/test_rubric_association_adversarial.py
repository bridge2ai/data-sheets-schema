"""Independent captured-identity controls; no provider calls or rubric scoring."""
from copy import deepcopy
import json
import shutil

import pytest

from data_sheets_schema import top_level_fitness_results as fit
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema.support_plan import canonical, sha256
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_rubric_association_index import prepare_case, indexed


@pytest.mark.parametrize("field", ["rubric", "project", "method", "d4d_file", "version",
                                  "job_id", "metadata.job_id", "metadata.label",
                                  "metadata.rubric_sha256", "metadata.evidence_authority_sha256",
                                  "metadata.schema_sha256", "evaluation_metadata.rubric_hash"])
def test_known_conflicting_identity_is_not_hidden_by_missing_historical_context(fixture, tmp_path, field):
    def change(roster, results):
        job = roster["jobs"][0]
        job.pop("applicability_context")
        result = results[job["rubric"]]
        if "." in field:
            section, key = field.split(".")
            result.setdefault(section, {})[key] = "0" * 64 if key.endswith(("sha256", "hash")) else "foreign"
        else:
            result[field] = "foreign"
    case = prepare_case(fixture, tmp_path, change=change)
    value = indexed(case, tmp_path / "index")
    row = next(row for row in value["rubric_rows"] if row["job_id"] == case["roster"]["jobs"][0]["id"])
    assert row["state"] == "mismatched"
    assert row["unsupported"] and any(item["field"] == "result." + field for item in row["conflicts"])
    assert value["rubric_counts"] == {"selected": 2, "associated": 1, "missing": 0, "mismatched": 1, "unsupported": 0}
    assert fit.recheck_index(tmp_path / "index") == value


def test_distinct_primary_jobs_for_one_record_rubric_remain_individual_rows(fixture, tmp_path):
    def change(roster, _results):
        extra = deepcopy(roster["jobs"][0])
        extra.update(id="separately-declared-primary", output="another-primary.json")
        roster["jobs"].append(extra)
        repeat = deepcopy(extra)
        repeat.update(id="repeatability-only", purpose="repeatability", output="repeatability-only.json")
        roster["jobs"].append(repeat)
        roster["jobs"].reverse()
    case = prepare_case(fixture, tmp_path, change=change)
    value = indexed(case, tmp_path / "index")
    assert value["rubric_counts"] == {"selected": 3, "associated": 3, "missing": 0, "mismatched": 0, "unsupported": 0}
    assert {row["job_id"] for row in value["rubric_rows"]} == {
        job["id"] for job in case["roster"]["jobs"] if job["purpose"] == "primary"}
    assert len([row for row in value["rubric_rows"] if row["rubric"] == "rubric10-semantic"]) == 2
    assert all(row["rating_accepted"] is False for row in value["rubric_rows"])
    assert fit.recheck_index(tmp_path / "index") == value


def test_semantically_equal_reencoded_plan_is_not_the_selected_raw_plan(fixture, tmp_path):
    case = prepare_case(fixture, tmp_path)
    other = tmp_path / "reencoded-plan"
    shutil.copytree(case["plan"], other)
    original = (other / "manifest.json").read_bytes()
    reencoded = json.dumps(json.loads(original), indent=3).encode() + b"\n"
    assert reencoded != original
    (other / "manifest.json").write_bytes(reencoded)
    output = tmp_path / "refused"
    with pytest.raises(fit.ResultError, match="rubric plan differs"):
        fit.build_index(case["descriptor"], [], output, rubric_associations=True, rubric_plan=other)
    assert not output.exists()
    assert (case["plan"] / "manifest.json").read_bytes() == original


@pytest.mark.parametrize("fault", ["captured_bytes", "derived_count", "result_pin"])
def test_replay_refuses_corrupt_artifacts_and_forged_derived_joins(fixture, tmp_path, fault):
    case = prepare_case(fixture, tmp_path)
    output = tmp_path / "index"
    value = indexed(case, output)
    pin = value["rubric_rows"][0]["result_artifact"]
    if fault == "captured_bytes":
        artifact = output / "artifacts" / pin["sha256"]
        artifact.write_bytes(artifact.read_bytes() + b" ")
    else:
        if fault == "derived_count":
            value["rubric_counts"].update(associated=999, selected=999)
        else:
            raw = b'{"assertion":"replacement declared by index alone"}'
            replacement = {"sha256": sha256(raw), "bytes": len(raw)}
            (output / "artifacts" / replacement["sha256"]).write_bytes(raw)
            value["rubric_rows"][0]["result_artifact"] = replacement
        (output / "index.json").write_bytes(canonical(value))
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    with pytest.raises(fit.ResultError):
        fit.recheck_index(output)
    assert before == {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}


def test_explicit_false_preserves_every_v1_published_byte(fixture, tmp_path):
    case = prepare_case(fixture, tmp_path)
    first, second = tmp_path / "omitted", tmp_path / "explicit-false"
    fit.build_index(case["descriptor"], [], first)
    fit.build_index(case["descriptor"], [], second, rubric_associations=False)
    tree = lambda root: {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert tree(first) == tree(second)
    assert json.loads((first / "index.json").read_bytes())["format"] == fit.INDEX_FORMAT


@pytest.mark.parametrize("mode,state", [("absent", "associated"), ("matching", "associated"),
    ("conflicting", "mismatched"), ("conflict_with_missing_context", "mismatched"),
    ("conflict_malformed_body", "mismatched"),
    ("malformed", "unsupported"), ("malformed_null", "unsupported"), ("missing_result", "missing")])
def test_roster_output_pin_is_reconciled_with_actual_planner_capture_and_portable_replay(
        fixture, tmp_path, monkeypatch, mode, state):
    def change(roster, results):
        job = roster["jobs"][0]
        pin = sha256(canonical(results[job["rubric"]]))
        if mode == "absent":
            return
        if mode.startswith("conflict"):
            pin = "0" * 64
        elif mode == "malformed":
            pin = "not-a-sha256"
        elif mode == "malformed_null":
            pin = None
        roster["pinned_files"][job["output"]] = pin
        if mode == "conflict_with_missing_context":
            job.pop("applicability_context")
        elif mode == "conflict_malformed_body":
            results[job["rubric"]] = b'{"malformed":'
    case = prepare_case(fixture, tmp_path, change=change,
                        present=("rubric20-semantic",) if mode == "missing_result" else
                                ("rubric10-semantic", "rubric20-semantic"))
    output = tmp_path / "index"
    value = indexed(case, output)
    job = case["roster"]["jobs"][0]
    row = next(row for row in value["rubric_rows"] if row["job_id"] == job["id"])
    assert row["state"] == state
    assert row["roster_output_pin"] == {"present": mode != "absent",
        "sha256": case["roster"]["pinned_files"].get(job["output"])}
    assert row["result_pin_basis"] == ("captured_plan_only" if mode == "absent"
                                        else "captured_plan_with_roster_output_declaration")
    assert value["rubric_counts"]["selected"] == 2
    assert sum(value["rubric_counts"][key] for key in ("associated", "missing", "mismatched", "unsupported")) == 2
    assert row["rating_accepted"] is row["scientific_scoring_eligible"] is False
    if mode in ("conflict_with_missing_context", "conflict_malformed_body"):
        assert row["conflicts"] and row["unsupported"]
    if mode == "missing_result":
        assert row["result_artifact"] is None and value["rubric_counts"]["missing"] == 1
    moved = tmp_path / "portable-index"
    shutil.copytree(output, moved)
    for path in (case["root"], case["plan"], case["descriptor"], output):
        path.rename(path.with_name(path.name + "-unavailable"))
    original = saved._file
    def captured_only(path, limit):
        assert path.is_relative_to(moved), path
        return original(path, limit)
    monkeypatch.setattr(saved, "_file", captured_only)
    assert fit.recheck_index(moved) == value
