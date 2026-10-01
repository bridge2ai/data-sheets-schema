#!/usr/bin/env python3
"""
Tests for the FAIRSCAPE RO-Crate → D4D converter's output contract.

#3969: every crate under data/ro-crate converted and wrote YAML, then
exited 1 because its own output failed D4D validation. The record is now
fitted to the schema's Dataset class, and what cannot be placed is recorded
in `dropped`. #3973: the converter read `rai:` spellings of three keys
FAIRSCAPE writes otherwise. #4072: the record describes the crate's root
data entity, not the last sub-crate in the @graph. #4073: the part of a
value a slot cannot hold is recorded too, and nothing is joined as a
Python repr. #4074: `resources` holds only hasPart members the crate types
as datasets, and `total_size_bytes` only a byte count.
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
#: data/ro-crate_packages/ are not among them (`TestRootDataEntity` converts
#: CM4AI's), and AI_READI's is not UTF-8.
BUNDLED = (
    "data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json",
    "data/ro-crate/examples/CM4AI_roundtrip.json",
    "data/ro-crate/examples/voice_d4d_to_fairscape.json",
    "data/ro-crate/examples/voice_fairscape_test.json",
)
FULL = repo_root / BUNDLED[0]

#: The CM4AI June 2026 release crate as published, and as `d4d rocrate
#: normalize` reduced it: ten entities typed ROCrate, the release and nine
#: sub-crates, in one @graph (#4072).
CM4AI_ZIP = repo_root / "data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip"
CM4AI_REDUCED = (repo_root / "data/ro-crate_packages/CM4AI/processed/"
                 "CM4AI_crate_metadata_reduced.json")
CM4AI_RELEASE = ("https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-"
                 "artificial-intelligence-June-2026-data-release")


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
    in the @graph."""
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
    #: its four hasPart members the @graph does not describe, and the
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
        from click.testing import CliRunner
        from src.fairscape_integration.cli import cli

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "record.yaml"
            result = CliRunner().invoke(
                cli, ["rocrate-to-d4d", str(FULL), "-o", str(output)])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(
                problems(yaml.safe_load(output.read_text(encoding="utf-8"))), [])
        for source in self.NO_SLOT[BUNDLED[0]] | set(self.CANNOT_HOLD[BUNDLED[0]]):
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
    """A release crate the way FAIRSCAPE writes one: the descriptor is about
    the release, and its two sub-crates, typed ROCrate like it, come before
    and after it in the @graph, so neither the first nor the last ROCrate
    entity is the release."""
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
        """Only the entity whose @id is `ro-crate-metadata.json` is the
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
        named the root."""
        path = repo_root / "data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json"
        graph = json.loads(path.read_text(encoding="utf-8"))["@graph"]
        root = root_data_entity(graph)
        record, _ = converted(path)
        self.assertEqual(record["id"], "doi:10.18130/V3/XNBOPG")
        self.assertEqual(record["title"], root["name"])
        # In @graph order, as before
        self.assertEqual(sorted(fc["id"] for fc in record["file_collections"]),
                         sorted(part["@id"] for part in root["hasPart"]))
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

    def test_additional_property_entries_it_cannot_read_are_reported(self):
        _, dropped = converted(crate({"additionalProperty": [
            "a bare string", {"@type": "Thing", "name": "Other", "value": "x"},
            {"@type": "PropertyValue", "value": "a value with no name"}]}))
        self.assertEqual([source for source, _ in dropped],
                         ["additionalProperty[0]", "additionalProperty[1]",
                          "additionalProperty[2]"])

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
        self.assertIn("ark:59853/schema-undescribed: the crate's @graph does not "
                      "describe it", why)
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
