"""The #2927 discrimination block in the legacy summarizers' reports (#3281).

`scripts/summarize_rubric{10,20}_results.py` read the presence/direct-API
evaluations under data/evaluation_llm/rubric10 and rubric20. Their items
already have the shape `item_scores()` reads; what they lack is a generation
label, and one directory holds two evaluators, two kinds of record and (for
rubric20, #275) potentially two maxima. These pin the mapping onto
`discrimination()` and that the block is measured per cohort, never over the
folder. The summarizers are run, not grepped (#278), with their output
redirected so no committed report is touched.
"""
import io
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from data_sheets_schema.semantic_comparison import (  # noqa: E402
    discrimination, item_scores, legacy_cohorts, legacy_record, render_legacy_discrimination,
)

HYBRID = {"evaluation_type": "rule_based_with_quality_heuristics",
          "name": "hybrid-heuristic-evaluator", "temperature": "N/A"}
JUDGE = {"evaluation_type": "llm_as_judge", "name": "claude-fable-5", "temperature": 0.0}


def legacy10(project, d4d_file, subs, model=HYBRID, kind="concatenated"):
    """A rubric10 evaluation as the legacy path writes it: sub-elements carry
    a 0/1 score and no max_score; the loader adds `evaluation_type`."""
    return {"rubric": "rubric10", "version": "1.0", "project": project, "method": "m",
            "d4d_file": d4d_file, "model": dict(model), "evaluation_type": kind,
            "overall_score": {"total_points": sum(subs), "max_points": 50,
                              "percentage": 2.0 * sum(subs)},
            "elements": [{"id": 1, "name": "E", "element_score": sum(subs), "element_max": 5,
                          "sub_elements": [{"name": f"s{i}", "score": s} for i, s in enumerate(subs)]}]}


def legacy20(project, d4d_file, scores, model=HYBRID, kind="concatenated", maximum=84):
    """A rubric20 evaluation as the legacy path writes it: `questions[]` with
    `max_score`, repeated under a `categories` mapping."""
    questions = [{"id": i, "name": f"q{i}", "score": s, "max_score": 5, "score_type": "numeric"}
                 for i, s in enumerate(scores, start=1)]
    total = sum(scores)
    return {"rubric": "rubric20", "version": "1.0", "project": project, "method": "m",
            "d4d_file": d4d_file, "model": dict(model), "evaluation_type": kind,
            "overall_score": {"total_points": total, "max_points": maximum,
                              "percentage": 100.0 * total / maximum},
            "questions": questions,
            "categories": {"Structural Completeness": {
                "name": "Structural Completeness", "questions": questions,
                "category_score": total, "category_max": 5 * len(scores)}}}


# --- the mapping -------------------------------------------------------------

def test_legacy_items_map_onto_item_scores():
    assert item_scores(legacy10("P", "a.yaml", [1, 0, 1])) == {"E1.1": (1, 1), "E1.2": (0, 1), "E1.3": (1, 1)}
    # The questions listed twice (top level and under their category) are one item each.
    assert item_scores(legacy20("P", "a.yaml", [5, 3])) == {"Q1": (5, 5), "Q2": (3, 5)}


def test_the_rated_file_is_the_label_where_the_evaluation_names_none():
    doc = legacy10("P", "data/x/P_d4d.yaml", [1])
    mapped = legacy_record(doc)
    assert mapped["label"] == "data/x/P_d4d.yaml"
    assert "label" not in doc, "the evaluation itself must not be modified"
    named = {**doc, "label": "2026-09-01_run"}
    assert legacy_record(named) is named
    unnamed = {k: v for k, v in doc.items() if k != "d4d_file"}
    assert legacy_record(unnamed) is unnamed


def test_a_file_rated_twice_in_a_cohort_is_a_duplicate_not_two_records():
    docs = [legacy10("P", "same.yaml", [1, 1]), legacy10("P", "same.yaml", [0, 1]),
            legacy10("P", "other.yaml", [0, 0])]
    block = discrimination(legacy_record(d) for d in docs)
    assert block["duplicates"] == [("P", "same.yaml", "rubric10")]
    assert block["rubrics"]["rubric10"]["records"] == 1
    text = "\n".join(render_legacy_discrimination(docs))
    assert "Rated more than once" in text and "`same.yaml`" in text


