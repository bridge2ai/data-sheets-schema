"""The receipt-origin block a provenance record carries (#2933).

`receipt_origin.origin` reads a run's transcript and says which coverage-
receipt snippets were in the receipt when the full record was first written
(`contemporaneous`) and which were added after it (`phase1_correction`,
`phase3_backport`). It writes nothing. This module is what a record keeps of
that report, under `receipts.origin`, and the line the gate summaries print
beside "snippets verified". The record contract's `receipts` block is an
open AnyBlock (`d4d_generation_record.yaml`), so the sub-block needs no
contract change; a new top-level block would.

Which block a writer records (`for_record`):

- given the run's transcripts (`d4d receipts check --write --transcript T`),
  the block is measured from them, and replaces what was there;
- given none -- `d4d provenance record`, `backfill-checks`, and `receipts
  check` without `--transcript`, none of which holds a transcript -- a
  measurement the record already carries is kept while the receipt on disk
  still has the sha256 it was measured on. A recomputation that cannot read
  the evidence must never erase a measurement (#907). Where the receipt has
  changed since, the block is `unknown` and the measurement is kept under
  `prior`, never shown as the split of bytes it did not read;
- with no measurement to keep, the block is `unknown` with the reason, and
  carries no classification: never `contemporaneous` (#2933).

The copy names no local path: transcripts by basename and sha256, as records
name them elsewhere (`run_observed_extended`), and the receipt by sha256 (the
receipts block beside it names the receipt's path). It keeps the instrument
and `NON_CHECKS` beside the counts. A block read from no transcript carries
neither: no instrument ran, so nothing is claimed to qualify.

Reported, never gated: post-draft snippets stay unaccepted for semantic
support until independent review (#2067), and no floor reads them.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

from data_sheets_schema import receipt_origin as ro

#: The writer had no transcript and the record carried no measurement.
NO_TRANSCRIPT = ("no transcript was given to the command that wrote this block, and the record carried "
                 "no measurement of its receipt: the receipt's history was not read, so no snippet is "
                 "classified")
#: An API-path record (it carries `api_usage`) has no tool-call transcript.
API_PATH = ("an API-path record: its receipt is returned inside the full phase's response, not written by "
            "tool calls, so there is no transcript for this instrument to read; that path's own accounts "
            "are the phase-1 snapshot (#807) and the receipt as written (#952)")


def measured(block: Any) -> bool:
    """Whether a block was read from transcripts -- at least one, each read
    (its sha256 recorded): a measurement, whatever its status. A block
    written with none, or naming one that could not be read, is not."""
    transcripts = block.get("transcripts") if isinstance(block, dict) else None
    return (isinstance(transcripts, list) and bool(transcripts)
            and all(isinstance(t, dict) and isinstance(t.get("sha256"), str) for t in transcripts))


def record_copy(block: dict[str, Any], *, recorded_by: str | None = None) -> dict[str, Any]:
    """`receipt_origin.origin`'s block as a record carries it: every key kept
    but the local paths -- a transcript by its basename beside its sha256,
    the receipt and the full record by their counts and hashes alone."""
    out = deepcopy(block)
    out["transcripts"] = [{"name": Path(t["path"]).name, "sha256": t.get("sha256"), "lines": t.get("lines")}
                          for t in block.get("transcripts") or []]
    for kind in ("receipt", "full"):
        if isinstance(out.get(kind), dict):
            out[kind] = {k: v for k, v in out[kind].items() if k not in ("path", "at_run")}
    if recorded_by is not None:
        out["recorded_by"] = recorded_by
    return out


def unknown(reason: str, *, prior: dict[str, Any] | None = None) -> dict[str, Any]:
    """A block no transcript was read for: the status and why, nothing else."""
    out: dict[str, Any] = {"instrument": ro.INSTRUMENT, "status": "unknown", "reasons": [reason], "transcripts": []}
    if prior is not None:
        out["prior"] = prior
    return out


def _last_measurement(prior: Any) -> dict[str, Any] | None:
    """The measurement a recorded block is or keeps: itself, or the one an
    `unknown` keeps under `prior` after its receipt changed."""
    if measured(prior):
        return prior
    if isinstance(prior, dict) and measured(prior.get("prior")):
        return prior["prior"]
    return None


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def for_record(prior: Any, receipt: Path, full: Path, *, transcripts: Sequence[Path] = (),
               receipt_at_run: Path | None = None, full_at_run: Path | None = None,
               api_path: bool = False, recorded_by: str | None = None) -> dict[str, Any]:
    """The `receipts.origin` block a writer records; see the module docstring.

    `prior` is the block the record carries now (or None), `receipt` and
    `full` the run's files as they are now, `transcripts` the run's, first
    invocation first. `receipt_at_run`/`full_at_run` are the paths as the
    transcript spelled them, where the files have moved (#3047).
    `recorded_by` names the command that read the transcripts; a kept
    measurement keeps its own.
    """
    if transcripts:
        return record_copy(ro.origin([Path(t) for t in transcripts], Path(receipt), Path(full),
                                     receipt_at_run=receipt_at_run, full_at_run=full_at_run),
                           recorded_by=recorded_by)
    last = _last_measurement(prior)
    if last is None:
        return unknown(API_PATH if api_path else NO_TRANSCRIPT)
    now = _sha256(receipt)
    then = last["receipt"].get("sha256") if isinstance(last.get("receipt"), dict) else None
    if then is not None and now == then:
        return deepcopy(last)
    return unknown(f"the receipt on disk (sha256 {now or 'unreadable'}) is not the receipt its origin was "
                   f"measured on (sha256 {then or 'not read'}): it changed after the transcripts that were "
                   "read, so their classification is not this receipt's; the measurement is kept under `prior`",
                   prior=deepcopy(last))


def split(receipts: Any) -> dict[str, int] | None:
    """The counts a gate summary shows beside "snippets verified": each
    origin, `post_draft` (the two after the draft), `removed_contemporaneous`
    and `readdressed`. None unless the block's origin was measured `checked`
    on the receipt the block checked (the same sha256, where the block pins
    one): a split of other bytes is never shown beside these counts."""
    origin = receipts.get("origin") if isinstance(receipts, dict) else None
    if not isinstance(origin, dict) or origin.get("status") != "checked" or not isinstance(origin.get("origin"), dict):
        return None
    artifacts = receipts.get("artifacts")
    pinned = (artifacts["receipt"].get("sha256")
              if isinstance(artifacts, dict) and isinstance(artifacts.get("receipt"), dict) else None)
    measured_on = origin["receipt"].get("sha256") if isinstance(origin.get("receipt"), dict) else None
    if pinned is not None and pinned != measured_on:
        return None
    values = {k: origin["origin"].get(k) for k in ro.ORIGINS}
    values.update(removed_contemporaneous=origin.get("removed_contemporaneous"), readdressed=origin.get("readdressed"))
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in values.values()):
        return None
    values["post_draft"] = values["phase1_correction"] + values["phase3_backport"]
    return values


def line(receipts: Any) -> str | None:
    """One line for a gate summary, or None where the receipts block carries
    no origin."""
    origin = receipts.get("origin") if isinstance(receipts, dict) else None
    if not isinstance(origin, dict):
        return None
    counts = split(receipts)
    if counts is not None:
        return (f"receipt origin: {counts['contemporaneous']} contemporaneous · {counts['phase1_correction']} "
                f"phase-1 correction · {counts['phase3_backport']} phase-3 back-port ({counts['post_draft']} "
                "post-draft, unaccepted as semantic support until independent review, #2067) · "
                f"{counts['removed_contemporaneous']} contemporaneous removed · {counts['readdressed']} re-addressed")
    if origin.get("status") == "checked":
        return "receipt origin: measured on other bytes than the receipt checked here; not shown beside its counts"
    reasons = [r for r in origin.get("reasons") or [] if isinstance(r, str)]
    more = f" (+{len(reasons) - 1} more)" if len(reasons) > 1 else ""
    return f"receipt origin: unknown — {reasons[0] if reasons else 'no reason recorded'}{more}"
