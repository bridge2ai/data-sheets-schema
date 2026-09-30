#!/usr/bin/env python3
"""
Generate the comprehensive SSSOM table: one row for every slot name in the
D4D schema.

Each slot's mapping is resolved in order of precedence, falling through only
when a higher source is silent (#2935):

1. The SKOS alignment TTL: a slot-level subject (``d4d:<slot>``), else a
   class-scoped one (``d4d:<Class>_<slot>``) for a class that carries the slot.
2. The schema's ``slot_uri`` (as ``skos:exactMatch``) and its
   ``exact_``/``close_``/``narrow_``/``broad_``/``related_mappings``, emitted
   with the matching SKOS predicate.
3. ``notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv``, where it suggests a URI. An
   entry with no suggested URI is silent and falls through; that includes the
   suggestions #2974 withdrew, whose ``review_note`` keeps the URI and why.
4. The keyword heuristics (``free_text`` / ``novel_d4d``), else ``unmapped``.
   A heuristic row is a status and asserts no mapping: no target, confidence
   0, and never ``semapv:ManualMappingCuration``, which only rungs 1 and 2
   earn. Until #2972 a ``novel_d4d`` row mapped ``d4d:<slot>`` to itself by
   exactMatch at confidence 1.0 under that justification, and an SSSOM
   consumer reads the justification, not ``mapping_source``.

   Every row of rung 4 is written in SSSOM's own form for "no match"
   (#3361): ``skos:exactMatch sssom:NoTermFound`` under
   ``semapv:UnspecifiedMatching``. The status (``free_text``, ``novel_d4d``,
   ``unmapped``) is in ``mapping_status``. Until #3361 these rows carried
   ``semapv:UnmappedProperty`` / ``semapv:UnmappableProperty`` as the
   predicate and ``semapv:FreeTextProperty`` / ``semapv:RequiresResearch``
   as the justification, none of which SEMAPV defines, with an empty
   ``object_id``, which SSSOM requires.

In both curated rungs only targets outside the D4D namespace count (#3054). A
``d4d:`` target is the slot itself or another D4D term, not an external
vocabulary: a ``d4d:`` slot_uri names the alignment's subject, and a TTL
triple such as ``d4d:File_file_type skos:exactMatch d4d:fileType`` restates
the slot's own slot_uri. So a slot whose only curated targets are D4D terms
falls through to rung 3 whichever input names them. The TTL's D4D targets
stay listed in ``other_curated_mappings``.

Before #2935 the heuristics ran first. They matched words in the slot name
*and description* and returned before the TTL was consulted, so 29 TTL-aligned
slots were labelled free text or novel: 25 whose TTL target is an external
term and 4 whose TTL target is a D4D term. The schema's own declarations were
never read, and a top-level slot that no class attribute repeats had no row.
The heuristic verdict is now recorded in ``heuristic_hint`` on every row and
decides ``mapping_status`` only when no curated source speaks.

One row per slot holds one primary mapping. Every other curated pair for the
slot is listed in ``other_curated_mappings`` with where it was declared, so no
curated alignment is dropped: a second TTL triple, the schema's declarations
where the TTL won, a slot_uri one class declares differently, a TTL triple
whose target is a D4D term.

``d4d_schema_path`` names a class that carries the slot: ``Dataset`` when it
does, else the first class (by name) that owns it. It is empty for a
top-level slot no class uses. ``d4d_owning_classes`` lists every class that
owns the slot: it declares the slot, and no ancestor that also declares it
does.

Where the TTL and the schema disagree, the TTL wins the row. "Disagree" means
the schema declares external targets for the slot and an external TTL pair is
not among them. Every such TTL pair is checked, slot-level and class-scoped
alike (#3053): the primary comes from a slot-level triple when there is one,
but a ``<Class>_<slot>`` triple is the TTL's word on the slot as well. The
schema side is every declaration of the slot *name*, in whichever class, so
two attributes that share a name are compared as one:
``regulatory_restrictions`` disagrees although its path class, Dataset,
declares no external target, because ExportControlRegulatoryRestrictions
declares an attribute of the same name that has them. A listing's reason says
whose declarations it compares (#3140). Each
such slot must be listed in ACCEPTED_DISAGREEMENTS or
OPEN_DISAGREEMENTS with the TTL and schema pairs it was reviewed for and a
reason. A listing matches only while both sides declare exactly those pairs
(#2991): a listed slot whose pairs change is ``changed``. A run warns about
every unlisted disagreement, every changed one, every listed slot that no
longer disagrees, and every open one; the tests fail on the first three.

The output is a function of the schema, the TTL, the recommendations and the
date. ``--date`` sets the date. ``--check`` regenerates in memory under the
date the committed file records, fails on any difference, and writes nothing.

So a change to any of those inputs regenerates both comprehensive tables in
the same commit (``make gen-sssom-comprehensive gen-sssom-uri-comprehensive``):
an edit to the schema, to the SKOS alignment TTL (a slot-level or
``<Class>_<slot>`` triple, such as the /d4d-add-mapping playbook adds), or to
the recommendations file. The drift tests fail until it does, and say so.
"""

import csv
import io
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add fairscape_models to path
fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
if fairscape_path.exists() and str(fairscape_path) not in sys.path:
    sys.path.insert(0, str(fairscape_path))

try:
    from fairscape_models.rocrate import ROCrateMetadataElem
    FAIRSCAPE_AVAILABLE = True
except ImportError:
    FAIRSCAPE_AVAILABLE = False


D4D_NAMESPACE = 'https://w3id.org/bridge2ai/data-sheets-schema/'

#: SKOS predicates from strongest to weakest. When a slot has several TTL
#: pairs, the primary is the strongest, then the first in the file.
SKOS_ORDER = ('exactMatch', 'closeMatch', 'narrowMatch', 'broadMatch',
              'relatedMatch')

#: Schema metaslots read as alignments, in the order a primary is chosen, and
#: the SKOS predicate each is emitted with.
SCHEMA_MAPPING_KINDS = (
    ('slot_uri', 'skos:exactMatch'),
    ('exact_mappings', 'skos:exactMatch'),
    ('close_mappings', 'skos:closeMatch'),
    ('narrow_mappings', 'skos:narrowMatch'),
    ('broad_mappings', 'skos:broadMatch'),
    ('related_mappings', 'skos:relatedMatch'),
)

