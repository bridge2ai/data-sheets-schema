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
#: The VOICE bundle as it stands. Changed twice, both times to take curator
#: text out of it: #421 removed `curation_note`, #427 removed
#: `verification_url`. Superseded values are kept beside it because runs
#: recorded them in `inputs.bundle_md5`, and a hash with no name is
#: indistinguishable from a corrupted one. `source_manifest.yaml`'s
#: `bundle_hash_history` carries the same mapping for all five projects.
#: #921 (2026-09-03) changed it a third time, for a different reason: the docx
#: extractor had been dropping w:sdt-wrapped runs (#886), and the VOICE
#: investigator table gained its ☒/☐ marks. Same discipline: superseded
#: value kept beside it, and in the manifest's history.
VOICE_BUNDLE_MD5 = "9193c3cbe60b62a2fc0f704a2c4d23a3"
VOICE_BUNDLE_MD5_PRE_921 = "dcd717170da6762569c0b4eeafc1c3d2"
VOICE_BUNDLE_MD5_PRE_427 = "3e5c24df7b46d97204cb007c43b99e92"
VOICE_BUNDLE_MD5_PRE_421 = "e637eb752ee8cab5f9f7a52782250469"


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

    def test_the_voice_bundle_matches_the_pinned_hash(self):
        """Adding a second dataset must not disturb the first.

        This used to assert the pre-#421 hash and read "49 runs record this
        md5" — true when written, and the reason VOICE keeps its identifier.
        #421 stripped curator prose out of every bundle, which changed all five
        hashes deliberately. Nothing re-verifies `inputs.bundle_md5` against
        disk, so no gate broke; the recorded hashes are now a statement about
        bytes that existed when those runs ran, which is what they always were.

        Re-pinned rather than deleted: the point of the test is that the file
        does not change *by accident*, and that is still worth asserting.
        """
        self.assertEqual(self._md5(CONCAT / "VOICE_preprocessed.txt"),
                         VOICE_BUNDLE_MD5)

    def test_every_pre_strip_hash_is_recorded_not_forgotten(self):
        """9 runs record the pre-#421 hash. Keeping the superseded values here
        is what lets someone reading those records tell "consumed the pre-#421
        bundle" from "consumed something unidentifiable"."""
        supers = {VOICE_BUNDLE_MD5_PRE_421, VOICE_BUNDLE_MD5_PRE_427, VOICE_BUNDLE_MD5_PRE_921}
        self.assertNotIn(VOICE_BUNDLE_MD5, supers)
        self.assertEqual(3, len(supers))
        for h in supers:
            self.assertEqual(32, len(h))

    def test_the_manifest_history_agrees_with_these_constants(self):
        """Two places record the same mapping; if they disagree, the one a
        reader happens to open is a coin toss."""
        events = yaml.safe_load(MANIFEST.read_text())["bundle_hash_history"]["events"]
        by_issue = {e["issue"]: e["projects"]["VOICE"] for e in events if "VOICE" in e["projects"]}
        self.assertEqual(VOICE_BUNDLE_MD5_PRE_421, by_issue[421]["before"])
        self.assertEqual(VOICE_BUNDLE_MD5_PRE_427, by_issue[427]["before"])
        self.assertEqual(VOICE_BUNDLE_MD5_PRE_921, by_issue[427]["after"])
        self.assertEqual(VOICE_BUNDLE_MD5_PRE_921, by_issue[921]["before"])
        self.assertEqual(VOICE_BUNDLE_MD5, by_issue[921]["after"])

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


@unittest.skipUnless(MANIFEST.exists(), "manifest not present")
class TestTheBundleRebuildsFromDeclaredInputs(unittest.TestCase):
    """#302: the bundle was built with an undeclared --input-dir override.

    That is #234 in a different file — a committed artifact its own documented
    generator cannot reproduce. It matters more here than for a mapping,
    because a generation run attests this bundle's md5, and an input nobody can
    regenerate is one nobody can check.
    """

    def test_the_source_directory_is_declared_in_the_manifest(self):
        """Beside the selection, not in whatever command someone typed.

        The manifest already says *which* files a project selects; the
        directory they are selected from belongs in the same place.
        """
        projects = yaml.safe_load(MANIFEST.read_text())["projects"]
        self.assertEqual(projects.get("VOICE_PEDIATRIC_source_dir"),
                         "data/preprocessed/individual/VOICE")

    def test_a_declared_source_dir_names_a_real_directory(self):
        projects = yaml.safe_load(MANIFEST.read_text())["projects"]
        for key, value in projects.items():
            if key.endswith("_source_dir"):
                with self.subTest(key=key):
                    self.assertTrue((REPO / value).is_dir(), value)

    def test_every_declared_source_dir_belongs_to_a_project(self):
        projects = yaml.safe_load(MANIFEST.read_text())["projects"]
        for key in projects:
            if key.endswith("_source_dir"):
                with self.subTest(key=key):
                    self.assertIn(key[: -len("_source_dir")], projects)


if __name__ == "__main__":
    unittest.main()
