"""Values deleted after phase 1, classified against the audit (#2923).

`reconcile_full` is told to remove what a finding identifies as unsupported.
Three v8 reviews found a receipted top-level slot removed with nothing in the
report; read value by value, eight v8 records lost a receipted value that no
finding's path covers (#3078, pinned by the corpus test below). These pin
the three classes on synthetic records — flattened (the text survives),
founded (a finding's path covers the value), unfounded — the identity join
that keeps a reorder or a stripped key from reading as a removal, and the
#899 convention that a run with no snapshot measures nothing rather than 0.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest
import yaml

from data_sheets_schema import removals as rm

RID = "doi:10.1/x"


def _record(**slots):
    return {"id": RID, "title": "A dataset", **slots}


def _receipt(*slots):
    return {"bundle_md5": "m", "chunks": [{"id": "c001", "status": "extracted",
                                           "extracted": [{"slot": s, "snippet": "a quoted passage"} for s in slots]}]}


def _audit(*findings):
    return {"findings": [{"severity": "minor", "record": "full", "issue": "x", **f} for f in findings],
            "summary": f"{len(findings)} findings"}


GOVERNANCE = {"committee_name": "Data Access Committee",
              "accountable_organization": {"name": "University of Example"},
              "stewardship_roles": ["Data steward", "Privacy officer"]}


class Classes(unittest.TestCase):
    def test_a_receipted_slot_that_disappears_with_no_finding_is_unfounded(self):
        """The VOICE 04f rep2 shape: a whole object gone, receipted, and the
        audit named something else."""
        b = rm.classify(_record(data_governance=GOVERNANCE, description="d"), _record(description="d"),
                        _audit({"slot": "description"}), receipt=_receipt("data_governance.committee_name"))
        self.assertEqual((b["removed"], b["flattened"], b["founded"], b["unfounded"]), (4, 0, 0, 4))
        self.assertEqual([r["path"] for r in b["unfounded_paths"]],
                         ["data_governance.committee_name", "data_governance.accountable_organization.name",
                          "data_governance.stewardship_roles[0]", "data_governance.stewardship_roles[1]"])
        self.assertEqual(b["receipted"], {"removed": 1, "flattened": 0, "deleted": 1, "founded": 0, "unfounded": 1})
        self.assertTrue(b["unfounded_paths"][0]["receipted"])

    def test_a_same_slot_finding_makes_it_founded(self):
        b = rm.classify(_record(data_governance=GOVERNANCE), _record(), _audit({"slot": "data_governance"}))
        self.assertEqual((b["founded"], b["unfounded"]), (4, 0))
        self.assertEqual(b["founded_by"], {"slot": 4, "review_paths": 0, "remove_relationship": 0})
        self.assertEqual(b["founded_paths"][0]["finding"], 0)

    def test_a_list_collapsed_to_a_string_with_the_same_text_is_flattened_not_deleted(self):
        before = _record(keywords=["voice biomarkers", "speech"],
                         creators=[{"name": "Ada", "principal_investigator": {"name": "Grace Hopper"}}])
        after = _record(keywords="voice biomarkers; speech",
                        creators=[{"name": "Ada", "principal_investigator": "Grace Hopper (PI)"}])
        b = rm.classify(before, after, _audit(), receipt=_receipt("keywords"))
        self.assertEqual((b["removed"], b["flattened"], b["deleted"], b["unfounded"]), (3, 3, 0, 0))
        self.assertEqual({r["path"]: r["into"] for r in b["flattened_paths"]},
                         {"keywords[0]": "keywords", "keywords[1]": "keywords",
                          "creators[0].principal_investigator.name": "creators[0].principal_investigator"})
        self.assertEqual(b["receipted"]["flattened"], 2)
        self.assertEqual(b["receipted"]["deleted"], 0)

    def test_text_elsewhere_in_the_record_does_not_make_a_deleted_top_level_slot_flattened(self):
        """The root is never the surviving ancestor: `Data Access Committee`
        quoted in the description does not keep `data_governance`."""
        after = _record(description="Requests go to the Data Access Committee.")
        b = rm.classify(_record(data_governance={"committee_name": "Data Access Committee"}), after, _audit())
        self.assertEqual((b["flattened"], b["unfounded"]), (0, 1))

    def test_a_single_scalar_and_a_one_item_list_of_it_are_the_same_value(self):
        b = rm.classify(_record(keywords=["speech"], license="CC-BY"), _record(keywords="speech", license=["CC-BY"]),
                        _audit())
        self.assertEqual(b["removed"], 0)

    def test_a_value_emptied_to_null_is_removed(self):
        b = rm.classify(_record(license="CC-BY"), _record(license=None), _audit())
        self.assertEqual([r["path"] for r in b["unfounded_paths"]], ["license"])


class Identity(unittest.TestCase):
    def test_a_reordered_list_is_not_a_removal(self):
        creators = [{"name": "Ada", "affiliation": "A"}, {"name": "Grace", "affiliation": "B"}]
        b = rm.classify(_record(creators=creators, keywords=["a1", "b2", "c3"]),
                        _record(creators=creators[::-1], keywords=["c3", "a1", "b2"]), _audit())
        self.assertEqual(b["removed"], 0)

    def test_an_entry_whose_minted_key_was_stripped_is_not_a_removal(self):
        """#1053: reconciliation stripped the minted ids from every entry;
        the entries are located at their own index and the ids themselves
        are minted, so outside the classification."""
        before = _record(creators=[{"id": f"{RID}#ada", "name": "Ada"}, {"id": f"{RID}#grace", "name": "Grace"}])
        after = _record(creators=[{"name": "Ada"}, {"name": "Grace"}])
        b = rm.classify(before, after, _audit())
        self.assertEqual(b["removed"], 0)
        self.assertEqual(b["exempt"], 2)

    def test_an_entry_inserted_ahead_does_not_make_the_moved_one_removed(self):
        before = _record(funders=[{"name": "NIH", "grant_id": "OT2"}])
        after = _record(funders=[{"name": "NSF", "grant_id": "X1"}, {"name": "NIH", "grant_id": "OT2"}])
        self.assertEqual(rm.classify(before, after, _audit())["removed"], 0)

    def test_a_dropped_entry_is_removed_even_when_another_entry_now_sits_at_its_index(self):
        before = _record(creators=[{"name": "Ada", "affiliation": "A"}, {"name": "Grace", "affiliation": "B"}])
        after = _record(creators=[{"name": "Grace", "affiliation": "B"}])
        b = rm.classify(before, after, _audit())
        self.assertEqual([r["path"] for r in b["unfounded_paths"]], ["creators[0].name", "creators[0].affiliation"])

    def test_a_resolver_url_member_and_its_curie_are_one_member(self):
        b = rm.classify(_record(related=["https://doi.org/10.5281/zenodo.1"]), _record(related=["doi:10.5281/zenodo.1"]),
                        _audit())
        self.assertEqual(b["removed"], 0)

    def test_a_duplicated_member_removed_once_is_one_removal(self):
        b = rm.classify(_record(tags=["x-ray", "x-ray"]), _record(tags=["x-ray"]), _audit())
        self.assertEqual(b["removed"], 1)


class DroppedEntries(unittest.TestCase):
    """#3076: a value of a list entry the join lost is not flattened by a
    word some sibling happens to carry — the list is not its ancestor."""

    def test_a_word_a_sibling_already_carried_does_not_flatten_a_dropped_entry(self):
        """The review's synthetic record: 'directory' is a word of the
        survivor's description, before and after."""
        survivor = {"name": "Retinal images", "collection_type": "archive", "description": "one directory per site"}
        before = _record(file_collections=[{"name": "ECG waveforms", "collection_type": "directory", "file_count": 12},
                                           survivor])
        b = rm.classify(before, _record(file_collections=[survivor]), _audit(), receipt=_receipt("file_collections[0]"))
        self.assertEqual((b["flattened"], b["unfounded"]), (0, 3))
        self.assertEqual(b["receipted"]["deleted"], 3)

    def test_a_value_every_sibling_shares_does_not_flatten_a_dropped_entry(self):
        """The AI_READI v7 rep2 `file_collections[9]` shape: the entry is in
        no sibling, its conformance standard is in every one."""
        def entry(n):
            return {"name": f"Collection {n}", "conforms_to": "CDS v0.1.1", "conforms_to_standard": ["CDS"]}

        b = rm.classify(_record(file_collections=[entry("a"), entry("b"), {**entry("root"), "name": "Root metadata files"}]),
                        _record(file_collections=[entry("a"), entry("b")]), _audit())
        self.assertEqual(sorted(r["path"] for r in b["unfounded_paths"]),
                         ["file_collections[2].conforms_to", "file_collections[2].conforms_to_standard[0]",
                          "file_collections[2].name"])
        self.assertEqual(b["flattened"], 0)

    def test_an_entry_whose_key_was_rewritten_is_flattened_into_the_sibling_carrying_its_identity(self):
        """The CM4AI v4 rep3 creator: the minted id replaced by the PI's ORCID,
        the PI object flattened to its name. The shared affiliation and role
        survive in that entry, not in the list at large; with the person
        gone they are deleted though the other creator still carries both."""
        krogan = {"id": "urn:x:creator:krogan",
                  "principal_investigator": {"id": "https://orcid.org/0000-0003-4902-337X", "name": "Nevan Krogan"},
                  "affiliations": [{"name": "University of California San Francisco"}], "credit_roles": ["investigation"]}
        other = {"id": "urn:x:creator:obernier", "principal_investigator": {"name": "Kirsten Obernier"},
                 "affiliations": [{"name": "University of California San Francisco"}], "credit_roles": ["investigation"]}
        rewritten = {"id": "ORCID:0000-0003-4902-337X", "principal_investigator": "Nevan Krogan",
                     "affiliations": [{"name": "University of California San Francisco"}], "credit_roles": ["investigation"]}
        before = _record(creators=[krogan, other])
        b = rm.classify(before, _record(creators=[rewritten, other]), _audit())
        self.assertEqual({r["path"]: r["into"] for r in b["flattened_paths"]},
                         {"creators[0].principal_investigator.name": "creators[0]",
                          "creators[0].affiliations[0].name": "creators[0]",
                          "creators[0].credit_roles[0]": "creators[0]"})
        gone = rm.classify(before, _record(creators=[other]), _audit())
        self.assertEqual(gone["flattened"], 0)
        self.assertIn("creators[0].affiliations[0].name", [r["path"] for r in gone["unfounded_paths"]])

    def test_an_entry_with_no_identifying_key_is_folded_where_one_sibling_carries_all_of_it(self):
        """The CHORUS 2026-08-11 leadership team, folded into one entry's
        notes: the shared affiliation survives in the fold, although as many
        entries carry it after as other entries did before."""
        before = _record(creators=[{"principal_investigator": "Eric R", "affiliations": ["MGH"]},
                                   {"principal_investigator": "Azra B", "affiliations": ["UF"]},
                                   {"principal_investigator": "Parisa R", "affiliations": ["UF"]}])
        after = _record(creators=[{"principal_investigator": "Eric R", "affiliations": ["MGH"]},
                                  {"notes": "The leadership team comprises Azra B (UF) and Parisa R (UF)."}])
        b = rm.classify(before, after, _audit())
        self.assertEqual({r["path"]: r["into"] for r in b["flattened_paths"]},
                         {"creators[1].principal_investigator": "creators[1]", "creators[1].affiliations[0]": "creators[1]",
                          "creators[2].principal_investigator": "creators[1]", "creators[2].affiliations[0]": "creators[1]"})
        self.assertEqual(b["deleted"], 0)

    def test_a_value_its_siblings_shared_survives_a_split_as_a_surplus(self):
        """An entry split into one entry per file: more entries carry the
        shared format than its sibling did before, and the surplus is the
        split entry's. Dropped outright, the same value is deleted."""
        tables = {"id": "x#tables", "name": "Tables", "formats": ["zip"]}
        before = _record(file_collections=[{"id": "x#images", "name": "Image archives", "formats": ["zip"]}, tables])
        split = rm.classify(before, _record(file_collections=[{"id": "x#img-a", "name": "img_a", "formats": ["zip"]},
                                                               {"id": "x#img-b", "name": "img_b", "formats": ["zip"]},
                                                               tables]), _audit())
        self.assertEqual({r["path"]: r["into"] for r in split["flattened_paths"]},
                         {"file_collections[0].formats[0]": "file_collections"})
        dropped = rm.classify(before, _record(file_collections=[tables]), _audit())
        self.assertEqual(dropped["flattened"], 0)
        self.assertIn("file_collections[0].formats[0]", [r["path"] for r in dropped["unfounded_paths"]])

    def test_two_siblings_carrying_the_identity_equally_are_no_fold(self):
        """A tie names no continuation: the shared site is then counted, and
        as many entries carry it after as its siblings did before."""
        jr = {"id": "x#1", "name": "Pat Lee Jr", "affiliations": [{"name": "Site A"}]}
        sr = {"id": "x#2", "name": "Pat Lee Sr", "affiliations": [{"name": "Site A"}]}
        before = _record(creators=[{"id": "x#dup", "name": "Pat Lee", "affiliations": [{"name": "Site A"}]}, jr, sr])
        b = rm.classify(before, _record(creators=[jr, sr]), _audit())
        self.assertEqual(b["flattened"], 0)
        self.assertEqual(sorted(r["path"] for r in b["unfounded_paths"]),
                         ["creators[0].affiliations[0].name", "creators[0].id", "creators[0].name"])

    def test_an_entry_with_no_identifying_key_is_no_fold_where_a_sibling_carries_only_part_of_it(self):
        """#3154: a keyless entry's continuation must carry every value it
        had. Parisa's entry folds into the note that names her and her site;
        Azra's shares only 'UF' with that note, so the note is not her
        continuation, and her 'UF' — as many entries carry it after as her
        siblings did before — is deleted, not credited to Parisa's fold."""
        before = _record(creators=[{"principal_investigator": "Eric R", "affiliations": ["MGH"]},
                                   {"principal_investigator": "Azra B", "affiliations": ["UF"]},
                                   {"principal_investigator": "Parisa R", "affiliations": ["UF"]}])
        after = _record(creators=[{"principal_investigator": "Eric R", "affiliations": ["MGH"]},
                                  {"notes": "Parisa R leads the UF site."}])
        b = rm.classify(before, after, _audit())
        self.assertEqual({r["path"]: r["into"] for r in b["flattened_paths"]},
                         {"creators[2].principal_investigator": "creators[1]", "creators[2].affiliations[0]": "creators[1]"})
        self.assertEqual(sorted(r["path"] for r in b["unfounded_paths"]),
                         ["creators[1].affiliations[0]", "creators[1].principal_investigator"])

    def test_the_published_non_check_names_both_routes_a_shared_value_is_flattened_by(self):
        """#3151: the continuation route flattens a value the dropped entry
        shared with that sibling though no more entries carry it after than
        before — the sibling's own copy is credited — and the emitted limit
        statement says so rather than naming the surplus route alone."""
        pat = {"id": "x#1", "name": "Pat Lee", "affiliations": [{"name": "Site A"}]}
        sam = {"id": "x#2", "name": "Sam Roe", "affiliations": [{"name": "Site A"}]}
        b = rm.classify(_record(creators=[pat, sam]), _record(creators=[{**sam, "notes": "With Pat Lee."}]), _audit())
        self.assertEqual({r["path"]: r["into"] for r in b["flattened_paths"]},
                         {"creators[0].name": "creators[0]", "creators[0].affiliations[0].name": "creators[0]"})
        text = next(n for n in b["non_checks"] if n.startswith("that a flattened value"))
        self.assertIn("the sibling recognised as the entry's continuation carries it", text)
        self.assertIn("otherwise only where more final entries carry it", text)
        self.assertNotIn("flattened only where", text)

    def test_a_list_collapsed_to_a_string_is_still_the_surviving_ancestor(self):
        """Only a list that is still a list is set aside."""
        before = _record(file_collections=[{"name": "ECG", "notes": "waveforms"}, {"name": "OCT", "notes": "scans"}])
        b = rm.classify(before, _record(file_collections="ECG waveforms; OCT scans"), _audit())
        self.assertEqual((b["flattened"], b["deleted"]), (4, 0))


