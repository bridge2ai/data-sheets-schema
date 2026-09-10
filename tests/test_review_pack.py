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

    def test_a_fragment_on_another_base_is_constructed_not_stated(self):
        """#901: the AI_READI v7 rep1 file_collections ids are fragments on
        the attested fairhub page URL. `minted: false` filed them with the
        DOIs; `origin` tells a label the record built from a reference it
        copied, and `base_in_bundle` whether the base is attested."""
        full = {"conforms_to_class": "Dataset", "id": "doi:10.60775/fairhub.3",
                "file_collections": [{"id": "https://fairhub.io/datasets/3#cardiac_ecg",
                                      "resources": [{"id": "doi:10.999/external"}]},
                                     {"id": "doi:10.60775/fairhub.3#own"},
                                     {"id": "urn:aireadi:thing"}],
                "creators": [{"id": "https://orcid.org/0000-0002-1825-0097"},
                             {"id": "https://example.org/people#alice"}]}
        bundle = "Dataset page: https://fairhub.io/datasets/3 (v2.0.0)\n"
        by = {e["path"]: e for e in rp._id_slots(full, bundle_text=bundle)[0]}
        fc = by["file_collections[0].id"]
        self.assertEqual(fc["origin"], "constructed")
        self.assertFalse(fc["minted"])                                  # unchanged boolean
        self.assertEqual(fc["base"], "https://fairhub.io/datasets/3")
        self.assertTrue(fc["base_in_bundle"])
        self.assertEqual(by["file_collections[1].id"]["origin"], "minted")
        self.assertEqual(by["file_collections[2].id"]["origin"], "minted")   # a urn
        self.assertEqual(by["file_collections[0].resources[0].id"]["origin"], "stated")
        self.assertNotIn("base", by["file_collections[0].resources[0].id"])
        self.assertEqual(by["creators[0].id"]["origin"], "stated")
        alice = by["creators[1].id"]
        self.assertEqual(alice["origin"], "constructed")
        self.assertFalse(alice["base_in_bundle"])                       # invented base
        # without the bundle the attestation is unknown, never guessed
        self.assertIsNone({e["path"]: e for e in rp._id_slots(full)[0]}["file_collections[0].id"]["base_in_bundle"])
        # a bare "#x" has no base: it is not constructed on anything
        self.assertEqual(rp._id_origin("#x", "doi:y"), ("stated", None))
        self.assertEqual(set(rp.ID_ORIGINS), {e["origin"] for e in rp._id_slots(full)[0]})


