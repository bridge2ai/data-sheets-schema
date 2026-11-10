"""Check review inputs and minimal records against frozen schemas, 2026-11-10.

Inputs: pinned full/Core LinkML source and exchange_canary.json in this checkout.
Outputs: notes/schema_review_20261110/validation_{core,full}.json.
Purpose: distinguish metadata validity from readiness/exchange evidence; no model calls.
Run one schema per invocation with existing dependencies and a 30-second cap.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import signal
import time

ROOT = Path(__file__).resolve().parents[2]
SHA = "7233f193ad102a8488b31ec7333662c8fefaa996"


def timeout_handler(*_):
    raise TimeoutError("30-second schema review validation cap")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", choices=["core", "full"])
    args = parser.parse_args()
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)
    start = time.monotonic()
    from linkml.generators.jsonschemagen import JsonSchemaGenerator
    from jsonschema.validators import validator_for
    source = ROOT / "src/data_sheets_schema/schema" / (
        "D4D_Core.yaml" if args.schema == "core" else "data_sheets_schema.yaml")
    target = "CoreDataset" if args.schema == "core" else "Dataset"
    serialized = JsonSchemaGenerator(str(source), top_class=target).serialize()
    generated = json.loads(serialized)
    cls = validator_for(generated)
    cls.check_schema(generated)
    validator = cls(generated)
    evidence = json.loads((ROOT / "notes/schema_review_20261110/exchange_canary.json").read_text())
    record = evidence["input"]
    if args.schema == "full":
        record = {k: v for k, v in record.items() if k != "distributions"}
    samples = {
        "id_only": {"id": "https://example.org/review/minimal"},
        "missing_id_control": {},
        "exchange_input" if args.schema == "core" else "shared_creator_input": record,
    }
    results = {}
    for name, value in samples.items():
        errors = sorted(validator.iter_errors(value), key=lambda e: str(e.path))
        results[name] = {"input": value, "valid": not errors, "errors": [
            {"path": list(e.path), "message": e.message} for e in errors]}
    output = {
        "source_sha": SHA, "schema": str(source.relative_to(ROOT)), "target_class": target,
        "validator": cls.__name__, "versions": {n: importlib.metadata.version(n)
            for n in ("linkml", "linkml-runtime", "jsonschema")},
        "generated_schema_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        "elapsed_seconds": time.monotonic() - start, "checks": results,
        "limits": "In-memory JSON Schema generated from pinned LinkML; no endpoint, scientific evidence, or RO-Crate conformance checks. No converter rerun.",
    }
    path = ROOT / f"notes/schema_review_20261110/validation_{args.schema}.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    assert path.stat().st_size > 0
    print(json.dumps({"output": str(path), "elapsed_seconds": output["elapsed_seconds"],
                      "checks": {k: v["valid"] for k, v in results.items()}}, indent=2))


if __name__ == "__main__":
    main()
