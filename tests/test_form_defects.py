"""Tests for the form-defect split.

Nothing here touches the network. The classifier is injected or run offline
against the committed cache, where a miss raises rather than billing.
"""

import json
import tempfile
import unittest
from pathlib import Path

from data_sheets_schema.agreement import OfflineCacheMiss, _digest
from data_sheets_schema.form_defects import (
    FORM_SUBTYPE_SYSTEM,
    SUBTYPES,
    FormFailure,
    FormSubtypeClassifier,
    _parse_subtype,
    attribute,
    load_form_failures,
    recorded_model,
    table,
)

REPO = Path(__file__).resolve().parents[1]
JUDGEMENTS = REPO / "data" / "evaluation_llm" / "judgement_cache"
SUBTYPE_CACHE = REPO / "data" / "evaluation_llm" / "form_subtype_cache"


class TestParseSubtype(unittest.TestCase):
    def test_bare_json(self):
        self.assertEqual(
            _parse_subtype('{"subtype": "hollow_object", "reason": "prose only"}'),
            ("hollow_object", "prose only"))

    def test_fenced_json(self):
        subtype, _ = _parse_subtype(
            '```json\n{"subtype": "collapsed_cardinality", "reason": "x"}\n```')
        self.assertEqual(subtype, "collapsed_cardinality")

    def test_truncated_is_salvaged(self):
        subtype, reason = _parse_subtype('{"subtype": "both", "reason": "clipped')
        self.assertEqual(subtype, "both")
        self.assertEqual(reason, "[truncated]")

    def test_an_unknown_label_is_rejected(self):
        with self.assertRaises(ValueError):
            _parse_subtype('{"subtype": "made_up", "reason": "x"}')

    def test_an_unreadable_answer_does_not_become_other(self):
        """`other` is a finding, not a bucket for the classifier's own failures.

        Defaulting a parse failure to `other` would let the residual category
        absorb errors — which is exactly how one `form` class came to hide two
        distinct defects.
        """
        with self.assertRaises(ValueError):
            _parse_subtype("I think this one is a bit of both, really.")


