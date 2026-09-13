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


def _load(directory: Path, project: str, *, path: Path | None = None,
          check_account: bool = True) -> dict | None:
    path = path or index_path(directory, project)
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
        if check_account and account.is_file():
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


def predecessor_generation(spec) -> str | None:
    """The current index explicitly superseded by a fresh run.

    Its own identity survives a missing or malformed usage journal. Only this
    index is selected; unrelated archives are not accepted as predecessors.
    """
    try:
        data = _load(spec.metadata_dir, spec.project, check_account=False)
    except ledger.UsageLedgerError:
        return None  # a fresh activation preserves opaque old bytes separately
    if data is not None and data["run_identity"] == ledger.run_identity(spec):
        return data["generation_id"]
    return None


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


def _read_verified(entry: dict) -> tuple[Path, bytes]:
    if (not isinstance(entry.get("path"), str) or not entry["path"]
            or not re.fullmatch(r"[a-f0-9]{64}", str(entry.get("sha256", "")))):
        raise ledger.UsageLedgerError("invalid portable snapshot byte attestation")
    path = Path(entry["path"])
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ledger.UsageLedgerError(f"generation snapshot bytes changed or are missing: {path}; restore its evidence") from exc
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ledger.UsageLedgerError(f"generation snapshot bytes changed or are missing: {path}; restore its evidence")
    return path, raw


def _verified(entry: dict) -> Path:
    return _read_verified(entry)[0]


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
        run = prior_record.get("run") or {}
        if run.get("generation_id") == generation and "intermediates" in prior_record:
            expected = []
            for entry in prior_record["intermediates"]:
                if entry.get("generation_id") != generation or not entry.get("phase"):
                    raise ledger.UsageLedgerError("saved phase history has ambiguous snapshot ownership")
                _verified(entry)
                expected.append({"name": entry["phase"], "path": entry["path"], "sha256": entry["sha256"],
                                 **({"usage_id": entry["usage_id"]} if entry.get("usage_id") else {})})
            current = existing["snapshots"]
            common = min(len(current), len(expected))
            if current[:common] != expected[:common]:
                raise ledger.UsageLedgerError("snapshot index diverges from the saved phase history; restore its evidence")
            if len(current) < len(expected):
                # The saved progress/portable record proves the missing suffix.
                # Restore only those verified entries; never directory guesses.
                existing["snapshots"] = expected
                _write(path, existing)
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
        if run.get("prior_generation_ids") and not run.get("generation_id"):
            raise ledger.UsageLedgerError("legacy snapshots have multiple generations; use --no-resume to regenerate")
        selected = {}
        for phase in ("full", "core"):
            name = f"{spec.project}_{phase}.yaml"
            entry = _portable_entry(prior_record, spec.project, name)
            if entry is not None:
                selected[entry["path"]] = name
        if not selected:
            raise ledger.UsageLedgerError("saved phases have no generation snapshot evidence; restore it or use --no-resume")
        # Keep the complete portable history in its attested order. Placing
        # the selected phase before older copies would make those current.
        for entry in prior_record.get("intermediates") or []:
            if not isinstance(entry, dict):
                raise ledger.UsageLedgerError("invalid portable snapshot evidence")
            if entry.get("generation_id") not in (None, run.get("generation_id")):
                raise ledger.UsageLedgerError("portable snapshot belongs to a different generation")
            _verified(entry)
            entries.append({"name": entry.get("phase") or selected.get(entry["path"]) or Path(entry["path"]).name,
                            "path": entry["path"], "sha256": entry["sha256"],
                            **({"usage_id": entry["usage_id"]} if entry.get("usage_id") else {})})
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


def _portable(directory: Path, project: str, record: dict | None, spec=None) -> dict | None:
    """The caller's record is authoritative; a neighboring index is not."""
    if record is None:
        path = directory / f"{project}_provenance.yaml"
        if not path.exists():
            return None
        import yaml
        try:
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, yaml.YAMLError) as exc:
            raise ledger.UsageLedgerError(f"cannot read snapshot owner record: {path}: {exc}") from exc
    run = record.get("run") if isinstance(record, dict) else None
    if (not isinstance(run, dict) or run.get("project") != project
            or (spec is not None and not ledger.record_matches(spec, run))):
        raise ledger.UsageLedgerError("snapshot owner record does not match the requested run")
    return record


def _portable_entry(record: dict, project: str, name: str) -> dict | None:
    run = record.get("run") or {}
    candidates = []
    pattern = re.compile(re.escape(Path(name).stem) + r"(?:_[0-9]+)?" + re.escape(Path(name).suffix))
    for entry in record.get("intermediates") or []:
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        phase = entry.get("phase")
        if (phase == name or (phase is None and pattern.fullmatch(Path(entry["path"]).name))):
            if not re.fullmatch(r"[a-f0-9]{64}", str(entry.get("sha256", ""))):
                raise ledger.UsageLedgerError("portable phase snapshot has no valid byte attestation")
            if entry.get("generation_id") not in (None, run.get("generation_id")):
                raise ledger.UsageLedgerError("portable phase snapshot belongs to a different generation")
            candidates.append(entry)
    # Earlier report instruments recorded their selected phase input before
    # generation UUIDs existed. That exact path/hash can disambiguate a legacy
    # inventory without guessing from directory order (#1418).
    if not run.get("generation_id") and name == f"{project}_full.yaml":
        pin = ((record.get("report_claims") or {}).get("artifacts") or {}).get("phase1_snapshot")
        if isinstance(pin, dict) and pin.get("path") and pin.get("sha256"):
            selected = [entry for entry in candidates
                        if entry["path"] == pin["path"] and entry["sha256"] == pin["sha256"]]
            if len(selected) != 1:
                raise ledger.UsageLedgerError("recorded phase snapshot pin does not match its portable inventory")
            return selected[0]
    if len(candidates) > 1 and any(e.get("phase") is None or not e.get("generation_id") for e in candidates):
        raise ledger.UsageLedgerError("portable phase snapshots have ambiguous generation ownership; restore their index")
    return candidates[-1] if candidates else None


