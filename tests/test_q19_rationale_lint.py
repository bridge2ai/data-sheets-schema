"""The Q19 rationale lint (#2911), calibrated against the recorded inspections.

Two inspections read every recorded 1.0 rubric20 Q19 rationale for
representation-based deductions: the 09-11 errata (#1337) flagged 15 of 24,
the CBORG review (#1349) 9 of 24. Those 48 labels are the calibration set,
parsed from the inspections' own Markdown and checked against their JSON
companions, so a parser that misread a row cannot pass as agreement.

What the calibration shows, and what these tests hold the lint to:

- every one of the 24 flagged ratings is flagged;
- none of the 18 Q19=5 ratings is, although every one of them names
  `was_derived_from`, a graph or PROV (so vocabulary alone would flag them);
  none of them contains a sentence the lint reads as withholding;
- the six ratings below 5 that the inspections left unflagged are flagged
  too. That disagreement is pinned by name, not hidden: the module
  docstring explains why reproducing it would mean fitting the phrasing.
"""
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

import pytest
from click.testing import CliRunner

from data_sheets_schema.q19_rationale_lint import (
    FULL_SCORE, NO_STATED_REASON, NOT_SCORED, REPRESENTATION, REPRESENTATION_AND_SUBSTANTIVE,
    REPRESENTATION_ONLY, STATED, SUBSTANTIVE, SUBSTANTIVE_ONLY, UNSTATED, inspection_statuses,
    lint_file, lint_q19, lint_report, q19_item, sha256_of, withholding_sentences,
)

ROOT = Path(__file__).resolve().parents[1]
ERRATA = ROOT / "notes/reference_rescore_2026-09-11/semantic_errata.md"
REVIEW = ROOT / "notes/reference_rescore_2026-09-12_cborg_runtime/semantic_review.md"
INSPECTIONS = {"09-11": ERRATA, "cborg": REVIEW}
EVALUATION_DIRS = [ROOT / "data/evaluation_llm/rubric20_semantic/reference_2026-09-11",
                   ROOT / "data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime"]

#: Below 5, left unflagged by the inspection that read them, flagged here.
DISAGREEMENTS = {
    ("09-11", "CM4AI_v8_rep1_r20_rating1"): REPRESENTATION_ONLY,
    ("09-11", "CM4AI_v8_rep2_r20_rating1"): REPRESENTATION_AND_SUBSTANTIVE,
    ("cborg", "CHORUS_v7_rep2_r20_rating1"): REPRESENTATION_AND_SUBSTANTIVE,
    ("cborg", "CHORUS_v7_rep3_r20_rating1"): REPRESENTATION_AND_SUBSTANTIVE,
    ("cborg", "CHORUS_v8_rep3_r20_rating1"): REPRESENTATION_AND_SUBSTANTIVE,
    ("cborg", "CM4AI_v7_rep1_r20_rating1"): REPRESENTATION_AND_SUBSTANTIVE,
}


@pytest.fixture(scope="module")
def statuses():
    return {(name, job): status for name, doc in INSPECTIONS.items()
            for job, status in inspection_statuses(doc).items()}


@pytest.fixture(scope="module")
def linted(statuses):
    return {key: lint_file(status.path) for key, status in statuses.items()}


# -- the calibration set ------------------------------------------------------

@pytest.mark.parametrize("name, companion, flagged", [
    ("09-11", ERRATA.with_suffix(".json"), 15),
    ("cborg", REVIEW.with_suffix(".json"), 9),
])
def test_each_inspection_parses_to_its_structured_companion(name, companion, flagged):
    parsed = inspection_statuses(INSPECTIONS[name])
    recorded = json.loads(companion.read_text(encoding="utf-8"))
    assert recorded["ratings_requiring_adjudication"] == flagged
    assert {job: (s.flagged, s.path) for job, s in parsed.items()} == {
        case["job_id"]: (case["status"] == "requires_adjudication", (ROOT / case["output"]).resolve())
        for case in recorded["cases"]}
    assert len(parsed) == 24 and sum(s.flagged for s in parsed.values()) == flagged


