"""Source-blind grammar for an explicitly selected, unsealed audit draft.

Only candidate bytes enter this checker. A pass does not establish source
coverage, quotation accuracy, hash identity, correct classifications, semantic
support, or actionable relationship removal. No scientific checker is imported.
Reports contain fixed codes and structural locations, never candidate prose or
candidate-supplied object keys. The caller owns draft provenance and sealing.
"""
from __future__ import annotations

import json
import math
import re

INSTRUMENT = "audit_grammar v1"
SCHEMA_VERSION = 1
MAX_BYTES = 64 * 32768
MAX_ERRORS = 20
STATUSES = frozenset({"fact", "planned", "in_progress", "applied", "instruction", "capability"})
IDENTITY_FIELDS = frozenset({"id", "name", "orcid", "doi", "grant_number", "variable_name",
                             "hash", "md5", "sha256", "checksum", "target_dataset"})
METADATA_FIELDS = frozenset({"source_type", "effective_priority", "priority_basis", "captured_at", "superseded_by"})
CLAIM_KEYS = frozenset({"text", "verdict", "attributed_to", "claim_status", "source_status", "evidence", "reason"})


class _JSONProblem(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _JSONProblem("json_duplicate_key")
        result[key] = value
    return result


def _nonfinite(_value):
    raise _JSONProblem("json_nonfinite")


def _load(raw):
    if type(raw) is not bytes:
        raise _JSONProblem("input_bytes_required")
    if len(raw) > MAX_BYTES:
        raise _JSONProblem("input_too_large")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _JSONProblem("json_unicode") from None
    try:
        value = json.loads(text, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except _JSONProblem:
        raise
    except (ValueError, RecursionError):
        raise _JSONProblem("json_syntax") from None
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise _JSONProblem("json_nonfinite")
        elif isinstance(item, str):
            try:
                item.encode("utf-8", errors="strict")
            except UnicodeError:
                raise _JSONProblem("json_unicode") from None
    return value


def _pointer(value):
    return isinstance(value, str) and value.startswith("/") and not re.search(r"~(?![01])", value)


class _Grammar:
    def __init__(self):
        self.errors = []
        self.count = 0

    def problem(self, code, path):
        self.count += 1
        if len(self.errors) < MAX_ERRORS:
            self.errors.append({"code": code, "path": path})

    def result(self):
        return {"instrument": INSTRUMENT, "schema_version": SCHEMA_VERSION,
                "passed": self.count == 0, "error_count": self.count,
                "errors": self.errors, "truncated": self.count > MAX_ERRORS}

    def obj(self, value, required, path, optional=frozenset()):
        if not isinstance(value, dict):
            self.problem("object_required", path)
            return False
        if not required <= set(value) or set(value) - required - optional:
            self.problem("object_keys", path)
        return True

    def array(self, value, path, *, nonempty=False):
        if not isinstance(value, list):
            self.problem("array_required", path)
            return False
        if nonempty and not value:
            self.problem("array_nonempty", path)
        return True

    def text(self, value, path):
        if not isinstance(value, str) or not value.strip():
            self.problem("text_nonempty", path)
            return False
        return True

    def enum(self, value, choices, path):
        if not isinstance(value, str) or value not in choices:
            self.problem("enum_value", path)
            return False
        return True

    def pointer(self, value, path, *, header=False):
        if not _pointer(value) and not (header and value == "@header"):
            self.problem("pointer_syntax", path)
            return False
        return True

    def digest(self, value, path):
        # Lexical shape only. There is deliberately no reference digest.
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            self.problem("digest_syntax", path)

    def document(self, value, path):
        if not self.obj(value, {"source", "chunk", "quote"}, path):
            return
        for field in ("source", "chunk", "quote"):
            self.text(value.get(field), path + "/" + field)

    def artifact(self, value, path):
        if not self.obj(value, {"artifact", "path", "op", "quote"}, path):
            return
        self.enum(value.get("artifact"), {"original_full", "original_core"}, path + "/artifact")
        self.pointer(value.get("path"), path + "/path", header=True)
        self.enum(value.get("op"), {"contains", "lacks"}, path + "/op")
        self.text(value.get("quote"), path + "/quote")

    def provenance(self, value, path):
        if not self.obj(value, {"provenance", "sha256", "source_id", "source", "field", "value"}, path):
            return
        self.enum(value.get("provenance"), {"source_manifest"}, path + "/provenance")
        self.digest(value.get("sha256"), path + "/sha256")
        self.text(value.get("source_id"), path + "/source_id")
        self.text(value.get("source"), path + "/source")
        field = value.get("field")
        if self.enum(field, METADATA_FIELDS, path + "/field"):
            scalar = value.get("value")
            if field == "effective_priority":
                if type(scalar) is not int or scalar <= 0:
                    self.problem("positive_integer_required", path + "/value")
            elif field == "priority_basis":
                self.enum(scalar, {"source_override", "source_type", "unranked"}, path + "/value")
            else:
                self.text(scalar, path + "/value")

    def removal(self, value, path):
        if not isinstance(value, dict):
            self.problem("object_required", path)
            return
        if "match" in value or "original_full_sha256" in value:
            self.obj(value, {"path", "match", "original_full_sha256"}, path)
            self.enum(value.get("match"), {"anonymous_structure_v1"}, path + "/match")
            self.digest(value.get("original_full_sha256"), path + "/original_full_sha256")
        else:
            self.obj(value, {"path"}, path, {"identity"})
            if "identity" in value and self.pointer(value["identity"], path + "/identity"):
                last = value["identity"].rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")
                if last not in IDENTITY_FIELDS:
                    self.problem("identity_field", path + "/identity")
        self.pointer(value.get("path"), path + "/path")

    def claim(self, value, path):
        if not self.obj(value, CLAIM_KEYS, path):
            return False
        self.text(value.get("text"), path + "/text")
        self.text(value.get("reason"), path + "/reason")
        self.enum(value.get("verdict"), {"supported", "revise"}, path + "/verdict")
        self.enum(value.get("claim_status"), STATUSES, path + "/claim_status")
        self.enum(value.get("source_status"), STATUSES | {"unstated"}, path + "/source_status")
        attributed = value.get("attributed_to")
        if self.array(attributed, path + "/attributed_to"):
            seen = set()
            for index, name in enumerate(attributed):
                where = path + f"/attributed_to/{index}"
                if self.text(name, where):
                    if name in seen:
                        self.problem("duplicate_attribution", where)
                    seen.add(name)
        evidence = value.get("evidence")
        if self.array(evidence, path + "/evidence", nonempty=value.get("verdict") == "supported"):
            provenance = any(isinstance(entry, dict) and "provenance" in entry for entry in evidence)
            for index, entry in enumerate(evidence):
                where = path + f"/evidence/{index}"
                if provenance:
                    self.provenance(entry, where)
                else:
                    self.document(entry, where)
            if provenance:
                if attributed != []:
                    self.problem("provenance_attribution", path + "/attributed_to")
                for field in ("claim_status", "source_status"):
                    if value.get(field) != "fact":
                        self.problem("provenance_status", path + "/" + field)
        if value.get("verdict") == "supported" and value.get("claim_status") != value.get("source_status"):
            self.problem("supported_status_mismatch", path)
        return value.get("verdict") == "revise"

    def review(self, value, path):
        revisions = {}
        if not self.obj(value, {"artifact", "sha256", "values"}, path):
            return revisions
        self.enum(value.get("artifact"), {"original_full"}, path + "/artifact")
        self.digest(value.get("sha256"), path + "/sha256")
        rows = value.get("values")
        if not self.array(rows, path + "/values"):
            return revisions
        seen = set()
        for index, row in enumerate(rows):
            where = path + f"/values/{index}"
            if not isinstance(row, dict):
                self.problem("object_required", where)
                continue
            pointer = row.get("path")
            valid_path = self.pointer(pointer, where + "/path")
            if valid_path:
                if pointer in seen:
                    self.problem("duplicate_review_path", where + "/path")
                seen.add(pointer)
            if "metadata_reason" in row:
                self.obj(row, {"path", "metadata_reason"}, where)
                self.text(row.get("metadata_reason"), where + "/metadata_reason")
                continue
            self.obj(row, {"path", "claims"}, where)
            claims = row.get("claims")
            if self.array(claims, where + "/claims", nonempty=True):
                for number, claim in enumerate(claims):
                    if self.claim(claim, where + f"/claims/{number}") and valid_path:
                        revisions[pointer] = where
        return revisions

    def audit(self, value):
        if not self.obj(value, {"findings", "summary", "source_review"}, ""):
            return
        self.text(value.get("summary"), "/summary")
        revisions = self.review(value.get("source_review"), "/source_review")
        linked = set()
        findings = value.get("findings")
        if self.array(findings, "/findings"):
            for index, finding in enumerate(findings):
                path = f"/findings/{index}"
                if not self.obj(finding, {"severity", "record", "slot", "issue", "evidence"}, path,
                                {"review_paths", "remove_relationship"}):
                    continue
                self.enum(finding.get("severity"), {"high", "medium", "low"}, path + "/severity")
                self.enum(finding.get("record"), {"full", "core", "both"}, path + "/record")
                self.text(finding.get("slot"), path + "/slot")
                self.text(finding.get("issue"), path + "/issue")
                evidence = finding.get("evidence")
                if self.array(evidence, path + "/evidence", nonempty=True):
                    for number, entry in enumerate(evidence):
                        where = path + f"/evidence/{number}"
                        if isinstance(entry, dict) and "source" in entry:
                            self.document(entry, where)
                        else:
                            self.artifact(entry, where)
                if "remove_relationship" in finding:
                    self.removal(finding["remove_relationship"], path + "/remove_relationship")
                if "review_paths" in finding:
                    pointers = finding["review_paths"]
                    if self.array(pointers, path + "/review_paths", nonempty=True):
                        for number, pointer in enumerate(pointers):
                            where = path + f"/review_paths/{number}"
                            if self.pointer(pointer, where):
                                if pointer not in revisions:
                                    self.problem("review_path_without_revise", where)
                                else:
                                    linked.add(pointer)
        for pointer, where in revisions.items():
            if pointer not in linked:
                self.problem("revise_without_finding", where)


def check(raw: bytes) -> dict:
    """Check one draft, returning bounded diagnostics without any source access.

    ``error_count`` counts detected grammar errors; ``errors`` holds the first
    twenty. A parse failure yields one fixed code at the root. JSON Pointers in
    this report locate grammar fields inside the draft, never source paths.
    """
    grammar = _Grammar()
    try:
        value = _load(raw)
    except _JSONProblem as error:
        grammar.problem(str(error), "")
    else:
        grammar.audit(value)
    return grammar.result()
