"""Offline checks of the paid-run gates; these never call an evaluator service."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest

from tests.test_evaluation.test_semantic_evaluation_contract import _rubric10_record, _rubric20_record

REAL_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reference_rescore", REAL_ROOT / "scripts/reference_rescore.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def valid_record(number=10):
    doc = _rubric10_record() if number == 10 else _rubric20_record()
    if number == 10:
        for e in doc["elements"]:
            for sub in e["sub_elements"]:
                sub["applicable"] = sub["score"] is not None
        doc["overall_score"]["total_points"] = 48
        doc["overall_score"]["normalized_percentage"] = 100.0
        doc["overall_score"]["fixed_percentage"] = 96.0
    else:
        doc["overall_score"]["fixed_percentage"] = round(100 * 83 / 88, 1)
    return doc


def test_registered_cohort_and_repeats_are_exact():
    jobs = runner.cohort_jobs()
    assert len(jobs) == 56 and len({j["id"] for j in jobs}) == 56
    assert jobs[0]["id"] == "CHORUS_v7_rep1_r10_rating1"
    assert len({j["input"] for j in jobs}) == 24
    assert sum(j["purpose"] == "primary" for j in jobs) == 48
    repeated = [j for j in jobs if j["purpose"] == "repeatability"]
    assert len(repeated) == 8
    assert {j["rubric"] for j in repeated} == {"rubric10-semantic"}
    assert all(j["cohort"] == "v7" and j["generation_rep"] == 1 for j in repeated)
    assert all((REAL_ROOT / j["input"]).exists() for j in jobs)


@pytest.mark.parametrize("number", [10, 20])
def test_arithmetic_checks_the_actual_item_scores(number):
    doc = valid_record(number)
    runner.check_arithmetic(doc)
    doc["overall_score"]["total_points"] -= 1
    with pytest.raises(ValueError, match="overall"):
        runner.check_arithmetic(doc)


@pytest.mark.parametrize("mutation", ["duplicates", "denominator", "percentage", "na"])
def test_plausible_but_wrong_item_or_percentage_results_fail(mutation):
    doc = valid_record()
    if mutation == "duplicates":
        doc["elements"][0]["id"] = 2
    elif mutation == "denominator":
        doc["elements"][7]["element_max"] = 5
    elif mutation == "percentage":
        doc["overall_score"]["fixed_percentage"] = 100
    else:
        doc["elements"][7]["sub_elements"][0]["applicable"] = True
    with pytest.raises(ValueError):
        runner.check_arithmetic(doc)


def events(doc, validator_success=True):
    return [
        {"type": "assistant", "message": {"model": "claude-opus-5", "content": [
            {"type": "text", "text": "verified current definition"},
            {"type": "tool_use", "name": "Bash", "id": "validate", "input": {
                "command": "poetry run python scripts/validate_evaluation_schema.py --file output_evaluation.json --rubric rubric10-semantic"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "validate",
            "is_error": not validator_success, "content": "VALID output_evaluation.json: rubric10-semantic"}]}},
        {"type": "result", "subtype": "success", "is_error": False},
    ]


@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "PLAN", tmp_path / "plan")
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    monkeypatch.setattr(runner.tempfile, "tempdir", str(temporary))
    monkeypatch.setattr(runner, "spawn_preamble", lambda agent: "PREAMBLE")

    def echo(agent, text):
        if "verified current definition" not in text:
            raise ValueError("stale echo")

    monkeypatch.setattr(runner, "verify_echo", echo)
    job = copy.deepcopy(runner.cohort_jobs()[0])
    (tmp_path / job["input"]).parent.mkdir(parents=True)
    (tmp_path / job["input"]).write_text("id: example\n")
    paths = ["scripts/validate_evaluation_schema.py", "scripts/reference_rescore.py", "pyproject.toml", "poetry.lock",
             ".claude/agents/d4d-rubric10-semantic.md", "data/rubric/rubric10.txt",
             "src/download/prompts/rubric10_semantic_schema.json"]
    for path in paths:
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_ROOT / path, dest)
    instrument = {"definition": paths[4], "definition_sha256": runner.digest(tmp_path / paths[4]),
                  "agent": job["agent"], "rubric": paths[5], "schema": paths[6], "preamble": "PREAMBLE"}
    prior = tmp_path / "prior_evaluation.json"
    prior.write_text('{"previous": true}\n')
    manifest = {"canary_id": job["id"], "jobs": [job], "requested_model": runner.MODEL,
                "effort": "high", "budget_cap_usd_per_attempt": 5,
                "instruments": {job["rubric"]: instrument},
                "pinned_files": {p: runner.digest(tmp_path / p) for p in paths + [job["input"]]},
                "prior_evaluations": {"prior_evaluation.json": runner.digest(prior)}}
    runner.write_json(runner.PLAN / "manifest.json", manifest)
    doc = valid_record()
    doc.update({k: job[k] for k in ("rubric", "project", "method", "label")})
    doc["d4d_file"] = job["input"]
    doc["model"] = {"name": "claude-opus-5", "evaluator_model": "claude-opus-5",
                    "temperature": None, "evaluation_type": "semantic_llm_judge"}
    doc["metadata"] = {"instrument_sha256": instrument["definition_sha256"],
                       "instrument_kind": "agent_definition", "rubric_hash": manifest["pinned_files"][instrument["rubric"]],
                       "input_sha256": manifest["pinned_files"][job["input"]]}
    return tmp_path, manifest, job, doc


def fake_cli(path, doc, trace, failure=False, run_validator=False):
    path.write_text(f"#!{sys.executable}\nimport json,sys,shlex,subprocess\nfrom pathlib import Path\n" +
                    f"assert Path.cwd().parent == Path({str(path.parent / 'temporary')!r})\n" +
                    ("print('Weekly quota exhausted')\nsys.exit(1)\n" if failure else
                     "prompt=sys.stdin.read()\nassert Path('input/record.yaml').read_text() in prompt\n" +
                     f"Path('output_evaluation.json').write_text({json.dumps(doc)!r})\n" +
                     f"trace=json.loads({json.dumps(trace)!r}.replace('__ISOLATED__', str(Path.cwd())))\n" +
                     ("command=trace[1]['message']['content'][1]['input']['command']\n"
                      "validated=subprocess.run(shlex.split(command),text=True,capture_output=True)\n"
                      "assert validated.returncode==0, validated.stdout+validated.stderr\n"
                      "trace[2]['message']['content'][0]['content']=validated.stdout\n" if run_validator else "") +
                     "print('\\n'.join(json.dumps(e) for e in trace))\n"))
    path.chmod(0o755)
    return str(path)


def test_invalid_or_unmatched_validator_receipt_is_rejected():
    trace = events(valid_record())
    trace[1]["message"]["content"][0]["content"] = "INVALID output_evaluation.json: rubric10-semantic"
    assert not runner.evaluator_validated(trace, "rubric10-semantic")
    trace = events(valid_record())
    trace[1]["message"]["content"][0]["tool_use_id"] = "another-call"
    assert not runner.evaluator_validated(trace, "rubric10-semantic")


@pytest.mark.parametrize("script,output", [
    ("scripts/validate_evaluation_schema.py", "__ISOLATED__/output_evaluation.json"),
    ("__ISOLATED__/scripts/validate_evaluation_schema.py", "output_evaluation.json"),
    ("__ISOLATED__/scripts/validate_evaluation_schema.py", "__ISOLATED__/output_evaluation.json"),
])
def test_equivalent_own_file_validator_paths_attest_the_rating(environment, script, output):
    root, manifest, job, doc = environment
    trace = events(doc)
    trace[0]["message"]["content"][1]["input"]["command"] = (
        f"poetry run python {script} --file {output} --rubric rubric10-semantic")
    trace.insert(0, {"type": "system", "subtype": "init", "cwd": "__ISOLATED__"})
    cli = fake_cli(root / "fake-claude", doc, trace, run_validator=True)
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "passed", receipt


@pytest.mark.parametrize("command_output,receipt_output", [
    ("/isolated/output_evaluation.json", "output_evaluation.json"),
    ("output_evaluation.json", "/isolated/output_evaluation.json"),
    ("/isolated/output_evaluation.json", "/other/output_evaluation.json"),
])
def test_validator_receipt_must_name_the_exact_command_output(command_output, receipt_output):
    trace = events(valid_record())
    trace[0]["message"]["content"][1]["input"]["command"] = (
        f"poetry run python scripts/validate_evaluation_schema.py --file {command_output} --rubric rubric10-semantic")
    trace[1]["message"]["content"][0]["content"] = f"VALID {receipt_output}: rubric10-semantic"
    trace.insert(0, {"type": "system", "subtype": "init", "cwd": "/isolated"})
    assert not runner.evaluator_validated(trace, "rubric10-semantic")


@pytest.mark.parametrize("timing", ["after", "overlapping"])
@pytest.mark.parametrize("revalidate", ["missing", "failed", "passed"])
def test_validation_must_follow_the_last_potential_mutation(timing, revalidate):
    trace = events(valid_record())
    write = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write",
            "id": "rewrite", "input": {"file_path": "/isolated/output_evaluation.json", "content": "{}"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "rewrite",
            "content": "File updated successfully"}]}},
    ]
    if timing == "after":
        trace = trace[:2] + write + trace[2:]
    else:
        trace = write[:1] + trace[:2] + write[1:] + trace[2:]
    if revalidate != "missing":
        fresh = events(valid_record(), validator_success=revalidate == "passed")[:2]
        fresh[0]["message"]["content"][1]["id"] = "fresh-validation"
        fresh[1]["message"]["content"][0]["tool_use_id"] = "fresh-validation"
        trace = trace[:-1] + fresh + trace[-1:]
    assert runner.evaluator_validated(trace, "rubric10-semantic") is (revalidate == "passed")


@pytest.mark.parametrize("command", [
    "poetry run python /other/scripts/validate_evaluation_schema.py --file /isolated/output_evaluation.json --rubric rubric10-semantic",
    "poetry run python /isolated/scripts/validate_evaluation_schema.py --file /other/output_evaluation.json --rubric rubric10-semantic",
    "poetry run python scripts/validate_evaluation_schema.py --file output_evaluation.json --rubric rubric20-semantic",
    'poetry run python scripts/validate_evaluation_schema.py --file output_evaluation.json --rubric rubric10-semantic; echo "EXIT=$?"',
    "poetry run python scripts/validate_evaluation_schema.py --file output_evaluation.json --rubric rubric10-semantic > /tmp/other",
    "poetry run python /isolated/$UNTRUSTED/../scripts/validate_evaluation_schema.py --file output_evaluation.json --rubric rubric10-semantic",
    "poetry run python 'scripts/validate_evaluation_schema.py --file output_evaluation.json --rubric rubric10-semantic",
    None,
])
def test_other_files_or_extra_shell_commands_do_not_attest_validation(command):
    trace = events(valid_record())
    trace[0]["message"]["content"][1]["input"]["command"] = command
    trace.insert(0, {"type": "system", "subtype": "init", "cwd": "/isolated"})
    assert not runner.evaluator_validated(trace, "rubric10-semantic")


def test_absolute_validator_needs_a_unique_recorded_working_directory():
    trace = events(valid_record())
    trace[0]["message"]["content"][1]["input"]["command"] = (
        "poetry run python /isolated/scripts/validate_evaluation_schema.py "
        "--file /isolated/output_evaluation.json --rubric rubric10-semantic")
    assert not runner.evaluator_validated(trace, "rubric10-semantic")
    trace[:0] = [{"type": "system", "subtype": "init", "cwd": p} for p in ("/isolated", "/other")]
    assert not runner.evaluator_validated(trace, "rubric10-semantic")


@pytest.mark.parametrize("placement", ["metadata", "both"])
def test_matching_metadata_label_is_accepted_without_rewriting(environment, placement):
    root, manifest, job, doc = environment
    doc["metadata"]["label"] = doc["label"]
    if placement == "metadata":
        del doc["label"]
    cli = fake_cli(root / "fake-claude", doc, events(doc))
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "passed", receipt
    assert json.loads((root / job["output"]).read_bytes()) == doc


@pytest.mark.parametrize("defect", ["top", "metadata", "missing"])
def test_missing_or_conflicting_labels_never_publish_a_rating(environment, defect):
    root, manifest, job, doc = environment
    doc["metadata"]["label"] = doc["label"]
    if defect == "missing":
        del doc["label"]
        del doc["metadata"]["label"]
    else:
        (doc if defect == "top" else doc["metadata"])["label"] = "another-run"
    cli = fake_cli(root / "fake-claude", doc, events(doc))
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "incomplete"
    assert not (root / job["output"]).exists()


def test_exact_poetry_validator_command_runs_in_isolated_environment(environment):
    import os
    import subprocess
    root, _, _, doc = environment
    (root / "output_evaluation.json").write_text(json.dumps(doc))
    env = {**os.environ, "VIRTUAL_ENV": sys.prefix,
           "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")}
    env.pop("CONDA_DEFAULT_ENV", None)
    done = subprocess.run(["poetry", "run", "python", "scripts/validate_evaluation_schema.py",
                           "--file", "output_evaluation.json", "--rubric", "rubric10-semantic"],
                          cwd=root, env=env, text=True, capture_output=True)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "VALID output_evaluation.json: rubric10-semantic" in done.stdout


def test_successful_canary_preserves_old_scores_and_gates_the_fill(environment):
    root, manifest, job, doc = environment
    old = (root / "prior_evaluation.json").read_bytes()
    trace = events(doc)
    trace.insert(1, {"type": "system", "subtype": "permission_denied",
                     "message": "Permission to use Bash has been denied"})
    trace.insert(2, {"type": "user", "message": {"content": "An ordinary text message"}})
    cli = fake_cli(root / "fake-claude", doc, trace)
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "passed", receipt
    assert (root / "prior_evaluation.json").read_bytes() == old
    fill = {**job, "id": "another-record"}
    with pytest.raises(FileNotFoundError):
        runner.require_canary(manifest, fill)
    runner.accept_canary(manifest)
    runner.require_canary(manifest, fill)
    assert runner.successful_receipt(manifest, job)["evaluation_sha256"] == runner.digest(root / job["output"])
    with pytest.raises(ValueError, match="overwrite"):
        runner.run_job(manifest, job, cli)


@pytest.mark.parametrize("index,role", [(0, "system"), (0, "user"), (1, "system"), (1, "assistant")])
def test_diagnostic_or_wrong_role_cannot_attest_validation(index, role):
    trace = events(valid_record())
    trace[index]["type"] = role
    assert not runner.evaluator_validated(trace, "rubric10-semantic")


def test_cli_attested_context_selector_preserves_reported_and_runtime_identity(environment):
    root, manifest, job, doc = environment
    doc["model"]["name"] = doc["model"]["evaluator_model"] = runner.MODEL
    trace = events(doc)
    trace[-1]["modelUsage"] = {runner.MODEL: {"canonicalModel": "claude-opus-5", "contextWindow": 1_000_000}}
    cli = fake_cli(root / "fake-claude", doc, trace)
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "passed", receipt
    assert receipt["runtime_model"] == "claude-opus-5"
    assert receipt["reported_model"] == runner.MODEL
    assert receipt["model_alias_evidence"]["basis"] == "CLI result modelUsage"
    assert json.loads((root / job["output"]).read_bytes())["model"] == doc["model"]


@pytest.mark.parametrize("placement", ["metadata", "both"])
@pytest.mark.parametrize("alias", [False, True])
def test_evaluator_model_locations_are_attested_without_rewriting(environment, placement, alias):
    root, manifest, job, doc = environment
    doc["metadata"]["evaluator_model"] = runner.MODEL if alias else doc["model"]["name"]
    if placement == "metadata":
        del doc["model"]["evaluator_model"]
    trace = events(doc)
    if alias:
        trace[-1]["modelUsage"] = {runner.MODEL: {"canonicalModel": "claude-opus-5", "contextWindow": 1_000_000}}
    cli = fake_cli(root / "fake-claude", doc, trace)
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "passed", receipt
    assert receipt["evaluator_model_declarations"]["metadata.evaluator_model"] == doc["metadata"]["evaluator_model"]
    assert json.loads((root / job["output"]).read_bytes()) == doc
    if alias:
        assert receipt["model_identity_aliases"]["metadata.evaluator_model"]["canonical_model"] == "claude-opus-5"


@pytest.mark.parametrize("defect", ["missing", "metadata_conflict", "model_conflict", "unattested_alias", "not_string"])
def test_missing_or_conflicting_evaluator_model_declarations_fail(environment, defect):
    root, manifest, job, doc = environment
    doc["metadata"]["evaluator_model"] = doc["model"]["name"]
    if defect == "missing":
        del doc["model"]["evaluator_model"]
        del doc["metadata"]["evaluator_model"]
    elif defect == "metadata_conflict":
        doc["metadata"]["evaluator_model"] = "another-model"
    elif defect == "model_conflict":
        doc["model"]["evaluator_model"] = "another-model"
    elif defect == "unattested_alias":
        doc["metadata"]["evaluator_model"] = runner.MODEL
    else:
        doc["metadata"]["evaluator_model"] = ["claude-opus-5"]
    cli = fake_cli(root / "fake-claude", doc, events(doc))
    assert runner.run_job(manifest, job, cli)["status"] == "incomplete"
    assert not (root / job["output"]).exists()


@pytest.mark.parametrize("defect", ["missing", "canonical", "context", "fields", "selector"])
def test_model_alias_requires_matching_runtime_usage_evidence(environment, defect):
    root, manifest, job, doc = environment
    doc["model"]["name"] = doc["model"]["evaluator_model"] = runner.MODEL
    alias = {"canonicalModel": "claude-opus-5", "contextWindow": 1_000_000}
    trace = events(doc)
    trace[-1]["modelUsage"] = {runner.MODEL: alias}
    if defect == "missing":
        del trace[-1]["modelUsage"]
    elif defect == "canonical":
        alias["canonicalModel"] = "another-model"
    elif defect == "context":
        alias["contextWindow"] = 200_000
    elif defect == "fields":
        doc["model"]["evaluator_model"] = "another-model"
    else:
        doc["model"]["name"] = doc["model"]["evaluator_model"] = "unrecognized-selector"
        trace[-1]["modelUsage"]["unrecognized-selector"] = alias
    cli = fake_cli(root / "fake-claude", doc, trace)
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "incomplete"
    assert not (root / job["output"]).exists()


@pytest.fixture
def retained_canary(environment, monkeypatch):
    root, manifest, job, doc = environment
    trace = events(doc)
    trace[:0] = [
        {"type": "system", "subtype": "init", "cwd": "/isolated"},
        {"type": "assistant", "message": {"model": "claude-opus-5", "content": [
            {"type": "tool_use", "name": "Write", "id": "write-output", "input": {
                "file_path": "/isolated/output_evaluation.json", "content": json.dumps(doc)}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "write-output",
            "content": "File created successfully"}]}},
    ]
    cli = fake_cli(root / "fake-claude", doc, trace)

    def old_parser(*args):
        raise AttributeError("'str' object has no attribute 'get'")

    with monkeypatch.context() as context:
        context.setattr(runner, "evaluator_validated", old_parser)
        failed = runner.run_job(manifest, job, cli)
    assert failed["status"] == "incomplete"
    source = next((runner.PLAN / "attempts" / job["id"]).iterdir())
    original_bytes = {p.name: p.read_bytes() for p in source.iterdir()}
    archive = runner.PLAN / "registrations/previous.json"
    archive.parent.mkdir()
    shutil.copyfile(runner.PLAN / "manifest.json", archive)
    updated = copy.deepcopy(manifest)
    script = root / "scripts/reference_rescore.py"
    script.write_bytes(script.read_bytes() + b"\n# Offline runner amendment fixture.\n")
    updated["pinned_files"]["scripts/reference_rescore.py"] = runner.digest(script)
    updated["supersedes_registration"] = {"path": str(archive.relative_to(root)),
                                         "sha256": runner.digest(archive), "reason": "runner parser fix"}
    runner.write_json(runner.PLAN / "manifest.json", updated)
    return root, updated, job, source, original_bytes


def test_recovery_preserves_attempt_and_requires_separate_acceptance(retained_canary):
    root, manifest, job, source, original_bytes = retained_canary
    recovered = runner.recover_canary(manifest, source)
    assert recovered["status"] == "passed" and recovered["model_calls_during_recovery"] == 0
    assert {p.name: p.read_bytes() for p in source.iterdir()} == original_bytes
    assert (root / job["output"]).read_bytes() == original_bytes["candidate.json"]
    assert runner.successful_receipt(manifest, job) == recovered
    fill = {**job, "id": "another-record"}
    with pytest.raises(FileNotFoundError):
        runner.require_canary(manifest, fill)
    runner.accept_canary(manifest)
    runner.require_canary(manifest, fill)
    with pytest.raises(ValueError, match="overwrite"):
        runner.recover_canary(manifest, source)


@pytest.mark.parametrize("outcome", ["passed", "incomplete", "runtime_mismatch"])
def test_noncanary_recovery_preserves_original_evidence_and_requires_reaccepted_canary(environment, monkeypatch, outcome):
    root, manifest, canary, doc = environment
    passed = outcome == "passed"
    job = {**canary, "id": canary["id"].replace("rating1", "rating2"), "rating": 2,
           "purpose": "repeatability", "output": canary["output"].replace("rating1", "rating2")}
    manifest["jobs"].append(job)
    runner.write_json(runner.PLAN / "manifest.json", manifest)
    trace = events(doc)
    trace[:0] = [
        {"type": "system", "subtype": "init", "cwd": "/isolated"},
        {"type": "assistant", "message": {"model": "claude-opus-5", "content": [
            {"type": "tool_use", "name": "Write", "id": "write-output", "input": {
                "file_path": "/isolated/output_evaluation.json", "content": json.dumps(doc)}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "write-output",
            "content": "File created successfully"}]}},
    ]
    cli = fake_cli(root / "fake-claude", doc, trace)
    assert runner.run_job(manifest, canary, cli)["status"] == "passed"
    runner.accept_canary(manifest)
    if outcome == "runtime_mismatch":
        doc["model"]["name"] = doc["model"]["evaluator_model"] = runner.MODEL
        trace[1]["message"]["content"][0]["input"]["content"] = json.dumps(doc)
        for event in trace:
            if event.get("type") == "assistant":
                event["message"]["model"] = runner.MODEL
        cli = fake_cli(root / "fake-claude", doc, trace)
    with monkeypatch.context() as context:
        if outcome == "incomplete":
            def old_parser(*args):
                raise ValueError("evaluator_model location rejected by old runner")
            context.setattr(runner, "validate_candidate", old_parser)
        receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == ("passed" if passed else "incomplete")
    source = next((runner.PLAN / "attempts" / job["id"]).iterdir())
    original_bytes = {p.name: p.read_bytes() for p in source.iterdir()}
    canary_source = next((runner.PLAN / "attempts" / canary["id"]).iterdir())
    archive = runner.PLAN / "registrations/before-model-location-fix.json"
    archive.parent.mkdir()
    shutil.copyfile(runner.PLAN / "manifest.json", archive)
    updated = copy.deepcopy(manifest)
    script = root / "scripts/reference_rescore.py"
    script.write_bytes(script.read_bytes() + b"\n# Runner-only location amendment.\n")
    updated["pinned_files"]["scripts/reference_rescore.py"] = runner.digest(script)
    updated["supersedes_registration"] = {"path": str(archive.relative_to(root)), "sha256": runner.digest(archive)}
    runner.write_json(runner.PLAN / "manifest.json", updated)
    with pytest.raises(ValueError, match="canary acceptance"):
        runner.recover_rating(updated, source)
    with pytest.raises(ValueError, match="original completed-CLI receipt"):
        runner.recover_canary(updated, source)
    runner.recover_canary(updated, canary_source)
    runner.accept_canary(updated)
    destination = root / job["output"]
    if outcome == "runtime_mismatch":
        with pytest.raises(ValueError, match="runtime model differs"):
            runner.recover_rating(updated, source)
        assert not destination.exists()
        assert {p.name: p.read_bytes() for p in source.iterdir()} == original_bytes
        return
    actual_open = Path.open

    def preserve_existing_output(path, mode="r", *args, **kwargs):
        if passed and path == destination and any(flag in mode for flag in "wax+"):
            raise AssertionError("existing rating must not be opened for writing")
        return actual_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", preserve_existing_output)
    recovered = runner.recover_rating(updated, source)
    assert recovered["status"] == "passed"
    assert recovered["preserved_existing_output"] is passed
    assert recovered["model_calls_during_recovery"] == 0
    assert {p.name: p.read_bytes() for p in source.iterdir()} == original_bytes
    assert destination.read_bytes() == original_bytes["candidate.json"]
    assert runner.successful_receipt(updated, job) == recovered
    with pytest.raises(ValueError, match="already exists"):
        runner.recover_rating(updated, source)
    receipts = {p: p.read_bytes() for p in (runner.PLAN / "attempts" / job["id"]).glob("*/receipt.json")}
    destination.unlink()
    with pytest.raises(ValueError, match="already exists"):
        runner.recover_rating(updated, source)
    assert not destination.exists()
    assert {p: p.read_bytes() for p in (runner.PLAN / "attempts" / job["id"]).glob("*/receipt.json")} == receipts


@pytest.mark.parametrize("filename", ["receipt.json", "prompt.txt"])
def test_recovery_rejects_changed_original_receipt_or_prompt(retained_canary, monkeypatch, filename):
    root, manifest, job, source, _ = retained_canary
    actual_run = runner.subprocess.run

    def change_evidence_after_validation(*args, **kwargs):
        completed = actual_run(*args, **kwargs)
        p = source / filename
        p.write_bytes(p.read_bytes() + b"\n")
        return completed

    monkeypatch.setattr(runner.subprocess, "run", change_evidence_after_validation)
    with pytest.raises(ValueError, match="changed during recovery"):
        runner.recover_canary(manifest, source)
    assert not (root / job["output"]).exists()


def test_later_runner_amendment_revalidates_the_existing_canary_without_rewriting(retained_canary, monkeypatch):
    root, manifest, job, source, original_bytes = retained_canary
    runner.recover_canary(manifest, source)
    runner.accept_canary(manifest)
    destination = root / job["output"]
    old_acceptance = (runner.PLAN / "canary_acceptance.json").read_bytes()
    archive = runner.PLAN / "registrations/previous-runner-amendment.json"
    shutil.copyfile(runner.PLAN / "manifest.json", archive)
    updated = copy.deepcopy(manifest)
    script = root / "scripts/reference_rescore.py"
    script.write_bytes(script.read_bytes() + b"\n# Second runner-only amendment fixture.\n")
    updated["pinned_files"]["scripts/reference_rescore.py"] = runner.digest(script)
    updated["supersedes_registration"] = {"path": str(archive.relative_to(root)), "sha256": runner.digest(archive)}
    runner.write_json(runner.PLAN / "manifest.json", updated)
    actual_open = Path.open

    def never_rewrite_output(path, mode="r", *args, **kwargs):
        if path == destination and any(flag in mode for flag in "wax+"):
            raise AssertionError("the existing canary must never be opened for writing")
        return actual_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", never_rewrite_output)
    receipt = runner.recover_canary(updated, source)
    assert receipt["status"] == "passed" and receipt["preserved_existing_output"]
    assert receipt["model_calls_during_recovery"] == 0
    assert destination.read_bytes() == original_bytes["candidate.json"]
    assert {p.name: p.read_bytes() for p in source.iterdir()} == original_bytes
    assert (runner.PLAN / "canary_acceptance.json").read_bytes() == old_acceptance
    with pytest.raises(ValueError, match="canary acceptance"):
        runner.require_canary(updated, {**job, "id": "another-record"})
    runner.accept_canary(updated)
    runner.require_canary(updated, {**job, "id": "another-record"})


def test_revalidation_cannot_treat_ambiguous_current_receipts_as_a_new_amendment(retained_canary):
    root, manifest, job, source, _ = retained_canary
    receipt = runner.recover_canary(manifest, source)
    duplicate = runner.PLAN / "attempts" / job["id"] / "duplicate/receipt.json"
    runner.write_json(duplicate, receipt)
    before = sorted((runner.PLAN / "attempts" / job["id"]).glob("*/receipt.json"))
    with pytest.raises(ValueError, match="already exists"):
        runner.recover_canary(manifest, source)
    assert sorted((runner.PLAN / "attempts" / job["id"]).glob("*/receipt.json")) == before


@pytest.mark.parametrize("entrypoint", [runner.recover_canary, runner.recover_rating])
def test_missing_output_does_not_allow_duplicate_current_registration_receipts(retained_canary, entrypoint):
    root, manifest, job, source, _ = retained_canary
    runner.recover_canary(manifest, source)
    receipts = {p: p.read_bytes() for p in (runner.PLAN / "attempts" / job["id"]).glob("*/receipt.json")}
    (root / job["output"]).unlink()
    with pytest.raises(ValueError, match="already exists"):
        entrypoint(manifest, source)
    assert not (root / job["output"]).exists()
    assert {p: p.read_bytes() for p in (runner.PLAN / "attempts" / job["id"]).glob("*/receipt.json")} == receipts


def test_overlapping_recovery_and_acceptance_cannot_publish_ambiguous_receipts(retained_canary, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    root, manifest, job, source, original_bytes = retained_canary
    runner.recover_canary(manifest, source)
    runner.accept_canary(manifest)
    archive = runner.PLAN / "registrations/before-overlapping-recovery.json"
    shutil.copyfile(runner.PLAN / "manifest.json", archive)
    updated = copy.deepcopy(manifest)
    script = root / "scripts/reference_rescore.py"
    script.write_bytes(script.read_bytes() + b"\n# Next runner-only amendment.\n")
    updated["pinned_files"]["scripts/reference_rescore.py"] = runner.digest(script)
    updated["supersedes_registration"] = {"path": str(archive.relative_to(root)), "sha256": runner.digest(archive)}
    runner.write_json(runner.PLAN / "manifest.json", updated)
    entered, release = Event(), Event()
    actual_validate = runner.validate_candidate

    def pause_inside_recovery(*args):
        entered.set()
        assert release.wait(timeout=10), "test did not release recovery"
        return actual_validate(*args)

    with monkeypatch.context() as context, ThreadPoolExecutor(max_workers=1) as pool:
        context.setattr(runner, "validate_candidate", pause_inside_recovery)
        pending = pool.submit(runner.recover_canary, updated, source)
        try:
            assert entered.wait(timeout=5), "recovery did not reach validation"
            for operation in (
                lambda: runner.recover_canary(updated, source),
                lambda: runner.accept_canary(updated),
                lambda: runner.require_canary(updated, {**job, "id": "another-record"}),
                lambda: runner.run_job(updated, job, "must-not-start"),
            ):
                with pytest.raises(ValueError, match="canary operation is in progress"):
                    operation()
        finally:
            release.set()
        receipt = pending.result(timeout=5)
    assert runner.successful_receipt(updated, job) == receipt
    assert (root / job["output"]).read_bytes() == original_bytes["candidate.json"]
    runner.accept_canary(updated)
    runner.require_canary(updated, {**job, "id": "another-record"})


def test_fill_rechecks_receipt_uniqueness_after_canary_acceptance(retained_canary):
    _, manifest, job, source, _ = retained_canary
    receipt = runner.recover_canary(manifest, source)
    runner.accept_canary(manifest)
    runner.write_json(runner.PLAN / "attempts" / job["id"] / "duplicate/receipt.json", receipt)
    with pytest.raises(ValueError, match="no unique successful receipt"):
        runner.require_canary(manifest, {**job, "id": "another-record"})


@pytest.mark.parametrize("defect", ["budget", "instrument", "archive", "registration", "prompt", "validator", "model", "candidate"])
def test_recovery_rejects_changed_contract_or_unattested_candidate(retained_canary, defect):
    root, manifest, job, source, _ = retained_canary
    if defect == "budget":
        manifest["budget_cap_usd_per_attempt"] = 6
    elif defect == "instrument":
        manifest["instruments"][job["rubric"]]["definition_sha256"] = "0" * 64
    elif defect == "archive":
        (root / manifest["supersedes_registration"]["path"]).write_text("{}")
    elif defect == "registration":
        receipt = json.loads((source / "receipt.json").read_bytes())
        receipt["manifest_sha256"] = "0" * 64
        runner.write_json(source / "receipt.json", receipt)
    elif defect == "prompt":
        (source / "prompt.txt").write_text("different prompt")
    elif defect in ("validator", "model"):
        path = source / "transcript.jsonl"
        trace = [json.loads(line) for line in path.read_text().splitlines()]
        if defect == "validator":
            trace = [e for e in trace if e["type"] != "user"]
        else:
            next(e for e in trace if e["type"] == "assistant")["message"]["model"] = "another-model"
        path.write_text("\n".join(json.dumps(e) for e in trace) + "\n")
    else:
        path = source / "candidate.json"
        doc = json.loads(path.read_bytes())
        doc["overall_score"]["total_points"] -= 1
        runner.write_json(path, doc)
    runner.write_json(runner.PLAN / "manifest.json", manifest)
    with pytest.raises(ValueError):
        runner.recover_canary(manifest, source)
    assert not (root / job["output"]).exists()
    assert not (runner.PLAN / "canary_acceptance.json").exists()


def test_recovery_rejects_candidate_changed_after_validation(retained_canary, monkeypatch):
    root, manifest, job, source, _ = retained_canary
    actual_run = runner.subprocess.run

    def mutate_after_validation(*args, **kwargs):
        completed = actual_run(*args, **kwargs)
        path = source / "candidate.json"
        path.write_bytes(path.read_bytes() + b"\n")
        return completed

    monkeypatch.setattr(runner.subprocess, "run", mutate_after_validation)
    with pytest.raises(ValueError, match="changed during recovery"):
        runner.recover_canary(manifest, source)
    assert not (root / job["output"]).exists()


def test_recovery_rejects_valid_json_changed_since_the_evaluator_wrote_it(retained_canary):
    root, manifest, job, source, _ = retained_canary
    path = source / "candidate.json"
    doc = json.loads(path.read_bytes())
    doc["elements"][0]["sub_elements"][0]["quality_note"] = "Assessment changed after the evaluator completed."
    runner.write_json(path, doc)
    with pytest.raises(ValueError, match="evaluator.*Write"):
        runner.recover_canary(manifest, source)
    assert not (root / job["output"]).exists()


def test_recovery_rejects_the_last_write_when_only_an_earlier_version_was_validated(retained_canary):
    root, manifest, job, source, _ = retained_canary
    path = source / "candidate.json"
    doc = json.loads(path.read_bytes())
    doc["elements"][0]["sub_elements"][0]["quality_note"] = "Revised after validation."
    runner.write_json(path, doc)
    trace_path = source / "transcript.jsonl"
    trace = [json.loads(line) for line in trace_path.read_text().splitlines()]
    later = copy.deepcopy(trace[1:3])
    later[0]["message"]["content"][0]["id"] = "revised-output"
    later[0]["message"]["content"][0]["input"]["content"] = path.read_text()
    later[1]["message"]["content"][0]["tool_use_id"] = "revised-output"
    trace = trace[:-1] + later + trace[-1:]
    trace_path.write_text("\n".join(json.dumps(e) for e in trace) + "\n")
    with pytest.raises(ValueError, match="did not successfully validate"):
        runner.recover_canary(manifest, source)
    assert not (root / job["output"]).exists()


@pytest.mark.parametrize("defect", ["missing", "failed", "unrelated", "sibling", "later_write", "cwd"])
def test_recovery_requires_the_last_successful_output_write(retained_canary, defect):
    root, manifest, job, source, _ = retained_canary
    path = source / "transcript.jsonl"
    trace = [json.loads(line) for line in path.read_text().splitlines()]
    if defect == "missing":
        trace = trace[:1] + trace[3:]
    elif defect == "failed":
        trace[2]["message"]["content"][0]["is_error"] = True
    elif defect == "unrelated":
        trace[1]["message"]["content"][0]["input"]["file_path"] = "/isolated/another.json"
    elif defect == "sibling":
        trace[1]["message"]["content"][0]["input"]["file_path"] = "/isolated/nested/output_evaluation.json"
    elif defect == "cwd":
        trace[0]["cwd"] = "/another-run"
    else:
        later = copy.deepcopy(trace[1:3])
        later[0]["message"]["content"][0]["id"] = "later-write"
        later[0]["message"]["content"][0]["input"]["content"] = "{}"
        later[1]["message"]["content"][0]["tool_use_id"] = "later-write"
        trace.extend(later)
    path.write_text("\n".join(json.dumps(e) for e in trace) + "\n")
    with pytest.raises(ValueError, match="evaluator.*Write"):
        runner.recover_canary(manifest, source)
    assert not (root / job["output"]).exists()


def test_failed_attempt_cannot_unlock_fill_or_create_a_live_rating(environment):
    root, manifest, job, doc = environment
    cli = fake_cli(root / "fake-claude", doc, [], failure=True)
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "incomplete"
    assert not (root / job["output"]).exists()
    assert list(runner.PLAN.glob("attempts/*/*/receipt.json"))
    assert "Weekly quota" in next(runner.PLAN.glob("attempts/*/*/transcript.jsonl")).read_text()
    with pytest.raises(ValueError, match="successful receipt"):
        runner.accept_canary(manifest)


@pytest.mark.parametrize("part", ["input", "definition", "prior"])
def test_frozen_byte_changes_stop_before_the_cli(environment, part):
    root, manifest, job, doc = environment
    path = {"input": job["input"], "definition": manifest["instruments"][job["rubric"]]["definition"],
            "prior": "prior_evaluation.json"}[part]
    (root / path).write_text("changed")
    with pytest.raises(ValueError, match="frozen bytes"):
        runner.run_job(manifest, job, "this-command-must-not-run")


@pytest.mark.parametrize("defect", ["model", "instrument", "echo", "validator", "input", "temperature", "kind", "rubric"])
def test_unattested_or_misidentified_candidate_is_retained_but_not_published(environment, defect):
    root, manifest, job, doc = environment
    trace = events(doc)
    if defect == "model":
        trace[0]["message"]["model"] = "another-model"
    elif defect == "instrument":
        doc["metadata"]["instrument_sha256"] = "0" * 64
    elif defect == "echo":
        trace[0]["message"]["content"][0]["text"] = "old definition"
    elif defect == "validator":
        trace = events(doc, validator_success=False)
    elif defect == "input":
        doc["metadata"]["input_sha256"] = "0" * 64
    elif defect == "kind":
        doc["metadata"]["instrument_kind"] = "api_system_prompt"
    elif defect == "rubric":
        doc["metadata"]["rubric_hash"] = "0" * 64
    else:
        doc["model"]["temperature"] = 0.0
    cli = fake_cli(root / "fake-claude", doc, trace)
    receipt = runner.run_job(manifest, job, cli)
    assert receipt["status"] == "incomplete"
    assert not (root / job["output"]).exists()
    assert list(runner.PLAN.glob("attempts/*/*/candidate.json"))


def test_existing_output_without_receipt_or_with_changed_bytes_cannot_resume(environment):
    root, manifest, job, doc = environment
    dest = root / job["output"]
    dest.parent.mkdir(parents=True)
    dest.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="successful receipt"):
        runner.successful_receipt(manifest, job)

    runner.write_json(runner.PLAN / "attempts" / job["id"] / "one/receipt.json", {
        "status": "passed", "evaluation_sha256": runner.digest(dest),
        "manifest_sha256": runner.digest(runner.PLAN / "manifest.json")})
    dest.write_text(dest.read_text() + "\n")
    with pytest.raises(ValueError, match="successful receipt"):
        runner.successful_receipt(manifest, job)


def test_repeatability_report_separates_repeated_ratings_from_generation_records(environment, monkeypatch):
    root, manifest, job, doc = environment
    monkeypatch.syspath_prepend(str(REAL_ROOT / "scripts"))
    jobs = []
    for rating in (1, 2, 3):
        j = {**job, "id": f"rating{rating}", "rating": rating,
             "purpose": "primary" if rating == 1 else "repeatability", "output": f"rating{rating}.json"}
        jobs.append(j)
    manifest["jobs"] = jobs
    runner.write_json(runner.PLAN / "manifest.json", manifest)
    for index, j in enumerate(jobs):
        d = copy.deepcopy(doc)
        # Score rows are independently attested by their receipts; this
        # fixture isolates aggregation of a known two-point spacing.
        d["overall_score"]["total_points"] = 40 + index
        d["overall_score"]["fixed_percentage"] = 80 + 2 * index
        d["overall_score"]["normalized_percentage"] = round(100 * (40 + index) / 48, 1)
        runner.write_json(root / j["output"], d)
        runner.write_json(runner.PLAN / "attempts" / j["id"] / "one/receipt.json", {
            "status": "passed", "evaluation_sha256": runner.digest(root / j["output"]),
            "manifest_sha256": runner.digest(runner.PLAN / "manifest.json")})
    results = runner.report_results(manifest)
    chorus = next(r for r in results["repeatability"] if r["project"] == "CHORUS")
    assert chorus["fixed_sample_sd"] == 2
    assert chorus["fixed_range"] == 4
    primary = next(r for r in results["generation_replicates"] if r["project"] == "CHORUS"
                   and r["cohort"] == "v7" and r["rubric"] == "rubric10-semantic")
    assert primary["records"] == 1
    ai_readi = next(r for r in results["repeatability"] if r["project"] == "AI_READI")
    assert ai_readi["fixed_sample_sd"] is None
