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


@pytest.mark.parametrize("stage,phase,inputs,output,margin,expected", [
    ("CHORUS worker", "typed_audit_worker", 1_009_249, 16_000, 0, "FAIL"),
    ("AI_READI worker", "typed_audit_worker", 1_557_087, 16_000, 0, "FAIL"),
    ("AI_READI omission", "typed_audit_omission", 1_257_986, 4_000, 0, "FAIL"),
    ("AI_READI report", "report", 931_279, 96_000, 150_000, "FAIL"),
    ("AI_READI regate", "report_regate", 1_314_737, 96_000, 150_000, "FAIL"),
    ("CHORUS regate", "report_regate", 783_597, 96_000, 150_000, "FAIL"),
    ("exact margin boundary", "report", 754_000, 96_000, 150_000, "PASS"),
    ("one token below margin", "report", 754_001, 96_000, 150_000, "FAIL"),
])
def test_historical_5072_numbers_are_arithmetic_fixtures_not_new_measurements(stage, phase, inputs, output, margin,
                                                                              expected):
    verdict = sizing.window_status(inputs, output, 1_000_000, margin, phase=phase)
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
    # The declared 2M window is capped to the route's 1M, and the ceiling still binds below it.
    assert row["status"] == "FAIL" and not row["fits_ceiling"] and row["window_tokens"] == 1_000_000
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
                             "/strategy/strategies (joined)", "/tools_used/0/tools (wrapped)"]
    import yaml
    value = yaml.safe_load(text)
    assert value["tools_used"][0]["tools"] == ["one toolkit"]
    assert value["strategy"]["strategies"] == "first second"
    assert "invented_notes" not in value["strategy"]
    assert text.startswith("id: x\ntools_used:\n  - id: x#tool\n") and "# a comment survives" in text
    same, none, _ = sweep.conform_record("id: x\n", schema)
    assert same == "id: x\n" and none == []
    one, unwrapped, _ = sweep.conform_record("id: x\nstrategy:\n  id: x#s\n  strategies:\n    - only\n", schema)
    assert unwrapped == ["/strategy/strategies (unwrapped)"] and yaml.safe_load(one)["strategy"]["strategies"] == "only"


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


def test_a_project_the_full_sweep_could_not_stage_is_added_whole():
    full = _sweep_results("abc", 100, 1_000, 900)
    full["projects"]["KIDS_FIRST"] = {"status": "UNKNOWN", "reason": "no bundle, context or record to stage"}
    rerun = {"root_head": "abc", "projects": {"KIDS_FIRST": {"status": "MEASURED", "primary": "L", "runs": {}}}}
    merged = sweep.merge(full, rerun)
    assert merged["projects"]["KIDS_FIRST"]["status"] == "MEASURED"
    assert merged["components_from"]["added_projects"] == ["KIDS_FIRST"]


def test_kids_first_inputs_come_from_its_canary_directory():
    root = Path(__file__).resolve().parents[1]
    bundle, manifest, context, missing = sweep.inputs_for(root, "KIDS_FIRST")
    assert missing == [] and context is None                   # the A3 builder synthesizes a draft context
    assert bundle.name == "KIDS_FIRST_preprocessed.txt" and manifest.name == "chunks.yaml"
    assert bundle.parent == root / "notes/matched_cborg_2026-09-13/kids_first"
    assert sweep.PROXY["KIDS_FIRST"] == "AI_READI" and "S7" in sweep.OPTIONS


def test_window_status_needs_the_phase_and_caps_a_larger_declared_window():
    with pytest.raises(TypeError):
        sizing.window_status(900_000, 96_000, 1_000_000, 0)          # no phase: a report would get 1M
    with pytest.raises(ValueError):
        sizing.window_status(900_000, 96_000, 1_000_000, 0, phase="unknown")
    verdict = sizing.window_status(1_496_000, 4_000, 2_000_000, 0, phase="typed_audit_worker")
    assert verdict["window_tokens"] == 1_000_000 and verdict["clearance_tokens"] == -500_000
    assert not verdict["fits_window"] and not verdict["fits_margin"] and verdict["status"] == "FAIL"


