"""Item discrimination and the within-project ordering gate (#2927).

The two semantic rubrics agree between projects and not inside them: on the
2026-09-12 reference set every AI_READI record scores 49/50 on rubric10, and
the reports printed within-project tables with nothing saying so. These pin
the measurement (items at ceiling or floor, distinct totals, tied pairs,
cross-rubric pair agreement on both bases) and the rule that withholds a
within-project order where a project has at most two distinct totals.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from data_sheets_schema.semantic_comparison import (
    ORDER_WITHHELD_AT_MOST, discrimination, item_scores, record_label,
    render_discrimination, withheld_projects, withholding_reason,
)

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = "reference_2026-09-12_cborg_runtime"


def r10(project, label, subs, adjusted=50, version=None):
    """subs: sub-element scores for element 1 (None = N/A); total is their sum,
    which stays at or below the rubric maximum of 50 for any fixture here."""
    total = sum(s for s in subs if s is not None)
    doc = {"rubric": "rubric10-semantic", "project": project, "label": label,
            "overall_score": {"total_points": total, "max_points": 50,
                              "adjusted_max_points": adjusted, "excluded_max_points": 50 - adjusted},
            "elements": [{"id": 1, "sub_elements": [
                {"score": s, **({"applicable": False} if s is None else {})} for s in subs]}]}
    if version is not None:
        doc["version"] = version
    return doc


def r20(project, label, total, adjusted=88, in_metadata=True):
    doc = {"rubric": "rubric20-semantic", "project": project,
           "overall_score": {"total_points": total, "max_points": 88,
                             "adjusted_max_points": adjusted, "excluded_max_points": 88 - adjusted},
           "categories": [{"questions": [{"id": 1, "score": 5, "max_score": 5},
                                         {"id": 2, "score": 1, "max_score": 1, "score_type": "pass_fail"}]}]}
    if in_metadata:
        doc["metadata"] = {"label": label}      # where rubric20 writes it
    else:
        doc["label"] = label
    return doc


# --- items -------------------------------------------------------------------

def test_items_are_named_by_position_and_question_id():
    assert item_scores(r10("P", "a", [1, 0, None])) == {"E1.1": (1, 1), "E1.2": (0, 1), "E1.3": (None, 1)}
    assert item_scores(r20("P", "a", 60)) == {"Q1": (5, 5), "Q2": (1, 1)}
    assert record_label(r20("P", "a", 60)) == "a"
    assert record_label(r20("P", "b", 60, in_metadata=False)) == "b"


def test_ceiling_and_floor_are_read_wherever_the_item_was_scored():
    block = discrimination([r10("P", "a", [1, 0, 1, None, 1]),
                            r10("P", "b", [1, 0, 0, None, None]),
                            r10("P", "c", [1, 0, 1, None, 1])])
    entry = block["rubrics"]["rubric10-semantic"]
    assert entry["ceiling"] == ["E1.1", "E1.5"]     # E1.5 is N/A once, at max elsewhere
    assert entry["floor"] == ["E1.2"]
    assert entry["never_scored"] == ["E1.4"]
    assert entry["not_scored"] == {"E1.4": 3, "E1.5": 1}
    text = "\n".join(render_discrimination(block))
    assert "At ceiling: 2/5 (E1.1, E1.5 (not scored on 1))" in text
    assert "At floor: 1/5 (E1.2)" in text


def test_items_that_vary_are_per_project_and_count_applicability_changes():
    block = discrimination([r10("P", "a", [1, 1, 1]), r10("P", "b", [1, 0, None]),
                            r10("Q", "a", [0, 1, 1]), r10("Q", "b", [0, 1, 1])])
    projects = block["rubrics"]["rubric10-semantic"]["projects"]
    assert projects["P"]["varying_items"] == ["E1.2", "E1.3"]
    assert projects["Q"]["varying_items"] == []


# --- distinct totals, ties and the gate --------------------------------------

def test_distinct_totals_and_ties_are_counted_on_each_basis():
    # a and b tie on points but not once b's N/A point is taken out.
    docs = [r10("P", "a", [1, 1]), r10("P", "b", [1, 1], adjusted=49), r10("P", "c", [1, 0]),
            r10("P", "d", [0, 0])]
    p = discrimination(docs)["rubrics"]["rubric10-semantic"]["projects"]["P"]
    assert p["pairs"] == 6
    assert p["distinct_totals"] == {"adjusted": 4, "fixed": 3}
    assert p["tied_pairs"] == {"adjusted": 0, "fixed": 1}
    assert p["withheld"] == {"adjusted": None, "fixed": None}


@pytest.mark.parametrize("totals,withheld", [([2, 2, 2], True), ([2, 1, 2], True),
                                              ([2, 1, 0], False)])
def test_at_most_two_distinct_totals_withholds_the_order_and_says_why(totals, withheld):
    docs = [r10("P", f"rep{i}", [1] * t + [0] * (2 - t)) for i, t in enumerate(totals)]
    block = discrimination(docs)
    reasons = withheld_projects(block, "rubric10-semantic")
    distinct = len(set(totals))
    assert ("P" in reasons) is withheld
    assert ORDER_WITHHELD_AT_MOST == 2
    text = "\n".join(render_discrimination(block))
    if withheld:
        assert reasons["P"] == {"adjusted": withholding_reason(distinct),
                                "fixed": withholding_reason(distinct)}
        assert f"**withheld on both bases**: {distinct} distinct total" in text
        assert "cannot rank records within the project" in text
    else:
        assert withholding_reason(distinct) is None
        assert "**withheld" not in text and "not withheld on either basis" in text


def test_a_gate_that_holds_on_one_basis_only_names_that_basis():
    # Points 2, 2, 1 (fixed: 2 distinct); adjusted 2/50, 2/49, 1/50 (3 distinct).
    docs = [r10("P", "a", [1, 1]), r10("P", "b", [1, 1], adjusted=49), r10("P", "c", [1, 0])]
    block = discrimination(docs)
    assert withheld_projects(block, "rubric10-semantic") == {"P": {"fixed": withholding_reason(2)}}
    assert "**withheld (fixed)**" in "\n".join(render_discrimination(block))


# --- cross-rubric pairs --------------------------------------------------------

def test_cross_rubric_pairs_join_on_project_and_label_and_report_both_bases():
    docs = [
        r10("P", "a", [1, 1, 1]), r20("P", "a", 70),
        r10("P", "b", [1, 1, 0], adjusted=48), r20("P", "b", 60),
        r10("P", "c", [1, 1, 0]), r20("P", "c", 60),
        r10("Q", "a", [1, 0, 0]), r20("Q", "a", 50, adjusted=58),
    ]
    block = discrimination(docs)["cross_rubric"]
    assert block["rubrics"] == ("rubric10-semantic", "rubric20-semantic")
    assert block["unjoined"] == [] and len(block["tables"]) == 1
    cross = block["tables"][0]
    assert cross["rubrics"] == ("rubric10-semantic", "rubric20-semantic")
    assert cross["joined_records"] == 4
    # fixed: P.a>P.b, P.a>P.c same; P.b vs P.c tied on both.
    assert cross["bases"]["fixed"]["within"] == {"pairs": 3, "same": 2, "opposite": 0,
                                                  "tied": 1, "undefined": 0}
    # adjusted: P.b is 2/48 > P.c 2/50 on rubric10, tied on rubric20 -> still tied.
    assert cross["bases"]["adjusted"]["within"]["tied"] == 1
    # Q.a: 1/50 and 50/88 on the fixed basis are below every P record on both
    # rubrics; on the adjusted basis its rubric20 50/58 is above every P
    # record's, so every between-project pair turns opposite.
    assert cross["bases"]["fixed"]["between"] == {"pairs": 3, "same": 3, "opposite": 0,
                                                   "tied": 0, "undefined": 0}
    assert cross["bases"]["adjusted"]["between"] == {"pairs": 3, "same": 0, "opposite": 3,
                                                      "tied": 0, "undefined": 0}
    text = "\n".join(render_discrimination(discrimination(docs)))
    assert "| N/A-adjusted (points / applicable maximum) | between projects | 3 | 0 | 3 | 0 |" in text
    assert "| fixed (points / full rubric maximum) | within project | 3 | 2 | 0 | 1 |" in text


def test_a_record_rated_once_under_one_rubric_is_named_not_joined():
    docs = [r10("P", "a", [1]), r20("P", "a", 70), r10("P", "b", [0]), r20("P", "c", 60)]
    cross = discrimination(docs)["cross_rubric"]
    assert cross["tables"][0]["joined_records"] == 1
    assert cross["unjoined"] == [("rubric10-semantic", "P", "b"), ("rubric20-semantic", "P", "c")]
    assert "Not joined" in "\n".join(render_discrimination(discrimination(docs)))


def test_one_rubric_gives_no_cross_rubric_table_and_says_so():
    block = discrimination([r10("P", "a", [1]), r10("P", "b", [0])])
    assert block["cross_rubric"]["rubrics"] is None
    assert "Cross-rubric agreement: not computed — 1 rubric in the cohort" in "\n".join(
        render_discrimination(block))


def test_a_record_rated_twice_is_left_out_not_chosen_between():
    docs = [r10("P", "a", [1]), r10("P", "a", [0]), r10("P", "b", [1]), r10("P", "c", [0])]
    block = discrimination(docs)
    assert block["duplicates"] == [("P", "a", "rubric10-semantic")]
    assert block["rubrics"]["rubric10-semantic"]["records"] == 2
    assert "Rated more than once" in "\n".join(render_discrimination(block))


def test_a_duplicate_records_other_rating_is_not_said_to_have_no_partner():
    """#3291: P/a's rubric20 rating has a partner; the partner was set aside."""
    docs = [r10("P", "a", [1]), r10("P", "a", [0]), r20("P", "a", 70),
            r10("P", "b", [1]), r20("P", "b", 60), r10("P", "c", [0]), r20("P", "c", 50),
            r20("P", "d", 40)]
    block = discrimination(docs)
    cross = block["cross_rubric"]
    assert cross["partner_duplicated"] == [("rubric20-semantic", "P", "a")]
    assert cross["unjoined"] == [("rubric20-semantic", "P", "d")]
    assert cross["tables"][0]["joined_records"] == 2
    text = "\n".join(render_discrimination(block))
    assert ("Not joined (no rating of the same (project, label) under the other rubric): "
            "P `d` (rubric20-semantic).") in text
    assert ("Not joined because the record's rating under the other rubric was rated more than "
            "once and left out: P `a` (rubric20-semantic).") in text


