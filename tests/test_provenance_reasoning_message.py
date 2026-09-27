"""The closing message of `d4d provenance reasoning` names a cause only where one applies (#2626)."""
import json

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
    with pytest.raises(ValueError):
        reasoning.read(log)
    assert reasoning.read_lenient(log) == ([entry(True)], [2])


def test_a_line_that_parses_but_is_not_an_entry_is_skipped(tmp_path):
    """A partial line can still be valid JSON (a bare number): not an entry either (#2695)."""
    from data_sheets_schema import reasoning
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text("12\n" + json.dumps(entry(True)) + "\n[1]\n")
    assert reasoning.read_lenient(log) == ([entry(True)], [1, 3])
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    assert "2 line(s) that are not a readable entry, skipped: 1, 3" in result.output
