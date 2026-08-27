"""Coverage receipts are checked, counted affirmatively, and gated (#708)."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import receipts as rc

BUNDLE = ("=" * 80 + "\nCONCATENATED DOCUMENT\n" + "=" * 80 + "\n\n"
          "FILE: a.txt\nPATH: x/a.txt\nSIZE: 1 bytes\n" + "-" * 80 + "\n"
          "The AI-READI dataset (Grant OT2OD032644) is a longitudinal, multimodal study.\n"
          "Funded by the NIH Common Fund's Bridge2AI program.\n\n" + "=" * 80 + "\n\n"
          "FILE: b.txt\nPATH: x/b.txt\nSIZE: 1 bytes\n" + "-" * 80 + "\n"
          "References\n[1] Something else entirely.\n")

FULL = {"id": "https://x/ds", "name": "ai-readi", "title": "AI-READI",
        "description": "a longitudinal, multimodal study", "conforms_to_class": "Dataset",
        "notes": "the run's own commentary",
        "funders": [{"id": "https://x/ds#funder-1", "name": "NIH Common Fund", "grant_id": "OT2OD032644"}],
        "file_collections": [{"id": "https://x/ds#fc1", "name": "raw",
                              "resources": [{"id": "https://x/ds#f1", "name": "a.tsv", "md5": "0" * 32}]}],
        "keywords": ["retina"]}


def _manifest_and_texts():
    from data_sheets_schema.chunking import chunk_text, chunk_texts
    chunks = chunk_text(BUNDLE)
    return ({"bundle_md5": hashlib.md5(BUNDLE.encode()).hexdigest(), "chunks": chunks},
            dict(zip([c["id"] for c in chunks], chunk_texts(BUNDLE, chunks))))


def _receipt(md5):
    return {"bundle_md5": md5, "chunks": [
        {"id": "c001", "status": "nothing_relevant", "reason": "bundle header"},
        {"id": "c002", "status": "extracted", "extracted": [
            {"slot": "funders[0].grant_id", "snippet": "Grant OT2OD032644"},
            {"slot": "description", "snippet": "a longitudinal, multimodal study"},
            {"slot": "funders[0].name", "snippet": "NIH Common Fund's"},
            {"slot": "title", "snippet": "AI-READI"},
            {"slot": "name", "snippet": "ai-readi"},
            {"slot": "id", "snippet": "AI-READI dataset"},
            {"slot": "keywords", "snippet": "study"},
            {"slot": "file_collections[0]", "snippet": "multimodal"}]},
        {"id": "c003", "status": "nothing_relevant", "reason": "references only"}]}


class Normalisation(unittest.TestCase):
    def test_exact_and_folded_matches_verify_and_paraphrase_does_not(self):
        text = "The Bridge2AI program — [NIH] “Common Fund”, 2024."
        self.assertTrue(rc.snippet_in("bridge2ai program", text)[0])
        self.assertTrue(rc.snippet_in('Bridge2AI program — "Common Fund"', text)[0])
        self.assertTrue(rc.snippet_in("Bridge2AI ... 2024", text)[0])          # split parts, in order
        self.assertFalse(rc.snippet_in("2024 ... Bridge2AI", text)[0])         # out of order
        self.assertFalse(rc.snippet_in("the Bridge to AI programme", text)[0])
        self.assertFalse(rc.snippet_in("[only editorial]", text)[0])


class Validator(unittest.TestCase):
    def setUp(self):
        self.manifest, self.texts = _manifest_and_texts()
        self.md5 = self.manifest["bundle_md5"]

    def test_a_clean_receipt_counts_affirmatively(self):
        b = rc.check(_receipt(self.md5), self.manifest, self.texts, FULL, self.md5)
        self.assertEqual(b["findings"], [])
        self.assertEqual(b["chunks"]["reviewed"], b["chunks"]["total"], 3)
        self.assertEqual(b["snippets"]["verified"], b["snippets"]["total"], 8)
        # conforms_to_class, notes and the minted ids are exempt; every other
        # populated leaf has a receipt — the container receipt on
        # file_collections[0] covers its name and its file's md5
        self.assertEqual(b["slots"]["without_receipt"], [])
        self.assertGreater(b["slots"]["exempt"], 0)
        self.assertEqual(b["slots"]["with_receipt"], b["slots"]["receiptable"])
        self.assertIn("chunks 3/3 reviewed", b["summary"]); self.assertIn("snippets 8/8", b["summary"])
        self.assertEqual(len(b["non_checks"]), 2)

    def test_every_defect_is_a_named_finding(self):
        r = _receipt(self.md5)
        r["chunks"].pop()                                              # c003 unreviewed
        r["chunks"][1]["extracted"][0]["snippet"] = "Grant OT2OD099999"  # not in chunk
        r["chunks"][1]["extracted"].append({"slot": "nowhere.at_all", "snippet": "study"})
        r["chunks"].append({"id": "c999", "status": "duplicate_of", "of": "c001"})
        r["chunks"].append({"id": "c002", "status": "nothing_relevant", "reason": ""})
        r["chunks"].append({"id": "c001", "status": "bogus"})
        b = rc.check(r, self.manifest, self.texts, FULL, "f" * 32)
        kinds = {f["kind"] for f in b["findings"]}
        for k in ("snippet_mismatch", "slot_not_in_record", "chunk_not_in_manifest",
                  "chunk_reviewed_more_than_once", "unknown_status", "nothing_relevant_without_reason",
                  "bundle_md5_disagreement"):
            self.assertIn(k, kinds, k)
        self.assertEqual(b["chunks"]["unreviewed"], ["c003"])
        self.assertEqual(b["snippets"]["mismatched"], 1)
        self.assertEqual(b["slots"]["unresolved"], ["nowhere.at_all"])

    def test_a_receipt_without_the_slot_lists_it_by_path(self):
        r = _receipt(self.md5)
        r["chunks"][1]["extracted"] = [p for p in r["chunks"][1]["extracted"] if p["slot"] != "title"]
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertEqual(b["slots"]["without_receipt"], ["title"])

    def test_redundant_with_and_duplicate_of_need_real_targets(self):
        r = _receipt(self.md5)
        r["chunks"][2] = {"id": "c003", "status": "redundant_with", "chunks": ["c002"]}
        self.assertEqual(rc.check(r, self.manifest, self.texts, FULL, self.md5)["findings"], [])
        r["chunks"][2] = {"id": "c003", "status": "redundant_with", "chunks": ["c042"]}
        self.assertEqual(rc.check(r, self.manifest, self.texts, FULL, self.md5)["findings"][0]["kind"],
                         "redundant_with_unknown_chunks")
        r["chunks"][2] = {"id": "c003", "status": "duplicate_of", "of": "c003"}
        self.assertEqual(rc.check(r, self.manifest, self.texts, FULL, self.md5)["findings"][0]["kind"],
                         "duplicate_of_unknown_chunk")

    def test_a_chunk_whose_text_is_missing_is_unchecked_not_verified(self):
        texts = {k: v for k, v in self.texts.items() if k != "c002"}
        b = rc.check(_receipt(self.md5), self.manifest, texts, FULL, self.md5)
        self.assertEqual(b["snippets"]["unchecked"], 8); self.assertEqual(b["snippets"]["verified"], 0)
        self.assertIn("unchecked", b["summary"])


class ClaimReceipts(unittest.TestCase):
    def test_inversion_names_the_derived_core_path(self):
        claims = rc.claim_receipts(_receipt("m"), FULL)
        self.assertEqual(claims["slots"]["funders[0].grant_id"]["receipts"][0]["chunk"], "c002")
        self.assertEqual(claims["slots"]["file_collections[0]"]["core_path"], "distributions[0]")
        self.assertEqual(claims["slots"]["description"]["core_path"], "description")
        pmap = rc.core_path_map(FULL)
        self.assertEqual(rc.core_path("file_collections[0].resources[0].md5", pmap), "distributions[1].md5")
        nested = {"resources": [{"file_collections": [{"id": "c", "resources": [{"id": "f"}, {"id": "g"}]}]}]}
        pm = rc.core_path_map(nested)
        self.assertEqual(rc.core_path("resources[0].file_collections[0].resources[1].sha256", pm),
                         "resources[0].distributions[2].sha256")


class OnDisk(unittest.TestCase):
    def test_block_for_names_each_reason_and_checks_when_it_can(self):
        from data_sheets_schema.chunking import build_manifest, dump_manifest
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bundle = tmp / "P_preprocessed.txt"; bundle.write_text(BUNDLE, encoding="utf-8")
            full = tmp / "P_d4d.yaml"; full.write_text(yaml.safe_dump(FULL), encoding="utf-8")
            receipt = tmp / "P_coverage_receipt.yaml"
            manifest = tmp / "P_chunks.yaml"
            md5 = hashlib.md5(BUNDLE.encode()).hexdigest()
            b = rc.block_for(full, receipt, bundle, md5, expected=False, manifest=manifest)
            self.assertFalse(b["checked"]); self.assertIn("no coverage receipt", b["reason"]); self.assertFalse(b["expected"])
            receipt.write_text(yaml.safe_dump(_receipt(md5)), encoding="utf-8")
            b = rc.block_for(full, receipt, bundle, md5, expected=True, manifest=manifest)
            self.assertFalse(b["checked"]); self.assertIn("no chunk manifest", b["reason"]); self.assertTrue(b["expected"])
            manifest.write_text(dump_manifest(build_manifest(bundle)), encoding="utf-8")
            b = rc.block_for(full, receipt, bundle, md5, expected=True, manifest=manifest)
            self.assertTrue(b["checked"]); self.assertEqual(b["findings"], [])
            self.assertEqual(b["artifacts"]["manifest"]["sha256"], hashlib.sha256(manifest.read_bytes()).hexdigest())
            b = rc.block_for(full, receipt, bundle, "0" * 32, expected=True, manifest=manifest)
            self.assertFalse(b["checked"]); self.assertIn("drifted", b["reason"])
            receipt.write_text("- not a receipt\n", encoding="utf-8")
            self.assertIn("unreadable", rc.block_for(full, receipt, bundle, md5, True, manifest)["reason"])


class Gate(unittest.TestCase):
    """The canary gate reads the block: absent-but-expected is UNMEASURABLE,
    an unreviewed chunk or an unverified snippet is a regression, and a run
    whose procedure writes no receipt is neither (#613)."""
    GOOD = {"pair": {"ran": True, "errors": 0}, "report": {"checked": True, "findings": []},
            "grounding": {"checked": True, "distinct": {"absent": 0}},
            "form": {"checked": True, "organisational_fragments": 0,
                     "undeclared_prefix_occurrences": 0, "british_spellings": 0}}
    BAR = {"pair errors": 5, "report findings": 5, "ungrounded identifiers": 5,
           "resolver URLs in identifier slots": 5, "organisational fragments": 5,
           "undeclared prefixes": 5, "British spellings": 5}

    def test_gate_semantics(self):
        from data_sheets_schema.canary import OK, REGRESSED, UNMEASURABLE, verdict
        clean = {"checked": True, "expected": True, "chunks": {"total": 3, "reviewed": 3},
                 "snippets": {"total": 8, "verified": 8, "mismatched": 0, "unchecked": 0}, "findings": []}
        self.assertEqual(verdict({**self.GOOD, "receipts": clean}, self.BAR)["status"], OK)
        self.assertEqual(verdict({**self.GOOD, "receipts": {**clean, "chunks": {"total": 3, "reviewed": 2}}},
                                 self.BAR)["status"], REGRESSED)
        self.assertEqual(verdict({**self.GOOD, "receipts": {**clean, "snippets": {"total": 8, "verified": 7, "mismatched": 1, "unchecked": 0}}},
                                 self.BAR)["status"], REGRESSED)
        self.assertEqual(verdict({**self.GOOD, "receipts": {**clean, "snippets": {"total": 8, "verified": 7, "mismatched": 0, "unchecked": 1}}},
                                 self.BAR)["status"], REGRESSED)
        self.assertEqual(verdict({**self.GOOD, "receipts": {"checked": False, "expected": True, "reason": "none"}},
                                 self.BAR)["status"], UNMEASURABLE)
        v = verdict({**self.GOOD, "receipts": {"checked": False, "expected": False, "reason": "none"}}, self.BAR)
        self.assertEqual(v["status"], OK)
        self.assertEqual(verdict(self.GOOD, self.BAR)["status"], OK)      # no block at all: pre-receipt arms
        # a receipt with zero snippets over a non-empty manifest is not clean
        self.assertEqual(verdict({**self.GOOD, "receipts": {**clean, "snippets": {"total": 0, "verified": 0, "mismatched": 0, "unchecked": 0}}},
                                 self.BAR)["status"], REGRESSED)


if __name__ == "__main__":
    unittest.main()
