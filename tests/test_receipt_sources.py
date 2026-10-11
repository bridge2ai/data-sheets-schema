"""A receipt's citations by source document and tier, read-only (#2937)."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from unittest import mock

import pytest
import yaml

from data_sheets_schema import chunking
from data_sheets_schema import provenance as pv
from data_sheets_schema import receipt_sources as rs
from data_sheets_schema import receipts as rc

ROOT = Path(__file__).resolve().parents[1]
SEP = "=" * 80


def _doc(name: str, body: str) -> str:
    return f"FILE: {name}\nPATH: x/{name}\nSIZE: 1 bytes\n" + "-" * 80 + f"\n{body}\n\n{SEP}\n\n"


RELEASE = ("The Voice Release Dataset contains 1,200 recordings of sustained vowel phonation "
           "collected at five clinical sites. Recordings are in English.")
HANDBOOK = "The handbook explains the consent workflow for participants in English."
WEBINAR = ("In the webinar we said the release holds sustained vowel phonation recordings "
           "collected at clinical sites. Participants can withdraw at any time.")

#: The acceptance fixture: three chunks, tiers 1, 2 and 4, no preamble.
BUNDLE3 = _doc("release.txt", RELEASE) + _doc("docs.txt", HANDBOOK) + _doc("webinar.txt", WEBINAR)

SOURCE_MANIFEST = b"""source_priority:
  1: [data resource]
  2: [documentation]
  4: [tutorial]
projects:
  P:
    - id: release
      source_type: data resource
      processed_file: release.txt
    - id: handbook
      source_type: documentation
      processed_file: docs.txt
    - id: webinar
      source_type: tutorial
      processed_file: webinar.txt
    - id: faq
      source_type: documentation
      processed_file: faq.txt
    - id: blog
      source_type: blog post
      processed_file: blog.txt
