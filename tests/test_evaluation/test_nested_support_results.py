"""Invented offline evidence verifies mechanics, never scientific accuracy."""
import copy
import hashlib
import json
from pathlib import Path
from datetime import date

from click.testing import CliRunner
import pytest

from data_sheets_schema import nested_support_results as results, support_plan, support_targets
from data_sheets_schema.cli.evaluate import evaluate
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_nested_support_plan import build


def encode(value):
    return json.dumps(value, sort_keys=True).encode()


def native(**changes):
    return {"id": "invented-message", "type": "message", "role": "assistant", "model": "judge",
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 12, "output_tokens": 23},
            "content": [{"type": "thinking", "thinking": "Invented test reasoning", "signature": "invented"},
                        {"type": "text", "text": json.dumps({"verdict": "supported", "reason": "Invented fixture response."})}],
            **changes}


@pytest.fixture
def plan(fixture):
    source, directory = fixture
    manifest = build(fixture, max_tokens=417)
    selections = [{"target_id": t["id"], "attempt_id": f"attempt-{i}"}
                  for i, t in enumerate(manifest["targets"]) if t["axis"] == support_targets.AXIS]
    return source, directory, manifest, selections


@pytest.fixture
def prepared(plan, tmp_path):
    source, directory, manifest, selections = plan
    descriptor = tmp_path / "descriptor"
    results.prepare(directory, descriptor, selections=selections, protocol=results.FORMAT)
    return source, directory, manifest, selections, descriptor


def attempt(prepared, tmp_path, response=None, *, index=0, name="attempt"):
    *_, selections, descriptor = prepared
    raw = encode(native() if response is None else response)
    path = tmp_path / (name + ".json")
    path.write_bytes(results.package_response((descriptor / "descriptor.json").read_bytes(),
        attempt_id=selections[index]["attempt_id"], native_message=raw))
    output = tmp_path / name
    value = results.accept(descriptor, path, output, attempt_id=selections[index]["attempt_id"])
    return value, output, raw


def replace_artifact(directory, pin, raw):
    new = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    (directory / "artifacts" / new["sha256"]).write_bytes(raw)
    return {**pin, **new}


def save_manifest(directory, manifest):
    (directory / "manifest.json").write_bytes(encode(manifest))


