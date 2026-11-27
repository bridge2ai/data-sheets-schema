#!/usr/bin/env python3
"""Budget check between projects of a release series, 2026-11-25.

Purpose: before a replicate stream starts its next project, estimate how much of the
account's weekly Fable allowance the series has used and would use, from the finished
transcripts' own cost totals, and say whether the stream may start. No model call.

Calibration comes from the environment and is not kept in this file. For series
2026-11-25c the two values were constants here, taken from the owner's usage readings of
the account; they were removed from the published copy on 2026-11-25 at the owner's
decision (issue 6352), and the rest of the script is as it was run. The base reading
already contained the series' first run (the canary), whose cost was therefore not counted
again: name such a run in D4D_BUDGET_ALREADY_COUNTED.

Inputs:  --series LABEL-PREFIX --model M --condition C, the launch worktrees (each holds
         .temp/launch/transcripts/<label>_rep<N>/<PROJECT>.stream.jsonl), --state-dir with one
         stream_rep<N>.state file per stream ("running <PROJECT>" or "idle"), and
         --next PROJECT, the project the calling stream wants to start.
         Environment: D4D_BUDGET_BASE_PERCENT (allowance used at the base reading) and
         D4D_BUDGET_POINTS_PER_USD (allowance points per USD at list price), both required;
         D4D_BUDGET_ALREADY_COUNTED (optional, "REPLICATE:PROJECT").
Outputs: one line of JSON on stdout; exit 0 = may start, exit 3 = stop (also when the
         estimate cannot be made or the calibration is missing or not valid). The line holds estimates
         of the account's usage: remove them before publishing a log that contains it.
Serves:  the release-series rerun (PR 6325, issue 6324). Date: 2026-11-25.
"""
import argparse
import glob
import json
import os
import sys

def calibration():
    """(base percent, points per USD, already-counted key or None) from the environment."""
    base = float(os.environ["D4D_BUDGET_BASE_PERCENT"])
    points = float(os.environ["D4D_BUDGET_POINTS_PER_USD"])
    if not (base >= 0 and points > 0):      # also refuses nan; a ratio of zero or less would always answer start
        raise ValueError("base percent must be 0 or more and points per USD above 0")
    counted = os.environ.get("D4D_BUDGET_ALREADY_COUNTED", "")
    key = None
    if counted:
        replicate, separator, project = counted.partition(":")
        if not (separator and replicate.isdigit() and project and ":" not in project):
            raise ValueError("D4D_BUDGET_ALREADY_COUNTED must be REPLICATE:PROJECT, replicate a number")
        key = (replicate, project)
    return base, points, key


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
    try:
        BASE_PERCENT, POINTS_PER_USD, ALREADY_COUNTED = calibration()
    except KeyError as exc:
        print(json.dumps({"decision": "stop", "reason": "calibration not given: %s" % exc.args[0]}))
        return 3
    except ValueError:      # the values are not echoed: this line goes into the stream log
        print(json.dumps({"decision": "stop", "reason": "calibration not valid"}))
        return 3
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