class Pack(unittest.TestCase):
    def _run(self, tmp, full=None, bundle_extra="", drift_after=False, drop_bundle=False):
        """A minimal run: bundle, manifest, receipt, records, provenance.
        `full` replaces the record; `bundle_extra` is appended to the bundle
        before its md5 is recorded; `drift_after` rewrites the bundle after
        the record pinned it; `drop_bundle` removes the file."""
        from data_sheets_schema.chunking import build_manifest, dump_manifest
        from tests.test_receipts import BUNDLE as _B, FULL as _F, _receipt
        BUNDLE = _B + bundle_extra; FULL = full or _F
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
        if drift_after:
            bundle.write_text(BUNDLE + "\nrewritten after the record pinned it\n", encoding="utf-8")
        if drop_bundle:
            bundle.unlink()
        return prov, instr

    def _constructed_full(self):
        from tests.test_receipts import FULL
        full = yaml.safe_load(yaml.safe_dump(FULL))
        full["file_collections"] = list(full.get("file_collections") or []) + [
            {"id": "https://example.org/landing/7#attested-label", "name": "attested"},
            {"id": "https://nowhere.example/x#invented-label", "name": "invented"}]
        return full

    def test_base_in_bundle_travels_through_build_pack_against_the_bytes_the_record_read(self):
        """#1108 review, findings 4 and 6: the first version's only
        constructed-id test called `_id_slots` directly, and `build_pack`
        read whatever file sat at `bundle_path` with no md5 check."""
        extra = "\nLanding page: https://example.org/landing/7\nSee https://example.org/landing/70 too\n"
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = self._run(tmp, full=self._constructed_full(), bundle_extra=extra)
            p = rp.build_pack(prov, instr)
            by = {e["path"]: e for e in p["id_slots"]["entries"]}
            self.assertEqual(p["id_slots"]["bundle_state"], "current")
            self.assertEqual(p["id_slots"]["record_id"], "https://x/ds")
            self.assertTrue(p["bundle"]["resolved_path"].endswith("P_preprocessed.txt"))
            self.assertTrue(by["file_collections[1].id"]["base_in_bundle"])
            self.assertFalse(by["file_collections[2].id"]["base_in_bundle"])
            self.assertFalse(any("base_in_bundle" in g for g in p["gaps"]))
        with tempfile.TemporaryDirectory() as tmp:                        # drifted: null, and a gap
            prov, instr = self._run(tmp, full=self._constructed_full(), bundle_extra=extra, drift_after=True)
            p = rp.build_pack(prov, instr)
            self.assertTrue(p["id_slots"]["bundle_state"].startswith("bundle drifted (recorded "))
            self.assertTrue(all(e["base_in_bundle"] is None for e in p["id_slots"]["entries"]
                                if e.get("origin") == "constructed"))
            self.assertTrue(any(g.startswith("id_slots.base_in_bundle unavailable: bundle drifted") for g in p["gaps"]))
        with tempfile.TemporaryDirectory() as tmp:                        # not on disk
            prov, instr = self._run(tmp, full=self._constructed_full(), drop_bundle=True)
            p = rp.build_pack(prov, instr)
            self.assertTrue(p["id_slots"]["bundle_state"].startswith("bundle not on disk ("))
            self.assertTrue(any(g.startswith("id_slots.base_in_bundle unavailable: bundle not on disk") for g in p["gaps"]))

    def test_a_prefix_of_a_longer_url_is_not_attestation_and_an_alias_form_is(self):
        """#1108 review, finding 5: of the 11 occurrences of the fairhub page
        in the AI_READI bundle, 10 are inside `…/3/access`; one bare line
        carried the whole claim. And a CURIE base is attested by its
        resolver form (#974 writes the CURIE, a bundle states the URL)."""
        self.assertFalse(rp._base_in("https://fairhub.io/datasets/3", "see https://fairhub.io/datasets/30 and https://fairhub.io/datasets/3/access"))
        self.assertTrue(rp._base_in("https://fairhub.io/datasets/3", "Source URL: https://fairhub.io/datasets/3\n"))
        self.assertTrue(rp._base_in("https://fairhub.io/datasets/3", "(https://fairhub.io/datasets/3)"))
        # a URL ending a sentence is the URL (round 2): `.` continues only when what follows does
        self.assertTrue(rp._base_in("http://integrativemodeling.org", "see http://integrativemodeling.org.\n\nNext"))
        self.assertTrue(rp._base_in("https://datascience.nih.gov/strides", "at https://datascience.nih.gov/strides.\nT"))
        self.assertFalse(rp._base_in("https://a.org/v", "https://a.org/v.1/x"))
        self.assertFalse(rp._base_in("https://a.org/v", "https://a.org/v-2"))
        self.assertFalse(rp._base_in("https://chorus4ai.org/dataset", "https://chorus4ai.org/dataset/"))   # a trailing slash is another resource
        self.assertTrue(rp._base_in("doi:10.18130/V3/HIGT4C", "at https://doi.org/10.18130/V3/HIGT4C today"))
        self.assertTrue(rp._base_in("https://doi.org/10.18130/V3/HIGT4C", "cite doi:10.18130/V3/HIGT4C"))

    def test_origin_edge_cases_from_the_review(self):
        """#1108 review, finding 8."""
        self.assertEqual(rp._id_origin("https://example.org/#", "doi:10.1/rec"), ("stated", None))   # empty fragment
        self.assertEqual(rp._id_origin("#x", "doi:y"), ("stated", None))
        self.assertEqual(rp._id_origin("  https://a.org#b  ", "doi:z"), ("constructed", "https://a.org"))
        # the record's own id in resolver form is a mint, not a label on someone else's identifier
        self.assertEqual(rp._id_origin("https://doi.org/10.60775/fairhub.3#a", "doi:10.60775/fairhub.3"), ("minted", None))
        self.assertEqual(rp._id_origin("doi:10.60775/fairhub.3#a", "https://doi.org/10.60775/fairhub.3"), ("minted", None))
        self.assertEqual(rp._id_origin(["doi:10.1/a#b"], "doi:z"), ("stated", None))
        # paths are case-sensitive; only scheme and host fold (round 2, note 5)
        self.assertEqual(rp._id_origin("https://example.org/Dataset/A#part", "https://example.org/dataset/a")[0], "constructed")
        self.assertEqual(rp._id_origin("HTTPS://EXAMPLE.org/dataset/a#part", "https://example.org/dataset/a")[0], "minted")

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
            self.assertEqual(p["pack_version"], 5)
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
            # none since #805 inlined the five Person slots and the marking
            # follows LinkML's own rule (#927 review); the block stays so a
            # future reference attribute is named to the reviewer
            self.assertEqual(entries, [])
            self.assertIn("not inlined", p["reference_attributes"]["note"])


