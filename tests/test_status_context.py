"""The status-context diagnostic (#2917): synthetic positive controls, each
paired with a negative control that keeps the qualifier, and the guarantee
that the validators it reads beside stay exactly as they were."""
import copy
import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import chunking, receipts as rc, source_review, status_context as sc
from data_sheets_schema.cli import cli

ROOT = Path(__file__).resolve().parents[1]


def _md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _bundle(*docs):
    """A study-shaped bundle: a preamble chunk, then one chunk per document
    (c002, c003, ...), as `chunking.chunk_text` cuts it."""
    text = "=" * 80 + "\nCONCATENATED DOCUMENT\n" + "=" * 80 + "\n\n"
    for i, body in enumerate(docs):
        text += (f"FILE: d{i}.txt\nPATH: x/d{i}.txt\nSIZE: 1 bytes\n" + "-" * 80 + "\n"
                 + body + "\n\n" + "=" * 80 + "\n\n")
    return text, {"bundle_md5": _md5(text), "chunks": chunking.chunk_text(text)}


def _receipt(text, pairs, cid="c002"):
    return {"bundle_md5": _md5(text), "chunks": [
        {"id": cid, "status": "extracted", "extracted": [{"slot": s, "snippet": q} for s, q in pairs]}]}


def _run(doc, pairs, record):
    text, manifest = _bundle(doc)
    return sc.receipt_context(_receipt(text, pairs), manifest, text, record)


def _line(text, needle):
    return text[:text.index(needle)].count("\n") + 1


def _rules(out, bucket="flags"):
    return [(f["rule"], f["slot"], f["class"]) for f in out[bucket]]


# ------------------------------------------------------------------ registry
@pytest.mark.parametrize("phrase,cls", [
    ("the project will acquire data", "planned"), ("a planned release", "planned"),
    ("the team plans to share", "planned"), ("they intend to publish", "planned"),
    ("the proposed cohort", "planned"), ("data to be released", "planned"),
    ("Anticipated Final Dataset", "prospective"), ("is expected to grow", "prospective"),
    ("in future releases", "prospective"), ("The goal is to build", "prospective"),
    ("the program aims to train", "prospective"), ("an upcoming release", "prospective"),
    ("curation is in progress", "in_progress"), ("de-identification in process", "in_progress"),
    ("ongoing enrolment", "in_progress"), ("collection is underway", "in_progress"),
    ("tools under development", "in_progress"), ("records are being harmonized", "in_progress"),
])
def test_registered_markers_carry_their_class(phrase, cls):
    assert cls in sc.classes(phrase)


#: One example per EXCLUDED_TERMS entry: the excluded sense, in a phrase.
EXCLUDED_EXAMPLES = {
    "target": "the target population", "intended": "intended uses of the data",
    "prospective": "a prospective cohort", "shall": "the licensee shall not redistribute",
    "expected": "the expected value", "plan": "a data management plan",
    "to be used": "the data are not to be used for commercial purposes",
}


@pytest.mark.parametrize("phrase", [*EXCLUDED_EXAMPLES.values(), "described in the process documentation"])
def test_excluded_terms_carry_no_status(phrase):
    assert sc.classes(phrase) == {}


def test_the_curator_list_names_every_exclusion_the_detector_makes():
    # EXCLUDED_TERMS is what a curator signs off (#2917, owner decision 3),
    # so an exclusion carved out of a registered pattern is listed there too
    # (#3091): every tested exclusion is a listed term, and every listed
    # term has a tested example.
    assert set(EXCLUDED_EXAMPLES) == set(sc.EXCLUDED_TERMS)
    for term, phrase in EXCLUDED_EXAMPLES.items():
        assert term in phrase and sc.classes(phrase) == {}, term


def test_registry_is_one_versioned_dataset_neutral_vocabulary():
    assert set(sc.STATUS_MARKERS) == set(sc.EXPRESSED_BY) == {"planned", "prospective", "in_progress"}
    assert set(sc.DECLARED_STATUS.values()) <= set(sc.STATUS_MARKERS)
    assert set(sc.PLANNED_EVIDENCE_CLASSES) <= set(sc.STATUS_MARKERS)
    assert sc.VOCABULARY["version"] == 1 and re.fullmatch(r"[0-9a-f]{64}", sc.VOCABULARY["sha256"])
    # Both rules record the same instrument and vocabulary.
    text, manifest = _bundle("Nothing here.")
    r1 = sc.receipt_context(_receipt(text, []), manifest, text, {})
    r2 = sc.review_status_expression({"artifact": "original_full", "sha256": "0", "values": []})
    assert r1["instrument"] == r2["instrument"] == sc.INSTRUMENT
    assert r1["vocabulary"] == r2["vocabulary"] == sc.VOCABULARY
    assert r1["gating"] is r2["gating"] is False and r1["assurance"] == r2["assurance"] == sc.ASSURANCE
    rules = json.dumps([sc.STATUS_MARKERS, sc.COUNTER_MARKERS, sorted(sc.LABEL_LEAVES)]).casefold()
    for token in ("chorus", "readi", "voice", "cm4ai", "bridge2ai", "omop", "dicom", "physionet"):
        assert token not in rules


# ------------------------------------------------------- normalised offsets
def test_offsets_reproduce_the_validators_normalisation_and_point_back_to_raw_text():
    text = 'The ﬁle \\n was “quoted”,  Straße — Café and \\"escaped\\" A) item'
    norm, offs = sc.normalised_offsets(text)
    assert norm == rc.normalise(text) and len(offs) == len(norm)
    assert offs == sorted(offs)
    for needle in ("file", "strasse", "café and", "escaped", "a item"):
        i = norm.index(needle)
        raw = text[offs[i]:offs[i + len(needle) - 1] + 1]
        assert rc.normalise(raw) == needle, (needle, raw)


def test_a_verified_snippet_is_located_at_its_exact_raw_span():
    text, manifest = _bundle(ENUMERATION + "\nIt will ship the Final  Report\n(“v2”) soon.")
    view = sc.BundleView(text, manifest)
    [[(a, b)]] = view.locate("c002", D_SNIPPET)
    assert text[a:b] == D_SNIPPET
    # A multi-part snippet is located part by part, across a line break and
    # folded punctuation and spacing.
    [[(a1, b1), (a2, b2)]] = view.locate("c002", "ship the final report...v2")
    assert (text[a1:b1], text[a2:b2]) == ("ship the Final  Report", "v2")
    assert view.chunk_text("c002") == chunking.chunk_texts(text, manifest["chunks"])[1]


def test_offsets_refuse_a_fold_the_replay_cannot_reproduce():
    # NFKC composes conjoining jamo across what the replay keeps apart.
    assert sc.normalised_offsets("가 data") is None


# ------------------------------------------------------------------ rule 1
ENUMERATION = ("Drawing on many disciplines, this project will A) establish a legal framework; "
               "B) perform community focus groups; C) ensure contextual factors; D) develop capabilities "
               "to acquire, standardize and label data such as waveforms; E) acquire data and transform "
               "data using approaches that limit re-identification; and F) cultivate expertise. "
               "To accomplish this, the team collaborates widely.")
D_SNIPPET = "develop capabilities to acquire, standardize and label data"
D_SLOT = "preprocessing_strategies[0].preprocessing_details"


