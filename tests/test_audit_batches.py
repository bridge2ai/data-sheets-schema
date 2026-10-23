"""Synthetic partition and explicit-integration contracts; no dataset fixtures."""
import ast
from copy import deepcopy
import hashlib
import inspect
import json

import pytest

from data_sheets_schema import audit_batches as batches


def encode(value):
    return batches.canonical_bytes(value)


def assertion():
    return {"source": "manual.txt", "chunk": "c003", "quote": "A synthetic source passage."}


def claim(text, *, verdict="supported", status="fact"):
    return {"text": text, "verdict": verdict, "attributed_to": [], "claim_status": status,
            "source_status": status, "evidence": [assertion()], "reason": "An explicit synthetic judgment."}


def finding(path="/name", *, remove=None):
    value = {"severity": "medium", "record": "full", "slot": path,
             "issue": "A model-authored synthetic finding.", "evidence": [assertion()], "review_paths": [path]}
    if remove is not None:
        value["remove_relationship"] = remove
    return value


def proposals(plan):
    rows = {r["path"]: r for r in plan["inventory"]["values"]}
    return {w["id"]: encode({"findings": [], "summary": "Synthetic worker proposal.", "source_review": {
        "artifact": "original_full", "sha256": plan["original_full_sha256"],
        "values": [{"path": p, "claims": [claim(rows[p]["text"])]} for p in w["paths"]]}}) for w in plan["workers"]}


def integration(plan, workers):
    index = batches.build_index(plan, workers)
    return {"kind": batches.INTEGRATION_KIND, "proposal_index_sha256": index["sha256"],
            "retain_other_rows_from_index_sha256": index["sha256"], "row_replacements": [],
            "finding_decisions": [{"id": f["id"], "previous_sha256": f["sha256"], "action": "retain",
                                   "reason": "Retain this explicit judgment.", "evidence": []} for f in index["findings"]],
            "new_findings": [], "summary": "The integration model's final summary."}


def revised_workers(plan):
    workers = proposals(plan)
    owner = next(w["id"] for w in plan["workers"] if "/name" in w["paths"])
    value = json.loads(workers[owner])
    row = next(r for r in value["source_review"]["values"] if r["path"] == "/name")
    row["claims"][0]["verdict"] = "revise"
    value["findings"] = [finding()]
    workers[owner] = encode(value)
    return workers


def rebind(plan):
    plan["sha256"] = batches.object_sha256({k: v for k, v in plan.items() if k != "sha256"})
    return plan


def codes(report):
    return {e["code"] for e in report["errors"]}


def test_plan_disjoint_whole_fields_and_original_inventory_order():
    raw = 'z:\n  - x: one\n    y: two\na: first\nb: false\nempty: []\nnullish: null\n'
    plan = batches.make_plan(raw, max_paths=2)
    assert plan["field_roots"] == ["/a", "/b", "/empty", "/nullish", "/z"]
    assert [w["roots"] for w in plan["workers"]] == [["/a", "/b", "/empty", "/nullish"], ["/z"]]
    assert plan["workers"][1]["paths"] == ["/z/0/x", "/z/0/y"]
    assert [r["path"] for r in plan["inventory"]["values"]] == ["/z/0/x", "/z/0/y", "/a", "/b"]
    batches.validate_plan(plan, raw)
    assert batches.make_plan(raw, max_paths=2) == plan
    output, lineage = batches.assemble(plan, proposals(plan), encode(integration(plan, proposals(plan))))
    assert [r["path"] for r in json.loads(output)["source_review"]["values"]] == [r["path"] for r in plan["inventory"]["values"]]
    assert len(lineage["rows"]) == 4


def test_packing_independent_of_dictionary_order_but_raw_identity_not():
    a = 'z: {second: two, first: one}\na: alpha\n'
    b = 'a: alpha\nz: {first: one, second: two}\n'
    pa, pb = batches.make_plan(a, max_paths=2), batches.make_plan(b, max_paths=2)
    assert pa["workers"] == pb["workers"]
    assert pa["sha256"] != pb["sha256"]
    assert pa["original_full_sha256"] != pb["original_full_sha256"]
    with pytest.raises(batches.AuditBatchError, match="plan_original_mismatch"):
        batches.validate_plan(pa, b)


