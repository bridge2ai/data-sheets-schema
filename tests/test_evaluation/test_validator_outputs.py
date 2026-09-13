"""An evaluator checks only its new output, with no historical exemptions."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_evaluation.test_semantic_evaluation_contract import (
    _validator,
)
from tests.test_evaluation.test_semantic_context_scope import record, ROOT


class NewEvaluationOutputs(unittest.TestCase):
    def setUp(self):
        self.m = _validator()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input_path = self.definition_path = None

    def make(self, rubric):
        doc, self.input_path = record(self.root, rubric)
        self.definition_path = ROOT / f".claude/agents/d4d-{rubric}-semantic.md"
        return doc

    def write(self, name, doc):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc))
        return path

    def check(self, paths, rubric=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = self.m.validate_outputs(paths, rubric, input_path=self.input_path,
                                             definition_path=self.definition_path)
        return status, output.getvalue()

    def test_each_rubric_accepts_its_documented_contract(self):
        for name in ("rubric10", "rubric20"):
            rubric, doc = name + "-semantic", self.make(name)
            with self.subTest(rubric=rubric):
                self.assertEqual(self.check([self.write("answer.json", doc)], rubric)[0], 0)

    def test_cli_checks_the_named_file_without_opening_its_siblings(self):
        answer = self.write("answer.json", self.make("rubric10"))
        self.write("another_evaluation.json", {"rubric": "not a real rubric"})
        with patch.object(self.m, "load_evaluation", wraps=self.m.load_evaluation) as read:
            self.assertEqual(self.check([answer], "rubric10-semantic")[0], 0)
            read.assert_called_once_with(answer)
        result = subprocess.run(
            [sys.executable, self.m.__file__, "--file", str(answer),
             "--input", str(self.input_path), "--agent-definition", str(self.definition_path),
             "--rubric", "rubric10-semantic"], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(str(answer), result.stdout)
        self.assertNotIn("another_evaluation", result.stdout)

    def test_new_output_cannot_use_archive_or_superseded_exemptions(self):
        bad = self.make("rubric10")
        bad["semantic_analysis"]["issues_detected"][0]["severity"] = "info"
        for name in ("label_aware/answer.json", "2026-09-11/answer.json",
                     "_archive/answer.json", "superseded/answer.json"):
            with self.subTest(name=name):
                status, output = self.check([self.write(name, bad)])
                self.assertEqual(status, 1)
                self.assertIn("severity", output)
        old_shape = {"rubric": "rubric10-semantic", "summary_scores": {}}
        self.assertEqual(self.check([self.write("old.json", old_shape)])[0], 1)

    def test_unreadable_unjudged_or_wrong_rubric_output_fails(self):
        for doc in (None, [], {"rubric": "rubric10"}, {"rubric": []}, {}):
            with self.subTest(doc=doc):
                self.assertEqual(self.check([self.write("answer.json", doc)])[0], 1)
        self.assertEqual(self.check([self.root / "missing.json"])[0], 1)
        wrong = self.write("wrong.json", self.make("rubric20"))
        status, output = self.check([wrong], "rubric10-semantic")
        self.assertEqual(status, 1)
        self.assertIn("expected rubric10-semantic", output)

    def test_one_bad_file_fails_the_whole_explicit_selection(self):
        good = self.write("good.json", self.make("rubric10"))
        bad = self.write("bad.json", {})
        status, output = self.check([bad, good])
        self.assertEqual(status, 1)
        self.assertIn(f"INVALID {bad}", output)
        self.assertIn(f"VALID {good}", output)
