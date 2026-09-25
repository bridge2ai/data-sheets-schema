"""The direct arm's preparer and launcher, offline (#2202). No model call, no login needed.

One test per guard (#2209, #2253, #2275): the third-round mutation pass over
the launcher and the preparer (215 mutants: guard removal, `raise` to `pass`,
boolean-operand neutralisation) left seven equivalent survivors and four
gaps this file has since closed. The equivalents: the stop path's shortcut
past `stopped_denials` (the same result line classified twice), the
`__main__` line, the absolute-path operands the prefix test and
`resolve(strict=True)` already imply, the `path.is_file()` operand of the pin
walk, and the stop-path renderer bound every direct rendering satisfies.
Every assertion on the child's environment is made on an input the guard
has not already filtered.
"""
import json
import os
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace
import uuid

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROLS = ROOT / "notes" / "matched_cborg_2026-09-13"
sys.path[:0] = [str(HERE), str(ROOT / "src"), str(CONTROLS), str(CONTROLS / "native_controls")]

import prepare_direct as preparation       # noqa: E402
import run_direct_canary as launcher       # noqa: E402
from budgeted_cborg import BudgetStop      # noqa: E402

AUTH = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}
JOB = "CHORUS_direct_rep1"
LAUNCH_ONLY = {"CLAUDE_CONFIG_DIR", "PYTHONPATH", "VIRTUAL_ENV"}


def remove_if_empty(directory):
    """The two method directories exist only for these tests until the arm's first record (#2219)."""
    try:
        Path(directory).rmdir()
    except OSError:
        pass


def arguments(tmp_path, fake, **overrides):
    # The cohort is one production cannot produce (#2218): the preparer refuses
    # an existing output directory, so a fixture label equal to a real record's
    # would fail every test here on the day the arm's first record lands. It
    # is also unique per call (#2254): the planned output directories are
    # under the checkout's corpus tree, and two tests on two xdist workers
    # must never plan one path.
    values = dict(output=tmp_path / "registration", project="CHORUS", claude_executable=str(fake), condition="generic_v9",
                  render_version=17, cohort=f"test_fixture_{uuid.uuid4().hex[:8]}", label_date="2026-09-22",
                  run_date="2026-09-22", deadline_seconds=21600, runaway_guard_usd="60",
                  context_window=200000, max_output_tokens=64000)
    values.update(overrides)
    assert values["cohort"] != preparation.DEFAULT_COHORT, "the fixture cohort must not be the production default"
    return SimpleNamespace(**values)


def test_the_fixture_cohort_is_one_production_does_not_produce_by_default(tmp_path):
    """#2228: the #2218 fix was guarded by nothing; #2254: two fixtures never share a cohort."""
    fixture = arguments(tmp_path, tmp_path / "claude")
    assert fixture.cohort.startswith("test_fixture_") and preparation.DEFAULT_COHORT == "generalized_direct_v1"
    assert fixture.cohort != arguments(tmp_path, tmp_path / "claude").cohort
    assert "-test-fixture-" not in preparation.DEFAULT_COHORT.replace("_", "-")
    # The preparer's own parser default is the production cohort, not the fixture's (#2258).
    parsed = preparation.parser().parse_args(["--output", "somewhere"])
    assert parsed.cohort == preparation.DEFAULT_COHORT != fixture.cohort
    assert (parsed.context_window, parsed.max_output_tokens) == (200000, 64000)


def fake_runtime(tmp_path, version="2.1.272 (Claude Code)"):
    fake = tmp_path / "claude"
    fake.write_text(f"#!/bin/sh\necho '{version}'\n")
    fake.chmod(0o700)
    return fake


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    """A real registration for CHORUS rendered offline, with the login probe and the runtime pinned by stand-ins."""
    monkeypatch.chdir(ROOT)
    for name in preparation.FORBIDDEN_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    fake = fake_runtime(tmp_path)
    monkeypatch.setattr(preparation, "auth_evidence", lambda executable, env: dict(AUTH))
    path = preparation.build(arguments(tmp_path, fake))
    return path, json.loads(path.read_text()), fake


# --- the preparer -----------------------------------------------------------

