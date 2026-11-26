"""Offline repeat placement controls, 2026-11-26.

Synthetic records and committed executable stand-ins exercise the unchanged
scorer, exact validator and exclusive export. Existing evaluation stores are
read through their real APIs in an isolated tree; no provider is called.
"""
from argparse import Namespace
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest

from data_sheets_schema.evaluation import validate
from tests.test_codex_root_scope_scorer import INSTRUMENT, root_scenario, scorer


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/adhoc/repeat_root_scope_scoring_20261126.py"
RUNNER = ROOT / "scripts/adhoc/score_semantic_rubric_codex_20261125.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    previous_cwd, previous_path = Path.cwd(), sys.path[:]
    try:
        with patch.dict(sys.modules, {name: module}):
            spec.loader.exec_module(module)
    finally:
        os.chdir(previous_cwd)
        sys.path[:] = previous_path
    return module


def repeat_helper():
    return load_module(HELPER, "root_scope_repeat_controls")


def batch(helper, jobs, accepted=None):
    return {"jobs": jobs, "orchestration": helper._orchestration(), "accepted_canary_job": accepted}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def synthetic_run(directory, rubric="rubric10", shared=None, project="Toy", **changes):
    args, tree, tools, evaluation = root_scenario(directory, rubric, **changes)
    if project != "Toy":
        renamed = Path(args.record).with_name(project + "_d4d.yaml")
        Path(args.record).rename(renamed)
        args.record = renamed
        evaluation.update(project=project, d4d_file=str(renamed.relative_to(tree)))
        case_path = tools / "case.json"
        case = json.loads(case_path.read_bytes())
        case["evaluation"] = evaluation
        case_path.write_text(json.dumps(case) + "\n")
    scope = tree / "data/evaluation_scope" / args.label / (project + ".scope.json")
    scope.parent.mkdir(parents=True)
    shutil.copyfile(args.scope_context, scope)
    args.scope_context = scope
    if shared is not None:
        args.codex_binary = shared[0].codex_binary
        args.poetry_binary = shared[0].poetry_binary
        args.auth_file = shared[0].auth_file
        tools = shared[2]
    runner = tree / "scripts/adhoc" / RUNNER.name
    runner.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RUNNER, runner)
    pinned = repeat_helper()._load_scorer(tree)
    return args, tree, tools, evaluation, pinned.build_plan(args)


def export_fixture(directory, rubric="rubric10", execute_repeat=True, project="Toy"):
    baseline = synthetic_run(directory / "baseline", rubric, project=project)
    repeated = synthetic_run(directory / "repeat", rubric, shared=baseline, project=project)
    for args, _, _, _, plan in ((baseline, repeated) if execute_repeat else (baseline,)):
        scorer.execute(plan, args)
    publication = directory / "publication"
    publication.mkdir()
    runs = directory / "repeat-controller"
    runs.mkdir()
    baseline_run = Path(baseline[4]["run_directory"])
    baseline_plan = baseline_run / "plan.json"
    baseline_receipt = baseline_run / "receipt.json"
    plan = repeated[4]
    destination = (publication / "data/evaluation_repeats" / INSTRUMENT /
                   "scoring_rep2" / (rubric + "_semantic") / Path(plan["output"]).name)
    job_id = "scoring-rep2-generation-rep1-" + project + "-" + rubric
    export_directory = runs / "export-manifests" / job_id
    scorer_argv = []
    for name in ("repo_root", "method_directory", "label", "record", "rubric", "run_directory",
                 "codex_binary", "poetry_binary", "validation_venv", "auth_file", "timeout",
                 "semantic_version", "scope_context"):
        scorer_argv.extend(["--" + name.replace("_", "-"), str(getattr(repeated[0], name))])
    job = {
        "id": job_id, "scoring_replicate": 2, "generation_replicate": 1,
        "plan": plan, "baseline_plan_path": str(baseline_plan),
        "baseline_receipt_path": str(baseline_receipt),
        "baseline_plan_sha256": sha(baseline_plan.read_bytes()),
        "baseline_receipt_sha256": sha(baseline_receipt.read_bytes()),
        "destination": str(destination), "export_directory": str(export_directory),
        "manifest_path": str(export_directory / "manifest.json"), "skip": False,
        "scorer_argv": scorer_argv,
    }
    return baseline, repeated, job, Namespace(publication_root=publication, runs_root=runs)


