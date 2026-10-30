#!/usr/bin/env python3
"""D70/#5212 review item 3: committed-record eligibility census, 2026-10-30.

Input: all Git-tracked YAML blobs in a selected ref (default d9b69d84d).
Output: every record's age, before/after canary and evaluation integrity
eligibility, and counts. Old policy is the identical optional-block predicate
in d9 canary._require_eligible_baseline and registered_eval_runner.prepare.
This does not assert other quality/registration requirements are satisfied.
No corpus writes, Git remotes, providers or network. V8 drift is fatal.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import yaml
from data_sheets_schema import canary, latch_journal as journal
from data_sheets_schema.evaluation.registered_eval_runner import require_eligible_generation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ref", default="d9b69d84d")
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()

def git(*command):
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(ROOT), *command])

names = git("ls-tree", "-r", "--name-only", "-z", args.ref).decode().split("\0")
rows = []
errors = []
for name in names:
    if not name.endswith((".yaml", ".yml")):
        continue
    raw = git("show", f"{args.ref}:{name}")
    if b"d4d_generation_provenance" not in raw:
        continue
    try:
        record = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        errors.append({"path": name, "error": str(exc)})
        continue
    if not isinstance(record, dict) or record.get("record_type") != "d4d_generation_provenance":
        continue
    model = record.get("model")
    before = (journal.eligibility_problem(model["runtime_integrity"])
              if isinstance(model, dict) and "runtime_integrity" in model else None)
    after = {}
    for consumer, call in (("canary", lambda: canary._require_eligible_baseline(record, name)),
                           ("evaluation", lambda: require_eligible_generation(record))):
        try:
            call()
            after[consumer] = True
        except (LookupError, ValueError):
            after[consumer] = False
    label = (record.get("run") or {}).get("label") or ""
    rows.append({"path": name, "label": label, "v8": "v8" in label,
                 "age": journal.record_age(record), "before_age": journal.record_age(record),
                 "before": {"canary": before is None, "evaluation": before is None},
                 "after": after, "reason": journal.record_eligibility_problem(record)})
counts = {"records": len(rows), "age": dict(Counter(row["age"] for row in rows)),
          "before": {key: sum(row["before"][key] for row in rows) for key in ("canary", "evaluation")},
          "after": {key: sum(row["after"][key] for row in rows) for key in ("canary", "evaluation")},
          "v8_records": sum(row["v8"] for row in rows),
          "v8_changes": sum(row["v8"] and row["before"] != row["after"] for row in rows)}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({"ref": git("rev-parse", args.ref).decode().strip(),
    "d41_commit": journal.D41_COMMIT, "d41_committed_at": journal.D41_COMMITTED_AT,
    "counts": counts, "parse_errors": errors, "records": rows}, indent=2) + "\n")
assert args.output.stat().st_size > 0
print(json.dumps(counts, indent=2))
assert not errors and not counts["v8_changes"]
