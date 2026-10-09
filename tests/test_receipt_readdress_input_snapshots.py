"""Duplicate CLI path snapshots must each survive publication preflight.

Actual CLI/prepare/writer, with a single deterministic file change
between the first and second real input reads. No provider or native authority.
"""
import hashlib
import json
import os

from click.testing import CliRunner
import pytest

from data_sheets_schema import receipt_readdress as rr
from data_sheets_schema.cli.receipts import receipts as receipt_cli


def _raw(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("changed_between_reads", [False, True])
def test_same_receipt_full_path_preserves_each_captured_snapshot(tmp_path, monkeypatch,
                                                               changed_between_reads):
    old_document = {
        "title": "current target",
        "chunks": [{"id": "c001", "status": "extracted", "extracted": [
            {"slot": "obsolete", "snippet": "unchanged quotation"}]}],
        "metadata": {"revision": 1, "flag": False},
    }
    new_document = json.loads(json.dumps(old_document))
    new_document["metadata"]["revision"] = 2
    old_raw = _raw(old_document)
    new_raw = _raw(new_document) if changed_between_reads else old_raw
    if changed_between_reads:
        assert old_raw != new_raw
    shared = tmp_path / "receipt-and-full.json"
    shared.write_bytes(old_raw)
    moves = tmp_path / "moves.json"
    map_raw = _raw({
        "version": 1,
        "receipt_sha256": _sha(old_raw),
        "full_sha256": _sha(new_raw),
        "moves": [{"chunk": "c001", "entry": 0, "slot": "obsolete", "new_slot": "title"}],
    })
    moves.write_bytes(map_raw)
    output = tmp_path / "repaired.yaml"
    original_read = rr.read_file
    shared_reads = []

    def controlled_read(path):
        raw = original_read(path)
        if path == shared:
            shared_reads.append(raw)
            if len(shared_reads) == 1 and changed_between_reads:
                # The first real read remains the receipt snapshot. The second
                # real read receives the changed full snapshot at the same Path.
                shared.write_bytes(new_raw)
        return raw

    monkeypatch.setattr(rr, "read_file", controlled_read)
    result = CliRunner().invoke(receipt_cli, [
        "readdress", "--receipt", str(shared), "--full", str(shared),
        "--map", str(moves), "--out", str(output),
    ])
    assert shared_reads[:2] == [old_raw, new_raw]
    assert len(shared_reads) >= 3  # Actual publication currentness check reached.
    assert shared.read_bytes() == new_raw
    assert moves.read_bytes() == map_raw
    if changed_between_reads:
        assert result.exit_code != 0
        assert "readdress input bytes changed before output publication" in result.output
        assert "output_sha256" not in result.output
        assert not os.path.lexists(output)
    else:
        assert result.exit_code == 0, result.output
        report = json.loads(result.output)
        assert report["receipt_sha256"] == report["full_sha256"] == _sha(old_raw)
        assert report["output_sha256"] == _sha(output.read_bytes())
        # Actual safe serialization need not keep JSON presentation.
        parsed = rr._read(output.read_bytes(), "test readdress output")
        expected = json.loads(old_raw)
        expected["chunks"][0]["extracted"][0]["slot"] = "title"
        assert rr._typed(parsed) == rr._typed(expected)
