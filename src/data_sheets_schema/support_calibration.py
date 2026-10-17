"""Offline, declared calibration controls for registered nested-support runs.

This module never dispatches requests or authenticates human review. It binds a
closed label set to captured instrument inputs and reconstructs execution before
counting any verdict. Synthetic evidence measures software behavior only.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from data_sheets_schema import nested_support_execution as execution
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema.support_judge import VERDICTS
from data_sheets_schema.support_plan import canonical, sha256

FORMAT = "support_calibration_v1"
CONTROLS_FORMAT = "support_calibration_controls_v1"
MAX_CONTROLS_BYTES = 4_000_000
MAX_CALIBRATION_BYTES = saved.MAX_MANIFEST_BYTES
KINDS = ("relationship_edge", "attribute_value")
DISPATCH_STATUSES = ("accepted", "failed", "spent_unknown", "not_started", "missing")
LIMITATIONS = [
    "Finding and review references are caller declarations, not authenticated evidence or approval.",
    "Captured execution bytes do not authenticate a provider call or a human label.",
    "Synthetic controls and local-fixture executions measure software behavior only.",
    "Pending labels are unscored; missing, failed and unstarted executions are not negative findings.",
    "Conditional observed rates describe resolved controls only, not full recall or false-positive rates.",
    "Defect classes are caller strata; binary detection is distinct from exact verdict agreement.",
    "Scientific review, private-control handling and paid-run authorization remain separate obligations.",
    "Numeric results do not authorize calibration acceptance, canaries or a cohort campaign.",
]


class CalibrationError(ValueError):
    """Calibration evidence does not satisfy the captured control contract."""


def _need(condition, message):
    if not condition:
        raise CalibrationError(message)


def _keys(value, keys, label):
    _need(type(value) is dict and set(value) == set(keys), f"{label} has missing or unknown fields")


def _text(value, label, maximum=1024):
    _need(type(value) is str and bool(value.strip()) and len(value) <= maximum,
          f"{label} must be bounded nonblank text")


def _digest(value, label):
    _need(type(value) is str and bool(saved._SHA.fullmatch(value)), f"{label} must be a SHA256")


def _reference(value, label):
    _keys(value, {"reference", "sha256"}, label)
    _text(value["reference"], f"{label}.reference", 4096)
    _digest(value["sha256"], f"{label}.sha256")


def _manifest(capture, registration_raw, controls_raw):
    registration = execution._load(capture, registration_raw)
    _need(registration["format"] == execution.FORMAT, "calibration requires nested-support registration")
    descriptor = saved._load_descriptor(capture, capture.get(registration["descriptor"]))
    controls = saved._read(controls_raw, "calibration controls", limit=MAX_CONTROLS_BYTES)
    _keys(controls, {"format", "calibration_id", "registration_sha256", "controls"}, "controls")
    _need(controls["format"] == CONTROLS_FORMAT, "explicit calibration controls format required")
    _text(controls["calibration_id"], "calibration_id", 128)
    _digest(controls["registration_sha256"], "registration_sha256")
    _need(controls["registration_sha256"] == sha256(registration_raw), "controls reference another registration")
    selections = descriptor["selections"]
    _need(type(controls["controls"]) is list and len(controls["controls"]) == len(selections)
          and bool(selections), "exactly one control per registered selection is required")
    by_target = {selection["target_id"]: selection for selection in selections}
    resolved, identifiers = {}, set()
    for control in controls["controls"]:
        _keys(control, {"control_id", "target_id", "attempt_id", "kind", "pointer", "binding_sha256",
                        "review_status", "expected_verdict", "defect_class", "finding", "review"}, "control")
        for key in ("control_id", "target_id", "attempt_id"):
            _text(control[key], key)
        _need(control["control_id"] not in identifiers, "duplicate control identifier")
        identifiers.add(control["control_id"])
        target = control["target_id"]
        _need(target in by_target and target not in resolved, "duplicate or unregistered target control")
        selection = by_target[target]
        binding = selection["binding"]
        _need(control["attempt_id"] == selection["attempt_id"], "control selects another attempt")
        _need(control["kind"] in KINDS and control["kind"] == binding["kind"], "control facet differs")
        _need(control["pointer"] == binding["pointer"], "control pointer differs")
        _digest(control["binding_sha256"], "binding_sha256")
        _need(control["binding_sha256"] == sha256(canonical(binding)), "control binding differs")
        status = control["review_status"]
        _need(status in ("reviewed", "pending", "synthetic"), "invalid control review status")
        if status == "pending":
            _need(control["expected_verdict"] is None or control["expected_verdict"] in VERDICTS,
                  "invalid pending expected verdict")
            if control["defect_class"] is not None:
                _text(control["defect_class"], "defect_class", 128)
        else:
            _need(control["expected_verdict"] in VERDICTS, "reviewed/synthetic control requires expected verdict")
            _text(control["defect_class"], "defect_class", 128)
        _reference(control["finding"], "finding")
        if status == "reviewed":
            _reference(control["review"], "review")
        else:
            _need(control["review"] is None, "pending/synthetic control cannot claim completed review")
        resolved[target] = {**control, "binding": binding}
    result = {"format": FORMAT, "kind": "control_manifest", "calibration_id": controls["calibration_id"],
            "registration": capture.add(registration_raw), "controls": capture.add(controls_raw),
            "resolved_controls": [resolved[s["target_id"]] for s in selections],
            "purpose": registration["declaration"]["purpose"],
            "original_readiness": registration["original_readiness"],
            "scientific_eligibility": False, "limitations": list(LIMITATIONS)}
    if "context_policy" in descriptor:
        result["context_policy"] = descriptor["context_policy"]
    return result


def _load_manifest(capture, raw):
    value = saved._read(raw, "calibration manifest", limit=MAX_CALIBRATION_BYTES)
    context_keys = {"context_policy"} if type(value) is dict and "context_policy" in value else set()
    _keys(value, {"format", "kind", "calibration_id", "registration", "controls", "resolved_controls",
                  "purpose", "original_readiness", "scientific_eligibility", "limitations"} | context_keys, "manifest")
    expected = _manifest(capture, capture.get(value["registration"], limit=execution.MAX_REGISTRATION_BYTES),
                         capture.get(value["controls"], limit=MAX_CONTROLS_BYTES))
    _need(raw == canonical(expected) + b"\n", "calibration manifest differs from reconstructed inputs")
    return expected


def prepare(registration: Path, controls_file: Path, output: Path) -> dict:
    """Capture a complete declared control set into a new portable directory."""
    capture = saved.Capture(registration)
    value = _manifest(capture, capture.entry("registration.json", limit=execution.MAX_REGISTRATION_BYTES),
                      saved._file(Path(controls_file), MAX_CONTROLS_BYTES))
    _write_new(output, capture, value, protected=(controls_file,))
    return value


def _write_new(output, capture, document, *, protected=()):
    _need(len(canonical(document)) + 1 <= MAX_CALIBRATION_BYTES,
          "calibration output exceeds manifest byte bound")
    saved._write_new(output, capture, "calibration.json", document, protected=protected)


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _metrics(rows, unresolved):
    observed = [row for row in rows if row["scored"]]
    positives = [row for row in rows if row["expected_verdict"] != "supported"]
    negatives = [row for row in rows if row["expected_verdict"] == "supported"]
    observed_positive = [row for row in observed if row["expected_verdict"] != "supported"]
    observed_negative = [row for row in observed if row["expected_verdict"] == "supported"]
    detected = sum(row["defect_detected"] for row in observed_positive)
    false_positive = sum(row["false_positive"] for row in observed_negative)
    agreed = sum(row["verdict_agreement"] for row in observed)
    conditional = {"recall": _rate(detected, len(observed_positive)),
                   "false_positive_rate": _rate(false_positive, len(observed_negative)),
                   "verdict_agreement_rate": _rate(agreed, len(observed))}
    return {"controls": len(rows), "unresolved_controls": len(rows) - len(observed),
            "observed_controls": len(observed), "positive_controls": len(positives),
            "negative_controls": len(negatives), "observed_positive_controls": len(observed_positive),
            "observed_negative_controls": len(observed_negative), "detected_positive_controls": detected,
            "false_positive_controls": false_positive, "agreed_controls": agreed,
            **{key: None if unresolved else value for key, value in conditional.items()},
            "conditional_observed_rates": conditional}


def _result(capture, manifest, ledger):
    execution_report = None
    if ledger is not None:
        execution_report = execution.recheck_captured(capture, ledger)
        _need(execution_report["registration"] == manifest["registration"],
              "execution registration differs from calibration registration")
    executed = {(row["target_id"], row["attempt_id"]): row
                for row in execution_report["rows"]} if execution_report else {}
    rows = []
    for control in manifest["resolved_controls"]:
        attempt = executed.get((control["target_id"], control["attempt_id"]))
        state = attempt["status"] if attempt else "not_started" if execution_report else "missing"
        saved_result = attempt.get("saved_result") if attempt else None
        assessment = saved_result["assessment"] if saved_result else None
        accepted = state == "accepted" and assessment is not None and assessment["status"] == "accepted"
        observed = assessment["verdict"] if accepted else None
        pending = control["review_status"] == "pending"
        scope = None if pending else "synthetic" if (
            control["review_status"] == "synthetic" or manifest["purpose"] == "local_fixture") else "reviewed"
        scored = accepted and not pending
        expected = control["expected_verdict"]
        row = {key: control[key] for key in ("control_id", "target_id", "attempt_id", "kind", "pointer",
                                             "review_status", "expected_verdict", "defect_class", "finding", "review")}
        row.update(dispatch_status=state, assessment_status=assessment["status"] if assessment else None,
                   observed_verdict=observed, raw_verdict=assessment["verdict"] if assessment else None,
                   problems=attempt.get("problems", []) if attempt else ["execution_not_supplied"] if ledger is None else [],
                   scored=scored, metric_scope=scope,
                   verdict_agreement=observed == expected if scored else None,
                   defect_detected=observed != "supported" if scored and expected != "supported" else None,
                   false_positive=observed != "supported" if scored and expected == "supported" else None)
        if "policy" in control["binding"]:
            row.update(policy=control["binding"]["policy"],
                       representation=control["binding"]["representation"])
        if "context_policy" in control["binding"]:
            row["context_policy"] = control["binding"]["context_policy"]
        rows.append(row)
    unresolved = sum(not row["scored"] for row in rows)
    groups, verdict_groups = [], []
    for scope in ("reviewed", "synthetic"):
        for kind in KINDS:
            selected = [row for row in rows if row["metric_scope"] == scope and row["kind"] == kind]
            if not selected:
                continue
            for defect_class in [None, *sorted({row["defect_class"] for row in selected})]:
                subset = selected if defect_class is None else [r for r in selected if r["defect_class"] == defect_class]
                groups.append({"scope": scope, "kind": kind, "defect_class": defect_class,
                               **_metrics(subset, unresolved)})
            for verdict in VERDICTS:
                subset = [row for row in selected if row["expected_verdict"] == verdict]
                if subset:
                    verdict_groups.append({"scope": scope, "kind": kind, "expected_verdict": verdict,
                                           **_metrics(subset, unresolved)})
    states = Counter(row["dispatch_status"] for row in rows)
    review = Counter(row["review_status"] for row in rows)
    result = {"format": FORMAT, "kind": "calibration_result", "calibration_id": manifest["calibration_id"],
            "registration": manifest["registration"], "purpose": manifest["purpose"],
            "evidence_scope": "declared_reviewed_labels" if any(r["metric_scope"] == "reviewed" for r in rows)
                              else "software_only",
            "totals": {"controls": len(rows), **{key: review[key] for key in ("reviewed", "synthetic", "pending")},
                       "unresolved_controls": unresolved, "dispatch_status": {key: states[key] for key in DISPATCH_STATUSES}},
            "rows": rows, "groups": groups, "verdict_groups": verdict_groups,
            "execution_accounting": execution_report,
            "original_readiness": manifest["original_readiness"], "scientific_eligibility": False,
            "limitations": list(LIMITATIONS)}
    if "context_policy" in manifest:
        result["context_policy"] = manifest["context_policy"]
    if any("policy" in row for row in rows):
        # These are subsets of the existing relationship controls, not new
        # observations. Absence of this issue does not establish schema validity.
        edges = [row for row in rows if row["kind"] == "relationship_edge"]
        subsets = {"schema_invalid_inline_class_string": [r for r in edges if r["representation"] is not None],
                   "other_relationship_edges": [r for r in edges if r["representation"] is None]}
        result["representation_counts"] = {"basis": "selected_relationship_controls",
                                            **{name: len(subset) for name, subset in subsets.items()}}
        representation_groups = []
        for scope in ("reviewed", "synthetic"):
            for status, subset in subsets.items():
                selected = [r for r in subset if r["metric_scope"] == scope]
                if not selected:
                    continue
                for defect_class in [None, *sorted({r["defect_class"] for r in selected})]:
                    members = selected if defect_class is None else [
                        r for r in selected if r["defect_class"] == defect_class]
                    representation_groups.append({"scope": scope, "kind": "relationship_edge",
                        "representation_status": status, "defect_class": defect_class,
                        **_metrics(members, unresolved)})
        result["representation_groups"] = representation_groups
    return result


def report(calibrationdir: Path, run_path: Path | None = None, output: Path | None = None) -> dict:
    """Reconstruct verdicts and optionally capture a new portable report.

    Without execution evidence every selected control is explicitly missing.
    Existing output directories and all input evidence are preserved.
    """
    capture = saved.Capture(calibrationdir)
    manifest_raw = capture.entry("calibration.json", limit=MAX_CALIBRATION_BYTES)
    manifest = _load_manifest(capture, manifest_raw)
    ledger = None
    if run_path is not None:
        run_capture, ledger = execution.capture_run(run_path)
        reconstructed = execution.recheck_captured(run_capture, ledger)
        cached = Path(run_path) / "report.json"
        if cached.exists() or cached.is_symlink():
            _need(saved._file(cached, saved.MAX_MANIFEST_BYTES) == canonical(reconstructed),
                  "saved execution report differs from reconstructed evidence")
        for raw in run_capture.blobs.values():
            capture.add(raw)
    result = _result(capture, manifest, ledger)
    if output is not None:
        document = {"format": FORMAT, "kind": "calibration_report", "calibration": capture.add(manifest_raw),
                    "execution_ledger": ledger, "result": result}
        protected = (run_path,) if run_path is not None else ()
        _write_new(output, capture, document, protected=protected)
    return result


def recheck(calibrationdir: Path) -> dict:
    """Reconstruct captured controls or a captured report without original paths."""
    capture = saved.Capture(calibrationdir)
    raw = capture.entry("calibration.json", limit=MAX_CALIBRATION_BYTES)
    value = saved._read(raw, "calibration evidence", limit=MAX_CALIBRATION_BYTES)
    _need(type(value) is dict, "calibration evidence must be a mapping")
    if value.get("kind") == "control_manifest":
        return _load_manifest(capture, raw)
    _keys(value, {"format", "kind", "calibration", "execution_ledger", "result"}, "calibration report")
    _need(value["format"] == FORMAT and value["kind"] == "calibration_report", "unknown calibration format")
    manifest = _load_manifest(capture, capture.get(value["calibration"], limit=MAX_CALIBRATION_BYTES))
    result = _result(capture, manifest, value["execution_ledger"])
    expected = {"format": FORMAT, "kind": "calibration_report", "calibration": value["calibration"],
                "execution_ledger": value["execution_ledger"], "result": result}
    _need(raw == canonical(expected) + b"\n", "saved calibration report differs from reconstructed evidence")
    return result
