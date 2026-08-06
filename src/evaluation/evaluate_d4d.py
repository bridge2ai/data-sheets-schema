#!/usr/bin/env python3
"""
D4D Evaluation Framework

Evaluates D4D (Datasheets for Datasets) YAML files using two rubric systems:
- rubric10: 10-element hierarchical rubric with binary sub-elements
- rubric20: 20-question detailed rubric with quality-based scoring

Compares three D4D generation methods:
- Curated Comprehensive: Manually curated, comprehensive datasheets
- GPT-5: Generated using GPT-5
- Claude Code Deterministic: Generated using Claude Code assistant (direct synthesis)

Author: Claude Code Assistant
Date: 2025-11-17
"""

import argparse
import json
import re
import csv
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from data_sheets_schema.constants import PROJECTS, METHODS, RUBRIC10_PATH, RUBRIC20_PATH

# Schema used for validation, keyed by method name
_METHOD_SCHEMA = {
    "claudecode_agent_core": (
        "src/data_sheets_schema/schema/data_sheets_schema_core.yaml",
        "CoreDataset",
    ),
}
_DEFAULT_SCHEMA = (
    "src/data_sheets_schema/schema/data_sheets_schema.yaml",
    "Dataset",
)


_VALIDATE_TIMEOUT_SECONDS = 60


def validate_d4d_yaml(file_path: Path, method: str = "") -> bool:
    """
    Run linkml-validate on a D4D YAML file.

    Selects the correct schema and target class automatically:
    - ``DatasetCollection`` wrapper format (curated files)  → extract first
      resource and validate as ``Dataset``
    - ``claudecode_agent_core`` method or ``_core`` in path → -C CoreDataset
    - Everything else                                       → -C Dataset

    Tries `linkml-validate` directly first, falls back to `poetry run
    linkml-validate` if the binary is not on PATH. Each invocation has a
    60-second timeout. Prints a clear warning on failure but does NOT raise —
    callers decide whether to abort.

    Returns True if validation passed, False otherwise (including when
    validation could not run because the tool is unavailable or timed out).
    """
    schema_file, class_name = _METHOD_SCHEMA.get(method, _DEFAULT_SCHEMA)

    # Path-based fallback when called without a method (e.g. from the render CLI)
    if method == "" and ("_core" in str(file_path) or "claudecode_agent_core" in str(file_path)):
        schema_file, class_name = _METHOD_SCHEMA["claudecode_agent_core"]

    # Peek at the YAML to detect DatasetCollection key-wrapped format used by
    # curated files.  In that format the file contains:
    #   DatasetCollection:
    #     resources:
    #       - {id: ..., ...}
    # linkml-validate cannot unwrap this automatically, so we extract the first
    # resource and validate it as a Dataset instead.
    validate_path = file_path
    tmp_file = None
    try:
        with open(file_path, "r", encoding="utf-8-sig") as fh:
            top = yaml.safe_load(fh)
        if isinstance(top, dict) and "DatasetCollection" in top:
            collection = top["DatasetCollection"]
            resources = collection.get("resources", []) if isinstance(collection, dict) else []
            if resources:
                tmp_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False, encoding="utf-8"
                )
                yaml.dump(resources[0], tmp_file)
                tmp_file.close()
                validate_path = Path(tmp_file.name)
                # class_name stays Dataset (already set above)
    except Exception:
        pass  # fall through and let linkml-validate report the real problem

    base_args = ["-s", schema_file, "-C", class_name, str(validate_path)]
    commands = [
        ["linkml-validate", *base_args],
        ["poetry", "run", "linkml-validate", *base_args],
    ]

    result = None
    last_error = ""
    try:
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=_VALIDATE_TIMEOUT_SECONDS,
                )
                break  # got a result (success or validation failure)
            except FileNotFoundError:
                last_error = f"command not found: {cmd[0]}"
                continue
            except subprocess.TimeoutExpired:
                last_error = f"timeout after {_VALIDATE_TIMEOUT_SECONDS}s"
                break
    finally:
        # Clean up temp file if we created one
        if tmp_file is not None:
            try:
                Path(tmp_file.name).unlink()
            except Exception:
                pass

    if result is None:
        print(
            f"\n{'='*60}\n"
            f"⚠️  VALIDATION SKIPPED: {file_path}\n"
            f"    {last_error or 'linkml-validate not available'}\n"
            "    Install linkml or run inside the poetry environment to enable validation.\n"
            f"{'='*60}\n"
        )
        return False

    if result.returncode != 0:
        print(
            f"\n{'='*60}\n"
            f"⚠️  VALIDATION FAILED: {file_path}\n"
            f"    Schema : {schema_file}  (class: {class_name})\n"
            f"{result.stdout.strip()}\n"
            f"{result.stderr.strip()}\n"
            f"{'='*60}\n"
            "    Proceeding anyway — fix the YAML before publishing.\n"
            f"{'='*60}\n"
        )
        return False

    print(f"✓ Validation passed [{class_name}]: {file_path.name}")
    return True