def test_distinct_checkouts_preserve_complete_prompt_and_all_input_hashes(tmp_path):
    helper = repeat_helper()
    for rubric in ("rubric10", "rubric20"):
        first = synthetic_run(tmp_path / rubric / "run1", rubric)
        second = synthetic_run(tmp_path / rubric / "run2", rubric, shared=first)
        left, right = first[4], second[4]
        assert left["repo_root"] != right["repo_root"]
        assert left["output"] != right["output"]
        assert left["run_directory"] != right["run_directory"]
        assert left["prompt"].encode() == right["prompt"].encode()
        assert left["runner_sha256"] == right["runner_sha256"]
        assert left["identity"] == right["identity"]
        assert left["deterministic_fields"] == right["deterministic_fields"]
        assert left["definition_provenance"] == right["definition_provenance"]
        assert {key: value["sha256"] for key, value in left["inputs"].items()} == {
            key: value["sha256"] for key, value in right["inputs"].items()}
        helper.verify_plan_identity(right, left)
        for key, replacement in (("prompt", right["prompt"] + "\n"),
                                 ("runner_sha256", "0" * 64)):
            forged = copy.deepcopy(right)
            forged[key] = replacement
            with pytest.raises((ValueError, RuntimeError)):
                helper.verify_plan_identity(forged, left)
        assert not Path(left["run_directory"]).exists()
        assert not Path(right["run_directory"]).exists()


def test_fake_repeat_exports_exact_validated_bytes_and_retains_both_runs(tmp_path, monkeypatch):
    helper = repeat_helper()
    monkeypatch.setattr(helper, "_checkout", lambda root: None)
    for rubric in ("rubric10", "rubric20"):
        baseline, repeated, job, args = export_fixture(tmp_path / rubric, rubric)
        first_output = Path(baseline[4]["output"])
        first_bytes = first_output.read_bytes()
        source = Path(repeated[4]["output"])
        source_bytes = source.read_bytes()
        source_receipt = Path(repeated[4]["run_directory"]) / "receipt.json"
        receipt_bytes = source_receipt.read_bytes()
        auth_bytes = repeated[0].auth_file.read_bytes()
        input_bytes = Path(repeated[0].record).read_bytes()
        original_publication = (args.publication_root / "data/evaluation_llm" /
                                (rubric + "_semantic") / "label_aware" /
                                INSTRUMENT / first_output.name)
        original_publication.parent.mkdir(parents=True)
        original_publication.write_bytes(first_bytes)
        helper.export_job(job, args)
        target = Path(job["destination"])
        assert target.relative_to(args.publication_root).parts[:4] == (
            "data", "evaluation_repeats", INSTRUMENT, "scoring_rep2")
        assert target.read_bytes() == source_bytes
        assert source_bytes == (repeated[2] / "validated-snapshot.json").read_bytes()
        assert source.read_bytes() == source_bytes
        assert source_receipt.read_bytes() == receipt_bytes
        assert first_output.read_bytes() == first_bytes
        assert original_publication.read_bytes() == first_bytes
        assert repeated[0].auth_file.read_bytes() == auth_bytes
        assert Path(repeated[0].record).read_bytes() == input_bytes
        assert not (Path(repeated[4]["codex_home"]) / "auth.json").exists()
        assert Path(job["manifest_path"]).is_file()
        assert Path(job["manifest_path"]).stat().st_size > 0
        assert validate.validate_outputs(
            [target], rubric=rubric + "-semantic",
            schema_dir=repeated[1] / "src/download/prompts",
            input_path=Path(repeated[0].record),
            definition_path=Path(repeated[4]["working_directory"]) / "agent-definition.md",
            semantic_version="6.0", scope_context_path=repeated[0].scope_context,
        ) == 0
        with pytest.raises((ValueError, RuntimeError, FileExistsError)):
            helper.export_job(job, args)
        assert target.read_bytes() == source_bytes
        assert first_output.read_bytes() == first_bytes
        assert original_publication.read_bytes() == first_bytes


