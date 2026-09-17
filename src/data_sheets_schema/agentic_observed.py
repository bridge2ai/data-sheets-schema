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
    """Sum across transcripts, one invocation per file.

    Two traps the first version fell into (#701): one API response is
    written as several JSONL lines sharing a ``message.id``, each repeating
    the input/cache counts with a running ``output_tokens`` — summing per
    line roughly doubles the total, so usage is taken once per message id
    (max output seen); and a file-reading call can fail (the tool caps a
    response at ~25k tokens) and return nothing, so a window counts only
    when its ``tool_result`` is not an error.

    A file is one invocation. Where it ends in the runtime's own terminal
    ``result`` carrying usage (stream-json, #1931) and no measurement event
    before that result fell outside the observed interval, the file's
    messages take the finalized ``total_tokens`` and ``output_tokens`` and
    the estimate is the subtraction pooled over them, because per-message
    snapshots in stream-json are not final (#1937); a file without a usable
    result keeps the per-message method the API path's log uses. A result
    the cut excluded, or preceded by an excluded measurement event, is set
    aside and counted under ``terminal_results_excluded_by_cut`` while the
    file's messages rest on snapshots (#1945/#1953).

    Evidence that does not fit that model is refused rather than
    reconciled (#1972–#1976, after rounds of reconciliation each of which
    another synthetic shape defeated): a message id carried by two files, a
    usage-bearing message after a file's result, a second result in one
    file, or a result repeated under one identity is counted under
    ``overlapping_evidence``, and every consumer treats such an observation
    as invalid, like one with malformed events. Name one file per
    invocation: a copy cut short beside the complete transcript is not two
    pieces of evidence.

    ``duration_ms`` is the sum of each file's own first-to-last span, so a
    killed-and-resumed run excludes the gap between invocations. ``until``
    cuts the observation at a timestamp: an agent that keeps acting after
    its run completed is not the run, and the record describes the run.
    """
    bundle_name = bundle.name if bundle else None
    malformed = overlapping = 0
    owner: dict[str, Path] = {}          # message id -> the file that carries it
    tool_owner: dict[str, Path] = {}     # tool_use id -> the file that carries it (#1980)
    seen_paths: set[str] = set()
    result_ids: set[str] = set()
    tools: set[str] = set()
    searches: set[str] = set()
    read_windows: dict[str, tuple[int, int]] = {}   # tool_use_id -> window
    result_refs: list[tuple[Path, str, bool]] = []  # (file, tool_use_id, is_error) of every tool_result (#1996)
    duration_ms = total_tokens = 0
    measure: dict[str, int] = {}
    from_terminal = excluded = 0
    terminal_thinking = without_usage = 0
    for path in transcripts:
        # The same file again — by path, by inode or by bytes — is the same
        # evidence again (#1979/#1986): a copy whose lines carry no id at
        # all cannot be told apart by its events, only by its identity.
        # Cheap identities first, the byte digest streamed only for a file
        # the cheap ones do not already know (#1995).
        st = Path(path).stat()
        idents = {str(Path(path).resolve()), f"inode:{st.st_dev}:{st.st_ino}"}
        if not idents & seen_paths:
            idents.add("sha256:" + _file_digest(path))
        if idents & seen_paths:
            overlapping += 1
            continue
        seen_paths |= idents
        result_seen = False              # a result occurred, usable or not (#1991)
        usage_by_msg: dict[str, dict] = {}
        blocks_by_msg: dict[str, dict] = {}
        first = last = None
        terminal: dict | None = None
        terminal_excluded = cut_before_terminal = False
        results = 0
        with path.open(encoding="utf-8") as fh:
            for n, line in enumerate(fh):
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                raw = j.get("message")
                msg = raw if isinstance(raw, dict) else {}
                measurement = j.get("type") in ("assistant", "user") or isinstance(raw, dict)
                # A result line is an invocation boundary whatever it carries
                # (#1999). One with no usage at all finalizes nothing and the
                # snapshots stand; one whose usage is present but not complete
                # accounting is malformed and refused rather than read as zeros.
                is_result = j.get("type") == "result"
                has_usage = "usage" in j
                usage_ok = _usage_complete(j.get("usage"))
                ts = j.get("timestamp")
                if ts:
                    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if until is not None and t > until:
                        # A result the cut itself excludes is recorded before
                        # it is skipped (#1952), whatever envelope it carries
                        # (#1989); an excluded measurement event before the
                        # file's result means the result describes more than
                        # the interval, one after it — the orchestrator's
                        # trailing events — does not (#1953), and an excluded
                        # informational line never does.
                        if is_result:
                            results += 1
                            ident = j.get("uuid") or line.strip()
                            if ident in result_ids or results > 1:
                                overlapping += 1        # a repeated or second result (#1981)
                            result_ids.add(ident)
                            if has_usage and not usage_ok:
                                malformed += 1
                            elif not has_usage:
                                without_usage += 1
                            terminal_excluded = usage_ok; result_seen = True
                        elif measurement and not result_seen:
                            cut_before_terminal = True
                        continue
                    first = first or t
                    last = t
                if j.get("type") in ("assistant", "user") and not isinstance(raw, dict):
                    # Claude Code 2.1.272 stream-json writes informational
                    # lines (`system`, `result`, …) with a string `message`
                    # (#1915); they carry no usage or content. An assistant or
                    # user event whose message is not a mapping — a string, a
                    # list, an empty value, or no key at all (#1946) — is
                    # malformed and is counted, and every consumer treats the
                    # observation as invalid (#1930).
                    malformed += 1
                if is_result:
                    # The runtime's own finalized accounting for the whole
                    # session: assistant events in stream-json carry only
                    # initial usage snapshots, so the per-message maximum
                    # undercounts by two orders of magnitude (#1931).
                    results += 1
                    ident = j.get("uuid") or line.strip()
                    if ident in result_ids or results > 1:
                        overlapping += 1
                    result_ids.add(ident)
                    if usage_ok:
                        terminal = j["usage"]
                    elif has_usage:
                        malformed += 1
                    else:
                        # A result that finalizes nothing: the snapshots
                        # stand and the observation says so (#2002).
                        without_usage += 1
                    result_seen = True
                    # A result line is a result, whatever its envelope
                    # carries (#1993): it is not also a message.
                    continue
                usage = msg.get("usage") or {}
                # A message's identity is checked whether or not it carries
                # usage (#1992): the same message in two files, or one after
                # this file's result, is not this invocation's evidence.
                mid = (msg.get("id") or j.get("uuid") or f"{path}:{n}") if (msg.get("id") or usage) else None
                if mid is not None and (owner.setdefault(mid, path) != path or result_seen):
                    overlapping += 1
                elif usage:
                    prev = usage_by_msg.get(mid)
                    if prev is None or usage.get("output_tokens", 0) >= prev.get("output_tokens", 0):
                        usage_by_msg[mid] = usage
                    content = [c for c in msg.get("content") or [] if isinstance(c, dict)]
                    blocks_by_msg.setdefault(mid, {}).update(_block_parts(content))
                for k, c in enumerate(msg.get("content") or []):
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "tool_result":
                        result_refs.append((path, c.get("tool_use_id"), bool(c.get("is_error"))))
                        continue
                    if c.get("type") != "tool_use":
                        continue
                    if result_seen:
                        # A tool call after the file's result, usable or not,
                        # is outside the invocation (#1988/#1991).
                        overlapping += 1
                        continue
                    tid = c.get("id") or f"{path}:{n}:{k}"
                    if tool_owner.setdefault(tid, path) != path:
                        # A tool call carried by another file: the same
                        # refusal as a shared message (#1980).
                        overlapping += 1
                        continue
                    tools.add(tid)
                    inp = c.get("input") or {}
                    if not bundle_name:
                        continue
                    if c.get("name") == "Read" and bundle_name in str(inp.get("file_path", "")):
                        start = int(inp.get("offset") or 0)
                        # offset is 1-indexed; 0/absent means from the top.
                        start = max(start - 1, 0) if start else 0
                        read_windows[tid] = (start, start + int(inp.get("limit") or READ_DEFAULT_LINES))
                    elif bundle_name in json.dumps(inp):
                        searches.add(tid)
        if first and last:
            duration_ms += int((last - first).total_seconds() * 1000)
        usable = terminal is not None and not cut_before_terminal
        total, m = _invocation_measure(usage_by_msg, blocks_by_msg, terminal if usable else None)
        if usable:
            from_terminal += 1
            if _terminal_thinking(terminal) is not None:
                terminal_thinking += 1
        elif (terminal is not None or terminal_excluded) and usage_by_msg:
            # A set-aside result qualifies the file's retained messages; a
            # file with none retained qualifies nothing (#1968).
            excluded += 1
        total_tokens += total
        for k, v in m.items():
            measure[k] = measure.get(k, 0) + v
    # A tool result belongs to the file that made the call (#1996): one
    # that answers another file's call is foreign evidence and is refused,
    # and only a same-file error marks the window failed.
    failed: set[str] = set()
    for ref_path, tid, is_error in result_refs:
        owner_path = tool_owner.get(tid)
        if owner_path is not None and owner_path != ref_path:
            overlapping += 1
        elif is_error:
            failed.add(tid)
    out = {"total_tokens": total_tokens, "tool_uses": len(tools), "duration_ms": duration_ms}
    out.update(measure)
    if from_terminal:
        out["usage_from_terminal_result"] = from_terminal
    if without_usage:
        out["terminal_results_without_usage"] = without_usage
    if terminal_thinking and "thinking_tokens" in out:
        # Where any invocation's thinking is a session total from its
        # terminal result, no turn coverage is claimed for the aggregate,
        # whatever per-turn counts another invocation contributed (#1982);
        # a terminal result carrying no thinking detail leaves the per-turn
        # coverage as measured (#1987). The provenance is recorded, so a
        # consumer never infers it from the other keys (#1994).
        out.pop("turns_with_thinking_tokens", None)
        out["thinking_from_terminal_results"] = terminal_thinking
    if excluded:
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
    if overlapping:
        out["overlapping_evidence"] = overlapping
    return out


