"""Typed-audit input is sized before anything is written or billed (#5155, A17 review F1/F3).

CHORUS_SIZING holds the 2026-10-22a run's own phase-1 record, core and
effective receipt; the counts below are that run's endpoint counts.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from click.testing import CliRunner
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_api_registrations import (
    DEFAULT_AUDIT_LIMITS,
    PARTITION_PROFILES,
    SIZING_EXPECTED_INPUT_TOKENS_PER_RESPONSE_TOKEN,
    SIZING_INPUT_TOKENS_PER_RESPONSE_TOKEN,
    SIZING_OMISSION_RESPONSE_CAP_FRACTION,
    SIZING_RECORD_FORMAT,
    SIZING_WORKER_RESPONSE_CAP_FRACTION,
    SizingRecord,
    build_registration,
    check_registration_sizing,
    cli,
    parse_project_limits,
    parse_sizing_records,
    prepare_registration,
    profile_covered,
    profile_sized,
    render_typed_audit_inputs,
    resolve_audit_limits,
    sizing_path,
)
from data_sheets_schema import audit_batches as b, shared_generation as sg, typed_audit as ta
from data_sheets_schema.chunking import manifest_from_bytes
from data_sheets_schema.schema_snapshot import capture_schema

CHORUS_SIZING = ROOT / "tests" / "fixtures" / "audit_batches" / "chorus_v10_2026-10-22a"
RUNS = ROOT / "data" / "d4d_concatenated" / "claudecode_api_core"
AI_READI_SIZING = RUNS / "2026-09-04g_claude-opus-5-api-generic-v8_rep2" / "intermediate"
BOUNDS = {"max_paths": 80, "max_inventory_bytes": 12288}
# Bounds whose integration call fits today's protocol for AI_READI (two workers of up to 96 KB).
AI_READI_FITS = {"max_paths": 512, "max_inventory_bytes": 98304, "max_workers": 2}
# 2026-10-22a's typed-audit stages, counted by the endpoint before admission, and their sum.
MEASURED = {"workers": (138859, 139001, 138283), "omission": 98527, "integration": 316914, "aggregate": 831584}
V10_RUN = os.environ.get("D4D_CHORUS_V10_TYPED_RUN")


def prepare(project, tmp_path, **options):
    return prepare_registration(project, "sizing_test", registration_path=tmp_path / "registration.json", **options)


def test_chorus_profile_limits_are_the_registered_ones():
    assert resolve_audit_limits("CHORUS", "chorus") == {
        "max_request_bytes": 32000000, "max_input_tokens_per_call": 1000000, "worker_output_tokens": 64000,
        "omission_output_tokens": 32000, "integration_output_tokens": 32000, "aggregate_input_tokens": 4000000,
        "context_limit_tokens": 1000000,
        "context_limit_basis": "Route context window 1,000,000 tokens; sized for largest bundle",
        "max_paths": 80, "max_inventory_bytes": 12288, "max_workers": 4, "aggregate_output_tokens": 320000,
        "max_calls": 6}
    assert "aggregate_input_tokens" not in DEFAULT_AUDIT_LIMITS


def test_profile_covers_only_its_own_bounds_caps_and_larger_allowances():
    limits = resolve_audit_limits("CHORUS", "chorus")
    assert profile_sized("chorus", limits)
    assert profile_sized("chorus", {**limits, "aggregate_input_tokens": 5000000, "max_calls": 9})
    assert not profile_sized(None, limits)
    for change in ({"max_workers": 16}, {"max_paths": 81}, {"worker_output_tokens": 96000},
                   {"aggregate_input_tokens": 3999999}):
        assert not profile_sized("chorus", {**limits, **change}), change
    # Limits equal to a profile's are that profile's, named or not, for its own project and arm only.
    assert profile_covered("CHORUS", "baseline", limits)
    assert not profile_covered("CHORUS", "crate_only", limits) and not profile_covered("AI_READI", "baseline", limits)


def test_an_allowance_no_profile_covers_needs_a_sizing_record(tmp_path):
    with pytest.raises(ValueError, match="aggregate_input_tokens has no default"):
        prepare("AI_READI", tmp_path, audit_limits={**BOUNDS, "max_workers": 16})
    with pytest.raises(ValueError, match="needs a sizing record"):
        prepare("AI_READI", tmp_path, audit_limits={**BOUNDS, "max_workers": 16, "aggregate_input_tokens": 99000000})
    # Changing a profile's bounds leaves its allowance behind.
    with pytest.raises(ValueError, match="needs a sizing record"):
        prepare("CHORUS", tmp_path, partition="chorus", audit_limits={"max_workers": 16})
    with pytest.raises(FileNotFoundError, match="sizing record for AI_READI is incomplete"):
        prepare("AI_READI", tmp_path, audit_limits={**BOUNDS, "max_workers": 16, "aggregate_input_tokens": 99000000},
                sizing_record=tmp_path)
    assert not list(tmp_path.iterdir())


def test_chorus_sizing_covers_its_canary_and_the_profile_allowance(tmp_path):
    # The run's own plan: three workers.
    _, _, three = prepare("CHORUS", tmp_path, audit_limits={**BOUNDS, "max_workers": 3, "aggregate_input_tokens": 4000000},
                          sizing_record=CHORUS_SIZING)
    assert three["plan_workers"] == 3
    assert three["worker_input_tokens"] >= max(MEASURED["workers"])
    assert three["omission_input_tokens"] >= MEASURED["omission"]
    assert three["integration_input_tokens"] >= MEASURED["integration"]
    assert three["aggregate_input_tokens"] >= MEASURED["aggregate"]
    # The profile's largest plan, four workers, fits its 4,000,000 with room. Every call fits its
    # window as expected; the worst case for integration does not, and is warned and recorded.
    _, _, profile = prepare("CHORUS", tmp_path, partition="chorus", sizing_record=CHORUS_SIZING)
    assert profile["max_workers"] == 4
    assert profile["aggregate_input_tokens"] == (4 * profile["worker_input_tokens"] + profile["omission_input_tokens"]
                                                 + profile["integration_worst_input_tokens"])
    assert MEASURED["aggregate"] < profile["aggregate_input_tokens"] < PARTITION_PROFILES["chorus"]["limits"]["aggregate_input_tokens"]
    assert profile["admissible_input_tokens"] == {"worker": 936000, "omission": 968000, "integration": 968000}
    assert all(profile[f"{stage}_input_tokens"] <= room for stage, room in profile["admissible_input_tokens"].items())
    assert profile["integration_worst_input_tokens"] > 968000
    assert len(profile["warnings"]) == 1 and "at worst, 4 worker responses" in profile["warnings"][0]
    assert profile["sizing_record"]["full"]["sha256"] == hashlib.sha256((CHORUS_SIZING / "CHORUS_full.yaml").read_bytes()).hexdigest()
    assert profile["stand_in"] is False and "53,204 of 64,000" in profile["notes"][0]


def test_the_response_constants_are_pinned_to_10_22a(tmp_path):
    """F7: the constants that decide whether a project fits are calibrated, not free."""
    assert SIZING_INPUT_TOKENS_PER_RESPONSE_TOKEN == 3.5
    assert SIZING_EXPECTED_INPUT_TOKENS_PER_RESPONSE_TOKEN == 1.2
    # 10-22a's usage ledger: its typed workers used 50,130, 43,348 and 14,032 of 64,000, its omission 23,997 of 32,000.
    workers, omission = (50130 / 64000 + 43348 / 64000 + 14032 / 64000) / 3, 23997 / 32000
    assert 0 <= SIZING_WORKER_RESPONSE_CAP_FRACTION - workers < 0.001
    assert 0 <= SIZING_OMISSION_RESPONSE_CAP_FRACTION - omission < 0.001
    _, _, three = prepare("CHORUS", tmp_path, audit_limits={**BOUNDS, "max_workers": 3, "aggregate_input_tokens": 4000000},
                          sizing_record=CHORUS_SIZING)
    used = 3 * 0.56 * 64000 + 0.75 * 32000
    assert three["integration_response_input_tokens"] == math.ceil(1.2 * used)
    assert three["integration_worst_response_input_tokens"] == 3.5 * (3 * 64000 + 32000)
    # The current estimate still covers the historical count. A14's larger
    # schema context changes the base, so that old total can no longer
    # distinguish response factors; the calibrated factors and formulas are
    # checked directly above.
    assert three["integration_input_tokens"] >= MEASURED["integration"]


@pytest.mark.parametrize("project,run", [("AI_READI", "2026-09-04g_claude-opus-5-api-generic-v8_rep2"),
                                         ("VOICE", "2026-09-04f_claude-opus-5-api-generic-v8_rep3")])
def test_large_projects_are_refused_when_their_expected_integration_cannot_fit(tmp_path, project, run):
    limits = {**BOUNDS, "max_workers": 16, "aggregate_input_tokens": 99000000}
    with pytest.raises(ValueError, match=f"^{project}: the typed-audit integration call sized on .*{project}_full.yaml "
                                         r"needs [\d,]+ input tokens for its own plan \(1[15] worker responses") as refused:
        prepare(project, tmp_path, audit_limits=limits, sizing_record=RUNS / run / "intermediate")
    assert "over the 968,000 it may take" in str(refused.value)
    assert "after billing every earlier stage" in str(refused.value)
    assert not list(tmp_path.iterdir())


def test_a_large_project_whose_expected_integration_fits_is_built_with_its_worst_case_warned(tmp_path):
    # The corrected S7 omission estimate raises this historical fixture above
    # its former 12M aggregate allowance. Keep this a positive build case.
    limits = {**BOUNDS, "max_workers": 16, "aggregate_input_tokens": 13000000}
    _, outputs, sizing = prepare("CM4AI", tmp_path, audit_limits=limits,
                                 sizing_record=RUNS / "2026-09-04g_claude-opus-5-api-generic-v8_rep1" / "intermediate")
    assert sizing["plan_workers"] == 8 and sizing["integration_input_tokens"] <= 968000
    assert 12000000 < sizing["aggregate_input_tokens"] <= limits["aggregate_input_tokens"]
    assert sizing["integration_worst_input_tokens"] > 968000
    recorded = json.loads(outputs[-1][1])["sizing"]
    assert recorded["warnings"] == sizing["warnings"] and "at worst, 16 worker responses" in recorded["warnings"][0]
    assert recorded["notes"] == sizing["notes"]
    assert any("no current typed owner traversal" in note for note in recorded["notes"])


def test_a_worker_call_that_cannot_fit_is_refused_too(tmp_path):
    limits = {**BOUNDS, "max_workers": 4, "aggregate_input_tokens": 4000000, "context_limit_tokens": 200000}
    with pytest.raises(ValueError, match=r"CHORUS: the typed-audit worker call .* over the 136,000 it may take"):
        prepare("CHORUS", tmp_path, audit_limits=limits, sizing_record=CHORUS_SIZING)


def test_large_project_allowance_is_refused_below_its_sizing_before_anything_is_written(tmp_path):
    limits = {**AI_READI_FITS, "aggregate_input_tokens": 2000000}
    with pytest.raises(ValueError, match="aggregate_input_tokens 2,000,000 is below the typed-audit input") as refused:
        prepare("AI_READI", tmp_path, audit_limits=limits, sizing_record=AI_READI_SIZING)
    assert "refused midway, after its first stages are billed" in str(refused.value)
    reg, outputs, sizing = prepare("AI_READI", tmp_path, audit_limits={**limits, "aggregate_input_tokens": 4000000},
                                   sizing_record=AI_READI_SIZING)
    assert reg["audit_limits"]["max_workers"] == 2 and reg["audit_limits"]["max_calls"] == 4
    assert sizing["plan_workers"] == 2 and sizing["max_workers"] == 2
    assert 2000000 < sizing["aggregate_input_tokens"] <= 4000000
    assert sizing["aggregate_input_tokens"] == (2 * sizing["worker_input_tokens"] + sizing["omission_input_tokens"]
                                                + sizing["integration_worst_input_tokens"])
    registration = (tmp_path / "registration.json").resolve()
    assert [path for path, _ in outputs] == [registration, sizing_path(registration)]
    assert not list(tmp_path.iterdir())


def test_a_sizing_record_is_bound_to_its_project_and_arm(tmp_path):
    chorus = SizingRecord.in_directory(CHORUS_SIZING, "CHORUS")
    limits = {**AI_READI_FITS, "aggregate_input_tokens": 4000000}
    with pytest.raises(ValueError, match="is not a AI_READI record of this arm: .*D4D Datasheet for CHORUS Dataset"):
        prepare("AI_READI", tmp_path, audit_limits=limits, sizing_record=chorus)
    with pytest.raises(ValueError, match="is not a CHORUS record of this arm: .*'# Arm: BASELINE .*CRATE-ONLY"):
        prepare("CHORUS", tmp_path, arm="crate_only", sizing_record=chorus,
                audit_limits={**BOUNDS, "max_workers": 4, "aggregate_input_tokens": 4000000})
    # A stand-in is sized only when asked for, and the record says so.
    _, outputs, sizing = prepare("AI_READI", tmp_path, audit_limits=limits, sizing_record=chorus, sizing_stand_in=True)
    assert sizing["stand_in"] is True
    assert json.loads(dict(outputs)[sizing_path((tmp_path / "registration.json").resolve())])["sizing"]["stand_in"] is True
    _, _, own = prepare("AI_READI", tmp_path, audit_limits=limits, sizing_record=AI_READI_SIZING, sizing_stand_in=True)
    assert own["stand_in"] is False


def test_the_sizing_is_recorded_beside_the_registration_and_checked_against_its_bytes(tmp_path):
    path = tmp_path / "registration.json"
    reg = build_registration("CHORUS", "sizing_test", registration_path=path, sizing_record=CHORUS_SIZING,
                             audit_limits={**BOUNDS, "max_workers": 3, "aggregate_input_tokens": 4000000})
    raw = path.read_bytes()
    record = json.loads(sizing_path(path).read_bytes())
    assert record["format"] == SIZING_RECORD_FORMAT
    assert record["registration_sha256"] == hashlib.sha256(raw).hexdigest() == hashlib.sha256(sg.canonical(reg)).hexdigest()
    assert record["sizing"]["aggregate_input_tokens"] <= reg["audit_limits"]["aggregate_input_tokens"]
    assert check_registration_sizing(path, raw) == record
    # Changed registration bytes no longer match the record; without one, an unprofiled allowance fails.
    with pytest.raises(ValueError, match="is not the sizing record of these registration bytes"):
        check_registration_sizing(path, raw.replace(b'"aggregate_input_tokens":4000000', b'"aggregate_input_tokens":4000001'))
    sizing_path(path).unlink()
    with pytest.raises(ValueError, match="no partition profile covers its aggregate_input_tokens"):
        check_registration_sizing(path, raw)
    # A profile registration needs none.
    profiled = tmp_path / "profiled.json"
    build_registration("CHORUS", "sizing_test", registration_path=profiled, partition="chorus")
    assert check_registration_sizing(profiled, profiled.read_bytes()) is None
    assert not sizing_path(profiled).exists()


def test_a_sizing_record_the_bounds_cannot_plan_is_refused(tmp_path):
    # AI_READI's v8 record needs 15 workers at these bounds.
    with pytest.raises(ValueError, match=r"does not plan under these bounds \(worker_count_bound\)"):
        prepare("AI_READI", tmp_path, audit_limits={**BOUNDS, "max_workers": 8, "aggregate_input_tokens": 99000000},
                sizing_record=AI_READI_SIZING)


def test_project_limits_and_sizing_records_parse_strictly():
    assert parse_project_limits(["AI_READI:max_paths=80,max-workers=16, aggregate_input_tokens=15000000",
                                 "CHORUS:partition=chorus", "VOICE:partition=none,max_workers=12"]) == {
        "AI_READI": {"max_paths": 80, "max_workers": 16, "aggregate_input_tokens": 15000000},
        "CHORUS": {"partition": "chorus"}, "VOICE": {"partition": None, "max_workers": 12}}
    for bad in (["AI_READI"], ["AI_READI:"], ["AI_READI:max_paths"], ["AI_READI:max_paths=x"],
                ["AI_READI:context_limit_basis=x"], ["AI_READI:max_paths=1,max_paths=2"], ["A:max_paths=1", "A:max_workers=2"]):
        with pytest.raises(ValueError):
            parse_project_limits(bad)
    assert parse_sizing_records(["AI_READI=/tmp/x"]) == {"AI_READI": Path("/tmp/x")}
    for bad in (["AI_READI"], ["=/tmp/x"], ["A=/x", "A=/y"]):
        with pytest.raises(ValueError):
            parse_sizing_records(bad)


def test_cli_builds_each_project_with_its_own_limits_or_writes_nothing(tmp_path):
    out = tmp_path / "regs"
    args = ["-p", "CHORUS,AI_READI", "-l", "per_project", "-o", str(out), "--project-limits", "CHORUS:partition=chorus",
            "--sizing-record", f"AI_READI={AI_READI_SIZING}"]
    for bounds, reason in (("max_paths=80,max_inventory_bytes=12288,max_workers=16,aggregate_input_tokens=99000000",
                            "the typed-audit integration call"),
                           ("max_paths=512,max_inventory_bytes=98304,max_workers=2,aggregate_input_tokens=2000000",
                            "is below the typed-audit input")):
        refused = CliRunner().invoke(cli, args + ["--project-limits", f"AI_READI:{bounds}"])
        assert refused.exit_code != 0 and reason in refused.output
        assert not out.exists() or not any(out.iterdir())  # not even the CHORUS registration built first
    built = CliRunner().invoke(cli, args + ["--project-limits", "AI_READI:max_paths=512,max_inventory_bytes=98304,"
                                                              "max_workers=2,aggregate_input_tokens=4000000"])
    assert built.exit_code == 0, built.output
    regs = {p: json.loads((out / f"registration_{p.lower()}_per_project.json").read_text()) for p in ("CHORUS", "AI_READI")}
    assert regs["CHORUS"]["audit_limits"] == resolve_audit_limits("CHORUS", "chorus")
    assert (regs["AI_READI"]["audit_limits"]["max_workers"], regs["AI_READI"]["audit_limits"]["aggregate_input_tokens"]) == (2, 4000000)
    assert not sizing_path(out / "registration_chorus_per_project.json").exists()
    assert "sizing record registration_ai_readi_per_project.sizing.json sha256=" in built.output
    assert "note: worker_output_tokens is calibrated on six CHORUS workers" in built.output
    assert "warning: at worst, 2 worker responses and the omission's at their caps" in built.output
    check = CliRunner().invoke(cli, ["-p", "CHORUS,AI_READI", "-l", "per_project", "-o", str(out), "--check"])
    assert check.exit_code == 0, check.output
    assert "(sized: registration_ai_readi_per_project.sizing.json)" in check.output
    stray = CliRunner().invoke(cli, args + ["--project-limits", "VOICE:partition=none"])
    assert stray.exit_code != 0 and "VOICE, which this build does not target" in stray.output


@pytest.fixture
def typed_inputs(tmp_path):
    root = tmp_path / "schema.yaml"
    root.write_text("id: https://example.test/typed\nname: typed\nimports: [child]\n")
    (tmp_path / "child.yaml").write_text("""id: https://example.test/child
