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


@pytest.fixture(autouse=True)
def _fresh_caches():
    """Run mode's process-local caches (#3709) never carry one test's
    bundle into another."""
    sc.clear_caches()
    yield
    sc.clear_caches()


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
    "in the process": "described in the process documentation",
}


@pytest.mark.parametrize("phrase", EXCLUDED_EXAMPLES.values())
def test_excluded_terms_carry_no_status(phrase):
    assert sc.classes(phrase) == {}


def test_every_listed_exclusion_has_a_tested_example_and_every_tested_exclusion_is_listed():
    # EXCLUDED_TERMS is what a curator signs off (#2917, owner decision 3)
    # (#3091, #3172): the examples above are the only exclusions this file
    # tests, each names its term, and the two lists are the same list.
    assert set(EXCLUDED_EXAMPLES) == set(sc.EXCLUDED_TERMS)
    for term, phrase in EXCLUDED_EXAMPLES.items():
        assert term in phrase and sc.classes(phrase) == {}, term


def _negative_lookaheads(pattern):
    """(literal prefix, alternatives) for each `(?!...)` in a pattern."""
    out, i = [], pattern.find("(?!")
    while i >= 0:
        depth, j = 1, i + 3
        while depth:
            depth += {"(": 1, ")": -1}.get(pattern[j], 0) if pattern[j - 1] != "\\" else 0
            j += 1
        body = pattern[i + 3:j - 1]
        out.append((pattern[:i], body.split("|")))
        i = pattern.find("(?!", j)
    return out


def test_every_lookahead_carve_out_in_a_registered_pattern_is_a_listed_exclusion():
    # #3172: derived from the patterns, not from a hand-kept list, so a
    # carve-out added to a pattern and not to EXCLUDED_TERMS fails here.
    carved = set()
    for terms in [*sc.STATUS_MARKERS.values(), sc.COUNTER_MARKERS]:
        for term, pattern in terms:
            assert "(?<!" not in pattern, f"{term}: read negative lookbehinds here before adding one"
            for prefix, alternatives in _negative_lookaheads(pattern):
                lead = prefix.split("|")[-1].replace("\\b", "")
                assert re.fullmatch(r"[a-z ]*", lead), f"{term}: a carve-out follows literal words"
                for alt in alternatives:
                    word = alt.replace("\\b", "")
                    assert re.fullmatch(r"[a-z ]+", word), f"{term}: carve-out {alt!r} is not a literal word"
                    carved.add((lead + word).strip())
    assert "to be used" in carved                          # the derivation sees today's carve-out
    assert carved <= set(sc.EXCLUDED_TERMS), carved - set(sc.EXCLUDED_TERMS)
    # The helper reads what a new carve-out would look like.
    assert _negative_lookaheads(r"\bto be (?!used\b|funded\b)\w+(?:ed|en)\b") == [
        (r"\bto be ", [r"used\b", r"funded\b"])]


def test_the_vocabulary_digest_is_pinned():
    # #3172: any change to a registered pattern, counter marker, class map
    # or label leaf moves this digest. Rotate the pin in the same change,
    # after listing in EXCLUDED_TERMS any sense the change leaves out.
    assert sc.VOCABULARY == {"version": 1,
                             "sha256": "59184b2d2ff47c54b231deefeb030369d5ebb4d956f44e9b1e96b27ccdf3efcc"}


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


def test_a_snippet_the_validator_verifies_split_at_its_line_breaks_is_located_part_by_part():
    # #3170: `receipts.snippet_in` retries a multi-line snippet with its
    # line breaks as implicit `...` (#882); locate splits it the same way,
    # so the snippet is read in context rather than reported unlocated.
    doc = ("The archive holds waveform telemetry\nand clinical notes; imaging is separate.\n"
           "Records were standardized to a common model.")
    snippet = "The archive holds waveform telemetry\nRecords were standardized to a common model"
    text, manifest = _bundle(doc)
    view = sc.BundleView(text, manifest)
    assert rc.snippet_in(snippet, view.chunk_text("c002")) == (True, "split-at-linebreaks")
    [[(a1, b1), (a2, b2)]] = view.locate("c002", snippet)
    assert (text[a1:b1], text[a2:b2]) == tuple(snippet.split("\n"))
    out = _run(doc, [("x", snippet)], {"x": "Records are standardized."})
    assert (out["counts"]["located"], out["counts"]["unlocated"]) == (1, 0)


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


@pytest.mark.parametrize("line,closes", [
    # #3170: a counter word closes a scope only on a heading-like line:
    # capitalised, at most HEADING_MAX_WORDS words and HEADING_MAX_CHARS
    # characters. Any other short line is passed over like a count label,
    # sentence terminator or not.
    ("Current Released Dataset", True),
    ("the current figures for the network", False),                                   # lower case
    ("Current counts at six sites of the network so far", False),                    # 10 words
    ("Current Consolidated Institutional Contributions Across Participating Hospitals", False),  # 79 chars
])
def test_a_counter_word_closes_a_scope_only_on_a_heading_like_line(line, closes):
    assert (len(line.split()) <= sc.HEADING_MAX_WORDS and len(line) <= sc.HEADING_MAX_CHARS
            and line[0].isupper()) is closes
    doc = f"Anticipated Final Dataset\n9\nDifferent data modalities\n{line}\n14\nData contributing hospitals"
    out = _run(doc, [("x", "14\nData contributing hospitals")], {"x": "Fourteen hospitals contribute data."})
    assert [f["governor"] for f in out["flags"]] == ([] if closes else ["Anticipated Final Dataset"])


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
    # An in-progress own line under a prospective heading. (A planned own
    # line there already expresses the heading's status, so nothing is
    # lost from the snippet and the heading is not flagged, #3232.)
    ("Anticipated Final Dataset\nCurrent Release in Progress\n50,000\nPatient admissions",
     "Current Release in Progress\n50,000", "Anticipated Final Dataset", "prospective"),
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


@pytest.mark.parametrize("heading", ["Future Data Releases", "Planned Data Releases"])
def test_a_governor_the_snippets_own_marker_expresses_is_not_lost(heading):
    # #3232: planned and prospective express each other (EXPRESSED_BY), so
    # a snippet whose own "will" sits under a "Future ..." heading carries
    # that status; a value that drops it is one loss, `modal_dropped`,
    # whichever of the two equivalent classes the heading uses.
    doc = f"{heading}\nThe consortium will release the imaging waveforms.\n"
    snippet = "will release the imaging waveforms"
    out = _run(doc, [("x", snippet)], {"x": "The consortium releases the imaging waveforms."})
    assert _rules(out) == [("modal_dropped", "x", "planned")]
    assert out["counts"]["flags"]["governor_outside_snippet"]["value"] == 0
    # The heading still governs a snippet that carries no marker of its own.
    bare = _run(doc, [("x", "release the imaging waveforms")], {"x": "The consortium releases the imaging waveforms."})
    assert bare["flags"] and {f["rule"] for f in bare["flags"]} == {"governor_outside_snippet"}
    # A status the snippet's marker does not express is still lost: "will"
    # does not express in-progress.
    ongoing = _run("Ongoing Data Releases\nThe consortium will release the imaging waveforms.\n",
                   [("x", snippet)], {"x": "The consortium releases the imaging waveforms."})
    assert sorted(_rules(ongoing)) == [("governor_outside_snippet", "x", "in_progress"),
                                       ("modal_dropped", "x", "planned")]
    # The same on a heading-shaped own line the snippet quotes (a case
    # #3171's test carried before this): its "Planned" answers the
    # "Anticipated" heading above.
    panel = _run("Anticipated Final Dataset\nCurrent Planned Release\n50,000\nPatient admissions",
                 [("x", "Current Planned Release\n50,000")], {"x": "50,000 admissions"})
    assert _rules(panel) == [("modal_dropped", "x", "planned")]


