"""The comprehensive SSSOM tables cover every schema slot, keep every curated
alignment, and regenerate exactly (#2935).

Until #2935 the keyword heuristics ran before the TTL was consulted, so 29
TTL-aligned slots were labelled free text or novel. The schema's own
``slot_uri`` and ``*_mappings`` were never read: of the 136 slots that declare
an external target there, 101 had no row or no ``mapped`` row in the table
(#3202 corrected an earlier count of 95). The table was also stale: 284 rows
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
import os
import re
import shutil
import subprocess
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
#: before #2935 (25 novel_d4d, 4 free_text). Four of them had a TTL target
#: in the D4D namespace only (FORMERLY_UNMAPPED_D4D_TARGET_SLOTS), which is
#: not an alignment (#3054), and #4052 removed those triples with the other
#: twins of #3942's d4d: class removals; of the other 25, 20 are mapped now
#: and 5 lost their TTL alignment (FORMERLY_UNMAPPED_WITHDRAWN_SLOTS).
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
FORMERLY_UNMAPPED_D4D_TARGET_SLOTS = {
    'addressing_gaps', 'content_warnings', 'informed_consent',
    'participant_compensation',
}
#: The five of those 25 whose only TTL triple #3971 and #3974 removed with
#: the slot-level twins of #3942's class corrections: each named a term its
#: vocabulary does not define (rai:prohibitedUses, rai:ethicalReview,
#: rai:confidentialityLevel, evi:samplingPlan). Nothing else curated speaks
#: for them, so the keyword hint decides their status again.
FORMERLY_UNMAPPED_WITHDRAWN_SLOTS = {
    'discouraged_uses', 'ethical_reviews', 'is_deidentified',
    'prohibited_uses', 'sampling_strategies',
}

#: Every slot-level triple #3971, #3974 and #4052 removed, with its old
#: target: the five above; extension_mechanism (closeMatch schema:license; a
#: way to contribute to a dataset is not its license); and the seven twins of
#: the classes #3942 found aligned to d4d: terms. A D4D target is not an
#: alignment (#3054), but each of the seven was its row's mapping (mapped,
#: source ttl) from #2935 (58ba281ca) until #3054 (9201af3d4), two commits
#: of the branch #2963 merged; anomalies, at_risk_populations and
#: human_subject_research had been mapped to theirs since #137 (84637af7c)
#: added the table (#147, 7ae9832ba, only moved it). From #3054 the rows
#: only listed the target, in
#: other_curated_mappings, until #4052 removed the triples.
SLOT_TRIPLES_REMOVED = {
    'discouraged_uses': 'rai:prohibitedUses',
    'prohibited_uses': 'rai:prohibitedUses',
    'ethical_reviews': 'rai:ethicalReview',
    'is_deidentified': 'rai:confidentialityLevel',
    'extension_mechanism': 'schema:license',
    'sampling_strategies': 'evi:samplingPlan',
    'addressing_gaps': 'd4d:addressingGaps',
    'anomalies': 'd4d:dataAnomalies',
    'content_warnings': 'd4d:contentWarning',
    'informed_consent': 'd4d:informedConsent',
    'human_subject_research': 'd4d:humanSubject',
    'at_risk_populations': 'd4d:atRiskPopulations',
    'participant_compensation': 'd4d:participantCompensation',
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


@functools.lru_cache(maxsize=None)
def ttl_match_triples(ttl=TTL):
    """(D4D local name, predicate, object CURIE, whether the object is in the
    D4D namespace) for every SKOS match triple on a D4D subject, by rdflib
    rather than the generator's regex."""
    import rdflib
    g = rdflib.Graph()
    g.parse(ttl, format="turtle")
    namespaces = sorted(((p, str(ns)) for p, ns in g.namespaces()),
                        key=lambda x: -len(x[1]))
    skos = "http://www.w3.org/2004/02/skos/core#"

    def curie(iri):
        for prefix, ns in namespaces:
            if iri.startswith(ns):
                return f"{prefix}:{iri[len(ns):]}"
        return iri

    found = []
    for s, p, o in g:
        s, p, o = str(s), str(p), str(o)
        if p.startswith(skos) and p.endswith("Match") and s.startswith(D4D):
            found.append((s[len(D4D):], "skos:" + p[len(skos):], curie(o),
                          o.startswith(D4D)))
    return tuple(found)


def ttl_slot_alignments(slot_names, internal=False):
    """{slot: [(predicate, object)]} for slot-level SKOS triples, by rdflib:
    those whose target is outside the D4D namespace, or with ``internal``
    those whose target is in it."""
    found = {}
    for subject, predicate, obj, in_d4d in ttl_match_triples():
        if subject in slot_names and in_d4d == internal:
            found.setdefault(subject, []).append((predicate, obj))
    return found


def ttl_subject_slot(schema, names, subject):
    """The slot a TTL subject speaks for: itself when it is a slot name, else
    ``<slot>`` of a ``<Class>_<slot>`` subject whose class carries the slot
    (the raw YAML). None when it is neither."""
    if subject in names:
        return subject
    classes = set(schema.get("classes") or {})
    for i, ch in enumerate(subject):
        cls, slot = subject[:i], subject[i + 1:]
        if (ch == "_" and cls in classes and slot in names
                and slot in raw_carried(schema, cls)):
            return slot
    return None


def ttl_all_alignments(schema, names, ttl=TTL, internal=False):
    """{slot: {(predicate, object)}} for every TTL triple on the slot,
    slot-level and ``<Class>_<slot>`` alike (#3053): targets outside the D4D
    namespace, or with ``internal`` those inside it (#3054)."""
    found = {}
    for subject, predicate, obj, in_d4d in ttl_match_triples(ttl):
        slot = ttl_subject_slot(schema, names, subject)
        if slot is not None and in_d4d == internal:
            found.setdefault(slot, set()).add((predicate, obj))
    return found


def raw_ancestors(schema, cls):
    """Every proper is_a / mixin ancestor of ``cls``, from the raw YAML."""
    classes = schema.get("classes") or {}
    seen, todo = set(), [cls]
    while todo:
        cdef = classes.get(todo.pop()) or {}
        for parent in [cdef.get("is_a")] + list(cdef.get("mixins") or []):
            if parent and parent not in seen:
                seen.add(parent)
                todo.append(parent)
    return seen


def raw_declarers(schema):
    """{slot: {class}} for classes that declare the slot themselves: in their
    ``attributes`` or their ``slots:`` list, from the raw YAML."""
    found = {}
    for cls, cdef in (schema.get("classes") or {}).items():
        cdef = cdef or {}
        for slot in set(cdef.get("attributes") or {}) | set(cdef.get("slots") or []):
            found.setdefault(slot, set()).add(cls)
    return found


def raw_carried(schema, cls):
    """Slots ``cls`` carries: its own declarations and its ancestors'."""
    classes = schema.get("classes") or {}
    carried = set()
    for c in {cls} | raw_ancestors(schema, cls):
        cdef = classes.get(c) or {}
        carried |= set(cdef.get("attributes") or {}) | set(cdef.get("slots") or [])
    return carried


def raw_slot_uris(schema):
    """{slot: {slot_uri}} from every declaration: top-level ``slots:``, class
    ``attributes`` and ``slot_usage``, from the raw YAML."""
    found = {}

    def add(slot, sdef):
        uri = (sdef or {}).get("slot_uri")
        if uri:
            found.setdefault(slot, set()).add(uri)

    for slot, sdef in (schema.get("slots") or {}).items():
        add(slot, sdef)
    for cdef in (schema.get("classes") or {}).values():
        for group in ("attributes", "slot_usage"):
            for slot, sdef in ((cdef or {}).get(group) or {}).items():
                add(slot, sdef)
    return found


def curated_sources(schema, names):
    """{slot: 'ttl' | 'schema'}: the curated source that speaks first for each
    slot, computed from the inputs and never from the table.

    The TTL speaks for a slot through a slot-level subject, or a
    ``<Class>_<slot>`` subject for a class that carries the slot (rdflib, and
    the raw YAML for what a class carries), with a target outside the D4D
    namespace (#3054); else the schema speaks when it declares an external
    target (raw YAML).
    """
    out = {slot: "schema" for slot in raw_external_declarations(schema)}
    out.update({slot: "ttl" for slot in ttl_all_alignments(schema, names)})
    return out


def raw_declaration_places(schema):
    """{slot: {(metaslot, target): {place}}} for every declaration in the raw
    YAML, D4D targets included. A place is a class that declares the slot in
    its ``attributes`` or ``slot_usage``, or '' for the top-level slot."""
    found = {}

    def add(slot, place, sdef):
        for metaslot, _ in SCHEMA_KINDS:
            value = (sdef or {}).get(metaslot)
            for v in ([value] if isinstance(value, str) else value or []):
                found.setdefault(slot, {}).setdefault((metaslot, v), set()).add(place)

    for slot, sdef in (schema.get("slots") or {}).items():
        add(slot, "", sdef)
    for cls, cdef in (schema.get("classes") or {}).items():
        for group in ("attributes", "slot_usage"):
            for slot, sdef in ((cdef or {}).get(group) or {}).items():
                add(slot, cls, sdef)
    return found


def raw_path_class(schema, slot):
    """The row's path class by the rule, from the raw YAML: ``Dataset`` when
    it carries the slot, else the first owner by name, else ''."""
    if slot in raw_carried(schema, "Dataset"):
        return "Dataset"
    declared = raw_declarers(schema).get(slot, set())
    owners = sorted(c for c in declared
                    if not declared & raw_ancestors(schema, c))
    return owners[0] if owners else ""


