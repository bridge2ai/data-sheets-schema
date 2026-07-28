"""Tests for RO-Crate normalization into D4D-usable artifacts."""

import json
import tempfile
import unittest
from pathlib import Path

from linkml_runtime import SchemaView

import yaml

from data_sheets_schema.rocrate_normalize import (
    DE_NOVO_EXCLUDE,
    DE_NOVO_INCLUDE,
    FULL_SCHEMA,
    DeNovoPolicyError,
    Result,
    _doi_key,
    _org_urn,
    assert_de_novo_safe,
    build_crate_bundle,
    build_person_index,
    document_corpus_exclusions,
    normalize_linkml,
    reduce_metadata,
)

PERSON_GRAPH = {
    "@graph": [
        {
            "@id": "https://orcid.org/0000-0003-4060-7360",
            "@type": "Person",
            "name": "Clark, T",
            "affiliation": {"@type": "Organization", "name": "University of Virginia"},
        },
        {"@id": "ark:59853/thing", "@type": "Dataset", "name": "not a person"},
    ]
}


class TestNormalizeLinkML(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sv = SchemaView(str(FULL_SCHEMA))
        cls.persons = build_person_index(PERSON_GRAPH)

    def normalize(self, doc):
        res = Result(project="TEST")
        return normalize_linkml(doc, self.persons, self.sv, res), res

    def test_bytes_remaps_rather_than_drops(self):
        """`bytes` carries a real size fact and must survive as total_size_bytes."""
        out, res = self.normalize({"name": "d", "bytes": 1319413953331})
        self.assertNotIn("bytes", out)
        self.assertEqual(out["total_size_bytes"], 1319413953331)
        self.assertTrue(any(c.action == "remap" for c in res.changes))

    def test_bytes_does_not_clobber_existing_total_size(self):
        out, _ = self.normalize(
            {"name": "d", "bytes": 999, "total_size_bytes": 123}
        )
        self.assertEqual(out["total_size_bytes"], 123)

    def test_redundant_format_keys_dropped(self):
        out, res = self.normalize(
            {"name": "d", "format": ["csv"], "encoding": ["csv"]}
        )
        self.assertNotIn("format", out)
        self.assertNotIn("encoding", out)
        self.assertEqual(
            2, sum(1 for c in res.changes if c.action == "drop-redundant")
        )

    def test_compression_holding_formats_is_dropped(self):
        out, res = self.normalize({"name": "d", "compression": ["pdf", "h5ad"]})
        self.assertNotIn("compression", out)
        self.assertTrue(any(c.step == "compression" for c in res.changes))

    def test_valid_compression_value_is_kept(self):
        out, _ = self.normalize({"name": "d", "compression": "gzip"})
        self.assertEqual(out["compression"], "gzip")

    def test_orcid_reference_resolves_and_keeps_identifier(self):
        out, _ = self.normalize(
            {"name": "d", "creators": [{"@id": "https://orcid.org/0000-0003-4060-7360"}]}
        )
        creator = out["creators"][0]
        self.assertEqual(creator["id"], "https://orcid.org/0000-0003-4060-7360")
        self.assertEqual(creator["name"], "Clark, T")
        self.assertEqual(
            creator["affiliations"][0]["name"], "University of Virginia"
        )

    def test_unresolvable_reference_keeps_id_without_inventing_name(self):
        out, _ = self.normalize(
            {"name": "d", "creators": [{"@id": "https://orcid.org/0000-0000-0000-0000"}]}
        )
        creator = out["creators"][0]
        self.assertEqual(creator["id"], "https://orcid.org/0000-0000-0000-0000")
        self.assertNotIn("name", creator)

    def test_created_by_list_flattens_to_string(self):
        out, _ = self.normalize(
            {
                "name": "d",
                "created_by": [
                    "Plain Name",
                    {"@id": "https://orcid.org/0000-0003-4060-7360"},
                ],
            }
        )
        self.assertIsInstance(out["created_by"], str)
        self.assertIn("Plain Name", out["created_by"])
        self.assertIn("Clark, T", out["created_by"])

    def test_org_urn_is_deterministic_and_clearly_local(self):
        first = _org_urn("University of California, San Diego")
        self.assertEqual(first, _org_urn("University of California, San Diego"))
        self.assertTrue(first.startswith("urn:d4d:org:"))
        self.assertNotIn(" ", first)


class TestReduceMetadata(unittest.TestCase):
    def test_large_inventory_collapses_and_reports_count(self):
        graph = {
            "@graph": [
                {
                    "@id": "x",
                    "name": "big",
                    "hasPart": [{"@id": f"ark:59853/dataset-{i}"} for i in range(200)],
                }
            ]
        }
        res = Result(project="TEST")
        out = reduce_metadata(graph, res)
        summary = out["@graph"][0]["hasPart"]
        self.assertEqual(summary["count"], 200)
        self.assertIn("dataset", summary["id_families"])
        self.assertTrue(any(c.action == "collapse" for c in res.changes))

    def test_small_inventory_is_left_alone(self):
        graph = {"@graph": [{"@id": "x", "hasPart": [{"@id": "a"}, {"@id": "b"}]}]}
        res = Result(project="TEST")
        out = reduce_metadata(graph, res)
        self.assertEqual(len(out["@graph"][0]["hasPart"]), 2)

    def test_schema_properties_collapse_but_keep_every_column(self):
        props = {f"col_{i}": {"description": f"Column col_{i}", "type": "number"}
                 for i in range(60)}
        graph = {"@graph": [{"@id": "s", "@type": "EVI:Schema", "name": "Sch",
                             "properties": props, "required": list(props)}]}
        res = Result(project="TEST")
        out = reduce_metadata(graph, res)
        summary = out["@graph"][0]["properties"]
        self.assertEqual(summary["count"], 60)
        self.assertEqual(len(summary["columns"]), 60)
        self.assertIn("col_0:number", summary["columns"])

    def test_real_column_descriptions_are_preserved(self):
        props = {f"col_{i}": {"description": f"Column col_{i}", "type": "number"}
                 for i in range(60)}
        props["special"] = {"description": "Validated PHQ-9 depression score",
                            "type": "integer"}
        graph = {"@graph": [{"@id": "s", "@type": "EVI:Schema",
                             "properties": props}]}
        out = reduce_metadata(graph, Result(project="TEST"))
        summary = out["@graph"][0]["properties"]
        self.assertIn("special", summary["described_columns"])
        self.assertEqual(
            summary["described_columns"]["special"]["description"],
            "Validated PHQ-9 depression score",
        )

    def test_required_collapses_only_when_it_duplicates_property_names(self):
        props = {f"c{i}": {"description": f"Column c{i}", "type": "string"}
                 for i in range(40)}
        dup = {"@graph": [{"@id": "a", "properties": dict(props),
                           "required": list(props)}]}
        out = reduce_metadata(dup, Result(project="TEST"))
        self.assertIsInstance(out["@graph"][0]["required"], dict)

        distinct = {"@graph": [{"@id": "b", "properties": dict(props),
                                "required": ["c0", "c1"]}]}
        out = reduce_metadata(distinct, Result(project="TEST"))
        self.assertEqual(out["@graph"][0]["required"], ["c0", "c1"])

    def test_small_property_map_is_left_alone(self):
        props = {"a": {"description": "Column a", "type": "string"}}
        graph = {"@graph": [{"@id": "s", "properties": props}]}
        out = reduce_metadata(graph, Result(project="TEST"))
        self.assertEqual(out["@graph"][0]["properties"], props)

    def test_source_document_is_not_mutated(self):
        graph = {
            "@graph": [
                {"@id": "x", "hasPart": [{"@id": f"a{i}"} for i in range(50)]}
            ]
        }
        reduce_metadata(graph, Result(project="TEST"))
        self.assertEqual(len(graph["@graph"][0]["hasPart"]), 50)


class TestDeNovoPolicy(unittest.TestCase):
    """The de novo fork must extract from evidence, never copy a D4D record."""

    def test_d4d_shaped_artifacts_are_blocked(self):
        for name in (
            "CM4AI_crate_d4d.yaml",
            "ro-crate-linkml.yaml",
            "ro-crate-datasheet.html",
            "ro-crate-preview.html",
        ):
            with self.subTest(name=name):
                with self.assertRaises(DeNovoPolicyError):
                    assert_de_novo_safe(name)

    def test_evidence_artifacts_are_allowed(self):
        for name in ("CM4AI_crate_metadata_reduced.json", "ai_ready_score.json"):
            with self.subTest(name=name):
                assert_de_novo_safe(name)  # must not raise

    def test_include_and_exclude_lists_are_disjoint(self):
        self.assertFalse(set(DE_NOVO_INCLUDE) & set(DE_NOVO_EXCLUDE))

    def test_every_exclusion_states_a_reason(self):
        for pattern, reason in DE_NOVO_EXCLUDE.items():
            self.assertTrue(reason.strip(), f"{pattern} has no stated reason")


class TestBuildCrateBundle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.packages = root / "packages"
        self.docs = root / "concatenated"
        processed = self.packages / "TESTPROJ" / "processed"
        raw = self.packages / "TESTPROJ" / "raw"
        processed.mkdir(parents=True)
        raw.mkdir(parents=True)
        self.docs.mkdir(parents=True)

        (self.docs / "TESTPROJ_preprocessed.txt").write_text("DOCUMENT CORPUS BODY")
        (processed / "TESTPROJ_crate_metadata_reduced.json").write_text(
            json.dumps({"@graph": [{"name": "EVIDENCE MARKER"}]})
        )
        (raw / "ai_ready_score.json").write_text(json.dumps({"name": "SCORE MARKER"}))
        # Both of these must stay out of the bundle.
        (processed / "TESTPROJ_crate_d4d.yaml").write_text("id: LEAKED_D4D_MARKER\n")
        (raw / "ro-crate-linkml.yaml").write_text("conforms_to: LEAKED_LINKML_MARKER\n")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self):
        return build_crate_bundle("TESTPROJ", self.packages, self.docs)

    def test_bundle_carries_docs_and_evidence(self):
        out, included, _ = self.build()
        text = out.read_text()
        self.assertIn("DOCUMENT CORPUS BODY", text)
        self.assertIn("EVIDENCE MARKER", text)
        self.assertIn("SCORE MARKER", text)
        self.assertEqual(len(included), 2)

    def test_d4d_shaped_content_never_reaches_the_bundle(self):
        out, _, withheld = self.build()
        text = out.read_text()
        self.assertNotIn("LEAKED_D4D_MARKER", text)
        self.assertNotIn("LEAKED_LINKML_MARKER", text)
        self.assertEqual(len(withheld), 2)

    def test_bundle_documents_what_it_withheld(self):
        out, _, _ = self.build()
        text = out.read_text()
        self.assertIn("CRATE ARTIFACTS WITHHELD", text)
        self.assertIn("TESTPROJ_crate_d4d.yaml", text)  # named, not silently dropped

    def test_missing_document_bundle_is_an_error(self):
        (self.docs / "TESTPROJ_preprocessed.txt").unlink()
        with self.assertRaises(FileNotFoundError):
            self.build()