def read_latest(directory: Path, project: str, name: str, *, spec=None,
                record: dict | None = None) -> tuple[bool, tuple[Path, bytes] | None]:
    """Read once under an expected live identity or portable byte attestation.

    The boolean distinguishes identified evidence from older unregistered
    helpers. A modern record without an index never falls back to filenames.
    """
    generation = ledger.generation_id(spec) if spec is not None else None
    if generation is not None:
        expected_inputs = ledger.recorded_inputs(spec)
        if expected_inputs is not None and expected_inputs != spec.input_identity():
            raise ledger.UsageLedgerError("snapshot input identity differs from the active generation")
    if record is not None and "intermediates" in record:
        # A caller checking a completed record supplies its exact attestation.
        # Its phase history outranks a restored index with the same UUID.
        portable = _portable(directory, project, record, spec)
        if generation is not None and portable["run"].get("generation_id") not in (None, generation):
            raise ledger.UsageLedgerError("completed snapshot record belongs to another generation")
        entry = _portable_entry(portable, project, name)
        if entry is None and portable["run"].get("generation_id"):
            raise ledger.UsageLedgerError("identified run has no attested phase snapshot; restore its evidence")
        return True, _read_verified(entry) if entry is not None else None
    if generation is not None:
        data = _load(directory, project)
        if (data is not None and not data.get("superseded")
                and data["generation_id"] == generation
                and data["run_identity"] == ledger.run_identity(spec)
                and data["input_identity"] == spec.input_identity()):
            entry = next((e for e in reversed(data["snapshots"]) if e["name"] == name), None)
            return True, _read_verified(entry) if entry is not None else None
        # Portable evidence may recover a missing/stale index, but cannot
        # replace a new active generation with a previous completed one.
        portable = _portable(directory, project, record, spec)
        if portable is None or portable["run"].get("generation_id") != generation:
            raise ledger.UsageLedgerError("snapshot index does not match the active run and input identity")
    else:
        portable = _portable(directory, project, record, spec)
    if portable is not None and (portable["run"].get("generation_id") or "intermediates" in portable):
        entry = _portable_entry(portable, project, name)
        if entry is None and portable["run"].get("generation_id"):
            raise ledger.UsageLedgerError("identified run has no attested phase snapshot; restore its evidence")
        return True, _read_verified(entry) if entry is not None else None
    if index_path(directory, project).exists() or any(
            index_path(directory, project).parent.glob(f"{project}_snapshot_index.previous-*.json")):
        raise ledger.UsageLedgerError("generation snapshots require a matching run record or active identity")
    return False, None  # historical helpers predate generation-bound snapshots


def latest(directory: Path, project: str, name: str, *, spec=None,
           record: dict | None = None) -> tuple[bool, Path | None]:
    indexed, snapshot = read_latest(directory, project, name, spec=spec, record=record)
    return indexed, snapshot[0] if snapshot is not None else None


def require_accounted(spec, prior_record: dict) -> None:
    """Do not let a completed record hide a later delivered attempt (#1416)."""
    generation = ledger.generation_id(spec)
    run = prior_record.get("run") or {}
    known = set(ledger.prior_generation_ids(spec) if generation else run.get("prior_generation_ids") or [])
    expected = generation or run.get("generation_id")
    rows = ledger.merge_usage(spec, list(prior_record.get("api_usage") or [])) if generation else prior_record.get("api_usage") or []
    accounted = {row.get("usage_id") for row in rows if isinstance(row, dict)}
    path = index_path(spec.metadata_dir, spec.project)
    paths = [path, *sorted(path.parent.glob(f"{spec.project}_snapshot_index.previous-*.json"))]
    for candidate in paths:
        try:
            data = _load(spec.metadata_dir, spec.project, path=candidate)
        except ledger.UsageLedgerError:
            if candidate == path:
                raise
            continue  # an explicit restart may preserve an opaque old index
        if data is None or data["run_identity"] != ledger.run_identity(spec):
            continue
        if data["generation_id"] in known:
            continue  # a recorded explicit restart preserves this predecessor
        if data["generation_id"] != expected or any(
                e.get("usage_id") is not None and e["usage_id"] not in accounted for e in data["snapshots"]):
            raise ledger.UsageLedgerError("generation snapshot evidence includes an unaccounted attempt; "
                                           "restore its usage ledger before resuming")



def require_completed_accounted(spec, record: dict) -> None:
    """A completed return must include every surviving call of this generation."""
    if ledger.generation_id(spec) is None:
        return
    ledger.require_matching_usage(spec, record.get("api_usage") or [], complete=True)


def entries(spec) -> list[dict] | None:
    data = _load(spec.provenance_path.parent, spec.project)
    if data is None:
        return None
    if data["generation_id"] != ledger.generation_id(spec) or data["run_identity"] != ledger.run_identity(spec):
        raise ledger.UsageLedgerError("cannot publish another generation's snapshots")
    for entry in data["snapshots"]:
        _verified(entry)
    return [{"path": entry["path"], "sha256": entry["sha256"], "phase": entry["name"],
             "generation_id": data["generation_id"],
             **({"usage_id": entry["usage_id"]} if entry.get("usage_id") else {})}
            for entry in data["snapshots"]]
