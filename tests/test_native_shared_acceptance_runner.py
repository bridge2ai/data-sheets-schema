"""Orchestration controls only: child results are fake, inventories/tar/Git real."""
import json
from pathlib import Path
import subprocess
import tarfile
import xml.etree.ElementTree as ET

import pytest

from utils import native_shared_acceptance as runner


def invoke(repo, output, head, **kwargs):
    """The test mocks all children; this is no declaration of actual isolation."""
    return runner.run(repo, output, head,
        quiet_lock=output.parent / 'held-quiet.lock', network_denied=True, **kwargs)


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

    def child(repo_arg, out, label, node, **kwargs):
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
    assert invoke(repo, output, head) == 0
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
    # Never overwrite a retained evidence bundle on retry.
    with pytest.raises(FileExistsError):
        runner.finalize(repo, output, head)
    assert "artifact-manifest.json" not in json.loads((output / "upload/artifact-manifest.json").read_text())


@pytest.mark.parametrize("state,code", [
    ("failure", 1), ("skipped", 0), ("malformed", 0), ("missing", 0), ("extra", 0), ("suite-error", 0),
])
def test_neutral_failure_or_incomplete_junit_blocks_omission_and_preserves_partial_case(case, monkeypatch, state, code):
    repo, output, head = case
    calls = []

    def child(repo_arg, out, label, node, **kwargs):
        calls.append(label)
        fake_result(out, label, node, state=state)
        return code

    monkeypatch.setattr(runner, "pytest_child", child)
    assert invoke(repo, output, head) == 1
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

    def child(repo_arg, out, label, node, **kwargs):
        calls.append(label)
        fake_result(out, label, node)
        (repo / "tracked.txt").write_text("changed within the test fixture\n")
        return 0

    monkeypatch.setattr(runner, "pytest_child", child)
    assert invoke(repo, output, head) == 1
    assert calls == ["neutral"]
    assert runner.finalize(repo, output, head) == 1
    assert not json.loads((output / "upload/preservation.json").read_text())["source_unchanged"]
    assert (output / "upload/cases.tar.gz").is_file()


def test_source_inspection_error_still_exports_failed_case_and_logs(case, monkeypatch):
    repo, output, head = case
    calls = []

    def child(repo_arg, out, label, node, **kwargs):
        calls.append(label)
        fake_result(out, label, node)
        (repo / "tracked.txt").unlink()
        (repo / "tracked.txt").mkdir()
        return 0

    monkeypatch.setattr(runner, "pytest_child", child)
    assert invoke(repo, output, head) == 1
    assert calls == ["neutral"]
    assert runner.finalize(repo, output, head) == 1
    upload = output / "upload"
    proof = json.loads((upload / "preservation.json").read_text())
    assert proof["source_inspection_succeeded"] is False
    assert proof["source_unchanged"] is False and proof["expected_head_matches"] is False
    assert proof["source_inspection_error"]["type"] == "ValueError"
    final_source = json.loads((upload / "source-final.json").read_text())
    assert final_source["inspection_failed"] is True
    assert "head" not in final_source and "tree" not in final_source
    for name in ("neutral.log", "neutral.xml", "outcome.json", "source-before.json"):
        assert (upload / name).read_bytes() == (output / name).read_bytes()
    outcome = json.loads((upload / "outcome.json").read_text())
    assert outcome["status"] == "failed" and outcome["omission_not_run"]
    with tarfile.open(upload / "cases.tar.gz") as archive:
        assert archive.extractfile("cases/neutral/.hidden").read() == b"retained synthetic bytes\x00"
    assert (upload / "artifact-manifest.json").is_file()


def test_wrong_head_fails_before_child(case, monkeypatch):
    repo, output, _ = case
    def child(*args):
        pytest.fail("wrong head reached child dispatch")
    monkeypatch.setattr(runner, "pytest_child", child)
    assert invoke(repo, output, "0" * 40) == 1
    assert "exact selected source head" in json.loads((output / "outcome.json").read_text())["error"]


def test_finalizer_error_cannot_become_success(case, monkeypatch):
    repo, output, head = case
    monkeypatch.setattr(runner, "pytest_child", lambda repo, out, label, node, **kw: (fake_result(out, label, node), 0)[1])
    assert invoke(repo, output, head) == 0
    def fail(*args, **kwargs):
        raise OSError("intentional archive failure")
    monkeypatch.setattr(runner.tarfile, "open", fail)
    assert runner.finalize(repo, output, head) == 1
    retained = json.loads((output / "upload/case-manifest.json").read_text())
    assert retained['status'] == 'capture_failed'
    assert retained['error']['message'] == 'intentional archive failure'
    assert (output / 'upload/neutral.log').read_bytes() == (output / 'neutral.log').read_bytes()
    assert (output / "upload/artifact-manifest.json").is_file()


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

    class Child:
        pid = 87654
        returncode = 0

        def poll(self):
            return 0

        def wait(self, *, timeout):
            assert timeout == 5
            return 0

    def child(command, **kwargs):
        calls.append((command, kwargs))
        return Child()

    monkeypatch.setattr(runner.subprocess, "Popen", child)
    killed = []
    monkeypatch.setattr(runner.os, 'killpg', lambda pid, sig: killed.append((pid, sig)))
    label, node = runner.NODES[0]
    lock = output.parent / 'quiet-lock'
    assert runner.pytest_child(repo, output, label, node, quiet_lock=lock) == 0
    command, kwargs = calls[0]
    assert command == [runner.sys.executable, "-B", "-c", runner.BOOTSTRAP, "-q", "-p", "no:cacheprovider", '-o', 'addopts=',
                       "--basetemp", str(output / "cases/neutral"),
                       "--junitxml", str(output / "neutral.xml"), node]
    assert kwargs["cwd"] == repo and kwargs['start_new_session'] is True
    assert killed == [(Child.pid, runner.signal.SIGKILL)]
    recorded = json.loads((output / 'neutral-command.json').read_text())
    assert recorded['timeout_seconds'] == 3600
    assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    (output / "cases/neutral").mkdir()
    with pytest.raises(ValueError, match="basetemp must be fresh"):
        runner.pytest_child(repo, output, label, node, quiet_lock=lock)
    assert len(calls) == 1


