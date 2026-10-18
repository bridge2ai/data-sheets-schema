"""The merged schema a run recorded, read by the hash it recorded (#3931).

A check recomputed after a run asks about the rules that run was given:
which CURIE prefixes its schema declared, which slots it ranged on
`uriorcurie` or on `Person`, which enum aliases its normaliser rewrote. A
schema release moves those rules. Every run records the merged schema it
read (`schema.full_path` with `full_sha256`, else `full_md5`), so a
schema-dependent recompute keys on that hash. It does not key on today's
file, or on the record's declared version: a release's final state
(`release_history.yaml`) is not the version a run made earlier under the
same label read (#3702).

`run_schema_bytes` is the one resolution, first written inside
`removals.run_enum_aliases` (#3702, #3788, #3851, #3953):

1. the file on disk, where its bytes hash to every hash the record gives;
2. a recorded reconstruction (`reconstructed_bytes`): bytes no reachable
   commit holds, committed as a hash-checked artefact and read before git
   is asked, so a fresh or shallow clone reads them too;
3. the committed version of the path whose every recorded hash matches
   (`provenance.committed_bytes_for`);
4. else nothing, and the caller reads today's schema. The basis says so and
   why: the record names no hash, no committed version matches, git cannot
   answer (a shallow clone) or cannot be started at all (#3851), or the
   reconstruction cannot be read. Each failure is this stated fallback,
   never a traceback.

The basis is one mapping wherever it is reported: `source`, the recorded
`path` and hashes, and either a `reason` or what was read (`commit` and
`matched_on` for a git blob; `artefact`, `base_commit`, `matched_on`,
`observed_at` and `reconstruction` for a reconstruction).

`identifier_rules` reads the identifier rules from those bytes for the
form block's undeclared-prefix count and the grounding block's walk and
resolver-URL findings. #3788 is the case: the 2026-08-13 v4 rep1 VOICE run
read a schema declaring `ROR`, `ORCID` and `doi`, which its commit's blob
lacks. On 2026-09-30, 192 of the 283 corpus records read a schema that
declares none of the three, which today's does: 282 resolve to a git blob
and one to its reconstruction.
"""
from __future__ import annotations

import hashlib
from typing import Any, NamedTuple

#: The fallback's `source`: what a caller reads when the run's bytes cannot
#: be recovered.
TODAY = "today's schema"


def run_schema_bytes(record: dict[str, Any] | None, *, kind: str = "full") -> tuple[bytes | None, dict[str, Any]]:
    """(bytes, basis): the merged schema the run recorded, from disk, from a
    recorded reconstruction, or from the committed version that matches, in
    that order; (None, basis) where none of them can be read, the basis
    saying today's schema is read instead and why. Every hash the record
    gives must match, so an md5-only record whose file changed on disk goes
    on to git (#3803). ``kind=core`` resolves the recorded core schema by
    exactly the same rules; the default full-schema contract is unchanged."""
    if kind not in {"full", "core"}:
        raise ValueError("schema kind must be full or core")
    schema = (record or {}).get("schema") if isinstance(record, dict) else None
    schema = schema if isinstance(schema, dict) else {}
    path, sha256, md5 = (schema.get(f"{kind}_{key}") for key in ("path", "sha256", "md5"))
    sha256 = sha256 if isinstance(sha256, str) and sha256 else None
    md5 = md5 if isinstance(md5, str) and md5 else None
    if not isinstance(path, str) or not path or not (sha256 or md5):
        return None, {"source": TODAY, "reason": ("the record names no merged schema by path and hash" if kind == "full"
                                          else "the record names no merged core schema by path and hash")}
    hashes = {k: v for k, v in (("sha256", sha256), ("md5", md5)) if v}
    from data_sheets_schema.resources import resource_path
    try:
        on_disk = resource_path(path)
        data = on_disk.read_bytes() if on_disk.is_file() else None
    except OSError:
        data = None
    if data is not None and all(getattr(hashlib, k)(data).hexdigest() == v for k, v in hashes.items()):
        return data, {"source": "the run's schema, on disk", "path": path, **hashes}
    # Bytes no reachable commit holds, committed as a hash-checked artefact
    # (#3788): read before git, which a shallow clone cannot answer (#3953).
    from data_sheets_schema.reconstructed_bytes import reconstructed_bytes_for
    try:
        rebuilt = reconstructed_bytes_for(path, md5=md5, sha256=sha256)
    except OSError as exc:
        return None, {"source": TODAY, "path": path, **hashes,
                      "reason": "the run's schema is not on disk and its recorded reconstruction "
                                f"could not be read ({type(exc).__name__}: {exc})"}
    if rebuilt is not None:
        data, entry = rebuilt
        return data, {"source": "the run's schema, reconstructed", "path": path, **hashes,
                      "artefact": entry["artefact"], "base_commit": entry["base_commit"],
                      "matched_on": entry["matched_on"], "observed_at": entry["observed_at"],
                      "reconstruction": f"reconstructed_bytes.RECONSTRUCTIONS (#{entry['issue']})"}
    from data_sheets_schema.provenance import GitUnavailable, committed_bytes_for
    try:
        found = committed_bytes_for(path, md5=md5, sha256=sha256)
    except GitUnavailable as exc:
        return None, {"source": TODAY, "path": path, **hashes,
                      "reason": f"the run's schema is not on disk and git cannot answer ({exc})"}
    except OSError as exc:
        # git could not be started at all (not installed, not on PATH, not
        # executable): the same degraded fallback, not a failure (#3851).
        return None, {"source": TODAY, "path": path, **hashes,
                      "reason": f"the run's schema is not on disk and git could not be run "
                                f"({type(exc).__name__}: {exc})"}
    if found is None:
        return None, {"source": TODAY, "path": path, **hashes,
                      "reason": "no committed version of the path hashes to what the record recorded"}
    data, entry = found
    return data, {"source": "the run's schema, a git blob", "path": path, **hashes,
                  "commit": entry["commit"], "matched_on": entry["matched_on"]}