def test_inventory_zero_false_dates_metadata_and_escaped_keys():
    raw = 'id: "https://example.invalid/set"\nconforms_to_class: Dataset\nobjects:\n- id: "https://example.invalid/set#one"\n  zero: 0\n  disabled: false\n  day: 2020-03-04\n"a/b~c": {"": present}\nnone: null\nblank: ""\n'
    plan = batches.make_plan(raw)
    rows = {r["path"]: r for r in plan["inventory"]["values"]}
    assert rows["/objects/0/zero"]["text"] == "0"
    assert rows["/objects/0/disabled"]["text"] == "false"
    assert rows["/objects/0/day"]["text"] == "2020-03-04"
    assert all(rows[p]["whole_value_required"] for p in ["/objects/0/zero", "/objects/0/disabled", "/objects/0/day"])
    assert rows["/objects/0/id"]["record_metadata_allowed"]
    assert not rows["/id"]["record_metadata_allowed"]
    assert "/a~1b~0c/" in rows
    assert "/none" not in rows and "/blank" not in rows
    # Compare inventory authority only; never call a production source validator.
    from data_sheets_schema.source_review import inventory
    assert plan["inventory"] == inventory(raw, "original_full")


@pytest.mark.parametrize("raw", ["{}", "empty: []\nnullish: null\nblank: ''\n"])
def test_empty_inventory_has_explicit_worker_and_no_invented_claim(raw):
    plan = batches.make_plan(raw)
    assert len(plan["workers"]) == 1 and plan["workers"][0]["paths"] == []
    workers = proposals(plan)
    result, lineage = batches.assemble(plan, workers, encode(integration(plan, workers)))
    assert json.loads(result)["source_review"]["values"] == [] and lineage["rows"] == []


@pytest.mark.parametrize("raw,code", [
    ('x: 1\nx: 2\n', 'record_duplicate_key'),
    ('1: value\n', 'record_key_invalid'),
    ('x: &loop [*loop]\n', 'original_cycle'),
    ('x: .nan\n', 'original_scalar_nonfinite'),
    ('x: !!binary SGk=\n', 'original_scalar_unsupported'),
    ('[one, two]', 'original_mapping_required'),
    ('x: {<<: {a: 1}}', 'record_key_invalid'),
    ('x: [', 'original_yaml_invalid'),
    ('x: 2020-99-99', 'original_yaml_invalid'),
])
def test_bad_original_fails_with_fixed_code(raw, code):
    with pytest.raises(batches.AuditBatchError, match=code):
        batches.make_plan(raw)


@pytest.mark.parametrize("key,value", [("max_paths", 0), ("max_paths", True), ("max_workers", 1.0), ("max_inventory_bytes", "100")])
def test_limits_are_positive_exact_integers(key, value):
    with pytest.raises(batches.AuditBatchError, match="plan_limits_invalid"):
        batches.make_plan('name: value', **{key: value})


def test_indivisible_lists_bytes_and_worker_count_fail_instead_of_truncate():
    with pytest.raises(batches.AuditBatchError, match="indivisible_field_bound"):
        batches.make_plan('terms: [one, two, three]', max_paths=2)
    with pytest.raises(batches.AuditBatchError, match="indivisible_field_bound"):
        batches.make_plan('name: ' + 'x' * 500, max_inventory_bytes=100)
    with pytest.raises(batches.AuditBatchError, match="worker_count_bound"):
        batches.make_plan('a: x\nb: y\nc: z', max_paths=1, max_workers=2)


def test_rehashed_forged_plan_cannot_change_ownership():
    plan = batches.make_plan('a: first\nb: second', max_paths=1)
    plan["workers"][0]["paths"] = ["/b"]
    rebind(plan)
    report = batches.check_worker(b'{}', plan, 'worker_0001')
    assert not report["passed"] and codes(report) == {"plan_workers"}
    with pytest.raises(batches.AuditBatchError):
        batches.validate_plan(plan, 'a: first\nb: second')


