"""Offline CLI controls for the registered score-gap selection rule, issue 6385.

2026-11-26. Synthetic records and measured rows only; no evaluator or provider.
The default canonical snapshot is the pre-option validity/coverage/label shape.
"""

from copy import deepcopy
import json
import hashlib
import pytest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import yaml


INSTRUMENT = "synthetic-score-instrument"
REVIEW_POLICY = "reported_only_pending_calibration_v1 (#835)"


def setup_case(tmp_path, monkeypatch):
    from data_sheets_schema.cli import runs as cli
    from data_sheets_schema import runs as model

    root = tmp_path / "data/d4d_concatenated"
    for label, slots in (("cfg_rep1", 4), ("cfg_rep2", 9), ("cfg_rep3", 6)):
        full = root / "claudecode_agent" / label
        core = root / "claudecode_agent_core" / label
        full.mkdir(parents=True)
        core.mkdir(parents=True)
        record = {"id": "example:record", "name": "Record", "title": "Title", "description": "Text"}
        record.update({"slot_" + str(i): ["value"] for i in range(slots)})
        (full / "P_d4d.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")
        (core / "P_d4d_core.yaml").write_text("id: example:record\n", encoding="utf-8")
        (core / "P_reconciliation.md").write_text("# synthetic fixture\n", encoding="utf-8")
        (core / "P_provenance.yaml").write_text(yaml.safe_dump({
            "record_mode": "live",
            "run": {"method": "claudecode_agent", "label": label, "project": "P"},
        }), encoding="utf-8")
    monkeypatch.setattr(model, "CONCAT_DIR", root)
    monkeypatch.setattr(cli, "_validates", lambda record: (True, "valid"))
    monkeypatch.setattr("data_sheets_schema.cli.provenance._require_repo_root_cwd", lambda name: None)
    return cli, root


def run(cli, *args):
    return CliRunner().invoke(cli.runs, ["select", "--method", "claudecode_agent",
                                       "--project", "P", "--config", "cfg", *args])


def score_rows(project, config, instrument_id, *, candidates, corpus_root, evidence_roots=(), evidence_index=None):
    rows = []
    for candidate in candidates:
        label = candidate["label"]
        midpoint = {"cfg_rep1": 80, "cfg_rep2": 40, "cfg_rep3": 50}[label]
        row = dict(candidate, project=project, instrument_id=instrument_id,
                   eligibility_problems=[], rubrics={},
                   slot_names=list(yaml.safe_load(candidate["record"].read_text())) if candidate.get("record") else [])
        def digest(value):
            return hashlib.sha256(value.encode()).hexdigest()

        for rubric, maximum in (("rubric10", 50), ("rubric20", 88)):
            row["rubrics"][rubric] = {"scorings": [
                {"scoring_number": number, "status": "measured",
                 "points": maximum * (midpoint + delta) / 100,
                 "maximum": maximum, "adjusted_max_points": maximum,
                 "percentage": midpoint + delta, "attempt": 1,
                 "publication_path": f"data/synthetic/{project}/{label}/{rubric}-{number}.json",
                 "sha256": digest(f"{label}-{rubric}-{number}"),
                 "receipt_sha256": digest(f"receipt-{label}-{rubric}-{number}"),
                 "measurement_identity": {
                     "instrument_id": instrument_id,
                     "definition_sha256": digest(rubric + "-definition"),
                     "schema_sha256": digest(rubric + "-schema"),
                     "rubric_sha256": digest(rubric + "-rubric"),
                     "evidence_authority_sha256": digest(rubric + "-authority"),
                     "scope_sha256": digest(label + "-scope"),
                     "record_sha256": digest(label + "-record"),
                     "context_sha256": digest("context"),
                     "prompt_sha256": digest(label + rubric + "-prompt"),
                     "runner_sha256": digest("runner"),
                 }}
                for number, delta in ((1, -1), (2, 0), (3, 1))
            ]}
        rows.append(row)
    return rows


def policy_args():
    return ("--score-policy", "score_gap_v1", "--score-instrument", INSTRUMENT)


