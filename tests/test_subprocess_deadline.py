"""Generic isolated-test and deadline contracts; no review tooling imports."""
import ast
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.utils import isolated_pytest as isolated
from tests.utils import subprocess_deadline as deadline

ROOT = Path(__file__).resolve().parents[1]


def test_default_route_has_no_review_adapter(monkeypatch, tmp_path):
    monkeypatch.delenv(isolated.REVIEW_ENV, raising=False)
    assert isolated.review_adapter(tmp_path) is None


@pytest.mark.parametrize("broken", ["digest", "root", "head"])
def test_review_adapter_must_bind_source_and_bytes(monkeypatch, tmp_path, broken):
    adapter = tmp_path / "adapter.py"
    adapter.write_text("raise AssertionError('not executed by this contract')\n")
    value = {"root": str(tmp_path), "runner": str(adapter),
             "sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(), "head": "a" * 40}
    value[{"digest": "sha256", "root": "root", "head": "head"}[broken]] = "wrong"
    monkeypatch.setenv(isolated.REVIEW_ENV, json.dumps(value))
    with pytest.raises(ValueError):
        isolated.review_adapter(tmp_path)


def test_explicit_valid_adapter_is_selected_without_import(monkeypatch, tmp_path):
    adapter = tmp_path / "adapter.py"
    adapter.write_text("raise AssertionError('adapter must not be imported here')\n")
    value = {"root": str(tmp_path), "runner": str(adapter),
             "sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(), "head": "a" * 40}
    monkeypatch.setenv(isolated.REVIEW_ENV, json.dumps(value))
    assert isolated.review_adapter(tmp_path) == value


@pytest.mark.parametrize("wrong", ["node", "pid"])
def test_child_marker_cannot_select_another_node_or_process(monkeypatch, tmp_path, wrong):
    request = SimpleNamespace(node=SimpleNamespace(nodeid="tests/test_case.py::test_real"))
    monkeypatch.setenv(isolated.NODE_ENV, "wrong" if wrong == "node" else request.node.nodeid)
    monkeypatch.setenv(isolated.PID_ENV, "wrong" if wrong == "pid" else str(os.getpid()))
    with pytest.raises(ValueError, match="exact node/PID"):
        isolated.run_isolated_pytest(request, tmp_path, root=ROOT, seconds=30, label="fixture")


def test_exact_child_marker_returns_to_the_original_assertion_body(monkeypatch, tmp_path):
    request = SimpleNamespace(node=SimpleNamespace(nodeid="tests/test_case.py::test_real"))
    monkeypatch.setenv(isolated.NODE_ENV, request.node.nodeid)
    monkeypatch.setenv(isolated.PID_ENV, str(os.getpid()))
    assert isolated.run_isolated_pytest(request, tmp_path, root=ROOT, seconds=30, label="fixture") is False


def test_ordinary_child_strips_ambient_review_plugins_and_credentials(monkeypatch):
    names = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CBORG_TOKEN", "PYTEST_PLUGINS",
             "PYTHONPATH", "D76_OUTPUT", isolated.REVIEW_ENV, isolated.NODE_ENV, isolated.PID_ENV]
    for name in names:
        monkeypatch.setenv(name, "synthetic-value-for-test")
    child = isolated.child_environment()
    assert not set(names).intersection(child)
    assert child["PYTHONDONTWRITEBYTECODE"] == "1"
    assert child["PYTEST_ADDOPTS"] == ""


def test_dependencies_follow_parent_paths_not_a_venv_directory_formula(monkeypatch, tmp_path):
    source, dependencies = tmp_path / "source", tmp_path / "conda-shaped-dependencies"
    source.mkdir()
    dependencies.mkdir()
    monkeypatch.setattr(sys, "path", [str(source), str(dependencies)])
    configuration = isolated.dependency_configuration(source)
    assert configuration["paths"] == [str(dependencies)]
    assert configuration["prefix"] == sys.prefix
    assert configuration["exec_prefix"] == sys.exec_prefix


def test_repository_local_environment_dependencies_are_retained(monkeypatch, tmp_path):
    source = tmp_path / "source"
    environment = source / ".venv"
    dependencies = environment / "site-packages"
    dependencies.mkdir(parents=True)
    (source / "src").mkdir()
    (source / "tests").mkdir()
    monkeypatch.setattr(sys, "prefix", str(environment))
    monkeypatch.setattr(sys, "exec_prefix", str(environment))
    monkeypatch.setattr(sys, "path", [str(source), str(source / "src"),
                                      str(source / "tests"), str(dependencies)])
    configuration = isolated.dependency_configuration(source)
    assert configuration["paths"] == [str(dependencies)]


def test_ordinary_utility_and_sg2_wrapper_do_not_import_review_scripts():
    for relative in ["tests/utils/isolated_pytest.py", "tests/utils/subprocess_deadline.py",
                     "tests/test_wave7_5213_d76_registration.py"]:
        source = (ROOT / relative).read_text()
        assert "scripts/adhoc/" not in source
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith("scripts.") for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("scripts.")


def test_timeout_retires_owned_group_before_final_reap(monkeypatch, tmp_path):
    events = []
    class Child:
        pid = 424242
        returncode = None
        waits = 0
        def wait(self, timeout):
            self.waits += 1
            events.append(("wait", timeout))
            if self.waits == 1:
                raise subprocess.TimeoutExpired("fixture", timeout)
            self.returncode = -9
            return self.returncode
    child = Child()
    monkeypatch.setattr(deadline.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(deadline.os, "killpg", lambda pid, sig: events.append(("signal", sig)))
    monkeypatch.setattr(deadline.time, "sleep", lambda seconds: events.append(("grace", seconds)))
    with (tmp_path / "log").open("wb") as stream:
        result = deadline.run(["fixture"], cwd=tmp_path, env={}, stream=stream,
                              evidence=tmp_path / "proof", seconds=1)
    assert result.expired and result.returncode == -9
    assert events == [("wait", 1), ("signal", signal.SIGTERM), ("grace", 5),
                      ("signal", signal.SIGKILL), ("wait", 10)]
    proof = json.loads((tmp_path / "proof/deadline.json").read_text())
    assert proof["termination_verified"] is True


@pytest.mark.parametrize("text,code", [("42 42 Z\n43 42 S\n", 0), ("43 42 Z\n", 0),
                                      ("", 1), ("malformed\n", 0)])
def test_live_or_unobserved_group_never_counts_as_retired(monkeypatch, text, code):
    monkeypatch.setattr(deadline.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=text, stderr="", returncode=code))
    assert deadline.owned_group_state(42)["all_retired"] is False


def test_generic_child_runs_a_real_case_in_a_non_git_source(tmp_path):
    source = tmp_path / "source"
    utility_dir = source / "tests/utils"
    utility_dir.mkdir(parents=True)
    (source / "tests/__init__.py").write_text("")
    (source / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    for name in ["isolated_pytest.py", "subprocess_deadline.py"]:
        (utility_dir / name).write_bytes((ROOT / "tests/utils" / name).read_bytes())
    (source / "tests/test_child.py").write_text(
        "def test_payload(tmp_path):\n"
        "    (tmp_path / 'persisted.txt').write_text('real child effect')\n"
        "    assert (tmp_path / 'persisted.txt').read_text() == 'real child effect'\n")
    assert not (source / ".git").exists()
    config = tmp_path / "dependencies.json"
    isolated.save(config, isolated.dependency_configuration(ROOT))
    output = tmp_path / "child"
    command = [sys.executable, "-S", "-P", "-B", str(utility_dir / "isolated_pytest.py"),
               "--root", str(source), "--node", "tests/test_child.py::test_payload",
               "--output", str(output), "--dependencies", str(config)]
    with (tmp_path / "child.log").open("wb") as stream:
        result = deadline.run(command, cwd=source, env=isolated.child_environment(), stream=stream,
                              evidence=tmp_path / "supervisor", seconds=30)
    assert not result.expired
    assert result.returncode == 0, (tmp_path / "child.log").read_text(errors="replace")
    report = json.loads((output / "outcome.json").read_text())
    assert report["passed"] and report["complete"] and report["review_attestation"] is False
    assert report["selected"] == ["tests/test_child.py::test_payload"]
    assert (output / "cases/test_payload0/persisted.txt").read_text() == "real child effect"
    assert (output / "pytest.xml").stat().st_size > 0