@pytest.mark.parametrize("snippet,equivalent", [
    ("will publish future imaging waveforms", {"prospective": "future"}),
    ("will publish the waveforms and plans to add labels", None),
])
def test_a_dropped_status_is_one_modal_dropped_whichever_equivalent_markers_carry_it(snippet, equivalent):
    # #3252: planned and prospective are one status (EXPRESSED_BY), so a
    # value that drops a snippet's "will" and "future" is one loss, as it is
    # for a snippet carrying two planned markers.
    doc = f"The consortium {snippet}.\n"
    out = _run(doc, [("x", snippet)], {"x": "The consortium publishes imaging waveforms."})
    assert _rules(out) == [("modal_dropped", "x", "planned")]
    assert out["flags"][0]["marker"] == "will"
    assert out["flags"][0].get("equivalent_markers") == equivalent
    assert out["counts"]["flags"]["modal_dropped"]["value"] == 1
    # A value keeping either equivalent marker keeps the status.
    assert _run(doc, [("x", snippet)], {"x": "Future imaging waveforms are published."})["flags"] == []
    # A distinct status the snippet also carries is still its own flag.
    ongoing = _run(f"The consortium {snippet}; curation is ongoing.\n",
                   [("x", f"{snippet}; curation is ongoing")], {"x": "The consortium publishes imaging waveforms."})
    assert _rules(ongoing) == [("modal_dropped", "x", "planned"), ("modal_dropped", "x", "in_progress")]


def test_a_lost_status_is_one_governor_flag_whichever_equivalent_governors_carry_it():
    # #3245/#3262: a marker-less snippet whose sentence carries "will"
    # (planned) under a "Future ..." heading (prospective) lost one status.
    # One flag, at the nearer governor (the sentence); the heading is listed
    # beside it, so neither governor is dropped from the output.
    doc = "Future Data Releases\nThe consortium will release the imaging waveforms.\n"
    record = {"x": "The consortium releases the imaging waveforms."}
    out = _run(doc, [("x", "release the imaging waveforms")], record)
    text, _m = _bundle(doc)
    assert _rules(out) == [("governor_outside_snippet", "x", "planned")]
    [flag] = out["flags"]
    assert (flag["marker"], flag["via"], flag["source_line"]) == ("will", "sentence", _line(text, "The consortium"))
    assert flag["equivalent_governors"] == [{"class": "prospective", "marker": "future", "via": "heading",
                                             "source_line": _line(text, "Future Data"),
                                             "governor": "Future Data Releases"}]
    assert out["counts"]["flags"]["governor_outside_snippet"]["value"] == 1
    # Two governors of one class were one flag already, with nothing beside it.
    [same] = _run(doc.replace("Future", "Planned"), [("x", "release the imaging waveforms")], record)["flags"]
    assert (same["class"], same["via"]) == ("planned", "sentence") and "equivalent_governors" not in same
    # A distinct status is still its own flag.
    ongoing = _run(doc.replace("Future", "Ongoing"), [("x", "release the imaging waveforms")], record)
    assert _rules(ongoing) == [("governor_outside_snippet", "x", "in_progress"),
                               ("governor_outside_snippet", "x", "planned")]
    assert not any("equivalent_governors" in f for f in ongoing["flags"])
    # A value expressing either equivalent class keeps the status.
    assert _run(doc, [("x", "release the imaging waveforms")],
                {"x": "Future releases include the imaging waveforms."})["flags"] == []


@pytest.mark.parametrize("doc,reported,beside", [
    (("In future the consortium,\nafter review by the board,\nwill release\n"
      "the imaging waveforms to approved users."), ("planned", "will"), ("prospective", "future")),
    # #3435: the nearer governor's class ("prospective") sorts after the
    # farther one's ("planned"), so only the line distance reports it; with
    # the distance tiebreak removed the class name would pick "will".
    (("The consortium will,\nafter review by the board,\nin future release\n"
      "the imaging waveforms to approved users."), ("prospective", "future"), ("planned", "will")),
])
def test_equivalent_governors_in_one_sentence_report_the_nearer_line(doc, reported, beside):
    # Both classes in the snippet's own sentence: the governor on the line
    # nearer the snippet is reported, the other listed beside it.
    out = _run(doc, [("x", "the imaging waveforms to approved users")], {"x": "Waveforms are released."})
    text, _m = _bundle(doc)
    [flag] = out["flags"]
    assert (flag["class"], flag["marker"]) == reported
    assert flag["source_line"] == _line(text, "in future release" if reported[1] == "future" else "will release")
    assert [(e["class"], e["marker"], e["via"]) for e in flag["equivalent_governors"]] == [
        (*beside, "sentence")]


@pytest.mark.parametrize("doc,reported,beside", [
    # #3488: the governor right after the snippet's last line is nearer than
    # one three lines above its first; measured from the first line alone it
    # was the farther. Its class ("prospective") sorts after the other's, so
    # the class name cannot be what reports it.
    (("The consortium will,\nafter careful review\nby the board,\nthe imaging waveforms\n"
      "and the labels\nand the reports\nand the codes\nin future to approved users."),
     ("prospective", "future", "in future to"), ("planned", "will", "The consortium will")),
    # The mirror: the governor above is the farther, the one below nearer.
    (("In future,\nafter careful review\nby the board,\nthe imaging waveforms\n"
      "and the labels\nand the reports\nand the codes\nwill go to approved users."),
     ("planned", "will", "will go to"), ("prospective", "future", "In future")),
])
@pytest.mark.parametrize("snippet", [
    "the imaging waveforms and the labels and the reports and the codes",
    # A quote in parts: the span ends at its last part's end, not its first's.
    "the imaging waveforms ... and the codes",
])
def test_line_distance_is_measured_from_the_snippets_span(doc, reported, beside, snippet):
    out = _run(doc, [("x", snippet)], {"x": "Waveforms are released."})
    text, _m = _bundle(doc)
    [flag] = out["flags"]
    assert flag["snippet_line"] == _line(text, "the imaging")
    assert (flag["class"], flag["marker"], flag["via"], flag["source_line"]) == (
        reported[0], reported[1], "sentence", _line(text, reported[2]))
    assert flag["equivalent_governors"] == [{"class": beside[0], "marker": beside[1], "via": "sentence",
                                             "source_line": _line(text, beside[2])}]


@pytest.mark.parametrize("heading,sentence_tail,reported,beside,via", [
    ("Future Data Releases", "will be released to approved users.",
     ("planned", "will"), ("prospective", "future"), "heading"),
    # The heading's class ("planned") also sorts first: only the via rank
    # reports the sentence's governor.
    ("Planned Data Releases", "are released in future to approved users.",
     ("prospective", "future"), ("planned", "planned"), "heading"),
    # #3468: the lead-in half of rule 1, a ':' clause above the snippet in
    # place of the heading, in both class orders.
    ("Future work includes:", "will be released to approved users.",
     ("planned", "will"), ("prospective", "future"), "lead-in"),
    ("The planned releases include:", "are released in future to approved users.",
     ("prospective", "future"), ("planned", "planned"), "lead-in"),
])
def test_a_sentence_governor_beats_a_nearer_heading_governor(heading, sentence_tail, reported, beside, via):
    # #3437: rule 1 of the ordering. The heading (or lead-in) sits one line
    # above the snippet and the sentence's marker two lines below it, so
    # line distance alone would report the heading; the sentence governor
    # is reported and the heading listed beside it.
    doc = f"{heading}\nThe imaging waveforms\nand the labels\n{sentence_tail}\n"
    out = _run(doc, [("x", "The imaging waveforms")], {"x": "Waveforms are released."})
    text, _m = _bundle(doc)
    [flag] = out["flags"]
    snippet_line = _line(text, "The imaging")
    assert flag["snippet_line"] == snippet_line
    assert (flag["class"], flag["marker"], flag["via"], flag["source_line"]) == (
        *reported, "sentence", snippet_line + 2)
    assert flag["equivalent_governors"] == [{"class": beside[0], "marker": beside[1], "via": via,
                                             "source_line": snippet_line - 1, "governor": heading}]


def test_the_plain_form_is_tried_first():
    # #3467: a snippet the plain form locates is located there, exactly as
    # before #3043, even where the linewrap-joined form holds a second
    # occurrence of it. Here the second (hyphen-wrapped) sentence carries no
    # marker, so trying the joined form first would find it, read it as an
    # unmarked occurrence and drop the flag the plain occurrence raises.
    doc = ("The consortium will release the imaging waveforms to approved users.\n"
           "Today the consortium releases the imag-\ning waveforms to approved users.")
    snippet = "the imaging waveforms to approved users"
    text, manifest = _bundle(doc)
    view = sc.BundleView(text, manifest)
    assert sc.HAYSTACK_FORMS[0] == "plain"
    [[(a, b)]] = view.locate("c002", snippet)
    assert text[a:b] == snippet
    assert text.index(snippet) == a
    out = _run(doc, [("x", snippet)], {"x": "The consortium releases the imaging waveforms."})
    assert _rules(out) == [("governor_outside_snippet", "x", "planned")]


