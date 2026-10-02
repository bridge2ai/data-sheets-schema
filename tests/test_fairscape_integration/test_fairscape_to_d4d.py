#!/usr/bin/env python3
"""
Tests for the FAIRSCAPE RO-Crate → D4D converter's output contract.

#3969: every crate under data/ro-crate converted and wrote YAML, then
exited 1 because its own output failed D4D validation. The record is now
fitted to the schema's Dataset class, and what cannot be placed is recorded
in `dropped`. #3973: the converter read `rai:` spellings of three keys
FAIRSCAPE writes otherwise. #4072: the record describes the crate's root
data entity, not the last sub-crate in the `@graph`. #4073: the part of a
value a slot cannot hold is recorded too, and nothing is joined as a
Python repr. #4074: `resources` holds only hasPart members the crate types
as datasets, and `total_size_bytes` only a byte count. #4098: the record is
validated before it is returned, and each value the schema rejects is left
out and recorded with the validator's message, so every record validates.
#4125: the value at fault goes alone where a slot may hold either of two
classes, text in `isPartOf` is not a reference, and "holds the value of X
instead" is said of the record as returned. #4126: the passes have no
limit, and a `dropped` path numbers an object by its place in the crate.
#4138, #4153: `parent_datasets` takes only the root's `isPartOf`
references, as `resources` takes only its `hasPart` members, whatever other
property maps to it; a key of either name inside a reference, or in another
nested Dataset, is recorded and no dataset is minted for it. #4139: a value
waiting for a slot can cost a pass for each level it nests. #4152: an
`additionalProperty` entry with no name is recorded whatever it carries, a
reference to an entity in the `@graph` included.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from functools import lru_cache
from pathlib import Path
from unittest import mock

import yaml
from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration import fairscape_to_d4d
from src.fairscape_integration.fairscape_to_d4d import (
    FairscapeToD4DConverter,
    main,
    resolvable_id,
    root_data_entity,
)

SCHEMA = repo_root / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

#: The four crates #3969 names, all under data/ro-crate/, which
#: `make test-fairscape-to-d4d` converts. The FAIRSCAPE release crates under
#: data/ro-crate_packages/ are not among them. `TestRootDataEntity` converts
#: CM4AI's and CHORUS's, and `TestTheRecordValidates` AI_READI's, decoded
#: from windows-1252 because it is not UTF-8 (#4089).
BUNDLED = (
    "data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json",
    "data/ro-crate/examples/CM4AI_roundtrip.json",
    "data/ro-crate/examples/voice_d4d_to_fairscape.json",
    "data/ro-crate/examples/voice_fairscape_test.json",
)
FULL = repo_root / BUNDLED[0]

#: The CM4AI June 2026 release crate as published, and as `d4d rocrate
#: normalize` reduced it: ten entities typed ROCrate, the release and nine
#: sub-crates, in one `@graph` (#4072).
CM4AI_ZIP = repo_root / "data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip"
CM4AI_REDUCED = (repo_root / "data/ro-crate_packages/CM4AI/processed/"
                 "CM4AI_crate_metadata_reduced.json")
CM4AI_RELEASE = ("https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-"
                 "artificial-intelligence-June-2026-data-release")

#: The AI-READI v3.0.0 release crate, which is windows-1252, not UTF-8
#: (#4089). Its root's `datePublished` is `11/17/25` (#4098).
AI_READI = repo_root / "data/ro-crate_packages/AI_READI/raw/ro-crate-metadata.json"
CHORUS = repo_root / "data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json"


@lru_cache(maxsize=1)
def _validator():
    """The validator `linkml.validator.validate` builds, which the converter
    runs, built once: a closed JSON Schema, so a key the class does not
    declare is an error."""
    return Validator(str(SCHEMA),
                     validation_plugins=[JsonschemaValidationPlugin(closed=True)])


def problems(record):
    """The validator's messages for `record` as a Dataset; empty when valid."""
    return [result.message
            for result in _validator().validate(record, "Dataset").results]


def quietly(call, *args):
    """`call(*args)` with the converter's progress lines kept off the output."""
    with contextlib.redirect_stdout(io.StringIO()):
        return call(*args)


def crate(root, *entities):
    """A crate whose root entity carries `root`, with `entities` after it
    in the `@graph`."""
    return {
        "@context": {"@vocab": "https://schema.org/"},
        "@graph": [
            {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
             "about": {"@id": "./"}},
            {"@id": "./", "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
             "name": "A test crate", **root},
            *entities,
        ],
    }


def texts(objects):
    """The text of each object a crate string was shaped into."""
    return [o.get("description") or o.get("name") for o in objects]


class TestBundledCratesValidate(unittest.TestCase):
    """#3969: each bundled crate converts to a record the schema accepts."""

    def test_each_bundled_crate_converts_to_a_valid_record(self):
        for path in BUNDLED:
            with self.subTest(crate=path):
                record = quietly(FairscapeToD4DConverter().convert,
                                 repo_root / path)
                self.assertEqual(problems(record), [])

    def test_the_command_exits_zero_on_each_bundled_crate(self):
        """The script `make test-fairscape-to-d4d` runs, end to end."""
        for path in BUNDLED:
            with self.subTest(crate=path), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "record.yaml"
                argv = ["fairscape_to_d4d.py", "--input", str(repo_root / path),
                        "--output", str(output)]
                with mock.patch.object(sys, "argv", argv):
                    self.assertEqual(quietly(main), 0)
                written = yaml.safe_load(output.read_text(encoding="utf-8"))
                self.assertEqual(problems(written), [])

    def test_the_record_holds_plain_types(self):
        """`yaml.dump`, which `fairscape-cli rocrate-to-d4d` uses, writes a
        str subclass as a python object tag that `safe_load` refuses."""
        for path in BUNDLED:
            with self.subTest(crate=path):
                record = quietly(FairscapeToD4DConverter().convert,
                                 repo_root / path)
                self.assertEqual(yaml.safe_load(yaml.dump(record)), record)

    def test_the_record_carries_no_converter_stamp(self):
        """`schema_version`, `generated_date` and `source` are not D4D
        slots, and the timestamp made every conversion differ."""
        first = quietly(FairscapeToD4DConverter().convert, FULL)
        second = quietly(FairscapeToD4DConverter().convert, FULL)
        self.assertEqual(first, second)
        for stamp in ("schema_version", "generated_date", "source"):
            self.assertNotIn(stamp, first)


class TestDroppedValuesAreRecorded(unittest.TestCase):
    """#3969: a crate value with no slot is left out and named."""

    EVI_COUNTS = {"evi:datasetCount", "evi:computationCount",
                  "evi:softwareCount", "evi:schemaCount", "evi:totalEntities"}
    NO_SLOT_REASON = "the schema declares no"
    #: What each bundled crate carries, of what this converter reads, that
    #: the schema gives no Dataset slot. Anything else it reads is placed,
    #: so a mapping to a slot the schema does not declare fails here.
    NO_SLOT = {
        BUNDLED[0]: EVI_COUNTS | {"additionalProperty[Completeness]",
                                  "additionalProperty[Data Governance Committee]"},
        BUNDLED[1]: EVI_COUNTS,
        BUNDLED[2]: set(),
        BUNDLED[3]: set(),
    }
    #: What else each bundled crate carries that its slot cannot hold, with
    #: the reason given (#4073, #4074): the full crate's size with a unit,
    #: its four hasPart members the `@graph` does not describe, and the
    #: ambiguous start date `9/1/2022` both crates write.
    CANNOT_HOLD = {
        BUNDLED[0]: {"contentSize": "a size with a unit, not a byte count",
                     "hasPart": "does not describe it",
                     "collection_timeframes[0].start_date": "ambiguous date '9/1/2022'"},
        BUNDLED[1]: {"collection_timeframes[0].start_date": "ambiguous date '9/1/2022'"},
        BUNDLED[2]: {},
        BUNDLED[3]: {},
    }

    def test_exactly_the_values_the_record_cannot_hold_are_dropped(self):
        for path, no_slot in self.NO_SLOT.items():
            cannot_hold = self.CANNOT_HOLD[path]
            with self.subTest(crate=path):
                converter = FairscapeToD4DConverter()
                quietly(converter.convert, repo_root / path)
                self.assertEqual({source for source, _ in converter.dropped},
                                 no_slot | set(cannot_hold))
                for source, reason in converter.dropped:
                    self.assertIn(cannot_hold.get(source, self.NO_SLOT_REASON),
                                  reason)

    def test_values_without_a_slot_are_named_not_written(self):
        converter = FairscapeToD4DConverter()
        record = quietly(converter.convert, FULL)
        dropped = dict(converter.dropped)
        for source, key in (("evi:datasetCount", "dataset_count"),
                            ("evi:totalEntities", "total_entities"),
                            ("additionalProperty[Completeness]", "completeness"),
                            ("additionalProperty[Data Governance Committee]",
                             "data_governance_committee")):
            with self.subTest(source=source):
                self.assertIn(source, dropped)
                self.assertIn(f"`{key}`", dropped[source])
                self.assertNotIn(key, record)

    def test_fairscape_cli_reports_what_it_drops(self):
        """On stderr, apart from the YAML the command writes (#3969, #4099).
        Click 8.1 mixes stderr into `output` unless told not to; 8.2 dropped
        the option and always keeps `stderr` apart."""
        from click.testing import CliRunner
        from src.fairscape_integration.cli import cli

        try:
            runner = CliRunner(mix_stderr=False)
        except TypeError:
            runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "record.yaml"
            result = runner.invoke(
                cli, ["rocrate-to-d4d", str(FULL), "-o", str(output)])
            self.assertEqual(result.exit_code, 0, result.stdout + result.stderr)
            self.assertEqual(
                problems(yaml.safe_load(output.read_text(encoding="utf-8"))), [])
        for source in self.NO_SLOT[BUNDLED[0]] | set(self.CANNOT_HOLD[BUNDLED[0]]):
            self.assertIn(f"not placed: {source}:", result.stderr)
        self.assertNotIn("not placed:", result.stdout)

    def test_each_conversion_reports_its_own_drops(self):
        converter = FairscapeToD4DConverter()
        quietly(converter.convert, FULL)
        once = list(converter.dropped)
        quietly(converter.convert, FULL)
        self.assertEqual(converter.dropped, once)
        quietly(converter.convert, crate({"license": "MIT"}))
        self.assertEqual(converter.dropped, [])

    def test_a_value_the_slot_cannot_hold_is_named(self):
        converter = FairscapeToD4DConverter()
        record = quietly(converter.convert, crate({
            "identifier": "ark:59853/not-a-doi",
            "contentSize": "a few gigabytes",
        }))
        self.assertNotIn("doi", record)
        self.assertNotIn("total_size_bytes", record)
        sources = [source for source, _ in converter.dropped]
        self.assertIn("identifier", sources)
        self.assertIn("contentSize", sources)
        self.assertEqual(problems(record), [])

    def test_a_file_collection_keeps_what_its_class_declares(self):
        converter = FairscapeToD4DConverter()
        record = quietly(converter.convert, {
            "@context": {"@vocab": "https://schema.org/"},
            "@graph": [
                {"@id": "./", "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
                 "name": "Parent", "hasPart": [{"@id": "#raw"}]},
                {"@id": "#raw", "@type": "Dataset", "name": "Raw files",
                 "contentSize": "2048", "fileFormat": "application/zip",
                 "d4d:collectionType": ["raw_data"], "d4d:fileCount": 2},
            ],
        })
        self.assertEqual(record["file_collections"], [
            {"id": "#raw", "name": "Raw files", "total_bytes": 2048,
             "collection_type": "raw_data", "file_count": 2}])
        self.assertNotIn("resources", record)
        self.assertIn("file_collections[0].compression",
                      [source for source, _ in converter.dropped])
        self.assertEqual(problems(record), [])


