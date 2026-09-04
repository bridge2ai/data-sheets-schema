"""A `mailto:` written as an identifier becomes a fragment on the record's
own id with the address kept in `email` (#981), and the undeclared-prefix
instrument no longer reads `mailto:` as a minted namespace (#982).

The third CM4AI v8 canary wrote `id: mailto:<address>` on six inlined
contact persons — D1 forces `Person.id` and the model had an email and no
ORCID. The fragment rule asks for a fragment on an identifier the evidence
supplies; the counter's own docstring had judged `mailto:` not a minted
namespace and left it uncounted only while the corpus had none.
"""

import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

from data_sheets_schema import api_runner, grounding
from data_sheets_schema.api_runner import PHASE_INSTRUCTIONS, normalise_mailto_ids, normalise_record_text
from tests.test_download.test_api_runner import FakeMessages, FakeResponse, spec


class TestTheNormaliser(unittest.TestCase):
    def test_a_mailto_id_becomes_a_fragment_and_the_address_moves_to_email(self):
        out = normalise_mailto_ids("id: doi:10.1/x\nethical_reviews:\n  contact_person:\n    id: mailto:jane@ucsd.edu\n    name: Jane\n")
        self.assertEqual(yaml.safe_load(out)["ethical_reviews"]["contact_person"],
                         {"id": "doi:10.1/x#person-jane-at-ucsd-edu", "email": "jane@ucsd.edu", "name": "Jane"})

    def test_list_items_keep_one_email_each_and_fill_an_empty_one(self):
        out = normalise_mailto_ids("id: doi:10.1/x\ndata_governance:\n  committee_members:\n  - id: \"mailto:bob@x.org\"\n"
                                   "    email: bob@x.org\n    name: Bob\n  - id: mailto:c@d.org\n    name: C\n    email:\n"
                                   "  - email:\n    id: mailto:e@f.org\n")
        people = yaml.safe_load(out)["data_governance"]["committee_members"]
        self.assertEqual(people[0], {"id": "doi:10.1/x#person-bob-at-x-org", "email": "bob@x.org", "name": "Bob"})
        self.assertEqual(people[1], {"id": "doi:10.1/x#person-c-at-d-org", "name": "C", "email": "c@d.org"})
        self.assertEqual(people[2], {"email": "e@f.org", "id": "doi:10.1/x#person-e-at-f-org"})
        self.assertEqual(out.count("email:"), 3)

    def test_an_email_before_the_id_is_not_duplicated(self):
        out = normalise_mailto_ids("id: doi:10.1/x\nethical_reviews:\n  contact_person:\n    email: jane@ucsd.edu\n    id: mailto:jane@ucsd.edu\n")
        self.assertEqual(out.count("email:"), 1)
        self.assertIn("#person-jane-at-ucsd-edu", out)

    def test_only_person_ranged_slots_are_touched(self):
        """#985: an Organization has no email slot."""
        text = "id: doi:10.1/x\ncreators:\n- name: Org\n  affiliation:\n  - id: mailto:grants@x.org\n    name: X\n"
        self.assertEqual(normalise_mailto_ids(text), text)

    def test_block_scalar_prose_is_never_touched(self):
        text = "id: doi:10.1/x\ndescription: |\n  id: mailto:inside@x.org\n  more\nname: n\n"
        self.assertEqual(normalise_mailto_ids(text), text)

    def test_an_address_yaml_would_misread_is_quoted(self):
        out = normalise_mailto_ids("id: doi:10.1/x\nethical_reviews:\n  contact_person:\n    id: \"mailto:*ops@x.org\"\n    name: O\n")
        self.assertEqual(yaml.safe_load(out)["ethical_reviews"]["contact_person"]["email"], "*ops@x.org")

    def test_the_slug_carries_local_part_and_domain(self):
        out = normalise_mailto_ids("id: doi:10.1/x\nethical_reviews:\n  contact_person:\n    id: mailto:info@a.org\n"
                                   "data_governance:\n  committee_contact:\n    id: mailto:info@b.org\n")
        self.assertIn("#person-info-at-a-org", out); self.assertIn("#person-info-at-b-org", out)

    def test_the_root_id_and_a_record_without_one_are_untouched(self):
        self.assertEqual(normalise_mailto_ids("id: mailto:root@x.org\nname: n\n"), "id: mailto:root@x.org\nname: n\n")
        text = "name: n\nethical_reviews:\n  contact_person:\n    id: mailto:a@b.org\n"
        self.assertEqual(normalise_mailto_ids(text), text)

    def test_a_root_with_a_fragment_is_left_alone_and_the_skip_logged(self):
        from data_sheets_schema.api_runner import _REWRITE_LOG
        log = []; token = _REWRITE_LOG.set(log)
        try:
            text = "id: https://chorus4ai.org/#dataset\nethical_reviews:\n  contact_person:\n    id: mailto:a@b.org\n"
            self.assertEqual(normalise_mailto_ids(text, phase="full"), text)
        finally:
            _REWRITE_LOG.reset(token)
        self.assertEqual(log[0]["kind"], "mailto_id_skipped")

    def test_the_rewrite_is_logged_and_summarised_apart_from_identifier_form(self):
        from data_sheets_schema.api_runner import _REWRITE_LOG, identifier_rewrite_summary
        log = []; token = _REWRITE_LOG.set(log)
        try:
            normalise_mailto_ids("id: doi:10.1/x\nethical_reviews:\n  contact_person:\n    id: mailto:J.Parker+lab@health.ucsd.edu\n", phase="full")
        finally:
            _REWRITE_LOG.reset(token)
        self.assertEqual(log[0]["to"], "doi:10.1/x#person-j-parker-lab-at-health-ucsd-edu")
        summary = identifier_rewrite_summary(log)
        self.assertEqual(summary["mailto_ids"]["full"]["contact_person"]["occurrences"], 1)
        self.assertEqual(summary["identifier_form"], {})

    def test_it_runs_after_the_identifier_form_so_the_fragment_hangs_off_the_curie(self):
        out = normalise_record_text("id: https://doi.org/10.1/x\nethical_reviews:\n  contact_person:\n    id: mailto:a@b.org\n")
        self.assertIn("id: doi:10.1/x#person-a-at-b-org\n", out)


