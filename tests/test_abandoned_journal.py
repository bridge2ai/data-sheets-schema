"""The abandoned-attempts journal the accounting gate reads (#2779).

Written and read as the reasoning log is (#2740, #2720, #2695): an append ends a
line an interrupted write left open, the reader splits on the newline alone, and
a line it cannot read is refused rather than skipped, since the gate must not
pass over a charge it cannot see.
"""
from dataclasses import replace
import json

import pytest

from data_sheets_schema import api_runner as api, usage_ledger as ledger
from tests.test_download.test_api_runner import spec


def _drop(s, attempt, **info):
    rows = []
    api._record_incomplete_stream(s, "full", attempt, "2026-09-28T00:00:00Z",
                                  {"usage": {"input_tokens": 1000}, **info}, rows)
    return rows[0]


def _cut_final_newline(path):
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    path.write_bytes(raw[:-1])


def test_a_row_appended_after_a_cut_newline_starts_its_own_line(tmp_path):
    """The issue's case (B): the final newline is lost, then a resumed process journals
    another row. Both rows survive, each on its own line, and both are recovered."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    first = _drop(s, 1)
    _cut_final_newline(api._abandoned_ledger(s))
    second = _drop(s, 2)
    assert api._abandoned_ledger(s).read_bytes().count(b"\n") == 2
    assert api.merge_abandoned_rows(s, []) == [first, second]


def test_a_torn_row_is_refused_not_skipped(tmp_path):
    """The issue's case (A): a row torn mid-write, then a resumed row. The torn line
    cannot be read, so the journal is refused, naming the line, and the gate that runs
    before every call refuses with it instead of passing with the charge unseen."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    _drop(s, 1)
    journal = api._abandoned_ledger(s)
    raw = journal.read_bytes()
    journal.write_bytes(raw[:len(raw) // 2])
    second = _drop(s, 2)
    # The resumed row starts a line of its own, whole, whatever the torn tail ended in (#2860).
    assert json.loads(journal.read_bytes().split(b"\n")[1]) == second
    with pytest.raises(ledger.UsageLedgerError, match=r"abandoned attempts: .*line 1 is not a readable entry"):
        api._abandoned_rows(s)
    with pytest.raises(ledger.UsageLedgerError, match="abandoned attempts"):
        api.merge_abandoned_rows(s, [])
    with pytest.raises(ledger.UsageLedgerError, match="abandoned attempts"):
        api._require_surviving_accounting(s, [])


def test_a_line_that_is_not_an_object_is_refused(tmp_path):
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    _drop(s, 1)
    with api._abandoned_ledger(s).open("ab") as stream:
        stream.write(b"[1, 2]\n")
    with pytest.raises(ledger.UsageLedgerError, match="line 2 is not a readable entry"):
        api._abandoned_rows(s)


def test_a_row_carrying_a_line_separator_character_reads_back_whole(tmp_path):
    """`ensure_ascii=False` leaves U+2028, U+2029 and U+0085 unescaped; the reader splits
    on the newline alone, so such a row is one row (#2720)."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    row = _drop(s, 1, outcome="transport error: Remote Protocol\u0085Error")
    assert api._abandoned_rows(s) == [row]
    assert api.merge_abandoned_rows(s, []) == [row]


def test_blank_lines_and_a_missing_journal_are_nothing(tmp_path):
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    assert api._abandoned_rows(s) == []
    first = _drop(s, 1)
    with api._abandoned_ledger(s).open("ab") as stream:
        stream.write(b"\n\n")
    second = _drop(s, 2)
    assert api._abandoned_rows(s) == [first, second]
    assert json.loads(api._abandoned_ledger(s).read_bytes().split(b"\n")[0]) == first


def test_a_fresh_generation_is_not_blocked_by_a_predecessors_torn_line(tmp_path):
    """#2859: the journal is kept across generations. A torn line a predecessor left is
    skipped, as the predecessor's rows are superseded anyway; this generation's own rows
    are read strictly from the boundary it recorded."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    old = _drop(s, 1)
    journal = api._abandoned_ledger(s)
    with journal.open("ab") as stream:
        stream.write(b'{"phase": "full", "usage_id": "torn", "input_tok')
    ledger.prepare_usage(s, resume=False)
    assert ledger.abandoned_journal_offset(s) == len(journal.read_bytes())
    assert api._abandoned_rows(s) == [old]
    assert api.merge_abandoned_rows(s, []) == []                  # the predecessor's row is superseded
    api._require_surviving_accounting(s, [])
    new = _drop(s, 1)
    assert api._abandoned_rows(s) == [old, new]
    assert api.merge_abandoned_rows(s, []) == [new]
    raw = journal.read_bytes()
    journal.write_bytes(raw[:len(raw) - 40])                      # this generation's own row, torn
    with pytest.raises(ledger.UsageLedgerError, match="line 3 is not a readable entry"):
        api._require_surviving_accounting(s, [])


def test_an_explicit_fresh_execution_runs_over_a_predecessors_torn_line(tmp_path):
    """#2859: the `--no-resume` route the resume refusals recommend is not refused."""
    from tests.test_download.test_api_runner import FakeClient
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    _drop(s, 1)
    with api._abandoned_ledger(s).open("ab") as stream:
        stream.write(b'{"phase": "full", "usage_id": "torn"')
    client = FakeClient()
    api.execute(s, resume=False, client=client)
    assert client.messages.calls


def test_a_journal_shorter_than_its_boundary_is_refused(tmp_path):
    """Bytes this generation counted on are gone: the journal was cut or replaced."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    _drop(s, 1)
    ledger.prepare_usage(s, resume=False)
    api._abandoned_ledger(s).write_bytes(b"")
    with pytest.raises(ledger.UsageLedgerError, match="shorter than when this generation began"):
        api._abandoned_rows(s)


def test_each_new_generation_records_its_own_boundary(tmp_path):
    """#2870: a fresh generation measures the journal as it finds it, not the boundary
    the previous ledger recorded."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    assert ledger.abandoned_journal_offset(s) == 0
    _drop(s, 1)
    ledger.prepare_usage(s, resume=False)
    first = len(api._abandoned_ledger(s).read_bytes())
    assert ledger.abandoned_journal_offset(s) == first > 0
    _drop(s, 1)
    ledger.prepare_usage(s, resume=False)
    assert ledger.abandoned_journal_offset(s) == len(api._abandoned_ledger(s).read_bytes()) > first


def test_a_first_ledger_opened_over_an_existing_journal_starts_after_it(tmp_path):
    """#2869: a generation opened by resume with no ledger yet, as the CLI opens one, does
    not own the lines already in the journal: another run's torn line there is skipped."""
    other = spec(out_dir=tmp_path)
    ledger.prepare_usage(other, resume=True)
    _drop(other, 1)
    with api._abandoned_ledger(other).open("ab") as stream:
        stream.write(b'{"phase": "full", "usage_id": "torn"')
    s = replace(other, label="another_rep1")                  # another run's identity, sharing the journal
    assert ledger.abandoned_journal_offset(s) is None
    assert len(api._abandoned_rows(s)) == 1                   # no generation: read as before, torn line skipped
    ledger.prepare_usage(s, resume=True)
    assert ledger.abandoned_journal_offset(s) == len(api._abandoned_ledger(s).read_bytes())
    api._require_surviving_accounting(s, [])


def test_the_boundary_is_in_bytes_and_lines_are_placed_by_their_start(tmp_path):
    """#2870, #2872: predecessor rows carrying multi-byte text, and a predecessor line torn
    in the middle of a character, are placed before the boundary by their byte offsets and
    skipped when unreadable; this generation's line that does not decode is refused."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    old = [_drop(s, 1, outcome="transport error: café 漢字 — dropped"), _drop(s, 2, outcome="ünïcödé")]
    journal = api._abandoned_ledger(s)
    torn = json.dumps({"phase": "full", "outcome": "漢字"}, ensure_ascii=False).encode("utf-8")
    with journal.open("ab") as stream:
        stream.write(torn[:torn.index("漢".encode("utf-8")) + 1])          # cut inside a character
    ledger.prepare_usage(s, resume=False)
    assert ledger.abandoned_journal_offset(s) == len(journal.read_bytes())
    assert api._abandoned_rows(s) == old
    new = _drop(s, 1, outcome="ascii")
    assert api._abandoned_rows(s) == [*old, new]
    # This generation's first line, undecodable: placed by its start in bytes, it lies at
    # the boundary; placed by characters it would fall before it and be skipped.
    raw = journal.read_bytes()
    boundary = ledger.abandoned_journal_offset(s)
    journal.write_bytes(raw[:boundary] + b'\n{"phase": "full", "outcome": "\xe6\xbc"}\n' + raw[boundary:].lstrip(b"\n"))
    with pytest.raises(ledger.UsageLedgerError, match="line 4 is not a readable entry"):
        api._abandoned_rows(s)


def test_a_journal_gone_after_its_boundary_is_refused(tmp_path):
    """#2871: bytes this generation began after are gone; removing the journal is refused as
    emptying it is. A generation whose journal was empty at its start may have none."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    assert api._abandoned_rows(s) == []
    _drop(s, 1)
    ledger.prepare_usage(s, resume=False)
    api._abandoned_ledger(s).unlink()
    with pytest.raises(ledger.UsageLedgerError, match="is gone, though this generation began after"):
        api._abandoned_rows(s)


@pytest.mark.parametrize("offset", [-1, "5", True, 2.0])
def test_an_invalid_boundary_is_refused(tmp_path, offset):
    """#2870: the ledger's boundary is a non-negative integer or the ledger is refused."""
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    path = ledger.ledger_path(s)
    data = json.loads(path.read_text())
    data["abandoned_journal_offset"] = offset
    path.write_text(json.dumps(data))
    with pytest.raises(ledger.UsageLedgerError, match="invalid abandoned-attempts journal boundary"):
        ledger.abandoned_journal_offset(s)
