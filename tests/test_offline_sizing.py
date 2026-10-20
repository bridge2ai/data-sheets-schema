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


# --- Ceilings no declaration can raise (#5072) ---------------------------------

@pytest.mark.parametrize("phase,inputs,output,window,margin,expected", [
    ("typed_audit_worker", 996_000, 4_000, 1_000_000, 0, "PASS"),
    ("typed_audit_worker", 996_001, 4_000, 2_000_000, 0, "FAIL"),    # a larger declared window cannot raise it
    ("report", 754_000, 96_000, 1_000_000, 0, "PASS"),
    ("report", 754_001, 96_000, 1_000_000, 0, "FAIL"),               # 850,001 in flight, no margin declared
    ("report_regate", 783_597, 96_000, 1_000_000, 100_000, "FAIL"),  # A1b's CHORUS regate row
    ("report_after_repair", 754_001, 96_000, 2_000_000, 0, "FAIL"),
    ("typed_audit_omission", 996_000, 4_000, 1_000_000, 0, "PASS"),
    ("full", 872_001, 128_000, 2_000_000, 0, "FAIL"),                # every phase keeps the route window
])
def test_a_declaration_cannot_raise_a_phase_ceiling(phase, inputs, output, window, margin, expected):
    verdict = sizing.window_status(inputs, output, window, margin, phase=phase)
    assert verdict["status"] == expected
    assert verdict["fits_ceiling"] == (expected == "PASS")
    assert verdict["ceiling_tokens"] == sizing.PHASE_CEILING_TOKENS.get(phase, sizing.ROUTE_WINDOW_TOKENS)


def ceiling_manifest(tmp_path, phase, input_tokens, max_tokens, window, margin):
    source = tmp_path / "source.txt"
    source.write_text("Exact source bytes.\n")
    inputs = [sizing.pin(source)]
    request = {"model": "fictional", "messages": [{"role": "user", "content": "source"}], "max_tokens": max_tokens}
    request_pin = save(tmp_path / "request.json", request)
    count = {"format": sizing.COUNT_FORMAT, "method": "endpoint messages.count_tokens", "request_id": "row",
             "request_sha256": sizing.sha(sizing.canonical(request)),
             "inputs_sha256": sizing.sha(sizing.canonical(inputs)), "input_tokens": input_tokens}
    manifest = {"format": sizing.FORMAT, "scope": "Invented row above its phase ceiling", "inputs": inputs,
                "requests": [{"id": "row", "phase": phase, "basis": "exact", "request": request_pin,
                              "count": save(tmp_path / "count.json", count), "context_limit_tokens": window,
                              "context_limit_basis": "Synthetic declared capacity", "required_margin_tokens": margin,
                              "margin_basis": "Synthetic declared margin"}]}
    path = tmp_path / "manifest.json"
    save(path, manifest)
    return path


@pytest.mark.parametrize("phase,input_tokens,max_tokens", [
    ("typed_audit_worker", 996_001, 4_000), ("report_regate", 754_001, 96_000)])
def test_the_cli_never_prints_pass_above_a_ceiling(tmp_path, capsys, phase, input_tokens, max_tokens):
    path = ceiling_manifest(tmp_path, phase, input_tokens, max_tokens, window=2_000_000, margin=0)
    row = sizing.review(path)["requests"][0]
    assert row["status"] == "FAIL" and row["fits_margin"] and not row["fits_ceiling"]
    assert sizing.main(["check", str(path)]) == 1
    printed = json.loads(capsys.readouterr().out)
    assert [r["status"] for r in printed["requests"]] == ["FAIL"]
    assert "PASS" not in json.dumps(printed)


# --- The A1 sweep's pure parts (scripts/offline_sizing.py) --------------------

from scripts import offline_sizing as sweep


def test_the_sweep_holds_the_evidence_readers_ceilings():
    assert sweep.ROUTE_WINDOW_TOKENS == sizing.ROUTE_WINDOW_TOKENS
    assert sweep.WORKER_CEILING_TOKENS == sizing.PHASE_CEILING_TOKENS["typed_audit_worker"]
    assert all(sizing.PHASE_CEILING_TOKENS[p] == sweep.REPORT_CEILING_TOKENS for p in sweep.REPORT_PHASES)


def test_placeholder_runs_were_counted_as_one_token_per_x():
    # With one token per 'x', each project's report and regate give the same clean ratio.
    for project in sweep.A1B:
        report, regate = sweep.clean_ratio(project, "report"), sweep.clean_ratio(project, "report_regate")
        assert abs(report - regate) < 0.0005, project
        assert all(0.33 < sweep.clean_ratio(project, f) < 0.42 for f in sweep.A1B[project])


def test_an_estimate_is_never_a_pass_and_counts_placeholders_in_tokens():
    worker = sweep.estimate("CHORUS", "typed_audit_worker", 2_461_846, 4_000)
    assert worker["verdict"] == "estimate_exceeds" and worker["ceiling_tokens"] == 1_000_000
    regate = sweep.estimate("CHORUS", "report_regate", 977_535, 96_000, placeholder_tokens=100_000)
    assert regate["ceiling_tokens"] == 850_000
    assert regate["estimated_input_tokens"] == round(977_535 * sweep.clean_ratio("CHORUS", "report_regate")) + 100_000
    assert regate["verdict"] == "estimate_fits"
    other = sweep.estimate("VOICE", "typed_audit_worker", 1_000, 4_000)
    assert other["ratio"] == round(max(sweep.clean_ratio(p, "typed_audit_worker") for p in sweep.A1B), 4)
    assert {"PASS", "FAIL"}.isdisjoint({worker["verdict"], regate["verdict"], other["verdict"]})


