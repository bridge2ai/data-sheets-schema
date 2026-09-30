"""Per-bundle attainability of rubric items (#2925).

The committed CHORUS file is the generator's output over the bytes all six
v7/v8 CHORUS reference records read; the validator re-derives it from those
bytes, refuses a hash that names other bytes, reads a drifted bundle from
its git blob, and never lets a pattern hit stand for support. Nothing here
may move a score.
"""
import copy
import hashlib
import json
from pathlib import Path
from unittest import mock

import pytest
import yaml

from data_sheets_schema import attainability as at
from data_sheets_schema import provenance as pv
from data_sheets_schema.chunking import DEFAULT_RULE
from data_sheets_schema.semantic_comparison import score_bases

ROOT = Path(__file__).resolve().parents[1]
CHORUS = "data/preprocessed/concatenated/CHORUS_preprocessed.txt"
CHORUS_MD5 = "9b2ef4b65d67957f79362266cab0bc7a"
CHORUS_FILE = ROOT / "data/attainability" / f"CHORUS_preprocessed_{CHORUS_MD5}.yaml"
AI_READI = "data/preprocessed/concatenated/AI_READI_preprocessed.txt"
AI_READI_V7_MD5 = "8abd7bf5389b562b95794d656af19392"
REFERENCE = {"rubric10": ROOT / "data/evaluation_llm/rubric10_semantic/reference_2026-09-12_cborg_runtime",
             "rubric20": ROOT / "data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime"}


def _entry(loaded, item_id):
    [entry] = [e for e in loaded.document["entries"] if e["item_id"] == item_id]
    return entry


def _chorus_evaluation(rubric="rubric10", name="CHORUS_v7_rep2_r10_rating1_evaluation.json"):
    return json.loads((REFERENCE[rubric] / name).read_text(encoding="utf-8"))


def _item(evaluation, item_id):
    return at.evaluation_items(evaluation)[item_id]


def _chorus_bytes():
    """The bytes the six records read, wherever they are now (#2914 will
    change the bundle on disk; this file stays about these bytes)."""
    return _git_or_skip(lambda: at.resolve_bytes(CHORUS, md5=CHORUS_MD5)[0])


def _git_or_skip(fn):
    try:
        return fn()
    except at.AttainabilityError as exc:
        if "shallow" in str(exc):
            pytest.skip("shallow clone; the committed versions are not here")
        raise


# -- the committed file -----------------------------------------------------

def test_the_committed_chorus_file_is_the_generators_output_and_validates():
    """`load` re-derives every deterministic entry from the pinned bytes under
    the recorded chunk rule, so every deterministic entry of a valid file is
    what its check writes (a curator or judge entry is hand-written, #3107).
    The committed file holds no such entry and is byte for byte what `derive`
    writes while the rubric text and chunk rule it pins are this checkout's;
    they stay pinned when this checkout's move on."""
    loaded = _git_or_skip(lambda: at.load(CHORUS_FILE))
    text = CHORUS_FILE.read_text(encoding="utf-8")
    assert text.startswith("# Attainability of rubric items")
    assert {e["method"].split(":")[0] for e in loaded.document["entries"]} == {"deterministic"}
    fresh = _git_or_skip(lambda: at.build_document(CHORUS, md5=CHORUS_MD5))
    if (fresh["rubrics"], fresh["chunk_rule"]) == (loaded.document["rubrics"], loaded.document["chunk_rule"]):
        assert at.dump(fresh) == text
    bundle = loaded.document["bundle"]
    raw = _chorus_bytes()
    assert (bundle["md5"], bundle["sha256"], bundle["bytes"]) == (
        CHORUS_MD5, hashlib.sha256(raw).hexdigest(), 35920)
    got = {(e["item_id"], e["route"]): (e["status"], e["method"], e["evidence"]["hit_count"])
           for e in loaded.document["entries"]}
    assert got == {
        ("E1.1", "doi_rrid"): ("not_stated_in_source", "deterministic:doi_rrid", 0),
        ("E4.1", None): ("unknown", "deterministic:ethics_review", 17),
        ("E4.4", None): ("not_stated_in_source", "deterministic:consent_text", 0),
        ("E6.1", None): ("unknown", "deterministic:version_string", 6),
        ("E10.2", None): ("not_stated_in_source", "deterministic:dataset_citation", 0),
    }


def test_zero_doi_rrid_and_consent_hits_are_recorded_with_method_and_pattern():
    loaded = at.load(CHORUS_FILE)
    for item_id, check in (("E1.1", "doi_rrid"), ("E4.4", "consent_text"), ("E10.2", "dataset_citation")):
        entry = _entry(loaded, item_id)
        assert entry["evidence"] == {"pattern": at.CHECKS_BY_NAME[check].pattern, "hit_count": 0, "snippets": []}
        assert entry["status"] == "not_stated_in_source"
    assert _entry(loaded, "E1.1")["route"] == "doi_rrid"       # the URI route stays open
    assert "DOI/RRID route only" in _entry(loaded, "E1.1")["note"]


def test_the_irb_lines_give_unknown_never_supported():
    """The four CHORUS 'IRB' lines are a training curriculum; a pattern hit
    is not evidence, so the entry stays unknown and lists them."""
    loaded = at.load(CHORUS_FILE)
    lines = _chorus_bytes().decode("utf-8").split("\n")
    irb = [n for n, line in enumerate(lines, 1) if "IRB" in line]
    assert irb == [647, 651, 664, 666]
    entry = _entry(loaded, "E4.1")
    assert entry["status"] == "unknown"
    listed = {s["lines"][0]: s for s in entry["evidence"]["snippets"]}
    for n in irb:
        assert listed[n]["sha256"] == hashlib.sha256(lines[n - 1].encode("utf-8")).hexdigest()
    assert not any(e["status"] in at.SUPPORT_STATUSES for e in loaded.document["entries"])
    # Even text that plainly states approval stays unknown by this route.
    _, text_lines = at._lines_by_chunk("IRB approval was obtained (protocol 42).\n", DEFAULT_RULE)
    assert at.deterministic_entry(at.CHECKS_BY_NAME["ethics_review"], text_lines)["status"] == "unknown"


def test_chunk_ids_are_the_committed_manifests():
    manifest = yaml.safe_load((ROOT / "data/preprocessed/chunks/CHORUS_chunks.yaml").read_text())
    if manifest["bundle_md5"] != CHORUS_MD5:
        pytest.skip("the chunk manifest now describes a later CHORUS bundle")
    spans = {c["id"]: c["lines"] for c in manifest["chunks"]}
    for entry in at.load(CHORUS_FILE).document["entries"]:
        for snip in entry["evidence"]["snippets"]:
            first, last = spans[snip["chunk"]]
            assert first <= snip["lines"][0] <= snip["lines"][1] <= last


# -- refusals ---------------------------------------------------------------

_NO_VERSION = "bundle: neither the file on disk nor any committed version"
_NO_GIT = "bundle: the file on disk is not the pinned bytes and git could not supply a committed version"


def _tampered_hash_problems(field):
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    value = doc["bundle"][field]
    doc["bundle"][field] = ("0" if value[0] != "0" else "1") + value[1:]
    problems, loaded = at.validate_text(at.dump(doc))           # no name: the bytes alone refuse it
    assert loaded is None, "accepted"
    return problems