def snapshot(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_score_policy_requires_an_explicit_instrument(tmp_path, monkeypatch):
    cli, _ = setup_case(tmp_path, monkeypatch)
    result = run(cli, "--score-policy", "score_gap_v1")
    assert result.exit_code != 0
    assert "--score-instrument" in result.output


def test_score_instrument_cannot_silently_change_the_default_route(tmp_path, monkeypatch):
    cli, _ = setup_case(tmp_path, monkeypatch)
    result = run(cli, "--score-instrument", INSTRUMENT)
    assert result.exit_code != 0
    assert "--score-policy" in result.output


def test_score_preview_prints_both_picks_and_preserves_every_file(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    before = snapshot(root)
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=score_rows):
        result = run(cli, *policy_args())
    assert result.exit_code == 0, result.output
    assert "cfg_rep2" in result.output
    assert "cfg_rep1" in result.output
    assert "score_gap" in result.output
    assert "→ cfg_rep1" in result.output
    policy, _ = json.JSONDecoder().raw_decode(result.output.split("Score policy:\n", 1)[1])
    assert policy["T"] > 0
    assert policy["gap"] == 40
    assert policy["rule"] == "score_gap"
    assert snapshot(root) == before


def test_score_preview_missing_measurement_keeps_the_coverage_pick(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)

    def missing(*args, **kwargs):
        rows = score_rows(*args, **kwargs)
        row = next(row for row in rows if row["label"] == "cfg_rep3")
        cell = row["rubrics"]["rubric20"]["scorings"][2]
        cell.update(status="not measured", points=None, maximum=None, percentage=None, attempt=None,
                    reason="refused scoring")
        return rows

    before = snapshot(root)
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=missing):
        result = run(cli, *policy_args())
    assert result.exit_code == 0, result.output
    assert "→ cfg_rep2" in result.output
    assert "policy_fallback" in result.output
    assert "not measured" in result.output
    assert snapshot(root) == before


def test_invalid_top_score_never_wins_cli_selection(tmp_path, monkeypatch):
    cli, _ = setup_case(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "_validates", lambda record: (Path(record).parent.name != "cfg_rep1", "valid"))
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=score_rows):
        result = run(cli, *policy_args())
    assert result.exit_code == 0, result.output
    assert "→ cfg_rep1" not in result.output
    assert "→ cfg_rep3" in result.output


def test_incomplete_candidate_coverage_is_not_measured_instead_of_zero(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    from data_sheets_schema import runs as model
    real_complete = model.is_complete
    monkeypatch.setattr(model, "is_complete", lambda method, label, project, concat_dir:
                        False if label == "cfg_rep1" else real_complete(method, label, project, concat_dir))
    passed = []

    def capture_candidates(*args, **kwargs):
        passed.extend(deepcopy(kwargs["candidates"]))
        return score_rows(*args, **kwargs)

    before = snapshot(root)
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=capture_candidates):
        result = run(cli, *policy_args())
    assert result.exit_code == 0, result.output
    incomplete = next(row for row in passed if row["label"] == "cfg_rep1")
    assert incomplete["validity"] == "incomplete"
    assert incomplete["record"].is_file()
    assert len(yaml.safe_load(incomplete["record"].read_text())) == 8
    assert incomplete["slots"] is None
    assert "→ cfg_rep1" not in result.output
    assert snapshot(root) == before


def test_default_canonical_block_is_byte_identical_and_never_reads_scores(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    captured = []

    def retain_record(record, path):
        captured.append(deepcopy(record.data))
        return path

    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=AssertionError("default read scores")), \
            patch("data_sheets_schema.provenance.ProvenanceRecord.write", retain_record):
        result = run(cli, "--execute")
    assert result.exit_code == 0, result.output
    assert len(captured) == 1
    expected = {
        "criterion": "full and core both validate against the current schema, then most slots, then lowest label",
        "selected_from": [
            {"label": label, "slots": slots, "validation": "valid",
             "validation_recorded_at_run_time": "unverified", "review_adverse": None,
             "review_not_evidence": "no review block"}
            for label, slots in (("cfg_rep1", 8), ("cfg_rep2", 13), ("cfg_rep3", 10))
        ],
        "margin_over_runner_up": 3,
        "runtime": None,
        "supersedes_runtimes": "unknown",
        "reviews_applied": False,
        "reviews_not_applied_because": "report-only (#835): calibrated selection rule not established; "
            "cfg_rep1: no review block; cfg_rep2: no review block; cfg_rep3: no review block",
        "review_policy": REVIEW_POLICY,
        "selected_by": "d4d runs select",
    }
    assert captured[0]["canonical"] == expected
    actual_bytes = yaml.safe_dump(captured[0]["canonical"], sort_keys=False, allow_unicode=True).encode()
    expected_bytes = yaml.safe_dump(expected, sort_keys=False, allow_unicode=True).encode()
    assert actual_bytes == expected_bytes
    assert "score_policy" not in captured[0]["canonical"]
    assert all("canonical" not in yaml.safe_load(path.read_text())
               for path in root.rglob("*_provenance.yaml"))


