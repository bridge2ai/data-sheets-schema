"""Orchestration controls only: child results are fake, inventories/tar/Git real."""
import json
from pathlib import Path
import subprocess
import tarfile
import xml.etree.ElementTree as ET

import pytest

from utils import native_shared_acceptance as runner


@pytest.fixture
def case(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tracked.txt").write_text("original tracked bytes\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=Offline Test", "-c", "user.email=test@example.invalid",
                    "commit", "-qm", "initial"], cwd=repo, check=True)
    head = runner.git(repo, "rev-parse", "HEAD").strip()
    return repo, tmp_path / "evidence", head


def fake_result(output, label, node, *, state="pass"):
    """Fabricated runner outcome, not an actual native result or helper."""
    base = output / "cases" / label
    base.mkdir()
    (base / ".hidden").write_bytes(b"retained synthetic bytes\x00")
    (output / (label + ".log")).write_text("FAKE child for orchestration test\n")
    path = output / (label + ".xml")
    if state == "missing":
        return
    if state == "malformed":
        path.write_text("<broken")
        return
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", tests="1", errors="0", failures="0", skipped="0")
    item = ET.SubElement(suite, "testcase", name=node.split("::")[1])
    if state in {"skipped", "failure"}:
        ET.SubElement(item, state)
    elif state == "extra":
        ET.SubElement(suite, "testcase", name=node.split("::")[1])
    elif state == "suite-error":
        suite.set("errors", "1")
    ET.ElementTree(root).write(path, encoding="utf-8")


def test_success_runs_exact_nodes_in_order_and_archives_without_following_links(case, monkeypatch):
    repo, output, head = case
    calls = []
    outside = output.parent / "never-archive.txt"
    outside.write_bytes(b"external sentinel, not part of synthetic case")

    def child(repo_arg, out, label, node):
        assert repo_arg == repo and out == output
        if label == "omission":
            assert (output / "source-after-neutral.json").is_file()
        calls.append((label, node))
        fake_result(out, label, node)
        base = out / "cases" / label
        (base / ".hidden").chmod(0o600)
        (base / "outside-link").symlink_to(outside)
        return 0

    monkeypatch.setattr(runner, "pytest_child", child)
    assert runner.run(repo, output, head) == 0
    assert calls == list(runner.NODES)
    assert runner.finalize(repo, output, head) == 0
    with tarfile.open(output / "upload/cases.tar.gz") as archive:
        names = archive.getnames()
        assert "cases/neutral/.hidden" in names
        assert archive.getmember("cases/neutral/.hidden").mode == 0o600
        link = archive.getmember("cases/neutral/outside-link")
        assert link.issym() and link.linkname == str(outside)
        assert not any("never-archive" in name for name in names)
        assert archive.extractfile("cases/neutral/.hidden").read() == b"retained synthetic bytes\x00"
    assert json.loads((output / "upload/outcome.json").read_text())["status"] == "passed"
    # An explicit finalizer retry must not claim to hash itself.
    assert runner.finalize(repo, output, head) == 0
    assert "artifact-manifest.json" not in json.loads((output / "upload/artifact-manifest.json").read_text())


@pytest.mark.parametrize("state,code", [
    ("failure", 1), ("skipped", 0), ("malformed", 0), ("missing", 0), ("extra", 0), ("suite-error", 0),
])
def test_neutral_failure_or_incomplete_junit_blocks_omission_and_preserves_partial_case(case, monkeypatch, state, code):
    repo, output, head = case
    calls = []

    def child(repo_arg, out, label, node):
        calls.append(label)
        fake_result(out, label, node, state=state)
        return code

    monkeypatch.setattr(runner, "pytest_child", child)
    assert runner.run(repo, output, head) == 1
    assert calls == ["neutral"]
    assert runner.finalize(repo, output, head) == 0
    outcome = json.loads((output / "upload/outcome.json").read_text())
    assert outcome["status"] == "failed" and outcome["omission_not_run"]
    assert (output / "upload/neutral.log").read_bytes() == (output / "neutral.log").read_bytes()
    with tarfile.open(output / "upload/cases.tar.gz") as archive:
        assert archive.extractfile("cases/neutral/.hidden").read() == b"retained synthetic bytes\x00"
        assert not any(name.startswith("cases/omission") for name in archive.getnames())


def test_source_drift_stops_second_test_and_remains_a_failed_preservation(case, monkeypatch):
    repo, output, head = case
    calls = []

    def child(repo_arg, out, label, node):
        calls.append(label)
        fake_result(out, label, node)
        (repo / "tracked.txt").write_text("changed within the test fixture\n")
        return 0

    monkeypatch.setattr(runner, "pytest_child", child)
    assert runner.run(repo, output, head) == 1
    assert calls == ["neutral"]
    assert runner.finalize(repo, output, head) == 1
    assert not json.loads((output / "upload/preservation.json").read_text())["source_unchanged"]
    assert (output / "upload/cases.tar.gz").is_file()


def test_wrong_head_fails_before_child(case, monkeypatch):
    repo, output, _ = case
    def child(*args):
        pytest.fail("wrong head reached child dispatch")
    monkeypatch.setattr(runner, "pytest_child", child)
    assert runner.run(repo, output, "0" * 40) == 1
    assert "exact selected source head" in json.loads((output / "outcome.json").read_text())["error"]


def test_finalizer_error_cannot_become_success(case, monkeypatch):
    repo, output, head = case
    monkeypatch.setattr(runner, "pytest_child", lambda repo, out, label, node: (fake_result(out, label, node), 0)[1])
    assert runner.run(repo, output, head) == 0
    def fail(*args, **kwargs):
        raise OSError("intentional archive failure")
    monkeypatch.setattr(runner.tarfile, "open", fail)
    with pytest.raises(OSError, match="intentional archive failure"):
        runner.finalize(repo, output, head)
    assert not (output / "upload/artifact-manifest.json").exists()


def test_inventory_refuses_symlink_as_case_root(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "not-evidence").write_text("not copied")
    link = tmp_path / "cases"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="root must not be a symlink"):
        runner.inventory(link)


def test_child_command_keeps_fixed_test_limits_and_fresh_basetemp(case, monkeypatch):
    repo, output, _ = case
    output.mkdir()
    (output / "cases").mkdir()
    calls = []

    def child(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", child)
    label, node = runner.NODES[0]
    assert runner.pytest_child(repo, output, label, node) == 0
    command, kwargs = calls[0]
    assert command == [runner.sys.executable, "-c", runner.BOOTSTRAP, "-q", "-p", "no:cacheprovider",
                       "--basetemp", str(output / "cases/neutral"),
                       "--junitxml", str(output / "neutral.xml"), node]
    assert kwargs["cwd"] == repo and "timeout" not in kwargs
    assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    (output / "cases/neutral").mkdir()
    with pytest.raises(ValueError, match="basetemp must be fresh"):
        runner.pytest_child(repo, output, label, node)
    assert len(calls) == 1