@pytest.mark.parametrize("field", ["md5", "sha256"])
def test_a_tampered_bundle_hash_is_refused(field):
    """The file on disk does not hash to the tampered value, so the refusal
    holds with or without git. That no committed version does either needs
    git to say: a shallow clone refuses on the first ground alone (#3135),
    and the second is then not observable here."""
    problems = _tampered_hash_problems(field)
    if any(p.startswith(_NO_GIT) and "shallow" in p for p in problems):
        pytest.skip("shallow clone: refused, but the committed versions are not here to search")
    assert any(p.startswith(_NO_VERSION) for p in problems), problems


@pytest.mark.parametrize("field", ["md5", "sha256"])
def test_a_tampered_bundle_hash_is_refused_where_git_cannot_answer(field):
    """#3135: the reproduction — git unavailable, as in a shallow clone. The
    hash is still refused, and the problem says git could not answer rather
    than that no committed version matches."""
    with mock.patch.object(pv, "bundle_bytes_for", side_effect=pv.GitUnavailable("shallow clone")):
        problems = _tampered_hash_problems(field)
    assert problems == [f"{_NO_GIT}: shallow clone"]


def test_tampered_entries_and_snippets_are_refused():
    base = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))

    def refused(mutate):
        doc = copy.deepcopy(base)
        mutate(doc)
        problems, loaded = at.validate_text(at.dump(doc), at.file_name(doc))
        assert loaded is None
        return " | ".join(problems)

    def by_item(doc, item_id):
        return next(e for e in doc["entries"] if e["item_id"] == item_id)

    assert "differs in status" in refused(lambda d: by_item(d, "E4.1").update(status="supported"))
    assert "differs in evidence" in refused(lambda d: by_item(d, "E4.4")["evidence"].update(hit_count=1))
    assert "differs in evidence" in refused(
        lambda d: by_item(d, "E6.1")["evidence"]["snippets"][0].update(sha256="0" * 64))
    assert "differs in note" in refused(                                          # #3111
        lambda d: by_item(d, "E4.4").update(note=by_item(d, "E4.4")["note"] + " Also a curator agreed."))
    assert "decides rubric10 E4.1, not this item" in refused(
        lambda d: by_item(d, "E1.1").update(method="deterministic:ethics_review"))
    assert "decides rubric10 E1.1 route doi_rrid" in refused(lambda d: by_item(d, "E1.1").update(route=None))
    assert "second entry" in refused(lambda d: d["entries"].append(copy.deepcopy(by_item(d, "E4.4"))))
    assert "no item 'E11.1'" in refused(lambda d: by_item(d, "E4.4").update(item_id="E11.1"))
    assert "rubric rubric10" in refused(lambda d: d["rubrics"]["rubric10"].update(sha256="0" * 64))
    assert "rubrics must map" in refused(lambda d: d.update(rubrics=["rubric10"]))
    assert "must be names" in refused(lambda d: by_item(d, "E4.4").update(item_id=["E4.4"]))
    assert "bundle bytes 1 is not 35920" in refused(lambda d: d["bundle"].update(bytes=1))
    problems, _ = at.validate_text(CHORUS_FILE.read_text(encoding="utf-8"), "CHORUS_preprocessed_other.yaml")
    assert any("file name" in p for p in problems)
    dup = CHORUS_FILE.read_text(encoding="utf-8").replace("status: unknown\n", "status: unknown\n  status: supported\n", 1)
    problems, _ = at.validate_text(dup)
    assert problems and "duplicate mapping key" in problems[0]


@pytest.mark.parametrize("where, extra", [
    # The reviewer's reproduction (#3239): each was accepted as valid.
    ((), {"overrides": {"E4.4": "supported"}}),
    (("bundle",), {"note": "a note nobody reads"}),
    (("rubrics", "rubric10"), {"extra": 1}),
])
def test_a_key_the_format_does_not_name_is_refused_at_every_level(where, extra):
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    target = doc
    for key in where:
        target = target[key]
    target.update(extra)
    problems, loaded = _git_or_skip(lambda: at.validate_text(at.dump(doc), CHORUS_FILE.name))
    assert loaded is None
    [key] = extra
    label = {(): "", ("bundle",): "bundle: ", ("rubrics", "rubric10"): "rubric rubric10: "}[where]
    assert problems == [f"{label}unknown keys {key}"]


def test_a_value_equal_but_not_identical_to_the_generators_is_refused():
    """#3182: `False == 0`, `0.0 == 0`, `True == 1` and `45.0 == 45` hold in
    Python, so these hand edits, none of which `derive` writes, validated as
    the generator's output. Each is refused, and so is an entry that leaves
    out its `route`, which `credited` reads by key."""
    base = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))

    def refused(mutate):
        doc = copy.deepcopy(base)
        mutate(doc)
        problems, loaded = at.validate_text(at.dump(doc), at.file_name(doc))
        assert loaded is None, "accepted"
        return " | ".join(problems)

    def by_item(doc, item_id):
        return next(e for e in doc["entries"] if e["item_id"] == item_id)

    for stand_in in (False, 0.0):
        assert "E4.4: is not what deterministic:consent_text writes" in refused(
            lambda d: by_item(d, "E4.4")["evidence"].update(hit_count=stand_in))
    assert "differs in evidence" in refused(
        lambda d: by_item(d, "E4.1")["evidence"]["snippets"][0].update(lines=[45.0, 45]))
    for stand_in in (True, 1.0):
        assert "format must be d4d-attainability version 1" in refused(lambda d: d.update(format_version=stand_in))
    assert "bundle bytes 35920.0 is not 35920" in refused(lambda d: d["bundle"].update(bytes=35920.0))
    assert "missing keys route" in refused(lambda d: by_item(d, "E4.4").pop("route"))
    assert "unsupported chunk rule version: 2.0" in refused(lambda d: d["chunk_rule"].update(version=2.0))
    # The unedited file is accepted, so the refusals above are the edits'.
    assert at.validate_text(at.dump(base), at.file_name(base))[0] == []


def test_identical_is_type_exact_all_the_way_down():
    assert at.identical({"a": [1, {"b": None}]}, {"a": [1, {"b": None}]})
    for a, b in ((0, False), (1, True), (45, 45.0), ([45, 45], [45.0, 45]), ({"n": 0}, {"n": False}),
                 ({"a": 1}, {"a": 1, "b": 2}), ([1], [1, 1]), (None, "null")):
        assert not at.identical(a, b) and not at.identical(b, a), (a, b)


@pytest.mark.parametrize("rule, why", [
    ({}, "unsupported chunk rule version: None"),       # chunk_text reads {} as this checkout's default
    ({"max_lines": 400, "max_bytes": 48000}, "unsupported chunk rule version: None"),
    ({**DEFAULT_RULE, "version": 99}, "unsupported chunk rule version: 99"),
    ({**DEFAULT_RULE, "unit": "paragraph"}, "unsupported chunk rule unit: 'paragraph'"),
    ({**DEFAULT_RULE, "split": "nonsense"}, "unsupported chunk rule split: 'nonsense'"),
    ({**DEFAULT_RULE, "overlap": 0}, "unsupported chunk rule fields"),
    ({**DEFAULT_RULE, "max_lines": True}, "chunk rule max_lines must be a positive integer"),
    ({**DEFAULT_RULE, "version": 2.0}, "unsupported chunk rule version: 2.0"),        # #3182
    ({**DEFAULT_RULE, "version": True}, "unsupported chunk rule version: True"),
])
def test_a_chunk_rule_the_chunker_does_not_implement_is_refused(rule, why):
    """`chunk_text` reads only the two window bounds, and an empty rule as the
    default, so the first six cases chunk exactly like the pinned rule and
    were accepted before #3107: the file attested a rule nobody chunked
    under, or none. `max_lines: True` (the bound 1) is now refused as a
    rule rather than by the entries it happens to move. `version: 2.0`
    passed the version's `in (2, '2-custom')` test until #3182, and a
    `True` version is pinned refused with the test rewritten."""
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    doc["chunk_rule"] = rule
    problems, loaded = at.validate_text(at.dump(doc), at.file_name(doc))
    assert loaded is None
    assert problems == [f"chunk_rule is not a rule the chunker implements, written in full: {why}"]


