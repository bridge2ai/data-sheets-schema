"""Receipt origin in the provenance record and the gate summaries (#2933).

`receipt_origin` classifies a receipt's snippets from the run's transcript and
writes nothing; `receipt_origin_record` is what `receipts.origin` keeps of it,
and the line printed beside "snippets verified". Synthetic transcripts only:
a contemporaneous snippet, a Phase 1 correction, a Phase 3 back-port, and a
run with no transcript.
"""
import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import backfill_checks as bc
from data_sheets_schema import canary
from data_sheets_schema import receipt_origin as ro
from data_sheets_schema import receipt_origin_record as ror
from tests.test_receipt_origin import PRE, SECRET, Run, receipt_text

PHASE1 = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701"),
                                ("license", "CC BY 4.0 license")]),
                      ("c002", [("description", "a multimodal collection")]))
FINAL = receipt_text(("c001", [("title", "The CHORUS dataset"), ("funders[0].grant_id", "OT2OD032701"),
                               ("license", "CC BY 4.0 license")]),
                     ("c002", [("description", "a multimodal collection")]),
                     ("c003", [("creators[0].name", SECRET)]))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _three_origins(root):
    """Three snippets written before the draft, one added before `derive
    core`, one back-ported after it; the receipt on disk is the last Write."""
    r = Run(root)
    r.write(r.receipt, PRE)
    r.write(r.full, "id: x\n")
    r.write(r.receipt, PHASE1)
    r.derive()
    r.write(r.receipt, FINAL)
    r.receipt.write_text(r.last_receipt, encoding="utf-8")
    return r, r.transcript()


def _receipts_block(origin, receipt):
    """A checked receipts block of `receipt`, as `receipts.block_for` pins it."""
    return {"checked": True, "expected": True, "artifacts": {"receipt": {"path": str(receipt), "sha256": _sha(receipt)}},
            "origin": origin}


# ---------------------------------------------------------------- the block
def test_each_origin_is_recorded_with_the_instrument_and_its_non_checks(tmp_path):
    r, transcript = _three_origins(tmp_path)
    block = ror.for_record(None, r.receipt, r.full, transcripts=[transcript], recorded_by="d4d receipts check")
    assert block["status"] == "checked", block["reasons"]
    assert block["origin"] == {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 1}
    assert (block["post_draft"], block["removed_contemporaneous"], block["readdressed"]) == (2, 0, 0)
    assert {(e["slot"], e["origin"]) for e in block["post_draft_entries"]} == {
        ("license", "phase1_correction"), ("creators[0].name", "phase3_backport")}
    assert block["instrument"] == ro.INSTRUMENT
    assert block["non_checks"] == list(ro.NON_CHECKS)               # the disclosure beside the counts
    assert block["recorded_by"] == "d4d receipts check"
    # No local path and no snippet text: the transcript by name and bytes,
    # the receipt by its sha256 (the receipts block names its path).
    assert block["transcripts"] == [{"name": "transcript.jsonl", "sha256": _sha(transcript),
                                     "lines": len(transcript.read_text().splitlines())}]
    assert block["receipt"]["sha256"] == _sha(r.receipt) and "path" not in block["receipt"]
    dumped = json.dumps(block)
    assert str(tmp_path) not in dumped and SECRET not in dumped


def test_a_receipt_written_before_the_draft_is_all_contemporaneous(tmp_path):
    r = Run(tmp_path)
    r.write(r.receipt, PRE)
    r.write(r.full, "id: x\n")
    r.derive()
    r.receipt.write_text(r.last_receipt, encoding="utf-8")
    block = ror.for_record(None, r.receipt, r.full, transcripts=[r.transcript()])
    assert block["origin"] == {"contemporaneous": 3, "phase1_correction": 0, "phase3_backport": 0}
    counts = ror.split(_receipts_block(block, r.receipt))
    assert (counts["contemporaneous"], counts["post_draft"]) == (3, 0)


