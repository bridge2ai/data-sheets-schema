"""Tests for the our-mapping crate → D4D arm."""

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

import yaml
from linkml_runtime import SchemaView

from data_sheets_schema.rocrate_map import (
    FULL_SCHEMA,
    CrateEncodingError,
    MapResult,
    _normalize_datetime,
    build_placement,
    crate_property,
    crate_root,
    doi_for_slot,
    load_mapping,
    map_crate,
    map_project,
    read_crate_json,
    resolve_path,
    validate,
    verdict_basis,
    write_provenance,
)
from data_sheets_schema.schema_cache import sha256_of

GRAPH = [
    {"@id": "ro-crate-metadata.json", "@type": "CreativeWork"},
    {"@id": "ark:59853/thing", "@type": ["https://w3id.org/EVI#Dataset",
                                         "https://w3id.org/EVI#ROCrate"],
     "name": "Test Crate", "description": "A crate for tests",
     "identifier": "https://doi.org/10.5555/Test",
     "author": ["Ada Lovelace", "Alan Turing"],
     "rai:dataBiases": "Sampling bias: clinic-recruited cohort.",
     "additionalProperty": [{"name": "Completeness", "value": "Interim"}],
     "keywords": ["voice", "health"]},
]


class TestPathResolution(unittest.TestCase):
    def setUp(self):
        self.root = crate_root(GRAPH)

    def test_crate_root_prefers_the_rocrate_entity(self):
        self.assertEqual(self.root["@id"], "ark:59853/thing")

    def test_type_match_tolerates_evi_prefixed_types(self):
        value, _ = resolve_path("@graph[?@type='Dataset']['name']", GRAPH, self.root)
        self.assertEqual(value, "Test Crate")

    def test_bare_property_resolves_on_root(self):
        value, _ = resolve_path("rai:dataBiases", GRAPH, self.root)
        self.assertEqual(value, "Sampling bias: clinic-recruited cohort.")

    def test_nested_name_selector(self):
        value, _ = resolve_path(
            "@graph[?@type='Dataset']['additionalProperty'][?name='Completeness']['value']",
            GRAPH, self.root)
        self.assertEqual(value, "Interim")

    def test_non_paths_are_reported_not_guessed(self):
        for expr in ("N/A", "encodingFormat MIME parameter", "d4d:samplingStrategy"):
            with self.subTest(expr=expr):
                value, note = resolve_path(expr, GRAPH, self.root)
                self.assertIsNone(value)
                self.assertEqual(note, "not a crate path")

    def test_absent_property_reports_why(self):
        value, note = resolve_path("@graph[?@type='Dataset']['nope']", GRAPH, self.root)
        self.assertIsNone(value)
        self.assertIn("nope", note)


class TestDateNormalization(unittest.TestCase):
    def test_iso_date_becomes_datetime(self):
        value, note = _normalize_datetime("2026-04-03")
        self.assertEqual(value, "2026-04-03T00:00:00Z")
        self.assertTrue(note)

    def test_unambiguous_us_order_resolves(self):
        value, _ = _normalize_datetime("12/16/2025")
        self.assertEqual(value, "2025-12-16T00:00:00Z")

    def test_unambiguous_day_first_resolves(self):
        value, _ = _normalize_datetime("16/12/2025")
        self.assertEqual(value, "2025-12-16T00:00:00Z")

    def test_ambiguous_date_is_dropped_not_guessed(self):
        value, note = _normalize_datetime("03/04/2026")
        self.assertIsNone(value)
        self.assertIn("ambiguous", note)


class TestMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def test_the_shipped_table_loads(self):
        self.assertGreater(len(self.rows), 100)
        self.assertTrue(all("D4D_Full_Path" in r for r in self.rows))

    def test_placement_is_schema_derived(self):
        placement = build_placement(self.sv)
        self.assertEqual(placement.get("EthicalReview"), "ethical_reviews")
        self.assertEqual(placement.get("PreprocessingStrategy"),
                         "preprocessing_strategies")

    def test_every_row_is_accounted_for(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        # id is appended separately, so field count is rows + at most one
        self.assertGreaterEqual(len(res.fields), len(self.rows))
        self.assertTrue(all(f.status in
                            ("filled", "subsumed", "empty", "unresolvable",
                             "unplaceable")
                            for f in res.fields))
        # One report row per table row, in table order, and the id apart.
        table = [f for f in res.fields if f.from_table]
        self.assertEqual([f.d4d_path for f in table],
                         [r["D4D_Full_Path"].strip() for r in self.rows])
        self.assertEqual([f.d4d_path for f in res.fields if not f.from_table],
                         ["Dataset.id"])

    def test_record_takes_its_id_from_the_crate(self):
        """A DOI id is written as the `doi:` CURIE, the form #974's write-time
        normaliser gives the generated arms (#2916)."""
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        self.assertEqual(res.record["id"], "doi:10.5555/Test")

    def test_string_authors_become_creator_objects(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        creators = res.record.get("creators")
        self.assertTrue(creators)
        self.assertEqual(creators[0]["name"], "Ada Lovelace")

    def test_nothing_is_filled_without_a_resolving_path(self):
        """An empty crate must yield no filled fields beyond none at all."""
        res = map_crate([{"@id": "x", "@type": "CreativeWork"}],
                        self.rows, self.sv, "TEST")
        self.assertEqual([f for f in res.fields if f.status == "filled"], [])
        self.assertEqual(res.record, {})

    def test_unplaceable_rows_state_a_reason(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        unplaceable = [f for f in res.fields if f.status == "unplaceable"]
        self.assertTrue(unplaceable)
        self.assertTrue(all(f.detail for f in unplaceable))


PROTOCOL = "rai:dataPreprocessingProtocol"
STEPS = ["Resampled to 16 kHz.", "Segmented by task."]


def _row(path, source, mtype="closeMatch", loss="minimal"):
    return {"D4D_Full_Path": path, "RO_Crate_JSON_Path": source,
            "Mapping_Type": mtype, "Information_Loss": loss}


DATASET_ROW = _row("Dataset.preprocessing_strategies",
                   f"@graph[?@type='Dataset']['{PROTOCOL}']")
NESTED_ROW = _row("PreprocessingStrategy.description", PROTOCOL, loss="moderate")


def _with_protocol(steps=STEPS, **extra):
    graph = copy.deepcopy(GRAPH)
    graph[1][PROTOCOL] = steps
    graph[1].update(extra)
    return graph


class TestNestedRowsNeverOverwrite(unittest.TestCase):
    """#2915. A nested `*.description` row replaced the objects a Dataset row
    had placed in the same host slot with one object of '; '-joined items,
    and the report counted both rows filled."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def status(self, res, path):
        return next(f for f in res.fields if f.d4d_path == path)

    def assert_one_object_per_item(self, res):
        # A short single-line item lands in `name`, a long one in
        # `description` (`_to_object`); either way, one object per item.
        self.assertEqual([list(o.values()) for o in res.record["preprocessing_strategies"]],
                         [[step] for step in STEPS])
        self.assertNotIn("; ".join(STEPS), json.dumps(res.record))

    def test_a_list_keeps_one_object_per_item_whatever_the_row_order(self):
        for rows in ([DATASET_ROW, NESTED_ROW], [NESTED_ROW, DATASET_ROW]):
            with self.subTest(first=rows[0]["D4D_Full_Path"]):
                res = map_crate(_with_protocol(), rows, self.sv, "TEST")
                self.assert_one_object_per_item(res)
                self.assertEqual(self.status(res, DATASET_ROW["D4D_Full_Path"]).status,
                                 "filled")
                nested = self.status(res, NESTED_ROW["D4D_Full_Path"])
                self.assertEqual(nested.status, "subsumed")
                self.assertIn("Dataset.preprocessing_strategies", nested.detail)
                self.assertEqual(nested.value_preview, "")
                # the report keeps table order
                self.assertEqual([f.d4d_path for f in res.fields if f.from_table],
                                 [r["D4D_Full_Path"] for r in rows])

    def test_the_shipped_table_keeps_the_list(self):
        res = map_crate(_with_protocol(), self.rows, self.sv, "TEST")
        self.assert_one_object_per_item(res)
        self.assertEqual(self.status(res, NESTED_ROW["D4D_Full_Path"]).status,
                         "subsumed")

    def test_filled_rows_count_distinct_top_level_slots(self):
        graph = _with_protocol(**{
            "rai:dataManipulationProtocol": "Deduplicated.",
            "rai:dataAnnotationProtocol": "Clinician labels.",
            "rai:dataAnnotationAnalysis": ["Kappa 0.8.", "Audited."],
        })
        res = map_crate(graph, self.rows, self.sv, "TEST")
        self.assertEqual(res.counts()["subsumed"], 4)
        self.assertEqual(res.counts()["filled"], len(res.record))

    def test_a_nested_row_alone_still_fills_its_host(self):
        res = map_crate(_with_protocol(["Resampled."]), [NESTED_ROW], self.sv, "TEST")
        self.assertEqual(res.record["preprocessing_strategies"],
                         [{"description": "Resampled."}])
        self.assertEqual(self.status(res, NESTED_ROW["D4D_Full_Path"]).status,
                         "filled")

    def test_a_nested_row_reading_another_property_is_not_merged(self):
        """Different crate property into a filled host: not placed, and the
        reason says merging is undecided; the host keeps the Dataset row's
        objects."""
        other = _row("PreprocessingStrategy.description", "rai:dataBiases")
        for rows in ([DATASET_ROW, other], [other, DATASET_ROW]):
            with self.subTest(first=rows[0]["RO_Crate_JSON_Path"]):
                res = map_crate(_with_protocol(), rows, self.sv, "TEST")
                self.assert_one_object_per_item(res)
                row = self.status(res, "PreprocessingStrategy.description")
                self.assertEqual(row.status, "unplaceable")
                self.assertIn("rai:dataBiases", row.detail)
                self.assertIn("not decided", row.detail)
        # Another property holding the same value is still another property:
        # the table did not declare it the same source, so it is not subsumed.
        res = map_crate(_with_protocol(**{"rai:dataBiases": STEPS}),
                        [DATASET_ROW, other], self.sv, "TEST")
        self.assertEqual(self.status(res, "PreprocessingStrategy.description").status,
                         "unplaceable")

    def test_the_same_property_on_another_entity_is_not_subsumed(self):
        """Same property name, different value: the Dataset row read a
        Dataset entity that is not the crate root, so the values differ and
        the nested row is not reported as already carried."""
        graph = _with_protocol(["Root step."])
        graph.insert(1, {"@id": "other", "@type": "Dataset", PROTOCOL: STEPS})
        res = map_crate(graph, [DATASET_ROW, NESTED_ROW], self.sv, "TEST")
        self.assert_one_object_per_item(res)
        self.assertEqual(self.status(res, NESTED_ROW["D4D_Full_Path"]).status,
                         "unplaceable")
        detail = self.status(res, NESTED_ROW["D4D_Full_Path"]).detail
        self.assertIn("the same crate property with a different value", detail)  # #3270
        self.assertNotIn("another crate property", detail)

    def test_crate_property_reads_both_spellings_as_one(self):
        self.assertEqual(crate_property(DATASET_ROW["RO_Crate_JSON_Path"]), PROTOCOL)
        self.assertEqual(crate_property(PROTOCOL), PROTOCOL)
        self.assertIsNone(crate_property("N/A"))
        self.assertNotEqual(
            crate_property("@graph[?@type='Dataset']['additionalProperty'][?name='A']['value']"),
            crate_property("@graph[?@type='Dataset']['additionalProperty'][?name='B']['value']"))

    def test_the_report_counts_rows_slots_and_the_id_apart(self):
        res = map_crate(_with_protocol(), self.rows, self.sv, "TEST")
        res.validation = "PASS"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            text = path.read_text(encoding="utf-8")
        filled = res.counts()["filled"]
        self.assertIn(f"({len(self.rows)} table rows applied, plus the record's "
                      "`id`, taken from the crate root)", text)
        self.assertIn(f"- Distinct top-level `Dataset` slots filled: {len(res.record)} "
                      f"(from {filled} filled rows, the `id` among them)", text)
        self.assertIn(f"| filled | {filled} | ", text)
        self.assertIn("| subsumed | 1 | ", text)
        self.assertRegex(text, r"\| PreprocessingStrategy\.description \| subsumed \|")
        self.assertNotIn("rows applied)", text.replace("taken from the crate root)", ""))


    def test_the_report_counts_slots_apart_from_rows_when_they_differ(self):
        """#3242: two nested rows filling one host with no Dataset row for it are
        two filled rows but one top-level slot, and the report says so."""
        rows = [NESTED_ROW, _row("PreprocessingStrategy.name", "name")]
        res = map_crate(_with_protocol(), rows, self.sv, "TEST")
        res.validation = "PASS"
        filled = res.counts()["filled"]
        slots = len([k for k, v in res.record.items() if v not in (None, "", [], {})])
        self.assertLess(slots, filled)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            text = path.read_text(encoding="utf-8")
        self.assertIn(f"- Distinct top-level `Dataset` slots filled: {slots} "
                      f"(from {filled} filled rows, the `id` among them)", text)


    def _report(self, res):
        res.validation = "PASS"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            return path.read_text(encoding="utf-8")

    def test_the_legend_counts_merge_undecided_rows_apart(self):
        """#3258: a row refused only because merging is undecided does have a
        route into the record, so the legend must not call every unplaceable
        row routeless; with none such, the legend is unchanged."""
        other = _row("PreprocessingStrategy.description", "rai:dataBiases")
        unrouted = _row("NoSuchClass.description", PROTOCOL)
        res = map_crate(_with_protocol(), [DATASET_ROW, other, unrouted],
                        self.sv, "TEST")
        self.assertEqual(res.counts()["unplaceable"], 2)
        self.assertTrue(self.status(res, other["D4D_Full_Path"]).merge_undecided)
        self.assertFalse(self.status(res, "NoSuchClass.description").merge_undecided)
        self.assertIn("| unplaceable | 2 | no route into a `Dataset` record; 1 of "
                      "them do resolve, but a `Dataset` row already filled the "
                      "host slot, from another crate property or from the same "
                      "property with a different value, and merging the two is "
                      "not decided |", self._report(res))
        res = map_crate(_with_protocol(), [DATASET_ROW, unrouted], self.sv, "TEST")
        self.assertIn("| unplaceable | 1 | no route into a `Dataset` record |",
                      self._report(res))


def _with_identifier(identifier):
    graph = copy.deepcopy(GRAPH)
    graph[1]["identifier"] = identifier
    return graph


def _write_cp1252_crate(project_dir: Path) -> Path:
    """A crate whose JSON is windows-1252, as the AI_READI crate's is: the
    copyright sign is byte 0xa9, which is not UTF-8 (#2969)."""
    graph = copy.deepcopy(GRAPH)
    graph[1]["copyrightNotice"] = "\u00a9 2025 Test"
    path = project_dir / "raw" / "ro-crate-metadata.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(json.dumps({"@graph": graph}, ensure_ascii=False)
                     .encode("cp1252"))
    return path


class TestCrateEncoding(unittest.TestCase):
    """#2969. A crate that is not UTF-8 raised a bare UnicodeDecodeError that
    ended the run at the first such project."""

    def test_a_non_utf8_crate_is_refused_by_name_and_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_cp1252_crate(Path(tmp) / "TEST")
            offset = path.read_bytes().index(b"\xa9")
            with self.assertRaises(CrateEncodingError) as cm:
                read_crate_json(path)
        message = str(cm.exception)
        self.assertIn(f"{path} is not UTF-8", message)
        self.assertIn(f"byte 0xa9 at offset {offset}, 1 undecodable byte(s)", message)
        self.assertIsInstance(cm.exception.__cause__, UnicodeDecodeError)

    def test_the_count_is_of_bytes_across_the_whole_file(self):
        """#3375. With one bad byte a constant 1, or the first error's length,
        reads right. Here the first error is one byte (0xa9), a later one is a
        truncated two-byte sequence (0xe2 0x82: one decoding error, two bytes)
        and a third is a lone 0x97: 4 bytes in 3 errors, so a constant, the
        first error's length and a count of decoding errors all read wrong."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ro-crate-metadata.json"
            graph = copy.deepcopy(GRAPH)
            graph[1]["copyrightNotice"] = "@A@ 2025 @B@ Test @C@"
            data = (json.dumps({"@graph": graph}).encode("ascii")
                    .replace(b"@A@", b"\xa9")
                    .replace(b"@B@", b"\xe2\x82")
                    .replace(b"@C@", b"\x97"))
            path.write_bytes(data)
            offset = data.index(b"\xa9")
            with self.assertRaises(CrateEncodingError) as cm:
                read_crate_json(path)
        self.assertIn(f"byte 0xa9 at offset {offset}, 4 undecodable byte(s)",
                      str(cm.exception))

    def test_a_utf8_crate_parses_as_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ro-crate-metadata.json"
            path.write_text(json.dumps({"@graph": GRAPH}, ensure_ascii=False),
                            encoding="utf-8")
            self.assertEqual(read_crate_json(path), {"@graph": GRAPH})

    def test_map_project_refuses_before_writing_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_cp1252_crate(Path(tmp) / "TEST")
            offset = path.read_bytes().index(b"\xa9")
            with self.assertRaises(CrateEncodingError) as cm:
                map_project("TEST", Path(tmp), sv=SchemaView(str(FULL_SCHEMA)),
                            rows=[])
            self.assertFalse((Path(tmp) / "TEST" / "processed").exists())
        # Word for word as before `read_crate_json` took a hint for the
        # routes that read a crate from any path: this arm reads a project's
        # crate, so its refusal points to the project's note (#4192).
        self.assertEqual(str(cm.exception), (
            f"{path} is not UTF-8, as RFC 8259 requires of JSON: byte 0xa9 at "
            f"offset {offset}, 1 undecodable byte(s) in all. Not decoded under "
            "a guessed encoding; declare or transcode it deliberately (see the "
            "project's `encoding_note` in crate_manifest.yaml)"))

    def test_the_map_command_reports_the_crate_and_maps_the_next(self):
        """The loop caught only FileNotFoundError, so no project after the
        undecodable one was mapped."""
        from click.testing import CliRunner
        from data_sheets_schema.cli.rocrate import rocrate
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_cp1252_crate(root / "AI_READI")
            good = root / "CHORUS" / "raw" / "ro-crate-metadata.json"
            good.parent.mkdir(parents=True)
            good.write_text(json.dumps({"@graph": GRAPH}), encoding="utf-8")
            r = CliRunner().invoke(rocrate, [
                "map", "--project", "AI_READI", "--project", "CHORUS",
                "--packages-dir", str(root)])
            self.assertIsInstance(r.exception, SystemExit, r.output)   # not a crash
            self.assertEqual(r.exit_code, 1, r.output)      # the refusal is a failure
            self.assertIn("AI_READI/raw/ro-crate-metadata.json is not UTF-8", r.output)
            self.assertTrue((root / "CHORUS" / "processed"
                             / "CHORUS_crate_mapped_d4d.yaml").exists(), r.output)
            self.assertFalse((root / "AI_READI" / "processed").exists())
            # CHORUS validates; the refusal is not called a validation failure (#3359)
            self.assertIn("✓ validation: PASS", r.output)
            self.assertIn("❌ 1 crate(s) refused (missing or unreadable), "
                          "0 validation failure(s)", r.output)


class TestFilledRowNotes(unittest.TestCase):
    """#3191. The report showed a filled row's value alone, hiding the note
    saying what was done to the crate's value, and the join note counted the
    joined string's characters as its items."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def test_a_join_counts_the_items_not_the_characters(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        field = next(f for f in res.fields if f.d4d_path == "Dataset.created_by")
        self.assertEqual(field.value_preview, "Ada Lovelace; Alan Turing")
        self.assertEqual(field.detail, "joined 2 list items")

    def cells(self, graph):
        res = map_crate(graph, self.rows, self.sv, "TEST")
        res.validation = "PASS"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            text = path.read_text(encoding="utf-8")
        return {line.split(" | ", 1)[0][2:]: line.rstrip(" |").rsplit(" | ", 1)[1]
                for line in text.splitlines() if " | filled | " in line}

    def test_a_filled_row_shows_its_note_beside_the_value(self):
        graph = copy.deepcopy(GRAPH)
        graph[1]["datePublished"] = "2026-04-03"
        cells = self.cells(graph)
        self.assertEqual(cells["Dataset.created_by"],
                         "Ada Lovelace; Alan Turing — joined 2 list items")
        self.assertEqual(cells["Dataset.issued"],
                         "2026-04-03T00:00:00Z — date -> date-time")
        self.assertEqual(cells["Dataset.known_biases"],
                         '[{"name": "Sampling bias: clinic-recruited cohort."}] — '
                         "string -> DatasetBias.name; wrapped scalar into a list")
        # A value placed as the crate holds it carries no note.
        self.assertEqual(cells["Dataset.title"], "Test Crate")


class TestDatesInAOneItemList(unittest.TestCase):
    """#4109. `_coerce` applied its date rule before the cardinality step
    unwrapped a one-item list, and the rule passes a list through unchanged:
    `["2026-06-30"]` was written as a date into the date-time slot `issued`,
    which fails the schema, and `["9/1/2022"]` was written as it stands, past
    the refusal its scalar form gets."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def map_issued(self, value):
        graph = copy.deepcopy(GRAPH)
        graph[1]["datePublished"] = value
        return map_crate(graph, self.rows, self.sv, "TEST")

    def issued(self, value):
        """`(issued, status, detail)` for a crate root with `datePublished:
        value`; `issued` is None where nothing was written."""
        res = self.map_issued(value)
        field = next(f for f in res.fields if f.d4d_path == "Dataset.issued")
        return res.record.get("issued"), field.status, field.detail

    def test_a_date_in_a_one_item_list_is_widened_to_a_date_time(self):
        self.assertEqual(self.issued(["2026-06-30"]),
                         ("2026-06-30T00:00:00Z", "filled",
                          "unwrapped single-item list; date -> date-time"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapped_d4d.yaml"
            path.write_text(yaml.safe_dump(self.map_issued(["2026-06-30"]).record,
                                           sort_keys=False, allow_unicode=True),
                            encoding="utf-8")
            self.assertEqual(validate(path), "PASS")

    def test_an_ambiguous_date_in_a_one_item_list_is_refused_as_the_scalar_is(self):
        refused = (None, "empty",
                   "ambiguous date '9/1/2022': both components are <= 12, so "
                   "DD/MM and MM/DD cannot be distinguished; dropped rather than "
                   "guessed")
        self.assertEqual(self.issued(["9/1/2022"]), refused)
        self.assertEqual(self.issued("9/1/2022"), refused)

    def test_a_scalar_date_is_widened_with_no_unwrap_note(self):
        """The control: the scalar form was already right."""
        self.assertEqual(self.issued("2026-06-30"),
                         ("2026-06-30T00:00:00Z", "filled", "date -> date-time"))

    def test_two_dates_are_not_unwrapped_as_one(self):
        """Only a one-item list is unwrapped before the date rule. What a
        single-valued date slot should do with two dates is a decision this
        fix does not make (#4144): refuse them, or keep the first and report
        the rest. Under either, `(issued, status, detail)` differs from the
        first date's alone, so the first date is never passed off as the
        list's only value, with the unwrap note or silently (#4154)."""
        two = self.issued(["2026-06-30", "2026-07-01"])
        self.assertNotIn("unwrapped single-item list", two[2])
        self.assertNotEqual(two, self.issued("2026-06-30"))

    def test_a_one_item_list_whose_item_is_not_text_is_left_to_the_cardinality_step(self):
        """The date rule reads text only, so the date branch unwraps a
        one-item list only when its item is text (#4154). Any other item is
        unwrapped once by the cardinality step, and the row is the one
        origin/main (`ba223f894`) wrote: `[null]` keeps its unwrap note
        rather than giving an empty row with no reason, and a nested list
        carries the note once rather than being unwrapped twice into a date
        the rule never read. These rows are pinned as unchanged, not as
        right: the nested list is still written as a list, which fails
        validation, and `[null]`'s detail names the unwrap, not the null.
        Neither is #4109's to change."""
        self.assertEqual(self.issued([None]),
                         (None, "empty", "unwrapped single-item list"))
        self.assertEqual(self.issued([["2026-06-30"]]),
                         (["2026-06-30"], "filled", "unwrapped single-item list"))

    def test_the_doi_and_class_range_rows_keep_their_one_item_list_details(self):
        """The unwrap is in the date branch, not hoisted, so a one-item list
        in the `doi` row and in a single-valued class-range row keeps its
        detail: the `doi` rule takes its one DOI from the list itself, and a
        class-range slot is shaped before the list is unwrapped, so its
        unwrap note still comes last, once. The enum rule's notes are not
        checked here: #4145 will change them."""
        graph = copy.deepcopy(GRAPH)
        graph[1]["identifier"] = ["https://doi.org/10.5555/Test"]
        graph[1]["rai:dataReleaseMaintenancePlan"] = ["Released annually."]
        details = {f.d4d_path: f.detail
                   for f in map_crate(graph, self.rows, self.sv, "TEST").fields}
        self.assertEqual(details["Dataset.doi"],
                         "the one DOI among 1 list item(s); resolver or `doi:` "
                         "prefix removed, case kept")
        updates = details["Dataset.updates"]
        self.assertTrue(updates.endswith("; unwrapped single-item list"), updates)
        self.assertEqual(updates.count("unwrapped single-item list"), 1, updates)


class TestDoi(unittest.TestCase):
    """#2916. The `doi` pattern is anchored to the bare DOI (#646) and crates
    carry the resolver URL; copying it through failed the schema while the
    provenance report still said PASS."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()
        # The slot's own declared pattern, as `_coerce` passes it.
        cls.pattern = cls.sv.induced_slot("doi", "Dataset").pattern

    def doi_field(self, res):
        return next(f for f in res.fields if f.d4d_path == "Dataset.doi")

    def test_a_resolver_url_is_written_as_the_bare_doi_in_its_case(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        self.assertEqual(res.record["doi"], "10.5555/Test")
        self.assertEqual(self.doi_field(res).status, "filled")

    def test_a_doi_curie_identifier_maps_to_the_same_record(self):
        res = map_crate(_with_identifier("doi:10.5555/Test"),
                        self.rows, self.sv, "TEST")
        self.assertEqual(res.record["doi"], "10.5555/Test")
        self.assertEqual(res.record["id"], "doi:10.5555/Test")

    def test_a_non_doi_identifier_writes_no_doi_and_says_why(self):
        res = map_crate(_with_identifier("ark:59853/other"),
                        self.rows, self.sv, "TEST")
        self.assertNotIn("doi", res.record)
        field = self.doi_field(res)
        self.assertEqual(field.status, "empty")
        self.assertIn("not a DOI", field.detail)
        # The id is not a DOI either, so it stays as the crate wrote it.
        self.assertEqual(res.record["id"], "ark:59853/other")

    def test_a_list_gives_up_its_one_doi(self):
        value, note = doi_for_slot(["ark:59853/other",
                                    "https://doi.org/10.5555/Test",
                                    "doi:10.5555/Test"], self.pattern)
        self.assertEqual(value, "10.5555/Test")
        self.assertIn("one DOI among 3", note)

    def test_two_different_dois_give_none_and_neither_is_chosen(self):
        res = map_crate(_with_identifier(["https://doi.org/10.5555/Test",
                                          "https://doi.org/10.5555/Other"]),
                        self.rows, self.sv, "TEST")
        self.assertNotIn("doi", res.record)
        field = self.doi_field(res)
        self.assertEqual(field.status, "empty")
        self.assertIn("2 distinct DOIs", field.detail)

    def test_a_bare_doi_passes_through_with_no_note(self):
        self.assertEqual(doi_for_slot("10.5555/Test", self.pattern),
                         ("10.5555/Test", ""))

    def test_case_variants_of_one_doi_are_one_doi_and_the_first_is_kept(self):
        """#2987. DOIs are case-insensitive, so two spellings that differ only
        in case name one DOI: the slot is filled, not emptied as '2 distinct
        DOIs'. The first spelling is written, in its own case."""
        for identifier, expected in (
                (["https://doi.org/10.18130/V3/HIGT4C", "doi:10.18130/v3/higt4c"],
                 "10.18130/V3/HIGT4C"),
                (["doi:10.18130/v3/higt4c", "https://doi.org/10.18130/V3/HIGT4C"],
                 "10.18130/v3/higt4c")):
            with self.subTest(identifier=identifier):
                res = map_crate(_with_identifier(identifier),
                                self.rows, self.sv, "TEST")
                self.assertEqual(res.record.get("doi"), expected)
                field = self.doi_field(res)
                self.assertEqual(field.status, "filled")
                self.assertNotIn("distinct", field.detail)
                self.assertIn("2 spellings", field.detail)

    def test_a_value_the_slot_pattern_accepts_is_kept_as_written(self):
        """#2989. `bare_doi` recognises a narrower shape than the slot's
        pattern; a value the pattern already accepts is valid, so it is
        neither dropped nor trimmed."""
        for value in ("10.5555/a b", "10.1234567890/x", "10.5555/x\ty",
                      "10.5555/x/", "10.5555/x "):
            with self.subTest(value=value):
                self.assertRegex(value, self.pattern)   # the schema accepts it
                self.assertEqual(doi_for_slot(value, self.pattern), (value, ""))
        # and the arm hands the slot's own pattern to the rule
        res = map_crate(_with_identifier("10.1234567890/x"), self.rows, self.sv, "TEST")
        self.assertEqual(res.record.get("doi"), "10.1234567890/x")

    def test_a_prefixed_doi_outside_the_repaired_shape_is_dropped_not_guessed(self):
        """#2989, the narrowness that remains: a `doi:` form with a ten-digit
        registrant is not one the repair recognises, and the reason says so
        rather than that it is not a DOI at all."""
        value, why = doi_for_slot("doi:10.1234567890/x", self.pattern)
        self.assertIsNone(value)
        self.assertIn("the slot accepts as written or the repair recognises", why)

    def test_the_repair_note_names_only_what_came_off(self):
        """#2989. The note no longer says a prefix came off when only
        whitespace or a trailing `/` did."""
        cases = {
            "https://doi.org/10.5555/Test":
                "resolver or `doi:` prefix removed, case kept",
            " 10.5555/Test":
                "surrounding whitespace removed, case kept",
            " doi:10.5555/Test/ ":
                "resolver or `doi:` prefix, trailing `/` and surrounding "
                "whitespace removed, case kept",
        }
        for written, note in cases.items():
            with self.subTest(written=written):
                self.assertEqual(doi_for_slot(written, self.pattern),
                                 ("10.5555/Test", note))

    def report_cells(self, graph):
        """The `Value / note` cell of each filled doi or id row in the
        provenance report `write_provenance` writes for `graph`."""
        res = map_crate(graph, self.rows, self.sv, "TEST")
        res.validation = "PASS"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            text = path.read_text(encoding="utf-8")
        cells = {}
        for line in text.splitlines():
            for name in ("Dataset.doi", "Dataset.id"):
                if line.startswith(f"| {name} | filled |"):
                    cells[name] = line.rstrip(" |").rsplit(" | ", 1)[1]
        return cells

    def test_the_report_names_the_crate_value_a_doi_and_id_were_rewritten_from(self):
        """#3139. The report showed only the rewritten values, beside
        `exactMatch / none` and the crate path, as though the crate held
        them; the repair note and the id's #974 note reached no file."""
        cells = self.report_cells(GRAPH)
        self.assertEqual(
            cells["Dataset.doi"],
            "10.5555/Test — rewritten from the crate's https://doi.org/10.5555/Test: "
            "resolver or `doi:` prefix removed, case kept")
        self.assertEqual(
            cells["Dataset.id"],
            "doi:10.5555/Test — rewritten from the crate's https://doi.org/10.5555/Test: "
            "required by the schema; taken from the crate itself; "
            "a DOI is written as the doi: CURIE (#974)")

    def test_the_report_claims_no_rewrite_where_the_crate_value_was_kept(self):
        """A value written as the crate holds it is shown alone: the bare DOI
        in `doi`, and the `doi:` CURIE in `id`. Each form rewrites only the
        other slot."""
        bare = self.report_cells(_with_identifier("10.5555/Test"))
        self.assertEqual(bare["Dataset.doi"], "10.5555/Test")
        self.assertEqual(bare["Dataset.id"],
                         "doi:10.5555/Test — rewritten from the crate's 10.5555/Test: "
                         "required by the schema; taken from the crate itself; "
                         "a DOI is written as the doi: CURIE (#974)")
        curie = self.report_cells(_with_identifier("doi:10.5555/Test"))
        self.assertEqual(curie["Dataset.id"], "doi:10.5555/Test")
        self.assertEqual(curie["Dataset.doi"],
                         "10.5555/Test — rewritten from the crate's doi:10.5555/Test: "
                         "resolver or `doi:` prefix removed, case kept")
        # An identifier that is not a DOI fills no doi row, and the id is
        # written as the crate wrote it.
        ark = self.report_cells(_with_identifier("ark:59853/other"))
        self.assertEqual(ark, {"Dataset.id": "ark:59853/other"})

    def test_an_id_taken_from_a_list_names_the_whole_list(self):
        """The id row names what the crate holds at its path, the list, and
        says which item it took, whether or not that item is a DOI."""
        both = ["https://doi.org/10.5555/Test", "https://doi.org/10.5555/Other"]
        cells = self.report_cells(_with_identifier(both))
        self.assertEqual(
            cells["Dataset.id"],
            'doi:10.5555/Test — rewritten from the crate\'s ["https://doi.org/10.5555/Test", '
            '"https://doi.org/10.5555/Other"]: required by the schema; taken from the '
            "crate itself; the first of 2 list item(s); a DOI is written as the doi: "
            "CURIE (#974)")
        self.assertNotIn("Dataset.doi", cells)   # two DOIs: the slot stays empty
        ark = self.report_cells(_with_identifier(["ark:59853/other"]))
        self.assertEqual(ark["Dataset.id"],
                         'ark:59853/other — rewritten from the crate\'s ["ark:59853/other"]: '
                         "required by the schema; taken from the crate itself; "
                         "the first of 1 list item(s)")

    def test_a_list_names_the_crate_list_it_gave_its_doi_up_from(self):
        res = map_crate(_with_identifier(["ark:59853/other",
                                          "https://doi.org/10.5555/Test"]),
                        self.rows, self.sv, "TEST")
        field = self.doi_field(res)
        self.assertEqual(field.value_preview, "10.5555/Test")
        self.assertEqual(field.rewritten_from,
                         '["ark:59853/other", "https://doi.org/10.5555/Test"]')
        self.assertIn("one DOI among 2", field.detail)

    def test_a_slot_that_declares_no_pattern_takes_only_the_bare_doi(self):
        self.assertEqual(doi_for_slot("https://doi.org/10.5555/x", None)[0],
                         "10.5555/x")
        self.assertIsNone(doi_for_slot("10.5555/a b", None)[0])

    def test_the_mapped_record_validates_against_the_schema(self):
        """The check test_map.py never made: the mapper's output is judged by
        the schema it claims to target, not only by its shape."""
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapped_d4d.yaml"
            path.write_text(yaml.safe_dump(res.record, sort_keys=False,
                                           allow_unicode=True), encoding="utf-8")
            self.assertEqual(validate(path), "PASS")


class TestVerdictBasis(unittest.TestCase):
    """#2916. A verdict names the schema it was reached against, so a later
    schema change leaves a PASS that says which schema it was about."""

    def test_the_basis_names_version_hash_and_date(self):
        basis = verdict_basis(FULL_SCHEMA, on="2026-09-28")
        self.assertRegex(basis, r"^schema \d+\.\d+\.\d+ / ")
        self.assertIn(f"sha256 {sha256_of(FULL_SCHEMA)}", basis)
        self.assertIn("/ 2026-09-28 ", basis)
        self.assertIn(str(FULL_SCHEMA), basis)

    def test_the_provenance_report_writes_it_beside_the_verdict(self):
        res = MapResult(project="TEST", validation="PASS")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            line = next(l for l in path.read_text(encoding="utf-8").splitlines()
                        if l.startswith("- Validation:"))
        self.assertTrue(line.startswith("- Validation: **PASS** — schema "), line)
        self.assertIn(f"sha256 {sha256_of(FULL_SCHEMA)}", line)
        self.assertRegex(line, r" / \d{4}-\d{2}-\d{2} ")


if __name__ == "__main__":
    unittest.main()
