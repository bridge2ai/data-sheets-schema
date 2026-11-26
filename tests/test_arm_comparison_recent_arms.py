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

    prefixes = {key: prefix for key, _d, prefix, *_ in m.ARMS}
    recent = [prefixes[key] for key in m.RECENT_ARMS]

    def facts(prefix, method=None, concat_dir=None):
        # the second recent arm alone records a reviewer; no arm disagrees on it
        return {"prefix": prefix, "values": {"reviewer": ["judge-x"] if prefix == recent[1] else ["None"]}}

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
    monkeypatch.setattr(m, "RECENT_LAUNCH_DIRS", {})          # no launch record is read for fixture data
    data = {key: {project: [] for project in m.PROJECTS} for key, *_ in m.ARMS}
    first, second = m.RECENT_ARMS
    one, two = m.PROJECTS[0], m.PROJECTS[1]
    data[first][one] = [{"pair": 0, "rec": {"inputs": {"bundle_md5": "a" * 32},
                                              "report_claims": {"instrument": "v7 (#1): the history follows"}}}]
    data[second][one] = [{"pair": 0, "rec": {"inputs": {"bundle_md5": "b" * 32},
                                               "report_claims": {"instrument": "v8 (#2): then v7 (#1)"},
                                               "model": {"reasoning_effort": "high"}}}]
    data[first][two] = [{"pair": 0, "rec": {"inputs": {"bundle_md5": "c" * 32}}}]
    data[second][two] = [{"pair": 0, "rec": {"inputs": {"bundle_md5": "c" * 32}}}]

    text = "\n".join(m.recent_arms_section(data))
    stated, _, one_sided = text.partition("Recorded by one arm of a pair only")

    assert "| model | model-a | model-b |" in text
    assert f"| input bundle, {one} (md5) | aaaaaaaa | bbbbbbbb |" in stated     # the bundles the records pinned
    assert f"input bundle, {two}" not in text                                   # the same bundle is no row
    assert "| report-claims instrument | v7 | v8 |" in stated                   # the version, not its history
    assert "| reviewer | not recorded | judge-x |" in one_sided                 # an absence is not a difference
    assert "| reasoning effort | not recorded | high |" in one_sided
    assert "reviewer" not in stated and "reasoning effort |" not in stated
    assert "launch record" not in text
    assert "no recorded procedure field differs" in text          # the pairs the stub says are alike
    assert {project for _label, project in seen} == set(m.RECENT_ONLY_PROJECTS)
    assert len(seen) == 3 * len(m.RECENT_ARMS) * len(m.RECENT_ONLY_PROJECTS)
    assert f"### {m.RECENT_ONLY_PROJECTS[0]}, the two v9 arms only" in text
    assert "27/30 = 90.0%" in text                                  # pooled over three replicates, not a mean of rates


def test_the_launch_lines_are_read_from_the_launch_records_and_never_the_account(tmp_path, monkeypatch):
    m = _module()
    arms = {key: (display, prefix) for key, display, prefix, *_ in m.ARMS}
    first, second = m.RECENT_ARMS
    monkeypatch.setattr(m, "RECENT_LAUNCH_DIRS", {first: "one", second: "two"})
    for directory, key, body in (
            ("one", first, "claude code: 9.9.1 (Claude Code)\naccount: someone\ndelivery: one prompt (claude -p)\n"),
            ("two", second, "claude code: 9.9.2 (Claude Code) (/opt/tool/bin/claude)\naccount: someone-else\n"
                            "settings: project only (--setting-sources project): nothing else\n")):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / f"P_{arms[key][1]}_rep1.launch.txt").write_text(body, encoding="utf-8")

    text = "\n".join(m.recent_launch_lines(arms, root=tmp_path))

    assert "| Claude Code version | 9.9.1 | 9.9.2 |" in text         # the number, not the path beside it
    assert "| settings sources | not stated | project only |" in text
    assert "| delivery | one prompt | not stated |" in text
    assert "someone" not in text and "/opt/tool" not in text and "account" not in text
    assert m.recent_launch_lines(arms, root=tmp_path / "absent") == []


def test_the_figures_are_drawn_for_every_registered_arm(tmp_path, monkeypatch):
    """The default invocation writes figures; an arm added without a colour made it raise."""
    pytest.importorskip("matplotlib")
    m = _module()
    metric = next(iter(m.METRICS))
    monkeypatch.setattr(m, "METRICS", {metric: m.METRICS[metric]})
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "OUT_FIG", tmp_path / "figures")
    data = {key: {project: [{metric: 1}, {metric: 3}] for project in m.PROJECTS} for key, *_ in m.ARMS}
    scores = {"rubric10": {key: {project: [{"total": 10, "max": 50}] for project in m.PROJECTS}
                           for key, *_ in m.ARMS}}

    m.write_figures(data, scores)

    assert (tmp_path / "figures" / f"arm_comparison_{metric}.png").stat().st_size > 0
    assert (tmp_path / "figures" / "arm_comparison_rubric10.png").stat().st_size > 0


@pytest.mark.corpus
def test_the_extra_project_is_the_one_the_records_hold():
    """A sixth project in either series must fail here, not be dropped in silence."""
    m = _module()
    from data_sheets_schema.runs import arm_facts

    prefixes = {key: prefix for key, _d, prefix, *_ in m.ARMS}
    for key in m.RECENT_ARMS:
        held = set(arm_facts(prefixes[key], concat_dir=m.CONCAT)["projects"])
        assert held - set(m.PROJECTS) == set(m.RECENT_ONLY_PROJECTS)


@pytest.mark.corpus
def test_the_committed_note_carries_the_section_and_says_why_the_score_cells_are_empty():
    m = _module()
    text = NOTE.read_text(encoding="utf-8")
    start = text.index("## Arms added 2026-11-26")
    section = text[start: text.index("\n## ", start + 1)]
    displays = {key: display for key, display, *_ in m.ARMS}
    pair = f"| {displays[m.RECENT_ARMS[0]]} / {displays[m.RECENT_ARMS[1]]} |"
    stated, _, rest = section.partition("Recorded by one arm of a pair only")

    def fields(block):
        return sorted(line.split("|")[2].strip() for line in block.splitlines() if line.startswith(pair))

    assert fields(stated) == ["model", "runtime"]  # what the two series' own records state differently
    assert fields(rest) == ["reviewer"]            # one series was reviewed, the other was not
    assert "| Claude Code version |" in rest       # how the sessions were started, from the launch records
    assert m.RECENT_SCORE_NOTE in text
    for project in m.RECENT_ONLY_PROJECTS:
        assert f"### {project}, the two v9 arms only" in section
        before = text[:start]
        assert f"| {project} |" not in before      # the project is in no earlier table
