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

    def test_a_prefix_resolves_and_a_project_prefers_the_directory_with_its_record(self):
        root = _corpus(self.root, {"claudecode_api": ["2026-02-02_b_rep1", "2026-02-02_b_rep2"]})
        self.assertEqual(method_for_label("2026-02-02_b", concat_dir=root), "claudecode_api")
        # No Q record anywhere: the directory that exists is the answer (#971), not an error.
        self.assertEqual(method_for_label("2026-02-02_b", "Q", concat_dir=root), "claudecode_api")

    def test_a_label_under_both_families_is_refused_not_guessed(self):
        root = _corpus(self.root, {"claudecode_agent": ["2026-03-03_c_rep1"], "claudecode_api": ["2026-03-03_c_rep1"]})
        with self.assertRaises(LookupError) as cm:
            method_for_label("2026-03-03_c_rep1", concat_dir=root)
        self.assertIn("both", str(cm.exception))

    def test_an_exact_directory_wins_over_a_prefix_match_elsewhere(self):
        """#970: `x_rep1` under one family is not confused with `x_rep10` under the other."""
        root = _corpus(self.root, {"claudecode_api": ["2026-09-01_cfg-v8_rep1"],
                                   "claudecode_agent": ["2026-09-01_cfg-v8_rep10"]})
        self.assertEqual(method_for_label("2026-09-01_cfg-v8_rep1", concat_dir=root), "claudecode_api")

    def test_a_label_directory_without_the_projects_record_still_resolves(self):
        """#971: the receipt check runs before the provenance record exists (#730)."""
        root = _corpus(self.root, {"claudecode_api": ["2026-09-04_x_rep1"]})
        (root / "claudecode_api_core" / "2026-09-04_x_rep1" / "P_provenance.yaml").unlink()
        self.assertEqual(method_for_label("2026-09-04_x_rep1", "P", concat_dir=root), "claudecode_api")
        # ... but a directory holding the record is preferred over one that does not.
        root = _corpus(self.root / "b", {"claudecode_api": ["2026-09-04_y_rep1"], "claudecode_agent": ["2026-09-04_y_rep1"]})
        (root / "claudecode_agent_core" / "2026-09-04_y_rep1" / "P_provenance.yaml").unlink()
        self.assertEqual(method_for_label("2026-09-04_y_rep1", "P", concat_dir=root), "claudecode_api")

    def test_a_label_shared_with_a_crate_arm_is_refused(self):
        """#973: the 2026-07-31 series exists under four arms; the baseline is not a safe default."""
        root = _corpus(self.root, {"claudecode_agent": ["2026-07-31_z_rep1"], "claudecode_agent_crate": ["2026-07-31_z_rep1"]})
        with self.assertRaises(LookupError) as cm:
            method_for_label("2026-07-31_z_rep1", concat_dir=root)
        self.assertIn("claudecode_agent_crate", str(cm.exception))

    def test_the_cli_helper_raises_a_click_error_not_a_traceback(self):
        import click
        from data_sheets_schema.cli.method import resolve_method
        from data_sheets_schema import provenance as pv
        keep = pv.CONCAT_DIR; pv.CONCAT_DIR = _corpus(self.root, {})
        try:
            with self.assertRaises(click.ClickException) as cm:
                resolve_method("nope")
            self.assertIn("no run labelled", str(cm.exception))
        finally:
            pv.CONCAT_DIR = keep

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

    def test_runs_select_resolves_the_v8_config(self):
        from data_sheets_schema.cli.runs import runs
        out = CliRunner().invoke(runs, ["select", "--project", "CM4AI", "--config", "2026-09-04_claude-opus-5-api-generic-v8"])
        self.assertNotIn("Traceback", out.output)
        self.assertNotIn("found 0", out.output, out.output[-400:])

    def test_compare_arms_reads_each_prefix_from_its_own_directory(self):
        """#973: v7 lives under claudecode_agent, v8 under claudecode_api."""
        from data_sheets_schema.cli.runs import runs
        out = CliRunner().invoke(runs, ["compare-arms", "--a", V7, "--b", "2026-09-04_claude-opus-5-api-generic-v8"])
        self.assertEqual(out.exit_code, 0, out.output[-600:])
        self.assertIn("3 label(s), 4 project(s)", out.output)
        self.assertIn("1 label(s), 1 project(s)", out.output)
        self.assertNotIn("No recorded procedural difference", out.output)

    def test_evaluate_spelling_refuses_a_prefix(self):
        from data_sheets_schema.cli.evaluate import evaluate
        out = CliRunner().invoke(evaluate, ["spelling", "--label", "2026-09-04_claude-opus-5-api-generic-v8", "--project", "CM4AI"])
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("not an exact label", out.output)

    def test_evaluate_verifiable_reads_labels_from_both_families(self):
        from data_sheets_schema.cli.evaluate import evaluate
        out = CliRunner().invoke(evaluate, ["verifiable", "--project", "CM4AI", "--label", f"{V7}_rep1", "--label", V8])
        self.assertEqual(out.exit_code, 0, out.output[-600:])
        self.assertIn(f"{V7}_rep1", out.output); self.assertIn(V8, out.output)
        out = CliRunner().invoke(evaluate, ["verifiable", "--project", "CM4AI", "--label", f"{V7}_rep1", "--method", "claudecode_api"])
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("not under claudecode_api", out.output)

    def test_receipts_check_finds_the_v8_record_without_a_method(self):
        from data_sheets_schema.cli.receipts import receipts
        out = CliRunner().invoke(receipts, ["check", "--label", V8, "--project", "CM4AI"])
        self.assertEqual(out.exit_code, 0, out.output[-600:])
        self.assertIn("chunks 28/28", out.output)


