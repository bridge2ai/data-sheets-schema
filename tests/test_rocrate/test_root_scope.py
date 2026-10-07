"""Adversarial root selection, assertion accounting and adapter integration."""

import copy
import tempfile
import unittest
from pathlib import Path

from data_sheets_schema.rocrate_map import FULL_SCHEMA, map_crate, write_provenance
from data_sheets_schema.rocrate_sources import present, resolve_path, select_root
from data_sheets_schema.schema_view import shared_view


ROOT_ID = "https://example.org/root"


def descriptor(identifier=ROOT_ID):
    return {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
            "about": {"@id": identifier}}


def row(path, source, **options):
    return {"D4D_Full_Path": path, "RO_Crate_JSON_Path": source,
            "Mapping_Type": "", "Information_Loss": "", **options}


class TestExplicitRootSelection(unittest.TestCase):
    def test_descriptor_precedes_conventional_and_rocrate_typed_decoys(self):
        root = {"@id": ROOT_ID, "@type": "Dataset", "name": "Root"}
        decoy = {"@id": "./", "@type": ["Dataset", "ROCrate"], "name": "Decoy"}
        for graph in ([descriptor(), root, decoy], [decoy, root, descriptor()]):
            chosen, detail = select_root(graph)
            self.assertIs(chosen, root)
            self.assertIn("about", detail)

    def test_conflicting_descriptors_and_unresolved_about_never_fall_back(self):
        root = {"@id": ROOT_ID, "@type": "Dataset"}
        conventional = {"@id": "./", "@type": "Dataset"}
        other = {"@id": "folder/ro-crate-metadata.json", "about": {"@id": "other"}}
        graphs = ([descriptor(), other, root, conventional],
                  [descriptor("missing"), conventional],
                  [{"@id": "ro-crate-metadata.json", "about": []}, conventional],
                  [{"@id": "ro-crate-metadata.json", "about": None}, conventional])
        for graph in graphs:
            with self.subTest(graph=graph):
                self.assertIsNone(select_root(graph)[0])

    def test_same_target_repeated_by_descriptors_is_not_a_conflict(self):
        root = {"@id": ROOT_ID, "@type": "Dataset"}
        other = {"@id": "folder/ro-crate-metadata.json", "about": [{"@id": ROOT_ID}]}
        self.assertIs(select_root([descriptor(), other, root])[0], root)

    def test_duplicate_target_ids_are_rejected_even_when_one_is_untyped(self):
        for identifier, reference in ((ROOT_ID, [descriptor()]), ("./", []), (".", [])):
            graph = reference + [{"@id": identifier, "@type": "Dataset"},
                                 {"@id": identifier, "name": "Ambiguous identity"}]
            with self.subTest(identifier=identifier):
                self.assertIsNone(select_root(graph)[0])
                self.assertIsNone(select_root(list(reversed(graph)))[0])

    def test_unreferenced_multiple_datasets_are_ambiguous_in_either_order(self):
        graph = [{"@id": "a", "@type": "Dataset"}, {"@id": "b", "@type": "Dataset"}]
        self.assertIsNone(select_root(graph)[0])
        self.assertIsNone(select_root(list(reversed(graph)))[0])

    def test_descriptor_cannot_promote_an_organization_to_root_dataset(self):
        root = {"@id": ROOT_ID, "@type": "Organization"}
        self.assertIsNone(select_root([descriptor(), root])[0])

    def test_unrelated_malformed_member_identifier_cannot_crash_descriptor_selection(self):
        root = {"@id": ROOT_ID, "@type": "Dataset"}
        member = {"@id": "http://[", "@type": "Dataset"}
        self.assertIs(select_root([member, descriptor(), root])[0], root)


