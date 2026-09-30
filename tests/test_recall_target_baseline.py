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
import sys
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


class CorpusFixture:
    """A small corpus built here: records, provenance, receipts, one bundle."""

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

    def _record(self, method, label, project, record, receipt=None, passed=True, chunks=None, provenance=None):
        full = self.corpus / method / label / f"{project}_d4d.yaml"
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(yaml.safe_dump(record), encoding="utf-8")
        core = self.corpus / f"{method}_core" / label
        core.mkdir(parents=True, exist_ok=True)
        inputs = {"bundle_path": self.bundle_rel, "bundle_md5": self.md5,
                  "chunks": chunks if chunks is not None else {"rule": RULE, "chunk_count": 4}}
        (core / f"{project}_provenance.yaml").write_text(
            yaml.safe_dump({"inputs": inputs, "validation": {"passed": passed}, **(provenance or {})}),
            encoding="utf-8")
        if receipt is not None:
            (core / f"{project}_coverage_receipt.yaml").write_text(yaml.safe_dump(receipt), encoding="utf-8")


class Baseline(CorpusFixture, unittest.TestCase):
    """The script over the small corpus."""

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
        self.m.PROJECTS, self.m.ADJUDICATION = ("P", "Q"), self.dir / "no_adjudication.yaml"
        self.m.DIGESTS = self.dir / "no_digests.yaml"
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


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


#: BUNDLE's c002 and c004 texts under RULE, as `chunk_texts` returns them.
C002 = "FILE: a.txt\nPATH: a.txt\nThis release is derived from the 2023 cohort; see the data dictionary.\n"
C004 = "FILE: c.txt\nPATH: c.txt\nProcessed with toolkit version 2.4.1 and 12 variables.\n"
FACT = {"id": "p-toolkit-2.4.1", "project": "P", "scope": "referent", "names": ["toolkit"],
        "version": "2.4.1", "snippet": "Processed with toolkit version 2.4.1", "reading": "c.txt states it."}


def _adjudication(path, chunks=None, facts=None):
    doc = {"chunks": chunks if chunks is not None else [
        {"project": "P", "chunk": "c002", "sha256": [_sha(C002)], "software_version": "none",
         "parent_dataset": "none", "reading": "A cohort, in text form."}],
        "facts": facts if facts is not None else [FACT],
        "bundles": [{"project": "P", "software_version": "One.", "parent_dataset": "None."}]}
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


