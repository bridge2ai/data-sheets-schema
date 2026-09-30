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
import random
import re
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
JUDGEMENTS = ROOT / "notes" / "absence_precision_judgements_99c92000.yaml"

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


class Time(unittest.TestCase):
    """#3894: the lint's time on one sentence grows linearly with the
    abbreviation dots in it. The first form of v4's `rsn.source-ranking`
    gap let two alternatives take the `.` of "e.g.," and tried a sentence
    with no partner for its verb or term 2^k ways: about 6 s at 20 items,
    so the n=20 call below fails its ceiling before n=40 is tried."""

    #: Verb with no term, term with no verb (each branch of the pattern
    #: fails), and a term whose verb closes the sentence (it matches).
    #: One "e.g.," per item, so the first form fails at n=20 in seconds
    #: rather than hanging (k such dots cost it 2^k).
    SENTENCES = {
        "verb, no term": ("The source was used, ", "e.g., x ", "and nothing else."),
        "term, no verb": ("The higher-ranked source lists items, ", "e.g., x ", "and more."),
        "term, then verb": ("The higher-ranked source lists items, ", "e.g., x ", "and that value is used."),
    }
    CEILING = 1.0       # seconds for one call; the fixed pattern takes about a millisecond

    def _lint(self, n):
        import time
        record = {"source_caveats": [head + item * n + tail for head, item, tail in self.SENTENCES.values()]}
        start = time.perf_counter()
        result = al.lint(record)
        return time.perf_counter() - start, result

    def test_time_grows_linearly_and_the_counts_do_not_move(self):
        results = {}
        for n in (20, 40):                                  # each call bounded before the next
            elapsed, results[n] = self._lint(n)
            self.assertLess(elapsed, self.CEILING, f"one lint call at n={n} took {elapsed:.2f} s")
        for n in (20, 40):
            hits = [(h["pointer"], h["patterns"]) for h in results[n]["hits"]]
            self.assertEqual(hits, [("/source_caveats/2", ["rsn.source-ranking"])])
        self.assertEqual(results[20]["by_pattern"], results[40]["by_pattern"])
        # Best of five against best of five: linear growth doubles the time,
        # quadratic quadruples it, and 2^k would multiply it by about a million.
        best = {n: min(self._lint(n)[0] for _ in range(5)) for n in (20, 40)}
        self.assertLess(best[40], 8 * best[20] + 0.005, best)