class TestRootPathResolution(unittest.TestCase):
    def test_missing_or_empty_root_never_falls_through_to_member(self):
        for value in (None, "", [], {}):
            root = {"@id": ROOT_ID, "@type": "Dataset", "name": value}
            member = {"@id": "member", "@type": "Dataset", "name": "Member only"}
            for graph in ([descriptor(), root, member], [member, root, descriptor()]):
                with self.subTest(value=value, graph=graph):
                    actual, detail = resolve_path("@graph[?@type='Dataset']['name']", graph, root)
                    self.assertIsNone(actual)
                    self.assertIn("member", detail)

    def test_false_and_zero_are_values_in_bare_and_graph_paths(self):
        for value in (False, 0):
            root = {"@id": ROOT_ID, "@type": "Dataset", "value": value}
            self.assertTrue(present(value))
            for expr in ("value", "@graph[?@type='Dataset']['value']"):
                with self.subTest(value=value, expr=expr):
                    actual, detail = resolve_path(expr, [root], root)
                    self.assertIs(actual, value)
                    self.assertEqual(detail, "")

    def test_named_selector_keeps_false_but_refuses_conflicting_entries(self):
        expression = "@graph[?@type='Dataset']['additionalProperty'][?name='Flag']['value']"
        root = {"@id": ROOT_ID, "@type": "Dataset",
                "additionalProperty": [{"name": "Flag", "value": False}]}
        self.assertIs(resolve_path(expression, [root], root)[0], False)
        root["additionalProperty"].append({"name": "Flag", "value": True})
        actual, detail = resolve_path(expression, [root], root)
        self.assertIsNone(actual)
        self.assertIn("multiple", detail)

    def test_unknown_graph_syntax_cannot_become_a_literal_property_lookup(self):
        for expression in ("@graph[0]['name']", "@graph[?@type='Dataset'].name",
                           "@graph[?@type='Dataset']['name']['unexpected']"):
            root = {"@id": ROOT_ID, "@type": "Dataset", expression: "Trap"}
            with self.subTest(expression=expression):
                actual, _ = resolve_path(expression, [root], root)
                self.assertIsNone(actual)


class TestRootScopeMapperIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sv = shared_view(FULL_SCHEMA)

    def map(self, root, rows, others=()):
        return map_crate([descriptor(), root, *others], rows, self.sv, "TEST")

    def test_human_fields_and_governance_literal_survive_mapper_integration(self):
        root = {"@id": ROOT_ID, "@type": "Dataset", "humanSubjectResearch": False,
                "humanSubjectExemption": "No", "irbProtocolId": "Protocol only",
                "irb": {"@type": "Organization", "name": "Explicit Board"},
                "dataGovernanceCommittee": "Named person, person@example.org"}
        rows = [row("Dataset.human_subject_research", "humanSubjectResearch",
                    Mapping_Rule="human_subjects", Rule_ID="human"),
                row("DataGovernance.description", "dataGovernanceCommittee", Rule_ID="governance")]
        result = self.map(root, rows)
        human = result.record["human_subject_research"]
        self.assertIs(human["involves_human_subjects"], False)
        self.assertEqual(human["ethics_review_board"], "Explicit Board")
        self.assertIn("Source humanSubjectExemption: No", human["description"])
        self.assertIn("Protocol only", human["description"])
        self.assertNotIn("irb_approval", human)
        self.assertEqual(result.record["data_governance"],
                         {"description": root["dataGovernanceCommittee"]})
        self.assertEqual([entry["rule_id"] for entry in result.sources["rows"]],
                         ["human", "governance"])

    def test_root_identifier_copy_does_not_establish_semantic_fidelity(self):
        root = {"@id": ROOT_ID, "@type": "Dataset", "identifier": ["10.1234/first", "10.1234/second"]}
        result = self.map(root, [])
        identifier = next(field for field in result.fields if not field.from_table)
        self.assertEqual((identifier.mapping_type, identifier.information_loss), ("", ""))
        self.assertIn("first of 2", identifier.detail)

    def test_inactive_rows_keep_raw_false_zero_and_full_list_in_original_denominator(self):
        long_text = "Complete original narrative. " * 20
        root = {"@id": ROOT_ID, "@type": "Dataset", "name": "Root",
                "fdaRegulated": False, "count": 0,
                "evidence": [long_text, None, ["nested"], {"value": False}]}
        rows = [row("Dataset.title", "name", Rule_ID="active"),
                row("QualityControl.fda_compliant", "fdaRegulated", Rule_ID="retired",
                    Execution="retired", Execution_Reason="Wrong semantic target"),
                row("EvidenceMetadata.total_entities", "count", Rule_ID="zero",
                    Execution="deferred", Execution_Reason="Preserve evidence graph count"),
                row("EvidenceMetadata.extra", "evidence", Rule_ID="list",
                    Execution="deferred", Execution_Reason="Unsupported target")]
        result = self.map(root, rows)
        self.assertEqual(len([field for field in result.fields if field.from_table]), 4)
        self.assertEqual([entry["status"] for entry in result.sources["rows"]],
                         ["filled", "retired", "deferred", "deferred"])
        self.assertEqual(len(result.sources["rows"]), 4)
        self.assertIs(result.sources["rows"][1]["root_assertions"][0]["value"], False)
        self.assertEqual(result.sources["rows"][2]["root_assertions"][0]["value"], 0)
        self.assertEqual(result.sources["rows"][3]["root_assertions"][0]["value"], root["evidence"])
        result.validation = "PASS"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.md"
            write_provenance(result, output, Path("crate.json"))
            report = output.read_text()
        self.assertIn("4 table rows declared", report)
        self.assertIn("Executable table rules: 1; retired: 1; deferred: 2; original table rows: 4", report)

    def test_missing_root_value_keeps_member_assertion_separate(self):
        root = {"@id": ROOT_ID, "@type": "Dataset"}
        member = {"@id": "member", "@type": "Dataset", "name": "Member name"}
        rows = [row("Dataset.title", "@graph[?@type='Dataset']['name']")]
        result = self.map(root, rows, [member])
        self.assertNotIn("title", result.record)
        evidence = result.sources["rows"][0]
        self.assertEqual(evidence["root_assertions"], [])
        self.assertEqual(evidence["member_assertions"][0]["entity_id"], "member")
        self.assertEqual(evidence["member_assertions"][0]["value"], "Member name")

    def test_raw_sidecar_is_independent_of_input_mutation_and_preserves_pointer_escaping(self):
        value = [{"literal": ["a", None, False]}]
        root = {"@id": ROOT_ID, "@type": "Dataset", "a~/b": value}
        rows = [row("NoClass.value", "a~/b", Execution="deferred", Execution_Reason="Keep evidence")]
        result = self.map(root, rows)
        retained = copy.deepcopy(result.sources)
        root["a~/b"][0]["literal"].append("later mutation")
        self.assertEqual(result.sources, retained)
        assertion = result.sources["rows"][0]["root_assertions"][0]
        self.assertTrue(assertion["json_pointer"].endswith("/a~0~1b"))

    def test_named_property_conflicts_remain_in_source_evidence(self):
        root = {"@id": ROOT_ID, "@type": "Dataset", "additionalProperty": [
            {"name": "Flag", "value": False}, {"name": "Flag", "value": True}]}
        expr = "@graph[?@type='Dataset']['additionalProperty'][?name='Flag']['value']"
        result = self.map(root, [row("Dataset.title", expr)])
        self.assertNotIn("title", result.record)
        self.assertEqual([assertion["value"] for assertion in result.sources["rows"][0]["root_assertions"]],
                         [False, True])

    def test_string_irb_reference_retains_linked_entity_used_by_adapter(self):
        root = {"@id": ROOT_ID, "@type": "Dataset", "irb": "https://example.org/board"}
        board = {"@id": "https://example.org/board", "@type": "Organization", "name": "Board"}
        result = self.map(root, [row("Dataset.human_subject_research", "humanSubjectResearch",
                                    Mapping_Rule="human_subjects")], [board])
        self.assertEqual(result.record["human_subject_research"]["ethics_review_board"], "Board")
        self.assertEqual(result.sources["rows"][0]["linked_assertions"][0]["value"], board)

    def test_adapter_evidence_follows_its_declared_reads_for_rocrate_only_root(self):
        root = {"@id": ROOT_ID, "@type": "ROCrate", "humanSubjectResearch": "Yes"}
        result = self.map(root, [row("Dataset.human_subject_research",
                                    "@graph[?@type='Dataset']['humanSubjectResearch']",
                                    Mapping_Rule="human_subjects")])
        self.assertTrue(result.record["human_subject_research"]["involves_human_subjects"])
        self.assertEqual(result.sources["rows"][0]["root_assertions"][0]["value"], "Yes")

    def test_opposing_token_inside_secondary_list_suppresses_boolean(self):
        root = {"@id": ROOT_ID, "@type": "Dataset", "humanSubjectResearch": True,
                "humanSubjects": [True, False, "qualified narrative"]}
        result = self.map(root, [row("Dataset.human_subject_research", "humanSubjectResearch",
                                    Mapping_Rule="human_subjects")])
        record = result.record["human_subject_research"]
        self.assertNotIn("involves_human_subjects", record)
        self.assertIn('[true, false, "qualified narrative"]', record["description"])
        originals = {entry["property"]: entry["value"]
                     for entry in result.sources["rows"][0]["root_assertions"]}
        self.assertEqual(originals["humanSubjects"], root["humanSubjects"])

    def test_imputation_adapter_preserves_original_lists_even_when_shaping_drops_items(self):
        values = ["No method was applied.", None, ["nested assertion"]]
        root = {"@id": ROOT_ID, "@type": "Dataset",
                "rai:dataImputationProtocol": values,
                "rai:imputationProtocol": "A conflicting legacy statement."}
        result = self.map(root, [row("Dataset.imputation_protocols", "rai:dataImputationProtocol",
                                    Mapping_Rule="imputation")])
        originals = {entry["property"]: entry["value"]
                     for entry in result.sources["rows"][0]["root_assertions"]}
        self.assertEqual(originals["rai:dataImputationProtocol"], values)
        self.assertEqual(originals["rai:imputationProtocol"], root["rai:imputationProtocol"])
        self.assertEqual(len(result.record["imputation_protocols"]), 2)

    def test_typed_parent_adapter_keeps_rejected_organization_assertion_in_evidence(self):
        parent_id = "https://example.org/parent"
        org_id = "https://example.org/organization"
        root = {"@id": ROOT_ID, "@type": "Dataset", "isPartOf": [parent_id, org_id]}
        parent = {"@id": parent_id, "@type": "Dataset"}
        organization = {"@id": org_id, "@type": "Organization"}
        result = self.map(root, [row("Dataset.parent_datasets", "isPartOf",
                                    Mapping_Rule="typed_parents")], [parent, organization])
        self.assertEqual(result.record["parent_datasets"], [{"id": parent_id}])
        evidence = result.sources["rows"][0]
        self.assertEqual(evidence["root_assertions"][0]["value"], [parent_id, org_id])
        self.assertEqual({entry["entity_id"] for entry in evidence["linked_assertions"]},
                         {parent_id, org_id})

    def test_unsupported_graph_syntax_is_not_reported_as_resolved_root_evidence(self):
        expression = "@graph[0]['name']"
        root = {"@id": ROOT_ID, "@type": "Dataset", expression: "Literal trap"}
        result = self.map(root, [row("Dataset.title", expression)])
        self.assertNotIn("title", result.record)
        self.assertEqual(result.sources["rows"][0]["root_assertions"], [])

    def test_unknown_adapter_fails_even_for_inactive_or_unplaceable_target(self):
        root = {"@id": ROOT_ID, "@type": "Dataset", "name": "Root"}
        for path in ("Dataset.title", "MissingClass.missing"):
            for disposition in ("active", "retired", "deferred"):
                with self.subTest(path=path, disposition=disposition):
                    with self.assertRaises(ValueError):
                        self.map(root, [row(path, "name", Mapping_Rule="unknown",
                                            Execution=disposition, Execution_Reason="Historical")])

    def test_known_adapter_wrong_destination_and_unknown_execution_fail(self):
        root = {"@id": ROOT_ID, "@type": "Dataset"}
        for adapter in ("human_subjects", "imputation", "typed_parents"):
            with self.subTest(adapter=adapter), self.assertRaises(ValueError):
                self.map(root, [row("Dataset.title", "name", Mapping_Rule=adapter)])
        with self.assertRaises(ValueError):
            self.map(root, [row("Dataset.title", "name", Execution="disabled")])
        for disposition in ("retired", "deferred"):
            with self.subTest(disposition=disposition), self.assertRaises(ValueError):
                self.map(root, [row("Dataset.title", "name", Execution=disposition)])


if __name__ == "__main__":
    unittest.main()