def test_a_custom_chunk_rule_is_checked_under_its_own_bounds():
    """A `2-custom` rule is one the chunker implements, so it is accepted as a
    rule — and the chunk ids and hits are then re-derived under its bounds,
    which the committed entries were not written under."""
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    doc["chunk_rule"] = {**DEFAULT_RULE, "version": "2-custom", "max_lines": 100}
    problems, loaded = at.validate_text(at.dump(doc), at.file_name(doc))
    assert loaded is None
    assert problems and all("differs in evidence" in p for p in problems), problems


def test_curator_entries_are_verified_against_the_bytes_and_kept_on_rewrite(tmp_path):
    doc = at.build_document(CHORUS, md5=CHORUS_MD5)
    target = at.write_document(doc, tmp_path)
    written = yaml.safe_load(target.read_text(encoding="utf-8"))
    hits = next(e for e in written["entries"] if e["item_id"] == "E6.1")["evidence"]["snippets"]
    written["entries"] = [e for e in written["entries"] if e["item_id"] != "E6.1"] + [{
        "rubric": "rubric10", "item_id": "E6.1", "route": None, "status": "not_stated_in_source",
        "method": "curator", "evidence": {"snippets": hits},
        "note": "Every line is Python version control, a call date or a statistics banner."}]
    target.write_text(at.dump(written), encoding="utf-8")
    assert at.load(target).document["entries"][-1]["method"] == "curator"

    at.write_document(at.build_document(CHORUS, md5=CHORUS_MD5), tmp_path)   # regenerate
    entries = at.load(target).document["entries"]
    e61 = [e for e in entries if e["item_id"] == "E6.1"]
    assert [e["method"] for e in e61] == ["curator"]                          # kept, not overwritten
    assert len(entries) == len(at.CHECKS)

    def refused(entry):
        bad = {**written, "entries": [entry]}
        problems, loaded = at.validate_text(at.dump(bad))
        assert loaded is None
        return " | ".join(problems)

    curator = written["entries"][-1]
    assert "sha256 does not match" in refused({**curator, "evidence": {"snippets": [{**hits[0], "sha256": "0" * 64}]}})
    assert "not inside c003" in refused({**curator, "evidence": {"snippets": [{**hits[0], "lines": [1, 1]}]}})
    assert "needs at least one snippet" in refused({**curator, "status": "supported", "evidence": {"snippets": []}})
    assert "method must be" in refused({**curator, "method": "judge:"})
    assert "note must say" in refused({**curator, "note": " "})
    assert "missing keys route" in refused({k: v for k, v in curator.items() if k != "route"})   # #3182
    for chunk in (["c003"], {"id": "c003"}):                         # a crash before #3108
        assert "chunk must be a chunk id" in refused(
            {**curator, "evidence": {"snippets": [{**hits[0], "chunk": chunk}]}})

    # A kept reading was made under the file's chunk rule and rubric texts:
    # a rewrite that moves either is refused and leaves the file as it was.
    before = target.read_bytes()
    moved = copy.deepcopy(doc)
    moved["chunk_rule"] = {**doc["chunk_rule"], "max_lines": 100}
    with pytest.raises(at.AttainabilityError, match="another chunk_rule"):
        at.write_document(moved, tmp_path)
    moved = copy.deepcopy(doc)
    moved["rubrics"]["rubric10"] = {**doc["rubrics"]["rubric10"], "sha256": "0" * 64}     # #3111
    with pytest.raises(at.AttainabilityError, match="another rubric rubric10"):
        at.write_document(moved, tmp_path)
    assert target.read_bytes() == before


# -- where the bytes come from -----------------------------------------------

def test_resolution_reads_disk_first_then_the_committed_version(tmp_path):
    raw = b"bundle bytes\n"
    md5, sha = hashlib.md5(raw).hexdigest(), hashlib.sha256(raw).hexdigest()
    disk = tmp_path / "b.txt"
    disk.write_bytes(raw)
    with mock.patch.object(pv, "bundle_bytes_for", side_effect=AssertionError("git was asked")):
        assert at.resolve_bytes("data/b.txt", md5=md5, sha256=sha, disk=disk) == (
            raw, {"source": "file on disk", "path": "data/b.txt"})
    disk.write_bytes(b"drifted\n")
    entry = {"commit": "c" * 40, "date": "2026-09-01", "md5": md5, "sha256": sha, "matched_on": ["md5", "sha256"]}
    with mock.patch.object(pv, "bundle_bytes_for", return_value=(raw, entry)) as git:
        got, basis = at.resolve_bytes("data/b.txt", md5=md5, sha256=sha, disk=disk)
    assert got == raw and basis["source"] == "git blob" and basis["commit"] == "c" * 40
    git.assert_called_once_with("data/b.txt", md5=md5, sha256=sha)
    with mock.patch.object(pv, "bundle_bytes_for", side_effect=pv.GitUnavailable("shallow clone")):
        with pytest.raises(at.AttainabilityError, match="git could not supply"):
            at.resolve_bytes("data/b.txt", md5=md5, disk=disk)
    with mock.patch.object(pv, "bundle_bytes_for", return_value=None):
        with pytest.raises(at.AttainabilityError, match="hashes to md5"):
            at.resolve_bytes("data/b.txt", md5=md5, disk=disk)


def test_a_drifted_bundle_resolves_from_its_git_blob():
    """The v7 AI_READI records read 8abd7bf5; the bundle on disk is a later
    version, so the entry is checkable only from the committed blob."""
    assert hashlib.md5((ROOT / AI_READI).read_bytes()).hexdigest() != AI_READI_V7_MD5
    doc = _git_or_skip(lambda: at.build_document(AI_READI, md5=AI_READI_V7_MD5))
    assert doc["bundle"]["md5"] == AI_READI_V7_MD5
    problems, loaded = at.validate_text(at.dump(doc), at.file_name(doc))
    assert problems == []
    assert loaded.bundle_basis["source"] == "git blob"
    assert set(loaded.bundle_basis["matched_on"]) == {"md5", "sha256"}
    # a DOI-rich bundle: presence everywhere, so nothing is decided
    assert {e["status"] for e in loaded.document["entries"]} == {"unknown"}


# -- the patterns err towards matching ---------------------------------------

@pytest.mark.parametrize("check, text, matches", [
    ("doi_rrid", "https://doi.org/10.13026/abc", True),
    ("doi_rrid", "the DOIs of each release", True),
    ("doi_rrid", "doi_url: x", True),
    ("doi_rrid", "RRID:SCR_012345", True),
    ("doi_rrid", "doing the work", False),
    ("consent_text", "unconsented use", True),
    ("consent_text", "a waiver of authorization", True),
    ("consent_text", "participants could opt-out", True),
    ("consent_text", "several options", False),
    ("ethics_review", "the bioethics board", True),
    ("ethics_review", "IRBs at each site", True),
    ("version_string", "format conversion scripts", False),
    ("version_string", "CHoRUS v2.1", True),
    ("version_string", "Current Released Dataset", True),
    ("dataset_citation", "please cite this dataset", True),
    ("dataset_citation", "an exciting solicitation", False),
])
def test_patterns(check, text, matches):
    import re
    assert bool(re.search(at.CHECKS_BY_NAME[check].pattern, text)) is matches


