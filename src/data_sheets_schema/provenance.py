"""Provenance records for D4D generation runs.

Every generation run should leave a machine-readable record of what produced it:
the schema it was built against, the model that wrote it, the exact input bytes,
the software and hardware, and the validation results.

Two modes, and the distinction is load-bearing:

- ``live`` — written as part of the generation run. Every field is observed.
- ``reconstructed`` — derived afterwards from artefacts on disk. Some fields are
  recoverable (model, from the record header), some are not (the byte state of
  an input bundle that has since been regenerated).

A reconstructed record **must not** present a present-day observation as if it
were the run's own. The input bundles were refreshed on 2026-07-24 and
2026-07-27; hashing them today and recording that against an April run would be
a fabricated provenance claim. Such fields are listed under ``unrecoverable``
with the reason, never silently filled.
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

RECORD_VERSION = 1
CONCAT_DIR = Path("data/d4d_concatenated")
FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
CORE_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")
SOURCE_MANIFEST = Path("data/preprocessed/source_manifest.yaml")
SOURCE_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema.yaml")

# The GitHub D4D assistant already centralises model settings here, and hashes
# its prompts. Both generation paths read this file rather than each declaring
# its own model and temperature, so the two cannot drift into being different
# procedures that claim to be the same one.
DETERMINISTIC_CONFIG = Path(".github/workflows/d4d_assistant_deterministic.config")

# The assistant hashes with SHA-256; the 33 run records written before this
# module existed use md5 for input bundles. Rather than silently mixing them,
# each hash field names its algorithm: prompts (new) use sha256, input bundles
# keep md5 so existing records stay comparable. Unifying on sha256 means
# rewriting those records and is deliberately left as a separate decision.
# One algorithm. The record format previously used sha256 for prompts and md5
# for inputs, artifacts and schemas — deliberate at the time (the GitHub
# assistant used sha256; 33 existing records used md5) but historical rather than
# principled, and md5 is not a defensible integrity hash in 2026.
#
# Switching the writer alone would have been a silent corpus-wide regression: 82
# of 89 records carry md5-bound validation verdicts, and `validation_status`
# re-hashes to detect staleness, so every one would have reported STALE. Readers
# are therefore algorithm-agnostic — they verify with whichever hash the record
# carries — and existing records are migrated only after their recorded md5 is
# confirmed to still match, which proves the bytes are the ones it described.
HASH_ALGORITHM = "sha256"
PROMPT_HASH = "sha256"
INPUT_HASH = "md5"

# Header fields carrying model/runtime identity.
HEADER_FIELDS = ("Generation Method", "Agent runtime", "Provider", "Model",
                 "Reasoning effort", "Mode", "Temperature", "Generated",
                 "Source bundle", "Source", "Source manifest", "Schema",
                 "Prior D4D factual reuse", "Arm")


def _md5(path: Path) -> str | None:
    if not path or not path.exists():
        return None
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256(path: Path) -> str | None:
    if not path or not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_generation_config(path: Path = DETERMINISTIC_CONFIG) -> dict[str, Any]:
    """Model settings shared with the GitHub assistant.

    Returning the file's own values rather than defaults matters: if the two
    paths disagree about the model or temperature they are different
    procedures, and the fingerprint should say so rather than paper over it.
    """
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def prompt_facts(prompt_paths: list[Path] | None) -> dict[str, Any]:
    """Hash every prompt file a run consumed.

    The prompt is a generation input as much as the bundle is, and until now it
    was the one input this record did not name. A condition whose prompt cannot
    be identified cannot be replicated — which is exactly why the 2026-07-27
    tuned prompts, written inline and never saved, are unreproducible.
    """
    if not prompt_paths:
        return {"paths": None,
                "note": ("no prompt files declared; the prompt was supplied "
                         "inline and is not recoverable from this record")}
    out = []
    for p in prompt_paths:
        p = Path(p)
        out.append({"path": str(p), "sha256": _sha256(p),
                    "bytes": p.stat().st_size if p.exists() else None,
                    "exists": p.exists()})
    return {"hash_algorithm": PROMPT_HASH, "files": out}


def _run(cmd: list[str]) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or None
    except Exception:
        return None


def parse_header(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith("#"):
            break
        key, _, value = line.lstrip("#").strip().partition(":")
        if key.strip() in HEADER_FIELDS:
            out[key.strip()] = value.strip()
    return out


def system_facts() -> dict[str, Any]:
    """Hardware and OS. Observed at call time — meaningful only for live records."""
    facts: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count": os.cpu_count(),
        "python": sys.version.split()[0],
    }
    if sys.platform == "darwin":
        brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        mem = _run(["sysctl", "-n", "hw.memsize"])
        facts["cpu_brand"] = brand
        facts["memory_bytes"] = int(mem) if mem and mem.isdigit() else None
    return facts


def software_facts() -> dict[str, Any]:
    import importlib.metadata as md

    def ver(pkg: str) -> str | None:
        try:
            return md.version(pkg)
        except Exception:
            return None

    return {
        "data_sheets_schema": ver("data-sheets-schema"),
        "linkml": ver("linkml"),
        "linkml_runtime": ver("linkml-runtime"),
        "python": sys.version.split()[0],
    }


def repo_facts() -> dict[str, Any]:
    dirty = _run(["git", "status", "--porcelain"])
    return {
        "commit": _run(["git", "rev-parse", "HEAD"]),
        "commit_short": _run(["git", "rev-parse", "--short", "HEAD"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(dirty),
        "dirty_file_count": len(dirty.splitlines()) if dirty else 0,
    }


def declared_schema_version() -> str | None:
    """The `version:` declared in the source schema, if any.

    Read from the source (`data_sheets_schema.yaml`) rather than the merged
    artefacts, because the merged files are generated and only pick the field
    up on the next regeneration. The version applies to both, since both derive
    from this source.
    """
    if not SOURCE_SCHEMA.exists():
        return None
    for line in SOURCE_SCHEMA.read_text(encoding="utf-8").splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip() or None
        if line and not line.startswith((" ", "-", "#")) and ":" in line:
            continue
    return None


def schema_facts() -> dict[str, Any]:
    """Schema identity: declared version plus content hashes of what was used."""
    version = declared_schema_version()
    merged_carries_version = False
    if FULL_SCHEMA.exists():
        head = FULL_SCHEMA.read_text(encoding="utf-8", errors="ignore")[:4000]
        merged_carries_version = any(
            l.startswith("version:") for l in head.splitlines())
    facts: dict[str, Any] = {
        "declared_version": version,
        "declared_in": str(SOURCE_SCHEMA),
        "full_path": str(FULL_SCHEMA),
        "full_sha256": _sha256(FULL_SCHEMA),
        "core_path": str(CORE_SCHEMA),
        "core_sha256": _sha256(CORE_SCHEMA),
        "merged_schema_carries_version": merged_carries_version,
    }
    if version and not merged_carries_version:
        facts["note"] = (
            "The version is declared in the source schema but the merged "
            "artefacts predate it; they will carry it after the next "
            "`make full-schema`. Content md5s identify exactly what was used.")
    elif not version:
        facts["note"] = (
            "No version declared; identity rests on content md5 plus commit.")
    return facts


def _slot_count(path: Path) -> int | None:
    try:
        return len(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except Exception:
        return None


def _artifact(path: Path) -> dict[str, Any] | None:
    """Describe an artifact without asserting its integrity.

    No hash, deliberately. A hash is a *claim*, and this one was made at the
    wrong moment: the agent path recorded provenance as a separate step from
    writing the artifacts, so 77 live records hashed a state their files merely
    passed through — one reconciliation report was hashed before its closing
    rows were appended, and the `-deprimed` series was hashed before its headers
    were relabelled. Nothing verified the claim, so it stayed wrong.

    Integrity now lives in exactly one place: `validation.artifacts`, written by
    `d4d runs validate` *after* the run, and re-checked by `validation_status`.
    Hashing after the artifacts are final removes the race rather than
    detecting it.

    `bytes` and `slots` remain. They describe rather than assert, and a
    description that drifts is a stale note, not a false guarantee.
    """
    if not path.exists():
        return None
    return {"path": str(path), "bytes": path.stat().st_size,
            "slots": _slot_count(path) if path.suffix == ".yaml" else None}


def _hashed_artifact(path: Path) -> dict[str, Any] | None:
    """Describe an artifact *and* pin it. Only for use after a run is complete."""
    art = _artifact(path)
    if art is None:
        return None
    return {**art, "sha256": _sha256(path)}


def recorded_hash(entry: dict[str, Any]) -> tuple[str, str] | None:
    """The (algorithm, value) an entry actually carries.

    sha256 preferred, md5 accepted. A record written before the unification is
    still verifiable on its own terms — refusing to read md5 would turn every
    historical verdict into an unverifiable one, which is the opposite of what
    hashing them was for.
    """
    for algo in ("sha256", "md5"):
        if entry.get(algo):
            return algo, entry[algo]
    return None


def hash_file(path: Path, algorithm: str = HASH_ALGORITHM) -> str | None:
    return _sha256(path) if algorithm == "sha256" else _md5(path)


def verify_entry(entry: dict[str, Any]) -> bool | None:
    """Does the file still hash to what the entry recorded? None if unknowable."""
    got = recorded_hash(entry)
    path = entry.get("path")
    if not got or not path or not Path(path).exists():
        return None
    algo, value = got
    return hash_file(Path(path), algo) == value


def preservable_validation(path: Path,
                           new_data: dict[str, Any]) -> dict[str, Any] | None:
    """A prior `validation:` block that a re-record may keep, or None.

    `record` rewrites the file from scratch while `d4d runs validate` writes the
    verdict separately, so re-recording used to delete it and the run failed
    `--strict` immediately with "nothing to verify" — while `record` printed a
    tick and exited 0 (#396). Re-recording is the *correct* response to several
    situations (a header field was added, Phase 3 corrected an artifact), so
    this was easy to hit and looked like success.

    A verdict is a claim about specific bytes, and it is still true if those
    bytes have not changed. So the block is carried forward only when every
    artifact it names still hashes to what it recorded. If any differs, or any
    is missing, the verdict is about a file that no longer exists in that form
    and is dropped — the same staleness rule `validation_status` applies.

    **The schema must also be unchanged.** "Validates" is a claim about a
    record *against a schema*, and `validation.artifacts` pins only the record.
    `validation_status` has the same blind spot, but there it is bounded:
    before this function existed, a re-record dropped the verdict and forced a
    re-validation. Carrying it forward would let a verdict outlive the schema
    it was reached against, so the record's own `schema` block is compared too
    and any difference drops it. Raised in review of #396; the gap is #426.

    Returns None when there is nothing to carry, when the caller supplied its
    own block, when the prior one no longer describes the artifacts, or when
    the schema has moved under it.
    """
    if "validation" in new_data:
        return None                      # caller's own verdict wins
    if not path.exists():
        return None
    try:
        prior = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:                                        # noqa: BLE001
        return None
    if not isinstance(prior, dict):
        return None
    v = prior.get("validation")
    if not isinstance(v, dict) or "passed" not in v:
        return None
    artifacts = v.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        # A verdict with nothing to re-hash cannot be shown still true.
        return None
    for entry in artifacts.values():
        if not isinstance(entry, dict) or verify_entry(entry) is not True:
            return None

    # Same record, same bytes, different schema is a different question.
    def _schema_id(d: dict[str, Any]) -> tuple[Any, Any]:
        sch = d.get("schema") or {}
        return (sch.get("full_sha256"), sch.get("core_sha256"))

    if _schema_id(prior) != _schema_id(new_data):
        return None
    return v


@dataclass
class ProvenanceRecord:
    data: dict[str, Any] = field(default_factory=dict)

    #: Set by :meth:`write`. True if a prior verdict was carried forward, False
    #: if one was found but dropped as stale, None if there was none. The CLI
    #: reads it to say which happened, because a silently dropped verdict is
    #: what made #396 hard to notice.
    validation_carried: bool | None = None

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(self.data)
        had_prior = False
        if "validation" not in data and path.exists():
            try:
                prior = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                had_prior = isinstance(prior, dict) and isinstance(
                    prior.get("validation"), dict)
            except Exception:                                # noqa: BLE001
                had_prior = False
        carried = preservable_validation(path, data)
        if carried is not None:
            data["validation"] = carried
            self.validation_carried = True
        elif had_prior:
            self.validation_carried = False
        path.write_text(
            "# D4D generation provenance record\n"
            f"# record_version {RECORD_VERSION} — see src/data_sheets_schema/provenance.py\n"
            + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8")
        return path


@dataclass
class Contribution:
    """One generated record that a derived record consumed.

    The hash is the point. A derived record that merely names its sources is not
    reproducible: the sources are themselves stochastic outputs that can be
    regenerated under the same label with different content. Pinning the bytes is
    what makes "this came from those" checkable rather than asserted.
    """

    label: str
    project: str
    method: str
    path: str
    sha256: str
    slots: int | None = None
    contributed_slots: int | None = None   # how many slots this source supplied


def contribution(path: Path, *, label: str, project: str, method: str,
                 contributed_slots: int | None = None) -> Contribution:
    # Hashed: a contributing record must be pinned, or "this came from those"
    # is an assertion rather than something checkable.
    art = _hashed_artifact(path)
    if art is None:
        raise FileNotFoundError(f"contributing record does not exist: {path}")
    return Contribution(label=label, project=project, method=method,
                        path=art["path"], sha256=art["sha256"],
                        slots=art["slots"],
                        contributed_slots=contributed_slots)


def _arm_of_sources(sources: list["Contribution"]) -> str:
    arms = {_arm_for(c.method) for c in sources}
    if len(arms) == 1:
        return arms.pop()
    # A merge across arms is a different object from a merge within one, and
    # flattening that to a single name would hide it.
    return "mixed: " + ", ".join(sorted(arms))


def build_derived_record(project: str, method: str, label: str, *,
                         sources: list[Contribution],
                         derivation: str,
                         outputs: dict[str, Path],
                         concat_dir: Path = CONCAT_DIR,
                         extra_notes: list[str] | None = None
                         ) -> ProvenanceRecord:
    """Provenance for a record built from other generated records.

    A fourth mode alongside `live` and `reconstructed`, rather than a flag on
    either. A merged record did not observe a generation and is not a recovered
    account of one — no model produced it, no bundle was read, no prompt was
    sent. Recording it as `live` would assert a generation that never happened;
    recording it as `reconstructed` would imply an original run to recover.

    So the model, prompt and input-bundle fields are absent by construction, and
    what takes their place is the source list: every contributing record pinned
    by md5, plus a statement of the rule that combined them. That is the whole
    factual content of a derived record, and it is checkable — re-running the
    same rule over the same bytes must reproduce it.

    This is what blocked merged records from shipping: `provenance.py` could not
    express "consumed other generated records", and claiming any existing mode
    would have been a false statement about how the artifact came to exist.
    """
    if not sources:
        raise ValueError(
            "a derived record must name its sources; a merge whose inputs are "
            "unrecorded cannot be reproduced or audited")

    # An absent output is fatal here, unlike in a generation record where a
    # phase may legitimately not have produced a report. The output is the whole
    # reason a derived record exists: one whose artifact is missing describes
    # nothing, yet would still be discovered and counted as provenance.
    missing = [k for k, v in outputs.items() if not Path(v).exists()]
    if missing or not outputs:
        raise FileNotFoundError(
            "a derived record must describe an artifact that exists; missing: "
            + (", ".join(f"{k}={outputs[k]}" for k in missing) or "(no outputs given)"))

    data: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "record_type": "d4d_derived_provenance",
        "record_mode": "derived",
        "record_generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # The arm comes from the sources, not from the derived method: a merge
        # of baseline records is still about the baseline arm, and asking
        # `_arm_for` about a merged method only yields "unknown".
        "run": {"label": label, "project": project, "method": method,
                "arm": _arm_of_sources(sources),
                "replicate": None},
        # Stated, not implied. A reader must not have to infer from the absence
        # of a model field that no model was involved.
        "derivation": {
            "rule": derivation,
            "source_count": len(sources),
            "reproducible": ("re-running this rule over the pinned source bytes "
                             "must reproduce this record"),
        },
        "sources": [asdict(c) for c in sources],
        "schema": schema_facts(),
        "software": software_facts(),
        "repo": repo_facts(),
        # Hashed here, unlike a generation record: a derived record has no
        # validation block, its output is written and hashed in one step, and
        # the whole point of the record is to pin what came from what.
        "outputs": {k: _hashed_artifact(v) for k, v in outputs.items()},
        "not_applicable": [
            {"field": "model",
             "reason": "no model produced this record; it combines existing ones"},
            {"field": "prompts",
             "reason": "no prompt was sent"},
            {"field": "inputs.bundle_md5",
             "reason": "no source bundle was read; the inputs are the records "
                       "listed under `sources`"},
        ],
        "notes": list(extra_notes or []) or None,
    }
    return ProvenanceRecord(data=data)


def build_record(project: str, method: str, label: str, *, mode: str,
                 input_bundle: Path | None = None,
                 input_verified: bool = False,
                 concat_dir: Path = CONCAT_DIR,
                 prompt_paths: list[Path] | None = None,
                 schema_digest_md5: str | None = None,
                 extra_notes: list[str] | None = None) -> ProvenanceRecord:
    """Assemble a provenance record for one project-run.

    ``mode`` is ``live`` or ``reconstructed``. ``input_verified`` must be True
    only when the input bundle on disk is known to be the same bytes the run
    consumed; otherwise the input hash is withheld as unrecoverable.
    """
    base = method[:-5] if method.endswith("_core") else method
    full = concat_dir / base / label / f"{project}_d4d.yaml"
    core = concat_dir / f"{base}_core" / label / f"{project}_d4d_core.yaml"
    report = concat_dir / f"{base}_core" / label / f"{project}_reconciliation.md"

    header = parse_header(full)
    unrecoverable: list[dict[str, str]] = []
    # Distinct from unrecoverable: these fields ARE populated, but the value is
    # asserted rather than observed. Collapsing the two would either hide a
    # claim that was never measured, or imply a field is missing when it is
    # present. Both mislead in different directions.
    unverified: list[dict[str, Any]] = []
    notes = list(extra_notes or [])

    # ---- inputs -------------------------------------------------------
    bundle = input_bundle
    if bundle is None:
        declared = header.get("Source bundle") or header.get("Source")
        bundle = Path(declared) if declared else None

    inputs: dict[str, Any] = {"bundle_path": str(bundle) if bundle else None}
    if bundle and bundle.exists() and input_verified:
        inputs.update({"bundle_md5": _md5(bundle),
                       "bundle_bytes": bundle.stat().st_size,
                       "hash_basis": "verified identical to the bytes consumed"})
    elif bundle:
        inputs["bundle_md5"] = None
        if mode == "live":
            # A live run knows its own input. Failing to hash it is a defect in
            # the capture, not an unrecoverable historical fact.
            raise FileNotFoundError(
                f"live provenance requires a readable input bundle; {bundle} "
                "is missing or unverified"
            )
        unrecoverable.append({
            "field": "inputs.bundle_md5",
            "reason": ("the input bundles were regenerated on 2026-07-24 and "
                       "2026-07-27; the bytes this run consumed are not "
                       "recoverable, and hashing the current file would assert "
                       "a false provenance claim"),
        })

    manifest_md5 = _md5(SOURCE_MANIFEST)
    if input_verified:
        inputs["source_manifest"] = {"path": str(SOURCE_MANIFEST),
                                     "md5": manifest_md5}
    else:
        inputs["source_manifest"] = {"path": str(SOURCE_MANIFEST), "md5": None}
        unrecoverable.append({
            "field": "inputs.source_manifest.md5",
            "reason": "manifest has been edited since this run",
        })

    # ---- model identity ------------------------------------------------
    model = {k.lower().replace(" ", "_"): v for k, v in header.items()
             if k in ("Generation Method", "Agent runtime", "Provider", "Model",
                      "Reasoning effort", "Mode", "Temperature")}
    if not model.get("model"):
        unrecoverable.append({
            "field": "model.model",
            "reason": "the record header predates model identity being written into headers",
        })

    # Temperature in a Claude Code header is asserted by the agent because the
    # prompt template says to write it, not observed from a setting the runtime
    # exposes. Recording it as though it were measured would be the same class
    # of false claim this module exists to prevent.
    runtime = (model.get("agent_runtime") or "").strip().lower()
    if model.get("temperature") and runtime == "claude code":
        model["temperature_basis"] = "asserted by the generating agent, not observed"
        unverified.append({
            "field": "model.temperature",
            "value": model.get("temperature"),
            "reason": ("the Claude Code runtime does not expose a temperature "
                       "setting to the agent or to this recorder; the header "
                       "value restates the prompt template rather than a "
                       "measured parameter. A direct API run can observe it."),
        })

    cfg = load_generation_config()
    declared = (cfg.get("model") or {}) if isinstance(cfg, dict) else {}
    if declared:
        model["shared_config"] = {
            "path": str(DETERMINISTIC_CONFIG),
            "name": declared.get("name"),
            "temperature": declared.get("temperature"),
            "max_tokens": declared.get("max_tokens"),
        }
        # Exact inequality, not substring (#349). The pin `claude-opus-5` is a
        # substring of every family variant — `claude-opus-5[1m]`,
        # `google/claude-opus-5-high` — so a containment test can never fire
        # for route drift, which is precisely what this note exists to record.
        if declared.get("name") and model.get("model") and \
                str(declared["name"]) != str(model["model"]):
            notes.append(
                f"Model mismatch: this run used {model['model']!r} while "
                f"{DETERMINISTIC_CONFIG} pins {declared['name']!r}. The two "
                "generation paths are not running the same model.")

    # ---- system --------------------------------------------------------
    if mode == "live":
        system = system_facts()
    else:
        system = {"note": ("not recorded at run time; the current machine is "
                           "not evidence of what produced this run")}
        unrecoverable.append({
            "field": "system",
            "reason": "hardware was not captured when this run executed",
        })

    data: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "record_type": "d4d_generation_provenance",
        "record_mode": mode,
        "record_generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run": {"label": label, "project": project, "method": method,
                "arm": _arm_for(base),
                "replicate": _replicate_for(label)},
        "model": model or None,
        "prompts": prompt_facts(prompt_paths),
        "schema": schema_facts() | (
            {"digest_md5": schema_digest_md5} if schema_digest_md5 else {}),
        "software": software_facts() if mode == "live" else {
            "note": "reconstructed; versions are today's, not the run's"},
        "repo": repo_facts(),
        "system": system,
        "inputs": inputs,
        "outputs": {"full": _artifact(full), "core": _artifact(core),
                    "report": _artifact(report)},
        "unrecoverable": unrecoverable or None,
        "unverified": unverified or None,
        "notes": notes or None,
    }
    return ProvenanceRecord(data)


def _arm_for(method: str) -> str:
    from data_sheets_schema.runs import ARM_BY_METHOD
    return ARM_BY_METHOD.get(method, "unknown")


def _replicate_for(label: str) -> int | None:
    from data_sheets_schema.runs import REPLICATE_RE
    m = REPLICATE_RE.match(label)
    return int(m.group("replicate")) if m else None


def record_path_for(project: str, method: str, label: str,
                    concat_dir: Path = CONCAT_DIR) -> Path:
    base = method[:-5] if method.endswith("_core") else method
    return concat_dir / f"{base}_core" / label / f"{project}_provenance.yaml"


def migrate_record_hashes(path: Path, *, dry_run: bool = True) -> dict[str, Any]:
    """Replace md5 with sha256 in one record, but only where verifiable.

    The verification order is the point. An entry is re-hashed only after its
    recorded md5 is confirmed to still match the file, which proves the bytes are
    the ones that hash described. Re-hashing without that check would launder a
    *stale* verdict into a fresh-looking one — the record would gain a correct
    sha256 for content that no longer matches the verdict attached to it, and the
    staleness that `validation_status` exists to surface would be erased.

    Entries that cannot be verified keep their md5 and are reported, not
    rewritten.
    """
    import yaml as _yaml

    data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    migrated: list[str] = []
    skipped: list[dict[str, str]] = []

    def _walk(node: Any, trail: str = "") -> None:
        if isinstance(node, dict):
            if node.get("md5") and node.get("path") and not node.get("sha256"):
                p = Path(node["path"])
                if not p.exists():
                    skipped.append({"at": trail, "why": "file absent"})
                elif _md5(p) != node["md5"]:
                    skipped.append({"at": trail, "why": "recorded md5 no longer "
                                    "matches; the entry is stale and must not "
                                    "be re-hashed"})
                else:
                    node["sha256"] = _sha256(p)
                    node.pop("md5")
                    migrated.append(trail)
            for k, v in node.items():
                _walk(v, f"{trail}.{k}" if trail else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _walk(v, f"{trail}[{i}]")

    _walk(data)

    # Scalar hash fields, which carry no path of their own.
    for section, key, target in (("inputs", "bundle_md5", "bundle_sha256"),
                                 ("inputs", "source_manifest", None)):
        node = data.get(section) or {}
        if key == "bundle_md5" and node.get(key) and not node.get(target):
            bundle = node.get("bundle_path")
            if bundle and Path(bundle).exists() and _md5(Path(bundle)) == node[key]:
                node[target] = _sha256(Path(bundle))
                node.pop(key)
                migrated.append(f"{section}.{key}")
            else:
                skipped.append({"at": f"{section}.{key}",
                                "why": "bundle absent or no longer matches"})

    if migrated and not dry_run:
        if skipped:
            data.setdefault("notes", None)
        ProvenanceRecord(data=data).write(path)

    return {"path": str(path), "migrated": migrated, "skipped": skipped,
            "dry_run": dry_run}


def strip_output_hashes(path: Path, *, dry_run: bool = True) -> dict[str, Any]:
    """Remove integrity claims from `outputs`, keeping the description.

    Not a cover-up of the 89 stale hashes: it is the removal of a claim that was
    made at the wrong moment and never checked. The artifacts themselves are
    pinned by `validation.artifacts`, written after the run and verified
    164/164. Keeping a second, earlier, unverified hash meant maintaining two
    claims about the same bytes and believing the wrong one.

    `bytes` and `slots` stay. A stale description is a note that has drifted; a
    stale hash is a guarantee that is false.
    """
    import yaml as _yaml

    data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("record_mode") == "derived":
        # A derived record has no validation block; its outputs are the only
        # pinning it has, and they are written and hashed in one step.
        return {"path": str(path), "removed": [], "skipped": "derived record"}

    removed = []
    for key, entry in (data.get("outputs") or {}).items():
        if not isinstance(entry, dict):
            continue
        for algo in ("sha256", "md5"):
            if entry.pop(algo, None) is not None:
                removed.append(f"outputs.{key}.{algo}")
    if removed and not dry_run:
        ProvenanceRecord(data=data).write(path)
    return {"path": str(path), "removed": removed, "dry_run": dry_run}