def test_repeat_export_collision_preserves_existing_destination(tmp_path, monkeypatch):
    helper = repeat_helper()
    monkeypatch.setattr(helper, "_checkout", lambda root: None)
    baseline, repeated, job, args = export_fixture(tmp_path)
    target = Path(job["destination"])
    target.parent.mkdir(parents=True)
    target.write_bytes(b"an earlier scoring result must stay untouched\n")
    before = {path: path.read_bytes() for path in (
        target, Path(baseline[4]["output"]), Path(repeated[4]["output"]))}
    with pytest.raises((ValueError, RuntimeError, FileExistsError)):
        helper.export_job(job, args)
    assert {path: path.read_bytes() for path in before} == before


def test_repeat_controller_executes_pinned_main_and_skips_only_verified_canary(tmp_path, monkeypatch):
    helper = repeat_helper()
    monkeypatch.setattr(helper, "_checkout", lambda root: None)
    baseline, repeated, job, args = export_fixture(tmp_path, execute_repeat=False, project="CM4AI")
    args.authorization_reference = "offline executable stand-in only"
    args.generation_replicate = 1
    args.accepted_canary = None
    before_baseline = Path(baseline[4]["output"]).read_bytes()
    original_auth = repeated[0].auth_file.read_bytes()
    assert not Path(repeated[4]["run_directory"]).exists()
    result = helper.execute_batch(batch(helper, [job]), args)
    assert result["status"] == "SELECTED_REPEAT_JOBS_COMPLETE"
    assert result["job_count"] == 1
    target = Path(job["destination"])
    assert target.is_file() and target.stat().st_size > 0
    assert target.read_bytes() == Path(repeated[4]["output"]).read_bytes()
    assert target.read_bytes() == (repeated[2] / "validated-snapshot.json").read_bytes()
    manifest = json.loads(Path(job["manifest_path"]).read_bytes())
    assert manifest["status"] == "EXPORTED_VALIDATED_REPEAT"
    assert manifest["source_head"] == helper.SCORER_HEAD
    assert manifest["destination_sha256"] == sha(target.read_bytes())
    assert manifest["source_output_sha256"] == manifest["destination_sha256"]
    assert manifest["prompt_equals_run1"] is True
    assert manifest["copy_validator_exit"] == 0
    assert Path(baseline[4]["output"]).read_bytes() == before_baseline
    assert repeated[0].auth_file.read_bytes() == original_auth
    assert not (Path(repeated[4]["codex_home"]) / "auth.json").exists()

    job["skip"] = True
    args.accepted_canary = Path(job["manifest_path"])
    invocation = repeated[2] / "invocation.json"
    before_invocation = invocation.stat().st_mtime_ns, invocation.read_bytes()
    skipped = helper.execute_batch(batch(helper, [job], accepted=job), args)
    assert skipped["results"] == [{"id": job["id"], "status": "VERIFIED_CANARY_ALREADY_EXPORTED"}]
    assert (invocation.stat().st_mtime_ns, invocation.read_bytes()) == before_invocation
    forged = copy.deepcopy(manifest)
    forged["destination_sha256"] = "0" * 64
    Path(job["manifest_path"]).write_text(json.dumps(forged) + "\n")
    with pytest.raises(ValueError, match="manifest differs"):
        helper.execute_batch(batch(helper, [job], accepted=job), args)
    assert (invocation.stat().st_mtime_ns, invocation.read_bytes()) == before_invocation
    assert target.read_bytes() == Path(repeated[4]["output"]).read_bytes()