#: What ``rocrate_json_path`` is read against: the RO-Crate 1.1 JSON-LD
#: context (https://w3id.org/ro/crate/1.1/context, version 1.1.3). Every
#: schema.org term it defines is keyed by its local name. These are the
#: property terms it keys bare for another vocabulary's IRI (#3052); its
#: class terms are left out, since an object here is a property.
ROCRATE_CONTEXT_TERMS: Dict[str, str] = {
    'http://purl.org/dc/terms/conformsTo': 'conformsTo',
    'http://www.w3.org/ns/prov#wasDerivedFrom': 'wasDerivedFrom',
    'http://purl.org/pav/importedBy': 'importedBy',
    'http://purl.org/pav/importedFrom': 'importedFrom',
    'http://purl.org/pav/importedOn': 'importedOn',
    'http://purl.org/pav/retrievedBy': 'retrievedBy',
    'http://purl.org/pav/retrievedFrom': 'retrievedFrom',
    'http://purl.org/pav/retrievedOn': 'retrievedOn',
    'http://pcdm.org/models#hasFile': 'hasFile',
    'http://pcdm.org/models#hasMember': 'hasMember',
    'https://bioschemas.org/ComputationalWorkflow#input': 'input',
    'https://bioschemas.org/ComputationalWorkflow#output': 'output',
    'https://www.w3.org/ns/iana/link-relations/relation#cite-as': 'cite-as',
}

#: The prefixes that context declares, by namespace. It declares ``dct``,
#: not ``dcterms``, and no prefix for DCAT, EVI, RAI, DUO, QUDT, SPDX or D4D.
ROCRATE_CONTEXT_PREFIXES: Dict[str, str] = {
    'http://schema.org/': 'schema',
    'http://purl.org/dc/terms/': 'dct',
    'http://www.w3.org/ns/prov#': 'prov',
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
    'http://www.w3.org/2000/01/rdf-schema#': 'rdfs',
    'http://purl.org/pav/': 'pav',
    'http://pcdm.org/models#': 'pcdm',
    'http://xmlns.com/foaf/0.1/': 'foaf',
    'http://purl.org/ontology/bibo/': 'bibo',
    'http://creativecommons.org/ns#': 'cc',
    'http://purl.org/cerif/frapo/': 'frapo',
    'http://www.w3.org/ns/rdfa#': 'rdfa',
    'https://www.w3.org/ns/iana/link-relations/relation#': 'rel',
    'http://purl.org/ro/roterms#': 'roterms',
    'http://purl.org/ro/wf4ever#': 'wf4ever',
    'http://purl.org/ro/wfdesc#': 'wfdesc',
    'http://purl.org/ro/wfprov#': 'wfprov',
}

#: schema.org's namespace in either scheme: the context writes http, the TTL
#: https.
SCHEMA_ORG = ('http://schema.org/', 'https://schema.org/')

FREE_TEXT_KEYWORDS = ('description', 'documentation', 'comment', 'notes',
                      'details', 'narrative', 'paragraph')
NOVEL_D4D_KEYWORDS = ('strategies', 'protocol', 'analyses', 'compensation',
                      'governance', 'warnings', 'gaps', 'impacts', 'biases',
                      'imputation', 'deidentif', 'confidential', 'vulnerable',
                      'ethical', 'prohibited', 'retention', 'errata')

_CROSS_VOCABULARY = (
    "cross-vocabulary: the TTL aligns the slot to an RO-Crate (schema.org / "
    "EVI) property and the schema serialises it as the DCAT / Dublin Core / "
    "PROV property for the same notion ({schema}); both are curated and the "
    "row carries the TTL's")
_STRENGTH_ONLY = (
    "same target, different strength: the schema's {schema} serialises the "
    "slot as the TTL's target, which the TTL qualifies as {ttl}; the row keeps "
    "the TTL predicate")
_BROADER_ONLY = (
    "compatible: the schema adds only a broader term ({schema}) beside the "
    "TTL's more specific alignment")
_NOT_SCHEMA_ORG = (
    "schema:conformsTo is not a schema.org term (https://schema.org/conformsTo "
    "does not resolve; checked 2026-09-28), and RO-Crate 1.1's JSON-LD context "
    "maps its conformsTo key to dcterms:conformsTo")


@dataclass(frozen=True)
class Listed:
    """A TTL/schema disagreement as it was reviewed (#2991).

    ``ttl`` and ``schema`` are the pairs each side declared for the slot when
    the reason was written, as ``'<predicate> <object>'``: every external TTL
    pair, from slot-level and ``<Class>_<slot>`` subjects (#3053), and every
    external schema declaration of the slot name, in whichever class declares
    it. A listing holds
    only while both sides still declare exactly these pairs: any change on
    either side makes the slot ``changed``, which warns and fails the tests,
    because the reason was written for the pairs listed and may no longer be
    true.

    ``reason`` names each schema declaration it cites by its metaslot
    (``slot_uri dcat:keyword``). A declaration the row's path class does not
    see (not its own, an ancestor's or the top-level slot's) is another
    class's, and the reason names it as ``<Class>.<slot>`` (#3140). A path
    class that declares the name as its own attribute, or has an ancestor
    that does, hides the top-level slot: that slot's declarations are then
    another's too, and the reason says they are the top-level slot's
    (#3193).
    """
    ttl: Tuple[str, ...]
    schema: Tuple[str, ...]
    reason: str

    def signature(self) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
        return tuple(sorted(set(self.ttl))), tuple(sorted(set(self.schema)))


def _cross(ttl: str, slot_uri: str) -> Listed:
    """A cross-vocabulary listing: the TTL's one pair against the schema's
    ``slot_uri`` (emitted as exactMatch)."""
    return Listed((ttl,), (f'skos:exactMatch {slot_uri}',),
                  _CROSS_VOCABULARY.format(schema=f'slot_uri {slot_uri}'))