class Coverage(unittest.TestCase):
    BEFORE = _record(ethical_reviews=[{"name": "IRB A", "review_details": "approved", "contact": {"name": "Pat"}},
                                      {"name": "IRB B", "review_details": "exempt", "contact": {"name": "Sam"}}],
                     regulatory_restrictions={"confidentiality_level": "restricted", "hipaa_compliant": "yes"},
                     description="d")
    AFTER = _record(ethical_reviews=[{"name": "IRB A"}, {"name": "IRB B"}], description="d")

    def _founded(self, *findings):
        b = rm.classify(self.BEFORE, self.AFTER, _audit(*findings))
        return sorted(r["path"] for r in b["founded_paths"]), b

    def test_a_nested_dotted_indexed_slot_covers_only_that_entry(self):
        founded, _b = self._founded({"slot": "ethical_reviews[1].contact"})
        self.assertEqual(founded, ["ethical_reviews[1].contact.name"])

    def test_a_wildcard_or_an_empty_bracket_or_a_stepped_over_index_covers_every_entry(self):
        for slot in ("ethical_reviews[*].review_details", "ethical_reviews[].review_details",
                     "ethical_reviews.review_details"):
            with self.subTest(slot=slot):
                founded, _b = self._founded({"slot": slot})
                self.assertEqual(founded, ["ethical_reviews[0].review_details", "ethical_reviews[1].review_details"])

    def test_a_json_pointer_in_review_paths_covers_its_descendants(self):
        founded, b = self._founded({"slot": "", "review_paths": ["/ethical_reviews/0/contact"]})
        self.assertEqual(founded, ["ethical_reviews[0].contact.name"])
        self.assertEqual(b["founded_by"]["review_paths"], 1)

    def test_an_ancestor_remove_relationship_covers_descendants(self):
        founded, b = self._founded({"slot": "", "remove_relationship": {"path": "/ethical_reviews/1", "identity": "/name"}})
        self.assertEqual(founded, ["ethical_reviews[1].contact.name", "ethical_reviews[1].review_details"])
        self.assertEqual(b["founded_by"]["remove_relationship"], 2)

    def test_a_multi_slot_finding_covers_each_slot_it_names(self):
        for slot in ("regulatory_restrictions.confidentiality_level / regulatory_restrictions.hipaa_compliant",
                     "regulatory_restrictions.confidentiality_level / hipaa_compliant",
                     "regulatory_restrictions.confidentiality_level, regulatory_restrictions.hipaa_compliant"):
            with self.subTest(slot=slot):
                founded, _b = self._founded({"slot": slot})
                self.assertEqual(founded, ["regulatory_restrictions.confidentiality_level",
                                           "regulatory_restrictions.hipaa_compliant"])

    def test_a_finding_on_an_unrelated_slot_or_the_root_founds_nothing(self):
        for finding in ({"slot": "description"}, {"slot": "(whole record)"}, {"slot": "[3] (core)"},
                        {"slot": "", "review_paths": ["/"]}, {"slot": "regulatory"}):
            with self.subTest(finding=finding):
                founded, b = self._founded(finding)
                self.assertEqual(founded, [])
                self.assertEqual(b["unfounded"], 6)

    def test_a_parenthetical_is_dropped_and_the_named_path_read(self):
        founded, _b = self._founded({"slot": "regulatory_restrictions (the confidentiality entry)"})
        self.assertEqual(len(founded), 2)

    def test_an_entry_named_in_brackets_is_selected_by_its_value(self):
        for slot in ("ethical_reviews[IRB B].review_details", "ethical_reviews[name=IRB B].review_details"):
            with self.subTest(slot=slot):
                founded, _b = self._founded({"slot": slot})
                self.assertEqual(founded, ["ethical_reviews[1].review_details"])

    def test_index_sets_select_their_entries(self):
        founded, _b = self._founded({"slot": "ethical_reviews[0..1].review_details"})
        self.assertEqual(len(founded), 2)

    def test_a_core_only_finding_does_not_found_a_full_record_removal(self):
        b = rm.classify(self.BEFORE, self.AFTER, _audit({"slot": "regulatory_restrictions", "record": "core"}))
        self.assertEqual(b["founded"], 0)
        self.assertEqual(b["unfounded_named_by_core_finding"], 2)
        for record in ("both", "full", None):
            with self.subTest(record=record):
                b = rm.classify(self.BEFORE, self.AFTER, _audit({"slot": "regulatory_restrictions", "record": record}))
                self.assertEqual(b["founded"], 2)

    def test_a_finding_index_one_past_the_end_founds_the_last_entry_and_says_so(self):
        """#3077: 04f v8 rep3 VOICE names `preprocessing_strategies[6]` of a
        six-entry list and means entry 5. As written it names no entry;
        counting from 1 is the only reading under which it names one."""
        for finding, via in (({"slot": "ethical_reviews[2].review_details"}, "slot"),
                             ({"slot": "", "review_paths": ["/ethical_reviews/2/review_details"]}, "review_paths")):
            with self.subTest(finding=finding):
                founded, b = self._founded(finding)
                self.assertEqual(founded, ["ethical_reviews[1].review_details"])
                self.assertEqual(b["founded_paths"][0]["by"], via)
                self.assertTrue(b["founded_paths"][0]["index_past_end"])
                self.assertEqual(b["founded_past_end"], 1)
                self.assertEqual((b["audit"]["paths_past_end"], b["audit"]["paths_one_past_end"]), (1, 1))
                self.assertIn("1 founded by an index one past the end", b["summary"])

    def test_an_index_in_range_or_further_past_the_end_is_read_as_written(self):
        founded, b = self._founded({"slot": "ethical_reviews[3].review_details"})
        self.assertEqual(founded, [])
        self.assertEqual((b["audit"]["paths_past_end"], b["audit"]["paths_one_past_end"], b["founded_past_end"]), (1, 0, 0))
        founded, b = self._founded({"slot": "ethical_reviews[0].review_details"})
        self.assertEqual(founded, ["ethical_reviews[0].review_details"])
        self.assertNotIn("index_past_end", b["founded_paths"][0])
        self.assertEqual((b["audit"]["paths_past_end"], b["founded_past_end"]), (0, 0))

    def test_an_index_into_an_empty_list_is_past_the_end_and_read_as_nothing(self):
        b = rm.classify(_record(tags=[], license="CC-BY"), _record(), _audit({"slot": "tags[0]"}))
        self.assertEqual((b["audit"]["paths_past_end"], b["audit"]["paths_one_past_end"]), (1, 0))
        self.assertEqual((b["founded"], b["unfounded"]), (0, 1))

    def test_an_exact_path_wins_over_a_past_end_reading(self):
        """A value an in-range path covers is not credited to a past-end one."""
        _founded, b = self._founded({"slot": "ethical_reviews[2]"}, {"slot": "ethical_reviews[1].review_details"})
        row = next(r for r in b["founded_paths"] if r["path"] == "ethical_reviews[1].review_details")
        self.assertEqual((row["finding"], row.get("index_past_end")), (1, None))

    def test_past_end_walks_literal_steps_only(self):
        original = {"a": [{"b": [1, 2]}], "c": {"d": []}}
        self.assertEqual(rm.past_end(["a", 1], original), (1, 1))
        self.assertEqual(rm.past_end(["a", 0, "b", 2], original), (2, 2))
        self.assertEqual(rm.past_end(["c", "d", 0], original), (0, 0))
        for fp in (["a", 0, "b", 1], ["a", "*", "b", 5], ["a", "b"], ["x", 3], ["a", frozenset({4})]):
            with self.subTest(fp=fp):
                self.assertIsNone(rm.past_end(fp, original))

    def test_a_mention_in_a_findings_text_is_reported_and_founds_nothing(self):
        b = rm.classify(self.BEFORE, self.AFTER,
                        _audit({"slot": "description", "issue": "see regulatory_restrictions too"}))
        self.assertEqual(b["founded"], 0)
        self.assertEqual(b["unfounded_mentioned_in_finding_text"], 2)