def test_repeat_controller_stops_a_failed_fake_run_without_export(tmp_path, monkeypatch):
    helper = repeat_helper()
    monkeypatch.setattr(helper, "_checkout", lambda root: None)
    baseline, repeated, job, args = export_fixture(tmp_path, execute_repeat=False, project="CM4AI")
    args.authorization_reference = "offline executable stand-in only"
    args.generation_replicate = 1
    args.accepted_canary = None
    before_baseline = Path(baseline[4]["output"]).read_bytes()
    before_auth = repeated[0].auth_file.read_bytes()
    case_path = repeated[2] / "case.json"
    case = json.loads(case_path.read_bytes())
    case["exit"] = 7
    case_path.write_text(json.dumps(case) + "\n")
    with pytest.raises(ValueError, match="scorer failed"):
        helper.execute_batch(batch(helper, [job]), args)
    receipt = json.loads((Path(repeated[4]["run_directory"]) / "receipt.json").read_bytes())
    assert receipt["status"] == "REFUSED"
    assert receipt["codex_exit"] == 7
    assert receipt["auth_copy_absent"] is True
    assert not Path(repeated[4]["output"]).exists()
    assert not Path(job["destination"]).exists()
    assert not Path(job["manifest_path"]).exists()
    assert not (Path(repeated[4]["codex_home"]) / "auth.json").exists()
    assert repeated[0].auth_file.read_bytes() == before_auth
    assert Path(baseline[4]["output"]).read_bytes() == before_baseline


def test_repeat_controller_bounds_stream_size_before_a_launch(tmp_path, monkeypatch):
    helper = repeat_helper()
    args = Namespace(authorization_reference="offline control", generation_replicate=1,
                     runs_root=tmp_path / "runs", accepted_canary=None)
    job = {"scoring_replicate": 2, "generation_replicate": 1,
           "plan": {"repo_root": str(tmp_path),
                    "identity": {"project": "CM4AI", "rubric": "rubric10-semantic"}}}

    class ReachedCheckout(Exception):
        pass

    visited = []

    def stop_before_launch(root):
        visited.append(root)
        raise ReachedCheckout

    monkeypatch.setattr(helper, "_checkout", stop_before_launch)
    for count in (0, 2, 19, 21, 60):
        with pytest.raises(ValueError, match="twenty-job"):
            helper.execute_batch(batch(helper, [job] * count), args)
        assert not visited
    with pytest.raises(ReachedCheckout):
        helper.execute_batch(batch(helper, [job]), args)
    assert len(visited) == 1
    visited.clear()
    with pytest.raises(ValueError, match="requires the accepted repeat canary"):
        helper.execute_batch(batch(helper, [job] * 20), args)
    assert not visited
    other = copy.deepcopy(job)
    other["plan"]["identity"]["project"] = "CHORUS"
    with pytest.raises(ValueError, match="requires the accepted repeat canary"):
        helper.execute_batch(batch(helper, [other]), args)
    assert not visited
    args.generation_replicate = None
    with pytest.raises(ValueError, match="twenty-job"):
        helper.execute_batch(batch(helper, [job] * 20), args)
    assert not visited


def test_repeat_export_refuses_changed_evidence_without_publishing(tmp_path, monkeypatch):
    helper = repeat_helper()
    monkeypatch.setattr(helper, "_checkout", lambda root: None)
    baseline, repeated, original_job, args = export_fixture(tmp_path)
    first = Path(baseline[4]["output"])
    first_bytes = first.read_bytes()
    source = Path(repeated[4]["output"])
    receipt = Path(repeated[4]["run_directory"]) / "receipt.json"
    candidate = Path(repeated[4]["run_directory"]) / "candidate_evaluation.json"
    cases = (
        (Path(original_job["baseline_receipt_path"]), b"\n"),
        (source, b"\n"),
        (candidate, b"\n"),
        (receipt, None),
    )
    for index, (path, suffix) in enumerate(cases):
        job = copy.deepcopy(original_job)
        export_dir = args.runs_root / "export-manifests" / ("refusal-" + str(index))
        job.update(id="refusal-" + str(index), export_directory=str(export_dir),
                   manifest_path=str(export_dir / "manifest.json"))
        before = path.read_bytes()
        if suffix is None:
            changed = json.loads(before)
            changed["status"] = "REFUSED"
            path.write_text(json.dumps(changed) + "\n")
        else:
            path.write_bytes(before + suffix)
        try:
            with pytest.raises((ValueError, RuntimeError, OSError)):
                helper.export_job(job, args)
            assert not Path(job["destination"]).exists()
            assert first.read_bytes() == first_bytes
        finally:
            path.write_bytes(before)


