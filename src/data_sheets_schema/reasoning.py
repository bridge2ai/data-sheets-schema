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

**The count is obtainable** (verified 2026-09-04, #999): CBORG now returns
`usage.output_tokens_details.thinking_tokens` — in the non-streaming body
and on the stream's `message_delta` usage — while still withholding the
text. The SDK's `get_final_message()` accumulates usage without that
field, so the runner reads it off the delta event and the capture records
it as `reasoning_tokens_observed` beside the estimate, with the estimate's
error where both exist. Records before this carry the estimate only.

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
    #: `output_tokens_details.thinking_tokens` as the endpoint reported it
    #: (#999); None where the endpoint returned no breakdown.
    thinking_tokens: int | None = None

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
            # The endpoint's own count where it gave one (#999), and how far
            # the estimate was from it: `estimate_error` is estimate minus
            # observed, positive when the estimate ran high. The estimate
            # stays for records that predate the count.
            "reasoning_tokens_observed": self.thinking_tokens,
            "stop_reason": self.stop_reason,
        }
        if self.thinking_tokens is not None and self.reasoning_tokens_estimate is not None:
            d["estimate_error"] = self.reasoning_tokens_estimate - self.thinking_tokens
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
        stop_reason=getattr(resp, "stop_reason", None),
        thinking_tokens=thinking_tokens(resp))


def thinking_tokens(resp) -> int | None:
    """`usage.output_tokens_details.thinking_tokens`, however the SDK carries
    it (#999): a model attribute, a `model_extra` entry, or a plain dict —
    the runner attaches the stream's delta usage as the last of these."""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return None
    details = getattr(usage, "output_tokens_details", None)
    if details is None and isinstance(getattr(usage, "model_extra", None), dict):
        details = usage.model_extra.get("output_tokens_details")
    if details is None and isinstance(usage, dict):
        details = usage.get("output_tokens_details")
    if details is None:
        return None
    value = details.get("thinking_tokens") if isinstance(details, dict) else getattr(details, "thinking_tokens", None)
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


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
    obs = [e.get("reasoning_tokens_observed") for e in entries]
    obs = [x for x in obs if x is not None]
    return {
        "entries": len(entries),
        "with_reasoning_block": sum(1 for e in entries
                                    if e.get("reasoning_present")),
        "with_reasoning_text": sum(1 for e in entries
                                   if e.get("reasoning_available")),
        "reasoning_tokens_estimate_total": sum(est) or None,
        "reasoning_tokens_estimate_max": max(est) if est else None,
        # The endpoint's own count (#999): entries that carry one, their
        # total, and — over the entries that carry both a count and an
        # estimate, which `with_estimate_error` counts — the summed error,
        # estimate minus observed.
        "with_observed_count": len(obs),
        "reasoning_tokens_observed_total": sum(obs) if obs else None,
        "with_estimate_error": sum(1 for e in entries if e.get("estimate_error") is not None),
        "estimate_error_total": (sum(e["estimate_error"] for e in entries
                                     if e.get("estimate_error") is not None)
                                 if obs else None),
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
#: An agentic run whose record carries a transcript-derived measure (#1000):
#: the orchestrator read the subagent's transcript, which records usage per
#: turn and, from recent runtimes, the thinking token count.
RECOVERED = "recovered_from_transcript"

#: The `run_observed` keys that make up that measure, written by
#: `scripts/agentic_observed.py` and `d4d provenance annotate-observed`.
OBSERVED_REASONING_KEYS = ("assistant_turns", "output_tokens", "thinking_blocks",
                           "thinking_text_chars", "visible_text_chars", "tool_input_chars",
                           "reasoning_tokens_estimate", "thinking_tokens",
                           "turns_with_thinking_tokens")


def log_status(runtime: str | None, label: str, log_exists: bool,
               observed: dict[str, Any] | None = None) -> str:
    """Why does this run have no reasoning log? (#400)

    `d4d provenance reasoning` printed one message for every empty case, which
    conflated three different situations. They are not interchangeable:

    - ``recovered_from_transcript`` — a Claude Code agentic run whose
      ``run_observed`` block carries the transcript-derived measure (#1000):
      the subagent cannot report its own accounting, but its transcript
      records usage per turn, signed (empty) thinking blocks, and — from
      recent runtimes — ``thinking_tokens``. Cache-inclusive runner
      accounting, one number per run: never averaged with ``api_usage``.
    - ``runtime_cannot_capture`` — a Claude Code agentic run with no such
      measure recorded. Writing a log carrying only the effort level would be
      *worse* than writing none: it would look comparable with the API
      path's and would not be, which is the substitution #400 argues against.
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
        if isinstance(observed, dict) and observed.get("output_tokens") is not None:
            return RECOVERED
        return NO_LOG_RUNTIME
    if label[:10] < CAPTURE_FROM:
        return NO_LOG_PREDATES
    return NO_LOG_MISSING
