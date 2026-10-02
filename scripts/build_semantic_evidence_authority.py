#!/usr/bin/env python3
"""Explicitly build the frozen semantic-v3 name authority from current sources.

This is a release operation, never part of evaluation acceptance. A later
authority revision needs its own instrument identity, not a silent rebuild.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from data_sheets_schema.evaluation_context import FIELD_ALIASES


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ("src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
           "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")
RUBRICS = ("data/rubric/rubric10.txt", "data/rubric/rubric20.txt")


def build(root: Path = ROOT) -> dict:
    names = set()
    sources = {}
    for relative in (*SCHEMAS, *RUBRICS, "src/data_sheets_schema/evaluation_context.py"):
        raw = (root / relative).read_bytes()
        sources[relative] = hashlib.sha256(raw).hexdigest()
        if relative in SCHEMAS:
            document = yaml.safe_load(raw)
            names.update(document.get("slots", {}))
            for definition in document.get("classes", {}).values():
                names.update(definition.get("attributes", {}))
                names.update(definition.get("slot_usage", {}))
                names.update(definition.get("slots", []))
        elif relative in RUBRICS:
            document = yaml.safe_load(raw)
            if relative == RUBRICS[0]:
                items = [item for element in document["d4d_complex_proxy_rubric"]["rubric"]
                         for item in element["sub_elements"]]
            else:
                items = document["d4d_evaluation_rubric"]["rubric"]
            for item in items:
                fields = item.get("field", [])
                for field in [fields] if isinstance(fields, str) else fields:
                    names.update(field.split("."))
    for field, aliases in FIELD_ALIASES.items():
        for path in (field, *aliases):
            names.update(path.split("."))
    return {"semantic_version": "3.0", "authority_version": "1.0",
            "policy": "declared schema/rubric/alias token names; not class/range traversal",
            "sources": sources, "names": sorted(names)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/rubric/semantic_evidence_authority_v3.json")
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
