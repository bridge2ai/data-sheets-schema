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
import hashlib
import re
import csv
import subprocess
import tempfile
import uuid
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from data_sheets_schema.constants import RUBRIC10_PATH, RUBRIC20_PATH
from data_sheets_schema.evaluation_context import (
    COLLECTION_POLICY, applicability, context_digest, dataset_units, field_values,
    identity, load_context, load_document, normalize_context, unwrap_document,
)

SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

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
    - Class-wrapped datasets and collections → unwrap and validate the whole
      declared class, including every resource
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

    # The method is an open identity; core selection also follows the actual
    # class declaration or file convention used by arbitrary pipeline methods.
    if method.endswith("_core") or "_core" in Path(file_path).stem:
        schema_file, class_name = _METHOD_SCHEMA["claudecode_agent_core"]

    # Unwrap the class envelope, retaining every collection resource.
    validate_path = file_path
    tmp_file = None
    try:
        with open(file_path, "r", encoding="utf-8-sig") as fh:
            top = yaml.safe_load(fh)
        document = unwrap_document(top)
        dataset_units(document)  # reject empty or malformed collections
        wrappers = {"Dataset", "CoreDataset", "DatasetCollection", "CoreDatasetCollection"} & set(top)
        if wrappers:
            class_name = next(iter(wrappers))
            schema_file = (_METHOD_SCHEMA["claudecode_agent_core"][0]
                           if class_name.startswith("Core") else _DEFAULT_SCHEMA[0])
        else:
            declared = str(document.get("conforms_to_class", ""))
            match = re.search(r"(?:^|[/#:])(CoreDataset(?:Collection)?|Dataset(?:Collection)?)$", declared)
            if match:
                class_name = match.group(1)
            elif "distributions" in document:
                class_name = "CoreDataset"
            if "resources" in document:
                class_name = "CoreDatasetCollection" if class_name.startswith("Core") else "DatasetCollection"
            schema_file = (_METHOD_SCHEMA["claudecode_agent_core"][0]
                           if class_name.startswith("Core") else _DEFAULT_SCHEMA[0])
        if wrappers:
            tmp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False, encoding="utf-8")
            yaml.safe_dump(document, tmp_file)
            tmp_file.close()
            validate_path = Path(tmp_file.name)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"Validation failed for {file_path}: {exc}")
        return False

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
    score: Optional[int]  # 0 or 1; None when not applicable
    found_values: List[str]  # Actual values found in D4D file
    applicable: bool = True
    applicability_status: str = "applicable"
    applicability_evidence: str = "Unconditional item"
    unit_scores: List[Dict[str, Any]] = field(default_factory=list)


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
    score: Optional[float]  # None when not applicable
    max_score: int
    score_label: str  # Description of the score level
    found_values: List[str]
    applicable: bool = True
    applicability_status: str = "applicable"
    applicability_evidence: str = "Unconditional item"
    fixed_max_score: int = 5
    unit_scores: List[Dict[str, Any]] = field(default_factory=list)


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
    rubric10_percentage: Optional[float]
    rubric20_total: float
    rubric20_max: int
    rubric20_percentage: Optional[float]
    # Run label, e.g. "2026-07-28_claude-opus-5-generic_rep1". None for methods
    # stored flat (one record per method). Without it, three replicates of one
    # method collapse onto the same key and silently overwrite each other —
    # which is why every score here was previously one unlabelled row per
    # (project, method).
    label: Optional[str] = None
    instrument: Dict[str, Any] = field(default_factory=dict)
    applicability_context: Dict[str, Any] = field(default_factory=dict)
    excluded_items: Dict[str, List[str]] = field(default_factory=dict)
    evaluation_scope: Dict[str, Any] = field(default_factory=dict)
    rubric10_fixed_max: int = 50
    rubric20_fixed_max: int = 88


