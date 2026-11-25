#!/usr/bin/env python3
"""Summarize a finished release series from its gate files and transcripts, 2026-11-25.

Purpose: one row per record of a release series (project x replicate), read from what each
run left behind in its launch worktree: the gate file written by
run_release_series_20261124.sh and the stream-json transcript. No model call, nothing
written to a worktree.

Inputs:  --series LABEL-PREFIX --model M --condition C, then the launch worktrees.
Outputs: a TSV on stdout (one row per record, then totals); exit 0 when every record has
         GATES: PASS, a single exact model, one recorder attempt and no permission denial
         left in its result; exit 1 otherwise.
Serves:  the release-series rerun 2026-11-25c (PR 6325, issues 6324, 6312). Date: 2026-11-25.
"""
import argparse
import glob
import json
import os
import re
import sys


def transcript_facts(path, model):
    facts = {"cost": None, "retries_529": 0, "denials": 0, "other_models": set(), "turns": 0,
             "result": None}
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get("type")
            if kind == "assistant":
                used = (event.get("message") or {}).get("model")
                if used == model:
                    facts["turns"] += 1
                elif used and used != "<synthetic>":
                    facts["other_models"].add(used)
            elif kind == "system" and event.get("subtype") == "api_retry":
                if event.get("error_status") == 529:
                    facts["retries_529"] += 1
            elif kind == "result":
                facts["result"] = event.get("subtype")
                value = event.get("total_cost_usd")
                if isinstance(value, (int, float)):
                    facts["cost"] = float(value)
                facts["denials"] = len(event.get("permission_denials") or [])
    return facts


def gate_facts(path):
    text = open(path, encoding="utf-8").read()

    def find(pattern, default=""):
        match = re.search(pattern, text, re.M)
        return match.group(1) if match else default

    return {
        "gates": find(r"^GATES: (\S+)"),
        "minutes": find(r"\| minutes ([0-9.]+)"),
        "recorder_attempts": find(r"^transcript recorder attempts: (\d+)"),
        "advisor_calls": find(r"^transcript advisor calls: (\d+)"),
        "models": find(r"^transcript models: (.*)$"),
        "full_bytes": find(r"_d4d\.yaml \((\d+) bytes\)"),
        "core_bytes": find(r"_d4d_core\.yaml \((\d+) bytes\)"),
        "chunks": find(r"chunks (\d+/\d+) reviewed"),
        "snippets": find(r"snippets (\d+/\d+) verified"),
        "slots": find(r"slots (\d+/\d+) with a receipt"),
        "render": find(r"^render gate: (\S+)"),
        "window": find(r"session exit \d+\s+(\S+ -> \S+)"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--condition", default="generic_v9")
    parser.add_argument("worktrees", nargs="+")
    args = parser.parse_args()
    stem = "%s_%s-claudecode-%s_rep" % (args.series, args.model, args.condition.replace("_", "-"))
    rows, bad, total_cost = [], [], 0.0
    for tree in args.worktrees:
        for gate in sorted(glob.glob(os.path.join(tree, ".temp/launch/gates", "*_" + stem + "*.txt"))):
            name = os.path.basename(gate)[:-len(".txt")]
            project, rep = name.split("_" + stem)
            facts = gate_facts(gate)
            stream = os.path.join(tree, ".temp/launch/transcripts", stem + rep, project + ".stream.jsonl")
            seen = transcript_facts(stream, args.model) if os.path.exists(stream) else None
            row = [project, "rep" + rep, facts["gates"], facts["window"], facts["minutes"],
                   str(seen["turns"]) if seen else "", facts["recorder_attempts"],
                   facts["full_bytes"], facts["core_bytes"], facts["chunks"], facts["snippets"],
                   facts["slots"], facts["render"],
                   "%.2f" % seen["cost"] if seen and seen["cost"] is not None else "",
                   str(seen["retries_529"]) if seen else "", str(seen["denials"]) if seen else "",
                   ",".join(sorted(seen["other_models"])) if seen else "no transcript"]
            rows.append(row)
            if seen and seen["cost"] is not None:
                total_cost += seen["cost"]
            problems = []
            if facts["gates"] != "PASS":
                problems.append("gates " + facts["gates"])
            if facts["recorder_attempts"] != "1":
                problems.append("recorder attempts " + facts["recorder_attempts"])
            if not seen:
                problems.append("no transcript")
            else:
                if seen["other_models"]:
                    problems.append("other models")
                if seen["denials"]:
                    problems.append("%d permission denial(s)" % seen["denials"])
                if seen["result"] != "success":
                    problems.append("result %s" % seen["result"])
            if problems:
                bad.append("%s rep%s: %s" % (project, rep, "; ".join(problems)))
    rows.sort(key=lambda row: (row[1], row[0]))
    print("\t".join(["project", "rep", "gates", "window_utc", "minutes", "model_messages",
                     "recorder_attempts", "full_bytes", "core_bytes", "chunks", "snippets",
                     "slots", "render", "cost_usd", "retries_529", "denials", "other_models"]))
    for row in rows:
        print("\t".join(row))
    print("# records: %d; total list-price cost USD: %.2f" % (len(rows), total_cost))
    for line in bad:
        print("# ATTENTION " + line)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
