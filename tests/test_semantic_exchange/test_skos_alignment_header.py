"""The SKOS alignment TTL's own statistics describe the triples it carries,
the class-level corrections of #3942 and #3926 hold, the pre-#149 class rows
are settled against the merged schemas (#3976), every slot-level twin of a
class correction carries its class's triple (#3971, #3995, #4002, #3974), and
no triple names an RAI term Croissant RAI 1.0 does not define.

Before #3942 the header said 189 triples (exact 112, close 59, related 10,
narrow 7, broad 1) while the file held 184 (111/58/9/6/0), and the per-section
and per-namespace counts were older still. Nothing checked them. The counts
here are taken from an rdflib parse, not from the generators' line pattern, and
the two parses are required to agree, so a triple written into a comment (which
the line pattern would read and a Turtle parser would not) fails.

Nothing here walks the corpus: the input is the TTL, plus the merged schemas
for the class names and declarations, and the repository's list of the
Croissant RAI 1.0 properties.
"""

import collections
import functools
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "src" / "semantic_exchange"
TTL = REPO / "src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl"
SCHEMAS = (REPO / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
           REPO / "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")
#: The repository's list of the 20 properties Croissant RAI 1.0 defines.
RAI_PROPERTIES = (REPO / "data/schema_comparison/schemas/croissant_rai/"
                  "croissant_rai_spec.md")
D4D = "https://w3id.org/bridge2ai/data-sheets-schema/"
SKOS = "http://www.w3.org/2004/02/skos/core#"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

#: The prefix each statistics line names, by its label.
NAMESPACE_LABELS = {
    "schema.org": "schema",
    "rai (Responsible AI)": "rai",
    "d4d (D4D-internal)": "d4d",
    "evi (FAIRSCAPE Evidence)": "evi",
    "dcat (Data Catalog Vocabulary)": "dcat",
    "rdf": "rdf",
}
PREDICATE_LABELS = {"Exact": "exactMatch", "Close": "closeMatch",
                    "Related": "relatedMatch", "Narrow": "narrowMatch",
                    "Broad": "broadMatch"}


def parsed_triples(path=TTL):
    """(subject local name, predicate local name, object CURIE) for every
    SKOS match triple on a D4D subject, by rdflib."""
    import rdflib
    g = rdflib.Graph()
    g.parse(path, format="turtle")
    namespaces = sorted(((p, str(ns)) for p, ns in g.namespaces()),
                        key=lambda x: -len(x[1]))

    def curie(iri):
        for prefix, ns in namespaces:
            if prefix and iri.startswith(ns):
                return f"{prefix}:{iri[len(ns):]}"
        return iri

    found = []
    for s, p, o in g:
        s, p, o = str(s), str(p), str(o)
        if s.startswith(D4D) and p.startswith(SKOS) and p.endswith("Match"):
            found.append((s[len(D4D):], p[len(SKOS):], curie(o)))
    return sorted(found)


def subject_kind(subject):
    """class, scoped (``<Class>_<slot>``) or slot, by the file's naming."""
    if subject[:1].isupper():
        return "scoped" if "_" in subject else "class"
    return "slot"


@functools.lru_cache(maxsize=None)
def raw_schema(path):
    """A merged schema as plain YAML, one parse per file for the module."""
    from data_sheets_schema.schema_cache import load_yaml
    return load_yaml(path) or {}


def raw_classes(path):
    return raw_schema(path).get("classes") or {}


def schema_classes():
    names = set()
    for path in SCHEMAS:
        names |= set(raw_classes(path))
    return names


def pairs_by_subject(triples):
    """{subject: {(predicate, object)}} for parsed triples."""
    found = collections.defaultdict(set)
    for subject, predicate, obj in triples:
        found[subject].add((predicate, obj))
    return found


def croissant_rai_properties():
    """``rai:<property>`` for each property the repository's Croissant RAI 1.0
    list names."""
    return set(re.findall(r"`(rai:\w+)`",
                          RAI_PROPERTIES.read_text(encoding="utf-8")))


