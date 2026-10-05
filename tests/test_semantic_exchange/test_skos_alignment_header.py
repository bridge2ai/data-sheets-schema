"""The SKOS alignment TTL's own statistics describe the triples it carries,
the class-level corrections of #3942 and #3926 hold, the 14 class rows #3942
did not review are settled against the merged schemas (#3976), a slot that
holds a class #3942, #3974 or #3976 changed carries that class's targets
only as the class now carries them, whether a triple's subject is the slot
(``d4d:<slot>``) or the slot in a class (``d4d:<Class>_<slot>``) (#3971,
#3995, #4002, #3974, #4052, #4078), a slot that holds any class with a
class-level triple carries each of that class's targets with the class's
predicate unless a listed exception gives a reason (#4036), no triple names
an RAI term Croissant RAI 1.0 does not define, and every EVI term a triple
names is recorded with the outcome of a check against EVI.

Before #3942 the header said 189 triples (exact 112, close 59, related 10,
narrow 7, broad 1) while the file held 184 (111/58/9/6/0), and the per-section
and per-namespace counts were older still. Nothing checked them. The counts
here are taken from an rdflib parse, not from the generators' line pattern, and
the two parses are required to agree, so a triple written into a comment (which
the line pattern would read and a Turtle parser would not) fails.

Nothing here walks the corpus: the input is the TTL, plus the merged schemas
for the class and slot names, declarations and slot ranges, and the
repository's list of the Croissant RAI 1.0 properties.
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


#: The 14 class rows #3942 did not review, as #3976 settled them against the
#: merged schemas' class_uri, is_a and *_mappings. #3942 covered the 70 class
#: triples #149 added that the legacy SSSOM table never carried; these 14 are
#: the class rows that table did carry (#3884 retired it). Not all predate
#: #149: Dataset's row came with #129, and DatasetCollection's, File's and
#: FileCollection's with #147, but #149 (e141852f5) added the other seven,
#: DataSubset's and those of the three Core* classes, and transcribed them
#: into the table.
CLASS_ROWS_3942_DID_NOT_REVIEW = {
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


class TestClassRows3942DidNotReview(unittest.TestCase):
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
        for cls, pairs in CLASS_ROWS_3942_DID_NOT_REVIEW.items():
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
#: of the check. #3942 left eleven marked (#3971, #3995, #4002) and nine
#: unmarked: labeling_strategies, raw_sources and the seven twins of its
#: d4d: class removals, which review round 1 of #4031 found (#4052). All
#: twenty are settled (#4031), so no TODO(#3942) is left in
#: the TTL, and the derived check below
#: (test_a_slot_that_holds_a_changed_class_follows_it) reads every slot that
#: holds a changed class in either merged schema, listed or not, under its
#: own name and under every class-scoped name (#4078).
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


#: The class-level pairs #3942 removed or replaced (5463875a9), by class: the
#: pairs each class carried before that commit and not after it, read from
#: an rdflib parse of the TTL on either side. Its message counts "Removed
#: (20)" and "Corrected (14)". History, so a pinned record; the slots that
#: hold each class are read from the schemas, never listed.
CLASS_PAIRS_3942_REPLACED = {
    # Removed: the class carries no triple now.
    "Creator": {("exactMatch", "schema:Person")},
    "Maintainer": {("exactMatch", "schema:Person")},
    "DataCollector": {("exactMatch", "schema:Person")},
    "FundingMechanism": {("exactMatch", "schema:Grant")},
    "HumanSubjectResearch": {("exactMatch", "d4d:humanSubject")},
    "InformedConsent": {("exactMatch", "d4d:informedConsent")},
    "AtRiskPopulations": {("exactMatch", "d4d:atRiskPopulations")},
    "ContentWarning": {("exactMatch", "d4d:contentWarning")},
    "AddressingGap": {("exactMatch", "d4d:addressingGaps")},
    "DataAnomaly": {("exactMatch", "d4d:dataAnomalies")},
    "HumanSubjectCompensation": {("exactMatch", "d4d:participantCompensation")},
    "Deidentification": {("closeMatch", "rai:confidentialityLevel")},
    "ExtensionMechanism": {("closeMatch", "schema:license")},
    "Relationships": {("closeMatch", "schema:isRelatedTo")},
    "CollectionConsent": {("closeMatch", "rai:personalSensitiveInformation")},
    "CollectionNotification": {("closeMatch", "rai:personalSensitiveInformation")},
    "ConsentRevocation": {("closeMatch", "rai:personalSensitiveInformation")},
    "DiscouragedUse": {("exactMatch", "rai:prohibitedUses")},
    "ProhibitedUse": {("exactMatch", "rai:prohibitedUses")},
    "EthicalReview": {("exactMatch", "rai:ethicalReview")},
    # Corrected: the class carries a replacement now.
    "Grantor": {("exactMatch", "schema:Organization")},
    "DataProtectionImpact": {("exactMatch", "rai:dataSocialImpact")},
    "LabelingStrategy": {("exactMatch", "rai:dataAnnotationProtocol")},
    "Instance": {("closeMatch", "schema:variableMeasured")},
    "Subpopulation": {("closeMatch", "schema:variableMeasured")},
    "VersionAccess": {("closeMatch", "schema:version")},
    "Confidentiality": {("closeMatch", "rai:personalSensitiveInformation")},
    "RetentionLimits": {("closeMatch", "schema:conditionsOfAccess")},
    "UseRepository": {("closeMatch", "schema:relatedLink")},
    "Splits": {("closeMatch", "schema:hasPart")},
    "RawData": {("exactMatch", "rai:dataCollectionRawData")},
    "ExistingUse": {("exactMatch", "rai:dataUseCases")},
    "SensitiveElement": {("closeMatch", "rai:personalSensitiveInformation")},
    "DistributionDate": {("closeMatch", "schema:dateCreated")},
}

#: The same record for the class-level changes made since: #3974
#: (SamplingStrategy) and #3976 (DataSubset, DatasetCollection,
#: CoreDatasetCollection).
CLASS_PAIRS_REPLACED_SINCE_3942 = {
    "SamplingStrategy": {("exactMatch", "evi:samplingPlan")},
    "DataSubset": {("exactMatch", "schema:Dataset")},
    "DatasetCollection": {("exactMatch", "schema:Dataset")},
    "CoreDatasetCollection": {("exactMatch", "schema:Dataset"),
                              ("closeMatch", "dcat:Catalog")},
}


def slots_holding(classes, schemas=SCHEMAS):
    """{class: {slot}}: every slot name a declaration of which, in one of
    ``schemas`` (both merged schemas unless given; top-level, class
    attribute or slot_usage), ranges over one of ``classes``, directly or
    through any_of / exactly_one_of."""
    found = collections.defaultdict(set)

    def ranges(definition):
        out = {(definition or {}).get("range")}
        for group in ("any_of", "exactly_one_of"):
            out |= {(alt or {}).get("range")
                    for alt in (definition or {}).get(group) or []}
        return out - {None}

    for path in schemas:
        schema = raw_schema(path)
        declarations = list((schema.get("slots") or {}).items())
        for cdef in (schema.get("classes") or {}).values():
            for group in ("attributes", "slot_usage"):
                declarations += list(((cdef or {}).get(group) or {}).items())
        for slot, definition in declarations:
            for cls in ranges(definition) & set(classes):
                found[cls].add(slot)
    return found


def schema_slot_names():
    """Every slot name either merged schema declares: top-level, in a
    class's ``slots:`` list, attributes or slot_usage."""
    names = set()
    for path in SCHEMAS:
        schema = raw_schema(path)
        names |= set(schema.get("slots") or {})
        for cdef in (schema.get("classes") or {}).values():
            names |= set((cdef or {}).get("slots") or [])
            for group in ("attributes", "slot_usage"):
                names |= set((cdef or {}).get(group) or {})
    return names


