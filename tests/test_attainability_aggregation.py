"""Fictional source-reading fixtures; no empirical scores or scientific approval.

The actual v1 validator, captured aggregator and reporting entry points run.
Only existing corpus/campaign discovery is isolated in consumer tests.
"""
import copy
import hashlib
import importlib.util
import json
import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import attainability as at
from data_sheets_schema import attainability_aggregation as aa
from data_sheets_schema.chunking import DEFAULT_RULE
from data_sheets_schema.evaluation_context import PREDICATES, context_digest
from tests.test_reference_rescore import current_record, environment, runner

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    got = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(got)
    return got


def fixture(root, *, number=10, readings=None, routes=(), complete=False, draft=False,
            context=True, adjudicate=None):
    root.mkdir(parents=True, exist_ok=True)
    def write(name, raw):
        p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
        return aa.pin(name, raw)
    def json_file(name, obj):
        return write(name, aa.canonical(obj) + b"\n")
    decision = {"kind": "declared_curator", "actor": "FICTIONAL offline fixture",
                "reference": "urn:fictional:3046:no-scientific-approval", "recorded_at": "2026-01-01T00:00:00Z",
                "rationale": "Synthetic engineering control; this does not approve a source reading."}
    bundle_raw = b"FICTIONAL example for software tests; no empirical source claims.\n"
    bundle = write("bundle.txt", bundle_raw); bundle["md5"] = hashlib.md5(bundle_raw).hexdigest()
    rname = f"rubric{number}"
    rubric_path = f"data/rubric/{rname}.txt"
    rub = write(rubric_path, (ROOT / rubric_path).read_bytes())
    definition_path = f".claude/agents/d4d-{rname}-semantic.md"
    definition = write(definition_path, (ROOT / definition_path).read_bytes())
    schema_path = f"src/download/prompts/{rname}_semantic_schema.json"
    schema = write(schema_path, (ROOT / schema_path).read_bytes())
    dependencies = [write(p, (ROOT / p).read_bytes()) for p in (
        "src/data_sheets_schema/evaluation_context.py", "src/data_sheets_schema/judge_contract.py")]
    record = write("record.yaml", b"id: urn:fictional:dataset\nconforms_to_class: Dataset\ntitle: Fictional test\n")
    ctx = {p: True for p in PREDICATES} if context else None
    ctx_pin = json_file("context.json", ctx) if ctx is not None else None
    evaluation = current_record(root / "record.yaml", number, ctx)
    evaluation.update(project="CHORUS", label="fictional_rep1")
    evaluation["metadata"].update(input_sha256=record["sha256"], rubric_sha256=rub["sha256"],
                                  instrument_sha256=definition["sha256"])
    ev = json_file("CHORUS_fictional_evaluation.json", evaluation)
    provenance = json_file("provenance.json", {"inputs": {"bundle_path": bundle["path"], "bundle_md5": bundle["md5"],
        "bundle_sha256": bundle["sha256"]}, "outputs": {"full": record}})
    items = aa.roster((ROOT / rubric_path).read_bytes(), rname)
    target = "E1.2" if number == 10 else "Q2"
    readings = [(target, None, "supported")] if readings is None else readings
    _, lines = at._lines_by_chunk(bundle_raw.decode(), DEFAULT_RULE)
    chunk = lines[1][0]
    snippet = {"chunk": chunk, "lines": [1, 1], "sha256": at.snippet_sha256(lines, 1, 1)}
    entries = [{"rubric": rname, "item_id": item, "route": route, "status": status, "method": "curator",
                "evidence": {"snippets": [snippet] if status in aa.SUPPORT else []},
                "note": "Fictional software-test reading, not human scientific approval."}
               for item, route, status in readings]
    document = {"format": at.FORMAT, "format_version": at.FORMAT_VERSION, "bundle": bundle,
                "chunk_rule": DEFAULT_RULE, "rubrics": {rname: {"path": rubric_path, "sha256": rub["sha256"]}},
                "entries": entries}
    docpin = write("source.yaml", at.dump(document).encode())
    rules = [{"item_id": i["item_id"], "maximum": i["maximum"], "applies_to": i["applies_to"],
              "rule": "any_sufficient" if i["item_id"] == target and routes else "whole_item_only",
              "routes": list(routes) if i["item_id"] == target else [],
              "alternatives_complete": complete if i["item_id"] == target and routes else False,
              "justification": "Fictional alternative relation for software tests only; not an E1.1 policy."}
             for i in items]
    policy = {"format": "d4d-attainability-item-policy", "version": 1, "state": "draft" if draft else "declared",
        "rubric": rname, "rubric_source": rub, "scoring_contract": {"kind": "semantic-agent", "definition": definition,
            "output_schema": schema, "semantic_version": "3.0", "evaluator_contract_sources": dependencies},
        "roster_sha256": aa.roster_digest(rname, rub, items), "items": rules, "denominator_rule": aa.BASIS,
        "partial_interpretation": "positive_lower_bound_not_explicit_absence_v1", "decision": None if draft else decision}
    pp = json_file("policy.json", policy)
    adj = None
    if adjudicate is not None:
        refs = sorted([aa.entry_ref(docpin["sha256"], e) for e in entries if e["item_id"] == target], key=aa._ref_order)
        adj = json_file("adjudication.json", {"format": "d4d-attainability-adjudication", "version": 1,
            "policy": pp, "source_document": docpin, "predecessor_documents": [], "bundle": bundle, "rubric": rub,
            "chunk_rule_sha256": aa.sha(aa.canonical(DEFAULT_RULE)), "resolutions": [{"item_id": target, "route": None,
                "scope_entries": refs, "scope_sha256": aa.sha(aa.canonical(refs)), "resolved_status": adjudicate,
                "evidence": [snippet] if adjudicate in aa.SUPPORT else [], "decision": decision}]})
    row = {"evaluation": ev, "evaluated_input": record, "generation_provenance": provenance, "bundle": bundle,
           "source_document": docpin, "policy": pp, "adjudication": adj, "context": ctx_pin,
           "scope_binding": {"evaluation_scope_sha256": aa.sha(aa.canonical(evaluation["evaluation_scope"])),
              "declaration": "source_readings_cover_selected_subject_scope", "decision": decision}}
    selection = {"format": "d4d-attainability-report-selection", "version": 1, "rows": [row]}
    json_file("selection.json", selection)
    return root / "selection.json", evaluation, selection, document


