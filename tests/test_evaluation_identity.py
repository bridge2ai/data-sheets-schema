"""Project and method are carried, never recovered from a composite key (#622).

`evaluate_d4d_llm` built result keys as `f"{project}_{method}"` and then split
them on the first underscore to get the pair back. That reported `AI_READI` as
project `AI`, and `VOICE_PEDIATRIC` as `VOICE` — silently merging two datasets
the manifest declares distinct, which is what the scope work in #422 and #441
exists to prevent.

The two hybrid batch scripts special-cased `AI_READI` alone. A special case for
one name is a standing admission that the parse is wrong; it stayed wrong for
every other name containing an underscore.

There is no correct split: a project may contain an underscore and so may a
method (`claudecode_agent`), so `AI_READI_claudecode_agent` is ambiguous in
both directions. The only fix is to carry what was known at the time.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class IdentityIsCarried(unittest.TestCase):

    def test_a_project_name_with_an_underscore_survives(self):
        from evaluation.evaluate_d4d_llm import IDENTITY, identity_of
        for project, method in (("AI_READI", "claudecode_agent"),
                                ("VOICE_PEDIATRIC", "curated"),
                                ("VOICE", "gpt5"),
                                ("SOME_OTHER_DATASET", "claudecode_assistant")):
            with self.subTest(project=project):
                key = f"{project}_{method}"
                results = {IDENTITY: {"project": project, "method": method}}
                self.assertEqual(identity_of(key, results), (project, method))

    def test_the_old_split_really_did_get_these_wrong(self):
        """The bug, stated as a test, so the fix cannot be undone quietly."""
        self.assertEqual("AI_READI_claudecode_agent".split("_", 1),
                         ["AI", "READI_claudecode_agent"])
        self.assertEqual("VOICE_PEDIATRIC_curated".split("_", 1),
                         ["VOICE", "PEDIATRIC_curated"])

    def test_an_unrecoverable_identity_is_named_rather_than_guessed(self):
        """A result predating the carried field cannot have it recovered.

        Reporting the raw key with an empty method is visibly incomplete. A
        guess is plausibly wrong, which is worse — the distinction this corpus
        keeps landing on (#470, #613).
        """
        from evaluation.evaluate_d4d_llm import identity_of
        self.assertEqual(identity_of("AI_READI_gpt5", {}),
                         ("AI_READI_gpt5", ""))

    def test_no_evaluator_splits_a_composite_key_any_more(self):
        root = Path(__file__).resolve().parent.parent
        offenders = []
        for rel in ("src/evaluation/evaluate_d4d_llm.py",
                    "scripts/batch_evaluate_rubric10_hybrid.py",
                    "scripts/batch_evaluate_rubric20_hybrid.py"):
            path = root / rel
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if 'project_method.split' in text or "parts = key.split('_')" in text:
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         "these recover identity by splitting a key again")

    def test_the_inventory_carries_identity(self):
        """Otherwise the hybrid scripts have nothing to read and fall back."""
        root = Path(__file__).resolve().parent.parent
        path = root / "scripts" / "evaluate_all_d4ds_rubric10.py"
        if not path.exists():
            self.skipTest("inventory builder not present in this checkout")
        text = path.read_text(encoding="utf-8")
        self.assertIn('"project": project, "method": method', text)


if __name__ == "__main__":
    unittest.main()