_CLAIMED_FORMS = {
    # Every form a check's claim names, with its inflections: a miss can only
    # turn unknown into not_stated_in_source, the one status a check certifies.
    "doi_rrid": ["doi:10.5281/zenodo.1", "the DOI", "DOIs", "10.13026/abc", "RRID", "RRIDs",
                 "SCR_012345", "AB_2336877", "CVCL_0030", "NLX_143813",
                 "Identifier: 10.1000.10/abc123"],                              # subdivided registrant, #3183
    "ethics_review": ["IRB", "IRBs", "Institutional Review Board", "institutional\treview", "ethics committee",
                      "ethical approval", "HREC", "HRECs", "REB", "REBs", "exempt", "exemption",
                      "Category 4 exemptions apply", "exempted", "exempts", "exempting", "non-exempt",
                      "nonexempt", "waiver", "waived", "waivers", "DPIA", "DPIAs",
                      "data protection impact assessment", "privacy board", "human subject",
                      "human subjects research", "oversight", "oversights",
                      # a compound hyphenated as well as spaced (#3183)
                      "All procedures complied with the university's human-subjects protections.",
                      "Human-Subject Protections", "institutional-review board approval",
                      "a data-protection impact assessment", "privacy-board review"],
    "consent_text": ["consent", "consented", "informed consents", "assent", "assented", "waiver",
                     "waivers", "parental permission", "permissions", "HIPAA authorization",
                     "authorisations", "opt-in", "opt-out", "opt out", "opted out", "opts in",
                     "participants opting out were removed", "opting-in", "opt-outs", "optout",
                     # a run of separators, as PDF extraction leaves (#3237)
                     "Participants may opt  out at any time.", "Participants may opt- out at any time.",
                     "opt - out", "opted \t in"],
    "version_string": ["version", "versions", "versioned", "Release", "released", "releases",
                       "releasing", "edition", "revisions", "v2", "V1.0.3", "Dataset 2.0.1 is out",
                       "The dataset is 2.0.1.", "at 1.2.3.", "1.0.0.2", "(2.0.1)"],
    "dataset_citation": ["DOI", "10.1234/x", "10.1000.10/abc123", "cite", "cites", "cited", "citing",
                         "citation", "citations",
                         "BibTeX", "acknowledgement", "acknowledgment", "Please acknowledge",
                         "please reference", "how to reference", "when referencing",
                         "Users should reference this dataset as", "it must be referenced as",
                         "kindly reference", "recommended reference"],
}


@pytest.mark.parametrize("check, text", [(c, t) for c, forms in _CLAIMED_FORMS.items() for t in forms])
def test_every_form_a_claim_names_matches(check, text):
    """#3109: 'The dataset is 2.0.1.', 'exemptions' and 'opting out' were
    missed although each claim names them."""
    import re
    assert re.search(at.CHECKS_BY_NAME[check].pattern, text), (check, text)


def _entry_over(check, text):
    _, lines = at._lines_by_chunk(text, DEFAULT_RULE)
    return at.deterministic_entry(at.CHECKS_BY_NAME[check], lines)


@pytest.mark.parametrize("check, text, hit_lines", [
    # The reviewers' reproductions (#3179): each was not_stated_in_source
    # with zero hits, read one line at a time.
    ("dataset_citation", "Users of this dataset should\nreference it as: Smith 2020.", [1, 2]),
    ("dataset_citation", "please\nreference the following paper", [1, 2]),
    ("ethics_review", "approved by the Johns Hopkins institutional\nreview board", [1, 2]),
    ("ethics_review", "Institutional\nReview Board", [1, 2]),
    ("ethics_review", "a data protection\nimpact assessment", [1, 2]),
    ("ethics_review", "a data\nprotection\nimpact assessment", [1, 2, 3]),     # three lines
    ("consent_text", "Participants could opt\nout at any time", [1, 2]),
    ("consent_text", "Participants gave con-\nsent", [1, 2]),                   # a split word
    ("ethics_review", "the eth-\nics committee", [1, 2]),
    ("ethics_review", "under the university's human-\nsubjects protections", [1, 2]),   # a compound
    ("consent_text", "an opt-\nout model", [1, 2]),
    # An indented continuation line (#3218): the indentation is part of the break.
    ("consent_text", "Participants gave con-\n  sent", [1, 2]),
    ("ethics_review", "the eth-\n    ics committee", [1, 2]),
    ("ethics_review", "the eth-  \n\t ics committee", [1, 2]),
    ("dataset_citation", "Users should\n\nreference it as", [1, 2, 3]),         # across a blank line
])
def test_a_statement_a_line_break_splits_is_not_an_absence(check, text, hit_lines):
    """#3179: the bundles are hard-wrapped, and a statement split across
    lines is a statement; a line-by-line search certified its absence."""
    entry = _entry_over(check, text)
    assert entry["status"] == "unknown", entry
    got = [s["lines"][0] for s in entry["evidence"]["snippets"]]
    assert got == [n for n in hit_lines if text.split("\n")[n - 1]]        # a blank line is touched by nothing
    assert entry["evidence"]["hit_count"] == len(got)


def test_every_claimed_form_split_by_a_line_break_still_matches():
    """Every claimed form, broken at each space (a wrapped line) and between
    each two letters with a hyphen (a hyphenated line end), is still a
    statement of it: `not_stated_in_source` for any of them would certify an
    absence the bundle does not have (#3179)."""
    misses = []
    for check, forms in _CLAIMED_FORMS.items():
        for form in forms:
            splits = [form[:i] + "\n" + form[i + 1:] for i, ch in enumerate(form) if ch.isspace()]
            splits += [form[:i] + "-\n" + form[i:] for i in range(1, len(form))
                       if form[i - 1].isalpha() and form[i].isalpha()]
            splits += [form[:i + 1] + "\n" + form[i + 1:] for i, ch in enumerate(form[:-1]) if ch == "-"]
            misses += [(check, s) for s in splits if _entry_over(check, s)["status"] != "unknown"]
    assert misses == []


@pytest.mark.parametrize("check, text", [
    # The reviewer's reproductions (#3238): a compound hyphen at one break and
    # a split-word hyphen at the next, which no reading of all breaks alike joins.
    ("ethics_review", "a data-\nprotec-\ntion impact assessment"),
    ("ethics_review", "human-\nsub-\njects research"),
    ("ethics_review", "insti-\ntutional-\nreview board"),                     # the split word first
    ("ethics_review", "a data-\nprotection\nim-\npact assessment"),            # a plain break between
    ("consent_text", "an opt-\nout-\ns list"),                                # opt-outs, both kinds
])
def test_a_statement_whose_hyphenated_breaks_need_different_readings_matches(check, text):
    entry = _entry_over(check, text)
    assert entry["status"] == "unknown", entry
    assert entry["evidence"]["hit_count"] == len(text.split("\n"))


