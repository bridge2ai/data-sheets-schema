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
], ids=["signed_empty_blocks", "no_blocks", "mixed", "redacted"])
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