def test_the_bytes_linted_are_the_bytes_the_inspections_read(statuses):
    """The CBORG review hashes every evaluation it read, the errata every
    one it flagged; a rewritten file would make agreement meaningless."""
    hashed = {key: s for key, s in statuses.items() if s.sha256}
    assert len(hashed) == 15 + 24
    assert {key for key, s in hashed.items() if sha256_of(s.path) != s.sha256} == set()


def test_every_rating_an_inspection_flagged_is_flagged(statuses, linted):
    missed = {key: linted[key].verdict for key, s in statuses.items()
              if s.flagged and not linted[key].flagged}
    assert missed == {}
    assert sum(s.flagged for s in statuses.values()) == 24


def test_no_full_score_is_flagged_though_every_one_names_the_vocabulary(statuses, linted):
    fives = {key for key, s in statuses.items() if s.q19_score == 5}
    assert len(fives) == 18
    for key in sorted(fives):
        result = linted[key]
        assert (result.verdict, result.flagged, result.reasons) == (FULL_SCORE, False, ()), key
        # What the score gate holds back: vocabulary alone would report each.
        assert any(m.kind == REPRESENTATION for m in result.mentions), key
        # And the withholding scope is not what saves them: no sentence in a
        # rationale that withholds nothing reads as withholding.
        item = q19_item(json.loads(statuses[key].path.read_text(encoding="utf-8")))
        assert withholding_sentences(item) == [], key


def test_the_disagreements_are_the_six_the_inspections_left_unflagged(statuses, linted):
    disagree = {key: linted[key].verdict for key, s in statuses.items()
                if s.flagged != linted[key].flagged}
    assert disagree == DISAGREEMENTS
    for key in DISAGREEMENTS:
        assert statuses[key].q19_score < 5 and not statuses[key].flagged


def test_the_grades_of_the_flagged_ratings(statuses, linted):
    """Documented in the module docstring; this keeps the docstring honest."""
    grades = Counter((s.flagged, linted[key].verdict) for key, s in statuses.items()
                     if s.q19_score < 5)
    assert grades == Counter({(True, REPRESENTATION_ONLY): 9,
                              (True, REPRESENTATION_AND_SUBSTANTIVE): 15,
                              (False, REPRESENTATION_ONLY): 1,
                              (False, REPRESENTATION_AND_SUBSTANTIVE): 5})


# -- the rules, on rationales written to isolate one each ---------------------

def item(score=4, label=None, note=None, analysis=None, max_score=5, **extra):
    out = {"id": 19, "score": score, "max_score": max_score, **extra}
    for key, value in (("score_label", label), ("quality_note", note),
                       ("semantic_analysis", analysis)):
        if value is not None:
            out[key] = value
    return out


def test_an_empty_slot_given_as_the_reason_is_flagged():
    result = lint_q19(item(note="Held at 4 because was_derived_from is empty."))
    assert (result.verdict, result.basis) == (REPRESENTATION_ONLY, STATED)
    assert result.concerns(REPRESENTATION) == ["empty_slot"]


def test_a_substantive_reason_is_reported_and_never_a_clean_pass():
    result = lint_q19(item(score=3, note="Held at 3 because there is no version history, "
                                         "no errata and no missing-data documentation."))
    assert (result.verdict, result.flagged) == (SUBSTANTIVE_ONLY, False)
    assert result.concerns(SUBSTANTIVE) == ["missing_data", "version_history"]


def test_both_kinds_are_flagged_with_the_substantive_one_listed():
    result = lint_q19(item(note="Held at 4 because the lineage is not machine-traversable "
                                "and there are no errata."))
    assert result.verdict == REPRESENTATION_AND_SUBSTANTIVE and result.flagged
    assert (result.concerns(REPRESENTATION), result.concerns(SUBSTANTIVE)) == (
        ["machine_form"], ["version_history"])


def test_only_the_sentences_that_withhold_are_read():
    """A slot named where the rationale is not explaining the score is not a
    reason, and data 'withheld' for privacy is not a withheld score."""
    result = lint_q19(item(
        note="Raw audio is withheld for privacy. Held at 4 because no errata are recorded.",
        analysis="was_derived_from is empty, and the lineage is not machine-readable."))
    assert result.basis == STATED
    assert (result.verdict, result.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])
    assert {m.concern for m in result.mentions} >= {"empty_slot", "machine_form"}