def test_the_assembled_audit_bound_counts_every_worker():
    limits = {"worker_output_tokens": 4_000, "integration_output_tokens": 4_000}
    assert sweep.findings_bound(6, limits) == 28_000 and sweep.findings_bound(2, limits) == 12_000
    assert sweep.delivered_body("a: 1\n", "chunks: []\n", "--- COVERAGE RECEIPT ---") == \
        "a: 1\n--- COVERAGE RECEIPT ---\nchunks: []\n"


def _typed_run(worker_bytes, omission_bytes, integration_bytes, workers_cap=4_000):
    worker = lambda b: {"payload_bytes": b, "max_output_tokens": workers_cap, "placeholder_tokens": 0}
    return {"typed": {"status": "MEASURED", "workers": [worker(b) for b in worker_bytes]},
            "stages": {"typed_audit_omission": {"payload_bytes": omission_bytes, "max_output_tokens": 4_000,
                                                "placeholder_tokens": 0},
                       "typed_audit_integration": {"payload_bytes": integration_bytes, "max_output_tokens": 4_000,
                                                   "placeholder_tokens": 4_000 * len(worker_bytes) + 4_000}}}


def test_typed_input_is_summed_over_every_typed_call_and_an_option_removes_from_each():
    run = _typed_run([1_000_000, 1_000_000], 800_000, 900_000)
    r = lambda phase: sweep.ratios("CHORUS", phase)[0]
    expected = (2 * round(1_000_000 * r("typed_audit_worker")) + round(800_000 * r("typed_audit_omission"))
                + round(900_000 * r("typed_audit_integration")) + 12_000)
    assert sweep.typed_aggregate("CHORUS", run) == expected
    components = {"typed_audit_worker (largest)": {"typed": {"shared.schema": 500_000}},
                  "typed_audit_omission": {"typed": {"payload.schema": 300_000}},
                  "typed_audit_integration": {"typed": {"shared.schema": 500_000}}}
    keys = ("typed.shared.schema", "typed.payload.schema")
    less = sweep.typed_aggregate("CHORUS", run, components, keys)
    assert less == (2 * round(500_000 * r("typed_audit_worker")) + round(500_000 * r("typed_audit_omission"))
                    + round(400_000 * r("typed_audit_integration")) + 12_000)
    assert sweep.typed_aggregate("CHORUS", {"typed": {"status": "REFUSED"}}) is None


TINY_RECORD = ("id: doi:10.1/x\n"
               "conforms_to_schema: https://example.org/schema\n"
               "title: A dataset, with a clause.\n"
               "creators:\n"
               "  - id: doi:10.1/x#person-1\n"
               "    name: Jane Doe\n"
               "  - id: other:2\n"
               "    name: Ann Roe\n"
               "size: 42\n")


def test_the_response_floor_is_a_response_the_worker_check_accepts():
    import yaml
    from data_sheets_schema import audit_batches
    plan = audit_batches.make_plan(TINY_RECORD, max_paths=4, max_inventory_bytes=4_096, max_workers=4, version=2)
    check = lambda raw, p, worker_id: audit_batches.check_worker(raw, p, worker_id, version=2)
    text = {row["path"]: row["text"] for row in plan["inventory"]["values"]}
    assert len(plan["workers"]) > 1
    for worker in plan["workers"]:
        floor = sweep.response_floor(plan, worker, check)
        variants = sweep.floor_variants(plan, worker)
        assert set(variants) == {"supported", "revised", "mixed"}
        assert floor["passed"] and floor["bytes"] == min(len(raw) for raw in variants.values())
        low = floor["worker_check_minimum"]
        assert low["passed"] and low["bytes"] <= floor["bytes"]
        for raw in variants.values():
            rows = yaml.safe_load(raw)["source_review"]["values"]
            assert [r["path"] for r in rows] == worker["paths"]
            for r in rows:
                if r["path"] in ("/conforms_to_schema", "/creators/0/id"):    # declared record metadata
                    assert set(r) == {"path", "metadata_reason"}
                else:
                    assert [c["text"] for c in r["claims"]] == [text[r["path"]]]  # the whole value, quoted
            # Every assigned path needs its row: one fewer is refused.
            short = yaml.safe_load(raw)
            short["source_review"]["values"].pop()
            assert not check(json.dumps(short).encode(), plan, worker["id"])["passed"]
    refused = sweep.response_floor(plan, plan["workers"][0], lambda *a: {"passed": False, "errors": [{"code": "x"}]})
    nothing = {"bytes": None, "passed": False, "errors": {"supported": ["x"], "revised": ["x"], "mixed": ["x"]}}
    assert refused == {**nothing, "worker_check_minimum": nothing}
    assert sweep.floor_tokens(10) == 3 and sweep.floor_tokens(None) is None


