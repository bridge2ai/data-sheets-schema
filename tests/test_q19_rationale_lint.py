"""The Q19 rationale lint (#2911), calibrated against the recorded inspections.

Two inspections read the Q19 rationales of the two recorded 1.0 reference
rescores, 24 each, for representation-based deductions: the 09-11 errata
(#1337) flagged 15 of 24, the CBORG review (#1349) 9 of 24. The other 85
committed rubric20 semantic outputs are labelled by no inspection. Those 48
labels are the calibration set, parsed from the inspections' own Markdown
and checked against their JSON companions, so a parser that misread a row
cannot pass as agreement.

What the calibration shows, and what these tests hold the lint to:

- every one of the 24 flagged ratings is flagged;
- none of the 18 Q19=5 ratings is, although every one of them names
  representation vocabulary (17 `was_derived_from`, a graph or PROV; CBORG
  AI_READI v8 rep2 `parent_datasets`, typed and machine-readable form), so
  vocabulary alone would flag them; none of them contains a sentence the
  lint reads as withholding;
- the six ratings below 5 that the inspections left unflagged are flagged
  too. That disagreement is pinned by name, not hidden: the module
  docstring explains why reproducing it would mean fitting the phrasing.
"""
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest
from click.testing import CliRunner

from data_sheets_schema.q19_rationale_lint import (
    FULL_SCORE, REASON_NOT_DETERMINED, NOT_SCORED, REPRESENTATION, REPRESENTATION_AND_SUBSTANTIVE,
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


def test_the_bytes_linted_are_the_bytes_the_inspections_read(statuses, tmp_path):
    """Both JSON companions hash every evaluation their inspection read; the
    errata's Markdown hashes only the 15 it flagged, so the hash a status
    carries is the companion's. A rewritten file would make agreement
    meaningless."""
    assert all(s.sha256 for s in statuses.values()) and len(statuses) == 48
    assert {key for key, s in statuses.items() if sha256_of(s.path) != s.sha256} == set()
    # Read without its companion, the errata could tie only 15 of 24 to bytes.
    shutil.copy(ERRATA, tmp_path / ERRATA.name)
    alone = inspection_statuses(tmp_path / ERRATA.name)
    assert sum(1 for s in alone.values() if s.sha256) == 15
    assert {job for job, s in alone.items() if s.sha256} == {
        job for job, s in alone.items() if s.flagged}


def test_every_rating_an_inspection_flagged_is_flagged(statuses, linted):
    missed = {key: linted[key].verdict for key, s in statuses.items()
              if s.flagged and not linted[key].flagged}
    assert missed == {}
    assert sum(s.flagged for s in statuses.values()) == 24


#: The words the docstrings say 17 of the 18 Q19=5 rationales use.
_NAMED = re.compile(r"was_derived_from|wasDerivedFrom|\bgraphs?\b|\bPROV\b", re.I)


def test_no_full_score_is_flagged_though_every_one_names_the_vocabulary(statuses, linted):
    fives = {key for key, s in statuses.items() if s.q19_score == 5}
    assert len(fives) == 18
    rationale = {key: " ".join(str(q19_item(json.loads(statuses[key].path.read_text(
        encoding="utf-8"))).get(field) or "") for field in
        ("score_label", "quality_note", "semantic_analysis")) for key in fives}
    assert {key for key in fives if not _NAMED.search(rationale[key])} == {
        ("cborg", "AI_READI_v8_rep2_r20_rating1")}
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


def test_concern_profiles_do_not_separate_the_labels(statuses, linted):
    """The module docstring's worked examples, kept honest: identical
    profiles carry both labels, and the reason one unflagged rating gives
    beyond a flagged one is given by as many flagged ratings as unflagged."""
    def profile(key):
        return (tuple(linted[key].concerns(REPRESENTATION)), tuple(linted[key].concerns(SUBSTANTIVE)))
    below = {key: s for key, s in statuses.items() if s.q19_score < 5}
    bare = {key: s.flagged for key, s in below.items()
            if profile(key) == (("empty_slot", "graph_form"), ())}
    assert bare == {("09-11", "CM4AI_v8_rep1_r20_rating1"): False,
                    ("09-11", "AI_READI_v7_rep3_r20_rating1"): True,
                    ("09-11", "CM4AI_v7_rep1_r20_rating1"): True,
                    ("09-11", "CM4AI_v8_rep3_r20_rating1"): True,
                    ("cborg", "CM4AI_v8_rep1_r20_rating1"): True}
    flagged, unflagged = ("09-11", "CHORUS_v8_rep3_r20_rating1"), ("cborg", "CHORUS_v7_rep2_r20_rating1")
    assert (statuses[flagged].flagged, statuses[unflagged].flagged) == (True, False)
    assert profile(flagged)[0] == profile(unflagged)[0] == ("empty_slot",)
    assert set(profile(unflagged)[1]) - set(profile(flagged)[1]) == {"missing_data"}
    missing = Counter(s.flagged for key, s in below.items() if "missing_data" in profile(key)[1])
    assert missing == Counter({True: 4, False: 4})


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
    # A concession needs no comma to be judged apart from the reason (#3011).
    "Held at 3 because version history is absent though was_derived_from is empty.",
    "Held at 3 because version history is absent in spite of an empty was_derived_from.",
])
def test_a_clause_that_accepts_or_disclaims_names_no_reason(sentence):
    result = lint_q19(item(score=3, note=sentence))
    assert (result.verdict, result.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])


def test_a_bare_verdict_takes_its_reason_from_the_next_sentence():
    result = lint_q19(item(note="Short of 5. parent_datasets is empty, so the derivation is "
                                "free text rather than a typed parent linkage."))
    assert result.basis == STATED
    assert result.concerns(REPRESENTATION) == ["empty_slot", "graph_form"]


def test_a_rationale_that_never_says_why_is_read_for_every_gap_it_names():
    result = lint_q19(item(note="Lineage is documented in prose.",
                           analysis="was_derived_from is empty."))
    assert (result.basis, result.verdict) == (UNSTATED, REPRESENTATION_ONLY)


@pytest.mark.parametrize("note", [
    # #3068: credit sentences of committed ratings, read as reasons before.
    "RO-Crate packages include provenance graphs linking datasets, software, and processing steps.",
    "EVI Evidence Graph Ontology is appropriate for representing computational workflows.",
    "The version chain is DOI-typed, and per-archive MD5 checksums give real integrity evidence.",
    "Lineage is fully recoverable from prose, which exceeds bare version history.",
    # #3069: says was_derived_from is populated; "missing data" names content.
    "was_derived_from is explicit rather than implied, and missing data is documented with "
    "reasons at instance level.",
])
def test_where_nothing_says_why_a_sentence_naming_no_gap_is_credit(note):
    result = lint_q19(item(label="Updates tracking and provenance, missing formal version_access",
                           note=note))
    assert (result.basis, result.verdict, result.flagged) == (UNSTATED, SUBSTANTIVE_ONLY, False)
    assert [(r.concern, r.field) for r in result.reasons] == [("version_history", "score_label")]


def test_where_nothing_says_why_the_credit_before_a_contrast_is_not_read():
    """The gap after "but" is read; the checksums and graph credited before it
    are not. A contrast naming nothing of its own keeps its subject."""
    mixed = lint_q19(item(note="Integrity is well supported (checksums on every archive) and a "
                               "PROV graph ships in the crates, but the record gives no "
                               "structured derivation links."))
    assert (mixed.basis, mixed.verdict, mixed.concerns(REPRESENTATION)) == (
        UNSTATED, REPRESENTATION_ONLY, ["empty_slot"])
    assert [r.sentence for r in mixed.reasons] == ["but the record gives no structured derivation links."]
    subject = lint_q19(item(note="Version control is well structured; changelog mentioned but not "
                                 "detailed in this file."))
    assert (subject.verdict, subject.concerns(SUBSTANTIVE)) == (SUBSTANTIVE_ONLY, ["version_history"])
    assert [r.clause for r in subject.reasons] == ["changelog mentioned"]


def test_a_label_gives_its_reason_after_the_contrast_not_its_credit():
    result = lint_q19(item(label="Well beyond version history, short of an explicit graph",
                           note="Held at 4 because missing-data documentation is absent."))
    assert result.concerns(REPRESENTATION) == ["graph_form"]
    assert result.concerns(SUBSTANTIVE) == ["missing_data"]


def test_a_label_without_contrast_is_credit():
    result = lint_q19(item(label="Full provenance graph with derivation paths",
                           note="Held at 4 because no errata are recorded."))
    assert (result.verdict, result.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])


_NEUTRAL = "Lineage is documented in prose across the collection and preprocessing sections."


@pytest.mark.parametrize("label, concern", [
    ("Held at 4 because was_derived_from is empty", "empty_slot"),
    ("Held at 4 because the lineage is scattered across sections", "scattered"),
    ("Complete in prose; PROV graph absent", "graph_form"),
    ("Prose lineage; was_derived_from empty", "empty_slot"),
    ("Very Good - provenance graph documented as packaged, derivation fields unpopulated", "empty_slot"),
])
def test_a_label_that_gives_its_reason_without_a_contrast_is_read(label, concern):
    """A label can be the only place a reason is stated (#3012)."""
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert (result.verdict, result.concerns(REPRESENTATION)) == (REPRESENTATION_ONLY, [concern])
    assert all(r.field == "score_label" for r in result.reasons)


def test_a_label_that_says_why_leaves_the_body_unread_as_reasons():
    """A label with a withholding cue and a reason states why, so the body's
    credit is not read as co-reasons; a bare label cue leaves the body to."""
    said = lint_q19(item(label="Held at 4 because was_derived_from is empty",
                         note="Version history and errata are documented."))
    assert (said.basis, said.verdict, said.concerns(SUBSTANTIVE)) == (STATED, REPRESENTATION_ONLY, [])
    bare = lint_q19(item(label="Short of 5", note="was_derived_from is empty."))
    assert (bare.basis, bare.verdict) == (UNSTATED, REPRESENTATION_ONLY)
    # "short of an" is a withholding cue as "short of a" is (#3068).
    for label in ("Well beyond version history, with a declared provenance graph, short of an "
                  "explicit graph in the record",
                  "Well beyond version history, with a declared provenance graph, short of a "
                  "full provenance graph"):
        result = lint_q19(item(label=label, note="Version history and errata are documented, "
                                                 "with checksums for every file."))
        assert (result.basis, result.verdict, result.concerns(SUBSTANTIVE)) == (
            STATED, REPRESENTATION_ONLY, []), label


def test_a_label_contrast_names_a_gap_and_leaves_the_body_to_say_why():
    """#3068: a contrast or absence clause names a gap without saying it held
    the score, so it does not state the basis; the body's gaps are read
    beside it, and its credit is not."""
    contrast = lint_q19(item(label="Full provenance graph, but no version history",
                             note="was_derived_from links every release to its parent dataset "
                                  "as a PROV graph. There are no errata."))
    assert (contrast.basis, contrast.verdict, contrast.concerns(REPRESENTATION)) == (
        UNSTATED, SUBSTANTIVE_ONLY, [])
    assert {r.sentence for r in contrast.reasons} == {"but no version history",
                                                      "There are no errata."}
    body_gap = lint_q19(item(label="Rich prose lineage; no errata",
                             note="Version history is documented. parent_datasets is empty."))
    assert (body_gap.basis, body_gap.verdict) == (UNSTATED, REPRESENTATION_AND_SUBSTANTIVE)
    assert (body_gap.concerns(REPRESENTATION), body_gap.concerns(SUBSTANTIVE)) == (
        ["empty_slot"], ["version_history"])


@pytest.mark.parametrize("bare, punctuated, rep, sub", [
    # #3068: the reason follows the cue whether or not a comma precedes it.
    ("Typed derivation links in was_derived_from but no version history",
     "Typed derivation links in was_derived_from, but no version history", [], ["version_history"]),
    ("Machine-readable PROV graph without errata", "Machine-readable PROV graph, without errata",
     [], ["version_history"]),
    ("Good versioning but no PROV graph", "Good versioning, but no PROV graph", ["graph_form"], []),
    ("Well beyond version history short of an explicit graph",
     "Well beyond version history, short of an explicit graph", ["graph_form"], []),
    ("Complete versioning rather than a PROV graph", "Complete versioning, rather than a PROV graph",
     ["graph_form"], []),
    # A spaced hyphen, an en dash, a parenthesis or a sentence end ends a
    # clause as a comma does: the reason after it is read, the credit before
    # it is not.
    ("Very Good - no formal provenance graph", "Very Good, no formal provenance graph",
     ["graph_form"], []),
    ("Very Good – no formal provenance graph", "Very Good, no formal provenance graph",
     ["graph_form"], []),
    ("Strong textual lineage (no PROV graph)", "Strong textual lineage, no PROV graph",
     ["graph_form"], []),
    ("Strong textual lineage. No PROV graph.", "Strong textual lineage, no PROV graph",
     ["graph_form"], []),
    ("Very Good - no errata recorded", "Very Good, no errata recorded", [], ["version_history"]),
    ("Full version history and errata - but no PROV graph",
     "Full version history and errata, but no PROV graph", ["graph_form"], []),
    ("Declared PROV graph with typed links – short of version history",
     "Declared PROV graph with typed links, short of version history", [], ["version_history"]),
])
def test_a_label_reason_does_not_depend_on_the_punctuation_before_its_cue(bare, punctuated, rep, sub):
    for body in (_NEUTRAL, "Held at 4 because no checksums are recorded."):
        results = [lint_q19(item(label=label, note=body)) for label in (bare, punctuated)]
        extra = [] if body == _NEUTRAL else ["integrity"]
        assert [(r.concerns(REPRESENTATION), r.concerns(SUBSTANTIVE)) for r in results] == [
            (rep, sorted(sub + extra))] * 2, (bare, body)


@pytest.mark.parametrize("label", [
    "graph claimed but not evidenced",
    "Rich narrative provenance; full provenance graph asserted rather than exhibited",
])
def test_a_label_contrast_naming_nothing_is_about_the_words_before_it(label):
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert (result.verdict, result.concerns(REPRESENTATION)) == (REPRESENTATION_ONLY, ["graph_form"])