def test_the_registration_names_the_arm_and_asserts_its_effort_in_the_rendered_instruction(prepared):
    path, registration, fake = prepared
    job = registration["generation"]["jobs"][0]
    assert registration["arm"] == {**registration["arm"], "method": "claudecode_direct", "runtime": "Claude Code (direct)",
                                   "provider": "Anthropic (Claude subscription, direct)"}
    assert registration["model"] == {**registration["model"], "model": "claude-opus-5", "effort": "max",
                                     "auxiliary_models_permitted": list(preparation.AUXILIARY_MODELS)}
    assert registration["native_runtime"]["cli_flags"][-2:] == ["--effort", "max"]
    assert registration["native_runtime"]["expected_api_key_source"] == "none"
    assert registration["native_runtime"]["environment"] == preparation.CHILD_ENVIRONMENT
    assert registration["native_runtime"]["environment"]["CLAUDE_SECURESTORAGE_CONFIG_DIR"] == ""
    assert registration["native_runtime"]["environment"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"
    instruction = Path(job["instruction"]).read_text()
    assert "# Agent runtime: Claude Code (direct)" in instruction
    assert "# Provider: Anthropic (Claude subscription, direct)" in instruction
    assert "provenance record" in instruction and "--reasoning-effort max" in instruction
    assert job["render_spec"]["reasoning_effort"] == "max"
    # The recorder reads the launch instruction by variable name: no shell expansion (#2282).
    assert job["render_spec"]["prompt_text_env"] is True
    assert "--prompt-text-env D4D_LAUNCH_INSTRUCTION" in instruction and "${D4D_LAUNCH_INSTRUCTION" not in instruction
    assert (job["method"], job["runtime"], job["execution_arm"]) == ("claudecode_direct", "Claude Code (direct)", "direct")
    # Output paths are checkout-relative, as in every registration; the launcher
    # verifies it runs from the registered checkout before it resolves them.
    assert all(launcher.under_direct_roots(d) for d in job["output_directories"] + list(job["outputs"].values()))
    assert not any((ROOT / d).exists() for d in job["output_directories"])
    assert sorted(p.name for p in path.parent.iterdir()) == ["prompts", "registration.json"]
    assert re.fullmatch(r"2026-09-22_claude-opus-5-direct-test-fixture-[0-9a-f]{8}-chorus_rep1", job["label"])
    assert "# Model: claude-opus-5" in instruction
    assert registration["model"]["limits_expected"] == {"contextWindow": 200000, "maxOutputTokens": 64000}
    assert registration["model"]["limits_basis"].startswith("the preparer's defaults")
    assert registration["native_runtime"]["executable"] in registration["pinned_files"]
    assert Path(registration["native_runtime"]["system_prompt"]).resolve() == (HERE / "system.md").resolve()
    assert registration["native_runtime"]["environment"]["CLAUDE_CODE_DISABLE_1M_CONTEXT"] == "1"
    assert registration["native_runtime"]["forbidden_environment"] == list(preparation.FORBIDDEN_ENVIRONMENT)
    assert set(registration["per_job_environment"][JOB]) == set(preparation.PER_JOB_NAMES)
    # Every pin reproduces; the playbooks, the schema sources, the prompts and
    # the arm's own scripts are pinned; nothing under the CBORG registrations is.
    pins = registration["pinned_files"]
    assert [p for p, h in pins.items() if not Path(p).is_file() or launcher.sha(p) != h] == []
    for expected in (".claude/commands/d4d-full-core.md", ".claude/agents/d4d-review-record.md",
                     "src/data_sheets_schema/runs.py", "src/download/prompts/canonical_hashes.yaml",
                     "notes/claudecode_direct/run_direct_canary.py", "native_controls/run_native_canary.py"):
        assert any(p.endswith(expected) for p in pins), expected
    assert not any(p.endswith((".pyc", ".txt.bak")) or Path(p).is_dir() for p in pins)
    assert not any("matched_cborg_2026-09-1" in p and "native_controls" not in p and not p.endswith(("prepare_registration.py", "run_api_canary.py", "budgeted_cborg.py")) for p in pins)


def test_preparation_refuses_a_runtime_that_is_not_on_the_login(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    fake = fake_runtime(tmp_path)
    def not_logged_in(executable, env):
        raise preparation.DirectStop("the runtime is not on the maintainer's claude.ai login: {'loggedIn': False}")
    monkeypatch.setattr(preparation, "auth_evidence", not_logged_in)
    with pytest.raises(preparation.DirectStop, match="claude.ai login"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r"))
    # A refused login leaves nothing: no registration directory, no probe directory (#2317).
    assert not (tmp_path / "r").exists()
    assert not list(tmp_path.glob(".r.auth-probe-*"))


def test_the_preparer_refuses_the_wrong_directory_an_existing_registration_and_existing_output(tmp_path, monkeypatch):
    fake = fake_runtime(tmp_path)
    monkeypatch.setattr(preparation, "auth_evidence", lambda executable, env: dict(AUTH))
    elsewhere = tmp_path / "elsewhere"; elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    with pytest.raises(preparation.DirectStop, match="prepare from the checkout root"):
        preparation.build(arguments(tmp_path, fake))
    monkeypatch.chdir(ROOT)
    (tmp_path / "registration").mkdir()
    with pytest.raises(preparation.DirectStop, match="registration directory already exists"):
        preparation.build(arguments(tmp_path, fake))
    cohort = f"test_fixture_{uuid.uuid4().hex[:8]}"
    planned = ROOT / f"data/d4d_concatenated/claudecode_direct/2026-09-22_claude-opus-5-direct-{cohort.replace('_', '-')}-chorus_rep1"
    planned.mkdir(parents=True)
    try:
        with pytest.raises(preparation.DirectStop, match="planned output directory already exists"):
            preparation.build(arguments(tmp_path, fake, output=tmp_path / "r2", cohort=cohort))
    finally:
        shutil.rmtree(planned)
        remove_if_empty(planned.parent)
    assert not (tmp_path / "r2").exists()
    with pytest.raises(preparation.DirectStop, match="limits must be positive"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r3", context_window=0))
    assert not (tmp_path / "r3").exists()
    # A project whose minted job id is not a single path component is refused before the registry is read (#2276).
    with pytest.raises(preparation.DirectStop, match="not a single path component"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r4", project="Kids.First"))
    assert not (tmp_path / "r4").exists()
    # The limits basis says where the values came from (#2267).
    given = preparation.build(arguments(tmp_path, fake, output=tmp_path / "r5", context_window=1_000_000))
    assert json.loads(given.read_text())["model"]["limits_basis"].startswith("given on the preparer's command line")
    assert json.loads(given.read_text())["model"]["limits_expected"]["contextWindow"] == 1_000_000


def test_the_preparer_refuses_an_instruction_that_is_not_the_direct_arms(tmp_path, monkeypatch):
    fake = fake_runtime(tmp_path)
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(preparation, "auth_evidence", lambda executable, env: dict(AUTH))
    RunSpec = preparation.generation.api_runner.RunSpec
    real = RunSpec.instruction
    for rendered, match in (("# Agent runtime: Claude Code (direct)\n# Provider: Anthropic (Claude subscription, direct)\n"
                             "# Model: claude-opus-5\n d4d provenance record --manifest none\n", "does not assert the registered effort"),
                            ("# Agent runtime: Claude Code (direct)\n# Model: claude-opus-5\n"
                             " d4d provenance record --reasoning-effort max\n", "runtime, provider and model"),
                            ("# Agent runtime: Claude Code (direct)\n# Provider: Anthropic (Claude subscription, direct)\n"
                             " d4d provenance record --reasoning-effort max\n", "runtime, provider and model"),
                            ("# Provider: Anthropic (Claude subscription, direct)\n# Model: claude-opus-5\n"
                             " d4d provenance record --reasoning-effort max\n", "runtime, provider and model")):
        monkeypatch.setattr(RunSpec, "instruction", property(lambda self, text=rendered: text))
        with pytest.raises(preparation.DirectStop, match=match):
            preparation.build(arguments(tmp_path, fake, output=tmp_path / "r"))
        assert not (tmp_path / "r").exists() or not (tmp_path / "r" / "registration.json").exists()
        shutil.rmtree(tmp_path / "r", ignore_errors=True)
    monkeypatch.setattr(RunSpec, "instruction", real)
    # A recorder line with a shell expansion, or an apostrophe in the specification, cannot run (#2282).
    expansion = real.func                    # `instruction` is a cached_property
    monkeypatch.setattr(RunSpec, "instruction", property(lambda self: expansion(self).replace(
        "--prompt-text-env D4D_LAUNCH_INSTRUCTION", '--prompt-text "${D4D_LAUNCH_INSTRUCTION:?x}"')))
    with pytest.raises(preparation.DirectStop, match="must read the launch instruction by --prompt-text-env"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r4"))
    assert not (tmp_path / "r4").exists()                     # refused before anything is written
    # Both the flag and an expansion on one line: the expansion alone refuses it.
    monkeypatch.setattr(RunSpec, "instruction", property(lambda self: expansion(self).replace(
        "--prompt-text-env D4D_LAUNCH_INSTRUCTION", '--prompt-text-env D4D_LAUNCH_INSTRUCTION "${HOME}"')))
    with pytest.raises(preparation.DirectStop, match="must read the launch instruction by --prompt-text-env"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r4b"))
    assert not (tmp_path / "r4b").exists()
    # No recorder line at all, with the effort still stated elsewhere.
    monkeypatch.setattr(RunSpec, "instruction", property(lambda self: "\n".join(
        "note: --reasoning-effort max" if " -m data_sheets_schema.cli provenance record" in line else line
        for line in expansion(self).splitlines())))
    with pytest.raises(preparation.DirectStop, match="must read the launch instruction by --prompt-text-env"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r4c"))
    assert not (tmp_path / "r4c").exists()
    monkeypatch.setattr(RunSpec, "instruction", real)
    rendered = RunSpec.render_spec
    monkeypatch.setattr(RunSpec, "render_spec", lambda self: {**rendered(self), "manifest_line": "# child's manifest"})
    with pytest.raises(preparation.DirectStop, match="carries an apostrophe"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r5"))
    assert not (tmp_path / "r5").exists()
    monkeypatch.setattr(RunSpec, "render_spec", rendered)
    monkeypatch.setattr(RunSpec, "is_agentic", property(lambda self: False))
    with pytest.raises(preparation.DirectStop, match="rendering specification is refused: prompt_text_env applies only to agentic"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r3"))
    assert not (tmp_path / "r3").exists()


def test_the_preparer_probes_the_login_in_the_childs_exact_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("UNRELATED_PARENT_VARIABLE", "never")
    fake = fake_runtime(tmp_path)
    seen = {}
    def probe(executable, env):
        seen.update(executable=executable, env=dict(env), probe_dir_existed=Path(env["CLAUDE_CONFIG_DIR"]).is_dir())
        return dict(AUTH)
    monkeypatch.setattr(preparation, "auth_evidence", probe)
    path = preparation.build(arguments(tmp_path, fake))
    registration = json.loads(path.read_text())
    per_job = registration["per_job_environment"][JOB]
    assert seen["executable"] == str(fake) and seen["probe_dir_existed"]
    assert seen["env"] == {**seen["env"], **preparation.CHILD_ENVIRONMENT, **per_job}
    probe_dir = Path(seen["env"]["CLAUDE_CONFIG_DIR"])
    assert probe_dir.parent == path.parent.parent and probe_dir.name.startswith(f".{path.parent.name}.auth-probe-")
    assert not probe_dir.exists()
    assert "UNRELATED_PARENT_VARIABLE" not in seen["env"]
    assert set(seen["env"]) <= set(preparation.PARENT_PASSTHROUGH) | set(preparation.CHILD_ENVIRONMENT) | set(per_job) | {"CLAUDE_CONFIG_DIR"}


def test_the_auth_probe_keeps_only_method_provider_and_plan(monkeypatch, tmp_path):
    calls = []
    def check_output(argv, env, text, timeout):
        calls.append((argv, env))
        return json.dumps({**AUTH, "email": "someone@example.org", "orgId": "org_secret", "token": "never"})
    monkeypatch.setattr(preparation.subprocess, "check_output", check_output)
    env = {"CLAUDE_CONFIG_DIR": str(tmp_path), "CLAUDE_SECURESTORAGE_CONFIG_DIR": "", "PATH": os.environ.get("PATH", "")}
    assert preparation.auth_evidence("/bin/claude", env) == AUTH
    argv, seen = calls[0]
    assert argv == ["/bin/claude", "auth", "status", "--json"]
    assert seen == env                                   # the probe runs in exactly the environment it is given
    for reported in ({**AUTH, "loggedIn": False}, {**AUTH, "authMethod": "console"},
                     {**AUTH, "apiProvider": "bedrock"}, {**AUTH, "subscriptionType": "pro"}):
        monkeypatch.setattr(preparation.subprocess, "check_output", lambda *a, **k: json.dumps(reported))
        with pytest.raises(preparation.DirectStop, match="claude.ai login"):
            preparation.auth_evidence("/bin/claude", env)


def test_the_child_environment_is_screened_wherever_its_values_come_from(tmp_path, monkeypatch):
    monkeypatch.setenv("UNRELATED_PARENT_VARIABLE", "never")
    monkeypatch.setenv("PATH", "/usr/bin")
    per_job = {"D4D_MANIFEST": "m.yaml", "D4D_PROFILE": "bridge2ai", "D4D_LAUNCH_INSTRUCTION": "i.md"}
    env = preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, per_job)
    assert env == {**env, **preparation.CHILD_ENVIRONMENT, **per_job, "CLAUDE_CONFIG_DIR": str(tmp_path), "PATH": "/usr/bin"}
    assert "UNRELATED_PARENT_VARIABLE" not in env
    assert set(env) <= set(preparation.PARENT_PASSTHROUGH) | set(preparation.CHILD_ENVIRONMENT) | set(per_job) | {"CLAUDE_CONFIG_DIR"}
    # A forbidden name in the job's variables is refused although the parent's environment never carried it.
    with pytest.raises(preparation.DirectStop, match="must not carry.*ANTHROPIC_BASE_URL"):
        preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, {**per_job, "ANTHROPIC_BASE_URL": "http://x"})
    # A registered child environment that is not the preparer's is refused, whatever it carries.
    with pytest.raises(preparation.DirectStop, match="differs from the preparer's"):
        preparation.child_environment(tmp_path, {**preparation.CHILD_ENVIRONMENT, "ANTHROPIC_API_KEY": "sk"}, per_job)
    with pytest.raises(preparation.DirectStop, match="differs from the preparer's"):
        preparation.child_environment(tmp_path, {k: v for k, v in preparation.CHILD_ENVIRONMENT.items() if k != "CLAUDE_SECURESTORAGE_CONFIG_DIR"}, per_job)
    # The parent's own key never passes through: it is not a pass-through name.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-parent")
    assert "ANTHROPIC_API_KEY" not in preparation.child_environment(tmp_path, None, per_job)
    # Nor does the recorder's corroboration variable, which is deliberately not forbidden (#2270).
    monkeypatch.setenv("CLAUDE_EFFORT", "low")
    assert "CLAUDE_EFFORT" not in preparation.FORBIDDEN_ENVIRONMENT
    assert "CLAUDE_EFFORT" not in preparation.child_environment(tmp_path, None, per_job)
    assert preparation.child_environment(tmp_path, None, per_job)["CLAUDE_CODE_DISABLE_1M_CONTEXT"] == "1"
    # No job variables at all is a valid call.
    bare = preparation.child_environment(tmp_path, None, None)
    assert set(bare) <= set(preparation.PARENT_PASSTHROUGH) | set(preparation.CHILD_ENVIRONMENT) | {"CLAUDE_CONFIG_DIR"}


def test_the_jobs_variables_are_an_allowlist_not_a_denylist(tmp_path, monkeypatch):
    """#2244: every value the binary reads reached the child through the job's variables."""
    per_job = {"D4D_MANIFEST": "m.yaml", "D4D_PROFILE": "bridge2ai", "D4D_LAUNCH_INSTRUCTION": "i.md"}
    # The probe's exact payload: lower-case proxies, cloud base URLs, TLS and model overrides.
    for name in ("https_proxy", "http_proxy", "GLOBAL_AGENT_HTTP_PROXY", "ANTHROPIC_BEDROCK_BASE_URL", "NODE_EXTRA_CA_CERTS",
                 "NODE_TLS_REJECT_UNAUTHORIZED", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL"):
        assert name in preparation.FORBIDDEN_ENVIRONMENT, name
        with pytest.raises(preparation.DirectStop, match=f"must not carry.*{name}"):
            preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, {**per_job, name: "x"})
    # A name the denylist does not know is refused by the allowlist, whatever its value.
    with pytest.raises(preparation.DirectStop, match="may add only.*refused: SOME_FUTURE_VARIABLE"):
        preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, {**per_job, "SOME_FUTURE_VARIABLE": "x"})
    # A registered constant cannot be shadowed: the traffic setting stays 1.
    with pytest.raises(preparation.DirectStop, match="refused: CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"):
        preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT,
                                      {**per_job, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "0"})
    with pytest.raises(preparation.DirectStop, match="refused: CLAUDE_CONFIG_DIR"):
        preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, {**per_job, "CLAUDE_CONFIG_DIR": "/elsewhere"})
    with pytest.raises(preparation.DirectStop, match="refused: PATH"):
        preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, {**per_job, "PATH": "/evil"})
    # A missing job variable is not refused here: the launcher checks the instruction it names.
    env = preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, {"D4D_MANIFEST": "m.yaml"})
    assert env["D4D_MANIFEST"] == "m.yaml" and "D4D_PROFILE" not in env
    with pytest.raises(preparation.DirectStop, match="values must be strings"):
        preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, {**per_job, "D4D_PROFILE": None})
    # The last check, on the environment as assembled, is live: a pass-through
    # name that is also forbidden is refused when the parent carries it.
    monkeypatch.setattr(preparation, "PARENT_PASSTHROUGH", preparation.PARENT_PASSTHROUGH + ("https_proxy",))
    monkeypatch.setenv("https_proxy", "http://proxy.invalid")
    with pytest.raises(preparation.DirectStop, match="must not carry.*https_proxy"):
        preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, per_job)
    monkeypatch.delenv("https_proxy")
    assert "https_proxy" not in preparation.child_environment(tmp_path, preparation.CHILD_ENVIRONMENT, per_job)


def test_the_denylist_and_the_allowlist_are_well_formed_and_disjoint():
    """The denylist names the redirections the 2.1.272 binary reads (#2244, each counted in the binary's
    strings when the list was written); the allowlist shares nothing with it or with the constants."""
    assert len(preparation.FORBIDDEN_ENVIRONMENT) == len(set(preparation.FORBIDDEN_ENVIRONMENT))
    assert {"https_proxy", "http_proxy", "all_proxy", "no_proxy", "GLOBAL_AGENT_HTTP_PROXY", "ANTHROPIC_BEDROCK_BASE_URL",
            "NODE_EXTRA_CA_CERTS", "NODE_TLS_REJECT_UNAUTHORIZED", "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "AWS_BEARER_TOKEN_BEDROCK", "CLAUDE_CODE_CLIENT_CERT",
            # the second scan (#2270)
            "CLAUDE_CODE_PROXY_URL", "CLAUDE_CODE_API_BASE_URL", "ANTHROPIC_API_HOST", "ANTHROPIC_DEFAULT_MODEL",
            "CLAUDE_CODE_EFFORT_LEVEL", "CLAUDE_CODE_MAX_CONTEXT_TOKENS", "CLAUDE_CODE_SESSION_ACCESS_TOKEN",
            "CLAUDE_API_KEY", "SSL_CERT_FILE", "CLAUDE_CODE_MANAGED_SETTINGS_PATH", "NODE_OPTIONS",
            "ANTHROPIC_BETAS"} <= set(preparation.FORBIDDEN_ENVIRONMENT)
    assert "CLAUDE_CODE_DISABLE_1M_CONTEXT" not in preparation.FORBIDDEN_ENVIRONMENT   # it is a registered constant
    assert not set(preparation.PER_JOB_NAMES) & set(preparation.FORBIDDEN_ENVIRONMENT)
    assert not set(preparation.PER_JOB_NAMES) & (set(preparation.CHILD_ENVIRONMENT) | set(preparation.PARENT_PASSTHROUGH))
    assert "CLAUDE_CONFIG_DIR" not in preparation.PER_JOB_NAMES


# --- the launcher -----------------------------------------------------------

def bind(tmp_path, path, review_name="review.json", word_name="word.json", jobs=(JOB,)):
    """The binder's whole record (#2245), as `bind_direct_launch.py review` writes it."""
    review = tmp_path / review_name
    code_commit = json.loads(Path(path).read_text())["code_commit"]
    review.write_text(json.dumps({"verdict": "approve", "ci_conclusion": "success", "registration_sha256": launcher.sha(path),
                                  "allowed_jobs": list(jobs), "ci_head": code_commit, "ci_run_id": 1,
                                  "independent_review_sha256": "a" * 64}))
    word = tmp_path / word_name
    word.write_text(json.dumps({"registration_sha256": launcher.sha(path), "exact_response": "launch the direct canary",
                                "recorded_at": "2026-09-22T00:00:00+00:00"}))
    return review, word


OWN_USAGE = {"inputTokens": 1000, "outputTokens": 500, "cacheReadInputTokens": 20000, "cacheCreationInputTokens": 3000,
             "contextWindow": 200000, "maxOutputTokens": 64000}
LIMITS = {"contextWindow": 200000, "maxOutputTokens": 64000}


def fake_child(*, apikey="none", result=True, denials=(), write_outputs=None, tools=("Read", "Write", "Bash"),
               model_usage=None, efforts=("max",), seen=None, terminal=None, results=1, model="claude-opus-5",
               version="2.1.272", inits=1, exit_code=0, control_lines=None, extra_events=(), raise_after=None):
    def execute_child(argv, *, proxy, instruction, attempt, cwd, env, deadline_seconds, verify_launch, record_stop=None,
                      command_policy=None, phase_spec=None, command_classifier=None, event_observer=None):
        verify_launch()
        if seen is not None:
            seen.update(argv=list(argv), env=dict(env), attempt=attempt, cwd=cwd, deadline_seconds=deadline_seconds)
        events = [{"type": "system", "subtype": "init", "model": model, "apiKeySource": apikey,
                   "claude_code_version": version, "tools": list(tools)}] * inits + list(extra_events)
        if result:
            final = {"type": "result", "terminal_reason": "completed", "stop_reason": "end_turn", "is_error": False,
                     "num_turns": 7, "total_cost_usd": 12.5,
                     "usage": {"input_tokens": 1000, "output_tokens": 500},
                     "modelUsage": model_usage if model_usage is not None else {"claude-opus-5": dict(OWN_USAGE)},
                     "permission_denials": list(denials)}
            final.update(terminal or {})
            events.extend([final] * results)
        (attempt / "transcript.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        decisions = [{"kind": "decision", "request": {"request": {"input": {"effort": {"level": level}, "tool_name": "Read"}}}}
                     for level in efforts]
        lines = [json.dumps(d) for d in decisions] + list(control_lines or [])
        (attempt / "control.jsonl").write_text("".join(line + "\n" for line in lines))
        if write_outputs:
            write_outputs()
        if raise_after is not None:
            raise raise_after
        return exit_code
    return execute_child


@pytest.fixture
def offline_launch(prepared, tmp_path, monkeypatch):
    path, registration, fake = prepared
    review, word = bind(tmp_path, path)
    probes = []
    def probe(executable, env):
        probes.append({"executable": executable, "env": dict(env), "config_existed": Path(env["CLAUDE_CONFIG_DIR"]).is_dir(),
                       "attempts_existed": (path.parent / "attempts").exists()})
        return dict(AUTH)
    monkeypatch.setattr(preparation, "auth_evidence", probe)
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
    launch = SimpleNamespace(path=path, registration=registration, review=review, word=word, write_outputs=write_outputs,
                             probes=probes, tmp_path=tmp_path)
    # Resolved now: a test that fails while chdir'd elsewhere must still clean the checkout's tree (#2277).
    absolute = [ROOT / d for d in job["output_directories"]]
    yield launch
    for directory in absolute:
        shutil.rmtree(directory, ignore_errors=True)
        remove_if_empty(directory.parent)


def run(launch, review=None, word=None, job=JOB):
    return launcher.main(["--registration", str(launch.path), "--review", str(review or launch.review),
                          "--launch-word", str(word or launch.word), "--job", job])


def stopped(launch, monkeypatch, child, reason, job=JOB):
    """A launch that starts and is stopped after the child ran, for the given reason."""
    monkeypatch.setattr(launcher.native, "execute_child", child)
    assert run(launch, job=job) == 1
    receipt = receipt_of(launch, job)
    assert receipt["status"] == "stopped" and receipt["reason"] == reason, receipt.get("reason")
    return receipt


def receipt_of(launch, job=JOB):
    return json.loads((launch.path.parent / "attempts" / job / "result.json").read_text())


def rewrite(launch, mutate, name, jobs=(JOB,)):
    """A registration altered in one respect, with a review and a launch word bound to its new hash,
    so that the launcher's own guard, not the binding, is what refuses it."""
    registration = json.loads(launch.path.read_text())
    mutate(registration)
    launch.path.write_text(json.dumps(registration, indent=2) + "\n")
    launch.review, launch.word = bind(launch.tmp_path, launch.path, f"review-{name}.json", f"word-{name}.json", jobs=jobs)
    return registration


def refused_before_anything_is_created(launch, monkeypatch, match, error=BudgetStop):
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched past a refused guard"))
    with pytest.raises(error, match=match):
        run(launch)
    assert not (launch.path.parent / "attempts").exists()
    assert sorted(p.name for p in launch.path.parent.iterdir()) == ["prompts", "registration.json"]
    assert not any(Path(d).exists() for d in launch.registration["generation"]["jobs"][0]["output_directories"])


def test_a_completed_offline_launch_reports_runtime_accounting_and_touches_no_ledger(offline_launch, monkeypatch):
    launch = offline_launch
    monkeypatch.setenv("UNRELATED_PARENT_VARIABLE", "never")
    seen = {}
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(write_outputs=launch.write_outputs, seen=seen))
    code = run(launch)
    receipt = receipt_of(launch)
    assert code == 0 and receipt["status"] == "completed_pending_independent_review"
    assert receipt["runtime_reported_cost_usd"] == 12.5 and receipt["num_turns"] == 7
    assert receipt["runtime_usage"] == {"input_tokens": 1000, "output_tokens": 500}
    assert receipt["runtime_model_usage"] == OWN_USAGE and receipt["runtime_limits_observed"] == LIMITS
    assert receipt["executable_sha256"] == launcher.sha(launch.registration["native_runtime"]["executable"])
    assert receipt["accounting_reconciliation"] == {"terminal_output_tokens": 500, "model_usage_output_tokens": 500, "difference": 0}
    assert receipt["auxiliary_model_usage"] == {} and receipt["effort_observed"] == ["max"]
    assert receipt["phase_history"] == {"checked": True, "problems": []}
    assert receipt["pretool_control"] == {"checked": True, "problems": [], "persisted_output_paths": []}
    assert receipt["auth"] == AUTH and receipt["permission_denials"] == [] and receipt["validation_problems"] == []
    assert receipt["arm"]["provider"] == "Anthropic (Claude subscription, direct)"
    assert not any("ledger" in key for key in receipt)
    assert not (launch.path.parent / "billing.json").exists()
    # The child ran in exactly the screened environment: the parent's stray variable is absent, the
    # registered variables, the job's and the isolated config directory present, nothing else.
    per_job = launch.registration["per_job_environment"][JOB]
    attempt = launch.path.parent / "attempts" / JOB
    assert seen["attempt"] == attempt and seen["cwd"] == str(ROOT) and seen["deadline_seconds"] == 21600
    assert seen["env"] == {**seen["env"], **preparation.CHILD_ENVIRONMENT, **per_job, "CLAUDE_CONFIG_DIR": str(attempt / "cli_config")}
    assert "UNRELATED_PARENT_VARIABLE" not in seen["env"]
    assert set(seen["env"]) <= set(preparation.PARENT_PASSTHROUGH) | set(preparation.CHILD_ENVIRONMENT) | set(per_job) | LAUNCH_ONLY
    assert sorted(receipt["child_environment_names"]) == sorted(seen["env"])
    argv = seen["argv"]
    assert argv[argv.index("--effort") + 1] == "max" and argv[argv.index("--model") + 1] == "claude-opus-5"
    assert argv[argv.index("--max-budget-usd") + 1] == "60" and argv[0] == launch.registration["native_runtime"]["executable"]
    # The login was probed once, in the child's environment, in a throwaway directory, before the attempt existed.
    [probe] = launch.probes
    assert probe["config_existed"] and not probe["attempts_existed"]
    assert Path(probe["env"]["CLAUDE_CONFIG_DIR"]).parent == launch.path.parent
    assert not Path(probe["env"]["CLAUDE_CONFIG_DIR"]).exists()
    assert {k: v for k, v in probe["env"].items() if k != "CLAUDE_CONFIG_DIR"} == \
           {k: v for k, v in seen["env"].items() if k not in LAUNCH_ONLY}


