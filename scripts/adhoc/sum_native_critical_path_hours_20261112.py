#!/usr/bin/env python3
"""Purpose: sum the rough effort ranges of the Codex helper's gate ledger for
the first native canary (handoffs/codex-native-critical-path-20261112.json),
in total, by who does the gate, and by state, and list the gates the owner
has to act on. It also walks the dependency graph to report the longest
chain of worker and lead hours, which is the least elapsed effort if every
independent lane ran at once.

Inputs: the JSON path (argument 1). Reads only.
Outputs: stdout.
Serves: owner direction D134 (native arm first); the lead's report to the
owner. Date: 2026-11-12.

The ranges are the helper's estimates for a successful first pass. This
script only adds them; it makes no estimate of its own.
"""
import json
import sys
from collections import defaultdict
from functools import lru_cache


def main() -> int:
    ledger = json.load(open(sys.argv[1]))
    gates = {g["id"]: g for g in ledger["gates"]}
    lo = sum(g["effort_hours"][0] for g in gates.values())
    hi = sum(g["effort_hours"][1] for g in gates.values())
    print(f"gates: {len(gates)}; total hours {lo:g} to {hi:g}")
    for field in ("who", "state"):
        groups = defaultdict(lambda: [0, 0.0, 0.0])
        for g in gates.values():
            row = groups[g[field]]
            row[0] += 1
            row[1] += g["effort_hours"][0]
            row[2] += g["effort_hours"][1]
        for key, (n, a, b) in sorted(groups.items()):
            print(f"  by {field} {key}: {n} gates, {a:g} to {b:g} hours")

    @lru_cache(maxsize=None)
    def chain(gid: str) -> tuple[float, float]:
        g = gates[gid]
        best = (0.0, 0.0)
        for dep in g["depends_on"]:
            cand = chain(dep)
            if cand[1] > best[1]:
                best = cand
        return best[0] + g["effort_hours"][0], best[1] + g["effort_hours"][1]

    last = max(gates, key=lambda gid: chain(gid)[1])
    a, b = chain(last)
    print(f"longest dependency chain ends at {last}: {a:g} to {b:g} hours")
    owner = [g for g in gates.values() if g["who"] == "owner"]
    print(f"gates the owner acts on: {len(owner)}")
    for g in owner:
        print(f"  {g['id']} [{g['state']}] {g['gate']}")
    ready = [g for g in gates.values()
             if g["state"] != "done" and g["who"] != "owner"
             and all(gates[d]["state"] == "done" for d in g["depends_on"])]
    print("worker or lead gates whose dependencies are all done:")
    for g in ready:
        print(f"  {g['id']} ({g['who']}, {g['effort_hours'][0]:g} to {g['effort_hours'][1]:g} h) {g['gate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