def test_refuses_missing_isolation_declaration_or_held_quiet_lock(case, monkeypatch):
    repo, output, head = case
    monkeypatch.setattr(runner, 'source', lambda *a: pytest.fail('refusal reached source scan'))
    lock = output.parent / 'shared-lock'
    assert runner.run(repo, output, head, quiet_lock=lock) == 1
    assert 'network-denied' in json.loads((output / 'outcome.json').read_text())['error']
    lock.mkdir()
    out2 = output.with_name('locked-output')
    assert runner.run(repo, out2, head, quiet_lock=lock, network_denied=True) == 1
    assert 'quiet-window lock' in json.loads((out2 / 'outcome.json').read_text())['error']
    assert lock.is_dir()


def test_child_environment_strips_provider_account_and_pytest_injection(case, monkeypatch):
    repo, _, _ = case
    for key in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'CBORG_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN',
                'AWS_SECRET_ACCESS_KEY', 'PYTEST_ADDOPTS', 'PYTHONSTARTUP', 'GIT_DIR'):
        monkeypatch.setenv(key, 'synthetic-not-a-secret')
    environment = runner.child_environment(repo)
    assert all(key not in environment for key in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'CBORG_API_KEY',
        'CLAUDE_CODE_OAUTH_TOKEN', 'AWS_SECRET_ACCESS_KEY', 'PYTEST_ADDOPTS', 'PYTHONSTARTUP', 'GIT_DIR'))
    assert environment['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] == '1'
    assert environment['PYTHONPATH'].split(runner.os.pathsep) == [str(repo / 'src'), str(repo / 'scripts'), str(repo)]
    assert not any(name.endswith('.native_shared_execution') for name in runner.ORIGINS)
    assert 'data_sheets_schema.native_execution_authority_v2' in runner.ORIGINS
    assert 'data_sheets_schema.native_shared_execution_orchestration' in runner.ORIGINS


@pytest.mark.parametrize('limit', ['MAX_SOURCE_BYTES', 'MAX_SOURCE_ENTRIES'])
def test_source_bounds_fail_before_any_child(case, monkeypatch, limit):
    repo, output, head = case
    monkeypatch.setattr(runner, limit, 0)
    monkeypatch.setattr(runner, 'pytest_child', lambda *a, **k: pytest.fail('bounded scan reached child'))
    assert invoke(repo, output, head) == 1
    assert 'bound exceeded' in json.loads((output / 'outcome.json').read_text())['error']


@pytest.mark.parametrize('cause', ['clock', 'lock', 'log'])
def test_child_refusal_reaps_process_group_and_retains_diagnostic(case, monkeypatch, cause):
    repo, output, _ = case
    output.mkdir(); (output / 'cases').mkdir()
    lock = output.parent / 'quiet-window'
    events = []

    class Child:
        pid = 86543
        returncode = None

        def poll(self):
            if cause == 'lock':
                lock.mkdir()
            return None

        def wait(self, *, timeout):
            events.append(('reap', timeout))
            return -9

    def spawn(command, **kwargs):
        if cause == 'log':
            kwargs['stdout'].write(b'too-long'); kwargs['stdout'].flush()
        return Child()

    monkeypatch.setattr(runner.subprocess, 'Popen', spawn)
    monkeypatch.setattr(runner.os, 'killpg', lambda pid, sig: events.append(('kill', pid, sig)))
    if cause == 'clock':
        samples = iter((0, 3601))
        monkeypatch.setattr(runner.time, 'monotonic', lambda: next(samples))
    if cause == 'log':
        monkeypatch.setattr(runner, 'MAX_LOG_BYTES', 1)
    expected = TimeoutError if cause == 'clock' else ValueError
    with pytest.raises(expected):
        runner.pytest_child(repo, output, *runner.NODES[0], quiet_lock=lock)
    assert events == [('kill', Child.pid, runner.signal.SIGKILL), ('reap', 5)]
    assert (output / 'neutral-command.json').is_file()
    assert (output / 'neutral.log').is_file()
    if cause == 'lock':
        assert lock.is_dir()


@pytest.mark.parametrize('wait_times_out', [False, True])
def test_denied_cleanup_never_turns_reaped_leader_into_group_success(monkeypatch, wait_times_out):
    denial = PermissionError('synthetic denied signal')
    reaped = []

    class Child:
        pid = 12

        def wait(self, *, timeout):
            reaped.append(timeout)
            if wait_times_out:
                raise subprocess.TimeoutExpired('synthetic child', timeout)
            return 0

    def refuse(*args):
        raise denial

    monkeypatch.setattr(runner.os, 'killpg', refuse)
    with pytest.raises(PermissionError) as error:
        runner._stop(Child())
    assert error.value is denial and reaped == [5]
