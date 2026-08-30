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
        (core / "P_coverage_receipt.yaml").write_text(yaml.safe_dump(_receipt(md5)))
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
            self.assertEqual(kinds["slot_receiptless"], 2); self.assertEqual(kinds["slot_reshaped"], 1)
            self.assertGreaterEqual(kinds["slot_receipted"], 1)
            chunk = next(i for i in p1["items"] if i["id"] == "chunk-c003")
            self.assertEqual(chunk["source"], "b.txt"); self.assertEqual(chunk["agent_reason"], "references only")
            slot = next(i for i in p1["items"] if i["kind"] == "slot_receipted")
            self.assertIn("snippet", slot); self.assertIn("lines", slot)
            self.assertIn("sha256 matches", p1["instruction"]["basis"]); self.assertEqual(p1["gaps"], [])
            # a different sample size changes the pack; the same one does not
            self.assertNotEqual(rp.build_pack(prov, instr, {"receipted_slots": 1})["items"], p1["items"])

    def test_gaps_are_named_not_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov, instr = self._run(tmp)
            p = rp.build_pack(prov, None)                       # no file, no spec in the record
            self.assertEqual(p["rules"], []); self.assertTrue(any(g.startswith("instruction") for g in p["gaps"]))
            other = Path(tmp) / "other.md"; other.write_text("edited\n")
            self.assertIn("does NOT match", rp.build_pack(prov, other)["instruction"]["basis"])


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
        self.assertEqual(rp.check_review(self.PACK, {"items": [{"id": "rule-01", "verdict": "cannot_tell", "evidence": "no schema"}]})["cannot_tell"], 1)


if __name__ == "__main__":
    unittest.main()
