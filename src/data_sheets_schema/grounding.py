"""Does an identifier appear in the bundle the record was generated from? (#547)

Found reviewing the v4 arm: VOICE rep1 carries 19 external identifiers that
appear nowhere in its input bundle. They are not wrong — `ror.org/032db5x82`
really is the University of South Florida, whose *name* appears 16 times in the
bundle. The run learned the institution from the evidence and supplied its ROR
from model memory.

**This is the hardest form of the fabrication class the provenance guard
exists to prevent: right answer, no evidence.** Checking the value cannot
detect it, because every value is correct. Only checking the source can, and
nothing in the pipeline did:

- `linkml-validate` — a well-formed `uriorcurie` is valid whatever it names;
- `d4d runs identifiers` — a resolvable IRI on a real host is the *best*
  outcome it recognises;
- `d4d_pair_consistency` — compares the pair, not either against the evidence.

Three outcomes, kept apart because collapsing them would make a real and narrow
defect look systematic:

``grounded``
    the bare identifier occurs in the bundle.
``minted_fragment``
    a bundle identifier with a local fragment appended —
    ``doi:10.60775/fairhub.3#split-train``. Legitimate: the base is attested
    and the fragment is ours.
``absent``
    neither. The identifier came from somewhere other than the evidence.

Reported, never fatal, following #520: historical records are annotated rather
than rewritten.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

#: Authorities whose identifiers name something in the world, so a record can
#: only have got one from its evidence or from memory. A locally minted `urn:`
#: or a bare token has no external referent to check against and is out of
#: scope here — `identifiers.classify` already reports on those.
_EXTERNAL = (
    # The fragment is part of the match for all three, not only the DOI: a
    # fragment on a ROR is itself a defect (`…/02r109517#rameau` asserts an
    # organisation and is used to name a person), and a pattern that stopped
    # at the `#` could not see it.
    ("ROR", re.compile(r"(?:https?://)?(?:ror\.org/|ROR:)"
                       r"0[0-9a-hj-km-np-tv-z]{6}[0-9]{2}(?:#[\w.\-]+)?", re.I)),
    ("ORCID", re.compile(r"(?:https?://)?(?:orcid\.org/|ORCID:)"
                         r"\d{4}-\d{4}-\d{4}-\d{3}[\dX](?:#[\w.\-]+)?", re.I)),
    # `#` is inside the match, not a terminator: `doi:10.60775/fairhub.3#split-train`
    # is a bundle DOI with a fragment of ours, and excluding the fragment made
    # every such value read as plainly `grounded` — erasing the distinction
    # this module exists to draw.
    ("doi", re.compile(r"(?:https?://)?(?:doi\.org/|doi:)10\.\d{4,9}/[^\s\"'<>]+",
                       re.I)),
    # ARKs ground like DOIs (#671 review): the classification change stopped
    # counting `ark:` as an invented prefix on the strength of nine
    # bundle-attested ARKs, and without this pattern nothing would have
    # caught a *minted* one — `ground("ark:99999/fake")` returned None, so an
    # unattested ark was neither an undeclared prefix nor `absent`. Now it
    # grounds against the bundle or counts `absent` like any external id.
    ("ark", re.compile(r"(?:https?://[^\s/]+/)?ark:/?\d{5,9}/[^\s\"'<>]+",
                       re.I)),
)

#: A ROR names an organisation. `…/02r109517#rameau` asserts "Weill Cornell
#: Medicine, fragment rameau" and is being used to identify a person — a person
#: needs an ORCID, or a minted id in a namespace of our own.
_ORG_AUTHORITIES = {"ROR"}


def authority(value: str) -> tuple[str, str] | None:
    """(authority, bare identifier) for an external identifier, else None.

    The bare form is what gets looked for in the bundle: a record may write
    `https://ror.org/032db5x82` where the bundle writes `ror.org/032db5x82` or
    `ROR:032db5x82`, and treating those as different identifiers would report
    a grounded value as absent.
    """
    for name, pattern in _EXTERNAL:
        m = pattern.search(value)
        if m:
            text = m.group(0)
            bare = re.sub(r"^(?:https?://)?(?:ror\.org/|orcid\.org/|doi\.org/)",
                          "", text, flags=re.I)
            bare = re.sub(r"^(?:ROR|ORCID|doi):", "", bare, flags=re.I)
            return name, bare
    return None


def ground(value: str, bundle: str) -> tuple[str, str, str] | None:
    """(authority, bare id, status) for an external identifier, else None."""
    found = authority(value)
    if not found:
        return None
    name, bare = found
    # Normalised before anything compares or counts it. DOIs are
    # case-insensitive in the local part by convention and case-varying in
    # practice, so `doi:10.1234/ABC` and `doi:10.1234/abc` were counted as two
    # distinct identifiers (#578).
    bare = bare.lower()
    base = bare.split("#", 1)[0]
    if bare in bundle:
        return name, bare, "grounded"
    if "#" in bare and base in bundle:
        return name, bare, "minted_fragment"
    return name, bare, "absent"


def person_fragment_on_org(value: str) -> bool:
    """A local fragment appended to an organisational identifier.

    Not decidable from the identifier alone — `#split-train` on a DOI is fine —
    so this is limited to authorities that name organisations, where any
    fragment makes the identifier assert something the authority does not.
    """
    found = authority(value)
    if not found:
        return False
    name, bare = found
    return name in _ORG_AUTHORITIES and "#" in bare


def declared_bases() -> list[tuple[str, str]]:
    """(url base, prefix) for every prefix the schema declares with an http base.

    Derived, never restated. The first version hardcoded three hosts while the
    schema declares 38 prefixes with an http base, so a resolver URL for any of
    the other 35 was invisible and adding a prefix did not extend the check —
    the defect of #340, #467 and #563 in a fourth place.

    Longest base first: `https://w3id.org/bridge2ai/standards-dataset-schema/`
    and `https://w3id.org/aio/` share a host, so matching the shorter one first
    would attribute a value to the wrong prefix.
    """
    import yaml

    from data_sheets_schema.provenance import FULL_SCHEMA
    schema = yaml.safe_load(FULL_SCHEMA.read_text(encoding="utf-8")) or {}
    out = []
    for prefix, value in (schema.get("prefixes") or {}).items():
        base = value.get("prefix_reference") if isinstance(value, dict) else value
        if isinstance(base, str) and base.startswith("http"):
            out.append((base.lower(), str(prefix)))
    return sorted(out, key=lambda pair: -len(pair[0]))


def resolver_urls_in_identifier_slots(record: dict[str, Any],
                                      slots: set[str]) -> list[dict[str, str]]:
    """Identifier slots holding a resolver URL where a prefix is declared (#591).

    Distinct from grounding, and invisible to it: `https://doi.org/10.60775/…`
    *is* in the bundle, so it grounds perfectly. What is wrong with it is form,
    not evidence — the schema declares `doi`, so two records naming that DOI in
    the two notations produce two identities.

    The v5 canary wrote 45 of these and passed a gate that measured pair
    consistency, report claims and grounding. None of the three could see the
    rule v5 exists to enforce.
    """
    from data_sheets_schema.identifiers import walk_identifiers

    bases = declared_bases()
    out, seen = [], set()
    for path, slot, value in walk_identifiers(record, slots):
        value = str(value)
        for base, prefix in bases:
            if value.lower().startswith(base) and len(value) > len(base):
                key = (path, value)
                if key in seen:
                    break
                seen.add(key)
                out.append({"kind": "resolver_url_in_identifier_slot",
                            "slot": slot, "path": path, "value": value,
                            "prefix": prefix})
                break
    return out


#: Counted in generated prose only. The American English rule exempts quoted
#: material — a title or a direct quotation keeps its source's spelling — so
#: double-quoted spans are removed before counting. That is the difference
#: between 613 and the ~626 a naive count gives for the v4 arm.
#: The form stems, as documentation of what the patterns below cover. The
#: patterns are the instrument; nothing counts on these strings. (A v1-era
#: comment about "the difference between 613 and ~626" described the quote
#: exemption's effect under the superseded substring instrument.)
BRITISH_FORMS = ("licence", "analyse", "organisation", "enrolment", "programme",
                 "standardis", "labelling", "centre", "recognise", "utilise",
                 "catalogue", "summarise", "behaviour", "colour", "favour",
                 "honour")
#: One pattern per form, word-bounded with explicit inflections (#653).
#:
#: The first instrument did `prose.count(form)`, and its dominant match was
#: "analyses" — the *American* plural of "analysis", substring-matched by
#: `analyse`: 60 of the full v5 arm's 84 counted occurrences (71%), and every
#: counted occurrence in CHORUS and CM4AI. "analyses" is excluded as ambiguous (US
#: noun plural and UK verb alike); the unambiguous British inflections
#: (analysed, analysing, bare analyse) are matched explicitly. `colour`,
#: `favour`, `honour` join the list — a genuinely British "colour fundus" in
#: an AI_READI record was invisible to the old instrument while American
#: "analyses" counted against it.
#: Named so a recompute's audit note says which instrument counted (#907).
BRITISH_INSTRUMENT = "v3 (#836/#859)"
BRITISH_PATTERNS = tuple(re.compile(rx) for rx in (
    # v2.1 (#670 review): the organise verb family — 76 occurrences in the v4
    # arm — had escaped both instruments; bare enrol/enrols, the licenced/
    # licencing misspellings, honourable, and the composed suffixes
    # (favourites, favourably, unfavourable, colourings, organisationally,
    # behaviourally) join it.
    r"\blicenc(?:es?|ed|ing)\b",
    r"\banalys(?:e|ed|ing)\b",
    r"\borganis(?:e|ed|es|ing|ers?|ations?|ational(?:ly)?)\b",
    r"\benrol(?:s|ments?)?\b",
    r"\bprogrammes?\b",
    r"\bstandardis(?:e|ed|es|ing|ations?)\b",
    r"\blabell(?:ing|ed)\b",
    r"\bcentr(?:e|es|ed|ing)\b",
    r"\brecognis(?:e|ed|es|ing)\b",
    r"\butilis(?:e|ed|es|ing|ations?)\b",
    r"\bcatalogu(?:e|es|ed|ing)\b",
    r"\bsummaris(?:e|ed|es|ing)\b",
    r"\bbehaviours?(?:al(?:ly)?)?\b",
    r"\bcolour(?:s|ed|ings?|ful)?\b",
    r"\b(?:un)?favour(?:s|ed|ing|abl[ye]|ites?)?\b",
    r"\bhonour(?:s|ed|ing|able)?\b",
    # v3 (#836, #859): the review pass found tumour/oedema/metres/travelling
    # in a record the instrument scored 0, and the v7 reviewers listed
    # personalised, centimetre, colour, generalisability, artefacts,
    # minimise, totalling, prioritising. The -ise verb family is one
    # pattern; `analyse` stays separate above because of "analyses".
    # Forms with an American homograph (practice, license, specialist,
    # emphasis, cancellation, judgement, program) are excluded or require
    # a suffix that only the British form takes.
    r"\b(?:centi|milli|kilo)?metres?\b",
    r"\btumours?\b",
    r"\boedema(?:tous)?\b",
    r"\bpaediatrics?\b",
    r"\bhaem(?:o\w*|atolog\w*|orrhag\w*)\b",
    r"\banaemi[ac]\b",
    r"\bageing\b",
    r"\btravell(?:ing|ed|ers?)\b",
    r"\bcounsell(?:ing|ed|ors?)\b",
    r"\bcancell(?:ed|ing)\b",
    r"\bmodell(?:ing|ed|ers?)\b",
    r"\btotall(?:ing|ed)\b",
    r"\bartefacts?\b",
    r"\bfibres?\b",
    r"\blitres?\b",
    r"\b(?:neighbour|labour|harbour|humour|vapour|flavour|rumour|armour|endeavour)"
    r"(?:s|ed|ing|hoods?|ous|able)?\b",
    r"\b(?:defence|offence|pretence)s?\b",
    r"\bfulfil(?:s|ment)?\b",
    r"\bpractis(?:e|ed|es|ing)\b",
    r"\bsceptic(?:al|ism|s)?\b",
    r"\bsulphur\w*\b",
    r"\b(?:minimis|maximis|optimis|personalis|generalis|prioritis|characteris|harmonis|"
    r"normalis|anonymis|pseudonymis|visualis|randomis|customis|centralis|finalis|"
    r"stabilis|sterilis|immunis|sensitis|categoris|capitalis|mobilis|realis|specialis|"
    r"emphasis|hypothesis|synthesis|digitis|authoris|criticis|italicis|localis|"
    r"marginalis|neutralis|operationalis|popularis|scrutinis|serialis|symbolis|"
    r"tokenis|vaporis|vocalis|westernis)(?:e|ed|es|ing|ations?|ability|ers?)\b",
))
_QUOTED = re.compile(r'"[^"\n]*"')


def british_spellings(text: str) -> int:
    """Occurrences of British forms in prose the record states (#602, #653).

    Prediction 5 of the v5 plan is measured on this and nothing computed it at
    run time — only `scripts/v5_baselines.py`, after the fact. A prediction the
    gate cannot see is one the gate cannot protect.

    Instrument v2 (#653): word-bounded patterns with explicit inflections.
    Numbers produced by the first instrument (the v4/v5 published notes) are
    not comparable with these; recorded form blocks for both study arms and
    every canary were recomputed under this instrument in the same change, so
    the corpus a gate reads speaks one instrument.

    Instrument v3 (#836, #859): the medical and measurement families
    (tumour, oedema, metre, paediatric, haem-) and the -ise verb family the
    reviews kept finding at 0. Recomputed corpus-wide in the same change,
    by the same discipline: `d4d provenance backfill-checks --blocks form`.
    """
    prose = _QUOTED.sub(" ", text).lower()
    return sum(len(p.findall(prose)) for p in BRITISH_PATTERNS)


#: IANA-registered URN namespace identifiers observed or plausible in this
#: corpus. `uuid` is the only one any record has written (40 occurrences).
URN_REGISTERED_NIDS = frozenset({"uuid", "isbn", "issn", "oid", "ietf",
                                 "doi", "lex"})


#: Schemes the undeclared-prefix metric never counts: `ark` since v2 (#671),
#: `mailto` since v3 (#982). Registered URN NIDs are handled by NID below.
EXCLUDED_SCHEMES = frozenset({"ark", "mailto"})
PREFIX_INSTRUMENT = "v3 (#982): ark and mailto excluded, urn by NID"


def undeclared_prefixes(record: dict[str, Any],
                        slots: set[str]) -> dict[str, int]:
    """`{prefix: occurrences}` for CURIE prefixes the schema does not declare.

    Prediction 4: the invented-prefix population stops growing. `chorus:`,
    `cm4ai:` and friends resolve to nothing, which is why v5's rule three tells
    the model to hang an identifier off an attested one instead of minting a
    namespace.

    Instrument v2 (2026-08-22, refined by the #671 review). The `ark:` scheme
    is not counted: the 2026-08-22c canary wrote nine bundle-attested ARKs
    into `file_collections[].id` — grounded, with minted fragments at zero for
    the first time — and the v1 instrument read the behaviour rules 2 and 3
    exist to produce as nine invented prefixes. An *unattested* ark is still
    caught, by grounding: `_EXTERNAL` grounds arks against the bundle, so a
    minted ark counts `absent`.

    `urn:` is **NID-aware**, not blanket-excluded — the first v2 draft
    excluded the whole scheme and thereby erased 758 corpus occurrences of
    minted namespaces wearing it (`urn:cm4ai:…`, `urn:chorus:…`, `urn:d4d:…`);
    a model switching `cm4ai:x` to `urn:cm4ai:x` would have exited the metric
    entirely. A urn under a registered NID (`urn:uuid:…`) is a real
    identifier; a urn under an invented NID is the same minted namespace the
    metric exists to count, reported as `urn:<nid>`.

    This set deliberately differs from `identifiers.NO_AUTHORITY_SCHEMES`:
    that answers "can this be resolved to an authority?", this answers "did
    someone invent a namespace?" — `mailto:` has no authority yet is not a
    minted namespace problem. Instrument v3 (2026-09-04, #982): it is
    excluded, as this docstring judged in v2 when the corpus had no
    occurrence; the v6 agentic CM4AI rep1 then wrote two and the v8 CM4AI
    canary six, and v2 counted both as invented namespaces. A `mailto:` id
    is the generation-side matter #981 handles; it is not this metric's.
    """
    from data_sheets_schema.identifiers import (declared_prefixes,
                                                walk_identifiers)
    declared = {p.lower() for p in declared_prefixes()}
    out: dict[str, int] = {}
    for _path, _slot, value in walk_identifiers(record, slots):
        text = str(value)
        m = re.match(r"^([A-Za-z][\w.\-]*):(?!//)", text)
        if not m:
            continue
        scheme = m.group(1).lower()
        if scheme in declared or scheme in EXCLUDED_SCHEMES:
            continue
        if scheme == "urn":
            nid = (text.split(":", 2)[1].lower()
                   if text.count(":") >= 2 else "")
            if nid in URN_REGISTERED_NIDS:
                continue
            out[f"urn:{nid}"] = out.get(f"urn:{nid}", 0) + 1
            continue
        out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


#: Address-ish tokens: an alias inside a hostname, path or filename
#: (b2ai-voice.org, voicecollab.ai, data/.../AI_READI_d4d.yaml,
#: AI_READI_preprocessed.txt) is an address, not prose. Slashes and file
#: extensions mark paths; the TLD list covers the hosts the corpus cites.
_URLISH = re.compile(
    r"\S*(?:://|www\.|/|\.org|\.com|\.io|\.gov|\.edu|\.ai|\.net"
    r"|\.yaml|\.txt|\.json|\.csv|\.md|\.pdf)\S*")
#: Header/comment lines. The record header block is pipeline-mandated
#: boilerplate whose {PROJECT} substitution writes the directory key verbatim
#: ("# D4D Datasheet for AI_READI Dataset") — counting it gave the metric a
#: permanent floor no naming rule can lower (#669 review).
_COMMENT_LINE = re.compile(r"^\s*#.*$", re.M)


def gc_label_variants(text: str, canonical: str,
                      variants: list[str]) -> dict[str, int]:
    """Occurrences of non-canonical GC labels in prose the record states (#668).

    The exemption structure mirrors the rule's own carve-outs, as far as text
    can: double-quoted spans are quoted source text; address-shaped tokens
    (URLs, paths, filenames) are identifiers; comment lines are the
    pipeline-mandated header, not model prose. Case-sensitive, because the
    variants differ from the canonical exactly by case and punctuation
    (CHORUS vs CHoRUS), and a case-blind count would count the canonical
    itself.

    Matching is word-bounded with underscore treated as a joining character:
    `Chorus` inside the repository name `Chorus_SOP` and `AI_READI` inside
    `AI_READI_d4d` are parts of identifiers, not prose mentions (#669
    review). Hyphen stays a boundary — the hyphenated long forms are variants
    themselves and are blanked longest-first before shorter forms are
    counted, so "B2AI-VOICE" is never also tallied under "VOICE".

    **What this cannot see**, stated rather than implied: a source-stated
    proper noun in an unquoted slot value (`name: Bridge2AI-Voice`, the
    release's own title) counts, though the rule's carve-outs exempt it. The
    residual is an over-count whose exempt share requires reading the
    matches; use it to compare records under one instrument, not as an
    absolute deviation count.
    """
    prose = _COMMENT_LINE.sub(" ", text)
    prose = _QUOTED.sub(" ", prose)
    prose = _URLISH.sub(" ", prose)
    out: dict[str, int] = {}
    for variant in sorted(variants, key=len, reverse=True):
        if variant == canonical:
            continue
        pattern = re.compile(
            r"(?<![A-Za-z0-9_])" + re.escape(variant) + r"(?![A-Za-z0-9_])")
        n = len(pattern.findall(prose))
        if n:
            out[variant] = n
            prose = pattern.sub(" ", prose)
    return out


def declared_naming(manifest_path: Path | None = None) -> dict[str, Any]:
    """The manifest's `naming:` block, `{}` when absent (#668)."""
    import yaml as _yaml
    path = manifest_path or Path("data/preprocessed/source_manifest.yaml")
    if not path.exists():
        return {}
    data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("naming") or {}


def form_facts(full: Path, core: Path,
               slots: set[str] | None = None) -> dict[str, Any]:
    """Counts that are properties of the records alone (#602).

    Separate from `grounding` deliberately. Grounding compares a record to its
    bundle and declines when the bundle has drifted (#452) — but undeclared
    prefixes, British spellings and organisational fragments need no bundle at
    all, and burying them inside a block that can decline would make three
    preregistered predictions unmeasurable for the 59 records whose bundle has
    moved.
    """
    import yaml as _yaml

    from data_sheets_schema.identifiers import uriorcurie_slots
    slots = slots if slots is not None else uriorcurie_slots()
    prefixes: dict[str, int] = {}
    british = 0
    fragments: set[str] = set()
    present = []
    for path in (full, core):
        if not path.exists():
            continue
        present.append(str(path))
        raw = path.read_text(encoding="utf-8", errors="replace")
        british += british_spellings(raw)
        doc = _yaml.safe_load(raw) or {}
        for prefix, n in undeclared_prefixes(doc, slots).items():
            prefixes[prefix] = prefixes.get(prefix, 0) + n
        from data_sheets_schema.identifiers import walk_identifiers
        for _p, _s, value in walk_identifiers(doc, slots):
            if person_fragment_on_org(str(value)):
                found = authority(str(value))
                if found:
                    fragments.add(found[1].lower())
    if not present:
        return {"checked": False, "reason": "neither record is on disk"}
    # GC label variants (#668): the project is derivable from the record
    # filename ({PROJECT}_d4d.yaml), and a project with no naming declaration
    # contributes nothing rather than failing — absence of a declaration is
    # not a defect in the record.
    label_variants: dict[str, int] = {}
    naming = declared_naming()
    project = full.name.split("_d4d")[0] if full.name else ""
    declared = naming.get(project) or {}
    if declared.get("canonical_label"):
        for path in (full, core):
            if not path.exists():
                continue
            found = gc_label_variants(
                path.read_text(encoding="utf-8", errors="replace"),
                declared["canonical_label"],
                list(declared.get("variants") or []))
            for k, v in found.items():
                label_variants[k] = label_variants.get(k, 0) + v
    return {"checked": True, "records": present,
            "undeclared_prefixes": prefixes,
            "undeclared_prefix_occurrences": sum(prefixes.values()),
            "prefix_instrument": PREFIX_INSTRUMENT,
            "british_spellings": british,
            "organisational_fragments": len(fragments),
            "gc_label_variants": label_variants,
            "gc_label_variant_occurrences": sum(label_variants.values())}


def check_record(record: dict[str, Any], bundle_text: str,
                 slots: set[str]) -> dict[str, Any]:
    """Ground every external identifier in one record against its bundle."""
    from data_sheets_schema.identifiers import walk_identifiers

    counts = {"grounded": 0, "minted_fragment": 0, "absent": 0}
    findings: list[dict[str, str]] = []
    lowered = bundle_text.lower()
    seen: set[tuple[str, ...]] = set()
    for path, _slot, value in walk_identifiers(record, slots):
        result = ground(value, lowered)
        if not result:
            continue
        name, bare, status = result
        counts[status] += 1
        if status == "absent" and (path, bare, "abs") not in seen:
            seen.add((path, bare, "abs"))
            findings.append({"kind": "identifier_not_in_bundle",
                             "authority": name, "identifier": bare,
                             "path": path})
        if person_fragment_on_org(value) and (path, bare, "frag") not in seen:
            seen.add((path, bare, "frag"))
            findings.append({"kind": "fragment_on_org_identifier",
                             "authority": name, "identifier": bare,
                             "path": path})
    # Occurrences and distinct identifiers are both reported. The first says
    # how much of the record rests on unattested values; the second says how
    # many facts are at issue. Reporting only occurrences turned 7 identifiers
    # that appear in both records into "14", and reporting only distinct hides
    # that one bad id can carry 20 slots.
    distinct = {"grounded": set(), "minted_fragment": set(), "absent": set()}
    for path, _slot, value in walk_identifiers(record, slots):
        r = ground(value, lowered)
        if r:
            distinct[r[2]].add(r[1])
    return {"checked": True, "counts": counts,
            "distinct": {k: len(v) for k, v in distinct.items()},
            "findings": findings}


def iter_external(record: dict[str, Any], slots: set[str]
                  ) -> Iterator[tuple[str, str, str]]:
    """(path, authority, bare id) for every external identifier in a record."""
    from data_sheets_schema.identifiers import walk_identifiers
    for path, _slot, value in walk_identifiers(record, slots):
        found = authority(value)
        if found:
            yield path, found[0], found[1]


def check_run(full: Path, core: Path, bundle: Path,
              slots: set[str] | None = None) -> dict[str, Any]:
    """Both records of a run, against the bundle it declares."""
    import yaml

    from data_sheets_schema.identifiers import uriorcurie_slots
    if not bundle.exists():
        return {"checked": False, "reason": f"bundle absent: {bundle}"}
    slots = slots if slots is not None else uriorcurie_slots()
    # Both records absent read as `checked: true` with three zeroes, which
    # `runs check` reported as fully grounded (#578). Zero identifiers found in
    # a file that is not there is not a measurement — the same distinction
    # `pair_consistency` draws with `ran: false`, missed here.
    missing = [str(p) for p in (full, core) if not p.exists()]
    if len(missing) == 2:
        return {"checked": False,
                "reason": f"neither record is on disk: {', '.join(missing)}"}
    text = bundle.read_text(encoding="utf-8", errors="replace")
    out: dict[str, Any] = {"checked": True,
                           "counts": {"grounded": 0, "minted_fragment": 0,
                                      "absent": 0},
                           "findings": []}
    # Distinct is taken over the *pair*, not summed per record: the same
    # identifier in both files is one identifier, and summing made VOICE rep1's
    # 7 organisational fragments read as 14.
    pooled: dict[str, set] = {"grounded": set(), "minted_fragment": set(),
                              "absent": set()}
    for which, path in (("full", full), ("core", core)):
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        r = check_record(doc, text, slots)
        for key, n in r["counts"].items():
            out["counts"][key] += n
        for f in r["findings"]:
            out["findings"].append({**f, "record": which})
        for f in resolver_urls_in_identifier_slots(doc, slots):
            out["findings"].append({**f, "record": which})
        doc_ids = doc
        from data_sheets_schema.identifiers import walk_identifiers
        for _p, _s, value in walk_identifiers(doc_ids, slots):
            g = ground(value, text.lower())
            if g:
                pooled[g[2]].add(g[1])
    out["distinct"] = {k: len(v) for k, v in pooled.items()}
    return out
