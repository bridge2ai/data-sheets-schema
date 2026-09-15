"""Durable completed-call usage, independent of the final provenance (#656)."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import re
from pathlib import Path
import tempfile
import uuid

import yaml


class UsageLedgerError(OSError):
    """Past usage cannot be established; do not silently start more calls."""


@contextmanager
def exclusive_run(spec):
    """One writer for shared artifacts, across processes and run identities."""
    with exclusive_outputs((spec.full_path, spec.core_path,
                            spec.report_path, spec.provenance_path)):
        yield


@contextmanager
def exclusive_outputs(paths):
    """Use the API writer's locks when maintaining one or more output files."""
    # filelock is already a locked main dependency, including its Windows
    # implementation. Keep a stable sidecar: unlinking a held lock lets a
    # competing process lock a different inode at the same path.
    from filelock import FileLock, Timeout

    # Split and flat layouts can share a full/core record while storing their
    # metadata elsewhere. Lock the actual files, including resolved aliases,
    # in one order so partial overlap cannot bypass output ownership (#1298).
    outputs = {path.resolve() for path in paths}
    held = []
    try:
        for output in sorted(outputs):
            path = output.with_name(f".{output.name}_api_run.lock")
            path.parent.mkdir(parents=True, exist_ok=True)
            lock = FileLock(path, timeout=0)
            try:
                lock.acquire()
            except Timeout as exc:
                raise UsageLedgerError(f"an API run is already active for {output}; "
                                       "retry after it finishes") from exc
            held.append(lock)
        yield
    finally:
        for lock in reversed(held):
            lock.release()


def recovery_files(directory: Path, project: str) -> list[Path]:
    """API journals that generic provenance reconstruction cannot replace."""
    progress = directory / f"{project}_api_progress.json"
    found = [progress] if progress.exists() or progress.is_symlink() else []
    if directory.is_dir():
        pattern = re.compile(re.escape(project) + r"_api_usage_[0-9a-f]{16}\.json")
        found.extend(path for path in directory.iterdir() if pattern.fullmatch(path.name))
    return sorted(found)


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
            "accept_legacy": accept_legacy, "rows": [],
            "input_identity": spec.input_identity()}


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
    if "input_identity" in data and not isinstance(data["input_identity"], dict):
        raise UsageLedgerError(f"invalid API input identity: {path}")
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


def recorded_inputs(spec) -> dict | None:
    """Only persisted pins count as evidence for a legacy progress file."""
    return _read(spec).get("input_identity") if ledger_path(spec).is_file() else None


def pin_inputs(spec) -> None:
    """Bind a verified legacy continuation before it can make another call."""
    data = _read(spec)
    if data.get("input_identity") is None:
        data["input_identity"] = spec.input_identity()
        _write(spec, data)


def _comparable(identity: dict) -> dict:
    """An identity without `profile_basis` inside its instruction spec: the
    basis was never an input (#1626), and a pin written while it sat there
    (#1581–#1626) must not refuse a resume whose inputs are the same (#1657)."""
    if not isinstance(identity, dict):
        return {}
    out = dict(identity)
    instr = out.get("instruction")
    if isinstance(instr, dict) and isinstance(instr.get("spec"), dict) and "profile_basis" in instr["spec"]:
        out["instruction"] = {**instr, "spec": {k: v for k, v in instr["spec"].items() if k != "profile_basis"}}
    return out


def _subset_differs(pinned, current) -> bool:
    """Every key the pin carries must match, at every depth (#1677): a
    nested mapping is compared key by key, so a spec that gained a key
    after the pin was written is not a different spec."""
    if isinstance(pinned, dict) and isinstance(current, dict):
        return any(_subset_differs(v, current.get(k)) if k in current else True for k, v in pinned.items())
    return pinned != current


#: Evidence required for resume comparison: the bundle entry and the hash
#: of the instruction sent. The earliest identities carried no instruction
#: hash and cannot establish this comparison (#1698).
#: `bundle` is an entry (`{path, sha256}`) or null where the spec had no
#: bundle to hash; `instruction.sha256` is the hash itself.
_REQUIRED_IN_A_PIN = (("bundle",), ("instruction", "sha256"))


