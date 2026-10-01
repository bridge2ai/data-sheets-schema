"""The SKOS alignment TTL's own statistics describe the triples it carries,
and the class-level corrections of #3942 and #3926 hold.

Before #3942 the header said 189 triples (exact 112, close 59, related 10,
narrow 7, broad 1) while the file held 184 (111/58/9/6/0), and the per-section
and per-namespace counts were older still. Nothing checked them. The counts
here are taken from an rdflib parse, not from the generators' line pattern, and
the two parses are required to agree, so a triple written into a comment (which
the line pattern would read and a Turtle parser would not) fails.

Nothing here walks the corpus: the input is the TTL, plus the merged schemas
for the class names.
"""

import collections
import re
import sys
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "src" / "semantic_exchange"
TTL = REPO / "src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl"
SCHEMAS = (REPO / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
           REPO / "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")
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


def schema_classes():
    names = set()
    for path in SCHEMAS:
        names |= set((yaml.safe_load(path.read_text()) or {}).get("classes") or {})
    return names


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


#: Slot-level twins of #3942's class corrections that this change left as
#: found (#3971, #3995), with the triple each still carries. While a twin
#: still carries that triple, the comment block directly above it says
#: TODO(#3942); a twin settled later drops out of the check.
SLOT_TWINS_LEFT_AS_FOUND = {
    "discouraged_uses": ("exactMatch", "rai:prohibitedUses"),
    "prohibited_uses": ("exactMatch", "rai:prohibitedUses"),
    "ethical_reviews": ("exactMatch", "rai:ethicalReview"),
    "is_deidentified": ("narrowMatch", "rai:confidentialityLevel"),
    "extension_mechanism": ("closeMatch", "schema:license"),
    "distribution_dates": ("exactMatch", "schema:dateCreated"),
    "retention_limit": ("narrowMatch", "schema:conditionsOfAccess"),
    "confidential_elements": ("exactMatch", "rai:personalSensitiveInformation"),
    "sensitive_elements": ("closeMatch", "rai:personalSensitiveInformation"),
    "existing_uses": ("exactMatch", "rai:dataUseCases"),
    "data_protection_impacts": ("exactMatch", "rai:dataSocialImpact"),
}


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


if __name__ == "__main__":
    unittest.main()