def test_score_record_adds_policy_without_applying_content_review(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    captured = []

    def retain_record(record, path):
        captured.append(deepcopy(record.data))
        return path

    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=score_rows), \
            patch("data_sheets_schema.provenance.ProvenanceRecord.write", retain_record):
        result = run(cli, *policy_args(), "--execute", "--score-owner-authorization", "synthetic owner decision")
    assert result.exit_code == 0, result.output
    assert len(captured) == 1
    canonical = captured[0]["canonical"]
    assert canonical["review_policy"] == REVIEW_POLICY
    assert canonical["reviews_applied"] is False
    assert canonical["score_policy"]["name"] == "score_gap_v1"
    assert canonical["score_policy"]["instrument_id"] == INSTRUMENT
    assert canonical["score_policy"]["rule"] == "score_gap"
    assert canonical["score_policy"]["current_policy_pick"] == "cfg_rep2"
    assert canonical["margin_over_runner_up"] == 3
    assert canonical["criterion"].endswith("decision: score_gap")
    assert "slot(s) ahead of the runner-up" not in result.output
    assert canonical["score_policy"]["owner_authorization"] == "synthetic owner decision"
    assert "cfg_rep1" in result.output
    assert all("canonical" not in yaml.safe_load(path.read_text())
               for path in root.rglob("*_provenance.yaml"))


def test_selection_pools_other_projects_in_the_same_series(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    for directory in (root / "claudecode_agent").iterdir():
        (directory / "Q_d4d.yaml").write_text("id: example:other\n", encoding="utf-8")
    seen = []

    def with_noisy_project(project, *args, **kwargs):
        seen.append(project)
        rows = score_rows(project, *args, **kwargs)
        if project == "Q":
            for row in rows:
                for family in row["rubrics"].values():
                    for cell, value in zip(family["scorings"], (1, 50, 99)):
                        cell.update(points=cell["maximum"] * value / 100, percentage=value)
        return rows

    before = snapshot(root)
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=with_noisy_project):
        result = run(cli, *policy_args())
    assert result.exit_code == 0, result.output
    assert set(seen) == {"P", "Q"}
    assert "→ cfg_rep2" in result.output
    assert "policy_fallback" in result.output
    assert "score gap is not greater than T" in result.output
    assert snapshot(root) == before


def test_instrument_bytes_drift_falls_back_with_the_exact_pooling_reason(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)

    def drifted(*args, **kwargs):
        rows = score_rows(*args, **kwargs)
        for row in rows:
            digest = "a" * 64 if row["label"] == "cfg_rep1" else "b" * 64
            for cell in row["rubrics"]["rubric10"]["scorings"]:
                cell["measurement_identity"]["definition_sha256"] = digest
        return rows

    before = snapshot(root)
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=drifted):
        result = run(cli, *policy_args())
    assert result.exit_code == 0, result.output
    assert "→ cfg_rep2" in result.output
    policy, _ = json.JSONDecoder().raw_decode(result.output.split("Score policy:\n", 1)[1])
    assert policy["rule"] == "policy_fallback"
    reason = "rubric10: instrument definition_sha256 differs across records"
    assert reason in result.output
    assert reason in policy["variation"]["fallback_reasons"]
    assert policy["variation"]["s"] == "not measured"
    assert policy["variation"]["degrees_of_freedom"] == 0
    assert snapshot(root) == before


def test_variation_command_reports_pooled_df_and_never_writes(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    before = snapshot(root)
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=score_rows):
        result = CliRunner().invoke(cli.runs, [
            "score-variation", "--method", "claudecode_agent", "--config", "cfg",
            "--score-instrument", INSTRUMENT,
        ])
    assert result.exit_code == 0, result.output
    assert '"degrees_of_freedom": 6' in result.output
    variation, _ = json.JSONDecoder().raw_decode(result.output.split("Series variation:\n", 1)[1])
    assert variation["s"] == pytest.approx(1.0)
    assert '"per_project"' in result.output
    assert '"per_rubric"' in result.output
    assert snapshot(root) == before