def pairs_on_slot(pairs, slot, classes):
    """What the TTL says for ``slot``: the pairs of its slot-level subject,
    ``d4d:<slot>``, and of every class-scoped one, ``d4d:<Class>_<slot>``,
    whose ``<Class>`` is one of ``classes``. The comprehensive generator
    takes a class-scoped triple as the TTL's word on the slot (#3053), and
    the /d4d-add-mapping playbook writes a class's own slots in that form.
    The generator reads one only for a class that carries the slot; this
    reads it for any of ``classes``, so no class-scoped triple on the slot's
    name is left out (#4078)."""
    found = set(pairs.get(slot, ()))
    for subject, subject_pairs in pairs.items():
        if (subject.endswith("_" + slot)
                and subject[:-len(slot) - 1] in classes):
            found |= subject_pairs
    return found


def slots_not_following(pairs, changed, holders, classes):
    """{(class, slot): pairs}: for each slot that holds a changed class, the
    pairs it carries in either form (pairs_on_slot) on one of that class's
    targets, former or current, that the class does not carry now. Empty
    when every holder follows its class."""
    found = {}
    for cls, lost in changed.items():
        now = pairs.get(cls, set())
        targets = {o for _, o in lost | now}
        for slot in holders.get(cls, ()):
            extra = {(p, o) for p, o in pairs_on_slot(pairs, slot, classes)
                     if o in targets} - now
            if extra:
                found[(cls, slot)] = extra
    return found