def test_a_label_clause_saying_something_is_absent_is_read_and_its_credit_is_not():
    result = lint_q19(item(label="Derivation fields unpopulated, strong version history",
                           note="Held at 4 because no checksums are recorded."))
    assert result.verdict == REPRESENTATION_AND_SUBSTANTIVE
    assert (result.concerns(REPRESENTATION), result.concerns(SUBSTANTIVE)) == (
        ["empty_slot"], ["integrity"])
    # "missing-data documentation" names content, not an absence.
    credit = lint_q19(item(label="Missing-data documentation and version history",
                           note="Held at 4 because no checksums are recorded."))
    assert (credit.verdict, credit.concerns(SUBSTANTIVE)) == (SUBSTANTIVE_ONLY, ["integrity"])


@pytest.mark.parametrize("sentence, concern", [
    ("Held at 4: text is permitted but no PROV graph is provided.", "graph_form"),
    ("Held at 4 because was_derived_from is empty even though the lineage is complete in prose.",
     "empty_slot"),
    ("Held at 4 because was_derived_from is empty though the lineage is complete in prose.",
     "empty_slot"),
    ("Held at 4 because the lineage is not expressed as a PROV-O graph although every step "
     "is described.", "graph_form"),
    ("Held at 4 because was_derived_from is empty despite a complete textual lineage.",
     "empty_slot"),
    ("Held at 4 because was_derived_from is empty in spite of a complete textual lineage.",
     "empty_slot"),
    # Every concession phrase ends a clause, "regardless of" and
    # "irrespective of" included (#3206).
    ("Held at 4 because was_derived_from is empty regardless of the prose lineage.",
     "empty_slot"),
    ("Held at 4 because was_derived_from is empty irrespective of the prose lineage.",
     "empty_slot"),
    # "however" ends a clause as "but" does (#3146).
    ("Held at 4: the rubric accepts text however no PROV graph is given.", "graph_form"),
    # An acceptance names its own object, so it does not take the clause
    # before it with it, as a disclaimer does (#3145).
    ("Held at 4 because no PROV graph is provided but prose is accepted.", "graph_form"),
])
def test_a_concession_sharing_a_clause_with_a_reason_removes_only_itself(sentence, concern):
    """#3011: the canonical #2911 rationale concedes text is complete and
    withholds for form in one clause."""
    result = lint_q19(item(note=sentence))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        STATED, REPRESENTATION_ONLY, [concern])


@pytest.mark.parametrize("phrase", ["regardless of", "irrespective of"])
def test_a_label_concession_without_a_comma_removes_only_itself(phrase):
    """#3206, in a score label: the concession is its own clause with or
    without a comma, so the reason before it is read either way."""
    for label in (f"Held at 4 because was_derived_from is empty {phrase} the prose lineage",
                  f"Held at 4 because was_derived_from is empty, {phrase} the prose lineage"):
        result = lint_q19(item(label=label))
        assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
            STATED, REPRESENTATION_ONLY, ["empty_slot"]), label


@pytest.mark.parametrize("connective", ["in place of", "instead of", "rather than"])
def test_in_place_of_names_a_form_and_accepts_nothing(connective):
    """#3205: "in place of", like "instead of" and "rather than", says what
    the lineage is given as. Only "accept", "permit" or "allow" accepts."""
    result = lint_q19(item(note=f"Held at 4 because the lineage is given as prose {connective} "
                                f"a PROV-O graph."))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        STATED, REPRESENTATION_ONLY, ["graph_form"])
    accepted = lint_q19(item(note="Held at 4 because no errata exist. The lineage is text, which "
                                  f"the rubric accepts {connective} a PROV-O graph."))
    assert (accepted.verdict, accepted.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])


def test_an_acceptance_joined_by_and_takes_its_clause_and_says_so():
    """#3205: clauses do not end at "and", so an acceptance joined to a
    reason by "and" alone takes the reason and the cue with it. The lint
    reports that the reason was not determined, and that a cue was not
    read; with a comma before "and" the reason is its own clause."""
    joined = lint_q19(item(note="Held at 4 because was_derived_from is empty and the rubric "
                                "accepts prose for lineage."))
    assert (joined.basis, joined.verdict, joined.cue_unread) == (
        UNSTATED, REASON_NOT_DETERMINED, True)
    comma = lint_q19(item(note="Held at 4 because was_derived_from is empty, and the rubric "
                               "accepts prose for lineage."))
    assert (comma.basis, comma.verdict, comma.cue_unread) == (STATED, REPRESENTATION_ONLY, False)
    # A disclaimed cue is not an unread one: nothing there says why.
    disclaimed = lint_q19(item(note="Nothing is deducted for the empty was_derived_from."))
    assert (disclaimed.basis, disclaimed.cue_unread) == (UNSTATED, False)
    # Nor is a cue in a clause that is read but names no reason ("Short of
    # 5"): the lint read it, and it does not say why.
    bare = lint_q19(item(label="Short of 5", note="parent_datasets is empty."))
    assert (bare.basis, bare.cue_unread) == (UNSTATED, False)


def test_a_conceded_withholding_sentence_does_not_hand_its_reason_to_a_neighbour():
    """With the reason lost, the credit sentence beside it was read as a
    substantive reason and the rating reported as substantive only."""
    result = lint_q19(item(note="The record documents version history and errata. Held at 4 "
                                "because was_derived_from is empty even though the lineage is "
                                "complete in prose."))
    assert (result.verdict, result.concerns(SUBSTANTIVE)) == (REPRESENTATION_ONLY, [])


def test_a_4_rather_than_a_5_withholds_and_rather_than_from_being_a_5_disclaims():
    withheld = lint_q19(item(note="A 4 rather than a 5 because was_derived_from is empty."))
    assert (withheld.basis, withheld.verdict) == (STATED, REPRESENTATION_ONLY)
    # Read whole, as no sentence withholds; the second disclaims its gap.
    disclaimed = lint_q19(item(note="No errata are recorded. The empty was_derived_from keeps "
                                    "this from being unimprovable rather than from being a 5."))
    assert (disclaimed.basis, disclaimed.verdict, disclaimed.concerns(REPRESENTATION)) == (
        UNSTATED, SUBSTANTIVE_ONLY, [])


# -- review round 3: disclaimers, denied permissions, credit after a contrast

@pytest.mark.parametrize("disclaimer", [
    "Nothing is deducted for the empty was_derived_from.",
    "No point is withheld for the absence of a PROV-O graph.",
    "No single point was deducted for the empty was_derived_from.",
    "The absence of a PROV-O graph does not keep it from 5.",
    "An empty was_derived_from is not a ground for withholding 5.",
    "The rubric does not permit withholding 5 for the absence of a PROV-O graph.",
    "The empty was_derived_from was not deducted here because the derivation is complete in prose.",
    # A disclaimer naming nothing of its own is about the clause before it.
    "The empty was_derived_from is noted but not penalised.",
    "The empty was_derived_from is noted, but not penalised.",
])
def test_a_negated_cue_disclaims_a_deduction_and_names_no_reason(disclaimer):
    """#3145: a cue negated within three words is not a cue, and its clause
    names no reason. It neither states the basis nor hands its reason to
    the body, so the body's gap ("no errata") is read and the disclaimed
    form is not."""
    result = lint_q19(item(note=disclaimer + " There are no errata."))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        UNSTATED, SUBSTANTIVE_ONLY, []), disclaimer
    assert withholding_sentences(item(note=disclaimer)) == []


def test_a_disclaiming_sentence_does_not_hand_its_neighbours_credit():
    """#3145: a disclaimer read as a cue that named no reason made the lint
    read both neighbouring sentences whole, credit included."""
    beside_a_cue = lint_q19(item(score=3, note=(
        "Derivation is recorded in prose and a PROV graph ships in the RO-Crate. An empty "
        "was_derived_from is not a reason to withhold 5. Held at 3 because no errata or "
        "version history are recorded.")))
    assert (beside_a_cue.basis, beside_a_cue.verdict, beside_a_cue.concerns(REPRESENTATION)) == (
        STATED, SUBSTANTIVE_ONLY, [])
    # A version-2 rationale that follows #2911's proposed clarification.
    compliant = lint_q19(item(score=3, note=(
        "Version history and errata are recorded. Lineage is complete in text and a PROV graph "
        "ships in the RO-Crate. An empty was_derived_from is not a ground for withholding 5 "
        "under the Q19 clarification. Scored 3 because no missing-data documentation is given.")))
    assert (compliant.verdict, compliant.concerns(SUBSTANTIVE)) == (SUBSTANTIVE_ONLY, ["missing_data"])
    alone = lint_q19(item(note="Lineage is complete in text and a PROV graph ships in the RO-Crate. "
                               "An empty was_derived_from is not a ground for withholding 5."))
    assert (alone.basis, alone.verdict, alone.reasons) == (UNSTATED, REASON_NOT_DETERMINED, ())


@pytest.mark.parametrize("note, verdict, concerns", [
    # A negation more than three words before the cue is about something else.
    ("No errata are recorded and this keeps it from 5.", SUBSTANTIVE_ONLY, ["version_history"]),
    ("was_derived_from is not populated so a point is deducted.", REPRESENTATION_ONLY, ["empty_slot"]),
    # A cue that is itself a negation is not negated by it.
    ("It does not reach 5 because no PROV graph is given.", REPRESENTATION_ONLY, ["graph_form"]),
    ("It is not a 5 because the lineage is not expressed as a graph.", REPRESENTATION_ONLY,
     ["graph_form"]),
    # A disclaimer that names its own concern removes only itself.
    ("Held at 3 because no errata are recorded but nothing is deducted for the empty "
     "was_derived_from.", SUBSTANTIVE_ONLY, ["version_history"]),
    ("Held at 3 for missing version history, not because was_derived_from is empty.",
     SUBSTANTIVE_ONLY, ["version_history"]),
])
def test_a_cue_is_disclaimed_only_by_a_negation_within_three_words(note, verdict, concerns):
    result = lint_q19(item(score=3, note=note))
    assert (result.basis, result.verdict) == (STATED, verdict)
    assert result.concerns(REPRESENTATION) + result.concerns(SUBSTANTIVE) == concerns


def test_a_disclaimer_after_a_cue_removes_its_clause_not_the_cue():
    """The cue still says why, so the basis stays stated and the other
    sentence's gap is not read as a candidate reason."""
    result = lint_q19(item(note="The lineage is not machine-readable. It falls short of 5 not "
                                "because of form but because no errata are recorded."))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        STATED, SUBSTANTIVE_ONLY, [])
    held = lint_q19(item(note="Held at 4 not because was_derived_from is empty but because no "
                              "errata are recorded."))
    assert (held.basis, held.verdict, held.concerns(SUBSTANTIVE)) == (
        STATED, SUBSTANTIVE_ONLY, ["version_history"])


def test_a_negation_within_three_words_always_disclaims():
    """The documented cost of the window: a terse genuine cue cannot be told
    from a disclaimer, so it gives no reason rather than a guessed one."""
    result = lint_q19(item(note="No PROV graph so held at 4."))
    assert (result.basis, result.verdict, result.flagged) == (UNSTATED, REASON_NOT_DETERMINED, False)


@pytest.mark.parametrize("note, concern", [
    ("Held at 4 because the empty was_derived_from does not allow a machine to traverse the "
     "lineage.", "empty_slot"),
    ("Held at 4 because prose lineage allows no machine traversal.", "machine_form"),
    ("Held at 4 because a PROV-O graph is not permitted to live outside the record.", "graph_form"),
    ("Held at 4 because the text form does not permit machine traversal.", "machine_form"),
    ("Held at 4 because the text form allows only a human-readable reconstruction of lineage.",
     "machine_form"),
    ("Held at 4 because the rubric does not accept prose in place of a PROV-O graph for the "
     "5-band.", "graph_form"),
])
def test_a_permission_denied_where_it_stands_states_a_limit(note, concern):
    """#3147: "does not allow", "allows no", "is not permitted" and the
    like accept nothing, so the reason they state is read."""
    result = lint_q19(item(note=note))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        STATED, REPRESENTATION_ONLY, [concern])


@pytest.mark.parametrize("word", ["accepted", "permitted", "allowed", "accepting", "permitting",
                                  "allowing", "acceptable", "allowable", "permissible"])
def test_every_listed_form_of_a_permission_accepts(word):
    """#3227: "allowed", "acceptable", "allowable" and "permissible" accept,
    as "accepted" and "permitted" already did, so the form they accept is
    not read as a reason."""
    result = lint_q19(item(score=3, note=f"Held at 3 because version history is absent; text is "
                                         f"{word} in place of a PROV-O graph."))
    assert (result.verdict, result.concerns(REPRESENTATION), result.concerns(SUBSTANTIVE)) == (
        SUBSTANTIVE_ONLY, [], ["version_history"])


@pytest.mark.parametrize("words", ["not permissible", "not allowed", "not acceptable",
                                   "permissible only"])
def test_a_new_permission_form_denied_where_it_stands_states_a_limit(words):
    """The denial side covers the new forms: "is not permissible" states a
    limit, and its reason is read."""
    result = lint_q19(item(note=f"Held at 4 because a PROV-O graph outside the record is {words} "
                                f"here."))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        STATED, REPRESENTATION_ONLY, ["graph_form"])


def test_a_denied_permission_that_disclaims_a_deduction_still_disclaims():
    """The disclaimer rule, not the permission rule, decides "does not
    permit withholding 5 for …": a plain negation guard would flag it."""
    result = lint_q19(item(score=3, note="Held at 3 because no errata are recorded; the rubric "
                                         "does not permit withholding 5 for the absence of a "
                                         "PROV-O graph."))
    assert (result.verdict, result.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])


@pytest.mark.parametrize("note, read", [
    ("No errata are recorded, but was_derived_from links every release to its parent dataset.",
     "No errata are recorded,"),
    ("There are no errata; however, a machine-readable PROV graph ships with typed "
     "was_derived_from links.", "There are no errata;"),
    ("Errata are absent, whereas the PROV-O graph is complete and machine-traversable.",
     "Errata are absent,"),
])
def test_where_nothing_says_why_credit_after_a_contrast_is_not_read(note, read):
    """#3146: a part after a contrast that names no gap is credit, as a part
    before one is."""
    result = lint_q19(item(label="Good", note=note))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        UNSTATED, SUBSTANTIVE_ONLY, [])
    assert [(r.concern, r.sentence) for r in result.reasons] == [("version_history", read)]


def test_a_part_naming_nothing_of_its_own_reads_its_subject_before_a_second_contrast():
    """"but not detailed" names nothing of its own; the gap after the next
    "but" is another part's, so the subject "changelog mentioned" is read."""
    result = lint_q19(item(label="Good", note="Version control is well structured; changelog "
                                              "mentioned but not detailed but was_derived_from is "
                                              "empty."))
    assert (result.basis, result.concerns(REPRESENTATION), result.concerns(SUBSTANTIVE)) == (
        UNSTATED, ["empty_slot"], ["version_history"])
    assert "Version control is well structured" not in {r.clause for r in result.reasons}


