"""Values deleted after phase 1, classified against the audit (#2923).

`reconcile_full` is told to remove what a finding identifies as unsupported.
Three v8 reviews found a receipted top-level slot removed with nothing in the
report; read value by value, eight v8 records carry a receipted value whose
text does not survive and that no finding's path covers (#3078, pinned by the
corpus test below) — some of them reworded or moved rather than lost (#3207,
also pinned below). These pin
the three classes on synthetic records — flattened (the text survives),
founded (a finding's path covers the value), unfounded — the identity join
that keeps a reorder or a stripped key from reading as a removal, and the
#899 convention that a run with no snapshot measures nothing rather than 0.
"""
import hashlib
import importlib.util
import json
import re
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

    def test_a_value_reworded_into_its_entrys_source_caveats_reads_as_deleted_and_the_limit_is_published(self):
        """#3207, the AI_READI 04g rep2 shape: `notes` dropped and its content
        restated, reworded, in the entry's new `source_caveats`. The text test
        is the value's own text, so this is a deletion — unfounded with no
        finding — and the emitted non-checks say the counts still err both
        ways and bound nothing (#3229), with the numeric guard and the
        rewritten class named (#3243)."""
        before = _record(sampling_strategies=[{"is_sample": True, "notes": "The healthsheet answers N/A on sampling."}])
        after = _record(sampling_strategies=[{"is_sample": True, "source_caveats":
                                              "The healthsheet answers \"N/A\" to the sampling question."}])
        b = rm.classify(before, after, _audit(), receipt=_receipt("sampling_strategies[0].notes"))
        self.assertEqual([r["path"] for r in b["unfounded_paths"]], ["sampling_strategies[0].notes"])
        self.assertEqual(b["receipted"]["deleted"], 1)
        text = next(n for n in b["non_checks"] if n.startswith("that a deleted value's content is gone"))
        for phrase in ("reworded", "source_caveats", "split across several list members", "coincidental containment",
                       "though a number no longer is", "bound nothing"):
            self.assertIn(phrase, text)
        self.assertNotIn("upper bound", text)
        rewritten = next(n for n in b["non_checks"] if n.startswith("that a rewritten value lost its content"))
        self.assertIn("never counted in them", rewritten)

    def test_a_single_scalar_and_a_one_item_list_of_it_are_the_same_value(self):
        b = rm.classify(_record(keywords=["speech"], license="CC-BY"), _record(keywords="speech", license=["CC-BY"]),
                        _audit())
        self.assertEqual(b["removed"], 0)

    def test_a_value_emptied_to_null_is_removed(self):
        b = rm.classify(_record(license="CC-BY"), _record(license=None), _audit())
        self.assertEqual([r["path"] for r in b["unfounded_paths"]], ["license"])


class Rewritten(unittest.TestCase):
    """#3243: a carried scalar whose path now holds other text is its own
    class, reported beside the removals and never counted in them."""

    def test_a_scalar_rewritten_in_place_is_reported_rewritten_not_removed(self):
        b = rm.classify(_record(license="CC-BY 4.0", description="Voice recordings of adults."),
                        _record(license="CC-BY 4.0", description="An unrelated sentence."), _audit(),
                        receipt=_receipt("description"))
        self.assertEqual((b["removed"], b["unfounded"]), (0, 0))
        self.assertEqual((b["rewritten"], b["rewritten_unfounded"], b["rewritten_receipted"]), (1, 1, 1))
        self.assertEqual(b["rewritten_paths"], [{"path": "description", "at": "description", "receipted": True,
                                                 "founded": False}])
        self.assertIn("1 rewritten in place (1 without a finding)", b["summary"])

    def test_the_22c_cm4ai_file_count_rewritten_from_2_to_1_is_rewritten(self):
        """The 22c CM4AI rep1 `file_collections[0]` shape: the entry kept its
        place, its file_count went from 2 to 1 when reconcile split it."""
        before = _record(file_collections=[{"id": "x#apms", "name": "APMS", "file_count": "2"}])
        after = _record(file_collections=[{"id": "x#apms", "name": "APMS", "file_count": "1"}])
        b = rm.classify(before, after, _audit())
        self.assertEqual([r["path"] for r in b["rewritten_paths"]], ["file_collections[0].file_count"])

    def test_an_extension_a_normalised_form_or_a_curie_is_not_a_rewrite(self):
        """The old text survives at the path: extended, reformatted to the
        same normalised words, a resolver URL written as its CURIE, or a
        value with no words (the AI_READI v4 `path: /`) left as it was."""
        before = _record(description="Voice recordings.", title="Bridge2AI-Voice",
                         funders=[{"name": "NIH", "id": "https://ror.org/01cwqze88"}], counts=12, path="/")
        after = _record(description="Voice recordings. Collected at five sites.", title="Bridge2AI Voice",
                        funders=[{"name": "NIH", "id": "ROR:01cwqze88"}], counts="12", path="/")
        b = rm.classify(before, after, _audit())
        self.assertEqual((b["rewritten"], b["removed"]), (0, 0), b["rewritten_paths"])
        moved = rm.classify(_record(path="/"), _record(path="-"), _audit())
        self.assertEqual([r["path"] for r in moved["rewritten_paths"]], ["path"])

    def test_a_rewrite_a_finding_covers_is_founded_and_its_phase_is_the_one_that_rewrote_it(self):
        before = _record(license="CC-BY 4.0", description="Old text.", title="A dataset")
        stages = [("reconcile_full", _record(license="CC0", description="Old text.")),
                  ("repair_full_r1", _record(license="CC0", description="New text."))]
        b = rm.classify(before, stages[-1][1], _audit({"slot": "license"}), intermediates=stages)
        rows = {r["path"]: r for r in b["rewritten_paths"]}
        self.assertEqual({p: (r["phase"], r["founded"]) for p, r in rows.items()},
                         {"license": ("reconcile_full", True), "description": ("repair_full_r1", False)})
        self.assertEqual((rows["license"]["by"], rows["license"]["finding"]), ("slot", 0))
        self.assertEqual((b["rewritten"], b["rewritten_unfounded"]), (2, 1))
        self.assertEqual(b["rewritten_unfounded_phase"], {"repair_full_r1": 1})

    def test_with_no_audit_or_no_snapshot_the_rewrites_are_not_sorted(self):
        b = rm.classify(_record(license="CC-BY"), _record(license="CC0"), None)
        self.assertEqual((b["rewritten"], b["rewritten_unfounded"], b["rewritten_receipted"]), (1, None, None))
        self.assertNotIn("founded", b["rewritten_paths"][0])
        self.assertIn("1 rewritten in place", b["summary"])
        none = rm.classify(None, _record(), _audit())
        self.assertEqual((none["rewritten"], none["rewritten_unfounded"], none["rewritten_paths"]), (None, None, []))

    def test_a_member_of_a_list_of_scalars_is_removed_not_rewritten(self):
        b = rm.classify(_record(keywords=["speech", "voice"]), _record(keywords=["speech", "audio"]), _audit())
        self.assertEqual((b["rewritten"], [r["path"] for r in b["unfounded_paths"]]), (0, ["keywords[1]"]))


