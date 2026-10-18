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

## The asymmetry, which is the whole basis of this module

**Absence is evidence; presence is not.** A token absent from every declared
source cannot have been read from one, so `ungrounded` is a real finding.
`grounded` means only that the characters occur somewhere in the corpus, which is
much weaker:

- **Coincidence passes.** `participants: 2025` is "grounded" by a document that
  says "published in 2025". The check has no notion of what the number counts.
- **Correct derivation fails.** A record stating 2,000 participants from a source
  describing "1,000 cases and 1,000 controls" is reported ungrounded, correctly
  by this method's rule and wrongly as a matter of fact.

So the `rate` is *not* an accuracy score, and must not be reported as one. It is
the proportion of stated tokens that could be located, and its useful direction is
downward: a record that drops relative to its peers is asserting things its
sources do not contain. Treat `ungrounded` as a list to read, not a number to
optimise.

This deliberately does not attempt prose. "The dataset addresses a gap in
multimodal voice research" is not checkable this way and is not the target;
`evidence_score.py` covers the schema-fitness question, and neither addresses
whether a claim is *true* in general.

## What is not counted, and which way that biases the rate

Counts below four digits are skipped: in an 80k-token corpus a three-digit
figure matches something almost always, so including them would manufacture
grounding rather than measure it. Accessions cover five prefixes. Both
exclusions shrink the denominator, and both therefore bias the reported rate
*upward* — the check is more forgiving than it looks, not less.

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
import hashlib
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping

# The corpus lookups below are anchored on the checkout (running the CLI
# from a subdirectory tried to open `tests/src/...`); the schema is a
# resource and resolves through `resources.resource_path` when read, so
# an installed package finds its own copy (#1485).
_REPO_ROOT = Path(__file__).resolve().parents[2]
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


def declared_bundle(method: str, label: str, project: str) -> Path | None:
    """The bundle a run actually declared, read from its provenance.

    Not `{project}_preprocessed.txt`. Arms read different inputs — `crate_only`
    reads `{project}_crate_only.txt` — and checking every run against the
    baseline bundle reported the whole crate arm as fabricating everything: 0 of
    5 DOIs, 0 of 11 URLs, 0 of 3 dates on one CHORUS record, for values that are
    presumably in the crate it was given. The provenance already records the
    answer; assuming it was the failure.
    """
    import yaml as _yaml
    from data_sheets_schema.provenance import record_path_for

    from data_sheets_schema.corpus import root
    corpus_root = root()
    rec = record_path_for(project, method, label,
                          corpus_root / "data/d4d_concatenated")
    if not rec.exists():
        return None
    data = _yaml.safe_load(rec.read_text(encoding="utf-8")) or {}
    path = (data.get("inputs") or {}).get("bundle_path")
    if not path:
        return None
    p = Path(path)
    return p if p.is_absolute() else corpus_root / p


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
    from data_sheets_schema.schema_view import shared_view
    return _identifier_slots_of(shared_view(schema_path))


def _identifier_slots_of(sv) -> set[str]:
    """Keep the same identifier/class-reference rule for any selected view."""
    classes = set(sv.all_classes())
    out = {s.name for s in sv.all_slots().values() if s.identifier}
    out |= {s.name for s in sv.all_slots().values() if s.range in classes}
    return out


@dataclass(frozen=True)
class _OwnerSlot:
    exempt_scalar: bool
    target_class: str | None
    multivalued: bool
    keyed: bool
    unsupported: bool


@dataclass(frozen=True)
class _OwnerClass:
    slots: Mapping[str, _OwnerSlot]
    unsupported: bool


