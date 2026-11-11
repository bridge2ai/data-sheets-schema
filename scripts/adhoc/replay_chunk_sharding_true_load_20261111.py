#!/usr/bin/env python3
"""Replay AGY1's sub-file chunk sharding against per-test durations hosted CI recorded.

Purpose:
  AGY1's handoff predicts shard loads from whole-file weights, assuming every
  test in a file costs the same. AGY2's pre-review says that assumption is
  false for the heavy files and that chunking would unbalance the shards.
  This script decides between them with the function AGY1 actually wrote: it
  assigns the collected roster to shards twice (file-level `balanced_files`,
  item-level `balanced_nodeids`) and sums, per shard, the per-test durations
  a hosted run recorded in its JUnit XML.

  It also asks whether a shard's deviation from its prediction in that run was
  shard-wide (every file slower or faster by a similar factor: the runner) or
  confined to a few files (the workload).

Inputs (all read-only):
  --plugin    utils/pytest_shard.py to load (AGY1's worktree copy)
  --weights   utils/ci_test_durations.json (committed; built from run 42916359440)
  --roster    a `pytest --collect-only -q` log (node ids in collection order)
  --junit-dir a directory holding tests-py3.12-shardN/pytest.xml for one run

Output: JSON on stdout (and to --output when given).

Limits, stated so the numbers are not over-read:
  - A test's JUnit time includes its fixture setup on the worker that ran it.
    Replaying a different partition keeps those times fixed, so the extra
    module/class fixture setup that splitting a file adds is NOT counted.
    The replay therefore flatters chunking.
  - Shard load here is summed case-seconds, not wall time. Wall time is about
    load divided by the workers kept busy, plus collection and job setup.
  - Weights from run 42916359440 replayed on that same run are in-sample for
    the file-level partition (it balances by construction). The out-of-sample
    run is the comparison that matters.

Serves: lead review of branch agy/ci-chunk-sharding-20261111 (no PR yet).
Date: 2026-11-11.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


def load_plugin(path: Path):
    spec = importlib.util.spec_from_file_location("pytest_shard_under_review", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_roster(path: Path) -> list[str]:
    nodeids = []
    for line in path.read_text(errors="replace").splitlines():
        if "::" in line and line.startswith("tests/") and not line.startswith("ERROR"):
            nodeids.append(line.strip())
    return nodeids


def junit_cases(junit_dir: Path, files: set[str]):
    """Yield (shard, nodeid, seconds) for every testcase in the run's shard XMLs."""
    modules = {f[:-3].replace("/", "."): f for f in files}
    unresolved = Counter()
    for xml in sorted(junit_dir.glob("tests-py3.12-shard*/pytest.xml")):
        shard = int(re.search(r"shard(\d+)", xml.parent.name).group(1))
        for case in ET.parse(xml).getroot().iter("testcase"):
            classname, name = case.attrib.get("classname", ""), case.attrib.get("name", "")
            parts = classname.split(".")
            hit = None
            for cut in range(len(parts), 0, -1):
                if ".".join(parts[:cut]) in modules:
                    hit = cut
                    break
            seconds = float(case.attrib.get("time", "0") or 0)
            if hit is None:
                unresolved[classname] += seconds
                yield shard, None, seconds
                continue
            file = modules[".".join(parts[:hit])]
            rest = parts[hit:]
            nodeid = "::".join([file, *rest, name])
            yield shard, nodeid, seconds
    junit_cases.unresolved = unresolved