@pytest.mark.parametrize("form", ["linewrap-joined", "joined-elided"])
def test_a_form_the_validator_would_not_build_is_refused(form, monkeypatch):
    # #3466: form_offsets checks its replay against the haystack receipts
    # itself builds, not against this module's copy of the join rule. Were
    # the validator to join an en-dash break too, the replay (which joins
    # hyphens only) no longer reproduces it and the form is refused.
    raw = "Partic\u2013\nipants were enrolled\n6.\nat two sites."
    real = rc.normalise_joined

    def joins_en_dash(text):
        return real(re.sub(r"(\w)\u2013[ \t]*\n[ \t]*(\w)", r"\1\2", text))
    assert sc.form_offsets(raw, form) is not None
    monkeypatch.setattr(rc, "normalise_joined", joins_en_dash)
    assert sc.form_offsets(raw, form) is None
    # The forms that do not join are unaffected.
    assert sc.form_offsets(raw, "plain") is not None
    assert sc.form_offsets(raw, "artifact-line-elided") is not None


@pytest.mark.parametrize("doc,form", [
    # #789: a PDF extractor's hyphenated wrap inside the quoted words.
    ("The consortium will release the imag-\ning waveforms to approved users.", "linewrap-joined"),
    # #887: a lone section-number line inside the quoted words.
    ("The consortium will release the\n7.\nimaging waveforms to approved users.", "artifact-line-elided"),
    # Both at once.
    ("The consortium will release the\n7.\nimag-\ning waveforms to approved users.", "artifact-line-elided"),
])
def test_a_snippet_verified_only_across_a_joined_break_or_an_elided_line_is_located(doc, form):
    # #3043: such a snippet was counted unlocated, so its context was never
    # read; it is now located through that form's offset map, its raw span
    # covering the break or the elided line.
    snippet = "the imaging waveforms to approved users"
    text, manifest = _bundle(doc)
    view = sc.BundleView(text, manifest)
    assert rc.snippet_in(snippet, view.chunk_text("c002")) == (True, form)
    [[(a, b)]] = view.locate("c002", snippet)
    assert text[a:b] == doc[doc.rindex("the", 0, doc.index("imag")):doc.index(" users") + len(" users")]
    out = _run(doc, [("x", snippet)], {"x": "The consortium releases the imaging waveforms."})
    assert (out["counts"]["located"], out["counts"]["unlocated"]) == (1, 0)
    [flag] = out["flags"]
    assert (flag["rule"], flag["class"], flag["marker"], flag["via"]) == (
        "governor_outside_snippet", "planned", "will", "sentence")
    # The negative control: a value keeping the status is located, unflagged.
    kept = _run(doc, [("x", snippet)], {"x": "The consortium will release the imaging waveforms."})
    assert (kept["counts"]["located"], kept["flags"]) == (1, [])


@pytest.mark.parametrize("doc,form", [
    ("The consortium will release the imaging waveforms to approved users.", "plain"),
    ("The consortium will release the imag-\ning waveforms to approved users.", "linewrap-joined"),
    ("The consortium will release the\n7.\nimaging waveforms to approved users.", "artifact-line-elided"),
    # Both at once: this module tries the forms in `HAYSTACK_FORMS` order,
    # so the one that locates it is the both-transform form.
    ("The consortium will release the\n7.\nimag-\ning waveforms to approved users.", "joined-elided"),
])
def test_the_counts_say_which_haystack_form_located_each_snippet(doc, form):
    # #3406: a snippet located only across a joined break or an elided line
    # had its context read on the raw text holding the break or the line;
    # the counts and the summary say how many were.
    snippet = "the imaging waveforms to approved users"
    text, manifest = _bundle(doc)
    assert sc.BundleView(text, manifest).located_form("c002", snippet) == form
    out = _run(doc, [("x", snippet), ("x", "not in the chunk at all")],
               {"x": "The consortium releases the imaging waveforms."})
    assert out["counts"]["located_by_form"] == {f: int(f == form) for f in sc.HAYSTACK_FORMS}
    if form == "plain":
        assert "joined or elided" not in out["summary"]
    else:
        assert f"1 located (1 only through a joined or elided form: {form} 1)" in out["summary"]


def test_the_summary_totals_snippets_not_forms_when_several_need_a_non_plain_form():
    # #3738: every other fixture has one non-plain snippet in one form, where
    # the snippet total and the number of distinct forms coincide. Here two
    # snippets need the joined form and one the elided form, beside one plain
    # snippet: the total is 3 (snippets), not 2 (forms), and each form keeps
    # its own count.
    doc = ("The consortium will release the imag-\ning waveforms to approved users. "
           "Each site will de-\nidentify the retinal photographs before transfer. "
           "The team will store the\n7.\ncalibration logs on a secure server. "
           "Plain text locates this sentence directly.")
    snippets = ["the imaging waveforms to approved users",
                "will deidentify the retinal photographs",
                "store the calibration logs on a secure server",
                "Plain text locates this sentence directly"]
    text, manifest = _bundle(doc)
    view = sc.BundleView(text, manifest)
    assert [view.located_form("c002", s) for s in snippets] == [
        "linewrap-joined", "linewrap-joined", "artifact-line-elided", "plain"]
    out = _run(doc, [("x", s) for s in snippets], {"x": "Released."})
    assert out["counts"]["located_by_form"] == {
        "plain": 1, "linewrap-joined": 2, "artifact-line-elided": 1, "joined-elided": 0}
    assert ("4 located (3 only through a joined or elided form: "
            "linewrap-joined 2, artifact-line-elided 1)") in out["summary"]


def test_only_located_snippets_are_counted_by_form():
    # Unlocated, indeterminate and unverified snippets name no form: the
    # tally sums to `located`.
    doc = "The team will harmonise records to a common model. " * (sc.MAX_PART_MATCHES + 1)
    out = _run(doc, [("x", "harmonise records to a common model"), ("x", "absent from the chunk")],
               {"x": "Records are harmonised."})
    assert out["counts"]["indeterminate"] == 1 and out["counts"]["not_verified"] == 1
    assert out["counts"]["located_by_form"] == dict.fromkeys(sc.HAYSTACK_FORMS, 0)
    text, manifest = _bundle("Nothing here.")
    assert sc.BundleView(text, manifest).located_form("c002", "absent from the chunk") is None


FORM_DOCS = {
    "plain": "The consortium will release the imaging waveforms to approved users.",
    "linewrap-joined": "The consortium will release the imag-\ning waveforms to approved users.",
    "artifact-line-elided": "The consortium will release the\n7.\nimaging waveforms to approved users.",
    "joined-elided": "The consortium will release the\n7.\nimag-\ning waveforms to approved users.",
}


@pytest.mark.parametrize("form", sc.HAYSTACK_FORMS)
def test_each_flag_names_the_form_its_snippet_was_located_through(form):
    # #3708: the counts said how many snippets a joined or elided form
    # located, not which flags were read there. Each flag now names a
    # non-plain form, both rules' flags, and a plain one names none.
    doc = FORM_DOCS[form]
    pairs = [("x", "the imaging waveforms to approved users"),        # governor_outside_snippet
             ("y", "will release the imaging waveforms")]            # modal_dropped
    out = _run(doc, pairs, {"x": "The consortium releases the imaging waveforms.", "y": "Released."})
    assert sorted(f["rule"] for f in out["flags"]) == ["governor_outside_snippet", "modal_dropped"]
    named = {f["rule"]: f.get("located_form") for f in out["flags"]}
    if form == "plain":
        assert named == {"governor_outside_snippet": None, "modal_dropped": None}
        assert all("located_form" not in f for f in out["flags"]) and out["form_located"] == []
        assert "read through a joined or elided form" not in out["summary"]
    else:
        assert named == {"governor_outside_snippet": form, "modal_dropped": form}
        assert [(u["slot"], u["form"]) for u in out["form_located"]] == [("x", form), ("y", form)]
        assert f"2 flags read through a joined or elided form: {form} 2" in out["summary"]
        assert any(f"located_form={form}" in line for line in sc.report_lines(out))
    assert out["counts"]["flags_by_located_form"] == {
        f: 2 * int(f == form) for f in sc.HAYSTACK_FORMS if f != "plain"}


