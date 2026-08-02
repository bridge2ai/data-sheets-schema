#!/usr/bin/env python
"""Regenerate every number in `notes/generic_v2_results.md`.

Why this exists: the pre-registered plan quoted a mean-fitness baseline that
cannot be reproduced from anything on disk (#216). Six candidate denominators
were tried and none matched. The lesson is not "recompute it more carefully" —
it is that a statistic quoted in a registered document needs to be *emitted by
committed code*, so a reader can regenerate it instead of trusting it.

Reads only the judgement cache and the records. Makes no API calls, so it is
free to run and cannot change what it measures.

    python scripts/generic_v2_report.py            # the table
    python scripts/generic_v2_report.py --check    # verify the note is current
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics as st
import sys

import yaml

RECORDS = "data/d4d_concatenated/claudecode_agent/{label}_rep*/*_d4d.yaml"
CACHE = "data/evaluation_llm/judgement_cache/*_fitness.jsonl"
V1 = "2026-07-28_claude-opus-5-generic"
V2 = "2026-07-31_claude-opus-5-generic-v2"
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
CLASSES = ("form", "substance", "target")

# The pre-registered baseline, so a drift in the *inputs* is caught here rather
# than discovered later. Failure counts only: the plan's mean-fitness row is
# unreproducible and deliberately not asserted (#216).
REGISTERED = {"form": 50, "substance": 40, "target": 41}
REGISTERED_BY_PROJECT = {"AI_READI": 37, "CHORUS": 36, "CM4AI": 39, "VOICE": 19}


def load_cache() -> dict[tuple[str, str], tuple[str, float]]:
    """Keyed exactly as `LLMSlotFitnessScorer` keys it: (slot, json-of-value)."""
    cache: dict[tuple[str, str], tuple[str, float]] = {}
    contexts = set()
    for path in glob.glob(CACHE):
        for line in open(path, encoding="utf-8"):
            d = json.loads(line)
            cache[(d["slot"], d["value"])] = (d["failure"], d["fitness"])
            contexts.add((d["axis"], d["model"], d["rubric"], d["corpus"],
                          d["schema"]))
    if len(contexts) > 1:
        print(f"WARNING: {len(contexts)} distinct judgement contexts in the "
              f"cache; v1 and v2 are not comparable across a context change.",
              file=sys.stderr)
        for c in sorted(contexts):
            print(f"    {c}", file=sys.stderr)
    return cache


def tally(label: str, cache) -> tuple[dict, dict, dict, int]:
    """Failure counts, fitness values and slot counts per project."""
    fails = collections.defaultdict(collections.Counter)
    fitness = collections.defaultdict(list)
    slots = collections.defaultdict(list)
    unscored = 0
    for path in sorted(glob.glob(RECORDS.format(label=label))):
        project = os.path.basename(path).replace("_d4d.yaml", "")
        record = yaml.safe_load(open(path, encoding="utf-8"))
        if not isinstance(record, dict):
            continue
        slots[project].append(len(record))
        for slot, value in record.items():
            key = (slot, json.dumps(value, sort_keys=True, default=str))
            if key not in cache:
                unscored += 1
                continue
            failure, score = cache[key]
            fitness[project].append(score)
            if failure and failure != "none":
                fails[project][failure] += 1
    return fails, fitness, slots, unscored


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if v1 no longer matches the "
                         "pre-registered failure counts")
    args = ap.parse_args()

    cache = load_cache()
    f1, fit1, slots1, miss1 = tally(V1, cache)
    f2, fit2, slots2, miss2 = tally(V2, cache)

    print(f"v1 = {V1}\nv2 = {V2}")
    print(f"unscored slot values: v1 {miss1}, v2 {miss2}\n")

    print("FAILURE COUNTS BY CLASS (v1 -> v2)")
    head = "".join(f"{p:>16s}" for p in PROJECTS)
    print(f"  {'class':11s}{head}{'total':>14s}")
    totals = {}
    for cls in CLASSES:
        cells, t1, t2 = [], 0, 0
        for p in PROJECTS:
            a, b = f1[p][cls], f2[p][cls]
            t1 += a
            t2 += b
            cells.append(f"{a:5d} ->{b:4d}   ")
        totals[cls] = (t1, t2)
        print(f"  {cls:11s}" + "".join(cells) + f"{t1:5d} ->{t2:4d}")
    g1 = sum(t[0] for t in totals.values())
    g2 = sum(t[1] for t in totals.values())
    cells = [f"{sum(f1[p][c] for c in CLASSES):5d} ->"
             f"{sum(f2[p][c] for c in CLASSES):4d}   " for p in PROJECTS]
    print(f"  {'TOTAL':11s}" + "".join(cells) + f"{g1:5d} ->{g2:4d}")

    print("\nSLOT COUNTS (mean per record)")
    for p in PROJECTS:
        a = st.mean(slots1[p]) if slots1[p] else 0
        b = st.mean(slots2[p]) if slots2[p] else 0
        print(f"  {p:10s} {a:6.1f} -> {b:6.1f}   ({b - a:+.1f})")

    print("\nMEAN FITNESS  (v1 and v2 computed identically; the plan's row is "
          "unreproducible, see #216)")
    for p in PROJECTS:
        a = st.mean(fit1[p]) if fit1[p] else 0
        b = st.mean(fit2[p]) if fit2[p] else 0
        print(f"  {p:10s} {a:.3f} -> {b:.3f}   ({b - a:+.3f})")

    drift = [f"{c}: {totals[c][0]} != {REGISTERED[c]}"
             for c in CLASSES if totals[c][0] != REGISTERED[c]]
    drift += [f"{p}: {sum(f1[p][c] for c in CLASSES)} != {REGISTERED_BY_PROJECT[p]}"
              for p in PROJECTS
              if sum(f1[p][c] for c in CLASSES) != REGISTERED_BY_PROJECT[p]]
    print("\nv1 against the pre-registered table: "
          + ("MATCHES" if not drift else "DRIFTED — " + "; ".join(drift)))
    if args.check and drift:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