def test_every_claimed_compound_split_at_its_hyphen_and_inside_a_word_still_matches():
    """Each claimed form written with a compound hyphen, broken after that
    hyphen and again, with a hyphen, between two letters of another word:
    one statement needing both readings of a hyphenated line end (#3238)."""
    misses, tried = [], 0
    for check, forms in _CLAIMED_FORMS.items():
        for form in forms:
            for h in [i for i, ch in enumerate(form) if ch == "-" and 0 < i < len(form) - 1
                      and form[i - 1].isalpha() and form[i + 1].isalpha()]:
                for i in range(1, len(form)):
                    if abs(i - h) > 1 and form[i - 1].isalpha() and form[i].isalpha():
                        cut = sorted([(h + 1, "\n"), (i, "-\n")], reverse=True)
                        text = form
                        for at_, ins in cut:
                            text = text[:at_] + ins + text[at_:]
                        tried += 1
                        if _entry_over(check, text)["status"] != "unknown":
                            misses.append((check, text))
    assert tried > 50 and misses == []


def test_the_mixed_readings_reach_as_far_as_the_note_says_and_no_further():
    """Within `MIXED_WINDOW_LINES` lines the breaks are read each on its own;
    beyond that the note's "Not seen" says a statement is missed, and it is."""
    n = at.MIXED_WINDOW_LINES
    inside = ["data-"] + ["-"] * (n - 3) + ["protec-", "tion impact"]
    beyond = ["data-"] + ["-"] * (n - 2) + ["protec-", "tion impact"]
    pattern = at.CHECKS_BY_NAME["ethics_review"].pattern
    lines = lambda xs: {k: ("c001", x) for k, x in enumerate(xs, 1)}
    assert len(inside) == n and at.matching_lines(pattern, lines(inside)) == list(range(1, n + 1))
    assert at.matching_lines(pattern, lines(beyond)) == []
    assert f"a statement over more than {n} lines whose hyphens need different readings" in \
        _entry_over("ethics_review", "x")["note"]


def test_a_line_break_does_not_join_what_no_reading_joins():
    """The readings add a line only where a match crosses its break, and a
    break with no hyphen before it is a space: 'over' 'sight' is two words,
    which the claims' "Not seen" says of a word split with no hyphen."""
    assert _entry_over("dataset_citation", "we should\nnot reference")["status"] == "not_stated_in_source"
    assert _entry_over("consent_text", "opt\nfor the smaller cohort")["status"] == "not_stated_in_source"
    assert _entry_over("ethics_review", "we looked it over\nsight unseen")["status"] == "not_stated_in_source"
    assert "Not seen: a word a break splits with no hyphen," in _entry_over("ethics_review", "x")["note"]
    # Lines matching alone are listed alone; a neighbour is not pulled in.
    entry = _entry_over("ethics_review", "the IRB approved it\nand then\nwe left")
    assert [s["lines"] for s in entry["evidence"]["snippets"]] == [[1, 1]]


def test_a_match_does_not_hide_a_crossing_match_it_overlaps():
    """The whole-text search restarts after each match's start, not its end:
    'ab' in line 1 would otherwise consume the 'b' that the crossing match
    'b c' starts on, and line 2 would go unlisted."""
    lines = {1: ("c001", "xab"), 2: ("c001", "c")}
    assert at.matching_lines(r"ab|b\s+c", lines) == [1, 2]


def test_a_line_that_matches_alone_is_a_hit_whatever_the_whole_text_reading_gives():
    """Each line is also searched alone: in the whole text a line's first
    character is not the start of the string, so a pattern anchored there
    would lose a line the line-by-line reading finds."""
    lines = {1: ("c001", "a heading"), 2: ("c001", "IRB approval")}
    assert at.matching_lines(r"^IRB", lines) == [2]


@pytest.mark.parametrize("pattern", [r"(?i)human-subjects", r"(?i)humansubjects"])
def test_each_reading_of_a_hyphenated_line_end_is_read(pattern):
    """After a hyphen a break is read both ways — the hyphen kept (a
    compound) and dropped (a split word). The current patterns join a
    compound with `[-\\s]+`, which the space reading already meets, so only a
    pattern that needs one reading alone shows it is taken."""
    lines = {1: ("c001", "under the university's Human-"), 2: ("c001", "Subjects protections")}
    assert at.matching_lines(pattern, lines) == [1, 2]


@pytest.mark.parametrize("check, text", [
    ("version_string", "X 2.0"),                                # the claim's own 'not seen'
    ("version_string", "Python 3.10 and 1.2"),
    ("consent_text", "participants agreed to take part"),
    ("consent_text", "opting to use a smaller cohort"),
    ("dataset_citation", "Smith J (2020). A dataset. Journal 1:2"),
])
def test_what_a_claim_says_it_does_not_see_is_not_matched(check, text):
    import re
    assert not re.search(at.CHECKS_BY_NAME[check].pattern, text)


def test_no_pattern_carries_a_literal_space():
    """A space lets the YAML writer fold the pattern across lines."""
    assert not [c.name for c in at.CHECKS if " " in c.pattern]


# -- credited although not stated --------------------------------------------

def test_a_synthetic_credit_on_an_absent_item_is_flagged():
    loaded = at.load(CHORUS_FILE)
    evaluation = _chorus_evaluation()
    assert at.credited_despite_absence(evaluation, loaded) == []
    _item(evaluation, "E4.4")["score"] = 1
    _item(evaluation, "E1.1")["score"] = "1"
    _item(evaluation, "E6.1")["score"] = 1                        # unknown: not flagged
    found = {(f["kind"], f["item_id"], f["route"]) for f in at.credited_despite_absence(evaluation, loaded)}
    # E1.1's entry speaks for the DOI/RRID route only (#3219): its credit may
    # rest on the persistent-URI route, so it is for review, not a finding.
    assert found == {("credited", "E4.4", None), ("credited_on_other_route", "E1.1", "doi_rrid")}
    _item(evaluation, "E4.4").update(applicable=False, applicability_status="not_applicable")
    _item(evaluation, "E10.2")["name"] = "Something else"
    found = {(f["kind"], f["item_id"]) for f in at.credited_despite_absence(evaluation, loaded)}
    assert found == {("credited_on_other_route", "E1.1"), ("unjoined", "E10.2")}
    assert at.credited_despite_absence(_chorus_evaluation("rubric20", "CHORUS_v7_rep2_r20_rating1_evaluation.json"),
                                       loaded) == []


def test_the_bundle_version_comes_from_the_records_provenance(tmp_path):
    """#3110: an evaluation of a record that read AI_READI 8abd7bf5 is joined
    to the file for 8abd7bf5, not to the AI_READI bundle on disk today — the
    project-name lookup the design rejects. Before #3110 no test told the two
    apart: the CHORUS bundle on disk is still the version its records read.
    Runs on pull requests; the corpus test below pins the reference arms."""
    disk_md5 = hashlib.md5((ROOT / AI_READI).read_bytes()).hexdigest()
    assert disk_md5 != AI_READI_V7_MD5
    record = tmp_path / "AI_READI_provenance.yaml"
    record.write_text(yaml.safe_dump({"inputs": {"bundle_path": AI_READI, "bundle_md5": AI_READI_V7_MD5}}),
                      encoding="utf-8")
    evaluation = {"rubric": "rubric10-semantic", "project": "AI_READI", "elements": [],
                  "d4d_file": "data/d4d_concatenated/claudecode_agent/LABEL_v7/AI_READI_d4d.yaml"}
    path = tmp_path / "AI_READI_evaluation.json"
    path.write_text(json.dumps(evaluation), encoding="utf-8")
    with mock.patch.object(pv, "record_path_for", return_value=record) as where:
        # Needs no git, so a shallow checkout still runs it.
        assert at.evaluation_bundle(evaluation) == {"path": AI_READI, "md5": AI_READI_V7_MD5,
                                                    "record": str(record)}
        where.assert_called_with("AI_READI", "claudecode_agent", "LABEL_v7")
        covered = at.write_document(_git_or_skip(lambda: at.build_document(AI_READI, md5=AI_READI_V7_MD5)),
                                    tmp_path / "attainability")
        [row] = at.credited_report([path], tmp_path / "attainability")
    assert row["bundle"]["md5"] == AI_READI_V7_MD5
    assert row["attainability"] == str(covered)
    # Every AI_READI 8abd7bf5 entry is unknown: the file can yield no finding
    # for this evaluation, and says so rather than read as a zero (#3181).
    assert (row["absences_checked"], row["findings"]) == ([], [])
    assert row["unchecked"] == "the file marks no rubric10 item not_stated_in_source"


