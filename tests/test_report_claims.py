"""Reconciliation-report claims, checked against the record and the schema.

Why this exists (#546): a reconciliation report is the audit trail a reviewer
reads *instead of* diffing YAML, and nothing checked it against anything. In
the 2026-08-13 v4 arm, every record that emitted a `distributions` block — 9 of
12 — reported having removed it, justified by the claim that `distributions` is
not declared. It is, with range `CoreDistribution`, and the blocks are still on
disk.

Most of these tests are about **precision**, because the first version of the
checker produced 122 findings across those 12 reports and most were wrong. A
checker whose output a reader learns to ignore is how the reports got into this
state.
"""

import unittest
from pathlib import Path

import yaml

from data_sheets_schema.report_claims import check_report, resolve

#: Real membership, not a convenient one (#1090). `distributions` is declared
#: on `CoreDataset` **only** — that is #546's whole premise, and a fixture
#: putting it on `Dataset` as well makes every core-versus-full assertion
#: below pass under either reading. It did: with `distributions` on both, the
#: #1087 regression test caught the defect through its `scope` string alone
#: and its finding-level assertion was vacuous.
import data_sheets_schema.report_claims as rc

DECLARED = {"Dataset": {"file_collections", "keywords", "source_caveats",
                        "notes", "conforms_to", "errata",
                        "collection_timeframes"},
            "CoreDataset": {"distributions", "source_caveats", "notes",
                            "errata", "collection_timeframes", "keywords",
                            "conforms_to"},
            "CoreDistribution": {"path", "md5", "format", "media_type",
                                 "source_caveats", "notes", "conforms_to"}}


class Harness(unittest.TestCase):
    def check(self, markdown, full=None, core=None):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "r.md"
        path.write_text(markdown, encoding="utf-8")
        return check_report(path, full or {}, core or {}, DECLARED)

    def kinds(self, markdown, **kw):
        return [(f["kind"], f["slot"]) for f in self.check(markdown, **kw)["findings"]]


class RemovalClaimTest(Harness):

    CORE = {"distributions": [{"path": "a"}, {"path": "b"}]}

    def test_action_line_naming_its_subject(self):
        md = ("### 2.1 `distributions`\n\n**Action:** the `distributions` "
              "block was removed from the core record in its entirety.\n")
        self.assertEqual(self.kinds(md, core=self.CORE),
                         [("removal_not_performed", "distributions")])

    def test_bare_subject_takes_the_slot_from_its_heading(self):
        """"the block was removed" names nothing; the heading above does.

        AI_READI rep1 is written this way. A version that read only the
        sentence reported nothing for it while the ten-entry block sat in the
        record.
        """
        md = ("### 2.1 Core `distributions` slot not in the schema\n\n"
              "**Resolution:** the block was removed. Its content was "
              "redistributed to slots that do exist.\n")
        # Two findings, both true: the heading asserts the slot is not in the
        # schema, which is the false premise the removal was reasoned from.
        self.assertEqual(sorted(self.kinds(md, core=self.CORE)),
                         [("false_schema_claim", "distributions"),
                          ("removal_not_performed", "distributions")])

    def test_table_row_with_the_change_cell_anywhere(self):
        """One report writes `| core | \\`distributions\\` | removed; … |`.

        The change cell is found, not assumed to be column 1.
        """
        md = ("| record | slot | change |\n|---|---|---|\n"
              "| core | `distributions` | removed; content moved |\n")
        self.assertEqual(self.kinds(md, core=self.CORE),
                         [("removal_not_performed", "distributions")])

    def test_a_true_removal_is_not_reported(self):
        md = "**Action:** the `distributions` block was removed.\n"
        self.assertEqual(self.kinds(md, core={"notes": "x"}), [])

    def test_an_emptied_slot_counts_as_removed(self):
        """`distributions: []` is not a two-entry block; calling that a false
        claim would be pedantry that buries the real finding."""
        md = "**Action:** the `distributions` block was removed.\n"
        self.assertEqual(self.kinds(md, core={"distributions": []}), [])


class PrecisionTest(Harness):
    """Each of these was a real false positive on the v4 reports."""

    def test_negation_is_not_a_removal(self):
        md = ("### `subsets`\n\n**Action:** a cross-referencing note was added "
              "to each so they cannot silently diverge; neither was deleted.\n")
        self.assertEqual(self.kinds(md, core={"subsets": [1]}), [])

    def test_content_removed_from_a_slot_is_not_the_slot(self):
        """"the citation prose removed from core `notes`" removes prose."""
        md = "**Action:** the citation prose was removed from core `notes`.\n"
        self.assertEqual(self.kinds(md, core={"notes": "kept"}), [])

    def test_a_claim_inside_a_slot_is_not_the_slot(self):
        """VOICE rep1: "the unfounded `source_caveats` claim was removed"."""
        md = ("**Action:** the structured amounts are recorded, and the "
              "unfounded `source_caveats` claim was removed.\n")
        self.assertEqual(self.kinds(md, core={"source_caveats": "kept"}), [])

    def test_a_slot_named_after_the_verb_is_not_the_subject(self):
        """VOICE rep1: the named slot is the one that survived."""
        md = ("### `file_collections`\n\n**Action:** the block was removed. "
              "Its content was already represented by the declared "
              "`distributions` slot, which was retained and left unchanged.\n")
        self.assertEqual(self.kinds(md, core={"distributions": [1]}), [])

    def test_a_slot_named_three_sentences_earlier_is_not_the_subject(self):
        """AI_READI rep1: reading the whole paragraph made `id` a subject."""
        md = ("**Action:** `id` is now `https://ror.org/01yc7t268`. That is "
              "the registered identifier. The minted URN was removed.\n")
        self.assertEqual(self.kinds(md, core={"id": "x"}), [])

    def test_a_field_of_a_slot_is_not_the_slot(self):
        """CM4AI rep2: "`collection_timeframes` dates | **Removed**"."""
        md = ("| n | sev | slot | change |\n|---|---|---|---|\n"
              "| 22 | low | `collection_timeframes` dates | **Removed** |\n")
        self.assertEqual(self.kinds(md, core={"collection_timeframes": [1]}), [])

    def test_removed_from_a_slot_in_a_table_cell(self):
        """CM4AI rep2: "Dataverse Subject in `keywords` | **Removed**"."""
        md = ("| n | slot | change |\n|---|---|---|\n"
              "| 23 | Dataverse Subject in `keywords` | **Removed** |\n")
        self.assertEqual(self.kinds(md, core={"keywords": [1, 2]}), [])

    def test_an_indexed_element_is_not_checked_by_index(self):
        """VOICE rep1 folded one `Erratum` into another.

        Removing an element renumbers the rest, so `errata[0]` afterwards is
        the object that survived. Skipped and counted, not guessed at.
        """
        md = ("#### (d) `errata[0]` removed\n\n**Action:** the object was "
              "dropped. Its remark was folded into the surviving object.\n")
        out = self.check(md, core={"errata": [{"erratum_details": "kept"}]})
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["claims_unnamed"], 1,
                         "skipped claims are counted, not silently dropped")

    def test_unnamed_claims_are_counted(self):
        md = "**Action:** the four MuSIC-pipeline objects were removed.\n"
        out = self.check(md)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["claims_unnamed"], 1)


class BothRecordsTest(Harness):
    """A claim naming both records must be checked against both (#578).

    `_target` returned `either` for a claim that named no record *and* for one
    that named both, and `either` was read against core alone. So "removed from
    the full and core records" passed when core removed it and full did not —
    the direction #566 exists to catch.
    """

    MD = ("**Action:** the `distributions` block was removed from the full "
          "record and the core record.\n")

    def test_survival_in_full_alone_is_reported(self):
        self.assertEqual(
            self.kinds(self.MD, full={"distributions": [1, 2]}, core={}),
            [("removal_not_performed", "distributions")])

    def test_survival_in_core_alone_is_reported(self):
        self.assertEqual(
            self.kinds(self.MD, full={}, core={"distributions": [1]}),
            [("removal_not_performed", "distributions")])

    def test_a_removal_from_both_passes(self):
        self.assertEqual(self.kinds(self.MD, full={}, core={}), [])


