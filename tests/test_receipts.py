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
            {"slot": "keywords", "snippet": "multimodal study"},
            {"slot": "file_collections[0]", "snippet": "longitudinal, multimodal"}]},
        {"id": "c003", "status": "nothing_relevant", "reason": "references only"}]}


class Normalisation(unittest.TestCase):
    def test_exact_and_folded_matches_verify_and_paraphrase_does_not(self):
        text = "The Bridge2AI program — [NIH] “Common Fund”, 2024."
        self.assertTrue(rc.snippet_in("bridge2ai program", text)[0])
        self.assertTrue(rc.snippet_in('program — [NIH] “Common Fund”', text)[0])
        self.assertTrue(rc.snippet_in("Bridge2AI program ... Common Fund, 2024", text)[0])   # parts, in order
        self.assertTrue(rc.snippet_in("Bridge2AI program [...] Common Fund, 2024", text)[0])
        self.assertFalse(rc.snippet_in("Common Fund, 2024 ... Bridge2AI program", text)[0])  # out of order
        self.assertFalse(rc.snippet_in("the Bridge to AI programme", text)[0])
        # #720: no editorial stripping — bracketed text is text, so a
        # bracket-padded fabrication fails and a real bracket verifies
        self.assertFalse(rc.snippet_in("Bridge2AI program [funded by the Gates Foundation]", text)[0])
        self.assertTrue(rc.snippet_in("[1] Something else", "References\n[1] Something else entirely.")[0])
        # #720: a snippet that could match anywhere attests nothing
        for short in ("a", "the", "…a…", "Fund", "Bridge2AI ... a"):
            ok, why = rc.snippet_in(short, text)
            self.assertFalse(ok, short); self.assertIn("short", why)
        # #763: a short numeric part anchors a phrase — one part of 8 pins it
        self.assertFalse(rc.snippet_in("2024", "in 2024 the program")[0])
        self.assertTrue(rc.snippet_in("50,000...admissions from ICU", "50,000\nPatient admissions from ICU, PICU")[0])
        # #780: an exact numeric value pins a passage at five characters
        self.assertTrue(rc.snippet_in("165,051", "a total of 165,051 files")[0])
        self.assertTrue(rc.snippet_in("3.82 TB", "size 3.82 TB in all")[0])
        self.assertFalse(rc.snippet_in("2024", "in 2024 the program")[0])
        self.assertFalse(rc.snippet_in("v1.0", "in v1.0 the program")[0])
        # #784: version strings and figure labels pin nothing
        for weak in ("3.0.0", "v3.0.0", "Table 1", "Fig. 1", "1,000"):   # "10 days" (7 chars, 2 digits) pins, as the review measured
            self.assertFalse(rc.snippet_in(weak, f"see {weak} here")[0], weak)
        # #789: a word the extraction wrapped mid-line is the word a reader quotes
        ok, why = rc.snippet_in("Participants are volunteers; therefore, there is selection bias",
                                "Partic-\nipants  are  volunteers;  therefore,  there  is  selection  bias\n")
        self.assertTrue(ok); self.assertEqual(why, "linewrap-joined")
        self.assertFalse(rc.snippet_in("Participants are volunteers", "Partic\nipants left; volunteers came")[0])
        self.assertTrue(rc.snippet_in("selection bias known as volunteer bias",
                                      "there  is  selection  bias\nknown  as  volunteer  bias  which")[0])
        # #786: a JSON-escaped newline in the bundle is whitespace
        self.assertTrue(rc.snippet_in("from the\nAI-READI Project (3.0.0) [Data set].",
                                      '"citation": "Diabetes from the\\nAI-READI Project (3.0.0) [Data set]. FAIRhub."')[0])
        # #765: three common words do not, however many parts they are split into
        ok, why = rc.snippet_in("the ... and ... for", "the cat and the dog for a walk")
        self.assertFalse(ok); self.assertIn("short", why)
        self.assertFalse(rc.snippet_in("the cat ... dog for", "the cat and the dog for a walk")[0])   # no part of 8, total 12


