"""Check a semantic rating's evidence claims and issue links against its input (#2920).

The version-2.0 semantic contract checks that each piece of evidence is a
non-empty string (`semantic_scope.validate_scope`). It never compares a quote,
a path or a count with the record that was scored, so a rating that gives a
record 38 creators when it has 39 is accepted (#1355). Semantic version 3
calls this checker after scope, context and instrument validation. Historical
version 1/2 acceptance is not retroactively changed.

Per `unit_scores` row, with paths relative to the resource the row scores:

    cited       [{path, quote?}]   the path resolves to a populated value, and
                                   a quote lies inside one scalar under it
                                   once whitespace is normalised
    absent      [{path}]           the path is missing, null or empty
    counts      [{path, claimed}]  the path names one list, of that length
    considered  [path, ...]        declared fields examined and not cited

Per item, `no_issue_reason` says why no lowered issue accounts for a score
below the maximum. Per `semantic_analysis.issues_detected` entry, `item_ids`
names the rubric items the issue concerns and `score_effect` is `lowered` or
`noted_only`.

Errors mark false or unreadable evidence: a path outside the grammar below
or a pointer that applies a key to a list, a cited path that does not
resolve or is empty, a quote the value does not contain, an "absent" path
that is populated, a miscount, an issue naming an unknown or non-applicable
item, and a lowered issue that names no item scored below its maximum.
Warnings mark accounting gaps: a populated declared field that a
below-maximum row neither cites nor considers, and a below-maximum item that
no lowered issue and no reason explains. The checker reads the rating and
never changes a score.

Paths. A path that begins with `/` is a JSON pointer (RFC 6901) and names one
value. Its tokens are keys or list indices; none is empty or padded with
whitespace, and `~` appears only in the escapes `~0` and `~1`. Any other path
uses the rubric's dotted notation. Each segment is a lowercase snake_case key,
as every schema slot and rubric field name is, and a list met before the last
segment is read element by element. So `creators.name` reaches every
creator's name, while `creators` is the list itself. A list index is written
only in pointer form (`/creators/0/name`), and so is a key that is not a
snake_case name, such as the few model-written `DOI` keys. Any other spelling
is a `malformed_path` error in every list, never a path that reaches nothing:
`#/creators` (a pointer begins with `/` and is relative to the row's
resource), `creators/0`, `creators.0.name`, `creators[0].name`, `Creators`,
and a path with a stray space. So is a pointer that meets a list and applies
to it a token that is not an index without leading zeros: `/creators/name`,
`/creators/01/name`, `/creators/-`. RFC 6901 gives such a token no element to
name, and the dotted `creators.name` is the spelling that reads across the
list (#3149). This is the one malformation the input decides, so it is found
by walking the pointer. Otherwise a pointer reaches nothing where a mapping
lacks its key, a canonical index is past the end of its list, or a token
would descend into a scalar, as a dotted path reaches nothing where a
mapping lacks its segment or the walk meets a scalar. This matters most for
`absent`, where a path that reaches nothing is a true absence. A value is
populated when it is a scalar other than null or a blank string, or a list
or mapping that holds one. A stated `false` or `0` is populated.

Quotes. A quote is matched, with whitespace normalised, against each scalar
under the path. It may be a substring of a string as written, of `true` or
`false` for a boolean, of a date or timestamp in ISO 8601 form or as Python
prints it, and of a number as Python prints it. The parsed input no longer
holds the text the record wrote, so a quote of a whole non-string scalar also
matches when YAML reads the quote as that same value. A timestamp must keep
its UTC offset. So `2026-05-01T00:00:00Z`, `yes` and `1.10` match the values a
record wrote that way. A quote YAML cannot read as a value, such as the
impossible date `2026-02-30`, matches only as text. Whitespace is normalised
on both sides, so a single-spaced quote matches a value written across lines,
as a literal block scalar is.

Declared fields. A rubric item's `field` names are read as the deterministic
presence instrument reads them, through `evaluation_context.field_values` and
its aliases for names that are not root slots (`format`, `media_type`,
`file_collections.total_bytes`). A name that does not resolve from the
resource root, such as rubric10's bare `confidentiality_level`,
`reidentification_risk` or `is_data_split`, is never populated and never
warns. A cited or considered path accounts for a declared field when it
reaches a location where the input populates that field, a value inside one,
or a container of one.

Aliased names. A dotted path that is a key of `FIELD_ALIASES` is read the
same way in every list, not only for coverage: it names what its own
spelling reaches and every other location `field_values` reads for it that
holds a value. So the declared name, as the rubric writes it, names all of
the field's locations. `absent: format` on a record whose formats sit under
`distribution_formats` is `absent_path_populated`, and `cited: format`
resolves there (#3148). A pointer names one value and is never read through
an alias, and an alias spelled out, such as `distribution_formats.format`,
is an ordinary dotted path. A container an alias passes through accounts
for nothing where it holds no value: citing `file_collections` does not
account for `format`, whose aliases include
`file_collections.resources.format`, when no file collection holds a format.

Limits. These checks are mechanical. They catch fabricated quotes, false
absences, miscounts and unmentioned declared fields. They do not establish
that a cited value supports the judgement, so an inference drawn against the
record, or a misreading of a field the row cites, passes them. #1355's Q13
deduction cited the `version_access` fields it misread. Version 3 rejects
absence names absent from its frozen schema/rubric name authority (#3027,
#3196), including `was_generated_by`: that old acceptance example was not a
declared field and is replaced by `errata`. A literal pointer token such as
`/version_access.version_details` is one unknown key, not a nested path.
The authority checks names, not class/range relationships: a path composed
entirely of declared names can still describe the wrong relationship. Legacy
version 2 keeps its original missing-key behavior. A count is the `len()` of
one list: the path, read as above, must name exactly one location, and it
must be a list. So an aliased name is counted only where its own spelling
holds every populated location, as `distribution_formats` does on a full
record; where an alias holds one too, the list is counted by pointer. A
filtered claim such as "38 with an ORCID" cannot be checked here and must
not be written as a count. Call this after `validate_scope`, which pins the
rubric bytes and the applicability context this module reads.
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime
import re
from typing import Any, Iterator

import yaml

from data_sheets_schema.evaluation_context import FIELD_ALIASES, dataset_units, field_values
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.resources import resource_path

SCORE_EFFECTS = frozenset({"lowered", "noted_only"})
ISSUE_TYPES = frozenset({"completeness", "consistency", "content_accuracy", "correctness",
                         "semantic_understanding"})
ISSUE_CATEGORIES = frozenset({
    "persistent_identifier", "consent_ethics", "scope_drift", "temporal_version",
    "source_conflict", "privacy_regulatory", "license_use_terms", "format_access",
    "variables_metadata", "processing_provenance", "count_size", "attribution",
    "bias_quality", "other",
})
_INDEX = re.compile(r"0|[1-9][0-9]*")
_NAME = re.compile(r"[a-z_][a-z0-9_]*")
_BAD_ESCAPE = re.compile(r"~(?![01])")


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


class EvidenceValidationError(ValueError):
    """An input-checked rating failed acceptance; retain its structured findings."""

    def __init__(self, report: EvidenceReport):
        self.report = report
        super().__init__("\n".join(f"{finding.code}: {finding.message}" for finding in report.errors))


def check_evidence(result: dict, document: dict, rubric_name: str) -> EvidenceReport:
    """Report where a rating's evidence or issue links contradict its input.

    Raises ValueError, as `validate_scope` does, when the rubric is not a
    general-context semantic rubric, the rating declares another rubric, or its
    applicability context or input document is malformed. A malformed evidence
    list, evidence entry or issue entry is reported as a finding rather than
    raised, and so is a quote YAML cannot read, such as an impossible date; the
    rating's item structure is `validate_scope`'s to refuse.
    """
    rubric_name, instrument, specification, rules = _issue_contract(result, rubric_name)
    fields = _declared_fields(rubric_name, specification)
    units = dict(dataset_units(document))
    absence_names = None
    if instrument is not None and instrument.evidence_authority_path is not None:
        from data_sheets_schema.semantic_evidence_authority import verify_authority
        absence_names = verify_authority(result.get("metadata") or {})
    findings: list[EvidenceFinding] = []
    for key, item in _items(result, rubric_name):
        rule = rules.get(key)
        applicable = bool(rule and rule["applicable"])
        maximum = rule["fixed_max_score"] if rule else None
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
            findings.extend(_row_findings(key, unit_path, unit, row, absence_names))
            if applicable and _below(row.get("score"), maximum):
                if absence_names is not None and not any(
                        isinstance(row.get(name), list) and row[name]
                        for name in ("cited", "absent", "counts", "considered")):
                    findings.append(EvidenceFinding(
                        "error", "missing_structured_evidence", key, None,
                        f"{key} {unit_path}: a deduction needs a cited, absent, counted or considered path",
                        unit=unit_path))
                findings.extend(_coverage(key, unit_path, unit, row, fields.get(key, ())))
    findings.extend(_issue_report(result, rubric_name, rules).findings)
    return EvidenceReport(tuple(findings))


def _issue_contract(result: dict, rubric_name: str):
    rubric_name = rubric_name.removesuffix("-semantic")
    if rubric_name not in {"rubric10", "rubric20"}:
        raise ValueError(f"unknown general-context semantic rubric: {rubric_name}")
    declared = str(result.get("rubric", rubric_name)).removesuffix("-semantic")
    if declared != rubric_name:
        raise ValueError(f"the rating declares {declared}, not {rubric_name}")
    from data_sheets_schema.semantic_instrument import select_semantic_instrument
    version = result.get("version")
    instrument = (select_semantic_instrument(rubric_name, version)
                  if version in ("2.0", "3.0", "4.0") else None)
    rubric_path = instrument.rubric_path if instrument else f"data/rubric/{rubric_name}.txt"
    specification = yaml.safe_load(resource_path(rubric_path).read_bytes())
    rules = evaluation_contract(rubric_name, specification, result.get("applicability_context"),
                                {"id": "evidence-contract"})["items"]
    return rubric_name, instrument, specification, rules


def _issue_report(result: dict, rubric_name: str, rules: dict) -> EvidenceReport:
    below = {key: item for key, item in _items(result, rubric_name)
             if rules.get(key, {}).get("applicable")
             and _below(item.get("score"), rules[key]["fixed_max_score"])}
    return EvidenceReport(tuple(_issue_findings(result, rules, below)))


def check_issue_links(result: dict, rubric_name: str) -> EvidenceReport:
    """Check issue-to-item links without claiming input evidence was checked.

    Call after schema/scope validation. This uses the same applicability and
    below-maximum rules, finding content and order as ``check_evidence``.
    Absence, quotation, count and field-coverage checks require the actual input
    and remain the responsibility of ``check_evidence``.
    """
    rubric_name, _, _, rules = _issue_contract(result, rubric_name)
    return _issue_report(result, rubric_name, rules)


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


def _follow(unit: dict, path: str) -> tuple[list[tuple[str, Any]], str | None]:
    """The (pointer, value) a JSON pointer names, and why it can name none.

    A pointer names nothing where a mapping lacks its key, a canonical index
    is past the end of its list, or a token would descend into a scalar; that
    is a true absence. A token met on a list that is not an index without
    leading zeros names no element at all under RFC 6901, so the second value
    says why, and every list reports it rather than `absent` reading it as
    missing (#3149).
    """
    node, walked = unit, ""
    for raw in path[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            if not _INDEX.fullmatch(token):
                return [], (f"applies the token {token!r} to the list at {walked}; a pointer token on a "
                            "list is an index without leading zeros, and dotted notation reads across a list")
            if int(token) >= len(node):
                return [], None
            node = node[int(token)]
        elif isinstance(node, dict) and token in node:
            node = node[token]
        else:
            return [], None
        walked += f"/{raw}"
    return [(path, node)], None


def _resolve(unit: dict, path: str) -> list[tuple[str, Any]]:
    """Every (pointer, value) a path's own spelling reaches in the unit; empty when it reaches none."""
    if path.startswith("/"):
        return _follow(unit, path)[0]

    def walk(node, parts, pointer):
        if not parts:
            return [(pointer, node)]
        if isinstance(node, list):
            return [hit for index, child in enumerate(node) for hit in walk(child, parts, f"{pointer}/{index}")]
        if isinstance(node, dict) and parts[0] in node:
            return walk(node[parts[0]], parts[1:], f"{pointer}/{_escape(parts[0])}")
        return []

    return walk(unit, path.split("."), "")


def _parts(pointer: str) -> list[str]:
    return pointer.split("/")[1:]


def _within(pointer: str, base: str) -> bool:
    """Whether a pointer is the base or a location inside it."""
    return _parts(pointer)[:len(_parts(base))] == _parts(base)


def _locations(unit: dict, path: str) -> list[tuple[str, Any]]:
    """Every (pointer, value) a path names, read as the coverage check reads a declared name.

    A dotted key of `FIELD_ALIASES` names what its own spelling reaches and
    every other populated location `field_values` reads for it. Reading it
    literally here while coverage read it through the aliases let `absent:
    format` pass on a record whose formats sit under `distribution_formats`,
    and made `cited: format` an unresolved path (#3148). What the spelling
    reaches is kept whole, so a list stays one list for `counts`.
    """
    hits = _resolve(unit, path)
    if path not in FIELD_ALIASES:  # no key begins with "/", so a pointer is read as written
        return hits
    return hits + [(pointer, value) for pointer, value in field_values(unit, path)
                   if _populated(value) and not any(_within(pointer, base) for base, _ in hits)]


def _path_problem(path: str) -> str | None:
    """Why a path is outside the grammar in the module docstring; None when it is inside."""
    if path != path.strip():
        return "has leading or trailing whitespace"
    if path.startswith("/"):
        tokens = path[1:].split("/")
        if any(not token or token != token.strip() for token in tokens):
            return "has an empty or whitespace-padded pointer token"
        if _BAD_ESCAPE.search(path):
            return "has a ~ that is neither the pointer escape ~0 nor ~1"
        return None
    if path.startswith("#"):
        return "begins with #; a pointer begins with / and is relative to the row's resource"
    for segment in path.split("."):
        if _NAME.fullmatch(segment):
            continue
        if "/" in segment:
            return "uses / in dotted notation; a pointer begins with /"
        if "[" in segment or "]" in segment or re.fullmatch(r"[0-9]+", segment):
            return "indexes a list in dotted notation; an index is written only in pointer form"
        return f"has the segment {segment!r}; a key that is not lowercase snake_case is written in pointer form"
    return None


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _scalars(value: Any) -> Iterator[Any]:
    """Every non-null scalar under a value."""
    if isinstance(value, dict):
        for child in value.values():
            yield from _scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from _scalars(child)
    elif value is not None:
        yield value


def _texts(scalar: Any) -> tuple[str, ...]:
    """The renderings of a non-string scalar that a partial quote may lie inside."""
    if isinstance(scalar, bool):
        return ("true" if scalar else "false",)
    if isinstance(scalar, datetime.datetime):
        return (scalar.isoformat(), str(scalar))
    if isinstance(scalar, datetime.date):
        return (scalar.isoformat(),)
    return (str(scalar),)


def _same_value(read: Any, scalar: Any) -> bool:
    """Whether YAML's reading of a whole quote is this non-string scalar."""
    if isinstance(scalar, bool) or isinstance(read, bool):
        return read is scalar
    if isinstance(scalar, (int, float)):
        return isinstance(read, (int, float)) and read == scalar
    if isinstance(scalar, datetime.datetime):
        return (isinstance(read, datetime.datetime) and read == scalar
                and read.utcoffset() == scalar.utcoffset())
    if isinstance(scalar, datetime.date):
        return type(read) is datetime.date and read == scalar
    return False


def _yaml_reading(quote: str) -> Any:
    """The value YAML reads a whole quote as; None when it reads none.

    Only `yaml.YAMLError` is PyYAML's own exception. Its constructors raise
    plain ones for text that matches a pattern but builds no value: ValueError
    for an impossible date or time (`2026-02-30`, `2026-01-01T25:00:00Z`) or
    `!!int abc`, AttributeError for `!!timestamp x`, KeyError for
    `!!bool maybe`, and RecursionError for deeply nested brackets. Every one
    means the quote is not a value the record could hold, so a misquoted
    date is a `quote_not_found` finding, not an exception out of
    `check_evidence` that a caller would take for a malformed input (#3072).
    """
    try:
        return yaml.safe_load(quote)
    except Exception:
        return None


def _quote_found(quote: str, values: list[Any]) -> bool:
    wanted = _normalise(quote)
    read, parsed = None, False
    for scalar in (s for value in values for s in _scalars(value)):
        if isinstance(scalar, str):
            if wanted in _normalise(scalar):
                return True
            continue
        if any(wanted in text for text in _texts(scalar)):
            return True
        if not parsed:
            read = _yaml_reading(wanted)
            parsed = True
        if read is not None and _same_value(read, scalar):
            return True
    return False


def _entry_path(entry: Any) -> str | None:
    path = entry.get("path") if isinstance(entry, dict) else None
    return path if isinstance(path, str) and path.strip() else None


def _unknown_absence_name(unit: dict, path: str, names: frozenset[str]) -> str | None:
    """Check even tokens after a missing parent; a typo is not an absence.

    Numeric tokens are indices on lists, not names. After a missing parent we
    cannot establish its class, so canonical indices remain possible. A known
    mapping never treats an undeclared numeric key as a list index.
    """
    if not path.startswith("/"):
        return next((part for part in path.split(".") if part not in names), None)
    unknown = object()
    node = unit
    for raw in path[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        index = _INDEX.fullmatch(token)
        if isinstance(node, list) and index:
            node = node[int(token)] if int(token) < len(node) else unknown
        else:
            if token not in names and not (node is unknown and index):
                return token
            node = node.get(token, unknown) if isinstance(node, dict) else unknown
    return None


def _row_findings(key: str, unit_path: str, unit: dict, row: dict,
                  absence_names: frozenset[str] | None = None) -> Iterator[EvidenceFinding]:
    def error(code, path, message):
        return EvidenceFinding("error", code, key, path, f"{key} {unit_path}: {message}", unit=unit_path)

    def malformed(name, index, path):
        # A path outside the grammar reaches nothing, and under `absent`
        # reaching nothing would pass as a true absence (#3017). So does a
        # pointer that applies a key token to a list, which only the input
        # can show (#3149).
        problem = _path_problem(path) or (_follow(unit, path)[1] if path.startswith("/") else None)
        return None if problem is None else error("malformed_path", path, f"{name}[{index}] path {path!r} {problem}")

    lists = {}
    for name in ("cited", "absent", "counts", "considered"):
        entries = row.get(name, [] if absence_names is None else None)
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
        if (finding := malformed("cited", index, path)) is not None:
            yield finding
            continue
        hits = _locations(unit, path)
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
        elif not _quote_found(quote, [value for _, value in hits]):
            yield error("quote_not_found", path, f"quotes {quote!r}, which no value at {path} contains")

    for index, entry in enumerate(lists["absent"]):
        path = _entry_path(entry)
        if path is None:
            yield error("malformed_evidence", None, f"absent[{index}] needs a non-empty path")
            continue
        if (finding := malformed("absent", index, path)) is not None:
            yield finding
            continue
        if absence_names is not None:
            unknown = _unknown_absence_name(unit, path, absence_names)
            if unknown is not None:
                yield error("unknown_absence_name", path,
                            f"absent[{index}] path {path!r} names undeclared field {unknown!r}")
                continue
        populated = [pointer for pointer, value in _locations(unit, path) if _populated(value)]
        if populated:
            yield error("absent_path_populated", path,
                        f"claims {path} is absent, but the input populates {populated[0]}")

    for index, entry in enumerate(lists["counts"]):
        path = _entry_path(entry)
        claimed = entry.get("claimed") if isinstance(entry, dict) else None
        if path is None or not isinstance(claimed, int) or isinstance(claimed, bool) or claimed < 0:
            yield error("malformed_evidence", path, f"counts[{index}] needs a path and a non-negative integer claim")
            continue
        if (finding := malformed("counts", index, path)) is not None:
            yield finding
            continue
        hits = _locations(unit, path)
        if not hits:
            yield error("count_path_unresolved", path, f"counts {path}, which the input does not contain")
        elif len(hits) != 1:
            yield error("count_path_not_list", path,
                        f"counts {path}, which names {len(hits)} locations in the input, not one list; "
                        f"the first is {hits[0][0]}")
        elif not isinstance(hits[0][1], list):
            yield error("count_path_not_list", path, f"counts {path}, which is not one list in the input")
        elif len(hits[0][1]) != claimed:
            yield error("count_mismatch", path,
                        f"counts {path} as {claimed}; the input has {len(hits[0][1])}")

    for index, entry in enumerate(lists["considered"]):
        if not isinstance(entry, str) or not entry.strip():
            yield error("malformed_evidence", None, f"considered[{index}] must be a non-empty path")
        elif (finding := malformed("considered", index, entry)) is not None:
            yield finding


def _named_paths(row: dict) -> list[str]:
    """The well-formed paths a row cites or lists as considered.

    A malformed path is already an error and accounts for no field. It can
    still resolve, because `_resolve` follows any key the input holds: on a
    record carrying a key that is not snake_case, `version_access.Change Log`
    reaches a location inside the populated `version_access` (#3073).
    """
    cited = row.get("cited") if isinstance(row.get("cited"), list) else []
    considered = row.get("considered") if isinstance(row.get("considered"), list) else []
    paths = [_entry_path(entry) for entry in cited] + [entry for entry in considered if isinstance(entry, str)]
    return [path for path in paths if path and path.strip() and _path_problem(path) is None]


def _coverage(key: str, unit_path: str, unit: dict, row: dict,
              declared: tuple[str, ...]) -> Iterator[EvidenceFinding]:
    """Warn on each populated declared field a deduction does not account for.

    A named path accounts for a field only where it reaches a location the
    input populates for that field, or a container or value of one. Comparing
    spellings instead let a container an alias passes through, such as
    `file_collections` for `format`, stand for values it does not hold (#3018).
    A named path is read by `_locations`, as every other list reads it, so the
    declared name reaches all of the field's locations and needs no rule of
    its own (#3148).
    """
    reached = [_parts(pointer) for path in _named_paths(row) for pointer, _ in _locations(unit, path)]
    for name in declared:
        populated = [_parts(pointer) for pointer, value in field_values(unit, name) if _populated(value)]
        if not populated:
            continue
        if not any(a[:len(b)] == b[:len(a)] for a in reached for b in populated):
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
        if result.get("version") in ("3.0", "4.0"):
            if (not isinstance(issue.get("type"), str) or issue["type"] not in ISSUE_TYPES
                    or not isinstance(issue.get("category"), str) or issue["category"] not in ISSUE_CATEGORIES
                    or effect not in SCORE_EFFECTS or "item_ids" not in issue
                    or len(ids) != len(set(ids)) or (effect == "noted_only" and ids)):
                yield EvidenceFinding(
                    "error", "malformed_issue", None, None,
                    f"issue {index}: version {result['version'][0]} requires declared type/category, score_effect, unique item_ids; "
                    "noted_only has no lowered item_ids", issue=index)
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
