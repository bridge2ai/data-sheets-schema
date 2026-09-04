"""A resolver URL in a `uriorcurie` slot is written as the CURIE it names (#974).

The rule has been in every arm prompt since v5; the v8 CM4AI re-canary wrote
the dataset's own DOI as `https://doi.org/…` under `id` with 15 fragments
minted on it — 16 resolver URLs against 0 across the v5, v6 and v7 arms.
A rule the model breaks one run in two gets a mechanism, like the enum
aliases and the dates before it: a write-time normaliser, applied wherever
the runner writes a record.
"""

import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

from data_sheets_schema import api_runner
from data_sheets_schema.api_runner import (
    PHASE_INSTRUCTIONS,
    curie_form,
    normalise_identifier_form,
    normalise_record_text,
)
from tests.test_download.test_api_runner import FakeMessages, FakeResponse, spec


class TestTheNormaliser(unittest.TestCase):
    def test_a_resolver_url_in_an_identifier_slot_becomes_the_curie_fragment_included(self):
        out = normalise_identifier_form("id: https://doi.org/10.18130/V3/HIGT4C\n"
                                        "file_collections:\n- id: \"https://doi.org/10.18130/V3/HIGT4C#collection-apms\"\n")
        self.assertIn("id: doi:10.18130/V3/HIGT4C\n", out)
        self.assertIn('- id: "doi:10.18130/V3/HIGT4C#collection-apms"', out)

    def test_orcid_and_ror_follow_the_schemas_prefixes(self):
        out = normalise_identifier_form("creators:\n- id: https://orcid.org/0000-0002-1708-8454\n"
                                        "  affiliation:\n  - id: https://ror.org/0168r3w48\n")
        self.assertIn("- id: ORCID:0000-0002-1708-8454", out)
        self.assertIn("  - id: ROR:0168r3w48", out)

    def test_a_uri_ranged_slot_and_prose_are_untouched(self):
        text = ("download_url: https://doi.org/10.18130/V3/HIGT4C\n"
                "description: see https://doi.org/10.1/x for details\n"
                "access_urls:\n- https://doi.org/10.1/y\n")
        self.assertEqual(normalise_identifier_form(text), text)

    def test_a_curie_and_an_undeclared_host_are_untouched(self):
        text = "id: doi:10.1/x\nsame_as:\n- https://example.org/thing\n"
        self.assertEqual(normalise_identifier_form(text), text)

    def test_items_under_a_multivalued_identifier_slot_are_covered(self):
        from data_sheets_schema.identifiers import uriorcurie_slots
        multi = sorted(s for s in uriorcurie_slots() if s not in ("id",))
        if not multi:
            self.skipTest("no multivalued uriorcurie slot to exercise")
        slot = multi[0]
        out = normalise_identifier_form(f"{slot}:\n- https://doi.org/10.1/a\n- doi:10.1/b\nname: n\n")
        self.assertIn("- doi:10.1/a\n", out)
        self.assertIn("- doi:10.1/b\n", out)

    def test_curie_form_uses_the_longest_declared_base(self):
        from data_sheets_schema.grounding import declared_bases
        bases = tuple(declared_bases())
        self.assertEqual(curie_form("https://doi.org/10.1/x", bases), "doi:10.1/x")
        self.assertIsNone(curie_form("https://doi.org/", bases))
        self.assertIsNone(curie_form("https://nothing.example/x", bases))

    def test_the_record_chain_ends_with_it(self):
        out = normalise_record_text("id: https://doi.org/10.1/x\nkeywords: a\n")
        self.assertEqual(yaml.safe_load(out), {"id": "doi:10.1/x", "keywords": ["a"]})


class _UrlIdFake(FakeMessages):
    def create(self, **kw):
        blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        if PHASE_INSTRUCTIONS["full"] in blob or PHASE_INSTRUCTIONS["reconcile_full"] in blob:
            self.calls.append(kw)
            return FakeResponse("```yaml\n# full\nid: https://doi.org/10.1/x\ntitle: T\nname: n\ndescription: d\n"
                                "keywords: [a]\ndownload_url: https://doi.org/10.1/x\n```")
        return super().create(**kw)


class TestOnTheRunner(unittest.TestCase):
    def test_the_written_full_and_core_carry_the_curie_and_the_grounding_check_sees_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            client = type("C", (), {})(); client.messages = _UrlIdFake()
            keep = api_runner._client; api_runner._client = lambda: client
            try:
                s = spec(out_dir=out)
                with unittest.mock.patch.object(api_runner, "_validator_lines", lambda *a: ([], None)):
                    api_runner.execute(s)
            finally:
                api_runner._client = keep
            full = yaml.safe_load(s.full_path.read_text()); core = yaml.safe_load(s.core_path.read_text())
            self.assertEqual(full["id"], "doi:10.1/x")
            self.assertEqual(core["id"], "doi:10.1/x")
            self.assertEqual(full["download_url"], "https://doi.org/10.1/x")       # `uri`, not `uriorcurie`
            d = yaml.safe_load((out / "CHORUS_provenance.yaml").read_text())
            self.assertEqual([f for f in d["grounding"]["findings"] if f["kind"] == "resolver_url_in_identifier_slot"], [])


if __name__ == "__main__":
    unittest.main()