class TestClassifierCache(unittest.TestCase):
    def _failure(self):
        return FormFailure(project="CHORUS", slot="creators", value='[{"a": 1}]',
                           reason="collapsed", fitness=0.5)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            first = FormSubtypeClassifier(model="m", cache_path=path)
            first._save(self._failure().key, "creators", "hollow_object", "why")
            second = FormSubtypeClassifier(model="m", cache_path=path, offline=True)
            self.assertEqual(second(self._failure()), ("hollow_object", "why"))
            self.assertEqual(second.memo_hits, 1)

    def test_a_different_model_does_not_reuse_the_label(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            FormSubtypeClassifier(model="m1", cache_path=path)._save(
                self._failure().key, "creators", "hollow_object", "why")
            other = FormSubtypeClassifier(model="m2", cache_path=path, offline=True)
            with self.assertRaises(OfflineCacheMiss):
                other(self._failure())

    def test_a_different_rubric_does_not_reuse_the_label(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            path.write_text(json.dumps(
                {"rubric": "stale", "model": "m", "key": self._failure().key,
                 "slot": "creators", "subtype": "other", "reason": "old"}) + "\n")
            classifier = FormSubtypeClassifier(model="m", cache_path=path,
                                               offline=True)
            with self.assertRaises(OfflineCacheMiss):
                classifier(self._failure())

    def test_the_cache_records_the_cap_and_rubric(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "c.jsonl"
            FormSubtypeClassifier(model="m", cache_path=path)._save(
                "k", "creators", "both", "r")
            written = json.loads(path.read_text().splitlines()[0])
            self.assertEqual(written["rubric"], _digest(FORM_SUBTYPE_SYSTEM))
            self.assertIn("chars", written)


class TestTable(unittest.TestCase):
    def test_counts_by_subtype_and_config(self):
        rows = [
            (FormFailure("P", "s", "v1a", "", 0.5, config="v1"),
             "collapsed_cardinality", ""),
            (FormFailure("P", "s", "v2a", "", 0.5, config="v2"),
             "hollow_object", ""),
            (FormFailure("P", "s", "v2b", "", 0.5, config="v2"),
             "hollow_object", ""),
        ]
        counts = table(rows)
        self.assertEqual(counts["collapsed_cardinality"], {"v1": 1})
        self.assertEqual(counts["hollow_object"], {"v2": 2})
        self.assertEqual(counts["both"], {})

    def test_every_subtype_has_a_row_even_at_zero(self):
        """A missing row and a zero row read differently."""
        counts = table([])
        self.assertEqual(set(counts), set(SUBTYPES))


@unittest.skipUnless(JUDGEMENTS.exists(), "judgement cache not present")
class TestAgainstTheRealCache(unittest.TestCase):
    def test_the_form_failures_are_the_two_arms_exactly(self):
        """50 v1 + 56 v2 = the 106 in the cache, with nothing unattributed.

        Attribution matches the stored value back against the records, since
        the fitness cache keeps no run label. If it ever stops being exact the
        two arms are being mixed, which is the error this module exists to undo.
        """
        failures = attribute(load_form_failures(JUDGEMENTS))
        counts = {}
        for failure in failures:
            counts[failure.config] = counts.get(failure.config, 0) + 1
        self.assertEqual(counts, {"v1": 50, "v2": 56})
        self.assertEqual(len(failures), 106)

    def test_the_real_cache_holds_exactly_one_rubric_and_model(self):
        """#277 — the premise this module rests on, asserted.

        The whole design is "do not re-judge fitness, classify what is already
        cached". That is only sound while the cache holds one instrument.
        """
        import json
        rubrics, models = set(), set()
        for path in JUDGEMENTS.glob("*_fitness.jsonl"):
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get("failure") == "form":
                    rubrics.add(entry.get("rubric", ""))
                    models.add(entry.get("model", ""))
        self.assertEqual(len(rubrics), 1, f"fitness rubrics: {sorted(rubrics)}")
        self.assertEqual(len(models), 1, f"fitness models: {sorted(models)}")

    def test_a_mixed_cache_is_refused_rather_than_pooled(self):
        """Loudly, not by filtering — a silent skip could halve the corpus
        and still produce a plausible table."""
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "X_fitness.jsonl"
            base = {"failure": "form", "slot": "creators", "value": "[]",
                    "reason": "r", "fitness": 0.5, "model": "m"}
            path.write_text(
                json.dumps({**base, "rubric": "a"}) + "\n"
                + json.dumps({**base, "rubric": "b"}) + "\n")
            with self.assertRaises(ValueError) as ctx:
                load_form_failures(Path(d))
            self.assertIn("rubric", str(ctx.exception))

    def test_no_value_reaches_the_truncation_cap(self):
        from data_sheets_schema.form_defects import VALUE_CHARS
        longest = max(len(f.value) for f in load_form_failures(JUDGEMENTS))
        self.assertLess(longest, VALUE_CHARS,
                        "a value now exceeds the cap; the classifier would be "
                        "judging a prefix (see #244)")


@unittest.skipUnless((SUBTYPE_CACHE / "form_subtypes.jsonl").exists(),
                     "subtype cache not present")
class TestTheSplitResult(unittest.TestCase):
    """The finding, pinned.

    The point of splitting `form` was that one class hid two defects moving in
    opposite directions. That is now a measured claim rather than a paragraph,
    and it should fail loudly if a re-run ever contradicts it.
    """

    def _classified(self):
        failures = attribute(load_form_failures(JUDGEMENTS))
        # The recorded instrument, not the live config pin (#351): the pin
        # moved once (#345) and every model-scoped cached subtype fell out of
        # scope, failing this offline rebuild of a frozen finding.
        cache = SUBTYPE_CACHE / "form_subtypes.jsonl"
        classifier = FormSubtypeClassifier(
            model=recorded_model(cache), cache_path=cache, offline=True)
        return [(f, *classifier(f)) for f in failures]

    def test_collapsed_cardinality_all_but_disappears_under_v2(self):
        counts = table(self._classified())
        present_v1 = (counts["collapsed_cardinality"].get("v1", 0)
                      + counts["both"].get("v1", 0))
        present_v2 = (counts["collapsed_cardinality"].get("v2", 0)
                      + counts["both"].get("v2", 0))
        self.assertGreater(present_v1, 30)
        self.assertLess(present_v2, 10)

    def test_hollow_objects_replace_them(self):
        counts = table(self._classified())
        present_v1 = counts["hollow_object"].get("v1", 0) + counts["both"].get("v1", 0)
        present_v2 = counts["hollow_object"].get("v2", 0) + counts["both"].get("v2", 0)
        self.assertLess(present_v1, 15)
        self.assertGreater(present_v2, 40)

    def test_the_totals_still_match_the_published_form_counts(self):
        """The split must partition the same 50/56, not re-measure them."""
        counts = table(self._classified())
        for config, expected in (("v1", 50), ("v2", 56)):
            total = sum(counts[s].get(config, 0) for s in SUBTYPES)
            self.assertEqual(total, expected, config)


if __name__ == "__main__":
    unittest.main()