class TestKeysFairscapeWrites(unittest.TestCase):
    """#3973: FAIRSCAPE's ROCrateMetadataElem declares `prohibitedUses`,
    `ethicalReview` and `rai:dataImputationProtocol`."""

    KEYS = (("prohibitedUses", "prohibited_uses"),
            ("ethicalReview", "ethical_reviews"),
            ("rai:dataImputationProtocol", "imputation_protocols"))
    #: What d4d_to_fairscape.py writes for the same three slots.
    LEGACY = (("rai:prohibitedUses", "prohibited_uses"),
              ("rai:ethicalReview", "ethical_reviews"),
              ("rai:imputationProtocol", "imputation_protocols"))

    def test_each_fairscape_key_reaches_its_slot(self):
        for key, slot in self.KEYS + self.LEGACY:
            with self.subTest(key=key):
                record = quietly(FairscapeToD4DConverter().convert,
                                 crate({key: f"Stated under {key}."}))
                self.assertEqual(texts(record[slot]), [f"Stated under {key}."])
                self.assertEqual(problems(record), [])

    def test_both_spellings_are_kept_in_the_multivalued_slot(self):
        for (key, slot), (legacy, _) in zip(self.KEYS, self.LEGACY):
            with self.subTest(key=key):
                record = quietly(FairscapeToD4DConverter().convert, crate({
                    key: "The FAIRSCAPE statement.",
                    legacy: "The round-trip statement."}))
                self.assertEqual(sorted(texts(record[slot])),
                                 ["The FAIRSCAPE statement.",
                                  "The round-trip statement."])
                same = quietly(FairscapeToD4DConverter().convert, crate({
                    key: "One statement.", legacy: "One statement."}))
                self.assertEqual(texts(same[slot]), ["One statement."])

    def test_the_bundled_crate_values_now_reach_the_record(self):
        root = next(e for e in json.loads(FULL.read_text(encoding="utf-8"))["@graph"]
                    if "Dataset" in e.get("@type", []))
        record = quietly(FairscapeToD4DConverter().convert, FULL)
        for key, slot in self.KEYS:
            with self.subTest(key=key):
                self.assertIn(root[key], texts(record[slot]))


class TestSharedSlots(unittest.TestCase):
    """Two crate properties for one slot (#3969)."""

    def test_a_single_valued_slot_records_the_value_it_supersedes(self):
        converter = FairscapeToD4DConverter()
        record = quietly(converter.convert, crate({
            "additionalProperty": [{"@type": "PropertyValue",
                                    "name": "Human Subject",
                                    "value": "From additionalProperty."}],
            "d4d:humanSubject": "From d4d:humanSubject."}))
        self.assertEqual(texts([record["human_subject_research"]]),
                         ["From d4d:humanSubject."])
        reasons = dict(converter.dropped)
        self.assertIn("superseded by d4d:humanSubject",
                      reasons["additionalProperty[Human Subject]"])

    def test_a_dedicated_property_wins_over_additional_property(self):
        """Whichever is read first: `license` is read before the
        `additionalProperty` entries, `d4d:humanSubject` after them."""
        converter = FairscapeToD4DConverter()
        record = quietly(converter.convert, crate({
            "license": "MIT",
            "additionalProperty": [{"@type": "PropertyValue",
                                    "name": "License", "value": "Other"}]}))
        self.assertEqual(record["license"], "MIT")
        self.assertIn("superseded by license",
                      dict(converter.dropped)["additionalProperty[License]"])

    def test_the_slot_takes_the_next_value_when_the_first_cannot_be_shaped(self):
        """The dedicated property comes first, but its value is chosen only
        once it is shaped: one its slot cannot hold leaves the slot to the
        `additionalProperty` value, and its entry says so (#4098). It used
        to leave the slot empty, and call the usable value superseded."""
        for root, slot, kept, source, fallback in (
                ({"license": {"@id": "https://spdx.org/licenses/MIT"}},
                 "license", "MIT", "license", ("License", "MIT")),
                ({"identifier": "ark:59853/x-1"}, "doi", "10.5555/ABC",
                 "identifier", ("DOI", "10.5555/ABC")),
                ({"d4d:humanSubject": True}, "human_subject_research",
                 {"name": "Approved by the IRB."}, "d4d:humanSubject",
                 ("Human Subject", "Approved by the IRB."))):
            with self.subTest(source=source):
                name, value = fallback
                record, dropped = converted(crate({**root, "additionalProperty": [
                    {"@type": "PropertyValue", "name": name, "value": value}]}))
                self.assertEqual(record[slot], kept)
                why = reasons(dropped, source)
                self.assertIn(f"not placed in `{slot}`", why)
                self.assertIn(f"`{slot}` holds the value of "
                              f"additionalProperty[{name}] instead", why)
                self.assertNotIn(f"additionalProperty[{name}]",
                                 [src for src, _ in dropped])
                self.assertEqual(problems(record), [])

    def test_the_slot_takes_the_next_value_when_the_schema_rejects_the_first(self):
        """`June 2026` is shaped, as `_coerce` leaves it, and the schema
        rejects it; the slot then takes the next value, in its place among
        the record's keys (#4098)."""
        record, dropped = converted(crate({
            "datePublished": "June 2026", "url": "https://example.org",
            "additionalProperty": [{"@type": "PropertyValue", "name": "Issued",
                                    "value": "2026-06-30"}]}))
        self.assertEqual(record["issued"], "2026-06-30T00:00:00Z")
        self.assertEqual(list(record), ["id", "title", "issued", "page"])
        self.assertEqual(dropped, [("datePublished", (
            "not placed in `issued`: June 2026 (the schema rejects it: 'June "
            "2026' is not a 'date-time'); `issued` holds the value of "
            "additionalProperty[Issued] instead"))])
        self.assertEqual(problems(record), [])

    def test_the_instead_clause_names_the_value_the_slot_ends_with(self):
        """Written once the record is valid (#4125). The next value can be
        rejected too, and then the slot is empty and no entry says what it
        holds; or a later value can replace it, and every entry names the
        one the slot ends with. The clause used to be written when a value
        was placed, before the schema had seen it."""
        for root, slot, first, second, key in (
                ({"license": {"@id": "https://spdx.org/licenses/MIT"},
                  "additionalProperty": [property_value("License", 5)]},
                 "license", "license", "additionalProperty[License]", "license"),
                ({"datePublished": {"@value": "2026"},
                  "additionalProperty": [property_value("Issued", "June 2026")]},
                 "issued", "datePublished", "additionalProperty[Issued]", "issued"),
                ({"d4d:humanSubject": True, "additionalProperty": [
                    property_value("Human Subject", {"name": 5})]},
                 "human_subject_research", "d4d:humanSubject",
                 "human_subject_research.name", "name")):
            with self.subTest(slot=slot):
                record, dropped = converted(crate(root))
                self.assertNotIn(slot, record)
                self.assertEqual(problems(record), [])
                self.assertIn(f"not placed in `{slot}`", reasons(dropped, first))
                self.assertIn(f"not placed in `{key}`", reasons(dropped, second))
                self.assertNotIn("instead", str(dropped))
        record, dropped = converted(crate({
            "datePublished": "June 2026",
            "additionalProperty": [property_value("Issued", "2026-06-30"),
                                   property_value("issued", "July 2026")]}))
        self.assertEqual(record["issued"], "2026-06-30T00:00:00Z")
        self.assertEqual(dropped, [
            ("datePublished", (
                "not placed in `issued`: June 2026 (the schema rejects it: "
                "'June 2026' is not a 'date-time'); `issued` holds the value "
                "of additionalProperty[Issued] instead")),
            ("additionalProperty[issued]", (
                "not placed in `issued`: July 2026 (the schema rejects it: "
                "'July 2026' is not a 'date-time'); `issued` holds the value "
                "of additionalProperty[Issued] instead"))])
        # Only a slot of the record itself is said to hold a value instead:
        # a reference's `description` is not the record's
        record, dropped = converted(crate({
            "description": "The root.",
            "isPartOf": [{"@id": "ark:59852/p", "description": {"@id": "#d"}}]}))
        self.assertEqual(record["description"], "The root.")
        self.assertEqual(dropped, [("parent_datasets[0].description", (
            "not placed in `description`: a crate reference or object, which "
            'a `string` slot does not hold: {"@id": "#d"}'))])

    def test_the_same_value_from_two_properties_is_not_dropped(self):
        """Nothing is left out when two properties state one value, and a
        value stated twice is superseded once."""
        license_entry = {"@type": "PropertyValue", "name": "License"}
        record, dropped = converted(crate({
            "license": "MIT",
            "additionalProperty": [{**license_entry, "value": "MIT"}]}))
        self.assertEqual((record["license"], dropped), ("MIT", []))
        record, dropped = converted(crate({
            "license": "MIT",
            "additionalProperty": [{**license_entry, "value": "Apache-2.0"},
                                   {**license_entry, "value": "Apache-2.0"}]}))
        self.assertEqual(record["license"], "MIT")
        self.assertEqual(dropped, [("additionalProperty[License]",
                                    "superseded by license, which also maps "
                                    "to `license`")])

    def test_each_value_for_a_slot_the_class_does_not_declare_is_named(self):
        record, dropped = converted(crate({"additionalProperty": [
            {"@type": "PropertyValue", "name": "Completeness", "value": "a"},
            {"@type": "PropertyValue", "name": "Completeness", "value": "b"}]}))
        self.assertNotIn("completeness", record)
        self.assertEqual(dropped, 2 * [("additionalProperty[Completeness]",
                                        "the schema declares no `completeness` "
                                        "slot on Dataset")])

    def test_a_list_for_a_single_valued_object_slot_is_one_object(self):
        record = quietly(FairscapeToD4DConverter().convert, crate({
            "rai:dataReleaseMaintenancePlan": ["Quarterly.", "Then yearly."]}))
        self.assertEqual(texts([record["updates"]]), ["Quarterly.; Then yearly."])
        self.assertEqual(problems(record), [])

    def test_a_multivalued_slot_keeps_both_values(self):
        converter = FairscapeToD4DConverter()
        record = quietly(converter.convert, crate({
            "additionalProperty": [{"@type": "PropertyValue",
                                    "name": "Prohibited Uses",
                                    "value": "From additionalProperty."}],
            "prohibitedUses": "From prohibitedUses."}))
        self.assertEqual(texts(record["prohibited_uses"]),
                         ["From additionalProperty.", "From prohibitedUses."])
        self.assertEqual(converter.dropped, [])


