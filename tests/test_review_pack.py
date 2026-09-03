"""The review pack is deterministic, complete, and its check is affirmative (#787)."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import review_pack as rp

INSTRUCTION = """Generate paired full and core D4D records for the P project.

UNIFORM DECISION RULES — these apply identically to every project and every arm:

- Populate a slot only where the declared bundle supports it. Prefer omission
  over inference.
- `Dataset` admits one referent.

--- ADDED IN v2 ---

- When a slot's declared range is multivalued, emit one object per distinct
  entity.

--- END ADDED IN v2 ---

RETURN: full slot count.
"""


class Rules(unittest.TestCase):
    def test_rule_bullets_are_extracted_with_their_block(self):
        rules = rp.rules_from(INSTRUCTION)
        self.assertEqual([r["block"] for r in rules], ["uniform", "uniform", "v2"])
        self.assertTrue(rules[0]["text"].startswith("Populate a slot only where"))
        self.assertIn("over inference", rules[0]["text"])          # continuation joined
        self.assertEqual([r["id"] for r in rules], ["rule-01", "rule-02", "rule-03"])
        self.assertEqual(rp.rules_from("no rules here\n- not a rule\n"), [])


class ValueAt(unittest.TestCase):
    def test_an_index_into_a_collapsed_string_does_not_resolve_to_a_character(self):
        rec = {"a": [{"b": "collapsed into one string"}], "c": "xyz"}
        self.assertEqual(rp._value_at(rec, "a[0].b"), "collapsed into one string")
        self.assertEqual(rp._value_at(rec, "a[0].b[3]"), rp.UNRESOLVED)      # not "l"
        self.assertEqual(rp._value_at(rec, "c[0]"), rp.UNRESOLVED)           # not "x"
        self.assertEqual(rp._value_at(rec, "a[5].b"), rp.UNRESOLVED)
        self.assertEqual(rp._value_at(rec, "a[0].zz"), rp.UNRESOLVED)
        # a genuine null leaf is null, not unresolved (#808)
        self.assertIsNone(rp._value_at({"n": None}, "n"))


class IdSlots(unittest.TestCase):
    def test_forced_and_optional_mints_are_told_apart(self):
        """#803: File/FileCollection/DataSubset ids are schema-forced;
        Creator ids are a choice. The pack must say which is which."""
        full = {"conforms_to_class": "Dataset", "id": "doi:x",
                "file_collections": [{"id": "doi:x#a", "resources": [{"id": "doi:10.999/external"}]}],
                "subsets": [{"id": "doi:x#train"}],
                "creators": [{"id": "doi:x#p1"}]}
        entries, gap = rp._id_slots(full)
        self.assertIsNone(gap)
        by = {e["path"]: e for e in entries}
        self.assertNotIn("id", by)                            # the record's own id is exempt
        self.assertTrue(by["file_collections[0].id"]["forced"])
        self.assertEqual(by["file_collections[0].id"]["class"], "FileCollection")
        self.assertTrue(by["subsets[0].id"]["forced"])
        self.assertFalse(by["creators[0].id"]["forced"])
        # minted separates a labelled part from a world-facing reference (#823)
        self.assertTrue(by["file_collections[0].id"]["minted"])
        self.assertTrue(by["creators[0].id"]["minted"])
        self.assertFalse(by["file_collections[0].resources[0].id"]["minted"])   # a real DOI
        # a path the walk cannot resolve is named, not guessed
        e2, _ = rp._id_slots({"conforms_to_class": "Dataset", "nonsuch": [{"id": "x#y"}]})
        self.assertEqual(e2, [{"path": "nonsuch[0].id", "resolvable": False}])
        # an unknown root class and an empty record are named gaps (#827)
        self.assertIn("not in the schema", rp._id_slots({"a": 1}, root_class="NoSuchClass")[1])


class Pack(unittest.TestCase):
    def _run(self, tmp):
        """A minimal run: bundle, manifest, receipt, records, provenance."""
        from data_sheets_schema.chunking import build_manifest, dump_manifest
        from tests.test_receipts import BUNDLE, FULL, _receipt
        tmp = Path(tmp)
        bundle = tmp / "P_preprocessed.txt"; bundle.write_text(BUNDLE, encoding="utf-8")
        manifest = tmp / "P_chunks.yaml"; manifest.write_text(dump_manifest(build_manifest(bundle)))
        core = tmp / "d4d_concatenated/claudecode_agent_core/L"; full_dir = tmp / "d4d_concatenated/claudecode_agent/L"
        core.mkdir(parents=True); full_dir.mkdir(parents=True)
        (full_dir / "P_d4d.yaml").write_text(yaml.safe_dump(FULL))
        (core / "P_d4d_core.yaml").write_text("id: x\n")
        md5 = hashlib.md5(BUNDLE.encode()).hexdigest()
        rec = _receipt(md5)          # drop two receipts so the record has receiptless leaves
        rec["chunks"][1]["extracted"] = [p for p in rec["chunks"][1]["extracted"] if p["slot"] not in ("title", "keywords")]
        (core / "P_coverage_receipt.yaml").write_text(yaml.safe_dump(rec))
        instr = tmp / "instruction.md"; instr.write_text(INSTRUCTION)
        prov = core / "P_provenance.yaml"
        prov.write_text("# header\n" + yaml.safe_dump({
            "run": {"label": "L", "project": "P", "method": "claudecode_agent"},
            "prompts": {"request": {"sha256": hashlib.sha256(INSTRUCTION.encode()).hexdigest()}},
            "inputs": {"bundle_path": str(bundle), "bundle_md5": md5,
                       "chunks": {"path": str(manifest), "chunk_count": 3}},
            "receipts": {"checked": True, "slots": {"without_receipt": ["keywords", "title"],
                                                     "reshaped_by_reconcile": ["funders[0].name"]}}}))
        return prov, instr

    def test_the_pack_is_complete_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = self._run(tmp)
            p1 = rp.build_pack(prov, instr); p2 = rp.build_pack(prov, instr)
            self.assertEqual(p1, p2)
            kinds = {}
            for i in p1["items"]:
                kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
            self.assertEqual(kinds["chunk_nothing_relevant"], 2)          # c001, c003 in the fixture receipt
            self.assertEqual(kinds["rule"], 3)
            # receiptless from the record and receipt themselves, not the record's list (#790)
            self.assertEqual(kinds["slot_receiptless"], p1["counts"]["receiptless_slots_total"])
            self.assertEqual(kinds["slot_receiptless"], 2); self.assertEqual(kinds["slot_reshaped"], 1)
            self.assertEqual(sorted(i["slot"] for i in p1["items"] if i["kind"] == "slot_receiptless"), ["keywords", "title"])
            self.assertEqual(p1["counts"]["sampled"]["receiptless"], kinds["slot_receiptless"])
            self.assertTrue(Path(p1["instruction"]["path"]).read_text().startswith("Generate paired"))
            self.assertNotIn("sha256", p1["provenance"]); self.assertEqual(len(p1["bundle"]["chunks"]), 3)
            self.assertGreaterEqual(kinds["slot_receipted"], 1)
            self.assertIn("id_slots", p1); self.assertIn("entries", p1["id_slots"])   # #803
            self.assertIn("pair_warning", p1["verdicts"])                              # #691
            chunk = next(i for i in p1["items"] if i["id"] == "chunk-c003")
            self.assertEqual(chunk["source"], "b.txt"); self.assertEqual(chunk["agent_reason"], "references only")
            slot = next(i for i in p1["items"] if i["kind"] == "slot_receipted")
            self.assertIn("snippet", slot["receipts"][0]); self.assertIn("lines", slot["receipts"][0]); self.assertIn("value", slot)
            self.assertIn("sha256 matches", p1["instruction"]["basis"]); self.assertEqual(p1["gaps"], [])
            # a different sample size changes the pack; the same one does not
            self.assertNotEqual(rp.build_pack(prov, instr, {"receipted_slots": 1})["items"], p1["items"])

    def test_a_pair_with_matched_distributions_yields_a_reviewable_item(self):
        """#691: the checker re-runs at pack time and its warning becomes an
        item — and when it runs, its failure-gap is absent."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = self._run(tmp)
            core = Path(tmp) / "d4d_concatenated/claudecode_agent_core/L/P_d4d_core.yaml"
            core.write_text(yaml.safe_dump({"id": "https://x/ds",
                                            "distributions": [{"id": "https://x/ds#fc1", "name": "raw"}]}))
            pack = rp.build_pack(prov, instr)
            pw = [i for i in pack["items"] if i["kind"] == "pair_warning"]
            self.assertGreaterEqual(len(pw), 1)
            self.assertIn("semantically", pw[0]["question"])
            self.assertFalse([g for g in pack["gaps"] if "pair" in g])

    def test_the_written_pack_has_no_yaml_aliases(self):
        """Chunk spans are shared between bundle.chunks and the items; a
        default dumper writes the second as `*id001` (#810)."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = self._run(tmp)
            out, _ = rp.write_pack(prov, instr)
            text = Path(out).read_text()
            self.assertNotIn("&id", text); self.assertNotIn("*id", text)
            self.assertIn("lines:", text)

    def test_gaps_are_named_not_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = self._run(tmp)
            p = rp.build_pack(prov, None)                       # no file, no spec in the record
            self.assertEqual(p["rules"], []); self.assertTrue(any(g.startswith("instruction") for g in p["gaps"]))
            other = Path(tmp) / "other.md"; other.write_text("edited\n")
            self.assertIn("does NOT match", rp.build_pack(prov, other)["instruction"]["basis"])


class PairWarnings(unittest.TestCase):
    def test_the_vocabulary_counts_divergent_as_adverse_and_consistent_as_not(self):
        """#691: a semantic-review-required warning becomes a reviewable item."""
        self.assertIn("pair_warning", rp.VERDICTS)
        self.assertIn("consistent", rp.AFFIRMATIVE)
        self.assertEqual(rp.ADVERSE["pair_warning"], ("divergent",))

    def test_an_answered_pair_item_counts(self):
        pack = {"_sha256": "abc", "items": [{"id": "pair-01", "kind": "pair_warning"}]}
        good = rp.check_review(pack, {"pack_sha256": "abc", "items": [
            {"id": "pair-01", "verdict": "consistent", "evidence": "file_collections[0] vs distributions[0]"}]})
        self.assertEqual((good["adverse"], good["cannot_tell"]), (0, 0))
        bad = rp.check_review(pack, {"pack_sha256": "abc", "items": [
            {"id": "pair-01", "verdict": "divergent", "evidence": "counts disagree"}]})
        self.assertEqual(bad["adverse"], 1)


