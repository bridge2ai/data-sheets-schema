"""The closing message of `d4d provenance reasoning` names a cause only where one applies (#2626)."""
import json
import re

import pytest
from click.testing import CliRunner

from data_sheets_schema.cli.provenance import provenance


def entry(present, kind="thinking"):
    return {"phase": "full", "reasoning_present": present, "reasoning_available": False,
            "blocks": [{"type": kind, "chars": 0, "signed": kind == "thinking"}] if present else [],
            "output_tokens": 100, "visible_text_chars": 40, "reasoning_tokens_estimate": 90}


@pytest.mark.parametrize("entries, says, never", [
    ([entry(True), entry(True)], "signed but empty because the requests named no thinking display",
     "No entry returned"),
    ([entry(False), entry(False)], "No entry returned a thinking block", "signed but empty"),
    # The shape of nearly every real log: some phases thought, some did not (#2665).
    ([entry(True), entry(False)], "signed but empty because the requests named no thinking display",
     "No entry returned"),
    ([entry(True, "redacted_thinking")], "redacted by the provider", "named no thinking display"),   # #2666
    # Signed-empty and redacted blocks together: each cause for its own blocks (#2693).
    ([entry(True), entry(True, "redacted_thinking")], "instead redacted by the provider", "No entry returned"),
], ids=["signed_empty_blocks", "no_blocks", "mixed", "redacted", "signed_and_redacted"])
def test_the_closing_message_matches_what_the_log_holds(tmp_path, entries, says, never):
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text("".join(json.dumps(e) + "\n" for e in entries))
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    assert says in result.output and never not in result.output


def test_a_log_with_no_entries_is_reported_not_a_crash(tmp_path):
    """#2667: a reasoning log created but never written."""
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text("")
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    assert "entries 0" in result.output


def test_several_empty_logs_are_reported_not_a_crash(tmp_path, monkeypatch):
    """#2692: every log a label selects is empty, so there is nothing to aggregate."""
    from types import SimpleNamespace
    import data_sheets_schema.runs as runs
    from data_sheets_schema.cli import provenance as module
    run = SimpleNamespace(method="claudecode_api", label="L", projects=["CHORUS", "VOICE"],
                          is_core=False, deterministic=False)
    monkeypatch.setattr(runs, "discover", lambda *a, **k: [run])
    monkeypatch.setattr(module, "_corpus_path", lambda *_: tmp_path)
    folder = tmp_path / "claudecode_api_core" / "L"
    folder.mkdir(parents=True)
    for project in run.projects:
        (folder / f"{project}_reasoning.jsonl").write_text("")
    result = CliRunner().invoke(provenance, ["reasoning", "--label", "L"])
    assert result.exit_code == 0, result.output
    assert result.output.count("entries 0") == 2


def test_a_partial_line_is_named_and_skipped_not_a_crash(tmp_path):
    """#2695: a run killed mid-write can leave a partial last line."""
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text(json.dumps(entry(True)) + "\n" + json.dumps(entry(True))[:40])
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    assert "1 line(s) that are not a readable entry, skipped: 2" in result.output
    assert "entries 1" in result.output