def summarize(loads: dict[int, float]) -> dict:
    values = [loads[k] for k in sorted(loads)]
    return {
        "per_shard_seconds": {str(k): round(loads[k], 1) for k in sorted(loads)},
        "max": round(max(values), 1),
        "min": round(min(values), 1),
        "spread": round(max(values) - min(values), 1),
        "mean": round(statistics.fmean(values), 1),
        "max_over_mean": round(max(values) / statistics.fmean(values), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--junit-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--totals", default="8,6", help="comma-separated shard totals to replay")
    args = parser.parse_args()

    plugin = load_plugin(args.plugin)
    weights = plugin.read_weights(str(args.weights))
    dedicated = set(plugin.DEDICATED_CASE_LANES.values())
    roster = [n for n in read_roster(args.roster) if n not in dedicated]
    files = {n.split("::", 1)[0] for n in roster} | set(weights)

    seconds = defaultdict(float)
    observed_shard_load = defaultdict(float)
    observed_file_shard = defaultdict(lambda: defaultdict(float))
    junit_total = unmatched_total = 0.0
    for shard, nodeid, value in junit_cases(args.junit_dir, files):
        junit_total += value
        observed_shard_load[shard] += value
        if nodeid is None:
            unmatched_total += value
            continue
        seconds[nodeid] += value
        observed_file_shard[shard][nodeid.split("::", 1)[0]] += value

    roster_set = set(roster)
    in_roster = sum(v for n, v in seconds.items() if n in roster_set)
    not_in_roster = sum(v for n, v in seconds.items() if n not in roster_set and n not in dedicated)
    result = {
        "plugin": str(args.plugin),
        "weights": str(args.weights),
        "roster": {"path": str(args.roster), "ordinary_occurrences": len(roster),
                   "ordinary_unique": len(roster_set)},
        "junit": {
            "dir": str(args.junit_dir),
            "total_case_seconds": round(junit_total, 1),
            "seconds_on_roster_nodeids": round(in_roster, 1),
            "seconds_on_nodeids_absent_from_roster": round(not_in_roster, 1),
            "seconds_with_unresolved_module": round(unmatched_total, 1),
            "roster_nodeids_with_a_duration": sum(1 for n in roster_set if n in seconds),
        },
        "observed_in_that_run": summarize(dict(observed_shard_load)),
        "replay": {},
    }

    for total in [int(t) for t in args.totals.split(",")]:
        file_owner = plugin.balanced_files((n.split("::", 1)[0] for n in roster), total, weights)
        node_owner = plugin.balanced_nodeids(roster, total, weights)
        by_file = {k: 0.0 for k in range(1, total + 1)}
        by_node = {k: 0.0 for k in range(1, total + 1)}
        predicted_file = {k: 0.0 for k in range(1, total + 1)}
        for path, owner in file_owner.items():
            predicted_file[owner] += weights.get(path, 0.0)
        for nodeid in roster_set:
            value = seconds.get(nodeid, 0.0)
            by_file[file_owner[nodeid.split("::", 1)[0]]] += value
            by_node[node_owner[nodeid]] += value
        result["replay"][str(total)] = {
            "file_level_predicted_from_weights": summarize(predicted_file),
            "file_level_true": summarize(by_file),
            "chunked_true": summarize(by_node),
            "chunked_max_minus_file_level_max": round(max(by_node.values()) - max(by_file.values()), 1),
        }

    # Was each shard's deviation shard-wide or confined to a few files?
    deviation = {}
    for shard in sorted(observed_file_shard):
        ratios, actual, predicted = [], 0.0, 0.0
        for path, value in observed_file_shard[shard].items():
            weight = weights.get(path)
            if weight is None:
                continue
            actual += value
            predicted += weight
            if weight >= 20.0:
                ratios.append((value / weight, weight, path))
        ratios.sort()
        only = [r for r, _, _ in ratios]
        quartiles = statistics.quantiles(only, n=4) if len(only) >= 4 else [None, None, None]
        biggest = sorted(ratios, key=lambda r: -abs(r[0] - 1) * r[1])[:3]
        deviation[str(shard)] = {
            "actual_over_predicted_total": round(actual / predicted, 3) if predicted else None,
            "files_with_weight_ge_20s": len(only),
            "per_file_ratio_q1_median_q3": [round(q, 3) if q is not None else None for q in quartiles],
            "largest_weighted_departures": [
                {"file": p, "weight": round(w, 1), "actual": round(r * w, 1), "ratio": round(r, 3)}
                for r, w, p in biggest],
        }
    result["per_shard_deviation_in_that_run"] = deviation

    text = json.dumps(result, indent=1)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
