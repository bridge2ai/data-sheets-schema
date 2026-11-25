"""PR 6340 reviewer regressions for issues 6345, 6346 and 6347, 2026-11-25.

Inputs are synthetic records, fake credentials and fake executable session logs.
The Poetry control invokes the unchanged real validator and can mutate its input
after it exits. Outputs stay in pytest's retained external evidence directory.
No test uses the installed Codex binary, a provider or a real authentication file.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from unittest.mock import patch

import pytest

from tests.test_codex_rubric_scorer_instrument import ROOT, scenario, scorer


SENTINEL = "PR6340_FAKE_CREDENTIAL_SENTINEL_NOT_A_REAL_SECRET"


def reviewed_scenario(directory, **changes):
    args, tree, tools, evaluation = scenario(directory, **changes)
    args.auth_file.write_text(json.dumps({"review_only": SENTINEL}) + "\n")
    source = ROOT / "tests/fixtures/rubric_scorer/poetry_review_stub.py"
    (tools / "poetry").write_text("#!" + sys.executable + "\n" + source.read_text())
    (tools / "poetry").chmod(0o700)
    return args, tree, tools, evaluation


def assert_auth_cleaned(plan, args, original):
    assert args.auth_file.read_bytes() == original
    run = Path(plan["run_directory"])
    assert not list(run.rglob("auth.json"))
    retained = json.loads((run / "plan.json").read_bytes())
    assert all(Path(value).name != "auth.json" for value in plan["artifacts"].values())
    assert all(Path(value).name != "auth.json" for value in retained["artifacts"].values())
    receipt = json.loads((run / "receipt.json").read_bytes())
    assert receipt["auth_copy_absent"] is True
    for path in run.rglob("*"):
        if path.is_file():
            assert SENTINEL.encode() not in path.read_bytes(), path
    return receipt


def test_copied_auth_is_removed_after_success_and_refusals(tmp_path):
    for case in ("success", "wrong_model", "bad_score"):
        args, _, tools, evaluation = reviewed_scenario(tmp_path / case)
        original = args.auth_file.read_bytes()
        if case == "wrong_model":
            (tools / "case.json").write_text(json.dumps({"evaluation": evaluation, "model": "another-model"}))
        elif case == "bad_score":
            evaluation["overall_score"]["total_points"] -= 1
            (tools / "case.json").write_text(json.dumps({"evaluation": evaluation}))
        plan = scorer.build_plan(args)
        if case == "success":
            scorer.execute(plan, args)
            assert Path(plan["output"]).read_bytes() == (tools / "validated-snapshot.json").read_bytes()
        else:
            with pytest.raises(scorer.ScorerError):
                scorer.execute(plan, args)
            assert not Path(plan["output"]).exists()
        invocation = json.loads((tools / "invocation.json").read_bytes())
        assert invocation["copied_auth_present"] is True
        assert invocation["copied_auth_mode"] == 0o600
        receipt = assert_auth_cleaned(plan, args, original)
        assert receipt["status"] == ("VALIDATED_AND_PUBLISHED" if case == "success" else "REFUSED")
        if (tools / "real-validator-result.json").exists():
            checked = json.loads((tools / "real-validator-result.json").read_bytes())
            assert checked["copied_auth_present_at_validation"] is False


def test_copied_auth_is_removed_after_a_real_stub_timeout(tmp_path):
    args, _, tools, _ = reviewed_scenario(tmp_path / "timeout", sleep_seconds=30)
    original = args.auth_file.read_bytes()
    args.timeout = 1
    plan = scorer.build_plan(args)
    with pytest.raises(subprocess.TimeoutExpired):
        scorer.execute(plan, args)
    assert json.loads((tools / "invocation.json").read_bytes())["copied_auth_present"] is True
    assert not Path(plan["output"]).exists()
    assert assert_auth_cleaned(plan, args, original)["status"] == "REFUSED"


def test_copied_auth_is_removed_after_interrupt_and_spawn_failure(tmp_path):
    for case in ("interrupt", "spawn_failure"):
        args, _, _, _ = reviewed_scenario(tmp_path / case)
        original = args.auth_file.read_bytes()
        plan = scorer.build_plan(args)

        def interrupt(command, prompt, working, env, stdout, stderr, timeout):
            assert (Path(env["CODEX_HOME"]) / "auth.json").read_bytes() == original
            raise KeyboardInterrupt("synthetic interruption after authentication copy")

        if case == "interrupt":
            with patch.object(scorer, "bounded_codex", side_effect=interrupt):
                with pytest.raises(KeyboardInterrupt):
                    scorer.execute(plan, args)
        else:
            with patch.object(scorer.subprocess, "Popen", side_effect=OSError("synthetic spawn failure")):
                with pytest.raises(OSError):
                    scorer.execute(plan, args)
        assert not Path(plan["output"]).exists()
        assert assert_auth_cleaned(plan, args, original)["status"] == "REFUSED"


def test_partial_auth_copy_is_removed_without_touching_source(tmp_path):
    args, _, _, _ = reviewed_scenario(tmp_path / "partial-write")
    original = args.auth_file.read_bytes()
    plan = scorer.build_plan(args)
    original_fdopen = scorer.os.fdopen

    class BrokenWrite:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def write(self, data):
            self.stream.write(data[:1])
            self.stream.flush()
            raise OSError("synthetic partial authentication copy")

        def __exit__(self, kind, value, traceback):
            self.stream.close()

    def fdopen(descriptor, mode, *args, **kwargs):
        stream = original_fdopen(descriptor, mode, *args, **kwargs)
        return BrokenWrite(stream) if mode == "wb" else stream

    with patch.object(scorer.os, "fdopen", side_effect=fdopen):
        with pytest.raises(OSError):
            scorer.execute(plan, args)
    assert not Path(plan["output"]).exists()
    assert assert_auth_cleaned(plan, args, original)["status"] == "REFUSED"


def test_sigterm_runs_auth_cleanup_in_the_real_cli_controller(tmp_path):
    args, _, tools, _ = reviewed_scenario(tmp_path / "sigterm", sleep_seconds=30)
    args.timeout = 60
    original = args.auth_file.read_bytes()
    plan = scorer.build_plan(args)
    command = [sys.executable, str(scorer.__file__), "--execute"]
    for name in ("repo_root", "method_directory", "label", "record", "rubric", "run_directory",
                 "codex_binary", "poetry_binary", "validation_venv", "auth_file",
                 "authorization_reference", "timeout"):
        command.extend(["--" + name.replace("_", "-"), str(getattr(args, name))])
    child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        while not (tools / "invocation.json").exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (tools / "invocation.json").is_file()
        child.send_signal(signal.SIGTERM)
        stdout, stderr = child.communicate(timeout=10)
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.communicate(timeout=10)
    (tmp_path / "controller.stdout.txt").write_bytes(stdout)
    (tmp_path / "controller.stderr.txt").write_bytes(stderr)
    assert child.returncode != 0
    assert not Path(plan["output"]).exists()
    assert assert_auth_cleaned(plan, args, original)["status"] == "REFUSED"


def test_post_validation_candidate_replacement_refuses_publication(tmp_path):
    args, _, tools, _ = reviewed_scenario(tmp_path / "validator-drift", post_validator_drift=True)
    original = args.auth_file.read_bytes()
    plan = scorer.build_plan(args)
    with pytest.raises(scorer.ScorerError):
        scorer.execute(plan, args)
    checked = json.loads((tools / "real-validator-result.json").read_bytes())
    assert checked["returncode"] == 0
    assert checked["post_validation_drift_applied"] is True
    assert checked["candidate_after_sha256"] != checked["accepted_snapshot_sha256"]
    assert not Path(plan["output"]).exists()
    receipt = assert_auth_cleaned(plan, args, original)
    assert receipt["validator_exit"] == 0
    assert receipt["status"] == "REFUSED"


def test_publication_never_uses_a_later_candidate_reread(tmp_path):
    args, _, tools, _ = reviewed_scenario(tmp_path / "after-check-drift")
    original = args.auth_file.read_bytes()
    plan = scorer.build_plan(args)
    physical = scorer.physical
    mutated = False

    def mutate_at_output(path):
        nonlocal mutated
        if Path(path) == Path(plan["output"]) and (tools / "real-validator-result.json").exists():
            candidate = Path(plan["run_directory"]) / "candidate_evaluation.json"
            candidate.write_bytes(b"LATE SYNTHETIC DRIFT AFTER VALIDATION CHECK\n")
            mutated = True
        return physical(path)

    with patch.object(scorer, "physical", side_effect=mutate_at_output):
        try:
            scorer.execute(plan, args)
        except scorer.ScorerError:
            assert not Path(plan["output"]).exists()
        else:
            accepted = (tools / "validated-snapshot.json").read_bytes()
            assert Path(plan["output"]).read_bytes() == accepted
            receipt = json.loads((Path(plan["run_directory"]) / "receipt.json").read_bytes())
            assert receipt["output_sha256"] == hashlib.sha256(accepted).hexdigest()
    assert mutated
    assert_auth_cleaned(plan, args, original)


def test_child_qualification_requires_its_own_turn_evidence(tmp_path):
    cases = [
        {"child_inherited_only": True},
        {"child_inherited_only": True, "child_assistant_model": "another-model"},
        {"child_model": "another-model"},
        {"child_effort": "low"},
        {"child_cwd": "/synthetic/outside"},
        {"child_marker_missing": True},
        {"child_boundary": 0},
        {"child_boundary": True},
        {"child_settings_thread": "foreign-thread"},
        {"child_turn": "stub-root-turn"},
        {"child_turn": "unstarted-child-turn"},
    ]
    for index, changes in enumerate(cases):
        args, _, _, _ = reviewed_scenario(tmp_path / f"ownership-{index}", child=True, **changes)
        original = args.auth_file.read_bytes()
        plan = scorer.build_plan(args)
        with pytest.raises(scorer.ScorerError):
            scorer.execute(plan, args)
        assert not Path(plan["output"]).exists()
        assert assert_auth_cleaned(plan, args, original)["status"] == "REFUSED"


def test_correlated_tools_and_consistent_model_fields_are_required(tmp_path):
    cases = [
        {"orphan_output": "root"},
        {"orphan_output": "child"},
        {"inherited_orphan_output": True},
        {"move_spawn_output_to_child": True},
        {"missing_spawn_output": True},
        {"root_assistant_model": "another-model"},
        {"child_assistant_model": "another-model"},
        {"child_custom_tool": True},
    ]
    for index, changes in enumerate(cases):
        args, _, _, _ = reviewed_scenario(tmp_path / f"correlation-{index}", child=True, **changes)
        original = args.auth_file.read_bytes()
        plan = scorer.build_plan(args)
        with pytest.raises(scorer.ScorerError):
            scorer.execute(plan, args)
        assert not Path(plan["output"]).exists()
        assert assert_auth_cleaned(plan, args, original)["status"] == "REFUSED"


def test_verified_child_boundary_with_own_turn_passes_real_validation(tmp_path):
    for index, changes in enumerate(({}, {"child_boundary_missing": True})):
        args, _, tools, _ = reviewed_scenario(tmp_path / f"owned-child-positive-{index}", child=True, **changes)
        original = args.auth_file.read_bytes()
        plan = scorer.build_plan(args)
        scorer.execute(plan, args)
        accepted = (tools / "validated-snapshot.json").read_bytes()
        assert Path(plan["output"]).read_bytes() == accepted
        output = json.loads(accepted)
        assert len(output["evaluation_model"]["session_logs"]) == 2
        assert assert_auth_cleaned(plan, args, original)["status"] == "VALIDATED_AND_PUBLISHED"
