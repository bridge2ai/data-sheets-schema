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
        "full_md5": _md5(FULL_SCHEMA),
        "core_path": str(CORE_SCHEMA),
        "core_md5": _md5(CORE_SCHEMA),
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
    if not path.exists():
        return None
    return {"path": str(path), "md5": _md5(path), "bytes": path.stat().st_size,
            "slots": _slot_count(path) if path.suffix == ".yaml" else None}


@dataclass
class ProvenanceRecord:
    data: dict[str, Any] = field(default_factory=dict)

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# D4D generation provenance record\n"
            f"# record_version {RECORD_VERSION} — see src/data_sheets_schema/provenance.py\n"
            + yaml.safe_dump(self.data, sort_keys=False, allow_unicode=True),
            encoding="utf-8")
        return path


@dataclass
class Contribution:
    """One generated record that a derived record consumed.

    The md5 is the point. A derived record that merely names its sources is not
    reproducible: the sources are themselves stochastic outputs that can be
    regenerated under the same label with different content. Pinning the bytes is
    what makes "this came from those" checkable rather than asserted.
    """

    label: str
    project: str
    method: str
    path: str
    md5: str
    slots: int | None = None
    contributed_slots: int | None = None   # how many slots this source supplied


def contribution(path: Path, *, label: str, project: str, method: str,
                 contributed_slots: int | None = None) -> Contribution:
    art = _artifact(path)
    if art is None:
        raise FileNotFoundError(f"contributing record does not exist: {path}")
    return Contribution(label=label, project=project, method=method,
                        path=art["path"], md5=art["md5"], slots=art["slots"],
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
        "outputs": {k: _artifact(v) for k, v in outputs.items()},
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
        if declared.get("name") and model.get("model") and \
                str(declared["name"]) not in str(model["model"]):
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
