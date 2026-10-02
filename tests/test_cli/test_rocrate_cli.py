#!/usr/bin/env python3
"""
CLI tests for d4d rocrate commands.
"""

import errno
import importlib.util
import json
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

import click
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
    repeated name once, in the order first given, with one stderr line for
    each repeated name, in the same order, and the #3638 count counts projects.

    BETA is given first and last; between them ALPHA is given four times and
    then GAMMA three times. In the order first given, BETA, ALPHA, GAMMA,
    ALPHA is in the middle. Ordered by how often each name was given
    (ALPHA 4, GAMMA 3, BETA 2) or by where each was last given (ALPHA,
    GAMMA, BETA), GAMMA is in the middle; alphabetically or in the
    manifest's order, BETA is. Reversing three names keeps the middle one,
    so the order first given is none of these orders in either direction:
    most or fewest repeats first, the earliest or the latest last mention
    first (a scan from the end gives the latest), A to Z or Z to A, the
    manifest's order or its reverse. All three names repeat, so the three
    notice lines must come in that order too, and since no two names were
    given the same number of times, each line must give its own name's count.

    Earlier inputs could not tell some of those orders apart. Before #4185
    the first name was also the most repeated, so the order by count matched
    the order first given. Before #4198 only two names repeated, and two
    names can only be in the order first given or its reverse, so one
    direction of each order matched it. normalize and map run with their
    library function replaced by a recorder, as #4165 was reproduced; the
    others run for real.
    """

    NAMES = ("BETA", "ALPHA", "ALPHA", "ALPHA", "ALPHA", "GAMMA", "GAMMA", "GAMMA", "BETA")
    ONCE_EACH = ["BETA", "ALPHA", "GAMMA"]
    NOTICES = ["⚠️  --project BETA was given 2 times; it runs once",
               "⚠️  --project ALPHA was given 4 times; it runs once",
               "⚠️  --project GAMMA was given 3 times; it runs once"]

    def _assert_ran_once_each(self, r, library):
        self.assertEqual([c.args[0] for c in library.call_args_list], self.ONCE_EACH,
                         r.stdout + r.stderr)
        self.assertEqual([line for line in r.stderr.splitlines() if "runs once" in line],
                         self.NOTICES, r.stderr)

    def test_the_input_tells_the_order_first_given_from_each_other_order(self):
        """What the five command tests below rely on, checked on NAMES itself
        so a later edit cannot lose it unnoticed: every name repeats, no two
        as often, and neither direction of the order by count, by last
        mention, alphabetical or the manifest's is the order first given
        (#4198)."""
        counts = [self.NAMES.count(name) for name in self.ONCE_EACH]
        last = {name: i for i, name in enumerate(self.NAMES)}     # a name's last index
        self.assertEqual(list(dict.fromkeys(self.NAMES)), self.ONCE_EACH)
        self.assertGreater(min(counts), 1)                         # a notice line apiece
        self.assertEqual(len(set(counts)), len(counts))            # no tie to break
        others = {"by count": sorted(self.ONCE_EACH, key=self.NAMES.count),
                  "by last mention": sorted(self.ONCE_EACH, key=last.get),
                  "alphabetical": sorted(self.ONCE_EACH),
                  "the manifest's": [p for p in self.PROJECTS if p in self.ONCE_EACH]}
        for label, order in others.items():
            for direction in (order, order[::-1]):
                with self.subTest(order=label, direction=direction):
                    self.assertNotEqual(direction, self.ONCE_EACH)

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
        self.docs.mkdir()
        for name in ("ALPHA", "GAMMA"):                    # BETA has no document bundle
            (self.docs / f"{name}_preprocessed.txt").write_text(name, encoding="utf-8")
            (self.packages / name / "processed").mkdir(parents=True)
        with patch("data_sheets_schema.rocrate_normalize.build_crate_bundle",
                   side_effect=lambda name, root: real(name, root, docs_dir=self.docs)) as build:
            r = self._invoke("bundle", projects=self.NAMES)

        self.assertIsInstance(r.exception, SystemExit, r.stdout + r.stderr)
        self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
        self._assert_ran_once_each(r, build)
        self.assertEqual(r.stderr.count("No document bundle"), 1, r.stderr)
        self.assertEqual(r.stderr.splitlines()[-1:],
                         ["❌ 1 of 3 bundle(s) not written"], r.stderr)   # was 2 of 9
        self.assertEqual(sorted(p.name for p in self.docs.glob("*_with_crate.txt")),
                         ["ALPHA_preprocessed_with_crate.txt",
                          "GAMMA_preprocessed_with_crate.txt"])

    def test_emit_arm_runs_a_repeated_project_once(self):
        for name in self.PROJECTS:
            self._record(name, "crate_d4d")
        with self._publishing_into_tmp() as emit:
            r = self._invoke("emit-arm", "--version", "v1", projects=self.NAMES)

        self.assertEqual(r.exit_code, 0, r.stdout + r.stderr)   # not refused against itself
        self._assert_ran_once_each(r, emit)
        self.assertNotIn("❌", r.stderr)
        self.assertEqual(r.stdout.splitlines()[-1:],
                         ["✅ Deterministic arm published under version v1"])
        self.assertEqual(sorted(p.name for p in (self.concat / "rocrate_mapped" / "v1").iterdir()),
                         ["ALPHA_d4d.yaml", "BETA_d4d.yaml", "GAMMA_d4d.yaml"])

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
        for name in self.PROJECTS:
            self._record(name, "crate_mapped_d4d")
        with self._publishing_into_tmp() as emit:
            r = self._invoke("emit-map-arm", "--version", "v1", projects=self.NAMES)

        self.assertEqual(r.exit_code, 0, r.stdout + r.stderr)
        self._assert_ran_once_each(r, emit)
        self.assertNotIn("❌", r.stderr)
        self.assertEqual(r.stdout.splitlines()[-1:], ["✅ our-mapping arm published under v1"])
        self.assertEqual(
            sorted(p.name for p in (self.concat / "rocrate_static_map" / "v1").iterdir()),
            ["ALPHA_d4d.yaml", "BETA_d4d.yaml", "GAMMA_d4d.yaml"])

    def test_each_repeated_name_gets_its_own_line_in_the_order_first_given(self):
        """Two names repeated, each a different number of times, and one given
        once: a line apiece for the two, in the order first given, none for
        the third. GAMMA comes first and last, ALPHA after it and more often,
        and BETA once, so the runs must be GAMMA, ALPHA, BETA and the lines
        GAMMA's then ALPHA's. Two lines can only be in the order first given
        or its reverse, so one direction of each other order would print them
        as here; the class's input, where three names repeat, is the one that
        tells those orders apart (#4198)."""
        from data_sheets_schema.rocrate_normalize import Result
        with patch("data_sheets_schema.rocrate_normalize.normalize_project",
                   side_effect=lambda name, root, sv=None: Result(project=name)) as run:
            r = self._invoke("normalize",
                             projects=("GAMMA", "ALPHA", "BETA", "ALPHA", "ALPHA", "GAMMA"))

        self.assertEqual(r.exit_code, 0, r.stdout + r.stderr)
        self.assertEqual([c.args[0] for c in run.call_args_list], ["GAMMA", "ALPHA", "BETA"])
        self.assertEqual(r.stderr.splitlines(),
                         ["⚠️  --project GAMMA was given 2 times; it runs once",
                          "⚠️  --project ALPHA was given 3 times; it runs once"], r.stderr)


class TestAnUnexpectedErrorIsCountedAndNamed(_PerProjectLoopFixture):
    """#4147 and #4148. The emit commands caught only their two refusals, so
    any other error from a project (a PermissionError writing its record, a
    UnicodeDecodeError reading it) left the loop there: the projects after it
    were never tried, no count was printed, and the caller saw a traceback.
    They now catch any Exception, as bundle does, and go on. Their success
    line is printed after the `try`, so an error printing it is not caught
    and counted against a project whose record was written.

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

    def test_an_error_printing_the_success_line_propagates_and_is_not_counted(self):
        """The success line is printed after the `try`, not in it (#4185). On
        a stdout that cannot encode its `✓`, or on a closed pipe, the error
        comes from the echo after the record is written; inside the `try` the
        catch-all would count that project as not published and go on to the
        next. Outside it the error propagates: a UnicodeEncodeError as itself,
        a broken pipe to click, which ends the run with a quiet exit 1."""
        real_echo = click.echo

        def closed_pipe(message=None, *args, **kw):        # the reader of stdout is gone
            if not kw.get("err") and str(message).startswith("  ✓ "):
                raise BrokenPipeError(errno.EPIPE, "Broken pipe")
            return real_echo(message, *args, **kw)

        stdouts = (("v1", "latin-1", None, UnicodeEncodeError),   # latin-1 has no ✓
                   ("v2", "utf-8", closed_pipe, SystemExit))      # click's exit 1 on EPIPE
        for command, method, variant in self.EMITS:
            for name in ("ALPHA", "BETA"):
                self._record(name, variant)
            for version, charset, echo, raised in stdouts:
                self.runner = CliRunner(mix_stderr=False, charset=charset)
                with self.subTest(command=command, raised=raised.__name__), \
                     patch("click.echo", side_effect=echo) if echo else nullcontext(), \
                     self._publishing_into_tmp() as emit:
                    r = self._invoke(command, "--version", version, projects=("ALPHA", "BETA"))

                    self.assertIsInstance(r.exception, raised, r.stdout + r.stderr)
                    self.assertEqual(r.exit_code, 1, r.stdout + r.stderr)
                    self.assertEqual([c.args[0] for c in emit.call_args_list], ["ALPHA"])
                    self.assertEqual([p.name for p in (self.concat / method / version).iterdir()],
                                     ["ALPHA_d4d.yaml"])   # written before the echo failed
                    self.assertEqual(r.stderr, "")       # nothing counted as not published

    def test_bundle_names_an_unexpected_error_and_never_prints_a_bare_reason(self):
        """DeNovoPolicyError is a RuntimeError and FileNotFoundError an
        OSError, so bundle's refusals could widen to either base. A
        RuntimeError and a PermissionError that carry a message are what
        would then print as a bare message, and fail here (#4185); an error
        with no message reads as its type alone either way."""
        from data_sheets_schema.rocrate_normalize import DeNovoPolicyError
        self.docs.mkdir()                                  # BETA has no document bundle
        refusal = (f"  ❌ BETA: No document bundle at {self.docs / 'BETA_preprocessed.txt'}; "
                   "run `make concat-preprocessed` first")
        withheld = "'ALPHA_crate_d4d.yaml' is withheld from the de novo fork: already D4D"
        denied = "ALPHA_preprocessed_with_crate.txt"
        for exc, line in ((KeyError("x"), "  ❌ ALPHA: KeyError: 'x'"),
                          # DeNovoPolicyError's base, then an OSError as FileNotFoundError is
                          (RuntimeError("boom"), "  ❌ ALPHA: RuntimeError: boom"),
                          (PermissionError(13, "Permission denied", denied),
                           f"  ❌ ALPHA: PermissionError: [Errno 13] Permission denied: '{denied}'"),
                          (RuntimeError(), "  ❌ ALPHA: RuntimeError"),          # no message
                          (DeNovoPolicyError(withheld), f"  ❌ ALPHA: {withheld}"),   # a refusal
                          (FileNotFoundError(), "  ❌ ALPHA: FileNotFoundError")):   # one with no message
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


class TestNormalizeAndMapUnexpectedErrors(_PerProjectLoopFixture):
    """Unexpected library errors are counted separately, with later projects tried."""

    def _library(self, command):
        if command == "normalize":
            return "data_sheets_schema.rocrate_normalize.normalize_project"
        return "data_sheets_schema.rocrate_map.map_project"

    def _result(self, command, name, validation):
        from data_sheets_schema.rocrate_normalize import Result
        from data_sheets_schema.rocrate_map import MapResult
        if command == "normalize":
            return Result(project=name, validation={f"{name}.yaml": validation})
        return MapResult(project=name, validation=validation)

    def test_counts_refusals_validation_and_errors_apart_and_continues(self):
        for command in ("normalize", "map"):
            for validation in ("PASS", "FAIL\ninvalid id"):
                def run(name, *args, **kwargs):
                    if name == "ALPHA":
                        raise PermissionError("read denied")
                    if name == "BETA":
                        raise FileNotFoundError("no crate")
                    return self._result(command, name, validation)

                with self.subTest(command=command, validation=validation), \
                     patch("data_sheets_schema.rocrate_map.load_mapping", return_value=[]), \
                     patch(self._library(command), side_effect=run) as operation:
                    result = self._invoke(command)
                self.assertEqual(result.exit_code, 1, result.output)
                self.assertIsInstance(result.exception, SystemExit)
                self.assertEqual([c.args[0] for c in operation.call_args_list], list(self.PROJECTS))
                self.assertIn("ALPHA: PermissionError: read denied", result.stderr)
                self.assertIn("BETA: no crate", result.stderr)
                invalid = int(validation.startswith("FAIL"))
                self.assertEqual(result.stderr.splitlines()[-1],
                                 "❌ 1 crate(s) refused (missing or unreadable), "
                                 f"{invalid} validation failure(s), 1 project error(s)")
                self.assertIn(validation.splitlines()[0], result.stdout)
                self.assertNotIn("complete", result.stdout)

    def test_empty_unexpected_error_names_its_type(self):
        for command in ("normalize", "map"):
            with self.subTest(command=command), \
                 patch("data_sheets_schema.rocrate_map.load_mapping", return_value=[]), \
                 patch(self._library(command), side_effect=RuntimeError()):
                result = self._invoke(command, projects=("ALPHA",))
            self.assertIn("ALPHA: RuntimeError", result.stderr)
            self.assertIn("1 project error(s)", result.stderr)
            self.assertEqual(result.exit_code, 1)

    def test_interrupt_and_explicit_exit_stop_the_loop(self):
        for command in ("normalize", "map"):
            for error in (KeyboardInterrupt(), SystemExit(7)):
                with self.subTest(command=command, error=error), \
                     patch("data_sheets_schema.rocrate_map.load_mapping", return_value=[]), \
                     patch(self._library(command), side_effect=error) as operation:
                    result = self._invoke(command)
                self.assertNotEqual(result.exit_code, 0)
                self.assertEqual([c.args[0] for c in operation.call_args_list], ["ALPHA"])
                self.assertNotIn("project error(s)", result.stderr)
                self.assertNotIn("complete", result.stdout)
