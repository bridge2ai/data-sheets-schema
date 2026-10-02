"""Versioned offline receipt completion, never a simulated empirical canary."""
import copy
from dataclasses import FrozenInstanceError, replace
from datetime import date
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner as runner, receipts as rc, rereceipt as rr
from data_sheets_schema.canary import receipt_floors
from data_sheets_schema.chunking import manifest_from_bytes
from tests.test_receipt_rereceipt import BUNDLE, FULL, _setup


def raw(value):
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).encode()


def inputs(record=None, receipt=None, **kwargs):
    manifest, _texts, current, _listed = _setup()
    return rr.Inputs(record=raw(FULL if record is None else record),
                     receipt=raw(current if receipt is None else receipt),
                     manifest=raw(manifest_from_bytes(BUNDLE.encode(), "fixture.txt")),
                     bundle=BUNDLE.encode(), schema=b"name: pinned_test_schema\n",
                     max_output_tokens=kwargs.get("max_output_tokens", 9000))


def answer(path="funders[0].grant_id", chunk="c002", snippet="Grant OT2OD032644"):
    return {"path": path, "receipt": {"chunk": chunk, "snippet": snippet}}


def test_only_new_verified_pairs_get_origin_and_idempotence_preserves_it():
    manifest, texts, receipt, listed = _setup()
    before = copy.deepcopy(receipt)
    answers = [answer(), answer("title", snippet="AI-READI dataset")]
    result = rc.apply_rereceipt(receipt, FULL, answers, texts,
                                listed=listed + ["title"], instrument_version=4)
    pairs = result["receipt"]["chunks"][1]["extracted"]
    assert pairs[0] == before["chunks"][1]["extracted"][0]
    assert pairs[-1]["origin"] == "rereceipt"
    assert (result["added"], result["already_present"]) == (1, 1)
    twice = rc.apply_rereceipt(result["receipt"], FULL, answers, texts,
                               listed=listed + ["title"], instrument_version=4)
    assert twice["receipt"] == result["receipt"]
    assert (twice["added"], twice["already_present"]) == (0, 2)
    assert receipt == before


@pytest.mark.parametrize("status, predicate", [
    ("nothing_relevant", {"reason": "references only"}),
    ("redundant_with", {"chunks": ["c002"]})])
def test_status_reversal_is_preserved_counted_and_does_not_add_reviewed_chunks(status, predicate):
    manifest, texts, receipt, listed = _setup()
    receipt["chunks"][2] = {"id": "c003", "status": status, **predicate}
    result = rc.apply_rereceipt(receipt, FULL, [answer("keywords", "c003", "Something else entirely")],
                                texts, listed=listed, instrument_version=4)
    block = rc.check(result["receipt"], manifest, texts, FULL, manifest["bundle_md5"], instrument_version=4)
    old = rc.check(receipt, manifest, texts, FULL, manifest["bundle_md5"])
    assert block["chunks"]["reviewed"] == old["chunks"]["reviewed"]
    assert block["rereceipt"]["status_reversal_count"] == 1
    assert block["rereceipt"]["status_reversals"] == [
        {"chunk": "c003", "prior": {"status": status, **predicate}}]
    assert block["snippets"]["by_origin"]["rereceipt"]["no_value_overlap"] == 1
    assert receipt_floors(block) == receipt_floors(rc.check(
        result["receipt"], manifest, texts, FULL, manifest["bundle_md5"]))


@pytest.mark.parametrize("status", ["missing", "duplicate_entry", "duplicate_of"])
def test_completion_cannot_manufacture_chunk_review_coverage(status):
    _m, _t, receipt, _l = _setup()
    if status == "missing":
        receipt["chunks"] = [c for c in receipt["chunks"] if c["id"] != "c002"]
    elif status == "duplicate_entry":
        receipt["chunks"].append(copy.deepcopy(receipt["chunks"][1]))
    else:
        receipt["chunks"][1] = {"id": "c002", "status": "duplicate_of", "of": "c001"}
    out = rr.complete(inputs(receipt=receipt), [answer()])
    assert out["counts"]["rejected_answers"] == 1
    assert out["counts"]["receipts_added"] == 0
    assert out["receipt"] == receipt
    assert out["after"]["chunks"]["reviewed"] == out["before"]["chunks"]["reviewed"]
    assert out["state"] == "answers_incomplete"


