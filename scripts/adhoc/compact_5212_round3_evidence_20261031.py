#!/usr/bin/env python3
"""#5212 Claude D, 2026-10-31: compact prior validation evidence for review.

Inputs: D73 evidence under notes/reviews. Outputs: path-normalized JSON and a
gzip shard plan; original bytes and hashes retained in scratch-5212fix.
Only this packet's generated evidence is rewritten, never captured run data.
"""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "notes/reviews/d73_5212_evidence_20261031"
SAVED = ROOT.parent / "scratch-5212fix/r3-original-evidence"
SAVED.mkdir(exist_ok=True)
records = []
for name in ("corpus-base.json", "corpus-packet.json", "shard-plan.json", "validation.json"):
    path, saved = EVIDENCE / name, SAVED / name
    raw = saved.read_bytes() if saved.exists() else path.read_bytes()
    if not saved.exists():
        saved.write_bytes(raw)
    normalized = raw.decode().replace(str(ROOT.parent / "scratch-5212fix") + "/", "scratch-5212fix/")
    normalized = normalized.replace(str(ROOT) + "/", "")
    normalized = normalized.replace(str(ROOT.parent) + "/", "d4d-executions/")
    normalized = normalized.replace(str(ROOT.parent.parent / "data-sheets-schema") + "/", "repo/")
    normalized = normalized.replace(str(ROOT), ".")
    normalized = normalized.replace("/Users/marcin/Docume[151 chars]", "scratch-5212fix/[abbreviated traceback]")
    # Parse again so a path substitution cannot silently damage the report.
    json.loads(normalized)
    result = normalized.encode()
    target = path
    if path.name == "shard-plan.json":
        target = path.with_suffix(".json.gz")
        target.write_bytes(gzip.compress(result, mtime=0))
        path.unlink(missing_ok=True)
    else:
        path.write_bytes(result)
    records.append({"file": path.name, "original_sha256": hashlib.sha256(raw).hexdigest(),
                    "original_bytes": len(raw), "retained": target.name,
                    "retained_bytes": target.stat().st_size})
(EVIDENCE / "compaction.json").write_text(json.dumps(records, indent=2) + "\n")
print(json.dumps(records, indent=2))