def test_usage_accounting_still_refuses_an_unreadable_line(tmp_path):
    """The strict reader stays strict: usage accounting must not skip a record (#2695)."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text(json.dumps(entry(True)) + "\n{not json")
    with pytest.raises(reasoning.UnreadableLog, match=rf"^{re.escape(str(log))}: line 2 is not a readable entry"):
        reasoning.read(log)
    assert reasoning.read_lenient(log) == ([entry(True)], [2])


def test_a_line_that_parses_but_is_not_an_entry_is_skipped(tmp_path):
    """A line that parses to something other than an object is not what `append`
    writes, so it is corruption, not a partial write; it is named too (#2724)."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text("12\n" + json.dumps(entry(True)) + "\n[1]\n")
    assert reasoning.read_lenient(log) == ([entry(True)], [1, 3])
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    assert "2 line(s) that are not a readable entry, skipped: 1, 3" in result.output


def test_a_text_field_with_a_unicode_line_separator_is_one_entry(tmp_path):
    """#2720: `append` leaves U+2028, U+2029 and U+0085 unescaped; only the newline
    it writes separates entries."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    middle = {**entry(True), "phase": "core", "note": "a\u2028b\u2029c\u0085d"}
    for value in (entry(True), middle, entry(True)):
        reasoning.append(log, value)
    assert reasoning.read(log) == [entry(True), middle, entry(True)]
    assert reasoning.read_lenient(log) == ([entry(True), middle, entry(True)], [])


def test_a_line_cut_inside_a_multibyte_character_is_named(tmp_path):
    """#2720: a partial write can split a UTF-8 sequence; the line is named, not a crash."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    reasoning.append(log, entry(True))
    raw = json.dumps({**entry(True), "note": "caf\u00e9"}, ensure_ascii=False).encode("utf-8")
    log.write_bytes(log.read_bytes() + raw[:raw.index("\u00e9".encode("utf-8")) + 1])
    assert reasoning.read_lenient(log) == ([entry(True)], [2])
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    assert "1 line(s) that are not a readable entry, skipped: 2" in result.output


def test_a_bad_byte_in_a_complete_line_is_named_not_replaced(tmp_path):
    """#2720: a complete line holding an invalid byte is unreadable, as accounting finds it."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_bytes(json.dumps(entry(True)).replace("present", "pr\xffsent").encode("latin-1") + b"\n"
                    + json.dumps(entry(False)).encode() + b"\n")
    assert reasoning.read_lenient(log) == ([entry(False)], [1])
    with pytest.raises(reasoning.UnreadableLog, match="line 1 .*UnicodeDecodeError"):
        reasoning.read(log)


def test_a_deeply_nested_line_is_named_not_a_crash(tmp_path):
    """#2722: json.loads raises RecursionError on deep nesting; it is corruption like any other."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text(json.dumps(entry(True)) + "\n" + "[" * 100000 + "\n")
    assert reasoning.read_lenient(log) == ([entry(True)], [2])
    with pytest.raises(reasoning.UnreadableLog, match="line 2"):
        reasoning.read(log)


def test_a_log_whose_only_line_is_partial_names_it(tmp_path):
    """#2724: a run killed during its first write; told apart from an empty log (#2667)."""
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text(json.dumps(entry(True))[:40])
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    assert "1 line(s) that are not a readable entry, skipped: 1" in result.output
    assert "entries 0" in result.output


def test_lines_are_numbered_as_physical_lines(tmp_path):
    """#2724: blank lines count, so the number names the line an editor shows."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text("\n" + json.dumps(entry(True)) + "\n\n" + json.dumps(entry(True))[:40])
    assert reasoning.read_lenient(log) == ([entry(True)], [4])


def test_the_diagnosis_says_it_covers_readable_entries_only(tmp_path, monkeypatch):
    """#2721: a skipped line may have held the block the diagnosis finds absent; the
    aggregate line counts the skipped lines and the diagnosis says what it covers."""
    from types import SimpleNamespace
    import data_sheets_schema.runs as runs
    from data_sheets_schema.cli import provenance as module
    run = SimpleNamespace(method="claudecode_api", label="L", projects=["CHORUS", "VOICE"],
                          is_core=False, deterministic=False)
    monkeypatch.setattr(runs, "discover", lambda *a, **k: [run])
    monkeypatch.setattr(module, "_corpus_path", lambda *_: tmp_path)
    folder = tmp_path / "claudecode_api_core" / "L"
    folder.mkdir(parents=True)
    (folder / "CHORUS_reasoning.jsonl").write_text(json.dumps(entry(False)) + "\n")
    (folder / "VOICE_reasoning.jsonl").write_text(json.dumps(entry(False)) + "\n" + json.dumps(entry(True))[:40])
    result = CliRunner().invoke(provenance, ["reasoning", "--label", "L"])
    assert result.exit_code == 0, result.output
    assert "2 log(s), 2 entries, 0 with reasoning text, 1 unreadable line(s) skipped" in result.output
    assert result.output.index("1 unreadable line(s) skipped: what follows describes the readable entries only") \
        < result.output.index("No entry returned a thinking block")


def test_telemetry_refuses_an_unreadable_line_naming_it(tmp_path):
    """#2723: telemetry joins entries to usage rows, so it stays strict, through the shared reader."""
    from data_sheets_schema import reasoning, run_telemetry
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text(json.dumps(entry(True)) + "\n" + json.dumps(entry(True))[:40])
    with pytest.raises(reasoning.UnreadableLog, match=rf"{re.escape(str(log))}: line 2"):
        run_telemetry._reasoning_entries(log)


BAD_LINES = {"partial": json.dumps(entry(True))[:40], "list": "[1]", "null": "null"}


@pytest.fixture(params=sorted(BAD_LINES))
def bad_run(request, tmp_path, monkeypatch):
    """A real run directory whose only usage row is a core one, so the full-output
    baseline consults the log, and whose log's second line is unreadable."""
    import yaml
    import data_sheets_schema.api_runner as api
    from data_sheets_schema import run_telemetry
    run = tmp_path / "claudecode_api_core" / "L1"
    run.mkdir(parents=True)
    (run / "CHORUS_provenance.yaml").write_text(yaml.safe_dump(
        {"api_usage": [{"phase": "core", "attempt": 1, "output_tokens": 10, "input_tokens": 5,
                        "stop_reason": "end_turn"}]}))
    log = run / "CHORUS_reasoning.jsonl"
    log.write_text(json.dumps({**entry(True), "phase": "core"}) + "\n" + BAD_LINES[request.param] + "\n")
    monkeypatch.setattr(run_telemetry, "CONCAT_DIR", tmp_path)
    monkeypatch.setattr(api, "CONCAT_DIR", tmp_path)
    return run, log


@pytest.mark.parametrize("function", ["run_telemetry", "accepted_full_output"])
def test_telemetry_readers_refuse_an_unreadable_line_by_name(bad_run, function):
    """#2723, #2739, #2741: through the real functions, a partial or non-object line is
    refused with a named error, never read past or crashed on."""
    from data_sheets_schema import reasoning, run_telemetry
    run, log = bad_run
    with pytest.raises(reasoning.UnreadableLog, match=rf"^{re.escape(str(log))}: line 2 is not a readable entry"):
        getattr(run_telemetry, function)(run, "CHORUS")


@pytest.mark.parametrize("command", [
    ["telemetry", "--label-prefix", "L1", "--method", "claudecode_api"],
    ["full-output-baseline", "--method", "claudecode_api", "--label", "L1", "--project", "CHORUS"],
], ids=["telemetry", "full_output_baseline"])
def test_the_runs_commands_refuse_an_unreadable_line_by_name(bad_run, tmp_path, command):
    """#2723, #2741: the whole command, not a stand-in: a named error, not a traceback,
    and the run is not silently dropped from the report."""
    from data_sheets_schema import reasoning
    from data_sheets_schema.cli.runs import runs as runs_cli
    _, log = bad_run
    argv = command + (["--output", str(tmp_path / "report.yaml")] if command[0] == "telemetry" else [])
    result = CliRunner().invoke(runs_cli, argv)
    assert result.exit_code == 1 and not isinstance(result.exception, (reasoning.UnreadableLog, AttributeError)), \
        result.output
    assert f"Error: {log}: line 2 is not a readable entry" in result.output
    assert not (tmp_path / "report.yaml").exists()


def test_usage_accounting_refuses_an_unreadable_line(tmp_path):
    """#2739, #2741: api_runner's own accounting check, not the reader alone."""
    import data_sheets_schema.api_runner as api
    from data_sheets_schema import usage_ledger
    from tests.test_download.test_api_runner import spec
    s = spec(out_dir=tmp_path)
    for bad in BAD_LINES.values():
        path = api._reasoning_path(s)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entry(True)) + "\n" + bad + "\n")
        with pytest.raises(usage_ledger.UsageLedgerError, match="cannot establish surviving reasoning usage.*line 2"):
            api._unrecorded_reasoning(s, {})