def test_a_readdress_only_rewrite_adds_nothing_and_counts_the_slots_moved(tmp_path):
    """The issue's acceptance case, through to the record and its line."""
    r = Run(tmp_path)
    r.write(r.receipt, PRE)
    r.write(r.full, "id: x\n")
    r.write(r.receipt, receipt_text(("c001", [("name", "The CHORUS dataset"), ("funders[1].grant_id", "OT2OD032701")]),
                                    ("c002", [("keywords", "a multimodal collection")])))
    r.receipt.write_text(r.last_receipt, encoding="utf-8")
    block = ror.for_record(None, r.receipt, r.full, transcripts=[r.transcript()])
    assert block["deltas"]["draft_to_final"] == {"removed": 0, "added": 0}
    counts = ror.split(_receipts_block(block, r.receipt))
    assert (counts["contemporaneous"], counts["post_draft"], counts["removed_contemporaneous"],
            counts["readdressed"]) == (3, 0, 0, 3)
    assert ror.line(_receipts_block(block, r.receipt)).endswith("0 contemporaneous removed · 3 re-addressed")


def assert_unclassified(block):
    assert block["status"] == "unknown"
    for key in ("origin", "snippets", "deltas", "post_draft", "post_draft_entries", "readdressed", "by_chunk"):
        assert key not in block, key                                # never a classification, never contemporaneous


def test_no_transcript_is_unknown_with_a_reason_and_classifies_nothing(tmp_path):
    r, _ = _three_origins(tmp_path)
    block = ror.for_record(None, r.receipt, r.full)
    assert_unclassified(block)
    assert block["reasons"] == [ror.NO_TRANSCRIPT] and block["transcripts"] == []
    assert block["instrument"] == ro.INSTRUMENT and "non_checks" not in block    # nothing was read, nothing claimed
    assert not ror.measured(block)
    rb = _receipts_block(block, r.receipt)
    assert ror.split(rb) is None
    assert ror.line(rb) == f"receipt origin: unknown — {ror.NO_TRANSCRIPT}"
    api = ror.for_record(None, r.receipt, r.full, api_path=True)
    assert_unclassified(api)
    assert api["reasons"] == [ror.API_PATH]


@pytest.mark.parametrize("damage", ["missing", "truncated"])
def test_an_unreadable_or_malformed_transcript_is_unknown_not_contemporaneous(tmp_path, damage):
    r, transcript = _three_origins(tmp_path)
    if damage == "missing":
        transcript.unlink()
    else:
        transcript.write_bytes(transcript.read_bytes()[:-1])         # last line unterminated
    block = ror.for_record(None, r.receipt, r.full, transcripts=[transcript])
    assert_unclassified(block)
    assert any(("cannot be read" if damage == "missing" else "malformed") in reason for reason in block["reasons"])
    assert ror.measured(block) is (damage == "truncated")            # read and found wanting; never read
    assert ror.split(_receipts_block(block, r.receipt)) is None


# ------------------------------------------------- a writer with no transcript
def test_a_measurement_is_kept_while_the_receipt_is_the_one_it_read(tmp_path):
    r, transcript = _three_origins(tmp_path)
    measured = ror.for_record(None, r.receipt, r.full, transcripts=[transcript], recorded_by="d4d receipts check")
    kept = ror.for_record(deepcopy(measured), r.receipt, r.full)
    assert kept == measured
    assert ror.for_record(deepcopy(measured), r.receipt, r.full, api_path=True) == measured


def test_a_changed_receipt_is_unknown_and_its_measurement_is_kept_under_prior(tmp_path):
    r, transcript = _three_origins(tmp_path)
    measured = ror.for_record(None, r.receipt, r.full, transcripts=[transcript])
    r.receipt.write_text(FINAL + "# edited after the run\n", encoding="utf-8")
    changed = ror.for_record(deepcopy(measured), r.receipt, r.full)
    assert_unclassified(changed)
    assert changed["prior"] == measured
    assert _sha(r.receipt) in changed["reasons"][0] and measured["receipt"]["sha256"] in changed["reasons"][0]
    assert ror.split(_receipts_block(changed, r.receipt)) is None
    # A second writer keeps the measurement, and restoring the bytes it read
    # restores it.
    again = ror.for_record(deepcopy(changed), r.receipt, r.full)
    assert again["prior"] == measured and again["status"] == "unknown"
    r.receipt.write_text(FINAL, encoding="utf-8")
    assert ror.for_record(deepcopy(again), r.receipt, r.full) == measured


def test_a_transcript_given_replaces_what_the_record_carried(tmp_path):
    r, transcript = _three_origins(tmp_path)
    stale = ror.unknown(ror.NO_TRANSCRIPT)
    fresh = ror.for_record(stale, r.receipt, r.full, transcripts=[transcript])
    assert fresh["status"] == "checked" and "prior" not in fresh


