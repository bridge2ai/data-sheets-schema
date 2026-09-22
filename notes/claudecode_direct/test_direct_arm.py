"""The direct arm's preparer and launcher, offline (#2202). No model call, no login needed."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROLS = ROOT / "notes" / "matched_cborg_2026-09-13"
sys.path[:0] = [str(HERE), str(ROOT / "src"), str(CONTROLS), str(CONTROLS / "native_controls")]

import prepare_direct as preparation       # noqa: E402
import run_direct_canary as launcher       # noqa: E402
from budgeted_cborg import BudgetStop      # noqa: E402

AUTH = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    """A real registration for CHORUS rendered offline, with the login probe and the runtime pinned by stand-ins."""
    monkeypatch.chdir(ROOT)
    for name in preparation.FORBIDDEN_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    fake = tmp_path / "claude"
    fake.write_text("#!/bin/sh\necho '2.1.272 (Claude Code)'\n"); fake.chmod(0o700)
    monkeypatch.setattr(preparation, "auth_evidence", lambda executable, config: dict(AUTH))
    output = tmp_path / "registration"
    args = SimpleNamespace(output=output, project="CHORUS", claude_executable=str(fake), condition="generic_v9",
                           render_version=17, cohort="generalized_direct_v1", label_date="2026-09-22",
                           run_date="2026-09-22", deadline_seconds=21600, runaway_guard_usd="60")
    path = preparation.build(args)
    return path, json.loads(path.read_text()), fake


def test_the_registration_names_the_arm_and_asserts_its_effort_in_the_rendered_instruction(prepared):
    path, registration, fake = prepared
    job = registration["generation"]["jobs"][0]
    assert registration["arm"] == {**registration["arm"], "method": "claudecode_direct", "runtime": "Claude Code (direct)",
                                   "provider": "Anthropic (Claude subscription, direct)"}
    assert registration["model"] == {**registration["model"], "model": "claude-opus-5", "effort": "max"}
    assert registration["native_runtime"]["cli_flags"][-2:] == ["--effort", "max"]
    assert registration["native_runtime"]["expected_api_key_source"] == "none"
    assert registration["native_runtime"]["environment"]["CLAUDE_SECURESTORAGE_CONFIG_DIR"] == ""
    instruction = Path(job["instruction"]).read_text()
    assert "# Agent runtime: Claude Code (direct)" in instruction
    assert "# Provider: Anthropic (Claude subscription, direct)" in instruction
    assert "provenance record" in instruction and "--reasoning-effort max" in instruction
    assert job["render_spec"]["reasoning_effort"] == "max" and job["method"] == "claudecode_direct"
    # Output paths are checkout-relative, as in every registration; the launcher
    # verifies it runs from the registered checkout before it resolves them.
    assert all(d.startswith("data/d4d_concatenated/claudecode_direct") for d in job["output_directories"])
    assert not any((ROOT / d).exists() for d in job["output_directories"])
    for name in ("registration.json", "prompts"):
        assert (path.parent / name).exists()
    # Every pin reproduces; nothing under the CBORG registrations is pinned.
    pins = registration["pinned_files"]
    assert [p for p, h in pins.items() if not Path(p).is_file() or launcher.sha(p) != h] == []
    assert not any("matched_cborg_2026-09-1" in p and "native_controls" not in p and not p.endswith(("prepare_registration.py", "run_api_canary.py", "budgeted_cborg.py")) for p in pins)


def test_preparation_refuses_a_runtime_that_is_not_on_the_login(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    fake = tmp_path / "claude"; fake.write_text("#!/bin/sh\necho '2.1.272 (Claude Code)'\n"); fake.chmod(0o700)
    def not_logged_in(executable, config):
        raise preparation.DirectStop("the runtime is not on the maintainer's claude.ai login: {'loggedIn': False}")
    monkeypatch.setattr(preparation, "auth_evidence", not_logged_in)
    args = SimpleNamespace(output=tmp_path / "r", project="CHORUS", claude_executable=str(fake), condition="generic_v9",
                           render_version=17, cohort="generalized_direct_v1", label_date="2026-09-22",
                           run_date="2026-09-22", deadline_seconds=21600, runaway_guard_usd="60")
    with pytest.raises(preparation.DirectStop, match="claude.ai login"):
        preparation.build(args)
    assert not (tmp_path / "r" / "registration.json").exists()


def test_the_auth_probe_keeps_only_method_provider_and_plan(monkeypatch, tmp_path):
    calls = []
    def check_output(argv, env, text, timeout):
        calls.append((argv, env))
        return json.dumps({**AUTH, "email": "someone@example.org", "orgId": "org_secret", "token": "never"})
    monkeypatch.setattr(preparation.subprocess, "check_output", check_output)
    assert preparation.auth_evidence("/bin/claude", tmp_path) == AUTH
    argv, env = calls[0]
    assert argv[1:] == ["auth", "status", "--json"]
    assert env["CLAUDE_CONFIG_DIR"] == str(tmp_path) and env["CLAUDE_SECURESTORAGE_CONFIG_DIR"] == ""
    assert not any(name in env for name in preparation.FORBIDDEN_ENVIRONMENT)


def bind(tmp_path, path):
    review = tmp_path / "review.json"
    review.write_text(json.dumps({"verdict": "approve", "ci_conclusion": "success", "registration_sha256": launcher.sha(path),
                                  "allowed_jobs": ["CHORUS_direct_rep1"]}))
    word = tmp_path / "word.json"
    word.write_text(json.dumps({"registration_sha256": launcher.sha(path), "exact_response": "launch the direct canary",
                                "recorded_at": "2026-09-22T00:00:00+00:00"}))
    return review, word


def fake_child(*, apikey="none", result=True, denials=(), write_outputs=None):
    def execute_child(argv, *, proxy, instruction, attempt, cwd, env, deadline_seconds, verify_launch, record_stop=None,
                      command_policy=None, phase_spec=None, command_classifier=None, event_observer=None):
        verify_launch()
        assert not any(name in env for name in preparation.FORBIDDEN_ENVIRONMENT)
        assert env["CLAUDE_SECURESTORAGE_CONFIG_DIR"] == "" and env["CLAUDE_CONFIG_DIR"] == str(attempt / "cli_config")
        assert argv[argv.index("--effort") + 1] == "max" and "--max-budget-usd" in argv
        assert argv[argv.index("--model") + 1] == "claude-opus-5"
        events = [{"type": "system", "subtype": "init", "model": "claude-opus-5", "apiKeySource": apikey,
                   "claude_code_version": "2.1.272", "tools": ["Read", "Write", "Bash"]}]
        if result:
            events.append({"type": "result", "terminal_reason": "completed", "stop_reason": "end_turn", "is_error": False,
                           "num_turns": 7, "total_cost_usd": 12.5,
                           "usage": {"input_tokens": 1000, "output_tokens": 500},
                           "modelUsage": {"claude-opus-5": {"contextWindow": 200000, "maxOutputTokens": 64000}},
                           "permission_denials": list(denials)})
        (attempt / "transcript.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        (attempt / "control.jsonl").write_text("")
        if write_outputs:
            write_outputs()
        return 0
    return execute_child


@pytest.fixture
def offline_launch(prepared, tmp_path, monkeypatch):
    path, registration, fake = prepared
    review, word = bind(tmp_path, path)
    monkeypatch.setattr(preparation, "auth_evidence", lambda executable, config: dict(AUTH))
    real_check_output = launcher.subprocess.check_output
    def check_output(argv, *a, **kw):        # only the runtime's own version query is stood in for
        if argv[1:] == ["--version"]:
            return "2.1.272 (Claude Code)"
        return real_check_output(argv, *a, **kw)
    monkeypatch.setattr(launcher.subprocess, "check_output", check_output)
    monkeypatch.setattr(launcher, "check_control_history",
                        lambda *a, **k: {"checked": True, "problems": [], "persisted_output_paths": []})
    monkeypatch.setattr(launcher, "phase_history", lambda *a, **k: {"checked": True, "problems": []})
    monkeypatch.setattr(launcher.native, "command_history", lambda *a, **k: {"problems": []})
    monkeypatch.setattr(launcher, "check_canary_receipts", lambda *a, **k: {"passed": True})
    monkeypatch.setattr(launcher.native, "native_evidence_check", lambda *a: {"checked": True, "findings": []})
    from data_sheets_schema import api_runner, agentic_observed
    monkeypatch.setattr(api_runner, "validate_outputs", lambda *a: [])
    monkeypatch.setattr(api_runner, "pair_consistency", lambda *a: {"ran": True, "consistent": True})
    monkeypatch.setattr(agentic_observed, "observe", lambda *a, **k: {"usage_from_terminal_result": 1})
    job = registration["generation"]["jobs"][0]
    def write_outputs():
        for target in job["outputs"].values():
            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_text("synthetic\n")
    yield path, registration, review, word, write_outputs
    for directory in job["output_directories"]:
        import shutil
        shutil.rmtree(directory, ignore_errors=True)


def test_a_completed_offline_launch_reports_runtime_accounting_and_touches_no_ledger(offline_launch, monkeypatch):
    path, registration, review, word, write_outputs = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(write_outputs=write_outputs))
    code = launcher.main(["--registration", str(path), "--review", str(review), "--launch-word", str(word),
                          "--job", "CHORUS_direct_rep1"])
    receipt = json.loads((path.parent / "attempts" / "CHORUS_direct_rep1" / "result.json").read_text())
    assert code == 0 and receipt["status"] == "completed_pending_independent_review"
    assert receipt["runtime_reported_cost_usd"] == 12.5 and receipt["num_turns"] == 7
    assert receipt["runtime_usage"] == {"input_tokens": 1000, "output_tokens": 500}
    assert receipt["auth"] == AUTH and receipt["permission_denials"] == []
    assert receipt["arm"]["provider"] == "Anthropic (Claude subscription, direct)"
    assert not any("ledger" in key for key in receipt)
    assert not any(name in receipt["child_environment_names"] for name in preparation.FORBIDDEN_ENVIRONMENT)
    assert not (path.parent / "billing.json").exists()


def test_a_key_authenticated_runtime_is_refused_after_the_run(offline_launch, monkeypatch):
    path, registration, review, word, write_outputs = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(apikey="ANTHROPIC_API_KEY", write_outputs=write_outputs))
    code = launcher.main(["--registration", str(path), "--review", str(review), "--launch-word", str(word),
                          "--job", "CHORUS_direct_rep1"])
    receipt = json.loads((path.parent / "attempts" / "CHORUS_direct_rep1" / "result.json").read_text())
    assert code == 1 and receipt["status"] == "stopped"
    assert receipt["reason"] == "native runtime initialization differs from registration"
    assert receipt["reason_source"] == "controller"


def test_a_provider_key_in_the_environment_refuses_before_anything_is_created(offline_launch, monkeypatch):
    path, registration, review, word, _ = offline_launch
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-never")
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched with a key present"))
    with pytest.raises(BudgetStop, match="refuses provider keys"):
        launcher.main(["--registration", str(path), "--review", str(review), "--launch-word", str(word),
                       "--job", "CHORUS_direct_rep1"])
    assert not (path.parent / "attempts").exists()


def test_the_launch_word_must_name_this_exact_registration(offline_launch, monkeypatch, tmp_path):
    path, registration, review, word, _ = offline_launch
    other = tmp_path / "other-word.json"
    other.write_text(json.dumps({"registration_sha256": "0" * 64, "exact_response": "launch"}))
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched without the word"))
    with pytest.raises(BudgetStop, match="launch word"):
        launcher.main(["--registration", str(path), "--review", str(review), "--launch-word", str(other),
                       "--job", "CHORUS_direct_rep1"])
    assert not (path.parent / "attempts").exists()


def test_a_run_that_ends_without_a_result_line_is_a_named_stop(offline_launch, monkeypatch):
    path, registration, review, word, _ = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(result=False))
    code = launcher.main(["--registration", str(path), "--review", str(review), "--launch-word", str(word),
                          "--job", "CHORUS_direct_rep1"])
    receipt = json.loads((path.parent / "attempts" / "CHORUS_direct_rep1" / "result.json").read_text())
    assert code == 1 and receipt["status"] == "stopped" and receipt["transcript_terminal_result"] == "absent"
    assert receipt["reason_source"] == "controller" and "permission_denials_note" in receipt