class Validator(unittest.TestCase):
    def setUp(self):
        self.manifest, self.texts = _manifest_and_texts()
        self.md5 = self.manifest["bundle_md5"]

    def test_a_clean_receipt_counts_affirmatively(self):
        b = rc.check(_receipt(self.md5), self.manifest, self.texts, FULL, self.md5)
        self.assertEqual(b["findings"], [])
        self.assertEqual((b["chunks"]["reviewed"], b["chunks"]["total"]), (3, 3))
        self.assertEqual((b["snippets"]["verified"], b["snippets"]["total"]), (8, 8))
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
        self.assertGreaterEqual(b["snippets"]["mismatched"], 1)
        self.assertEqual(b["slots"]["unresolved"], ["nowhere.at_all"])

    def test_a_path_reshaped_after_the_receipt_is_reported_not_a_finding(self):
        """#758: reconcile flattened principal_investigator: {name} to a
        string on the v7 canary; the receipt's path resolved in the phase-1
        snapshot and not in the final record."""
        r = _receipt(self.md5)
        r["chunks"][1]["extracted"].append({"slot": "funders[0].contact.name", "snippet": "NIH Common Fund's"})
        original = {**FULL, "funders": [{**FULL["funders"][0], "contact": {"name": "x"}}]}
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5, original)
        self.assertEqual(b["slots"]["reshaped_by_reconcile"], ["funders[0].contact.name"])
        self.assertNotIn("slot_not_in_record", {f["kind"] for f in b["findings"]})
        self.assertIn("reshaped by reconcile", b["summary"])
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertIn("slot_not_in_record", {f["kind"] for f in b["findings"]})
        r["chunks"][1]["extracted"].append({"slot": "never.there", "snippet": "NIH Common Fund's"})
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5, original)
        self.assertEqual(b["slots"]["unresolved"], ["never.there"])

    def test_a_receipt_on_a_list_covers_only_itself_and_an_entry_covers_its_leaves(self):
        """#721: `funders` must not attest every funder; `funders[0]` attests
        funder 0's leaves (which is how a boolean or enum gets a receipt)."""
        r = _receipt(self.md5)
        r["chunks"][1]["extracted"] = [p for p in r["chunks"][1]["extracted"] if not p["slot"].startswith("funders")]
        r["chunks"][1]["extracted"].append({"slot": "funders", "snippet": "NIH Common Fund's"})
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertIn("funders[0].grant_id", b["slots"]["without_receipt"])
        r["chunks"][1]["extracted"][-1]["slot"] = "funders[0]"
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertNotIn("funders[0].grant_id", b["slots"]["without_receipt"])
        r["chunks"][1]["extracted"].append({"slot": "", "snippet": "NIH Common Fund's"})
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertIn("slot_empty", {f["kind"] for f in b["findings"]})

    def test_exemptions_follow_the_records(self):
        """#722: commentary is exempt at any depth; conforms_to is a bundle
        fact; a fragment is minted only on the record's own id."""
        full = {**FULL, "conforms_to": "OMOP CDM",
                "funders": [{"id": "https://x/ds#funder-1", "name": "NIH", "source_caveats": "not stated"}],
                "external_resources": [{"id": "https://other.org/page#section", "name": "p"}]}
        leaves = dict(rc.populated_leaves(full))
        ex = {p for p, v in leaves.items() if rc.exempt(p, v, full["id"])}
        self.assertIn("funders[0].source_caveats", ex); self.assertIn("notes", ex)
        self.assertIn("funders[0].id", ex)                     # minted on the record's id
        self.assertNotIn("external_resources[0].id", ex)       # a real anchor elsewhere
        self.assertNotIn("conforms_to", ex)

    def test_malformed_entries_are_findings_not_tracebacks(self):
        r = _receipt(self.md5)
        r["chunks"][1]["extracted"] = "Grant OT2OD032644"
        r["chunks"].append("not an entry"); r["chunks"].append({"id": [1], "status": "extracted"})
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertEqual(sum(f["kind"] == "malformed_entry" for f in b["findings"]), 3)

    def test_redundant_with_a_chunk_that_extracted_nothing_is_a_contradiction(self):
        r = _receipt(self.md5)
        r["chunks"][2] = {"id": "c003", "status": "redundant_with", "chunks": ["c001"]}   # c001: nothing_relevant
        kinds = {f["kind"] for f in rc.check(r, self.manifest, self.texts, FULL, self.md5)["findings"]}
        self.assertIn("redundant_with_a_chunk_that_extracted_nothing", kinds)

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

    def test_a_snippet_in_a_neighbouring_chunk_is_reported_not_gated(self):
        """#763: both v7 canaries cited the chunk next door for ~2% of
        snippets. The text is in the bundle, so support holds; attribution
        is its own number and the gate keeps its floor for text found nowhere."""
        from data_sheets_schema.canary import receipt_floors
        r = _receipt(self.md5)
        r["chunks"][2] = {"id": "c003", "status": "extracted",
                          "extracted": [{"slot": "title", "snippet": "Grant OT2OD032644"}]}   # text is in c002
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertEqual((b["snippets"]["adjacent"], b["snippets"]["mismatched"]), (1, 0))
        self.assertEqual(b["findings"][0]["kind"], "snippet_adjacent_chunk"); self.assertEqual(b["findings"][0]["found_in"], ["c002"])
        self.assertIn("adjacent chunk", b["summary"])
        f = receipt_floors({**b, "expected": True})
        self.assertEqual((f["snippets unverified"], f["receipt findings"]), (0, 0))
        r["chunks"][0] = {"id": "c001", "status": "extracted", "extracted": [{"slot": "title", "snippet": "Something else entirely"}]}  # in c003, two away
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertEqual(b["snippets"]["elsewhere"], 1)

    def test_a_snippet_cut_by_a_chunk_boundary_is_reported_as_spanning(self):
        """#781: the passage exists in the bundle across c002/c003; no single
        chunk holds it, and it must not read as found nowhere."""
        from data_sheets_schema.canary import receipt_floors
        r = _receipt(self.md5)
        # the last content line of a.txt (end of c002) and the first line of c003
        r["chunks"][1]["extracted"].append({"slot": "title", "snippet": "Bridge2AI program. FILE: b.txt"})
        assert "Bridge2AI program." in self.texts["c002"] and self.texts["c003"].startswith("FILE: b.txt")
        b = rc.check(r, self.manifest, self.texts, FULL, self.md5)
        self.assertEqual(b["snippets"]["spans_boundary"], 1)
        self.assertEqual(b["snippets"]["mismatched"], 0)
        self.assertEqual(receipt_floors({**b, "expected": True})["snippets unverified"], 0)

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
        self.assertEqual(rc.core_path("file_collections", pmap), "distributions")
        nested = {"id": "https://x/ds", "name": "n",
                  "resources": [{"id": "https://x/sub", "name": "s",
                                 "file_collections": [{"id": "https://x/sub#c", "name": "c", "resources": [
                                     {"id": "https://x/sub#f", "name": "f"}, {"id": "https://x/sub#g", "name": "g"}]}]}]}
        pm = rc.core_path_map(nested)
        self.assertEqual(rc.core_path("resources[0].file_collections[0].resources[1].name", pm),
                         "resources[0].distributions[2].name")
        # #723: an entry the derivation drops (nothing projectable) shifts
        # nothing — the map is by id against the derived core
        skipped = {"id": "https://x/ds", "name": "n",
                   "file_collections": [{"unknown_slot_only": 1, "resources": [{"id": "https://x/ds#f", "name": "f"}]},
                                        {"id": "https://x/ds#c2", "name": "c2"}]}
        pm = rc.core_path_map(skipped)
        self.assertEqual(rc.core_path("file_collections[1].name", pm), "distributions[1].name")
        self.assertIsNone(rc.core_path("file_collections[0].unknown_slot_only", pm))


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