class TestSlotTwinsFollowTheirClasses(unittest.TestCase):
    """#3971, #3995, #4002, #3974, #4052, #4078. Until these changes each of
    the 21 twins #4031 settled disagreed with its class, in the TTL at
    8a19955b5, the main commit #4031 branched from:

    - twelve carried a triple on a term whose class triple #3942 removed:
      discouraged_uses, prohibited_uses, ethical_reviews, is_deidentified,
      extension_mechanism, and the seven on d4d: terms;
    - eight carried a triple on a term whose class triple #3942 corrected,
      and differed from the class's replacement: raw_sources,
      existing_uses, data_protection_impacts and confidential_elements said
      exactMatch where their classes said close, close, broad and related;
      distribution_dates said exactMatch schema:dateCreated where its class
      said closeMatch schema:datePublished; sensitive_elements said close
      where its class said exact, labeling_strategies close where its class
      said narrow, and retention_limit narrow where its class said related;
    - sampling_strategies said relatedMatch evi:samplingPlan where
      SamplingStrategy said exactMatch. #3942 did not change that class;
      #3974 removed both triples, since EVI defines no samplingPlan.

    #4031 checked them against a list of the 21 and their settled pairs
    (SETTLED_TWINS). Because it was a list, the seven twins of #3942's d4d:
    class removals, which it did not name until #4052, kept the removed
    triple with every test passing. The derived check reads every slot that
    holds a changed class in either merged schema, under its own name and
    under every class-scoped name, ``d4d:<Class>_<slot>``, the form the
    /d4d-add-mapping playbook writes for a class's slots (#4078). #4036
    removed the list: TestASlotAgreesWithTheClassItHolds holds every slot
    that holds a class with a class-level triple, changed or not, to the
    class's strength on each target the class carries.
    """

    @classmethod
    def setUpClass(cls):
        cls.pairs = pairs_by_subject(parsed_triples())
        cls.classes = schema_classes()
        cls.changed = {**CLASS_PAIRS_3942_REPLACED,
                       **CLASS_PAIRS_REPLACED_SINCE_3942}
        # Every class's holders, read from both merged schemas
        # (test_the_holders_are_read_from_both_merged_schemas); the check
        # reads the changed classes' among them.
        cls.every = slots_holding(cls.classes)
        cls.holders = {c: cls.every[c] for c in cls.changed if c in cls.every}

    def test_the_record_holds_3942s_count_and_no_class_kept_a_lost_pair(self):
        """CLASS_PAIRS_3942_REPLACED is complete by #3942's own count: of
        its classes, twenty carry no triple now and fourteen a replacement.
        No class in either record carries a pair it lost."""
        removed = [c for c in CLASS_PAIRS_3942_REPLACED if not self.pairs.get(c)]
        self.assertEqual(
            (len(removed), len(CLASS_PAIRS_3942_REPLACED) - len(removed)),
            (20, 14))
        for cls, lost in self.changed.items():
            with self.subTest(cls=cls):
                self.assertFalse(lost & self.pairs.get(cls, set()))

    def test_a_slot_that_holds_a_changed_class_follows_it(self):
        """Derived, not listed: a slot that holds a changed class (a
        declaration of it, in either merged schema, ranges over the class)
        carries a triple on one of that class's targets, former or current,
        only as the class now carries it, whether the triple's subject is
        the slot (``d4d:<slot>``) or the slot in a class
        (``d4d:<Class>_<slot>``). So a class triple that was removed and
        left on such a slot fails in either form, and so does a correction
        the slot did not follow. A slot that never shared a target with its
        class is not constrained: creators holds Creator and says closeMatch
        schema:author, a property, where Creator lost exactMatch
        schema:Person, a type."""
        self.assertEqual(slots_not_following(self.pairs, self.changed,
                                             self.holders, self.classes), {})
        # Not vacuous: the check reads holders for 35 of the 38 changed
        # classes. No slot of either merged schema holds the other three:
        # DatasetCollection and CoreDatasetCollection are tree roots, and
        # FundingMechanism.grantor has range string, not Grantor.
        self.assertEqual(set(self.changed) - set(self.holders),
                         {"CoreDatasetCollection", "DatasetCollection",
                          "Grantor"})

    def test_the_check_reads_a_triple_in_either_form(self):
        """#4078: each triple below, added to the TTL's own, is reported,
        whether its subject is the slot or the slot in a class, and it is
        all that is added to what the TTL alone reports. CollectionConsent's
        closeMatch rai:personalSensitiveInformation is the class triple
        #3942 removed, here on collection_consents, which no list names;
        exactMatch on confidential_elements is the contradiction #3995
        settled, on a listed twin. CoreDataset is a class only the core
        schema defines."""
        def check(pairs):
            return slots_not_following(pairs, self.changed, self.holders,
                                       self.classes)

        alone = check(self.pairs)
        psi = "rai:personalSensitiveInformation"
        for subject, cls, slot, pair in (
                ("collection_consents", "CollectionConsent",
                 "collection_consents", ("closeMatch", psi)),
                ("Dataset_collection_consents", "CollectionConsent",
                 "collection_consents", ("closeMatch", psi)),
                ("confidential_elements", "Confidentiality",
                 "confidential_elements", ("exactMatch", psi)),
                ("Dataset_confidential_elements", "Confidentiality",
                 "confidential_elements", ("exactMatch", psi)),
                ("CoreDataset_confidential_elements", "Confidentiality",
                 "confidential_elements", ("exactMatch", psi))):
            pairs = {s: set(p) for s, p in self.pairs.items()}
            pairs.setdefault(subject, set()).add(pair)
            added = {key: extra - alone.get(key, set())
                     for key, extra in check(pairs).items()}
            with self.subTest(subject=subject):
                self.assertEqual({k: v for k, v in added.items() if v},
                                 {(cls, slot): {pair}})

    def test_every_subject_but_a_class_is_read_for_a_schema_slot(self):
        """The reading is complete: every slot-level subject is a slot name
        of either merged schema, and every class-scoped one is
        ``<Class>_<slot>`` for a class and a slot name of either merged
        schema, which pairs_on_slot reads for that slot. A misspelled class
        or slot would be read for no slot, so a triple on it would escape
        the derived check; it fails here instead."""
        slots = schema_slot_names()
        probe = {("probe", "probe")}
        for subject in self.pairs:
            if subject_kind(subject) == "class":
                continue
            with self.subTest(subject=subject):
                self.assertTrue(
                    {s for s in slots
                     if pairs_on_slot({subject: probe}, s, self.classes)},
                    f"d4d:{subject} is read for no slot of either merged "
                    "schema")

    def test_the_holders_are_read_from_both_merged_schemas(self):
        """The holders the check reads are those of the full and the core
        schema together (#4078), and each schema declares holders the other
        does not: only the core schema's distributions holds
        CoreDistribution, and only the full schema's participant_compensation
        holds HumanSubjectCompensation. When this was written the core
        schema added no holder of a changed class that the full schema
        lacks, so a check over the changed classes alone could not see the
        core schema dropped; this one is made over every class."""
        def flat(found):
            return {(c, s) for c, slots in found.items() for s in slots}

        alone = {path: flat(slots_holding(self.classes, (path,)))
                 for path in SCHEMAS}
        self.assertEqual(flat(self.every),
                         alone[SCHEMAS[0]] | alone[SCHEMAS[1]])
        for path, other, own in (
                (SCHEMAS[0], SCHEMAS[1],
                 ("HumanSubjectCompensation", "participant_compensation")),
                (SCHEMAS[1], SCHEMAS[0], ("CoreDistribution", "distributions"))):
            with self.subTest(schema=path.name):
                self.assertIn(own, alone[path] - alone[other])