def test_modal_governing_an_enumeration_is_lost_from_a_snippet_cut_from_item_d():
    record = {"preprocessing_strategies": [{"preprocessing_details": "Data are standardized and labelled."}]}
    out = _run(ENUMERATION, [(D_SLOT, D_SNIPPET)], record)
    [flag] = out["flags"]
    text, _m = _bundle(ENUMERATION)
    assert (flag["rule"], flag["slot"], flag["class"], flag["marker"], flag["via"]) == (
        "governor_outside_snippet", D_SLOT, "planned", "will", "enumeration")
    assert flag["source_line"] == flag["snippet_line"] == _line(text, "Drawing on")
    assert out["counts"]["flags"]["governor_outside_snippet"] == {"value": 1, "label": 0}


def test_negative_control_the_value_keeps_the_modal():
    record = {"preprocessing_strategies": [{"preprocessing_details": "The project will standardize and label data."}]}
    assert _run(ENUMERATION, [(D_SLOT, D_SNIPPET)], record)["flags"] == []
    # A prospective marker expresses the same not-yet status.
    record["preprocessing_strategies"][0]["preprocessing_details"] = "Anticipated standardization of the data."
    assert _run(ENUMERATION, [(D_SLOT, D_SNIPPET)], record)["flags"] == []


def test_a_sibling_items_modal_does_not_govern_another_item():
    doc = ("The consortium A) has built a legal framework; B) will run focus groups next year; "
           "C) develops capabilities to standardize data to a common model; D) will curate labels later.")
    record = {"x": "Data are standardized to a common model."}
    assert _run(doc, [("x", "develops capabilities to standardize data to a common model")], record)["flags"] == []
    # The same item under a governing lead-in is flagged.
    governed = doc.replace("The consortium A) has built", "The consortium will A) build")
    assert _rules(_run(governed, [("x", "develops capabilities to standardize data to a common model")],
                       record)) == [("governor_outside_snippet", "x", "planned")]


def test_an_enumeration_whose_items_end_in_periods_is_followed_back_to_its_lead_in():
    doc = ("This project will A) establish a framework for sharing. B) standardize data to a common "
           "model. C) release the data to researchers.")
    record = {"x": "Data are standardized to a common model."}
    [flag] = _run(doc, [("x", "standardize data to a common model")], record)["flags"]
    assert (flag["marker"], flag["via"]) == ("will", "enumeration")


def test_bulleted_items_under_a_colon_lead_in():
    doc = "The consortium will:\n- acquire records from each site\n- standardize data to a common model\n"
    record = {"x": "Data are standardized to a common model."}
    [flag] = _run(doc, [("x", "standardize data to a common model")], record)["flags"]
    assert (flag["marker"], flag["via"]) == ("will", "enumeration")
    unmarked = doc.replace("The consortium will:", "The consortium has:")
    assert _run(unmarked, [("x", "standardize data to a common model")], record)["flags"] == []


PANEL = ("Snapshot of the dataset\nAnticipated Final Dataset\n100,000\nPatient admissions\n9\n"
         "Different data modalities\n14\nData contributing hospitals\nCurrent Released Dataset\n"
         "50,000\nPatient admissions from intensive care\nProject Components")
PANEL_PAIRS = [("data_collectors[0].collector_details", "14\nData contributing hospitals"),
               ("instances[0].counts", "50,000...Patient admissions from intensive care")]


def test_a_status_heading_above_a_numeric_panel_is_found_past_the_count_labels():
    record = {"data_collectors": [{"collector_details": "Fourteen hospitals contribute data."}],
              "instances": [{"counts": "50,000 admissions"}]}
    out = _run(PANEL, PANEL_PAIRS, record)
    text, _m = _bundle(PANEL)
    [flag] = out["flags"]
    assert (flag["slot"], flag["class"], flag["marker"], flag["via"], flag["governor"]) == (
        "data_collectors[0].collector_details", "prospective", "anticipated", "heading", "Anticipated Final Dataset")
    assert flag["source_line"] == _line(text, "Anticipated Final Dataset")
    # The nearest preceding short line is a count label, not the heading.
    assert text.split("\n")[flag["snippet_line"] - 2] == "Different data modalities"
    # The released figures sit under the counter-heading, which closes the scope.
    assert not [f for f in out["flags"] if f["slot"] == "instances[0].counts"]


def test_negative_control_the_panel_value_keeps_the_heading_status():
    record = {"data_collectors": [{"collector_details": "An anticipated fourteen hospitals will contribute."}],
              "instances": [{"counts": "50,000 admissions"}]}
    assert _run(PANEL, PANEL_PAIRS, record)["flags"] == []


def test_without_the_counter_heading_the_anticipated_scope_reaches_the_released_figures():
    record = {"data_collectors": [{"collector_details": "Fourteen hospitals contribute data."}],
              "instances": [{"counts": "50,000 admissions"}]}
    open_panel = PANEL.replace("Current Released Dataset\n", "")
    slots = {f["slot"] for f in _run(open_panel, PANEL_PAIRS, record)["flags"]}
    assert slots == {"data_collectors[0].collector_details", "instances[0].counts"}


@pytest.mark.parametrize("snippet", [
    "Current Released Dataset\n50,000",
    "Current Released Dataset",
    "Current Released Dataset\n50,000\nPatient admissions from intensive care",
    "Current Released Dataset...50,000...Patient admissions from intensive care",
    "Released Dataset\n50,000",
])
def test_a_snippet_that_quotes_the_counter_heading_is_under_it(snippet):
    # #3089: the heading scan read only the lines above a part's own line,
    # so a part starting on "Current Released Dataset" was governed by the
    # "Anticipated" heading above it — and `status: released`, receipted by
    # that heading alone, was flagged as having lost "anticipated".
    record = {"instances": [{"counts": "50,000 admissions"}], "status": "released"}
    out = _run(PANEL, [("instances[0].counts", snippet), ("status", snippet)], record)
    assert out["counts"]["located"] == 2 and out["flags"] == []


def test_a_part_that_starts_under_the_status_heading_stays_governed_past_a_counter_heading():
    # The counter-heading closes the scope for the text below it, not for
    # the quoted figures above it, which the status heading governs.
    record = {"instances": [{"counts": "14 hospitals and 50,000 admissions"}]}
    spanning = "14\nData contributing hospitals\nCurrent Released Dataset\n50,000"
    [flag] = _run(PANEL, [("instances[0].counts", spanning)], record)["flags"]
    assert (flag["rule"], flag["via"], flag["governor"]) == (
        "governor_outside_snippet", "heading", "Anticipated Final Dataset")


def test_evidence_quoting_the_counter_heading_is_not_planned_evidence():
    text, manifest = _bundle(PANEL)
    view = sc.BundleView(text, manifest)
    released = _review(("/instances/0/counts", [
        _claim("50,000 admissions", "fact", quote="Current Released Dataset\n50,000")]))
    assert sc.review_status_expression(released, view=view)["flags"] == []


