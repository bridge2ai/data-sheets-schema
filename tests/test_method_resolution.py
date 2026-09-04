"""Downstream commands find a run's directory from its label (#934); strict
receipts fail only on the gate's classes (#881); a reviewer's pair
attestation survives recomputation (#856).

From generic_v8 the API baseline writes under `claudecode_api` (#690) while
every downstream `--method` default still said `claudecode_agent` — the
wrong directory for a v8 run, silently. The default is now the directory
the label lives in, and an ambiguous or absent label is an error that says
so rather than a guess.
"""

import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

from data_sheets_schema import backfill_checks, canary
from data_sheets_schema.cli.receipts import strict_failure
from data_sheets_schema.runs import AGENT_FAMILY, method_for_label

V8 = "2026-09-04_claude-opus-5-api-generic-v8_rep1"
V7 = "2026-09-01_claude-opus-5-api-generic-v7"


def _corpus(tmp: Path, layout: dict[str, list[str]]) -> Path:
    """{method: [label, ...]} -> a concat dir with a P provenance record per label."""
    for method, labels in layout.items():
        for label in labels:
            d = tmp / f"{method}_core" / label
            d.mkdir(parents=True)
            (d / "P_provenance.yaml").write_text("run: {}\n")
    return tmp


class TestResolver(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_an_exact_label_resolves_to_its_directory(self):
        root = _corpus(self.root, {"claudecode_agent": ["2026-01-01_a_rep1"], "claudecode_api": ["2026-02-02_b_rep1"]})
        self.assertEqual(method_for_label("2026-01-01_a_rep1", concat_dir=root), "claudecode_agent")
        self.assertEqual(method_for_label("2026-02-02_b_rep1", "P", concat_dir=root), "claudecode_api")

    def test_a_prefix_resolves_and_a_project_filters(self):
        root = _corpus(self.root, {"claudecode_api": ["2026-02-02_b_rep1", "2026-02-02_b_rep2"]})
        self.assertEqual(method_for_label("2026-02-02_b", concat_dir=root), "claudecode_api")
        with self.assertRaises(LookupError):
            method_for_label("2026-02-02_b", "Q", concat_dir=root)        # no Q record

    def test_a_label_under_both_families_is_refused_not_guessed(self):
        root = _corpus(self.root, {"claudecode_agent": ["2026-03-03_c_rep1"], "claudecode_api": ["2026-03-03_c_rep1"]})
        with self.assertRaises(LookupError) as cm:
            method_for_label("2026-03-03_c_rep1", concat_dir=root)
        self.assertIn("both", str(cm.exception))

    def test_an_absent_label_names_the_directories_searched(self):
        with self.assertRaises(LookupError) as cm:
            method_for_label("nope", concat_dir=_corpus(self.root, {}))
        for m in AGENT_FAMILY:
            self.assertIn(m, str(cm.exception))


@unittest.skipUnless(Path(f"data/d4d_concatenated/claudecode_api_core/{V8}").exists(), "v8 canary not on disk")
class TestAgainstTheCorpus(unittest.TestCase):
    def test_the_v8_canary_resolves_to_the_api_directory_and_v7_to_the_agent_one(self):
        self.assertEqual(method_for_label(V8, "CM4AI"), "claudecode_api")
        self.assertEqual(method_for_label(V7, "CM4AI"), "claudecode_agent")

    def test_receipts_check_finds_the_v8_record_without_a_method(self):
        from data_sheets_schema.cli.receipts import receipts
        out = CliRunner().invoke(receipts, ["check", "--label", V8, "--project", "CM4AI"])
        self.assertEqual(out.exit_code, 0, out.output[-600:])
        self.assertIn("chunks 28/28", out.output)


class TestBaselineAcrossTheFamily(unittest.TestCase):
    def test_the_baseline_reads_both_directories_when_no_method_is_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for method, errors in (("claudecode_agent", 1), ("claudecode_api", 3)):
                d = root / f"{method}_core" / "2026-05-05_x_rep1"; d.mkdir(parents=True)
                (d / "P_provenance.yaml").write_text(yaml.safe_dump({
                    "pair_consistency": {"ran": True, "errors": errors}, "report_claims": {"checked": True, "findings": []},
                    "grounding": {"checked": True}, "form": {"checked": True}}))
            self.assertEqual(canary.baseline_for("P", "2026-05-05_x", concat_dir=root)["pair errors"], 3)
            self.assertEqual(canary.baseline_for("P", "2026-05-05_x", method="claudecode_agent", concat_dir=root)["pair errors"], 1)
            self.assertEqual(canary.report_basis("P", "2026-05-05_x", concat_dir=root)["vacuous"], 2)


class TestStrictIsTheGate(unittest.TestCase):
    """#881: the CLI and the canary gate must fail on the same receipt classes."""

    CLEAN = {"checked": True, "expected": True, "chunks": {"total": 3, "reviewed": 3},
             "snippets": {"total": 8, "verified": 8, "mismatched": 0, "unchecked": 0},
             "slots": {"addressing_slips_count": 0}, "findings": [], "findings_gated": 0}

    def test_wrong_chunk_attributions_do_not_fail_strict(self):
        block = {**self.CLEAN, "findings": [{"kind": "snippet_adjacent_chunk"}] * 26}
        self.assertFalse(strict_failure(block))

    def test_the_gates_classes_do(self):
        self.assertTrue(strict_failure({**self.CLEAN, "chunks": {"total": 3, "reviewed": 2}}))
        self.assertTrue(strict_failure({**self.CLEAN, "findings_gated": 1,
                                        "findings": [{"kind": "slot_not_in_record"}]}))
        self.assertTrue(strict_failure({**self.CLEAN, "snippets": {"total": 8, "verified": 0, "mismatched": 0, "unchecked": 0}}))


class TestAttestationsSurvive(unittest.TestCase):
    """#856: `pair_consistency.semantic_review` is a reviewer's verdict, not the checker's."""

    REVIEW = {"warning": "semantic-review-required", "verdict": "consistent", "reviewed_by": "a reviewer"}

    def test_carry_attestations_keeps_the_review_and_takes_the_new_counts(self):
        old = {"ran": True, "errors": 2, "semantic_review": self.REVIEW}
        new = {"ran": True, "errors": 0}
        out = backfill_checks.carry_attestations("pair_consistency", old, new)
        self.assertEqual((out["errors"], out["semantic_review"]), (0, self.REVIEW))
        self.assertNotIn("semantic_review", new, "the new block is not mutated")
        self.assertEqual(backfill_checks.carry_attestations("form", {"x": 1}, {"y": 2}), {"y": 2})

    def test_apply_with_overwrite_keeps_the_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "P_provenance.yaml"
            p.write_text("# header\n" + yaml.safe_dump({"run": {}, "pair_consistency": {"ran": True, "errors": 2,
                                                                                         "semantic_review": self.REVIEW}}))
            backfill_checks.apply(p, {"pair_consistency": {"ran": True, "errors": 0, "checked": True}}, overwrite=True)
            rec = yaml.safe_load(p.read_text().split("\n", 1)[1])
            self.assertEqual(rec["pair_consistency"]["errors"], 0)
            self.assertEqual(rec["pair_consistency"]["semantic_review"], self.REVIEW)


if __name__ == "__main__":
    unittest.main()
