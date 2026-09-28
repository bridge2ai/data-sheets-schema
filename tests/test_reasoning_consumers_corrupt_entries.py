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


CORE = [{"phase": "core", "attempt": 1, "output_tokens": 10, "stop_reason": "end_turn"}]
GOOD = entry(attempt=1, output_tokens=555)
LATER = entry(attempt=3, output_tokens=777)
HUGE = int("1" + "0" * 309)          # an integer beyond float range, which json.loads accepts


@pytest.mark.parametrize("log, accepted, seen", [
    # A key holding a list or object equals no refused row's, so the entry is not refused
    # and, last, is the answer; only hashing it crashed (#2873, #2902).
    ([GOOD, entry(attempt=[2], output_tokens=900)], 900, 2),
    ([GOOD, entry(attempt={"n": 2}, output_tokens=900)], 900, 2),
    ([entry(attempt=[2], output_tokens=900)], 900, 1),
    # A later entry that could never be accepted leaves the rule's answer standing (#2898,
    # #2900, #2901).
    ([GOOD, entry(attempt=[2], output_tokens=900, stop_reason="max_tokens")], 555, 2),
    ([GOOD, entry(attempt=[2], output_tokens=None)], 555, 2),
    ([GOOD, entry(attempt=2, output_tokens=[900])], 555, 2),
    ([GOOD, entry(attempt=2, output_tokens="900")], 555, 2),
    ([GOOD, entry(attempt=2, output_tokens=float("nan"))], 555, 2),
    ([GOOD, entry(attempt=2, output_tokens=True)], 555, 2),
    ([GOOD, entry(attempt=2, output_tokens=HUGE)], 555, 2),
    ([GOOD, entry(attempt=2, output_tokens=10 ** 15)], 555, 2),
    ([GOOD, entry(attempt=2, output_tokens=900, unusable_reason="no YAML document")], 555, 2),
    ([GOOD, entry(attempt=2, output_tokens=900, outcome="transport error: X (#1017)")], 555, 2),
    # Comparable values are compared as the runner wrote them, as main compared them; a
    # fraction is a count the runner writes (#2898).
    ([GOOD, entry(attempt="2", output_tokens=900)], 900, 2),
    ([GOOD, entry(attempt=2, output_tokens=900.5)], 900, 2),
    # Nothing before the answer changes it, however many entries (#2896, #2899).
    ([entry(attempt=[1], output_tokens=900), LATER], 777, 2),
    ([entry(attempt=[1], output_tokens=900), entry(attempt=[2], output_tokens=901), LATER], 777, 3),
], ids=["list-attempt", "object-attempt", "only-list-attempt", "later-max-tokens", "later-null-output",
        "list-output", "text-output", "nan-output", "flag-output", "output-beyond-float", "output-at-bound",
        "later-unusable", "later-abandoned", "text-attempt", "fraction-output", "list-before",
        "two-lists-before"])
def test_the_baseline_follows_the_rule_around_corrupt_log_entries(run, log, accepted, seen):
    """#2873, #2896, #2898-#2902: the provenance holds no accepted full row, so the log is
    consulted. The answer is the last end_turn reply, not abandoned or refused as unusable,
    reporting a numeric output count of a size a response can have, that the provenance's
    refused rows do not match on the raw (attempt, output_tokens). Every entry those rows
    do not rule out is counted as seen, and every other end_turn reply as retried."""
    from data_sheets_schema.run_telemetry import accepted_full_output
    result = accepted_full_output(run(CORE, log), "CHORUS")
    assert result["output_tokens"] == accepted, result
    others = sum(1 for e in log if e.get("stop_reason") == "end_turn" and not e.get("outcome")) - 1
    assert result["attempts_seen"] == seen and result["retried"] == others, result


def test_a_list_attempt_after_a_refused_reply_is_not_that_reply(run):
    """#2902: a refused row's key is comparable, so a later reply whose attempt is a list
    cannot be it; the rule takes that later reply."""
    from data_sheets_schema.run_telemetry import accepted_full_output
    refused = [{"phase": "full", "attempt": 1, "output_tokens": 500, "stop_reason": "end_turn",
                "unusable_reason": "no YAML document"}]
    result = accepted_full_output(run(refused, [GOOD, entry(attempt=1, output_tokens=500),
                                                entry(attempt=[2], output_tokens=900)]), "CHORUS")
    assert (result["output_tokens"], result["attempt"]) == (900, [2])


def test_the_baseline_command_survives_an_unhashable_attempt(run):
    """#2873, #2902: the whole command, text and JSON, as the review reproduced it: no
    crash, and the later reply, which no refused row matches, is the answer."""
    from data_sheets_schema.cli.runs import runs as runs_cli
    run(CORE, [GOOD, entry(attempt=[2])])
    for extra in ([], ["--json"]):
        result = CliRunner().invoke(runs_cli, ["full-output-baseline", "--method", "claudecode_api",
                                               "--label", "L1", "--project", "CHORUS", *extra])
        assert result.exit_code == 0, result.output
    assert json.loads(result.output)["CHORUS"]["mean"] == 100