class TestIdentifiers(unittest.TestCase):
    """#3969: the record's id, and ARKs in identifier slots."""

    def test_an_ark_is_written_as_its_resolver_url(self):
        cases = {
            "ark:59853/rocrate-x": "https://n2t.net/ark:59853/rocrate-x",
            "ark:/59853/rocrate-x": "https://n2t.net/ark:/59853/rocrate-x",
            # Already resolvable, or not an ARK: left as written
            "https://fairscape.net/ark:59852/x": "https://fairscape.net/ark:59852/x",
            "ark:/Ideker_Lab": "ark:/Ideker_Lab",
            "doi:10.1234/x": "doi:10.1234/x",
            "./": "./",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(resolvable_id(value), expected)

    def test_bundled_references_are_resolver_urls(self):
        """The full crate's isPartOf references, written as ARKs. Its hasPart
        members are not written (`TestDatasetParts`)."""
        root = next(e for e in json.loads(FULL.read_text(encoding="utf-8"))["@graph"]
                    if "Dataset" in e.get("@type", []))
        record = quietly(FairscapeToD4DConverter().convert, FULL)
        self.assertEqual(
            [item["id"] for item in record["parent_datasets"]],
            ["https://n2t.net/" + item["@id"] for item in root["isPartOf"]])

    def test_the_record_id_is_the_roots_identifier_else_its_id(self):
        """On one-entity graphs; which entity is the root is
        `TestRootDataEntity`'s."""
        cases = (
            ({"@id": "./", "identifier": "https://doi.org/10.5555/Test"},
             "doi:10.5555/Test"),
            ({"@id": "ark:59853/rocrate-x"}, "https://n2t.net/ark:59853/rocrate-x"),
            ({"@id": "./"}, "./"),
        )
        for root, expected in cases:
            with self.subTest(root=root):
                record = quietly(FairscapeToD4DConverter().convert, {"@graph": [
                    {"@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
                     "name": "A test crate", **root}]})
                self.assertEqual(record["id"], expected)
                self.assertEqual(problems(record), [])

    def test_the_doi_slot_takes_the_bare_doi(self):
        record = quietly(FairscapeToD4DConverter().convert, crate(
            {"identifier": "https://doi.org/10.18130/V3/K7TGEM"}))
        self.assertEqual(record["doi"], "10.18130/V3/K7TGEM")


def converted(crate_or_path):
    """`(record, dropped)` for one conversion."""
    converter = FairscapeToD4DConverter()
    record = quietly(converter.convert, crate_or_path)
    return record, converter.dropped


def reasons(dropped, source):
    """Every reason `dropped` gives for `source`, joined."""
    return " | ".join(reason for src, reason in dropped if src == source)


def validated(crate_json):
    """`(record, dropped, validations)`: one conversion, and how many times
    `_settle` validated the record on the way."""
    real = fairscape_to_d4d.record_validator
    count = [0]

    def counting(schema):
        validator = real(schema)

        class Counting:
            def iter_results(self, *args):
                count[0] += 1
                return validator.iter_results(*args)

        return Counting()

    with mock.patch.object(fairscape_to_d4d, "record_validator", counting):
        record, dropped = converted(crate_json)
    return record, dropped, count[0]


def property_value(name, value):
    """An `additionalProperty` entry."""
    return {"@type": "PropertyValue", "name": name, "value": value}


def tracked_full_crate():
    """The tracked full crate's JSON, read afresh, and its root in it."""
    crate_json = json.loads(FULL.read_text(encoding="utf-8"))
    root = next(e for e in crate_json["@graph"]
                if "Dataset" in e.get("@type", []))
    return crate_json, root


ROCRATE = ["Dataset", "https://w3id.org/EVI#ROCrate"]


def sub_crate(name, last):
    """A sub-crate of `release_crate`'s release, with a part and a parent of
    its own."""
    return {"@id": f"ark:59853/rocrate-{name}", "@type": ROCRATE,
            "name": f"A sub-crate listed {'last' if last else 'first'}",
            "identifier": f"https://doi.org/10.5555/{name.upper()}",
            "hasPart": [{"@id": "ark:59853/dataset-file"}],
            "isPartOf": [{"@id": "ark:59853/rocrate-release"}]}


def release_crate():
    """A release crate whose descriptor is about the release, with its two
    sub-crates, typed ROCrate like it, before and after it in the `@graph`.

    FAIRSCAPE writes the release first, as `@graph[1]`, the first ROCrate
    entity, with its sub-crates after it (every tracked release crate is
    laid out so). This layout is built so that neither the first nor the
    last ROCrate entity is the release, which only the descriptor's
    `about` names. A JSON-LD `@graph` is unordered, so it is the same
    crate in any order."""
    return {"@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
         "about": {"@id": "ark:59853/rocrate-release"}},
        sub_crate("sub-a", last=False),
        {"@id": "ark:59853/rocrate-release", "@type": ROCRATE,
         "name": "The release", "description": "What the release holds.",
         "identifier": "https://doi.org/10.5555/RELEASE",
         "hasPart": [{"@id": "ark:59853/rocrate-sub-a"},
                     {"@id": "ark:59853/rocrate-sub-b"}],
         "isPartOf": [{"@id": "ark:59852/project-x"}]},
        sub_crate("sub-b", last=True),
        {"@id": "ark:59853/dataset-file", "@type": "Dataset",
         "name": "A file set of a sub-crate"},
    ]}


class TestRootDataEntity(unittest.TestCase):
    """#4072: the record describes the crate's root data entity, by the
    RO-Crate rule: the descriptor's `about`, else `./`, else the first
    ROCrate-typed entity. The last ROCrate-typed entity, which the converter
    took, is a sub-crate in a FAIRSCAPE release crate."""

    def test_the_root_is_the_entity_the_descriptor_is_about(self):
        record, dropped = converted(release_crate())
        self.assertEqual(record["id"], "doi:10.5555/RELEASE")
        self.assertEqual(record["title"], "The release")
        self.assertEqual(record["description"], "What the release holds.")
        self.assertEqual(record["doi"], "10.5555/RELEASE")
        # Its sub-crates are its parts; their parts and parents are not its
        self.assertEqual(
            [(fc["id"], fc["name"]) for fc in record["file_collections"]],
            [("https://n2t.net/ark:59853/rocrate-sub-a",
              "A sub-crate listed first"),
             ("https://n2t.net/ark:59853/rocrate-sub-b",
              "A sub-crate listed last")])
        self.assertEqual([p["id"] for p in record["parent_datasets"]],
                         ["https://n2t.net/ark:59852/project-x"])
        self.assertNotIn("resources", record)
        self.assertEqual(dropped, [])
        self.assertEqual(problems(record), [])

    def test_a_sub_crates_metadata_file_is_not_the_descriptor(self):
        """Only the entity whose `@id` is `ro-crate-metadata.json` is the
        descriptor, not a file listed under that name in a sub-directory."""
        crate_json = release_crate()
        crate_json["@graph"].insert(0, {
            "@id": "sub-b/ro-crate-metadata.json", "@type": "CreativeWork",
            "about": {"@id": "ark:59853/rocrate-sub-b"}})
        record, _ = converted(crate_json)
        self.assertEqual(record["title"], "The release")

    def test_without_a_descriptor_the_root_is_dot_slash_then_the_first_rocrate(self):
        from data_sheets_schema.rocrate_map import crate_root
        dot_slash = [{"@id": "ark:59853/rocrate-a", "@type": ROCRATE,
                      "name": "A sub-crate"},
                     {"@id": "./", "@type": "Dataset", "name": "The root"},
                     {"@id": "ark:59853/rocrate-b", "@type": ROCRATE,
                      "name": "Another sub-crate"}]
        first = [{"@id": "ark:59853/rocrate-a", "@type": ROCRATE, "name": "First"},
                 {"@id": "ark:59853/rocrate-b", "@type": ROCRATE, "name": "Second"}]
        for graph, title in ((dot_slash, "The root"), (first, "First")):
            with self.subTest(title=title):
                record, _ = converted({"@graph": graph})
                self.assertEqual(record["title"], title)
        # The third rule is the one `rocrate_map.crate_root` and FAIRSCAPE apply
        self.assertIs(root_data_entity(first), crate_root(first))

    def test_a_descriptor_naming_no_entity_falls_back(self):
        graph = [{"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
                  "about": {"@id": "ark:59853/not-in-the-graph"}},
                 {"@id": "./", "@type": ROCRATE, "name": "The root"},
                 {"@id": "ark:59853/rocrate-a", "@type": ROCRATE, "name": "Later"}]
        record, _ = converted({"@graph": graph})
        self.assertEqual(record["title"], "The root")

    def test_the_tracked_cm4ai_release_crate_is_its_june_2026_release(self):
        """The reduced crate keeps every entity; its hasPart lists are
        summaries, so it has no parts to convert."""
        from data_sheets_schema.rocrate_map import crate_root
        graph = json.loads(CM4AI_REDUCED.read_text(encoding="utf-8"))["@graph"]
        root = root_data_entity(graph)
        self.assertEqual(root["@id"], CM4AI_RELEASE)
        self.assertIs(root, crate_root(graph))
        self.assertEqual(sum(1 for e in graph if "ROCrate" in str(e.get("@type"))), 10)
        record, _ = converted(CM4AI_REDUCED)
        self.assertEqual(record["id"], "doi:10.18130/V3/HIGT4C")
        self.assertEqual(record["title"], root["name"])
        self.assertEqual(record["description"], root["description"])
        self.assertEqual(problems(record), [])

    def test_a_root_typed_evi_dataset_is_found_by_the_descriptor(self):
        """CHORUS types its root and sub-crates https://w3id.org/EVI#Dataset,
        not Dataset, which the converter required before the descriptor
        named the root.

        As published, the root is also the first ROCrate entity, so the
        third rule finds it too. The same crate with its sub-crates listed
        first is found only by the descriptor (#4099)."""
        crate_json = json.loads(CHORUS.read_text(encoding="utf-8"))
        graph = crate_json["@graph"]
        descriptor = next(e for e in graph if e["@id"] == "ro-crate-metadata.json")
        root = next(e for e in graph if e["@id"] == descriptor["about"]["@id"])
        subcrates = [e for e in graph if e is not root and e is not descriptor]
        self.assertTrue(subcrates and all("ROCrate" in str(e["@type"])
                                          for e in subcrates))
        for order, entities in (("as published", graph),
                                ("sub-crates first",
                                 [descriptor, *subcrates, root])):
            with self.subTest(order=order):
                record, dropped = converted({**crate_json, "@graph": entities})
                self.assertIs(root_data_entity(entities), root)
                self.assertEqual(record["id"], "doi:10.18130/V3/XNBOPG")
                self.assertEqual(record["title"], root["name"])
                # In `@graph` order, which is not the order of the root's
                # hasPart; the reference's `name` is the entity's own
                self.assertEqual([fc["id"] for fc in record["file_collections"]],
                                 [e["@id"] for e in subcrates])
                self.assertNotEqual([e["@id"] for e in subcrates],
                                    [part["@id"] for part in root["hasPart"]])
                self.assertEqual(
                    {source for source, _ in dropped},
                    {"contentSize", *(f"{e['@id']}.contentSize" for e in subcrates)})
                self.assertEqual(problems(record), [])

    def test_the_cm4ai_release_zip_converts_as_its_june_2026_release(self):
        with zipfile.ZipFile(CM4AI_ZIP) as archive:
            crate = json.loads(archive.read(
                "cm4ai_release_metadata/ro-crate-metadata.json"))
        graph = crate["@graph"]
        root = next(e for e in graph if e.get("@id") == CM4AI_RELEASE)
        record, dropped = converted(crate)
        self.assertEqual(record["id"], "doi:10.18130/V3/HIGT4C")
        self.assertEqual(record["title"], root["name"])
        # The nine sub-crates are its parts, and the record is not among them
        subcrates = [e["@id"] for e in graph
                     if "ROCrate" in str(e.get("@type")) and e is not root]
        self.assertEqual(len(subcrates), 9)
        self.assertEqual([fc["id"] for fc in record["file_collections"]], subcrates)
        self.assertEqual([p["id"] for p in record["parent_datasets"]],
                         [p["@id"] for p in root["isPartOf"]])
        # Its other hasPart members are people and terms, not datasets
        self.assertNotIn("resources", record)
        typed = {e["@id"]: e["@type"] for e in graph}
        not_parts = [ref["@id"] for ref in root["hasPart"]
                     if ref["@id"] not in subcrates]
        self.assertEqual(sorted({typed[ref] for ref in not_parts}),
                         ["DefinedTerm", "Person"])
        part_reasons = reasons(dropped, "hasPart")
        for ref in not_parts:
            self.assertIn(f"{ref}: the crate types it", part_reasons)
        self.assertEqual(problems(record), [])