def test_a_label_slot_flag_names_its_form_too():
    out = _run(FORM_DOCS["linewrap-joined"], [("creators[0].name", "the imaging waveforms to approved users")],
               {"creators": [{"name": "The imaging waveforms"}]})
    assert out["flags"] == [] and [f["located_form"] for f in out["label_slot"]] == ["linewrap-joined"]
    assert out["counts"]["flags_by_located_form"]["linewrap-joined"] == 1


def test_an_unlocated_snippets_flag_names_no_form():
    # A modal_dropped flag reads only the snippet: where no form locates it,
    # neither its line nor any context was read, so no form is named.
    text, manifest = _bundle("Nothing here.")
    receipt = _receipt(text, [("x", "the data will be released")])
    view = sc.BundleView(text, manifest)
    view.verified = lambda cid, snippet: True       # verified by fiat; located by nothing
    out = sc.receipt_context(receipt, manifest, text, {"x": "Released."}, view=view)
    [flag] = out["flags"]
    assert flag["rule"] == "modal_dropped" and flag["snippet_line"] is None and "located_form" not in flag
    assert out["counts"]["unlocated"] == 1 and out["form_located"] == []


@pytest.mark.parametrize("form", sc.HAYSTACK_FORMS)
def test_rule_2_names_the_form_an_evidence_quotes_context_was_read_through(form):
    text, manifest = _bundle(FORM_DOCS[form])
    view = sc.BundleView(text, manifest)
    out = sc.review_status_expression(_review(("/description", [
        _claim("The waveforms are released.", "fact", quote="the imaging waveforms to approved users")])),
        view=view)
    [flag] = out["flags"]
    assert (flag["rule"], flag["via"], flag["marker"]) == ("planned_evidence_declared_fact", "sentence", "will")
    assert flag.get("located_form") == (None if form == "plain" else form)
    assert out["counts"]["quotes_located_by_form"] == {f: int(f == form) for f in sc.HAYSTACK_FORMS}
    assert ("read only through a joined or elided form" in out["summary"]) == (form != "plain")


@pytest.mark.parametrize("form", sc.HAYSTACK_FORMS)
def test_each_haystack_form_maps_to_the_validators_own_haystack(form):
    raw = ("Partic-\r\nipants were   enrolled\n6.\nat SITE-\n  One; “data” \\n were\n 12. \n"
           "shared-\nwith 100. partners\n7.")
    hay = {"plain": rc.normalise(raw), "linewrap-joined": rc.normalise_joined(raw),
           "artifact-line-elided": rc.normalise(rc.elide_artifact_lines(raw)),
           "joined-elided": rc.normalise_joined(rc.elide_artifact_lines(raw))}[form]
    norm, offs = sc.form_offsets(raw, form)
    assert norm == hay and len(offs) == len(norm)
    assert offs == sorted(offs)
    # Every folded word character comes from a raw character that folds to it.
    for ch, o in zip(norm, offs):
        if ch != " ":
            assert rc.normalise(raw[o]) == ch, (ch, raw[o])


@pytest.mark.parametrize("leaf", sorted(sc.LABEL_LEAVES))
def test_label_slots_are_reported_in_their_own_bucket(leaf):
    doc = "Anticipated Final Dataset\nContributing sites\nNorthern Hospital Network\n"
    out = _run(doc, [(f"creators[0].{leaf}", "Northern Hospital Network")],
               {"creators": [{leaf: "Northern Hospital Network"}]})
    assert out["flags"] == []
    assert _rules(out, "label_slot") == [("governor_outside_snippet", f"creators[0].{leaf}", "prospective")]
    assert out["counts"]["slots_flagged"] == {"value": 0, "label": 1}


@pytest.mark.parametrize("path,kind", [
    ("creators[0].name", "label"), ("/title", "label"), ("variables[2].label", "label"), ("/items/0/label", "label"),
    ("creators[0].affiliation", "value"), ("/description", "value"), ("labels", "value"), ("", "value"),
])
def test_slot_class_reads_the_leaf_of_a_dotted_path_or_a_json_pointer(path, kind):
    # The module and the PR name the label leaves `name`, `title` and `label`.
    assert sc.LABEL_LEAVES == {"name", "title", "label"}
    assert sc.slot_class(path) == kind


def test_semicolons_separate_terms_but_a_colon_lead_in_still_governs():
    terms = "Preferred terms:\nCare;Illness;Goals;Data Element;Hospitals"
    out = _run(terms, [("keywords", "Care;Illness")], {"keywords": ["Care", "Illness"]})
    assert out["counts"]["located"] == 1 and out["flags"] == []
    clauses = "The project will: collect records; standardize data to a common model; release data."
    [flag] = _run(clauses, [("x", "standardize data to a common model")], {"x": "Data are standardized."})["flags"]
    assert (flag["marker"], flag["via"]) == ("will", "sentence")


@pytest.mark.parametrize("doc,snippet,value", [
    # #3170: the ';'-clauses before the part are cut off as well as those
    # after it — a marker in an earlier independent clause, or in an
    # earlier term of a list, does not govern the part.
    ("The team will expand the network; records are standardized to a common model.",
     "records are standardized to a common model", "Records are standardized to a common model."),
    ("Preferred terms:\nGoals;Care;Illness;Data Element;Hospitals", "Care;Illness", ["Care", "Illness"]),
])
def test_a_semicolon_clause_before_the_part_does_not_govern_it(doc, snippet, value):
    out = _run(doc, [("keywords", snippet)], {"keywords": value})
    assert out["counts"]["located"] == 1 and out["flags"] == []


@pytest.mark.parametrize("earlier", [
    # #3211: a ':' inside a token of an earlier independent clause is not a
    # lead-in, so it does not bring that clause's marker back.
    "The team will host files at https://example.org",
    "The team will meet at 10:30 daily",
    "The team will balance sites (see ratio 3:1)",
    # A ':' in a later clause than the first is not the sentence's lead-in.
    "Records are kept; the team will add notes: more sites",
])
def test_a_colon_that_ends_no_lead_in_does_not_bring_back_an_earlier_clause(earlier):
    doc = earlier + "; records are standardized to a common model."
    out = _run(doc, [("x", "records are standardized to a common model")],
               {"x": "Records are standardized to a common model."})
    assert out["counts"]["located"] == 1 and out["flags"] == []


def test_a_lead_in_colon_in_the_first_clause_governs_but_only_up_to_the_colon():
    # The lead-in is read up to its ':'; the rest of the first clause is an
    # independent term and its marker does not govern the part.
    [flag] = _run("Planned: sites; records are standardized to a common model.",
                  [("x", "records are standardized to a common model")], {"x": "Records are standardized."})["flags"]
    assert (flag["marker"], flag["via"]) == ("planned", "sentence")
    out = _run("Scope: the team will expand the network; records are standardized to a common model.",
               [("x", "records are standardized to a common model")], {"x": "Records are standardized."})
    assert out["counts"]["located"] == 1 and out["flags"] == []


def test_a_parenthesised_letter_enumeration_is_followed_back_to_its_lead_in():
    # The "(a)" form the module docstring names, beside "A)" and "1)".
    doc = "The project will (a) collect records; (b) standardize data to a common model; (c) release data."
    [flag] = _run(doc, [("x", "standardize data to a common model")], {"x": "Data are standardized."})["flags"]
    assert (flag["marker"], flag["via"]) == ("will", "enumeration")


def test_an_enumeration_after_the_part_does_not_govern_it():
    # Items do not govern their lead-in: the sentence is cut at the first
    # enumeration after the part, so the items' own "will" is not read.
    doc = "Records are standardized to a common model, and next year the team A) will publish; B) will release."
    out = _run(doc, [("x", "Records are standardized to a common model")], {"x": "Records are standardized."})
    assert out["counts"]["located"] == 1 and out["flags"] == []