def result(selection):
    closure = aa.capture(selection)
    return closure, aa.recheck_captured(closure)["rows"][0]


def item(row, key="E1.2"):
    return next(i for i in row["source_inventory"] if i["item_id"] == key)


def test_actual_capture_positive_private_returns_and_relocated_pure_recheck(tmp_path, monkeypatch):
    selection, evaluation, _, _ = fixture(tmp_path / "positive")
    before = {p: p.read_bytes() for p in selection.parent.rglob("*") if p.is_file()}
    closure, row = result(selection)
    assert len(row["source_inventory"]) == 50
    assert row["basis"]["attained"] == row["basis"]["attainable"] == 1
    assert row["basis"]["full_maximum"] == 50 and row["state"] == "partial_coverage"
    assert row["historical_bases"]["total"] == evaluation["overall_score"]["total_points"]
    assert row["reading_authentication"] == "not_verified"
    expected = aa.recheck_captured(closure)
    def refuse(*args, **kwargs):
        pytest.fail("ambient access in captured recheck")
    with monkeypatch.context() as m:
        for name in ("open", "read_bytes", "read_text", "resolve", "cwd"):
            m.setattr(Path, name, refuse)
        m.setattr(subprocess, "Popen", refuse); m.setattr(socket, "socket", refuse)
        m.setattr(at, "resolve_bytes", refuse)
        got = aa.recheck_captured(copy.deepcopy(closure))
        assert got == expected
        got["limitations"].clear(); got["rows"][0]["basis"]["eligible_item_ids"].clear()
        assert aa.recheck_captured(closure) == expected
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_real_shared_validator_basis_and_duplicate_order(tmp_path, monkeypatch):
    selection, _, data, document = fixture(tmp_path / "validator")
    bundle = data["rows"][0]["bundle"]
    raw = (selection.parent / bundle["path"]).read_bytes()
    rub = document["rubrics"]["rubric10"]
    rubric_raw = (ROOT / rub["path"]).read_bytes()
    captured = at._CapturedAttainabilityBytes(((bundle["path"], raw), (rub["path"], rubric_raw)))
    problems, checked = at._validate_captured_text(at.dump(document), captured=captured)
    assert problems == [] and checked.bundle_basis == {"source": "captured bytes", "path": "bundle.txt", "sha256": aa.sha(raw), "bytes": len(raw)}
    # Compare actual public live path on an absolute bundle, without replacing
    # either validator or resolver; the public rubric is the exact same bytes.
    live = copy.deepcopy(document); live["bundle"]["path"] = str(selection.parent / "bundle.txt")
    live_problems, loaded = at.validate_text(at.dump(live))
    assert live_problems == [] and loaded.bundle_basis == {"source": "file on disk", "path": live["bundle"]["path"]}
    assert checked.rubric_items == loaded.rubric_items
    with monkeypatch.context() as m:
        m.setattr(at, "resolve_bytes", lambda *a, **k: pytest.fail("captured fallback"))
        problems, checked = at._validate_captured_text("bundle: wrong\nbundle: twice\n", captured=captured)
        assert checked is None and problems[0].startswith("duplicate mapping key")
        problems, checked = at._validate_captured_text(at.dump(document), captured=at._CapturedAttainabilityBytes(()))
        assert checked is None and "captured bytes do not contain" in problems[0]