class Containment(unittest.TestCase):
    """What the flattening test counts as the value's text surviving."""

    def test_a_short_number_is_never_flattened_by_coincidental_containment(self):
        """#3243, the 22c CM4AI `file_count` 3 shape: a dropped key whose
        short value appears by chance in text under its surviving parent
        ("3.8 GB") is deleted, not flattened."""
        before = _record(file_collections=[{"name": "Images", "file_count": 3, "description": "A zip."}])
        after = _record(file_collections=[{"name": "Images", "description": "A zip. Listed as 3.8 GB."}])
        b = rm.classify(before, after, _audit(), receipt=_receipt("file_collections[0].file_count"))
        self.assertEqual(b["flattened"], 0)
        self.assertEqual([r["path"] for r in b["unfounded_paths"]], ["file_collections[0].file_count"])
        self.assertEqual(b["receipted"]["deleted"], 1)

    def test_a_short_number_of_a_dropped_entry_is_not_flattened_into_its_list(self):
        """The same guard on the list route (#3076's `_folded_into`): the
        22c entry was dropped and its '3' is a token of a sibling's size."""
        keep = {"id": "x#a", "name": "Tables", "description": "3.8 GB of tables"}
        before = _record(file_collections=[{"id": "x#b", "name": "Images", "file_count": 3}, keep])
        b = rm.classify(before, _record(file_collections=[keep, {"id": "x#c", "name": "More", "notes": "3 files"}]),
                        _audit())
        self.assertNotIn("file_collections[0].file_count", [r["path"] for r in b["flattened_paths"]])
        self.assertIn("file_collections[0].file_count", [r["path"] for r in b["unfounded_paths"]])

    def test_a_long_number_or_a_date_quoted_in_prose_is_deleted_but_one_carried_whole_is_flattened(self):
        """#3130: a number is carried whole or not at all. The v4 VOICE rep1
        count 32522 survived within its entry only as one per-feature count
        in the entry's `source_caveats` (elsewhere in the record it is also
        quoted in `file_collections[0].description`, outside the entry the
        test is scoped to, #3552), and the CM4AI collection dates only as the award
        period beside "the sources give no start or end date" — v2 read both
        as flattened. The v3 AI_READI release date, carried as itself in
        its list, still is; and a word still flattens by containment."""
        before = _record(instances=[{"name": "Recording features", "counts": 32522}],
                         collection_timeframes=[{"start_date": "2022-09-01", "notes": "enrolment"}],
                         distribution_dates=[{"id": "x#a", "release_dates": ["2024-11-08"]},
                                             {"id": "x#b", "release_dates": ["2025-11-17"]}],
                         keywords=["voice", "speech"])
        after = _record(instances=[{"name": "Recording features",
                                    "source_caveats": "Row counts differ by feature: pitch n 32522, loudness n 31855."}],
                        collection_timeframes=[{"notes": "enrolment; the award period runs from 2022-09-01"}],
                        distribution_dates=[{"id": "x#a", "release_dates": ["2024-11-08", "2025-11-17"]}],
                        keywords="voice and speech")
        b = rm.classify(before, after, _audit())
        self.assertEqual({r["path"] for r in b["flattened_paths"]},
                         {"distribution_dates[1].release_dates[0]", "keywords[0]", "keywords[1]"})
        self.assertEqual({r["path"] for r in b["unfounded_paths"]},
                         {"instances[0].counts", "collection_timeframes[0].start_date", "distribution_dates[1].id"})
        for value, want in ((3, False), ("1,024", False), ("2023", False), (12345, True), ("3 files", True),
                            (True, False), ("", False)):
            with self.subTest(value=value):
                self.assertIs(rm._flattenable(value), want)
        for value, node, want in ((12345, {"a": 12345}, True), (12345, {"a": "12345 sets"}, False),
                                  ("2022-09-01", {"a": "2022-09-01"}, True), ("2022-09-01", ["from 2022-09-01"], False),
                                  ("3 files", {"a": "3 files, 2 GB"}, True)):
            with self.subTest(value=value, node=node):
                self.assertIs(rm._kept_in(value, node), want)

    def test_a_resolver_url_whose_curie_survives_is_flattened_not_deleted(self):
        """#3129, the AI_READI v4 rep1 shape: the single phase-1 creator
        carried its affiliations' ROR URLs and its PI's ORCID URL; the
        final record's consortium entry carries them as CURIEs."""
        before = _record(creators=[{"name": "AI-READI Consortium",
                                    "affiliations": [{"name": "UCSD", "id": "https://ror.org/0168r3w48"}],
                                    "principal_investigator": {"name": "Pat Lee",
                                                               "id": "https://orcid.org/0000-0002-1825-0097"}}])
        after = _record(creators=[{"name": "AI-READI Consortium",
                                   "affiliations": "UCSD (ROR:0168r3w48)",
                                   "principal_investigator": "Pat Lee, ORCID:0000-0002-1825-0097"}])
        b = rm.classify(before, after, _audit())
        self.assertEqual({r["path"]: r["into"] for r in b["flattened_paths"]},
                         {"creators[0].affiliations[0].name": "creators[0].affiliations",
                          "creators[0].affiliations[0].id": "creators[0].affiliations",
                          "creators[0].principal_investigator.name": "creators[0].principal_investigator",
                          "creators[0].principal_investigator.id": "creators[0].principal_investigator"})
        self.assertEqual(b["deleted"], 0)

    def test_a_resolver_url_whose_curie_survives_in_a_dropped_entrys_continuation_is_flattened(self):
        """#3129 on the list route: the dropped entry's continuation is found
        by its ORCID, and the ROR URL survives there as a CURIE."""
        pi = {"id": "https://orcid.org/0000-0002-1825-0097", "name": "Pat Lee",
              "affiliations": [{"id": "https://ror.org/0168r3w48"}]}
        before = _record(creators=[{"id": "x#c1", "principal_investigator": pi}, {"id": "x#c2", "name": "Sam"}])
        after = _record(creators=[{"id": "ORCID:0000-0002-1825-0097", "name": "Pat Lee",
                                   "affiliations": [{"id": "ROR:0168r3w48"}]}, {"id": "x#c2", "name": "Sam"}])
        b = rm.classify(before, after, _audit())
        self.assertEqual({r["path"]: r["into"] for r in b["flattened_paths"]}.get(
            "creators[0].principal_investigator.affiliations[0].id"), "creators[0]")
        self.assertNotIn("creators[0].principal_investigator.affiliations[0].id",
                         [r["path"] for r in b["unfounded_paths"]])

    def test_a_url_quoted_inside_prose_still_matches_as_written(self):
        """Canonicalising adds a form; it never drops the written one."""
        before = _record(ethical_reviews=[{"name": "IRB", "contact": {"page": "https://ror.org/0168r3w48"}}])
        after = _record(ethical_reviews=[{"name": "IRB", "contact": "see https://ror.org/0168r3w48 for the board"}])
        b = rm.classify(before, after, _audit())
        self.assertEqual([r["path"] for r in b["flattened_paths"]], ["ethical_reviews[0].contact.page"])


    def test_a_sibling_carrying_the_curie_counts_before_so_the_list_route_can_narrow(self):
        """#3383: the list-level surplus compares two counts `_survives`
        widens alike. A dropped sibling carried the ROR as a CURIE, so the
        one surviving URL is no surplus: v1 read it flattened into
        `creators`, v2 reads it deleted."""
        before = _record(creators=[{"id": "x#a", "name": "Ann", "affiliations": [{"id": "https://ror.org/0168r3w48"}]},
                                   {"id": "x#b", "name": "Bob", "affiliations": [{"id": "ROR:0168r3w48"}]}])
        after = _record(creators=[{"id": "x#c", "name": "Cat", "affiliations": [{"id": "https://ror.org/0168r3w48"}]}])
        b = rm.classify(before, after, _audit())
        self.assertNotIn("creators[0].affiliations[0].id", [r["path"] for r in b["flattened_paths"]])
        self.assertIn("creators[0].affiliations[0].id", [r["path"] for r in b["unfounded_paths"]])

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
        gone they are deleted though the other creator still carries both.
        The PI's ORCID URL survives as the entry's CURIE id (#3129)."""
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
                          "creators[0].principal_investigator.id": "creators[0]",
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

    def test_the_cli_lists_the_rewritten_values_on_request(self):
        """#3243: counted in the summary, listed under --rewritten."""
        import click.testing
        from data_sheets_schema.cli.review import review as review_cli
        block = rm.classify(_record(license="CC-BY", description="old words"),
                            _record(license="CC0", description="new text"), _audit({"slot": "license"}))
        args = ["removals", "--method", "claudecode_api", "--label", "L", "--project", "VOICE"]
        with mock.patch("data_sheets_schema.cli.review._provenance", lambda *_: Path(__file__)), \
                mock.patch("data_sheets_schema.removals.for_record", return_value=block):
            plain = click.testing.CliRunner().invoke(review_cli, args)
            listed = click.testing.CliRunner().invoke(review_cli, args + ["--rewritten"])
        self.assertEqual((plain.exit_code, listed.exit_code), (0, 0), plain.output + listed.output)
        self.assertIn("2 rewritten in place (1 without a finding)", plain.output)
        self.assertNotIn("≠", plain.output)
        self.assertIn("≠ founded license → license (phase unattributed)", listed.output)
        self.assertIn("≠ unfounded description → description (phase unattributed)", listed.output)


class Spelling(unittest.TestCase):
    """#3038: a British spelling and the American form the #1002 normaliser
    writes are one text, so a member or a scalar respelled at write time is
    neither removed nor rewritten."""

    def test_a_member_respelled_at_write_time_is_carried_not_removed(self):
        """The 22c AI_READI rep2 shape: its one `restrictions` member said
        'licence' at phase 1 and 'license' in the written record."""
        before = _record(external_resources=[{"name": "Zenodo", "restrictions": ["Open access under CC BY-NC 4.0 licence."]}])
        after = _record(external_resources=[{"name": "Zenodo", "restrictions": ["Open access under CC BY-NC 4.0 license."]}])
        b = rm.classify(before, after, _audit())
        self.assertEqual((b["removed"], b["rewritten"]), (0, 0))

    def test_a_scalar_respelled_in_place_is_not_rewritten(self):
        b = rm.classify(_record(description="Versions are not updated to correct labelling errors."),
                        _record(description="Versions are not updated to correct labeling errors."), _audit())
        self.assertEqual((b["removed"], b["rewritten"]), (0, 0))

    def test_an_identifier_keeps_its_spelling_and_a_reworded_member_is_still_removed(self):
        self.assertIn("programme", rm._member("https://example.org/programme/"))
        self.assertEqual(rm._member("The Organisation Centre"), rm._member("the organization center"))
        b = rm.classify(_record(keywords=["voice biomarkers", "speech"]),
                        _record(keywords=["vocal biomarkers", "speech"]), _audit())
        self.assertEqual([r["path"] for r in b["unfounded_paths"]], ["keywords[0]"])


class Relocation(unittest.TestCase):
    """#3223: where a deleted value's words went, reported beside the classes
    and never moving one."""

    NOTE = "The healthsheet answers N/A to the sampling strategy question for this release."

    def test_a_value_reworded_into_its_entrys_source_caveats_has_a_candidate_marked_a_change_of_standing(self):
        """The AI_READI 04g rep2 shape (#3207): still unfounded and deleted,
        and the candidate names the caveat."""
        before = _record(sampling_strategies=[{"is_sample": True, "notes": self.NOTE}])
        after = _record(sampling_strategies=[{"is_sample": True, "source_caveats":
                                              "For the sampling strategy question the healthsheet answers N/A."}])
        b = rm.classify(before, after, _audit())
        self.assertEqual((b["deleted"], b["unfounded"]), (1, 1))
        self.assertEqual(b["unfounded_paths"][0]["relocated_candidate"],
                         {"to": "sampling_strategies[0].source_caveats", "share": 0.833, "change_of_standing": True})
        self.assertEqual((b["relocated_candidate"], b["relocated_candidate_unfounded"],
                          b["relocated_candidate_standing"]), (1, 1, 1))
        self.assertIn("1 deleted with a relocation candidate (1 into source_caveats)", b["summary"])

    def test_a_member_split_across_several_members_is_found_in_the_list_taken_whole(self):
        """The VOICE 04f rep1 `special_protections[0]` shape: one member
        split and reworded into two, neither of which carries its share."""
        before = _record(at_risk_populations={"special_protections": [
            "Participants with mood disorders, depression and anxiety receive additional safeguards.", "Minors excluded."]})
        after = _record(at_risk_populations={"special_protections": [
            "Minors excluded.", "Additional safeguards apply to participants", "with mood disorders, depression and anxiety."]})
        b = rm.classify(before, after, _audit())
        row = b["unfounded_paths"][0]
        self.assertEqual(row["path"], "at_risk_populations.special_protections[0]")
        self.assertEqual(row["relocated_candidate"]["to"], "at_risk_populations.special_protections")
        self.assertFalse(row["relocated_candidate"]["change_of_standing"])

    def test_an_identifier_is_found_by_its_own_text_elsewhere_and_a_near_miss_is_not(self):
        """A fragment id on the landing page is not the page, though ten of
        its twelve content words are the page's (the CM4AI v8 creator ids)."""
        pi = "https://orcid.org/0000-0002-1825-0097"
        page = "https://dataverse.example.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C"
        before = _record(creators=[{"name": "Consortium", "principal_investigator": {"name": "Pat Lee", "id": pi}}],
                         contact={"email": "mailto:dac@example.org"}, publisher={"id": page + "#creator-khaliq-h"})
        after = _record(creators=[{"name": "Consortium"}], maintainers=[{"id": "ORCID:0000-0002-1825-0097"}],
                        notes="Requests go to dac@example.org.", page=page)
        b = rm.classify(before, after, _audit())
        where = {r["path"]: r.get("relocated_candidate") for r in b["unfounded_paths"]}
        self.assertEqual(where["creators[0].principal_investigator.id"]["to"], "maintainers[0].id")
        self.assertEqual(where["contact.email"]["to"], "notes")
        self.assertIsNone(where["publisher.id"])                   # the page is not the fragment

    def test_a_short_value_is_not_assessed_and_a_low_share_has_no_candidate(self):
        before = _record(license="CC-BY", description="Collected at three sites over two years by trained staff.")
        after = _record(notes="Staff were trained.")
        b = rm.classify(before, after, _audit())
        self.assertEqual((b["unfounded"], b["relocated_candidate"], b["relocated_not_assessed"]), (2, 0, 1))

    def test_a_short_identifier_is_assessed_and_the_non_check_says_so(self):
        """#3553: an identifier-shaped value is assessed by its own text
        whatever its word count, and the non-check says it."""
        value = "ROR:05gq02987"
        self.assertLess(len(rm._words(value)), rm.RELOCATED_MIN_WORDS)
        assessed, where = rm._Relocation(_record(notes="Hosted by ror:05gq02987.")).candidate(value)
        self.assertTrue(assessed)
        self.assertEqual(where["to"], "notes")
        b = rm.classify(_record(license="CC-BY"), _record(), _audit())
        text = next(n for n in b["non_checks"] if n.startswith("that a relocation candidate restates the value"))
        self.assertIn("is not assessed unless it is identifier-shaped", text)

    def test_an_identifier_quoted_in_prose_is_found_as_survives_finds_it(self):
        """#3585: the needle as written and as `_member` reads it, against
        each scalar read both ways, as `_survives` does — a resolver URL
        quoted verbatim in prose (the orcid.org URLs moved into
        `creators[i].notes`) is found; a CURIE is found in prose that quotes
        it and in a scalar that is its URL, and not in prose quoting its
        URL, which `_survives` does not find either."""
        url, curie = "https://orcid.org/0000-0002-1825-0097", "ORCID:0000-0002-1825-0097"
        hays = {"url in prose": f"PI ORCID {url}.", "curie in prose": f"PI ORCID {curie}.",
                "url alone": url, "curie alone": curie}
        found = {(v, k): rm._Relocation(_record(notes=h)).candidate(v) for v in (url, curie) for k, h in hays.items()}
        for (v, k), (assessed, where) in found.items():
            self.assertTrue(assessed, (v, k))
            self.assertEqual(where is not None, rm._survives(v, hays[k]), (v, k))
        self.assertEqual({key for key, (_a, where) in found.items() if where is None}, {(curie, "url in prose")})
        # Token boundaries still hold: a longer ORCID is not this one.
        self.assertEqual(rm._Relocation(_record(notes=f"PI ORCID {url}1.")).candidate(url), (True, None))
        # Through classify: a creator's ORCID URL deleted, quoted in another
        # entry's notes (outside the entry, so deleted rather than flattened).
        before = _record(creators=[{"name": "Pat Lee", "id": url}, {"name": "Consortium"}])
        after = _record(creators=[{"name": "Pat Lee"}, {"name": "Consortium", "notes": f"PI ORCID {url}."}])
        b = rm.classify(before, after, _audit())
        row = next(r for r in b["unfounded_paths"] if r["path"] == "creators[0].id")
        self.assertEqual(row["relocated_candidate"]["to"], "creators[1].notes")

    def test_an_identifier_is_not_found_as_the_prefix_of_a_longer_identifier(self):
        """#3603: normalisation makes `/`, `#`, `-` and `.` token boundaries,
        so containment found a site root inside a deeper page URL and `#pi`
        inside `#pi-record`. A match must now end where an identifier
        ends; where it ends a sentence, sits in brackets or is a CURIE
        written with a space in prose (the 22b/22c AI_READI "(ROR
        00cvxb145)") it is still found."""
        root, pi = "https://chorus4ai.org/", "https://reporter.nih.gov/project-details/10472824#pi"
        for hay in ("Files at https://chorus4ai.org/data/v2 are listed.", "https://chorus4ai.org/#dataset"):
            self.assertEqual(rm._Relocation(_record(notes=hay)).candidate(root), (True, None), hay)
        self.assertEqual(rm._Relocation(_record(notes=pi + "-record")).candidate(pi), (True, None))
        for hay in ("Home: https://chorus4ai.org.", "(see https://chorus4ai.org/)", root.rstrip("/"),
                    "Mirrors: https://mirror.example.org/,https://chorus4ai.org/"):
            self.assertEqual(rm._Relocation(_record(notes=hay)).candidate(root)[1]["to"], "notes", hay)
        self.assertEqual(rm._Relocation(_record(notes=f"PI record <{pi}>; see the award.")).candidate(pi)[1]["to"],
                         "notes")
        self.assertEqual(rm._Relocation(_record(notes="Washington (ROR 00cvxb145, itself listed)")).candidate(
            "ROR:00cvxb145")[1]["to"], "notes")
        self.assertEqual(rm._Relocation(_record(notes="Washington (ROR 00cvxb145x)")).candidate("ROR:00cvxb145"),
                         (True, None))
        # And it starts where an identifier starts: another scheme ending
        # in the same letters is not this one.
        self.assertEqual(rm._Relocation(_record(notes="See MIRROR:00cvxb145.")).candidate("ROR:00cvxb145"),
                         (True, None))
        # A `mailto:` scheme is set aside on the carrying side too.
        self.assertEqual(rm._Relocation(_record(notes="Write to mailto:dac@example.org.")).candidate(
            "mailto:dac@example.org")[1]["to"], "notes")
        # Through classify: the 2026-08-13 shape, a PI id deleted where a
        # sibling's id extends it.
        before = _record(creators=[{"name": "Consortium", "principal_investigator": {"name": "Pat Lee", "id": pi}},
                                   {"name": "Pat Lee", "id": pi + "-record"}])
        after = _record(creators=[{"name": "Consortium"}, {"name": "Pat Lee", "id": pi + "-record"}])
        b = rm.classify(before, after, _audit())
        row = next(r for r in b["unfounded_paths"] if r["path"] == "creators[0].principal_investigator.id")
        self.assertNotIn("relocated_candidate", row)
        self.assertEqual(b["relocated_candidate"], 0)
        text = next(n for n in b["non_checks"] if n.startswith("that a relocation candidate restates the value"))
        self.assertIn("never as the prefix or the tail of a longer one", text)
        self.assertIn("those figures are over both routes", text)
        self.assertNotIn("not measured", text)

    def test_an_identifier_is_not_found_as_the_tail_of_a_longer_identifier(self):
        """#3618: the start mirrors `_IDENTIFIER_END`. A needle that begins
        after a character continuing an identifier (`.`, `-`, `/`, `:`, `@`
        and the rest) is the tail of a longer, different one — another
        person's address, a path inside a deeper URL. Where it begins the
        text, follows a space or bracket, or follows the `mailto:` scheme
        set aside on both sides, it is still found."""
        mail = "mailto:smith@lab.edu"
        for hay in ("Write to j.smith@lab.edu for access", "Write to jo-smith@lab.edu.",
                    "Write to mailto:j.smith@lab.edu.", "id=smith@lab.edu", "a/smith@lab.edu"):
            self.assertEqual(rm._Relocation(_record(contact=hay)).candidate(mail), (True, None), hay)
        for hay in ("Write to smith@lab.edu for access", "smith@lab.edu", "(smith@lab.edu)",
                    "Write to mailto:smith@lab.edu.", "Write to MAILTO:Smith@Lab.edu."):
            self.assertEqual(rm._Relocation(_record(contact=hay)).candidate(mail)[1]["to"], "contact", hay)
        # A URL quoted as a query value or after a proxy prefix is a
        # different identifier; a CURIE's scheme must not be the tail of a
        # longer one either.
        root = "https://chorus4ai.org/"
        for hay in ("https://proxy.example.org/?u=https://chorus4ai.org/", "see x.https://chorus4ai.org/"):
            self.assertEqual(rm._Relocation(_record(notes=hay)).candidate(root), (True, None), hay)
        self.assertEqual(rm._Relocation(_record(notes="See lab.ror:00cvxb145 here.")).candidate("ROR:00cvxb145"),
                         (True, None))
        self.assertEqual(rm._Relocation(_record(notes="Washington (ROR 00cvxb145, itself listed)")).candidate(
            "ROR:00cvxb145")[1]["to"], "notes")
        # Through classify: a contact's address deleted where another
        # person's address ends in the same letters.
        before = _record(contacts=[{"name": "Sam Smith", "email": mail}], contact="Write to j.smith@lab.edu.")
        after = _record(contacts=[{"name": "Sam Smith"}], contact="Write to j.smith@lab.edu.")
        b = rm.classify(before, after, _audit())
        row = next(r for r in b["unfounded_paths"] if r["path"] == "contacts[0].email")
        self.assertNotIn("relocated_candidate", row)
        text = next(n for n in b["non_checks"] if n.startswith("that a relocation candidate restates the value"))
        self.assertIn("starts and ends an identifier", text)

    def test_a_mailto_scheme_counts_only_where_it_starts_an_identifier(self):
        """#3623: the `mailto:` set aside on the carrying side is held to the
        same start. Inside a proxy URL's query, after a path or a hyphen, it
        is part of a longer identifier, as an `https://` URL is there."""
        mail = "mailto:smith@lab.edu"
        for hay in ("https://proxy.example.org/?u=mailto:smith@lab.edu", "x-mailto:smith@lab.edu",
                    "see a/mailto:smith@lab.edu", "id=MAILTO:smith@lab.edu", "lab.mailto:smith@lab.edu"):
            self.assertEqual(rm._Relocation(_record(contact=hay)).candidate(mail), (True, None), hay)
        for hay in ("mailto:smith@lab.edu", "Write to mailto:smith@lab.edu.", "(mailto:smith@lab.edu)",
                    "<MAILTO:smith@lab.edu>"):
            self.assertEqual(rm._Relocation(_record(contact=hay)).candidate(mail)[1]["to"], "contact", hay)
        # Through classify: the proxy case the review reproduced.
        before = _record(contacts=[{"name": "Sam Smith", "email": mail}],
                         page="https://proxy.example.org/?u=mailto:smith@lab.edu")
        after = _record(contacts=[{"name": "Sam Smith"}], page="https://proxy.example.org/?u=mailto:smith@lab.edu")
        b = rm.classify(before, after, _audit())
        row = next(r for r in b["unfounded_paths"] if r["path"] == "contacts[0].email")
        self.assertNotIn("relocated_candidate", row)
        self.assertEqual(b["relocated_candidate_unfounded"], 0)

    def test_a_candidate_moves_no_class_count(self):
        before = _record(sampling_strategies=[{"is_sample": True, "notes": self.NOTE}])
        after = _record(sampling_strategies=[{"is_sample": True}], source_caveats=self.NOTE.replace("N/A", "n/a"))
        with mock.patch.object(rm, "RELOCATED_THRESHOLD", 1.01):
            none = rm.classify(before, after, _audit())
        some = rm.classify(before, after, _audit())
        self.assertEqual((none["relocated_candidate"], some["relocated_candidate"]), (0, 1))
        for key in ("removed", "flattened", "deleted", "founded", "unfounded", "rewritten"):
            self.assertEqual(none[key], some[key], key)

    def test_a_value_flattened_only_into_source_caveats_keeps_its_class_and_is_marked(self):
        """The 2026-08-20 v5 AI_READI `confidentiality_level` shape: the enum
        value's text survives only in the caveat saying the slot is omitted."""
        before = _record(regulatory_restrictions={"confidentiality_level": "restricted", "notes": "x"})
        after = _record(regulatory_restrictions={"notes": "x", "source_caveats":
                                                 "The slot is omitted: the source value does not map onto restricted."})
        b = rm.classify(before, after, _audit())
        self.assertEqual((b["flattened"], b["flattened_into_source_caveats"]), (1, 1))
        self.assertTrue(b["flattened_paths"][0]["into_source_caveats"])
        kept = rm.classify(before, _record(regulatory_restrictions={"notes": "x; restricted access"}), _audit())
        self.assertEqual((kept["flattened"], kept["flattened_into_source_caveats"]), (1, 0))
        # "Only" (#3550): text a claim still carries is not marked, even
        # where a caveat beside the claim carries it too.
        both = rm.classify(before, _record(regulatory_restrictions={
            "notes": "x; restricted access", "source_caveats": "The source says the data are restricted."}), _audit())
        self.assertEqual((both["flattened"], both["flattened_into_source_caveats"]), (1, 0))
        self.assertNotIn("into_source_caveats", both["flattened_paths"][0])


def _review(original, judgments, sha=None):
    """An original_full source review: {path: 'supported'|'revise'|'metadata'}."""
    rows = []
    for pointer, j in judgments.items():
        if j == "metadata":
            rows.append({"path": pointer, "metadata_reason": "record metadata"})
        else:
            rows.append({"path": pointer, "claims": [{"text": "t", "verdict": j}]})
    return {"artifact": "original_full", "sha256": sha, "values": rows}


class SourceReview(unittest.TestCase):
    """#3037: a bound source review's judgment on each deleted value, and a
    value reviewed supported founded only by a finding linked to it."""

    BEFORE = _record(license="CC-BY", keywords=["voice", "speech"], description="d")
    AFTER = _record(description="d")
    JUDGED = {"/license": "supported", "/keywords/0": "revise", "/keywords/1": "supported", "/id": "metadata"}

    def _audit(self, *findings, sha=None):
        a = _audit(*findings)
        a["source_review"] = _review(self.BEFORE, self.JUDGED, sha)
        return a

    def test_a_supported_value_a_free_text_slot_names_is_unfounded_and_a_revise_one_is_founded(self):
        b = rm.classify(self.BEFORE, self.AFTER, self._audit({"slot": "license"}, {"slot": "keywords"}))
        rows = {r["path"]: r for r in b["founded_paths"] + b["unfounded_paths"]}
        self.assertEqual({p for p in rows if p in {r["path"] for r in b["unfounded_paths"]}}, {"license", "keywords[1]"})
        self.assertTrue(rows["license"]["supported_slot_only"])
        self.assertEqual(rows["keywords[0]"]["source_review"], "revise")
        self.assertEqual(b["source_review"]["deleted"], {"supported": 2, "revise": 1, "metadata": 0, "unreviewed": 0})
        self.assertEqual((b["source_review"]["unfounded_supported"], b["source_review"]["unfounded_supported_slot_only"]),
                         (2, 2))
        self.assertEqual(b["source_review"]["state"], "unhashed")

    def test_a_linked_finding_founds_a_supported_value(self):
        b = rm.classify(self.BEFORE, self.AFTER, self._audit(
            {"slot": "license", "remove_relationship": {"path": "/license"}},
            {"slot": "keywords", "review_paths": ["/keywords/1"]}))
        self.assertEqual({r["path"]: r["by"] for r in b["founded_paths"]},
                         {"license": "remove_relationship", "keywords[0]": "slot", "keywords[1]": "review_paths"})

    def test_a_value_exempted_as_metadata_is_judged_metadata_when_deleted_or_rewritten(self):
        """#3587: a row the review exempted as record metadata reads
        `metadata`, not `unreviewed`, on deleted and rewritten rows."""
        before = _record(publisher="Example University", version="1.0", license="CC-BY")
        after = _record(version="2.0")
        audit = _audit()
        audit["source_review"] = _review(before, {"/publisher": "metadata", "/version": "metadata",
                                                  "/license": "supported"})
        b = rm.classify(before, after, audit)
        judged = {r["path"]: r["source_review"] for r in b["unfounded_paths"] + b["rewritten_paths"]}
        self.assertEqual(judged, {"publisher": "metadata", "version": "metadata", "license": "supported"})
        self.assertEqual(b["source_review"]["deleted"], {"supported": 1, "revise": 0, "metadata": 1, "unreviewed": 0})
        self.assertEqual(b["source_review"]["rewritten"], {"supported": 0, "revise": 0, "metadata": 1, "unreviewed": 0})

    def test_unfounded_supported_counts_only_the_unfounded_supported_values(self):
        """#3587: a supported value a linked finding founds is not counted
        in `unfounded_supported`; one a free-text slot alone names is."""
        b = rm.classify(self.BEFORE, self.AFTER, self._audit(
            {"slot": "license", "remove_relationship": {"path": "/license"}}, {"slot": "keywords"}))
        self.assertEqual(b["source_review"]["deleted"]["supported"], 2)
        self.assertEqual({r["path"] for r in b["unfounded_paths"]}, {"keywords[1]"})
        self.assertEqual((b["source_review"]["unfounded_supported"],
                          b["source_review"]["unfounded_supported_slot_only"]), (1, 1))

    def test_a_review_bound_to_other_bytes_is_not_read_and_says_so(self):
        b = rm.classify(self.BEFORE, self.AFTER, self._audit({"slot": "license"}, sha="a" * 64),
                        snapshot_sha256="b" * 64)
        self.assertEqual(b["source_review"]["state"], "unbound")
        self.assertIsNone(b["source_review"]["deleted"])
        self.assertIn("license", {r["path"] for r in b["founded_paths"]})     # the v2 rule, unchanged
        self.assertIn("source review not read", b["summary"])

    def test_a_rewritten_value_reviewed_supported_is_founded_only_by_a_linked_finding(self):
        """#3551: the linked-only rule holds on rewritten rows too — a
        free-text slot does not found a supported value rewritten in place."""
        before, after = _record(license="CC-BY 4.0 International"), _record(license="MIT")
        audit = _audit({"slot": "license"})
        audit["source_review"] = _review(before, {"/license": "supported"})
        b = rm.classify(before, after, audit)
        row = b["rewritten_paths"][0]
        self.assertEqual((row["path"], row["source_review"], row["founded"]), ("license", "supported", False))
        self.assertTrue(row["supported_slot_only"])
        self.assertEqual(b["rewritten_unfounded"], 1)
        audit = _audit({"slot": "license", "review_paths": ["/license"]})
        audit["source_review"] = _review(before, {"/license": "supported"})
        row = rm.classify(before, after, audit)["rewritten_paths"][0]
        self.assertEqual((row["founded"], row["by"]), (True, "review_paths"))
        audit = _audit({"slot": "license"})
        audit["source_review"] = _review(before, {"/license": "revise"})
        self.assertTrue(rm.classify(before, after, audit)["rewritten_paths"][0]["founded"])

    def test_revise_on_any_claim_wins_and_supported_needs_every_claim(self):
        """#3551: a value is judged revise where any claim on it is, and
        supported only where every claim is."""
        before = _record(license="CC-BY", keywords=["voice", "speech", "audio"])
        review = {"artifact": "original_full", "sha256": None, "values": [
            {"path": "/license", "claims": [{"verdict": "supported"}, {"verdict": "revise"}]},
            {"path": "/keywords/0", "claims": [{"verdict": "supported"}, {"verdict": "supported"}]},
            {"path": "/keywords/1", "claims": [{"verdict": "supported"}, {"verdict": "unclear"}]}]}
        audit = _audit()
        audit["source_review"] = review
        b = rm.classify(before, _record(), audit)
        judged = {r["path"]: r["source_review"] for r in b["unfounded_paths"]}
        self.assertEqual(judged, {"license": "revise", "keywords[0]": "supported", "keywords[1]": "unreviewed",
                                  "keywords[2]": "unreviewed"})

    def test_a_malformed_review_is_unusable_and_the_removals_are_still_classified(self):
        """#3624: claims that are not a list, a claim that is not a mapping,
        or a verdict that is not a string make the review unusable, named
        with its row; the classification is the one with no review."""
        plain = rm.classify(self.BEFORE, self.AFTER, _audit({"slot": "license"}))
        for claims, why in ((5, "its claims are a int, not a list"), (None, "its claims are a NoneType, not a list"),
                            (["supported"], "a claim is not a mapping"),
                            ([{"verdict": ["supported"]}], "a claim's verdict is not a string"),
                            ([{"verdict": "supported"}, {"text": "t"}], "a claim's verdict is not a string")):
            audit = self._audit({"slot": "license"})
            audit["source_review"]["values"].append({"path": "/description", "claims": claims})
            b = rm.classify(self.BEFORE, self.AFTER, audit)
            self.assertEqual(b["source_review"], {
                "state": "unusable", "reason": f"the source review's row /description is malformed: {why}",
                "deleted": None, "rewritten": None, "unfounded_supported": None,
                "unfounded_supported_slot_only": None}, claims)
            for key in ("removed", "deleted", "founded", "unfounded", "rewritten"):
                self.assertEqual(b[key], plain[key], (claims, key))
            self.assertNotIn("source_review", b["unfounded_paths"][0])
            self.assertIn(f"source review not read: the source review's row /description is malformed: {why}",
                          b["summary"])

    def test_without_a_source_review_nothing_changes(self):
        b = rm.classify(self.BEFORE, self.AFTER, _audit({"slot": "license"}))
        self.assertIsNone(b["source_review"])
        self.assertNotIn("source_review", b["founded_paths"][0])


class Evidence(unittest.TestCase):
    """#3037: the native and direct arms freeze `evidence/original_full.yaml`
    and write `evidence/audit.json`, and no phase output."""

    def _run(self, tmp, *, method="claudecode_direct", records=("CHORUS",), intermediate=False):
        base = Path(tmp)
        core_dir = base / f"{method}_core" / "L"
        (core_dir / "evidence").mkdir(parents=True)
        (base / method / "L").mkdir(parents=True)
        for p in records:
            (core_dir / f"{p}_provenance.yaml").write_text(yaml.safe_dump({"run": {"project": p, "label": "L"}}))
        raw = yaml.safe_dump(SourceReview.BEFORE).encode()
        (core_dir / "evidence" / "original_full.yaml").write_bytes(raw)
        audit = _audit({"slot": "license"}, {"slot": "keywords"})
        audit["source_review"] = _review(SourceReview.BEFORE, SourceReview.JUDGED, hashlib.sha256(raw).hexdigest())
        (core_dir / "evidence" / "audit.json").write_text(json.dumps(audit))
        (base / method / "L" / "CHORUS_d4d.yaml").write_text(yaml.safe_dump(SourceReview.AFTER))
        if intermediate:
            (core_dir / "intermediate").mkdir()
            (core_dir / "intermediate" / "CHORUS_full.yaml").write_text(yaml.safe_dump(_record(description="d")))
        return core_dir / "CHORUS_provenance.yaml"

    def test_a_direct_run_is_read_from_its_evidence_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov = self._run(tmp)
            before = OnDisk._tree(tmp)
            b = rm.for_record(prov)
            self.assertEqual(OnDisk._tree(tmp), before)
        self.assertTrue(b["checked"])
        self.assertEqual(b["artifacts"]["phase1_snapshot"]["source"], "evidence")
        self.assertEqual(b["artifacts"]["audit"]["state"], "usable")
        self.assertEqual((b["artifacts"]["phases"], b["phase"]), ([], None))
        self.assertIn("snapshots no phase output", b["artifacts"]["phases_reason"])
        self.assertEqual(b["source_review"]["state"], "bound")
        self.assertEqual({r["path"] for r in b["unfounded_paths"]}, {"license", "keywords[1]"})

    def test_a_malformed_bound_review_is_reported_not_raised(self):
        """#3624 on the native/direct path: the review is hash-matched and
        the audit usable, but a row's claims are not a list."""
        for claims in (5, [{"verdict": ["revise"]}]):
            with tempfile.TemporaryDirectory() as tmp:
                prov = self._run(tmp)
                path = prov.parent / "evidence" / "audit.json"
                audit = json.loads(path.read_text())
                audit["source_review"]["values"][0]["claims"] = claims
                path.write_text(json.dumps(audit))
                b = rm.for_record(prov)
            self.assertTrue(b["checked"])
            self.assertEqual(b["artifacts"]["audit"]["state"], "usable")
            self.assertEqual(b["source_review"]["state"], "unusable")
            self.assertIn("is malformed", b["source_review"]["reason"])
            self.assertEqual((b["removed"], b["unfounded"]), (3, 0))   # founded by their slots, as with no review

    def test_an_edited_original_unbinds_the_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            prov = self._run(tmp)
            path = prov.parent / "evidence" / "original_full.yaml"
            path.write_text(path.read_text() + "# edited\n")
            b = rm.for_record(prov)
        self.assertEqual(b["source_review"]["state"], "unbound")

    def test_the_api_snapshot_wins_and_an_evidence_directory_two_records_share_is_no_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = rm.for_record(self._run(tmp, method="claudecode_api", intermediate=True))
        self.assertTrue(b["artifacts"]["phase1_snapshot"]["path"].endswith("intermediate/CHORUS_full.yaml"))
        self.assertEqual(b["removed"], 0)
        with tempfile.TemporaryDirectory() as tmp:
            b = rm.for_record(self._run(tmp, records=("CHORUS", "VOICE")))
        self.assertFalse(b["checked"])
        self.assertIn("2 records share this label directory", b["artifacts"]["phase1_snapshot"]["reason"])

    def test_the_cli_says_why_a_direct_run_is_unattributed_and_shows_the_annotations(self):
        import click.testing
        from data_sheets_schema.cli.review import review as review_cli
        with tempfile.TemporaryDirectory() as tmp:
            prov = self._run(tmp)
            with mock.patch("data_sheets_schema.cli.review._provenance", lambda m, l, p: prov):
                r = click.testing.CliRunner().invoke(review_cli, ["removals", "--method", "claudecode_direct",
                                                                  "--label", "L", "--project", "CHORUS"])
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertIn("removed at: not attributed (the native/direct evidence protocol snapshots no phase output)",
                      r.output)
        self.assertIn("✗ unfounded license (phase unattributed, its slot is mentioned in a finding's text, "
                      "source review: supported, only a finding's free-text slot names it)", r.output)


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


#: Every v8 API record with a receipted value whose text does not survive and
#: that no finding's path covers (#3078): the three whole-slot cases the reviews
#: found and five more. Not all are losses: AI_READI 04g rep2's only such value
#: is reworded into a caveat (#3207, pinned below).
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
def test_the_v8_records_with_a_receipted_value_deleted_that_no_finding_covers(monkeypatch):
    """The module docstring's count: eight v8 records, not the three whole
    slots the reviews found — six of the twelve-record fill."""
    monkeypatch.chdir(CONCAT.parents[1])
    provs = sorted(CONCAT.glob("claudecode_api_core/*-v8_rep*/*_provenance.yaml"))
    if not provs:
        pytest.skip("no v8 API records in this checkout")
    found = {(p.parent.name, p.name.split("_provenance")[0]) for p in provs
             if ((rm.for_record(p)["receipted"] or {}).get("unfounded") or 0) > 0}
    assert found == RECEIPTED_UNFOUNDED_V8


#: #3207: receipted values counted deleted and unfounded whose content the final
#: record carries reworded elsewhere — (label, project, removed path, final
#: path, a phrase of the old text the final path restates).
REWORDED_NOT_LOST = [
    ("2026-09-04g_claude-opus-5-api-generic-v8_rep2", "AI_READI", "sampling_strategies[0].notes",
     "sampling_strategies[0].source_caveats", "to the question of the sampling strategy"),
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep1", "VOICE", "at_risk_populations.special_protections[0]",
     "at_risk_populations.special_protections[2]", "such as mood disorders, depression and anxiety"),
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep1", "VOICE", "ethical_reviews[1].review_details",
     "data_governance.notes", "memorandum setting out the ethical justification"),
    ("2026-09-04f_claude-opus-5-api-generic-v8_rep3", "CHORUS", "acquisition_methods[0].notes",
     "labeling_strategies[0].data_annotation_protocol", "clinical validation SOP"),
]


