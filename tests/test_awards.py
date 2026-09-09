"""Prediction 2's denominator is a stated pattern over pinned bytes (#1028).

The plan registered AI_READI 2, CHORUS 1, CM4AI 3, VOICE 3 "by the pattern
`\\b[A-Z]\\d{2}[A-Z]{2}\\d{6}\\b` and kin", counted by hand; the AI_READI bundle
states three awards in its flagship paper's funding line and the 04f record
populated three. The mechanical count is now `awards.award_numbers`, pinned
here to each bundle's md5, and the reading that decides which awards fund
*this* dataset is registered in the note beside the count.
"""
import hashlib
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import awards

ROOT = Path(__file__).resolve().parents[1]
BUNDLES = ROOT / "data" / "preprocessed" / "concatenated"

#: Per-bundle mechanical counts as registered, keyed by the bytes they were
#: counted on. A bundle rewrite that changes the count must re-register.
REGISTERED = {
    "AI_READI": ("d22b61a9f844", {"OT2OD032644": 18, "P30DK035816": 2, "UL1TR003096": 1, "UL1TR001442": 1}),
    "CHORUS": ("9b2ef4b65d67", {"OT2OD032701": 3}),
    "CM4AI": ("50037fc631ea", {"OT2OD032742": 10, "U54CA274502": 1, "U24HG012107": 1, "U24CA269436": 1,
                               "R01GM083960": 1, "P41GM109824": 1, "U24HG006673": 1, "U54HG012513": 1}),
    "VOICE": ("9193c3cbe60b", {"OT2OD032720": 11, "R01EB030362": 5, "U24EB037545": 4}),
}

#: The reading registered beside the count: awards the dataset paper's
#: funding statement attributes to this research or this work.
FUNDING = {"AI_READI": 3, "CHORUS": 1, "CM4AI": 2, "VOICE": 1}


class TestThePattern(unittest.TestCase):
    def test_the_forms_the_bundles_write(self):
        for written, core in (("1OT2OD032742-01", "OT2OD032742"), ("5U24HG012107", "U24HG012107"),
                              ("UL1TR003096", "UL1TR003096"), ("5U54HG012513-02", "U54HG012513"),
                              ("R01GM083960", "R01GM083960"), ("#1OT2OD032720-01.", "OT2OD032720"),
                              ("OT2 OD032742", "OT2OD032742"), ("U54 CA274502", "U54CA274502"),   # the spaced form (#1161 review, M1)
                              ("P30 DK035816", "P30DK035816"), ("U24-HG006673", "U24HG006673")):
            with self.subTest(written=written):
                self.assertEqual(list(awards.award_numbers(f"grant {written} funded")), [core])

    def test_the_activity_code_is_a_real_shape(self):
        """One letter and two digits, or two letters and one digit (#1161
        review, S5); nothing else — and no identifier that merely looks like
        one."""
        for token in ("AB12CD345678", "XU54HG012513", "S3://bucket/AB12CD345678", "UUID 8F2AB123456",
                      "B35XWX", "doi:10.1038/s41586-025-08878-3", "RRID:AB_2138153", "GSE123456",
                      "NCT01234567", "PMC12037532", "ENSG00000139618", "ot2od032742"):
            with self.subTest(token=token):
                self.assertEqual(list(awards.award_numbers(token)), [])
        for token in ("T32EY007143", "K99AG123456", "DP2HG012345"):
            self.assertEqual(list(awards.award_numbers(token)), [token])

    def test_the_narrow_registered_form_misses_most_of_them(self):
        """Why the hand count was wrong: one letter and two digits, no type
        digit — R01 and P30 match, OT2 and UL1 and a prefixed U24 do not."""
        text = "1OT2OD032742-01 5U24HG012107 UL1TR003096 R01GM083960 P30DK035816"
        self.assertEqual(sorted(awards.NIH_AWARD_NARROW.findall(text)), ["P30DK035816", "R01GM083960"])
        self.assertEqual(len(awards.award_numbers(text)), 5)

    def test_a_mention_carries_its_source_file_and_context(self):
        text = "FILE: paper_row2.txt\nSome prose. Funding: NIH grants OT2OD032644 and P30DK035816.\n"
        ms = awards.award_mentions(text, window=30)
        self.assertEqual([m["award"] for m in ms], ["OT2OD032644", "P30DK035816"])
        self.assertEqual(ms[0]["source"], "FILE: paper_row2.txt")
        self.assertIn("Funding", ms[0]["context"])


