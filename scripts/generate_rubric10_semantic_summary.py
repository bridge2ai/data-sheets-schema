#!/usr/bin/env python3
"""
Generate summary outputs for rubric10-semantic evaluation.
Reads all evaluation JSON files and generates:
1. evaluation_summary.yaml (D4D_Evaluation_Summary schema)
2. all_scores.csv
3. summary_report.md
"""

import json
import csv
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
eval_dir = Path("data/evaluation_llm/rubric10_semantic/concatenated")
output_dir = Path("data/evaluation_llm/rubric10_semantic")

# Read all evaluation files
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

        evaluations.append({
            "file": json_file.name,
            "project": project,
            "method": method,
            "data": data
        })

# Extract scores
scores_data = []
for ev in evaluations:
    data = ev["data"]

    # Handle both output formats
    if "summary_scores" in data:
        total_score = data["summary_scores"]["total_score"]
        # Handle variations in max_score key name
        if "total_max_score" in data["summary_scores"]:
            max_score = data["summary_scores"]["total_max_score"]
        elif "max_possible_score" in data["summary_scores"]:
            max_score = data["summary_scores"]["max_possible_score"]
        else:
            max_score = 50  # Default
        # Handle variations in percentage key name
        if "overall_percentage" in data["summary_scores"]:
            percentage = data["summary_scores"]["overall_percentage"]
        elif "percentage" in data["summary_scores"]:
            percentage = data["summary_scores"]["percentage"]
        else:
            percentage = (total_score / max_score) * 100
    elif "scoring_summary" in data:
        total_score = data["scoring_summary"]["total_score"]
        max_score = data["scoring_summary"].get("max_score", 50)
        percentage = data["scoring_summary"]["percentage"]
    else:
        print(f"Warning: Could not find scores in {ev['file']}")
        continue

    # Count consistency checks
    consistency_checks = data["semantic_analysis"].get("consistency_checks", {})
    total_checks = len(consistency_checks)
    consistency_passed = sum(1 for v in consistency_checks.values() if isinstance(v, dict) and v.get("consistency") == "consistent")

    # Count issues from completeness_gaps
    completeness_gaps = data["semantic_analysis"].get("completeness_gaps", {})
    total_issues = (
        len(completeness_gaps.get("high_priority_missing", [])) +
        len(completeness_gaps.get("medium_priority_missing", [])) +
        len(completeness_gaps.get("low_priority_missing", []))
    )

    scores_data.append({
        "project": ev["project"],
        "method": ev["method"],
        "file": ev["file"],
        "total_score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "consistency_checks": total_checks,
        "consistency_passed": consistency_passed,
        "issues_detected": total_issues
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

# Element performance (average across all files)
element_scores = defaultdict(list)
for ev in evaluations:
    data = ev["data"]

    # Handle both output formats
    if "element_scores" in data:
        elements = data["element_scores"]
        id_key = "element_id"
        score_key = "element_score"
        name_key = "element_name"
    elif "detailed_scores" in data:
        elements = data["detailed_scores"]
        id_key = "element"
        score_key = "score"
        name_key = "name"
    else:
        continue

    for elem in elements:
        element_scores[elem[id_key]].append({
            "score": elem[score_key],
            "name": elem[name_key]
        })

element_performance = []
for elem_id, scores in sorted(element_scores.items()):
    element_performance.append({
        "element_id": str(elem_id),
        "element_name": scores[0]["name"],
        "average_score": sum(s["score"] for s in scores) / len(scores),
        "max_score": 5,
        "average_percentage": (sum(s["score"] for s in scores) / len(scores)) / 5 * 100
    })

# Collect completeness gaps from semantic analysis
all_high_priority_gaps = defaultdict(int)
all_medium_priority_gaps = defaultdict(int)
all_low_priority_gaps = defaultdict(int)

for ev in evaluations:
    gaps = ev["data"]["semantic_analysis"].get("completeness_gaps", {})
    for gap in gaps.get("high_priority_missing", []):
        all_high_priority_gaps[gap] += 1
    for gap in gaps.get("medium_priority_missing", []):
        all_medium_priority_gaps[gap] += 1
    for gap in gaps.get("low_priority_missing", []):
        all_low_priority_gaps[gap] += 1

# Collect strengths and weaknesses
all_strengths = defaultdict(int)
all_weaknesses = defaultdict(int)

for ev in evaluations:
    semantic = ev["data"]["semantic_analysis"]
    for strength in semantic.get("strengths", []):
        all_strengths[strength] += 1
    for weakness in semantic.get("weaknesses", []):
        all_weaknesses[weakness] += 1

# Generate evaluation_summary.yaml
eval_summary = {
    "id": f"rubric10_semantic_evaluation_{datetime.now().strftime('%Y_%m_%d')}",
    "rubric_type": "rubric10",
    "rubric_description": "10-element hierarchical rubric with semantic analysis: binary scoring (0/1), maximum 50 points, enhanced with correctness validation, consistency checking, and semantic understanding assessment",
    "total_files_evaluated": total_files,
    "evaluation_date": datetime.now().isoformat(),
    "overall_performance": {
        "average_score": round(avg_score, 1),
        "max_score": 50,
        "average_percentage": round(avg_pct, 1),
        "best_score": best["total_score"],
        "worst_score": worst["total_score"],
        "best_performer": {
            "file": best["file"],
            "method": best["method"],
            "project": best["project"],
            "score": best["total_score"],
            "percentage": best["percentage"]
        },
        "worst_performer": {
            "file": worst["file"],
            "method": worst["method"],
            "project": worst["project"],
            "score": worst["total_score"],
            "percentage": worst["percentage"]
        }
    },
    "method_comparison": method_comparison,
    "project_comparison": project_comparison,
    "element_performance": element_performance,
    "common_strengths": [
        {"description": strength, "frequency": freq}
        for strength, freq in sorted(all_strengths.items(), key=lambda x: -x[1])[:5]
    ],
    "common_weaknesses": [
        {"description": weakness, "frequency": freq, "severity": "high" if freq > 8 else "medium" if freq > 4 else "low"}
        for weakness, freq in sorted(all_weaknesses.items(), key=lambda x: -x[1])[:5]
    ],
    "key_insights": [
        {"insight": "Semantic evaluation includes identifier validation, consistency checking, and completeness gap analysis", "impact": "high"},
        {"insight": f"{method_comparison[0]['method']} method achieved highest average score ({method_comparison[0]['average_percentage']:.1f}%)", "impact": "high"},
        {"insight": f"{project_comparison[0]['project']} project scored highest on average ({project_comparison[0]['average_percentage']:.1f}%)", "impact": "medium"},
        {"insight": f"Average consistency check pass rate across all files: {sum(s['consistency_passed'] for s in scores_data) / sum(s['consistency_checks'] for s in scores_data) * 100:.1f}%", "impact": "medium"},
        {"insight": f"Most common high-priority gap: {max(all_high_priority_gaps.items(), key=lambda x: x[1])[0] if all_high_priority_gaps else 'None'}", "impact": "high"}
    ],
    "semantic_analysis_summary": {
        "total_gaps_detected": sum(s["issues_detected"] for s in scores_data),
        "gap_breakdown": {
            "high_priority": len(all_high_priority_gaps),
            "medium_priority": len(all_medium_priority_gaps),
            "low_priority": len(all_low_priority_gaps)
        },
        "common_high_priority_gaps": [
            {"description": gap, "frequency": freq, "severity": "high"}
            for gap, freq in sorted(all_high_priority_gaps.items(), key=lambda x: -x[1])[:5]
        ],
        "common_medium_priority_gaps": [
            {"description": gap, "frequency": freq, "severity": "medium"}
            for gap, freq in sorted(all_medium_priority_gaps.items(), key=lambda x: -x[1])[:5]
        ],
        "semantic_quality_insights": [
            f"Most consistent field across all files: {method_comparison[0]['method']} generation method",
            f"Average completeness gaps per file: {sum(s['issues_detected'] for s in scores_data) / total_files:.1f}",
            f"High-priority gaps appear in {sum(1 for s in scores_data if s['issues_detected'] > 0)} of {total_files} files",
            "Semantic analysis reveals patterns in identifier validation, grant format checking, and IRB documentation"
        ]
    }
}

# Write evaluation_summary.yaml
with open(output_dir / "evaluation_summary.yaml", "w") as f:
    yaml.dump(eval_summary, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

print(f"✅ Generated: {output_dir / 'evaluation_summary.yaml'}")

# Generate all_scores.csv
with open(output_dir / "all_scores.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "project", "method", "file", "total_score", "max_score", "percentage",
        "consistency_checks", "consistency_passed", "issues_detected"
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
    f.write(f"- **Worst Performer:** {worst['project']} {worst['method']} - {worst['total_score']}/50 ({worst['percentage']:.1f}%)\n")
    f.write(f"- **Total Semantic Issues Detected:** {len(all_issues)}\n\n")

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

    f.write("## Element Performance\n\n")
    f.write("| Element | Name | Avg Score | Avg % |\n")
    f.write("|---------|------|-----------|-------|\n")
    for ep in element_performance:
        f.write(f"| {ep['element_id']} | {ep['element_name']} | {ep['average_score']:.1f}/5 | {ep['average_percentage']:.1f}% |\n")
    f.write("\n")

    f.write("## Semantic Analysis Highlights\n\n")
    f.write(f"**Total Completeness Gaps Detected:** {sum(s['issues_detected'] for s in scores_data)}\n\n")
    f.write("**Gap Breakdown by Priority:**\n\n")
    f.write(f"- **High Priority:** {len(all_high_priority_gaps)} unique gaps\n")
    f.write(f"- **Medium Priority:** {len(all_medium_priority_gaps)} unique gaps\n")
    f.write(f"- **Low Priority:** {len(all_low_priority_gaps)} unique gaps\n")
    f.write("\n")

    if all_high_priority_gaps:
        f.write("**Top High-Priority Gaps:**\n\n")
        for gap, freq in sorted(all_high_priority_gaps.items(), key=lambda x: -x[1])[:5]:
            f.write(f"- {gap} ({freq} files)\n")
        f.write("\n")

    if all_weaknesses:
        f.write("**Most Common Weaknesses:**\n\n")
        for weakness, freq in sorted(all_weaknesses.items(), key=lambda x: -x[1])[:5]:
            f.write(f"- {weakness} ({freq} files)\n")
        f.write("\n")

    f.write("## Detailed Scores by Project and Method\n\n")
    for project in sorted(set(s["project"] for s in scores_data)):
        f.write(f"### {project}\n\n")
        f.write("| Method | Score | % | Consistency Checks | Gaps |\n")
        f.write("|--------|-------|---|-------------------|------|\n")
        for s in sorted([s for s in scores_data if s["project"] == project], key=lambda x: -x["total_score"]):
            consistency_rate = f"{s['consistency_passed']}/{s['consistency_checks']}" if s['consistency_checks'] > 0 else "N/A"
            f.write(f"| {s['method']} | {s['total_score']}/50 | {s['percentage']:.1f}% | {consistency_rate} | {s['issues_detected']} |\n")
        f.write("\n")

print(f"✅ Generated: {output_dir / 'summary_report.md'}")
print("\n🎉 All summary outputs generated successfully!")