def test_repeat_checkout_refuses_a_different_head(tmp_path):
    helper = repeat_helper()
    wrong = subprocess.CompletedProcess([], 0, stdout="0" * 40 + "\n", stderr="")
    with patch.object(helper.subprocess, "run", return_value=wrong):
        with pytest.raises((ValueError, RuntimeError)):
            helper._checkout(tmp_path)


def test_repeat_location_leaves_real_reader_results_and_corpus_exit_unchanged(tmp_path, monkeypatch):
    args, tree, tools, _, plan = synthetic_run(tmp_path / "canary")
    scorer.execute(plan, args)
    raw = Path(plan["output"]).read_bytes()
    document = json.loads(raw)
    publication = tmp_path / "publication"
    family = "rubric10_semantic"
    live_dir = publication / "data/evaluation_llm" / family / "label_aware"
    live_dir.mkdir(parents=True)
    direct = live_dir / Path(plan["output"]).name
    direct.write_bytes(raw)
    run1 = live_dir / INSTRUMENT / Path(plan["output"]).name
    run1.parent.mkdir()
    run1.write_bytes(raw)
    base = publication / "data/evaluation_llm"
    arm = load_module(ROOT / "scripts/arm_comparison.py", "repeat_arm_reader")
    manifest = load_module(ROOT / "scripts/evaluation_manifest.py", "repeat_manifest_reader")
    audit = load_module(ROOT / "scripts/audit_evaluation_comparability.py", "repeat_audit_reader")
    monkeypatch.setattr(arm, "EVAL_DIRS", {"rubric10": live_dir})
    monkeypatch.setattr(arm, "CONCAT", publication / "data/d4d_concatenated")
    monkeypatch.setattr(manifest, "ROOT", publication)
    monkeypatch.chdir(publication)

    def readers():
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = validate.main(eval_base=base, schema_dir=tree / "src/download/prompts")
        # This is the same nonrecursive selection used by review.disposition
        # to annotate evaluations predating an amendment.
        label, project = document["label"], document["project"]
        predating = sorted(str(path) for path in Path("data/evaluation_llm").glob(
            f"*/label_aware/{project}_*{label.rsplit('_', 1)[-1]}_evaluation.json")
            if label.split("_")[0] in path.read_text()[:4000])
        return {
            "discovered": validate.discover(base), "corpus_exit": code,
            "corpus_report": output.getvalue(),
            "arm": arm.rubric_scores([label], project),
            "manifest": manifest.live_and_archived(),
            "audit": audit.evaluations(publication), "predating": predating,
        }

    before = readers()
    assert len(before["discovered"]) == 2
    assert before["corpus_exit"] == 0
    assert len(before["arm"]) == 1
    assert len(before["manifest"][0]) == 1
    assert len(before["audit"][0]) == 1
    assert len(before["predating"]) == 1
    for number in (2, 3):
        target = (publication / "data/evaluation_repeats" / INSTRUMENT /
                  ("scoring_rep" + str(number)) / family / direct.name)
        target.parent.mkdir(parents=True)
        target.write_bytes(raw)
        assert target.read_bytes() == raw
    assert readers() == before
    assert run1.read_bytes() == raw and direct.read_bytes() == raw
    assert not (Path(plan["codex_home"]) / "auth.json").exists()
