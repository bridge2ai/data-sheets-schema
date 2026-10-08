"""Saved-report controls for #4650; these never run the bundle measurement."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "notes/shared_line_joining_2026-10-07/replay.py"


@pytest.fixture
def replay(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("shared_line_join_replay", DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = tmp_path / "candidate"
    driver = candidate / DRIVER.relative_to(ROOT)
    driver.parent.mkdir(parents=True)
    driver.write_bytes(DRIVER.read_bytes())
    for relative in (module.PANEL, module.SCRIPT):
        path = candidate / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    monkeypatch.setattr(module, "DRIVER", driver)
    panel = module.load_panel(candidate / module.PANEL)
    sources = {path: module.pin(ROOT / path) for path in module.SOURCE_FILES}
    rows = [{"identity": module.identity(row), "status": "measured",
             "measurement": {key: row[key] for key in module.METRICS}}
            for row in panel["measurement"]["rows"]]
    common = {"format": module.FORMAT, "kind": "measurement",
              "panel_sha256": module.PANEL_SHA, "rows": rows,
              "inputs_preserved": True, "disk_inputs_before": {}, "disk_inputs_after": {},
              "source_before": sources, "source_after": deepcopy(sources),
              "word_list": panel["measurement"]["words"],
              "settings": {"compare_window": 10, "joins_per_window": 2, "join_context_lines": None},
              "driver_sha256": module.sha(driver.read_bytes()), "markdown": "identical saved table\n"}
    baseline = {**deepcopy(common), "repo_commit": module.BASELINE_COMMIT}
    for field in ("source_before", "source_after"):
        baseline[field][module.SCRIPT] = deepcopy(module.BASELINE_SCRIPT)
    current = {**deepcopy(common), "repo_commit": "c" * 40}
    paths = [tmp_path / "baseline-results/report.json", tmp_path / "candidate-results/report.json"]
    for path, value in zip(paths, (baseline, current)):
        path.parent.mkdir()
        path.write_text(json.dumps(value), encoding="utf-8")
    args = SimpleNamespace(baseline=paths[0], candidate=paths[1], output=tmp_path / "comparison")
    return module, args, candidate


def change_report(path, change):
    value = json.loads(path.read_bytes())
    change(value)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_exact_baseline_and_reviewed_candidate_compare_without_measurement(replay):
    module, args, _ = replay
    before = [path.read_bytes() for path in (args.baseline, args.candidate)]
    assert module.compare(args) == 0
    result = json.loads((args.output / "report.json").read_bytes())
    assert result["equal"] is True and len(result["rows"]) == 22
    assert result["baseline_source"] == {"commit": module.BASELINE_COMMIT, "script": module.BASELINE_SCRIPT}
    assert result["candidate_source"]["script"]["sha256"] == module.CANDIDATE_SCRIPT_SHA
    assert [path.read_bytes() for path in (args.baseline, args.candidate)] == before


@pytest.mark.parametrize("mode", ("same_file", "copied_candidate", "swapped", "candidate_with_baseline_commit"))
def test_candidate_twice_and_swapped_roles_refuse(replay, mode):
    module, args, _ = replay
    if mode == "same_file":
        args.baseline = args.candidate
    elif mode == "copied_candidate":
        args.baseline.write_bytes(args.candidate.read_bytes())
    elif mode == "swapped":
        args.baseline, args.candidate = args.candidate, args.baseline
    else:
        args.baseline.write_bytes(args.candidate.read_bytes())
        change_report(args.baseline, lambda value: value.update(repo_commit=module.BASELINE_COMMIT))
    with pytest.raises(ValueError, match="same file|identical|baseline commit differs|baseline script differs"):
        module.compare(args)
    assert not args.output.exists()


@pytest.mark.parametrize("target,field", (("baseline", "commit"), ("baseline", "script"), ("candidate", "script")))
def test_required_role_identity_cannot_be_relabelled(replay, target, field):
    module, args, _ = replay

    def change(value):
        if field == "commit":
            value["repo_commit"] = "f" * 40
        else:
            for key in ("source_before", "source_after"):
                value[key][module.SCRIPT]["sha256"] = "f" * 64

    change_report(getattr(args, target), change)
    with pytest.raises(ValueError, match=f"{target} {field} differs"):
        module.compare(args)
    assert not args.output.exists()


def test_changed_current_script_cannot_redefine_the_reviewed_candidate(replay):
    module, args, candidate = replay
    script = candidate / module.SCRIPT
    script.write_bytes(script.read_bytes() + b"\n# unreviewed change\n")
    changed_pin = module.pin(script)

    def change(value):
        for key in ("source_before", "source_after"):
            value[key][module.SCRIPT] = changed_pin

    change_report(args.candidate, change)
    with pytest.raises(ValueError, match="current candidate script differs from reviewed identity"):
        module.compare(args)
    assert not args.output.exists()


@pytest.mark.parametrize("command", ("run", "compare"))
def test_output_cannot_be_inside_driver_checkout_with_external_inputs(replay, command, tmp_path):
    module, args, candidate = replay
    output = candidate / "new-results"
    if command == "run":
        baseline_repo = tmp_path / "baseline-repo"
        baseline_repo.mkdir()
        # No panel or runnable source exists here: rejection precedes measurement.
        args = SimpleNamespace(repo=baseline_repo, words=tmp_path / "absent-words", output=output)
    else:
        args.output = output
    with pytest.raises(ValueError, match="output overlaps an input directory"):
        getattr(module, command)(args)
    assert not output.exists()


def test_measurement_difference_is_retained_as_failed_comparison(replay):
    module, args, _ = replay

    def change(value):
        value["rows"][0]["measurement"]["lines"] += 1

    change_report(args.candidate, change)
    assert module.compare(args) == 1
    result = json.loads((args.output / "report.json").read_bytes())
    assert result["equal"] is False
    assert result["rows"][0]["baseline_candidate_equal"] is False
    assert result["rows"][0]["historical_equal"] is False
    assert len(result["rows"]) == 22
