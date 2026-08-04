"""VOICE_PEDIATRIC is scoped by its bundle, not by its name (#292).

Both datasets are documented in one corpus, so the question was how a run
targeting the pediatric dataset is told which one to describe.

**Not by `{MANIFEST_LINE}`.** An earlier note claimed that field could carry the
scope. It cannot: it is substituted into the *output record's* header block, as
a provenance comment, not into the instruction. The frozen prompt body says
"DECLARED INPUT BUNDLE — your only source of dataset facts: {BUNDLE}", so the
bundle is the scope, and scoping there needs no change to any frozen prompt.
"""

import hashlib
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "data" / "preprocessed" / "source_manifest.yaml"
CONCAT = REPO / "data" / "preprocessed" / "concatenated"

#: What the 49 runs subject to the live-provenance rule recorded for the VOICE
#: bundle. Renaming or rebuilding it would invalidate their attestation.
VOICE_BUNDLE_MD5 = "e637eb752ee8cab5f9f7a52782250469"


@unittest.skipUnless(MANIFEST.exists(), "manifest not present")
class TestTheManifestEntry(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.projects = yaml.safe_load(MANIFEST.read_text())["projects"]

    def test_both_voice_datasets_are_declared(self):
        self.assertIn("VOICE", self.projects)
        self.assertIn("VOICE_PEDIATRIC", self.projects)

    def test_the_pediatric_selection_leads_with_its_own_record(self):
        first = self.projects["VOICE_PEDIATRIC"][0]["id"]
        self.assertEqual(first, "physionet_pediatric_1_1_0")

    def test_the_adult_version_pages_are_excluded(self):
        """Including them would import adult facts into a pediatric datasheet —
        the failure the fitness axis calls `target`."""
        ids = {s["id"] for s in self.projects["VOICE_PEDIATRIC"]}
        for adult in ("physionet_1_1", "physionet_3_0_0", "physionet_3_1_0"):
            with self.subTest(source=adult):
                self.assertNotIn(adult, ids)

    def test_every_pediatric_source_is_a_voice_source(self):
        """They share a corpus; the pediatric selection is a subset, not new
        material."""
        voice = {s["id"] for s in self.projects["VOICE"]}
        for s in self.projects["VOICE_PEDIATRIC"]:
            with self.subTest(source=s["id"]):
                self.assertIn(s["id"], voice)

    def test_the_voice_selection_is_unchanged(self):
        self.assertEqual(len(self.projects["VOICE"]), 11)


@unittest.skipUnless((CONCAT / "VOICE_preprocessed.txt").exists(),
                     "bundles not present")
class TestTheBundles(unittest.TestCase):

    def _md5(self, path):
        return hashlib.md5(path.read_bytes()).hexdigest()

    def test_the_voice_bundle_still_matches_what_runs_attested(self):
        """49 runs record this md5 in `inputs.bundle_md5`.

        Adding a second dataset must not disturb the first — rebuilding or
        renaming this file would invalidate their attestation, which is the
        whole reason VOICE keeps its identifier.
        """
        self.assertEqual(self._md5(CONCAT / "VOICE_preprocessed.txt"),
                         VOICE_BUNDLE_MD5)

    def test_the_pediatric_bundle_exists_and_is_smaller(self):
        ped = CONCAT / "VOICE_PEDIATRIC_preprocessed.txt"
        self.assertTrue(ped.exists())
        self.assertLess(ped.stat().st_size,
                        (CONCAT / "VOICE_preprocessed.txt").stat().st_size)

    def test_it_carries_the_pediatric_dataset_identifier(self):
        text = (CONCAT / "VOICE_PEDIATRIC_preprocessed.txt").read_text(
            errors="ignore")
        self.assertIn("h995-bt35", text)

    def test_it_carries_no_adult_version_pages(self):
        text = (CONCAT / "VOICE_PEDIATRIC_preprocessed.txt").read_text(
            errors="ignore")
        for adult in ("b2ai-voice/3.1.0", "b2ai-voice/3.0.0"):
            with self.subTest(page=adult):
                self.assertNotIn(adult, text)


if __name__ == "__main__":
    unittest.main()
