#!/usr/bin/env python3
"""
Generate basic summary outputs for rubric10-semantic evaluation.
This version handles multiple JSON output formats from different agents.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
eval_dir = Path("data/evaluation_llm/rubric10_semantic/concatenated")
output_dir = Path("data/evaluation_llm/rubric10_semantic")

# Read all evaluation files and extract scores (handling format variations)
evaluations = []
for json_file in sorted(eval_dir.glob("*.json")):
    with open(json_file) as f:
        data = json.load(f)

        # Parse filename: PROJECT_METHOD_evaluation.json
        parts = json_file.stem.replace("_evaluation", "").split("_")
        if len(parts) >= 2:
            project = parts[0]
            method = "_".join(parts[1:])
        else:
            project = parts[0]
            method = "unknown"

        # Extract scores - try multiple format variations
        total_score = None
        max_score = 50
        percentage = None

        # Format 1: summary_scores
        if "summary_scores" in data:
            total_score = data["summary_scores"].get("total_score")
            max_score = data["summary_scores"].get("total_max_score",
                data["summary_scores"].get("max_possible_score", 50))
            percentage = data["summary_scores"].get("overall_percentage",
                data["summary_scores"].get("percentage"))

        # Format 2: scoring_summary
        elif "scoring_summary" in data:
            total_score = data["scoring_summary"].get("total_score")
            max_score = data["scoring_summary"].get("max_score", 50)
            percentage = data["scoring_summary"].get("percentage")

        # Format 3: summary
        elif "summary" in data:
            summary = data["summary"]
            total_score = summary.get("total_score", summary.get("overall_score"))
            max_score = summary.get("max_score", summary.get("max_possible_score", 50))
            percentage = summary.get("percentage", summary.get("overall_percentage"))

        # Format 4: scores
        elif "scores" in data:
            scores = data["scores"]
            if isinstance(scores, dict):
                total_score = scores.get("total", scores.get("overall"))
                max_score = scores.get("max", 50)
                percentage = scores.get("percentage")

        # Format 5: summary_statistics
        elif "summary_statistics" in data:
            stats = data["summary_statistics"]
            total_score = stats.get("total_score")
            max_score = stats.get("max_score", 50)
            percentage = stats.get("percentage")

        # Calculate percentage if not provided
        if total_score and percentage is None:
            percentage = (total_score / max_score) * 100

        if total_score is not None:
            evaluations.append({
                "file": json_file.name,
                "project": project,
                "method": method,
                "total_score": total_score,
                "max_score": max_score,
                "percentage": percentage,
                "data": data
            })
        else:
            print(f"Warning: Could not extract score from {json_file.name}")

if not evaluations:
    print("❌ No evaluation files could be processed!")
    exit(1)

print(f"✅ Processed {len(evaluations)} evaluation files")

# Extract scores for CSV
scores_data = []
for ev in evaluations:
    scores_data.append({
        "project": ev["project"],
        "method": ev["method"],
        "file": ev["file"],
        "total_score": ev["total_score"],
        "max_score": ev["max_score"],
        "percentage": round(ev["percentage"], 1)
    })

# Calculate statistics
total_files = len(scores_data)
avg_score = sum(s["total_score"] for s in scores_data) / total_files
avg_pct = sum(s["percentage"] for s in scores_data) / total_files
best = max(scores_data, key=lambda x: x["total_score"])
worst = min(scores_data, key=lambda x: x["total_score"])

# Method comparison
method_stats = defaultdict(lambda: {"scores": [], "files": []})
for s in scores_data:
    method_stats[s["method"]]["scores"].append(s["total_score"])
    method_stats[s["method"]]["files"].append(s["file"])

method_comparison = []
for method, stats in method_stats.items():
    method_comparison.append({
        "method": method,
        "file_count": len(stats["scores"]),
        "average_score": sum(stats["scores"]) / len(stats["scores"]),
        "average_percentage": (sum(stats["scores"]) / len(stats["scores"])) / 50 * 100
    })
method_comparison.sort(key=lambda x: x["average_score"], reverse=True)
for rank, mc in enumerate(method_comparison, 1):
    mc["rank"] = rank

# Project comparison
project_stats = defaultdict(lambda: {"scores": [], "files": []})
for s in scores_data:
    project_stats[s["project"]]["scores"].append(s["total_score"])
    project_stats[s["project"]]["files"].append(s["file"])

project_comparison = []
for project, stats in project_stats.items():
    project_comparison.append({
        "project": project,
        "file_count": len(stats["scores"]),
        "average_score": sum(stats["scores"]) / len(stats["scores"]),
        "average_percentage": (sum(stats["scores"]) / len(stats["scores"])) / 50 * 100
    })
project_comparison.sort(key=lambda x: x["average_score"], reverse=True)
for rank, pc in enumerate(project_comparison, 1):
    pc["rank"] = rank

# Generate all_scores.csv
with open(output_dir / "all_scores.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "project", "method", "file", "total_score", "max_score", "percentage"
    ])
    writer.writeheader()
    writer.writerows(scores_data)

print(f"✅ Generated: {output_dir / 'all_scores.csv'}")

# Generate summary_report.md
with open(output_dir / "summary_report.md", "w") as f:
    f.write("# Rubric10-Semantic Evaluation Summary Report\n\n")
    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"**Total Files Evaluated:** {total_files}\n\n")

    f.write("## Executive Summary\n\n")
    f.write(f"- **Average Score:** {avg_score:.1f}/50 ({avg_pct:.1f}%)\n")
    f.write(f"- **Best Performer:** {best['project']} {best['method']} - {best['total_score']}/50 ({best['percentage']:.1f}%)\n")
    f.write(f"- **Worst Performer:** {worst['project']} {worst['method']} - {worst['total_score']}/50 ({worst['percentage']:.1f}%)\n\n")

    f.write("## Method Comparison\n\n")
    f.write("| Rank | Method | Files | Avg Score | Avg % |\n")
    f.write("|------|--------|-------|-----------|-------|\n")
    for mc in method_comparison:
        f.write(f"| {mc['rank']} | {mc['method']} | {mc['file_count']} | {mc['average_score']:.1f}/50 | {mc['average_percentage']:.1f}% |\n")
    f.write("\n")

    f.write("## Project Comparison\n\n")
    f.write("| Rank | Project | Files | Avg Score | Avg % |\n")
    f.write("|------|---------|-------|-----------|-------|\n")
    for pc in project_comparison:
        f.write(f"| {pc['rank']} | {pc['project']} | {pc['file_count']} | {pc['average_score']:.1f}/50 | {pc['average_percentage']:.1f}% |\n")
    f.write("\n")

    f.write("## Detailed Scores by Project and Method\n\n")
    for project in sorted(set(s["project"] for s in scores_data)):
        f.write(f"### {project}\n\n")
        f.write("| Method | Score | % |\n")
        f.write("|--------|-------|---|\n")
        for s in sorted([s for s in scores_data if s["project"] == project], key=lambda x: -x["total_score"]):
            f.write(f"| {s['method']} | {s['total_score']}/50 | {s['percentage']:.1f}% |\n")
        f.write("\n")

print(f"✅ Generated: {output_dir / 'summary_report.md'}")
print("\n🎉 Summary outputs generated successfully!")
print("\nNote: This is a simplified summary due to varying output formats from different evaluation agents.")
print("For detailed semantic analysis, please review individual evaluation JSON files.")
