"""Finite outgoing model projections for #4954, with visible loss diagnostics.

These fifteen fields are not additions to reverse ROUTES or supplied-evidence
identity. A retained narrative projection is not structural source preservation.
"""
from __future__ import annotations

from data_sheets_schema.fairscape_route_assertions import assertion, same_json
from data_sheets_schema.rocrate_parent_admission import snapshot


SCOPE = "fairscape-forward-types-v1"
# source, wire alias, source cardinality, list-valued wire, exact text members
FIELDS = (
    ('known_limitations', 'rai:dataLimitations', 'list', False, ('limitation_description', 'description', 'name')),
    ('known_biases', 'rai:dataBiases', 'list', False, ('bias_description', 'description', 'name')),
    ('intended_uses', 'rai:dataUseCases', 'list', False, ('usage_notes', 'description', 'name')),
    ('updates', 'rai:dataReleaseMaintenancePlan', 'object', False, ('update_details', 'description', 'name')),
    ('missing_data_documentation', 'rai:dataCollectionMissingData', 'list', False, ('missing_data_patterns', 'description', 'name')),
    ('raw_data_sources', 'rai:dataCollectionRawData', 'list', False, ('source_description',)),
    ('collection_timeframes', 'rai:dataCollectionTimeframe', 'list', True, ('timeframe_details', 'description', 'name')),
    ('preprocessing_strategies', 'rai:dataPreprocessingProtocol', 'list', True, ('preprocessing_details', 'description', 'name')),
    ('annotation_analyses', 'rai:dataAnnotationAnalysis', 'list', True, ('annotation_quality_details', 'description', 'name')),
    ('distribution_formats', 'evi:formats', 'list', True, ('format', 'media_type', 'name')),
    ('addressing_gaps', 'd4d:addressingGaps', 'list', False, ('response', 'description', 'name')),
    ('anomalies', 'd4d:dataAnomalies', 'list', False, ('anomaly_details', 'description', 'name')),
    ('content_warnings', 'd4d:contentWarning', 'list', False, ('description', 'name')),
    ('informed_consent', 'd4d:informedConsent', 'list', False, ('description', 'name')),
    ('at_risk_populations', 'd4d:atRiskPopulations', 'object', False, ('description', 'name')),
)


class ForwardProjectionWarning(UserWarning):
    """A model-valid conversion omitted or partially projected covered data."""


def initialize(state):
    state["projection_scope"] = {
        "contract": SCOPE, "sources": [field[0] for field in FIELDS],
        "compatibility_alias": "vulnerable_populations",
        "limits": "Fifteen outgoing fields only; model validity and retained text do not establish source-shape preservation or scientific coverage.",
    }
    state["projection_summary"] = {
        "status": "pending", "model_valid": None, "incomplete": None,
        "omitted": [], "partial": [], "null_not_emitted": [], "superseded": [],
    }


def _text(value, members):
    if type(value) is str:
        return value, "legacy string retained exactly; not a D4D object validation"
    if type(value) is dict and len(value) == 1:
        key = next(iter(value))
        if key in members and type(value[key]) is str:
            return value[key], "exact single-member narrative projection; raw object retained in evidence"
    return None, "unsupported value or richer object; no stringify, field selection or narrative inference"


def _unit(row, value, index):
    return {"source_index": index,
            "source_pointer": row["source_pointer"] + ("/" + str(index) if index is not None else ""),
            "raw": snapshot(value), "decision": "unplaced",
            "reason": "no supported projection", "projected_value": None,
            "projection_index": None, "retention": "not_constructed", "final_value": None}


