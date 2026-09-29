"""A receipt's citations by source document and tier, read-only (#2937)."""
import hashlib
import json
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


@pytest.mark.corpus
def test_the_screen_and_join_figures_the_module_states_on_the_24_fig19_records():
    """The counts the MIN_MATCH_* comment and the module docstring state
    (#3121, #3122, #3123), so a floor or join change cannot leave them stale."""
    if not REFERENCE.exists():
        pytest.skip("the reference rescore manifest is not on disk")
    source_manifest = (ROOT / "data/preprocessed/source_manifest.yaml").read_bytes()
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

    def screen(**floors):
        out = [(project, rs.source_dependence(receipt, run["manifest"], source_manifest, project, full,
                                              run["texts"], **floors))
               for project, _core, receipt, run, full in runs]
        return out, [o["lower_tier_with_higher_tier_token_match"] for _p, o in out]

    reports, s = screen()
    assert sum(x["count"] for x in s) == 104
    assert sum(x["screened"] for x in s) == 1336 and sum(x["verbatim"] for x in s) == 30
    by_project = {}
    for (project, _o), x in zip(reports, s):
        by_project[project] = by_project.get(project, 0) + x["count"]
    assert by_project == {"AI_READI": 18, "CHORUS": 1, "CM4AI": 76, "VOICE": 9}
    assert sum(x["count"] for x in screen(min_tokens=3, min_chars=0)[1]) == 104
    assert sum(x["count"] for x in screen(min_tokens=2, min_chars=12)[1]) == 120
    assert sum(x["count"] for x in screen(min_tokens=1, min_chars=12)[1]) == 123
    loosest = screen(min_tokens=1, min_chars=0)[1]
    assert sum(x["count"] for x in loosest) == 152
    assert sum(x["outcomes"]["below_floor"] for x in loosest) == 42        # every one a value with no token

    # the join is by index: counted paths the #899 identity join reads elsewhere
    elsewhere = {}
    for (project, core, _receipt, _run, full), (_p, report) in zip(runs, reports):
        snapshot = yaml.safe_load((core / "intermediate" / f"{project}_full.yaml").read_text())
        for row in report["by_path"]:
            basis = rc.remap_path(row["path"], snapshot, full)["basis"]
            if basis not in ("same", "same_key_stripped", "not_in_snapshot"):
                elsewhere[basis] = elsewhere.get(basis, 0) + 1
    assert elsewhere == {"entry_dropped": 11, "by_overlap": 4, "by_id": 1, "by_name": 1,
                         "by_variable_name": 1, "ambiguous": 1}