def test_an_entry_left_without_its_newline_is_not_joined_by_the_next(tmp_path):
    """#2740: an interrupted write can leave a complete entry without its newline; the
    next append ends that line first, so both entries stay readable."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    reasoning.append(log, entry(True))
    log.write_bytes(log.read_bytes() + json.dumps(entry(False)).encode())      # no newline
    reasoning.append(log, {**entry(True), "phase": "core"})
    assert reasoning.read(log) == [entry(True), entry(False), {**entry(True), "phase": "core"}]
    assert log.read_bytes().endswith(b"\n") and b"\n\n" not in log.read_bytes()
    # A partial line is ended too: it stays named, and the new entry is readable.
    log.write_bytes(log.read_bytes() + json.dumps(entry(True)).encode()[:30])
    reasoning.append(log, entry(False))
    assert reasoning.read_lenient(log) == ([entry(True), entry(False), {**entry(True), "phase": "core"}, entry(False)],
                                           [4])


def _two_logs(tmp_path, monkeypatch, chorus, voice):
    from types import SimpleNamespace
    import data_sheets_schema.runs as runs
    from data_sheets_schema.cli import provenance as module
    run = SimpleNamespace(method="claudecode_api", label="L", projects=["CHORUS", "VOICE"],
                          is_core=False, deterministic=False)
    monkeypatch.setattr(runs, "discover", lambda *a, **k: [run])
    monkeypatch.setattr(module, "_corpus_path", lambda *_: tmp_path)
    folder = tmp_path / "claudecode_api_core" / "L"
    folder.mkdir(parents=True)
    (folder / "CHORUS_reasoning.jsonl").write_text(chorus)
    (folder / "VOICE_reasoning.jsonl").write_text(voice)
    return CliRunner().invoke(provenance, ["reasoning", "--label", "L"])


def test_skipped_lines_are_summed_over_every_log(tmp_path, monkeypatch):
    """#2741: two unreadable lines in the first log and one in the second are three."""
    partial = json.dumps(entry(True))[:40]
    result = _two_logs(tmp_path, monkeypatch,
                       json.dumps(entry(False)) + "\n" + partial + "\n" + "[1]\n",
                       json.dumps(entry(False)) + "\n" + partial)
    assert result.exit_code == 0, result.output
    assert "2 log(s), 2 entries, 0 with reasoning text, 3 unreadable line(s) skipped" in result.output
    assert "3 unreadable line(s) skipped: what follows describes the readable entries only" in result.output