def test_real_cli_round_trip_keeps_subset_and_full_plan_distinct(plan, tmp_path):
    _, directory, manifest, selections = plan
    descriptor, output = tmp_path / "descriptor", tmp_path / "accepted"
    response = tmp_path / "response.json"
    before = {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    runner = CliRunner()
    selection = selections[0]
    commands = [
        ["support-results", "prepare", "--plan", str(directory), "--output", str(descriptor),
         "--protocol", results.FORMAT, "--select", selection["target_id"], selection["attempt_id"]],
        ["support-results", "accept", "--descriptor", str(descriptor), "--response", str(response),
         "--attempt", selection["attempt_id"], "--output", str(output)],
        ["support-results", "recheck", "--result", str(output)],
        ["support-results", "report", "--descriptor", str(descriptor), "--result", str(output)],
    ]
    for command in commands:
        if command[1] == "accept":
            response.write_bytes(results.package_response((descriptor / "descriptor.json").read_bytes(),
                attempt_id=selection["attempt_id"], native_message=encode(native())))
        checked = runner.invoke(evaluate, command)
        assert checked.exit_code == 0, checked.output
    report = json.loads(checked.output)
    assert report["all_selected_responses_accepted"] is True
    assert report["all_planned_nested_targets_selected"] is False
    assert report["all_planned_nested_responses_accepted"] is False
    assert report["full_plan_declared_counts"] == manifest["counts"]
    assert report["readiness"] == manifest["readiness"]
    assert report["readiness"]["ready_for_paid_run"] is False
    assert report["fitness"] == "separate_and_unscored"
    assert before == {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}


def test_all_kinds_are_reconstructed_and_reports_preserve_missing(prepared, tmp_path):
    *_, selections, descriptor = prepared
    empty = results.report(descriptor, [])
    assert sum(v["missing"] for v in empty["selected_counts"].values()) == len(selections)
    value, output, raw = attempt(prepared, tmp_path)
    assert value["assessment"]["status"] == "accepted"
    assert value["assessment"]["reasoning"][0]["thinking"] == "Invented test reasoning"
    assert (output / "artifacts" / value["response"]["sha256"]).read_bytes() == raw
    assert results.recheck(output) == value
    report = results.report(descriptor, [output])
    assert sum(v["accepted"] for v in report["selected_counts"].values()) == 1
    assert sum(v["missing"] for v in report["selected_counts"].values()) == len(selections) - 1
    assert set(report["selected_counts"]) == {"relationship_edge", "attribute_value"}


@pytest.mark.parametrize("mode", ["truncated", "unknown_stop", "wrong_model", "alias_model", "tool_and_text",
    "refusal_and_text", "two_text_blocks", "fenced", "trailing", "wrong_verdict", "blank_reason",
    "extra_verdict_key", "input_none", "output_none", "input_bool", "output_negative", "output_over_cap",
    "cache_bool", "usage_missing"])
def test_rejected_native_responses_preserve_raw_and_never_score(prepared, tmp_path, mode):
    response = native()
    if mode == "truncated": response["stop_reason"] = "max_tokens"
    elif mode == "unknown_stop": response["stop_reason"] = None
    elif mode in ("wrong_model", "alias_model"): response["model"] = "other" if mode == "wrong_model" else "judge-latest"
    elif mode in ("tool_and_text", "refusal_and_text"): response["content"].append({"type": "tool_use" if mode == "tool_and_text" else "refusal", "text": "declined"})
    elif mode == "two_text_blocks": response["content"].append({"type": "text", "text": " "})
    elif mode == "fenced": response["content"][-1]["text"] = "```json\n" + response["content"][-1]["text"] + "\n```"
    elif mode == "trailing": response["content"][-1]["text"] += " commentary"
    elif mode in ("wrong_verdict", "blank_reason", "extra_verdict_key"):
        verdict = {"verdict": "invented" if mode == "wrong_verdict" else "supported", "reason": " " if mode == "blank_reason" else "fixture"}
        if mode == "extra_verdict_key": verdict["score"] = 1
        response["content"][-1]["text"] = json.dumps(verdict)
    elif mode == "usage_missing": response.pop("usage")
    else:
        field, value = {"input_none": ("input_tokens", None), "output_none": ("output_tokens", None),
            "input_bool": ("input_tokens", True), "output_negative": ("output_tokens", -1),
            "output_over_cap": ("output_tokens", 418), "cache_bool": ("cache_read_input_tokens", False)}[mode]
        response["usage"][field] = value
    value, output, raw = attempt(prepared, tmp_path, response)
    assert value["assessment"]["status"] == "rejected"
    assert value["assessment"]["verdict"] is None
    assert value["assessment"]["usage"] == response.get("usage")
    assert results.recheck(output) == value
    assert (output / "artifacts" / value["response"]["sha256"]).read_bytes() == raw
    report = results.report(prepared[-1], [output])
    assert sum(v["rejected"] for v in report["selected_counts"].values()) == 1
    assert sum(v["accepted"] for v in report["selected_counts"].values()) == 0


@pytest.mark.parametrize("raw", [b'{"model":"judge","model":"other"}', b'NaN', b'\xff', b''])
def test_raw_parse_rejection_is_a_recheckable_saved_artifact(prepared, tmp_path, raw):
    path = tmp_path / "raw.json"
    path.write_bytes(results.package_response((prepared[-1] / "descriptor.json").read_bytes(),
        attempt_id=prepared[-2][0]["attempt_id"], native_message=raw))
    output = tmp_path / "rejected"
    value = results.accept(prepared[-1], path, output, attempt_id=prepared[-2][0]["attempt_id"])
    assert value["assessment"]["status"] == "rejected"
    assert results.recheck(output) == value
    assert (output / "artifacts" / value["response"]["sha256"]).read_bytes() == raw


@pytest.mark.parametrize("field", ["kind", "pointer", "value_sha256", "context_sha256", "specification_ref", "output_token_ceiling"])
def test_rehashed_manifest_target_claim_cannot_replace_reconstructed_authority(plan, tmp_path, field):
    _, directory, manifest, selections = plan
    row = next(t for t in manifest["targets"] if t["id"] == selections[0]["target_id"])
    row[field] = {"kind": "relationship_edge", "pointer": "/invented", "output_token_ceiling": 418}.get(field, "0" * 64)
    save_manifest(directory, manifest)
    with pytest.raises((results.ResultError, ValueError)):
        results.prepare(directory, tmp_path / "descriptor", selections=selections, protocol=results.FORMAT)
    assert not (tmp_path / "descriptor").exists()


def test_rehashed_inventory_is_compared_to_original_record_and_schema(plan, tmp_path):
    _, directory, manifest, selections = plan
    record = manifest["records"][0]
    doc = json.loads((directory / "artifacts" / record["inventory"]["sha256"]).read_bytes())
    doc["targets"][0]["context_sha256"] = "0" * 64
    new = replace_artifact(directory, record["inventory"], encode(doc))
    record["inventory"] = new
    for target in manifest["targets"]:
        if target["axis"] == support_targets.AXIS: target["inventory_artifact"] = new
    save_manifest(directory, manifest)
    with pytest.raises(results.ResultError, match="inventory differs"):
        results.prepare(directory, tmp_path / "descriptor", selections=selections, protocol=results.FORMAT)


def test_schema_and_bundle_changes_cannot_hide_behind_rehashed_pins(plan, tmp_path):
    _, directory, manifest, selections = plan
    source = manifest["schema"]["sources"][0]
    raw = (directory / "artifacts" / source["sha256"]).read_bytes().replace(b"range: integer", b"range: string")
    manifest["schema"]["sources"][0] = replace_artifact(directory, source, raw)
    save_manifest(directory, manifest)
    with pytest.raises(results.ResultError, match="specification differs"):
        results.prepare(directory, tmp_path / "descriptor", selections=selections, protocol=results.FORMAT)


def test_saved_evidence_is_self_contained_and_never_reads_ambient_schema(prepared, tmp_path, monkeypatch):
    from data_sheets_schema import schema_snapshot, schema_view, evaluation_model
    def forbidden(*args, **kwargs):
        pytest.fail("ambient schema/config/provider access is forbidden")
    monkeypatch.setattr(schema_snapshot, "capture_schema", forbidden)
    monkeypatch.setattr(schema_view, "resolve_import_path", forbidden)
    monkeypatch.setattr(evaluation_model, "evaluation_model_settings", forbidden)
    source = prepared[0]
    source.rename(tmp_path / "source-moved")
    value, output, _ = attempt(prepared, tmp_path)
    prepared[-1].rename(tmp_path / "descriptor-moved")
    assert results.recheck(output) == value


def test_each_artifact_path_is_read_once_per_operation(plan, tmp_path, monkeypatch):
    real, paths = results._file, []
    def once(path, limit):
        assert Path(path) not in paths, path
        paths.append(Path(path))
        return real(path, limit)
    monkeypatch.setattr(results, "_file", once)
    results.prepare(plan[1], tmp_path / "descriptor", selections=plan[-1], protocol=results.FORMAT)
    assert paths


@pytest.mark.parametrize("mutation", ["duplicate_target", "duplicate_record", "bool_count", "fitness_selection", "duplicate_attempt"])
def test_ambiguous_identity_or_denominator_refuses(plan, tmp_path, mutation):
    _, directory, manifest, selections = plan
    if mutation == "duplicate_target": manifest["targets"].append(copy.deepcopy(manifest["targets"][0]))
    elif mutation == "duplicate_record": manifest["records"].append(copy.deepcopy(manifest["records"][0]))
    elif mutation == "bool_count": manifest["counts"]["records"] = True
    elif mutation == "fitness_selection": selections[0]["target_id"] = next(t["id"] for t in manifest["targets"] if t["axis"] == "fitness")
    else: selections[1]["attempt_id"] = selections[0]["attempt_id"]
    save_manifest(directory, manifest)
    with pytest.raises(results.ResultError):
        results.prepare(directory, tmp_path / "descriptor", selections=selections, protocol=results.FORMAT)


@pytest.mark.parametrize("which", ["assessment", "binding", "raw"])
def test_rechecker_reconstructs_result_instead_of_trusting_saved_flags(prepared, tmp_path, which):
    value, output, _ = attempt(prepared, tmp_path)
    if which == "raw":
        (output / "artifacts" / value["response"]["sha256"]).write_bytes(encode(native(model="other")))
    elif which == "assessment":
        value["assessment"]["verdict"] = "contradicted"
        (output / "result.json").write_bytes(encode(value))
    else:
        value["binding"]["context_sha256"] = "0" * 64
        (output / "result.json").write_bytes(encode(value))
    with pytest.raises(results.ResultError): results.recheck(output)


def test_duplicate_attempts_are_not_silently_deduplicated(prepared, tmp_path):
    _, output, _ = attempt(prepared, tmp_path)
    with pytest.raises(results.ResultError, match="duplicate attempt"):
        results.report(prepared[-1], [output, output])


def test_output_alias_and_existing_destinations_preserve_evidence(prepared, tmp_path):
    descriptor = prepared[-1]
    response = tmp_path / "raw.json"
    response.write_bytes(encode(native()))
    link = tmp_path / "alias"
    link.symlink_to(descriptor, target_is_directory=True)
    for output in (descriptor, link / "new-output", response):
        with pytest.raises(results.ResultError):
            results.accept(descriptor, response, output, attempt_id=prepared[-2][0]["attempt_id"])
    assert response.read_bytes() == encode(native())
    assert not (descriptor / "new-output").exists()


def test_artifact_symlink_refuses_without_reading_outside_plan(plan, tmp_path):
    _, directory, manifest, selections = plan
    pin = manifest["schema"]["nested_specification"]
    path = directory / "artifacts" / pin["sha256"]
    outside = tmp_path / "outside.json"
    outside.write_bytes(path.read_bytes())
    path.rename(path.with_name(path.name + ".saved"))
    path.symlink_to(outside)
    with pytest.raises(results.ResultError):
        results.prepare(directory, tmp_path / "descriptor", selections=selections, protocol=results.FORMAT)


@pytest.mark.parametrize("field,value", [("descriptor_sha256", "0" * 64), ("target_id", "another-record:target"),
    ("attempt_id", "another-attempt"), ("request_sha256", "0" * 64), ("format", "legacy-cache-v2")])
def test_wrong_bound_envelopes_are_preserved_rejected(prepared, tmp_path, field, value):
    descriptor, selections = prepared[-1], prepared[-2]
    raw = encode(native())
    envelope = json.loads(results.package_response((descriptor / "descriptor.json").read_bytes(),
        attempt_id=selections[0]["attempt_id"], native_message=raw))
    envelope[field] = value
    response = tmp_path / "wrong-envelope.json"
    response.write_bytes(encode(envelope))
    output = tmp_path / "rejected-envelope"
    checked = results.accept(descriptor, response, output, attempt_id=selections[0]["attempt_id"])
    assert checked["assessment"]["status"] == "rejected"
    assert f"response_envelope_{field}_conflicts" in checked["assessment"]["problems"]
    assert (output / "artifacts" / checked["response"]["sha256"]).read_bytes() == raw
    assert (output / "artifacts" / checked["response_envelope"]["sha256"]).read_bytes() == response.read_bytes()
    assert results.recheck(output) == checked


def test_direct_native_json_is_preserved_but_not_accepted_without_binding(prepared, tmp_path):
    response = tmp_path / "direct-native.json"
    raw = encode(native())
    response.write_bytes(raw)
    output = tmp_path / "rejected-direct"
    checked = results.accept(prepared[-1], response, output, attempt_id=prepared[-2][0]["attempt_id"])
    assert checked["assessment"]["status"] == "rejected"
    assert checked["assessment"]["problems"] == ["direct_native_message_requires_explicit_binding_envelope"]
    assert checked["assessment"]["usage"] == native()["usage"]
    assert (output / "artifacts" / checked["response"]["sha256"]).read_bytes() == raw
    assert results.recheck(output) == checked


def test_envelope_from_another_target_cannot_be_relabeled_at_accept(prepared, tmp_path):
    selections, descriptor = prepared[-2:]
    path = tmp_path / "first-envelope.json"
    path.write_bytes(results.package_response((descriptor / "descriptor.json").read_bytes(),
        attempt_id=selections[0]["attempt_id"], native_message=encode(native())))
    checked = results.accept(descriptor, path, tmp_path / "second", attempt_id=selections[1]["attempt_id"])
    assert checked["assessment"]["status"] == "rejected"
    assert "response_envelope_target_id_conflicts" in checked["assessment"]["problems"]
    assert "response_envelope_attempt_id_conflicts" in checked["assessment"]["problems"]


def test_accepted_result_and_raw_envelope_cannot_cross_identical_record_values(fixture, tmp_path):
    import yaml
    from tests.test_evaluation.test_support_plan import rewrite_roster
    source, directory = fixture
    (source / "second.yaml").write_bytes((source / "record.yaml").read_bytes())
    provenance = yaml.safe_load((source / "provenance.yaml").read_bytes())
    provenance["run"]["label"] = "second_rep1"
    (source / "second-provenance.yaml").write_text(yaml.safe_dump(provenance))
    def add(roster):
        jobs = copy.deepcopy(roster["jobs"])
        for job in jobs:
            job.update(id="second_" + job["id"], input="second.yaml", label="second_rep1", provenance="second-provenance.yaml")
        roster["jobs"] += jobs
        roster["pinned_files"]["second.yaml"] = hashlib.sha256((source / "second.yaml").read_bytes()).hexdigest()
    rewrite_roster(source, add)
    manifest = build(fixture, max_tokens=417)
    selected = [next(t for t in manifest["targets"] if t["record_id"] == record["id"] and t["pointer"] == "/title")
                for record in manifest["records"]]
    assert selected[0]["request_sha256"] == selected[1]["request_sha256"]
    descriptors = []
    for i, target in enumerate(selected):
        path = tmp_path / f"descriptor-{i}"
        results.prepare(directory, path, selections=[{"target_id": target["id"], "attempt_id": "attempt"}], protocol=results.FORMAT)
        descriptors.append(path)
    envelope = tmp_path / "response.json"
    envelope.write_bytes(results.package_response((descriptors[0] / "descriptor.json").read_bytes(),
        attempt_id="attempt", native_message=encode(native())))
    first = tmp_path / "first"
    assert results.accept(descriptors[0], envelope, first, attempt_id="attempt")["assessment"]["status"] == "accepted"
    rejected = results.accept(descriptors[1], envelope, tmp_path / "second", attempt_id="attempt")
    assert rejected["assessment"]["status"] == "rejected"
    with pytest.raises(results.ResultError, match="another descriptor"):
        results.report(descriptors[1], [first])


def test_persisted_complete_request_bytes_are_checked_not_recreated_over_drift(prepared, tmp_path):
    descriptor = prepared[-1]
    value = json.loads((descriptor / "descriptor.json").read_bytes())
    pin = value["selections"][0]["binding"]["request"]
    (descriptor / "artifacts" / pin["sha256"]).write_bytes(b"{}")
    with pytest.raises(results.ResultError, match="digest differs"):
        results.report(descriptor, [])


def test_native_date_and_quoted_spelling_have_distinct_reconstructed_identity(fixture, tmp_path):
    from tests.test_evaluation.test_nested_support_plan import add_slot, change_record
    source, directory = fixture
    add_slot(source, "issued", {"range": "date"})
    change_record(source, {"issued": date(2026, 1, 2)})
    manifest = build(fixture, max_tokens=417)
    target = next(t for t in manifest["targets"] if t["axis"] == support_targets.AXIS and t["pointer"] == "/issued")
    descriptor = tmp_path / "date-descriptor"
    results.prepare(directory, descriptor, selections=[{"target_id": target["id"], "attempt_id": "date"}], protocol=results.FORMAT)
    assert b"issued: 2026-01-02" in (source / "record.yaml").read_bytes()
    raw = (source / "record.yaml").read_bytes().replace(b"issued: 2026-01-02", b"issued: '2026-01-02'")
    record = manifest["records"][0]
    record["record"] = replace_artifact(directory, record["record"], raw)
    record["record"]["recorded_hashes"]["sha256"] = hashlib.sha256(raw).hexdigest()
    roster = json.loads((directory / "artifacts" / manifest["roster"]["sha256"]).read_bytes())
    roster["pinned_files"]["record.yaml"] = hashlib.sha256(raw).hexdigest()
    manifest["roster"] = replace_artifact(directory, manifest["roster"], encode(roster))
    save_manifest(directory, manifest)
    with pytest.raises(results.ResultError, match="inventory differs"):
        results.prepare(directory, tmp_path / "wrong-date", selections=[{"target_id": target["id"], "attempt_id": "date"}], protocol=results.FORMAT)


def test_existing_planner_requests_match_pre_edit_captures(fixture):
    source, directory = fixture
    baseline = json.loads((Path(__file__).parents[1] / "fixtures/support_plans/pre_result_contract_requests.json").read_bytes())
    for version in (1, 2):
        output = directory.with_name(f"old-v{version}")
        manifest = support_plan.build_plan(source / "roster.json", output, root=source, profile="neutral",
            schema_path=source / "schema.yaml", model="judge", plan_version=version,
            artifact_kind="full" if version == 2 else None, max_tokens=417)
        assert manifest["counts"] == baseline[str(version)]["counts"]
        requests = {t["id"]: support_plan.materialize_request(output, t["id"]) for t in manifest["targets"]}
        assert requests == baseline[str(version)]["requests"]


def test_complete_invented_responses_do_not_certify_science_or_paid_readiness(prepared, tmp_path):
    paths = [attempt(prepared, tmp_path, index=i, name=f"saved-{i}")[1]
             for i in range(len(prepared[-2]))]
    report = results.report(prepared[-1], paths)
    assert report["all_planned_nested_responses_accepted"] is True
    assert report["scientific_accuracy"] == "unverified"
    assert report["full_record_schema_validation"] == "not_performed"
    assert report["readiness"] == prepared[2]["readiness"]
    assert report["readiness"]["ready_for_paid_run"] is False


def test_cli_preserves_rejection_and_recheck_does_not_upgrade_it(prepared, tmp_path):
    response = tmp_path / "native.json"
    response.write_bytes(encode(native()))
    output = tmp_path / "rejected"
    runner = CliRunner()
    checked = runner.invoke(evaluate, ["support-results", "accept", "--descriptor", str(prepared[-1]),
        "--response", str(response), "--attempt", prepared[-2][0]["attempt_id"], "--output", str(output)])
    assert checked.exit_code == 1
    assert "direct_native_message_requires_explicit_binding_envelope" in checked.output
    checked = runner.invoke(evaluate, ["support-results", "recheck", "--result", str(output)])
    assert checked.exit_code == 0
    assert json.loads(checked.output)["assessment"]["status"] == "rejected"
    assert response.read_bytes() == encode(native())


@pytest.mark.parametrize("mode", ["bundle", "provenance", "generator", "family"])
def test_selected_source_authority_is_rebuilt_not_just_rehashed(plan, tmp_path, mode):
    import yaml
    _, directory, manifest, selections = plan
    row = manifest["records"][0]
    if mode == "bundle":
        row["bundle"] = replace_artifact(directory, row["bundle"], b"FILE: another.txt\nUnsupported replacement.\n")
    elif mode == "provenance":
        pin = row["provenance"]
        value = yaml.safe_load((directory / "artifacts" / pin["sha256"]).read_bytes())
        value["run"]["label"] = "another_rep1"
        row["provenance"] = replace_artifact(directory, pin, yaml.safe_dump(value).encode())
    else:
        row["generator" if mode == "generator" else "same_family"] = "forged"
    save_manifest(directory, manifest)
    with pytest.raises(results.ResultError, match="bundle bytes|provenance identity|generator/family"):
        results.prepare(directory, tmp_path / "descriptor", selections=selections, protocol=results.FORMAT)


@pytest.mark.parametrize("model", [None, "independent-judge"])
def test_default_model_selection_comes_only_from_captured_config(fixture, tmp_path, monkeypatch, model):
    import yaml
    from data_sheets_schema import evaluation_model
    source, directory = fixture
    config = source / "evaluator.yaml"
    config.write_text(yaml.safe_dump({"version": 1, "model": model}))
    monkeypatch.setattr(evaluation_model, "CONFIG_PATH", config)
    manifest = build(fixture, model=None, max_tokens=417)
    selected = next(t for t in manifest["targets"] if t["axis"] == support_targets.AXIS)
    config.rename(source / "old-evaluator.yaml")
    descriptor = tmp_path / "descriptor"
    selections = [{"target_id": selected["id"], "attempt_id": "captured-config"}]
    value = results.prepare(directory, descriptor, selections=selections, protocol=results.FORMAT)
    assert value["selections"][0]["binding"]["model"] == manifest["model"]
    assert manifest["model"]["basis"] == ("defaults_to_generation_model" if model is None else "evaluation_config")
    manifest["model"]["basis"] = "explicit_override"
    save_manifest(directory, manifest)
    with pytest.raises(results.ResultError, match="model/basis"):
        results.prepare(directory, tmp_path / "wrong-basis", selections=selections, protocol=results.FORMAT)


def test_missing_captured_schema_import_cannot_resolve_from_ambient_package(plan, tmp_path):
    _, directory, manifest, selections = plan
    assert len(manifest["schema"]["sources"]) > 1
    manifest["schema"]["sources"] = manifest["schema"]["sources"][:1]
    save_manifest(directory, manifest)
    with pytest.raises(results.ResultError, match="outside the captured closure"):
        results.prepare(directory, tmp_path / "descriptor", selections=selections, protocol=results.FORMAT)


@pytest.mark.parametrize("mode", ["blocked_boolean", "inventory_boolean"])
def test_boolean_cannot_impersonate_reconstructed_integer_counts(fixture, tmp_path, mode):
    from tests.test_evaluation.test_nested_support_plan import change_record
    source, directory = fixture
    change_record(source, {"creators": [{"name": "Dana", "unknown": "x"}]})
    manifest = build(fixture, max_tokens=417)
    selections = [{"target_id": next(t["id"] for t in manifest["targets"] if t["axis"] == support_targets.AXIS),
                   "attempt_id": "first"}]
    if mode == "blocked_boolean":
        assert manifest["counts"]["blocked_by_axis"]["grounding_v3"] == 1
        manifest["counts"]["blocked_by_axis"]["grounding_v3"] = True
    else:
        manifest["records"][0]["support_targets_by_kind"]["relationship_edge"] = True
    save_manifest(directory, manifest)
    with pytest.raises(results.ResultError):
        results.prepare(directory, tmp_path / "descriptor", selections=selections, protocol=results.FORMAT)


@pytest.mark.parametrize("mode", ["invalid_base64", "duplicate_key", "surrogate", "extra_key"])
def test_malformed_envelope_or_unicode_preserves_exact_rejected_evidence(prepared, tmp_path, mode):
    descriptor_raw = (prepared[-1] / "descriptor.json").read_bytes()
    response = native(model="\ud800") if mode == "surrogate" else native()
    envelope = results.package_response(descriptor_raw, attempt_id=prepared[-2][0]["attempt_id"], native_message=encode(response))
    value = json.loads(envelope)
    if mode == "invalid_base64":
        value["message_base64"] = "?"
        envelope = encode(value)
    elif mode == "duplicate_key":
        envelope = envelope.rstrip()[:-1] + b',"format":"duplicate"}'
    elif mode == "extra_key":
        value["accepted"] = True
        envelope = encode(value)
    path = tmp_path / "response.json"
    path.write_bytes(envelope)
    output = tmp_path / "rejected"
    accepted = results.accept(prepared[-1], path, output, attempt_id=prepared[-2][0]["attempt_id"])
    assert accepted["assessment"]["status"] == "rejected"
    assert (output / "artifacts" / accepted["response_envelope"]["sha256"]).read_bytes() == envelope
    assert results.recheck(output) == accepted


def test_importing_offline_consumer_does_not_import_provider_or_api_runner():
    import os
    import subprocess
    import sys
    source = '''import importlib.abc, sys
class RejectProvider(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname == "anthropic" or fullname.startswith("anthropic.") or fullname == "data_sheets_schema.api_runner":
            raise AssertionError("offline consumer imported provider/runtime: " + fullname)
sys.meta_path.insert(0, RejectProvider())
from data_sheets_schema import nested_support_results
assert nested_support_results.FORMAT == "nested_support_result_v1"
'''
    checked = subprocess.run([sys.executable, "-c", source], env=os.environ.copy(), capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
