"""Offline instrument controls for issue 6315, 2026-11-25.

Inputs are synthetic records, unchanged rubric support, and executable stubs.
Outputs are retained pytest fixtures and validated synthetic evaluations.
No test invokes the installed Codex binary or a provider.
"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

import pytest

from tests.test_evaluation.test_semantic_context_scope import record


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/adhoc/score_semantic_rubric_codex_20261125.py"
SPEC = importlib.util.spec_from_file_location("rubric_scorer_20261125", MODULE_PATH)
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)

SUPPORT = [
    "scripts/validate_evaluation_schema.py",
    "src/data_sheets_schema/resources.py",
    "src/data_sheets_schema/evaluation_context.py",
    "src/data_sheets_schema/judge_contract.py",
    "src/data_sheets_schema/semantic_scope.py",
    "src/data_sheets_schema/semantic_instrument.py",
    "src/data_sheets_schema/semantic_evidence.py",
    "src/data_sheets_schema/semantic_evidence_authority.py",
    "src/data_sheets_schema/evaluation/__init__.py",
    "src/data_sheets_schema/evaluation/validate.py",
    "data/rubric/semantic_evidence_authority_v3.json",
    "pyproject.toml",
]


def scenario(directory, rubric="rubric10", context=None, **changes):
    directory.mkdir(parents=True)
    tree = directory / "tree"
    tree.mkdir()
    files = SUPPORT + [
        name
        for family in ("rubric10", "rubric20")
        for name in (
            f".claude/agents/d4d-{family}-semantic.md",
            f"data/rubric/{family}.txt",
            f"src/download/prompts/{family}_semantic_schema.json",
        )
    ]
    for name in files:
        destination = tree / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    fixture = directory / "fixture"
    fixture.mkdir()
    evaluation, input_path = record(fixture, rubric, context={} if context is None else context)
    label = "2026-11-25_stub_rep1"
    target = tree / "data/d4d_concatenated/synthetic_method" / label / "Toy_d4d.yaml"
    target.parent.mkdir(parents=True)
    shutil.copyfile(input_path, target)
    evaluation.update(project="Toy", method="synthetic_method", d4d_file=str(target.relative_to(tree)), label=label)
    evaluation["model"]["name"] = "forged-prompt-claim"
    evaluation["evaluation_model"] = {"name": "forged-prompt-claim", "basis": "prompt"}
    tools = directory / "tools"
    tools.mkdir()
    for name in ("codex", "poetry"):
        source = ROOT / f"tests/fixtures/rubric_scorer/{name}_stub.py"
        destination = tools / name
        destination.write_text("#!" + sys.executable + "\n" + source.read_text())
        destination.chmod(0o700)
    (tools / "case.json").write_text(json.dumps({"evaluation": evaluation, **changes}))
    auth = directory / "fake-auth.json"
    auth.write_text('{"offline_test": true}\n')
    auth.chmod(0o600)
    argv = [
        "--repo-root", str(tree), "--method-directory", "synthetic_method",
        "--label", label, "--record", str(target), "--rubric", rubric + "-semantic",
        "--run-directory", str(directory / "run"),
        "--codex-binary", str(tools / "codex"), "--poetry-binary", str(tools / "poetry"),
        "--validation-venv", sys.prefix, "--auth-file", str(auth),
        "--authorization-reference", "offline fixture only, never a live authorization",
        "--execute",
    ]
    if context is not None:
        argv.extend(["--context", str(fixture / "caller-context.yaml")])
    args = scorer.parser().parse_args(argv)
    return args, tree, tools, evaluation


def test_plan_is_read_only_and_passes_instrument_explicitly(tmp_path):
    args, tree, tools, _ = scenario(tmp_path / "plan")
    args.execute = False
    args.plan = True
    before = sorted(str(p.relative_to(tree)) for p in tree.rglob("*"))
    with patch.object(scorer.subprocess, "run", side_effect=AssertionError("plan called a process")), \
            patch.object(scorer.subprocess, "Popen", side_effect=AssertionError("plan started a process")):
        plan = scorer.build_plan(args)
    assert before == sorted(str(p.relative_to(tree)) for p in tree.rglob("*"))
    assert not Path(plan["run_directory"]).exists()
    assert not (tools / "invocation.json").exists()
    assert scorer.sys.dont_write_bytecode is True
    command = plan["command"]
    assert "gpt-6-astra" in command
    assert any("model_reasoning_effort" in item and "ultra" in item for item in command)
    assert any("service_tier" in item and "fast" in item for item in command)
    assert "--ignore-user-config" in command and "--ignore-rules" in command
    assert "--skip-git-repo-check" in command
    for forbidden in ("--dangerously-bypass-approvals-and-sandbox", "--resume", "--search"):
        assert forbidden not in command
    assert plan["validation_command"][1:3] == ["run", "python"]
    assert "--input" in plan["validation_command"]
    assert "--agent-definition" in plan["validation_command"]
    definition = (tree / ".claude/agents/d4d-rubric10-semantic.md").read_text()
    assert definition in plan["prompt"]


def test_real_validation_and_session_derived_model_for_both_rubrics(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        args, tree, tools, original = scenario(tmp_path / rubric, rubric)
        plan = scorer.build_plan(args)
        assert plan["deterministic_fields"]["metadata"] == original["metadata"]
        assert plan["deterministic_fields"]["applicability_context"] == original["applicability_context"]
        assert plan["deterministic_fields"]["evaluation_scope"] == original["evaluation_scope"]
        scorer.execute(plan, args)
        output = Path(plan["output"])
        assert output.is_file()
        result = json.loads(output.read_text())
        assert result["model"]["name"] == "gpt-6-astra"
        assert result["model"]["temperature"] is None
        assert result["evaluation_model"]["name"] == "gpt-6-astra"
        assert result["overall_score"] == original["overall_score"]
        invocation = json.loads((tools / "invocation.json").read_text())
        assert invocation["cwd"] == plan["working_directory"]
        assert invocation["codex_home"] == plan["codex_home"]
        assert not (Path(invocation["cwd"]) / ".git").exists()
        assert (Path(invocation["cwd"]) / "record.yaml").read_bytes() == Path(args.record).read_bytes()
        assert invocation["working_files"] == sorted(plan["inputs"])
        checked = json.loads((tools / "validator-invocation.json").read_text())
        assert "validate_evaluation_schema.py" in checked["argv"][2]
        assert "--rubric" in checked["argv"]
        assert output.name.endswith("_evaluation.json")
        assert "label_aware" in output.parts
        with pytest.raises((scorer.ScorerError, FileExistsError)):
            scorer.execute(plan, args)


def test_input_and_output_boundaries_refuse_before_launch(tmp_path):
    for change in ("outside_label", "symlink", "existing_output", "existing_run"):
        args, tree, tools, _ = scenario(tmp_path / change)
        if change == "outside_label":
            another = tree / "data/d4d_concatenated/synthetic_method/other/Toy_d4d.yaml"
            another.parent.mkdir()
            shutil.copyfile(args.record, another)
            args.record = another
        elif change == "symlink":
            target = Path(args.record)
            original = target.with_name("original.yaml")
            target.rename(original)
            target.symlink_to(original.name)
        elif change == "existing_run":
            Path(args.run_directory).mkdir()
        else:
            plan = scorer.build_plan(args)
            output = Path(plan["output"])
            output.parent.mkdir(parents=True)
            output.write_text("prior evaluation, preserve these bytes")
        with pytest.raises(scorer.ScorerError):
            scorer.build_plan(args)
        assert not (tools / "invocation.json").exists()
        if change == "existing_output":
            assert output.read_text() == "prior evaluation, preserve these bytes"


def test_untrusted_or_missing_rollout_never_publishes(tmp_path):
    cases = [
        {"model": "different-model"}, {"effort": "low"}, {"missing_log": True},
        {"missing_context": True}, {"wrong_cwd": True}, {"thread": "foreign-thread"},
        {"external_tool": True}, {"exit": 7}, {"missing_child_log": True},
    ]
    for index, case in enumerate(cases):
        args, _, tools, _ = scenario(tmp_path / f"case-{index}", **case)
        plan = scorer.build_plan(args)
        with pytest.raises(scorer.ScorerError):
            scorer.execute(plan, args)
        assert not Path(plan["output"]).exists()
        assert (tools / "invocation.json").exists()


def test_real_validator_rejects_bad_score_and_input_hash(tmp_path):
    for mutation in ("score", "input_hash"):
        args, _, tools, original = scenario(tmp_path / mutation)
        evaluation = copy.deepcopy(original)
        if mutation == "score":
            evaluation["overall_score"]["total_points"] -= 1
        else:
            evaluation["metadata"]["input_sha256"] = "0" * 64
        (tools / "case.json").write_text(json.dumps({"evaluation": evaluation}))
        plan = scorer.build_plan(args)
        with pytest.raises(scorer.ScorerError):
            scorer.execute(plan, args)
        assert not Path(plan["output"]).exists()
        assert (tools / "validator-invocation.json").exists()


def test_delegated_session_is_bound_and_foreign_children_refuse(tmp_path):
    for index, changes in enumerate(({}, {"child_parent": "foreign-thread"},
                                      {"child_model": "different-model"})):
        args, _, _, _ = scenario(tmp_path / f"child-{index}", child=True, **changes)
        plan = scorer.build_plan(args)
        if changes:
            with pytest.raises(scorer.ScorerError):
                scorer.execute(plan, args)
            assert not Path(plan["output"]).exists()
        else:
            scorer.execute(plan, args)
            result = json.loads(Path(plan["output"]).read_text())
            assert {entry["id"] for entry in result["evaluation_model"]["session_logs"]} == {
                "stub-thread", "00000000-0000-4000-8000-000000000001"}


def test_authorization_and_planned_input_drift_refuse_before_process(tmp_path):
    for change in ("authorization", "record", "executable"):
        args, _, tools, _ = scenario(tmp_path / change)
        plan = scorer.build_plan(args)
        if change == "authorization":
            args.authorization_reference = None
        elif change == "record":
            Path(args.record).write_text("id: changed:record\n")
        else:
            with (tools / "codex").open("a") as handle:
                handle.write("\n# changed executable bytes\n")
        with pytest.raises(scorer.ScorerError):
            scorer.execute(plan, args)
        assert not (tools / "invocation.json").exists()
        assert not Path(plan["run_directory"]).exists()


def test_supplied_independent_context_passes_real_validation(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        args, _, tools, original = scenario(tmp_path / rubric, rubric,
                                            context={"human_subjects": False})
        plan = scorer.build_plan(args)
        assert "--context" in plan["validation_command"]
        assert "caller-context.yaml" in plan["inputs"]
        assert plan["deterministic_fields"]["metadata"] == original["metadata"]
        assert plan["deterministic_fields"]["applicability_context"] == original["applicability_context"]
        scorer.execute(plan, args)
        result = json.loads(Path(plan["output"]).read_text())
        assert result["applicability_context"] == original["applicability_context"]
        assert result["metadata"]["context_sha256"] == original["metadata"]["context_sha256"]
        assert result["overall_score"]["excluded_max_points"] > 0
        validation = json.loads((tools / "validator-invocation.json").read_text())
        assert "--context" in validation["argv"]


def test_label_is_required_and_cannot_name_another_series(tmp_path):
    for change in ("missing", "wrong"):
        args, _, tools, evaluation = scenario(tmp_path / change)
        if change == "missing":
            evaluation.pop("label")
        else:
            evaluation["label"] = "another-series"
        (tools / "case.json").write_text(json.dumps({"evaluation": evaluation}))
        plan = scorer.build_plan(args)
        with pytest.raises(scorer.ScorerError):
            scorer.execute(plan, args)
        assert not Path(plan["output"]).exists()
        assert not (tools / "validator-invocation.json").exists()


def test_registered_support_byte_drift_refuses_before_process(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        sources = [
            f".claude/agents/d4d-{rubric}-semantic.md",
            f"data/rubric/{rubric}.txt",
            f"src/download/prompts/{rubric}_semantic_schema.json",
            "data/rubric/semantic_evidence_authority_v3.json",
        ]
        for index, source in enumerate(sources):
            args, tree, tools, _ = scenario(tmp_path / f"{rubric}-{index}", rubric)
            with (tree / source).open("ab") as handle:
                handle.write(b"\n")
            with patch.object(scorer.subprocess, "run", side_effect=AssertionError("plan called a process")), \
                    patch.object(scorer.subprocess, "Popen", side_effect=AssertionError("plan started a process")):
                with pytest.raises(scorer.ScorerError):
                    scorer.build_plan(args)
            assert not Path(args.run_directory).exists()
            assert not (tools / "invocation.json").exists()
