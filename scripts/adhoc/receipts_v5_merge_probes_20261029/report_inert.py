# Purpose: repeat claude's v7/v8 report-corpus probe for N1/N3/N4, 2026-10-29.
# Inputs: selected tree, output path, optional canary record key; output: exact JSON blocks.
# Adapted from /private/tmp/claude-501/receipts-v5-IDc5/scripts/report_inert.py.
import json, sys, traceback
from pathlib import Path
from data_sheets_schema import backfill_checks as bf
TREE = Path(sys.argv[1]); OUT = Path(sys.argv[2])
rows = {}
provs = sorted(p for p in (TREE / "data").rglob("*_provenance.yaml")
               if any(p.parent.glob("*_reconciliation.md")))
if len(sys.argv) > 3:
    provs = [p for p in provs if str(p.relative_to(TREE)) == sys.argv[3]]
for prov in provs:
    if not any(prov.parent.glob("*_reconciliation.md")):
        continue
    key = str(prov.relative_to(TREE)); row = {}
    for v in (8, 7):
        try:
            row[f"v{v}"] = bf.compute(prov, only={"report_claims"}, report_claims_version=v).get("report_claims")
        except Exception as e:
            row[f"v{v}"] = {"error": f"{type(e).__name__}: {e}"}
    rows[key] = row
    if len(rows) % 10 == 0:
        OUT.with_suffix(".progress").write_text(f"{len(rows)}/{len(provs)} records completed\n")
OUT.write_text(json.dumps(rows, sort_keys=True, indent=1, default=str).replace(str(TREE), "<TREE>"))
OUT.with_suffix(".progress").write_text(f"{len(rows)}/{len(provs)} records completed\n")
print("records", len(rows), "checked v8", sum(1 for r in rows.values() if (r["v8"] or {}).get("checked")))