def projections(state, data):
    """Project finite root assertions; every declined unit remains detached."""
    result = {}
    fields = list(FIELDS)
    if "vulnerable_populations" in data:
        _, target, shape, many, members = FIELDS[-1]
        fields.append(("vulnerable_populations", target, shape, many, members))
    for source, target, shape, many, members in fields:
        present = source in data
        raw = data.get(source)
        row = assertion(source, "/" + source, present, raw, target)
        row.update(projection_scope=SCOPE, source_cardinality=shape,
                   wire_cardinality="list" if many else "scalar", units=[], projection=None)
        state["assertions"].append(row)
        if not present:
            continue
        if source == "at_risk_populations" and "vulnerable_populations" in data:
            row.update(decision="superseded", reason="superseded by present vulnerable_populations, the historical winner including null or unsupported values")
            continue
        if raw is None:
            row.update(decision="null_not_emitted", retention="not_emitted",
                       reason="explicit null omitted from the wire; not a missing assertion or scientific negative")
            continue
        values = list(enumerate(raw)) if type(raw) is list else [(None, raw)]
        row["units"] = [_unit(row, value, index) for index, value in values]
        admitted = []
        if many:
            if type(raw) is list:
                for unit in row["units"]:
                    value, reason = _text(unit["raw"], members)
                    unit["reason"] = reason
                    if value is not None:
                        unit.update(decision="constructed", projected_value=value,
                                    projection_index=len(admitted))
                        admitted.append(value)
                if not raw or admitted:
                    row["projection"] = admitted
            else:
                row["reason"] = "list-valued target requires an outer list; no scalar wrapping"
                row["units"][0]["reason"] = row["reason"]
        else:
            eligible = type(raw) is str or (shape == "object" and type(raw) is dict)
            value = raw
            if shape == "list" and type(raw) is list and len(raw) == 1 and type(raw[0]) is dict:
                eligible = True
                value = raw[0]
            if eligible:
                text, reason = _text(value, members)
                row["units"][0]["reason"] = reason
                if text is not None:
                    row["projection"] = text
                    row["units"][0].update(decision="constructed", projected_value=text)
                else:
                    row["reason"] = reason
            else:
                row["reason"] = ("scalar target requires one exact narrative object in its declared source cardinality or a direct legacy string; no list selection, deduplication or concatenation")
                for unit in row["units"]:
                    unit["reason"] = row["reason"]
        if row["projection"] is not None:
            result[target] = snapshot(row["projection"])
            row.update(decision="constructed", projected_value=snapshot(row["projection"]),
                       reason="finite text projection; unsupported units remain in evidence" if any(
                           u["decision"] == "unplaced" for u in row["units"])
                       else "all admitted projected values supplied to the model; raw shape remains evidence")
        elif many and type(raw) is list:
            row["reason"] = "nonempty list has no admitted narrative units; target omitted instead of invented empty list"
    return result


def finish(state, root=None):
    """Observe actual model values, without promoting projected text to raw equality."""
    summary = state["projection_summary"]
    if root is None:
        summary.update(status="failed", model_valid=False, incomplete=None)
        for row in state["assertions"]:
            if row.get("projection_scope") == SCOPE:
                for unit in row["units"]:
                    if unit["decision"] == "constructed":
                        unit.update(retention="unknown_failed", final_value=None)
        return
    summary.update(status="complete", model_valid=True, incomplete=False)
    for row in state["assertions"]:
        if row.get("projection_scope") != SCOPE:
            continue
        target = row["target"]
        actual = root.get(target)
        row["final_value"] = snapshot(actual)
        if row["decision"] == "constructed":
            many = row["wire_cardinality"] == "list"
            admitted = [unit for unit in row["units"] if unit["decision"] == "constructed"]
            for unit in admitted:
                position = unit["projection_index"]
                observed = (actual[position] if many and type(actual) is list and position < len(actual)
                            else actual if not many else None)
                unit["final_value"] = snapshot(observed)
                unit["retention"] = ("retained" if same_json(observed, unit["projected_value"])
                                     else "not_retained")
            matches = target in root and same_json(actual, row["projection"])
            unplaced = any(unit["decision"] == "unplaced" for unit in row["units"])
            row["retention"] = ("retained" if matches and not unplaced else "partial"
                                if any(unit["retention"] == "retained" for unit in admitted)
                                else "not_retained")
            if not matches:
                row["reason"] = "actual model value did not exactly retain the complete projected value"
        entry = {key: row[key] for key in ("source", "source_pointer", "target", "reason")}
        entry["unplaced_indices"] = [u["source_index"] for u in row["units"]
                                     if u["decision"] == "unplaced"]
        if row["decision"] == "null_not_emitted":
            summary["null_not_emitted"].append(entry)
        elif row["decision"] == "superseded":
            summary["superseded"].append(entry)
            if row["presence"] == "present":
                summary["omitted"].append(entry)
        elif row["presence"] == "present":
            if row["retention"] == "partial":
                summary["partial"].append(entry)
            elif row["retention"] != "retained":
                summary["omitted"].append(entry)
    summary["incomplete"] = bool(summary["omitted"] or summary["partial"])


def warning_messages(evidence):
    """Finite caller diagnostics; the complete evidence remains separately available."""
    summary = evidence.get("projection_summary", {})
    if not summary.get("incomplete"):
        return []
    lines = ["Incomplete forward projection: model validity does not establish source preservation."]
    for kind in ("omitted", "partial"):
        for entry in summary[kind]:
            lines.append(kind + " " + entry["source_pointer"] + ": " + entry["reason"])
    return lines
