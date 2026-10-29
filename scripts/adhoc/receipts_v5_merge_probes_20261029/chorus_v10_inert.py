# Purpose: repeat claude's CHORUS v10 probe for N1/N3/N4, 2026-10-29.
# Inputs: archived canaries, selected source tree; output: request and check identities.
# Adapted from /private/tmp/claude-501/receipts-v5-IDc5/scripts/chorus_v10_inert.py.
"""Inertness probe on the CHORUS v10 canaries (10-20a, 10-22a), v5 off.

Run once per tree (PYTHONPATH selects the tree). Writes one JSON with:
  - receipt-completion request payload rebuilt from the saved inputs, its
    canonical sha256 and whether it equals the saved request bytes;
  - receipt-completion result recomputed from the saved response, and whether
    it equals the saved result;
  - receipts.check v3 and v4 (D37, phase-1 snapshot) blocks for the final
    coverage receipt; claim sidecar; uncovered leaves for the phase-1 receipt.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml

assert os.environ.get("RECEIPTS_V5_INSTRUMENT") is None, "run with v5 off"
from data_sheets_schema import receipts as rc, receipt_completion as rcomp  # noqa: E402
from data_sheets_schema.chunking import chunk_texts  # noqa: E402

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
TREE = Path(rc.__file__).resolve().parents[2]
BUNDLE = TREE / "data/preprocessed/concatenated/CHORUS_preprocessed.txt"
MANIFEST = TREE / "data/preprocessed/chunks/CHORUS_chunks.yaml"


def canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


out = {"receipts_file": str(Path(rc.__file__).resolve()),
       "RECEIPTS_INSTRUMENT_sha": sha(rc.RECEIPTS_INSTRUMENT.encode()),
       "RERECEIPTS_INSTRUMENT_sha": sha(rc.RERECEIPTS_INSTRUMENT.encode()),
       "runs": {}}
manifest = yaml.safe_load(MANIFEST.read_text())
texts = dict(zip([c["id"] for c in manifest["chunks"]], chunk_texts(BUNDLE.read_text(), manifest["chunks"])))
md5 = hashlib.md5(BUNDLE.read_bytes()).hexdigest()
for label in ("2026-10-20a", "2026-10-22a"):
    core = ROOT / label / "core"
    inter = core / "intermediate"
    row = {}
    inputs = json.loads((inter / "CHORUS_receipt_completion_inputs.json").read_text())
    req, inventory = rcomp.build_request(inputs)
    payload = rcomp.request_payload(req, inputs["request_settings"], {"max_output_tokens": inputs["max_output_tokens"]})
    saved_req = (inter / "CHORUS_receipt_completion_request.json").read_bytes()
    row["request_sha256"] = sha(canon(payload))
    row["request_equals_saved_bytes"] = canon(payload) == saved_req
    row["requested_paths"] = inventory["requested_paths"]
    resp = json.loads((inter / "CHORUS_receipt_completion_response.json").read_text())
    result = rcomp._result(inputs, resp["text"].encode(), truncated=resp["stop_reason"] == "max_tokens",
                           no_work=resp["stop_reason"] == "no_work")
    row["result_sha256"] = sha(canon(result))
    saved_results = sorted(inter.glob("CHORUS_receipt_completion_result*.json"))
    row["result_equals_saved"] = {p.name: (json.loads(p.read_text()) == result
                                           or rcomp._as_saved_before(result, json.loads(p.read_text()))
                                           == json.loads(p.read_text()))
                                  for p in saved_results}
    receipt = rc.load_receipt(core / "CHORUS_coverage_receipt.yaml")
    phase1_receipt = rc.load_receipt(inter / "CHORUS_coverage_receipt.yaml")
    full = yaml.safe_load((ROOT / label / "full" / "CHORUS_d4d.yaml").read_text()) or {}
    original = yaml.safe_load((inter / "CHORUS_full.yaml").read_text()) or {}
    row["v3"] = rc.check(receipt, manifest, texts, full, md5, original)
    row["v4"] = rc.check(receipt, manifest, texts, full, md5, original, instrument_version=4)
    row["v4_phase1_on_snapshot"] = rc.check(phase1_receipt, manifest, texts, original, md5, original,
                                            instrument_version=4)
    row["claims"] = rc.claim_receipts(receipt, full, original)
    row["claims_bare"] = rc.claim_receipts(receipt)
    row["uncovered_phase1"] = rc.uncovered_receiptable_leaves(phase1_receipt, manifest, texts, original, md5,
                                                              original=original)
    row["uncovered_final"] = rc.uncovered_receiptable_leaves(receipt, manifest, texts, full, md5,
                                                             original=original)
    out["runs"][label] = row
OUT.write_text(json.dumps(out, sort_keys=True, indent=1, default=str))
for label, row in out["runs"].items():
    print(label, "request==saved:", row["request_equals_saved_bytes"], row["request_sha256"][:16],
          "| result==saved:", row["result_equals_saved"],
          "| v4 at_receipt:", row["v4"]["slots"].get("with_receipt_at_receipt"), "/",
          row["v4"]["slots"].get("receiptable_at_receipt"),
          "| v3 with/receiptable:", row["v3"]["slots"]["with_receipt"], "/", row["v3"]["slots"]["receiptable"])
