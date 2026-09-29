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

@pytest.mark.parametrize("field", ["md5", "sha256"])
def test_a_tampered_bundle_hash_is_refused(field):
    doc = yaml.safe_load(CHORUS_FILE.read_text(encoding="utf-8"))
    value = doc["bundle"][field]
    doc["bundle"][field] = ("0" if value[0] != "0" else "1") + value[1:]
    problems, loaded = at.validate_text(at.dump(doc))           # no name: the bytes alone refuse it
    assert loaded is None
    assert any(p.startswith("bundle: neither the file on disk nor any committed version") for p in problems), problems


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


@pytest.mark.parametrize("rule, why", [
    ({}, "unsupported chunk rule version: None"),       # chunk_text reads {} as this checkout's default
    ({"max_lines": 400, "max_bytes": 48000}, "unsupported chunk rule version: None"),
    ({**DEFAULT_RULE, "version": 99}, "unsupported chunk rule version: 99"),
    ({**DEFAULT_RULE, "unit": "paragraph"}, "unsupported chunk rule unit: 'paragraph'"),
    ({**DEFAULT_RULE, "split": "nonsense"}, "unsupported chunk rule split: 'nonsense'"),
    ({**DEFAULT_RULE, "overlap": 0}, "unsupported chunk rule fields"),
    ({**DEFAULT_RULE, "max_lines": True}, "chunk rule max_lines must be a positive integer"),
])
def test_a_chunk_rule_the_chunker_does_not_implement_is_refused(rule, why):
    """`chunk_text` reads only the two window bounds, and an empty rule as the
    default, so all but the last case chunk exactly like the pinned rule and
    were accepted before #3107: the file attested a rule nobody chunked
    under, or none. The last (`True` is the bound 1) is now refused as a
    rule rather than by the entries it happens to move."""
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
                 "SCR_012345", "AB_2336877", "CVCL_0030", "NLX_143813"],
    "ethics_review": ["IRB", "IRBs", "Institutional Review Board", "institutional\treview", "ethics committee",
                      "ethical approval", "HREC", "HRECs", "REB", "REBs", "exempt", "exemption",
                      "Category 4 exemptions apply", "exempted", "exempts", "exempting", "non-exempt",
                      "nonexempt", "waiver", "waived", "waivers", "DPIA", "DPIAs",
                      "data protection impact assessment", "privacy board", "human subject",
                      "human subjects research", "oversight", "oversights"],
    "consent_text": ["consent", "consented", "informed consents", "assent", "assented", "waiver",
                     "waivers", "parental permission", "permissions", "HIPAA authorization",
                     "authorisations", "opt-in", "opt-out", "opt out", "opted out", "opts in",
                     "participants opting out were removed", "opting-in", "opt-outs", "optout"],
    "version_string": ["version", "versions", "versioned", "Release", "released", "releases",
                       "releasing", "edition", "revisions", "v2", "V1.0.3", "Dataset 2.0.1 is out",
                       "The dataset is 2.0.1.", "at 1.2.3.", "1.0.0.2", "(2.0.1)"],
    "dataset_citation": ["DOI", "10.1234/x", "cite", "cites", "cited", "citing", "citation", "citations",
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
    assert found == {("credited", "E4.4", None), ("credited", "E1.1", "doi_rrid")}
    _item(evaluation, "E4.4").update(applicable=False, applicability_status="not_applicable")
    _item(evaluation, "E10.2")["name"] = "Something else"
    found = {(f["kind"], f["item_id"]) for f in at.credited_despite_absence(evaluation, loaded)}
    assert found == {("credited", "E1.1"), ("unjoined", "E10.2")}
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


@pytest.mark.corpus   # reads the reference records' provenance under data/d4d_concatenated
def test_no_cborg_runtime_rubric10_record_is_credited_on_a_chorus_absence():
    rows = at.credited_report(sorted(REFERENCE["rubric10"].glob("*_evaluation.json")))
    assert len(rows) == 32
    chorus = [r for r in rows if "/CHORUS_" in r["evaluation"]]
    assert len(chorus) == 8
    assert all(r["bundle"]["md5"] == CHORUS_MD5 and r["attainability"] for r in chorus)
    assert all(r["attainability"] is None for r in rows if r not in chorus)
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
