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
    import re as _re

    from data_sheets_schema.identifiers import declared_prefixes, walk_identifiers
    declared = {p.lower() for p in declared_prefixes()}
    hosts = {"doi.org": "doi", "ror.org": "ror", "orcid.org": "orcid"}
    out = []
    for path, slot, value in walk_identifiers(record, slots):
        value = str(value)
        m = _re.match(r"^https?://(?:www\.)?([^/]+)/", value)
        if not m:
            continue
        prefix = hosts.get(m.group(1).lower())
        if prefix and prefix in declared:
            out.append({"kind": "resolver_url_in_identifier_slot",
                        "slot": slot, "path": path, "value": value,
                        "prefix": prefix})
    return out


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