def test_the_floor_meets_the_terminal_quoting_rule_and_the_worker_minimum_does_not():
    from data_sheets_schema import audit_batches, source_review
    plan = audit_batches.make_plan(TINY_RECORD, max_paths=4, max_inventory_bytes=4_096, max_workers=4, version=2)
    chunks = {"c001": {"source": "doc.txt", "text": "Jane Doe and Ann Roe made a dataset."}}

    def review(quote=None):
        rows = [r for w in plan["workers"] for r in json.loads(sweep.floor_variants(plan, w, quote=quote)[
            "supported"])["source_review"]["values"]]
        return source_review.check({"artifact": "original_full", "sha256": plan["original_full_sha256"],
                                    "values": rows}, raw=TINY_RECORD, artifact="original_full", chunks=chunks,
                                   audit_findings=[], protocol_version=7)["findings"]
    floor, low = sweep.sort_findings(review()), sweep.sort_findings(review(quote="t"))
    # The one-character evidence fails the evidence assertions either way;
    # only the one-character claims fail the quoting and coverage rules.
    assert floor["findings"] > 0 and floor["quote_or_coverage"] == 0
    assert low["quote_or_coverage"] > 0


def test_the_floor_audit_is_the_assembled_audit_of_every_row():
    import yaml
    from data_sheets_schema import audit_batches, audit_grammar
    plan = audit_batches.make_plan(TINY_RECORD, max_paths=4, max_inventory_bytes=4_096, max_workers=4, version=2)
    text = sweep.floor_assembly(audit_batches, plan)
    assert audit_grammar.check(text.encode("utf-8"), version=2)["passed"]
    rows = yaml.safe_load(text)["source_review"]["values"]
    assert [r["path"] for r in rows] == [r["path"] for r in plan["inventory"]["values"]]
    # At least every worker's rows: the assembled audit drops only their envelopes.
    rows_bytes = sum(len(sweep.floor_variants(plan, w)["supported"]) for w in plan["workers"])
    assert len(text.encode("utf-8")) > rows_bytes - 200 * len(plan["workers"])
    broken = {**plan, "workers": plan["workers"][:-1]}          # a path no worker answers
    assert sweep.floor_assembly(audit_batches, broken) is None


def test_the_larger_audit_carry_is_kept():
    caps = (900_000, 96_000, 28_000, "registered output caps")
    floor = (1_000_000, 96_000, 0, "workers' smallest responses, assembled")
    assert sweep.larger_carry("AI_READI", "report", [caps, floor])[3] == floor[3]
    assert sweep.larger_carry("AI_READI", "report", [caps, (900_100, 96_000, 0, "x")])[3] == caps[3]


class _Request:
    """A request whose wire size is its text."""
    def __init__(self, phase, texts):
        self.phase, self.system, self.cached_blocks = phase, "", []
        self.messages = [{"role": "user", "content": [{"type": "text", "text": t} for t in texts]}]