@dataclass
class SubElementScore:
    """Score for a single sub-element in rubric10"""
    name: str
    field_paths: List[str]
    score: int  # 0 or 1
    found_values: List[str]  # Actual values found in D4D file


@dataclass
class ElementScore:
    """Score for a single element in rubric10"""
    element_id: int
    name: str
    description: str
    sub_element_scores: List[SubElementScore]
    total_score: float  # 0-5
    max_score: int = 5


@dataclass
class QuestionScore:
    """Score for a single question in rubric20"""
    question_id: int
    name: str
    description: str
    category: str
    score_type: str  # "numeric" or "pass_fail"
    score: float  # 0-5 for numeric, 0 or 1 for pass/fail
    max_score: int
    score_label: str  # Description of the score level
    found_values: List[str]


@dataclass
class D4DEvaluation:
    """Complete evaluation result for a single D4D file"""
    project: str
    method: str  # "curated", "gpt5", or "claudecode"
    file_path: str
    timestamp: str
    rubric10_scores: List[ElementScore]
    rubric20_scores: List[QuestionScore]
    rubric10_total: float
    rubric10_max: int
    rubric10_percentage: float
    rubric20_total: float
    rubric20_max: int
    rubric20_percentage: float
    # Run label, e.g. "2026-07-28_claude-opus-5-generic_rep1". None for methods
    # stored flat (one record per method). Without it, three replicates of one
    # method collapse onto the same key and silently overwrite each other —
    # which is why every score here was previously one unlabelled row per
    # (project, method).
    label: Optional[str] = None


