"""Offline causal regressions for the 2026-10-29 E3x review findings."""
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation import blind_review_pack as pack
from tests.test_audit_evaluation_comparability import audit
from tests.test_audit_evaluation_comparability import (
    isolated_execution_locks, no_network, no_unmocked_runtime,
    registered_generation_inputs, registered_prepared, registered_case,
    registered_audit, registered_problem, registered_roster,
    rewrite_plan,
)


def cohort_file(tmp_path, cells=None):
    path = tmp_path / "cohort.yaml"
    path.write_text(yaml.safe_dump({"format": "evaluation_cohort_v1", "cells": cells or [
        {"arm": "novel", "projects": ["EXTERNAL"], "replicates": [2, 7],
         "label_template": "declared_rep{replicate}", "method": "claudecode_api",
         "condition": "generic_v10", "input_arm": "baseline"}]}))
    return path


def test_f5_manifest_queues_unrated_nonlegacy_replicates(tmp_path):
    manifest = cohort_file(tmp_path)
    result = audit.audit(tmp_path, roster_manifest=manifest)
    assert {(r["arm"], r["project"], r["label"], r["replicate"]) for r in result["records"]} == {
        ("novel", "EXTERNAL", "declared_rep2", 2), ("novel", "EXTERNAL", "declared_rep7", 7)}
    assert len(result["rescore_tuples"]) == 4
    assert result["scope"]["roster_manifest"]["sha256"] == audit.sha(manifest.read_bytes())


def test_f5_campaign_uses_declared_cohort_without_version_heuristics(tmp_path):
    manifest = cohort_file(tmp_path)
    records = [pack.Record("novel", "EXTERNAL", f"declared_rep{r}", tmp_path / f"{r}.yaml") for r in (2, 7)]
    assert pack.validate_cohort(records, cohort_manifest=manifest) == records
    with pytest.raises(ValueError, match="declared cohort"):
        pack.validate_cohort(records[:1], cohort_manifest=manifest)


def test_f6_cli_arm_must_match_manifest_assignment(registered_case):
    _, output, _ = registered_case
    result = registered_audit(registered_case, directories=[("swapped-arm", output)])
    assert registered_problem(result) == ["registered_arm_mapping_undeclared_or_mismatched"]
    assert result["totals"]["bound_registered_rating_files"] == 0


def test_f6_bound_run_is_visible_beside_grouping_arm(registered_case):
    result = registered_audit(registered_case)
    run = registered_case[2].document()["generation_run"]
    assert result["summary"][0]["bound_generation_runs"] == [run]
    markdown = audit.markdown(result)
    assert all(run[key] in markdown for key in ("arm", "method", "label"))


def test_f7_untargeted_registered_tuple_stays_visibly_pending(registered_case):
    root, output, _ = registered_case
    result = audit.audit(root, roster_manifest=registered_roster(registered_case),
                         registered_evaluations=[("explicit-v10", output)])
    queued = next(row for row in result["rescore_tuples"] if row["rubric"] == "rubric20")
    assert queued["reasons"] == ["package_not_committed", "pending_target_selection"]
    assert queued["action"] == "select_targets_verify_execution_lock_and_commit_package"
    assert "pending_target_selection" in audit.markdown(result)


def test_f11_plan_records_yaml_emitter_and_audit_names_drift(registered_case):
    _, output, prepared = registered_case
    identity = prepared.document()["blinding"]
    assert identity["pyyaml_version"] == yaml.__version__
    assert identity["dumper_class"] == "yaml.dumper.SafeDumper"
    rewrite_plan(output, lambda plan: plan["blinding"].update(pyyaml_version="different-version"))
    assert registered_problem(registered_audit(registered_case)) == ["registered_yaml_emitter_version_mismatch"]


