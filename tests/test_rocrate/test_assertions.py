"""Source-preserving decisions on one selected crate root (#2915)."""

import copy
import json
import unittest

from data_sheets_schema.rocrate_assertions import (
    human_subject_record, imputation_values, typed_parent_values,
)


class TestHumanSubjectAssertions(unittest.TestCase):
    def test_false_is_present_and_missing_is_not_a_negative_assertion(self):
        record, detail = human_subject_record({"humanSubjectResearch": False}, [])
        self.assertIs(record["involves_human_subjects"], False)
        self.assertIn("Source humanSubjectResearch: false", record["description"])
        self.assertIsNone(human_subject_record({}, [
            {"@type": "Dataset", "humanSubjectResearch": True}])[0])

    def test_only_explicit_tokens_normalize_and_raw_text_survives(self):
        for raw, wanted in ((True, True), (False, False), (" YES ", True), ("No", False)):
            with self.subTest(raw=raw):
                record, _ = human_subject_record({"humanSubjectResearch": raw}, [])
                self.assertIs(record["involves_human_subjects"], wanted)
                if isinstance(raw, str):
                    self.assertIn(raw, record["description"])
        for raw in (0, 1, "true", "None - commercially available cell lines", "No, except X"):
            with self.subTest(raw=raw):
                record, _ = human_subject_record({"humanSubjectResearch": raw}, [])
                self.assertNotIn("involves_human_subjects", record)

    def test_lists_and_conflicts_are_preserved_without_choosing_a_winner(self):
        value = ["Yes", "No", None, ["qualified narrative"]]
        record, detail = human_subject_record({"humanSubjectResearch": value}, [])
        self.assertIn(json.dumps(value), record["description"])
        self.assertNotIn("involves_human_subjects", record)
        record, detail = human_subject_record({
            "humanSubjectResearch": "Yes", "humanSubjects": "No"}, [])
        self.assertNotIn("involves_human_subjects", record)
        self.assertIn("Source humanSubjects: No", record["description"])
        self.assertIn("opposing explicit", detail)
        record, _ = human_subject_record({"humanSubjects": "Yes"}, [])
        self.assertNotIn("involves_human_subjects", record)

    def test_exemption_and_protocol_never_become_approval_or_compliance(self):
        root = {"humanSubjectExemption": "HIPAA exemption 4 ((45 CFR 46.104(d)(4))",
                "irbProtocolId": "#2022P000707", "fdaRegulated": True}
        record, detail = human_subject_record(root, [])
        self.assertEqual(set(record), {"description"})
        self.assertIn(root["humanSubjectExemption"], record["description"])
        self.assertIn("Source irbProtocolId: #2022P000707", record["description"])
        self.assertIn("do not establish approval", detail)
        self.assertNotIn("fdaRegulated", record["description"])
        record, _ = human_subject_record({"humanSubjectExemption": "No"}, [])
        self.assertIn("Source humanSubjectExemption: No", record["description"])

    def test_reference_resolution_is_explicit_unique_typed_and_order_independent(self):
        root = {"@id": "root", "irb": {"@id": "board"}}
        board = {"@id": "board", "@type": "Organization", "name": "Stated Board"}
        child = {"@id": "child", "@type": "Dataset", "humanSubjectResearch": "Yes"}
        a = human_subject_record(root, [root, board, child])
        b = human_subject_record(root, [child, board, root])
        self.assertEqual(a, b)
        self.assertEqual(a[0]["ethics_review_board"], "Stated Board")
        self.assertNotIn("involves_human_subjects", a[0])
        self.assertIn('"name": "Stated Board"', a[0]["description"])
        for graph in ([root], [board, dict(board)], [dict(board, **{"@type": "Person"})]):
            with self.subTest(graph=graph):
                record, _ = human_subject_record(root, graph)
                self.assertNotIn("ethics_review_board", record)

    def test_inline_irb_list_keeps_names_separate_and_preserves_other_fields(self):
        boards = [{"@type": "Organization", "name": "A", "contactPoint": {"email": "a@x"}},
                  {"@type": "Organization", "name": "B"}]
        root = {"irb": boards}
        before = copy.deepcopy(root)
        record, detail = human_subject_record(root, [])
        self.assertNotIn("ethics_review_board", record)
        self.assertIn("a@x", record["description"])
        self.assertIn("multiple board names", detail)
        self.assertEqual(root, before)

    def test_inline_board_cannot_override_an_incompatible_graph_type(self):
        root = {"irb": {"@id": "board", "@type": "Organization", "name": "Claim"}}
        record, detail = human_subject_record(root, [{"@id": "board", "@type": "Person"}])
        self.assertNotIn("ethics_review_board", record)
        self.assertIn("types disagree", detail)

    def test_conflicting_inline_and_referenced_board_names_are_both_retained(self):
        root = {"irb": {"@id": "board", "@type": "Organization", "name": "Inline"}}
        record, detail = human_subject_record(root, [
            {"@id": "board", "@type": "Organization", "name": "Referenced"}])
        self.assertNotIn("ethics_review_board", record)
        self.assertIn("Inline", record["description"])
        self.assertIn("Referenced", record["description"])
        self.assertIn("neither name selected", detail)


