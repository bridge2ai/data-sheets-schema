"""Durable completed-call usage, independent of the final provenance (#656)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

import yaml


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


def _record_generations(spec) -> list[str]:
    """A portable record can retain history after its ledger was omitted."""
    try:
        record = yaml.safe_load(spec.provenance_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return []  # explicit fresh execution also permits malformed old records
    identity = record.get("run") if isinstance(record, dict) else None
    if not record_matches(spec, identity):
        return []
    generation = identity.get("generation_id")
    if not isinstance(generation, str) or not generation:
        return []
    history = identity.get("prior_generation_ids") or []
    if not isinstance(history, list):
        history = []
    return list(dict.fromkeys(value for value in [*history, generation]
                              if isinstance(value, str) and value))


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
    pending = data.get("pending_call")
    if pending is not None and (
            not isinstance(pending, dict) or not isinstance(pending.get("usage_id"), str)
            or not pending["usage_id"] or pending["usage_id"] in ids):
        raise UsageLedgerError(f"invalid pending API call identity: {path}")
    return data


def require_resolved(spec) -> None:
    pending = _read(spec).get("pending_call")
    if pending is not None:
        raise UsageLedgerError(
            f"API call {pending['usage_id']} has unresolved accounting in {ledger_path(spec)}; "
            "restore its usage before resuming, or explicitly start fresh to archive this generation")


def begin_call(spec, phase: str, attempt: int, started_at: str) -> str:
    """Commit intent before a request so response persistence can fail safely."""
    require_resolved(spec)
    data = _read(spec)
    identifier = uuid.uuid4().hex
    data["pending_call"] = {"usage_id": identifier, "phase": phase,
                            "attempt": attempt, "started_at": started_at}
    _write(spec, data)
    return identifier


def cancel_call(spec, identifier: str) -> None:
    """Resolve a transport error that delivered no completed response."""
    data = _read(spec)
    if (data.get("pending_call") or {}).get("usage_id") != identifier:
        raise UsageLedgerError("cannot resolve a different pending API call")
    data.pop("pending_call")
    _write(spec, data)


def prepare_usage(spec, *, resume: bool) -> str:
    """Establish the generation boundary before any call can be made (#1291)."""
    path = ledger_path(spec)
    if resume and path.exists():
        require_resolved(spec)
        return _read(spec)["generation_id"]
    data = _empty(spec, accept_legacy=resume)
    if not resume:
        data["prior_generation_ids"] = _record_generations(spec)
    if path.exists():
        try:
            previous = _read(spec)
        except UsageLedgerError:
            previous = None  # explicit fresh execution retains opaque bad bytes
        if previous is not None:
            data["prior_generation_ids"] = list(dict.fromkeys([
                *data["prior_generation_ids"], *previous.get("prior_generation_ids", []),
                previous["generation_id"],
            ]))
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
    pending = data.get("pending_call")
    if pending is not None:
        if pending["usage_id"] != row["usage_id"]:
            raise UsageLedgerError("cannot persist a different call while accounting is unresolved")
        # This removal and the completed counters are one atomic replacement.
        # If replacement fails, the prior ledger still carries the pending ID.
        data.pop("pending_call")
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
