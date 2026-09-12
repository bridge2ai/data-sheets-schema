"""Compile the generation-record contract, including its non-null policy.

LinkML's Any range admits null even when a slot is required. The record
schema explicitly opts into non-null required values; implement that policy
in the exported JSON Schema, shared by the runtime and CLI validators.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema.exceptions import best_match
from jsonschema.validators import validator_for
from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml.validator.plugins import JsonschemaValidationPlugin
from linkml.validator.report import Severity, ValidationResult
from linkml_runtime.linkml_model.meta import SchemaDefinition


def _non_null_required(schema: dict) -> None:
    """Add a value constraint wherever the generated contract requires a key.

    Traverse schema keywords only. Arbitrary examples/defaults are data, and
    a user-supplied object containing a key called 'required' is not a schema.
    Keep the conditions in place so optional blocks stay optional by mode.
    """
    for key in ("$defs", "definitions", "properties", "patternProperties", "dependentSchemas"):
        for child in (schema.get(key) or {}).values():
            if isinstance(child, dict):
                _non_null_required(child)
    for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
        for child in schema.get(key) or []:
            if isinstance(child, dict):
                _non_null_required(child)
    for key in ("if", "then", "else", "not", "items", "additionalProperties", "contains"):
        child = schema.get(key)
        if isinstance(child, dict):
            _non_null_required(child)
    for name in schema.get("required") or []:
        properties = schema.setdefault("properties", {})
        previous = properties.get(name, {})
        properties[name] = {"allOf": [previous, {"not": {"type": "null"}}]}


def compile_record_schema(path: Path, *, content: bytes | None = None) -> dict:
    raw = path.read_bytes() if content is None else content
    source = yaml.safe_load(raw)
    policy = (source.get("annotations") or {}).get("required_values_non_null", False)
    if not isinstance(policy, bool):
        raise ValueError("required_values_non_null must be a boolean schema annotation")
    definition = SchemaDefinition(**source)
    definition.source_file = str(path.resolve())
    schema = json.loads(JsonSchemaGenerator(
        definition, top_class="GenerationRecord", not_closed=False,
        mergeimports=True, base_dir=str(path.resolve().parent),
        include_range_class_descendants=True).serialize())
    if policy:
        _non_null_required(schema)
        schema["$comment"] = (
            "Compiled from the generation-record LinkML schema with its "
            "required_values_non_null policy. Export with d4d provenance record-schema; "
            "generic LinkML generation does not implement this annotation.")
    return schema


class RecordValidationPlugin(JsonschemaValidationPlugin):
    """Use the same complete JSON contract that record-schema exports."""

    def __init__(self, schema: dict):
        super().__init__(closed=True)
        cls = validator_for(schema)
        cls.check_schema(schema)
        self.validator = cls(schema, format_checker=cls.FORMAT_CHECKER)

    def process(self, instance, context):
        for error in self.validator.iter_errors(instance):
            best = best_match([error])
            yield ValidationResult(
                type="jsonschema validation", severity=Severity.ERROR,
                instance=instance, instantiates=context.target_class,
                message=f"{best.message} in /{'/'.join(str(p) for p in best.absolute_path)}",
                context=[item.message for item in error.context], source=best)
