"""Parent/runtime controls using fabricated child replies, never real dispatch.

No checkpoint builder, recovered code, helper, provider or interpreter fixture
is executed. Real bounded readers and executable identity helpers inspect only
temporary synthetic files and the reviewed diagnostic utility.
"""

from copy import deepcopy
import json
from pathlib import Path
import signal
import subprocess
from types import ModuleType, SimpleNamespace

import pytest


DRIVER = Path(__file__).resolve().parents[1] / "notes/native_full_schema_profile_2026-10-07/profile_checkpoint.py"


@pytest.fixture
def profile():
    module = ModuleType("_full_schema_parent_runtime_tests")
    module.__file__ = str(DRIVER)
    exec(compile(DRIVER.read_bytes(), str(DRIVER), "exec"), module.__dict__)
    return module


@pytest.fixture
def parent_case(profile, tmp_path, monkeypatch):
    tools = profile.utility()
    driver = tmp_path / "reviewed-driver.py"
    driver.write_bytes(DRIVER.read_bytes())
    monkeypatch.setattr(profile, "__file__", str(driver))
    monkeypatch.setattr(profile, "utility", lambda: tools)
    source, recovery, dependencies = [tmp_path / name for name in ("source", "recovery", "dependencies")]
    for path in (source, recovery, dependencies):
        path.mkdir()
        (path / "preserved.txt").write_bytes(("invented " + path.name).encode())
    interpreter, git = tmp_path / "python-not-executed", tmp_path / "git-not-executed"
    for executable in (interpreter, git):
        executable.write_bytes(b"SYNTHETIC EXECUTABLE IDENTITY ONLY\n")
        executable.chmod(0o700)
    alias = tmp_path / "python-alias"
    alias.symlink_to(interpreter)
    monkeypatch.setattr(profile, "sys", SimpleNamespace(executable=str(alias),
        flags=SimpleNamespace(isolated=1, no_site=1), dont_write_bytecode=True))
    monkeypatch.setattr(profile.shutil, "which", lambda name: str(git) if name == "git" else None)
    provenance = {"source_commit": profile.SOURCE_COMMIT, "synthetic_test": True}
    originals = {path: (path / "preserved.txt").read_bytes() for path in (source, recovery)}
    verifications = []

    def verify(selected_source, selected_recovery):
        assert (selected_source, selected_recovery) == (source, recovery)
        verifications.append(True)
        for path, raw in originals.items():
            profile.require(tools.read_file(path / "preserved.txt") == raw, "input pin changed")
        return {"provenance": deepcopy(provenance)}

    monkeypatch.setattr(tools, "verify_inputs", verify)
    checkpoint = tmp_path / "preparation"
    case = checkpoint / "case"
    case.mkdir(parents=True)
    (case / "retained.txt").write_bytes(b"Fictional prepared checkpoint; never executed\n")
    inventory = profile.tree_manifest(case, read=tools.read_file)
    selected = tools.executable_identity(interpreter)
    result = {
        "format": profile.CHILD_FORMAT, "mode": "prepare",
        "selection_relative": "authority/profile-selection.json", "declared_deadline_seconds": 900,
        "preparation_stages": [], "synthetic_parameters": {"fixture_only": True},
        "checkpoint": {"label": profile.LABEL, "complete": False, "workers_declared": 3,
                       "workers_consumed": 1, "receipt_consumed": True},
        "case_inventory": inventory,
        "loaded_closure": [{"origin": "dependency/preserved.txt",
                            "sha256": profile.sha((dependencies / "preserved.txt").read_bytes()),
                            "bytes": (dependencies / "preserved.txt").stat().st_size}],
        "python_identity": selected,
        "git": {"identity": tools.executable_identity(git), "calls": {}},
        "flags": {"isolated": 1, "no_site": 1, "dont_write_bytecode": True},
        "environment": {"python": "invented", "platform": "invented", "machine": "invented"},
        "recovered_provenance": provenance,
    }
    preparation = {"format": profile.FORMAT, "mode": "prepare", "status": "completed",
        "scientific_eligibility": False, "execution_authorized": False,
        "native_acceptance_evaluated": False, "historical_capture_complete": False,
        "utility_sha256": profile.UTILITY_SHA256, "driver_sha256": profile.sha(driver.read_bytes()),
        "python_identity": selected, "result": deepcopy(result)}
    (checkpoint / "report.json").write_bytes(profile.canonical(preparation))
    args = SimpleNamespace(command="prepare", source=source, recovery=recovery,
        dependencies=dependencies, checkpoint=checkpoint, output=tmp_path / "new-output")
    kills, invocations, communications = [], [], []
    monkeypatch.setattr(profile.os, "killpg", lambda pid, sig: kills.append((pid, sig)))

    def install(*, code=0, body=None, stderr=b"", timeout=False, timeout_exit=-signal.SIGKILL, after=None):
        selected_result = deepcopy(result)
        if args.command == "measure":
            for key in ("selection_relative", "declared_deadline_seconds", "preparation_stages",
                        "checkpoint", "synthetic_parameters"):
                selected_result.pop(key)
            selected_result.update(mode="measure", operations=[], projection={})
        raw = profile.canonical(selected_result) if body is None else body
        class Child:
            pid = 71999
            returncode = code

            def communicate(self, input=None, timeout=None):
                communications.append((input, timeout))
                if len(communications) == 1:
                    assert input is not None
                    config = json.loads(input)
                    if config["mode"] == "prepare" and code == 0 and not install_timeout:
                        fresh_case = Path(config["case"])
                        fresh_case.mkdir()
                        (fresh_case / "retained.txt").write_bytes((case / "retained.txt").read_bytes())
                    if after is not None:
                        after(config)
                    if install_timeout:
                        raise subprocess.TimeoutExpired("fixed reviewed child", timeout)
                if install_timeout:
                    self.returncode = timeout_exit
                return raw, stderr

        install_timeout = timeout
        def popen(argv, **kwargs):
            invocations.append((argv, kwargs))
            return Child()
        monkeypatch.setattr(profile.subprocess, "Popen", popen)
    return SimpleNamespace(args=args, tools=tools, source=source, recovery=recovery,
        dependencies=dependencies, checkpoint=checkpoint, case=case, driver=driver,
        interpreter=interpreter, git=git, selected=selected, result=result, preparation=preparation,
        original_case=inventory, verifications=verifications, invocations=invocations,
        communications=communications, kills=kills, install=install)


