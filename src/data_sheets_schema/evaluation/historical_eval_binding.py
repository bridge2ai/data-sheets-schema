"""Explicit retrospective artifact identity, never a generation registration (#5126).

The pinned cohort and decision are caller-selected evidence. Hashes do not
authenticate human approval, provider execution or permission to score.
"""
from pathlib import Path
import hashlib

from .run_identity import same_run

FORMAT = "historical_artifact_binding_v1"
EVALUATION_FORMAT = "registered_historical_semantic_evaluation_v1"
KIND = "historical_provenance_v1"
CONDITION_POINTER = "/prompts/request/spec/condition"


def checked_pin(pin):
    from . import registered_eval_runner as runner
    if (not isinstance(pin, dict) or set(pin) != {"path", "sha256", "bytes"}
            or not isinstance(pin["path"], str)
            or not Path(pin["path"]).is_absolute()
            or ".." in Path(pin["path"]).parts or str(Path(pin["path"])) != pin["path"]
            or not isinstance(pin["sha256"], str) or not runner._SHA.fullmatch(pin["sha256"])
            or type(pin["bytes"]) is not int or not 0 < pin["bytes"] <= runner.MAX_FILE_BYTES):
        raise ValueError("historical evidence requires an absolute bounded file pin")
    return pin


def normalized_run(provenance, *, condition_pointer):
    """Resolve only the declared historical pointer; conflicting evidence refuses."""
    if condition_pointer != CONDITION_POINTER:
        raise ValueError("unsupported historical condition pointer")
    if (not isinstance(provenance, dict)
            or provenance.get("record_type") != "d4d_generation_provenance"
            or "shared_generation" in provenance):
        raise ValueError("historical authority requires provenance without shared generation")
    run = provenance.get("run")
    if not isinstance(run, dict) or not same_run(run, run):
        raise ValueError("historical provenance has an invalid run identity")
    for key in ("project", "label", "method", "arm"):
        value = run.get(key)
        if (not isinstance(value, str) or not value or value != value.strip()
                or len(value) > 4096 or any(ord(c) < 32 for c in value)):
            raise ValueError("historical run requires explicit bounded identities")
    if type(run.get("replicate")) is not int or run["replicate"] < 1:
        raise ValueError("historical run requires an explicit positive replicate")
    condition = provenance
    for key in ("prompts", "request", "spec", "condition"):
        if not isinstance(condition, dict) or key not in condition:
            raise ValueError("historical condition pointer is missing")
        condition = condition[key]
    if (not isinstance(condition, str) or not condition or condition != condition.strip()
            or len(condition) > 4096 or any(ord(c) < 32 for c in condition)):
        raise ValueError("historical condition must be a bounded nonempty string")
    if "condition" in run and run["condition"] != condition:
        raise ValueError("historical condition evidence conflicts")
    return {**run, "condition": condition}


