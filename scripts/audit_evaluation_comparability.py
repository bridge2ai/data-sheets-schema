#!/usr/bin/env python3
"""Audit historical evaluation identity/condition gaps without rewriting evidence.

Purpose: deterministic Step E0/E4 inventory for #2911, #2912 and #1077.
Inputs: selected checkout's generation provenance/artifacts and the two direct
label_aware JSON stores; optional independently selected model/context pins.
Outputs: JSON or Markdown on stdout only. No scoring, provider calls or writes.
Date: 2026-10-20. Retained ratings elsewhere require separate ingestion review;
an absent qualifying rating here does not prove no such rating exists elsewhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_sheets_schema import agent_pin
from data_sheets_schema.evaluation_context import context_digest, normalize_context, unwrap_document
from data_sheets_schema.evaluation.validate import validate_evaluation
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.semantic_scope import validate_scope

PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
ARMS = {
    "v4": ("2026-08-13_claude-opus-5-api-generic-v4", PROJECTS),
    "22c": ("2026-08-22c_claude-opus-5-api-generic-v5", PROJECTS),
    "v6": ("2026-08-28_claude-opus-5-claudecode-generic-v6", PROJECTS),
    "v7": ("2026-09-01_claude-opus-5-api-generic-v7", PROJECTS),
    "v8_04f": ("2026-09-04f_claude-opus-5-api-generic-v8", ("CHORUS", "VOICE")),
    "v8_04g": ("2026-09-04g_claude-opus-5-api-generic-v8", ("AI_READI", "CM4AI")),
}
RUBRICS = ("rubric10", "rubric20")
MAX_BYTES = 32 * 1024 * 1024
HEX = re.compile(r"[0-9a-fA-F]{64}\Z")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def mapping(value):
    return value if isinstance(value, dict) else {}


def pre_three_version(value):
    """Flag numeric earlier versions without treating arbitrary tags as versions."""
    return (isinstance(value, str)
            and re.fullmatch(r"[0-2](?:\.\d+)*", value) is not None)


def read(path):
    """Bound reads and refuse symlink escapes; caller selects canonical paths."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BYTES:
            raise ValueError("not a bounded nonempty regular file")
        raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > MAX_BYTES or any(getattr(before, key) != getattr(after, key) for key in
                                  ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")):
        raise ValueError("file changed during capture")
    return raw


class UniqueLoader(getattr(yaml, "CSafeLoader", yaml.SafeLoader)):
    pass


UniqueLoader.yaml_implicit_resolvers = {
    key: [(tag, expression) for tag, expression in resolvers
          if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in UniqueLoader.yaml_implicit_resolvers.items()
}


def finite_tree(value, ancestors=None, depth=0, budget=None):
    """Bound malformed YAML aliases/depth and reject non-JSON scientific scalars."""
    ancestors = set() if ancestors is None else ancestors
    budget = [500_000] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0 or depth > 64:
        raise ValueError("document exceeds structural bounds")
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    if not isinstance(value, (dict, list)) or id(value) in ancestors:
        raise ValueError("document contains nonfinite, unsupported or recursive values")
    if isinstance(value, dict) and any(not isinstance(key, str) for key in value):
        raise ValueError("document has nonstring mapping keys")
    ancestors.add(id(value))
    for child in value.values() if isinstance(value, dict) else value:
        finite_tree(child, ancestors, depth + 1, budget)
    ancestors.remove(id(value))


def unique_mapping(loader, node):
    out = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in out:
            raise ValueError("mapping has duplicate or nonstring keys")
        out[key] = loader.construct_object(value_node)
    return out


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def document(raw, *, json_only=False):
    if json_only:
        def pairs(rows):
            result = {}
            for key, value in rows:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        def invalid(value):
            raise ValueError("nonfinite JSON value")
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    else:
        value = yaml.load(raw, Loader=UniqueLoader)
    if not isinstance(value, dict):
        raise ValueError("document is not a mapping")
    finite_tree(value)
    return value


def local_path(root, value):
    if not isinstance(value, str) or not value:
        return None
    try:
        path = root / value
        if ".." in path.parts:
            return None
        resolved = path.resolve()
        resolved.relative_to(root)
        return resolved
    except (ValueError, OSError, RuntimeError):
        return None


def relative(root, path):
    return path.relative_to(root).as_posix()


def read_local(root, path):
    selected = local_path(root, str(path))
    if selected is None:
        raise ValueError("selected file escapes checkout")
    return read(selected)


def load_record(root, arm, project, label):
    """One exact provenance identity; never choose an ambiguous method copy."""
    paths = sorted((root / "data/d4d_concatenated").glob(f"*_core/{label}/{project}_provenance.yaml"))
    result = {"arm": arm, "project": project, "label": label,
        "provenance_files": [relative(root, path) for path in paths], "canonical": False,
        "record_path": None, "record_sha256": None, "validation_passed": None,
        "generation_method": None, "reasons": []}
    if len(paths) != 1:
        result["reasons"].append("provenance_missing" if not paths else "provenance_ambiguous")
        return result, None
    try:
        raw = read_local(root, paths[0])
        rec = document(raw)
        result["provenance_sha256"] = sha(raw)
    except (OSError, ValueError, yaml.YAMLError, UnicodeError, RecursionError):
        result["reasons"].append("provenance_unreadable")
        return result, None
    run = mapping(rec.get("run"))
    result["canonical"] = "canonical" in rec
    result["canonical_criterion"] = mapping(rec.get("canonical")).get("criterion")
    result["generation_method"] = run.get("method")
    result["validation_passed"] = mapping(rec.get("validation")).get("passed")
    if (rec.get("record_type") != "d4d_generation_provenance" or run.get("project") != project
            or run.get("label") != label or run.get("method") != paths[0].parents[1].name.removesuffix("_core")
            or (run.get("replicate") is not None and
                (type(run["replicate"]) is not int or run["replicate"] != int(label.rsplit("_rep", 1)[1])))):
        result["reasons"].append("provenance_identity_conflict")
    outputs = mapping(mapping(rec.get("outputs")).get("full"))
    artifact = mapping(mapping(mapping(rec.get("validation")).get("artifacts")).get("full"))
    name = artifact.get("path") or outputs.get("path")
    path = local_path(root, name)
    if path is None:
        result["reasons"].append("generation_artifact_path_missing_or_external")
        return result, None
    result["record_path"] = relative(root, path)
    if outputs.get("path") and local_path(root, outputs["path"]) != path:
        result["reasons"].append("generation_artifact_paths_conflict")
    try:
        full_raw = read(path)
        result["record_sha256"] = sha(full_raw)
    except (OSError, ValueError):
        result["reasons"].append("generation_artifact_unavailable")
        return result, None
    pins = [(key, value) for entry in (artifact, outputs) for key, value in entry.items()
            if key in ("md5", "sha256")]
    if not pins:
        result["reasons"].append("generation_artifact_hash_missing")
    elif any(not isinstance(value, str) or hashlib.new(key, full_raw).hexdigest() != value.lower()
             for key, value in pins):
        result["reasons"].append("generation_artifact_hash_mismatch")
    if result["validation_passed"] is False:
        result["reasons"].append("generation_record_declared_invalid")
    elif result["validation_passed"] is not True:
        result["reasons"].append("generation_validation_unknown")
    return result, full_raw


def evaluations(root):
    """Direct filesystem glob includes ignored/hidden entries in selected stores."""
    rows, problems, stores = [], [], []
    for rubric in RUBRICS:
        folder = root / "data/evaluation_llm" / (rubric + "_semantic") / "label_aware"
        stores.append({"rubric": rubric, "path": relative(root, folder),
                       "exists": folder.is_dir(), "glob": "*.json (nonrecursive)"})
        for path in sorted(folder.glob("*.json")):
            try:
                raw = read_local(root, path)
                doc = document(raw, json_only=True)
                rows.append({"store": rubric, "path": relative(root, path), "sha256": sha(raw), "doc": doc})
            except (OSError, ValueError, UnicodeError, RecursionError):
                problems.append({"path": relative(root, path), "reason": "evaluation_unreadable_or_invalid_json"})
    return rows, problems, stores


def instrument(rubric, version):
    selected = select_semantic_instrument(rubric, version)
    paths = (selected.definition_path, selected.rubric_path, selected.schema_path, selected.evidence_authority_path)
    resources = {name: read(ROOT / name) for name in paths}
    return selected, resources


def association(root, evaluation, record):
    """Content labels or exact recorded artifact paths only; filenames never join."""
    doc = evaluation["doc"]
    metadata = mapping(doc.get("metadata"))
    labels = {value for value in (doc.get("label"), metadata.get("label")) if isinstance(value, str)}
    named = doc.get("project") == record["project"] and record["label"] in labels
    path = local_path(root, doc.get("d4d_file"))
    exact_path = record["record_path"] is not None and path == root / record["record_path"]
    return named or exact_path


def inspect_evaluation(root, evaluation, record, full_raw, *, version, evaluator_model, target_context,
                       instrument_snapshot=None):
    rubric, doc = evaluation["store"], evaluation["doc"]
    metadata, model = mapping(doc.get("metadata")), mapping(doc.get("model"))
    labels = [value for value in (doc.get("label"), metadata.get("label")) if value is not None]
    reasons, pending = [], []
    row = {key: evaluation[key] for key in ("path", "sha256")}
    row.update(rubric=doc.get("rubric"), version=doc.get("version"),
        evaluator=model.get("evaluator_model") or model.get("name"),
        model_name=model.get("name"), context_block_present=isinstance(doc.get("applicability_context"), dict),
        context_hash=metadata.get("context_sha256"), input_hashes={},
        session_id=metadata.get("session_id") or doc.get("session_id"),
        declared_repeat_n=mapping(doc.get("repeat_panel")).get("n"),
        reasons=reasons, pending=pending)
    if doc.get("rubric") != rubric + "-semantic":
        reasons.append("rubric_disagrees_with_store")
    if doc.get("version") != version:
        reasons.append("pre_3_instrument" if pre_three_version(doc.get("version")) else "instrument_version_mismatch")
    if doc.get("project") != record["project"] or any(value != record["label"] for value in labels):
        reasons.append("evaluation_run_identity_conflict")
    if doc.get("method") is not None and doc["method"] != record["generation_method"]:
        reasons.append("evaluation_method_conflict")
    path = local_path(root, doc.get("d4d_file"))
    if record["record_path"] is None or path != root / record["record_path"]:
        reasons.append("evaluation_input_path_unverified")
    hashes = {key: metadata[key] for key in ("input_sha256", "d4d_file_hash") if key in metadata}
    row["input_hashes"] = hashes
    if not hashes:
        reasons.append("evaluation_input_hash_missing")
    elif any(not isinstance(value, str) or not HEX.fullmatch(value) or value.lower() != record["record_sha256"]
             for value in hashes.values()):
        reasons.append("evaluation_input_hash_mismatch")
    if not isinstance(row["evaluator"], str) or not row["evaluator"].strip():
        reasons.append("evaluator_model_missing")
    elif model.get("name") and model.get("evaluator_model") and model["name"] != model["evaluator_model"]:
        reasons.append("evaluator_model_fields_conflict")
    if evaluator_model is None:
        pending.append("target_evaluator_not_selected")
    elif row["evaluator"] != evaluator_model:
        reasons.append("evaluator_differs_from_target")
    normalized = None
    if not row["context_block_present"]:
        reasons.append("applicability_context_missing")
    else:
        try:
            normalized = normalize_context(doc["applicability_context"])
            computed = context_digest(normalized)
            if not isinstance(row["context_hash"], str) or row["context_hash"] != computed:
                reasons.append("applicability_context_hash_missing_or_mismatched")
        except (TypeError, ValueError):
            reasons.append("applicability_context_invalid")
    if target_context is None:
        pending.append("target_context_not_selected")
    elif normalized != target_context:
        reasons.append("applicability_context_differs_from_target")
    selected, resources = instrument_snapshot or instrument(rubric, version)
    for key, name in (("instrument_sha256", selected.definition_path), ("rubric_sha256", selected.rubric_path),
                      ("evidence_authority_sha256", selected.evidence_authority_path)):
        if metadata.get(key) != sha(resources[name]):
            reasons.append(key + "_missing_or_mismatched")
    echo = metadata.get("definition_echo") or doc.get("definition_echo")
    if not isinstance(echo, str):
        reasons.append("definition_echo_evidence_missing")
    else:
        try:
            predecessor = read(ROOT / select_semantic_instrument("rubric20", "3.0").definition_path).decode() if version == "4.0" else None
            agent_pin.verify_echo(selected.agent, echo, predecessor_text=predecessor)
        except (ValueError, OSError, RuntimeError):
            reasons.append("definition_echo_not_verified")
    row["contract_checked"] = False
    if doc.get("version") == version and full_raw is not None and normalized is not None:
        row["contract_checked"] = True
        try:
            valid, errors = validate_evaluation(doc, json.loads(resources[selected.schema_path]),
                                               resource_reader=resources.__getitem__)
            if not valid:
                raise ValueError("; ".join(errors[:3]))
            validate_scope(doc, document=unwrap_document(document(full_raw)),
                input_sha256=sha(full_raw), expected_context=normalized, resource_reader=resources.__getitem__)
        except (ValueError, TypeError, KeyError, yaml.YAMLError):
            reasons.append("current_semantic_contract_invalid")
    row["reasons"] = sorted(set(reasons))
    row["pending"] = sorted(set(pending))
    row["eligible_for_condition_review"] = not reasons and not pending and not record["reasons"]
    return row


def repeat_panel(rows):
    """Three generation replicates or a reported n are not three ratings."""
    groups = {}
    for row in rows:
        if row["reasons"]:
            continue
        key = (row["version"], row["evaluator"], row["context_hash"])
        groups.setdefault(key, []).append(row)
    best = max(groups.values(), key=lambda group: len({row["session_id"] for row in group
        if isinstance(row["session_id"], str) and row["session_id"].strip()}), default=[])
    sessions = {row["session_id"] for row in best if isinstance(row["session_id"], str) and row["session_id"].strip()}
    identities = {row["sha256"] for row in best}
    distinct = min(len(sessions), len(identities))
    return {"declared_n": sorted({row["declared_repeat_n"] for row in rows
            if type(row["declared_repeat_n"]) is int and row["declared_repeat_n"] >= 0}),
        "contract_valid_rating_files": len(best), "distinct_reported_sessions": distinct,
        "target_conditions_selected": bool(best) and all(not row["pending"] for row in best),
        "reported_n_at_least_three": any(type(row["declared_repeat_n"]) is int and row["declared_repeat_n"] >= 3 for row in rows),
        "three_distinct_session_claims_present": distinct >= 3,
        "independence_verified": False,
        "basis": "Content-bound files and distinct recorded session identities; no retained transcript/receipt authentication in this store audit."}


def audit(root, *, arms=None, rubric20_version="3.0", evaluator_model=None, contexts=None):
    root = Path(root).resolve()
    arms = ARMS if arms is None else arms
    if rubric20_version not in ("3.0", "4.0"):
        raise ValueError("rubric20 target must be 3.0 or 4.0")
    contexts = {} if contexts is None else contexts
    normalized_contexts = {project: normalize_context(value) for project, value in contexts.items()}
    snapshots = {rubric: instrument(rubric, "3.0" if rubric == "rubric10" else rubric20_version)
                 for rubric in RUBRICS}
    evaluations_found, problems, stores = evaluations(root)
    records, rescore, excluded, associated = [], [], [], set()
    for arm, (prefix, projects) in sorted(arms.items()):
        for project in sorted(set(projects)):
            for replicate in (1, 2, 3):
                label = f"{prefix}_rep{replicate}"
                record, raw = load_record(root, arm, project, label)
                record["replicate"] = replicate
                record["evaluations"] = {}
                for rubric in RUBRICS:
                    candidates = [evaluation for evaluation in evaluations_found
                                  if evaluation["store"] == rubric and association(root, evaluation, record)]
                    associated.update(evaluation["path"] for evaluation in candidates)
                    rows = [inspect_evaluation(root, evaluation, record, raw,
                        version="3.0" if rubric == "rubric10" else rubric20_version,
                        evaluator_model=evaluator_model, target_context=normalized_contexts.get(project),
                        instrument_snapshot=snapshots[rubric])
                        for evaluation in candidates]
                    reasons = set(record["reasons"])
                    if not rows:
                        reasons.add("evaluation_missing_from_selected_stores")
                    if rows and not any(not row["reasons"] for row in rows):
                        reasons.update(reason for row in rows for reason in row["reasons"])
                    pending = sorted({reason for row in rows for reason in row["pending"]})
                    panel = repeat_panel(rows) if rubric == "rubric20" else None
                    block = {"files": rows, "file_count": len(rows), "reasons": sorted(reasons),
                             "pending": pending, "repeat_panel": panel,
                             "comparable_for_final_v10": False,
                             "status": "rescore_or_ingestion_required" if reasons else "condition_review_pending"}
                    record["evaluations"][rubric] = block
                    if reasons:
                        rescore.append({"arm": arm, "project": project, "label": label, "rubric": rubric,
                            "target_version": "3.0" if rubric == "rubric10" else rubric20_version,
                            "reasons": sorted(reasons), "action": "ingest_bound_current_rating_or_rescore"})
                records.append(record)
        # Retained invalid/out-of-cohort v8 canaries remain visible, not pooled.
        for path in sorted((root / "data/d4d_concatenated").glob(f"*_core/{prefix}_rep*/*_provenance.yaml")):
            project = path.name.removesuffix("_provenance.yaml")
            if project not in projects:
                declared_valid, exclusion = None, "outside_selected_arm_project_roster"
                try:
                    declaration = document(read_local(root, path))
                    declared_valid = mapping(declaration.get("validation")).get("passed")
                    if declared_valid is False:
                        exclusion = "declared_invalid_generation_outside_selected_roster"
                except (OSError, ValueError, yaml.YAMLError, UnicodeError, RecursionError):
                    exclusion = "unreadable_provenance_outside_selected_roster"
                excluded.append({"arm": arm, "project": project, "label": path.parent.name,
                    "provenance": relative(root, path), "validation_passed": declared_valid,
                    "reason": exclusion})
    # An artifact path can be reused by more than one provenance identity.
    # A label/path disagreement is therefore visible in every candidate record;
    # never resolve it by selecting the first or by trusting a filename.
    links = {}
    for record in records:
        for rubric, block in record["evaluations"].items():
            for row in block["files"]:
                links.setdefault(row["path"], []).append((record, rubric, block, row))
    for candidates in links.values():
        if len(candidates) <= 1:
            continue
        for record, rubric, block, row in candidates:
            row["reasons"] = sorted(set(row["reasons"]) | {"evaluation_linkage_ambiguous"})
            row["eligible_for_condition_review"] = False
    for record in records:
        for rubric, block in record["evaluations"].items():
            if block["files"] and not any(not row["reasons"] for row in block["files"]):
                block["reasons"] = sorted(set(block["reasons"]) |
                    {reason for row in block["files"] for reason in row["reasons"]})
                block["status"] = "rescore_or_ingestion_required"
            if rubric == "rubric20":
                block["repeat_panel"] = repeat_panel(block["files"])
            if block["reasons"]:
                existing = next((item for item in rescore if all(item[key] == record[key]
                    for key in ("arm", "project", "label")) and item["rubric"] == rubric), None)
                if existing is not None:
                    existing["reasons"] = block["reasons"]
                else:
                    rescore.append({**{key: record[key] for key in ("arm", "project", "label")},
                        "rubric": rubric, "target_version": "3.0" if rubric == "rubric10" else rubric20_version,
                        "reasons": block["reasons"], "action": "ingest_bound_current_rating_or_rescore"})
    rescore.sort(key=lambda item: tuple(item[key] for key in ("arm", "project", "label", "rubric")))
    summary = []
    for arm, (_, projects) in sorted(arms.items()):
        for project in sorted(set(projects)):
            group = [row for row in records if row["arm"] == arm and row["project"] == project]
            summary.append({"arm": arm, "project": project, "expected_records": len(group),
                "canonical_labels": [row["label"] for row in group if row["canonical"]],
                "provenance_present": sum(bool(row["provenance_files"]) for row in group),
                "evaluations_present": {rubric: sum(row["evaluations"][rubric]["file_count"] > 0 for row in group) for rubric in RUBRICS},
                "rescore_or_ingestion_tuples": sum(item["arm"] == arm and item["project"] == project for item in rescore)})
    repeat_gaps = []
    for project in sorted({row["project"] for row in records}):
        candidates = [{"arm": row["arm"], "project": project, "label": row["label"], "rubric": "rubric20"}
                      for row in records if row["project"] == project and not row["reasons"]
                      and row["evaluations"]["rubric20"]["repeat_panel"]["three_distinct_session_claims_present"]]
        repeat_gaps.append({"project": project, "status": "independence_and_selection_review_pending" if candidates
                            else "fixed_record_selection_and_repeat_ratings_pending",
                            "three_session_candidate_tuples": candidates,
                            "action": "Select one fixed record per project; ingest or obtain >=3 ratings under the selected conditions, then authenticate separate rating sessions.",
                            "independence_verified": False})
    return {"format": "historical_evaluation_comparability_audit_v1",
        "scope": {"stores": stores, "filesystem_globs_include_ignored_and_hidden": True,
            "other_evaluation_directories_audited": False, "historical_files_mutated": False,
            "absence_basis": "Only the explicitly listed nonrecursive label_aware stores and selected provenance paths.",
            "repeat_policy": "At least three independent ratings of one fixed selected record per project; no requirement to repeat every generation replicate."},
        "targets": {"rubric10": "3.0", "rubric20": rubric20_version,
            "evaluator_model": evaluator_model, "context_digests": {key: context_digest(value) for key, value in sorted(normalized_contexts.items())},
            "context_human_review_verified": False},
        "totals": {"expected_records": len(records), "parseable_files_in_selected_stores": len(evaluations_found),
            "associated_evaluation_files": len(associated), "rescore_or_ingestion_tuples": len(rescore),
            "excluded_records": len(excluded), "unreadable_evaluation_files": len(problems),
            "unassociated_evaluation_files": len(evaluations_found) - len(associated),
            "projects_with_repeat_actions": len(repeat_gaps)},
        "summary": summary, "records": records, "rescore_tuples": rescore,
        "repeat_panel_actions": repeat_gaps,
        "excluded_records": excluded, "unreadable_evaluations": problems,
        "unassociated_evaluations": [{key: row[key] for key in ("path", "store", "sha256")}
                                    for row in evaluations_found if row["path"] not in associated],
        "interpretation": "Inventory and deterministic contract checks only. Presence, hashes, model names and reported repeat counts do not establish human approval, runtime authenticity, independence or scientific comparability. Review retained ratings outside these stores before commissioning rescoring."}


def markdown(result):
    def esc(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["# Historical evaluation comparability audit", "", result["interpretation"], "",
        f"Targets: rubric10 {result['targets']['rubric10']}; rubric20 {result['targets']['rubric20']}.",
        f"Expected records: {result['totals']['expected_records']}; associated evaluation files: {result['totals']['associated_evaluation_files']}; rescore/ingestion tuples: {result['totals']['rescore_or_ingestion_tuples']}.",
        "Applicability context presence is not human review. Counts cover only the named stores.", "",
        "| Arm | Project | Records | Provenance | Rubric10 present | Rubric20 present | Rescore/ingestion tuples |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for row in result["summary"]:
        lines.append("| " + " | ".join(esc(value) for value in (row["arm"], row["project"], row["expected_records"],
            row["provenance_present"], row["evaluations_present"]["rubric10"], row["evaluations_present"]["rubric20"],
            row["rescore_or_ingestion_tuples"])) + " |")
    lines += ["", "Canonical labels are provenance declarations, not independently reselected winners.",
              "", "## Recorded conditions", "", "| Arm | Project | Label | Rubric | File | Version | Evaluator | Context block/hash | Repeat evidence |",
              "|---|---|---|---|---|---|---|---|---|"]
    for record in result["records"]:
        for rubric, block in record["evaluations"].items():
            for row in block["files"]:
                panel = block["repeat_panel"]
                repeat = "not requested" if panel is None else f"{panel['distinct_reported_sessions']} distinct session claims; independence unverified"
                lines.append("| " + " | ".join(esc(value) for value in (record["arm"], record["project"], record["label"], rubric,
                    row["path"], row["version"], row["evaluator"], f"{row['context_block_present']} / {row['context_hash'] or 'missing'}", repeat)) + " |")
    lines += ["", "## Exact rescore or ingestion queue", "", "| Arm | Project | Label | Rubric | Target | Reasons |",
              "|---|---|---|---|---|---|"]
    for row in result["rescore_tuples"]:
        lines.append("| " + " | ".join(esc(value) for value in (row["arm"], row["project"], row["label"], row["rubric"],
            row["target_version"], "; ".join(row["reasons"]))) + " |")
    lines += ["", "No automatic rescore is authorized. First check retained ratings outside the selected stores.",
              f"Excluded records: {len(result['excluded_records'])}; unassociated evaluation files: {len(result['unassociated_evaluations'])}; unreadable files: {len(result['unreadable_evaluations'])}.", ""]
    lines += ["## Repeat-panel action queue", ""]
    for row in result["repeat_panel_actions"]:
        lines.append(f"- {row['project']}: {row['status']}. {row['action']}")
    lines += ["", "## Canonical declarations and excluded records", ""]
    for row in result["summary"]:
        lines.append(f"- {row['arm']} / {row['project']}: canonical labels: {', '.join(row['canonical_labels']) or 'none recorded'}.")
    for row in result["excluded_records"]:
        lines.append(f"- Excluded: {row['arm']} / {row['project']} / {row['label']}: {row['reason']}.")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--rubric20-version", choices=("3.0", "4.0"), default="3.0")
    parser.add_argument("--evaluator-model", help="Explicit final-condition evaluator; no alias equivalence inferred")
    parser.add_argument("--context", action="append", default=[], metavar="PROJECT=PATH",
                        help="Independently selected context to compare, not a human-approval attestation")
    args = parser.parse_args(argv)
    root, contexts = args.root.resolve(), {}
    for item in args.context:
        project, separator, name = item.partition("=")
        path = local_path(root, name)
        if not separator or project in contexts or project not in PROJECTS or path is None:
            parser.error("--context requires unique PROJECT=PATH inside the selected checkout")
        contexts[project] = document(read(path))
    result = audit(root, rubric20_version=args.rubric20_version,
                   evaluator_model=args.evaluator_model, contexts=contexts)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) if args.format == "json" else markdown(result), end="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
