"""Build a healthsheet-only generation input.

A dataset whose upstream record carries a Healthsheet (in the study, one
does: 84 questions across 14 sections, served by its repository's API —
the record, bundle name and project are the profile's facts, #628) keeps
it in its standard corpus, because the corpus is meant to reflect what
upstream actually publishes rather than an artificially levelled set.

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
    from data_sheets_schema.chunking import anchored
    path = record_path if record_path is not None else (anchored(default_record()) if default_record() else None)   # from any directory (#1567)
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


def _project(project: str | None) -> str:
    """The dataset the bundle is about: the caller's, else the active
    profile's; never a literal (#1464)."""
    from data_sheets_schema.profiles import active_profile
    name = project or active_profile().healthsheet_project
    if not name:
        raise ValueError("no project for the healthsheet bundle: the active profile names none; pass one")
    return name


def _shown(source: Path) -> str:
    """The record's path as the bundle names it: repository-relative under
    the checkout, so the bytes do not depend on how the caller spelled it
    (#1564)."""
    import os
    from data_sheets_schema.chunking import corpus_root
    REPO_ROOT = corpus_root()                      # the checkout the run's corpus is anchored on (#1640)
    p = Path(source)
    try:
        r = p.resolve()
        if REPO_ROOT is not None and (r == REPO_ROOT.resolve() or REPO_ROOT.resolve() in r.parents):
            return os.path.relpath(r, REPO_ROOT)
    except OSError:
        pass
    return str(source)


def render(healthsheet: dict, record: dict, source: Path, *,
           project: str | None = None,
           display: str | None = None) -> tuple[str, HealthsheetStats]:
    """`display` is the dataset's name in prose (the profile's for its own
    record — the tracked bundle's bytes depend on it, #1542); the key otherwise."""
    project = _project(project)
    display = display or project
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
        f"Project: {project}",
        f"Dataset: {record.get('title', '')}",
        f"DOI: {record.get('doi', '')}",
        f"Source: {_shown(source)}",
        "Origin: FAIRhub API record, metadata.healthsheet",
        "",
        "This bundle contains the Healthsheet and nothing else — no publications,",
        "no documentation, no license, no IRB protocol. It exists to measure what",
        "a single structured upstream source yields on its own. It is NOT the",
        f"{display} baseline; the baseline corpus carries all cited sources,",
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
                 name: str | None = None,
                 project: str | None = None) -> tuple[Path, HealthsheetStats]:
    """`name` is the bundle's file name: the caller's, else the active
    profile's, else derived from the record's stem. `project` is the
    dataset the bundle identifies itself as: the caller's, else the
    active profile's (#1464)."""
    record_path = _record(record_path)
    # The profile's name and project describe the profile's *own* record;
    # any other record names its project and gets its own file (#1493).
    from data_sheets_schema.chunking import anchored
    from data_sheets_schema.profiles import active_profile
    prof = active_profile()
    own = (prof.healthsheet_record is not None
           and Path(record_path).resolve() == anchored(Path(prof.healthsheet_record)).resolve())   # from any directory (#1544)
    project = project or (prof.healthsheet_project if own else None)
    if not project:
        raise ValueError(f"no project for {record_path}: it is not the active profile's record; pass one")
    own_name = own and project == prof.healthsheet_project        # the study's bundle is the study's dataset (#1516)
    healthsheet, record = load_healthsheet(record_path)
    text, stats = render(healthsheet, record, record_path, project=project,
                         display=prof.healthsheet_display if own_name else None)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / (name or (bundle_name() if own_name else None) or f"{project}_healthsheet_only.txt")
    from data_sheets_schema.profiles import PROFILES
    reserved = {p.healthsheet_bundle for p in PROFILES.values() if p.healthsheet_bundle}
    if not own_name and name is None and target.name in reserved:
        # A record that is not the profile's may not take a profile's
        # tracked bundle name by claiming its project — under any active
        # profile (#1543, #1565).
        raise ValueError(f"{target.name} is the active profile's bundle name; pass --name for {record_path}")
    target.write_text(text, encoding="utf-8")
    return target, stats