def test_the_baseline_prints_an_attempt_it_cannot_encode(run):
    """#2904: the text output escapes a lone surrogate in the accepted attempt."""
    from data_sheets_schema.cli.runs import runs as runs_cli
    run(CORE, [entry(attempt="\ud800", output_tokens=900)])
    result = CliRunner().invoke(runs_cli, ["full-output-baseline", "--method", "claudecode_api",
                                           "--label", "L1", "--project", "CHORUS"])
    assert result.exit_code == 0, result.output
    assert "L1: 900 (attempt \\ud800, reasoning_log)" in result.output


def test_a_refused_row_still_drops_its_log_entry(run):
    """#2873: the match key of a good entry is unchanged, so an entry the provenance
    recorded as refused is still dropped, and the reason says so when nothing is left."""
    from data_sheets_schema.run_telemetry import accepted_full_output
    refused = [{"phase": "full", "attempt": 1, "output_tokens": 500, "stop_reason": "end_turn",
                "unusable_reason": "no YAML document"}]
    directory = run(refused, [entry(attempt=1, output_tokens=500), entry(attempt=[2], output_tokens=None)])
    result = accepted_full_output(directory, "CHORUS")
    assert result["output_tokens"] is None
    assert result["reason"] == ("no accepted full attempt: 1 full row(s) in the provenance, 2 in the reasoning "
                                "log (1 of them the provenance recorded as refused)")


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


def _telemetry(tmp_path, *extra):
    from data_sheets_schema.cli.runs import runs as runs_cli
    out = tmp_path / "report.yaml"
    result = CliRunner().invoke(runs_cli, ["telemetry", "--label-prefix", "L1", "--method", "claudecode_api",
                                           "--output", str(out), *extra])
    assert result.exit_code == 0, result.output
    return yaml.safe_load(out.read_text())["runs"][0]


@pytest.mark.parametrize("value", ["90", 90.5, True, 10 ** 15])
def test_the_reasoning_total_sums_only_integer_counts(run, tmp_path, value):
    """#2894: both sums in the total, the legacy one over unidentified entries and the one
    over entries matched by usage_id, leave out an estimate that is not an integer count;
    a string there once crashed the matched sum."""
    usage = [{"phase": "core", "attempt": 1, "output_tokens": 10, "input_tokens": 5, "stop_reason": "end_turn"},
             {"phase": "full", "attempt": 1, "output_tokens": 20, "input_tokens": 5, "stop_reason": "end_turn",
              "usage_id": "u1"}]
    run(usage, [entry(phase="core", reasoning_tokens_estimate=value),
                entry(phase="full", usage_id="u1", reasoning_tokens_estimate=value),
                entry(phase="audit", reasoning_tokens_estimate=7)])
    assert _telemetry(tmp_path)["total_reasoning_tokens_estimate"] == 7


def test_a_refused_row_validates(run, tmp_path):
    """#2892: an attempt the runner refused carries unusable_reason, which the schema now
    declares, so the report validates."""
    usage = [{"phase": "full", "attempt": 1, "output_tokens": 10, "input_tokens": 5, "stop_reason": "end_turn",
              "unusable_reason": "no YAML document"}]
    run(usage, [entry()])
    (attempt,) = [a for p in _telemetry(tmp_path, "--validate")["phases"] for a in p["attempts"]]
    assert attempt["unusable_reason"] == "no YAML document"


def test_an_entry_the_runner_wrote_without_an_output_count_is_passed_over(run):
    """#2896: to_dict writes null for an output count it did not get. Such an entry is
    matchable and is not accepted, as a provenance row without a count is not, so the rule
    takes the attempt before it."""
    from data_sheets_schema.run_telemetry import accepted_full_output
    core = [{"phase": "core", "attempt": 1, "output_tokens": 10, "stop_reason": "end_turn"}]
    result = accepted_full_output(run(core, [entry(attempt=1, output_tokens=555),
                                             entry(attempt=2, output_tokens=None)]), "CHORUS")
    assert (result["output_tokens"], result["attempt"]) == (555, 1)


def test_entries_without_an_attempt_stay_matchable(run):
    """#2897: older runs wrote full entries with no attempt; six real replicates' baselines
    come from such entries, so an absent attempt is matchable and the last one accepted."""
    from data_sheets_schema.run_telemetry import accepted_full_output
    core = [{"phase": "core", "attempt": 1, "output_tokens": 10, "stop_reason": "end_turn"}]
    first, last = entry(output_tokens=100), entry(output_tokens=25491)
    first.pop("attempt", None), last.pop("attempt", None)
    result = accepted_full_output(run(core, [first, last]), "CHORUS")
    assert (result["output_tokens"], result["source"]) == (25491, "reasoning_log")