def test_labels_that_are_not_consecutive_are_not_an_enumeration():
    # An inline enumeration is a run of consecutive labels: site "A)" and
    # site "C)" are names, so the sentence, not an item, is the context.
    doc = "Enrolment will expand at site A) and records from site C) are standardized to a common model."
    [flag] = _run(doc, [("x", "records from site C) are standardized to a common model")],
                  {"x": "Records are standardized."})["flags"]
    assert (flag["marker"], flag["via"]) == ("will", "sentence")


def test_a_repeated_snippet_is_flagged_only_when_every_occurrence_is_governed():
    one = "The team will harmonise records to a common model."
    record = {"x": "Records are harmonised to a common model."}
    assert len(_run(one, [("x", "harmonise records to a common model")], record)["flags"]) == 1
    both = one + " Separately, the archive can harmonise records to a common model today."
    assert _run(both, [("x", "harmonise records to a common model")], record)["flags"] == []


TRAILING = ("Nursing flowsheets\n\nPlanned Collection Streams\nWaveform telemetry\n\n\n"
            "{second} Dataset\nWaveform telemetry")
TRAILING_SNIPPET = "Nursing flowsheets...Waveform telemetry"


@pytest.mark.parametrize("second,flagged", [("Current Released", False), ("Planned Future", True)])
def test_a_later_part_matched_twice_is_governed_only_when_every_ordered_choice_is(second, flagged):
    # #3266: the trailing part occurs under a status heading and again under
    # a counter-heading. The first part's earliest completion is the
    # governed row; the other row is an equally admissible occurrence, so
    # the planned status is not carried by every occurrence.
    doc = TRAILING.format(second=second)
    record = {"x": "Nursing flowsheets and waveform telemetry."}
    out = _run(doc, [("x", TRAILING_SNIPPET)], record)
    assert out["counts"]["located"] == 1
    assert bool(_rules(out)) is flagged
    text, manifest = _bundle(doc)
    view = sc.BundleView(text, manifest)
    review = _review(("/x", [_claim("Nursing flowsheets and waveform telemetry.", "fact",
                                    quote=TRAILING_SNIPPET)]))
    flags = sc.review_status_expression(review, view=view)["flags"]
    assert [f["rule"] for f in flags] == (["planned_evidence_declared_fact"] if flagged else [])


def test_an_ungoverned_occurrence_past_the_fiftieth_is_read():
    governed = "The team will harmonise records to a common model. " * 50
    record = {"x": "Records are harmonised to a common model."}
    snippet = "harmonise records to a common model"
    assert len(_run(governed, [("x", snippet)], record)["flags"]) == 1
    doc = governed + "Separately, the archive can harmonise records to a common model today."
    out = _run(doc, [("x", snippet)], record)
    assert out["counts"]["located"] == 1 and out["flags"] == []


def test_a_part_matched_past_the_cap_is_indeterminate_not_flagged():
    doc = "The team will harmonise records to a common model. " * (sc.MAX_PART_MATCHES + 1)
    record = {"x": "Records are harmonised to a common model."}
    out = _run(doc, [("x", "harmonise records to a common model")], record)
    assert out["flags"] == []
    assert (out["counts"]["located"], out["counts"]["unlocated"], out["counts"]["indeterminate"]) == (0, 0, 1)
    assert "1 indeterminate" in out["summary"]
    text, manifest = _bundle(doc)
    review = _review(("/x", [_claim("Records are harmonised.", "fact", quote="harmonise records to a common model")]))
    rule2 = sc.review_status_expression(review, view=sc.BundleView(text, manifest))
    assert rule2["flags"] == [] and rule2["counts"]["indeterminate_quotes"] == 1
    assert rule2["counts"]["unlocated_quotes"] == 0 and "1 indeterminate" in rule2["summary"]
    # At the cap itself every occurrence is read, and all are governed.
    at_cap = "The team will harmonise records to a common model. " * sc.MAX_PART_MATCHES
    assert len(_run(at_cap, [("x", "harmonise records to a common model")], record)["flags"]) == 1


NESTED = "The consortium A) {a} imaging; B) {b} (a) {ia}waveform telemetry; (b) standardized records; C) {c} records."
NESTED_ITEMS = {"a": "acquires", "b": "maintains", "ia": "", "c": "shares"}


@pytest.mark.parametrize("change,flagged", [
    ({}, False),
    ({"a": "will acquire"}, False),            # an outer sibling item's marker (the #3266 case)
    ({"c": "will share"}, False),              # an outer item after the nested list
    ({"ia": "will add "}, False),              # an inner sibling item's marker
    ({"b": "will maintain"}, True),            # the containing item governs its sub-items
])
def test_a_nested_enumeration_inherits_its_containing_items_governor_and_no_siblings(change, flagged):
    doc = NESTED.format(**{**NESTED_ITEMS, **change})
    record = {"x": "Records are standardized."}
    out = _run(doc, [("x", "standardized records")], record)
    assert out["counts"]["located"] == 1
    assert _rules(out) == ([("governor_outside_snippet", "x", "planned")] if flagged else [])
    text, manifest = _bundle(doc)
    review = _review(("/x", [_claim("Records are standardized.", "fact", quote="standardized records")]))
    flags = sc.review_status_expression(review, view=sc.BundleView(text, manifest))["flags"]
    assert [f["rule"] for f in flags] == (["planned_evidence_declared_fact"] if flagged else [])


def test_a_nested_enumeration_inherits_the_sentences_governing_clause():
    doc = NESTED.format(**NESTED_ITEMS).replace("The consortium A) acquires", "The consortium will A) acquire")
    out = _run(doc, [("x", "standardized records")], {"x": "Records are standardized."})
    [flag] = out["flags"]
    assert (flag["class"], flag["marker"], flag["via"]) == ("planned", "will", "enumeration")


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
    # #3212: a run is read from its own files, so a file option beside
    # --label/--project is refused rather than silently ignored.
    for extra in (["--bundle", str(bundle)], ["--record", str(tmp_path / "record.yaml")],
                  ["--final", str(tmp_path / "record.yaml")], ["--chunk-manifest", str(tmp_path / "study_chunks.yaml")]):
        ignored = CliRunner().invoke(cli, ["receipts", "status-context", "--label", "L", "--project", "P", *extra])
        assert ignored.exit_code == 2 and f"{extra[0]} apply to --receipt" in ignored.output, (extra, ignored.output)
    # #3253: --method names a run's directory family, which --receipt does
    # not read; beside the named files it is refused, not ignored.
    method = CliRunner().invoke(cli, args + ["--method", "claudecode_api"])
    assert method.exit_code == 2 and "--method" in method.output, method.output
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
    breaks = "a\nb\r\nc\rd\x0be\x0cf\x1cg\x85h\u2028i\u2029j"
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
    # #3212: a chunk manifest without the bundle it chunks is refused, not ignored.
    (tmp_path / "chunks.yaml").write_text("chunks: []", encoding="utf-8")
    lone = CliRunner().invoke(cli, ["review", "status-expression", "--audit", str(tmp_path / "audit.json"),
                                    "--chunk-manifest", str(tmp_path / "chunks.yaml")])
    assert lone.exit_code == 2 and "--chunk-manifest is read only with --bundle" in lone.output
    with pytest.raises(ValueError, match="give --bundle too"):
        sc.file_status_expression(tmp_path / "audit.json", chunk_manifest=tmp_path / "chunks.yaml")
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


#: The five committed receipt snippets that were unlocated before #3043:
#: each verifies only across a hyphenated line break (#3406).
JOINED_BEFORE_3043 = [
    ("claudecode_agent", "2026-08-28d_claude-opus-5-api-generic-v7_rep1", "AI_READI"),
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep2", "VOICE"),
    ("claudecode_api", "2026-09-04d_claude-opus-5-api-generic-v8_rep1", "VOICE"),
    ("claudecode_api", "2026-09-04e_claude-opus-5-api-generic-v8_rep1", "VOICE"),
    ("claudecode_api", "2026-09-04f_claude-opus-5-api-generic-v8_rep2", "VOICE"),
]