def test_all_diagnostic_splits_sum_to_legacy_and_unknown_markers_stay_visible():
    manifest, texts, receipt, _ = _setup()
    full = {**FULL, "funders": [{"name": "Alpha", "grant_id": "Beta", "description": "Gamma"}]}
    pairs = []
    for marker in (None, "rereceipt", {"untrusted": True}):
        origin = {} if marker is None else {"origin": marker}
        pairs += [{"slot": "name", "snippet": "Something else entirely", **origin},
                  {"slot": "funders[0]", "snippet": "Something else entirely", **origin},
                  {"slot": "title", "snippet": "AI", **origin}]
    receipt["chunks"][2] = {"id": "c003", "status": "extracted", "extracted": pairs,
                            "rereceipt_prior": []}
    old = rc.check(receipt, manifest, texts, full, manifest["bundle_md5"])
    new = rc.check(receipt, manifest, texts, full, manifest["bundle_md5"], instrument_version=4)
    origins = new["snippets"].pop("by_origin")
    assert new.pop("rereceipt")["unusable_prior_count"] == 1
    assert new.pop("instrument").startswith("v4 ")
    old.pop("instrument")
    assert new == old
    for metric in ("no_value_overlap", "entry_single_leaf", "unattesting"):
        assert [origins[name][metric] for name in ("phase1", "rereceipt", "unknown")] == [1, 1, 1]
    for metric in origins["phase1"]:
        assert sum(row[metric] for row in origins.values()) == old["snippets"][metric]


@pytest.mark.parametrize("marker", [None, [], 4, False, "phase1", "other"])
def test_explicit_malformed_marker_is_not_assumed_phase1(marker):
    manifest, texts, receipt, _ = _setup()
    receipt["chunks"][1]["extracted"][0]["origin"] = marker
    block = rc.check(receipt, manifest, texts, FULL, manifest["bundle_md5"], instrument_version=4)
    assert block["snippets"]["by_origin"]["unknown"]["total"] == 1
    assert block["snippets"]["by_origin"]["phase1"]["total"] == 0


def test_missing_rejected_extra_and_unsupported_have_distinct_conserved_units():
    pinned = inputs()
    unsupported = {"path": "description", "unsupported": True, "reason": "needs independent audit"}
    result = rr.complete(pinned, [answer(), unsupported, answer("name"), answer("name"),
                                  {"path": "outside", "unsupported": True, "reason": "extra"}, 3])
    c = result["counts"]
    assert (c["receipts_added"], c["unsupported"], c["rejected_answers"], c["rejected_paths"]) == (1, 1, 4, 1)
    assert c["requested"] == c["accepted"] + c["rejected_paths"] + c["unanswered"]
    assert c["answers_received"] == c["accepted"] + c["rejected_answers"]
    assert c["never_receipted_before"] - c["never_receipted_after"] == 1
    assert result["unsupported_audit_candidates"] == [
        {"path": "description", "reason": "needs independent audit"}]
    assert "description" in result["still_uncovered_paths"]
    assert yaml.safe_load(pinned.record) == FULL
    assert result["state"] == "answers_incomplete"


def test_all_unsupported_is_answers_complete_but_never_coverage_or_support():
    pinned = inputs()
    result = rr.complete(pinned, [{"path": p, "unsupported": True, "reason": "not established"}
                                   for p in pinned.paths()])
    assert result["state"] == "answers_complete"
    assert result["counts"]["never_receipted_after"] == result["counts"]["requested"]
    assert result["counts"]["receipts_added"] == 0
    assert result["receipt"] == yaml.safe_load(pinned.receipt)


