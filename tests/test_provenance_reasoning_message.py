"""The closing message of `d4d provenance reasoning` names a cause only where one applies (#2626)."""
import json

import pytest
from click.testing import CliRunner

from data_sheets_schema.cli.provenance import provenance


def entry(present):
    return {"phase": "full", "reasoning_present": present, "reasoning_available": False,
            "output_tokens": 100, "visible_text_chars": 40, "reasoning_tokens_estimate": 90}


@pytest.mark.parametrize("present, says, never", [
    (True, "signed but empty because the requests named no thinking display", "No entry returned"),
    (False, "No entry returned a thinking block", "signed but empty"),
], ids=["signed_empty_blocks", "no_blocks"])
def test_the_closing_message_matches_what_the_log_holds(tmp_path, present, says, never):
    log = tmp_path / "CHORUS_reasoning.jsonl"
    log.write_text("".join(json.dumps(entry(present)) + "\n" for _ in range(2)))
    result = CliRunner().invoke(provenance, ["reasoning", "--path", str(log)])
    assert result.exit_code == 0, result.output
    assert says in result.output and never not in result.output
