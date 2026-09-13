"""Build a healthsheet-only generation input.

AI-READI is the only Grand Challenge that publishes a Healthsheet — 84
questions across 14 sections, served by the FAIRhub API. It stays in the
standard AI-READI corpus, because the corpus is meant to reflect what upstream
actually publishes rather than an artificially levelled set.

This module additionally extracts it as a **standalone** generation input, so
one further question can be asked: what does a D4D record look like when built
from the healthsheet alone, with no other documents?

The rendering is faithful — section, question, response, nothing else. No
question is dropped, no answer is summarized, and unanswered questions are
emitted as such rather than silently omitted, so the input shows its own gaps.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

OUTPUT_DIR = Path("data/preprocessed/concatenated")


# The upstream record and bundle name are the *active* profile's facts
# (#628, #1444), read when asked: the study's under `bridge2ai`, none under
# `neutral` — this module is the healthsheet renderer, not the study.
def default_record() -> Path | None:
    from data_sheets_schema.profiles import active_profile
    return active_profile().healthsheet_record


def bundle_name() -> str | None:
    from data_sheets_schema.profiles import active_profile
    return active_profile().healthsheet_bundle


def _record(record_path: Path | None) -> Path:
    path = record_path or default_record()
    if path is None:
        raise FileNotFoundError(
            "no healthsheet record: the active profile names none; pass one")
    return Path(path)
RULE = "=" * 80


@dataclass
class HealthsheetStats:
    sections: int = 0
    questions: int = 0
    answered: int = 0
    unanswered: list[str] = field(default_factory=list)


def load_healthsheet(record_path: Path | None = None) -> tuple[dict, dict]:
    """Return (healthsheet, whole record). Raises if the record has none."""
    record_path = _record(record_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    healthsheet = record.get("metadata", {}).get("healthsheet")
    if not healthsheet:
        raise KeyError(f"No healthsheet in {record_path}")
    return healthsheet, record


def render(healthsheet: dict, record: dict, source: Path) -> tuple[str, HealthsheetStats]:
    stats = HealthsheetStats()
    body: list[str] = []

    for section, items in healthsheet.items():
        if not isinstance(items, list):
            continue
        stats.sections += 1
        title = section.replace("_", " ").upper()
        body += ["", RULE, f"SECTION: {title}", RULE, ""]
        for item in items:
            stats.questions += 1
            question = str(item.get("question", "")).strip()
            response = str(item.get("response", "")).strip()
            body.append(f"Q: {question}")
            if response:
                stats.answered += 1
                body += ["A: " + response, ""]
            else:
                stats.unanswered.append(f"{section}:{item.get('id')}")
                body += ["A: (no response provided)", ""]

    header = [
        RULE,
        "HEALTHSHEET-ONLY SOURCE BUNDLE",
        RULE,
        "Project: AI_READI",
        f"Dataset: {record.get('title', '')}",
        f"DOI: {record.get('doi', '')}",
        f"Source: {source}",
        "Origin: FAIRhub API record, metadata.healthsheet",
        "",
        "This bundle contains the Healthsheet and nothing else — no publications,",
        "no documentation, no license, no IRB protocol. It exists to measure what",
        "a single structured upstream source yields on its own. It is NOT the",
        "AI-READI baseline; the baseline corpus carries all cited sources,",
        "including this one.",
        "",
        f"Sections: {stats.sections}",
        f"Questions: {stats.questions} ({stats.answered} answered, "
        f"{stats.questions - stats.answered} unanswered)",
        "",
        "Unanswered questions are shown explicitly rather than omitted, so the",
        "input's own coverage gaps are visible to whatever consumes it.",
        RULE,
    ]
    return "\n".join(header + body) + "\n", stats


def build_bundle(record_path: Path | None = None,
                 output_dir: Path = OUTPUT_DIR, *,
                 name: str | None = None) -> tuple[Path, HealthsheetStats]:
    """`name` is the bundle's file name: the caller's, else the active
    profile's, else derived from the record's stem."""
    record_path = _record(record_path)
    healthsheet, record = load_healthsheet(record_path)
    text, stats = render(healthsheet, record, record_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / (name or bundle_name() or f"{record_path.stem}_healthsheet_only.txt")
    target.write_text(text, encoding="utf-8")
    return target, stats