class TestPartialValuesAreRecorded(unittest.TestCase):
    """#4073: whatever part of a value its slot does not hold is recorded in
    `dropped`, and no value is joined as a Python repr."""

    def test_a_single_valued_enum_slot_records_the_values_it_does_not_hold(self):
        for given, kept, left in ((["raw_data", "processed_data"], "raw_data",
                                   "processed_data"),
                                  (["raw_data", "bogus_kind"], "raw_data",
                                   "bogus_kind")):
            with self.subTest(given=given):
                record, dropped = converted(crate(
                    {"hasPart": [{"@id": "#raw"}]},
                    {"@id": "#raw", "@type": "Dataset", "name": "Raw files",
                     "d4d:collectionType": given}))
                self.assertEqual(record["file_collections"][0]["collection_type"],
                                 kept)
                why = reasons(dropped, "file_collections[0].collection_type")
                self.assertIn(f"not placed in `collection_type`: {left}", why)
                self.assertEqual(problems(record), [])

    def test_identifiers_beyond_the_one_each_slot_holds_are_recorded(self):
        record, dropped = converted(crate({"identifier": [
            "https://doi.org/10.5555/abc", "ark:59852/other-id"]}))
        self.assertEqual(record["id"], "doi:10.5555/abc")
        self.assertEqual(record["doi"], "10.5555/abc")
        why = reasons(dropped, "identifier")
        for slot in ("id", "doi"):
            self.assertIn(f"not placed in `{slot}`: ", why)
        self.assertEqual(why.count("ark:59852/other-id"), 2)
        # An identifier that is not text is not written as one
        record, dropped = converted(crate({"identifier": {"@id": "#x"}}))
        self.assertEqual(record["id"], "./")
        self.assertIn("not placed in `id`", reasons(dropped, "identifier"))

    def test_a_reference_keeps_the_keys_its_class_declares_and_names_the_rest(self):
        record, dropped = converted(crate({"author": [
            {"@id": "https://orcid.org/0000-0002-1825-0097", "@type": "Person",
             "name": "Jane Doe", "affiliation": "UCSD", "jobTitle": "Curator"},
            {"@id": "https://orcid.org/0000-0001-5109-3700", "id": "#own-id",
             "name": {"@value": "Ann Roe", "@language": "en"}},
            {"@id": "#ref", "@reverse": {"author": {"@id": "./"}}}]}))
        self.assertEqual(record["creators"], [
            {"id": "https://orcid.org/0000-0002-1825-0097", "name": "Jane Doe"},
            {"id": "#own-id"}, {"id": "#ref"}])
        self.assertEqual({source for source, _ in dropped},
                         {"creators[0].affiliation", "creators[0].jobTitle",
                          "creators[1].@id", "creators[1].name",
                          "creators[2].@reverse"})

    def test_references_are_never_joined_as_python_text(self):
        record, dropped = converted(crate({
            "additionalProperty": [{"@type": "PropertyValue",
                                    "name": "Human Subject",
                                    "value": [{"@id": "#irb"}, {"@id": "#consent"}]}],
            "rai:dataReleaseMaintenancePlan": ["Quarterly.", {"@id": "#plan"}],
            "license": [{"@id": "https://spdx.org/licenses/MIT"},
                        {"@id": "https://spdx.org/licenses/Apache-2.0"}],
        }))
        self.assertNotIn("{'@id'", json.dumps(record))
        for slot, source in (("human_subject_research",
                              "additionalProperty[Human Subject]"),
                             ("updates", "rai:dataReleaseMaintenancePlan"),
                             ("license", "license")):
            with self.subTest(slot=slot):
                self.assertNotIn(slot, record)
                self.assertIn(f"not placed in `{slot}`", reasons(dropped, source))
        self.assertEqual(problems(record), [])

    def test_a_reference_beside_text_in_a_text_slot_is_recorded(self):
        """The text is placed, and the reference or object beside it, which
        a slot that does not range over a class cannot hold, is named
        (#4099)."""
        for key, value, kept, left in (
                ("license", ["MIT", {"@id": "https://spdx.org/licenses/Apache-2.0"}],
                 "MIT", '{"@id": "https://spdx.org/licenses/Apache-2.0"}'),
                ("keywords", ["a", {"@type": "DefinedTerm", "name": "b"}],
                 ["a"], '{"@type": "DefinedTerm", "name": "b"}')):
            with self.subTest(key=key):
                record, dropped = converted(crate({key: value}))
                self.assertEqual(record[key], kept)
                self.assertEqual(dropped, [(key, (
                    f"part of the value not placed in `{key}`: {left} (a "
                    "crate reference or object, which a `string` slot does "
                    "not hold)"))])
                self.assertEqual(problems(record), [])

    def test_an_is_part_of_entry_with_no_id_is_recorded(self):
        record, dropped = converted(crate({"isPartOf": [
            {"name": "Project X"}, {"@id": "ark:59852/project-y"}]}))
        self.assertEqual(record["parent_datasets"],
                         [{"id": "https://n2t.net/ark:59852/project-y"}])
        self.assertEqual(dropped, [("isPartOf", (
            'an entry with no `@id`: {"name": "Project X"}'))])

    def test_text_in_is_part_of_is_not_a_reference(self):
        """JSON-LD reads a string under `isPartOf` as text, as it reads
        `{"@value": …}`: it names no dataset, and is recorded, not written
        as a parent's `id` (#4125)."""
        def said(text):
            return ("isPartOf", (
                f"text, not a reference: {text} (under RO-Crate's context "
                "JSON-LD reads text under `isPartOf` as a literal, which names "
                "no dataset the record can point at; a reference is written "
                '`{"@id": …}`)'))
        names = ["Cell Maps for AI project", "University of California San Diego"]
        for value in (names[0], names):
            with self.subTest(value=value):
                record, dropped = converted(crate({"isPartOf": value}))
                self.assertNotIn("parent_datasets", record)
                self.assertEqual(dropped, [said(name) for name in
                                           ([value] if isinstance(value, str)
                                            else value)])
        record, dropped = converted(crate({"isPartOf": [
            names[0], {"@value": names[1]}, {"@id": "ark:59852/project-y"}]}))
        self.assertEqual(record["parent_datasets"],
                         [{"id": "https://n2t.net/ark:59852/project-y"}])
        self.assertEqual(dropped, [said(names[0]), ("isPartOf", (
            f'an entry with no `@id`: {{"@value": "{names[1]}"}}'))])
        self.assertEqual(problems(record), [])

    def test_a_single_valued_identifier_slot_keeps_one_identifier(self):
        record, dropped = converted(crate(
            {"publisher": ["ark:59852/org-a", "ark:59852/org-b"]}))
        self.assertEqual(record["publisher"], "https://n2t.net/ark:59852/org-a")
        self.assertIn("ark:59852/org-b", reasons(dropped, "publisher"))

    def test_an_additional_property_named_resources_is_reported_not_a_crash(self):
        for value in ("https://example.org/supplement",
                      ["https://example.org/a", "https://example.org/b"],
                      {"@id": "https://example.org/a"}):
            with self.subTest(value=value):
                record, dropped = converted(crate({"additionalProperty": [
                    {"@type": "PropertyValue", "name": "Resources",
                     "value": value}]}))
                self.assertNotIn("resources", record)
                self.assertIn("not placed in `resources`",
                              reasons(dropped, "additionalProperty[Resources]"))
                self.assertEqual(problems(record), [])

    def test_parent_datasets_takes_only_is_part_of_references(self):
        """An `additionalProperty` named "Parent Datasets" maps to
        `parent_datasets` by its name, as one named "Resources" maps to
        `resources`. It is a name and a value, not a reference under
        `isPartOf`. Its text became a parent whose `id` `_to_object` minted,
        asserting a dataset the crate does not identify, with nothing in
        `dropped`, and beside a real `isPartOf` reference it was a second
        parent (#4138). It is recorded, as text under `isPartOf` is
        (#4125), and so is a reference in it, or the slot's own name."""
        text = "Cell Maps for AI project"
        entry = property_value("Parent Datasets", text)

        def said(source, shown):
            return (source, (
                f"not placed in `parent_datasets`: {shown} is not a reference "
                "under the root's `isPartOf`, which is all `parent_datasets` "
                "holds"))

        for root, parents in (
                ({"additionalProperty": [entry]}, None),
                ({"isPartOf": [{"@id": "ark:59852/p"}],
                  "additionalProperty": [entry]},
                 [{"id": "https://n2t.net/ark:59852/p"}])):
            with self.subTest(is_part_of="isPartOf" in root):
                record, dropped = converted(crate(root))
                self.assertEqual(record.get("parent_datasets"), parents)
                self.assertEqual(
                    dropped, [said("additionalProperty[Parent Datasets]", text)])
                self.assertNotIn("urn:d4d", json.dumps(record))
                self.assertEqual(problems(record), [])
        record, dropped = converted(crate({"additionalProperty": [
            property_value("Parent Datasets", {"@id": "ark:59852/q"}),
            property_value("parent_datasets", "Project Z")]}))
        self.assertNotIn("parent_datasets", record)
        self.assertEqual(dropped, [
            said("additionalProperty[Parent Datasets]", '{"@id": "ark:59852/q"}'),
            said("additionalProperty[parent_datasets]", "Project Z")])
        # The tracked full crate, whose root has two `isPartOf` references,
        # with the entry added: the record is the one the crate gives
        # without it, and the entry is the one value more in `dropped`
        def full_crate(*added):
            crate_json = json.loads(FULL.read_text(encoding="utf-8"))
            root = next(e for e in crate_json["@graph"]
                        if "Dataset" in e.get("@type", []))
            root["additionalProperty"] = [*root["additionalProperty"], *added]
            return crate_json
        before, before_dropped = converted(full_crate())
        after, after_dropped = converted(full_crate(entry))
        self.assertEqual(len(after["parent_datasets"]), 2)
        self.assertEqual(after, before)
        self.assertEqual(
            [each for each in after_dropped if each not in before_dropped],
            [said("additionalProperty[Parent Datasets]", text)])
        self.assertEqual(len(after_dropped), len(before_dropped) + 1)

    def test_a_nested_dataset_takes_no_datasets_of_its_own(self):
        """A `parent_datasets` or `resources` key inside an `isPartOf` or
        `hasPart` reference, or in a DataSubset, is not the root's
        `isPartOf` or `hasPart`, the only properties those slots take
        (`DATASET_SLOTS`). Its text became a dataset whose `id` `_to_object`
        minted, `urn:d4d:fairscape:parent_datasets:1`, with nothing in
        `dropped` (#4153). It is recorded, text and references alike, and
        the object keeps its other keys; an empty value states nothing, and
        is not. A FileCollection's `resources` holds Files, and keeps
        them."""
        holds = {"parent_datasets": "a reference under the root's `isPartOf`",
                 "resources": "a hasPart member the crate types as a dataset"}

        def said(source, slot, shown):
            return (source, (f"not placed in `{slot}`: {shown} is not "
                             f"{holds[slot]}, which is all `{slot}` holds"))

        parent = {"id": "https://n2t.net/ark:59852/p"}
        for root, slot, kept, source, key, shown in (
                ({"isPartOf": [{"@id": "ark:59852/p",
                                "parent_datasets": "Project Z"}]},
                 "parent_datasets", [parent], "parent_datasets[0]",
                 "parent_datasets", "Project Z"),
                ({"isPartOf": [{"@id": "ark:59852/p",
                                "resources": ["Supplement A", "Supplement B"]}]},
                 "parent_datasets", [parent], "parent_datasets[0]",
                 "resources", '["Supplement A", "Supplement B"]'),
                ({"hasPart": [{"@id": "ark:59853/rocrate-y", "@type": "Dataset",
                               "name": "Y", "parent_datasets": "Project Z"}]},
                 "resources",
                 [{"id": "https://n2t.net/ark:59853/rocrate-y", "name": "Y"}],
                 "resources[0]", "parent_datasets", "Project Z"),
                ({"additionalProperty": [property_value("Subsets", {
                    "@id": "#s", "parent_datasets": [{"@id": "ark:59852/q"}]})]},
                 "subsets", [{"id": "#s"}], "subsets[0]", "parent_datasets",
                 '[{"@id": "ark:59852/q"}]')):
            with self.subTest(source=f"{source}.{key}"):
                record, dropped = converted(crate(root))
                self.assertEqual(record[slot], kept)
                self.assertEqual(dropped, [said(f"{source}.{key}", key, shown)])
                self.assertNotIn("urn:d4d", json.dumps(record))
                self.assertEqual(problems(record), [])
        # An empty value states nothing, and is not recorded, as elsewhere
        record, dropped = converted(crate({"isPartOf": [
            {"@id": "ark:59852/p", "parent_datasets": [], "resources": ""}]}))
        self.assertEqual((record["parent_datasets"], dropped), ([parent], []))
        files = [{"@id": "#f", "name": "a file"}]
        record, dropped = converted(crate({"additionalProperty": [
            property_value("File Collections", {"@id": "#fc", "resources": files})]}))
        self.assertEqual(record["file_collections"], [
            {"id": "#fc", "resources": [{"id": "#f", "name": "a file"}]}])
        self.assertEqual((dropped, problems(record)), ([], []))
        # The tracked full crate with the key in its first `isPartOf`
        # reference: the record is the one the crate gives without it, and
        # the key is the one entry more in `dropped`
        crate_json, _ = tracked_full_crate()
        before, before_dropped = converted(crate_json)
        crate_json, root = tracked_full_crate()
        root["isPartOf"][0]["parent_datasets"] = "Bridge2AI program"
        after, after_dropped = converted(crate_json)
        self.assertEqual(after, before)
        self.assertEqual(
            [each for each in after_dropped if each not in before_dropped],
            [said("parent_datasets[0].parent_datasets", "parent_datasets",
                  "Bridge2AI program")])
        self.assertEqual(len(after_dropped), len(before_dropped) + 1)

    def test_additional_property_entries_it_cannot_read_are_reported(self):
        _, dropped = converted(crate({"additionalProperty": [
            "a bare string", {"@type": "Thing", "name": "Other", "value": "x"},
            {"@type": "PropertyValue", "value": "a value with no name"}]}))
        self.assertEqual([source for source, _ in dropped],
                         ["additionalProperty[0]", "additionalProperty[1]",
                          "additionalProperty[2]"])

    def test_an_additional_property_entry_with_no_name_is_recorded(self):
        """Whatever else it carries (#4152). A reference (`{"@id": …}`) is
        RO-Crate's flattened form: the entity it names states the name and
        the value. Until #4152 an entry with no name was recorded only when
        it held a `value`, so a reference reached neither the record nor
        `dropped`: flattened, typed, not in a list, or naming an entity the
        `@graph` does not describe. The reason names the reference, which
        is not looked up in the `@graph`. The same entity written inline
        reaches its slot."""
        entity = {"@id": "#pv-at-risk", "@type": "PropertyValue",
                  "name": "At Risk Populations",
                  "value": "Children under 13 are excluded."}

        def said(n, shown, ref=None):
            return (f"additionalProperty[{n}]", (
                "a PropertyValue with no name written as text, so no slot to "
                f"read it into: {shown}"
                + (f" (a reference to {ref}, which is not looked up in the "
                   "`@graph`)" if ref else "")))

        for entries, shown, ref in (
                ([{"@id": "#pv-at-risk"}], '{"@id": "#pv-at-risk"}',
                 "#pv-at-risk"),
                ([{"@id": "#pv-at-risk", "@type": "PropertyValue"}],
                 '{"@id": "#pv-at-risk", "@type": "PropertyValue"}',
                 "#pv-at-risk"),
                ({"@id": "#pv-at-risk"}, '{"@id": "#pv-at-risk"}',
                 "#pv-at-risk"),
                ([{"@id": "#pv-elsewhere"}], '{"@id": "#pv-elsewhere"}',
                 "#pv-elsewhere"),
                ([{"@type": "PropertyValue"}], '{"@type": "PropertyValue"}',
                 None)):
            with self.subTest(entries=entries):
                record, dropped = converted(
                    crate({"additionalProperty": entries}, entity))
                self.assertEqual(record, {"id": "./", "title": "A test crate"})
                self.assertEqual(dropped, [said(0, shown, ref)])
        inline = {key: value for key, value in entity.items() if key != "@id"}
        record, dropped = converted(crate({"additionalProperty": [inline]}))
        self.assertEqual(texts([record["at_risk_populations"]]),
                         ["Children under 13 are excluded."])
        self.assertEqual(dropped, [])
        # The tracked full crate with the reference added after its entries,
        # and the entity in its `@graph`: the record is the one the crate
        # gives without them, and the reference the one entry more
        crate_json, _ = tracked_full_crate()
        before, before_dropped = converted(crate_json)
        crate_json, root = tracked_full_crate()
        n = len(root["additionalProperty"])
        root["additionalProperty"].append({"@id": "#pv-at-risk"})
        crate_json["@graph"].append(entity)
        after, after_dropped = converted(crate_json)
        self.assertEqual(after, before)
        self.assertEqual(
            [each for each in after_dropped if each not in before_dropped],
            [said(n, '{"@id": "#pv-at-risk"}', "#pv-at-risk")])
        self.assertEqual(len(after_dropped), len(before_dropped) + 1)

    def test_a_start_and_end_date_are_one_collection_timeframe(self):
        record, dropped = converted(crate(
            {"rai:dataCollectionTimeframe": ["2022-09-01", "1/31/2026"]}))
        self.assertEqual(record["collection_timeframes"],
                         [{"start_date": "2022-09-01", "end_date": "2026-01-31"}])
        self.assertEqual(dropped, [])
        self.assertEqual(problems(record), [])
        # Prose about the period is not a start and an end: the VOICE crate
        # writes two sentences, and each describes the period, as before.
        prose = ["Collection began in 2023 and is ongoing.",
                 "Releases are static snapshots."]
        record, dropped = converted(crate({"rai:dataCollectionTimeframe": prose}))
        self.assertEqual(texts(record["collection_timeframes"]), prose)
        self.assertEqual(dropped, [])

    def test_a_date_the_rule_cannot_read_is_reported_not_guessed(self):
        record, dropped = converted(crate(
            {"rai:dataCollectionTimeframe": ["9/1/2022", "1/31/2026"]}))
        self.assertEqual(record["collection_timeframes"],
                         [{"end_date": "2026-01-31"}])
        self.assertIn("ambiguous date '9/1/2022'",
                      reasons(dropped, "collection_timeframes[0].start_date"))
        self.assertEqual(problems(record), [])
        record, dropped = converted(crate({"rai:dataCollectionTimeframe": [
            "2022-01-01", "2022-06-01", "2023-01-01"]}))
        self.assertNotIn("collection_timeframes", record)
        self.assertIn("3 items", reasons(dropped, "rai:dataCollectionTimeframe"))