def test_a_refused_login_consumes_nothing(offline_launch, monkeypatch):
    launch = offline_launch
    def expired(executable, env):
        raise preparation.DirectStop("the runtime is not on the maintainer's claude.ai login: {'loggedIn': False}")
    monkeypatch.setattr(preparation, "auth_evidence", expired)
    refused_before_anything_is_created(launch, monkeypatch, "claude.ai login", error=preparation.DirectStop)
    # And the same job can still be launched once the login is back.
    monkeypatch.setattr(preparation, "auth_evidence", lambda executable, env: dict(AUTH))
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(write_outputs=launch.write_outputs))
    assert run(launch) == 0


def test_a_key_authenticated_runtime_is_refused_after_the_run(offline_launch, monkeypatch):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(apikey="ANTHROPIC_API_KEY", write_outputs=launch.write_outputs))
    code = run(launch)
    receipt = receipt_of(launch)
    assert code == 1 and receipt["status"] == "stopped"
    assert receipt["reason"].startswith("native runtime initialization differs from registration: model 'claude-opus-5', key source 'ANTHROPIC_API_KEY'")
    assert receipt["reason_source"] == "controller"


def test_an_initialization_with_other_tools_is_refused(offline_launch, monkeypatch):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child",
                        fake_child(tools=("Read", "Write", "Bash", "WebFetch"), write_outputs=launch.write_outputs))
    assert run(launch) == 1
    assert "tools ['Bash', 'Read', 'WebFetch', 'Write'] against" in receipt_of(launch)["reason"]


