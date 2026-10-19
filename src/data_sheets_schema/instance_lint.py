"""In-process validator and linter for D4D data-sheet instances.

``linkml-validate`` checks schema conformance; this module is the
dataset-author-facing layer on top of it:

* schema validation run in-process (no ``poetry run`` subprocess), so it
  works from an installed wheel in any working directory;
* lint checks that go beyond schema validity — unknown fields (with
  did-you-mean hints), placeholder prose (``TBD``/``N/A``), empty values,
  missing identifier prose, British spellings, and per-section completeness
  against the Gebru et al. datasheet sections;
* a JSON-serialisable report plus a completeness score, so CI can gate on
  it.

Only the standard library, PyYAML and ``linkml``/``linkml-runtime`` (both
already core dependencies) are used. Heavy imports stay inside functions
so importing this module never slows down other ``d4d`` commands.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ERROR = "error"
WARNING = "warning"

#: Whole-value placeholders that signal an unanswered datasheet question.
PLACEHOLDER_VALUES = frozenset({
    "tbd", "todo", "n/a", "unknown", "?", "not applicable", "not stated",
})

#: Identifier prose every datasheet should carry (schema-optional, lint-warned).
IDENTIFIER_SLOTS = ("title", "name", "description")

#: Slots whose values are identifiers/locators, never prose to spell-check.
NON_PROSE_SLOTS = frozenset({
    "id", "page", "download_url", "doi", "publisher", "was_derived_from",
    "conforms_to", "conforms_to_class", "conforms_to_schema",
})

#: Sections every datasheet is expected to answer; an empty one warns.
ALWAYS_APPLICABLE_SECTIONS = (
    "Identification & metadata",
    "Motivation",
    "Composition",
    "Uses",
    "Distribution",
)

#: D4D module file stem -> human section name, in Gebru et al. order.
SECTION_MODULES = (
    ("D4D_Motivation", "Motivation"),
    ("D4D_Composition", "Composition"),
    ("D4D_Collection", "Collection process"),
    ("D4D_Preprocessing", "Preprocessing / cleaning / labeling"),
    ("D4D_Uses", "Uses"),
    ("D4D_Distribution", "Distribution"),
    ("D4D_Maintenance", "Maintenance"),
    ("D4D_Human", "Human subjects"),
    ("D4D_Ethics", "Ethics"),
    ("D4D_Data_Governance", "Data governance"),
)
METADATA_SECTION = "Identification & metadata"

#: Fallback class -> section when the D4D module files are not beside the
#: schema (e.g. a minimal install). Mirrors SECTION_MODULES above.
_FALLBACK_CLASS_SECTIONS = {
    # Motivation
    "Purpose": "Motivation", "Task": "Motivation", "AddressingGap": "Motivation",
    "Creator": "Motivation", "FundingMechanism": "Motivation",
    "Grantor": "Motivation", "Grant": "Motivation",
    # Composition
    "Instance": "Composition", "SamplingStrategy": "Composition",
    "MissingInfo": "Composition", "Relationships": "Composition",
    "Splits": "Composition", "DataAnomaly": "Composition",
    "DatasetBias": "Composition", "DatasetLimitation": "Composition",
    "ExternalResource": "Composition", "Confidentiality": "Composition",
    "ContentWarning": "Composition", "Subpopulation": "Composition",
    "Deidentification": "Composition", "SensitiveElement": "Composition",
    "DatasetRelationship": "Composition",
    # Collection
    "InstanceAcquisition": "Collection process",
    "CollectionMechanism": "Collection process",
    "DataCollector": "Collection process",
    "CollectionTimeframe": "Collection process",
    "DirectCollection": "Collection process",
    "MissingDataDocumentation": "Collection process",
    "RawDataSource": "Collection process",
    # Preprocessing
    "PreprocessingStrategy": "Preprocessing / cleaning / labeling",
    "CleaningStrategy": "Preprocessing / cleaning / labeling",
    "LabelingStrategy": "Preprocessing / cleaning / labeling",
    "RawData": "Preprocessing / cleaning / labeling",
    "ImputationProtocol": "Preprocessing / cleaning / labeling",
    "AnnotationAnalysis": "Preprocessing / cleaning / labeling",
    "MachineAnnotationTools": "Preprocessing / cleaning / labeling",
    # Uses
    "ExistingUse": "Uses", "UseRepository": "Uses", "OtherTask": "Uses",
    "FutureUseImpact": "Uses", "DiscouragedUse": "Uses",
    "IntendedUse": "Uses", "ProhibitedUse": "Uses",
    # Distribution
    "ThirdPartySharing": "Distribution", "DistributionFormat": "Distribution",
    "DistributionDate": "Distribution", "CoreDistribution": "Distribution",
    # Maintenance
    "Maintainer": "Maintenance", "Erratum": "Maintenance",
    "UpdatePlan": "Maintenance", "RetentionLimits": "Maintenance",
    "RetentionLimit": "Maintenance", "VersionAccess": "Maintenance",
    "ExtensionMechanism": "Maintenance",
    # Human subjects
    "HumanSubjectResearch": "Human subjects",
    "InformedConsent": "Human subjects",
    "ParticipantPrivacy": "Human subjects",
    "HumanSubjectCompensation": "Human subjects",
    "AtRiskPopulations": "Human subjects",
    # Ethics
    "EthicalReview": "Ethics", "DataProtectionImpact": "Ethics",
    "CollectionNotification": "Ethics", "CollectionConsent": "Ethics",
    "ConsentRevocation": "Ethics",
    # Governance
    "LicenseAndUseTerms": "Data governance", "IPRestrictions": "Data governance",
    "ExportControlRegulatoryRestrictions": "Data governance",
    "DataGovernance": "Data governance",
}


@dataclass
class Issue:
    """One validation or lint finding."""

    severity: str  # "error" | "warning"
    code: str
    path: str  # JSON-pointer-ish, e.g. "/purposes/0/statement"
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SectionCoverage:
    name: str
    total_slots: int
    populated_slots: int

    @property
    def coverage(self) -> int:
        if not self.total_slots:
            return 0
        return round(100 * self.populated_slots / self.total_slots)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_slots": self.total_slots,
            "populated_slots": self.populated_slots,
            "coverage": self.coverage,
        }


@dataclass
class LintReport:
    """The full validate/lint outcome for one instance file."""

    file: str
    schema: str
    target_class: str
    valid: bool
    issues: list = field(default_factory=list)
    sections: list = field(default_factory=list)
    schema_sha256: str = ""

    @property
    def errors(self) -> list:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> list:
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def completeness(self) -> int:
        coverages = [s.coverage for s in self.sections if s.total_slots]
        if not coverages:
            return 0
        return round(sum(coverages) / len(coverages))

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "schema": self.schema,
            "schema_sha256": self.schema_sha256,
            "target_class": self.target_class,
            "valid": self.valid,
            "summary": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "completeness": self.completeness,
            },
            "issues": [i.to_dict() for i in self.issues],
            "sections": [s.to_dict() for s in self.sections],
        }


# ---------------------------------------------------------------------------
# schema loading (cached by resolved path + a digest of the root and its
# transitive imports; heavy imports local)
# ---------------------------------------------------------------------------

def _schema_key(schema_path: str) -> tuple[str, str]:
    """(resolved path, sha256 of the root file): what the report records."""
    p = Path(schema_path)
    try:
        resolved = str(p.resolve())
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception as exc:
        raise ValueError(f"Invalid schema ({p.name}): {exc}") from exc
    return resolved, sha


def _cache_key(schema_path: str) -> tuple[str, str]:
    """(resolved path, digest of the root and its transitive imports), as
    shared_view keys its views: an edit confined to an imported module must
    not return the cached view or validator (#5082)."""
    from data_sheets_schema.schema_snapshot import capture_schema

    resolved, _ = _schema_key(schema_path)
    try:
        return resolved, capture_schema(resolved).key[1]
    except Exception as exc:
        raise ValueError(f"Invalid schema ({Path(schema_path).name}): {exc}") from exc


@lru_cache(maxsize=8)
def _schema_view_cached(resolved_path: str, closure_digest: str):
    # The package's shared view (#926): a view built here would be pinned by
    # linkml's class-level method caches for the life of the process (#5075).
    from data_sheets_schema.schema_view import shared_view

    try:
        sv = shared_view(resolved_path)
        sv.all_classes()
    except Exception as exc:
        raise ValueError(
            f"Invalid schema ({Path(resolved_path).name}): {exc}"
        ) from exc
    return sv


def _schema_view(schema_path: str):
    return _schema_view_cached(*_cache_key(schema_path))


@lru_cache(maxsize=8)
def _validator_cached(resolved_path: str, closure_digest: str):
    from linkml.validator import Validator
    from linkml.validator.plugins import JsonschemaValidationPlugin

    sv = _schema_view_cached(resolved_path, closure_digest)
    try:
        return Validator(
            sv.schema,
            validation_plugins=[JsonschemaValidationPlugin(closed=True)],
        )
    except Exception as exc:
        raise ValueError(
            f"Invalid schema ({Path(resolved_path).name}): {exc}"
        ) from exc


def _validator(schema_path: str):
    return _validator_cached(*_cache_key(schema_path))


def _module_class_sections(schema_path: str) -> dict:
    """Map class name -> section name from the D4D module files.

    Starts from ``_FALLBACK_CLASS_SECTIONS`` (which also covers Core-schema
    classes such as ``CoreDistribution``) and overlays any ``D4D_*.yaml``
    files from the packaged schema directory and from ``schema_path``'s parent
    directory using ``schema_cache.load_yaml``.
    """
    from data_sheets_schema import schema_cache
    from data_sheets_schema.constants import SCHEMA_DIR
    from data_sheets_schema.resources import resource_path

    mapping: dict = dict(_FALLBACK_CLASS_SECTIONS)
    stems = dict(SECTION_MODULES)
    candidate_dirs: list[Path] = []
    try:
        default_dir = resource_path(SCHEMA_DIR)
        if default_dir.is_dir():
            candidate_dirs.append(default_dir.resolve())
    except Exception:
        pass
    schema_dir = Path(schema_path).parent.resolve()
    if schema_dir not in candidate_dirs and schema_dir.is_dir():
        candidate_dirs.append(schema_dir)

    for directory in candidate_dirs:
        for module_file in sorted(directory.glob("D4D_*.yaml")):
            section = stems.get(module_file.stem)
            if section is None:
                continue
            try:
                doc = schema_cache.load_yaml(module_file) or {}
            except Exception:
                continue
            for class_name in (doc.get("classes") or {}):
                mapping[class_name] = section
    return mapping


def _class_sections(schema_path: str) -> dict:
    return _module_class_sections(schema_path)


def _section_for_slot(slot, sv, class_sections: dict) -> str:
    rng = getattr(slot, "range", None)
    if rng and rng in sv.all_classes() and rng in class_sections:
        return class_sections[rng]
    return METADATA_SECTION


# ---------------------------------------------------------------------------
# instance loading
# ---------------------------------------------------------------------------

def load_instance(path: str | Path) -> Any:
    """Load a YAML or JSON data-sheet instance (by file extension)."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _dup_json_path(dup: dict[str, Any]) -> str:
    raw_path = dup.get("path") or "$"
    key = dup.get("key", "")
    if raw_path == "$":
        return f"/{key}"
    norm = re.sub(r"\[(\d+)\]", r"/\1", raw_path).replace(".", "/")
    return f"/{norm}/{key}"


# ---------------------------------------------------------------------------
# value helpers
# ---------------------------------------------------------------------------

def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in PLACEHOLDER_VALUES


def _is_substantive(value: Any) -> bool:
    """A value that counts as an answered datasheet question."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not _is_placeholder(value)
    if isinstance(value, (list, tuple)):
        return any(_is_substantive(v) for v in value)
    if isinstance(value, dict):
        return any(_is_substantive(v) for v in value.values())
    return True


def _json_path(base: str, key: str) -> str:
    return f"{base}/{key}" if base else f"/{key}"


# ---------------------------------------------------------------------------
# schema validation (in-process linkml.validator)
# ---------------------------------------------------------------------------

def _run_schema_validation(
    data: Any, schema_path: str, target_class: str
) -> list:
    from linkml.validator.report import Severity

    validator = _validator(schema_path)
    report = validator.validate(data, target_class)
    issues = []
    for r in report.results:
        if r.severity == Severity.INFO:
            continue
        message = str(r.message)
        # Unknown fields are reported by the linter itself (with a
        # did-you-mean hint and a precise path); drop linkml's generic
        # "Additional properties are not allowed" duplicate.
        if "Additional properties are not allowed" in message:
            continue
        severity = ERROR if r.severity in (Severity.ERROR, Severity.FATAL) else WARNING
        issues.append(
            Issue(
                severity=severity,
                code="schema-violation",
                path=_result_path(message),
                message=message,
            )
        )
    return issues


# ---------------------------------------------------------------------------
# lint checks
# ---------------------------------------------------------------------------

def _result_path(message: str) -> str:
    """Extract the JSON path from a validator message.

    linkml 1.9's ``ValidationResult.instance`` carries the offending
    *value*, not a path; the path is appended to the message as
    ``... in /some/path`` (``/`` for the document root).
    """
    match = re.search(r" in (/[^ ]*)\s*$", message)
    return match.group(1) if match else "/"


def _lint_node(data: dict, class_name: str | None, sv, path: str, issues: list) -> None:
    """Recursively lint unknown fields, placeholders, empties, spelling.

    Unknown-field detection only runs when the enclosing class is known;
    otherwise every key would be a false positive. On nested objects
    (``path != ""``), slots from any descendant of ``class_name`` are
    permitted to match LinkML's ``include_range_class_descendants=True``
    polymorphic range semantics (e.g. ``DataSubset`` under ``Dataset.resources``).
    """
    if not isinstance(data, dict):
        return
    slot_names: dict = {}
    if class_name and class_name in sv.all_classes():
        candidate_classes = (
            sv.class_descendants(class_name, reflexive=True)
            if path
            else [class_name]
        )
        for cls in candidate_classes:
            for s in sv.class_induced_slots(cls):
                slot_names.setdefault(s.name, s)
    else:
        return
    for key, value in data.items():
        key_str = key if isinstance(key, str) else str(key)
        child = _json_path(path, key_str)
        slot = slot_names.get(key) if isinstance(key, str) else None
        if slot is None:
            hint = ""
            if isinstance(key, str):
                close = difflib.get_close_matches(key, slot_names, n=1, cutoff=0.7)
                if close:
                    hint = f"; did you mean '{close[0]}'?"
            issues.append(
                Issue(ERROR, "unknown-field", child,
                      f"Unknown field '{key_str}' for {class_name or 'instance'}{hint}")
            )
            continue
        _lint_value(key_str, value, slot, class_name, sv, child, issues)


def _lint_value(key, value, slot, class_name, sv, path: str, issues: list) -> None:
    if value is None:
        return
    rng = getattr(slot, "range", None)
    if isinstance(value, str):
        if not value.strip():
            issues.append(Issue(WARNING, "empty-value", path,
                                f"'{key}' is an empty string"))
        elif _is_placeholder(value):
            issues.append(Issue(WARNING, "placeholder-value", path,
                                f"'{key}' holds a placeholder ('{value.strip()}') "
                                "instead of an answer"))
        else:
            _lint_spelling(key, value, path, issues)
        return
    if isinstance(value, dict):
        # Only descend when the range names a schema class; otherwise the
        # keys cannot be checked against induced slots.
        if rng in sv.all_classes():
            _lint_node(value, rng, sv, path, issues)
        return
    if isinstance(value, (list, tuple)):
        item_class = rng if rng in sv.all_classes() else None
        for i, item in enumerate(value):
            item_path = f"{path}/{i}"
            if isinstance(item, dict):
                if item_class:
                    _lint_node(item, item_class, sv, item_path, issues)
            elif isinstance(item, str):
                if not item.strip():
                    issues.append(Issue(WARNING, "empty-value", item_path,
                                        f"'{key}' contains an empty string"))
                elif _is_placeholder(item):
                    issues.append(Issue(WARNING, "placeholder-value", item_path,
                                        f"'{key}' holds a placeholder "
                                        f"('{item.strip()}') instead of an answer"))
                else:
                    _lint_spelling(key, item, item_path, issues)


def _lint_spelling(key: str, text: str, path: str, issues: list) -> None:
    if key in NON_PROSE_SLOTS:
        return
    from data_sheets_schema import american_spelling

    if american_spelling._verbatim(key):
        return
    _, rewrites, _ = american_spelling.americanise(text)
    if rewrites:
        british_word, _ = rewrites[0]
        issues.append(
            Issue(WARNING, "british-spelling", path,
                  f"'{key}' uses a British spelling ('{british_word}'); "
                  "the datasheet convention is American English")
        )


def _lint_identifiers(data: dict, target_class: str, sv, issues: list) -> None:
    induced = {s.name for s in sv.class_induced_slots(target_class)}
    for slot in IDENTIFIER_SLOTS:
        if slot in induced and not _is_substantive(data.get(slot)):
            issues.append(
                Issue(WARNING, "missing-identifier", f"/{slot}",
                      f"'{slot}' is missing or empty; every datasheet should "
                      "carry identifier prose")
            )


def _section_coverage(data: dict, target_class: str, sv, class_sections: dict) -> list:
    sections: dict = {}
    order: list = []

    def section(name: str) -> dict:
        if name not in sections:
            sections[name] = {"total": 0, "populated": 0}
            order.append(name)
        return sections[name]

    for slot in sv.class_induced_slots(target_class):
        sec = section(_section_for_slot(slot, sv, class_sections))
        sec["total"] += 1
        if _is_substantive(data.get(slot.name)):
            sec["populated"] += 1
    return [
        SectionCoverage(name=n, total_slots=sections[n]["total"],
                        populated_slots=sections[n]["populated"])
        for n in order
    ]


# ---------------------------------------------------------------------------
# public entry points
# ---------------------------------------------------------------------------

def lint_instance(
    data: Any,
    schema_path: str,
    target_class: str,
    *,
    skip_schema_validation: bool = False,
) -> LintReport:
    """Validate and lint one loaded instance; return the report."""
    _, schema_sha256 = _schema_key(schema_path)
    sv = _schema_view(schema_path)
    if target_class not in sv.all_classes():
        raise ValueError(
            f"Target class '{target_class}' is not in the schema "
            f"({Path(schema_path).name})"
        )
    issues: list = []
    if isinstance(data, dict) and not skip_schema_validation:
        issues.extend(_run_schema_validation(data, schema_path, target_class))

    sections: list = []
    if isinstance(data, dict):
        _lint_node(data, target_class, sv, "", issues)
        _lint_identifiers(data, target_class, sv, issues)
        class_sections = _class_sections(schema_path)
        sections = _section_coverage(data, target_class, sv, class_sections)
        for sec in sections:
            if sec.populated_slots == 0 and sec.name in ALWAYS_APPLICABLE_SECTIONS:
                issues.append(
                    Issue(WARNING, "empty-section", "/",
                          f"Section '{sec.name}' has no answered questions "
                          f"({sec.total_slots} slots, none populated)")
                )
    else:
        issues.append(
            Issue(ERROR, "not-a-mapping", "/",
                  f"Instance must be a mapping for {target_class}, "
                  f"got {type(data).__name__}")
        )

    valid = not any(i.severity == ERROR for i in issues)
    return LintReport(
        file="",
        schema=str(schema_path),
        target_class=target_class,
        valid=valid,
        issues=issues,
        sections=sections,
        schema_sha256=schema_sha256,
    )


def lint_file(
    path: str | Path,
    schema_path: str,
    target_class: str,
    *,
    skip_schema_validation: bool = False,
) -> LintReport:
    """Load, validate and lint one instance file; return the report."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Instance file not found: {path}")
    _, schema_sha256 = _schema_key(schema_path)
    sv = _schema_view(schema_path)
    if target_class not in sv.all_classes():
        raise ValueError(
            f"Target class '{target_class}' is not in the schema "
            f"({Path(schema_path).name})"
        )
    if not skip_schema_validation:
        _validator(schema_path)

    from data_sheets_schema import duplicate_keys

    try:
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() == ".json":
            data = json.loads(text)
            dups = duplicate_keys.find_duplicate_keys(text)
        else:
            dups = duplicate_keys.find_duplicate_keys(text, strict=True)
            data = yaml.safe_load(text)
    except Exception as exc:
        report = LintReport(
            file=str(p),
            schema=str(schema_path),
            target_class=target_class,
            valid=False,
            schema_sha256=schema_sha256,
        )
        report.issues.append(
            Issue(ERROR, "unparseable", "/", f"Could not parse {p.name}: {exc}")
        )
        return report

    report = lint_instance(data, schema_path, target_class,
                           skip_schema_validation=skip_schema_validation)
    report.file = str(p)
    if dups:
        for dup in dups:
            report.issues.append(
                Issue(
                    ERROR,
                    "duplicate-key",
                    _dup_json_path(dup),
                    duplicate_keys.describe([dup]),
                )
            )
        report.valid = not any(i.severity == ERROR for i in report.issues)
    return report