class TestDatasetParts(unittest.TestCase):
    """#4074: `resources` holds only hasPart members the crate types as
    datasets, and a byte count is never made from a size with a unit."""

    def test_only_members_typed_as_datasets_are_resources(self):
        record, dropped = converted(crate(
            {"hasPart": [{"@id": "#tool"}, {"@id": "#step"},
                         {"@id": "https://orcid.org/0000-0002-1825-0097"},
                         {"@id": "ark:59853/schema-undescribed"},
                         {"@id": "#evi-files"},
                         {"@id": "ark:59853/rocrate-elsewhere",
                          "@type": "Dataset"}]},
            {"@id": "#tool", "@type": "https://w3id.org/EVI#Software", "name": "T"},
            {"@id": "#step", "@type": "https://w3id.org/EVI#Computation", "name": "S"},
            {"@id": "https://orcid.org/0000-0002-1825-0097", "@type": "Person",
             "name": "P"},
            {"@id": "#evi-files", "@type": "https://w3id.org/EVI#Dataset",
             "name": "EVI-typed files"}))
        # A described dataset is a file collection; one only a reference
        # types is a component dataset
        self.assertEqual([fc["id"] for fc in record["file_collections"]],
                         ["#evi-files"])
        self.assertEqual(record["resources"],
                         [{"id": "https://n2t.net/ark:59853/rocrate-elsewhere"}])
        why = reasons(dropped, "hasPart")
        for ref in ("#tool", "#step", "https://orcid.org/0000-0002-1825-0097"):
            self.assertIn(f"{ref}: the crate types it", why)
        self.assertIn("ark:59853/schema-undescribed: the crate's `@graph` does "
                      "not describe it", why)
        self.assertEqual(problems(record), [])

    def test_total_size_bytes_is_the_crates_byte_count(self):
        from data_sheets_schema.rocrate_map import (
            MAPPING_TSV, load_mapping, map_crate)
        root = next(e for e in json.loads(FULL.read_text(encoding="utf-8"))["@graph"]
                    if "Dataset" in e.get("@type", []))
        record, dropped = converted(FULL)
        self.assertEqual(record["total_size_bytes"],
                         root["evi:totalContentSizeBytes"])
        self.assertIn(f"'{root['contentSize']}' is a size with a unit",
                      reasons(dropped, "contentSize"))
        mapped = map_crate(json.loads(FULL.read_text(encoding="utf-8"))["@graph"],
                           load_mapping(repo_root / MAPPING_TSV),
                           FairscapeToD4DConverter()._schema_view())
        self.assertEqual(record["total_size_bytes"],
                         mapped.record["total_size_bytes"])

    def test_a_size_with_a_unit_is_not_converted(self):
        for size, expected in (("2 GB", None), ("2048", 2048),
                               ("2048 bytes", 2048), (2048, 2048)):
            with self.subTest(size=size):
                record, dropped = converted(crate(
                    {"contentSize": size, "hasPart": [{"@id": "#raw"}]},
                    {"@id": "#raw", "@type": "Dataset", "name": "Raw files",
                     "contentSize": size}))
                self.assertEqual(record.get("total_size_bytes"), expected)
                self.assertEqual(record["file_collections"][0].get("total_bytes"),
                                 expected)
                if expected is None:
                    self.assertIn("a size with a unit",
                                  reasons(dropped, "contentSize"))
                    self.assertIn("a size with a unit",
                                  reasons(dropped, "#raw.contentSize"))
                else:
                    self.assertEqual(dropped, [])

    def test_the_byte_count_supersedes_a_content_size_that_disagrees(self):
        """`evi:totalContentSizeBytes` is the size, and a byte `contentSize`
        that differs from it is named, for the root and for a file
        collection (#4099)."""
        record, dropped = converted(crate(
            {"contentSize": "2048", "evi:totalContentSizeBytes": 4096,
             "hasPart": [{"@id": "#raw"}]},
            {"@id": "#raw", "@type": "Dataset", "name": "Raw files",
             "contentSize": "2048", "evi:totalContentSizeBytes": 4096}))
        self.assertEqual(record["total_size_bytes"], 4096)
        self.assertEqual(record["file_collections"][0]["total_bytes"], 4096)
        self.assertEqual(dict(dropped), {
            "contentSize": ("superseded by evi:totalContentSizeBytes, which "
                            "also maps to `total_size_bytes`"),
            "#raw.contentSize": ("not placed in `total_bytes`: 2048; superseded "
                                 "by evi:totalContentSizeBytes, 4096")})

    def test_a_total_content_size_that_is_not_a_count_is_recorded(self):
        record, dropped = converted(crate({"evi:totalContentSizeBytes": "19.1 TB"}))
        self.assertNotIn("total_size_bytes", record)
        self.assertIn("not placed in `total_size_bytes`: '19.1 TB' is a size "
                      "with a unit", reasons(dropped, "evi:totalContentSizeBytes"))

    def test_a_byte_count_may_group_its_digits(self):
        """Commas in threes, and `BYTES` in any case, are a byte count; a
        size is not one, and the reason says what the size states (#4098)."""
        for size, expected in (("2,048 bytes", 2048), ("2,048", 2048),
                               ("2,048 B", 2048), ("1,000,000 bytes", 1000000),
                               ("2048 BYTES", 2048)):
            with self.subTest(size=size):
                record, dropped = converted(crate({"contentSize": size}))
                self.assertEqual(record["total_size_bytes"], expected)
                self.assertEqual(dropped, [])
        for size, said, unsaid in (
                ("2 GiB", "is a size with a 1024-based unit", "1000- or 1024"),
                ("2048 KiB", "is a size with a 1024-based unit", "1000- or 1024"),
                ("2 GB", "does not state whether the unit is 1000- or 1024-based",
                 "1024-based unit"),
                ("2,04 bytes", "is not a byte count", "a size with"),
                ("2 widgets", "is not a byte count", "a size with")):
            with self.subTest(size=size):
                record, dropped = converted(crate({"contentSize": size}))
                self.assertNotIn("total_size_bytes", record)
                self.assertIn(said, reasons(dropped, "contentSize"))
                self.assertNotIn(unsaid, reasons(dropped, "contentSize"))

    def test_a_part_typed_only_as_a_crate_is_a_file_collection(self):
        """An RO-Crate is a dataset of its own (`is_dataset`, #4099)."""
        record, dropped = converted(crate(
            {"hasPart": [{"@id": "#sub"}]},
            {"@id": "#sub", "@type": "https://w3id.org/EVI#ROCrate",
             "name": "A sub-crate"}))
        self.assertEqual(record["file_collections"],
                         [{"id": "#sub", "name": "A sub-crate"}])
        self.assertEqual(dropped, [])

    def test_a_references_keys_are_fitted_or_recorded(self):
        """An `isPartOf` reference, and a `hasPart` member only its
        reference types as a dataset, keep the keys Dataset declares, and
        each other key is named (#4098). They used to become `{id}`."""
        reference = {"@type": "Dataset", "name": "Project X",
                     "description": "The parent project",
                     "url": "https://example.org/x", "funder": "NIH"}
        record, dropped = converted(crate({
            "isPartOf": [{"@id": "ark:59852/project-x", **reference}],
            "hasPart": [{"@id": "ark:59853/rocrate-y", **reference}]}))
        for slot, ref in (("parent_datasets", "ark:59852/project-x"),
                          ("resources", "ark:59853/rocrate-y")):
            with self.subTest(slot=slot):
                self.assertEqual(record[slot], [{
                    "id": f"https://n2t.net/{ref}", "name": "Project X",
                    "description": "The parent project"}])
                for key in ("url", "funder"):
                    self.assertEqual(
                        reasons(dropped, f"{slot}[0].{key}"),
                        f"the schema declares no `{key}` slot on Dataset")
        self.assertEqual(len(dropped), 4)
        self.assertEqual(problems(record), [])

    def test_what_a_part_reference_says_beyond_its_entity_is_recorded(self):
        """A member the `@graph` describes is a file collection made from
        that entity. A key the reference states that the entity does not,
        or states otherwise, is named (#4098); one it states as the entity
        does is not, as on CHORUS (`TestRootDataEntity`)."""
        record, dropped = converted(crate(
            {"hasPart": [{"@id": "#raw", "@type": "Dataset", "name": "Raw files",
                          "description": "Said only here"},
                         {"@id": "#other", "name": "Another name"}]},
            {"@id": "#raw", "@type": "Dataset", "name": "Raw files"},
            {"@id": "#other", "@type": "Dataset", "name": "Other files"}))
        self.assertEqual([fc["name"] for fc in record["file_collections"]],
                         ["Raw files", "Other files"])
        why = reasons(dropped, "hasPart")
        self.assertIn("#raw: `description` Said only here, which the root's "
                      "`hasPart` states for it, is not what the `@graph`'s "
                      "entity for it states", why)
        self.assertIn("#other: `name` Another name", why)
        self.assertNotIn("#raw: `name`", why)
        self.assertEqual(len(dropped), 2)

    def test_an_ark_in_any_identifier_slot_is_its_resolver_url(self):
        record, _ = converted(crate({
            "publisher": "ark:59852/organization-x",
            "contentUrl": "ark:59853/download-x",
            "author": [{"@id": "ark:59853/person-x", "name": "Jane Doe"}]}))
        self.assertEqual(record["publisher"],
                         "https://n2t.net/ark:59852/organization-x")
        self.assertEqual(record["download_url"],
                         "https://n2t.net/ark:59853/download-x")
        self.assertEqual(record["creators"][0]["id"],
                         "https://n2t.net/ark:59853/person-x")

    def test_the_arms_differ_only_where_the_converter_says_they_do(self):
        """Every slot this converter and the static-map arm both write holds
        the same value, apart from a split author string, a start and end
        date, and `prohibited_uses`, which this converter fills from two
        crate properties."""
        from data_sheets_schema.rocrate_map import (
            MAPPING_TSV, load_mapping, map_crate)
        rows = load_mapping(repo_root / MAPPING_TSV)
        view = FairscapeToD4DConverter()._schema_view()
        expected = {BUNDLED[0]: {"creators", "collection_timeframes",
                                 "prohibited_uses"},
                    BUNDLED[1]: {"creators", "collection_timeframes"},
                    BUNDLED[2]: {"creators"},
                    BUNDLED[3]: {"creators"}}
        for path, differ in expected.items():
            with self.subTest(crate=path):
                crate_json = json.loads((repo_root / path).read_text(encoding="utf-8"))
                ours, _ = converted(crate_json)
                theirs = map_crate(crate_json["@graph"], rows, view).record
                self.assertEqual({slot for slot in set(ours) & set(theirs)
                                  if ours[slot] != theirs[slot]}, differ)


