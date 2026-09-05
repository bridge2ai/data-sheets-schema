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


def reasoning_measure(usage_by_msg: dict, blocks_by_msg: dict) -> dict:
    """The transcript's reasoning measure (#1000), flat non-negative integers
    so `annotate-observed` can validate them like the other totals.

    Comparable in kind with the API path's log: `output_tokens` per turn is
    what the estimate subtracts the visible text from, and
    `thinking_tokens` is the runtime's own count where the transcript
    carries `usage.output_tokens_details` (recent Claude Code versions; the
    key is omitted, not zeroed, when no turn has it). Cache-inclusive
    orchestrator accounting, never to be averaged with `api_usage`.
    """
    if not usage_by_msg:
        return {}
    output = sum(u.get("output_tokens", 0) or 0 for u in usage_by_msg.values())
    counted = [((u.get("output_tokens_details") or {}).get("thinking_tokens"))
               for u in usage_by_msg.values() if isinstance(u.get("output_tokens_details"), dict)]
    counted = [c for c in counted if isinstance(c, int) and not isinstance(c, bool)]
    blocks = sum(b[0] for b in blocks_by_msg.values())
    thinking_chars = sum(b[1] for b in blocks_by_msg.values())
    visible = sum(b[2] for b in blocks_by_msg.values())
    out = {"assistant_turns": len(usage_by_msg), "output_tokens": output,
           "thinking_blocks": blocks, "thinking_text_chars": thinking_chars,
           "visible_text_chars": visible,
           "reasoning_tokens_estimate": max(0, output - visible // 4)}
    if counted:
        out["thinking_tokens"] = sum(counted)
        out["turns_with_thinking_tokens"] = len(counted)
    return out


def receipt_cross_check(covered: set[int], receipt: Path, manifest: Path) -> dict:
    """Chunks the receipt marks reviewed whose lines the transcript never
    opened (#709). The receipt is the agent's claim; the read windows are
    the observation; a reviewed chunk with no window over it is the cheap
    cheat — or a read through a shell tool, which this counts as unopened:
    the playbook mandates the file tool for chunk reads for exactly this
    reason (#711 review F5), and parsing `sed -n`/`cat` is a known gap.
    `covered` is 0-based line indexes."""
    import yaml
    rec = yaml.safe_load(receipt.read_text(encoding="utf-8")) or {}
    man = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    spans = {c["id"]: c["lines"] for c in man.get("chunks") or []
             if isinstance(c, dict) and isinstance(c.get("id"), str) and isinstance(c.get("lines"), list)}
    claimed = [e.get("id") for e in rec.get("chunks") or [] if isinstance(e, dict)]
    strangers = sorted({str(c) for c in claimed if c not in spans})
    dupes = sorted({c for c in claimed if claimed.count(c) > 1 and c in spans})
    unopened = [cid for cid in spans if cid in claimed
                and any(i not in covered for i in range(spans[cid][0] - 1, spans[cid][1]))]
    unclaimed = [cid for cid in spans if cid not in claimed]
    # The denominator is the manifest, not the receipt (#732): a receipt of
    # bogus ids must not read as 0/0. Strangers, duplicates and unclaimed
    # chunks are reported beside it; the validator (#708) fails them.
    return {"receipt_chunks_total": len(spans),
            "receipt_chunks_unopened": len(unopened),
            "_receipt_unopened_ids": unopened, "_receipt_strangers": strangers,
            "_receipt_duplicates": dupes, "_receipt_unclaimed": unclaimed}


def observe(transcripts: list[Path], bundle: Path | None,
            until: datetime | None = None, receipt: Path | None = None,
            manifest: Path | None = None) -> dict:
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
    # Per API message, deduplicated like usage (#1000): thinking blocks,
    # their text length (0 through CBORG and this runtime alike), and the
    # visible text length the estimate subtracts.
    blocks_by_msg: dict[str, tuple[int, int, int]] = {}
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
                        continue
                    first = first or t
                    last = t
                msg = j.get("message") or {}
                usage = msg.get("usage") or {}
                if usage:
                    mid = msg.get("id") or f"{path}:{j.get('uuid')}"
                    prev = usage_by_msg.get(mid)
                    if prev is None or usage.get("output_tokens", 0) >= prev.get("output_tokens", 0):
                        usage_by_msg[mid] = usage
                    content = [c for c in msg.get("content") or [] if isinstance(c, dict)]
                    counts = (sum(1 for c in content if c.get("type") in ("thinking", "redacted_thinking")),
                              sum(len(c.get("thinking") or "") for c in content if c.get("type") == "thinking"),
                              sum(len(c.get("text") or "") for c in content if c.get("type") == "text"))
                    seen = blocks_by_msg.get(mid)
                    if seen is None or counts >= seen:
                        blocks_by_msg[mid] = counts
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
    out.update(reasoning_measure(usage_by_msg, blocks_by_msg))
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
        if receipt is not None and manifest is not None:
            out.update(receipt_cross_check(covered, receipt, manifest))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("transcripts", nargs="+", type=Path)
    ap.add_argument("--bundle", type=Path, default=None,
                    help="the run's declared input bundle; enables coverage")
    ap.add_argument("--until", default=None,
                    help="ISO timestamp; ignore transcript events after it (an agent's "
                         "activity after its run completed is not the run)")
    ap.add_argument("--receipt", type=Path, default=None,
                    help="the run's coverage receipt; with --manifest, reports chunks "
                         "marked reviewed that the transcript never opened (#709)")
    ap.add_argument("--manifest", type=Path, default=None,
                    help="the bundle's chunk manifest (data/preprocessed/chunks/)")
    args = ap.parse_args()
    if (args.receipt is None) != (args.manifest is None):
        print("--receipt and --manifest go together", file=sys.stderr)
        return 2
    if args.receipt is not None and args.bundle is None:
        print("--receipt needs --bundle: the cross-check is against the bundle's read windows", file=sys.stderr)
        return 2
    until = datetime.fromisoformat(args.until.replace("Z", "+00:00")) if args.until else None
    missing = [str(t) for t in args.transcripts if not t.exists()]
    if missing:
        print(f"missing transcript(s): {missing}", file=sys.stderr)
        return 2
    obs = observe(args.transcripts, args.bundle, until, args.receipt, args.manifest)
    info = {k: v for k, v in obs.items() if k.startswith("_")}
    run = {k: v for k, v in obs.items() if not k.startswith("_")}
    print(json.dumps(run))
    if info:
        print(f"note: bundle search touches (not counted as read): "
              f"{info['_bundle_search_touches']}; bundle reads that errored "
              f"(not counted as read): {info['_bundle_reads_failed']}", file=sys.stderr)
        if info.get("_receipt_unopened_ids"):
            print(f"receipt chunks marked reviewed but never opened by the file tool: "
                  f"{info['_receipt_unopened_ids']}", file=sys.stderr)
        for key, what in (("_receipt_strangers", "receipt ids not in the manifest"),
                          ("_receipt_duplicates", "receipt ids entered more than once"),
                          ("_receipt_unclaimed", "manifest chunks the receipt never mentions")):
            if info.get(key):
                print(f"{what}: {info[key]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
