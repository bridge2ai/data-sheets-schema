"""Offline repeat placement controls, 2026-11-26.

Synthetic records and committed executable stand-ins exercise the unchanged
scorer, exact validator and exclusive export. Existing evaluation stores are
read through their real APIs in an isolated tree; no provider is called.
"""
from argparse import Namespace
import contextlib
import copy
import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from unittest.mock import patch

import pytest

from data_sheets_schema.evaluation import validate
from tests.test_codex_root_scope_scorer import INSTRUMENT, root_scenario


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/adhoc/repeat_root_scope_scoring_20261126.py"


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


def measured_runner_bytes(helper):
    """Historical repeat controls keep the runner pinned by their controller.

    Read the retained Git object, never a measured checkout. Missing history or
    a digest mismatch fails the fixture; it cannot select the current revision.
    """
    raw = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{helper.SCORER_HEAD}:{helper.RUNNER}"],
        check=True, capture_output=True, timeout=30,
    ).stdout
    assert sha(raw) == helper.RUNNER_SHA, "measured fixture runner blob differs from its pin"
    return raw


def execute_measured_fixture(plan, args):
    helper = repeat_helper()
    tree = Path(plan["repo_root"])
    pinned = helper._load_scorer(tree)
    return helper.in_checkout(tree, pinned.execute, plan, args)


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
    helper = repeat_helper()
    runner = tree / helper.RUNNER
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_bytes(measured_runner_bytes(helper))
    pinned = helper._load_scorer(tree)
    return args, tree, tools, evaluation, helper.in_checkout(tree, pinned.build_plan, args)


def export_fixture(directory, rubric="rubric10", execute_repeat=True, project="Toy"):
    baseline = synthetic_run(directory / "baseline", rubric, project=project)
    repeated = synthetic_run(directory / "repeat", rubric, shared=baseline, project=project)
    for args, _, _, _, plan in ((baseline, repeated) if execute_repeat else (baseline,)):
        execute_measured_fixture(plan, args)
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
    from tests.test_codex_root_scope_scorer import scorer as current_scorer
    helper = repeat_helper()
    monkeypatch.setattr(helper, "_checkout", lambda root: None)
    for rubric in ("rubric10", "rubric20"):
        with patch.object(current_scorer, "execute",
                          side_effect=AssertionError("historical fixture executed the current runner")):
            baseline, repeated, job, args = export_fixture(tmp_path / rubric, rubric)
        assert baseline[4]["runner_sha256"] == repeated[4]["runner_sha256"] == helper.RUNNER_SHA
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


def test_measured_fixture_refuses_a_changed_git_blob():
    helper = repeat_helper()
    raw = measured_runner_bytes(helper)
    changed = subprocess.CompletedProcess([], 0, stdout=raw + b"\n", stderr=b"")
    with patch.object(subprocess, "run", return_value=changed):
        with pytest.raises(AssertionError, match="measured fixture runner blob differs"):
            measured_runner_bytes(helper)


def test_measured_loader_refuses_changed_fixture_runner_bytes(tmp_path):
    helper = repeat_helper()
    runner = tmp_path / helper.RUNNER
    runner.parent.mkdir(parents=True)
    runner.write_bytes(measured_runner_bytes(helper) + b"\n")
    with pytest.raises(ValueError, match="pinned scorer runner differs"):
        helper._load_scorer(tmp_path)


def test_repeat_location_leaves_real_reader_results_and_corpus_exit_unchanged(tmp_path, monkeypatch):
    args, tree, tools, _, plan = synthetic_run(tmp_path / "canary")
    execute_measured_fixture(plan, args)
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


def export_failure_stream(directory):
    """Reuse the review's accepted canary plus twenty-row fake stream control."""
    helper = repeat_helper()
    helper._checkout = lambda root: None
    _, _, accepted, accepted_args = export_fixture(directory / "accepted", project="CM4AI")
    helper.export_job(accepted, accepted_args)
    accepted["skip"] = True
    baseline, repeated, job, args = export_fixture(directory / "stream", execute_repeat=False, project="CM4AI")
    args.authorization_reference = "offline issue 6378 executable stand-in only"
    args.generation_replicate = 1
    args.accepted_canary = Path(accepted["manifest_path"])
    calls = directory / "main-invocations.json"
    calls.write_text("[]\n")
    loaded = helper._load_scorer

    def counted_loader(root):
        module = loaded(root)
        original_main = module.main

        def counted_main(argv):
            rows = json.loads(calls.read_bytes())
            rows.append(list(argv))
            calls.write_text(json.dumps(rows) + "\n")
            return original_main(argv)

        module.main = counted_main
        return module

    helper._load_scorer = counted_loader
    before = {"baseline": Path(baseline[4]["output"]).read_bytes(),
              "auth": repeated[0].auth_file.read_bytes()}

    def execute():
        return helper.execute_batch(batch(helper, [job] * 20, accepted=accepted), args)

    return helper, baseline, repeated, job, args, calls, before, execute