@pytest.mark.parametrize("whole", ["supported", "not_stated_in_source"])
@pytest.mark.parametrize("resolution", [None, "supported", "not_stated_in_source"])
def test_unregistered_extra_route_blocks_whole_assertion_and_adjudication(tmp_path, whole, resolution):
    selection, *_ = fixture(tmp_path / "extra", readings=[("E1.2", None, whole), ("E1.2", "UNREGISTERED", "supported")], adjudicate=resolution)
    _, row = result(selection)
    got = item(row)
    assert got["final_status"] == "unknown" and got["resolution_state"] == "unregistered_routes"
    assert not got["eligible"] and row["absent_positive_scores"] == []
    assert row["basis"]["percentage"] is None


@pytest.mark.parametrize("readings,complete,expected", [
    ([("a", "not_stated_in_source")], True, "unknown"),
    ([("a", "not_stated_in_source"), ("b", "unknown")], True, "unknown"),
    ([("a", "not_stated_in_source"), ("b", "supported")], False, "supported"),
    ([("a", "not_stated_in_source"), ("b", "not_stated_in_source")], True, "not_stated_in_source"),
    ([("a", "not_stated_in_source"), ("b", "not_stated_in_source")], False, "unknown"),
    ([(None, "unknown"), ("a", "supported")], False, "supported"),
    ([(None, "partly_supported"), ("a", "supported")], False, "supported"),
    ([(None, "not_stated_in_source"), ("a", "partly_supported")], True, "conflict"),
])
def test_real_route_combinations(tmp_path, readings, complete, expected):
    selection, *_ = fixture(tmp_path / "routes", readings=[("E1.2", r, s) for r, s in readings], routes=("a", "b"), complete=complete)
    _, row = result(selection)
    assert item(row)["final_status"] == expected


def test_actual_scoped_resolution_and_stale_document_refusal(tmp_path):
    selection, _, selected, document = fixture(tmp_path / "resolved", readings=[("E1.2", None, "not_stated_in_source"),
        ("E1.2", "a", "supported")], routes=("a",), complete=True, adjudicate="supported")
    closure, row = result(selection)
    assert item(row)["initial_status"] == "conflict" and item(row)["final_status"] == "supported"
    # New honestly pinned document; leave the original adjudication unchanged.
    changed = copy.deepcopy(document); changed["entries"][0]["note"] += " changed reading"
    raw = at.dump(changed).encode(); target = selection.parent / "changed-source.yaml"; target.write_bytes(raw)
    variant = copy.deepcopy(selected); variant["rows"][0]["source_document"] = aa.pin(target.name, raw)
    (selection.parent / "stale-selection.json").write_bytes(aa.canonical(variant))
    with pytest.raises(ValueError, match="adjudication identity mismatch: source_document"):
        aa.capture(selection.parent / "stale-selection.json")
    assert aa.recheck_captured(closure)["rows"][0] == row


