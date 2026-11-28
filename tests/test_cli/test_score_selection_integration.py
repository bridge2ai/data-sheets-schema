"""Real reader-to-CLI regressions from review F/G fixtures, issue 6385.

2026-11-26. All calls are previews on synthetic files. The score reader,
receipt checks, arithmetic and CLI formatting are never mocked.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import click
import pytest
import yaml

from tests.score_selection_cases import Case, INSTRUMENT, LABELS, METHOD, report, sha, snapshot, write


def policy(case, **kw):
    before = snapshot(case.tmp)
    result = case.invoke(**kw)
    assert snapshot(case.tmp) == before
    return result, report(result, "Score policy")


def fallback(case, reason, **kw):
    result, value = policy(case, **kw)
    assert value["rule"] == "policy_fallback", value
    assert value["current_policy_pick"] == "cfg_rep2"
    assert "→ cfg_rep2" in result.output
    assert reason.lower() in json.dumps(value).lower(), value
    return result, value


def values_with_key(value, key):
    if isinstance(value, dict):
        if key in value:
            yield value
        for child in value.values():
            yield from values_with_key(child, key)
    elif isinstance(value, list):
        for child in value:
            yield from values_with_key(child, key)


def same_variation(left, right, census):
    """Variation has no validity/coverage pass; its measurements must agree."""
    for key in ("s", "degrees_of_freedom", "records", "per_project", "per_rubric", "fallback_reasons"):
        assert left[key] == right[key]
    assert "series_census" not in right
    for a, b in zip(left["series_census"], census, strict=True):
        for key in ("project", "label", "cells", "usable_paired_count", "not_measured_cells"):
            assert a[key] == b[key]


def test_real_reader_complete_series_changes_pick_and_variation_matches(tmp_path):
    case = Case(tmp_path).base()
    result, value = policy(case)
    assert value["current_policy_pick"] == "cfg_rep2"
    assert value["highest_mean_pick"] == "cfg_rep1"
    assert value["rule"] == "score_gap"
    assert value["gap"] > value["T"] > 0
    assert "→ cfg_rep1" in result.output
    printed_variation = report(result, "Series variation")
    same_variation(printed_variation, value["variation"], value["series_census"])
    assert printed_variation["records"] == 6
    assert len(list(values_with_key(value, "series_census"))) == 1
    before = snapshot(case.tmp)
    variation = report(case.invoke(variation=True), "Series variation")
    same_variation(variation, value["variation"], value["series_census"])
    assert variation["records"] == 6
    assert variation["degrees_of_freedom"] == 12
    assert set(variation["per_project"]) == {"P", "Q"}
    assert snapshot(case.tmp) == before


def test_receipt_only_project_and_missing_records_remain_in_the_census(tmp_path):
    """Reviewer N1b: dropping all record files must not drop that project's rows."""
    case = Case(tmp_path).base(noisy=True)
    for label, _slots in LABELS:
        (case.concat / METHOD / label / "Q_d4d.yaml").unlink()
    result, value = fallback(case, "candidate record is missing")
    census = value["series_census"]
    assert {(row["project"], row["label"]) for row in census} == {
        (project, label) for project in ("P", "Q") for label, _slots in LABELS}
    for label, _slots in LABELS:
        assert f"Q/{label}" in value["fallback_reason"]
        row = next(row for row in census if (row["project"], row["label"]) == ("Q", label))
        assert row["not_measured_cells"]
    assert {(row["project"], row["label"]) for row in value["discovered_census"]} == {
        (project, label) for project in ("P", "Q") for label, _slots in LABELS}
    variation = report(case.invoke(variation=True), "Series variation")
    same_variation(variation, value["variation"], census)


def test_receipt_only_project_outside_manifest_is_disclosed_and_falls_back(tmp_path):
    case = Case(tmp_path, manifest_projects=("P",)).base(noisy=True)
    for label, _slots in LABELS:
        (case.concat / METHOD / label / "Q_d4d.yaml").unlink()
    _result, value = fallback(case, "Q/cfg_rep1")
    assert value["series_roster"]["projects"] == ["P"]
    assert {(row["project"], row["label"]) for row in value["roster_unexpected"]} == {
        ("Q", label) for label, _slots in LABELS}
    assert set(row["project"] for row in value["series_census"]) == {"P", "Q"}