@pytest.mark.parametrize("gap,governed", [
    ("", True),
    ("\n", True),                                                      # one blank line: the same block
    ("9\nDifferent data modalities\n", True),                          # count labels are passed over
    ("\n\n", False),                                                   # two blank lines end the block
    ("-" * 20 + "\n", False),                                          # a document separator ends it
    ("The consortium publishes a summary for every site.\n", False),   # a prose line ends it
    ("Partner hospitals contribute waveform telemetry, clinical notes and imaging to the shared archive "
     "under the data use agreement that every institution in the network signed in its first year\n",
     False),                                                           # so does a paragraph-length line
])
def test_what_ends_a_status_headings_block(gap, governed):
    # #3092: each end-of-block rule the docstrings document, against the
    # same heading and figures with the gap between them varied.
    doc = "Anticipated Final Dataset\n" + gap + "14\nData contributing hospitals"
    out = _run(doc, [("x", "14\nData contributing hospitals")], {"x": "Fourteen hospitals contribute data."})
    assert [(f["via"], f["governor"]) for f in out["flags"]] == (
        [("heading", "Anticipated Final Dataset")] if governed else [])


def test_a_counter_word_in_a_sentence_is_not_a_counter_heading():
    # Only a heading or lead-in closes a scope: "the current plan" is still
    # the anticipated one.
    doc = "Anticipated Final Dataset\nThe current plan covers 14 hospitals across the network."
    [flag] = _run(doc, [("x", "covers 14 hospitals across the network")], {"x": "Fourteen hospitals."})["flags"]
    assert (flag["via"], flag["governor"]) == ("heading", "Anticipated Final Dataset")


@pytest.mark.parametrize("doc,snippet,governed", [
    # A listed abbreviation and a single-letter initial do not end a
    # sentence, so the modal before them governs the words after them.
    ("The study will enrol approx. 500 adults from partner sites.", "500 adults from partner sites", True),
    ("Harmonisation will be overseen by J. Rivera and the imaging core.", "Rivera and the imaging core", True),
    # A full stop after any other word does.
    ("The study will expand. 500 adults joined from partner sites.", "500 adults joined from partner sites", False),
])
def test_an_abbreviation_or_an_initial_does_not_end_the_sentence(doc, snippet, governed):
    out = _run(doc, [("x", snippet)], {"x": "Partner sites contribute adults."})
    assert [(f["marker"], f["via"]) for f in out["flags"]] == ([("will", "sentence")] if governed else [])


def test_a_numbered_item_is_read_as_an_item_not_cut_at_its_number():
    # A one- or two-digit number at a line start is a list label, not a
    # sentence end, so a numbered item is followed back to its lead-in.
    doc = "The consortium will:\n1. acquire records from each site\n2. standardize data to a common model\n"
    [flag] = _run(doc, [("x", "standardize data to a common model")], {"x": "Data are standardized."})["flags"]
    assert (flag["marker"], flag["via"]) == ("will", "enumeration")


@pytest.mark.parametrize("gap,governed", [
    ("\n", True),                          # one blank line is passed over on the way back to the lead-in
    ("\n\n", False),                       # a second blank line ends the walk
    ("\nROLE: what will change\n", False),  # so does a document separator, marker and all
])
def test_what_ends_the_walk_back_from_an_item_to_its_lead_in(gap, governed):
    doc = "The consortium will:" + gap + "\n- acquire records\n- standardize data to a common model"
    out = _run(doc, [("x", "standardize data to a common model")], {"x": "Data are standardized."})
    assert [(f["marker"], f["via"]) for f in out["flags"]] == ([("will", "enumeration")] if governed else [])


LIST_AFTER = "\n- Records were acquired from each site\n- Data were standardized to a common model"


@pytest.mark.parametrize("before,governed", [
    # #3167: the walk back from an item reaches the unit before the list;
    # a finished sentence there is the end of the previous paragraph, not
    # the list's governing clause ...
    ("The consortium will publish a paper next year.", False),
    ("The consortium will publish a paper next year.\n", False),       # a blank line between
    ("Is the archive expected to grow?", False),
    # ... unless it announces the list,
    ("The study will collect the following data.", True),
    ("The data will be prepared as follows.", True),
    # and an open clause governs: a colon, no terminator, or a full stop
    # that is an abbreviation and so does not end the sentence.
    ("The consortium will:", True),
    ("Over the next two years the consortium will", True),
    ("The consortium will enrol approx.", True),
])
def test_a_finished_sentence_before_a_list_governs_it_only_when_it_announces_it(before, governed):
    out = _run(before + LIST_AFTER, [("x", "Data were standardized to a common model")],
               {"x": "Data are standardized to a common model."})
    assert out["counts"]["located"] == 1
    assert [f["via"] for f in out["flags"]] == (["enumeration"] if governed else [])


def test_a_numbered_section_heading_is_not_governed_by_the_previous_sections_last_sentence():
    # #3167's committed shape: "11. ECONOMIC BURDEN ..." after section 10's
    # last sentence, which carries "will" and "future".
    doc = ("The data set will be publicly available to researchers in the future.\n"
           "11. ECONOMIC BURDEN TO PARTICIPANTS\nParticipants bear no costs for the study visits.")
    out = _run(doc, [("x", "ECONOMIC BURDEN TO PARTICIPANTS")], {"x": "Economic burden to participants"})
    assert out["counts"]["located"] == 1 and out["flags"] == []
    # An inline enumeration after a finished sentence is read the same way.
    inline = "The team will expand. A) collect records; B) standardize data to a common model."
    assert _run(inline, [("x", "standardize data to a common model")], {"x": "Data are standardized."})["flags"] == []


def test_a_single_parenthesised_number_is_not_an_enumeration():
    # An inline enumeration needs two consecutive labels: "(see table 2)"
    # is a reference, so the sentence, not an item, is the context.
    doc = "Enrolment will grow (see table 2) and records are standardized to a common model."
    [flag] = _run(doc, [("x", "records are standardized to a common model")], {"x": "Records are standardized."})["flags"]
    assert (flag["marker"], flag["via"]) == ("will", "sentence")


@pytest.mark.parametrize("doc,snippet,marker", [
    # A sentence wrapped onto a lower-case line is read whole, before the
    # snippet and after it.
    ("Imaging and waveform data will\nbe released to approved researchers.",
     "be released to approved researchers", "will"),
    ("Standardized imaging and waveform data are\nexpected to be available in 2027.",
     "Standardized imaging and waveform data", "expected to"),
])
def test_a_sentence_wrapped_across_lines_is_read_whole(doc, snippet, marker):
    [flag] = _run(doc, [("x", snippet)], {"x": "Standardized data are available to researchers."})["flags"]
    assert (flag["marker"], flag["via"]) == (marker, "sentence")


@pytest.mark.parametrize("labels,governed", [(29, True), (30, False)])
def test_a_status_heading_governs_only_within_the_heading_window(labels, governed):
    # HEADING_WINDOW (30) non-blank lines scanned above a part end the block.
    doc = ("Anticipated Final Dataset\n" + "\n".join(f"Site {i}" for i in range(labels))
           + "\n14\nData contributing hospitals")
    out = _run(doc, [("x", "14\nData contributing hospitals")], {"x": "Fourteen hospitals contribute data."})
    assert [f["via"] for f in out["flags"]] == (["heading"] if governed else [])