class TestInstrumentV3(unittest.TestCase):
    def test_mailto_is_not_a_minted_namespace_but_invented_ones_still_are(self):
        rec = {"id": "doi:1", "creators": [{"id": "mailto:a@b"}, {"id": "urn:cm4ai:x"}, {"id": "chorus:1"},
                                           {"id": "ark:12345/abc"}, {"id": "urn:uuid:1"}]}
        self.assertEqual(grounding.undeclared_prefixes(rec, {"id"}), {"urn:cm4ai": 1, "chorus": 1})
        self.assertIn("mailto", grounding.EXCLUDED_SCHEMES)

    def test_the_form_block_names_its_instrument(self):
        with tempfile.TemporaryDirectory() as tmp:
            full = Path(tmp) / "P_d4d.yaml"; core = Path(tmp) / "P_d4d_core.yaml"
            full.write_text("id: doi:1\ncreators:\n- id: mailto:a@b\n"); core.write_text("id: doi:1\n")
            block = grounding.form_facts(full, core)
        self.assertEqual(block["undeclared_prefix_occurrences"], 0)
        self.assertEqual(block["prefix_instrument"], grounding.PREFIX_INSTRUMENT)


class _MailtoFake(FakeMessages):
    def create(self, **kw):
        blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        if PHASE_INSTRUCTIONS["full"] in blob or PHASE_INSTRUCTIONS["reconcile_full"] in blob:
            self.calls.append(kw)
            return FakeResponse("```yaml\n# full\nid: doi:10.1/x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n"
                                "ethical_reviews:\n  contact_person:\n    id: mailto:jane@ucsd.edu\n    name: Jane\n```")
        return super().create(**kw)


class TestOnTheRunner(unittest.TestCase):
    def test_the_written_record_carries_the_fragment_and_the_form_block_reads_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            client = type("C", (), {})(); client.messages = _MailtoFake()
            keep = api_runner._client; api_runner._client = lambda: client
            try:
                s = spec(out_dir=out)
                with unittest.mock.patch.object(api_runner, "_validator_lines", lambda *a: ([], None)):
                    api_runner.execute(s)
            finally:
                api_runner._client = keep
            full = yaml.safe_load(s.full_path.read_text())
            self.assertEqual(full["ethical_reviews"]["contact_person"]["id"], "doi:10.1/x#person-jane-at-ucsd-edu")
            self.assertEqual(full["ethical_reviews"]["contact_person"]["email"], "jane@ucsd.edu")
            d = yaml.safe_load((out / "CHORUS_provenance.yaml").read_text())
            self.assertEqual(d["form"]["undeclared_prefix_occurrences"], 0)
            self.assertGreaterEqual(d["normalisation"]["mailto_ids"]["full"]["contact_person"]["occurrences"], 1)


if __name__ == "__main__":
    unittest.main()
