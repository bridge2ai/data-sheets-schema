#!/usr/bin/env python3
# Purpose: record the reasoning effort the launcher asserted for the 16 agentic
#   runs of 2026-11-22 (series 2026-11-22b and the canary 2026-11-22). Their
#   provenance records say "no effort is recorded ... the provider default
#   applied. That is not a value this run chose", because the recorder call
#   omitted --reasoning-effort. The driver launched every session with
#   `--effort high` and each committed launch file says so. Review finding F1
#   on PR #6309.
# Why a script and not `d4d provenance record --reasoning-effort high`: a
#   re-record rewrites the whole record (it moved repo.commit and the
#   timestamp and dropped the canonical block on the three records commit
#   686e5b66a re-recorded). `d4d provenance backfill-effort` reads the model
#   route, and the route `claude-opus-5-5` names no effort.
# What it changes, per record, in the record's text (no YAML re-dump):
#   - adds model.reasoning_effort and model.reasoning_effort_basis, placed
#     before model.shared_config, where the recorder puts them;
#   - replaces the one `unverified` entry for model.reasoning_effort (value
#     null) with an entry of value `high`. No entry is added.
#   It refuses a record whose launch file does not state `effort: high (CLI
#   flag`, one that already carries an effort, and any edit whose parsed
#   result differs from the parsed original in anything but those keys.
# Inputs: data/d4d_concatenated/claudecode_agent_core/2026-11-22*_rep*/*_provenance.yaml
#   and notes/final_agentic_2026-11-22/launch/{PROJECT}_{LABEL}.launch.txt
# Outputs: the same provenance files, edited in place under --execute.
# Usage (from the repository root):
#   python scripts/adhoc/assert_launcher_effort_2026-11-22.py            # report
#   python scripts/adhoc/assert_launcher_effort_2026-11-22.py --only P --execute   # one record
#   python scripts/adhoc/assert_launcher_effort_2026-11-22.py --execute  # all
# Date: 2026-11-22. Serves PR #6309.
from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path

import yaml

CORE = Path("data/d4d_concatenated/claudecode_agent_core")
LAUNCH = Path("notes/final_agentic_2026-11-22/launch")
SCRIPT = "scripts/adhoc/assert_launcher_effort_2026-11-22.py"
EFFORT = "high"
BASIS = ("asserted by the launcher (the Claude Code command line was given "
         "--effort high, as the committed launch file states), not observed; "
         "added after the run because the recorder call omitted "
         "--reasoning-effort")
FIELD_LINE = "- field: model.reasoning_effort\n"
LAUNCH_EVIDENCE = re.compile(r"effort: high \(CLI flag")


def reason(launch: Path) -> str:
    return ("the launcher passed --effort high to the Claude Code command line "
            f"and the committed launch file {launch.as_posix()} says so; neither "
            "the record header nor the model route carries it, so nothing here "
            "observed it. The recorder call omitted --reasoning-effort and "
            "wrote that the provider default applied; this entry replaces that "
            f"statement ({SCRIPT}, review of PR #6309).")


def records() -> list[Path]:
    return sorted(CORE.glob("2026-11-22*_claude-opus-5-5-claudecode-generic-v9_rep*/*_provenance.yaml"))


def launch_file(record: Path) -> Path:
    project = record.name[: -len("_provenance.yaml")]
    return LAUNCH / f"{project}_{record.parent.name}.launch.txt"


