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

Bundle coverage counts only the file-reading tool's *successful* windows over
the bundle (a read with no limit is the tool's default window of
READ_DEFAULT_LINES; a read that errored — the tool caps one response at
~25k tokens — counts as unread).
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


def observe(transcripts: list[Path], bundle: Path | None,
            until: datetime | None = None) -> dict:
    """Sum across transcripts. Two traps the first version fell into (#701):

    - one API response is written as several JSONL lines sharing a
      ``message.id``, each repeating the input/cache counts with a running
      ``output_tokens`` — summing per line roughly doubles the total. Usage is
      taken once per message id (max output seen);
    - a file-reading call can fail (the tool caps a response at ~25k tokens)
      and return nothing; its window must not count as read. Windows are
      kept only when their ``tool_result`` is not an error.

    ``duration_ms`` is the sum of each transcript's own first-to-last span, so
    a killed-and-resumed run excludes the gap between invocations.

    ``until`` cuts the observation at a timestamp: an agent that keeps acting
    after its run completed (stray re-invocations did this to one 2026-08-24
    agent) is not the run, and the record describes the run.
    """
    usage_by_msg: dict[str, dict] = {}
    tools = searches = 0
    duration_ms = 0
    read_windows: dict[str, tuple[int, int]] = {}   # tool_use_id -> window
    failed: set[str] = set()
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
                    if until is not None and t > until:
                        break
                    first = first or t
                    last = t
                msg = j.get("message") or {}
                usage = msg.get("usage") or {}
                if usage:
                    mid = msg.get("id") or f"{path}:{j.get('uuid')}"
                    prev = usage_by_msg.get(mid)
                    if prev is None or usage.get("output_tokens", 0) >= prev.get("output_tokens", 0):
                        usage_by_msg[mid] = usage
                for c in msg.get("content") or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "tool_result" and c.get("is_error"):
                        failed.add(c.get("tool_use_id"))
                        continue
                    if c.get("type") != "tool_use":
                        continue
                    tools += 1
                    inp = c.get("input") or {}
                    if not bundle_name:
                        continue
                    if c.get("name") == "Read" and bundle_name in str(inp.get("file_path", "")):
                        start = int(inp.get("offset") or 0)
                        # offset is 1-indexed; 0/absent means from the top.
                        start = max(start - 1, 0) if start else 0
                        read_windows[c.get("id")] = (start, start + int(inp.get("limit") or READ_DEFAULT_LINES))
                    elif bundle_name in json.dumps(inp):
                        searches += 1
        if first and last:
            duration_ms += int((last - first).total_seconds() * 1000)
    total = sum(_usage_total(u) for u in usage_by_msg.values())
    out = {"total_tokens": total, "tool_uses": tools, "duration_ms": duration_ms}
    if bundle:
        n_lines = sum(1 for _ in bundle.open(encoding="utf-8"))
        covered = set()
        for tid, (a, b) in read_windows.items():
            if tid in failed:
                continue
            covered.update(range(a, min(b, n_lines)))
        out["bundle_lines_read"] = len(covered)
        out["bundle_lines_total"] = n_lines
        out["_bundle_search_touches"] = searches          # informational; not an observed field
        out["_bundle_reads_failed"] = sum(1 for t in read_windows if t in failed)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("transcripts", nargs="+", type=Path)
    ap.add_argument("--bundle", type=Path, default=None,
                    help="the run's declared input bundle; enables coverage")
    ap.add_argument("--until", default=None,
                    help="ISO timestamp; ignore transcript events after it (an agent's "
                         "activity after its run completed is not the run)")
    args = ap.parse_args()
    until = datetime.fromisoformat(args.until.replace("Z", "+00:00")) if args.until else None
    missing = [str(t) for t in args.transcripts if not t.exists()]
    if missing:
        print(f"missing transcript(s): {missing}", file=sys.stderr)
        return 2
    obs = observe(args.transcripts, args.bundle, until)
    info = {k: v for k, v in obs.items() if k.startswith("_")}
    run = {k: v for k, v in obs.items() if not k.startswith("_")}
    print(json.dumps(run))
    if info:
        print(f"note: bundle search touches (not counted as read): "
              f"{info['_bundle_search_touches']}; bundle reads that errored "
              f"(not counted as read): {info['_bundle_reads_failed']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
