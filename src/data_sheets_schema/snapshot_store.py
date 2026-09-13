"""Generation-bound phase evidence, with historical files kept intact (#1409)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from data_sheets_schema import usage_ledger as ledger


def index_path(directory: Path, project: str) -> Path:
    return directory / "intermediate" / f"{project}_snapshot_index.json"


def _load(directory: Path, project: str) -> dict | None:
    path = index_path(directory, project)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or data.get("version") != 1
                or not isinstance(data.get("generation_id"), str)
                or not data["generation_id"]
                or not isinstance(data.get("run_identity"), dict)
                or data["run_identity"].get("project") != project
                or not isinstance(data.get("input_identity"), dict)
                or not isinstance(data.get("snapshots"), list)):
            raise ValueError("invalid snapshot index identity")
        key = hashlib.sha256(json.dumps(data["run_identity"], sort_keys=True).encode()).hexdigest()[:16]
        account = directory / f"{project}_api_usage_{key}.json"
        if account.is_file():
            owner = json.loads(account.read_text(encoding="utf-8"))
            if not isinstance(owner, dict):
                raise ValueError("invalid snapshot owner ledger")
            if (owner.get("generation_id") != data["generation_id"]
                    or owner.get("identity") != data["run_identity"]
                    or (owner.get("input_identity") is not None
                        and owner["input_identity"] != data["input_identity"])):
                # A writer that is opening a fresh generation must archive
                # the old index first; readers must not treat it as current.
                data["superseded"] = True
        for entry in data["snapshots"]:
            if (not isinstance(entry, dict)
                    or any(not isinstance(entry.get(key), str) or not entry[key]
                           for key in ("name", "path", "sha256"))
                    or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])):
                raise ValueError("invalid snapshot entry")
        return data
    except (OSError, ValueError) as exc:
        raise ledger.UsageLedgerError(f"cannot recover generation snapshots from {path}: {exc}") from exc


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.stem}.", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _verified(entry: dict) -> Path:
    path = Path(entry["path"])
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise ledger.UsageLedgerError(f"generation snapshot bytes changed or are missing: {path}; restore its evidence")
    return path


def activate(spec, *, fresh: bool, completed: bool, prior_record: dict) -> None:
    """Establish the snapshot owner before reading or writing any phase."""
    directory = spec.provenance_path.parent
    path = index_path(directory, spec.project)
    try:
        existing = _load(directory, spec.project)
    except ledger.UsageLedgerError:
        if not fresh:
            raise
        existing = {"unreadable": True}  # explicit restart archives the opaque bytes
    identity = ledger.run_identity(spec)
    generation = ledger.generation_id(spec)
    if existing is not None and existing.get("generation_id") == generation:
        if existing["run_identity"] != identity or existing["input_identity"] != spec.input_identity():
            raise ledger.UsageLedgerError("generation snapshot identity disagrees with the active run")
        return
    if existing is not None and existing.get("generation_id") in ledger.prior_generation_ids(spec):
        fresh = True  # an explicit restart already recorded this predecessor
    if existing is not None and not fresh:
        raise ledger.UsageLedgerError("generation snapshot index belongs to a different generation; restore its evidence")
    entries = []
    if completed and not fresh:
        # Legacy progress can adopt only hash-attested phase evidence from
        # its matched portable record, never a directory's numbered files.
        run = prior_record.get("run") or {}
        if run.get("prior_generation_ids"):
            raise ledger.UsageLedgerError("legacy snapshots have multiple generations; use --no-resume to regenerate")
        pattern = re.compile(re.escape(spec.project) + r"_(full|core)(?:_[0-9]+)?\.yaml")
        for entry in prior_record.get("intermediates") or []:
            if not isinstance(entry, dict) or not entry.get("path") or not entry.get("sha256"):
                continue
            match = pattern.fullmatch(Path(entry["path"]).name)
            if match:
                _verified(entry)
                entries.append({"name": f"{spec.project}_{match[1]}.yaml",
                                "path": entry["path"], "sha256": entry["sha256"]})
        entries.sort(key=lambda entry: int(re.search(r"_([0-9]+)\.yaml$", entry["path"])[1])
                     if re.search(r"_([0-9]+)\.yaml$", entry["path"]) else 1)
        if not entries:
            raise ledger.UsageLedgerError("saved phases have no generation snapshot evidence; restore it or use --no-resume")
    data = {"version": 1, "generation_id": generation, "run_identity": identity,
            "input_identity": ledger.recorded_inputs(spec) or spec.input_identity(), "snapshots": entries}
    if existing is not None:
        archive = path.with_name(f"{path.stem}.previous-{uuid.uuid4().hex}.json")
        with archive.open("xb") as stream:
            stream.write(path.read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
    _write(path, data)


def record(spec, name: str, path: Path, *, usage_id: str | None = None) -> None:
    """Register delivered evidence even when its inputs changed mid-call."""
    if ledger.generation_id(spec) is None:
        return  # standalone historical helpers have no active generation
    directory = spec.provenance_path.parent
    data = _load(directory, spec.project)
    replaced = (data is not None and data["generation_id"] != ledger.generation_id(spec)
                and data["generation_id"] in ledger.prior_generation_ids(spec))
    if data is None or replaced:
        # Standalone recovery helpers may follow prepare_usage directly. The
        # ledger's explicit archived-generation history authorizes replacement.
        activate(spec, fresh=replaced, completed=False, prior_record={})
        data = _load(directory, spec.project)
    if data["generation_id"] != ledger.generation_id(spec) or data["run_identity"] != ledger.run_identity(spec):
        raise ledger.UsageLedgerError("cannot attach a snapshot to another generation")
    entry = {"name": name, "path": str(path),
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if usage_id is not None:
        entry["usage_id"] = usage_id
    data["snapshots"].append(entry)
    _write(index_path(directory, spec.project), data)


def latest(directory: Path, project: str, name: str) -> tuple[bool, Path | None]:
    """Whether an index exists, and its last verified snapshot for this phase."""
    data = _load(directory, project)
    if data is None:
        return False, None
    if data.get("superseded"):
        raise ledger.UsageLedgerError("snapshot index is not the active generation; restore its evidence")
    entry = next((e for e in reversed(data["snapshots"]) if e["name"] == name), None)
    return True, _verified(entry) if entry is not None else None


def entries(spec) -> list[dict] | None:
    data = _load(spec.provenance_path.parent, spec.project)
    if data is None:
        return None
    if data["generation_id"] != ledger.generation_id(spec) or data["run_identity"] != ledger.run_identity(spec):
        raise ledger.UsageLedgerError("cannot publish another generation's snapshots")
    for entry in data["snapshots"]:
        _verified(entry)
    return [{"path": entry["path"], "sha256": entry["sha256"]} for entry in data["snapshots"]]
