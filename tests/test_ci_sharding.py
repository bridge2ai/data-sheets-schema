"""A CI split must execute every test exactly once and retain failures."""

from collections import Counter
from pathlib import Path
import os
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

from utils.pytest_shard import balanced_files, read_weights, shard_for


ROOT = Path(__file__).resolve().parents[1]


def _run(root, *args):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "src")))
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "utils.pytest_shard", "-q",
         "-p", "no:cacheprovider", *args], cwd=root, env=env,
        capture_output=True, text=True, timeout=90,
    )


def _cases(path):
    return Counter((case.attrib["classname"], case.attrib["name"])
                   for case in ET.parse(path).iter("testcase"))


@pytest.mark.parametrize("weighted", [False, True])
def test_shards_cover_the_real_collection_exactly_once_with_xdist(tmp_path, weighted):
    # Include both pytest filename conventions, classes, parameterization,
    # a corpus marker and a skip. Assignment must not depend on worker ID.
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers = corpus: corpus check\n")
    for number in range(16):
        name = f"test_{number}.py" if number % 2 else f"{number}_test.py"
        (tmp_path / name).write_text(
            "import pytest\n"
            "@pytest.mark.corpus\n"
            "@pytest.mark.parametrize('x', ['first', 'nested::value'])\n"
            "def test_values(x): assert x\n"
            "class TestGroup:\n"
            "    def test_method(self): assert True\n"
            "@pytest.mark.skip(reason='fixture skip')\n"
            "def test_skip(): pass\n"
        )
    whole = _run(tmp_path, "--junitxml=all.xml")
    assert whole.returncode == 0, whole.stdout + whole.stderr
    expected = _cases(tmp_path / "all.xml")
    assert sum(expected.values()) == 64
    flags = []
    if weighted:
        # Only half the files have timings. Untimed files must still run;
        # obsolete timing entries must never become collected tests.
        weights = {f"{number}_test.py": number + 1 for number in range(0, 16, 2)}
        weights["test_removed.py"] = 10000
        timing = tmp_path / "timings.json"
        timing.write_text(json.dumps({"schema_version": 1, "file_seconds": weights}))
        flags = [f"--ci-shard-timings={timing}"]
    actual = Counter()
    for index in range(1, 5):
        result = _run(tmp_path, f"--ci-shard={index}/4", "-n", "logical", "--maxprocesses=4",
                      "--dist=load", "--maxschedchunk=1", *flags, f"--junitxml=shard-{index}.xml")
        assert result.returncode == 0, result.stdout + result.stderr
        actual.update(_cases(tmp_path / f"shard-{index}.xml"))
    assert actual == expected
    assert set(actual.values()) == {1}


def test_one_long_case_starts_before_a_file_with_many_short_cases(tmp_path):
    (tmp_path / "test_many.py").write_text("\n".join(
        f"def test_{i}(): pass" for i in range(12)))
    (tmp_path / "test_single.py").write_text("def test_expensive(): pass\n")
    (tmp_path / "timings.json").write_text(json.dumps({
        "schema_version": 1,
        "file_seconds": {"test_many.py": 12, "test_single.py": 10}}))
    result = _run(tmp_path, "--collect-only", "--ci-shard=1/1",
                  "--ci-shard-timings=timings.json")
    assert result.returncode == 0, result.stdout + result.stderr
    collected = [line for line in result.stdout.splitlines() if "::test_" in line]
    assert collected[0] == "test_single.py::test_expensive"
    assert collected[1:] == [f"test_many.py::test_{i}" for i in range(12)]


@pytest.mark.parametrize("value", ["0/4", "5/4", "1/0", "1", "one/four", "1/4/5"])
def test_invalid_shard_is_a_usage_error(tmp_path, value):
    result = _run(tmp_path, f"--ci-shard={value}")
    assert result.returncode == 4
    assert "--ci-shard must be" in result.stderr


@pytest.mark.parametrize("weighted", [False, True])
def test_failure_and_empty_selection_cannot_pass(tmp_path, weighted):
    (tmp_path / "test_failure.py").write_text("def test_failure(): assert False\n")
    owning = shard_for("test_failure.py::test_failure", 2)
    flags = []
    if weighted:
        (tmp_path / "timings.json").write_text(json.dumps(
            {"schema_version": 1, "file_seconds": {"test_failure.py": 1}}))
        flags = ["--ci-shard-timings=timings.json"]
        owning = balanced_files(["test_failure.py"], 2, {"test_failure.py": 1})["test_failure.py"]
    result = _run(tmp_path, f"--ci-shard={owning}/2", "-n", "2", *flags)
    assert result.returncode == 1, result.stdout + result.stderr
    empty = _run(tmp_path, f"--ci-shard={3 - owning}/2", *flags)
    assert empty.returncode == 5, empty.stdout + empty.stderr


def test_measured_partition_is_order_independent_and_reduces_estimated_imbalance():
    weights = read_weights(ROOT / "utils/ci_test_durations.json")
    assigned = balanced_files(weights, 4, weights)
    assert assigned == balanced_files(reversed(list(weights)), 4, weights)
    assert set(assigned) == set(weights)
    previous, balanced = [0.0] * 4, [0.0] * 4
    for path, seconds in weights.items():
        previous[shard_for(path, 4) - 1] += seconds
        balanced[assigned[path] - 1] += seconds
    assert max(balanced) < max(previous) * .8
    assert max(balanced) / min(balanced) < 1.05


@pytest.mark.parametrize("payload", ["{}", "not json", '{"schema_version":1,"file_seconds":{}}',
    '{"schema_version":true,"file_seconds":{"test_a.py":1}}',
    '{"schema_version":1,"file_seconds":{"test_a.py":-1}}',
    '{"schema_version":1,"file_seconds":{"test_a.py":NaN}}',
    '{"schema_version":1,"file_seconds":{"test_a.py":true}}',
    '{"schema_version":1,"file_seconds":{"test_a.py":1,"test_a.py":2}}'])
def test_invalid_explicit_timing_data_is_a_usage_error_before_tests(tmp_path, payload):
    (tmp_path / "test_must_not_run.py").write_text("def test_broken(): assert False\n")
    (tmp_path / "timings.json").write_text(payload)
    result = _run(tmp_path, "--ci-shard=1/4", "--ci-shard-timings=timings.json")
    assert result.returncode == 4, result.stdout + result.stderr
    assert "invalid --ci-shard-timings" in result.stderr


def test_aggregate_check_rejects_failed_cancelled_and_skipped_dependencies(tmp_path):
    workflow = yaml.safe_load((ROOT / ".github/workflows/main.yaml").read_text())
    gate = workflow["jobs"]["test"]
    assert gate["if"] == "always()"
    assert set(gate["needs"]) == {"python-tests", "schema-examples"}
    script = gate["steps"][0]["run"]
    for event in ("pull_request", "push", "workflow_dispatch"):
        for python_result in ("success", "failure", "cancelled", "skipped"):
            for build_result in ("success", "failure", "cancelled", "skipped"):
                env = {**os.environ, "EVENT_NAME": event,
                       "PYTHON_RESULT": python_result, "BUILD_RESULT": build_result}
                result = subprocess.run(["bash", "-e", "-c", script], cwd=tmp_path,
                                        env=env, capture_output=True, timeout=10)
                expected_build = "skipped" if event == "pull_request" else "success"
                assert (result.returncode == 0) == (
                    python_result == "success" and build_result == expected_build
                ), (event, python_result, build_result)
