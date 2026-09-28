"""The abandoned-attempts journal the accounting gate reads (#2779).

Written and read as the reasoning log is (#2740, #2720, #2695): an append ends a
line an interrupted write left open, the reader splits on the newline alone, and
a line it cannot read is refused rather than skipped, since the gate must not
pass over a charge it cannot see.
"""
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
