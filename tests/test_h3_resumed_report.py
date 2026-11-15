"""Codex197 reporter acceptance controls, 2026-11-13; synthetic saved evidence only."""
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / 'scripts/adhoc/report_h3_resumed_matrix_20261113.py'
SPEC = importlib.util.spec_from_file_location('h3_resumed_report', PATH)
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


def fixture(tmp_path):
    stage = tmp_path / 'stages/full'
    stage.mkdir(parents=True)
    demo = tmp_path / 'demonstration.json'
    demo.write_text('{}')
    (tmp_path / 'stage-config.json').write_text('{}')
    result = dict(status='passed', action='full', role=None,
                  config=REPORT.pin(tmp_path / 'stage-config.json'),
                  outputs=dict(demonstration=REPORT.pin(demo)),
                  side_effects=dict(native_executions=0, model_calls=0, probes_executed=0, captures=0, reservations=0))
    (stage / 'result.json').write_text(json.dumps(result))
    outcome = dict(status='passed', returncode=0, cleanup_verified=True,
                   result=REPORT.pin(stage / 'result.json'), demonstration_proof=REPORT.pin(demo))
    (stage / 'outcome.json').write_text(json.dumps(outcome))
    return stage, demo, outcome


def test_terminal_accepts_complete_pinned_cohort(tmp_path):
    stage, demo, _ = fixture(tmp_path)
    assert REPORT.verify_terminal(stage, demo)['status'] == 'verified'


def test_aggregate_without_terminal_outcome_is_not_accepted(tmp_path):
    stage, demo, _ = fixture(tmp_path)
    (stage / 'outcome.json').rename(stage / 'preserved-outcome.json')
    with pytest.raises(FileNotFoundError):
        REPORT.verify_terminal(stage, demo)


def test_postflight_failure_overrides_complete_aggregate(tmp_path):
    stage, demo, outcome = fixture(tmp_path)
    outcome['postflight_error'] = 'source changed'
    (stage / 'outcome.json').write_text(json.dumps(outcome))
    with pytest.raises(ValueError, match='cleanup/postflight'):
        REPORT.verify_terminal(stage, demo)


def test_cleanup_failure_overrides_complete_aggregate(tmp_path):
    stage, demo, outcome = fixture(tmp_path)
    outcome['cleanup_verified'] = False
    (stage / 'outcome.json').write_text(json.dumps(outcome))
    with pytest.raises(ValueError, match='cleanup/postflight'):
        REPORT.verify_terminal(stage, demo)


def test_changed_demo_cannot_inherit_terminal_acceptance(tmp_path):
    stage, demo, _ = fixture(tmp_path)
    demo.write_text('{"changed": true}')
    with pytest.raises(ValueError, match='pins differ'):
        REPORT.verify_terminal(stage, demo)


def test_failed_git_inspection_is_not_clean():
    assert REPORT.command_text(dict(returncode=1, stdout='', stderr='failure'), '(clean)') == 'INSPECTION FAILED: failure'