class Carriage(unittest.TestCase):
    """#3289: how a record carries a versioned software fact."""

    def setUp(self):
        self.m = _script()
        self.fact = {"id": "f", "names": ["b2aiprep"], "version": "3.0.0"}

    def carried(self, record):
        return self.m.fact_carriage(record, self.fact)

    def test_used_software_with_the_version_or_a_tools_string_is_structured(self):
        self.assertEqual(self.carried({"preprocessing_strategies": [{"used_software": [
            {"name": "b2aiprep", "version": "3.0.0"}]}]}), "structured")
        self.assertEqual(self.carried({"machine_annotation_tools": [{"tools": ["b2aiprep v3.0.0"]}]}), "structured")

    def test_structured_needs_the_fact_s_name_and_version_in_one_entry(self):
        # Review of #3534 (#3573): every positive case above names b2aiprep
        # with 3.0.0, so dropping either check survived. Another tool at the
        # fact's version, the fact's tool at another version, or the two
        # split across entries is not structured carriage of the fact.
        cases = [
            ({"used_software": [{"name": "openSMILE", "version": "3.0.0"}]}, "absent"),
            ({"used_software": [{"name": "b2aiprep", "version": "2.0.0"}]}, "name_only"),
            ({"used_software": [{"name": "b2aiprep", "version": "2.0.0"},
                                {"name": "openSMILE", "version": "3.0.0"}]}, "name_only"),
            ({"tools": ["openSMILE v3.0.0"]}, "absent"),
            ({"tools": ["b2aiprep v2.0.0"]}, "name_only"),
            ({"tools": ["b2aiprep v2.0.0", "openSMILE v3.0.0"]}, "name_only"),
        ]
        for record, expected in cases:
            self.assertEqual(self.carried(record), expected, record)

    def test_structured_takes_the_name_from_the_entry_s_naming_fields(self):
        """Review of #3534 (#3620): a used_software entry for another tool at
        the fact's version is not the fact's structured carriage because its
        description or a nested mapping mentions the fact's name. The name
        must be the entry's `name`, `id` or `url`; a name in the entry's
        description, beside its version, is still carried, as elsewhere."""
        other = {"name": "openSMILE", "version": "3.0.0"}
        self.assertEqual(self.carried({"used_software": [dict(other, description="Run on the output of b2aiprep.")]}),
                         "elsewhere")
        self.assertEqual(self.carried({"used_software": [dict(other, depends_on={"name": "b2aiprep"})]}),
                         "name_only")
        for k, v in (("name", "b2aiprep"), ("id", "b2aiprep"), ("url", "https://github.com/sensein/b2aiprep")):
            entry = {"name": "Bridge2AI library", "version": "3.0.0", k: v}
            self.assertEqual(self.carried({"used_software": [entry]}), "structured", k)

    def test_prose_or_one_mapping_s_own_values_is_elsewhere(self):
        self.assertEqual(self.carried({"description": "Generated with the b2aiprep library, version 3.0.0."}),
                         "elsewhere")
        self.assertEqual(self.carried({"external_resources": [{"name": "b2aiprep", "version": "3.0.0"}]}),
                         "elsewhere")
        # A used_software entry without the version does not make it structured.
        self.assertEqual(self.carried({"used_software": [{"name": "b2aiprep"}],
                                       "notes": "b2aiprep 3.0.0 generated this release"}), "elsewhere")

    def test_name_without_the_version_and_nothing_at_all(self):
        self.assertEqual(self.carried({"tools": ["b2aiprep"], "version": "3.0.0"}), "name_only")
        self.assertEqual(self.carried({"description": "Features from openSMILE 3.0.0."}), "absent")

    def test_the_version_is_a_whole_token(self):
        for s in ("b2aiprep 13.0.0", "b2aiprep 3.0.01", "b2aiprep 3.0.0.1", "b2aiprep x3.0.0"):
            self.assertEqual(self.carried({"description": s}), "name_only", s)
        for s in ("b2aiprep v3.0.0", "b2aiprep (v.3.0.0)", "b2aiprep version 3.0.0", "b2aiprep 3.0.0."):
            self.assertEqual(self.carried({"description": s}), "elsewhere", s)

    def test_an_attached_suffix_makes_another_version(self):
        """Review of #3534 (#3583): a prerelease, post-release, development
        or build suffix is another version on every carriage path, whatever
        prefix the version carries; sentence punctuation still ends it."""
        suffixed = ("3.0.0-rc1", "3.0.0--rc1", "3.0.0.post1", "3.0.0.dev1", "3.0.0+build.1", "3.0.0a1", "3.0.0-1")
        for suffix in suffixed:
            for prefix in ("", "v", "v.", "version "):
                v = prefix + suffix
                for record in ({"used_software": [{"name": "b2aiprep", "version": v}]},
                               {"tools": [f"b2aiprep {v}"]},
                               {"description": f"Uses b2aiprep {v}."},
                               {"external_resources": [{"name": "b2aiprep", "version": v}]}):
                    self.assertEqual(self.carried(record), "name_only", record)
        for tail in (".", ",", ";", ")", "-", " "):
            for prefix in ("", "v", "v.", "version "):
                v = prefix + "3.0.0"
                self.assertEqual(self.carried({"tools": [f"(b2aiprep {v}{tail} "]}), "structured", (v, tail))
                self.assertEqual(self.carried({"description": f"b2aiprep {v}{tail} then"}), "elsewhere",
                                 (v, tail))
        self.assertEqual(self.carried({"used_software": [{"name": "b2aiprep", "version": "v3.0.0."}]}),
                         "structured")

    def test_the_version_matches_only_as_a_complete_version_token(self):
        """Review of #3534 (#3629): the fact's version inside a longer version
        token, as its build part (`2.0.0+3.0.0`), its prerelease part
        (`2.0.0-3.0.0`) or before a suffix joined by several separators
        (`3.0.0--rc1`), is another version on every carriage path; a name
        joined by a hyphen, a lone separator after a space and sentence
        punctuation are not part of the token."""
        paths = (lambda v: {"used_software": [{"name": "b2aiprep", "version": v}]},
                 lambda v: {"tools": [f"b2aiprep {v}"]},
                 lambda v: {"description": f"Uses b2aiprep {v}."},
                 lambda v: {"external_resources": [{"name": "b2aiprep", "version": v}]})
        longer = ("2.0.0+3.0.0", "2.0.0+v3.0.0", "x+3.0.0", "2.0.0-3.0.0", "v2-3.0.0", "3.0.0--rc1",
                  "3.0.0.-rc1", "3.0.0+-build", "v3.0.0--rc1", "version 3.0.0--rc1")
        for v in longer:
            for path in paths:
                self.assertEqual(self.carried(path(v)), "name_only", v)
        whole = ("b2aiprep-3.0.0", "b2aiprep-v3.0.0", " +3.0.0", "(3.0.0)", "3.0.0--", "3.0.0.",
                 "2.0.0+3.0.0 and 3.0.0", "3.0.0 not 2.0.0+3.0.0")
        for v in whole:
            for path, expected in zip(paths, ("structured", "structured", "elsewhere", "elsewhere")):
                self.assertEqual(self.carried(path(v)), expected, (v, expected))

    def test_the_name_is_a_whole_token(self):
        """Review of #3534 (#3601): the name, like the version, matches only
        where no word character or hyphen is attached to it."""
        for s in ("myb2aiprep 3.0.0", "b2aiprepx 3.0.0", "pre-b2aiprep 3.0.0", "b2aiprep-extra 3.0.0"):
            self.assertEqual(self.carried({"description": s}), "absent", s)
            self.assertEqual(self.carried({"tools": [s]}), "absent", s)
        for s in ("(b2aiprep) 3.0.0", "b2aiprep, 3.0.0", "B2AIPREP 3.0.0"):
            self.assertEqual(self.carried({"description": s}), "elsewhere", s)

    def test_a_mapping_s_list_valued_slot_is_its_own_value(self):
        """Review of #3534 (#3600): a resource entry naming the software in a
        multivalued string slot, with the version in a scalar beside it,
        carries both; a nested mapping's values are still not its own."""
        entry = {"external_resources": ["https://github.com/eipm/b2aiprep"],
                 "future_guarantees": "with version 3.0.0 deposited at Zenodo"}
        self.assertEqual(self.carried({"external_resources": [entry]}), "elsewhere")
        self.assertEqual(self.carried({"external_resources": [dict(entry, external_resources="https://github.com/eipm/b2aiprep")]}),
                         "elsewhere")
        nested = {"name": "b2aiprep", "details": {"note": "with version 3.0.0"}}
        self.assertEqual(self.carried({"external_resources": [nested]}), "name_only")