@pytest.mark.parametrize("mutation", ["duplicate", "missing_scope", "extra_scope", "wrong_snippet"])
def test_adjudication_semantic_refusals_after_honest_repins(tmp_path, mutation):
    selection, _, selected, _ = fixture(tmp_path / "adjudication", adjudicate="supported")
    identity = selected["rows"][0]["adjudication"]
    a = json.loads((selection.parent / identity["path"]).read_bytes())
    if mutation == "duplicate":a["resolutions"].append(copy.deepcopy(a["resolutions"][0]))
    elif mutation == "missing_scope":a["resolutions"][0]["scope_entries"] = []
    elif mutation == "extra_scope":a["resolutions"][0]["scope_entries"].append(copy.deepcopy(a["resolutions"][0]["scope_entries"][0]))
    else:a["resolutions"][0]["evidence"][0]["sha256"] = "0" * 64
    raw = aa.canonical(a); p = selection.parent / "changed-adjudication.json"; p.write_bytes(raw)
    variant = copy.deepcopy(selected); variant["rows"][0]["adjudication"] = aa.pin(p.name, raw)
    q = selection.parent / "changed-selection.json"; q.write_bytes(aa.canonical(variant))
    with pytest.raises(ValueError, match="adjudication|scoped entries"):
        aa.capture(q)


def test_unknown_applicability_and_varied_maxima_are_separate(tmp_path):
    selected, ev, *_ = fixture(tmp_path / "unknown", readings=[("E4.4", None, "supported")], context=False)
    _, row = result(selected)
    assert item(row, "E4.4")["applicability"] == "unknown"
    assert row["historical_bases"]["adjusted_max"] == ev["overall_score"]["adjusted_max_points"] == 50
    assert row["basis"]["attainable"] == 0 and row["basis"]["percentage"] is None
    selected, *_ = fixture(tmp_path / "varied", number=20, readings=[("Q2", None, "supported"), ("Q5", None, "supported")])
    _, row = result(selected)
    assert row["basis"]["attained"] == row["basis"]["attainable"] == 6
    assert len(row["source_inventory"]) == 20 and row["basis"]["full_maximum"] == 88


def test_draft_no_implicit_policy_and_closure_bounds(tmp_path):
    selected, *_ = fixture(tmp_path / "draft", draft=True)
    closure, row = result(selected)
    assert row["state"] == "unavailable" and row["basis"]["percentage"] is None
    count = len(closure["blobs"]); size = sum(b["bytes"] for b in closure["blobs"])
    assert aa.recheck_captured(closure, limits=replace(aa.DEFAULT_LIMITS, blobs=count, decoded_bytes=size))
    for limits in (replace(aa.DEFAULT_LIMITS, blobs=count-1), replace(aa.DEFAULT_LIMITS, decoded_bytes=size-1),
                   replace(aa.DEFAULT_LIMITS, references=1), replace(aa.DEFAULT_LIMITS, depth=2),
                   replace(aa.DEFAULT_LIMITS, nodes=10), replace(aa.DEFAULT_LIMITS, dependency_depth=3)):
        with pytest.raises(ValueError):aa.recheck_captured(closure, limits=limits)
    with pytest.raises(ValueError):replace(aa.DEFAULT_LIMITS, rows=257)


def test_full_roster_missing_policy_item_and_changed_maximum_refuse(tmp_path):
    selected, _, selection, _ = fixture(tmp_path / "roster")
    identity = selection["rows"][0]["policy"]
    original = json.loads((selected.parent / identity["path"]).read_bytes())
    for mutation in ("missing", "maximum"):
        policy = copy.deepcopy(original)
        if mutation == "missing":policy["items"].pop()
        else:policy["items"][0]["maximum"] = 2
        raw = aa.canonical(policy); p = selected.parent / (mutation + "-policy.json");p.write_bytes(raw)
        variant = copy.deepcopy(selection);variant["rows"][0]["policy"] = aa.pin(p.name, raw)
        q = selected.parent / (mutation + "-selection.json");q.write_bytes(aa.canonical(variant))
        with pytest.raises(ValueError, match="roster|maxima"):aa.capture(q)


