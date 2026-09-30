"""The measure of words a bundle splits across lines with no hyphen (#3199).

`attainability.matching_lines` does not read a break inside a word with no
hyphen; the script counts, per bundle version, the breaks that are such a
split, the ordinary wraps that would join if every break were read that
way, and the checks either reading would move. These pin each count on
text small enough to read, so the table in the note means what it says.
"""
import importlib.util
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import attainability as at

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "measure_unhyphenated_line_splits.py"


@pytest.fixture(scope="module")
def m():
    spec = importlib.util.spec_from_file_location("measure_unhyphenated_line_splits", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TEXT = ("Participants gave their con\n"            # con/sent: both words, joins to one
        "sent in writing and the partic\n"         # partic/ipants: neither half a word
        "ipants left.\n"
        "We looked it over\n"                      # over/sight: oversight is no word here
        "sight unseen.\n"
        "The consent form and the participants were fine.")
WORDS = {"gave", "their", "in", "writing", "and", "the", "left", "we", "looked", "it", "over", "sight",
         "unseen", "con", "sent"}


def test_the_split_word_and_the_joining_wrap_are_told_apart(m):
    got = m.measure(TEXT, WORDS)
    assert got["letter_breaks"] == 3                              # 'left.' / 'We' ends in a full stop
    assert got["split_words"] == [{"line": 2, "tail": "partic", "head": "ipants", "word": "participants"}]
    assert got["wraps_that_join"] == 1                            # con/sent
    # 'participants' is no check's form, so reading the split changes nothing;
    # reading every break as nothing joins 'con' 'sent' and 'over' 'sight'.
    assert got["moved"] == {}
    assert got["moved_if_every_break_joins"] == {"consent_text": "lines", "ethics_review": "status"}
    # One half a word and one not is neither: the issue's method asks that
    # neither half be a word, and such a break is no ordinary wrap either.
    one_half = m.measure("we gave con\nsent now", {"we", "gave", "sent", "now", "consent"})
    assert (one_half["split_words"], one_half["wraps_that_join"], one_half["letter_breaks"]) == ([], 0, 1)


def test_a_word_is_a_line_interior_token_of_the_bundle_or_an_entry_of_the_list(m):
    """The halves being judged are a line's first and last tokens, so those
    never count as words by themselves; the joined word does count when it
    is interior somewhere ('participants' on the last line)."""
    assert m.interior_words(["partic", "a b c", "ipants x"]) == {"b"}
    got = m.measure(TEXT)                                         # no word list at all
    # 'con' and 'sent' are interior nowhere, so by the bundle alone con/sent
    # is a split word too, and 'participants' and 'consent' are words.
    assert {s["word"] for s in got["split_words"]} == {"participants", "consent"}
    assert "consent" in m.interior_words(TEXT.split("\n"))


def test_a_split_that_hides_a_checked_form_moves_its_status(m):
    text = "Participants gave con\nsent to take part."
    got = m.measure(text, {"participants", "gave", "to", "take", "part", "consent"})
    assert got["split_words"] == [{"line": 1, "tail": "con", "head": "sent", "word": "consent"}]
    assert got["moved"] == {"consent_text": "status"}
    # The check itself still certifies the absence: the reading is not added.
    _, lines = at._lines_by_chunk(text, {})
    assert at.matching_lines(at.CHECKS_BY_NAME["consent_text"].pattern, lines) == []


def test_a_hyphenated_break_is_not_a_letter_break(m):
    assert m.letter_breaks(["con-", "sent", "a.", "b"]) == [(2, "sent", "a")]
    assert m.letter_breaks(["  over  ", "  sight"]) == [(1, "over", "sight")]


def test_the_window_counts_are_the_windows_the_readings_search(m):
    got = m.measure("a-\nb-\nc\nd\ne\nf\ng-\nh")
    assert (got["hyphenated_breaks"], got["most_in_one_window"]) == (3, 2)
    assert got["mixed_windows"] == 1           # lines 1-6 read breaks 1 and 2; no other window holds two
    wider = m.measure("data-\n-\n-\n-\n-\n-\nprotec-\ntion impact", compare_window=8)
    assert wider["window_moves"] == {"ethics_review": [0, 8]}
    assert at.MIXED_WINDOW_LINES == 6                              # restored


def test_bundle_versions_count_records_and_list_the_unreadable(m, tmp_path):
    for label, inputs in (("a", {"bundle_path": "x.txt", "bundle_md5": "1" * 32}),
                          ("b", {"bundle_path": "x.txt", "bundle_md5": "1" * 32}),
                          ("c", {"bundle_path": "x.txt", "bundle_md5": None})):
        (tmp_path / label).mkdir()
        (tmp_path / label / "P_provenance.yaml").write_text(yaml.safe_dump({"inputs": inputs}), encoding="utf-8")
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "P_provenance.yaml").write_text("inputs: [unclosed\n", encoding="utf-8")
    versions, unreadable = m.bundle_versions(tmp_path)
    assert versions == {("x.txt", "1" * 32): 2}
    assert len(unreadable) == 1 and "d/P_provenance.yaml (ParserError)" in unreadable[0]


def test_the_command_refuses_a_missing_word_list(m, tmp_path, capsys):
    assert m.main(["--words", str(tmp_path / "none"), "--corpus", str(tmp_path)]) == 2
    assert "no word list at" in capsys.readouterr().err