@lru_cache(maxsize=8)
def _captured_owner_rules(raw: bytes, kind: str) -> Mapping[str, _OwnerClass]:
    """Immutable induced rules by actual owner; no SchemaView is retained.

    A global slot name cannot distinguish an object reference in one class
    from a literal assertion in another (#4269). Inheritance, slot_usage and
    class-local attributes are resolved before projecting these small rules.
    Conditional ranges and type designators are explicitly unsupported; they
    must not quietly borrow an unrelated owner's identifier exemption.
    """
    from data_sheets_schema.schema_view import version_document, version_view
    from data_sheets_schema.provenance import CORE_SCHEMA
    path = CORE_SCHEMA if kind == "core" else FULL_SCHEMA
    root = "CoreDataset" if kind == "core" else "Dataset"
    with version_view(path, version_document(raw)) as view:
        classes = view.all_classes()
        if root not in classes:
            raise ValueError(f"selected {kind} schema does not declare {root}")
        ranges = set(classes) | set(view.all_types()) | set(view.all_enums())
        constraints = ("any_of", "all_of", "exactly_one_of", "none_of")
        rules = {}
        for name in classes:
            unsupported = any(
                getattr(classes[parent], key, None)
                for parent in view.class_ancestors(name)
                for key in (*constraints, "rules"))
            slots = {}
            for slot in view.class_induced_slots(name):
                target = str(slot.range) if slot.range in classes else None
                slots[str(slot.name)] = _OwnerSlot(
                    exempt_scalar=bool(slot.identifier or target), target_class=target,
                    multivalued=bool(slot.multivalued),
                    keyed=bool(slot.inlined and not slot.inlined_as_list),
                    unsupported=bool(slot.range not in ranges or slot.designates_type or
                                     any(getattr(slot, key, None) for key in constraints)))
            rules[str(name)] = _OwnerClass(MappingProxyType(slots), unsupported)
        return MappingProxyType(rules)


def _pins(section: dict, prefix: str) -> dict[str, str]:
    out = {}
    for algorithm, length in (("sha256", 64), ("md5", 32)):
        name = f"{prefix}_{algorithm}"
        value = section.get(name)
        if value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(rf"[a-fA-F0-9]{{{length}}}", value):
            raise ValueError(f"{name} is not a valid {algorithm} digest")
        out[algorithm] = value.lower()
    return out


def _selected_schema(record: dict, kind: str) -> tuple[Mapping[str, _OwnerClass], dict]:
    from data_sheets_schema.provenance import CORE_SCHEMA
    from data_sheets_schema.resources import resource_path
    from data_sheets_schema.run_schema import TODAY, run_schema_bytes
    if kind not in {"full", "core"}:
        raise ValueError("schema kind must be full or core")
    section = record.get("schema")
    section = {} if section is None else section
    if not isinstance(section, dict):
        raise ValueError("provenance schema must be a mapping")
    pins = _pins(section, kind)
    # Normalize valid hexadecimal case for the existing exact-byte resolver.
    selected_record = {**record, "schema": {**section, **{f"{kind}_{k}": v for k, v in pins.items()}}}
    raw, basis = run_schema_bytes(selected_record, kind=kind)
    if raw is None:
        path = resource_path(CORE_SCHEMA if kind == "core" else FULL_SCHEMA)
        raw = path.read_bytes()
        basis = {**basis, "actual_path": str(path)}
    elif any(getattr(hashlib, algorithm)(raw).hexdigest() != digest for algorithm, digest in pins.items()):
        raise ValueError("recovered schema bytes contradict the recorded hashes")
    # A recovered but unusable historical authority is not a current-schema
    # success. Parsing errors are reported as unchecked by check_run.
    rules = _captured_owner_rules(raw, kind)
    return rules, {**basis, "kind": kind, "actual_sha256": hashlib.sha256(raw).hexdigest(),
                   "status": "current_fallback" if basis["source"] == TODAY else "recorded",
                   "selection_instrument": "verifiable-run-schema-v1",
                   "claim_exclusion_rule": "actual_owner_induced_slots_v1"}