def report(case):
    return json.loads((case.args.output / "report.json").read_bytes())


@pytest.mark.parametrize("phase,bound", [("prepare", 900), ("measure", 600)])
def test_dispatch_uses_fixed_resolved_child_and_separate_phase_bound(profile, parent_case, monkeypatch,
                                                                  phase, bound):
    case = parent_case
    case.args.command = phase
    monkeypatch.setenv("PYTHONPATH", "/untrusted-python-path")
    monkeypatch.setenv("PYTHONSTARTUP", "/untrusted-startup")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("D4D_TEST_PRESERVED_ENV", "invented")
    case.install()
    assert profile.dispatch(case.args) == 0
    assert len(case.invocations) == len(case.communications) == 1
    argv, options = case.invocations[0]
    assert argv == [str(case.interpreter), "-I", "-B", "-S", str(case.driver), "_child"]
    assert options["cwd"] == case.source
    assert options["start_new_session"] is True
    assert options["stdin"] == options["stdout"] == options["stderr"] == subprocess.PIPE
    assert not any(key.startswith(("PYTHON", "GIT_")) for key in options["env"])
    assert options["env"]["D4D_TEST_PRESERVED_ENV"] == "invented"
    raw, timeout = case.communications[0]
    assert timeout == bound
    config = json.loads(raw)
    assert config["mode"] == phase and config["python_identity"] == case.selected
    assert config["source"] == str(case.source) and config["recovery"] == str(case.recovery)
    assert config["dependencies"] == str(case.dependencies) and config["git"] == str(case.git)
    assert config["case"] == str(case.args.output / "case" if phase == "prepare" else case.case)
    assert len(case.verifications) == 2
    value = report(case)
    assert value["status"] == "completed" and value["diagnostic_wall_bound_seconds"] == bound
    assert value["python_identity"] == case.selected
    assert value["driver_sha256"] == profile.sha(case.driver.read_bytes())
    assert value["utility_sha256"] == profile.UTILITY_SHA256
    assert value["declared_acceptance_deadline_seconds"] == 900
    assert all(value[field] is False for field in ("scientific_eligibility", "execution_authorized",
                "native_acceptance_evaluated", "historical_capture_complete"))
    assert profile.tree_manifest(case.case) == case.original_case