class TestTheRecordValidates(unittest.TestCase):
    """#4098: every record `convert` returns validates, and each value the
    schema rejects is left out and named in `dropped` with the validator's
    message, whatever the per-slot rules let through."""

    def assert_left_out(self, crate_json, slot, source, *said):
        """`slot` is not in the record, which validates, and `source` is
        named in `dropped` with a reason saying each of `said`."""
        record, dropped = converted(crate_json)
        self.assertNotIn(slot, record)
        self.assertEqual(problems(record), [])
        why = reasons(dropped, source)
        for text in said:
            self.assertIn(text, why)
        return record, dropped

    def test_the_ai_readi_release_date_is_left_out(self):
        """The tracked AI-READI v3.0.0 release crate's root has
        `datePublished: 11/17/25`, which `_coerce` leaves as written. The
        file is windows-1252 (#4089), so it is decoded as that here."""
        crate_json = json.loads(AI_READI.read_bytes().decode("cp1252"))
        _, dropped = self.assert_left_out(
            crate_json, "issued", "datePublished",
            "not placed in `issued`: 11/17/25 (the schema rejects it: "
            "'11/17/25' is not a 'date-time')")
        self.assertEqual({source for source, _ in dropped},
                         {"contentSize", "datePublished"})

    def test_a_date_time_the_date_rule_does_not_read_is_left_out(self):
        for key, slot, value in (("datePublished", "issued", "June 2026"),
                                 ("datePublished", "issued", "2026"),
                                 ("datePublished", "issued", "11/17/25"),
                                 ("dateCreated", "created_on", "2026-01")):
            with self.subTest(key=key, value=value):
                self.assert_left_out(
                    crate({key: value}), slot, key,
                    f"not placed in `{slot}`: {value} (the schema rejects it: "
                    f"'{value}' is not a 'date-time')")

    def test_a_one_item_list_is_read_as_its_item(self):
        """For a single-valued slot, before the date in it is read: as
        `_coerce` reads it, `["2026-06-30"]` kept a date the slot does not
        take."""
        for key, slot, value, expected in (
                ("datePublished", "issued", ["2026-06-30"], "2026-06-30T00:00:00Z"),
                ("dateModified", "last_updated_on", ["2026-01-31"],
                 "2026-01-31T00:00:00Z"),
                ("datePublished", "issued", ["12/16/2025"], "2025-12-16T00:00:00Z")):
            with self.subTest(value=value):
                record, dropped = converted(crate({key: value}))
                self.assertEqual(record[slot], expected)
                self.assertEqual(dropped, [])
                self.assertEqual(problems(record), [])
        # A date the rule will not guess is refused in a list as on its own
        self.assert_left_out(crate({"datePublished": ["9/1/2022"]}), "issued",
                             "datePublished", "ambiguous date '9/1/2022'")

    def test_a_count_written_as_text_is_left_out(self):
        record, dropped = converted(crate(
            {"hasPart": [{"@id": "#raw"}]},
            {"@id": "#raw", "@type": "Dataset", "name": "Raw files",
             "d4d:fileCount": "200"}))
        self.assertEqual(record["file_collections"],
                         [{"id": "#raw", "name": "Raw files"}])
        self.assertEqual(dropped, [("file_collections[0].file_count", (
            "not placed in `file_count`: 200 (the schema rejects it: '200' is "
            "not of type 'integer', 'null')"))])
        self.assertEqual(problems(record), [])

    def test_an_object_without_a_required_key_is_left_out_whole(self):
        self.assert_left_out(
            crate({"rai:dataCollectionRawData": {"@id": "#raw"}}),
            "raw_data_sources", "rai:dataCollectionRawData",
            'not placed in `raw_data_sources`: {"id": "#raw"} (the schema '
            "rejects it: 'source_description' is a required property)")
        # Beside one its class can hold, it is a part of the value
        record, dropped = converted(crate({"rai:dataCollectionRawData": [
            {"@id": "#raw"}, "Survey responses."]}))
        self.assertEqual(record["raw_data_sources"],
                         [{"source_description": "Survey responses."}])
        self.assertIn('part of the value not placed in `raw_data_sources`: '
                      '{"id": "#raw"}',
                      reasons(dropped, "rai:dataCollectionRawData"))
        self.assertEqual(problems(record), [])

    def test_leaving_a_required_value_out_leaves_its_object_out(self):
        """The schema rejects the object's required key, and then the object
        that lacks it, a pass later: three validations, the last of them
        the one that finds the record valid."""
        crate_json = crate({"rai:dataCollectionRawData": [
            {"@id": "#raw", "source_description": 5}]})
        record, dropped, passes = validated(crate_json)
        self.assertNotIn("raw_data_sources", record)
        self.assertEqual(dropped, [
            ("raw_data_sources[0].source_description", (
                "not placed in `source_description`: 5 (the schema rejects it: "
                "5 is not of type 'string')")),
            ("rai:dataCollectionRawData", (
                'not placed in `raw_data_sources`: {"id": "#raw"} (the schema '
                "rejects it: 'source_description' is a required property)"))])
        self.assertEqual(problems(record), [])
        self.assertEqual(passes, 3)

    def test_a_value_inside_one_left_out_goes_with_it(self):
        """The object lacks its required key, and its `id` is not text: it
        is left out once, with both messages, the second saying where in
        the object it is (#4126)."""
        record, dropped = converted(crate(
            {"rai:dataCollectionRawData": [{"@id": "#raw", "id": 5}]}))
        self.assertNotIn("raw_data_sources", record)
        self.assertEqual(reasons(dropped, "rai:dataCollectionRawData"), (
            'not placed in `raw_data_sources`: {"id": 5} (the schema rejects '
            "it: 'source_description' is a required property; 5 is not of "
            "type 'string', 'null' in `id`)"))
        self.assertEqual([source for source, _ in dropped],
                         ["raw_data_sources[0].@id", "rai:dataCollectionRawData"])

    def test_each_rejected_item_of_a_list_is_named(self):
        """Left out last first, so each is the item named; the reason
        quotes the item, which is text or a number, and gives no position
        (#4126)."""
        record, dropped = converted(crate({"keywords": [7, "a", 8]}))
        self.assertEqual(record["keywords"], ["a"])
        self.assertEqual(dropped, [
            ("keywords", "part of the value not placed in `keywords`: 7 (the "
                         "schema rejects it: 7 is not of type 'string')"),
            ("keywords", "part of the value not placed in `keywords`: 8 (the "
                         "schema rejects it: 8 is not of type 'string')")])

    def test_a_key_its_class_does_not_declare_is_left_out_by_name(self):
        """`_fit` keeps only declared keys, so this reaches `_settle` only
        if something else adds one; the closed schema names it, and only it
        goes. LinkML closes every nested class; the record's own top level
        is closed only because the validator asks for it (`closed=True`)."""
        converter = FairscapeToD4DConverter()
        record = converter._settle(
            {"id": "./", "alias": "C",
             "creators": [{"name": "A", "nickname": "B"}]},
            {"alias": "alternateName", "creators": "author"}, {})
        self.assertEqual(record, {"id": "./", "creators": [{"name": "A"}]})
        self.assertEqual(converter.dropped, [
            ("alternateName", (
                "not placed in `alias`: C (the schema rejects it: Additional "
                "properties are not allowed ('alias' was unexpected))")),
            ("creators[0].nickname", (
                "not placed in `nickname`: B (the schema rejects it: Additional "
                "properties are not allowed ('nickname' was unexpected))"))])

    def test_a_record_no_value_left_out_can_make_valid_is_an_error(self):
        """A root with no `@id` and no `identifier` gives no `id`, which the
        schema requires and leaving values out cannot supply."""
        with self.assertRaisesRegex(
                ValueError, "cannot be made valid by leaving values out: "
                            "'id' is a required property"):
            converted({"@graph": [{"@type": ROCRATE, "name": "No identifier"}]})

    def test_whatever_the_crate_holds_the_record_validates(self):
        """A value of the wrong kind for each slot it maps to: each one is
        either in the record or named in `dropped`."""
        values = {
            "identifier": {"@id": "#not-text"}, "datePublished": "June 2026",
            "dateModified": ["9/1/2022"], "dateCreated": 2026, "license": 5,
            "version": {"v": 1}, "keywords": [{"@id": "#k"}, 7],
            "url": ["https://a.example", "https://b.example"],
            "publisher": {"@id": "ark:59852/org"}, "contentUrl": 12,
            "contentSize": "lots", "isPartOf": "ark:59852/project",
            "rai:dataCollectionRawData": [{"@id": "#raw"}, "Survey."],
            "rai:dataCollectionTimeframe": ["2022-09-01", "2026-13-45"],
            "d4d:humanSubject": True, "d4d:atRiskPopulations": [{"@value": "x"}],
            "evi:totalContentSizeBytes": -1,
        }
        #: The slot each property maps to (`_map_basic_properties` and on)
        slots = {"identifier": "doi", "datePublished": "issued",
                 "dateModified": "last_updated_on", "dateCreated": "created_on",
                 "license": "license", "version": "version",
                 "keywords": "keywords", "url": "page", "publisher": "publisher",
                 "contentUrl": "download_url", "contentSize": "total_size_bytes",
                 "isPartOf": "parent_datasets",
                 "rai:dataCollectionRawData": "raw_data_sources",
                 "rai:dataCollectionTimeframe": "collection_timeframes",
                 "d4d:humanSubject": "human_subject_research",
                 "d4d:atRiskPopulations": "at_risk_populations",
                 "evi:totalContentSizeBytes": "total_size_bytes"}
        record, dropped = converted(crate(values))
        self.assertEqual(problems(record), [])
        named = {source for source, _ in dropped}
        for key, slot in slots.items():
            with self.subTest(key=key):
                self.assertTrue(
                    slot in record or key in named
                    or any(source.startswith(slot) for source in named),
                    f"{key} is neither in `{slot}` nor named in `dropped`")
        # The end date's month is 13: the date rule writes it, the schema
        # does not accept it
        self.assertIn("'2026-13-45' is not a 'date'",
                      reasons(dropped, "collection_timeframes[0].end_date"))

    def test_a_wrong_value_in_a_reference_goes_alone(self):
        """An item of `parent_datasets` or `resources` may be a Dataset or a
        DataSubset, and the validator reports one error for the whole item.
        The value at fault goes, named by its key, and the reference stays
        (#4125). The whole reference used to go, under a reason that named
        no key."""
        record, dropped = converted(crate({
            "isPartOf": [{"@id": "ark:59852/project-x", "name": "Project X",
                          "version": 2, "keywords": ["a", 7]}],
            "hasPart": [{"@id": "ark:59853/rocrate-y", "@type": "Dataset",
                         "name": "Y", "license": 5}]}))
        self.assertEqual(record["parent_datasets"], [{
            "id": "https://n2t.net/ark:59852/project-x", "name": "Project X",
            "keywords": ["a"]}])
        self.assertEqual(record["resources"], [{
            "id": "https://n2t.net/ark:59853/rocrate-y", "name": "Y"}])
        self.assertEqual(dropped, [
            ("resources[0].license", (
                "not placed in `license`: 5 (the schema rejects it: 5 is not "
                "of type 'string', 'null')")),
            ("parent_datasets[0].version", (
                "not placed in `version`: 2 (the schema rejects it: 2 is not "
                "of type 'string', 'null')")),
            ("parent_datasets[0].keywords", (
                "part of the value not placed in `keywords`: 7 (the schema "
                "rejects it: 7 is not of type 'string')"))])
        self.assertEqual(problems(record), [])

    def test_the_class_that_needs_the_fewest_values_left_out_is_taken(self):
        """As a Dataset this parent loses `is_data_split` and `version`; as
        a DataSubset, which declares `is_data_split`, only `version`."""
        converter = FairscapeToD4DConverter()
        record = converter._settle(
            {"id": "./", "parent_datasets": [
                {"id": "#p", "is_data_split": True, "version": 2}]},
            {"parent_datasets": "isPartOf"}, {})
        self.assertEqual(record, {"id": "./", "parent_datasets": [
            {"id": "#p", "is_data_split": True}]})
        self.assertEqual(converter.dropped, [("parent_datasets[0].version", (
            "not placed in `version`: 2 (the schema rejects it: 2 is not of "
            "type 'string', 'null')"))])
        self.assertEqual(problems(record), [])

    def test_a_value_every_class_rejects_goes_whole(self):
        """An object that lacks a required key is rejected whole by both
        classes, and a number by a class and by nothing: each goes whole,
        for the reasons its slot's own class gives, a value inside it
        named by where it is in it (#4125)."""
        converter = FairscapeToD4DConverter()
        record = converter._settle(
            {"id": "./",
             "parent_datasets": [{"name": "no id", "version": 2,
                                  "keywords": ["a", 7]}],
             "human_subject_research": 5},
            {"parent_datasets": "isPartOf",
             "human_subject_research": "d4d:humanSubject"}, {})
        self.assertEqual(record, {"id": "./"})
        self.assertEqual(converter.dropped, [
            ("isPartOf", (
                'not placed in `parent_datasets`: {"name": "no id", "version": '
                '2, "keywords": ["a", 7]} (the schema rejects it: \'id\' is a '
                "required property; 2 is not of type 'string', 'null' in "
                "`version`; 7 is not of type 'string' in `keywords`)")),
            ("d4d:humanSubject", (
                "not placed in `human_subject_research`: 5 (the schema rejects "
                "it: 5 is not of type 'object')"))])

    def test_an_object_slot_leaves_out_every_wrong_value_in_one_pass(self):
        """A single-valued object slot may hold its class or nothing, and
        the validator reports one error for the whole object. Every value
        its class rejects goes in the same pass (#4125, #4126): it used to
        be one a pass, and 25 IRB numbers ran past the 20-pass limit."""
        numbers = list(range(2019001, 2019026))
        record, dropped, passes = validated(crate({"d4d:humanSubject": {
            "@id": "#hsr", "description": "Approved.", "irb_approval": numbers,
            "ethics_review_board": 6, "name": 8}}))
        self.assertEqual(record["human_subject_research"],
                         {"id": "#hsr", "description": "Approved."})
        self.assertEqual(passes, 2)
        self.assertEqual(
            [reason for source, reason in dropped
             if source == "human_subject_research.irb_approval"],
            [f"part of the value not placed in `irb_approval`: {n} (the schema "
             f"rejects it: {n} is not of type 'string')" for n in numbers])
        self.assertEqual(
            {source for source, _ in dropped},
            {"human_subject_research.irb_approval",
             "human_subject_research.ethics_review_board",
             "human_subject_research.name"})
        self.assertEqual(problems(record), [])

    def test_any_number_of_rejected_values_for_one_slot_is_left_out(self):
        """Each value waiting for `issued` is tried once, and as a text with
        nothing nested in it costs one pass; there is no limit on passes,
        which end because each leaves a value out (#4126). 26 `issued`
        values ran past the 20-pass limit, and the crate was an error
        although leaving them out makes it valid. A value with values
        nested in it can cost more (#4139)."""
        values = [f"Month {n} 2026" for n in range(25)]
        record, dropped = converted(crate({
            "datePublished": "Month X 2026",
            "additionalProperty": [property_value("Issued", value)
                                   for value in values]}))
        self.assertNotIn("issued", record)
        self.assertEqual(problems(record), [])
        self.assertEqual(sorted(reason for _, reason in dropped), sorted(
            f"not placed in `issued`: {value} (the schema rejects it: "
            f"'{value}' is not a 'date-time')"
            for value in ["Month X 2026", *values]))

    def test_a_waiting_value_can_cost_a_pass_for_each_level_it_nests(self):
        """Each of the six values for `human_subject_research`, the one
        placed and the five waiting, holds a software whose `id` is not
        text. One pass leaves out the `id`, the next the software that then
        lacks it, with the objects it leaves empty, and the slot takes the
        next value. That is two passes for each of the six, and one that
        finds the record valid: 13 validations. The root has no `name`, so
        the record holds its `id` and the slot's value alone. The bound
        `_settle` stated until #4139 counted each waiting value once: the
        record's values at the start, nested ones included (`id`, the
        object, its `used_software` list, the software, its `id` and
        `name`: 6), the 5 waiting and the last pass, 12, one short. It now
        counts what each waiting value brings into the record, nested
        values included. Until #4153 the root had a `name`, whose `title`
        made that count 13, the number of validations, so the test ran a
        case the old bound did not miss."""
        def research(tool):
            return {"used_software": [{"id": 5, "name": tool}]}

        tools = [f"tool {n}" for n in range(5)]
        crate_json = crate({
            "d4d:humanSubject": research("tool A"),
            "additionalProperty": [property_value("Human Subject", research(tool))
                                   for tool in tools]})
        del crate_json["@graph"][1]["name"]
        record, dropped, passes = validated(crate_json)
        self.assertEqual(record, {"id": "./"})
        self.assertEqual(passes, 13)
        self.assertEqual(sorted(dropped), sorted(
            [("human_subject_research.used_software[0].id", (
                "not placed in `id`: 5 (the schema rejects it: 5 is not of "
                "type 'string')"))] * 6
            + [("human_subject_research.used_software", (
                f'not placed in `used_software`: {{"name": "{tool}"}} (the '
                "schema rejects it: 'id' is a required property)"))
               for tool in ["tool A", *tools]]))


