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
MIT software licence, neither a dataset licence).

A source in a project's corpus may describe a related-but-distinct dataset
rather than this one, as VOICE's ``physionet_pediatric_1_1_0`` describes the
pediatric release. The manifest's ``scope:`` block says so
(``related_but_distinct[].in_bundle``), and from v2 (#3283) the inventory
reads it off the same bytes: such a source is listed under
``related_sources`` with the dataset it belongs to and is left out of every
count of this dataset's evidence -- tier 1, governance and release records.
Only the declaration moves a source; nothing is inferred from a source's
type, name or text, so an undeclared related source is still counted as
this dataset's, and ``scope.status`` says whether there was a declaration to
read.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import json

import yaml

from data_sheets_schema import scope as scope_decl
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

INSTRUMENT = "release_inventory v2 (#2914, #3283)"


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


def _related(raw: bytes | str, project: str, source_ids: set[str]) -> tuple[dict, dict[str, list[dict]]]:
    """The project's scope declaration, and source id -> the related-but-
    distinct datasets whose ``in_bundle`` names it.

    Every shape short of a usable declaration is a status: ``undeclared``
    (no scope entry for the project), ``malformed`` (the entry, or its
    ``related_but_distinct``, is not the shape ``scope.check_manifest``
    reads), ``declared``. An ``in_bundle`` id the project lists no source
    for moves nothing and is named under ``in_bundle_unmatched`` as
    written. Ids are compared exactly as ``check_manifest`` compares them
    -- no stripping, no cast to text (#3447) -- and nothing is merged: one
    item per value ``check_manifest`` reports, repeats and equal-but-
    differently-written values (``7`` and ``7.0``) included, in entry and
    value order (#3507). So this list is that checker's unmatched-source
    finding surfaced where its effect would be. A source an entry names
    twice is moved for that entry once.

    An entry ``scope.malformed_in`` classifies as skipped (not a mapping, or
    no usable identifier) moves nothing: every other reader of the
    declaration skips it and the generation scope block omits it, so the
    model is never told its sources belong to another dataset (#3477). It
    is listed under ``skipped_entries`` with that classifier's problem and
    its ``in_bundle`` as written; its unmatched ids are still named, as
    ``check_manifest`` names them.

    An ``in_bundle`` value that is not an identifier at all -- a bool, a
    nested list, a mapping -- names no source and moves nothing
    (``scope.in_bundle_of`` drops it). It is not left out silently (#3543):
    it is listed under ``in_bundle_not_ids`` with its entry's index and the
    value as written, one item per value ``check_manifest`` reports as
    carrying something "not a source id", on usable and skipped entries
    alike, in entry and value order. The value is kept in a JSON-safe form
    (``_json_safe``) beside the type ``yaml.safe_load`` gave it, which is
    the type ``check_manifest`` names: a date, bytes or a set is a value
    YAML can write there, and storing it raw made ``to_json`` raise (#3580).

    An entry that names this dataset itself -- one of its identifiers (``id``
    or an alias, compared as ``scope._norm`` compares spellings) is the
    declaration's ``referent_id``, or its ``manifest_key`` is this project --
    contradicts the declaration it sits in, and ``check_manifest`` reports
    it as "the referent is also listed as related-but-distinct". Moving
    its sources would take this dataset's own release evidence out of its
    counts on the strength of that contradiction, so it moves nothing
    (#3581). It is listed under ``self_referential_entries``
    with what it matched on and its ``in_bundle`` as written; its unmatched
    ids are still named. The test is ``scope.names_referent``, the one
    ``check_manifest`` reports on (#3584): a narrower one would let an
    alias or a ``doi:`` spelling of the referent remove the evidence.
    """
    declared = scope_decl.scope_in(raw, project)
    status = {"status": "declared", "in_bundle_unmatched": [], "in_bundle_not_ids": [],
              "skipped_entries": [], "self_referential_entries": []}
    if declared is None:
        return {**status, "status": "undeclared"}, {}
    related = declared.get("related_but_distinct") if isinstance(declared, dict) else None
    if not isinstance(declared, dict) or not isinstance(related or [], list):
        return {**status, "status": "malformed"}, {}
    skipped = {row["index"]: row["problem"]
               for row in scope_decl.malformed_in(declared) if row["skipped"]}
    referent = declared.get("referent_id")
    moved: dict[str, list[dict]] = {}
    for index, entry in enumerate(related or []):
        claimed: set[str] = set()      # this entry's moved sources, each once
        if index in skipped:
            status["skipped_entries"].append({"index": index, "problem": skipped[index],
                                              "in_bundle": scope_decl.in_bundle_of(entry)})
        else:
            itself = scope_decl.names_referent(entry, referent, project)
            if itself:
                skipped[index] = "names this dataset itself"
                status["self_referential_entries"].append(
                    {"index": index, "matched_on": itself,
                     "in_bundle": scope_decl.in_bundle_of(entry)})
        dataset = {"id": entry.get("id") if scope_decl._is_identifier(entry.get("id")) else None,
                   "name": entry.get("name") if isinstance(entry.get("name"), str) else None,
                   "manifest_key": (entry.get("manifest_key")
                                    if scope_decl._is_identifier(entry.get("manifest_key")) else None),
                   # The entry's aliases, as every scope reader takes them: an
                   # entry identified by also_known_as alone is usable, and
                   # this is then the only identifier that names it (#3494).
                   "also_known_as": scope_decl.aliases_of(
                       {"also_known_as": entry.get("also_known_as")}),
                   } if isinstance(entry, dict) else None
        written = entry.get("in_bundle") if isinstance(entry, dict) else None
        if written:     # the shapes and the falsy guard check_manifest applies
            for value in (list(written) if isinstance(written, (list, tuple)) else [written]):
                if not scope_decl._is_identifier(value):
                    status["in_bundle_not_ids"].append({"index": index, "type": type(value).__name__,
                                                        "value": _json_safe(value)})
        for sid in scope_decl.in_bundle_of(entry):
            if sid not in source_ids:
                status["in_bundle_unmatched"].append(sid)
            elif index not in skipped and sid not in claimed:
                claimed.add(sid)
                moved.setdefault(sid, []).append(dataset)
    return status, moved


#: Types a rejected value can keep as it is: JSON writes them unchanged.
_JSON_SCALARS = (str, int, float, bool, type(None))


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _json_safe(value):
    """A value ``yaml.safe_load`` produced, in a form ``json.dumps`` writes
    and that is the same for the same bytes (#3580). JSON scalars, lists and
    string-keyed mappings are kept as they are; anything else becomes a
    one-key mapping naming its YAML tag: a date or timestamp its ISO text,
    bytes (``!!binary``) their base64, a set its members sorted by their
    canonical JSON (a set's own order varies with string hashing), and a
    mapping with a key that is not a string its ``[key, value]`` pairs in
    the order written. The row that carries it also names the loaded type,
    so a written mapping that happens to look like one of these tags is
    still told apart at the top level."""
    if isinstance(value, _JSON_SCALARS):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        if all(isinstance(k, str) for k in value):
            return {k: _json_safe(v) for k, v in value.items()}
        return {"!!map": [[_json_safe(k), _json_safe(v)] for k, v in value.items()]}
    if isinstance(value, (set, frozenset)):
        return {"!!set": sorted((_json_safe(v) for v in value), key=_canonical)}
    if isinstance(value, (datetime.date, datetime.datetime)):
        return {"!!timestamp": value.isoformat()}
    if isinstance(value, (bytes, bytearray)):
        return {"!!binary": base64.b64encode(bytes(value)).decode("ascii")}
    return {f"!!{type(value).__name__}": repr(value)}


def inventory(manifest: bytes | str, crate_manifest: bytes | str | None, project: str) -> dict:
    """The release-level corpus inventory of one project.

    ``manifest`` is the source manifest's exact bytes (or text) and
    ``crate_manifest`` the crate manifest's, or ``None`` when none applies.
    Raises ``ValueError`` where ``source_metadata.projection`` does: a
    project the manifest does not declare, or a manifest it cannot bind.
    """
    authority = source_metadata.projection(manifest, project)
    scope, moved = _related(manifest, project, {row["source_id"] for row in authority["sources"]})
    related = [{**_brief(row), "related_datasets": moved[row["source_id"]]}
               for row in authority["sources"] if row["source_id"] in moved]
    rows = [row for row in authority["sources"] if row["source_id"] not in moved]
    tier1 = [_brief(row) for row in rows if row["effective_priority"] == 1]
    governance = _typed(rows, GOVERNANCE_TYPES)
    release_types = {_fold(t) for t in RELEASE_RECORD_TYPES}
    releases = [_brief(row) for row in rows if _fold(row["source_type"]) in release_types]
    return {
        "instrument": INSTRUMENT,
        "project": project,
        "source_manifest_sha256": authority["sha256"],
        "sources": len(authority["sources"]),
        "scope": scope,
        "related_sources": related,
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


def _written(value) -> str:
    """An in_bundle value as the manifest wrote it: a plain string as
    itself, anything else (a number, a padded or empty string) in repr so
    the reader can see why it matched no source (#3446, #3447)."""
    if isinstance(value, str) and value and value == value.strip():
        return value
    return repr(value)


def _owner(dataset: dict | None) -> str:
    """The name a related dataset is rendered under: its manifest_key, name
    or id, else its aliases -- an entry identified by ``also_known_as``
    alone is usable to every scope reader, and they are then all that
    names it (#3494). ``str()``: an id or manifest_key a manifest wrote as
    a number is kept, which ``scope._is_identifier`` admits (#3446) -- the
    number 0 included: a value is passed over only when it is absent or
    blank, never for being falsy (#3506)."""
    if dataset is None:
        return "a malformed entry"
    for named in (dataset["manifest_key"], dataset["name"], dataset["id"]):
        if named is not None and str(named).strip():
            return str(named)
    if dataset.get("also_known_as"):
        return "a dataset also known as " + " / ".join(dataset["also_known_as"])
    return "an unnamed dataset"


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
    for entry in inv["related_sources"]:
        owners = ", ".join(_owner(d) for d in entry["related_datasets"])
        lines.append(f"   {'related source':18} {_ids([entry])} ({entry['source_type']}): "
                     f"declared in_bundle for {owners}, not counted above")
    scope = inv["scope"]
    if scope["status"] == "malformed":
        lines.append("   scope              declaration is malformed; no source moved")
    for row in scope["skipped_entries"]:
        lines.append(f"   scope              related_but_distinct[{row['index']}]: {row['problem']}"
                     + (f"; its in_bundle moves nothing: {', '.join(_written(v) for v in row['in_bundle'])}"
                        if row["in_bundle"] else ""))
    for row in scope["self_referential_entries"]:
        named = ", ".join(f"{m['field']} {_written(m['value'])}" for m in row["matched_on"])
        lines.append(f"   scope              related_but_distinct[{row['index']}]: names this "
                     f"dataset itself ({named}); its in_bundle moves nothing"
                     + (f": {', '.join(_written(v) for v in row['in_bundle'])}" if row["in_bundle"] else ""))
    for row in scope["in_bundle_not_ids"]:
        # A bool, null, list or mapping as written; a date, bytes or a set
        # by its type and the JSON-safe form stored, so the line is the same
        # for the same bytes (#3580).
        shown = (repr(row["value"]) if row["type"] in ("bool", "NoneType", "list", "dict")
                 else f"a {row['type']} {_canonical(row['value'])}")
        lines.append(f"   scope              related_but_distinct[{row['index']}]: in_bundle "
                     f"carries {shown}, not a source id; it moves nothing")
    if scope["in_bundle_unmatched"]:
        lines.append(f"   scope              in_bundle names no source of this project: "
                     f"{', '.join(_written(v) for v in scope['in_bundle_unmatched'])}")
    lines.append(f"   crate in corpus    {'yes' if inv['crate_in_document_corpus'] else 'no'}"
                 f" · crate policy: {crate}")
    return lines


def lacking_release_evidence(inventories: list[dict]) -> list[str]:
    """Projects whose document corpus holds no release record and no
    licence or DUA source of their own -- the ones whose release-level slots
    a record cannot fill from its bundle. A related-but-distinct dataset's
    release record is not this dataset's release evidence (#3283)."""
    return [inv["project"] for inv in inventories
            if not inv["release_record_in_document_corpus"]
            and not inv["governance"]["license"] and not inv["governance"]["DUA"]]