class Agree(unittest.TestCase):
    PACK = {"_sha256": "abc", "items": [
        {"id": "slot-001", "kind": "slot_receipted"}, {"id": "slot-002", "kind": "slot_receipted"},
        {"id": "slot-003", "kind": "slot_receiptless"}, {"id": "rule-01", "kind": "rule"}]}

    def _rev(self, verdicts):
        return {"pack_sha256": "abc", "items": [{"id": i, "verdict": v}
                for i, v in zip(("slot-001", "slot-002", "slot-003", "rule-01"), verdicts)]}

    def test_kappa_and_disagreements_are_computed_on_the_trichotomy(self):
        a = self._rev(("supported", "weak", "inferred", "followed"))
        b = self._rev(("supported", "supported", "inferred", "violated"))
        r = rp.agree(self.PACK, a, b)
        self.assertEqual(r["paired_items"], 4)
        self.assertEqual(r["percent_class_agreement"], 50.0)      # 2 of 4 same class
        self.assertEqual(r["percent_exact_agreement"], 50.0)
        self.assertEqual({d["id"] for d in r["disagreements"]}, {"slot-002", "rule-01"})
        self.assertEqual((r["adverse_a"], r["adverse_b"], r["adverse_delta"]), (2, 2, 0))
        self.assertIsNotNone(r["kappa_class"])
        # weak vs unsupported: same class, not exact — agreement splits
        r2 = rp.agree(self.PACK, self._rev(("supported", "weak", "inferred", "followed")),
                      self._rev(("supported", "unsupported", "inferred", "followed")))
        self.assertEqual(r2["percent_class_agreement"], 100.0)
        self.assertEqual(r2["percent_exact_agreement"], 75.0)

    def test_all_one_class_makes_kappa_undefined_not_zero(self):
        a = self._rev(("supported", "supported", "bundle_supports", "followed"))
        r = rp.agree(self.PACK, a, a)
        self.assertEqual(r["percent_class_agreement"], 100.0); self.assertIsNone(r["kappa_class"])

    def test_reviews_of_different_packs_refuse_to_pair(self):
        with self.assertRaises(ValueError):
            rp.agree(self.PACK, {"pack_sha256": "zzz", "items": []}, self._rev(("supported",) * 4))

    def test_a_missing_verdict_is_unanswered_not_adverse(self):
        """#861: {'id': ...} with no verdict must not count as a rating."""
        a = self._rev(("supported", "weak", "inferred", "followed"))
        b = {"pack_sha256": "abc", "items": [{"id": "slot-001", "verdict": "supported"},
                                             {"id": "slot-002"},
                                             {"id": "slot-003", "verdict": None},
                                             {"id": "rule-01", "verdict": "followed"}]}
        r = rp.agree(self.PACK, a, b)
        self.assertEqual(r["paired_items"], 2)
        self.assertEqual(r["unanswered_in_either"], ["slot-002", "slot-003"])
        self.assertEqual(r["adverse_b"], 0)

    def test_unanswered_items_are_excluded_and_named(self):
        a = self._rev(("supported", "weak", "inferred", "followed"))
        b = {"pack_sha256": "abc", "items": a["items"][:2]}
        r = rp.agree(self.PACK, a, b)
        self.assertEqual(r["paired_items"], 2); self.assertEqual(r["unanswered_in_either"], ["slot-003", "rule-01"])