class SchemaClaimTest(Harness):

    def test_a_slot_said_not_to_exist_but_declared(self):
        md = ("**Finding:** the core record carried a `distributions` block. "
              "No such slot exists in the `CoreDataset` inventory.\n")
        self.assertEqual(self.kinds(md),
                         [("false_schema_claim", "distributions")])

    def test_the_subject_is_the_slot_not_the_attribution(self):
        """VOICE rep1 correctly attributes `path` to `FileCollection`.

        Flagging the names that follow the phrase made the checker contradict
        a sentence that was right.
        """
        md = ("The core record carried a `distributions` block. This slot is "
              "not declared on `CoreDataset`, and the key set is a hybrid of "
              "`FileCollection` (`path`) and `DistributionFormat` "
              "(`format`, `media_type`).\n")
        self.assertEqual(self.kinds(md),
                         [("false_schema_claim", "distributions")])

    def test_keys_said_not_to_be_attested(self):
        """CM4AI rep3 names `md5` and `path`; both are `CoreDistribution`."""
        md = ("No such slot appears in the inventory for `Dataset`, and `md5` "
              "and `path` are not attested keys on any listed range class.\n")
        self.assertEqual(sorted(self.kinds(md)),
                         [("false_schema_claim", "md5"),
                          ("false_schema_claim", "path")])

    def test_an_element_removal_is_not_tested_as_a_slot_removal(self):
        """#782: the 2026-08-28c AI_READI report's two findings."""
        md = ("## `sensitive_elements`\n\n**Action:** `description` was removed from all eleven objects. "
              "The content was redistributed into declared fields.\n\n"
              "**Action:** The second object was removed. The single remaining object asserts `false`.\n")
        core = {"sensitive_elements": [{"description": "x"}], "description": "top"}
        self.assertEqual(self.kinds(md, core=core), [])
        # the same shape with a root slot really claimed removed is still caught
        md2 = "## `distributions`\n\n**Action:** The `distributions` block was removed from the core record.\n"
        self.assertEqual(self.kinds(md2, core={"distributions": [{"id": "d"}]}), [("removal_not_performed", "distributions")])

    def test_prose_about_a_value_not_appearing_is_not_a_schema_claim(self):
        """#757: the v7 API canary's only report finding. The sentence is
        about a value, and the previous sentence's slot must not be borrowed
        as its subject when it has no demonstrative."""
        md = ("- **The leadership roster was removed from `description`** in both "
              "records. The final sentence of the original description (\"The team "
              "comprises A. B (X).\") does not appear in the reconciled description.\n")
        self.assertEqual(self.kinds(md), [])
        md2 = ("The core record carried a `distributions` block. This slot does not "
               "appear in the `CoreDataset` inventory.\n")
        self.assertEqual(self.kinds(md2), [("false_schema_claim", "distributions")])
        # the guard itself: the phrase matches, the sentence has no backticked
        # subject and no demonstrative, so the previous slot is not borrowed
        md3 = ("The core record carried a `distributions` block. Nothing of that kind "
               "does not appear in the supplied schema digest, of course.\n")
        self.assertEqual(self.kinds(md3), [])
        # #760: the corpus's true positives carry an adjective run before the noun
        for md in ("`distributions` does not appear in the supplied schema digest.\n",
                   "It carried a `distributions` block that does not appear in the supplied slot inventory.\n",
                   "`distributions` does not appear in the supplied 98-slot inventory.\n"):
            self.assertEqual(self.kinds(md), [("false_schema_claim", "distributions")], md)

    def test_a_true_absence_claim_is_not_reported(self):
        md = "**Finding:** `invented_slot` is not declared on `CoreDataset`.\n"
        self.assertEqual(self.kinds(md), [])

    def test_a_dotted_claim_is_not_answered_by_its_root(self):
        """`distributions.bogus` is not `distributions` (#578).

        Resolving a dotted path to its root contradicted a report that was
        right, because the root exists. Checking it properly needs the range
        class of the parent slot, which this does not resolve — so it is
        skipped rather than guessed at, and a true claim is left alone.
        """
        md = ("**Finding:** `distributions.bogus` is not declared on "
              "`CoreDistribution`.\n")
        self.assertEqual(self.kinds(md), [])


class ResolveTest(unittest.TestCase):

    def test_dotted_and_indexed(self):
        d = {"instances": [{"counts": 3}]}
        self.assertEqual(resolve(d, "instances[0].counts"), (True, 3))
        self.assertEqual(resolve(d, "instances[1].counts")[0], False)
        self.assertEqual(resolve(d, "instances[0].missing")[0], False)

    def test_star_means_any_element(self):
        """`creators[*].affiliations` survives if any creator has one."""
        d = {"creators": [{"name": "a"}, {"name": "b", "affiliations": ["x"]}]}
        self.assertEqual(resolve(d, "creators[*].affiliations"), (True, ["x"]))
        self.assertEqual(resolve(d, "creators[*].orcid")[0], False)


class CorpusTest(unittest.TestCase):
    """The finding itself, pinned against the records it came from."""

    BASE = Path("data/d4d_concatenated")
    LABELS = [f"2026-08-13_claude-opus-5-api-generic-v4_rep{r}"
              for r in (1, 2, 3)]

    def test_every_record_with_a_distributions_block_claims_it_removed(self):
        from data_sheets_schema.report_claims import declared_slots
        declared = declared_slots()
        retained, claimed = [], []
        for label in self.LABELS:
            core_dir = self.BASE / "claudecode_agent_core" / label
            full_dir = self.BASE / "claudecode_agent" / label
            if not core_dir.exists():
                self.skipTest("v4 arm not present in this checkout")
            for proj in ("AI_READI", "CHORUS", "CM4AI", "VOICE"):
                core_p = core_dir / f"{proj}_d4d_core.yaml"
                report = core_dir / f"{proj}_reconciliation.md"
                if not (core_p.exists() and report.exists()):
                    continue
                core = yaml.safe_load(core_p.read_text(encoding="utf-8")) or {}
                if not core.get("distributions"):
                    continue
                retained.append(f"{proj}_{label[-4:]}")
                full_p = full_dir / f"{proj}_d4d.yaml"
                full = yaml.safe_load(full_p.read_text(encoding="utf-8")) \
                    if full_p.exists() else {}
                out = check_report(report, full or {}, core, declared)
                if any(f["kind"] == "removal_not_performed"
                       and f["slot"].startswith("distributions")
                       for f in out["findings"]):
                    claimed.append(f"{proj}_{label[-4:]}")
        self.assertEqual(len(retained), 9,
                         "9 of the 12 v4 records emitted a distributions block")
        self.assertEqual(sorted(claimed), sorted(retained),
                         "every one of them reports having removed it")


class ScopedSchemaClaimTest(Harness):
    """A schema claim that names its own inventory is checked against it
    (#1022, #1046, #1087).

    The two slots below carry the whole distinction, and each is declared in
    exactly one place, so no assertion here passes under both readings
    (#1090):

    - `file_collections` — `Dataset` only, so "not in the core schema" is
      true and "not in the full schema" is false;
    - `distributions` — `CoreDataset` only, which is #546's premise, so the
      two are reversed.

    The shape the v8 report instruction produces is "not declared by the core
    schema and appears only in the full record". Resolving that against every
    class made true sentences into findings and had two reports rewritten
    over them.
    """

    def test_a_core_scoped_claim_is_checked_against_the_core_classes(self):
        md = ("`file_collections` is not declared by the core schema and "
              "appears only in the full record.\n")
        self.assertEqual(self.kinds(md), [])

    def test_a_core_scoped_claim_that_is_false_is_still_caught(self):
        """`distributions` is on CoreDataset, so this one is wrong."""
        md = "`distributions` is not declared in the core schema.\n"
        self.assertEqual(self.kinds(md), [("false_schema_claim", "distributions")])

    def test_a_full_scoped_claim_is_checked_against_dataset(self):
        """`distributions` is on CoreDataset only, so a claim about the full
        schema is true and a claim against every class would be false."""
        md = "`distributions` is not declared on the full schema.\n"
        self.assertEqual(self.kinds(md), [])

    def test_a_full_scoped_claim_that_is_false_is_still_caught(self):
        md = "`file_collections` is not declared in the full schema.\n"
        self.assertEqual(self.kinds(md),
                         [("false_schema_claim", "file_collections")])

    def test_an_unscoped_claim_is_unchanged(self):
        """The v2 reading, kept: with no scope named, any class holding the
        slot contradicts the claim."""
        md = "`file_collections` is not a declared slot.\n"
        self.assertEqual(self.kinds(md),
                         [("false_schema_claim", "file_collections")])

    def test_naming_both_scopes_reads_as_the_core_one(self):
        """The full mention is where the slot *is* — the clause's own
        contrast — not a second inventory to check the claim against."""
        md = ("`file_collections` is not declared by the core schema and "
              "appears only in the full record, which declares it on "
              "`Dataset`.\n")
        self.assertEqual(self.kinds(md), [])

    def test_the_scope_noun_is_not_only_the_word_schema(self):
        """VOICE 04f rep1 wrote "Not declared in the core projection." The
        reports vary the noun; the qualifier is what carries the scope."""
        for noun in ("projection", "record", "inventory", "view"):
            with self.subTest(noun=noun):
                md = f"`file_collections` is not declared in the core {noun}.\n"
                self.assertEqual(self.kinds(md), [])

    def test_a_claim_ranging_over_every_class_is_not_scoped_by_one_it_names(self):
        """CM4AI rep3's sentence names `Dataset` in its first half and then
        claims two keys are unattested "on any listed range class"; that half
        is about all of them."""
        md = ("No such slot appears in the inventory for `Dataset`, and "
              "`md5` and `path` are not attested keys on any listed range "
              "class.\n")
        self.assertEqual(sorted(self.kinds(md)),
                         [("false_schema_claim", "md5"),
                          ("false_schema_claim", "path")])

    def test_a_scope_word_in_another_clause_does_not_decide_the_scope(self):
        """#1087, the defect this rule introduced and a review caught before
        it merged.

        A reconciliation report says "the full record" constantly, and `full`
        resolves to Dataset alone — which excludes both core classes. Read
        over the whole sentence, the trailing clause here scoped a claim about
        `distributions` to Dataset, where it is not declared, and silenced the
        one finding #546 exists to make. The claim is in the first clause and
        is about the core record.
        """
        md = ("It carried a `distributions` block that does not appear in the "
              "supplied slot inventory, and stated content in five slots that "
              "the full record did not state.\n")
        self.assertEqual(self.kinds(md),
                         [("false_schema_claim", "distributions")])
        self.assertEqual(self.check(md)["findings"][0]["scope"], "unscoped")

    def test_the_scope_word_in_the_claims_own_clause_still_decides(self):
        """The clause bound must not undo the fix it guards."""
        md = ("The audit was wrong about several things, and "
              "`file_collections` is not declared by the core schema.\n")
        self.assertEqual(self.kinds(md), [])

    def test_the_finding_says_which_scope_it_used(self):
        md = "`distributions` is not declared in the core schema.\n"
        finding = self.check(md)["findings"][0]
        self.assertEqual(finding["scope"], "core")
        self.assertIn("scoped to the core schema", finding["detail"])

    def test_the_instrument_names_the_change(self):
        from data_sheets_schema.report_claims import REPORT_CLAIMS_INSTRUMENT
        self.assertTrue(REPORT_CLAIMS_INSTRUMENT.startswith("v7"),
                        REPORT_CLAIMS_INSTRUMENT)
        self.assertIn("#994", REPORT_CLAIMS_INSTRUMENT)
        self.assertIn("#1122", REPORT_CLAIMS_INSTRUMENT)
        self.assertIn("#1046", REPORT_CLAIMS_INSTRUMENT)


