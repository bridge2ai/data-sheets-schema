"""A CI split must execute every test exactly once and retain failures."""

from collections import Counter
from pathlib import Path
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

from utils.pytest_shard import shard_for


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


def test_shards_cover_the_real_collection_exactly_once_with_xdist(tmp_path):
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
    actual = Counter()
    for index in range(1, 5):
        result = _run(tmp_path, f"--ci-shard={index}/4", "-n", "2",
                      f"--junitxml=shard-{index}.xml")
        assert result.returncode == 0, result.stdout + result.stderr
        actual.update(_cases(tmp_path / f"shard-{index}.xml"))
    assert actual == expected
    assert set(actual.values()) == {1}


@pytest.mark.parametrize("value", ["0/4", "5/4", "1/0", "1", "one/four", "1/4/5"])
def test_invalid_shard_is_a_usage_error(tmp_path, value):
    result = _run(tmp_path, f"--ci-shard={value}")
    assert result.returncode == 4
    assert "--ci-shard must be" in result.stderr


def test_failure_and_empty_selection_cannot_pass(tmp_path):
    (tmp_path / "test_failure.py").write_text("def test_failure(): assert False\n")
    owning = shard_for("test_failure.py::test_failure", 2)
    result = _run(tmp_path, f"--ci-shard={owning}/2", "-n", "2")
    assert result.returncode == 1, result.stdout + result.stderr
    empty = _run(tmp_path, f"--ci-shard={3 - owning}/2")
    assert empty.returncode == 5, empty.stdout + empty.stderr


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
