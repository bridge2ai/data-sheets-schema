"""Read-only evidence tables for the registered score-gap rule (issue 6385).

Published scores are not execution receipts. Explicit evidence roots supply
saved plans, receipts and repeat export manifests; absent proof remains missing.
This reader never opens a refused candidate, raw response or session transcript.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

from data_sheets_schema._score_selection_math import decide, pooled_variation, summarize


FAMILIES = ("rubric10", "rubric20")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000_000:
        raise ValueError(f"not a bounded regular evidence file: {path}")
    return path.read_bytes()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(path):
    raw = _read(path)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"evidence must be an object: {path}")
    return value, _sha(raw)


def _require(value, message):
    if not value:
        raise ValueError(message)


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _digest(value):
    _require(isinstance(value, str) and _HEX.fullmatch(value), "missing measured-input digest")
    return value


def load_evidence_index(evidence_roots=()):
    """Index only named metadata files, never traverse scorer output trees.

    Roots may be run directories or their immediate parent. Repeat exports are
    discovered only at root/export-manifests/*/manifest.json, or when an export
    directory itself is explicitly supplied. No conventional machine path is
    searched when callers omit this input.
    """
    runs, manifests, issues = {}, {}, []
    for supplied in evidence_roots:
        root = Path(supplied).absolute()
        _require(root.is_dir() and not root.is_symlink(), f"invalid evidence root: {root}")
        children = [p for p in sorted(root.iterdir()) if p.is_dir() and not p.is_symlink()]
        for directory in [root, *children]:
            plan_path, receipt_path = directory / "plan.json", directory / "receipt.json"
            if not (plan_path.exists() and receipt_path.exists()):
                continue
            key = str(plan_path)
            if key in runs:
                continue
            try:
                plan, plan_sha = _json(plan_path)
                receipt, receipt_sha = _json(receipt_path)
                runs[key] = {"plan": plan, "receipt": receipt, "plan_path": key,
                             "plan_sha256": plan_sha, "receipt_path": str(receipt_path),
                             "receipt_sha256": receipt_sha}
            except (OSError, ValueError) as exc:
                issues.append(str(exc))
        export_roots = [root / "export-manifests"]
        if root.name == "export-manifests":
            export_roots.append(root)
        paths = [root / "manifest.json"]
        for directory in export_roots:
            if directory.is_dir() and not directory.is_symlink():
                paths.extend(p / "manifest.json" for p in sorted(directory.iterdir())
                             if p.is_dir() and not p.is_symlink())
        for path in paths:
            if not path.exists() or str(path) in manifests:
                continue
            try:
                value, digest = _json(path)
                manifests[str(path)] = {"value": value, "path": str(path), "sha256": digest}
            except (OSError, ValueError) as exc:
                issues.append(str(exc))
    return {"runs": runs, "manifests": list(manifests.values()), "issues": issues}


def _missing(number, reason):
    return {"scoring_number": number, "status": "not measured", "points": None,
            "maximum": None, "percentage": None, "attempt": None,
            "measurement_identity": None, "reason": reason}


def _identity_matches(plan, project, method, label, family, instrument):
    identity = plan.get("identity", {})
    return (isinstance(identity, dict) and plan.get("instrument") == instrument
            and identity.get("instrument_id") == instrument
            and all(identity.get(key) == value for key, value in
                    (("project", project), ("method", method), ("label", label),
                     ("rubric", family + "-semantic"))))


def _accepted_metadata(entry):
    plan, receipt = entry["plan"], entry["receipt"]
    _require(receipt.get("status") == "VALIDATED_AND_PUBLISHED", "scoring receipt is not accepted")
    _require(receipt.get("plan_sha256") == _sha(json.dumps(plan, sort_keys=True).encode()),
             "receipt does not bind its saved plan")
    _require(type(receipt.get("codex_exit")) is int and receipt["codex_exit"] == 0
             and type(receipt.get("validator_exit")) is int and receipt["validator_exit"] == 0
             and receipt.get("auth_copy_absent") is True, "acceptance or cleanup is unproven")
    _require(receipt.get("output") == plan.get("output"), "receipt publication path differs")
    _require(Path(plan.get("run_directory", "")) == Path(entry["plan_path"]).parent,
             "plan names another run directory")
    _require(receipt.get("output_sha256") == receipt.get("validator_input_sha256"),
             "published and validated hashes differ")
    return _digest(receipt.get("output_sha256"))


def _measurement(plan, record_sha):
    metadata = _mapping(_mapping(plan.get("deterministic_fields")).get("metadata"))
    inputs = _mapping(plan.get("inputs"))
    names = {"record_sha256": ("input_sha256", "record.yaml"),
             "definition_sha256": ("instrument_sha256", "agent-definition.md"),
             "evidence_authority_sha256": ("evidence_authority_sha256", "evidence-authority.json"),
             "scope_sha256": ("scope_context_sha256", "scope-context.json"),
             "rubric_sha256": ("rubric_sha256", "rubric.txt")}
    result = {"instrument_id": plan["instrument"]}
    for name, (meta_name, input_name) in names.items():
        digest = _digest(metadata.get(meta_name))
        _require(digest == _mapping(inputs.get(input_name)).get("sha256"), "plan input and metadata differ")
        result[name] = digest
    _require(result["record_sha256"] == record_sha, "scoring names changed record bytes")
    result["schema_sha256"] = _digest(_mapping(inputs.get("output-schema.json")).get("sha256"))
    result["context_sha256"] = _digest(metadata.get("context_sha256"))
    result["prompt_sha256"] = _digest(plan.get("prompt_sha256"))
    result["runner_sha256"] = _digest(plan.get("runner_sha256"))
    _require(result["prompt_sha256"] == _sha(plan.get("prompt", "").encode()), "plan prompt digest differs")
    provenance = _mapping(plan.get("definition_provenance"))
    _require(provenance.get("composed_sha256") == result["definition_sha256"],
             "composed definition is not pinned")
    return result


def _published_deterministic_fields(value, planned):
    """Match input invariants while retaining publication-only annotations.

    The captured v6 output schemas leave metadata open to additional fields.
    Evaluators use that space for timestamp and assessment notes; those notes
    are not part of the six planned input hashes. Every planned metadata key
    remains mandatory and exact. Scope, context and any other planned block
    still require full equality, including their closed internal structure.
    """
    _require(isinstance(planned, dict), "planned deterministic fields are not an object")
    for key, expected_value in planned.items():
        if key == "metadata":
            actual = value.get(key)
            _require(isinstance(actual, dict) and isinstance(expected_value, dict),
                     "published measured-input metadata is not an object")
            for name, expected in expected_value.items():
                _require(name in actual and actual[name] == expected,
                         "published measured-input metadata differs: " + name)
        else:
            _require(value.get(key) == expected_value,
                     "published measured-input block differs: " + key)


def _score_cell(index, number, path, *, project, method, label, family, instrument, record_sha):
    matches = [entry for entry in index["runs"].values()
               if _identity_matches(entry["plan"], project, method, label, family, instrument)]
    referenced = {item["value"].get("actual_plan") for item in index["manifests"]}
    manifest = None
    if number == 1:
        choices = [entry for entry in matches if entry["plan_path"] not in referenced
                   and entry["receipt"].get("status") == "VALIDATED_AND_PUBLISHED"]
    else:
        exports = [item for item in index["manifests"]
                   if item["value"].get("scoring_replicate") == number
                   and _mapping(item["value"].get("identity")).get("project") == project
                   and _mapping(item["value"].get("identity")).get("method") == method
                   and _mapping(item["value"].get("identity")).get("label") == label
                   and _mapping(item["value"].get("identity")).get("rubric") == family + "-semantic"
                   and _mapping(item["value"].get("identity")).get("instrument_id") == instrument]
        if len(exports) != 1:
            return _missing(number, "missing or ambiguous accepted repeat export")
        manifest = exports[0]
        choices = [entry for entry in matches if entry["plan_path"] == manifest["value"].get("actual_plan")]
    if len(choices) != 1:
        reasons = sorted({str(entry["receipt"].get("failure", "scoring receipt is not accepted"))
                          for entry in matches if entry["receipt"].get("status") == "REFUSED"})
        return _missing(number, "; ".join(reasons) or "missing or ambiguous accepted scoring receipt")
    entry = choices[0]
    try:
        expected = _accepted_metadata(entry)
        plan, receipt = entry["plan"], entry["receipt"]
        measured = _measurement(plan, record_sha)
        attempt, refused = 1, None
        if manifest:
            value = manifest["value"]
            _require(value.get("status") == "EXPORTED_VALIDATED_REPEAT"
                     and value.get("copy_validator_exit") == 0, "repeat export is not accepted")
            _require(value.get("identity") == plan["identity"], "repeat identity differs")
            for kind in ("plan", "receipt"):
                _require(value.get("actual_" + kind) == entry[kind + "_path"]
                         and value.get("actual_" + kind + "_sha256") == entry[kind + "_sha256"],
                         "repeat metadata binding differs")
            _require(value.get("destination_sha256") == value.get("source_output_sha256") == expected,
                     "repeat publication hash differs")
            _require(Path(value.get("destination", "")).name == path.name
                     and tuple(Path(value.get("destination", "")).parts[-5:]) == tuple(path.parts[-5:]),
                     "repeat publication identity path differs")
            attempt = value.get("attempt", 1)
            _require(type(attempt) is int and attempt in (1, 2), "invalid published attempt")
            if attempt == 2:
                refused = _mapping(value.get("refused_attempt_receipt"))
                candidates = [item for item in matches
                              if item["receipt_path"] == refused.get("path")]
                _require(len(candidates) == 1, "replacement lacks retained refused receipt")
                original = candidates[0]
                _require(original["receipt_sha256"] == refused.get("sha256")
                         and original["receipt"].get("status") == "REFUSED",
                         "replacement refusal binding differs")
                refused_plan = _mapping(value.get("refused_attempt_plan"))
                _require(refused_plan.get("path") == original["plan_path"]
                         and refused_plan.get("sha256") == original["plan_sha256"],
                         "replacement refused-plan binding differs")
                _require(original["receipt"].get("plan_sha256")
                         == _sha(json.dumps(original["plan"], sort_keys=True).encode()),
                         "refused receipt does not bind its saved plan")
                _require(_measurement(original["plan"], record_sha) == measured,
                         "replacement differs from refused measured inputs")
                refused = {**refused, "reason": original["receipt"].get("failure")}
        # No candidate/raw-response/session path is opened: only the declared
        # publication, after its accepted metadata and measured identity pass.
        raw = _read(path)
        _require(_sha(raw) == expected, "published bytes do not match accepted receipt")
        value = json.loads(raw)
        _require(isinstance(value, dict), "published scoring is not an object")
        for key in ("project", "method", "label", "rubric", "version", "d4d_file"):
            _require(value.get(key) == plan["identity"].get(key), "published scoring identity differs")
        _require(value.get("scorer_instrument") == {"id": instrument,
                 "prompt_sha256": measured["prompt_sha256"], "runner_sha256": measured["runner_sha256"]},
                 "published instrument differs")
        _published_deterministic_fields(value, plan["deterministic_fields"])
        score = value.get("overall_score", {})
        points, maximum = score.get("total_points"), score.get("adjusted_max_points")
        _require(all(type(item) in (int, float) and math.isfinite(item) for item in (points, maximum))
                 and 0 <= points <= maximum and maximum > 0, "score is not a finite points/maximum pair")
        return {"scoring_number": number, "status": "measured", "points": points,
                "maximum": maximum, "percentage": 100 * points / maximum, "attempt": attempt,
                "measurement_identity": measured, "reason": None, "path": str(path),
                "sha256": expected, "receipt": entry["receipt_path"],
                "receipt_sha256": entry["receipt_sha256"], "refused_attempt": refused,
                "manifest": manifest["path"] if manifest else None}
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return _missing(number, str(exc))


def _other_evidence(record, project, label, method, root, record_sha):
    import yaml
    provenance_path = record.parent.parent.parent / (method + "_core") / label / (project + "_provenance.yaml")
    provenance = {}
    if provenance_path.is_file():
        try:
            value = yaml.safe_load(_read(provenance_path))
        except (OSError, ValueError, yaml.YAMLError):
            value = None
        if isinstance(value, dict):
            provenance = value
    receipts = provenance.get("receipts")
    coverage = (receipts.get("slots") if isinstance(receipts, dict) and receipts.get("checked") is True else None)
    review = provenance.get("review")
    from data_sheets_schema.review_pack import review_evidence_why
    review_counts = review.get("by_kind") if review_evidence_why(review) is None else None
    presence = []
    presence_root = root / "data/evaluation"
    if presence_root.is_dir():
        for path in sorted(presence_root.glob("*/scores.json")):
            try:
                values = json.loads(_read(path))
            except (OSError, ValueError):
                continue
            if not isinstance(values, list):
                continue
            for value in values:
                if (isinstance(value, dict) and value.get("project") == project
                        and value.get("method") == method and value.get("label") == label
                        and _mapping(value.get("instrument")).get("input_sha256") == record_sha):
                    presence.append({"path": str(path), "instrument": value.get("instrument"),
                                     **{family: value.get(family) for family in FAMILIES}})
    return coverage, review_counts, presence or None