class Check(unittest.TestCase):
    PACK = {"_sha256": "abc", "items": [
        {"id": "chunk-c001", "kind": "chunk_nothing_relevant"},
        {"id": "slot-001", "kind": "slot_receipted"},
        {"id": "rule-01", "kind": "rule"}]}

    def test_every_item_once_with_a_vocabulary_verdict_and_evidence(self):
        good = {"pack_sha256": "abc", "items": [
            {"id": "chunk-c001", "verdict": "confirmed", "evidence": "lines 1-18 header"},
            {"id": "slot-001", "verdict": "misread", "evidence": "line 12"},
            {"id": "rule-01", "verdict": "followed", "evidence": "funders[0]"}]}
        b = rp.check_review(self.PACK, good)
        self.assertEqual((b["items_answered"], b["items_total"], b["adverse"], b["cannot_tell"]), (3, 3, 1, 0))
        self.assertEqual(b["findings"], []); self.assertIn("3/3 answered", b["summary"])
        bad = {"pack_sha256": "zzz", "items": [
            {"id": "chunk-c001", "verdict": "fine", "evidence": "x"},
            {"id": "chunk-c001", "verdict": "confirmed", "evidence": "x"},
            {"id": "slot-001", "verdict": "supported"},
            {"id": "slot-999", "verdict": "supported", "evidence": "x"}]}
        b = rp.check_review(self.PACK, bad)
        kinds = [f["kind"] for f in b["findings"]]
        for k in ("verdict_not_in_vocabulary", "item_answered_twice", "verdict_without_evidence",
                  "answer_for_unknown_item", "review_of_another_pack"):
            self.assertIn(k, kinds, k)
        self.assertEqual(b["unanswered"], ["rule-01"])
        nohash = rp.check_review(self.PACK, {"items": [{"id": "rule-01", "verdict": "cannot_tell", "evidence": "no schema"}]})
        self.assertEqual(nohash["cannot_tell"], 1)
        self.assertIn("review_without_pack_hash", [f["kind"] for f in nohash["findings"]])      # #792
        # every non-affirmative, non-cannot_tell verdict counts as adverse (#792/#793)
        for kind, verdicts in rp.VERDICTS.items():
            for v in verdicts:
                self.assertEqual(v in rp.ADVERSE[kind], v not in rp.AFFIRMATIVE and v != "cannot_tell", (kind, v))
        self.assertIn("weak", rp.ADVERSE["slot_receipted"]); self.assertIn("inferred", rp.ADVERSE["slot_receiptless"])