#: One disagreement the strength rule allows, as it was reviewed: the class
#: the slot holds, the target, the predicates the slot carries on it
#: (slot-level and class-scoped together, pairs_on_slot), the predicates the
#: class carries on it, and why the disagreement stands.
StrengthException = collections.namedtuple(
    "StrengthException",
    "cls target slot_predicates class_predicates reason")

#: The disagreements TestASlotAgreesWithTheClassItHolds allows, by slot
#: (#4036). A listing holds only while the TTL and the merged schemas give
#: exactly the disagreement it names, as a listing in
#: generate_comprehensive_sssom.py's ACCEPTED_DISAGREEMENTS holds only for
#: the pairs it names (#2991). One that gives no reason, names a slot neither
#: merged schema declares, or no longer disagrees fails the rule, and so does
#: one whose predicates have changed.
STRENGTH_EXCEPTIONS = {
    "distribution_formats": StrengthException(
        "DistributionFormat", "evi:formats", ("exactMatch",), ("closeMatch",),
        "EVI 1.6 defines no formats term (EVI_TARGETS_CHECKED), so no "
        "definition settles either strength. #4037 decides every triple on "
        "evi:formats, this slot's and its class's among them."),
}


def strength_disagreements(pairs, holders, classes):
    """{(slot, class, target): (slot predicates, class predicates)}: for each
    class in ``holders`` and each slot that holds it, every target the class
    carries on which the slot, slot-level and class-scoped together
    (pairs_on_slot), carries other predicates than the class. Only a target
    both carry is compared: the rule is about the strength of one
    alignment, and a slot that carries another target, or none, says
    nothing about this one."""
    found = {}
    for cls, slots in holders.items():
        held = collections.defaultdict(set)
        for predicate, obj in pairs.get(cls, ()):
            held[obj].add(predicate)
        for slot in slots:
            carried = collections.defaultdict(set)
            for predicate, obj in pairs_on_slot(pairs, slot, classes):
                if obj in held:
                    carried[obj].add(predicate)
            for obj, predicates in carried.items():
                if predicates != held[obj]:
                    found[(slot, cls, obj)] = (tuple(sorted(predicates)),
                                              tuple(sorted(held[obj])))
    return found


