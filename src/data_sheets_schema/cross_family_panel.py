"""Portable, offline declarations for a semantic cross-family panel (#4606).

This module registers inputs and planned rating slots. It neither runs raters
nor accepts results, scores, scientific approvals, or execution authorization.
Rechecking reconstructs the registration from captured bytes, not cached flags.
"""
from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path, PurePosixPath
import re

from data_sheets_schema import nested_support_results as saved
from data_sheets_schema.evaluation_context import (
    COLLECTION_POLICY, PREDICATES, context_digest, dataset_units, normalize_context,
)
from data_sheets_schema.evaluation_model import model_family, same_family
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.support_plan import canonical, sha256

FORMAT = "cross_family_panel_v1"
DECLARATION_FORMAT = "cross_family_panel_declaration_v1"
MAX_PANEL_BYTES = saved.MAX_MANIFEST_BYTES
MAX_RECORDS = 10_000
MAX_CELLS = 10_000
RUBRICS = ("rubric10", "rubric20")
ROLES = ("same_family", "cross_family")
DECISIONS = ("selection_policy", "rater_policy", "route", "budget",
             "scientific_review", "execution_authorization")
V4_PREDECESSOR = ".claude/agents/d4d-rubric20-semantic.md"
V4_PREDECESSOR_SHA256 = "35de3a37264e80f48e6e037fed42b6cc586152058d4da6c08bad93b8096f588b"
# The same validator authority captured by reference_rescore, plus the model
# disclosure and panel implementation. Capturing code does not execute it.
VALIDATOR_SUPPORT = (
    "src/data_sheets_schema/resources.py",
    "src/data_sheets_schema/evaluation/__init__.py",
    "src/data_sheets_schema/evaluation/validate.py",
    "src/data_sheets_schema/evaluation_context.py",
    "src/data_sheets_schema/judge_contract.py",
    "src/data_sheets_schema/semantic_scope.py",
    "src/data_sheets_schema/semantic_instrument.py",
    "src/data_sheets_schema/semantic_evidence.py",
    "src/data_sheets_schema/semantic_evidence_authority.py",
    "src/data_sheets_schema/agent_pin.py",
    "src/data_sheets_schema/evaluation_model.py",
    "src/data_sheets_schema/cross_family_panel.py",
)
LIMITATIONS = (
    "This is an offline registration, not a result, score, statistical comparison, or execution permit.",
    "Model, family, rater, route, provenance and review identities are caller declarations, not authentication.",
    "Captured provenance is not checked for association with the selected record or generator.",
    "Missing applicability predicates remain unknown; they are not evidence of non-applicability.",
    "Review references do not establish human scientific approval or lift any existing review hold.",
    "Distinct input hashes do not prove independent observations; identical bytes are explicitly clustered.",
    "Captured instrument and validator bytes identify a future instrument; no evaluation has been accepted.",
    "A predecessor hash is a declared reference, not proof of continuity or authorization.",
)
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class PanelError(ValueError):
    """A declaration or captured panel does not meet this registration contract."""


def _need(condition, reason):
    if not condition:
        raise PanelError(reason)


def _closed(value, keys, label):
    _need(type(value) is dict and set(value) == set(keys), f"{label} requires exactly: {', '.join(sorted(keys))}")
    return value


def _text(value, label):
    _need(type(value) is str and bool(value) and value == value.strip() and len(value) <= 4096,
          f"{label} must be nonblank trimmed text within 4096 characters")
    return value


def _optional_text(value, label):
    return None if value is None else _text(value, label)


def _identifier(value, label):
    _need(type(value) is str and bool(_ID.fullmatch(value)), f"{label} must be a bounded identifier")
    return value


def _digest(value, label):
    _need(type(value) is str and bool(_SHA.fullmatch(value)), f"{label} must be a SHA256 digest")
    return value


def _path(value):
    _text(value, "artifact path")
    path = PurePosixPath(value)
    _need(not path.is_absolute() and path.as_posix() == value and value != "."
          and ".." not in path.parts and "\\" not in value and "\0" not in value,
          "artifact path must be a normalized relative POSIX path inside the declared root")
    return value


