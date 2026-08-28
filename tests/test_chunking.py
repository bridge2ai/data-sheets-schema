"""The chunk manifest is a pure function of the bundle and its rule (#707)."""
import hashlib
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEADER = ("=" * 80 + "\nCONCATENATED DOCUMENT\n" + "=" * 80 + "\nTotal Files: 2\n"
          + "=" * 80 + "\n\nTABLE OF CONTENTS\n" + "-" * 80 + "\n  1. a.txt\n  2. b.txt\n"
          + "=" * 80 + "\n\n")


def _doc(name, body_lines):
    return (f"FILE: {name}\nPATH: x/{name}\nSIZE: 1 bytes\n" + "-" * 80 + "\n"
            + "\n".join(body_lines) + "\n\n" + "=" * 80 + "\n\n")


def _bundle(a_lines=5, b_lines=5):
    return (HEADER + _doc("a.txt", [f"a{i}" for i in range(a_lines)])
            + _doc("b.txt", [f"b{i}" for i in range(b_lines)])).rstrip("\n") + "\n"


class ChunkText(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.chunking import DEFAULT_RULE
        self.rule = dict(DEFAULT_RULE)

    def test_chunks_reassemble_to_the_exact_bundle(self):
        from data_sheets_schema.chunking import chunk_text, chunk_texts
        for text in (_bundle(), _bundle(1000, 3), _bundle().rstrip("\n"), "no headers at all\nx"):
            chunks = chunk_text(text, {**self.rule, "max_lines": 7, "max_bytes": 40})
            self.assertEqual("".join(chunk_texts(text, chunks)), text)
            for c, body in zip(chunks, chunk_texts(text, chunks)):
                self.assertEqual(c["sha256"], hashlib.sha256(body.encode()).hexdigest())
                self.assertEqual(c["bytes"], len(body.encode()))

    def test_same_bytes_same_rule_same_manifest(self):
        from data_sheets_schema.chunking import chunk_text
        self.assertEqual(chunk_text(_bundle(300, 300), self.rule),
                         chunk_text(_bundle(300, 300), self.rule))

    def test_documents_are_the_unit_and_the_preamble_is_its_own_chunk(self):
        from data_sheets_schema.chunking import PREAMBLE, chunk_text
        chunks = chunk_text(_bundle(), self.rule)
        self.assertEqual([c["source"] for c in chunks], [PREAMBLE, "a.txt", "b.txt"])
        self.assertEqual(chunks[0]["lines"][0], 1)
        # every chunk starts where the previous ended
        for prev, nxt in zip(chunks, chunks[1:]):
            self.assertEqual(nxt["lines"][0], prev["lines"][1] + 1)
        self.assertEqual([c["id"] for c in chunks], ["c001", "c002", "c003"])

    def test_both_bounds_hold_and_parts_are_numbered(self):
        from data_sheets_schema.chunking import chunk_text
        rule = {**self.rule, "max_lines": 100, "max_bytes": 10_000}
        chunks = chunk_text(_bundle(1000, 2), rule)
        a = [c for c in chunks if c["source"] == "a.txt"]
        self.assertGreater(len(a), 1)
        for c in chunks:
            self.assertLessEqual(c["lines"][1] - c["lines"][0] + 1, 100)
            self.assertLessEqual(c["bytes"], 10_000)
        self.assertEqual([c["part"] for c in a], [[i, len(a)] for i in range(1, len(a) + 1)])
        self.assertNotIn("part", chunks[0])
        # the byte bound bites before the line bound on long lines
        long = chunk_text(_bundle(50, 1).replace("a1\n", "a1" + "x" * 600 + "\n"),
                          {**self.rule, "max_lines": 100, "max_bytes": 700})
        self.assertTrue(all(c["bytes"] <= 700 for c in long))

    def test_a_line_above_the_byte_bound_is_its_own_chunk_and_named_oversize(self):
        from data_sheets_schema.chunking import chunk_text, chunk_texts
        text = _bundle(3, 1).replace("a1\n", "a1" + "y" * 2000 + "\n")
        chunks = chunk_text(text, {**self.rule, "max_bytes": 500})
        big = [c for c in chunks if c.get("oversize")]
        self.assertEqual(len(big), 1)
        self.assertEqual(big[0]["lines"][0], big[0]["lines"][1])
        self.assertEqual("".join(chunk_texts(text, chunks)), text)

    def test_the_rule_is_recorded_and_changes_the_manifest(self):
        from data_sheets_schema.chunking import build_manifest
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "P_preprocessed.txt"
            p.write_text(_bundle(500, 5), encoding="utf-8")
            m1 = build_manifest(p)
            m2 = build_manifest(p, {**m1["rule"], "max_lines": 50})
            self.assertEqual(m1["rule"], __import__("data_sheets_schema.chunking", fromlist=["DEFAULT_RULE"]).DEFAULT_RULE)
            self.assertNotEqual(m1["chunk_count"], m2["chunk_count"])
            self.assertEqual(m1["bundle_md5"], hashlib.md5(p.read_bytes()).hexdigest())
            self.assertEqual(sum(c["bytes"] for c in m1["chunks"]), m1["bundle_bytes"])


class ManifestOnDisk(unittest.TestCase):
    def _dirs(self, tmp):
        concat, chunks = Path(tmp) / "concat", Path(tmp) / "chunks"
        concat.mkdir()
        (concat / "P_preprocessed.txt").write_text(_bundle(20, 20), encoding="utf-8")
        return concat, chunks

    def test_write_check_and_drift(self):
        from data_sheets_schema.chunking import manifest_status, write_manifest
        with tempfile.TemporaryDirectory() as tmp:
            concat, chunks = self._dirs(tmp)
            self.assertEqual(manifest_status("P", concat, chunks)[0], "missing")
            out, m = write_manifest("P", concat_dir=concat, chunks_dir=chunks)
            self.assertEqual(manifest_status("P", concat, chunks)[0], "current")
            # same bytes rewritten → identical file (the file's sha256 is a receipt)
            before = out.read_bytes()
            write_manifest("P", concat_dir=concat, chunks_dir=chunks)
            self.assertEqual(before, out.read_bytes())
            (concat / "P_preprocessed.txt").write_text(_bundle(21, 20), encoding="utf-8")
            st, why = manifest_status("P", concat, chunks)
            self.assertEqual(st, "stale"); self.assertIn("md5", why)
            self.assertEqual(manifest_status("Q", concat, chunks)[0], "no_bundle")
            # a manifest under another rule reproduces but is not the instrument (#714)
            write_manifest("P", {**m["rule"], "max_lines": 5}, concat_dir=concat, chunks_dir=chunks)
            self.assertEqual(manifest_status("P", concat, chunks)[0], "off_rule")
            out.write_text("- not\n- a mapping\n", encoding="utf-8")
            self.assertEqual(manifest_status("P", concat, chunks)[0], "unreadable")

    def test_the_manifest_does_not_depend_on_how_the_bundle_was_addressed(self):
        """#713: same bytes, same rule, same file — whatever path spelled it."""
        from data_sheets_schema.chunking import build_manifest, dump_manifest
        with tempfile.TemporaryDirectory() as tmp:
            concat, _ = self._dirs(tmp)
            rel = concat / "P_preprocessed.txt"
            self.assertEqual(dump_manifest(build_manifest(rel)),
                             dump_manifest(build_manifest(rel.resolve())))

    def test_a_crate_evidence_section_is_a_boundary_and_the_hint_names_the_project(self):
        """#745/#744: crate sections open with FILE: + ROLE:, and the rebuild hint
        strips the kind suffix rather than splitting on '_'."""
        from data_sheets_schema.chunking import chunk_text, manifest_status_for
        text = _bundle(3, 3) + "FILE: P_crate_metadata_reduced.json\nROLE: crate evidence\n" + "-" * 80 + "\n{}\n"
        self.assertEqual([c["source"] for c in chunk_text(text)],
                         ["<preamble>", "a.txt", "b.txt", "P_crate_metadata_reduced.json"])
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / "AI_READI_healthsheet_only.txt"; b.write_text("x\n", encoding="utf-8")
            st, hint = manifest_status_for(b, Path(tmp) / "chunks")
            self.assertEqual(st, "missing"); self.assertIn("--project AI_READI", hint)

    def test_a_quoted_file_line_is_content_not_a_boundary(self):
        """#718: only a FILE: line followed by PATH: starts a document."""
        from data_sheets_schema.chunking import chunk_text, chunk_texts
        text = _bundle(3, 3).replace("a1\n", "FILE: quoted in prose\nmore\n")
        chunks = chunk_text(text)
        self.assertEqual([c["source"] for c in chunks], ["<preamble>", "a.txt", "b.txt"])
        self.assertEqual("".join(chunk_texts(text, chunks)), text)

    def test_chunks_input_attaches_only_for_the_same_bytes(self):
        from data_sheets_schema.chunking import chunks_input, file_sha256, write_manifest
        with tempfile.TemporaryDirectory() as tmp:
            concat, chunks = self._dirs(tmp)
            bundle = concat / "P_preprocessed.txt"
            md5 = hashlib.md5(bundle.read_bytes()).hexdigest()
            self.assertIsNone(chunks_input(bundle, md5, chunks))          # no manifest
            out, m = write_manifest("P", concat_dir=concat, chunks_dir=chunks)
            got = chunks_input(bundle, md5, chunks)
            self.assertEqual(got["sha256"], file_sha256(out))
            self.assertEqual(got["rule"], m["rule"]); self.assertEqual(got["chunk_count"], m["chunk_count"])
            self.assertIsNone(chunks_input(bundle, "0" * 32, chunks))     # other bytes
            self.assertIsNone(chunks_input(None, md5, chunks))
            out.write_text("- broken\n", encoding="utf-8")                  # #715
            self.assertIsNone(chunks_input(bundle, md5, chunks))
            out.write_text(": not yaml: [", encoding="utf-8")
            self.assertIsNone(chunks_input(bundle, md5, chunks))

    def test_the_cli_writes_and_checks(self):
        import click.testing
        from data_sheets_schema.cli.bundle import bundle as bundle_cli
        from data_sheets_schema import chunking
        with tempfile.TemporaryDirectory() as tmp:
            concat, chunks = self._dirs(tmp)
            (concat / "AI_READI_preprocessed.txt").write_text(_bundle(20, 20), encoding="utf-8")
            old = chunking.CONCAT_DIR, chunking.CHUNKS_DIR
            chunking.CONCAT_DIR, chunking.CHUNKS_DIR = concat, chunks
            try:
                runner = click.testing.CliRunner()
                r = runner.invoke(bundle_cli, ["chunk", "--check", "--strict", "--project", "AI_READI"])
                self.assertEqual(r.exit_code, 1, r.output); self.assertIn("missing", r.output)
                r = runner.invoke(bundle_cli, ["chunk", "--project", "AI_READI"])
                self.assertEqual(r.exit_code, 0, r.output); self.assertIn("chunks over", r.output)
                r = runner.invoke(bundle_cli, ["chunk", "--check", "--strict", "--project", "AI_READI"])
                self.assertEqual(r.exit_code, 0, r.output); self.assertIn("current", r.output)
                r = runner.invoke(bundle_cli, ["chunk", "--project", "AI_READI", "--max-lines", "5"])
                self.assertEqual(r.exit_code, 0, r.output)
                self.assertIn("custom", (chunks / "AI_READI_chunks.yaml").read_text())
            finally:
                chunking.CONCAT_DIR, chunking.CHUNKS_DIR = old


class ManifestNaming(unittest.TestCase):
    def test_every_bundle_kind_has_its_own_manifest_and_an_unsegmented_bundle_chunks(self):
        """#725: crate, with-crate and healthsheet bundles are chunked too,
        each to a manifest of its own name; a bundle with no FILE: headers is
        one unsegmented document, windowed like any other."""
        from data_sheets_schema.chunking import (UNSEGMENTED, chunk_text, chunks_input, manifest_for,
                                                  project_bundles, write_manifest_for)
        self.assertEqual(manifest_for(Path("x/CHORUS_preprocessed.txt")).name, "CHORUS_chunks.yaml")
        self.assertEqual(manifest_for(Path("x/CHORUS_crate_only.txt")).name, "CHORUS_crate_only_chunks.yaml")
        self.assertEqual(manifest_for(Path("x/AI_READI_healthsheet_only.txt")).name,
                         "AI_READI_healthsheet_only_chunks.yaml")
        chunks = chunk_text("no file headers here\n" * 3)
        self.assertEqual([c["source"] for c in chunks], [UNSEGMENTED])
        with tempfile.TemporaryDirectory() as tmp:
            concat, chunks_dir = Path(tmp) / "concat", Path(tmp) / "chunks"
            concat.mkdir()
            for suffix in ("_preprocessed.txt", "_crate_only.txt"):
                (concat / f"P{suffix}").write_text(_bundle(5, 5), encoding="utf-8")
            (concat / "P_unknown_kind.txt").write_text("x\n", encoding="utf-8")
            found = project_bundles("P", concat)
            self.assertEqual([b.name for b in found], ["P_preprocessed.txt", "P_crate_only.txt"])
            for b in found:
                write_manifest_for(b, chunks_dir=chunks_dir)
            crate = concat / "P_crate_only.txt"
            got = chunks_input(crate, hashlib.md5(crate.read_bytes()).hexdigest(), chunks_dir)
            self.assertEqual(Path(got["path"]).name, "P_crate_only_chunks.yaml")


@unittest.skipUnless((ROOT / "data/preprocessed/concatenated/CHORUS_preprocessed.txt").exists(),
                     "corpus bundle absent")
class CorpusManifests(unittest.TestCase):
    def test_committed_manifests_are_current_and_under_the_read_cap(self):
        """Every bundle of every kind has a committed manifest that reproduces
        from its bytes, and no chunk exceeds the bound that keeps it readable
        in one tool call."""
        from data_sheets_schema.chunking import (load_manifest, manifest_for, manifest_status_for,
                                                  project_bundles)
        from data_sheets_schema.constants import PROJECTS
        seen = 0
        for name in PROJECTS:
            for b in project_bundles(name):
                with self.subTest(bundle=b.name):
                    seen += 1
                    st, detail = manifest_status_for(b)
                    self.assertEqual(st, "current", detail)   # also asserts the default rule (#714)
                    m = load_manifest(manifest_for(b))
                    self.assertEqual(m["bundle"], b.name)
                    self.assertFalse([c for c in m["chunks"] if c.get("oversize")],
                                     "a line above max_bytes cannot be read in one call")
                    self.assertIn(m["chunks"][0]["source"], ("<preamble>", "<unsegmented>"))
        self.assertEqual(seen, len(list((ROOT / "data/preprocessed/concatenated").glob("*.txt"))),
                         "every .txt bundle in the concatenated directory is covered")


if __name__ == "__main__":
    unittest.main()
