"""Offline, byte-bound preparation/accounting for a future receipt turn (#2926).

This does not execute a model, select a coverage floor, or certify support.
The full/re-addressed phase-1 snapshot is the input; audit/report attempts,
especially terminal failures, must never be resumed through this interface.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema import receipts
from data_sheets_schema.chunking import chunk_texts, validate_manifest_mapping
from data_sheets_schema.duplicate_keys import find_duplicate_keys

RENDER_VERSION = 24
HEADER = "# Receipt completion: immutable inputs and every uncovered leaf\n\n"
INSTRUCTION = (
    "Return one YAML mapping with a `rereceipt` list. For EVERY listed path, "
    "return exactly one item: {path: ..., receipt: {chunk: cNNN, snippet: ...}} "
    "with a verbatim supporting passage from that exact chunk, OR "
    "{path: ..., unsupported: true, reason: ...}. Inspect the enclosing source "
    "context: a verified quotation alone does not establish support. Do not "
    "repeat, omit, rename, or add paths. Do not edit the record or receipt. "
    "An unsupported answer is a candidate for later independent audit, not "
    "permission to remove a value. Use only an existing uniquely listed chunk "
    "with status extracted, nothing_relevant, or redundant_with; never a "
    "duplicate_of chunk. A verified correction of the latter two judgments "
    "is retained and counted as a phase-1 status reversal. Return no other keys."
)
POLICY = (
    "offline preparation only; full/full_readdress before audit; receipts v4; "
    "all uncovered paths without truncation; explicit output cap; unsupported "
    "requires later independent audit; diagnostics nonterminal; no new coverage "
    "floor; no reopening terminal audit/report attempts; execution requires a "
    "separately registered condition and measured canaries"
)


def _mapping(raw: bytes, label: str) -> dict[str, Any]:
    text = raw.decode("utf-8")
    if find_duplicate_keys(text):
        raise ValueError(f"{label} has duplicate YAML keys")
    value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a YAML mapping")
    return value


@dataclass(frozen=True)
class Inputs:
    """Exact input bytes, not live paths or mutable parsed objects.

    The caller supplies the current phase-1 snapshot and its selected merged
    schema. Schema bytes are pinned, not schema-validated here. Recorded bundle
    recovery/materialization happens upstream; this layer refuses drift.
    """

    record: bytes
    receipt: bytes
    manifest: bytes
    bundle: bytes
    schema: bytes
    max_output_tokens: int

    def __post_init__(self) -> None:
        if type(self.max_output_tokens) is not int or self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be an explicit positive integer")
        for label in ("record", "receipt", "manifest", "bundle", "schema"):
            if not isinstance(getattr(self, label), bytes) or not getattr(self, label):
                raise ValueError(f"{label} must be nonempty immutable bytes")
        self.parsed()

    def parsed(self) -> tuple[dict, dict, dict, dict[str, str]]:
        record = _mapping(self.record, "record")
        receipt = _mapping(self.receipt, "receipt")
        manifest = _mapping(self.manifest, "manifest")
        _mapping(self.schema, "schema")
        validate_manifest_mapping(manifest, self.bundle, manifest.get("bundle"))
        md5 = hashlib.md5(self.bundle).hexdigest()
        if receipt.get("bundle_md5") != md5:
            raise ValueError("receipt bundle_md5 does not match the pinned bundle")
        entries = receipt.get("chunks")
        if not isinstance(entries, list):
            raise ValueError("receipt chunks must be a list")
        texts = dict(zip([c["id"] for c in manifest["chunks"]],
                         chunk_texts(self.bundle.decode("utf-8"), manifest["chunks"])))
        return record, receipt, manifest, texts

    def identity(self) -> dict[str, Any]:
        return {"sha256": {name: hashlib.sha256(getattr(self, name)).hexdigest()
                           for name in ("record", "receipt", "manifest", "bundle", "schema")},
                "render_version": RENDER_VERSION, "receipt_instrument_version": 4,
                "contract_sha256": hashlib.sha256(json.dumps(
                    [HEADER, INSTRUCTION, POLICY, receipts.RERECEIPTS_INSTRUMENT],
                    ensure_ascii=False).encode("utf-8")).hexdigest(),
                "max_output_tokens": self.max_output_tokens}

    def paths(self) -> list[str]:
        record, receipt, manifest, texts = self.parsed()
        return receipts.uncovered_receiptable_leaves(
            receipt, manifest, texts, record, manifest["bundle_md5"], original=record)

    def inventory(self) -> dict[str, Any]:
        return {"input_identity": self.identity(), "record": _mapping(self.record, "record"),
                "requested_paths": self.paths(), "policy": POLICY}


def parse_answers(raw: bytes) -> list[Any]:
    """Keep malformed list items for rejection accounting; never filter them out."""
    parsed = _mapping(raw, "answers")
    if set(parsed) != {"rereceipt"} or not isinstance(parsed["rereceipt"], list):
        raise ValueError("answers must contain only a rereceipt list")
    return parsed["rereceipt"]


def complete(inputs: Inputs, answers: list[Any], *, expected_identity: dict | None = None) -> dict[str, Any]:
    """Account for one response against exactly the prepared inputs.

    Answers-complete means every requested path has one accepted action, not
    that coverage is complete or that any claim is supported. Rejected extra
    answers also prevent that state. No record value is ever removed.
    """
    if not isinstance(answers, list):
        raise ValueError("answers must be a list")
    if expected_identity is not None and expected_identity != inputs.identity():
        raise ValueError("saved request identity differs from the completion inputs or contract")
    record, receipt, manifest, texts = inputs.parsed()
    md5 = manifest["bundle_md5"]
    listed = receipts.uncovered_receiptable_leaves(receipt, manifest, texts, record, md5, original=record)
    before = receipts.check(receipt, manifest, texts, record, md5, record, instrument_version=4)
    merged = receipts.apply_rereceipt(receipt, record, answers, texts,
                                      listed=listed, instrument_version=4)
    after = receipts.check(merged["receipt"], manifest, texts, record, md5, record, instrument_version=4)
    pending = receipts.uncovered_receiptable_leaves(
        merged["receipt"], manifest, texts, record, md5, original=record)
    requested = set(listed)
    supplied = {a["path"] for a in answers if isinstance(a, dict)
                and isinstance(a.get("path"), str) and a["path"] in requested}
    rejected = {r["path"] for r in merged["rejections"]
                if isinstance(r["path"], str) and r["path"] in requested}
    unanswered = [p for p in listed if p not in supplied]
    accepted = merged["added"] + merged["already_present"] + merged["unsupported"]
    return {"input_identity": inputs.identity(), "policy": POLICY,
            "schema_validation": "not performed; selected schema bytes pinned only",
            "state": "answers_complete" if accepted == len(listed) and not merged["rejected"]
                     else "answers_incomplete",
            "requested_paths": listed, "unanswered_paths": unanswered,
            "rejected_paths": [p for p in listed if p in rejected],
            "still_uncovered_paths": pending,
            "counts": {"requested": len(listed), "answers_received": len(answers),
                       "accepted": accepted, "unanswered": len(unanswered),
                       "rejected_answers": merged["rejected"], "rejected_paths": len(rejected),
                       "receipts_added": merged["added"], "already_present": merged["already_present"],
                       "unsupported": merged["unsupported"],
                       "never_receipted_before": len(listed), "never_receipted_after": len(pending),
                       "status_reversals_added": len(merged["status_changed"])},
            "unsupported_audit_candidates": merged["unsupported_paths"],
            "rejections": merged["rejections"], "added_pairs": merged["added_pairs"],
            "receipt": merged["receipt"], "before": before, "after": after}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("record", "receipt", "manifest", "bundle", "schema"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--max-output-tokens", type=int, required=True)
    parser.add_argument("--answers", type=Path, help="Saved YAML response; omitted means inventory only")
    parser.add_argument("--inventory", type=Path,
                        help="Previously saved inventory; required when checking answers")
    args = parser.parse_args()
    if bool(args.answers) != bool(args.inventory):
        parser.error("--answers and --inventory must be supplied together")
    inputs = Inputs(**{name: getattr(args, name).read_bytes()
                       for name in ("record", "receipt", "manifest", "bundle", "schema")},
                    max_output_tokens=args.max_output_tokens)
    if args.answers:
        inventory = _mapping(args.inventory.read_bytes(), "inventory")
        identity = inventory.get("input_identity")
        if not isinstance(identity, dict):
            parser.error("saved inventory must contain input_identity")
        result = complete(inputs, parse_answers(args.answers.read_bytes()), expected_identity=identity)
    else:
        result = inputs.inventory()
    print(yaml.safe_dump(result, sort_keys=False, allow_unicode=True), end="")


if __name__ == "__main__":
    main()