def strength_problems(found, exceptions, slot_names):
    """[(slot, problem)]: each disagreement in ``found`` that no listing in
    ``exceptions`` names, or names with other predicates; and each listing
    whose reason has 20 characters or fewer (a listing in the generator
    must give more, test_the_lists_are_disjoint_and_give_reasons), that
    names a slot not in ``slot_names`` (every slot name of either merged
    schema), or that names a disagreement ``found`` does not hold. Empty
    when the rule holds."""
    problems = []
    for (slot, cls, obj), (carried, held) in sorted(found.items()):
        listing = exceptions.get(slot)
        said = f"{'/'.join(carried)} {obj} where {cls} carries {'/'.join(held)}"
        if listing is None or (listing.cls, listing.target) != (cls, obj):
            problems.append((slot, "unlisted: " + said))
        elif (tuple(listing.slot_predicates),
              tuple(listing.class_predicates)) != (carried, held):
            problems.append((slot, "not the listed disagreement: " + said))
    for slot, listing in sorted(exceptions.items()):
        if len((listing.reason or "").strip()) <= 20:
            problems.append((slot, "listed without a reason"))
        if slot not in slot_names:
            problems.append((slot, "stale: neither merged schema declares it"))
        elif (slot, listing.cls, listing.target) not in found:
            problems.append((slot, f"stale: no disagreement with {listing.cls} "
                                   f"on {listing.target}"))
    return problems