@pytest.mark.corpus
@pytest.mark.parametrize("label, project, removed, final_path, phrase", REWORDED_NOT_LOST)
def test_a_reworded_or_moved_value_is_counted_deleted_though_its_content_survives(
        label, project, removed, final_path, phrase, monkeypatch):
    """#3207: the module docstring's named cases. Each reads as a receipted
    unfounded deletion at reconcile_full, and the final record restates it
    at another path — so rewording inflates the counts (which, #3229, are
    not bounds: coincidental flattening and in-place rewrites deflate them)."""
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay(label, project)
    row = next((r for r in b["unfounded_paths"] if r["path"] == removed), None)
    assert row and row.get("receipted") and row["phase"] == "reconcile_full", b["summary"]
    inter = CONCAT / "claudecode_api_core" / label / "intermediate" / f"{project}_full.yaml"
    final = CONCAT / "claudecode_api" / label / f"{project}_d4d.yaml"
    squash = lambda v: " ".join(str(v).split())
    ok, old = rm._resolve_value(yaml.safe_load(inter.read_text()), removed)
    assert ok and phrase in squash(old)
    ok, new = rm._resolve_value(yaml.safe_load(final.read_text()), final_path)
    assert ok and phrase in squash(new)
    assert squash(old) not in squash(new)          # reworded: the old text does not survive verbatim


