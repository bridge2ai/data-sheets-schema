"""Offline replay boundary controls for issue 6384, 2026-11-26.

Only synthetic retained files are created. No model, validator or publication.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("session_identity_replay", ROOT / "scripts/adhoc/replay_scorer_session_identity_6384_20261126.py")
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)
SENTINEL = "SYNTHETIC_ASSISTANT_CONTENT_MUST_NOT_LEAVE_REPLAY"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def synthetic_bytes(directory):
    """Snapshot only test-created files, including the synthetic candidate."""
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def retained_run(tmp_path, category="published"):
    run = tmp_path / "runs" / "synthetic-run"
    plan = {"run_directory": str(run), "codex_home": str(run / "codex-home"),
            "working_directory": str(run / "working"), "runner_sha256": "a" * 64,
            "prompt_sha256": "b" * 64, "prompt": SENTINEL, "inputs": {},
            "identity": {"project": "Example", "method": "synthetic", "rubric": "rubric10-semantic",
                         "label": "2026-11-25c_synthetic_rep1", "version": "6.0", "instrument_id": "synthetic"}}
    receipt = {"status": "VALIDATED_AND_PUBLISHED", "finished_utc": "2026-11-26T01:00:02Z",
               "codex_started_utc": "2026-11-26T01:00:00Z", "codex_finished_utc": "2026-11-26T01:00:01Z",
               "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()}
    if category != "published":
        receipt["status"] = "REFUSED"
        receipt["failure"] = ("ScorerError: " + replay.FALSE_REASONS[0] if category == "false_refusal" else SENTINEL)
        if category == "true_refusal":
            receipt["validator_exit"] = 1
    write(run / "plan.json", plan)
    write(run / "receipt.json", receipt)
    write(run / "codex.stdout.jsonl", {"type": "thread.started", "thread_id": "root"})
    log = run / "codex-home/sessions/root.jsonl"
    write(log, {"type": "session_meta", "payload": {"id": "root", "base_instructions": SENTINEL}})
    with log.open("a") as stream:
        stream.write(json.dumps({"type": "response_item", "payload": {"role": "assistant", "text": SENTINEL}}) + "\n")
    candidate = run / "candidate_evaluation.json"
    write(candidate, {"secret": SENTINEL, "score": 999})
    report, values = replay.inventory([run.parent])
    return run, report, values, log, candidate


def accepting_reader(log):
    module = SimpleNamespace(read_file=replay.read)

    def identity(plan, started, finished):
        module.read_file(Path(plan["run_directory"]) / "codex.stdout.jsonl")
        module.read_file(log)
        return {"session_logs": [{"parent_thread_id": None, "owned_turn_ids": ["root-turn"]}]}

    module.session_identity = identity
    return module


def test_inventory_and_replay_never_export_assistant_or_refused_output(tmp_path):
    for category in ("published", "false_refusal", "true_refusal"):
        run, report, values, log, candidate = retained_run(tmp_path / category, category)
        before = candidate.read_bytes()
        module = accepting_reader(log)
        result = replay.replay_one(module, b"", report["runs"][0], *values[str(run)])
        assert result["identity_result"] == "ACCEPT"
        assert result["category"] == category
        assert result["original_status"] == ("VALIDATED_AND_PUBLISHED" if category == "published" else "REFUSED")
        assert result["evaluation_validation_performed"] is False
        assert result["publication_performed"] is False
        assert result["input_bytes_unchanged"] is True
        assert SENTINEL not in json.dumps(report)
        assert SENTINEL not in json.dumps(result)
        assert candidate.read_bytes() == before
        assert not any("candidate" in pin["path"] for pin in result["read_pins"])


def test_reader_cannot_open_candidate_or_other_unapproved_file(tmp_path):
    run, report, values, log, candidate = retained_run(tmp_path)
    module = accepting_reader(log)
    module.session_identity = lambda plan, started, finished: module.read_file(candidate)
    result = replay.replay_one(module, b"", report["runs"][0], *values[str(run)])
    assert result["identity_result"] == "REFUSE"
    assert SENTINEL not in json.dumps(result)
    assert "candidate" not in result["reason"]


def test_dynamic_reader_error_values_are_withheld():
    source = b'def example():\n    require(False, f"unexpected tool activity: {value}")\n'
    reason = replay.safe_reason(ValueError("unexpected tool activity: " + SENTINEL), source)
    assert reason == "unexpected tool activity: [dynamic value withheld]"
    assert SENTINEL not in replay.safe_reason(ValueError(SENTINEL), source)


def test_metadata_shape_inventory_exports_only_types_and_parent_comparison(tmp_path):
    run, report, values, log, _candidate = retained_run(tmp_path)
    write(log.parent / "child.jsonl", {"type": "session_meta", "payload": {
        "id": "child", "parent_thread_id": "root", "forked_from_id": "root",
        "subagent_history_start_ordinal": 7, "base_instructions": SENTINEL}})
    result = replay.metadata_shapes(report, values)
    assert list(result["child_shape_counts"].values()) == [1]
    assert "equals_parent=True" in next(iter(result["child_shape_counts"]))
    assert SENTINEL not in json.dumps(result)


def test_replay_detects_changed_metadata_and_session_bytes(tmp_path):
    for changed in ("metadata", "session"):
        run, report, values, log, _candidate = retained_run(tmp_path / changed)
        module = accepting_reader(log)
        if changed == "metadata":
            with (run / "receipt.json").open("a") as stream:
                stream.write(" ")
        else:
            original = module.session_identity

            def mutating_identity(plan, started, finished):
                result = original(plan, started, finished)
                with log.open("a") as stream:
                    stream.write(" ")
                return result

            module.session_identity = mutating_identity
        with pytest.raises(ValueError, match="changed"):
            replay.replay_one(module, b"", report["runs"][0], *values[str(run)])


def test_output_cannot_be_written_inside_input_roots(tmp_path, monkeypatch):
    run, _report, _values, _log, _candidate = retained_run(tmp_path)
    monkeypatch.setattr(replay.os, "getpriority", lambda *args: 10)
    target = run.parent / "forbidden-report.json"
    with pytest.raises(ValueError, match="outside retained roots"):
        replay.main(["--root", str(run.parent), "--inventory-only", "--output", str(target)])
    assert not target.exists()


def test_output_cannot_be_written_inside_explicit_run_excluded_from_census(tmp_path, monkeypatch):
    kept, _report, _values, _log, _candidate = retained_run(tmp_path / "included")
    excluded, _report, _values, _log, _candidate = retained_run(tmp_path / "excluded")
    plan = json.loads((excluded / "plan.json").read_bytes())
    plan["identity"]["label"] = "unrelated_series_rep1"
    write(excluded / "plan.json", plan)
    receipt = json.loads((excluded / "receipt.json").read_bytes())
    receipt["plan_sha256"] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    write(excluded / "receipt.json", receipt)
    monkeypatch.setattr(replay.os, "getpriority", lambda *args: 10)
    target = excluded / "forbidden-report.json"
    with pytest.raises(ValueError, match="outside explicitly supplied runs"):
        replay.main(["--run-directory", str(kept), "--run-directory", str(excluded),
                     "--inventory-only", "--output", str(target)])
    assert not target.exists()


def identity_alias(monkeypatch, alias, protected, *, same_device=True):
    """Simulate filesystem name aliases on case-sensitive CI as well."""
    original = Path.stat
    info = original(protected)
    substitute = SimpleNamespace(st_dev=info.st_dev if same_device else info.st_dev + 1,
                                 st_ino=info.st_ino, st_mode=info.st_mode)

    def lookup(path, *args, **kwargs):
        return substitute if path == alias else original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", lookup)


def test_case_alias_output_is_refused_on_case_insensitive_filesystem(tmp_path, monkeypatch):
    run, _report, _values, _log, _candidate = retained_run(tmp_path)
    alias = run.parent.with_name(run.parent.name.upper())
    if not alias.exists() or not alias.samefile(run.parent):
        pytest.skip("case-sensitive filesystem; portable identity-alias controls still run")
    monkeypatch.setattr(replay.os, "getpriority", lambda *args: 10)
    target = alias / run.name / "forbidden-report.json"
    before = synthetic_bytes(run)
    assert not target.is_relative_to(run.parent)
    with pytest.raises(ValueError, match="output aliases a protected directory"):
        replay.main(["--root", str(run.parent), "--inventory-only", "--output", str(target)])
    assert not target.exists()
    assert not (run / target.name).exists()
    assert synthetic_bytes(run) == before


def test_replay_protects_selected_explicit_excluded_and_root_identities(tmp_path, monkeypatch):
    for kind in ("selected", "excluded", "root"):
        case = tmp_path / kind
        run, _report, _values, _log, _candidate = retained_run(case / "included")
        protected = run
        arguments = ["--run-directory", str(run)]
        if kind == "root":
            protected = run.parent
            arguments = ["--root", str(protected)]
        elif kind == "excluded":
            protected, _report, _values, _log, _candidate = retained_run(case / "excluded")
            plan = json.loads((protected / "plan.json").read_bytes())
            plan["identity"]["label"] = "unrelated_series_rep1"
            write(protected / "plan.json", plan)
            receipt = json.loads((protected / "receipt.json").read_bytes())
            receipt["plan_sha256"] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
            write(protected / "receipt.json", receipt)
            arguments.extend(["--run-directory", str(protected)])
        alias = case / "different-spelling"
        alias.mkdir()
        target = alias / "forbidden-report.json"
        before = synthetic_bytes(case)
        assert not target.is_relative_to(protected)
        with monkeypatch.context() as control:
            control.setattr(replay.os, "getpriority", lambda *args: 10)
            identity_alias(control, alias, protected)
            with pytest.raises(ValueError, match="output aliases a protected directory"):
                replay.main([*arguments, "--inventory-only", "--output", str(target)])
        assert not target.exists()
        assert synthetic_bytes(case) == before


def load_adhoc(name, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/adhoc"))
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/adhoc" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plan_preflight_and_final_verifier_refuse_source_and_baseline_aliases_early(tmp_path, monkeypatch):
    module = load_adhoc("verify_session_reader_plan_revision_6384_20261126", monkeypatch)

    def forbidden(*args, **kwargs):
        raise AssertionError("output guard did not run before Git or baseline reads")

    monkeypatch.setattr(module, "git", forbidden)
    monkeypatch.setattr(module, "document", forbidden)
    for mode in ("preflight", "compare"):
        for protected_name in ("source", "baseline"):
            case = tmp_path / mode / protected_name
            source, baseline, alias = (case / name for name in ("source", "baseline", "alias"))
            for directory in (source, baseline, alias):
                directory.mkdir(parents=True)
            target = alias / "forbidden-evidence"
            args = SimpleNamespace(repo_root=source, baseline_runs=baseline, evidence_directory=target,
                                   expected_head="synthetic-head", measured_runner_sha256="a" * 64)
            protected = source if protected_name == "source" else baseline
            with monkeypatch.context() as control:
                identity_alias(control, alias, protected)
                with pytest.raises(ValueError, match="output aliases a protected directory"):
                    getattr(module, mode)(args)
            assert not target.exists()


def test_scanner_refuses_checkout_alias_before_git_or_archive(tmp_path, monkeypatch):
    module = load_adhoc("verify_session_reader_scanner_arrays_6384_20261126", monkeypatch)
    source, alias = tmp_path / "source", tmp_path / "alias"
    source.mkdir()
    alias.mkdir()
    target = alias / "forbidden-evidence"

    def forbidden(*args, **kwargs):
        raise AssertionError("output guard did not run before Git or archive")

    monkeypatch.setattr(module, "git", forbidden)
    identity_alias(monkeypatch, alias, source)
    args = SimpleNamespace(repo_root=source, evidence_directory=target, candidate_ref="synthetic-head")
    with pytest.raises(ValueError, match="output aliases a protected directory"):
        module.verify(args)
    assert not target.exists()


def test_output_guard_retains_symlink_refusal_and_device_distinction(tmp_path, monkeypatch):
    protected, outside = tmp_path / "protected", tmp_path / "outside"
    protected.mkdir()
    outside.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(protected, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        replay.require_output_outside(link / "report.json", [protected])
    target = outside / "report.json"
    with monkeypatch.context() as control:
        identity_alias(control, outside, protected, same_device=False)
        assert replay.require_output_outside(target, [protected]) == target


def test_outside_inventory_report_is_still_written(tmp_path, monkeypatch):
    run, _report, _values, _log, _candidate = retained_run(tmp_path)
    monkeypatch.setattr(replay.os, "getpriority", lambda *args: 10)
    target = tmp_path / "outside-report.json"
    assert replay.main(["--root", str(run.parent), "--inventory-only", "--output", str(target)]) == 0
    saved = json.loads(target.read_bytes())
    assert saved["counts"] == {"2026-11-25c/published": 1}
    assert not (run / target.name).exists()