class TestASlotAgreesWithTheClassItHolds(unittest.TestCase):
    """#4036: a slot whose range is a class with a class-level triple carries
    each target that class carries with the class's predicate, whether its
    subject is the slot (``d4d:<slot>``) or the slot in a class
    (``d4d:<Class>_<slot>``), unless STRENGTH_EXCEPTIONS lists the
    disagreement with a reason. The slot holds the class's objects, so a
    slot and its class that align one target at different strengths say
    two things about one value.

    Until #4036 ten slots disagreed with their classes and every test
    passed. The checks were a list of the 21 twins #4031 settled
    (SETTLED_TWINS) and the derived check above, which reads only the
    classes #3942, #3974 and #3976 changed; none of the ten classes is one
    of those. Nine slots follow their classes now. The tenth,
    distribution_formats, is listed until #4037 decides evi:formats.
    """

    @classmethod
    def setUpClass(cls):
        cls.pairs = pairs_by_subject(parsed_triples())
        cls.classes = schema_classes()
        cls.aligned = {s for s in cls.pairs if subject_kind(s) == "class"}
        cls.holders = slots_holding(cls.aligned)
        cls.slot_names = schema_slot_names()

    def problems(self, pairs=None, exceptions=STRENGTH_EXCEPTIONS,
                 holders=None, slot_names=None):
        """What the rule reports, on the TTL and the merged schemas unless
        given others."""
        found = strength_disagreements(
            self.pairs if pairs is None else pairs,
            self.holders if holders is None else holders, self.classes)
        return strength_problems(
            found, exceptions,
            self.slot_names if slot_names is None else slot_names)

    def changed(self, subject, add, drop=None):
        """The TTL's pairs, with ``add`` added to ``subject`` and ``drop``
        removed from it."""
        pairs = {s: set(p) for s, p in self.pairs.items()}
        pairs.setdefault(subject, set()).add(add)
        pairs[subject].discard(drop)
        return pairs

    def test_every_slot_agrees_with_the_class_it_holds_or_is_listed(self):
        self.assertEqual(self.problems(), [])

    def test_the_rule_reads_the_holders_of_every_aligned_class(self):
        """Not vacuous: every class with a class-level triple has a holder
        the rule reads, but the three no slot of either merged schema holds
        (see test_a_slot_that_holds_a_changed_class_follows_it). The listed
        disagreement is one the rule finds, or the first test would report
        it stale."""
        self.assertEqual(self.aligned - set(self.holders),
                         {"CoreDatasetCollection", "DatasetCollection",
                          "Grantor"})

    def test_a_planted_disagreement_fails_in_either_form(self):
        """known_biases holds DatasetBias, and both say exactMatch
        rai:dataBiases. A closeMatch on the slot fails whether its subject
        is the slot or the slot in a class, a class of either merged schema
        (CoreDataset is a class only the core schema defines). So does the
        class changing strength without its slot."""
        exact = ("exactMatch", "rai:dataBiases")
        close = ("closeMatch", "rai:dataBiases")
        self.assertEqual(self.pairs["known_biases"], {exact})
        self.assertEqual(self.pairs["DatasetBias"], {exact})
        for subject, drop, carried, held in (
                ("known_biases", exact, "closeMatch", "exactMatch"),
                ("Dataset_known_biases", None, "closeMatch/exactMatch",
                 "exactMatch"),
                ("CoreDataset_known_biases", None, "closeMatch/exactMatch",
                 "exactMatch"),
                ("DatasetBias", exact, "exactMatch", "closeMatch")):
            with self.subTest(subject=subject):
                self.assertEqual(
                    self.problems(pairs=self.changed(subject, close, drop)),
                    [("known_biases", f"unlisted: {carried} rai:dataBiases "
                                      f"where DatasetBias carries {held}")])

    def test_a_listing_without_a_reason_fails(self):
        for reason in (None, "", "   ", "see #4037"):
            listing = STRENGTH_EXCEPTIONS["distribution_formats"]._replace(
                reason=reason)
            with self.subTest(reason=reason):
                self.assertEqual(
                    self.problems(exceptions={"distribution_formats": listing}),
                    [("distribution_formats", "listed without a reason")])

    def test_a_stale_listing_fails(self):
        """A listing whose disagreement is gone fails: the slot follows its
        class, the slot is gone from both merged schemas, or the listing
        names a slot no schema declares. A listing whose predicates changed
        fails as not the listed disagreement."""
        exact, close = ("exactMatch", "evi:formats"), ("closeMatch", "evi:formats")
        stale = ("distribution_formats",
                 "stale: no disagreement with DistributionFormat on evi:formats")
        self.assertEqual(
            self.problems(pairs=self.changed("distribution_formats", close,
                                             exact)),
            [stale])
        gone = {c: s - {"distribution_formats"} for c, s in self.holders.items()}
        self.assertEqual(
            self.problems(holders=gone,
                          slot_names=self.slot_names - {"distribution_formats"}),
            [("distribution_formats",
              "stale: neither merged schema declares it")])
        self.assertEqual(
            self.problems(exceptions={
                **STRENGTH_EXCEPTIONS,
                "no_such_slot": STRENGTH_EXCEPTIONS["distribution_formats"]}),
            [("no_such_slot", "stale: neither merged schema declares it")])
        self.assertEqual(
            self.problems(pairs=self.changed(
                "distribution_formats", ("relatedMatch", "evi:formats"), exact)),
            [("distribution_formats",
              "not the listed disagreement: relatedMatch evi:formats where "
              "DistributionFormat carries closeMatch")])