@pytest.mark.corpus
def test_the_v4_ai_readi_rep1_identifiers_that_survive_as_curies_are_flattened(monkeypatch):
    """#3129: the single phase-1 creator's eight affiliation ROR URLs, its
    own ROR URL and its PI's ORCID, and the two contact objects collapsed to
    the ORCID CURIE, survive in the final record as CURIEs. v1 counted all
    twelve deleted and 40 unfounded; v2 counts 29."""
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay("2026-08-13_claude-opus-5-api-generic-v4_rep1", "AI_READI", method="claudecode_agent")
    flat = {r["path"] for r in b["flattened_paths"]}
    assert {f"creators[0].affiliations[{i}].id" for i in range(8)} <= flat
    assert {"creators[0].id", "creators[0].principal_investigator.id", "data_governance.committee_contact.id",
            "license_and_use_terms.contact_person.id"} <= flat
    assert (b["unfounded"], b["flattened"]) == (29, 32)


@pytest.mark.corpus
def test_the_five_digit_count_v2_flattened_is_32522_in_the_pinned_snapshot_and_now_deleted(monkeypatch):
    """#3130, and a correction to #3396: the snapshot the removals read for
    v4 VOICE rep1 is the one its run pins, `VOICE_full_2.yaml`, where
    `instances[1].counts` is 32522 — not the 29278 of `VOICE_full.yaml`,
    which #3396 read. Within its entry, `instances[1]`, its only surviving
    trace is one per-feature count in the entry's `source_caveats` (the
    final record also quotes it in `file_collections[0].description`,
    outside that entry, #3552), so v3, which carries a number only as a
    scalar equal to it under the nearest surviving ancestor, reads it deleted (unsorted: this run's audit is
    ambiguous, #3153)."""
    monkeypatch.chdir(CONCAT.parents[1])
    monkeypatch.setattr(rm, "PATH_LIMIT", 10 ** 6)
    label = "2026-08-13_claude-opus-5-api-generic-v4_rep1"
    b = _replay(label, "VOICE", method="claudecode_agent")
    pinned = Path(b["artifacts"]["phase1_snapshot"]["path"])
    assert pinned.name == "VOICE_full_2.yaml"
    assert yaml.safe_load(pinned.read_text())["instances"][1]["counts"] == 32522
    assert "instances[1].counts" not in {r["path"] for r in b["flattened_paths"]}
    assert "instances[1].counts" in {r["path"] for r in b["unsorted_paths"]}
    final = yaml.safe_load((CONCAT / "claudecode_agent" / label / "VOICE_d4d.yaml").read_text())
    assert "32522" in " ".join(str(final["instances"][1]["source_caveats"]).split())