def test_the_auxiliary_model_is_recorded_and_a_foreign_model_stops_the_run(offline_launch, monkeypatch):
    launch = offline_launch
    haiku = {"claude-opus-5": {**OWN_USAGE, "inputTokens": 900}, "claude-haiku-4-5": {"inputTokens": 12000, "outputTokens": 40}}
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(model_usage=haiku, write_outputs=launch.write_outputs))
    assert run(launch) == 0
    receipt = receipt_of(launch)
    assert receipt["status"] == "completed_pending_independent_review"
    assert receipt["runtime_model_usage"] == {**OWN_USAGE, "inputTokens": 900}
    assert receipt["auxiliary_model_usage"] == {"claude-haiku-4-5": {"inputTokens": 12000, "outputTokens": 40}}
    reset(launch)
    foreign = {"claude-opus-5": dict(OWN_USAGE), "claude-sonnet-4-5": {"inputTokens": 1, "outputTokens": 1}}
    stopped(launch, monkeypatch, fake_child(model_usage=foreign, write_outputs=launch.write_outputs),
            "native terminal accounting names a model the registration does not permit: claude-sonnet-4-5")
    reset(launch)
    stopped(launch, monkeypatch, fake_child(model_usage={"claude-haiku-4-5": {"inputTokens": 1, "outputTokens": 1}},
                                            write_outputs=launch.write_outputs),
            "native terminal accounting does not name the registered model")


def test_the_model_gate_measures_the_work_not_only_the_names(offline_launch, monkeypatch):
    """#2247: the registered model with an empty entry and an auxiliary carrying all the work completed cleanly."""
    launch = offline_launch
    probe = {"claude-opus-5": {}, "claude-haiku-4-5": {"inputTokens": 2_000_000, "outputTokens": 90_000}}
    stopped(launch, monkeypatch, fake_child(model_usage=probe, write_outputs=launch.write_outputs),
            "native terminal accounting for the registered model is incomplete")
    for own, reason in (({**OWN_USAGE, "outputTokens": 0}, "shows no work on the registered model"),
                        ({**OWN_USAGE, "inputTokens": 0, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0},
                         "shows no work on the registered model"),
                        ({**OWN_USAGE, "outputTokens": -1}, "for the registered model is incomplete"),
                        ({**OWN_USAGE, "outputTokens": "500"}, "for the registered model is incomplete"),
                        ("not a mapping", "for the registered model is not a mapping")):
        reset(launch)
        stopped(launch, monkeypatch, fake_child(model_usage={"claude-opus-5": own}, write_outputs=launch.write_outputs),
                "native terminal accounting " + reason)
    # A permitted auxiliary that generated as much as the registered model is a main-loop fallback, not an auxiliary.
    for aux, reason in (({"inputTokens": 5, "outputTokens": 500}, "an auxiliary model carried at least as much generation as the registered model: claude-haiku-4-5"),
                        ({"inputTokens": 5}, "native terminal accounting for an auxiliary model is incomplete: claude-haiku-4-5"),
                        ([], "native terminal accounting for an auxiliary model is incomplete: claude-haiku-4-5")):
        reset(launch)
        stopped(launch, monkeypatch, fake_child(model_usage={"claude-opus-5": dict(OWN_USAGE), "claude-haiku-4-5": aux},
                                                write_outputs=launch.write_outputs), reason)
    reset(launch)
    stopped(launch, monkeypatch, fake_child(terminal={"modelUsage": None}, write_outputs=launch.write_outputs),
            "native terminal model accounting is missing")
    # An absent cache count is incomplete, not a TypeError (#2275).
    reset(launch)
    stopped(launch, monkeypatch, fake_child(model_usage={"claude-opus-5": {k: v for k, v in OWN_USAGE.items() if k != "cacheReadInputTokens"}},
                                            write_outputs=launch.write_outputs),
            "native terminal accounting for the registered model is incomplete")
    # Two auxiliaries each below the registered model but together above it are a fallback (#2271).
    reset(launch)
    stopped(launch, monkeypatch, fake_child(model_usage={"claude-opus-5": dict(OWN_USAGE),
                                                         "claude-haiku-4-5": {"inputTokens": 5, "outputTokens": 300},
                                                         "claude-haiku-4-5-20251001": {"inputTokens": 5, "outputTokens": 300}},
                                            write_outputs=launch.write_outputs),
            "the auxiliary models together carried at least as much generation as the registered model")
    # The reconciliation is recorded, not gated.
    reset(launch)
    monkeypatch.setattr(launcher.native, "execute_child",
                        fake_child(model_usage={"claude-opus-5": {**OWN_USAGE, "outputTokens": 120}}, write_outputs=launch.write_outputs))
    assert run(launch) == 0
    assert receipt_of(launch)["accounting_reconciliation"] == {"terminal_output_tokens": 500, "model_usage_output_tokens": 120, "difference": 380}
    # The init line is the only guard on the main-loop model before the accounting: a wrong model or version
    # there stops, and the stop names what was observed (#2266: the 1M build reports itself as another model).
    reset(launch)
    receipt = stopped(launch, monkeypatch, fake_child(model="claude-opus-5[1m]", write_outputs=launch.write_outputs),
                      "native runtime initialization differs from registration: model 'claude-opus-5[1m]', key source 'none', "
                      "version '2.1.272', tools ['Bash', 'Read', 'Write'] against 'claude-opus-5', 'none', '2.1.272', ['Bash', 'Read', 'Write']")
    reset(launch)
    stopped(launch, monkeypatch, fake_child(version="2.1.271", write_outputs=launch.write_outputs),
            "native runtime initialization differs from registration: model 'claude-opus-5', key source 'none', "
            "version '2.1.271', tools ['Bash', 'Read', 'Write'] against 'claude-opus-5', 'none', '2.1.272', ['Bash', 'Read', 'Write']")
    # A real transcript carries other system events and other init-like events; only system/init counts (#2275).
    reset(launch)
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(
        extra_events=[{"type": "system", "subtype": "thinking_tokens", "count": 85}, {"type": "user", "subtype": "init"},
                      {"type": "system", "subtype": "permission_denied"}, {"type": "assistant", "message": {}}],
        write_outputs=launch.write_outputs))
    assert run(launch) == 0


def test_the_runtime_limits_are_recorded_and_a_difference_is_a_validation_problem(offline_launch, monkeypatch):
    """#2246: a 1M-context terminal completed with zero validation problems."""
    launch = offline_launch
    wide = {"claude-opus-5": {**OWN_USAGE, "contextWindow": 1_000_000}}
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(model_usage=wide, write_outputs=launch.write_outputs))
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert receipt["status"] == "validation_failed"
    assert receipt["runtime_limits_observed"] == {"contextWindow": 1_000_000, "maxOutputTokens": 64000}
    assert receipt["validation_problems"] == [
        "the runtime reported limits {'contextWindow': 1000000, 'maxOutputTokens': 64000} where the registration expects "
        "{'contextWindow': 200000, 'maxOutputTokens': 64000}"]
    reset(launch)
    absent = {"claude-opus-5": {k: v for k, v in OWN_USAGE.items() if k != "maxOutputTokens"}}
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(model_usage=absent, write_outputs=launch.write_outputs))
    assert run(launch) == 1
    assert receipt_of(launch)["runtime_limits_observed"] == {"contextWindow": 200000, "maxOutputTokens": None}
    # The registration must state them, as positive integers, under exactly the two keys.
    reset(launch)
    for name, limits in (("missing", None), ("zero", {"contextWindow": 0, "maxOutputTokens": 64000}),
                         ("string", {"contextWindow": "200000", "maxOutputTokens": 64000}),
                         ("extra", {"contextWindow": 200000, "maxOutputTokens": 64000, "other": 1})):
        rewrite(launch, lambda r, limits=limits: r["model"].update(limits_expected=limits), f"limits-{name}")
        refused_before_anything_is_created(launch, monkeypatch, "does not state the expected runtime limits")


def test_an_effort_the_runtime_did_not_honour_is_a_validation_problem(offline_launch, monkeypatch):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(efforts=("high", "max"), write_outputs=launch.write_outputs))
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert receipt["status"] == "validation_failed" and receipt["effort_observed"] == ["high", "max"]
    assert receipt["validation_problems"] == ["the runtime reported effort ['high', 'max'] where the registration asserts 'max'"]
    # An effort no callback reported is its own finding, not a mismatch (#2249).
    reset(launch)
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(efforts=(), write_outputs=launch.write_outputs))
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert receipt["status"] == "validation_failed" and receipt["effort_observed"] == []
    assert receipt["validation_problems"] == ["the runtime reported no effort on any tool callback; the registration asserts 'max'"]
    # Malformed control lines are skipped, on the completed path and on the stop path (#2250).
    malformed = ['[1, 2]', '"text"', json.dumps({"kind": "decision", "request": []}),
                 json.dumps({"kind": "decision", "request": {"request": "x"}}),
                 json.dumps({"kind": "decision", "request": {"request": {"input": 5}}}),
                 json.dumps({"kind": "decision", "request": {"request": {"input": {"effort": {"level": 3}}}}})]
    reset(launch)
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(control_lines=malformed, write_outputs=launch.write_outputs))
    assert run(launch) == 0 and receipt_of(launch)["effort_observed"] == ["max"]
    reset(launch)
    receipt = stopped(launch, monkeypatch, fake_child(result=False, control_lines=malformed),
                      "native runtime initialization or terminal result is missing or ambiguous")
    assert receipt["effort_observed"] == ["max"]


def test_a_provider_key_in_the_environment_refuses_before_anything_is_created(offline_launch, monkeypatch):
    launch = offline_launch
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-never")
    refused_before_anything_is_created(launch, monkeypatch, "refuses provider keys")


