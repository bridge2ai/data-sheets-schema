"""Opt-in restore-only API policy (#2923), using the existing removals instrument.

Nothing here establishes that a phase-1 value was true. Restoration is a
conservative alternative to silently deleting it without a covering finding.
New audit amendments and historical reclassification are outside this policy.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

POLICY_PATH = Path("src/download/prompts/removal_repair_v1.md")
POLICY_SHA256 = "cd21a27d1b2ac9ac8893d0d0537811a0bac563811a2a879296d262091b1f0f81"
VERSION = 1
PHASE = "removal_repair_full"


def policy_text() -> str:
    from data_sheets_schema.resources import resource_path
    raw = resource_path(POLICY_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError("removal repair v1 policy bytes do not match their frozen digest")
    return raw.decode("utf-8")


def policy_identity() -> dict:
    policy_text()  # a missing/drifted instrument cannot be named as verified
    return {"version": VERSION, "sha256": POLICY_SHA256, "path": str(POLICY_PATH)}


def _typed_equal(a: Any, b: Any) -> bool:
    return type(a) is type(b) and a == b


def _leaves(doc: dict) -> list[tuple[str, Any, str | None]]:
    from data_sheets_schema.removals import values
    # No stringification of malformed keys into otherwise valid addresses.
    def check(node, ancestors=frozenset()):
        if isinstance(node, (dict, list)):
            if id(node) in ancestors:
                raise ValueError("record contains a cyclic YAML alias")
            ancestors = ancestors | {id(node)}
        if isinstance(node, dict):
            if any(not isinstance(k, str) or not re.fullmatch(r"\w+", k) for k in node):
                raise ValueError("record has a key outside the removal path grammar")
            for v in node.values():
                check(v, ancestors)
        elif isinstance(node, list):
            for v in node:
                check(v, ancestors)
    check(doc)
    return values(doc)


def load_inputs(original_raw: str, current_raw: str, audit_raw: str) -> tuple[dict, dict, dict]:
    from data_sheets_schema.evidence_assertions import load_json, load_record
    original, current = load_record(original_raw), load_record(current_raw)
    audit = load_json(audit_raw)
    if not original or not current:
        raise ValueError("original and current records must be nonempty mappings")
    for doc in (original, current):
        _leaves(doc)
    if (not isinstance(audit, dict) or not isinstance(audit.get("findings"), list)
            or any(not isinstance(f, dict) for f in audit["findings"])):
        raise ValueError("audit must carry a readable findings list")
    return original, current, audit


def reading(original_raw: str, current_raw: str, audit_raw: str, *, receipt=None) -> dict:
    from data_sheets_schema.removals import classify
    original, current, audit = load_inputs(original_raw, current_raw, audit_raw)
    # Public diagnostics remain capped at 50; a repair work order must include
    # every target and the resulting success check must cover all of them.
    return classify(original, current, audit, receipt=receipt,
                    snapshot_sha256=hashlib.sha256(original_raw.encode()).hexdigest(),
                    path_limit=None)


def restored_candidate(original_raw: str, current_raw: str, audit_raw: str,
                       candidate_raw: str, *, receipt=None) -> dict:
    """Reject prose-only resolution, novel facts and damage to retained data.

    All comparisons follow the detector's existing receipt identity join;
    ambiguous joins are refused. Required restoration is exact and typed,
    not containment in commentary or the detector's flattening heuristic.
    """
    from data_sheets_schema.evidence_assertions import load_record
    from data_sheets_schema.receipts import _resolve_value, remap_path
    original, current, audit = load_inputs(original_raw, current_raw, audit_raw)
    candidate = load_record(candidate_raw)
    candidate_leaves = _leaves(candidate)
    before = reading(original_raw, current_raw, audit_raw, receipt=receipt)
    targets = {r["path"] for r in before["unfounded_paths"]}
    if before["unfounded"] != len(targets):
        raise ValueError("removal work order is incomplete or ambiguous")

    def same_leaf(path, old, new, value):
        mapped = remap_path(path, old, new)
        actual = mapped.get("path")
        present, found = _resolve_value(new, actual) if actual else (False, None)
        if not present or not _typed_equal(value, found):
            return None
        return actual

    # Preserve every populated current scalar, including ids and commentary.
    retained = set()
    for path, value, _ in _leaves(current):
        mapped = same_leaf(path, current, candidate, value)
        if mapped is None or mapped in retained:
            raise ValueError(f"candidate changes or ambiguously collapses current value: {path}")
        retained.add(mapped)
    for path in targets:
        present, value = _resolve_value(original, path)
        if not present or same_leaf(path, original, candidate, value) is None:
            raise ValueError(f"candidate does not restore original value at its structural role: {path}")
    used_original = set()
    for path, value, _ in candidate_leaves:
        if path in retained:
            continue
        original_path = same_leaf(path, candidate, original, value)
        scaffolding = False
        if original_path:
            parent, _, key = original_path.rpartition(".")
            scaffolding = key in {"id", "class", "conforms_to_class"} and any(
                target.startswith(parent + ".") for target in targets)
        if (original_path is None or original_path in used_original
                or (original_path not in targets and not scaffolding)):
            raise ValueError(f"candidate adds material outside the restoration work order: {path}")
        used_original.add(original_path)
    after = reading(original_raw, candidate_raw, audit_raw, receipt=receipt)
    if after["unfounded"] != 0:
        raise ValueError("candidate leaves unfounded removals")
    return after


def request_payload(original_raw: str, current_raw: str, audit_raw: str,
                    receipt_raw: str | None, before: dict) -> str:
    """Data for one restore-only request, including uncapped values and receipt."""
    from data_sheets_schema.receipts import _resolve_value
    original, _, _ = load_inputs(original_raw, current_raw, audit_raw)
    work = [{**row, "original_value": _resolve_value(original, row["path"])[1]}
            for row in before["unfounded_paths"]]
    # YAML retains date/bool/number types in the work order and safely quotes
    # strings; JSON escapes untrusted record delimiters in the envelope.
    return json.dumps({"original_full_yaml": original_raw, "current_full_yaml": current_raw,
                       "unchanged_audit_json": audit_raw, "coverage_receipt_yaml": receipt_raw,
                       "restoration_work_order_yaml": yaml.safe_dump(work, sort_keys=False)},
                      ensure_ascii=False)


def inspect_run(spec, *, record=None) -> tuple[dict, dict]:
    """Current reading and exact request inputs, with no historical glob fallback."""
    from data_sheets_schema.snapshot_store import read_latest
    inputs = {}
    pins = {}
    for key, name in (("original", "full.yaml"), ("audit", "audit.json")):
        indexed, found = read_latest(spec.metadata_dir, spec.project,
                                     f"{spec.project}_{name}", spec=spec, record=record)
        if not indexed or found is None:
            raise ValueError(f"removal repair requires an attested {key} snapshot")
        path, raw = found
        inputs[key] = raw.decode("utf-8")
        pins[key] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    raw = spec.full_path.read_bytes()
    inputs["current"] = raw.decode("utf-8")
    pins["current"] = {"path": str(spec.full_path), "sha256": hashlib.sha256(raw).hexdigest()}
    inputs["receipt"] = None
    if spec.writes_receipt:
        indexed, found = read_latest(spec.metadata_dir, spec.project,
                                     f"{spec.project}_coverage_receipt.yaml", spec=spec, record=record)
        if not indexed or found is None:
            raise ValueError("removal repair requires the attested coverage receipt")
        path, raw = found
        inputs["receipt"] = raw.decode("utf-8")
        pins["receipt"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    receipt = yaml.safe_load(inputs["receipt"]) if inputs["receipt"] is not None else None
    out = reading(inputs["original"], inputs["current"], inputs["audit"], receipt=receipt)
    out["artifacts"] = pins
    return out, inputs


def output_pins(spec) -> dict:
    return {name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in (("full", spec.full_path), ("core", spec.core_path))}


def completion_check(spec, *, record=None, expected_outputs=None) -> dict:
    """Recompute final facts; a saved/model-written pass is never authority."""
    from data_sheets_schema.usage_ledger import UsageLedgerError
    out = {"policy": policy_identity(), "checked": False, "findings": []}
    try:
        final, _ = inspect_run(spec, record=record)
        out.update(checked=True, final=final)
        if final["unfounded"] != 0:
            out["findings"] = [{"kind": "unfounded_removals", "count": final["unfounded"]}]
        if expected_outputs is not None:
            actual = output_pins(spec)
            for name in ("full", "core"):
                expected = expected_outputs.get(name) if isinstance(expected_outputs, dict) else None
                if not isinstance(expected, dict) or not re.fullmatch(r"[a-f0-9]{64}", str(expected.get("sha256", ""))):
                    raise ValueError(f"verified removal repair {name} output pin is missing or invalid")
                if actual[name] != expected:
                    out["findings"].append({"kind": "removal_output_changed", "artifact": name,
                                            "expected": expected, "actual": actual[name]})
    except (OSError, ValueError, UnicodeError, yaml.YAMLError, UsageLedgerError) as exc:
        out["checked"] = False
        out["findings"] = [{"kind": "removal_inputs_unusable", "detail": str(exc)}]
    return out


def run(spec, client, settings: dict, usage: list) -> dict:
    """One admitted restoration, verified before publishing either record.

    Rejections are terminal in the existing generation ledger. It owns the
    allowance too, so an interrupted/failed/truncated delivery cannot buy a
    second attempt by dropping a response or removing a progress file.
    """
    import tempfile
    import time
    from datetime import datetime, timezone
    from data_sheets_schema import api_runner as api, reasoning, usage_ledger
    from data_sheets_schema.derive_core import core_header, derive_core

    out = {"policy": policy_identity(), "checked": False, "findings": [],
           "attempted": False, "changed": False}

    def reject(kind, detail):
        out["findings"] = [{"kind": kind, "detail": detail}]
        # Before snapshots/provenance, whose persistence can itself fail.
        usage_ledger.record_evidence_refusal(spec, "report", out)
        api._snapshot(spec, f"{spec.project}_removal_repair_check.json", json.dumps(out, indent=2))
        return out

    try:
        before, inputs = inspect_run(spec)
        out["output_pins"] = output_pins(spec)
    except (OSError, ValueError, UnicodeError, yaml.YAMLError, usage_ledger.UsageLedgerError) as exc:
        return reject("removal_inputs_unusable", str(exc))
    out.update(checked=True, before=before, final=before)
    if before["unfounded"] == 0:
        if usage_ledger.removal_repair_attempted(spec):
            # Do not relabel previously restored bytes as an untouched run.
            # This recovers provenance, never its saved success reading.
            out = usage_ledger.accepted_removal_outcome(spec)
            out.update(checked=True, final=before, resumed=True)
        return out
    if before["unfounded"] is None:
        return reject("removal_inputs_unusable", "unfounded removals could not be classified")
    if usage_ledger.removal_repair_attempted(spec):
        out["attempted"] = True
        return reject("removal_repair_exhausted", "this generation already admitted its one restore-only repair")
    digest = api.schema_digest.digest_text("Dataset", profile=spec.profile_obj)
    req = api.PhaseRequest(phase=PHASE, system=policy_text(), messages=[{
        "role": "user", "content": [
            {"type": "text", "text": digest, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": request_payload(inputs["original"], inputs["current"],
                                                       inputs["audit"], inputs["receipt"], before)},
            {"type": "text", "text": policy_text()}]}])
    started, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), time.monotonic()
    ceiling = api.phase_max_tokens(spec, PHASE, api.DEFAULT_MAX_TOKENS, model=settings["name"])
    out["attempted"] = True
    try:
        resp, call_id = api._call_with_usage(
            spec, PHASE, 1, started, client, model=settings["name"],
            thinking=settings.get("thinking"), effort=settings.get("effort"),
            max_tokens=ceiling, temperature=settings["temperature"],
            system=req.system, messages=req.messages,
            on_incomplete=lambda info: api._record_incomplete_stream(
                spec, PHASE, 1, started, info, usage, max_tokens=ceiling))
    except usage_ledger.UsageLedgerError:
        raise  # unresolved accounting already prevents any continuation
    except Exception as exc:  # a transport failure still consumes admission
        return reject("removal_repair_call_failed", str(exc))
    call_usage = api._append_usage(spec, usage, {
        "usage_id": call_id, "phase": PHASE, "attempt": 1, "started_at": started,
        "seconds": round(time.monotonic() - t0, 3),
        "input_tokens": getattr(resp.usage, "input_tokens", None),
        "output_tokens": getattr(resp.usage, "output_tokens", None),
        "thinking_tokens": reasoning.thinking_tokens(resp),
        "cache_read": getattr(resp.usage, "cache_read_input_tokens", None),
        "cache_write": getattr(resp.usage, "cache_creation_input_tokens", None),
        "max_tokens": ceiling, "stop_reason": getattr(resp, "stop_reason", None)})
    response = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    out["usage_id"] = call_id
    out["response_sha256"] = hashlib.sha256(response.encode()).hexdigest()
    api._snapshot(spec, f"{spec.project}_removal_repair_response.txt", response, usage_id=call_id)
    reasoning.append(api._reasoning_path(spec), {"phase": PHASE, "label": spec.label,
        "project": spec.project, "model": settings["name"], "attempt": 1,
        **api._reasoning_usage(spec, call_usage), **reasoning.capture(resp).to_dict()})
    if getattr(resp, "stop_reason", None) == "max_tokens":
        return reject("removal_repair_truncated", "response truncated; records left unchanged")
    try:
        body = api._extract(response, "yaml", api.FULL_SCHEMA_PATH, "Dataset")
        body = api.stamp_provenance_header(body, settings)
        receipt = yaml.safe_load(inputs["receipt"]) if inputs["receipt"] is not None else None
        after = restored_candidate(inputs["original"], inputs["current"], inputs["audit"],
                                   body, receipt=receipt)
        # A candidate must validate, including its derived core, while the
        # actual output pair is still untouched. No shape-repair loop follows
        # this check, because it could delete the restored facts again.
        with tempfile.TemporaryDirectory(prefix="d4d-removal-candidate-") as directory:
            full, core = Path(directory) / "full.yaml", Path(directory) / "core.yaml"
            full.write_text(body, encoding="utf-8")
            # Use the intended full-record destination in the Sources header,
            # not this temporary validation filename. The projection itself
            # still reads only the verified candidate bytes.
            header = "\n".join(core_header(body, spec.full_path, phase4_complete=True))
            projected = yaml.safe_dump(derive_core(yaml.safe_load(body)),
                                       sort_keys=False, allow_unicode=True, width=88)
            core_body = api.stamp_provenance_header(api.normalise_record_text(
                (header + "\n\n" if header else "") + projected), settings)
            core.write_text(core_body, encoding="utf-8")
            for path, schema, cls in ((full, api.FULL_SCHEMA_PATH, "Dataset"),
                                      (core, api.CORE_SCHEMA_PATH, "CoreDataset")):
                errors, failure = api._validator_lines(path, schema, cls)
                if failure or errors:
                    raise ValueError(f"candidate {cls} does not validate: {failure or errors}")
        # Protect against input/output edits during the asynchronous model call.
        current_reading, now = inspect_run(spec)
        if now != inputs:
            out["final"] = current_reading
            raise ValueError("removal repair inputs changed during the request")
    except (OSError, ValueError, RuntimeError, UnicodeError, yaml.YAMLError) as exc:
        return reject("removal_repair_rejected", str(exc))
    # Snapshot accepted bytes before replacing outputs; failure retains paid
    # evidence and cannot purchase another response under this generation.
    api._snapshot(spec, f"{spec.project}_removal_repair_full.yaml", body, usage_id=call_id)
    spec.full_path.write_text(body, encoding="utf-8")
    spec.core_path.write_text(core_body, encoding="utf-8")
    out.update(changed=True, final=after, output_pins=output_pins(spec))
    out["final"]["artifacts"] = {**before["artifacts"], "current": {
        "path": str(spec.full_path), "sha256": hashlib.sha256(body.encode()).hexdigest()}}
    api._snapshot(spec, f"{spec.project}_removal_repair_check.json", json.dumps(out, indent=2))
    return out
