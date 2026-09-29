"""The recall-target baseline (#2930): lineage, variables and versioned
software per record and arm, and the receipt chunks marked
`nothing_relevant`/`redundant_with` that carry a lexical cue.

The synthetic corpus pins what a count means — which keys, at what depth,
what an entry is — that a record with no receipt reads None and never 0,
that the chunk text is the bytes the record hashed under its own rule, and
that the committed note is what the records reproduce.
"""
import contextlib
import hashlib
import importlib.util
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recall_target_baseline.py"

RULE = {"version": 2, "unit": "source-document", "boundary": "FILE: line followed by PATH: or ROLE:",
        "preamble": "own-chunk", "split": "line-window", "max_lines": 400, "max_bytes": 48000}
#: Three chunks under RULE: the preamble, then one per FILE: document.
BUNDLE = ("Summary of the bundle.\n"
          "FILE: a.txt\nPATH: a.txt\nThis release is derived from the 2023 cohort; see the data dictionary.\n"
          "FILE: b.txt\nPATH: b.txt\nContact the team by email.\n"
          "FILE: c.txt\nPATH: c.txt\nProcessed with toolkit version 2.4.1 and 12 variables.\n")


def _script():
    spec = importlib.util.spec_from_file_location("recall_target_baseline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Counting(unittest.TestCase):
    def setUp(self):
        self.m = _script()

    def test_lineage_and_variables_are_populated_entries_at_any_depth(self):
        record = {
            "was_derived_from": "The 2023 cohort release",
            "parent_datasets": [{"id": "doi:10.1/p"}, {}, {"name": ""}],
            "variables": [{"variable_name": "age"}, {"variable_name": "sex"}, None],
            "resources": [{"was_derived_from": ["doi:10.1/a", "", "doi:10.1/b"],
                           "variables": [{"variable_name": "hr", "description": None}]}],
            "description": "derived from nothing counted here",
        }
        c = self.m.target_counts(record)
        self.assertEqual((c["was_derived_from"], c["parent_datasets"], c["lineage"], c["variables"]), (3, 1, 4, 3))

    def test_an_empty_slot_counts_zero(self):
        c = self.m.target_counts({"was_derived_from": "", "parent_datasets": [], "variables": None})
        self.assertEqual((c["lineage"], c["variables"]), (0, 0))

    def test_software_counts_entries_with_a_populated_version(self):
        record = {"preprocessing_strategies": [{"used_software": [
            {"name": "a", "version": "3.0.0"}, {"name": "b", "version": ""}, {"name": "c"}]}],
            "machine_annotation_tools": [{"tools": ["Whisper Large", "openSMILE v3.0.1", "Praat version 6",
                                                    "spaCy 3.5.0", ""]}]}
        c = self.m.target_counts(record)
        self.assertEqual((c["software"], c["software_versioned"]), (3, 1))
        self.assertEqual((c["tools"], c["tools_versioned"]), (4, 3))

    def test_tools_version_reads_two_part_and_named_versions_but_not_model_names(self):
        """#3301: `v.gpt-4-1106-preview` (a committed v6 CM4AI record) and a
        bare two-part version are versions in a `tools` string; a hyphenated
        model name, `node2vec` and a stated `unknown` are not."""
        versioned = ["GPT-4 v.gpt-4-1106-preview", "samtools 1.9", "Python 3.11", "node2vec v0.4",
                     "tool v2", "Praat version 6", "spaCy 3.5.0"]
        plain = ["GPT-4", "GPT-4 unknown", "OHNLP toolkit unknown", "DenseNet-121", "node2vec",
                 "OpenAI Whisper Large", "Speech Articulatory Coding (sparc)"]
        c = self.m.target_counts({"machine_annotation_tools": [{"tools": versioned + plain}]})
        self.assertEqual((c["tools"], c["tools_versioned"]), (len(versioned) + len(plain), len(versioned)))
        for t in versioned:
            self.assertTrue(self.m.TOOL_VERSION.search(t), t)
        for t in plain:
            self.assertFalse(self.m.TOOL_VERSION.search(t), t)

    def test_the_chunk_version_cue_stays_narrow_for_prose_decimals(self):
        """The chunk cue does not read a bare decimal as a version (#3301)."""
        self.assertEqual(self.m.chunk_cues("Sessions lasted 4.5 hours (p < 0.05)."), {})


class Cues(unittest.TestCase):
    def setUp(self):
        self.m = _script()

    def test_each_class_is_detected_and_plain_text_is_not(self):
        self.assertEqual(set(self.m.chunk_cues("The data are derived  from\nthe parent dataset.")), {"lineage"})
        self.assertEqual(set(self.m.chunk_cues("See the data dictionary for column names.")), {"variables"})
        self.assertEqual(set(self.m.chunk_cues("Built with release 4.0 of the pipeline.")), {"version"})
        self.assertEqual(self.m.chunk_cues("Contact the team by email."), {})

    def test_matches_are_counted_per_pattern(self):
        hits = self.m.chunk_cues("variables, variable and a codebook; v1.2 and 1.2.3")
        self.assertEqual(hits["variables"], {"var.variable": 2, "var.codebook": 1})
        self.assertEqual(hits["version"], {"ver.version-token": 2})

    def test_cues_match_over_whitespace_collapsed_text(self):
        # var.codebook allows one whitespace character (code\s?books?), so a line
        # break plus a space between the words matches only after the collapse (#3312).
        self.assertEqual(self.m.chunk_cues("see the code \n book"), {"variables": {"var.codebook": 1}})

    def test_only_chunks_marked_nothing_relevant_or_redundant_with_are_candidates(self):
        receipt = {"chunks": [
            {"id": "c001", "status": "extracted", "extracted": []},
            {"id": "c002", "status": "nothing_relevant", "reason": "x"},
            {"id": "c003", "status": "redundant_with", "chunks": ["c001"]},
            {"id": "c004", "status": "nothing_relevant", "reason": "y"},
            {"id": "c005", "status": "duplicate_of", "chunk": "c001"},
        ]}
        texts = {"c001": "lineage", "c002": "a derivation of the source dataset", "c003": "12 variables",
                 "c004": "Contact by email.", "c005": "version 2"}
        out = self.m.receipt_candidates(receipt, texts)
        self.assertEqual(out["marked"], 3)
        self.assertEqual(out["by_status"], {"nothing_relevant": 2, "redundant_with": 1})
        self.assertEqual([(c["chunk"], c["status"], set(c["cues"])) for c in out["candidates"]],
                         [("c002", "nothing_relevant", {"lineage"}), ("c003", "redundant_with", {"variables"})])

    def test_unknown_chunk_text_is_none_not_an_empty_list(self):
        out = self.m.receipt_candidates({"chunks": [{"id": "c001", "status": "nothing_relevant"}]}, None)
        self.assertIsNone(out["candidates"])
        self.assertEqual(out["marked"], 1)

    def test_a_receipt_chunk_the_record_s_chunks_lack_is_reported(self):
        out = self.m.receipt_candidates({"chunks": [{"id": "c009", "status": "nothing_relevant"}]}, {"c001": ""})
        # Unmeasured, not zero: the marked chunk was never read (Codex review of #3278).
        self.assertEqual((out["candidates"], out["missing_chunks"]), (None, ["c009"]))
        out = self.m.receipt_candidates({"chunks": [{"id": "c009", "status": "nothing_relevant"},
                                                    {"id": "c001", "status": "nothing_relevant"}]},
                                        {"c001": "derived from the parent dataset"})
        self.assertIsNone(out["candidates"])


class Baseline(unittest.TestCase):
    """The script over a small corpus built here."""

    def setUp(self):
        self.m = _script()
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.corpus = self.dir / "data" / "d4d_concatenated"
        self.bundle_rel = "data/preprocessed/concatenated/P_preprocessed.txt"
        bundle = self.dir / self.bundle_rel
        bundle.parent.mkdir(parents=True)
        bundle.write_text(BUNDLE, encoding="utf-8")
        self.md5 = hashlib.md5(BUNDLE.encode()).hexdigest()
        self.arms = (("a1", "Arm one", ("L_rep1", "L_rep2")), ("a2", "Arm two", ("M_rep1",)))
        # L_rep1 P: receipted; L_rep1 Q: no receipt; L_rep2 P: invalid; M_rep1 P: under the API directory.
        self._record("claudecode_agent", "L_rep1", "P", {"was_derived_from": "x", "variables": [{"n": 1}]},
                     receipt={"chunks": [{"id": "c001", "status": "nothing_relevant"},
                                         {"id": "c002", "status": "redundant_with", "chunks": ["c004"]},
                                         {"id": "c003", "status": "nothing_relevant"},
                                         {"id": "c004", "status": "extracted", "extracted": []}]})
        self._record("claudecode_agent", "L_rep1", "Q", {"variables": []})
        self._record("claudecode_agent", "L_rep2", "P", {"was_derived_from": "y"}, passed=False)
        self._record("claudecode_api", "M_rep1", "P", {"parent_datasets": [{"id": "p"}]})

    def _record(self, method, label, project, record, receipt=None, passed=True, chunks=None):
        full = self.corpus / method / label / f"{project}_d4d.yaml"
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(yaml.safe_dump(record), encoding="utf-8")
        core = self.corpus / f"{method}_core" / label
        core.mkdir(parents=True, exist_ok=True)
        inputs = {"bundle_path": self.bundle_rel, "bundle_md5": self.md5,
                  "chunks": chunks if chunks is not None else {"rule": RULE, "chunk_count": 4}}
        (core / f"{project}_provenance.yaml").write_text(
            yaml.safe_dump({"inputs": inputs, "validation": {"passed": passed}}), encoding="utf-8")
        if receipt is not None:
            (core / f"{project}_coverage_receipt.yaml").write_text(yaml.safe_dump(receipt), encoding="utf-8")

    def _collect(self):
        return self.m.collect(self.corpus, arms=self.arms, root=self.dir, projects=("P", "Q"))

    def test_rows_exclusions_and_candidates(self):
        c = self._collect()
        self.assertEqual([(r["arm"], r["path"]) for r in c["rows"]],
                         [("a1", "claudecode_agent/L_rep1/P_d4d.yaml"), ("a1", "claudecode_agent/L_rep1/Q_d4d.yaml"),
                          ("a2", "claudecode_api/M_rep1/P_d4d.yaml")])
        self.assertEqual(c["excluded"], ["claudecode_agent/L_rep2/P_d4d.yaml"])
        p = c["rows"][0]
        self.assertTrue(p["text_basis"].startswith("bundle on disk"))
        # c002 (document a.txt) and c004 (c.txt) carry cues; c003 (b.txt) and the preamble do not.
        self.assertEqual([(x["chunk"], set(x["cues"])) for x in p["receipt"]["candidates"]],
                         [("c002", {"lineage", "variables"})])

    def test_a_record_without_a_receipt_reads_none_never_zero(self):
        c = self._collect()
        q = c["rows"][1]
        self.assertIsNone(q["receipt"])
        s = self.m.arm_summary([r for r in c["rows"] if r["arm"] == "a2"])
        self.assertEqual((s["receipts"], s["marked"], s["candidates"], s["by_class"]), (0, None, None, None))
        md = self.m.render_markdown(c, arms=self.arms)
        self.assertIn("| a1 | `claudecode_agent/L_rep1/Q_d4d.yaml` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | – | – | – |", md)
        self.assertIn("| Arm two | 1 | 1 (1.0) | 0 (0.0) | 1 (1.0) |", md)
        self.assertIn("| 0 | – | – | – | – | – |", md)

    def test_chunk_text_not_recovered_is_none_with_its_reason(self):
        self._record("claudecode_agent", "L_rep1", "P", {"variables": []},
                     receipt={"chunks": [{"id": "c001", "status": "nothing_relevant"}]},
                     chunks={"rule": RULE, "chunk_count": 7})
        row = self._collect()["rows"][0]
        self.assertIsNone(row["receipt"]["candidates"])
        self.assertIn("not the 7 it cites", row["text_basis"])
        md = self.m.render_markdown(self._collect(), arms=self.arms)
        self.assertIn("Chunk text not recovered: the record's rule gives 4 chunks, not the 7 it cites. Candidates –.", md)

    def test_a_drifted_bundle_is_read_from_the_version_the_record_hashed(self):
        (self.dir / self.bundle_rel).write_text(BUNDLE + "FILE: d.txt\nPATH: d.txt\nnew\n", encoding="utf-8")
        from data_sheets_schema import provenance
        asked = []

        def fake(path, md5=None, sha256=None):
            asked.append((path, md5))
            return BUNDLE.encode(), {"commit": "0" * 40}
        orig, provenance.bundle_bytes_for = provenance.bundle_bytes_for, fake
        self.addCleanup(setattr, provenance, "bundle_bytes_for", orig)
        row = self._collect()["rows"][0]
        self.assertEqual(asked, [(self.bundle_rel, self.md5)])
        self.assertTrue(row["text_basis"].startswith("committed version (git)"))
        self.assertEqual([x["chunk"] for x in row["receipt"]["candidates"]], ["c002"])

    def test_a_drifted_bundle_with_no_matching_version_is_not_read(self):
        (self.dir / self.bundle_rel).write_text("other bytes\n", encoding="utf-8")
        from data_sheets_schema import provenance
        orig, provenance.bundle_bytes_for = provenance.bundle_bytes_for, lambda *a, **k: None
        self.addCleanup(setattr, provenance, "bundle_bytes_for", orig)
        row = self._collect()["rows"][0]
        self.assertIsNone(row["receipt"]["candidates"])
        self.assertIn("no committed version", row["text_basis"])

    def test_the_note_is_deterministic_and_moves_with_a_record_byte(self):
        first = self.m.render_markdown(self._collect(), arms=self.arms)
        self.assertEqual(first, self.m.render_markdown(self._collect(), arms=self.arms))
        with (self.corpus / "claudecode_api/M_rep1/P_d4d.yaml").open("a", encoding="utf-8") as f:
            f.write("# a comment\n")
        self.assertNotEqual(first, self.m.render_markdown(self._collect(), arms=self.arms))

    def test_a_label_under_both_directories_is_refused(self):
        self._record("claudecode_api", "L_rep1", "P", {})
        with self.assertRaises(LookupError):
            self._collect()

    def test_check_is_read_only_and_reports_staleness(self):
        self.m.CORPUS, self.m.OUT_MD, self.m.ROOT, self.m.ARMS = self.corpus, self.dir / "note.md", self.dir, self.arms
        self.m.PROJECTS = ("P", "Q")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.m.main(["--check"]), 1)
        self.assertFalse(self.m.OUT_MD.exists())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.m.main([]), 0)
        written = self.m.OUT_MD.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.m.main(["--check"]), 0)
        self.assertEqual(self.m.OUT_MD.read_bytes(), written)
        # An existing note whose bytes differ is stale, and --check leaves it
        # as it found it rather than rewriting it (#3308).
        stale = written + b"x"
        self.m.OUT_MD.write_bytes(stale)
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.m.main(["--check"]), 1)
        self.assertIn("stale", err.getvalue())
        self.assertEqual(self.m.OUT_MD.read_bytes(), stale)


def test_the_arms_are_arm_comparison_s_where_both_name_one():
    """The baseline's arms are fixed in the script; where `arm_comparison.py`
    names the same arm it must span the same labels."""
    cwd = os.getcwd()
    try:
        spec = importlib.util.spec_from_file_location("arm_comparison_2930", ROOT / "scripts" / "arm_comparison.py")
        ac = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ac)
    finally:
        os.chdir(cwd)
    theirs = {key: ac.arm_labels(prefix) for key, _, prefix, _, _ in ac.ARMS}
    mine = {key: list(labels) for key, _, labels in _script().ARMS}
    shared = set(theirs) & set(mine)
    assert shared == set(mine) - {"v9canary"}
    for key in shared:
        assert mine[key] == theirs[key], key


@pytest.mark.corpus   # walks the committed corpus and the bundles' git history
def test_the_committed_baseline_is_what_the_records_reproduce():
    m = _script()
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(m.collect()), (
        "notes/recall_target_baseline.md does not match the records: run scripts/recall_target_baseline.py")


if __name__ == "__main__":
    unittest.main()