def _owned_claims(document: dict, rules: Mapping[str, _OwnerClass], root: str) -> Iterator[Claim]:
    """Walk only established class/slot ownership, preserving token semantics."""
    def pointer(path, key):
        return path + "/" + str(key).replace("~", "~0").replace("/", "~1")

    def entity(node, owner, path):
        rule = rules[owner]
        if rule.unsupported:
            raise ValueError(f"cannot establish unconditional schema ownership for {owner} at {path or '/'}")
        for name, value in node.items():
            here = pointer(path, name)
            slot = rule.slots.get(name)
            if slot is None:
                raise ValueError(f"unknown schema slot {owner}.{name} at {here}")
            if slot.unsupported:
                raise ValueError(f"unknown/conditional range or type designator at {here}")
            if value is None:
                continue
            if isinstance(value, dict) and slot.multivalued:
                if not slot.keyed or slot.target_class is None:
                    raise ValueError(f"cannot establish keyed-map ownership at {here}")
                # Keys are identifiers of entries, not attributes of the owner.
                for key, member in value.items():
                    if not isinstance(member, dict):
                        raise ValueError(f"keyed-map entry is not an entity at {pointer(here, key)}")
                    yield from entity(member, slot.target_class, pointer(here, key))
                continue
            members = enumerate(value) if isinstance(value, list) else [(None, value)]
            for index, member in members:
                location = pointer(here, index) if index is not None else here
                if isinstance(member, dict):
                    if slot.target_class is None:
                        raise ValueError(f"no class range for nested entity at {location}")
                    yield from entity(member, slot.target_class, location)
                elif isinstance(member, list):
                    raise ValueError(f"no schema owner for nested list at {location}")
                elif not slot.exempt_scalar:
                    # Use the unchanged lexical extractor, explicitly disabling
                    # its historical global-name exclusions for this one value.
                    yield from extract({name: member}, skip_slots=set())

    yield from entity(document, root, "")


def _selected_source(record: dict, provenance: Path, fallback: Path | None) -> tuple[bytes, dict]:
    from data_sheets_schema.backfill_checks import declared_bundle as bundle_path
    from data_sheets_schema.name_grounding import record_bundle_bytes
    inputs = record.get("inputs")
    inputs = {} if inputs is None else inputs
    if not isinstance(inputs, dict):
        raise ValueError("provenance inputs must be a mapping")
    pins = _pins(inputs, "bundle")
    declared = inputs.get("bundle_path") or inputs.get("bundle")
    if declared is not None and (not isinstance(declared, str) or not declared.strip()):
        raise ValueError("declared bundle path must be a nonempty string")
    if pins:
        if not declared:
            raise ValueError("recorded bundle hashes have no declared bundle path")
        normalized = {**record, "inputs": {**inputs, "bundle_path": declared,
                       **{f"bundle_{k}": v for k, v in pins.items()}}}
        raw, basis = record_bundle_bytes(normalized, provenance)
        if raw is None:
            raise ValueError(f"recorded source unavailable: {basis.get('reason', 'no matching bytes')}")
        if any(getattr(hashlib, algorithm)(raw).hexdigest() != digest for algorithm, digest in pins.items()):
            raise ValueError("recovered source bytes contradict the recorded hashes")
        basis = {**basis, "status": "recorded", "recorded_hashes": pins}
    else:
        path = bundle_path(record, provenance) if declared else fallback
        if path is None:
            raise ValueError("no declared or legacy fallback source bundle")
        raw = path.read_bytes()
        basis = {"status": "legacy_current_unverified", "source": "current bundle file",
                 "path": str(path), "reason": "provenance pins no input bundle hash"}
    return raw, {**basis, "actual_sha256": hashlib.sha256(raw).hexdigest(),
                 "actual_md5": hashlib.md5(raw).hexdigest()}