def test_owner_rulings_are_recorded_without_automatically_changing_pick(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    rulings = [{"label": "cfg_rep1", "slot": "description", "ruling": "accepted after sibling comparison",
                "authorization_reference": "synthetic owner decision"}]
    authority = tmp_path / "owner-rulings.json"
    authority.write_text(json.dumps(rulings), encoding="utf-8")
    captured = []

    def retain_record(record, path):
        captured.append(deepcopy(record.data))
        return path

    before = snapshot(root)
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=score_rows), \
            patch("data_sheets_schema.provenance.ProvenanceRecord.write", retain_record):
        preview = run(cli, *policy_args(), "--score-owner-rulings", str(authority))
        assert preview.exit_code == 0, preview.output
        policy, _ = json.JSONDecoder().raw_decode(preview.output.split("Score policy:\n", 1)[1])
        assert policy["owner_rulings"] == rulings
        assert policy["T"] > 0 and policy["gap"] == 40
        assert captured == []
        assert snapshot(root) == before
        result = run(cli, *policy_args(), "--score-owner-rulings", str(authority), "--execute",
                     "--score-owner-authorization", "synthetic owner decision")
    assert result.exit_code == 0, result.output
    assert "→ cfg_rep1" in result.output
    assert captured[0]["canonical"]["score_policy"]["owner_rulings"] == rulings
    assert captured[0]["canonical"]["reviews_applied"] is False
    assert snapshot(root) == before


def test_owner_rulings_cannot_be_attached_to_the_default_route(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    authority = tmp_path / "owner-rulings.json"
    authority.write_text("[]", encoding="utf-8")
    before = snapshot(root)
    result = run(cli, "--score-owner-rulings", str(authority))
    assert result.exit_code != 0
    assert "--score-policy" in result.output
    assert snapshot(root) == before


def test_execution_preflight_requires_nonempty_owner_authorization(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    import click
    before = snapshot(root)
    for authorization in (None, "", " "):
        with pytest.raises(click.ClickException, match="score-owner-authorization"):
            cli._require_score_selection_options("score_gap_v1", INSTRUMENT, (), None,
                                                  execute=True, authorization=authorization)
    cli._require_score_selection_options("score_gap_v1", INSTRUMENT, (), None,
                                          execute=True, authorization="synthetic owner word")
    assert snapshot(root) == before


def test_owner_authorization_requires_score_policy(tmp_path, monkeypatch):
    cli, _ = setup_case(tmp_path, monkeypatch)
    result = run(cli, "--score-owner-authorization", "synthetic owner word")
    assert result.exit_code != 0
    assert "require --score-policy" in result.output


def test_owner_ruling_unknown_slot_refuses_and_valid_ruling_prints(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    authority = tmp_path / "rulings.json"
    row = {"label": "cfg_rep1", "slot": "absent-slot", "ruling": "retain for owner review",
           "authorization_reference": "synthetic owner word"}
    authority.write_text(json.dumps([row]))
    before = snapshot(root)
    with patch("data_sheets_schema.score_selection.build_evidence_table", side_effect=score_rows):
        refused = run(cli, *policy_args(), "--score-owner-rulings", str(authority))
        assert refused.exit_code != 0
        assert "slot is absent" in refused.output
        row["slot"] = "description"
        authority.write_text(json.dumps([row]))
        result = run(cli, *policy_args(), "--score-owner-rulings", str(authority))
        assert result.exit_code == 0, result.output
        assert "Owner ruling recorded (does not change arithmetic): cfg_rep1 / description" in result.output
        assert row["ruling"] in result.output
    assert snapshot(root) == before


def test_owner_authorization_portability_preserves_verbatim_urls(tmp_path, monkeypatch):
    cli, root = setup_case(tmp_path, monkeypatch)
    import click
    before = snapshot(root)
    for text in (str(tmp_path / "owner-word.txt"), "owner confirms " + str(tmp_path / "decision")):
        with pytest.raises(click.ClickException, match="repository-relative"):
            cli._require_score_selection_options("score_gap_v1", INSTRUMENT, (), None,
                                                  execute=True, authorization=text)
    cli._require_score_selection_options("score_gap_v1", INSTRUMENT, (), None,
                                          execute=True, authorization="https://example.org/owner-decision")
    assert snapshot(root) == before