# --- the cohorts -------------------------------------------------------------

def test_cohorts_split_by_record_kind_evaluator_and_maximum():
    docs = [legacy20("P", "a", [5], model=HYBRID), legacy20("P", "b", [5], model=JUDGE),
            legacy20("P", "c", [5], kind="individual"), legacy20("P", "d", [5], maximum=88),
            legacy20("P", "e", [4], model=HYBRID)]
    keys = {key: [d["d4d_file"] for d in members] for key, members in legacy_cohorts(docs)}
    assert keys == {("concatenated", "claude-fable-5", 84): ["b"],
                    ("concatenated", "hybrid-heuristic-evaluator", 84): ["a", "e"],
                    ("concatenated", "hybrid-heuristic-evaluator", 88): ["d"],
                    ("individual", "hybrid-heuristic-evaluator", 84): ["c"]}


def test_pooling_two_evaluators_would_manufacture_an_order():
    """Each evaluator gives the project's three records one total; only their
    offset differs. Pooled, that offset reads as separation; per cohort, the
    order is withheld under both evaluators."""
    docs = ([legacy10("P", f"f{i}.yaml", [1, 1]) for i in range(3)]
            + [legacy10("P", f"f{i}.yaml", [0, 1], model=JUDGE) for i in range(3)])
    pooled = discrimination(legacy_record(d) for d in docs)
    assert pooled["duplicates"], "pooled, the two evaluators' ratings of one file collide"
    cohorts = legacy_cohorts(docs)
    assert len(cohorts) == 2
    for _key, members in cohorts:
        entry = discrimination(legacy_record(d) for d in members)["rubrics"]["rubric10"]
        assert entry["projects"]["P"]["distinct_totals"] == {"adjusted": 1, "fixed": 1}
        assert all(entry["projects"]["P"]["withheld"].values())
    text = "\n".join(render_legacy_discrimination(docs))
    assert text.count("## Item discrimination and within-project orderings") == 2
    assert "concatenated evaluations by claude-fable-5 scored out of 50 (#2927)" in text
    assert "concatenated evaluations by hybrid-heuristic-evaluator scored out of 50 (#2927)" in text
    assert "Rated more than once" not in text


def test_an_unrecorded_evaluator_is_named_as_such():
    doc = legacy10("P", "a.yaml", [1])
    doc["model"] = {}
    text = "\n".join(render_legacy_discrimination([doc]))
    assert "concatenated evaluations by an unrecorded evaluator scored out of 50" in text


# --- the summarizers ---------------------------------------------------------

@pytest.fixture
def summarizer(request):
    import importlib
    mod = importlib.import_module(request.param)
    real = mod.EVAL_DIR
    with tempfile.TemporaryDirectory() as tmp:
        mod.EVAL_DIR = Path(tmp)
        try:
            yield mod
        finally:
            mod.EVAL_DIR = real


def _report(mod, results):
    with redirect_stdout(io.StringIO()):
        mod.create_detailed_report(results)
    return (mod.EVAL_DIR / "summary_report.md").read_text()


@pytest.mark.parametrize("summarizer", ["summarize_rubric10_results"], indirect=True)
def test_rubric10_report_carries_the_block_per_cohort(summarizer):
    docs = [legacy10("AI_READI", "a.yaml", [1, 1, 0]), legacy10("AI_READI", "b.yaml", [1, 1, 0]),
            legacy10("AI_READI", "c.yaml", [1, 0, 0], kind="individual")]
    text = _report(summarizer, docs)
    assert "Rubric10 Detailed Evaluation Report" in text
    assert "## Item discrimination and within-project orderings, concatenated evaluations by hybrid-heuristic-evaluator scored out of 50 (#2927)" in text
    assert "## Item discrimination and within-project orderings, individual evaluations by hybrid-heuristic-evaluator scored out of 50 (#2927)" in text
    assert "**withheld on both bases**: 1 distinct total" in text
    assert "At ceiling: 1/3 (E1.1)" in text


