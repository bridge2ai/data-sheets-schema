#!/usr/bin/env python3
"""
CLI tests for d4d rocrate commands.
"""

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


class _PerProjectLoopFixture(unittest.TestCase):
    """Three declared projects; temporary crate-package, document-bundle and
    publication directories; and a runner that starts every run in an empty
    working directory. The per-project loop tests below share it; it holds no
    tests of its own."""

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


class TestPerProjectLoopsEndWithACount(_PerProjectLoopFixture):
    """#3638. bundle, emit-arm and emit-map-arm counted the projects they did
    not finish, then exited 1 without printing the count, so a caller reading
    only the last line could not tell how many had failed. Each now ends with
    one stderr line naming what it counts, before the exit. A run with nothing
    to count ends as it did, as normalize and map do (#3359).

    Both numbers count projects, and the total is how many the loop tried.
    With --project they are the names given, a repeated name once (#4165).
    With none, which is how notes/D4D_GENERATION_ARMS.md runs all three, they
    are the declared projects that have the input the command looks for.

    In the mixed runs, which name all three projects and BETA twice, BETA
    fails and ALPHA and GAMMA succeed, so the count, the total and the number
    that succeeded all differ, and a count of the names given would read
    "2 of 4". In the no-project runs (#4155) only ALPHA and BETA have the
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

    MIXED = ("ALPHA", "BETA", "GAMMA", "BETA")             # BETA, which fails, twice (#4165)

    def test_bundle_counts_the_bundles_it_did_not_write(self):
        from data_sheets_schema import rocrate_normalize
        real = rocrate_normalize.build_crate_bundle
        self.docs.mkdir()
        for name in ("ALPHA", "GAMMA"):                    # BETA has no document bundle
            (self.docs / f"{name}_preprocessed.txt").write_text(name, encoding="utf-8")
            (self.packages / name / "processed").mkdir(parents=True)
        with patch("data_sheets_schema.rocrate_normalize.build_crate_bundle",
                   side_effect=lambda name, root: real(name, root, docs_dir=self.docs)):
            r = self._invoke("bundle", projects=self.MIXED)
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
            r = self._invoke("emit-arm", "--version", "v1", projects=self.MIXED)
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
            r = self._invoke("emit-map-arm", "--version", "v1", projects=self.MIXED)
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


class TestARepeatedProjectRunsOnce(_PerProjectLoopFixture):
    """#4165. `project_choice` returns --project as typed, so a name given
    twice ran its project twice. The emit commands then refused the record the
    first pass had just published: a run that published every project exited
    1, its last line saying one was not. Each of the five commands now runs a
    repeated name once, in the order first given, with one stderr line saying
    so, and the #3638 count counts projects.

    BETA is given three times around ALPHA, so the order kept (BETA first) is
    neither alphabetical nor the manifest's, and the line must give the real
    number of times. normalize and map run with their library function
    replaced by a recorder, as #4165 was reproduced; the others run for real.
    """

    NAMES = ("BETA", "ALPHA", "BETA", "BETA")
    NOTICE = "⚠️  --project BETA was given 3 times; it runs once"

    def _assert_ran_once_each(self, r, library):
        self.assertEqual([c.args[0] for c in library.call_args_list], ["BETA", "ALPHA"],
                         r.stdout + r.stderr)
        self.assertEqual([line for line in r.stderr.splitlines() if "runs once" in line],
                         [self.NOTICE], r.stderr)

    def test_normalize_runs_a_repeated_project_once(self):
        from data_sheets_schema.rocrate_normalize import Result
        with patch("data_sheets_schema.rocrate_normalize.normalize_project",
                   side_effect=lambda name, root, sv=None: Result(
                       project=name, validation={f"{name}_crate_d4d.yaml": "PASS"})) as run:
            r = self._invoke("normalize", projects=self.NAMES)

        self.assertEqual(r.exit_code, 0, r.stdout + r.stderr)
        self._assert_ran_once_each(r, run)
        self.assertEqual(r.stdout.splitlines()[-1:], ["✅ Normalization complete"])

    def test_bundle_runs_a_repeated_project_once_and_counts_projects(self):
        from data_sheets_schema import rocrate_normalize
        real = rocrate_normalize.build_crate_bundle
        self.docs.mkdir()                                  # BETA has no document bundle
        (self.docs / "ALPHA_preprocessed.txt").write_text("ALPHA", encoding="utf-8")
        (self.packages / "ALPHA" / "processed").mkdir(parents=True)
        with patch("data_sheets_schema.rocrate_normalize.build_crate_bundle",
                   side_effect=lambda name, root: real(name, root, docs_dir=self.docs)) as build:
            r = self._invoke("bundle", projects=self.NAMES)

        self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)
        self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
        self._assert_ran_once_each(r, build)
        self.assertEqual(r.stderr.count("No document bundle"), 1, r.stderr)
        self.assertEqual(r.stderr.splitlines()[-1:],
                         ["❌ 1 of 2 bundle(s) not written"], r.stderr)   # was 3 of 4
        self.assertEqual([p.name for p in self.docs.glob("*_with_crate.txt")],
                         ["ALPHA_preprocessed_with_crate.txt"])

    def test_emit_arm_runs_a_repeated_project_once(self):
        for name in ("ALPHA", "BETA"):
            self._record(name, "crate_d4d")
        with self._publishing_into_tmp() as emit:
            r = self._invoke("emit-arm", "--version", "v1", projects=self.NAMES)

        self.assertEqual(r.exit_code, 0, r.stdout + r.stderr)   # not refused against itself
        self._assert_ran_once_each(r, emit)
        self.assertNotIn("❌", r.stderr)
        self.assertEqual(r.stdout.splitlines()[-1:],
                         ["✅ Deterministic arm published under version v1"])
        self.assertEqual(sorted(p.name for p in (self.concat / "rocrate_mapped" / "v1").iterdir()),
                         ["ALPHA_d4d.yaml", "BETA_d4d.yaml"])

    def test_map_runs_a_repeated_project_once(self):
        from data_sheets_schema.rocrate_map import MapResult
        # load_mapping reads a path relative to the working directory, which is empty
        with patch("data_sheets_schema.rocrate_map.load_mapping", return_value=[]), \
             patch("data_sheets_schema.rocrate_map.map_project",
                   side_effect=lambda name, root, sv=None, rows=None: MapResult(
                       project=name, validation="PASS")) as run:
            r = self._invoke("map", projects=self.NAMES)

        self.assertEqual(r.exit_code, 0, r.stdout + r.stderr)
        self._assert_ran_once_each(r, run)
        self.assertEqual(r.stdout.splitlines()[-1:], ["✅ Static mapping complete"])

    def test_emit_map_arm_runs_a_repeated_project_once(self):
        for name in ("ALPHA", "BETA"):
            self._record(name, "crate_mapped_d4d")
        with self._publishing_into_tmp() as emit:
            r = self._invoke("emit-map-arm", "--version", "v1", projects=self.NAMES)

        self.assertEqual(r.exit_code, 0, r.stdout + r.stderr)
        self._assert_ran_once_each(r, emit)
        self.assertNotIn("❌", r.stderr)
        self.assertEqual(r.stdout.splitlines()[-1:], ["✅ our-mapping arm published under v1"])
        self.assertEqual(
            sorted(p.name for p in (self.concat / "rocrate_static_map" / "v1").iterdir()),
            ["ALPHA_d4d.yaml", "BETA_d4d.yaml"])

    def test_each_repeated_name_gets_its_own_line_in_the_order_first_given(self):
        """Two names repeated, each a different number of times, and one given
        once: a line apiece for the two, in the order first given, none for
        the third."""
        from data_sheets_schema.rocrate_normalize import Result
        with patch("data_sheets_schema.rocrate_normalize.normalize_project",
                   side_effect=lambda name, root, sv=None: Result(project=name)) as run:
            r = self._invoke("normalize",
                             projects=("GAMMA", "ALPHA", "BETA", "GAMMA", "ALPHA", "GAMMA"))

        self.assertEqual(r.exit_code, 0, r.stdout + r.stderr)
        self.assertEqual([c.args[0] for c in run.call_args_list], ["GAMMA", "ALPHA", "BETA"])
        self.assertEqual(r.stderr.splitlines(),
                         ["⚠️  --project GAMMA was given 3 times; it runs once",
                          "⚠️  --project ALPHA was given 2 times; it runs once"], r.stderr)


class TestAnUnexpectedErrorIsCountedAndNamed(_PerProjectLoopFixture):
    """#4147 and #4148. The emit commands caught only their two refusals, so
    any other error from a project (a PermissionError writing its record, a
    UnicodeDecodeError reading it) left the loop there: the projects after it
    were never tried, no count was printed, and the caller saw a traceback.
    They now catch any Exception, as bundle does, and go on.

    bundle printed the bare message, so a KeyError read as its quoted key and a
    message-less error as nothing at all. Each error line now names the type of
    anything but an expected refusal, whose text is unchanged, and an error with
    no message, a refusal's type included, reads as its type alone.
    KeyboardInterrupt and SystemExit are not Exceptions, and still stop the loop.
    """

    EMITS = (("emit-arm", "rocrate_mapped", "crate_d4d"),
             ("emit-map-arm", "rocrate_static_map", "crate_mapped_d4d"))

    def _alpha_raises(self, function, exc, **into_tmp):
        """The library function, run for real into the temporary directories,
        except that ALPHA raises `exc` before anything is written."""
        from data_sheets_schema import rocrate_normalize
        real = getattr(rocrate_normalize, function)

        def run(name, *args, **kw):
            if name == "ALPHA":
                raise exc
            return real(name, *args, **into_tmp, **kw)
        return patch(f"data_sheets_schema.rocrate_normalize.{function}", side_effect=run)

    def _check_the_emit_loop_goes_on(self, command, method, variant):
        for name in ("ALPHA", "BETA"):
            self._record(name, variant)
        errors = ((PermissionError(13, "Permission denied", "ALPHA_d4d.yaml"),
                   "PermissionError: [Errno 13] Permission denied: 'ALPHA_d4d.yaml'"),
                  (KeyError("x"), "KeyError: 'x'"),
                  (PermissionError(), "PermissionError"),         # no message
                  (FileNotFoundError(), "FileNotFoundError"))     # a refusal's type, no message
        for n, (exc, reason) in enumerate(errors):
            version = f"v{n}"
            with self.subTest(reason=reason), \
                 self._alpha_raises("emit_deterministic_arm", exc, concat_dir=self.concat) as emit:
                r = self._invoke(command, "--version", version, projects=("ALPHA", "BETA"))

                self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)   # not a crash
                self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
                self.assertEqual([c.args[0] for c in emit.call_args_list], ["ALPHA", "BETA"])
                self.assertEqual(r.stderr.splitlines(),
                                 [f"  ❌ ALPHA: {reason}", "",
                                  "❌ 1 of 2 project(s) not published"], r.stderr)
                self.assertEqual([p.name for p in (self.concat / method / version).iterdir()],
                                 ["BETA_d4d.yaml"])

    def test_emit_arm_goes_on_after_an_unexpected_error(self):
        self._check_the_emit_loop_goes_on("emit-arm", "rocrate_mapped", "crate_d4d")

    def test_emit_map_arm_goes_on_after_an_unexpected_error(self):
        self._check_the_emit_loop_goes_on("emit-map-arm", "rocrate_static_map",
                                          "crate_mapped_d4d")

    def test_an_interrupt_or_exit_still_stops_an_emit_loop(self):
        """Exception, never BaseException: the next project is not tried."""
        for command, method, variant in self.EMITS:
            for name in ("ALPHA", "BETA"):
                self._record(name, variant)
            for exc, code in ((KeyboardInterrupt(), 1), (SystemExit(3), 3)):
                with self.subTest(command=command, stop=type(exc).__name__), \
                     self._alpha_raises("emit_deterministic_arm", exc,
                                        concat_dir=self.concat) as emit:
                    r = self._invoke(command, "--version", "v1", projects=("ALPHA", "BETA"))

                    self.assertEqual(r.exit_code, code, r.stdout + r.stderr)
                    self.assertEqual([c.args[0] for c in emit.call_args_list], ["ALPHA"])
                    self.assertNotIn("not published", r.stderr)
                    self.assertFalse((self.concat / method).exists())

    def test_bundle_names_an_unexpected_error_and_never_prints_a_bare_reason(self):
        from data_sheets_schema.rocrate_normalize import DeNovoPolicyError
        self.docs.mkdir()                                  # BETA has no document bundle
        refusal = (f"  ❌ No document bundle at {self.docs / 'BETA_preprocessed.txt'}; "
                   "run `make concat-preprocessed` first")
        withheld = "'ALPHA_crate_d4d.yaml' is withheld from the de novo fork: already D4D"
        for exc, line in ((KeyError("x"), "  ❌ KeyError: 'x'"),
                          (RuntimeError(), "  ❌ RuntimeError"),          # no message
                          (DeNovoPolicyError(withheld), f"  ❌ {withheld}"),   # a refusal
                          (FileNotFoundError(), "  ❌ FileNotFoundError")):   # one with no message
            with self.subTest(line=line), \
                 self._alpha_raises("build_crate_bundle", exc, docs_dir=self.docs) as build:
                r = self._invoke("bundle", projects=("ALPHA", "BETA"))

                self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)
                self.assertEqual([c.args[0] for c in build.call_args_list], ["ALPHA", "BETA"])
                self.assertEqual(r.stderr.splitlines(),
                                 [line, refusal, "", "❌ 2 of 2 bundle(s) not written"],
                                 r.stderr)

    def test_the_emit_refusals_read_as_before(self):
        """The two refusals the emit commands always caught are messages
        written for the reader, and get no type."""
        for command, method, variant in self.EMITS:
            self._record("BETA", variant)                  # GAMMA has no record
            earlier = self.concat / method / "v1" / "BETA_d4d.yaml"
            earlier.parent.mkdir(parents=True)
            earlier.write_text("an earlier run's record\n", encoding="utf-8")
            missing = self.packages / "GAMMA" / "processed" / f"GAMMA_{variant}.yaml"
            with self.subTest(command=command), self._publishing_into_tmp():
                r = self._invoke(command, "--version", "v1", projects=("BETA", "GAMMA"))

                self.assertEqual(r.stderr.splitlines(), [
                    f"  ❌ BETA: {earlier} already exists; use a new version label "
                    "rather than overwriting a published run",
                    f"  ❌ GAMMA: No normalized record at {missing}; "
                    "run `d4d rocrate normalize` first",
                    "", "❌ 2 of 2 project(s) not published"], r.stderr)


if __name__ == "__main__":
    unittest.main()
