"""What release-level evidence each project's document corpus holds (#2914).

A record can only state a licence, a DOI, a version or a release date that
its bundle carries. The projects' corpora are not alike on exactly those
facts: AI_READI's carries its release-3.0.0 RO-Crate and v2.0 licence
(#539/#540), CM4AI's and VOICE's carry their Dataverse and PhysioNet release
records, and CHORUS's carries none of them -- its release facts are in the
XNBOPG crate, which ``crate_manifest.yaml`` keeps out of the document corpus
on purpose (``document_corpus: exclude``). A cross-project difference on
identifier, licence or version slots is then a property of the corpus, not
of generation, and this inventory is what lets a report say so.

The inventory is a pure function of the bytes it is given: the source
manifest, read through ``source_metadata.projection`` (the same tiers and
the same ``priority:`` override ``source_priority.priority_of`` applies),
and optionally the crate manifest. No file is opened here and nothing is
looked up in an ambient registry, so the same bytes give the same output.

What it states is a declaration about the corpus, not about the documents'
content: a source typed ``license`` is counted as a licence source whatever
its text says, and a project with none may still mention a licence in prose
(CHORUS's bundle quotes a training-programme "Licensing Agreement" and an
MIT software licence, neither a dataset licence). Nor does it consult the
``scope:`` block: a release record in a project's corpus may describe a
related-but-distinct dataset, as VOICE's ``physionet_pediatric_1_1_0`` does.
"""
from __future__ import annotations

import hashlib
import json

import yaml

from data_sheets_schema import source_metadata

#: Source types that carry the terms a dataset is released under. Spelled as
#: the study manifest's ``source_priority`` table spells them; matched
#: case-insensitively so a neutral manifest's ``License`` is not missed.
GOVERNANCE_TYPES = ("license", "DUA", "IRB")

#: Source types that are the release describing itself: the crate, its
#: structured metadata, and the repository record of the release. They are
#: the study's tier-1 types, named here rather than read off tier 1 so that a
#: ``priority:`` override on a documentation page does not make it a release
#: record. ``historical data release`` is not one: it records an earlier
#: release, not the one the record describes.
RELEASE_RECORD_TYPES = ("RO-Crate", "structured metadata", "data resource")

#: The type that means the crate itself is in the document corpus.
CRATE_TYPE = "RO-Crate"

INSTRUMENT = "release_inventory v1 (#2914)"


def _fold(value: str) -> str:
    return value.strip().casefold()


def _typed(rows, types) -> dict[str, list[dict]]:
    wanted = {_fold(t): t for t in types}
    out: dict[str, list[dict]] = {t: [] for t in types}
    for row in rows:
        name = wanted.get(_fold(row["source_type"]))
        if name is not None:
            out[name].append(_brief(row))
    return out


def _brief(row) -> dict:
    return {"source_id": row["source_id"], "source_type": row["source_type"],
            "effective_priority": row["effective_priority"],
            "superseded": "superseded_by" in row}


def _crate_policy(raw: bytes | str | None, project: str) -> dict:
    """The crate manifest's ``document_corpus`` declaration for one project.

    Every absence is a status, never an exception: no crate manifest was
    supplied (a neutral or external dataset), the manifest has no entry for
    the project, or the entry declares no policy -- which the downloader
    treats as ``allow`` (``rocrate_normalize.document_corpus_exclusions``)
    and which is reported as ``undeclared`` rather than as that default.
    """
    if raw is None:
        return {"status": "not_supplied", "document_corpus": None, "crate_manifest_sha256": None}
    encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
    if not isinstance(encoded, bytes):
        raise ValueError("crate manifest must be exact bytes or text")
    digest = hashlib.sha256(encoded).hexdigest()
    try:
        data = yaml.safe_load(encoded.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"crate manifest is not readable YAML: {exc}") from exc
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, dict):
        return {"status": "no_projects", "document_corpus": None, "crate_manifest_sha256": digest}
    entry = projects.get(project)
    if entry is None:
        return {"status": "no_entry", "document_corpus": None, "crate_manifest_sha256": digest}
    if not isinstance(entry, dict):
        return {"status": "malformed_entry", "document_corpus": None, "crate_manifest_sha256": digest}
    policy = entry.get("document_corpus")
    if policy is None or not str(policy).strip():
        return {"status": "undeclared", "document_corpus": None, "crate_manifest_sha256": digest}
    return {"status": "declared", "document_corpus": str(policy).strip().lower(),
            "crate_manifest_sha256": digest}