def assert_refused_export(fixture, existing_destination=None):
    helper, baseline, repeated, job, args, calls, before, _ = fixture
    destination = Path(job["destination"])
    export = Path(job["export_directory"])
    staged = export / "staged-evaluation.json"
    if existing_destination is None:
        assert not destination.exists()
    else:
        assert destination.read_bytes() == existing_destination
    assert not Path(job["manifest_path"]).exists()
    failure = json.loads((export / "failure.json").read_bytes())
    assert failure["status"] == "EXPORT_REFUSED"
    assert failure["failure"]
    assert staged.is_file() and staged.stat().st_size > 0
    assert not staged.is_relative_to(args.publication_root / "data/evaluation_repeats")
    assert len(json.loads(calls.read_bytes())) == 1
    assert Path(baseline[4]["output"]).read_bytes() == before["baseline"]
    assert repeated[0].auth_file.read_bytes() == before["auth"]
    assert not (Path(repeated[4]["codex_home"]) / "auth.json").exists()
    receipt = json.loads((Path(repeated[4]["run_directory"]) / "receipt.json").read_bytes())
    assert receipt["status"] == "VALIDATED_AND_PUBLISHED"
    assert receipt["output_sha256"] == sha(Path(repeated[4]["output"]).read_bytes())
    return failure, staged


def export_command(command, job):
    return ("--file" in command and
            Path(command[command.index("--file") + 1]) ==
            Path(job["export_directory"]) / "staged-evaluation.json")


def test_repeat_export_faults_keep_only_private_evidence(tmp_path, failure_kind):
    """Issue 6378 review cases, now requiring absent public destinations."""
    fixture = export_failure_stream(tmp_path)
    helper, _, repeated, job, _, _, _, execute = fixture
    staged = Path(job["export_directory"]) / "staged-evaluation.json"
    destination = Path(job["destination"])
    original_open, original_popen, original_link = Path.open, subprocess.Popen, os.link
    original_stat = Path.stat
    validator_launches = []
    full_volume = [False]

    class PartialWrite:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *values):
            self.handle.close()

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def write(self, raw):
            self.handle.write(raw[:23])
            self.handle.flush()
            full_volume[0] = failure_kind == "enospc_global"
            raise OSError(errno.ENOSPC, "synthetic disk-full after 23 private staging bytes")

    def limited_open(path, mode="r", *positional, **keywords):
        if full_volume[0] and any(character in mode for character in "xwa+"):
            raise OSError(errno.ENOSPC, "synthetic full volume also prevents refusal enrichment")
        opened = original_open(path, mode, *positional, **keywords)
        if failure_kind in ("enospc", "enospc_global") and path == staged and mode == "xb":
            return PartialWrite(opened)
        return opened

    def different_device(path, *positional, **keywords):
        observed = original_stat(path, *positional, **keywords)
        if failure_kind == "different_filesystem" and path == destination.parent:
            values = list(observed)
            values[2] += 1
            return os.stat_result(values)
        return observed

    failed_validator = tmp_path / "exit17-validator.py"
    failed_validator.write_text("# Issue 6378 synthetic validator rejection.\nraise SystemExit(17)\n")

    def altered_popen(command, *positional, **keywords):
        if export_command(command, job):
            validator_launches.append(list(command))
            assert not destination.exists()
            if failure_kind == "strict_rejection":
                value = json.loads(staged.read_bytes())
                value["metadata"]["scope_context_sha256"] = "0" * 64
                staged.write_text(json.dumps(value) + "\n")
            elif failure_kind == "exit17":
                command = [sys.executable, str(failed_validator)]
        return original_popen(command, *positional, **keywords)

    def failed_link(source, target, *positional, **keywords):
        if Path(target) == destination:
            assert staged.is_file()
            assert len(validator_launches) == 1
            assert json.loads((repeated[2] / "real-validator-result.json").read_bytes())["returncode"] == 0
            if failure_kind == "before_publication":
                raise OSError(errno.EIO, "synthetic failure after validation before publication")
            if failure_kind == "after_publication":
                original_link(source, target, *positional, **keywords)
                raise OSError(errno.EIO, "synthetic failure after atomic publication syscall")
            if failure_kind == "changed_publication":
                original_link(source, target, *positional, **keywords)
                destination.chmod(0o600)
                destination.write_bytes(b"synthetic changed bytes after publication\n")
                return None
        return original_link(source, target, *positional, **keywords)

    dispositions = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    with patch.object(Path, "open", limited_open), patch.object(subprocess, "Popen", altered_popen), \
            patch.object(os, "link", failed_link), patch.object(Path, "stat", different_device):
        with pytest.raises((OSError, ValueError, RuntimeError)):
            execute()
    failure, retained = assert_refused_export(fixture)
    assert {number: signal.getsignal(number) for number in dispositions} == dispositions
    assert len(validator_launches) == (0 if failure_kind.startswith("enospc") else 1)
    if failure_kind.startswith("enospc"):
        assert retained.stat().st_size == 23
        if failure_kind == "enospc_global":
            # The initially persisted fallback is sufficient even when the
            # full volume prevents saving richer diagnostics after failure.
            assert failure["failure"] == "export has not completed"
        else:
            assert "23 private staging bytes" in failure["failure"]
    elif failure_kind == "strict_rejection":
        assert json.loads((repeated[2] / "real-validator-result.json").read_bytes())["returncode"] != 0


