"""Is the schema a run is generated against the schema this repo holds?

The digest sent to the model, the schema records are validated against and the
identity slots the pair checker uses are all read from the *merged* schemas,
which are generated artifacts. A module edited without regenerating makes every
record in an arm attest to a digest describing an older schema — and no field
in the record can reveal it, because the record correctly hashes the merged
file it actually read.

Nothing checked this before a generation run. `make check-sync` exists and is
not on the generation path; #521 records a period when it reported staleness
and the remedy it named was a silent no-op.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from data_sheets_schema import schema_digest
from data_sheets_schema.profiles import BRIDGE2AI   # the study's instrument, whatever D4D_PROFILE says (#1497)
from data_sheets_schema.schema_sync import (
    IN_SYNC,
    MERGED_SCHEMAS,
    STALE,
    UNCHECKED,
    blocking,
    check,
    check_one,
)


class DigestIsAFunctionOfContentTest(unittest.TestCase):
    """The digest must not depend on where the file sits.

    It did: the rendered digest names the schema it came from, so identical
    bytes in a temp directory fingerprinted differently. That silently broke
    the check this module exists to perform, because rebuild-and-compare builds
    into a temp directory — three digests for one schema:
    `44d29023` in place, `2c93af56` rebuilt, `173abe3e` copied.
    """

    SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")

    def test_identical_bytes_elsewhere_fingerprint_the_same(self):
        if not self.SCHEMA.exists():
            self.skipTest("merged schema not present in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / self.SCHEMA.name
            shutil.copy2(self.SCHEMA, copy)
            here = schema_digest.fingerprint(
                schema_digest.digest_text("Dataset", self.SCHEMA))
            there = schema_digest.fingerprint(
                schema_digest.digest_text("Dataset", copy))
            self.assertEqual(here, there)

    def test_the_committed_digest_did_not_move(self):
        """A digest move must be a deliberate act, acknowledged here.

        This constant is the acknowledgment. When it fails, either the schema
        moved by accident — investigate before touching this — or it moved on
        purpose, in which case updating the constant is the record that
        someone meant it.

        Moves so far: `44d29023` → `580992ed` on 2026-08-21, anchoring the
        `doi` pattern (#646), after the v5 arm completed. Both study arms were
        re-validated under the new schema (24 records, all valid — they write
        bare DOIs); every non-bare doi value in the corpus (~100–122 by
        file scope; the count is scope-dependent, the location is not) lives
        in labels from 2026-08-12 or earlier,
        which keep the verdicts they were pinned with (#426).

        `580992ed` → `163c7e4d` on 2026-09-03: the digest renders two levels
        of object range (`NESTING_DEPTH`, #900, v8 plan step A) reached
        through inlined attributes — Grant, Organization, Person (via
        `committee_members`) and File join the 67 — and marks the eight
        class-ranged attributes that are references, not inlined objects
        (`principal_investigator: Person (reference — a string, not an
        object)`, #805), with no change to the schema itself, so no
        record's validity moves; the slot inventory recorded under the new
        digest is identical to the old one. Every run from here records the
        new digest; the v7 arm keeps `580992ed`, which is one of the things
        v7-vs-v8 measures. The CoreDataset digest moves with it
        (`b0c42638` → `10d60d20`); it is not pinned here because the ledger
        keys on the Dataset digest (`LEDGER_KEY_CLASS`).

        `163c7e4d` → `ffe03dd4` on 2026-09-03 (D1, #805): the five
        Person-ranged slots are `inlined: true` with descriptions that ask
        for the object, and the reference marking now follows LinkML's own
        rule (`SchemaView.is_inlined`: a class range with no identifier is
        inlined implicitly — the #927 review found the three markers the
        slot-flag test had left were false). No reference attribute remains
        in this schema; SamplingStrategy and MissingInfo join the rendered
        classes (72). A schema content change: a bare name string in those
        slots no longer validates, so records that predate it keep the
        verdicts they were pinned with (#426) and re-validate as invalid
        under this schema — the #646 precedent. The CoreDataset digest
        moves with it (`10d60d20` → `386a470d`).

        `ffe03dd4` → the pinned value below, on 2026-09-09 (#1114, #1115,
        #1126): description-only. The `doi` description gave a real Nature
        DOI as its example and the digest renders descriptions ahead of the
        arm prompt on every request; the example is now a form and the
        operative sentence (the bare DOI only) sits inside the digest's
        300-character window, where the first draft of this change had
        pushed it out. docExample annotations and the `latest_version_doi`
        description lost their real and corpus identifiers too — they reach
        the agentic runtime through the merged schema file, not the digest.
        No slot added or removed: the inventory under the new digest is the
        old one (98 Dataset, 84 CoreDataset), no record's validity moves,
        and the CoreDataset digest moves with it (`386a470d…` → `dfb9f93c…`). No v9 record exists.

        `a91bad8b` → the pinned value below, on 2026-09-13 (#1302, #628): the
        digest renders the term sources the schema's description declares
        for `Instance.data_topic` (GO, MeSH, EFO, NCIT; `schema_digest.
        TERM_SOURCES`) ahead of the pinned registry list, so a source-
        supported identifier from those ontologies is in range whether or
        not B2AI_TOPIC lists it — the scope the description has stated since
        #487 and the renderer added in #538 never carried. The vocabulary
        itself is now the active profile's: under `bridge2ai` the same
        pinned list follows the scope, under `neutral` only the scope is
        rendered (`029c2abc…`). The schema files are untouched — no slot
        added or removed, no schema hash or record validity moves — and
        both new digests are in the ledger. The v9 CHORUS canary of
        2026-09-12 consumed `a91bad8b`, which its record carries.

        `cd3c79f2` -> the pinned value below, on 2026-09-13 (#1771):
        nested string-list cardinality is now rendered. Neutral moves from
        `029c2abc` to `94859bbb`. Schema bytes and inventories are unchanged;
        the failed v10 CHORUS canary retains its prior `cd3c79f2` instrument.
        Both previous profile inventories remain in the historical ledger.
        """
        if not self.SCHEMA.exists():
            self.skipTest("merged schema not present in this checkout")
        self.assertEqual(
            schema_digest.fingerprint(schema_digest.digest_text("Dataset", profile=BRIDGE2AI)),
            "6be1582236d9320bac6040b9a8b92da9")


class SyncCheckTest(unittest.TestCase):

    def test_the_repository_is_in_sync(self):
        """If this fails, do not generate: rebuild a stale schema with the command
        `d4d schema check-digest` names for it, or fix the cause an unchecked row's reason
        names, then commit (#2775, #2790)."""
        rows = check()
        self.assertEqual(blocking(rows), [],
                         "a merged schema is stale or could not be checked (see the rows)")
        self.assertTrue(all(r["status"] == IN_SYNC for r in rows))

    def test_a_tampered_merged_schema_is_caught(self):
        """A check that never fails is indistinguishable from no check."""
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        # Other tests read the committed artifact concurrently. Tamper with
        # a private copy, including when restoring its original bytes (#1217).
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / merged.name
            original = merged.read_bytes()
            copy.write_bytes(original + b"\n# not a line any rebuild emits\n")
            row = check_one(copy, source, cls, marker)
            self.assertEqual(row["status"], STALE)
            self.assertIn("differs from a fresh build", row["reason"])
            # The evidence is kept rather than deleted with the temp dir.
            rebuilt = Path(row["rebuilt_at"])
            self.addCleanup(shutil.rmtree, rebuilt.parent)
            self.assertTrue(rebuilt.exists())
            copy.write_bytes(original)
            self.assertEqual(check_one(copy, source, cls, marker)["status"],
                             IN_SYNC, "the restored copy must be in sync")

    def test_a_missing_source_is_unchecked_and_still_blocks(self):
        """A gate that could not run has not passed."""
        row = check_one(Path("nope_all.yaml"), Path("nope.yaml"), "Dataset")
        self.assertEqual(row["status"], "unchecked")
        self.assertEqual(blocking([row]), [row])


class GateTest(unittest.TestCase):

    def test_execute_refuses_to_start_when_the_schema_is_stale(self):
        """Fatal, unlike every other check on this path.

        The others describe records that remain usable evidence; this one
        corrupts the run's central input before a token is spent.
        """
        import inspect

        from data_sheets_schema.api_runner import _execute
        source = inspect.getsource(_execute)
        self.assertIn("schema_sync", source)
        # Before the client is built, or the check is decoration.
        self.assertLess(source.index("schema_sync"), source.index("_client()"))




class RefusalWordingTest(unittest.TestCase):
    """#2738: a check that could not run is refused as unchecked, not as a stale schema."""

    def _refusal(self, rows):
        import tempfile
        from unittest import mock
        from data_sheets_schema import api_runner as api, schema_sync
        from tests.test_download.test_api_runner import FakeClient, spec
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(schema_sync, "check", lambda **_: rows):
            client = FakeClient()
            with self.assertRaises(RuntimeError) as caught:
                api.execute(spec(out_dir=Path(tmp)), client=client)
            self.assertEqual(client.messages.calls, [])
        return str(caught.exception)

    def test_an_unchecked_row_is_not_called_stale(self):
        message = self._refusal([{"class": "CoreDataset", "status": UNCHECKED,
                                  "reason": "digest could not be computed: timed out after 600 seconds"}])
        self.assertTrue(message.startswith("the schema sync check could not run"), message)
        self.assertIn("CoreDataset: digest could not be computed", message)
        self.assertIn("fix the cause named above, or retry if it was transient", message)
        self.assertTrue(message.endswith("or check with `d4d schema check-digest`."), message)
        self.assertNotIn("not built from the current source", message)
        # No rebuild advice of any kind for an unchecked row, the core's included (#2774).
        self.assertNotIn("make regen-all", message)
        self.assertNotIn("gen-core-schema", message)
        self.assertNotIn("rm -f", message)

    def test_a_stale_row_is_still_called_stale(self):
        message = self._refusal([{"class": "Dataset", "status": STALE, "reason": "rebuild differs"}])
        self.assertTrue(message.startswith("the merged schema is not built from the current source"), message)
        self.assertIn("Rebuild with `make regen-all`", message)
        self.assertTrue(message.endswith("or check with `d4d schema check-digest`."), message)
        self.assertNotIn("could not run", message)

    def test_a_stale_core_schema_is_told_how_to_rebuild_the_core(self):
        """#2756: regen-all never rebuilds the core merged schema."""
        from data_sheets_schema.schema_sync import REBUILD
        message = self._refusal([{"class": "CoreDataset", "status": STALE, "reason": "rebuild differs"}])
        # The whole command: gen-core-schema alone is a no-op on a newer stale file (#2774).
        self.assertIn(f"`{REBUILD['CoreDataset']}`", message)
        self.assertTrue(REBUILD["CoreDataset"].startswith("rm -f "))
        self.assertNotIn("make regen-all", message)
        both = self._refusal([{"class": "CoreDataset", "status": STALE, "reason": "x"},
                              {"class": "Dataset", "status": STALE, "reason": "y"}])
        self.assertIn("make gen-core-schema", both)
        self.assertIn("make regen-all", both)

    def test_both_causes_are_named_each_with_its_rows(self):
        message = self._refusal([{"class": "Dataset", "status": STALE, "reason": "rebuild differs"},
                                 {"class": "CoreDataset", "status": UNCHECKED, "reason": "timed out"}])
        stale_part, unchecked_part = message.split("; the schema sync check could not run")
        self.assertIn("Dataset: rebuild differs", stale_part)
        self.assertNotIn("CoreDataset", stale_part)
        self.assertIn("CoreDataset: timed out", unchecked_part)
        self.assertNotIn("Dataset: rebuild differs", unchecked_part)        # each row under one cause (#2799)
        # Only the stale row's rebuild: the unchecked core gets no rm -f (#2788).
        for text in ("rm -f", "gen-core-schema"):
            self.assertNotIn(text, message)


class DigestTimeoutTest(unittest.TestCase):

    def test_the_digest_child_gets_the_hang_guard(self):
        """#2738: the digest child's bound is the regeneration's hang guard, not 60 s."""
        import subprocess
        from unittest import mock
        from data_sheets_schema import schema_sync
        seen = {}

        def run(*args, **kwargs):
            seen.update(kwargs)
            raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
        schema_sync.forget_rebuilds()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(schema_sync.subprocess, "run", run):
            schema = Path(tmp) / "x.yaml"; schema.write_text("id: x\n")
            with self.assertRaises(subprocess.TimeoutExpired):
                schema_sync._rebuilt_fingerprint("Dataset", schema, schema, "x.yaml")
        self.assertEqual(seen["timeout"], schema_sync.DIGEST_TIMEOUT_SECONDS)
        self.assertGreaterEqual(schema_sync.DIGEST_TIMEOUT_SECONDS, 600)


class CheckDigestSummaryTest(unittest.TestCase):

    def test_the_summary_tells_stale_from_unchecked(self):
        """#2738: `d4d schema check-digest` counts each cause under its own advice."""
        from unittest import mock
        from click.testing import CliRunner
        from data_sheets_schema import schema_sync
        from data_sheets_schema.cli.schema import schema as schema_cli
        rows = [{"class": "Dataset", "status": STALE, "merged": "a.yaml", "reason": "rebuild differs"},
                {"class": "CoreDataset", "status": UNCHECKED, "merged": "b.yaml", "reason": "timed out"},
                {"class": "Other", "status": IN_SYNC, "merged": "c.yaml"}]
        for given, says, never in (
                (rows, ["1 of 3 merged schema(s) not current", "1 of 3 merged schema(s) could not be checked"],
                 ["rm -f", "gen-core-schema"]),                  # the unchecked core gets no rebuild (#2788)
                ([rows[1], rows[2]], ["1 of 2 merged schema(s) could not be checked"], ["not current", "regen-all"]),
                ([rows[0], rows[2]], ["1 of 2 merged schema(s) not current", "regen-all"], ["could not be checked"])):
            with mock.patch.object(schema_sync, "check", lambda **_: given):
                result = CliRunner().invoke(schema_cli, ["check-digest"])
                strict = CliRunner().invoke(schema_cli, ["check-digest", "--strict"])
            for text in says:
                self.assertIn(text, result.output)
            for text in never:
                self.assertNotIn(text, result.output)
            # --strict fails on an unchecked schema as on a stale one: it is the gate (#2758).
            self.assertEqual((result.exit_code, strict.exit_code), (0, 1), strict.output)
        with mock.patch.object(schema_sync, "check", lambda **_: [rows[2]]):
            self.assertEqual(CliRunner().invoke(schema_cli, ["check-digest", "--strict"]).exit_code, 0)

    def test_the_summary_gives_each_cause_its_advice(self):
        """#2774: the CLI names the core's own rebuild and the unchecked advice, and never
        rebuild advice for an unchecked row."""
        from unittest import mock
        from click.testing import CliRunner
        from data_sheets_schema import schema_sync
        from data_sheets_schema.cli.schema import schema as schema_cli
        stale_core = {"class": "CoreDataset", "status": STALE, "merged": "core.yaml", "reason": "differs"}
        unchecked_core = {"class": "CoreDataset", "status": UNCHECKED, "merged": "core.yaml", "reason": "timed out"}
        with mock.patch.object(schema_sync, "check", lambda **_: [stale_core]):
            stale = CliRunner().invoke(schema_cli, ["check-digest"]).output
        with mock.patch.object(schema_sync, "check", lambda **_: [unchecked_core]):
            unchecked = CliRunner().invoke(schema_cli, ["check-digest"]).output
        self.assertIn(f"`{schema_sync.REBUILD['CoreDataset']}`", stale)
        self.assertNotIn("make regen-all", stale)
        self.assertIn(schema_sync.UNCHECKED_ADVICE, unchecked)
        for text in ("gen-core-schema", "rm -f", "regen-all"):
            self.assertNotIn(text, unchecked)


class UnparseableMergedSchemaTest(unittest.TestCase):

    def test_a_merged_schema_that_differs_and_does_not_parse_is_stale(self):
        """#2773: the rebuild already shows it is stale, so the digest failing on a conflict
        marker does not make it unchecked, and its rebuild advice applies."""
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / merged.name
            copy.write_bytes(b"<<<<<<< HEAD\n" + merged.read_bytes())
            row = check_one(copy, source, cls, marker)
        kept = Path(row.get("rebuilt_at", ""))
        try:
            self.assertEqual(row["status"], STALE, row)
            self.assertIn("could not be computed", row["reason"])
            self.assertTrue(kept.is_file())
        finally:
            if kept.name:
                shutil.rmtree(kept.parent, ignore_errors=True)     # 1.4 MB a run (#2791)

    def test_a_digest_failure_on_a_matching_file_stays_unchecked(self):
        """#2773: only a file the rebuild shows differs is called stale."""
        from unittest import mock
        from data_sheets_schema import schema_sync
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        def boom(*a, **k):
            raise RuntimeError("digest child failed")
        with mock.patch.object(schema_digest, "digest_text", boom):
            row = check_one(merged, source, cls, marker)
        self.assertEqual(row["status"], UNCHECKED, row)


class StaleBranchGuardTest(unittest.TestCase):
    """#2788: a digest failure is stale only when the rebuild already differs and nothing
    moved during the check; otherwise it is unchecked, and never a crash."""

    def _row(self, *, move=None, before_compare=False):
        from unittest import mock
        from data_sheets_schema import profiles, schema_sync
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / merged.name
            copy.write_bytes(merged.read_bytes())

            def regenerate(src, target, flag, **kwargs):
                target.write_bytes(b"id: a differing rebuild\n")      # same is False
                return True, None

            def digest(*args, **kwargs):
                if move == "merged":
                    copy.write_bytes(copy.read_bytes() + b"# moved during the check\n")
                raise RuntimeError("digest failed")

            patches = [mock.patch.object(schema_sync, "_regenerate", regenerate),
                       mock.patch.object(schema_digest, "digest_text", digest)]
            if move == "source":
                patches.append(mock.patch.object(schema_sync, "_source_state", lambda _s: ("moved",)))
            if before_compare:
                def vocabulary(*a, **k):
                    raise RuntimeError("vocabulary pin missing")
                patches.append(mock.patch.object(profiles, "vocabulary_bytes", vocabulary))
            for patch in patches:
                patch.start()
            try:
                row = schema_sync.check_one(copy, source, cls, marker)
            finally:
                for patch in reversed(patches):
                    patch.stop()
        if row.get("rebuilt_at"):
            shutil.rmtree(Path(row["rebuilt_at"]).parent, ignore_errors=True)
        return row

    def test_a_differing_rebuild_with_a_failed_digest_is_stale(self):
        self.assertEqual(self._row()["status"], STALE)

    def test_a_merged_file_that_moved_during_the_check_is_unchecked(self):
        self.assertEqual(self._row(move="merged")["status"], UNCHECKED)

    def test_a_source_that_moved_during_the_check_is_unchecked(self):
        self.assertEqual(self._row(move="source")["status"], UNCHECKED)

    def test_a_failure_before_the_comparison_is_unchecked_not_a_crash(self):
        row = self._row(before_compare=True)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("vocabulary pin missing", row["reason"])


class RebuildOperandTest(unittest.TestCase):
    """#2788: the rebuild commands are checked against the schemas and the Makefile, not
    against themselves: the core's rm -f removes the core merged file and nothing else,
    and every make target it names exists."""

    def test_each_rebuild_command_names_its_own_merged_file_and_real_targets(self):
        import re as _re
        from data_sheets_schema.schema_sync import REBUILD
        makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text()
        targets = set(_re.findall(r"^([A-Za-z0-9_.-]+):", makefile, flags=_re.M))
        merged_by_class = {cls: str(merged) for merged, _source, cls, _marker in MERGED_SCHEMAS}
        self.assertEqual(set(REBUILD), set(merged_by_class))
        for cls, command in REBUILD.items():
            removed = _re.findall(r"rm -f (\S+)", command)
            self.assertLessEqual(set(removed), {merged_by_class[cls]}, command)
            for target in _re.findall(r"make (\S+)", command):
                self.assertIn(target, targets, command)
        self.assertEqual(_re.findall(r"rm -f (\S+)", REBUILD["CoreDataset"]), [merged_by_class["CoreDataset"]])


class SourceParseFailureTest(unittest.TestCase):

    def test_a_source_module_that_does_not_parse_is_named(self):
        """#2789: the row says the source failed, and which module, not a digest."""
        merged, source, cls, marker = MERGED_SCHEMAS[1]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp) / "schema"
            shutil.copytree(source.parent, schema_dir)
            broken = schema_dir / "D4D_Core.yaml"
            broken.write_text("<<<<<<< HEAD\n" + broken.read_text())
            row = check_one(schema_dir / merged.name, schema_dir / source.name, cls, marker)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertTrue(row["reason"].startswith("the source schema could not be read: source module "), row)
        self.assertIn("D4D_Core.yaml does not parse", row["reason"])


class RebuildDigestTimeoutTest(unittest.TestCase):

    def test_the_rebuilds_digest_timing_out_on_a_stale_file_is_stale_with_its_digest(self):
        """#2799: the #2738 failure itself, the rebuild's digest child timing out after the
        merged file's own digest was computed, on a file whose rebuild differs."""
        import subprocess
        from unittest import mock
        from data_sheets_schema import schema_sync
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")

        def regenerate(src, target, flag, **kwargs):
            target.write_bytes(b"id: a differing rebuild\n")
            return True, None

        def timed_out(*args, **kwargs):
            raise subprocess.TimeoutExpired("digest child", schema_sync.DIGEST_TIMEOUT_SECONDS)

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / merged.name
            copy.write_bytes(merged.read_bytes())
            with mock.patch.object(schema_sync, "_regenerate", regenerate), \
                 mock.patch.object(schema_sync, "_rebuilt_fingerprint", timed_out):
                row = schema_sync.check_one(copy, source, cls, marker)
        try:
            self.assertEqual(row["status"], STALE, row)
            self.assertTrue(row.get("digest"), row)                        # the merged file's own
            self.assertIn("timed out", row["reason"])
            # Not blamed on the merged file's digest, which was computed (#2805).
            self.assertTrue(row["reason"].startswith(
                "the merged schema differs from a fresh build of its source; a digest could not be computed"), row)
            # The kept file is the rebuild, the one to diff against the merged file (#2805).
            self.assertEqual(Path(row["rebuilt_at"]).read_bytes(), b"id: a differing rebuild\n")
        finally:
            if row.get("rebuilt_at"):
                shutil.rmtree(Path(row["rebuilt_at"]).parent, ignore_errors=True)


class SourceNamingNegativeTest(unittest.TestCase):

    def test_a_missing_import_is_not_called_a_parse_failure(self):
        """#2799: a module is named only when one really does not parse; a missing import
        keeps its own error."""
        merged, source, cls, marker = MERGED_SCHEMAS[1]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp) / "schema"
            shutil.copytree(source.parent, schema_dir)
            (schema_dir / "D4D_Variables.yaml").unlink()
            row = check_one(schema_dir / merged.name, schema_dir / source.name, cls, marker)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertNotIn("does not parse", row["reason"])

    def test_a_yaml_constructor_error_names_the_module(self):
        """#2800: PyYAML raises a plain ValueError for an impossible date; the module is named."""
        merged, source, cls, marker = MERGED_SCHEMAS[1]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp) / "schema"
            shutil.copytree(source.parent, schema_dir)
            broken = schema_dir / "D4D_Core.yaml"
            broken.write_text(broken.read_text() + "\ncreated_on: 2023-02-30\n")
            row = check_one(schema_dir / merged.name, schema_dir / source.name, cls, marker)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("D4D_Core.yaml does not parse", row["reason"])


class NamedFailureTest(unittest.TestCase):
    """#2804: a broken vocabulary pin, an emptied source module and a module that breaks
    while the check runs are each named, not reported as a digest failure."""

    def _core_copy(self, tmp):
        merged, source, cls, marker = MERGED_SCHEMAS[1]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        schema_dir = Path(tmp) / "schema"
        shutil.copytree(source.parent, schema_dir)
        return schema_dir / merged.name, schema_dir / source.name, cls, marker

    def test_an_emptied_source_module_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            merged, source, cls, marker = self._core_copy(tmp)
            (source.parent / "D4D_Core.yaml").write_text("")
            row = check_one(merged, source, cls, marker)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("D4D_Core.yaml is not a schema", row["reason"])

    def test_a_vocabulary_pin_that_does_not_parse_is_named(self):
        from unittest import mock
        from data_sheets_schema import profiles
        with tempfile.TemporaryDirectory() as tmp:
            merged, source, cls, marker = self._core_copy(tmp)
            with mock.patch.object(profiles, "vocabulary_bytes", lambda *a, **k: b"<<<<<<< HEAD\nsource: x\n"):
                row = check_one(merged, source, cls, marker, profile=profiles.profile_named("bridge2ai"))
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertTrue(row["reason"].startswith("the vocabulary pin "), row)
        self.assertIn("does not parse", row["reason"])

    def test_a_source_module_that_breaks_during_the_check_is_named(self):
        from unittest import mock
        from data_sheets_schema import schema_sync
        with tempfile.TemporaryDirectory() as tmp:
            merged, source, cls, marker = self._core_copy(tmp)
            broken = source.parent / "D4D_Core.yaml"

            def regenerate(src, target, flag, **kwargs):
                target.write_bytes(b"id: a differing rebuild\n")
                return True, None

            def digest(*args, **kwargs):
                broken.write_text("<<<<<<< HEAD\n" + broken.read_text())    # a merge lands mid-check
                raise RuntimeError("digest failed")

            with mock.patch.object(schema_sync, "_regenerate", regenerate), \
                 mock.patch.object(schema_digest, "digest_text", digest):
                row = schema_sync.check_one(merged, source, cls, marker)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertTrue(row["reason"].startswith("the source schema could not be read (it changed during the check)"), row)
        self.assertIn("D4D_Core.yaml does not parse", row["reason"])


class BrokenFreshBuildTest(unittest.TestCase):

    def test_a_fresh_build_that_does_not_digest_needs_source_repair_not_a_rebuild(self):
        """#2808: the merged file digests and the rebuild differs, but the rebuild's digest
        fails for a reason other than time (a renamed root class): rebuilding cannot help,
        so the row is unchecked and says the source needs repair."""
        from unittest import mock
        from data_sheets_schema import schema_sync
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")

        def regenerate(src, target, flag, **kwargs):
            target.write_bytes(b"id: a differing rebuild\n")
            return True, None

        def broken(*args, **kwargs):
            raise schema_sync.RebuiltDigestFailed(1, 'rebuilt digest process failed: No such class: "CoreDataset"')

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / merged.name
            copy.write_bytes(merged.read_bytes())
            with mock.patch.object(schema_sync, "_regenerate", regenerate), \
                 mock.patch.object(schema_sync, "_rebuilt_fingerprint", broken):
                row = schema_sync.check_one(copy, source, cls, marker)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertTrue(row["reason"].startswith("a fresh build of the source could not be digested"), row)
        self.assertNotIn("rebuilt_at", row)


class UnnamedWrapperTest(unittest.TestCase):

    def test_a_wrapper_with_an_id_but_no_name_is_not_blamed(self):
        """#2809: the loader derives a missing name from the id, so the broken import is
        the one named."""
        merged, source, cls, marker = MERGED_SCHEMAS[1]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp) / "schema"
            shutil.copytree(source.parent, schema_dir)
            wrapper = schema_dir / source.name
            wrapper.write_text("\n".join(line for line in wrapper.read_text().splitlines()
                                          if not line.startswith("name:")) + "\n")
            broken = schema_dir / "D4D_Core.yaml"
            broken.write_text("<<<<<<< HEAD\n" + broken.read_text())
            row = check_one(schema_dir / merged.name, wrapper, cls, marker)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("D4D_Core.yaml does not parse", row["reason"])
        self.assertNotIn("is not a schema", row["reason"])


class ClassificationEdgeTest(unittest.TestCase):
    """#2814-#2816: a process failure is not a source defect; a pin that is no mapping,
    or that changes during the check, is named, not advised a rebuild."""

    def _row(self, *, rebuilt_error=None, profile_name=None, pin=None, pin_after=None):
        from unittest import mock
        from data_sheets_schema import profiles, schema_sync
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        calls = []

        def regenerate(src, target, flag, **kwargs):
            target.write_bytes(b"id: a differing rebuild\n")
            return True, None

        def vocabulary(*args, **kwargs):
            calls.append(1)
            return pin if (pin_after is None or len(calls) == 1) else pin_after

        def failing(*args, **kwargs):
            raise rebuilt_error

        def digest_fails(*args, **kwargs):
            raise RuntimeError("digest failed")

        patches = [mock.patch.object(schema_sync, "_regenerate", regenerate)]
        if rebuilt_error is not None:
            patches.append(mock.patch.object(schema_sync, "_rebuilt_fingerprint", failing))
        if pin is not None:
            patches.append(mock.patch.object(profiles, "vocabulary_bytes", vocabulary))
        if pin_after is not None:
            patches.append(mock.patch.object(schema_digest, "digest_text", digest_fails))
        profile = profiles.profile_named(profile_name) if profile_name else None
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / merged.name
            copy.write_bytes(merged.read_bytes())
            for patch in patches:
                patch.start()
            try:
                row = schema_sync.check_one(copy, source, cls, marker, profile=profile)
            finally:
                for patch in reversed(patches):
                    patch.stop()
        if row.get("rebuilt_at"):
            shutil.rmtree(Path(row["rebuilt_at"]).parent, ignore_errors=True)
        return row

    def test_a_killed_digest_child_is_stale_not_a_source_defect(self):
        from data_sheets_schema import schema_sync
        row = self._row(rebuilt_error=schema_sync.RebuiltDigestFailed(-9, "rebuilt digest process failed: "))
        self.assertEqual(row["status"], STALE, row)
        self.assertNotIn("source needs repair", row["reason"])

    def test_an_unspawnable_digest_child_is_stale_not_a_source_defect(self):
        row = self._row(rebuilt_error=BlockingIOError(11, "Resource temporarily unavailable"))
        self.assertEqual(row["status"], STALE, row)
        self.assertNotIn("source needs repair", row["reason"])

    def test_a_pin_that_is_not_a_mapping_is_named(self):
        row = self._row(profile_name="bridge2ai", pin=b"- invalid\n")
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertTrue(row["reason"].startswith("the vocabulary pin "), row)
        self.assertIn("is not a mapping", row["reason"])

    def test_a_pin_that_changes_during_the_check_is_a_retry(self):
        row = self._row(profile_name="bridge2ai", pin=b"vocabularies: {}\n",
                        pin_after=b"<<<<<<< HEAD\nsource: x\n")
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("changed during the sync check", row["reason"])


class NestedPinTest(unittest.TestCase):
    """#2820: a pin malformed below its top level fails only when rendered; the digest
    that fails succeeds without it, so the pin is named, not a rebuild or a repair."""

    BAD_PIN = b"vocabularies: {B2AI_TOPIC: [B2AI_TOPIC:1]}\n"

    def _run(self, *, fail_live):
        from unittest import mock
        from data_sheets_schema import profiles, schema_sync
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        bridge2ai = profiles.profile_named("bridge2ai")

        def regenerate(src, target, flag, **kwargs):
            target.write_bytes(merged.read_bytes())            # the fresh build, without the comment
            return True, None

        def digest(class_name, path, *, profile=None):
            if fail_live and profile is not None and profile.name == "bridge2ai":
                raise AttributeError("'list' object has no attribute 'items'")
            return "live digest text"

        def rebuilt(class_name, path, vocabulary, name, profile=None):
            if profile is not None and profile.name == "bridge2ai":
                raise schema_sync.RebuiltDigestFailed(1, "rebuilt digest process failed: 'list' object has no attribute 'items'")
            return "0" * 32

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / merged.name
            copy.write_bytes(merged.read_bytes() + b"\n# a comment\n")
            with mock.patch.object(schema_sync, "_regenerate", regenerate), \
                 mock.patch.object(profiles, "vocabulary_bytes",
                                   lambda p: self.BAD_PIN if p.name == "bridge2ai" else b""), \
                 mock.patch.object(schema_digest, "digest_text", digest), \
                 mock.patch.object(schema_sync, "_rebuilt_fingerprint", rebuilt):
                row = schema_sync.check_one(copy, source, cls, marker, profile=bridge2ai)
        if row.get("rebuilt_at"):
            shutil.rmtree(Path(row["rebuilt_at"]).parent, ignore_errors=True)
        return row

    def test_the_live_digest_failing_on_the_pin_names_it(self):
        row = self._run(fail_live=True)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertTrue(row["reason"].startswith("the vocabulary pin "), row)
        self.assertIn("cannot be rendered", row["reason"])

    def test_the_fresh_builds_digest_failing_on_the_pin_names_it(self):
        row = self._run(fail_live=False)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("cannot be rendered", row["reason"])
        self.assertNotIn("source needs repair", row["reason"])


class _PinHarness:
    """check_one on a merged copy that differs from its rebuild, under the bridge2ai
    profile with a healthy pin, the child digest `rebuilt` and the live `digest`."""

    GOOD_PIN = b"vocabularies: {}\n"

    def _run(self, rebuilt, *, source_state=None, digest=None):
        from unittest import mock
        from data_sheets_schema import profiles, schema_sync
        merged, source, cls, marker = MERGED_SCHEMAS[0]
        if not merged.exists():
            self.skipTest("merged schema not present in this checkout")
        self.pin = self.GOOD_PIN

        def regenerate(src, target, flag, **kwargs):
            target.write_bytes(merged.read_bytes())
            return True, None

        patches = [mock.patch.object(schema_sync, "_regenerate", regenerate),
                   mock.patch.object(profiles, "vocabulary_bytes", lambda p: self.pin if p.name == "bridge2ai" else b""),
                   mock.patch.object(schema_digest, "digest_text", digest or (lambda *a, **k: "live digest text")),
                   mock.patch.object(schema_sync, "_rebuilt_fingerprint", rebuilt)]
        if source_state is not None:
            patches.append(mock.patch.object(schema_sync, "_source_state", source_state))
        with tempfile.TemporaryDirectory() as tmp:
            self.copy = copy = Path(tmp) / merged.name
            copy.write_bytes(merged.read_bytes() + b"\n# a comment\n")
            for patch in patches:
                patch.start()
            try:
                row = schema_sync.check_one(copy, source, cls, marker, profile=profiles.profile_named("bridge2ai"))
            finally:
                for patch in reversed(patches):
                    patch.stop()
        if row.get("rebuilt_at"):
            shutil.rmtree(Path(row["rebuilt_at"]).parent, ignore_errors=True)
        return row


class HealthyPinTest(_PinHarness, unittest.TestCase):
    """#2827: a healthy pin is never blamed for a process failure, a failure that does
    not recur, or a source that broke after both digests succeeded."""

    def test_a_killed_child_does_not_blame_the_pin(self):
        from data_sheets_schema import schema_sync

        def rebuilt(class_name, path, vocabulary, name, profile=None):
            if profile is not None and profile.name == "bridge2ai":
                raise schema_sync.RebuiltDigestFailed(-9, "rebuilt digest process failed: ")
            return "0" * 32
        row = self._run(rebuilt)
        self.assertEqual(row["status"], STALE, row)
        self.assertNotIn("vocabulary pin", row["reason"])

    def test_a_failure_that_does_not_recur_is_neither_the_pin_nor_the_source(self):
        from data_sheets_schema import schema_sync
        calls = []

        def rebuilt(class_name, path, vocabulary, name, profile=None):
            calls.append(profile.name if profile else None)
            if len(calls) == 1:
                raise schema_sync.RebuiltDigestFailed(1, "rebuilt digest process failed: a passing fault")
            return "0" * 32
        row = self._run(rebuilt)
        self.assertEqual(row["status"], STALE, row)
        self.assertNotIn("vocabulary pin", row["reason"])
        self.assertNotIn("source needs repair", row["reason"])

    def test_a_source_that_broke_after_both_digests_is_named_not_the_pin(self):
        def source_state(src):            # read only after both digests: the source broke meanwhile
            raise ValueError("source module D4D_Core.yaml does not parse: conflict marker")
        row = self._run(lambda *a, **k: "0" * 32, source_state=source_state)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertTrue(row["reason"].startswith("the source schema could not be read (it changed during the check)"), row)



class DiagnosticProbeTest(_PinHarness, unittest.TestCase):
    """#2747 Codex review: the digest that failed is probed again, then without the
    vocabulary, on the bytes the check read. A probe that fails as a process is
    inconclusive, not evidence against the pin or the source, and a diagnosis is given
    only while the live inputs are still the ones probed."""

    def sequenced(self, *outcomes):
        """A child digest that answers each call with the next outcome: an exception to
        raise, or None for a digest. Records each call's profile and schema bytes."""
        from data_sheets_schema import schema_sync
        self.calls = []

        def rebuilt(class_name, path, vocabulary, name, profile=None):
            self.calls.append((profile.name if profile else None, Path(path).read_bytes(), Path(path)))
            outcome = outcomes[len(self.calls) - 1]
            if callable(outcome):
                outcome = outcome()
            if outcome is not None:
                raise outcome
            return "0" * 32
        return rebuilt

    def test_a_retry_killed_by_a_signal_does_not_blame_the_pin(self):
        from data_sheets_schema import schema_sync
        failed = lambda code: schema_sync.RebuiltDigestFailed(code, "rebuilt digest process failed")
        row = self._run(self.sequenced(failed(1), failed(-9), None))
        self.assertEqual(row["status"], STALE, row)
        self.assertNotIn("vocabulary pin", row["reason"])
        self.assertEqual([c[0] for c in self.calls], ["bridge2ai", "bridge2ai"])    # no neutral probe

    def test_retries_that_time_out_are_not_a_source_defect(self):
        import subprocess
        from data_sheets_schema import schema_sync
        timeout = subprocess.TimeoutExpired(["digest"], 600)
        row = self._run(self.sequenced(schema_sync.RebuiltDigestFailed(1, "failed"), timeout, timeout))
        self.assertEqual(row["status"], STALE, row)
        self.assertNotIn("source needs repair", row["reason"])
        self.assertNotIn("vocabulary pin", row["reason"])

    def test_a_neutral_probe_that_fails_as_a_process_blames_neither(self):
        from data_sheets_schema import schema_sync
        failed = lambda code: schema_sync.RebuiltDigestFailed(code, "rebuilt digest process failed")
        row = self._run(self.sequenced(failed(1), failed(1), failed(-9)))
        self.assertEqual(row["status"], STALE, row)
        self.assertNotIn("source needs repair", row["reason"])
        self.assertNotIn("vocabulary pin", row["reason"])

    def test_a_recurring_failure_on_both_profiles_needs_source_repair(self):
        from data_sheets_schema import schema_sync
        failed = lambda code: schema_sync.RebuiltDigestFailed(code, "rebuilt digest process failed")
        row = self._run(self.sequenced(failed(1), failed(1), failed(1)))
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("source needs repair", row["reason"])

    def test_a_retry_that_printed_no_digest_is_not_a_source_defect(self):
        """Source repair needs the fresh build's own failure twice: a child that exited 0
        without a digest is not the source failing to digest."""
        from data_sheets_schema import schema_sync
        row = self._run(self.sequenced(schema_sync.RebuiltDigestFailed(1, "failed"),
                                       schema_sync.RebuiltDigestFailed(0, "rebuilt digest process failed: "),
                                       schema_sync.RebuiltDigestFailed(1, "failed")))
        self.assertEqual(row["status"], STALE, row)
        self.assertNotIn("source needs repair", row["reason"])

    def test_a_merged_file_repaired_during_the_probes_is_a_retry_not_the_pin(self):
        """The merged file fails to digest twice, then is repaired before the neutral
        probe: the probe still reads the bytes the check read, and the diagnosis is
        withheld because the live file moved."""
        from data_sheets_schema import schema_sync

        def live_fails(*args, **kwargs):
            raise KeyError("No such class: Dataset")

        def repair():
            self.copy.write_bytes(self.copy.read_bytes() + b"# repaired\n")
            return None                                    # the neutral probe then succeeds
        row = self._run(self.sequenced(schema_sync.RebuiltDigestFailed(1, "No such class: Dataset"), repair),
                        digest=live_fails)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("changed during the sync check", row["reason"])
        self.assertEqual([c[0] for c in self.calls], ["bridge2ai", "neutral"])
        probed = {c[1] for c in self.calls}
        self.assertEqual(len(probed), 1)                    # both probes read one set of bytes...
        self.assertNotIn(b"# repaired", probed.pop())       # ...the ones the check read
        self.assertTrue(all(c[2] != self.copy for c in self.calls))   # never the live file

    def test_a_pin_edited_during_the_probes_is_a_retry(self):
        from data_sheets_schema import schema_sync

        def edit_pin():
            self.pin = b"vocabularies: {B2AI_TOPIC: {}}\n"
            return None
        row = self._run(self.sequenced(schema_sync.RebuiltDigestFailed(1, "failed"),
                                       schema_sync.RebuiltDigestFailed(1, "failed"), edit_pin))
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("changed during the sync check", row["reason"])

    def test_a_source_edited_during_the_probes_is_a_retry_not_a_repair(self):
        from data_sheets_schema import schema_sync
        real, reads = schema_sync._source_state, []

        def source_state(src):            # as read before the probes, then edited during them
            reads.append(src)
            return real(src) if len(reads) == 1 else ("edited during the probes",)
        failed = lambda: schema_sync.RebuiltDigestFailed(1, "failed")
        row = self._run(self.sequenced(failed(), failed(), failed()), source_state=source_state)
        self.assertEqual(len(reads), 2)
        self.assertEqual(row["status"], UNCHECKED, row)
        self.assertIn("changed during the sync check", row["reason"])
        self.assertNotIn("source needs repair", row["reason"])


if __name__ == "__main__":
    unittest.main()