@unittest.skipUnless(Path(f"data/d4d_concatenated/claudecode_api_core/{V8}").exists(), "v8 canary not on disk")
class TestPreRecordReceiptCheck(unittest.TestCase):
    def test_receipts_check_before_the_record_exists_resolves_and_runs(self):
        """#971: the Phase-1 path of the agentic playbook — receipt and full record on disk, no record yet."""
        import shutil
        from data_sheets_schema import provenance as pv
        from data_sheets_schema.cli.receipts import receipts
        src_core = Path(f"data/d4d_concatenated/claudecode_api_core/{V8}")
        src_full = Path(f"data/d4d_concatenated/claudecode_api/{V8}")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "claudecode_api_core" / V8).mkdir(parents=True); (root / "claudecode_api" / V8).mkdir(parents=True)
            for name in ("CM4AI_coverage_receipt.yaml", "CM4AI_d4d_core.yaml"):
                shutil.copy(src_core / name, root / "claudecode_api_core" / V8 / name)
            shutil.copy(src_full / "CM4AI_d4d.yaml", root / "claudecode_api" / V8 / "CM4AI_d4d.yaml")
            keep = pv.CONCAT_DIR; pv.CONCAT_DIR = root
            try:
                out = CliRunner().invoke(receipts, ["check", "--label", V8, "--project", "CM4AI"])
            finally:
                pv.CONCAT_DIR = keep
        self.assertNotIn("Traceback", out.output)
        self.assertIn("chunks 28/28", out.output, out.output[-600:])


class TestBaselineAcrossTheFamily(unittest.TestCase):
    def test_a_prefix_spanning_both_runtimes_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _corpus(Path(tmp), {"claudecode_agent": ["2026-09-01_v7_rep1"], "claudecode_api": ["2026-09-04_v8_rep1"]})
            for d in root.glob("*_core/*/P_provenance.yaml"):
                d.write_text(yaml.safe_dump({"pair_consistency": {"ran": True, "errors": 0}}))
            with self.assertRaises(LookupError):
                canary.baseline_for("P", "2026-09-0", concat_dir=root)
            self.assertEqual(canary.baseline_for("P", "2026-09-01", concat_dir=root)["pair errors"], 0)

    def test_the_baseline_finds_a_prefix_in_either_directory_when_no_method_is_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for method, label, errors in (("claudecode_agent", "2026-05-05_v7_rep1", 1),
                                          ("claudecode_api", "2026-05-06_v8_rep1", 3)):
                d = root / f"{method}_core" / label; d.mkdir(parents=True)
                (d / "P_provenance.yaml").write_text(yaml.safe_dump({
                    "pair_consistency": {"ran": True, "errors": errors}, "report_claims": {"checked": True, "findings": []},
                    "grounding": {"checked": True}, "form": {"checked": True}}))
            self.assertEqual(canary.baseline_for("P", "2026-05-05_v7", concat_dir=root)["pair errors"], 1)
            self.assertEqual(canary.baseline_for("P", "2026-05-06_v8", concat_dir=root)["pair errors"], 3)
            self.assertEqual(canary.report_basis("P", "2026-05-06_v8", concat_dir=root)["vacuous"], 1)


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

    def test_a_review_of_a_different_pair_is_carried_as_stale(self):
        """#969: the review's evidence names the md5s of the pair it read."""
        old = {"ran": True, "artifacts": {"full": {"md5": "a"}, "core": {"md5": "b"}}, "semantic_review": self.REVIEW}
        same = backfill_checks.carry_attestations("pair_consistency", old, {"ran": True, "artifacts": old["artifacts"]})
        self.assertEqual(same["semantic_review"], self.REVIEW)
        moved = backfill_checks.carry_attestations("pair_consistency", old,
                                                   {"ran": True, "artifacts": {"full": {"md5": "c"}, "core": {"md5": "b"}}})
        self.assertTrue(moved["semantic_review"]["stale"])
        self.assertEqual(moved["semantic_review"]["attested_artifacts"], old["artifacts"])
        self.assertEqual(moved["semantic_review"]["verdict"], "consistent")

    def test_a_re_record_keeps_the_review_and_a_recheck_keeps_reliability(self):
        """#973: the record writer and `review check --write` both rebuilt blocks from scratch."""
        from data_sheets_schema.provenance import ProvenanceRecord
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "P_provenance.yaml"
            p.write_text(yaml.safe_dump({"run": {}, "pair_consistency": {"ran": True, "errors": 1, "artifacts": {"full": {"md5": "a"}},
                                                                         "semantic_review": self.REVIEW},
                                         "review": {"checked": True, "artifacts": {"pack": {"sha256": "p"}},
                                                    "reliability": {"kappa": 0.8}}}))
            rec = ProvenanceRecord(data={"run": {}, "pair_consistency": {"ran": True, "errors": 0, "artifacts": {"full": {"md5": "a"}}},
                                         "review": {"checked": True, "artifacts": {"pack": {"sha256": "q"}}}})
            rec.write(p)
            out = yaml.safe_load(p.read_text().split("\n", 2)[2])
            self.assertEqual(out["pair_consistency"]["semantic_review"], self.REVIEW)          # same artifacts
            self.assertEqual(out["review"]["reliability"]["kappa"], 0.8)
            self.assertTrue(out["review"]["reliability"]["stale"])                              # pack moved

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
