#!/usr/bin/env python3
"""
Tests for the FAIRSCAPE RO-Crate → D4D converter's output contract.

#3969: every bundled crate converted and wrote YAML, then exited 1 because
its own output failed D4D validation. The record is now fitted to the
schema's Dataset class, and what cannot be placed is recorded in `dropped`.
#3973: the converter read `rai:` spellings of three keys FAIRSCAPE writes
otherwise.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
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
)

SCHEMA = repo_root / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

#: Every FAIRSCAPE crate the repository bundles, the four
#: `make test-fairscape-to-d4d` converts.
BUNDLED = (
    "data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json",
    "data/ro-crate/examples/CM4AI_roundtrip.json",
    "data/ro-crate/examples/voice_d4d_to_fairscape.json",
    "data/ro-crate/examples/voice_fairscape_test.json",
)
FULL = repo_root / BUNDLED[0]


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


def crate(root):
    """A one-dataset crate whose root entity carries `root`."""
    return {
        "@context": {"@vocab": "https://schema.org/"},
        "@graph": [
            {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
             "about": {"@id": "./"}},
            {"@id": "./", "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
             "name": "A test crate", **root},
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

    def test_exactly_the_values_without_a_slot_are_dropped(self):
        for path, expected in self.NO_SLOT.items():
            with self.subTest(crate=path):
                converter = FairscapeToD4DConverter()
                quietly(converter.convert, repo_root / path)
                self.assertEqual({source for source, _ in converter.dropped},
                                 expected)
                for source, reason in converter.dropped:
                    self.assertIn("the schema declares no", reason)

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
        from click.testing import CliRunner
        from src.fairscape_integration.cli import cli

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "record.yaml"
            result = CliRunner().invoke(
                cli, ["rocrate-to-d4d", str(FULL), "-o", str(output)])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(
                problems(yaml.safe_load(output.read_text(encoding="utf-8"))), [])
        for source in self.NO_SLOT[BUNDLED[0]]:
            self.assertIn(f"not placed: {source}:", result.output)

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
        root = next(e for e in json.loads(FULL.read_text(encoding="utf-8"))["@graph"]
                    if "Dataset" in e.get("@type", []))
        record = quietly(FairscapeToD4DConverter().convert, FULL)
        for prop, slot in (("hasPart", "resources"), ("isPartOf", "parent_datasets")):
            with self.subTest(slot=slot):
                self.assertEqual(
                    [item["id"] for item in record[slot]],
                    ["https://n2t.net/" + item["@id"] for item in root[prop]])

    def test_the_record_id_comes_from_the_crate_root(self):
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