class Playbook(unittest.TestCase):
    """#709: the agentic Phase 1 is the receipt protocol, and the record says
    a receipt was expected."""
    TEXT = (Path(__file__).resolve().parent.parent / ".claude/commands/d4d-full-core.md").read_text(encoding="utf-8")

    def test_phase_one_reads_the_manifest_receipts_each_chunk_and_mandates_the_file_tool(self):
        import re
        p1 = re.sub(r"\s+", " ", self.TEXT.split("## Phase 1", 1)[1].split("## Phase 2", 1)[0])
        for needle in ("_chunks.yaml", "coverage-receipt entry before reading the next",
                       "file-reading tool", "never through a shell", "redundant_with",
                       "nothing_relevant", "duplicate_of", "d4d receipts check"):
            self.assertIn(needle, p1, needle)
        # the rule the validator enforces, not a looser paraphrase of it (#733)
        self.assertIn(f"at least {rc.MIN_SNIPPET_CHARS} characters after normalisation", p1)
        for status in rc.STATUSES:
            self.assertIn(status, p1)

    def test_the_check_is_executable_before_the_record_exists(self):
        """#730: Phase 1 runs the check before Phase 2, when no provenance
        record exists; the command must work from what is on disk."""
        from data_sheets_schema import provenance as pv
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bundle = tmp / "P_preprocessed.txt"; bundle.write_text(BUNDLE, encoding="utf-8")
            from data_sheets_schema.chunking import build_manifest, dump_manifest
            (tmp / "chunks").mkdir(); (tmp / "chunks/P_chunks.yaml").write_text(dump_manifest(build_manifest(bundle)))
            core = tmp / "concat/claudecode_agent_core/L"; full_dir = tmp / "concat/claudecode_agent/L"
            core.mkdir(parents=True); full_dir.mkdir(parents=True)
            (full_dir / "P_d4d.yaml").write_text(f"# D4D Datasheet for P Dataset\n# Source bundle: {bundle}\n\n"
                                                 + yaml.safe_dump(FULL), encoding="utf-8")
            (core / "P_coverage_receipt.yaml").write_text(yaml.safe_dump(_receipt(hashlib.md5(BUNDLE.encode()).hexdigest())))
            from data_sheets_schema import chunking
            old = pv.CONCAT_DIR, chunking.CHUNKS_DIR
            pv.CONCAT_DIR, chunking.CHUNKS_DIR = tmp / "concat", tmp / "chunks"
            try:
                # --project is a closed choice, so the command's record-less
                # path is exercised through the same calls it makes
                from data_sheets_schema.cli import receipts as mod
                p = mod._run_paths("claudecode_agent", "L", "P")
                self.assertFalse(p["provenance"].exists())
                header = pv.parse_header(p["full"])
                self.assertEqual(header.get("Source bundle"), str(bundle))
                block = rc.block_for(p["full"], rc.receipt_path(p["core_dir"], "P"), Path(header["Source bundle"]),
                                     pv._md5(bundle), True)
                self.assertTrue(block["checked"]); self.assertEqual(block["findings"], [])
            finally:
                pv.CONCAT_DIR, chunking.CHUNKS_DIR = old

    def test_the_record_step_passes_receipt_expected_and_names_the_receipt_artifact(self):
        self.assertIn("--receipt-expected", self.TEXT)
        self.assertIn('"{PROJECT}_coverage_receipt.yaml"', self.TEXT)
        self.assertIn("_coverage_receipt.yaml`", self.TEXT.split("## Outputs", 1)[1].split("## Factual", 1)[0])


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
        # #727: one mismatched snippet is one regression line, not two
        from data_sheets_schema.canary import receipt_floors
        one = {**clean, "snippets": {"total": 8, "verified": 7, "mismatched": 1, "unchecked": 0},
               "findings": [{"kind": "snippet_mismatch"}]}
        self.assertEqual(receipt_floors(one)["receipt findings"], 0)
        self.assertEqual(len(verdict({**self.GOOD, "receipts": one}, self.BAR)["regressions"]), 1)

    def test_backfill_apply_does_not_rewrite_a_record_with_an_empty_receipts_block(self):
        """#726: 235 records would otherwise change for no information."""
        from data_sheets_schema import backfill_checks as bc
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "P_provenance.yaml"
            p.write_text("# header\nrun_id: x\n", encoding="utf-8")
            empty = {"receipts": {"checked": False, "expected": False, "reason": "none"}}
            self.assertFalse(bc.apply(p, empty))
            self.assertNotIn("receipts", p.read_text())
            self.assertTrue(bc.apply(p, {"receipts": {"checked": False, "expected": True, "reason": "none"}}))
            self.assertIn("receipts", p.read_text())


if __name__ == "__main__":
    unittest.main()
