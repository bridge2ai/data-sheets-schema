"""Captured semantic panel ratings: mechanical acceptance, never authorization.

All scoring resources come from the selected captured panel. Captured Python is
never imported: panels naming other validator source bytes are unsupported.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path, PurePosixPath

from data_sheets_schema import cross_family_panel as panels
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema import resources
from data_sheets_schema.evaluation_context import normalize_context, unwrap_document
from data_sheets_schema.support_plan import canonical, sha256

FORMAT = "cross_family_panel_results_v1"
SUBMISSIONS_FORMAT = "cross_family_panel_submissions_v1"
MAX_RESULTS_BYTES = saved.MAX_MANIFEST_BYTES
MAX_RESULT_BYTES = saved.MAX_RESPONSE_BYTES
IDENTITY = ("record_id", "rubric", "version", "role", "attempt_id", "model", "family", "rater", "route", "binding_sha256")
LIMITATIONS = (
    "Accepted means offline structural and internal consistency under the captured semantic instrument only.",
    "Slot, model, family, rater and route associations are caller declarations, not authenticated provider execution.",
    "Mechanical evidence checks do not establish that cited content supports a judgement or that scores are scientifically correct.",
    "No human review, statistical agreement, calibration, independence, execution authorization or scientific eligibility is established.",
    "All required panel slots remain in the denominator, including missing, rejected and unsupported ratings.",
    "Only panels with the current supported validator source pins can be accepted; captured Python is never executed.",
    "Hashes check consistency with the declared panel, not the authenticity of a caller who can replace the entire package.",
)

PanelResultError = panels.PanelError


def _key(row):
    return tuple(row[name] for name in ("record_id", "rubric", "role"))


def _source_pin(name):
    relative = PurePosixPath(name)
    panels._need(relative.parts[:2] == ("src", "data_sheets_schema"), "validator source must belong to the imported package")
    return {"path": name, **saved._pin(saved._file(resources.PACKAGE_ROOT.joinpath(*relative.parts[2:]), saved.MAX_ARTIFACT_BYTES))}


def _code_authority(panel):
    """Compare source identities only; never resolve installed instruments."""
    current = [_source_pin(name) for name in panels.VALIDATOR_SUPPORT]
    declared = {pin["path"]: pin for pin in panel["validator_authority"]}
    mismatches = [pin["path"] for pin in current if declared.get(pin["path"]) != pin]
    return current, mismatches


def _identity(slot):
    return {**{key: slot[key] for key in IDENTITY if key != "version"},
            "version": slot["binding"]["instrument"]["version"]}


def _submissions(raw, panel_raw, panel):
    value = panels._closed(saved._read(raw, "panel submissions", limit=MAX_RESULTS_BYTES),
                           {"format", "panel_sha256", "submissions"}, "panel submissions")
    panels._need(value["format"] == SUBMISSIONS_FORMAT, "explicit cross_family_panel_submissions_v1 is required")
    panels._need(panels._digest(value["panel_sha256"], "panel_sha256") == sha256(panel_raw),
                 "submissions name another panel SHA256")
    slots = {_key(slot): slot for slot in panel["slots"]}
    selected, attempts = {}, set()
    for row in panels._list(value["submissions"], "submissions", len(slots)):
        panels._closed(row, {*IDENTITY, "result"}, "rating submission")
        for name in ("record_id", "rubric", "role", "version"):
            panels._text(row[name], name)
        for name in ("attempt_id", "model", "family", "rater", "route"):
            panels._optional_text(row[name], name)
        panels._digest(row["binding_sha256"], "binding_sha256")
        key = _key(row)
        panels._need(key in slots, "submission names an unknown panel slot")
        panels._need(key not in selected, "duplicate submission for a panel slot")
        if row["attempt_id"] is not None:
            panels._need(row["attempt_id"] not in attempts, "duplicate submitted attempt_id")
            attempts.add(row["attempt_id"])
        panels._closed(row["result"], {"path", "sha256"}, "submitted result")
        panels._path(row["result"]["path"])
        panels._digest(row["result"]["sha256"], "submitted result SHA256")
        selected[key] = row
    return selected


def _payload_identity(result, slot, record, instrument):
    """Reconcile payload declarations too; a correct sidecar cannot relabel them."""
    errors = []
    expected = {"rubric": slot["rubric"] + "-semantic", "version": instrument["version"],
                "project": record["project"], "method": record["method"], "d4d_file": record["input"]["path"]}
    for key, value in expected.items():
        if result.get(key) != value:
            errors.append(f"payload.{key} conflicts with the registered slot")
    model = result.get("model")
    if not isinstance(model, dict) or model.get("name") != slot["model"]:
        errors.append("payload.model.name conflicts with the registered model")
    elif "family" in model and model["family"] != slot["family"]:
        errors.append("payload.model.family conflicts with the registered family")
    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("payload.metadata must be a mapping")
        metadata = {}
    if metadata.get("instrument_sha256") != instrument["resources"]["definition"]["sha256"]:
        errors.append("payload.metadata.instrument_sha256 conflicts with the captured definition")
    # Historical aliases are independently checked whenever supplied.
    aliases = {"label": record["label"], "generation_label": record["label"],
               "cohort": record["cohort"], "replicate": record["replicate"],
               "generation_rep": record["replicate"], "record_id": slot["record_id"],
               "attempt_id": slot["attempt_id"], "role": slot["role"], "route": slot["route"],
               "rater": slot["rater"], "family": slot["family"],
               "rubric_hash": instrument["resources"]["rubric"]["sha256"],
               "d4d_file_hash": record["input"]["sha256"]}
    evaluator_ids = []
    for label, section in (("payload", result), ("metadata", metadata),
                           ("evaluation_metadata", result.get("evaluation_metadata", {}))):
        if not isinstance(section, dict):
            errors.append(f"payload.{label} must be a mapping")
            continue
        for key, value in aliases.items():
            if key in section and canonical(section[key]) != canonical(value):
                errors.append(f"payload.{label}.{key} conflicts with the registered slot")
        if "evaluator_id" in section:
            evaluator_ids.append(section["evaluator_id"])
    if (slot["rater"] is not None and not evaluator_ids) or any(value != slot["rater"] for value in evaluator_ids):
        errors.append("payload.evaluator_id conflicts with the registered rater")
    return errors


def _assessment(capture, panel, slot, submission, pin, code_mismatches):
    row = {**{name: slot[name] for name in ("record_id", "rubric", "role", "attempt_id")},
           "state": "missing", "submission": submission, "result": pin, "errors": [], "warnings": []}
    if slot["status"] == "missing":
        row["errors"] = ["rating slot was not registered"]
        return row
    if submission is None:
        row["errors"] = ["registered rating has no submitted result"]
        return row
    row["errors"] = [f"submission.{name} conflicts with the registered slot"
                     for name, expected in _identity(slot).items()
                     if canonical(submission[name]) != canonical(expected)]
    if row["errors"]:
        row["state"] = "rejected"
        return row
    instrument = slot["binding"]["instrument"]
    if code_mismatches or instrument["version"] not in ("3.0", "4.0") or slot["model"] is None:
        row["state"] = "unsupported"
        if code_mismatches:
            row["errors"].append("captured validator source differs; fresh registration with predecessor is required")
        if instrument["version"] not in ("3.0", "4.0"):
            row["errors"].append("historical semantic instrument cannot accept new ratings")
        if slot["model"] is None:
            row["errors"].append("rating model was not declared at registration")
        return row
    record = next(record for record in panel["records"] if record["record_id"] == slot["record_id"])
    assets = {asset["path"]: asset for asset in instrument["resources"].values() if asset is not None}

    def resource_reader(name):
        panels._need(name in assets, f"semantic resource is outside the captured instrument: {name}")
        return capture.get(assets[name])

    from data_sheets_schema.evaluation.validate import validate_evaluation
    from data_sheets_schema.semantic_scope import validate_scope
    from data_sheets_schema.semantic_evidence import EvidenceValidationError
    from jsonschema import SchemaError
    from referencing.exceptions import Unresolvable

    try:
        result = saved._read(capture.get(pin, limit=MAX_RESULT_BYTES), "submitted rating", limit=MAX_RESULT_BYTES)
        panels._need(type(result) is dict, "submitted rating must be a JSON object")
        row["errors"].extend(_payload_identity(result, slot, record, instrument))
        if row["errors"]:
            row["state"] = "rejected"
            return row
        schema = saved._read(resource_reader(instrument["resources"]["schema"]["path"]), "captured semantic schema")
        valid, problems = validate_evaluation(result, schema, resource_reader=resource_reader)
        if not valid:
            row["errors"].extend(problems)
        else:
            document = unwrap_document(saved._read(capture.get(record["input"]), "captured D4D", yaml_allowed=True))
            source = record["context"]["source"]
            original_context = (None if source is None else
                                saved._read(capture.get(source), "captured original context", yaml_allowed=True))
            panels._need(normalize_context(original_context) == record["context"]["normalized"],
                         "original and normalized captured context differ")
            evidence = validate_scope(result, document=document, input_sha256=record["input"]["sha256"],
                                      expected_context=original_context, resource_reader=resource_reader)
            row["warnings"] = [asdict(finding) for finding in evidence.warnings]
    except EvidenceValidationError as exc:
        row["errors"].extend(f"{finding.code}: {finding.message}" for finding in exc.report.errors)
        row["warnings"] = [asdict(finding) for finding in exc.report.warnings]
    except (ValueError, TypeError, KeyError, IndexError, SchemaError, Unresolvable) as exc:
        row["errors"].append(f"semantic acceptance refused: {exc}")
    row["state"] = "rejected" if row["errors"] else "accepted"
    return row


def _results(capture, panel_raw, submissions_raw, read_result):
    panel = panels._recheck(capture, panel_raw)
    selected = _submissions(submissions_raw, panel_raw, panel)
    validator, code_mismatches = _code_authority(panel)
    captured_files, pins = {}, {}
    # Capture all declared bytes before assessment, including misbound results.
    for key, submission in selected.items():
        reference = submission["result"]
        name = reference["path"]
        if name not in captured_files:
            captured_files[name] = capture.add(read_result(name))
        pin = captured_files[name]
        panels._need(pin["sha256"] == reference["sha256"], "submitted result SHA256 differs from its bytes")
        panels._need(pin["bytes"] <= MAX_RESULT_BYTES, "submitted rating exceeds byte bound")
        pins[key] = pin
    rows = [_assessment(capture, panel, slot, selected.get(_key(slot)), pins.get(_key(slot)), code_mismatches)
            for slot in panel["slots"]]
    counts = Counter(row["state"] for row in rows)
    result = {"format": FORMAT, "panel": capture.add(panel_raw), "submissions": capture.add(submissions_raw),
              "captured_files": captured_files, "rows": rows,
              "counts": {"selected": len(rows), **{state: counts[state] for state in ("accepted", "rejected", "missing", "unsupported")}},
              "validator_authority": validator, "validator_source_mismatches": code_mismatches,
              "acceptor_authority": _source_pin("src/data_sheets_schema/cross_family_panel_results.py"),
              "readiness": {name: panel[name] for name in ("missing_cells", "missing_slots", "pending_decisions", "decisions",
                                                          "duplicate_content_clusters")},
              "execution_authorized": False, "scientific_eligibility": False,
              "limitations": list(LIMITATIONS)}
    raw = canonical(result)
    panels._need(len(raw) + 1 <= MAX_RESULTS_BYTES, "panel results output exceeds manifest byte bound")
    return saved._read(raw, "reconstructed panel results", limit=MAX_RESULTS_BYTES)


def accept_panel_results(panel: Path, submissions_file: Path, output: Path, *, root: Path) -> dict:
    """Accept one explicitly declared set of saved ratings into a new package."""
    try:
        capture = saved.Capture(panel)
        inputs = saved.Capture(root)
        panel_raw = saved._file(capture.root / "panel.json", panels.MAX_PANEL_BYTES)
        submissions_raw = saved._file(Path(submissions_file), MAX_RESULTS_BYTES)

        def read_result(name):
            path = inputs.root
            for part in PurePosixPath(name).parts:
                path = path / part
                panels._need(not path.is_symlink(), "submitted result paths cannot traverse symlinks")
            return saved._file(path, MAX_RESULT_BYTES)

        result = _results(capture, panel_raw, submissions_raw, read_result)
        saved._write_new(output, capture, "results.json", result, protected=(inputs.root, submissions_file))
        return result
    except saved.ResultError as exc:
        raise PanelResultError(str(exc)) from exc


def recheck_panel_results(directory: Path) -> dict:
    """Rebuild every acceptance decision from captured bytes without input paths."""
    try:
        capture = saved.Capture(directory)
        raw = saved._file(capture.root / "results.json", MAX_RESULTS_BYTES)
        value = saved._read(raw, "panel results", limit=MAX_RESULTS_BYTES)
        panels._need(type(value) is dict and value.get("format") == FORMAT, "unsupported panel results format")
        files = value.get("captured_files")
        panels._need(type(files) is dict, "panel results require captured_files")

        def read_result(name):
            panels._need(name in files, "submitted result capture is missing")
            return capture.get(files[name], limit=MAX_RESULT_BYTES)

        result = _results(capture, capture.get(value["panel"], limit=panels.MAX_PANEL_BYTES),
                          capture.get(value["submissions"], limit=MAX_RESULTS_BYTES), read_result)
        panels._need(canonical(value) == canonical(result), "panel results differ from captured reconstruction")
        return result
    except saved.ResultError as exc:
        raise PanelResultError(str(exc)) from exc