def _stub_runtime():
    api = SimpleNamespace(
        build_phase=lambda spec, phase, carry: _Request(phase, [f"{k}: {v}" for k, v in carry.items()]),
        _append_regate=lambda request, spec, report, findings: request.messages[0]["content"].append(
            {"type": "text", "text": "regate: " + report}),
        build_readdress=lambda request, body, unresolved: _Request("full_readdress", [body]),
        build_repair=lambda phase, record, errors, profile, _captured_digest: _Request(phase, [record]),
        READDRESS_MAX_TOKENS=8_000, RECEIPT_MARK="--- COVERAGE RECEIPT ---", output_limit=lambda name: 128_000,
        phase_max_tokens=lambda spec, phase, default, model=None: 128_000 if phase == "full" else 96_000)
    rc = SimpleNamespace(
        request_payload=lambda request, settings, registration: {
            "messages": request.messages, "max_tokens": registration["max_output_tokens"]},
        build_request=lambda inputs: (_Request("full_receipt_completion", [inputs["record"]]), None),
        schema_capture=lambda spec: {}, registration_identity=lambda spec: {},
        policy_identity=lambda version=None: {}, registration=lambda spec: {"max_output_tokens": 4_000})
    sg = SimpleNamespace(canonical=lambda value: json.dumps(value, sort_keys=True).encode("utf-8"),
                         generation_context=lambda spec: "context", digest_text=lambda spec, cls: "digest")
    return SimpleNamespace(api=api, rc=rc, sg=sg)


def _stub_run(tmp_path):
    run = tmp_path / "run"
    (run / "intermediate").mkdir(parents=True)
    for name, text in (("intermediate/P_full.yaml", "full: record\n"), ("intermediate/P_core.yaml", "core: x\n"),
                       ("P_coverage_receipt.yaml", "chunks: []\n"), ("../manifest.yaml", "x\n"), ("../bundle.txt", "x\n")):
        (run / name).write_text(text)
    spec = SimpleNamespace(out_dir=str(run), chunk_manifest=str(tmp_path / "manifest.yaml"),
                           bundle=str(tmp_path / "bundle.txt"), input_identity=lambda: {},
                           receipt_completion_version=2, profile_obj=None)
    reg = {"audit_limits": {"worker_output_tokens": 4_000, "integration_output_tokens": 4_000},
           "receipt": {"max_output_tokens": 4_000}}
    return spec, reg, {"reconciled_full": None, "completed_core": None, "report": None}


AUDITED = ("reconcile_full", "report", "report_regate", "report_regate_with_v8_report")


def test_the_requests_that_carry_the_audit_keep_the_larger_carry(tmp_path):
    m, (spec, reg, files) = _stub_runtime(), _stub_run(tmp_path)
    settings, bound = {"max_tokens": 96_000, "name": "fictional"}, sweep.findings_bound(2, reg["audit_limits"])
    measure = lambda floor: sweep.measure_ordinary(m, "P", spec, settings, reg, files, 2, floor)
    # A floor far above the caps' bound is carried as bytes, with no placeholder
    # but the regate's report as written.
    out, bases = measure("a" * 200_000)
    assert {p: bases[p] for p in AUDITED} == {p: "workers' smallest responses, assembled" for p in AUDITED}
    assert [out[p][1] for p in AUDITED] == [0, 0, 96_000, 0]
    assert all("a" * 200_000 in json.dumps(out[p][0]) for p in AUDITED)
    # A floor below the caps' bound loses to it.
    out, bases = measure("a" * 100)
    assert {p: bases[p] for p in AUDITED} == {p: "registered output caps" for p in AUDITED}
    assert [out[p][1] for p in AUDITED] == [bound, bound, bound + 96_000, bound]
    out, bases = measure(None)
    assert set(bases.values()) == {"registered output caps"} and out["full"][1] == 0


def test_integration_carries_the_larger_of_the_caps_and_the_floor_envelopes():
    m, omission = _stub_runtime(), {"max_tokens": 4_000}
    workers = [{"max_output_tokens": 4_000}] * 3
    empty, floored = {"messages": [], "max_tokens": 4_000}, {"messages": ["e" * 100_000], "max_tokens": 4_000}
    alternatives = sweep.integration_alternatives(m, workers, omission, [empty, floored])
    assert [a[2] for a in alternatives] == [16_000, 4_000] and alternatives[1][4] is floored
    chosen = sweep.larger_carry("CHORUS", "typed_audit_integration", alternatives)
    assert chosen[3] == "workers' smallest responses, as saved envelopes"
    assert len(sweep.integration_alternatives(m, workers, omission, [empty])) == 1


