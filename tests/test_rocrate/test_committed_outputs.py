"""The committed crate-mapper outputs validate against today's schema (#2916).

`data/ro-crate_packages/*/processed/` holds the working outputs of the two
deterministic mappers: `d4d rocrate map` (`*_crate_mapped_d4d.yaml`) and
`d4d rocrate normalize` (`*_crate_d4d.yaml`). #646 anchored the `doi` pattern
and nothing re-validated them, so five reports went on saying PASS over
records the schema rejected. They are not provenance records — no
`<method>_core` record pins their verdict, so `runs.validation_status` calls
them UNVERIFIED and `recheck-validation` never visits them — which leaves this
as the check that fails when a schema change makes them invalid.

The published arm directories (`rocrate_static_map/2026-07-27_ourmap-v{1,2}`,
`rocrate_mapped/2026-07-24_deterministic-v1`) are deliberately not walked:
they keep the verdicts they were published with (#426/#520).
"""

import re
import tempfile
import unittest
from pathlib import Path

import pytest

from data_sheets_schema.rocrate_map import PACKAGES_DIR, validate

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / PACKAGES_DIR

#: The five records committed when this guard was written. More may follow
#: (AI_READI once its crate maps); fewer means the glob stopped seeing them.
KNOWN = {
    "CHORUS_crate_mapped_d4d.yaml", "CM4AI_crate_mapped_d4d.yaml",
    "VOICE_crate_mapped_d4d.yaml", "CHORUS_crate_d4d.yaml", "CM4AI_crate_d4d.yaml",
}

#: A verdict line and the basis #2916 writes beside it.
VERDICT_LINE = re.compile(r"^- (?:Validation|`[^`]+_crate_d4d\.yaml`): \*\*")
BASIS = re.compile(r"\*\*(?:PASS|FAIL)\*\* — schema \S+ / sha256 [0-9a-f]{64} "
                   r"/ \d{4}-\d{2}-\d{2} \(`[^`]+`\)$")


def committed_records(packages: Path = PACKAGES) -> list[Path]:
    return sorted([*packages.glob("*/processed/*_crate_mapped_d4d.yaml"),
                   *packages.glob("*/processed/*_crate_d4d.yaml")])


def rejected(paths: list[Path]) -> list[tuple[str, str]]:
    """(path, verdict) for every record the current merged schema rejects,
    judged by the mappers' own `validate`, so the guard and the verdict the
    reports record are one instrument."""
    out = []
    for path in paths:
        verdict = validate(path)
        if verdict != "PASS":
            out.append((str(path), verdict))
    return out


@pytest.mark.corpus   # reads the committed mapper outputs under data/ (#1203)
class TestCommittedMapperOutputs(unittest.TestCase):
    def test_every_committed_record_passes_the_current_schema(self):
        records = committed_records()
        self.assertLessEqual(KNOWN, {p.name for p in records})
        self.assertEqual([], rejected(records))

    def test_the_guard_fails_a_record_with_the_resolver_url_restored(self):
        """The pre-#2916 form of a committed record: the same bytes with the
        crate's resolver URL back in `doi`."""
        source = PACKAGES / "CHORUS" / "processed" / "CHORUS_crate_mapped_d4d.yaml"
        text = source.read_text(encoding="utf-8")
        self.assertIn("\ndoi: 10.18130/V3/XNBOPG\n", text)
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / source.name
            copy.write_text(text.replace("\ndoi: 10.18130/V3/XNBOPG\n",
                                         "\ndoi: https://doi.org/10.18130/V3/XNBOPG\n"),
                            encoding="utf-8")
            found = rejected([copy])
        self.assertEqual(1, len(found))
        self.assertIn("in /doi", found[0][1])

    def test_every_committed_verdict_names_the_schema_it_was_reached_against(self):
        lines = []
        for report in sorted([*PACKAGES.glob("*/processed/*_crate_mapping_provenance.md"),
                              *PACKAGES.glob("*/processed/*_crate_changes.md")]):
            for line in report.read_text(encoding="utf-8").splitlines():
                if VERDICT_LINE.match(line):
                    lines.append((report.name, line))
        # One per mapped record and one per normalized record.
        self.assertGreaterEqual(len(lines), len(KNOWN))
        self.assertEqual([], [(name, line) for name, line in lines
                              if not BASIS.search(line)])


if __name__ == "__main__":
    unittest.main()