#: Each EVI term the TTL names, with whether EVI defines it. The repository
#: holds no copy of EVI, so this records a check made against EVI 1.6, the
#: version https://w3id.org/EVI resolves to (79 terms; the Turtle fetched
#: 2026-10-01T06:40Z, sha256 8b5bb170..., for #3974 and #4037): it defines
#: none of the three. They stay in the TTL until #4037 decides each triple.
#: A new EVI target is checked against EVI the same way and recorded here
#: with what was found.
EVI_TARGETS_CHECKED = {
    "evi:formats": False,
    "evi:md5": False,
    "evi:sha256": False,
}


class TestNoUndefinedRaiTermAndNoUncheckedEviTerm(unittest.TestCase):
    """Scope: the rai: and evi: targets, of every subject.

    An rai: target must be one of the 20 properties Croissant RAI 1.0
    defines, read from the repository's list: #3942 removed the class
    triples on terms it does not define, and #3971 and #3974 their slot
    twins. An evi: target must be recorded in EVI_TARGETS_CHECKED. The
    three recorded are not EVI 1.6 terms; they are #4037's, so this class
    names them and does not fail on them. It fails on an RAI term RAI 1.0
    does not define, on an EVI term nobody has checked, on one recorded as
    undefined other than #4037's three, and on evi:samplingPlan (#3974).

    Not checked here: schema: targets. Class-level ones are checked against
    rdflib's schema.org term list (TestClassLevelCorrections). The three
    slot-level triples on schema:conformsTo, which schema.org does not
    define, are OPEN disagreements in generate_comprehensive_sssom.py."""

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

    def test_every_evi_target_is_recorded_as_checked(self):
        """The record names exactly the EVI targets the TTL names: an
        unrecorded one fails until it is checked against EVI, and a recorded
        one the TTL no longer names fails until the record follows (#4037).
        The only terms recorded as undefined are the three #4037 holds; a
        term found undefined later belongs in no triple. A term recorded as
        defined is taken on the record's word: with no copy of EVI here,
        that is the limit of this check."""
        evi = {o for _, _, o in self.triples if o.startswith("evi:")}
        self.assertEqual(evi, set(EVI_TARGETS_CHECKED))
        self.assertLessEqual(
            {t for t, defined in EVI_TARGETS_CHECKED.items() if not defined},
            {"evi:formats", "evi:md5", "evi:sha256"})

    def test_no_triple_names_evi_sampling_plan(self):
        """#3974: EVI 1.6, the version https://w3id.org/EVI resolves to, has
        79 terms and no samplingPlan in its Turtle, RDF/XML or JSON-LD form
        or on its documentation page (checked 2026-09-30); the repository
        holds no copy of EVI to test against."""
        self.assertNotIn("evi:samplingPlan", {o for _, _, o in self.triples})
        self.assertNotIn("evi:samplingPlan", EVI_TARGETS_CHECKED)


if __name__ == "__main__":
    unittest.main()