#: TTL/schema disagreements that are understood. The TTL target is the row's;
#: the schema's declaration stays in ``other_curated_mappings``. No warning.
ACCEPTED_DISAGREEMENTS: Dict[str, Listed] = {
    'title': _cross('skos:exactMatch schema:name', 'dcterms:title'),
    'keywords': _cross('skos:exactMatch schema:keywords', 'dcat:keyword'),
    'publisher': _cross('skos:exactMatch schema:publisher',
                        'dcterms:publisher'),
    'page': _cross('skos:exactMatch schema:url', 'dcat:landingPage'),
    'bytes': _cross('skos:exactMatch schema:contentSize', 'dcat:byteSize'),
    'created_on': _cross('skos:exactMatch schema:dateCreated',
                         'dcterms:created'),
    'issued': _cross('skos:exactMatch schema:datePublished', 'dcterms:issued'),
    'last_updated_on': _cross('skos:exactMatch schema:dateModified',
                              'dcterms:modified'),
    'format': _cross('skos:exactMatch schema:encodingFormat', 'dcterms:format'),
    'created_by': _cross('skos:closeMatch schema:creator', 'dcterms:creator'),
    'modified_by': _cross('skos:closeMatch schema:contributor',
                          'dcterms:contributor'),
    'compression': Listed(
        ('skos:closeMatch evi:formats',),
        ('skos:exactMatch dcat:compressFormat',),
        "compatible: the TTL hedges with closeMatch evi:formats, the general "
        "format term it also uses for distribution_formats and encoding; the "
        "schema's slot_uri dcat:compressFormat is the specific DCAT term for "
        "a compression format"),
    'themes': _cross('skos:closeMatch schema:about', 'dcat:theme'),
    'external_resources': _cross('skos:closeMatch schema:relatedLink',
                                 'dcterms:references'),
    'was_derived_from': Listed(
        ('skos:exactMatch schema:isBasedOn',),
        ('skos:exactMatch dcterms:source', 'skos:exactMatch prov:wasDerivedFrom'),
        _CROSS_VOCABULARY.format(
            schema='slot_uri prov:wasDerivedFrom, exact_mappings '
                   'dcterms:source')),
    # #3140: not a cross-vocabulary choice. The row's path class declares no
    # external target; the schema's pairs are those of another attribute that
    # shares the slot name.
    'regulatory_restrictions': Listed(
        ('skos:closeMatch schema:conditionsOfAccess',),
        ('skos:broadMatch DUO:0000021', 'skos:broadMatch DUO:0000022',
         'skos:broadMatch DUO:0000028', 'skos:exactMatch dcterms:accessRights'),
        "a shared slot name, not two alignments of one slot: the row's path "
        "class, Dataset, declares regulatory_restrictions with slot_uri "
        "d4d:regulatoryRestrictions (range "
        "ExportControlRegulatoryRestrictions, an inlined object) and no "
        "external mapping, and its subclass "
        "DataSubset inherits that declaration. The schema's pairs belong to "
        "ExportControlRegulatoryRestrictions.regulatory_restrictions, a "
        "different attribute with the same name: a multivalued string naming "
        "each restriction, with slot_uri dcterms:accessRights and "
        "broad_mappings DUO:0000021, DUO:0000022 and DUO:0000028. The TTL's "
        "slot-level closeMatch schema:conditionsOfAccess names no class. It "
        "is the target the core schema (D4D_Core.yaml) gives the core's "
        "counterpart, CoreDataset.regulatory_restrictions, as a broad "
        "mapping; the full schema gives Dataset.regulatory_restrictions no "
        "external target. The row carries the TTL's target, and "
        "other_curated_mappings labels each schema pair with the class that "
        "declares it"),
    'md5': Listed(
        ('skos:exactMatch evi:md5',),
        ('skos:broadMatch dcterms:identifier',),
        _BROADER_ONLY.format(schema='broad_mappings dcterms:identifier')),
    'license_and_use_terms': Listed(
        ('skos:closeMatch schema:license',),
        ('skos:exactMatch schema:license',),
        _STRENGTH_ONLY.format(schema='slot_uri schema:license',
                              ttl='closeMatch')),
    'dialect': Listed(
        ('skos:closeMatch schema:encodingFormat',),
        ('skos:exactMatch schema:encodingFormat',),
        _STRENGTH_ONLY.format(schema='slot_uri schema:encodingFormat',
                              ttl='closeMatch')),
    # #3193: the path class redeclares media_type as its own attribute, so it
    # does not see the top-level slot, and an exact mapping is not a
    # serialisation (only a slot_uri is).
    'media_type': Listed(
        ('skos:closeMatch schema:encodingFormat',),
        ('skos:exactMatch dcat:mediaType',
         'skos:exactMatch schema:encodingFormat'),
        "same target, different strength, on declarations the row's path "
        "class does not make: DistributionFormat declares its own media_type "
        "attribute with slot_uri dcat:mediaType and no exact mapping. The "
        "exact_mappings schema:encodingFormat is on the top-level media_type "
        "slot and on File.media_type, and says the two terms are equivalent; "
        "it does not serialise the slot, whose slot_uri is dcat:mediaType in "
        "every declaration. The TTL's slot-level triple qualifies that "
        "equivalence as closeMatch; the row keeps the TTL predicate"),
    # #3053: the TTL's two class-scoped triples (DatasetCollection_resources,
    # FileCollection_resources) say exactMatch schema:hasPart and agree with
    # the schema; its slot-level triple is the one that qualifies it.
    'resources': Listed(
        ('skos:exactMatch schema:hasPart', 'skos:relatedMatch schema:hasPart'),
        ('skos:exactMatch schema:hasPart',),
        _STRENGTH_ONLY.format(schema='slot_uri schema:hasPart',
                              ttl='relatedMatch at slot level (its '
                                  'DatasetCollection_resources and '
                                  'FileCollection_resources triples say '
                                  'exactMatch, as the schema does)')),
    'path': Listed(
        ('skos:narrowMatch schema:contentUrl',),
        ('skos:exactMatch schema:contentUrl',),
        _STRENGTH_ONLY.format(schema='slot_uri schema:contentUrl',
                              ttl='narrowMatch')),
}

#: Disagreements where one side is probably wrong. The TTL still wins the row
#: (precedence), but every run warns until a curator settles them.
OPEN_DISAGREEMENTS: Dict[str, Listed] = {
    'creators': Listed(
        ('skos:closeMatch schema:author',),
        ('skos:exactMatch schema:creator',),
        "same vocabulary, different term: the TTL says closeMatch "
        "schema:author, the schema's slot_uri is schema:creator"),
    'download_url': Listed(
        ('skos:exactMatch schema:contentUrl',),
        ('skos:exactMatch dcat:downloadURL', 'skos:exactMatch schema:url'),
        "same vocabulary, different term: the TTL says exactMatch "
        "schema:contentUrl, the schema's exact_mappings says schema:url "
        "(beside slot_uri dcat:downloadURL); both cannot be exact"),
    'id': Listed(
        ('skos:exactMatch rdf:ID',),
        ('skos:exactMatch schema:identifier',),
        "the TTL says exactMatch rdf:ID, an RDF/XML syntax attribute rather "
        "than a property; the schema's slot_uri is schema:identifier"),
    'hash': Listed(
        ('skos:exactMatch evi:md5',),
        ('skos:broadMatch dcterms:identifier',),
        "the TTL says exactMatch evi:md5 for a slot that does not fix the "
        "hash algorithm (md5 and sha256 are separate slots); the schema "
        "declares only broad_mappings dcterms:identifier"),
    'sha256': Listed(
        ('skos:exactMatch evi:sha256',),
        ('skos:exactMatch schema:sha256',),
        "two vocabularies' checksum terms: the TTL says exactMatch "
        "evi:sha256, the schema's slot_uri is schema:sha256; one should be "
        "the slot's serialisation, or the TTL should carry both"),
    # #2990: these three were listed as accepted until review round 1 of
    # #2963. The TTL side names an IRI that does not exist.
    'conforms_to': Listed(
        ('skos:exactMatch schema:conformsTo',),
        ('skos:exactMatch dcterms:conformsTo',),
        "the TTL says exactMatch schema:conformsTo, but " + _NOT_SCHEMA_ORG
        + ", the schema's slot_uri; the TTL's target is probably the wrong "
        "IRI for the same property"),
    'conforms_to_class': Listed(
        ('skos:narrowMatch schema:conformsTo',),
        ('skos:broadMatch dcterms:conformsTo',),
        "the TTL says narrowMatch schema:conformsTo, but " + _NOT_SCHEMA_ORG
        + "; and narrowMatch says the target is narrower than the slot, while "
        "the TTL's own comment calls the D4D slot the narrower one and the "
        "schema's broad_mappings dcterms:conformsTo says the target is "
        "broader, so the two declarations point in opposite directions"),
    'conforms_to_schema': Listed(
        ('skos:narrowMatch schema:conformsTo',),
        ('skos:broadMatch dcterms:conformsTo',),
        "the TTL says narrowMatch schema:conformsTo, but " + _NOT_SCHEMA_ORG
        + "; and narrowMatch says the target is narrower than the slot, while "
        "the TTL's own comment calls the D4D slot the narrower one and the "
        "schema's broad_mappings dcterms:conformsTo says the target is "
        "broader, so the two declarations point in opposite directions"),
}


