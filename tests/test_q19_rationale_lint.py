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
from data_sheets_schema.q19_rationale_lint import _credit_clauses

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
    """Documented in the module docstring; this keeps the docstring honest.
    CBORG CM4AI v8 rep2 moved from 15 to 9 (#3128): its identifier and
    fixity co-reasons were credit before "but the top band requires …"."""
    grades = Counter((s.flagged, linted[key].verdict) for key, s in statuses.items()
                     if s.q19_score < 5)
    cm4ai = linted[("cborg", "CM4AI_v8_rep2_r20_rating1")]
    assert (statuses[("cborg", "CM4AI_v8_rep2_r20_rating1")].flagged, cm4ai.verdict,
            cm4ai.concerns(SUBSTANTIVE)) == (True, REPRESENTATION_ONLY, [])
    assert grades == Counter({(True, REPRESENTATION_ONLY): 10,
                              (True, REPRESENTATION_AND_SUBSTANTIVE): 14,
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
])
def test_an_outer_list_item_is_not_guessed_without_parallel_structure(note):
    """#3260: no flag on a disclaimed list, and no guess where the words do
    not say which list the fragment belongs to."""
    result = lint_q19(item(note=note))
    assert result.concerns(REPRESENTATION) == [], note


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
    # "whereas complete" turns back to credit and names no gap, so it is
    # not read with the reason (#3128, #3432).
    assert withholding_sentences(rating) == [("score_label", "Prose accepted short of a graph")]


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


# -- credit read as a reason (#2982, #3128, #3194) ----------------------------

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


def test_credit_before_a_contrast_in_a_sentence_that_says_why_is_not_read():
    """#3128: the committed CBORG CM4AI v8 rep2 form. A sentence carrying a
    cue was read whole, so the credit before its "but" gave identifier and
    fixity co-reasons."""
    result = lint_q19(item(note=(
        "Above the version-history band on several counts - named sources with persistent "
        "identifiers and file-level fixity - but the top band requires the links to be "
        "represented as a graph.")))
    assert (result.basis, result.verdict) == (STATED, REPRESENTATION_ONLY)
    assert (result.concerns(REPRESENTATION), result.concerns(SUBSTANTIVE)) == (["graph_form"], [])


@pytest.mark.parametrize("note", [
    # #3128's own example, with a vocabulary word in the credit.
    "Checksums are recorded (md5 on every archive), and it is held at 4 because no PROV "
    "graph is given.",
    "Checksums are recorded on every archive, but it falls short of 5 because no PROV graph "
    "is given.",
])
def test_credit_before_a_cue_that_names_its_own_reason_is_not_read(note):
    result = lint_q19(item(note=note))
    assert (result.basis, result.verdict, result.concerns(SUBSTANTIVE)) == (
        STATED, REPRESENTATION_ONLY, []), note


@pytest.mark.parametrize("note, concerns", [
    # A cue that names nothing points back at the words before it.
    ("Checksums are missing on every archive, which keeps it from 5.", ["integrity"]),
    ("The PROV graph is referenced, not given, which keeps it from 5.", ["graph_form"]),
    # Credit after the cue is read (disclosed: a clause rule there drops
    # real reasons on the committed ratings).
    ("Held at 4 because no PROV graph is given, and checksums are recorded.",
     ["graph_form", "integrity"]),
])
def test_what_a_cue_sentence_still_reads(note, concerns):
    result = lint_q19(item(note=note))
    assert sorted(result.concerns(REPRESENTATION) + result.concerns(SUBSTANTIVE)) == concerns, note


def test_where_nothing_says_why_a_credit_clause_sharing_a_part_with_a_gap_is_not_read():
    """#3128: the committed CHORUS 2026-08-28b API rep1 form. A gap part with
    no contrast word was read whole, so its credit clause ("missing data is
    documented") gave a missing-data reason."""
    result = lint_q19(item(note=(
        "Relationships are recoverable from prose, giving a partial lineage, and missing data "
        "is documented per modality.")))
    assert result.basis == UNSTATED
    assert "missing_data" not in result.concerns(SUBSTANTIVE)
    assert result.concerns(SUBSTANTIVE) == ["lineage_content"]
    aside = lint_q19(item(note="Checksums are recorded (md5 on every archive), and no PROV graph."))
    assert (aside.verdict, aside.concerns(SUBSTANTIVE)) == (REPRESENTATION_ONLY, [])


@pytest.mark.parametrize("note, concerns", [
    # A verbless clause may be an item of the list whose gap a neighbour states.
    ("No version history, errata or structured derivation graph.",
     ["empty_slot", "graph_form", "version_history"]),
    # Credit sharing a clause with a gap is read (disclosed).
    ("Checksums are recorded on every archive and was_derived_from is empty.",
     ["empty_slot", "integrity"]),
])
def test_where_nothing_says_why_what_a_gap_part_still_reads(note, concerns):
    result = lint_q19(item(note=note))
    assert result.basis == UNSTATED
    assert sorted(result.concerns(REPRESENTATION) + result.concerns(SUBSTANTIVE)) == concerns, note