# ------------------------------------------------------------- the summaries
def test_the_split_is_shown_only_beside_the_receipt_it_was_measured_on(tmp_path):
    r, transcript = _three_origins(tmp_path)
    measured = ror.for_record(None, r.receipt, r.full, transcripts=[transcript])
    rb = _receipts_block(measured, r.receipt)
    assert ror.split(rb) == {"contemporaneous": 3, "phase1_correction": 1, "phase3_backport": 1,
                             "removed_contemporaneous": 0, "readdressed": 0, "post_draft": 2}
    assert ror.line(rb) == ("receipt origin: 3 contemporaneous · 1 phase-1 correction · 1 phase-3 back-port "
                            "(2 post-draft, unaccepted as semantic support until independent review, #2067) · "
                            "0 contemporaneous removed · 0 re-addressed")
    other = {**rb, "artifacts": {"receipt": {"sha256": "0" * 64}}}
    assert ror.split(other) is None
    assert "not shown" in ror.line(other)
    assert ror.split({**rb, "origin": {**measured, "origin": {**measured["origin"], "phase3_backport": True}}}) is None
    assert ror.line({"checked": True}) is None and ror.split(None) is None


def test_the_canary_reports_the_split_and_never_gates_it(tmp_path):
    r, transcript = _three_origins(tmp_path)
    floors = {"chunks": {"total": 3, "reviewed": 3}, "snippets": {"total": 5, "verified": 5, "mismatched": 0,
                                                                   "unchecked": 0}, "findings": []}
    without = {"receipts": {**_receipts_block(ror.unknown(ror.NO_TRANSCRIPT), r.receipt), **floors}}
    measured = ror.for_record(None, r.receipt, r.full, transcripts=[transcript])
    with_origin = {"receipts": {**_receipts_block(measured, r.receipt), **floors}}
    reported = canary.counts_from(with_origin, canary.REPORTED_ONLY)
    assert (reported["snippets contemporaneous"], reported["snippets post-draft"]) == (3, 2)
    absent = canary.counts_from(without, canary.REPORTED_ONLY)
    assert absent["snippets contemporaneous"] is None and absent["snippets post-draft"] is None
    gated = {name for name, _, _ in canary.METRICS}
    assert not {"snippets contemporaneous", "snippets post-draft"} & gated
    a, b = canary.verdict(with_origin, {}, baseline_requested=False), canary.verdict(without, {}, baseline_requested=False)
    assert a == b                                                   # no row, no floor reads it
    assert not [row for row in a["rows"] if "contemporaneous" in row["metric"] or "post-draft" in row["metric"]]
    assert {row["metric"] for row in a["rows"]} >= {"chunks unreviewed", "snippets unverified"}


def test_the_offline_canary_prints_the_origin_after_its_rows(tmp_path, monkeypatch):
    """`d4d api verdict` is the canary gate for a record after the fact, on any
    arm: the origin is printed beside the receipt rows, never as one."""
    from data_sheets_schema import provenance
    from data_sheets_schema.cli.api import api as api_cli
    r, transcript = _three_origins(tmp_path)
    measured = ror.for_record(None, r.receipt, r.full, transcripts=[transcript])
    path = tmp_path / "P_provenance.yaml"
    monkeypatch.setattr(provenance, "record_path_for", lambda *args, **kwargs: path)
    rows = [{"metric": "snippets unverified", "run": 0, "baseline_worst": 0}]
    monkeypatch.setattr(canary, "offline_verdict", lambda *args, **kwargs: {
        "status": canary.OK, "rows": rows, "regressions": [], "blind": [], "unbaselined": []})
    out = {}
    for name, origin in (("measured", measured), ("unread", ror.unknown(ror.NO_TRANSCRIPT)), ("absent", None)):
        receipts = _receipts_block(origin, r.receipt)
        if origin is None:
            del receipts["origin"]
        path.write_text(yaml.safe_dump({"receipts": receipts}), encoding="utf-8")
        result = CliRunner().invoke(api_cli, ["verdict", "--method", "claudecode_direct", "--label", "L",
                                              "--project", "P", "--canary-baseline", "x"])
        assert result.exit_code == 0, result.output
        out[name] = result.output.splitlines()
    rows_at = next(i for i, text in enumerate(out["measured"]) if "snippets unverified" in text)
    assert out["measured"][rows_at + 1] == f"   · {ror.line(_receipts_block(measured, r.receipt))}"
    assert out["unread"][rows_at + 1] == f"   · receipt origin: unknown — {ror.NO_TRANSCRIPT}"
    assert not [text for text in out["absent"] if "receipt origin" in text]