def raw_hides_top_level(schema, cls, slot):
    """Whether ``cls`` or an ancestor declares ``slot`` as its own attribute,
    which replaces the top-level slot for the class (#3193).

    This is LinkML's rule: ``SchemaView.induced_slot`` takes the attribute of
    the class or of any ancestor whenever one exists, and never consults
    ``slots:``. A class that lists the name under ``slots:`` as well as under
    ``attributes`` still hides the top-level slot (#3392); six classes in the
    merged schema do so."""
    classes = schema.get("classes") or {}
    near = {cls} | raw_ancestors(schema, cls) if cls else set()
    return any(slot in ((classes.get(c) or {}).get("attributes") or {})
               for c in near)


def raw_seen_by(schema, cls, slot):
    """The places whose declarations a row with path class ``cls`` sees: the
    class, its ancestors, and the top-level slot ('') unless one of them
    redeclares the name as its own attribute (#3193)."""
    near = {cls} | raw_ancestors(schema, cls) if cls else set()
    return near | (set() if raw_hides_top_level(schema, cls, slot) else {""})


def declaration_name(place, slot):
    """How a reason names a declaration: ``<Class>.<slot>``, or the top-level
    slot for place ''."""
    return f"{place}.{slot}" if place else f"top-level {slot} slot"


#: A schema declaration a listing's reason cites: a metaslot, then its target
#: ("slot_uri dcat:keyword", "the schema's slot_uri is schema:creator",
#: "exact_mappings says schema:url").
REASON_CITES = re.compile(
    r"\b(" + "|".join(m for m, _ in SCHEMA_KINDS) + r")\s+(?:is\s+|says\s+)?"
    r"([A-Za-z][\w.-]*:[\w.-]*\w)")


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
        """The table committed before #2935 had 34 continuation lines, from
        34 rows whose description held a line break; a line-oriented reader
        (grep, awk, a '#' filter) splits such a row mid-row."""
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
        """81 slot-level subjects, each with an external target, and none
        with a D4D target: a D4D target is not an alignment (#3054), and
        #4052 removed the 7 slot-level triples that named one. (94 subjects,
        87 external, until #3971 and #3974 removed six slot-level triples;
        88 and 81 until #4052 removed seven more; SLOT_TRIPLES_REMOVED.)"""
        self.assertGreater(len(self.ttl), 75)
        self.assertEqual(ttl_slot_alignments(self.names, internal=True), {})

    def test_every_slot_level_alignment_is_the_mapped_row(self):
        """Every slot-level triple whose target is outside the D4D
        namespace; a D4D target is not an alignment (#3054, below)."""
        for slot, pairs in sorted(self.ttl.items()):
            with self.subTest(slot=slot):
                row = self.comp[slot]
                self.assertEqual(
                    (row["mapping_status"], row["mapping_source"]),
                    ("mapped", "ttl"),
                    f"the TTL aligns {slot}; {gcs.REGENERATE_HINT}")
                self.assertEqual(row["mapping_justification"],
                                 "semapv:ManualMappingCuration")
                primary = (row["predicate_id"], row["object_id"])
                self.assertIn(primary, pairs)
                if len(pairs) == 1:
                    self.assertEqual(primary, pairs[0])
                self.assertLessEqual(set(pairs), pairs_in(row))

    def test_the_29_the_heuristics_used_to_hide(self):
        """25 were aligned to an external term: 20 still are and are mapped,
        and the 5 whose term no vocabulary defines are aligned no longer
        (#3971, #3974) and not mapped. The other 4 named only a D4D term:
        from #2935 (58ba281ca) it was the row's mapping, until #3054
        (9201af3d4) made it listed and not mapped; #4052 removed those
        triples too, so they name no term now and are still not mapped."""
        external = FORMERLY_UNMAPPED_TTL_SLOTS - FORMERLY_UNMAPPED_D4D_TARGET_SLOTS
        self.assertEqual(len(external), 25)
        self.assertLessEqual(FORMERLY_UNMAPPED_WITHDRAWN_SLOTS, external)
        aligned = external - FORMERLY_UNMAPPED_WITHDRAWN_SLOTS
        self.assertEqual(len(aligned), 20)
        self.assertLessEqual(aligned, set(self.ttl))
        internal = ttl_slot_alignments(self.names, internal=True)
        withdrawn = (FORMERLY_UNMAPPED_WITHDRAWN_SLOTS
                     | FORMERLY_UNMAPPED_D4D_TARGET_SLOTS)
        self.assertLessEqual(withdrawn, set(SLOT_TRIPLES_REMOVED))
        self.assertFalse(withdrawn & (set(self.ttl) | set(internal)))
        for slot in sorted(aligned):
            with self.subTest(slot=slot):
                self.assertEqual(self.comp[slot]["mapping_status"], "mapped")
        for slot in sorted(withdrawn):
            with self.subTest(slot=slot):
                self.assertNotEqual(self.comp[slot]["mapping_status"], "mapped")

    def test_a_d4d_target_is_listed_and_never_the_mapped_row(self):
        """#3054: the schema rung drops a D4D target because it names the
        slot itself or another D4D term, not an external vocabulary; the TTL
        rung does the same. Every TTL triple with a D4D target (slot-level
        or class-scoped, by rdflib) stays in the row, and a slot with no
        external curated target is not ``mapped`` whichever input names the
        D4D term. Before #3054, 10 rows were ``mapped`` to a D4D term, 7 of
        them to the slot's own slot_uri. #4052 removed the 7 slot-level
        triples among those 10 (SLOT_TRIPLES_REMOVED); the 3 class-scoped
        ones are left (File_file_type, FileCollection_collection_type,
        FileCollection_file_count), each naming its slot's own slot_uri. A
        change that removes them too leaves this test nothing to read on the
        committed tables, and the fixture test of the same rule
        (TestPrecedenceOnAFixture) is then what checks it."""
        internal = ttl_all_alignments(self.schema, self.names, internal=True)
        self.assertEqual(set(internal), {"collection_type", "file_count",
                                         "file_type"})
        curated = curated_sources(self.schema, self.names)
        slot_uris = raw_slot_uris(self.schema)
        self_alignments = [s for s, pairs in internal.items()
                           if {o for _, o in pairs} & slot_uris.get(s, set())]
        self.assertEqual(sorted(self_alignments),
                         ["collection_type", "file_count", "file_type"])
        generated = {r["subject_id"][len("d4d:"):]: r for r in
                     study_generator().generate_comprehensive_sssom("2001-01-01")}
        tables = (("comprehensive", self.comp), ("generated", generated),
                  ("uri", self.uri))
        for table, rows in tables:
            for slot, pairs in sorted(internal.items()):
                with self.subTest(table=table, slot=slot):
                    row = rows[slot]
                    self.assertLessEqual(pairs, pairs_in(row))
                    self.assertNotIn((row["predicate_id"], row["object_id"]), pairs)
                    if slot not in curated:
                        self.assertNotEqual(row["mapping_status"], "mapped")
                        self.assertNotIn(row["mapping_source"], ("ttl", "schema"))
                        self.assertIn("TTL names only D4D terms", row["comment"])
            for slot, row in sorted(rows.items()):
                if row["mapping_status"] == "mapped":
                    with self.subTest(table=table, slot=slot):
                        self.assertFalse(row["object_id"].startswith("d4d:"))

    def test_named_examples(self):
        """Three of these moved with #3971, #3995 and #4002: each slot now
        carries its class's triple (data_protection_impacts was exactMatch,
        sensitive_elements closeMatch, distribution_dates exactMatch
        schema:dateCreated). ethical_reviews, which was named here with
        exactMatch rai:ethicalReview, is aligned no longer (below)."""
        for slot, pair in {
            "description": ("skos:exactMatch", "schema:description"),
            "missing_data_documentation":
                ("skos:exactMatch", "rai:dataCollectionMissingData"),
            "data_protection_impacts": ("skos:broadMatch", "rai:dataSocialImpact"),
            "sensitive_elements":
                ("skos:exactMatch", "rai:personalSensitiveInformation"),
            "distribution_dates": ("skos:closeMatch", "schema:datePublished"),
            "ip_restrictions": ("skos:closeMatch", "schema:conditionsOfAccess"),
        }.items():
            with self.subTest(slot=slot):
                row = self.comp[slot]
                self.assertEqual((row["predicate_id"], row["object_id"]), pair)

    def test_a_slot_whose_ttl_triple_was_removed_asserts_no_mapping(self):
        """#3971, #3974, #4052: the TTL says nothing about the thirteen slots
        whose triple was removed, and nothing else curated speaks for them,
        so in both tables each row is the keyword hint's status, names no
        term, and keeps no trace of the old target: for the seven whose
        target was a D4D term, other_curated_mappings listed it until
        #4052."""
        curated = curated_sources(self.schema, self.names)
        internal = ttl_slot_alignments(self.names, internal=True)
        for table, rows in (("comprehensive", self.comp), ("uri", self.uri)):
            for slot, target in sorted(SLOT_TRIPLES_REMOVED.items()):
                with self.subTest(table=table, slot=slot):
                    self.assertNotIn(slot, self.ttl)
                    self.assertNotIn(slot, internal)
                    self.assertNotIn(slot, curated)
                    row = rows[slot]
                    self.assertIn(row["mapping_source"], ("heuristic", "none"))
                    self.assertEqual(row["object_id"], "sssom:NoTermFound")
                    self.assertNotIn(target, row["other_curated_mappings"])

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
    """Which slots a curated source speaks for is computed from the inputs
    (``curated_sources``), never read from the table's ``mapping_source``
    (#2996). The resolution writes that column together with the status, so
    a heuristic that overrides a curated slot relabels it ``heuristic``, and a
    test that picked curated rows by that column would never see it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.curated = curated_sources(cls.schema, cls.names)

    def test_curated_slots_include_ones_the_keywords_match(self):
        """Not vacuous: slots whose *names* alone trip a keyword are curated."""
        keywords = gcs.FREE_TEXT_KEYWORDS + gcs.NOVEL_D4D_KEYWORDS
        by_name = [s for s in self.curated if any(k in s for k in keywords)]
        self.assertGreaterEqual(len(by_name), 40)
        self.assertLessEqual(
            FORMERLY_UNMAPPED_TTL_SLOTS - FORMERLY_UNMAPPED_D4D_TARGET_SLOTS
            - FORMERLY_UNMAPPED_WITHDRAWN_SLOTS,
            set(self.curated))
        self.assertFalse((FORMERLY_UNMAPPED_D4D_TARGET_SLOTS
                          | FORMERLY_UNMAPPED_WITHDRAWN_SLOTS) & set(self.curated))

    def test_every_curated_slot_is_mapped_from_its_source_whatever_the_hint(self):
        for slot, source in sorted(self.curated.items()):
            with self.subTest(slot=slot):
                row = self.comp[slot]
                self.assertEqual(
                    (row["mapping_status"], row["mapping_source"]),
                    ("mapped", source),
                    f"{slot} has a curated {source} source in the inputs; "
                    f"{gcs.REGENERATE_HINT}")

    def test_the_hint_decides_status_only_without_a_curated_source(self):
        for slot, row in sorted(self.comp.items()):
            with self.subTest(slot=slot):
                if row["mapping_status"] in ("free_text", "novel_d4d"):
                    self.assertNotIn(slot, self.curated)
                    self.assertEqual(row["mapping_source"], "heuristic")
                    self.assertEqual(row["mapping_status"], row["heuristic_hint"])
                if row["mapping_source"] == "heuristic":
                    self.assertNotIn(slot, self.curated)
                    self.assertIn(row["mapping_status"], ("free_text", "novel_d4d"))


class TestOnlyCuratedRowsClaimCuration(_Committed):
    """#2972: the 22 ``novel_d4d`` rows were written as ``d4d:<slot>
    skos:exactMatch d4d:<slot>`` under semapv:ManualMappingCuration at
    confidence 1.0: a keyword guess that mapped the slot to itself and said
    a curator had. An SSSOM consumer reads ``mapping_justification``, not the
    table's own ``mapping_source``. Checked on both committed tables and on a
    fresh generation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        generated = study_generator().generate_comprehensive_sssom("2001-01-01")
        cls.tables = {"comprehensive": cls.comp, "uri": cls.uri,
                      "generated": {r["subject_id"][len("d4d:"):]: r
                                    for r in generated}}
        cls.curated = curated_sources(cls.schema, cls.names)

    def test_manual_curation_is_claimed_exactly_where_a_curated_source_speaks(self):
        for table, rows in self.tables.items():
            for slot, row in sorted(rows.items()):
                with self.subTest(table=table, slot=slot):
                    self.assertEqual(
                        row["mapping_justification"] == gcs.CURATED_JUSTIFICATION,
                        slot in self.curated)

    def test_a_heuristic_row_asserts_no_mapping(self):
        novel = 0
        for table, rows in self.tables.items():
            for slot, row in sorted(rows.items()):
                if row["mapping_source"] != "heuristic":
                    continue
                with self.subTest(table=table, slot=slot):
                    self.assertEqual((row["object_id"], float(row["confidence"])),
                                     ("sssom:NoTermFound", 0.0))
                    self.assertEqual(
                        (row["predicate_id"], row["mapping_justification"]),
                        ("skos:exactMatch", "semapv:UnspecifiedMatching"))
                    if row["mapping_status"] == "novel_d4d":
                        novel += 1
                        self.assertIn("not curated", row["comment"])
        self.assertGreaterEqual(novel, 3 * 15, "too few novel_d4d rows to test")

    def test_no_row_maps_a_slot_to_itself(self):
        for table, rows in self.tables.items():
            for slot, row in sorted(rows.items()):
                with self.subTest(table=table, slot=slot):
                    self.assertNotEqual(row["object_id"], f"d4d:{slot}")

    def test_a_committed_novel_row_asks_for_a_slot_uri_only_where_none_is_declared(self):
        """On the committed table. Every novel slot there declares a
        slot_uri (``needing slot_uri: 0/301``), so this reads only the "no"
        half; the fixture test below reads the "yes" half (#3377)."""
        declared = raw_slot_uris(self.schema)
        for slot, row in sorted(self.uri.items()):
            if row["mapping_status"] == "novel_d4d":
                with self.subTest(slot=slot):
                    self.assertEqual(row["needs_slot_uri"],
                                     "no" if slot in declared else "yes")

    def test_a_novel_row_still_asks_for_a_slot_uri_where_none_is_declared(self):
        """The URI table's ``needs_slot_uri`` reads the status, not the
        object, so a novel slot with no slot_uri still says yes. The study
        schema has no such slot, so this strips ``addressing_gaps``'s
        ``slot_uri`` from a copy of it (#3377)."""
        slot, uri_line = "addressing_gaps", "slot_uri: d4d:addressingGaps"
        text = SCHEMA.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count(uri_line), 1)
        stripped = "\n".join(line for line in text.split("\n")
                             if line.strip() != uri_line)
        self.assertNotIn("d4d:addressingGaps", stripped)
        with tempfile.TemporaryDirectory() as d:
            changed = Path(d) / SCHEMA.name
            changed.write_text(stripped, encoding="utf-8")
            gen = gcsu.ComprehensiveURISSSOMGenerator(changed, TTL, RECS)
            rows = {r["d4d_slot_name"]: r
                    for r in gen.generate_comprehensive_uri_sssom("2001-01-01")}
        row = rows[slot]
        self.assertEqual((row["mapping_status"], row["d4d_slot_uri_current"]),
                         ("novel_d4d", ""))
        self.assertEqual(row["needs_slot_uri"], "yes")
        for other, r in sorted(rows.items()):
            if other != slot:
                with self.subTest(slot=other):
                    self.assertEqual(r["needs_slot_uri"],
                                     self.uri[other]["needs_slot_uri"])