def test_a_file_that_decides_nothing_for_the_evaluations_rubric_is_reported_unchecked(tmp_path, capsys):
    """#3181: the CHORUS file pins only rubric10, so it can yield no finding
    for a rubric20 evaluation. `credited` printed that row like a checked
    one — the file, no findings, a `--strict` pass — and counted it covered."""
    record = tmp_path / "CHORUS_provenance.yaml"
    record.write_text(yaml.safe_dump({"inputs": {"bundle_path": CHORUS, "bundle_md5": CHORUS_MD5}}),
                      encoding="utf-8")
    r10 = REFERENCE["rubric10"] / "CHORUS_v7_rep2_r10_rating1_evaluation.json"
    r20 = REFERENCE["rubric20"] / "CHORUS_v7_rep2_r20_rating1_evaluation.json"
    with mock.patch.object(pv, "record_path_for", return_value=record):
        checked, unchecked = at.credited_report([r10, r20])
        assert at.main(["credited", "--strict", str(r10), str(r20)]) == 0
    assert Path(checked["attainability"]).resolve() == Path(unchecked["attainability"]).resolve() == CHORUS_FILE.resolve()
    assert (checked["rubric"], checked["absences_checked"], checked["unchecked"], checked["findings"]) == (
        "rubric10", ["E1.1 route doi_rrid", "E4.4", "E10.2"], None, [])
    assert (unchecked["rubric"], unchecked["absences_checked"], unchecked["findings"]) == ("rubric20", [], [])
    assert unchecked["unchecked"] == ("the file pins no rubric20 text (it pins rubric10), "
                                      "so it decides nothing for this evaluation")
    out = capsys.readouterr().out
    assert f"{r10}: 9b2ef4b6 — " in out and " — rubric10 checked against E1.1 route doi_rrid, E4.4, E10.2\n" in out
    assert f"{r20}: 9b2ef4b6 — " in out and " — unchecked: the file pins no rubric20 text" in out
    assert out.rstrip().endswith("2 evaluation(s), 2 on a bundle version with an attainability file, "
                                 "1 checked against at least one absence, 0 finding(s)")


@pytest.mark.corpus   # reads the reference records' provenance under data/d4d_concatenated
def test_no_cborg_runtime_rubric10_record_is_credited_on_a_chorus_absence():
    rows = at.credited_report(sorted(REFERENCE["rubric10"].glob("*_evaluation.json")))
    assert len(rows) == 32
    chorus = [r for r in rows if "/CHORUS_" in r["evaluation"]]
    assert len(chorus) == 8
    assert all(r["bundle"]["md5"] == CHORUS_MD5 and r["attainability"] for r in chorus)
    assert all(r["absences_checked"] == ["E1.1 route doi_rrid", "E4.4", "E10.2"] and r["unchecked"] is None
               for r in chorus)                                                    # a measured zero
    assert all(r["attainability"] is None and r["unchecked"] == "no attainability file for this bundle version"
               for r in rows if r not in chorus)
    assert [f for r in rows for f in r["findings"]] == []
    # The version each arm read, from its records' provenance (#3110): the v7
    # AI_READI and VOICE records read bundles the disk no longer holds.
    read = {}
    for r in rows:
        name = Path(r["evaluation"]).name
        arm = name[: name.index("_rep")]
        read.setdefault(arm, set()).add(r["bundle"]["md5"][:8])
    assert read == {"AI_READI_v7": {"8abd7bf5"}, "AI_READI_v8": {"d22b61a9"},
                    "CHORUS_v7": {"9b2ef4b6"}, "CHORUS_v8": {"9b2ef4b6"},
                    "CM4AI_v7": {"50037fc6"}, "CM4AI_v8": {"50037fc6"},
                    "VOICE_v7": {"dcd71717"}, "VOICE_v8": {"9193c3cb"}}


@pytest.mark.corpus   # reads the reference records' provenance under data/d4d_concatenated
def test_the_cborg_runtime_rubric20_chorus_records_are_reported_unchecked():
    """#3181: the six rubric20 CHORUS evaluations are on the covered bundle
    version, but the file pins no rubric20 text: no finding was possible,
    and the rows say so instead of reading as six more measured zeros."""
    rows = at.credited_report(sorted(REFERENCE["rubric20"].glob("*_evaluation.json")))
    assert len(rows) == 24
    chorus = [r for r in rows if "/CHORUS_" in r["evaluation"]]
    assert len(chorus) == 6 and all(r["attainability"] for r in chorus)
    assert {r["unchecked"] for r in chorus} == {
        "the file pins no rubric20 text (it pins rubric10), so it decides nothing for this evaluation"}
    assert all(r["unchecked"] for r in rows) and [f for r in rows for f in r["findings"]] == []


def test_attainability_moves_no_score():
    """Every cborg_runtime evaluation — 24 rubric10 and 24 rubric20 primary
    ratings, and the 8 rubric10 repeats — scores the same with the
    attainability file loaded and run over it, and is not mutated. The CHORUS
    file is paired with every evaluation on purpose: the most code runs."""
    paths = sorted(REFERENCE["rubric10"].glob("*.json")) + sorted(REFERENCE["rubric20"].glob("*.json"))
    assert len(paths) == 56 and sum("rating1" in p.name for p in paths) == 48

    def fields(doc):
        bases = score_bases(doc, 50 if doc["rubric"] == "rubric10-semantic" else 88)
        overall = doc["overall_score"]
        return (bases.total, bases.fixed_max, bases.adjusted_max,
                overall["total_points"], overall["max_points"], overall["adjusted_max_points"])

    docs = {p: json.loads(p.read_text(encoding="utf-8")) for p in paths}
    before = {p: fields(d) for p, d in docs.items()}
    snapshot = copy.deepcopy(docs)
    loaded = at.load(CHORUS_FILE)
    flagged = 0
    for doc in docs.values():
        at.evaluation_items(doc)
        flagged += len(at.credited_despite_absence(doc, loaded))
    assert flagged > 0                                    # AI_READI and VOICE credit E4.4, as they may
    assert {p: fields(d) for p, d in docs.items()} == before
    assert docs == snapshot