@pytest.mark.corpus   # reads committed runs, two of them from git blobs; the main-branch lane (#1203)
@pytest.mark.parametrize("method,label,project", JOINED_BEFORE_3043)
def test_replay_the_snippets_unlocated_before_3043_report_the_joined_form(method, label, project):
    core = ROOT / "data" / "d4d_concatenated" / f"{method}_core" / label
    receipt = core / f"{project}_coverage_receipt.yaml"
    if not receipt.exists():
        pytest.skip(f"{label} not on disk")
    out = sc.run_status_context(core / f"{project}_provenance.yaml", receipt,
                                ROOT / "data" / "d4d_concatenated" / method / label / f"{project}_d4d.yaml")
    assert out["checked"], out.get("reason")
    by_form = out["counts"]["located_by_form"]
    assert out["counts"]["unlocated"] == 0
    assert {f: n for f, n in by_form.items() if f != "plain"} == {
        "linewrap-joined": 1, "artifact-line-elided": 0, "joined-elided": 0}
    assert sum(by_form.values()) == out["counts"]["located"]
    assert "(1 only through a joined or elided form: linewrap-joined 1)" in out["summary"]


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


# ------------------------------------------------ run mode's refusals (#3234)
def _run_dir(tmp_path, *, chunk_count_offset=0, snapshot="usable"):
    """A run laid out as `run_status_context` reads it: a provenance record
    declaring the bundle's path, md5 and chunking rule (and the chunk count
    it cites), the coverage receipt beside it, an optional phase-1 snapshot
    under `intermediate/`, and the final record."""
    text, _m = _bundle(ENUMERATION)
    bundle = tmp_path / "study.txt"
    bundle.write_text(text, encoding="utf-8")
    manifest = chunking.manifest_from_bytes(text.encode("utf-8"), bundle.name, chunking.DEFAULT_RULE)
    core = tmp_path / "core"
    (core / "intermediate").mkdir(parents=True)
    provenance = core / "P_provenance.yaml"
    provenance.write_text("# header\n" + yaml.safe_dump({"run": {"project": "P"}, "inputs": {
        "bundle_path": str(bundle), "bundle_md5": _md5(text),
        "chunks": {"rule": chunking.DEFAULT_RULE, "bundle_name": bundle.name,
                   "chunk_count": manifest["chunk_count"] + chunk_count_offset}}}), encoding="utf-8")
    receipt = core / "P_coverage_receipt.yaml"
    receipt.write_text(yaml.safe_dump(_receipt(text, [(D_SLOT, D_SNIPPET)])), encoding="utf-8")
    dropped = {"preprocessing_strategies": [{"preprocessing_details": "Data are standardized."}]}
    kept = {"preprocessing_strategies": [{"preprocessing_details": "Data will be standardized."}]}
    if snapshot == "usable":
        (core / "intermediate" / "P_full.yaml").write_text(yaml.safe_dump(dropped), encoding="utf-8")
    elif snapshot is not None:
        (core / "intermediate" / "P_full.yaml").write_text(snapshot, encoding="utf-8")
    # The final record keeps the status: read in the snapshot's place, it
    # would report nothing, which is why an unusable snapshot must refuse.
    full = tmp_path / "P_d4d.yaml"
    full.write_text(yaml.safe_dump(kept), encoding="utf-8")
    return provenance, receipt, full


def test_run_mode_reads_the_snapshot_the_record_cites_chunk_count_for(tmp_path):
    out = sc.run_status_context(*_run_dir(tmp_path))
    assert out["checked"] and out["value_basis"].startswith("phase-1 snapshot")
    assert [(f["rule"], f["slot"], f["final_expresses_status"]) for f in out["flags"]] == [
        ("governor_outside_snippet", D_SLOT, True)]


@pytest.mark.parametrize("offset", [1, -1])
def test_run_mode_refuses_bytes_its_rule_chunks_to_another_count_than_the_record_cites(tmp_path, offset):
    out = sc.run_status_context(*_run_dir(tmp_path, chunk_count_offset=offset))
    assert out["checked"] is False and "not the" in out["reason"] and "it cites" in out["reason"]
    assert "flags" not in out


@pytest.mark.parametrize("snapshot", ["- a list\n- not a record\n", "key: [unclosed\n", "", "just a scalar\n"])
def test_run_mode_refuses_a_snapshot_present_but_not_usable_rather_than_reading_the_final_record(tmp_path, snapshot):
    out = sc.run_status_context(*_run_dir(tmp_path, snapshot=snapshot))
    snap = tmp_path / "core" / "intermediate" / "P_full.yaml"
    assert out["checked"] is False and f"snapshot {snap} is present but not usable" in out["reason"], out
    assert "flags" not in out and "value_basis" not in out


def test_run_mode_without_a_snapshot_reads_the_final_record(tmp_path):
    # The agentic path writes no snapshot; the full record is then the
    # record the receipt addresses, which here keeps the status.
    out = sc.run_status_context(*_run_dir(tmp_path, snapshot=None))
    assert out["checked"] and out["value_basis"].startswith("record ") and out["flags"] == []


def test_every_file_option_says_which_mode_reads_it():
    # #3233: each option a mode refuses outside it says so in --help.
    receipts_cmd = cli.commands["receipts"].commands["status-context"]
    helps = {p.name: p.help for p in receipts_cmd.params}
    assert helps["method"].startswith("with --label/--project:"), helps["method"]  # #3253
    for name in ("bundle_file", "record_file", "final_file", "chunk_manifest"):
        assert helps[name].startswith("with --receipt:"), (name, helps[name])
    review_cmd = cli.commands["review"].commands["status-expression"]
    assert {p.name: p.help for p in review_cmd.params}["chunk_manifest"].startswith("with --bundle:")


# ------------------------------------------- one process, many receipts (#3709)
def _drifted_run(tmp_path, name, text):
    """A run whose bundle on disk has drifted from the bytes its record
    hashed; `bundle_bytes_for` is what recovers them (patched by the caller)."""
    run = tmp_path / name
    run.mkdir()
    provenance, receipt, full = _run_dir(run)
    record = yaml.safe_load(provenance.read_text(encoding="utf-8").split("\n", 1)[1])
    Path(record["inputs"]["bundle_path"]).write_text(text + "drifted since\n", encoding="utf-8")
    record["inputs"]["bundle_path"] = "data/study.txt"
    provenance.write_text("# header\n" + yaml.safe_dump(record), encoding="utf-8")
    return provenance, receipt, full


def test_run_mode_recovers_and_chunks_a_shared_drifted_bundle_once_per_process(tmp_path, monkeypatch):
    from data_sheets_schema import provenance as pv
    text, _m = _bundle(ENUMERATION)
    calls = {"git": 0, "chunk": 0, "view": 0}

    def recovered(rel, md5=None, sha256=None):
        calls["git"] += 1
        assert (rel, md5) == ("data/study.txt", _md5(text))
        return text.encode("utf-8"), {"commit": "c0ffee"}
    real_chunk, real_view = chunking.manifest_from_bytes, sc.BundleView

    def chunk(*a, **k):
        calls["chunk"] += 1
        return real_chunk(*a, **k)

    class View(real_view):
        def __init__(self, *a, **k):
            calls["view"] += 1
            super().__init__(*a, **k)
    runs = [_drifted_run(tmp_path, n, text) for n in ("rep1", "rep2", "rep3")]
    monkeypatch.setattr(pv, "bundle_bytes_for", recovered)
    monkeypatch.setattr(chunking, "manifest_from_bytes", chunk)
    monkeypatch.setattr(sc, "BundleView", View)
    outs = [sc.run_status_context(*r) for r in runs]
    assert calls == {"git": 1, "chunk": 1, "view": 1}
    assert all(o["checked"] and o["bundle_basis"]["source"] == "git blob" for o in outs), outs
    # A hit is the answer a fresh process gives.
    sc.clear_caches()
    fresh = sc.run_status_context(*runs[2])
    assert calls == {"git": 2, "chunk": 2, "view": 2}
    assert json.dumps(fresh, sort_keys=True, default=str) == json.dumps(outs[2], sort_keys=True, default=str)
    assert [f["slot"] for f in outs[0]["flags"]] == [D_SLOT]