def edit(record: Path) -> tuple[str, str] | str:
    """Return (old_text, new_text), or a string saying why nothing is done."""
    launch = launch_file(record)
    if not launch.exists():
        return f"REFUSED no launch file {launch}"
    if not LAUNCH_EVIDENCE.search(launch.read_text(encoding="utf-8")):
        return f"REFUSED launch file does not state effort high: {launch}"

    old = record.read_text(encoding="utf-8")
    before = yaml.safe_load(old)
    model = before.get("model") or {}
    if model.get("reasoning_effort"):
        return f"SKIPPED already carries effort {model['reasoning_effort']!r}"
    entries = [i for i, u in enumerate(before.get("unverified") or [])
               if u.get("field") == "model.reasoning_effort"]
    if len(entries) != 1:
        return f"REFUSED {len(entries)} unverified entries for model.reasoning_effort"
    index = entries[0]
    stale = before["unverified"][index]
    if stale.get("value") is not None or not str(stale.get("reason", "")).startswith("no effort is recorded"):
        return "REFUSED the unverified entry is not the null 'no effort is recorded' entry"

    lines = old.splitlines(keepends=True)

    # 1. model block: insert the two keys before `  shared_config:`.
    starts = [i for i, ln in enumerate(lines) if ln == "model:\n"]
    if len(starts) != 1:
        return f"REFUSED {len(starts)} top-level model blocks"
    end = next(i for i in range(starts[0] + 1, len(lines)) if not lines[i].startswith(" "))
    shared = [i for i in range(starts[0] + 1, end) if lines[i] == "  shared_config:\n"]
    if len(shared) != 1:
        return f"REFUSED {len(shared)} model.shared_config lines"
    insert = yaml.safe_dump({"reasoning_effort": EFFORT, "reasoning_effort_basis": BASIS},
                            sort_keys=False, width=78)
    insert_lines = ["  " + ln for ln in insert.splitlines(keepends=True)]
    lines[shared[0]:shared[0]] = insert_lines

    # 2. the unverified entry: replace its span, add nothing.
    fields = [i for i, ln in enumerate(lines) if ln == FIELD_LINE]
    if len(fields) != 1:
        return f"REFUSED {len(fields)} text lines '{FIELD_LINE.strip()}'"
    span_end = next((i for i in range(fields[0] + 1, len(lines)) if not lines[i].startswith("  ")),
                    len(lines))
    replacement = yaml.safe_dump(
        [{"field": "model.reasoning_effort", "value": EFFORT, "reason": reason(launch)}],
        sort_keys=False, width=80)
    lines[fields[0]:span_end] = replacement.splitlines(keepends=True)

    new = "".join(lines)
    after = yaml.safe_load(new)
    expected = copy.deepcopy(before)
    expected["model"]["reasoning_effort"] = EFFORT
    expected["model"]["reasoning_effort_basis"] = BASIS
    expected["unverified"][index] = {"field": "model.reasoning_effort", "value": EFFORT,
                                     "reason": reason(launch)}
    if after != expected:
        return "REFUSED the edited text does not parse to the original plus the three changes"
    if list(after) != list(before) or len(after["unverified"]) != len(before["unverified"]):
        return "REFUSED top-level key order or the number of unverified entries moved"
    keys = list(after["model"])
    if keys.index("reasoning_effort_basis") + 1 != keys.index("shared_config"):
        return "REFUSED the new keys are not directly before model.shared_config"
    return old, new


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="write the records")
    parser.add_argument("--only", type=Path, help="restrict to one provenance record")
    args = parser.parse_args()
    if not CORE.is_dir():
        print("run from the repository root", file=sys.stderr)
        return 2
    targets = records()
    if args.only:
        targets = [p for p in targets if p == args.only]
    if not targets:
        print("no record selected", file=sys.stderr)
        return 2
    refused = 0
    for record in targets:
        result = edit(record)
        if isinstance(result, str):
            refused += result.startswith("REFUSED")
            print(f"{result}: {record}")
            continue
        old, new = result
        if args.execute:
            record.write_text(new, encoding="utf-8")
            if record.read_text(encoding="utf-8") != new:
                print(f"REFUSED write did not persist: {record}")
                refused += 1
                continue
        added = len(new.splitlines()) - len(old.splitlines())
        print(f"{'WROTE' if args.execute else 'WOULD WRITE'} ({added:+d} lines): {record}")
    return 1 if refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