#: #3130: every numeric-only value removals v2 flattened over the 87 checked
#: records — (label, project, path, flattened under v3).
NUMERIC_FLATTENINGS_V2 = [
    ("2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1", "AI_READI", "distribution_dates[2].release_dates[0]", True),
    ("2026-08-13_claude-opus-5-api-generic-v4_rep1", "VOICE", "instances[1].counts", False),
    *[(label, "CM4AI", f"collection_timeframes[0].{k}", False)
      for label in ("2026-08-13_claude-opus-5-api-generic-v4_rep2", "2026-08-13_claude-opus-5-api-generic-v4_rep3",
                    "2026-09-01_claude-opus-5-api-generic-v7_rep2", "2026-09-01_claude-opus-5-api-generic-v7_rep3")
      for k in ("start_date", "end_date")],
]


@pytest.mark.corpus
def test_a_number_v2_flattened_into_prose_is_deleted_and_the_date_carried_whole_is_not(monkeypatch):
    """#3130: of the ten, nine were a count or a date quoted in the prose
    that disowned it; the release date carried as itself stays flattened."""
    monkeypatch.chdir(CONCAT.parents[1])
    monkeypatch.setattr(rm, "PATH_LIMIT", 10 ** 6)
    for label, project, path, flattened in NUMERIC_FLATTENINGS_V2:
        b = _replay(label, project, method="claudecode_agent")
        classes = {cls for cls in ("flattened", "founded", "unfounded", "unsorted")
                   if path in {r["path"] for r in b[f"{cls}_paths"]}}
        assert len(classes) == 1 and ("flattened" in classes) is flattened, (label, path, classes)