class TestImputationAssertions(unittest.TestCase):
    def test_negative_narrative_is_retained_and_never_made_into_a_method(self):
        text = "No imputation is applied; users may choose MICE for their analyses."
        values, detail = imputation_values({"rai:dataImputationProtocol": text})
        self.assertEqual(values, [text])
        self.assertIn("do not imply an applied method", detail)
        self.assertIsNone(imputation_values({})[0])

    def test_dual_keys_preserve_order_conflicts_and_exact_deduplication(self):
        values, detail = imputation_values({
            "rai:dataImputationProtocol": ["No imputation", "same"],
            "rai:imputationProtocol": ["MICE was used", "same"]})
        self.assertEqual(values, ["No imputation", "same", "MICE was used"])
        self.assertIn("without overwriting", detail)
        self.assertEqual(imputation_values({"rai:imputationProtocol": "legacy"})[0], ["legacy"])

    def test_nested_values_nulls_and_boolean_numeric_distinctions_survive(self):
        root = {"rai:dataImputationProtocol": [False, 0, None, ["x"], {"name": "x"}]}
        before = copy.deepcopy(root)
        values, _ = imputation_values(root)
        self.assertEqual(values, before["rai:dataImputationProtocol"])
        self.assertIs(values[0], False)
        values[-1]["name"] = "changed"
        self.assertEqual(root, before)


class TestTypedParentAssertions(unittest.TestCase):
    def test_only_explicit_dataset_types_place_without_graph_order_dependence(self):
        root = {"@id": "root", "isPartOf": ["parent", "org", "project", "https://x/Dataset/guess"]}
        graph = [root, {"@id": "parent", "@type": ["https://w3id.org/EVI#Dataset"]},
                 {"@id": "org", "@type": "Organization"},
                 {"@id": "project", "@type": "Project"}]
        a = typed_parent_values(root, graph)
        self.assertEqual(a, typed_parent_values(root, list(reversed(graph))))
        self.assertEqual(a[0], [{"@id": "parent"}])
        self.assertEqual(a[1].count("refused"), 3)

    def test_missing_root_property_never_reads_a_member_dataset(self):
        graph = [{"@id": "child", "isPartOf": {"@id": "p", "@type": "Dataset"}}]
        self.assertIsNone(typed_parent_values({"@id": "root"}, graph)[0])
        self.assertIsNone(typed_parent_values({"isPartOf": "p"}, graph)[0])

    def test_self_and_known_cycles_are_refused(self):
        for graph in (
                [{"@id": "root", "@type": "Dataset", "isPartOf": "root"}],
                [{"@id": "root", "isPartOf": "p"},
                 {"@id": "p", "@type": "Dataset", "isPartOf": "root"}],
                [{"@id": "root", "isPartOf": "p"},
                 {"@id": "p", "@type": "Dataset", "isPartOf": "q"},
                 {"@id": "q", "@type": "Dataset", "isPartOf": "p"}]):
            with self.subTest(graph=graph):
                values, detail = typed_parent_values(graph[0], graph)
                self.assertIsNone(values)
                self.assertIn("cycle", detail)

    def test_duplicate_identity_or_conflicting_inline_type_is_refused(self):
        root = {"@id": "root", "isPartOf": "p"}
        duplicate = [{"@id": "p", "@type": "Dataset"},
                     {"@id": "p", "@type": "Dataset"}]
        self.assertIsNone(typed_parent_values(root, duplicate)[0])
        root["isPartOf"] = {"@id": "p", "@type": "Dataset"}
        self.assertIsNone(typed_parent_values(root, [{"@id": "p", "@type": "Organization"}])[0])

    def test_inline_typed_parent_deduplication_and_shared_ancestors(self):
        root = {"@id": "root", "isPartOf": [
            {"@id": "p", "@type": "Dataset"}, "p", "q"]}
        graph = [{"@id": "p", "@type": "Dataset", "isPartOf": "a"},
                 {"@id": "q", "@type": "Dataset", "isPartOf": "a"},
                 {"@id": "a", "@type": "Dataset"}]
        before = copy.deepcopy((root, graph))
        values, detail = typed_parent_values(root, graph)
        self.assertEqual(values, [{"@id": "p"}, {"@id": "q"}])
        self.assertIn("duplicate reference subsumed", detail)
        self.assertEqual((root, graph), before)

    def test_inline_empty_edges_cannot_hide_a_graph_cycle(self):
        root = {"@id": "root", "isPartOf": {
            "@id": "p", "@type": "Dataset", "isPartOf": []}}
        graph = [{"@id": "p", "@type": "Dataset", "isPartOf": "root"}]
        values, detail = typed_parent_values(root, graph)
        self.assertIsNone(values)
        self.assertIn("cycle", detail)
        # A reference's extra inline edge is also evidence, even when its
        # explicit Dataset type comes only from the graph entity.
        root["isPartOf"] = {"@id": "p", "isPartOf": "root"}
        values, detail = typed_parent_values(root, [{"@id": "p", "@type": "Dataset"}])
        self.assertIsNone(values)
        self.assertIn("cycle", detail)

    def test_ambiguous_ancestor_and_inline_self_cycle_are_refused(self):
        root = {"@id": "root", "isPartOf": "p"}
        graph = [{"@id": "p", "@type": "Dataset", "isPartOf": "a"},
                 {"@id": "a"}, {"@id": "a"}]
        values, detail = typed_parent_values(root, graph)
        self.assertIsNone(values)
        self.assertIn("duplicate graph identities", detail)
        root["isPartOf"] = {"@id": "p", "@type": "Dataset", "isPartOf": {"@id": "p"}}
        values, detail = typed_parent_values(root, [])
        self.assertIsNone(values)
        self.assertIn("cycle", detail)


if __name__ == "__main__":
    unittest.main()