"""

FULL = {"id": "https://x/ds",
        "title": "Voice Release Dataset",
        "description": "sustained vowel phonation recordings collected at clinical sites",
        "withdrawal": "Participants can withdraw at any time",
        "language": "English",
        "keywords": ["voice", "phonation"],
        "creator": "Jane Parker Example Lab",
        "publisher": "Example Publishing House",
        "funders": [],
        "notes": "the run's own commentary"}


def _manifest(bundle: str) -> tuple[dict, dict]:
    raw = bundle.encode("utf-8")
    manifest = chunking.manifest_from_bytes(raw, "P_preprocessed.txt")
    texts = dict(zip([c["id"] for c in manifest["chunks"]], chunking.chunk_texts(bundle, manifest["chunks"])))
    return manifest, texts


def _acceptance_receipt(md5: str) -> dict:
    return {"bundle_md5": md5, "chunks": [
        {"id": "c001", "status": "nothing_relevant", "reason": "read; nothing new"},
        {"id": "c002", "status": "nothing_relevant", "reason": "consent workflow only"},
        {"id": "c003", "status": "extracted", "extracted": [
            {"slot": "description", "snippet": "sustained vowel phonation recordings collected at clinical sites"},
            {"slot": "withdrawal", "snippet": "Participants can withdraw at any time"}]}]}


def test_a_lower_tier_citation_with_a_higher_tier_token_match_is_counted():
    """The issue's acceptance fixture: the tier-4 chunk is the only citation
    for two paths, and the tier-1 chunk holds every token of one of them."""
    manifest, texts = _manifest(BUNDLE3)
    assert [(c["id"], c["source"]) for c in manifest["chunks"]] == [
        ("c001", "release.txt"), ("c002", "docs.txt"), ("c003", "webinar.txt")]
    out = rs.source_dependence(_acceptance_receipt(manifest["bundle_md5"]), manifest, SOURCE_MANIFEST,
                               "P", FULL, texts)
    assert out["paths"] == 2
    assert out["single_document"] == {"paths": 2, "share": 1.0}
    assert out["paths_by_citing_documents"] == {1: 2}
    tiers = {t["tier"]: t for t in out["by_tier"]}
    assert tiers[4]["sole_share"] == 1.0 and tiers[4]["paths_sole_document"] == 2
    assert tiers[1]["paths_sole_document"] == 0 and tiers[2]["paths_sole_document"] == 0
    docs = {d["document"]: d for d in out["documents"]}
    assert (docs["webinar"]["paths_citing"], docs["webinar"]["paths_sole"], docs["webinar"]["sole_share"]) == (2, 2, 1.0)
    assert docs["release"]["paths_citing"] == 0 and docs["release"]["chunks"] == ["c001"]
    screen = out["lower_tier_with_higher_tier_token_match"]
    assert screen["count"] == 1 and screen["screened"] == 2
    assert screen["by_cited_tier"] == [{"tier": 4, "paths": 1}]
    [ex] = screen["examples"]
    assert ex["path"] == "description"
    assert ex["verbatim"] is False and screen["verbatim"] == 0     # every token, not as one run
    assert ex["cited"] == [{"document": "webinar", "tier": 4, "chunks": ["c003"]}]
    assert ex["higher_tier_chunks"] == [{"chunk": "c001", "document": "release", "tier": 1}]
    rows = {r["path"]: r for r in out["by_path"]}
    assert rows["description"]["token_screen"] == "higher_tier_match"
    assert rows["withdrawal"]["token_screen"] == "no_higher_tier_match"      # the handbook has "participants" only
    assert out["unit"] == rs.UNIT and "#2819" in out["unit"]


def _rich():
    """Preamble, tiers 1/2/4, an unranked and an undeclared source."""
    bundle = (f"{SEP}\nCONCATENATED DOCUMENT\n{SEP}\n\n" + _doc("release.txt", RELEASE) + _doc("docs.txt", HANDBOOK)
              + _doc("webinar.txt", WEBINAR) + _doc("faq.txt", "Frequently asked: the consent workflow.")
              + _doc("blog.txt", "A post by Jane Parker of Example Lab.")
              + _doc("extra.txt", "Published by Example Publishing House."))
    manifest, texts = _manifest(bundle)
    assert [c["source"] for c in manifest["chunks"]] == [
        chunking.PREAMBLE, "release.txt", "docs.txt", "webinar.txt", "faq.txt", "blog.txt", "extra.txt"]
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": "c001", "status": "extracted", "extracted": [
            {"slot": "keywords", "snippet": "CONCATENATED DOCUMENT"},
            {"slot": "creator", "snippet": "CONCATENATED DOCUMENT"}]},
        {"id": "c002", "status": "extracted", "extracted": [
            {"slot": "title", "snippet": "The Voice Release Dataset"}]},
        {"id": "c003", "status": "extracted", "extracted": [
            {"slot": "title", "snippet": "handbook"},
            {"slot": "language", "snippet": "participants in English"},
            {"slot": "notes", "snippet": "the consent workflow"},
            {"slot": "gone", "snippet": "the consent workflow"},
            {"slot": "funders", "snippet": "the consent workflow"},
            {"slot": "", "snippet": "the consent workflow"}]},
        {"id": "c004", "status": "extracted", "extracted": [
            {"slot": "description", "snippet": "sustained vowel phonation recordings"}]},
        {"id": "c005", "status": "redundant_with", "chunks": ["c003"]},
        {"id": "c006", "status": "extracted", "extracted": [
            {"slot": "creator", "snippet": "Jane Parker of Example Lab"}]},
        {"id": "c007", "status": "extracted", "extracted": [
            {"slot": "publisher", "snippet": "Example Publishing House"}]},
        {"id": "c099", "status": "extracted", "extracted": [
            {"slot": "title", "snippet": "not a chunk of this manifest"}]}]}
    return manifest, texts, receipt


def test_preamble_unranked_undeclared_and_every_screen_outcome():
    manifest, texts, receipt = _rich()
    out = rs.source_dependence(receipt, manifest, SOURCE_MANIFEST, "P", FULL, texts)
    # "gone" does not resolve in the record and "funders" resolves to an empty
    # list (fig19's `resolves`); "" is no slot; c099 is not in the manifest
    assert out["entries"] == {"pairs": 13, "kept": 9, "unresolved_in_final": 2,
                              "on_unknown_chunks": 1, "empty_slot": 1}
    assert out["paths_unresolved_in_final"] == 2
    assert out["paths"] == 7
    # the preamble is no document: keywords has none, creator has only the blog
    assert out["paths_by_citing_documents"] == {0: 1, 1: 5, 2: 1}
    assert out["single_document"]["paths"] == 5
    assert out["preamble"] == {"chunks": ["c001"], "citations": 2, "paths_cited": 2,
                               "paths_cited_only_by_preamble": 1}
    tiers = {t["tier"]: t for t in out["by_tier"]}
    assert sorted(tiers) == [1, 2, 4, rs.UNRANKED]
    assert {t: tiers[t]["paths_sole_document"] for t in tiers} == {1: 0, 2: 2, 4: 1, rs.UNRANKED: 2}
    assert tiers[1]["paths_best_tier"] == 1 and tiers[1]["paths_citing"] == 1
    assert tiers[2]["paths_citing"] == 3 and tiers[2]["paths_best_tier"] == 2
    assert tiers[rs.UNRANKED]["documents"] == ["blog", "undeclared:extra.txt"]
    # unranked sources take 99 and are listed apart, with why
    assert out["unranked"] == [{"document": "blog", "source": "blog.txt", "basis": "unranked"},
                               {"document": "undeclared:extra.txt", "source": "extra.txt", "basis": "undeclared"}]
    assert [d["tier"] for d in out["documents"]] == sorted(d["tier"] for d in out["documents"])
    docs = {d["document"]: d for d in out["documents"]}
    # every share is over all 7 paths, not over the single-document ones
    assert (docs["handbook"]["paths_citing"], docs["handbook"]["paths_sole"], docs["handbook"]["sole_share"]) == (3, 2, 2 / 7)
    assert tiers[2]["sole_share"] == 2 / 7 and out["single_document"]["share"] == 5 / 7
    assert out["redundant_with"] == {"entries": 1, "documents_pointed_to": ["handbook"]}
    screen = out["lower_tier_with_higher_tier_token_match"]
    assert screen["outcomes"] == {"higher_tier_match": 1, "no_higher_tier_match": 2, "below_floor": 1,
                                  "no_higher_tier_chunk": 1, "exempt": 1, "preamble_only": 1}
    assert sum(screen["outcomes"].values()) == out["paths"]
    rows = {r["path"]: r["token_screen"] for r in out["by_path"]}
    assert rows == {"description": "higher_tier_match", "creator": "no_higher_tier_match",
                    "publisher": "no_higher_tier_match",
                    "language": "below_floor",             # "English" is in the tier-1 chunk: one token, 7 characters
                    "title": "no_higher_tier_chunk",       # cited by the release: nothing ranks above it
                    "notes": "exempt", "keywords": "preamble_only"}
    assert [e["path"] for e in screen["examples"]] == ["description"]
    # nothing here is superseded, and a preamble-only path cites no document:
    # it keeps `preamble_only` and is not screened. Without that pass-through
    # its empty document set reads as "all superseded" and it would be counted
    # as having no replacement chunk (#3475)
    s_rows = {r["path"]: r["supersession_screen"] for r in out["by_path"]}
    assert s_rows["keywords"] == "preamble_only" and s_rows["notes"] == "exempt"
    assert out["superseded_with_replacement_token_match"]["outcomes"] == {
        "replacement_match": 0, "no_replacement_match": 0, "below_floor": 0, "no_replacement_chunk": 0,
        "cites_a_current_source": 5, "exempt": 1, "preamble_only": 1}
    lines = rs.render({**out, "run": {}})
    assert "· 0 with no replacement chunk in the bundle ·" in "\n".join(lines)
    # the supersession line prints every unscreened outcome, as the tier line
    # does, so its figures and "screened" add up to the path count (#3493)
    s_line = next(ln for ln in lines if "superseded, replacement token match" in ln)
    assert s_line.endswith("· 0 below the floors · 1 exempt · 1 preamble only"), s_line
    so = out["superseded_with_replacement_token_match"]
    printed = (so["screened"] + so["outcomes"]["cites_a_current_source"] + so["outcomes"]["no_replacement_chunk"]
               + so["outcomes"]["below_floor"] + so["outcomes"]["exempt"] + so["outcomes"]["preamble_only"])
    assert printed == out["paths"]


def test_a_chunk_without_text_is_listed_and_never_read_as_a_match():
    manifest, texts, receipt = _rich()
    del texts["c002"]                                  # the tier-1 chunk
    out = rs.source_dependence(receipt, manifest, SOURCE_MANIFEST, "P", FULL, texts)
    screen = out["lower_tier_with_higher_tier_token_match"]
    assert screen["chunks_without_text"] == ["c002"]
    assert screen["count"] == 0
    assert {r["path"]: r["token_screen"] for r in out["by_path"]}["description"] == "no_higher_tier_match"


def test_the_floors_are_parameters_and_the_examples_are_capped():
    manifest, texts, receipt = _rich()
    out = rs.source_dependence(receipt, manifest, SOURCE_MANIFEST, "P", FULL, texts, min_tokens=1, min_chars=4,
                               examples=1)
    screen = out["lower_tier_with_higher_tier_token_match"]
    assert screen["count"] == 2                        # "English" now screens and matches the release
    assert screen["floors"] == {"min_tokens": 1, "min_chars": 4, "token_min_chars": rs.TOKEN_MIN_CHARS}
    assert len(screen["examples"]) == 1 and screen["examples_truncated"] == 1
    screen = rs.source_dependence(receipt, manifest, SOURCE_MANIFEST, "P", FULL, texts, min_tokens=1,
                                  min_chars=4)["lower_tier_with_higher_tier_token_match"]
    assert {e["path"]: e["verbatim"] for e in screen["examples"]} == {"description": False, "language": True}
    assert screen["verbatim"] == 1


#: Values cited only by the tier-4 webinar whose every token the tier-1
#: release holds, so the floors alone decide which are flagged (#3122).
FLOOR_FULL = {"id": "https://x/ds",
              "triple": "five clinical sites",       # 3 tokens, 17 characters
              "pair": "sustained phonation",         # 2 tokens, 18 characters
              "short": "five sites",                 # 2 tokens,  9 characters
              "language": "English",                 # 1 token,   7 characters
              "flag": "Yes"}                         # no token: "yes" is under 4 characters


def _floor_screen(**floors) -> dict[str, str]:
    manifest, texts = _manifest(BUNDLE3)
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": "c003", "status": "extracted",
         "extracted": [{"slot": s, "snippet": "the webinar"} for s in FLOOR_FULL if s != "id"]}]}
    out = rs.source_dependence(receipt, manifest, SOURCE_MANIFEST, "P", FLOOR_FULL, texts, **floors)
    return {r["path"]: r["token_screen"] for r in out["by_path"]}


@pytest.mark.parametrize("floors, flagged", [
    ({}, {"triple"}),                                          # the defaults: 3 tokens, 12 characters
    ({"min_tokens": 3, "min_chars": 0}, {"triple"}),           # at 3 tokens the character floor cannot bind
    ({"min_tokens": 2}, {"triple", "pair"}),                   # "five sites" is 2 tokens but 9 characters
    ({"min_tokens": 2, "min_chars": 9}, {"triple", "pair", "short"}),
    ({"min_tokens": 1}, {"triple", "pair"}),                   # the character floor alone keeps out English
    ({"min_tokens": 1, "min_chars": 7}, {"triple", "pair", "short", "language"}),
    ({"min_tokens": 1, "min_chars": 0}, {"triple", "pair", "short", "language"}),
])
def test_the_token_floor_and_the_character_floor_each_bind(floors, flagged):
    """Each floor keeps out a value the other admits, at its boundary: the
    default token floor is what keeps "sustained phonation" (2 tokens, 18
    characters) out, and the character floor alone keeps "five sites"
    (2 tokens, 9 characters) out at a two-token floor (#3122)."""
    rows = _floor_screen(**floors)
    assert {p for p, o in rows.items() if o == "higher_tier_match"} == flagged
    assert {p for p, o in rows.items() if o != "higher_tier_match"} == set(rows) - flagged
    assert all(o in ("higher_tier_match", "below_floor") for o in rows.values())
    assert rows["flag"] == "below_floor"                       # no token: never matched, whatever the floor


def test_a_value_with_no_token_is_never_screened_and_a_zero_token_floor_is_refused():
    """An empty token set is a subset of every chunk: with no token floor,
    "Yes" would be flagged against the release and the handbook (#3121)."""
    assert rc._value_tokens("Yes") == set()
    assert _floor_screen(min_tokens=1, min_chars=0)["flag"] == "below_floor"
    for floor in (0, -1):
        with pytest.raises(ValueError, match="min_tokens must be at least 1"):
            _floor_screen(min_tokens=floor, min_chars=0)


def test_a_path_is_joined_to_the_final_record_by_index_alone():
    """No phase-1 snapshot join (#3123): reconciliation dropped `creators[0]`,
    so the receipt's `creators[0]` (Alpha, at phase 1) now reads Beta and is
    counted there, while its `creators[2]` (Gamma) is unresolved because
    index 2 is gone, though Gamma is still in the record."""
    snapshot = {"id": "https://x/ds", "creators": [{"name": "Alpha Example"}, {"name": "Beta Example"},
                                                   {"name": "Gamma Example"}]}
    final = {"id": "https://x/ds", "creators": snapshot["creators"][1:]}
    assert rc.remap_path("creators[0]", snapshot, final)["basis"] == "entry_dropped"
    manifest, texts = _manifest(BUNDLE3)
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": "c003", "status": "extracted", "extracted": [
            {"slot": "creators[0]", "snippet": "Alpha Example"},
            {"slot": "creators[2]", "snippet": "Gamma Example"}]}]}
    out = rs.source_dependence(receipt, manifest, SOURCE_MANIFEST, "P", final, texts)
    assert out["paths"] == 1 and [r["path"] for r in out["by_path"]] == ["creators[0]"]
    assert out["by_path"][0]["documents"] == ["webinar"]
    assert out["entries"]["unresolved_in_final"] == 1 and out["paths_unresolved_in_final"] == 1


