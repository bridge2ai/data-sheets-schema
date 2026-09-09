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
        self.assertTrue(REPORT_CLAIMS_INSTRUMENT.startswith("v5"),
                        REPORT_CLAIMS_INSTRUMENT)
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

    def check_with(self, markdown, snapshot, full=None, core=None):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "r.md"
        path.write_text(markdown, encoding="utf-8")
        return check_report(path, full or {}, core or {}, DECLARED, snapshot=snapshot)

    def test_a_slot_the_snapshot_carried_and_the_record_dropped_with_no_row_is_a_finding(self):
        snap = {"keywords": ["a"], "regulatory_restrictions": {"regulatory_restrictions": "a legal framework"}}
        full = {"keywords": ["a"]}
        b = self.check_with(self.TABLE, snap, full=full, core=full)
        self.assertEqual([(f["kind"], f["slot"], f["record"]) for f in b["findings"]],
                         [("removal_not_recorded", "regulatory_restrictions", "full")])
        self.assertTrue(b["snapshot_checked"])
        self.assertEqual(b["removals_unrecorded"], ["regulatory_restrictions"])
        self.assertEqual(b["removals_unrecorded_count"], 1)
        self.assertIn("add a `removed` row or restore the value", b["findings"][0]["detail"])

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

    def test_a_snapshot_diff_without_a_table_lists_and_does_not_find(self):
        snap = {"keywords": ["a"], "publisher": "NIH"}
        b = self.check_with("## Changes\n\nProse only, no table.\n", snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual(b["findings"], [])
        self.assertEqual(b["removals_unrecorded"], ["publisher"])
        self.assertEqual(b["removals_unrecorded_count"], 1)
        self.assertIn("no dispositions table", b["snapshot_basis"])
        b = self.check_with(self.TABLE, snap, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertEqual([f["slot"] for f in b["findings"]], ["publisher"])
        self.assertEqual(b["snapshot_basis"], "unrecorded removals are findings")

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

    def test_the_instrument_is_v5(self):
        b = self.check(self.TABLE, full={"keywords": ["a"]}, core={"keywords": ["a"]})
        self.assertTrue(b["instrument"].startswith("v5 (#1054)"))
        self.assertIn("v4 (#1122)", b["instrument"])