def inventory(manifest: bytes | str, crate_manifest: bytes | str | None, project: str) -> dict:
    """The release-level corpus inventory of one project.

    ``manifest`` is the source manifest's exact bytes (or text) and
    ``crate_manifest`` the crate manifest's, or ``None`` when none applies.
    Raises ``ValueError`` where ``source_metadata.projection`` does: a
    project the manifest does not declare, or a manifest it cannot bind.
    """
    authority = source_metadata.projection(manifest, project)
    rows = authority["sources"]
    tier1 = [_brief(row) for row in rows if row["effective_priority"] == 1]
    governance = _typed(rows, GOVERNANCE_TYPES)
    release_types = {_fold(t) for t in RELEASE_RECORD_TYPES}
    releases = [_brief(row) for row in rows if _fold(row["source_type"]) in release_types]
    return {
        "instrument": INSTRUMENT,
        "project": project,
        "source_manifest_sha256": authority["sha256"],
        "sources": len(rows),
        "tier1_count": len(tier1),
        "tier1_current_count": sum(not e["superseded"] for e in tier1),
        "tier1": tier1,
        "governance": governance,
        "release_records": releases,
        "crate_in_document_corpus": any(_fold(e["source_type"]) == _fold(CRATE_TYPE) for e in releases),
        "release_record_in_document_corpus": bool(releases),
        "crate_policy": _crate_policy(crate_manifest, project),
    }


def to_json(inventories: list[dict]) -> str:
    """Canonical JSON: sorted keys, fixed separators, one trailing newline."""
    return json.dumps(inventories, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _ids(entries) -> str:
    if not entries:
        return "none"
    return ", ".join(e["source_id"] + (" (superseded)" if e["superseded"] else "") for e in entries)


def render(inv: dict) -> list[str]:
    """Human-readable lines for one inventory, stable for the same input."""
    policy = inv["crate_policy"]
    crate = (f"document_corpus: {policy['document_corpus']}" if policy["status"] == "declared"
             else {"not_supplied": "no crate manifest supplied",
                   "no_projects": "crate manifest declares no projects",
                   "no_entry": "no crate-manifest entry",
                   "malformed_entry": "crate-manifest entry is not a mapping",
                   "undeclared": "entry declares no document_corpus policy"}[policy["status"]])
    lines = [
        f"{inv['project']}",
        f"   tier-1 sources     {inv['tier1_count']} ({inv['tier1_current_count']} current)"
        + (f": {_ids(inv['tier1'])}" if inv["tier1"] else ""),
    ]
    for kind in GOVERNANCE_TYPES:
        lines.append(f"   {kind + ' sources':18} {_ids(inv['governance'][kind])}")
    lines.append(f"   release record     {'yes' if inv['release_record_in_document_corpus'] else 'no'}"
                 + (f": {_ids(inv['release_records'])}" if inv["release_records"] else ""))
    lines.append(f"   crate in corpus    {'yes' if inv['crate_in_document_corpus'] else 'no'}"
                 f" · crate policy: {crate}")
    return lines


def lacking_release_evidence(inventories: list[dict]) -> list[str]:
    """Projects whose document corpus holds no release record and no
    licence or DUA source -- the ones whose release-level slots a record
    cannot fill from its bundle."""
    return [inv["project"] for inv in inventories
            if not inv["release_record_in_document_corpus"]
            and not inv["governance"]["license"] and not inv["governance"]["DUA"]]