def test_a_moved_or_dropped_entrys_path_is_unresolved_where_the_entry_at_its_index_lacks_it():
    """The index is still there, but the entry now at it does not hold the
    path, or holds it empty: the path is unresolved, not counted at that
    entry (#3190). Dropped: Alpha's affiliation, where index 0 is now Beta,
    whose affiliation is empty. Moved: reconciliation swapped the funders, so
    `funders[0].award` reads Fund Two, which has no award, while Fund One's
    award still resolves at `funders[1]`. `creators[0].name` is still read
    by index and credited to Beta, as #3123 states."""
    snapshot = {"id": "https://x/ds",
                "creators": [{"name": "Alpha Example", "affiliation": "Alpha Example Laboratory"},
                             {"name": "Beta Example", "affiliation": ""}],
                "funders": [{"name": "Fund One", "award": "R01 Example Award"}, {"name": "Fund Two"}]}
    final = {"id": "https://x/ds", "creators": snapshot["creators"][1:],
             "funders": [snapshot["funders"][1], snapshot["funders"][0]]}
    assert rc.remap_path("creators[0].affiliation", snapshot, final)["basis"] == "entry_dropped"
    assert rc.remap_path("funders[0].award", snapshot, final) == {"path": "funders[1].award", "basis": "by_name"}
    # both indexes are still there; one entry holds the leaf empty, the other not at all
    assert rc.resolve(final, "creators[0].affiliation") and not rc.resolve(final, "funders[0].award")
    assert rc.resolve(final, "funders[0]")
    manifest, texts = _manifest(BUNDLE3)
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": "c003", "status": "extracted", "extracted": [
            {"slot": "creators[0].name", "snippet": "Alpha Example"},
            {"slot": "creators[0].affiliation", "snippet": "Alpha Example Laboratory"},
            {"slot": "funders[0].award", "snippet": "R01 Example Award"}]}]}
    out = rs.source_dependence(receipt, manifest, SOURCE_MANIFEST, "P", final, texts)
    assert [r["path"] for r in out["by_path"]] == ["creators[0].name"] and out["paths"] == 1
    assert out["entries"]["kept"] == 1
    assert out["entries"]["unresolved_in_final"] == 2 and out["paths_unresolved_in_final"] == 2


def test_the_token_floor_stated_is_the_one_value_tokens_applies():
    assert rc._value_tokens("abc abcd") == {"abcd"}
    assert rs.TOKEN_MIN_CHARS == 4
    assert rs.MIN_MATCH_CHARS == rc.MIN_MULTIPART_CHARS
    # the comment's "at three tokens the character floor cannot bind"
    assert rs.MIN_MATCH_TOKENS * rs.TOKEN_MIN_CHARS >= rs.MIN_MATCH_CHARS


def test_mismatched_bytes_and_an_undeclared_project_are_refused():
    manifest, texts = _manifest(BUNDLE3)
    with pytest.raises(ValueError, match="bundle_md5"):
        rs.source_dependence(_acceptance_receipt("0" * 32), manifest, SOURCE_MANIFEST, "P", FULL, texts)
    with pytest.raises(ValueError, match="not declared"):
        rs.source_dependence(_acceptance_receipt(manifest["bundle_md5"]), manifest, SOURCE_MANIFEST, "Q", FULL, texts)


#: Supersession (#3049): the October and June releases are both tier 1, so
#: the tier screen cannot compare them; `v1 → v2 → v3` is a chain whose only
#: text-bearing replacement is at its end; `retired`'s replacement has no chunk.
SUPERSEDED_MANIFEST = b"""source_priority:
  1: [data resource]
  4: [tutorial]
projects:
  P:
    - id: october
      source_type: data resource
      processed_file: october.txt
      superseded_by: june
    - id: june
      source_type: data resource
      processed_file: june.txt
    - id: v1
      source_type: tutorial
      processed_file: v1.txt
      superseded_by: v2
    - id: v2
      source_type: tutorial
      processed_file: v2.txt
      superseded_by: v3
    - id: v3
      source_type: tutorial
      processed_file: v3.txt
    - id: retired
      source_type: tutorial
      processed_file: retired.txt
      superseded_by: absent
    - id: absent
      source_type: tutorial
      processed_file: absent.txt
"""

OCTOBER = "The October release holds 1,200 recordings from five clinical sites. Contact the steward."
JUNE = "The June release holds 1,200 recordings from five clinical sites and adds pediatric sessions."
V1 = "Workshop one: annotation guidelines for vowel phonation."
V2 = "Workshop two: nothing about annotation."
V3 = "Workshop three: revised annotation guidelines for vowel phonation tasks."
RETIRED = "An old page about retired calibration procedures here."

SUPERSEDED_FULL = {"id": "https://x/ds",
                   "sites": "recordings from five clinical sites",       # in June too
                   "steward": "contact the data steward office",         # October only
                   "both": "recordings from five clinical sites",        # cited to October and June
                   "count": "1,200",                                     # no token
                   "guidelines": "annotation guidelines vowel phonation",  # v1; v2 lacks it, v3 holds it
                   "calibration": "retired calibration procedures",      # replacement has no chunk
                   "workshop": "nothing about annotation",               # cited to v1 and v2; only v2 holds it
                   # exempt (owes no receipt), cited only to October, and June holds every token:
                   # it must stay `exempt`, never be screened into a replacement match (#3444)
                   "notes": "recordings from five clinical sites"}