class TestDoiKey(unittest.TestCase):
    """A DOI must compare equal across the forms upstream actually uses."""

    def test_equivalent_forms_reduce_to_one_key(self):
        forms = [
            "https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/XNBOPG",
            "https://doi.org/10.18130/V3/XNBOPG",
            "doi:10.18130/V3/XNBOPG",
            "10.18130/V3/XNBOPG",
            "https://doi.org/10.18130/v3/xnbopg/",
        ]
        self.assertEqual({_doi_key(f) for f in forms}, {"10.18130/v3/xnbopg"})

    def test_distinct_dois_do_not_collide(self):
        self.assertNotEqual(_doi_key("doi:10.18130/V3/XNBOPG"),
                            _doi_key("doi:10.18130/V3/HIGT4C"))

    def test_urls_without_a_doi_yield_none(self):
        for u in ("https://chorus4ai.org/", "https://fairhub.io/datasets/3", ""):
            self.assertIsNone(_doi_key(u))


class TestDocumentCorpusExclusions(unittest.TestCase):
    """The crate corpus may claim a record; the document corpus then skips it.

    Failing open matters more than failing closed here: a wrong exclusion
    silently removes a real input document and shifts a baseline.
    """

    def write(self, projects):
        d = Path(self.tmp.name)
        (d / "crate_manifest.yaml").write_text(
            yaml.safe_dump({"version": 1, "projects": projects}), encoding="utf-8")
        return d

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_exclude_claims_the_doi_in_every_url_form(self):
        d = self.write({"CHORUS": {
            "dataset_url": "https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/XNBOPG",
            "doi": "10.18130/V3/XNBOPG",
            "document_corpus": "exclude",
            "document_corpus_reason": "record exists to publish the crate",
        }})
        ex = document_corpus_exclusions(d)
        for form in ("https://doi.org/10.18130/V3/XNBOPG",
                     "doi:10.18130/V3/XNBOPG",
                     "https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/XNBOPG"):
            match = ex.match(form)
            self.assertIsNotNone(match, form)
            self.assertEqual(match[0], "CHORUS")
            self.assertIn("publish the crate", match[1])

    def test_allow_is_not_excluded_even_though_it_declares_a_doi(self):
        """CM4AI's case: same shape of URL, but a legitimate input document."""
        d = self.write({"CM4AI": {
            "dataset_url": "https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C",
            "doi": "10.18130/V3/HIGT4C",
            "document_corpus": "allow",
        }})
        ex = document_corpus_exclusions(d)
        self.assertIsNone(ex.match(
            "https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C"))
        self.assertEqual(ex.dois, {})

    def test_undecided_does_not_exclude_but_is_reported(self):
        d = self.write({"AI_READI": {"doi": "10.1234/PENDING",
                                     "document_corpus": "undecided"}})
        ex = document_corpus_exclusions(d)
        self.assertIsNone(ex.match("https://doi.org/10.1234/PENDING"))
        self.assertEqual(ex.undecided, ["AI_READI"])

    def test_absent_declaration_does_not_exclude(self):
        d = self.write({"VOICE": {"doi": "10.13026/k81f-qr68"}})
        ex = document_corpus_exclusions(d)
        self.assertIsNone(ex.match("https://doi.org/10.13026/k81f-qr68"))
        self.assertEqual(ex.undecided, [])

    def test_missing_manifest_excludes_nothing(self):
        ex = document_corpus_exclusions(Path(self.tmp.name) / "nope")
        self.assertEqual(ex.dois, {})
        self.assertIsNone(ex.match("https://doi.org/10.18130/V3/XNBOPG"))

    def test_real_manifest_claims_chorus_and_spares_cm4ai(self):
        """Guards the live config, not just the mechanism."""
        ex = document_corpus_exclusions()
        chorus = ex.match(
            "https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/XNBOPG")
        self.assertIsNotNone(chorus, "CHORUS crate DOI must be excluded")
        self.assertEqual(chorus[0], "CHORUS")
        self.assertIsNone(
            ex.match("https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C"),
            "CM4AI release landing page is a legitimate input document")
        for url in ("https://physionet.org/content/b2ai-voice/3.1.0/",
                    "https://fairhub.io/datasets/3",
                    "https://chorus4ai.org/"):
            self.assertIsNone(ex.match(url), url)


if __name__ == "__main__":
    unittest.main()