def header_statistics(text):
    """The numbers the ``Alignment Statistics`` block states."""
    block = text[text.index("# Alignment Statistics"):]
    stats = {"total": int(re.search(r"# Total mappings: (\d+) SKOS triples",
                                    block).group(1))}
    for label, kind in (("Class-level", "class"),
                        (r"Class-scoped slot \(d4d:<Class>_<slot>\)", "scoped"),
                        ("Slot-level", "slot")):
        stats[kind] = int(re.search(rf"# - {label}: (\d+)", block).group(1))
    for label, predicate in PREDICATE_LABELS.items():
        m = re.search(rf"# - {label} matches: (\d+) \((\d+\.\d)%\)", block)
        stats[predicate] = (int(m.group(1)), m.group(2))
    for label, prefix in NAMESPACE_LABELS.items():
        stats["ns:" + prefix] = int(
            re.search(rf"# - {re.escape(label)}: (\d+)\n", block).group(1))
    return stats


def section_counts(text):
    """{section title: (stated count, triples under it)} for each section
    header carrying a count, up to the next such header or the statistics."""
    sections, current = {}, None
    for line in text.splitlines():
        m = re.match(r"# (.+) \((\d+) triples\)$", line)
        if m:
            current = m.group(1)
            sections[current] = [int(m.group(2)), 0]
        elif line.startswith("# Alignment Statistics"):
            current = None
        elif current and re.match(r"d4d:\w+\s+skos:\w+Match\s+\S+\s+\.", line):
            sections[current][1] += 1
    return {k: tuple(v) for k, v in sections.items()}


class TestHeaderMatchesTriples(unittest.TestCase):
    """#3942: the statistics block counts the triples the file carries."""

    @classmethod
    def setUpClass(cls):
        cls.text = TTL.read_text()
        cls.triples = parsed_triples()
        cls.stats = header_statistics(cls.text)

    def test_the_line_pattern_and_a_turtle_parse_read_the_same_triples(self):
        """The generators read the TTL with a line pattern; a triple in a
        comment would reach them and not a Turtle parser."""
        import generate_comprehensive_sssom as gcs
        by_pattern = sorted(gcs.ComprehensiveSSSOMGenerator._parse_skos(
            None, self.text))
        self.assertEqual(by_pattern, self.triples)

    def test_total(self):
        self.assertEqual(self.stats["total"], len(self.triples))

    def test_subject_kinds(self):
        kinds = collections.Counter(subject_kind(s) for s, _, _ in self.triples)
        for kind in ("class", "scoped", "slot"):
            with self.subTest(kind=kind):
                self.assertEqual(self.stats[kind], kinds[kind])

    def test_predicates_and_percentages(self):
        counts = collections.Counter(p for _, p, _ in self.triples)
        self.assertEqual(set(counts) - set(PREDICATE_LABELS.values()), set())
        for predicate in PREDICATE_LABELS.values():
            with self.subTest(predicate=predicate):
                n = counts[predicate]
                self.assertEqual(
                    self.stats[predicate],
                    (n, f"{100 * n / len(self.triples):.1f}"))

    def test_target_namespaces(self):
        counts = collections.Counter(o.split(":", 1)[0] for _, _, o in self.triples)
        self.assertEqual(set(counts) - set(NAMESPACE_LABELS.values()), set())
        for prefix in NAMESPACE_LABELS.values():
            with self.subTest(prefix=prefix):
                self.assertEqual(self.stats["ns:" + prefix], counts[prefix])

    def test_section_counts(self):
        sections = section_counts(self.text)
        self.assertTrue(sections)
        for title, (stated, found) in sections.items():
            with self.subTest(section=title):
                self.assertEqual(stated, found)