def test_a_one_word_colon_lead_in_governs_where_a_one_word_line_does_not():
    # The two-word minimum is for heading-like lines (a flattened table's
    # "Planned" cell); a lead-in's colon says it governs what follows.
    doc = "Planned:\n\nWorkshops on the common data model"
    [flag] = _run(doc, [("x", "Workshops on the common data model")], {"x": "Workshops on the common data model."})["flags"]
    assert (flag["marker"], flag["via"], flag["governor"]) == ("planned", "lead-in", "Planned:")


def test_a_one_word_status_line_is_a_table_cell_not_a_heading():
    doc = "Data type\n\nControlled\n\nPlanned\n\nWaveform telemetry\n(bedside monitors)"
    record = {"x": "Waveform telemetry from bedside monitors."}
    assert _run(doc, [("x", "Waveform telemetry\n(bedside monitors)")], record)["flags"] == []
    two_words = doc.replace("\nPlanned\n", "\nPlanned Collection\n")
    assert _rules(_run(two_words, [("x", "Waveform telemetry\n(bedside monitors)")], record)) == [
        ("governor_outside_snippet", "x", "planned")]


TABLE_LAYOUTS = {
    # A flattened two-column status table under a status heading, in three
    # row orders: the item-first rows, the same rows swapped, and a
    # status-first layout. {cell} is the first row's status cell.
    "item first": "Planned Data Collection\nModality\nStatus\nWaveform telemetry\n{cell}\nImaging studies\nPending",
    "rows swapped": "Planned Data Collection\nModality\nStatus\nImaging studies\nPending\nWaveform telemetry\n{cell}",
    "status first": "Planned Data Collection\nStatus\nModality\n{cell}\nWaveform telemetry\nPending\nImaging studies",
}
TABLE_PAIRS = [("a", "Waveform telemetry"), ("b", "Imaging studies")]
TABLE_RECORD = {"a": "Waveform telemetry is collected.", "b": "Imaging studies are collected."}


@pytest.mark.parametrize("layout", TABLE_LAYOUTS)
@pytest.mark.parametrize("cell", ["Completed", "Released", "Current", "Existing", "Pending"])
def test_a_one_word_counter_cell_does_not_close_a_status_headings_scope(cell, layout):
    # #3166: a one-word line is a table cell as often as a heading, for a
    # counter word as for a status word. A "Completed" cell closed the
    # heading's scope for every row below it, so the result depended on the
    # row order; now every row of every layout is read under the heading.
    out = _run(TABLE_LAYOUTS[layout].format(cell=cell), TABLE_PAIRS, TABLE_RECORD)
    assert out["counts"]["located"] == 2
    assert sorted((f["slot"], f["via"], f["governor"]) for f in out["flags"]) == [
        ("a", "heading", "Planned Data Collection"), ("b", "heading", "Planned Data Collection")]


@pytest.mark.parametrize("cell", ["Completed Studies", "Completed:"])
def test_a_two_word_counter_heading_or_a_counter_lead_in_still_closes_the_scope(cell):
    # The two-word minimum is the only change: a counter heading of two
    # words, or a one-word counter lead-in, closes the scope below it.
    out = _run(TABLE_LAYOUTS["status first"].format(cell=cell), TABLE_PAIRS, TABLE_RECORD)
    assert out["counts"]["located"] == 2 and out["flags"] == []


@pytest.mark.parametrize("doc,snippet,governor,cls", [
    # An own line carrying a status marker is a status heading, not a
    # counter-heading, whatever counter word it also carries — with or
    # without a sentence terminator on it (#3171). The heading above still
    # governs the classes the own line does not carry.
    ("Ongoing Work Streams\nCurrent Planned Release\n50,000\nPatient admissions",
     "Current Planned Release\n50,000", "Ongoing Work Streams", "in_progress"),
    ("Anticipated Final Dataset\nCurrent Planned Release\n50,000\nPatient admissions",
     "Current Planned Release\n50,000", "Anticipated Final Dataset", "prospective"),
    ("Anticipated Final Dataset\nCurrent release; planned expansion\n50,000",
     "Current release", "Anticipated Final Dataset", "prospective"),
])
def test_an_own_line_carrying_a_status_marker_does_not_close_the_scope(doc, snippet, governor, cls):
    out = _run(doc, [("x", snippet)], {"x": "50,000 admissions"})
    assert [(f["class"], f["via"], f["governor"]) for f in out["flags"]
            if f["rule"] == "governor_outside_snippet"] == [(cls, "heading", governor)]


def test_a_colon_lead_in_governs_the_short_lines_below_it_and_a_wrapped_item_is_not_a_heading():
    doc = ("Training will include:\n\nWorkshops on using notebooks\n\nOngoing mentorship and support\n"
           "using cloud platforms\n\nWorkshops on the common data model\n")
    record = {"x": "Workshops on the common data model."}
    [flag] = _run(doc, [("x", "Workshops on the common data model")], record)["flags"]
    assert (flag["class"], flag["marker"], flag["via"], flag["governor"]) == (
        "planned", "will", "lead-in", "Training will include:")
    current = doc.replace("Training will include:", "Training currently includes:")
    assert _run(current, [("x", "Workshops on the common data model")], record)["flags"] == []


def test_the_snippet_itself_carries_the_modal_the_value_dropped():
    doc = "Access will be granted to approved researchers after review."
    snippet = "Access will be granted to approved researchers"
    out = _run(doc, [("access_details", snippet)], {"access_details": "Access is granted to approved researchers."})
    assert _rules(out) == [("modal_dropped", "access_details", "planned")]
    assert out["flags"][0]["marker"] == "will"
    for kept in ("Access will be granted to approved researchers.",
                 "Access is anticipated for approved researchers."):
        assert _run(doc, [("access_details", snippet)], {"access_details": kept})["flags"] == []


def test_label_slots_are_reported_in_their_own_bucket():
    doc = "Anticipated Final Dataset\nContributing sites\nNorthern Hospital Network\n"
    out = _run(doc, [("creators[0].name", "Northern Hospital Network")],
               {"creators": [{"name": "Northern Hospital Network"}]})
    assert out["flags"] == []
    assert _rules(out, "label_slot") == [("governor_outside_snippet", "creators[0].name", "prospective")]
    assert out["counts"]["slots_flagged"] == {"value": 0, "label": 1}


def test_semicolons_separate_terms_but_a_colon_lead_in_still_governs():
    terms = "Preferred terms:\nCare;Illness;Goals;Data Element;Hospitals"
    out = _run(terms, [("keywords", "Care;Illness")], {"keywords": ["Care", "Illness"]})
    assert out["counts"]["located"] == 1 and out["flags"] == []
    clauses = "The project will: collect records; standardize data to a common model; release data."
    [flag] = _run(clauses, [("x", "standardize data to a common model")], {"x": "Data are standardized."})["flags"]
    assert (flag["marker"], flag["via"]) == ("will", "sentence")


def test_a_repeated_snippet_is_flagged_only_when_every_occurrence_is_governed():
    one = "The team will harmonise records to a common model."
    record = {"x": "Records are harmonised to a common model."}
    assert len(_run(one, [("x", "harmonise records to a common model")], record)["flags"]) == 1
    both = one + " Separately, the archive can harmonise records to a common model today."
    assert _run(both, [("x", "harmonise records to a common model")], record)["flags"] == []


