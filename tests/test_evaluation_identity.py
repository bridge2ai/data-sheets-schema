"""Project and method are carried, never recovered from a composite key (#622).

`evaluate_d4d_llm` built result keys as `f"{project}_{method}"` and then split
them on the first underscore to get the pair back. That reported `AI_READI` as
project `AI`, and `VOICE_PEDIATRIC` as `VOICE` — silently merging two datasets
the manifest declares distinct, which is what the scope work in #422 and #441
exists to prevent.

There is no correct split. A project may contain an underscore and so may a
method (`claudecode_agent`), so `AI_READI_claudecode_agent` is ambiguous in
both directions. The only fix is to carry what was known at the time.

## Why these tests drive real files

The first version of this module asserted on source text — a grep over three
hardcoded paths, and a literal substring for the inventory. It passed while the
committed `file_inventory.json` was still in the old format, which made the
hybrid scripts fall back on every entry and report project
`AI_READI_gpt5_concatenated`, method `""` (#632). One test that loaded the real
inventory through `entry_identity` would have caught it.

So the guards below load the actual file, and the format check is a behavioural
round-trip rather than a string match.
"""

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

INVENTORY = ROOT / "data" / "evaluation_llm" / "rubric10" / "file_inventory.json"
HYBRIDS = ("scripts/batch_evaluate_rubric10_hybrid.py",
           "scripts/batch_evaluate_rubric20_hybrid.py")


def _load(rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IdentityIsCarried(unittest.TestCase):

    def test_a_project_name_with_an_underscore_survives(self):
        from evaluation.evaluate_d4d_llm import IDENTITY, identity_of
        for project, method in (("AI_READI", "claudecode_agent"),
                                ("VOICE_PEDIATRIC", "curated"),
                                ("VOICE", "gpt5"),
                                ("SOME_OTHER_DATASET", "claudecode_assistant")):
            with self.subTest(project=project):
                results = {IDENTITY: {"project": project, "method": method}}
                self.assertEqual(
                    identity_of(f"{project}_{method}", results),
                    (project, method))

    def test_an_unrecoverable_identity_keeps_the_whole_key(self):
        """A result predating the carried field cannot have it recovered.

        Returning the whole key is visibly unresolved. Returning a *prefix* of
        it — what the split did — is plausibly wrong, and that is the worse
        failure (#470, #613).
        """
        from evaluation.evaluate_d4d_llm import identity_of
        self.assertEqual(identity_of("AI_READI_gpt5", {}), ("AI_READI_gpt5", ""))


class TheCommittedInventoryResolves(unittest.TestCase):
    """The regression #632, as a test.

    The format changed and the committed file did not, so every entry took the
    fallback. Nothing detected it because nothing read the real file.
    """

    def setUp(self):
        if not INVENTORY.exists():
            self.skipTest("no inventory in this checkout")
        self.inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))

    def test_every_entry_yields_its_project_and_method(self):
        for rel in HYBRIDS:
            module = _load(rel)
            for section in ("concatenated_files", "individual_files"):
                for key, entry in (self.inventory.get(section) or {}).items():
                    with self.subTest(script=rel, key=key):
                        project, method, _ = module.entry_identity(key, entry)
                        self.assertTrue(project and method)
                        # The bug's signature: the key leaking into the value.
                        self.assertNotEqual(project, key)
                        self.assertTrue(
                            key.startswith(f"{project}_{method}"),
                            f"{key!r} does not begin with {project}_{method}")

    def test_ai_readi_is_not_reported_as_ai(self):
        """The specific misattribution, named."""
        module = _load(HYBRIDS[0])
        seen = set()
        for section in ("concatenated_files", "individual_files"):
            for key, entry in (self.inventory.get(section) or {}).items():
                seen.add(module.entry_identity(key, entry)[0])
        if not any(p.startswith("AI") for p in seen):
            self.skipTest("no AI-READI entries in this checkout")
        self.assertIn("AI_READI", seen)
        self.assertNotIn("AI", seen)

    def test_the_recorded_totals_count_files_not_dict_keys(self):
        """`sum(len(entry))` over dict entries counted 4 apiece (#632)."""
        meta = self.inventory.get("metadata") or {}
        true_individual = sum(
            len(e["paths"]) for e in
            (self.inventory.get("individual_files") or {}).values())
        self.assertEqual(meta.get("total_individual_files"), true_individual)
        self.assertEqual(meta.get("total_concatenated_files"),
                         len(self.inventory.get("concatenated_files") or {}))


class ALegacyInventoryIsRefused(unittest.TestCase):
    """Falling back was worse than the bug (#632).

    The old split got every project in the current corpus right. The fallback
    got every one wrong and wrote a full set of misattributed results with
    nothing printed and exit status 0.
    """

    LEGACY = ("data/d4d_concatenated/gpt5/AI_READI_d4d.yaml",   # a bare path
              {"project": "AI_READI"},                          # no method
              {"method": "gpt5"},                               # no project
              {})

    def test_each_legacy_shape_raises(self):
        for rel in HYBRIDS:
            module = _load(rel)
            for entry in self.LEGACY:
                with self.subTest(script=rel, entry=str(entry)[:30]):
                    with self.assertRaises(module.LegacyInventory):
                        module.entry_identity("AI_READI_gpt5_concatenated",
                                              entry)

    def test_the_refusal_says_how_to_fix_it(self):
        """A refusal nobody can act on is only a different kind of stuck."""
        module = _load(HYBRIDS[0])
        with self.assertRaises(module.LegacyInventory) as caught:
            module.entry_identity("k", "some/path.yaml")
        self.assertIn("evaluate_all_d4ds_rubric10.py", str(caught.exception))


class NothingRederivesIdentityFromAName(unittest.TestCase):
    """The sites the first fix missed (#633).

    Scoped by searching the evaluation code rather than by listing files: the
    previous version hardcoded three paths and so missed four more, and a
    reintroduced split with different quoting evaded it entirely.
    """

    SUSPICIOUS = re.compile(
        r"(?:project|inferred_project)\s*,\s*(?:method|inferred_method)"
        r"\s*=\s*[^\n]*\.split\(")

    def test_no_evaluation_module_splits_a_name_into_project_and_method(self):
        offenders = []
        for directory in ("src/evaluation", "scripts"):
            base = ROOT / directory
            if not base.exists():
                continue
            for path in sorted(base.rglob("*.py")):
                if self.SUSPICIOUS.search(path.read_text(encoding="utf-8")):
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [],
                         "these recover identity by splitting a name; read the "
                         "record's own fields instead")

    def test_the_pattern_matches_the_code_it_is_meant_to_catch(self):
        """Otherwise the guard above passes by matching nothing at all."""
        for line in ('            project, method = project_method.split("_", 1)',
                     "        inferred_project, inferred_method = f.split('_')"):
            with self.subTest(line=line.strip()[:40]):
                self.assertTrue(self.SUSPICIOUS.search(line))

    def test_the_evaluation_records_carry_what_the_summarisers_need(self):
        """The parsers were re-deriving fields already present in the file."""
        directory = ROOT / "data/evaluation_llm/rubric10_semantic/concatenated"
        if not directory.exists():
            self.skipTest("no semantic evaluations in this checkout")
        files = sorted(directory.glob("*_evaluation.json"))
        if not files:
            self.skipTest("no evaluation files in this checkout")
        carrying = 0
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:                                  # noqa: BLE001
                continue
            if isinstance(data, dict) and data.get("project"):
                carrying += 1
        self.assertTrue(carrying,
                        "no evaluation file records its own project, so the "
                        "summarisers have nothing to read")


if __name__ == "__main__":
    unittest.main()