class Exemptions(unittest.TestCase):
    def test_source_caveats_and_class_declarations_are_outside_but_notes_are_not(self):
        before = _record(conforms_to_class="Dataset", source_caveats=["caveat"],
                         content_warnings=[{"content_warnings_present": True, "notes": "graphic imagery"}])
        b = rm.classify(before, _record(), _audit())
        self.assertEqual(b["exempt"], 2)
        self.assertEqual(sorted(r["path"] for r in b["unfounded_paths"]),
                         ["content_warnings[0].content_warnings_present", "content_warnings[0].notes"])

    def test_a_boolean_is_never_flattened(self):
        before = _record(regulatory_restrictions={"hipaa_compliant": True, "summary": "HIPAA applies: true"})
        after = _record(regulatory_restrictions={"summary": "HIPAA applies: true"})
        b = rm.classify(before, after, _audit())
        self.assertEqual((b["flattened"], b["unfounded"]), (0, 1))


class Absent(unittest.TestCase):
    def test_no_snapshot_measures_nothing_rather_than_zero(self):
        b = rm.classify(None, _record(), _audit())
        self.assertFalse(b["checked"])
        for key in ("removed", "flattened", "deleted", "founded", "unfounded", "receipted", "phase"):
            self.assertIsNone(b[key], key)
        self.assertIn("#899", b["reason"])

    def test_no_audit_counts_deletions_but_sorts_none_of_them(self):
        b = rm.classify(_record(data_governance=GOVERNANCE), _record(), None, receipt=_receipt("data_governance"))
        self.assertEqual((b["deleted"], b["founded"], b["unfounded"]), (4, None, None))
        self.assertEqual(len(b["unsorted_paths"]), 4)
        self.assertEqual(b["receipted"], {"removed": 4, "flattened": 0, "deleted": 4, "founded": None, "unfounded": None})
        self.assertIn("no audit", b["summary"])

    def test_an_audit_that_could_not_be_read_is_not_called_absent(self):
        """#3153: an audit that exists but could not be read, or one with no
        findings list, sorts nothing — and the summary says which, never
        that there is no audit."""
        b = rm.classify(_record(data_governance=GOVERNANCE), _record(), None,
                        audit_unread="JSONDecodeError: Expecting value")
        self.assertEqual((b["deleted"], b["founded"], b["unfounded"]), (4, None, None))
        self.assertIn("4 deleted · the audit could not be read (JSONDecodeError: Expecting value)", b["summary"])
        self.assertNotIn("no audit", b["summary"])
        b = rm.classify(_record(data_governance=GOVERNANCE), _record(), {"summary": "no findings key"})
        self.assertIn("the audit carries no findings list", b["summary"])
        self.assertNotIn("no audit", b["summary"])

    def test_no_receipt_leaves_the_receipted_counts_none(self):
        self.assertIsNone(rm.classify(_record(a="x"), _record(), _audit())["receipted"])