def check_run(record_path: Path, provenance_path: Path, *, kind: str = "full",
              fallback_bundle: Path | None = None, project: str = "", label: str = "") -> dict:
    """Read-only token measurement with independently visible schema/source bases.

    Missing historical schema bytes use a disclosed current-schema fallback.
    Unusable recovered schemas and unavailable/contradictory pinned source
    bytes are unchecked, never zero claims or an implicit current-source score.
    Legacy unpinned sources remain usable only as explicitly unverified files.
    Exemptions follow induced slots of the actual owning class. Unknown slots,
    conditional ownership and unsupported container shapes are unchecked; this
    lexical measurement does not substitute for full schema validation.
    Low-level check_record retains its existing caller-supplied inputs contract.
    """
    import yaml
    from data_sheets_schema.duplicate_keys import find_duplicate_keys, describe

    def mapping(raw, name):
        text = raw.decode("utf-8")
        duplicates = find_duplicate_keys(text, strict=True)
        if duplicates:
            raise ValueError(f"{name}: {describe(duplicates)}")
        value = yaml.safe_load(text)
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a YAML mapping")
        return value

    out = {"project": project, "label": label, "checked": False, "record_path": str(record_path),
           "provenance_path": str(provenance_path), "schema_basis": None, "source_basis": None,
           "stated": None, "grounded": None, "rate": None}
    try:
        raw = record_path.read_bytes()
        out["record_sha256"] = hashlib.sha256(raw).hexdigest()
        document = mapping(raw, "the evaluated record")
        try:
            provenance_raw = provenance_path.read_bytes()
        except FileNotFoundError:
            provenance_raw = None
        out["provenance_sha256"] = hashlib.sha256(provenance_raw).hexdigest() if provenance_raw is not None else None
        provenance = mapping(provenance_raw, "provenance") if provenance_raw is not None else {}
        rules, out["schema_basis"] = _selected_schema(provenance, kind)
        source_raw, out["source_basis"] = _selected_source(provenance, provenance_path, fallback_bundle)
        haystack = normalise_bundle(source_raw.decode("utf-8"))
        assessment = RecordCheck(project=project, label=label)
        for claim in _owned_claims(document, rules, "CoreDataset" if kind == "core" else "Dataset"):
            claim.grounded = any(grounded_in(claim.kind, rendering, haystack)
                                 for rendering in renderings(claim.kind, claim.value))
            assessment.claims.append(claim)
    except (OSError, ValueError, TypeError, RecursionError, yaml.YAMLError) as exc:
        out["reason"] = f"{type(exc).__name__}: {exc}"
        return out
    out.update(checked=True, stated=assessment.stated, grounded=assessment.grounded, rate=assessment.rate,
               claims=[vars(claim).copy() for claim in assessment.claims])
    return out


MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


# Sources abbreviate, and they do not agree on how. PhysioNet writes "Aug. 18,
# 2025" and "Sept. 3, 2025"; Dataverse writes "Aug 18, 2025"; AP style leaves
# March, April, May, June and July unabbreviated. Generating only the full name
# reported 11 dates as invented on the 2026-08-07 sweep that the bundle plainly
# carried -- including all three of the dates the corpus test called this
# check's "first real positive" (#404).
#
# Widening this cannot equate two different dates: a rendering still has to
# carry the same day and year, so the month form is the only thing varying and
# every form here names the same month.
def _month_forms(m: int) -> list[str]:
    full = MONTHS[m - 1].lower()
    forms = [full]
    if len(full) > 3:                      # "may" is already its abbreviation
        stem = full[:3]
        forms += [f"{stem}.", stem]
        if full == "september":            # "sept." is commoner than "sep."
            forms += ["sept.", "sept"]
    return list(dict.fromkeys(forms))