def test_each_part_of_a_multipart_snippet_is_read_in_its_own_context():
    doc = "Nursing flowsheets\nThe archive will be rebuilt next year.\nYes (common schema with extensions)"
    record = {"x": "Nursing flowsheets use the common schema."}
    out = _run(doc, [("x", "Nursing flowsheets...Yes (common schema with")], record)
    assert out["counts"]["located"] == 1 and out["flags"] == []


def test_unverified_and_unresolved_snippets_are_counted_and_never_flagged():
    out = _run(ENUMERATION, [(D_SLOT, "this passage is not in the chunk at all"),
                             ("absent.path", D_SNIPPET)], {})
    assert out["flags"] == [] and out["label_slot"] == []
    assert (out["counts"]["not_verified"], out["counts"]["value_unresolved"]) == (1, 1)


def test_final_record_is_followed_by_identity_and_reports_whether_it_expresses_the_status():
    snapshot = {"preprocessing_strategies": [{"id": "p1", "preprocessing_details": "Data are standardized."}]}
    final = {"preprocessing_strategies": [{"id": "p0", "preprocessing_details": "An earlier step."},
                                          {"id": "p1", "preprocessing_details": "Data will be standardized."}]}
    text, manifest = _bundle(ENUMERATION)
    out = sc.receipt_context(_receipt(text, [(D_SLOT, D_SNIPPET)]), manifest, text, snapshot, final=final)
    [flag] = out["flags"]
    assert flag["final_path"] == "preprocessing_strategies[1].preprocessing_details"
    assert flag["final_expresses_status"] is True


# ------------------------------------------------------------------ rule 2
def _claim(text, status, quote="The plan is described.", verdict="supported", chunk="c002"):
    return {"text": text, "verdict": verdict, "attributed_to": [], "claim_status": status,
            "source_status": status, "evidence": [{"source": "d0.txt", "chunk": chunk, "quote": quote}],
            "reason": "synthetic"}


def _review(*rows):
    return {"artifact": "original_full", "sha256": "0" * 64,
            "values": [{"path": p, "claims": claims} for p, claims in rows]}


def test_a_claim_declared_planned_whose_text_is_unqualified():
    out = sc.review_status_expression(_review(("/data_collectors/0/collector_details",
                                               [_claim("Fourteen hospitals contribute data.", "planned")])))
    [flag] = out["flags"]
    assert (flag["rule"], flag["path"], flag["declared"]) == (
        "status_unexpressed", "/data_collectors/0/collector_details", "planned")
    kept = sc.review_status_expression(_review(("/data_collectors/0/collector_details",
                                                [_claim("Fourteen hospitals will contribute data.", "planned")])))
    assert kept["flags"] == [] and kept["counts"]["expressed"] == 1


def test_in_progress_is_expressed_only_by_an_in_progress_marker():
    planned_words = _review(("/notes", [_claim("Curation will continue.", "in_progress")]))
    assert _rules_r2(sc.review_status_expression(planned_words)) == [("status_unexpressed", "/notes")]
    ongoing = _review(("/notes", [_claim("Curation is ongoing.", "in_progress")]))
    assert sc.review_status_expression(ongoing)["flags"] == []


def _rules_r2(out, bucket="flags"):
    return [(f["rule"], f["path"]) for f in out[bucket]]


def test_malformed_model_output_is_counted_not_raised():
    review = _review(("/notes", [_claim("Curation continues.", ["planned"]), "not a claim"]),
                     ("/other", "not a claims list"))
    out = sc.review_status_expression(review)
    assert out["flags"] == [] and out["counts"]["declared"] == {"None": 1}
    text, manifest = _bundle(ENUMERATION)
    manifest["chunks"].append({"id": "c999", "lines": [10**6, 10**6 + 1]})
    view = sc.BundleView(text, manifest)
    assert "c999" not in view.chunks and "c002" in view.chunks
    manifest["chunks"].append({"id": ["c002"], "lines": [5, 6]})           # an unhashable id is not a chunk
    assert set(sc.BundleView(text, manifest).chunks) == set(view.chunks)


def _malformed_receipt(text):
    pair = {"slot": D_SLOT, "snippet": D_SNIPPET}
    return {"bundle_md5": _md5(text), "chunks": [
        {"id": ["c002"], "status": "extracted", "extracted": [pair]},       # an unhashable chunk id
        {"id": "c002", "status": "extracted", "extracted": 5},              # extracted not a list
        {"id": "c002", "status": "extracted", "extracted": pair},           # one pair, not listed
        "not an entry",
        {"id": "c002", "status": "extracted", "extracted": ["not a pair", pair]},   # a pair not a mapping
        {"id": 7, "status": "nothing_relevant", "reason": "boilerplate"},  # any status needs a string id
        {"id": "c002", "status": "extracted", "extracted": [pair]}]}        # the one well-formed entry


def test_a_malformed_receipt_entry_is_counted_not_raised():
    # #3090: the receipt is model output. The entries `receipts.check`
    # reports as `malformed_entry` (#724) are counted and not read, and the
    # well-formed entry beside them still is.
    text, manifest = _bundle(ENUMERATION)
    record = {"preprocessing_strategies": [{"preprocessing_details": "Data are standardized."}]}
    receipt = _malformed_receipt(text)
    out = sc.receipt_context(receipt, manifest, text, record)
    c = out["counts"]
    assert (c["malformed_entries"], c["snippets"], c["verified"]) == (6, 1, 1)
    texts = dict(zip((ch["id"] for ch in manifest["chunks"]), chunking.chunk_texts(text, manifest["chunks"])))
    findings = rc.check(receipt, manifest, texts, record, manifest["bundle_md5"])["findings"]
    assert c["malformed_entries"] == sum(1 for f in findings if f["kind"] == "malformed_entry")
    assert _rules(out) == [("governor_outside_snippet", D_SLOT, "planned")]
    assert "6 malformed receipt entries not read" in out["summary"]
    assert "malformed" not in _run(ENUMERATION, [(D_SLOT, D_SNIPPET)], record)["summary"]


@pytest.mark.parametrize("chunk", [["c002"], {"id": "c002"}, 2, "c999"])
def test_evidence_naming_no_chunk_of_the_bundle_is_counted_not_raised(chunk):
    text, manifest = _bundle(ENUMERATION)
    view = sc.BundleView(text, manifest)
    out = sc.review_status_expression(_review(("/x", [
        _claim("Capabilities exist.", "fact", quote="develop capabilities", chunk=chunk)])), view=view)
    assert out["flags"] == [] and out["counts"]["quotes_chunk_not_in_bundle"] == 1
    assert "1 quote(s) on supported fact claims examined, 1 naming no chunk of the bundle" in out["summary"]
    # The same quote in its own chunk is read in its context.
    [flag] = sc.review_status_expression(_review(("/x", [
        _claim("Capabilities exist.", "fact", quote="develop capabilities")])), view=view)["flags"]
    assert (flag["rule"], flag["via"], flag["marker"]) == ("planned_evidence_declared_fact", "enumeration", "will")


