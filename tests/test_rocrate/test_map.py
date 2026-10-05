"""Tests for the our-mapping crate → D4D arm."""

import contextlib
import copy
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from linkml_runtime import SchemaView

from data_sheets_schema.rocrate_map import (
    FULL_SCHEMA,
    GRAPH_RE,
    UNPLACED_KINDS,
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


#: #4168: a value in either date form that is no calendar date, and why.
#: Year 0000 is no year: `datetime.date` starts at 0001, and the schema's
#: date-time check rejects 0000 too. So `01/02/0000`, whose components are
#: both months, names no date in either order and is not ambiguous (#4183).
IMPOSSIBLE_DATES = {
    "13/13/2026": "as DD/MM/YYYY, month 13 is not in 1-12, and as MM/DD/YYYY, "
                  "month 13 is not in 1-12",
    "31/31/2026": "as DD/MM/YYYY, month 31 is not in 1-12, and as MM/DD/YYYY, "
                  "month 31 is not in 1-12",
    "12/32/2026": "as DD/MM/YYYY, month 32 is not in 1-12, and as MM/DD/YYYY, "
                  "day 32 is not in 1-31 for 2026-12",
    "31/02/2026": "as DD/MM/YYYY, day 31 is not in 1-28 for 2026-02, and as "
                  "MM/DD/YYYY, month 31 is not in 1-12",
    "0/0/2026": "as DD/MM/YYYY, month 0 is not in 1-12, and as MM/DD/YYYY, "
                "month 0 is not in 1-12",
    "01/02/0000": "as DD/MM/YYYY, year 0000 is not in 0001-9999, and as "
                  "MM/DD/YYYY, year 0000 is not in 0001-9999",
    "2026-13-45": "month 13 is not in 1-12",
    "0000-01-01": "year 0000 is not in 0001-9999",
}


def _ambiguous(text):
    return (None, f"ambiguous date {text!r}: both components are <= 12, so "
                  "DD/MM and MM/DD cannot be distinguished; dropped rather than "
                  "guessed")


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

    def test_an_impossible_date_is_not_a_calendar_date(self):
        """#4168. `datetime.date` checks a date before it is widened, and
        neither order reads any of these slash dates as one. `13/13/2026`,
        `31/31/2026` and `0/0/2026` had been called ambiguous, "both
        components are <= 12", and so, until #4183, had `01/02/0000`;
        `12/32/2026` and `31/02/2026` had been widened to date-times the
        schema rejects, as `2026-13-45` and `0000-01-01` had."""
        for text, why in IMPOSSIBLE_DATES.items():
            with self.subTest(text=text):
                self.assertEqual(_normalize_datetime(text),
                                 (None, f"not a calendar date {text!r}: {why}; dropped"))

    def test_the_calendar_decides_not_a_count_of_days(self):
        """29 February is a date in a leap year only, and the leap years
        are the Gregorian calendar's (#4197): 1900 is not one, though four
        divides it, and 2000 is, since 400 divides it. A rule that counts
        every fourth year keeps 1900's, and one that also leaves out every
        hundredth refuses 2000's; the schema's date-time check does
        neither."""
        self.assertEqual(_normalize_datetime("29/02/2024"),
                         ("2024-02-29T00:00:00Z", "DD/MM/YYYY -> date-time"))
        self.assertEqual(_normalize_datetime("2024-02-29"),
                         ("2024-02-29T00:00:00Z", "date -> date-time"))
        self.assertEqual(
            _normalize_datetime("02/29/2026"),
            (None, "not a calendar date '02/29/2026': as DD/MM/YYYY, month 29 is "
                   "not in 1-12, and as MM/DD/YYYY, day 29 is not in 1-28 for "
                   "2026-02; dropped"))
        self.assertEqual(
            _normalize_datetime("2026-02-29"),
            (None, "not a calendar date '2026-02-29': day 29 is not in 1-28 for "
                   "2026-02; dropped"))
        self.assertEqual(
            _normalize_datetime("1900-02-29"),
            (None, "not a calendar date '1900-02-29': day 29 is not in 1-28 for "
                   "1900-02; dropped"))
        self.assertEqual(
            _normalize_datetime("29/02/1900"),
            (None, "not a calendar date '29/02/1900': as DD/MM/YYYY, day 29 is "
                   "not in 1-28 for 1900-02, and as MM/DD/YYYY, month 29 is not "
                   "in 1-12; dropped"))
        self.assertEqual(_normalize_datetime("2000-02-29"),
                         ("2000-02-29T00:00:00Z", "date -> date-time"))
        self.assertEqual(_normalize_datetime("29/02/2000"),
                         ("2000-02-29T00:00:00Z", "DD/MM/YYYY -> date-time"))

    def test_ambiguous_means_both_orders_read_a_date(self):
        """The ambiguity reason is kept where it is true: both orders read
        a calendar date, so both components are months, the edges 1 and 12
        included. A 0 is neither a day nor a month, in either position, so
        a slash date with one is not a calendar date in either order. Nor
        are two months in year 0000 (#4183), which `IMPOSSIBLE_DATES`
        covers."""
        for text in ("03/04/2026", "1/12/2026", "12/1/2026", "01/02/0001"):
            with self.subTest(text=text):
                self.assertEqual(_normalize_datetime(text), _ambiguous(text))
        cases = {
            "0/12/2026": "as DD/MM/YYYY, day 0 is not in 1-31 for 2026-12, and as "
                         "MM/DD/YYYY, month 0 is not in 1-12",
            "12/0/2026": "as DD/MM/YYYY, month 0 is not in 1-12, and as "
                         "MM/DD/YYYY, day 0 is not in 1-31 for 2026-12",
            "5/0/2026": "as DD/MM/YYYY, month 0 is not in 1-12, and as "
                        "MM/DD/YYYY, day 0 is not in 1-31 for 2026-05",
        }
        for text, why in cases.items():
            with self.subTest(text=text):
                self.assertEqual(_normalize_datetime(text),
                                 (None, f"not a calendar date {text!r}: {why}; dropped"))

    def test_a_valid_date_resolves_as_before(self):
        """A date with one reading keeps its value and its note: the order
        that reads it is the one whose month is in 1-12."""
        cases = {
            "2026-04-03": ("2026-04-03T00:00:00Z", "date -> date-time"),
            " 2026-04-03 ": ("2026-04-03T00:00:00Z", "date -> date-time"),
            "12/16/2025": ("2025-12-16T00:00:00Z", "MM/DD/YYYY -> date-time"),
            "16/12/2025": ("2025-12-16T00:00:00Z", "DD/MM/YYYY -> date-time"),
            "1/31/2026": ("2026-01-31T00:00:00Z", "MM/DD/YYYY -> date-time"),
            "31/1/2026": ("2026-01-31T00:00:00Z", "DD/MM/YYYY -> date-time"),
            "13/12/2026": ("2026-12-13T00:00:00Z", "DD/MM/YYYY -> date-time"),
            "12/13/2026": ("2026-12-13T00:00:00Z", "MM/DD/YYYY -> date-time"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(_normalize_datetime(text), expected)


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
        """Every row placed nowhere says why, the table's own reason with
        the schema's. None has to be unplaceable: a table whose every row
        places passes too (#2915)."""
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        declared = {row["D4D_Full_Path"].strip(): row for row in self.rows}
        for f in res.fields:
            if f.status != "unplaceable":
                continue
            with self.subTest(row=f.d4d_path):
                self.assertTrue(f.detail)
                row = declared[f.d4d_path]
                self.assertEqual(f.unplaced, row["Unplaced"].strip())
                self.assertIn(row["Unplaced_Reason"].strip(), f.detail)


def unplaced_problems(rows, sv):
    """`(d4d path, problem)` for each table row the schema contradicts.

    A row's D4D path is judged by the placement `map_crate` applies, run on
    a crate with nothing in it, where a row is `unplaceable` only because
    its path places nowhere in a `Dataset` record. Such a row must say why
    in the table's `Unplaced` column (an `UNPLACED_KINDS` key) and
    `Unplaced_Reason`; a row that places must say neither, or the report
    would call a placed row unplaced (#2915)."""
    fields = [f for f in map_crate([], rows, sv, "TABLE").fields if f.from_table]
    problems = []
    for row, field in zip(rows, fields, strict=True):
        kind = (row.get("Unplaced") or "").strip()
        reason = (row.get("Unplaced_Reason") or "").strip()
        if field.status != "unplaceable":
            if kind or reason:
                problems.append((field.d4d_path, "places, but the table "
                                 "declares it unplaced"))
        elif not kind:
            problems.append((field.d4d_path, "places nowhere, and the table "
                             f"does not say why: {field.detail}"))
        elif kind not in UNPLACED_KINDS:
            problems.append((field.d4d_path, f"declares {kind!r}, which is "
                             f"not one of {sorted(UNPLACED_KINDS)}"))
        elif not reason:
            problems.append((field.d4d_path, f"declares {kind!r} with no reason"))
    return problems


class TestTableAgainstSchema(unittest.TestCase):
    """#2915. 54 of the table's 136 rows named a slot or class the schema
    does not have, and `map_crate` dropped every value they read, `exactMatch`
    rows included, with nothing to say the table was wrong. Every row's D4D
    path is now judged against the merged schema: it places in a `Dataset`
    record, or the table says why it does not."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def row(self, path):
        return next(r for r in self.rows if r["D4D_Full_Path"].strip() == path)

    def test_every_row_places_or_the_table_says_why(self):
        self.assertEqual([], unplaced_problems(self.rows, self.sv))

    def test_the_guard_fails_a_stale_name_restored(self):
        """The pre-#2915 form of one row: the slot the schema renamed."""
        rows = copy.deepcopy(self.rows)
        stale = next(r for r in rows
                     if r["D4D_Full_Path"].strip() == "Dataset.at_risk_populations")
        stale["D4D_Full_Path"] = "Dataset.vulnerable_populations"
        self.assertEqual(unplaced_problems(rows, self.sv), [(
            "Dataset.vulnerable_populations", "places nowhere, and the table "
            "does not say why: 'vulnerable_populations' is not a slot on Dataset")])

    def test_the_guard_fails_a_declaration_on_a_row_that_places(self):
        """A retargeted row that kept its declaration would be reported
        unplaced while it places."""
        for kind, reason in (("out_of_scope", "a reason"), ("", "a reason"),
                             ("owner_question", "")):
            rows = copy.deepcopy(self.rows)
            title = next(r for r in rows if r["D4D_Full_Path"].strip() == "Dataset.title")
            title["Unplaced"], title["Unplaced_Reason"] = kind, reason
            with self.subTest(kind=kind, reason=reason):
                self.assertEqual(unplaced_problems(rows, self.sv), [(
                    "Dataset.title", "places, but the table declares it unplaced")])

    def test_the_guard_fails_a_declaration_with_no_kind_it_knows_or_no_reason(self):
        for kind, reason, problem in (
                ("wontfix", "a reason", "declares 'wontfix', which is not one of "
                 f"{sorted(UNPLACED_KINDS)}"),
                ("out_of_scope", " ", "declares 'out_of_scope' with no reason"),
                ("", "a reason", "places nowhere, and the table does not say why: "
                 "'bytes' is not a slot on Dataset")):
            rows = copy.deepcopy(self.rows)
            row = next(r for r in rows if r["D4D_Full_Path"].strip() == "Dataset.bytes")
            row["Unplaced"], row["Unplaced_Reason"] = kind, reason
            with self.subTest(kind=kind, reason=reason):
                self.assertEqual(unplaced_problems(rows, self.sv),
                                 [("Dataset.bytes", problem)])

    def test_the_retargeted_rows_place_the_crate_values_they_read(self):
        """A crate holding each property a retargeted row reads fills the
        slot the schema now has for it, and the record validates. The two
        nested rows read the property a `Dataset` row already placed, so
        they are subsumed, not placed twice. The governance row is not
        retargeted: every crate's `dataGovernanceCommittee` names a person, so
        it stays unplaceable as an owner question and writes nothing."""
        graph = copy.deepcopy(GRAPH)
        graph[1].update({
            "d4d:atRiskPopulations": "No minors enrolled.",
            "relatedLink": "https://example.org/related",
            "rai:machineAnnotationTools": ["OpenSMILE 3.0", "Praat 6.4"],
            "dataGovernanceCommittee": "Jane Doe",
            "rai:dataReleaseMaintenancePlan": "Released annually.",
        })
        res = map_crate(graph, self.rows, self.sv, "TEST")
        record = res.record
        self.assertEqual(record["at_risk_populations"], {"name": "No minors enrolled."})
        self.assertEqual(record["external_resources"],
                         [{"name": "https://example.org/related"}])
        self.assertEqual(record["machine_annotation_tools"],
                         [{"name": "OpenSMILE 3.0"}, {"name": "Praat 6.4"}])
        self.assertNotIn("data_governance", record)
        status = {f.d4d_path: f.status for f in res.fields}
        self.assertEqual(status["MachineAnnotationTools.tools"], "subsumed")
        self.assertEqual(status["UpdatePlan.frequency"], "subsumed")
        self.assertEqual(status["DatasetCollection.data_governance_committee"], "unplaceable")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapped_d4d.yaml"
            path.write_text(yaml.safe_dump(record, sort_keys=False,
                                           allow_unicode=True), encoding="utf-8")
            self.assertEqual(validate(path), "PASS")

    def test_the_report_says_what_the_table_declares(self):
        res = map_crate(GRAPH, self.rows, self.sv, "TEST")
        res.validation = "PASS"
        field = next(f for f in res.fields if f.d4d_path == "Dataset.bytes")
        self.assertEqual(field.unplaced, "out_of_scope")
        self.assertEqual(field.detail, "'bytes' is not a slot on Dataset; out of "
                         "scope, as the table declares: "
                         + self.row("Dataset.bytes")["Unplaced_Reason"].strip())
        field = next(f for f in res.fields if f.d4d_path == "EthicalReview.irb_id")
        self.assertIn("awaiting an owner's decision, as the table declares: "
                      "Left as it is pending #4043", field.detail)
        kinds = [r["Unplaced"].strip() for r in self.rows if r["Unplaced"].strip()]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapping_provenance.md"
            write_provenance(res, path, Path("crate/ro-crate-metadata.json"))
            text = path.read_text(encoding="utf-8")
        legend = next(line for line in text.splitlines()
                      if line.startswith("| unplaceable | "))
        self.assertTrue(legend.startswith(
            f"| unplaceable | {res.counts()['unplaceable']} | no route into a "
            "`Dataset` record"), legend)
        self.assertTrue(legend.endswith(
            f"; the mapping table says why for {len(kinds)} of them: "
            f"{kinds.count('out_of_scope')} out of scope, "
            f"{kinds.count('owner_question')} awaiting an owner's decision |"), legend)
        self.assertRegex(text, r"\| Dataset\.bytes \| unplaceable \| .* out of "
                               r"scope, as the table declares: `bytes` is a `File` slot")


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

    def test_an_impossible_date_is_refused_alone_and_in_a_one_item_list(self):
        """#4168. The row is empty, with the reason that the value is not a
        calendar date, whether the crate writes it alone or as the one item
        of a list."""
        for text, why in IMPOSSIBLE_DATES.items():
            refused = (None, "empty", f"not a calendar date {text!r}: {why}; dropped")
            with self.subTest(text=text):
                self.assertEqual(self.issued(text), refused)
                self.assertEqual(self.issued([text]), refused)

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

    def test_a_one_item_list_of_null_or_of_a_list_gets_a_row_naming_it(self):
        """#4164. Neither reaches the date rule. `[null]` is no value, and
        the reason names the null; its row had named only the unwrap. A
        list inside a list is refused, not flattened: the cardinality step
        had unwrapped it once and written `['2026-06-30']` into this
        single-valued slot, which fails validation. The date rule never
        read the inner value, so `[["9/1/2022"]]` was never called
        ambiguous either. #4154 had pinned those rows as unchanged, not as
        right."""
        self.assertEqual(self.issued([None]),
                         (None, "empty", "no value: the list holds only null ([null])"))
        for value in ([["2026-06-30"]], [["9/1/2022"]]):
            with self.subTest(value=value):
                self.assertEqual(self.issued(value), (
                    None, "empty",
                    "a list inside a list, for a slot that holds one value: "
                    f"{json.dumps(value)}; dropped rather than flattened"))

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


#: A crate root holding nothing a table row reads.
BARE_ROOT = {"@id": "ark:59853/thing",
             "@type": ["https://w3id.org/EVI#Dataset", "https://w3id.org/EVI#ROCrate"]}

#: One table row for each kind of slot `_coerce` fills: text, a list of text,
#: a date-time, the doi, an enum, a list of objects, one object, an integer,
#: a boolean, a uri, a uriorcurie, and text in a nested class's object.
ONE_ROW_OF_EACH_KIND = {
    "Dataset.title", "Dataset.keywords", "Dataset.issued", "Dataset.doi",
    "Dataset.compression", "Dataset.creators", "Dataset.updates",
    "Dataset.total_size_bytes", "Dataset.is_tabular", "Dataset.download_url",
    "Dataset.publisher", "PreprocessingStrategy.description",
}


def _crate_holding(source, value):
    """A crate whose root holds `value` at the table path `source`, and
    nothing else a table row reads."""
    root = copy.deepcopy(BARE_ROOT)
    m = GRAPH_RE.match(source)
    if m and m.group("name"):
        root[m.group("prop")] = [{"name": m.group("name"), m.group("prop2"): value}]
    else:
        root[m.group("prop") if m else source] = value
    return [{"@id": "ro-crate-metadata.json", "@type": "CreativeWork"}, root]


class TestNullAndNestedListItems(unittest.TestCase):
    """#4164. `_coerce` read a list of null and a list inside a list as
    values. A single-valued slot's `[null]` row was `empty` with the unwrap
    as its only reason, and `[[x]]` wrote the inner list into the slot; a
    multivalued slot kept `[null]` as written; a class-range slot made
    `{name: 'None'}` or `{name: "['x']"}`; and an enum slot raised
    TypeError, which ended `map_crate`. #4183: a list that mixes values
    with lists keeps the values, and the row names each list it drops."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def rows_reading(self, value):
        """`(d4d path, status, detail, written)` for every table row that
        `_coerce` reads, each mapped alone from a crate holding `value` at
        its path. A row that cannot be placed, or declares no crate path,
        never reaches `_coerce` and is left out. `written` is the record
        without its `id`, which `map_crate` takes from the crate root and no
        table row supplies."""
        out = []
        for row in self.rows:
            graph = _crate_holding((row.get("RO_Crate_JSON_Path") or "").strip(), value)
            res = map_crate(graph, [row], self.sv, "TEST")
            field = res.fields[0]
            if field.status in ("unplaceable", "unresolvable"):
                continue
            out.append((field.d4d_path, field.status, field.detail,
                        {k: v for k, v in res.record.items() if k != "id"}))
        self.assertLessEqual(ONE_ROW_OF_EACH_KIND, {path for path, *_ in out})
        return out

    def test_a_list_of_only_null_is_no_value_in_every_row(self):
        """The row is `empty`, its reason names the null, and nothing is
        written, whatever the slot's range or cardinality."""
        for value in ([None], [None, None]):
            why = f"no value: the list holds only null ({json.dumps(value)})"
            for path, *row in self.rows_reading(value):
                with self.subTest(value=value, row=path):
                    self.assertEqual(tuple(row), ("empty", why, {}))

    def holds(self, path):
        """What the reason says the row's slot holds."""
        cls, _, slot = path.partition(".")
        return ("a list of single values"
                if self.sv.induced_slot(slot, cls).multivalued else "one value")

    def test_a_list_of_lists_is_refused_in_every_row(self):
        """Refused, not flattened, whatever the slot's range, where every
        item is a list, or a list or null: nothing is left to shape. The
        reason says which kind of slot it is: one that holds one value, or
        one that holds a list of single values."""
        for value in ([["x"]], [["x", "y"]], [None, ["x"]]):
            for path, *row in self.rows_reading(value):
                why = (f"a list inside a list, for a slot that holds "
                       f"{self.holds(path)}: {json.dumps(value)}; dropped "
                       "rather than flattened")
                with self.subTest(value=value, row=path):
                    self.assertEqual(tuple(row), ("empty", why, {}))

    def test_a_list_beside_a_value_is_dropped_and_the_value_kept_in_every_row(self):
        """#4183. Every row maps a list that mixes values with lists as it
        maps the values alone, whatever the slot's range or cardinality,
        and its detail first names each list it dropped. #4164 had refused
        the whole row, which emptied a `doi` row origin/main filled with a
        valid DOI. A null beside a value is dropped with its own note (#4172)."""
        cases = (
            (["x", ["y"]], ["x"], "1 of 2 list items is a list", '["y"]'),
            ([["y"], "x"], ["x"], "1 of 2 list items is a list", '["y"]'),
            (["x", ["y"], ["z", "w"]], ["x"],
             "2 of 3 list items are lists", '["y"], ["z", "w"]'),
            (["x", "v", ["y"]], ["x", "v"], "1 of 3 list items is a list", '["y"]'),
            (["x", None, ["y"]], ["x", None], "1 of 3 list items is a list", '["y"]'),
        )
        for value, alone, how_many, named in cases:
            rows_alone = {path: row for path, *row in self.rows_reading(alone)}
            for path, status, detail, written in self.rows_reading(value):
                status_alone, detail_alone, written_alone = rows_alone[path]
                left_out = (f"{how_many} inside the list, for a slot that holds "
                            f"{self.holds(path)}: {named}; dropped rather than "
                            "flattened")
                with self.subTest(value=value, row=path):
                    self.assertEqual((status, written), (status_alone, written_alone))
                    self.assertEqual(detail, "; ".join(
                        part for part in (left_out, detail_alone) if part))

    def keywords(self, value):
        """`(keywords, status, detail)` for the shipped table and `GRAPH`
        with `keywords: value`."""
        graph = copy.deepcopy(GRAPH)
        graph[1]["keywords"] = value
        res = map_crate(graph, self.rows, self.sv, "TEST")
        field = next(f for f in res.fields if f.d4d_path == "Dataset.keywords")
        return res.record.get("keywords"), field.status, field.detail

    def test_a_multivalued_slot_keeps_its_values_and_drops_a_list_inside(self):
        """The choice #4164 left open: a list inside the list a multivalued
        slot reads is not one of the single values the slot holds, so it is
        dropped, not flattened into the slot's list. The values beside it
        are kept (#4183), and a list of nothing but lists is refused. A list
        of single values fills the slot as before."""
        self.assertEqual(self.keywords(["voice", ["health"]]), (
            ["voice"], "filled",
            "1 of 2 list items is a list inside the list, for a slot that holds a "
            'list of single values: ["health"]; dropped rather than flattened'))
        self.assertEqual(self.keywords([["voice", "health"]]), (
            None, "empty",
            "a list inside a list, for a slot that holds a list of single values: "
            '[["voice", "health"]]; dropped rather than flattened'))
        self.assertEqual(self.keywords(["voice", "health"]),
                         (["voice", "health"], "filled", ""))

    def test_null_beside_a_value_is_dropped_before_every_rows_rules(self):
        """#4172: null must not become text, an object or a retained null.
        Zero and false are values, and a remaining date or DOI still goes
        through its own rule. A refused value retains the null detail too."""
        for item in ("voice", "2026-06-30", "9/1/2022",
                     "https://doi.org/10.5555/x", "bzip2", 0, False):
            alone = {path: row for path, *row in self.rows_reading([item])}
            for mixed in ([None, item], [item, None], [None, item, None]):
                count = len(mixed) - 1
                note = (f"{count} of {len(mixed)} list items "
                        f"{'is' if count == 1 else 'are'} null; dropped")
                for path, status, detail, written in self.rows_reading(mixed):
                    status_alone, detail_alone, written_alone = alone[path]
                    with self.subTest(row=path, value=mixed):
                        self.assertEqual((status, written), (status_alone, written_alone))
                        self.assertEqual(detail, "; ".join(
                            part for part in (note, detail_alone) if part))
        self.assertEqual(self.keywords(["voice", None]), (
            ["voice"], "filled", "1 of 2 list items is null; dropped"))


class TestEnumNonTextItems(unittest.TestCase):
    """#4173: an enum rejects objects and references without ending a map."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.rows = load_mapping()

    def test_objects_and_references_are_reported_and_permitted_text_survives(self):
        for rejected in ({"@id": "https://example.org/zip"},
                         {"@id": "x", "name": "bzip2"}, {}, 1, True):
            for value, expected in ((rejected, None), ([rejected], None),
                                    ([None, rejected], None),
                                    ([rejected, "bzip2"], "bzip2"),
                                    (["bzip2", rejected], "bzip2")):
                graph = copy.deepcopy(GRAPH)
                graph[1]["evi:formats"] = value
                res = map_crate(graph, self.rows, self.sv, "TEST")
                field = next(f for f in res.fields if f.d4d_path == "Dataset.compression")
                with self.subTest(value=value):
                    self.assertEqual(res.record.get("compression"), expected)
                    self.assertEqual(field.status, "empty" if expected is None else "filled")
                    if value == {}:
                        self.assertIn("empty or absent", field.detail)
                        continue
                    self.assertIn("non-text enum item(s)", field.detail)
                    self.assertIn(json.dumps(rejected), field.detail)
                    self.assertIn("dropped", field.detail)
                    # An unrelated row survives too: no map-wide exception.
                    self.assertEqual(res.record["title"], "Test Crate")


class TestRecordIdListItems(unittest.TestCase):
    """#4174: the required id uses the same null/nested-list refusals."""

    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))

    def mapped(self, identifier, root_id="ark:59853/thing"):
        root = {**BARE_ROOT, "@id": root_id, "identifier": identifier}
        res = map_crate([root], [], self.sv, "TEST")
        return res, next(f for f in res.fields if f.d4d_path == "Dataset.id")

    def test_null_or_nested_only_identifier_falls_back_to_root_id(self):
        for value in ([None], [None, None], [["x"]], [None, ["x"]]):
            with self.subTest(value=value):
                res, field = self.mapped(value)
                self.assertEqual(res.record, {"id": "ark:59853/thing"})
                self.assertEqual(field.status, "filled")
                self.assertFalse(field.from_table)
                self.assertIn("identifier:", field.detail)
                self.assertIn(json.dumps(value), field.detail)
                self.assertIn("fell back to @id", field.detail)

    def test_mixed_identifier_keeps_first_remaining_item_and_its_original_preview(self):
        for value in ([None, "https://doi.org/10.5555/x"],
                      [["bad"], "https://doi.org/10.5555/x", None],
                      ["https://doi.org/10.5555/x", None, "other"]):
            with self.subTest(value=value):
                res, field = self.mapped(value)
                self.assertEqual(res.record, {"id": "doi:10.5555/x"})
                self.assertEqual(field.rewritten_from, json.dumps(value))
                self.assertIn("remaining list item(s)", field.detail)
                self.assertIn("null; dropped", field.detail)
                self.assertNotIn("fell back", field.detail)

    def test_root_id_is_filtered_too_and_refusals_are_reported_if_both_are_empty(self):
        res, field = self.mapped([None], [None, "ark:59853/fallback"])
        self.assertEqual(res.record, {"id": "ark:59853/fallback"})
        self.assertIn("@id: 1 of 2 list items is null; dropped", field.detail)
        for root_id in ([None], [["x"]], None):
            with self.subTest(root_id=root_id):
                res, field = self.mapped([["identifier"]], root_id)
                self.assertEqual(res.record, {})
                self.assertEqual(field.status, "empty")
                self.assertFalse(field.from_table)
                self.assertIn("dropped rather than flattened", field.detail)


class TestNestedListsAcrossTheArms(unittest.TestCase):
    """#4175, #4183. `_coerce`'s comment says where this arm and the
    FAIRSCAPE converter of PR #4042 agree on a list of nulls or lists and on
    a list that mixes values with lists. Both arms are run here on each
    shape, for one crate property of each kind that both map to the same
    `Dataset` slot: text, a list of text, a date-time, the doi, a list of
    objects and one object. `rai:dataCollectionTimeframe` given dates, the
    comment's second exception, has a test of its own (#4197)."""

    #: crate property -> (the slot both arms fill from it, a value it takes)
    PAIRS = {
        "name": ("title", "x"),
        "keywords": ("keywords", "x"),
        "datePublished": ("issued", "2026-06-30"),
        "identifier": ("doi", "https://doi.org/10.5555/x"),
        "author": ("creators", "x"),
        "rai:dataReleaseMaintenancePlan": ("updates", "x"),
    }

    @classmethod
    def setUpClass(cls):
        repo_root = str(Path(__file__).resolve().parents[2])
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from src.fairscape_integration.fairscape_to_d4d import FairscapeToD4DConverter
        cls.converter_class = FairscapeToD4DConverter
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.table = load_mapping()

    def this_arm(self, prop, slot, value, detail=False):
        """What `map_crate` writes in `slot`, from the table's row for it,
        and with `detail`, the row's detail beside it."""
        row = next(row for row in self.table
                   if row["D4D_Full_Path"].strip() == f"Dataset.{slot}"
                   and row["RO_Crate_JSON_Path"].strip()
                   == f"@graph[?@type='Dataset']['{prop}']")
        source = row["RO_Crate_JSON_Path"].strip()
        self.assertEqual(source, f"@graph[?@type='Dataset']['{prop}']")
        res = map_crate(_crate_holding(source, value), [row], self.sv, "TEST")
        written = res.record.get(slot)
        return (written, res.fields[0].detail) if detail else written

    def converter(self, prop, slot, value, dropped=False):
        """What the converter writes in `slot` for a crate root holding
        `value` at `prop`, and with `dropped`, what it records as left out
        beside it."""
        crate = {"@context": {"@vocab": "https://schema.org/"}, "@graph": [
            {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
             "about": {"@id": "./"}},
            {"@id": "./", "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
             "name": "A test crate", prop: value}]}
        converter = self.converter_class()
        with contextlib.redirect_stdout(io.StringIO()):
            written = converter.convert(crate).get(slot)
        return (written, converter.dropped) if dropped else written

    def test_documented_exceptions_across_all_shared_pairs_and_value_kinds(self):
        """#4201: detect property-specific work before the converter's
        `_shape`, such as `_timeframe` and `exact_bytes`. Derive the shared
        pairs from the table and the converter's mappings, including a
        pair whose slot the schema does not declare (both arms omit it).
        No committed crate or generated output is read by this sweep."""
        probe = self.converter_class()
        probe._described = {}
        probe._collected = {}
        mappings = (probe._map_basic_properties, probe._map_complex_properties,
                    probe._map_evi_properties, probe._map_rai_properties,
                    probe._map_d4d_properties)
        shared = set()
        for row in self.table:
            path = row["D4D_Full_Path"].strip()
            match = GRAPH_RE.fullmatch(row.get("RO_Crate_JSON_Path", "").strip())
            if not (path.startswith("Dataset.") and match
                    and match["type"] == "Dataset" and not match["name"]):
                continue
            prop, slot = match["prop"], path.partition(".")[2]
            # A number is accepted by exact_bytes, so that mapping is not
            # lost merely because a text sentinel would be refused.
            mapped = {(p, s) for mapping in mappings
                      for p, s, _ in mapping({prop: 1})}
            if (prop, slot) in mapped:
                shared.add((prop, slot))
        self.assertGreaterEqual(len(shared), 37)
        self.assertLessEqual({(p, s) for p, (s, _) in self.PAIRS.items()}, shared)
        kinds = {
            "text": "x", "iso_date": "2022-09-01",
            "slash_date": "1/31/2026", "ambiguous_date": "9/1/2022",
            "integer": 42, "digits": "2022", "boolean": True,
            "url": "https://example.org/x", "doi_url": "https://doi.org/10.5555/x",
            "reference": {"@id": "https://example.org/x"}, "object": {"name": "x"},
        }
        changed = set()
        for prop, slot in sorted(shared):
            for kind, item in kinds.items():
                ours_alone = self.this_arm(prop, slot, [item])
                theirs_alone = self.converter(prop, slot, [item])
                for mixed in ([item, ["y"]], [["y"], item], [item, [item]]):
                    with self.subTest(prop=prop, slot=slot, kind=kind, value=mixed):
                        self.assertEqual(self.this_arm(prop, slot, mixed), ours_alone)
                        theirs_mixed = self.converter(prop, slot, mixed)
                        if theirs_mixed != theirs_alone:
                            changed.add((slot, kind))
                            self.assertEqual(ours_alone, theirs_alone)
        # The single-valued class-range slots; #2915 made
        # `at_risk_populations` one the arms share.
        expected = {(slot, kind)
                    for slot in ("updates", "human_subject_research",
                                 "at_risk_populations")
                    for kind in kinds if kind != "boolean"}
        expected.update(("collection_timeframes", kind) for kind in (
            "iso_date", "slash_date", "ambiguous_date", "digits"))
        self.assertEqual(changed, expected)

    def test_neither_arm_writes_a_list_of_nulls_or_lists(self):
        for prop, (slot, x) in self.PAIRS.items():
            for value in ([None], [None, None], [[x]], [[x, "y"]], [None, [x]]):
                with self.subTest(prop=prop, value=value):
                    self.assertIsNone(self.this_arm(prop, slot, value))
                    self.assertIsNone(self.converter(prop, slot, value))

    def test_a_mixed_list_is_written_as_its_values_alone_but_in_one_object(self):
        """Each arm writes for a list mixing a value with a list what it
        writes for the value alone, and the two agree on the value alone,
        except in a single-valued slot whose range is a class (`updates`):
        the converter joins only text into one object, so it writes nothing
        for the mixed list. The other exception is the next test's."""
        for prop, (slot, x) in self.PAIRS.items():
            alone = self.this_arm(prop, slot, [x])
            self.assertIsNotNone(alone)
            self.assertEqual(self.converter(prop, slot, [x]), alone)
            for value in ([x, ["y"]], [["y"], x]):
                with self.subTest(prop=prop, value=value):
                    self.assertEqual(self.this_arm(prop, slot, value), alone)
                    self.assertEqual(self.converter(prop, slot, value),
                                     None if slot == "updates" else alone)

    def test_a_timeframe_list_of_dates_is_a_start_and_an_end_to_the_converter(self):
        """#4197, the second exception in `_coerce`'s comment. Where an item
        of `rai:dataCollectionTimeframe` is written as a date, the
        converter's `_timeframe` reads the list before `_shape` does: two
        items are a start and an end, a list inside the list counting as
        one of them, and three or more are dropped whole. This arm writes
        what it writes for the values alone, a timeframe named by the date,
        and its detail names each list it dropped. The arms agree on the
        values alone, on lists of nothing but lists and nulls, and wherever
        no item is written as a date. What the converter writes and records
        is pinned as it is, not as right: #4194 decides it, and a change
        there changes this test and the comment."""
        prop, slot = "rai:dataCollectionTimeframe", "collection_timeframes"
        for value in (["2022-09-01"], ["2026-06-30"], ["x"],
                      ["x", ["y"]], [["y"], "x"], ["x", ["2026-01-31"]]):
            both = [{"name": next(v for v in value if isinstance(v, str))}]
            with self.subTest(value=value):
                self.assertEqual(self.this_arm(prop, slot, value), both)
                self.assertEqual(self.converter(prop, slot, value), both)
        for value in ([["2022-09-01"]], [["2022-09-01", "2026-01-31"]],
                      [["2022-09-01"], ["2026-01-31"]], [None, ["2022-09-01"]]):
            with self.subTest(value=value):
                self.assertIsNone(self.this_arm(prop, slot, value))
                self.assertIsNone(self.converter(prop, slot, value))
        cases = (
            # the crate's value, its values alone, the lists this arm names
            # as dropped, and what the converter writes and records
            (["2022-09-01", ["2026-01-31"]], ["2022-09-01"],
             '1 of 2 list items is a list inside the list, for a slot that '
             'holds a list of single values: ["2026-01-31"]',
             [{"start_date": "2022-09-01", "end_date": "2026-01-31"}], []),
            (["2022-09-01", ["y"]], ["2022-09-01"],
             '1 of 2 list items is a list inside the list, for a slot that '
             'holds a list of single values: ["y"]',
             [{"start_date": "2022-09-01"}],
             [("collection_timeframes[0].end_date",
               "not placed in `end_date`: not a calendar date: y")]),
            ([["y"], "2026-06-30"], ["2026-06-30"],
             '1 of 2 list items is a list inside the list, for a slot that '
             'holds a list of single values: ["y"]',
             [{"end_date": "2026-06-30"}],
             [("collection_timeframes[0].start_date",
               "not placed in `start_date`: not a calendar date: y")]),
            (["2022-09-01", ["y"], ["z"]], ["2022-09-01"],
             '2 of 3 list items are lists inside the list, for a slot that '
             'holds a list of single values: ["y"], ["z"]',
             None,
             [("rai:dataCollectionTimeframe",
               "not placed in `collection_timeframes`: 3 items, where Croissant "
               "RAI defines this property as the start and end date of the "
               "collection")]),
        )
        for value, alone, left_out, converted, recorded in cases:
            with self.subTest(value=value):
                written_alone, detail_alone = self.this_arm(
                    prop, slot, alone, detail=True)
                self.assertEqual(written_alone, [{"name": alone[0]}])
                self.assertEqual(self.converter(prop, slot, alone), written_alone)
                self.assertEqual(self.this_arm(prop, slot, value, detail=True), (
                    written_alone,
                    f"{left_out}; dropped rather than flattened; {detail_alone}"))
                self.assertEqual(self.converter(prop, slot, value, dropped=True),
                                 (converted, recorded))


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

    def test_a_list_inside_the_list_is_dropped_and_the_doi_kept(self):
        """#4183. origin/main took the one DOI among the items, and the
        record validated; #4164's first version refused the whole row. The
        list inside the list is dropped and named, the DOI is written as
        origin/main wrote it, and the report names the crate's whole list."""
        crate_value = ["https://doi.org/10.5555/x", ["y"]]
        res = map_crate(_with_identifier(crate_value), self.rows, self.sv, "TEST")
        field = self.doi_field(res)
        self.assertEqual((res.record.get("doi"), field.status), ("10.5555/x", "filled"))
        self.assertEqual(
            field.detail,
            '1 of 2 list items is a list inside the list, for a slot that holds '
            'one value: ["y"]; dropped rather than flattened; the one DOI among '
            "1 list item(s); resolver or `doi:` prefix removed, case kept")
        self.assertEqual(field.rewritten_from, json.dumps(crate_value))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TEST_crate_mapped_d4d.yaml"
            path.write_text(yaml.safe_dump(res.record, sort_keys=False,
                                           allow_unicode=True), encoding="utf-8")
            self.assertEqual(validate(path), "PASS")

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
