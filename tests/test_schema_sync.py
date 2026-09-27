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
        """If this fails, do not generate — regenerate and commit first."""
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
        self.assertNotIn("make regen-all", message)

    def test_a_stale_row_is_still_called_stale(self):
        message = self._refusal([{"class": "Dataset", "status": STALE, "reason": "rebuild differs"}])
        self.assertTrue(message.startswith("the merged schema is not built from the current source"), message)
        self.assertIn("Rebuild with `make regen-all`", message)
        self.assertTrue(message.endswith("or check with `d4d schema check-digest`."), message)
        self.assertNotIn("could not run", message)

    def test_a_stale_core_schema_is_told_how_to_rebuild_the_core(self):
        """#2756: regen-all never rebuilds the core merged schema."""
        message = self._refusal([{"class": "CoreDataset", "status": STALE, "reason": "rebuild differs"}])
        self.assertIn("make gen-core-schema", message)
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
                (rows, ["1 of 3 merged schema(s) not current", "1 of 3 merged schema(s) could not be checked"], []),
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


if __name__ == "__main__":
    unittest.main()