class IdentifierRules(NamedTuple):
    """What a merged schema says about identifiers: the CURIE prefixes it
    declares (as written), the slots whose induced range is `uriorcurie`
    and those whose induced range is `Person`, and its http prefix bases
    (lower-cased, longest first, as `grounding.declared_bases` orders them)."""
    prefixes: frozenset[str]
    slots: frozenset[str]
    persons: frozenset[str]
    bases: tuple[tuple[str, str], ...]


def todays_identifier_rules() -> IdentifierRules:
    """The rules of the merged schema on disk, from the functions every
    other caller reads them with."""
    from data_sheets_schema.grounding import declared_bases
    from data_sheets_schema.identifiers import declared_prefixes, person_slots, uriorcurie_slots
    return IdentifierRules(frozenset(declared_prefixes()), frozenset(uriorcurie_slots()),
                           frozenset(person_slots()), tuple(declared_bases()))


def _derive_rules(data: bytes) -> IdentifierRules:
    """The rules of other bytes, by the functions today's are read with.

    The bytes are parsed once (`schema_view.version_document`). The prefixes
    and bases are read from that document, and the induced slots from a
    view of it (`schema_view.version_view`). That view is the version's own,
    so reading it does not evict today's (#926). It is released when the
    slots have been read, because these rules are what `_rules_of` keeps
    (#4082). Bytes that import a local file are refused, since the import
    would be read from today's tree."""
    from data_sheets_schema.grounding import declared_bases_of
    from data_sheets_schema.identifiers import (FULL_SCHEMA, declared_prefixes_of, person_slots_of,
                                                uriorcurie_slots_of)
    from data_sheets_schema.schema_view import version_document, version_view
    doc = version_document(data)
    prefixes, bases = frozenset(declared_prefixes_of(doc)), tuple(declared_bases_of(doc))
    with version_view(FULL_SCHEMA, doc) as view:
        slots, persons = frozenset(uriorcurie_slots_of(view)), frozenset(person_slots_of(view))
    return IdentifierRules(prefixes, slots, persons, bases)


#: Identifier rules by the sha256 of the merged-schema bytes they were read
#: from, so each schema version is derived once per process. The rules are
#: kept here, and the view they were read from is not (#4082).
_RULES_BY_SHA256: dict[str, IdentifierRules] = {}


def _rules_of(data: bytes) -> IdentifierRules:
    """The rules of `data`, derived once per version. Bytes equal to today's
    file are read through today's functions and their shared view, so a
    record whose run read today's schema builds no second view of it."""
    key = hashlib.sha256(data).hexdigest()
    if key not in _RULES_BY_SHA256:
        from data_sheets_schema.identifiers import FULL_SCHEMA
        from data_sheets_schema.schema_cache import sha256_of
        try:
            today = sha256_of(FULL_SCHEMA)
        except OSError:
            today = None
        _RULES_BY_SHA256[key] = todays_identifier_rules() if key == today else _derive_rules(data)
    return _RULES_BY_SHA256[key]


def identifier_rules(record: dict[str, Any] | None) -> tuple[IdentifierRules, dict[str, Any]]:
    """(rules, basis): the identifier rules of the merged schema the run
    recorded (`run_schema_bytes`), else today's, the basis saying which and
    why. Recovered bytes that cannot be read as a schema are the same
    stated fallback, with the reason."""
    data, basis = run_schema_bytes(record)
    if data is None:
        return todays_identifier_rules(), basis
    try:
        return _rules_of(data), basis
    except Exception as exc:  # noqa: BLE001 — recovered bytes no view can load are a fallback, not a crash
        return todays_identifier_rules(), {
            "source": TODAY, **{k: basis[k] for k in ("path", "sha256", "md5") if k in basis},
            "reason": f"the bytes recovered as {basis['source']!r} could not be loaded as a schema "
                      f"({type(exc).__name__}: {exc})"}