def sssom_justification_pattern():
    """The ``mapping_justification`` pattern of the SSSOM schema the
    installed ``sssom`` package ships: the SEMAPV terms SSSOM admits."""
    import yaml
    try:
        import sssom_schema
    except ImportError:
        return None
    path = Path(sssom_schema.__file__).parent / "schema" / "sssom_schema.yaml"
    slots = yaml.safe_load(path.read_text(encoding="utf-8"))["slots"]
    return re.compile(slots["mapping_justification"]["pattern"])


class TestNoRowNamesAPerson(_Committed):
    """#2971: every row of every SSSOM table carried ``author_id``
    ``https://orcid.org/0000-0000-0000-0000``, a well-formed ORCID naming
    nobody. The owner's decision: no person on any row. A curated row
    (``mapping_source`` ttl or schema) leaves ``author_id`` empty, since
    nobody is named as the curator, and every other row is credited to the
    generating script through SSSOM's ``mapping_tool``. The curated slots are
    computed from the inputs, not read from the table."""

    PLACEHOLDER = "0000-0000-0000-0000"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        generated = study_generator().generate_comprehensive_sssom("2001-01-01")
        cls.tables = {"comprehensive": cls.comp, "uri": cls.uri,
                      "generated": {r["subject_id"][len("d4d:"):]: r
                                    for r in generated}}
        cls.curated = curated_sources(cls.schema, cls.names)
        # Every SSSOM table the repository commits, the structural one
        # included.
        cls.all_tables = sorted(
            set((REPO / "src/data_sheets_schema/semantic_exchange").glob("*sssom*.tsv"))
            | set((REPO / "data/semantic_exchange").glob("*sssom*.tsv")))

    #: The legacy property-level table, its interface subset and the 33-slot
    #: URI table, retired with their generators (#3884). Nothing read them,
    #: and no check could hold them to their inputs (the property-level table
    #: had fallen 70 TTL triples behind); a copy put back would be unchecked
    #: again.
    RETIRED = ("d4d_rocrate_sssom_mapping.tsv",
               "d4d_rocrate_sssom_mapping_subset.tsv",
               "d4d_rocrate_sssom_uri_mapping.tsv")

    def test_the_repository_commits_the_tables_this_checks(self):
        names = {p.name for p in self.all_tables}
        for name in (COMP.name, URI.name,
                     "d4d_rocrate_structural_mapping.sssom.tsv"):
            self.assertIn(name, names)

    def test_the_retired_tables_and_their_generators_are_gone(self):
        """#3884: the only SSSOM tables committed are the drift-checked ones,
        and nothing that wrote or named a retired table is left to recreate
        it: no generator, no Makefile target, no converter default."""
        self.assertEqual(
            {p.name for p in self.all_tables},
            {COMP.name, URI.name, "d4d_rocrate_structural_mapping.sssom.tsv"})
        for script in ("generate_sssom_mapping.py",
                       "generate_sssom_uri_mapping.py"):
            self.assertFalse((REPO / "src/semantic_exchange" / script).exists(),
                             script)
        for path in ("Makefile",
                     "src/fairscape_integration/fairscape_to_d4d.py",
                     "src/fairscape_integration/cli.py"):
            text = (REPO / path).read_text(encoding="utf-8")
            for name in self.RETIRED:
                # The converter's comment names the table it no longer
                # loads; a path to it would be a reader.
                self.assertNotIn(f"semantic_exchange/{name}", text, path)
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        for target in ("gen-sssom-full", "gen-sssom-subset", "gen-sssom-uri:",
                       "gen-sssom:"):
            self.assertNotIn(target, makefile)

    def test_no_table_carries_the_placeholder_or_an_author(self):
        for path in self.all_tables:
            with self.subTest(table=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(self.PLACEHOLDER, text)
                self.assertNotIn("orcid.org", text)
                for row in read_table(text):
                    self.assertEqual(row.get("author_id") or "", "",
                                     row.get("subject_id"))

    def test_the_tool_is_credited_exactly_where_no_curated_source_speaks(self):
        credited = 0
        for table, rows in self.tables.items():
            for slot, row in sorted(rows.items()):
                with self.subTest(table=table, slot=slot):
                    self.assertEqual(row["author_id"], "")
                    if slot in self.curated:
                        self.assertEqual(row["mapping_tool"], "")
                    else:
                        credited += 1
                        self.assertEqual(row["mapping_tool"], gcs.MAPPING_TOOL)
                        self.assertTrue(row["mapping_tool"].endswith(
                            "src/semantic_exchange/generate_comprehensive_sssom.py"))
        self.assertGreaterEqual(credited, 3 * 100, "too few uncurated rows to test")

    def test_the_tool_column_follows_author_id(self):
        for cls in (gcs.ComprehensiveSSSOMGenerator,
                    gcsu.ComprehensiveURISSSOMGenerator):
            with self.subTest(generator=cls.__name__):
                i = cls.FIELDNAMES.index("author_id")
                self.assertEqual(cls.FIELDNAMES[i + 1], "mapping_tool")


class TestStatusRowsUseSSSOMsNoMatchForm(_Committed):
    """#3361: the ``free_text``, ``novel_d4d`` and ``unmapped`` rows were
    written with ``semapv:UnmappedProperty`` / ``semapv:UnmappableProperty``
    as the predicate, ``semapv:FreeTextProperty`` /
    ``semapv:RequiresResearch`` as the justification and an empty
    ``object_id``. SEMAPV defines none of those four terms, and SSSOM
    requires an object. SSSOM's form for "no match" is ``object_id
    sssom:NoTermFound`` with a justification SEMAPV defines.

    The admitted justifications are read from the SSSOM schema the installed
    ``sssom`` package ships, not from the generator. Checked on both
    committed tables and on a fresh generation. Not checked here: the one
    ``recommended`` row's ``semapv:SuggestedMapping``, which that pattern
    does not admit either. That row asserts a mapping, not a status, so it
    is outside #3361 and needs its own decision."""

    NO_MATCH = ("free_text", "novel_d4d", "unmapped")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        generated = study_generator().generate_comprehensive_sssom("2001-01-01")
        cls.tables = {"comprehensive": cls.comp, "uri": cls.uri,
                      "generated": {r["subject_id"][len("d4d:"):]: r
                                    for r in generated}}
        cls.pattern = sssom_justification_pattern()

    def test_a_status_row_names_no_term_found_and_only_a_status_row_does(self):
        seen = 0
        for table, rows in self.tables.items():
            for slot, row in sorted(rows.items()):
                with self.subTest(table=table, slot=slot):
                    no_match = row["mapping_status"] in self.NO_MATCH
                    self.assertEqual(row["object_id"] == "sssom:NoTermFound",
                                     no_match)
                    self.assertNotEqual(row["object_id"], "")
                    if no_match:
                        seen += 1
                        self.assertEqual(
                            (row["predicate_id"], row["mapping_justification"],
                             row["object_label"], row["object_source"]),
                            ("skos:exactMatch", "semapv:UnspecifiedMatching",
                             "", ""))
        self.assertGreaterEqual(seen, 3 * 100, "too few status rows to test")

    def test_no_row_uses_a_semapv_term_as_its_predicate(self):
        for table, rows in self.tables.items():
            for slot, row in sorted(rows.items()):
                with self.subTest(table=table, slot=slot):
                    self.assertFalse(row["predicate_id"].startswith("semapv:"))

    def test_every_justification_but_a_suggestion_is_one_sssom_admits(self):
        if self.pattern is None:
            self.skipTest("the sssom_schema package is not installed")
        for table, rows in self.tables.items():
            for slot, row in sorted(rows.items()):
                if row["mapping_status"] == "recommended":
                    continue
                with self.subTest(table=table, slot=slot):
                    self.assertRegex(row["mapping_justification"], self.pattern)


class TestRecommendationsAudit(_Committed):
    """#2974: since #2935 the recommendations file feeds the table's
    ``recommended`` rows. Nine surfaced; the audit withdrew those eight, whose
    suggested term names another notion, cannot hold the slot's value, or is
    not a schema.org term, and eight more that a curated target shadows
    (16 in all; #3376). A withdrawn entry keeps its URI and the reason in
    ``review_note``."""

    WITHDRAWN_FROM_THE_TABLE = {
        "credit_roles", "erratum_url", "identifiers_removed", "limitation_type",
        "missing_value_code", "tool_accuracy", "was_inferred_derived",
        "was_validated_verified",
    }
    #: Withdrawn too, but never surfaced: a curated target maps each slot.
    SHADOWED_BY_A_CURATED_TARGET = {
        "distribution_dates", "end_date", "precision",
        "representative_verification", "start_date", "target_dataset",
        "tools", "version_access",
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(RECS, encoding="utf-8", newline="") as f:
            cls.recs = {r["attribute"]: r
                        for r in csv.DictReader(f, delimiter="\t")}

    def test_a_withdrawn_suggestion_is_silent_and_says_why(self):
        withdrawn = {a for a, r in self.recs.items()
                     if r["review_note"].startswith("withdrawn ")}
        self.assertLessEqual(self.WITHDRAWN_FROM_THE_TABLE, withdrawn)
        for attr in sorted(withdrawn):
            with self.subTest(attribute=attr):
                r = self.recs[attr]
                self.assertEqual((r["suggested_uri"], r["confidence"]), ("", ""))
                self.assertIn("#2974", r["review_note"])
                self.assertNotEqual(self.comp[attr]["mapping_status"], "recommended")

    def test_the_audit_withdrew_the_eight_surfaced_and_eight_shadowed(self):
        """The docstring's count, held to the file (#3376)."""
        withdrawn = {a for a, r in self.recs.items()
                     if r["review_note"].startswith("withdrawn ")}
        self.assertEqual(withdrawn, self.WITHDRAWN_FROM_THE_TABLE
                         | self.SHADOWED_BY_A_CURATED_TARGET)
        self.assertEqual(len(withdrawn), 16)
        for attr in sorted(self.SHADOWED_BY_A_CURATED_TARGET):
            with self.subTest(attribute=attr):
                self.assertEqual(self.comp[attr]["mapping_status"], "mapped")
                self.assertIn(self.comp[attr]["mapping_source"], ("ttl", "schema"))

    def test_every_confidence_names_a_uri(self):
        """``add_slot_uris.py`` selects entries by confidence alone and writes
        their ``suggested_uri`` into the schema, so a graded entry with no URI
        would write an empty slot_uri."""
        for attr, r in sorted(self.recs.items()):
            if r["confidence"] in ("high", "medium"):
                with self.subTest(attribute=attr):
                    self.assertTrue(r["suggested_uri"])

    def test_no_suggestion_names_a_term_schema_org_does_not_define(self):
        """``schema:date`` is not a schema.org term (#3124); rdflib's list."""
        from rdflib.namespace import SDO
        for attr, r in sorted(self.recs.items()):
            uri = r["suggested_uri"]
            if uri.startswith("schema:"):
                with self.subTest(attribute=attr, uri=uri):
                    self.assertIn(f"https://schema.org/{uri[len('schema:'):]}", SDO)

    def test_each_recommended_row_is_a_suggestion_the_file_still_makes(self):
        for slot, row in sorted(self.comp.items()):
            if row["mapping_status"] == "recommended":
                with self.subTest(slot=slot):
                    self.assertEqual(row["object_id"],
                                     self.recs[slot]["suggested_uri"])
                    self.assertEqual(row["mapping_justification"],
                                     "semapv:SuggestedMapping")
        self.assertEqual(
            sorted(s for s, r in self.comp.items()
                   if r["mapping_status"] == "recommended"), ["access_url"])


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

    def test_owners_are_the_declarers_no_declaring_ancestor_precedes(self):
        """The rule, recomputed from the raw YAML (#2998): a class owns a slot
        when it declares it and no is_a/mixin ancestor that also declares it
        does. The merged schema repeats inherited attributes on subclasses,
        so every declarer carries the slot and the carrier test above cannot
        tell an owner from a subclass that repeats it."""
        declarers = raw_declarers(self.schema)
        for slot, row in sorted(self.comp.items()):
            with self.subTest(slot=slot):
                declared = declarers.get(slot, set())
                expected = sorted(c for c in declared
                                  if not declared & raw_ancestors(self.schema, c))
                self.assertEqual(
                    list(filter(None, row["d4d_owning_classes"].split("|"))),
                    expected)

    def test_named_owners(self):
        self.assertEqual(self.comp["description"]["d4d_owning_classes"],
                         "DatasetProperty|Grant|NamedThing|Organization")
        self.assertEqual(self.comp["used_software"]["d4d_schema_path"],
                         "DatasetProperty.used_software")

    def test_the_path_is_dataset_else_the_first_owner(self):
        """``Dataset`` when it carries the slot (raw YAML), else the first
        owning class by name; a subclass that repeats the slot is never the
        path when an ancestor owns it."""
        dataset = raw_carried(self.schema, "Dataset")
        for slot, row in sorted(self.comp.items()):
            with self.subTest(slot=slot):
                owners = list(filter(None, row["d4d_owning_classes"].split("|")))
                if slot in dataset:
                    self.assertEqual(row["d4d_schema_path"], f"Dataset.{slot}")
                elif owners:
                    self.assertEqual(row["d4d_schema_path"], f"{owners[0]}.{slot}")

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


class TestURITableReadsEveryDeclaredSlotUri(_Committed):
    """``d4d_slot_uri_current`` against the raw YAML (#2997). Before #2935
    the URI table read slot_uri from top-level ``slots:`` only (31/284); a
    slot_uri set on a class attribute or in ``slot_usage`` counts too."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.declared = raw_slot_uris(cls.schema)
        cls.top_level = {slot for slot, sdef in (cls.schema.get("slots") or {}).items()
                         if (sdef or {}).get("slot_uri")}

    def test_the_current_slot_uri_is_one_the_schema_declares(self):
        for slot, row in sorted(self.uri.items()):
            with self.subTest(slot=slot):
                current = row["d4d_slot_uri_current"]
                if slot in self.declared:
                    self.assertIn(current, self.declared[slot])
                else:
                    self.assertEqual(current, "")

    def test_a_slot_uri_declared_only_below_the_top_level_counts(self):
        below = set(self.declared) - self.top_level
        self.assertGreater(len(below), 200)
        for slot in sorted(below):
            with self.subTest(slot=slot):
                self.assertTrue(self.uri[slot]["d4d_slot_uri_current"])

    def test_the_coverage_header_counts_every_declared_slot_uri(self):
        text = URI.read_text(encoding="utf-8")
        n = len(self.names)
        self.assertIn(f"# Current slot_uri coverage: {len(self.declared)}/{n} ",
                      text)

    def test_needs_slot_uri_only_where_none_is_declared(self):
        for slot, row in sorted(self.uri.items()):
            with self.subTest(slot=slot):
                expected = ("yes" if slot not in self.declared
                            and row["mapping_status"] in ("recommended", "novel_d4d")
                            else "no")
                self.assertEqual(row["needs_slot_uri"], expected)


#: An excerpt of the RO-Crate 1.1 JSON-LD context
#: (https://w3id.org/ro/crate/1.1/context, version 1.1.3), written here from
#: the published file rather than taken from the generator: every property
#: term it keys bare for an IRI outside schema.org, and every prefix it
#: declares. It keys schema.org's terms by their local names.
ROCRATE_11_BARE = {
    "cite-as": "https://www.w3.org/ns/iana/link-relations/relation#cite-as",
    "conformsTo": "http://purl.org/dc/terms/conformsTo",
    "hasFile": "http://pcdm.org/models#hasFile",
    "hasMember": "http://pcdm.org/models#hasMember",
    "importedBy": "http://purl.org/pav/importedBy",
    "importedFrom": "http://purl.org/pav/importedFrom",
    "importedOn": "http://purl.org/pav/importedOn",
    "input": "https://bioschemas.org/ComputationalWorkflow#input",
    "output": "https://bioschemas.org/ComputationalWorkflow#output",
    "retrievedBy": "http://purl.org/pav/retrievedBy",
    "retrievedFrom": "http://purl.org/pav/retrievedFrom",
    "retrievedOn": "http://purl.org/pav/retrievedOn",
    "wasDerivedFrom": "http://www.w3.org/ns/prov#wasDerivedFrom",
}
ROCRATE_11_PREFIXES = {
    "bibo": "http://purl.org/ontology/bibo/",
    "cc": "http://creativecommons.org/ns#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "frapo": "http://purl.org/cerif/frapo/",
    "pav": "http://purl.org/pav/",
    "pcdm": "http://pcdm.org/models#",
    "prov": "http://www.w3.org/ns/prov#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfa": "http://www.w3.org/ns/rdfa#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rel": "https://www.w3.org/ns/iana/link-relations/relation#",
    "roterms": "http://purl.org/ro/roterms#",
    "schema": "http://schema.org/",
    "wf4ever": "http://purl.org/ro/wf4ever#",
    "wfdesc": "http://purl.org/ro/wfdesc#",
    "wfprov": "http://purl.org/ro/wfprov#",
}


@functools.lru_cache(maxsize=None)
def study_generator():
    """The generator on the study's schema, TTL and recommendations."""
    return gcs.ComprehensiveSSSOMGenerator(SCHEMA, TTL, RECS)


class TestRoCratePathFollowsTheContext(unittest.TestCase):
    """``rocrate_json_path`` names the key a crate written with the RO-Crate
    1.1 context carries the object under (#3052). The rule this replaced
    keyed only ``schema:`` objects bare, so ``dcterms:conformsTo`` got a
    ``dcterms:conformsTo`` key (the context declares ``dct``, not
    ``dcterms``, and binds the bare ``conformsTo`` to that IRI) and
    ``prov:wasDerivedFrom`` lost its bare term. The rule before #2935 keyed
    ``schema:conformsTo`` as ``conformsTo``, which expands to Dublin Core's
    IRI.

    Checked on the generator's rows and on the committed table. Not
    checked: whether a ``schema:`` object is a term of the schema.org release
    the context was built from (the excerpt above cannot say; see the
    generator's ``rocrate_key``)."""

    @classmethod
    def setUpClass(cls):
        cls.gen = study_generator()
        cls.tables = {
            "generated": cls.gen.generate_comprehensive_sssom("2001-01-01"),
            "committed": read_table(COMP),
        }

    @staticmethod
    def key(path):
        return path.split("['", 1)[1][:-2]

    def test_named_keys(self):
        for curie, key in {
            "dcterms:conformsTo": "conformsTo",
            "prov:wasDerivedFrom": "wasDerivedFrom",
            "schema:conformsTo": "schema:conformsTo",
            "schema:name": "name",
            "dcterms:accessRights": "dct:accessRights",
            "rdf:ID": "rdf:ID",
            "dcat:byteSize": "dcat:byteSize",
            "evi:md5": "evi:md5",
        }.items():
            with self.subTest(curie=curie):
                self.assertEqual(self.gen.rocrate_key(curie), key)
        # No row's object is prov:wasDerivedFrom since #2974 withdrew
        # was_inferred_derived's suggestion; the key is checked above.
        for table, rows in self.tables.items():
            by_slot = {r["subject_id"]: r for r in rows}
            for slot, key in {"d4d:conforms_to_standard": "conformsTo",
                              "d4d:conforms_to": "schema:conformsTo"}.items():
                with self.subTest(table=table, slot=slot):
                    self.assertEqual(by_slot[slot]["rocrate_json_path"],
                                     f"@graph[?@type='Dataset']['{key}']")

    def test_every_key_expands_to_the_object_under_the_context(self):
        """A bare key or a key on a declared prefix expands, under the
        excerpt, to the object's IRI, and is the shortest such key; a key on
        any other prefix is the object's own CURIE, for a vocabulary the
        context declares no prefix for."""
        schema_org = ("http://schema.org/", "https://schema.org/")
        for table, rows in self.tables.items():
            for row in rows:
                obj, path = row["object_id"], row["rocrate_json_path"]
                with self.subTest(table=table, slot=row["subject_id"], object=obj):
                    # A row that asserts no mapping names no key (#3361).
                    if obj == "sssom:NoTermFound":
                        self.assertEqual(path, "")
                        continue
                    namespace = row["object_source"]
                    self.assertNotEqual(namespace, "unknown")
                    if namespace in schema_org:
                        namespace = schema_org[0]
                    local = obj.split(":", 1)[1]
                    iri = namespace + local
                    key = self.key(path)
                    bare = ({k for k, v in ROCRATE_11_BARE.items() if v == iri}
                            | ({local} if namespace == schema_org[0]
                               and local not in ROCRATE_11_BARE else set()))
                    if bare:
                        self.assertEqual({key}, bare)
                    elif ":" in key and key.split(":", 1)[0] in ROCRATE_11_PREFIXES:
                        prefix, rest = key.split(":", 1)
                        self.assertEqual(ROCRATE_11_PREFIXES[prefix] + rest, iri)
                    else:
                        self.assertNotIn(namespace, ROCRATE_11_PREFIXES.values())
                        self.assertEqual(key, obj)
                    self.assertFalse(key.startswith("dcterms:"))


class TestDisagreementsAreListed(unittest.TestCase):
    """A TTL/schema disagreement the lists do not name is new and must be
    looked at; a listed one whose pairs changed must be looked at again; a
    listed one that no longer occurs is stale."""

    @classmethod
    def setUpClass(cls):
        cls.gen = gcs.ComprehensiveSSSOMGenerator(SCHEMA, TTL, RECS)
        cls.listed = {**gcs.ACCEPTED_DISAGREEMENTS, **gcs.OPEN_DISAGREEMENTS}

    def test_no_unlisted_changed_or_stale_disagreement(self):
        report = self.gen.disagreement_report()
        self.assertEqual(report["unlisted"], [])
        self.assertEqual(report["changed"], [])
        self.assertEqual(report["stale"], [])

    def test_the_lists_are_disjoint_and_give_reasons(self):
        self.assertFalse(set(gcs.ACCEPTED_DISAGREEMENTS) & set(gcs.OPEN_DISAGREEMENTS))
        for slot, entry in self.listed.items():
            with self.subTest(slot=slot):
                self.assertGreater(len(entry.reason.strip()), 20)

    def test_each_listing_names_the_pairs_the_inputs_declare(self):
        """Read independently of the generator (#2991): the TTL's triples by
        rdflib and the schema's external declarations from the raw YAML must
        be exactly the pairs the listing was written for. The TTL side is
        every external triple on the slot, slot-level and ``<Class>_<slot>``
        alike (#3053): ``resources`` is listed with both its slot-level
        relatedMatch and its class-scoped exactMatch."""
        schema = raw_schema()
        names = raw_slot_names(schema)
        ttl = ttl_all_alignments(schema, names)
        declared = raw_external_declarations(schema)
        self.assertEqual(ttl["resources"],
                         {("skos:relatedMatch", "schema:hasPart"),
                          ("skos:exactMatch", "schema:hasPart")})
        for slot, entry in sorted(self.listed.items()):
            with self.subTest(slot=slot):
                self.assertEqual(set(entry.ttl),
                                 {f"{p} {o}" for p, o in ttl.get(slot, set())})
                self.assertEqual(set(entry.schema),
                                 {f"{p} {o}" for p, o in declared.get(slot, set())})

    def test_every_slot_where_the_inputs_disagree_is_listed(self):
        """The disagreement rule recomputed from the inputs (#3053): a slot
        disagrees when the schema declares external targets and some
        external TTL pair on it, from any subject, is not among them."""
        schema = raw_schema()
        names = raw_slot_names(schema)
        ttl = ttl_all_alignments(schema, names)
        declared = raw_external_declarations(schema)
        disagree = {slot for slot, pairs in ttl.items()
                    if declared.get(slot) and pairs - declared[slot]}
        self.assertIn("resources", disagree)
        self.assertEqual(sorted(disagree), sorted(self.listed))

    def _generator_with_ttl(self, edit):
        """A generator on the real schema and an edited copy of the TTL."""
        text = TTL.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as d:
            changed = Path(d) / TTL.name
            changed.write_text(edit(text), encoding="utf-8")
            return gcs.ComprehensiveSSSOMGenerator(SCHEMA, changed, RECS)

    def test_a_changed_class_scoped_triple_on_a_listed_slot_is_changed(self):
        """#3053's first reproduction: ``resources`` also has a slot-level
        triple, so its class-scoped ones were never checked, and the listing
        held while one of them changed target."""
        old = "d4d:FileCollection_resources skos:exactMatch schema:hasPart ."
        new = "d4d:FileCollection_resources skos:exactMatch schema:isPartOf ."
        self.assertEqual(TTL.read_text(encoding="utf-8").count(old), 1)
        gen = self._generator_with_ttl(lambda text: text.replace(old, new))
        res = gen.resolutions["resources"]
        self.assertEqual((res.predicate, res.object, res.disagreement),
                         ("skos:relatedMatch", "schema:hasPart", "changed"))
        report = gen.disagreement_report()
        self.assertEqual((report["changed"], report["unlisted"], report["stale"]),
                         (["resources"], [], []))
        self.assertTrue(any("disagreement on resources is not the listed one" in w
                            and "skos:exactMatch schema:isPartOf" in w
                            for w in gen.warnings()))

    def test_a_disagreeing_class_scoped_triple_on_an_unlisted_slot_warns(self):
        """#3053's second reproduction, in the form /d4d-add-mapping writes:
        a ``<Class>_<slot>`` triple beside a slot-level one that agrees."""
        self.assertIn("description", raw_carried(raw_schema(), "FileCollection"))
        added = "d4d:FileCollection_description skos:exactMatch schema:abstract .\n"
        gen = self._generator_with_ttl(lambda text: text + added)
        res = gen.resolutions["description"]
        self.assertEqual((res.predicate, res.object, res.disagreement),
                         ("skos:exactMatch", "schema:description", "unlisted"))
        self.assertEqual(gen.disagreement_report()["unlisted"], ["description"])
        self.assertTrue(any("disagree on description" in w for w in gen.warnings()))

    def test_open_disagreements_warn_on_every_run(self):
        warnings = "\n".join(self.gen.warnings())
        for slot in gcs.OPEN_DISAGREEMENTS:
            self.assertIn(f"disagreement on {slot}:", warnings)

    def test_a_stale_listing_warns(self):
        stale = gcs.Listed(("skos:exactMatch schema:x",), ("skos:exactMatch dcterms:x",),
                           "not a disagreement")
        with mock.patch.dict(gcs.ACCEPTED_DISAGREEMENTS, {"doi": stale}):
            report = self.gen.disagreement_report()
            self.assertIn("doi", report["stale"])
            self.assertTrue(any("doi is listed" in w for w in self.gen.warnings()))

    def test_no_accepted_listing_names_a_schema_org_term_that_does_not_exist(self):
        """#2990: the TTL aligned the conforms_to slots to schema:conformsTo,
        which schema.org does not define (RO-Crate 1.1's context maps its
        conformsTo key to dcterms:conformsTo). A side that names no term is
        probably wrong, so the listing is open, not accepted. Checked against
        rdflib's schema.org term list."""
        from rdflib.namespace import SDO
        for slot, entry in sorted(gcs.ACCEPTED_DISAGREEMENTS.items()):
            for pair in entry.ttl + entry.schema:
                obj = pair.split(" ", 1)[1]
                if obj.startswith("schema:"):
                    with self.subTest(slot=slot, object=obj):
                        self.assertIn(f"https://schema.org/{obj[len('schema:'):]}", SDO)
        self.assertNotIn("https://schema.org/conformsTo", SDO)

    def test_every_declaration_a_reason_cites_is_attributed_to_its_class(self):
        """#3140: the regulatory_restrictions reason said the schema
        serialises the slot as dcterms:accessRights. The row's path class,
        Dataset, declares slot_uri d4d:regulatoryRestrictions; dcterms:
        accessRights is the slot_uri of
        ExportControlRegulatoryRestrictions.regulatory_restrictions, another
        attribute with the same name. From the raw YAML: every
        ``<metaslot> <target>`` a reason cites is declared for the slot name,
        and one the path class does not see (its own, an ancestor's or the
        top-level slot's) is named with a class that declares it."""
        schema = raw_schema()
        places = raw_declaration_places(schema)
        for slot, entry in sorted(self.listed.items()):
            seen = raw_seen_by(schema, raw_path_class(schema, slot), slot)
            for metaslot, target in REASON_CITES.findall(entry.reason):
                with self.subTest(slot=slot, cites=f"{metaslot} {target}"):
                    where = places.get(slot, {}).get((metaslot, target), set())
                    self.assertTrue(where, "no declaration of the slot says so")
                    if not where & seen:
                        self.assertTrue(
                            any(declaration_name(cls, slot) in entry.reason
                                for cls in where),
                            f"only {sorted(where)} declare it, the path class "
                            "sees none of them, and the reason names none")
        self.assertIn(("slot_uri", "dcterms:title"),
                      REASON_CITES.findall(self.listed["title"].reason))
        self.assertIn(("slot_uri", "dcterms:accessRights"),
                      REASON_CITES.findall(
                          self.listed["regulatory_restrictions"].reason))

    def test_a_reason_names_the_attribute_whose_pairs_the_path_class_cannot_see(self):
        """Checked on the listing's schema pairs, not on what its reason
        cites, so a reason that cites none of them is held to it too: the
        reason before #3140 cited only "the DUO broad_mappings" for the DUO
        pairs. A pair that no declaration the path class sees makes is another
        class's, and the reason names each class that owns it as
        ``<Class>.<slot>``."""
        schema = raw_schema()
        places = raw_declaration_places(schema)
        metaslots = {}
        for metaslot, predicate in SCHEMA_KINDS:
            metaslots.setdefault(predicate, []).append(metaslot)
        unseen = set()
        for slot, entry in sorted(self.listed.items()):
            seen = raw_seen_by(schema, raw_path_class(schema, slot), slot)
            for pair in entry.schema:
                predicate, target = pair.split(" ", 1)
                where = set().union(*(places.get(slot, {}).get((m, target), set())
                                      for m in metaslots[predicate]))
                with self.subTest(slot=slot, pair=pair):
                    self.assertTrue(where)
                    if where & seen:
                        continue
                    unseen.add(slot)
                    for cls in sorted(c for c in where
                                      if not where & raw_ancestors(schema, c)):
                        self.assertIn(declaration_name(cls, slot), entry.reason)
        self.assertIn("regulatory_restrictions", unseen)
        self.assertIn("media_type", unseen)

    def test_media_type_attributes_its_exact_mapping_and_calls_it_none_a_serialisation(self):
        """#3193, from the raw YAML: the row's path class, DistributionFormat,
        declares its own media_type attribute (slot_uri dcat:mediaType, no
        exact_mappings) and does not list the top-level slot, so it does not
        see the top-level slot's exact_mappings schema:encodingFormat, which
        File.media_type repeats. The reason used to say that exact mapping
        "serialises the slot"; only a slot_uri serialises one."""
        schema = raw_schema()
        slot = "media_type"
        classes = schema["classes"]
        self.assertEqual(raw_path_class(schema, slot), "DistributionFormat")
        own = classes["DistributionFormat"]["attributes"][slot]
        self.assertEqual((own.get("slot_uri"), own.get("exact_mappings")),
                         ("dcat:mediaType", None))
        self.assertNotIn(slot, classes["DistributionFormat"].get("slots") or [])
        self.assertTrue(raw_hides_top_level(schema, "DistributionFormat", slot))
        self.assertNotIn("", raw_seen_by(schema, "DistributionFormat", slot))
        self.assertEqual(
            raw_declaration_places(schema)[slot][("exact_mappings",
                                                  "schema:encodingFormat")],
            {"", "File"})
        reason = gcs.ACCEPTED_DISAGREEMENTS[slot].reason
        for phrase in ("DistributionFormat declares its own media_type attribute",
                       declaration_name("", slot), "File.media_type"):
            self.assertIn(phrase, reason)
        self.assertNotIn("serialises the slot as", reason)

    def test_the_hiding_rule_is_linkmls_whether_or_not_slots_lists_the_name(self):
        """#3392: an attribute on the class or an ancestor replaces the
        top-level slot even when the class also lists the name under
        ``slots:``. The helper is checked against linkml_runtime's
        ``SchemaView.induced_slot`` on a fixture where the two declarations
        carry different slot_uris, and against every class of the merged
        schema that lists a name both ways."""
        from linkml_runtime.utils.schemaview import SchemaView
        fixture = textwrap.dedent("""\
            id: https://example.org/s3371
            name: s3371
            prefixes:
              linkml: https://w3id.org/linkml/
              ex: https://example.org/
            default_prefix: ex
            imports:
              - linkml:types
            slots:
              foo:
                slot_uri: ex:top
            classes:
              Both:
                slots:
                  - foo
                attributes:
                  foo:
                    slot_uri: ex:attr
              Child:
                is_a: Both
              SlotsOnly:
                slots:
                  - foo
            """)
        import yaml
        schema = yaml.safe_load(fixture)
        sv = SchemaView(fixture)
        for cls in ("Both", "Child", "SlotsOnly"):
            with self.subTest(cls=cls):
                induced = sv.induced_slot("foo", cls).slot_uri
                self.assertEqual(raw_hides_top_level(schema, cls, "foo"),
                                 induced == "ex:attr")
        self.assertTrue(raw_hides_top_level(schema, "Both", "foo"))
        self.assertFalse(raw_hides_top_level(schema, "SlotsOnly", "foo"))

        merged = raw_schema()
        both = sorted((c, n) for c, cdef in merged["classes"].items()
                      for n in set((cdef or {}).get("attributes") or {})
                      & set((cdef or {}).get("slots") or []))
        self.assertTrue(both, "the merged schema lists no name both ways")
        for cls, name in both:
            with self.subTest(cls=cls, slot=name):
                self.assertTrue(raw_hides_top_level(merged, cls, name))
                self.assertNotIn("", raw_seen_by(merged, cls, name))

    def test_only_a_slot_uri_is_said_to_serialise_the_slot(self):
        """#3193: the strength-only template says "the schema's <metaslot>
        <target> serialises the slot"; an exact or other mapping states an
        equivalence and is not how the slot is written."""
        cites = re.compile(r"the schema's (\w+) \S+ serialises the slot")
        found = 0
        for slot, entry in sorted(self.listed.items()):
            for metaslot in cites.findall(entry.reason):
                found += 1
                with self.subTest(slot=slot):
                    self.assertEqual(metaslot, "slot_uri")
        self.assertGreaterEqual(found, 4)

    def test_regulatory_restrictions_is_listed_as_a_shared_name(self):
        """#3140, from the raw YAML and as the reason states it: Dataset's
        regulatory_restrictions is an ExportControlRegulatoryRestrictions
        object with a D4D slot_uri and no external mapping; the schema's
        pairs are those of a multivalued string attribute of that class; the
        core schema's counterpart, CoreDataset.regulatory_restrictions,
        carries the TTL's target as a broad mapping. So it is not the
        cross-vocabulary case the reason used to call it."""
        from data_sheets_schema.schema_cache import load_yaml
        slot = "regulatory_restrictions"
        classes = raw_schema()["classes"]
        on_dataset = classes["Dataset"]["attributes"][slot]
        other = classes["ExportControlRegulatoryRestrictions"]["attributes"][slot]
        self.assertEqual((on_dataset["slot_uri"], on_dataset["range"]),
                         ("d4d:regulatoryRestrictions",
                          "ExportControlRegulatoryRestrictions"))
        self.assertEqual([m for m, _ in SCHEMA_KINDS[1:] if on_dataset.get(m)], [])
        self.assertEqual((other["slot_uri"], other["range"], other["multivalued"]),
                         ("dcterms:accessRights", "string", True))
        self.assertEqual(sorted(other["broad_mappings"]),
                         ["DUO:0000021", "DUO:0000022", "DUO:0000028"])
        core = load_yaml(REPO / "src/data_sheets_schema/schema/D4D_Core.yaml")
        self.assertEqual(
            core["classes"]["CoreDataset"]["attributes"][slot]["broad_mappings"],
            ["schema:conditionsOfAccess"])
        self.assertEqual(self.gen.declared_slot_uri(slot),
                         "d4d:regulatoryRestrictions")
        self.assertEqual({p.where for p, _ in self.gen.schema_pairs(slot)},
                         {"ExportControlRegulatoryRestrictions"})
        reason = gcs.ACCEPTED_DISAGREEMENTS[slot].reason
        self.assertFalse(reason.startswith("cross-vocabulary"))
        for phrase in ("Dataset, declares regulatory_restrictions with slot_uri "
                       "d4d:regulatoryRestrictions",
                       "ExportControlRegulatoryRestrictions.regulatory_restrictions",
                       "CoreDataset.regulatory_restrictions"):
            self.assertIn(phrase, reason)

    def test_the_conforms_to_slots_are_open(self):
        for slot in ("conforms_to", "conforms_to_class", "conforms_to_schema"):
            with self.subTest(slot=slot):
                self.assertIn(slot, gcs.OPEN_DISAGREEMENTS)
                self.assertNotIn(slot, gcs.ACCEPTED_DISAGREEMENTS)
                self.assertEqual(self.gen.resolutions[slot].disagreement, "open")
                row = next(r for r in read_table(COMP)
                           if r["subject_id"] == f"d4d:{slot}")
                self.assertIn("TTL and schema disagree (open)", row["comment"])

    def test_a_changed_ttl_pair_on_an_accepted_slot_is_not_accepted(self):
        """#2991's reproduction: the TTL's license_and_use_terms triple moves
        to another predicate and target. Matched by slot name alone it stayed
        'accepted' under a reason that no longer held."""
        old = "d4d:license_and_use_terms skos:closeMatch schema:license ."
        new = "d4d:license_and_use_terms skos:relatedMatch schema:usageInfo ."
        text = TTL.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1)
        with tempfile.TemporaryDirectory() as d:
            changed = Path(d) / TTL.name
            changed.write_text(text.replace(old, new), encoding="utf-8")
            gen = gcs.ComprehensiveSSSOMGenerator(SCHEMA, changed, RECS)
        res = gen.resolutions["license_and_use_terms"]
        self.assertEqual((res.predicate, res.object, res.disagreement),
                         ("skos:relatedMatch", "schema:usageInfo", "changed"))
        report = gen.disagreement_report()
        self.assertEqual(report["changed"], ["license_and_use_terms"])
        self.assertEqual((report["unlisted"], report["stale"]), ([], []))
        self.assertTrue(any(
            "disagreement on license_and_use_terms is not the listed one" in w
            and "skos:relatedMatch schema:usageInfo" in w
            and "skos:closeMatch schema:license" in w
            for w in gen.warnings()))
        row = next(r for r in gen.generate_comprehensive_sssom("2001-01-01")
                   if r["subject_id"] == "d4d:license_and_use_terms")
        self.assertIn("TTL and schema disagree (not the listed pairs)", row["comment"])


class TestCommittedTablesRegenerate(unittest.TestCase):
    """Drift: regenerated in memory under the date the file records, the
    table must be byte-for-byte the committed one. A change that moves a
    slot's mapping regenerates both tables in the same commit: a schema
    release, and equally an edit to the SKOS alignment TTL or the URI
    recommendations file (#2993)."""

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
            self.fail(f"{committed.name} does not regenerate from the schema, "
                      "the SKOS alignment TTL and the recommendations file "
                      f"({len(differ)} rows differ: {differ[:10]}). "
                      f"{gcs.REGENERATE_HINT}.")

    def test_a_drift_failure_says_how_to_regenerate_and_what_moves_the_tables(self):
        """#2993: the failure itself says what to run and that the TTL moves
        the tables, for whoever edits the TTL without the /d4d-add-mapping
        playbook (which says the same since #3884)."""
        with tempfile.TemporaryDirectory() as d:
            stale = Path(d) / COMP.name
            stale.write_text(self._without_first_row(COMP.read_text(encoding="utf-8")),
                             encoding="utf-8")
            with self.assertRaises(AssertionError) as caught:
                self._assert_regenerates(
                    stale, self.comp_gen.render_sssom(gcs.committed_date(COMP)),
                    "subject_id")
        message = str(caught.exception)
        for needle in ("make gen-sssom-comprehensive gen-sssom-uri-comprehensive",
                       "commit them with the change", "SKOS alignment TTL",
                       "/d4d-add-mapping", "D4D_MISSING_URI_RECOMMENDATIONS.tsv"):
            self.assertIn(needle, message)

    def test_the_add_mapping_playbook_regenerates_and_names_nobody(self):
        """#2993, #3883, #3884: the /d4d-add-mapping playbook sends new
        mappings through the TTL and the comprehensive generator, runs the
        drift check, commits the tables with the TTL, writes no author and no
        row by hand, and points at no retired table."""
        text = (REPO / ".claude/commands/d4d-add-mapping.md").read_text(
            encoding="utf-8")
        for needle in ("make gen-sssom-comprehensive gen-sssom-uri-comprehensive",
                       "make check-sssom-comprehensive",
                       "d4d_rocrate_skos_alignment.ttl",
                       COMP.name, URI.name):
            self.assertIn(needle, text)
        self.assertNotIn("0000-0000-0000-0000", text)
        self.assertNotIn("orcid.org", text)
        self.assertNotIn("Skip regen", text)
        self.assertNotIn("make gen-sssom-all", text)
        for name in TestNoRowNamesAPerson.RETIRED:
            self.assertNotIn(f"semantic_exchange/{name}", text)

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
                self.assertIn(gcs.REGENERATE_HINT, out)
                self.assertEqual(stale.read_bytes(), before)

    def test_make_check_reports_both_tables_when_both_drift(self):
        """#2995: the make target ran the two checks as separate recipe
        lines, so a drift in the first stopped make before the second ran.
        Run through make itself, with the interpreter under test as
        ``python``, the fixture schema, TTL and recommendations as inputs,
        and both tables pointed at stale copies of the fixture's tables."""
        if shutil.which("make") is None:
            self.skipTest("make is not installed")
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            inputs = {"D4D_SCHEMA_ALL": d / "schema.yaml",
                      "SKOS_ALIGNMENT": d / "align.ttl",
                      "URI_RECOMMENDATIONS": d / "recs.tsv"}
            inputs["D4D_SCHEMA_ALL"].write_text(textwrap.dedent(FIXTURE_SCHEMA))
            inputs["SKOS_ALIGNMENT"].write_text(FIXTURE_TTL)
            inputs["URI_RECOMMENDATIONS"].write_text(FIXTURE_RECS)
            uri_gen = gcsu.ComprehensiveURISSSOMGenerator(
                inputs["D4D_SCHEMA_ALL"], inputs["SKOS_ALIGNMENT"],
                inputs["URI_RECOMMENDATIONS"])
            stale = {"SSSOM_COMPREHENSIVE": (d / "comp.tsv",
                                             uri_gen.comp_gen.render_sssom("2001-01-01")),
                     "SSSOM_URI_COMPREHENSIVE": (d / "uri.tsv",
                                                 uri_gen.render_sssom("2001-01-01"))}
            for path, text in stale.values():
                path.write_text(self._without_first_row(text), encoding="utf-8")
            env = dict(os.environ)
            env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent),
                                           env.get("PATH", "")])
            env["PYTHONPATH"] = os.pathsep.join(
                [str(REPO), str(REPO / "src"), env.get("PYTHONPATH", "")])
            result = subprocess.run(
                ["make", "--no-print-directory", "check-sssom-comprehensive",
                 "RUN=", "PROJECTS=unused"]
                + [f"{var}={path}" for var, path in inputs.items()]
                + [f"{var}={path}" for var, (path, _) in stale.items()],
                cwd=REPO, env=env, capture_output=True, text=True, timeout=600)
            output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, output)
            for var, (path, text) in stale.items():
                with self.subTest(table=var):
                    self.assertIn(f"✗ {path} does not regenerate", output)
                    self.assertIn("1 rows only in the regeneration", output)
                    self.assertEqual(path.read_text(encoding="utf-8"),
                                     self._without_first_row(text))

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
      own_uri_ttl:
        description: Declares a D4D slot_uri the TTL restates.
        slot_uri: d4d:ownUriTtl
      own_uri_scoped:
        description: Declares a D4D slot_uri a class-scoped triple restates.
        slot_uri: d4d:ownUriScoped
