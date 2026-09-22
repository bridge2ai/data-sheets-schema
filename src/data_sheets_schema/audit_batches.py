"""Pure, opt-in audit batching and model-authored integration (protocol 7).

No source validator or provider is imported. Grammar verifies declarations, never
whether a quotation, status, attribution or scientific judgment is true. Callers
must validate_plan against the frozen original before using its structural roster.
All provisional bytes remain the caller's responsibility to preserve.

Worker bytes have the ordinary audit object shape, with a partial source_review
containing exactly that worker's assigned paths. Integration has exactly::

    {kind: "audit_integration_v1", proposal_index_sha256: HEX,
     retain_other_rows_from_index_sha256: HEX,
     row_replacements: [{path: POINTER, previous_sha256: HEX, row: ROW,
                         reason: TEXT, evidence: [ASSERTION, ...]}],
     finding_decisions: [{id: ID, previous_sha256: HEX, action: ACTION,
                          reason: TEXT, evidence: [ASSERTION, ...],
                          findings: [FINDING, ...]}],
     new_findings: [FINDING, ...], summary: TEXT}

Every indexed finding requires one decision. ``findings`` is present only for
``replace`` and may contain several complete findings (a model-authored split).
``retain`` may have empty evidence; replacements and drops require assertions.
Rows cannot be deleted or invented. The explicit retain-other-rows digest binds
all rows not individually replaced. No controller judgment resolves a conflict.
"""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
import math
import re

import yaml

from . import audit_grammar

PLAN_KIND = "audit_batch_plan_v1"
INDEX_KIND = "audit_batch_index_v1"
INTEGRATION_KIND = "audit_integration_v1"
INSTRUMENT = "audit_batches grammar v1"
MAX_ORIGINAL_BYTES = 4_000_000
MAX_NODES = 100_000
MAX_DEPTH = 64
MAX_FIELD_ROOTS = 4096
MAX_ERRORS = 20
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class AuditBatchError(ValueError):
    """A fixed, source-free error code, never candidate prose."""


def canonical_bytes(value) -> bytes:
    """Type-preserving canonical JSON for identities, with a final newline."""
    try:
        return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise AuditBatchError("canonical_json_invalid") from None