def build_evidence_table(project, config, instrument_id, *, candidates, corpus_root,
                         evidence_roots=(), evidence_index=None):
    """One evidence row per candidate; missing measurements are explicit cells.

    Candidate dictionaries carry the existing selector's freshly computed
    validity and slot count. This function neither validates nor marks records.
    """
    root = Path(corpus_root).absolute()
    _require(isinstance(instrument_id, str) and instrument_id
             and Path(instrument_id).name == instrument_id and instrument_id not in (".", ".."),
             "instrument id must be one path component")
    index = evidence_index if evidence_index is not None else load_evidence_index(evidence_roots)
    rows = []
    for candidate in sorted(candidates, key=lambda item: item["label"]):
        label = candidate["label"]
        record = Path(candidate["record"]) if candidate.get("record") else None
        method = candidate.get("method") or (record.parent.parent.name if record else None)
        import yaml
        record_sha, slots, record_issue = None, None, None
        if record and record.is_file():
            try:
                raw = _read(record)
                record_sha = _sha(raw)
                loaded = yaml.safe_load(raw)
                slots = len(loaded) if isinstance(loaded, dict) else None
            except (OSError, ValueError, yaml.YAMLError) as exc:
                record_issue = str(exc)
        row = {"project": project, "config": config, "instrument_id": instrument_id,
               "label": label, "validity": candidate["validity"], "slots": slots,
               "record_sha256": record_sha, "rubrics": {},
               "review_adverse": candidate.get("review_adverse"),
               "review_not_evidence": candidate.get("review_not_evidence"),
               "receipt_coverage": None, "presence_evaluation": None, "review_verdict_counts": None}
        if record_sha:
            coverage, reviews, presence = _other_evidence(record, project, label, method, root, record_sha)
            row.update(receipt_coverage=coverage, review_verdict_counts=reviews, presence_evaluation=presence)
        for family in FAMILIES:
            cells = []
            for number in (1, 2, 3):
                directory = (root / "data/evaluation_llm" / (family + "_semantic") / "label_aware" / instrument_id
                             if number == 1 else root / "data/evaluation_repeats" / instrument_id /
                             ("scoring_rep" + str(number)) / (family + "_semantic"))
                path = directory / (project + "_" + label + "_evaluation.json")
                cells.append(_score_cell(index, number, path, project=project, method=method, label=label,
                                         family=family, instrument=instrument_id, record_sha=record_sha)
                             if record_sha else _missing(number, "record bytes are not available"))
            row["rubrics"][family] = {"scorings": cells}
        summary = summarize(row)
        for family in FAMILIES:
            row["rubrics"][family].update(summary["rubrics"][family])
        row["paired"] = summary["paired"]
        row["paired_numbers"] = summary["paired_numbers"]
        row["problems"] = summary["problems"]
        row["evidence_issues"] = index["issues"] + ([record_issue] if record_issue else [])
        rows.append(row)
    return rows
