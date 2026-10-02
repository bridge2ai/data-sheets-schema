"""Exact registered gates, offline reads and CLI/canary parity; no paid calls."""
import copy
import hashlib
import json

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import canary, receipts, receipt_completion_policy as cp
from data_sheets_schema.api_runner import RUNTIME
from data_sheets_schema.receipt_completion import POLICY_SHA256
from data_sheets_schema.cli.receipts import check as command, strict_failure


def registration(floor=None):
    return {"format": cp.FORMAT, "registration_id": "supplied-test-only", "condition": "generic",
            "runtime_policy_sha256": POLICY_SHA256, "receipt_instrument_version": 4,
            "max_output_tokens": 4096, "max_request_bytes": 1_000_000,
            "context_limit_tokens": 1_000_000, "context_limit_basis": "synthetic test capacity, not a route claim",
            "coverage_floor": floor or {"state": "registered", "numerator": 2, "denominator": 3}}


def declaration(reg=None):
    raw = json.dumps(reg or registration()).encode()
    return {"condition": "generic", "runtime": RUNTIME, "render_version": 8,
            "receipt_completion_version": 1, "receipt_completion_policy_sha256": POLICY_SHA256,
            "receipt_completion_registration": cp.registration_identity(raw)}


def policy(floor=None):
    return cp.select_policy(declaration(registration(floor)))


@pytest.mark.parametrize("change", [
    {"max_output_tokens": True}, {"max_output_tokens": 0}, {"max_request_bytes": -1},
    {"receipt_instrument_version": 3}, {"runtime_policy_sha256": "0" * 64},
    {"extra": 1}, {"registration_id": " "}, {"condition": []},
    {"context_limit_tokens": True}, {"context_limit_tokens": 0}, {"context_limit_tokens": 1024},
    {"context_limit_basis": " "}, {"context_limit_basis": None},
    {"coverage_floor": {"state": "pending"}},
    {"coverage_floor": {"state": "registered", "numerator": 1, "denominator": True}},
    {"coverage_floor": {"state": "registered", "numerator": 4, "denominator": 3}},
    {"coverage_floor": {"state": "registered", "numerator": 0.5, "denominator": 1}},
])
def test_registration_refuses_ambiguous_or_unregistered_values(change):
    with pytest.raises(ValueError):
        cp.parse_registration(json.dumps({**registration(), **change}).encode())


@pytest.mark.parametrize("raw", [b'{"format":1,"format":2}', b'NaN', b'[]', b'null', b'\xff', b'{} trailing'])
def test_registration_requires_strict_json(raw):
    with pytest.raises(ValueError):
        cp.parse_registration(raw)


