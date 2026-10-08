"""Captured declaration association is deliberately weaker than rating acceptance."""
import copy
import json
from pathlib import Path
import shutil

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import rubric_association as rubric
from data_sheets_schema import top_level_fitness_results as fit
from data_sheets_schema.evaluation_context import context_digest, normalize_context
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.support_plan import canonical, sha256
from data_sheets_schema.cli.evaluate import evaluate
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_nested_support_plan import build
from tests.test_evaluation.test_top_level_fitness_results import prepared  # noqa: F401
from tests.test_evaluation.test_nested_support_execution import peer  # noqa: F401
from tests.test_evaluation.test_support_execution_index import case as support_case  # noqa: F401


def prepare_case(fixture, tmp_path, *, change=None, present=("rubric10-semantic", "rubric20-semantic"), v4=False):
    root, plan = fixture
    roster = json.loads((root / "roster.json").read_bytes())
    roster["instruments"] = {}
    results = {}
    for job in roster["jobs"]:
        job["rubric"] += "-semantic"
        selected = select_semantic_instrument(job["rubric"], "4.0" if v4 and job["rubric"] == "rubric20-semantic" else "3.0")
        job["agent"] = selected.agent
        job["applicability_context"] = {"human_subjects": False}
        for path in (selected.definition_path, selected.rubric_path, selected.schema_path, selected.evidence_authority_path):
            # Declared arbitrary hashes make no assertion that shipped instrument bytes were captured.
            roster["pinned_files"][path] = sha256(path.encode())
        instrument = {"version": selected.version, "agent": selected.agent,
                      "definition": selected.definition_path, "rubric": selected.rubric_path,
                      "schema": selected.schema_path, "definition_sha256": roster["pinned_files"][selected.definition_path]}
        if selected.version == "4.0":
            path = select_semantic_instrument("rubric20-semantic", "3.0").definition_path
            roster["pinned_files"][path] = sha256(path.encode())
            instrument.update(predecessor_definition=path, predecessor_sha256=roster["pinned_files"][path])
        roster["instruments"][job["rubric"]] = instrument
        context = normalize_context(job["applicability_context"])
        results[job["rubric"]] = {"rubric": job["rubric"], "version": selected.version,
            "project": job["project"], "label": job["label"], "method": job["method"], "d4d_file": job["input"],
            "metadata": {"input_sha256": roster["pinned_files"][job["input"]],
                "instrument_kind": "agent_definition", "instrument_sha256": instrument["definition_sha256"],
                "rubric_sha256": roster["pinned_files"][selected.rubric_path],
                "evidence_authority_sha256": roster["pinned_files"][selected.evidence_authority_path],
                "context_sha256": context_digest(context)},
            "applicability_context": context, "evaluation_scope": {"units": [{"path": "#", "id": "ex:harbor"}],
                "policy": "single_dataset", "collection_metadata_inherited": False}}
    if change:
        change(roster, results)
    (root / "roster.json").write_bytes(canonical(roster))
    for job in roster["jobs"]:
        if job["rubric"] in present:
            value = results[job["rubric"]]
            (root / job["output"]).write_bytes(value if isinstance(value, bytes) else canonical(value))
    manifest = build(fixture)
    selections = [{"target_id": row["id"], "attempt_id": f"fitness-{i}"}
                  for i, row in enumerate(manifest["targets"]) if row["axis"] == "fitness"]
    descriptor = tmp_path / "descriptor"
    fit.prepare(plan, descriptor, selections=selections, protocol=fit.FORMAT)
    return {"root": root, "plan": plan, "descriptor": descriptor, "manifest": manifest,
            "roster": roster, "results": results, "selections": selections}


def indexed(case, output):
    return fit.build_index(case["descriptor"], [], output, rubric_associations=True, rubric_plan=case["plan"])


