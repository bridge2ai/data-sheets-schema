#!/usr/bin/env python3
"""
Systematic D4D Evaluation Script for Rubric10

This script orchestrates rubric10 evaluation of ALL D4D files (individual and concatenated)
across all projects and generation methods, using Claude Code conversational evaluation.

Usage:
    python scripts/evaluate_all_d4ds_rubric10.py

Output:
    - data/evaluation_llm/rubric10/file_inventory.json
    - data/evaluation_llm/rubric10/evaluation_plan.md
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Projects
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE"]

# Generation methods
INDIVIDUAL_METHODS = ["gpt5", "claudecode_agent", "claudecode_assistant"]
CONCATENATED_METHODS = ["curated", "gpt5", "claudecode", "claudecode_agent", "claudecode_assistant"]


def find_individual_files() -> Dict[str, List[str]]:
    """Find all individual D4D files."""
    files = {}

    for project in PROJECTS:
        for method in INDIVIDUAL_METHODS:
            dir_path = BASE_DIR / "data" / "d4d_individual" / method / project
            if dir_path.exists():
                yaml_files = list(dir_path.glob("*_d4d.yaml"))
                for yaml_file in yaml_files:
                    key = f"{project}_{method}_individual"
                    if key not in files:
                        files[key] = []
                    files[key].append(str(yaml_file.relative_to(BASE_DIR)))

    return files


def find_concatenated_files() -> Dict[str, str]:
    """Find all concatenated D4D files."""
    files = {}

    for project in PROJECTS:
        for method in CONCATENATED_METHODS:
            file_path = BASE_DIR / "data" / "d4d_concatenated" / method / f"{project}_d4d.yaml"
            if file_path.exists():
                key = f"{project}_{method}_concatenated"
                files[key] = str(file_path.relative_to(BASE_DIR))

    return files


def create_file_inventory():
    """Create comprehensive inventory of all D4D files to evaluate."""

    individual_files = find_individual_files()
    concatenated_files = find_concatenated_files()

    # Count statistics
    total_individual = sum(len(files) for files in individual_files.values())
    total_concatenated = len(concatenated_files)

    inventory = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "projects": PROJECTS,
            "individual_methods": INDIVIDUAL_METHODS,
            "concatenated_methods": CONCATENATED_METHODS,
            "total_individual_files": total_individual,
            "total_concatenated_files": total_concatenated,
            "total_files": total_individual + total_concatenated
        },
        "individual_files": individual_files,
        "concatenated_files": concatenated_files
    }

    # Save inventory
    output_dir = BASE_DIR / "data" / "evaluation_llm" / "rubric10"
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory_path = output_dir / "file_inventory.json"
    with open(inventory_path, 'w') as f:
        json.dump(inventory, f, indent=2)

    print(f"✅ File inventory created: {inventory_path}")
    print(f"   Total files to evaluate: {total_individual + total_concatenated}")
    print(f"   - Individual files: {total_individual}")
    print(f"   - Concatenated files: {total_concatenated}")

    return inventory


def create_evaluation_plan(inventory: Dict):
    """Create markdown evaluation plan for Claude Code."""

    plan = f"""# Rubric10 Evaluation Plan

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Scope

**Total files to evaluate:** {inventory['metadata']['total_files']}
- Individual files: {inventory['metadata']['total_individual_files']}
- Concatenated files: {inventory['metadata']['total_concatenated_files']}

## Evaluation Settings

- **Rubric:** rubric10 (10 elements, 50 sub-elements, max 50 points)
- **Temperature:** 0.0 (fully deterministic)
- **Model:** claude-sonnet-4-5-20250929 (date-pinned)
- **Method:** Conversational LLM-as-judge within Claude Code

## Individual Files by Project

"""

    # Individual files breakdown
    for project in PROJECTS:
        plan += f"\n### {project}\n\n"
        project_files = {k: v for k, v in inventory['individual_files'].items() if k.startswith(project)}

        for method in INDIVIDUAL_METHODS:
            key = f"{project}_{method}_individual"
            if key in project_files:
                files = project_files[key]
                plan += f"**{method}:** {len(files)} files\n"
                for file_path in files:
                    plan += f"  - `{file_path}`\n"
        plan += "\n"

    # Concatenated files
    plan += "## Concatenated Files by Project\n\n"

    for project in PROJECTS:
        plan += f"\n### {project}\n\n"
        project_files = {k: v for k, v in inventory['concatenated_files'].items() if k.startswith(project)}

        for method in CONCATENATED_METHODS:
            key = f"{project}_{method}_concatenated"
            if key in project_files:
                file_path = project_files[key]
                plan += f"**{method}:** `{file_path}`\n"
        plan += "\n"

    # Evaluation procedure
    plan += """## Evaluation Procedure