class APackIsNeverRewrittenUnderItsPin(unittest.TestCase):
    """#1095: a review run regenerated the pack it was reviewing, moving the
    committed file underneath the sha256 its own record attests. The guard
    is on the bytes (#1124 review, SF1): a rewrite that would leave the
    file as it is passes; one that would move it under a live pin — or
    orphan a pin whose pack is gone (MF1), or that cannot read a pin file
    (SF3) — is refused unless forced."""

    SMALLER = {"receipted_slots": 3, "receiptless_slots": 3}   # a different sample: different bytes

    def _pinned(self, tmp, by, name="P_review.yaml"):
        prov, instr = Pack()._run(tmp)
        out, _ = rp.write_pack(prov, instr)
        sha = hashlib.sha256(out.read_bytes()).hexdigest()
        if by == "review":
            (out.parent / name).write_text(yaml.safe_dump({"pack_sha256": sha, "items": []}))
        else:
            text = prov.read_text(); head, body = text.split("\n", 1)
            d = yaml.safe_load(body); d["review"] = {"artifacts": {"pack": {"sha256": sha}}}
            prov.write_text(head + "\n" + yaml.safe_dump(d))
        return prov, instr, out, sha

    def test_a_rewrite_that_would_move_a_pinned_pack_is_refused_and_force_moves_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            self.assertEqual([p["by"] for p in rp.pack_pins(prov)[0]], ["review"])
            with self.assertRaises(rp.PackAttested) as cm:
                rp.write_pack(prov, instr, self.SMALLER)
            self.assertIn("review_of_another_pack", str(cm.exception))
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), sha)     # untouched
            rp.write_pack(prov, instr, self.SMALLER, force=True)                       # deliberate
            self.assertNotEqual(hashlib.sha256(out.read_bytes()).hexdigest(), sha)

    def test_a_byte_identical_rewrite_is_not_a_rewrite(self):
        """The pack is deterministic; regenerating it with the same inputs
        leaves every pin holding, so nothing is refused and nothing is
        warned about (#1124 review, SF1)."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            rp.write_pack(prov, instr)                                                  # no force needed
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), sha)

    def test_a_pack_the_record_pins_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "record")
            self.assertEqual([p["by"] for p in rp.pack_pins(prov)[0]], ["provenance record"])
            with self.assertRaises(rp.PackAttested):
                rp.write_pack(prov, instr, self.SMALLER)

    def test_a_deleted_pack_does_not_delete_the_guard(self):
        """#1124 review, MF1: the agent is told to run `d4d review pack`
        exactly when no pack exists — and every committed pack is behind
        the code, so removing one to get a current one would orphan the
        review beside it silently."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            out.unlink()
            current, stale = rp.pack_pins(prov)
            self.assertEqual(current, []); self.assertEqual([(p["by"], p["pack_on_disk"]) for p in stale], [("review", False)])
            with self.assertRaises(rp.PackAttested):
                rp.write_pack(prov, instr, self.SMALLER)           # would orphan the review's pin
            rp.write_pack(prov, instr)                              # reproduces the pinned bytes: allowed
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), sha)

    def test_an_unreadable_pin_file_fails_closed(self):
        """#1124 review, SF3: a review file that does not parse used to lose
        its pin silently, leaving the pack freely rewritable."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            (out.parent / "P_review_b.yaml").write_text("pack_sha256: [unclosed")
            _, _, unreadable = rp.pack_pins_report(prov)
            self.assertEqual([u["by"] for u in unreadable], ["review"])
            with self.assertRaises(rp.PackAttested) as cm:
                rp.write_pack(prov, instr, self.SMALLER)
            self.assertIn("unreadable", str(cm.exception))

    def test_a_refusal_leaves_the_instruction_file_as_it_found_it(self):
        """#1124 review, MF-R1: building before the guard had `build_pack`
        rewrite `{P}_review_instruction.md` on a refused call, so the
        reviewer read an instruction the pack does not attest."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            ipath = rp.record_paths(prov)["instruction"]
            before = ipath.read_text()
            other = Path(tmp) / "other_instruction.md"
            other.write_text(before + "\nTAMPERED\n")
            with self.assertRaises(rp.PackAttested):
                rp.write_pack(prov, other, self.SMALLER)
            self.assertEqual(ipath.read_text(), before)                                # untouched
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), sha)
            rp.write_pack(prov, other, self.SMALLER, force=True)
            self.assertIn("TAMPERED", ipath.read_text())                               # written with the pack

    def test_build_pack_refuses_the_state_that_writes_nothing_and_returns_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            with self.assertRaises(ValueError):
                rp.build_pack(prov, instr, write_instruction=False)

    def test_the_cli_names_the_record_that_would_not_parse(self):
        import click.testing
        from unittest import mock
        from data_sheets_schema.cli.review import review as review_cli
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            prov.write_text("# header\nreview: [unclosed")
            base = ["pack", "--method", "claudecode_agent", "--label", "L", "--project", "VOICE", "--force",
                    "--instruction", str(instr)]
            with mock.patch("data_sheets_schema.cli.review._provenance", lambda m, l, p: prov):
                r = click.testing.CliRunner().invoke(review_cli, base)
            self.assertNotEqual(r.exit_code, 0)
            self.assertTrue(r.output.startswith(f"Error: {prov} could not be read as YAML"), r.output)   # the record, not PyYAML's mark

    def test_a_broken_core_record_names_itself_in_the_pair_gap(self):
        """#1124 round 6, SF-R6a: the pair-warnings block degrades to a named
        gap; the name must be the file, not the wrapper's class."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            core = rp.record_paths(prov)["core"]
            core.write_text("bad: [unclosed")
            pack = rp.build_pack(prov, instr)
            gaps = [g for g in pack["gaps"] if g.startswith("pair warnings unavailable")]
        self.assertEqual(len(gaps), 1, pack["gaps"])
        self.assertIn(str(core), gaps[0])
        self.assertNotIn("UnreadableYAML", gaps[0])
        self.assertNotIn("\n", gaps[0])                                   # one line, not PyYAML's mark block

    def test_an_unreadable_snapshot_is_not_reported_as_no_snapshot(self):
        """#1124 round 6, SF-R6b: `receipt_join.basis` is what the reviewer reads
        to decide whether an index shift may be scored unsupported; a snapshot
        that exists and will not parse is a gap, not an absence."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            receipt = rp.record_paths(prov)["receipt"]
            snap_dir = receipt.parent / "intermediate"; snap_dir.mkdir(exist_ok=True)
            snap = snap_dir / receipt.name.replace("_coverage_receipt.yaml", "_full.yaml")
            snap.write_text("bad: [unclosed")
            pack = rp.build_pack(prov, instr)
            self.assertEqual(pack["receipt_join"]["basis"], "index")
            self.assertIn("present but unreadable", pack["receipt_join"]["reason"])
            self.assertTrue(any(str(snap) in g for g in pack["gaps"]), pack["gaps"])
            snap.unlink()
            pack = rp.build_pack(prov, instr)
            self.assertIn("no phase-1 snapshot", pack["receipt_join"]["reason"])

    def test_the_cli_names_whichever_file_would_not_parse(self):
        """The pack reads several YAML files; the message names the one that
        failed, not the record by default (#1124 round 5)."""
        import click.testing
        from unittest import mock
        from data_sheets_schema.cli.review import review as review_cli
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            paths = rp.record_paths(prov)
            for broken in ("full", "receipt"):
                path = paths[broken]
                keep = path.read_text()
                path.write_text("bad: [unclosed")
                base = ["pack", "--method", "claudecode_agent", "--label", "L", "--project", "VOICE", "--force",
                        "--instruction", str(instr)]
                with mock.patch("data_sheets_schema.cli.review._provenance", lambda m, l, p: prov):
                    r = click.testing.CliRunner().invoke(review_cli, base)
                path.write_text(keep)
                self.assertNotEqual(r.exit_code, 0, broken)
                self.assertTrue(r.output.startswith(f"Error: {path} could not be read as YAML"), (broken, r.output))

    def test_an_unparsable_provenance_record_is_a_named_refusal(self):
        """#1124 review, SF-R2: `build_pack` re-parsed the record before the
        guard and raised a bare ParserError."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            prov.write_text("# header\nreview: [unclosed")
            with self.assertRaises(rp.PackAttested) as cm:
                rp.write_pack(prov, instr, self.SMALLER)
            self.assertIn("provenance record", str(cm.exception)); self.assertIn("unreadable", str(cm.exception))

    def test_pack_pins_folds_unreadable_into_stale(self):
        """SF-R1: the 2-tuple's docstring promised this and the first
        version dropped them."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            (out.parent / "P_review_b.yaml").write_text("pack_sha256: [unclosed")
            current, stale = rp.pack_pins(prov)
            self.assertEqual([p["by"] for p in current], ["review"])
            self.assertEqual([(p["by"], p["sha256"]) for p in stale], [("review", "unreadable (ParserError)")])

    def test_the_refusal_names_each_pins_class_and_the_callers_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            out.unlink()
            with self.assertRaises(rp.PackAttested) as cm:
                rp.write_pack(prov, instr, self.SMALLER, force_hint="`--force`")
            self.assertIn("its pack is not on disk", str(cm.exception)); self.assertIn("Pass `--force`", str(cm.exception))
            self.assertNotIn("force=True", str(cm.exception))

    def test_runs_check_reads_the_pin_state_from_the_records_location(self):
        """The `d4d runs check` drift branch (SF2), through the function it
        calls: no drift while the pack is the pinned one, `missing` when it
        is gone, `rewritten` after a forced rewrite."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "record")
            self.assertIsNone(rp.pack_pin_state(prov))
            rp.write_pack(prov, instr, self.SMALLER, force=True)
            self.assertEqual(rp.pack_pin_state(prov), "rewritten")
            out.unlink()
            self.assertEqual(rp.pack_pin_state(prov), "missing")
            prov.write_text("# header\nrun: {}\n")
            self.assertIsNone(rp.pack_pin_state(prov))                                 # no pin, no drift

    def test_the_cli_says_when_a_rewrite_restored_a_stale_pins_pack(self):
        """SF-R3: regenerating a pack back to the bytes a stale review pins
        is the repair case, and used to be reported as the pack having
        moved under that pin."""
        import click.testing
        from unittest import mock
        from data_sheets_schema.cli.review import review as review_cli
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            rp.write_pack(prov, instr, self.SMALLER, force=True)                       # moved away from the pin
            self.assertEqual(rp.pack_pins(prov)[0], [])
            base = ["pack", "--method", "claudecode_agent", "--label", "L", "--project", "VOICE", "--force",
                    "--instruction", str(instr)]
            with mock.patch("data_sheets_schema.cli.review._provenance", lambda m, l, p: prov):
                r = click.testing.CliRunner().invoke(review_cli, base)                  # default sample: the pinned bytes
            self.assertEqual(r.exit_code, 0, r.output)
            self.assertIn("restored the pack", r.output); self.assertNotIn("had already moved", r.output)
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), sha)

    def test_build_pack_returns_only_the_pack(self):
        """SF-R3a: the instruction travels out of band, never as a key."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            out: list[str] = []
            pack = rp.build_pack(prov, instr, write_instruction=False, instruction_out=out)
            self.assertNotIn("_instruction_text", pack)
            self.assertEqual(len(out), 1); self.assertIn("rule", out[0].lower())
            self.assertEqual(pack, rp.build_pack(prov, instr))                        # identical mapping either way

    def test_runs_check_reports_a_moved_pack_through_the_cli(self):
        """SF-R3c: the `d4d runs check` drift branch, end to end — the
        wiring MF-R3 broke and the wording a reader sees."""
        import os
        import click.testing
        from data_sheets_schema import provenance
        from data_sheets_schema.cli.runs import runs as runs_cli
        from tests.test_provenance_reasoning_effort import header                # the fixture's record header
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                label, method = "2026-08-09_test_rep1", "claudecode_agent"
                concat = Path("data/d4d_concatenated")
                full = concat / method / label; core = concat / f"{method}_core" / label
                full.mkdir(parents=True); core.mkdir(parents=True)
                Path("src/data_sheets_schema").mkdir(parents=True)               # the repo-root marker (#672)
                body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
                head = header("claude-opus-5", "Claude Code")
                (full / "P_d4d.yaml").write_text(head + body); (core / "P_d4d_core.yaml").write_text(head + body)
                (core / "P_reconciliation.md").write_text("# r\n"); Path("b.txt").write_text("docs\n")
                rec = provenance.build_record("P", method, label, mode="live", input_bundle=Path("b.txt"),
                                              input_verified=True, concat_dir=concat)
                prov = provenance.record_path_for("P", method, label, concat)
                rec.write(prov)
                pack = core / "P_review_pack.yaml"; pack.write_text("pack_version: 5\nitems: []\n")
                text = prov.read_text(); hdr, rest = text.split("\n", 1)
                d = yaml.safe_load(rest); d["review"] = {"artifacts": {"pack": {"sha256": hashlib.sha256(pack.read_bytes()).hexdigest()}}}
                prov.write_text(hdr + "\n" + yaml.safe_dump(d))
                r = click.testing.CliRunner().invoke(runs_cli, ["check"])
                self.assertEqual(r.exit_code, 0, r.output); self.assertNotIn("pins a pack", r.output)
                pack.write_text("pack_version: 5\nitems: [moved]\n")
                r = click.testing.CliRunner().invoke(runs_cli, ["check"])
                self.assertEqual(r.exit_code, 0, r.output)
                self.assertIn("pins a pack that is not the one on disk", r.output); self.assertIn("rewritten", r.output)
                pack.unlink()
                r = click.testing.CliRunner().invoke(runs_cli, ["check"])
                self.assertEqual(r.exit_code, 0, r.output)
                self.assertIn("pins a pack that is not the one on disk", r.output)
                self.assertRegex(r.output, r"missing")
                self.assertNotIn("rewritten", r.output.split("pins a pack that is not the one on disk", 1)[1])
            finally:
                os.chdir(here)

    def test_the_b_review_and_the_pack_itself(self):
        """The `_b` glob case the six three-pin records exercise; the pack
        file never reads as a pin on itself."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review", name="P_review_b.yaml")
            current, _ = rp.pack_pins(prov)
            self.assertEqual([p["path"].split("/")[-1] for p in current], ["P_review_b.yaml"])

    def test_a_stale_pin_does_not_block_and_is_named(self):
        """A review that pins a hash the file no longer has: the pack already
        moved once; rewriting it is allowed, and the stale pin is reported."""
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            (out.parent / "P_review.yaml").write_text(yaml.safe_dump({"pack_sha256": "0" * 64, "items": []}))
            current, stale = rp.pack_pins(prov)
            self.assertEqual(current, []); self.assertEqual([p["by"] for p in stale], ["review"])
            rp.write_pack(prov, instr, self.SMALLER)

    def test_no_pack_means_no_pins_and_a_free_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = Pack()._run(tmp)
            self.assertEqual(rp.pack_pins(prov), ([], []))
            rp.write_pack(prov, instr)

    def test_the_cli_refuses_without_force_and_names_what_moved(self):
        import click.testing
        from data_sheets_schema.cli.review import review as review_cli
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr, out, sha = self._pinned(tmp, "review")
            from unittest import mock
            base = ["pack", "--method", "claudecode_agent", "--label", "L", "--project", "VOICE", "--receipted", "3", "--receiptless", "3"]
            with mock.patch("data_sheets_schema.cli.review._provenance", lambda m, l, p: prov):
                r = click.testing.CliRunner().invoke(review_cli, base)
                self.assertNotEqual(r.exit_code, 0); self.assertIn("pinned by hash", r.output)
                r = click.testing.CliRunner().invoke(review_cli, base + ["--force"])
                self.assertEqual(r.exit_code, 0, r.output); self.assertIn("redo that review", r.output)
                self.assertLess(r.output.index("✓"), r.output.index("redo that review"))   # warnings after the tick
                r = click.testing.CliRunner().invoke(review_cli, base + ["--force"])         # byte-identical now
                self.assertEqual(r.exit_code, 0, r.output); self.assertNotIn("redo that review", r.output)

    def test_the_agent_is_told_never_to_regenerate(self):
        text = (Path(__file__).resolve().parents[1] / ".claude" / "agents" / "d4d-review-record.md").read_text()
        self.assertIn("never regenerate it", text)
        self.assertIn("Only\nwhen there is no pack at all", text)
        self.assertNotIn("not yours to pass). The pack\nIt names", text)              # the dangling sentence (#1124 MF2)
        for key in ("receipt_join", "reference_attributes"):                           # version-conditioned (SF4)
            i = text.index(key); self.assertIn("pack_version", text[i - 400:i + 400], key)