class Adjudication(CorpusFixture, unittest.TestCase):
    """#3289: the hand reading is checked for shape, its verdicts are
    matched to candidates by chunk text sha256, and its facts are measured
    against each record's hashed bytes."""

    def _collect(self, **kw):
        adj = self.m.load_adjudication(_adjudication(self.dir / "adj.yaml", **kw))
        return self.m.collect(self.corpus, arms=self.arms, root=self.dir, projects=("P", "Q"),
                              adjudication=adj)

    def test_a_malformed_reading_is_refused(self):
        good = {"project": "P", "chunk": "c002", "sha256": [_sha(C002)], "software_version": "none",
                "parent_dataset": "none", "reading": "r"}
        for bad in (dict(good, software_version="maybe"), dict(good, parent_dataset="perhaps"),
                    dict(good, sha256=_sha(C002)), dict(good, sha256=["abc"]), dict(good, reading="")):
            with self.assertRaises(ValueError):
                self.m.load_adjudication(_adjudication(self.dir / "bad.yaml", chunks=[bad]))
        with self.assertRaises(ValueError):
            self.m.load_adjudication(_adjudication(self.dir / "bad.yaml", chunks=[good, dict(good, chunk="c009")]))
        for bad in (dict(FACT, scope="none"), dict(FACT, snippet=""), dict(FACT, names="toolkit"),
                    dict(FACT, names=[]), dict(FACT, names=["toolkit", 2])):
            with self.assertRaises(ValueError):
                self.m.load_adjudication(_adjudication(self.dir / "bad.yaml", facts=[bad]))
        with self.assertRaises(ValueError):
            self.m.load_adjudication(_adjudication(self.dir / "bad.yaml", facts=[FACT, FACT]))

    def test_an_unquoted_version_is_refused_not_read_as_a_number(self):
        """Review of #3534 (#3621): YAML reads `version: 2.10` as the float
        2.1, so every match would look for 2.1. A version or snippet that is
        not a string is an error."""
        path = self.dir / "unquoted.yaml"
        text = _adjudication(path).read_text(encoding="utf-8")
        self.assertIn("version: 2.4.1", text)
        path.write_text(text.replace("version: 2.4.1", "version: 2.10"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "version must be a quoted string, not float 2.1"):
            self.m.load_adjudication(path)
        path.write_text(text.replace("version: 2.4.1", "version: '2.10'"), encoding="utf-8")
        self.assertEqual(self.m.load_adjudication(path)["facts"][0]["version"], "2.10")
        with self.assertRaises(ValueError):
            self.m.load_adjudication(_adjudication(self.dir / "bad.yaml", facts=[dict(FACT, snippet=3)]))

    def test_candidates_are_matched_by_chunk_text_sha256(self):
        cov = self.m.adjudication_coverage(self._collect(), arms=self.arms)
        self.assertEqual([(e["chunk"], e["arms"], e["verdict"]["reading"]) for e in cov["matched"]],
                         [("c002", ["a1"], "A cohort, in text form.")])
        self.assertEqual((cov["missing"], cov["unmatched"]), ([], []))

    def test_a_candidate_without_a_verdict_and_a_verdict_without_a_candidate_are_listed(self):
        stale = {"project": "P", "chunk": "c002", "sha256": [_sha(C002 + "edited")], "software_version": "none",
                 "parent_dataset": "none", "reading": "Read on other bytes."}
        c = self._collect(chunks=[stale])
        cov = self.m.adjudication_coverage(c, arms=self.arms)
        self.assertEqual([(e["chunk"], e["sha256"]) for e in cov["missing"]], [("c002", _sha(C002))])
        self.assertEqual([u["reading"] for u in cov["unmatched"]], ["Read on other bytes."])
        self.assertEqual(cov["matched"], [])
        md = self.m.render_markdown(c, arms=self.arms)
        self.assertIn(f"Not adjudicated: P c002 `{_sha(C002)[:12]}` (a1).", md)
        self.assertIn("Adjudicated but matching no candidate: P c002.", md)

    def test_only_version_and_lineage_candidates_need_a_verdict(self):
        """Variables are #2079's question, not the bundle reading's."""
        def row(arm, chunk, cues):
            return {"arm": arm, "project": "P", "receipt": {"candidates": [
                {"chunk": chunk, "status": "nothing_relevant", "cues": cues, "sha256": _sha(chunk)}]}}
        collected = {"rows": [row("a1", "c007", {"variables": {"var.column": 2}}),
                              row("a2", "c008", {"version": {"ver.version-token": 1}}),
                              row("a1", "c009", {"lineage": {"lin.lineage": 1}, "variables": {"var.variable": 1}})],
                     "adjudication": {"chunks": []}}
        cov = self.m.adjudication_coverage(collected, arms=self.arms)
        self.assertEqual([(e["chunk"], e["arms"]) for e in cov["missing"]], [("c008", ["a2"]), ("c009", ["a1"])])

    def test_a_fact_is_stated_in_the_hashed_bytes_and_its_carriage_measured(self):
        c = self._collect()
        by_path = {r["path"]: r for r in c["rows"]}
        p = by_path["claudecode_agent/L_rep1/P_d4d.yaml"]["facts"]["p-toolkit-2.4.1"]
        self.assertEqual(p, {"stated": True, "chunks": ["c004"], "carried": "absent"})
        # No receipt, so no chunk text; the bytes are still read for the snippet.
        m = by_path["claudecode_api/M_rep1/P_d4d.yaml"]["facts"]["p-toolkit-2.4.1"]
        self.assertEqual((m["stated"], m["chunks"]), (True, None))
        self.assertNotIn("facts", by_path["claudecode_agent/L_rep1/Q_d4d.yaml"])
        md = self.m.render_markdown(c, arms=self.arms)
        self.assertIn("## Bundle adjudication (#3289)", md)
        self.assertIn("| `p-toolkit-2.4.1` | referent | c004 | Arm one | 1 | 1 | 0 | 0 | 0 | 1 |", md)
        self.assertIn("| P | c002 | `" + _sha(C002)[:12] + "` | a1 | none | none | A cohort, in text form. |", md)
        self.assertLess(md.index("## Bundle adjudication"), md.index("## Lexical candidates by record"))

    def test_a_snippet_the_bytes_lack_is_not_stated_and_unrecovered_bytes_are_unknown(self):
        c = self._collect(facts=[dict(FACT, snippet="Processed with toolkit version 9.9.9")])
        self.assertIs(c["rows"][0]["facts"]["p-toolkit-2.4.1"]["stated"], False)
        (self.dir / self.bundle_rel).write_text("other bytes\n", encoding="utf-8")
        from data_sheets_schema import provenance
        orig, provenance.bundle_bytes_for = provenance.bundle_bytes_for, lambda *a, **k: None
        self.addCleanup(setattr, provenance, "bundle_bytes_for", orig)
        c = self._collect()
        self.assertIsNone(c["rows"][0]["facts"]["p-toolkit-2.4.1"]["stated"])
        md = self.m.render_markdown(c, arms=self.arms)
        self.assertIn("| `p-toolkit-2.4.1` | referent | – | Arm one | 1 | – |", md)

    def test_an_arm_partly_unrecovered_says_stated_n_of_m(self):
        """Review of #3534 (#3602): where some of an arm's rows have their
        bytes recovered and others do not, `stated` counts the known rows and
        says how many; a bare N would read as N of all the arm's records."""
        c = self._collect()
        row = next(r for r in c["rows"] if r["arm"] == "a1" and "p-toolkit-2.4.1" in (r.get("facts") or {}))
        unknown = dict(row, path=row["path"] + "#unrecovered",
                       facts={"p-toolkit-2.4.1": {"stated": None, "chunks": None, "carried": "name_only"}})
        c["rows"].append(unknown)
        md = self.m.render_markdown(c, arms=self.arms)
        self.assertIn("| `p-toolkit-2.4.1` | referent | c004 | Arm one | 2 | 1 of 1 | 0 | 0 | 1 | 1 |", md)

    def test_without_an_adjudication_the_note_has_no_section(self):
        c = self.m.collect(self.corpus, arms=self.arms, root=self.dir, projects=("P", "Q"))
        self.assertIsNone(c["adjudication"])
        self.assertNotIn("Bundle adjudication", self.m.render_markdown(c, arms=self.arms))


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
    collected = m.collect()
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(collected), (
        "notes/recall_target_baseline.md does not match the records: run scripts/recall_target_baseline.py")
    # #3289: every version or lineage candidate has a verdict on its bytes,
    # every verdict still names a candidate, and every fact is stated in the
    # bytes some counted record hashed.
    cov = m.adjudication_coverage(collected)
    assert (cov["missing"], cov["unmatched"]) == ([], [])
    for fact in collected["adjudication"]["facts"]:
        assert any((r.get("facts") or {}).get(fact["id"], {}).get("stated") for r in collected["rows"]), fact["id"]
    # #3525: every counted record's pinned digest was re-rendered at its
    # commit, and the render reproduced the md5 the record pins.
    renders = {(d["commit"], d["digest_md5"]): d for d in collected["digests"]["renders"]}
    for r in collected["rows"]:
        assert renders[(r["commit"], r["digest_md5"])]["reproduced"], r["path"]


#: The shape of a parenthesised version citation in a bundle (#3571, #3611):
#: `(v3.20.0)`, `(v 1.7.3)`, `(v.1.21.6)`, `(v.gpt-4-1106-preview)`,
#: `(Version 3.0.0)`, `(version 1.1)`, `(Version: 2.1)`, `(ver. 2.1)`, and
#: any of these with any amount of text before the close, as in `(version
#: 3, released fall 2025)` or `(v.12, NDEx uuid 0b04e9eb-...; Extended Data
#: Fig. 2b,e )` (#3617: the tail was bounded at 60 characters, and two
#: CM4AI citations ran past it unexamined); any case. The tail stops at the
#: first parenthesis, so it never spans a nested or a later citation. A bare `v` must be followed by a digit
#: and a `v.` by a token carrying one, so abbreviations such as `(VNNs)`,
#: `(VHI-10)` and `(VUMC)` are not citations.
VERSION_CITATION = __import__("re").compile(
    r"\((?:v\s?(?=\d)|v\.\s?(?=[\w.-]*\d)|ver\.?\s?(?=\d)|version:?\s?(?=\d))[\w.-]+[^()]*\)",
    __import__("re").IGNORECASE)

#: Parenthesised version citations in the bundles that are not software:
#: (project, the text the citation follows, what it versions). A hit whose
#: preceding text ends with that phrase (a closing quote allowed) is not a
#: software statement. Everything else of that shape must be some fact of
#: its project: the version in the parentheses, one of the fact's names in
#: the citation text just before it.
NOT_SOFTWARE = (("AI_READI", "AI-READI DATA LICENSE AGREEMENT", "a license version"),
                ("AI_READI", "current version of the dataset", "the dataset's own release"),
                ("CM4AI", "HPA", "a database release"),
                ("CM4AI", "CORUM", "a database release"),
                ("CM4AI", "STRING interactome", "a database release"),
                ("CM4AI", "STRING 78 , 79", "a reference database release (#3617)"),
                ("CM4AI", "CORUM 25 complex", "a reference database release (#3617)"),
                ("VOICE", "diverse voice dataset linked to health information", "the dataset's own releases"),
                ("VOICE", "Bridge2AI-Voice Pediatric Dataset", "the related pediatric dataset's release"),
                ("VOICE", "Discovery DOI", "a dataset release's DOI"))


@pytest.mark.parametrize("text", [
    "(v3.20.0)", "(v 1.7.3)", "(v.1.21.6)", "(v.gpt-4-1106-preview)", "(Version 3.0.0)", "(version 1.1)",
    "(VERSION 2)", "(Version: 2.1)", "(ver. 2.1)", "(Ver 2.1)", "(version 3, released fall 2025)",
    "(v.9.9, NDEx uuid 0b04e9eb-8e60-11ee-8a13-005056ae23aa; Extended Data Fig. 2b,e )"])
def test_the_citation_shape_sees_every_spelling_of_a_version(text):
    """#3611: the shape was case-sensitive on `Version` and wanted a digit
    straight after the prefix, so `(version 1.1)`, `(Version: 2.1)`, `(ver.
    2.1)` and `(v.gpt-4-1106-preview)` were never examined. #3617: a tail
    longer than 60 characters before the close was never examined either."""
    assert VERSION_CITATION.fullmatch(text), text


@pytest.mark.parametrize("text", ["(VNNs)", "(VHI-10)", "(VUMC)", "(v)", "(version)", "(very 2)", "(vs. 2)", "(v. above)", "(v.s.)"])
def test_the_citation_shape_skips_abbreviations(text):
    assert not VERSION_CITATION.search(text), text


#: The object-ranges part of a digest, as `schema_digest.render` writes it.
PREAMBLE = ("# Object ranges — required keys\n\n"
            "On every object below: `id` is `uriorcurie`; `used_software` is `Software[]`. A value of the "
            "wrong kind for its declared range is a defect even when it reads well.\n\n")
TOOLS = ("- **MachineAnnotationTools** — required: none\n"
         "    - also accepts: `notes`, `tool_accuracy`, `tools`, `version`\n")
SOFTWARE_ENTRY = ("- **Software** — required: none\n"
                  "    - also accepts: `license`, `url`, `version`\n")


def _git(repo, *args):
    import subprocess
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


class SoftwareInDigest(unittest.TestCase):
    """#3525: what a rendered digest says about `used_software` and `Software`."""

    def setUp(self):
        self.m = _script()

    def test_a_preamble_only_digest_names_no_key_of_software(self):
        got = self.m.software_in_digest("## `keywords` — *string* [many]\n\n" + PREAMBLE + TOOLS)
        self.assertEqual(got, {"used_software_mentions": 1, "in_universal_ranges": True, "own_slot_heading": False,
                               "software_entry": False, "software_keys": []})

    def test_a_software_entry_and_its_keys_are_read_and_only_its_own(self):
        text = "## `used_software` — *Software* [many]\nTools.\n\n" + PREAMBLE + SOFTWARE_ENTRY + TOOLS
        got = self.m.software_in_digest(text)
        self.assertEqual(got, {"used_software_mentions": 2, "in_universal_ranges": True, "own_slot_heading": True,
                               "software_entry": True, "software_keys": ["license", "url", "version"]})

    def test_a_class_whose_name_starts_with_software_is_not_its_entry(self):
        got = self.m.software_in_digest(PREAMBLE + "- **SoftwareTool** — required: `name`\n")
        self.assertEqual((got["software_entry"], got["software_keys"]), (False, []))

    def test_the_entry_ends_at_the_first_unindented_line(self):
        got = self.m.software_in_digest(PREAMBLE + "- **Software** — required: `name`\n\nSee `version` below.\n")
        self.assertEqual(got["software_keys"], ["name"])


class DigestMeasurement(CorpusFixture, unittest.TestCase):
    """#3525: re-rendering at a commit, and the note section it feeds."""

    def setUp(self):
        super().setUp()
        self.repo = self.dir / "repo"
        pkg = self.repo / "src" / "data_sheets_schema"
        (pkg / "schema").mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        self.digest = "# Target class `Dataset`\n\n" + PREAMBLE + TOOLS
        (pkg / "schema_digest.py").write_text(
            f"def digest_text(class_name):\n    assert class_name == 'Dataset'\n    return {self.digest!r}\n",
            encoding="utf-8")
        (pkg / "schema" / "D4D_Base_import.yaml").write_text(yaml.safe_dump(
            {"classes": {"Software": {"is_a": "NamedThing", "attributes": {"version": {}, "license": {}}}}}),
            encoding="utf-8")
        prompt = self.repo / "src" / "download" / "prompts" / "arm.md"
        prompt.parent.mkdir(parents=True)
        prompt.write_text("Name the tools under `used_software`.\n", encoding="utf-8")
        _git(self.repo, "init", "-q")
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-qm", "fixture")
        import subprocess
        self.commit = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], check=True,
                                     capture_output=True, text=True).stdout.strip()
        self.md5 = hashlib.md5(self.digest.encode()).hexdigest()
        self.prompt_sha = hashlib.sha256(prompt.read_bytes()).hexdigest()

    def _pin(self, method, label, project, md5, record=None):
        self._record(method, label, project, record or {}, provenance={
            "schema": {"digest_md5": md5}, "repo": {"commit": self.commit},
            "model": {"agent_runtime": "Claude API (direct)"},
            "prompts": {"files": [{"path": "src/download/prompts/arm.md", "sha256": self.prompt_sha}]}})

    def _measure(self, **kw):
        rows = self.m.collect(self.corpus, arms=self.arms, root=self.dir, projects=("P", "Q"))["rows"]
        path = self.dir / "digests.yaml"
        path.write_text(self.m.dump_digests(self.m.measure_digests(rows, repo=self.repo, **kw)), encoding="utf-8")
        return self.m.load_digests(path)

    def _note(self, digests):
        c = self.m.collect(self.corpus, arms=self.arms, root=self.dir, projects=("P", "Q"), digests=digests)
        return self.m.render_markdown(c, arms=self.arms)

    def test_the_commit_s_own_code_renders_the_digest_and_its_md5_is_confirmed(self):
        self._pin("claudecode_agent", "L_rep1", "P", self.md5)
        dig = self._measure()
        [r] = dig["renders"]
        self.assertEqual((r["commit"], r["rendered_md5"], r["reproduced"]), (self.commit, self.md5, True))
        self.assertEqual((r["software_entry"], r["software_keys"], r["used_software_mentions"]), (False, [], 1))
        self.assertEqual(r["software_attributes"], ["license", "version"])
        self.assertEqual(dig["prompts"], [{"commit": self.commit, "path": "src/download/prompts/arm.md",
                                           "sha256": self.prompt_sha, "at_commit": True,
                                           "names_used_software": True}])

    def test_a_render_that_does_not_reproduce_the_pin_is_not_evidence(self):
        self._pin("claudecode_agent", "L_rep1", "P", "0" * 32)
        dig = self._measure()
        self.assertFalse(dig["renders"][0]["reproduced"])
        md = self._note(dig)
        self.assertIn(f"Not reproduced: `{self.commit[:10]}` `00000000`.", md)
        self.assertIn("| Arm one | Claude API (direct), None | 2 | `00000000`, `None` | 2 | 0 of 2 | – |", md)
        self.assertIn("No render reproduces its record's md5", md)

    def test_a_render_that_fails_is_recorded_with_its_error(self):
        import subprocess
        self._pin("claudecode_agent", "L_rep1", "P", self.md5)

        def broken(commit):
            raise subprocess.CalledProcessError(1, ["python"], stderr=b"Traceback\nImportError: no linkml\n")
        dig = self._measure(render=broken)
        self.assertEqual((dig["renders"][0]["reproduced"], dig["renders"][0]["error"]),
                         (False, "ImportError: no linkml"))
        self.assertIn("(ImportError: no linkml)", self._note(dig))

    def test_the_note_says_no_digest_shows_software_s_keys_and_lists_unmeasured_records(self):
        self._pin("claudecode_agent", "L_rep1", "P", self.md5)
        self._pin("claudecode_api", "M_rep1", "P", self.md5, {"used_software": [{"name": "x", "version": "1"}]})
        dig = self._measure()
        md = self._note(dig)
        self.assertIn("## used_software in the schema digest (#3525)", md)
        self.assertIn("| Arm two | Claude API (direct) | 1 | `" + self.md5[:8] + "` | 1 | 1 of 1 | 1 | no | no "
                      "| none | yes | 1 |", md)
        # L_rep1 Q pins no digest, so it has no render.
        self.assertIn("Counted records with no render measured: `claudecode_agent/L_rep1/Q_d4d.yaml`.", md)
        self.assertIn("In all 1 reproduced renders (1 distinct digests), `used_software` is named only", md)
        # The arm's prompt is counted and names the slot (#3760).
        self.assertIn("A prompt file that names `used_software` is counted above", md)
        self.assertLess(md.index("(#3525)"), md.index("## Lexical candidates by record"))

    def test_a_digest_that_shows_software_is_named_and_the_conclusion_withheld(self):
        self.digest = "# Target class `Dataset`\n\n" + PREAMBLE + SOFTWARE_ENTRY
        (self.repo / "src" / "data_sheets_schema" / "schema_digest.py").write_text(
            f"def digest_text(class_name):\n    return {self.digest!r}\n", encoding="utf-8")
        _git(self.repo, "commit", "-qam", "show Software")
        import subprocess
        self.commit = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], check=True,
                                     capture_output=True, text=True).stdout.strip()
        md5 = hashlib.md5(self.digest.encode()).hexdigest()
        self._pin("claudecode_api", "M_rep1", "P", md5)
        md = self._note(self._measure())
        self.assertIn("Renders that show `Software`, a key of it, or a `used_software` heading of its own: "
                      f"`{self.commit[:10]}` (license, url, version).", md)
        self.assertNotIn("is named only", md)

    def test_a_used_software_heading_without_a_software_entry_claims_no_entry(self):
        # #3761: the render gives `used_software` its own heading, but
        # `Software` has no entry, so no entry may be claimed for it.
        self._recommit_digest("# Target class `Dataset`\n\n## `used_software` — *Software* [many]\nTools.\n\n"
                              + PREAMBLE + TOOLS)
        self._pin("claudecode_api", "M_rep1", "P", self.md5)
        dig = self._measure()
        r = dig["renders"][0]
        self.assertEqual((r["own_slot_heading"], r["software_entry"], r["software_keys"]), (True, False, []))
        md = self._note(dig)
        self.assertIn("Renders that show `Software`, a key of it, or a `used_software` heading of its own: "
                      f"`{self.commit[:10]}` (no `Software` entry; `used_software` has its own heading).", md)
        self.assertNotIn("entry, no keys", md)
        self.assertNotIn("Software` has no entry and", md)

    def _recommit_digest(self, digest):
        import subprocess
        self.digest = digest
        (self.repo / "src" / "data_sheets_schema" / "schema_digest.py").write_text(
            f"def digest_text(class_name):\n    return {self.digest!r}\n", encoding="utf-8")
        _git(self.repo, "commit", "-qam", "another digest")
        self.commit = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], check=True,
                                     capture_output=True, text=True).stdout.strip()
        self.md5 = hashlib.md5(self.digest.encode()).hexdigest()

    def test_named_only_in_the_preamble_is_claimed_only_where_every_render_says_so(self):
        # #3733: no Software entry, but `used_software` is named outside the
        # preamble's range line, which this digest does not carry.
        self._recommit_digest("# Target class `Dataset`\n\n"
                              "- **Tooling** — required: none\n    - also accepts: `used_software`\n")
        self._pin("claudecode_api", "M_rep1", "P", self.md5)
        dig = self._measure()
        self.assertEqual((dig["renders"][0]["in_universal_ranges"], dig["renders"][0]["used_software_mentions"]),
                         (False, 1))
        md = self._note(dig)
        self.assertNotIn("is named only", md)
        self.assertIn("In all 1 reproduced renders (1 distinct digests), `Software` has no entry and", md)
        self.assertIn("no key of `Software` is shown (`used_software` is not named only in the object-ranges", md)
        # Two mentions, one of them the preamble's and no heading: not "named only" either.
        self._recommit_digest("# Target class `Dataset`\n\n" + PREAMBLE + TOOLS
                              + "- **Tooling** — required: none\n    - also accepts: `used_software`\n")
        self._pin("claudecode_api", "M_rep1", "P", self.md5)
        dig = self._measure()
        r = dig["renders"][0]
        self.assertEqual((r["in_universal_ranges"], r["used_software_mentions"], r["own_slot_heading"],
                          r["software_entry"]), (True, 2, False, False))
        md = self._note(dig)
        self.assertNotIn("is named only", md)
        self.assertIn("no key of `Software` is shown (`used_software` is not named only in the object-ranges", md)

    def test_a_prompt_whose_bytes_changed_at_the_commit_is_not_counted(self):
        # #3734/#3736: the record hashed other bytes than the commit holds.
        self._record("claudecode_api", "M_rep1", "P", {}, provenance={
            "schema": {"digest_md5": self.md5}, "repo": {"commit": self.commit},
            "model": {"agent_runtime": "Claude API (direct)"},
            "prompts": {"files": [{"path": "src/download/prompts/arm.md", "sha256": "f" * 64},
                                  {"path": "src/download/prompts/gone.md", "sha256": "e" * 64}]}})
        dig = self._measure()
        self.assertEqual([(p["path"], p["at_commit"], p["names_used_software"]) for p in dig["prompts"]],
                         [("src/download/prompts/arm.md", False, True), ("src/download/prompts/gone.md", None, None)])
        md = self._note(dig)
        # The file names used_software, but not in the bytes the record read.
        self.assertIn("| Arm two | Claude API (direct) | 1 | `" + self.md5[:8] + "` | 1 | 1 of 1 | 1 | no | no "
                      "| none | – | 0 |", md)
        self.assertIn("(`–`: no record in the arm hashed a prompt file whose bytes\n"
                      "reproduce at its commit, either because it hashes none or because none it hashed does)", md)
        # And the closing note does not say a prompt naming the slot is
        # counted above, since none is (#3760).
        self.assertIn("In all 1 reproduced renders (1 distinct digests), `used_software` is named only", md)
        self.assertNotIn("counted above", md)

    def test_a_render_from_another_copy_of_the_package_is_refused(self):
        # #3735: an interpreter that finds `data_sheets_schema` somewhere
        # other than the archive (as an editable install would) must not
        # answer for the commit's code.
        import stat
        import subprocess
        shadow = self.dir / "shadow" / "data_sheets_schema"
        shadow.mkdir(parents=True)
        (shadow / "__init__.py").write_text("", encoding="utf-8")
        (shadow / "schema_digest.py").write_text("def digest_text(c):\n    return 'the shadow copy'\n",
                                                 encoding="utf-8")
        wrapper = self.dir / "shadowed_python"
        wrapper.write_text(f"#!/bin/sh\nPYTHONPATH={shadow.parent}:$PYTHONPATH exec {sys.executable} \"$@\"\n",
                           encoding="utf-8")
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            self.m.render_at(self.commit, self.repo, python=str(wrapper))
        self.assertIn(b"AssertionError", caught.exception.stderr)
        self.assertIn(str(shadow).encode(), caught.exception.stderr)
        self._pin("claudecode_agent", "L_rep1", "P", self.md5)
        [r] = self._measure(python=str(wrapper))["renders"]
        self.assertFalse(r["reproduced"])
        self.assertIn("AssertionError", r["error"])
        # The unshadowed interpreter renders the commit's own digest.
        self.assertEqual(self.m.render_at(self.commit, self.repo), self.digest)

    def test_a_malformed_measurement_is_refused(self):
        self._pin("claudecode_agent", "L_rep1", "P", self.md5)
        good = self._measure()["renders"][0]
        for bad in ([dict(good, reproduced=False)], [good, good], [dict(good, commit="abc")],
                    [{k: v for k, v in good.items() if k != "software_keys"}],
                    [{k: v for k, v in good.items() if k != "rendered_md5"}]):
            path = self.dir / "bad_digests.yaml"
            path.write_text(yaml.safe_dump({"renders": bad}), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.m.load_digests(path)

    def test_without_a_measurement_the_note_has_no_section(self):
        self._pin("claudecode_agent", "L_rep1", "P", self.md5)
        self.assertNotIn("(#3525)", self._note(None))


@pytest.mark.corpus   # reads the committed bundles
def test_every_parenthesised_version_citation_in_the_bundles_is_a_fact_or_named_as_not_software():
    """Review of #3534 (#3571, #3611): the adjudication says its facts hold
    every versioned software statement in the bundles, and the first reading
    missed two citations of this shape, "Name (v3.20.0)" and "Name (Version
    3.0.0)". A citation of the `VERSION_CITATION` shape that no fact covers
    and `NOT_SOFTWARE` does not name fails here. Versions stated outside
    parentheses ("b2aiprep v3.0.0", "package version 2.18") are not this
    test's business: the adjudication's own search found those."""
    m = _script()
    facts = m.load_adjudication(m.ADJUDICATION)["facts"]
    re = __import__("re")
    uncovered = []
    for project in m.PROJECTS:
        path = ROOT / "data" / "preprocessed" / "concatenated" / f"{project}_preprocessed.txt"
        text = " ".join(path.read_text(encoding="utf-8").split())
        excused = [re.compile(re.escape(phrase) + r"""["'”’]?\s*$""")
                   for p, phrase, _ in NOT_SOFTWARE if p == project]
        patterns = [m._fact_patterns(f) for f in facts if f["project"] == project]
        for hit in VERSION_CITATION.finditer(text):
            before = text[max(0, hit.start() - 60):hit.start()]
            if any(e.search(before) for e in excused) or any(
                    names.search(before) and version.search(hit.group(0)) for names, version in patterns):
                continue
            uncovered.append(f"{project}: …{before}{hit.group(0)}")
    assert uncovered == []


if __name__ == "__main__":
    unittest.main()