def test_where_nothing_says_why_a_gap_after_a_contrast_keeps_its_list():
    """A list continuing the gap after the contrast is the same part."""
    result = lint_q19(item(label="Good", note="Version history is complete, but no PROV graph is "
                                              "given, and the lineage is scattered across sections."))
    assert (result.verdict, result.concerns(REPRESENTATION), result.concerns(SUBSTANTIVE)) == (
        REPRESENTATION_ONLY, ["graph_form", "scattered"], [])


@pytest.mark.parametrize("bare, punctuated", [
    ("Machine-readable PROV graph lacking errata", "Machine-readable PROV graph, lacking errata"),
    ("Typed was_derived_from links and errata missing", "Typed was_derived_from links, errata missing"),
    ("Complete PROV-O graph with version history absent", "Complete PROV-O graph, version history absent"),
    ("Typed PROV graph lacks errata", "Typed PROV graph, lacks errata"),
    # "not" inside a clause, like an absence word, may follow credit.
    ("Typed PROV graph with errata not recorded", "Typed PROV graph, errata not recorded"),
])
def test_a_label_absence_clause_naming_both_kinds_is_not_read(bare, punctuated):
    """#3146: the words do not say which of the two is absent, and the
    answer would decide the flag, so the clause is not read; the comma makes
    the absent one a clause of its own, which is."""
    for body, extra in ((_NEUTRAL, []), ("Held at 4 because no checksums are recorded.", ["integrity"])):
        unread, read = (lint_q19(item(label=label, note=body)) for label in (bare, punctuated))
        assert (unread.flagged, unread.concerns(REPRESENTATION), unread.concerns(SUBSTANTIVE)) == (
            False, [], extra), (bare, body)
        assert (read.verdict, read.concerns(REPRESENTATION), read.concerns(SUBSTANTIVE)) == (
            SUBSTANTIVE_ONLY, [], sorted(extra + ["version_history"])), (punctuated, body)
        if body == _NEUTRAL:
            assert unread.verdict == REASON_NOT_DETERMINED


def test_a_label_absence_clause_naming_one_kind_or_opening_with_its_word_is_read():
    """A coordinated subject of one kind is read whole; so is a clause that
    opens with its absence word, whose object is everything after it."""
    result = lint_q19(item(label="Textual provenance with lineage and agents; version history and "
                                 "missingness absent", note=_NEUTRAL))
    assert (result.verdict, result.concerns(SUBSTANTIVE)) == (
        SUBSTANTIVE_ONLY, ["missing_data", "version_history"])
    opening = lint_q19(item(label="Rich prose lineage, lacking errata and a PROV graph", note=_NEUTRAL))
    assert (opening.verdict, opening.concerns(REPRESENTATION), opening.concerns(SUBSTANTIVE)) == (
        REPRESENTATION_AND_SUBSTANTIVE, ["graph_form"], ["version_history"])


#: #3248: a disclaimer, concession or acceptance keeps its scope across the
#: parentheses and comma lists that split what it is about.
_SCOPED = [
    # The Codex scenario: a parenthesis names the slots the disclaimer covers.
    "Held at 3 because no errata are recorded; nothing is deducted for the empty derivation "
    "slots (was_derived_from, parent_datasets).",
    # A comma list after "not because of".
    "Held at 3 because no errata are recorded, not because of the empty was_derived_from, "
    "parent_datasets or PROV graph.",
    # A disclaimer with no verb yet: the fragment that supplies it completes it.
    "Held at 3 not because was_derived_from, parent_datasets and the PROV graph are empty, "
    "but because no errata are recorded.",
    # A concession around a parenthesis, and the words after it closes.
    "Held at 3 because no errata are recorded, despite the dedicated fields "
    "(was_derived_from, parent_datasets) being empty.",
    # An aside of a disclaimer is about it, verb or not.
    "Held at 3 because no errata are recorded; nothing is deducted for the prose form "
    "(the derivation slots are empty).",
    # An acceptance whose object is listed.
    "Held at 3 because no errata are recorded; the rubric accepts prose lineage, typed "
    "links, PROV graph or none.",
]


@pytest.mark.parametrize("note", _SCOPED)
def test_a_disclaimer_keeps_its_scope_across_parentheses_and_lists(note):
    """#3248: splitting at a parenthesis or a comma left the slots named in
    a disclaimer's list as reasons of their own, so a rating that says in
    so many words that nothing is deducted for them was flagged."""
    result = lint_q19(item(score=3, note=note))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        STATED, SUBSTANTIVE_ONLY, []), note
    assert result.concerns(SUBSTANTIVE) == ["version_history"]


def test_a_disclaimer_keeps_its_scope_back_over_the_list_it_closes():
    """#3248: "…, but that is not a reason to withhold 5" disclaims the whole
    list before it, not only its last item."""
    result = lint_q19(item(note=(
        "The empty was_derived_from, parent_datasets and PROV graph are noted, but that is not "
        "a reason to withhold 5. No errata are recorded.")))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        UNSTATED, SUBSTANTIVE_ONLY, [])
    # A clause of its own before the list is read.
    kept = lint_q19(item(note=(
        "No errata are recorded, the empty was_derived_from, parent_datasets and PROV graph are "
        "noted, but that is not a reason to withhold 5.")))
    assert (kept.verdict, kept.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])
    assert kept.concerns(SUBSTANTIVE) == ["version_history"]


@pytest.mark.parametrize("note, concern", [
    # A fragment with a finite verb after a complete concession says its own.
    ("Although the lineage is complete in prose, was_derived_from is empty, which holds it at 4.",
     "empty_slot"),
    # A parenthesis after a clause that is read is read.
    ("Held at 4 because the derivation slots are empty (was_derived_from, parent_datasets).",
     "empty_slot"),
    # A semicolon ends the scope.
    ("Held at 4 because nothing is deducted for prose; was_derived_from empty.", "empty_slot"),
    # A conjunction opens a clause of its own.
    ("Held at 4: nothing is deducted for the prose form, but no PROV graph.", "graph_form"),
])
def test_a_disclaimer_scope_ends_where_a_clause_of_its_own_begins(note, concern):
    result = lint_q19(item(note=note))
    assert result.flagged and concern in result.concerns(REPRESENTATION), note


def test_a_verbless_fragment_after_an_unread_clause_is_not_read():
    """#3248, the cost: a fragment with no finite verb after a clause that
    is not read may be its list item or an item of an outer list. Where
    nothing sets it apart as the outer list's (below), it is not read, so
    the reason it may give is lost rather than a disclaimed slot flagged."""
    result = lint_q19(item(note=(
        "Held at 4 because no errata are recorded despite the changelog being public, "
        "and was_derived_from empty.")))
    assert (result.verdict, result.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])


def test_an_outer_list_item_after_a_concession_is_read_by_parallel_structure():
    """#3260: the committed 09-11 CHORUS v7 rep1 rating's last "no …" item
    after a concession is an item of the outer "no …" list, and is read; its
    verdict does not move (graph_form was read already)."""
    chorus = lint_file(EVALUATION_DIRS[0] / "CHORUS_v7_rep1_r20_rating1_evaluation.json")
    assert chorus.verdict == REPRESENTATION_AND_SUBSTANTIVE
    assert chorus.concerns(REPRESENTATION) == ["empty_slot", "graph_form"]
    assert any("parent_datasets linkage" in r.clause for r in chorus.reasons
               if r.concern == "empty_slot")
    result = lint_q19(item(note=(
        "Held at 4: no version_access, no errata channel despite the changelog being thorough, "
        "and no structured was_derived_from linkage.")))
    assert result.concerns(REPRESENTATION) == ["empty_slot"]


@pytest.mark.parametrize("note", [
    # The concession's own list opens with the same word: whose item is it?
    "Held at 4 because no errata are recorded, no changelog despite no PROV graph, "
    "and no was_derived_from.",
    # A disclaimer's list is never an outer list: a pure disclaimer, which
    # does not concede either ...
    "Held at 4 because no errata are recorded, no changelog, not because of the prose form, "
    "no was_derived_from.",
    # ... and one that concedes as it disclaims, where only the disclaimer
    # guard in `_outer_item` keeps the item out (#3465).
    "Held at 4 because no errata are recorded, no changelog, although nothing is deducted "
    "for the prose form, no was_derived_from.",
    # An acceptance whose item does not repeat the outer list's opening.
    "Held at 4 because no errata are recorded, no changelog, which the rubric accepts, "
    "and was_derived_from.",
    # A fragment that repeats the opening word but disclaims on its own:
    # it is not read for its own words, so parallel structure does not
    # make it read (the `read and` guard in `_in_scope`).
    "No errata, despite the changelog, no deduction for the empty was_derived_from.",
])
def test_an_outer_list_item_is_not_guessed_without_parallel_structure(note):
    """#3260: no flag on a disclaimed list, and no guess where the words do
    not say which list the fragment belongs to."""
    result = lint_q19(item(note=note))
    assert result.concerns(REPRESENTATION) == [], note


def test_an_outer_list_needs_its_opening_clause_read():
    """#3434 (b), #3260: a verbless fragment after a concession is read as
    an item of the outer list only where the clause that list opens with
    is read. Here that clause disclaims, so "and no PROV graph" may be the
    disclaimer's own item, and it is not read."""
    disclaimed = lint_q19(item(note=(
        "No point is withheld for errata, despite the changelog confirming releases, "
        "and no PROV graph.")))
    assert (disclaimed.verdict, disclaimed.reasons) == (REASON_NOT_DETERMINED, ())
    read = lint_q19(item(note=(
        "No errata, despite the changelog confirming releases, and no PROV graph.")))
    assert read.concerns(REPRESENTATION) == ["graph_form"]


#: #3575: fragments that share only an article, or that may be coordinated
#: with the acceptance's own objects, with origin/main's reading (checked
#: against a git-archive copy of it): (field, text). Every row reads
#: STATED substantive_only [version_history] on main; the round-5 branch
#: read the accepted objects as empty_slot and graph_form reasons.
_ACCEPTED_OBJECTS = [
    # Codex's example, as a label and as a note: every object opens with "the".
    ("label", "Held at 4: the errata are missing, although we accept the empty "
     "was_derived_from, the empty parent_datasets and the absent PROV graph."),
    ("note", "Held at 4: the errata are missing, although we accept the empty "
     "was_derived_from, the empty parent_datasets and the absent PROV graph."),
    # A shared article, the acceptance carrying none: only the absence-word
    # guard keeps it out.
    ("note", "Held at 4: the errata are missing, although prose lineage is accepted, "
     "the empty was_derived_from."),
    # A shared absence word the acceptance's own objects open with: only the
    # "carries it nowhere" guard keeps it out.
    ("note", "Held at 4: no errata, although we accept no was_derived_from, "
     "no parent_datasets and no PROV graph."),
]


@pytest.mark.parametrize("field, text", _ACCEPTED_OBJECTS)
def test_an_article_or_an_accepted_object_is_no_outer_list_evidence(field, text):
    """#3575, #3260: a fragment is an outer list's item only where it
    shares an absence word with the list and the acceptance carries that
    word nowhere. These read exactly as on main."""
    rating = item(label=text, note=_NEUTRAL) if field == "label" else item(note=text)
    result = lint_q19(rating)
    assert (result.basis, result.verdict, sorted({r.concern for r in result.reasons})) == (
        STATED, SUBSTANTIVE_ONLY, ["version_history"]), text


def test_an_absence_word_list_the_acceptance_does_not_share_is_still_recovered():
    """#3260 as narrowed by #3575: "no …" items either side of an acceptance
    that carries no "no" (main reads substantive_only here, dropping the
    last item)."""
    result = lint_q19(item(note=(
        "Held at 4: no errata, although prose lineage is accepted, no was_derived_from.")))
    assert result.concerns(REPRESENTATION) == ["empty_slot"]


def test_strict_passes_a_disclaimed_list(tmp_path):
    """#3248: the Codex scenario exits 0 under --strict."""
    from data_sheets_schema.cli import cli
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [item(
            score=3, note=_SCOPED[0])]}]}))
    result = CliRunner().invoke(cli, ["evaluate", "q19-lint", "--strict", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "substantive_only" in result.output and "0 flagged of 1" in result.output


#: #3264: a label reason is a range of the label, its clauses judged in the
#: whole label, so a gap named in a concession's aside or list is conceded.
_CONCEDED_LABELS = [
    # The Codex scenario.
    "Good despite empty provenance fields (no was_derived_from)",
    "Good despite empty provenance fields, no was_derived_from",
    "Good despite empty provenance fields no was_derived_from",
    "Good although the fields are empty (no was_derived_from, no parent_datasets)",
    "Good; nothing deducted for the empty fields (was_derived_from)",
]


@pytest.mark.parametrize("label", _CONCEDED_LABELS)
def test_a_label_reason_keeps_the_scope_of_the_clause_it_follows(label):
    """#3264: the label reason "no was_derived_from)" was cut from the label
    and read on its own, apart from the "despite" that governs it, so a
    conceded gap was a reason and --strict failed; the form with no
    punctuation was already substantive_only."""
    result = lint_q19(item(score=3, label=label, note="Held at 3 because no errata are recorded."))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        STATED, SUBSTANTIVE_ONLY, []), label


@pytest.mark.parametrize("label, reason", [
    ("Good versioning (no PROV graph)", "no PROV graph)"),
    ("Good versioning, no PROV graph", "no PROV graph"),
    ("Good versioning but no PROV graph", "but no PROV graph"),
])
def test_a_label_reason_after_credit_is_still_read(label, reason):
    """#3264: judging a label reason in the whole label removes only what a
    concession, acceptance or disclaimer governs; after credit it is read
    and shown as the same words as before."""
    rating = item(score=3, label=label, note="Held at 3 because no errata are recorded.")
    result = lint_q19(rating)
    assert result.concerns(REPRESENTATION) == ["graph_form"], label
    assert ("score_label", reason) in withholding_sentences(rating)


#: #3264: a withholding cue in the aside of an acceptance: the parenthesised
#: form must read as the same words with no parentheses do.
_ACCEPTED_ASIDE = ("The PROV graph documents all source data. The rubric accepts prose (even if "
                   "it falls short of a full graph). No errata are recorded.")


def test_a_cue_in_an_acceptance_aside_does_not_say_why():
    """#3264: the aside was marked unread, but its cue still set the stated
    basis, and because its sentence named no reason the neighbouring credit
    ("The PROV graph documents all source data.") was read as a graph_form
    reason. It now reads as the unparenthesised sentence does: nothing says
    why, and the cue is reported as unread."""
    plain = lint_q19(item(score=3, note=_ACCEPTED_ASIDE.replace("(", "").replace(")", "")))
    result = lint_q19(item(score=3, note=_ACCEPTED_ASIDE))
    assert (result.basis, result.verdict, result.cue_unread) == (
        UNSTATED, SUBSTANTIVE_ONLY, True)
    assert (plain.basis, plain.verdict, plain.cue_unread) == (
        result.basis, result.verdict, result.cue_unread)
    assert withholding_sentences(item(score=3, note=_ACCEPTED_ASIDE)) == []


def test_the_report_says_a_cue_in_an_acceptance_aside_was_not_read(tmp_path):
    """#3264: the aside is the acceptance's scope, not its clause, and the
    report line says so."""
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [item(
            score=3, note=_ACCEPTED_ASIDE)]}]}))
    lines, flagged = lint_report([tmp_path])
    assert flagged == 0 and lines[0].startswith(SUBSTANTIVE_ONLY)
    assert "a withholding cue stands in the scope of an acceptance or concession" in lines[0]