def _list(value, label, maximum):
    _need(type(value) is list and len(value) <= maximum, f"{label} must be a list within {maximum} entries")
    return value


def _family(model, family, label):
    _optional_text(model, f"{label} model")
    _optional_text(family, f"{label} family")
    actual = model_family(model)
    _need(family == actual, f"{label} family differs from the declared model's recognized family")
    return actual


def _structured(raw, label, *, yaml_allowed=False, limit=saved.MAX_ARTIFACT_BYTES):
    return saved._read(raw, label, limit=limit, yaml_allowed=yaml_allowed)


def _registration(capture, declaration_raw, read_path, read_authority=None):
    declaration = _closed(_structured(declaration_raw, "panel declaration", limit=MAX_PANEL_BYTES), {
        "format", "panel_id", "predecessor_sha256", "matrix", "records", "instruments", "slots", "decisions",
    }, "panel declaration")
    _need(declaration["format"] == DECLARATION_FORMAT, "explicit cross_family_panel_declaration_v1 is required")
    panel_id = _identifier(declaration["panel_id"], "panel_id")
    predecessor = declaration["predecessor_sha256"]
    if predecessor is not None:
        _digest(predecessor, "predecessor_sha256")
    captured_files = {}
    authority_paths = set()
    if read_authority is None:
        read_authority = read_path

    def artifact(path, expected=None, *, authority=False):
        path = _path(path)
        if authority:
            authority_paths.add(path)
        if path not in captured_files:
            raw = read_authority(path) if authority else read_path(path)
            _need(bool(raw), f"artifact is empty: {path}")
            captured_files[path] = capture.add(raw)
        pin = captured_files[path]
        if expected is not None:
            _need(pin["sha256"] == _digest(expected, "artifact sha256"), f"artifact hash differs: {path}")
        return {"path": path, **pin}

    def reference(value, label):
        _closed(value, {"path", "sha256"}, label)
        _need(_path(value["path"]) not in authority_paths, "caller evidence cannot alias an instrument authority path")
        return artifact(value["path"], value["sha256"])

    pending = []

    def unresolved(subject, reason):
        pending.append({"subject": subject, "reason": reason})

    matrix = _closed(declaration["matrix"], {"projects", "cohorts"}, "matrix")
    for axis in ("projects", "cohorts"):
        values = _list(matrix[axis], f"matrix {axis}", MAX_CELLS)
        _need(bool(values), f"matrix {axis} cannot be empty")
        for value in values:
            _text(value, f"matrix {axis} entry")
        _need(len(values) == len(set(values)), f"duplicate matrix {axis}")
    _need(len(matrix["projects"]) * len(matrix["cohorts"]) <= MAX_CELLS, "matrix exceeds cell bound")
    decisions = _closed(declaration["decisions"], DECISIONS, "decisions")
    for name, decision in decisions.items():
        _closed(decision, {"status", "reference"}, f"decision {name}")
        _need(decision["status"] in ("pending", "declared"), f"decision {name} has unsupported status")
        _optional_text(decision["reference"], f"decision {name} reference")
        if decision["status"] == "declared":
            _text(decision["reference"], f"decision {name} reference")
        else:
            unresolved(f"decisions.{name}", "pending caller decision")

    instruments = []
    names = set()
    for selection in _list(declaration["instruments"], "instruments", 2):
        _closed(selection, {"rubric", "version"}, "instrument selection")
        rubric, version = selection["rubric"], selection["version"]
        _need(rubric in RUBRICS and rubric not in names, "unknown or duplicate semantic rubric")
        names.add(rubric)
        try:
            selected = select_semantic_instrument(rubric, version)
        except (ValueError, TypeError) as exc:
            raise PanelError(str(exc)) from exc
        resources = {"rubric": artifact(selected.rubric_path, authority=True),
                     "definition": artifact(selected.definition_path, authority=True),
                     "schema": artifact(selected.schema_path, authority=True), "evidence_authority": None,
                     "predecessor_definition": None}
        schema = _structured(capture.get(resources["schema"]), "semantic schema")
        _need(type(schema) is dict, "semantic schema must be a mapping")
        if selected.evidence_authority_path is not None:
            authority_pin = artifact(selected.evidence_authority_path, authority=True)
            authority = _structured(capture.get(authority_pin), "semantic evidence authority")
            _need(type(authority) is dict and authority.get("semantic_version") == "3.0"
                  and authority.get("authority_version") == "1.0", "invalid semantic v3 evidence authority")
            authority_names = authority.get("names")
            _need(type(authority_names) is list and bool(authority_names)
                  and all(type(n) is str and n for n in authority_names)
                  and authority_names == sorted(set(authority_names)), "invalid semantic evidence names")
            resources["evidence_authority"] = authority_pin
        if version == "4.0":
            resources["predecessor_definition"] = artifact(V4_PREDECESSOR, V4_PREDECESSOR_SHA256, authority=True)
        acceptance = "historical_classification_only" if version == "2.0" else "current_new_output_validator"
        if version == "2.0":
            unresolved(f"instruments.{rubric}.new_output_acceptance",
                       "semantic 2.0 is historical_classification_only; the captured validator refuses new outputs")
        instruments.append({"rubric": rubric, "version": version, "agent": selected.agent,
                            "acceptance_contract": acceptance, "resources": resources})
    _need(names == set(RUBRICS), "both rubric10 and rubric20 must be explicitly selected")
    instruments.sort(key=lambda row: row["rubric"])
    authorities = [artifact(path, authority=True) for path in VALIDATOR_SUPPORT]

    records, by_id, logical, content = [], {}, set(), defaultdict(list)
    for declaration_row in _list(declaration["records"], "records", MAX_RECORDS):
        row = _closed(declaration_row, {"record_id", "project", "cohort", "label", "method", "replicate",
                                       "input", "provenance", "generator", "context"}, "selected record")
        record_id = _identifier(row["record_id"], "record_id")
        _need(record_id not in by_id, "duplicate record_id")
        for key in ("project", "cohort", "label", "method"):
            _text(row[key], f"record {key}")
        _need(row["project"] in matrix["projects"] and row["cohort"] in matrix["cohorts"],
              "record lies outside the required matrix")
        _need(type(row["replicate"]) is int and row["replicate"] > 0, "replicate must be a positive integer")
        identity = tuple(row[k] for k in ("project", "cohort", "label", "method", "replicate"))
        _need(identity not in logical, "duplicate logical record identity")
        logical.add(identity)
        input_pin = reference(row["input"], "record input")
        document = _structured(capture.get(input_pin), "record input", yaml_allowed=True)
        try:
            units = [{"path": path, "id": unit.get("id")} for path, unit in dataset_units(document)]
        except (ValueError, TypeError) as exc:
            raise PanelError(f"record scope cannot be determined: {exc}") from exc
        scope = {"collection_metadata_inherited": False,
                 "policy": COLLECTION_POLICY if len(units) > 1 else "single_dataset", "units": units}
        provenance = None if row["provenance"] is None else reference(row["provenance"], "record provenance")
        generator = _closed(row["generator"], {"model", "family"}, "generator")
        family = _family(generator["model"], generator["family"], "generator")
        if family is None:
            unresolved(f"records.{record_id}.generator", "generator model family is unknown")
        context = _closed(row["context"], {"source", "review_status", "review_reference"}, "record context")
        _need(context["review_status"] in ("pending", "declared_reviewed"), "unsupported context review_status")
        _optional_text(context["review_reference"], "context review_reference")
        if context["review_status"] == "declared_reviewed":
            _text(context["review_reference"], "context review_reference")
        else:
            unresolved(f"records.{record_id}.context.review", "context review is pending")
        context_pin = None if context["source"] is None else reference(context["source"], "context source")
        original_context = None if context_pin is None else _structured(capture.get(context_pin), "context", yaml_allowed=True)
        try:
            normalized = normalize_context(original_context)
        except ValueError as exc:
            raise PanelError(f"invalid applicability context: {exc}") from exc
        unknown = sorted(predicate for predicate in PREDICATES
                         if normalized.get(predicate, {}).get("value") is None)
        if context_pin is None:
            unresolved(f"records.{record_id}.context.source", "context source absent; predicates remain unknown")
        resolved = {**{key: row[key] for key in ("record_id", "project", "cohort", "label", "method", "replicate")},
                    "input": input_pin, "provenance": provenance,
                    "provenance_association": "not_supplied" if provenance is None else "unverified_declaration",
                    "generator": dict(generator), "context": {
                        "source": context_pin, "normalized": normalized, "sha256": context_digest(normalized),
                        "unknown_predicates": unknown, "review_status": context["review_status"],
                        "review_reference": context["review_reference"],
                        "review_subject": "unknown_context_declaration" if context_pin is None else "supplied_context",
                        "approval_authenticated": False}, "evaluation_scope": scope}
        records.append(resolved)
        by_id[record_id] = resolved
        content[input_pin["sha256"]].append(record_id)

    declared_slots, attempts = {}, set()
    for row in _list(declaration["slots"], "slots", 4 * MAX_RECORDS):
        _closed(row, {"record_id", "rubric", "role", "attempt_id", "model", "family", "rater", "route"}, "rating slot")
        _need(type(row["record_id"]) is str and row["record_id"] in by_id, "slot names an unselected record")
        _need(row["rubric"] in RUBRICS and row["role"] in ROLES, "slot has unsupported rubric or role")
        key = (row["record_id"], row["rubric"], row["role"])
        _need(key not in declared_slots, "duplicate rating slot")
        attempt = _identifier(row["attempt_id"], "attempt_id")
        _need(attempt not in attempts, "duplicate attempt_id")
        attempts.add(attempt)
        family = _family(row["model"], row["family"], "rating slot")
        for field in ("rater", "route"):
            _optional_text(row[field], f"slot {field}")
            if row[field] is None:
                unresolved(f"slots.{attempt}.{field}", f"{field} is not declared")
        relation = same_family(row["model"], by_id[row["record_id"]]["generator"]["model"])
        if relation is not None:
            _need(relation == (row["role"] == "same_family"), "slot role contradicts recognized generator/evaluator families")
        else:
            unresolved(f"slots.{attempt}.family_relation", "model family relation is unknown")
        declared_slots[key] = {**row, "family_relation": "unknown" if relation is None else
                               ("same_family" if relation else "cross_family")}

    slots, missing_slots = [], []
    for record in records:
        for instrument in instruments:
            binding = {"record_id": record["record_id"],
                       "record_identity": {key: record[key] for key in ("project", "cohort", "label", "method", "replicate")},
                       "input_sha256": record["input"]["sha256"], "context_sha256": record["context"]["sha256"],
                       "evaluation_scope": record["evaluation_scope"], "instrument": instrument}
            binding_sha = sha256(canonical(binding))
            for role in ROLES:
                key = (record["record_id"], instrument["rubric"], role)
                identity = {"record_id": key[0], "rubric": key[1], "role": role}
                if key in declared_slots:
                    slot = {**declared_slots[key], "status": "declared"}
                else:
                    missing_slots.append(identity)
                    slot = {**identity, "status": "missing", "attempt_id": None, "model": None,
                            "family": None, "rater": None, "route": None, "family_relation": "unknown"}
                slots.append({**slot, "binding": binding, "binding_sha256": binding_sha})

    cells = [{"project": project, "cohort": cohort,
              "record_ids": [r["record_id"] for r in records if r["project"] == project and r["cohort"] == cohort]}
             for project in matrix["projects"] for cohort in matrix["cohorts"]]
    clusters = [{"input_sha256": digest, "record_ids": ids}
                for digest, ids in sorted(content.items()) if len(ids) > 1]
    result = {"format": FORMAT, "kind": "registration", "panel_id": panel_id,
              "predecessor_sha256": predecessor, "declaration": capture.add(declaration_raw),
              "captured_files": captured_files, "matrix": matrix, "cells": cells,
              "records": records, "instruments": instruments, "validator_authority": authorities,
              "slots": slots, "missing_cells": [{"project": cell["project"], "cohort": cell["cohort"]}
                                                  for cell in cells if not cell["record_ids"]],
              "missing_slots": missing_slots, "pending_decisions": pending, "decisions": decisions,
              "duplicate_content_clusters": clusters,
              "counts": {"required_cells": len(cells), "selected_records": len(records),
                         "distinct_input_artifacts": len(content), "required_slots": len(slots),
                         "declared_slots": len(declared_slots)},
              "execution_authorized": False, "scientific_eligibility": False,
              "limitations": list(LIMITATIONS)}
    # Bound the exact published bytes before any destination is created, then
    # detach repeated bindings and imported/caller values before returning.
    serialized = canonical(result)
    _need(len(serialized) + 1 <= MAX_PANEL_BYTES, "panel output exceeds manifest byte bound")
    return _structured(serialized, "reconstructed panel", limit=MAX_PANEL_BYTES)