@pytest.mark.parametrize("phase", ["prepare", "measure"])
@pytest.mark.parametrize("already_exited", [False, True])
def test_timeout_always_reaps_and_retains_partial_new_case(profile, parent_case, monkeypatch,
                                                         phase, already_exited):
    case = parent_case
    case.args.command = phase
    def partial(config):
        if phase == "prepare":
            path = Path(config["case"])
            path.mkdir()
            (path / "partial.txt").write_bytes(b"retained incomplete fixture")
    case.install(timeout=True, timeout_exit=0 if already_exited else -signal.SIGKILL,
                 body=b'{"unaccepted_partial":true}', stderr=b"invented diagnostic", after=partial)
    if already_exited:
        def gone(pid, sig):
            case.kills.append((pid, sig))
            raise ProcessLookupError("child exited after timeout but before kill")
        monkeypatch.setattr(profile.os, "killpg", gone)
    assert profile.dispatch(case.args) == 1
    assert case.kills == [(71999, signal.SIGKILL)]
    assert len(case.communications) == 2 and case.communications[1] == (None, None)
    assert len(case.verifications) == 2
    value = report(case)
    assert value["status"] == "diagnostic_timeout" and value["result"] is None
    assert value["historical_capture_complete"] is False
    assert value["scientific_eligibility"] is False and value["execution_authorized"] is False
    assert b"unaccepted_partial" not in (case.args.output / "report.json").read_bytes()
    assert (case.args.output / "refusal.stderr").read_bytes() == b"invented diagnostic"
    if phase == "prepare":
        assert (case.args.output / "case/partial.txt").read_bytes() == b"retained incomplete fixture"
    assert profile.tree_manifest(case.case) == case.original_case


def test_nonzero_child_cannot_publish_a_completed_result_and_stderr_is_bounded(profile, parent_case):
    case = parent_case
    stderr = b"x" * (1024 * 1024 + 10)
    case.install(code=3, stderr=stderr)
    assert profile.dispatch(case.args) == 1
    value = report(case)
    assert value["status"] == "diagnostic_refused" and value["result"] is None
    assert value["child_exit_code"] == 3
    assert value["stderr_bytes"] == len(stderr) and value["stderr_sha256"] == profile.sha(stderr)
    assert (case.args.output / "refusal.stderr").stat().st_size == 1024 * 1024
    assert len(case.invocations) == 1


@pytest.mark.parametrize("fault", ["invalid_json", "child_size", "wrapped_report_size"])
def test_invalid_or_oversize_success_does_not_publish_partial_report(profile, parent_case, monkeypatch, fault):
    case = parent_case
    raw = profile.canonical(case.result)
    if fault == "invalid_json":
        raw = b"{"
    elif fault == "child_size":
        monkeypatch.setattr(profile, "MAX_REPORT_BYTES", len(raw) - 1)
    else:
        monkeypatch.setattr(profile, "MAX_REPORT_BYTES", len(raw) + 1)
    case.install(body=raw)
    expected = {"invalid_json": None, "child_size": "child result exceeds report bound",
                "wrapped_report_size": "publication exceeds complete report bound"}[fault]
    with pytest.raises(ValueError, match=expected):
        profile.dispatch(case.args)
    assert not (case.args.output / "report.json").exists()
    assert profile.tree_manifest(case.case) == case.original_case
    assert len(case.invocations) == 1


@pytest.mark.parametrize("fault", ["source", "interpreter", "interpreter_replaced", "git", "driver",
                                   "checkpoint_file", "preparation_report"])
def test_identity_drift_refuses_publication_after_child_completion(profile, parent_case, fault):
    case = parent_case
    case.args.command = "measure"
    def changed(config):
        if fault == "source":
            (case.source / "preserved.txt").write_bytes(b"foreign source")
        elif fault == "interpreter":
            case.interpreter.write_bytes(b"different executable")
        elif fault == "interpreter_replaced":
            replacement = case.interpreter.with_name("same-bytes-new-inode")
            replacement.write_bytes(case.interpreter.read_bytes())
            replacement.chmod(0o700)
            replacement.replace(case.interpreter)
        elif fault == "driver":
            case.driver.write_bytes(case.driver.read_bytes() + b"\n# changed\n")
        elif fault == "git":
            case.git.write_bytes(b"changed git executable")
        elif fault == "checkpoint_file":
            (case.case / "retained.txt").write_bytes(b"mutated checkpoint")
        else:
            (case.checkpoint / "report.json").write_bytes(b"mutated declaration")
    case.install(after=changed)
    with pytest.raises(ValueError):
        profile.dispatch(case.args)
    assert not (case.args.output / "report.json").exists()
    assert len(case.invocations) == 1


@pytest.mark.parametrize("fault", ["arbitrary_json", "missing_field", "extra_field", "phase",
                                   "python", "git", "provenance", "flags", "boolean_flag",
                                   "inventory", "git_call_count"])
