"""`d4d render generate-all` — the downstream half of #176.

Two problems, not one. The command was a stub that printed instructions and
generated nothing, and the script it pointed at read `data/sheets_concatenated`,
a directory that no longer exists. Neither knew about run labels, so the output
path `data/d4d_html/concatenated/{method}/{PROJECT}.html` had nowhere to put one
and a project rendered from two replicates overwrote itself.
"""

import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

REC = {"id": "https://example.org/x", "name": "x", "title": "T",
       "description": "d", "keywords": ["a"]}


class TestGenerateAll(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.cli import render as render_cli
        self.cli = render_cli.render
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path.cwd()
        root = Path(self.tmp.name)
        for label in ("2026-08-01_cfg_rep1", "2026-08-01_cfg_rep2"):
            d = root / "data" / "d4d_concatenated" / "claudecode_agent" / label
            d.mkdir(parents=True)
            rec = dict(REC, description=f"from {label}")
            (d / "P_d4d.yaml").write_text(yaml.safe_dump(rec), encoding="utf-8")
        import os
        os.chdir(root)

    def tearDown(self):
        import os
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def _run(self, *args):
        return CliRunner().invoke(self.cli, ["generate-all", *args])

    def test_a_dry_run_renders_nothing(self):
        out = self._run()
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn("Dry run", out.output)
        self.assertFalse(Path("data/d4d_html").exists(), "a dry run wrote HTML")

    def test_it_actually_generates(self):
        """It used to print instructions and produce nothing at all."""
        out = self._run("--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertTrue(Path(
            "data/d4d_html/concatenated/claudecode_agent/"
            "2026-08-01_cfg_rep1/P_d4d.html").exists())

    def test_two_labels_do_not_collide(self):
        """The bug: one output path per (method, project), so the second
        replicate silently replaced the first."""
        self._run("--execute")
        a = Path("data/d4d_html/concatenated/claudecode_agent/"
                 "2026-08-01_cfg_rep1/P_d4d.html")
        b = Path("data/d4d_html/concatenated/claudecode_agent/"
                 "2026-08-01_cfg_rep2/P_d4d.html")
        self.assertTrue(a.exists() and b.exists())
        self.assertNotEqual(a.read_bytes(), b.read_bytes(),
                            "both labels rendered to the same content")

    def test_filters_narrow_the_job(self):
        out = self._run("--label", "2026-08-01_cfg_rep1")
        self.assertIn("1 record(s)", out.output)

    def test_an_empty_selection_is_an_error_not_a_silent_success(self):
        out = self._run("--project", "NOSUCH")
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("no records matched", out.output)

    def test_publish_warns_when_it_would_overwrite(self):
        """The flat path the docs build reads has no room for a label, so
        publishing several means sort order decides what gets published."""
        out = self._run("--publish")
        self.assertIn("overwrite earlier ones", out.output)
        self.assertIn("2 labels", out.output)

    def test_publish_of_a_single_label_does_not_warn(self):
        out = self._run("--publish", "--label", "2026-08-01_cfg_rep1")
        self.assertNotIn("overwrite", out.output)

    def test_the_published_name_matches_what_the_docs_already_serve(self):
        """`{PROJECT}_d4d.yaml` -> `{PROJECT}_d4d.html`, the name already in the
        published directories. Writing `{PROJECT}.html` would not replace the
        stale render — the docs glob copies every `*.html`, so both would ship
        under two names with nothing saying which is current (#235)."""
        self._run("--publish", "--label", "2026-08-01_cfg_rep1", "--execute")
        flat = Path("data/d4d_html/concatenated/claudecode_agent")
        self.assertTrue((flat / "P_d4d.html").exists())
        self.assertFalse((flat / "P.html").exists(),
                         "published under a name the docs build does not serve")

    def test_publish_writes_the_flat_copy_the_docs_build_reads(self):
        self._run("--publish", "--label", "2026-08-01_cfg_rep1", "--execute")
        self.assertTrue(Path("data/d4d_html/concatenated/claudecode_agent/"
                             "P_d4d.html").exists())


if __name__ == "__main__":
    unittest.main()