def _write_panel(output, capture, result):
    """Publish exclusively; a new child of a corpus root cannot replace inputs."""
    output = Path(output)
    raw = canonical(result) + b"\n"
    _need(len(raw) <= MAX_PANEL_BYTES, "panel output exceeds manifest byte bound")
    _need(not output.exists() and not output.is_symlink(), "output already exists")
    _need(output.parent.is_dir(), "output parent must exist")
    try:
        output.mkdir()
        artifacts = output / "artifacts"
        artifacts.mkdir()
        for digest, artifact in capture.blobs.items():
            with (artifacts / digest).open("xb") as stream:
                stream.write(artifact)
                stream.flush()
                os.fsync(stream.fileno())
        with (output / "panel.json").open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise PanelError(f"cannot publish new panel: {exc}") from exc


def prepare_panel(declaration: Path, output: Path, *, root: Path) -> dict:
    """Capture a closed declaration and selected corpus into a new directory."""
    try:
        from data_sheets_schema import resources

        capture = saved.Capture(root)
        raw = saved._file(Path(declaration), MAX_PANEL_BYTES)

        def corpus_path(name):
            path = capture.root
            for part in PurePosixPath(name).parts:
                path = path / part
                _need(not path.is_symlink(), "artifact paths cannot traverse symlinks")
            return path

        def read_path(name):
            path = corpus_path(name)
            return saved._file(path, saved.MAX_ARTIFACT_BYTES)

        def read_authority(name):
            # No resource_path/cwd lookup: the installed/imported package owns
            # canonical instruments; root only owns the caller's evidence.
            relative = PurePosixPath(name)
            if relative.parts[:2] == ("src", "data_sheets_schema"):
                trusted = resources.PACKAGE_ROOT.joinpath(*relative.parts[2:])
            else:
                trusted = (resources.CHECKOUT_ROOT or resources.INSTALL_ROOT) / name
            asset = saved._file(trusted, saved.MAX_ARTIFACT_BYTES)
            shadow = corpus_path(name)
            if shadow.exists():
                _need(read_path(name) == asset, f"caller authority differs from trusted package asset: {name}")
            return asset

        result = _registration(capture, raw, read_path, read_authority)
        _write_panel(output, capture, result)
        return result
    except saved.ResultError as exc:
        raise PanelError(str(exc)) from exc


def _recheck(capture, raw):
    """Reconstruct an existing panel from a caller's captured artifact store."""
    value = _structured(raw, "panel manifest", limit=MAX_PANEL_BYTES)
    _need(type(value) is dict, "panel manifest must be a mapping")
    files = value.get("captured_files")
    _need(type(files) is dict, "panel manifest requires captured_files")

    def read_path(name):
        _need(name in files, f"captured artifact is missing: {name}")
        return capture.get(files[name])

    _need(type(value.get("declaration")) is dict, "panel declaration pin is missing")
    declaration_raw = capture.get(value["declaration"], limit=MAX_PANEL_BYTES)
    expected = _registration(capture, declaration_raw, read_path)
    _need(canonical(value) == canonical(expected), "panel differs from captured reconstruction")
    return expected


def recheck_panel(directory: Path) -> dict:
    """Reconstruct from captured artifacts alone, including missing/pending rows."""
    try:
        capture = saved.Capture(directory)
        # The manifest is bounded separately; it is not a referenced artifact
        # and must not consume the captured-artifact budget a second time.
        raw = saved._file(capture.root / "panel.json", MAX_PANEL_BYTES)
        return _recheck(capture, raw)
    except saved.ResultError as exc:
        raise PanelError(str(exc)) from exc