def test_actual_semantic_comparison_cli_default_and_opt_in(tmp_path, monkeypatch):
    selected, evaluation, selection, _ = fixture(tmp_path / "semantic")
    m = module("report_semantic_comparison")
    ev = selected.parent / selection["rows"][0]["evaluation"]["path"]
    raw = ev.read_bytes()
    original = m.report([ev])
    output = tmp_path / "semantic.md"
    monkeypatch.setattr(sys, "argv", ["report_semantic_comparison.py", str(ev), "--output", str(output), "--attainability-selection", str(selected)])
    m.main()
    assert output.read_text().startswith(original.rstrip("\n"))
    assert "Source-supported item basis" in output.read_text()
    sidecar = json.loads(Path(str(output) + ".attainability.json").read_bytes())
    assert aa.recheck_captured(sidecar["capture"]) == sidecar["report"]
    assert ev.read_bytes() == raw
    with pytest.raises(SystemExit):m.main()
    assert m.report([ev]) == original


def test_actual_arm_cli_score_consumer_and_default_render(tmp_path, monkeypatch):
    selected, _, selection, _ = fixture(tmp_path / "arm")
    m = module("arm_comparison")
    monkeypatch.setattr(m, "PROJECTS", ("CHORUS",))
    monkeypatch.setattr(m, "ARMS", (("fixture", "Fictional", "fictional", "offline", "reps"),))
    monkeypatch.setattr(m, "EVAL_DIRS", {"rubric10": selected.parent})
    monkeypatch.setattr(m, "generator_model", lambda *_: None)
    data = {"fixture": {"CHORUS": []}}
    monkeypatch.setattr(m, "collect", lambda: data)
    # Corpus sections are independent discovery, not the selected score/report
    # consumer. Keep them as stable literal fixture sections in both paths.
    for name in ("release_inventory_section", "replicate_structure_section", "nested_structure_section",
                 "omission_candidate_section", "entry_omission_section", "receipted_where_empty_section"):
        monkeypatch.setattr(m, name, lambda *a: ["Synthetic existing corpus section", ""])
    scores = {"rubric10": {"fixture": {"CHORUS": m.rubric_scores("fictional", "CHORUS")}}}
    original = m.render_markdown(data, scores)
    assert scores["rubric10"]["fixture"]["CHORUS"]
    out = tmp_path / "arm.md"
    monkeypatch.setattr(sys, "argv", ["arm_comparison.py", "--no-figures", "--output", str(out), "--attainability-selection", str(selected)])
    assert m.main() == 0
    assert out.read_text().startswith(original)
    assert "Source-supported item basis" in out.read_text()
    assert m.render_markdown(data, scores) == original


def test_actual_reference_report_callthrough_preserves_legacy_fields(environment, tmp_path, monkeypatch):
    root, manifest, job, _ = environment
    selected, evaluation, selection, _ = fixture(root / "aggregation")
    job = {**job, "output": "aggregation/CHORUS_fictional_evaluation.json", "input": "aggregation/record.yaml",
           "purpose": "primary", "cohort": "v7", "generation_rep": 1}
    manifest["jobs"] = [job]
    manifest["pinned_files"][job["input"]] = runner.digest(root / job["input"])
    runner.write_json(runner.PLAN / "manifest.json", manifest)
    runner.write_json(runner.PLAN / "attempts" / job["id"] / "fictional/receipt.json", {
        "status": "passed", "evaluation_sha256": runner.digest(root / job["output"]),
        "manifest_sha256": runner.digest(runner.PLAN / "manifest.json")})
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    monkeypatch.setattr(runner, "now", lambda: "fixed test clock")
    monkeypatch.setattr(runner, "run_job", lambda *a: pytest.fail("report must not call an evaluator"))
    original = runner.report_results(manifest)
    old_md = (runner.PLAN / "results.md").read_bytes(); old_json = (runner.PLAN / "results.json").read_bytes()
    destination = tmp_path / "new-report"
    monkeypatch.setattr(sys, "argv", ["reference_rescore.py", "report", "--attainability-selection", str(selected), "--report-output", str(destination)])
    assert runner.main() == 0
    after = json.loads((destination / "results.json").read_bytes())
    assert after.pop("attainability")["rows"][0]["basis"]["attainable"] == 1
    assert after == original
    assert (runner.PLAN / "results.md").read_bytes() == old_md
    assert (runner.PLAN / "results.json").read_bytes() == old_json
    assert "Source-supported item basis" in (destination / "results.md").read_text()