@dataclass(frozen=True)
class CuratedPair:
    """One curated alignment of a slot, and where it was declared."""
    predicate: str          # e.g. skos:exactMatch
    object: str             # CURIE
    source: str             # 'ttl' or 'schema'
    where: str = ''         # '' (slot-level / top-level), a class, or a TTL subject


@dataclass
class Resolution:
    """How one slot resolves. Both comprehensive tables are built from this."""
    slot: str
    path_class: str
    owners: List[str]
    description: str
    hint: str
    status: str
    source: str
    predicate: str
    object: str
    confidence: float
    justification: str
    comment: str
    origin: str = ''        # the TTL subject or schema metaslot of the primary
    others: List[str] = field(default_factory=list)
    # '', 'accepted', 'open', 'changed' (listed for other pairs) or 'unlisted'
    disagreement: str = ''
    # The (TTL, schema) pairs, as text, where the two disagree
    disagreement_pairs: Tuple[Tuple[str, ...], Tuple[str, ...]] = ((), ())
    notes: List[str] = field(default_factory=list)  # appended to the comment


#: How a row's comment names each kind of TTL/schema disagreement.
DISAGREEMENT_NOTES = {
    'accepted': 'accepted',
    'open': 'open',
    'changed': 'not the listed pairs',
    'unlisted': 'unlisted',
}

#: What a drift failure tells the reader to do (#2993).
REGENERATE_HINT = (
    "Regenerate both tables with `make gen-sssom-comprehensive "
    "gen-sssom-uri-comprehensive` and commit them with the change that moved "
    "them: an edit to the schema, to the SKOS alignment TTL (a slot-level or "
    "<Class>_<slot> triple, as /d4d-add-mapping adds) or to "
    "notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv moves them")


#: The comment on a ``novel_d4d`` row. The status is the keyword heuristic's
#: guess that no external vocabulary has the notion; nobody reviewed it.
NOVEL_D4D_COMMENT = ('Keyword heuristic: probably a novel D4D concept with no '
                     'external counterpart - not curated, no mapping asserted')

#: The justification only a curated source earns: a TTL triple or a schema
#: declaration. A heuristic or recommended row never carries it (#2972).
CURATED_JUSTIFICATION = 'semapv:ManualMappingCuration'

#: SSSOM's object for "no term was found" (#3361). A row that asserts no
#: mapping (``free_text``, ``novel_d4d``, ``unmapped``) carries it as its
#: ``object_id``, with the predicate a match was looked for under and a
#: justification SEMAPV defines. The resolution's own ``object`` stays empty:
#: it names a target, and there is none, so the RO-Crate path, object label,
#: object source and recommended slot_uri stay empty too.
NO_TERM_FOUND = 'sssom:NoTermFound'
NO_TERM_PREDICATE = 'skos:exactMatch'
NO_TERM_JUSTIFICATION = 'semapv:UnspecifiedMatching'


#: The sources whose rows a curated input declares: a TTL triple or a schema
#: declaration. Every other source (``recommendations``, ``heuristic``,
#: ``none``) is this generator's resolution.
CURATED_SOURCES = ('ttl', 'schema')

#: SSSOM's ``mapping_tool`` for a row the generator decided rather than a
#: curated input declared (#2971). Every row once carried ``author_id``
#: ``https://orcid.org/0000-0000-0000-0000``, a well-formed ORCID naming
#: nobody. No row names a person now: nobody is named as the curator of the
#: TTL or the schema declarations, so a curated row leaves ``author_id``
#: empty too, and a heuristic, recommended or unmapped row is credited to
#: this script instead. SSSOM requires neither ``author_id`` nor
#: ``creator_id`` on a mapping. No ``mapping_tool_version`` is written: the
#: script has no version of its own, and the table's date and
#: ``mapping_set_version`` already say which generation it is.
MAPPING_TOOL = ('https://github.com/bridge2ai/data-sheets-schema/blob/main/'
                'src/semantic_exchange/generate_comprehensive_sssom.py')


def mapping_tool(res: 'Resolution') -> str:
    """The row's ``mapping_tool``: empty for a curated row, else this script."""
    return '' if res.source in CURATED_SOURCES else MAPPING_TOOL


def sssom_object_id(res: 'Resolution') -> str:
    """The row's ``object_id``: the target, else ``sssom:NoTermFound``."""
    return res.object or NO_TERM_FOUND


def heuristic_hint(slot: str, description: str) -> str:
    """The keyword verdict: 'free_text', 'novel_d4d' or ''.

    Advisory. It decides ``mapping_status`` only when no curated source speaks
    for the slot, and is recorded either way.
    """
    desc = (description or '').lower()
    name = slot.lower()
    if any(kw in name or kw in desc for kw in FREE_TEXT_KEYWORDS):
        return 'free_text'
    if any(kw in name or kw in desc for kw in NOVEL_D4D_KEYWORDS):
        return 'novel_d4d'
    return ''


def parse_ttl_prefixes(content: str) -> Dict[str, str]:
    """``@prefix p: <uri> .`` declarations of a Turtle file."""
    return dict(re.findall(r'@prefix\s+(\w*):\s*<([^>]*)>\s*\.', content))


def committed_date(path: Path) -> str:
    """The ``# Date:`` a committed table records, as YYYY-MM-DD."""
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('#'):
            break
        m = re.match(r'#\s*Date:\s*(\S+)', line)
        if m:
            return date.fromisoformat(m.group(1)[:10]).isoformat()
    raise ValueError(f"{path} records no '# Date:' header line, so it cannot "
                     "be regenerated under the date it was made")


