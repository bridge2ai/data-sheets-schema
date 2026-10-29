"""N3 causal regressions; the outer deadline also bounds the unfixed implementation."""
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from data_sheets_schema import receipts as rc


def probe(pattern, text, mode):
    pair = {"slot": "record_count", "tool": {
        "name": "regex_count", "args": {"pattern": pattern}, "result": 0}}
    manifest = {"bundle_md5": "abc", "chunks": [{"id": "c001"}]}
    full = {"record_count": 0}
    if mode == "verify":
        return rc.verify_tool_receipt(pair, "c001", {"c001": text}, manifest, full)
    receipt = {"bundle_md5": "abc", "chunks": [
        {"id": "c001", "status": "extracted", "extracted": [pair]}]}
    return rc.check(receipt, manifest, {"c001": text}, full, "abc", original=full, instrument_version=5)


@pytest.mark.parametrize("mode", ["verify", "check"])
def test_n3_pathological_pattern_refuses_within_deadline(mode):
    # Reviewer's 9-character polynomial pattern: formerly ~33 seconds at n=320,
    # and check() evaluates it three times when a snapshot is supplied.
    runner = Path(__file__).resolve().parents[1] / "scripts/adhoc/validate_receipts_v5_merge_20261029.py"
    start = time.monotonic()
    result = subprocess.run([sys.executable, "-S", "-B", str(runner),
                             "--tree", str(Path(rc.__file__).resolve().parents[2]), "--script", __file__,
                             "--", mode], capture_output=True, text=True, timeout=4, check=True)
    assert time.monotonic() - start < 4
    value = json.loads(result.stdout)
    if mode == "verify":
        assert value[0] is False and "time budget" in value[1] and value[2] is None
    else:
        assert value["tool_receipts"]["verified"] == 0
        assert value["slots"]["with_receipt"] == 0
        assert value["slots"]["with_receipt_at_receipt"] == 0
        assert any(f["kind"] == "tool_receipt_mismatch" and "time budget" in f["reason"]
                   for f in value["findings"])


@pytest.mark.parametrize("pattern,text", [("a" * 201, "abc"), ("x", "a" * (48 * 1024 + 1)),
                                         ("a{99999999999999999999}", "abc"), ("[", "abc")],
                         ids=["long-pattern", "long-source", "overflow", "invalid"])
def test_n3_pattern_and_input_bounds_fail_closed(pattern, text):
    ok, reason, computed = probe(pattern, text, "verify")
    assert not ok and reason and computed is None


@pytest.mark.parametrize("pattern,expected", [("[Aa]lpha", 2), ("(Alpha)", 1), ("(?=a)", 3)])
def test_n3_bounded_regex_retains_nonoverlapping_count(pattern, expected):
    pair = {"slot": "record_count", "tool": {
        "name": "regex_count", "args": {"pattern": pattern}, "result": expected}}
    result = rc.verify_tool_receipt(pair, "c001", {"c001": "Alpha alpha"},
                                    {"chunks": [{"id": "c001"}]}, {"record_count": expected})
    assert result[0] and result[2] == expected


if __name__ == "__main__":
    print(json.dumps(probe(".*.*.*.*x", "a" * 320, sys.argv[1])))
