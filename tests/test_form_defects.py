"""Tests for the form-defect split.

Nothing here touches the network. The classifier is injected or run offline
against the committed cache, where a miss raises rather than billing.
"""

import json
import tempfile
import unittest

import yaml
from pathlib import Path

from data_sheets_schema.agreement import OfflineCacheMiss, _digest
from data_sheets_schema.form_defects import (
    FOLDED_SUBTYPES,
    FORM_SUBTYPE_SYSTEM,
    SUBTYPES,
    FormFailure,
    FormSubtypeClassifier,
    PooledInstruments,
    _parse_subtype,
    _value_index,
    attribute,
    classify,
    folded,
    load_form_failures,
    main,
    recorded_model,
    recorded_models,
    table,
)

from data_sheets_schema.constants import PROJECTS

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


class TestIndexCoversEveryProject(unittest.TestCase):
    """A project the index never opens becomes an `unattributed` column (#463).

    `attribute` assigns `config = ""` to any value it cannot match, and nothing
    distinguishes "this value came from a project we did not look at" from
    "this value matched no record". VOICE_PEDIATRIC was missing from a
    hardcoded literal from #298 onward and stayed quiet only because nothing
    from it had been fitness-scored yet.
    """

    def _corpus(self, root, project, slot, value, label="lbl", rep=1):
        """One record on disk, in the layout load_replicates expects."""
        d = root / "claudecode_agent" / f"{label}_rep{rep}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{project}_d4d.yaml").write_text(
            yaml.safe_dump({slot: value}), encoding="utf-8")

    def test_a_value_from_every_registered_project_is_attributed(self):
        """Behavioural: index a record per project, attribute a failure from each.

        The earlier version of this test compared `_value_index`'s default
        argument against PROJECTS, which would pass unchanged if the function
        ignored the argument entirely.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, project in enumerate(PROJECTS):
                self._corpus(root, project, "creators", [f"value-{i}"])

            failures = [FormFailure(project, "creators",
                                    json.dumps([f"value-{i}"]), "", 0.5)
                        for i, project in enumerate(PROJECTS)]
            attribute(failures, root=root, configs={"v1": "lbl"})

            unattributed = [f.project for f in failures if not f.config]
            self.assertEqual(unattributed, [],
                             "a registered project was not indexed")

    def test_voice_pediatric_specifically_attributes(self):
        """The project the hardcoded literal actually omitted (#463)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._corpus(root, "VOICE_PEDIATRIC", "creators", ["pediatric"])
            failure = FormFailure("VOICE_PEDIATRIC", "creators",
                                  json.dumps(["pediatric"]), "", 0.5)
            attribute([failure], root=root, configs={"v1": "lbl"})
            self.assertEqual(failure.config, "v1")

    def test_a_project_left_out_of_the_list_goes_unattributed(self):
        """The failure mode itself, so the guard is known to be able to fire."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._corpus(root, "VOICE_PEDIATRIC", "creators", ["pediatric"])
            index = _value_index(root, "claudecode_agent", {"v1": "lbl"},
                                 projects=("AI_READI",))
            self.assertEqual(index, {})


class TestDefaultInstrument(unittest.TestCase):
    """The cache names the instrument; the live config pin does not (#462).

    The pin moved from `google/claude-opus-5-high` to `claude-opus-5` and every
    model-scoped entry fell out of scope at once — 106 of 106 cached labels
    invisible, an offline rebuild broken, and an online rebuild about to append
    a second instrument to the same file.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "subtypes.jsonl"
        self.addCleanup(self.tmp.cleanup)

    def _write(self, model, key="k1"):
        self.path.write_text(json.dumps({
            "rubric": _digest(FORM_SUBTYPE_SYSTEM), "model": model,
            "chars": 4000, "key": key, "slot": "s",
            "subtype": "hollow_object", "reason": ""}) + "\n", encoding="utf-8")

    def test_the_recorded_instrument_wins_over_the_live_pin(self):
        self._write("google/claude-opus-5-high")
        classifier = FormSubtypeClassifier(cache_path=self.path, offline=True)
        self.assertEqual(classifier.model, "google/claude-opus-5-high")

    def test_the_entries_are_actually_loaded(self):
        """The model resolving right is only useful if the memo fills."""
        self._write("google/claude-opus-5-high")
        classifier = FormSubtypeClassifier(cache_path=self.path, offline=True)
        self.assertEqual(len(classifier._memo), 1)

    def test_an_explicit_model_still_overrides(self):
        """Re-classifying under a new instrument stays possible, and stated."""
        self._write("google/claude-opus-5-high")
        classifier = FormSubtypeClassifier(cache_path=self.path,
                                           model="claude-opus-5", offline=True)
        self.assertEqual(classifier.model, "claude-opus-5")
        self.assertEqual(len(classifier._memo), 0)

    def test_a_missing_cache_falls_back_to_the_pin(self):
        """Nothing recorded means nothing to reproduce; the pin is all there is."""
        classifier = FormSubtypeClassifier(
            cache_path=Path(self.tmp.name) / "absent.jsonl", offline=True)
        self.assertIsInstance(classifier.model, str)
        self.assertTrue(classifier.model)

    def _pool(self):
        self.path.write_text("\n".join(
            json.dumps({"rubric": _digest(FORM_SUBTYPE_SYSTEM), "model": m,
                        "chars": 4000, "key": f"k{i}", "slot": "s",
                        "subtype": "other", "reason": ""})
            for i, m in enumerate(["a-model", "b-model"])) + "\n",
            encoding="utf-8")

    def test_a_pooled_cache_refuses_rather_than_choosing(self):
        """Falling back to the pin here reports a partial table as whole (#464).

        An earlier version asserted that construction *succeeded* on a pooled
        cache, on the reasoning that `recorded_model` would surface the error
        where it is explained. Nothing on the production path calls
        `recorded_model`, so that reasoning encoded the defect as the expected
        behaviour: the run would load only the entries matching whichever model
        the live pin happened to name, and print their counts as the table.
        """
        self._pool()
        with self.assertRaises(PooledInstruments):
            FormSubtypeClassifier(cache_path=self.path, offline=True).model

    def test_an_explicit_model_still_works_on_a_pooled_cache(self):
        """Refusal is about *choosing* an instrument, not about using a named one.

        Someone repairing a pooled cache has to be able to address one arm of
        it; what they may not do is have the tool pick for them.
        """
        self._pool()
        classifier = FormSubtypeClassifier(cache_path=self.path,
                                           model="a-model", offline=True)
        self.assertEqual(classifier.model, "a-model")
        self.assertEqual(len(classifier._memo), 1)

    def test_recorded_models_reports_every_instrument(self):
        self._pool()
        self.assertEqual(recorded_models(self.path), {"a-model", "b-model"})

    def test_main_refuses_to_pool_a_second_instrument(self):
        """--model on a cache recording another must not silently append (#464).

        The write is what does the damage: once two models are in one file,
        `recorded_model` refuses it and the published table stops being
        reproducible. Checked before any judgement work, so the refusal costs
        nothing and cannot half-write.
        """
        self._write("a-model")
        code = main(["--cache", str(self.path), "--model", "b-model",
                     "--judgement-cache", str(Path(self.tmp.name) / "none")])
        self.assertEqual(code, 2)
        self.assertEqual(recorded_models(self.path), {"a-model"})

    def test_main_allows_pooling_when_it_is_stated(self):
        """The escape hatch exists; it just has to be asked for."""
        self._write("a-model")
        code = main(["--cache", str(self.path), "--model", "b-model",
                     "--allow-pooled-cache",
                     "--judgement-cache", str(Path(self.tmp.name) / "none")])
        self.assertNotEqual(code, 2)

    def test_main_does_not_refuse_the_model_already_recorded(self):
        """Naming the instrument the cache already holds is not pooling."""
        self._write("a-model")
        code = main(["--cache", str(self.path), "--model", "a-model",
                     "--judgement-cache", str(Path(self.tmp.name) / "none")])
        self.assertNotEqual(code, 2)

    def test_pooled_instruments_is_a_value_error(self):
        """Existing `except ValueError` handlers keep working."""
        self._pool()
        with self.assertRaises(ValueError):
            recorded_model(self.path)


class TestFolded(unittest.TestCase):
    """`both` counts toward each named subtype — the reporting convention.

    It lived only in the prose of `notes/form_defect_split_2026-08-03.md`, so an
    arm counted from the raw table compared against a baseline short by the
    whole `both` bucket (#461).
    """

    def test_both_counts_toward_each_named_subtype(self):
        counts = {
            "collapsed_cardinality": {"v1": 34, "v2": 2},
            "hollow_object": {"v1": 0, "v2": 45},
            "both": {"v1": 8, "v2": 5},
            "other": {"v1": 8, "v2": 4},
        }
        merged = folded(counts)
        self.assertEqual(merged["collapsed_cardinality"], {"v1": 42, "v2": 7})
        self.assertEqual(merged["hollow_object"], {"v1": 8, "v2": 50})

    def test_the_published_headline_figures_are_reproduced(self):
        """42 -> 7 and 8 -> 50 are what the note reports; pin them to the code.

        Neither figure appears in either of the note's own tables, because both
        fold `both` in. Anyone re-deriving them from the raw table gets 34 -> 2
        and 0 -> 45 and a comparison wrong by the size of that bucket.
        """
        counts = {
            "collapsed_cardinality": {"v1": 34, "v2": 2},
            "hollow_object": {"v1": 0, "v2": 45},
            "both": {"v1": 8, "v2": 5},
            "other": {"v1": 8, "v2": 4},
        }
        merged = folded(counts)
        self.assertEqual(
            (merged["collapsed_cardinality"]["v1"],
             merged["collapsed_cardinality"]["v2"]), (42, 7))
        self.assertEqual(
            (merged["hollow_object"]["v1"], merged["hollow_object"]["v2"]),
            (8, 50))

    def test_folded_subtypes_may_exceed_the_total(self):
        """A `both` value exhibits each defect, so it is counted twice on purpose.

        Asserted rather than left implicit: a reader who checks the folded rows
        against the total and finds them larger should find that documented as
        intent, not discover it as a suspected double-count.
        """
        counts = {
            "collapsed_cardinality": {"v1": 1},
            "hollow_object": {"v1": 1},
            "both": {"v1": 10},
            "other": {"v1": 0},
        }
        merged = folded(counts)
        total = sum(v.get("v1", 0) for v in counts.values())
        folded_sum = sum(merged[s].get("v1", 0) for s in FOLDED_SUBTYPES)
        self.assertEqual(total, 12)
        self.assertEqual(folded_sum, 22)
        self.assertGreater(folded_sum, total)

    def test_a_missing_both_bucket_is_not_an_error(self):
        merged = folded({"collapsed_cardinality": {"v1": 3},
                         "hollow_object": {"v1": 1}})
        self.assertEqual(merged["collapsed_cardinality"], {"v1": 3})
        self.assertEqual(merged["hollow_object"], {"v1": 1})

    def test_folding_does_not_mutate_the_raw_counts(self):
        """The raw table stays reportable — `both` is a real classification."""
        counts = {
            "collapsed_cardinality": {"v1": 34},
            "hollow_object": {"v1": 0},
            "both": {"v1": 8},
            "other": {"v1": 8},
        }
        folded(counts)
        self.assertEqual(counts["collapsed_cardinality"], {"v1": 34})
        self.assertEqual(counts["both"], {"v1": 8})


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

    def test_the_published_split_rebuilds_offline_at_zero_cost(self):
        """The v1->v2 table reproduces from cache, with no paid call (#462).

        This is the property that broke: the classifier resolved the live pin
        rather than the instrument the cache records, so all 106 labels were
        invisible and this rebuild raised OfflineCacheMiss. It asserts the two
        published headline figures as well as the raw table, because the
        headlines fold the `both` bucket and nothing else pins them (#461).
        """
        cache = SUBTYPE_CACHE / "form_subtypes.jsonl"
        if not cache.exists():
            self.skipTest("subtype cache not present")
        classifier = FormSubtypeClassifier(cache_path=cache, offline=True)
        classified = classify(attribute(load_form_failures(JUDGEMENTS)),
                              classifier)
        self.assertEqual(classifier.calls, 0, "an offline rebuild paid for a call")

        # A config with no failures of a subtype is absent from the row rather
        # than present at 0 — table() counts, it does not tabulate a grid — so
        # read through .get the way the report does.
        def cell(rows, subtype, config):
            return rows[subtype].get(config, 0)

        counts = table(classified)
        self.assertEqual(
            [cell(counts, s, c) for s in SUBTYPES for c in ("v1", "v2")],
            [34, 2, 0, 45, 8, 5, 8, 4])

        merged = folded(counts)
        self.assertEqual(
            [cell(merged, s, c) for s in FOLDED_SUBTYPES for c in ("v1", "v2")],
            [42, 7, 8, 50])

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