def table_rows(text: str, key: str) -> Dict[str, Dict[str, str]]:
    """Data rows of a rendered table, keyed by the ``key`` column."""
    body = ''.join(line for line in text.splitlines(keepends=True)
                   if not line.startswith('#'))
    return {r[key]: r for r in csv.DictReader(io.StringIO(body), delimiter='\t')}


def report_drift(committed: Path, regenerated: str, key: str) -> int:
    """Compare a committed table with its regeneration; 0 when identical."""
    current = committed.read_text(encoding='utf-8') if committed.exists() else None
    if current == regenerated:
        print(f"✓ {committed} regenerates exactly.")
        return 0
    print(f"✗ {committed} does not regenerate from its inputs.")
    if current is None:
        print("  The file does not exist.")
        print(f"  {REGENERATE_HINT}.")
        return 1
    have, made = table_rows(current, key), table_rows(regenerated, key)
    lost = sorted(set(have) - set(made))
    gained = sorted(set(made) - set(have))
    changed = sorted(k for k in set(have) & set(made) if have[k] != made[k])
    for label, keys in (('rows only in the committed file', lost),
                        ('rows only in the regeneration', gained),
                        ('rows that differ', changed)):
        if keys:
            print(f"  {len(keys)} {label}: {', '.join(keys[:20])}"
                  + (' ...' if len(keys) > 20 else ''))
    old_head = [line for line in current.splitlines() if line.startswith('#')]
    new_head = [line for line in regenerated.splitlines() if line.startswith('#')]
    if old_head != new_head:
        print("  The '#' header differs.")
    print(f"  {REGENERATE_HINT}.")
    return 1