def test_a_registration_carrying_a_key_or_a_redirection_is_refused(offline_launch, monkeypatch):
    launch = offline_launch
    # A forbidden name in the registration's job variables is refused before anything is created: the exact
    # binding (#2265) sees it first; `child_environment`'s own denylist is tested directly above.
    rewrite(launch, lambda r: r["per_job_environment"][JOB].update(ANTHROPIC_BASE_URL="http://proxy.invalid"), "perjob")
    refused_before_anything_is_created(launch, monkeypatch, "bind exactly the job's manifest, profile and launch instruction")
    rewrite(launch, lambda r: r["per_job_environment"][JOB].pop("ANTHROPIC_BASE_URL"), "perjob-restored")
    # A name the denylist does not know is refused before anything is created: by the exact binding of the
    # job's three variables (#2265), which runs before the allowlist (#2244) the preparer's probe applies.
    rewrite(launch, lambda r: r["per_job_environment"][JOB].update(SOME_FUTURE_VARIABLE="x"), "perjob-extra")
    refused_before_anything_is_created(launch, monkeypatch, "bind exactly the job's manifest, profile and launch instruction")
    rewrite(launch, lambda r: r["per_job_environment"][JOB].pop("SOME_FUTURE_VARIABLE"), "perjob-extra-restored")
    rewrite(launch, lambda r: r["native_runtime"]["environment"].update(ANTHROPIC_API_KEY="sk-registered"), "env")
    refused_before_anything_is_created(launch, monkeypatch, "child environment differs from the preparer's")


def test_the_launch_word_must_name_this_exact_registration(offline_launch, monkeypatch, tmp_path):
    launch = offline_launch
    other = tmp_path / "other-word.json"
    other.write_text(json.dumps({"registration_sha256": "0" * 64, "exact_response": "launch"}))
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched without the word"))
    with pytest.raises(BudgetStop, match="launch word"):
        run(launch, word=other)
    blank = tmp_path / "blank-word.json"
    blank.write_text(json.dumps({"registration_sha256": launcher.sha(launch.path), "exact_response": "   "}))
    with pytest.raises(BudgetStop, match="launch word"):
        run(launch, word=blank)
    assert not (launch.path.parent / "attempts").exists()


def test_the_review_binding_is_checked_in_every_respect(offline_launch, monkeypatch, tmp_path):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched without approval"))
    good = json.loads(launch.review.read_text())
    for name, change in (("verdict", {"verdict": "reject"}), ("ci", {"ci_conclusion": "failure"}),
                         ("sha", {"registration_sha256": "0" * 64}), ("jobs", {"allowed_jobs": ["VOICE_direct_rep1"]})):
        review = tmp_path / f"review-{name}.json"
        review.write_text(json.dumps({**good, **change}))
        with pytest.raises(BudgetStop, match="independent approval and CI"):
            run(launch, review=review)
    with pytest.raises(BudgetStop, match="independent approval and CI"):
        run(launch, job="VOICE_direct_rep1")
    # The CI evidence is read, not only the verdict (#2245): the run must be on the registered commit,
    # and the record must name a run and the independent review it bound.
    for name, change, match in (("head", {"ci_head": "0" * 40}, "not on the registered code commit"),
                                ("no-head", {"ci_head": None}, "not on the registered code commit"),
                                ("run", {"ci_run_id": 0}, "does not bind a CI run"),
                                ("run-str", {"ci_run_id": "1"}, "does not bind a CI run"),
                                ("independent", {"independent_review_sha256": "zz"}, "does not bind a CI run"),
                                ("no-independent", {"independent_review_sha256": None}, "does not bind a CI run")):
        review = tmp_path / f"review-{name}.json"
        review.write_text(json.dumps({**good, **change}))
        with pytest.raises(BudgetStop, match=match):
            run(launch, review=review)
    assert not (launch.path.parent / "attempts").exists()


@pytest.mark.parametrize("name, mutate, match", [
    ("repository", lambda r: r.update(repository="/elsewhere/checkout"), "runs from the checkout"),
    ("commit", lambda r: r.update(code_commit="0" * 40), "not at the registered code commit"),
    ("python", lambda r: r.update(python="/usr/bin/python3.99"), "registered Python differs"),
    ("arm", lambda r: r["arm"].update(method="claudecode_agent"), "names another arm"),
    ("model", lambda r: r["model"].update(model="claude-sonnet-5"), "another model or effort"),
    ("effort", lambda r: r["model"].update(effort="high"), "another model or effort"),
    ("auxiliary", lambda r: r["model"].update(auxiliary_models_permitted=["claude-sonnet-4-5"]), "other auxiliary models"),
    ("flags", lambda r: r["native_runtime"].update(cli_flags=[f for f in r["native_runtime"]["cli_flags"] if f != "--safe-mode"]),
     "CLI flags differ"),
    ("keysource", lambda r: r["native_runtime"].update(expected_api_key_source="ANTHROPIC_API_KEY"), "expects a login"),
    ("job-method", lambda r: r["generation"]["jobs"][0].update(method="claudecode_agent"), "belongs to another arm"),
    ("job-runtime", lambda r: r["generation"]["jobs"][0].update(runtime="Claude Code"), "belongs to another arm"),
    ("job-effort", lambda r: r["generation"]["jobs"][0]["render_spec"].update(reasoning_effort="high"), "does not assert the registered effort"),
    ("job-expansion", lambda r: r["generation"]["jobs"][0]["render_spec"].pop("prompt_text_env"), "by --prompt-text-env"),
    ("outputs", lambda r: r["generation"]["jobs"][0].update(
        output_directories=[d.replace("claudecode_direct", "claudecode_agent") for d in r["generation"]["jobs"][0]["output_directories"]]),
     "outside the direct arm's directories"),
    ("output-path", lambda r: r["generation"]["jobs"][0]["outputs"].update(
        report=r["generation"]["jobs"][0]["outputs"]["report"].replace("claudecode_direct_core", "claudecode_api_core")),
     "outside the direct arm's directories"),
    ("traversal", lambda r: r["generation"]["jobs"][0].update(
        output_directories=["data/d4d_concatenated/claudecode_direct/../claudecode_agent/x"]), "outside the direct arm's directories"),
    ("pin", lambda r: r["pinned_files"].update({next(p for p in r["pinned_files"] if p.endswith("system.md")): "0" * 64}),
     "a registered pin changed"),
    ("policy", lambda r: r["per_job_command_policy"][JOB].update(mutated=True), "command policy differs"),
    ("instruction", lambda r: r["per_job_environment"][JOB].update(D4D_LAUNCH_INSTRUCTION="/elsewhere/instruction.md"),
     "exact registered launch instruction"),
    ("kind", lambda r: r.update(kind="d4d_native_registration"), "not a direct-arm registration"),
    ("schema", lambda r: r.update(schema_version=2), "not a direct-arm registration"),
    ("no-outputs", lambda r: r["generation"]["jobs"][0].update(output_directories=[]), "names no output directory"),
    ("forbidden", lambda r: r["native_runtime"].update(forbidden_environment=["ANTHROPIC_API_KEY"]),
     "registered forbidden environment differs"),
    ("policy-input", lambda r: r["generation"]["jobs"][0]["outputs"].update(
        report=r["generation"]["jobs"][0]["outputs"]["report"] + ".other"), "command policy cannot be built"),
    ("env-shape", lambda r: r["per_job_environment"].update({JOB: ["D4D_MANIFEST=x"]}), "job environment is not a mapping"),
    ("env-missing", lambda r: r["per_job_environment"].pop(JOB), "job environment is not a mapping"),
    ("env-profile", lambda r: r["per_job_environment"][JOB].update(D4D_PROFILE="neutral"), "bind exactly the job's manifest, profile"),
    ("env-manifest", lambda r: r["per_job_environment"][JOB].update(D4D_MANIFEST="/elsewhere/manifest.yaml"), "bind exactly the job's"),
    ("env-short", lambda r: r["per_job_environment"][JOB].pop("D4D_PROFILE"), "bind exactly the job's"),
    ("system-prompt", lambda r: r["native_runtime"].update(system_prompt=r["generation"]["jobs"][0]["instruction"]),
     "system prompt is not the direct arm's system.md"),
    ("system-prompt-none", lambda r: r["native_runtime"].pop("system_prompt"), "system prompt is not the direct arm's system.md"),
    ("deadline", lambda r: r["generation"].update(attempt_deadline_seconds="soon"), "attempt deadline is not a positive integer"),
    ("deadline-zero", lambda r: r["generation"].update(attempt_deadline_seconds=0), "attempt deadline is not a positive integer"),
    ("guard-int", lambda r: r["generation"].update(runaway_budget_guard_usd=60), "runaway guard is not a positive decimal string"),
    ("guard-zero", lambda r: r["generation"].update(runaway_budget_guard_usd="0"), "runaway guard is not a positive decimal string"),
    ("guard-text", lambda r: r["generation"].update(runaway_budget_guard_usd="sixty"), "runaway guard is not a positive decimal string"),
    ("condition", lambda r: r["generation"]["jobs"][0]["render_spec"].update(condition="generic_v99"), "specification cannot be built"),
    ("render-version", lambda r: r["generation"]["jobs"][0].update(render_version="17"), "specification cannot be built"),
    ("second-job-id", lambda r: r["generation"]["jobs"].append({**r["generation"]["jobs"][0], "id": 5}), "not a single path component"),
    ("second-job-id-null", lambda r: r["generation"]["jobs"].append({**r["generation"]["jobs"][0], "id": None}), "not a single path component"),
])
def test_every_registration_guard_refuses_before_anything_is_created(offline_launch, monkeypatch, name, mutate, match):
    launch = offline_launch
    rewrite(launch, mutate, name)
    refused_before_anything_is_created(launch, monkeypatch, match)


def test_a_registration_without_a_commit_does_not_match_a_review_without_a_head(offline_launch, monkeypatch, tmp_path):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched without a commit"))
    registration = json.loads(launch.path.read_text())
    del registration["code_commit"]
    launch.path.write_text(json.dumps(registration, indent=2) + "\n")
    review = tmp_path / "review-headless.json"
    review.write_text(json.dumps({**json.loads(launch.review.read_text()), "registration_sha256": launcher.sha(launch.path),
                                  "ci_head": None}))
    with pytest.raises(BudgetStop, match="not on the registered code commit"):
        run(launch, review=review)
    assert not (launch.path.parent / "attempts").exists()


def test_a_job_id_is_one_path_component(offline_launch, monkeypatch):
    """#2252: `../pwned_attempt` wrote the attempt outside attempts/."""
    launch = offline_launch
    for bad in ("../pwned_attempt", "a/b", ".", "", "x y"):
        def mutate(r, bad=bad):
            job = r["generation"]["jobs"][0]
            for block in ("per_job_environment", "per_job_command_policy"):
                r[block][bad] = r[block].pop(job["id"])
            job["id"] = bad
        rewrite(launch, mutate, f"id-{abs(hash(bad))}", jobs=(bad,))
        monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched a traversal id"))
        with pytest.raises(BudgetStop, match="not a single path component"):
            run(launch, job=bad)
        assert not (launch.path.parent / "attempts").exists()
        assert not (launch.path.parent.parent / "pwned_attempt").exists()


