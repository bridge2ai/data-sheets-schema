"""The generation-specificity audit skill runs and can see (#4007).

`.claude/skills/d4d-generation-specificity-audit/scan.py` finds Grand
Challenge project, Bridge2AI program and biomedical/clinical specificity in
the generation surfaces of every approach, and reports what "api" means in
the code. These tests pin that the scanner is not blind: its self-test plants
one token per category, a token planted in a copy of a real surface file is
reported as a violation, the tracked-exceptions file parses with a reason on
every entry, and the API-meaning section names the live conditions.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "d4d-generation-specificity-audit"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("d4d_specificity_scan", SKILL / "scan.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module          # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


scan = _load_scanner()


class TestTheSkillFiles(unittest.TestCase):
    def test_the_skill_declares_name_and_description(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        front = text.split("---", 2)[1]
        self.assertIn("name: d4d-generation-specificity-audit", front)
        self.assertIn("description:", front)

    def test_the_exceptions_file_parses_and_every_entry_has_a_reason(self):
        entries = scan.load_exceptions(SKILL / "exceptions.yaml")
        self.assertGreater(len(entries), 0)
        for e in entries:
            self.assertTrue(e["reason"].strip(), e)
            self.assertTrue(e["decision"].strip(), e)
        globs = {g for e in entries for g in e["_paths"]}
        for seeded in ("src/data_sheets_schema/profiles.py", "data/preprocessed/source_manifest.yaml",
                       "src/download/prompts/components/*.md",
                       "src/data_sheets_schema/constants/projects.py"):
            self.assertIn(seeded, globs)

    def test_a_malformed_exception_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "x.yaml"
            bad.write_text("exceptions:\n  - path: a.py\n    category: gc_project\n    decision: '#1'\n")
            with self.assertRaisesRegex(ValueError, "reason"):
                scan.load_exceptions(bad)
            bad.write_text("exceptions:\n  - path: a.py\n    reason: r\n    decision: d\n")
            with self.assertRaisesRegex(ValueError, "token"):
                scan.load_exceptions(bad)

    def test_the_tokens_come_from_the_neutrality_test_and_the_skill(self):
        tokens = scan.load_tokens(ROOT)
        sources = {t.source for t in tokens}
        self.assertIn("tests/test_neutral_generation_schema.py:STUDY_IDENTITY", sources)
        self.assertIn("tokens.yaml", sources)
        self.assertEqual({t.category for t in tokens}, set(scan.CATEGORIES))


class TestTheScannerSees(unittest.TestCase):
    def setUp(self):
        self.tokens = scan.load_tokens(ROOT)

    def test_the_seeded_self_test_passes(self):
        result = scan.self_test(self.tokens)
        self.assertTrue(result["passed"], result["problems"])

    def test_a_scanner_with_no_tokens_fails_its_self_test(self):
        self.assertFalse(scan.self_test([])["passed"])

    def _planted(self, rel: str, line: str):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / rel).parent.mkdir(parents=True)
            shutil.copy(ROOT / rel, root / rel)
            text = (root / rel).read_text(encoding="utf-8")
            if not text.endswith("\n"):
                text += "\n"
            (root / rel).write_text(text + line + "\n", encoding="utf-8")
            planted_at = len((text + line).splitlines())
            surface = scan.Surface(rel, ["native_agentic"], "model_facing", "live", "test")
            hits = scan.scan_file(root, surface, self.tokens)
        for h in hits:
            h["exception"] = None
            h["violation"] = scan.is_violation(h)
        return [h for h in hits if h["line"] == planted_at], hits

    def test_a_gc_token_planted_in_a_playbook_is_a_violation(self):
        planted, _ = self._planted(".claude/commands/d4d-full-core.md",
                                   "Prefer the CM4AI release notes when two sources disagree.")
        self.assertTrue(planted)
        self.assertEqual({h["category"] for h in planted}, {"gc_project"})
        self.assertTrue(all(h["violation"] for h in planted))

    def test_a_project_branch_planted_in_runner_code_is_a_violation(self):
        # the branch is the line before the planted `pass`
        _, hits = self._planted("src/data_sheets_schema/healthsheet.py",
                                "if __name__ == 'VOICE_PEDIATRIC':\n    pass")
        branch = [h for h in hits if h["match"] == "VOICE_PEDIATRIC" and h["context"] == "code_branch"]
        self.assertTrue(branch)
        self.assertTrue(all(h["violation"] for h in branch))

    def test_a_comment_is_reported_but_does_not_fail(self):
        _, hits = self._planted("src/data_sheets_schema/healthsheet.py", "# measured on CHORUS rep1")
        comment = [h for h in hits if h["context"] == "comment" and h["match"] == "CHORUS"]
        self.assertTrue(comment)
        self.assertFalse(any(h["violation"] for h in comment))

    def test_text_above_the_prompt_body_is_header_not_model_facing(self):
        units = list(scan._markdown_units("# v9\nCHORUS rep2 changelog\n## Prompt body\nRead it.\n",
                                          prompt_header=True))
        self.assertEqual([u[1] for u in units][:3], ["header", "header", "header"])
        self.assertNotIn("header", [u[1] for u in units][3:])


class TestApiMeaning(unittest.TestCase):
    def test_the_section_names_every_live_condition_and_derives_its_shape(self):
        from data_sheets_schema.api_runner import CONDITION_PROMPTS, PHASES
        cond = scan.condition_table(ROOT)
        self.assertEqual(set(cond["prompts"]), set(CONDITION_PROMPTS))
        self.assertEqual(cond["phases"], list(PHASES))
        meaning = scan.api_meaning(ROOT, {"conditions": cond})
        self.assertTrue(cond["live"])
        self.assertIn("generic", cond["live"])
        for name in cond["live"]:
            self.assertIn(name, meaning["conditions"])
            self.assertEqual(meaning["conditions"][name]["status"], "live")
            self.assertIn(meaning["conditions"][name]["shape"], {"MONOLITHIC", "MULTI-PHASE"})
        self.assertEqual(set(meaning["conditions"]), set(CONDITION_PROMPTS))
        self.assertTrue(meaning["verdict"])

    def test_the_legacy_concatenated_script_is_classified(self):
        meaning = scan.api_meaning(ROOT, {"conditions": scan.condition_table(ROOT)})
        self.assertIn("src/download/process_concatenated_d4d_claude.py", meaning["legacy"])


@pytest.mark.corpus   # walks every generation surface of the repository (~15 s)
class TestTheWholeAudit(unittest.TestCase):
    def test_the_audit_runs_and_its_exit_status_is_its_violations(self):
        result = scan.run(ROOT)
        self.assertTrue(result["self_test"]["passed"])
        self.assertEqual(result["exit"], 1 if result["violations"] else 0)
        approaches = {a for s in result["surfaces"].values() for a in s["approaches"]}
        self.assertEqual(approaches, set(scan.APPROACHES))
        for v in result["violations"]:
            self.assertEqual(v["category"], "gc_project")
            self.assertIsNone(v["exception"])
        markdown = scan.render_markdown(result)
        for live in result["facts"]["conditions"]["live"]:
            self.assertIn(f"| {live} |", markdown)

    def test_every_model_facing_module_is_in_a_discovered_closure(self):
        _, facts = scan.discover(ROOT)
        stems = {Path(p).stem for p in facts["api_closure"] + facts["native_closure"]}
        stems |= {"healthsheet", "rocrate_normalize"}
        self.assertEqual(scan.MODEL_FACING_MODULES - stems, set())


if __name__ == "__main__":
    unittest.main()
