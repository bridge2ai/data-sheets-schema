"""Report accounting and record overlap for revised fig09 (#2915, #4385).

This compares a deterministic record with a pinned historical generated record.
Record overlap does not establish whether a source supplies the same information.
Source observations are reported independently of output-slot overlap.
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Any

import yaml

from data_sheets_schema.scope import bare_doi, _norm


STATUSES = ("filled", "subsumed", "empty", "unresolvable", "unplaceable",
            "retired", "deferred")
OVERLAP = ("both_agree", "both_differ_scalar", "both_differ_nested",
           "crate_only", "generated_only")
EMPTY = (None, "", [], {})


def _cells(line: str) -> list[str]:
    return [value.strip().strip("`") for value in
            re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def parse_report(text: str) -> dict[str, Any]:
    """Read current and legacy report headers without silently losing statuses.

    The Outcome table counts report entries, including the separately reported
    root identifier. Original table rows, active rules and populated slots are
    different denominators. Counts are checked against the per-field table.
    """
    result: dict[str, Any] = {"outcome": {}, "loss": {}, "maptype": {},
                              "fields": [], "original_rows": None,
                              "active_rows": None, "distinct_slots": None}
    header = next((line for line in text.splitlines()
                   if line.startswith("- Mapping table:")), "")
    old = re.search(r"\((\d+) (?:table )?rows (?:applied|declared)\b", header)
    original = re.search(r"\b(\d+) (?:original|retained)(?: table)? rows\b", header)
    if old or original:
        result["original_rows"] = int((original or old)[1])
    active = re.search(r"\b(\d+) active(?: (?:table|executable))? rows\b", header)
    if active:
        result["active_rows"] = int(active[1])
    slots = re.search(r"Distinct top-level `Dataset` slots filled: (\d+)", text)
    if slots:
        result["distinct_slots"] = int(slots[1])
    section = None
    fidelity = None
    for line in text.splitlines():
        if line.startswith("## "):
            section = {"## Outcome": "outcome",
                       "## Fidelity of what was filled": "fidelity",
                       "## Per-field detail": "fields"}.get(line)
            continue
        if not line.startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 2 or set(cells[0]) <= {"-", ":", " "}:
            continue
        if section == "outcome":
            if cells[0] == "Status":
                continue
            if cells[0] not in STATUSES:
                raise ValueError(f"unrecognized mapping outcome: {cells[0]}")
            if cells[0] in result["outcome"]:
                raise ValueError(f"duplicate mapping outcome: {cells[0]}")
            result["outcome"][cells[0]] = int(cells[1])
        elif section == "fidelity":
            if cells[0] == "Mapping type":
                fidelity = "maptype"
            elif cells[0] == "Information loss":
                fidelity = "loss"
            elif fidelity:
                label = "—" if cells[0] in ("(unstated)", "—", "unassessed") else cells[0]
                if fidelity == "loss" and label not in ("none", "minimal", "moderate", "high", "—"):
                    raise ValueError(f"unrecognized declared loss: {label}")
                if label in result[fidelity]:
                    raise ValueError(f"duplicate {fidelity} label: {label}")
                result[fidelity][label] = int(cells[1])
        elif section == "fields" and cells[0] != "D4D path":
            if len(cells) != 6 or cells[1] not in STATUSES:
                raise ValueError("malformed per-field mapping row")
            result["fields"].append(dict(zip(
                ("d4d_path", "status", "mapping_type", "information_loss",
                 "source_path", "detail"), cells)))
    if not result["outcome"] or not result["fields"]:
        raise ValueError("report lacks outcome or per-field accounting")
    counted = Counter(row["status"] for row in result["fields"])
    if any(result["outcome"].get(status, 0) != counted[status]
           for status in set(result["outcome"]) | set(counted)):
        raise ValueError("outcome counts disagree with per-field rows")
    if any(value < 0 for value in result["outcome"].values()):
        raise ValueError("negative report count")
    # The historical report did not explicitly identify root-derived rows.
    # The current form does, so enforce the original-table denominator there.
    root_rows = sum(row["source_path"] == "crate root identifier/@id"
                    for row in result["fields"])
    if result["original_rows"] is not None:
        if len(result["fields"]) - root_rows != result["original_rows"]:
            raise ValueError("original row count disagrees with per-field table")
    else:
        raise ValueError("report does not declare its original table-row count")
    derived_active = result["original_rows"] - counted["retired"] - counted["deferred"]
    if result["active_rows"] is None:
        result["active_rows"] = derived_active
    elif result["active_rows"] != derived_active:
        raise ValueError("active row count does not reconcile to dispositions")
    for dimension in ("loss", "maptype"):
        if sum(result[dimension].values()) != counted["filled"]:
            raise ValueError(f"{dimension} counts disagree with filled rows")
    result["root_identifier_rows"] = root_rows
    result["report_entries"] = len(result["fields"])
    return result


def normalized_value(value: Any) -> str:
    return re.sub(r"\s+", " ", yaml.safe_dump(
        value, sort_keys=True, allow_unicode=True)).strip()


def values_agree(slot: str, first: Any, second: Any) -> bool:
    """DOI identity is normalized only for identifier slots and actual DOIs.

    Other scalar and nested values retain the historical serialized comparison;
    nested differences are not a scientific finding of disagreement.
    """
    if slot in ("doi", "id") and bare_doi(first) and bare_doi(second):
        return _norm(first) == _norm(second)
    return normalized_value(first) == normalized_value(second)


def compare_records(project: str, crate: dict, generated: dict) -> tuple[dict, list]:
    if not isinstance(crate, dict) or not isinstance(generated, dict):
        raise ValueError("each record must be a mapping")
    ck = {key for key, value in crate.items() if value not in EMPTY}
    gk = {key for key, value in generated.items() if value not in EMPTY}
    counts = dict.fromkeys(OVERLAP, 0)
    detail = []
    for slot in sorted(ck | gk):
        nested = any(isinstance(value, (dict, list))
                     for value in (crate.get(slot), generated.get(slot)))
        kind = "nested" if nested else "scalar"
        if slot in ck and slot in gk:
            state = "both_agree" if values_agree(slot, crate[slot], generated[slot]) \
                else f"both_differ_{kind}"
        else:
            state = "crate_only" if slot in ck else "generated_only"
        counts[state] += 1
        detail.append({"project": project, "slot": slot, "state": state,
                       "value_kind": kind, "source_evidence": "not_assessed_by_slot_overlap",
                       "crate_value": normalized_value(crate[slot]) if slot in ck else "",
                       "generated_value": normalized_value(generated[slot]) if slot in gk else ""})
    return counts, detail


def generated_v8_rep1(manifest: dict) -> dict[str, str]:
    """Select the explicit historical comparator, refusing competing inputs."""
    selected = {}
    for job in manifest["jobs"]:
        if job.get("cohort") == "v8" and job.get("generation_rep") == 1:
            project, path = job["project"], job["input"]
            if project in selected and selected[project] != path:
                raise ValueError(f"ambiguous v8 rep 1 input for {project}")
            selected[project] = path
    if not selected:
        raise ValueError("manifest has no historical v8 rep 1 inputs")
    return selected


def source_evidence_rows(sidecar: dict) -> list[dict]:
    """Keep source presence, entity scope and row placement as separate facts.

    An inactive duplicate can have source evidence already placed by another
    row, so this table never equates an unplaced row with missing information
    in the complete record. It is a row inventory, not unique-source coverage.
    """
    if sidecar.get("format_version") != 1 or not isinstance(sidecar.get("rows"), list):
        raise ValueError("expected mapping-source sidecar version 1")
    from data_sheets_schema.rocrate_map import GRAPH_RE, NOT_A_PATH

    results = []
    seen = set()
    for row in sidecar["rows"]:
        rule_id = row["rule_id"]
        if rule_id in seen:
            raise ValueError(f"duplicate source-evidence rule ID: {rule_id}")
        seen.add(rule_id)
        root = row["root_assertions"]
        members = row["member_assertions"]
        if not isinstance(root, list) or not isinstance(members, list):
            raise ValueError("source assertions must be lists")
        root_present = any(assertion["value"] not in EMPTY for assertion in root)
        member_present = any(assertion["value"] not in EMPTY for assertion in members)
        expression = row["source_expression"].strip()
        readable = bool(GRAPH_RE.fullmatch(expression)) or (
            bool(expression) and not NOT_A_PATH.fullmatch(expression)
            and not expression.startswith("@graph") and not any(c.isspace() for c in expression))
        if root_present:
            presence = "root_value_present"
        elif member_present:
            presence = "member_value_only"
        elif root or members:
            presence = "property_present_but_empty"
        else:
            presence = "source_absent_for_expression" if readable else "not_assessed"
        results.append({"project": sidecar["project"], "rule_id": rule_id,
                        "execution": row["execution"], "d4d_path": row["d4d_path"],
                        "destination_slot": row.get("destination_slot"),
                        "mapping_status": row["status"], "source_evidence": presence,
                        "placed_by_this_row": row["status"] == "filled",
                        "root_value_present": root_present,
                        "member_value_present": member_present,
                        "source_expression": expression,
                        "resolution_note": row.get("resolution_note", ""),
                        "root_assertions": root, "member_assertions": members,
                        "linked_assertions": row.get("linked_assertions", [])})
    return results