# --------------------------------------------------------- the record writers
def _pack(tmp_path):
    from tests.test_review_pack import Pack
    prov, _ = Pack()._run(tmp_path)
    receipt = prov.parent / "P_coverage_receipt.yaml"
    return prov, receipt


def _body(prov):
    return yaml.safe_load(bc._split_header(prov.read_text(encoding="utf-8"))[1])


def test_backfill_writes_unknown_with_no_transcript_and_keeps_a_measurement(tmp_path):
    prov, receipt = _pack(tmp_path)
    blocks = bc.compute(prov, only={"receipts"})
    assert blocks["receipts"]["checked"], blocks["receipts"].get("reason")
    assert_unclassified(blocks["receipts"]["origin"])
    assert blocks["receipts"]["origin"]["reasons"] == [ror.NO_TRANSCRIPT]
    line = bc.summarise(blocks)
    assert "origin" not in line and "contemporaneous" not in line   # the recorder's line during a run is unchanged
    # A measurement of this receipt, as `receipts check --write --transcript`
    # leaves it, survives a recomputation that reads no transcript.
    r = Run(tmp_path / "run")
    r.receipt, r.full = receipt, bc.record_paths(prov)["full"]
    r.write(r.receipt, receipt.read_text(encoding="utf-8"))
    r.write(r.full, "id: x\n")
    r.derive(full=str(r.full))
    measured = ror.for_record(None, receipt, r.full, transcripts=[r.transcript()], recorded_by="d4d receipts check")
    assert measured["status"] == "checked", measured["reasons"]
    bc.apply(prov, {"receipts": {**blocks["receipts"], "origin": measured}}, overwrite=True)
    again = bc.compute(prov, only={"receipts"})
    assert again["receipts"]["origin"] == measured
    assert again["receipts"]["recorded_by"] == bc.RECORDED_BY and measured["recorded_by"] == "d4d receipts check"
    assert ror.split(again["receipts"])["contemporaneous"] == measured["origin"]["contemporaneous"]
    summary = bc.summarise(again)
    assert f"({measured['origin']['contemporaneous']} contemporaneous, 0 post-draft)" in summary
    bc.apply(prov, again, overwrite=True)
    assert _body(prov)["receipts"]["origin"] == measured
    # An origin that is not this receipt's is not carried over its counts.
    receipt.write_text(receipt.read_text(encoding="utf-8") + "# edited\n", encoding="utf-8")
    moved = bc.compute(prov, only={"receipts"})["receipts"]["origin"]
    assert moved["status"] == "unknown" and moved["prior"] == measured


def test_an_api_path_record_says_why_there_is_no_transcript(tmp_path):
    prov, _ = _pack(tmp_path)
    body = _body(prov)
    body["api_usage"] = [{"phase": "full"}]
    prov.write_text("# header\n" + yaml.safe_dump(body), encoding="utf-8")
    origin = bc.compute(prov, only={"receipts"})["receipts"]["origin"]
    assert_unclassified(origin)
    assert origin["reasons"] == [ror.API_PATH]


def test_the_record_contract_takes_the_block_inside_receipts_only(tmp_path):
    """The brief's first question: `receipts` is an open AnyBlock, so the
    sub-block needs no contract change; a new top-level block would."""
    from data_sheets_schema import provenance
    from tests.test_record_required_values import record as minimal_record
    r, transcript = _three_origins(tmp_path)
    good = minimal_record()
    good["receipts"] = _receipts_block(ror.for_record(None, r.receipt, r.full, transcripts=[transcript]), r.receipt)
    assert provenance.check_record(good) == ([], None)
    good["receipts"]["origin"] = ror.for_record(good["receipts"]["origin"], r.receipt, r.full)
    assert provenance.check_record(good) == ([], None)
    good["receipts"]["origin"] = ror.unknown(ror.NO_TRANSCRIPT)
    assert provenance.check_record(good) == ([], None)
    top_level = {**minimal_record(), "receipt_origin": ror.unknown(ror.NO_TRANSCRIPT)}
    findings, failure = provenance.check_record(top_level)
    assert failure is None and any("receipt_origin" in f for f in findings)