class TestClassLevelCorrections(unittest.TestCase):
    """#3942 and #3926."""

    @classmethod
    def setUpClass(cls):
        cls.triples = parsed_triples()
        cls.classes = {s: [(p, o) for s2, p, o in cls.triples if s2 == s]
                       for s, _, _ in cls.triples if subject_kind(s) == "class"}

    def test_every_class_subject_is_a_schema_class(self):
        self.assertEqual(set(self.classes) - schema_classes(), set())

    def test_no_class_is_aligned_to_a_d4d_term(self):
        """A D4D target is not an alignment to an external vocabulary (#3054)."""
        for cls, pairs in self.classes.items():
            for predicate, obj in pairs:
                with self.subTest(cls=cls):
                    self.assertFalse(obj.startswith("d4d:"), (predicate, obj))

    def test_class_level_schema_org_targets_are_schema_org_terms(self):
        from rdflib.namespace import SDO
        terms = set(SDO.__annotations__)
        for cls, pairs in self.classes.items():
            for _, obj in pairs:
                if obj.startswith("schema:"):
                    with self.subTest(cls=cls, obj=obj):
                        self.assertIn(obj.split(":", 1)[1], terms)

    def test_role_and_funding_wrappers_are_not_exact_matches(self):
        for cls, target in (("Creator", "schema:Person"),
                            ("Maintainer", "schema:Person"),
                            ("DataCollector", "schema:Person"),
                            ("FundingMechanism", "schema:Grant")):
            with self.subTest(cls=cls):
                self.assertNotIn(("exactMatch", target),
                                 self.classes.get(cls, []))

    def test_no_class_is_aligned_to_a_term_croissant_rai_does_not_define(self):
        """rai:prohibitedUses, rai:ethicalReview, rai:confidentialityLevel and
        rai:imputationProtocol are not Croissant RAI 1.0 properties."""
        undefined = {"rai:prohibitedUses", "rai:ethicalReview",
                     "rai:confidentialityLevel", "rai:imputationProtocol"}
        for cls, pairs in self.classes.items():
            for _, obj in pairs:
                with self.subTest(cls=cls):
                    self.assertNotIn(obj, undefined)

    def test_grantor_is_narrower_than_organization(self):
        self.assertEqual(self.classes["Grantor"],
                         [("broadMatch", "schema:Organization")])

    def test_distribution_date_is_a_release_date(self):
        """A distribution date is a release date: the class's release_dates
        attribute declares dcterms:available. The class said
        schema:dateCreated before #3942; the predicate and the namespace did
        not change, so no count above sees the object revert."""
        self.assertEqual(self.classes["DistributionDate"],
                         [("closeMatch", "schema:datePublished")])

    def test_imputation_slot_and_class_name_the_same_rai_term(self):
        """#3926: the slot said rai:imputationProtocol, which RAI does not
        define; the class, its schema exact_mappings and fairscape_models
        say rai:dataImputationProtocol."""
        slot = [(p, o) for s, p, o in self.triples if s == "imputation_protocols"]
        self.assertEqual(slot, [("exactMatch", "rai:dataImputationProtocol")])
        self.assertEqual(self.classes["ImputationProtocol"], slot)
        self.assertNotIn("rai:imputationProtocol",
                         {o for _, _, o in self.triples})


#: The class rows #3942 did not review (it covered the 70 class triples #149
#: added that the legacy table never carried), as #3976 settled them against
#: the merged schemas' class_uri, is_a and *_mappings.
PRE_149_CLASS_ROWS = {
    "Dataset": {("exactMatch", "schema:Dataset")},
    "DatasetCollection": {("closeMatch", "schema:Dataset"),
                          ("closeMatch", "dcat:Catalog")},
    "File": {("exactMatch", "schema:MediaObject"),
             ("closeMatch", "schema:DigitalDocument")},
    "FileCollection": {("exactMatch", "schema:Dataset"),
                       ("closeMatch", "dcat:Distribution")},
    "DataSubset": {("broadMatch", "schema:Dataset")},
    "CoreDataset": {("exactMatch", "schema:Dataset"),
                    ("closeMatch", "dcat:Dataset")},
    "CoreDatasetCollection": {("closeMatch", "schema:Dataset"),
                              ("exactMatch", "dcat:Catalog")},
    "CoreDistribution": {("exactMatch", "schema:DataDownload"),
                         ("closeMatch", "dcat:Distribution")},
}

#: Schema declarations the TTL's comments record as wrong or as contradicting
#: each other, left for a schema change (#3976): (merged schema, class,
#: metaslot, value). The rows above were settled with these in place.
RECORDED_SCHEMA_CONTRADICTIONS = (
    (SCHEMAS[0], "Dataset", "class_uri", "dcat:Distribution"),
    (SCHEMAS[0], "Dataset", "exact_mappings", "schema:DataDownload"),
    (SCHEMAS[0], "File", "class_uri", "schema:MediaObject"),
    (SCHEMAS[0], "File", "exact_mappings", "schema:DigitalDocument"),
    (SCHEMAS[1], "CoreDataset", "class_uri", "dcat:Dataset"),
    (SCHEMAS[1], "CoreDataset", "close_mappings", "dcat:Dataset"),
    (SCHEMAS[1], "CoreDistribution", "class_uri", "dcat:Distribution"),
    (SCHEMAS[1], "CoreDistribution", "close_mappings", "dcat:Distribution"),
)