def _ordinal(d: int) -> str:
    """`17` -> `17th`. 11, 12 and 13 take `th` despite ending 1, 2, 3."""
    if 11 <= d % 100 <= 13:
        return f"{d}th"
    return f"{d}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th') }"


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
    if kind == "count":
        return number_renderings(v)
    if kind != "iso_date":
        return [v]
    # Validated as a real calendar date, not merely three numbers. `MONTHS[m-1]`
    # with m == 0 indexes backwards and rendered `2025-00-17` as "December 17,
    # 2025" — an impossible date reported as grounded. `date()` rejects month 0,
    # day 31 in June, and 29 February in a common year alike.
    import datetime
    try:
        parts = [int(x) for x in value.split("-")]
        dt = datetime.date(*parts)
    except (ValueError, TypeError):
        return [v]
    y, m, d = dt.year, dt.month, dt.day
    out = [v]
    for month in _month_forms(m):
        out += [f"{month} {d}, {y}",
                f"{month} {d:02d}, {y}",
                f"{d} {month} {y}",
                f"{d:02d} {month} {y}",
                # Ordinal day. The VOICE IRB protocol writes "January 17th,
                # 2023", which no cardinal rendering matches (#406).
                f"{month} {_ordinal(d)}, {y}",
                f"{_ordinal(d)} {month} {y}"]
    out += [f"{m:02d}/{d:02d}/{y}",
            f"{m}/{d}/{y}",
            f"{y}/{m:02d}/{d:02d}"]
    return list(dict.fromkeys(out))


def normalise(kind: str, value: str) -> str:
    """Reduce a token to the form a source document would plausibly carry.

    Only differences that never change identity: a DOI's resolver prefix, a
    URL's scheme and trailing slash, case. Anything more aggressive would start
    equating tokens that genuinely differ, which is the failure this is meant to
    detect.
    """
    # `:` joined the strip set in #406. `rstrip` stops at the first character
    # not in it, so `10.60775/fairhub.1):` halted on the colon and never
    # reached the `)` — the DOI kept two characters of prose punctuation and
    # could not match. Four values on the 2026-08-07 sweep. A DOI may contain a
    # colon, but only a broken one *ends* with bare punctuation, which is the
    # same trade already accepted for `.`, `;` and `)`.
    v = value.strip().rstrip(".,;:)]").lower()
    # Applied to both kinds, and identically to the bundle. Stripping the
    # resolver from DOIs but not from DOI-shaped URLs made the two sides
    # asymmetric, so `https://doi.org/10.18130/V3/HIGT4C` could never match a
    # bundle that plainly contained it — 27 URLs on CM4AI alone were reported as
    # invented when they were present.
    v = re.sub(r"^https?://", "", v)
    v = re.sub(r"^(?:dx\.)?doi\.org/|^doi:", "", v)
    return v.rstrip("/")


def _is_whole_token(kind: str, text: str, start: int, end: int) -> bool:
    """Is this match a token in its own right, or part of a longer one?

    The same boundary rule `grounded_in` applies to the bundle, applied to the
    record — because the question is the same question. `\\b\\d{4,}\\b` fires
    inside a dotted identifier, so `2024.11.03.621734` yielded the claim
    `621734`, a grant number `2021.0346` yielded `0346`, and `zenodo.17555036`
    yielded `17555036`. None of those is a figure the record asserts; each was
    counted in `stated` and then, correctly, never found (#406).

    That inflated the denominator with tokens that were never claims, which
    biases the reported rate *downward* — the opposite direction to the
    false-negative bugs fixed alongside this, and the reason both had to be
    settled before any rate from this check is quoted.

    Applied to every kind, not just counts: the asymmetry between what is
    extracted and what is looked for is the defect, and it is not specific to
    one pattern.
    """
    before = text[start - 1] if start else ""
    after = text[end] if end < len(text) else ""
    if before and re.fullmatch(_PRECEDES.get(kind, r"\w"), before):
        return False
    # `_CONTINUES` entries may need two characters (`\.\d`), so test the tail.
    if after and re.match(_CONTINUES.get(kind, r"\w"), text[end:]):
        return False
    return True


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
                    if not _is_whole_token(kind, text, m.start(), m.end()):
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
        claim.grounded = any(
            grounded_in(claim.kind, r, haystack)
            for r in renderings(claim.kind, claim.value))
        result.claims.append(claim)
    return result