def test_unreadable_selected_candidate_is_a_named_fallback_not_a_traceback(tmp_path):
    """Reviewer F7b exercises the selected project's YAML parser failure."""
    case = Case(tmp_path).base()
    (case.concat / METHOD / "cfg_rep3/P_d4d.yaml").write_text("a: [unclosed\n", encoding="utf-8")
    result, value = fallback(case, "cannot be read")
    assert "P/cfg_rep3" in value["fallback_reason"]
    assert "Traceback" not in result.output
    assert result.exception is None
    variation = report(case.invoke(variation=True), "Series variation")
    assert any("P/cfg_rep3" in reason and "cannot be read" in reason
               for reason in variation["fallback_reasons"])


def test_manifest_roster_detects_a_project_missing_from_corpus_and_receipts(tmp_path):
    case = Case(tmp_path, manifest_projects=("P", "Q", "R")).base()
    _result, value = fallback(case, "R/cfg_rep1")
    assert value["series_roster"]["projects"] == ["P", "Q", "R"]
    assert value["series_roster"]["manifest_sha256"] == sha(case.manifest.read_bytes())
    assert len(value["expected_roster"]) == 9
    assert len(value["discovered_census"]) == 6
    assert len(value["series_census"]) == 9
    assert {(row["project"], row["label"]) for row in value["roster_missing"]} == {
        ("R", label) for label, _slots in LABELS}
    assert value["s"] == value["T"] == "not measured"
    assert "series_census" not in value["variation"]
    explicit = ("--score-series-project", "P", "--score-series-project", "Q")
    result, narrowed = policy(case, extra=explicit)
    assert narrowed["rule"] == "score_gap"
    assert narrowed["series_roster"]["projects"] == ["P", "Q"]
    assert "explicit" in narrowed["series_roster"]["basis"]
    assert len(narrowed["expected_roster"]) == 6
    assert narrowed["roster_missing"] == narrowed["roster_unexpected"] == []
    variation = report(case.invoke(variation=True, extra=explicit), "Series variation")
    same_variation(variation, narrowed["variation"], narrowed["series_census"])
    assert "→ cfg_rep1" in result.output


def test_explicit_narrower_roster_records_excluded_projects_and_changes_pool_only_explicitly(tmp_path):
    case = Case(tmp_path).base(noisy=True)
    _result, full = fallback(case, "score gap is not greater than T")
    explicit = ("--score-series-project", "P")
    result, narrow = policy(case, extra=explicit)
    assert full["variation"]["records"] == 6
    assert narrow["variation"]["records"] == 3
    assert narrow["series_roster"]["projects"] == ["P"]
    assert narrow["series_roster"]["excluded_discovered_projects"] == ["Q"]
    assert set(row["project"] for row in narrow["series_census"]) == {"P"}
    assert narrow["rule"] == "score_gap"
    assert "→ cfg_rep1" in result.output


def test_variation_reader_valueerror_is_a_clean_cli_message_without_writes(tmp_path):
    case = Case(tmp_path)
    before = snapshot(case.tmp)
    result = case.invoke(variation=True)
    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit)
    assert result.output.startswith("Error:")
    assert "cfg" in result.output
    assert "Traceback" not in result.output
    assert snapshot(case.tmp) == before


