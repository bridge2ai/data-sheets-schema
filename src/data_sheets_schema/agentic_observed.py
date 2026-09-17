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

    `output_tokens` per turn is what the estimate subtracts the visible
    output from — and in an agentic transcript the visible output is mostly
    tool-call payloads (the Write of the datasheet itself), not text, so
    `tool_input_chars` is subtracted with `visible_text_chars` (#1011). The
    API path has no tool calls; there the same subtraction is text only.
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
    blocks = thinking_chars = visible = tool_input = estimate = 0
    for mid, u in usage_by_msg.items():
        parts = blocks_by_msg.get(mid, {})
        m_visible = sum(chars for kind, chars in parts.values() if kind == "text")
        m_tool = sum(chars for kind, chars in parts.values() if kind == "tool_use")
        blocks += sum(1 for kind, _ in parts.values() if kind == "thinking")
        thinking_chars += sum(chars for kind, chars in parts.values() if kind == "thinking")
        visible += m_visible
        tool_input += m_tool
        # Per message and floored at 0, as the API path's log does per entry
        # (#1012), so the two subtractions are the same arithmetic.
        estimate += max(0, (u.get("output_tokens", 0) or 0) - (m_visible + m_tool) // 4)
    out = {"assistant_turns": len(usage_by_msg), "output_tokens": output,
           "thinking_blocks": blocks, "thinking_text_chars": thinking_chars,
           "visible_text_chars": visible, "tool_input_chars": tool_input,
           "reasoning_tokens_estimate": estimate}
    if counted:
        out["thinking_tokens"] = sum(counted)
        out["turns_with_thinking_tokens"] = len(counted)
    return out


def _block_parts(content: list) -> dict:
    """Each content block of a transcript line, keyed so the same block seen
    on two lines of one message counts once and different blocks of one
    message (the runtime writes one block per line) all count (#1011)."""
    parts = {}
    for c in content:
        kind = c.get("type")
        if kind in ("thinking", "redacted_thinking"):
            # Identity: the signature, a redacted block's opaque `data`, or
            # the text. Two identical text blocks or two id-less identical
            # tool calls in one message would count once — not a shape this
            # runtime writes, and a transcript line carries no block index.
            text = c.get("thinking") or ""
            parts[("thinking", c.get("signature") or c.get("data") or text)] = ("thinking", len(text))
        elif kind == "text":
            text = c.get("text") or ""
            parts[("text", text)] = ("text", len(text))
        elif kind == "tool_use":
            payload = json.dumps(c.get("input") or {}, ensure_ascii=False)
            parts[("tool_use", c.get("id") or payload)] = ("tool_use", len(payload))
    return parts


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
    # Per transcript first (#1935/#1944): a file is one runtime invocation's
    # record, but two files can describe one session — a copy cut short and
    # the complete file, or a resumed session whose second file re-lists the
    # first's messages — so files sharing a message id are reconciled into
    # one session before any total is chosen. Within a session usage is the
    # maximum snapshot per message id (#701), blocks and tool ids are unions,
    # and the terminal result is the one carried by the file that saw the
    # most messages.
    files: list[dict] = []
    bundle_name = bundle.name if bundle else None
    malformed = 0
    for path in transcripts:
        f = {"path": path, "usage": {}, "blocks": {}, "tools": {}, "searches": set(), "reads": {},
             "failed": set(), "first": None, "last": None, "terminal": None, "cut": False}
        with path.open(encoding="utf-8") as fh:
            for n, line in enumerate(fh):
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                raw = j.get("message")
                msg = raw if isinstance(raw, dict) else {}
                measurement = j.get("type") in ("assistant", "user") or isinstance(raw, dict)
                ts = j.get("timestamp")
                if ts:
                    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if until is not None and t > until:
                        # An excluded measurement event means a terminal
                        # result of this file describes more than the
                        # interval; an excluded informational line does not
                        # (#1936/#1945).
                        if measurement:
                            f["cut"] = True
                        continue
                    f["first"] = f["first"] or t
                    f["last"] = t
                if j.get("type") in ("assistant", "user") and not isinstance(raw, dict):
                    # Claude Code 2.1.272 stream-json writes informational
                    # lines (`system`, `result`, …) with a string `message`
                    # (#1915); they carry no usage or content. An assistant or
                    # user event whose message is not a mapping — a string, a
                    # list, an empty value, or no key at all (#1946) — is
                    # malformed and is counted, and every consumer treats the
                    # observation as invalid (#1930).
                    malformed += 1
                if j.get("type") == "result" and isinstance(j.get("usage"), dict):
                    # The runtime's own finalized accounting for the whole
                    # session: assistant events in stream-json carry only
                    # initial usage snapshots, so the per-message maximum
                    # undercounts by two orders of magnitude (#1931).
                    f["terminal"] = j["usage"]
                usage = msg.get("usage") or {}
                if usage:
                    mid = msg.get("id") or f"{path}:{j.get('uuid')}"
                    prev = f["usage"].get(mid)
                    if prev is None or usage.get("output_tokens", 0) >= prev.get("output_tokens", 0):
                        f["usage"][mid] = usage
                    content = [c for c in msg.get("content") or [] if isinstance(c, dict)]
                    f["blocks"].setdefault(mid, {}).update(_block_parts(content))
                for k, c in enumerate(msg.get("content") or []):
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "tool_result" and c.get("is_error"):
                        f["failed"].add(c.get("tool_use_id"))
                        continue
                    if c.get("type") != "tool_use":
                        continue
                    tid = c.get("id") or f"{path}:{n}:{k}"
                    f["tools"][tid] = True
                    inp = c.get("input") or {}
                    if not bundle_name:
                        continue
                    if c.get("name") == "Read" and bundle_name in str(inp.get("file_path", "")):
                        start = int(inp.get("offset") or 0)
                        # offset is 1-indexed; 0/absent means from the top.
                        start = max(start - 1, 0) if start else 0
                        f["reads"][tid] = (start, start + int(inp.get("limit") or READ_DEFAULT_LINES))
                    elif bundle_name in json.dumps(inp):
                        f["searches"].add(tid)
        files.append(f)
    sessions = _sessions(files)
    tools: set = set()
    searches: set = set()
    read_windows: dict[str, tuple[int, int]] = {}
    failed: set[str] = set()
    for f in files:
        tools.update(f["tools"]); searches.update(f["searches"])
        read_windows.update(f["reads"]); failed.update(f["failed"])
    duration_ms = 0
    out = {"total_tokens": 0, "tool_uses": len(tools)}
    measure: dict[str, int] = {}
    from_terminal = excluded = 0
    for members in sessions:
        usage_by_msg: dict[str, dict] = {}
        blocks_by_msg: dict[str, dict] = {}
        for f in members:
            for mid, u in f["usage"].items():
                prev = usage_by_msg.get(mid)
                if prev is None or u.get("output_tokens", 0) >= prev.get("output_tokens", 0):
                    usage_by_msg[mid] = u
            for mid, parts in f["blocks"].items():
                blocks_by_msg.setdefault(mid, {}).update(parts)
        firsts = [f["first"] for f in members if f["first"]]
        lasts = [f["last"] for f in members if f["last"]]
        if firsts and lasts:
            duration_ms += int((max(lasts) - min(firsts)).total_seconds() * 1000)
        cut = any(f["cut"] for f in members)
        carriers = sorted((f for f in members if f["terminal"] is not None), key=lambda f: len(f["usage"]))
        terminal = carriers[-1]["terminal"] if carriers else None
        total, m = _invocation_measure(usage_by_msg, blocks_by_msg, None if cut else terminal)
        if terminal is not None:
            if cut:
                excluded += 1
            else:
                from_terminal += 1
        out["total_tokens"] += total
        for k, v in m.items():
            measure[k] = measure.get(k, 0) + v
    out["duration_ms"] = duration_ms
    out.update(measure)
    if from_terminal:
        out["usage_from_terminal_result"] = from_terminal
    if excluded:
        # The session's finalized totals exist but describe events past the
        # cut, so the snapshot accounting stands and the observation says so
        # rather than passing as complete (#1945).
        out["terminal_results_excluded_by_cut"] = excluded
    if bundle:
        n_lines = sum(1 for _ in bundle.open(encoding="utf-8"))
        covered = set()
        for tid, (a, b) in read_windows.items():
            if tid in failed:
                continue
            covered.update(range(a, min(b, n_lines)))
        out["bundle_lines_read"] = len(covered)
        out["bundle_lines_total"] = n_lines
        out["_bundle_search_touches"] = len(searches)     # informational; not an observed field
        out["_bundle_reads_failed"] = sum(1 for t in read_windows if t in failed)
        if receipt is not None and manifest is not None:
            out.update(receipt_cross_check(covered, receipt, manifest))
    if malformed:
        out["malformed_message_events"] = malformed
    return out


def _sessions(files: list[dict]) -> list[list[dict]]:
    """Group transcripts that share a message id into one session (#1944);
    a transcript sharing none is a session of its own, so a killed-and-
    resumed run whose second file starts afresh stays two invocations."""
    parent = list(range(len(files)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    owner: dict[str, int] = {}
    for i, f in enumerate(files):
        for mid in f["usage"]:
            if mid in owner:
                parent[find(i)] = find(owner[mid])
            else:
                owner[mid] = i
    groups: dict[int, list[dict]] = {}
    for i, f in enumerate(files):
        groups.setdefault(find(i), []).append(f)
    return [groups[k] for k in sorted(groups)]

def _invocation_measure(usage_by_msg: dict, blocks_by_msg: dict, terminal_usage: dict | None) -> tuple[int, dict]:
    """One invocation's totals and reasoning measure. Where the invocation's
    transcript ends in a terminal ``result`` carrying usage and no event of
    that transcript fell outside the observed interval, the runtime's own
    finalized totals stand for the session (#1931): its ``total_tokens`` and
    ``output_tokens`` replace the per-message snapshot sums, and the
    estimate is the same subtraction pooled over the session, because the
    per-message outputs are not final and cannot be subtracted from one by
    one (#1937). A transcript with any event cut by ``until`` keeps the
    snapshot accounting: the terminal result describes the whole session,
    the cut part included (#1936). An invocation without a terminal result
    keeps the per-message method the API path's log uses."""
    m = reasoning_measure(usage_by_msg, blocks_by_msg)
    total = sum(_usage_total(u) for u in usage_by_msg.values())
    if terminal_usage is None:
        return total, m
    final_output = int(terminal_usage.get("output_tokens", 0) or 0)
    total = _usage_total(terminal_usage)
    m["output_tokens"] = final_output
    m["reasoning_tokens_estimate"] = max(
        0, final_output - (m.get("visible_text_chars", 0) + m.get("tool_input_chars", 0)) // 4)
    details = terminal_usage.get("output_tokens_details")
    if isinstance(details, dict) and isinstance(details.get("thinking_tokens"), int) \
            and not isinstance(details.get("thinking_tokens"), bool):
        m["thinking_tokens"] = details["thinking_tokens"]
        m["turns_with_thinking_tokens"] = m.get("assistant_turns", 0)
    return total, m

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