For each file, the rubric10 agent will:

1. **Read D4D YAML** using Read tool
2. **Apply rubric10 criteria** across 10 elements:
   - Element 1: Dataset Discovery and Identification (5 sub-elements)
   - Element 2: Dataset Access and Retrieval (5 sub-elements)
   - Element 3: Data Reuse and Interoperability (5 sub-elements)
   - Element 4: Ethical Use and Privacy Safeguards (5 sub-elements)
   - Element 5: Data Composition and Structure (5 sub-elements)
   - Element 6: Data Provenance and Version Tracking (5 sub-elements)
   - Element 7: Scientific Motivation and Funding Transparency (5 sub-elements)
   - Element 8: Technical Transparency (5 sub-elements)
   - Element 9: Dataset Evaluation and Limitations Disclosure (5 sub-elements)
   - Element 10: Cross-Platform and Community Integration (5 sub-elements)

3. **Score each sub-element** (0 or 1):
   - 1: Field present AND meaningful
   - 0: Field absent, generic, incomplete, or vague

4. **Provide evidence** from D4D file for each score

5. **Generate JSON output** with:
   - Overall score (total_points/50)
   - Element-by-element breakdown
   - Strengths, weaknesses, recommendations

6. **Save results** to:
   - Individual: `data/evaluation_llm/rubric10/individual/{project}_{method}_{filename}_evaluation.json`
   - Concatenated: `data/evaluation_llm/rubric10/concatenated/{project}_{method}_evaluation.json`

## Expected Output

After all evaluations complete:

1. **Individual evaluation JSONs:** ~{inventory['metadata']['total_individual_files']} files
2. **Concatenated evaluation JSONs:** {inventory['metadata']['total_concatenated_files']} files
3. **Summary CSV:** `data/evaluation_llm/rubric10/all_scores.csv`
4. **Summary report:** `data/evaluation_llm/rubric10/summary_report.md`

## Output Format

Each evaluation JSON contains:

```json
{{
  "rubric": "rubric10",
  "d4d_file": "path/to/file.yaml",
  "project": "PROJECT_NAME",
  "method": "METHOD_NAME",
  "type": "individual" or "concatenated",
  "overall_score": {{
    "total_points": 38.5,
    "max_points": 50,
    "percentage": 77.0
  }},
  "elements": [
    {{
      "id": 1,
      "name": "Dataset Discovery and Identification",
      "element_score": 5,
      "element_max": 5,
      "sub_elements": [...]
    }},
    ...
  ],
  "assessment": {{
    "strengths": [...],
    "weaknesses": [...],
    "recommendations": [...]
  }}
}}
```

## Summary Table Format

After evaluation, create table:

| Project | Type | Method | Score | Elements Passing | Top Element | Weakest Element |
|---------|------|--------|-------|------------------|-------------|-----------------|
| AI_READI | concat | curated | 42/50 (84%) | 8/10 | Discovery (5/5) | Provenance (2/5) |
| AI_READI | concat | gpt5 | 18/50 (36%) | 3/10 | Access (4/5) | Integration (0/5) |
| ... | ... | ... | ... | ... | ... | ... |

## Commands to Run

This plan can be executed conversationally in Claude Code with:

```
Using the d4d-rubric10 agent, evaluate all files listed in
data/evaluation_llm/rubric10/file_inventory.json and save results
according to this evaluation plan.
```
"""

    # Save plan
    output_dir = BASE_DIR / "data" / "evaluation_llm" / "rubric10"
    plan_path = output_dir / "evaluation_plan.md"

    with open(plan_path, 'w') as f:
        f.write(plan)

    print(f"✅ Evaluation plan created: {plan_path}")

    return plan_path


if __name__ == "__main__":
    print("=" * 60)
    print("D4D Rubric10 Evaluation - File Inventory & Plan Generator")
    print("=" * 60)
    print()

    # Create file inventory
    inventory = create_file_inventory()
    print()

    # Create evaluation plan
    plan_path = create_evaluation_plan(inventory)
    print()

    print("=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print()
    print("1. Review the file inventory:")
    print("   cat data/evaluation_llm/rubric10/file_inventory.json")
    print()
    print("2. Review the evaluation plan:")
    print("   cat data/evaluation_llm/rubric10/evaluation_plan.md")
    print()
    print("3. Use this Claude Code prompt:")
    print()
    print("   " + "─" * 56)
    print("   Using the d4d-rubric10 agent, evaluate all files listed")
    print("   in data/evaluation_llm/rubric10/file_inventory.json and")
    print("   save results according to the evaluation plan at")
    print("   data/evaluation_llm/rubric10/evaluation_plan.md")
    print("   " + "─" * 56)
    print()