def _superseded():
    bundle = "".join(_doc(n, t) for n, t in (("october.txt", OCTOBER), ("june.txt", JUNE), ("v1.txt", V1),
                                             ("v2.txt", V2), ("v3.txt", V3), ("retired.txt", RETIRED)))
    manifest, texts = _manifest(bundle)
    assert [c["id"] for c in manifest["chunks"]] == ["c001", "c002", "c003", "c004", "c005", "c006"]
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": "c001", "status": "extracted", "extracted": [
            {"slot": s, "snippet": "the october release"} for s in ("sites", "steward", "both", "count", "notes")]},
        {"id": "c002", "status": "extracted", "extracted": [{"slot": "both", "snippet": "the june release"}]},
        {"id": "c003", "status": "extracted", "extracted": [{"slot": "guidelines", "snippet": "workshop one"},
                                                           {"slot": "workshop", "snippet": "workshop one"}]},
        {"id": "c004", "status": "extracted", "extracted": [{"slot": "workshop", "snippet": "nothing about"}]},
        {"id": "c006", "status": "extracted", "extracted": [{"slot": "calibration", "snippet": "an old page"}]}]}
    return rs.source_dependence(receipt, manifest, SUPERSEDED_MANIFEST, "P", SUPERSEDED_FULL, texts)


def test_a_path_cited_only_to_a_superseded_source_is_screened_against_its_replacement():
    """A separate count (#3049): the tier screen leaves `sites` alone, since
    June shares October's tier; the supersession screen flags it, and follows
    the `superseded_by` chain past v2 to v3 for `guidelines`."""
    out = _superseded()
    rows = {r["path"]: r for r in out["by_path"]}
    assert {p: r["supersession_screen"] for p, r in rows.items()} == {
        "sites": "replacement_match", "guidelines": "replacement_match",
        "steward": "no_replacement_match",
        "both": "cites_a_current_source",           # June is cited beside October
        "count": "below_floor",
        "calibration": "no_replacement_chunk",      # `absent` is declared but not in the bundle
        # v2 is cited too, so its own chunk is no replacement: only v3's is read
        "workshop": "no_replacement_match",
        # cited only to October, June holds its tokens, but an exempt path is not screened (#3444)
        "notes": "exempt"}
    assert rows["notes"]["token_screen"] == "exempt" and "replacement_chunks" not in rows["notes"]
    assert rows["sites"]["token_screen"] == "no_higher_tier_chunk"      # the tier screen cannot see it
    assert rows["sites"]["replacement_chunks"] == ["c002"]
    assert rows["guidelines"]["replacement_chunks"] == ["c005"]           # v2 (c004) lacks the tokens
    s = out["superseded_with_replacement_token_match"]
    assert s["count"] == 2 and s["screened"] == 4
    assert s["outcomes"] == {"replacement_match": 2, "no_replacement_match": 2, "below_floor": 1,
                             "no_replacement_chunk": 1, "cites_a_current_source": 1, "exempt": 1,
                             "preamble_only": 0}
    assert sum(s["outcomes"].values()) == out["paths"]
    assert s["superseded_documents"] == [{"document": "october", "superseded_by": "june"},
                                         {"document": "v1", "superseded_by": "v2"},
                                         {"document": "v2", "superseded_by": "v3"},
                                         {"document": "retired", "superseded_by": "absent"}]
    # guidelines is cited to tier 4 and v3 is tier 4, so the tier screen has no chunk above it either
    assert s["also_higher_tier_match"] == 0
    ex = {e["path"]: e for e in s["examples"]}
    assert ex["sites"]["verbatim"] is True and s["verbatim"] == 1
    assert ex["sites"]["cited"] == [{"document": "october", "tier": 1, "superseded_by": "june", "chunks": ["c001"]}]
    assert ex["sites"]["replacement_chunks"] == [{"chunk": "c002", "document": "june", "tier": 1}]
    assert out["instrument"] == rs.INSTRUMENT and "#3049" in rs.INSTRUMENT
    text = "\n".join(rs.render({**out, "run": {}}))
    assert "superseded, replacement token match: 2 of 4 screened paths" in text
    assert "cited october (tier 1, superseded by june, c001); verbatim in c002 june (tier 1)" in text


def test_the_supersession_screen_changes_no_tier_outcome():
    """The tier screen's outcomes, counts and examples are the same with the
    supersession links removed from the manifest: the new count is beside
    the old one, not inside it."""
    out = _superseded()
    plain = re.sub(rb"\n      superseded_by: \w+", b"", SUPERSEDED_MANIFEST)
    assert b"superseded_by" not in plain
    manifest, texts = _manifest("".join(_doc(n, t) for n, t in (
        ("october.txt", OCTOBER), ("june.txt", JUNE), ("v1.txt", V1), ("v2.txt", V2), ("v3.txt", V3),
        ("retired.txt", RETIRED))))
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": "c001", "status": "extracted", "extracted": [
            {"slot": s, "snippet": "x"} for s in ("sites", "steward", "both", "count", "notes")]},
        {"id": "c002", "status": "extracted", "extracted": [{"slot": "both", "snippet": "x"}]},
        {"id": "c003", "status": "extracted", "extracted": [{"slot": "guidelines", "snippet": "x"},
                                                           {"slot": "workshop", "snippet": "x"}]},
        {"id": "c004", "status": "extracted", "extracted": [{"slot": "workshop", "snippet": "x"}]},
        {"id": "c006", "status": "extracted", "extracted": [{"slot": "calibration", "snippet": "x"}]}]}
    base = rs.source_dependence(receipt, manifest, plain, "P", SUPERSEDED_FULL, texts)
    key = "lower_tier_with_higher_tier_token_match"
    assert out[key] == base[key]
    assert [r["token_screen"] for r in out["by_path"]] == [r["token_screen"] for r in base["by_path"]]
    assert base["superseded_with_replacement_token_match"]["outcomes"]["cites_a_current_source"] == 7


def test_the_higher_tier_and_supersession_screens_can_flag_one_path():
    """Superseded at tier 4 by a tier-1 replacement: both screens flag it,
    and `also_higher_tier_match` counts it once."""
    sm = SOURCE_MANIFEST.replace(b"      processed_file: webinar.txt\n",
                                 b"      processed_file: webinar.txt\n      superseded_by: release\n")
    manifest, texts = _manifest(BUNDLE3)
    out = rs.source_dependence(_acceptance_receipt(manifest["bundle_md5"]), manifest, sm, "P", FULL, texts)
    rows = {r["path"]: r for r in out["by_path"]}
    assert (rows["description"]["token_screen"], rows["description"]["supersession_screen"]) == (
        "higher_tier_match", "replacement_match")
    s = out["superseded_with_replacement_token_match"]
    assert (s["count"], s["also_higher_tier_match"]) == (1, 1)
    assert out["lower_tier_with_higher_tier_token_match"]["count"] == 1