def test_actual_cli_captured_only_relocation_without_rating_acceptance(fixture, tmp_path, monkeypatch):
    case = prepare_case(fixture, tmp_path, v4=True)
    runner = CliRunner()
    output = tmp_path / "index"
    result = runner.invoke(evaluate, ["fitness-results", "index", "--descriptor", str(case["descriptor"]),
        "--rubric-associations", "--rubric-plan", str(case["plan"]), "--output", str(output)])
    assert result.exit_code == 0, result.output
    value = json.loads(result.output)
    assert value["format"] == fit.INDEX_FORMAT_V3
    assert value["rubric_counts"] == {"selected": 2, "associated": 2, "missing": 0, "mismatched": 0, "unsupported": 0}
    assert value["rubric_rating_acceptance"] is value["scientific_scoring_eligible"] is False
    assert all(row["rating_accepted"] is row["scientific_scoring_eligible"] is False for row in value["rubric_rows"])
    assert value["strata"]["fitness_top_level"]["missing"] == len(case["selections"])
    assert value["readiness"] == case["manifest"]["readiness"]
    # These minimal declarations have no rubric scores and are not valid ratings.
    assert all("elements" not in raw and "categories" not in raw for raw in case["results"].values())
    moved = tmp_path / "portable"
    shutil.copytree(output, moved)
    for path in (case["root"], case["plan"], case["descriptor"], output):
        path.rename(path.with_name(path.name + "-unavailable"))
    original = Path.read_bytes
    def captured_only(path):
        assert path.is_relative_to(moved), path
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", captured_only)
    assert fit.recheck_index(moved) == value


def test_default_index_unchanged_and_no_implicit_plan_fallback(fixture, tmp_path):
    case = prepare_case(fixture, tmp_path)
    value = fit.build_index(case["descriptor"], [], tmp_path / "default")
    explicit = fit.build_index(case["descriptor"], [], tmp_path / "false", rubric_associations=False)
    assert value == explicit
    assert value["format"] == fit.INDEX_FORMAT and not any(key.startswith("rubric_") for key in value)
    output = tmp_path / "without-plan"
    with pytest.raises(fit.ResultError, match="cannot read evidence file"):
        fit.build_index(case["descriptor"], [], output, rubric_associations=True)
    assert not output.exists()


@pytest.mark.parametrize("mode,state", [("absent", "missing"), ("malformed", "unsupported"),
    ("historical_context", "unsupported"), ("wrong_input", "mismatched"), ("wrong_alias", "mismatched"),
    ("missing_context_and_wrong_label", "mismatched"), ("context_false_vs_missing", "mismatched"),
    ("scope_omitted_member", "mismatched"), ("inherited_zero", "mismatched"),
    ("missing_version", "unsupported"), ("old_version", "unsupported"), ("wrong_agent", "mismatched"),
    ("definition_pin_conflict", "mismatched"), ("definition_and_other_pin_conflict", "mismatched")])
def test_rows_remain_in_denominator_for_partial_or_conflicting_declarations(fixture, tmp_path, mode, state):
    key = "rubric10-semantic"
    def change(roster, results):
        row = results[key]
        job = roster["jobs"][0]
        inst = roster["instruments"][key]
        if mode == "malformed": results[key] = b'{"rubric":1,"rubric":2}'
        elif mode == "historical_context": job.pop("applicability_context")
        elif mode == "wrong_input": row["metadata"]["input_sha256"] = "0" * 64
        elif mode == "wrong_alias": row["evaluation_metadata"] = {"d4d_file_hash": "0" * 64}
        elif mode == "missing_context_and_wrong_label":
            job.pop("applicability_context")
            row["metadata"]["replicate_label"] = "another"
        elif mode == "context_false_vs_missing": row["applicability_context"] = {}
        elif mode == "scope_omitted_member": row["evaluation_scope"]["units"] = []
        elif mode == "inherited_zero": row["evaluation_scope"]["collection_metadata_inherited"] = 0
        elif mode == "missing_version": inst.pop("version")
        elif mode == "old_version": inst["version"] = row["version"] = "2.0"
        elif mode == "wrong_agent": job["agent"] = "other-agent"
        elif mode.startswith("definition"):
            roster["pinned_files"][inst["definition"]] = "0" * 64
            if mode == "definition_and_other_pin_conflict": job.pop("applicability_context")
    case = prepare_case(fixture, tmp_path, change=change,
                        present=("rubric20-semantic",) if mode == "absent" else (key, "rubric20-semantic"))
    value = indexed(case, tmp_path / "index")
    assert value["rubric_counts"]["selected"] == 2
    assert value["rubric_counts"][state] == 1 and value["rubric_counts"]["associated"] == 1
    assert next(row for row in value["rubric_rows"] if row["rubric"] == key)["state"] == state
    assert fit.recheck_index(tmp_path / "index") == value