def test_worker_source_blindness_and_no_production_validator_imports():
    plan = batches.make_plan('name: initial')
    workers = proposals(plan)
    key = plan["workers"][0]["id"]
    value = json.loads(workers[key])
    row = value["source_review"]["values"][0]
    row["claims"][0].update(text="An unrelated literal the checker must not validate", claim_status="applied", source_status="applied")
    row["claims"][0]["evidence"][0]["quote"] = "No source bytes exist here."
    assert batches.check_worker(encode(value), plan, key)["passed"]
    imports = [ast.unparse(n) for n in ast.walk(ast.parse(inspect.getsource(batches))) if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not any(x in text for text in imports for x in ["source_review", "evidence_assertions", "api_runner", "httpx", "anthropic"])


@pytest.mark.parametrize("damage,code", [
    ("hash", "worker_original_digest"), ("missing", "worker_path_roster"),
    ("extra", "worker_path_roster"), ("duplicate", "duplicate_review_path")])
def test_worker_exact_roster_and_hash(damage, code):
    plan = batches.make_plan('name: first\nsize: second')
    workers = proposals(plan);key = next(iter(workers));value = json.loads(workers[key])
    if damage == "hash":value["source_review"]["sha256"] = "f" * 64
    if damage == "missing":value["source_review"]["values"].pop()
    if damage == "extra":value["source_review"]["values"].append({"path": "/other", "claims": [claim("Extra")]})
    if damage == "duplicate":value["source_review"]["values"].append(deepcopy(value["source_review"]["values"][0]))
    assert code in codes(batches.check_worker(encode(value), plan, key))


def test_worker_cannot_remove_another_owners_relationship():
    plan = batches.make_plan('name: first\nroles: [{name: second}]', max_paths=1)
    workers = proposals(plan);key = next(iter(workers));value = json.loads(workers[key])
    value["findings"] = [finding(remove={"path": "/roles/0", "identity": "/name"})]
    value["source_review"]["values"][0]["claims"][0]["verdict"] = "revise"
    assert "worker_removal_owner" in codes(batches.check_worker(encode(value), plan, key))


def test_index_binds_raw_whitespace_and_canonical_typed_rows():
    plan = batches.make_plan('name: first\nsize: 0', max_paths=1)
    workers = proposals(plan);index = batches.build_index(plan, workers)
    reordered = dict(reversed(list(workers.items())))
    assert batches.build_index(plan, reordered) == index
    key = next(iter(workers));workers[key] = json.dumps(json.loads(workers[key]), indent=4).encode()
    changed = batches.build_index(plan, workers)
    assert changed["sha256"] != index["sha256"] and changed["rows"] == index["rows"]
    assert batches.object_sha256({"x": False}) != batches.object_sha256({"x": 0})
    assert batches.object_sha256({"x": 0}) != batches.object_sha256({"x": 0.0})


def test_retain_assembly_preserves_exact_semantic_objects_and_inputs():
    plan = batches.make_plan('name: "Unicode λ \\n literal"\nsize: 0', max_paths=1)
    workers = proposals(plan);value = integration(plan, workers);before = deepcopy((plan, workers, value))
    raw, lineage = batches.assemble(plan, workers, encode(value))
    result = json.loads(raw)
    assert result["summary"] == value["summary"]
    expected_rows = {r["path"]: r for proposal in workers.values() for r in json.loads(proposal)["source_review"]["values"]}
    assert result["source_review"]["values"] == [expected_rows[r["path"]] for r in plan["inventory"]["values"]]
    assert (plan, workers, value) == before
    assert lineage["audit_sha256"] == hashlib.sha256(raw).hexdigest()
    assert lineage["integration_sha256"] == hashlib.sha256(encode(value)).hexdigest()


def test_model_replacement_and_new_finding_preserved_with_lineage():
    plan = batches.make_plan('name: Original\nother: unchanged', max_paths=1)
    workers = proposals(plan);index = batches.build_index(plan, workers);value = integration(plan, workers)
    old = next(r for r in index["rows"] if r["path"] == "/name")
    replacement = {"path": "/name", "claims": [claim("Original", verdict="revise", status="planned")]}
    value["row_replacements"] = [{"path": "/name", "previous_sha256": old["sha256"], "row": replacement,
                                  "reason": "Integration explicitly revises this judgment.", "evidence": [assertion()]}]
    value["new_findings"] = [finding()]
    raw, lineage = batches.assemble(plan, workers, encode(value))
    result = json.loads(raw)
    assert result["source_review"]["values"][0] == replacement
    assert result["findings"] == value["new_findings"]
    assert lineage["rows"][0]["origin"]["kind"] == "integration_replacement"
    assert lineage["rows"][1]["origin"]["kind"] == "worker"
    assert lineage["decision_assertions"] == [assertion()]


def test_finding_split_drop_and_retention_require_model_decisions():
    plan = batches.make_plan('name: Original')
    workers = revised_workers(plan);value = integration(plan, workers)
    assert batches.check_integration(encode(value), plan, workers)["passed"]
    value["finding_decisions"][0].update(action="replace", evidence=[assertion()], findings=[finding(), {**finding(), "issue": "Separate model-authored detail."}])
    raw, lineage = batches.assemble(plan, workers, encode(value))
    assert json.loads(raw)["findings"] == value["finding_decisions"][0]["findings"]
    assert [x["replacement_ordinal"] for x in lineage["findings"]] == [0, 1]
    # A drop cannot erase the sole finding while its retained row still says revise.
    decision = value["finding_decisions"][0];decision.pop("findings");decision["action"] = "drop"
    assert "revise_without_finding" in codes(batches.check_integration(encode(value), plan, workers))
    index = batches.build_index(plan, workers)
    value["row_replacements"] = [{"path": "/name", "previous_sha256": index["rows"][0]["sha256"],
        "row": {"path": "/name", "claims": [claim("Original")]}, "reason": "A documented reconsideration.", "evidence": [assertion()]}]
    raw, lineage = batches.assemble(plan, workers, encode(value))
    assert json.loads(raw)["findings"] == []
    assert lineage["finding_dispositions"][0]["action"] == "drop"


@pytest.mark.parametrize("damage,code", [
    ("index", "integration_index_digest"), ("attestation", "integration_index_digest"),
    ("missing_decision", "finding_decision_roster"), ("extra_decision", "finding_id_unknown"),
    ("duplicate_decision", "finding_decision_duplicate"), ("predecessor", "finding_predecessor_digest"),
    ("silent_drop", "text_nonempty"), ("drop_no_evidence", "array_nonempty"),
    ("unknown_action", "enum_value"), ("retain_with_replacement", "object_keys"),
    ("empty_replacement", "array_nonempty")])
def test_bad_decisions_fail_with_fixed_structural_codes(damage, code):
    plan = batches.make_plan('name: Original');workers = revised_workers(plan);value = integration(plan, workers)
    d = value["finding_decisions"][0]
    if damage == "index":value["proposal_index_sha256"] = "0" * 64
    if damage == "attestation":value["retain_other_rows_from_index_sha256"] = None
    if damage == "missing_decision":value["finding_decisions"] = []
    if damage == "extra_decision":value["finding_decisions"].append({**d, "id": "secret arbitrary id"})
    if damage == "duplicate_decision":value["finding_decisions"].append(deepcopy(d))
    if damage == "predecessor":d["previous_sha256"] = "0" * 64
    if damage == "silent_drop":d.update(action="drop", reason="", evidence=[assertion()])
    if damage == "drop_no_evidence":d.update(action="drop", evidence=[])
    if damage == "unknown_action":d["action"] = "choose_best"
    if damage == "retain_with_replacement":d["findings"] = [finding()]
    if damage == "empty_replacement":d.update(action="replace", evidence=[assertion()], findings=[])
    report = batches.check_integration(encode(value), plan, workers)
    assert not report["passed"] and code in codes(report)
    assert "secret arbitrary id" not in json.dumps(report)
    with pytest.raises(batches.AuditBatchError):batches.assemble(plan, workers, encode(value))


@pytest.mark.parametrize("damage,code", [
    ("unknown", "replacement_path_unknown"), ("different", "replacement_row_path"),
    ("duplicate", "replacement_path_duplicate"), ("predecessor", "replacement_predecessor_digest"),
    ("reason", "text_nonempty"), ("evidence", "array_nonempty")])
def test_bad_whole_row_replacements_fail(damage, code):
    plan = batches.make_plan('name: Original');workers = proposals(plan);index = batches.build_index(plan, workers);value = integration(plan, workers)
    item = {"path": "/name", "previous_sha256": index["rows"][0]["sha256"],
            "row": {"path": "/name", "claims": [claim("Original")]}, "reason": "Model replacement.", "evidence": [assertion()]}
    value["row_replacements"] = [item]
    if damage == "unknown":item["path"] = "/invented"
    if damage == "different":item["row"]["path"] = "/invented"
    if damage == "duplicate":value["row_replacements"].append(deepcopy(item))
    if damage == "predecessor":item["previous_sha256"] = "0" * 64
    if damage == "reason":item["reason"] = ""
    if damage == "evidence":item["evidence"] = []
    assert code in codes(batches.check_integration(encode(value), plan, workers))


def test_joint_removal_duplicate_and_ancestor_overlaps_are_rejected():
    plan = batches.make_plan('roles: [{name: A, description: B}]')
    workers = proposals(plan);value = integration(plan, workers)
    f = finding('/roles/0/name', remove={"path": "/roles/0", "identity": "/name"});f.pop('review_paths')
    value["new_findings"] = [f, deepcopy(f)]
    assert "removal_overlap" in codes(batches.check_integration(encode(value), plan, workers))
    value["new_findings"][1]["remove_relationship"] = {"path": "/roles/0/description"}
    assert "removal_overlap" in codes(batches.check_integration(encode(value), plan, workers))
    value["new_findings"] = [{**f, "remove_relationship": {"path": "/not_in_original"}}]
    assert "removal_root_unknown" in codes(batches.check_integration(encode(value), plan, workers))


def test_escaped_pointer_overlap_uses_tokens_not_text_prefix():
    plan = batches.make_plan('"a/b": [{name: A}]\na: [{name: B}]')
    workers = proposals(plan);value = integration(plan, workers)
    first = finding('/a~1b/0/name', remove={"path": "/a~1b/0", "identity": "/name"});first.pop('review_paths')
    second = finding('/a/0/name', remove={"path": "/a/0", "identity": "/name"});second.pop('review_paths')
    value["new_findings"] = [first, second]
    assert batches.check_integration(encode(value), plan, workers)["passed"]


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'NaN', b'"\\ud800"', b'\xff', b'[]', b'null', b'{'])
def test_malformed_input_reports_are_bounded_and_never_echo_payload(raw):
    plan = batches.make_plan('name: Original');workers = proposals(plan)
    for report in [batches.check_worker(raw, plan, 'worker_0001'), batches.check_integration(raw, plan, workers)]:
        assert not report['passed']
        assert len(report['errors']) <= 20 and len(json.dumps(report)) < 3000


