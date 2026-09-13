"""Standalone offline provider fixtures copied into the clean wheel canary.

Imports only the standard library and declared package dependencies. This is
test support, not a provider or an evaluation of a real dataset.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from data_sheets_schema import api_runner, resources
from data_sheets_schema.evaluation_context import context_digest, load_document
from data_sheets_schema.judge_contract import evaluation_contract
from judge_fixtures import judge_reply

PROJECT = "EXTERNAL_CLINICAL"
METHOD = "external_api"


def response(text):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=100, output_tokens=50,
                              cache_read_input_tokens=0, cache_creation_input_tokens=0),
        stop_reason="end_turn", model="offline-fixture")


class GenerationClient:
    def __init__(self):
        self.messages = self
        self.calls = []

    def create(self, **request):
        self.calls.append(request)
        content = request["messages"][-1]["content"]
        text = " ".join(part.get("text", "") for part in content)
        if api_runner.PHASE_INSTRUCTIONS["full_readdress"] in text:
            return response("readdress: []\n")
        phase = next((phase for phase, instruction in api_runner.PHASE_INSTRUCTIONS.items()
                      if instruction in text), None)
        assert phase is not None, "unrecognized generation request"
        if phase == "audit":
            return response('{"findings": [], "summary": "none"}')
        if phase == "report":
            return response("# Reconciliation\nNo discrepancies.\n\n## Dispositions\n\n"
                            "| slot | disposition | record | reason |\n|---|---|---|---|\n"
                            "| `keywords` | retained | full | kept |\n")
        return response("```yaml\nid: https://example.org/clinical\n"
                        "title: Open Clinical Cohort\nname: clinical\n"
                        "description: Synthetic clinical test fixture.\n"
                        "keywords: [clinical]\n```")

    @contextmanager
    def stream(self, **request):
        result = self.create(**request)
        yield SimpleNamespace(get_final_message=lambda: result)


class JudgeClient:
    def __init__(self):
        self.messages = self
        self.calls = []

    def create(self, **request):
        self.calls.append(request)
        contract = json.loads(request["messages"][0]["content"].split("```json\n")[1].split("```")[0])
        rubric = "rubric10" if next(iter(contract["items"])).startswith("E") else "rubric20"
        return response(json.dumps(judge_reply(contract, rubric, PROJECT, METHOD)))


def semantic_record(path, rubric, context, definition):
    """Build a complete zero-score synthetic semantic reply for both rubrics."""
    document, input_sha = load_document(path)
    raw = resources.resource_path(f"data/rubric/{rubric}.txt").read_bytes()
    contract = evaluation_contract(rubric, yaml.safe_load(raw), context, document)
    result = judge_reply(contract, rubric, PROJECT, METHOD)
    r10 = rubric == "rubric10"
    for index, group in enumerate(result["elements" if r10 else "categories"], 1):
        group.update(name=f"Element {index}" if r10 else group["name"], description="Synthetic test group")
        fixed = 0
        for item in group["sub_elements" if r10 else "questions"]:
            key = item["id"] if r10 else f"Q{item['id']}"
            rule = contract["items"][key]
            fixed += rule["fixed_max_score"]
            item.update(description="Synthetic test item", quality_note="No evidence in test reply",
                        score_label="No evidence", applicability_status=rule["status"],
                        applicability_evidence=rule["evidence"])
            if r10:
                item["item_id"] = item.pop("id")
            else:
                item.update(max_score=rule["fixed_max_score"],
                            score_type="pass_fail" if rule["fixed_max_score"] == 1 else "numeric")
        if not r10:
            group["category_max"] = fixed
    maximum = sum(rule["fixed_max_score"] for rule in contract["items"].values())
    adjusted = sum(rule["max_score"] for rule in contract["items"].values())
    result.update(rubric=f"{rubric}-semantic", version="2.0", d4d_file=str(path),
                  evaluation_timestamp="2026-09-13T00:00:00Z",
                  model={"name": "offline-fixture", "temperature": 0,
                         "evaluation_type": "semantic_llm_judge"},
                  applicability_context=contract["context"], evaluation_scope=contract["scope"],
                  semantic_analysis={"issues_detected": [], "semantic_insights": [],
                                     "consistency_checks": {"passed": 0, "failed": 0, "warnings": 0},
                                     "correctness_validations": {}},
                  metadata={"input_sha256": input_sha, "context_sha256": context_digest(contract["context"]),
                            "rubric_sha256": hashlib.sha256(raw).hexdigest(),
                            "instrument_sha256": hashlib.sha256(definition.read_bytes()).hexdigest()})
    result["overall_score"].update(
        total_points=0, max_points=maximum, adjusted_max_points=adjusted,
        excluded_max_points=maximum-adjusted, normalized_percentage=0 if adjusted else None,
        fixed_percentage=0,
        **{"sub_elements_not_applicable" if r10 else "questions_not_applicable":
           sum(not rule["applicable"] for rule in contract["items"].values())})
    return result


def check_installed_evaluation_and_rendering(path, core_path):
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    from data_sheets_schema.evaluation import evaluate_d4d, evaluate_d4d_llm, validate
    from data_sheets_schema.rendering import human_readable_renderer

    for module in (api_runner, evaluate_d4d, evaluate_d4d_llm, validate, human_readable_renderer):
        assert Path(module.__file__).resolve().is_relative_to(resources.PACKAGE_ROOT.resolve()), module.__file__
    assert not resources.is_checkout()
    assert not Path("data/preprocessed").exists()
    assert not Path("data/d4d_concatenated").exists()

    runner = CliRunner()
    context = {"human_subjects": {"value": True, "evidence": "Synthetic clinical cohort"},
               "processing_software": {"value": False, "evidence": "No software produced in this fixture"}}
    context_path = Path("context.yaml")
    context_path.write_text(yaml.safe_dump(context), encoding="utf-8")
    result = runner.invoke(cli, ["evaluate", "presence", "--file", str(path),
                               "--project", PROJECT, "--method", METHOD,
                               "--context", str(context_path), "--output-dir", "presence"])
    assert result.exit_code == 0, result.output + str(result.exception)
    scores = list(Path("presence").rglob("scores.json"))
    assert len(scores) == 1, scores
    assert PROJECT in scores[0].read_text()

    client = JudgeClient()
    evaluator = evaluate_d4d_llm.D4DLLMEvaluator(
        evaluate_d4d_llm.LLMEvaluationConfig(error_dir=Path("errors"), attempts_dir=Path("attempts")),
        context=context, client=client)
    judgments = evaluator.evaluate_file(path, PROJECT, METHOD, "both")
    assert len(client.calls) == 2 and len(list(Path("attempts").glob("*.json"))) == 2
    for rubric, judgment in judgments.items():
        assert judgment["metadata"]["instrument_kind"] == "api_system_prompt"
        target = Path(f"{rubric}_api.json")
        target.write_text(json.dumps(judgment), encoding="utf-8")
        html = target.with_suffix(".html")
        result = runner.invoke(cli, ["render", "evaluation", str(target), "--rubric", rubric, "-o", str(html)])
        assert result.exit_code == 0 and html.is_file(), result.output + str(result.exception)

        definition = resources.resource_path(f".claude/agents/d4d-{rubric}-semantic.md")
        semantic = semantic_record(path, rubric, context, definition)
        target = Path(f"{rubric}_semantic.json")
        target.write_text(json.dumps(semantic), encoding="utf-8")
        args = ["evaluate", "validate", str(target), "--input", str(path),
                "--agent-definition", str(definition), "--context", str(context_path)]
        result = runner.invoke(cli, args)
        assert result.exit_code == 0, result.output + str(result.exception)
        html = target.with_suffix(".html")
        result = runner.invoke(cli, ["render", "evaluation", str(target), "--rubric", rubric, "-o", str(html)])
        assert result.exit_code == 0 and html.is_file(), result.output + str(result.exception)
        # A real validation failure must propagate from the installed command.
        semantic["metadata"]["input_sha256"] = "0" * 64
        target.write_text(json.dumps(semantic), encoding="utf-8")
        result = runner.invoke(cli, args)
        assert result.exit_code != 0 and "digest" in result.output, result.output

    for source in (path, core_path):
        html = source.with_suffix(".html")
        result = runner.invoke(cli, ["render", "html", str(source), "-o", str(html)])
        assert result.exit_code == 0 and html.is_file(), result.output + str(result.exception)
        assert "Open Clinical Cohort" in html.read_text()
        assert (html.parent / "datasheet-common.css").is_file()
    print("installed evaluation and rendering passed")
