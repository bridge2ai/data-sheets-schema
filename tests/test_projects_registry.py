"""VOICE is two datasets, and the registry says so (#292).

The pediatric companion has its own DOI, protocol and Research Ethics Board
approval. It was being represented as a nested object inside VOICE's
`related_datasets`, which is what made no VOICE replicate validate — the schema
declares that slot a reference, and LinkML cannot be made to accept both a
reference and an inline object (#297). A dataset with those three things is its
own datasheet.
"""

import unittest

from data_sheets_schema.constants import PROJECTS
from data_sheets_schema.constants.projects import (
    SHARED_CORPUS_GROUPS, get_preprocessed_path, get_raw_path,
)


class TestTheRegistry(unittest.TestCase):

    def test_both_voice_datasets_are_projects(self):
        self.assertIn("VOICE", PROJECTS)
        self.assertIn("VOICE_PEDIATRIC", PROJECTS)

    def test_the_main_dataset_keeps_its_identifier(self):
        """Not renamed to VOICE_main.

        198 of the paths that would move are archived records, archived because
        their provenance could not be verified. Rewriting the project field of
        runs set aside for provenance reasons is the opposite of what archiving
        them was for.
        """
        self.assertNotIn("VOICE_main", PROJECTS)

    def test_path_helpers_work_for_the_new_project(self):
        for helper in (get_raw_path, get_preprocessed_path):
            with self.subTest(helper=helper.__name__):
                self.assertTrue(
                    str(helper("VOICE_PEDIATRIC")).endswith("VOICE_PEDIATRIC"))

    def test_the_shared_corpus_is_declared(self):
        """They are separate records from one source corpus.

        An analysis treating projects as independent samples would otherwise
        count them as two, and #169's power argument turns on exactly that
        count.
        """
        group = SHARED_CORPUS_GROUPS["bridge2ai_voice"]
        self.assertEqual(sorted(group), ["VOICE", "VOICE_PEDIATRIC"])
        for name in group:
            self.assertIn(name, PROJECTS)

    def test_every_shared_corpus_member_is_a_real_project(self):
        for group in SHARED_CORPUS_GROUPS.values():
            for name in group:
                with self.subTest(project=name):
                    self.assertIn(name, PROJECTS)


if __name__ == "__main__":
    unittest.main()