def test_a_cached_manifest_is_a_copy_and_a_git_failure_is_not_cached(tmp_path, monkeypatch):
    from data_sheets_schema import provenance as pv
    text, _m = _bundle(ENUMERATION)
    raw = text.encode("utf-8")
    first = sc._chunked(raw, "study.txt", chunking.DEFAULT_RULE, chunking.manifest_from_bytes)
    first["chunks"].clear()
    assert sc._chunked(raw, "study.txt", chunking.DEFAULT_RULE, chunking.manifest_from_bytes)["chunks"]
    # A key over any YAML shape, keys of mixed types included, never raises.
    assert len({sc._key({1: "a", "b": 2}), sc._key(["a"]), sc._key("a")}) == 3
    # Another name is another manifest.
    assert sc._chunked(raw, "other.txt", chunking.DEFAULT_RULE, chunking.manifest_from_bytes)["bundle"] == "other.txt"
    answers = [pv.GitUnavailable("no git here"), (raw, {"commit": "c0ffee"})]

    def recovered(rel, md5=None, sha256=None):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer
    monkeypatch.setattr(pv, "bundle_bytes_for", recovered)
    run = _drifted_run(tmp_path, "rep1", text)
    refused = sc.run_status_context(*run)
    assert refused["checked"] is False and "no git here" in refused["reason"]
    assert sc.run_status_context(*run)["checked"] and answers == []


def test_the_same_bytes_and_name_under_another_rule_is_another_manifest():
    # #3775: the manifest key carries the rule. A record chunked under a
    # narrower window than another record of the same bundle and name must
    # not read the first record's chunk layout.
    text, _m = _bundle(ENUMERATION, "second document\n" * 8)
    raw = text.encode("utf-8")
    calls = []

    def build(*a):
        calls.append(a[2])
        return chunking.manifest_from_bytes(*a)
    narrow = {**chunking.DEFAULT_RULE, "max_lines": 3}
    wide = sc._chunked(raw, "study.txt", chunking.DEFAULT_RULE, build)
    small = sc._chunked(raw, "study.txt", narrow, build)
    assert calls == [chunking.DEFAULT_RULE, narrow]
    assert (wide["rule"], small["rule"]) == (chunking.DEFAULT_RULE, narrow)
    assert small["chunk_count"] > wide["chunk_count"]
    assert small == chunking.manifest_from_bytes(raw, "study.txt", narrow)
    # And each is still a hit under its own rule.
    assert sc._chunked(raw, "study.txt", narrow, build) == small and len(calls) == 2


def test_the_same_bytes_under_another_chunk_layout_is_another_view():
    # #3776: the view key carries each chunk's line range, not the bytes
    # alone. Two manifests of one bundle that cut it differently must each
    # get a view that reads their own chunks.
    text, _m = _bundle(ENUMERATION, "second document\n" * 8)
    raw = text.encode("utf-8")
    wide = chunking.manifest_from_bytes(raw, "study.txt", chunking.DEFAULT_RULE)
    narrow = chunking.manifest_from_bytes(raw, "study.txt", {**chunking.DEFAULT_RULE, "max_lines": 3})
    a, b = sc._shared_view(raw, text, wide), sc._shared_view(raw, text, narrow)
    assert a is not b
    for view, manifest in ((a, wide), (b, narrow)):
        assert {c["id"]: view.chunk_text(c["id"]) for c in manifest["chunks"]} == \
            {c["id"]: sc.BundleView(text, manifest).chunk_text(c["id"]) for c in manifest["chunks"]}
    assert sc._shared_view(raw, text, wide) is a and sc._shared_view(raw, text, narrow) is b


def test_records_that_differ_only_in_sha256_recover_their_bytes_separately(tmp_path, monkeypatch):
    # #3776: the recovered-bytes key carries sha256 as well as path and md5.
    # A record whose sha256 names other bytes must ask git again, not take
    # the first record's answer (which `bundle_bytes_for` would refuse).
    from data_sheets_schema import provenance as pv
    asked = []

    def recovered(rel, md5=None, sha256=None):
        asked.append(sha256)
        return (b"version " + sha256.encode(), {"commit": sha256[:6]})
    monkeypatch.setattr(pv, "bundle_bytes_for", recovered)
    absent = tmp_path / "gone.txt"
    base = {"bundle_path": "data/study.txt", "bundle_md5": "0" * 32}
    first = sc._record_bytes(absent, {**base, "bundle_sha256": "a" * 64})
    second = sc._record_bytes(absent, {**base, "bundle_sha256": "b" * 64})
    assert asked == ["a" * 64, "b" * 64]
    assert (first[0], second[0]) == (b"version " + b"a" * 64, b"version " + b"b" * 64)
    assert second[1]["commit"] == "bbbbbb"
    assert sc._record_bytes(absent, {**base, "bundle_sha256": "b" * 64})[0] == second[0] and len(asked) == 2


def test_the_corpus_diagnostic_tallies_each_project_by_form_and_lists_what_it_could_not_read(tmp_path):
    concat = tmp_path / "concat"

    def run(method, label, project, doc, value):
        text, _m = _bundle(doc)
        core, full_dir = concat / f"{method}_core" / label, concat / method / label
        core.mkdir(parents=True, exist_ok=True)
        full_dir.mkdir(parents=True, exist_ok=True)
        bundle = tmp_path / f"{label}_{project}.txt"
        bundle.write_text(text, encoding="utf-8")
        rule = chunking.DEFAULT_RULE
        count = chunking.manifest_from_bytes(text.encode("utf-8"), bundle.name, rule)["chunk_count"]
        (core / f"{project}_provenance.yaml").write_text("# header\n" + yaml.safe_dump({"run": {"project": project}, "inputs": {
            "bundle_path": str(bundle), "bundle_md5": _md5(text),
            "chunks": {"rule": rule, "bundle_name": bundle.name, "chunk_count": count}}}), encoding="utf-8")
        (core / f"{project}_coverage_receipt.yaml").write_text(yaml.safe_dump(_receipt(text, [
            ("x", "the imaging waveforms to approved users"), ("y", "absent from every chunk")])), encoding="utf-8")
        (full_dir / f"{project}_d4d.yaml").write_text(yaml.safe_dump({"x": value, "y": "y"}), encoding="utf-8")
    run("m_a", "L1", "P", FORM_DOCS["plain"], "Released.")
    run("m_a", "L2", "P", FORM_DOCS["linewrap-joined"], "Released.")
    run("m_b", "L1", "Q", FORM_DOCS["artifact-line-elided"], "It will be released.")
    (concat / "m_b_core" / "L2").mkdir(parents=True)
    (concat / "m_b_core" / "L2" / "Q_coverage_receipt.yaml").write_text("chunks: []\n", encoding="utf-8")
    before = _tree_hashes(tmp_path)
    out = sc.corpus_status_context(concat)
    assert _tree_hashes(tmp_path) == before and out["gating"] is False
    p, q = out["projects"]["P"], out["projects"]["Q"]
    assert p["unchecked"] == [], p["unchecked"]
    assert (p["receipts"], p["checked"], p["located"], p["unlocated"]) == (2, 2, 2, 0)
    assert p["located_by_form"] == {"plain": 1, "linewrap-joined": 1, "artifact-line-elided": 0, "joined-elided": 0}
    assert p["flags_by_located_form"] == {"linewrap-joined": 1, "artifact-line-elided": 0, "joined-elided": 0}
    assert [(u["receipt"], u["slot"], u["form"]) for u in p["form_located_snippets"]] == [
        ("m_a_core/L2/P_coverage_receipt.yaml", "x", "linewrap-joined")]
    assert (q["receipts"], q["checked"], q["located_by_form"]["artifact-line-elided"]) == (2, 1, 1)
    assert q["flags_by_located_form"]["artifact-line-elided"] == 0      # the value keeps "will"
    [unchecked] = q["unchecked"]
    assert unchecked["receipt"] == "m_b_core/L2/Q_coverage_receipt.yaml" and "no provenance record" in unchecked["reason"]
    assert out["totals"]["receipts"] == 4 and out["totals"]["checked"] == 3
    assert out["totals"]["located_by_form"] == {"plain": 1, "linewrap-joined": 1, "artifact-line-elided": 1,
                                                "joined-elided": 0}
    lines = sc.corpus_report_lines(out)
    assert all(len(line.splitlines()) == 1 for line in lines)
    assert any(line.startswith("   · linewrap-joined P: m_a_core/L2/P_coverage_receipt.yaml") for line in lines)
    assert any(line.startswith("   · unchecked Q: m_b_core/L2/Q_coverage_receipt.yaml") for line in lines)