@pytest.mark.corpus
def test_the_22c_ai_readi_member_respelled_licence_to_license_is_not_removed(monkeypatch):
    """#3038 on the corpus: v2 read the one `restrictions` member of
    `external_resources[5]` as removed; the written record respells it."""
    monkeypatch.chdir(CONCAT.parents[1])
    monkeypatch.setattr(rm, "PATH_LIMIT", 10 ** 6)
    b = _replay("2026-08-22c_claude-opus-5-api-generic-v5_rep2", "AI_READI", method="claudecode_agent")
    removed = {r["path"] for cls in ("flattened", "founded", "unfounded", "unsorted") for r in b[f"{cls}_paths"]}
    assert "external_resources[5].restrictions[0]" not in removed
    assert (b["unfounded"], b["rewritten_unfounded"]) == (3, 4)


_NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")


def _stated_relocation_measurement() -> dict[str, tuple[int, int, int]]:
    """(tp, fp, fn) as the labelled sample's header states them at the
    declared threshold — over the whole sample, and split by the route
    `_Relocation.candidate` decides a row on (#3613) — after checking that
    the header's precision and recall follow from its counts, that the
    routes add up to the whole, and that the published definitions — the
    removals non-check and the arm table's row — state the same
    measurement in words (#3549) and the content-word route's own figures."""
    root = Path(__file__).resolve().parents[1]
    header = " ".join(line.lstrip("# ").strip() for line in
                      (root / rm.RELOCATED_VALIDATION).read_text().splitlines() if line.startswith("#"))
    m = re.search(r"At RELOCATED_THRESHOLD ([\d.]+) on this sample: (\d+) candidates, (\d+) correct "
                  r"\(precision ([\d.]+)\); (\d+) relocations labelled, (\d+) found \(recall ([\d.]+)\)", header)
    assert m, "the sample header no longer states the measurement in the form this test reads"
    threshold, candidates, tp, precision, labelled, found, recall = m.groups()
    assert float(threshold) == rm.RELOCATED_THRESHOLD
    tp, candidates, labelled = int(tp), int(candidates), int(labelled)
    assert int(found) == tp
    assert f"{tp / candidates:.2f}" == precision and f"{tp / labelled:.2f}" == recall
    ident = re.search(r"Identifier route: (\d+) rows, (\d+) candidates, (\d+) correct; (\d+) relocations "
                      r"labelled, (\d+) found \((\d+) false positives, (\d+) missed\)", header)
    content = re.search(r"Content-word route: (\d+) rows, (\d+) candidates, (\d+) correct \(precision "
                        r"([\d.]+)\); (\d+) relocations labelled, (\d+) found \(recall ([\d.]+)\)", header)
    assert ident and content, "the sample header no longer states the split by route in the form this test reads"
    i_rows, i_cand, i_tp, i_lab, i_found, i_fp, i_fn = map(int, ident.groups())
    assert (i_found, i_fp, i_fn) == (i_tp, i_cand - i_tp, i_lab - i_tp)
    c_rows, c_cand, c_tp, c_prec, c_lab, c_found, c_rec = content.groups()
    c_rows, c_cand, c_tp, c_lab = int(c_rows), int(c_cand), int(c_tp), int(c_lab)
    assert int(c_found) == c_tp
    assert f"{c_tp / c_cand:.2f}" == c_prec and f"{c_tp / c_lab:.2f}" == c_rec
    sample_rows = len(yaml.safe_load((root / rm.RELOCATED_VALIDATION).read_text())["rows"])
    assert i_rows + c_rows == sample_rows
    assert (i_tp + c_tp, i_cand + c_cand, i_lab + c_lab) == (tp, candidates, labelled)
    in_ten = f"about {_NUMBER_WORDS[round(10 * tp / candidates)]} times in ten"
    in_five = f"about {_NUMBER_WORDS[round(5 * tp / labelled)]} relocations in five"
    spec = importlib.util.spec_from_file_location("arm_comparison_3549", root / "scripts" / "arm_comparison.py")
    arm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(arm)
    for name, text in (("removals NON_CHECKS", " ".join(rm.NON_CHECKS)),
                       ("arm table unfoundedrelocated", " ".join(arm.METRICS["unfoundedrelocated"][3].split()))):
        assert in_ten in text and in_five in text, (name, in_ten, in_five)
        # #3613: the published figures are over both routes, and each
        # definition states the content-word route's own.
        assert "not measured" not in text, name
        for figure in (f"{i_rows} of", f"{sample_rows} rows", f"{c_rows} content-word rows",
                       f"{i_tp} found", c_prec, c_rec):
            assert figure in text, (name, figure)
    return {"all": (tp, candidates - tp, labelled - tp),
            "identifier": (i_tp, i_cand - i_tp, i_lab - i_tp),
            "content": (c_tp, c_cand - c_tp, c_lab - c_tp)}


