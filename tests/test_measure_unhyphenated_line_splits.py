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
    assert len(unreadable) == 1 and "d/P_provenance.yaml is not YAML" in unreadable[0]


@pytest.mark.parametrize("body, why", [
    ("inputs: false\n", "is not a mapping with an inputs mapping"),
    ("inputs: []\n", "is not a mapping with an inputs mapping"),
    ("inputs: {bundle_path: 5, bundle_md5: abc}\n", "names a bundle_path or bundle_md5 that is not a string"),
    ("inputs: {bundle_path: [x.txt], bundle_md5: abc}\n", "names a bundle_path or bundle_md5 that is not a string"),
    ("recorded: 2026-99-29\ninputs: {bundle_path: x.txt, bundle_md5: abc}\n", "cannot be read: month must be in"),
    ("- inputs\n", "is not a mapping with an inputs mapping"),
])
def test_a_malformed_record_is_listed_and_the_records_after_it_still_counted(m, tmp_path, capsys, body, why):
    """#3579: the script read `inputs` with `or {}` and skipped any value
    that was not a string, so `inputs: false` and a non-string bundle path
    vanished from both the versions and the unreadable list, and an
    unquoted invalid date raised ValueError out of the run. It now reads a
    record as `credited` does: the malformed one (between two good ones) is
    listed with its reason, both good ones are counted, and the command
    prints its table and exits 1."""
    good = {"inputs": {"bundle_path": "x.txt", "bundle_md5": "1" * 32}}
    for label, text in (("a", yaml.safe_dump(good)), ("b", body), ("c", yaml.safe_dump(good))):
        (tmp_path / label).mkdir()
        (tmp_path / label / "P_provenance.yaml").write_text(text, encoding="utf-8")
    versions, unreadable = m.bundle_versions(tmp_path)
    assert versions == {("x.txt", "1" * 32): 2}
    assert len(unreadable) == 1 and "b/P_provenance.yaml" in unreadable[0] and why in unreadable[0], unreadable
    assert m.main(["--no-word-list", "--corpus", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "| `x.txt` | `11111111` | 2 |" in out and "Provenance records that could not be read: " in out


def test_a_readable_corpus_exits_zero(m, tmp_path, capsys):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "P_provenance.yaml").write_text("inputs: {bundle_path: x.txt, bundle_md5: null}\n",
                                                      encoding="utf-8")
    assert m.main(["--no-word-list", "--corpus", str(tmp_path)]) == 0


def test_the_command_refuses_a_missing_word_list(m, tmp_path, capsys):
    assert m.main(["--words", str(tmp_path / "none"), "--corpus", str(tmp_path)]) == 2
    assert "no word list at" in capsys.readouterr().err


def test_every_break_joins_means_every_break_not_only_letter_letter_ones(m):
    """#3438: the AI_READI bundles wrap their version as 'for v' / '2.0.0',
    a letter/digit break. Read as nothing it joins to 'v2.0.0', a match of
    `version_string` that takes a character from the first line, which the
    bytes as they are do not. The every-break column must see it."""
    got = m.measure("This documentation is for v\n2.0.0 of the data.")
    assert got["letter_breaks"] == 0 and got["joinable_breaks"] == 1
    assert got["moved_if_every_break_joins"] == {"version_string": "lines"}
    bare = m.measure("This documentation is for v\n2 of the data.")         # 'v2': no match either side
    assert bare["moved_if_every_break_joins"] == {"version_string": "status"}
    # Digit/digit and punctuation breaks count; a blank line and a hyphenated
    # break (read already) do not.
    assert m.joinable_breaks(["10.", "1234/x", "", "y", "con-", "sent", "z"]) == [1, 4, 6]


def test_a_letter_outside_ascii_is_a_letter(m):
    """#3438: the CM4AI bundles carry breaks with a letter outside ASCII on
    one side; the split-word test judges them like any other."""
    assert m.letter_breaks(["un café", "über alles"]) == [(1, "café", "über")]
    assert m.interior_words(["a naïve b"]) == {"naïve"}
    got = m.measure("the prot\négé left", {"the", "left", "protégé"})
    assert got["split_words"] == [{"line": 1, "tail": "prot", "head": "égé", "word": "protégé"}]


def test_the_wider_window_reports_its_own_load(m):
    """#3439: the window counts at `--compare-window N` are the cost of the
    wider window; the table's are at `MIXED_WINDOW_LINES`."""
    got = m.measure("a-\nb\nc\nd-\ne\nf\ng-\nh\ni", compare_window=8)
    assert (got["mixed_windows"], got["most_in_one_window"]) == (3, 2)
    assert (got["compare_mixed_windows"], got["compare_most_in_one_window"]) == (4, 3)
    assert m.window_load(at._lines_by_chunk("a-\nb\nc\nd-\ne\nf\ng-\nh\ni", {})[1], 8) == (4, 3)
    result = {"words": {"path": None, "sha256": None, "entries": 0}, "mixed_window_lines": 6,
              "compare_window": 8, "unreadable_records": [],
              "rows": [{"bundle": "x/B.txt", "md5": "f" * 32, "records": 1, **got}]}
    assert ("At 8 lines the most hyphenated breaks in one window is 3 (`B.txt` `ffffffff`, "
            "4 windows with two or more), read 24 ways") in m.markdown(result)
    # The heaviest wider window is named, not the row heaviest at six lines.
    six = {**got, "most_in_one_window": 5, "compare_most_in_one_window": 2, "compare_mixed_windows": 9}
    result["rows"].insert(0, {"bundle": "x/A.txt", "md5": "a" * 32, "records": 1, **six})
    assert "window is 3 (`B.txt`" in m.markdown(result)


def test_a_match_that_only_touches_the_break_does_not_cross_it(m):
    """#3471: a match crosses a join only when it takes a character from
    each side. One that ends where the first line ends ('consent' / 'from')
    or starts where the second begins ('nothing' / 'consent') is a match on
    one line as it stands, and joining the break adds nothing to it. The
    review of #3471 counted such matches as crossing and the column gained
    `ethics_review` on the CHORUS document versions and five checks on the
    CM4AI, AI_READI, VOICE and VOICE_PEDIATRIC ones."""
    for text in ("We obtained consent\nfrom all.", "We obtained nothing\nconsent later."):
        lines = text.split("\n")
        assert m.crossing_checks(lines, 1) == set(), text
        assert m.measure(text)["moved_if_every_break_joins"] == {}, text
    # A crossing on a check both lines already match adds no line.
    assert m.crossing_checks(["consent was con", "sent twice, consent"], 1) == {"consent_text"}
    assert m.measure("consent was con\nsent twice, consent")["moved_if_every_break_joins"] == {}
    # One character past the break on each side is a crossing.
    assert m.crossing_checks(["We obtained consen", "t from all."], 1) == {"consent_text"}
    assert m.crossing_checks(["We obtained c", "onsent from all."], 1) == {"consent_text"}


def test_every_break_joins_is_searched_one_break_at_a_time(m):
    """#3470: the every-break column joins the two lines around one break
    and reads no other line, so a match needing two breaks at once (or a
    third line at all) is not found (#3490). The note and README call the column a lower bound for
    that reason; these pin the cases they name. `--joins-per-window 2`
    finds them (#3481, the test below); this column keeps its scope."""
    assert m.measure("Participants gave con\nsent to take part.")["moved_if_every_break_joins"] == {
        "consent_text": "status"}
    for text in ("Participants gave con\nsen\nt to take part.",       # two unhyphenated breaks
                 "Participants gave con-\nsen\nt to take part.",      # one beside a hyphen's reading
                 "a data\nprotection im\npact assessment was done"):  # a space, then the join
        assert m.measure(text)["moved_if_every_break_joins"] == {}, text
    assert m.measure("a data pro\ntection impact assessment was done")["moved_if_every_break_joins"] == {
        "ethics_review": "status"}


def test_joins_per_window_searches_up_to_k_breaks_at_once(m):
    """#3481: `--joins-per-window K` reads every run of K consecutive breaks
    every way in which at least one joins, a hyphen's break under each of
    its readings. At K=2 it finds the three cases the one-break column
    misses; a word split over three unhyphenated breaks needs K=3."""
    for text, moved in (("Participants gave con\nsen\nt to take part.", {"consent_text": "status"}),
                        ("Participants gave con-\nsen\nt to take part.", {"consent_text": "status"}),
                        ("a data\nprotection im\npact assessment was done", {"ethics_review": "status"})):
        got = m.measure(text, joins_per_window=2)
        assert got["moved_if_every_break_joins"] == {}, text
        assert got["moved_if_up_to_k_breaks_join"] == moved, text
    three = "Participants gave co\nns\nen\nt to take part."
    assert m.measure(three, joins_per_window=2)["moved_if_up_to_k_breaks_join"] == {}
    assert m.measure(three, joins_per_window=3)["moved_if_up_to_k_breaks_join"] == {"consent_text": "status"}
    assert "moved_if_up_to_k_breaks_join" not in m.measure(three)


@pytest.mark.parametrize("text", [TEXT, "This documentation is for v\n2.0.0 of the data.",
                                  "This documentation is for v\n2 of the data.", "We obtained consent\nfrom all.",
                                  "consent was con\nsent twice, consent", "We obtained c\nonsent from all."])
def test_one_join_per_window_is_the_every_break_column(m, text):
    """K=1 is the every-break column read by the module's search
    (`attainability.join_matching_lines`) rather than the script's own, so
    the two must agree; K=2 reads every single join too."""
    got = m.measure(text, joins_per_window=1)
    assert got["moved_if_up_to_k_breaks_join"] == got["moved_if_every_break_joins"], text
    assert m.measure(text, joins_per_window=2)["moved_if_up_to_k_breaks_join"] == got["moved_if_every_break_joins"]


def test_joins_per_window_adds_a_column_and_refuses_zero(m, tmp_path, capsys):
    got = m.measure("Participants gave con\nsen\nt to take part.", joins_per_window=2)
    result = {"words": {"path": None, "sha256": None, "entries": 0}, "mixed_window_lines": 6,
              "compare_window": None, "joins_per_window": 2, "unreadable_records": [],
              "rows": [{"bundle": "x/B.txt", "md5": "f" * 32, "records": 1, **got},
                       {"bundle": "x/C.txt", "md5": "c" * 32, "records": 1, "error": "gone"}]}
    table = m.markdown(result).splitlines()
    assert table[2].endswith("| Most in one | Moved if up to 2 breaks join |")
    assert table[3].endswith("|---:|---|")
    assert table[4].endswith("| none | 0 | 0 | 0 | consent_text (status) |"), table[4]
    assert all(line.count("|") == table[2].count("|") for line in table[2:6])
    assert "Moved if up to" not in m.markdown({**result, "joins_per_window": None})
    assert m.main(["--no-word-list", "--corpus", str(tmp_path), "--joins-per-window", "0"]) == 2
    assert "--joins-per-window must be at least 1" in capsys.readouterr().err
