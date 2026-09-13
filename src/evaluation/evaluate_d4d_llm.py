#!/usr/bin/env python3
"""
D4D LLM-based Evaluation Framework

Evaluates D4D (Datasheets for Datasets) YAML files using LLM-as-judge approach
with Claude Sonnet 4.5. Provides quality-based assessment using rubric10 and rubric20,
complementing the existing field-presence detection in evaluate_d4d.py.

Usage:
    # Evaluate single file with both rubrics
    python src/evaluation/evaluate_d4d_llm.py \\
      --file data/d4d_concatenated/claudecode/VOICE_d4d.yaml \\
      --project VOICE --method claudecode

    # Evaluate all projects
    python src/evaluation/evaluate_d4d_llm.py --all

    # Evaluate with specific rubric only
    python src/evaluation/evaluate_d4d_llm.py --file ... --rubric rubric10

Author: Claude Code
Date: 2025-12-06
"""

import argparse
import json
import csv
import yaml
import hashlib
import uuid
from pathlib import Path
from typing import Dict, List, Any, Literal, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import anthropic
from data_sheets_schema.evaluation_context import (
    context_digest, identity, load_context, normalize_context, unwrap_document,
)
from data_sheets_schema.judge_contract import evaluation_contract, validate_result, VERSION


#: Where a result's identity is carried, so no exporter has to parse it out of
#: a composite key. A dataset name may contain underscores and so may a method
#: (`claudecode_agent`), which makes such a key ambiguous in both directions —
#: no split recovers `AI_READI` + `claudecode_agent` from
#: `AI_READI_claudecode_agent`, and the previous one silently did not (#622).
IDENTITY = "identity"


def identity_of(key: str, project_results: dict) -> tuple[str, str]:
    """`(project, method)` for one result.

    Falls back to naming the gap rather than guessing. A result written before
    identity was carried cannot have it recovered — the ambiguity is real, not
    an implementation shortcut — so it reports the raw key as the project and
    leaves the method empty, which is visibly incomplete rather than plausibly
    wrong.
    """
    carried = project_results.get(IDENTITY) if isinstance(project_results, dict) \
        else None
    if isinstance(carried, dict) and carried.get("project"):
        return str(carried["project"]), str(carried.get("method") or "")
    return key, ""


@dataclass
class LLMEvaluationConfig:
    """Configuration for LLM-based evaluation"""
    model: str = "claude-sonnet-4-5-20250929"  # Date-pinned model selection
    temperature: float = 0.0  # Reduces sampling variation; repeatability still needs measurement
    max_tokens: int = 8000
    rubric_dir: Path = Path("data/rubric")
    prompts_dir: Path = Path("src/download/prompts")
    schema_path: Path = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
    error_dir: Path = Path("data/evaluation_llm/errors")
    attempts_dir: Optional[Path] = None


class D4DLLMEvaluator:
    """LLM-as-judge evaluator for D4D files using Claude Sonnet 4.5"""

    def __init__(self, config: Optional[LLMEvaluationConfig] = None, *, context=None, client=None):
        self.config = config or LLMEvaluationConfig()
        self.context = normalize_context(context)
        self._rubric_bytes = {}

        # Load rubrics
        self.rubric10 = self._load_rubric("rubric10.txt")
        self.rubric20 = self._load_rubric("rubric20.txt")

        # Load prompts
        self.rubric10_system_prompt = self._load_prompt("rubric10_system_prompt.md")
        self.rubric20_system_prompt = self._load_prompt("rubric20_system_prompt.md")
        # Validate inputs and load local assets before constructing a provider.
        self.client = client if client is not None else anthropic.Anthropic()

    def _load_rubric(self, filename: str) -> Dict[str, Any]:
        """Load and parse rubric YAML"""
        path = self.config.rubric_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Rubric file not found: {path}")

        raw = path.read_bytes()
        self._rubric_bytes[filename] = raw
        return yaml.safe_load(raw)

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template"""
        path = self.config.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")

        with open(path) as f:
            return f.read()

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _build_system_prompt(self, rubric_name: Literal["rubric10", "rubric20"]) -> str:
        """Construct system prompt with rubric specification"""
        # Select base prompt
        if rubric_name == "rubric10":
            prompt = self.rubric10_system_prompt
            rubric = self.rubric10
        else:
            prompt = self.rubric20_system_prompt
            rubric = self.rubric20

        # Insert rubric specification
        rubric_spec = yaml.dump(rubric, sort_keys=False, default_flow_style=False)
        prompt = prompt.replace("{RUBRIC_SPECIFICATION}", rubric_spec)

        return prompt

    def _build_user_prompt(self, d4d_content: str, project: str, method: str, d4d_filename: str,
                           *, contract: dict) -> str:
        """Construct user prompt with D4D file to evaluate"""
        return f"""Evaluate this D4D datasheet for quality and completeness.

