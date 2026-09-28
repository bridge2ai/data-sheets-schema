"""The runs commands that read the reasoning log survive a corrupt entry (#2873, #2874).

The readers take any JSON object as an entry, so the accounting gate reads whatever
the runner wrote (#2876); each consumer uses a field only when it is what the runner
writes, and otherwise acts as if the entry did not carry it, as the reasoning report
does (#2722).
"""
import json

import pytest
import yaml
from click.testing import CliRunner


def entry(**fields):
    return {"phase": "full", "reasoning_present": True, "reasoning_available": False,
            "blocks": [{"type": "thinking", "chars": 0, "signed": True}],
            "output_tokens": 100, "visible_text_chars": 40, "reasoning_tokens_estimate": 90,
            "stop_reason": "end_turn", **fields}


@pytest.fixture
def run(tmp_path, monkeypatch):
    """A claudecode_api run directory under a temporary CONCAT_DIR."""
    import data_sheets_schema.api_runner as api
    from data_sheets_schema import run_telemetry
    directory = tmp_path / "claudecode_api_core" / "L1"
    directory.mkdir(parents=True)
    monkeypatch.setattr(run_telemetry, "CONCAT_DIR", tmp_path)
    monkeypatch.setattr(api, "CONCAT_DIR", tmp_path)

    def write(api_usage, log_entries):
        (directory / "CHORUS_provenance.yaml").write_text(yaml.safe_dump({"api_usage": api_usage}))
        (directory / "CHORUS_reasoning.jsonl").write_text("".join(json.dumps(e) + "\n" for e in log_entries))
        return directory
    return write


BAD_KEYS = [("attempt", [1]), ("attempt", {"n": 1}), ("attempt", "1"), ("attempt", 1.5), ("attempt", True),
            ("output_tokens", "100"), ("output_tokens", 100.5), ("output_tokens", [100]), ("output_tokens", None)]


@pytest.mark.parametrize("field, value", BAD_KEYS)
def test_the_baseline_sets_aside_a_log_entry_it_cannot_match(run, field, value):
    """#2873: the provenance holds no accepted full row, so the log is consulted. An entry
    whose attempt or output count is not what the runner writes can neither be matched
    to a refused row nor be the accepted output; it is set aside and counted, and a good
    entry beside it is still found. An unhashable attempt once crashed the command."""
    from data_sheets_schema.run_telemetry import accepted_full_output
    core = [{"phase": "core", "attempt": 1, "output_tokens": 10, "stop_reason": "end_turn"}]
    directory = run(core, [entry(attempt=1, output_tokens=777), entry(**{"attempt": 2, field: value})])
    result = accepted_full_output(directory, "CHORUS")
    assert (result["output_tokens"], result["source"]) == (777, "reasoning_log")
    directory = run(core, [entry(**{"attempt": 2, field: value})])
    result = accepted_full_output(directory, "CHORUS")
    assert result["output_tokens"] is None
    assert result["reason"].endswith("1 in the reasoning log (1 of them with an attempt or output count "
                                     "that is not an integer, set aside)"), result["reason"]


def test_the_baseline_command_survives_an_unhashable_attempt(run):
    """#2873: the whole command, as the review reproduced it."""
    from data_sheets_schema.cli.runs import runs as runs_cli
    core = [{"phase": "core", "attempt": 1, "output_tokens": 10, "stop_reason": "end_turn"}]
    run(core, [entry(attempt=[1]), entry(attempt=2, output_tokens=555)])
    result = CliRunner().invoke(runs_cli, ["full-output-baseline", "--method", "claudecode_api",
                                           "--label", "L1", "--project", "CHORUS", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["CHORUS"]["mean"] == 555


def test_a_refused_row_still_drops_its_log_entry(run):
    """#2873: the match key of a good entry is unchanged, so an entry the provenance
    recorded as refused is still dropped beside one set aside as unmatchable."""
    from data_sheets_schema.run_telemetry import accepted_full_output
    refused = [{"phase": "full", "attempt": 1, "output_tokens": 500, "stop_reason": "end_turn",
                "unusable_reason": "no YAML document"}]
    directory = run(refused, [entry(attempt=1, output_tokens=500), entry(attempt=[2])])
    result = accepted_full_output(directory, "CHORUS")
    assert result["output_tokens"] is None
    assert result["reason"] == ("no accepted full attempt: 1 full row(s) in the provenance, 2 in the reasoning "
                                "log (1 of them the provenance recorded as refused) (1 of them with an attempt "
                                "or output count that is not an integer, set aside)")


def _nested(depth):
    value = True
    for _ in range(depth):
        value = [value]
    return value


@pytest.mark.parametrize("field, value", [
    ("reasoning_present", _nested(400)), ("reasoning_present", "yes"), ("reasoning_available", 1),
    ("reasoning_tokens_estimate", "90"), ("reasoning_tokens_estimate", 90.5), ("reasoning_tokens_estimate", True),
    ("visible_text_chars", [40]), ("visible_text_chars", 10 ** 15)])
def test_telemetry_leaves_out_a_field_its_schema_cannot_hold(run, tmp_path, field, value):
    """#2874: the report takes a reasoning entry's count only when it is an integer count
    and its flags only when they are booleans, so a corrupt one is left out, as if the
    entry did not carry it, rather than failing the schema or, nested deep enough, the
    YAML dump that writes the report."""
    from data_sheets_schema.cli.runs import runs as runs_cli
    usage = [{"phase": "core", "attempt": 1, "output_tokens": 10, "input_tokens": 5, "stop_reason": "end_turn"}]
    run(usage, [entry(phase="core", **{field: value})])
    out = tmp_path / "report.yaml"
    result = CliRunner().invoke(runs_cli, ["telemetry", "--label-prefix", "L1", "--method", "claudecode_api",
                                           "--output", str(out)])
    assert result.exit_code == 0, result.output
    attempts = [a for r in yaml.safe_load(out.read_text())["runs"] for p in r["phases"] for a in p["attempts"]]
    assert len(attempts) == 1 and field not in attempts[0]
    kept = {"reasoning_present": True, "reasoning_available": False, "reasoning_tokens_estimate": 90,
            "visible_text_chars": 40}
    kept.pop(field)
    assert {k: attempts[0][k] for k in kept} == kept


@pytest.mark.parametrize("phase", [["core"], {"p": "core"}, 7])
def test_telemetry_joins_no_row_to_an_entry_whose_phase_is_not_text(run, tmp_path, phase):
    """#2874: the join keys entries by phase; one whose phase is a list or object once
    crashed it as an unhashable key. It joins no row. Its estimate is a valid count, and
    the legacy total counts every unidentified entry, joined or not, so it stays in."""
    from data_sheets_schema.cli.runs import runs as runs_cli
    usage = [{"phase": "core", "attempt": 1, "output_tokens": 10, "input_tokens": 5, "stop_reason": "end_turn"}]
    run(usage, [entry(phase=phase), entry(phase="core", reasoning_tokens_estimate=33)])
    out = tmp_path / "report.yaml"
    result = CliRunner().invoke(runs_cli, ["telemetry", "--label-prefix", "L1", "--method", "claudecode_api",
                                           "--output", str(out)])
    assert result.exit_code == 0, result.output
    report = yaml.safe_load(out.read_text())["runs"][0]
    (attempt,) = [a for p in report["phases"] for a in p["attempts"]]
    assert attempt["reasoning_tokens_estimate"] == 33
    assert report["total_reasoning_tokens_estimate"] == 90 + 33