def test_a_cue_in_a_disclaimer_aside_is_disclaimed():
    """#3264: a cue in the scope of a disclaimer does not say why and is not
    reported as unread: the disclaimer covers it."""
    result = lint_q19(item(score=3, note=(
        "The PROV graph documents all source data. Nothing is deducted for the prose form "
        "(which falls short of a full graph). No errata are recorded.")))
    assert (result.basis, result.verdict, result.cue_unread) == (
        UNSTATED, SUBSTANTIVE_ONLY, False)


def test_a_cue_before_a_disclaimer_in_its_own_clause_still_says_why():
    """#3264 keeps the documented exception: a disclaimer after the cue in
    the cue's own clause removes that clause, not the cue."""
    result = lint_q19(item(score=3, note=(
        "The PROV graph documents all source data. It falls short of 5 not because of form "
        "but because no errata are recorded.")))
    assert (result.basis, result.verdict) == (STATED, SUBSTANTIVE_ONLY)
    assert all("documents all source data" not in r.sentence for r in result.reasons)


def test_a_cue_a_later_disclaimer_takes_back_does_not_send_the_lint_to_its_neighbours():
    """#3264: a clause that a following "but that is not penalised" takes
    back is not read for the disclaimer's words, so its cue does not say
    why, and the neighbouring credit is not read as a reason."""
    result = lint_q19(item(score=3, note=(
        "The PROV graph documents all source data. The empty was_derived_from falls short of "
        "the typed form, but that is not penalised. No errata are recorded.")))
    assert (result.basis, result.verdict, result.cue_unread) == (
        UNSTATED, SUBSTANTIVE_ONLY, False)


def test_a_label_contrast_in_an_acceptance_aside_does_not_start_the_reason():
    """#3264: "short of" in an acceptance's aside started the label reason,
    and the reason then ran on over the credit after the semicolon, so
    "typed PROV graph otherwise complete" was read as a graph_form reason."""
    rating = item(score=3, label=(
        "Prose lineage accepted (short of a full graph); typed PROV graph otherwise complete"),
        note="No errata are recorded.")
    result = lint_q19(rating)
    assert (result.verdict, result.concerns(REPRESENTATION)) == (SUBSTANTIVE_ONLY, [])
    assert [s for s in withholding_sentences(rating) if s[0] == "score_label"] == []


def test_a_label_cue_is_judged_in_the_whole_label():
    """#3264: a label's cue says why only where the whole label reads its
    clause. Here the cue follows an acceptance and a comma with no verb of
    its own, so the basis is unstated (the body's gaps are read too) and
    the cue is reported as unread; read cut out of the label, "held at 4"
    stated the basis and the body's graph_form gap went unread."""
    result = lint_q19(item(score=3, label=(
        "Prose accepted, was_derived_from empty and held at 4; no errata"),
        note="The lineage is not given as a PROV graph."))
    assert (result.basis, result.verdict, result.cue_unread) == (
        UNSTATED, REPRESENTATION_AND_SUBSTANTIVE, True)
    assert result.concerns(REPRESENTATION) == ["graph_form"]


def test_a_label_clause_that_accepts_is_judged_whole_not_from_the_cut():
    """#3264: "short of a graph" is cut from "Prose accepted short of a
    graph", whose clause accepts; judged from the cut it stated the basis.
    A contrast that names nothing read is about the words before it, so
    the reason reaches back over the whole clause, as it is judged."""
    label = "Prose accepted short of a graph whereas complete"
    rating = item(score=3, label=label, note="No errata are recorded.")
    result = lint_q19(rating)
    assert (result.basis, result.verdict, result.cue_unread) == (
        UNSTATED, SUBSTANTIVE_ONLY, True)
    assert withholding_sentences(rating) == [("score_label", label)]


def test_a_label_cue_in_an_accepting_clause_does_not_state_the_basis():
    """#3264: the label reason starts at "short of", inside the clause
    "Prose accepted short of a graph". Its cue is judged by that whole
    clause, which accepts, so it does not state the basis and the body's
    gap is read; judged from the cut, the clause accepted nothing."""
    result = lint_q19(item(score=3, label="Prose accepted short of a graph whereas no errata",
                           note="The lineage is not given as a PROV graph."))
    assert (result.basis, result.verdict, result.cue_unread) == (
        UNSTATED, REPRESENTATION_AND_SUBSTANTIVE, True)


def test_a_label_cue_in_an_acceptance_list_does_not_start_the_reason():
    """#3264: "held at 4" continues the acceptance before the comma, with
    no verb of its own, so it starts no label reason, although read on its
    own it would."""
    rating = item(score=3, label="Prose accepted, held at 4 whereas complete",
                  note="No errata are recorded.")
    assert [s for s in withholding_sentences(rating) if s[0] == "score_label"] == []
    assert lint_q19(rating).verdict == SUBSTANTIVE_ONLY


@pytest.mark.parametrize("rating", [
    item(score=3, label=_CONCEDED_LABELS[0], note="Held at 3 because no errata are recorded."),
    item(score=3, note=_ACCEPTED_ASIDE),
])
def test_strict_passes_a_conceded_label_and_an_accepted_aside(tmp_path, rating):
    """#3264: both Codex scenarios exit 0 under --strict."""
    from data_sheets_schema.cli import cli
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [rating]}]}))
    result = CliRunner().invoke(cli, ["evaluate", "q19-lint", "--strict", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "substantive_only" in result.output and "0 flagged of 1" in result.output


def test_a_score_below_maximum_with_no_reason_is_reported_as_such():
    result = lint_q19(item(note="Good provenance overall."))
    assert (result.verdict, result.flagged) == (REASON_NOT_DETERMINED, False)
    assert REASON_NOT_DETERMINED == "reason_not_determined"


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

def _section(job, status, link, sha="0" * 64, score=4):
    return (f"## {job}\n\nRecorded Q19: {score}/5. Status: `{status}`.\n\n"
            f"Original output: [evaluation]({link}); SHA256 `{sha}`\n\n")


_TABLE = ("| Record | Q19 | Recorded total /88 | Inspection status | Evidence |\n"
          "|---|---|---|---|---|\n"
          "| A | 4 | 70 | Requires adjudication | [Q19 rationale](a.json#L1) |\n")


@pytest.mark.parametrize("text, message", [
    ("# nothing here\n", "no inspection records"),
    (_section("A", "maybe", "a.json"), "unknown inspection status"),
    (_section("A", "requires_adjudication", "a.json") * 2, "two sections"),
    ("## A\n\nRecorded Q19: 4/5.\n", "no Q19 status"),
    ("| A | 4 | 70 | Requires adjudication | [x](a.json#L1) |\n" * 2, "listed twice"),
    # A table row that is not a record is refused, not skipped (#3014).
    (_TABLE + "| B | 4 | n/a | Requires adjudication | [x](b.json#L1) |\n", "review.md:4: table row"),
    (_TABLE + "| B | 4.5 | 70 | Requires adjudication | [x](b.json#L1) |\n", "review.md:4: table row"),
    (_TABLE + "| B | 4 | 70 | Requires adjudication | [x](b.json#L1) extra |\n", "review.md:4: table row"),
    (_TABLE + "| B-2 | 4 | 70 | Requires adjudication | [x](b.json#L1) |\n", "review.md:4: table row"),
])
def test_an_inspection_that_cannot_be_read_whole_is_refused(tmp_path, text, message):
    doc = tmp_path / "review.md"
    doc.write_text(text)
    with pytest.raises(ValueError, match=message):
        inspection_statuses(doc)


def test_a_table_header_and_separator_are_not_records(tmp_path):
    doc = tmp_path / "review.md"
    doc.write_text("Prose.\n\n" + _TABLE)
    assert list(inspection_statuses(doc)) == ["A"]


def _companion_case(job="A", status="requires_adjudication", output="a.json", sha="0" * 64,
                    score=4, **extra):
    """A companion case agreeing with `_section`/`_TABLE` unless told not to.
    `score=None` records no `q19_score`; a `q19` mapping stands in for it."""
    case = {"job_id": job, "status": status, "output": output, "evaluation_sha256": sha}
    if score is not None and "q19" not in extra:
        case["q19_score"] = score
    return case | extra


@pytest.mark.parametrize("cases, message", [
    ([_companion_case(), _companion_case(job="B")], r"only in the companion \['B'\]"),
    ([_companion_case(status="not_flagged_by_this_inspection")], "A: status disagree"),
    ([_companion_case(output="elsewhere/a.json")], "A: output disagree"),
    ([_companion_case(q19_score=3)], "A: Q19 score disagree"),
    ([_companion_case(q19={"score": 5})], "A: Q19 score disagree"),
    # #3228: a case that records no score does not agree with one that does.
    ([_companion_case(score=None)], "A: Q19 score disagree"),
    ([_companion_case(q19={"rationale": "no score"})], "A: Q19 score disagree"),
    ([_companion_case(sha="1" * 64)], "A: sha256 disagree"),
    ([_companion_case(sha=None)], "A: no evaluation_sha256"),
    ([_companion_case(), _companion_case()], "A is listed twice"),
    ([], "no cases"),
])
def test_a_companion_that_disagrees_with_its_markdown_is_refused(tmp_path, cases, message):
    doc = tmp_path / "review.md"
    doc.write_text(_section("A", "requires_adjudication", "a.json"))
    doc.with_suffix(".json").write_text(json.dumps({"cases": cases}))
    with pytest.raises(ValueError, match=message):
        inspection_statuses(doc)


def test_a_boolean_companion_score_is_not_a_score(tmp_path):
    """`True == 1` in Python; a companion recording `true` names no score."""
    doc = tmp_path / "review.md"
    doc.write_text(_section("A", "requires_adjudication", "a.json", score=1))
    doc.with_suffix(".json").write_text(json.dumps({"cases": [_companion_case(score=True)]}))
    with pytest.raises(ValueError, match="A: Q19 score disagree"):
        inspection_statuses(doc)


@pytest.mark.parametrize("case", [_companion_case(), _companion_case(q19={"score": 4})])
def test_a_companion_that_agrees_with_its_markdown_is_read(tmp_path, case):
    """The refusals above are disagreements, not a companion refused
    whatever it says: either score field agreeing with the Markdown reads."""
    doc = tmp_path / "review.md"
    doc.write_text(_section("A", "requires_adjudication", "a.json"))
    doc.with_suffix(".json").write_text(json.dumps({"cases": [case]}))
    assert inspection_statuses(doc)["A"].q19_score == 4


def test_a_companion_supplies_the_hash_the_markdown_does_not(tmp_path):
    doc = tmp_path / "review.md"
    doc.write_text(_TABLE)
    assert inspection_statuses(doc)["A"].sha256 is None
    doc.with_suffix(".json").write_text(json.dumps({"cases": [
        _companion_case(sha="2" * 64)]}))
    assert inspection_statuses(doc)["A"].sha256 == "2" * 64


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
    # #3070: 09-11 CHORUS v8 rep1 says nothing about why its score is 4; its
    # label's credit ("Substantial textual lineage …") was not read.
    unstated = [line for line in result.output.splitlines() if "(nothing says why" in line]
    assert [line.rsplit("/", 1)[-1] for line in unstated] == [
        "CHORUS_v8_rep1_r20_rating1_evaluation.json"]
    assert "whole rationale" not in result.output
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


def test_the_report_says_what_an_unstated_rating_was_read_for(tmp_path):
    """#3070: where nothing says why, the label's reason clauses and the
    body's gaps are read, not the whole rationale, and the line says so."""
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [item(
            label="Substantial textual lineage, but no versioning or typed derivation links",
            note="Version history is documented. parent_datasets is empty.")]}]}))
    lines, flagged = lint_report([tmp_path], show=True)
    assert flagged == 1 and "whole rationale" not in "\n".join(lines)
    assert "(nothing says why: label reason clauses and body gaps read)" in lines[0]
    assert "Version history is documented" not in "\n".join(lines)


def test_the_report_says_a_cue_was_not_read_rather_than_that_nothing_says_why(tmp_path):
    """#3205: a rating opening "Held at 4 because" does say why; where its
    cue shares a clause with an acceptance the line says the cue was not
    read. --strict still exits 0: the verdict is not a flag."""
    from data_sheets_schema.cli import cli
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [item(
            note="Held at 4 because was_derived_from is empty and the rubric accepts prose "
                 "for lineage.")]}]}))
    lines, flagged = lint_report([tmp_path])
    assert flagged == 0 and lines[0].startswith(REASON_NOT_DETERMINED)
    assert ("(a withholding cue stands in the scope of an acceptance or concession and was not "
            "read: label reason clauses and body gaps read)") in lines[0]
    assert "nothing says why" not in lines[0]
    result = CliRunner().invoke(cli, ["evaluate", "q19-lint", "--strict", str(tmp_path)])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("label", [
    "Typed was_derived_from links and errata missing",
    "Machine-readable PROV graph lacking errata",
    "Typed PROV graph with errata not recorded",
    "Good; typed PROV graph with errata not recorded",
])
def test_a_label_clause_left_unread_as_ambiguous_is_reported_as_such(tmp_path, label):
    """#3404: a label clause whose "not" or absence word stands inside it,
    naming both kinds of concern, is not read (#3146). Where nothing else
    says why, the report said "nothing says why", as if the label named
    nothing; it says the clause was left unread as ambiguous. The verdict
    is unchanged, and --strict still exits 0."""
    from data_sheets_schema.cli import cli
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert (result.basis, result.verdict, result.reasons) == (UNSTATED, REASON_NOT_DETERMINED, ())
    assert result.label_ambiguous and not result.cue_unread
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [item(label=label, note=_NEUTRAL)]}]}))
    lines, flagged = lint_report([tmp_path])
    assert flagged == 0 and lines[0].startswith(REASON_NOT_DETERMINED)
    assert ("(a label clause names both kinds of concern and was left unread as ambiguous: "
            "label reason clauses and body gaps read)") in lines[0]
    assert "nothing says why" not in lines[0]
    run = CliRunner().invoke(cli, ["evaluate", "q19-lint", "--strict", str(tmp_path)])
    assert run.exit_code == 0, run.output