def test_the_command_line_checks_and_refuses(tmp_path, capsys):
    assert at.main(["check", str(CHORUS_FILE)]) == 0
    assert "3 not_stated_in_source, 2 unknown" in capsys.readouterr().out
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    doc["entries"][0]["status"] = "supported"
    bad = tmp_path / CHORUS_FILE.name
    bad.write_text(at.dump(doc), encoding="utf-8")
    assert at.main(["check", str(bad)]) == 1
    assert "INVALID" in capsys.readouterr().out

    # The reviewers' two reproductions: an empty chunk rule printed `ok`
    # (#3107), and a curator snippet naming its chunk as a list raised a
    # TypeError out of `check` instead of listing the problem (#3108).
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    doc["chunk_rule"] = {}
    bad.write_text(at.dump(doc), encoding="utf-8")
    assert at.main(["check", str(bad)]) == 1
    assert f"INVALID {bad}\n  - chunk_rule is not a rule the chunker implements" in capsys.readouterr().out
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    doc["entries"].append({"rubric": "rubric10", "item_id": "E5.1", "route": None, "status": "unknown",
                           "method": "curator", "note": "A reading.",
                           "evidence": {"snippets": [{"chunk": ["c003"], "lines": [414, 414], "sha256": "0" * 64}]}})
    bad.write_text(at.dump(doc), encoding="utf-8")
    assert at.main(["check", str(bad)]) == 1
    out = capsys.readouterr().out
    assert f"INVALID {bad}" in out and "snippets[0]: chunk must be a chunk id, not list" in out


def test_a_file_that_cannot_be_read_as_text_is_reported_and_the_next_still_checked(tmp_path, capsys):
    """#3180: `load` read the file outside the validator, so one Latin-1 byte
    raised UnicodeDecodeError out of `check` and every later file went
    unchecked; a missing file did the same with FileNotFoundError."""
    bad = tmp_path / CHORUS_FILE.name
    bad.write_bytes(CHORUS_FILE.read_bytes() + "# curator: caf\xe9\n".encode("latin-1"))
    missing = tmp_path / "CHORUS_preprocessed_missing.yaml"
    assert at.main(["check", str(bad), str(missing), str(CHORUS_FILE)]) == 1
    out = capsys.readouterr().out
    assert f"INVALID {bad}\n  - not UTF-8 text: 'utf-8' codec can't decode byte 0xe9" in out
    assert f"INVALID {missing}\n  - cannot be read: No such file or directory" in out
    assert f"ok {CHORUS_FILE} (file on disk)" in out                 # checked after both


def test_a_bundle_path_carrying_a_nul_byte_is_a_problem_not_a_traceback():
    """#3180: `git` raised ValueError('embedded null byte'), which neither
    `resolve_bytes` nor the validator caught."""
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    doc["bundle"]["path"] = "data/preprocessed/concatenated/CHORUS\0x.txt"
    problems, loaded = at.validate_text(at.dump(doc))
    assert loaded is None
    assert problems == ["bundle: the path carries a NUL byte, which no file or committed path can"]
    with pytest.raises(at.AttainabilityError, match=r"CHORUS\\0x\.txt: the path carries a NUL byte"):
        at.resolve_bytes(doc["bundle"]["path"], md5=CHORUS_MD5)


def _credited_main(tmp_path, evaluation, *flags):
    """`credited` over one CHORUS rubric10 evaluation, its record's
    provenance naming the bundle version the CHORUS file is about."""
    record = tmp_path / "CHORUS_provenance.yaml"
    record.write_text(yaml.safe_dump({"inputs": {"bundle_path": CHORUS, "bundle_md5": CHORUS_MD5}}),
                      encoding="utf-8")
    path = tmp_path / "CHORUS_evaluation.json"
    path.write_text(json.dumps(evaluation), encoding="utf-8")
    with mock.patch.object(pv, "record_path_for", return_value=record):
        return at.main(["credited", *flags, str(path)])


def test_a_credit_on_an_item_a_route_entry_leaves_open_is_for_review_not_a_finding(tmp_path, capsys):
    """#3219: E1.1 accepts a persistent URI, which no pattern settles, so an
    evaluation crediting it on 'id: ark:/12345/chorus-release-1' may be
    right. It failed `credited --strict` as a finding; it is listed for a
    curator and the gate passes. A credit on a settled absence still fails."""
    evaluation = _chorus_evaluation()
    _item(evaluation, "E1.1")["score"] = 1
    assert _credited_main(tmp_path, evaluation, "--strict") == 0
    out = capsys.readouterr().out
    assert "  credited_on_other_route: E1.1 (route doi_rrid) 1.0 the bundle states nothing by the doi_rrid route" in out
    assert out.rstrip().endswith("1 checked against at least one absence, 0 finding(s), "
                                 "1 credit(s) on another route to review")
    _item(evaluation, "E4.4")["score"] = 1
    assert _credited_main(tmp_path, evaluation, "--strict") == 1
    out = capsys.readouterr().out
    assert "  credited: E4.4 1.0\n" in out and out.rstrip().endswith(
        "1 finding(s), 1 credit(s) on another route to review")
    assert _credited_main(tmp_path, evaluation) == 0                         # reported, not gated


def test_a_bundle_path_no_file_system_can_hold_is_reported_and_the_next_file_still_checked(tmp_path, capsys):
    """#3217: a path component longer than NAME_MAX made `is_file` raise
    OSError ('File name too long') out of `resolve_bytes`, `load` and
    `check`, and the files after it went unchecked."""
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    doc["bundle"]["path"] = "data/" + "a" * 300 + "/CHORUS_preprocessed.txt"
    bad = tmp_path / at.file_name(doc)
    bad.write_text(at.dump(doc), encoding="utf-8")
    assert at.main(["check", str(bad), str(CHORUS_FILE)]) == 1
    out = capsys.readouterr().out
    assert f"INVALID {bad}\n  - bundle: " in out
    assert f"ok {CHORUS_FILE} (file on disk)" in out                 # checked after it


def test_a_path_through_a_directory_that_cannot_be_searched_falls_back_to_git(tmp_path):
    """#3217: on Python 3.13 `is_file` raises EACCES rather than answering
    False; the committed version may still answer, and when none does the
    problem is named."""
    raw = b"bundle bytes\n"
    md5, sha = hashlib.md5(raw).hexdigest(), hashlib.sha256(raw).hexdigest()
    locked = mock.Mock(spec=Path)
    locked.is_file.side_effect = PermissionError(13, "Permission denied")
    entry = {"commit": "c" * 40, "date": "2026-09-01", "matched_on": ["md5", "sha256"]}
    with mock.patch.object(pv, "bundle_bytes_for", return_value=(raw, entry)):
        assert at.resolve_bytes("data/b.txt", md5=md5, sha256=sha, disk=locked)[1]["source"] == "git blob"
    with mock.patch.object(pv, "bundle_bytes_for", return_value=None):
        with pytest.raises(at.AttainabilityError, match="hashes to md5"):
            at.resolve_bytes("data/b.txt", md5=md5, disk=locked)
    with mock.patch.object(pv, "bundle_bytes_for", side_effect=OSError(63, "File name too long")):
        with pytest.raises(at.AttainabilityError, match="nor git can read this path"):
            at.resolve_bytes("data/b.txt", md5=md5, disk=locked)
    with mock.patch.object(at, "validate_text", side_effect=OSError(13, "Permission denied")):
        with pytest.raises(at.AttainabilityError, match="a file it names cannot be read"):
            at.load(CHORUS_FILE)


