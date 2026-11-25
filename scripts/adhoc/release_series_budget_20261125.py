#!/usr/bin/env python3
"""Budget check between projects of a release series, 2026-11-25.

Purpose: before a replicate stream starts its next project, estimate how much of the
account's weekly Fable allowance the series has used and would use, from the finished
transcripts' own cost totals, and say whether the stream may start. No model call.

Calibration (owner's two /usage pastes on claude-work, 2026-11-25): the Fable week went
from 5 to 11 percent while about 21 USD at list price was spent, so 6 points per 21 USD,
an upper bound. The second paste (11 percent) already contains the series' first run
(CHORUS replicate 1, the canary), whose cost is therefore not counted again.

Inputs:  --series LABEL-PREFIX --model M --condition C, the launch worktrees (each holds
         .temp/launch/transcripts/<label>_rep<N>/<PROJECT>.stream.jsonl), --state-dir with one
         stream_rep<N>.state file per stream ("running <PROJECT>" or "idle"), and
         --next PROJECT, the project the calling stream wants to start.
Outputs: one line of JSON on stdout; exit 0 = may start, exit 3 = stop (also when the
         estimate cannot be made).
Serves:  the release-series rerun (PR 6325, issue 6324). Date: 2026-11-25.
"""
import argparse
import glob
import json
import os
import sys

BASE_PERCENT = 11.0          # claude-work Fable week at the second paste
POINTS_PER_USD = 6.0 / 21.0  # upper bound from the two pastes
ALREADY_COUNTED = ("1", "CHORUS")  # replicate 1 CHORUS is inside BASE_PERCENT
# Session minutes of the 2026-11-22b series relative to CHORUS, used until a project has a
# measured cost in this series.
RELATIVE = {"CHORUS": 1.0, "AI_READI": 2.4, "CM4AI": 1.8, "VOICE": 1.6, "VOICE_PEDIATRIC": 1.4}
LIMIT_PERCENT = 90.0


def result_cost(path):
    cost = None
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("type") == "result":
                    value = event.get("total_cost_usd")
                    if isinstance(value, (int, float)) and not event.get("is_error"):
                        cost = float(value)
    except OSError:
        return None
    return cost


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--condition", default="generic_v9")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--next", required=True, dest="next_project")
    parser.add_argument("--rep", required=True)
    parser.add_argument("worktrees", nargs="+")
    args = parser.parse_args()
    stem = "%s_%s-claudecode-%s_rep" % (args.series, args.model, args.condition.replace("_", "-"))
    costs = {}       # (rep, project) -> cost
    for tree in args.worktrees:
        for path in glob.glob(os.path.join(tree, ".temp/launch/transcripts", stem + "*", "*.stream.jsonl")):
            rep = os.path.basename(os.path.dirname(path))[len(stem):]
            project = os.path.basename(path)[:-len(".stream.jsonl")]
            cost = result_cost(path)
            if cost is not None:
                costs[(rep, project)] = cost
    spent = sum(cost for key, cost in costs.items() if key != ALREADY_COUNTED)
    by_project = {}
    for (rep, project), cost in costs.items():
        by_project.setdefault(project, []).append(cost)
    chorus = by_project.get("CHORUS")
    if not chorus:
        print(json.dumps({"decision": "stop", "reason": "no finished CHORUS run to scale from"}))
        return 3
    unit = sum(chorus) / len(chorus)

    def estimate(project):
        measured = by_project.get(project)
        if measured:
            return max(measured)          # the dearer of what was seen
        return unit * RELATIVE.get(project, max(RELATIVE.values()))

    in_flight = []
    for path in sorted(glob.glob(os.path.join(args.state_dir, "stream_rep*.state"))):
        rep = os.path.basename(path)[len("stream_rep"):-len(".state")]
        try:
            words = open(path, encoding="utf-8").read().split()
        except OSError:
            words = []
        if rep != args.rep and len(words) == 2 and words[0] == "running" and (rep, words[1]) not in costs:
            in_flight.append(words[1])
    now = BASE_PERCENT + spent * POINTS_PER_USD
    ahead = (estimate(args.next_project) + sum(estimate(project) for project in in_flight)) * POINTS_PER_USD
    projected = now + ahead
    decision = "start" if projected <= LIMIT_PERCENT else "stop"
    print(json.dumps({"decision": decision, "next": args.next_project, "rep": args.rep,
                      "finished_runs": len(costs), "spent_usd_beyond_base": round(spent, 2),
                      "fable_week_percent_now_estimate": round(now, 1),
                      "in_flight_elsewhere": in_flight,
                      "fable_week_percent_if_started_estimate": round(projected, 1),
                      "limit_percent": LIMIT_PERCENT}, sort_keys=True))
    return 0 if decision == "start" else 3


if __name__ == "__main__":
    sys.exit(main())