def test_an_unpinned_executable_is_refused(offline_launch, monkeypatch, tmp_path):
    """#2263: a substitute that prints the pinned version string launched."""
    launch = offline_launch
    (tmp_path / "elsewhere").mkdir()
    substitute = fake_runtime(tmp_path / "elsewhere")
    def swap(r):
        r["native_runtime"]["executable"] = str(substitute)
    rewrite(launch, swap, "unpinned-exe")
    refused_before_anything_is_created(launch, monkeypatch, "registered executable is not pinned")
    # Pinned with the wrong bytes: the pin loop refuses it.
    def swap_pinned(r):
        r["native_runtime"]["executable"] = str(substitute)
        r["pinned_files"][str(substitute)] = "0" * 64
    rewrite(launch, swap_pinned, "unpinned-exe-badhash")
    refused_before_anything_is_created(launch, monkeypatch, "a registered pin changed")


def test_a_deleted_pin_is_a_named_stop(offline_launch, monkeypatch, tmp_path):
    launch = offline_launch
    extra = tmp_path / "pinned-then-deleted.txt"
    extra.write_text("pinned\n")
    rewrite(launch, lambda r: r["pinned_files"].update({str(extra): launcher.sha(extra)}), "extra-pin")
    extra.unlink()
    refused_before_anything_is_created(launch, monkeypatch, "a registered pin changed: pinned-then-deleted.txt")


def test_the_launcher_refuses_another_checkout_and_another_runtime_version(offline_launch, monkeypatch, tmp_path):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched from the wrong place"))
    other = tmp_path / "elsewhere"; other.mkdir()
    monkeypatch.chdir(other)
    with pytest.raises(BudgetStop, match="runs from the checkout"):
        run(launch)
    monkeypatch.chdir(ROOT)
    real_check_output = launcher.subprocess.check_output
    monkeypatch.setattr(launcher.subprocess, "check_output",
                        lambda argv, *a, **k: "2.1.271 (Claude Code)" if argv[1:] == ["--version"] else real_check_output(argv, *a, **k))
    with pytest.raises(BudgetStop, match="native runtime version changed"):
        run(launch)
    assert not (launch.path.parent / "attempts").exists()


def test_existing_output_or_a_consumed_attempt_is_never_overwritten(offline_launch, monkeypatch):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched over existing output"))
    job = launch.registration["generation"]["jobs"][0]
    Path(job["output_directories"][0]).mkdir(parents=True)
    with pytest.raises(BudgetStop, match="never overwrite or resume"):
        run(launch)
    assert not (launch.path.parent / "attempts").exists()
    shutil.rmtree(job["output_directories"][0])
    (launch.path.parent / "attempts" / JOB).mkdir(parents=True)
    with pytest.raises(BudgetStop, match="attempt identity is consumed"):
        run(launch)
    assert launch.probes == []                           # nothing was probed for a consumed attempt


def test_a_registration_whose_instruction_changed_is_refused(offline_launch, monkeypatch):
    launch = offline_launch
    job = launch.registration["generation"]["jobs"][0]
    with Path(job["instruction"]).open("a") as out:
        out.write("\n# edited after registration\n")
    refused_before_anything_is_created(launch, monkeypatch, "a registered pin changed")


def test_a_run_that_ends_without_a_result_line_is_a_named_stop(offline_launch, monkeypatch):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(result=False))
    code = run(launch)
    receipt = receipt_of(launch)
    assert code == 1 and receipt["status"] == "stopped" and receipt["transcript_terminal_result"] == "absent"
    assert receipt["reason_source"] == "controller" and "permission_denials_note" in receipt
    assert receipt["effort_observed"] == ["max"]
    assert receipt["pretool_control"] == {"checked": True, "problems": [], "persisted_output_paths": []}
    assert receipt["phase_history"] == {"checked": True, "problems": []}


def reset(launch):
    """Between two launches of one fixture: the attempt identity and the outputs are consumed by design."""
    shutil.rmtree(launch.path.parent / "attempts", ignore_errors=True)
    for directory in launch.registration["generation"]["jobs"][0]["output_directories"]:
        shutil.rmtree(directory, ignore_errors=True)


def stopped_with(launch, monkeypatch, child, reason):
    reset(launch)
    monkeypatch.setattr(launcher.native, "execute_child", child)
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert receipt["status"] == "stopped" and receipt["reason"] == reason, receipt.get("reason")
    return receipt


def test_a_terminal_that_did_not_complete_or_is_ambiguous_is_a_named_stop(offline_launch, monkeypatch):
    launch = offline_launch
    receipt = stopped_with(launch, monkeypatch, fake_child(terminal={"is_error": True}, write_outputs=launch.write_outputs),
                           "native attempt failed or stopped before completion")
    # Stopped after the denials were classified: the stop path keeps that classification.
    assert receipt["disqualifying_denials"] == [] and "permission_denials_note" not in receipt
    for terminal in ({"stop_reason": "max_tokens"}, {"terminal_reason": "deadline"}):
        stopped_with(launch, monkeypatch, fake_child(terminal=terminal, write_outputs=launch.write_outputs),
                     "native attempt failed or stopped before completion")
    stopped_with(launch, monkeypatch, fake_child(results=2, write_outputs=launch.write_outputs),
                 "native runtime initialization or terminal result is missing or ambiguous")


def test_incomplete_usage_or_missing_artifacts_stop_the_run(offline_launch, monkeypatch):
    launch = offline_launch
    stopped_with(launch, monkeypatch, fake_child(terminal={"usage": {"input_tokens": 1000}}, write_outputs=launch.write_outputs),
                 "native terminal usage is incomplete")
    stopped_with(launch, monkeypatch, fake_child(terminal={"usage": {"input_tokens": -1, "output_tokens": 5}},
                                                 write_outputs=launch.write_outputs), "native terminal usage is incomplete")
    stopped_with(launch, monkeypatch, fake_child(terminal={"usage": None}, write_outputs=launch.write_outputs),
                 "native terminal usage is incomplete")
    stopped_with(launch, monkeypatch, fake_child(), "native generation did not produce every registered artifact")
    stopped_with(launch, monkeypatch, fake_child(exit_code=1, write_outputs=launch.write_outputs),
                 "native attempt failed or stopped before completion")
    stopped_with(launch, monkeypatch, fake_child(inits=0, write_outputs=launch.write_outputs),
                 "native runtime initialization or terminal result is missing or ambiguous")
    stopped_with(launch, monkeypatch, fake_child(inits=2, write_outputs=launch.write_outputs),
                 "native runtime initialization or terminal result is missing or ambiguous")


def test_an_unchecked_evidence_result_and_a_failed_pair_are_named_problems(offline_launch, monkeypatch):
    launch = offline_launch
    from data_sheets_schema import api_runner
    monkeypatch.setattr(launcher.native, "native_evidence_check", lambda *a: {"checked": False, "findings": []})
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(write_outputs=launch.write_outputs))
    assert run(launch) == 1
    assert receipt_of(launch)["validation_problems"] == ["explicit evidence assertions were not checked"]
    monkeypatch.setattr(launcher.native, "native_evidence_check", lambda *a: {"checked": True, "findings": []})
    for pair, problem in ((None, "the full and core records were not checked for consistency"),
                          ({"ran": False}, "the full and core records were not checked for consistency"),
                          ({"ran": True, "consistent": False}, "the full and core records are not consistent")):
        reset(launch)
        monkeypatch.setattr(api_runner, "pair_consistency", lambda *a, pair=pair: pair)
        assert run(launch) == 1
        receipt = receipt_of(launch)
        assert receipt["status"] == "validation_failed" and receipt["validation_problems"] == [problem]
        assert receipt["pair_consistency"] == pair


def test_the_stop_path_keeps_a_phase_history_already_computed(offline_launch, monkeypatch):
    launch = offline_launch
    calls = []
    def phase_history(events, spec, complete, **kw):
        calls.append(complete)
        return {"checked": True, "problems": [], "complete": complete}
    monkeypatch.setattr(launcher, "phase_history", phase_history)
    # Stopped after the history was computed for the completed run: kept, not recomputed as incomplete.
    receipt = stopped(launch, monkeypatch, fake_child(terminal={"is_error": True}, write_outputs=launch.write_outputs),
                      "native attempt failed or stopped before completion")
    assert receipt["phase_history"]["complete"] is True and calls == [True]
    # Stopped before it: computed once, as incomplete.
    reset(launch); calls.clear()
    receipt = stopped(launch, monkeypatch, fake_child(result=False),
                      "native runtime initialization or terminal result is missing or ambiguous")
    assert receipt["phase_history"]["complete"] is False and calls == [False]


def test_a_failed_receipt_or_evidence_check_is_a_validation_problem(offline_launch, monkeypatch):
    launch = offline_launch
    monkeypatch.setattr(launcher, "check_canary_receipts", lambda *a, **k: {"passed": False, "problems": ["x"]})
    monkeypatch.setattr(launcher.native, "native_evidence_check", lambda *a: {"checked": True, "findings": ["unsupported"]})
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(write_outputs=launch.write_outputs))
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert receipt["status"] == "validation_failed"
    assert receipt["validation_problems"] == ["coverage receipt acceptance failed", "explicit evidence assertions failed"]
    assert receipt["receipt_acceptance"]["passed"] is False and receipt["evidence_assertions"]["findings"] == ["unsupported"]


def test_only_a_registered_canary_of_this_arm_can_be_launched(offline_launch, monkeypatch, tmp_path):
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", lambda *a, **k: pytest.fail("launched an unregistered job"))
    review = tmp_path / "review-wide.json"
    review.write_text(json.dumps({**json.loads(launch.review.read_text()), "allowed_jobs": [JOB, "CHORUS_direct_rep2"]}))
    with pytest.raises(BudgetStop, match="only runs registered direct-arm canaries"):
        run(launch, review=review, job="CHORUS_direct_rep2")
    rewrite(launch, lambda r: r["generation"]["jobs"][0].update(canary=False), "not-canary")
    refused_before_anything_is_created(launch, monkeypatch, "only runs registered direct-arm canaries")


def test_a_changed_input_identity_or_rendering_and_an_unresolved_executable_are_refused(offline_launch, monkeypatch, tmp_path):
    launch = offline_launch
    rewrite(launch, lambda r: r["generation"]["jobs"][0]["input_identity"].update(tampered=True), "identity")
    refused_before_anything_is_created(launch, monkeypatch, "instruction or input identity changed")
    rewrite(launch, lambda r: r["generation"]["jobs"][0]["input_identity"].pop("tampered"), "identity-restored")
    rewrite(launch, lambda r: r["generation"]["jobs"][0]["render_spec"].update(provider="someone else"), "rendering")
    refused_before_anything_is_created(launch, monkeypatch, "instruction or input identity changed")
    rewrite(launch, lambda r: r["generation"]["jobs"][0]["render_spec"].update(provider=preparation.PROVIDER), "rendering-restored")
    link = tmp_path / "claude-link"
    link.symlink_to(launch.registration["native_runtime"]["executable"])
    def via_link(r):
        r["native_runtime"]["executable"] = str(link)
        r["pinned_files"][str(link)] = launcher.sha(link)
    rewrite(launch, via_link, "symlink")
    refused_before_anything_is_created(launch, monkeypatch, "absolute resolved path")


