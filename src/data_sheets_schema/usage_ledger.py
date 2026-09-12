"""Durable completed-call usage, independent of the final provenance (#656)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid


class UsageLedgerError(OSError):
    """Past usage cannot be established; do not silently start more calls."""


def run_identity(spec) -> dict:
    return {key: getattr(spec, key) for key in ("project", "label", "method", "condition")}


def identity_is_foreign(spec, identity, *, recorded: bool = False) -> bool:
    """Use actual conflicting identity evidence, not a missing optional field."""
    if not isinstance(identity, dict):
        return False
    expected = run_identity(spec)
    if recorded and not spec.condition_stated:
        expected.pop("condition")
    return any(identity.get(key) is not None and identity[key] != value
               for key, value in expected.items())


def record_matches(spec, identity) -> bool:
    return (isinstance(identity, dict)
            and all(identity.get(key) == getattr(spec, key) for key in ("project", "method", "label"))
            and not identity_is_foreign(spec, identity, recorded=True))


def ledger_path(spec) -> Path:
    # Flat output directories may be reused for another label. Keep those
    # accounts separate, without putting an arbitrary label in a filename.
    key = hashlib.sha256(json.dumps(run_identity(spec), sort_keys=True).encode()).hexdigest()[:16]
    return spec.metadata_dir / f"{spec.project}_api_usage_{key}.json"


def _empty(spec, *, accept_legacy: bool) -> dict:
    return {"version": 1, "identity": run_identity(spec),
            "generation_id": uuid.uuid4().hex, "prior_generation_ids": [],
            "accept_legacy": accept_legacy, "rows": []}


def _read(spec) -> dict:
    path = ledger_path(spec)
    if not path.exists():
        return _empty(spec, accept_legacy=True)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UsageLedgerError(f"cannot recover API usage from {path}: {exc}") from exc
    if (not isinstance(data, dict) or data.get("version") != 1
            or data.get("identity") != run_identity(spec) or not isinstance(data.get("rows"), list)):
        raise UsageLedgerError(f"invalid API usage ledger identity or version: {path}")
    if (not isinstance(data.get("generation_id"), str) or not data["generation_id"]
            or not isinstance(data.get("accept_legacy"), bool)):
        raise UsageLedgerError(f"invalid API usage generation identity: {path}")
    prior = data.get("prior_generation_ids", [])
    if (not isinstance(prior, list) or any(not isinstance(value, str) or not value for value in prior)
            or len(set(prior)) != len(prior) or data["generation_id"] in prior):
        raise UsageLedgerError(f"invalid API usage generation history: {path}")
    ids = []
    for row in data["rows"]:
        if not isinstance(row, dict) or not isinstance(row.get("usage_id"), str) or not row["usage_id"]:
            raise UsageLedgerError(f"API usage row has no stable identity: {path}")
        ids.append(row["usage_id"])
    if len(set(ids)) != len(ids):
        raise UsageLedgerError(f"duplicate API usage identities in {path}")
    return data


def prepare_usage(spec, *, resume: bool) -> str:
    """Establish the generation boundary before any call can be made (#1291)."""
    path = ledger_path(spec)
    if resume and path.exists():
        return _read(spec)["generation_id"]
    data = _empty(spec, accept_legacy=resume)
    if path.exists():
        try:
            previous = _read(spec)
        except UsageLedgerError:
            previous = None  # explicit fresh execution retains opaque bad bytes
        if previous is not None:
            data["prior_generation_ids"] = [*previous.get("prior_generation_ids", []), previous["generation_id"]]
        # Copy and sync before atomically replacing the live ledger. A crash
        # before replacement leaves the old generation active and recoverable.
        archive = path.with_name(f"{path.stem}.previous-{uuid.uuid4().hex}.json")
        with archive.open("xb") as out:
            out.write(path.read_bytes())
            out.flush()
            os.fsync(out.fileno())
    _write(spec, data)
    return data["generation_id"]


def generation_id(spec) -> str | None:
    return _read(spec)["generation_id"] if ledger_path(spec).exists() else None


def prior_generation_ids(spec) -> list[str]:
    return list(_read(spec).get("prior_generation_ids", []))


def same_generation(spec, identifier) -> bool:
    if not ledger_path(spec).exists():
        return True  # a completed portable record needs no recovery journal
    data = _read(spec)
    return (identifier == data["generation_id"]
            or (identifier is None and data["accept_legacy"]))


def persist_usage(spec, row: dict) -> None:
    """Atomically save a call or its later outcome under the same identity."""
    if not isinstance(row.get("usage_id"), str) or not row["usage_id"]:
        raise UsageLedgerError("cannot persist an API usage row without its identity")
    data = _read(spec)
    rows = data["rows"]
    for index, previous in enumerate(rows):
        if previous["usage_id"] == row["usage_id"]:
            rows[index] = row
            break
    else:
        rows.append(row)
    _write(spec, data)


def _write(spec, data: dict) -> None:
    path = ledger_path(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.stem}.", suffix=".tmp", delete=False) as out:
            temporary = Path(out.name)
            json.dump(data, out, ensure_ascii=True, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    except (OSError, ValueError, TypeError) as exc:
        raise UsageLedgerError(f"could not persist API usage: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def append_usage(spec, usage: list[dict], row: dict) -> dict:
    row.setdefault("usage_id", uuid.uuid4().hex)
    persist_usage(spec, row)
    usage.append(row)
    return row


def merge_usage(spec, usage: list[dict]) -> list[dict]:
    """Recover each journaled call once; final record/live rows take precedence."""
    have = {r["usage_id"] for r in usage
            if isinstance(r, dict) and isinstance(r.get("usage_id"), str)}
    for row in _read(spec)["rows"]:
        if row["usage_id"] not in have:
            usage.append(row)
            have.add(row["usage_id"])
    return usage