class TestDroppedPaths(unittest.TestCase):
    """#4126: a `dropped` path numbers the items of a list one way, by the
    item's position in the list the converter read for the slot, the
    crate's list for a crate property. That position is the same in every
    validation pass, and whether or not the item reached the record."""

    def test_an_object_is_numbered_by_its_place_in_the_crate(self):
        """The first author yields no Creator, the first `isPartOf` entry is
        text and the first `hasPart` member is software, so the object made
        from each second one is the first of its list in the record. It is
        named by its place in the crate both by `_object`, which reads it,
        and by `_leave_out`, which validates it. They used to number it
        apart: `creators[1].email` and `creators[0].name`."""
        record, dropped = converted(crate({
            "author": [{"@type": "Person"},
                       {"@id": "#b", "name": 5, "email": "b@example.org"}],
            "isPartOf": ["Project X", {"@id": "ark:59852/project-y",
                                       "version": 2}],
            "hasPart": [{"@id": "#tool"},
                        {"@id": "ark:59853/rocrate-y", "@type": "Dataset",
                         "license": 5}]},
            {"@id": "#tool", "@type": "https://w3id.org/EVI#Software",
             "name": "T"}))
        self.assertEqual(record["creators"], [{"id": "#b"}])
        self.assertEqual(record["parent_datasets"],
                         [{"id": "https://n2t.net/ark:59852/project-y"}])
        self.assertEqual(record["resources"],
                         [{"id": "https://n2t.net/ark:59853/rocrate-y"}])
        self.assertEqual(
            [source for source, _ in dropped
             if source.startswith(("creators", "parent_datasets", "resources"))],
            ["creators[1].email", "creators[1].name", "resources[1].license",
             "parent_datasets[1].version"])
        self.assertEqual(problems(record), [])
        # A JSON null is an item of the crate's list too
        record, dropped = converted(crate({"author": [
            None, {"@id": "#b", "name": 5}]}))
        self.assertEqual(record["creators"], [{"id": "#b"}])
        self.assertEqual([source for source, _ in dropped], ["creators[1].name"])

    def test_an_object_keeps_its_number_from_pass_to_pass(self):
        """`#r1`'s software loses its `id` in the first pass, and is left
        out in the second, after `#r0` went in the first; it was named
        `raw_data_sources[1]` and then `raw_data_sources[0]`. No reason
        quotes LinkML's pointer, which numbers the record as one pass saw
        it."""
        record, dropped = converted(crate({"rai:dataCollectionRawData": [
            {"@id": "#r0"},
            {"@id": "#r1", "source_description": "Survey.",
             "used_software": [{"id": 5, "name": "tool"}]}]}))
        self.assertEqual(record["raw_data_sources"],
                         [{"id": "#r1", "source_description": "Survey."}])
        self.assertEqual(dropped, [
            ("rai:dataCollectionRawData", (
                'part of the value not placed in `raw_data_sources`: {"id": '
                "\"#r0\"} (the schema rejects it: 'source_description' is a "
                "required property)")),
            ("raw_data_sources[1].used_software[0].id", (
                "not placed in `id`: 5 (the schema rejects it: 5 is not of "
                "type 'string')")),
            ("raw_data_sources[1].used_software", (
                'not placed in `used_software`: {"name": "tool"} (the schema '
                "rejects it: 'id' is a required property)"))])
        self.assertEqual(problems(record), [])


class TestValidationIsNotVacuous(unittest.TestCase):

    def test_a_schema_that_cannot_be_found_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "record.yaml"
            output.write_text("id: ./\n", encoding="utf-8")
            with mock.patch.object(fairscape_to_d4d, "resource_path",
                                   return_value=Path(tmp) / "absent.yaml"):
                self.assertFalse(quietly(
                    FairscapeToD4DConverter()._validate_d4d, output))


if __name__ == "__main__":
    unittest.main()