def repin_json(selection_path, selected, role, value, stem):
    """Retain old files and honestly readdress one selected JSON artifact."""
    raw = aa.canonical(value)
    path = selection_path.parent / (stem + '.json')
    path.write_bytes(raw)
    changed = copy.deepcopy(selected)
    changed['rows'][0][role] = aa.pin(path.name, raw)
    out = selection_path.parent / (stem + '-selection.json')
    out.write_bytes(aa.canonical(changed))
    return out


@pytest.mark.parametrize('mutation', ['instrument_pin', 'scope', 'input_hash', 'item_score', 'item_row', 'item_applicability'])
def test_missing_historical_evidence_is_unavailable_without_changing_old_bases(tmp_path, mutation):
    selected, evaluation, selected_doc, _ = fixture(tmp_path / mutation)
    original = copy.deepcopy(evaluation)
    if mutation == 'instrument_pin': evaluation['metadata'].pop('instrument_sha256')
    elif mutation == 'scope': evaluation.pop('evaluation_scope')
    elif mutation == 'input_hash': evaluation['metadata'].pop('input_sha256')
    elif mutation == 'item_score': evaluation['elements'][0]['sub_elements'][1]['score'] = None
    elif mutation == 'item_row': evaluation['elements'][0]['sub_elements'].pop()
    else: evaluation['elements'][0]['sub_elements'][1].pop('applicable')
    changed = repin_json(selected, selected_doc, 'evaluation', evaluation, 'historical')
    _, row = result(changed)
    assert row['state'] == 'unavailable'
    assert all(row['basis'][key] is None for key in ('attained', 'attainable', 'percentage'))
    assert row['basis']['eligible_item_ids'] == [] and row['absent_positive_scores'] == []
    assert row['historical_bases']['total'] == original['overall_score']['total_points']
    assert len(row['source_inventory']) == 50


@pytest.mark.parametrize('mode', ['validation_sha', 'validation_md5', 'missing', 'contradictory'])
def test_actual_generation_provenance_hash_boundaries(tmp_path, mode):
    selected, _, selected_doc, _ = fixture(tmp_path / mode)
    row = selected_doc['rows'][0]
    prov = json.loads((selected.parent / row['generation_provenance']['path']).read_bytes())
    output = prov['outputs']['full']; output.pop('sha256')
    if mode != 'missing':
        key = 'md5' if mode == 'validation_md5' else 'sha256'
        digest = hashlib.new(key, (selected.parent / row['evaluated_input']['path']).read_bytes()).hexdigest()
        prov['validation'] = {'passed': True, 'artifacts': {'full': {'path': output['path'], key: digest}}}
    if mode == 'contradictory':output['sha256'] = '0' * 64
    changed = repin_json(selected, selected_doc, 'generation_provenance', prov, 'generation')
    if mode == 'contradictory':
        with pytest.raises(ValueError, match='evaluated input hash mismatch'): result(changed)
    else:
        _, got = result(changed)
        assert got['basis']['attainable'] == (None if mode == 'missing' else 1)
        if mode == 'missing':assert any('evaluated-input hash' in r['detail'] for r in got['reasons'])


