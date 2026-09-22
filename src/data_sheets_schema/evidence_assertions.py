"""Check explicit evidence, not semantic entailment (#1801/#1815/#1816).

Version 1 binds quotations to an artifact/path or document/chunk and checks
removal of relationships an audit explicitly rejected. Opt-in version 2 also
proves child removals in uniquely matched anonymous objects and validates
actions at audit admission. Opt-in version 3 requires complete scalar-value
source reviews and checks declared attribution/status consistency. Opt-in
version 4 adds exact-original-bound anonymous whole-member removals. Opt-in
version 5 permits narrowly projected registered provenance in source reviews.
Version 6 preserves those scientific checks; a separately registered native
audit may use a bounded source-free draft grammar stage before the final check. No version
independently classifies prose or certifies semantic conclusions. All inputs
are read only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

import yaml

INSTRUMENT = "evidence_assertions v1 (#1801, #1815, #1816)"
ARTIFACTS = {"original_full", "original_core", "final_full", "final_core"}
MISSING = object()
# Stable identifier and content-checksum slots declared by the D4D schema,
# plus human-readable names. A schema-driven regression checks coverage when
# the schema changes. Contact details and descriptive text are not identities.
IDENTITY_FIELDS = frozenset({"id", "name", "orcid", "doi", "grant_number",
                             "variable_name", "hash", "md5", "sha256", "checksum", "target_dataset"})
NARRATIVE_FIELDS = frozenset({"description", "notes", "source_caveats"})


def instrument(protocol_version: int = 1) -> str:
    if type(protocol_version) is not int or protocol_version not in (1, 2, 3, 4, 5, 6, 7):
        raise ValueError("unsupported evidence protocol version")
    return {1: INSTRUMENT, 2: "evidence_assertions v2 (#1839)",
            3: "evidence_assertions v3 / source_review v1 (#1815, #1782)",
            4: "evidence_assertions v4 / source_review v1 (#2165)",
            5: "evidence_assertions v5 / source_review v2 (#2169)",
            6: "evidence_assertions v6 / source_review v2 (#2178)",
            7: "evidence_assertions v7 / source_review v2 (#2192)"}[protocol_version]


def protocol_for_renderer(render_version: int) -> int:
    return 7 if render_version >= 20 else 6 if render_version >= 18 else 5 if render_version >= 16 else 4 if render_version >= 15 else 3 if render_version >= 12 else 2 if render_version >= 11 else 1


def _review_authority(protocol_version, source_manifest_raw, project):
    """Keep legacy calls/signatures at their call sites exactly as before."""
    instrument(protocol_version)
    if protocol_version in (5, 6, 7):
        return {"protocol_version": protocol_version, "source_manifest_raw": source_manifest_raw, "project": project}
    if source_manifest_raw is not None or project is not None:
        raise ValueError("registered provenance authority requires evidence protocol 5")
    return {}


def load_json(raw: str | bytes):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate evidence JSON key: {key}")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique)


def load_record(raw: str) -> dict:
    from data_sheets_schema.duplicate_keys import find_duplicate_keys
    if find_duplicate_keys(raw):
        raise ValueError("artifact has duplicate YAML mapping keys; its location is ambiguous")
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError("artifact must be a YAML mapping")
    return value


def _tokens(pointer: str) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("location must be a non-root JSON Pointer, or @header")
    if re.search(r"~(?![01])", pointer):
        raise ValueError("invalid JSON Pointer escape")
    return [part.replace("~1", "/").replace("~0", "~")
            for part in pointer[1:].split("/")]


def _at(value: Any, tokens: list[str]) -> Any:
    for token in tokens:
        if isinstance(value, dict):
            value = value.get(token, MISSING)
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            index = int(token)
            value = value[index] if index < len(value) else MISSING
        else:
            return MISSING
    return value


def _fold(text: str) -> str:
    # Fold line wrapping only. Keep punctuation, case and modal verbs.
    return " ".join(text.split())


def _literal(value: Any, quote: str, seen: set[int] | None = None) -> bool:
    if isinstance(value, str):
        return _fold(quote) in _fold(value)
    if value is None or isinstance(value, (bool, int, float)):
        # A scalar is one value: 2 is not evidence of a value of 12.
        return quote.strip() == json.dumps(value, allow_nan=False)
    seen = set() if seen is None else seen
    if id(value) in seen:
        return False
    seen.add(id(value))
    if isinstance(value, dict):
        return any(_literal(v, quote, seen) for v in value.values())
    if isinstance(value, list):
        return any(_literal(v, quote, seen) for v in value)
    return False


def _header(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            break
        lines.append(line)
    return "\n".join(lines)


def _problem(kind: str, detail: str, **fields) -> dict:
    return {"kind": kind, "detail": detail, **fields}


def check_assertions(claims, *, artifacts: dict[str, str],
                     chunks: dict[str, dict[str, str]]) -> list[dict]:
    """Check declared assertions against caller-selected inputs."""
    if not isinstance(claims, list):
        return [_problem("evidence_contract", "claims must be an array")]
    findings, parsed = [], {}
    for index, claim in enumerate(claims):
        try:
            if not isinstance(claim, dict):
                raise ValueError("each assertion must be an object")
            if "source" in claim:
                if set(claim) != {"source", "chunk", "quote"}:
                    raise ValueError("source assertion needs exactly source, chunk and quote")
                chunk = chunks.get(claim["chunk"])
                if chunk is None or chunk["source"] != claim["source"]:
                    raise ValueError("the named document does not own the named chunk")
                if claim["source"] == "<preamble>":
                    raise ValueError("the bundle preamble is not a source document")
                quote = claim["quote"]
                if not isinstance(quote, str) or not quote.strip():
                    raise ValueError("quote must be nonempty text")
                if _fold(quote) not in _fold(chunk["text"]):
                    findings.append(_problem("source_quote_not_found",
                        "quote is absent from the named document's named chunk",
                        assertion=index, source=claim["source"], chunk=claim["chunk"]))
                continue
            if set(claim) != {"artifact", "path", "op", "quote"}:
                raise ValueError("artifact assertion needs exactly artifact, path, op and quote")
            name, path, op, quote = (claim[k] for k in ("artifact", "path", "op", "quote"))
            if name not in ARTIFACTS or name not in artifacts:
                raise ValueError("the named artifact was not supplied")
            if op not in {"contains", "lacks"} or not isinstance(quote, str) or not quote.strip():
                raise ValueError("op must be contains or lacks, with a nonempty quote")
            if path == "@header":
                value = _header(artifacts[name])
            else:
                if name not in parsed:
                    parsed[name] = load_record(artifacts[name])
                value = _at(parsed[name], _tokens(path))
                if value is MISSING:
                    raise ValueError("artifact path does not exist; absence of a field is not a lost qualifier")
            found = _literal(value, quote)
            if found != (op == "contains"):
                findings.append(_problem("artifact_assertion_contradicted",
                    f"quoted text is {'present' if found else 'absent'} at this exact artifact location",
                    assertion=index, artifact=name, path=path, op=op, quote=quote))
        except (ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
            findings.append(_problem("evidence_contract", str(exc), assertion=index))
    return findings


def check_audit(audit, *, artifacts: dict[str, str], chunks: dict,
                protocol_version: int = 1, source_manifest_raw: bytes | str | None = None,
                project: str | None = None) -> dict:
    """Require evidence for each finding before using its recommendation."""
    authority = _review_authority(protocol_version, source_manifest_raw, project)
    problems, count = [], 0
    if not isinstance(audit, dict) or not isinstance(audit.get("findings"), list):
        problems.append(_problem("evidence_contract", "audit.findings must be an array"))
    else:
        for index, finding in enumerate(audit["findings"]):
            if not isinstance(finding, dict):
                problems.append(_problem("evidence_contract", "audit finding must be an object", finding=index))
                continue
            claims = finding.get("evidence")
            if not isinstance(claims, list) or not claims:
                problems.append(_problem("evidence_contract", "every audit finding needs a nonempty evidence array", finding=index))
                continue
            count += len(claims)
            problems += [{**f, "finding": index} for f in
                         check_assertions(claims, artifacts=artifacts, chunks=chunks)]
    if protocol_version >= 2 and isinstance(audit, dict) and isinstance(audit.get("findings"), list):
        # Check whether declarations are actionable before a paid reconciliation.
        # With identical inputs a valid action is retained, which is expected here.
        try:
            original = load_record(artifacts["original_full"])
            preconditions = [f for f in check_relationship_removals(
                audit, original, original, protocol_version=protocol_version,
                original_raw=artifacts["original_full"])
                if f["kind"] != "unsupported_relationship_retained"]
            problems += preconditions
            if not preconditions:
                paths = [_tokens(f["remove_relationship"]["path"]) for f in audit["findings"]
                         if isinstance(f, dict) and "remove_relationship" in f]
                projected = _project_removals(original, paths)
                problems += check_relationship_removals(audit, original, projected,
                    protocol_version=protocol_version, original_raw=artifacts["original_full"])
        except (ValueError, KeyError, yaml.YAMLError) as exc:
            problems.append(_problem("evidence_contract", str(exc)))
    out = {"instrument": instrument(protocol_version), "checked": True,
           "assertions_checked": count, "findings": problems}
    if protocol_version >= 3:
        from data_sheets_schema import source_review
        review = source_review.check(audit.get("source_review") if isinstance(audit, dict) else None,
            raw=artifacts["original_full"], artifact="original_full", chunks=chunks,
            audit_findings=audit.get("findings") if isinstance(audit, dict) else None, **authority)
        out["source_review_original"] = review
        problems.extend(review["findings"])
    return out


def _identity_paths(declared=None):
    paths = {(key,) for key in IDENTITY_FIELDS}
    if declared is not None:
        for depth in range(1, len(declared)):
            paths.update(tuple(declared[:depth]) + (key,) for key in IDENTITY_FIELDS)
        paths.add(tuple(declared))
    return paths


def _member_identities(member, declared=None):
    if not isinstance(member, dict):
        raise ValueError("indexed relationship members must be objects with stable identities")
    paths = _identity_paths(declared)
    if declared is not None:
        # The selected member is the entire rejected relationship. A stable
        # wrapper ID cannot hide a different person or resource below it.
        # Ancestors use only their own identity: binding their descendants
        # would make the intended child removal invalidate ancestor matching.
        def descendants(value, prefix=(), ancestors=frozenset()):
            if not isinstance(value, (dict, list)):
                return
            if id(value) in ancestors:
                raise ValueError("cyclic relationship identity is ambiguous")
            ancestors = ancestors | {id(value)}
            if isinstance(value, dict):
                for key, child in value.items():
                    path = prefix + (key,)
                    if key in IDENTITY_FIELDS:
                        paths.add(path)
                    descendants(child, path, ancestors)
            else:
                for index, child in enumerate(value):
                    descendants(child, prefix + (str(index),), ancestors)

        descendants(member)
        # Bind absence too, at every containing object. An ID moved from a
        # rejected person to a surviving wrapper is still a new identity.
        for depth in range(1, len(declared)):
            prefix = tuple(declared[:depth])
            if not isinstance(_at(member, prefix), dict):
                raise ValueError("declared identity must follow nested objects, not indexed lists or scalars")
    identities = {path: _at(member, path) for path in paths}
    present = [value for value in identities.values() if value is not MISSING]
    if not present or any(not isinstance(value, str) or not value.strip() for value in present):
        raise ValueError("indexed relationship member or ancestor has no usable stable identity")
    return identities


def _member_structure(value, ancestors=frozenset()):
    """Bind structured content, allowing only narrative text to change."""
    if not isinstance(value, (dict, list)):
        return (type(value), value)
    if id(value) in ancestors:
        raise ValueError("cyclic relationship structure is ambiguous")
    ancestors = ancestors | {id(value)}
    if isinstance(value, list):
        return (list, [_member_structure(child, ancestors) for child in value])
    return (dict, {key: _member_structure(child, ancestors) for key, child in value.items()
                   if not (key in NARRATIVE_FIELDS and (child is None or isinstance(child, str)))})


def _matched_member(original, final, index, declared=None):
    """Resolve a member after reordering; a changed identity is ambiguous.

    Every remaining member must match exactly one original member with all
    its identifying fields intact. An unmatched/new member could be the
    rejected subject renamed, so absence cannot be established in that case.
    """
    identities = [_member_identities(member, declared) for member in original]
    overlap_paths = _identity_paths(declared)
    structures = [_member_structure(member) for member in original] if declared is not None else None
    if not isinstance(final, list):
        raise ValueError("final relationship container changed shape")
    mapped = {}
    for member in final:
        current = _member_identities(member, declared)
        structure = _member_structure(member) if structures is not None else None
        candidates = [i for i, fields in enumerate(identities) if current == fields
                      and (structures is None or structure == structures[i])]
        overlaps = [i for i, fields in enumerate(identities)
                    if any(path in overlap_paths and value is not MISSING and current.get(path, MISSING) == value
                           for path, value in fields.items())]
        if len(candidates) != 1 or overlaps != candidates or candidates[0] in mapped:
            raise ValueError("relationship identity or structure changed, disappeared, or is ambiguous; removal is unverified")
        mapped[candidates[0]] = member
    return mapped.get(index, MISSING)


def _without_fields(member, paths):
    """Copy dictionary paths only; never mutate or follow unstable list indexes."""
    if not isinstance(member, dict):
        raise ValueError("anonymous relationship ancestors must be objects")
    result = dict(member)
    for path in paths:
        current = result
        for token in path[:-1]:
            if token not in current:
                break
            child = current[token]
            if not isinstance(child, dict):
                raise ValueError("anonymous child removal paths must follow objects, not lists or scalars")
            current[token] = dict(child)
            current = current[token]
        else:
            current.pop(path[-1], None)
    return result


def _project_removals(value, paths):
    """Apply validated actions simultaneously in memory, using original indexes.

    Only selected ancestors are copied. Neither original objects nor model
    files are changed, and this hypothetical result is never published.
    """
    if not paths:
        return value
    if any(not path for path in paths):
        return MISSING
    mapping = isinstance(value, dict)
    result = {} if mapping else []
    entries = value.items() if mapping else enumerate(value)
    for key, child in entries:
        tails = [path[1:] for path in paths if path[0] == (key if mapping else str(key))]
        remaining = _project_removals(child, tails)
        if remaining is not MISSING:
            if isinstance(result, dict):
                result[key] = remaining
            else:
                result.append(remaining)
    return result


def _has_structural_anchor(structure):
    kind, value = structure
    if kind is dict:
        return any(_has_structural_anchor(child) for child in value.values())
    if kind is list:
        return any(_has_structural_anchor(child) for child in value)
    return value is not None and value != ""


def _matched_anonymous_ancestor(original, final, index, prefix, removal_paths):
    """Prove a bijection using all unchanged structure, not a chosen prose key.

    This supports child-field removals, not removal/replacement of anonymous
    members. Each original member's own masks locate its possible survivors.
    Only a unique complete correspondence proves which member survived.
    """
    if not isinstance(final, list) or len(final) != len(original):
        raise ValueError("anonymous ancestor members must all survive; removal or replacement is unverified")
    allowed = {i: [] for i in range(len(original))}
    for path in removal_paths:
        if path[:len(prefix)] != prefix or len(path) <= len(prefix) + 1:
            continue
        token, tail = path[len(prefix)], path[len(prefix) + 1:]
        if not re.fullmatch(r"0|[1-9][0-9]*", token) or int(token) not in allowed:
            continue
        if any(part in NARRATIVE_FIELDS for part in tail):
            raise ValueError("anonymous relationship removal cannot select narrative fields")
        allowed[int(token)].append(tail)
    signatures = [_member_structure(_without_fields(member, allowed[i]))
                  for i, member in enumerate(original)]
    if not all(_has_structural_anchor(sig) for sig in signatures):
        raise ValueError("anonymous ancestor lacks an unchanged structural anchor")
    identities = [_member_identities(member) if IDENTITY_FIELDS.intersection(member) else None
                  for member in original]
    candidates = {}
    for position, member in enumerate(final):
        candidates[position] = set()
        for i, signature in enumerate(signatures):
            try:
                if identities[i] is not None:
                    identity = _member_identities(member)
                    if identity != identities[i]:
                        continue
                    # Preserve v1's identifier safeguards in a mixed list.
                    # Structural anchors cannot excuse missing/borrowed IDs.
                    if any(j != i and fields is not None and any(
                            value is not MISSING and identity[path] == value
                            for path, value in fields.items())
                           for j, fields in enumerate(identities)):
                        continue
                current = _member_structure(_without_fields(member, allowed[i]))
            except ValueError:
                continue  # This member cannot match this original; other masks may match.
            if current == signature:
                candidates[position].add(i)
    mapped = {}
    while candidates:
        # A unique perfect bipartite matching always has a forced row.
        # Peel it and repeat. Without one, any perfect matching would have
        # an alternating cycle, or there is no complete matching at all.
        forced = next(((position, next(iter(choices))) for position, choices in candidates.items()
                       if len(choices) == 1), None)
        if forced is None or any(not choices for choices in candidates.values()):
            raise ValueError("anonymous ancestor structure changed, disappeared, or is ambiguous")
        position, matched = forced
        mapped[matched] = final[position]
        del candidates[position]
        for choices in candidates.values():
            choices.discard(matched)
    return mapped[index]


def _relationship_after(original, final, tokens, declared, *, protocol_version=1, removal_paths=()):
    """Walk dict keys and match each indexed ancestor, never its old index."""
    old, current = original, final
    for offset, token in enumerate(tokens):
        if isinstance(old, list):
            index = int(token)
            identity = declared if offset == len(tokens) - 1 else None
            if (protocol_version >= 2 and offset < len(tokens) - 1
                    and any(isinstance(member, dict) and not IDENTITY_FIELDS.intersection(member)
                            for member in old)):
                current = _matched_anonymous_ancestor(
                    old, current, index, tokens[:offset], removal_paths)
                old = old[index]
                continue
            # Validate the subject/ancestor even when the entire container
            # was removed; a declaration still needs an evidenced identity.
            _member_identities(old[index], identity)
            if current is not MISSING:
                current = _matched_member(old, current, index, identity)
            old = old[index]
        else:
            if current is not MISSING:
                if not isinstance(current, dict):
                    raise ValueError("final relationship ancestor changed shape")
                current = current.get(token, MISSING)
            old = old[token]
    return current


def check_relationship_removals(audit, original: dict, final: dict, *,
                                protocol_version: int = 1,
                                original_raw: str | bytes | None = None) -> list[dict]:
    """Check declared removal without treating list positions as identity.

    For a list member, identity is a pointer relative to that member, ending
    in a schema identifier field or name. All identifiers and indexed ancestors must retain
    stable identities. A non-list relationship must be absent altogether.
    Protocol 4's explicit anonymous whole-member form requires original_raw;
    dictionaries alone cannot establish its exact-artifact binding. Legacy
    forms and protocol versions do not use this additional argument.
    This checks the declared action, not the audit's semantic judgment.
    """
    instrument(protocol_version)
    findings, removal_paths, handled = [], [], set()
    if protocol_version >= 4:
        from data_sheets_schema.anonymous_removals import check
        handled, findings = check(audit, original, final, original_raw=original_raw)
    if protocol_version >= 2:
        for finding in audit.get("findings", []):
            try:
                removal_paths.append(_tokens(finding["remove_relationship"]["path"]))
            except (ValueError, TypeError, KeyError):
                pass  # The per-finding validation below reports malformed declarations.
    for index, finding in enumerate(audit.get("findings", [])):
        if index in handled:
            continue
        if not isinstance(finding, dict) or "remove_relationship" not in finding:
            continue
        rule = finding["remove_relationship"]
        try:
            if not isinstance(rule, dict) or set(rule) - {"path", "identity"}:
                raise ValueError("remove_relationship needs path and, for a list member, identity")
            tokens = _tokens(rule["path"])
            old = _at(original, tokens)
            if old is MISSING:
                raise ValueError("unsupported relationship does not exist in the original")
            parent = _at(original, tokens[:-1])
            identity_tokens = None
            if isinstance(parent, list):
                identity_tokens = _tokens(rule.get("identity"))
                if identity_tokens[-1] not in IDENTITY_FIELDS:
                    raise ValueError("list identity must end in a schema identifier field or name")
                identity = _at(old, identity_tokens)
                if not isinstance(identity, str) or not identity.strip():
                    raise ValueError("original list member has no usable declared identity")
            else:
                if "identity" in rule:
                    raise ValueError("identity is only valid for an indexed list member")
            retained = _relationship_after(original, final, tokens, identity_tokens,
                protocol_version=protocol_version, removal_paths=removal_paths) is not MISSING
            if retained:
                findings.append(_problem("unsupported_relationship_retained",
                    "the audit rejected this relationship, but the final record still asserts it; a disclaimer does not remove it",
                    finding=index, path=rule["path"]))
        except (ValueError, TypeError, KeyError) as exc:
            findings.append(_problem("evidence_contract", str(exc), finding=index))
    return findings


def report_payload(text: str, *, protocol_version: int = 1) -> dict:
    """Read one JSON appendix; never infer coverage of free prose."""
    headings = list(re.finditer(r"(?m)^## Evidence assertions[ \t]*$", text))
    if len(headings) != 1:
        raise ValueError("report requires exactly one ## Evidence assertions appendix")
    section = re.split(r"(?m)^## ", text[headings[0].end():], maxsplit=1)[0]
    fence = chr(96) * 3
    match = re.fullmatch(r"\s*" + fence + r"json\s*\n([\s\S]*?)\n" + fence + r"\s*", section)
    if not match:
        raise ValueError("evidence appendix must contain exactly one JSON code block")
    value = load_json(match.group(1))
    keys = {"claims", "source_review"} if protocol_version >= 3 else {"claims"}
    if not isinstance(value, dict) or set(value) != keys or not isinstance(value["claims"], list):
        raise ValueError("evidence appendix must be an object with a claims array")
    return value


def report_assertions(text: str) -> list:
    return report_payload(text)["claims"]


def check_report(text: str, *, artifacts: dict, chunks: dict, protocol_version: int = 1,
                 source_manifest_raw: bytes | str | None = None, project: str | None = None) -> dict:
    authority = _review_authority(protocol_version, source_manifest_raw, project)
    payload = report_payload(text, protocol_version=protocol_version)
    claims = payload["claims"]
    out = {"assertions_checked": len(claims),
           "findings": check_assertions(claims, artifacts=artifacts, chunks=chunks)}
    if protocol_version >= 3:
        from data_sheets_schema import source_review
        review = source_review.check(payload["source_review"], raw=artifacts["final_full"],
                                     artifact="final_full", chunks=chunks, **authority)
        out["source_review_final"] = review
        out["findings"].extend(review["findings"])
    return out


def source_chunks(bundle: Path, manifest: Path) -> tuple[dict, dict]:
    from data_sheets_schema import chunking
    raw, manifest_raw = bundle.read_bytes(), manifest.read_bytes()
    from data_sheets_schema.duplicate_keys import find_duplicate_keys
    if find_duplicate_keys(manifest_raw.decode("utf-8")):
        raise ValueError("chunk manifest has duplicate YAML mapping keys")
    mapping = yaml.safe_load(manifest_raw)
    chunking.validate_manifest_mapping(mapping, raw, mapping["bundle"])
    chunks = {c["id"]: {"source": c["source"], "text": part}
              for c, part in zip(mapping["chunks"], chunking.chunk_texts(raw.decode("utf-8"), mapping["chunks"]))}
    return chunks, {"bundle": hashlib.sha256(raw).hexdigest(),
                    "chunk_manifest": hashlib.sha256(manifest_raw).hexdigest()}


def check_files(*, audit: Path, bundle: Path, manifest: Path,
                artifacts: dict[str, Path], report: Path | None = None,
                protocol_version: int = 1, source_manifest: Path | None = None,
                project: str | None = None, integration_assertions: list | None = None) -> dict:
    """Read exact supplied paths; never discover another run's snapshots."""
    # Check opt-in before reading a new authority path. Chunk manifest and
    # source manifest are distinct inputs and cannot substitute for one another.
    _review_authority(protocol_version, source_manifest, project)
    if integration_assertions is not None and (protocol_version != 7 or type(integration_assertions) is not list):
        raise ValueError('integration assertions require protocol 7 and an explicit array')
    source_raw = source_manifest.read_bytes() if source_manifest is not None else None
    authority = ({"source_manifest_raw": source_raw, "project": project}
                 if protocol_version in (5, 6, 7) else {})
    raw_artifacts = {k: p.read_bytes() for k, p in artifacts.items()}
    texts = {k: raw.decode("utf-8") for k, raw in raw_artifacts.items()}
    chunks, pins = source_chunks(bundle, manifest)
    audit_raw = audit.read_bytes()
    parsed = load_json(audit_raw)
    from data_sheets_schema.api_runner import _audit_shape_problem
    shape = _audit_shape_problem(parsed) if isinstance(parsed, dict) else "audit must be an object"
    if shape:
        raise ValueError(shape)
    out = check_audit(parsed, artifacts={k: v for k, v in texts.items() if k.startswith("original_")},
                      chunks=chunks, protocol_version=protocol_version, **authority)
    if integration_assertions is not None:
        out['findings'] += [{**finding, 'integration_decision': True} for finding in
                           check_assertions(integration_assertions,
                               artifacts={k: v for k, v in texts.items() if k.startswith('original_')},
                               chunks=chunks)]
        out['assertions_checked'] += len(integration_assertions)
        out['integration_assertions_checked'] = len(integration_assertions)
    if source_raw is not None:
        pins["source_manifest"] = hashlib.sha256(source_raw).hexdigest()
    pins["audit"] = hashlib.sha256(audit_raw).hexdigest()
    pins.update({k: hashlib.sha256(raw).hexdigest() for k, raw in raw_artifacts.items()})
    if "original_full" in texts and "final_full" in texts and isinstance(parsed, dict):
        out["findings"] += check_relationship_removals(
            parsed, load_record(texts["original_full"]), load_record(texts["final_full"]),
            protocol_version=protocol_version, original_raw=raw_artifacts["original_full"])
    if report is not None:
        raw = report.read_bytes()
        pins["report"] = hashlib.sha256(raw).hexdigest()
        try:
            report_check = check_report(raw.decode("utf-8"), artifacts=texts, chunks=chunks,
                                        protocol_version=protocol_version, **authority)
            out["assertions_checked"] += report_check["assertions_checked"]
            out["findings"] += report_check["findings"]
            if "source_review_final" in report_check:
                out["source_review_final"] = report_check["source_review_final"]
        except (ValueError, UnicodeError) as exc:
            out["findings"].append(_problem("evidence_contract", str(exc)))
    out["artifact_sha256"] = pins
    out["scope"] = "Declared evidence only; semantic support and omitted claims require independent review."
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-version", type=int, choices=(1, 2, 3, 4, 5, 6, 7), default=1)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--project")
    for name in ("audit", "bundle", "manifest", "original-full"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("original-core", "final-full", "final-core", "report"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args(argv)
    artifacts = {k: getattr(args, k) for k in sorted(ARTIFACTS) if getattr(args, k)}
    try:
        result = check_files(audit=args.audit, bundle=args.bundle, manifest=args.manifest,
                             artifacts=artifacts, report=args.report, protocol_version=args.protocol_version,
                             **({"source_manifest": args.source_manifest, "project": args.project}
                                if args.source_manifest is not None or args.project is not None else {}))
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        result = {"instrument": instrument(args.protocol_version), "checked": False,
                  "findings": [_problem("evidence_inputs_unusable", str(exc))]}
    print(json.dumps(result, indent=2))
    return int(not result["checked"] or bool(result["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
