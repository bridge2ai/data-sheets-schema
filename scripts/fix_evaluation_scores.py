#!/usr/bin/env python3
"""
Fix scoring errors in rubric20-semantic evaluation JSON files.

This script recalculates the overall_score.total_points and percentage
by summing all question scores in the evaluation. This corrects LLM
calculation errors.

Usage:
    poetry run python scripts/fix_evaluation_scores.py [--dry-run] [--input-dir DIR]

Options:
    --dry-run       Show what would be fixed without modifying files
    --input-dir     Directory containing evaluation JSON files
                    (default: data/evaluation_llm/rubric20_semantic/concatenated)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import argparse


def calculate_total_score(eval_data: Dict) -> Tuple[float, float]:
    """
    Calculate total score from all questions.

    Returns:
        (total_points, max_points): Sum of all question scores and max scores
    """
    total_points = 0.0
    max_points = 0.0

    for category in eval_data.get("categories", []):
        for question in category.get("questions", []):
            total_points += float(question.get("score", 0))
            max_points += float(question.get("max_score", 0))

    return total_points, max_points


def fix_evaluation_scores(eval_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Fix overall_score in an evaluation JSON file.

    Returns:
        (modified, message): Whether file was modified and a status message
    """
    # Load evaluation
    with open(eval_path, 'r') as f:
        eval_data = json.load(f)

    # Fix missing or null required fields (if file is in rubric20_semantic directory)
    fields_fixed = False
    if "rubric20_semantic" in str(eval_path):
        # Infer project and method from filename if needed
        # Pattern: {PROJECT}_{METHOD}_evaluation.json
        filename = eval_path.stem  # e.g., "CHORUS_claudecode_agent_evaluation"
        if filename.endswith("_evaluation"):
            parts = filename.replace("_evaluation", "").split("_")
            # parts = ["CHORUS", "claudecode", "agent"]
            inferred_project = parts[0] if len(parts) >= 1 else "unknown"
            inferred_method = "_".join(parts[1:]) if len(parts) > 1 else "unknown"
        else:
            inferred_project = "unknown"
            inferred_method = "unknown"

        # Fix rubric field
        if eval_data.get("rubric") is None:
            eval_data["rubric"] = "rubric20-semantic"
            fields_fixed = True

        # Fix version field
        if eval_data.get("version") is None:
            eval_data["version"] = "1.0"
            fields_fixed = True

        # Fix project field
        if eval_data.get("project") is None:
            eval_data["project"] = inferred_project
            fields_fixed = True

        # Fix method field
        if eval_data.get("method") is None:
            eval_data["method"] = inferred_method
            fields_fixed = True

        # Fix d4d_file field
        if eval_data.get("d4d_file") is None:
            project = eval_data.get("project", inferred_project)
            method = eval_data.get("method", inferred_method)
            eval_data["d4d_file"] = f"data/d4d_concatenated/{method}/{project}_d4d.yaml"
            fields_fixed = True

        # Fix evaluation_timestamp field
        if eval_data.get("evaluation_timestamp") is None:
            # Use file modification time as placeholder
            from datetime import datetime
            mtime = eval_path.stat().st_mtime
            timestamp = datetime.fromtimestamp(mtime).isoformat()
            eval_data["evaluation_timestamp"] = timestamp
            fields_fixed = True

        # Fix model field
        if eval_data.get("model") is None:
            eval_data["model"] = {
                "name": "claude-sonnet-4-5-20250929",
                "temperature": 0.0,
                "evaluation_type": "semantic_llm_judge"
            }
            fields_fixed = True

    # Only process rubric20-semantic evaluations
    if eval_data.get("rubric") != "rubric20-semantic":
        return False, f"Skipped: not rubric20-semantic (rubric={eval_data.get('rubric')})"

    # Calculate correct total from questions
    calculated_total, calculated_max = calculate_total_score(eval_data)

    # Get current overall_score
    current_total = eval_data.get("overall_score", {}).get("total_points", 0)
    current_max = eval_data.get("overall_score", {}).get("max_points", 0)
    current_percentage = eval_data.get("overall_score", {}).get("percentage", 0)

    # Calculate correct percentage
    calculated_percentage = (calculated_total / calculated_max * 100) if calculated_max > 0 else 0

    # Check if correction needed (scores or fields)
    score_needs_fix = (
        abs(calculated_total - current_total) > 0.01 or
        abs(calculated_max - current_max) > 0.01 or
        abs(calculated_percentage - current_percentage) > 0.01
    )

    if not score_needs_fix and not fields_fixed:
        return False, "Already correct"

    needs_fix = score_needs_fix or fields_fixed

    # Build status message
    diff = calculated_total - current_total
    message = (
        f"Corrected: {current_total}/{current_max} ({current_percentage:.1f}%) → "
        f"{calculated_total}/{calculated_max} ({calculated_percentage:.1f}%) "
        f"[{diff:+.0f} points]"
    )

    if dry_run:
        return True, f"[DRY RUN] {message}"

    # Update overall_score
    eval_data["overall_score"] = {
        "total_points": calculated_total,
        "max_points": calculated_max,
        "percentage": round(calculated_percentage, 1)
    }

    # Write back to file
    with open(eval_path, 'w') as f:
        json.dump(eval_data, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add trailing newline

    return True, message


def main():
    parser = argparse.ArgumentParser(
        description="Fix scoring errors in rubric20-semantic evaluation JSON files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without modifying files"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/evaluation_llm/rubric20_semantic/concatenated"),
        help="Directory containing evaluation JSON files"
    )

    args = parser.parse_args()

    # Find evaluation files
    base_dir = Path(__file__).parent.parent
    eval_dir = base_dir / args.input_dir

    if not eval_dir.exists():
        print(f"ERROR: Directory not found: {eval_dir}")
        return 1

    eval_files = list(eval_dir.glob("*_evaluation.json"))

    if not eval_files:
        print(f"No evaluation files found in {eval_dir}")
        return 1

    print(f"Found {len(eval_files)} evaluation files in {eval_dir.relative_to(base_dir)}")
    if args.dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***\n")
    print()

    # Process each file
    fixed_count = 0
    skipped_count = 0

    for eval_file in sorted(eval_files):
        print(f"Processing: {eval_file.name}")

        try:
            modified, message = fix_evaluation_scores(eval_file, dry_run=args.dry_run)
            print(f"  {message}")

            if modified:
                fixed_count += 1
            else:
                skipped_count += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            skipped_count += 1

        print()

    # Summary
    print("=" * 60)
    print("SUMMARY:")
    print(f"  ✅ Fixed:   {fixed_count}")
    print(f"  ⏭️  Skipped: {skipped_count}")
    print(f"  📊 Total:   {fixed_count + skipped_count}")
    print("=" * 60)

    if args.dry_run and fixed_count > 0:
        print("\nRun without --dry-run to apply fixes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
