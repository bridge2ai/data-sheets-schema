"""Offline recall of a Phase 3 audit against held-out review observations (#2921).

Reconciliation fixes only what the source audit finds, and nothing measured
what it misses: three direct-arm audits of one bundle, by one model under one
instruction, disagreed on basic defects, while the independent observations kept
out of the audit instruction were never used to score one. A ground-truth entry is one such observation,
located by JSON Pointers into one frozen original and pinned to that original's
sha256. This module validates a file of entries and scores audits of an original
against the entries that name it.

It reads only the bytes the caller passes: no provider, no source validator, no
filesystem search, and it knows no location for ground truth. The audit's shape
is checked by ``audit_grammar.check``, read-only; that grammar, and the audit
batch modules beside it, are not changed here (the closed ``kind`` field on
findings waits for audit28, #2921).

What a hit is — ``HIT_RULE``, provisional until the owner signs it off, and no
report on real audits should be quoted before then: a ground-truth path is hit
when the audit names that pointer, or an ancestor of it on pointer segments, as
a source_review row carrying a revise claim, a finding review_path, or a
finding remove_relationship path. A flag strictly below the path is reported
(``flagged_below``) and is not a hit; supported rows, metadata rows and findings
that name no pointer are never hits.

An audit flag that no entry accounts for is a review candidate, never a false
positive: the reviewed set is small and says nothing about what it did not
review. A report carries entry ids, kinds and pointers, never an observation's
text or any of the audit's prose.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

import yaml

from data_sheets_schema import audit_grammar

INSTRUMENT = "audit_recall v1 (#2921)"
FORMAT = "audit_ground_truth_v1"
#: The closed list the issue proposes plus ``omission`` (#2930). Provisional
#: until the owner signs the list off on #2921, and it must equal the audit
#: grammar's finding ``kind`` enum once that lands under a new protocol version.
KINDS = ("role_placement", "status_scope", "date_scope", "absence_or_self_narration",
         "quotation_fidelity", "identifier_count", "attribution", "omission", "other")
HIT_RULE = {
    "id": "pointer_cover_v1",
    "definition": (
        "A ground-truth path is hit when the audit names that pointer, or an ancestor of it on "
        "JSON Pointer segments, as a source_review row carrying a revise claim, a finding "
        "review_path, or a finding remove_relationship path. A flag strictly below the path is "
        "reported as flagged_below and is not a hit. Supported rows, metadata rows and findings "
        "that name no pointer are never hits."),
    "status": "provisional: requires owner sign-off before any report on real audits (#2921)",
}
MISS_CATEGORIES = ("judged_supported", "flagged_below", "metadata_only", "not_reviewed")
MAX_GROUND_TRUTH_BYTES = 4_194_304
MAX_ORIGINAL_BYTES = 8_388_608
MAX_PROBLEMS = 50
#: End of input in both dialects a ``pattern`` here meets: Python's ``re``, which
#: jsonschema runs with ``re.search``, and ECMA-262, which JSON Schema names. A
#: bare "$" also matches before a final newline in Python, so a hash or id
#: ending in "\n" loaded here, then joined nothing, while any other validator of
#: the committed schema refused it (#3097).
_END = r"(?![\s\S])"
_HEX = "^[0-9a-f]{64}" + _END
_POINTER = "^(/([^/~]|~[01])*)+" + _END
_TEXT = {"type": "string", "pattern": r"\S"}


class GroundTruthError(ValueError):
    """A ground-truth file that cannot be scored against; ``problems`` says why."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(f"{p['at'] or '/'}: {p['problem']}" for p in self.problems))


class AuditRecallError(ValueError):
    """An audit or original that cannot be joined or scored."""


