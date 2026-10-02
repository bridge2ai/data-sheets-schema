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
    assert lines[0].split("|")[2:11] == lines[1].split("|")[2:11]
    if kind == "concatenated":
        # The top and weakest questions come from the list shape's categories too.
        assert "N/A" not in lines[1]

    report = (out_dir / "summary_report.md").read_text()
    for name, scores in CATEGORY_SCORES.items():
        assert f"#### {name}\n- Average score: {float(sum(scores)):.1f}\n" in report


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
        assert f"#### {name}\n- Average score: {pooled:.1f}\n" in report


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


# Cohort identity and lossless rating rows (#3632 / #3631).

def _identified(project="NEW_PROJECT", method="new_method", score_shift=0, **updates):
    scores = {name: [max(0, score - score_shift) for score in values]
              for name, values in CATEGORY_SCORES.items()}
    doc = _evaluation(project, "same_record.yaml", "list", category_scores=scores)
    doc.update(method=method, model={"name": "judge-a", "temperature": 0},
               metadata={"rubric_hash": "recorded-hash"},
               evaluation_timestamp="2026-10-02T00:00:00Z",
               _evaluation_file="concatenated/a_evaluation.json")
    doc.update(updates)
    return doc


def _all_csv_rows(out):
    with (out / "all_scores.csv").open(newline="") as stream:
        return list(csv.DictReader(stream))


def test_every_concatenated_rating_survives_including_same_evaluator_repeats(out_dir):
    docs = [_identified(),
            _identified(score_shift=1, _evaluation_file="concatenated/b_evaluation.json"),
            _identified(model={"name": "judge-b", "temperature": 0},
                        _evaluation_file="concatenated/c_evaluation.json"),
            _identified(method="claudecode_agent_core",
                        _evaluation_file="concatenated/core_evaluation.json")]
    _run_all(docs)
    table = (out_dir / "summary_table.md").read_text().split("## Top Performing")[0]
    assert table.count("| NEW_PROJECT |") == 4
    for doc in docs:
        assert table.count(doc["_evaluation_file"]) == 1
    rows = _all_csv_rows(out_dir)
    assert len(rows) == 4
    assert {r["evaluation_file"] for r in rows} == {d["_evaluation_file"] for d in docs}
    assert {r["evaluator"] for r in rows} == {"judge-a", "judge-b"}
    assert "Rated more than once" in (out_dir / "summary_report.md").read_text()


@pytest.mark.parametrize("different", [
    {"model": {"name": "judge-b", "temperature": 0}},
    {"model": {"name": "judge-a", "temperature": 1}},
    {"version": "2.0"},
    {"metadata": {"rubric_hash": "another-recorded-hash"}},
    {"evaluation_type": "individual"},
])
def test_all_report_averages_separate_recorded_instruments(out_dir, different):
    first = _identified()
    second = _identified(score_shift=2, **different)
    _run_all([first, second])
    report = (out_dir / "summary_report.md").read_text()
    for section in ["Executive Summary", "Method Comparison", "Project Comparison"]:
        content = report.split("## " + section + "\n", 1)[1].split("\n## ", 1)[0]
        assert content.count("### Scored out of") == 2
        for doc in [first, second]:
            assert f"{doc['overall_score']['total_points']:.1f}/84" in content
        pooled = sum(d['overall_score']['total_points'] for d in [first, second]) / 2
        assert f"{pooled:.1f}/84" not in content
    content = report.split("## Category Performance\n", 1)[1]
    for name in CATEGORY_SCORES:
        scores = [mod.categories_by_name(doc)[name]['category_score'] for doc in [first, second]]
        assert f"#### {name}\n- Average score: {sum(scores) / 2:.1f}\n" not in content
    # The discrimination blocks must use the same split, rather than treating
    # differing instruments as repeated ratings or score discrimination.
    assert report.count("## Item discrimination and within-project orderings") == 2
    assert "Rated more than once" not in report
    assert report.count("Measured on 1 of the 2 evaluations above") == 2


def test_individual_table_splits_evaluators_and_maxima(out_dir):
    docs = [_identified(evaluation_type="individual"),
            _identified(evaluation_type="individual", score_shift=2,
                        model={"name": "judge-b", "temperature": 0})]
    docs.append(_identified(evaluation_type="individual",
                            overall_score={"total_points": 70, "max_points": 88, "percentage": 79.5}))
    _run_all(docs)
    table = (out_dir / "summary_table.md").read_text().split("## Top Performing")[0]
    assert table.count("| NEW_PROJECT |") == 3
    assert "/MIXED" not in table
    assert table.count("Scored out of 84") == 2
    assert "Scored out of 88" in table
    assert "| Evaluations |" in table


def test_input_order_does_not_choose_a_duplicate_or_change_outputs(out_dir):
    docs = [_identified(), _identified(score_shift=1),
            _identified(model={"name": "judge-b", "temperature": 0})]
    _run_all(docs)
    def content():
        return {p.name: "\n".join(line for line in p.read_text().splitlines()
                                  if not line.startswith("**Generated:**"))
                for p in out_dir.iterdir()}
    first = content()
    _run_all(list(reversed(docs)))
    assert content() == first
    assert len(_all_csv_rows(out_dir)) == 3


def test_loader_preserves_paths_and_explicit_legacy_cohort_boundary(out_dir):
    import json
    for name in ["individual/custom/P_b_evaluation.json", "individual/custom/P_a_evaluation.json",
                 "concatenated/z_evaluation.json", "concatenated/a_evaluation.json",
                 "concatenated/dated_run/excluded_evaluation.json"]:
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_identified()))
    docs = mod.load_evaluation_results()
    assert len(docs) == 4
    assert {r['_evaluation_file'] for r in docs} == {
        "individual/custom/P_b_evaluation.json", "individual/custom/P_a_evaluation.json",
        "concatenated/z_evaluation.json", "concatenated/a_evaluation.json"}
    assert [r['_evaluation_file'] for r in docs] == sorted(r['_evaluation_file'] for r in docs)
    # Loading adds in-memory source identity; it does not rewrite the input.
    assert json.loads((out_dir / "concatenated/z_evaluation.json").read_text()) == _identified()


def test_table_labels_cannot_add_columns_or_rows(out_dir):
    _run_all([_identified(project="P|extra\nrow", method="m<test>")])
    table = (out_dir / "summary_table.md").read_text()
    assert "P&#124;extra<br>row" in table
    assert "m&lt;test&gt;" in table
    assert "| P|extra" not in table


@pytest.mark.corpus
def test_committed_csv_and_table_cover_the_loader_cohort():
    results = mod.load_evaluation_results()
    assert results
    rows = _all_csv_rows(mod.EVAL_DIR)
    assert len(rows) == len(results)
    assert {r["evaluation_file"] for r in rows} == {r["_evaluation_file"] for r in results}
    table = (mod.EVAL_DIR / "summary_table.md").read_text().split("## Top Performing")[0]
    for result in results:
        if result["evaluation_type"] == "concatenated":
            assert table.count(result["_evaluation_file"]) == 1
    # Raw historic scores remain exactly the loaded evaluation's values.
    by_file = {r["evaluation_file"]: r for r in rows}
    for result in results:
        row = by_file[result["_evaluation_file"]]
        assert float(row["total_score"]) == result["overall_score"]["total_points"]
        assert float(row["max_score"]) == result["overall_score"]["max_points"]
        assert row["evaluator"] == result["model"]["name"]
