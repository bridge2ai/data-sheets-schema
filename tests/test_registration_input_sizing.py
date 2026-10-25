"""The typed-audit aggregate input allowance is sized before anything is built or billed (#5155).

CHORUS_SIZING holds the 2026-10-22a run's own phase-1 record, core and
effective receipt; the counts below are that run's endpoint counts.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest
from click.testing import CliRunner
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_api_registrations import (
    DEFAULT_AUDIT_LIMITS,
    PARTITION_PROFILES,
    cli,
    parse_project_limits,
    parse_sizing_records,
    prepare_registration,
    profile_sized,
    render_typed_audit_inputs,
    resolve_audit_limits,
)
from data_sheets_schema import audit_batches as b, shared_generation as sg, typed_audit as ta
from data_sheets_schema.chunking import manifest_from_bytes
from data_sheets_schema.schema_snapshot import capture_schema

CHORUS_SIZING = ROOT / "tests" / "fixtures" / "audit_batches" / "chorus_v10_2026-10-22a"
RUNS = ROOT / "data" / "d4d_concatenated" / "claudecode_api_core"
AI_READI_SIZING = RUNS / "2026-09-04g_claude-opus-5-api-generic-v8_rep2" / "intermediate"
BOUNDS = {"max_paths": 80, "max_inventory_bytes": 12288}
# 2026-10-22a's typed-audit stages, counted by the endpoint before admission.
MEASURED = {"workers": (138859, 139001, 138283), "omission": 98527, "integration": 316914, "aggregate": 831979}
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
    # The profile's largest plan, four workers, fits its 4,000,000 with room.
    _, _, profile = prepare("CHORUS", tmp_path, partition="chorus", sizing_record=CHORUS_SIZING)
    assert profile["max_workers"] == 4
    assert profile["aggregate_input_tokens"] == (4 * profile["worker_input_tokens"] + profile["omission_input_tokens"]
                                                 + profile["integration_input_tokens"])
    assert MEASURED["aggregate"] < profile["aggregate_input_tokens"] < PARTITION_PROFILES["chorus"]["limits"]["aggregate_input_tokens"]
    assert profile["sizing_record"]["full"]["sha256"] == hashlib.sha256((CHORUS_SIZING / "CHORUS_full.yaml").read_bytes()).hexdigest()


def test_large_project_allowance_is_refused_below_its_sizing_before_anything_is_written(tmp_path):
    limits = {**BOUNDS, "max_workers": 16, "aggregate_input_tokens": 4000000}
    with pytest.raises(ValueError, match="aggregate_input_tokens 4,000,000 is below the typed-audit input") as refused:
        prepare("AI_READI", tmp_path, audit_limits=limits, sizing_record=AI_READI_SIZING)
    assert "refused midway, after its first stages are billed" in str(refused.value)
    reg, outputs, sizing = prepare("AI_READI", tmp_path, audit_limits={**limits, "aggregate_input_tokens": 16000000},
                                   sizing_record=AI_READI_SIZING)
    assert reg["audit_limits"]["max_workers"] == 16 and reg["audit_limits"]["max_calls"] == 18
    assert sizing["plan_workers"] == 15 and sizing["max_workers"] == 16
    assert 4000000 < sizing["aggregate_input_tokens"] <= 16000000
    assert sizing["aggregate_input_tokens"] == (16 * sizing["worker_input_tokens"] + sizing["omission_input_tokens"]
                                                + sizing["integration_input_tokens"])
    assert [path for path, _ in outputs] == [(tmp_path / "registration.json").resolve()]
    assert not list(tmp_path.iterdir())


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
    ai_readi = "AI_READI:max_paths=80,max_inventory_bytes=12288,max_workers=16,aggregate_input_tokens="
    refused = CliRunner().invoke(cli, args + ["--project-limits", ai_readi + "4000000"])
    assert refused.exit_code != 0
    assert "is below the typed-audit input" in refused.output
    assert not out.exists() or not any(out.iterdir())  # not even the CHORUS registration built first
    built = CliRunner().invoke(cli, args + ["--project-limits", ai_readi + "16000000"])
    assert built.exit_code == 0, built.output
    regs = {p: json.loads((out / f"registration_{p.lower()}_per_project.json").read_text()) for p in ("CHORUS", "AI_READI")}
    assert regs["CHORUS"]["audit_limits"] == resolve_audit_limits("CHORUS", "chorus")
    assert (regs["AI_READI"]["audit_limits"]["max_workers"], regs["AI_READI"]["audit_limits"]["aggregate_input_tokens"]) == (16, 16000000)
    assert "integration could exceed max_input_tokens_per_call" in built.output
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
    """The sizing renders the typed packet's own requests, digests and owner classes aside."""
    t = typed_inputs
    snapshot = capture_schema(t["schema_root"].absolute(), strict=True)
    packet = ta.prepare(protocol="typed_audit_protocol_v1", original_full=t["record"], bundle=t["bundle"],
                        manifest=t["manifest"], receipt=t["receipt"], context=t["context"], schema_path=t["schema_root"],
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
    wire = deepcopy(packet["omission_request"])
    wire["payload"]["schema"] = {k: v for k, v in wire["payload"]["schema"].items() if k not in ("classes", "slots")}
    mine = deepcopy(rendered["requests"]["omission"])
    owners = mine["payload"].pop("owner_classes")
    assert set(wire["payload"].pop("owner_classes")) <= set(owners)
    for key in ("input_sha256",):
        mine["payload"][key] = wire["payload"][key]
    mine["request_sha256"] = wire["request_sha256"]
    assert mine == wire
    # Integration: the same shared context, contract and rows; responses are sized from the caps.
    integration = rendered["requests"]["integration"]["integration_request"]["payload"]
    assert integration["shared_context"] == packet["requests"]["shared_context"]
    assert integration["output_contract"] == packet["contracts"]["integration"]
    assert [row["path"] for row in integration["proposal_index"]["rows"]] == [r["path"] for r in packet["plan"]["inventory"]["values"]]


@pytest.mark.skipif(not V10_RUN, reason="set D4D_CHORUS_V10_TYPED_RUN to the 2026-10-22a intermediate directory")
def test_rendering_reproduces_the_chorus_v10_wire():
    """Rendered from 10-22a's own inputs, every request matches its saved text but for the allowances."""
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
    assert rendered["worker_bytes"] - max(actual[:3]) == allowance + reworded
    owners = (len(sg.canonical(rendered["requests"]["omission"]["payload"]["owner_classes"]))
              - len(sg.canonical(packet["omission_request"]["payload"]["owner_classes"])))
    assert owners >= 0
    assert rendered["omission_bytes"] - actual[3] == allowance + owners
    assert rendered["integration_base_bytes"] < actual[4]
