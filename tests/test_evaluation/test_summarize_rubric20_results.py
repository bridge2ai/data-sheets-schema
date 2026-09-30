"""scripts/summarize_rubric20_results.py reads both shapes of `categories` (#3524).

The hybrid evaluator writes `categories` as a mapping keyed on category name
and repeats the questions at the top level; the claude-fable-5 evaluations
under data/evaluation_llm/rubric20/concatenated write a list of named entries
and list the questions only under them. All three writers read categories by
name, so on the list shape every one raised AttributeError. These build the
same scores in both shapes and require the same summary from each. The
summarizer is run with its output redirected, so no committed report is
touched.
"""
import csv
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import summarize_rubric20_results as mod  # noqa: E402

CATEGORY_SCORES = {"Structural Completeness": [5, 4, 3, 5, 1],
                   "Metadata Quality & Content": [5, 5, 2, 4, 0],
                   "Technical Documentation": [3, 3, 3, 3, 1],
                   "FAIRness & Accessibility": [4, 2, 5, 5, 1]}


def _categories(category_scores=CATEGORY_SCORES):
    categories, qid = [], 1
    for name, scores in category_scores.items():
        questions = []
        for score in scores:
            maximum = 1 if qid % 5 == 0 else 5
            questions.append({"id": qid, "name": f"question {qid}", "score": score,
                              "max_score": maximum,
                              "score_type": "pass_fail" if maximum == 1 else "numeric"})
            qid += 1
        categories.append({"name": name, "questions": questions,
                           "category_score": sum(scores),
                           "category_max": sum(q["max_score"] for q in questions)})
    return categories


def _evaluation(project, d4d_file, shape, kind="concatenated",
                category_scores=CATEGORY_SCORES):
    categories = _categories(category_scores)
    total = sum(c["category_score"] for c in categories)
    doc = {"rubric": "rubric20", "version": "1.0", "project": project,
           "method": "claudecode_agent", "d4d_file": d4d_file, "evaluation_type": kind,
           "overall_score": {"total_points": total, "max_points": 84,
                             "percentage": 100.0 * total / 84}}
    if shape == "mapping":  # the hybrid evaluator
        doc["categories"] = {c["name"]: c for c in categories}
        doc["questions"] = [q for c in categories for q in c["questions"]]
    else:  # the claude-fable-5 evaluations
        doc["categories"] = categories
    return doc


@pytest.fixture
def out_dir():
    real = mod.EVAL_DIR
    with tempfile.TemporaryDirectory() as tmp:
        mod.EVAL_DIR = Path(tmp)
        try:
            yield mod.EVAL_DIR
        finally:
            mod.EVAL_DIR = real


def _run_all(results):
    with redirect_stdout(io.StringIO()):
        mod.create_csv_summary(results)
        mod.create_markdown_table(results)
        mod.create_detailed_report(results)


def _csv_rows(out):
    with open(out / "all_scores.csv", newline="") as f:
        return {row["project"]: row for row in csv.DictReader(f)}


@pytest.mark.parametrize("kind", ["concatenated", "individual"])
def test_both_shapes_give_the_same_summary(out_dir, kind):
    _run_all([_evaluation("AI_READI", "a/AI_READI_d4d.yaml", "mapping", kind),
              _evaluation("VOICE", "a/VOICE_d4d.yaml", "list", kind)])
    rows = _csv_rows(out_dir)
    columns = ["cat1_structural", "cat2_metadata", "cat3_technical", "cat4_fairness",
               "question_scores"]
    mapped = {c: rows["AI_READI"][c] for c in columns}
    listed = {c: rows["VOICE"][c] for c in columns}
    assert mapped == listed
    assert [mapped[c] for c in columns[:4]] == [str(sum(s)) for s in CATEGORY_SCORES.values()]
    # Twenty questions, each once: neither shape drops them or counts them twice.
    assert len(listed["question_scores"].split(",")) == 20

    table = (out_dir / "summary_table.md").read_text()
    lines = [line for line in table.splitlines()
             if line.startswith("| AI_READI |") or line.startswith("| VOICE |")]
    assert len(lines) == 2
    assert lines[0].split("|")[2:] == lines[1].split("|")[2:]
    if kind == "concatenated":
        # The top and weakest questions come from the list shape's categories too.
        assert "N/A" not in lines[1]

    report = (out_dir / "summary_report.md").read_text()
    for name, scores in CATEGORY_SCORES.items():
        assert f"### {name}\n- Average score: {float(sum(scores)):.1f}\n" in report


def test_the_list_shape_is_read_by_name_not_position():
    doc = _evaluation("P", "p.yaml", "list")
    doc["categories"].reverse()
    by_name = mod.categories_by_name(doc)
    assert list(by_name) == list(reversed(CATEGORY_SCORES))
    assert by_name["Structural Completeness"]["category_score"] == 18


def test_a_mapping_is_returned_as_written():
    doc = _evaluation("P", "p.yaml", "mapping")
    assert mod.categories_by_name(doc) is doc["categories"]
    assert mod.categories_by_name({}) == {}


@pytest.mark.parametrize("damage, message", [
    (lambda cats: cats[1].pop("name"), "a category with no name"),
    (lambda cats: cats[1].update(name=cats[0]["name"]), "category 'Structural Completeness' twice"),
])
def test_a_category_the_summary_cannot_address_is_refused(damage, message):
    doc = _evaluation("P", "p.yaml", "list")
    damage(doc["categories"])
    with pytest.raises(ValueError, match=message):
        mod.categories_by_name(doc)


def test_the_detailed_report_pools_the_list_shaped_categories(out_dir):
    """The Category Performance averages count the list-shaped record (#3660).

    The two records carry different scores, so dropping either one moves
    every category's pooled average off the mean of the two.
    """
    other = {name: [max(s - 1, 0) for s in scores]
             for name, scores in CATEGORY_SCORES.items()}
    _run_all([_evaluation("AI_READI", "a/AI_READI_d4d.yaml", "mapping"),
              _evaluation("VOICE", "a/VOICE_d4d.yaml", "list", category_scores=other)])
    report = (out_dir / "summary_report.md").read_text()
    for name, scores in CATEGORY_SCORES.items():
        pooled = (sum(scores) + sum(other[name])) / 2
        assert pooled not in (float(sum(scores)), float(sum(other[name])))
        assert f"### {name}\n- Average score: {pooled:.1f}\n" in report


def test_the_top_level_questions_win_where_both_are_listed():
    doc = _evaluation("P", "p.yaml", "mapping")
    # Make the top-level copies differ from the category copies, so the
    # choice between the two lists is visible, not only double counting.
    doc["questions"] = [dict(q, score=0, name=f"top-level {q['id']}")
                        for q in doc["questions"]]
    questions = mod.questions_of(doc)
    assert [q["id"] for q in questions] == list(range(1, 21))
    assert [q["name"] for q in questions] == [f"top-level {i}" for i in range(1, 21)]
    assert all(q["score"] == 0 for q in questions)
    # A question listed only under a category is not read where a top-level
    # list exists (the difference from item_scores() the docstring names).
    doc["categories"]["Structural Completeness"]["questions"].append(
        {"id": 21, "name": "category only", "score": 5, "max_score": 5})
    assert 21 not in [q["id"] for q in mod.questions_of(doc)]
    listed = _evaluation("P", "p.yaml", "list")
    assert [q["id"] for q in mod.questions_of(listed)] == list(range(1, 21))