**Project:** {project}
**Generation Method:** {method}
**Filename:** {d4d_filename}

**Declared applicability and required evaluation scope:**
```json
{json.dumps(contract, ensure_ascii=False, sort_keys=True)}
```

**D4D YAML Content:**
```yaml
{d4d_content}
```

Provide your evaluation in the specified JSON format. Remember to assess QUALITY, not just presence."""

    def evaluate_file(
        self,
        d4d_path: Path,
        project: str,
        method: str,
        rubric: Literal["rubric10", "rubric20", "both"] = "both"
    ) -> Dict[str, Any]:
        """
        Evaluate a D4D file using LLM-as-judge.

        Args:
            d4d_path: Path to D4D YAML file
            project: Nonempty dataset or project identity supplied by the caller
            method: Nonempty generation-method identity supplied by the caller
            rubric: Which rubric to use ("rubric10", "rubric20", or "both")

        Returns:
            Dictionary with evaluation results for requested rubric(s)
        """
        identity(project, "project")
        identity(method, "method")
        if rubric not in {"rubric10", "rubric20", "both"}:
            raise ValueError("unknown rubric")
        # Capture the exact input once; both judges receive these same bytes.
        if not d4d_path.exists():
            raise FileNotFoundError(f"D4D file not found: {d4d_path}")

        raw = d4d_path.read_bytes()
        d4d_content = raw.decode("utf-8-sig")
        d4d_file_hash = hashlib.sha256(raw).hexdigest()

        results = {}

        # Evaluate with rubric10
        if rubric in ["rubric10", "both"]:
            print(f"🔍 Evaluating with rubric10: {d4d_path.name}")
            results["rubric10"] = self._evaluate_with_rubric(
                "rubric10",
                d4d_content,
                project,
                method,
                d4d_path.name,
                d4d_file_hash
            )

        # Evaluate with rubric20
        if rubric in ["rubric20", "both"]:
            print(f"🔍 Evaluating with rubric20: {d4d_path.name}")
            results["rubric20"] = self._evaluate_with_rubric(
                "rubric20",
                d4d_content,
                project,
                method,
                d4d_path.name,
                d4d_file_hash
            )

        return results

    def _evaluate_with_rubric(
        self,
        rubric_name: Literal["rubric10", "rubric20"],
        d4d_content: str,
        project: str,
        method: str,
        d4d_filename: str,
        d4d_file_hash: str
    ) -> Dict[str, Any]:
        """Evaluate with a specific rubric using Claude API"""
        identity(project, "project")
        identity(method, "method")
        specification = self.rubric10 if rubric_name == "rubric10" else self.rubric20
        contract = evaluation_contract(
            rubric_name, specification, self.context,
            unwrap_document(yaml.safe_load(d4d_content)))
        # Build and attest the actual strings sent to the provider.
        system_prompt = self._build_system_prompt(rubric_name)
        user_prompt = self._build_user_prompt(
            d4d_content, project, method, d4d_filename, contract=contract)

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
        except Exception as e:
            raise RuntimeError(f"Claude API call failed: {e}") from e

        raw_response = "\n".join(block.text for block in response.content if hasattr(block, "text"))
        # Validate the accepted score under this instrument's own contract.
        try:
            if getattr(response, "stop_reason", "end_turn") not in {"end_turn", "stop_sequence"}:
                raise ValueError("provider did not finish the evaluation")
            evaluation = self._parse_llm_response(raw_response)
            validate_result(evaluation, rubric_name, project, method, contract)
        except Exception as e:
            # Identity is data, never a path component. Preserve every attempt.
            self.config.error_dir.mkdir(parents=True, exist_ok=True)
            error_file = self.config.error_dir / f"{rubric_name}_{uuid.uuid4().hex}.json"
            with error_file.open("x", encoding="utf-8") as f:
                json.dump({"error": str(e), "response": raw_response,
                           "project": project, "method": method,
                           "input_sha256": d4d_file_hash,
                           "instrument_sha256": hashlib.sha256(system_prompt.encode()).hexdigest(),
                           "request_user_prompt_sha256": hashlib.sha256(user_prompt.encode()).hexdigest()},
                          f, indent=2)
            raise RuntimeError(
                f"Failed to accept LLM response. Response saved to {error_file}"
            ) from e

        # Preserve judge annotations, but attest the actual request ourselves.
        # This runner sends an expanded API template, not a Claude agent
        # definition (#1239). A judge's claimed digest is separate evidence.
        metadata = dict(evaluation.get("metadata") or {})
        if "instrument_sha256" in metadata:
            metadata["evaluator_reported_instrument_sha256"] = metadata["instrument_sha256"]
        metadata.update({
            "evaluator_id": metadata.get("evaluator_id") or str(uuid.uuid4()),
            "rubric_hash": hashlib.sha256(self._rubric_bytes[f"{rubric_name}.txt"]).hexdigest(),
            "d4d_file_hash": d4d_file_hash,
            "instrument_kind": "api_system_prompt",
            "instrument_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
            "request_user_prompt_sha256": hashlib.sha256(user_prompt.encode("utf-8")).hexdigest(),
            "context_sha256": context_digest(self.context),
            "instrument_version": VERSION,
            "model": self.config.model,
            "temperature": self.config.temperature,
        })
        evaluation["metadata"] = metadata
        evaluation["model"] = {"name": self.config.model, "temperature": self.config.temperature,
                               "evaluation_type": "llm_as_judge"}
        evaluation["d4d_file"] = d4d_filename
        if getattr(response, "model", None):
            metadata["response_model"] = response.model
        if self.config.attempts_dir is not None:
            # Retain each accepted rating before a later rubric can fail.
            self.config.attempts_dir.mkdir(parents=True, exist_ok=True)
            attempt = self.config.attempts_dir / f"{rubric_name}_{uuid.uuid4().hex}.json"
            with attempt.open("x", encoding="utf-8") as stream:
                json.dump({"evaluation": evaluation, "raw_response": raw_response}, stream, indent=2)

        return evaluation

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Extract and validate JSON from LLM response"""
        # Handle markdown code blocks
        if "```json" in response_text:
            # Extract JSON from code block
            parts = response_text.split("```json")
            if len(parts) > 1:
                json_text = parts[1].split("```")[0]
            else:
                json_text = response_text
        elif "```" in response_text:
            # Generic code block
            parts = response_text.split("```")
            if len(parts) >= 3:
                json_text = parts[1]
            else:
                json_text = response_text
        else:
            json_text = response_text

        # Parse JSON
        return json.loads(json_text.strip())

    def export_to_csv(self, results: Dict[str, Any], output_path: Path):
        """Export results to CSV compatible with existing format"""
        rows = []

        for project_method, project_results in results.items():
            project, method = identity_of(project_method, project_results)

            row = {
                "project": project,
                "method": method,
                "label": (project_results.get(IDENTITY) or {}).get("label"),
                "file_path": (project_results.get(IDENTITY) or {}).get("file_path"),
            }

            # Add rubric10 scores
            if "rubric10" in project_results:
                r10 = project_results["rubric10"]
                row["rubric10_total"] = r10["overall_score"]["total_points"]
                row["rubric10_max"] = r10["overall_score"]["max_points"]
                row["rubric10_percentage"] = r10["overall_score"]["percentage"]

            # Add rubric20 scores
            if "rubric20" in project_results:
                r20 = project_results["rubric20"]
                row["rubric20_total"] = r20["overall_score"]["total_points"]
                row["rubric20_max"] = r20["overall_score"]["max_points"]
                row["rubric20_percentage"] = r20["overall_score"]["percentage"]

            for rubric in ("rubric10", "rubric20"):
                if rubric not in project_results:
                    continue
                result = project_results[rubric]
                score = result["overall_score"]
                metadata = result.get("metadata") or {}
                for name in ("fixed_max_points", "fixed_percentage"):
                    row[f"{rubric}_{name}"] = score.get(name)
                row[f"{rubric}_excluded_items"] = json.dumps(score.get("excluded_items", []))
                for name in ("instrument_sha256", "context_sha256", "d4d_file_hash"):
                    row[f"{rubric}_{name}"] = metadata.get(name)
                row[f"{rubric}_scope"] = json.dumps(result.get("evaluation_scope"), sort_keys=True)

            rows.append(row)

        # Write CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', newline='') as f:
            if rows:
                fields = list(dict.fromkeys(key for row in rows for key in row))
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

    def export_to_markdown(
        self,
        results: Dict[str, Any],
        output_path: Path,
        rubric_name: Literal["rubric10", "rubric20"]
    ):
        """Generate detailed Markdown report for a specific rubric"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(f"# D4D {rubric_name.upper()} LLM Evaluation Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Model:** {self.config.model} (temperature={self.config.temperature})\n\n")
            f.write("Fixed and applicability-adjusted scores have different denominators. "
                    "Compare only matching instruments, contexts and excluded-item sets.\n\n")
            f.write("---\n\n")

            # Summary table
            f.write("## Summary\n\n")
            f.write("| Project | Method | Run | Input | Total | Max | Percentage |\n")
            f.write("|---------|--------|-----|-------|-------|-----|------------|\n")

            for project_method, project_results in results.items():
                if rubric_name in project_results:
                    project, method = identity_of(project_method,
                                                  project_results)
                    r = project_results[rubric_name]["overall_score"]
                    percentage = "N/A" if r["percentage"] is None else f"{r['percentage']:.1f}%"
                    run = project_results.get(IDENTITY) or {}
                    f.write(f"| {project} | {method} | {run.get('label') or '—'} | {run.get('file_path') or project_results[rubric_name].get('d4d_file', 'unrecorded')} | {r['total_points']} | {r['max_points']} | {percentage} |\n")

            f.write("\n---\n\n")

            # Detailed analysis
            f.write("## Detailed Analysis\n\n")

            for project_method, project_results in results.items():
                if rubric_name not in project_results:
                    continue

                project, method = identity_of(project_method, project_results)
                result = project_results[rubric_name]

                f.write(f"### {project} - {method}\n\n")

                # Overall score
                score = result["overall_score"]
                percentage = "N/A" if score["percentage"] is None else f"{score['percentage']:.1f}%"
                f.write(f"**Overall Score:** {score['total_points']}/{score['max_points']} ({percentage})\n\n")
                f.write(f"**Fixed maximum:** {score.get('fixed_max_points', 'unrecorded')}; "
                        f"**excluded items:** {', '.join(score.get('excluded_items', [])) or 'none'}\n\n")
                f.write(f"**Instrument:** {result.get('metadata', {}).get('instrument_sha256', 'unrecorded')}\n\n")
                f.write(f"**Context:** {result.get('metadata', {}).get('context_sha256', 'unrecorded')}\n\n")

                # Strengths
                if "assessment" in result and "strengths" in result["assessment"]:
                    f.write("**Strengths:**\n")
                    for strength in result["assessment"]["strengths"]:
                        f.write(f"- {strength}\n")
                    f.write("\n")

                # Weaknesses
                if "assessment" in result and "weaknesses" in result["assessment"]:
                    f.write("**Weaknesses:**\n")
                    for weakness in result["assessment"]["weaknesses"]:
                        f.write(f"- {weakness}\n")
                    f.write("\n")

                # Recommendations
                if "assessment" in result and "recommendations" in result["assessment"]:
                    f.write("**Recommendations:**\n")
                    for rec in result["assessment"]["recommendations"]:
                        f.write(f"- {rec}\n")
                    f.write("\n")

                f.write("---\n\n")

    def export_to_json(self, results: Dict[str, Any], output_path: Path):
        """Save full results as JSON"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate declared D4D records using the direct API judge"
    )

    # Input options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Path to single D4D YAML file")
    group.add_argument("--all", action="store_true", help="Evaluate all D4D files")

    # Evaluation options
    parser.add_argument(
        "--project",
        help="Project name (required if --file is used)"
    )
    parser.add_argument(
        "--method",
        help="Generation method (required if --file is used): curated, gpt5, claudecode, etc."
    )
    parser.add_argument(
        "--rubric",
        choices=["rubric10", "rubric20", "both"],
        default="both",
        help="Which rubric to use (default: both)"
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/evaluation_llm"),
        help="Output directory (default: data/evaluation_llm)"
    )

    parser.add_argument("--context", type=Path, help="YAML/JSON applicability declarations")
    parser.add_argument("--base-dir", type=Path, default=Path("data/d4d_concatenated"),
                        help="Root containing method and optional run-label directories")
    args = parser.parse_args()

    # Validate arguments
    if args.file and (not args.project or not args.method):
        parser.error("--file requires --project and --method")

    # Collect files to evaluate
    if args.file:
        identity(args.project, "project")
        identity(args.method, "method")
        files_to_evaluate = [(args.file, args.project, args.method, None)]
    else:
        files_to_evaluate = []
        method_paths = sorted(path for path in args.base_dir.iterdir() if path.is_dir()) if args.base_dir.is_dir() else []
        for method_path in method_paths:
            if args.method and method_path.name != args.method:
                continue
            for d4d_file in sorted(method_path.rglob("*.yaml")):
                relative = d4d_file.relative_to(method_path)
                if len(relative.parts) > 2:
                    continue
                suffix = next((s for s in ("_d4d_core.yaml", "_d4d.yaml", "_curated.yaml")
                               if d4d_file.name.endswith(s)), None)
                if suffix is None:
                    continue
                project = d4d_file.name[:-len(suffix)]
                if args.project and project != args.project:
                    continue
                files_to_evaluate.append((d4d_file, project, method_path.name,
                                          relative.parts[0] if len(relative.parts) == 2 else None))
    if not files_to_evaluate:
        parser.error("no D4D records matched the selected inputs")
    context = load_context(args.context)
    output_dir = args.output_dir / (
        datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_api-judge-v2_" + uuid.uuid4().hex)
    # Every invocation has its own directory; preserve all earlier evaluations.
    evaluator = D4DLLMEvaluator(LLMEvaluationConfig(error_dir=output_dir / "errors",
                                                  attempts_dir=output_dir / "attempts"), context=context)

    print(f"📊 Found {len(files_to_evaluate)} D4D files to evaluate\n")

    # Evaluate files
    all_results = {}
    failures = 0
    for d4d_file, project, method, label in files_to_evaluate:
        print(f"\n{'='*60}")
        print(f"Evaluating: {project} - {method}")
        print(f"File: {d4d_file}")
        print('='*60)

        try:
            results = evaluator.evaluate_file(d4d_file, project, method, args.rubric)
            # Carried, not re-derived. Both values are in hand here; recovering
            # them later by splitting the key on its first underscore reported
            # AI_READI as project "AI" and VOICE_PEDIATRIC as "VOICE" — merging
            # two datasets the manifest declares distinct (#622).
            results[IDENTITY] = {"project": project, "method": method, "label": label,
                                "file_path": str(d4d_file)}
            all_results[json.dumps([project, method, label, str(d4d_file)])] = results
            evaluator.export_to_json(all_results, output_dir / "scores.json")

            # Print summary
            if "rubric10" in results:
                r10 = results["rubric10"]["overall_score"]
                print(f"✅ Rubric10: {r10['total_points']}/{r10['max_points']}")

            if "rubric20" in results:
                r20 = results["rubric20"]["overall_score"]
                print(f"✅ Rubric20: {r20['total_points']}/{r20['max_points']}")

        except Exception as e:
            failures += 1
            print(f"❌ Evaluation failed: {e}")
            import traceback
            traceback.print_exc()

    # Export results
    if all_results:
        print(f"\n{'='*60}")
        print("📝 Exporting results...")
        print('='*60)

        # Export CSV
        csv_path = output_dir / "scores.csv"
        evaluator.export_to_csv(all_results, csv_path)
        print(f"✅ CSV exported to: {csv_path}")

        # Export JSON
        json_path = output_dir / "scores.json"
        evaluator.export_to_json(all_results, json_path)
        print(f"✅ JSON exported to: {json_path}")

        # Export Markdown reports
        if args.rubric in ["rubric10", "both"]:
            md_path = output_dir / "rubric10" / "summary_report.md"
            evaluator.export_to_markdown(all_results, md_path, "rubric10")
            print(f"✅ Rubric10 report exported to: {md_path}")

        if args.rubric in ["rubric20", "both"]:
            md_path = output_dir / "rubric20" / "summary_report.md"
            evaluator.export_to_markdown(all_results, md_path, "rubric20")
            print(f"✅ Rubric20 report exported to: {md_path}")

        print(f"\n✨ Evaluation complete! Results saved to {output_dir}")
    else:
        print("\n⚠️  No results to export")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
