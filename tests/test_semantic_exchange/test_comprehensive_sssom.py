"""The comprehensive SSSOM tables cover every schema slot, keep every curated
alignment, and regenerate exactly (#2935).

Until #2935 the keyword heuristics ran before the TTL was consulted, so 29
TTL-aligned slots were labelled free text or novel. The schema's own
``slot_uri`` and ``*_mappings`` were never read, so 95 slots with declared
external targets had none in the table. The table was also stale: 284 rows
against 301 slot names. The only test asked for more than 200 rows.

The expectations here are computed from the inputs by other means than the
generator (raw YAML for the schema, rdflib for the TTL), so a generator that
drops a source fails them rather than agreeing with itself.

Nothing here walks the corpus: the inputs are the schema, the TTL and the
recommendations file.
"""

import csv
import functools
import io
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "src" / "semantic_exchange"
SCHEMA = REPO / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
TTL = REPO / "src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl"
RECS = REPO / "notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv"
COMP = REPO / "src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv"
URI = REPO / "src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_comprehensive.tsv"
D4D = "https://w3id.org/bridge2ai/data-sheets-schema/"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_comprehensive_sssom as gcs  # noqa: E402
import generate_comprehensive_sssom_uri as gcsu  # noqa: E402

#: The 29 TTL-aligned slots the committed table did not label ``mapped``
#: before #2935 (25 novel_d4d, 4 free_text).
FORMERLY_UNMAPPED_TTL_SLOTS = {
    'addressing_gaps', 'annotation_analyses', 'cleaning_strategies',
    'collection_timeframes', 'confidential_elements', 'content_warnings',
    'data_protection_impacts', 'description', 'discouraged_uses', 'errata',
    'ethical_reviews', 'external_resources', 'future_use_impacts',
    'imputation_protocols', 'informed_consent', 'intended_uses',
    'ip_restrictions', 'is_deidentified', 'known_biases', 'known_limitations',
    'labeling_strategies', 'license_and_use_terms',
    'missing_data_documentation', 'participant_compensation',
    'preprocessing_strategies', 'prohibited_uses', 'regulatory_restrictions',
    'retention_limit', 'sampling_strategies',
}

SCHEMA_KINDS = (('slot_uri', 'skos:exactMatch'),
                ('exact_mappings', 'skos:exactMatch'),
                ('close_mappings', 'skos:closeMatch'),
                ('narrow_mappings', 'skos:narrowMatch'),
                ('broad_mappings', 'skos:broadMatch'),
                ('related_mappings', 'skos:relatedMatch'))


def read_table(path_or_text):
    text = (path_or_text.read_text(encoding="utf-8")
            if isinstance(path_or_text, Path) else path_or_text)
    body = "".join(line for line in text.splitlines(keepends=True)
                   if not line.startswith("#"))
    return list(csv.DictReader(io.StringIO(body), delimiter="\t"))


def pairs_in(row):
    """(predicate, object) the row asserts: its primary and every other one."""
    out = {(row["predicate_id"], row["object_id"])}
    for entry in filter(None, row["other_curated_mappings"].split(" | ")):
        predicate, obj = entry.split(" ", 2)[:2]
        out.add((predicate, obj))
    return out


@functools.lru_cache(maxsize=None)
def raw_schema():
    """The merged schema as plain YAML: one parse for the whole module."""
    from data_sheets_schema.schema_cache import load_yaml
    return load_yaml(SCHEMA)


def raw_slot_names(schema):
    names = set(schema.get("slots") or {})
    for cdef in (schema.get("classes") or {}).values():
        names |= set((cdef or {}).get("attributes") or {})
    return names


def raw_external_declarations(schema):
    """{slot: {(predicate, object)}} for every non-D4D declaration."""
    prefixes = {p: (v if isinstance(v, str) else v["prefix_reference"])
                for p, v in (schema.get("prefixes") or {}).items()}

    def external(curie):
        return not prefixes.get(curie.split(":", 1)[0], "").startswith(D4D)

    found = {}

    def add(slot, definition):
        for metaslot, predicate in SCHEMA_KINDS:
            value = (definition or {}).get(metaslot)
            for v in ([value] if isinstance(value, str) else value or []):
                if external(v):
                    found.setdefault(slot, set()).add((predicate, v))

    for slot, sdef in (schema.get("slots") or {}).items():
        add(slot, sdef)
    for cdef in (schema.get("classes") or {}).values():
        for group in ("attributes", "slot_usage"):
            for slot, sdef in ((cdef or {}).get(group) or {}).items():
                add(slot, sdef)
    return found