def declared(definition, metaslot):
    """A class definition's values for a metaslot, as a list."""
    value = (definition or {}).get(metaslot)
    return [value] if isinstance(value, str) else list(value or [])


class TestPre149ClassRows(unittest.TestCase):
    """#3976: six classes said exactMatch schema:Dataset (Dataset,
    DatasetCollection, FileCollection, DataSubset, CoreDataset,
    CoreDatasetCollection), and the full schema's Dataset declares class_uri
    dcat:Distribution and exact_mappings schema:DataDownload. Each row is
    settled against what the merged schemas declare; where a schema looks
    wrong it is left alone and its declaration recorded."""

    @classmethod
    def setUpClass(cls):
        cls.triples = parsed_triples()
        cls.pairs = pairs_by_subject(cls.triples)
        cls.schemas = {path: raw_classes(path) for path in SCHEMAS}

    def test_each_row_as_settled(self):
        for cls, pairs in PRE_149_CLASS_ROWS.items():
            with self.subTest(cls=cls):
                self.assertEqual(self.pairs[cls], pairs)

    def test_an_exact_match_to_schema_dataset_is_one_a_schema_declares(self):
        """Six exact matches to one term made all six classes one concept
        (SKOS exactMatch is transitive). Besides Dataset, whose own
        declaration is the one recorded as wrong, a class is exact to
        schema:Dataset only where its schema's exact_mappings say so."""
        by_schema = {c for classes in self.schemas.values()
                     for c, d in classes.items()
                     if "schema:Dataset" in declared(d, "exact_mappings")}
        exact = {s for s, p, o in self.triples if subject_kind(s) == "class"
                 and (p, o) == ("exactMatch", "schema:Dataset")}
        self.assertEqual(by_schema, {"FileCollection", "CoreDataset"})
        self.assertEqual(exact, by_schema | {"Dataset"})

    def test_a_subclass_is_broader_matched_to_its_parents_exact_target(self):
        """DataSubset is_a Dataset, so the term Dataset matches exactly is
        broader than DataSubset, as schema:Organization is for Grantor."""
        full = self.schemas[SCHEMAS[0]]
        self.assertEqual(full["DataSubset"]["is_a"], "Dataset")
        parent = {o for p, o in self.pairs["Dataset"] if p == "exactMatch"}
        self.assertTrue(parent)
        self.assertEqual(self.pairs["DataSubset"],
                         {("broadMatch", o) for o in parent})

    def test_a_class_uri_that_is_also_an_exact_mapping_is_exact(self):
        """Where a schema gives one target as both a class's class_uri and
        its exact_mappings, the TTL's triple on that target is exactMatch.
        CoreDatasetCollection (dcat:Catalog) said closeMatch until #3976."""
        checked = set()
        for classes in self.schemas.values():
            for cls, definition in classes.items():
                for uri in declared(definition, "class_uri"):
                    if uri not in declared(definition, "exact_mappings"):
                        continue
                    for predicate, obj in self.pairs.get(cls, ()):
                        if obj == uri:
                            checked.add(cls)
                            with self.subTest(cls=cls, target=uri):
                                self.assertEqual(predicate, "exactMatch")
        self.assertIn("CoreDatasetCollection", checked)

    def test_each_recorded_schema_contradiction_is_still_declared(self):
        """The TTL keeps Dataset exactMatch schema:Dataset against the full
        schema's Dataset declarations, keeps File's DigitalDocument close
        beside its class_uri, and follows close_mappings where a core class
        names the same target as its class_uri. A schema change that removes
        one of these declarations settles it; then the TTL comment recording
        it, the row it qualifies and this list are updated together."""
        for path, cls, metaslot, value in RECORDED_SCHEMA_CONTRADICTIONS:
            with self.subTest(cls=cls, metaslot=metaslot, value=value):
                self.assertIn(value,
                              declared(self.schemas[path][cls], metaslot))