# ------------------------------------------------------- d4d receipts check
def _checked_run(root):
    """A run whose receipt the receipts check verifies: six snippets before
    the draft, a seventh as a Phase 1 correction, an eighth back-ported after
    `derive core`."""
    from data_sheets_schema.chunking import build_manifest, dump_manifest
    from tests.test_receipts import BUNDLE, FULL, _receipt
    r = Run(root)
    bundle = root / "CHORUS_preprocessed.txt"
    bundle.write_text(BUNDLE, encoding="utf-8")
    manifest = root / "CHORUS_chunks.yaml"
    manifest.write_text(dump_manifest(build_manifest(bundle)))
    md5 = hashlib.md5(BUNDLE.encode()).hexdigest()
    final = _receipt(md5)

    def upto(n):
        rec = deepcopy(final)
        rec["chunks"][1]["extracted"] = final["chunks"][1]["extracted"][:n]
        return yaml.safe_dump(rec, sort_keys=False)
    full_text = f"# Source bundle: {bundle}\n" + yaml.safe_dump(FULL, sort_keys=False)
    r.write(r.receipt, upto(6))
    r.write(r.full, full_text)
    r.write(r.receipt, upto(7))
    r.derive()
    r.write(r.receipt, upto(8))
    r.receipt.write_text(r.last_receipt, encoding="utf-8")
    r.full.write_text(full_text, encoding="utf-8")
    prov = r.receipt.parent / "CHORUS_provenance.yaml"
    prov.write_text("# header\n" + yaml.safe_dump({
        "run": {"label": "L", "project": "CHORUS", "method": "claudecode_direct"},
        "inputs": {"bundle_path": str(bundle), "bundle_md5": md5, "receipt_expected": True,
                   "chunks": {"path": str(manifest), "chunk_count": 3}}}), encoding="utf-8")
    return r, r.transcript(), prov


@pytest.fixture
def check(monkeypatch):
    import data_sheets_schema.cli.receipts as cli

    def invoke(r, prov, *extra):
        monkeypatch.setattr(cli, "_run_paths", lambda *args: {"core_dir": r.receipt.parent, "full": r.full,
                                                              "provenance": prov})
        return CliRunner().invoke(cli.check, ["--method", "claudecode_direct", "--label", "L", "--project", "CHORUS",
                                              *extra])
    return invoke


def test_check_write_with_a_transcript_records_the_split_beside_snippets_verified(tmp_path, check):
    r, transcript, prov = _checked_run(tmp_path)
    result = check(r, prov, "--write", "--transcript", str(transcript))
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    summary = next(i for i, text in enumerate(lines) if "snippets" in text and "verified" in text)
    assert lines[summary + 1].strip().startswith("receipt origin: 6 contemporaneous · 1 phase-1 correction · "
                                                 "1 phase-3 back-port (2 post-draft"), result.output
    written = _body(prov)["receipts"]
    assert written["checked"] and written["recorded_by"] == "d4d receipts check"
    origin = written["origin"]
    assert origin["status"] == "checked" and origin["recorded_by"] == "d4d receipts check"
    assert origin["origin"] == {"contemporaneous": 6, "phase1_correction": 1, "phase3_backport": 1}
    assert {(e["slot"], e["origin"]) for e in origin["post_draft_entries"]} == {
        ("keywords", "phase1_correction"), ("file_collections[0]", "phase3_backport")}
    assert origin["receipt"]["sha256"] == written["artifacts"]["receipt"]["sha256"]
    assert origin["non_checks"] == list(ro.NON_CHECKS)
    reported = canary.counts_from(canary.checks_from_record(_body(prov)), canary.REPORTED_ONLY)
    assert (reported["snippets contemporaneous"], reported["snippets post-draft"]) == (6, 2)
    # Run again with no transcript, as the playbook does mid-run: the
    # measurement of this receipt is kept, and still printed.
    again = check(r, prov, "--write")
    assert again.exit_code == 0, again.output
    assert _body(prov)["receipts"]["origin"] == origin
    assert "receipt origin: 6 contemporaneous" in again.output