@pytest.mark.parametrize("label, note, basis", [
    # A comma makes the absent one a clause of its own, which is read.
    ("Typed was_derived_from links, errata missing", _NEUTRAL, UNSTATED),
    # A clause of one kind is read.
    ("Textual lineage; version history and missingness absent", _NEUTRAL, UNSTATED),
    # The absence word stands in a concession, which is not read for its own
    # reason, not for ambiguity.
    ("Good despite typed PROV graph with errata not recorded", _NEUTRAL, UNSTATED),
    # The same with an absence word rather than "not" (#3683).
    ("Good despite typed was_derived_from links and errata missing", _NEUTRAL, UNSTATED),
    ("Good despite machine-readable PROV graph lacking errata", _NEUTRAL, UNSTATED),
    # A body sentence says why: the report does not say "nothing says why".
    ("Typed PROV graph with errata not recorded", "Held at 4 because no checksums are recorded.",
     STATED),
    # The issue's example: since review round 5 of PR #3417 reverted the
    # #3194 cue rule, a label cue clause naming both kinds is read.
    ("Held at 4 because the typed PROV graph lacks errata", _NEUTRAL, STATED),
])
def test_a_label_read_or_unread_for_another_reason_is_not_called_ambiguous(label, note, basis):
    result = lint_q19(item(label=label, note=note))
    assert (result.basis, result.label_ambiguous) == (basis, False), label


@pytest.mark.parametrize("label, verdict", [
    ("Typed PROV graph with errata not recorded but thin", REPRESENTATION_AND_SUBSTANTIVE),
    ("Typed PROV graph with errata not recorded but otherwise strong",
     REPRESENTATION_AND_SUBSTANTIVE),
    ("Typed PROV graph with errata not recorded without more", REPRESENTATION_AND_SUBSTANTIVE),
])
def test_a_both_kinds_clause_read_before_an_empty_contrast_is_not_called_unread(tmp_path, label,
                                                                                verdict):
    """#3681: a contrast that names nothing of its own reads the clause
    before it, so a clause naming both kinds is read there after all, and
    its concerns are the reasons; the report does not say it was left
    unread."""
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert (result.basis, result.verdict, result.label_ambiguous) == (UNSTATED, verdict, False)
    assert all(r.sentence == label for r in result.reasons)
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [item(label=label, note=_NEUTRAL)]}]}))
    lines, _ = lint_report([tmp_path])
    assert "left unread as ambiguous" not in lines[0]


@pytest.mark.parametrize("label", [
    "Typed PROV graph with errata not recorded but version history not detailed",
    # #3749: an absence word rather than "not". The contrast returns before
    # the clause-level absence check, so the part is noted in the loop.
    "Typed PROV graph with errata missing but version history not detailed",
    "Machine-readable PROV graph lacking errata but version history not detailed",
])
def test_a_both_kinds_clause_left_before_a_contrast_that_names_its_own_reason_is_unread(
        tmp_path, label):
    """#3681's contrast: where the contrast names a reason of its own, the
    clause before it stays unread, and is reported so, whether its word is
    "not" or an absence word (#3749). The reasons are the contrast's only."""
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert (result.verdict, result.concerns(SUBSTANTIVE), result.label_ambiguous) == (
        SUBSTANTIVE_ONLY, ["version_history"], True)
    assert [r.sentence for r in result.reasons] == ["but version history not detailed"]
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [item(label=label, note=_NEUTRAL)]}]}))
    lines, _ = lint_report([tmp_path])
    assert "left unread as ambiguous" in lines[0]
    assert "nothing says why" not in lines[0]


@pytest.mark.parametrize("label", [
    # The absence word opens the part: it says what is absent (#3146).
    "Missing errata with typed PROV graph but version history not detailed",
    # One kind only.
    "errata missing but version history not detailed",
    # In a concession: unread for that, not for ambiguity.
    "Good despite typed PROV graph with errata missing but version history not detailed",
])
def test_an_absence_word_before_a_contrast_is_not_called_ambiguous_when_its_part_is_clear(label):
    """#3749's bounds: the part before the contrast is noted only where its
    absence word stands inside it, in a part that is read, naming both
    kinds."""
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert (result.concerns(SUBSTANTIVE), result.label_ambiguous) == (["version_history"], False)


def test_both_unread_notes_are_reported_together(tmp_path):
    """A rating can leave a cue unread in an acceptance and a label clause
    unread as ambiguous; the report names both."""
    (tmp_path / "a_evaluation.json").write_text(json.dumps({
        "rubric": "rubric20-semantic", "categories": [{"questions": [item(
            label="Typed PROV graph with errata not recorded",
            note="Held at 4 because was_derived_from is empty and the rubric accepts prose "
                 "for lineage.")]}]}))
    lines, _ = lint_report([tmp_path])
    assert ("(a withholding cue stands in the scope of an acceptance or concession and was not "
            "read; a label clause names both kinds of concern and was left unread as ambiguous: "
            "label reason clauses and body gaps read)") in lines[0]


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


def _mirror_errata(tmp_path):
    """The 09-11 errata, its companion and the 24 evaluations it read, laid
    out as in the repository so its relative links resolve."""
    notes = tmp_path / ERRATA.parent.relative_to(ROOT)
    notes.mkdir(parents=True)
    for doc in (ERRATA, ERRATA.with_suffix(".json")):
        shutil.copy(doc, notes / doc.name)
    evaluations = tmp_path / EVALUATION_DIRS[0].relative_to(ROOT)
    shutil.copytree(EVALUATION_DIRS[0], evaluations)
    return notes / ERRATA.name, evaluations


def test_an_evaluation_the_errata_left_unflagged_is_checked_against_its_bytes(tmp_path):
    """#3010: the errata's Markdown hashes only the 15 it flagged; the 9 it
    left unflagged, two of the pinned disagreements among them, are checked
    against the companion's hashes."""
    doc, evaluations = _mirror_errata(tmp_path)
    lines, _ = lint_report(inspections=[doc])
    assert "inspection agreement: 22/24 (flagged by both 15, by neither 7)" in lines
    target = evaluations / "CM4AI_v8_rep1_r20_rating1_evaluation.json"
    assert not inspection_statuses(doc)["CM4AI_v8_rep1_r20_rating1"].flagged
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="CM4AI_v8_rep1_r20_rating1: .* is not the bytes"):
        lint_report(inspections=[doc])


def test_an_inspection_record_with_no_hash_is_refused(tmp_path):
    doc, _ = _mirror_errata(tmp_path)
    doc.with_suffix(".json").unlink()
    with pytest.raises(ValueError, match="AI_READI_v7_rep1_r20_rating1: the inspection records no sha256"):
        lint_report(inspections=[doc])


def test_an_evaluation_whose_q19_is_not_the_recorded_score_is_refused(tmp_path):
    """The hash matches; the inspection recorded another score for it."""
    evaluation = tmp_path / "A_evaluation.json"
    shutil.copy(EVALUATION_DIRS[1] / "CHORUS_v7_rep2_r20_rating1_evaluation.json", evaluation)
    doc = tmp_path / "semantic_review.md"
    doc.write_text(_section("A", "not_flagged_by_this_inspection", evaluation.name,
                            sha=sha256_of(evaluation), score=3))
    with pytest.raises(ValueError, match="records Q19 3, .* scores 4"):
        lint_report(inspections=[doc])
    doc.write_text(_section("A", "not_flagged_by_this_inspection", evaluation.name,
                            sha=sha256_of(evaluation), score=4))
    assert lint_report(inspections=[doc])[1] == 1


# -- an empty-slot match needs words saying the slot is empty (#2982) ---------

@pytest.mark.parametrize("note", [
    "Held at 4 because errata are thin; was_derived_from links every release to its parent.",
    "It falls short of 5 on version history: the changelog is thin and parent_datasets names "
    "the source release.",
])
def test_an_empty_slot_named_as_credit_in_a_sentence_saying_nothing_is_empty_is_not_read(note):
    """#2982: the empty-slot concern matches a slot's name; where nothing
    the lint reads with it says anything is empty or absent, the slot is
    credit. It is still reported as a mention: vocabulary alone."""
    result = lint_q19(item(note=note))
    assert (result.basis, result.verdict, result.concerns(REPRESENTATION)) == (
        STATED, SUBSTANTIVE_ONLY, []), note
    assert any(m.concern == "empty_slot" for m in result.mentions)


@pytest.mark.parametrize("note", [
    # The emptiness word in a neighbouring clause of the same sentence.
    "Held at 4 because the dedicated derivation fields (was_derived_from, parent_datasets) "
    "are empty.",
    "No version history, errata or structured derivation, so held at 4.",
    "Held at 4 because what is missing is the typed representation: derivation lives in "
    "prose rather than in was_derived_from edges.",
])
def test_an_empty_slot_whose_emptiness_a_neighbouring_clause_states_is_read(note):
    """#2982: the requirement is sentence-level, because a clause-level one
    loses the committed reasons that name the slot in a list or parenthesis
    and say it is empty beside it."""
    assert "empty_slot" in lint_q19(item(note=note)).concerns(REPRESENTATION), note


@pytest.mark.parametrize("note", [
    "Held at 4 because the missing-data documentation sits beside was_derived_from.",
    "Held at 4 because missing data documentation sits beside was_derived_from.",
])
def test_missing_data_documentation_does_not_say_a_slot_is_empty(note):
    """#3434 (c), #2982: "missing-data documentation" names content, so it
    does not make a slot named in the same sentence an empty-slot reason."""
    result = lint_q19(item(note=note))
    assert (result.basis, result.concerns(REPRESENTATION)) == (STATED, []), note


@pytest.mark.parametrize("field, text, basis", [
    ("note", "Held at 4 because of the absence of was_derived_from links.", STATED),
    ("note", "Held at 4 because the record omits was_derived_from.", STATED),
    ("note", "Held at 4 because the record omitted was_derived_from.", STATED),
    ("note", "Held at 4: was_derived_from and parent_datasets are unset.", STATED),
    ("note", "Lineage is in prose; the absence of was_derived_from keeps it from 5.", STATED),
    ("label", "Held at 4: absence of was_derived_from", STATED),
])
def test_an_absence_stated_as_absence_omits_or_unset_is_an_empty_slot_reason(field, text, basis):
    """#3539: the #2982 gate dropped these stated absences, which main read
    as empty-slot reasons: `_EMPTINESS` knew "absent" but not "absence",
    and neither "omits" nor "unset". They read as on main again."""
    rating = item(label=text, note=_NEUTRAL) if field == "label" else item(note=text)
    result = lint_q19(rating)
    assert (result.basis, result.verdict, [r.concern for r in result.reasons]) == (
        basis, REPRESENTATION_ONLY, ["empty_slot"]), text


@pytest.mark.parametrize("note", [
    "Held at 4: two absences, was_derived_from and parent_datasets.",
    "Held at 4 because parent_datasets is the sole absentee.",
    "Held at 4 because was_derived_from and parent_datasets remain the gaps.",
    "Held at 4: the one gap is parent_datasets.",
    "Held at 4 because the dedicated provenance field is silent.",
    "Held at 4 because the dedicated provenance field is therefore silent.",
    "Held at 4 because parent_datasets is the only gap.",
    "Held at 4: the three gaps are resources, variables and parent_datasets.",
    "Held at 4: the four genuine absences are doi, variables and parent_datasets.",
])
def test_an_absence_named_as_a_noun_or_state_is_not_recognised(note):
    """#3544, a measurement: committed evaluation text the vocabulary was
    not written against says a slot is absent in these forms, and the
    closed list does not read them (11 of the 31 misses the module
    docstring counts). Forms that read them were withdrawn from PR #3654
    after three review rounds each found a slot named as credit read as an
    empty-slot reason (#3668, #3680, #3694); widening the list is a design
    decision. Main's reading stands."""
    result = lint_q19(item(note=note))
    assert (result.basis, result.verdict, result.reasons) == (STATED, REASON_NOT_DETERMINED, ()), note


_CREDIT = "was_derived_from links every release to its parent."