def ttl_slot_alignments(slot_names):
    """{slot: [(predicate, object)]} for slot-level SKOS triples, by rdflib."""
    import rdflib
    g = rdflib.Graph()
    g.parse(TTL, format="turtle")
    namespaces = sorted(((p, str(ns)) for p, ns in g.namespaces()),
                        key=lambda x: -len(x[1]))
    skos = "http://www.w3.org/2004/02/skos/core#"

    def curie(iri):
        for prefix, ns in namespaces:
            if iri.startswith(ns):
                return f"{prefix}:{iri[len(ns):]}"
        return iri

    found = {}
    for s, p, o in g:
        s, p, o = str(s), str(p), str(o)
        if not (p.startswith(skos) and p.endswith("Match") and s.startswith(D4D)):
            continue
        slot = s[len(D4D):]
        if slot in slot_names:
            found.setdefault(slot, []).append(
                ("skos:" + p[len(skos):], curie(o)))
    return found


class _Committed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.comp = {r["subject_id"][len("d4d:"):]: r for r in read_table(COMP)}
        cls.uri = {r["d4d_slot_name"]: r for r in read_table(URI)}
        cls.schema = raw_schema()
        cls.names = raw_slot_names(cls.schema)


class TestEverySlotHasOneRow(_Committed):

    def test_comprehensive_subjects_are_exactly_the_schema_slots(self):
        rows = read_table(COMP)
        subjects = [r["subject_id"] for r in rows]
        self.assertEqual(len(subjects), len(set(subjects)), "duplicate subject_id")
        have = {s[len("d4d:"):] for s in subjects}
        self.assertEqual(sorted(self.names - have), [],
                         "schema slots with no row in the comprehensive table")
        self.assertEqual(sorted(have - self.names), [],
                         "rows that name no schema slot")

    def test_uri_table_rows_are_exactly_the_schema_slots(self):
        self.assertEqual(set(self.uri), self.names)

    def test_every_row_is_one_physical_line(self):
        """A description's line breaks once made 32 continuation lines, which
        a line-oriented reader (grep, awk, a '#' filter) splits mid-row."""
        for path in (COMP, URI):
            with self.subTest(table=path.name):
                text = path.read_text(encoding="utf-8")
                lines = [line for line in text.splitlines()
                         if not line.startswith("#")]
                self.assertEqual(len(lines) - 1, len(read_table(text)))

    def test_both_tables_resolve_every_slot_the_same_way(self):
        for slot, row in self.comp.items():
            with self.subTest(slot=slot):
                u = self.uri[slot]
                self.assertEqual(
                    (row["mapping_status"], row["predicate_id"], row["object_id"],
                     row["mapping_source"], row["other_curated_mappings"]),
                    (u["mapping_status"], u["predicate_id"], u["object_id"],
                     u["mapping_source"], u["other_curated_mappings"]))