def test_unscored_invalid_record_and_unrelated_metadata_name_the_fallback_cause(tmp_path):
    for problem in ("unscored-invalid", "unrelated-metadata"):
        case = Case(tmp_path / problem)
        if problem == "unscored-invalid":
            for label, slots in LABELS:
                case.record("P", label, slots)
                case.record("Q", label, slots)
                case.score_record("Q", label, [30, 30, 31], [50, 51, 50])
                if label != "cfg_rep3":
                    case.score_record("P", label, [40, 41, 40] if label == "cfg_rep1" else [35, 35, 36],
                                      [70, 71, 70] if label == "cfg_rep1" else [62, 62, 63])
            result, value = fallback(case, "P/cfg_rep3", invalid=("cfg_rep3",))
        else:
            case.base()
            bad = case.receipts / "unrelated-run" / "plan.json"
            bad.parent.mkdir()
            bad.write_text("{truncated", encoding="utf-8")
            result, value = fallback(case, "unrelated-run/plan.json")
        assert "Traceback" not in result.output
        assert str(case.tmp) not in json.dumps(value)


def test_incomplete_series_has_only_explicit_partial_noise_diagnostics(tmp_path):
    case = Case(tmp_path).base()
    (case.entry("Q", "cfg_rep2", "rubric20", 3)["run"] / "receipt.json").unlink()
    _result, value = fallback(case, "Q/cfg_rep2")
    assert value["s"] == value["T"] == "not measured"
    assert value["variation"]["s"] == "not measured"
    partial = value["variation"]["partial_variation"]
    assert partial["partial_s"] > 0
    assert partial["partial_T"] > 0
    assert partial["partial_degrees_of_freedom"] > 0
    assert partial["partial_records"] > 0


def test_replacement_from_another_project_is_listed_in_the_selected_block(tmp_path):
    case = Case(tmp_path).base()
    refused = case.scoring("Q", "cfg_rep2", "rubric20", 3, 0, status="REFUSED", run_name="refused-other-project")
    accepted = case.entry("Q", "cfg_rep2", "rubric20", 3)
    accepted["manifest"].update(attempt=2,
        refused_attempt_receipt={"path": str(refused["run"] / "receipt.json"), "sha256": refused["receipt_sha"]},
        refused_attempt_plan={"path": str(refused["run"] / "plan.json"), "sha256": refused["plan_sha"]})
    write(accepted["manifest_path"], accepted["manifest"])
    _result, value = policy(case)
    assert value["rule"] == "score_gap"
    assert len(value["replaced_cells"]) == 1
    replacement = value["replaced_cells"][0]
    assert replacement["project"] == "Q"
    assert replacement["label"] == "cfg_rep2"
    assert replacement["rubric"] == "rubric20"
    assert replacement["refused_attempt"]["plan_sha256"] == refused["plan_sha"]
    assert replacement["refused_attempt"]["receipt_sha256"] == refused["receipt_sha"]


def test_refusal_disclosures_keep_only_bounded_path_free_prefix_and_hashes(tmp_path):
    paths = ("file:/sensitive/run/candidate.json", "file:///sensitive/run/candidate.json",
             "/sensitive/run folder/candidate.json", "Z:\\sensitive\\run folder\\candidate.json",
             "\\\\server\\sensitive\\candidate.json")
    for index, path in enumerate(paths):
        case = Case(tmp_path / str(index)).base()
        refused = case.scoring("P", "cfg_rep1", "rubric10", 3, 0,
                               status="REFUSED", run_name="refused-first")
        refused["receipt"]["failure"] = "ValueError: validation failed for " + path + " hidden suffix"
        case.refresh(refused, receipt=True)
        accepted = case.entry(number=3)
        accepted["manifest"].update(attempt=2,
            refused_attempt_receipt={"path": str(refused["run"] / "receipt.json"), "sha256": refused["receipt_sha"]},
            refused_attempt_plan={"path": str(refused["run"] / "plan.json"), "sha256": refused["plan_sha"]})
        write(accepted["manifest_path"], accepted["manifest"])
        _result, value = policy(case)
        assert value["rule"] == "score_gap"
        first = value["replaced_cells"][0]["refused_attempt"]
        assert first["reason"] == "ValueError: validation failed for"
        assert first["receipt_sha256"] == refused["receipt_sha"]
        assert first["plan_sha256"] == refused["plan_sha"]
        assert len(first["reason"]) <= 200
        assert "sensitive" not in json.dumps(value)
        assert "hidden suffix" not in json.dumps(value)


