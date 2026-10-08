"""Compare captured semantic identity declarations, never accept or score a rating."""
from __future__ import annotations

from data_sheets_schema.evaluation_context import (
    COLLECTION_POLICY, context_digest, dataset_units, normalize_context,
)
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema.support_plan import canonical

MAX_ROSTER_JOBS = 10_000
STATES = ("associated", "missing", "mismatched", "unsupported")
COUNT_BASIS = "captured primary roster jobs for exactly the fitness descriptor's selected records"
LIMITATIONS = [
    "Rubric association checks declared identity only; it does not accept a rating or a score.",
    "Instrument hashes are captured roster declarations, not authentication of released resource bytes.",
    "Rubric schema, arithmetic, evaluator execution and scientific validity are not assessed.",
    "Missing historical context remains unsupported; no rubric scores or repeatability ratings are propagated.",
]


def assess(document, job, roster, record):
    """Keep known conflicts visible even when other historical declarations are absent."""
    conflicts, unknown = [], []

    def issue(items, field, reason):
        items.append({"field": field, "reason": reason})

    def check(container, key, expected, location, *, required=True):
        field = f"{location}.{key}"
        if key not in container:
            if required:
                issue(unknown, field, "missing_declaration")
        elif expected is not None and canonical(container[key]) != canonical(expected):
            issue(conflicts, field, "declaration_conflicts")

    def mapping(value, location):
        if not isinstance(value, dict):
            issue(unknown, location, "missing_or_invalid_mapping")
            return {}
        return value

    def digest(value, location):
        if not isinstance(value, str) or not saved._SHA.fullmatch(value):
            issue(unknown, location, "missing_or_invalid_sha256")
            return None
        return value

    metadata = mapping(document.get("metadata"), "result.metadata")
    legacy = mapping(document["evaluation_metadata"], "result.evaluation_metadata") if "evaluation_metadata" in document else {}
    instruments = mapping(roster.get("instruments"), "roster.instruments")
    instrument = mapping(instruments.get(job["rubric"]), "roster.instrument")
    pins = roster["pinned_files"]
    for field, expected in (("rubric", job["rubric"]), ("project", job["project"]),
                            ("method", job["method"]), ("d4d_file", job["input"])):
        check(document, field, expected, "result")
    labels = [(document, "label", "result"), (metadata, "label", "result.metadata"),
              (metadata, "replicate_label", "result.metadata")]
    if not any(key in container for container, key, _ in labels):
        issue(unknown, "result.label", "missing_declaration")
    for container, key, location in labels:
        check(container, key, job["label"], location, required=False)
    for field in ("cohort", "generation_rep"):
        check(document, field, job[field], "result", required=False)
        check(metadata, field, job[field], "result.metadata", required=False)
    check(document, "job_id", job["id"], "result", required=False)
    check(metadata, "job_id", job["id"], "result.metadata", required=False)

    input_sha = pins[job["input"]]  # The caller already rechecks exact record bytes.
    check(metadata, "input_sha256", input_sha, "result.metadata")
    for container, location in ((metadata, "result.metadata"), (legacy, "result.evaluation_metadata")):
        check(container, "d4d_file_hash", input_sha, location, required=False)

    version = instrument.get("version")
    if not isinstance(version, str) or not version:
        issue(unknown, "roster.instrument.version", "missing_declaration")
        version = None
    check(document, "version", version, "result")
    selected = None
    try:
        if job["rubric"] not in {"rubric10-semantic", "rubric20-semantic"} or version not in {"3.0", "4.0"}:
            raise ValueError("unsupported declared semantic contract")
        selected = select_semantic_instrument(job["rubric"], version)
    except ValueError:
        issue(unknown, "roster.instrument", "unsupported_semantic_contract")

    resources = {}
    for key in ("definition", "rubric", "schema"):
        path = instrument.get(key)
        if not isinstance(path, str) or not path:
            issue(unknown, f"roster.instrument.{key}", "missing_declaration")
            resources[key] = None
        else:
            resources[key] = digest(pins.get(path), f"roster.pinned_files.{key}")
        if selected is not None:
            check(instrument, key, getattr(selected, key + "_path"), "roster.instrument")
    definition = digest(instrument.get("definition_sha256"), "roster.instrument.definition_sha256")
    if definition is not None and resources["definition"] is not None and definition != resources["definition"]:
        issue(conflicts, "roster.instrument.definition_sha256", "contradicts_pinned_files")
    # Both declarations must agree independently; a preferred alias cannot hide a conflict.
    check(metadata, "instrument_sha256", definition, "result.metadata")
    check(metadata, "instrument_sha256", resources["definition"], "result.metadata")
    check(metadata, "instrument_kind", "agent_definition", "result.metadata")
    check(metadata, "rubric_sha256", resources["rubric"], "result.metadata")
    check(legacy, "rubric_hash", resources["rubric"], "result.evaluation_metadata", required=False)
    check(metadata, "schema_sha256", resources["schema"], "result.metadata", required=False)
    agent = instrument.get("agent")
    if not isinstance(agent, str) or not agent:
        issue(unknown, "roster.instrument.agent", "missing_declaration")
        agent = None
    check(job, "agent", agent, "roster.job")
    if selected is not None:
        check(instrument, "agent", selected.agent, "roster.instrument")
        check(job, "agent", selected.agent, "roster.job")
        authority = digest(pins.get(selected.evidence_authority_path), "roster.pinned_files.evidence_authority")
        check(metadata, "evidence_authority_sha256", authority, "result.metadata")
    else:
        authority = None
    predecessor = None
    if version == "4.0":
        path = select_semantic_instrument("rubric20-semantic", "3.0").definition_path
        check(instrument, "predecessor_definition", path, "roster.instrument")
        predecessor = digest(pins.get(path), "roster.pinned_files.predecessor")
        declared = digest(instrument.get("predecessor_sha256"), "roster.instrument.predecessor_sha256")
        if declared is not None and predecessor is not None and declared != predecessor:
            issue(conflicts, "roster.instrument.predecessor_sha256", "contradicts_pinned_files")

    contexts = {}
    for container, location in ((job, "roster.job"), (document, "result")):
        if "applicability_context" not in container or not isinstance(container["applicability_context"], dict):
            issue(unknown, f"{location}.applicability_context", "missing_or_invalid_mapping")
            continue
        try:
            contexts[location] = normalize_context(container["applicability_context"])
        except ValueError:
            issue(unknown, f"{location}.applicability_context", "invalid_context_declaration")
    if len(contexts) == 2 and canonical(contexts["roster.job"]) != canonical(contexts["result"]):
        issue(conflicts, "result.applicability_context", "declaration_conflicts")
    for context in contexts.values():
        check(metadata, "context_sha256", context_digest(context), "result.metadata")
    if not contexts:
        check(metadata, "context_sha256", None, "result.metadata")

    scope = mapping(document.get("evaluation_scope"), "result.evaluation_scope")
    check(scope, "collection_metadata_inherited", False, "result.evaluation_scope")
    try:
        units = [{"path": path, "id": unit.get("id")} for path, unit in dataset_units(record)]
    except ValueError:
        issue(unknown, "record", "unsupported_dataset_scope")
    else:
        check(scope, "units", units, "result.evaluation_scope")
        check(scope, "policy", COLLECTION_POLICY if len(units) > 1 else "single_dataset", "result.evaluation_scope")

    # Deduplicate diagnostics while preserving their deterministic field order.
    def unique(rows):
        return [dict(pair) for pair in dict.fromkeys(tuple(row.items()) for row in rows)]
    return {"state": "mismatched" if conflicts else "unsupported" if unknown else "associated",
            "conflicts": unique(conflicts), "unsupported": unique(unknown),
            "declared_instrument": {"version": version, "agent": agent,
                                    **resources, "evidence_authority": authority, "predecessor": predecessor},
            "declared_context_sha256": context_digest(contexts["roster.job"]) if "roster.job" in contexts else None}