def _invocation_measure(usage_by_msg: dict, blocks_by_msg: dict, terminal_usage: dict | None) -> tuple[int, dict]:
    """One invocation's totals and reasoning measure. With a usable terminal
    ``result`` the runtime's own finalized totals stand for the file
    (#1931): ``total_tokens`` and ``output_tokens`` replace the per-message
    snapshot sums, the estimate is the same subtraction pooled over the
    file's messages, because the per-message outputs are not final (#1937),
    and ``thinking_tokens`` is the session total the result carries.
    Without one the per-message method the API path's log uses stands."""
    m = reasoning_measure(usage_by_msg, blocks_by_msg)
    total = sum(_usage_total(u) for u in usage_by_msg.values())
    if terminal_usage is None:
        return total, m
    final_output = int(terminal_usage.get("output_tokens", 0) or 0)
    total = _usage_total(terminal_usage)
    m["output_tokens"] = final_output
    m["reasoning_tokens_estimate"] = max(
        0, final_output - (m.get("visible_text_chars", 0) + m.get("tool_input_chars", 0)) // 4)
    thinking = _terminal_thinking(terminal_usage)
    if thinking is not None:
        # The runtime's session total, not a per-turn count: no turn
        # coverage is claimed for it (#1978).
        m["thinking_tokens"] = thinking
        m.pop("turns_with_thinking_tokens", None)
    return total, m


def _count_ok(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _usage_complete(usage) -> bool:
    """Is a terminal result's usage complete accounting (#1999/#2003)?
    input_tokens and output_tokens present, every count present a
    non-negative integer that is not a boolean, thinking detail included."""
    if not isinstance(usage, dict):
        return False
    for k in ("input_tokens", "output_tokens"):
        if not _count_ok(usage.get(k)):
            return False
    for k in ("cache_read_input_tokens", "cache_creation_input_tokens"):
        if k in usage and not _count_ok(usage[k]):
            return False
    details = usage.get("output_tokens_details")
    if details is not None:
        if not isinstance(details, dict):
            return False
        if "thinking_tokens" in details and not _count_ok(details["thinking_tokens"]):
            return False
    return True


def _file_digest(path: Path) -> str:
    """sha256 of a file, streamed (#1995)."""
    import hashlib
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _terminal_thinking(terminal_usage: dict) -> int | None:
    """The thinking count a terminal result carries, if any."""
    details = terminal_usage.get("output_tokens_details")
    if isinstance(details, dict) and isinstance(details.get("thinking_tokens"), int) \
            and not isinstance(details.get("thinking_tokens"), bool):
        return details["thinking_tokens"]
    return None

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