@pytest.mark.parametrize("sentence", [
    "Held at 3 because version history is absent, although was_derived_from is empty.",
    "Held at 3 because version history is absent; the rubric accepts text in place of a PROV-O graph.",
    "An empty was_derived_from is not a reason to withhold 5 here; held at 3 because version history is absent.",
])
def test_a_clause_that_accepts_or_disclaims_names_no_reason(sentence):
    result = lint_q19(item(score=3, note=sentence))
    assert (result.verdict, result.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])


def test_a_bare_verdict_takes_its_reason_from_the_next_sentence():
    result = lint_q19(item(note="Short of 5. parent_datasets is empty, so the derivation is "
                                "free text rather than a typed parent linkage."))
    assert result.basis == STATED
    assert result.concerns(REPRESENTATION) == ["empty_slot", "graph_form"]


def test_a_rationale_that_never_says_why_is_read_whole():
    result = lint_q19(item(note="Lineage is documented in prose.",
                           analysis="was_derived_from is empty."))
    assert (result.basis, result.verdict) == (UNSTATED, REPRESENTATION_ONLY)


def test_a_label_gives_its_reason_after_the_contrast_not_its_credit():
    result = lint_q19(item(label="Well beyond version history, short of an explicit graph",
                           note="Held at 4 because missing-data documentation is absent."))
    assert result.concerns(REPRESENTATION) == ["graph_form"]
    assert result.concerns(SUBSTANTIVE) == ["missing_data"]


def test_a_label_without_contrast_is_credit():
    result = lint_q19(item(label="Full provenance graph with derivation paths",
                           note="Held at 4 because no errata are recorded."))
    assert (result.verdict, result.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])


def test_a_score_below_maximum_with_no_reason_is_reported_as_such():
    result = lint_q19(item(note="Good provenance overall."))
    assert (result.verdict, result.flagged) == (NO_STATED_REASON, False)


@pytest.mark.parametrize("score, max_score, verdict", [
    (None, 5, NOT_SCORED), (5, 5, FULL_SCORE), (True, 5, NOT_SCORED),
    # A score with nothing to compare it with is not a full score.
    (4, None, NOT_SCORED), (4, "5", NOT_SCORED),
])
def test_only_a_numeric_score_below_maximum_is_linted(score, max_score, verdict):
    result = lint_q19(item(score=score, max_score=max_score,
                           note="Held at 4 because was_derived_from is empty."))
    assert (result.verdict, result.reasons) == (verdict, ())


@pytest.mark.parametrize("sentence", [
    "One point withheld because was_derived_from is empty.",
    "The fifth mark is withheld because the lineage is not expressed as a graph.",
    "The top band is withheld because the lineage is scattered across fields.",
])
def test_a_passive_withheld_after_what_a_score_withholds_is_a_cue(sentence):
    result = lint_q19(item(note="Lineage is complete in text. " + sentence))
    assert (result.basis, result.verdict) == (STATED, REPRESENTATION_ONLY)
    assert {r.sentence for r in result.reasons} == {sentence}


def test_mentions_are_the_vocabulary_alone():
    """Reported at any score, with no scope and no acceptance clause: the
    count the score gate and the withholding scope are measured against."""
    result = lint_q19(item(score=5, note="The rubric accepts text in place of a PROV-O graph."))
    assert result.reasons == ()
    assert [(m.concern, m.match) for m in result.mentions] == [("graph_form", "PROV-O")]


def test_a_version_2_item_is_read_from_the_fields_it_has():
    """2.0 items carry unit_scores and no per-item semantic_analysis."""
    evaluation = {"rubric": "rubric20-semantic", "version": "2.0", "categories": [
        {"questions": [{"id": 18, "score": 0}]},
        {"questions": [item(score=3, note="Held at 3 because the lineage is not expressed as a graph.",
                            unit_scores=[{"path": "#", "score": 3, "evidence": "x"}])]}]}
    assert lint_q19(q19_item(evaluation)).verdict == REPRESENTATION_ONLY


