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
import datetime
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

#: Primitive ranges that get scalar type checks. linkml's validator does not
#: check scalar coercion (even `linkml-validate` passes `count: not-a-number`
#: for an integer slot), so the linter does it here.
_INT_RE = re.compile(r"^[+-]?\d+$")
_BOOL_WORDS = frozenset(
    {"true", "false", "yes", "no", "y", "n", "on", "off", "1", "0"})
_DATE_FORMATS = ("%Y/%m/%d", "%d %B %Y", "%B %d, %Y", "%Y-%m", "%Y")
_DATETIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                     "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M")
_TIME_FORMATS = ("%H:%M:%S", "%H:%M")

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
# schema loading (cached; heavy imports stay local)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _schema_view(schema_path: str):
    from linkml_runtime import SchemaView

    return SchemaView(schema_path)


def _module_class_sections(schema_path: str) -> dict:
    """Map class name -> section name from the D4D module files.

    Falls back to the static table when the module sources are not beside
    the schema file.
    """
    schema_dir = Path(schema_path).parent
    mapping: dict = {}
    stems = {stem for stem, _ in SECTION_MODULES}
    found_any = False
    for module_file in sorted(schema_dir.glob("D4D_*.yaml")):
        if module_file.stem not in stems:
            continue
        try:
            doc = yaml.safe_load(module_file.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        section = dict(SECTION_MODULES)[module_file.stem]
        for class_name in (doc.get("classes") or {}):
            mapping[class_name] = section
        found_any = True
    if not found_any:
        mapping = dict(_FALLBACK_CLASS_SECTIONS)
    return mapping


@lru_cache(maxsize=4)
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
        import json

        return json.loads(text)
    return yaml.safe_load(text)


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
    from linkml.validator import validate
    from linkml.validator.report import Severity

    report = validate(data, schema_path, target_class=target_class)
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
    otherwise every key would be a false positive.
    """
    if not isinstance(data, dict):
        return
    slot_names: dict = {}
    if class_name and class_name in sv.all_classes():
        for s in sv.class_induced_slots(class_name):
            slot_names[s.name] = s
    else:
        return
    for key, value in data.items():
        child = _json_path(path, key)
        slot = slot_names.get(key)
        if slot is None:
            hint = ""
            close = difflib.get_close_matches(key, slot_names, n=1, cutoff=0.7)
            if close:
                hint = f"; did you mean '{close[0]}'?"
            issues.append(
                Issue(ERROR, "unknown-field", child,
                      f"Unknown field '{key}' for {class_name or 'instance'}{hint}")
            )
            continue
        _lint_value(key, value, slot, class_name, sv, child, issues)


def _strptime_any(text: str, formats) -> bool:
    text = text.strip()
    for fmt in formats:
        try:
            datetime.datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    return False


def _lint_scalar_type(key: str, value: Any, rng: str | None, path: str,
                      issues: list) -> None:
    """Scalar type checks linkml's validator skips (see module docstring)."""
    if rng == "integer":
        ok = ((isinstance(value, int) and not isinstance(value, bool))
              or (isinstance(value, str) and bool(_INT_RE.match(value.strip()))))
    elif rng in ("float", "double", "decimal"):
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        if not ok and isinstance(value, str):
            try:
                float(value.strip())
                ok = True
            except ValueError:
                ok = False
    elif rng == "boolean":
        ok = (isinstance(value, bool)
              or (isinstance(value, str)
                  and value.strip().lower() in _BOOL_WORDS))
    elif rng == "date":
        ok = (isinstance(value, datetime.date)
              or (isinstance(value, str)
                  and (_fromiso(value, "date") or _strptime_any(value, _DATE_FORMATS))))
    elif rng == "datetime":
        ok = (isinstance(value, datetime.datetime)
              or (isinstance(value, str)
                  and (_fromiso(value, "datetime")
                       or _strptime_any(value, _DATETIME_FORMATS))))
    elif rng == "time":
        ok = (isinstance(value, datetime.time)
              or (isinstance(value, str)
                  and (_fromiso(value, "time") or _strptime_any(value, _TIME_FORMATS))))
    else:
        return
    if not ok:
        issues.append(
            Issue(ERROR, "type-mismatch", path,
                  f"'{key}' should be {rng}, got {value!r}")
        )


def _fromiso(value: str, kind: str) -> bool:
    try:
        text = value.strip()
        if kind == "date":
            datetime.date.fromisoformat(text)
        elif kind == "datetime":
            datetime.datetime.fromisoformat(text)
        else:
            datetime.time.fromisoformat(text)
        return True
    except ValueError:
        return False


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
            _lint_scalar_type(key, value, rng, path, issues)
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
                    _lint_scalar_type(key, item, rng, item_path, issues)
            else:
                _lint_scalar_type(key, item, rng, item_path, issues)
        return
    _lint_scalar_type(key, value, rng, path, issues)


def _lint_spelling(key: str, text: str, path: str, issues: list) -> None:
    if key in NON_PROSE_SLOTS or "://" in text:
        return
    from data_sheets_schema import american_spelling

    for pattern, _fix in american_spelling.RULES:
        match = pattern.search(text)
        if match:
            issues.append(
                Issue(WARNING, "british-spelling", path,
                      f"'{key}' uses a British spelling ('{match.group(0)}'); "
                      "the datasheet convention is American English")
            )
            return


def _lint_identifiers(data: dict, issues: list) -> None:
    for slot in IDENTIFIER_SLOTS:
        if not _is_substantive(data.get(slot)):
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
        _lint_identifiers(data, issues)
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
    try:
        data = load_instance(p)
    except Exception as exc:
        report = LintReport(file=str(p), schema=str(schema_path),
                            target_class=target_class, valid=False)
        report.issues.append(
            Issue(ERROR, "unparseable", "/", f"Could not parse {p.name}: {exc}")
        )
        return report
    report = lint_instance(data, schema_path, target_class,
                           skip_schema_validation=skip_schema_validation)
    report.file = str(p)
    return report
