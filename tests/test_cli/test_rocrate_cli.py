#!/usr/bin/env python3
"""
CLI tests for d4d rocrate commands.
"""

import importlib.util
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data_sheets_schema.cli import cli
from tests.test_cli._helpers import build_module_tree

#: The parser `d4d rocrate parse` imports: the copy setup_repo_imports puts
#: on sys.path
LEGACY_PARSER = (Path(__file__).resolve().parents[2]
                 / ".claude" / "agents" / "scripts" / "rocrate_parser.py")


class TestROCrateCLI(unittest.TestCase):
    """Test RO-Crate CLI behavior."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.runner = CliRunner()

        self.input_a = self.test_path / "a.json"
        self.input_b = self.test_path / "b.json"
        self.input_a.write_text("{}", encoding="utf-8")
        self.input_b.write_text("{}", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_transform_merge_mode_accepts_inputs_without_positional_input_file(self):
        fake_module = types.SimpleNamespace(main=lambda: None)

        with patch("data_sheets_schema.cli.rocrate.require_repo_context"), \
             patch("data_sheets_schema.cli.rocrate.setup_repo_imports"), \
             patch.dict(sys.modules, {"rocrate_to_d4d": fake_module}):
            result = self.runner.invoke(
                cli,
                [
                    "rocrate",
                    "transform",
                    "--merge",
                    "--inputs",
                    str(self.input_a),
                    "--inputs",
                    str(self.input_b),
                    "-o",
                    str(self.test_path / "output.yaml"),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("merge mode", result.output)
        self.assertIn("D4D YAML saved to", result.output)

    def test_transform_single_file_mode_still_requires_input_file(self):
        result = self.runner.invoke(
            cli,
            [
                "rocrate",
                "transform",
                "-o",
                str(self.test_path / "output.yaml"),
            ],
        )

        self.assertEqual(result.exit_code, 2, msg=result.output)
        self.assertIn("Missing argument 'INPUT_FILE'", result.output)

    def test_parse_writes_json_output(self):
        class FakeParser:
            def __init__(self, input_file):
                self.input_file = input_file

            def get_all_entities(self):
                return {"dataset": {"@type": "Dataset"}}

        fake_modules = build_module_tree("rocrate_parser", ROCrateParser=FakeParser)
        output_file = self.test_path / "parsed.json"

        with patch("data_sheets_schema.cli.rocrate.require_repo_context"), \
             patch("data_sheets_schema.cli.rocrate.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            result = self.runner.invoke(
                cli,
                ["rocrate", "parse", str(self.input_a), "--output", str(output_file)],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(output_file.exists(), msg=result.output)
        self.assertIn("Parsed 1 entities", result.output)

    def test_merge_invokes_merger_with_primary_marker(self):
        calls = []

        class FakeMerger:
            def add_rocrate(self, input_file, is_primary=False):
                calls.append(("add", input_file, is_primary))

            def merge(self):
                calls.append(("merge",))
                return {"merged": True}

        fake_modules = build_module_tree("rocrate_merger", ROCrateMerger=FakeMerger)
        output_file = self.test_path / "merged.json"

        with patch("data_sheets_schema.cli.rocrate.require_repo_context"), \
             patch("data_sheets_schema.cli.rocrate.setup_repo_imports"), \
             patch.dict(sys.modules, fake_modules):
            result = self.runner.invoke(
                cli,
                [
                    "rocrate",
                    "merge",
                    str(self.input_a),
                    str(self.input_b),
                    "--primary",
                    str(self.input_b),
                    "-o",
                    str(output_file),
                ],
            )

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(output_file.exists(), msg=result.output)
        self.assertEqual(
            calls,
            [
                ("add", str(self.input_a), False),
                ("add", str(self.input_b), True),
                ("merge",),
            ],
        )
        self.assertIn("Merged RO-Crate saved", result.output)


class TestParseRefusesACrateThatIsNotUtf8(unittest.TestCase):
    """#4186. The parser `d4d rocrate parse` imports, the copy under
    .claude/agents/scripts, opens a crate as UTF-8 itself, so a crate that
    is not UTF-8 ended the command with a bare UnicodeDecodeError. The
    command reads the crate first as `fairscape-cli parse` reads one, and
    refuses it with a CrateEncodingError naming the first byte that does
    not decode: one `❌ Error:` line on stderr, exit 1, no output written.

    That parser runs for real, loaded from its path. setup_repo_imports,
    which would put its directory on sys.path for the rest of the session,
    is patched out, as above.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.crate = Path(self.test_dir) / "ro-crate-metadata.json"
        text = json.dumps({"@context": "https://w3id.org/ro/crate/1.1/context",
                           "@graph": [{"@id": "./", "@type": "Dataset",
                                       "name": "Données © 2025"}]},
                          ensure_ascii=False)
        self.crate.write_bytes(text.encode("windows-1252"))
        # Every character before the é is ASCII, so its index is its offset
        self.offset = text.index("é")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_refuses_it_by_name(self):
        spec = importlib.util.spec_from_file_location("rocrate_parser", LEGACY_PARSER)
        parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser)
        output = Path(self.test_dir) / "parsed.json"

        with patch("data_sheets_schema.cli.rocrate.require_repo_context"), \
             patch("data_sheets_schema.cli.rocrate.setup_repo_imports"), \
             patch.dict(sys.modules, {"rocrate_parser": parser}):
            result = CliRunner(mix_stderr=False).invoke(
                cli, ["rocrate", "parse", str(self.crate), "--output", str(output)])

        self.assertEqual(result.exit_code, 1, result.stdout + result.stderr)
        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.stdout, f"📦 Parsing RO-Crate: {self.crate}\n")
        # é (0xe9) and © (0xa9) are the two bytes that do not decode
        self.assertEqual(
            result.stderr,
            f"❌ Error: {self.crate} is not UTF-8, as RFC 8259 requires of JSON: "
            f"byte 0xe9 at offset {self.offset}, 2 undecodable byte(s) in all. "
            "Not decoded under a guessed encoding; transcode it to UTF-8 from "
            "the encoding it is written in\n")
        self.assertFalse(output.exists())