class Identity(unittest.TestCase):
    def test_the_result_names_the_instrument_version_and_lexicon_bytes(self):
        """The newest registered version unless one is passed (#3132)."""
        result = al.lint({"notes": POSITIVE[0][0]})
        self.assertEqual(result["instrument"], "absence_self_narration lexicon v4 (#3791)")
        self.assertEqual(result["lexicon"]["version"], 4)
        self.assertEqual(result["lexicon"]["sha256"], hashlib.sha256(
            (lx.LEXICON_DIR / "absence_self_narration_v4.yaml").read_bytes()).hexdigest())
        self.assertIs(result["gating"], False)
        v1 = al.lint({"notes": POSITIVE[0][0]}, lx.load(al.LEXICON, 1))
        self.assertEqual((v1["lexicon"]["version"], v1["lexicon"]["sha256"]),
                         (1, hashlib.sha256(LEXICON_FILE.read_bytes()).hexdigest()))
        self.assertEqual(v1["hits"], result["hits"])

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

    def _run(self, *argv):
        """Run the script's main; return its exit status, stdout and stderr."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            status = self.m.main(list(argv))
        return status, out.getvalue(), err.getvalue()

    def _main(self, *argv):
        """Run the script's main; return its exit status and what it wrote to stderr."""
        status, _, err = self._run(*argv)
        return status, err

    def _tree(self):
        """Every file under the test directory, with its bytes."""
        return {p.relative_to(self.dir).as_posix(): p.read_bytes() for p in sorted(self.dir.rglob("*")) if p.is_file()}

    def _spoil_note(self):
        """Append a line no rewrite keeps: a rewrite of a current note
        reproduces its bytes, so only a note that differs shows one."""
        with self.m.OUT_MD.open("a", encoding="utf-8") as f:
            f.write("a line no rewrite would keep\n")

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

    def test_sample_prints_each_phrase_in_its_context_and_the_draw_last(self):
        collected = self.m.collect(self.corpus)
        out = self.m.sample(collected, 5, 1)
        self.assertEqual(out[0], f"## {BWA}: 2 of 2 phrases")
        self.assertTrue(any("[[The bundle does not]]" in line for line in out))
        digest = self.m.draw_sha256(self.m.draw(collected, 5, 1))
        self.assertEqual(out[-1], f"draw sha256 {digest} (--sample 5 --seed 1)")

    def test_the_sample_mode_writes_nothing(self):
        """#3173: the mode's read-only promise is checked in `main`, where it
        lives, not in the function that only returns lines. A run with no
        note must not create one either."""
        self.assertEqual(self._main("--repin")[0], 0)
        self._spoil_note()
        before = self._tree()
        status, out, err = self._run("--sample", "3")
        self.assertEqual(status, 0, err)
        self.assertIn(f"## {BWA}: 2 of 2 phrases", out)
        self.assertEqual(self._tree(), before)
        self.m.OUT_MD.unlink()
        before = self._tree()
        self.assertEqual(self._run("--sample", "3", "--seed", "7")[0], 0)
        self.assertEqual(self._tree(), before)

    def test_the_sample_is_drawn_from_the_pinned_records_only(self):
        """#3173: a record added since the pin is not drawn from, and a pinned
        record whose bytes moved stops the draw rather than being sampled as
        the bytes it holds now."""
        self.assertEqual(self._main("--repin")[0], 0)
        self._write("m_c/label9/T_d4d.yaml", {"notes": "No source states it, and keywords is left empty."})
        status, out, err = self._run("--sample", "50")
        self.assertEqual(status, 0, err)
        self.assertIn("reported, not counted: 1 full record(s)", err)
        self.assertIn(f"## {BWA}: 2 of 2 phrases", out)
        self.assertIn(f"## {RSN}: 2 of 2 phrases", out)
        self.assertNotIn("m_c/label9/T_d4d.yaml", out)
        self.assertEqual(self._main("--repin")[0], 0)                    # the control: once pinned, it is drawn
        status, out, err = self._run("--sample", "50")
        self.assertIn(f"## {BWA}: 3 of 3 phrases", out)
        self.assertIn("m_c/label9/T_d4d.yaml", out)
        with (self.corpus / "m_b/P_d4d.yaml").open("a", encoding="utf-8") as f:
            f.write("# a comment changes no count\n")
        status, out, err = self._run("--sample", "50")
        self.assertEqual((status, out), (1, ""))
        self.assertIn("changed m_b/P_d4d.yaml", err)

    @staticmethod
    def _drawn(out, cls):
        """The (record, pointer) of each phrase `--sample` printed for a class."""
        section = out.split(f"## {cls}: ", 1)[1].split("\n## ", 1)[0]
        return [(m[1], m[2]) for m in re.finditer(r"^\d+\. (\S+) (\S+) ", section, re.M)]

    def test_the_sample_is_the_seeded_draw_over_the_pinned_phrases(self):
        """#3173: `--sample N --seed S` is `random.Random(S).sample` over each
        class's pinned phrases in record order, one generator per class: the
        draw the committed precision table names. A seed that is ignored, a
        draw that takes the first N, a generator one class's draw advances
        for the next, or a default seed other than the table's fails here."""
        for i in range(12):
            self._write(f"m_d/label/P{i:02d}_d4d.yaml", {"source_caveats": f"The bundle does not state item {i}.",
                                                         "notes": [f"Identifier {i} coined for this record."]})
        self.assertEqual(self._main("--repin")[0], 0)
        collected = self.m.collect(self.corpus, pins=self.m.read_pins(self.m.PINS))
        hits = {cls: [(r["path"], h["pointer"]) for r in collected["records"] if r["result"]
                      for h in r["result"]["hits"] if h["class"] == cls] for cls in (BWA, RSN)}
        self.assertEqual((len(hits[BWA]), len(hits[RSN])), (14, 14))
        drawn = {}
        for seed in (5, 6):
            status, out, err = self._run("--sample", "3", "--seed", str(seed))
            self.assertEqual(status, 0, err)
            self.assertEqual(self._run("--sample", "3", "--seed", str(seed))[1], out)        # reproducible
            for cls in (BWA, RSN):
                drawn[seed, cls] = self._drawn(out, cls)
                self.assertEqual(drawn[seed, cls], random.Random(seed).sample(hits[cls], 3))
            self.assertEqual(out.splitlines()[-1], f"draw sha256 {self.m.draw_sha256(self.m.draw(collected, 3, seed))}"
                                                   f" (--sample 3 --seed {seed})")
        self.assertNotEqual(drawn[5, BWA], drawn[6, BWA])
        self.assertNotIn(hits[BWA][:3], [drawn[5, BWA], drawn[6, BWA]])
        self.assertEqual(self._run("--sample", "3")[1], self._run("--sample", "3", "--seed", "2919")[1])

    def test_a_sample_below_one_or_a_seed_without_sample_is_refused(self):
        """#3173: `--sample 0` was read as no `--sample` and rewrote the note,
        and `--sample -1` ended in a ValueError. Each is now a usage error
        that writes nothing; so is a `--seed` that no draw would use."""
        self.assertEqual(self._main("--repin")[0], 0)
        self._spoil_note()
        before = self._tree()
        for argv, message in [(["--sample", "0"], "argument --sample: 0 is not a count of at least 1"),
                              (["--sample", "-1"], "argument --sample: -1 is not a count of at least 1"),
                              (["--sample", "x"], "argument --sample: 'x' is not an integer"),
                              (["--seed", "5"], "--seed applies only with --sample"),
                              (["--check", "--seed", "5"], "--seed applies only with --sample")]:
            with self.subTest(argv=argv):
                err = io.StringIO()
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as ctx:
                        self.m.main(argv)
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn(message, err.getvalue())
                self.assertEqual(self._tree(), before)

    def test_the_draw_digest_names_the_phrases_drawn_and_their_order(self):
        """What the note's draw sha256 is over: each drawn phrase's class,
        record, pointer and span, in the order drawn, and nothing printed."""
        p = ("m/P_d4d.yaml", {"pointer": "/notes/0", "start": 3, "end": 9, "text": "x", "patterns": ["a"]})
        q = ("m/Q_d4d.yaml", {"pointer": "/description", "start": 0, "end": 4, "text": "y", "patterns": ["b"]})
        r = ("m/R_d4d.yaml", {"pointer": "/notes/1", "start": 1, "end": 2, "text": "z", "patterns": ["c"]})
        expected = hashlib.sha256((f"{BWA}\tm/Q_d4d.yaml\t/description\t0\t4\n{BWA}\tm/P_d4d.yaml\t/notes/0\t3\t9\n"
                                   f"{RSN}\tm/R_d4d.yaml\t/notes/1\t1\t2\n").encode()).hexdigest()
        self.assertEqual(self.m.draw_sha256({BWA: (5, [q, p]), RSN: (1, [r])}), expected)
        reworded = (p[0], {**p[1], "text": "other words", "patterns": []})
        self.assertEqual(self.m.draw_sha256({BWA: (9, [q, reworded]), RSN: (1, [r])}), expected)
        self.assertNotEqual(self.m.draw_sha256({BWA: (5, [p, q]), RSN: (1, [r])}), expected)      # another order
        self.assertNotEqual(self.m.draw_sha256({BWA: (5, [q]), RSN: (1, [p, r])}), expected)      # another class

    def _collect_v1(self):
        """The fixture corpus under lexicon v1, whose precision entry and
        judgements (#3197) the tests below spoil and check. The note counts
        under v3 since #3520; the mechanism is the same for every entry."""
        return self.m.collect(self.corpus, lx.load(al.LEXICON, 1))

    def _judgements_copy(self, checked, edit=None, **fields):
        """Point a precision entry at a copy of the committed judgements with
        top-level `fields` replaced and `edit` applied to the parsed file."""
        data = yaml.safe_load(JUDGEMENTS.read_text(encoding="utf-8"))
        data.update(fields)
        if edit:
            edit(data)
        path = self.dir / f"judgements_{len(list(self.dir.glob('judgements_*')))}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        checked["judgements"] = str(path)
        return path

    def test_precision_is_shown_only_for_the_lexicon_it_was_checked_under(self):
        """#3094: the sample is keyed by lexicon sha256, so a note under other
        lexicon bytes shows none, and a sample keyed to those other bytes is
        not shown under v1. Its judgements name the bytes they were judged
        under too, so moving the entry alone is refused (#3197)."""
        collected = self._collect_v1()
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
        entry = dict(self.m.PRECISION[v1.sha256])
        self.m.PRECISION = {other.sha256: entry}
        with self.assertRaisesRegex(self.m.Refused, "lexicon_sha256 is '7b5c2237"):
            self.m.render_markdown(under_other)
        self._judgements_copy(entry, lexicon_sha256=other.sha256)
        self.assertIn(table, self.m.render_markdown(under_other))
        md = self.m.render_markdown(collected)
        self.assertIn("No precision sample has been checked", md)
        self.assertNotIn(table, md)

    def test_a_precision_sample_says_which_record_set_it_was_drawn_from(self):
        collected = self._collect_v1()
        checked = self.m.PRECISION[collected["lexicon"].sha256]
        self.assertNotEqual(checked["record_set_sha256"], collected["record_set_sha256"])
        md = self.m.render_markdown(collected)
        self.assertIn("It was drawn from another record set (record-set sha256", md)
        self.assertIn(f"`{checked['record_set_sha256']}`), not the one this note counts.", md)
        self.assertIn(f"`{checked['draw_sha256']}`; `--sample` prints it last.", md)
        self.assertIn("A seeded sample (`--sample 50 --seed 2919`)", md)
        checked.update(seed=11)                                          # the draw it names is the entry's ...
        with self.assertRaisesRegex(self.m.Refused, "seed is 2919, not the precision entry's 11"):
            self.m.render_markdown(collected)                            # ... and its judgements' (#3197)
        self._judgements_copy(checked, seed=11)
        self.assertIn("A seeded sample (`--sample 50 --seed 11`)", self.m.render_markdown(collected))
        checked["record_set_sha256"] = collected["record_set_sha256"]
        self._judgements_copy(checked, seed=11, record_set_sha256=collected["record_set_sha256"])
        md = self.m.render_markdown(collected)
        self.assertIn("It was drawn from the record set this note counts.", md)
        self.assertNotIn("another record set", md)

    def test_judgements_naming_another_draw_lexicon_record_set_sample_or_seed_are_refused(self):
        """#3197/#3566: the file must name each of the entry's identity fields.
        The draw hash covers only the phrases, so a file naming another record
        set, sample or draw would otherwise pass; each mismatch is refused."""
        collected = self._collect_v1()
        checked = self.m.PRECISION[collected["lexicon"].sha256]
        for key, value in [("draw_sha256", "0" * 64), ("lexicon_sha256", "1" * 64),
                           ("record_set_sha256", "2" * 64), ("sample", checked["sample"] + 1),
                           ("seed", checked["seed"] + 1)]:
            with self.subTest(key=key):
                self._judgements_copy(checked, **{key: value})
                with self.assertRaisesRegex(self.m.Refused, f"{key} is {value!r}, not the precision entry's"):
                    self.m.render_markdown(collected)
        self._judgements_copy(checked)                   # the control: an unspoiled copy renders
        self.assertIn("| record_self_narration | 47 | 3 | 0 |", self.m.render_markdown(collected))

    def test_judgements_of_other_classes_or_of_more_phrases_than_the_sample_are_refused(self):
        """#3566: a missing class is refused, not a KeyError; an extra class
        is refused, not ignored; a class with more rows than the sample, or
        rows that are not a list, is refused before its draw is hashed."""
        collected = self._collect_v1()
        checked = self.m.PRECISION[collected["lexicon"].sha256]

        def missing(data):
            del data["judgements"][RSN]

        def extra(data):
            data["judgements"]["another_class"] = []

        def oversized(data):
            rows = data["judgements"][BWA]
            rows.append(dict(rows[0]))

        def not_a_list(data):
            data["judgements"][BWA] = {"verdict": "in class"}

        for edit, message in [(missing, r"judges classes \['bundle_wide_absence'\], not the precision entry's"),
                              (extra, r"judges classes \['another_class', .*not the precision entry's"),
                              (oversized, f"{BWA} is not a list of at most 50 judgements"),
                              (not_a_list, f"{BWA} is not a list of at most 50 judgements")]:
            with self.subTest(edit=edit.__name__):
                self._judgements_copy(checked, edit)
                with self.assertRaisesRegex(self.m.Refused, message):
                    self.m.render_markdown(collected)

    def test_judgements_that_do_not_parse_are_not_a_mapping_or_lack_a_key_are_refused(self):
        """#3596: a file that does not parse, whose top level is not a mapping,
        whose `judgements` is not a mapping, or with a row missing any of
        record, pointer, start or end is refused, not a YAMLError,
        AttributeError or KeyError that `main` would let through as a
        traceback."""
        collected = self._collect_v1()
        checked = self.m.PRECISION[collected["lexicon"].sha256]
        cases = []
        for key in ("record", "pointer", "start", "end"):
            def drop_key(data, key=key):
                del data["judgements"][RSN][4][key]
            cases.append((f"row without {key}", drop_key, "needs record, pointer, start, end, a reason"))

        def judgements_a_list(data):
            data["judgements"] = list(data["judgements"].values())
        cases.append(("judgements a list", judgements_a_list, "has no `judgements` mapping"))
        for name, edit, message in cases:
            with self.subTest(case=name):
                self._judgements_copy(checked, edit)
                with self.assertRaisesRegex(self.m.Refused, message):
                    self.m.render_markdown(collected)
        for name, text, message in [("top level a list", "- judgements: {}\n", "has no `judgements` mapping"),
                                    ("does not parse", "judgements: [unclosed\n", "does not parse")]:
            with self.subTest(case=name):
                path = self.dir / f"judgements_raw_{name.replace(' ', '_')}.yaml"
                path.write_text(text, encoding="utf-8")
                checked["judgements"] = str(path)
                with self.assertRaisesRegex(self.m.Refused, message):
                    self.m.render_markdown(collected)
        self._judgements_copy(checked)                   # the control: an unspoiled copy renders
        self.assertIn("| record_self_narration | 47 | 3 | 0 |", self.m.render_markdown(collected))

    def test_the_committed_judgements_bear_out_the_v1_table(self):
        """#3197: one verdict and reason per drawn phrase, whose tally is the
        table; the three borderline phrases are the ranking-vocabulary ones
        the note describes."""
        v1 = lx.load(al.LEXICON, 1)
        checked = self.m.PRECISION[v1.sha256]
        data = self.m.read_judgements(v1.sha256, checked)
        rows = data["judgements"]
        self.assertEqual({cls: len(r) for cls, r in rows.items()}, {BWA: 50, RSN: 50})
        self.assertTrue(all(r["reason"].strip() for cls in rows for r in rows[cls]))
        borderline = [r for r in rows[RSN] if r["verdict"] == "borderline"]
        self.assertEqual([r["patterns"] for r in borderline], [["rsn.source-ranking"]] * 3)
        self.assertEqual(data["recorded"], "2026-09-29")
        self.assertIn("re-recorded", JUDGEMENTS.read_text(encoding="utf-8"))
        md = self.m.render_markdown(self._collect_v1())
        self.assertIn("Each phrase's verdict and reason are in `notes/absence_precision_judgements_99c92000.yaml`", md)
        self.assertIn("They are not the 2026-09-28 judgements", md)

    def test_a_table_its_judgements_do_not_bear_out_is_refused(self):
        """#3197: the table is rendered only beside judgements of the draw it
        names whose tally is its counts. Each spoiled copy is refused, and
        `main` then writes nothing and exits 1."""
        collected = self._collect_v1()
        checked = self.m.PRECISION[collected["lexicon"].sha256]

        def flip(data):                                  # an in-class phrase judged borderline
            data["judgements"][BWA][0]["verdict"] = "borderline"

        def drop(data):
            data["judgements"][RSN].pop()

        def move(data):
            data["judgements"][RSN][0]["pointer"] = "/notes/9"

        def swap(data):                                  # the same phrases in another order
            rows = data["judgements"][BWA]
            rows[0], rows[1] = rows[1], rows[0]

        def unreasoned(data):
            data["judgements"][RSN][4]["reason"] = "  "

        def unknown(data):
            data["judgements"][RSN][4]["verdict"] = "probably"

        def undated(data):
            del data["recorded"]

        for edit, message in [(flip, r"verdict tally .* is not the precision entry's counts"),
                              (drop, "its phrases are not the draw 99c92000a3c2"),
                              (move, "its phrases are not the draw"),
                              (swap, "its phrases are not the draw"),
                              (unreasoned, "needs record, pointer, start, end, a reason"),
                              (unknown, "a verdict from"),
                              (undated, "does not say when its verdicts were recorded")]:
            with self.subTest(edit=edit.__name__):
                self._judgements_copy(checked, edit)
                with self.assertRaisesRegex(self.m.Refused, message):
                    self.m.render_markdown(collected)
        self._judgements_copy(checked)                   # the control: an unspoiled copy renders
        self.assertIn("| record_self_narration | 47 | 3 | 0 |", self.m.render_markdown(collected))
        checked["classes"] = {BWA: (50, 0, 0), RSN: (48, 2, 0)}          # counts the verdicts do not give
        with self.assertRaisesRegex(self.m.Refused, "verdict tally"):
            self.m.render_markdown(collected)
        checked["classes"] = {BWA: (50, 0, 0), RSN: (47, 3, 0)}
        checked["judgements"] = str(self.dir / "absent.yaml")
        with self.assertRaisesRegex(self.m.Refused, "could not be read"):
            self.m.render_markdown(collected)
        del checked["judgements"]
        with self.assertRaisesRegex(self.m.Refused, "names no judgements file"):
            self.m.render_markdown(collected)
        self.m.collect = lambda *a, **k: collected       # main over the same records, without a real corpus
        self.m.read_pins = lambda *a, **k: {}
        self.m.unpinned = lambda *a, **k: []
        before = self._tree()
        status, out, err = self._run()
        self.assertEqual((status, out), (1, ""))
        self.assertIn("refused: the precision entry names no judgements file", err)
        self.assertEqual(self._tree(), before)

    def test_the_note_counts_under_its_named_version_and_names_later_ones(self):
        """#3132: registering a version does not move the note's counts; the
        note names the later ones and is stale until regenerated. Counting
        under another is a change of `LEXICON_VERSION`, and a precision table
        is shown only under the bytes it was checked under. Since #3791 the
        note counts under v4, the newest, so it names none."""
        self.assertEqual(self.m.LEXICON_VERSION, 4)
        collected = self.m.collect(self.corpus)
        v2, v3, v4 = (lx.load(al.LEXICON, v) for v in (2, 3, 4))
        self.assertEqual(collected["lexicon"].sha256, v4.sha256)
        md = self.m.render_markdown(collected)
        self.assertNotIn("Later versions", md)
        self.assertIn("| record_self_narration | 49 | 1 | 0 |", md)
        self.m.LEXICON_VERSION = 3
        md = self.m.render_markdown(self.m.collect(self.corpus))
        self.assertIn(f"- **Later versions:** v4 (`absence_self_narration_v4.yaml`, sha256 `{v4.sha256}`). "
                      "This note counts under v3", md)
        self.assertIn("| record_self_narration | 50 | 0 | 0 |", md)
        self.m.LEXICON_VERSION = 1
        under_v1 = self.m.collect(self.corpus)
        md = self.m.render_markdown(under_v1)
        self.assertIn(f"- **Later versions:** v2 (`absence_self_narration_v2.yaml`, sha256 `{v2.sha256}`); "
                      f"v3 (`absence_self_narration_v3.yaml`, sha256 `{v3.sha256}`); "
                      f"v4 (`absence_self_narration_v4.yaml`, sha256 `{v4.sha256}`). This note counts under v1", md)
        self.assertIn("| record_self_narration | 47 | 3 | 0 |", md)
        self.m.LEXICON_VERSION = 2
        under_v2 = self.m.collect(self.corpus)
        self.assertEqual(self.m.summarise(under_v2), self.m.summarise(under_v1))    # v2 changes no match
        md = self.m.render_markdown(under_v2)
        self.assertIn("No precision sample has been checked under this lexicon's sha256.", md)

    def test_v3_moves_only_the_source_ranking_counts(self):
        """#3520: over a record whose only ranking phrase is a source conflict,
        v2 counts it and v3 does not; a ranking phrase with a preference verb
        counts under both. The fixture corpus has no ranking phrase, so its
        v2 and v3 counts are equal."""
        self._write("m_e/label/S_d4d.yaml", {"source_caveats": "Publisher: two tier-1 sources disagree.",
                                              "notes": ["The higher-ranked source is preferred."]})
        under = {v: self.m.collect(self.corpus, lx.load(al.LEXICON, v)) for v in (2, 3)}
        counts = {v: self.m.summarise(c)["patterns"]["rsn.source-ranking"] for v, c in under.items()}
        self.assertEqual((counts[2]["matches"], counts[3]["matches"]), (2, 1))
        self.assertEqual((counts[2]["records"], counts[3]["records"]), (1, 1))
        hits = [h for r in under[3]["records"] if r["path"] == "m_e/label/S_d4d.yaml"
                for h in r["result"]["hits"]]
        self.assertEqual([(h["pointer"], h["text"]) for h in hits], [("/notes/0", "higher-ranked")])
        (self.corpus / "m_e/label/S_d4d.yaml").unlink()
        totals = {v: self.m.summarise(self.m.collect(self.corpus, lx.load(al.LEXICON, v)))["total"] for v in (2, 3)}
        self.assertEqual(totals[2], totals[3])

    def test_v4_moves_only_the_source_ranking_counts(self):
        """#3791: a ranking term whose verb is past a `;`, or past the `.` of
        "St." (#3792), counts under v4 and not under v3; one whose verb is in
        the next sentence counts under neither. The fixture corpus has no
        ranking phrase, so its v3 and v4 counts are equal."""
        self._write("m_e/label/S_d4d.yaml", {
            "source_caveats": ["The higher-ranked source gives 19 July 2023; that date is recorded here.",
                               "The higher-ranked source names Washington University in St. Louis as the "
                               "sponsor, and that name is used.",
                               "Two tier-1 sources disagree. Both values are recorded above."]})
        under = {v: self.m.collect(self.corpus, lx.load(al.LEXICON, v)) for v in (3, 4)}
        counts = {v: self.m.summarise(c)["patterns"]["rsn.source-ranking"] for v, c in under.items()}
        self.assertEqual((counts[3]["matches"], counts[4]["matches"]), (0, 2))
        hits = [(h["pointer"], h["text"]) for r in under[4]["records"] if r["path"] == "m_e/label/S_d4d.yaml"
                for h in r["result"]["hits"] if "rsn.source-ranking" in h["patterns"]]
        self.assertEqual(hits, [("/source_caveats/0", "higher-ranked"), ("/source_caveats/1", "higher-ranked")])
        (self.corpus / "m_e/label/S_d4d.yaml").unlink()
        totals = {v: self.m.summarise(self.m.collect(self.corpus, lx.load(al.LEXICON, v)))["total"] for v in (3, 4)}
        self.assertEqual(totals[3], totals[4])

    def test_the_committed_v3_judgements_bear_out_the_v3_table(self):
        """#3520: the v3 sample's verdicts are written down per phrase, its
        bundle_wide_absence phrases are v1's (no pattern of that class moved)
        with v1's verdicts, and none of its record_self_narration phrases is
        one of the three ranking-vocabulary conflicts v1's sample judged
        borderline."""
        v1, v3 = (lx.load(al.LEXICON, v) for v in (1, 3))
        checked = self.m.PRECISION[v3.sha256]
        data = self.m.read_judgements(v3.sha256, checked)
        rows = data["judgements"]
        self.assertEqual({cls: len(r) for cls, r in rows.items()}, {BWA: 50, RSN: 50})
        self.assertEqual((data["recorded"], checked["checked"]), ("2026-09-30", "2026-09-30"))
        old = self.m.read_judgements(v1.sha256, self.m.PRECISION[v1.sha256])["judgements"]
        self.assertEqual(rows[BWA], old[BWA])
        span = lambda r: (r["record"], r["pointer"], r["start"], r["end"])                      # noqa: E731
        borderline_v1 = {span(r) for r in old[RSN] if r["verdict"] == "borderline"}
        self.assertEqual(len(borderline_v1), 3)
        self.assertFalse(borderline_v1 & {span(r) for r in rows[RSN]})
        md = self.m.render_markdown(self.m.collect(self.corpus, v3))
        self.assertIn("`notes/absence_precision_judgements_bd0c63ed.yaml`, recorded\n2026-09-30 when the sample "
                      "was checked", md)
        self.assertNotIn("by reading this draw again", md)

    def test_the_committed_v4_judgements_bear_out_the_v4_table(self):
        """#3791: the v4 sample's verdicts are written down per phrase; its
        bundle_wide_absence phrases and verdicts are v3's (no pattern of that
        class moved), and its one borderline record_self_narration phrase is
        a name of the declared ranking, which v4 did not change (#3706)."""
        v3, v4 = (lx.load(al.LEXICON, v) for v in (3, 4))
        checked = self.m.PRECISION[v4.sha256]
        self.assertEqual(checked["classes"], {BWA: (50, 0, 0), RSN: (49, 1, 0)})
        data = self.m.read_judgements(v4.sha256, checked)
        rows = data["judgements"]
        self.assertEqual({cls: len(r) for cls, r in rows.items()}, {BWA: 50, RSN: 50})
        self.assertEqual((data["recorded"], checked["checked"]), ("2026-09-30", "2026-09-30"))
        old = self.m.read_judgements(v3.sha256, self.m.PRECISION[v3.sha256])["judgements"]
        self.assertEqual(rows[BWA], old[BWA])
        borderline = [r for r in rows[RSN] if r["verdict"] != "in_class"]
        self.assertEqual([(r["verdict"], r["patterns"], r["text"]) for r in borderline],
                         [("borderline", ["rsn.source-ranking"], "input manifest")])
        md = self.m.render_markdown(self.m.collect(self.corpus))
        self.assertIn("`notes/absence_precision_judgements_574f03c2.yaml`, recorded\n2026-09-30 when the sample "
                      "was checked", md)