@pytest.mark.parametrize("summarizer", ["summarize_rubric20_results"], indirect=True)
def test_rubric20_report_carries_the_block_per_maximum(summarizer):
    docs = [legacy20("VOICE", "a.yaml", [5, 3]), legacy20("VOICE", "b.yaml", [5, 0]),
            legacy20("VOICE", "c.yaml", [5, 3], maximum=88)]
    text = _report(summarizer, docs)
    assert "Scored out of 84" in text and "Scored out of 88" in text
    assert "concatenated evaluations by hybrid-heuristic-evaluator scored out of 84 (#2927)" in text
    assert "concatenated evaluations by hybrid-heuristic-evaluator scored out of 88 (#2927)" in text
    assert "At ceiling: 1/2 (Q1)" in text


# --- what each block says it measured (#3570) --------------------------------

def test_each_block_counts_its_cohort_against_every_evaluation_above():
    """The report above pools every evaluation loaded, of both kinds; a block
    measures one cohort, so it must not claim all of an evaluator's
    evaluations above. It says how many of the total it measured and that the
    rest are in no count."""
    docs = [legacy10("P", "a.yaml", [1, 1]), legacy10("P", "b.yaml", [0, 1]),
            legacy10("P", "c.yaml", [1, 0], kind="individual"),
            legacy10("P", "d.yaml", [1, 1], model=JUDGE)]
    text = "\n".join(render_legacy_discrimination(docs))
    assert "Measured on the hybrid-heuristic-evaluator evaluations above" not in text
    assert "Measured on the claude-fable-5 evaluations above" not in text
    assert ("Measured on 2 of the 4 evaluations above: the concatenated evaluations by "
            "hybrid-heuristic-evaluator scored out of 50. The other 2 are in no count in this "
            "block; each is measured in a block of its own, one rating per record.") in text
    assert ("Measured on 1 of the 4 evaluations above: the individual evaluations by "
            "hybrid-heuristic-evaluator scored out of 50. The other 3 are in no count in this "
            "block") in text
    assert ("Measured on 1 of the 4 evaluations above: the concatenated evaluations by "
            "claude-fable-5 scored out of 50. The other 3") in text
    assert text.count("Evaluations by any other evaluator are in no count in this block") == 3
    assert "no count below" not in text


def test_no_block_denies_a_count_that_a_later_block_makes():
    """Cohort blocks are rendered one after another, so a block above another
    must not say the other cohorts' evaluations are "in no count below": the
    next block counts them (#3598). Every block but the last is checked
    against what follows it."""
    docs = [legacy10("P", "a.yaml", [1, 1]), legacy10("P", "b.yaml", [0, 1]),
            legacy10("P", "c.yaml", [1, 0], kind="individual"),
            legacy10("P", "d.yaml", [1, 1], model=JUDGE)]
    text = "\n".join(render_legacy_discrimination(docs))
    blocks = re.split(r"(?m)^## Item discrimination", text)[1:]
    assert len(blocks) == 3
    for block in blocks[:-1]:
        assert "no count below" not in block


def test_a_single_cohort_names_no_others():
    docs = [legacy10("P", "a.yaml", [1, 1]), legacy10("P", "b.yaml", [0, 1])]
    text = "\n".join(render_legacy_discrimination(docs))
    assert ("Measured on 2 of the 2 evaluations above: the concatenated evaluations by "
            "hybrid-heuristic-evaluator scored out of 50, one rating per record.") in text
    assert "The other" not in text


def test_measured_on_and_left_out_are_exclusive():
    from data_sheets_schema.semantic_comparison import render_discrimination
    block = discrimination([legacy_record(legacy10("P", "a.yaml", [1]))])
    with pytest.raises(ValueError):
        render_discrimination(block, measured_on="1 of 2", left_out=["x"])


@pytest.mark.parametrize("summarizer", ["summarize_rubric10_results"], indirect=True)
def test_rubric10_report_block_counts_against_the_report_total(summarizer):
    docs = [legacy10("AI_READI", "a.yaml", [1, 1, 0]), legacy10("AI_READI", "b.yaml", [1, 1, 0]),
            legacy10("AI_READI", "c.yaml", [1, 0, 0], kind="individual")]
    text = _report(summarizer, docs)
    assert "**Total Evaluations:** 3" in text
    assert "Measured on 2 of the 3 evaluations above: the concatenated evaluations" in text
    assert "Measured on 1 of the 3 evaluations above: the individual evaluations" in text
