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


@pytest.mark.parametrize("command, patched", [
    (["telemetry", "--label-prefix", "L", "--method", "claudecode_api"], "collect_report"),
    (["full-output-baseline", "--method", "claudecode_api", "--label", "L", "--project", "CHORUS"],
     "full_output_baseline"),
], ids=["telemetry", "full_output_baseline"])
def test_the_runs_commands_refuse_an_unreadable_line_by_name(tmp_path, monkeypatch, command, patched):
    """#2723: the refusal is a named error, not the bare JSONDecodeError traceback of #2695."""
    from data_sheets_schema import reasoning, run_telemetry
    from data_sheets_schema.cli.runs import runs as runs_cli
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text(json.dumps(entry(True)) + "\n" + json.dumps(entry(True))[:40])
    monkeypatch.setattr(run_telemetry, patched, lambda *a, **k: reasoning.read(log))
    result = CliRunner().invoke(runs_cli, command)
    assert result.exit_code == 1 and not isinstance(result.exception, reasoning.UnreadableLog), result.output
    assert f"Error: {log}: line 2 is not a readable entry" in result.output