class TestPerProjectLoopsEndWithACount(unittest.TestCase):
    """#3638. bundle, emit-arm and emit-map-arm counted the projects they did
    not finish, then exited 1 without printing the count, so a caller reading
    only the last line could not tell how many had failed. Each now ends with
    one stderr line naming what it counts, before the exit. A run with nothing
    to count ends as it did, as normalize and map do (#3359).

    Both numbers count the loop's entries, and the total is how many it tried.
    With --project the entries are the names given, and a repeated name counts
    each time. With none, which is how notes/D4D_GENERATION_ARMS.md runs all
    three, they are the declared projects that have the input the command
    looks for.

    In the mixed runs that name all three projects, BETA fails and ALPHA and
    GAMMA succeed, so the count, the total and the number that succeeded all
    differ. In the no-project runs (#4155) only ALPHA and BETA have the
    command's input. GAMMA, declared too, has what another command reads
    instead (a crate never normalized, or the other emit command's record) and
    is never tried. ALPHA is done and BETA fails, so the total, 2, is neither
    the number the manifest declares (3) nor the number of --project values
    (0). "1 of 2" cannot tell failures from successes; the mixed runs can.

    The library functions run for real. The commands pass them no output
    directory, so each is patched to add a temporary one, and every run starts
    in an empty working directory, where a relative default would land if a
    patch missed: never in the checkout's data/.
    """

    PROJECTS = ("ALPHA", "BETA", "GAMMA")

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.runner = CliRunner(mix_stderr=False)
        self.manifest = self.test_path / "source_manifest.yaml"
        self.manifest.write_text(
            "projects:\n" + "".join(f"  {p}: {{sources: []}}\n" for p in self.PROJECTS),
            encoding="utf-8")
        self.packages = self.test_path / "packages"
        self.docs = self.test_path / "concatenated"
        self.concat = self.test_path / "d4d_concatenated"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _invoke(self, *args, projects=PROJECTS):
        argv = ["--manifest", str(self.manifest), "rocrate", *args,
                "--packages-dir", str(self.packages)]
        for name in projects:
            argv += ["--project", name]
        with self.runner.isolated_filesystem(temp_dir=self.test_dir):
            return self.runner.invoke(cli, argv)

    def _record(self, project, variant):
        """A normalized record for emit_deterministic_arm to publish."""
        path = self.packages / project / "processed" / f"{project}_{variant}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# normalizer header\nid: {project}\n", encoding="utf-8")

    def _publishing_into_tmp(self):
        from data_sheets_schema import rocrate_normalize
        real = rocrate_normalize.emit_deterministic_arm
        return patch("data_sheets_schema.rocrate_normalize.emit_deterministic_arm",
                     side_effect=lambda name, version, root, **kw: real(
                         name, version, root, concat_dir=self.concat, **kw))

    def test_bundle_counts_the_bundles_it_did_not_write(self):
        from data_sheets_schema import rocrate_normalize
        real = rocrate_normalize.build_crate_bundle
        self.docs.mkdir()
        for name in ("ALPHA", "GAMMA"):                    # BETA has no document bundle
            (self.docs / f"{name}_preprocessed.txt").write_text(name, encoding="utf-8")
            (self.packages / name / "processed").mkdir(parents=True)
        with patch("data_sheets_schema.rocrate_normalize.build_crate_bundle",
                   side_effect=lambda name, root: real(name, root, docs_dir=self.docs)):
            r = self._invoke("bundle")
            ok = self._invoke("bundle", projects=("ALPHA",))

        self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)   # not a crash
        self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr.splitlines()[-1:],
                         ["❌ 1 of 3 bundle(s) not written"], r.stderr)
        self.assertIn("No document bundle", r.stderr)      # the reason stays above it
        self.assertEqual(sorted(p.name for p in self.docs.glob("*_with_crate.txt")),
                         ["ALPHA_preprocessed_with_crate.txt",
                          "GAMMA_preprocessed_with_crate.txt"])

        self.assertEqual(ok.exit_code, 0, ok.stdout + ok.stderr)   # nothing to count
        self.assertNotIn("❌", ok.stderr)
        self.assertEqual(ok.stdout.splitlines()[-1:], ["✅ Crate-augmented bundles written"])

    def test_emit_arm_counts_the_projects_it_did_not_publish(self):
        for name in ("ALPHA", "GAMMA"):                    # BETA has no normalized record
            self._record(name, "crate_d4d")
        with self._publishing_into_tmp():
            r = self._invoke("emit-arm", "--version", "v1")
            ok = self._invoke("emit-arm", "--version", "v2", projects=("ALPHA",))

        self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)
        self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr.splitlines()[-1:],
                         ["❌ 1 of 3 project(s) not published"], r.stderr)
        self.assertIn("BETA: No normalized record", r.stderr)
        self.assertEqual(sorted(p.name for p in (self.concat / "rocrate_mapped" / "v1").iterdir()),
                         ["ALPHA_d4d.yaml", "GAMMA_d4d.yaml"])

        self.assertEqual(ok.exit_code, 0, ok.stdout + ok.stderr)
        self.assertNotIn("❌", ok.stderr)
        self.assertEqual(ok.stdout.splitlines()[-1:],
                         ["✅ Deterministic arm published under version v2"])

    def test_emit_map_arm_counts_the_projects_it_did_not_publish(self):
        for name in self.PROJECTS:
            self._record(name, "crate_mapped_d4d")
        earlier = self.concat / "rocrate_static_map" / "v1" / "BETA_d4d.yaml"
        earlier.parent.mkdir(parents=True)
        earlier.write_text("an earlier run's record\n", encoding="utf-8")   # refused, kept
        with self._publishing_into_tmp():
            r = self._invoke("emit-map-arm", "--version", "v1")
            ok = self._invoke("emit-map-arm", "--version", "v2", projects=("ALPHA",))

        self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)
        self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr.splitlines()[-1:],
                         ["❌ 1 of 3 project(s) not published"], r.stderr)
        self.assertIn("BETA_d4d.yaml already exists", r.stderr)
        self.assertEqual(earlier.read_text(encoding="utf-8"), "an earlier run's record\n")
        self.assertEqual(sorted(p.name for p in earlier.parent.iterdir()),
                         ["ALPHA_d4d.yaml", "BETA_d4d.yaml", "GAMMA_d4d.yaml"])

        self.assertEqual(ok.exit_code, 0, ok.stdout + ok.stderr)
        self.assertNotIn("❌", ok.stderr)
        self.assertEqual(ok.stdout.splitlines()[-1:], ["✅ our-mapping arm published under v2"])

    def test_bundle_with_no_project_counts_the_normalized_projects_it_tried(self):
        from data_sheets_schema import rocrate_normalize
        real = rocrate_normalize.build_crate_bundle
        self.docs.mkdir()
        for name in ("ALPHA", "GAMMA"):                    # BETA has no document bundle
            (self.docs / f"{name}_preprocessed.txt").write_text(name, encoding="utf-8")
        for name in ("ALPHA", "BETA"):
            (self.packages / name / "processed").mkdir(parents=True)
        (self.packages / "GAMMA" / "raw").mkdir(parents=True)     # a crate never normalized
        with patch("data_sheets_schema.rocrate_normalize.build_crate_bundle",
                   side_effect=lambda name, root: real(name, root, docs_dir=self.docs)) as build:
            r = self._invoke("bundle", projects=())

        self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)
        self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
        self.assertEqual([c.args[0] for c in build.call_args_list], ["ALPHA", "BETA"])
        self.assertEqual(r.stderr.splitlines()[-1:],
                         ["❌ 1 of 2 bundle(s) not written"], r.stderr)
        self.assertIn("No document bundle", r.stderr)
        self.assertEqual([p.name for p in self.docs.glob("*_with_crate.txt")],
                         ["ALPHA_preprocessed_with_crate.txt"])

    def test_emit_arm_with_no_project_counts_the_projects_with_a_normalized_record(self):
        for name in ("ALPHA", "BETA"):
            self._record(name, "crate_d4d")
        self._record("GAMMA", "crate_mapped_d4d")          # emit-map-arm's input, not this one's
        earlier = self.concat / "rocrate_mapped" / "v1" / "BETA_d4d.yaml"
        earlier.parent.mkdir(parents=True)
        earlier.write_text("an earlier run's record\n", encoding="utf-8")   # refused, kept
        with self._publishing_into_tmp() as emit:
            r = self._invoke("emit-arm", "--version", "v1", projects=())

        self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)
        self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
        self.assertEqual([c.args[0] for c in emit.call_args_list], ["ALPHA", "BETA"])
        self.assertEqual(r.stderr.splitlines()[-1:],
                         ["❌ 1 of 2 project(s) not published"], r.stderr)
        self.assertIn("BETA_d4d.yaml already exists", r.stderr)
        self.assertEqual(earlier.read_text(encoding="utf-8"), "an earlier run's record\n")
        self.assertEqual(sorted(p.name for p in earlier.parent.iterdir()),
                         ["ALPHA_d4d.yaml", "BETA_d4d.yaml"])

    def test_emit_map_arm_with_no_project_counts_the_projects_with_a_mapped_record(self):
        for name in ("ALPHA", "BETA"):
            self._record(name, "crate_mapped_d4d")
        self._record("GAMMA", "crate_d4d")                 # emit-arm's input, not this one's
        earlier = self.concat / "rocrate_static_map" / "v1" / "BETA_d4d.yaml"
        earlier.parent.mkdir(parents=True)
        earlier.write_text("an earlier run's record\n", encoding="utf-8")   # refused, kept
        with self._publishing_into_tmp() as emit:
            r = self._invoke("emit-map-arm", "--version", "v1", projects=())

        self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)
        self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
        self.assertEqual([c.args[0] for c in emit.call_args_list], ["ALPHA", "BETA"])
        self.assertEqual(r.stderr.splitlines()[-1:],
                         ["❌ 1 of 2 project(s) not published"], r.stderr)
        self.assertIn("BETA_d4d.yaml already exists", r.stderr)
        self.assertEqual(earlier.read_text(encoding="utf-8"), "an earlier run's record\n")
        self.assertEqual(sorted(p.name for p in earlier.parent.iterdir()),
                         ["ALPHA_d4d.yaml", "BETA_d4d.yaml"])


if __name__ == "__main__":
    unittest.main()
