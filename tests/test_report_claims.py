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

DECLARED = {"Dataset": {"file_collections", "distributions", "keywords"},
            "CoreDataset": {"distributions", "source_caveats", "notes",
                            "errata", "collection_timeframes"},
            "CoreDistribution": {"path", "md5", "format", "media_type"}}


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
        md = ("## `sensitive_elements`\n\n`description` was removed from all eleven objects. "
              "The content was redistributed into declared fields.\n\n"
              "The second object was removed. The single remaining object asserts `false`.\n")
        self.assertEqual(self.kinds(md), [])

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


if __name__ == "__main__":
    unittest.main()