class D4DEvaluator:
    """Main evaluator class for D4D YAML files"""

    def __init__(self, rubric10_path: str, rubric20_path: str):
        self.rubric10_path = Path(rubric10_path)
        self.rubric20_path = Path(rubric20_path)
        self.rubric10 = self._load_rubric10()
        self.rubric20 = self._load_rubric20()

    def _load_rubric10(self) -> Dict[str, Any]:
        """Load and parse rubric10.txt"""
        with open(self.rubric10_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_rubric20(self) -> Dict[str, Any]:
        """Load and parse rubric20.txt"""
        with open(self.rubric20_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_d4d_yaml(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a D4D YAML file.
        Handles both:
        1. Flat D4D schema format (gpt5, claudecode)
        2. DatasetCollection schema format (curated comprehensive)

        For DatasetCollection format, extracts the first resource.
        """
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        # Check if this is a DatasetCollection format
        if isinstance(data, dict) and 'DatasetCollection' in data:
            # Extract the first resource from DatasetCollection
            if 'resources' in data['DatasetCollection'] and data['DatasetCollection']['resources']:
                return data['DatasetCollection']['resources'][0]
            else:
                print(
                    f"Warning: DatasetCollection format but no resources found in {file_path}")
                return {}

        # Otherwise, return as-is (flat D4D format)
        return data

    def _extract_field_value(self, d4d_data: Dict[str, Any], field_path: str) -> Optional[Any]:
        """
        Extract a field value from D4D data using dot notation path.

        Examples:
            "title" -> d4d_data["title"]
            "license_and_use_terms.description" -> d4d_data["license_and_use_terms"]["description"]
        """
        parts = field_path.split('.')
        current = d4d_data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None

        return current

    def _is_field_present(self, d4d_data: Dict[str, Any], field_paths: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if any of the field paths are present and non-empty in D4D data.
        Returns (is_present, found_values)
        """
        found_values = []

        for field_path in field_paths:
            value = self._extract_field_value(d4d_data, field_path)

            # Check if value is present and meaningful
            if value is not None:
                # Handle different types
                if isinstance(value, str) and value.strip():
                    # Truncate long strings
                    found_values.append(f"{field_path}: {value[:100]}")
                    return True, found_values
                elif isinstance(value, (list, dict)) and value:
                    found_values.append(
                        f"{field_path}: {type(value).__name__} (non-empty)")
                    return True, found_values
                elif isinstance(value, (int, float, bool)):
                    found_values.append(f"{field_path}: {value}")
                    return True, found_values

        return False, found_values

    def _score_rubric10_element(self, d4d_data: Dict[str, Any], element: Dict[str, Any]) -> ElementScore:
        """Score a single element from rubric10"""
        sub_element_scores = []

        for sub_elem in element['sub_elements']:
            # Get field paths for this sub-element
            field_paths = sub_elem['field']
            if isinstance(field_paths, str):
                field_paths = [field_paths]

            # Check if field is present
            is_present, found_values = self._is_field_present(
                d4d_data, field_paths)

            score = 1 if is_present else 0

            sub_element_scores.append(SubElementScore(
                name=sub_elem['name'],
                field_paths=field_paths,
                score=score,
                found_values=found_values
            ))

        # Total score is sum of sub-element scores
        total_score = sum(s.score for s in sub_element_scores)

        return ElementScore(
            element_id=element['id'],
            name=element['name'],
            description=element['description'],
            sub_element_scores=sub_element_scores,
            total_score=total_score,
            max_score=5
        )

    # Questions whose bands state an explicit numeric threshold, and the
    # quantity each threshold is about. The rest describe tiers of depth
    # ("No X" / "basic X" / "comprehensive X"), which are scored by how much of
    # the question's own declared field set is populated.
    # Q1 is the one measured question whose bands leave a gap: 0 is "<=40%",
    # 3 is "~70%", 5 is ">=90%", and nothing states what 41-69% scores. One rule
    # resolves it — a gap between two bands is split at the midpoint — and it is
    # applied to *both* boundaries. Taking the midpoint at one end and the
    # stated threshold at the other, as an earlier version did, made a record at
    # 45% score 0 while a record at 85% scored 3, for no stated reason.
    Q1_BAND_THRESHOLDS = ((5, 0.80),    # midpoint of 70 and 90
                          (3, 0.55),    # midpoint of 40 and 70
                          (0, 0.0))
    RUBRIC20_MEASURES = {
        1: "proportion_populated",   # <=40% / ~70% / >=90% of fields
        2: "char_length",            # <50 / 50-200 / >200 chars
        3: "item_count",             # <3 / 3-7 / >=8 keywords
        4: "distinct_types",         # 1 / 2-3 / >3 file types
    }

    def _raw_values(self, d4d_data, field_paths):
        """The actual field values, not `_is_field_present`'s descriptions.

        `_is_field_present` returns display strings — `"keywords: list
        (non-empty)"` — and truncates text at 100 characters. Measuring those
        would count the length of a description rather than the content, and cap
        every long entry at the same value. Anything that measures must read the
        values directly.
        """
        out = []
        for f in field_paths:
            v = self._extract_field_value(d4d_data, f)
            if v is not None and v != "" and v != [] and v != {}:
                out.append(v)
        return out

    def _score_numeric_rubric20(self, question, d4d_data, field_paths,
                                is_present, found_values):
        """Score a 0-5 question by measuring it, not by asserting a constant.

        This previously returned 0 when a field was absent and a flat 4 when it
        was present — never 1, 2, 3 or 5. Measured across the whole corpus that
        made rubric20 return 71/88 for *every* record, so it could not rank
        anything, and the one rubric meant to discriminate on quality was inert.

        Four questions state an explicit numeric threshold and are measured
        directly. The remaining thirteen describe tiers — "No bias
        documentation" / "basic bias identification" / "comprehensive bias
        categorization" — and are scored by how much of the question's own
        declared field set is populated: none, some, all.

        **That is a coverage proxy for depth, not a measurement of depth.** A
        record can populate every field of a question shallowly and score 5
        here. Judging whether the content is actually comprehensive is what the
        `d4d-rubric20-semantic` agent is for; this path is the free, fast,
        deterministic one, and it should not be read as more than it is.
        """
        bands = {int(k): v for k, v in question['scoring'].items()}
        measure = self.RUBRIC20_MEASURES.get(question['id'], "field_coverage")

        if not is_present and measure != "proportion_populated":
            return 0, bands.get(0, "Not present")

        values = self._raw_values(d4d_data, field_paths)

        if measure == "char_length":
            n = max((len(str(v)) for v in values), default=0)
            score = 5 if n > 200 else 3 if n >= 50 else 0
            return score, f"{bands.get(score, '')} (measured {n} chars)"

        if measure == "item_count":
            n = self._count_items(values)
            score = 5 if n >= 8 else 3 if n >= 3 else 0
            return score, f"{bands.get(score, '')} (measured {n} items)"

        if measure == "distinct_types":
            n = self._count_distinct_types(values)
            score = 5 if n > 3 else 3 if n >= 2 else 0
            return score, f"{bands.get(score, '')} (measured {n} distinct)"

        # proportion_populated and field_coverage share a denominator: the
        # question's own declared fields. Only the band boundaries differ.
        populated = sum(1 for f in field_paths
                        if self._is_field_present(d4d_data, [f])[0])
        total = len(field_paths) or 1
        frac = populated / total
        if measure == "proportion_populated":
            score = self._band_for(frac, self.Q1_BAND_THRESHOLDS)
        else:
            # Tiered: nothing populated is 0, everything is 5, partial is 3.
            score = 0 if populated == 0 else (5 if populated == total else 3)
        return score, (f"{bands.get(score, '')} "
                       f"({populated}/{total} fields populated)")

    @staticmethod
    def _band_for(value, thresholds):
        """Highest band whose threshold the measurement reaches."""
        for score, floor in thresholds:
            if value >= floor:
                return score
        return 0

    @staticmethod
    def _count_items(found_values) -> int:
        n = 0
        for v in found_values:
            if isinstance(v, (list, tuple, set)):
                n += len(v)
            elif isinstance(v, str):
                # A single string may still enumerate several items.
                n += len([x for x in re.split(r"[,;\n]", v) if x.strip()])
            elif v is not None:
                n += 1
        return n

    @staticmethod
    def _count_distinct_types(found_values) -> int:
        seen = set()
        for v in found_values:
            items = v if isinstance(v, (list, tuple)) else [v]
            for it in items:
                if isinstance(it, dict):
                    for key in ("format", "file_type", "media_type", "type",
                                "extension"):
                        if it.get(key):
                            seen.add(str(it[key]).lower())
                            break
                elif it is not None:
                    seen.add(str(it).lower())
        return len(seen)

    def _score_rubric20_question(self, d4d_data: Dict[str, Any], question: Dict[str, Any]) -> QuestionScore:
        """Score a single question from rubric20"""
        field_paths = question['field']
        if isinstance(field_paths, str):
            field_paths = [field_paths]

        is_present, found_values = self._is_field_present(
            d4d_data, field_paths)

        score_type = question['score_type']

        if score_type == 'pass_fail':
            # Binary scoring
            score = 1 if is_present else 0
            max_score = 1
            score_label = "Pass" if is_present else "Fail"
        else:
            score, score_label = self._score_numeric_rubric20(
                question, d4d_data, field_paths, is_present, found_values)
            max_score = 5

        return QuestionScore(
            question_id=question['id'],
            name=question['name'],
            description=question['description'],
            category=self._get_question_category(question['id']),
            score_type=score_type,
            score=score,
            max_score=max_score,
            score_label=score_label,
            found_values=found_values
        )

    def _get_question_category(self, question_id: int) -> str:
        """Get category name for a rubric20 question based on ID"""
        if 1 <= question_id <= 5:
            return "Structural Completeness"
        elif 6 <= question_id <= 10:
            return "Metadata Quality & Content"
        elif 11 <= question_id <= 15:
            return "Technical Documentation"
        elif 16 <= question_id <= 20:
            return "FAIRness & Accessibility"
        else:
            return "Unknown"

    def evaluate_d4d_file(self, file_path: Path, project: str, method: str,
                          label: Optional[str] = None) -> D4DEvaluation:
        """Evaluate a single D4D YAML file using both rubrics"""

        # Load D4D data
        d4d_data = self._load_d4d_yaml(file_path)

        # Score rubric10
        rubric10_scores = []
        for element in self.rubric10['d4d_complex_proxy_rubric']['rubric']:
            element_score = self._score_rubric10_element(d4d_data, element)
            rubric10_scores.append(element_score)

        rubric10_total = sum(s.total_score for s in rubric10_scores)
        rubric10_max = len(rubric10_scores) * 5
        rubric10_percentage = (
            rubric10_total / rubric10_max * 100) if rubric10_max > 0 else 0

        # Score rubric20
        rubric20_scores = []
        for question in self.rubric20['d4d_evaluation_rubric']['rubric']:
            question_score = self._score_rubric20_question(d4d_data, question)
            rubric20_scores.append(question_score)

        rubric20_total = sum(s.score for s in rubric20_scores)
        rubric20_max = sum(s.max_score for s in rubric20_scores)
        rubric20_percentage = (
            rubric20_total / rubric20_max * 100) if rubric20_max > 0 else 0

        return D4DEvaluation(
            project=project,
            method=method,
            file_path=str(file_path),
            timestamp=datetime.now().isoformat(),
            rubric10_scores=rubric10_scores,
            rubric20_scores=rubric20_scores,
            rubric10_total=rubric10_total,
            rubric10_max=rubric10_max,
            rubric10_percentage=rubric10_percentage,
            rubric20_total=rubric20_total,
            rubric20_max=rubric20_max,
            rubric20_percentage=rubric20_percentage,
            label=label,
        )

    @staticmethod
    def discover_records(base_dir: Path, project: str,
                         method: str) -> List[Tuple[Optional[str], Path]]:
        """Every record for one (project, method), as (label, path) pairs.

        Replaces a hardcoded per-method path table that assumed one record per
        method. Generation outputs moved into run-labelled directories
        (`{method}/{label}/{PROJECT}_d4d.yaml`), which left that table pointing
        at paths that no longer exist — `--method claudecode_agent` evaluated
        zero files while reporting success.

        Both layouts are supported, because they both still exist: `curated`,
        `gpt5` and `claudecode` remain flat, and `label` is None for those.
        Discovery is by glob rather than by an enumerated method list, so arms
        added later (crate, healthsheet, crate_only) work without an edit here.
        """
        method_dir = base_dir / "d4d_concatenated" / method
        if not method_dir.is_dir():
            return []

        # Filename depends on the method, not the layout.
        if method == "curated":
            stems = [f"{project}_curated.yaml"]
        elif method.endswith("_core"):
            stems = [f"{project}_d4d_core.yaml"]
        else:
            stems = [f"{project}_d4d.yaml"]

        found: List[Tuple[Optional[str], Path]] = []
        for stem in stems:
            flat = method_dir / stem
            if flat.is_file():
                found.append((None, flat))
            for sub in sorted(p for p in method_dir.iterdir() if p.is_dir()):
                nested = sub / stem
                if nested.is_file():
                    found.append((sub.name, nested))
        return found

    def evaluate_all_projects(self, base_dir: Path, projects: List[str],
                              methods: List[str],
                              include_invalid: bool = False,
                              ) -> List[D4DEvaluation]:
        """Evaluate every discovered record for the given projects and methods."""
        evaluations = []

        for project in projects:
            for method in methods:
                records = self.discover_records(base_dir, project, method)
                if not records:
                    print(f"No records found for {project}/{method}")
                    continue

                for label, file_path in records:
                    tag = f"{project}/{method}" + (f"/{label}" if label else "")

                    # Validate before evaluating; skip on failure so the batch
                    # report only contains evaluations of valid YAML — unless
                    # the caller opts in: records generated under an older
                    # schema version fail the current validator without being
                    # wrong (#374), and a silent skip excluded whole sweeps.
                    if not validate_d4d_yaml(file_path, method):
                        if not include_invalid:
                            print(f"Skipping evaluation for {tag}: "
                                  "validation failed.")
                            continue
                        print(f"Evaluating {tag} despite validation failure "
                              "(--include-invalid).")

                    print(f"Evaluating {tag}...")
                    evaluation = self.evaluate_d4d_file(
                        file_path, project, method, label=label)
                    evaluations.append(evaluation)

        return evaluations

    def evaluate_individual_files(self, base_dir: Path, methods: List[str]) -> List[D4DEvaluation]:
        """Evaluate all individual D4D files for given methods"""

        evaluations = []

        for method in methods:
            method_dir = base_dir / "d4d_individual" / method

            if not method_dir.exists():
                print(
                    f"Skipping method {method}: directory not found at {method_dir}")
                continue

            # Find all *_d4d.yaml files (excluding *_metadata.yaml)
            d4d_files = sorted(method_dir.glob("**/*_d4d.yaml"))
            d4d_files = [
                f for f in d4d_files if not f.name.endswith("_metadata.yaml")]

            print(
                f"\nEvaluating {len(d4d_files)} individual files for method: {method}")

            for file_path in d4d_files:
                # Extract project and file identifier from path
                # Path format: data/d4d_individual/{method}/{PROJECT}/{filename}_d4d.yaml
                project = file_path.parent.name
                file_id = file_path.stem.replace("_d4d", "")

                print(f"  - {project}/{file_id}...")

                evaluation = self.evaluate_d4d_file(
                    file_path, f"{project}/{file_id}", method)
                evaluations.append(evaluation)

        return evaluations

    def generate_summary_report(self, evaluations: List[D4DEvaluation], output_path: Path):
        """Generate executive summary report in Markdown"""

        lines = []
        lines.append("# D4D Evaluation Summary Report")
        lines.append(f"\nGenerated: {datetime.now().isoformat()}\n")

        lines.append("## Overview\n")
        lines.append(f"Total evaluations: {len(evaluations)}\n")

        # Group by project
        projects = set(e.project for e in evaluations)
        lines.append(f"Projects evaluated: {', '.join(sorted(projects))}\n")

        # Group by method
        methods = set(e.method for e in evaluations)
        lines.append(f"Methods evaluated: {', '.join(sorted(methods))}\n")

        lines.append("\n## Overall Scores\n")
        lines.append("### Rubric10 Scores (0-50)\n")
        lines.append("| Project | Curated | GPT-5 | Claude Code |")
        lines.append("|---------|---------|-------|-------------|")

        for project in sorted(projects):
            row = [project]
            for method in ["curated", "gpt5", "claudecode"]:
                evals = [e for e in evaluations if e.project ==
                         project and e.method == method]
                if evals:
                    score = f"{evals[0].rubric10_total:.1f} ({evals[0].rubric10_percentage:.1f}%)"
                else:
                    score = "N/A"
                row.append(score)
            lines.append("| " + " | ".join(row) + " |")

        lines.append("\n### Rubric20 Scores (varies by max)\n")
        lines.append("| Project | Curated | GPT-5 | Claude Code |")
        lines.append("|---------|---------|-------|-------------|")

        for project in sorted(projects):
            row = [project]
            for method in ["curated", "gpt5", "claudecode"]:
                evals = [e for e in evaluations if e.project ==
                         project and e.method == method]
                if evals:
                    score = f"{evals[0].rubric20_total:.1f}/{evals[0].rubric20_max} ({evals[0].rubric20_percentage:.1f}%)"
                else:
                    score = "N/A"
                row.append(score)
            lines.append("| " + " | ".join(row) + " |")

        lines.append("\n## Method Comparison\n")

        for method in sorted(methods):
            method_evals = [e for e in evaluations if e.method == method]
            if not method_evals:
                continue

            avg_rubric10 = sum(
                e.rubric10_percentage for e in method_evals) / len(method_evals)
            avg_rubric20 = sum(
                e.rubric20_percentage for e in method_evals) / len(method_evals)

            lines.append(f"\n### {method.upper()}")
            lines.append(f"- Average Rubric10: {avg_rubric10:.1f}%")
            lines.append(f"- Average Rubric20: {avg_rubric20:.1f}%")
            lines.append(f"- Evaluations: {len(method_evals)}")

        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

        print(f"Summary report written to {output_path}")

    def generate_detailed_report(self, evaluation: D4DEvaluation, output_path: Path):
        """Generate detailed evaluation report for a single D4D file"""

        lines = []
        lines.append(
            f"# Detailed Evaluation: {evaluation.project} - {evaluation.method.upper()}")
        lines.append(f"\nEvaluated: {evaluation.timestamp}")
        lines.append(f"File: `{evaluation.file_path}`\n")

        lines.append("## Overall Scores\n")
        lines.append(
            f"- **Rubric10**: {evaluation.rubric10_total:.1f}/{evaluation.rubric10_max} ({evaluation.rubric10_percentage:.1f}%)")
        lines.append(
            f"- **Rubric20**: {evaluation.rubric20_total:.1f}/{evaluation.rubric20_max} ({evaluation.rubric20_percentage:.1f}%)\n")

        lines.append("## Rubric10 Element Scores\n")
        lines.append("| ID | Element | Score | Details |")
        lines.append("|----|---------|-------|---------|")

        for elem_score in evaluation.rubric10_scores:
            passed = sum(
                1 for s in elem_score.sub_element_scores if s.score == 1)
            failed = len(elem_score.sub_element_scores) - passed
            details = f"{passed}/5 sub-elements present"
            lines.append(
                f"| {elem_score.element_id} | {elem_score.name} | {elem_score.total_score}/5 | {details} |")

        lines.append("\n### Rubric10 Sub-Element Details\n")

        for elem_score in evaluation.rubric10_scores:
            lines.append(f"\n#### {elem_score.element_id}. {elem_score.name}")
            lines.append(f"\n{elem_score.description}\n")

            for sub_score in elem_score.sub_element_scores:
                status = "✅" if sub_score.score == 1 else "❌"
                lines.append(f"- {status} **{sub_score.name}**")
                if sub_score.found_values:
                    lines.append(f"  - Found: {sub_score.found_values[0]}")
                else:
                    lines.append(
                        f"  - Fields checked: {', '.join(sub_score.field_paths)}")

        lines.append("\n## Rubric20 Question Scores\n")

        # Group by category
        categories = {}
        for q_score in evaluation.rubric20_scores:
            if q_score.category not in categories:
                categories[q_score.category] = []
            categories[q_score.category].append(q_score)

        for category, questions in categories.items():
            lines.append(f"\n### {category}\n")
            lines.append("| ID | Question | Score | Status |")
            lines.append("|----|----------|-------|--------|")

            for q_score in questions:
                if q_score.score_type == "pass_fail":
                    score_str = q_score.score_label
                else:
                    score_str = f"{q_score.score:.1f}/{q_score.max_score}"

                status = "✅" if (q_score.score == 1 and q_score.score_type == "pass_fail") or (
                    q_score.score >= 3 and q_score.score_type == "numeric") else "❌"
                lines.append(
                    f"| {q_score.question_id} | {q_score.name} | {score_str} | {status} |")

        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

        print(f"Detailed report written to {output_path}")

    def export_scores_csv(self, evaluations: List[D4DEvaluation], output_path: Path):
        """Export all scores to CSV"""

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'project', 'method', 'label',
                'rubric10_total', 'rubric10_max', 'rubric10_percentage',
                'rubric20_total', 'rubric20_max', 'rubric20_percentage'
            ])

            # Data rows
            for eval in evaluations:
                writer.writerow([
                    eval.project,
                    eval.method,
                    eval.label or '',
                    eval.rubric10_total,
                    eval.rubric10_max,
                    eval.rubric10_percentage,
                    eval.rubric20_total,
                    eval.rubric20_max,
                    eval.rubric20_percentage
                ])

        print(f"Scores exported to {output_path}")

    def export_scores_json(self, evaluations: List[D4DEvaluation], output_path: Path):
        """Export all scores to JSON with full details"""

        # Convert dataclasses to dicts
        data = []
        for eval in evaluations:
            eval_dict = {
                'project': eval.project,
                'method': eval.method,
                'label': eval.label,
                'file_path': eval.file_path,
                'timestamp': eval.timestamp,
                'rubric10': {
                    'total': eval.rubric10_total,
                    'max': eval.rubric10_max,
                    'percentage': eval.rubric10_percentage,
                    'elements': []
                },
                'rubric20': {
                    'total': eval.rubric20_total,
                    'max': eval.rubric20_max,
                    'percentage': eval.rubric20_percentage,
                    'questions': []
                }
            }

            # Add rubric10 element details
            for elem_score in eval.rubric10_scores:
                eval_dict['rubric10']['elements'].append({
                    'id': elem_score.element_id,
                    'name': elem_score.name,
                    'score': elem_score.total_score,
                    'max_score': elem_score.max_score,
                    'sub_elements': [
                        {
                            'name': s.name,
                            'score': s.score,
                            'found': bool(s.found_values)
                        }
                        for s in elem_score.sub_element_scores
                    ]
                })

            # Add rubric20 question details
            for q_score in eval.rubric20_scores:
                eval_dict['rubric20']['questions'].append({
                    'id': q_score.question_id,
                    'name': q_score.name,
                    'category': q_score.category,
                    'score': q_score.score,
                    'max_score': q_score.max_score,
                    'score_label': q_score.score_label
                })

            data.append(eval_dict)

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Detailed scores exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate D4D YAML files using rubrics')
    parser.add_argument('--base-dir', type=str, default='data',
                        help='Base directory containing d4d_concatenated/ or d4d_individual/')
    parser.add_argument('--rubric10', type=str, default=str(RUBRIC10_PATH),
                        help='Path to rubric10.txt')
    parser.add_argument('--rubric20', type=str, default=str(RUBRIC20_PATH),
                        help='Path to rubric20.txt')
    parser.add_argument('--projects', nargs='+', default=PROJECTS,
                        help='Projects to evaluate (concatenated mode only)')
    parser.add_argument('--methods', nargs='+', default=['curated', 'gpt5', 'claudecode'],
                        help='Methods to evaluate (supported: curated, gpt5, claudecode)')
    parser.add_argument('--output-dir', type=str, default='data/evaluation',
                        help='Output directory for reports')
    parser.add_argument('--project', type=str,
                        help='Evaluate single project only (concatenated mode)')
    parser.add_argument('--individual', action='store_true',
                        help='Evaluate individual D4D files instead of concatenated')
    parser.add_argument('--include-invalid', action='store_true',
                        help='Evaluate records that fail schema validation too. '
                             'Presence detection works on any parseable YAML; '
                             'records generated under an older schema version '
                             'fail the current validator without being wrong '
                             '(#374), and skipping them silently excluded '
                             'whole sweeps from the scores.')

    args = parser.parse_args()

    # Override projects if single project specified
    if args.project:
        projects = [args.project]
    else:
        projects = args.projects

    # Create evaluator
    evaluator = D4DEvaluator(args.rubric10, args.rubric20)

    # Evaluate all files
    base_dir = Path(args.base_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Choose evaluation mode
    if args.individual:
        # Evaluate individual files
        # For individual mode, exclude 'curated' method as it doesn't have individual files
        methods = [m for m in args.methods if m != 'curated']
        evaluations = evaluator.evaluate_individual_files(base_dir, methods)
    else:
        # Evaluate concatenated files
        evaluations = evaluator.evaluate_all_projects(
            base_dir, projects, args.methods,
            include_invalid=args.include_invalid)

    if not evaluations:
        print("No evaluations completed!")
        return

    # Generate summary report
    summary_path = output_dir / "summary_report.md"
    evaluator.generate_summary_report(evaluations, summary_path)

    # Generate detailed reports
    detailed_dir = output_dir / "detailed_analysis"
    detailed_dir.mkdir(exist_ok=True)

    for evaluation in evaluations:
        # For individual files, use sanitized filename
        safe_project = evaluation.project.replace("/", "_").replace(" ", "_")
        # The label must be in the filename. Without it, replicates of one
        # method write to the same path and only the last one survives — the
        # report would silently describe one arbitrary run while appearing to
        # cover them all.
        parts = [safe_project, evaluation.method]
        if evaluation.label:
            parts.append(evaluation.label.replace("/", "_"))
        detail_path = detailed_dir / f"{'_'.join(parts)}_evaluation.md"
        evaluator.generate_detailed_report(evaluation, detail_path)

    # Export scores
    evaluator.export_scores_csv(evaluations, output_dir / "scores.csv")
    evaluator.export_scores_json(evaluations, output_dir / "scores.json")

    print(f"\n✅ Evaluation complete! Results in {output_dir}")


if __name__ == "__main__":
    main()