#: Slot-level twins of a class correction left as found, with the triple
#: each still carries. While a twin still carries that triple, the comment
#: block directly above it says TODO(#3942); a twin settled later drops out
#: of the check. #3942 left eleven marked (#3971, #3995, #4002) and two
#: unmarked (labeling_strategies, raw_sources); #3971 settled all thirteen
#: (SETTLED_TWINS below), so no TODO(#3942) is left in the TTL.
SLOT_TWINS_LEFT_AS_FOUND = {}


def todo_above(lines, index, twins):
    """Whether the comment block directly above ``lines[index]`` carries
    TODO(#3942). ``twins`` maps slot to (predicate, object); a twin line
    directly above that carries the same target is skipped, so one comment
    covers adjacent twins of one term (discouraged_uses and prohibited_uses)
    and no other twin's comment does."""
    target = lines[index].split()[2]
    same = [s for s, (_, obj) in twins.items() if obj == target]
    i = index - 1
    while i >= 0 and any(lines[i].startswith(f"d4d:{s} ") for s in same):
        i -= 1
    block = []
    while i >= 0 and lines[i].startswith("#"):
        block.append(lines[i])
        i -= 1
    return any("TODO(#3942)" in line for line in block)


class TestSlotLevelTwinsAreMarked(unittest.TestCase):
    """#4000: the PR and #3971 say every slot-level twin left as found is
    marked TODO in the TTL; three were not."""

    def test_each_twin_left_as_found_carries_a_todo(self):
        lines = TTL.read_text().splitlines()
        triples = set(parsed_triples())
        for slot, (predicate, obj) in SLOT_TWINS_LEFT_AS_FOUND.items():
            if (slot, predicate, obj) not in triples:
                continue
            line = f"d4d:{slot} skos:{predicate} {obj} ."
            with self.subTest(slot=slot):
                self.assertIn(line, lines)
                self.assertTrue(
                    todo_above(lines, lines.index(line), SLOT_TWINS_LEFT_AS_FOUND),
                    f"{slot}: no TODO(#3942) directly above {line!r}")

    def test_every_todo_marks_a_twin_left_as_found(self):
        """The other direction (#3971): a TODO(#3942) sits directly above a
        twin the list still names, so a settled twin's TODO is removed with
        it. With every twin settled, none is left."""
        lines = TTL.read_text().splitlines()
        marked = {lines.index(f"d4d:{slot} skos:{predicate} {obj} .")
                  for slot, (predicate, obj) in SLOT_TWINS_LEFT_AS_FOUND.items()
                  if f"d4d:{slot} skos:{predicate} {obj} ." in lines}
        for i, line in enumerate(lines):
            if "TODO(#3942)" not in line:
                continue
            j = i
            while j < len(lines) and lines[j].startswith("#"):
                j += 1
            with self.subTest(line=i + 1):
                self.assertIn(j, marked, f"a TODO(#3942) above no twin left "
                                         f"as found: {line!r}")

    def test_the_check_reads_a_missing_todo(self):
        twins = {"a": ("exactMatch", "x:y"), "b": ("exactMatch", "x:y"),
                 "c": ("exactMatch", "x:z")}
        lines = ["# an ordinary comment", "d4d:a skos:exactMatch x:y ."]
        self.assertFalse(todo_above(lines, 1, twins))
        # One comment covers adjacent twins of one term ...
        lines = ["# TODO(#3942): x", "d4d:a skos:exactMatch x:y .",
                 "d4d:b skos:exactMatch x:y ."]
        self.assertTrue(todo_above(lines, 2, twins))
        # ... and not a twin of another term below them.
        lines = ["# TODO(#3942): x", "d4d:a skos:exactMatch x:y .",
                 "d4d:c skos:exactMatch x:z ."]
        self.assertFalse(todo_above(lines, 2, twins))