def test_complete_series_with_other_fixed_rubric_maxima_remains_eligible(tmp_path):
    case = Case(tmp_path).base()
    _result, original = policy(case)
    for entry in case.entries.values():
        score = entry["publication"]["overall_score"]
        for key in ("total_points", "max_points", "adjusted_max_points"):
            score[key] *= 2
        case.refresh(entry, publication=True)
    _result, value = policy(case)
    assert value["rule"] == "score_gap"
    assert value["percentage_base"]["maxima"] == {"rubric10": 100, "rubric20": 176}
    assert value["s"] == pytest.approx(original["s"])
    assert value["T"] == pytest.approx(original["T"])
    assert value["gap"] == pytest.approx(original["gap"])


def test_missing_other_project_evidence_cannot_shrink_the_series_silently(tmp_path):
    case = Case(tmp_path)
    q_root = case.tmp / "other-receipts"
    q_root.mkdir()
    case.base(q_root=q_root, noisy=True)
    complete, complete_policy = policy(case, roots=(case.receipts, q_root))
    assert complete_policy["rule"] == "policy_fallback"
    assert complete_policy["s"] > 10
    result, value = fallback(case, "not measured")
    census = value["series_census"]
    assert len(census) == 6
    assert "Q" in json.dumps(census)
    assert "cfg_rep1" in json.dumps(census)
    assert "missing" in json.dumps(census).lower()
    variation = report(case.invoke(variation=True), "Series variation")
    same_variation(variation, value["variation"], value["series_census"])


def test_partial_pair_diagnostics_join_scoring_numbers_not_cell_positions(tmp_path):
    case = Case(tmp_path).base()
    (case.entry("Q", "cfg_rep1", "rubric10", 2)["run"] / "receipt.json").unlink()
    result, value = fallback(case, "not measured")
    partial = next(row for row in value["series_census"]
                   if row["project"] == "Q" and row["label"] == "cfg_rep1")
    assert partial["paired_numbers"] == [1, 3]
    assert partial["usable_paired_count"] == 2
    paired_one = (100 * 30 / 50 + 100 * 50 / 88) / 2
    paired_three = (100 * 31 / 50 + 100 * 50 / 88) / 2
    assert partial["paired"]["mean"] == pytest.approx((paired_one + paired_three) / 2)
    assert partial["paired"]["spread"] == pytest.approx(abs(paired_three - paired_one) / (2 ** 0.5))
    variation = report(case.invoke(variation=True), "Series variation")
    same_variation(variation, value["variation"], value["series_census"])


def test_other_project_record_and_receipt_errors_are_reported_not_tracebacks(tmp_path):
    for problem in ("changed-record", "malformed-record", "malformed-receipt"):
        case = Case(tmp_path / problem).base()
        if problem == "changed-record":
            path = case.concat / METHOD / "cfg_rep1/Q_d4d.yaml"
            path.write_text(path.read_text() + "another_slot: [value]\n", encoding="utf-8")
            reason = "changed record bytes"
        elif problem == "malformed-record":
            (case.concat / METHOD / "cfg_rep1/Q_d4d.yaml").write_text("a: [unclosed\n", encoding="utf-8")
            reason = "cannot be read"
        else:
            (case.entry("Q", "cfg_rep1", "rubric10", 2)["run"] / "receipt.json").write_text("{truncated", encoding="utf-8")
            reason = "JSONDecodeError"
        result, value = fallback(case, reason)
        assert "Traceback" not in result.output
        assert len(value["series_census"]) == 6
        assert reason.lower() in case.invoke(variation=True).output.lower()


def test_malformed_plan_identity_is_reported_without_traceback(tmp_path):
    for name, identity in (("none", None), ("list", [])):
        case = Case(tmp_path / name).base()
        entry = case.entry("Q", "cfg_rep1", "rubric10", 2)
        entry["plan"]["identity"] = identity
        case.refresh(entry, plan=True)
        result, value = fallback(case, "not measured")
        assert "Traceback" not in result.output
        assert case.invoke(variation=True).exit_code == 0