TINY_SCHEMA = """id: https://example.org/tiny
name: tiny
prefixes: {linkml: https://w3id.org/linkml/}
imports: [linkml:types]
default_range: string
classes:
  Dataset:
    attributes:
      id: {identifier: true}
      tools_used: {range: Tool, multivalued: true, inlined_as_list: true}
      strategy: {range: Strategy, inlined: true}
  Tool:
    attributes:
      id: {identifier: true}
      tools: {multivalued: true}
  Strategy:
    attributes:
      id: {identifier: true}
      strategies: {}
"""


def test_conformance_wraps_joins_and_removes_without_reformatting(tmp_path):
    schema = tmp_path / "tiny.yaml"
    schema.write_text(TINY_SCHEMA)
    record = ("id: x\n"
              "tools_used:\n"
              "  - id: x#tool\n"
              "    tools: one toolkit   # a comment survives\n"
              "strategy:\n"
              "  id: x#s\n"
              "  strategies:\n"
              "    - first\n"
              "    - second\n"
              "  invented_notes: not in the schema\n")
    text, edits, unfixable = sweep.conform_record(record, schema)
    assert unfixable == []
    assert sorted(edits) == ["/strategy/invented_notes (undeclared in Strategy, removed)",
                             "/strategy/strategies (joined)", "/tools_used/0/tools"]
    import yaml
    value = yaml.safe_load(text)
    assert value["tools_used"][0]["tools"] == ["one toolkit"]
    assert value["strategy"]["strategies"] == "first second"
    assert "invented_notes" not in value["strategy"]
    assert text.startswith("id: x\ntools_used:\n  - id: x#tool\n") and "# a comment survives" in text
    same, none, _ = sweep.conform_record("id: x\n", schema)
    assert same == "id: x\n" and none == []


def test_a_receipt_moves_by_chunk_hash_and_drops_removed_chunks():
    old = {"bundle_md5": "old", "chunks": [
        {"id": "c001", "source": "<preamble>", "sha256": "p-old"}, {"id": "c002", "source": "a", "sha256": "A"},
        {"id": "c003", "source": "crate", "sha256": "C"}, {"id": "c004", "source": "d", "sha256": "D"}]}
    new = {"bundle_md5": "new", "chunks": [
        {"id": "c001", "source": "<preamble>", "sha256": "p-new"}, {"id": "c002", "source": "a", "sha256": "A"},
        {"id": "c003", "source": "d", "sha256": "D"}, {"id": "c004", "source": "e", "sha256": "E"}]}
    receipt = ("bundle_md5: old\n"
               "chunks:\n"
               "- id: c001\n  status: nothing_relevant\n  reason: Header.\n"
               "- id: c002\n  status: extracted\n  extracted:\n  - slot: description\n    snippet: kept verbatim\n"
               "- id: c003\n  status: extracted\n  extracted:\n  - slot: x\n    snippet: crate text\n"
               "- id: c004\n  status: redundant_with\n  chunks:\n  - c003\n  - c002\n")
    text, info = sweep.remap_receipt(receipt, old, new)
    import yaml
    value = yaml.safe_load(text)
    assert value["bundle_md5"] == "new"
    assert [c["id"] for c in value["chunks"]] == ["c001", "c002", "c003", "c004"]
    assert value["chunks"][2] == {"id": "c003", "status": "redundant_with", "chunks": ["c002"]}
    assert value["chunks"][3]["status"] == "nothing_relevant"
    assert "crate text" not in text and "kept verbatim" in text
    assert info["dropped"] == ["c003"] and info["added"] == ["c004"] and info["moved"] == 3
    with pytest.raises(ValueError):
        sweep.remap_receipt(receipt.replace("bundle_md5: old", "bundle_md5: other"), old, new)


def test_a_minimal_receipt_names_every_chunk(tmp_path):
    manifest = tmp_path / "chunks.yaml"
    manifest.write_text("bundle_md5: abc\nchunks:\n- id: c001\n  sha256: x\n- id: c002\n  sha256: y\n")
    import yaml
    value = yaml.safe_load(sweep.minimal_receipt(manifest))
    assert value["bundle_md5"] == "abc"
    assert [(c["id"], c["status"]) for c in value["chunks"]] == [("c001", "nothing_relevant"),
                                                                ("c002", "nothing_relevant")]


def _sweep_results(head, full_bytes, worker_bytes, omission_bytes):
    stage = lambda b: {"payload_bytes": b, "estimated_in_flight_tokens": b // 2}
    return {"root_head": head, "projects": {"CHORUS": {"status": "MEASURED", "primary": "L", "runs": {"L|G2": {
        "stages": {"full": stage(full_bytes), "typed_audit_omission": stage(omission_bytes)},
        "typed": {"workers": [{"worker_id": "worker_0001", "payload_bytes": worker_bytes}]},
        "components": {"rerun": False}}}}}}


def test_a_rerun_merges_only_when_it_repeats_the_measurement():
    full = _sweep_results("abc", 100, 1_000, 900)
    rerun = _sweep_results("abc", 100, 1_018, 918)          # the scratch-path offset, uniform
    rerun["projects"]["CHORUS"]["runs"]["L|G2"]["components"] = {"rerun": True}
    merged = sweep.merge(full, rerun)
    assert merged["projects"]["CHORUS"]["runs"]["L|G2"]["components"] == {"rerun": True}
    assert merged["components_from"]["typed_byte_offsets"] == {"CHORUS": [18]}
    for changed in (_sweep_results("other", 100, 1_018, 918),     # another tree
                    _sweep_results("abc", 101, 1_018, 918),       # an ordinary phase moved
                    _sweep_results("abc", 100, 1_018, 919),       # offsets differ between typed stages
                    _sweep_results("abc", 100, 1_101, 1_001)):    # more than a path's length
        with pytest.raises(ValueError):
            sweep.merge(full, changed)
