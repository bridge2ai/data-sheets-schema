"""#5211 packet-review F7: sizing warns about its own context, without relaxing execution.

Synthetic schema/records only; 2026-10-29. No provider or historical edits.
"""
from copy import deepcopy
import json

import pytest
import yaml

from data_sheets_schema import shared_generation as shared, typed_audit
from data_sheets_schema.schema_snapshot import capture_schema
from scripts import build_api_registrations as builder
from tests.test_registration_input_sizing import typed_inputs  # noqa: F401


def vocabulary_case(typed_inputs, value):
    fixture = typed_inputs
    child = fixture["schema_root"].with_name("child.yaml")
    child.write_text(child.read_text().replace("title: {}", "title: {values_from: [TEST_TOPIC]}"))
    document = yaml.safe_load(fixture["record"])
    document["title"] = value
    record = yaml.safe_dump(document, sort_keys=False).encode()
    snapshot = capture_schema(fixture["schema_root"].absolute(), strict=True)
    return fixture, record, snapshot


def strict_packet(fixture, record, snapshot, context):
    return typed_audit.prepare(
        protocol="typed_audit_protocol_v1", original_full=record, bundle=fixture["bundle"],
        manifest=fixture["manifest"], receipt=fixture["receipt"], context=context,
        schema_path=fixture["schema_root"], schema_snapshot=snapshot,
        omission_wire=typed_audit.SHARED_OMISSION_WIRE,
        max_output_tokens=fixture["limits"]["omission_output_tokens"],
        **{key: fixture["limits"][key] for key in
           ("max_paths", "max_inventory_bytes", "max_workers", "max_request_bytes")})


@pytest.mark.parametrize("value", ["Example", None], ids=["populated", "null"])
def test_vocabulary_refusal_is_named_and_execution_still_refuses(typed_inputs, value):
    fixture, record, snapshot = vocabulary_case(typed_inputs, value)
    rendered = builder.render_typed_audit_inputs(
        "EXAMPLE", fixture["limits"], fixture["registration"], record=record, core=None,
        receipt=fixture["receipt"], context=fixture["context"], schema_snapshot=snapshot)
    assert "registered context vocabulary" in rendered["owner_allowance_note"]
    assert "historical sizing record has no current" not in rendered["owner_allowance_note"]
    assert "not validation of an executable packet" in rendered["owner_allowance_note"]
    assert "including null values" in rendered["owner_allowance_warning"]
    assert "would be refused" in rendered["owner_allowance_warning"]
    payload = rendered["requests"]["omission"]["payload"]
    assert payload["record_yaml"] == record.decode()
    assert len(payload["owner_classes"][""]) >= 32
    with pytest.raises(ValueError, match="missing explicitly supplied vocabulary"):
        strict_packet(fixture, record, snapshot, fixture["context"])

    # A declared vocabulary fixes this cause; it is never inferred by sizing.
    context_doc = json.loads(fixture["context"])
    context_doc["vocabulary"] = {"TEST_TOPIC": ["Example"]}
    context = shared.canonical(context_doc)
    context_path = fixture["schema_root"].with_name("declared-context.json")
    context_path.write_bytes(context)
    registration = deepcopy(fixture["registration"])
    registration["inputs"]["context"] = shared.file_pin(context_path)
    checked = builder.render_typed_audit_inputs(
        "EXAMPLE", fixture["limits"], registration, record=record, core=None,
        receipt=fixture["receipt"], context=context, schema_snapshot=snapshot)
    assert checked["owner_allowance_note"] is None
    assert checked["owner_allowance_warning"] is None
    strict_packet(fixture, record, snapshot, context)


def test_vocabulary_warning_reaches_the_own_record_sizing_result(typed_inputs, tmp_path):
    fixture, record, snapshot = vocabulary_case(typed_inputs, "Example")
    record = b"# D4D Datasheet for EXAMPLE Dataset\n# Arm: baseline\n" + record
    full, core, receipt = (tmp_path / name for name in ("full.yaml", "core.yaml", "receipt.yaml"))
    full.write_bytes(record)
    core.write_bytes(record)
    receipt.write_bytes(fixture["receipt"])
    registration = {**fixture["registration"], "run": {"arm": "baseline"}}
    limits = {**fixture["limits"], "worker_output_tokens": 64000,
              "integration_output_tokens": 32000, "max_input_tokens_per_call": 1000000,
              "context_limit_tokens": 1000000}
    result = builder.size_typed_audit_input(
        "EXAMPLE", limits, registration, sizing_record=builder.SizingRecord(full, core, receipt),
        context=fixture["context"], schema_snapshot=snapshot)
    assert result["stand_in"] is False
    assert any("registered context is missing explicitly supplied vocabulary" in warning
               and "would be refused" in warning for warning in result["warnings"])
    assert any("registered context vocabulary" in note for note in result["notes"])
    assert not any("historical sizing record has no current" in note for note in result["notes"])


def test_absent_vocabulary_slot_does_not_warn_or_refuse(typed_inputs):
    fixture, record, snapshot = vocabulary_case(typed_inputs, None)
    document = yaml.safe_load(record)
    del document["title"]
    record = yaml.safe_dump(document, sort_keys=False).encode()
    rendered = builder.render_typed_audit_inputs(
        "EXAMPLE", fixture["limits"], fixture["registration"], record=record, core=None,
        receipt=fixture["receipt"], context=fixture["context"], schema_snapshot=snapshot)
    assert rendered["owner_allowance_note"] is None
    assert rendered["owner_allowance_warning"] is None
    strict_packet(fixture, record, snapshot, fixture["context"])


def test_historical_schema_drift_is_not_reported_as_missing_vocabulary(typed_inputs):
    fixture = typed_inputs
    document = yaml.safe_load(fixture["record"])
    document["old_schema_field"] = {"text": "Historical structure."}
    record = yaml.safe_dump(document).encode()
    snapshot = capture_schema(fixture["schema_root"].absolute(), strict=True)
    rendered = builder.render_typed_audit_inputs(
        "EXAMPLE", fixture["limits"], fixture["registration"], record=record, core=None,
        receipt=fixture["receipt"], context=fixture["context"], schema_snapshot=snapshot)
    assert "historical sizing record has no current typed owner traversal" in rendered["owner_allowance_note"]
    assert "undeclared slot" in rendered["owner_allowance_note"]
    assert rendered["owner_allowance_warning"] is None
    with pytest.raises(ValueError, match="undeclared slot"):
        strict_packet(fixture, record, snapshot, fixture["context"])