def test_undeclared_refusals_never_become_ordinary_accepted_cells(tmp_path):
    for mode in ("baseline", "repeat-without-attempt", "third-attempt"):
        case = Case(tmp_path / mode).base()
        number = 1 if mode == "baseline" else 3
        first = case.scoring("P", "cfg_rep1", "rubric10", number, 0,
                             status="REFUSED", run_name="refused-first")
        if mode == "third-attempt":
            case.scoring("P", "cfg_rep1", "rubric10", number, 0,
                         status="REFUSED", run_name="refused-second")
            accepted = case.entry(number=number)
            accepted["manifest"].update(attempt=2,
                refused_attempt_receipt={"path": str(first["run"] / "receipt.json"), "sha256": first["receipt_sha"]},
                refused_attempt_plan={"path": str(first["run"] / "plan.json"), "sha256": first["plan_sha"]})
            write(accepted["manifest_path"], accepted["manifest"])
        fallback(case, "refus")


def test_declared_replacement_is_measured_and_disclosed_without_refused_output(tmp_path):
    case = Case(tmp_path).base()
    refused = case.scoring("P", "cfg_rep1", "rubric10", 3, 0, status="REFUSED", run_name="refused-first")
    accepted = case.entry(number=3)
    accepted["manifest"].update(attempt=2,
        refused_attempt_receipt={"path": str(refused["run"] / "receipt.json"), "sha256": refused["receipt_sha"]},
        refused_attempt_plan={"path": str(refused["run"] / "plan.json"), "sha256": refused["plan_sha"]})
    write(accepted["manifest_path"], accepted["manifest"])
    result, value = policy(case)
    assert value["rule"] == "score_gap"
    assert len(value["replaced_cells"]) == 1
    replacement = value["replaced_cells"][0]
    assert replacement["attempt"] == 2
    assert replacement["scoring_number"] == 3
    assert replacement["receipt_sha256"] == accepted["receipt_sha"]
    assert "synthetic refusal" in json.dumps(value)


def test_fixed_denominator_and_project_context_are_required(tmp_path):
    for change in ("adjusted-maximum", "context-between-records", "context-between-rubrics"):
        case = Case(tmp_path / change).base()
        for number in (1, 2, 3):
            entry = case.entry("P", "cfg_rep1", "rubric20", number)
            if change == "adjusted-maximum":
                entry["publication"]["overall_score"]["adjusted_max_points"] = 44
                case.refresh(entry, publication=True)
            else:
                families = ("rubric10", "rubric20") if change == "context-between-records" else ("rubric20",)
                for family in families:
                    item = case.entry("P", "cfg_rep1", family, number)
                    item["plan"]["deterministic_fields"]["metadata"]["context_sha256"] = sha(b"different context")
                    case.refresh(item, plan=True, publication=True)
        fallback(case, "fixed percentage base" if change == "adjusted-maximum" else "context")


def test_other_project_consistent_definition_drift_falls_back_in_both_commands(tmp_path):
    case = Case(tmp_path).base()
    for number in (1, 2, 3):
        entry = case.entry("Q", "cfg_rep3", "rubric10", number)
        digest = sha(b"another composed definition")
        entry["plan"]["inputs"]["agent-definition.md"]["sha256"] = digest
        entry["plan"]["deterministic_fields"]["metadata"]["instrument_sha256"] = digest
        entry["plan"]["definition_provenance"]["composed_sha256"] = digest
        case.refresh(entry, plan=True, publication=True)
    result, value = fallback(case, "definition_sha256 differs across records")
    variation = case.invoke(variation=True)
    assert variation.exit_code == 0, variation.output
    assert "definition_sha256 differs across records" in variation.output


def test_copied_or_symlinked_receipts_report_specific_reasons(tmp_path):
    case = Case(tmp_path).base()
    copied = case.tmp / "copied-receipts"
    shutil.copytree(case.receipts, copied)
    fallback(case, "copied or relocated receipt root", roots=(copied,))
    alias = case.tmp / "alias"
    alias.symlink_to(case.receipts, target_is_directory=True)
    fallback(case, "symlink", roots=(alias,))