class ComprehensiveSSSOMGenerator:
    """Generate comprehensive SSSOM including all D4D slots."""

    FIELDNAMES = [
        'd4d_schema_path',
        'subject_id',
        'subject_label',
        'predicate_id',
        'rocrate_json_path',
        'object_id',
        'object_label',
        'mapping_justification',
        'confidence',
        'comment',
        'author_id',
        'mapping_tool',
        'mapping_date',
        'subject_source',
        'object_source',
        'mapping_set_id',
        'mapping_set_version',
        'mapping_status',
        'mapping_source',
        'other_curated_mappings',
        'heuristic_hint',
        'd4d_owning_classes',
        'd4d_description',
    ]

    def __init__(
        self,
        d4d_schema: Path,
        skos_file: Path,
        recommendations_file: Optional[Path] = None
    ):
        self.d4d_schema = d4d_schema
        self.skos_file = skos_file
        self.recommendations_file = recommendations_file

        from data_sheets_schema.schema_view import shared_view
        self.sv = shared_view(d4d_schema)

        ttl = Path(skos_file).read_text(encoding='utf-8')
        self.skos_triples = self._parse_skos(ttl)
        self.namespaces = self._namespace_map(ttl)
        self.recommendations = (self._load_recommendations()
                                if recommendations_file else {})
        self.d4d_attributes = self._load_d4d_attributes()
        self.resolutions = {slot: self._resolve(slot)
                            for slot in sorted(self.d4d_attributes)}

    # ------------------------------------------------------------ inputs
    def _load_d4d_attributes(self) -> Dict[str, Dict]:
        """Every slot name in the schema, with the classes that own it.

        ``SchemaView.all_slots`` covers top-level ``slots:`` and every class
        attribute, so a top-level slot no attribute repeats still gets a row.

        The merged schema repeats inherited attributes on every subclass
        (``description`` is declared on 78 classes), so a class *owns* a slot
        when it declares it and no ancestor that also declares it does:
        ``description`` is owned by DatasetProperty, Grant, NamedThing and
        Organization.
        """
        sv = self.sv
        classes = sorted(sv.all_classes())
        carriers: Dict[str, List[str]] = {}
        declarers: Dict[str, List[str]] = {}
        for cls in classes:
            for slot in sv.class_slots(cls):
                carriers.setdefault(slot, []).append(cls)
            for slot in sv.class_slots(cls, direct=True):
                declarers.setdefault(slot, []).append(cls)

        top_level = sv.all_slots(attributes=False)
        attributes = {}
        for slot in sv.all_slots():
            carried = carriers.get(slot, [])
            declared = set(declarers.get(slot, []))
            owned = [c for c in sorted(declared)
                     if not declared & set(sv.class_ancestors(c)[1:])]
            if 'Dataset' in carried:
                path_class = 'Dataset'
            else:
                path_class = (owned or carried or [''])[0]
            definitions = self._definitions(slot, path_class, classes, top_level)
            description = next((d.description for _, d in definitions
                                if d.description), '')
            attributes[slot] = {
                'description': description,
                'path_class': path_class,
                'owners': owned,
                'definitions': definitions,
            }
        return attributes

    def _definitions(self, slot, path_class, classes, top_level):
        """Every declaration of ``slot``, most specific to ``path_class`` first.

        The path class, then its ancestors, then the top-level slot, then every
        other class by name; within a class, ``slot_usage`` before
        ``attributes``. The first external target in this order is the schema's
        primary mapping. That is the one its path class sees unless the class's
        own attribute carries no external target and a hidden top-level slot
        does, in which case the row takes the top-level slot's (#3424; no slot
        in the committed schema is shaped so).

        Where the path class or an ancestor declares the name as its own
        attribute, that attribute replaces the top-level slot for the class,
        which then does not see the slot's declarations (#3193). They keep
        their place here, after the path class and its ancestors and before
        every other class, as another class's would if it came first by name;
        so no row moves, and the rule changes only what a listing's reason
        must attribute (``Listed``).
        """
        sv = self.sv
        near = list(sv.class_ancestors(path_class)) if path_class else []
        order = near + [None] + [c for c in classes if c not in near]
        found = []
        for cls in order:
            if cls is None:
                if slot in top_level:
                    found.append(('', top_level[slot]))
                continue
            cdef = sv.get_class(cls)
            for group in (cdef.slot_usage, cdef.attributes):
                if group and slot in group:
                    found.append((cls, group[slot]))
        return found

    def _parse_skos(self, content: str) -> List[Tuple[str, str, str]]:
        """(subject, predicate, object) for every SKOS match triple, in order.

        The pattern fits the file's one-triple-per-line layout; an rdflib parse
        finds the same triples.
        """
        pattern = r'd4d:(\w+)\s+skos:(\w+Match)\s+(\S+)\s+\.'
        return [m.groups() for m in re.finditer(pattern, content)]

    def _namespace_map(self, ttl: str) -> Dict[str, str]:
        """Prefix -> namespace IRI: the TTL's declarations, then the schema's."""
        mapping = {p: str(uri) for p, uri in self.sv.namespaces().items()}
        mapping.update(parse_ttl_prefixes(ttl))
        return mapping

    def _load_recommendations(self) -> Dict[str, Dict]:
        """Load URI recommendations from TSV."""
        recommendations = {}

        if not self.recommendations_file.exists():
            return recommendations

        with open(self.recommendations_file) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                attr = row['attribute']
                recommendations[attr] = {
                    'suggested_uri': row.get('suggested_uri', ''),
                    'confidence': row.get('confidence', 'unknown')
                }

        return recommendations

    # ------------------------------------------------------------ curated sources
    def _is_internal(self, curie: str) -> bool:
        prefix = curie.split(':', 1)[0] if ':' in curie else ''
        return (curie.startswith(D4D_NAMESPACE)
                or self.namespaces.get(prefix, '').startswith(D4D_NAMESPACE))

    def ttl_pairs(self, slot: str) -> Tuple[List[CuratedPair], List[CuratedPair]]:
        """(slot-level, class-scoped) TTL triples on ``slot``, strongest first.

        A class-scoped subject is ``<Class>_<slot>`` for a class that carries
        the slot (``d4d:FileCollection_total_bytes``). D4D targets are
        included; the resolution sets them aside (#3054).
        """
        classes = set(self.sv.all_classes())
        slot_level, scoped = [], []
        for subject, predicate, obj in self.skos_triples:
            if subject == slot:
                slot_level.append(CuratedPair(f'skos:{predicate}', obj, 'ttl'))
            elif subject.endswith('_' + slot):
                cls = subject[:-len(slot) - 1]
                if cls in classes and slot in self.sv.class_slots(cls):
                    scoped.append(CuratedPair(f'skos:{predicate}', obj, 'ttl',
                                              f'd4d:{subject}'))
        rank = {f'skos:{p}': i for i, p in enumerate(SKOS_ORDER)}
        slot_level.sort(key=lambda p: rank.get(p.predicate, len(rank)))
        scoped.sort(key=lambda p: rank.get(p.predicate, len(rank)))
        return slot_level, scoped

    def schema_pairs(self, slot: str) -> List[Tuple[CuratedPair, str]]:
        """External targets the schema declares for ``slot``, with the metaslot."""
        pairs = []
        for cls, definition in self.d4d_attributes[slot]['definitions']:
            for metaslot, predicate in SCHEMA_MAPPING_KINDS:
                value = getattr(definition, metaslot, None)
                values = [value] if isinstance(value, str) else list(value or [])
                for v in map(str, values):
                    if not self._is_internal(v):
                        pairs.append((CuratedPair(predicate, v, 'schema', cls),
                                      metaslot))
        return pairs

    def declared_slot_uri(self, slot: str) -> str:
        """The slot_uri the row's path class sees, D4D namespace included."""
        for _, definition in self.d4d_attributes[slot]['definitions']:
            if definition.slot_uri:
                return str(definition.slot_uri)
        return ''

    # ------------------------------------------------------------ resolution
    def _resolve(self, slot: str) -> Resolution:
        res = self._resolve_mapping(slot)
        if not res.path_class:
            res.notes.append('no class uses this slot')
        return res

    def _resolve_mapping(self, slot: str) -> Resolution:
        info = self.d4d_attributes[slot]
        base = dict(slot=slot, path_class=info['path_class'],
                    owners=info['owners'], description=info['description'],
                    hint=heuristic_hint(slot, info['description']))

        slot_level, scoped = self.ttl_pairs(slot)
        # A D4D target is not an alignment, in the TTL as in the schema
        # (#3054): it is listed, never the row.
        internal = [p for p in slot_level + scoped if self._is_internal(p.object)]
        slot_level = [p for p in slot_level if not self._is_internal(p.object)]
        scoped = [p for p in scoped if not self._is_internal(p.object)]
        schema = self.schema_pairs(slot)
        ttl_used = slot_level or scoped        # where the primary comes from
        ttl_all = slot_level + scoped          # what the schema is checked against (#3053)
        curated = ttl_all + [p for p, _ in schema] + internal
        silent = ([] if ttl_used or not internal else
                  ['TTL names only D4D terms, which are not alignments'])

        if ttl_used:                                       # 1. TTL
            primary = ttl_used[0]
            origin = primary.where or f'd4d:{slot}'
            comment = 'Mapped via SKOS alignment' + (
                f' ({primary.where})' if primary.where else '')
            source = 'ttl'
        elif schema:                                       # 2. schema
            primary, origin = schema[0]
            comment = f'Mapped via schema {origin}'
            source = 'schema'
        else:
            primary = None

        if primary is not None:
            schema_curated = [p for p, _ in schema]
            disagreement = self._disagreement(slot, ttl_all, schema_curated)
            return Resolution(
                **base, status='mapped', source=source,
                predicate=primary.predicate, object=primary.object,
                confidence=self._get_confidence(primary.predicate.split(':')[1]),
                justification=CURATED_JUSTIFICATION,
                comment=comment, origin=origin,
                others=self._others(primary, curated),
                disagreement=disagreement,
                disagreement_pairs=(self.signature(ttl_all, schema_curated)
                                    if disagreement else ((), ())),
                notes=([f'TTL and schema disagree '
                        f'({DISAGREEMENT_NOTES[disagreement]})']
                       if disagreement else []))

        # No curated external target: only a TTL D4D term can be left over.
        base.update(others=self._others(None, internal), notes=silent)

        rec = self.recommendations.get(slot)                # 3. recommendation
        if rec and rec['suggested_uri']:
            return Resolution(
                **base, status='recommended', source='recommendations',
                predicate='skos:closeMatch', object=rec['suggested_uri'],
                confidence=0.7 if rec['confidence'] == 'high' else 0.5,
                justification='semapv:SuggestedMapping',
                comment=f"Recommended mapping (confidence: {rec['confidence']})")

        if base['hint'] == 'novel_d4d':                     # 4. heuristics
            # A status, not a mapping (#2972): the keyword verdict names no
            # target, and a ``d4d:<slot>`` object would map the slot to itself
            # under a justification no curator gave.
            return Resolution(
                **base, status='novel_d4d', source='heuristic',
                predicate=NO_TERM_PREDICATE, object='',
                confidence=0.0, justification=NO_TERM_JUSTIFICATION,
                comment=NOVEL_D4D_COMMENT)
        if base['hint'] == 'free_text':
            return Resolution(
                **base, status='free_text', source='heuristic',
                predicate=NO_TERM_PREDICATE, object='',
                confidence=0.0, justification=NO_TERM_JUSTIFICATION,
                comment='Free text/narrative field - no URI needed')
        return Resolution(
            **base, status='unmapped', source='none',
            predicate=NO_TERM_PREDICATE, object='', confidence=0.0,
            justification=NO_TERM_JUSTIFICATION,
            comment='Unmapped - needs vocabulary research')

    def _disagreement(self, slot: str, ttl: List[CuratedPair],
                      schema: List[CuratedPair]) -> str:
        """'' when the TTL and the schema agree, else how the slot is listed.

        A listing is matched on the slot *and* the pairs both sides declare
        (#2991): a listed slot whose TTL or schema pairs are no longer the
        listed ones is ``changed``, not accepted or open, because its reason
        was written for other pairs.
        """
        if not self.disagrees(ttl, schema):
            return ''
        seen = self.signature(ttl, schema)
        for status, listing in (('accepted', ACCEPTED_DISAGREEMENTS),
                                ('open', OPEN_DISAGREEMENTS)):
            entry = listing.get(slot)
            if entry is not None:
                return status if entry.signature() == seen else 'changed'
        return 'unlisted'

    @staticmethod
    def signature(ttl: List[CuratedPair], schema: List[CuratedPair]
                  ) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
        """The distinct (TTL, schema) pairs, each as sorted
        ``'<predicate> <object>'`` text: what a listing is matched on."""
        def text(pairs):
            return tuple(sorted({f'{p.predicate} {p.object}' for p in pairs}))
        return text(ttl), text(schema)

    @staticmethod
    def disagrees(ttl: List[CuratedPair], schema: List[CuratedPair]) -> bool:
        """The schema declares external targets and a TTL pair is not one.

        ``ttl`` is every external TTL pair on the slot, slot-level and
        class-scoped (#3053), not only the ones the primary was chosen from.
        """
        if not ttl or not schema:
            return False
        declared = {(p.predicate, p.object) for p in schema}
        return any((p.predicate, p.object) not in declared for p in ttl)

    def _others(self, primary: Optional[CuratedPair],
                curated: List[CuratedPair]) -> List[str]:
        """Every curated pair but the primary (if any), with where it was
        declared.

        A schema pair names the classes that declare it, less any whose
        ancestor declares the same pair: the merged schema repeats an
        inherited attribute on every subclass, and ``id``'s slot_uri would
        otherwise name 78 classes.
        """
        where: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
        for p in curated:
            key = (p.predicate, p.object)
            if primary is not None and key == (primary.predicate, primary.object):
                continue
            places = where.setdefault(key, {}).setdefault(p.source, [])
            if p.where not in places:
                places.append(p.where)
        out = []
        for (predicate, obj), sources in where.items():
            labels = []
            for source in ('ttl', 'schema'):
                places = sources.get(source)
                if places is None:
                    continue
                if '' in places:
                    labels.append(source)
                    continue
                if source == 'schema':
                    places = [c for c in places if not set(places)
                              & set(self.sv.class_ancestors(c)[1:])]
                labels.append(f"{source} {', '.join(sorted(places))}")
            out.append(f"{predicate} {obj} ({'; '.join(labels)})")
        return out

    def disagreement_report(self) -> Dict[str, List[str]]:
        """Slots by how their TTL/schema disagreement is listed, plus stale ones.

        ``changed``: listed, but the pairs that now disagree are not the
        listed ones. ``stale``: listed, and the slot no longer disagrees.
        """
        report = {'accepted': [], 'open': [], 'changed': [], 'unlisted': [],
                  'stale': []}
        for slot, res in self.resolutions.items():
            if res.disagreement:
                report[res.disagreement].append(slot)
        listed = set(ACCEPTED_DISAGREEMENTS) | set(OPEN_DISAGREEMENTS)
        live = (set(report['accepted']) | set(report['open'])
                | set(report['changed']))
        report['stale'] = sorted(listed - live)
        return report

    def warnings(self) -> List[str]:
        """What a run says about TTL/schema disagreements."""
        report = self.disagreement_report()
        out = []
        for slot in report['unlisted']:
            res = self.resolutions[slot]
            out.append(f"TTL and schema disagree on {slot} and it is in neither "
                       f"disagreement list: TTL {res.predicate} {res.object}; "
                       f"others: {' | '.join(res.others)}")
        for slot in report['changed']:
            entry = ACCEPTED_DISAGREEMENTS.get(slot) or OPEN_DISAGREEMENTS[slot]
            (l_ttl, l_schema) = entry.signature()
            (ttl, schema) = self.resolutions[slot].disagreement_pairs
            out.append(
                f"the TTL/schema disagreement on {slot} is not the listed one, "
                f"so its reason may no longer hold: listed TTL "
                f"{' | '.join(l_ttl)} against schema {' | '.join(l_schema)}; "
                f"now TTL {' | '.join(ttl)} against schema "
                f"{' | '.join(schema)}. Re-review the reason and update the "
                "listing")
        for slot in report['stale']:
            out.append(f"{slot} is listed as a TTL/schema disagreement but no "
                       "longer disagrees; remove it from the list")
        for slot in report['open']:
            out.append(f"unsettled TTL/schema disagreement on {slot}: "
                       f"{OPEN_DISAGREEMENTS[slot].reason}")
        return out

    # ------------------------------------------------------------ rows
    def generate_comprehensive_sssom(self, mapping_date: Optional[str] = None
                                     ) -> List[Dict]:
        """Generate comprehensive SSSOM rows for all D4D slots."""
        mapping_date = mapping_date or date.today().isoformat()
        rows = []
        for slot, res in self.resolutions.items():
            # One physical line per row: a description's line breaks would
            # otherwise be written as a quoted multi-line cell.
            desc = ' '.join(res.description.split())
            rows.append({
                'd4d_schema_path': f"{res.path_class}.{slot}" if res.path_class else '',
                'subject_id': f"d4d:{slot}",
                'subject_label': slot.replace('_', ' ').title(),
                'predicate_id': res.predicate,
                'rocrate_json_path': self._get_rocrate_path(res.object),
                'object_id': sssom_object_id(res),
                'object_label': self._object_label(res.object),
                'mapping_justification': res.justification,
                'confidence': res.confidence,
                'comment': '; '.join([res.comment] + res.notes),
                'author_id': '',
                'mapping_tool': mapping_tool(res),
                'mapping_date': mapping_date,
                'subject_source': D4D_NAMESPACE,
                'object_source': self._get_vocab_source(res.object),
                'mapping_set_id': 'd4d-rocrate-comprehensive-v1',
                'mapping_set_version': '2.0',
                'mapping_status': res.status,
                'mapping_source': res.source,
                'other_curated_mappings': ' | '.join(res.others),
                'heuristic_hint': res.hint,
                'd4d_owning_classes': '|'.join(res.owners),
                'd4d_description': desc[:100] + '...' if len(desc) > 100 else desc,
            })
        return rows

    @staticmethod
    def _object_label(uri: str) -> str:
        return uri.split(':', 1)[1] if ':' in uri else uri

    def rocrate_key(self, uri: str) -> str:
        """The key a crate written with the RO-Crate 1.1 context carries
        ``uri``'s IRI under (#3052), in this order:

        1. The context's bare term for another vocabulary's IRI:
           ``conformsTo`` for ``dcterms:conformsTo``, ``wasDerivedFrom`` for
           ``prov:wasDerivedFrom``.
        2. Else, for a schema.org IRI, its local name: the context keys
           schema.org's terms bare. Not where the context binds that name to
           another IRI: the bare ``conformsTo`` is Dublin Core's, so
           ``schema:conformsTo`` goes on to rule 3. The name is not checked
           against the schema.org release the context was built from, so a
           ``schema:`` IRI that release lacks (``schema:measurementMethod``,
           or one schema.org does not define, such as ``schema:example``)
           still gets a bare key the context does not define.
        3. Else a compact IRI on a prefix the context declares:
           ``dct:accessRights``, never ``dcterms:``, which the context does
           not declare.
        4. Else the table's own CURIE (``dcat:byteSize``, ``evi:md5``,
           ``rai:ethicalReview``). The context defines no such key; a crate
           carries it only where its own context declares the prefix, as
           the FAIRSCAPE profile example
           (``data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json``)
           declares ``evi``, ``rai`` and ``d4d``.

        A crate written with another context can use another key for the
        same property: the VOICE FAIRSCAPE crate writes
        ``prov:wasDerivedFrom``. The key named here is the RO-Crate 1.1
        context's.
        """
        prefix, local = uri.split(':', 1) if ':' in uri else ('', uri)
        namespace = self.namespaces.get(prefix)
        if namespace is None:
            return uri
        if namespace in SCHEMA_ORG:
            namespace = SCHEMA_ORG[0]
        iri = namespace + local
        if iri in ROCRATE_CONTEXT_TERMS:
            return ROCRATE_CONTEXT_TERMS[iri]
        if (namespace == SCHEMA_ORG[0]
                and local not in ROCRATE_CONTEXT_TERMS.values()):
            return local
        if namespace in ROCRATE_CONTEXT_PREFIXES:
            return f'{ROCRATE_CONTEXT_PREFIXES[namespace]}:{local}'
        return uri

    def _get_rocrate_path(self, uri: str) -> str:
        """RO-Crate JSON path of the row's object: the Dataset entity's key
        for it, as ``rocrate_key`` names it."""
        if not uri:
            return ''
        return f"@graph[?@type='Dataset']['{self.rocrate_key(uri)}']"

    def _get_vocab_source(self, uri: str) -> str:
        """Namespace IRI of a CURIE, from the TTL's or the schema's prefixes."""
        if not uri or ':' not in uri:
            return ''
        return self.namespaces.get(uri.split(':', 1)[0], 'unknown')

    def _get_confidence(self, predicate: str) -> float:
        """Get confidence based on SKOS predicate."""
        confidence_map = {
            'exactMatch': 1.0,
            'closeMatch': 0.9,
            'relatedMatch': 0.7,
            'narrowMatch': 0.8,
            'broadMatch': 0.8
        }
        return confidence_map.get(predicate, 0.5)

    @staticmethod
    def status_counts(rows: List[Dict]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for row in rows:
            counts[row['mapping_status']] = counts.get(row['mapping_status'], 0) + 1
        return dict(sorted(counts.items()))

    def render_sssom(self, mapping_date: Optional[str] = None) -> str:
        """The comprehensive SSSOM TSV, as the file holds it."""
        mapping_date = mapping_date or date.today().isoformat()
        rows = self.generate_comprehensive_sssom(mapping_date)
        out = io.StringIO()
        out.write('# Comprehensive SSSOM Mapping - ALL D4D Slots\n')
        out.write('# One row per schema slot name. Precedence: SKOS alignment TTL, '
                  'schema slot_uri/*_mappings, URI recommendations, keyword '
                  'heuristics\n')
        out.write(f'# Date: {mapping_date}\n')
        out.write(f'# Total attributes: {len(rows)}\n')
        out.write('#\n')
        out.write('# Status breakdown:\n')
        for status, count in self.status_counts(rows).items():
            out.write(f'#   {status}: {count}\n')
        out.write('#\n')
        writer = csv.DictWriter(out, fieldnames=self.FIELDNAMES,
                                delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        return out.getvalue()

    def write_sssom(self, output_file: Path, mapping_date: Optional[str] = None):
        """Write comprehensive SSSOM TSV."""
        mapping_date = mapping_date or date.today().isoformat()
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            f.write(self.render_sssom(mapping_date))

        rows = self.generate_comprehensive_sssom(mapping_date)
        print(f"✓ Wrote {len(rows)} comprehensive mappings to {output_file}")
        print("\nStatus breakdown:")
        for status, count in self.status_counts(rows).items():
            print(f"  {status}: {count}")


def iso_date(value: str) -> str:
    """argparse type for ``--date``: a YYYY-MM-DD date."""
    return date.fromisoformat(value).isoformat()


def add_common_arguments(parser, output_default: str) -> None:
    """Arguments both comprehensive generators take."""
    parser.add_argument(
        '--schema',
        default='src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        help='D4D schema file'
    )
    parser.add_argument(
        '--skos',
        default='src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl',
        help='SKOS alignment file'
    )
    parser.add_argument(
        '--recommendations',
        default='notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv',
        help='URI recommendations file'
    )
    parser.add_argument('--output', default=output_default,
                        help='Output TSV (the committed file --check compares)')
    parser.add_argument(
        '--date', type=iso_date, default=None,
        help='Mapping date, YYYY-MM-DD (default: today). Everything else in '
             'the output is a function of the inputs.')
    parser.add_argument(
        '--check', action='store_true',
        help="Regenerate in memory under the date the committed --output "
             "records and report any difference. Writes nothing; exits "
             "non-zero on drift.")


def main(argv=None):
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate comprehensive SSSOM for ALL D4D slots'
    )
    add_common_arguments(
        parser,
        'src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv')
    args = parser.parse_args(argv)

    recommendations = Path(args.recommendations)
    generator = ComprehensiveSSSOMGenerator(
        Path(args.schema),
        Path(args.skos),
        recommendations if recommendations.exists() else None
    )
    for warning in generator.warnings():
        print(f"WARNING: {warning}", file=sys.stderr)

    output_file = Path(args.output)
    if args.check:
        pinned = committed_date(output_file) if output_file.exists() else args.date
        return report_drift(output_file, generator.render_sssom(pinned),
                            'subject_id')

    output_file.parent.mkdir(parents=True, exist_ok=True)
    print("\nGenerating comprehensive SSSOM mapping...")
    generator.write_sssom(output_file, args.date)

    print("\n✓ Comprehensive SSSOM generation complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
