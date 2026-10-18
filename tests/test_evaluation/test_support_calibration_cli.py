"""CLI boundary tests with invented controls and no provider access."""
import json

from click.testing import CliRunner

from data_sheets_schema import support_calibration as calibration
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.support_plan import canonical
from tests.test_evaluation.test_support_calibration_adversarial import scenario  # noqa: F401
from tests.test_evaluation.test_nested_support_results import plan  # noqa: F401
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401


def test_cli_registers_missing_observations_then_captures_and_rechecks(scenario):
    case = scenario()
    case.controls_path.write_bytes(canonical(case.controls))
    runner = CliRunner()
    target = case.root / "cli-calibration"
    prepared = runner.invoke(evaluate, ["support-calibration", "prepare",
        "--registration", str(case.registration), "--controls", str(case.controls_path),
        "--output", str(target)])
    assert prepared.exit_code == 0, prepared.output
    assert json.loads(prepared.output) == calibration.recheck(target)
    absent = runner.invoke(evaluate, ["support-calibration", "report", "--calibration", str(target)])
    assert absent.exit_code == 0, absent.output
    assert json.loads(absent.output) == calibration.report(target)
    assert not case.calls

    case.run()
    calls = len(case.calls)
    portable = case.root / "cli-report"
    reported = runner.invoke(evaluate, ["support-calibration", "report", "--calibration", str(target),
        "--run", str(case.output), "--output", str(portable)])
    assert reported.exit_code == 0, reported.output
    assert json.loads(reported.output) == calibration.recheck(portable)
    checked = runner.invoke(evaluate, ["support-calibration", "recheck", "--calibration", str(portable)])
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output) == json.loads(reported.output)
    assert len(case.calls) == calls


def test_cli_refuses_wrong_target_and_preserves_existing_output(scenario):
    case = scenario()
    calibrated = case.prepare()
    before = (calibrated / "calibration.json").read_bytes()
    runner = CliRunner()
    refusal = runner.invoke(evaluate, ["support-calibration", "prepare",
        "--registration", str(case.registration), "--controls", str(case.controls_path),
        "--output", str(calibrated)])
    assert refusal.exit_code != 0
    assert "Error:" in refusal.output
    assert (calibrated / "calibration.json").read_bytes() == before
    case.controls["controls"][0]["attempt_id"] = "unselected-retry"
    case.controls_path.write_bytes(canonical(case.controls))
    destination = case.root / "invalid-control"
    refusal = runner.invoke(evaluate, ["support-calibration", "prepare",
        "--registration", str(case.registration), "--controls", str(case.controls_path),
        "--output", str(destination)])
    assert refusal.exit_code != 0
    assert "Error:" in refusal.output
    assert not destination.exists()
    assert not case.calls
