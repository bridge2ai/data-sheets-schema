"""Separate evaluation conditions from fixed-record repeats (#5126, 2026-11-05).

These keys describe already-admitted evaluation plans. They do not admit a
generation artifact, establish scientific comparability, or authenticate review.
"""
from copy import deepcopy
import hashlib
import json


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def evaluation_condition_key(plan):
    """Identify the shared rating procedure, excluding generation identities.

    A runtime's installation path and an authority's checkout root are not
    experimental conditions. Their byte identities remain in this key. The
    per-attempt cap is retained because it is passed to the evaluator runtime;
    the number of ratings and total panel allocation are not one rating's input.
    """
    from .registered_eval_runner import EVALUATOR_MODULES
    from data_sheets_schema.semantic_instrument import select_semantic_instrument

    implementations = []
    for module in EVALUATOR_MODULES:
        matches = [pin for pin in plan["authorities"]
                   if pin["path"].endswith("/data_sheets_schema/" + module)]
        if len(matches) != 1:
            raise ValueError("evaluation condition requires each common evaluator implementation")
        pin = matches[0]
        implementations.append({"module": module, "sha256": pin["sha256"], "bytes": pin["bytes"]})
    selected = select_semantic_instrument(plan["instrument"]["rubric"], plan["instrument"]["version"])
    schema_pins = [pin for pin in plan["authorities"]
                   if pin["path"].endswith("/" + selected.schema_path)]
    if len(schema_pins) != 1:
        raise ValueError("evaluation condition requires the selected instrument schema")
    schema = {"resource": selected.schema_path,
              **{key: schema_pins[0][key] for key in ("sha256", "bytes")}}
    runtime = deepcopy(plan["runtime"])
    binary = runtime["binary"]
    if binary is not None:
        runtime["binary"] = {key: binary[key] for key in ("sha256", "bytes")}
    blinding = {key: plan["blinding"][key]
                for key in ("version", "pyyaml_version", "dumper_class")}
    return _digest({
        "format": "evaluation_condition_key_v1",
        "record_role": plan["record_role"],
        "context_sha256": plan["context_sha256"],
        "instrument": plan["instrument"],
        "instrument_schema": schema,
        "execution_adapter": plan["execution_adapter"],
        "execution_mode": plan["execution_mode"],
        "runtime": runtime,
        "reserved_cost_dollars_per_attempt": plan["reserved_cost_dollars_per_attempt"],
        "blinding_policy": blinding,
        "evaluator_implementations": implementations,
    })


def repeat_key(plan):
    """Identify repeated ratings of exactly one bound input and condition."""
    return _digest({
        "format": "evaluation_repeat_key_v1",
        "evaluation_condition_key": evaluation_condition_key(plan),
        "generation_evaluation_format": plan["format"],
        "generation_run": plan["generation_run"],
        "generation_registration": plan["generation_registration"],
        "generation_provenance": plan["generation_provenance"],
        "historical_binding": plan.get("historical_binding"),
        "historical_identity": plan.get("historical_identity"),
        "record": plan["record"],
        "blinded_input_sha256": plan["blinded_input_sha256"],
        "blinding": plan["blinding"],
    })
