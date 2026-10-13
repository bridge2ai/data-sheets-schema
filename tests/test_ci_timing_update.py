"""Scheduling hints retain JUnit occurrences without accepting copied inputs."""

import hashlib
import subprocess
import xml.etree.ElementTree as ET

import pytest

from utils.update_ci_shard_timings import build


@pytest.fixture
def timing_inputs(tmp_path):
    repository = tmp_path / "repository"
    tests = repository / "tests"
    tests.mkdir(parents=True)
    (tests / "test_budget.py").write_text("def test_budget(): pass\n")
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    subprocess.run(["git", "add", "tests/test_budget.py"], cwd=repository, check=True)
    results = tmp_path / "results"
    results.mkdir()
    return repository, results


def junit(results, shard, *records):
    path = results / shard / "pytest.xml"
    path.parent.mkdir(parents=True)
    suite = ET.Element("testsuite", tests=str(len(records)))
    for record in records:
        fields = {"classname": "tests.test_budget", "name": "test_budget[00]",
                  "time": "0.014", **record}
        outcome = fields.pop("outcome", None)
        case = ET.SubElement(suite, "testcase", fields)
        if outcome:
            ET.SubElement(case, outcome)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
    return path


def estimate(timing_inputs):
    repository, results = timing_inputs
    return build(results, repository, run_id=123, commit="a" * 40)


def test_parameter_id_collision_retains_both_occurrences_and_times(timing_inputs):
    _, results = timing_inputs
    # Actual pytest/JUnit shape from #5020: integer 0 and string '00' can
    # produce the same label. They remain two records, not one repeated input.
    source = junit(results, "shard1", {"time": "0.014"}, {"time": "0.015"})
    original = source.read_bytes()

    value = estimate(timing_inputs)

    assert value["source"]["test_cases"] == 2
    assert value["file_seconds"] == {"tests/test_budget.py": 0.029}
    assert value["source"]["artifacts"] == [{
        "path": "shard1/pytest.xml", "sha256": hashlib.sha256(original).hexdigest()}]
    assert source.read_bytes() == original


def test_same_label_in_different_artifacts_is_rejected(timing_inputs):
    _, results = timing_inputs
    junit(results, "shard1", {"time": "0.014"})
    junit(results, "shard2", {"time": "0.015"})
    with pytest.raises(ValueError, match="duplicate case across artifacts"):
        estimate(timing_inputs)


@pytest.mark.parametrize("copy_kind", ["bytes", "symlink"])
def test_copied_or_referenced_artifact_is_rejected(timing_inputs, copy_kind):
    _, results = timing_inputs
    source = junit(results, "shard1", {})
    duplicate = results / "shard2" / "pytest.xml"
    duplicate.parent.mkdir()
    if copy_kind == "bytes":
        duplicate.write_bytes(source.read_bytes())
    else:
        duplicate.symlink_to(source)
    with pytest.raises(ValueError, match="duplicate artifact input"):
        estimate(timing_inputs)


def test_distinct_labels_and_skips_keep_their_record_counts(timing_inputs):
    _, results = timing_inputs
    junit(results, "shard1", {"name": "test_first", "time": "0.014"})
    junit(results, "shard2", {"name": "test_second", "time": "0.015"},
          {"name": "test_skipped", "time": "0", "outcome": "skipped"})
    value = estimate(timing_inputs)
    assert value["source"]["test_cases"] == 3
    assert value["file_seconds"] == {"tests/test_budget.py": 0.029}


@pytest.mark.parametrize("outcome", ["failure", "error"])
def test_unsuccessful_case_still_refuses(timing_inputs, outcome):
    _, results = timing_inputs
    junit(results, "shard1", {"outcome": outcome})
    with pytest.raises(ValueError, match="use a successful run"):
        estimate(timing_inputs)


@pytest.mark.parametrize("duration", ["-0.001", "NaN", "Infinity"])
def test_invalid_duration_still_refuses(timing_inputs, duration):
    _, results = timing_inputs
    junit(results, "shard1", {"time": duration})
    with pytest.raises(ValueError, match="invalid recorded duration"):
        estimate(timing_inputs)


def test_unknown_collected_module_still_refuses(timing_inputs):
    _, results = timing_inputs
    junit(results, "shard1", {"classname": "tests.test_untracked"})
    with pytest.raises(ValueError, match="cannot map collected case"):
        estimate(timing_inputs)


@pytest.mark.parametrize("empty_artifact", [False, True])
def test_empty_input_still_refuses(timing_inputs, empty_artifact):
    _, results = timing_inputs
    if empty_artifact:
        junit(results, "shard1")
    with pytest.raises(ValueError, match="no test cases|no pytest.xml"):
        estimate(timing_inputs)
