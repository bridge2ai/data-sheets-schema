"""Offline root-scope scorer controls for issues 6358 and 6360, 2026-11-25.

Inputs are synthetic records, independent scope files and executable stand-ins.
The fake Poetry entrypoint forwards to the real exact-file validator. Evidence
stays in pytest's external basetemp; no installed Codex or provider is called.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

import pytest
import yaml

from tests.test_codex_rubric_scorer_instrument import ROOT, scenario, scorer


INSTRUMENT = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
# Frozen definition bytes reviewed in candidate 26b74b67e, before composition.
FROZEN_DEFINITIONS = {
    "rubric10": "84f42966ae968881aa65263c8d4f32a0ffe6988a85d24ea8d5a933e99ee1354d",
    "rubric20": "6beda6a0a46230b9c6128f9251c9eac0b5771f022c10b47cbc752f017432de52",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def items(evaluation):
    family = evaluation["rubric"].removesuffix("-semantic")
    for group in evaluation["elements" if family == "rubric10" else "categories"]:
        yield from group["sub_elements" if family == "rubric10" else "questions"]


def write_case(tools, evaluation):
    path = tools / "case.json"
    value = json.loads(path.read_bytes())
    value["evaluation"] = evaluation
    path.write_text(json.dumps(value) + "\n")


def root_scenario(directory, rubric="rubric10", context=None, **changes):
    args, tree, tools, evaluation = scenario(directory, rubric, context=context, **changes)
    support = ["src/data_sheets_schema/root_scope.py", "src/data_sheets_schema/root_scope_definition.py"]
    support += [name for family in ("rubric10", "rubric20") for name in (
        f"data/rubric/root_scope_v6/{family}_definition_overrides.json",
        f"src/download/prompts/{family}_semantic_v6_schema.json",
    )]
    for name in support:
        destination = tree / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    original_document = {"id": "example:parent", "title": "Synthetic root datasheet",
                         "resources": [{"id": "example:child-a"}, {"id": "example:child-b"}]}
    Path(args.record).write_text(yaml.safe_dump(original_document))
    scope = directory / "caller-scope.json"
    scope.write_text(json.dumps({
        "policy": "root_dataset_v1", "input_sha256": sha(Path(args.record).read_bytes()),
        "reason": "The caller selected the complete submitted synthetic datasheet.",
    }, indent=2, sort_keys=True) + "\n")
    argv = ["--semantic-version", "6.0", "--scope-context", str(scope), "--execute"]
    for name in ("repo_root", "method_directory", "label", "record", "rubric", "run_directory",
                 "codex_binary", "poetry_binary", "validation_venv", "auth_file",
                 "authorization_reference", "timeout"):
        argv.extend(["--" + name.replace("_", "-"), str(getattr(args, name))])
    if args.context is not None:
        argv.extend(["--context", str(args.context)])
    args = scorer.parser().parse_args(argv)
    evaluation["version"] = "6.0"
    evaluation["evaluation_scope"] = {
        "selection_policy": "root_dataset_v1", "policy": "single_dataset",
        "units": [{"path": "#", "id": original_document["id"]}],
        "collection_metadata_inherited": False,
    }
    evaluation["metadata"].update(
        input_sha256=sha(Path(args.record).read_bytes()), scope_context_sha256=sha(scope.read_bytes()),
        instrument_sha256=FROZEN_DEFINITIONS[rubric],
    )
    for item in items(evaluation):
        row = copy.deepcopy(item["unit_scores"][0])
        row["path"] = "#"
        item["unit_scores"] = [row]
    write_case(tools, evaluation)
    source = ROOT / "tests/fixtures/rubric_scorer/poetry_review_stub.py"
    (tools / "poetry").write_text("#!" + sys.executable + "\n" + source.read_text())
    (tools / "poetry").chmod(0o700)
    return args, tree, tools, evaluation


def assert_definition_provenance(plan, tree):
    family = plan["identity"]["rubric"].removesuffix("-semantic")
    source = f".claude/agents/d4d-{family}-semantic.md"
    overrides = f"data/rubric/root_scope_v6/{family}_definition_overrides.json"
    expected = {
        "source_path": source, "source_sha256": sha((tree / source).read_bytes()),
        "overrides_path": overrides, "overrides_sha256": sha((tree / overrides).read_bytes()),
        "composed_sha256": FROZEN_DEFINITIONS[family],
    }
    assert plan["definition_provenance"] == expected
    assert plan["inputs"]["agent-definition.md"] == {
        "source": "root_scope_v6_composition", "sha256": expected["composed_sha256"],
    }
    descriptor = next(json.loads(line) for line in plan["prompt"].splitlines()
                      if line.startswith("{") and '"required_deterministic_fields"' in line)
    assert descriptor["definition_provenance"] == expected
    beginning = plan["prompt"].index("BEGIN agent-definition.md (")
    header, rest = plan["prompt"][beginning:].split("\n", 1)
    composed, _ = rest.split("\nEND agent-definition.md\n", 1)
    raw = composed.encode()
    assert sha(raw) == FROZEN_DEFINITIONS[family]
    assert header == f"BEGIN agent-definition.md ({len(raw)} bytes; sha256 {sha(raw)})"
    assert (tree / source).read_text() not in plan["prompt"]
    assert (tree / overrides).read_text() not in plan["prompt"]
    assert not list((tree / ".claude/agents").glob("*-v6.md"))
    return expected


def test_root_scope_plan_is_read_only_and_keeps_applicability_separate(tmp_path):
    args, tree, tools, evaluation = root_scenario(tmp_path / "plan", context={"human_subjects": False})
    args.execute = False
    args.plan = True
    before = Path(args.record).read_bytes()
    scope_before = args.scope_context.read_bytes()
    with patch.object(scorer.subprocess, "run", side_effect=AssertionError("plan called a process")), \
            patch.object(scorer.subprocess, "Popen", side_effect=AssertionError("plan started a process")):
        plan = scorer.build_plan(args)
    assert plan["instrument"] == INSTRUMENT
    assert plan["identity"]["version"] == "6.0"
    assert plan["deterministic_fields"]["evaluation_scope"] == evaluation["evaluation_scope"]
    assert plan["deterministic_fields"]["metadata"] == evaluation["metadata"]
    assert_definition_provenance(plan, tree)
    assert plan["deterministic_fields"]["applicability_context"] == evaluation["applicability_context"]
    assert "--scope-context" in plan["validation_command"]
    assert plan["validation_command"][plan["validation_command"].index("--scope-context") + 1] == str(args.scope_context)
    assert plan["validation_command"][plan["validation_command"].index("--semantic-version") + 1] == "6.0"
    assert "--context" in plan["validation_command"]
    assert scope_before.decode() in plan["prompt"]
    assert str(tree) not in plan["prompt"]
    assert any(value["source"] == str(args.scope_context) and value["sha256"] == sha(scope_before)
               for value in plan["inputs"].values())
    assert Path(args.record).read_bytes() == before
    assert args.scope_context.read_bytes() == scope_before
    assert not Path(plan["run_directory"]).exists()
    assert not (tools / "invocation.json").exists()


def run_fake_canary(tmp_path, rubric, child=False):
    args, tree, tools, evaluation = root_scenario(tmp_path / rubric, rubric, child=child)
    before_record = Path(args.record).read_bytes()
    before_auth = args.auth_file.read_bytes()
    plan = scorer.build_plan(args)
    expected_definition = assert_definition_provenance(plan, tree)
    scorer.execute(plan, args)
    output = Path(plan["output"])
    accepted = (tools / "validated-snapshot.json").read_bytes()
    assert output.is_file() and output.read_bytes() == accepted
    result = json.loads(accepted)
    assert result["version"] == "6.0"
    assert result["scorer_instrument"]["id"] == INSTRUMENT
    assert INSTRUMENT in output.parts
    assert result["evaluation_scope"] == evaluation["evaluation_scope"]
    assert result["metadata"] == evaluation["metadata"]
    assert result["overall_score"] == evaluation["overall_score"]
    checked = json.loads((tools / "real-validator-result.json").read_bytes())
    assert checked["returncode"] == 0
    assert checked["accepted_snapshot_sha256"] == sha(accepted)
    assert checked["copied_auth_present_at_validation"] is False
    run = Path(plan["run_directory"])
    logs = result["evaluation_model"]["session_logs"]
    assert len(logs) == (2 if child else 1)
    for entry in logs:
        relative = Path(entry["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert relative.parts[:2] == ("codex-home", "sessions")
        assert sha((run / relative).read_bytes()) == entry["sha256"]
    for path in (Path.home(), run, Path(plan["repo_root"]), args.auth_file):
        assert str(path).encode() not in accepted
    assert Path(args.record).read_bytes() == before_record
    assert args.auth_file.read_bytes() == before_auth
    assert not (Path(plan["codex_home"]) / "auth.json").exists()
    receipt = json.loads((run / "receipt.json").read_bytes())
    assert receipt["status"] == "VALIDATED_AND_PUBLISHED"
    assert receipt["validator_input_sha256"] == sha(accepted)
    assert receipt["definition_provenance"] == expected_definition
    assert sha((run / "working/agent-definition.md").read_bytes()) == FROZEN_DEFINITIONS[rubric]


def test_fake_canary_rubric10_through_real_validator(tmp_path):
    run_fake_canary(tmp_path, "rubric10", child=True)


def test_fake_canary_rubric20_through_real_validator(tmp_path):
    run_fake_canary(tmp_path, "rubric20")


def test_scope_declarations_refuse_before_fake_launch(tmp_path):
    cases = ("missing", "wrong_hash", "missing_reason", "blank_reason", "unknown_field",
             "unknown_policy", "malformed_json", "duplicate_key", "collection", "core_collection")
    for change in cases:
        args, _, tools, _ = root_scenario(tmp_path / change)
        declaration = json.loads(args.scope_context.read_bytes())
        if change == "missing":
            args.scope_context = None
        elif change == "malformed_json":
            args.scope_context.write_text("{broken JSON\n")
        elif change == "duplicate_key":
            args.scope_context.write_text('{"policy":"root_dataset_v1","policy":"root_dataset_v1",'
                                          '"input_sha256":"' + declaration["input_sha256"] + '","reason":"fixture"}')
        else:
            if change == "wrong_hash":
                declaration["input_sha256"] = "0" * 64
            elif change == "missing_reason":
                declaration.pop("reason")
            elif change == "blank_reason":
                declaration["reason"] = " "
            elif change == "unknown_field":
                declaration["undeclared"] = True
            elif change == "unknown_policy":
                declaration["policy"] = "choose_any_unit"
            else:
                document = yaml.safe_load(Path(args.record).read_bytes())
                document["conforms_to_class"] = "DatasetCollection" if change == "collection" else "CoreDatasetCollection"
                Path(args.record).write_text(yaml.safe_dump(document))
                declaration["input_sha256"] = sha(Path(args.record).read_bytes())
            args.scope_context.write_text(json.dumps(declaration) + "\n")
        with pytest.raises((ValueError, OSError)):
            scorer.build_plan(args)
        assert not Path(args.run_directory).exists()
        assert not (tools / "invocation.json").exists()


def test_legacy_mode_refuses_a_root_scope_override(tmp_path):
    args, _, tools, _ = root_scenario(tmp_path / "legacy-override")
    args.semantic_version = "3.0"
    with pytest.raises(ValueError):
        scorer.build_plan(args)
    assert not (tools / "invocation.json").exists()


def test_scope_bytes_changed_after_plan_refuse_before_launch(tmp_path):
    args, _, tools, _ = root_scenario(tmp_path / "scope-drift")
    plan = scorer.build_plan(args)
    with args.scope_context.open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError):
        scorer.execute(plan, args)
    assert not Path(args.run_directory).exists()
    assert not (tools / "invocation.json").exists()


def test_definition_component_changes_refuse_before_fake_launch(tmp_path):
    for phase in ("before_plan", "after_plan"):
        for component in ("source", "overrides"):
            args, tree, tools, _ = root_scenario(tmp_path / f"{phase}-{component}")
            plan = scorer.build_plan(args) if phase == "after_plan" else None
            path = (tree / ".claude/agents/d4d-rubric10-semantic.md" if component == "source"
                    else tree / "data/rubric/root_scope_v6/rubric10_definition_overrides.json")
            with path.open("ab") as handle:
                handle.write(b"\n")
            with pytest.raises(ValueError):
                if plan is None:
                    scorer.build_plan(args)
                else:
                    scorer.execute(plan, args)
            assert not Path(args.run_directory).exists()
            assert not (tools / "invocation.json").exists()


def test_real_validator_refuses_forged_scope_and_evidence(tmp_path):
    for change in ("unit", "scope_hash", "selection_policy", "evidence_pointer"):
        args, _, tools, evaluation = root_scenario(tmp_path / change)
        plan = scorer.build_plan(args)
        if change == "unit":
            evaluation["evaluation_scope"]["units"] = [{"path": "#/resources/0", "id": "example:child-a"}]
            for item in items(evaluation):
                item["unit_scores"][0]["path"] = "#/resources/0"
        elif change == "scope_hash":
            evaluation["metadata"]["scope_context_sha256"] = "0" * 64
        elif change == "selection_policy":
            evaluation["evaluation_scope"]["selection_policy"] = "choose_any_unit"
        else:
            next(items(evaluation))["unit_scores"][0]["cited"] = [{"path": "/missing_root_field"}]
        write_case(tools, evaluation)
        with pytest.raises(scorer.ScorerError):
            scorer.execute(plan, args)
        assert not Path(plan["output"]).exists()
        checked = json.loads((tools / "real-validator-result.json").read_bytes())
        assert checked["returncode"] != 0
        assert json.loads((Path(plan["run_directory"]) / "receipt.json").read_bytes())["status"] == "REFUSED"


def test_published_output_refuses_absolute_home_paths_in_model_text(tmp_path):
    for index, leaked in enumerate(("/Users/synthetic-owner/private/trace.json",
                                   "/home/synthetic-owner/private/trace.json",
                                   "file:/Users/synthetic-owner/private/trace.json")):
        args, _, tools, evaluation = root_scenario(tmp_path / f"local-path-{index}")
        evaluation["semantic_analysis"]["semantic_insights"] = ["Local diagnostic: " + leaked]
        write_case(tools, evaluation)
        plan = scorer.build_plan(args)
        with pytest.raises((scorer.ScorerError, ValueError)):
            scorer.execute(plan, args)
        assert not Path(plan["output"]).exists()
        assert not (Path(plan["codex_home"]) / "auth.json").exists()
        receipt = json.loads((Path(plan["run_directory"]) / "receipt.json").read_bytes())
        assert receipt["status"] == "REFUSED"