# A token must not match inside a longer one. `10.1234/x` found inside
# `10.1234/xyz`, or `1234` inside `12345`, reports a fabricated value as
# grounded — the failure this module exists to catch, produced by the module
# itself. Characters that can legitimately continue each kind of token.
# A period is ambiguous: `10.1234/x.5` continues the DOI, `10.1234/x.` ends a
# sentence. So a dot counts as continuation only when a word character follows
# it — otherwise a DOI at the end of a sentence would never be found.
_CONTINUES = {
    "doi": r"(?:[\w/:-]|\.\w)",
    "url": r"(?:[\w/:%?=&#-]|\.\w)",
    "accession": r"[\w-]",
    # A dot continues a count only when a digit follows: `1234.5` is a different
    # quantity, while `1234.` ends a sentence. Same shape as the DOI rule.
    #
    # A comma needs the identical treatment and did not get it (#406). It was
    # `[\d,]`, so any comma continued the number — but a comma is a thousands
    # separator only before a digit. After one it is a delimiter, and the
    # commonest place a figure is followed by a delimiter is JSON:
    # `"size": 3815969779678,`. That rejected every byte count in the FAIRhub
    # API source, 10 values on the 2026-08-07 sweep, each of them plainly
    # present. `1,234,567` must still not be matched by `1234`, which the
    # `,\d` branch preserves.
    "count": r"(?:\d|,\d|\.\d)",
    "iso_date": r"[\d-]",
}
# What may *precede* is narrower than what may follow. A slash is a path
# separator, not part of the token: the VOICE bundle carries
# `zenodo.org/doi/10.5281/zenodo.12760724`, and treating `/` as continuation
# meant a DOI inside a URL path was never found — a real DOI reported as
# invented. Only characters that would make it a *different, longer* identifier
# are excluded.
_PRECEDES = {
    "doi": r"[\w.-]",
    "url": r"[\w.-]",
    "accession": r"[\w-]",
    # Letters too: `v1234` is a version identifier, not the count 1234.
    "count": r"[\w,.]",
    "iso_date": r"[\d-]",
}


def grounded_in(kind: str, rendering: str, haystack: str) -> bool:
    """Is this rendering present as a whole token, not inside a longer one?

    A locator may carry a trailing slash on either side. `normalise` strips it
    from the claim but the bundle is normalised wholesale and keeps it, and `/`
    continues both a URL and a DOI, so `(?!/)` rejected every one a source
    wrote with its trailing slash -- 104 values on the 2026-08-07 sweep, all of
    them present (#404). The optional `/?` restores the symmetry that
    `normalise` intends.

    Applied to `doi` as well as `url`, because `normalise` ends in
    `rstrip("/")` for every kind, so the asymmetry it creates is not specific
    to one. No DOI in the corpus currently trips it -- 0 of 245 measured on the
    2026-08-07 sweep -- so this half is latent, fixed because the defect is the
    same one and finding it twice is worse than fixing it once.

    It does not weaken the boundary guarantee, because the guard still applies
    after it: against `example.com/a/b`, `/?` first consumes the slash and the
    lookahead rejects `b`, then backtracks to empty and the lookahead rejects
    the slash. Both branches fail, which is the required answer. A rendering
    that already ends in `/` is unaffected, since `/?` may match empty.
    """
    after = _CONTINUES.get(kind, r"\w")
    before = _PRECEDES.get(kind, r"\w")
    optional = "/?" if kind in ("url", "doi") else ""
    pat = re.compile(
        rf"(?<!{before}){re.escape(rendering)}{optional}(?!{after})")
    return bool(pat.search(haystack))


def number_renderings(value: str) -> list[str]:
    """A figure as a document might write it, with and without separators.

    `61937` appears in the VOICE bundle as `61,937` and was reported as invented.
    Sources group thousands; records do not.
    """
    digits = value.replace(",", "")
    if not digits.isdigit():
        return [value]
    grouped = f"{int(digits):,}"
    return list(dict.fromkeys([digits, grouped, grouped.replace(",", " ")]))


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