if __name__ == "__main__":
    unittest.main()


class IdentityJoin(unittest.TestCase):
    def test_a_receipted_item_follows_its_entry_and_the_receiptless_set_excludes_it(self):
        """#899: with a phase-1 snapshot the pack joins receipt paths to the
        final record by entry identity; without one it says so."""
        from tests.test_receipts import FULL
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            core = prov.parent
            full_p = Path(tmp) / "d4d_concatenated/claudecode_agent/L/P_d4d.yaml"
            j0 = rp.build_pack(prov, instr)["receipt_join"]
            self.assertEqual(j0["basis"], "index"); self.assertIn("no phase-1 snapshot", j0["reason"])
            (core / "intermediate").mkdir()
            (core / "intermediate/P_full.yaml").write_text(yaml.safe_dump(FULL))
            moved = {**FULL, "funders": [{"id": "https://x/ds#funder-0", "name": "Other"}, FULL["funders"][0]]}
            full_p.write_text(yaml.safe_dump(moved))
            p = rp.build_pack(prov, instr, {"receipted_slots": 50})
            self.assertEqual(p["receipt_join"]["basis"], "identity"); self.assertEqual(p["gaps"], [])
            self.assertEqual(p["pack_version"], 4)
            grant = next(i for i in p["items"] if i.get("slot") == "funders[0].grant_id")
            self.assertEqual(grant["resolved_path"], "funders[1].grant_id")
            self.assertEqual(grant["resolution"], "by_id"); self.assertEqual(grant["value"], "OT2OD032644")
            self.assertIn("followed by identity", grant["question"])
            receiptless = {i["slot"] for i in p["items"] if i["kind"] == "slot_receiptless"}
            self.assertIn("funders[0].name", receiptless)            # the inserted entry
            self.assertNotIn("funders[1].name", receiptless)         # the moved, receipted one