@pytest.fixture(scope="module")
def committed():
    """The script and the committed pinned records, linted once for the
    corpus tests below."""
    m = _script()
    pins = m.read_pins(m.PINS)
    try:
        collected = m.collect(m.CORPUS, pins=pins)
    except m.Stale as exc:
        pytest.fail(f"{exc}: run scripts/absence_claims_baseline.py --repin")
    return m, pins, collected


@pytest.mark.corpus   # walks the committed corpus
def test_the_committed_baseline_is_what_its_pinned_records_reproduce(committed):
    """Fails only when a pinned record changed or is gone, or when the note
    does not match the pinned records. A record added since the pin is
    reported as a warning and not counted (#3045)."""
    m, pins, collected = committed
    assert collected["record_set_sha256"] in m.OUT_MD.read_text(encoding="utf-8")
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(collected), (
        "notes/absence_claims_baseline.md does not match its pinned records: run scripts/absence_claims_baseline.py")
    new = m.unpinned(m.CORPUS, pins)
    if new:
        warnings.warn(f"{len(new)} full record(s) are not in the absence baseline's pinned set and are not "
                      f"counted (reported, not stale), e.g. {new[:3]}; --repin counts them", stacklevel=1)


@pytest.mark.corpus   # walks the committed corpus
def test_the_committed_precision_sample_is_the_draw_it_names(committed):
    """#3173: the precision table names a seeded draw over the pinned records
    and its sha256; drawing it again from those records gives that sha256.
    Nothing to re-draw when the note counts a record set other than the one
    the sample was drawn from; the note says so itself."""
    m, _, collected = committed
    checked = m.PRECISION.get(collected["lexicon"].sha256)
    if checked is None:
        pytest.skip("no precision sample is recorded under the current lexicon's sha256")
    if checked["record_set_sha256"] != collected["record_set_sha256"]:
        pytest.skip("the precision sample was drawn from another record set")
    assert m.draw_sha256(m.draw(collected, checked["sample"], checked["seed"])) == checked["draw_sha256"], (
        "the seeded precision sample no longer draws the phrases it names")


if __name__ == "__main__":
    unittest.main()
