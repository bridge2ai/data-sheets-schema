"""The two descriptive arms added to the arm comparison on 2026-11-26.

They are registered like any other arm, a fifth project that only they cover is
reported in its own section and never pooled, and what differs between them is
read from the records.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "arm_comparison.py"
NOTE = ROOT / "notes" / "arm_comparison.md"


def _module():
    spec = importlib.util.spec_from_file_location("arm_comparison", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_recent_arms_are_registered_and_the_project_list_is_unchanged():
    m = _module()
    keys = [key for key, *_ in m.ARMS]
    assert keys[-2:] == list(m.RECENT_ARMS)
    assert len(m.PROJECTS) == 4
    assert not set(m.RECENT_ONLY_PROJECTS) & set(m.PROJECTS)
    for first, second in m.RECENT_PAIRS:
        assert first in keys and second in keys


def test_the_section_is_empty_without_a_collected_replicate_and_reads_nothing(monkeypatch):
    m = _module()
    monkeypatch.setattr(m, "run_metrics", lambda *a, **k: pytest.fail("the corpus was read for fixture data"))
    empty = {key: {project: [] for project in m.PROJECTS} for key, *_ in m.ARMS}

    assert m.recent_arms_section(empty) == []


def test_the_section_is_empty_when_the_arms_are_not_registered(monkeypatch):
    m = _module()
    monkeypatch.setattr(m, "ARMS", (("fixture", "fixture", "fixture", "offline", "reps"),))

    assert m.recent_arms_section({"fixture": {project: [{"pair": 0}] for project in m.PROJECTS}}) == []


def test_the_section_states_differences_from_the_records_and_reports_the_extra_project(monkeypatch):
    m = _module()
    from data_sheets_schema import runs

    def facts(prefix, method=None, concat_dir=None):
        return {"prefix": prefix}

    def confounds(a, b):
        if {a["prefix"], b["prefix"]} == {dict((k, p) for k, _d, p, *_ in m.ARMS)[key] for key in m.RECENT_ARMS}:
            return [{"field": "model", a["prefix"]: "model-a", b["prefix"]: "model-b"}]
        return []

    monkeypatch.setattr(runs, "arm_facts", facts)
    monkeypatch.setattr(runs, "arm_confounds", confounds)
    seen = []

    def metrics(label, project):
        seen.append((label, project))
        return {"pair": 1, "receiptable": 10, "withreceipt": 9, "snippets": 4, "wrongchunk": 0}

    monkeypatch.setattr(m, "run_metrics", metrics)
    data = {key: {project: [] for project in m.PROJECTS} for key, *_ in m.ARMS}
    data[m.RECENT_ARMS[0]][m.PROJECTS[0]] = [{"pair": 0}]

    text = "\n".join(m.recent_arms_section(data))

    assert "| model | model-a | model-b |" in text
    assert "no recorded procedure field differs" in text          # the pairs the stub says are alike
    assert {project for _label, project in seen} == set(m.RECENT_ONLY_PROJECTS)
    assert len(seen) == 3 * len(m.RECENT_ARMS) * len(m.RECENT_ONLY_PROJECTS)
    assert f"### {m.RECENT_ONLY_PROJECTS[0]}, the two v9 arms only" in text
    assert "27/30 = 90.0%" in text                                  # pooled over three replicates, not a mean of rates


@pytest.mark.corpus
def test_the_committed_note_carries_the_section_and_says_why_the_score_cells_are_empty():
    m = _module()
    text = NOTE.read_text(encoding="utf-8")
    start = text.index("## Arms added 2026-11-26")
    section = text[start: text.index("\n## ", start + 1)]
    displays = {key: display for key, display, *_ in m.ARMS}
    pair = f"| {displays[m.RECENT_ARMS[0]]} / {displays[m.RECENT_ARMS[1]]} |"
    fields = sorted(line.split("|")[2].strip() for line in section.splitlines() if line.startswith(pair))

    assert fields == ["model", "runtime"]          # what the two series' own records state differently
    assert m.RECENT_SCORE_NOTE in text
    for project in m.RECENT_ONLY_PROJECTS:
        assert f"### {project}, the two v9 arms only" in section
        before = text[:start]
        assert f"| {project} |" not in before      # the project is in no earlier table
