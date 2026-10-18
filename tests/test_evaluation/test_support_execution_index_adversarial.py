"""Independent offline join controls; invented bytes are not calibration.

The real durable execution writer uses an in-process byte supplier. The inherited
planner fixture forbids all network/provider access, including during replay.
"""

from copy import deepcopy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import nested_support_execution as execution
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema import support_plan
from data_sheets_schema import top_level_fitness_results as fitness
from tests.test_evaluation.test_nested_support_execution import declaration, reply
from tests.test_evaluation.test_nested_support_plan import build
from tests.test_evaluation.test_support_plan import fixture, rewrite_roster  # noqa: F401
from tests.test_evaluation.test_top_level_fitness_results import prepared  # noqa: F401


def snapshot(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def chosen(manifest, *, record_id=None):
    targets = [row for row in manifest["targets"] if row["axis"] == "grounding_v3"
               and (record_id is None or row["record_id"] == record_id)]
    # Include a relationship and explicit false/zero values, rather than only
    # nonempty strings that could mask a truthiness-based denominator bug.
    selected = [next(row for row in targets if row["kind"] == "relationship_edge")]
    selected += [next(row for row in targets if row["pointer"] == pointer)
                 for pointer in ("/enabled", "/count")]
    return [{"target_id": row["id"], "attempt_id": f"support-{i}"}
            for i, row in enumerate(selected)]


def make_case(plan, selections, root, monkeypatch, *, stop_after_one=False):
    root.mkdir()
    descriptor, registration, output = root / "descriptor", root / "registration", root / "run"
    description = saved.prepare(plan, descriptor, selections=selections, protocol=saved.FORMAT)
    declared = declaration({"url": "http://127.0.0.1:9/v1/messages"}, output)
    declared["registration_id"] = "invented-" + root.name
    count = len(selections)
    declared["limits"].update(max_calls=count, total_response_bytes=count * 50_001,
                              input_scheduling_threshold=100 if stop_after_one else count * 100,
                              output_scheduling_threshold=count * 1000)
    declaration_path = root / "declaration.json"
    declaration_path.write_bytes(support_plan.canonical(declared))
    registered = execution.prepare(descriptor, declaration_path, registration)
    calls = []
    raw = support_plan.canonical(reply())

    def run(*, status=200, admission_only=False, before_admission=False):
        def dispatch(*args):
            calls.append(args[1])
            if admission_only:
                raise OSError("invented interruption after admission")
            return {"status_code": status, "request_id": "invented", "body_complete": True,
                    "failure": None, "duration_seconds": 0, "stage": "complete"}, raw
        monkeypatch.setattr(execution, "_dispatch", dispatch)
        if before_admission:
            original = execution._exclusive
            def stop(path, data):
                if path.name == "admitted.json":
                    raise OSError("invented interruption before admission")
                return original(path, data)
            with monkeypatch.context() as patch:
                patch.setattr(execution, "_exclusive", stop)
                return execution.run(registration)
        return execution.run(registration)

    def standalone(*, name="saved", attempt_id=None):
        attempt_id = attempt_id or selections[0]["attempt_id"]
        response = root / (name + ".json")
        response.write_bytes(saved.package_response((descriptor / "descriptor.json").read_bytes(),
            attempt_id=attempt_id, native_message=raw))
        destination = root / name
        value = saved.accept(descriptor, response, destination, attempt_id=attempt_id)
        return destination, value

    return SimpleNamespace(root=root, descriptor=descriptor, registration=registration,
                           output=output, description=description, registered=registered,
                           calls=calls, run=run, standalone=standalone)


@pytest.fixture
def case(prepared, tmp_path, monkeypatch):
    return make_case(prepared[1], chosen(prepared[2]), tmp_path / "support", monkeypatch)


def index(case, prepared, *, name="index", results=()):
    destination = case.root / name
    value = fitness.build_index(prepared[-2], [], destination,
                                support_execution=case.output, support_results=results)
    return destination, value


@pytest.mark.parametrize("before", [False, True])
def test_admission_unknown_and_never_started_keep_distinct_spent_values(case, prepared, before):
    with pytest.raises(OSError, match="invented interruption"):
        case.run(admission_only=not before, before_admission=before)
    _, value = index(case, prepared)
    rows = value["support_rows"]
    assert len(rows) == 3
    assert [row["state"] for row in rows] == ["missing"] * 3
    assert [row["dispatch_state"] for row in rows] == (
        ["not_started"] * 3 if before else ["spent_unknown", "not_started", "not_started"])
    assert rows[0]["spent"] is (False if before else True)
    assert all(row["spent"] is False for row in rows[1:])
    assert all(row["assessment"] is None for row in rows)
    assert value["strata"]["relationship_edge"] == {
        "selected": 1, "accepted": 0, "rejected": 0, "missing": 1}
    assert value["strata"]["attribute_value"] == {
        "selected": 2, "accepted": 0, "rejected": 0, "missing": 2}
    # Unexecuted fitness remains caller-saved/unknown; support does not alter it.
    assert all(row["spent"] is None and row["dispatch_state"] == "unknown"
               for row in value["fitness_rows"])
    assert value["scientific_scoring_eligible"] is False
    assert len(case.calls) == (0 if before else 1)


def test_false_and_zero_targets_survive_stopping_with_missing_responses(prepared, tmp_path, monkeypatch):
    case = make_case(prepared[1], chosen(prepared[2]), tmp_path / "limited", monkeypatch,
                     stop_after_one=True)
    case.run()
    _, value = index(case, prepared)
    by_pointer = {row["pointer"]: row for row in value["support_rows"]}
    assert set(by_pointer) == {"/creators/0", "/enabled", "/count"}
    for pointer in ("/enabled", "/count"):
        assert by_pointer[pointer]["state"] == "missing"
        assert by_pointer[pointer]["dispatch_state"] == "not_started"
        assert by_pointer[pointer]["spent"] is False
        assert by_pointer[pointer]["assessment"] is None
    assert value["strata"]["attribute_value"]["selected"] == 2
    assert value["strata"]["attribute_value"]["missing"] == 2
    assert len(case.calls) == 1


def test_v1_remains_supplied_only_and_keeps_its_original_row_shape(case, prepared):
    case.run(status=429)
    standalone, saved_result = case.standalone()
    old = fitness.build_index(prepared[-2], [], case.root / "v1", support_results=[standalone])
    explicit = fitness.build_index(prepared[-2], [], case.root / "explicit-v1",
                                   support_results=[standalone], support_execution=None)
    assert old == explicit
    assert snapshot(case.root / "v1") == snapshot(case.root / "explicit-v1")
    assert old["format"] == "top_level_fitness_index_v1"
    assert set(old) == {"format", "descriptor", "plan", "result_artifacts", "support_result_artifacts",
                        "fitness_rows", "support_rows", "strata", "support_count_basis", "execution",
                        "mode", "approval_basis", "scientific_scoring_eligible", "readiness", "limitations"}
    binding = saved_result["binding"]
    assert old["support_rows"] == [{
        "record_id": binding["record_id"], "target_id": saved_result["target_id"],
        "attempt_id": saved_result["attempt_id"], "kind": "relationship_edge",
        "pointer": "/creators/0", "state": "accepted", "assessment": saved_result["assessment"],
        "result": old["support_result_artifacts"][0],
        "fitness_target_links": [row["target_id"] for row in old["fitness_rows"]
                                 if row["pointer"] == "/creators"],
        "fitness_propagated": False}]
    assert old["strata"]["relationship_edge"] == {"accepted": 1}
    assert old["strata"]["attribute_value"] == {}
    assert fitness.recheck_index(case.root / "v1") == old
    _, actual = index(case, prepared, results=[standalone])
    assert actual["support_rows"][0]["assessment"]["status"] == "accepted"
    assert actual["support_rows"][0]["state"] == "rejected"
    assert actual["support_rows"][0]["dispatch_state"] == "failed"
    assert actual["strata"]["relationship_edge"]["accepted"] == 0
    assert actual["strata"]["attribute_value"]["missing"] == 2


def test_same_record_and_targets_from_another_plan_cannot_join(prepared, tmp_path, monkeypatch):
    other_plan = tmp_path / "other-plan"
    alternate = build((prepared[0], other_plan), max_tokens=418)
    case = make_case(other_plan, chosen(alternate), tmp_path / "other-support", monkeypatch)
    case.run()
    assert chosen(alternate) == chosen(prepared[2])
    assert alternate["records"][0]["record"] == prepared[2]["records"][0]["record"]
    before = snapshot(case.output)
    with pytest.raises(ValueError, match="same plan|another plan|plan.*differs"):
        index(case, prepared)
    assert not (case.root / "index").exists()
    assert snapshot(case.output) == before


@pytest.mark.parametrize("association", ["duplicate", "alternate_attempt", "unstarted"])
def test_supplied_result_cannot_add_an_attempt_outside_the_execution(case, prepared, association):
    case.run(status=429)
    if association == "alternate_attempt":
        descriptor = case.root / "alternate-descriptor"
        target = case.description["selections"][0]["target_id"]
        saved.prepare(prepared[1], descriptor,
                      selections=[{"target_id": target, "attempt_id": "unregistered-retry"}],
                      protocol=saved.FORMAT)
        response = case.root / "alternate-response.json"
        response.write_bytes(saved.package_response((descriptor / "descriptor.json").read_bytes(),
            attempt_id="unregistered-retry", native_message=support_plan.canonical(reply())))
        supplied = case.root / "alternate-result"
        saved.accept(descriptor, response, supplied, attempt_id="unregistered-retry")
    else:
        aid = case.description["selections"][1 if association == "unstarted" else 0]["attempt_id"]
        supplied, _ = case.standalone(attempt_id=aid)
    paths = [supplied, supplied] if association == "duplicate" else [supplied]
    before = snapshot(case.output)
    with pytest.raises(ValueError, match="duplicate support attempt|differs from its actual execution ledger"):
        index(case, prepared, results=paths)
    assert not (case.root / "index").exists()
    assert snapshot(case.output) == before


def test_unselected_record_cannot_join_even_with_identical_dataset_bytes(fixture, tmp_path, monkeypatch):
    source, plan_path = fixture
    (source / "second.yaml").write_bytes((source / "record.yaml").read_bytes())
    provenance = yaml.safe_load((source / "provenance.yaml").read_bytes())
    provenance["run"]["label"] = "second_rep1"
    (source / "second-provenance.yaml").write_text(yaml.safe_dump(provenance))
    def add(roster):
        jobs = deepcopy(roster["jobs"])
        for job in jobs:
            job.update(id="second_" + job["id"], input="second.yaml", label="second_rep1",
                       provenance="second-provenance.yaml")
        roster["jobs"] += jobs
        roster["pinned_files"]["second.yaml"] = support_plan.sha256((source / "second.yaml").read_bytes())
    rewrite_roster(source, add)
    manifest = build(fixture, max_tokens=417)
    first, second = manifest["records"]
    assert first["record"]["sha256"] == second["record"]["sha256"]
    fitness_target = next(row for row in manifest["targets"]
                          if row["record_id"] == first["id"] and row["axis"] == "fitness")
    descriptor = tmp_path / "fitness-selected-first"
    fitness.prepare(plan_path, descriptor,
                    selections=[{"target_id": fitness_target["id"], "attempt_id": "fitness-only"}],
                    protocol=fitness.FORMAT)
    case = make_case(plan_path, chosen(manifest, record_id=second["id"]), tmp_path / "second", monkeypatch)
    case.run()
    destination = tmp_path / "wrong-record-index"
    with pytest.raises(ValueError, match="exact record|selected.*record|same plan"):
        fitness.build_index(descriptor, [], destination, support_execution=case.output)
    assert not destination.exists()


def replace_pin(directory, pin, value):
    raw = support_plan.canonical(value)
    changed = {**pin, "sha256": support_plan.sha256(raw), "bytes": len(raw)}
    (directory / "artifacts" / changed["sha256"]).write_bytes(raw)
    return changed


@pytest.mark.parametrize("mutation", ["row_dropped", "false_spent", "none_spent", "dispatch_count",
                                      "plan", "record", "attempt", "saved_report", "admission"])
def test_rehashed_ledger_or_derived_claims_cannot_override_captured_dispatch(case, prepared, mutation):
    case.run(status=429)
    destination, value = index(case, prepared)
    changed = deepcopy(value)
    row = changed["support_rows"][0]
    if mutation == "row_dropped":
        changed["support_rows"].pop()
        changed["strata"]["attribute_value"]["selected"] -= 1
        changed["strata"]["attribute_value"]["missing"] -= 1
    elif mutation in {"false_spent", "none_spent"}:
        row["spent"] = False if mutation == "false_spent" else None
    elif mutation == "dispatch_count":
        counts = changed["support_dispatch_counts"]["relationship_edge"]
        counts["accepted"], counts["failed"] = 1, 0
    elif mutation == "plan":
        changed["plan"]["sha256"] = "f" * 64
    elif mutation == "record":
        row["record"]["sha256"] = "f" * 64
    elif mutation == "attempt":
        row["attempt_id"] = "unregistered-retry"
    elif mutation == "saved_report":
        metadata = changed["support_execution"]
        report = deepcopy(metadata["report"])
        report["all_selected_accepted"] = True
        report["rows"][0]["status"] = "accepted"
        metadata["saved_report"] = replace_pin(destination, metadata["saved_report"], report)
        metadata["report"] = report
    else:
        entry = changed["support_execution"]["ledger"]["attempts"][0]
        admission = json.loads((destination / "artifacts" / entry["admitted"]["sha256"]).read_bytes())
        admission["attempt_id"] = "unregistered-retry"
        entry["admitted"] = replace_pin(destination, entry["admitted"], admission)
    (destination / "index.json").write_bytes(support_plan.canonical(changed))
    with pytest.raises(ValueError):
        fitness.recheck_index(destination)


def test_relocated_index_reads_only_its_captured_artifacts(case, prepared, tmp_path, monkeypatch):
    case.run()
    original, expected = index(case, prepared)
    portable = tmp_path / "portable"
    shutil.copytree(original, portable)
    before = snapshot(portable)
    for path in (prepared[0], prepared[1], prepared[-2], case.root):
        path.rename(path.with_name(path.name + "-retained"))
    read_bytes = Path.read_bytes
    def local_read(path):
        assert path.is_relative_to(portable), f"ambient artifact read: {path}"
        return read_bytes(path)
    def forbidden(*args, **kwargs):
        pytest.fail("portable index replay requested runtime, dispatch or original run")
    monkeypatch.setattr(Path, "read_bytes", local_read)
    monkeypatch.setattr(execution, "_identity", forbidden)
    monkeypatch.setattr(execution, "_dispatch", forbidden)
    monkeypatch.setattr(execution, "capture_run", forbidden)
    assert fitness.recheck_index(portable) == expected
    assert snapshot(portable) == before
