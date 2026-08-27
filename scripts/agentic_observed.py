#!/usr/bin/env python
"""Orchestrator-observed totals for an agentic run, from the runner's transcripts.

The agentic runtime cannot report its own accounting (#400). The launcher can
read the subagent runner's transcript files after the fact and sum what they
record: token usage per turn, tool uses, wall duration — and, since #700, how
much of the declared bundle the run actually opened. This script computes the
`--run` JSON for `d4d provenance annotate-observed` so the numbers come from
one place instead of an ad-hoc shell loop (the loop once summed the killed
invocation of a resumed run and missed the productive one, #688).

Transcripts live under the runner's config directory, which differs by account
(`~/.claude` or `~/.claude-work`); pass every transcript for the run,
including a killed first invocation, and the totals are summed across them.

    poetry run python scripts/agentic_observed.py \\
        --bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt \\
        ~/.claude-work/projects/<project>/<session>/subagents/agent-a<name>-*.jsonl

Bundle coverage counts only the file-reading tool's windows over the bundle
(a read with no limit is the tool's default window of READ_DEFAULT_LINES).
Searches (grep, shell) over the bundle are counted separately and reported,
but a line reached only by search is not counted as read: nothing attests
that the run saw its context.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

#: The file-reading tool returns this many lines when no limit is given.
READ_DEFAULT_LINES = 2000


def _usage_total(u: dict) -> int:
    return (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0) + u.get("output_tokens", 0))


def observe(transcripts: list[Path], bundle: Path | None) -> dict:
    total = tools = searches = 0
    duration_ms = 0
    windows: list[tuple[int, int]] = []
    bundle_name = bundle.name if bundle else None
    for path in transcripts:
        first = last = None
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = j.get("timestamp")
                if ts:
                    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    first = first or t
                    last = t
                msg = j.get("message") or {}
                usage = msg.get("usage") or {}
                total += _usage_total(usage)
                for c in msg.get("content") or []:
                    if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                        continue
                    tools += 1
                    inp = c.get("input") or {}
                    if not bundle_name:
                        continue
                    if c.get("name") == "Read" and bundle_name in str(inp.get("file_path", "")):
                        start = int(inp.get("offset") or 0)
                        # The tool's offset is 1-indexed for humans and 0 means
                        # "from the top"; a limit is a line count.
                        start = max(start - 1, 0) if start else 0
                        windows.append((start, start + int(inp.get("limit") or READ_DEFAULT_LINES)))
                    elif bundle_name in json.dumps(inp):
                        searches += 1
        if first and last:
            duration_ms += int((last - first).total_seconds() * 1000)
    out = {"total_tokens": total, "tool_uses": tools, "duration_ms": duration_ms}
    if bundle:
        n_lines = sum(1 for _ in bundle.open(encoding="utf-8"))
        covered = set()
        for a, b in windows:
            covered.update(range(a, min(b, n_lines)))
        out["bundle_lines_read"] = len(covered)
        out["bundle_lines_total"] = n_lines
        out["_bundle_search_touches"] = searches   # informational; not an observed field
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("transcripts", nargs="+", type=Path)
    ap.add_argument("--bundle", type=Path, default=None,
                    help="the run's declared input bundle; enables coverage")
    args = ap.parse_args()
    missing = [str(t) for t in args.transcripts if not t.exists()]
    if missing:
        print(f"missing transcript(s): {missing}", file=sys.stderr)
        return 2
    obs = observe(args.transcripts, args.bundle)
    info = {k: v for k, v in obs.items() if k.startswith("_")}
    run = {k: v for k, v in obs.items() if not k.startswith("_")}
    print(json.dumps(run))
    if info:
        print(f"note: bundle search touches (not counted as read): "
              f"{info['_bundle_search_touches']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
