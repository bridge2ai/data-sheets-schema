#!/usr/bin/env python3
"""
Generate Grand Challenge × Approach comparison table from rubric evaluation results.
Outputs both a formatted markdown table and a TSV file for analysis.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from data_sheets_schema.constants import RUBRIC20_MAX_SCORE
from data_sheets_schema.rubric_pooling import MixedDenominators, common_denominator


def _r20_cells(records, avg_points):
    """Score and percentage cells for a set of rubric20 records.

    Refuses rather than dividing by a constant: this table compares Grand
    Challenge approaches, and if one approach's evaluations predate the
    denominator correction and another's do not, a pooled average compares an
    approach against a measurement change (#281). `common_denominator` raises
    on a mixed set; the cells say so instead of printing a number.
    """
    try:
        denom = common_denominator(records)
    except MixedDenominators as mixed:
        return (f"{avg_points:.1f}/MIXED{tuple(mixed.seen)}", "n/a (mixed maxima)")
    return f"{avg_points:.1f}/{denom}", f"{(avg_points / denom) * 100:.1f}%"

# Project root
BASE_DIR = Path(__file__).parent.parent

# Grand Challenges and methods
GRAND_CHALLENGES = ["AI_READI", "CHORUS", "CM4AI", "VOICE"]
METHODS = ["gpt5", "claudecode", "claudecode_agent", "claudecode_assistant"]


def load_evaluation_scores(rubric: str) -> Dict[Tuple[str, str], Dict]:
    """Load all evaluation scores for a given rubric."""
    eval_dir = BASE_DIR / "data" / "evaluation_llm" / rubric / "concatenated"
    scores = {}
    
    for json_file in eval_dir.glob("*_evaluation.json"):
        with open(json_file) as f:
            data = json.load(f)
            project = data.get("project")
            method = data.get("method")
            
            if project and method:
                scores[(project, method)] = data["overall_score"]
    
    return scores


def generate_comparison_table():
    """Generate the complete GC × Approach comparison table."""
    
    # Load scores from both rubrics
    r10_scores = load_evaluation_scores("rubric10")
    r20_scores = load_evaluation_scores("rubric20")
    
    # Prepare data structure
    rows = []
    
    # Header
    headers = ["Project", "Rubric10", "Rubric20", "R10%", "R20%"]
    rows.append(headers)
    
    # Data rows
    for gc in GRAND_CHALLENGES:
        gc_r10_total = 0
        gc_r20_total = 0
        gc_r20_records = []
        gc_count = 0
        
        for method in METHODS:
            key = (gc, method)
            
            if key in r10_scores and key in r20_scores:
                r10 = r10_scores[key]
                r20 = r20_scores[key]
                
                row = [
                    f"{gc} - {method}",
                    f"{r10['total_points']}/50",
                    f"{r20['total_points']}/{r20.get('max_points', RUBRIC20_MAX_SCORE)}",
                    f"{r10['percentage']}%",
                    f"{r20['percentage']}%"
                ]
                rows.append(row)
                
                gc_r10_total += r10['total_points']
                gc_r20_total += r20['total_points']
                gc_r20_records.append({'overall_score': r20})
                gc_count += 1
        
        # GC average row
        if gc_count > 0:
            gc_r10_avg = gc_r10_total / gc_count
            gc_r20_avg = gc_r20_total / gc_count
            gc_r10_pct = (gc_r10_avg / 50) * 100
            gc_r20_score_cell, gc_r20_pct_cell = _r20_cells(gc_r20_records, gc_r20_avg)
            
            avg_row = [
                f"{gc} Average",
                f"{gc_r10_avg:.1f}/50",
                gc_r20_score_cell,
                f"{gc_r10_pct:.1f}%",
                gc_r20_pct_cell
            ]
            rows.append(avg_row)
            rows.append(["", "", "", "", ""])  # Blank separator
    
    # Overall method averages
    for method in METHODS:
        method_r10_total = 0
        method_r20_total = 0
        method_r20_records = []
        method_count = 0
        
        for gc in GRAND_CHALLENGES:
            key = (gc, method)
            if key in r10_scores and key in r20_scores:
                method_r10_total += r10_scores[key]['total_points']
                method_r20_total += r20_scores[key]['total_points']
                method_r20_records.append({'overall_score': r20_scores[key]})
                method_count += 1
        
        if method_count > 0:
            method_r10_avg = method_r10_total / method_count
            method_r20_avg = method_r20_total / method_count
            method_r10_pct = (method_r10_avg / 50) * 100
            method_r20_score_cell, method_r20_pct_cell = _r20_cells(method_r20_records, method_r20_avg)
            
            method_row = [
                f"Overall - {method}",
                f"{method_r10_avg:.1f}/50",
                method_r20_score_cell,
                f"{method_r10_pct:.1f}%",
                method_r20_pct_cell
            ]
            rows.append(method_row)
    
    # Grand average
    grand_r10_total = sum(s['total_points'] for s in r10_scores.values())
    grand_r20_total = sum(s['total_points'] for s in r20_scores.values())
    grand_r20_records = [{'overall_score': s} for s in r20_scores.values()]
    grand_count = len(r10_scores)
    
    if grand_count > 0:
        grand_r10_avg = grand_r10_total / grand_count
        grand_r20_avg = grand_r20_total / grand_count
        grand_r10_pct = (grand_r10_avg / 50) * 100
        grand_r20_score_cell, grand_r20_pct_cell = _r20_cells(grand_r20_records, grand_r20_avg)
        
        grand_row = [
            "Grand Average",
            f"{grand_r10_avg:.1f}/50",
            grand_r20_score_cell,
            f"{grand_r10_pct:.1f}%",
            grand_r20_pct_cell
        ]
        rows.append(grand_row)
    
    return rows


def write_tsv(rows: List[List[str]], output_path: Path):
    """Write table data to TSV file."""
    with open(output_path, 'w') as f:
        for row in rows:
            f.write('\t'.join(row) + '\n')


def write_markdown(rows: List[List[str]], output_path: Path):
    """Write table data as markdown."""
    with open(output_path, 'w') as f:
        f.write("# Grand Challenge × Approach Comparison\n\n")
        f.write("## Complete Evaluation Results\n\n")
        
        # Write header
        f.write("| " + " | ".join(rows[0]) + " |\n")
        f.write("|" + "|".join(["------"] * len(rows[0])) + "|\n")
        
        # Write data rows
        for row in rows[1:]:
            if all(cell == "" for cell in row):
                f.write("| | | | | |\n")  # Blank separator
            else:
                f.write("| " + " | ".join(row) + " |\n")


def main():
    print("=" * 70)
    print("Grand Challenge × Approach Comparison Table Generator")
    print("=" * 70)
    print()
    
    # Generate table
    print("Loading evaluation scores...")
    rows = generate_comparison_table()
    print(f"Generated {len(rows)} rows")
    print()
    
    # Output paths
    output_dir = BASE_DIR / "data" / "evaluation_llm"
    tsv_path = output_dir / "gc_approach_comparison.tsv"
    md_path = output_dir / "gc_approach_comparison.md"
    
    # Write files
    write_tsv(rows, tsv_path)
    print(f"✅ TSV file created: {tsv_path}")
    
    write_markdown(rows, md_path)
    print(f"✅ Markdown file created: {md_path}")
    
    print()
    print("=" * 70)
    print("Table generation complete!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