def test_observed_efforts_reads_only_decision_records(tmp_path):
    log = tmp_path / "control.jsonl"
    log.write_bytes(b"".join([
        json.dumps({"kind": "initialize_sent"}).encode() + b"\n",
        json.dumps({"kind": "decision", "request": {"request": {"input": {"effort": {"level": "max"}}}}}).encode() + b"\n",
        json.dumps({"kind": "decision", "request": {"request": {"input": {"effort": "high"}}}}).encode() + b"\n",
        json.dumps({"kind": "persisted_output", "request": {"request": {"input": {"effort": {"level": "low"}}}}}).encode() + b"\n",
        b"\xff not json\n",
        b"[1, 2, 3]\n", b'"a string"\n', b"7\n",                                            # not mappings (#2250)
        json.dumps({"kind": "decision", "request": None}).encode() + b"\n",
        json.dumps({"kind": "decision", "request": ["x"]}).encode() + b"\n",
        json.dumps({"kind": "decision", "request": {"request": "x"}}).encode() + b"\n",
        json.dumps({"kind": "decision", "request": {"request": {"input": None}}}).encode() + b"\n",
        json.dumps({"kind": "decision", "request": {"request": {"input": {"effort": {"level": 3}}}}}).encode() + b"\n",
        json.dumps({"kind": "decision", "request": {"request": {"input": {"effort": 3}}}}).encode() + b"\n",
        json.dumps({"kind": "decision", "request": {"request": {"input": {}}}}).encode() + b"\n"]))
    assert launcher.observed_efforts(log) == ["high", "max"]


def test_the_binding_helper_writes_records_only_for_this_exact_registration(prepared, tmp_path, monkeypatch):
    import bind_direct_launch as binding
    path, registration, _ = prepared
    digest = binding.sha(path)
    independent = tmp_path / "independent.json"
    independent.write_text(json.dumps({"verdict": "approve", "registration_sha256": digest}))
    runs = {"1": {"status": "completed", "conclusion": "success", "headSha": registration["code_commit"], "name": "Build and test data_sheets_schema"},
            "2": {"status": "completed", "conclusion": "failure", "headSha": registration["code_commit"], "name": "Build and test data_sheets_schema"},
            "3": {"status": "completed", "conclusion": "success", "headSha": "0" * 40, "name": "Build and test data_sheets_schema"},
            "4": {"status": "completed", "conclusion": "success", "headSha": registration["code_commit"], "name": "Publish"},
            "5": {"status": "in_progress", "conclusion": "", "headSha": registration["code_commit"], "name": "Build and test data_sheets_schema"}}
    monkeypatch.setattr(binding, "ci_run", lambda run_id: runs[str(run_id)])
    out = tmp_path / "review.json"
    binding.main(["review", "--registration", str(path), "--independent-review", str(independent), "--ci-run", "1", "--out", str(out)])
    record = json.loads(out.read_text())
    assert record["registration_sha256"] == digest and record["allowed_jobs"] == [JOB]
    assert record["ci_run_id"] == 1 and record["ci_conclusion"] == "success"
    for run_id, reason in (("2", "not a completed success"), ("3", "not on the registered code commit"),
                           ("4", "not the build-and-test workflow"), ("5", "not a completed success")):
        with pytest.raises(SystemExit, match=reason):
            binding.main(["review", "--registration", str(path), "--independent-review", str(independent),
                          "--ci-run", run_id, "--out", str(tmp_path / f"r{run_id}.json")])
        assert not (tmp_path / f"r{run_id}.json").exists()
    for name, verdict in (("stale", {"verdict": "approve", "registration_sha256": "f" * 64}),
                          ("rejected", {"verdict": "reject", "registration_sha256": digest})):
        other = tmp_path / f"{name}.json"
        other.write_text(json.dumps(verdict))
        with pytest.raises(SystemExit, match="exact registration"):
            binding.main(["review", "--registration", str(path), "--independent-review", str(other), "--ci-run", "1",
                          "--out", str(tmp_path / f"r-{name}.json")])
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        binding.main(["review", "--registration", str(path), "--independent-review", str(independent), "--ci-run", "1", "--out", str(out)])
    word = tmp_path / "word.json"
    binding.main(["word", "--registration", str(path), "--exact-response", "launch the CHORUS direct canary",
                  "--quoted-request", "May I launch registration abc?", "--out", str(word)])
    assert json.loads(word.read_text())["registration_sha256"] == digest
    with pytest.raises(SystemExit, match="exact response"):
        binding.main(["word", "--registration", str(path), "--exact-response", "   ", "--quoted-request", "q", "--out", str(tmp_path / "w2.json")])
    assert not (tmp_path / "w2.json").exists()
    # The launcher accepts exactly these records.
    review_ok = json.loads(out.read_text()); word_ok = json.loads(word.read_text())
    assert review_ok["verdict"] == "approve" and review_ok["ci_conclusion"] == "success"
    assert word_ok["exact_response"].strip() and word_ok["registration_sha256"] == digest


def test_the_recorder_permission_probe_builds_its_cases_offline(tmp_path):
    """The probe's case builders, without the binary: every variant keeps the line's command and prefix (#2282)."""
    import shlex
    import probe_recorder_permission as probe
    spec = {"manifest_line": "# Source manifest: m.yaml", "provider": "Anthropic (Claude subscription, direct)",
            "runtime": "Claude Code (direct)"}
    line = ("/py -m data_sheets_schema.cli provenance record --project X --render-spec-json "
            + shlex.quote(json.dumps(spec)) + ' --prompt-text "${D4D_LAUNCH_INSTRUCTION:?Set it}"')
    cases = {c["id"]: c["command"] for c in probe.isolation_cases(line, tmp_path / "i.md")}
    assert cases["real_as_given"] == line and cases["real_expansion"].endswith(probe.EXPANSION)
    assert cases["real_env_flag"].endswith(probe.ENV_FLAG) and "${" not in cases["real_env_flag"]
    # The env-form line the fix renders is accepted as well (#2310): its "as given" case is itself.
    env_line = line.rpartition(' --prompt-text "')[0] + " " + probe.ENV_FLAG
    env_cases = {c["id"]: c["command"] for c in probe.isolation_cases(env_line, tmp_path / "i.md")}
    assert env_cases["real_as_given"] == env_line and env_cases["real_expansion"] == cases["real_expansion"]
    with pytest.raises(RuntimeError, match="neither launch-instruction form"):
        probe.isolation_cases(line.rpartition(' --prompt-text "')[0], tmp_path / "i.md")
    assert all(c.startswith("/py -m data_sheets_schema.cli provenance record") for c in cases.values())
    assert "#" not in cases["real_env_flag_no_hash"] and "(" not in cases["real_env_flag_no_parens"]
    fixture = {c["id"] for c in probe.recorder_cases(line, tmp_path / "i.md")}
    assert {"expansion", "literal_path", "env_flag", "bare", "stem_only"} <= fixture




# Synthetic values in the runtime's event shape; no reading from a real attempt.
RATE = {"type": "rate_limit_event", "rate_limit_info": {
    "status": "allowed_warning", "resetsAt": 2000000000, "rateLimitType": "seven_day", "utilization": 0.62,
    "isUsingOverage": False, "surpassedThreshold": 0.5,
    "unifiedWindows": {"five_hour": {"utilization": 0.27, "resetsAt": 1999990000},
                       "seven_day": {"utilization": 0.62, "resetsAt": 2000000000}}}}


def rate_event(windows, **info):
    return {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed_warning", **info, "unifiedWindows": windows}}


def test_the_receipt_keeps_the_runtimes_rate_limit_reports(offline_launch, monkeypatch):
    """#2283, #2335: first, last and highest per window, each with its own reset."""
    launch = offline_launch
    early = rate_event({"seven_day": {"utilization": 0.58, "resetsAt": 2000000000}})
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(extra_events=[early, RATE], write_outputs=launch.write_outputs))
    assert run(launch) == 0
    limits = receipt_of(launch)["rate_limits"]
    assert limits["events"] == 2 and limits["statuses"] == ["allowed_warning"] and limits["overage_used"] is False
    week = limits["windows"]["seven_day"]
    assert (week["first"]["utilization"], week["last"]["utilization"], week["max"]["utilization"]) == (0.58, 0.62, 0.62)
    assert limits["windows"]["five_hour"]["first"] == {"utilization": 0.27, "resets_at": 1999990000}
    # A stopped attempt keeps them too.
    reset(launch)
    receipt = stopped(launch, monkeypatch, fake_child(result=False, extra_events=[RATE]),
                      "native runtime initialization or terminal result is missing or ambiguous")
    assert receipt["rate_limits"]["windows"]["seven_day"]["max"]["utilization"] == 0.62


def test_rate_limits_keep_a_falling_window_and_its_reset_apart(tmp_path):
    """#2335, #2339: a peak followed by a reset is not paired with the later reset."""
    path = tmp_path / "t.jsonl"
    events = [rate_event({"five_hour": {"utilization": 0.80, "resetsAt": 100}}),
              rate_event({"five_hour": {"utilization": 0.10, "resetsAt": 200}}, isUsingOverage=True),
              {"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "rateLimitType": "seven_day",
                                                               "utilization": 0.99, "resetsAt": 300}},
              rate_event({"opus": {"utilization": "high", "resetsAt": 400}, "sonnet": {"utilization": 0.5, "resetsAt": "soon"}})]
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    limits = launcher.rate_limits(path)
    five = limits["windows"]["five_hour"]
    assert five["max"] == {"utilization": 0.80, "resets_at": 100} and five["last"] == {"utilization": 0.10, "resets_at": 200}
    assert limits["windows"]["seven_day"]["max"] == {"utilization": 0.99, "resets_at": 300}   # a top-level-only window
    assert "opus" not in limits["windows"]                                                  # a non-numeric utilization
    assert limits["windows"]["sonnet"]["max"] == {"utilization": 0.5, "resets_at": None}    # a non-integer reset
    assert limits["overage_used"] is True and limits["statuses"] == ["allowed_warning", "rejected"]


def test_rate_limits_never_raise(tmp_path):
    assert launcher.rate_limits(tmp_path / "absent.jsonl")["note"] == "no transcript"
    garbage = tmp_path / "garbage.jsonl"
    deep = b"[" * 100000
    garbage.write_bytes(b"\xff\n{not json\n" + deep + b"\n[1]\n" + json.dumps({"type": "rate_limit_event", "rate_limit_info": "x"}).encode()
                        + b"\n" + json.dumps(RATE).encode() + b"\n")
    limits = launcher.rate_limits(garbage)
    assert limits["events"] == 1 and "note" not in limits                                   # skipped per line (#2340)


def recorder_denial(launch):
    job = launch.registration["generation"]["jobs"][0]
    recorder = next(line.strip() for line in Path(job["instruction"]).read_text().splitlines()
                    if " -m data_sheets_schema.cli provenance record" in line)
    return {"tool_name": "Bash", "tool_use_id": "denied_recorder", "tool_input": {"command": recorder}}