def ground_truth_schema() -> dict:
    """The JSON Schema every ground-truth file satisfies (draft 2020-12).

    ``data/audit_ground_truth/ground_truth.schema.json`` is this, rendered by
    ``schema_text``; a test holds the two equal. Uniqueness of ids, line order,
    line numbers written as integers, calendar dates and relative note paths are
    checked in code as well.
    """
    entry = {
        "type": "object", "additionalProperties": False,
        "required": ["id", "target_original_full_sha256", "paths", "kind", "governing_source",
                     "observation", "reviewer_role", "reviewed_on", "provenance_note", "held_out"],
        "properties": {
            "id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]*" + _END, "maxLength": 128},
            "target_original_full_sha256": {"type": "string", "pattern": _HEX,
                "description": "sha256 of the exact original_full bytes the observation describes."},
            "paths": {"type": "array", "minItems": 1, "uniqueItems": True,
                      "items": {"type": "string", "pattern": _POINTER},
                      "description": "JSON Pointers into that original where the defect sits."},
            "kind": {"enum": list(KINDS)},
            "governing_source": {
                "type": "object", "additionalProperties": False,
                "required": ["bundle_sha256", "lines"],
                "anyOf": [{"required": ["source"]}, {"required": ["chunk"]}],
                "properties": {
                    "bundle_sha256": {"type": "string", "pattern": _HEX,
                        "description": "sha256 of the bundle the lines are numbered in."},
                    "source": {**_TEXT, "description": "Document name, as the bundle's FILE: header gives it."},
                    "chunk": {**_TEXT, "description": "Chunk id from that bundle's chunk manifest."},
                    "lines": {"type": "array", "minItems": 2, "maxItems": 2,
                              "items": {"type": "integer", "minimum": 1},
                              "description": "First and last bundle line, 1-based and inclusive."}}},
            "observation": {**_TEXT, "maxLength": 2000},
            "reviewer_role": {**_TEXT, "maxLength": 200},
            "reviewed_on": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}" + _END},
            "provenance_note": {**_TEXT, "description": "Repository-relative path of the note recording the review."},
            "held_out": {"const": True},
        }}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Held-out audit ground truth",
        "description": ("Independent review observations of frozen originals, kept out of every "
                        "generation and audit instruction, used only to score audit recall (#2921)."),
        "type": "object", "additionalProperties": False,
        "required": ["format", "project", "entries"],
        "properties": {"format": {"const": FORMAT}, "project": _TEXT, "description": _TEXT,
                       "entries": {"type": "array", "minItems": 1, "items": entry}},
    }


def schema_text() -> str:
    return json.dumps(ground_truth_schema(), indent=2, ensure_ascii=False) + "\n"