name: child
prefixes: {linkml: 'https://w3id.org/linkml/'}
imports: [linkml:types]
default_range: string
classes:
  Creator:
    attributes:
      name: {}
      affiliation: {}
  Dataset:
    attributes:
      title: {}
      creators: {range: Creator, multivalued: true, inlined_as_list: true}
""")
    bundle = b"Preamble\nFILE: manual.txt\nPATH: manual.txt\nExample release provides a complete description.\nFILE: other.txt\nPATH: other.txt\nAdditional source.\n"
    manifest = manifest_from_bytes(bundle, "invented")
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": row["id"], "status": status} for row, status in zip(manifest["chunks"],
                                      ("nothing_relevant", "redundant_with", "duplicate_of"))]}
    context = {"format": "omission_context_v1", "root_class": "Dataset", "scopes": [
        {"owner": "", "referent": "Example", "release": "1", "scope": "This release only."}],
        "source_policy": {"priority": ["manual.txt", "other.txt"], "basis": "Invented fixture."}, "vocabulary": {}}
    record = yaml.safe_dump({"title": "Example", "creators": [
        {"name": f"Person {i}", "affiliation": f"Institute {i}"} for i in range(12)]}, sort_keys=False).encode()
    files = {"bundle": bundle, "manifest": b.canonical_bytes(manifest), "context": b.canonical_bytes(context)}
    for name, raw in files.items():
        (tmp_path / name).write_bytes(raw)
    registration = {"selection": sg.descriptor(), "inputs": {
        "bundle": sg.file_pin(tmp_path / "bundle"), "chunk_manifest": sg.file_pin(tmp_path / "manifest"),
        "source_manifest": None, "context": sg.file_pin(tmp_path / "context"),
        "profile": {"name": "neutral", "basis": "stated by the caller", "vocabulary": None}}}
    limits = {"max_paths": 6, "max_inventory_bytes": 12288, "max_workers": 8, "omission_output_tokens": 4000,
              "max_request_bytes": 32000000}
    return dict(schema_root=root, bundle=bundle, manifest=files["manifest"], receipt=b.canonical_bytes(receipt),
                context=files["context"], record=record, registration=registration, limits=limits)


def test_rendering_agrees_with_the_typed_packet(typed_inputs):
    """Sizing shares the sealed omission wire, with fixed-width worker digests."""
    t = typed_inputs
    snapshot = capture_schema(t["schema_root"].absolute(), strict=True)
    packet = ta.prepare(protocol="typed_audit_protocol_v1", original_full=t["record"], bundle=t["bundle"],
                        manifest=t["manifest"], receipt=t["receipt"], context=t["context"], schema_path=t["schema_root"],
                        schema_snapshot=snapshot, omission_wire=ta.SHARED_OMISSION_WIRE,
                        max_output_tokens=t["limits"]["omission_output_tokens"],
                        **{k: t["limits"][k] for k in ("max_paths", "max_inventory_bytes", "max_workers", "max_request_bytes")})
    rendered = render_typed_audit_inputs("EXAMPLE", t["limits"], t["registration"], record=t["record"], core=None,
                                         receipt=t["receipt"], context=t["context"], schema_snapshot=snapshot)
    assert rendered["shared_context"] == packet["requests"]["shared_context"]
    assert rendered["plan_workers"] == len(packet["plan"]["workers"]) == 5
    for mine, worker in zip(rendered["requests"]["workers"], packet["plan"]["workers"]):
        theirs = ta.worker_request(packet, worker["id"])
        stage, expected = json.loads(mine["payload"]["stage"]), json.loads(theirs["payload"]["stage"])
        assert stage == {**expected, "shared_context_sha256": stage["shared_context_sha256"]}
        assert len(sg.canonical(mine)) == len(sg.canonical(theirs))
    assert rendered["requests"]["omission"] == ta.omission_wire_request(packet)
    # Integration: the same shared context, contract and rows; responses are sized from the caps.
    integration = rendered["requests"]["integration"]["integration_request"]["payload"]
    assert integration["shared_context"] == packet["requests"]["shared_context"]
    assert integration["output_contract"] == packet["contracts"]["integration"]
    assert [row["path"] for row in integration["proposal_index"]["rows"]] == [r["path"] for r in packet["plan"]["inventory"]["values"]]


def test_historical_sizing_receipt_does_not_relax_execution_validation(typed_inputs):
    """An old receipt is an estimate input, never authority for a current packet."""
    t = typed_inputs
    snapshot = capture_schema(t["schema_root"].absolute(), strict=True)
    old = yaml.safe_load(t["receipt"])
    old["bundle_md5"] = "0" * 32
    receipt = yaml.safe_dump(old).encode()
    rendered = render_typed_audit_inputs("EXAMPLE", t["limits"], t["registration"], record=t["record"], core=None,
        receipt=receipt, context=t["context"], schema_snapshot=snapshot)
    payload = rendered["requests"]["omission"]["payload"]
    assert payload["receipt_yaml"] == receipt.decode()
    assert payload["input_sha256"]["receipt"] == hashlib.sha256(receipt).hexdigest()
    with pytest.raises(ValueError, match="receipt does not name the captured bundle"):
        ta.prepare(protocol="typed_audit_protocol_v1", original_full=t["record"], bundle=t["bundle"],
            manifest=t["manifest"], receipt=receipt, context=t["context"], schema_path=t["schema_root"],
            schema_snapshot=snapshot, omission_wire=ta.SHARED_OMISSION_WIRE,
            max_output_tokens=t["limits"]["omission_output_tokens"])


def test_historical_owner_allowance_does_not_relax_execution_validation(typed_inputs):
    t = typed_inputs
    snapshot = capture_schema(t["schema_root"].absolute(), strict=True)
    document = yaml.safe_load(t["record"])
    document["old_schema_field"] = {"text": "An older record shape."}
    record = yaml.safe_dump(document).encode()
    rendered = render_typed_audit_inputs("EXAMPLE", t["limits"], t["registration"], record=record, core=None,
        receipt=t["receipt"], context=t["context"], schema_snapshot=snapshot)
    assert "undeclared slot" in rendered["owner_allowance_note"]
    assert "not validation of an executable packet" in rendered["owner_allowance_note"]
    payload = rendered["requests"]["omission"]["payload"]
    assert payload["record_yaml"] == record.decode()
    assert len(payload["owner_classes"]["/old_schema_field"]) >= 32
    with pytest.raises(ValueError, match="undeclared slot"):
        ta.prepare(protocol="typed_audit_protocol_v1", original_full=record, bundle=t["bundle"],
            manifest=t["manifest"], receipt=t["receipt"], context=t["context"], schema_path=t["schema_root"],
            schema_snapshot=snapshot, omission_wire=ta.SHARED_OMISSION_WIRE,
            max_output_tokens=t["limits"]["omission_output_tokens"])


@pytest.mark.skipif(not V10_RUN, reason="set D4D_CHORUS_V10_TYPED_RUN to the 2026-10-22a intermediate directory")
def test_rendering_reproduces_the_chorus_v10_wire():
    """Historical lineage allows the explicit D35/A14 changes; current parity is mandatory elsewhere."""
    run = Path(V10_RUN)
    packet = json.loads((run / "CHORUS_typed_audit_packet.json").read_bytes())
    raw = {key: ta._unblob(value) for key, value in packet["inputs"].items()}
    wires = []
    for i in range(5):
        wire = json.loads((run / f"CHORUS_typed_audit_{i}_request.json").read_bytes())
        wires.append([part["text"] for message in wire["messages"] for part in message["content"]
                      if part.get("type") == "text"] + [wire["system"]])
    carry = wires[0][2]
    registration = json.loads(json.loads(carry[carry.index("{"):])["input_identity"]["shared_generation"]["registration"]["raw_json"])
    for pin in (registration["inputs"]["bundle"], registration["inputs"]["chunk_manifest"], registration["inputs"]["source_manifest"]):
        if not Path(pin["path"]).is_file() or hashlib.sha256(Path(pin["path"]).read_bytes()).hexdigest() != pin["sha256"]:
            pytest.skip(f"{pin['path']} no longer holds the bytes the run pinned")
    limits = {**registration["audit_limits"], "max_workers": len(packet["plan"]["workers"])}
    rendered = render_typed_audit_inputs("CHORUS", limits, registration, record=raw["original_full"],
                                         core=raw["original_core"], receipt=raw["receipt"], context=raw["context"],
                                         schema_snapshot=ta._snapshot(packet["schema_sources"]))
    actual = [sum(len(text.encode()) for text in parts) for parts in wires]
    allowance = rendered["carry_allowance_bytes"] - len(carry.encode())
    assert allowance >= 0
    # Since that run, one worker-contract sentence was reworded (D35); it occurs twice in each worker request.
    reworded = 2 * (len("Every removal's owning root (its top-level field, or its list entry when the plan splits that list) belongs")
                    - len("Every removal's top-level owner belongs"))
    # A14 restores schema descriptions and sends its sealed S7 omission wire.
    # Compare those declared changes explicitly, rather than treating v10 as
    # the current wire. test_wave6_a14_a17_sizing checks today's real formatter.
    schema_bytes = len(sg._schema_context(SimpleNamespace(full_schema=ta._snapshot(packet["schema_sources"])),
                                         raw["original_full"].decode()).encode())
    assert all(parts[3] == wires[0][3] for parts in wires[:3])
    assert rendered["worker_bytes"] - max(actual[:3]) == allowance + reworded + schema_bytes - len(wires[0][3].encode())
    old_inner = json.loads(wires[3][6].split("\n\n", 1)[1])
    old_binding = json.loads(wires[3][5].split("\n\n", 1)[1])
    binding_delta = (len(sg.canonical({**old_binding, "packet_inner_request_sha256": "0" * 64}))
                     - len(sg.canonical(old_binding)))
    inner_delta = len(sg.canonical(rendered["requests"]["omission"])) - len(sg.canonical(old_inner))
    assert rendered["omission_bytes"] - actual[3] == (allowance + inner_delta + binding_delta
                                                     + schema_bytes - len(wires[3][3].encode()))
    assert rendered["integration_base_bytes"] < actual[4]
    # The expected-response constants are this run's own usage ledger.
    ledger = json.loads(next(run.parent.glob("CHORUS_api_usage_*.json")).read_bytes())
    used = {phase: [row["output_tokens"] / row["max_tokens"] for row in ledger["rows"] if row.get("phase") == phase]
            for phase in ("typed_audit_worker", "typed_audit_omission")}
    assert len(used["typed_audit_worker"]) == 3 and len(used["typed_audit_omission"]) == 1
    assert 0 <= SIZING_WORKER_RESPONSE_CAP_FRACTION - sum(used["typed_audit_worker"]) / 3 < 0.001
    assert 0 <= SIZING_OMISSION_RESPONSE_CAP_FRACTION - used["typed_audit_omission"][0] < 0.001