class RowsByRecordTest(Harness):
    """The block tallies the dispositions rows by record column (#1122).

    A `both` row wrongly flipped to `full` produces no finding — a `full`
    row resolves against the full record only — so the v9 canary reader
    compares the `both` count with the v8 fill's. That count has to be on
    the record, not recomputed from the report by whoever reads it."""

    MD = ("## Dispositions\n\n"
          "| slot | disposition | record | reason |\n|---|---|---|---|\n"
          "| `notes` | retained | both | as written |\n"
          "| `errata` | retained | full | full only |\n"
          "| `keywords` | retained | core | core only |\n"
          "| `conforms_to` | retained |  | unsaid |\n"
          "| `source_caveats` | retained | ambos | not a record |\n"
          "| `collection_timeframes` | retained | both | as written |\n")

    def test_every_record_value_is_counted_under_its_own_key(self):
        block = self.check(self.MD, full={"notes": 1, "errata": 1, "conforms_to": 1,
                                          "source_caveats": 1, "collection_timeframes": 1},
                           core={"notes": 1, "keywords": 1, "collection_timeframes": 1})
        self.assertEqual(block["rows_by_record"],
                         {"full": 1, "core": 1, "both": 2, "either": 1, "no_record_column": 0, "invalid": 1})
        self.assertEqual(sum(block["rows_by_record"].values()), block["disposition_rows"])

    def test_the_keys_are_fixed_and_zero_filled(self):
        block = self.check("## Dispositions\n\n| slot | disposition | record |\n|---|---|---|\n"
                           "| `notes` | retained | both |\n", full={"notes": 1}, core={"notes": 1})
        self.assertEqual(list(block["rows_by_record"]),
                         ["full", "core", "both", "either", "no_record_column", "invalid"])
        self.assertEqual(block["rows_by_record"],
                         {"full": 0, "core": 0, "both": 1, "either": 0, "no_record_column": 0, "invalid": 0})

    def test_a_table_with_no_record_column_is_counted_apart_from_an_empty_cell(self):
        """Every `either` in the corpus came from a table with no record
        column — a report format that named no record, not a run that left
        a cell empty (#1139 review, S2). A reader comparing `both` counts
        across arms must be able to tell "none" from "not measurable"."""
        block = self.check("## Dispositions\n\n| # | Severity | Slot | Disposition |\n|---|---|---|---|\n"
                           "| 1 | low | `notes` | retained |\n| 2 | low | `errata` | retained |\n",
                           full={"notes": 1, "errata": 1}, core={"notes": 1})
        self.assertEqual(block["rows_by_record"]["no_record_column"], 2)
        self.assertEqual(block["rows_by_record"]["either"], 0)

    def test_a_cell_that_spells_the_sentinel_is_invalid_not_a_missing_column(self):
        """#1139 review, R1: the column's presence must not be forgeable
        from a cell, or the two states S2 separated collapse again."""
        block = self.check("## Dispositions\n\n| slot | disposition | record |\n|---|---|---|\n"
                           "| `notes` | retained | no_record_column |\n| `errata` | retained | No_Record_Column |\n",
                           full={"notes": 1, "errata": 1}, core={"notes": 1})
        self.assertEqual(block["rows_by_record"]["invalid"], 2)
        self.assertEqual(block["rows_by_record"]["no_record_column"], 0)
        self.assertEqual(block["claims_unnamed"], 2)

    def test_a_report_without_a_table_tallies_zero(self):
        block = self.check("## Report\n\nNothing changed.\n")
        self.assertEqual(block["disposition_rows"], 0)
        self.assertEqual(sum(block["rows_by_record"].values()), 0)


class TheFixtureMatchesTheSchemaTest(unittest.TestCase):
    """The fixture's membership is the real one where the scope tests rely on
    it (#1090).

    A fixture that puts `distributions` on `Dataset` as well as `CoreDataset`
    makes every core-versus-full assertion pass under either reading, which
    is what let the #1087 regression test's finding-level assertion be
    vacuous. This pins the two slots those tests turn on.
    """

    def test_every_slot_in_the_fixture_is_declared_where_the_schema_says(self):
        """Every slot, not only the two the scope tests turn on.

        Pinning two left `errata` and `collection_timeframes` diverging one
        slot away from the trap the pin was written for. They are used only by
        removal tests today, which never consult the class inventory — which
        is exactly what was true of `distributions` until a scope rule started
        reading it.
        """
        from data_sheets_schema.report_claims import declared_slots
        real = declared_slots()
        if "Dataset" not in real or "CoreDataset" not in real:
            self.skipTest("the schema is not importable in this checkout")
        for slot in sorted({s for names in DECLARED.values() for s in names}):
            with self.subTest(slot=slot):
                self.assertEqual(
                    sorted(c for c, s in DECLARED.items() if slot in s),
                    sorted(c for c, s in real.items() if slot in s))


if __name__ == "__main__":
    unittest.main()