class _Loader(yaml.SafeLoader):
    """No duplicate or merge keys; dates stay the strings the file wrote."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise GroundTruthError([{"at": "", "problem": "YAML merge keys are not allowed"}])
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise GroundTruthError([{"at": "", "problem": "mapping keys must be strings"}])
            if key in seen:
                raise GroundTruthError([{"at": "", "problem": f"duplicate mapping key {key!r}"}])
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


_Loader.add_constructor("tag:yaml.org,2002:timestamp",
                        lambda loader, node: loader.construct_scalar(node))


def _at(parts):
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def load_ground_truth(raw: bytes) -> dict:
    """Parse and validate one ground-truth file, refusing any incomplete entry.

    Every problem found is reported (up to ``MAX_PROBLEMS``), not the first.
    """
    from jsonschema import Draft202012Validator
    if type(raw) is not bytes:
        raise TypeError("ground truth is read from bytes")
    if len(raw) > MAX_GROUND_TRUTH_BYTES:
        raise GroundTruthError([{"at": "", "problem": "file exceeds the byte bound"}])
    try:
        value = yaml.load(raw.decode("utf-8", errors="strict"), Loader=_Loader)
    except UnicodeError:
        raise GroundTruthError([{"at": "", "problem": "file is not UTF-8"}]) from None
    except yaml.YAMLError as exc:
        raise GroundTruthError([{"at": "", "problem": f"not YAML: {exc.__class__.__name__}"}]) from None
    problems = [{"at": _at(error.absolute_path),
                 # The one anyOf; its default message repeats the whole mapping.
                 "problem": ("must name a source or a chunk" if error.validator == "anyOf"
                             else error.message[:300])}
                for error in sorted(Draft202012Validator(ground_truth_schema()).iter_errors(value),
                                    key=lambda e: (_at(e.absolute_path), e.message))]
    entries = value.get("entries") if isinstance(value, dict) else None
    seen = {}
    for index, entry in enumerate(entries if isinstance(entries, list) else []):
        if not isinstance(entry, dict):
            continue
        where = f"/entries/{index}"
        ident = entry.get("id")
        if isinstance(ident, str):
            if ident in seen:
                problems.append({"at": where + "/id", "problem": f"duplicates the id of /entries/{seen[ident]}"})
            seen.setdefault(ident, index)
        stamp = entry.get("reviewed_on")
        if isinstance(stamp, str):
            try:
                date.fromisoformat(stamp)
            except ValueError:
                problems.append({"at": where + "/reviewed_on", "problem": "not a calendar date"})
        source = entry.get("governing_source")
        lines = source.get("lines") if isinstance(source, dict) else None
        if isinstance(lines, list):
            # The schema's "integer" admits 9.0; an integral float is still an
            # authoring slip here, and must not skip the order check (#3098).
            for number, line in enumerate(lines):
                if type(line) is float and line.is_integer():
                    problems.append({"at": f"{where}/governing_source/lines/{number}",
                                     "problem": "a line number is written as an integer, not a float"})
            if (len(lines) == 2 and all(type(n) in (int, float) for n in lines)
                    and lines[0] > lines[1]):
                problems.append({"at": where + "/governing_source/lines", "problem": "first line is after the last"})
        note = entry.get("provenance_note")
        if isinstance(note, str) and note.strip():
            # Segments as written: PurePosixPath would fold "a/./b" and "a//b".
            if "\\" in note or any(part in ("", ".", "..") for part in note.split("/")):
                problems.append({"at": where + "/provenance_note", "problem": "must be a repository-relative path"})
    if problems:
        raise GroundTruthError(problems[:MAX_PROBLEMS])
    return value


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _below(pointer: str, ancestor: str) -> bool:
    """True when ``pointer`` is strictly inside ``ancestor``, on segment boundaries."""
    return pointer.startswith(ancestor + "/")


def _covers(flag: str, path: str) -> str | None:
    if flag == path:
        return "exact"
    if _below(path, flag):
        return "ancestor"
    return None


def _recall(hits: int, total: int):
    return round(hits / total, 4) if total else "n/a"


def _audit_flags(audit):
    rows = {"revise": [], "supported": [], "metadata": []}
    for row in audit["source_review"]["values"]:
        if "metadata_reason" in row:
            rows["metadata"].append(row["path"])
        elif any(claim["verdict"] == "revise" for claim in row["claims"]):
            rows["revise"].append(row["path"])
        else:
            rows["supported"].append(row["path"])
    flags = [{"pointer": p, "via": "revise_row"} for p in rows["revise"]]
    for number, finding in enumerate(audit["findings"]):
        flags += [{"pointer": p, "via": "review_path", "finding": number}
                  for p in finding.get("review_paths", ())]
        if "remove_relationship" in finding:
            flags.append({"pointer": finding["remove_relationship"]["path"],
                          "via": "remove_relationship", "finding": number})
    return rows, flags


def _judge(path, rows, flags):
    """One ground-truth path against one audit: a hit with its basis, or a miss."""
    basis = [{**flag, "relation": relation} for flag in flags
             if (relation := _covers(flag["pointer"], path))]
    if basis:
        return {"outcome": "hit", "basis": basis}
    over = [{"pointer": p, "relation": r} for p in rows["supported"] if (r := _covers(p, path))]
    below_flags = sorted({flag["pointer"] for flag in flags if _below(flag["pointer"], path)})
    below_supported = sorted(p for p in rows["supported"] if _below(p, path))
    metadata = sorted(p for p in rows["metadata"] if _covers(p, path) or _below(p, path))
    if over:
        return {"outcome": "miss", "miss": "judged_supported", "rows": over}
    if below_flags:
        return {"outcome": "miss", "miss": "flagged_below", "flags": below_flags}
    if below_supported:
        return {"outcome": "miss", "miss": "judged_supported",
                "rows": [{"pointer": p, "relation": "below"} for p in below_supported]}
    if metadata:
        return {"outcome": "miss", "miss": "metadata_only", "rows": metadata}
    return {"outcome": "miss", "miss": "not_reviewed"}


def _populated(original_raw: bytes):
    from data_sheets_schema.source_review import inventory
    try:
        text = original_raw.decode("utf-8", errors="strict")
        return [row["path"] for row in inventory(text, "original_full")["values"]]
    except (UnicodeError, ValueError, yaml.YAMLError) as exc:
        raise AuditRecallError(f"original is not a readable YAML record: {exc.__class__.__name__}") from None


def score(audit_raw: bytes, original_raw: bytes, truth: dict, *,
          replicate: str | None = None, audit_label: str | None = None,
          original_label: str | None = None) -> dict:
    """Score one audit of one original against the entries that name that original.

    The audit must pass ``audit_grammar.check`` and its ``source_review.sha256``
    must equal the original's sha256; either failure is refused rather than
    scored. Entries for other originals are counted and set aside: with none
    applicable, recall is "n/a", not 0.
    """
    if type(audit_raw) is not bytes or type(original_raw) is not bytes:
        raise TypeError("audit and original are read from bytes")
    if len(original_raw) > MAX_ORIGINAL_BYTES:
        raise AuditRecallError("original exceeds the byte bound")
    grammar = audit_grammar.check(audit_raw)
    if not grammar["passed"]:
        codes = ", ".join(sorted({error["code"] for error in grammar["errors"]}))
        raise AuditRecallError(f"audit fails {grammar['instrument']} ({grammar['error_count']} error(s): {codes})")
    audit = json.loads(audit_raw.decode("utf-8"))
    original_sha = _sha(original_raw)
    if audit["source_review"]["sha256"] != original_sha:
        raise AuditRecallError("the audit's source_review.sha256 does not name this original's sha256")
    populated = _populated(original_raw)
    rows, flags = _audit_flags(audit)
    applicable = [e for e in truth["entries"] if e["target_original_full_sha256"] == original_sha]

    paths, entries, used = [], [], set()
    for entry in applicable:
        judged = []
        for path in entry["paths"]:
            verdict = _judge(path, rows, flags)
            used.update(b["pointer"] for b in verdict.get("basis", ()))
            judged.append(verdict)
            paths.append({"entry": entry["id"], "kind": entry["kind"], "path": path,
                          "resolves_in_original": any(p == path or _below(p, path) for p in populated),
                          **verdict})
        hit = sum(v["outcome"] == "hit" for v in judged)
        entries.append({"entry": entry["id"], "kind": entry["kind"], "paths": len(judged), "paths_hit": hit,
                        "status": "all_paths_hit" if hit == len(judged) else "some_paths_hit" if hit else "no_path_hit"})

    by_kind = {}
    for kind in KINDS:
        mine = [p for p in paths if p["kind"] == kind]
        hits = sum(p["outcome"] == "hit" for p in mine)
        found = [e for e in entries if e["kind"] == kind]
        by_kind[kind] = {"paths": len(mine), "hits": hits, "recall": _recall(hits, len(mine)),
                         "entries": len(found),
                         **{status: sum(e["status"] == status for e in found)
                            for status in ("all_paths_hit", "some_paths_hit", "no_path_hit")}}
    hits = sum(p["outcome"] == "hit" for p in paths)
    candidates = {}
    for flag in flags:
        if flag["pointer"] in used:
            continue
        item = candidates.setdefault(flag["pointer"], {"pointer": flag["pointer"], "via": set(), "findings": set(),
            "inside_entries": sorted({p["entry"] for p in paths if _below(flag["pointer"], p["path"])})})
        item["via"].add(flag["via"])
        if "finding" in flag:
            item["findings"].add(flag["finding"])
    other = {}
    for entry in truth["entries"]:
        if entry["target_original_full_sha256"] != original_sha:
            other[entry["target_original_full_sha256"]] = other.get(entry["target_original_full_sha256"], 0) + 1
    return {
        "replicate": replicate,
        "audit": {"path": audit_label, "sha256": _sha(audit_raw), "source_review_sha256": original_sha,
                  "findings": len(audit["findings"]),
                  "rows": {key: len(value) for key, value in rows.items()}},
        "original": {"path": original_label, "sha256": original_sha},
        "audit_grammar": {"instrument": grammar["instrument"], "passed": True},
        "applicable_entries": len(applicable),
        "entries_for_other_originals": dict(sorted(other.items())),
        "status": "scored" if applicable else "no_applicable_entries",
        "totals": {"paths": len(paths), "hits": hits, "recall": _recall(hits, len(paths)),
                   "entries": len(entries)},
        "by_kind": by_kind,
        "entries": entries,
        "paths": paths,
        "misses_judged_supported": [
            {"entry": p["entry"], "kind": p["kind"], "path": p["path"], "rows": p["rows"]}
            for p in paths if p.get("miss") == "judged_supported"],
        "review_candidates": [
            {**item, "via": sorted(item["via"]), "findings": sorted(item["findings"])}
            for _, item in sorted(candidates.items())],
    }


def report(runs, truth: dict, *, ground_truth_raw: bytes, ground_truth_label: str | None = None,
           arm: str | None = None) -> dict:
    """Score each run — a mapping of ``audit``/``original`` bytes, optional
    ``replicate`` and path labels — and pin the instruments and inputs.

    Replicates are reported side by side and never pooled.
    """
    replicates = []
    for number, run in enumerate(runs):
        try:
            replicates.append(score(run["audit"], run["original"], truth, replicate=run.get("replicate"),
                                    audit_label=run.get("audit_path"), original_label=run.get("original_path")))
        except AuditRecallError as exc:
            name = run.get("replicate") or run.get("audit_path") or f"run {number}"
            raise AuditRecallError(f"{name}: {exc}") from None
    return {
        "instrument": INSTRUMENT,
        "instrument_sha256": _sha(Path(__file__).read_bytes()),
        "hit_rule": dict(HIT_RULE),
        "audit_grammar": {"instrument": audit_grammar.INSTRUMENT,
                          "sha256": _sha(Path(audit_grammar.__file__).read_bytes())},
        "ground_truth": {"path": ground_truth_label, "sha256": _sha(ground_truth_raw),
                         "format": truth["format"], "project": truth["project"],
                         "entries": len(truth["entries"])},
        "arm": arm,
        "replicates": replicates,
        "limits": [
            f"Scored against held-out entries for one project ({truth['project']}) from a small reviewed set; "
            "each replicate states its own denominators. This measures which of those observations an audit "
            "missed, not general audit quality.",
            "A review candidate is an audit flag no entry accounts for. It is not a false positive: the "
            "reviewed set says nothing about what it did not review.",
            "Replicates are not pooled. An original no entry names has 0 applicable entries and recall n/a.",
        ],
    }


def render_text(value: dict) -> str:
    """The report as a short summary; the JSON report is the record."""
    rule = value["hit_rule"]
    lines = [f"{value['instrument']}  hit rule {rule['id']} — {rule['status']}",
             f"ground truth {value['ground_truth']['path'] or '(bytes)'} sha256 {value['ground_truth']['sha256'][:12]} "
             f"project {value['ground_truth']['project']}; entries {value['ground_truth']['entries']}"
             + (f"; arm {value['arm']}" if value["arm"] else "")]
    for run in value["replicates"]:
        name = run["replicate"] or "(replicate not stated)"
        lines += ["", f"replicate {name}: audit {run['audit']['sha256'][:12]} on original {run['original']['sha256'][:12]}",
                  f"  applicable entries {run['applicable_entries']}; status {run['status']}"]
        if not run["applicable_entries"]:
            lines.append("  no entry names this original: recall is n/a, not 0")
        lines.append(f"  {'kind':28}{'paths':>6}{'hits':>6}{'recall':>8}{'entries':>9}{'all':>5}{'some':>6}{'none':>6}")
        for kind, row in run["by_kind"].items():
            recall = row["recall"] if row["recall"] == "n/a" else f"{row['recall']:.1%}"
            lines.append(f"  {kind:28}{row['paths']:>6}{row['hits']:>6}{recall:>8}{row['entries']:>9}"
                         f"{row['all_paths_hit']:>5}{row['some_paths_hit']:>6}{row['no_path_hit']:>6}")
        total = run["totals"]
        recall = total["recall"] if total["recall"] == "n/a" else f"{total['recall']:.1%}"
        lines.append(f"  {'total':28}{total['paths']:>6}{total['hits']:>6}{recall:>8}{total['entries']:>9}")
        for miss in run["misses_judged_supported"]:
            rows = ", ".join(f"{r['pointer']} ({r['relation']})" for r in miss["rows"])
            lines.append(f"  miss judged supported: {miss['entry']} [{miss['kind']}] {miss['path']} <- {rows}")
        for item in run["review_candidates"]:
            inside = f" inside {', '.join(item['inside_entries'])}" if item["inside_entries"] else ""
            lines.append(f"  review candidate: {item['pointer']} via {', '.join(item['via'])}{inside}")
    lines += [""] + value["limits"]
    return "\n".join(lines) + "\n"
