"""BC1 own-record sizing/roster regressions; no provider (2026-10-27)."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from tests.test_bc1_context import fixture as context_fixture
from data_sheets_schema import bc1_registration as reg, bc1_selection as selected
from scripts import build_api_registrations as builder


@pytest.fixture
def sizing_fixture(context_fixture, tmp_path):
    selection, inputs = context_fixture
    pins = selection["inputs"]
    for name, key in (("bundle", "bundle"), ("chunk_manifest", "manifest"), ("context", "context")):
        path = tmp_path / (name + ".json")
        path.write_bytes(inputs[key])
        pins[name] = reg._pin(path, inputs[key])
    pins["source_manifest"] = None
    pins["core_schema"] = deepcopy(pins["full_schema"])
    pins["project"] = "KIDS_FIRST"
    paths = {}
    for key in ("full", "core", "receipt"):
        paths[key] = tmp_path / (key + ".yaml")
        content = inputs["receipt"] if key == "receipt" else inputs["record"]
        if key != "receipt":
            content = b"# D4D Datasheet for KIDS_FIRST Dataset\n# Arm: de novo\n" + content
        paths[key].write_bytes(content)
    paths["receipt_result"] = tmp_path / "receipt-result.json"
    paths["receipt_result"].write_bytes(reg._raw({
        "receipt_after_sha256": hashlib.sha256(inputs["receipt"]).hexdigest(),
        "input_identity": {"fixture": "saved receipt outcome"}, "registration": {},
        "unsupported_audit_candidates": [{"reason": "quotes \\\" and unicode λ"}]}))
    limits = {"max_paths": 2, "max_inventory_bytes": 8192, "max_workers": 8,
              "worker_output_tokens": 64000, "omission_output_tokens": 32000,
              "integration_output_tokens": 64000, "max_request_bytes": 32000000,
              "max_input_tokens_per_call": 2000000, "context_limit_tokens": 2000000,
              "context_limit_basis": "offline test", "aggregate_input_tokens": 40000000}
    counts = selected.allowances(8, 2, omission_output_tokens=32000)
    limits.update({k: counts[k] for k in ("max_calls", "aggregate_output_tokens")})
    registration = {"format": "shared_generation_registration_v1", "registration_id": "offline-bc1",
        "registration_path": str(tmp_path / "registration.json"),
        "run": {"project": "KIDS_FIRST", "arm": "de novo", "method": "API", "label": "offline"},
        "selection": {"condition": "generic_v10"}, "inputs": pins,
        "runtime": {"model": "offline-fixture", "thinking": None, "temperature": None, "effort": None},
        "bounded_carry": selected.registration_block(fan_in=2), "audit_limits": limits}
    return registration, SimpleNamespace(**paths), inputs


def test_same_production_planner_and_wire_sizes_count_every_group_and_final(sizing_fixture):
    registration, files, inputs = sizing_fixture
    before = {name: Path(getattr(files, name)).read_bytes() for name in ("full", "core", "receipt")}
    result = reg.size_inputs(registration, sizing_record=files,
        context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])
    assert result["plan_workers"] > 1
    calls = result["plan_workers"] + 1 + len(result["groups"]) + 1
    for totals in result["own_plan_scenarios"].values():
        assert totals["calls"] == calls
        assert totals["wire_bytes"] > 0
        assert totals["output_token_reservations"] == 64000 * (calls - 1) + 32000
    assert result["own_plan_scenarios"]["visible_cap_ascii_scenario"]["wire_bytes"] > result["own_plan_scenarios"]["empty_future_floor"]["wire_bytes"]
    assert result["expected_visible_bytes"] is None
    assert result["actual_provider_token_counts"] is None
    assert result["admission"] == "UNVERIFIED_UNTIL_ACTUAL_REQUEST_COUNT"
    for row in result["rows"]:
        assert len(row["wire_sha256"]) == 64
        assert row["actual_count_tokens"] is None
    assert any(row["stage"].get("stage_id") == "final" for row in result["rows"])
    reg.check_sizing_record(registration, result)
    truncated = deepcopy(result)
    truncated["rows"] = [r for r in truncated["rows"] if r["stage"].get("stage_id") != "final"]
    with pytest.raises(ValueError, match="group/final requests are incomplete"):
        reg.check_sizing_record(registration, truncated)
    files.receipt.write_bytes(before["receipt"] + b"\n")
    with pytest.raises(ValueError, match="source bytes changed"):
        reg.check_sizing_record(registration, result)
    files.receipt.write_bytes(before["receipt"])
    assert {name: Path(getattr(files, name)).read_bytes() for name in before} == before


def test_own_project_record_required_and_source_changed_sidecar_refuses(sizing_fixture):
    registration, files, inputs = sizing_fixture
    registration["run"]["project"] = "CHORUS"
    with pytest.raises(ValueError, match="actual full record"):
        reg.size_inputs(registration, sizing_record=files, context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])
    result = reg.size_inputs(registration, sizing_record=files, context_raw=inputs["context"],
        schema_snapshot=inputs["schema_snapshot"], exploratory_stand_in=True)
    assert result["exploratory_stand_in"] is True
    with pytest.raises(ValueError, match="actual project/arm sizing"):
        reg.check_sizing_record(registration, result)


@pytest.mark.parametrize("fan,workers", [(1, 3), (2, 3), (2, 32)])
def test_registration_allowances_include_all_groups_and_separate_final(fan, workers):
    limits = builder.resolve_audit_limits("KIDS_FIRST", overrides={"max_paths": 80,
        "max_inventory_bytes": 12288, "max_workers": workers, "aggregate_input_tokens": 50000000},
        bounded_carry_version=1, bc1_fan_in=fan)
    groups = (workers + fan - 1) // fan
    assert limits["max_calls"] == workers + 1 + groups + 1
    assert limits["aggregate_output_tokens"] == (workers + groups + 1) * 64000 + 32000
    assert limits["integration_output_tokens"] == 64000


def test_legacy_profile_is_preserved_but_cannot_waive_bc1_sizing(tmp_path, monkeypatch):
    old = builder.resolve_audit_limits("CHORUS", "chorus")
    assert old["max_calls"] == 6 and old["integration_output_tokens"] == 32000
    with pytest.raises(ValueError, match="actual sizing record"):
        builder.prepare_registration("CHORUS", "offline", registration_path=tmp_path / "r.json",
                                     partition="chorus", bounded_carry_version=1)
    monkeypatch.delattr(builder.sg, "BC1_HOOK_VERSION", raising=False)
    with pytest.raises(ValueError, match="hook is not installed"):
        builder.prepare_registration("CHORUS", "offline", registration_path=tmp_path / "r.json",
            partition="chorus", bounded_carry_version=1, sizing_record=tmp_path)
    assert not (tmp_path / "r.json").exists()
    assert set(reg.PROJECTS) == {"CHORUS", "AI_READI", "CM4AI", "VOICE", "VOICE_PEDIATRIC", "KIDS_FIRST"}


def test_neutral_context_cannot_be_synthesized_for_bc1(tmp_path):
    with pytest.raises(ValueError, match="no draft vocabulary injection"):
        builder.prepare_registration("KIDS_FIRST", "offline", registration_path=tmp_path / "r.json",
            bounded_carry_version=1, sizing_record=tmp_path, synthesize_draft_context=True)


def test_requested_small_actual_wire_byte_limit_is_enforced(sizing_fixture):
    registration, files, inputs = sizing_fixture
    registration["audit_limits"]["max_request_bytes"] = 100
    with pytest.raises(ValueError, match="request|bound|wire"):
        reg.size_inputs(registration, sizing_record=files, context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])


@pytest.mark.parametrize("project", reg.PROJECTS)
def test_every_project_uses_its_own_header_without_inferred_study_profile(sizing_fixture, project):
    registration, files, inputs = sizing_fixture
    registration["run"]["project"] = registration["inputs"]["project"] = project
    files.full.write_bytes((f"# D4D Datasheet for {project} Dataset\n# Arm: de novo\nname: Example\n").encode())
    files.core.write_bytes((f"# D4D Core Datasheet for {project} Dataset\n# Arm: de novo\nname: Example\n").encode())
    result = reg.size_inputs(registration, sizing_record=files,
        context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])
    assert result["project"] == project and result["own_project_and_arm_record"]
    assert result["captured_inputs"]["profile"]["name"] == "neutral"
    assert result["own_plan_scenarios"]["empty_future_floor"]["calls"] == 4
    assert result["downstream_projection"]["bytes"] is None


@pytest.mark.parametrize("limit,value,message", [
    ("max_input_tokens_per_call", 100, "over per-call room"),
    ("context_limit_tokens", 65000, "over per-call room"),
    ("aggregate_input_tokens", 3, "over allowance"),
])
def test_fit_gate_recomputes_and_refuses_before_builder_writes(sizing_fixture, monkeypatch, limit, value, message):
    registration, files, inputs = sizing_fixture
    registration["audit_limits"][limit] = value
    result = reg.size_inputs(registration, sizing_record=files,
        context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])
    with pytest.raises(ValueError, match=message):
        reg.check_sizing_record(registration, result)
    # Keep the real builder's prepare -> validate -> write ordering. Only its
    # expensive byte measurement is supplied by this already rendered fixture.
    def measured(candidate, **kwargs):
        result["registration_sha256"] = hashlib.sha256(reg._raw(candidate)).hexdigest()
        result["project"] = candidate["run"]["project"]
        return result
    monkeypatch.setattr(reg, "size_inputs", measured)
    monkeypatch.setattr(builder, "_write_outputs", lambda *a: pytest.fail("wrote refused plan"))
    with pytest.raises(ValueError, match=message):
        builder.build_registration("CHORUS", "offline", partition="chorus", bounded_carry_version=1,
            audit_limits={"max_workers": 8, "max_input_tokens_per_call": 2000000,
                          "context_limit_tokens": 2000000, limit: value},
            sizing_record=builder.SizingRecord(files.full, files.core, files.receipt, files.receipt_result),
            registration_path=files.full.parent / "refused.json")
    assert not (files.full.parent / "refused.json").exists()


def test_real_carry_escaping_calibration_and_determinism(sizing_fixture):
    registration, files, inputs = sizing_fixture
    options = dict(sizing_record=files, context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])
    first = reg.size_inputs(registration, **options)
    assert reg._raw(first) == reg._raw(reg.size_inputs(registration, **options))
    assert first["calibration"] == registration["bounded_carry"]["contract"]["sizing_calibration"]
    assert first["receipt_completion_carry"]["actual"] is True
    rows = first["rows"]
    for bound in (r for r in rows if r["scenario"] == "visible_cap_escaped_bound"):
        ascii_row = next(r for r in rows if r["stage"] == bound["stage"] and r["scenario"] == "visible_cap_ascii_scenario")
        assert bound["wire_bytes"] > ascii_row["wire_bytes"]
    forged = deepcopy(first)
    forged["rows"][0]["estimated_input_tokens"] = 0
    with pytest.raises(ValueError, match="calibrated wire bytes"):
        reg.check_sizing_record(registration, forged)
    files.receipt_result.unlink()
    with pytest.raises(ValueError, match="saved receipt-completion result"):
        reg.size_inputs(registration, **options)


def test_fit_gate_accepts_exact_aggregate_and_input_boundaries(sizing_fixture):
    registration, files, inputs = sizing_fixture
    options = dict(sizing_record=files, context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])
    result = reg.size_inputs(registration, **options)
    largest = max(row['estimated_input_tokens'] for row in result['rows'] if row['gated'])
    total = max(result['own_plan_scenarios'][name]['estimated_input_tokens'] for name in reg.GATED_SCENARIOS)
    registration['audit_limits'].update(max_input_tokens_per_call=largest, aggregate_input_tokens=total)
    result = reg.size_inputs(registration, **options)
    reg.check_sizing_record(registration, result)
    assert any(not r['estimated_context_fits'] for r in result['rows'] if not r['gated'])
    assert result['own_plan_scenarios']['visible_cap_escaped_bound']['estimated_input_tokens'] > total


def test_d62_split_applies_to_every_call_and_measured_escaping_only_to_future(sizing_fixture):
    registration, files, inputs = sizing_fixture
    result = reg.size_inputs(registration, sizing_record=files,
        context_raw=inputs['context'], schema_snapshot=inputs['schema_snapshot'])
    for row in result['rows']:
        if row['scenario'] in ('captured_record', reg.FLOOR):
            assert row['estimated_input_tokens'] == math.ceil(row['wire_bytes'] / 2.48)
            assert row['future_wire_bytes'] == 0
        if row['scenario'] == reg.CAPS:
            floor = next(r for r in result['rows'] if r['stage'] == row['stage'] and r['scenario'] == reg.FLOOR)
            assert row['request_bytes'] == floor['wire_bytes']
            assert row['planning_future_wire_bytes'] == math.ceil(row['future_wire_bytes'] * 1.25)
            assert row['estimated_input_tokens'] == math.ceil(
                floor['wire_bytes'] / 2.48 + math.ceil(row['future_wire_bytes'] * 1.25) / 1.75)
    forged = deepcopy(result)
    forged['calibration']['future_response_escape_factor'] = 1.0
    with pytest.raises(ValueError, match='component calibration'):
        reg.check_sizing_record(registration, forged)


@pytest.fixture
def completed_chorus(tmp_path):
    source = Path(__file__).parent / 'fixtures/audit_batches/chorus_v10_2026-10-22a'
    intermediate = tmp_path / 'completed/intermediate'
    intermediate.mkdir(parents=True)
    for name in ('full', 'core'):
        (intermediate / f'CHORUS_{name}.yaml').write_bytes((source / f'CHORUS_{name}.yaml').read_bytes())
    effective = (source / 'CHORUS_coverage_receipt.yaml').read_bytes()
    (intermediate / 'CHORUS_coverage_receipt.yaml').write_text('# earlier receipt\nchunks: []\n')
    (intermediate.parent / 'CHORUS_coverage_receipt.yaml').write_bytes(effective)
    (intermediate / 'CHORUS_receipt_completion_result.json').write_bytes(reg._raw({
        'receipt_yaml': effective.decode(), 'receipt_after_sha256': hashlib.sha256(effective).hexdigest(),
        'input_identity': {}, 'registration': {}, 'unsupported_audit_candidates': []}))
    return intermediate


def test_completed_run_cli_sizing_uses_exact_effective_receipt_and_check_revalidates(completed_chorus, tmp_path):
    output = tmp_path / 'registrations'
    args = ['-p', 'CHORUS', '-l', 'completed', '--partition', 'chorus',
            '--bounded-carry-version', '1', '--aggregate-input-tokens', '4500000',
            '--sizing-record', f'CHORUS={completed_chorus}', '-o', str(output)]
    result = CliRunner().invoke(builder.cli, args)
    assert result.exit_code == 0, result.output
    path = output / 'registration_chorus_completed.json'
    assert path.stat().st_size > 0
    record = builder.check_registration_sizing(path, path.read_bytes())
    assert record is not None
    files = builder.SizingRecord.in_directory(completed_chorus, 'CHORUS', effective_receipt=True)
    assert files.receipt.parent == completed_chorus.parent
    # v0 keeps its prior selection, including when a completion result exists.
    assert builder.SizingRecord.in_directory(completed_chorus, 'CHORUS').receipt.parent == completed_chorus
    files.receipt.write_bytes(files.receipt.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='source bytes changed'):
        builder.check_registration_sizing(path, path.read_bytes())
    with pytest.raises(ValueError, match='exact effective receipt'):
        builder.SizingRecord.in_directory(completed_chorus, 'CHORUS', effective_receipt=True)


@pytest.mark.parametrize('allowance,ceiling,message', [
    (4000000, 1000000, 'over allowance'),
    (4500000, 600000, 'over per-call room'),
])
def test_completed_run_cli_and_library_refuse_before_any_write(completed_chorus, tmp_path, allowance, ceiling, message):
    output = tmp_path / 'refused'
    args = ['-p', 'CHORUS', '-l', 'refused', '--partition', 'chorus',
            '--bounded-carry-version', '1', '--aggregate-input-tokens', str(allowance),
            '--max-input-tokens-per-call', str(ceiling),
            '--sizing-record', f'CHORUS={completed_chorus}', '-o', str(output)]
    result = CliRunner().invoke(builder.cli, args)
    assert result.exit_code != 0 and message in result.output, result.output
    assert not output.exists()
    with pytest.raises(ValueError, match=message):
        builder.build_registration('CHORUS', 'refused', partition='chorus', bounded_carry_version=1,
            audit_limits={'aggregate_input_tokens': allowance, 'max_input_tokens_per_call': ceiling},
            sizing_record=completed_chorus, registration_path=output / 'registration.json')
    assert not output.exists()


def test_completed_receipt_text_cannot_disagree_with_its_hash(completed_chorus):
    path = completed_chorus / 'CHORUS_receipt_completion_result.json'
    outcome = json.loads(path.read_bytes())
    outcome['receipt_yaml'] += '\n'
    path.write_bytes(reg._raw(outcome))
    with pytest.raises(ValueError, match='invalid effective receipt bytes'):
        builder.SizingRecord.in_directory(completed_chorus, 'CHORUS', effective_receipt=True)


@pytest.mark.parametrize('value', ['ordinary text', '"' * 200, '\\' * 200,
                                  '\x00\t\r\n' * 50, 'λ 漢字 😀' * 50])
def test_future_json_escaped_envelope_bounds_actual_serialized_text(value):
    # Valid candidate JSON is embedded in the stage JSON, then in provider JSON.
    candidate = reg._raw({'strings': [value], 'body': {'literal': value}}).decode()
    bound = '\\' * len(candidate.encode())
    def wire(text):
        return reg._raw({'text': reg._raw({'concern_packet': text}).decode()})
    assert len(wire(candidate)) <= len(wire(bound))
    if value == '\\' * 200:
        assert len(wire(candidate)) > len(wire('x' * len(candidate.encode())))