# ---------------------------------------------------------------- on disk
def _record(tmp: Path, bundle_text: str, **inputs) -> tuple[Path, Path]:
    bundle = tmp / "P_preprocessed.txt"
    bundle.write_text(bundle_text, encoding="utf-8")
    raw = bundle_text.encode("utf-8")
    built = chunking.manifest_from_bytes(raw, bundle.name)
    record = {"inputs": {"bundle_path": str(bundle), "bundle_md5": hashlib.md5(raw).hexdigest(),
                         "chunks": {"path": str(tmp / "P_chunks.yaml"),
                                    "sha256": hashlib.sha256(chunking.dump_manifest(built).encode()).hexdigest(),
                                    "rule": dict(chunking.DEFAULT_RULE), "chunk_count": built["chunk_count"]},
                         **inputs}}
    prov = tmp / "P_provenance.yaml"
    # sort_keys=False, as the recorder writes: the rule's key order is part
    # of the manifest bytes its sha256 attests.
    prov.write_text("# provenance\n# header\n" + yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    return prov, bundle


def test_run_chunks_rebuilds_the_records_manifest_from_the_bytes_it_hashed(tmp_path):
    prov, bundle = _record(tmp_path, BUNDLE3)
    run = rs.run_chunks(prov)
    assert run["basis"] == {"source": "bundle on disk", "path": str(bundle)}
    assert run["manifest"] == chunking.manifest_from_bytes(BUNDLE3.encode(), bundle.name)
    assert run["texts"]["c001"].startswith("FILE: release.txt")


def test_run_chunks_refuses_a_manifest_digest_the_bytes_do_not_reproduce(tmp_path):
    prov, _bundle = _record(tmp_path, BUNDLE3)
    record = yaml.safe_load(prov.read_text())
    record["inputs"]["chunks"]["sha256"] = "0" * 64
    prov.write_text(yaml.safe_dump(record, sort_keys=False))
    with pytest.raises(ValueError, match="do not reproduce"):
        rs.run_chunks(prov)
    del record["inputs"]["chunks"]
    prov.write_text(yaml.safe_dump(record, sort_keys=False))
    with pytest.raises(ValueError, match="inputs.chunks"):
        rs.run_chunks(prov)


def test_run_chunks_recovers_a_drifted_bundle_from_the_committed_version(tmp_path):
    prov, bundle = _record(tmp_path, BUNDLE3)
    bundle.write_text(BUNDLE3 + "drifted\n", encoding="utf-8")
    entry = {"commit": "a" * 40, "date": "2026-09-01", "md5": "x", "sha256": "y", "matched_on": ["md5"]}
    with mock.patch.object(pv, "bundle_bytes_for", return_value=(BUNDLE3.encode(), entry)) as found:
        run = rs.run_chunks(prov)
    assert found.call_args.args[0] == str(bundle)
    assert run["basis"] == {"source": "git blob", "path": str(bundle), "commit": "a" * 40}
    assert run["manifest"]["bundle_md5"] == hashlib.md5(BUNDLE3.encode()).hexdigest()
    with mock.patch.object(pv, "bundle_bytes_for", return_value=None):
        with pytest.raises(ValueError, match="no committed version"):
            rs.run_chunks(prov)


def test_the_source_manifest_basis_compares_whichever_hash_the_run_kept():
    raw = SOURCE_MANIFEST
    assert rs.source_manifest_basis({}, raw) == {"recorded": None, "same_bytes": None}
    same = {"inputs": {"source_manifest": {"path": "m.yaml", "md5": hashlib.md5(raw).hexdigest()}}}
    assert rs.source_manifest_basis(same, raw)["same_bytes"] is True
    other = {"inputs": {"source_manifest": {"path": "m.yaml", "sha256": "0" * 64}}}
    assert rs.source_manifest_basis(other, raw)["same_bytes"] is False


def test_run_source_manifest_reads_the_bytes_the_run_recorded(tmp_path):
    """`--at-run-commit` (#3050): the file on disk when it hashes to the
    run's record, else the committed version that does, by hash."""
    sm = tmp_path / "source_manifest.yaml"
    sm.write_bytes(SOURCE_MANIFEST)
    prov = tmp_path / "P_provenance.yaml"
    record = {"inputs": {"source_manifest": {"path": str(sm), "md5": hashlib.md5(SOURCE_MANIFEST).hexdigest()}}}
    with mock.patch.object(pv, "committed_bytes_for") as git:
        assert rs.run_source_manifest(record, prov) == (SOURCE_MANIFEST, {"source": "manifest on disk",
                                                                          "path": str(sm)})
    git.assert_not_called()
    sm.write_bytes(SOURCE_MANIFEST + b"# edited since the run\n")
    entry = {"commit": "b" * 40, "date": "2026-09-01", "md5": "x", "sha256": "y", "matched_on": ["md5"]}
    with mock.patch.object(pv, "committed_bytes_for", return_value=(SOURCE_MANIFEST, entry)) as git:
        raw, basis = rs.run_source_manifest(record, prov)
    assert git.call_args.args == (str(sm),)
    assert git.call_args.kwargs == {"md5": hashlib.md5(SOURCE_MANIFEST).hexdigest(), "sha256": None}
    assert raw == SOURCE_MANIFEST and basis == {"source": "git blob", "path": str(sm), "commit": "b" * 40}
    # Every hash the run kept must match the file on disk (#3443): with md5
    # and sha256 recorded and only the md5 matching, the disk is not used.
    sm.write_bytes(SOURCE_MANIFEST)
    both = {"inputs": {"source_manifest": {"path": str(sm), "md5": hashlib.md5(SOURCE_MANIFEST).hexdigest(),
                                           "sha256": "0" * 64}}}
    with mock.patch.object(pv, "committed_bytes_for", return_value=None) as git:
        with pytest.raises(ValueError, match="no committed version .* md5 and sha256"):
            rs.run_source_manifest(both, prov)
    assert git.call_args.kwargs == {"md5": hashlib.md5(SOURCE_MANIFEST).hexdigest(), "sha256": "0" * 64}
    both["inputs"]["source_manifest"]["sha256"] = hashlib.sha256(SOURCE_MANIFEST).hexdigest()
    with mock.patch.object(pv, "committed_bytes_for") as git:
        assert rs.run_source_manifest(both, prov)[1] == {"source": "manifest on disk", "path": str(sm)}
    git.assert_not_called()
    sm.write_bytes(SOURCE_MANIFEST + b"# edited since the run\n")
    with mock.patch.object(pv, "committed_bytes_for", return_value=None):
        with pytest.raises(ValueError, match="no committed version .* md5"):
            rs.run_source_manifest(record, prov)
    with mock.patch.object(pv, "committed_bytes_for", side_effect=pv.GitUnavailable("shallow clone")):
        with pytest.raises(pv.GitUnavailable, match="shallow"):
            rs.run_source_manifest(record, prov)


def test_run_source_manifest_anchors_a_relative_path_on_the_records_tree(tmp_path, monkeypatch):
    """The corpus records `inputs.source_manifest.path` relative
    (`data/preprocessed/source_manifest.yaml`). It resolves against the tree
    that holds the record's `data/d4d_concatenated`, never the caller's
    working directory (#3505): a run inspected from elsewhere reads the file
    beside its record, and a record outside a corpus tree does not borrow
    whatever the working directory happens to hold."""
    rel = "data/preprocessed/source_manifest.yaml"
    tree = tmp_path / "tree"
    sm = tree / rel
    sm.parent.mkdir(parents=True)
    sm.write_bytes(SOURCE_MANIFEST)
    prov = tree / "data" / "d4d_concatenated" / "m_core" / "L" / "P_provenance.yaml"
    prov.parent.mkdir(parents=True)
    record = {"inputs": {"source_manifest": {"path": rel, "md5": hashlib.md5(SOURCE_MANIFEST).hexdigest()}}}
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    with mock.patch.object(pv, "committed_bytes_for") as git:
        assert rs.run_source_manifest(record, prov) == (SOURCE_MANIFEST, {"source": "manifest on disk",
                                                                          "path": str(sm)})
    git.assert_not_called()
    # A working directory holding a same-named file with the same bytes is
    # still not where the record's tree is.
    decoy = elsewhere / rel
    decoy.parent.mkdir(parents=True)
    decoy.write_bytes(SOURCE_MANIFEST)
    with mock.patch.object(pv, "committed_bytes_for") as git:
        assert rs.run_source_manifest(record, prov)[1] == {"source": "manifest on disk", "path": str(sm)}
    git.assert_not_called()
    # A record outside any corpus tree has no base for a relative path: the
    # disk is not read (not even the working directory's matching file) and
    # the bytes are looked for in git under the path as recorded.
    loose = tmp_path / "loose" / "P_provenance.yaml"
    loose.parent.mkdir()
    with mock.patch.object(pv, "committed_bytes_for", return_value=None) as git:
        with pytest.raises(ValueError, match="no committed version of data/preprocessed/source_manifest.yaml"):
            rs.run_source_manifest(record, loose)
    assert git.call_args.args == (rel,)


def test_a_git_blob_basis_is_labelled_with_the_commit_it_was_found_at():
    """The basis keys the hash as `commit`; the text line must not present a
    commit hash as a blob's (#3476)."""
    assert rs.basis_label({"source": "git blob", "path": "m.yaml", "commit": "a" * 40}) == \
        f"git blob at commit {'a' * 12}"
    assert rs.basis_label({"source": "bundle on disk", "path": "b.txt"}) == "bundle on disk"
    assert rs.basis_label({}) == "?"
    manifest, texts = _manifest(BUNDLE3)
    out = rs.source_dependence(_acceptance_receipt(manifest["bundle_md5"]), manifest, SOURCE_MANIFEST, "P",
                               FULL, texts)
    text = "\n".join(rs.render({**out, "run": {"bundle_basis": {"source": "git blob", "commit": "c" * 40}}}))
    assert f"chunks from the git blob at commit {'c' * 12}" in text


def test_run_source_manifest_refuses_a_run_that_recorded_no_path_or_no_hash(tmp_path):
    prov = tmp_path / "P_provenance.yaml"
    unselected = {"inputs": {"source_manifest": {"path": None, "basis": "the bundle is not the one it declares"}}}
    with pytest.raises(ValueError, match="no source manifest path .*the bundle is not the one it declares"):
        rs.run_source_manifest(unselected, prov)
    with pytest.raises(ValueError, match="no source manifest path"):
        rs.run_source_manifest({}, prov)
    with pytest.raises(ValueError, match="no source manifest hash"):
        rs.run_source_manifest({"inputs": {"source_manifest": {"path": "m.yaml"}}}, prov)


def _tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_the_command_reports_and_writes_nothing(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from data_sheets_schema.cli import cli
    manifest, _texts = _manifest(BUNDLE3)
    sm = tmp_path / "source_manifest.yaml"
    sm.write_bytes(SOURCE_MANIFEST)
    concat = tmp_path / "concat"
    core, full_dir = concat / "m_core" / "L", concat / "m" / "L"
    core.mkdir(parents=True)
    full_dir.mkdir(parents=True)
    prov, _bundle = _record(core, BUNDLE3, source_manifest={"path": str(sm), "sha256": hashlib.sha256(SOURCE_MANIFEST).hexdigest()})
    (core / "P_coverage_receipt.yaml").write_text(yaml.safe_dump(_acceptance_receipt(manifest["bundle_md5"])))
    (full_dir / "P_d4d.yaml").write_text("# D4D Datasheet for P Dataset\n" + yaml.safe_dump(FULL))
    monkeypatch.setattr(pv, "CONCAT_DIR", concat)
    before = _tree(tmp_path)
    args = ["--manifest", str(sm), "receipts", "sources", "--method", "m", "--label", "L", "--project", "P"]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    out = result.output
    assert "paths 2, from 2 of 2 extracted pairs" in out
    assert "cited by exactly one document: 2/2 (1.000)" in out
    assert "tier 4         sole 2/2 (1.000)" in out
    assert "(the bytes the run recorded)" in out
    assert "1 of 2 screened paths" in out
    assert "description = 'sustained vowel phonation" in out and "c001 release (tier 1)" in out
    assert "#2819" in out and "not checked here" in out
    result = CliRunner().invoke(cli, args + ["--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["lower_tier_with_higher_tier_token_match"]["count"] == 1
    assert report["run"]["bundle_basis"]["source"] == "bundle on disk"
    assert [r["path"] for r in report["by_path"]] == ["description", "withdrawal"]
    assert _tree(tmp_path) == before                   # read-only: no provenance, receipt or sidecar write
    result = CliRunner().invoke(cli, ["--manifest", str(sm), "receipts", "sources", "--method", "m",
                                      "--label", "L", "--project", "Q"])
    assert result.exit_code != 0 and "no " in result.output


def test_at_run_commit_reads_tiers_from_the_manifest_the_run_recorded(tmp_path, monkeypatch):
    """The selected manifest ranks the webinar at tier 1, so by today's
    ranking nothing sits above it; the run recorded the manifest that ranks
    it tier 4, and `--at-run-commit` reads that one (#3050)."""
    from click.testing import CliRunner

    from data_sheets_schema.cli import cli
    manifest, _texts = _manifest(BUNDLE3)
    recorded = tmp_path / "recorded_manifest.yaml"
    recorded.write_bytes(SOURCE_MANIFEST)
    today = tmp_path / "source_manifest.yaml"
    today.write_bytes(SOURCE_MANIFEST.replace(b"  1: [data resource]\n  2: [documentation]\n  4: [tutorial]\n",
                                              b"  1: [data resource, tutorial]\n  2: [documentation]\n"))
    assert today.read_bytes() != SOURCE_MANIFEST
    assert rs.source_dependence(_acceptance_receipt(manifest["bundle_md5"]), manifest, today.read_bytes(), "P",
                                FULL, _texts)["lower_tier_with_higher_tier_token_match"]["count"] == 0
    concat = tmp_path / "concat"
    core, full_dir = concat / "m_core" / "L", concat / "m" / "L"
    core.mkdir(parents=True)
    full_dir.mkdir(parents=True)
    _record(core, BUNDLE3, source_manifest={"path": str(recorded), "md5": hashlib.md5(SOURCE_MANIFEST).hexdigest()})
    (core / "P_coverage_receipt.yaml").write_text(yaml.safe_dump(_acceptance_receipt(manifest["bundle_md5"])))
    (full_dir / "P_d4d.yaml").write_text("# D4D Datasheet for P Dataset\n" + yaml.safe_dump(FULL))
    monkeypatch.setattr(pv, "CONCAT_DIR", concat)
    before = _tree(tmp_path)
    args = ["--manifest", str(today), "receipts", "sources", "--method", "m", "--label", "L", "--project", "P"]
    default = json.loads(CliRunner().invoke(cli, args + ["--json"]).output)
    assert default["lower_tier_with_higher_tier_token_match"]["count"] == 0
    assert default["run"]["source_manifest_basis"]["same_bytes"] is False
    result = CliRunner().invoke(cli, args + ["--at-run-commit", "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["lower_tier_with_higher_tier_token_match"]["count"] == 1
    assert report["source_manifest_sha256"] == hashlib.sha256(SOURCE_MANIFEST).hexdigest()
    assert report["run"]["source_manifest_bytes"] == {"source": "manifest on disk", "path": str(recorded)}
    # run.source_manifest is a path in both modes; the basis is in
    # source_manifest_bytes, and only the text line joins the two (#3492)
    assert report["run"]["source_manifest"] == str(recorded)
    assert default["run"]["source_manifest"] == str(today)
    assert report["run"]["source_manifest_basis"]["same_bytes"] is True
    assert report["non_checks"][-1] == rs.NON_CHECK_AT_RUN_COMMIT and report["non_checks"] != default["non_checks"]
    # the default non-check names what the flag reads: the recorded bytes, by
    # hash, not the manifest at the run's commit (#3445)
    assert "bytes the run recorded" in default["non_checks"][-1]
    assert "recovered by hash rather than from the run's commit" in default["non_checks"][-1]
    text = CliRunner().invoke(cli, args + ["--at-run-commit"]).output
    assert f"tiers: {recorded} (manifest on disk) sha256" in text and "(the bytes the run recorded)" in text
    # recovered from git, the hash on the line is the commit the blob was
    # found at, and the line says so (#3476)
    entry = {"commit": "b" * 40, "date": "2026-09-01", "md5": "x", "sha256": "y", "matched_on": ["md5"]}
    recorded.write_bytes(SOURCE_MANIFEST + b"# edited\n")
    with mock.patch.object(pv, "committed_bytes_for", return_value=(SOURCE_MANIFEST, entry)):
        text = CliRunner().invoke(cli, args + ["--at-run-commit"]).output
    assert f"tiers: {recorded} (git blob at commit {'b' * 12}) sha256" in text, text
    with mock.patch.object(pv, "committed_bytes_for", return_value=(SOURCE_MANIFEST, entry)):
        report = json.loads(CliRunner().invoke(cli, args + ["--at-run-commit", "--json"]).output)
    assert report["run"]["source_manifest"] == str(recorded)                   # a path, not a label (#3492)
    assert report["run"]["source_manifest_bytes"] == {"source": "git blob", "path": str(recorded),
                                                      "commit": "b" * 40}
    recorded.write_bytes(SOURCE_MANIFEST)
    with mock.patch.object(pv, "committed_bytes_for", side_effect=pv.GitUnavailable("shallow clone")):
        recorded.write_bytes(SOURCE_MANIFEST + b"# edited\n")
        result = CliRunner().invoke(cli, args + ["--at-run-commit"])
    assert result.exit_code != 0 and "shallow clone" in result.output
    recorded.write_bytes(SOURCE_MANIFEST)
    assert _tree(tmp_path) == before                   # read-only


# ---------------------------------------------------------------- corpus
V8_VOICE = "2026-09-04f_claude-opus-5-api-generic-v8_rep1"
#: fig19's inputs for this record — notes/figures/set_2303/fig19_source_dependence.csv
#: (field_paths_citing, field_paths_sole_source) and _records.csv, built by
#: scripts/figures/fig19_source_dependence.py at 6f1407ca6 on the #2303
#: figure branch — in the same unit, over the same 181 paths.
FIG19_VOICE_V8_REP1 = {
    "physionet_3_1_0": (64, 52), "physionet_3_0_0": (2, 1), "physionet_1_1": (5, 1),
    "physionet_pediatric_1_1_0": (2, 1), "project_documentation": (112, 87),
    "documentation_repository": (2, 1), "data_transfer_use_agreement": (11, 5), "irb_protocol": (9, 3),
    "feasibility_publication": (1, 1), "audiomics_white_paper": (1, 1), "nih_reporter_project": (3, 2)}


@pytest.mark.corpus
def test_a_committed_v8_voice_record_reproduces_fig19():
    core = ROOT / "data/d4d_concatenated/claudecode_api_core" / V8_VOICE
    prov = core / "VOICE_provenance.yaml"
    if not prov.exists():
        pytest.skip("the v8 VOICE record is not on disk")
    before = prov.read_bytes()
    try:
        run = rs.run_chunks(prov)
    except pv.GitUnavailable as exc:                   # a drifted bundle needs the history
        pytest.skip(f"the record's bytes need git history: {exc}")
    full = yaml.safe_load((ROOT / "data/d4d_concatenated/claudecode_api" / V8_VOICE / "VOICE_d4d.yaml").read_text())
    out = rs.source_dependence(rc.load_receipt(core / "VOICE_coverage_receipt.yaml"), run["manifest"],
                               (ROOT / "data/preprocessed/source_manifest.yaml").read_bytes(), "VOICE", full,
                               run["texts"])
    assert out["paths"] == 181
    assert out["entries"]["unresolved_in_final"] == 8
    assert out["single_document"]["paths"] == 155                 # 0.856354
    assert {d["document"]: (d["paths_citing"], d["paths_sole"]) for d in out["documents"]} == FIG19_VOICE_V8_REP1
    assert round(next(d for d in out["documents"] if d["document"] == "physionet_3_1_0")["sole_share"], 6) == 0.287293
    assert round(next(d for d in out["documents"] if d["document"] == "project_documentation")["sole_share"], 6) == 0.480663
    assert out["preamble"]["citations"] == 0
    assert prov.read_bytes() == before


#: The 24 records fig19 reads (#2303): the reference rescore's inputs.
REFERENCE = ROOT / "notes/reference_rescore_2026-09-12_cborg_runtime/manifest.json"


def _fig19_runs() -> list[tuple]:
    """(project, core directory, receipt, run chunks, final record) for each
    of the 24 records, loaded once per process; skips where they cannot be."""
    if _FIG19_RUNS:
        return _FIG19_RUNS
    if not REFERENCE.exists():
        pytest.skip("the reference rescore manifest is not on disk")
    runs = []
    for inp in sorted({j["input"] for j in json.loads(REFERENCE.read_text())["jobs"]}):
        _data, _concat, method, label, name = Path(inp).parts
        project = name[:-len("_d4d.yaml")]
        core = ROOT / "data/d4d_concatenated" / f"{method}_core" / label
        prov = core / f"{project}_provenance.yaml"
        if not prov.exists():
            pytest.skip(f"{prov} is not on disk")
        try:
            run = rs.run_chunks(prov)
        except pv.GitUnavailable as exc:               # a drifted bundle needs the history
            pytest.skip(f"the record's bytes need git history: {exc}")
        runs.append((project, core, rc.load_receipt(core / f"{project}_coverage_receipt.yaml"), run,
                     yaml.safe_load((ROOT / inp).read_text())))
    assert len(runs) == 24
    _FIG19_RUNS.extend(runs)
    return _FIG19_RUNS


_FIG19_RUNS: list[tuple] = []


def _fig19_reports(**floors) -> list[tuple[str, dict]]:
    source_manifest = (ROOT / "data/preprocessed/source_manifest.yaml").read_bytes()
    return [(project, rs.source_dependence(receipt, run["manifest"], source_manifest, project, full,
                                           run["texts"], **floors))
            for project, _core, receipt, run, full in _fig19_runs()]


@pytest.mark.corpus
def test_the_screen_figures_the_module_states_on_the_24_fig19_records():
    """The counts the MIN_MATCH_* comment and the module docstring state
    (#3121, #3122), so a floor change cannot leave them stale."""
    def screen(**floors):
        return [o["lower_tier_with_higher_tier_token_match"] for _p, o in _fig19_reports(**floors)]

    reports = _fig19_reports()
    s = [o["lower_tier_with_higher_tier_token_match"] for _p, o in reports]
    assert sum(x["count"] for x in s) == 104
    assert sum(x["screened"] for x in s) == 1336 and sum(x["verbatim"] for x in s) == 30
    by_project = {}
    for (project, _o), x in zip(reports, s):
        by_project[project] = by_project.get(project, 0) + x["count"]
    assert by_project == {"AI_READI": 18, "CHORUS": 1, "CM4AI": 76, "VOICE": 9}
    assert sum(x["count"] for x in screen(min_tokens=3, min_chars=0)) == 104
    assert sum(x["count"] for x in screen(min_tokens=2, min_chars=12)) == 120
    assert sum(x["count"] for x in screen(min_tokens=1, min_chars=12)) == 123
    loosest = screen(min_tokens=1, min_chars=0)
    assert sum(x["count"] for x in loosest) == 152
    assert sum(x["outcomes"]["below_floor"] for x in loosest) == 42        # every one a value with no token


@pytest.mark.corpus
def test_the_supersession_figures_the_module_states_on_the_24_fig19_records():
    """The supersession screen's counts in the module docstring (#3049)."""
    reports = _fig19_reports()
    s = [o["superseded_with_replacement_token_match"] for _p, o in reports]
    outcomes = Counter()
    for x in s:
        outcomes.update(x["outcomes"])
    assert outcomes["replacement_match"] + outcomes["no_replacement_match"] + outcomes["below_floor"] == 74
    assert outcomes["no_replacement_chunk"] == 0
    # 83 paths are cited only to superseded sources (#3441): the 74 screened
    # above plus 9 exempt ones the screen passes through, and every one of
    # the 83 has a chunk of some replacement down its chain in its bundle.
    only_superseded, with_chunk = Counter(), 0
    for _project, o in reports:
        docs = o["documents"]
        docs = docs if isinstance(docs, dict) else {d["document"]: d for d in docs}
        for r in o["by_path"]:
            if not r["documents"] or not all(docs[d].get("superseded_by") for d in r["documents"]):
                continue
            only_superseded[r["supersession_screen"]] += 1
            chain, seen = [docs[d].get("superseded_by") for d in r["documents"]], set()
            while chain:
                d = chain.pop()
                if d is not None and d not in seen:
                    seen.add(d)
                    chain.append(docs[d].get("superseded_by"))
            with_chunk += any(docs[d]["chunks"] for d in seen - set(r["documents"]))
    assert only_superseded == {"no_replacement_match": 50, "replacement_match": 12, "below_floor": 12,
                               "exempt": 9}
    assert sum(only_superseded.values()) == 83 and with_chunk == 83
    assert sum(x["screened"] for x in s) == 62 and sum(x["count"] for x in s) == 12
    assert sum(x["verbatim"] for x in s) == 1 and sum(x["also_higher_tier_match"] for x in s) == 0
    replaced = Counter()
    for (project, _o), x in zip(reports, s):
        for ex in x["examples"]:
            replaced[(project, *sorted({h["document"] for h in ex["replacement_chunks"]}))] += 1
    assert replaced == {("CM4AI", "june_2026_dataverse_release"): 8, ("VOICE", "physionet_3_1_0"): 4}
    assert all(x["examples_truncated"] is None for x in s)


@pytest.mark.corpus
def test_the_24_fig19_records_rank_the_same_at_their_run_commit():
    """`--at-run-commit` (#3050) on the 24 fig19 records: every one reads its
    manifest from a git blob (12 md5 41408d…, 12 6c71e8…), and those bytes
    rank every cited document as today's manifest does, so fig19 and both
    screens are unchanged by the choice."""
    today = (ROOT / "data/preprocessed/source_manifest.yaml").read_bytes()
    seen = Counter()
    for project, core, receipt, run, full in _fig19_runs():
        try:
            raw, basis = rs.run_source_manifest(run["record"], core / f"{project}_provenance.yaml")
        except pv.GitUnavailable as exc:
            pytest.skip(f"the recorded manifests need git history: {exc}")
        seen[(basis["source"], hashlib.md5(raw).hexdigest()[:6])] += 1
        a = rs.source_dependence(receipt, run["manifest"], today, project, full, run["texts"])
        b = rs.source_dependence(receipt, run["manifest"], raw, project, full, run["texts"])
        for key in ("by_tier", "documents", "lower_tier_with_higher_tier_token_match",
                    "superseded_with_replacement_token_match"):
            assert a[key] == b[key], (project, core.name, key)
    assert seen == {("git blob", "41408d"): 12, ("git blob", "6c71e8"): 12}


@pytest.mark.corpus
def test_the_join_figures_the_module_states_on_the_24_fig19_records():
    """The by-index join the module docstring states (#3123, #3190): every
    path left unresolved, by its identity basis (`receipts.remap_path`
    against the phase-1 snapshot) and by where its by-index read stops in
    the final record, and the counted paths the identity join reads
    elsewhere."""
    elsewhere = {}
    unresolved = Counter()
    unresolved_at_a_held_index = {}
    for (project, core, receipt, run, full), (_p, report) in zip(_fig19_runs(), _fig19_reports()):
        snapshot = yaml.safe_load((core / "intermediate" / f"{project}_full.yaml").read_text())
        for row in report["by_path"]:
            basis = rc.remap_path(row["path"], snapshot, full)["basis"]
            if basis not in ("same", "same_key_stripped", "not_in_snapshot"):
                elsewhere[basis] = elsewhere.get(basis, 0) + 1
        known = {c["id"] for c in run["manifest"]["chunks"]}
        slots = {str(p.get("slot") or "") for e in receipt.get("chunks") or []
                 if isinstance(e, dict) and e.get("status") == "extracted" and e.get("id") in known
                 for p in e.get("extracted") or [] if isinstance(p, dict)}
        left = {s for s in slots if s.strip()} - {row["path"] for row in report["by_path"]}
        assert len(left) == report["paths_unresolved_in_final"]
        for path in left:
            remap = rc.remap_path(path, snapshot, full)
            key = (remap["basis"], _where_the_read_stops(full, path))
            unresolved[key] += 1
            if _moved_or_dropped(key[0]) and key[1] != "index_gone":
                # where the identity join would read it, when the value is still there
                there = remap["path"] if remap["path"] and _where_the_read_stops(full, remap["path"]) == "resolves" \
                    else None
                unresolved_at_a_held_index[(project, core.name, path)] = (*key, there)
    assert {k: n for k, n in unresolved.items() if _moved_or_dropped(k[0])} == {
        ("entry_dropped", "index_gone"): 28, ("by_overlap", "index_gone"): 2, ("ambiguous", "index_gone"): 1,
        ("by_overlap", "leaf_missing"): 1, ("entry_dropped", "leaf_missing"): 1}
    assert unresolved_at_a_held_index == {
        ("AI_READI", "2026-09-01_claude-opus-5-api-generic-v7_rep3", "distribution_formats[0].media_type"):
            ("by_overlap", "leaf_missing", "distribution_formats[2].media_type"),
        ("CHORUS", "2026-09-01_claude-opus-5-api-generic-v7_rep3", "creators[1].principal_investigator.name"):
            ("entry_dropped", "leaf_missing", None)}
    # the rest are not moved or dropped: a leaf reconciliation removed or
    # reshaped under an entry that stayed, and paths phase 1 never had
    assert {k: n for k, n in unresolved.items() if not _moved_or_dropped(k[0])} == {
        ("leaf_dropped", "leaf_missing"): 97, ("leaf_dropped", "shape"): 5, ("unresolved", "shape"): 26,
        ("not_in_snapshot", "leaf_missing"): 3}
    assert sum(unresolved.values()) == 164
    assert elsewhere == {"entry_dropped": 11, "by_overlap": 4, "by_id": 1, "by_name": 1,
                         "by_variable_name": 1, "ambiguous": 1}

def _moved_or_dropped(basis: str) -> bool:
    """A `receipts.remap_path` basis for an entry reconciliation moved or dropped."""
    return basis in ("entry_dropped", "ambiguous") or basis.startswith("by_")


def _where_the_read_stops(record, path: str) -> str:
    """Where a by-index read of `path` stops in `record`: `index_gone` (a list
    shorter than the index), `leaf_missing` (a mapping without the key),
    `shape` (a step into a value of the other kind), `empty` (it reaches an
    unpopulated value), or `resolves`."""
    cur = record
    for part in re.findall(r"[\w]+|\[\d+\]", path):
        if part.startswith("["):
            if not isinstance(cur, list):
                return "shape"
            if int(part[1:-1]) >= len(cur):
                return "index_gone"
            cur = cur[int(part[1:-1])]
        else:
            if not isinstance(cur, dict):
                return "shape"
            if part not in cur:
                return "leaf_missing"
            cur = cur[part]
    return "resolves" if rc._populated(cur) else "empty"