def test_exact_plan_pin_and_missing_declared_blob_refuse_without_publication(fixture, tmp_path):
    case = prepare_case(fixture, tmp_path)
    copy_plan = tmp_path / "different-plan"
    shutil.copytree(case["plan"], copy_plan)
    manifest = copy.deepcopy(case["manifest"])
    manifest["unrelated"] = "different raw plan"
    (copy_plan / "manifest.json").write_bytes(canonical(manifest))
    with pytest.raises(fit.ResultError, match="rubric plan differs"):
        fit.build_index(case["descriptor"], [], tmp_path / "bad-plan", rubric_associations=True, rubric_plan=copy_plan)
    assert not (tmp_path / "bad-plan").exists()
    pin = case["manifest"]["records"][0]["rubric_join_jobs"][0]["result_artifact"]
    (case["plan"] / "artifacts" / pin["sha256"]).unlink()
    with pytest.raises(fit.ResultError, match="cannot read evidence file"):
        indexed(case, tmp_path / "lost-blob")
    assert not (tmp_path / "lost-blob").exists()


@pytest.mark.parametrize("mode", ["drop_job", "duplicate_job", "foreign_job", "wrong_output", "wrong_rubric"])
def test_join_membership_cannot_shrink_or_replace_roster_denominator(fixture, tmp_path, mode):
    case = prepare_case(fixture, tmp_path)
    manifest = copy.deepcopy(case["manifest"])
    rows = manifest["records"][0]["rubric_join_jobs"]
    if mode == "drop_job": rows.pop()
    elif mode == "duplicate_job": rows[1] = copy.deepcopy(rows[0])
    elif mode == "foreign_job": rows[0]["id"] = "foreign"
    elif mode == "wrong_output": rows[0]["output"] = "another.json"
    else: rows[0]["rubric"] = "another"
    (case["plan"] / "manifest.json").write_bytes(canonical(manifest))
    descriptor = tmp_path / "changed-descriptor"
    fit.prepare(case["plan"], descriptor, selections=case["selections"], protocol=fit.FORMAT)
    with pytest.raises(fit.ResultError, match="rubric join"):
        fit.build_index(descriptor, [], tmp_path / "invalid", rubric_associations=True, rubric_plan=case["plan"])
    assert not (tmp_path / "invalid").exists()


@pytest.mark.parametrize("change", [lambda row: row.update(state="associated"),
    lambda row: row.update(rating_accepted=True), lambda row: row.update(scientific_scoring_eligible=True)])
def test_saved_association_flags_are_reconstructed(fixture, tmp_path, change):
    case = prepare_case(fixture, tmp_path, present=("rubric20-semantic",))
    output = tmp_path / "index"
    value = indexed(case, output)
    change(next(row for row in value["rubric_rows"] if row["state"] == "missing"))
    (output / "index.json").write_bytes(canonical(value))
    with pytest.raises(fit.ResultError, match="differs from reconstructed"):
        fit.recheck_index(output)


def test_roster_job_bound_and_output_bound_preflight(fixture, tmp_path, monkeypatch):
    case = prepare_case(fixture, tmp_path)
    monkeypatch.setattr(rubric, "MAX_ROSTER_JOBS", 1)
    with pytest.raises(fit.ResultError, match="job bound"):
        indexed(case, tmp_path / "too-many")
    assert not (tmp_path / "too-many").exists()
    monkeypatch.setattr(rubric, "MAX_ROSTER_JOBS", 10_000)
    monkeypatch.setattr(fit, "MAX_DOCUMENT_BYTES", 1)
    with pytest.raises(fit.ResultError, match="document exceeds byte bound"):
        indexed(case, tmp_path / "too-large")
    assert not (tmp_path / "too-large").exists()


def test_selected_records_only_with_no_reads_of_unselected_result_pins(fixture, tmp_path):
    root = fixture[0]
    def change(roster, _results):
        raw = (root / "record.yaml").read_bytes()
        (root / "other.yaml").write_bytes(raw)  # Same values/bytes, distinct registered lineage.
        provenance = yaml.safe_load((root / "provenance.yaml").read_bytes())
        provenance["run"]["label"] = "condition_rep2"
        (root / "other-provenance.yaml").write_text(yaml.safe_dump(provenance))
        roster["pinned_files"]["other.yaml"] = sha256(raw)
        for original in list(roster["jobs"]):
            job = copy.deepcopy(original)
            job.update(id=original["id"] + "-other", input="other.yaml", output=original["output"] + ".other",
                       provenance="other-provenance.yaml", label="condition_rep2", generation_rep=2)
            roster["jobs"].append(job)
    case = prepare_case(fixture, tmp_path, change=change)
    selected = next(row for row in case["manifest"]["records"] if row["record"]["path"] == "record.yaml")
    other = next(row for row in case["manifest"]["records"] if row["record"]["path"] == "other.yaml")
    for row in other["rubric_join_jobs"]:
        row["result_artifact"] = {"sha256": "f" * 64, "bytes": 13}
    (case["plan"] / "manifest.json").write_bytes(canonical(case["manifest"]))
    subset = [row for row in case["selections"] if row["target_id"].startswith(selected["id"] + ":")]
    descriptor = tmp_path / "selected-descriptor"
    fit.prepare(case["plan"], descriptor, selections=subset, protocol=fit.FORMAT)
    case["descriptor"] = descriptor
    value = indexed(case, tmp_path / "index")
    assert value["rubric_counts"]["selected"] == value["rubric_counts"]["associated"] == 2
    assert {row["record_id"] for row in value["rubric_rows"]} == {selected["id"]}
    assert fit.recheck_index(tmp_path / "index") == value