def test_the_evidence_context_counts_cover_only_the_quotes_examined():
    # #3168: a context is read only where it can decide a flag — on a
    # supported claim declared fact, for a quote with no planned marker of
    # its own, up to the claim's first hit. A bad chunk elsewhere is not
    # examined and so not counted, and the summary says what was examined.
    text, manifest = _bundle(ENUMERATION)
    view = sc.BundleView(text, manifest)
    bad = {"source": "d0.txt", "chunk": "c999", "quote": "develop capabilities"}
    hit = {"source": "d0.txt", "chunk": "c002", "quote": "The service will be deployed."}
    not_examined = [
        _claim("Capabilities are planned.", "planned", chunk="c999"),              # declared planned
        _claim("Capabilities are underway.", "in_progress", chunk="c999"),         # declared in progress
        _claim("Capabilities exist.", "fact", chunk="c999", verdict="revise"),     # not supported
        {**_claim("Capabilities exist.", "fact"), "evidence": [hit, bad]},         # after the first hit
        {**_claim("Capabilities exist.", "fact"), "evidence": [{**hit, "chunk": "c999"}]},   # its own marker
    ]
    out = sc.review_status_expression(_review(("/x", not_examined)), view=view)
    c = out["counts"]
    assert (c["quotes_examined_for_context"], c["quotes_chunk_not_in_bundle"], c["unlocated_quotes"]) == (0, 0, 0)
    assert "evidence context: 0 quote(s) on supported fact claims examined, 0 naming no chunk" in out["summary"]
    examined = [{**_claim("Capabilities exist.", "fact"), "evidence": [
        bad, {**bad, "chunk": "c002", "quote": "not a passage of this chunk"},
        {**bad, "chunk": "c002", "quote": "perform community focus groups"}]}]
    c = sc.review_status_expression(_review(("/x", examined)), view=view)["counts"]
    assert (c["quotes_examined_for_context"], c["quotes_chunk_not_in_bundle"], c["unlocated_quotes"]) == (3, 1, 1)


def test_a_review_naming_no_artifact_cannot_be_bound_to_a_record():
    review = {**_review(("/notes", [_claim("Curation continues.", "planned")])), "artifact": ["original_full"]}
    with pytest.raises(ValueError, match="names no artifact"):
        sc.review_status_expression(review, record_raw="notes: Curation continues.\n")


ODD_SHAPES = [None, 5, 1.5, True, "", "c002", ["c002"], {"id": "c002"}, [["x"]], [None]]


def test_no_model_output_field_of_any_shape_raises():
    # #3090, generalised: each field a model writes, in the receipt and in
    # the source review, set in turn to each odd shape. A malformed field is
    # counted or passed over; neither rule raises (only a record that cannot
    # be bound to the review is a ValueError, which the CLI reports).
    text, manifest = _bundle(ENUMERATION)
    view = sc.BundleView(text, manifest)
    pair = {"slot": D_SLOT, "snippet": D_SNIPPET}
    record = {"preprocessing_strategies": [{"preprocessing_details": "Data are standardized."}]}
    for odd in ODD_SHAPES:
        entries = [odd, {"id": odd, "status": "extracted", "extracted": [pair]},
                   {"id": "c002", "status": odd, "extracted": [pair]},
                   {"id": "c002", "status": "extracted", "extracted": odd},
                   {"id": "c002", "status": "extracted", "extracted": [odd]},
                   {"id": "c002", "status": "extracted", "extracted": [{"slot": odd, "snippet": D_SNIPPET}]},
                   {"id": "c002", "status": "extracted", "extracted": [{"slot": D_SLOT, "snippet": odd}]}]
        for entry in entries:
            for addressed, final in ((record, odd), (odd, record)):
                sc.receipt_context({"bundle_md5": _md5(text), "chunks": [entry]}, manifest, text, addressed,
                                   final=final)
        claim = _claim("Capabilities exist.", "fact", quote="develop capabilities")
        claims = [{**claim, "evidence": odd}, {**claim, "evidence": [odd]},
                  {**claim, "evidence": [{**claim["evidence"][0], "chunk": odd}]},
                  {**claim, "evidence": [{**claim["evidence"][0], "quote": odd}]},
                  {**claim, "claim_status": odd}, {**claim, "text": odd}, {**claim, "verdict": odd}, odd]
        rows = [{"path": "/x", "claims": claims}, {"path": odd, "claims": [claim]}, {"path": "/x", "claims": odd}, odd]
        review = {"artifact": "original_full", "sha256": "0" * 64, "values": rows}
        sc.review_status_expression(review, view=view)
        sc.review_status_expression(review)
        with pytest.raises(ValueError):
            sc.review_status_expression({**review, "artifact": odd}, record_raw="x: 1\n")


def test_a_name_slot_is_routed_to_the_label_bucket():
    out = sc.review_status_expression(_review(("/creators/0/name", [_claim("Northern Network", "planned")]),
                                              ("/title", [_claim("A Data Resource", "planned")])))
    assert out["flags"] == []
    assert _rules_r2(out, "label_slot") == [("status_unexpressed", "/creators/0/name"),
                                            ("status_unexpressed", "/title")]


def test_a_marker_elsewhere_in_the_same_value_counts_once_the_record_is_read():
    raw = "notes: The team will release data. Data include waveforms.\n"
    inv = source_review.inventory(raw, "original_full")
    review = {"artifact": "original_full", "sha256": inv["sha256"], "values": [{"path": "/notes", "claims": [
        _claim("The team will release data.", "planned"), _claim("Data include waveforms.", "planned")]}]}
    assert _rules_r2(sc.review_status_expression(review)) == [("status_unexpressed", "/notes")]
    out = sc.review_status_expression(review, record_raw=raw)
    assert out["flags"] == [] and out["counts"]["expressed_elsewhere_in_value"] == 1
    with pytest.raises(ValueError, match="sha256"):
        sc.review_status_expression(review, record_raw=raw.replace("waveforms", "images"))


def test_evidence_carrying_a_planned_marker_while_the_claim_is_declared_fact():
    out = sc.review_status_expression(_review(("/description", [
        _claim("The service is deployed.", "fact", quote="The service will be deployed.")])))
    [flag] = out["flags"]
    assert (flag["rule"], flag["via"], flag["marker"]) == ("planned_evidence_declared_fact", "quote", "will")
    fact = sc.review_status_expression(_review(("/description", [
        _claim("The service is deployed.", "fact", quote="The service is deployed.")])))
    assert fact["flags"] == []
    revise = sc.review_status_expression(_review(("/description", [
        _claim("The service is deployed.", "fact", quote="The service will be deployed.", verdict="revise")])))
    assert revise["flags"] == []


def test_evidence_under_a_status_heading_is_read_with_the_bundle():
    text, manifest = _bundle(PANEL)
    view = sc.BundleView(text, manifest)
    governed = _review(("/data_collectors/0/collector_details", [
        _claim("14 hospitals contribute data", "fact", quote="14\nData contributing hospitals")]))
    assert sc.review_status_expression(governed)["flags"] == []            # no bundle: the quote alone
    [flag] = sc.review_status_expression(governed, view=view)["flags"]
    assert (flag["via"], flag["marker"], flag["governor"]) == ("heading", "anticipated", "Anticipated Final Dataset")
    released = _review(("/instances/0/counts", [
        _claim("50,000 admissions", "fact", quote="50,000\nPatient admissions from intensive care")]))
    assert sc.review_status_expression(released, view=view)["flags"] == []


