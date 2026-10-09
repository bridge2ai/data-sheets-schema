"""#4446: actual offline CLI/helper repair, never native or scientific acceptance."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import struct

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import api_runner, receipt_readdress as rr
from data_sheets_schema import receipt_origin as ro, receipt_origin_record as ror
from data_sheets_schema.cli.receipts import receipts as receipt_cli
from tests.test_receipt_origin import Run, receipt_text


def raw(value):
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def document():
    return {"bundle_md5": "b" * 32, "note": "unchanged source metadata", "chunks": [
        {"id": "c001", "status": "extracted", "extra": {"flag": False, "count": 0, "ratio": -0.0,
                                                           "date": date(2026, 10, 9)},
         "extracted": [{"slot": "obsolete", "snippet": "α quoted\nsecond line", "tag": [False, 0]},
                       {"slot": "obsolete", "snippet": "α quoted\nsecond line"},
                       {"slot": "title", "snippet": "Already addressed"}]},
        {"id": "c002", "status": "nothing_relevant", "reason": "original declared reason"}]}


def full():
    return {"id": "x", "title": "Already addressed", "names": ["first", "second"],
            "flag": False, "zero": 0, "absent": None, "empty": [],
            "a.b": "a literal key, not a path", "a": {"b": "real nested target"}}


def move(entry=0, target="names[0]"):
    return {"chunk": "c001", "entry": entry, "slot": "obsolete", "new_slot": target}


def mapping(receipt_raw, full_raw, moves=None):
    return {"version": 1, "receipt_sha256": sha(receipt_raw), "full_sha256": sha(full_raw),
            "moves": [move()] if moves is None else moves}


def files(tmp_path):
    receipt_raw, full_raw = raw(document()), raw(full())
    receipt, record, changes = (tmp_path / name for name in ("receipt.yaml", "full.yaml", "moves.yaml"))
    receipt.write_bytes(receipt_raw); record.write_bytes(full_raw)
    changes.write_bytes(raw(mapping(receipt_raw, full_raw)))
    return receipt, record, changes


def invoke(receipt, full_path, *extra):
    return CliRunner().invoke(receipt_cli, ["readdress", "--receipt", str(receipt),
                                          "--full", str(full_path), *map(str, extra)])


def test_help_inventory_is_readonly_and_candidates_are_structural(tmp_path):
    help_result = CliRunner().invoke(receipt_cli, ["readdress", "--help"])
    assert help_result.exit_code == 0 and "--map" in help_result.output and "--out" in help_result.output
    paths = files(tmp_path)
    before = {p: p.read_bytes() for p in paths}
    result = invoke(*paths[:2])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["receipt_sha256"] == sha(before[paths[0]]) and data["full_sha256"] == sha(before[paths[1]])
    assert [(r["chunk"], r["entry"], r["slot"], r["snippet"]) for r in data["unresolved"]] == [
        ("c001", 0, "obsolete", "α quoted\nsecond line"),
        ("c001", 1, "obsolete", "α quoted\nsecond line")]
    assert data["candidate_paths"] == ["id", "title", "names", "names[0]", "names[1]",
                                       "flag", "zero", "absent", "empty", "a", "a.b"]
    assert "not semantic matches" in data["limitations"][0]
    assert {p: p.read_bytes() for p in paths} == before
    assert set(tmp_path.iterdir()) == set(paths)


def test_cli_applies_only_named_ordinals_and_preserves_typed_content(tmp_path):
    receipt, record, changes = files(tmp_path)
    moves = [move(1, "names[1]"), move(0, "flag")]
    # Map key order is not a semantic constraint.
    changes.write_bytes(raw(mapping(receipt.read_bytes(), record.read_bytes(),
                                   [dict(reversed(list(row.items()))) for row in moves])))
    before = {p: p.read_bytes() for p in (receipt, record, changes)}
    out = tmp_path / "new.yaml"
    result = invoke(receipt, record, "--map", changes, "--out", out)
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["moved"] == moves and report["output_sha256"] == sha(out.read_bytes())
    expected = document()
    expected["chunks"][0]["extracted"][1]["slot"] = "names[1]"
    expected["chunks"][0]["extracted"][0]["slot"] = "flag"
    parsed = yaml.safe_load(out.read_bytes())
    assert parsed == expected
    extra = parsed["chunks"][0]["extra"]
    assert extra["flag"] is False and type(extra["count"]) is int
    assert struct.pack('>d', extra["ratio"]) == struct.pack('>d', -0.0)
    assert type(extra["date"]) is date
    assert parsed["chunks"][0]["extracted"][0]["tag"] == [False, 0]
    assert type(parsed["chunks"][0]["extracted"][0]["tag"][1]) is int
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("damage", [
    "extra_field", "snippet", "drop", "no_target", "target_unresolved", "target_malformed",
    "target_whitespace", "target_bool", "ordinal_bool", "ordinal_negative", "ordinal_large",
    "chunk_unknown", "old_slot_wrong", "already_resolves", "duplicate", "empty", "row_list",
    "bad_version", "old_receipt", "old_full", "late_invalid",
])
def test_entire_map_refuses_before_publication(tmp_path, damage):
    receipt, record, changes = files(tmp_path)
    m = mapping(receipt.read_bytes(), record.read_bytes())
    row = m["moves"][0]
    if damage == "extra_field": m["unexpected"] = True
    elif damage == "snippet": row["snippet"] = "new quote"
    elif damage == "drop": row["drop"] = True
    elif damage == "no_target": del row["new_slot"]
    elif damage == "target_unresolved": row["new_slot"] = "names[2]"
    elif damage == "target_malformed": row["new_slot"] = "names[-1]"
    elif damage == "target_whitespace": row["new_slot"] = " title "
    elif damage == "target_bool": row["new_slot"] = False
    elif damage == "ordinal_bool": row["entry"] = False
    elif damage == "ordinal_negative": row["entry"] = -1
    elif damage == "ordinal_large": row["entry"] = 100
    elif damage == "chunk_unknown": row["chunk"] = "c999"
    elif damage == "old_slot_wrong": row["slot"] = "different"
    elif damage == "already_resolves": row.update(entry=2, slot="title")
    elif damage == "duplicate": m["moves"].append(deepcopy(row))
    elif damage == "empty": m["moves"] = []
    elif damage == "row_list": m["moves"] = [[]]
    elif damage == "bad_version": m["version"] = True
    elif damage == "old_receipt": m["receipt_sha256"] = "0" * 64
    elif damage == "old_full": m["full_sha256"] = "0" * 64
    elif damage == "late_invalid": m["moves"].append(move(1, "not_a_target"))
    changes.write_bytes(raw(m))
    before = {p: p.read_bytes() for p in (receipt, record, changes)}
    out = tmp_path / "new.yaml"
    result = invoke(receipt, record, "--map", changes, "--out", out)
    assert result.exit_code != 0 and "receipt readdress refused" in result.output
    assert not os.path.lexists(out)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("damage", ["duplicate_keys", "duplicate_chunks", "cycle", "merge",
                                    "bad_entry", "bad_status", "wrong_full_shape"])
def test_ambiguous_or_unsupported_input_is_not_silently_normalised(tmp_path, damage):
    receipt, record, changes = files(tmp_path)
    value = document()
    if damage == "duplicate_keys": receipt.write_bytes(receipt.read_bytes() + b"chunks: []\n")
    elif damage == "duplicate_chunks":
        value["chunks"].append(deepcopy(value["chunks"][0])); receipt.write_bytes(raw(value))
    elif damage == "cycle": receipt.write_bytes(b"chunks: []\ncycle: &a [*a]\n")
    elif damage == "merge": receipt.write_bytes(b"chunks: []\nbase: &a {x: 1}\ncopy: {<<: *a}\n")
    elif damage == "bad_entry":
        value["chunks"][0]["extracted"][0]["snippet"] = 1; receipt.write_bytes(raw(value))
    elif damage == "bad_status":
        value["chunks"][0]["status"] = "guessed"; receipt.write_bytes(raw(value))
    elif damage == "wrong_full_shape": record.write_bytes(b"- title: x\n")
    before = {p: p.read_bytes() for p in (receipt, record, changes)}
    result = invoke(receipt, record)
    assert result.exit_code != 0 and "receipt readdress refused" in result.output
    assert {p: p.read_bytes() for p in before} == before


def test_alias_side_effect_outside_named_slot_is_refused():
    shared = {"slot": "obsolete", "snippet": "same text"}
    value = document(); value["chunks"][0]["extracted"] = [shared, shared]
    receipt_raw, full_raw = raw(value), raw(full())
    # A real YAML alias survives deepcopy; moving one dict would change both.
    assert b"*id" in receipt_raw
    with pytest.raises(ValueError, match="outside the named slot"):
        rr.prepare(receipt_raw, full_raw, raw(mapping(receipt_raw, full_raw)))


@pytest.mark.parametrize("mutant", ["false_to_zero", "snippet", "status", "unselected_slot"])
def test_non_slot_preservation_is_checked_after_actual_apply(monkeypatch, mutant):
    receipt_raw, full_raw = raw(document()), raw(full())
    original = api_runner.apply_readdress
    def changed(receipt, record, answers):
        result = original(receipt, record, answers)
        chunk = receipt["chunks"][0]
        if mutant == "false_to_zero": chunk["extra"]["flag"] = 0
        elif mutant == "snippet": chunk["extracted"][0]["snippet"] += " changed"
        elif mutant == "status": chunk["status"] = "nothing_relevant"
        elif mutant == "unselected_slot": chunk["extracted"][1]["slot"] = "title"
        return result
    monkeypatch.setattr(api_runner, "apply_readdress", changed)
    with pytest.raises(ValueError, match="outside the named slot"):
        rr.prepare(receipt_raw, full_raw, raw(mapping(receipt_raw, full_raw)))



def test_requested_target_survives_helper_answer_mutation(monkeypatch):
    receipt_raw, full_raw = raw(document()), raw(full())
    original = api_runner.apply_readdress
    def changed(receipt, record, answers):
        answers[0]["new_slot"] = "title"
        return original(receipt, record, answers)
    monkeypatch.setattr(api_runner, "apply_readdress", changed)
    with pytest.raises(ValueError, match="exactly the requested moves"):
        rr.prepare(receipt_raw, full_raw, raw(mapping(receipt_raw, full_raw)))


def test_giant_out_of_range_old_index_remains_visible_and_repairable(tmp_path):
    receipt, record, changes = files(tmp_path)
    value = document()
    old = "names[" + "9" * 5000 + "]"
    value["chunks"][0]["extracted"][0]["slot"] = old
    receipt.write_bytes(raw(value))
    listed = invoke(receipt, record)
    assert listed.exit_code == 0, listed.output
    assert json.loads(listed.output)["unresolved"][0]["slot"] == old
    row = move(); row["slot"] = old
    changes.write_bytes(raw(mapping(receipt.read_bytes(), record.read_bytes(), [row])))
    out = tmp_path / "new.yaml"
    applied = invoke(receipt, record, "--map", changes, "--out", out)
    assert applied.exit_code == 0, applied.output
    assert yaml.safe_load(out.read_bytes())["chunks"][0]["extracted"][0]["slot"] == "names[0]"
    # A giant destination is still invalid, and must not publish a prefix.
    row["new_slot"] = "names[" + "9" * 5000 + "]"
    changes.write_bytes(raw(mapping(receipt.read_bytes(), record.read_bytes(), [row])))
    invalid = tmp_path / "invalid.yaml"
    refused = invoke(receipt, record, "--map", changes, "--out", invalid)
    assert refused.exit_code != 0 and not os.path.lexists(invalid)


def test_long_leading_zero_index_keeps_existing_resolution(tmp_path):
    receipt, record, _ = files(tmp_path)
    value = document()
    old = "names[" + "0" * 5000 + "1]"
    value["chunks"][0]["extracted"][0]["slot"] = old
    receipt.write_bytes(raw(value))
    listed = invoke(receipt, record)
    assert listed.exit_code == 0, listed.output
    assert [(row["entry"], row["slot"]) for row in json.loads(listed.output)["unresolved"]] == [(1, "obsolete")]


def test_serialization_readback_and_complete_inventory_limits(monkeypatch):
    receipt_raw, full_raw = raw(document()), raw(full())
    map_raw = raw(mapping(receipt_raw, full_raw))
    original = yaml.safe_dump
    def changed(value, *args, **kwargs):
        value = deepcopy(value); value["chunks"][0]["extra"]["flag"] = 0
        return original(value, *args, **kwargs)
    with monkeypatch.context() as context:
        context.setattr(yaml, "safe_dump", changed)
        with pytest.raises(ValueError, match="serialized.*typed content"):
            rr.prepare(receipt_raw, full_raw, map_raw)
    with monkeypatch.context() as context:
        context.setattr(rr, "MAX_PATH_BYTES", 3)
        with pytest.raises(ValueError, match="complete target-path inventory"):
            rr.inventory(receipt_raw, full_raw)
    with monkeypatch.context() as context:
        context.setattr(rr, "MAX_REPORT_BYTES", 10)
        with pytest.raises(ValueError, match="complete readdress report"):
            rr.inventory(receipt_raw, full_raw)
        with pytest.raises(ValueError, match="complete readdress report"):
            rr.prepare(receipt_raw, full_raw, map_raw)


@pytest.mark.parametrize("kind", ["receipt", "full", "map", "existing", "symlink", "dangling", "hardlink"])
def test_existing_or_alias_outputs_never_replace_input_bytes(tmp_path, kind):
    receipt, record, changes = files(tmp_path)
    out = tmp_path / "out.yaml"
    if kind == "receipt": out = receipt
    elif kind == "full": out = record
    elif kind == "map": out = changes
    elif kind == "existing": out.write_bytes(b"preserve this")
    elif kind == "symlink": out.symlink_to(receipt)
    elif kind == "dangling": out.symlink_to(tmp_path / "absent.yaml")
    elif kind == "hardlink": os.link(receipt, out)
    before = {p: p.read_bytes() for p in (receipt, record, changes)}
    result = invoke(receipt, record, "--map", changes, "--out", out)
    assert result.exit_code != 0 and "new file" in result.output
    assert {p: p.read_bytes() for p in before} == before
    if kind == "existing": assert out.read_bytes() == b"preserve this"
    if kind in ("symlink", "dangling"): assert out.is_symlink()


def test_fresh_input_check_and_exclusive_open_close_the_normal_race(tmp_path, monkeypatch):
    receipt, record, changes = files(tmp_path)
    inputs = tuple((p, p.read_bytes()) for p in (receipt, record, changes))
    output, _ = rr.prepare(*(raw for _, raw in inputs))
    out = tmp_path / "new.yaml"
    changes.write_bytes(inputs[2][1] + b"\n")
    with pytest.raises(ValueError, match="input bytes changed"):
        rr.write_new(out, output, inputs=inputs)
    assert not out.exists()
    changes.write_bytes(inputs[2][1])
    original_open = Path.open
    def competing_open(path, mode='r', *args, **kwargs):
        if path == out and mode == 'xb':
            with original_open(path, 'wb') as stream: stream.write(b"other publisher")
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", competing_open)
    with pytest.raises(FileExistsError):
        rr.write_new(out, output, inputs=inputs)
    assert out.read_bytes() == b"other publisher"
    assert tuple((p, p.read_bytes()) for p, _ in inputs) == inputs


@pytest.mark.parametrize("failure", ["write_and_close", "short_and_close", "close"])
def test_write_failure_keeps_primary_error_and_cli_never_reports_success(tmp_path, monkeypatch, failure):
    receipt, record, changes = files(tmp_path)
    out = tmp_path / "new.yaml"
    primary, secondary = OSError("primary write failure"), OSError("secondary close failure")
    calls = []
    class BrokenStream:
        def write(self, data):
            calls.append('write')
            if failure == 'write_and_close': raise primary
            return len(data) - 1 if failure == 'short_and_close' else len(data)
        def close(self):
            calls.append('close'); raise secondary
    original_open = Path.open
    def fake_open(path, mode='r', *args, **kwargs):
        if path == out and mode == 'xb': return BrokenStream()
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fake_open)
    inputs = tuple((p, p.read_bytes()) for p in (receipt, record, changes))
    output, _ = rr.prepare(*(raw for _, raw in inputs))
    with pytest.raises(OSError) as error:
        rr.write_new(out, output, inputs=inputs)
    if failure == 'write_and_close': assert error.value is primary
    elif failure == 'short_and_close': assert str(error.value) == 'incomplete readdress output write'
    else: assert error.value is secondary
    assert calls == ['write', 'close']
    result = invoke(receipt, record, "--map", changes, "--out", out)
    assert result.exit_code != 0 and "output_sha256" not in result.output
    assert tuple((p, p.read_bytes()) for p, _ in inputs) == inputs


def test_path_only_output_never_inherits_origin_and_synthetic_history_counts_only_moves(tmp_path):
    run = Run(tmp_path)
    original = receipt_text(("c001", [("obsolete", "source phrase")]))
    full_text = "id: x\ntitle: source phrase\n"
    run.write(run.receipt, original); run.write(run.full, full_text)
    run.receipt.write_text(original); run.full.write_text(full_text)
    transcript = run.transcript()
    origin = ror.for_record(None, run.receipt, run.full, transcripts=[transcript])
    assert origin['status'] == 'checked' and origin['origin']['contemporaneous'] == 1
    provenance = tmp_path / 'provenance.yaml'
    provenance.write_bytes(raw({'receipts': {'origin': origin}}))
    changes = tmp_path / 'moves.yaml'
    changes.write_bytes(raw(mapping(run.receipt.read_bytes(), run.full.read_bytes(), [move(0, 'title')])))
    originals = {p: p.read_bytes() for p in (run.receipt, run.full, transcript, provenance, changes)}
    out = tmp_path / 'new-receipt.yaml'
    result = invoke(run.receipt, run.full, '--map', changes, '--out', out)
    assert result.exit_code == 0, result.output
    assert {p: p.read_bytes() for p in originals} == originals
    unknown = ror.for_record(origin, out, run.full)
    assert unknown['status'] == 'unknown' and unknown['prior'] == origin
    assert ror.split({'origin': origin, 'artifacts': {'receipt': {'sha256': sha(out.read_bytes())}}}) is None
    # A separate explicit synthetic event tests the actual origin instrument;
    # the CLI neither creates that event nor rewrites the real source transcript.
    run.write(run.receipt, out.read_text())
    synthetic = run.transcript('synthetic-after.jsonl')
    measured = ro.origin([synthetic], out, run.full, receipt_at_run=run.receipt, full_at_run=run.full)
    assert measured['status'] == 'checked', measured['reasons']
    assert measured['deltas']['draft_to_final'] == {'removed': 0, 'added': 0}
    assert measured['readdressed'] == 1 and measured['post_draft'] == 0
    assert {p: p.read_bytes() for p in originals} == originals


def test_cli_requires_map_and_new_output_together(tmp_path):
    receipt, record, changes = files(tmp_path)
    for extra in (('--map', changes), ('--out', tmp_path / 'new.yaml')):
        result = invoke(receipt, record, *extra)
        assert result.exit_code == 2 and '--map and --out' in result.output
    assert not (tmp_path / 'new.yaml').exists()