#: #3809: a receipt with more unlocated and form-located snippets than a
#: list carries (3 and 2 past the cap).
OVER_CAP = {"unlocated": sc.LISTED_PER_RECEIPT + 3, "form_located": sc.LISTED_PER_RECEIPT + 2}


def _over_cap_pairs():
    joined = [(f"j{i}", "the imaging waveforms to approved users") for i in range(OVER_CAP["form_located"])]
    absent = [(f"u{i}", f"absent phrase number {i}") for i in range(OVER_CAP["unlocated"])]
    return joined + absent, {slot: "Released." for slot, _q in joined + absent}


def test_a_cut_snippet_list_says_how_many_it_left_out(monkeypatch):
    # #3809: the lists stop at LISTED_PER_RECEIPT while the counts are
    # complete; the omitted count, the summary and the report say so.
    monkeypatch.setattr(sc.BundleView, "verified", lambda self, cid, snippet: True)
    pairs, record = _over_cap_pairs()
    out = _run(FORM_DOCS["linewrap-joined"], pairs, record)
    assert out["counts"]["unlocated"] == OVER_CAP["unlocated"]
    assert out["counts"]["located_by_form"]["linewrap-joined"] == OVER_CAP["form_located"]
    assert (len(out["unlocated"]), out["unlocated_omitted"]) == (sc.LISTED_PER_RECEIPT, 3)
    assert (len(out["form_located"]), out["form_located_omitted"]) == (sc.LISTED_PER_RECEIPT, 2)
    assert (f"3 unlocated and 2 form-located snippet(s) not listed (at most {sc.LISTED_PER_RECEIPT}"
            in out["summary"])
    assert any(line.startswith("   · 3 more unlocated not listed") for line in sc.report_lines(out))


def test_a_list_within_the_cap_omits_nothing_and_says_nothing():
    out = _run(FORM_DOCS["linewrap-joined"], [("x", "the imaging waveforms to approved users")], {"x": "Released."})
    assert (out["unlocated_omitted"], out["form_located_omitted"]) == (0, 0)
    assert "not listed" not in out["summary"]
    assert not any("not listed" in line for line in sc.report_lines(out))


def test_the_corpus_diagnostic_says_how_many_snippets_its_lists_left_out(tmp_path, monkeypatch):
    # #3809: the corpus lists concatenate each receipt's capped list, so the
    # omitted counts are summed per project and in the totals and printed.
    monkeypatch.setattr(sc.BundleView, "verified", lambda self, cid, snippet: True)
    concat = tmp_path / "concat"
    pairs, record = _over_cap_pairs()
    text, _m = _bundle(FORM_DOCS["linewrap-joined"])
    bundle = tmp_path / "P.txt"
    bundle.write_text(text, encoding="utf-8")
    rule = chunking.DEFAULT_RULE
    count = chunking.manifest_from_bytes(text.encode("utf-8"), bundle.name, rule)["chunk_count"]
    for label in ("L1", "L2"):
        core, full_dir = concat / "m_core" / label, concat / "m" / label
        core.mkdir(parents=True)
        full_dir.mkdir(parents=True)
        (core / "P_provenance.yaml").write_text("# header\n" + yaml.safe_dump({"run": {"project": "P"}, "inputs": {
            "bundle_path": str(bundle), "bundle_md5": _md5(text),
            "chunks": {"rule": rule, "bundle_name": bundle.name, "chunk_count": count}}}), encoding="utf-8")
        (core / "P_coverage_receipt.yaml").write_text(yaml.safe_dump(_receipt(text, pairs)), encoding="utf-8")
        (full_dir / "P_d4d.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")
    out = sc.corpus_status_context(concat)
    p = out["projects"]["P"]
    assert p["unchecked"] == [], p["unchecked"]
    assert p["unlocated"] == 2 * OVER_CAP["unlocated"]
    assert (len(p["unlocated_snippets"]), p["unlocated_snippets_omitted"]) == (2 * sc.LISTED_PER_RECEIPT, 6)
    assert (len(p["form_located_snippets"]), p["form_located_snippets_omitted"]) == (2 * sc.LISTED_PER_RECEIPT, 4)
    t = out["totals"]
    assert (t["unlocated_snippets_omitted"], t["form_located_snippets_omitted"]) == (6, 4)
    lines = sc.corpus_report_lines(out)
    clause = f"6 unlocated and 4 form-located snippet(s) not listed below (at most {sc.LISTED_PER_RECEIPT}"
    assert clause in lines[1] and any(line.startswith("   P: ") and clause in line for line in lines)


def test_the_corpus_help_names_the_list_cap():
    cmd = cli.commands["receipts"].commands["status-context"]
    [opt] = [o for o in cmd.params if "--corpus" in o.opts]
    assert f"at most {sc.LISTED_PER_RECEIPT} of each per receipt" in opt.help


def test_the_corpus_flag_reads_the_corpus(tmp_path, monkeypatch):
    from data_sheets_schema import provenance as pv
    monkeypatch.setattr(pv, "CONCAT_DIR", tmp_path)
    ok = CliRunner().invoke(cli, ["receipts", "status-context", "--corpus"])
    assert ok.exit_code == 0, ok.output
    assert f"corpus under {tmp_path}" in ok.output and "0/0 receipts read" in ok.output
    as_json = CliRunner().invoke(cli, ["receipts", "status-context", "--corpus", "--json"])
    assert json.loads(as_json.output)["totals"]["receipts"] == 0


#: Every status-context option `--corpus` refuses, with a value it accepts
#: (None: an existing file). #3777: the test named three of the eight.
CORPUS_REFUSED = {"--method": "m", "--label": "L", "--project": "P", "--receipt": None, "--bundle": None,
                  "--record": None, "--final": None, "--chunk-manifest": None}


def test_the_corpus_refusal_list_is_every_option_but_the_mode_and_the_output_form():
    cmd = cli.commands["receipts"].commands["status-context"]
    options = {o for p in cmd.params for o in p.opts if o.startswith("--")}
    assert options - {"--corpus", "--json", "--help"} == set(CORPUS_REFUSED)


@pytest.mark.parametrize("option", sorted(CORPUS_REFUSED))
def test_the_corpus_flag_refuses_every_other_option(option, tmp_path, monkeypatch):
    from data_sheets_schema import provenance as pv
    monkeypatch.setattr(pv, "CONCAT_DIR", tmp_path)
    value = CORPUS_REFUSED[option]
    if value is None:
        value = tmp_path / "given.yaml"
        value.write_text("{}\n", encoding="utf-8")
    bad = CliRunner().invoke(cli, ["receipts", "status-context", "--corpus", option, str(value)])
    assert bad.exit_code == 2, bad.output
    assert f"--corpus reads every committed receipt; {option} would be ignored" in bad.output


@pytest.mark.corpus   # walks every committed coverage receipt; run on every PR and merge (#1361)
def test_the_committed_corpus_locates_every_snippet_and_names_the_five_joined_ones():
    concat = ROOT / "data" / "d4d_concatenated"
    if not any(concat.glob("*_core/*/*_coverage_receipt.yaml")):
        pytest.skip("no committed receipts on disk")
    out = sc.corpus_status_context(concat)
    t = out["totals"]
    assert t["checked"] == t["receipts"], [u for p in out["projects"].values() for u in p["unchecked"]]
    assert (t["unlocated"], t["indeterminate"]) == (0, 0)
    assert {f: n for f, n in t["located_by_form"].items() if f != "plain"} == {
        "linewrap-joined": 5, "artifact-line-elided": 0, "joined-elided": 0}
    assert sum(t["located_by_form"].values()) == t["located"]
    joined = sorted((u["receipt"].split("/")[0][:-len("_core")], u["receipt"].split("/")[1],
                     u["receipt"].split("/")[2][:-len("_coverage_receipt.yaml")])
                    for p in out["projects"].values() for u in p["form_located_snippets"])
    assert joined == sorted(JOINED_BEFORE_3043)
