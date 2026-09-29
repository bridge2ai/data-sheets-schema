"""Bundle-wide absence claims and record self-narration in free text (#2919).

The controls are the issue's own: five phrases the lint must flag, each under
its class, and one passage-local absence it must not. The rest pins what a
count means — which leaves are read, where a hit is reported, which lexicon
produced it — and that the committed baseline is what its pinned records
reproduce, with a record added since the pin reported rather than failed.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
import warnings
from pathlib import Path

import click.testing
import pytest
import yaml

from data_sheets_schema import absence_lint as al
from data_sheets_schema import lexicon as lx

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "absence_claims_baseline.py"
LEXICON_FILE = lx.LEXICON_DIR / "absence_self_narration_v1.yaml"

BWA, RSN = "bundle_wide_absence", "record_self_narration"

#: The issue's positive controls, each in a sentence of the kind a record carries.
POSITIVE = [
    ("No source in the bundle states a retention period for the data.", BWA, "No source in the bundle"),
    ("The calendar period of the encounters is not stated by any source.", BWA, "not stated by any source"),
    ("`keywords` is left empty.", RSN, "is left empty"),
    ("No per-site counts are published, so those slots are omitted.", RSN, "slots are omitted"),
    ("The release lists 1,200 recordings, which is the count recorded here.", RSN, "recorded here"),
]
#: The issue's negative control: an absence a passage states, quoted from it.
PASSAGE_LOCAL = "The release notes state that no erratum has been issued."


def _hits(record):
    return [(h["pointer"], h["class"], h["text"]) for h in al.lint(record)["hits"]]


class Controls(unittest.TestCase):
    def test_each_positive_control_is_flagged_under_its_class(self):
        for text, cls, phrase in POSITIVE:
            with self.subTest(text=text):
                self.assertEqual(_hits({"source_caveats": text}), [("/source_caveats", cls, phrase)])

    def test_a_passage_local_absence_is_not_flagged(self):
        result = al.lint({"source_caveats": PASSAGE_LOCAL, "errata": [{"erratum_details": PASSAGE_LOCAL}]})
        self.assertEqual((result["leaves"], result["phrases"], result["hits"]), (2, 0, []))

    def test_a_phrase_in_name_id_or_keywords_is_not_counted(self):
        phrase = POSITIVE[0][0]
        record = {"id": "doi:10.1/x#no-source-in-the-bundle", "name": phrase, "keywords": [phrase, "left empty"],
                  "creators": [{"name": phrase, "id": "is left empty"}],
                  # keys under an excluded key are skipped whole
                  "keywords_extra": None, "resources": [{"keywords": [{"description": phrase}]}]}
        self.assertEqual(_hits(record), [])
        self.assertEqual(al.lint(record)["leaves"], 0)
        record["description"] = phrase                                          # the control
        self.assertEqual(_hits(record), [("/description", BWA, "No source in the bundle")])

    def test_nothing_nested_under_name_or_id_is_read(self):
        """A string under `name` or `id` goes unread because neither is a
        free-text key, excluded or not; only a mapping or list under one
        reaches the exclusion itself (#3095). The control puts the same nodes
        under keys that are not excluded, where every one is read."""
        phrase = POSITIVE[0][0]
        nested = {"name": {"description": phrase}, "id": [{"notes": phrase}],
                  "creators": [{"name": [{"source_caveats": phrase}], "id": {"x_details": phrase}}]}
        self.assertEqual((_hits(nested), al.lint(nested)["leaves"]), ([], 0))
        control = {"alias": {"description": phrase}, "ids": [{"notes": phrase}],
                   "creators": [{"names": [{"source_caveats": phrase}], "ref": {"x_details": phrase}}]}
        self.assertEqual([h[0] for h in _hits(control)], [
            "/alias/description", "/ids/0/notes", "/creators/0/names/0/source_caveats", "/creators/0/ref/x_details"])


class Pointers(unittest.TestCase):
    def test_a_nested_list_members_caveat_is_reported_at_its_pointer(self):
        record = {"maintainers": [{"name": "A", "description": "Runs the portal."},
                                  {"name": "B", "source_caveats": "The bundle does not state her role."}]}
        self.assertEqual(_hits(record), [("/maintainers/1/source_caveats", BWA, "The bundle does not")])

    def test_list_members_details_slots_and_deep_nesting(self):
        record = {"notes": ["Plain note.", "Identifier coined for this record."],
                  "updates": {"update_details": ["Quarterly.", "x", "The sources do not state a cadence."]},
                  "resources": [{"file_collections": [{}, {}, {}, {"description": "total_bytes is omitted here."}]}]}
        self.assertEqual(_hits(record), [
            ("/notes/1", RSN, "this record"),
            ("/updates/update_details/2", BWA, "The sources do not state"),
            ("/resources/0/file_collections/3/description", RSN, "total_bytes is omitted here"),
        ])

    def test_pointer_tokens_are_escaped(self):
        record = {"a/b": [{"c~d": {"notes": "so those slots are omitted"}}]}
        self.assertEqual(_hits(record)[0][0], "/a~1b/0/c~0d/notes")

    def test_an_alias_is_read_where_it_appears_and_a_cycle_ends(self):
        record = yaml.safe_load("a: &x {notes: identifier coined for this record}\nb: *x\n"
                                "loop: &loop {self: *loop, notes: [is left empty]}\n")
        self.assertEqual([h[0] for h in _hits(record)], ["/a/notes", "/b/notes", "/loop/notes/0"])

    def test_non_string_leaves_are_not_read(self):
        import datetime
        record = {"description": 3, "notes": [datetime.date(2026, 1, 1), None, True], "timeframe_details": {}}
        self.assertEqual(al.lint(record)["leaves"], 0)


class Counting(unittest.TestCase):
    def test_two_patterns_on_the_same_words_are_one_phrase(self):
        result = al.lint({"notes": "No source in the bundle states a count."})
        self.assertEqual(result["phrases"], 1)
        self.assertEqual(result["hits"][0]["patterns"], ["bwa.no-source", "bwa.not-in-bundle"])
        self.assertEqual((result["by_pattern"]["bwa.no-source"], result["by_pattern"]["bwa.not-in-bundle"]), (1, 1))

    def test_every_class_and_pattern_is_present_at_zero(self):
        """A zero is a measurement, so the key is there when nothing matched."""
        result = al.lint({})
        self.assertEqual(result["by_class"], {BWA: {"phrases": 0, "leaves": 0}, RSN: {"phrases": 0, "leaves": 0}})
        self.assertEqual(set(result["by_pattern"]), {p.id for p in lx.load(al.LEXICON).patterns})
        self.assertEqual(set(result["by_pattern"].values()), {0})

    def test_text_is_matched_whitespace_collapsed(self):
        """A folded or literal block scalar wraps where the model wrapped it."""
        self.assertEqual(_hits({"notes": "No\n  source in the\tbundle states it."})[0][2], "No source in the bundle")


class Identity(unittest.TestCase):
    def test_the_result_names_the_instrument_version_and_lexicon_bytes(self):
        result = al.lint({"notes": POSITIVE[0][0]})
        self.assertEqual(result["instrument"], "absence_self_narration lexicon v1 (#2919)")
        self.assertEqual(result["lexicon"]["version"], 1)
        self.assertEqual(result["lexicon"]["sha256"], hashlib.sha256(LEXICON_FILE.read_bytes()).hexdigest())
        self.assertIs(result["gating"], False)

    def test_a_lexicon_without_the_scope_this_reader_needs_is_refused(self):
        raw = LEXICON_FILE.read_text(encoding="utf-8").replace("  excluded_keys: [name, id, keywords]\n", "")
        lexicon = lx.parse(raw.encode(), file="edited.yaml")
        with self.assertRaisesRegex(lx.LexiconError, "scope must list excluded_keys"):
            al.lint({}, lexicon)


class ReadOnlyCli(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.cli.review import review
        self.review = review
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.record = self.dir / "P_d4d.yaml"
        self.record.write_text("# header\nid: doi:10.1/x\nsource_caveats: >-\n  No source in the bundle\n"
                               "  states a license.\nnotes:\n- which is the count recorded here\n", encoding="utf-8")

    def test_text_output_reports_hits_exits_zero_and_writes_nothing(self):
        before = hashlib.sha256(self.record.read_bytes()).hexdigest()
        r = click.testing.CliRunner().invoke(self.review, ["absence-lint", "--record", str(self.record)])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("/source_caveats  bundle_wide_absence", r.output)
        self.assertIn("/notes/0  record_self_narration  rsn.recorded-here", r.output)
        self.assertIn("not gating", r.output)
        self.assertEqual(hashlib.sha256(self.record.read_bytes()).hexdigest(), before)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["P_d4d.yaml"])

    def test_json_is_one_result_per_record(self):
        r = click.testing.CliRunner().invoke(
            self.review, ["absence-lint", "--record", str(self.record), "--record", str(self.record), "--json"])
        self.assertEqual(r.exit_code, 0, r.output)
        out = json.loads(r.output)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["record"], str(self.record))
        self.assertEqual({h["pointer"] for h in out[0]["hits"]}, {"/source_caveats", "/notes/0"})

    def test_a_record_that_is_not_a_mapping_is_an_error_not_a_zero(self):
        self.record.write_text("- a list\n", encoding="utf-8")
        r = click.testing.CliRunner().invoke(self.review, ["absence-lint", "--record", str(self.record)])
        self.assertEqual(r.exit_code, 1)
        self.assertIn("is not a mapping", r.output)


def _script():
    spec = importlib.util.spec_from_file_location("absence_claims_baseline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Baseline(unittest.TestCase):
    """The script over a small corpus built here: selection, counting, the
    pinned record set and the check, without walking the committed corpus."""

    def setUp(self):
        self.m = _script()
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        corpus = self.corpus = self.dir / "data" / "d4d_concatenated"
        self._write("m_a/label1/P_d4d.yaml", {"source_caveats": "The bundle does not state a date.",
                                              "notes": ["Identifier coined for this record."]})
        self._write("m_a/label2/Q_d4d.yaml", {"description": "A plain description."})
        self._write("m_a/label2/intermediate/Q_d4d.yaml", {"notes": "not a record: too deep"})
        self._write("m_a_core/label1/P_d4d.yaml", {"notes": "a core record, never counted: left empty"})
        self._write("m_b/P_d4d.yaml", {"notes": "No source states it; so those slots are omitted."})
        (corpus / "m_b" / "R_d4d.yaml").write_text("- not a mapping\n", encoding="utf-8")
        self.m.CORPUS = corpus
        self.m.OUT_MD = self.dir / "note.md"
        self.m.PINS = self.dir / "records.yaml"

    def _write(self, rel, record):
        path = self.corpus / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(record), encoding="utf-8")

    def test_selection_counts_and_totals(self):
        collected = self.m.collect(self.corpus)
        self.assertEqual([r["path"] for r in collected["records"]],
                         ["m_a/label1/P_d4d.yaml", "m_a/label2/Q_d4d.yaml", "m_b/P_d4d.yaml", "m_b/R_d4d.yaml"])
        s = self.m.summarise(collected)
        self.assertEqual(s["methods"]["m_a"], {"records": 2, "unreadable": 0, "any": 1, "leaves": 3,
                                               BWA: {"records": 1, "phrases": 1}, RSN: {"records": 1, "phrases": 1}})
        self.assertEqual(s["methods"]["m_b"], {"records": 2, "unreadable": 1, "any": 1, "leaves": 1,
                                               BWA: {"records": 1, "phrases": 1}, RSN: {"records": 1, "phrases": 1}})
        self.assertEqual((s["total"]["records"], s["total"][BWA]["phrases"]), (4, 2))
        self.assertEqual(s["unreadable"], ["m_b/R_d4d.yaml (not a mapping)"])
        md = self.m.render_markdown(collected)
        self.assertIn("| m_a | 2 | 1 | 1 | 1 | 1 | 1 | 3 |", md)
        self.assertIn("| **all** | 4 | 2 | 2 | 2 | 2 | 2 | 4 |", md)
        self.assertIn("`m_b/R_d4d.yaml (not a mapping)`", md)
        self.assertIn(collected["lexicon"].sha256, md)
        self.assertIn("**Regex caveat.**", md)

    def test_the_note_is_deterministic_and_moves_with_any_record_byte(self):
        first = self.m.render_markdown(self.m.collect(self.corpus))
        self.assertEqual(first, self.m.render_markdown(self.m.collect(self.corpus)))
        with (self.corpus / "m_a/label2/Q_d4d.yaml").open("a", encoding="utf-8") as f:
            f.write("# a comment changes no count\n")
        self.assertNotEqual(first, self.m.render_markdown(self.m.collect(self.corpus)))

    def _main(self, *argv):
        """Run the script's main; return its exit status and what it wrote to stderr."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            status = self.m.main(list(argv))
        return status, err.getvalue()

    def test_check_is_read_only_and_needs_a_pinned_record_set(self):
        self.assertEqual(self._main("--check")[0], 1)                     # nothing pinned yet
        status, err = self._main()                                        # nor does a plain run pin silently
        self.assertEqual(status, 1)
        self.assertIn("could not be read", err)
        self.assertFalse(self.m.OUT_MD.exists() or self.m.PINS.exists())
        self.assertEqual(self._main("--repin")[0], 0)
        self.assertEqual(self._main("--check"), (0, ""))
        pins = self.m.read_pins(self.m.PINS)
        self.assertEqual(sorted(pins), ["m_a/label1/P_d4d.yaml", "m_a/label2/Q_d4d.yaml",
                                        "m_b/P_d4d.yaml", "m_b/R_d4d.yaml"])
        for rel, sha in pins.items():
            self.assertEqual(sha, hashlib.sha256((self.corpus / rel).read_bytes()).hexdigest())
        digest = hashlib.sha256("".join(f"{rel} {pins[rel]}\n" for rel in sorted(pins)).encode()).hexdigest()
        self.assertIn(f"record-set sha256 `{digest}`", self.m.OUT_MD.read_text(encoding="utf-8"))
        with self.m.OUT_MD.open("a", encoding="utf-8") as f:
            f.write("edited by hand\n")
        written = self.m.OUT_MD.read_bytes()
        status, err = self._main("--check")
        self.assertEqual(status, 1)
        self.assertIn("does not match its 4 pinned records", err)
        self.assertEqual(self.m.OUT_MD.read_bytes(), written)

    def test_a_record_added_after_pinning_is_reported_not_counted(self):
        """#3045: a data PR that only adds records leaves the note current.
        The added records are named, and only `--repin` counts them."""
        self.assertEqual(self._main("--repin")[0], 0)
        note, pins = self.m.OUT_MD.read_bytes(), self.m.PINS.read_bytes()
        self._write("m_b/S_d4d.yaml", {"notes": "is left empty"})
        self._write("m_c/label9/T_d4d.yaml", {"notes": "No source states it."})
        status, err = self._main("--check")
        self.assertEqual(status, 0, err)
        self.assertIn("reported, not counted: 2 full record(s)", err)
        self.assertIn("(m_b/S_d4d.yaml; m_c/label9/T_d4d.yaml)", err)
        self.assertEqual(self._main()[0], 0)                             # a plain rewrite does not count them
        self.assertEqual((self.m.OUT_MD.read_bytes(), self.m.PINS.read_bytes()), (note, pins))
        self.assertEqual(self.m.unpinned(self.corpus, self.m.read_pins(self.m.PINS)),
                         ["m_b/S_d4d.yaml", "m_c/label9/T_d4d.yaml"])
        self.assertEqual(self._main("--repin")[0], 0)                    # the deliberate act does
        self.assertIn("| **all** | 6 |", self.m.OUT_MD.read_text(encoding="utf-8"))
        self.assertEqual(len(self.m.read_pins(self.m.PINS)), 6)
        self.assertEqual(self._main("--check"), (0, ""))

    def test_a_pinned_record_that_changed_or_is_gone_makes_the_note_stale(self):
        self.assertEqual(self._main("--repin")[0], 0)
        note = self.m.OUT_MD.read_bytes()
        q = self.corpus / "m_a/label2/Q_d4d.yaml"
        original = q.read_bytes()
        q.write_bytes(original + b"# a comment changes no count\n")
        status, err = self._main("--check")
        self.assertEqual(status, 1)
        self.assertIn("changed m_a/label2/Q_d4d.yaml", err)
        status, err = self._main()                                       # nor is the note rewritten over it
        self.assertEqual(status, 1)
        self.assertIn("--repin", err)
        self.assertEqual(self.m.OUT_MD.read_bytes(), note)
        q.write_bytes(original)
        self.assertEqual(self._main("--check"), (0, ""))
        (self.corpus / "m_b/P_d4d.yaml").unlink()
        status, err = self._main("--check")
        self.assertEqual(status, 1)
        self.assertIn("gone m_b/P_d4d.yaml", err)
        with self.assertRaises(self.m.Stale) as ctx:
            self.m.collect(self.corpus, pins=self.m.read_pins(self.m.PINS))
        self.assertEqual((ctx.exception.changed, ctx.exception.missing), ([], ["m_b/P_d4d.yaml"]))

    def test_a_malformed_pin_file_is_refused(self):
        sha = "ab" * 32                          # a string in YAML; 64 zeros would parse as the integer 0
        self.m.PINS.write_text(f"records: {{m_b/P_d4d.yaml: {sha}}}\n", encoding="utf-8")
        self.assertEqual(self.m.read_pins(self.m.PINS), {"m_b/P_d4d.yaml": sha})       # the control
        for text, message in [
            ("records: {}\n", "no `records` mapping"),
            ("- a list\n", "no `records` mapping"),
            ("records: {m_b/P_d4d.yaml: not-a-sha}\n", "is not a path under the corpus pinned to a sha256"),
            (f"records: {{../outside_d4d.yaml: {sha}}}\n", "is not a path under the corpus"),
            (f"records: {{/abs/P_d4d.yaml: {sha}}}\n", "is not a path under the corpus"),
            ("records: [\n", "does not parse"),
        ]:
            with self.subTest(text=text):
                self.m.PINS.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(self.m.Stale, message):
                    self.m.read_pins(self.m.PINS)
                self.assertEqual(self._main("--check")[0], 1)

    def test_sample_prints_phrases_in_context_and_writes_nothing(self):
        out = self.m.sample(self.m.collect(self.corpus), 5, 1)
        self.assertEqual(out[0], f"## {BWA}: 2 of 2 phrases")
        self.assertTrue(any("[[The bundle does not]]" in line for line in out))
        self.assertFalse(self.m.OUT_MD.exists())

    def test_precision_is_shown_only_for_the_lexicon_it_was_checked_under(self):
        """#3094: the sample is keyed by lexicon sha256, so a note under other
        lexicon bytes shows none, and a sample keyed to those other bytes is
        not shown under v1."""
        collected = self.m.collect(self.corpus)
        v1 = collected["lexicon"]
        table = "| bundle_wide_absence | 50 | 0 | 0 |"
        self.assertIn(v1.sha256, self.m.PRECISION)
        self.assertIn(table, self.m.render_markdown(collected))
        # v1's patterns under other bytes: a stand-in for a later version
        other = lx.parse(LEXICON_FILE.read_bytes() + b"# a later version\n", file="absence_self_narration_v2.yaml")
        self.assertNotEqual(other.sha256, v1.sha256)
        under_other = self.m.collect(self.corpus, other)
        self.assertEqual(self.m.summarise(under_other)["total"], self.m.summarise(collected)["total"])
        md = self.m.render_markdown(under_other)
        self.assertIn("No precision sample has been checked under this lexicon's sha256.", md)
        self.assertNotIn(table, md)
        self.assertNotIn("| in class |", md)
        self.m.PRECISION = {other.sha256: self.m.PRECISION[v1.sha256]}
        self.assertIn(table, self.m.render_markdown(under_other))
        md = self.m.render_markdown(collected)
        self.assertIn("No precision sample has been checked", md)
        self.assertNotIn(table, md)

    def test_a_precision_sample_says_which_record_set_it_was_drawn_from(self):
        collected = self.m.collect(self.corpus)
        checked = self.m.PRECISION[collected["lexicon"].sha256]
        self.assertNotEqual(checked["record_set_sha256"], collected["record_set_sha256"])
        md = self.m.render_markdown(collected)
        self.assertIn("It was drawn from another record set (record-set sha256", md)
        self.assertIn(f"`{checked['record_set_sha256']}`), not the one this note counts.", md)
        checked["record_set_sha256"] = collected["record_set_sha256"]
        md = self.m.render_markdown(collected)
        self.assertIn("It was drawn from the record set this note counts.", md)
        self.assertNotIn("another record set", md)


@pytest.mark.corpus   # walks the committed corpus
def test_the_committed_baseline_is_what_its_pinned_records_reproduce():
    """Fails only when a pinned record changed or is gone, or when the note
    does not match the pinned records. A record added since the pin is
    reported as a warning and not counted (#3045)."""
    m = _script()
    pins = m.read_pins(m.PINS)
    try:
        collected = m.collect(m.CORPUS, pins=pins)
    except m.Stale as exc:
        pytest.fail(f"{exc}: run scripts/absence_claims_baseline.py --repin")
    assert collected["record_set_sha256"] in m.OUT_MD.read_text(encoding="utf-8")
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(collected), (
        "notes/absence_claims_baseline.md does not match its pinned records: run scripts/absence_claims_baseline.py")
    new = m.unpinned(m.CORPUS, pins)
    if new:
        warnings.warn(f"{len(new)} full record(s) are not in the absence baseline's pinned set and are not "
                      f"counted (reported, not stale), e.g. {new[:3]}; --repin counts them", stacklevel=1)


if __name__ == "__main__":
    unittest.main()
