"""Actual local transport and captured support joins; no calibration claims."""
import copy
import json
from pathlib import Path
import shutil
import socket
from types import SimpleNamespace
from urllib.parse import urlsplit

from click.testing import CliRunner
import pytest

from data_sheets_schema import nested_support_execution as execution
from data_sheets_schema import nested_support_results as support
from data_sheets_schema import top_level_fitness_results as fitness
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.support_plan import canonical
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_top_level_fitness_results import prepared, native  # noqa: F401
from tests.test_evaluation.test_nested_support_execution import peer, declaration, reply  # noqa: F401

_CONNECT = socket.socket.connect


@pytest.fixture
def case(prepared, peer, tmp_path, monkeypatch):
    endpoint = urlsplit(peer["url"])

    def connect(sock, address):
        assert address == ("127.0.0.1", endpoint.port), "non-fixture network access"
        return _CONNECT(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
    candidates = [row for row in prepared[2]["targets"] if row["axis"] == "grounding_v3"]
    chosen = [next(row for row in candidates if row["kind"] == kind)
              for kind in ("relationship_edge", "attribute_value")]
    selections = [{"target_id": row["id"], "attempt_id": f"support-{i}"} for i, row in enumerate(chosen)]
    descriptor = tmp_path / "support-descriptor"
    selected = support.prepare(prepared[1], descriptor, selections=selections, protocol=support.FORMAT)
    registered, run = tmp_path / "support-registered", tmp_path / "support-run"
    decl_path = tmp_path / "support-declaration.json"
    decl_path.write_bytes(canonical(declaration(peer, run)))
    registration = execution.prepare(descriptor, decl_path, registered)
    return SimpleNamespace(prepared=prepared, descriptor=descriptor, selected=selected,
        fitness_descriptor=prepared[4], registered=registered, run=run, registration=registration)


def index(case, output, **kwargs):
    return fitness.build_index(case.fitness_descriptor, [], output, support_execution=case.run, **kwargs)


def saved_support(case, report, output, *, changed_verdict=None):
    result = report["rows"][0]["saved_result"]
    raw = (case.run / "artifacts" / result["response"]["sha256"]).read_bytes()
    if changed_verdict:
        body = json.loads(raw)
        body["content"][-1]["text"] = json.dumps({"verdict": changed_verdict, "reason": "Invented alternate reply."})
        raw = canonical(body)
    envelope = support.package_response((case.descriptor / "descriptor.json").read_bytes(),
        attempt_id=result["attempt_id"], native_message=raw)
    path = output.with_suffix(".json")
    path.write_bytes(envelope)
    support.accept(case.descriptor, path, output, attempt_id=result["attempt_id"])
    return output


def test_cli_captures_both_axes_and_rechecks_after_originals_move(case, peer, tmp_path, monkeypatch):
    fitness_run, fitness_registration = tmp_path / "fitness-run", tmp_path / "fitness-registered"
    # Select every original fitness target; declare enough budget for this fixture.
    declared = declaration(peer, fitness_run)
    declared["format"] = execution.FITNESS_FORMAT
    count = len(case.prepared[3])
    declared["limits"].update(max_calls=count, input_scheduling_threshold=100 * count,
        output_scheduling_threshold=417 * count, total_response_bytes=50_001 * count)
    decl_path = tmp_path / "fitness-declaration.json"
    decl_path.write_bytes(canonical(declared))
    execution.prepare(case.fitness_descriptor, decl_path, fitness_registration)
    peer["body"] = canonical(native(usage={"input_tokens": 12, "output_tokens": 23,
        "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}))
    fitness_report = execution.run(fitness_registration)
    peer["body"] = canonical(reply())
    support_report = execution.run(case.registered)
    output = tmp_path / "joined"
    checked = CliRunner().invoke(evaluate, ["fitness-results", "index",
        "--descriptor", str(case.fitness_descriptor), "--execution", str(fitness_run),
        "--support-execution", str(case.run), "--output", str(output)])
    assert checked.exit_code == 0, checked.output
    value = json.loads(checked.output)
    assert value["format"] == fitness.INDEX_FORMAT_V2
    assert value["execution"]["report"] == fitness_report
    assert value["support_execution"]["report"] == support_report
    assert value["mode"] == value["support_mode"] == "local_fixture"
    assert value["scientific_scoring_eligible"] is False
    assert value["readiness"] == value["support_readiness"] == case.registration["original_readiness"]
    assert all(v is None for v in value["support_decision_references"].values())
    assert all(row["state"] == row["dispatch_state"] == "accepted" and row["spent"] is True
               for row in value["support_rows"])
    assert all(row["result"] is None and row["fitness_propagated"] is False for row in value["support_rows"])
    for kind in ("relationship_edge", "attribute_value"):
        assert value["strata"][kind] == {"selected": 1, "accepted": 1, "missing": 0, "rejected": 0}
    portable = tmp_path / "portable"
    shutil.copytree(output, portable)
    for path in (case.prepared[0], case.prepared[1], case.fitness_descriptor, case.descriptor,
                 case.registered, case.run, fitness_registration, fitness_run, output):
        path.rename(path.with_name(path.name + "-unavailable"))
    original_read = Path.read_bytes

    def captured_only(path):
        assert path.is_relative_to(portable), path
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", captured_only)
    monkeypatch.setattr(execution, "_dispatch", lambda *_: pytest.fail("index dispatched"))
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("index used network"))
    assert fitness.recheck_index(portable) == value
    assert len(peer["requests"]) == count + 2


@pytest.mark.parametrize("fault", ["http_429", "malformed", "truncated"])
def test_failed_support_retains_later_unstarted_and_raw_assessment(case, peer, tmp_path, fault):
    if fault == "http_429":
        peer["status"] = 429
    else:
        body = reply()
        if fault == "malformed":
            body["content"][-1]["text"] = "not a verdict"
        else:
            body["stop_reason"] = "max_tokens"
        peer["body"] = canonical(body)
    report = execution.run(case.registered)
    assert report["rows"][0]["status"] == "failed"
    output = tmp_path / "index"
    value = index(case, output)
    first, later = value["support_rows"]
    assert (first["state"], first["dispatch_state"], first["spent"]) == ("rejected", "failed", True)
    assert (later["state"], later["dispatch_state"], later["spent"]) == ("missing", "not_started", False)
    assert later["assessment"] is None
    assert first["assessment"]["status"] == ("accepted" if fault == "http_429" else "rejected")
    assert sum(value["strata"][k]["selected"] for k in ("relationship_edge", "attribute_value")) == 2
    assert value["support_dispatch_counts"][first["kind"]]["failed"] == 1
    assert value["support_dispatch_counts"][later["kind"]]["not_started"] == 1
    assert fitness.recheck_index(output) == value
    assert len(peer["requests"]) == 1


@pytest.mark.parametrize("boundary,expected,request_count", [
    ("admitted", "not_started", 0), ("response", "spent_unknown", 1), ("settled", "accepted", 1),
])
def test_interruption_reconstructs_support_without_repurchase(case, peer, tmp_path, monkeypatch,
                                                           boundary, expected, request_count):
    original = execution._exclusive

    def interrupted(path, raw):
        if path.name == boundary + ".json":
            raise OSError("invented interrupted publication")
        return original(path, raw)

    with monkeypatch.context() as changed:
        changed.setattr(execution, "_exclusive", interrupted)
        with pytest.raises(OSError, match="invented interrupted"):
            execution.run(case.registered)
    output = tmp_path / "index"
    value = index(case, output)
    first, second = value["support_rows"]
    assert first["dispatch_state"] == expected
    assert first["spent"] is (expected != "not_started")
    assert second["dispatch_state"] == "not_started" and second["spent"] is False
    assert value["support_execution"]["saved_report"] is None
    assert fitness.recheck_index(output) == value
    assert len(peer["requests"]) == request_count
    with pytest.raises(ValueError, match="exist"):
        execution.run(case.registered)
    assert len(peer["requests"]) == request_count


def test_matching_saved_support_is_optional_but_cannot_override_failed_dispatch(case, peer, tmp_path):
    peer["status"] = 429
    report = execution.run(case.registered)
    result = saved_support(case, report, tmp_path / "support-result")
    value = index(case, tmp_path / "index", support_results=[result])
    assert value["support_rows"][0]["assessment"]["status"] == "accepted"
    assert value["support_rows"][0]["state"] == "rejected"
    assert value["support_rows"][0]["result"] is not None
    alternative = saved_support(case, report, tmp_path / "alternate", changed_verdict="unsupported")
    refused = tmp_path / "refused"
    with pytest.raises(ValueError, match="differs from its actual execution ledger"):
        index(case, refused, support_results=[alternative])
    assert not refused.exists()


def test_opt_out_keeps_exact_v1_shape_and_bytes(case, peer, tmp_path):
    execution.run(case.registered)
    original = fitness.build_index(case.fitness_descriptor, [], tmp_path / "default")
    explicit = fitness.build_index(case.fitness_descriptor, [], tmp_path / "explicit", support_execution=None)
    assert original == explicit
    assert (tmp_path / "default" / "index.json").read_bytes() == (tmp_path / "explicit" / "index.json").read_bytes()
    assert original["format"] == fitness.INDEX_FORMAT
    assert "support_execution" not in original and "support_mode" not in original
    assert original["support_rows"] == []
    assert fitness.recheck_index(tmp_path / "default") == original
    changed = copy.deepcopy(original)
    changed["format"] = fitness.INDEX_FORMAT_V2
    (tmp_path / "default" / "index.json").write_bytes(canonical(changed))
    with pytest.raises(ValueError, match="requires captured support execution"):
        fitness.recheck_index(tmp_path / "default")
