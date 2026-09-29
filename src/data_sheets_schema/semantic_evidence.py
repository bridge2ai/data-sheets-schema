"""Check a semantic rating's evidence claims and issue links against its input (#2920).

The version-2.0 semantic contract checks that each piece of evidence is a
non-empty string (`semantic_scope.validate_scope`). It never compares a quote,
a path or a count with the record that was scored, so a rating that gives a
record 38 creators when it has 39 is accepted (#1355). This module is the
check the next contract version will call. Nothing calls it yet and no schema
or agent emits its fields, so the field names below are a draft. They are kept
in one place so that the version bump adopts or renames them together.

Per `unit_scores` row, with paths relative to the resource the row scores:

    cited       [{path, quote?}]   the path resolves to a populated value, and
                                   a quote lies inside one scalar under it
                                   once whitespace is normalised
    absent      [{path}]           the path is missing, null or empty
    counts      [{path, claimed}]  the path resolves to one list of that length
    considered  [path, ...]        declared fields examined and not cited

Per item, `no_issue_reason` says why no lowered issue accounts for a score
below the maximum. Per `semantic_analysis.issues_detected` entry, `item_ids`
names the rubric items the issue concerns and `score_effect` is `lowered` or
`noted_only`.

Errors mark false evidence: a cited path that does not resolve or is empty, a
quote the value does not contain, an "absent" path that is populated, a
miscount, an issue naming an unknown or non-applicable item, and a lowered
issue that names no item scored below its maximum. Warnings mark accounting
gaps: a populated declared field that a below-maximum row neither cites nor
considers, and a below-maximum item that no lowered issue and no reason
explains. The checker reads the rating and never changes a score.

Paths. A path that begins with `/` is a JSON pointer (RFC 6901) and names one
value. Any other path uses the rubric's dotted notation: each segment is a
mapping key, and a list met before the last segment is read element by
element. So `creators.name` reaches every creator's name, while `creators` is
the list itself. A list index is written only in pointer form
(`/creators/0/name`); a dotted segment is always a key, so `creators.0.name`
and `creators[0].name` reach nothing. A value is populated when it is a scalar
other than null or a blank string, or a list or mapping that holds one. A
stated `false` or `0` is populated. A quote is matched against each scalar's
text: a string as written, `true` or `false` for a boolean, and a number as
Python prints it.

Declared fields. A rubric item's `field` names are read as the deterministic
presence instrument reads them, through `evaluation_context.field_values` and
its aliases for names that are not root slots (`format`, `media_type`,
`file_collections.total_bytes`). A name that does not resolve from the
resource root, such as rubric10's bare `confidentiality_level`,
`reidentification_risk` or `is_data_split`, is never populated and never
warns. A cited or considered path accounts for a declared field when one
names the other or a field inside it; list indices are ignored.

Limits. These checks are mechanical. They catch fabricated quotes, false
absences, miscounts and unmentioned declared fields. They do not establish
that a cited value supports the judgement, so an inference drawn against the
record or an overstated reading of a populated field passes them. A count is
the `len()` of one list. A filtered claim such as "38 with an ORCID" cannot be
checked here and must not be written as a count. Call this after
`validate_scope`, which pins the rubric bytes and the applicability context
this module reads.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterator

import yaml

from data_sheets_schema.evaluation_context import FIELD_ALIASES, dataset_units, field_values
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.resources import resource_path

SCORE_EFFECTS = frozenset({"lowered", "noted_only"})
_INDEX = re.compile(r"0|[1-9][0-9]*")


@dataclass(frozen=True)
class EvidenceFinding:
    """One evaluator-evidence problem, located in the rating and its input."""

    severity: str             # "error" | "warning"
    code: str
    item_id: str | None
    path: str | None          # the input path at issue, relative to `unit`
    message: str
    unit: str | None = None   # the resource the row scores: "#", "#/resources/0"
    issue: int | None = None  # index into semantic_analysis.issues_detected


@dataclass(frozen=True)
class EvidenceReport:
    findings: tuple[EvidenceFinding, ...]

    @property
    def errors(self) -> tuple[EvidenceFinding, ...]:
        return tuple(f for f in self.findings if f.severity == "error")

    @property
    def warnings(self) -> tuple[EvidenceFinding, ...]:
        return tuple(f for f in self.findings if f.severity == "warning")

    @property
    def passed(self) -> bool:
        return not self.errors


def check_evidence(result: dict, document: dict, rubric_name: str) -> EvidenceReport:
    """Report where a rating's evidence or issue links contradict its input.

    Raises ValueError, as `validate_scope` does, when the rubric is not a
    general-context semantic rubric, the rating declares another rubric, or its
    applicability context or input document is malformed. A malformed evidence
    list, evidence entry or issue entry is reported as a finding rather than
    raised; the rating's item structure is `validate_scope`'s to refuse.
    """
    rubric_name = rubric_name.removesuffix("-semantic")
    if rubric_name not in {"rubric10", "rubric20"}:
        raise ValueError(f"unknown general-context semantic rubric: {rubric_name}")
    declared = str(result.get("rubric", rubric_name)).removesuffix("-semantic")
    if declared != rubric_name:
        raise ValueError(f"the rating declares {declared}, not {rubric_name}")
    specification = yaml.safe_load(resource_path(f"data/rubric/{rubric_name}.txt").read_bytes())
    rules = evaluation_contract(rubric_name, specification, result.get("applicability_context"),
                                {"id": "evidence-contract"})["items"]
    fields = _declared_fields(rubric_name, specification)
    units = dict(dataset_units(document))
    findings: list[EvidenceFinding] = []
    below: dict[str, dict] = {}
    for key, item in _items(result, rubric_name):
        rule = rules.get(key)
        applicable = bool(rule and rule["applicable"])
        maximum = rule["fixed_max_score"] if rule else None
        if applicable and _below(item.get("score"), maximum):
            below[key] = item
        rows = item.get("unit_scores")
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            unit_path = row.get("path")
            unit = units.get(unit_path) if isinstance(unit_path, str) else None
            if unit is None:
                findings.append(EvidenceFinding(
                    "error", "unknown_unit", key, None,
                    f"{key}: {unit_path!r} is not a resource of the input", unit=str(unit_path)))
                continue
            findings.extend(_row_findings(key, unit_path, unit, row))
            if applicable and _below(row.get("score"), maximum):
                findings.extend(_coverage(key, unit_path, unit, row, fields.get(key, ())))
    findings.extend(_issue_findings(result, rules, below))
    return EvidenceReport(tuple(findings))


def _declared_fields(rubric_name: str, specification: dict) -> dict[str, tuple[str, ...]]:
    """Item keys derived as `judge_contract.evaluation_contract` derives them."""
    if rubric_name == "rubric10":
        entries = [(f"E{element['id']}.{index}", item)
                   for element in specification["d4d_complex_proxy_rubric"]["rubric"]
                   for index, item in enumerate(element["sub_elements"], 1)]
    else:
        entries = [(f"Q{item['id']}", item) for item in specification["d4d_evaluation_rubric"]["rubric"]]
    declared = {}
    for key, item in entries:
        names = item.get("field") or ()
        declared[key] = (names,) if isinstance(names, str) else tuple(names)
    return declared


def _items(result: dict, rubric_name: str) -> Iterator[tuple[str, dict]]:
    groups = result.get("elements" if rubric_name == "rubric10" else "categories")
    for group in groups if isinstance(groups, list) else []:
        items = group.get("sub_elements" if rubric_name == "rubric10" else "questions") \
            if isinstance(group, dict) else None
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict):
                key = item.get("item_id") if rubric_name == "rubric10" else f"Q{item.get('id')}"
                # A key that is not a string names no rubric item and cannot index one.
                yield (key if isinstance(key, str) else None), item


def _below(score: Any, maximum: int | None) -> bool:
    return (maximum is not None and isinstance(score, (int, float))
            and not isinstance(score, bool) and score < maximum)


def _populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_populated(child) for child in value.values())
    if isinstance(value, list):
        return any(_populated(child) for child in value)
    return True


def _escape(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def _resolve(unit: dict, path: str) -> list[tuple[str, Any]]:
    """Every (pointer, value) a path reaches in the unit; empty when it reaches none."""
    if path.startswith("/"):
        node = unit
        for raw in path[1:].split("/"):
            token = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and token in node:
                node = node[token]
            elif isinstance(node, list) and _INDEX.fullmatch(token) and int(token) < len(node):
                node = node[int(token)]
            else:
                return []
        return [(path, node)]

    def walk(node, parts, pointer):
        if not parts:
            return [(pointer, node)]
        if isinstance(node, list):
            return [hit for index, child in enumerate(node) for hit in walk(child, parts, f"{pointer}/{index}")]
        if isinstance(node, dict) and parts[0] in node:
            return walk(node[parts[0]], parts[1:], f"{pointer}/{_escape(parts[0])}")
        return []

    return walk(unit, path.split("."), "")


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _scalars(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for child in value.values():
            yield from _scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from _scalars(child)
    elif isinstance(value, bool):
        yield "true" if value else "false"
    elif value is not None:
        yield str(value)


def _entry_path(entry: Any) -> str | None:
    path = entry.get("path") if isinstance(entry, dict) else None
    return path if isinstance(path, str) and path.strip() else None


def _row_findings(key: str, unit_path: str, unit: dict, row: dict) -> Iterator[EvidenceFinding]:
    def error(code, path, message):
        return EvidenceFinding("error", code, key, path, f"{key} {unit_path}: {message}", unit=unit_path)

    lists = {}
    for name in ("cited", "absent", "counts", "considered"):
        entries = row.get(name, [])
        if isinstance(entries, list):
            lists[name] = entries
        else:
            lists[name] = []
            yield error("malformed_evidence", None, f"{name} must be a list")

    for index, entry in enumerate(lists["cited"]):
        path = _entry_path(entry)
        if path is None:
            yield error("malformed_evidence", None, f"cited[{index}] needs a non-empty path")
            continue
        hits = _resolve(unit, path)
        if not hits:
            yield error("cited_path_unresolved", path, f"cites {path}, which the input does not contain")
            continue
        if not any(_populated(value) for _, value in hits):
            yield error("cited_path_empty", path, f"cites {path}, which is null or empty in the input")
            continue
        if "quote" not in entry:
            continue
        quote = entry["quote"]
        if not isinstance(quote, str) or not quote.strip():
            yield error("malformed_evidence", path, f"cited[{index}] quote must be a non-blank string")
        elif not any(_normalise(quote) in _normalise(text) for _, value in hits for text in _scalars(value)):
            yield error("quote_not_found", path, f"quotes {quote!r}, which no value at {path} contains")

    for index, entry in enumerate(lists["absent"]):
        path = _entry_path(entry)
        if path is None:
            yield error("malformed_evidence", None, f"absent[{index}] needs a non-empty path")
            continue
        populated = [pointer for pointer, value in _resolve(unit, path) if _populated(value)]
        if populated:
            yield error("absent_path_populated", path,
                        f"claims {path} is absent, but the input populates {populated[0]}")

    for index, entry in enumerate(lists["counts"]):
        path = _entry_path(entry)
        claimed = entry.get("claimed") if isinstance(entry, dict) else None
        if path is None or not isinstance(claimed, int) or isinstance(claimed, bool) or claimed < 0:
            yield error("malformed_evidence", path, f"counts[{index}] needs a path and a non-negative integer claim")
            continue
        hits = _resolve(unit, path)
        if not hits:
            yield error("count_path_unresolved", path, f"counts {path}, which the input does not contain")
        elif len(hits) != 1 or not isinstance(hits[0][1], list):
            yield error("count_path_not_list", path, f"counts {path}, which is not one list in the input")
        elif len(hits[0][1]) != claimed:
            yield error("count_mismatch", path,
                        f"counts {path} as {claimed}; the input has {len(hits[0][1])}")

    for index, entry in enumerate(lists["considered"]):
        if not isinstance(entry, str) or not entry.strip():
            yield error("malformed_evidence", None, f"considered[{index}] must be a non-empty path")


def _name_parts(path: str) -> list[str]:
    """A cited path as field names: pointer escapes undone, list indices dropped."""
    if path.startswith("/"):
        parts = [raw.replace("~1", "/").replace("~0", "~") for raw in path[1:].split("/")]
        return [part for part in parts if not _INDEX.fullmatch(part)]
    return path.split(".")


def _coverage(key: str, unit_path: str, unit: dict, row: dict,
              declared: tuple[str, ...]) -> Iterator[EvidenceFinding]:
    """Warn on each populated declared field a deduction does not account for."""
    cited = row.get("cited") if isinstance(row.get("cited"), list) else []
    considered = row.get("considered") if isinstance(row.get("considered"), list) else []
    named = [_name_parts(path) for path in
             [_entry_path(entry) for entry in cited]
             + [entry for entry in considered if isinstance(entry, str) and entry.strip()]
             if path is not None]
    named = [parts for parts in named if parts]
    for name in declared:
        if not any(_populated(value) for _, value in field_values(unit, name)):
            continue
        spellings = [name.split("."), *(alias.split(".") for alias in FIELD_ALIASES.get(name, ()))]
        if not any(parts[:len(spelling)] == spelling[:len(parts)]
                   for parts in named for spelling in spellings):
            yield EvidenceFinding(
                "warning", "uncovered_populated_field", key, name,
                f"{key} {unit_path}: scored below its maximum without citing or considering "
                f"{name}, which the input populates", unit=unit_path)


def _issue_findings(result: dict, rules: dict, below: dict[str, dict]) -> Iterator[EvidenceFinding]:
    analysis = result.get("semantic_analysis")
    issues = analysis.get("issues_detected") if isinstance(analysis, dict) else None
    if issues is not None and not isinstance(issues, list):
        yield EvidenceFinding("error", "malformed_issue", None, None, "issues_detected must be a list")
    lowered: set[str] = set()
    for index, issue in enumerate(issues if isinstance(issues, list) else []):
        ids = issue.get("item_ids", []) if isinstance(issue, dict) else None
        effect = issue.get("score_effect") if isinstance(issue, dict) else None
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids) or (
                effect is not None and (not isinstance(effect, str) or effect not in SCORE_EFFECTS)):
            yield EvidenceFinding("error", "malformed_issue", None, None,
                                  f"issue {index}: item_ids must be a list of item ids and score_effect "
                                  f"one of {', '.join(sorted(SCORE_EFFECTS))}", issue=index)
            continue
        for item_id in ids:
            if item_id not in rules:
                yield EvidenceFinding("error", "unknown_item_id", item_id, None,
                                      f"issue {index} names {item_id}, which the rubric does not define",
                                      issue=index)
            elif not rules[item_id]["applicable"]:
                yield EvidenceFinding("error", "non_applicable_item_id", item_id, None,
                                      f"issue {index} names {item_id}, which is not applicable in this context",
                                      issue=index)
        if effect == "lowered":
            deducted = [item_id for item_id in ids if item_id in below]
            lowered.update(deducted)
            if not deducted:
                why = (f"none of {', '.join(ids)} is scored below its maximum" if ids
                       else "it names no item")
                yield EvidenceFinding("error", "lowered_issue_without_deduction", ids[0] if ids else None, None,
                                      f"issue {index} is marked lowered, but {why}", issue=index)
    for key, item in below.items():
        reason = item.get("no_issue_reason")
        if key not in lowered and not (isinstance(reason, str) and reason.strip()):
            yield EvidenceFinding("warning", "deduction_without_linked_issue", key, None,
                                  f"{key} is scored below its maximum, but no lowered issue names it "
                                  "and it gives no no_issue_reason")