def test_historical_scope_implementation_never_runs_current_substitute(tmp_path, monkeypatch):
    selected, _, selected_doc, _ = fixture(tmp_path / 'historic-contract')
    policy = json.loads((selected.parent / selected_doc['rows'][0]['policy']['path']).read_bytes())
    different = b'# retained historical implementation, deliberately not executable\n'
    path = selected.parent / 'historical-context.py'; path.write_bytes(different)
    # Keep the recorded logical path: changed raw implementation is not today's
    # algorithm even when the declaration calls it by a familiar name.
    dep = policy['scoring_contract']['evaluator_contract_sources'][0]
    (selected.parent / dep['path']).write_bytes(different)
    policy['scoring_contract']['evaluator_contract_sources'][0] = aa.pin(dep['path'], different)
    changed = repin_json(selected, selected_doc, 'policy', policy, 'historic-policy')
    # A historical context grammar must not be run through today's normalizer.
    variant = json.loads(changed.read_bytes())
    raw = aa.canonical({'historical_predicate': {'value': 'recorded historical decision'}})
    context_path = selected.parent / 'historical-context.json'; context_path.write_bytes(raw)
    variant['rows'][0]['context'] = aa.pin(context_path.name, raw)
    changed.write_bytes(aa.canonical(variant))
    monkeypatch.setattr(aa, 'evaluation_contract', lambda *a: pytest.fail('historical implementation substituted'))
    _, got = result(changed)
    assert got['basis']['attainable'] is None and got['scope_sha256'] is None
    assert any(r['code'] == 'unsupported_historical_contract' for r in got['reasons'])


def test_missing_scope_declaration_is_unavailable_but_conflicting_scope_refuses(tmp_path):
    selected, _, selected_doc, _ = fixture(tmp_path / 'scope')
    for absent in (True, False):
        changed = copy.deepcopy(selected_doc)
        if absent:changed['rows'][0]['scope_binding'] = None
        else:changed['rows'][0]['scope_binding']['evaluation_scope_sha256'] = '0' * 64
        path = selected.parent / ('absent.json' if absent else 'wrong.json')
        path.write_bytes(aa.canonical(changed))
        if absent:
            _, row = result(path)
            assert row['basis']['percentage'] is None and row['scope_sha256'] is None
        else:
            with pytest.raises(ValueError, match='scope identity mismatch'):result(path)


def test_yaml_bounds_and_json_keys_remain_separate():
    assert aa._yaml(b'scoring: {0: absent, 1: present}\n', aa.DEFAULT_LIMITS) == {'scoring': {0: 'absent', 1: 'present'}}
    with pytest.raises(ValueError, match='keys must be strings'):aa.canonical({0: 'not JSON metadata'})
    with pytest.raises(ValueError, match='YAML node/depth'):aa._yaml(b'a: ' + b'[' * 65 + b'0' + b']' * 65, aa.DEFAULT_LIMITS)
    with pytest.raises(ValueError, match='cyclic'):aa._yaml(b'a: &a [*a]', aa.DEFAULT_LIMITS)


def test_output_protection_uses_every_consulted_yaml_pin_after_input_disappears(tmp_path, monkeypatch):
    selected, _, selection, document = fixture(tmp_path / 'protection')
    path = 'data/rubric/rubric20.txt'
    raw = (ROOT / path).read_bytes()
    extra = selected.parent / path
    extra.write_bytes(raw)
    document['rubrics']['rubric20'] = {'path': path, 'sha256': aa.sha(raw)}
    # This second v1 rubric has no corresponding JSON policy pin. It is still
    # a consulted source and must remain protected after the initial capture.
    source_raw = at.dump(document).encode()
    source = selected.parent / 'both-rubrics.yaml'; source.write_bytes(source_raw)
    selection['rows'][0]['source_document'] = aa.pin(source.name, source_raw)
    q = selected.parent / 'both-selection.json'; q.write_bytes(aa.canonical(selection))
    captured = aa.capture(q)
    prepared = {'capture': captured, 'report': aa.recheck_captured(captured)}
    retained = selected.parent / 'retained-rubric20.txt'
    extra.rename(retained)
    with monkeypatch.context() as m:
        m.setattr(Path, 'open', lambda *a, **k: pytest.fail('protected paths cannot reread source'))
        protected = aa.protected_paths(prepared)
    assert extra in protected
    with pytest.raises(ValueError, match='outside all inputs'):aa.write_new(extra, b'not a replacement', protected)
    assert not extra.exists() and retained.read_bytes() == raw
