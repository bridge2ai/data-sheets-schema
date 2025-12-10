#!/usr/bin/env python3
"""
Compare LLM-based evaluation with presence-based evaluation

This script compares the results of:
1. LLM-as-judge evaluation (quality-based assessment)
2. Presence-based evaluation (field existence detection)

Generates comparison tables and identifies cases where presence=1 but quality is low.

Usage:
    python src/evaluation/compare_evaluation_methods.py \\
      --llm-dir data/evaluation_llm \\
      --presence-dir data/evaluation \\
      --output-dir data/evaluation_comparison

Author: Claude Code
Date: 2025-12-06
"""

import argparse
import json
import csv
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ComparisonResult:
    """Comparison between LLM and presence-based evaluation"""
    project: str
    method: str
    rubric: str
    presence_score: float
    presence_percentage: float
    llm_score: float
    llm_percentage: float
    delta_percentage: float  # LLM - Presence
    quality_insights: List[str]


class EvaluationComparator:
    """Compare LLM-based and presence-based evaluations"""

    def __init__(self, llm_dir: Path, presence_dir: Path):
        self.llm_dir = llm_dir
        self.presence_dir = presence_dir

    def load_llm_scores(self) -> Dict[str, Any]:
        """Load LLM evaluation scores from JSON"""
        scores_path = self.llm_dir / "scores.json"
        if not scores_path.exists():
            raise FileNotFoundError(f"LLM scores not found: {scores_path}")

        with open(scores_path) as f:
            return json.load(f)

    def load_presence_scores(self) -> Dict[str, Any]:
        """Load presence-based evaluation scores from JSON"""
        scores_path = self.presence_dir / "scores.json"
        if not scores_path.exists():
            raise FileNotFoundError(f"Presence scores not found: {scores_path}")

        with open(scores_path) as f:
            return json.load(f)

    def compare(self) -> List[ComparisonResult]:
        """Compare LLM and presence evaluations"""
        llm_scores = self.load_llm_scores()
        presence_scores = self.load_presence_scores()

        results = []

        # Compare each project/method combination
        for project_method in llm_scores.keys():
            project, method = project_method.split("_", 1)

            # Find matching presence evaluation
            presence_key = None
            for key in presence_scores.keys():
                if key.startswith(f"{project}_") and method in key:
                    presence_key = key
                    break

            if not presence_key:
                print(f"⚠️  No matching presence evaluation for {project_method}")
                continue

            llm = llm_scores[project_method]
            presence = presence_scores[presence_key]

            # Compare rubric10
            if "rubric10" in llm and "rubric10" in presence:
                delta = llm["rubric10"]["overall_score"]["percentage"] - presence["rubric10"]["percentage"]

                results.append(ComparisonResult(
                    project=project,
                    method=method,
                    rubric="rubric10",
                    presence_score=presence["rubric10"]["total"],
                    presence_percentage=presence["rubric10"]["percentage"],
                    llm_score=llm["rubric10"]["overall_score"]["total_points"],
                    llm_percentage=llm["rubric10"]["overall_score"]["percentage"],
                    delta_percentage=delta,
                    quality_insights=llm["rubric10"].get("assessment", {}).get("weaknesses", [])
                ))

            # Compare rubric20
            if "rubric20" in llm and "rubric20" in presence:
                delta = llm["rubric20"]["overall_score"]["percentage"] - presence["rubric20"]["percentage"]

                results.append(ComparisonResult(
                    project=project,
                    method=method,
                    rubric="rubric20",
                    presence_score=presence["rubric20"]["total"],
                    presence_percentage=presence["rubric20"]["percentage"],
                    llm_score=llm["rubric20"]["overall_score"]["total_points"],
                    llm_percentage=llm["rubric20"]["overall_score"]["percentage"],
                    delta_percentage=delta,
                    quality_insights=llm["rubric20"].get("assessment", {}).get("weaknesses", [])
                ))

        return results

    def export_to_csv(self, results: List[ComparisonResult], output_path: Path):
        """Export comparison to CSV"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Project", "Method", "Rubric",
                "Presence Score", "Presence %",
                "LLM Score", "LLM %",
                "Delta %"
            ])

            for r in results:
                writer.writerow([
                    r.project, r.method, r.rubric,
                    f"{r.presence_score:.1f}", f"{r.presence_percentage:.1f}",
                    f"{r.llm_score:.1f}", f"{r.llm_percentage:.1f}",
                    f"{r.delta_percentage:+.1f}"
                ])

    def export_to_markdown(self, results: List[ComparisonResult], output_path: Path):
        """Generate detailed Markdown comparison report"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write("# LLM vs Presence-Based Evaluation Comparison\n\n")
            f.write("This report compares quality-based LLM evaluation with field-presence detection.\n\n")
            f.write("---\n\n")

            # Summary table
            f.write("## Summary Table\n\n")
            f.write("| Project | Method | Rubric | Presence % | LLM % | Delta |\n")
            f.write("|---------|--------|--------|------------|-------|-------|\n")

            for r in results:
                delta_sign = "📈" if r.delta_percentage > 0 else "📉" if r.delta_percentage < 0 else "➡️"
                f.write(
                    f"| {r.project} | {r.method} | {r.rubric} | "
                    f"{r.presence_percentage:.1f}% | {r.llm_percentage:.1f}% | "
                    f"{delta_sign} {r.delta_percentage:+.1f}% |\n"
                )

            f.write("\n---\n\n")

            # Key insights
            f.write("## Key Insights\n\n")

            # Find largest positive deltas (LLM scored higher)
            positive_deltas = sorted(
                [r for r in results if r.delta_percentage > 10],
                key=lambda x: x.delta_percentage,
                reverse=True
            )

            if positive_deltas:
                f.write("### Cases Where LLM Scored Higher (Quality > Presence)\n\n")
                for r in positive_deltas[:5]:
                    f.write(f"**{r.project} - {r.method} ({r.rubric}): +{r.delta_percentage:.1f}%**\n")
                    f.write("- Presence-based evaluation likely gave credit for incomplete fields\n")
                    f.write("- LLM detected higher quality content\n\n")

            # Find largest negative deltas (Presence scored higher)
            negative_deltas = sorted(
                [r for r in results if r.delta_percentage < -10],
                key=lambda x: x.delta_percentage
            )

            if negative_deltas:
                f.write("### Cases Where Presence Scored Higher (Presence > Quality)\n\n")
                f.write("*These are the most important findings - fields exist but quality is low*\n\n")

                for r in negative_deltas[:5]:
                    f.write(f"**{r.project} - {r.method} ({r.rubric}): {r.delta_percentage:.1f}%**\n")
                    f.write(f"- Fields exist (presence={r.presence_percentage:.1f}%) but quality is low (LLM={r.llm_percentage:.1f}%)\n")

                    if r.quality_insights:
                        f.write("- Quality issues identified by LLM:\n")
                        for insight in r.quality_insights[:3]:
                            f.write(f"  - {insight}\n")
                    f.write("\n")

            f.write("---\n\n")

            # Methodology
            f.write("## Methodology\n\n")
            f.write("**Presence-Based Evaluation:**\n")
            f.write("- Binary field detection (exists/doesn't exist)\n")
            f.write("- Fast, free, good for CI/CD\n")
            f.write("- Doesn't assess content quality\n\n")

            f.write("**LLM Quality Assessment:**\n")
            f.write("- Reads and assesses content quality\n")
            f.write("- Evaluates completeness, actionability, usefulness\n")
            f.write("- Slower, costs money, provides deep insights\n")
            f.write("- Temperature 0.5 for reproducible quality judgments\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compare LLM-based evaluation with presence-based evaluation"
    )

    parser.add_argument(
        "--llm-dir",
        type=Path,
        default=Path("data/evaluation_llm"),
        help="Directory with LLM evaluation results (default: data/evaluation_llm)"
    )
    parser.add_argument(
        "--presence-dir",
        type=Path,
        default=Path("data/evaluation"),
        help="Directory with presence evaluation results (default: data/evaluation)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/evaluation_comparison"),
        help="Output directory (default: data/evaluation_comparison)"
    )

    args = parser.parse_args()

    print("🔍 Comparing LLM vs Presence-based evaluations...\n")

    # Initialize comparator
    comparator = EvaluationComparator(args.llm_dir, args.presence_dir)

    # Compare
    results = comparator.compare()

    print(f"📊 Compared {len(results)} evaluation results\n")

    # Export
    csv_path = args.output_dir / "comparison.csv"
    comparator.export_to_csv(results, csv_path)
    print(f"✅ CSV exported to: {csv_path}")

    md_path = args.output_dir / "comparison_report.md"
    comparator.export_to_markdown(results, md_path)
    print(f"✅ Markdown report exported to: {md_path}")

    print(f"\n✨ Comparison complete! Results saved to {args.output_dir}")


if __name__ == "__main__":
    main()
