"""The shared generation schemas carry no study content (#1875).

Both generation arms consume the schema: the API arm through the rendered
digest, the native agentic arm through the merged schema files its playbook
names. Under the `neutral` profile the digest already rendered no study
vocabulary (#1302), but the merged files still carried AI-READI titles, a
Bridge2AI-Voice committee example, real IRB and award identifiers and a
whole diabetes/CGM/retina example family modelled on one study. The playbook
forbids copying an example as a fact; this test removes the exposure rather
than relying on that rule.

Scanned: every class, slot, attribute and enum description, `d4d:docExample`
annotation and example value in the modules the two generation roots import
(parsed, so comments are not scanned: they are not model-facing), the two
merged files the native toolchain selects under `neutral`, and the digest
under both profiles. Not scanned: schema-level metadata (`id`, `name`,
`title`, `description`, `prefixes`, `see_also`), which names the schema's own
namespace; the evaluation-summary schema and the record/telemetry contracts,
which no generation phase reads.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "src" / "data_sheets_schema" / "schema"
GENERATION_ROOTS = ("data_sheets_schema.yaml", "data_sheets_schema_core.yaml")

#: Study names and aliases, the study platform, the real identifiers the
#: examples carried, and the design hallmarks of the study the example
#: family was modelled on. Case-insensitive where the token is a word.
STUDY_IDENTITY = [
    r"AI[-_ ]?READI", r"CM4AI", r"Cell Maps for AI", r"CHo?RUS", r"Bridge2AI[-_ ]Voice",
    r"Voice as a Biomarker", r"VOICE_PEDIATRIC", r"fairhub", r"salutogenesis",
    r"Heidelberg Spectralis", r"ETDRS", r"DeepDR", r"EYEPACS", r"UCSF Epic", r"OT2OD032644",
    r"IRB-300010084", r"IRB-811480", r"STUDY00017428", r"paperswithcode\.com/dataset/ai-readi",
    r"Bridge2AI standards", r"(?-i:\bVOICE\b)", r"(?-i:\bDACO\b)",
    # the study's real enrollment dates, participant and site counts (#1883)
    r"2023-07-18", r"2026-11-30", r"4,000 participants", r"3 collection sites",
]
#: The design hallmarks of the study the example family was modelled on.
#: These are ordinary biomedical words too: the study profile's pinned
#: registry vocabulary legitimately lists diabetes and retinal imaging, so
#: the `bridge2ai` digest is scanned for identity only, everything else for both.
STUDY_DESIGN = [r"T2DM", r"Type 2 Diabetes", r"diabet", r"retina", r"retinopathy",
                r"ophthalmolog", r"\bCGM\b", r"HbA1c", r"hba1c"]
#: The study's registry prefixes are declared (`prefixes:`, `values_from:`)
#: and rendered into the digest's vocabulary lists by design; what must not
#: appear is a sentence about them in a description (#1889). Scanned on the
#: parsed source fields only, never on a whole file or a digest.
PROSE_ONLY = [r"(?-i:\bB2AI_[A-Z]+)"]
IDENTITY = re.compile("|".join(STUDY_IDENTITY), re.IGNORECASE)
PATTERN = re.compile("|".join(STUDY_IDENTITY + STUDY_DESIGN), re.IGNORECASE)
PROSE = re.compile("|".join(STUDY_IDENTITY + STUDY_DESIGN + PROSE_ONLY), re.IGNORECASE)
MODEL_FACING_KEYS = {"description", "examples", "annotations", "comments", "title"}
SCHEMA_LEVEL_KEYS = {"id", "name", "title", "description", "prefixes", "see_also",
                     "default_prefix", "imports", "license", "default_range", "version",
                     "emit_prefixes", "subsets", "settings"}


def _closure(root: Path) -> list[Path]:
    """Every module the root imports, transitively. An unresolved file is an
    error: a scan that silently drops a module proves nothing (#1884)."""
    seen, todo = [], [root]
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        if not path.exists():
            raise FileNotFoundError(f"schema module not found: {path}")
        seen.append(path)
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for name in doc.get("imports") or []:
            if name.startswith("linkml:"):
                continue
            todo.append(path.parent / f"{name}.yaml")
    return seen


def _model_facing(path: Path):
    """(location, text) for every model-facing string below schema level."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = []

    def walk(node, where, under_model_facing):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{where}.{key}", under_model_facing or key in MODEL_FACING_KEYS)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{where}[{i}]", under_model_facing)
        elif isinstance(node, str) and under_model_facing:
            out.append((where, node))
    for key, value in doc.items():
        if key in SCHEMA_LEVEL_KEYS:
            continue
        walk(value, f"{path.name}:{key}", key in MODEL_FACING_KEYS)
    return out


def _findings(pairs):
    return [f"{where}: {match.group(0)!r} in {text[:90]!r}"
            for where, text in pairs for match in [PROSE.search(text)] if match]


class TestGenerationSchemaSources(unittest.TestCase):
    def test_the_generation_closure_is_the_modules_the_roots_import(self):
        closures = {root: [p.name for p in _closure(SCHEMA / root)] for root in GENERATION_ROOTS}
        self.assertEqual(len(closures["data_sheets_schema.yaml"]), 14)
        self.assertEqual(len(closures["data_sheets_schema_core.yaml"]), 14)
        names = {n for c in closures.values() for n in c}
        self.assertEqual(len(names), 16)
        for expected in ("D4D_Base_import.yaml", "D4D_Data_Governance.yaml", "D4D_Core.yaml",
                         "D4D_Human.yaml", "D4D_Composition.yaml", "D4D_FileCollection.yaml"):
            self.assertIn(expected, names)
        self.assertNotIn("D4D_Evaluation_Summary.yaml", names)
        self.assertNotIn("d4d_generation_record.yaml", names)

    def test_an_unresolved_import_fails_the_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "root.yaml"
            root.write_text("id: x\nname: x\nimports:\n  - linkml:types\n  - missing_module\n")
            with self.assertRaises(FileNotFoundError):
                _closure(root)

    def test_no_model_facing_text_names_the_study(self):
        pairs = [pair for root in GENERATION_ROOTS for p in _closure(SCHEMA / root)
                 for pair in _model_facing(p)]
        self.assertGreater(len(pairs), 500)
        self.assertEqual(_findings(pairs), [])

    def test_the_scanner_sees_what_it_scans(self):
        """A guard that cannot fail proves nothing: seeded modules go through
        the real closure and traversal, and every planted string is found
        where it was planted (#1884)."""
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "base.yaml"
            base.write_text(yaml.safe_dump({
                "id": "https://example.org/base", "name": "base",
                "description": "The AI-READI schema-level description is not scanned",
                "comments": ["a module-level VOICE comment is scanned"],
                "slots": {"title": {"description": "plain", "annotations": {"d4d:docExample": "AI-READI: title"}},
                          "topic": {"description": "the B2AI_TOPIC prefix is the natural home"},
                          "notes": {"comments": ["Verified on VOICE"], "examples": [{"value": "fairhub.io/x"}]},
                          "clean": {"description": "nothing here", "title": "CGM-free"}},
                "classes": {"Thing": {"attributes": {"topic": {"description": "as a term from the Bridge2AI standards registry"}}}},
            }, sort_keys=False))
            root = Path(d) / "root.yaml"
            root.write_text(yaml.safe_dump({"id": "https://example.org/root", "name": "root",
                                            "imports": ["linkml:types", "base"],
                                            "classes": {"Root": {"description": "Type 2 Diabetes cohort"}}}, sort_keys=False))
            pairs = [pair for p in _closure(root) for pair in _model_facing(p)]
        found = _findings(pairs)
        where = sorted(f.split(": ")[0] for f in found)
        self.assertEqual(where, sorted([
            "root.yaml:classes.Root.description",
            "base.yaml:comments[0]",
            "base.yaml:slots.title.annotations.d4d:docExample",
            "base.yaml:slots.topic.description",
            "base.yaml:slots.notes.comments[0]",
            "base.yaml:slots.notes.examples[0].value",
            "base.yaml:slots.clean.title",
            "base.yaml:classes.Thing.attributes.topic.description",
        ]))
        # lower-case "voice" is an ordinary word; the alias is uppercase only
        self.assertEqual(_findings([("v", "the voice of the participant")]), [])

    def test_examples_are_placeholders_not_real_identifiers(self):
        """The award and IRB examples were a real NIH award and three real
        IRB protocol numbers; a placeholder must keep the form and not the
        identity."""
        from data_sheets_schema.awards import NIH_AWARD
        text = (SCHEMA / "D4D_Motivation.yaml").read_text(encoding="utf-8")
        awards = {m.group(1) for m in NIH_AWARD.finditer(text)}
        self.assertEqual(awards, {"R01XX000000"})
        ethics = (SCHEMA / "D4D_Ethics.yaml").read_text(encoding="utf-8")
        self.assertNotRegex(ethics, r"IRB-\d{5,}")


class TestWhatEachArmConsumes(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema import schema_digest
        self._cwd = os.getcwd(); os.chdir(ROOT)
        schema_digest._TEXT_CACHE.clear()
        self._env = mock.patch.dict(os.environ, {}, clear=False); self._env.start()

    def tearDown(self):
        from data_sheets_schema import schema_digest
        schema_digest._TEXT_CACHE.clear()
        self._env.stop(); os.chdir(self._cwd)

    def test_the_native_toolchain_selects_clean_schemas_under_neutral(self):
        """The #1875 probe: what `agentic_runtime.toolchain()` hands the
        executable playbook under `D4D_PROFILE=neutral`."""
        os.environ["D4D_PROFILE"] = "neutral"
        from data_sheets_schema import agentic_runtime
        from data_sheets_schema.profiles import select_profile
        self.assertEqual(select_profile(None).profile.name, "neutral")
        environment = agentic_runtime.toolchain()
        playbook = agentic_runtime.playbook_text(environment)
        for logical in agentic_runtime.SCHEMAS:
            path = Path(environment["resources"][logical])
            self.assertIn(str(path), playbook, logical)
            text = path.read_text(encoding="utf-8")
            hits = sorted({m.group(0) for m in PATTERN.finditer(text)})
            self.assertEqual(hits, [], f"{logical} carries {hits}")

    def test_the_digest_is_clean_under_both_profiles(self):
        from data_sheets_schema import schema_digest
        from data_sheets_schema.profiles import profile_named
        for name, pattern in (("neutral", PATTERN), ("bridge2ai", IDENTITY)):
            for cls in ("Dataset", "CoreDataset"):
                text = schema_digest.digest_text(cls, profile=profile_named(name))
                hits = sorted({m.group(0) for m in pattern.finditer(text)})
                self.assertEqual(hits, [], f"{name}/{cls} carries {hits}")
        # The study digest does render its pinned vocabulary; that is the
        # profile's fact, and the neutral digest must not carry it.
        study = schema_digest.digest_text("Dataset", profile=profile_named("bridge2ai"))
        neutral = schema_digest.digest_text("Dataset", profile=profile_named("neutral"))
        self.assertNotEqual(study, neutral)


if __name__ == "__main__":
    unittest.main()