@pytest.mark.parametrize("note, verdict, concerns", [
    # A slot named as credit beside a gap in something else: main's gate
    # drops the slot, and the bare words "gap" and "silent" re-admitted it.
    (f"Held at 4 because errata are thin, a gap; {_CREDIT}", SUBSTANTIVE_ONLY, ["version_history"]),
    (f"Held at 4 because errata leave gaps in the history; {_CREDIT}", SUBSTANTIVE_ONLY,
     ["version_history"]),
    (f"Held at 4 because the errata are silent on the Snellen removal; {_CREDIT}",
     SUBSTANTIVE_ONLY, ["version_history"]),
    (f"Held at 4 because errata are thin, a documentation gap; {_CREDIT}", SUBSTANTIVE_ONLY,
     ["version_history"]),
    (f"Held at 4 because two integrity gaps remain; {_CREDIT}", REASON_NOT_DETERMINED, []),
    # A slot said to fill the gap is not absent.
    ("Held at 4 because was_derived_from fills the gap.", REASON_NOT_DETERMINED, []),
    ("Held at 4 because was_derived_from fills the one gap.", REASON_NOT_DETERMINED, []),
    ("Held at 4 because related_datasets covers the one gap.", REASON_NOT_DETERMINED, []),
    # With an article or quantifier between, or in the passive (#3680).
    ("Held at 4 because was_derived_from fills the two gaps.", REASON_NOT_DETERMINED, []),
    ("Held at 4 because was_derived_from closes the two remaining gaps.",
     REASON_NOT_DETERMINED, []),
    ("Held at 4 because was_derived_from fills both of the two gaps.", REASON_NOT_DETERMINED, []),
    ("Held at 4 because the two gaps are filled by was_derived_from.", REASON_NOT_DETERMINED, []),
    ("Held at 4 because the one gap is closed by parent_datasets.", REASON_NOT_DETERMINED, []),
    # The perfect, modal and two-adverb passive and a numeral quantifier
    # (#3694).
    ("Held at 4 because the one gap has been closed by parent_datasets.",
     REASON_NOT_DETERMINED, []),
    ("Held at 4 because the two gaps have been filled by was_derived_from.",
     REASON_NOT_DETERMINED, []),
    ("Held at 4 because the two gaps will be filled by was_derived_from.",
     REASON_NOT_DETERMINED, []),
    ("Held at 4 because the two gaps are now fully filled by was_derived_from.",
     REASON_NOT_DETERMINED, []),
    ("Held at 4 because was_derived_from fills two of the three gaps.", REASON_NOT_DETERMINED, []),
    # "silent" modifying something other than a slot (#3684). The bare
    # "silent" of this PR's first commit read both as empty-slot reasons; the
    # later "is/are ... silent" form did not, and neither does main's list,
    # which reads "silent" in no form. All those forms are withdrawn.
    (f"Held at 4 because errata are thin, with silent corrections; {_CREDIT}", SUBSTANTIVE_ONLY,
     ["version_history"]),
    (f"Held at 4 because of silent errata; {_CREDIT}", SUBSTANTIVE_ONLY, ["version_history"]),
])
def test_a_gap_or_silence_about_something_else_licenses_no_slot(note, verdict, concerns):
    """#3668, #3680, #3694: "gap" and "silent" as often name a concern other
    than a slot, or a slot filling one, and the gate is sentence-level;
    main's reading of each of these stands. On all but one of them some
    form PR #3654 tried and withdrew (#3544) read a slot as an empty-slot
    reason: on the two #3684 cases only the bare "silent" of the first
    commit did, and on "related_datasets covers the one gap" none did; it
    pins that a slot filling a gap is not absent."""
    result = lint_q19(item(note=note))
    assert (result.basis, result.verdict, [r.concern for r in result.reasons]) == (
        STATED, verdict, concerns), note


@pytest.mark.parametrize("note", [
    # The issue's example, and the placements the #3544 measurement found:
    # the list is closed and does not recognise them.
    "Held at 4 because was_derived_from is left out.",
    "Held at 4 because derivation is recorded in related_datasets rather than was_derived_from.",
    "Held at 4 because related_datasets entries stand in for parent_datasets.",
])
def test_an_absence_phrased_otherwise_is_still_not_recognised(note):
    """The documented limit (#3544): the words are a closed list, so an
    absence stated otherwise gives no empty-slot reason."""
    result = lint_q19(item(note=note))
    assert (result.basis, result.verdict, result.reasons) == (STATED, REASON_NOT_DETERMINED, ())


#: Every example the review rounds of PR #3417 found regressed against main
#: (#3464, #3485, #3499, #3500, #3501, #3538, #3540), with main's basis,
#: verdict and reasons: (issue, field, text, basis, verdict, concerns). The
#: clause-level credit rules (#3128) and the label cue one-kind rule (#3194)
#: that caused them were reverted to main's behaviour in review round 5. A
#: label row carries the neutral body note `_NEUTRAL`; every row is at 4/5.
_MAIN_READINGS = [
    ("#3464", "note", "Derivation is described across four fields, but this keeps it from 5. "
     "Version history is excellent.", STATED, REPRESENTATION_ONLY, ["scattered"]),
    ("#3464", "note", "Lineage is recorded as human-readable prose, but it is held at 4 for "
     "that reason.", STATED, REPRESENTATION_ONLY, ["machine_form"]),
    ("#3464", "note", "The provenance is a human-readable narrative, however, which keeps it "
     "from 5.", STATED, REPRESENTATION_ONLY, ["machine_form"]),
    ("#3464", "note", "Errata are recorded in the changelog, but that falls short of 5.",
     STATED, SUBSTANTIVE_ONLY, ["version_history"]),
    ("#3464", "note", "The provenance is a human-readable narrative, but that is why it does "
     "not reach 5.", STATED, REPRESENTATION_ONLY, ["machine_form"]),
    ("#3485", "label", "Held at 4 because was_derived_from is empty and no errata are recorded",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["empty_slot", "version_history"]),
    ("#3485", "label", "Held at 4 because no PROV graph and no errata",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "version_history"]),
    ("#3485", "label", "Held at 4 because no PROV graph is given and no errata are recorded",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "version_history"]),
    ("#3485", "label", "Held at 4 because the PROV graph and the errata are both missing",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "version_history"]),
    ("#3485", "label", "Held at 4 because of no PROV graph and no checksums",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "integrity"]),
    ("#3499", "note", "Version history is thorough. It is held at 4 whereas a 5 requires a "
     "typed PROV graph.", STATED, REPRESENTATION_ONLY, ["graph_form"]),
    ("#3499", "note", "Errata are recorded. Held at 4 however, for want of a PROV graph.",
     STATED, REPRESENTATION_ONLY, ["graph_form"]),
    ("#3499", "note", "Version history is thorough. Held at 4, but for the absence of a typed "
     "PROV graph.", STATED, REPRESENTATION_ONLY, ["graph_form"]),
    ("#3499", "note", "Held at 4, but for the absence of a typed PROV graph.",
     STATED, REPRESENTATION_ONLY, ["graph_form"]),
    ("#3499", "note", "It is held at 4 whereas a 5 requires a typed PROV graph.",
     STATED, REPRESENTATION_ONLY, ["graph_form"]),
    ("#3500", "label", "Held at 4 whereas a 5 requires a typed PROV graph",
     STATED, REPRESENTATION_ONLY, ["graph_form"]),
    ("#3500", "label", "Very Good, held at 4, however, for want of a typed PROV graph",
     STATED, REPRESENTATION_ONLY, ["graph_form"]),
    ("#3501", "note", "No errata are recorded, and the lineage is narrative rather than "
     "graph-structured or machine-readable.", UNSTATED, REPRESENTATION_AND_SUBSTANTIVE,
     ["graph_form", "machine_form", "version_history"]),
    ("#3501", "note", "Errata are not recorded, and the graph must be reconstructed by a reader.",
     UNSTATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "scattered", "version_history"]),
    ("#3501", "note", "Held at 4 because no errata are recorded, and the lineage is narrative "
     "rather than graph-structured or machine-readable.", STATED,
     REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "machine_form", "version_history"]),
    # Review round 5.
    ("#3538", "label", "It is held at 4 because no PROV graph and no errata",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "version_history"]),
    ("#3538", "label", "Score held at 4 because no PROV graph and no errata",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "version_history"]),
    ("#3538", "label", "Very good lineage held at 4 because no PROV graph and no errata",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "version_history"]),
    ("#3538", "label", "One point deducted for no PROV graph and no errata",
     STATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "version_history"]),
    ("#3540", "label", "No errata, however lineage is human-readable prose",
     UNSTATED, REPRESENTATION_AND_SUBSTANTIVE, ["machine_form", "version_history"]),
    ("#3540", "label", "No errata, but the graph must be reconstructed by a reader",
     UNSTATED, REPRESENTATION_AND_SUBSTANTIVE, ["graph_form", "scattered", "version_history"]),
]


@pytest.mark.parametrize("issue, field, text, basis, verdict, concerns", _MAIN_READINGS,
                         ids=[f"{row[0]}-{i}" for i, row in enumerate(_MAIN_READINGS)])
def test_every_review_regression_reads_as_on_main(issue, field, text, basis, verdict, concerns):
    """The regression table: rounds 2 to 5 of PR #3417's review each found a
    major regression against main from the clause-level credit rules
    (#3128) or the label cue one-kind rule (#3194). Each row is main's
    reading, checked against a git-archive copy of origin/main; none of
    the issues says main was wrong for its row."""
    rating = item(label=text, note=_NEUTRAL) if field == "label" else item(note=text)
    result = lint_q19(rating)
    assert (result.basis, result.verdict, sorted({r.concern for r in result.reasons})) == (
        basis, verdict, concerns), (issue, text)


#: #3576: texts where the #2982 gate filters the only empty-slot match
#: ("incomplete" and "partly populated" are not `_EMPTINESS` words), with
#: origin/main's basis and concerns (checked against a git-archive copy of
#: it). The round-5 branch let the empty result steer what was read and
#: gave the credit around it as the reason: the label reason range moved
#: back over "Excellent version history", a cue sentence's neighbour was
#: read, and a body part's preceding credit was joined to it.
_FILTERED_ONLY_MATCH = [
    ("label", "Excellent version history but held at 4 for incomplete was_derived_from",
     STATED, ["empty_slot"]),
    ("label only", "Excellent version history but held at 4 for incomplete was_derived_from",
     STATED, ["empty_slot"]),
    ("note", "Excellent version history. Held at 4 for incomplete was_derived_from.",
     STATED, ["empty_slot"]),
    ("unstated note", "Version history is excellent but was_derived_from is only partly "
     "populated.", UNSTATED, ["empty_slot"]),
    ("unstated note", "Errata are recorded in the changelog but was_derived_from is "
     "incomplete.", UNSTATED, ["empty_slot"]),
]


@pytest.mark.parametrize("field, text, main_basis, main_concerns", _FILTERED_ONLY_MATCH)
def test_a_filtered_empty_slot_match_never_sends_the_lint_to_credit(
        field, text, main_basis, main_concerns):
    """#3576: the emptiness gate filters reasons and chooses nothing that is
    read (`_names_reason`). Against main the basis is unchanged and the
    reasons are main's less the filtered empty-slot match, so no credit
    becomes a reason."""
    rating = {"label": item(label=text, note=_NEUTRAL), "label only": item(label=text),
              "note": item(note=text),
              "unstated note": item(label="Very good", note=text)}[field]
    result = lint_q19(rating)
    concerns = {r.concern for r in result.reasons}
    assert result.basis == main_basis, text
    assert concerns <= set(main_concerns) - {"empty_slot"}, (text, result.reasons)
    assert result.verdict == REASON_NOT_DETERMINED, text


@pytest.mark.parametrize("field, text, concerns", [
    # #3194: a label clause whose cue stands inside it and names both kinds.
    ("label", "Typed PROV graph falls short on errata", ["graph_form", "version_history"]),
    ("label", "Typed PROV graph held at 4 for errata", ["graph_form", "version_history"]),
    # #3128: label credit after a contrast, and body credit before a cue or
    # a contrast in a sentence that says why.
    ("label", "No PROV graph, but excellent version history", ["graph_form", "version_history"]),
    ("note", "Checksums are recorded (md5 on every archive), and it is held at 4 because no "
     "PROV graph is given.", ["graph_form", "integrity"]),
    ("note", "Above the version-history band on several counts - named sources with persistent "
     "identifiers and file-level fixity - but the top band requires the links to be "
     "represented as a graph.", ["graph_form", "identifiers", "integrity"]),
])
def test_the_forms_3128_and_3194_name_are_still_read_as_on_main(field, text, concerns):
    """#3128 and #3194 stay open: their heuristics regressed main on stated
    reasons in five review rounds of PR #3417 and were reverted, so these
    forms read their credit as a reason, as on main, until a design
    decision settles how credit is told from a reason."""
    rating = item(label=text, note=_NEUTRAL) if field == "label" else item(note=text)
    result = lint_q19(rating)
    assert sorted({r.concern for r in result.reasons}) == concerns, text


# -- the committed corpus -----------------------------------------------------

#: Empty-slot reasons on the committed ratings whose clause names the slot in
#: a list or parenthesis, with the emptiness stated in a neighbouring clause
#: of the same sentence. Each was read by hand; the value is the words that
#: say the slot is empty.
_EMPTY_IN_A_NEIGHBOURING_CLAUSE = {
    ("label_aware/AI_READI_2026-09-04gapi_rep1_evaluation.json",
     "and the dedicated derivation slots"): "(was_derived_from, parent_datasets) and errata are empty",
    ("label_aware/CHORUS_2026-08-22c_rep3_evaluation.json",
     "errata or structured derivation graph."): "there is no version history, errata or structured",
    ("label_aware/CHORUS_2026-08-28bapi_rep1_evaluation.json",
     "errata or structured derivation"): "No version history, errata or structured derivation",
    ("label_aware/CM4AI_2026-09-01api_rep3_evaluation.json",
     "and the typed derivation slots that would express lineage in the datasheet"):
        "was_derived_from and parent_datasets, are both empty",
    ("label_aware/superseded_fable5/CHORUS_2026-09-01api_rep3_evaluation.json",
     "structured derivation path or missingness documentation."):
        "No version history, errata, structured derivation path",
    ("reference_2026-09-11/AI_READI_v7_rep3_r20_rating1_evaluation.json",
     "derivation lives in prose across raw_data_sources and preprocessing_strategies rather than "
     "in was_derived_from or parent_datasets edges"): "What is missing is the typed representation",
    ("reference_2026-09-11/AI_READI_v8_rep3_r20_rating1_evaluation.json",
     "the two schema slots built for derivation"): "(`was_derived_from`, `parent_datasets`) are empty",
    ("reference_2026-09-11/CHORUS_v7_rep2_r20_rating1_evaluation.json",
     "Scored 4 rather than 5 because the dedicated derivation fields"):
        "(was_derived_from, parent_datasets) are empty",
    ("reference_2026-09-11/CM4AI_v7_rep3_r20_rating1_evaluation.json",
     "and the schema's own derivation slots"): "was_derived_from and parent_datasets - are empty",
    ("reference_2026-09-12_cborg_runtime/AI_READI_v8_rep1_r20_rating1_evaluation.json",
     "was_derived_from"): "(was_derived_from, parent_datasets, errata) are all empty",
}