class GoneEntries(unittest.TestCase):
    def test_a_receipt_whose_entry_is_gone_shows_unresolved_and_covers_nothing(self):
        """#907 review A/B: never the value of whatever now sits at the index;
        a path the snapshot never had is not credited by the pack either."""
        from tests.test_receipts import FULL
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            core = prov.parent
            full_p = Path(tmp) / "d4d_concatenated/claudecode_agent/L/P_d4d.yaml"
            (core / "intermediate").mkdir()
            (core / "intermediate/P_full.yaml").write_text(yaml.safe_dump(FULL))
            replaced = {**FULL, "funders": [{"id": "https://x/ds#funder-9", "name": "Someone Else", "grant_id": "OTHER"}]}
            full_p.write_text(yaml.safe_dump(replaced))
            p = rp.build_pack(prov, instr, {"receipted_slots": 50})
            grant = next(i for i in p["items"] if i.get("slot") == "funders[0].grant_id")
            self.assertIsNone(grant["resolved_path"]); self.assertEqual(grant["resolution"], "entry_dropped")
            self.assertEqual(grant["value"], rp.UNRESOLVED)
            receiptless = {i["slot"] for i in p["items"] if i["kind"] == "slot_receiptless"}
            self.assertIn("funders[0].grant_id", receiptless)          # the replacement is unreceipted
            (core / "intermediate/P_full.yaml").write_text(yaml.safe_dump({**FULL, "funders": []}))
            full_p.write_text(yaml.safe_dump(FULL))
            p2 = rp.build_pack(prov, instr, {"receipted_slots": 50})
            grant2 = next(i for i in p2["items"] if i.get("slot") == "funders[0].grant_id")
            self.assertEqual(grant2["resolution"], "not_in_snapshot"); self.assertEqual(grant2["value"], rp.UNRESOLVED)
            self.assertIn("funders[0].grant_id", {i["slot"] for i in p2["items"] if i["kind"] == "slot_receiptless"})


class RegistryLabels(unittest.TestCase):
    def test_a_values_from_curie_carries_its_pinned_label(self):
        """#912: the digest shows the model `id=name`; the pack shows the reviewer the same."""
        from data_sheets_schema.schema_digest import vocabularies
        topics = vocabularies().get("B2AI_TOPIC") or {}
        self.assertTrue(topics, "the pinned vocabulary must be present")
        curie, label = next(iter(topics.items()))
        self.assertEqual(rp._registry_label(curie), label)
        self.assertIsNone(rp._registry_label("B2AI_TOPIC:999999"))
        self.assertIsNone(rp._registry_label("plain text")); self.assertIsNone(rp._registry_label(None))
        from tests.test_receipts import FULL
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            full_p = Path(tmp) / "d4d_concatenated/claudecode_agent/L/P_d4d.yaml"
            full_p.write_text(yaml.safe_dump({**FULL, "data_topic": [curie]}))
            p = rp.build_pack(prov, instr, {"receiptless_slots": 50})
            item = next(i for i in p["items"] if str(i.get("slot", "")).startswith("data_topic"))
            self.assertEqual(item["value_label"], label)


class ReferenceAttributes(unittest.TestCase):
    def test_the_pack_names_the_reference_attributes(self):
        """#805/#916: the reviewer is told which class-ranged attributes take a
        string, so rule-08 is not charged on a Person reference."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            p = rp.build_pack(prov, instr)
            entries = p["reference_attributes"]["entries"]
            self.assertIn("Creator.principal_investigator → Person (reference — a string, not an object)", entries)
            self.assertEqual(len(entries), 8)
            self.assertIn("not inlined", p["reference_attributes"]["note"])