def test_check_without_a_transcript_prints_what_it_printed_before(tmp_path, check):
    r, _, prov = _checked_run(tmp_path)
    result = check(r, prov, "--write")
    assert result.exit_code == 0, result.output
    assert "receipt origin" not in result.output and "contemporaneous" not in result.output   # mid-run output unchanged
    origin = _body(prov)["receipts"]["origin"]
    assert_unclassified(origin)
    assert origin["reasons"] == [ror.NO_TRANSCRIPT]


def test_the_at_run_spellings_need_a_transcript(tmp_path, check):
    r, _, prov = _checked_run(tmp_path)
    result = check(r, prov, "--receipt-at-run", str(r.receipt))
    assert result.exit_code == 2 and "--transcript" in result.output
    assert "receipts" not in _body(prov)


def test_a_withheld_write_says_so_instead_of_ticking(tmp_path, check):
    """`apply` keeps a checked block over an unchecked recomputation (#907):
    the command printed "written", and the origin it read was dropped."""
    r, transcript, prov = _checked_run(tmp_path)
    assert check(r, prov, "--write").exit_code == 0
    kept = _body(prov)["receipts"]
    Path(_body(prov)["inputs"]["chunks"]["path"]).unlink()           # the recomputation can no longer check
    result = check(r, prov, "--write", "--transcript", str(transcript))
    assert result.exit_code == 0, result.output
    assert "✓ receipts block written" not in result.output
    assert "not written" in result.output and "receipt origin read here is not written either" in result.output
    assert _body(prov)["receipts"] == kept


# ------------------------------------------------------- d4d provenance record
def test_a_re_record_keeps_the_origin_it_cannot_read_again(tmp_path):
    """`provenance record` rewrites the record before its inline checks run,
    and no recorder holds the transcript: the measurement is handed through."""
    from data_sheets_schema.cli import provenance as prov_cli
    root, label = tmp_path, "2026-10-05_test_rep1"
    concat = root / "data" / "d4d_concatenated"
    full_dir, core_dir = concat / "claudecode_agent" / label, concat / "claudecode_agent_core" / label
    full_dir.mkdir(parents=True)
    core_dir.mkdir(parents=True)
    (root / "src" / "data_sheets_schema").mkdir(parents=True)
    header = ("# D4D Datasheet for TESTPROJ Dataset\n# Agent runtime: Claude Code\n# Provider: Anthropic\n"
              "# Model: claude-opus-5\n# Reasoning effort: high\n# Temperature: 0.0\n")
    body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
    (full_dir / "TESTPROJ_d4d.yaml").write_text(header + body)
    (core_dir / "TESTPROJ_d4d_core.yaml").write_text(header + body)
    (core_dir / "TESTPROJ_reconciliation.md").write_text("# report\n")
    bundle = root / "bundle.txt"
    bundle.write_text("source documents\n")
    r = Run(root / "run")
    r.receipt, r.full = core_dir / "TESTPROJ_coverage_receipt.yaml", full_dir / "TESTPROJ_d4d.yaml"
    r.write(r.receipt, PRE)
    r.write(r.full, header + body)
    r.write(r.receipt, FINAL)
    r.receipt.write_text(r.last_receipt, encoding="utf-8")
    measured = ror.for_record(None, r.receipt, r.full, transcripts=[r.transcript()], recorded_by="d4d receipts check")
    assert measured["status"] == "checked", measured["reasons"]
    record_path = core_dir / "TESTPROJ_provenance.yaml"

    def record():
        cwd = os.getcwd()
        os.chdir(root)
        try:
            return CliRunner().invoke(prov_cli.provenance, [
                "record", "--project", "TESTPROJ", "--method", "claudecode_agent", "--label", label,
                "--input-bundle", str(bundle), "--receipt-expected"])
        finally:
            os.chdir(cwd)

    first = record()
    assert first.exit_code == 0, first.output
    assert "receipt origin" not in first.output and "contemporaneous" not in first.output
    origin = _body(record_path)["receipts"]["origin"]
    assert_unclassified(origin)
    data = _body(record_path)
    data["receipts"]["origin"] = measured                            # as `receipts check --write --transcript` leaves it
    record_path.write_text("# header\n" + yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    second = record()
    assert second.exit_code == 0, second.output
    assert _body(record_path)["receipts"]["origin"] == measured