# ------------------------------------------- the validators stay as they were
def test_receipts_check_is_byte_identical_beside_the_diagnostic():
    from tests.test_receipts import BUNDLE, FULL, _manifest_and_texts, _receipt as receipt_fixture
    manifest, texts = _manifest_and_texts()
    receipt = receipt_fixture(manifest["bundle_md5"])
    before = json.dumps(rc.check(receipt, manifest, texts, FULL, manifest["bundle_md5"]), sort_keys=True)
    inputs = copy.deepcopy((receipt, manifest, texts, FULL))
    out = sc.receipt_context(receipt, manifest, BUNDLE, FULL)
    assert out["counts"]["verified"] > 0
    assert (receipt, manifest, texts, FULL) == inputs                       # nothing passed in is modified
    assert json.dumps(rc.check(receipt, manifest, texts, FULL, manifest["bundle_md5"]), sort_keys=True) == before


def test_source_review_check_is_byte_identical_beside_the_diagnostic():
    from tests.test_source_review import CHUNKS, review_for
    raw = "description: The protocol describes a planned independent validation set.\n"
    review = review_for(raw)
    review["values"][0]["claims"][0].update(attributed_to=["protocol.txt"], claim_status="planned",
                                            source_status="planned")
    audit = {"findings": [], "summary": "0 findings", "source_review": review}
    check = lambda: json.dumps(source_review.check(review, raw=raw, artifact="original_full", chunks=CHUNKS),
                               sort_keys=True)
    before, inputs = check(), copy.deepcopy(audit)
    out = sc.review_status_expression(audit, record_raw=raw)
    assert out["counts"]["expressed"] == 1 and out["flags"] == []
    assert audit == inputs and check() == before


