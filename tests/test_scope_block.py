"""The declared scope reaches the model, not only the checker (#932).

v8's R2 tells the model that a passage whose subject is another dataset
belongs in `related_datasets` and never in the referent's own slots. The
manifest declares which datasets those are, per project, in its `scope:`
block — and until this change that declaration was read only by `scope.py`
and `d4d download scope --check`. A rule about a distinction the model was
never shown is a rule only the checker can enforce, which is how the #441
class of scope leak survived reconciliation (#913).
"""
import unittest
from unittest import mock

from data_sheets_schema.api_runner import ASSEMBLY_LAYOUT, scope_block

DECLARED = {
    "WITH_RELATED": {
        "referent": "Example adult dataset",
        "referent_id": "https://doi.org/10.5555/adult",
        "referent_note": "Earlier releases in the bundle are the same dataset.",
        "related_but_distinct": [{
            "id": "https://doi.org/10.5555/paed",
            "name": "Example pediatric dataset",
            "also_known_as": ["https://doi.org/10.5555/paed-1-1"],
            "why": "a separate project with its own protocol",
            "express_as": "related_datasets",
            "in_bundle": "paediatric_source_1",
        }],
    },
    "NO_RELATED": {"referent": "Example solo dataset",
                   "referent_id": "https://doi.org/10.5555/solo",
                   "related_but_distinct": []},
    "NO_REFERENT": {"related_but_distinct": []},
}


def _declared(project, manifest=None):
    return DECLARED.get(project)


class TestWhatTheModelIsTold(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch("data_sheets_schema.scope.scope_of", _declared)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def test_the_related_dataset_is_named_with_every_identifier_it_answers_to(self):
        """A check that knew only the project DOI would pass a record naming
        the version DOI (`scope.related_ids`); the model needs both too."""
        block = scope_block("WITH_RELATED")
        self.assertIn("Example pediatric dataset", block)
        self.assertIn("https://doi.org/10.5555/paed", block)
        self.assertIn("https://doi.org/10.5555/paed-1-1", block)
        self.assertIn("a separate project with its own protocol", block)
        self.assertIn("`related_datasets`", block)
        self.assertIn("paediatric_source_1", block)

    def test_the_referent_and_its_note_come_first(self):
        block = scope_block("WITH_RELATED")
        self.assertTrue(block.startswith("DECLARED SCOPE — this record is about "
                                         "Example adult dataset "
                                         "(https://doi.org/10.5555/adult)."))
        self.assertIn("Earlier releases in the bundle are the same dataset.", block)

    def test_a_project_with_no_related_dataset_still_gets_its_referent(self):
        """The referent note carries the earlier-release half of R2, which is
        the half AI_READI needs and CM4AI needs; an empty related list is not
        a reason to send nothing."""
        block = scope_block("NO_RELATED")
        self.assertIn("Example solo dataset", block)
        self.assertNotIn("NOT this one", block)

    def test_it_names_the_datasets_and_does_not_restate_the_rule(self):
        """The block supplies facts; the rules supply the behaviour. If it
        started asserting what a passage means, two texts would govern one
        decision."""
        block = scope_block("WITH_RELATED")
        self.assertIn("it does not tell you what any passage says", block)

    def test_no_referent_and_no_project_send_nothing(self):
        self.assertIsNone(scope_block("NO_REFERENT"))
        self.assertIsNone(scope_block("ABSENT_PROJECT"))

    def test_an_arm_that_declares_the_manifest_unused_sends_nothing(self):
        """Same exemption as the ranking and naming blocks (#603/#668): the
        crate and healthsheet arms supply one bundle and state the manifest
        unused, so a declaration drawn from it would describe documents they
        were never given."""
        self.assertIsNone(scope_block("WITH_RELATED", "Source manifest: not used"))
        self.assertIsNotNone(scope_block("WITH_RELATED", "Source manifest: v3"))


class TestTheAssemblyDigestMoves(unittest.TestCase):
    def test_the_layout_names_the_new_block(self):
        """A block added to the request with no change to ASSEMBLY_LAYOUT would
        leave two conditions indistinguishable by their recorded prompt
        evidence — the #353 defect the digest exists to prevent."""
        self.assertIn("declared scope", ASSEMBLY_LAYOUT)


class TestTheRealManifest(unittest.TestCase):
    def test_every_declared_project_renders_or_declines_for_a_stated_reason(self):
        from data_sheets_schema.scope import all_scopes
        for project, declared in all_scopes().items():
            with self.subTest(project=project):
                block = scope_block(project)
                if declared.get("referent"):
                    self.assertIsNotNone(block)
                    self.assertIn(declared["referent"], block)
                else:
                    self.assertIsNone(block)

    def test_no_project_identifier_is_hardcoded_in_the_renderer(self):
        """#647: a real identifier in code reaches the model verbatim. Every
        value in the block comes from the manifest."""
        import inspect
        from data_sheets_schema import api_runner
        src = inspect.getsource(api_runner.scope_block)
        for token in ("doi.org/10.", "physionet", "fairhub", "cm4ai", "chorus"):
            self.assertNotIn(token, src.lower())


if __name__ == "__main__":
    unittest.main()