def test_inventory_is_uncapped_and_input_identity_uses_original_bytes_including_dates():
    pinned = inputs({**FULL, "issued": date(2026, 1, 2),
                      "creators": [{"name": f"Person {n}"} for n in range(75)]})
    assert len(pinned.paths()) > 75
    assert "creators[74].name" in pinned.paths()
    inv = pinned.inventory()
    assert inv["record"]["issued"] == date(2026, 1, 2)
    assert inv["input_identity"]["sha256"]["record"] == hashlib.sha256(pinned.record).hexdigest()
    inv["record"]["title"] = "mutated"
    assert pinned.inventory()["record"]["title"] == FULL["title"]
    with pytest.raises(FrozenInstanceError):
        pinned.record = b"title: replaced\n"


@pytest.mark.parametrize("field,value", [
    ("receipt", b"bundle_md5: wrong\nchunks: []\n"),
    ("record", b"name: one\nname: two\n"),
    ("manifest", b"chunks: []\n"),
    ("schema", b"[]\n"), ("max_output_tokens", True), ("max_output_tokens", 0)])
def test_bad_identity_or_ambiguous_inputs_refused(field, value):
    with pytest.raises(ValueError):
        replace(inputs(), **{field: value})


def test_forged_chunk_manifest_is_refused_even_with_matching_bundle_hash():
    pinned = inputs()
    manifest = yaml.safe_load(pinned.manifest)
    manifest["chunks"][1]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="canonical chunk identities"):
        replace(pinned, manifest=raw(manifest))


def test_parser_does_not_silently_drop_malformed_answers():
    assert rr.parse_answers(b"rereceipt: [3, null]\n") == [3, None]
    for value in (b"rereceipt: []\nrecord: {}", b"rereceipt: {}", b"rereceipt: []\nrereceipt: []"):
        with pytest.raises(ValueError):
            rr.parse_answers(value)


def test_request_preserves_entire_latest_exchange_and_isolates_mutable_messages():
    pinned = inputs()
    req = runner.PhaseRequest("full_readdress", "system", [{"type": "text", "text": "prefix"}],
                              [{"role": "user", "content": "original"},
                               {"role": "assistant", "content": "full response"},
                               {"role": "user", "content": "readdress request"}])
    before = copy.deepcopy(req)
    draft = runner.build_rereceipt(req, "readdress response", pinned, render_version=24)
    assert draft.messages[:3] == req.messages
    assert draft.messages[3] == {"role": "assistant", "content": "readdress response"}
    inventory = yaml.safe_load(draft.messages[-1]["content"][0]["text"].removeprefix(rr.HEADER))
    assert inventory["requested_paths"] == pinned.paths()
    assert inventory["input_identity"]["max_output_tokens"] == 9000
    assert inventory["input_identity"]["sha256"] == pinned.identity()["sha256"]
    draft.messages[0]["content"] = "changed"
    draft.cached_blocks[0]["text"] = "changed"
    assert req == before


@pytest.mark.parametrize("phase", ["audit", "report", "report_regate", "reconcile_full"])
def test_receipt_correction_cannot_reopen_later_attempt(phase):
    with pytest.raises(ValueError, match="precede audit/report"):
        runner.build_rereceipt(runner.PhaseRequest(phase, "system"), "terminal result", inputs(), render_version=24)


def test_render24_cannot_spend_through_either_execution_entrypoint():
    spec = SimpleNamespace(render_version=24, _replay_only=False)
    for fn, kwargs in ((runner.execute, {}), (runner._execute, {"resume": False, "client": object()})):
        with pytest.raises(ValueError, match="offline only"):
            fn(spec, **kwargs)


def test_all_historical_assembly_digests_are_identical_and_new_bytes_are_covered(monkeypatch):
    baseline = json.loads(Path(__file__).with_name("rereceipt_legacy_assembly.json").read_text())
    assert {str(i): runner.assembly_digest(i)["sha256"] for i in range(1, 24)} == baseline
    before = runner.assembly_digest(24)["sha256"]
    assert before != baseline["23"]
    monkeypatch.setattr(rr, "INSTRUCTION", rr.INSTRUCTION + " Additional rule.")
    assert runner.assembly_digest(24)["sha256"] != before
    assert runner.assembly_digest(23)["sha256"] == baseline["23"]
    with pytest.raises(ValueError, match="requires renderer 24"):
        runner.phase_instruction("full_rereceipt", 23)