class TestTheRecordSide(unittest.TestCase):
    def test_distinct_awards_under_grant_number_at_any_depth(self):
        rec = {"funders": [{"name": "NIH", "grant_number": ["OT2OD032644", "1OT2OD032644-01"]},
                           {"name": "NIH", "grant_number": "P30DK035816"},
                           {"name": "UVA", "grant_number": "Frederick Thomas Fund"}],
               "nested": {"deeper": [{"grant_number": None}]}}
        self.assertEqual(awards.record_award_numbers(rec),
                         ["OT2OD032644", "P30DK035816", "Frederick Thomas Fund"])


class TestTheCorpus(unittest.TestCase):
    def _bundle(self, project):
        path = BUNDLES / f"{project}_preprocessed.txt"
        if not path.exists():
            self.skipTest(f"{path} not in this checkout")
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        # A moved bundle fails, it does not skip (#1161 review, S1): the
        # registered count is pinned to bytes, and a rewrite nobody
        # re-registered would otherwise leave this test green with no
        # coverage — the `bundle_hash_history` guard's discipline.
        self.assertTrue(md5.startswith(REGISTERED[project][0]),
                        f"{project} bundle has moved ({md5[:12]}); re-register the count in REGISTERED and the plan note")
        return path

    def test_the_plan_note_registers_the_same_counts(self):
        """Two places record the mapping; if they disagree, the one a reader
        opens is a coin toss (#1161 review, S4)."""
        import re
        note = (ROOT / "notes" / "generic_v8_analysis_plan.md").read_text(encoding="utf-8")
        row = next(ln for ln in note.splitlines() if "Recounted 2026-09-09 (#1028)" in ln)
        for project, (md5, counts) in REGISTERED.items():
            with self.subTest(project=project):
                m = re.search(rf"{project} \*\*(\d+)\*\* \(({md5[:8]})…\)", row)
                self.assertIsNotNone(m, f"{project} token count and md5 not in the registry row")
                self.assertEqual(int(m.group(1)), len(counts))
        for project, ceiling in FUNDING.items():
            self.assertIsNotNone(re.search(rf"{project} \*\*{ceiling}\*\*", row.split("stated as funding this dataset", 1)[1]),
                                 f"{project} funding ceiling {ceiling} not in the registry row")

    def test_every_registered_bundle_count_reproduces_on_its_bytes(self):
        for project, (_md5, counts) in REGISTERED.items():
            with self.subTest(project=project):
                b = awards.bundle_awards(self._bundle(project))
                self.assertEqual(b["awards"], counts)

    def test_the_v8_fill_populates_the_awards_the_note_reads(self):
        """The reading registered beside the count: the awards that fund this
        dataset — AI_READI 3 (the flagship paper's funding line), CHORUS 1,
        CM4AI 2 (the CM4AI paper's two Bridge2AI awards), VOICE 1 (the
        PhysioNet platform's grants are not the dataset's)."""
        fill = {"VOICE": "2026-09-04f", "CHORUS": "2026-09-04f", "AI_READI": "2026-09-04g", "CM4AI": "2026-09-04g"}
        paths = {(project, rep): (ROOT / "data" / "d4d_concatenated" / "claudecode_api"
                                  / f"{prefix}_claude-opus-5-api-generic-v8_rep{rep}" / f"{project}_d4d.yaml")
                 for project, prefix in fill.items() for rep in (1, 2, 3)}
        if not all(p.exists() for p in paths.values()):
            self.skipTest("the v8 fill is not in this checkout")
        met_funding = met_registered = 0
        for (project, rep), path in paths.items():
            got = [a for a in awards.record_award_numbers(yaml.safe_load(path.read_text(encoding="utf-8")))
                   if awards.NIH_AWARD.fullmatch(a)]
            self.assertGreaterEqual(len(got), 1, f"{project} rep{rep}")                # the registered target
            self.assertTrue(set(got) <= set(REGISTERED[project][1]), f"{project} rep{rep} populates an award the bundle does not state")
            met_funding += len(got) >= FUNDING[project]
            met_registered += len(got) >= len(REGISTERED[project][1])
        self.assertEqual(met_funding, 11)                                               # CM4AI rep3 is the one below
        self.assertEqual(met_registered, 3)                                             # CHORUS only, under every stated token


if __name__ == "__main__":
    unittest.main()
