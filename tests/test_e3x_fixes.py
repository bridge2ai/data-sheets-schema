"""Offline causal regressions for the 2026-10-29 E3x review findings."""
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation import blind_review_pack as pack
from tests.test_audit_evaluation_comparability import audit


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