class D4DEvaluator:
    """Main evaluator class for D4D YAML files"""

    def __init__(self, rubric10_path: str, rubric20_path: str, *, context: dict | None = None):
        self.rubric10_path = Path(rubric10_path)
        self.rubric20_path = Path(rubric20_path)
        self._rubric_bytes = {}
        self.rubric10 = self._load_rubric10()
        self.rubric20 = self._load_rubric20()
        self.context = normalize_context(context)
        from data_sheets_schema import evaluation_context
        pins = {"rubric10": hashlib.sha256(self._rubric_bytes["rubric10"]).hexdigest(),
                "rubric20": hashlib.sha256(self._rubric_bytes["rubric20"]).hexdigest(),
                "runner": SOURCE_SHA256,
                "context_policy": evaluation_context.SOURCE_SHA256}
        self.instrument = {"kind": "deterministic_presence", "version": "2.0",
                           "sha256": hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest(),
                           "inputs": pins}

    def _load_rubric10(self) -> Dict[str, Any]:
        """Load and parse rubric10.txt"""
        raw = self.rubric10_path.read_bytes()
        self._rubric_bytes["rubric10"] = raw
        return yaml.safe_load(raw)

    def _load_rubric20(self) -> Dict[str, Any]:
        """Load and parse rubric20.txt"""
        raw = self.rubric20_path.read_bytes()
        self._rubric_bytes["rubric20"] = raw
        return yaml.safe_load(raw)

    def _load_d4d_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Keep every dataset resource; only remove an optional class wrapper."""
        return load_document(file_path)[0]

    def _extract_field_value(self, d4d_data: Dict[str, Any], field_path: str) -> Optional[Any]:
        values = [value for _, value in field_values(d4d_data, field_path)]
        return values[0] if len(values) == 1 else values or None

    def _is_field_present(self, d4d_data: Dict[str, Any], field_paths: List[str]) -> Tuple[bool, List[str]]:
        found = []
        for field_path in field_paths:
            for pointer, value in field_values(d4d_data, field_path):
                meaningful = ((isinstance(value, str) and bool(value.strip()))
                              or isinstance(value, (int, float, bool))
                              or (isinstance(value, (list, dict)) and bool(value)))
                if meaningful:
                    found.append(f"{pointer}: {str(value)[:100]}")
        return bool(found), found

    def _score_rubric10_element(self, d4d_data: Dict[str, Any], element: Dict[str, Any]) -> ElementScore:
        """For a collection, credit an item only when every resource supplies it."""
        sub_element_scores = []
        units = dataset_units(d4d_data)
        for sub_elem in element['sub_elements']:
            paths = sub_elem['field']
            field_paths = [paths] if isinstance(paths, str) else paths
            decision = applicability(sub_elem.get('applies_to', element.get('applies_to')), self.context)
            unit_scores, evidence = [], []
            for pointer, unit in units:
                present, values = self._is_field_present(unit, field_paths)
                unit_scores.append({"path": pointer, "score": int(present) if decision.applicable else None})
                evidence.extend(pointer + value for value in values)
            score = min(row['score'] for row in unit_scores) if decision.applicable else None
            sub_element_scores.append(SubElementScore(
                name=sub_elem['name'], field_paths=field_paths, score=score,
                found_values=evidence, applicable=decision.applicable,
                applicability_status=decision.status, applicability_evidence=decision.evidence,
                unit_scores=unit_scores))
        return ElementScore(
            element_id=element['id'], name=element['name'], description=element['description'],
            sub_element_scores=sub_element_scores,
            total_score=sum(row.score or 0 for row in sub_element_scores),
            max_score=sum(row.applicable for row in sub_element_scores))

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
        found = {}
        for field_path in field_paths:
            for pointer, value in field_values(d4d_data, field_path):
                if value is not None and value != "" and value != [] and value != {}:
                    found[pointer] = value
        return list(found.values())

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
        aliases = {"text/csv": "csv", "text/tab-separated-values": "tsv",
                   "application/json": "json", "application/ld+json": "jsonld",
                   "application/xml": "xml", "text/xml": "xml",
                   "text/plain": "txt", "image/png": "png", "image/jpeg": "jpeg",
                   "jpg": "jpeg", "image/tiff": "tiff", "tif": "tiff",
                   "application/pdf": "pdf", "application/dicom": "dicom"}
        def canonical(value):
            token = str(value).strip().lower().split(";", 1)[0].strip().lstrip(".")
            return aliases.get(token, token)
        for v in found_values:
            items = v if isinstance(v, (list, tuple)) else [v]
            for it in items:
                if isinstance(it, dict):
                    for key in ("format", "file_type", "media_type", "type",
                                "extension"):
                        if it.get(key):
                            seen.add(canonical(it[key]))
                            break
                elif it is not None:
                    seen.add(canonical(it))
        return len(seen)

    def _score_rubric20_question(self, d4d_data: Dict[str, Any], question: Dict[str, Any]) -> QuestionScore:
        paths = question['field']
        field_paths = [paths] if isinstance(paths, str) else paths
        decision = applicability(question.get('applies_to'), self.context)
        score_type = question['score_type']
        fixed_max = 1 if score_type == 'pass_fail' else 5
        unit_scores, evidence = [], []
        for pointer, unit in dataset_units(d4d_data):
            present, values = self._is_field_present(unit, field_paths)
            if not decision.applicable:
                score, label = None, "Not applicable"
            elif score_type == 'pass_fail':
                score, label = int(present), "Pass" if present else "Fail"
            else:
                score, label = self._score_numeric_rubric20(question, unit, field_paths, present, values)
            unit_scores.append({"path": pointer, "score": score, "label": label})
            evidence.extend(pointer + value for value in values)
        selected = min(unit_scores, key=lambda row: row['score'] or 0)
        return QuestionScore(
            question_id=question['id'], name=question['name'], description=question['description'],
            category=self._get_question_category(question['id']), score_type=score_type,
            score=selected['score'], max_score=fixed_max if decision.applicable else 0,
            score_label=selected['label'], found_values=evidence,
            applicable=decision.applicable, applicability_status=decision.status,
            applicability_evidence=decision.evidence, fixed_max_score=fixed_max, unit_scores=unit_scores)

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
        identity(project, "project")
        identity(method, "method")
        d4d_data, input_sha256 = load_document(file_path)
        units = dataset_units(d4d_data)

        # Score rubric10
        rubric10_scores = []
        for element in self.rubric10['d4d_complex_proxy_rubric']['rubric']:
            element_score = self._score_rubric10_element(d4d_data, element)
            rubric10_scores.append(element_score)

        rubric10_total = sum(s.total_score for s in rubric10_scores)
        rubric10_max = sum(s.max_score for s in rubric10_scores)
        rubric10_percentage = (
            rubric10_total / rubric10_max * 100) if rubric10_max > 0 else None

        # Score rubric20
        rubric20_scores = []
        for question in self.rubric20['d4d_evaluation_rubric']['rubric']:
            question_score = self._score_rubric20_question(d4d_data, question)
            rubric20_scores.append(question_score)

        rubric20_total = sum(s.score or 0 for s in rubric20_scores)
        rubric20_max = sum(s.max_score for s in rubric20_scores)
        rubric20_percentage = (
            rubric20_total / rubric20_max * 100) if rubric20_max > 0 else None

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
            instrument={**self.instrument, "input_sha256": input_sha256,
                        "context_sha256": context_digest(self.context)},
            applicability_context=self.context,
            excluded_items={
                "rubric10": [f"E{element.element_id}.{index}" for element in rubric10_scores
                             for index, sub in enumerate(element.sub_element_scores, 1) if not sub.applicable],
                "rubric20": [f"Q{question.question_id}" for question in rubric20_scores if not question.applicable]},
            evaluation_scope={"policy": COLLECTION_POLICY if len(units) > 1 else "single_dataset",
                              "units": [{"path": path, "id": unit.get("id")} for path, unit in units],
                              "collection_metadata_inherited": False},
            rubric10_fixed_max=sum(len(e.sub_element_scores) for e in rubric10_scores),
            rubric20_fixed_max=sum(q.fixed_max_score for q in rubric20_scores),
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

    def evaluate_individual_files(self, base_dir: Path, methods: List[str],
                                  projects: List[str] | None = None) -> List[D4DEvaluation]:
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
                if projects and project not in projects:
                    continue
                file_id = file_path.stem.replace("_d4d", "")

                print(f"  - {project}/{file_id}...")

                evaluation = self.evaluate_d4d_file(
                    file_path, f"{project}/{file_id}", method)
                evaluations.append(evaluation)

        return evaluations

    def generate_summary_report(self, evaluations: List[D4DEvaluation], output_path: Path):
        """List every declared identity and run without pooling unlike assessments."""
        lines = ["# D4D Presence Evaluation Summary", "",
                 "Scores measure field presence and coverage, not semantic quality.",
                 "Collection scores use the minimum item score across every terminal resource; "
                 "collection metadata is not implicitly inherited by children.",
                 "Adjusted scores must not be pooled or ranked across different comparison groups.", ""]
        for rubric in ("rubric10", "rubric20"):
            lines += [f"## {rubric}", "",
                      "| Project | Method | Run | Points | Fixed % | Adjusted % | Excluded items | Comparison group |",
                      "|---|---|---|---:|---:|---:|---|---|"]
            for result in evaluations:
                total = getattr(result, rubric + "_total")
                maximum = getattr(result, rubric + "_max")
                fixed = getattr(result, rubric + "_fixed_max")
                percentage = getattr(result, rubric + "_percentage")
                excluded = result.excluded_items.get(rubric, [])
                basis = {"instrument": result.instrument.get("sha256"),
                         "context": result.instrument.get("context_sha256"),
                         "excluded": excluded,
                         "policy": result.evaluation_scope.get("policy"),
                         "units": len(result.evaluation_scope.get("units", []))}
                group = hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()[:12]
                cells = [result.project, result.method, result.label or "—", f"{total:g}/{maximum}",
                         f"{total / fixed * 100:.1f}" if fixed else "N/A",
                         f"{percentage:.1f}" if percentage is not None else "N/A",
                         ", ".join(excluded) or "none", group]
                lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ")
                                                for cell in cells) + " |")
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Summary report written to {output_path}")

    def generate_detailed_report(self, evaluation: D4DEvaluation, output_path: Path):
        """Generate detailed evaluation report for a single D4D file"""

        lines = []
        lines.append(
            f"# Detailed Evaluation: {evaluation.project} - {evaluation.method.upper()}")
        lines.append(f"\nEvaluated: {evaluation.timestamp}")
        lines.append(f"File: `{evaluation.file_path}`\n")
        lines.append(f"Instrument: `{evaluation.instrument.get('sha256', 'unrecorded')}`")
        lines.append(f"Applicability context: `{evaluation.instrument.get('context_sha256', 'unrecorded')}`")
        lines.append(f"Scope: {evaluation.evaluation_scope.get('policy', 'single_dataset')}")

        lines.append("## Overall Scores\n")
        lines.append(
            f"- **Rubric10**: {evaluation.rubric10_total:.1f}/{evaluation.rubric10_max} ({_percentage_text(evaluation.rubric10_percentage)})")
        lines.append(
            f"- **Rubric20**: {evaluation.rubric20_total:.1f}/{evaluation.rubric20_max} ({_percentage_text(evaluation.rubric20_percentage)})\n")

        lines.append("## Rubric10 Element Scores\n")
        lines.append("| ID | Element | Score | Details |")
        lines.append("|----|---------|-------|---------|")

        for elem_score in evaluation.rubric10_scores:
            passed = sum(
                1 for s in elem_score.sub_element_scores if s.score == 1)
            excluded = sum(not s.applicable for s in elem_score.sub_element_scores)
            details = f"{passed}/{elem_score.max_score} applicable sub-elements present; {excluded} N/A"
            lines.append(
                f"| {elem_score.element_id} | {elem_score.name} | {elem_score.total_score}/{elem_score.max_score} | {details} |")

        lines.append("\n### Rubric10 Sub-Element Details\n")

        for elem_score in evaluation.rubric10_scores:
            lines.append(f"\n#### {elem_score.element_id}. {elem_score.name}")
            lines.append(f"\n{elem_score.description}\n")

            for sub_score in elem_score.sub_element_scores:
                status = "N/A" if not sub_score.applicable else "✅" if sub_score.score == 1 else "❌"
                lines.append(f"- {status} **{sub_score.name}**")
                lines.append(f"  - Applicability: {sub_score.applicability_status}; {sub_score.applicability_evidence}")
                if sub_score.found_values:
                    lines.extend(f"  - Found: {value}" for value in sub_score.found_values)
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
                if not q_score.applicable:
                    score_str = "N/A"
                elif q_score.score_type == "pass_fail":
                    score_str = q_score.score_label
                else:
                    score_str = f"{q_score.score:.1f}/{q_score.max_score}"

                status = ("N/A" if not q_score.applicable else "✅" if
                          (q_score.score == 1 and q_score.score_type == "pass_fail") or
                          ((q_score.score or 0) >= 3 and q_score.score_type == "numeric") else "❌")
                lines.append(
                    f"| {q_score.question_id} | {q_score.name} | {score_str} | {status} |")
            for q_score in questions:
                lines.append(f"\nApplicability for Q{q_score.question_id}: {q_score.applicability_status}; "
                             f"{q_score.applicability_evidence}\n")

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
                'rubric20_total', 'rubric20_max', 'rubric20_percentage',
                'rubric10_fixed_max', 'rubric20_fixed_max', 'excluded_items',
                'instrument_sha256', 'context_sha256', 'evaluation_scope'
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
                    eval.rubric20_percentage,
                    eval.rubric10_fixed_max, eval.rubric20_fixed_max,
                    json.dumps(eval.excluded_items, sort_keys=True),
                    eval.instrument.get('sha256'), eval.instrument.get('context_sha256'),
                    json.dumps(eval.evaluation_scope, sort_keys=True)
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
                'instrument': eval.instrument,
                'applicability_context': eval.applicability_context,
                'excluded_items': eval.excluded_items,
                'evaluation_scope': eval.evaluation_scope,
                'rubric10': {
                    'total': eval.rubric10_total,
                    'max': eval.rubric10_max,
                    'fixed_max': eval.rubric10_fixed_max,
                    'fixed_percentage': (eval.rubric10_total / eval.rubric10_fixed_max * 100
                                         if eval.rubric10_fixed_max else None),
                    'percentage': eval.rubric10_percentage,
                    'elements': []
                },
                'rubric20': {
                    'total': eval.rubric20_total,
                    'max': eval.rubric20_max,
                    'fixed_max': eval.rubric20_fixed_max,
                    'fixed_percentage': (eval.rubric20_total / eval.rubric20_fixed_max * 100
                                         if eval.rubric20_fixed_max else None),
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
                            'found': bool(s.found_values),
                            'evidence': s.found_values,
                            'applicable': s.applicable,
                            'applicability_status': s.applicability_status,
                            'applicability_evidence': s.applicability_evidence,
                            'unit_scores': s.unit_scores
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
                    'score_label': q_score.score_label,
                    'applicable': q_score.applicable,
                    'applicability_status': q_score.applicability_status,
                    'applicability_evidence': q_score.applicability_evidence,
                    'fixed_max_score': q_score.fixed_max_score,
                    'unit_scores': q_score.unit_scores,
                    'evidence': q_score.found_values
                })

            data.append(eval_dict)

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Detailed scores exported to {output_path}")


def _percentage_text(value):
    return f"{value:.1f}%" if value is not None else "N/A"


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate D4D YAML files using rubrics')
    parser.add_argument('--base-dir', type=str, default='data',
                        help='Base directory containing d4d_concatenated/ or d4d_individual/')
    parser.add_argument('--file', type=Path, help='One explicit D4D file; requires --project and one --methods value')
    parser.add_argument('--context', type=Path, help='YAML/JSON applicability declarations')
    parser.add_argument('--rubric10', type=str, default=str(RUBRIC10_PATH),
                        help='Path to rubric10.txt')
    parser.add_argument('--rubric20', type=str, default=str(RUBRIC20_PATH),
                        help='Path to rubric20.txt')
    parser.add_argument('--projects', nargs='+', default=None,
                        help='Projects to evaluate (concatenated mode only)')
    parser.add_argument('--methods', nargs='+', default=None,
                        help='Declared methods; otherwise discover method directories')
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
    if args.file and (not args.project or not args.methods or len(args.methods) != 1 or args.individual):
        parser.error("--file requires --project, exactly one --methods value, and no --individual")
    base_dir = Path(args.base_dir)
    if args.methods is None:
        directory = base_dir / ("d4d_individual" if args.individual else "d4d_concatenated")
        args.methods = sorted(path.name for path in directory.iterdir() if path.is_dir()) if directory.is_dir() else []

    # Override projects if single project specified
    if args.project:
        projects = [args.project]
    else:
        projects = args.projects or []
        if not projects and not args.individual:
            found = set()
            for method in args.methods:
                directory = base_dir / "d4d_concatenated" / method
                for suffix in ("_d4d_core.yaml", "_d4d.yaml", "_curated.yaml"):
                    found.update(path.name[:-len(suffix)] for path in directory.rglob("*" + suffix))
            projects = sorted(found)

    # Create evaluator
    evaluator = D4DEvaluator(args.rubric10, args.rubric20, context=load_context(args.context))

    # Evaluate all files
    output_dir = Path(args.output_dir) / (
        datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_presence-v2_" +
        evaluator.instrument["sha256"][:12] + "_" + uuid.uuid4().hex[:8])

    # Choose evaluation mode
    if args.file:
        if not args.include_invalid and not validate_d4d_yaml(args.file, args.methods[0]):
            parser.error("D4D validation failed; --include-invalid explicitly permits presence-only inspection")
        evaluations = [evaluator.evaluate_d4d_file(args.file, args.project, args.methods[0])]
    elif args.individual:
        evaluations = evaluator.evaluate_individual_files(base_dir, args.methods, projects=projects)
    else:
        # Evaluate concatenated files
        evaluations = evaluator.evaluate_all_projects(
            base_dir, projects, args.methods,
            include_invalid=args.include_invalid)

    if not evaluations:
        parser.error("no D4D records matched the selected inputs")
    output_dir.mkdir(parents=True, exist_ok=False)

    # Generate summary report
    summary_path = output_dir / "summary_report.md"
    evaluator.generate_summary_report(evaluations, summary_path)

    # Generate detailed reports
    detailed_dir = output_dir / "detailed_analysis"
    detailed_dir.mkdir(exist_ok=True)

    for evaluation in evaluations:
        # For individual files, use sanitized filename
        def safe_token(value):
            return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:80] + "-" + hashlib.sha256(value.encode()).hexdigest()[:8]
        safe_project = safe_token(evaluation.project)
        # The label must be in the filename. Without it, replicates of one
        # method write to the same path and only the last one survives — the
        # report would silently describe one arbitrary run while appearing to
        # cover them all.
        parts = [safe_project, safe_token(evaluation.method)]
        if evaluation.label:
            parts.append(safe_token(evaluation.label))
        detail_path = detailed_dir / f"{'_'.join(parts)}_evaluation.md"
        evaluator.generate_detailed_report(evaluation, detail_path)

    # Export scores
    evaluator.export_scores_csv(evaluations, output_dir / "scores.csv")
    evaluator.export_scores_json(evaluations, output_dir / "scores.json")

    print(f"\n✅ Evaluation complete! Results in {output_dir}")


if __name__ == "__main__":
    main()