@pytest.mark.corpus
def test_every_empty_slot_reason_in_the_committed_ratings_is_said_to_be_empty():
    """The module docstring's count (#3069, #2982, 88 since #3260 read
    CHORUS v7 rep1's outer-list item). The empty-slot concern matches a
    slot's name; on the 133 committed ratings each such reason names the slot
    in a clause saying something is empty or negated, or in one of the ten
    hand-read lists above whose emptiness a neighbouring clause states. A
    credit clause naming a populated slot is neither, so it fails here, as
    CHORUS 2026-09-04f API rep1's did before a sentence naming no gap went
    unread where nothing says why."""
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "data/evaluation_llm"],
                            capture_output=True, text=True, check=True).stdout.split("\0")
    ratings = [ROOT / f for f in listed if f.endswith("_evaluation.json")
               and json.loads((ROOT / f).read_text(encoding="utf-8")).get("rubric")
               == "rubric20-semantic"]
    assert len(ratings) == 133
    empty = re.compile(r"\b(?:empty|absent|unpopulated|unused|no|not|none|nor|neither|lacks?"
                       r"|lacking|missing|without|null)\b", re.I)
    base = ROOT / "data/evaluation_llm/rubric20_semantic"
    reasons = [(path.relative_to(base).as_posix(), r) for path in ratings
               for r in lint_file(path).reasons if r.concern == "empty_slot"]
    assert len(reasons) == 88
    elsewhere = {(path, r.clause): r.sentence for path, r in reasons if not empty.search(r.clause)}
    assert set(elsewhere) == set(_EMPTY_IN_A_NEIGHBOURING_CLAUSE)
    for key, said in _EMPTY_IN_A_NEIGHBOURING_CLAUSE.items():
        assert said in elsewhere[key], key
    # The credit sentence that was read as an empty-slot reason (#3069).
    chorus = lint_file(base / "label_aware/CHORUS_2026-09-04fapi_rep1_evaluation.json")
    assert chorus.basis == UNSTATED
    assert [r for r in chorus.reasons if "explicit rather than implied" in r.sentence] == []


#: The placements the #3544 measurement found by hand among the committed
#: evaluation sentences that name a slot outside the Q19 fields and carry
#: no absence word: each says a slot is unused by saying where its content
#: is instead, and none is recognised. A fragment of each sentence.
_UNRECOGNISED_PLACEMENTS = [
    "placed in descriptive fields rather than structured fields",
    "in narrative fields rather than structured fields",
    "recorded under used_software rather than the dedicated slot",
    "inside the citation rather than a dedicated slot",
    "sit outside their dedicated slots",
    "derivation in related_datasets rather than was_derived_from",
    "only in prose or in adjacent slots rather than in their dedicated structured fields",
    "carried in notes rather than structured slots",
    "Substituted rather than named",
    "Covered by semantic equivalents: parent_datasets",
    "sit in prose rather than in the structured slots",
    "derivation recorded outside the derivation slots",
    "live in free-text notes rather than structured slots",
    "stand in for parent_datasets",
    "residing in prose rather than in the designated structured fields",
    "parent_datasets is arguably satisfied semantically",
    # Credit until the ordered test's step 2 was asked of the 111 credit
    # sentences (#3838). Each says where a slot's content is instead, in so
    # many words: the first follows "parent_datasets is absent." in its
    # issue (VOICE 2026-09-04f API rep1, rubric20 issues_detected[5]); the
    # second lists the related_datasets edges "in place of a parent_datasets
    # slot" in AI_READI v8 rep2's Q19 evidence (09-11 reference). Both are
    # misses: neither carries an `_EMPTINESS` word.
    "The derivation is carried instead by was_derived_from (narrative)",
    "in place of a parent_datasets slot",
]

#: The absences the #3544 measurement found named as a noun or a state
#: among the same sentences: "absences", "absentee", a counted or sole
#: "gap", "silent". The closed list does not recognise them. Forms that did
#: (`_ABSENCE_NAMED`) were tried on PR #3654 and withdrawn after three
#: review rounds each found a slot named as credit read as an empty-slot
#: reason (#3668, #3680, #3694); widening the list is a design decision
#: (#3544). A fragment of each sentence; the last is the whole sentence.
_UNRECOGNISED_NAMED_ABSENCES = [
    "Falls short of the 90% threshold on two absences: resources, and parent_datasets",
    "the four genuine absences (doi, variables, parent_datasets, confidentiality_level)",
    "two of the four absences are functionally covered by sibling slots",
    "parent_datasets is the sole absentee",
    "The one gap, parent_datasets, is functionally covered",
    "parent_datasets is the only gap, and the derivation",
    "The two gaps are structural rather than informational",
    "The three gaps are slot-selection rather than information gaps",
    "The dedicated provenance field is therefore silent",
    "confidentiality_level is now populated (an improvement over sibling records); doi, variables, "
    "resources and parent_datasets remain the gaps",
    "doi, variables, resources and parent_datasets remain the gaps.",
]

#: The rest of the hand-read sentences that are not credit or a description
#: of a populated slot (#3669), by class: a fragment of each. These were
#: classed before the module docstring's ordered test existed; steps 1 and 2
#: (named absence, then placement) were re-asked of every one, against its
#: own rating, and none moved (#3838). Where the answer was closest it is
#: noted beside the pin.
_HAND_READ_NOT_CREDIT = {
    # An absence the list does not recognise that is not a placement.
    "unrecognised_absence": [
        "5 of 6 creators unnamed in structured fields",
        "parent_datasets logged as a low-severity completeness gap",
    ],
    # How many designated fields are populated, naming no absent slot.
    # Step 1: "four of the five ... are populated" implies a fifth that is
    # not, but names neither it nor its absence; each quality note says what
    # is missing in its next sentence, with an `_EMPTINESS` word
    # ("future_use_impacts is empty"; "no acquisition window is given")
    # (#3838).
    "count": [
        "Four of the five designated fields are populated and the guidance",
        "Four of the five designated fields are populated with genuinely",
    ],
    # A criticism of what a populated slot holds. Step 2 was re-asked of each
    # (#3838) and none says where a slot's content is instead:
    # - "was_derived_from is present but as prose ... rather than an
    #   identifier" (AI_READI 2026-09-04g API rep2, Q19 evidence) says what
    #   the slot holds and in what form, not that its content is elsewhere.
    #   Its rating says the link to fairhub.2 "is recoverable only from
    #   related_datasets", a placement, in a sentence of its own; this one
    #   names no other holder, where "keeping the study-name prose in notes"
    #   among the recommendations was a criticism for the same reason;
    # - "The record discloses this, but the structured field understates the
    #   standards landscape" (CHORUS v7 rep1, rubric10 cborg): "this" is the
    #   collapse of three standards into OTHER, which its rating says
    #   source_caveats discloses. That is a caveat about a populated slot's
    #   value, not the slot's content held elsewhere, as "keep the
    #   alternative reading in source_caveats" was not;
    # - the two institution sentences and the FAIRhub data-entry sentence
    #   object to populated attributions; the conflict is disclosed in the
    #   caveats, an alternative to the value and not its content elsewhere.
    "criticism": [
        "Institutional attribution is contested in the structured fields themselves",
        "Responsible-institution conflict is recorded but left unresolved",
        "the structured field understates the standards landscape",
        "FAIRhub data-entry error propagated into two structured slots",
        "was_derived_from is present but as prose",
    ],
    # What was_derived_from records, rather than a parent dataset. Each says
    # what the populated slot holds; the absence of related_datasets or
    # parent_datasets is stated elsewhere in the same sub-element, with an
    # `_EMPTINESS` word ("related_datasets: absent", "No parent_datasets and
    # no related_datasets"), not in these (#3838).
    "qualification": [
        "was_derived_from carries source-system provenance rather than",
        "was_derived_from describes source systems rather than a parent dataset",
        "was_derived_from points to clinical source systems rather than to datasets",
        "was_derived_from records derivation from source clinical systems",
    ],
    # A slot's bare name, as a list item.
    "bare_name": ["parent_datasets", "was_derived_from"],
    # The criterion's definition.
    "criterion": [
        "Proportion of mandatory schema fields populated (id, title, description, keywords, "
        "license, doi, page, creators, purposes, instances, resources, parent_datasets, "
        "variables, confidentiality level)",
        "Proportion of mandatory schema fields populated (id, title, description, keywords, "
        "license, doi, page, creators, purposes, instances, resources, parent_datasets, "
        "variables, confidentiality_level)",
    ],
}


