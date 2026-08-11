"""Capture the model's reasoning blocks alongside each generated artifact.

A generated D4D record is the model's *conclusion*. The reasoning that produced
it — which source passage it credited, which candidate value it rejected — is
discarded the moment the response is parsed. That is the material an audit of a
disputed field would want, and it is unrecoverable afterwards: the same prompt
re-run is a different sample.

## What is actually available, measured

Reasoning arrives as a `thinking` content block. Whether that block carries
plaintext depends on the endpoint, so this module records what it observed
rather than assuming:

- **Direct Anthropic** (`ANTHROPIC_API_KEY`) — `thinking` carries text.
- **CBORG** (`google/claude-opus-5-high`, verified 2026-07-29) — the block
  arrives with a valid `signature` and `thinking: ''`. Not a streaming
  artifact: a non-streaming `messages.create` returns the same empty block, and
  the stream emits *no* `thinking_delta` events at all, only a `signature`
  event. The proxy strips the plaintext and forwards the signed envelope.

So on the endpoint this project currently generates with, **the reasoning text
is not obtainable**. Capturing it anyway is still worth the few lines: the
record then states that a reasoning block existed, was signed, and was withheld
— which is a different and more useful claim than silence — and the same code
captures the real text unchanged if a run is ever pointed at the direct API.

## The token estimate

`output_tokens` covers thinking *and* visible text, so when the plaintext is
withheld the difference between them is the only surviving measure of how much
reasoning happened. `reasoning_tokens_estimate` reports it, and is an estimate
in the strict sense — visible text is counted with a 4-chars-per-token
approximation, not by the tokenizer that billed it. It is sound for "this
judgement reasoned 10x longer than that one" and unsound for cost attribution.
This is also the quantity that explains truncation: a call can exhaust
`max_tokens` and return empty text, having spent the entire budget on thinking.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Visible-text tokens are estimated, not counted. The API bills a single
# output_tokens figure for thinking plus text and never breaks it down, so
# subtracting an estimate is the only available route to the thinking share.
CHARS_PER_TOKEN = 4


@dataclass
class ReasoningCapture:
    """What a single response revealed about its own reasoning."""

    blocks: list[dict[str, Any]] = field(default_factory=list)
    text_chars: int = 0
    output_tokens: int | None = None
    stop_reason: str | None = None

    @property
    def present(self) -> bool:
        """A reasoning block existed, whether or not its text came through."""
        return bool(self.blocks)

    @property
    def available(self) -> bool:
        """The reasoning text itself was returned, not just its envelope."""
        return any(b.get("chars") for b in self.blocks)

    @property
    def reasoning_tokens_estimate(self) -> int | None:
        if self.output_tokens is None:
            return None
        visible = self.text_chars // CHARS_PER_TOKEN
        return max(0, self.output_tokens - visible)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "reasoning_present": self.present,
            "reasoning_available": self.available,
            "blocks": self.blocks,
            "output_tokens": self.output_tokens,
            "visible_text_chars": self.text_chars,
            "reasoning_tokens_estimate": self.reasoning_tokens_estimate,
            "stop_reason": self.stop_reason,
        }
        if self.present and not self.available:
            d["withheld_note"] = (
                "The endpoint returned a signed but empty thinking block. The "
                "reasoning text was not available to capture; it was not lost "
                "by this code.")
        return d


def capture(resp) -> ReasoningCapture:
    """Read reasoning blocks off a response without assuming they carry text."""
    blocks: list[dict[str, Any]] = []
    text_chars = 0

    for b in getattr(resp, "content", None) or []:
        kind = getattr(b, "type", "")
        if kind == "text":
            text_chars += len(getattr(b, "text", "") or "")
            continue
        if kind not in ("thinking", "redacted_thinking"):
            continue
        thinking = getattr(b, "thinking", None) or ""
        entry: dict[str, Any] = {
            "type": kind,
            "chars": len(thinking),
            # A signature with no text is the signal that the plaintext was
            # withheld upstream rather than never produced. Store its presence,
            # never its value — it is long, opaque, and of no use here.
            "signed": bool(getattr(b, "signature", None)),
        }
        if thinking:
            entry["thinking"] = thinking
        blocks.append(entry)

    return ReasoningCapture(
        blocks=blocks,
        text_chars=text_chars,
        output_tokens=getattr(getattr(resp, "usage", None), "output_tokens", None),
        stop_reason=getattr(resp, "stop_reason", None))


def append(path: Path, entry: dict[str, Any]) -> None:
    """Append one JSON-lines record.

    JSONL because entries are written as each phase or judgement completes: a
    run that dies at phase 5 keeps the four reasoning records it earned, where a
    single JSON document rewritten each time would risk truncation mid-write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def read(path: Path) -> list[dict[str, Any]]:
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in
            Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def summarise(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate a reasoning log, keeping presence and availability distinct."""
    if not entries:
        return {"entries": 0}
    est = [e.get("reasoning_tokens_estimate") for e in entries]
    est = [x for x in est if x is not None]
    return {
        "entries": len(entries),
        "with_reasoning_block": sum(1 for e in entries
                                    if e.get("reasoning_present")),
        "with_reasoning_text": sum(1 for e in entries
                                   if e.get("reasoning_available")),
        "reasoning_tokens_estimate_total": sum(est) or None,
        "reasoning_tokens_estimate_max": max(est) if est else None,
        "truncated": sum(1 for e in entries
                         if e.get("stop_reason") == "max_tokens"),
    }


#: The first run whose phases wrote a reasoning log. Runs before this date are
#: missing one because capture postdates them — a different claim from a run
#: whose runtime cannot produce one, and from a run that should have written one
#: and did not.
CAPTURE_FROM = "2026-07-31"

NO_LOG_RUNTIME = "runtime_cannot_capture"
NO_LOG_PREDATES = "capture_postdates_run"
NO_LOG_MISSING = "missing"
HAS_LOG = "present"


def log_status(runtime: str | None, label: str, log_exists: bool) -> str:
    """Why does this run have no reasoning log? (#400)

    `d4d provenance reasoning` printed one message for every empty case, which
    conflated three different situations. They are not interchangeable:

    - ``runtime_cannot_capture`` — a Claude Code agentic run. The subagent has
      no access to its own token accounting, so no log can exist. Writing one
      carrying only the effort level would be *worse* than writing none: it
      would look comparable with the API path's and would not be, which is the
      substitution #400 argues against.
    - ``capture_postdates_run`` — an API run from before ``CAPTURE_FROM``.
      Unrecoverable, and nobody's fault.
    - ``missing`` — an API run from after capture existed, with no log. That is
      a defect rather than a limitation, and is the only one of the three worth
      chasing.

    The distinction matters wherever arms are compared: a missing reasoning
    figure for the agentic arm must not be read as zero spend.
    """
    if log_exists:
        return HAS_LOG
    if (runtime or "").strip().lower() == "claude code":
        return NO_LOG_RUNTIME
    if label[:10] < CAPTURE_FROM:
        return NO_LOG_PREDATES
    return NO_LOG_MISSING