@pytest.mark.parametrize("version", [True, 2, 5, "4"])
def test_instrument_selection_is_explicit(version):
    with pytest.raises(ValueError, match="instrument version"):
        rc.receipt_instrument(version)


@pytest.mark.parametrize("field,value", [
    ("record", raw({**FULL, "title": "other"})),
    ("schema", b"name: another_schema\n"), ("max_output_tokens", 10000)])
def test_saved_request_identity_refuses_input_drift(field, value):
    pinned = inputs()
    changed = replace(pinned, **{field: value})
    with pytest.raises(ValueError, match="saved request identity differs"):
        rr.complete(changed, [], expected_identity=pinned.identity())


def test_cli_roundtrip_requires_saved_identity_and_never_writes_inputs(tmp_path, monkeypatch, capsys):
    pinned = inputs()
    argv = ["rereceipt"]
    for name in ("record", "receipt", "manifest", "bundle", "schema"):
        path = tmp_path / (name + ".yaml")
        path.write_bytes(getattr(pinned, name))
        argv += ["--" + name, str(path)]
    argv += ["--max-output-tokens", str(pinned.max_output_tokens)]
    monkeypatch.setattr("sys.argv", argv)
    rr.main()
    inventory = tmp_path / "inventory.yaml"
    inventory.write_text(capsys.readouterr().out)
    answers = tmp_path / "answers.yaml"
    answers.write_bytes(raw({"rereceipt": [answer()]}))
    monkeypatch.setattr("sys.argv", argv + ["--answers", str(answers)])
    with pytest.raises(SystemExit):
        rr.main()
    capsys.readouterr()
    monkeypatch.setattr("sys.argv", argv + ["--answers", str(answers), "--inventory", str(inventory)])
    rr.main()
    result = yaml.safe_load(capsys.readouterr().out)
    assert result["counts"]["receipts_added"] == 1
    for name in ("record", "receipt", "manifest", "bundle", "schema"):
        assert (tmp_path / (name + ".yaml")).read_bytes() == getattr(pinned, name)
    (tmp_path / "record.yaml").write_bytes(raw({**FULL, "title": "drifted"}))
    with pytest.raises(ValueError, match="saved request identity differs"):
        rr.main()


def test_render24_is_api_only(tmp_path):
    with pytest.raises(ValueError, match="API-only"):
        runner.RunSpec(project="external", arm="external", method="external", bundle=tmp_path / "bundle.txt",
                       label="offline", manifest=None, runtime="Claude Code", render_version=24)


def _corpus_receipts():
    base = Path(__file__).resolve().parents[1] / "data/d4d_concatenated/claudecode_api_core"
    return [pytest.param(p, id=f"{p.parent.name}/{p.name}")
            for p in sorted(base.glob("*-generic-v8_rep*/*_coverage_receipt.yaml"))]


@pytest.mark.corpus
@pytest.mark.parametrize("receipt", _corpus_receipts())
def test_real_corpus_v4_retains_all_legacy_counts_and_floors(receipt, monkeypatch):
    from click.testing import CliRunner
    from data_sheets_schema.cli.receipts import receipts as group
    project = receipt.name.split("_coverage_receipt")[0]
    provenance = receipt.parent / f"{project}_provenance.yaml"
    original_bytes = (receipt.read_bytes(), provenance.read_bytes())
    calls = []
    legacy_check = rc.check

    def compare(*args, **kwargs):
        old = legacy_check(*args, **kwargs)
        new = legacy_check(*args, **kwargs, instrument_version=4)
        assert receipt_floors(old) == receipt_floors(new)
        origins = new["snippets"].pop("by_origin")
        for metric in origins["phase1"]:
            assert sum(row[metric] for row in origins.values()) == old["snippets"][metric]
        new.pop("rereceipt")
        new["instrument"] = old["instrument"]
        assert new == old
        calls.append(old)
        return old

    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    monkeypatch.setattr(rc, "check", compare)
    result = CliRunner().invoke(group, ["check", "--method", "claudecode_api",
                                        "--label", receipt.parent.name, "--project", project])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1, result.output
    assert (receipt.read_bytes(), provenance.read_bytes()) == original_bytes