class UnrecordedRemovalTest(Harness):
    """#1054 (instrument v5): the phase-1 snapshot makes an unrecorded
    removal deterministic, and a retention claim in prose is a claim."""

    TABLE = ("## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n"
             "| `keywords` | retained | both | fine |\n")

    def check_with(self, markdown, snapshot, full=None, core=None, expected=True):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "r.md"
        path.write_text(markdown, encoding="utf-8")
        return check_report(path, full or {}, core or {}, DECLARED, snapshot=snapshot,
                            dispositions_expected=expected)

    def test_a_slot_the_snapshot_carried_and_the_record_dropped_with_no_row_is_a_finding(self):
        snap = {"keywords": ["a"], "regulatory_restrictions": {"regulatory_restrictions": "a legal framework"}}
        full = {"keywords": ["a"]}
        b = self.check_with(self.TABLE, snap, full=full, core=full)
        self.assertEqual([(f["kind"], f["slot"], f["record"]) for f in b["findings"]],
                         [("removal_not_recorded", "regulatory_restrictions", "full")])
        self.assertTrue(b["snapshot_checked"])
        self.assertEqual(b["removals_unrecorded"], ["regulatory_restrictions"])
        self.assertEqual(b["removals_unrecorded_count"], 1)
        self.assertIn("add a `removed` row for `regulatory_restrictions`", b["findings"][0]["detail"])

    def test_a_removed_row_or_a_removal_sentence_records_it(self):
        snap = {"keywords": ["a"], "data_governance": {"accountable_organization": "USF"}, "content_warnings": {"content_warnings_present": False}}
        full = {"keywords": ["a"]}
        md = (self.TABLE + "| `data_governance` | removed | both | out of scope |\n\n"
              "**Action:** the `content_warnings` object was removed from the record.\n")
        b = self.check_with(md, snap, full=full, core=full)
        self.assertEqual([f["kind"] for f in b["findings"] if f["kind"] == "removal_not_recorded"], [])
        self.assertEqual(b["removals_unrecorded"], [])

    def test_a_whole_object_counts_and_so_does_a_leaf_at_the_root(self):
        snap = {"keywords": ["a"], "data_governance": {"stewards": [{"name": "x"}]}, "id": "doi:10.1/x"}
        b = self.check_with(self.TABLE, snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(sorted(f["slot"] for f in b["findings"]), ["data_governance", "id"])

    def test_commentary_and_class_declarations_and_empty_values_are_not_removals(self):
        snap = {"keywords": ["a"], "notes": "phase-1 note", "source_caveats": ["x"], "conforms_to_schema": "s",
                "conforms_to_class": "c", "errata": [], "funders": None}
        b = self.check_with(self.TABLE, snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(b["findings"], [])

    def test_a_value_that_survives_is_not_a_removal_and_an_emptied_one_is(self):
        snap = {"keywords": ["a"], "funders": [{"name": "NIH"}]}
        self.assertEqual(self.check_with(self.TABLE, snap, full={"keywords": ["a"], "funders": [{"name": "NIH"}]},
                                         core={"keywords": ["a"]})["findings"], [])
        b = self.check_with(self.TABLE, snap, full={"keywords": ["a"], "funders": []}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"]], ["funders"])

    def test_no_snapshot_is_reported_as_not_checked_never_as_clean(self):
        b = self.check(self.TABLE, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertFalse(b["snapshot_checked"])
        self.assertIsNone(b["removals_unrecorded_count"])
        self.assertEqual(b["removals_unrecorded"], [])

    def test_a_prose_claim_names_a_leaf_or_a_record_and_is_satisfied_anywhere(self):
        md = (self.TABLE + "\nThe four named reviewers stay in `review_details`; the caveat remains in "
              "`core.notes`; the split rationale remains in `splits.split_details`.\n")
        full = {"keywords": ["a"], "ethical_reviews": [{"review_details": "four reviewers"}],
                "splits": [{"split_details": "70/15/15"}]}
        core = {"keywords": ["a"], "notes": "the caveat"}
        b = self.check(md, full=full, core=core)
        self.assertEqual(b["findings"], [])
        self.assertEqual(b["prose_retention_claims"], 3)
        # `core.notes` is the core's notes, not the full record's
        b = self.check(md, full={**full, "notes": "the caveat"}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"]], ["core.notes"])

    def test_a_snapshot_diff_on_a_run_never_asked_for_the_table_lists_and_does_not_find(self):
        """The gate is the run's own expectation (#961), not a parsed table
        (#1175 review, M2): a pre-#929 audit summary with Slot/Disposition
        headers parses as one and must not promote a report into findings."""
        snap = {"keywords": ["a"], "publisher": "NIH"}
        audit = ("| # | Severity | Slot | Disposition |\n|---|---|---|---|\n| 1 | low | `keywords` | retained |\n\n"
                 "- `publisher` **removed**. The bundle gives no publisher.\n")
        b = self.check_with("## Changes\n\nProse only, no table.\n", snap, full={"keywords": ["a"]}, core={"keywords": ["a"]}, expected=False)
        self.assertEqual(b["findings"], [])
        self.assertEqual(b["removals_unrecorded"], ["publisher"])
        self.assertEqual(b["removals_unrecorded_count"], 1)
        self.assertIn("no dispositions table expected", b["snapshot_basis"])
        b = self.check_with(audit, {"keywords": ["a"], "publisher": "NIH", "created_on": "2025"},
                            full={"keywords": ["a"]}, core={"keywords": ["a"]}, expected=False)
        self.assertEqual(b["findings"], [])                                     # the audit table is not the table
        self.assertEqual(b["removals_unrecorded"], ["created_on"])              # `publisher` is recorded in prose
        # expected and the table unparsable: still findings, and the basis says so
        b = self.check_with("## Dispositions\n\n(the model wrote no table)\n", snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"]], ["publisher"])
        self.assertIn("no table parsed", b["snapshot_basis"])
        b = self.check_with(self.TABLE, snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"]], ["publisher"])
        self.assertEqual(b["snapshot_basis"], "dispositions table expected: unrecorded removals are findings")

    def test_a_nested_or_core_only_removal_does_not_record_a_whole_slot_removal(self):
        """#1175 review, M1: a row removing `x.leaf` or `x[0]`, or removing `x`
        from the core alone, says nothing about `x` leaving the full record."""
        snap = {"keywords": ["a"], "data_governance": {"committee_contact": "x", "other": "y"},
                "errata": [{"a": 1}, {"b": 2}], "funders": [{"name": "NIH"}]}
        md = (self.TABLE + "| `data_governance.committee_contact` | removed | both | PII |\n"
              "| `errata[0]` | removed | full | dup |\n| `funders` | removed | core | out of core |\n")
        b = self.check_with(md, snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(sorted(f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"),
                         ["data_governance", "errata", "funders"])
        md2 = self.TABLE + "| `funders` | removed | full | out |\n| `errata` | removed | both | dup |\n"
        b = self.check_with(md2, {"keywords": ["a"], "funders": [{"name": "NIH"}], "errata": [{"a": 1}]},
                            full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f for f in b["findings"] if f["kind"] == "removal_not_recorded"], [])

    def test_a_prose_removal_statement_records_it_for_suppression_only(self):
        """#1175 review, S1: headings, bold leads and "is absent from" record a
        removal the strict claim parser does not read; they suppress the
        snapshot finding and are never removal claims."""
        snap = {"keywords": ["a"], "errata": [{"a": 1}], "cleaning_strategies": [{"x": 1}],
                "conforms_to_standard": "x", "splits": [{"s": 1}]}
        md = (self.TABLE + "\n### 4.7 Removed `errata` (low)\n\n- `cleaning_strategies` **removed**. Rationale.\n\n"
              "`conforms_to_standard` is absent from both records.\n\n#### F12. `splits` removed from full record\n")
        b = self.check_with(md, snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f for f in b["findings"] if f["kind"] == "removal_not_recorded"], [])
        self.assertEqual(b["removals_unrecorded"], [])
        self.assertEqual([f for f in b["findings"] if f["kind"] == "removal_not_performed"], [])

    def test_the_weak_removal_signal_reads_casualties_not_destinations_or_the_core(self):
        """#1175 round 2, M1: a destination ("recorded in `errata`"), a sentence
        about the core alone, or a table line with a removal word records
        nothing about a full-record removal."""
        snap = {"keywords": ["a"], "errata": [{"a": 1}], "funders": [{"n": 1}], "compression": "gz", "splits": [{"s": 1}]}
        md = (self.TABLE + "| `errata` | Reviewed | both | Dropped the duplicate entry; slot kept |\n\n"
              "- `keywords`, `funders` and `compression` are absent from the core record.\n\n"
              "The enum was dropped; the facts are recorded in `errata`.\n\n"
              "**`splits`.** Removed from the full record; nothing to keep.\n")
        b = self.check_with(md, snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(sorted(f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"),
                         ["compression", "errata", "funders"])
        self.assertEqual(b["removals_unrecorded"], ["errata", "funders", "compression"])

    def test_a_removal_claim_in_an_unrecognised_table_is_still_read(self):
        """#1175 round 3, M1/S2: the exclusion is the parsed table's own
        extent, not the heading's section, so a `| core | slot | change |`
        table under `## Dispositions` keeps its claims (the #546 shape) and a
        dispositions-shaped table with no heading is still the strict
        reader's."""
        md = ("## Dispositions\n\n| record | slot | change |\n|---|---|---|\n| core | `distributions` | removed; content redistributed |\n")
        b = self.check(md, full={"keywords": ["a"]}, core={"distributions": [{"path": "a"}]})
        self.assertEqual([(f["kind"], f["slot"]) for f in b["findings"]], [("removal_not_performed", "distributions")])
        md2 = self.TABLE + "\n| record | slot | change |\n|---|---|---|\n| core | `distributions` | removed; content redistributed |\n"
        b = self.check(md2, full={"keywords": ["a"]}, core={"keywords": ["a"], "distributions": [{"path": "a"}]})
        self.assertEqual([(f["kind"], f["slot"]) for f in b["findings"]], [("removal_not_performed", "distributions")])
        headless = ("| slot | disposition | record | reason |\n|---|---|---|---|\n| `keywords` | retained | both | fine |\n"
                    "| `errata` | Reviewed | both | Dropped the duplicate entry; slot kept |\n")
        b = self.check_with(headless, {"keywords": ["a"], "errata": [{"a": 1}]}, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"], ["errata"])

    def test_a_recognised_table_with_no_parseable_row_is_still_the_strict_readers(self):
        """#1175 round 4, M1: keyed on the parsed rows, a table whose header
        the strict reader recognised but whose rows it could not read was
        excluded by nobody, and "| `errata` | Reviewed | both | slot kept |"
        became a removal claim and a removal record at once (#962 again)."""
        md = ("## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n"
              "| `errata` | Reviewed | both | Dropped the duplicate entry; slot kept |\n")
        b = self.check(md, full={"errata": [{"a": 1}]}, core={"errata": [{"a": 1}]})
        self.assertEqual(b["findings"], []); self.assertEqual(b["claims_checked"], 0)
        b = self.check_with(md, {"errata": [{"a": 1}]}, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"], ["errata"])

    def test_a_second_table_under_the_first_starts_its_own_extent(self):
        """#1175 round 4, S4: two tables with no blank line between them are
        one contiguous run of `|` lines; the second's header decides for
        itself whether it is the strict reader's."""
        md = (self.TABLE + "| record | slot | change |\n|---|---|---|\n| core | `distributions` | removed; content redistributed |\n")
        b = self.check(md, full={"keywords": ["a"]}, core={"keywords": ["a"], "distributions": [{"path": "a"}]})
        self.assertEqual([(f["kind"], f["slot"]) for f in b["findings"]], [("removal_not_performed", "distributions")])
        md = (self.TABLE + "| slot | disposition | record | reason |\n|---|---|---|---|\n| `errata` | Reviewed | both | kept |\n")
        b = self.check(md, full={"keywords": ["a"], "errata": [1]}, core={"keywords": ["a"], "errata": [1]})
        self.assertEqual(b["findings"], [])                                        # recognised too: excluded

    def test_a_coordinated_casualty_list_is_not_a_destination(self):
        """#1175 round 4, S1: "the values in `a`, `b` and `c` were removed"
        — the removal word follows the list, so every item is a casualty and
        an unrecorded removal of any of them is recorded, not a finding."""
        snapshot = {"collection_timeframes": [1], "distribution_dates": [1], "versions_available": [1], "funders": [1]}
        md = self.TABLE + "\nThe dates in `collection_timeframes`, `distribution_dates`, `versions_available` and `funders` were removed.\n"
        b = self.check_with(md, snapshot, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f for f in b["findings"] if f["kind"] == "removal_not_recorded"], [])
        md = self.TABLE + "\n`funders` was removed; its values are already recorded in `collection_timeframes` and `distribution_dates`.\n"
        b = self.check_with(md, snapshot, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(sorted(f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"),
                         ["collection_timeframes", "distribution_dates", "versions_available"])

    def test_a_list_named_before_a_retention_or_a_distant_removal_is_not_a_casualty_list(self):
        """#1175 round 5, M1: the corpus sentences the first casualty rule
        silenced — a destination named before a removal elsewhere in the
        sentence, a retention verb after the list, "rather than removed"."""
        snapshot = {"funders": [1], "prohibition_reason": "x", "description": "y", "related_datasets": [1], "version_access": [1]}
        for sent in ("The NIH award period (a funding fact, already carried under `funders`) and the site list have been removed.",
                     "The reasons were rewritten to carry the prohibition statement and its rationale together in `prohibition_reason`, and `description` was trimmed; the duplicates were removed.",
                     "These are retained as evidence about the prior release — in `related_datasets` and `version_access` — rather than removed.",
                     "The range stays in `funders`, so nothing is dropped."):
            b = self.check_with(self.TABLE + "\n" + sent + "\n", snapshot, full={"keywords": ["a"]}, core={"keywords": ["a"]})
            found = sorted(f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded")
            self.assertEqual(found, sorted(snapshot), sent)                                 # none silenced
        md = self.TABLE + "\nThe dates in `collection_timeframes`, `distribution_dates` and `versions_available` were removed.\n"
        b = self.check_with(md, {"collection_timeframes": [1], "distribution_dates": [1], "versions_available": [1]},
                            full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f for f in b["findings"] if f["kind"] == "removal_not_recorded"], [])   # still a casualty list

    def test_the_seven_sentences_the_codex_review_named_do_not_record_a_removal(self):
        """#1175 Codex review, M1: the weak signal added every backticked
        name in any sentence carrying a removal word, so a retention, a
        negation, a hypothetical, a neighbouring clause, a container and a
        core-only statement each silenced a real unrecorded removal."""
        for sent in ("`funders` was retained rather than removed.",
                     "`funders` was never removed.",
                     "If `funders` is removed, explain why.",
                     "`errata` was removed because `funders` remains valid.",
                     "`funders` contains identifiers that were removed.",
                     "Deleted prose remains in the existing `funders` block."):
            b = self.check_with(self.TABLE + "\n" + sent + "\n", {"funders": [1]},
                                full={"keywords": ["a"]}, core={"keywords": ["a"]})
            self.assertEqual([f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"], ["funders"], sent)
        # ... and a real one still records
        b = self.check_with(self.TABLE + "\n`funders` was removed.\n", {"funders": [1]},
                            full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f for f in b["findings"] if f["kind"] == "removal_not_recorded"], [])

    def test_a_disposition_joined_by_a_dash_or_a_colon_still_records(self):
        """#1175 round 7, M1: an em dash and a colon join a slot to its
        disposition in these reports, so splitting on them severed the
        subject from the removal word in 197 of the 301 corpus reports."""
        for sent in ("### 2.1 `funders` — removed (high)",
                     "**`funders` — slot removed entirely.**",
                     "**`funders`** — object removed in full.",
                     "- **Removed:** `funders`.",
                     "**`funders` (finding 3) — slot removed.**",
                     "`funders`: removed."):
            b = self.check_with(self.TABLE + "\n" + sent + "\n", {"funders": [1]},
                                full={"keywords": ["a"]}, core={"keywords": ["a"]})
            self.assertEqual([f for f in b["findings"] if f["kind"] == "removal_not_recorded"], [], sent)

    def test_a_contrast_after_the_removal_word_does_not_void_it(self):
        """#1175 round 7, M2: "was removed, not renamed" and "removed
        rather than guessed" were voided by their own contrast — 21 corpus
        names — while "retained rather than removed" must still void."""
        for sent in ("`funders` was removed from all four rather than guessed.",
                     "**Core dropped `funders` without a structured home.**",
                     "`funders` was removed, not renamed.",
                     "`funders` omitted rather than approximated."):
            b = self.check_with(self.TABLE + "\n" + sent + "\n", {"funders": [1]},
                                full={"keywords": ["a"]}, core={"keywords": ["a"]})
            self.assertEqual([f for f in b["findings"] if f["kind"] == "removal_not_recorded"], [], sent)
        b = self.check_with(self.TABLE + "\n`funders` was retained rather than removed.\n", {"funders": [1]},
                            full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"], ["funders"])

    def test_a_negation_in_the_previous_sentence_does_not_void_a_retention_claim(self):
        """#1175 round 7, M3: the 80-character window spanned a full stop,
        so all 19 genuine prose retention claims of that shape were dropped."""
        md = (self.TABLE + "\nThe bundle names no DPIA or equivalent formal privacy risk assessment. "
              "The substantive content is retained under `notes`.\n")
        b = self.check(md, full={"keywords": ["a"], "notes": "x"}, core={"keywords": ["a"]})
        self.assertEqual(b["prose_retention_claims"], 1); self.assertEqual(b["findings"], [])
        md = self.TABLE + "\nNo value remains in `errata`.\n"
        b = self.check(md, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(b["prose_retention_claims"], 0); self.assertEqual(b["findings"], [])

    def test_a_claim_the_reader_rejects_records_no_removal(self):
        """#1175 Codex review, M3: a row naming `funders` whose claim is a
        field removed from every entry was counted unnamed and still
        suppressed the snapshot finding."""
        md = self.TABLE + "| `funders` | removed | full | the `role` field was removed from all entries |\n"
        b = self.check_with(md, {"funders": [1]}, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"], ["funders"])
        self.assertEqual(b["claims_unnamed"], 1)

    def test_a_generic_removal_row_reads_its_record_cell(self):
        """#1175 Codex review, M6: `| full | `x` | removed |` read as
        `either` — against the core record — so a slot the full record
        still carries raised nothing."""
        md = "| record | slot | change |\n|---|---|---|\n| full | `keywords` | removed |\n"
        b = self.check(md, full={"keywords": ["a"]}, core={})
        self.assertEqual([(f["kind"], f["record"]) for f in b["findings"]], [("removal_not_performed", "full")])

    def test_a_second_recognised_header_decodes_its_own_columns(self):
        """#1175 Codex review, M5: the second table's rows were decoded with
        the first table's column map."""
        md = ("## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n"
              "| `keywords` | retained | both | fine |\n"
              "| disposition | slot | record | reason |\n|---|---|---|---|\n"
              "| removed | `errata` | full | gone |\n")     # contiguous: a blank line already reset the header
        b = self.check(md, full={"keywords": ["a"], "errata": [1]}, core={"keywords": ["a"]})
        self.assertEqual([(f["kind"], f["slot"]) for f in b["findings"]], [("removal_not_performed", "errata")])

    def test_a_retention_claim_needs_a_slot_and_an_unnegated_clause(self):
        """#1175 Codex review, M7."""
        md = self.TABLE + "\nNo value remains in `errata`. The flag remains at `false`.\n"
        b = self.check(md, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(b["findings"], []); self.assertEqual(b["prose_retention_claims"], 0)

    def test_a_recognised_header_without_a_separator_and_a_decorated_header_are_the_strict_readers(self):
        """#1175 round 5, M2/S1: `disposition_rows` and the exclusion share
        one header rule — no separator row required, markdown decoration
        stripped — so the two readers cannot own different tables."""
        for header in ("| slot | disposition | record | reason |", "| **Slot** | **Disposition** | **Record** | **Reason** |",
                       "| Slot: | Disposition: | Record | Reason |"):
            md = f"## Dispositions\n\n{header}\n| `keywords` | retained | both | fine |\n| `errata` | Reviewed | both | Dropped the duplicate entry; slot kept |\n"
            b = self.check(md, full={"keywords": ["a"], "errata": [1]}, core={"keywords": ["a"], "errata": [1]})
            self.assertEqual(b["findings"], [], header); self.assertEqual(b["claims_checked"], 1, header)
            b = self.check_with(md, {"keywords": ["a"], "errata": [{"a": 1}]}, full={"keywords": ["a"]}, core={"keywords": ["a"]})
            self.assertEqual([f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"], ["errata"], header)

    def test_a_loose_only_live_value_is_described_from_the_loose_reading(self):
        """#1175 round 4, S6: a `both` row whose slot is live only through
        the dotted-over-list reading names the core when the core carries it,
        and counts the entries rather than saying "a value"."""
        md = self.TABLE + "| `splits.split_details` | removed | both | gone |\n"
        core = {"keywords": ["a"], "splits": [{"split_details": [{"n": 1}, {"n": 2}]}]}
        b = self.check(md, full={"keywords": ["a"]}, core=core)
        f = [x for x in b["findings"] if x["kind"] == "removal_not_performed"]
        self.assertEqual(len(f), 1); self.assertNotIn("a value", f[0]["detail"]); self.assertIn("2", f[0]["detail"])
        core = {"keywords": ["a"], "splits": [{"split_details": [{"n": 1}, {"n": 2}, {"n": 3}]}, {"split_details": [{"n": 4}, {"n": 5}]}]}
        b = self.check(md, full={"keywords": ["a"]}, core=core)
        f = [x for x in b["findings"] if x["kind"] == "removal_not_performed"]
        self.assertIn("5", f[0]["detail"])                                                  # entries, not matches (round 5, S2)

    def test_the_weak_signal_skips_coordinated_destinations_and_class_names(self):
        """#1175 round 3, S1/S5."""
        snap = {"keywords": ["a"], "license_and_use_terms": {"x": 1}, "distribution_formats": [{"f": 1}], "variables": [{"v": 1}]}
        md = (self.TABLE + "\nThe enum was dropped; the access conditions are already recorded in `license_and_use_terms` and `distribution_formats`.\n\n"
              "The full record's 57 `VariableMetadata` objects were removed with the `variables` slot.\n")
        b = self.check_with(md, snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(sorted(f["slot"] for f in b["findings"] if f["kind"] == "removal_not_recorded"),
                         ["distribution_formats", "license_and_use_terms"])

    def test_a_removed_row_steps_over_a_list_as_a_retained_row_does(self):
        """#1175 round 3, S4."""
        md = self.TABLE + "| `splits.split_details` | removed | full | gone |\n"
        b = self.check(md, full={"keywords": ["a"], "splits": [{"split_details": "70/15/15"}]}, core={"keywords": ["a"]})
        self.assertEqual([(f["kind"], f["slot"]) for f in b["findings"]], [("removal_not_performed", "splits.split_details")])

    def test_a_dotted_claim_whose_root_is_absent_is_not_satisfied_elsewhere(self):
        """#1175 round 2, S2."""
        md = self.TABLE + "\nThe figures remain in `errata.description`.\n"
        b = self.check(md, full={"keywords": ["a"], "description": "top-level"}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"]], ["errata.description"])
        b = self.check(md, full={"keywords": ["a"], "errata": [{"description": "x"}]}, core={"keywords": ["a"]})
        self.assertEqual(b["findings"], [])

    def test_a_table_row_steps_over_a_list_as_prose_does(self):
        """#1175 round 2, S3: one claim, one reading."""
        md = self.TABLE + "| `splits.split_details` | retained | full | fine |\n"
        b = self.check(md, full={"keywords": ["a"], "splits": [{"split_details": "70/15/15"}]}, core={"keywords": ["a"]})
        self.assertEqual(b["findings"], [])

    def test_a_negated_retention_and_a_non_slot_token_are_not_claims(self):
        """#1175 review, S2."""
        md = (self.TABLE + "\nNothing remains in `errata`. It never remains in `notes`; neither record retains it, "
              "so nothing remains in `content_warnings`. The slot remains in `CoreDataset`. "
              "The literal string remains in `HIPAA`.\n")
        b = self.check(md, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(b["findings"], [])
        self.assertEqual(b["prose_retention_claims"], 0)
        # a negator in an earlier clause does not negate the claim (#1175 round 2, S1)
        md = self.TABLE + "\nThe bundle names no formal committee, so the statement was retained under `notes`.\n"
        b = self.check(md, full={"keywords": ["a"], "notes": "x"}, core={"keywords": ["a"]})
        self.assertEqual(b["prose_retention_claims"], 1); self.assertEqual(b["findings"], [])

    def test_prose_paths_step_over_lists_and_a_wrapped_sentence_is_one_claim(self):
        """#1175 review, S3/S4: `splits.split_details` means `splits[*].split_details`,
        and a claim that wraps across lines is still read."""
        md = (self.TABLE + "\nThe split rationale remains in\n`splits.split_details` and the roles stay in\n"
              "`data_governance.stewards`.\n")
        full = {"keywords": ["a"], "splits": [{"split_details": "70/15/15"}], "data_governance": {"stewards": [{"n": 1}]}}
        b = self.check(md, full=full, core={"keywords": ["a"]})
        self.assertEqual(b["findings"], [])
        self.assertEqual(b["prose_retention_claims"], 2)

    def test_a_prose_retention_claim_is_checked(self):
        md = (self.TABLE + "\nThe legal analysis remains in `regulatory_restrictions.regulatory_restrictions` "
              "and the roles stay in `data_governance.stewards`.\n")
        full = {"keywords": ["a"], "data_governance": {"stewards": [{"name": "x"}]}}
        b = self.check(md, full=full, core={"keywords": ["a"]})
        self.assertEqual([(f["kind"], f["slot"], f["record"]) for f in b["findings"]],
                         [("retention_not_shown", "regulatory_restrictions.regulatory_restrictions", "either")])
        self.assertEqual(b["prose_retention_claims"], 2)
        # present in the core alone satisfies it, as an unnamed record column does
        b = self.check(md, full={"keywords": ["a"]}, core={"keywords": ["a"], "regulatory_restrictions": {"regulatory_restrictions": "x"},
                                                           "data_governance": {"stewards": [{"name": "x"}]}})
        self.assertEqual(b["findings"], [])

    def test_a_negated_or_tabled_retention_is_not_a_prose_claim(self):
        md = (self.TABLE + "| `errata` | retained | both | it remains in `errata` |\n\n"
              "The caveat no longer remains in `source_caveats`; it was not kept in `notes`.\n")
        b = self.check(md, full={"keywords": ["a"], "errata": [{"x": 1}]}, core={"keywords": ["a"], "errata": [{"x": 1}]})
        self.assertEqual(b["prose_retention_claims"], 0)
        self.assertEqual(b["findings"], [])

    def test_the_instrument_is_v7(self):
        """The block names the current reading first and keeps every earlier
        one, so a block computed under either is readable from its own text."""
        b = self.check(self.TABLE, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertTrue(b["instrument"].startswith("v7 (#1089, #1194, #1196)"))
        self.assertIn("v5 (#1054)", b["instrument"])
        self.assertIn("v4 (#1122)", b["instrument"])


class PresentTenseRemovalTest(Harness):
    """#1175 round 8 widened the removal word to the present tense, and round
    9 found nothing pinned it and that the widening records names the reports
    do not say were removed (M4, S1, S2). `removals_unrecorded` is a
    *suppression* set, so a false name here silences a real finding on that
    slot, and a missing true form raises a false one."""

    TABLE = ("## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n"
             "| `keywords` | retained | both | fine |\n")

    def unrecorded(self, sentence, slot="citation"):
        import tempfile
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "r.md"
        path.write_text(self.TABLE + "\n" + sentence + "\n", encoding="utf-8")
        snap = {"keywords": ["a"], slot: "a value the record no longer carries"}
        full = {"keywords": ["a"]}
        return check_report(path, full, full, DECLARED, snapshot=snap,
                            dispositions_expected=True)["removals_unrecorded"]

    def test_every_present_tense_form_records_the_removal(self):
        """Reading only past participles listed `citation` as unrecorded when
        the report said "Both records now omit `citation`". `omitted?` matches
        `omitte`, not `omit`, which is how the gap survived a review round."""
        for sentence in (
                "Both records now omit `citation`.",
                "Reconciliation omits `citation` from both records.",
                "Reconciliation removes `citation` from both records.",
                "The projection remove `citation` in this pass.",
                "This pass drops `citation`.",
                "The reconcile step strips `citation`.",
                "The core deletes `citation`.",
                "The curator withdraws `citation`."):
            with self.subTest(sentence):
                self.assertEqual(self.unrecorded(sentence), [], sentence)

    def test_a_sentence_about_the_core_alone_records_nothing_about_the_full_record(self):
        """The deliberate line the widening does not cross: "The core record
        omits `citation`" is a claim about the core, and the unrecorded-removal
        finding is against the full record."""
        self.assertEqual(self.unrecorded("The core record omits `citation`."), ["citation"])

    def test_the_past_participles_still_record_it(self):
        for sentence in ("`citation` was removed.", "`citation` was deleted.", "`citation` was dropped.",
                         "`citation` was omitted.", "`citation` was stripped.", "`citation` was withdrawn.",
                         "`citation` is absent from both records."):
            with self.subTest(sentence):
                self.assertEqual(self.unrecorded(sentence), [], sentence)

    def test_a_denied_removal_records_nothing(self):
        """S2: "None of these is a slot removed from a record: `citation` …"
        denies a removal and was suppressing one. `nothing` and `none` void;
        bare `no` does not, because 19 of the 20 corpus clauses where it
        precedes the removal word are removals."""
        for sentence in ("None of these is a slot removed from a record: `citation` and `keywords`.",
                         "Nothing was removed and `citation` stays."):
            with self.subTest(sentence):
                self.assertEqual(self.unrecorded(sentence), ["citation"], sentence)

    def test_a_bare_no_before_the_removal_word_is_still_a_removal(self):
        self.assertEqual(
            self.unrecorded("`citation` has no `CoreDistribution` counterpart and is dropped."), [])

    def test_a_rewritten_slot_is_present(self):
        """S1: "`special_protections` was rewritten to drop the superseded
        clause" leaves the slot in the record; four corpus clauses have this
        shape."""
        self.assertEqual(
            self.unrecorded("`citation` was rewritten to drop the superseded clause."), ["citation"])

    def test_a_road_not_taken_is_not_a_removal(self):
        """The corpus clause, from the 2026-08-05 v3 rep1 AI_READI report:
        the sentence explains why the relations were *retained*."""
        self.assertEqual(
            self.unrecorded("Retained because `Dataset` requires `citation`, the targets are unambiguous, "
                            "and the alternative is to drop five well-evidenced relations."), ["citation"])

    def test_the_removal_word_as_a_noun_is_not_a_removal(self):
        """S1: "The intentional projection drops are unchanged: …". Only the
        -s forms before a verb — "the slots removed are `a` and `b`" is a
        real removal and must stay one."""
        self.assertEqual(
            self.unrecorded("The intentional projection drops are unchanged: `citation`."), ["citation"])
        self.assertEqual(
            self.unrecorded("The slots removed are `citation` and `keywords`."), [])


#: What `declared_ranges` returns, in miniature: every core class, its slots,
#: and the class each slot ranges to (`None` for a scalar). `resources` ranges
#: back to `CoreDataset`, which is what makes a nested path worth walking.
RANGES = {
    "CoreDataset": {"keywords": None, "notes": None, "source_caveats": None,
                    "resources": "CoreDataset", "distributions": "CoreDistribution",
                    "creators": "Creator"},
    "CoreDistribution": {"format": None, "media_type": None, "path": None},
    "Creator": {"name": None, "orcid": None},
}

#: The slot map that goes with `RANGES`, derived from it so the two describe
#: one schema. In production both come from the same `SchemaView`; a test that
#: let them drift would be checking a core class that does not exist.
NESTED_DECLARED = {cls: set(slots) for cls, slots in RANGES.items()}


class CoreDeclaresNestedTest(unittest.TestCase):
    """#994: the core-declares test read the path's root slot only.

    Sound while every class-ranged slot the two classes share has the same
    range. Two do not: `resources` ranges to `Dataset` on the full and
    `CoreDataset` on the core, so it recurses into a smaller class, and a
    derived core carries `distributions` where the full carries
    `distribution_formats`. A finding on a `both` row under either was
    already correct — the row is checked against the core record literally —
    but it could not say the core *could not* carry the value, which is the
    difference between "name `full`" and "the two records disagree".
    """

    def test_indices_are_not_steps(self):
        self.assertEqual(rc._path_steps("resources[0].creators[12].name"),
                         ["resources", "creators", "name"])
        self.assertEqual(rc._path_steps("keywords"), ["keywords"])

    def test_a_nested_path_is_walked_against_the_class_each_step_lands_in(self):
        for path, expected in (("keywords", True),
                               ("resources", True),
                               ("resources[0].keywords", True),
                               ("resources[0].resources[1].keywords", True),
                               ("resources[0].file_collections", False),   # Dataset has it, CoreDataset does not
                               ("distributions[0].format", True),
                               ("distributions[0].keywords", False),       # CoreDistribution has no keywords
                               ("creators[0].name", True),
                               ("creators[0].affiliation", False)):
            with self.subTest(path):
                self.assertIs(rc._core_declares(path, NESTED_DECLARED, RANGES), expected)

    def test_a_scalar_cannot_carry_a_further_step(self):
        self.assertFalse(rc._core_declares("keywords[0].anything", NESTED_DECLARED, RANGES))

    def test_a_class_the_map_does_not_carry_is_not_read_as_a_scalar(self):
        """#994 round 2, S1. `ranges` said `creators` ranges to `Creator`;
        the map simply had no `Creator` entry. Reading that back as "the
        step before it was a scalar" wrote a sentence contradicting the
        map's own entry and dropped the row from the total. A gap in the
        map is not evidence, so the walk stops and leaves the root test's
        answer standing."""
        partial = {"CoreDataset": {"keywords": None, "creators": "Creator"}}
        verdict, cause = rc._core_path_verdict("creators.name", NESTED_DECLARED, partial)
        self.assertEqual(verdict, rc.HOLDABLE)
        self.assertEqual(cause, "")

    def test_the_root_class_missing_from_the_map_names_no_step_at_all(self):
        """The same gap at the first step. It used to index `steps[-1]`,
        which Python reads from the end, so the sentence named the path's
        last step as the scalar (#994 round 2, S1)."""
        verdict, cause = rc._core_path_verdict("creators.name", NESTED_DECLARED, {"Other": {}})
        self.assertEqual(verdict, rc.HOLDABLE)
        self.assertEqual(cause, "")

    def test_a_real_scalar_still_names_the_step_that_holds_the_value(self):
        verdict, cause = rc._core_path_verdict("creators[0].name.given", NESTED_DECLARED, RANGES)
        self.assertEqual(verdict, rc.NOT_A_PATH)
        self.assertIn("`name` holds a value, not an object", cause)

    def test_without_ranges_the_root_test_stands(self):
        """A caller that has not been updated keeps the old answer rather
        than a wrong one."""
        for path in ("resources[0].file_collections", "distributions[0].keywords"):
            with self.subTest(path):
                self.assertTrue(rc._core_declares(path, NESTED_DECLARED))
                self.assertFalse(rc._core_declares(path, NESTED_DECLARED, RANGES))

    def test_a_root_the_core_lacks_is_still_caught_either_way(self):
        for ranges in (None, RANGES):
            with self.subTest(ranges=bool(ranges)):
                self.assertFalse(rc._core_declares("file_collections", NESTED_DECLARED, ranges))

    def test_an_empty_path_declares_nothing(self):
        self.assertFalse(rc._core_declares("", NESTED_DECLARED, RANGES))


    def test_a_wildcard_subscript_is_not_a_step(self):
        """#994 round 1, M1: `[*]` is this module's own notation and appears
        in committed dispositions tables (`creators[*].name`). Splitting on
        `[` and filtering digits left `*]` standing as a step, so a real row
        walked into a slot no class has and was reported as one the core
        could not carry — a fabricated finding with `*]` in its cause."""
        self.assertEqual(rc._path_steps("creators[*].affiliations"),
                         ["creators", "affiliations"])
        self.assertEqual(rc._path_steps("a[*][0].b[12].c"), ["a", "b", "c"])
        declared, ranges = rc.declared_slots(), rc.declared_ranges()
        for path in ("creators[*].name", "creators[*].affiliations", "instances[*].notes"):
            with self.subTest(path):
                self.assertTrue(rc._core_declares(path, declared, ranges))
                # the broken form was a step literally named `*]`
                self.assertNotIn("declares no `*]`",
                                 rc._core_cannot_hold_cause(path, declared, ranges))

    def test_the_walk_can_narrow_the_root_test_and_never_widen_it(self):
        """#994 round 1, M2. The checker's failure direction is silencing, so
        a `ranges` map that disagreed with `declared` — stale, or a caller
        mixing two schemas — must not be able to answer True where the root
        test says False. The root gate stands whatever the ranges say."""
        generous = {"CoreDataset": {"anything": None, "keywords": None}}
        self.assertFalse(rc._core_declares("anything", {"CoreDataset": set()}, generous))
        self.assertFalse(rc._core_declares("keywords", {"CoreDataset": {"other"}}, generous))
        self.assertIn("the core class declares no `keywords` slot",
                      rc._core_cannot_hold_cause("keywords", {"CoreDataset": {"other"}}, generous))
        # and it still narrows
        self.assertFalse(rc._core_declares("resources[0].subsets", NESTED_DECLARED, RANGES))

    def test_a_core_schema_with_no_CoreDataset_is_refused(self):
        with self.assertRaises(ValueError):
            rc._core_declares("keywords", {"Dataset": {"keywords"}}, RANGES)

    def test_the_cause_names_the_step_and_the_class_that_lacks_it(self):
        self.assertIn("the core class declares no `file_collections` slot",
                      rc._core_cannot_hold_cause("file_collections", NESTED_DECLARED, RANGES))
        self.assertIn("`CoreDataset` declares no `file_collections` slot",
                      rc._core_cannot_hold_cause("resources[0].file_collections", NESTED_DECLARED, RANGES))
        self.assertIn("`CoreDistribution` declares no `keywords` slot",
                      rc._core_cannot_hold_cause("distributions[0].keywords", NESTED_DECLARED, RANGES))

    def test_without_ranges_there_is_no_nested_cause_to_give(self):
        """The sentence never claims a precision the walk did not have. With
        no ranges the root test is the whole answer: a path whose root the
        core declares is holdable and carries no cause at all, and only a
        missing root produces one, naming the root."""
        self.assertEqual(
            rc._core_cannot_hold_cause("resources[0].file_collections", NESTED_DECLARED, None), "")
        cause = rc._core_cannot_hold_cause("file_collections", NESTED_DECLARED, None)
        self.assertIn("the core class declares no `file_collections` slot", cause)
        self.assertNotIn("CoreDataset", cause)

    def test_the_real_schema_agrees_on_the_two_divergences_the_issue_names(self):
        """Against the committed schema, not the fixture: `resources` recurses
        into `CoreDataset` and `distributions` into `CoreDistribution`."""
        declared, ranges = rc.declared_slots(), rc.declared_ranges()
        self.assertEqual(ranges["CoreDataset"]["resources"], "CoreDataset")
        self.assertEqual(ranges["CoreDataset"]["distributions"], "CoreDistribution")
        self.assertTrue(rc._core_declares("resources[0].keywords", declared, ranges))
        self.assertFalse(rc._core_declares("resources[0].subsets", declared, ranges))
        self.assertFalse(rc._core_declares("resources[0].file_collections", declared, ranges))
        # and the root test, which is what shipped before, says otherwise
        self.assertTrue(rc._core_declares("resources[0].subsets", declared))


class CoreCannotHoldEndToEndTest(Harness):
    """The cause as a reader meets it, on a `both` row (#994)."""

    def check_with_ranges(self, markdown, full, core):
        import tempfile
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "r.md"
        path.write_text(markdown, encoding="utf-8")
        return check_report(path, full, core, NESTED_DECLARED, ranges=RANGES)

    TABLE = ("## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n")

    def test_a_nested_both_row_names_the_class_that_cannot_carry_it(self):
        full = {"resources": [{"file_collections": [{"id": "x"}]}]}
        for slot in ("resources[0].file_collections", "resources[*].file_collections",
                     "resources.file_collections"):
            with self.subTest(slot=slot):
                md = self.TABLE + f"| `{slot}` | retained | both | kept |\n"
                b = self.check_with_ranges(md, full, {"keywords": ["a"]})
                (f,) = [x for x in b["findings"] if x["slot"] == slot]
                self.assertIn("`CoreDataset` declares no `file_collections` slot", f["detail"])
                self.assertEqual(b["claims_core_cannot_hold"], 1)

    def test_an_unpopulated_implicit_list_path_is_not_a_core_schema_cause(self):
        for child in ({}, {"file_collections": []}, {"file_collections": None}):
            with self.subTest(child=child):
                md = self.TABLE + "| `resources.file_collections` | retained | both | kept |\n"
                b = self.check_with_ranges(md, {"resources": [child]}, {})
                self.assertEqual(b["claims_core_cannot_hold"], 0)
                self.assertTrue(b["findings"])
                self.assertNotIn("declares no", b["findings"][0]["detail"])

    def test_a_nested_row_the_core_can_carry_is_a_plain_contradiction(self):
        """Not every nested `both` row is a schema matter: where the core
        could carry it and does not, the two records disagree."""
        full = {"resources": [{"keywords": ["a"]}]}
        md = self.TABLE + "| `resources[0].keywords` | retained | both | kept |\n"
        b = self.check_with_ranges(md, full, {"keywords": ["a"]})
        (f,) = [x for x in b["findings"] if x["slot"] == "resources[0].keywords"]
        self.assertNotIn("declares no", f["detail"])
        self.assertEqual(b["claims_core_cannot_hold"], 0)


class CorePathVerdictTest(unittest.TestCase):
    """Three answers, not two (#994 round 1, S3). A path the core cannot
    carry and a path no class can carry are different things, and only the
    first is the core's fault."""

    def test_a_step_through_a_scalar_is_not_the_cores_fault(self):
        for path in ("keywords[0].anything", "keywords.anything", "notes[0].x"):
            with self.subTest(path):
                verdict, cause = rc._core_path_verdict(path, NESTED_DECLARED, RANGES)
                self.assertEqual(verdict, rc.NOT_A_PATH)
                self.assertIn("holds a value, not an object", cause)
                # the old text named an empty class and gave advice that
                # cannot help: the full record's slot is equally scalar
                self.assertNotIn("no `` class", cause)
                self.assertNotIn("must name `full`", cause)

    def test_a_step_the_core_lacks_is_the_cores_fault_and_says_so(self):
        verdict, cause = rc._core_path_verdict("resources[0].subsets", NESTED_DECLARED, RANGES)
        self.assertEqual(verdict, rc.CORE_CANNOT_HOLD)
        self.assertIn("must name `full`", cause)

    def test_a_holdable_path_carries_no_cause(self):
        self.assertEqual(rc._core_path_verdict("resources[0].keywords", NESTED_DECLARED, RANGES),
                         (rc.HOLDABLE, ""))

    def test_an_empty_path_names_no_slot(self):
        verdict, cause = rc._core_path_verdict("", NESTED_DECLARED, RANGES)
        self.assertEqual(verdict, rc.NOT_A_PATH)
        self.assertIn("names no slot", cause)

    def test_a_dotted_digit_is_a_step_and_a_subscript_is_not(self):
        """#994 round 1, S2: filtering digits from the flattened tokens
        dropped a dotted `0` as though it were an index. No slot is named
        that today; a quiet behaviour change is still one."""
        self.assertEqual(rc._path_steps("0"), ["0"])
        self.assertEqual(rc._path_steps("a.0.b"), ["a", "0", "b"])
        self.assertEqual(rc._path_steps("a[0].b[*].c"), ["a", "b", "c"])

    def test_the_scalar_case_needs_a_schema_invalid_full_record(self):
        """Worth pinning, because it bounds how much the S3 fix mattered.
        The cause is only consulted where the *full* record carries a
        populated value at the path. `resolve` walks the parsed record with
        no schema awareness, so nothing can be populated under a slot the
        full record holds as a scalar — and for a schema-valid record that
        is every slot the core schema declares scalar. A row like
        `keywords[0].anything` is then a plain contradiction, with no cause
        and nothing counted. Only a full record that violates its own
        schema reaches the sentence through here (#994 round 2, S2); the
        companion test below is that record."""
        import tempfile
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "r.md"
        path.write_text("## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n"
                        "| `keywords[0].anything` | retained | both | kept |\n", encoding="utf-8")
        b = check_report(path, {"keywords": ["a"]}, {"keywords": ["a"]},
                         NESTED_DECLARED, ranges=RANGES)
        (f,) = [x for x in b["findings"] if x["slot"] == "keywords[0].anything"]
        self.assertEqual(f["detail"], "report says retained; the both record does not carry it")
        self.assertEqual(b["claims_core_cannot_hold"], 0)

    def test_a_full_record_that_breaks_its_schema_does_reach_the_scalar_cause(self):
        """The bound above is on schema-valid records, not on the entry
        point. Nothing validates `full` before `check_report` reads it, and
        `resolve` asks only whether the value it is standing on is a dict
        or a list. A full record holding objects under a slot the core
        schema declares scalar resolves the path, reaches the verdict, and
        gets the sentence describing the core schema's declared range.
        It remains a finding, excluded from `claims_core_cannot_hold`
        (#994 round 2, S2)."""
        import tempfile
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "r.md"
        path.write_text("## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n"
                        "| `keywords[0].anything` | retained | both | kept |\n", encoding="utf-8")
        b = check_report(path, {"keywords": [{"anything": "x"}]}, {"keywords": ["a"]},
                         NESTED_DECLARED, ranges=RANGES)
        (f,) = [x for x in b["findings"] if x["slot"] == "keywords[0].anything"]
        self.assertIn("`keywords` holds a value, not an object", f["detail"])
        self.assertEqual(b["claims_core_cannot_hold"], 0)