class TestTTLAlignmentsAreMapped(_Committed):
    """Every slot-level SKOS triple, read by rdflib rather than the regex."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ttl = ttl_slot_alignments(cls.names)

    def test_the_ttl_has_slot_level_alignments(self):
        self.assertGreater(len(self.ttl), 90)

    def test_every_slot_level_alignment_is_the_mapped_row(self):
        for slot, pairs in sorted(self.ttl.items()):
            with self.subTest(slot=slot):
                row = self.comp[slot]
                self.assertEqual(row["mapping_status"], "mapped")
                self.assertEqual(row["mapping_source"], "ttl")
                self.assertEqual(row["mapping_justification"],
                                 "semapv:ManualMappingCuration")
                primary = (row["predicate_id"], row["object_id"])
                self.assertIn(primary, pairs)
                if len(pairs) == 1:
                    self.assertEqual(primary, pairs[0])
                self.assertLessEqual(set(pairs), pairs_in(row))

    def test_the_29_the_heuristics_used_to_hide(self):
        self.assertLessEqual(FORMERLY_UNMAPPED_TTL_SLOTS, set(self.ttl))
        for slot in sorted(FORMERLY_UNMAPPED_TTL_SLOTS):
            with self.subTest(slot=slot):
                self.assertEqual(self.comp[slot]["mapping_status"], "mapped")

    def test_named_examples(self):
        for slot, pair in {
            "ethical_reviews": ("skos:exactMatch", "rai:ethicalReview"),
            "description": ("skos:exactMatch", "schema:description"),
            "missing_data_documentation":
                ("skos:exactMatch", "rai:dataCollectionMissingData"),
            "data_protection_impacts": ("skos:exactMatch", "rai:dataSocialImpact"),
            "ip_restrictions": ("skos:closeMatch", "schema:conditionsOfAccess"),
        }.items():
            with self.subTest(slot=slot):
                row = self.comp[slot]
                self.assertEqual((row["predicate_id"], row["object_id"]), pair)

    def test_a_class_scoped_alignment_maps_a_slot_with_no_slot_level_one(self):
        """``d4d:FileCollection_total_bytes`` is the TTL's word on total_bytes
        (#294), and the schema's exact_mappings agree with it."""
        self.assertNotIn("total_bytes", self.ttl)
        row = self.comp["total_bytes"]
        self.assertEqual((row["mapping_status"], row["predicate_id"],
                          row["object_id"], row["d4d_schema_path"]),
                         ("mapped", "skos:exactMatch", "dcat:byteSize",
                          "FileCollection.total_bytes"))
        self.assertIn("d4d:FileCollection_total_bytes", row["comment"])
        self.assertNotIn("disagree", row["comment"])


class TestSchemaDeclaredMappingsAreKept(_Committed):
    """Every non-D4D slot_uri or *_mappings value, read from the raw YAML."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.declared = raw_external_declarations(cls.schema)

    def test_the_schema_declares_external_targets(self):
        self.assertGreater(len(self.declared), 100)

    def test_every_declared_target_is_in_its_slots_mapped_row(self):
        for slot, pairs in sorted(self.declared.items()):
            with self.subTest(slot=slot):
                row = self.comp[slot]
                self.assertEqual(row["mapping_status"], "mapped")
                self.assertEqual(sorted(pairs - pairs_in(row)), [])

    def test_a_slot_the_ttl_does_not_align_takes_the_schemas_target(self):
        for slot, pair in {
            "data_use_permission": ("skos:exactMatch", "DUO:0000001"),
            "committee_contact": ("skos:broadMatch", "schema:contactPoint"),
            "unit": ("skos:exactMatch", "qudt:unit"),
            "access_urls": ("skos:exactMatch", "dcat:accessURL"),
            "checksum": ("skos:exactMatch", "spdx:checksum"),
        }.items():
            with self.subTest(slot=slot):
                row = self.comp[slot]
                self.assertEqual(row["mapping_source"], "schema")
                self.assertEqual((row["predicate_id"], row["object_id"]), pair)

    def test_same_as_has_a_row_although_no_class_uses_it(self):
        row = self.comp["same_as"]
        self.assertEqual((row["mapping_status"], row["object_id"]),
                         ("mapped", "schema:sameAs"))
        self.assertEqual(row["d4d_schema_path"], "")
        self.assertIn("no class uses this slot", row["comment"])

    def test_where_the_ttl_wins_the_schemas_targets_stay_visible(self):
        row = self.comp["regulatory_restrictions"]
        self.assertEqual((row["predicate_id"], row["object_id"]),
                         ("skos:closeMatch", "schema:conditionsOfAccess"))
        for pair in (("skos:exactMatch", "dcterms:accessRights"),
                     ("skos:broadMatch", "DUO:0000021"),
                     ("skos:broadMatch", "DUO:0000022"),
                     ("skos:broadMatch", "DUO:0000028")):
            self.assertIn(pair, pairs_in(row))


class TestHeuristicsNeverOverrideCuration(_Committed):

    def test_a_curated_row_is_mapped_whatever_the_hint(self):
        hinted = [r for r in self.comp.values()
                  if r["mapping_source"] in ("ttl", "schema") and r["heuristic_hint"]]
        self.assertTrue(hinted, "no curated slot trips a keyword; test is vacuous")
        for row in hinted:
            with self.subTest(slot=row["subject_id"]):
                self.assertEqual(row["mapping_status"], "mapped")

    def test_the_hint_decides_status_only_without_a_curated_source(self):
        for row in self.comp.values():
            with self.subTest(slot=row["subject_id"]):
                if row["mapping_status"] in ("free_text", "novel_d4d"):
                    self.assertEqual(row["mapping_source"], "heuristic")
                    self.assertEqual(row["mapping_status"], row["heuristic_hint"])
                if row["mapping_source"] == "heuristic":
                    self.assertIn(row["mapping_status"], ("free_text", "novel_d4d"))


class TestSchemaPathNamesACarrier(_Committed):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from data_sheets_schema.schema_view import shared_view
        cls.sv = shared_view(SCHEMA)

    def test_path_class_carries_the_slot(self):
        classes = set(self.sv.all_classes())
        for slot, row in self.comp.items():
            with self.subTest(slot=slot):
                path = row["d4d_schema_path"]
                if not path:
                    self.assertFalse(
                        [c for c in classes if slot in self.sv.class_slots(c)],
                        "empty path for a slot some class carries")
                    continue
                cls, name = path.split(".", 1)
                self.assertEqual(name, slot)
                self.assertIn(cls, classes)
                self.assertIn(slot, self.sv.class_slots(cls))

    def test_owning_classes_carry_the_slot(self):
        for slot, row in self.comp.items():
            for cls in filter(None, row["d4d_owning_classes"].split("|")):
                with self.subTest(slot=slot, cls=cls):
                    self.assertIn(slot, self.sv.class_slots(cls))

    def test_a_schema_declaration_names_its_classes_not_their_subclasses(self):
        """The merged schema repeats ``id``'s slot_uri on 78 classes; the row
        names the four that declare it without inheriting it."""
        for slot, row in self.comp.items():
            for entry in filter(None, row["other_curated_mappings"].split(" | ")):
                places = entry[entry.index("(") + 1:-1]
                for part in places.split("; "):
                    if not part.startswith("schema "):
                        continue
                    listed = set(part[len("schema "):].split(", "))
                    for cls in listed:
                        with self.subTest(slot=slot, cls=cls):
                            self.assertFalse(
                                listed & set(self.sv.class_ancestors(cls)[1:]))
        others = self.comp["id"]["other_curated_mappings"]
        self.assertIn("skos:exactMatch schema:identifier (schema ", others)
        self.assertIn("NamedThing", others)
        self.assertNotIn("AddressingGap", others)

    def test_a_nested_slot_is_not_written_as_a_dataset_slot(self):
        """190 of 284 rows named ``Dataset.<slot>`` for slots Dataset lacks."""
        row = self.comp["committee_name"]
        self.assertNotIn("committee_name", self.sv.class_slots("Dataset"))
        self.assertFalse(row["d4d_schema_path"].startswith("Dataset."))


class TestDisagreementsAreListed(unittest.TestCase):
    """A TTL/schema disagreement the lists do not name is new and must be
    looked at; a listed one that no longer occurs is stale."""

    @classmethod
    def setUpClass(cls):
        cls.gen = gcs.ComprehensiveSSSOMGenerator(SCHEMA, TTL, RECS)

    def test_no_unlisted_and_no_stale_disagreement(self):
        report = self.gen.disagreement_report()
        self.assertEqual(report["unlisted"], [])
        self.assertEqual(report["stale"], [])

    def test_the_lists_are_disjoint_and_give_reasons(self):
        self.assertFalse(set(gcs.ACCEPTED_DISAGREEMENTS) & set(gcs.OPEN_DISAGREEMENTS))
        for slot, reason in {**gcs.ACCEPTED_DISAGREEMENTS,
                             **gcs.OPEN_DISAGREEMENTS}.items():
            with self.subTest(slot=slot):
                self.assertGreater(len(reason.strip()), 20)

    def test_open_disagreements_warn_on_every_run(self):
        warnings = "\n".join(self.gen.warnings())
        for slot in gcs.OPEN_DISAGREEMENTS:
            self.assertIn(f"disagreement on {slot}:", warnings)

    def test_a_stale_listing_warns(self):
        with mock.patch.dict(gcs.ACCEPTED_DISAGREEMENTS, {"doi": "not a disagreement"}):
            report = self.gen.disagreement_report()
            self.assertIn("doi", report["stale"])
            self.assertTrue(any("doi is listed" in w for w in self.gen.warnings()))


class TestCommittedTablesRegenerate(unittest.TestCase):
    """Drift: regenerated in memory under the date the file records, the
    table must be byte-for-byte the committed one. A schema-release PR that
    moves a slot must regenerate both tables."""

    @classmethod
    def setUpClass(cls):
        cls.uri_gen = gcsu.ComprehensiveURISSSOMGenerator(SCHEMA, TTL, RECS)
        cls.comp_gen = cls.uri_gen.comp_gen

    def _assert_regenerates(self, committed, text, key):
        current = committed.read_text(encoding="utf-8")
        if current != text:
            have = {r[key]: r for r in read_table(current)}
            made = {r[key]: r for r in read_table(text)}
            differ = sorted(k for k in set(have) | set(made)
                            if have.get(k) != made.get(k))
            self.fail(f"{committed.name} does not regenerate "
                      f"({len(differ)} rows differ: {differ[:10]}); run "
                      "make gen-sssom-comprehensive gen-sssom-uri-comprehensive")

    def test_comprehensive_table(self):
        self._assert_regenerates(
            COMP, self.comp_gen.render_sssom(gcs.committed_date(COMP)),
            "subject_id")

    def test_uri_table(self):
        self._assert_regenerates(
            URI, self.uri_gen.render_sssom(gcs.committed_date(URI)),
            "d4d_slot_name")

    def test_the_date_is_the_only_thing_the_day_changes(self):
        a = self.comp_gen.render_sssom("2001-01-01")
        b = self.comp_gen.render_sssom("2001-01-01")
        c = self.comp_gen.render_sssom("2002-02-02")
        self.assertEqual(a, b)
        self.assertEqual(a.replace("2001-01-01", "2002-02-02"), c)

    def _main(self, module, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = module.main(["--schema", str(SCHEMA), "--skos", str(TTL),
                                "--recommendations", str(RECS)] + argv)
        return code, out.getvalue()

    def test_check_passes_on_the_committed_tables_and_writes_nothing(self):
        for module, path in ((gcs, COMP), (gcsu, URI)):
            with self.subTest(table=path.name):
                before = path.read_bytes()
                code, out = self._main(module, ["--check", "--output", str(path)])
                self.assertEqual(code, 0, out)
                self.assertEqual(path.read_bytes(), before)

    @staticmethod
    def _without_first_row(text):
        """The table with its first data row removed, written the same way."""
        comments = "".join(line for line in text.splitlines(keepends=True)
                           if line.startswith("#"))
        body = "".join(line for line in text.splitlines(keepends=True)
                       if not line.startswith("#"))
        reader = csv.DictReader(io.StringIO(body), delimiter="\t")
        rows = list(reader)[1:]
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=reader.fieldnames,
                                delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return comments + out.getvalue()

    def test_check_fails_on_a_stale_table_and_leaves_it_alone(self):
        for module, path in ((gcs, COMP), (gcsu, URI)):
            with self.subTest(table=path.name), tempfile.TemporaryDirectory() as d:
                stale = Path(d) / path.name
                stale.write_text(
                    self._without_first_row(path.read_text(encoding="utf-8")),
                    encoding="utf-8")
                before = stale.read_bytes()
                code, out = self._main(module, ["--check", "--output", str(stale)])
                self.assertEqual(code, 1)
                self.assertIn("rows only in the regeneration", out)
                self.assertEqual(stale.read_bytes(), before)

    def test_date_flag_pins_the_written_table(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "t.tsv"
            code, _ = self._main(gcs, ["--date", "2003-03-03", "--output", str(out)])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("# Date: 2003-03-03\n", text)
            self.assertEqual({r["mapping_date"] for r in read_table(text)},
                             {"2003-03-03"})


FIXTURE_SCHEMA = """\
id: https://example.org/fixture
name: fixture
prefixes:
  linkml: https://w3id.org/linkml/
  d4d: https://w3id.org/bridge2ai/data-sheets-schema/
  schema: http://schema.org/
  dcterms: http://purl.org/dc/terms/
  rai: http://mlcommons.org/croissant/RAI/
default_prefix: d4d
default_range: string
imports:
  - linkml:types
classes:
  Dataset:
    attributes:
      ethical_notes:
        description: Free-text notes on the ethical review.
      governance_details:
        description: Narrative details of governance.
        slot_uri: dcterms:accessRights
      prohibited_things:
        description: Things that are prohibited.
      retention_impacts:
        description: Impacts of retention.
      plain:
        description: Nothing a keyword matches.
      empty_recommendation:
        description: A recommendation without a URI.
      both_named:
        description: Aligned by the TTL and declared by the schema.
        slot_uri: dcterms:title
      own_uri:
        description: Declares only a D4D slot_uri.
        slot_uri: d4d:ownUri
"""

FIXTURE_TTL = """\
@prefix d4d: <https://w3id.org/bridge2ai/data-sheets-schema/> .
@prefix schema: <https://schema.org/> .
@prefix rai: <http://mlcommons.org/croissant/RAI/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

d4d:ethical_notes skos:exactMatch rai:ethicalReview .
d4d:both_named skos:exactMatch schema:name .
"""

FIXTURE_RECS = (
    "attribute\tdescription\trange\tused_in_classes\tsuggested_uri\tconfidence\n"
    "prohibited_things\t\tstring\tDataset\tschema:usageInfo\thigh\n"
    "empty_recommendation\t\tstring\tDataset\t\tlow\n"
    "ethical_notes\t\tstring\tDataset\tschema:comment\thigh\n"
)


class TestPrecedenceOnAFixture(unittest.TestCase):
    """Each rung of the precedence, on slots whose names and descriptions trip
    the keyword heuristics, so a heuristic that runs first shows up."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        d = Path(cls._tmp.name)
        (d / "schema.yaml").write_text(textwrap.dedent(FIXTURE_SCHEMA))
        (d / "align.ttl").write_text(FIXTURE_TTL)
        (d / "recs.tsv").write_text(FIXTURE_RECS)
        cls.gen = gcs.ComprehensiveSSSOMGenerator(
            d / "schema.yaml", d / "align.ttl", d / "recs.tsv")
        cls.res = cls.gen.resolutions

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_ttl_outranks_every_keyword_and_the_recommendation(self):
        r = self.res["ethical_notes"]
        self.assertEqual(r.hint, "free_text")
        self.assertEqual((r.status, r.source, r.predicate, r.object),
                         ("mapped", "ttl", "skos:exactMatch", "rai:ethicalReview"))

    def test_the_schema_outranks_the_keywords(self):
        r = self.res["governance_details"]
        self.assertEqual(r.hint, "free_text")
        self.assertEqual((r.status, r.source, r.predicate, r.object),
                         ("mapped", "schema", "skos:exactMatch", "dcterms:accessRights"))

    def test_a_recommendation_outranks_the_keywords(self):
        r = self.res["prohibited_things"]
        self.assertEqual(r.hint, "novel_d4d")
        self.assertEqual((r.status, r.object), ("recommended", "schema:usageInfo"))

    def test_an_empty_recommendation_is_silent(self):
        self.assertEqual(self.res["empty_recommendation"].status, "unmapped")

    def test_the_keywords_decide_only_what_nothing_curated_covers(self):
        self.assertEqual(self.res["retention_impacts"].status, "novel_d4d")
        self.assertEqual(self.res["plain"].status, "unmapped")

    def test_a_d4d_slot_uri_is_not_an_alignment(self):
        r = self.res["own_uri"]
        self.assertEqual(r.status, "unmapped")
        self.assertEqual(self.gen.declared_slot_uri("own_uri"), "d4d:ownUri")

    def test_an_unlisted_disagreement_warns_and_the_ttl_still_wins(self):
        r = self.res["both_named"]
        self.assertEqual((r.object, r.disagreement), ("schema:name", "unlisted"))
        self.assertIn("skos:exactMatch dcterms:title (schema Dataset)", r.others)
        self.assertTrue(any("disagree on both_named" in w
                            for w in self.gen.warnings()))


if __name__ == "__main__":
    unittest.main()