def test_the_relocation_measurement_the_sample_states_is_the_one_the_definitions_publish():
    """#3549: the header's counts, its precision and recall, and the words
    the non-check and the arm table use for them agree; #3613: so do the
    counts by route."""
    assert _stated_relocation_measurement() == {"all": (25, 3, 6), "identifier": (5, 0, 0),
                                                "content": (20, 3, 6)}


@pytest.mark.corpus
def test_the_relocation_threshold_measures_what_the_labelled_sample_says(monkeypatch):
    """#3223: precision and recall of the candidate at the declared
    threshold, recomputed on the hand-labelled sample and compared with
    what the sample file's header states (whose figures the published
    definitions are checked against, #3549) — over the whole sample and
    by the route `_Relocation.candidate` takes, identifier-shaped or
    content-word (#3613)."""
    monkeypatch.chdir(CONCAT.parents[1])
    sample = yaml.safe_load((CONCAT.parents[1] / rm.RELOCATED_VALIDATION).read_text())
    assert (sample["threshold"], sample["min_content_words"]) == (rm.RELOCATED_THRESHOLD, rm.RELOCATED_MIN_WORDS)
    records: dict = {}
    counts = {route: [0, 0, 0] for route in ("all", "identifier", "content")}
    for row in sample["rows"]:
        key = (row["label"], row["project"])
        if key not in records:
            core = next(CONCAT.glob(f"*_core/{row['label']}/{row['project']}_provenance.yaml"), None)
            if core is None:
                pytest.skip(f"{key} is not in this checkout")
            b = rm.for_record(core)
            snapshot = yaml.safe_load(Path(b["artifacts"]["phase1_snapshot"]["path"]).read_text())
            records[key] = (snapshot, rm._Relocation(yaml.safe_load(Path(b["artifacts"]["final"]).read_text())))
        snapshot, relocation = records[key]
        ok, value = rm._resolve_value(snapshot, row["path"])
        assert ok, row
        where = relocation.candidate(value)[1]
        assert (where or {}).get("to") == row["candidate"], row
        route = ("identifier" if isinstance(value, str) and rm._IDENTIFIER_SHAPED.fullmatch(value.strip())
                 else "content")
        for tally in (counts["all"], counts[route]):
            tally[0] += bool(where) and row["relocated"]
            tally[1] += bool(where) and not row["relocated"]
            tally[2] += (not where) and row["relocated"]
    assert {route: tuple(c) for route, c in counts.items()} == _stated_relocation_measurement()


@pytest.mark.corpus
def test_the_22c_cm4ai_file_counts_are_deleted_and_rewritten_not_flattened_or_carried(monkeypatch):
    """#3243 on the record the issue names: the dropped `file_collections[1]`
    had file_count 3, which v1 read as flattened into the '3' of '3.8 GB';
    `file_collections[0]` kept its place and its file_count went 2 -> 1."""
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay("2026-08-22c_claude-opus-5-api-generic-v5_rep1", "CM4AI", method="claudecode_agent")
    assert "file_collections[1].file_count" in {r["path"] for r in b["unfounded_paths"]}
    assert "file_collections[1].file_count" not in {r["path"] for r in b["flattened_paths"]}
    rewritten = {r["path"]: r for r in b["rewritten_paths"]}
    assert rewritten["file_collections[0].file_count"]["at"] == "file_collections[0].file_count"
    assert b["unfounded"] == 10