def test_fourth_scoring_is_reported_instead_of_reusing_three_score_threshold(tmp_path):
    case = Case(tmp_path).base()
    for family, points in (("rubric10", 50), ("rubric20", 88)):
        case.scoring("P", "cfg_rep2", family, 4, points)
    result, value = fallback(case, "more than three")
    assert any(cell["scoring_number"] == 4 for cell in values_with_key(value, "scoring_number"))


def test_policy_contains_portable_cell_arithmetic_and_hashes(tmp_path):
    case = Case(tmp_path).base()
    result, value = policy(case)
    assert str(case.tmp) not in json.dumps(value)
    cells = [cell for cell in values_with_key(value, "scoring_number") if cell.get("status") == "measured"]
    assert cells
    for cell in cells:
        assert cell["maximum"] in (50, 88)
        assert cell["percentage"] == pytest.approx(100 * cell["points"] / cell["maximum"])
        assert cell["attempt"] == 1
        assert len(cell["receipt_sha256"]) == 64
        assert len(cell["publication_sha256"]) == 64
        path = Path(cell["publication_path"])
        assert not path.is_absolute()
        assert sha((case.corpus / path).read_bytes()) == cell["publication_sha256"]


def test_incomplete_generation_has_no_measured_coverage_even_when_record_exists(tmp_path):
    case = Case(tmp_path).base()
    (case.concat / (METHOD + "_core") / "cfg_rep1/P_d4d_core.yaml").unlink()
    result, value = policy(case)
    table = report(result, "Evidence table")
    row = next(row for row in table if row["label"] == "cfg_rep1")
    assert row["validity"] == "incomplete"
    assert row["slots"] == "not measured"
    assert "description" in row["slot_names"]
    assert "→ cfg_rep1" not in result.output


def test_owner_rulings_are_visible_and_do_not_change_arithmetic(tmp_path):
    case = Case(tmp_path).base()
    _, original = policy(case)
    path = case.tmp / "owner-rulings.json"
    rulings = [{"label": "cfg_rep1", "slot": "description", "ruling": "needs owner review",
                "authorization_reference": "owner decision fixture"}]
    write(path, rulings)
    result, value = policy(case, extra=("--score-owner-rulings", str(path)))
    assert value["owner_rulings"] == rulings
    assert "needs owner review" in result.output
    for key in ("current_policy_pick", "highest_mean_pick", "s", "T", "gap", "rule"):
        assert value[key] == original[key]
    for field, invalid in (("label", "cfg_rep99"), ("slot", "invented_slot")):
        bad = [dict(rulings[0], **{field: invalid})]
        write(path, bad)
        before = snapshot(case.tmp)
        refused = case.invoke(extra=("--score-owner-rulings", str(path)))
        assert refused.exit_code != 0
        assert "owner ruling" in refused.output
        assert snapshot(case.tmp) == before


def test_owner_ruling_references_are_portable_and_closed(tmp_path):
    case = Case(tmp_path).base()
    path = case.tmp / "owner-rulings.json"
    ruling = {"label": "cfg_rep1", "slot": "description", "ruling": "owner reviewed this slot",
              "authorization_reference": "https://example.org/decisions/owner-choice"}
    write(path, [ruling])
    _, value = policy(case, extra=("--score-owner-rulings", str(path)))
    assert value["owner_rulings"] == [ruling]
    for invalid in (dict(ruling, authorization_reference=str(case.tmp / "local-word.md")),
                    dict(ruling, undeclared_path=str(case.tmp / "private-notes.md"))):
        write(path, [invalid])
        before = snapshot(case.tmp)
        result = case.invoke(extra=("--score-owner-rulings", str(path)))
        assert result.exit_code != 0
        assert "owner" in result.output.lower()
        assert snapshot(case.tmp) == before