def test_a_rubric_held_under_two_versions_is_measured_per_version():
    """#3290: a version offset is neither a distinct total nor a pair order."""
    docs = [r10("P", "a", [1, 1, 1], version="1.1"), r20("P", "a", 70, adjusted=88),
            r10("P", "b", [1, 0, 0], version="1.0"), r20("P", "b", 60),
            r10("P", "c", [1, 0, 0], version="1.0"), r20("P", "c", 50)]
    for doc in docs:
        if doc["rubric"] == "rubric20-semantic":
            doc["version"] = "1.0"
    block = discrimination(docs)
    assert sorted(block["rubrics"]) == ["rubric10-semantic v1.0", "rubric10-semantic v1.1",
                                        "rubric20-semantic"]
    # Pooled, P would have 2 distinct rubric10 totals (3 and 1) from a version offset.
    assert block["rubrics"]["rubric10-semantic v1.0"]["projects"]["P"]["distinct_totals"] == {
        "adjusted": 1, "fixed": 1}
    assert block["rubrics"]["rubric10-semantic v1.1"]["records"] == 1
    tables = {t["rubrics"]: t for t in block["cross_rubric"]["tables"]}
    assert set(tables) == {("rubric10-semantic v1.0", "rubric20-semantic"),
                           ("rubric10-semantic v1.1", "rubric20-semantic")}
    # Only b-c is ordered: rubric10 v1.0 ties them, so the pair is tied.
    assert tables[("rubric10-semantic v1.0", "rubric20-semantic")]["bases"]["fixed"]["within"] == {
        "pairs": 1, "same": 0, "opposite": 0, "tied": 1, "undefined": 0}
    assert tables[("rubric10-semantic v1.1", "rubric20-semantic")]["bases"]["fixed"]["within"]["pairs"] == 0
    assert block["cross_rubric"]["unjoined"] == []
    text = "\n".join(render_discrimination(block))
    assert "Split by instrument version: rubric10-semantic." in text
    assert "**rubric10-semantic v1.1** — 1 records" in text
    # One version throughout keeps the bare name.
    single = discrimination([r10("P", "a", [1], version="1.0"), r10("P", "b", [0], version="1.0")])
    assert list(single["rubrics"]) == ["rubric10-semantic"]
    assert "Split by instrument version" not in "\n".join(render_discrimination(single))