def test_q19_is_found_by_id_exactly_once():
    with pytest.raises(ValueError, match="found 0"):
        q19_item({"categories": [{"questions": [{"id": 18}]}]})
    with pytest.raises(ValueError, match="found 2"):
        q19_item({"categories": [{"questions": [{"id": 19}]}, {"questions": [{"id": 19}]}]})


def test_only_rubric20_semantic_evaluations_are_linted(tmp_path):
    path = tmp_path / "x_evaluation.json"
    path.write_text(json.dumps({"rubric": "rubric20", "categories": [{"questions": [item()]}]}))
    with pytest.raises(ValueError, match="not a rubric20-semantic evaluation"):
        lint_file(path)


# -- reading an inspection strictly -------------------------------------------

def _section(job, status, link, sha="0" * 64):
    return (f"## {job}\n\nRecorded Q19: 4/5. Status: `{status}`.\n\n"
            f"Original output: [evaluation]({link}); SHA256 `{sha}`\n\n")


@pytest.mark.parametrize("text, message", [
    ("# nothing here\n", "no inspection records"),
    (_section("A", "maybe", "a.json"), "unknown inspection status"),
    (_section("A", "requires_adjudication", "a.json") * 2, "two sections"),
    ("## A\n\nRecorded Q19: 4/5.\n", "no Q19 status"),
    ("| A | 4 | 70 | Requires adjudication | [x](a.json#L1) |\n" * 2, "listed twice"),
])
def test_an_inspection_that_cannot_be_read_whole_is_refused(tmp_path, text, message):
    doc = tmp_path / "review.md"
    doc.write_text(text)
    with pytest.raises(ValueError, match=message):
        inspection_statuses(doc)


# -- the command --------------------------------------------------------------

def _hashes():
    return {p: hashlib.sha256(p.read_bytes()).hexdigest()
            for d in EVALUATION_DIRS for p in sorted(d.rglob("*")) if p.is_file()} | {
        p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ERRATA, REVIEW)}


def test_the_command_reports_agreement_and_changes_no_evaluation_file():
    from data_sheets_schema.cli import cli
    before = _hashes()
    args = ["evaluate", "q19-lint", "--show", "--inspection", str(ERRATA), "--inspection", str(REVIEW)]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert "30 flagged of 30 Q19 score(s) below maximum; 48 rating(s)" in result.output
    assert "inspection agreement: 42/48 (flagged by both 24, by neither 18)" in result.output
    assert "flagged by the inspection, not the lint" not in result.output
    assert "reference_rescore_2026-09-11/CM4AI_v8_rep1_r20_rating1" in result.output
    strict = CliRunner().invoke(cli, args + ["--strict"])
    assert strict.exit_code == 1
    assert _hashes() == before


def test_strict_passes_a_directory_with_nothing_flagged(tmp_path):
    from data_sheets_schema.cli import cli
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic",
        "categories": [{"questions": [item(score=3, note="Held at 3 because no errata exist.")]}]}))
    result = CliRunner().invoke(cli, ["evaluate", "q19-lint", "--strict", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "substantive_only" in result.output and "0 flagged of 1" in result.output


def test_the_report_refuses_an_inspection_whose_evaluation_is_gone(tmp_path):
    doc = tmp_path / "semantic_review.md"
    doc.write_text(_section("A", "requires_adjudication", "gone_evaluation.json"))
    with pytest.raises(ValueError, match="gone_evaluation.json is missing"):
        lint_report(inspections=[doc])
    with pytest.raises(ValueError, match="nothing to lint"):
        lint_report()


def test_the_command_refuses_an_inspection_of_other_bytes(tmp_path):
    from data_sheets_schema.cli import cli
    evaluation = tmp_path / "A_evaluation.json"
    shutil.copy(EVALUATION_DIRS[1] / "CHORUS_v7_rep2_r20_rating1_evaluation.json", evaluation)
    doc = tmp_path / "semantic_review.md"
    doc.write_text(_section("A", "not_flagged_by_this_inspection", evaluation.name, sha="f" * 64))
    result = CliRunner().invoke(cli, ["evaluate", "q19-lint", "--inspection", str(doc)])
    assert result.exit_code == 1
    assert "not the bytes the inspection read" in result.output