def test_changed_raw_proposal_invalidates_prepared_integration():
    plan = batches.make_plan('name: Original');workers = proposals(plan);value = integration(plan, workers)
    workers['worker_0001'] += b'\n'
    assert 'integration_index_digest' in codes(batches.check_integration(encode(value), plan, workers))
    with pytest.raises(batches.AuditBatchError, match='proposal_roster'):
        batches.build_index(plan, {})


def test_empty_field_count_cannot_evade_preflight_bounds():
    raw = "\n".join(f"field_{i}: null" for i in range(batches.MAX_FIELD_ROOTS + 1))
    with pytest.raises(batches.AuditBatchError, match="field_count_bound"):
        batches.make_plan(raw)


@pytest.mark.parametrize("field", ["row_replacements", "finding_decisions", "new_findings", "summary", "kind", "proposal_index_sha256", "retain_other_rows_from_index_sha256"])
@pytest.mark.parametrize("bad", [None, True, 0, {}, []])
def test_integration_wrong_typed_fields_never_raise_or_leak(field, bad):
    plan = batches.make_plan("name: Original")
    workers = revised_workers(plan)
    value = integration(plan, workers)
    value[field] = bad
    report = batches.check_integration(encode(value), plan, workers)
    # Empty row replacements/new findings are valid for this retaining integration.
    if field in {"row_replacements", "new_findings"} and type(bad) is list:
        assert report["passed"]
    else:
        assert not report["passed"]
    assert len(report["errors"]) <= batches.MAX_ERRORS


def test_replacement_reports_do_not_echo_record_keys_or_candidate_text():
    plan = batches.make_plan("name: Original")
    workers = proposals(plan)
    index = batches.build_index(plan, workers)
    value = integration(plan, workers)
    value["row_replacements"] = [{"path": "/PRIVATE_SENTINEL", "previous_sha256": index["rows"][0]["sha256"],
        "row": {"path": "/PRIVATE_SENTINEL", "claims": [claim("PRIVATE_SENTINEL")]},
        "reason": "PRIVATE_SENTINEL", "evidence": []}]
    report = batches.check_integration(encode(value), plan, workers)
    assert not report["passed"]
    assert "PRIVATE_SENTINEL" not in json.dumps(report)