def _identity_differs(pinned: dict, current: dict) -> bool:
    """Compare the input evidence a pin can attest.

    Original file-entry fields and an instruction hash are required. Later
    optional keys, including an omitted legacy profile, remain compatible;
    present entries must be complete and every recorded value must match.
    The descriptive profile basis is excluded from identity (#1657).
    """
    if not isinstance(pinned, dict) or not isinstance(current, dict):
        return True
    for path in _REQUIRED_IN_A_PIN:
        # The keys must be there; a value recorded as null (a spec with no
        # bundle to hash) is a recorded fact and is compared as one.
        node = pinned
        for key in path[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
        if not isinstance(node, dict) or path[-1] not in node:
            return True
    # These file entries were all present in the original input identity
    # (#1402). None records an unused input; a mapping records both its
    # address and its observed hash, including an explicit missing-file null.
    # Dropping a hash is not the compatibility case of a newly added key.
    for name in ("bundle", "source_manifest", "chunks"):
        if name not in pinned:
            return True
        entry = pinned[name]
        if entry is not None and (not isinstance(entry, dict)
                                  or not {"path", "sha256"} <= entry.keys()):
            return True
    # Only omission of the whole profile has a historical meaning (#1460).
    # A partial profile cannot attest the instrument for a resumed phase.
    if "profile" in pinned:
        profile = pinned["profile"]
        if (not isinstance(profile, dict) or not profile.get("name")
                or not profile.get("digest_md5")):
            return True
    return _subset_differs(_comparable(pinned), _comparable(current))


def pre_profile_pin(pinned) -> bool:
    """A pin whose instruction predates the `--profile` line: its spec
    carries no `profile`, whether or not the pin's top level does (the
    #1460–#1581 window wrote the key beside an instruction that had not
    yet changed, #1712) — the case whose instruction cannot render again
    (#1628, #1677). A pin of any other shape is not one (#1701)."""
    if not isinstance(pinned, dict):
        return False
    instr = pinned.get("instruction")
    spec = instr.get("spec") if isinstance(instr, dict) else None
    import re
    digest = instr.get("sha256") if isinstance(instr, dict) else None
    return (isinstance(digest, str) and re.fullmatch(r"[0-9a-fA-F]{64}", digest) is not None
            and isinstance(spec, dict)
            and {"condition", "bundle", "render_version"} <= spec.keys()
            and "profile" not in spec)


def identity_refusal(pinned: dict, where: str) -> str:
    base = (f"generation input identity changed {where}; restore the recorded inputs or use "
            "--no-resume for an explicit new generation")
    if pre_profile_pin(pinned):
        base += (" (a generation pinned before the instruction carried its profile hashed an "
                 "instruction that no longer renders, and cannot be resumed; #1628, #1712)")
    return base


def require_resolved(spec) -> None:
    data = _read(spec)
    pending = data.get("pending_call")
    if pending is not None:
        raise UsageLedgerError(
            f"API call {pending['usage_id']} has unresolved accounting in {ledger_path(spec)}; "
            "restore its usage before resuming, or explicitly start fresh to archive this generation")

    pinned = data.get("input_identity")
    if pinned is not None and _identity_differs(pinned, spec.input_identity()):
        raise UsageLedgerError(identity_refusal(pinned, "(bundle, manifests or resolved instruction)"))
    _finish_reasoning_archive(spec, data)
    from data_sheets_schema.snapshot_store import finish_activation
    finish_activation(spec)


def begin_call(spec, phase: str, attempt: int, started_at: str) -> str:
    """Commit intent before a request so response persistence can fail safely."""
    require_resolved(spec)
    data = _read(spec)
    if data.get("evidence_refusal") is not None:
        raise UsageLedgerError("this generation has a terminal evidence refusal; no further calls are allowed")
    if phase == "report_regate":
        if report_regate_attempted(spec):
            raise UsageLedgerError("this generation already attempted its one report regeneration")
        # Admission consumes the allowance even if the response is truncated,
        # discarded, or the transport later fails (#1821).
        data["report_regate_attempted"] = True
    identifier = uuid.uuid4().hex
    data["pending_call"] = {"usage_id": identifier, "phase": phase,
                            "attempt": attempt, "started_at": started_at}
    _write(spec, data)
    return identifier


def report_regate_attempted(spec) -> bool:
    """Paid or admitted work exhausts the allowance, not retained output."""
    if not ledger_path(spec).exists():
        return False
    data = _read(spec)
    return (bool(data.get("report_regate_attempted"))
            or any(row.get("phase") == "report_regate" for row in data["rows"])
            or (data.get("pending_call") or {}).get("phase") == "report_regate")


def evidence_refusal(spec) -> dict | None:
    """A terminal refusal belongs to this ledger's current generation."""
    if not ledger_path(spec).exists():
        return None
    refusal = _read(spec).get("evidence_refusal")
    if refusal is not None and (not isinstance(refusal, dict)
            or refusal.get("stage") not in {"audit", "reconcile", "report"}
            or not isinstance(refusal.get("reading"), dict)):
        raise UsageLedgerError("invalid terminal evidence refusal; restore the generation ledger")
    return refusal


def record_evidence_refusal(spec, stage: str, reading: dict) -> None:
    """Atomically retain rejection independently of progress and final files."""
    if not ledger_path(spec).exists():
        raise UsageLedgerError("cannot record evidence refusal without the generation ledger")
    data = _read(spec)
    if data.get("evidence_refusal") is None:
        data["evidence_refusal"] = {"stage": stage, "reading": reading}
        _write(spec, data)


def cancel_call(spec, identifier: str) -> None:
    """Resolve a transport error that delivered no completed response."""
    data = _read(spec)
    if (data.get("pending_call") or {}).get("usage_id") != identifier:
        raise UsageLedgerError("cannot resolve a different pending API call")
    data.pop("pending_call")
    _write(spec, data)


def prepare_usage(spec, *, resume: bool) -> str:
    """Establish the generation boundary before any call can be made (#1291)."""
    if getattr(spec, "_replay_only", False):
        # A replay spec carries no instrument; it must not open or continue
        # a generation (#1568).
        raise UsageLedgerError("a replay spec cannot prepare a usage generation")
    path = ledger_path(spec)
    if resume and path.exists():
        require_resolved(spec)
        return _read(spec)["generation_id"]
    data = _empty(spec, accept_legacy=resume)
    if not resume:
        data["prior_generation_ids"] = _record_generations(spec)
        from data_sheets_schema.snapshot_store import predecessor_generation
        predecessor = predecessor_generation(spec)
        if predecessor is not None and predecessor not in data["prior_generation_ids"]:
            data["prior_generation_ids"].append(predecessor)
        from data_sheets_schema.snapshot_store import activation_intent
        data["pending_snapshot_activation"] = activation_intent(spec)
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
    if not resume:
        reasoning = spec.metadata_dir / f"{spec.project}_reasoning.jsonl"
        if reasoning.exists():
            data["pending_reasoning_archive"] = {
                "name": f"{spec.project}_reasoning.previous-{uuid.uuid4().hex}.jsonl",
                "sha256": hashlib.sha256(reasoning.read_bytes()).hexdigest(),
            }
    _write(spec, data)
    _finish_reasoning_archive(spec, data)
    return data["generation_id"]


def _finish_reasoning_archive(spec, data: dict) -> None:
    """Finish a recorded restart boundary without parsing predecessor bytes.

    The plan is durable before the rename. If a process dies after renaming,
    the next resume verifies the archive and completes the same plan.
    """
    pending = data.get("pending_reasoning_archive")
    if pending is None:
        return
    pattern = re.escape(f"{spec.project}_reasoning.previous-") + r"[a-f0-9]{32}\.jsonl"
    if (not isinstance(pending, dict)
            or not re.fullmatch(pattern, str(pending.get("name", "")))
            or Path(pending["name"]).name != pending["name"]
            or not re.fullmatch(r"[a-f0-9]{64}", str(pending.get("sha256", "")))):
        raise UsageLedgerError("invalid predecessor reasoning archive plan")
    source = spec.metadata_dir / f"{spec.project}_reasoning.jsonl"
    archive = source.with_name(pending["name"])
    try:
        if source.exists():
            if hashlib.sha256(source.read_bytes()).hexdigest() != pending["sha256"]:
                raise UsageLedgerError("predecessor reasoning changed during archive initialization")
            if archive.exists():
                raise UsageLedgerError("reasoning archive target already exists while the source remains")
            os.replace(source, archive)
        if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != pending["sha256"]:
            raise UsageLedgerError("predecessor reasoning archive is missing or its bytes changed")
        data.setdefault("reasoning_archives", []).append(dict(pending))
        data.pop("pending_reasoning_archive")
        _write(spec, data)
    except OSError as exc:
        raise UsageLedgerError(f"cannot establish reasoning generation boundary: {exc}") from exc


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


def require_matching_usage(spec, usage: list[dict], *, complete: bool = False) -> None:
    """A stable ID never excuses contradictory surviving call counters."""
    recorded = {row.get("usage_id"): row for row in usage if isinstance(row, dict)}
    for row in _read(spec)["rows"]:
        previous = recorded.get(row["usage_id"])
        if (previous is None and complete) or (
                previous is not None and any(previous.get(key) != value for key, value in row.items())):
            raise UsageLedgerError("billed attempt accounting is absent from or conflicts with the record; "
                                   "restore its progress and accounting before resuming")