def _tree_hashes(root):
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def test_the_receipts_cli_reads_named_files_writes_nothing_and_exits_zero(tmp_path):
    text, _m = _bundle(ENUMERATION)
    bundle = tmp_path / "study.txt"
    bundle.write_text(text, encoding="utf-8")
    (tmp_path / "study_chunks.yaml").write_text(chunking.dump_manifest(chunking.build_manifest(bundle)),
                                                encoding="utf-8")
    (tmp_path / "receipt.yaml").write_text(yaml.safe_dump(_receipt(text, [(D_SLOT, D_SNIPPET)])), encoding="utf-8")
    (tmp_path / "record.yaml").write_text(yaml.safe_dump(
        {"preprocessing_strategies": [{"preprocessing_details": "Data are standardized."}]}), encoding="utf-8")
    before = _tree_hashes(tmp_path)
    args = ["receipts", "status-context", "--receipt", str(tmp_path / "receipt.yaml"),
            "--bundle", str(bundle), "--record", str(tmp_path / "record.yaml")]
    result = CliRunner().invoke(cli, args + ["--json"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert [(f["rule"], f["slot"]) for f in out["flags"]] == [("governor_outside_snippet", D_SLOT)]
    text_out = CliRunner().invoke(cli, args)
    assert text_out.exit_code == 0 and "flag governor_outside_snippet" in text_out.output
    assert "assurance: Lexical and non-gating" in text_out.output
    assert _tree_hashes(tmp_path) == before
    # A receipt written against other bytes is not read against these.
    (tmp_path / "receipt.yaml").write_text(yaml.safe_dump({**_receipt(text, []), "bundle_md5": "0" * 32}))
    stale = CliRunner().invoke(cli, args)
    assert stale.exit_code == 0 and "unchecked: the receipt names bundle md5" in stale.output
    usage = CliRunner().invoke(cli, ["receipts", "status-context", "--receipt", str(tmp_path / "receipt.yaml")])
    assert usage.exit_code == 2
    escape = CliRunner().invoke(cli, ["receipts", "status-context", "--label", "L", "--project", "../x"])
    assert escape.exit_code == 2 and "basename" in escape.output
    (tmp_path / "receipt.yaml").write_text("chunks: [unclosed", encoding="utf-8")
    broken = CliRunner().invoke(cli, args)
    assert broken.exit_code == 1 and "Error:" in broken.output and broken.exception.__class__ is SystemExit


def test_the_text_report_prints_each_flag_on_one_line_whatever_its_text_spans():
    # #3169: a snippet, a governor, a slot or a reason can carry bundle or
    # model line breaks; each is written as the two characters \n, so a
    # line-oriented reader sees one line per flag. JSON keeps the text.
    doc = ("Anticipated Final Dataset\n14\nData contributing hospitals\n\n"
           "The consortium\nwill:\n\nWorkshops on the common data model")
    out = _run(doc, [("x", "14\nData contributing hospitals"), ("y", "Workshops on the common data model")],
               {"x": "Fourteen hospitals contribute data.", "y": "Workshops on the common data model."})
    assert [(f["slot"], f["snippet"], f["governor"]) for f in out["flags"]] == [
        ("x", "14\nData contributing hospitals", "Anticipated Final Dataset"),
        ("y", "Workshops on the common data model", "The consortium\nwill:")]
    lines = sc.report_lines(out)
    assert len(lines) == 5 and all(len(line.splitlines()) == 1 for line in lines)
    assert "snippet=14\\nData contributing hospitals" in lines[2] and "governor=The consortium\\nwill:" in lines[3]
    flag = out["flags"][0]
    breaks = "a\nb\r\nc\rd\x0be\x0cf\x1cg\x85h i j"
    synthetic = {**out, "summary": "claims " + breaks,
                 "flags": [{**flag, "snippet": breaks, "governor": breaks}],
                 "label_slot": [{**flag, "slot": "creators[0].name\nx"}],
                 "unlocated": [{"chunk": "c\n002", "slot": "s\nlot", "snippet": breaks}]}
    lines = sc.report_lines(synthetic)
    assert len(lines) == 7 and all(len(line.splitlines()) == 1 for line in lines)
    assert "snippet=a\\nb\\nc\\nd\\ne\\nf\\ng\\nh\\ni\\nj" in lines[2] and "governor=a\\nb" in lines[2]
    assert lines[4].startswith("   flag governor_outside_snippet creators[0].name\\nx:")
    assert lines[5] == "   · unlocated: chunk=c\\n002 slot=s\\nlot"
    unchecked = sc.report_lines({**sc._unchecked(sc.RULE_RECEIPT, "no manifest at\n/x"), "rule": "r\nule"})
    assert unchecked == ["   status_context v1 (#2917) · r\\nule · non-gating", "   · unchecked: no manifest at\\n/x"]


def test_the_receipts_cli_prints_a_multiline_snippet_on_one_line(tmp_path):
    text, _m = _bundle(PANEL)
    bundle = tmp_path / "study.txt"
    bundle.write_text(text, encoding="utf-8")
    (tmp_path / "study_chunks.yaml").write_text(chunking.dump_manifest(chunking.build_manifest(bundle)),
                                                encoding="utf-8")
    (tmp_path / "receipt.yaml").write_text(yaml.safe_dump(_receipt(text, PANEL_PAIRS[:1])), encoding="utf-8")
    (tmp_path / "record.yaml").write_text(yaml.safe_dump(
        {"data_collectors": [{"collector_details": "Fourteen hospitals contribute data."}]}), encoding="utf-8")
    args = ["receipts", "status-context", "--receipt", str(tmp_path / "receipt.yaml"),
            "--bundle", str(bundle), "--record", str(tmp_path / "record.yaml")]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert len(lines) == 4 and all(line.startswith("   ") for line in lines)
    assert "snippet=14\\nData contributing hospitals" in lines[2]
    as_json = json.loads(CliRunner().invoke(cli, args + ["--json"]).output)
    assert as_json["flags"][0]["snippet"] == "14\nData contributing hospitals"


def test_the_review_cli_reads_an_audit_and_writes_nothing(tmp_path):
    audit = {"findings": [], "summary": "0 findings", "source_review": _review(
        ("/notes", [_claim("Curation continues.", "in_progress")]))}
    (tmp_path / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
    before = _tree_hashes(tmp_path)
    result = CliRunner().invoke(cli, ["review", "status-expression", "--audit", str(tmp_path / "audit.json"), "--json"])
    assert result.exit_code == 0, result.output
    assert [(f["rule"], f["path"]) for f in json.loads(result.output)["flags"]] == [("status_unexpressed", "/notes")]
    assert _tree_hashes(tmp_path) == before
    (tmp_path / "bad.json").write_text("[]", encoding="utf-8")
    bad = CliRunner().invoke(cli, ["review", "status-expression", "--audit", str(tmp_path / "bad.json")])
    assert bad.exit_code == 1 and "no source_review" in bad.output


def test_both_clis_count_malformed_model_output_and_exit_zero(tmp_path):
    # #3090: a list chunk id in a receipt, or in an audit's evidence, raised
    # an uncaught TypeError through both commands.
    text, _m = _bundle(ENUMERATION)
    bundle = tmp_path / "study.txt"
    bundle.write_text(text, encoding="utf-8")
    (tmp_path / "study_chunks.yaml").write_text(chunking.dump_manifest(chunking.build_manifest(bundle)),
                                                encoding="utf-8")
    (tmp_path / "receipt.yaml").write_text(yaml.safe_dump(_malformed_receipt(text)), encoding="utf-8")
    (tmp_path / "record.yaml").write_text(yaml.safe_dump(
        {"preprocessing_strategies": [{"preprocessing_details": "Data are standardized."}]}), encoding="utf-8")
    before = _tree_hashes(tmp_path)
    receipts = CliRunner().invoke(cli, ["receipts", "status-context", "--receipt", str(tmp_path / "receipt.yaml"),
                                        "--bundle", str(bundle), "--record", str(tmp_path / "record.yaml")])
    assert receipts.exit_code == 0 and receipts.exception is None, receipts.output
    assert "6 malformed receipt entries not read" in receipts.output
    audit = {"source_review": _review(("/x", [
        _claim("Capabilities exist.", "fact", quote="develop capabilities", chunk=["c002"])]))}
    (tmp_path / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
    review = CliRunner().invoke(cli, ["review", "status-expression", "--audit", str(tmp_path / "audit.json"),
                                      "--bundle", str(bundle)])
    assert review.exit_code == 0 and review.exception is None, review.output
    assert "1 naming no chunk of the bundle" in review.output
    before[tmp_path / "audit.json"] = hashlib.sha256((tmp_path / "audit.json").read_bytes()).hexdigest()
    assert _tree_hashes(tmp_path) == before


# ------------------------------------------------ replay on a committed run
V8_REP1 = "2026-09-04f_claude-opus-5-api-generic-v8_rep1"
V8_CORE = ROOT / "data" / "d4d_concatenated" / "claudecode_api_core" / V8_REP1
V8_FULL = ROOT / "data" / "d4d_concatenated" / "claudecode_api" / V8_REP1 / "CHORUS_d4d.yaml"


@pytest.mark.skipif(not (V8_CORE / "CHORUS_coverage_receipt.yaml").exists(), reason="v8 rep1 run not on disk")
def test_replay_flags_the_planned_preprocessing_the_v8_rep1_chorus_receipt_quotes_from_line_45():
    files = [V8_CORE / "CHORUS_provenance.yaml", V8_CORE / "CHORUS_coverage_receipt.yaml", V8_FULL,
             V8_CORE / "intermediate" / "CHORUS_full.yaml"]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    out = sc.run_status_context(files[0], files[1], V8_FULL)
    assert out["checked"] and out["value_basis"].startswith("phase-1 snapshot")
    flagged = {(f["slot"], f["source_line"], f["marker"], f["via"], f.get("final_expresses_status"))
               for f in out["flags"] if f["rule"] == "governor_outside_snippet"}
    for i in (0, 1):
        assert (f"preprocessing_strategies[{i}].preprocessing_details", 45, "will", "enumeration", False) in flagged
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files} == before
    # #3169 on committed data: three of this run's flagged snippets span
    # bundle lines, and the text report still prints one line per flag.
    assert sum("\n" in f["snippet"] for f in out["flags"] + out["label_slot"]) >= 1
    lines = sc.report_lines(out)
    assert all(len(line.splitlines()) == 1 and line.startswith("   ") for line in lines)
    assert len(lines) == (3 + len(out["flags"]) + len(out["unlocated"])
                          + (1 + len(out["label_slot"]) if out["label_slot"] else 0))


V8_REP3 = "2026-09-04f_claude-opus-5-api-generic-v8_rep3"
V8_REP3_CORE = ROOT / "data" / "d4d_concatenated" / "claudecode_api_core" / V8_REP3
V8_REP3_FULL = ROOT / "data" / "d4d_concatenated" / "claudecode_api" / V8_REP3 / "CHORUS_d4d.yaml"


@pytest.mark.skipif(not (V8_REP3_CORE / "CHORUS_coverage_receipt.yaml").exists(), reason="v8 rep3 run not on disk")
def test_replay_the_v8_rep3_chorus_receipt_quoting_the_counter_heading_is_not_flagged():
    # #3089 on committed data: this receipt quotes "Current Released
    # Dataset ... Patient admissions" for `instances[0].counts`, and the
    # "Anticipated Final Dataset" heading nine lines above it was reported
    # as its governor. The consortium count under that heading still is.
    receipt = V8_REP3_CORE / "CHORUS_coverage_receipt.yaml"
    files = [V8_REP3_CORE / "CHORUS_provenance.yaml", receipt, V8_REP3_FULL,
             V8_REP3_CORE / "intermediate" / "CHORUS_full.yaml"]
    quoted = [p["snippet"] for e in rc.load_receipt(receipt)["chunks"] if isinstance(e, dict)
              for p in e.get("extracted") or [] if p.get("slot") == "instances[0].counts"]
    assert any(q.startswith("Current Released Dataset") for q in quoted)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    out = sc.run_status_context(files[0], files[1], V8_REP3_FULL)
    assert out["checked"] and out["value_basis"].startswith("phase-1 snapshot")
    governed = {f["slot"] for f in out["flags"] if f.get("governor") == "Anticipated Final Dataset"}
    assert "instances[0].counts" not in governed and "creators[0].notes" in governed
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files} == before