def test_owner_authorization_guard_directly_refuses_missing_and_blank_words():
    from data_sheets_schema.cli.runs import _require_score_selection_options
    with patch("data_sheets_schema.cli.provenance._require_repo_root_cwd", lambda name: None):
        for word in (None, "", "   "):
            with pytest.raises(click.ClickException, match="score-owner-authorization"):
                _require_score_selection_options("score_gap_v1", INSTRUMENT, (), None,
                                                 execute=True, authorization=word)
        _require_score_selection_options("score_gap_v1", INSTRUMENT, (), None,
                                         execute=True, authorization="owner-approved synthetic guard control")


def test_policy_excludes_replica_like_suffixes_but_legacy_discovery_is_unchanged(tmp_path):
    case = Case(tmp_path).base()
    case.record("P", "cfg_rep1_old", 99)
    case.record("Q", "cfg_rep1_old", 99)
    result, value = policy(case)
    assert "cfg_rep1_old" not in json.dumps(value)
    assert len(value["series_census"]) == 6
    legacy = case.invoke(policy=False)
    assert legacy.exit_code == 0, legacy.output
    assert "→ cfg_rep1_old" in legacy.output


def test_default_preview_matches_registered_historical_source_without_score_reads(tmp_path):
    """Compare c08 previews and captured canonical bytes; no scorer or write runs."""
    repository = Path(__file__).resolve().parents[2]
    historical = subprocess.run(["git", "show", "c08bd9edde73ec06473393d479d5cc597641de6c:src/data_sheets_schema/cli/runs.py"],
                                cwd=repository, capture_output=True, check=False)
    if historical.returncode:
        pytest.skip("historical c08 source object is unavailable in this checkout")
    name = "data_sheets_schema.cli._historical_score_selection_runs"
    spec = importlib.util.spec_from_loader(name, loader=None, origin="registered c08 CLI source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        exec(compile(historical.stdout, "registered c08 CLI source", "exec"), module.__dict__)
        for scenario in ("default", "coverage-tie", "invalid", "ignore-reviews", "retired-option", "legacy-suffix"):
            case = Case(tmp_path / scenario)
            for label, slots in LABELS:
                case.record("P", label, 9 if scenario == "coverage-tie" else slots)
            if scenario == "legacy-suffix":
                case.record("P", "cfg_rep1_old", 99)
            extra = (("--ignore-reviews",) if scenario == "ignore-reviews" else
                     ("--review-margin", "2") if scenario == "retired-option" else ())
            invalid = ("cfg_rep2",) if scenario == "invalid" else ()
            before = snapshot(case.tmp)
            old = case.invoke(module=module, policy=False, extra=extra, invalid=invalid)
            current = case.invoke(policy=False, extra=extra, invalid=invalid)
            assert old.exit_code == current.exit_code
            assert old.output.encode() == current.output.encode(), scenario
            assert snapshot(case.tmp) == before
        # Reach the historical canonical construction through direct callbacks;
        # the writer is intercepted, no CLI execution option or mark is used.
        from data_sheets_schema import runs as model
        from data_sheets_schema.cli import runs as current_cli
        fresh = Case(tmp_path / "canonical-bytes")
        for label, slots in LABELS:
            fresh.record("P", label, slots)
        before = snapshot(fresh.tmp)
        canonical_bytes = []
        for implementation in (module, current_cli):
            captured = []

            def retain(record, path):
                captured.append(yaml.safe_dump(record.data["canonical"], sort_keys=False,
                                               allow_unicode=True).encode())
                return path

            with patch.object(model, "CONCAT_DIR", fresh.concat), \
                    patch.object(implementation, "_validates", lambda path: (True, "valid")), \
                    patch("data_sheets_schema.cli.provenance._require_repo_root_cwd", lambda name: None), \
                    patch("data_sheets_schema.provenance.ProvenanceRecord.write", retain):
                implementation.select_cmd.callback(method=METHOD, project="P", config="cfg",
                    allow_unverified=False, execute=True, ignore_reviews=False, review_margin=None,
                    supersede_all_runtimes=False)
            assert len(captured) == 1
            canonical_bytes.append(captured[0])
            assert snapshot(fresh.tmp) == before
        assert canonical_bytes[0] == canonical_bytes[1]
    finally:
        sys.modules.pop(name, None)
