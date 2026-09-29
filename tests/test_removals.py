"""Values deleted after phase 1, classified against the audit (#2923).

`reconcile_full` is told to remove what a finding identifies as unsupported,
and three v8 API records lost a receipted value no finding named. These pin
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
        self.assertNotIn("phase", b["unfounded_paths"][0])


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
        self.assertEqual(json.loads(j.output)["unfounded"], 4)


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
def test_an_agentic_record_is_unmeasured_not_zero(monkeypatch):
    monkeypatch.chdir(CONCAT.parents[1])
    b = _replay("2026-08-28_claude-opus-5-claudecode-generic-v6_rep1", "CHORUS", method="claudecode_agent")
    assert b["checked"] is False and b["unfounded"] is None