#: The slot-level twins #3942 left as found, and sampling_strategies (#3974),
#: as #3971, #3995, #4002 and #3974 settled them: the class the slot holds
#: (its range), and the pairs the slot and that class both carry. A twin
#: follows its class unless the slot's semantics differ; none of these do.
#: An empty set is a removed triple: its target is not a term its vocabulary
#: defines (rai:prohibitedUses, rai:ethicalReview, rai:confidentialityLevel,
#: evi:samplingPlan) or names another notion (schema:license for an
#: extension mechanism). labeling_strategies and raw_sources are twins of
#: #3942's LabelingStrategy and RawData corrections that no TODO marked.
SETTLED_TWINS = {
    "discouraged_uses": ("DiscouragedUse", set()),
    "prohibited_uses": ("ProhibitedUse", set()),
    "ethical_reviews": ("EthicalReview", set()),
    "is_deidentified": ("Deidentification", set()),
    "extension_mechanism": ("ExtensionMechanism", set()),
    "sampling_strategies": ("SamplingStrategy", set()),
    "distribution_dates": ("DistributionDate",
                           {("closeMatch", "schema:datePublished")}),
    "retention_limit": ("RetentionLimits",
                        {("relatedMatch", "schema:conditionsOfAccess")}),
    "confidential_elements": ("Confidentiality",
                              {("relatedMatch", "rai:personalSensitiveInformation")}),
    "sensitive_elements": ("SensitiveElement",
                           {("exactMatch", "rai:personalSensitiveInformation")}),
    "existing_uses": ("ExistingUse", {("closeMatch", "rai:dataUseCases")}),
    "data_protection_impacts": ("DataProtectionImpact",
                                {("broadMatch", "rai:dataSocialImpact")}),
    "labeling_strategies": ("LabelingStrategy",
                            {("narrowMatch", "rai:dataAnnotationProtocol")}),
    "raw_sources": ("RawData", {("closeMatch", "rai:dataCollectionRawData")}),
}


class TestSlotTwinsFollowTheirClasses(unittest.TestCase):
    """#3971, #3995, #4002, #3974: until these, the class level and the slot
    level disagreed for each twin (exactMatch on the slot where the class
    said related, broad or close, or a triple on a term whose class triple
    #3942 removed)."""

    @classmethod
    def setUpClass(cls):
        cls.pairs = pairs_by_subject(parsed_triples())

    def test_each_twin_is_the_slot_that_holds_its_class(self):
        """Read from the full schema: every declaration of the slot name that
        sets a range (top-level, attribute or slot_usage) ranges over the
        class, so the slot's value is that class's object."""
        schema = raw_schema(SCHEMAS[0])
        for slot, (cls, _) in SETTLED_TWINS.items():
            definitions = [(schema.get("slots") or {}).get(slot)]
            for cdef in (schema.get("classes") or {}).values():
                for group in ("attributes", "slot_usage"):
                    definitions.append(((cdef or {}).get(group) or {}).get(slot))
            ranges = {d["range"] for d in definitions if d and d.get("range")}
            with self.subTest(slot=slot):
                self.assertEqual(ranges, {cls})

    def test_a_twin_and_its_class_carry_the_settled_pairs(self):
        for slot, (cls, pairs) in SETTLED_TWINS.items():
            with self.subTest(slot=slot):
                self.assertEqual(self.pairs.get(slot, set()), pairs)
            with self.subTest(cls=cls):
                self.assertEqual(self.pairs.get(cls, set()), pairs)


class TestNoTripleNamesAnUndefinedTerm(unittest.TestCase):
    """#3942 removed the class triples on RAI terms Croissant RAI 1.0 does not
    define; #3971 and #3974 removed their slot twins."""

    @classmethod
    def setUpClass(cls):
        cls.triples = parsed_triples()

    def test_every_rai_target_is_a_croissant_rai_1_0_property(self):
        """Every subject, class, class-scoped or slot. The 20 properties are
        read from the repository's list (the published specification,
        https://docs.mlcommons.org/croissant/docs/croissant-rai-spec.html,
        names the same and none of prohibitedUses, ethicalReview or
        confidentialityLevel; checked 2026-09-30)."""
        properties = croissant_rai_properties()
        self.assertEqual(len(properties), 20)
        for subject, predicate, obj in self.triples:
            if obj.startswith("rai:"):
                with self.subTest(subject=subject, obj=obj):
                    self.assertIn(obj, properties)

    def test_no_triple_names_evi_sampling_plan(self):
        """#3974: EVI 1.6, the version https://w3id.org/EVI resolves to, has
        79 terms and no samplingPlan in its Turtle, RDF/XML or JSON-LD form
        or on its documentation page (checked 2026-09-30); the repository
        holds no copy of EVI to test against."""
        self.assertNotIn("evi:samplingPlan", {o for _, _, o in self.triples})


if __name__ == "__main__":
    unittest.main()
