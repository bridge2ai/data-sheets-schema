"""`scripts/validate_evaluation_schema.py` judges every evaluation on disk.

#833: the discovery loop was `{rubric}_semantic/concatenated/*.json` — one
directory per rubric, one level deep. It reached 28 of the 204 semantic
artifacts in the repository and never looked at `label_aware/`, which is
where every evaluation since 2026-08 lives and which the cross-arm table
reads. A schema-invalid artifact sat there unreported.
"""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_evaluation_schema.py"


def _module():
    spec = importlib.util.spec_from_file_location("validate_evaluation_schema", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Discovery(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_every_evaluation_at_any_depth_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for rel in ("r10/concatenated/A_evaluation.json",
                        "r10/label_aware/B_evaluation.json",
                        "r10/label_aware/superseded_gate_v1/C_evaluation.json",
                        "r20/concatenated/2026-07-22_opus-4.8/D_evaluation.json",
                        "r20/concatenated/_archive_2026-07-22/E_evaluation.json"):
                p = base / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("{}")
            (base / "r10" / "label_aware" / "notes.json").write_text("{}")     # not an evaluation
            found = {p.name for p in self.m.discover(base)}
            self.assertEqual(found, {"A_evaluation.json", "B_evaluation.json", "C_evaluation.json",
                                     "D_evaluation.json", "E_evaluation.json"})

    def test_an_archive_marker_anywhere_above_the_file_marks_it_kept(self):
        base = Path("/base")
        for rel, kept in (("r10/label_aware/B_evaluation.json", False),
                          ("r10/concatenated/A_evaluation.json", False),
                          ("r10/label_aware/superseded_gate_v1/C_evaluation.json", True),
                          ("r10/label_aware/superseded_fable5/C_evaluation.json", True),
                          ("r20/concatenated/_archive_2026-07-22/E_evaluation.json", True),
                          ("r20/concatenated/2026-07-22_opus-4.8/D_evaluation.json", True),
                          # the marker must be a directory, not the file itself
                          ("r10/label_aware/superseded_evaluation.json", False)):
            with self.subTest(rel):
                self.assertEqual(self.m.is_kept(base / rel, base), kept)


class TheRepositoryState(unittest.TestCase):
    """What the corpus actually holds, so a regression in either direction is
    visible. These are counts, not floors: update them with the reason."""

    def setUp(self):
        self.m = _module()
        self.base = ROOT / "data" / "evaluation_llm"
        if not self.base.exists():
            self.skipTest("no evaluation corpus in this checkout")

    def test_the_label_aware_evaluations_are_judged(self):
        found = self.m.discover(self.base)
        label_aware = [p for p in found if "label_aware" in p.parts]
        self.assertGreater(len(label_aware), 100)
        # and the one the old loop reached is still reached
        self.assertTrue(any("concatenated" in p.parts for p in found))

    def test_the_only_live_invalid_rubric10_artifact_is_the_one_833_names(self):
        """Its `severity: info` is commentary; `overall_score` is intact, so
        the score the cross-arm table reads is unaffected. Kept as written —
        it is what the evaluator produced."""
        schema = self.m.load_schema(ROOT / "src" / "download" / "prompts" / "rubric10_semantic_schema.json")
        bad = []
        for p in self.m.discover(self.base):
            if self.m.is_kept(p, self.base):
                continue
            d = json.loads(p.read_text())
            if d.get("rubric") != "rubric10-semantic":
                continue
            if self.m.classify(d, schema)[0] == "invalid":
                bad.append(p.name)
        self.assertEqual(bad, ["AI_READI_2026-08-28dapi_rep1_evaluation.json"])


class ExitCode(unittest.TestCase):
    """#833 asked for a regression test that a schema-invalid label-aware
    artifact makes the run fail. Four tests of the helpers did not reach the
    exit code, which is the whole point of the check: the artifact it was
    filed about had been sitting in `label_aware/` unreported."""

    def setUp(self):
        self.m = _module()
        self.schema_dir = ROOT / "src" / "download" / "prompts"
        if not (self.schema_dir / "rubric10_semantic_schema.json").exists():
            self.skipTest("no schemas in this checkout")
        good = ROOT / "data" / "evaluation_llm" / "rubric10_semantic" / "label_aware"
        cands = [p for p in good.glob("*_evaluation.json")
                 if self.m.classify(json.loads(p.read_text()),
                                    self.m.load_schema(self.schema_dir / "rubric10_semantic_schema.json"))[0] == "valid"]
        if not cands:
            self.skipTest("no valid rubric10-semantic artifact to build from")
        self.valid = json.loads(cands[0].read_text())

    def _tree(self, tmp, where, doc):
        d = Path(tmp) / "rubric10_semantic" / where
        d.mkdir(parents=True, exist_ok=True)
        (d / "X_evaluation.json").write_text(json.dumps(doc))
        return Path(tmp)

    def _invalid(self):
        doc = json.loads(json.dumps(self.valid))
        issues = doc.setdefault("semantic_analysis", {}).setdefault("issues_detected", [])
        if issues:
            issues[0]["severity"] = "info"          # the value the schema does not admit
        else:
            issues.append({"severity": "info", "issue": "x", "location": "x", "recommendation": "x"})
        return doc

    def test_a_valid_label_aware_artifact_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._tree(tmp, "label_aware", self.valid)
            self.assertEqual(self.m.main(eval_base=base, schema_dir=self.schema_dir), 0)

    def test_an_invalid_label_aware_artifact_fails_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._tree(tmp, "label_aware", self._invalid())
            self.assertEqual(self.m.main(eval_base=base, schema_dir=self.schema_dir), 1)

    def test_the_same_artifact_under_an_archive_marker_does_not(self):
        """Kept evidence is reported and never rewritten to pass, so it must
        not fail the run either."""
        for where in ("label_aware/superseded_fable5", "concatenated/_archive_2026-07-22",
                      "concatenated/2026-07-22_opus-4.8", "concatenated/2026-07-22"):
            with self.subTest(where):
                with tempfile.TemporaryDirectory() as tmp:
                    base = self._tree(tmp, where, self._invalid())
                    self.assertEqual(self.m.main(eval_base=base, schema_dir=self.schema_dir), 0)

    def test_an_unreadable_artifact_in_a_live_directory_fails_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            d = base / "rubric10_semantic" / "label_aware"; d.mkdir(parents=True)
            (d / "X_evaluation.json").write_text("{not json")
            self.assertEqual(self.m.main(eval_base=base, schema_dir=self.schema_dir), 1)

    def test_non_object_json_does_not_abort_the_remaining_inventory(self):
        for doc in (None, [], "not an object"):
            for kept in (False, True):
                with self.subTest(doc=doc, kept=kept), tempfile.TemporaryDirectory() as tmp:
                    base = self._tree(tmp, "label_aware", self.valid)
                    bad_dir = base / "_archive" if kept else base
                    bad_dir.mkdir(exist_ok=True)
                    (bad_dir / "A_evaluation.json").write_text(json.dumps(doc))
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        result = self.m.main(eval_base=base, schema_dir=self.schema_dir)
                    self.assertEqual(result, 0 if kept else 1)
                    self.assertIn("evaluation must be a JSON object", output.getvalue())
                    self.assertRegex(output.getvalue(), r"live\s+valid\s+1")
                    where = "kept" if kept else "live"
                    self.assertRegex(output.getvalue(), where + r"\s+valid[^\n]+unreadable\s+1")
