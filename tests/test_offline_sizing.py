"""Offline evidence and production-request regressions for #5072."""
from copy import deepcopy
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from data_sheets_schema import offline_sizing as sizing


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("sizing must not contact a provider")
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def save(path, value):
    path.write_bytes(sizing.canonical(value))
    return sizing.pin(path)


@pytest.fixture
def saved(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("Exact source bytes, including café.\n")
    inputs = [sizing.pin(source)]
    request = {"model": "fictional", "messages": [{"role": "user", "content": "source"}],
               "max_tokens": 96_000, "thinking": {"type": "adaptive", "display": "summarized"}}
    request_pin = save(tmp_path / "request.json", request)
    count = {"format": sizing.COUNT_FORMAT, "method": "endpoint messages.count_tokens",
             "request_id": "report", "request_sha256": sizing.sha(sizing.canonical(request)),
             "inputs_sha256": sizing.sha(sizing.canonical(inputs)), "input_tokens": 700_000}
    count_pin = save(tmp_path / "count.json", count)
    manifest = {"format": sizing.FORMAT, "scope": "Invented single saved request, not a full run",
        "inputs": inputs, "requests": [{"id": "report", "phase": "report", "basis": "exact",
        "request": request_pin, "count": count_pin, "context_limit_tokens": 1_000_000,
        "context_limit_basis": "Synthetic declared capacity", "required_margin_tokens": 150_000,
        "margin_basis": "Synthetic explicit 15 percent margin"}]}
    path = tmp_path / "manifest.json"
    save(path, manifest)
    return path, manifest, request, count


def test_saved_count_has_exact_arithmetic_but_no_campaign_or_provider_approval(saved):
    path, manifest, _, _ = saved
    report = sizing.review(path)
    row = report["requests"][0]
    assert row["status"] == "PASS"
    assert row["clearance_tokens"] == 204_000
    assert row["max_output_tokens"] == 96_000
    assert report["full_run_readiness"] == "UNKNOWN"
    assert report["billing"] == "not verified"
    assert report["provider_support"] == "not checked"
    assert report["launch_authorization"] == "none"
    assert report["inputs"] == manifest["inputs"]


@pytest.mark.parametrize("stage,inputs,output,margin,expected", [
    ("CHORUS worker", 1_009_249, 16_000, 0, "FAIL"),
    ("AI_READI worker", 1_557_087, 16_000, 0, "FAIL"),
    ("AI_READI omission", 1_257_986, 4_000, 0, "FAIL"),
    ("AI_READI report", 931_279, 96_000, 150_000, "FAIL"),
    ("AI_READI regate", 1_314_737, 96_000, 150_000, "FAIL"),
    ("CHORUS regate", 783_597, 96_000, 150_000, "FAIL"),
    ("exact margin boundary", 754_000, 96_000, 150_000, "PASS"),
    ("one token below margin", 754_001, 96_000, 150_000, "FAIL"),
])
def test_historical_5072_numbers_are_arithmetic_fixtures_not_new_measurements(stage, inputs, output, margin, expected):
    verdict = sizing.window_status(inputs, output, 1_000_000, margin)
    assert verdict["status"] == expected, stage
    if stage == "CHORUS regate":
        assert verdict["fits_window"] and not verdict["fits_margin"]


@pytest.mark.parametrize("change", ["count absent", "request absent", "scenario", "dry-run"])
def test_missing_evidence_or_simulation_stays_unknown(saved, change):
    path, manifest, _, _ = saved
    row = manifest["requests"][0]
    if change == "count absent":
        row["count"] = None
    if change == "request absent":
        row["request"] = row["count"] = None
    if change == "scenario":
        row["basis"] = "scenario"
    save(path, manifest)
    report = sizing.review(path, dry_run=change == "dry-run")
    assert report["requests"][0]["status"] == "UNKNOWN"
    assert report["full_run_readiness"] == "UNKNOWN"


@pytest.mark.parametrize("kind", ["source", "request", "count"])
@pytest.mark.parametrize("mode", ["missing", "same-length replacement"])
def test_pinned_files_are_required_and_byte_exact(saved, kind, mode):
    path, manifest, _, _ = saved
    item = manifest["inputs"][0] if kind == "source" else manifest["requests"][0][kind]
    selected = Path(item["path"])
    if mode == "missing":
        selected.unlink()
        expected = OSError
    else:
        raw = selected.read_bytes()
        selected.write_bytes(b"x" + raw[1:])
        expected = ValueError
    with pytest.raises(expected):
        sizing.review(path)


@pytest.mark.parametrize("field,value", [
    ("request_id", "other"), ("request_sha256", "0" * 64), ("inputs_sha256", "0" * 64),
    ("method", "byte estimate"), ("input_tokens", True), ("input_tokens", "700000"),
    ("input_tokens", -1), ("input_tokens", None),
])
def test_unbound_or_invalid_count_refuses_even_with_current_file_hash(saved, field, value):
    path, manifest, _, count = saved
    count[field] = value
    manifest["requests"][0]["count"] = save(path.parent / "count.json", count)
    save(path, manifest)
    with pytest.raises(ValueError):
        sizing.review(path)


@pytest.mark.parametrize("raw", [b'{"format":1,"format":2}', b'{"x":NaN}', b'\xff'])
def test_ambiguous_or_invalid_json_refuses(tmp_path, raw):
    path = tmp_path / "manifest.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        sizing.review(path)


def test_replacing_source_and_repinning_manifest_does_not_reuse_old_count(saved):
    path, manifest, _, _ = saved
    source = Path(manifest["inputs"][0]["path"])
    source.write_text("New no-crate source, not the historic source.\n")
    manifest["inputs"] = [sizing.pin(source)]
    save(path, manifest)
    with pytest.raises(ValueError, match="not bound"):
        sizing.review(path)


def test_changed_output_cap_cannot_reuse_prior_count(saved):
    path, manifest, request, _ = saved
    request["max_tokens"] = 128_000
    manifest["requests"][0]["request"] = save(path.parent / "request.json", request)
    save(path, manifest)
    with pytest.raises(ValueError, match="not bound"):
        sizing.review(path)


def test_duplicate_rows_and_unexpected_metadata_refuse(saved):
    path, manifest, _, _ = saved
    manifest["requests"].append(deepcopy(manifest["requests"][0]))
    save(path, manifest)
    with pytest.raises(ValueError, match="duplicate request"):
        sizing.review(path)
    manifest["requests"].pop()
    manifest["requests"][0]["max_tokens"] = 1
    save(path, manifest)
    with pytest.raises(ValueError, match="exactly"):
        sizing.review(path)


def test_cli_has_unknown_exit_and_never_overwrites(saved, tmp_path):
    path, _, _, _ = saved
    output = tmp_path / "review.json"
    assert sizing.main(["check", str(path), "--dry-run", "--out", str(output)]) == 1
    before = output.read_bytes()
    report = json.loads(before)
    assert report["requests"][0]["status"] == "UNKNOWN"
    with pytest.raises(SystemExit) as exc:
        sizing.main(["check", str(path), "--out", str(output)])
    assert exc.value.code == 2
    assert output.read_bytes() == before


def production_spec(tmp_path, version):
    if version == 2:
        from tests.test_source_heading_runtime_api import draft_files, selected_spec
        return selected_spec(tmp_path, draft_files.__wrapped__())
    from tests.test_generation_manifest_identity import external
    from tests.test_shared_generation_selection import registration_for, selected_spec
    spec = external.__wrapped__(tmp_path)
    return selected_spec(spec, registration_for(spec))


@pytest.mark.parametrize("version", [1, 2])
def test_production_full_export_matches_sender_and_effective_cap(tmp_path, monkeypatch, version):
    from data_sheets_schema import api_runner as api
    monkeypatch.setattr(api, "provider_identity", lambda: {"provider": None, "base_url": None})
    spec = production_spec(tmp_path, version)
    monkeypatch.setenv("D4D_RECEIPT_FULL_MAX_TOKENS", "91000")
    payload, inputs = sizing.full_request(spec)
    settings = api._model_settings(spec.condition)
    sent = {}
    class ObservedSender(Exception):
        pass
    def capture(*args, **kwargs):
        sent.update(kwargs)
        raise ObservedSender
    monkeypatch.setattr(api, "_call_with_usage", capture)
    with pytest.raises(ObservedSender):
        api._generate_phase(spec, "full", {}, object(), settings, [])
    # Exercise the real adapter's entire logical body, including SDK extra_body
    # normalization. Stop at a local stream boundary, before any network use.
    wire = {}
    class ObservedWire(BaseException):
        pass
    def stream(**kwargs):
        wire.update(kwargs)
        raise ObservedWire
    client = SimpleNamespace(messages=SimpleNamespace(stream=stream))
    with pytest.raises(ObservedWire):
        api._call_with_retry(client, **sent, transport_attempts=1)
    wire.update(wire.pop("extra_body", {}))
    assert payload == wire
    assert payload["max_tokens"] == 91_000
    assert "temperature" not in payload
    assert any(item["path"] == str(spec.bundle) for item in inputs)
    assert not spec.out_dir.exists()
    Path(spec.bundle).write_text("changed")
    with pytest.raises(ValueError, match="authority changed"):
        sizing.full_request(spec)


@pytest.mark.parametrize("version", [1, 2])
def test_prepare_full_creates_explicit_unknown_later_stages(tmp_path, monkeypatch, version):
    from data_sheets_schema import api_runner as api
    monkeypatch.setattr(api, "provider_identity", lambda: {"provider": None, "base_url": None})
    spec = production_spec(tmp_path, version)
    reg = json.loads(spec.shared_generation_registration)
    output = tmp_path / "fresh-export"
    manifest_path = sizing.prepare_full(reg["registration_path"], output,
        context_limit_tokens=900_000, context_limit_basis="Synthetic caller declaration",
        required_margin_tokens=150_000, margin_basis="Synthetic margin")
    report = sizing.review(manifest_path)
    assert {row["phase"] for row in report["requests"]} == sizing.PHASES
    assert all(row["status"] == "UNKNOWN" for row in report["requests"])
    assert report["requests"][0]["payload_bytes"] > 0
    assert report["requests"][0]["max_output_tokens"] > 0
    assert all(row["payload_bytes"] is None for row in report["requests"][1:])
    assert not spec.out_dir.exists()
    with pytest.raises(FileExistsError):
        sizing.prepare_full(reg["registration_path"], output,
            context_limit_tokens=900_000, context_limit_basis="Synthetic caller declaration",
            required_margin_tokens=150_000, margin_basis="Synthetic margin")
