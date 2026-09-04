"""A resolver URL in a `uriorcurie` slot is written as the CURIE it names (#974).

The rule has been in every arm prompt since v5; the v8 CM4AI re-canary wrote
the dataset's own DOI as `https://doi.org/…` under `id` with 15 fragments
minted on it — 16 resolver URLs against 0 on every 12-record fill since v5.
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
        """`example.org` is a declared base, so the undeclared host must be one the schema does not name."""
        text = "id: doi:10.1/x\npublisher: https://nothing.example/thing\n"
        self.assertEqual(normalise_identifier_form(text), text)

    def test_a_base_without_a_trailing_delimiter_is_not_rewritten(self):
        from data_sheets_schema.grounding import declared_bases
        bare = [b for b, _ in declared_bases() if not b.endswith(("/", "#", "_", ":"))]
        if not bare:
            self.skipTest("every declared base ends in a delimiter")
        # A shorter declared base with a delimiter may still match (`linkml:report/foo`
        # for the `https://w3id.org/linkml/` prefix); what must never appear is a
        # local part that starts with the delimiter the bare base lacked.
        out = normalise_identifier_form(f"id: {bare[0]}/foo\n")
        self.assertNotRegex(out, r"^id: \w+:/")

    def test_items_under_a_multivalued_identifier_slot_are_covered(self):
        """Every current identifier slot is single-valued; the item path is for the next one."""
        from data_sheets_schema.grounding import declared_bases
        with unittest.mock.patch.object(api_runner, "_identifier_form_tables",
                                        lambda: (frozenset({"same_as"}), tuple(declared_bases()))):
            out = normalise_identifier_form("same_as:\n- https://doi.org/10.1/a\n- doi:10.1/b\nname: n\n")
        self.assertIn("- doi:10.1/a\n", out)
        self.assertIn("- doi:10.1/b\n", out)

    def test_block_scalar_prose_is_never_touched(self):
        """#977: a description whose text looks like a key line is prose."""
        text = "description: |\n  id: https://doi.org/10.1/x\n  more\nid: https://doi.org/10.1/y\n"
        out = normalise_identifier_form(text)
        self.assertIn("  id: https://doi.org/10.1/x\n", out)
        self.assertIn("\nid: doi:10.1/y\n", out)

    def test_a_commented_key_closes_the_enclosing_state(self):
        """#977: an empty `id:` followed by `access_urls: # mirrors` must not own the items."""
        text = "distribution_formats:\n- id:\n  access_urls: # mirrors\n  - https://doi.org/10.1/x\n"
        self.assertEqual(normalise_identifier_form(text), text)

    def test_a_sibling_item_is_not_read_as_a_child(self):
        with unittest.mock.patch.object(api_runner, "_identifier_form_tables",
                                        lambda: (frozenset({"data_topic"}), tuple(__import__("data_sheets_schema.grounding", fromlist=["declared_bases"]).declared_bases()))):
            out = normalise_identifier_form("objects:\n- groups:\n  - data_topic:\n    - https://doi.org/10.1/right\n  - https://doi.org/10.1/wrong\n")
        self.assertIn("    - doi:10.1/right\n", out)
        self.assertIn("  - https://doi.org/10.1/wrong\n", out)

    def test_trailing_comments_and_crlf_survive(self):
        out = normalise_identifier_form("id: https://doi.org/10.1/x # source\r\nname: n\r\n")
        self.assertEqual(out, "id: doi:10.1/x # source\r\nname: n\r\n")

    def test_the_path_is_case_sensitive_and_the_host_is_not(self):
        from data_sheets_schema.grounding import declared_bases
        bases = tuple(declared_bases())
        self.assertEqual(curie_form("HTTPS://DOI.ORG/10.1/ABC", bases), "doi:10.1/ABC")
        rai = [(b, p) for b, p in bases if "croissant" in b]
        if len(rai) >= 2:
            lower = next(p for b, p in rai if "/rai/" in b)
            self.assertEqual(curie_form("http://mlcommons.org/croissant/rai/Thing", bases), f"{lower}:Thing")

    def test_a_dash_without_a_space_is_not_a_list_item(self):
        text = "-id: https://doi.org/10.1/x\n"
        self.assertEqual(normalise_identifier_form(text), text)

    def test_rewrites_are_logged_with_their_phase(self):
        from data_sheets_schema.api_runner import _REWRITE_LOG, identifier_rewrite_summary
        log = []; token = _REWRITE_LOG.set(log)
        try:
            normalise_identifier_form("id: https://doi.org/10.1/x\n", phase="full")
            normalise_identifier_form("id: https://doi.org/10.1/x\n", phase="reconcile_full")
        finally:
            _REWRITE_LOG.reset(token)
        summary = identifier_rewrite_summary(log)
        self.assertEqual(summary["occurrences"], 2)
        self.assertEqual(summary["distinct_values"], 1)
        self.assertEqual(summary["identifier_form"]["full"]["id"]["occurrences"], 1)

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
            # #978: the record still says what the model wrote.
            self.assertGreaterEqual(d["normalisation"]["occurrences"], 1)
            self.assertEqual(d["normalisation"]["distinct_values"], 1)
            self.assertIn("full", d["normalisation"]["identifier_form"])


class TestReceiptIdentityAcrossForms(unittest.TestCase):
    def test_an_entry_id_in_either_form_is_the_same_entry(self):
        """#979: a phase-1 snapshot may carry the URL form the model wrote."""
        from data_sheets_schema.receipts import _entry_key
        self.assertEqual(_entry_key({"id": "https://doi.org/10.1/x#files", "name": "n"}),
                         _entry_key({"id": "doi:10.1/x#files", "name": "n"}))


if __name__ == "__main__":
    unittest.main()