# --- the reports -----------------------------------------------------------------

def _write(tmp_path, docs):
    paths = []
    for i, doc in enumerate(docs):
        path = tmp_path / f"{i}_evaluation.json"
        path.write_text(json.dumps(doc))
        paths.append(path)
    return paths


def test_the_comparison_report_carries_the_block_over_the_named_cohort(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    from report_semantic_comparison import report
    docs = [r10("P", "a", [1, 1]), r10("P", "a", [1, 0]), r10("P", "b", [1, 1]), r10("P", "c", [1, 1])]
    paths = _write(tmp_path, docs)
    before = [p.read_bytes() for p in paths]
    whole = report(paths)
    assert "Rated more than once" in whole
    # The primaries only: P has one distinct total, so no order.
    primaries = report(paths, [paths[0], paths[2], paths[3]])
    assert "Rated more than once" not in primaries
    assert "| P | 3 | 1 / 1 |" in primaries
    assert "**withheld on both bases**: 1 distinct total" in primaries
    with pytest.raises(ValueError, match="cohort names evaluations the report does not"):
        report(paths[:2], [paths[3]])
    assert [p.read_bytes() for p in paths] == before


def test_arm_comparison_partitions_by_evaluator_and_flags_the_project_cell():
    spec = importlib.util.spec_from_file_location("arm_comparison_2927", ROOT / "scripts" / "arm_comparison.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    scores = {"rubric10": {k: {p: [] for p in m.PROJECTS} for k, *_ in m.ARMS}}
    arms = [k for k, *_ in m.ARMS]

    def entry(label, total, evaluator):
        doc = r10("VOICE", label, [1] * total + [0] * (3 - total))
        doc["model"] = {"evaluator_model": evaluator}
        return {"label": label, "total": total, "max": 50, "adjusted_max": 50, "pct": 2.0 * total,
                "evaluator": evaluator, "file": f"VOICE_{label}_evaluation.json", "doc": doc}

    # Pooled, the two evaluators give three distinct totals; each alone gives two.
    scores["rubric10"][arms[-2]]["VOICE"] = [entry("x_rep1", 3, "one"), entry("x_rep2", 2, "one")]
    scores["rubric10"][arms[-1]]["VOICE"] = [entry("y_rep1", 1, "two"), entry("y_rep2", 1, "two")]
    cohorts = m.rubric_discrimination(scores)
    assert [(e, a) for e, a, _v, _b in cohorts] == [("one", [arms[-2]]), ("two", [arms[-1]])]
    data = {k: {p: [] for p in m.PROJECTS} for k in arms}
    text = m.render_markdown(data, scores)
    assert "| VOICE (no within-project order — one: 2 distinct totals; two: 1 distinct total) |" in text
    assert "## Item discrimination and within-project orderings, one evaluations (#2927)" in text
    assert "| AI_READI | – |" in text                 # no evaluations, no flag
    assert m._withheld_cell("CM4AI", [("e", {"fixed": withholding_reason(2)})]) == (
        "CM4AI (no within-project order — e, fixed basis: 2 distinct totals)")


def test_arm_comparison_gates_each_rubric_version_of_one_evaluator_apart():
    """#3290: one evaluator's v1.0 and v1.1 totals are not pooled."""
    spec = importlib.util.spec_from_file_location("arm_comparison_3290", ROOT / "scripts" / "arm_comparison.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    scores = {"rubric10": {k: {p: [] for p in m.PROJECTS} for k, *_ in m.ARMS}}
    arms = [k for k, *_ in m.ARMS]

    def entry(label, total, version):
        doc = r10("VOICE", label, [1] * total + [0] * (3 - total), version=version)
        return {"label": label, "total": total, "max": 50, "adjusted_max": 50, "pct": 2.0 * total,
                "evaluator": "one", "file": f"VOICE_{label}_evaluation.json", "doc": doc}

    # Pooled: 3 distinct totals, not withheld. Per version: 2 and 1, both withheld.
    scores["rubric10"][arms[-1]]["VOICE"] = [entry("x_rep1", 3, "1.1"), entry("x_rep2", 2, "1.0"),
                                             entry("x_rep3", 1, "1.0"), entry("x_rep4", 3, "1.1")]
    text = m.render_markdown({k: {p: [] for p in m.PROJECTS} for k in arms}, scores)
    assert ("| VOICE (no within-project order — one v1.0: 2 distinct totals; "
            "one v1.1: 1 distinct total) |") in text
    assert "rubric10-semantic v1.0, v1.1" in text
    assert "measured per version (#3290)" in text


@pytest.mark.corpus
def test_the_2026_09_12_reference_set_reproduces_the_issue_and_is_not_written(tmp_path):
    """#2927's evidence, recomputed from the committed rating1 files."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from report_semantic_comparison import report
    evaluations = ROOT / "data" / "evaluation_llm"
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(evaluations.rglob("*")) if p.is_file()}
    paths = [p for rubric in ("rubric10", "rubric20")
             for p in sorted((evaluations / f"{rubric}_semantic" / REFERENCE).glob("*_rating1_evaluation.json"))]
    assert len(paths) == 48
    block = discrimination(json.loads(p.read_bytes()) for p in paths)
    r10_block, r20_block = block["rubrics"]["rubric10-semantic"], block["rubrics"]["rubric20-semantic"]
    assert block["duplicates"] == []
    assert r10_block["ceiling"] == [
        "E1.2", "E1.4", "E2.1", "E2.2", "E2.4", "E2.5", "E3.3", "E3.5", "E4.2", "E5.4", "E6.5",
        "E7.1", "E7.2", "E7.3", "E7.4", "E7.5", "E8.1", "E8.2", "E8.5", "E9.1", "E9.4", "E10.4"]
    assert r10_block["items"] == 50
    assert r20_block["ceiling"] == ["Q2", "Q5", "Q6", "Q16"]
    projects = r10_block["projects"]
    assert projects["AI_READI"]["distinct_totals"] == {"adjusted": 1, "fixed": 1}
    assert projects["AI_READI"]["varying_items"] == []
    assert projects["VOICE"]["distinct_totals"] == {"adjusted": 2, "fixed": 2}
    assert projects["VOICE"]["varying_items"] == ["E3.4", "E10.3"]
    assert set(withheld_projects(block, "rubric10-semantic")) == {"AI_READI", "VOICE"}
    assert withheld_projects(block, "rubric20-semantic") == {}
    assert len(block["cross_rubric"]["tables"]) == 1
    cross = block["cross_rubric"]["tables"][0]["bases"]
    triple = lambda c: (c["pairs"], c["same"], c["opposite"], c["tied"])  # noqa: E731
    assert triple(cross["adjusted"]["within"]) == (60, 25, 8, 27)
    assert triple(cross["adjusted"]["between"]) == (216, 193, 2, 21)
    assert triple(cross["fixed"]["within"]) == (60, 21, 12, 27)
    assert triple(cross["fixed"]["between"]) == (216, 181, 12, 23)
    text = report(paths)
    assert "| AI_READI | 6 | 1 / 1 |" in text and "| VOICE | 6 | 2 / 2 |" in text
    assert text.count("**withheld on both bases**") == 2
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(evaluations.rglob("*")) if p.is_file()}
    assert after == before
