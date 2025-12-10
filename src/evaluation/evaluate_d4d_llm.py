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


@dataclass
class LLMEvaluationConfig:
    """Configuration for LLM-based evaluation"""
    model: str = "claude-sonnet-4-5-20250929"  # Date-pinned for determinism
    temperature: float = 0.0  # Fully deterministic evaluation
    max_tokens: int = 8000
    rubric_dir: Path = Path("data/rubric")
    prompts_dir: Path = Path("src/download/prompts")
    schema_path: Path = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")


class D4DLLMEvaluator:
    """LLM-as-judge evaluator for D4D files using Claude Sonnet 4.5"""

    def __init__(self, config: Optional[LLMEvaluationConfig] = None):
        self.config = config or LLMEvaluationConfig()

        # Initialize Anthropic client
        try:
            self.client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
        except Exception as e:
            raise RuntimeError(
                "Failed to initialize Anthropic client. "
                "Please set ANTHROPIC_API_KEY environment variable."
            ) from e

        # Load rubrics
        self.rubric10 = self._load_rubric("rubric10.txt")
        self.rubric20 = self._load_rubric("rubric20.txt")

        # Load prompts
        self.rubric10_system_prompt = self._load_prompt("rubric10_system_prompt.md")
        self.rubric20_system_prompt = self._load_prompt("rubric20_system_prompt.md")

    def _load_rubric(self, filename: str) -> Dict[str, Any]:
        """Load and parse rubric YAML"""
        path = self.config.rubric_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Rubric file not found: {path}")

        with open(path) as f:
            return yaml.safe_load(f)

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
        return f"sha256:{sha256.hexdigest()[:16]}..."  # Truncated for readability

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

    def _build_user_prompt(self, d4d_content: str, project: str, method: str, d4d_filename: str) -> str:
        """Construct user prompt with D4D file to evaluate"""
        return f"""Evaluate this D4D datasheet for quality and completeness.

**Project:** {project}
**Generation Method:** {method}
**Filename:** {d4d_filename}

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
            project: Project name (AI_READI, CHORUS, CM4AI, VOICE)
            method: Generation method (curated, gpt5, claudecode, etc.)
            rubric: Which rubric to use ("rubric10", "rubric20", or "both")

        Returns:
            Dictionary with evaluation results for requested rubric(s)
        """
        # Load D4D file
        if not d4d_path.exists():
            raise FileNotFoundError(f"D4D file not found: {d4d_path}")

        with open(d4d_path) as f:
            d4d_content = f.read()

        # Calculate file hash
        d4d_file_hash = self._calculate_file_hash(d4d_path)

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
        # Build prompts
        system_prompt = self._build_system_prompt(rubric_name)
        user_prompt = self._build_user_prompt(d4d_content, project, method, d4d_filename)

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

        # Parse response
        try:
            evaluation = self._parse_llm_response(response.content[0].text)
        except Exception as e:
            # Save failed response for debugging
            error_file = Path(f"evaluation_error_{rubric_name}_{project}_{method}.txt")
            with open(error_file, 'w') as f:
                f.write(f"Error: {e}\n\n")
                f.write(f"Response:\n{response.content[0].text}")
            raise RuntimeError(
                f"Failed to parse LLM response. Response saved to {error_file}"
            ) from e

        # Add metadata
        evaluation["metadata"] = {
            "evaluator_id": str(uuid.uuid4()),
            "rubric_hash": self._calculate_file_hash(self.config.rubric_dir / f"{rubric_name}.txt"),
            "d4d_file_hash": d4d_file_hash
        }

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
            project, method = project_method.split("_", 1)

            row = {
                "project": project,
                "method": method,
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

            rows.append(row)

        # Write CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', newline='') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
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
            f.write(f"**Model:** claude-sonnet-4-5-20250929 (temperature=0.0)\n\n")
            f.write("---\n\n")

            # Summary table
            f.write("## Summary\n\n")
            f.write("| Project | Method | Total | Max | Percentage |\n")
            f.write("|---------|--------|-------|-----|------------|\n")

            for project_method, project_results in results.items():
                if rubric_name in project_results:
                    project, method = project_method.split("_", 1)
                    r = project_results[rubric_name]["overall_score"]
                    f.write(f"| {project} | {method} | {r['total_points']} | {r['max_points']} | {r['percentage']:.1f}% |\n")

            f.write("\n---\n\n")

            # Detailed analysis
            f.write("## Detailed Analysis\n\n")

            for project_method, project_results in results.items():
                if rubric_name not in project_results:
                    continue

                project, method = project_method.split("_", 1)
                result = project_results[rubric_name]

                f.write(f"### {project} - {method}\n\n")

                # Overall score
                score = result["overall_score"]
                f.write(f"**Overall Score:** {score['total_points']}/{score['max_points']} ({score['percentage']:.1f}%)\n\n")

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
        description="Evaluate D4D YAML files using LLM-as-judge (Claude Sonnet 4.5)"
    )

    # Input options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Path to single D4D YAML file")
    group.add_argument("--all", action="store_true", help="Evaluate all D4D files")

    # Evaluation options
    parser.add_argument(
        "--project",
        choices=["AI_READI", "CHORUS", "CM4AI", "VOICE"],
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

    args = parser.parse_args()

    # Validate arguments
    if args.file and (not args.project or not args.method):
        parser.error("--file requires --project and --method")

    # Initialize evaluator
    print("🚀 Initializing D4D LLM Evaluator...")
    evaluator = D4DLLMEvaluator()

    # Collect files to evaluate
    if args.file:
        files_to_evaluate = [(args.file, args.project, args.method)]
    else:
        # Find all D4D files
        files_to_evaluate = []
        base_dir = Path("data/d4d_concatenated")

        for method_dir in ["curated", "gpt5", "claudecode", "claudecode_agent", "claudecode_assistant"]:
            method_path = base_dir / method_dir
            if not method_path.exists():
                continue

            for d4d_file in method_path.glob("*_d4d.yaml"):
                project = d4d_file.stem.replace("_d4d", "")
                files_to_evaluate.append((d4d_file, project, method_dir))

    print(f"📊 Found {len(files_to_evaluate)} D4D files to evaluate\n")

    # Evaluate files
    all_results = {}
    for d4d_file, project, method in files_to_evaluate:
        print(f"\n{'='*60}")
        print(f"Evaluating: {project} - {method}")
        print(f"File: {d4d_file}")
        print('='*60)

        try:
            results = evaluator.evaluate_file(d4d_file, project, method, args.rubric)
            all_results[f"{project}_{method}"] = results

            # Print summary
            if "rubric10" in results:
                r10 = results["rubric10"]["overall_score"]
                print(f"✅ Rubric10: {r10['total_points']}/{r10['max_points']} ({r10['percentage']:.1f}%)")

            if "rubric20" in results:
                r20 = results["rubric20"]["overall_score"]
                print(f"✅ Rubric20: {r20['total_points']}/{r20['max_points']} ({r20['percentage']:.1f}%)")

        except Exception as e:
            print(f"❌ Evaluation failed: {e}")
            import traceback
            traceback.print_exc()

    # Export results
    if all_results:
        print(f"\n{'='*60}")
        print("📝 Exporting results...")
        print('='*60)

        # Export CSV
        csv_path = args.output_dir / "scores.csv"
        evaluator.export_to_csv(all_results, csv_path)
        print(f"✅ CSV exported to: {csv_path}")

        # Export JSON
        json_path = args.output_dir / "scores.json"
        evaluator.export_to_json(all_results, json_path)
        print(f"✅ JSON exported to: {json_path}")

        # Export Markdown reports
        if args.rubric in ["rubric10", "both"]:
            md_path = args.output_dir / "rubric10" / "summary_report.md"
            evaluator.export_to_markdown(all_results, md_path, "rubric10")
            print(f"✅ Rubric10 report exported to: {md_path}")

        if args.rubric in ["rubric20", "both"]:
            md_path = args.output_dir / "rubric20" / "summary_report.md"
            evaluator.export_to_markdown(all_results, md_path, "rubric20")
            print(f"✅ Rubric20 report exported to: {md_path}")

        print(f"\n✨ Evaluation complete! Results saved to {args.output_dir}")
    else:
        print("\n⚠️  No results to export")


if __name__ == "__main__":
    main()