def test_the_output_allowance_must_cover_every_stage_admission():
    # Every worker's cap is the largest floor (30); before the third worker 30
    # is spent, so 60; omission and integration add their caps to 60.
    assert sweep.peak_output_need([10, 20, 30], 4, 4) == 64
    # The largest first: the second worker's admission reserves its full cap.
    assert sweep.peak_output_need([100, 10], 4, 4) == 200
    assert sweep.peak_output_need([5], 4_000, 4_000) == 4_005
    row = {"ceiling_tokens": 850_000, "estimated_in_flight_tokens": 816_145, "ratio": 0.3545}
    assert sweep.room_per_row(row, 554) == round(33_855 / 0.3545 / 554)


def _summary_results():
    est = lambda phase, size, cap, placeholder=0, **more: {
        **sweep.estimate("CHORUS", phase, size, cap, placeholder_tokens=placeholder), **more}
    floor = {"bytes": 40_000, "variant": "revised", "passed": True,
             "worker_check_minimum": {"bytes": 30_000, "variant": "revised", "passed": True}}
    workers = [{"worker_id": f"worker_000{i}", "paths": 100 + i, "response_floor": floor,
                **est("typed_audit_worker", 2_000_000 + i, 4_000)} for i in (1, 2)]
    basis = "workers' smallest responses, assembled"
    stages = {"typed_audit_omission": est("typed_audit_omission", 1_500_000, 4_000),
              "typed_audit_integration": est("typed_audit_integration", 1_900_000, 4_000, 4_000,
                                             carry_basis="workers' smallest responses, as saved envelopes"),
              "full_receipt_completion_after_readdress": est("full_receipt_completion_after_readdress", 1_000_000,
                                                             4_000, 8_000),
              "report": est("report", 1_000_000, 96_000, carry_basis=basis),
              "report_regate": est("report_regate", 1_000_000, 96_000, 96_000, carry_basis=basis),
              "report_regate_with_v8_report": {**est("report_regate", 1_010_000, 96_000, carry_basis=basis),
                                               "phase": "report_regate"}}
    limits = {"aggregate_input_tokens": 4_000_000, "aggregate_output_tokens": 100_000, "worker_output_tokens": 4_000,
              "omission_output_tokens": 4_000, "integration_output_tokens": 4_000}
    run = {"status": "MEASURED", "typed": {"status": "MEASURED", "worker_count": 2, "workers": workers},
           "stages": stages, "audit_limits": limits, "staging": {"original_full": {
               "conformance_edits": ["/a/0/b (wrapped)", "/c (joined)"], "source_bytes": 1_000, "staged_bytes": 990}}}
    return {"grid": {"G2": {"max_paths": 192, "max_inventory_bytes": 32_768, "max_workers": 16}},
            "projects": {"CHORUS": {"status": "MEASURED", "primary": "L", "record_project": "CHORUS",
                                    "proxy": False, "runs": {"L|G2": run}}}}


def test_the_summary_marks_floor_carries_and_derives_the_output_tables():
    out = sweep.summary(_summary_results())
    first = next(line for line in out.splitlines() if line.startswith("| CHORUS | ") and "(1)" in line)
    assert first.count("†") == 3                       # integration, report and regate carry the floor
    assert "| CHORUS | 10,000 / 7,500 (102) |" in out    # the largest floor and the worker-check minimum
    assert "| CHORUS | 24,000 (20,000) |" in out         # the admission peak: 10,000 + 10,000 + 4,000
    assert "| CHORUS `L` | 2: 1 / 0 / 1 / 0 |" in out and "| CHORUS | 203 |" in out


def test_a_foreign_checkout_on_the_import_path_is_filtered(tmp_path):
    root, other = tmp_path / "root", tmp_path / "other"
    for base in (root, other):
        (base / "src" / "data_sheets_schema").mkdir(parents=True)
    assert not sweep.foreign_path(str(root), root) and not sweep.foreign_path(str(root / "src"), root)
    assert sweep.foreign_path(str(other / "src"), root)
    assert not sweep.foreign_path(str(tmp_path / "missing"), root)