test_repeat_export_faults_keep_only_private_evidence = pytest.mark.parametrize(
    "failure_kind", ("enospc", "enospc_global", "strict_rejection", "exit17", "before_publication",
                     "after_publication", "changed_publication", "different_filesystem")
)(test_repeat_export_faults_keep_only_private_evidence)


def test_repeat_export_atomic_collision_preserves_the_other_publication(tmp_path):
    fixture = export_failure_stream(tmp_path)
    _, _, _, job, _, _, _, execute = fixture
    destination = Path(job["destination"])
    original_link = os.link
    existing = b"another writer won exclusive publication\n"

    def collide(source, target, *positional, **keywords):
        if Path(target) == destination:
            assert not destination.exists()
            destination.write_bytes(existing)
        return original_link(source, target, *positional, **keywords)

    with patch.object(os, "link", collide):
        with pytest.raises((OSError, ValueError, RuntimeError)):
            execute()
    assert_refused_export(fixture, existing_destination=existing)


def wait_control_file(path, controller, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        done, status = os.waitpid(controller, os.WNOHANG)
        if done:
            raise AssertionError(f"controller exited before signal point: {os.waitstatus_to_exitcode(status)}")
        time.sleep(0.02)
    raise AssertionError("controller did not reach its bounded signal point")


def wait_control_exit(controller, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        done, status = os.waitpid(controller, os.WNOHANG)
        if done:
            return os.waitstatus_to_exitcode(status)
        time.sleep(0.02)
    raise AssertionError("export interruption did not finish within its bound")


def assert_group_stopped(group):
    # A killed orphan can briefly be a zombie until the platform init reaps it;
    # it is no longer executing. Every non-zombie group member must be absent.
    result = subprocess.run(["ps", "-axo", "pgid=,stat="], check=True, capture_output=True, text=True)
    active = [line for line in result.stdout.splitlines()
              if line.split()[0] == str(group) and not line.split()[1].startswith("Z")]
    assert not active, f"validator group still executing: {active}"


def test_repeat_export_signals_stop_the_stream_and_validator_group(tmp_path, signal_name, phase):
    fixture = export_failure_stream(tmp_path)
    helper, _, _, job, _, _, _, execute = fixture
    signum = getattr(signal, signal_name)
    ready = tmp_path / "signal-ready.json"
    spawned = tmp_path / "validator-spawned.json"
    result_path = tmp_path / "controller-result.json"
    validator = tmp_path / "sleeping-validator.py"
    validator.write_text(
        "# Issue 6378 offline TERM-resistant validator group.\n"
        "import json, os, signal, time\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "child = os.fork()\n"
        "if child == 0:\n"
        "    time.sleep(60)\n    os._exit(0)\n"
        f"Path({str(ready)!r}).write_text(json.dumps({{'pid': os.getpid(), 'child': child}}))\n"
        "time.sleep(60)\n"
    )
    original_validate = helper._validate_staged
    original_popen, original_link = subprocess.Popen, os.link
    original_write_json, original_unlink = helper.write_json, Path.unlink

    def paused_validate(command, root, environment, export, control):
        if phase == "before_validator":
            ready.write_text(json.dumps({"phase": phase}) + "\n")
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                control.check()
                time.sleep(0.01)
            raise AssertionError("test signal never reached export controller")
        return original_validate(command, root, environment, export, control)

    def controlled_popen(command, *positional, **keywords):
        is_export = export_command(command, job)
        if is_export and phase in ("during_validator", "after_spawn"):
            assert keywords.get("start_new_session") is True
            command = [sys.executable, str(validator)]
        child = original_popen(command, *positional, **keywords)
        if is_export:
            spawned.write_text(json.dumps({"pid": child.pid, "group": child.pid}) + "\n")
            if phase == "after_spawn":
                # Real Popen succeeded, but the caller has not assigned its
                # returned handle yet. The handler must defer to that assignment.
                os.kill(os.getpid(), signum)
        return child

    def controlled_link(source, target, *positional, **keywords):
        value = original_link(source, target, *positional, **keywords)
        if phase == "after_link" and Path(target) == Path(job["destination"]):
            os.kill(os.getpid(), signum)
        return value

    def controlled_json(path, value):
        original_write_json(path, value)
        if phase == "after_manifest" and Path(path) == Path(job["manifest_path"]):
            os.kill(os.getpid(), signum)

    def controlled_unlink(path, *positional, **keywords):
        value = original_unlink(path, *positional, **keywords)
        if phase == "after_refusal_unlink" and path == Path(job["export_directory"]) / "failure.json":
            # This signal is blocked by the commit checkpoint. sigpending
            # must still force rollback and restore the reserved refusal.
            os.kill(os.getpid(), signum)
        return value

    controller = os.fork()
    if controller == 0:
        dispositions = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
        result = {}
        try:
            with patch.object(helper, "_validate_staged", paused_validate), \
                    patch.object(subprocess, "Popen", controlled_popen), patch.object(os, "link", controlled_link), \
                    patch.object(helper, "write_json", controlled_json), patch.object(Path, "unlink", controlled_unlink):
                execute()
            result["unexpected_success"] = True
        except BaseException as exc:
            result.update(exception=type(exc).__name__, message=str(exc))
        result["handlers_restored"] = all(signal.getsignal(number) == before for number, before in dispositions.items())
        result_path.write_text(json.dumps(result, sort_keys=True) + "\n")
        os._exit(2 if "exception" in result else 0)
    reaped = False
    started = time.monotonic()
    try:
        if phase in ("before_validator", "during_validator"):
            wait_control_file(ready, controller)
            if phase == "during_validator":
                assert json.loads(ready.read_bytes())["child"] > 0
            os.kill(controller, signum)
        assert wait_control_exit(controller) == 2
        reaped = True
        assert time.monotonic() - started < 20
        result = json.loads(result_path.read_bytes())
        assert result["handlers_restored"] is True
        assert "unexpected_success" not in result
        assert_refused_export(fixture)
        if phase in ("after_manifest", "after_refusal_unlink"):
            assert (Path(job["export_directory"]) / "unaccepted-manifest.json").is_file()
        if phase == "before_validator":
            assert not spawned.exists()
        elif spawned.exists():
            assert_group_stopped(json.loads(spawned.read_bytes())["group"])
    finally:
        if spawned.exists():
            group = json.loads(spawned.read_bytes())["group"]
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if not reaped:
            try:
                os.kill(controller, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(controller, 0)
            except ChildProcessError:
                pass


test_repeat_export_signals_stop_the_stream_and_validator_group = pytest.mark.parametrize(
    "signal_name,phase", [(name, phase) for name in ("SIGINT", "SIGTERM", "SIGHUP")
                          for phase in ("before_validator", "during_validator", "after_spawn", "after_link",
                                        "after_manifest", "after_refusal_unlink")]
)(test_repeat_export_signals_stop_the_stream_and_validator_group)