def test_identity_binds_exact_bytes_and_installed_policy(monkeypatch):
    raw = json.dumps(registration()).encode()
    assert cp.registration_identity(raw) != cp.registration_identity(raw + b'\n')
    from data_sheets_schema import receipt_completion as runtime
    monkeypatch.setattr(runtime, "POLICY_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="frozen SHA256"):
        cp.parse_registration(raw)


def test_selection_authority_and_runtime_identity():
    spec = declaration()
    record = {"prompts": {"request": {"spec": spec}}, "receipt_completion": {"registration": spec["receipt_completion_registration"]}}
    assert cp.select_policy(record=record) == cp.select_policy(spec, record)
    assert cp.select_policy(record={"receipts": {"instrument": receipts.RERECEIPTS_INSTRUMENT}}) is None
    assert cp.select_policy(record={"condition": "generic", "origin": "rereceipt"}) is None
    altered = copy.deepcopy(spec)
    altered["receipt_completion_registration"]["raw_json"] += "\n"
    for bad in (altered, {**spec, "runtime": "api"}, {**spec, "render_version": 7},
                {**spec, "receipt_completion_version": True}, {**spec, "condition": "other"}):
        with pytest.raises(ValueError):
            cp.select_policy(bad)
    for key in cp.SPEC_KEYS:
        with pytest.raises(ValueError):
            cp.select_policy({k: v for k, v in spec.items() if k != key})
    with pytest.raises(ValueError):
        cp.select_policy({"condition": "generic"}, record)
    with pytest.raises(ValueError):
        cp.select_policy(record={"receipt_completion": record["receipt_completion"]})


@pytest.mark.parametrize("covered,eligible,passed", [(2, 3, True), (1, 3, False), (3, 3, True)])
def test_exact_fraction(covered, eligible, passed):
    assert cp.evaluate_floor({"with_receipt": covered, "receiptable": eligible}, policy())["passed"] is passed


def test_large_fraction_near_boundary_and_pending_empty_never_pass():
    n = 10**18
    p = policy({"state": "registered", "numerator": n - 1, "denominator": n})
    assert not cp.evaluate_floor({"with_receipt": n - 2, "receiptable": n}, p)["passed"]
    assert cp.evaluate_floor({"with_receipt": n - 1, "receiptable": n}, p)["passed"]
    assert cp.evaluate_floor({"with_receipt": 0, "receiptable": 0}, p)["state"] == "not_applicable"
    pending = policy({"state": "pending", "mode": "diagnostic_pilot"})
    assert cp.evaluate_floor({"with_receipt": 9, "receiptable": 9}, pending)["state"] == "pending"
    assert not cp.evaluate_floor({"with_receipt": 9, "receiptable": 9}, pending)["passed"]


@pytest.mark.parametrize("change", [
    {"with_receipt": True}, {"receiptable": 3.0}, {"with_receipt": -1}, {"with_receipt": 4},
    {"populated": 3, "exempt": 1}, {"without_receipt": [], "without_receipt_truncated": None},
    {"without_receipt": ["/x"], "without_receipt_truncated": False},
    {"never_receipted": 0, "added_after_receipt": 0}, {"never_receipted": False},
])
def test_bad_coverage_counters_refused(change):
    with pytest.raises(ValueError):
        cp.evaluate_floor({"with_receipt": 2, "receiptable": 3, **change}, policy())


def block(p, covered=2, eligible=3):
    return {"checked": True, "expected": True, "instrument": receipts.RERECEIPTS_INSTRUMENT,
            cp.BLOCK_KEY: cp.block_identity(p), "slots": {"with_receipt": covered, "receiptable": eligible},
            "chunks": {"total": 1, "reviewed": 1}, "snippets": {"verified": 1}, "findings": []}


@pytest.mark.parametrize("floor,covered,eligible,status", [
    (None, 2, 3, canary.OK), (None, 1, 3, canary.REGRESSED),
    (None, 0, 0, canary.UNMEASURABLE),
    ({"state": "pending", "mode": "diagnostic_pilot"}, 3, 3, canary.UNMEASURABLE),
])
def test_cli_and_canary_share_floor_without_trusting_stored_pass(floor, covered, eligible, status):
    b = block(policy(floor), covered, eligible)
    b["coverage_floor"] = {"passed": True, "state": "passed"}  # Must be recomputed.
    verdict = canary.verdict({"receipts": b}, {}, baseline_requested=False)
    # Other unmeasured canary instruments are irrelevant to this isolated test;
    # inspect the coverage row and regression/blind lists directly.
    assert strict_failure(b) is (status != canary.OK)
    row = next(r for r in verdict["rows"] if r["metric"] == "registered receipt coverage")
    assert (row["run"] is None) is (status == canary.UNMEASURABLE)
    if status != canary.UNMEASURABLE:
        assert row["run"] == int(status != canary.OK)


def test_record_cannot_downgrade_or_change_policy():
    spec = declaration()
    selected = cp.select_policy(spec)
    rec = {"prompts": {"request": {"spec": spec}}, "receipts": block(selected)}
    assert canary.checks_from_record(rec)["receipts"]["checked"]
    for replacement in ({}, {**block(selected), "instrument": receipts.RECEIPTS_INSTRUMENT},
                        block(policy({"state": "registered", "numerator": 0, "denominator": 1}))):
        assert not canary.checks_from_record({**rec, "receipts": replacement})["receipts"]["checked"]
    assert not canary.checks_from_record({"receipts": block(selected)})["receipts"]["checked"]


@pytest.mark.parametrize("counter", [
    {"never_receipted": 1, "added_after_receipt": None},
    {"never_receipted": None, "added_after_receipt": 1},
    {"without_receipt_truncated": -1}, {"without_receipt_truncated": True},
    {"without_receipt_truncated": 0},
    {"addressing_slips_count": -1}, {"exempt_on_carried_identifier": -1},
    {"receipt_paths": False}, {"exempt_on_carried_identifier": 1, "populated": 3, "exempt": 0},
])
def test_optional_counters_cannot_bypass_registered_gate(counter):
    b = block(policy(), 3, 3)
    b["slots"].update(counter)
    assert strict_failure(b)
    assert canary.receipt_coverage_floor(b)["state"] == "unmeasurable"


@pytest.mark.parametrize("snapshot,explicit", [
    (declaration(), declaration(registration({"state": "pending", "mode": "diagnostic_pilot"}))),
    (declaration(), {"condition": "generic"}),
    ({"condition": "generic"}, declaration()),
])
def test_disk_compares_every_supplied_declaration_before_reading(disk, snapshot, explicit):
    from types import SimpleNamespace
    spec = SimpleNamespace(receipt_completion_version=snapshot.get("receipt_completion_version", 0),
                           render_spec=lambda: snapshot)
    b = receipts.block_for(**disk, snapshot_spec=spec, receipt_render_spec=explicit)
    assert b["expected"] and not b["checked"]
    assert "policy" in b["reason"] and "snapshot" in b["reason"]


def test_default_snapshot_cannot_silently_select_new_record_policy(disk):
    from data_sheets_schema.api_runner import RunSpec
    spec = RunSpec(project="P", arm="A", method="claudecode_api", bundle=disk["bundle"], label="L",
                   out_dir=disk["full_path"].parent, manifest=None, profile="neutral", provider="test", render_version=8)
    rec = {"run": {"project": "P", "method": "claudecode_api", "label": "L", "condition": "generic"},
           "prompts": {"request": {"spec": declaration()}}}
    b = receipts.block_for(**disk, snapshot_spec=spec, snapshot_record=rec)
    assert b["expected"] and not b["checked"]
    assert "policy selection refused" in b["reason"]


@pytest.fixture
def disk(tmp_path):
    from data_sheets_schema.chunking import build_manifest, dump_manifest
    from tests.test_receipts import BUNDLE, FULL, _receipt
    bundle, full, receipt, manifest = (tmp_path / n for n in ("P.txt", "P_d4d.yaml", "P_coverage_receipt.yaml", "chunks.yaml"))
    bundle.write_text(BUNDLE)
    full.write_text(f"# Source bundle: {bundle}\n" + yaml.safe_dump(FULL))
    md5 = hashlib.md5(bundle.read_bytes()).hexdigest()
    receipt.write_text(yaml.safe_dump(_receipt(md5)))
    manifest.write_text(dump_manifest(build_manifest(bundle)))
    return dict(full_path=full, receipt=receipt, bundle=bundle, record_bundle_md5=md5, expected=True, manifest=manifest)


def test_disk_rebuild_selects_registration_instrument_and_retains_legacy(disk):
    legacy = receipts.block_for(**disk)
    selected = receipts.block_for(**disk, receipt_render_spec=declaration())
    assert legacy["checked"] and legacy["instrument"] == receipts.RECEIPTS_INSTRUMENT
    assert cp.BLOCK_KEY not in legacy and "coverage_floor" not in legacy
    assert selected["checked"] and selected["instrument"] == receipts.RERECEIPTS_INSTRUMENT
    assert selected["slots"] == legacy["slots"]
    assert selected["coverage_floor"]["registration_sha256"] == declaration()["receipt_completion_registration"]["sha256"]
    rec = {"run": {"project": "P"}, "prompts": {"request": {"spec": declaration()}}}
    assert receipts.block_for(**disk, snapshot_record=rec) == selected


def test_real_cli_preprovenance_and_write_prevent_policy_override(disk, tmp_path, monkeypatch):
    import data_sheets_schema.cli.receipts as cli
    p = {"core_dir": tmp_path, "full": disk["full_path"], "provenance": tmp_path / "P_provenance.yaml"}
    monkeypatch.setattr(cli, "_run_paths", lambda *args: p)
    regpath = tmp_path / "registration.json"
    regpath.write_text(json.dumps(registration({"state": "pending", "mode": "diagnostic_pilot"})))
    args = ["--method", "claudecode_api", "--label", "L", "--project", "P", "--strict",
            "--chunk-manifest", str(disk["manifest"]), "--receipt-completion-registration", str(regpath)]
    result = CliRunner().invoke(command, args)
    assert result.exit_code == 1, result.output
    assert "pending" in result.output
    p["provenance"].write_text(yaml.safe_dump({"inputs": {"bundle_path": str(disk["bundle"]), "bundle_md5": disk["record_bundle_md5"], "receipt_expected": True}}))
    original = p["provenance"].read_bytes()
    result = CliRunner().invoke(command, [*args, "--write"])
    assert result.exit_code == 1 and "historical run" in result.output
    assert p["provenance"].read_bytes() == original


def test_real_cli_writes_selected_v4_and_pending_does_not_pass(disk, tmp_path, monkeypatch):
    import data_sheets_schema.cli.receipts as cli
    p = {"core_dir": tmp_path, "full": disk["full_path"], "provenance": tmp_path / "P_provenance.yaml"}
    monkeypatch.setattr(cli, "_run_paths", lambda *args: p)
    spec = declaration(registration({"state": "pending", "mode": "diagnostic_pilot"}))
    rec = {"run": {"project": "P"}, "prompts": {"request": {"spec": spec}},
           "inputs": {"bundle_path": str(disk["bundle"]), "bundle_md5": disk["record_bundle_md5"], "receipt_expected": True}}
    p["provenance"].write_text(yaml.safe_dump(rec))
    args = ["--method", "claudecode_api", "--label", "L", "--project", "P", "--strict", "--write",
            "--chunk-manifest", str(disk["manifest"])]
    result = CliRunner().invoke(command, args)
    assert result.exit_code == 1 and "pending" in result.output, result.output
    after = yaml.safe_load(p["provenance"].read_text())
    assert after["prompts"] == rec["prompts"]
    assert after["receipts"]["instrument"] == receipts.RERECEIPTS_INSTRUMENT
    assert after["receipts"]["coverage_floor"]["state"] == "pending"
    assert strict_failure(canary.checks_from_record(after)["receipts"])