class Phase(unittest.TestCase):
    def test_the_phase_is_the_one_after_the_last_output_that_still_carried_it(self):
        before = _record(a="1", b="2", c="3")
        stages = [("reconcile_full", _record(b="2", c="3")), ("repair_full_r1", _record(c="3"))]
        b = rm.classify(before, _record(), _audit(), intermediates=stages)
        self.assertEqual({r["path"]: r["phase"] for r in b["unfounded_paths"]},
                         {"a": "reconcile_full", "b": "repair_full_r1", "c": "write"})
        self.assertEqual(b["phase"], {"reconcile_full": 1, "repair_full_r1": 1, "write": 1})

    def test_a_value_restored_and_lost_again_is_named_by_the_later_loss(self):
        stages = [("reconcile_full", _record()), ("repair_full_r1", _record(a="1"))]
        b = rm.classify(_record(a="1"), _record(), _audit(), intermediates=stages)
        self.assertEqual(b["unfounded_paths"][0]["phase"], "write")

    def test_an_unreadable_phase_output_leaves_every_removal_unattributed(self):
        stages = [("reconcile_full", None), ("repair_full_r1", _record())]
        b = rm.classify(_record(a="1"), _record(), _audit(), intermediates=stages)
        self.assertIsNone(b["phase"])
        self.assertIsNone(b["unfounded_phase"])
        self.assertNotIn("phase", b["unfounded_paths"][0])

    def test_the_unfounded_count_is_split_by_the_phase_that_removed_each_value(self):
        """#3150: a repair round acts on validation errors, not on the
        audit, so the unfounded values it removes are counted apart from
        reconcile_full's. The v4 VOICE rep2 shape: reconcile_full kept the
        PI object, repair_full_r1 collapsed it to its name and dropped the
        constructed id. Founded and flattened values are not in the split."""
        pi = {"id": "https://b2ai-voice.org/person/pat", "name": "Pat Lee"}
        before = _record(creators=[{"name": "Lab", "principal_investigator": pi}], license="CC-BY", a="1")
        reconciled = _record(creators=[{"name": "Lab", "principal_investigator": pi}])
        repaired = _record(creators=[{"name": "Lab", "principal_investigator": "Pat Lee"}])
        stages = [("reconcile_full", reconciled), ("repair_full_r1", repaired)]
        b = rm.classify(before, repaired, _audit({"slot": "license"}), intermediates=stages)
        self.assertEqual({r["path"]: r["phase"] for r in b["unfounded_paths"]},
                         {"creators[0].principal_investigator.id": "repair_full_r1", "a": "reconcile_full"})
        self.assertEqual(b["unfounded_phase"], {"repair_full_r1": 1, "reconcile_full": 1})
        self.assertEqual(b["phase"], {"reconcile_full": 2, "repair_full_r1": 2})
        self.assertEqual(rm.classify(before, repaired, None, intermediates=stages)["unfounded_phase"], None)

    def test_the_split_counts_past_the_listed_paths(self):
        """The split is over every unfounded value, not the capped list."""
        before = _record(**{f"s{i}": str(i) for i in range(rm.PATH_LIMIT + 5)})
        b = rm.classify(before, _record(), _audit(), intermediates=[("reconcile_full", _record())])
        self.assertEqual(b["unfounded_phase"], {"reconcile_full": rm.PATH_LIMIT + 5})
        self.assertEqual(b["unfounded_paths_truncated"], 5)