def admit(raw, read_pin, *, binding_path):
    """Validate captured binding bytes using only the supplied bounded reader.

    Used by preparation, saved-package audit and explicitly opted-in campaign
    packs. No registration is synthesized, original evidence is never edited,
    and missing historical controls remain unavailable.
    """
    from . import registered_eval_runner as runner
    from .cohort_manifest import parse_cohort
    from data_sheets_schema.provenance import resolve_record_input

    doc = runner._json(raw)
    fields = {"format", "record_role", "record", "provenance", "cohort", "decision",
              "decision_reference", "condition_pointer"}
    if (not isinstance(doc, dict) or set(doc) != fields or doc["format"] != FORMAT
            or doc["record_role"] != "full"):
        raise ValueError("requires an explicit historical full-artifact binding")
    reference = doc["decision_reference"]
    if (not isinstance(reference, str) or not reference or reference != reference.strip()
            or len(reference) > 4096 or any(ord(c) < 32 for c in reference)):
        raise ValueError("historical binding requires a bounded decision reference")

    def take(name):
        pin = checked_pin(doc[name])
        value = read_pin(pin)
        if not isinstance(value, bytes) or len(value) != pin["bytes"] or runner._sha(value) != pin["sha256"]:
            raise ValueError("historical captured evidence differs from its pin")
        return value

    original, provenance_raw = take("record"), take("provenance")
    cohort_raw = take("cohort")
    take("decision")
    prior = runner._yaml(provenance_raw)
    run = normalized_run(prior, condition_pointer=doc["condition_pointer"])
    runner.require_eligible_generation(prior)
    from data_sheets_schema.latch_journal import record_age
    if record_age(prior) != "pre-D41":
        raise ValueError("historical authority requires positive pre-D41 age evidence")
    cohort = parse_cohort(cohort_raw)
    entries = [entry for entry in cohort if same_run(
        {**entry, "arm": entry["input_arm"]}, run)
        and entry["condition"] == run["condition"] and entry["replicate"] == run["replicate"]]
    if len(entries) != 1:
        raise ValueError("historical run is absent or ambiguous in the pinned cohort")
    validation = prior.get("validation")
    if not isinstance(validation, dict) or validation.get("passed") is not True:
        raise ValueError("historical record validation must explicitly pass")
    artifacts = validation.get("artifacts")
    artifact = artifacts.get("full") if isinstance(artifacts, dict) else None
    if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
        raise ValueError("historical provenance must bind its full output")
    def check_output(entry, *, required):
        if not isinstance(entry, dict):
            raise ValueError("historical full output declaration must be a mapping")
        if required or "path" in entry:
            path = entry.get("path")
            if not isinstance(path, str) or not path:
                raise ValueError("historical full output path must be explicit")
            resolved = resolve_record_input(Path(path), Path(doc["provenance"]["path"]))
            if resolved is None or str(resolved.absolute()) != doc["record"]["path"]:
                raise ValueError("historical full output path differs from provenance")
        hashes = {key: entry[key] for key in ("md5", "sha256") if key in entry}
        if (required and not hashes) or any(
                not isinstance(digest, str) or hashlib.new(key, original).hexdigest() != digest
                for key, digest in hashes.items()):
            raise ValueError("historical full output hash differs from provenance")

    check_output(artifact, required=True)
    # Older provenance can retain a second description (and old hash claims)
    # under outputs. Missing claims stay unknown; supplied claims must agree.
    disagreements = []
    if "outputs" in prior:
        if not isinstance(prior["outputs"], dict):
            raise ValueError("historical outputs must be a mapping")
        if "full" in prior["outputs"]:
            check_output(prior["outputs"]["full"], required=False)
            output = prior["outputs"]["full"]
            if "bytes" in output and output["bytes"] != len(original):
                disagreements.append({"source": "outputs.full.bytes",
                                      "claimed": output["bytes"], "actual": len(original)})
    binding_pin = runner.shared.file_pin(Path(binding_path), raw)
    checked_pin(binding_pin)
    identity = {
        "kind": KIND, "cohort": doc["cohort"], "decision": doc["decision"],
        "decision_reference": reference, "condition_pointer": doc["condition_pointer"],
        "normalized_run": run,
        "recorded_byte_claim_disagreements": disagreements,
        "evidence_status": {"generation_registration": "not_recorded",
                            "generation_acceptance": "not_established"},
    }
    return {"generation_run": {key: run[key] for key in ("arm", "project", "label", "method")},
            "normalized_run": run, "provenance": prior, "original": original,
            "record": doc["record"], "generation_provenance": doc["provenance"],
            "historical_binding": binding_pin, "historical_identity": identity,
            "comparison_arm": entries[0]["comparison_arm"], "cohort_entry": entries[0]}


def forbidden_paths(admitted):
    identity = admitted["historical_identity"]
    return tuple(pin["path"] for pin in (admitted["historical_binding"],
        admitted["generation_provenance"], identity["cohort"], identity["decision"]))


def parse_binding_argument(value):
    """CLI spelling is SHA256=PATH; the digest is independently supplied."""
    from . import registered_eval_runner as runner
    digest, sep, path = value.partition("=")
    if not sep or not runner._SHA.fullmatch(digest) or not path:
        raise ValueError("historical binding requires SHA256=PATH")
    return Path(path), digest


def capture_for_pack(bindings, *, cohort_pin, decisions):
    """Capture opt-in historical pack inputs; return admissions and read guards."""
    from . import registered_eval_runner as runner
    bindings, decisions = tuple(bindings), tuple(decisions)
    if not bindings:
        if decisions:
            raise ValueError("historical decisions require explicit historical bindings")
        return {}, {}
    if not cohort_pin or not decisions or len(bindings) > 1000 or len(decisions) > 1000:
        raise ValueError("historical campaign binding requires cohort and selected decision")
    snapshots = {}
    total = 0

    def take_path(path):
        nonlocal total
        path = Path(path).absolute()
        if path.resolve() != path or ".." in path.parts:
            raise ValueError(f"historical authorities require canonical absolute paths without aliases: {path}")
        raw = runner._read(path)
        if str(path) in snapshots and snapshots[str(path)] != raw:
            raise ValueError("historical pack authority changed during capture")
        if str(path) not in snapshots:
            total += len(raw)
            if total > 128_000_000:
                raise ValueError("historical pack authority byte bound exceeded")
        snapshots[str(path)] = raw
        return raw

    def take_pin(pin):
        checked_pin(pin)
        raw = take_path(pin["path"])
        if len(raw) != pin["bytes"] or runner._sha(raw) != pin["sha256"]:
            raise ValueError("historical pack authority pin differs")
        return raw

    selected_decisions = [runner.shared.file_pin(Path(path).absolute(), take_path(path)) for path in decisions]
    admitted = {}
    for path, digest in bindings:
        path = Path(path).absolute()
        raw = take_path(path)
        if not isinstance(digest, str) or not runner._SHA.fullmatch(digest) or runner._sha(raw) != digest:
            raise ValueError("historical binding SHA256 differs")
        entry = admit(raw, take_pin, binding_path=str(path))
        identity = entry["historical_identity"]
        if identity["cohort"] != cohort_pin or selected_decisions.count(identity["decision"]) != 1:
            raise ValueError("historical pack cohort or decision differs from selected authority")
        selected = entry["cohort_entry"]
        key = (selected["arm"], selected["project"], selected["label"])
        if key in admitted:
            raise ValueError("duplicate historical pack identity")
        admitted[key] = entry
    return admitted, snapshots
