# Purpose: repeat claude's receipt-corpus probe for N1/N3/N4, 2026-10-29.
# Inputs: selected tree, output path, optional canary record key; output: exact JSON blocks.
# Adapted from /private/tmp/claude-501/receipts-v5-IDc5/scripts/corpus_inert.py.
"""Corpus inertness probe: recompute every receipts block the way backfill does.

Run once per tree with v5 off (no env, no explicit version). For each
provenance record beside a coverage receipt it records:
  - the backfill receipts block (block_for path, default version selection);
  - the same check() inputs re-run at explicit v3 and v4 (D37 counters);
  - claim sidecars (with and without the record) and the uncovered-leaf list.
A spy captures check()'s arguments so v3/v4 run on exactly the bytes block_for chose.
"""
import json
import os
import sys
import traceback
from pathlib import Path

assert os.environ.get("RECEIPTS_V5_INSTRUMENT") is None or os.environ.get("ALLOW_ENV") == "1"
from data_sheets_schema import receipts as rc  # noqa: E402
from data_sheets_schema import backfill_checks as bf  # noqa: E402

TREE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
captured: list = []
_orig_check = rc.check


def spy(*args, **kwargs):
    block = _orig_check(*args, **kwargs)
    captured.append((args, kwargs, block))
    return block


rc.check = spy
provs = sorted(p for p in (TREE / "data").rglob("*_provenance.yaml")
               if any(p.parent.glob("*_coverage_receipt.yaml")))
if len(sys.argv) > 3:
    provs = [p for p in provs if str(p.relative_to(TREE)) == sys.argv[3]]
rows = {}
for prov in provs:
    key = str(prov.relative_to(TREE))
    captured.clear()
    row: dict = {}
    try:
        blocks = bf.compute(prov, only={"receipts"})
        rec = blocks.get("receipts") or {}
        rec.pop("origin", None)          # transcript-derived, not this instrument
        row["block"] = rec
        if captured:
            args, kwargs, _block = captured[-1]
            receipt, manifest, texts, full, md5 = args[:5]
            original = args[5] if len(args) > 5 else kwargs.get("original")
            ib = kwargs.get("identifier_bases")
            row["v3"] = _orig_check(receipt, manifest, texts, full, md5, original, identifier_bases=ib)
            row["v4"] = _orig_check(receipt, manifest, texts, full, md5, original, identifier_bases=ib,
                                    instrument_version=4)
            row["claims"] = rc.claim_receipts(receipt, full, original, identifier_bases=ib)
            row["claims_bare"] = rc.claim_receipts(receipt)
            row["uncovered"] = rc.uncovered_receiptable_leaves(receipt, manifest, texts, full, md5,
                                                               original=original, identifier_bases=ib)
            row["has_snapshot"] = original is not None
    except Exception as exc:  # noqa: BLE001 - recorded as data
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["trace"] = traceback.format_exc()[-600:]
    rows[key] = row
OUT.write_text(json.dumps(rows, sort_keys=True, indent=1, default=str))
checked = sum(1 for r in rows.values() if (r.get("block") or {}).get("checked"))
errors = sum(1 for r in rows.values() if "error" in r)
snap = sum(1 for r in rows.values() if r.get("has_snapshot"))
print(f"records {len(rows)} · block checked {checked} · with snapshot {snap} · errors {errors}")
