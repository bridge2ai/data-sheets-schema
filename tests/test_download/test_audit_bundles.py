"""#446 — a derived bundle that is behind its inputs, detected rather than remembered.

`{PROJECT}_preprocessed_with_crate.txt` embeds the document bundle verbatim.
#421 stripped curator prose out of the document bundles and nothing rebuilt the
crate bundles, so for a day the de novo arm read 9 curation notes the baseline
arm no longer saw, while both were described as the same corpus. Nothing caught
it; #445 found it by rebuilding for an unrelated reason and diffing.

The check is rebuild-and-compare, not mtime. `crate_only` and
`healthsheet_only` are legitimately older than the document bundles because they
do not derive from them, so an mtime rule would report three false positives on
the real corpus today.
"""

import hashlib
import unittest
from pathlib import Path

from click.testing import CliRunner

REPO = Path(__file__).resolve().parents[2]
CONCAT = REPO / "data" / "preprocessed" / "concatenated"


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _run(*args):
    from data_sheets_schema.cli.download import download
    return CliRunner().invoke(download, ["audit-bundles", *args])


def _crate_inputs_complete(project: str = "CM4AI") -> bool:
    """Can this checkout rebuild the crate bundle at all?

    Part of the crate package is gitignored (`data/ro-crate_packages/*/crate/`),
    so a clean clone rebuilds the de novo bundle from fewer artifacts than it
    was built from — CI reported it stale on all three Pythons before the audit
    learned to tell the two apart (#453). Tests about crate staleness are
    meaningless where the inputs are absent, so they skip rather than assert
    something the environment cannot support.
    """
    import tempfile
    from data_sheets_schema.cli.download import _crate_evidence_in
    from data_sheets_schema.rocrate_normalize import build_crate_bundle
    bundle = CONCAT / f"{project}_preprocessed_with_crate.txt"
    if not bundle.exists():
        return False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _, included, _ = build_crate_bundle(
                project, out_path=Path(tmp) / "x.txt")
    except Exception:                                          # noqa: BLE001
        return False
    return not (_crate_evidence_in(bundle) - set(included))


@unittest.skipUnless(CONCAT.is_dir(), "corpus not present")
class TestTheAuditOverTheRealCorpus(unittest.TestCase):
    """Runs against the real bundles, and restores anything it touches."""

    def test_the_corpus_is_currently_consistent(self):
        r = _run("--strict")
        self.assertEqual(0, r.exit_code, r.output)
        self.assertIn("matches what its inputs produce", r.output)

    def test_it_catches_a_bundle_that_no_longer_matches_its_inputs(self):
        """The canary for the checker itself. A checker that has never been
        seen to fail is not evidence of anything."""
        target = CONCAT / "CM4AI_preprocessed.txt"
        original = target.read_bytes()
        self.addCleanup(target.write_bytes, original)

        target.write_bytes(original + b"\n# an edit nothing rebuilt\n")
        r = _run("--strict")
        self.assertEqual(1, r.exit_code)
        self.assertIn("CM4AI_preprocessed.txt", r.output)
        self.assertIn("d4d download concatenate --project CM4AI", r.output)

    @unittest.skipUnless(_crate_inputs_complete(),
                         "crate inputs are gitignored and absent here (#453)")
    def test_the_crate_bundle_is_reported_when_the_document_bundle_moves(self):
        """The propagation failure itself: editing the document bundle makes
        the crate bundle stale, because the crate bundle embeds it."""
        target = CONCAT / "CM4AI_preprocessed.txt"
        original = target.read_bytes()
        self.addCleanup(target.write_bytes, original)

        target.write_bytes(original + b"\n# an edit nothing rebuilt\n")
        r = _run()
        self.assertIn("CM4AI_preprocessed_with_crate.txt", r.output)
        self.assertIn("d4d rocrate bundle --project CM4AI", r.output)

    def test_restoring_the_bytes_restores_the_verdict(self):
        target = CONCAT / "CM4AI_preprocessed.txt"
        before = _md5(target)
        original = target.read_bytes()
        target.write_bytes(original + b"\n# temporary\n")
        target.write_bytes(original)
        self.assertEqual(before, _md5(target))
        self.assertEqual(0, _run("--strict").exit_code)

    def test_unrebuildable_bundles_are_named_rather_than_passed(self):
        """A bundle with no registered rebuild route cannot be checked, and
        that is a gap in this command — not evidence the file is current."""
        r = _run()
        self.assertIn("no rebuild route registered", r.output)
        self.assertIn("crate_only", r.output)


@unittest.skipUnless(CONCAT.is_dir(), "corpus not present")
class TestTheBuildersAreDeterministic(unittest.TestCase):
    """Rebuild-and-compare is only sound if a rebuild is reproducible; a
    builder that stamped a timestamp would report every bundle stale forever."""

    def test_the_crate_bundle_builds_identically_twice(self):
        import tempfile
        from data_sheets_schema.rocrate_normalize import build_crate_bundle
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.txt"
            b = Path(tmp) / "b.txt"
            build_crate_bundle("CM4AI", out_path=a)
            build_crate_bundle("CM4AI", out_path=b)
            self.assertEqual(_md5(a), _md5(b))

    def test_out_path_does_not_touch_the_real_bundle(self):
        import tempfile
        from data_sheets_schema.rocrate_normalize import build_crate_bundle
        real = CONCAT / "CM4AI_preprocessed_with_crate.txt"
        before = _md5(real)
        with tempfile.TemporaryDirectory() as tmp:
            build_crate_bundle("CM4AI", out_path=Path(tmp) / "x.txt")
        self.assertEqual(before, _md5(real))



@unittest.skipUnless(CONCAT.is_dir(), "corpus not present")
class TestAnIncompleteCheckoutIsNotStaleness(unittest.TestCase):
    """#453. Part of the crate package is gitignored, so a clean clone rebuilds
    the de novo bundle from fewer artifacts. That is a fact about the checkout,
    not about the bundle, and reporting it as `stale` sent three CI jobs red
    over a file that was current."""

    def test_the_two_are_reported_differently(self):
        r = _run("--strict")
        if _crate_inputs_complete():
            self.assertEqual(0, r.exit_code, r.output)
            self.assertNotIn("missing crate artifacts", r.output)
        else:
            # The clean-clone case: named, not failed.
            self.assertEqual(0, r.exit_code, r.output)
            self.assertIn("missing crate artifacts", r.output)

    def test_the_header_names_what_the_bundle_was_built_from(self):
        """The comparison only works because the bundle records its own inputs;
        without that, "fewer inputs" and "different output" are the same
        observation."""
        from data_sheets_schema.cli.download import _crate_evidence_in
        bundle = CONCAT / "CM4AI_preprocessed_with_crate.txt"
        self.assertIn("CM4AI_crate_metadata_reduced.json",
                      _crate_evidence_in(bundle))

if __name__ == "__main__":
    unittest.main()