def object_sha256(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _bound(value):
    return {**value, "sha256": object_sha256(value)}


def _pointer(tokens):
    return "".join("/" + str(x).replace("~", "~0").replace("/", "~1") for x in tokens)


def _tokens(path):
    if not isinstance(path, str) or not path.startswith("/") or re.search(r"~(?![01])", path):
        raise AuditBatchError("pointer_invalid")
    return tuple(x.replace("~1", "/").replace("~0", "~") for x in path[1:].split("/"))


class _RecordLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        for key, _ in node.value:
            if key.tag != "tag:yaml.org,2002:str":
                raise AuditBatchError("record_key_invalid")
            name = self.construct_object(key, deep=deep)
            if name in seen:
                raise AuditBatchError("record_duplicate_key")
            seen.add(name)
        return super().construct_mapping(node, deep=deep)


def _inventory(raw):
    if type(raw) is not str:
        raise AuditBatchError("original_text_required")
    try:
        data = raw.encode("utf-8")
        if len(data) > MAX_ORIGINAL_BYTES:
            raise AuditBatchError("original_byte_bound")
        record = yaml.load(raw, Loader=_RecordLoader)
    except AuditBatchError:
        raise
    except (UnicodeError, yaml.YAMLError, RecursionError, ValueError, TypeError):
        raise AuditBatchError("original_yaml_invalid") from None
    if type(record) is not dict:
        raise AuditBatchError("original_mapping_required")
    values, nodes = [], 0

    def walk(value, tokens=(), active=frozenset()):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES or len(tokens) > MAX_DEPTH:
            raise AuditBatchError("original_structure_bound")
        typ = type(value)
        if typ in (dict, list):
            if id(value) in active:
                raise AuditBatchError("original_cycle")
            active = active | {id(value)}
            for key, child in (value.items() if typ is dict else enumerate(value)):
                walk(child, (*tokens, key), active)
        elif value is not None and value != "":
            if typ not in (str, int, float, bool, date, datetime):
                raise AuditBatchError("original_scalar_unsupported")
            if typ is float and not math.isfinite(value):
                raise AuditBatchError("original_scalar_nonfinite")
            text = (value if typ is str else value.isoformat() if typ in (date, datetime)
                    else json.dumps(value, ensure_ascii=False, allow_nan=False))
            path = _pointer(tokens)
            metadata = (path in {"/conforms_to_schema", "/conforms_to_class"}
                        or (path.endswith("/id") and path != "/id"
                            and isinstance(record.get("id"), str) and record["id"].strip()
                            and typ is str and value.startswith(record["id"] + "#")))
            values.append({"path": path, "text": text, "record_metadata_allowed": bool(metadata),
                           "whole_value_required": typ is not str})
    walk(record)
    inventory = {"artifact": "original_full", "sha256": hashlib.sha256(data).hexdigest(), "values": values}
    canonical_bytes(inventory)  # Reject unencodable YAML strings before registration.
    roots = [_pointer((key,)) for key in record]
    if len(roots) > MAX_FIELD_ROOTS:
        raise AuditBatchError("field_count_bound")
    canonical_bytes(roots)
    return inventory, sorted(roots, key=lambda x: x.encode("utf-8"))


def _limits(value):
    keys = {"max_paths", "max_inventory_bytes", "max_workers"}
    if type(value) is not dict or set(value) != keys or any(type(v) is not int or v < 1 for v in value.values()):
        raise AuditBatchError("plan_limits_invalid")
    return value


def _pack(inventory, roots, limits):
    groups = {root: [] for root in roots}
    for row in inventory["values"]:
        root = _pointer(_tokens(row["path"])[:1])
        if root not in groups:
            raise AuditBatchError("plan_path_owner_missing")
        groups[root].append(row)
    for rows in groups.values():
        rows.sort(key=lambda row: row["path"].encode("utf-8"))
    workers, current_roots, current_rows = [], [], []

    def fits(rows):
        return len(rows) <= limits["max_paths"] and len(canonical_bytes(rows)) <= limits["max_inventory_bytes"]

    def flush():
        workers.append({"id": f"worker_{len(workers) + 1:04d}", "roots": list(current_roots),
                        "paths": [r["path"] for r in current_rows],
                        "inventory_bytes": len(canonical_bytes(current_rows))})
        if len(workers) > limits["max_workers"]:
            raise AuditBatchError("worker_count_bound")

    for root in roots:
        rows = groups[root]
        if not fits(rows):
            raise AuditBatchError("indivisible_field_bound")
        if current_roots and not fits(current_rows + rows):
            flush()
            current_roots, current_rows = [], []
        current_roots.append(root)
        current_rows.extend(rows)
    if current_roots or not workers:
        if not fits(current_rows):
            raise AuditBatchError("empty_inventory_bound")
        flush()
    return workers


def make_plan(original_full: str, *, max_paths: int = 96, max_inventory_bytes: int = 16384,
              max_workers: int = 16) -> dict:
    """Pack whole top-level fields; an empty record gets one explicit empty worker.

    Bytes bound the canonical assigned inventory rows, not the rendered prompt.
    The caller must separately bound complete sources, schema and runtime context.
    """
    limits = _limits(dict(max_paths=max_paths, max_inventory_bytes=max_inventory_bytes, max_workers=max_workers))
    inventory, roots = _inventory(original_full)
    return _bound({"schema_version": 1, "kind": PLAN_KIND, "original_full_sha256": inventory["sha256"],
                   "limits": limits, "inventory": inventory, "field_roots": roots,
                   "workers": _pack(inventory, roots, limits)})


def validate_plan(plan, original_full) -> None:
    """Recompute against frozen original bytes, not merely a self-supplied hash."""
    try:
        expected = make_plan(original_full, **_limits(plan["limits"]))
        if canonical_bytes(plan) != canonical_bytes(expected):
            raise AuditBatchError("plan_original_mismatch")
    except AuditBatchError:
        raise
    except (TypeError, KeyError, ValueError):
        raise AuditBatchError("plan_invalid") from None


def _plan(plan):
    """Structural self-consistency only; original authority is validate_plan's job."""
    try:
        if type(plan) is not dict or set(plan) != {"schema_version", "kind", "original_full_sha256", "limits", "inventory", "field_roots", "workers", "sha256"}:
            raise AuditBatchError("plan_shape")
        if type(plan["schema_version"]) is not int or plan["schema_version"] != 1 or plan["kind"] != PLAN_KIND:
            raise AuditBatchError("plan_version")
        if not isinstance(plan["original_full_sha256"], str) or not _DIGEST.fullmatch(plan["original_full_sha256"]):
            raise AuditBatchError("plan_digest")
        if object_sha256({k: v for k, v in plan.items() if k != "sha256"}) != plan["sha256"]:
            raise AuditBatchError("plan_digest")
        inv = plan["inventory"]
        if type(inv) is not dict or set(inv) != {"artifact", "sha256", "values"} or inv["artifact"] != "original_full" or inv["sha256"] != plan["original_full_sha256"] or type(inv["values"]) is not list:
            raise AuditBatchError("plan_inventory")
        seen = set()
        for row in inv["values"]:
            if type(row) is not dict or set(row) != {"path", "text", "record_metadata_allowed", "whole_value_required"}:
                raise AuditBatchError("plan_inventory")
            _tokens(row["path"])
            if row["path"] in seen or type(row["text"]) is not str or not row["text"] or type(row["record_metadata_allowed"]) is not bool or type(row["whole_value_required"]) is not bool:
                raise AuditBatchError("plan_inventory")
            seen.add(row["path"])
        roots = plan["field_roots"]
        if type(roots) is not list or len(roots) > MAX_FIELD_ROOTS or any(len(_tokens(x)) != 1 for x in roots) or roots != sorted(set(roots), key=lambda x: x.encode("utf-8")):
            raise AuditBatchError("plan_roots")
        workers = _pack(inv, roots, _limits(plan["limits"]))
        if canonical_bytes(workers) != canonical_bytes(plan["workers"]):
            raise AuditBatchError("plan_workers")
        return plan
    except AuditBatchError:
        raise
    except (TypeError, KeyError, ValueError, UnicodeError, RecursionError):
        raise AuditBatchError("plan_invalid") from None


def _report(errors=()):
    return {"instrument": INSTRUMENT, "schema_version": 1, "passed": not errors,
            "error_count": len(errors), "errors": list(errors[:MAX_ERRORS]), "truncated": len(errors) > MAX_ERRORS}


def _failure(code, path=""):
    return _report([{"code": code, "path": path}])


def _load(raw):
    try:
        return audit_grammar._load(raw)
    except audit_grammar._JSONProblem as exc:
        raise AuditBatchError(str(exc)) from None


def check_worker(raw: bytes, plan, worker_id) -> dict:
    """Candidate-only grammar plus registered structural path/root ownership."""
    try:
        _plan(plan)
        worker = next((w for w in plan["workers"] if w["id"] == worker_id), None)
        if worker is None:
            return _failure("worker_id_unknown")
        result = audit_grammar.check(raw)
        if not result["passed"]:
            return {**result, "instrument": INSTRUMENT}
        audit = _load(raw)
        review = audit["source_review"]
        if review["sha256"] != plan["original_full_sha256"]:
            return _failure("worker_original_digest", "/source_review/sha256")
        if set(r["path"] for r in review["values"]) != set(worker["paths"]):
            return _failure("worker_path_roster", "/source_review/values")
        for i, finding in enumerate(audit["findings"]):
            removal = finding.get("remove_relationship")
            if removal and _pointer(_tokens(removal["path"])[:1]) not in worker["roots"]:
                return _failure("worker_removal_owner", f"/findings/{i}/remove_relationship/path")
        return _report()
    except AuditBatchError as exc:
        return _failure(str(exc))
    except (TypeError, KeyError, ValueError, RecursionError):
        return _failure("worker_structure_invalid")


def build_index(plan, proposals: dict[str, bytes]) -> dict:
    """Bind every immutable worker, row and finding; validate no source claims."""
    _plan(plan)
    if type(proposals) is not dict or set(proposals) != {w["id"] for w in plan["workers"]}:
        raise AuditBatchError("proposal_roster")
    workers, by_path, findings = [], {}, []
    for worker in plan["workers"]:
        key, raw = worker["id"], proposals[worker["id"]]
        if not check_worker(raw, plan, key)["passed"]:
            raise AuditBatchError("worker_invalid")
        value = _load(raw)
        workers.append({"id": key, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        for row in value["source_review"]["values"]:
            by_path[row["path"]] = {"path": row["path"], "worker_id": key, "sha256": object_sha256(row)}
        for i, finding in enumerate(value["findings"]):
            findings.append({"id": f"{key}:{i + 1:04d}", "worker_id": key, "ordinal": i, "sha256": object_sha256(finding)})
    return _bound({"schema_version": 1, "kind": INDEX_KIND, "plan_sha256": plan["sha256"],
                   "original_full_sha256": plan["original_full_sha256"], "workers": workers,
                   "rows": [by_path[r["path"]] for r in plan["inventory"]["values"]], "findings": findings})


def _assertions(grammar, value, path, *, nonempty):
    if grammar.array(value, path, nonempty=nonempty):
        for i, item in enumerate(value):
            where = f"{path}/{i}"
            if isinstance(item, dict) and "source" in item:
                grammar.document(item, where)
            else:
                grammar.artifact(item, where)


def _finding(grammar, value, path):
    if not grammar.obj(value, {"severity", "record", "slot", "issue", "evidence"}, path,
                       {"review_paths", "remove_relationship"}):
        return
    grammar.enum(value.get("severity"), {"high", "medium", "low"}, path + "/severity")
    grammar.enum(value.get("record"), {"full", "core", "both"}, path + "/record")
    grammar.text(value.get("slot"), path + "/slot")
    grammar.text(value.get("issue"), path + "/issue")
    _assertions(grammar, value.get("evidence"), path + "/evidence", nonempty=True)
    if "review_paths" in value and grammar.array(value["review_paths"], path + "/review_paths", nonempty=True):
        for i, pointer in enumerate(value["review_paths"]):
            grammar.pointer(pointer, f"{path}/review_paths/{i}")
    if "remove_relationship" in value:
        grammar.removal(value["remove_relationship"], path + "/remove_relationship")


def _integration(raw, plan, proposals):
    index = build_index(plan, proposals)
    value = _load(raw)
    g = audit_grammar._Grammar()
    required = {"kind", "proposal_index_sha256", "retain_other_rows_from_index_sha256", "row_replacements", "finding_decisions", "new_findings", "summary"}
    if not g.obj(value, required, ""):
        return value, index, g.result()
    g.enum(value.get("kind"), {INTEGRATION_KIND}, "/kind")
    g.text(value.get("summary"), "/summary")
    for key in ("proposal_index_sha256", "retain_other_rows_from_index_sha256"):
        if value.get(key) != index["sha256"]:
            g.problem("integration_index_digest", "/" + key)
    row_index = {r["path"]: r for r in index["rows"]}
    seen_rows = set()
    replacements = value.get("row_replacements")
    if g.array(replacements, "/row_replacements"):
        for i, item in enumerate(replacements):
            at = f"/row_replacements/{i}"
            if not g.obj(item, {"path", "previous_sha256", "row", "reason", "evidence"}, at):
                continue
            path = item.get("path")
            if not isinstance(path, str) or path not in row_index:
                g.problem("replacement_path_unknown", at + "/path")
            elif path in seen_rows:
                g.problem("replacement_path_duplicate", at + "/path")
            else:
                seen_rows.add(path)
                if item.get("previous_sha256") != row_index[path]["sha256"]:
                    g.problem("replacement_predecessor_digest", at + "/previous_sha256")
            row = item.get("row")
            g.review({"artifact": "original_full", "sha256": plan["original_full_sha256"], "values": [row]}, at + "/row_shape")
            if not isinstance(row, dict) or row.get("path") != path:
                g.problem("replacement_row_path", at + "/row")
            g.text(item.get("reason"), at + "/reason")
            _assertions(g, item.get("evidence"), at + "/evidence", nonempty=True)
    finding_index = {f["id"]: f for f in index["findings"]}
    seen_findings = set()
    decisions = value.get("finding_decisions")
    if g.array(decisions, "/finding_decisions"):
        for i, item in enumerate(decisions):
            at = f"/finding_decisions/{i}"
            if not isinstance(item, dict):
                g.problem("object_required", at)
                continue
            action = item.get("action")
            g.obj(item, {"id", "previous_sha256", "action", "reason", "evidence"}, at,
                  {"findings"} if action == "replace" else set())
            g.enum(action, {"retain", "replace", "drop"}, at + "/action")
            identity = item.get("id")
            if not isinstance(identity, str) or identity not in finding_index:
                g.problem("finding_id_unknown", at + "/id")
            elif identity in seen_findings:
                g.problem("finding_decision_duplicate", at + "/id")
            else:
                seen_findings.add(identity)
                if item.get("previous_sha256") != finding_index[identity]["sha256"]:
                    g.problem("finding_predecessor_digest", at + "/previous_sha256")
            g.text(item.get("reason"), at + "/reason")
            _assertions(g, item.get("evidence"), at + "/evidence", nonempty=action != "retain")
            if action == "replace" and g.array(item.get("findings"), at + "/findings", nonempty=True):
                for j, finding in enumerate(item["findings"]):
                    _finding(g, finding, at + f"/findings/{j}")
    if seen_findings != set(finding_index):
        g.problem("finding_decision_roster", "/finding_decisions")
    if g.array(value.get("new_findings"), "/new_findings"):
        for i, finding in enumerate(value["new_findings"]):
            _finding(g, finding, f"/new_findings/{i}")
    return value, index, g.result()


def _materialize(plan, proposals, value, index):
    audits = {key: _load(raw) for key, raw in proposals.items()}
    rows = {r["path"]: r for audit in audits.values() for r in audit["source_review"]["values"]}
    replacements = {r["path"]: (i, r) for i, r in enumerate(value["row_replacements"])}
    lineage_rows = []
    for entry in index["rows"]:
        path = entry["path"]
        if path in replacements:
            i, replacement = replacements[path]
            rows[path] = replacement["row"]
            origin = {"kind": "integration_replacement", "ordinal": i,
                      "previous_sha256": replacement["previous_sha256"], "row_sha256": object_sha256(rows[path])}
        else:
            origin = {"kind": "worker", "worker_id": entry["worker_id"], "row_sha256": entry["sha256"]}
        lineage_rows.append({"path": path, "origin": origin})
    decisions = {d["id"]: (i, d) for i, d in enumerate(value["finding_decisions"])}
    findings, lineage_findings, dispositions = [], [], []
    for entry in index["findings"]:
        ordinal, decision = decisions[entry["id"]]
        dispositions.append({"id": entry["id"], "action": decision["action"],
                             "decision_ordinal": ordinal, "decision_sha256": object_sha256(decision)})
        chosen = ([audits[entry["worker_id"]]["findings"][entry["ordinal"]]] if decision["action"] == "retain"
                  else decision["findings"] if decision["action"] == "replace" else [])
        for j, finding in enumerate(chosen):
            lineage_findings.append({"final_ordinal": len(findings), "kind": decision["action"],
                                     "predecessor_id": entry["id"], "decision_ordinal": ordinal,
                                     "replacement_ordinal": j if decision["action"] == "replace" else None,
                                     "finding_sha256": object_sha256(finding)})
            findings.append(finding)
    for i, finding in enumerate(value["new_findings"]):
        lineage_findings.append({"final_ordinal": len(findings), "kind": "integration_new", "ordinal": i,
                                 "finding_sha256": object_sha256(finding)})
        findings.append(finding)
    audit = {"findings": findings, "summary": value["summary"], "source_review": {
        "artifact": "original_full", "sha256": plan["original_full_sha256"],
        "values": [rows[r["path"]] for r in plan["inventory"]["values"]]}}
    lineage = {"schema_version": 1, "kind": "audit_batch_lineage_v1", "plan_sha256": plan["sha256"],
               "proposal_index_sha256": index["sha256"], "rows": lineage_rows,
               "findings": lineage_findings, "finding_dispositions": dispositions,
               "decision_assertions": [e for d in value["row_replacements"] + value["finding_decisions"] for e in d["evidence"]]}
    return audit, lineage


def _removal_errors(audit, plan):
    paths, errors = [], []
    roots = set(plan["field_roots"])
    for i, finding in enumerate(audit["findings"]):
        if "remove_relationship" not in finding:
            continue
        tokens = _tokens(finding["remove_relationship"]["path"])
        at = f"/assembled/findings/{i}/remove_relationship/path"
        if _pointer(tokens[:1]) not in roots:
            errors.append({"code": "removal_root_unknown", "path": at})
        if any(tokens[:len(other)] == other or other[:len(tokens)] == tokens for other in paths):
            errors.append({"code": "removal_overlap", "path": at})
        paths.append(tokens)
    return errors


def _checked_integration(raw, plan, proposals):
    value, index, report = _integration(raw, plan, proposals)
    if not report["passed"]:
        return None, None, {**report, "instrument": INSTRUMENT}
    audit, lineage = _materialize(plan, proposals, value, index)
    encoded = canonical_bytes(audit)
    report = audit_grammar.check(encoded)
    if not report["passed"]:
        return None, None, {**report, "instrument": INSTRUMENT,
                            "errors": [{**e, "path": "/assembled" + e["path"]} for e in report["errors"]]}
    errors = _removal_errors(audit, plan)
    if errors:
        return None, None, _report(errors)
    lineage.update(integration_sha256=hashlib.sha256(raw).hexdigest(), audit_sha256=hashlib.sha256(encoded).hexdigest())
    return encoded, lineage, _report()


def check_integration(raw: bytes, plan, proposals) -> dict:
    """Structure and complete explicit integration only; no source entailment."""
    try:
        return _checked_integration(raw, plan, proposals)[2]
    except AuditBatchError as exc:
        return _failure(str(exc))
    except (TypeError, KeyError, ValueError, RecursionError):
        return _failure("integration_structure_invalid")


def assemble(plan, proposals, integration_raw) -> tuple[bytes, dict]:
    """Apply only explicit model decisions, producing audit bytes and lineage.

    Neither this operation nor grammar establishes scientific acceptance. The
    caller invokes the sole terminal source/evidence check after exact sealing.
    """
    try:
        encoded, lineage, report = _checked_integration(integration_raw, plan, proposals)
        if not report["passed"]:
            raise AuditBatchError("integration_invalid")
        return encoded, lineage
    except AuditBatchError:
        raise
    except (TypeError, KeyError, ValueError, RecursionError):
        raise AuditBatchError("integration_structure_invalid") from None