"""

FIXTURE_TTL = """\
@prefix d4d: <https://w3id.org/bridge2ai/data-sheets-schema/> .
@prefix schema: <https://schema.org/> .
@prefix rai: <http://mlcommons.org/croissant/RAI/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

d4d:ethical_notes skos:exactMatch rai:ethicalReview .
d4d:both_named skos:exactMatch schema:name .
d4d:own_uri_ttl skos:exactMatch d4d:ownUriTtl .
d4d:Dataset_own_uri_scoped skos:exactMatch d4d:ownUriScoped .
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

    def test_a_novel_row_is_a_status_and_claims_no_curation(self):
        """#2972: not ``d4d:retention_impacts skos:exactMatch
        d4d:retention_impacts`` at 1.0 under manual curation."""
        r = self.res["retention_impacts"]
        self.assertEqual(
            (r.status, r.source, r.predicate, r.object, r.confidence,
             r.justification),
            ("novel_d4d", "heuristic", "skos:exactMatch", "", 0.0,
             "semapv:UnspecifiedMatching"))
        row = next(x for x in self.gen.generate_comprehensive_sssom("2001-01-01")
                   if x["subject_id"] == "d4d:retention_impacts")
        self.assertEqual((row["object_id"], row["object_label"],
                          row["rocrate_json_path"], row["object_source"]),
                         ("sssom:NoTermFound", "", "", ""))

    def test_a_d4d_slot_uri_is_not_an_alignment(self):
        r = self.res["own_uri"]
        self.assertEqual(r.status, "unmapped")
        self.assertEqual(self.gen.declared_slot_uri("own_uri"), "d4d:ownUri")

    def test_a_d4d_target_is_not_an_alignment_whichever_input_names_it(self):
        """#3054: the same fact, a slot's only curated target being its own
        D4D slot_uri, resolves the same way whether the schema states it or
        the TTL restates it, slot-level or class-scoped. The TTL's triple
        stays listed."""
        for slot in ("own_uri", "own_uri_ttl", "own_uri_scoped"):
            with self.subTest(slot=slot):
                r = self.res[slot]
                self.assertEqual(
                    (r.status, r.source, r.predicate, r.object, r.confidence,
                     r.justification),
                    ("unmapped", "none", "skos:exactMatch", "", 0.0,
                     "semapv:UnspecifiedMatching"))
        self.assertEqual(self.res["own_uri"].others, [])
        self.assertEqual(self.res["own_uri_ttl"].others,
                         ["skos:exactMatch d4d:ownUriTtl (ttl)"])
        self.assertEqual(self.res["own_uri_scoped"].others,
                         ["skos:exactMatch d4d:ownUriScoped "
                          "(ttl d4d:Dataset_own_uri_scoped)"])
        for slot in ("own_uri_ttl", "own_uri_scoped"):
            with self.subTest(slot=slot):
                self.assertIn("TTL names only D4D terms, which are not alignments",
                              self.res[slot].notes)
        self.assertEqual(self.res["own_uri"].notes, [])

    def test_an_unlisted_disagreement_warns_and_the_ttl_still_wins(self):
        r = self.res["both_named"]
        self.assertEqual((r.object, r.disagreement), ("schema:name", "unlisted"))
        self.assertIn("skos:exactMatch dcterms:title (schema Dataset)", r.others)
        self.assertTrue(any("disagree on both_named" in w
                            for w in self.gen.warnings()))

    def _generator(self):
        """A fresh generator, so it resolves under whatever lists are patched."""
        d = Path(self._tmp.name)
        return gcs.ComprehensiveSSSOMGenerator(
            d / "schema.yaml", d / "align.ttl", d / "recs.tsv")

    def test_a_listing_holds_only_for_the_pairs_it_names(self):
        """#2991: a listing is matched on the slot and both sides' pairs.
        Here the TTL says exactMatch schema:name and the schema's slot_uri
        dcterms:title."""
        as_reviewed = gcs.Listed(("skos:exactMatch schema:name",),
                                 ("skos:exactMatch dcterms:title",),
                                 "fixture: reviewed for exactly these pairs")
        with mock.patch.dict(gcs.ACCEPTED_DISAGREEMENTS, {"both_named": as_reviewed}):
            gen = self._generator()
            self.assertEqual(gen.resolutions["both_named"].disagreement, "accepted")
            # The study's other listings are stale on the fixture; only
            # both_named is asked about.
            self.assertFalse([w for w in gen.warnings() if "both_named" in w])
        for side, listing in (
                ("schema", gcs.Listed(as_reviewed.ttl,
                                      ("skos:exactMatch dcterms:creator",),
                                      as_reviewed.reason)),
                ("ttl", gcs.Listed(("skos:closeMatch schema:name",),
                                   as_reviewed.schema, as_reviewed.reason))):
            for listing_name in ("ACCEPTED_DISAGREEMENTS", "OPEN_DISAGREEMENTS"):
                with self.subTest(changed_side=side, listed_in=listing_name), \
                        mock.patch.dict(getattr(gcs, listing_name),
                                        {"both_named": listing}):
                    gen = self._generator()
                    self.assertEqual(gen.resolutions["both_named"].disagreement,
                                     "changed")
                    report = gen.disagreement_report()
                    self.assertEqual(report["changed"], ["both_named"])
                    self.assertNotIn("both_named", report["stale"])
                    warnings = gen.warnings()
                    self.assertTrue(any("on both_named is not the listed one" in w
                                        for w in warnings))
                    self.assertFalse(any("unsettled" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