def test_completed_child_must_match_selected_report_and_runtime(profile, parent_case, fault):
    case = parent_case
    changed = deepcopy(case.result)
    if fault == "arbitrary_json":
        changed = ["not a child report"]
    elif fault == "missing_field":
        changed.pop("case_inventory")
    elif fault == "extra_field":
        changed["scientific_eligibility"] = True
    elif fault == "phase":
        changed["mode"] = "measure"
    elif fault == "python":
        changed["python_identity"]["sha256"] = "0" * 64
    elif fault == "git":
        changed["git"]["identity"]["sha256"] = "0" * 64
    elif fault == "provenance":
        changed["recovered_provenance"]["source_commit"] = "foreign-source"
    elif fault in {"flags", "boolean_flag"}:
        changed["flags"]["isolated"] = True if fault == "boolean_flag" else 0
    elif fault == "inventory":
        changed["case_inventory"] = {"entries": {}, "files": 0, "bytes": 0}
    else:
        changed["git"]["calls"] = {"rev-parse HEAD": True}
    case.install(body=profile.canonical(changed))
    with pytest.raises(ValueError):
        profile.dispatch(case.args)
    assert not (case.args.output / "report.json").exists()
    assert len(case.invocations) == 1
    assert (case.args.output / "case/retained.txt").read_bytes() == (case.case / "retained.txt").read_bytes()


@pytest.mark.parametrize("fault", ["driver", "parent_python", "child_python", "git", "provenance", "flags"])
def test_preparation_cannot_cross_driver_runtime_or_recovered_source(profile, parent_case, fault):
    case = parent_case
    case.args.command = "measure"
    changed = deepcopy(case.preparation)
    if fault == "driver":
        changed["driver_sha256"] = "0" * 64
    elif fault == "parent_python":
        changed["python_identity"]["sha256"] = "0" * 64
    elif fault == "child_python":
        changed["result"]["python_identity"]["sha256"] = "0" * 64
    elif fault == "git":
        changed["result"]["git"]["identity"]["sha256"] = "0" * 64
    elif fault == "provenance":
        changed["result"]["recovered_provenance"]["source_commit"] = "foreign-source"
    else:
        changed["result"]["flags"]["no_site"] = 0
    (case.checkpoint / "report.json").write_bytes(profile.canonical(changed))
    case.install()
    with pytest.raises(ValueError):
        profile.dispatch(case.args)
    assert case.invocations == [] and not case.args.output.exists()
    assert profile.tree_manifest(case.case) == case.original_case


@pytest.mark.parametrize("destination", ["existing", "source_child", "recovery_child",
                                        "dependency_child", "checkpoint_child", "symlink_parent"])
def test_overlapping_or_existing_output_is_refused_before_launch(profile, parent_case, tmp_path, destination):
    case = parent_case
    case.args.command = "measure"
    if destination == "existing":
        case.args.output.mkdir()
        (case.args.output / "report.json").write_bytes(b"prior reviewed output")
    elif destination == "symlink_parent":
        alias = tmp_path / "output-alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        case.args.output = alias / "new"
    else:
        parent = {"source_child": case.source, "recovery_child": case.recovery,
                  "dependency_child": case.dependencies, "checkpoint_child": case.checkpoint}[destination]
        case.args.output = parent / "new"
    case.install()
    with pytest.raises(ValueError):
        profile.dispatch(case.args)
    assert case.invocations == []
    if destination == "existing":
        assert (case.args.output / "report.json").read_bytes() == b"prior reviewed output"
    else:
        assert not case.args.output.exists()


def test_absent_git_dependency_refuses_before_output_or_launch(profile, parent_case, monkeypatch):
    case = parent_case
    case.install()
    monkeypatch.setattr(profile.shutil, "which", lambda _: None)
    with pytest.raises(ValueError, match="Git dependency unavailable"):
        profile.dispatch(case.args)
    assert not case.args.output.exists() and case.invocations == []


@pytest.mark.parametrize("field", ["isolated", "no_site", "dont_write_bytecode"])
def test_parent_isolation_is_checked_before_utility_or_input_access(profile, parent_case, monkeypatch, field):
    case = parent_case
    if field == "dont_write_bytecode":
        profile.sys.dont_write_bytecode = False
    else:
        setattr(profile.sys.flags, field, 0)
    def forbidden():
        pytest.fail("unisolated parent reached diagnostic utility")
    monkeypatch.setattr(profile, "utility", forbidden)
    with pytest.raises(ValueError, match="requires -I -B -S isolation"):
        profile.dispatch(case.args)
    assert not case.args.output.exists() and case.verifications == []