def test_v2_remains_unchanged_and_v3_can_include_captured_support_execution(support_case, tmp_path):
    from data_sheets_schema import nested_support_execution as execution
    execution.run(support_case.registered)
    kwargs = {"support_execution": support_case.run}
    old = fit.build_index(support_case.fitness_descriptor, [], tmp_path / "v2", **kwargs)
    explicit = fit.build_index(support_case.fitness_descriptor, [], tmp_path / "explicit-v2",
                               rubric_associations=False, **kwargs)
    assert old == explicit and old["format"] == fit.INDEX_FORMAT_V2
    joined = fit.build_index(support_case.fitness_descriptor, [], tmp_path / "v3",
                             rubric_associations=True, **kwargs)
    assert joined["format"] == fit.INDEX_FORMAT_V3
    assert joined["rubric_counts"]["selected"] == joined["rubric_counts"]["missing"] == 2
    projected = {key: value for key, value in joined.items() if not key.startswith("rubric_")}
    projected["format"] = fit.INDEX_FORMAT_V2
    assert projected == old
    assert fit.recheck_index(tmp_path / "v2") == old
    assert fit.recheck_index(tmp_path / "v3") == joined


def test_scope_keeps_all_collection_members_and_boolean_identity(fixture, tmp_path):
    case = prepare_case(fixture, tmp_path)
    job = case["roster"]["jobs"][0]
    result = copy.deepcopy(case["results"][job["rubric"]])
    document = {"resources": [{"id": "one"}, {"id": "two"}]}
    result["evaluation_scope"] = {"units": [{"path": "#/resources/0", "id": "one"},
                                             {"path": "#/resources/1", "id": "two"}],
        "policy": "minimum_per_item_across_all_resource_datasets_v1", "collection_metadata_inherited": False}
    assert rubric.assess(result, job, case["roster"], document)["state"] == "associated"
    result["evaluation_scope"]["units"].pop()
    assert rubric.assess(result, job, case["roster"], document)["state"] == "mismatched"
    result["evaluation_scope"] = {"units": [{"path": "#", "id": 0}],
        "policy": "single_dataset", "collection_metadata_inherited": False}
    assert rubric.assess(result, job, case["roster"], {"id": False})["state"] == "mismatched"


def test_undeclared_extra_blob_cannot_supply_a_missing_result(fixture, tmp_path):
    case = prepare_case(fixture, tmp_path, present=("rubric20-semantic",))
    raw = canonical(case["results"]["rubric10-semantic"])
    (case["plan"] / "artifacts" / sha256(raw)).write_bytes(raw)
    value = indexed(case, tmp_path / "index")
    assert value["rubric_counts"]["missing"] == 1
    assert not (tmp_path / "index" / "artifacts" / sha256(raw)).exists()


@pytest.mark.parametrize("mode", ["malformed_result", "conflicting_label"])
def test_roster_output_pin_conflicts_and_unsupported_reasons_are_both_retained(fixture, tmp_path, mode):
    key = "rubric10-semantic"
    def change(roster, results):
        job = roster["jobs"][0]
        if mode == "malformed_result":
            results[key] = b"malformed result bytes"
            roster["pinned_files"][job["output"]] = "0" * 64
        else:
            results[key]["label"] = "another record"
            job.pop("applicability_context")
            roster["pinned_files"][job["output"]] = {"not": "a digest"}
    case = prepare_case(fixture, tmp_path, change=change)
    value = indexed(case, tmp_path / "index")
    row = next(row for row in value["rubric_rows"] if row["rubric"] == key)
    assert row["state"] == "mismatched" and row["conflicts"] and row["unsupported"]
    assert row["result_pin_basis"] == "captured_plan_with_roster_output_declaration"
    assert row["roster_output_pin"] == {"present": True,
        "sha256": "0" * 64 if mode == "malformed_result" else {"not": "a digest"}}
    assert any(reason["field"] == "roster.pinned_files.output"
               for reason in row["conflicts"] + row["unsupported"])
    assert fit.recheck_index(tmp_path / "index") == value