def test_a_stopped_receipt_leads_with_the_disqualifying_denial_only_for_the_evidence_stop(offline_launch, monkeypatch):
    """#2285, #2334: the denial leads only where the child completed and the controller stopped for missing evidence."""
    launch = offline_launch
    evidence = BudgetStop("native control session ended without complete evidence")
    child = fake_child(terminal={"subtype": "success", "permission_denials": [recorder_denial(launch)]},
                       write_outputs=launch.write_outputs, raise_after=evidence)
    monkeypatch.setattr(launcher.native, "execute_child", child)
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert receipt["status"] == "stopped" and receipt["child_completed"] is True
    assert receipt["reason_source"] == "denial" and receipt["reason"].startswith("disqualified: denied prescribed call")
    assert receipt["controller_reason"] == "native control session ended without complete evidence"
    assert receipt["controller_reason_source"] == "controller"
    # Without a disqualifying denial the controller's reason stands.
    reset(launch)
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(terminal={"subtype": "success"},
                        write_outputs=launch.write_outputs, raise_after=evidence))
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert receipt["reason"] == "native control session ended without complete evidence" and "controller_reason" not in receipt
    # Another controller stop beside a denial keeps the headline: a deadline after the result,
    # and a child that did not complete.
    for stop, terminal in ((BudgetStop("native attempt deadline elapsed"), {"subtype": "success"}),
                           (evidence, {"subtype": "error_max_budget_usd", "is_error": True, "terminal_reason": "budget"})):
        reset(launch)
        monkeypatch.setattr(launcher.native, "execute_child", fake_child(
            terminal={**terminal, "permission_denials": [recorder_denial(launch)]}, write_outputs=launch.write_outputs,
            raise_after=stop))
        assert run(launch) == 1
        receipt = receipt_of(launch)
        assert receipt["reason"] == str(stop) and receipt["reason_source"] == "controller" and "controller_reason" not in receipt
        assert receipt["disqualifying_denials"]


def test_an_init_line_naming_another_model_keeps_the_model_in_the_reason_beside_a_denial(offline_launch, monkeypatch):
    """#2334: a [1m] stop names the observed model even when a denial is present."""
    launch = offline_launch
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(
        model="claude-opus-5[1m]", terminal={"subtype": "success", "permission_denials": [recorder_denial(launch)]},
        write_outputs=launch.write_outputs))
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert "model 'claude-opus-5[1m]'" in receipt["reason"] and receipt["reason_source"] == "controller"


def test_the_child_outcome_names_calls_no_decision_covers(tmp_path):
    """#2338: by id and transcript line; #2340: non-string ids are skipped, not fatal."""
    transcript, control_log = tmp_path / "t.jsonl", tmp_path / "c.jsonl"
    long_text = "x" * 500
    events = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "a", "name": "Read"},
                                                             {"type": "tool_use", "id": "b", "name": "Write"},
                                                             {"type": "tool_use", "id": "c", "name": "Write"},
                                                             {"type": "tool_use", "id": ["odd"], "name": "Bash"}]}},
              {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "b",
                                                        "content": [{"type": "text", "text": long_text}]},
                                                       {"type": "tool_result", "tool_use_id": {"odd": 1}, "content": "?"}]}},
              {"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed", "stop_reason": "end_turn"}]
    transcript.write_text("".join(json.dumps(e) + "\n" for e in events))
    control_log.write_text(json.dumps({"kind": "decision", "request": {"request": {"input": {"tool_use_id": "a"}}}}) + "\n"
                           + json.dumps({"kind": "input_rejected_before_callback", "tool_use_id": "c"}) + "\n"
                           + json.dumps({"kind": "input_rejected_before_callback", "tool_use_id": ["x"]}) + "\n")
    outcome = launcher.child_outcome(transcript, control_log)
    assert outcome["child_completed"] is True and outcome["result_subtype"] == "success"
    [entry] = outcome["uncovered_tool_calls"]
    assert (entry["tool_use_id"], entry["tool"], entry["transcript_line"]) == ("b", "Write", 1)
    assert len(entry["result_head"]) == 160 and entry["result_head"].startswith('[{"type": "text"')
    assert "child_outcome_note" not in outcome
    # No control log: every call is uncovered and the absence is said.
    missing = launcher.child_outcome(transcript, tmp_path / "absent.jsonl")
    assert missing["control_log_missing"] is True and {e["tool_use_id"] for e in missing["uncovered_tool_calls"]} == {"a", "b", "c"}
    assert launcher.child_outcome(tmp_path / "absent.jsonl", control_log)["uncovered_tool_calls"] is None


@pytest.mark.parametrize("terminal, exit_code, completed", [
    ({"subtype": "success", "is_error": False, "terminal_reason": "completed", "stop_reason": "end_turn"}, 0, True),
    ({"subtype": "success", "is_error": False, "terminal_reason": "completed", "stop_reason": "end_turn"}, 1, False),
    ({"subtype": "success", "is_error": False, "terminal_reason": "completed", "stop_reason": "max_tokens"}, 0, False),
    ({"subtype": "success", "is_error": False, "terminal_reason": "max_turns", "stop_reason": "end_turn"}, 0, False),
    ({"subtype": "error_max_budget_usd", "is_error": True, "terminal_reason": "completed", "stop_reason": "end_turn"}, 0, False),
])
def test_child_completed_uses_the_launchers_own_predicate(tmp_path, terminal, exit_code, completed):
    """#2337: never 'completed' beside the launcher's 'failed or stopped before completion'."""
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(json.dumps({"type": "result", **terminal}) + "\n")
    assert launcher.child_outcome(transcript, tmp_path / "c.jsonl", exit_code)["child_completed"] is completed
    two = tmp_path / "two.jsonl"
    two.write_text((json.dumps({"type": "result", **terminal}) + "\n") * 2)
    assert launcher.child_outcome(two, tmp_path / "c.jsonl", 0)["child_completed"] is False



def test_the_first_disqualifying_denial_leads_and_only_the_exact_evidence_stop_is_relabelled(offline_launch, monkeypatch):
    """#2339: which denial leads; exact equality of the evidence-stop reason; #2334: a pin change stays the reason."""
    launch = offline_launch
    job = launch.registration["generation"]["jobs"][0]
    receipts = next(line.strip() for line in Path(job["instruction"]).read_text().splitlines()
                    if " -m data_sheets_schema.cli" in line and "receipts check" in line)
    second = {"tool_name": "Bash", "tool_use_id": "denied_receipts", "tool_input": {"command": receipts}}
    evidence = BudgetStop("native control session ended without complete evidence")
    monkeypatch.setattr(launcher.native, "execute_child", fake_child(
        terminal={"subtype": "success", "permission_denials": [recorder_denial(launch), second]},
        write_outputs=launch.write_outputs, raise_after=evidence))
    assert run(launch) == 1
    receipt = receipt_of(launch)
    assert len(receipt["disqualifying_denials"]) == 2
    assert receipt["reason"] == "disqualified: " + receipt["disqualifying_denials"][0]
    assert "provenance record" in receipt["reason"]
    for stop in (BudgetStop("native input rejection has contradictory execution evidence"),
                 BudgetStop("a registered pin changed: instruction.md")):
        reset(launch)
        monkeypatch.setattr(launcher.native, "execute_child", fake_child(
            terminal={"subtype": "success", "permission_denials": [recorder_denial(launch)]},
            write_outputs=launch.write_outputs, raise_after=stop))
        assert run(launch) == 1
        receipt = receipt_of(launch)
        assert receipt["reason"] == str(stop) and receipt["reason_source"] == "controller"
        assert "controller_reason" not in receipt and receipt["disqualifying_denials"]


def test_the_outcome_and_rate_readers_skip_malformed_shapes(tmp_path):
    """#2339: the window, decision-record and content-block guards; #2340: an aborted scan names itself."""
    rates = tmp_path / "rates.jsonl"
    rates.write_text(json.dumps(rate_event({"odd": 5, "seven_day": {"utilization": 0.5, "resetsAt": 1}})) + "\n")
    windows = launcher.rate_limits(rates)["windows"]
    assert "odd" not in windows and windows["seven_day"]["max"] == {"utilization": 0.5, "resets_at": 1}
    transcript, control_log = tmp_path / "t.jsonl", tmp_path / "c.jsonl"
    events = [{"type": "assistant", "message": {"content": ["plain text", {"type": "tool_use", "id": "a", "name": "Read"},
                                                             {"type": "tool_use", "id": "b", "name": "Read"}]}}]
    transcript.write_text("".join(json.dumps(e) + "\n" for e in events))
    control_log.write_text("".join(json.dumps(r) + "\n" for r in [
        {"kind": "decision", "request": "text"},                                          # request not a mapping
        {"kind": "decision", "request": {"request": "text"}},                             # inner not a mapping
        {"kind": "decision", "request": {"request": {"input": ["a"]}}},                   # input not a mapping
        {"kind": "decision", "request": {"request": {"input": {"tool_use_id": ["a"]}}}},  # id not a string
        {"kind": "decision", "request": {"request": {"input": {"tool_use_id": "b"}}}}]))
    outcome = launcher.child_outcome(transcript, control_log)
    assert [e["tool_use_id"] for e in outcome["uncovered_tool_calls"]] == ["a"]
    aborted = launcher.child_outcome(tmp_path, control_log)                               # a directory, not a file
    assert aborted["uncovered_tool_calls"] is None and aborted["child_outcome_note"].startswith("outcome unreadable:")


def test_a_command_policy_that_cannot_be_built_is_a_named_stop_that_leaves_nothing(tmp_path, monkeypatch):
    """#2369, #2317: a registered spelling the runtime would refuse stops preparation before anything stays."""
    monkeypatch.chdir(ROOT)
    for name in preparation.FORBIDDEN_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    fake = fake_runtime(tmp_path)
    monkeypatch.setattr(preparation, "auth_evidence", lambda executable, env: dict(AUTH))

    def refused(job, python, repository):
        raise ValueError("a registered command is not admitted as written (synthetic): x")
    monkeypatch.setattr(preparation, "build_command_policy", refused)
    with pytest.raises(preparation.DirectStop, match="command policy cannot be built: a registered command is not admitted"):
        preparation.build(arguments(tmp_path, fake, output=tmp_path / "r"))
    assert not (tmp_path / "r").exists()
    assert not list(tmp_path.glob(".r.auth-probe-*"))


def test_a_respelled_prescribed_call_denied_by_the_controller_does_not_disqualify(prepared):
    """#2369: under the registered version-5 policy a respelling is the controller's refusal."""
    path, registration, fake = prepared
    job = registration["generation"]["jobs"][0]
    policy = registration["per_job_command_policy"][job["id"]]
    assert policy["version"] == 5 and policy["literal_admission"] == 1
    receipts = next(line.strip() for line in Path(job["instruction"]).read_text().splitlines()
                    if " -m data_sheets_schema.cli" in line and "receipts check" in line)
    classified = launcher.native.classify_denials(
        [{"tool_name": "Bash", "tool_use_id": "respelled", "tool_input": {"command": receipts + " --label $X"}},
         {"tool_name": "Bash", "tool_use_id": "registered", "tool_input": {"command": receipts}}],
        instruction_text="", python=policy["python"], repository="/unused", output_directories=[],
        readable_inputs=[], command_policy=policy)
    assert [d["classification"] for d in classified] == ["not_prescribed", "prescribed"]
    assert launcher.native.denial_problems(classified) == [
        f"denied prescribed call (Bash): {classified[1]['basis']}"]