class SlotGrammar(unittest.TestCase):
    def test_the_observed_slot_forms_parse(self):
        original = {"file_collections": [], "human_subject_research": {}, "instances": []}
        cases = {
            "data_collectors[].role": [["data_collectors", "*", "role"]],
            "instances[2..7,11]": [["instances", frozenset({2, 3, 4, 5, 6, 7, 11})]],
            "file_collections[].file_count / total_bytes": [["file_collections", "*", "file_count"],
                                                           ["file_collections", "*", "total_bytes"]],
            "human_subject_research.irb_approval / regulatory_compliance / special_populations":
                [["human_subject_research", "irb_approval"], ["human_subject_research", "regulatory_compliance"],
                 ["human_subject_research", "special_populations"]],
            "subsets (full) / resources (core) — holdout test set": [["subsets"], ["resources"]],
            "description vs confidential_elements": [["description"], ["confidential_elements"]],
            "`creators[0].name`": [["creators", 0, "name"]],
            "/creators/0/name": [["creators", 0, "name"]],
            "(whole record)": [],
        }
        for slot, want in cases.items():
            with self.subTest(slot=slot):
                self.assertEqual(rm.slot_paths(slot, original), want)


class OnDisk(unittest.TestCase):
    """`for_record` reads the run's files where the runner left them and
    writes nothing."""

    def _run(self, tmp, *, snapshot=True, audit=True):
        base = Path(tmp)
        core_dir = base / "claudecode_api_core" / "L"
        (core_dir / "intermediate").mkdir(parents=True)
        (base / "claudecode_api" / "L").mkdir(parents=True)
        prov = core_dir / "VOICE_provenance.yaml"
        prov.write_text(yaml.safe_dump({"run": {"project": "VOICE", "label": "L"}}))
        original = _record(data_governance=GOVERNANCE, description="d", keywords=["a1", "b2"])
        if snapshot:
            (core_dir / "intermediate" / "VOICE_full.yaml").write_text(yaml.safe_dump(original))
        (core_dir / "intermediate" / "VOICE_reconcile_full.yaml").write_text(
            yaml.safe_dump(_record(description="d", keywords=["a1", "b2"])))
        (core_dir / "intermediate" / "VOICE_repair_full_r1.yaml").write_text(
            yaml.safe_dump(_record(description="d", keywords="a1, b2")))
        if audit:
            (core_dir / "intermediate" / "VOICE_audit.json").write_text(json.dumps(_audit({"slot": "description"})))
        (core_dir / "VOICE_coverage_receipt.yaml").write_text(yaml.safe_dump(_receipt("data_governance.committee_name")))
        (base / "claudecode_api" / "L" / "VOICE_d4d.yaml").write_text(
            yaml.safe_dump(_record(description="d", keywords="a1, b2")))
        return prov

    @staticmethod
    def _tree(tmp):
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(tmp).rglob("*")) if p.is_file()}

    def test_a_run_on_disk_is_classified_with_its_phases_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov = self._run(tmp)
            before = self._tree(tmp)
            b = rm.for_record(prov)
            self.assertEqual(self._tree(tmp), before)
        self.assertEqual((b["unfounded"], b["flattened"]), (4, 2))
        self.assertEqual(b["phase"], {"reconcile_full": 4, "repair_full_r1": 2})
        self.assertEqual(b["receipted"]["deleted"], 1)
        self.assertEqual(b["artifacts"]["audit"]["state"], "usable")
        self.assertEqual(b["artifacts"]["receipt"]["state"], "usable")
        self.assertEqual([p["phase"] for p in b["artifacts"]["phases"]], ["reconcile_full", "repair_full_r1"])

    def test_an_unreadable_receipt_is_named_and_measures_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov = self._run(tmp)
            (prov.parent / "VOICE_coverage_receipt.yaml").write_text("chunks: [unclosed")
            b = rm.for_record(prov)
        self.assertIsNone(b["receipted"])
        self.assertEqual(b["artifacts"]["receipt"]["state"], "unusable")
        self.assertEqual(b["unfounded"], 4)

    def test_a_run_with_no_snapshot_is_not_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = rm.for_record(self._run(tmp, snapshot=False))
        self.assertFalse(b["checked"])
        self.assertIsNone(b["unfounded"])

    def test_a_run_with_no_audit_sorts_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = rm.for_record(self._run(tmp, audit=False))
        self.assertEqual((b["deleted"], b["unfounded"]), (4, None))
        self.assertEqual(b["artifacts"]["audit"]["state"], "absent")

    def test_a_missing_phase_output_is_a_gap_not_a_phase_to_skip(self):
        """#3152: with reconcile_full's output gone, a value it removed is
        not credited to repair_full_r1, which never saw it: the removals are
        unattributed and the missing output is listed."""
        with tempfile.TemporaryDirectory() as tmp:
            prov = self._run(tmp)
            (prov.parent / "intermediate" / "VOICE_reconcile_full.yaml").unlink()
            b = rm.for_record(prov)
        self.assertEqual((b["unfounded"], b["flattened"]), (4, 2))
        self.assertIsNone(b["phase"])
        self.assertIsNone(b["unfounded_phase"])
        self.assertNotIn("phase", b["unfounded_paths"][0])
        self.assertEqual([(p["phase"], p["state"]) for p in b["artifacts"]["phases"]],
                         [("reconcile_full", "absent"), ("repair_full_r1", "usable")])

    def test_an_unreadable_audit_is_reported_as_such_on_disk_and_by_the_cli(self):
        """#3153: the audit is there and cannot be read; neither the
        summary nor a row says the run has no audit."""
        import click.testing
        from data_sheets_schema.cli.review import review as review_cli
        with tempfile.TemporaryDirectory() as tmp:
            prov = self._run(tmp)
            (prov.parent / "intermediate" / "VOICE_audit.json").write_text("{not json")
            b = rm.for_record(prov)
            with mock.patch("data_sheets_schema.cli.review._provenance", lambda m, l, p: prov):
                r = click.testing.CliRunner().invoke(review_cli, ["removals", "--method", "claudecode_api",
                                                                  "--label", "L", "--project", "VOICE"])
        self.assertEqual(b["artifacts"]["audit"]["state"], "unusable")
        self.assertIn("the audit could not be read (JSONDecodeError", b["summary"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertNotIn("no audit", r.output)
        self.assertIn("? deleted, unsorted data_governance.committee_name (reconcile_full, receipted)", r.output)

    def test_the_cli_prints_the_unfounded_values_and_writes_nothing(self):
        import click.testing
        from data_sheets_schema.cli.review import review as review_cli
        with tempfile.TemporaryDirectory() as tmp:
            prov = self._run(tmp)
            before = self._tree(tmp)
            args = ["removals", "--method", "claudecode_api", "--label", "L", "--project", "VOICE"]
            with mock.patch("data_sheets_schema.cli.review._provenance", lambda m, l, p: prov):
                r = click.testing.CliRunner().invoke(review_cli, args + ["--flattened"])
                j = click.testing.CliRunner().invoke(review_cli, args + ["--json"])
            self.assertEqual(self._tree(tmp), before)
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("4 unfounded", r.output)
        self.assertIn("✗ unfounded data_governance.committee_name (reconcile_full, receipted)", r.output)
        self.assertIn("~ keywords[0] → keywords (repair_full_r1)", r.output)
        self.assertIn("unfounded, by the phase that removed them: reconcile_full 4", r.output)
        self.assertEqual(json.loads(j.output)["unfounded"], 4)


class CliPastEnd(unittest.TestCase):
    def test_the_cli_reports_finding_paths_past_the_end(self):
        import click.testing
        from data_sheets_schema.cli.review import review as review_cli
        block = rm.classify(Coverage.BEFORE, Coverage.AFTER,
                            _audit({"slot": "ethical_reviews[2].review_details"}, {"slot": "ethical_reviews[9]"}))
        with mock.patch("data_sheets_schema.cli.review._provenance", lambda *_: Path(__file__)), \
                mock.patch("data_sheets_schema.removals.for_record", return_value=block):
            r = click.testing.CliRunner().invoke(review_cli, ["removals", "--method", "claudecode_api", "--label", "L",
                                                              "--project", "VOICE"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("finding paths indexing past the end of their list: 2 (1 one past, read as the last entry;"
                      " 1 value(s) founded so)", r.output)


# ------------------------------------------------------------ corpus replay
CONCAT = Path(__file__).resolve().parents[1] / "data" / "d4d_concatenated"


def _replay(label, project, method="claudecode_api"):
    prov = CONCAT / f"{method}_core" / label / f"{project}_provenance.yaml"
    if not prov.exists():
        pytest.skip(f"{prov} is not in this checkout")
    return rm.for_record(prov)


@pytest.mark.corpus
@pytest.mark.parametrize("label, project, slot", [
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep2", "VOICE", "data_governance"),
    ("2026-09-04g_claude-opus-5-api-generic-v8_rep3", "AI_READI", "content_warnings"),
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep2", "CHORUS", "regulatory_restrictions"),
])
def test_the_three_named_removals_are_unfounded_and_removed_at_reconcile(label, project, slot, monkeypatch):
    monkeypatch.chdir(CONCAT.parents[1])            # the records attest their evidence by repo-relative path
    b = _replay(label, project)
    rows = [r for r in b["unfounded_paths"] if r["path"].split(".")[0].split("[")[0] == slot]
    assert rows, b["summary"]
    assert {r["phase"] for r in rows} == {"reconcile_full"}
    assert any(r.get("receipted") for r in rows)


@pytest.mark.corpus
def test_the_v9_canary_has_no_unfounded_removal(monkeypatch):
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay("2026-09-12_claude-opus-5-api-generic-v9_rep1", "CHORUS")
    assert b["unfounded"] == 0
    assert b["founded"] >= 14 and b["receipted"]["deleted"] >= 14


@pytest.mark.corpus
def test_an_audit_of_ambiguous_generation_is_named_not_called_absent(monkeypatch):
    """#3153 on the arm record the review named: v4 rep1 VOICE carries
    VOICE_audit.json and VOICE_audit_2.json with no index to say which is
    the run's."""
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay("2026-08-13_claude-opus-5-api-generic-v4_rep1", "VOICE", method="claudecode_agent")
    assert b["artifacts"]["audit"]["state"] == "unusable" and b["unfounded"] is None
    assert "the audit could not be read (portable phase snapshots have ambiguous generation ownership" in b["summary"]
    assert "no audit" not in b["summary"]


@pytest.mark.corpus
def test_the_v4_voice_rep2_unfounded_removals_are_all_the_repair_rounds(monkeypatch):
    """#3150: the 14 unfounded values of v4 VOICE rep2 are constructed ids
    that reconcile_full still carried and repair_full_r1 dropped when it
    collapsed each person object to a name."""
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay("2026-08-13_claude-opus-5-api-generic-v4_rep2", "VOICE", method="claudecode_agent")
    assert (b["unfounded"], b["unfounded_phase"]) == (14, {"repair_full_r1": 14})
    assert {r["path"].rsplit(".", 1)[-1] for r in b["unfounded_paths"]} == {"id"}


@pytest.mark.corpus
def test_an_agentic_record_is_unmeasured_not_zero(monkeypatch):
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay("2026-08-28_claude-opus-5-claudecode-generic-v6_rep1", "CHORUS", method="claudecode_agent")
    assert b["checked"] is False and b["unfounded"] is None


@pytest.mark.corpus
def test_the_v7_root_metadata_entry_is_deleted_and_its_past_end_findings_found_it(monkeypatch):
    """#3076 and #3077 on the record both reviews named: the dropped
    `file_collections[9]` ("Root metadata files") is in no sibling, so its
    'metadata' and CDS values are deleted, not flattened into the list; the
    audit's `file_collections[10].id` / `.file_count` of a ten-entry list
    describe that entry — the first quotes its `#root-metadata` id, the
    second its `file_count: 9`, and no other entry has either (#3155) — and
    found exactly those two leaves."""
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay("2026-09-01_claude-opus-5-api-generic-v7_rep2", "AI_READI", method="claudecode_agent")
    inter = CONCAT / "claudecode_agent_core" / "2026-09-01_claude-opus-5-api-generic-v7_rep2" / "intermediate"
    issues = {f["slot"]: f["issue"] for f in json.loads((inter / "AI_READI_audit.json").read_text())["findings"]}
    snapshot = yaml.safe_load((inter / "AI_READI_full.yaml").read_text())["file_collections"]
    assert "#root-metadata" in issues["file_collections[10].id"]
    assert "#root-metadata" not in issues["file_collections[10].file_count"]
    assert "file_count: 9" in issues["file_collections[10].file_count"]
    assert [i for i, e in enumerate(snapshot) if str(e.get("id")).endswith("#root-metadata")] == [9]
    assert [i for i, e in enumerate(snapshot) if e.get("file_count") == 9] == [9]
    entry = "file_collections[9]."
    assert not [r for r in b["flattened_paths"] if r["path"].startswith(entry)]
    assert {r["path"] for r in b["unfounded_paths"] if r["path"].startswith(entry)} == {
        entry + k for k in ("name", "path", "description", "collection_type", "conforms_to",
                            "conforms_to_standard[0]")}
    assert {r["path"] for r in b["founded_paths"] if r.get("index_past_end")} == {entry + "id", entry + "file_count"}
    assert (b["unfounded"], b["founded_past_end"], b["receipted"]["deleted"]) == (6, 2, 33)


@pytest.mark.corpus
@pytest.mark.parametrize("label, project, path", [
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep1", "VOICE", "preprocessing_strategies[6].preprocessing_details"),
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep3", "VOICE", "preprocessing_strategies[5].preprocessing_details"),
])
def test_a_v8_finding_one_past_the_end_founds_the_last_entry(label, project, path, monkeypatch):
    """#3077: the two v8 VOICE findings that index one past the end of
    `preprocessing_strategies` describe its last entry."""
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay(label, project)
    assert [r["path"] for r in b["founded_paths"] if r.get("index_past_end")] == [path]
    assert path not in {r["path"] for r in b["unfounded_paths"]}


#: Every v8 API record with a receipted value removed that no finding's path
#: covers (#3078): the three whole-slot cases the reviews found and five more.
RECEIPTED_UNFOUNDED_V8 = {
    ("2026-09-04b_claude-opus-5-api-generic-v8_rep1", "CM4AI"),       # canary
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep1", "AI_READI"),    # declared invalid by its own block
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep1", "VOICE"),
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep2", "CHORUS"),      # regulatory_restrictions
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep2", "VOICE"),       # data_governance
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep3", "CHORUS"),
    ("2026-09-04g_claude-opus-5-api-generic-v8_rep2", "AI_READI"),
    ("2026-09-04g_claude-opus-5-api-generic-v8_rep3", "AI_READI"),    # content_warnings
}


@pytest.mark.corpus
def test_the_v8_records_that_lost_a_receipted_value_no_finding_covers(monkeypatch):
    """The module docstring's count: eight v8 records, not the three whole
    slots the reviews found — six of the twelve-record fill."""
    monkeypatch.chdir(CONCAT.parents[1])
    provs = sorted(CONCAT.glob("claudecode_api_core/*-v8_rep*/*_provenance.yaml"))
    if not provs:
        pytest.skip("no v8 API records in this checkout")
    found = {(p.parent.name, p.name.split("_provenance")[0]) for p in provs
             if ((rm.for_record(p)["receipted"] or {}).get("unfounded") or 0) > 0}
    assert found == RECEIPTED_UNFOUNDED_V8
