"""The self_disclaimed corpus baseline (#3041): `scripts/self_disclaimed_baseline.py`
over a small corpus built here (selection, companions, counting, the pinned
set, the parse and the check), and the committed note against its pinned
records in the corpus lane."""
import contextlib
import importlib.util
import io
import warnings
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import self_disclaimed as sd
from data_sheets_schema.duplicate_keys import find_duplicate_keys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "self_disclaimed_baseline.py"
LABEL = "2026-01-01_example_rep1"
DISCLAIMER = "No source states who maintains the dataset."


def _script():
    spec = importlib.util.spec_from_file_location("self_disclaimed_baseline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def maintainer(name, caveat=True):
    member = {"name": name, "maintainer_details": "Listed under Contact Us."}
    if caveat:
        member["source_caveats"] = DISCLAIMER
    return member


def dump(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else yaml.safe_dump(value, sort_keys=False),
                    encoding="utf-8")
    return path


@pytest.fixture
def corpus(tmp_path):
    """One labelled pair and one unlabelled record.

    P: the snapshot flags Person A only; the final drops Person A,
    keeps Person B and adds a flagged Person C and an unflagged Person E.
    Its receipt, written against the snapshot, addresses Person A with a
    role predicate and nobody else. Q (unlabelled): one flag.
    `_full.yaml` is superseded by `_full_2.yaml`; `_full_2b.yaml` is not a
    snapshot."""
    root = tmp_path / "data" / "d4d_concatenated"
    core = root / "method_a_core" / LABEL
    dump(root / "method_a" / LABEL / "P_d4d.yaml",
         {"id": "x", "maintainers": [maintainer("Person B"), maintainer("Person C"),
                                     maintainer("Person E", caveat=False)]})
    dump(core / "intermediate" / "P_full.yaml", {"id": "x", "maintainers": []})
    dump(core / "intermediate" / "P_full_2.yaml",
         {"id": "x", "maintainers": [maintainer("Person A"), maintainer("Person B", caveat=False)]})
    dump(core / "intermediate" / "P_full_2b.yaml", {"id": "x"})
    dump(core / "P_coverage_receipt.yaml", {"chunks": [
        {"id": "c001", "status": "extracted",
         "extracted": [{"slot": "maintainers[0]", "snippet": "Maintained by Person A"}]}]})
    dump(root / "method_b" / "Q_d4d.yaml", {"id": "y", "maintainers": [maintainer("Person D")]})
    dump(root / "method_b_core" / "ignored_d4d.yaml", {"id": "z"})
    return root


def test_companions_are_the_last_numbered_snapshot_and_the_receipt(corpus):
    m = _script()
    assert [p.relative_to(corpus).as_posix() for p in m.record_paths(corpus)] == [
        f"method_a/{LABEL}/P_d4d.yaml", "method_b/Q_d4d.yaml"]
    found = m.companions(corpus, corpus / "method_a" / LABEL / "P_d4d.yaml")
    assert {k: v.name for k, v in found.items()} == {"snapshot": "P_full_2.yaml",
                                                     "receipt": "P_coverage_receipt.yaml"}
    assert m.companions(corpus, corpus / "method_b" / "Q_d4d.yaml") == {"snapshot": None, "receipt": None}


def test_counts_by_method_and_label(corpus):
    m = _script()
    collected = m.collect(corpus, lexicon_versions=[1, 2])
    s = m.summarise(collected, m.LEXICON_VERSION)
    a, b, t = s["methods"]["method_a"], s["methods"]["method_b"], s["total"]
    assert (a["records"], a["flagged"], a["flagged_records"], b["flagged"], t["flagged"]) == (1, 2, 1, 1, 3)
    # Snapshot to final: Person A's overlap join lands on Person C, whose
    # name conflicts, so it is identity_unresolved (#3265), not retained;
    # Person B's snapshot entry carries no disclaimer, so the final's
    # Person B and Person C are final_only.
    assert (a["pairs"], a["pair_flags"], a["classes"]["identity_unresolved"], a["classes"][m.RETAINED],
            a["final_only"]) == (1, 1, 1, 0, 2)
    assert b["pairs"] == 0
    # Check (b) against the snapshot (two members, not the final's three):
    # Person A is receipted with a predicate; Person B has no receipt and
    # is kept in the final.
    assert (a["receipts"], a["receipts_unchecked"], a["rp_against_snapshot"], a["rp_members"],
            a["rp_flagged"]) == (1, 0, 1, 2, 1)
    assert (a["rp_reasons"]["no_receipt"], a["rp_classes"][m.RP_RETAINED]) == (1, 1)
    assert s["labels"][("method_a", LABEL)]["flagged"] == 2 and s["labels"][("method_b", "-")]["flagged"] == 1


def test_the_note_names_the_lexicon_and_counts_every_version(corpus):
    m = _script()
    collected = m.collect(corpus)
    md = m.render_markdown(collected)
    assert sorted(collected["lexicons"]) == m.versions() and 1 in m.versions()
    current = collected["lexicons"][m.LEXICON_VERSION]
    assert f"sha256 `{current.sha256}`" in md and collected["record_set_sha256"] in md
    for version, lexicon in collected["lexicons"].items():
        assert f"| v{version} | `{lexicon.sha256[:12]}…` |" in md


def test_a_changed_or_missing_pinned_file_is_stale_and_a_new_record_is_reported(corpus):
    m = _script()
    pins = m.current_records(corpus)
    snapshot = corpus / pins[f"method_a/{LABEL}/P_d4d.yaml"]["snapshot"]["path"]
    snapshot.write_text(snapshot.read_text(encoding="utf-8") + "# edited\n", encoding="utf-8")
    with pytest.raises(m.Stale, match=r"1 pinned file\(s\) changed and 0 gone: changed .*P_full_2\.yaml"):
        m.collect(corpus, pins=pins)
    snapshot.unlink()
    with pytest.raises(m.Stale, match=r"0 pinned file\(s\) changed and 1 gone"):
        m.collect(corpus, pins=pins)
    dump(corpus / "method_b" / "R_d4d.yaml", {"id": "r"})
    assert m.unpinned(corpus, pins) == ["method_b/R_d4d.yaml"]


def test_pins_round_trip_and_a_malformed_pin_is_stale(corpus, tmp_path):
    m = _script()
    pins = m.current_records(corpus)
    path = tmp_path / "pins.yaml"
    m.write_pins(pins, path)
    assert m.read_pins(path) == pins
    entry = pins[f"method_a/{LABEL}/P_d4d.yaml"]
    for bad in ({**entry, "snapshot": {"path": "../x.yaml", "sha256": entry["sha256"]}},
                {**entry, "sha256": "abc"}, {k: v for k, v in entry.items() if k != "receipt"}):
        dump(path, {"records": {f"method_a/{LABEL}/P_d4d.yaml": bad}})
        with pytest.raises(m.Stale):
            m.read_pins(path)


@pytest.mark.parametrize("text", [
    "a: 1\na: 2\n",
    "true: 1\nTrue: 2\n",
    "1: a\n1.0: b\n",
    "a:\n- b: 1\n  b: 2\n",
    "1: a\n'1': b\n",
    "x: &x {k: 1}\nz:\n  <<: *x\n  k: 2\n",
    "x: &x {k: 1}\ny: &y {k: 2}\nz:\n  <<: [*x, *y]\n",
    "x: &x {k: 1}\nz:\n  <<: *x\n  <<: *x\n",
])
def test_a_record_is_refused_exactly_where_the_cli_refuses_it(text):
    """The script's fast parse refuses the duplicate keys
    `duplicate_keys.find_duplicate_keys` finds, and no merge key (`<<`)."""
    m = _script()
    try:
        m.load_record(text.encode())
        refused = False
    except ValueError as exc:
        refused = "duplicate" in str(exc)
    assert refused == bool(find_duplicate_keys(text))


def test_the_refusal_is_the_public_scan_on_libyaml(monkeypatch):
    """`load_record` asks `duplicate_keys.find_duplicate_keys` with the fast
    loader, not a private walk (#3704)."""
    from data_sheets_schema import duplicate_keys
    m = _script()
    seen = []

    def scan(text, loader=yaml.SafeLoader, *, strict=False):
        seen.append((loader, strict))
        return [{"path": "$", "key": "a", "lines": [1, 2], "count": 2}]

    monkeypatch.setattr(duplicate_keys, "find_duplicate_keys", scan)
    with pytest.raises(ValueError, match="duplicate"):
        m.load_record(b"a: 1\n")
    assert seen == [(duplicate_keys.FAST_LOADER, True)]


@pytest.mark.parametrize("head", ["a: 1\na: 2\nb: ", "b: "])
def test_a_record_too_deep_to_scan_is_refused_as_the_cli_refuses_it(head):
    """#3799: libyaml composes and constructs a record nested past the
    recursion limit, but the duplicate-key walk cannot reach its keys. The
    script refuses it (ValueError) where the CLI raises; it never loads a
    value whose first `a` the load silently dropped."""
    from data_sheets_schema import evidence_assertions
    m = _script()
    text = head + "{x: " * 1200 + "1" + "}" * 1200 + "\n"
    with pytest.raises(RecursionError):
        evidence_assertions.load_record(text)
    with pytest.raises(ValueError, match="recursion limit"):
        m.load_record(text.encode())


def test_the_note_carries_the_pr1_subtotal_and_says_which_finals_it_counted(corpus, monkeypatch):
    """#3029's figures counted two methods' finals; the note says so and
    carries their subtotal beside the all-methods total (#3703). A method
    with no records adds nothing to the subtotal."""
    m = _script()
    dump(corpus / "method_c" / "S_d4d.yaml", {"id": "s", "maintainers": [maintainer("Person F")]})
    monkeypatch.setattr(m, "PR1_METHODS", ("method_a", "method_c", "method_absent"))
    md = m.render_markdown(m.collect(corpus))
    assert "counted only the `method_a` and `method_c` and `method_absent` finals" in md
    assert "compare with the `method_a + method_c + method_absent` row, not with `**all**`" in md
    rows = [line for line in md.splitlines() if line.startswith("| *method_a + method_c + method_absent* |")]
    # method_a: 1 record, 2 flagged; method_c: 1 record, 1 flagged; method_b (Q) is left out.
    assert rows == ["| *method_a + method_c + method_absent* | 2 | 0 | 4 | 3 | 2 | 0 | 0 |"]
    assert "| **all** | 3 | 0 | 5 | 4 | 3 | 0 | 0 |" in md


def test_an_unreadable_file_is_listed_and_its_pair_is_not_diffed(corpus):
    m = _script()
    dump(corpus / "method_a_core" / LABEL / "intermediate" / "P_full_2.yaml", "a: 1\na: 2\n")
    s = m.summarise(m.collect(corpus), m.LEXICON_VERSION)
    a = s["methods"]["method_a"]
    assert (a["records"], a["unreadable"], a["flagged"], a["pairs"], a["rp_flagged"]) == (1, 0, 2, 0, 0)
    assert s["unreadable"] == [f"method_a_core/{LABEL}/intermediate/P_full_2.yaml "
                               "(artifact has duplicate YAML mapping keys; its location is ambiguous)"]
    # The receipt parsed, but no check (b) ran on it (#3730).
    assert (a["receipts"], a["receipts_unchecked"], a["rp_members"]) == (0, 1, 0)


@pytest.mark.parametrize("refused", ["final", "both"])
def test_a_receipt_beside_a_refused_final_is_not_counted_as_checked(corpus, refused):
    """A refused final has no check (b), even where its snapshot parses, so
    its receipt is `receipts_unchecked`, never `receipts` (#3730)."""
    m = _script()
    dump(corpus / "method_a" / LABEL / "P_d4d.yaml", "a: 1\na: 2\n")
    if refused == "both":
        dump(corpus / "method_a_core" / LABEL / "intermediate" / "P_full_2.yaml", "a: 1\na: 2\n")
    collected = m.collect(corpus)
    s = m.summarise(collected, m.LEXICON_VERSION)
    a, t = s["methods"]["method_a"], s["total"]
    assert (a["records"], a["unreadable"], a["pairs"]) == (1, 1, 0)
    assert (a["receipts"], a["receipts_unchecked"], a["rp_members"], a["rp_flagged"]) == (0, 1, 0, 0)
    assert (t["receipts"], t["receipts_unchecked"]) == (0, 1)
    md = m.render_markdown(collected)
    assert "| method | receipts checked | not checked |" in md
    assert "| method_a | 0 | 1 |" in md


@pytest.mark.parametrize("final_refused", [False, True])
@pytest.mark.parametrize("receipt_text", ["chunks: [\n", "chunks: {}\n"])
def test_a_refused_receipt_is_neither_checked_nor_not_checked(corpus, receipt_text, final_refused):
    """`not checked` is a *readable* receipt whose final or snapshot was
    refused (#3730); a receipt that is itself refused (not YAML, or no
    `chunks` list) is listed as unreadable and counted in neither column
    (#3757), whether or not its final parses."""
    m = _script()
    receipt = dump(corpus / "method_a_core" / LABEL / "P_coverage_receipt.yaml", receipt_text)
    if final_refused:
        dump(corpus / "method_a" / LABEL / "P_d4d.yaml", "a: 1\na: 2\n")
    collected = m.collect(corpus)
    s = m.summarise(collected, m.LEXICON_VERSION)
    a, t = s["methods"]["method_a"], s["total"]
    assert (a["records"], a["unreadable"]) == (1, int(final_refused))
    assert (a["receipts"], a["receipts_unchecked"], a["rp_members"]) == (0, 0, 0)
    assert (t["receipts"], t["receipts_unchecked"]) == (0, 0)
    assert any(line.startswith(receipt.relative_to(corpus).as_posix() + " (") for line in s["unreadable"])


def test_check_is_read_only_and_fails_when_stale(corpus, tmp_path, monkeypatch):
    m = _script()
    out_md, pins = tmp_path / "note.md", tmp_path / "pins.yaml"
    monkeypatch.setattr(m, "CORPUS", corpus)
    monkeypatch.setattr(m, "OUT_MD", out_md)
    monkeypatch.setattr(m, "PINS", pins)

    def run(*argv):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            return m.main(list(argv)), err.getvalue()

    assert run("--check")[0] == 1                     # no pins yet
    assert run("--repin")[0] == 0 and out_md.exists() and pins.exists()
    written = out_md.read_bytes()
    assert run("--check") == (0, "")
    dump(corpus / "method_b" / "R_d4d.yaml", {"id": "r"})
    code, err = run("--check")
    assert code == 0 and "reported, not counted: 1 full record" in err
    out_md.write_text("edited\n", encoding="utf-8")
    assert run("--check")[0] == 1 and out_md.read_text(encoding="utf-8") == "edited\n"
    assert run()[0] == 0 and out_md.read_bytes() == written
    dump(corpus / "method_b" / "Q_d4d.yaml", {"id": "changed"})
    code, err = run("--check")
    assert code == 1 and "stale: 1 pinned file(s) changed" in err


@pytest.mark.corpus   # walks the committed corpus
def test_the_committed_baseline_is_what_its_pinned_records_reproduce():
    """Fails when a pinned file changed or is gone, or when the note does not
    match the pinned files. A record added since the pin is a warning."""
    m = _script()
    pins = m.read_pins(m.PINS)
    try:
        collected = m.collect(m.CORPUS, pins=pins)
    except m.Stale as exc:
        pytest.fail(f"{exc}: run scripts/self_disclaimed_baseline.py --repin")
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(collected), (
        "notes/self_disclaimed_baseline.md does not match its pinned records: run scripts/self_disclaimed_baseline.py")
    new = m.unpinned(m.CORPUS, pins)
    if new:
        warnings.warn(f"{len(new)} full record(s) are not in the self_disclaimed baseline's pinned set and are "
                      f"not counted (reported, not stale), e.g. {new[:3]}; --repin counts them", stacklevel=1)
    assert m.LEXICON_VERSION == sd.load_lexicon().version