@pytest.mark.parametrize("label, read", [
    ("No PROV graph, but excellent version history", ["graph_form"]),
    ("No PROV graph but excellent version history", ["graph_form"]),
    # "whereas" and "however" turn back to credit with or without a comma
    # (#3432): the label parts cut only before "but".
    ("No PROV graph, whereas excellent version history", ["graph_form"]),
    ("No PROV graph whereas excellent version history", ["graph_form"]),
    ("No PROV graph however excellent version history", ["graph_form"]),
    # A later contrast that names a gap is part of the reason.
    ("No PROV graph, but no errata either", ["graph_form", "version_history"]),
    ("Short of a full graph, but errata not recorded", ["graph_form", "version_history"]),
    ("No PROV graph whereas errata not recorded", ["graph_form", "version_history"]),
    # So is one that carries a withholding cue and names no gap (#3433).
    ("No PROV graph, but falls short on errata too", ["graph_form", "version_history"]),
    ("No PROV graph, but held at 4 for errata", ["graph_form", "version_history"]),
])
def test_label_credit_after_its_reason_turning_back_with_a_contrast_is_not_read(label, read):
    """#3128: a label's reason ran from its first cue to its end, so credit
    after it was read."""
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert sorted(result.concerns(REPRESENTATION) + result.concerns(SUBSTANTIVE)) == read, label


@pytest.mark.parametrize("note, reasons", [
    # #3128's CBORG CM4AI v8 rep2 form, with a sentence after it that
    # points back and names no reason of its own.
    ("Above the band - persistent identifiers and file-level fixity - but the top band "
     "requires the links to be represented as a graph. One point is withheld for that.",
     ["graph_form"]),
    ("Short of 5. Checksums are recorded on every archive, but it falls short of 5 because "
     "no PROV graph is given.", ["graph_form"]),
])
def test_a_neighbour_that_says_why_keeps_its_credit_apart(note, reasons):
    """#3431: a cue sentence naming no reason reads the sentences either
    side of it. One that itself says why was read whole as well as by its
    parts, so its credit came back and its reason was counted twice."""
    result = lint_q19(item(note=note))
    assert result.basis == STATED
    assert [r.concern for r in result.reasons] == reasons, note


def test_a_clause_carrying_a_withholding_cue_is_never_credit():
    """#3434 (a): `_credit_clauses` sets apart finite clauses naming no
    gap, but not one carrying a cue. The lint never asks it about such a
    clause today (a cue in a clause that is read always says why, so it
    starts the cue clause `_credit_before_cue` stops at, and where nothing
    says why no read clause carries one), so the rule is pinned on the
    function itself."""
    sentence = "It is held at 4 because errata are thin, and checksums are recorded."
    assert _credit_clauses(sentence, 0, len(sentence)) == frozenset({(41, len(sentence))})


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


@pytest.mark.parametrize("note", [
    "Held at 4 because the missing-data documentation sits beside was_derived_from.",
    "Held at 4 because missing data documentation sits beside was_derived_from.",
])
def test_missing_data_documentation_does_not_say_a_slot_is_empty(note):
    """#3434 (c), #2982: "missing-data documentation" names content, so it
    does not make a slot named in the same sentence an empty-slot reason."""
    result = lint_q19(item(note=note))
    assert (result.basis, result.concerns(REPRESENTATION)) == (STATED, []), note


@pytest.mark.parametrize("label", [
    "Typed PROV graph falls short on errata",
    "Held at 4 because the typed PROV graph lacks errata",
])
def test_a_label_cue_clause_naming_both_kinds_is_not_read(label):
    """#3194: the one-kind rule covers a label clause whose withholding cue
    stands inside it or opens it; its words do not say which concern is
    credit. The committed ratings have no such label clause."""
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert (result.verdict, result.reasons) == (REASON_NOT_DETERMINED, ()), label


@pytest.mark.parametrize("label, concern", [
    ("Held at 4 because was_derived_from is empty", "empty_slot"),
    ("Typed PROV graph falls short of a machine-readable form", "graph_form"),
])
def test_a_label_cue_clause_naming_one_kind_is_read(label, concern):
    result = lint_q19(item(label=label, note=_NEUTRAL))
    assert result.flagged and concern in result.concerns(REPRESENTATION), label


@pytest.mark.parametrize("note, verdict, reasons", [
    ("Derivation is described across four fields, but this keeps it from 5. "
     "Version history is excellent.", REPRESENTATION_ONLY,
     [("scattered", "Derivation is described across four fields")]),
    ("Lineage is recorded as human-readable prose, but it is held at 4 for that reason.",
     REPRESENTATION_ONLY, [("machine_form", "Lineage is recorded as human-readable prose")]),
    ("The provenance is a human-readable narrative, however, which keeps it from 5.",
     REPRESENTATION_ONLY, [("machine_form", "The provenance is a human-readable narrative")]),
    ("Errata are recorded in the changelog, but that falls short of 5.",
     SUBSTANTIVE_ONLY, [("version_history", "Errata are recorded in the changelog")]),
    # The cue's part names a gap word ("not") and still nothing of its own.
    ("The provenance is a human-readable narrative, but that is why it does not reach 5.",
     REPRESENTATION_ONLY, [("machine_form", "The provenance is a human-readable narrative")]),
])
def test_a_cue_naming_nothing_after_a_contrast_points_back_across_it(note, verdict, reasons):
    """#3464: a cue that names nothing points back at the words before it,
    which are read, even across "but", "whereas" or "however". Cut at the
    contrast, the reason was dropped and the sentence named none, so its
    neighbour was read in its place: credit ("Version history is
    excellent.") became the stated reason and the verdict flipped."""
    result = lint_q19(item(note=note))
    assert result.basis == STATED
    assert (result.verdict, [(r.concern, r.clause) for r in result.reasons]) == (
        verdict, reasons), note


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