def _broken_evaluation(tmp_path, how):
    """A CHORUS rubric10 evaluation broken one way (#3200), and the reason
    its row must give. The evaluations named BROKEN read their own record."""
    good = _chorus_evaluation()
    path = tmp_path / "broken_evaluation.json"
    record = tmp_path / "BROKEN_provenance.yaml"
    body = None
    if how == "not JSON":
        body, why = "{", f"the evaluation {path} is not JSON: Expecting property name"
    elif how == "not UTF-8":
        path.write_bytes(json.dumps(good).encode("utf-8")[:-1] + "\xe9}".encode("latin-1"))
        why = f"the evaluation {path} is not UTF-8 text: 'utf-8' codec can't decode byte 0xe9"
    elif how == "not an object":
        body, why = "[]", f"the evaluation {path} is not a JSON object"
    elif how == "missing":
        why = f"the evaluation {path} cannot be read: No such file or directory"
    elif how == "an element with no id":
        broken = copy.deepcopy(good)
        del broken["elements"][3]["id"]
        for sub in broken["elements"][3]["sub_elements"]:
            sub.pop("item_id", None)
        body, why = json.dumps(broken), f"the evaluation {path} has items that cannot be keyed: KeyError: 'id'"
    elif how == "a sub-element that is not an object":
        broken = copy.deepcopy(good)
        broken["elements"][0]["sub_elements"][0] = "E1.1: 1"
        body, why = json.dumps(broken), f"the evaluation {path} has items that cannot be keyed: AttributeError"
    else:
        body = json.dumps({**good, "project": "BROKEN"})
        too_long = (f"the provenance record {record} names a bundle version whose attainability file "
                    "cannot be looked up: File name too long")
        record.write_text({"provenance not YAML": "inputs: [unclosed\n",
                           "provenance not a mapping": "- inputs\n",
                           "inputs not a mapping": "inputs: [a, b]\n",
                           "inputs an empty list": "inputs: []\n",
                           "inputs an empty string": "inputs: ''\n",
                           "inputs false": "inputs: false\n",
                           "a bundle md5 that is not a string": yaml.safe_dump(
                               {"inputs": {"bundle_path": CHORUS, "bundle_md5": [CHORUS_MD5]}}),
                           "a bundle md5 of zero": yaml.safe_dump(
                               {"inputs": {"bundle_path": CHORUS, "bundle_md5": 0}}),
                           "a bundle path that is an empty list": yaml.safe_dump(
                               {"inputs": {"bundle_path": [], "bundle_md5": CHORUS_MD5}}),
                           "a bundle md5 too long for a file name": yaml.safe_dump(
                               {"inputs": {"bundle_path": CHORUS, "bundle_md5": "a" * 400}}),
                           "a bundle path too long for a file name": yaml.safe_dump(
                               {"inputs": {"bundle_path": "data/" + "b" * 400 + ".txt",
                                           "bundle_md5": CHORUS_MD5}}),
                           "a bundle md5 with a NUL byte": yaml.safe_dump(
                               {"inputs": {"bundle_path": CHORUS, "bundle_md5": "ab\0cd"}}),
                           "a bundle path with a NUL byte": yaml.safe_dump(
                               {"inputs": {"bundle_path": "data/x\0y.txt", "bundle_md5": CHORUS_MD5}})}[how],
                          encoding="utf-8")
        with_nul = (f"the provenance record {record} names a bundle version whose attainability file "
                    "cannot be looked up: the bundle_path or bundle_md5 carries a NUL byte, which no file name can")
        not_a_string = f"the provenance record {record} names a bundle_path or bundle_md5 that is not a string"
        why = {"provenance not YAML": f"the provenance record {record} is not YAML: while parsing",
               "a bundle md5 that is not a string": not_a_string,
               "a bundle md5 of zero": not_a_string,
               "a bundle path that is an empty list": not_a_string,
               "a bundle md5 too long for a file name": too_long,
               "a bundle path too long for a file name": too_long,
               "a bundle md5 with a NUL byte": with_nul,
               "a bundle path with a NUL byte": with_nul}.get(
            how, f"the provenance record {record} is not a mapping with an inputs mapping")
    if body is not None:
        path.write_text(body, encoding="utf-8")
    return path, why


@pytest.mark.parametrize("body", ["{}\n", "inputs: null\n", "inputs: {}\n",
                                  "inputs: {bundle_path: null, bundle_md5: abc}\n",
                                  "inputs: {bundle_path: x.txt, bundle_md5: ''}\n",
                                  "inputs: {bundle_path: '', bundle_md5: abc}\n",
                                  "inputs: {bundle_path: x.txt}\n"])
def test_a_record_that_names_no_bundle_is_not_unreadable(tmp_path, body):
    """#3489: the type checks look at the value as written, so a falsy
    non-mapping or non-string is unreadable. An absent, null or mapping
    `inputs` whose `bundle_path` or `bundle_md5` is absent, null or an empty
    string still names no bundle and returns None rather than raising; an
    empty-string `inputs` is not among these (#3503) and is unreadable."""
    record = tmp_path / "CHORUS_provenance.yaml"
    record.write_text(body, encoding="utf-8")
    evaluation = {"project": "CHORUS", "d4d_file": "data/d4d_concatenated/claudecode_agent/L/CHORUS_d4d.yaml"}
    with mock.patch.object(pv, "record_path_for", return_value=record):
        assert at.evaluation_bundle(evaluation) is None


@pytest.mark.parametrize("how", ["not JSON", "not UTF-8", "not an object", "missing", "an element with no id",
                                 "a sub-element that is not an object", "provenance not YAML",
                                 "provenance not a mapping", "inputs not a mapping",
                                 "inputs an empty list", "inputs an empty string", "inputs false",
                                 "a bundle md5 that is not a string", "a bundle md5 of zero",
                                 "a bundle path that is an empty list", "a bundle md5 too long for a file name",
                                 "a bundle path too long for a file name", "a bundle md5 with a NUL byte",
                                 "a bundle path with a NUL byte"])
def test_an_evaluation_that_cannot_be_read_is_reported_and_the_next_still_checked(tmp_path, capsys, how):
    """#3200: `credited_report` read each evaluation with a bare `json.loads`,
    keyed its elements by `element['id']` and read the record's provenance
    with no guard, so one broken input raised out of `credited` and the
    evaluations after it went unreported. Its row now names the file and
    why, counts apart, and fails the run with or without --strict."""
    record = tmp_path / "CHORUS_provenance.yaml"
    record.write_text(yaml.safe_dump({"inputs": {"bundle_path": CHORUS, "bundle_md5": CHORUS_MD5}}),
                      encoding="utf-8")
    good = REFERENCE["rubric10"] / "CHORUS_v7_rep2_r10_rating1_evaluation.json"
    broken, why = _broken_evaluation(tmp_path, how)

    def where(project, method, label):
        return tmp_path / f"{project}_provenance.yaml"

    with mock.patch.object(pv, "record_path_for", side_effect=where):
        first, middle, last = at.credited_report([good, broken, good])
        assert at.main(["credited", str(good), str(broken), str(good)]) == 1
    assert first == last and first["unchecked"] is None and first["unreadable"] is False
    assert first["absences_checked"] == ["E1.1 route doi_rrid", "E4.4", "E10.2"]
    assert middle["unreadable"] is True and middle["unchecked"].startswith(why), middle["unchecked"]
    assert (middle["bundle"], middle["attainability"], middle["absences_checked"], middle["findings"]) == (
        None, None, [], [])
    out = capsys.readouterr().out
    assert f"{broken}: bundle unknown — unreadable: {why}" in out
    assert "\0" not in out                   # a NUL in the record is never printed raw (#3541)
    assert out.count(" — rubric10 checked against E1.1 route doi_rrid, E4.4, E10.2\n") == 2   # the one after it too
    assert out.rstrip().endswith("3 evaluation(s), 1 that could not be read, 2 on a bundle version with an "
                                 "attainability file, 2 checked against at least one absence, 0 finding(s)")