#: The 122 sentences the leading-verb regex puts among the recommendations,
#: read by hand (#3747) with the classes of the 155 and one more, a request.
#: A fragment of each; a fragment that is a whole sentence matches only that
#: sentence (one is the opening of another). Each is classed by the ordered
#: test in the module docstring, whose first answer wins: named absence,
#: placement, criticism, else request. A recommendation's imperative is not
#: the absence: a sentence is read for what it says beside the imperative,
#: and against its own rating.
_RECOMMENDATIONS_READ = {
    # A named absence, in the noun form of the 11.
    "named_absence": [
        "Fill the structural gaps: record the Snellen variable removal",
    ],
    # A placement, of the kind the 16 count: where the slot's content is
    # instead, in another slot, a relation, prose, notes or a file.
    "placement": [
        "in addition to the typed related_datasets entry",
        "revision history currently held in related_datasets notes",
        "rather than reconstructed from three others",
        "make the provenance chain machine-readable rather than inferable from prose",
        "evidenced by structured fields rather than prose alone",
        "now carried only by raw_data_sources prose",
        "record version predecessors as parent_datasets in addition to the related_datasets",
        "express the version predecessors as parent_datasets in addition to the related_datasets",
        "(large-v3 mentioned in descriptions)",
        "Instantiate the provenance graph the notes describe",
        "Keep the RRID in the citation as published",
        "Mirror the is_new_version_of targets into parent_datasets and list",
        "or state that the relation is expressed only through related_datasets",
        "rather than only related_datasets prose",
        "out of source_caveats into structured slots",
        "regulatory_restrictions.confidentiality_level with the values already present in prose",
        "from the prior-version and source DOIs already in related_datasets",
        "Populate parent_datasets from the two is_new_version_of edges",
        "so version derivation resolves through the derivation slots as well as related_datasets",
        "with the predecessor release DOIs already present in related_datasets",
        "with the prior version DOIs in addition to related_datasets",
        "making the derivation graph queryable rather than inferable from prose",
        "Populate parent_datasets with the is_new_version_of targets",
        "Synapse raw-audio accession already named in related_datasets",
        "Synapse raw-audio accession already recorded in related_datasets",
        "Health Data Nexus records already named in related_datasets",
        "source dataset DOIs already listed in related_datasets",
        "keeping the descriptive related_datasets entry alongside it",
        "(duplicating related_datasets is acceptable)",
        "machine-discoverable through the derivation slots as well as through related_datasets",
        "already carried in related_datasets (doi:10.13026/k81f-qr68 for v3.0.0",
        "already named in related_datasets (doi:10.13026/k81f-qr68, doi:10.57764/qb6h-em84)",
        "all of which have prose or external equivalents today",
        "Populate parent_datasets/was_derived_from from related_datasets",
        "from information already present in the record",
        "parent_datasets/was_derived_from from the is_new_version_of relations.",
        "from the is_new_version_of relations; add an errata entry",
        "the ancestry that related_datasets currently holds alone",
        "Populate the dedicated slots that currently hold their content elsewhere: download_url",
        "Populate the dedicated slots with the values already present in prose",
        "the negative findings currently buried in notes",
        "mirror the derives_from edge into parent_datasets",
        "so the documented lineage becomes traversable rather than narrative",
        "keeping the related_datasets entries as the typed expression of the same relations",
        "deposition archives and external repository deposits already named in raw_data_sources",
        "ATCC, HipSci and MassIVE sources already described in prose",
        "the typed links that related_datasets already implies",
        "so the provenance graph asserted in notes is realised in the datasheet",
        "so the lineage already present in prose becomes an entity-activity-agent structure",
        "deposition-archive and external-repository sources already named in raw_data_sources",
        "device-export-to-standard conversions already described",
        "device-export-to-standard-format conversions already described in prose",
        "release chain already typed in related_datasets, so lineage is machine-readable",
        "release chain already typed in related_datasets.",
        "Promote information already present in prose into its structured field",
        "the October 2025 release DOI that related_datasets already names as the predecessor",
        "expressing the FAIRSCAPE provenance lineage as was_derived_from/parent_datasets links",
        # Beside the imperative these say the derivation provenance is already
        # in the RO-Crate/FAIRscape package shipped with the release, a file,
        # as the FAIRSCAPE sentence above does; their rating says a
        # machine-readable provenance representation exists in the release
        # (#3808).
        "provenance already packaged with the release",
        "provenance shipped with the release",
        # Pinned as criticisms until review round 4 (#3836) re-asked step 2
        # of every criticism and request before step 3. Each says where the
        # content is, which step 2 asks first, so each is a placement
        # whatever it also objects to:
        # - the two FAIRSCAPE sentences of AI_READI v8 rep2 rating 1 put the
        #   derivation edges in the RO-Crate's sub-crates, a file, which
        #   was_derived_from is to reference; the second also calls the
        #   lineage "the prose lineage", and its rating's issues_detected[7]
        #   and weaknesses[4] say provenance is "distributed across prose
        #   fields". That was_derived_from holds the study's name in prose,
        #   the reason they were criticisms, is a step-3 reason;
        # - "already listed in version_access" says where the four releases
        #   related_datasets lacks are, the form of "already named in
        #   related_datasets" above. Its rating's objection to the one
        #   predecessor related_datasets holds (#3820) is a step-3 reason;
        # - "rather than inferring derivation from filenames" says the
        #   derivation is held as an inference from the archive names, the
        #   form of "rather than inferable from prose" above; its rating says
        #   preprocessing_strategies carries the atlas-from-raw derivation
        #   "Inferred from the paired archive names" and "the linkage lives
        #   in prose and in filename parallelism". Until this round it was
        #   read as saying how a reader infers derivation rather than where
        #   the content is (#3808), which the two pins above contradict.
        "reference its per-sub-crate derivation edges from was_derived_from",
        "reference its sub-crate derivation edges from was_derived_from, converting the prose lineage",
        "extend related_datasets to the full five-release chain already listed in version_access",
        "rather than inferring derivation from filenames",
    ],
    # A criticism: step 3 of the ordered test in the module docstring. The
    # sentence names a value the record holds and asks for it to be
    # different or for more of it, and its own rating objects to that value
    # in that respect (#3808, #3819, #3829). was_derived_from holds the
    # study's name in prose in the AI_READI rating the first comes from, as
    # its own evidence quotes; the next four are about a populated
    # method, institution or confidentiality level, the last of them asking
    # for a different value of confidentiality_level, which its rating says
    # is 'restricted' where the sources give 'HL7:2N' (#3808). In the three
    # after that, publisher holds 'https://fairhub.io/', which each rating
    # criticises as a URL where the organisation name belongs; beside the
    # requests for empty slots, each asks for the name (#3819). The citation
    # holds RRID:SCR_007345, which its rating says identifies PhysioNet and
    # not the dataset, and the sentence asks for the citation to say so;
    # "Keep the RRID in the citation as published", a placement above, keeps
    # the value. The FAIRSCAPE, five-release-chain and filename sentences
    # were criticisms here until review round 4 moved them to placement
    # (#3836): step 2 is asked before step 3. The same round re-asked steps
    # 1 and 2 of every criticism and request; these stayed, because each
    # says where content is to go, not where a slot's content is now:
    # "keeping the study-name prose in notes" (the value was_derived_from
    # holds, moving to notes), "keep the alternative reading in
    # source_caveats" and "keeping the divergent platform and RO-Crate
    # values in the details prose" (alternatives to a populated slot's
    # value, not its content held elsewhere), and "state whether the
    # shipped RO-Crate provenance graphs carry per-modality processing
    # parameters", which asks whether a file holds something, where "the
    # sub-crate derivation edges" says it does.
    #
    # The last nine were pinned as requests until the ordered test was
    # applied to every sentence that reaches it (#3829). In each, beside the
    # slots it asks to fill, the sentence asks for more of a value its rating
    # says is populated and faults in that respect:
    # - ethical_reviews holds the USF IRB and Canadian REB reviews, and the
    #   rating's note on it says "no conflicts-of-interest statement";
    # - preprocessing_strategies names b2aiprep, openSMILE, sparc, ppgs and
    #   Whisper, which the rating says carry no version ("No tool carries a
    #   version number"), and external_resources, which it faults for not
    #   listing the feasibility publication and white paper;
    # - preprocessing_strategies and machine_annotation_tools name sparc,
    #   openSMILE, Praat, Parselmouth, ppgs and Whisper, which "have neither
    #   version nor URL";
    # - source_caveats discloses the 419,614-byte residual, which the rating
    #   calls "stated but unexplained";
    # - keywords holds 7 entries ("Only 7 keywords");
    # - file_collections lists ten archives and conforms_to claims an
    #   RO-Crate provenance graph, and the rating says no listed archive is
    #   stated to carry it;
    # - variables holds four columns ("enumerates only four columns");
    # - the text formats are listed with no encoding, which the rating
    #   records as a warning;
    # - file_collections lists ten collections, and the rating says "no
    #   collection carries a was_generated_by".
    # A criticism is not a miss: it says what a populated slot holds, not
    # that a slot is empty.
    "criticism": [
        "set was_derived_from to the same identifier, keeping the study-name prose in notes",
        "keep the alternative reading in source_caveats rather than in the structured slot",
        "keeping the divergent platform and RO-Crate values in the details prose",
        "rather than asserting a method in the structured slot that the platform metadata contradicts",
        "Keep the caveat but consider a value nearer",
        "Set publisher to the organization name FAIRhub",
        "Populate confidentiality_level ('HL7:2N'), parent_datasets/was_derived_from",
        "Populate data_protection_impacts (truthful status)",
        "Clarify in the citation or a dedicated field",
        "a conflicts-of-interest statement under ethical_reviews",
        "Add tool versions (b2aiprep, openSMILE, sparc, ppgs, Whisper)",
        "Add versions and URLs for sparc, openSMILE, Praat, Parselmouth, ppgs and Whisper",
        "attribute the disclosed 419,614-byte residual",
        "add at least one more keyword",
        "name the archive carrying the RO-Crate descriptor and provenance graph",
        "alongside an expanded variables list covering the principal phenotype columns",
        "State character encoding (presumably UTF-8) on the text formats",
        "give each file_collection a was_generated_by link",
    ],
    # A request: step 4, what reaches it. The imperative names a slot to
    # fill, and nothing beside it says the slot is empty, where its content
    # is, or asks for a change to a value its rating faults. Not counted as
    # a miss: a request presupposes an unfilled slot without stating one,
    # and some are conditional ("if part of larger collection"). Where a
    # request names a populated value, step 3 fails on one of its two
    # parts, and these are the sentences where that was closest:
    # - it asks for the value to be re-expressed in another slot or
    #   structure, which leaves the value as it is: "Mirror the version
    #   lineage into parent_datasets", "Express the conversion and QC chain
    #   as PROV-O activities", "Document FAIRSCAPE provenance graph structure
    #   ... in dedicated provenance field", "Populate download_url with the
    #   FAIRhub access endpoint" (the endpoint is in access_urls), "typed
    #   relationships (e.g., is-part-of Bridge2AI, has-archive Zenodo)"
    #   (Zenodo is in external_resources), the holdout set that splits
    #   describes;
    # - it asks for a change to a release artifact the record points at,
    #   not to a value the record holds: "expose the lineage through the
    #   existing RO-Crate", and "consider embedding the RO-Crate lineage as a
    #   provenance graph", which gives the slots' content as
    #   doi:10.60775/fairhub.2 and the lineage a graph of its own, where
    #   "provenance already packaged with the release" above is the
    #   derivation path the slot is to hold;
    # - its rating's objection is to an empty slot, not to the value it
    #   names: "Add was_derived_from per file collection ... exploiting the
    #   RO-Crate conformance already declared", whose rating credits the
    #   file_collections for binding entities to activities and faults the
    #   empty was_derived_from; "record the Snellen change as an erratum",
    #   whose ratings fault the empty errata, not the known_limitations
    #   entry that holds the change.
    # Review round 4 re-asked steps 1 and 2 of all 40 (#3836). None names an
    # absence, and none says where the content of a slot it asks to fill is
    # now: "the RO-Crate lineage" is to become a graph of its own, as above,
    # not what the parent_datasets/was_derived_from it asks for are to hold.
    "request": [
        "Add explicit deidentification method",
        "Add parent_datasets field linking to Bridge2AI",
        "Add parent_datasets or hierarchical relationship",
        "Add parent_datasets/was_derived_from pointing",
        "Add provenance information (was_derived_from, release_notes)",
        "Add related_datasets/parent_datasets entries",
        "Add related_datasets/parent_datasets with",
        "Add release_notes or was_derived_from for",
        "mirror the version lineage into parent_datasets",
        "Add was_derived_from field for provenance",
        "Add was_derived_from per file collection",
        "Consider adding hierarchical resources or",
        "Consider adding parent_datasets field linking",
        "Document FAIRSCAPE provenance graph structure",
        "Express the conversion and QC chain as PROV-O",
        "Express the feature-from-audio derivation",
        "Express typed related_datasets entries for",
        "Include provenance chain using was_derived_from",
        "Include was_derived_from to document provenance",
        "Link to related datasets: parent_datasets",
        "Mirror doi:10.60775/fairhub.1 and doi:10.60775/fairhub.2",
        "Mirror the fairhub.1/fairhub.2 predecessors into parent_datasets/was_derived_from and "
        "record the Snellen change as an erratum",
        "record the Snellen change as an erratum so provenance slots are machine-readable",
        "record the Snellen visual-acuity change as an erratum",
        "record the Snellen drop as an erratum so lineage and changes",
        "Mirror the predecessor versions into parent_datasets/was_derived_from so lineage",
        "Mirror the predecessors into parent_datasets/was_derived_from",
        "Mirror the two predecessor releases into",
        "Mirror the v2.0.0 predecessor into parent_datasets/was_derived_from",
        "Populate a top-level version field, document",
        "Populate download_url with the FAIRhub access",
        "Populate parent_datasets / was_derived_from",
        "Populate parent_datasets with the 3.0.0 DOI",
        "Populate parent_datasets with the controlled-access",
        "Populate parent_datasets with the prior version DOIs",
        "Populate parent_datasets/was_derived_from for",
        "Populate was_derived_from to link each released",
        "Populate was_derived_from to type the derivation",
        "Populate was_derived_from with the Synapse raw-audio entity and bind",
        "Record the publisher as a URI",
    ],
}


def _pinned(fragment, sentences):
    """The sentences a fragment pins: the one it is, else those holding it."""
    return [s for s in sentences if s == fragment] or [s for s in sentences if fragment in s]


@pytest.mark.corpus
def test_the_absence_vocabulary_recall_measured_on_the_committed_text():
    """The module docstring's #3544 measurement. In the Q19 fields of the
    133 committed ratings, every sentence naming a slot carries an
    `_EMPTINESS` word but two, which say the slot is populated. Outside
    them, in text the vocabulary was not written against, the sentences
    naming a slot with no `_EMPTINESS` word are 155 read by hand: 31
    absences the list misses (the 11 named absences and 18 placements
    above, and the two of `_HAND_READ_NOT_CREDIT`), the other classes of
    `_HAND_READ_NOT_CREDIT`, each pinned by a fragment, and 109 that are
    credit (#3669; two of the 111 first read as credit are placements under
    the ordered test's step 2, #3838); and 122 a leading-verb regex sorts as recommendations,
    read by hand too (#3747): 64 more misses (a named absence and 63
    placements), 18 criticisms and 40 requests, each pinned by a fragment
    in `_RECOMMENDATIONS_READ` to the class the module docstring's ordered
    test gives it (#3829, #3836). 95 of the 277 state an absence the list
    misses.
    The list is main's; this measures it and changes nothing (#3544)."""
    from data_sheets_schema import q19_rationale_lint as lint
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "data/evaluation_llm"],
                            capture_output=True, text=True, check=True).stdout.split("\0")
    documents = []
    for f in listed:
        if f.endswith(".json"):
            try:
                documents.append(json.loads((ROOT / f).read_text(encoding="utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    slot = lint.REPRESENTATION_CONCERNS["empty_slot"]
    ratings = [d for d in documents if isinstance(d, dict) and d.get("rubric") == "rubric20-semantic"]
    assert len(ratings) == 133
    q19 = [s for d in ratings for _, s in lint._sentences(q19_item(d)) if slot.search(s)]
    unmarked = [s for s in q19 if not lint._EMPTINESS.search(s)]
    assert (len(q19), len(unmarked)) == (121, 2)
    assert all("was_derived_from" in s and ("explicit rather than implied" in s or "populated" in s)
               for s in unmarked)

    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for v in value.values():
                yield from strings(v)
        elif isinstance(value, list):
            for v in value:
                yield from strings(v)

    inside = {s for d in ratings for _, s in lint._sentences(q19_item(d))}
    outside = {s.strip() for d in documents for text in strings(d)
               for s in lint._SENTENCE.split(text)
               if s.strip() and slot.search(s) and s.strip() not in inside}
    recommendation = re.compile(
        r"^(?:populate|add|mirror|record|express|link|use|include|consider|document|fill|emit"
        r"|expose|publish|wire|instantiate|promote|set|move|provide|state|replace|encode|model"
        r"|capture|declare|convert|represent|reference|attach|list|map|split|clarify|name|keep"
        r"|resolve|attribute)\b", re.I)
    marked = [s for s in outside if lint._EMPTINESS.search(s)]
    rest = [s for s in outside if not lint._EMPTINESS.search(s)]
    recommendations = [s for s in rest if recommendation.match(s)]
    assert (len(outside), len(marked), len(recommendations)) == (1046, 769, 122)
    read = [s for s in rest if not recommendation.match(s)]
    assert len(read) == 155
    # The regex sorts by the first word only; the 122 are read by hand like
    # the 155, and every one is pinned by one fragment to one class (#3747).
    sorted_ = {}
    for kind, fragments in _RECOMMENDATIONS_READ.items():
        for fragment in fragments:
            hits = _pinned(fragment, recommendations)
            assert len(hits) == 1, (kind, fragment)
            assert hits[0] not in sorted_, (kind, fragment)
            sorted_[hits[0]] = kind
    assert set(sorted_) == set(recommendations)
    assert Counter(sorted_.values()) == {"named_absence": 1, "placement": 63, "criticism": 18,
                                         "request": 40}
    # The 64 misses are misses: in a Q19 note the gate reads none of them
    # as an empty-slot reason, as on main.
    for sentence, kind in sorted_.items():
        if kind in ("named_absence", "placement"):
            assert not [r for r in lint_q19(item(note=f"Held at 4. {sentence}")).reasons
                        if r.concern == "empty_slot"], sentence
    classified, misses = [], []
    for fragment in _UNRECOGNISED_NAMED_ABSENCES:
        # The second "remain the gaps" sentence is the whole of one.
        hits = [s for s in read if (s == fragment if fragment.startswith("doi,") else fragment in s)]
        assert len(hits) == 1, fragment
        classified += hits
        misses += hits
    for fragment in _UNRECOGNISED_PLACEMENTS:
        hits = [s for s in read if fragment in s]
        assert len(hits) == 1, fragment
        classified += hits
        misses += hits
    for kind, fragments in _HAND_READ_NOT_CREDIT.items():
        for fragment in fragments:
            # A bare name is the whole sentence; the others are part of one.
            hits = [s for s in read if (s == fragment if kind == "bare_name" else fragment in s)]
            assert len(hits) == 1, (kind, fragment)
            classified += hits
            if kind == "unrecognised_absence":
                misses += hits
    assert len(set(classified)) == len(classified) == 46
    assert len(set(misses)) == len(misses) == 31
    # 109 left are credit: 155 less the 11, 18 and 17 pinned above (#3838).
    assert len(read) - len(classified) == 109
    # The classes are the module docstring's counts, so a pin moved from one
    # class to another fails here, as a recommendation's does above.
    assert (len(_UNRECOGNISED_NAMED_ABSENCES), len(_UNRECOGNISED_PLACEMENTS)) == (11, 18)
    assert {kind: len(fragments) for kind, fragments in _HAND_READ_NOT_CREDIT.items()} == {
        "unrecognised_absence": 2, "count": 2, "criticism": 5, "qualification": 4,
        "bare_name": 2, "criterion": 2}
    # The 31 misses are misses: the gate reads none of them — the named
    # absences, the placements or the unrecognised absences — as an
    # empty-slot reason, as it reads none of the 64 above; it reads
    # `_EMPTINESS` words only, as on main (#3872).
    for sentence in misses:
        assert not [r for r in lint_q19(item(note=f"Held at 4. {sentence}")).reasons
                    if r.concern == "empty_slot"], sentence
    # The words these absences are named in: without an `_EMPTINESS` word
    # they occur in 13 slot sentences outside the Q19 fields, the 11 above,
    # a recommendation and the completeness gap of `_HAND_READ_NOT_CREDIT`.
    bare = re.compile(r"\b(?:absences|absentees?|gaps?|silent)\b", re.I)
    worded = [s for s in rest if bare.search(s)]
    named = classified[:len(_UNRECOGNISED_NAMED_ABSENCES)]
    assert len(worded) == 13 and set(named) <= set(worded)
    left = sorted(set(worded) - set(named))
    assert [s[:24] for s in left] == ["Fill the structural gaps", "parent_datasets logged a"]
