"""Offline, path-only receipt repair with unchanged source evidence (#4446).

The map binds exact receipt/full bytes. Only the named slot strings may change;
resolution is structural, not a judgment that a snippet supports its new slot.
Original files, provenance, transcript history and API readdress behavior remain
unchanged. A new receipt never acquires the original receipt's measured origin.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re

import yaml

from data_sheets_schema import receipts
from data_sheets_schema.audit_omissions import MAX_INPUT_BYTES, _file, _read

VERSION = 1
MAX_PATH_BYTES = MAX_INPUT_BYTES
MAX_REPORT_BYTES = 32_000_000
LIMITATIONS = [
    "Target paths are structural possibilities, not semantic matches or support judgments.",
    "Only slot addresses change; source receipts, full records, provenance and transcripts are not written.",
    "A new receipt does not inherit the original receipt's measured origin or acceptance.",
]
_FIELDS = ("chunk", "entry", "slot", "new_slot")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _closed(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"{label} must contain exactly {', '.join(fields)}")


def _inputs(receipt_raw: bytes, full_raw: bytes):
    receipt = _read(receipt_raw, "receipt")
    full = _read(full_raw, "full record")
    if type(full) is not dict or type(receipt) is not dict or type(receipt.get("chunks")) is not list:
        raise ValueError("full record must be a mapping and receipt must have a chunks list")
    chunks = {}
    for index, chunk in enumerate(receipt["chunks"]):
        if type(chunk) is not dict or type(chunk.get("id")) is not str or not chunk["id"]:
            raise ValueError("each receipt chunk must have a nonempty string id")
        if chunk["id"] in chunks:
            raise ValueError("receipt chunk ids must be unique")
        if chunk.get("status") not in receipts.STATUSES:
            raise ValueError("receipt chunk status is not supported")
        chunks[chunk["id"]] = index
        if chunk["status"] == "extracted" or "extracted" in chunk:
            if chunk["status"] != "extracted" or type(chunk.get("extracted")) is not list:
                raise ValueError("extracted entries require extracted status and a list")
            for entry in chunk["extracted"]:
                if (type(entry) is not dict or type(entry.get("slot")) is not str
                        or type(entry.get("snippet")) is not str):
                    raise ValueError("each extracted entry needs string slot and snippet fields")
    return receipt, full, chunks


def _typed(value, path=(), masked=frozenset()):
    """Compare complete values without equating false/zero or changing strings.

    Mask positions during traversal, never by mutating a copied alias graph.
    An alias-induced slot change elsewhere must remain visible to this check.
    """
    if path in masked:
        return ("masked-slot",)
    kind = type(value)
    if kind is dict:
        return (kind, tuple((key, _typed(item, (*path, key), masked))
                            for key, item in value.items()))
    if kind is list:
        return (kind, tuple(_typed(item, (*path, index), masked)
                            for index, item in enumerate(value)))
    if kind is float:
        return (kind, value.hex())
    if kind in (date, datetime):
        return (kind, value.isoformat())
    return (kind, value)


def _target_paths(full):
    paths, total = [], 0

    def visit(value, path):
        nonlocal total
        if path and receipts.resolve(full, path):
            total += len(path.encode("utf-8"))
            if total > MAX_PATH_BYTES:
                raise ValueError("complete target-path inventory exceeds its byte bound")
            paths.append(path)
        if type(value) is dict:
            for key, item in value.items():
                # Literal punctuation in a key must not be mistaken for path syntax.
                if re.fullmatch(r"\w+", key):
                    visit(item, f"{path}.{key}" if path else key)
        elif type(value) is list:
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(full, "")
    return paths


def report_text(report) -> str:
    text = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    if len(text.encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError("complete readdress report exceeds its byte bound")
    return text


def inventory(receipt_raw: bytes, full_raw: bytes) -> dict:
    """List every unresolved chunk/ordinal and every resolvable target path."""
    from data_sheets_schema.api_runner import unresolved_receipt_slots

    receipt, full, _ = _inputs(receipt_raw, full_raw)
    result = {"version": VERSION, "receipt_sha256": _sha(receipt_raw),
              "full_sha256": _sha(full_raw),
              "unresolved": unresolved_receipt_slots(full, receipt),
              "candidate_paths": _target_paths(full), "limitations": list(LIMITATIONS)}
    report_text(result)  # Refuse an overlarge complete inventory, never truncate it.
    return result


def prepare(receipt_raw: bytes, full_raw: bytes, map_raw: bytes) -> tuple[bytes, dict]:
    """Validate the whole move map, then prepare new bytes without writing."""
    from data_sheets_schema.api_runner import apply_readdress

    receipt, full, chunks = _inputs(receipt_raw, full_raw)
    mapping = _read(map_raw, "readdress map")
    _closed(mapping, ("version", "receipt_sha256", "full_sha256", "moves"), "readdress map")
    if type(mapping["version"]) is not int or mapping["version"] != VERSION:
        raise ValueError("readdress map version must be integer 1")
    if mapping["receipt_sha256"] != _sha(receipt_raw) or mapping["full_sha256"] != _sha(full_raw):
        raise ValueError("readdress map hashes differ from the exact receipt/full inputs")
    if type(mapping["moves"]) is not list or not mapping["moves"]:
        raise ValueError("readdress map requires a nonempty moves list")
    rows, identities, masked = [], set(), set()
    for row in mapping["moves"]:
        _closed(row, _FIELDS, "each move")
        cid, ordinal, old, new = (row[key] for key in _FIELDS)
        if type(cid) is not str or cid not in chunks:
            raise ValueError("move names an unknown chunk")
        if type(ordinal) is not int or ordinal < 0:
            raise ValueError("move entry must be a nonnegative integer ordinal")
        if (cid, ordinal) in identities:
            raise ValueError("duplicate move chunk/entry identity")
        identities.add((cid, ordinal))
        entries = receipt["chunks"][chunks[cid]].get("extracted", [])
        if ordinal >= len(entries):
            raise ValueError("move names an unavailable extracted entry")
        if type(old) is not str or old != entries[ordinal]["slot"]:
            raise ValueError("move slot differs from the exact original entry")
        if receipts.resolve(full, old):
            raise ValueError("move source slot already resolves")
        if type(new) is not str or not receipts.resolve(full, new):
            raise ValueError("move new_slot does not resolve in the full record")
        rows.append(dict(zip(_FIELDS, (cid, ordinal, old, new))))
        masked.add(("chunks", chunks[cid], "extracted", ordinal, "slot"))
    candidate = deepcopy(receipt)
    summary = apply_readdress(candidate, full, deepcopy(rows))
    _closed(summary, ("moved", "dropped", "rejected", "emptied"), "readdress result")
    if (summary["dropped"] or summary["rejected"] or summary["emptied"]
            or _typed(summary["moved"]) != _typed(rows)):
        raise ValueError("readdress helper did not apply exactly the requested moves")
    for row in rows:
        if candidate["chunks"][chunks[row["chunk"]]]["extracted"][row["entry"]]["slot"] != row["new_slot"]:
            raise ValueError("readdress helper changed an unexpected target")
    if _typed(candidate, masked=masked) != _typed(receipt, masked=masked):
        raise ValueError("readdress changed receipt content outside the named slot strings")
    output = yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True, width=10_000).encode("utf-8")
    reread = _read(output, "serialized readdressed receipt")
    if _typed(reread) != _typed(candidate):
        raise ValueError("serialized readdressed receipt changes typed content")
    result = {"version": VERSION, "receipt_sha256": _sha(receipt_raw),
              "full_sha256": _sha(full_raw), "map_sha256": _sha(map_raw),
              "output_sha256": _sha(output), "moved": rows,
              "limitations": list(LIMITATIONS)}
    report_text(result)
    return output, result


def read_file(path: Path) -> bytes:
    return _file(Path(path), MAX_INPUT_BYTES)


def write_new(output: Path, raw: bytes, *, inputs: tuple[tuple[Path, bytes], ...]) -> None:
    """New-only output after current input-byte checks; no success on close failure.

    Every input read remains a separate snapshot, including repeated paths.
    An I/O failure may leave a partial newly created file, which is never retried
    or silently overwritten. This is not a concurrent-filesystem sandbox.
    """
    output = Path(output)
    if os.path.lexists(output):
        raise ValueError("readdress output must be a new file, not an existing path or symlink")
    parent = output.parent.resolve(strict=True)
    destination = parent / output.name
    for path, expected in inputs:
        if Path(path).resolve(strict=True) == destination:
            raise ValueError("readdress output aliases an input")
        if read_file(Path(path)) != expected:
            raise ValueError("readdress input bytes changed before output publication")
    stream = output.open("xb")  # O_EXCL also refuses a destination created since preflight.
    primary = None
    try:
        if stream.write(raw) != len(raw):
            raise OSError("incomplete readdress output write")
    except BaseException as exc:
        primary = exc
        raise
    finally:
        try:
            stream.close()
        except BaseException:
            if primary is None:
                raise