def test_nothing_skipped_prints_no_count_and_no_caveat(tmp_path, monkeypatch):
    """#2741: the count and the caveat appear only when a line was skipped."""
    result = _two_logs(tmp_path, monkeypatch, json.dumps(entry(False)) + "\n", json.dumps(entry(False)) + "\n")
    assert result.exit_code == 0, result.output
    assert "2 log(s), 2 entries, 0 with reasoning text\n" in result.output
    assert "unreadable" not in result.output and "No entry returned a thinking block" in result.output


def test_logs_holding_only_unreadable_lines_are_counted(tmp_path, monkeypatch):
    """#2742: logs killed during their first write are not empty; the aggregate says so."""
    partial = json.dumps(entry(True))[:40]
    result = _two_logs(tmp_path, monkeypatch, partial, partial)
    assert result.exit_code == 0, result.output
    assert "2 log(s), 0 entries, 0 with reasoning text, 2 unreadable line(s) skipped" in result.output



@pytest.mark.parametrize("kind, diagnosis", [
    ("thinking", "The blocks are signed but empty"),
    ("redacted_thinking", "redacted by the provider"),
], ids=["signed_empty", "redacted"])
def test_the_caveat_precedes_every_diagnosis(tmp_path, kind, diagnosis):
    """#2764: the caveat is not tied to the no-block branch."""
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text(json.dumps(entry(True, kind)) + "\n" + json.dumps(entry(True))[:40])
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    caveat = "1 unreadable line(s) skipped: what follows describes the readable entries only"
    assert caveat in result.output and diagnosis in result.output, result.output
    assert result.output.index(caveat) < result.output.index(diagnosis)


def test_several_empty_logs_print_no_aggregate(tmp_path, monkeypatch):
    """#2764, #2692: logs that are all empty have nothing to aggregate."""
    result = _two_logs(tmp_path, monkeypatch, "", "")
    assert result.exit_code == 0, result.output
    assert result.output.count("entries 0") == 2 and "2 log(s)," not in result.output


def test_an_append_after_a_tail_cut_inside_a_character(tmp_path):
    """#2765: the dangling tail may end inside a UTF-8 sequence; append checks bytes and
    never decodes, so it neither raises nor joins the new entry to the tail."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    reasoning.append(log, entry(True))
    raw = json.dumps({**entry(True), "note": "caf\u00e9"}, ensure_ascii=False).encode("utf-8")
    log.write_bytes(log.read_bytes() + raw[:raw.index("\u00e9".encode("utf-8")) + 1])
    reasoning.append(log, entry(False))
    assert reasoning.read_lenient(log) == ([entry(True), entry(False)], [2])
