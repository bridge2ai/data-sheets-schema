"""Check the values a record states against the documents it was given.

The surviving half of #165. Agreement between replicates measures
self-consistency: a prompt that reliably produces the same wrong answer scores
perfectly. The obvious remedy — compare against `curated` as a gold standard — is
refuted, because those records were ChatGPT-generated and document superseded
releases (#177). So correctness has to be grounded in something else.

Some values can be checked without any reference record at all. A DOI, an
accession, a participant count, a release date: these are tokens that must appear
*literally* in a source document, because that is where they came from. If a
record states `10.13026/249v-w155` and no input document contains it, the record
invented it — and no comparison with another record was needed to know that.

This deliberately does not attempt prose. "The dataset addresses a gap in
multimodal voice research" is not checkable this way and is not the target;
`evidence_score.py` covers the schema-fitness question, and neither addresses
whether a claim is *true* in general.

## Why identifiers are excluded

Measured on VOICE: `id` holds 181 URLs of which 7 appear in the bundle (4%);
every other URL-bearing slot runs 80-100%. `id` is a *constructed* identifier —
LinkML requires one and the generator mints it — so checking it against the
source would report 174 fabrications that are nothing of the kind. The exclusion
is read from the schema (`identifier: true`), not hardcoded, so a schema that
marks another slot as an identifier is handled without changing this file.

## The denominator trap

A record that states nothing is trivially correct on everything it states. So
:func:`check_record` reports ``stated`` alongside ``grounded``, and no caller
should read the ratio without the count. The same trap is written into
`notes/generic_v2_analysis_plan.md`, and it is the reason the metric here is a
pair rather than a percentage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")

# Token kinds that must appear verbatim in a source document if they are real.
# Deliberately narrow: each is a string a human copied from somewhere, not a
# phrasing the model could reasonably vary.
PATTERNS: dict[str, re.Pattern] = {
    "doi": re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+"),
    "url": re.compile(r"https?://[^\s'\"<>)]+"),
    "iso_date": re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    # Four digits or more. Below that, coincidental matches in unrelated text
    # swamp the signal — "3 sites" appears in almost any corpus.
    "count": re.compile(r"\b\d{4,}\b"),
    "accession": re.compile(r"\b(?:GSE|SRR|PRJNA|SAMN|E-MTAB-)\d+\b"),
}


@dataclass
class Claim:
    """One checkable token, and where the record states it."""

    kind: str
    value: str
    slot: str
    grounded: bool | None = None      # None until checked

    @property
    def normalised(self) -> str:
        return normalise(self.kind, self.value)


@dataclass
class RecordCheck:
    project: str
    label: str
    claims: list[Claim] = field(default_factory=list)

    @property
    def stated(self) -> int:
        return len(self.claims)

    @property
    def grounded(self) -> int:
        return sum(1 for c in self.claims if c.grounded)

    @property
    def ungrounded(self) -> list[Claim]:
        return [c for c in self.claims if c.grounded is False]

    @property
    def rate(self) -> float | None:
        """Fraction grounded — **meaningless without `stated`**.

        Returns None rather than 1.0 for a record that states nothing, so a
        caller cannot accidentally rank an empty record top.
        """
        return (self.grounded / self.stated) if self.stated else None

    def by_kind(self) -> dict[str, tuple[int, int]]:
        out: dict[str, list[int]] = {}
        for c in self.claims:
            slot = out.setdefault(c.kind, [0, 0])
            slot[0] += 1
            slot[1] += 1 if c.grounded else 0
        return {k: (v[0], v[1]) for k, v in out.items()}


def identifier_slots(schema_path: Path = FULL_SCHEMA) -> set[str]:
    """Slots whose string values are constructed identifiers, not assertions.

    Two kinds, both read from the schema rather than listed here:

    - slots marked ``identifier: true`` — `id`;
    - **class-ranged slots**. When a slot's range is a class, a bare string in
      it is a reference to an instance, not a literal claim. The generator mints
      those URIs: `principal_investigator: https://b2ai-voice.org/person/
      bensoussan-yael` is a `Person` reference, and demanding it appear in a
      source document reported 17 fabrications on one VOICE record that were
      nothing of the kind.

    A dict in such a slot is still walked — the *fields inside* a nested Person
    are ordinary assertions. Only the identifier string is exempt.
    """
    from linkml_runtime import SchemaView
    sv = SchemaView(str(schema_path))
    classes = set(sv.all_classes())
    out = {s.name for s in sv.all_slots().values() if s.identifier}
    out |= {s.name for s in sv.all_slots().values() if s.range in classes}
    return out


MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


def renderings(kind: str, value: str) -> list[str]:
    """Every spelling a source document might plausibly use for one token.

    Dates are the case that forced this. A record states `2025-01-17` while the
    document says "January 17, 2025" — the same fact, and a single normalised
    form counted it as fabricated. Measured on VOICE that misreported 17 dates,
    which would have been published as invented values.

    Checking several renderings is more honest than rewriting the bundle into a
    canonical form: it makes the accepted variation explicit and enumerable,
    where a bundle-wide rewrite hides which transformations were applied.
    """
    v = normalise(kind, value)
    if kind != "iso_date":
        return [v]
    try:
        y, m, d = (int(x) for x in value.split("-"))
        month = MONTHS[m - 1]
    except (ValueError, IndexError):
        return [v]
    return [v,
            f"{month} {d}, {y}".lower(),
            f"{month} {d:02d}, {y}".lower(),
            f"{d} {month} {y}".lower(),
            f"{d:02d} {month} {y}".lower(),
            f"{month} {y}".lower(),          # month precision in the source
            f"{m:02d}/{d:02d}/{y}",
            f"{m}/{d}/{y}",
            f"{y}/{m:02d}/{d:02d}"]


def normalise(kind: str, value: str) -> str:
    """Reduce a token to the form a source document would plausibly carry.

    Only differences that never change identity: a DOI's resolver prefix, a
    URL's scheme and trailing slash, case. Anything more aggressive would start
    equating tokens that genuinely differ, which is the failure this is meant to
    detect.
    """
    v = value.strip().rstrip(".,;)]").lower()
    # Applied to both kinds, and identically to the bundle. Stripping the
    # resolver from DOIs but not from DOI-shaped URLs made the two sides
    # asymmetric, so `https://doi.org/10.18130/V3/HIGT4C` could never match a
    # bundle that plainly contained it — 27 URLs on CM4AI alone were reported as
    # invented when they were present.
    v = re.sub(r"^https?://", "", v)
    v = re.sub(r"^(?:dx\.)?doi\.org/|^doi:", "", v)
    return v.rstrip("/")


def extract(record: dict[str, Any], *,
            skip_slots: set[str] | None = None) -> Iterator[Claim]:
    """Every checkable token in a record, with the slot that states it."""
    skip = skip_slots if skip_slots is not None else identifier_slots()

    def walk(node: Any, slot: str = "") -> Iterator[Claim]:
        if isinstance(node, dict):
            for k, v in node.items():
                # A class-ranged slot holding a *string* is an identifier
                # reference; the same slot holding a dict is a nested object
                # whose fields are ordinary assertions and must still be checked.
                if k in skip and not isinstance(v, (dict, list)):
                    continue
                if k in skip and isinstance(v, list) and all(
                        not isinstance(x, dict) for x in v):
                    continue
                yield from walk(v, k)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v, slot)
        elif isinstance(node, (str, int, float)):
            text = str(node)
            # Deduplicated by *span*, not by value. Specific kinds are matched
            # first and the characters they consume are withheld from the rest:
            # `https://doi.org/10.x/y` matches the URL pattern too, and
            # `10.13026/249v-w155` contains `13026`, which the count pattern
            # would claim as a separate figure. Both inflated `stated` and
            # depressed the rate by counting one fact twice — once grounded and
            # once not. Value-level dedup does not catch the second case,
            # because the two tokens normalise differently.
            taken: list[tuple[int, int]] = []

            def _overlaps(a: int, b: int) -> bool:
                return any(a < end and start < b for start, end in taken)

            for kind in ("accession", "doi", "url", "iso_date", "count"):
                for m in PATTERNS[kind].finditer(text):
                    if _overlaps(m.start(), m.end()):
                        continue
                    taken.append((m.start(), m.end()))
                    yield Claim(kind=kind, value=m.group(),
                                slot=slot or "(root)")

    yield from walk(record)


def check_record(record: dict[str, Any], bundle: str, *,
                 project: str = "", label: str = "",
                 skip_slots: set[str] | None = None) -> RecordCheck:
    """Which of a record's checkable tokens appear in the bundle it declared."""
    haystack = normalise_bundle(bundle)
    result = RecordCheck(project=project, label=label)
    for claim in extract(record, skip_slots=skip_slots):
        claim.grounded = any(r in haystack
                             for r in renderings(claim.kind, claim.value))
        result.claims.append(claim)
    return result


def normalise_bundle(bundle: str) -> str:
    """The bundle in the same normalised form the claims are reduced to.

    Built once per check rather than per claim: a record states hundreds of
    tokens and the bundle runs to 80k+ tokens, so normalising it repeatedly is
    the difference between a second and a minute.
    """
    t = bundle.lower()
    t = re.sub(r"https?://", "", t)
    t = re.sub(r"(?:dx\.)?doi\.org/|doi:", "", t)
    return t
