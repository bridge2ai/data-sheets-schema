"""Deterministic, offline source-review packs (E2; #3280/#1782/#1801/#1815).

The reviewer directory contains only ``blind_*.yaml`` and ``review_sheet.tsv``.
Its separate private key must be written outside that directory and never
distributed. File permissions are local access controls, not encryption.

Selection is explicit. This prepares review materials, not scientific approval,
generation acceptance, or proof that source content cannot reveal its origin.
Scientific strings are never redacted. Ambiguous provenance or an identifier
remaining in source text causes refusal and requires explicit blinding review.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
import tempfile
from typing import Iterable
import unicodedata

import yaml

from data_sheets_schema.cross_family_panel_analysis import _rename_new, _sync_directory
from data_sheets_schema.evaluation import registered_eval_runner as registered
from data_sheets_schema.evaluation_context import unwrap_document

FORMAT = "blind_source_review_pack_v1"
BLINDING_VERSION = "identity_aware_sorted_v1"
FINGERPRINT_NOTICE = (
    "Reviewer copies preserve scientific wording. Slot structure, size, spelling, process prose, content origin, "
    "and matching against public source text can still reveal a generation arm. Counts are "
    "textual hints, not arm attribution or proof of blinding; zero is not assurance. Keep "
    "new outputs unpublished until blinded review completes. Historical public records "
    "cannot be made secret by this pack."
)
REVIEW_COLUMNS = (
    "blind_id", "project", "reviewer", "accuracy_score", "completeness_score",
    "hallucination_count", "omission_notes", "verdict",
)
MAX_RECORDS = 1000
MAX_PACK_BYTES = 128_000_000
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_WRAPPERS = frozenset({"Dataset", "CoreDataset", "DatasetCollection", "CoreDatasetCollection"})
_MODEL_KEYS = frozenset({"generator_model", "generation_model", "model", "model_selector"})
_METADATA_KEYS = registered._ENVELOPE_KEYS | {
    "generator_model", "generation_model", "generation_provenance", "generation_arm",
}
_GENERATION_PROVENANCE_KEYS = frozenset({
    "record_type", "run", "inputs", "outputs", "model", "prompts", "schema", "validation",
    "shared_generation", "run_observed", "profile", "profile_basis", "generation_method",
})
_HEADER = re.compile(
    r"^#\s*(?:arm|label|run[ _]label|model|generator[ _]model|generation[ _]model|"
    r"source(?:[ _](?:bundle|manifest|path))?|prompt|schema|input[ _]path|output[ _]path)"
    r"\s*:\s*(.*?)\s*$", re.IGNORECASE,
)
_MODEL_LITERAL = re.compile(
    r"\b(?:claude-[\w.\[\]-]+|gpt-[\w.-]+|gemini-[\w.-]+|"
    r"(?:meta-)?llama[- ][\w.-]+|deepseek-[\w.-]+)\b", re.IGNORECASE,
)
_CRATE_WORD = re.compile(r"\b(?:ro[- ]?)?crates?\b", re.IGNORECASE)


def _canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _text(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError(f"{name} requires a nonempty string of at most 4096 characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{name} cannot contain control characters")
    return value


@dataclass(frozen=True)
class Record:
    """One explicit selection; ``source_sha256`` optionally pins input bytes."""

    arm: str
    project: str
    label: str
    source_path: Path
    source_sha256: str | None = None
    input_arm: str | None = None

    def __post_init__(self):
        for name in ("arm", "project", "label"):
            _text(getattr(self, name), name)
        for name in ("arm", "label"):
            value = getattr(self, name)
            if value != value.strip() or not _fold_identity(value):
                raise ValueError(f"{name} cannot have surrounding whitespace or an empty folded identity")
        if len(_fold_identity(self.arm)) < 2:
            raise ValueError("arm requires at least 2 non-whitespace characters")
        folded_arm = _fold_identity(self.arm)
        if not folded_arm[0].isalnum() or not folded_arm[-1].isalnum():
            raise ValueError("arm cannot have edge punctuation")
        if not isinstance(self.source_path, (str, os.PathLike)):
            raise ValueError("source_path must be a filesystem path")
        object.__setattr__(self, "source_path", Path(_text(str(self.source_path), "source_path")))
        if self.source_sha256 is not None and (
                not isinstance(self.source_sha256, str) or not _SHA.fullmatch(self.source_sha256)):
            raise ValueError("source_sha256 must be a lowercase SHA256 digest")

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.arm, self.project, self.label


def parse_record(value: str) -> Record:
    """Parse ``ARM:PROJECT:LABEL=PATH`` without interpreting shell syntax."""
    try:
        identity, path = value.split("=", 1)
        arm, project, label = identity.split(":", 2)
    except ValueError as exc:
        raise ValueError("record must be ARM:PROJECT:LABEL=PATH") from exc
    return Record(arm, project, label, Path(_text(path, "source_path")))


def read_manifest(path: Path) -> list[Record]:
    """Read strict JSON-compatible YAML/JSON; relative paths use its directory.

    Shape: ``{"records": [{"arm": ..., "project": ..., "label": ...,
    "source_path": ..., "source_sha256": optional_sha256}, ...]}``.
    """
    path = Path(path)
    raw = registered._read(path)
    value = registered._json(raw) if path.suffix.lower() == ".json" else registered._yaml(raw)
    if not isinstance(value, dict) or set(value) != {"records"} or not isinstance(value["records"], list):
        raise ValueError("manifest must contain exactly one records list")
    records = []
    for entry in value["records"]:
        required = {"arm", "project", "label", "source_path"}
        if not isinstance(entry, dict) or not required <= set(entry) or set(entry) - required - {"source_sha256"}:
            raise ValueError("manifest record requires arm, project, label, source_path and optional source_sha256")
        source = Path(_text(entry["source_path"], "source_path"))
        if not source.is_absolute():
            source = path.absolute().parent / source
        records.append(Record(entry["arm"], entry["project"], entry["label"], source,
                              entry.get("source_sha256")))
    return records


def validate_cohort(records: Iterable[Record], *, cohort: str = "campaign", cohort_manifest=None) -> list[Record]:
    records = list(records)
    if not records or len(records) > MAX_RECORDS or not all(isinstance(record, Record) for record in records):
        raise ValueError(f"select 1..{MAX_RECORDS} explicit Record entries")
    if len({record.identity for record in records}) != len(records):
        raise ValueError("duplicate arm/project/label selection")
    if cohort not in {"campaign", "synthetic"}:
        raise ValueError("cohort must be campaign or synthetic")
    if cohort == "campaign":
        from .cohort_manifest import read_cohort
        if cohort_manifest is None:
            raise ValueError("campaign requires a declared cohort manifest")
        declared, _ = read_cohort(cohort_manifest)
        if {r.identity for r in records} != {(r["arm"], r["project"], r["label"]) for r in declared}:
            raise ValueError("selection differs from the declared cohort")
    return sorted(records, key=lambda record: record.identity)


def _strings(value):
    """Read keys as well as values; safe only after the strict acyclic parser."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _metadata_identifiers(value) -> set[str]:
    """Collect exact identifiers without treating all metadata prose as IDs."""
    found = set()
    if isinstance(value, list):
        for item in value:
            found.update(_metadata_identifiers(item))
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _MODEL_KEYS | _METADATA_KEYS | {"arm", "label", "path"} and isinstance(item, str):
                if item:
                    found.add(item)
            if key in _MODEL_KEYS and isinstance(item, list):
                if any(not isinstance(entry, str) or not entry for entry in item):
                    raise ValueError("ambiguous model metadata; explicit blinding review required")
                found.update(item)
            elif key in _MODEL_KEYS and item is not None and not isinstance(item, str):
                raise ValueError("ambiguous model metadata; explicit blinding review required")
            if isinstance(item, (list, dict)):
                found.update(_metadata_identifiers(item))
    return found


def _strip(raw: bytes, record: Record) -> tuple[bytes, set[str]]:
    # Reuse the existing strict parser and final comment/envelope stripper.
    document = registered._yaml(raw)
    if not isinstance(document, dict):
        raise ValueError("blind review input must be a Dataset mapping")
    identifiers = set()
    # Column-zero metadata comments can occur anywhere, including after keys.
    # Token spans distinguish real comments from '# Model:' text inside a
    # quoted multiline scalar or literal block. Never treat scientific strings
    # as controller metadata merely because they resemble a comment header.
    source = raw.decode("utf-8-sig")
    spans = iter((token.start_mark.index, token.end_mark.index)
                 for token in yaml.scan(source)
                 if isinstance(token, yaml.tokens.ScalarToken) and token.style is not None)
    span = next(spans, None)
    offset = 0
    for line in source.splitlines(keepends=True):
        while span is not None and span[1] <= offset:
            span = next(spans, None)
        inside_scalar = span is not None and span[0] <= offset < span[1]
        match = _HEADER.match(line)
        if not inside_scalar and match and match[1]:
            identifiers.add(match[1])
        offset += len(line)

    def clean_envelope(mapping):
        clean = {}
        for key, item in mapping.items():
            if key in _METADATA_KEYS:
                identifiers.update(_metadata_identifiers({key: item}))
                continue
            if key == "arm":
                if item not in (record.arm, record.input_arm):
                    raise ValueError("ambiguous root arm; explicit blinding review required")
                continue
            if key == "label" and item == record.label:
                continue
            if key == "provenance":
                if (isinstance(item, dict) and item.get("record_type") == "d4d_generation_provenance"
                        and set(item) <= _GENERATION_PROVENANCE_KEYS):
                    identifiers.update(_metadata_identifiers(item))
                    continue
                raise ValueError("ambiguous scientific provenance; explicit blinding review required")
            if key in {"model", "model_selector"}:
                raise ValueError("ambiguous root model; explicit blinding review required")
            clean[key] = item
        return clean

    document = clean_envelope(document)
    unwrap_document(document)
    wrappers = set(document) & _WRAPPERS
    if wrappers:
        wrapper = next(iter(wrappers))
        document[wrapper] = clean_envelope(document[wrapper])

    def inspect_nested(value):
        if isinstance(value, dict):
            if set(value) & (_METADATA_KEYS | {"provenance", "arm", "model", "model_selector"}):
                raise ValueError("nested provenance or generation metadata needs explicit blinding review")
            for item in value.values():
                inspect_nested(item)
        elif isinstance(value, list):
            for item in value:
                inspect_nested(item)

    inspect_nested(document)
    blinded = registered.blind_record(yaml.safe_dump(document, sort_keys=True, allow_unicode=True).encode())
    return blinded, identifiers


def _fingerprints(blinded: bytes) -> dict:
    """Count hints in each decoded scientific string, never across strings."""
    from data_sheets_schema.grounding import BRITISH_INSTRUMENT, BRITISH_PATTERNS

    document = unwrap_document(registered._yaml(blinded))
    strings = list(_strings(document))
    paths = _key_paths(document)
    return {
        "top_level_slots": sorted(document), "key_paths": paths,
        "key_path_count": len(paths), "blinded_bytes": len(blinded),
        "british_form_occurrences": sum(
            len(pattern.findall(text.lower())) for text in strings for pattern in BRITISH_PATTERNS
        ),
        "british_instrument": BRITISH_INSTRUMENT,
        "british_patterns_sha256": _sha(_canonical([pattern.pattern for pattern in BRITISH_PATTERNS])),
        "crate_word_occurrences": sum(len(_CRATE_WORD.findall(text)) for text in strings),
        "counting_basis": "decoded scientific string keys and values, separately; repeated occurrences count",
        "british_basis": "BRITISH_PATTERNS applied to lowercase strings, including quoted scientific text",
        "crate_basis": "case-insensitive Unicode word-boundary matches for crate/crates, RO-Crate, RO Crate, ROCrate",
    }


def _key_paths(value, prefix=()):
    """Unique mapping paths, with typed steps and list positions collapsed."""
    paths = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = (*prefix, ("key", key))
            paths.add(json.dumps(path, ensure_ascii=False, separators=(",", ":")))
            paths.update(_key_paths(child, path))
    elif isinstance(value, list):
        for child in value:
            paths.update(_key_paths(child, (*prefix, ("item",))))
    return sorted(paths)


def _separability(entries):
    """Descriptive per-project arm contrasts; no content changes or approval."""
    from itertools import combinations
    result = {}
    for project in sorted({r["project"] for r in entries}):
        groups = {}
        for entry in entries:
            if entry["project"] == project:
                groups.setdefault(entry["arm"], []).append(entry["fingerprint_diagnostics"])
        comparisons = []
        for left, right in combinations(sorted(groups), 2):
            paths = {arm: [set(r["key_paths"]) for r in groups[arm]] for arm in (left, right)}
            exclusive = {arm: sorted(set.intersection(*paths[arm]) - set.union(*paths[other]))
                         for arm, other in ((left, right), (right, left))}
            sizes = {arm: [min(r["blinded_bytes"] for r in groups[arm]),
                           max(r["blinded_bytes"] for r in groups[arm])] for arm in (left, right)}
            comparisons.append({"arms": [left, right], "record_counts": {a: len(groups[a]) for a in (left, right)},
                "exclusive_key_paths": exclusive, "key_path_separable": any(exclusive.values()),
                "blinded_size_ranges": sizes,
                "size_ranges_overlap": max(sizes[left][0], sizes[right][0]) <= min(sizes[left][1], sizes[right][1])})
        result[project] = {"status": "descriptive_only" if comparisons else "insufficient_comparison_arms",
                           "comparisons": comparisons}
    return result


def _fold_identity(value):
    return "".join(char for char in unicodedata.normalize("NFKC", value)
                   if unicodedata.category(char) != "Cf").casefold()


def _identifier_leaked(ident_folded: str, text_folded: str) -> bool:
    """Short IDs require boundaries outside Unicode letters/numbers/marks.

    Punctuation and underscores remain delimiters. Longer identifiers retain
    exact case-folded substring matching; no source text is normalized away.
    """
    ident_folded, text_folded = _fold_identity(ident_folded), _fold_identity(text_folded)
    if not ident_folded:
        return False
    if len(ident_folded) < 4:
        def word_character(char):
            return char.isalnum() or unicodedata.category(char).startswith("M")

        for match in re.finditer("(?=" + re.escape(ident_folded) + ")", text_folded):
            start, end = match.start(), match.start() + len(ident_folded)
            if ((start == 0 or not word_character(text_folded[start - 1]))
                    and (end == len(text_folded) or not word_character(text_folded[end]))):
                return True
        return False
    return ident_folded in text_folded


def _leakage(raw: bytes, forbidden: set[str], *, yaml_document: bool = False):
    text = raw.decode("utf-8")
    strings = [text]
    if yaml_document:
        strings.extend(_strings(registered._yaml(raw)))
    folded = [_fold_identity(item) for item in strings]
    if any(
        _identifier_leaked(identifier, item)
        for identifier in forbidden
        if identifier
        for item in folded
    ):
        raise ValueError("generation identity remains in reviewer content; explicit blinding review required")
    if any(_MODEL_LITERAL.search(item) for item in folded):
        raise ValueError("generator model identifier remains in reviewer content; explicit blinding review required")


def _identity_blind(raw: bytes, record: Record, forbidden=()) -> tuple[bytes, set[str]]:
    if not isinstance(record, Record) or not isinstance(raw, bytes):
        raise ValueError("blinding requires captured bytes and an explicit Record identity")
    if record.source_sha256 is not None and _sha(raw) != record.source_sha256:
        raise ValueError("selected source_sha256 does not match input")
    identifiers = set(forbidden)
    if any(not isinstance(item, str) for item in identifiers):
        raise ValueError("forbidden blinding identifiers must be strings")
    blinded, metadata_ids = _strip(raw, record)
    if record.input_arm is not None:
        metadata_ids.discard(record.input_arm)
    identifiers.update((record.arm, record.label, str(record.source_path)))
    identifiers.update(metadata_ids)
    _leakage(blinded, identifiers, yaml_document=True)
    return blinded, metadata_ids


def blind_input(raw: bytes, record: Record, *, forbidden=()) -> bytes:
    """Apply the pack's identity-aware gate without reading any source path.

    The caller supplies the actual registered or selected identity. Campaign
    labels are never inferred from models, conditions, filenames or source
    metadata; an inconsistent root/wrapper arm requires explicit review.
    """
    return _identity_blind(raw, record, forbidden)[0]


def _timestamp(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError("generated_at must be an explicit UTC timestamp YYYY-MM-DDTHH:MM:SSZ")
    datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return value


def _write(path: Path, raw: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _new_destination(path: Path, label: str) -> Path:
    if path.exists() or path.is_symlink():
        raise ValueError(f"{label} already exists; never overwrite a review package or key")
    if not path.parent.is_dir() or path.name in {"", ".", ".."}:
        raise ValueError(f"{label} requires an existing parent and a new name")
    destination = path.parent.resolve(strict=True) / path.name
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"{label} already exists; never overwrite a review package or key")
    return destination


def _verify_private_key(path: Path, raw: bytes, identity: tuple[int, int]):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or (info.st_dev, info.st_ino) != identity):
        raise ValueError("private key identity or permissions changed")
    if registered._read(path) != raw:
        raise ValueError("written private key does not match captured bytes")
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or (info.st_dev, info.st_ino) != identity):
        raise ValueError("private key identity or permissions changed")


def build_blind_review_pack(records: Iterable[Record], output_dir: Path, *, key_output: Path, seed: str | int,
                            cohort: str = "campaign", generated_at: str | None = None,
                            cohort_manifest=None) -> dict:
    """Publish reviewer files and an external private key without overwrites.

    Seeded order is SHA256(seed, arm, project, label), independent of selection
    order and filesystem location. A missing generated_at stays null, avoiding
    wall-clock nondeterminism. Supplying a timestamp does not authenticate it.
    The private key is published and synced before the reviewer directory.
    A later failure can leave an orphan private key, or both outputs if the
    reviewer-parent sync fails; external destinations are never cleaned up.
    This process's ordering cannot prevent later changes by another writer.
    Share only the reviewer directory, never the key. No scoring is authorized.
    """
    if isinstance(seed, bool) or not isinstance(seed, (str, int)):
        raise ValueError("seed must be a nonempty string or integer")
    seed = _text(str(seed), "seed")
    generated_at = _timestamp(generated_at)
    records = validate_cohort(records, cohort=cohort, cohort_manifest=cohort_manifest)
    declared, cohort_pin = [], None
    if cohort == "campaign":
        from .cohort_manifest import read_cohort
        declared, cohort_pin = read_cohort(cohort_manifest)
    if cohort == "campaign" and (not _SHA.fullmatch(seed) or len(set(seed)) < 8):
        raise ValueError("campaign blind review pack requires a 64-character hex seed with at least 8 distinct hex digits")
    output = Path(output_dir)
    key_path = Path(key_output)
    if key_path.absolute() == output.absolute() or output.absolute() in key_path.absolute().parents:
        raise ValueError("private key must be outside the reviewer directory")
    destination = _new_destination(output, "output directory")
    key_destination = _new_destination(key_path, "private key")
    if key_destination == destination or destination in key_destination.parents:
        raise ValueError("private key must be outside the reviewer directory")
    captured, paths, inodes, total = [], set(), set(), 0
    forbidden = {identifier for record in records for identifier in (record.arm, record.label, str(record.source_path))}
    for record in records:
        path = record.source_path.resolve(strict=True)
        info = path.stat()
        inode = (info.st_dev, info.st_ino)
        if path in paths or inode in inodes:
            raise ValueError("duplicate source file or filesystem alias in selection")
        paths.add(path)
        inodes.add(inode)
        raw = registered._read(path)
        total += len(raw)
        if total > MAX_PACK_BYTES:
            raise ValueError("selected source bytes exceed pack size bound")
        digest = _sha(raw)
        if record.source_sha256 is not None and record.source_sha256 != digest:
            raise ValueError("selected source_sha256 does not match input")
        if cohort == "campaign":
            from data_sheets_schema.provenance import record_path_for, recorded_hash
            prov_candidate = path.parent / f"{record.project}_provenance.yaml"
            if not prov_candidate.is_file() and path.parent.parent != path.parent:
                method_dir = path.parent.parent.name
                concat_dir = path.parent.parent.parent
                corpus_prov = record_path_for(record.project, method_dir, record.label, concat_dir=concat_dir)
                if corpus_prov.is_file():
                    prov_candidate = corpus_prov
                else:
                    default_prov = record_path_for(record.project, method_dir, record.label)
                    if default_prov.is_file():
                        prov_candidate = default_prov
            if not prov_candidate.is_file():
                raise ValueError(
                    f"campaign record {record.project}:{record.label} has no provenance record at {prov_candidate}"
                )
            prov_doc = registered._yaml(registered._read(prov_candidate))
            if not isinstance(prov_doc, dict):
                raise ValueError(f"campaign record provenance at {prov_candidate} is not a YAML mapping")
            run_block = prov_doc.get("run") or {}
            if isinstance(run_block, dict) and run_block.get("label") and run_block["label"] != record.label:
                raise ValueError("campaign record label does not match sibling provenance run.label")
            declaration = next(r for r in declared if
                (r["arm"], r["project"], r["label"]) == record.identity)
            from .run_identity import same_run
            if (not same_run(run_block, {**declaration, "arm": declaration["input_arm"]})
                    or run_block.get("condition") != declaration["condition"]
                    or (run_block.get("replicate") is not None and
                        (type(run_block["replicate"]) is not int or run_block["replicate"] != declaration["replicate"]))):
                raise ValueError("campaign record identity differs from the declared cohort provenance")
            forbidden.update((declaration["condition"], declaration["method"], f'rep{declaration["replicate"]}'))
            val_block = prov_doc.get("validation") or {}
            artifacts = val_block.get("artifacts") if isinstance(val_block, dict) else None
            full_art = artifacts.get("full") if isinstance(artifacts, dict) else None
            if not isinstance(full_art, dict) or recorded_hash(full_art) is None:
                raise ValueError("campaign record provenance is missing validation.artifacts.full hash")
            rec_hash = recorded_hash(full_art)
            if hashlib.new(rec_hash[0], raw).hexdigest() != rec_hash[1]:
                raise ValueError("campaign record bytes do not match sibling provenance validation.artifacts.full")
        blinded, metadata_ids = _identity_blind(raw, record, forbidden)
        forbidden.update(metadata_ids)
        forbidden.update((str(path), str(record.source_path.absolute())))
        captured.append((record, path, digest, blinded))
    captured.sort(key=lambda item: (_sha(_canonical([seed, *item[0].identity])), item[0].identity))
    review = io.StringIO(newline="")
    writer = csv.writer(review, delimiter="\t", lineterminator="\n")
    writer.writerow(REVIEW_COLUMNS)
    entries, files = [], {}
    for index, (record, path, digest, blinded) in enumerate(captured, 1):
        blind_id = f"blind_{index:02d}"
        filename = blind_id + ".yaml"
        _leakage(blinded, forbidden, yaml_document=True)
        writer.writerow((blind_id, record.project, "", "", "", "", "", ""))
        entries.append({
            "blind_id": blind_id, "arm": record.arm, "project": record.project,
            "label": record.label, "source_path": str(path),
            "source_sha256": digest, "blinded_sha256": _sha(blinded),
            "fingerprint_diagnostics": _fingerprints(blinded),
        })
        files[filename] = blinded
    files["review_sheet.tsv"] = review.getvalue().encode()
    _leakage(files["review_sheet.tsv"], forbidden)
    key = {
        "format": FORMAT, "seed": seed, "generated_at": generated_at,
        "blinding_version": BLINDING_VERSION,
        "normalization": "sorted mapping keys; scientific scalar values and list order preserved",
        "residual_fingerprint_notice": FINGERPRINT_NOTICE,
        "structural_separability": _separability(entries),
        "timestamp_basis": "caller_supplied_unverified" if generated_at else "omitted_for_reproducibility",
        "cohort": cohort, "cohort_manifest": cohort_pin, "generator": {
            "algorithm": "sha256_seed_identity_order_v1",
            "module_sha256": _sha(registered._read(Path(__file__))),
            "stripper_module_sha256": _sha(registered._read(Path(registered.__file__))),
            "pyyaml_version": yaml.__version__,
        },
        "distribution": "reviewer directory contains YAML/TSV only; never share the separate private key",
        "publication": "private key first; late failure may retain orphan key or both outputs; neither is overwritten or removed",
        "scientific_approval": False, "records": entries,
    }
    key_raw = _canonical(key)
    owned = []

    def private_stage(parent, prefix):
        path = Path(tempfile.mkdtemp(prefix=prefix, dir=parent))
        info = path.lstat()
        owned.append((path, (info.st_dev, info.st_ino)))
        os.chmod(path, 0o700)
        return path

    try:
        stage = private_stage(destination.parent, ".blind-review-pack-")
        key_stage = private_stage(key_destination.parent, ".blind-review-key-")
        for name, raw in files.items():
            _write(stage / name, raw)
        key_file = key_stage / "sealed_blind_key.json"
        _write(key_file, key_raw)
        key_info = key_file.lstat()
        key_identity = (key_info.st_dev, key_info.st_ino)

        def verify_review():
            if {path.name for path in stage.iterdir()} != set(files):
                raise ValueError("reviewer directory contains unexpected files")
            for name, expected in files.items():
                actual = registered._read(stage / name)
                if actual != expected:
                    raise ValueError("written review package does not match captured bytes")
                _leakage(actual, forbidden, yaml_document=name.endswith(".yaml"))
            for _, path, digest, _ in captured:
                if _sha(registered._read(path)) != digest:
                    raise ValueError("source changed during review pack preparation")

        verify_review()
        _verify_private_key(key_file, key_raw, key_identity)
        _sync_directory(stage)
        _sync_directory(key_stage)
        _rename_new(key_file, key_destination)
        _sync_directory(key_destination.parent)
        _verify_private_key(key_destination, key_raw, key_identity)
        verify_review()
        _rename_new(stage, destination)
        _sync_directory(destination.parent)
    finally:
        original_error = sys.exc_info()[1]
        cleanup_errors = []
        for path, identity in owned:
            try:
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue
                if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != identity:
                    raise OSError(f"owned staging directory was replaced; refusing cleanup: {path}")
                shutil.rmtree(path)
            except OSError as exc:
                cleanup_errors.append(exc)
        if cleanup_errors:
            note = "Temporary staging cleanup failed; external outputs were retained: " + "; ".join(map(str, cleanup_errors))
            if original_error is not None:
                add_note = getattr(original_error, "add_note", None)
                if callable(add_note):
                    add_note(note)
                else:
                    # Python 3.9/3.10 do not render exception notes. Preserve
                    # the error and attached diagnostic even if stderr fails.
                    original_error.__notes__ = [*getattr(original_error, "__notes__", ()), note]
                    try:
                        print(note, file=sys.stderr)
                    except (OSError, ValueError):
                        pass
            else:
                raise OSError(note) from cleanup_errors[0]
    return key


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--manifest", type=Path, help="Strict YAML/JSON records manifest; paths relative to manifest")
    selection.add_argument("--record", action="append", help="Repeat ARM:PROJECT:LABEL=PATH; paths relative to cwd")
    parser.add_argument(
        "--seed",
        default=None,
        help="Cryptographic seed (64 hex characters with at least 8 distinct hex digits in campaign mode; auto-generated via secrets.token_hex(32) if omitted)",
    )
    parser.add_argument("--cohort", choices=("campaign", "synthetic"), default="campaign",
                        help="Campaign requires an explicit cohort manifest; synthetic accepts other sizes")
    parser.add_argument("--cohort-manifest", type=Path, help="Declared evaluation_cohort_v1 campaign")
    parser.add_argument("--generated-at", help="Optional explicit UTC YYYY-MM-DDTHH:MM:SSZ; otherwise null, not current time")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New 0700 reviewer directory containing only YAML and review_sheet.tsv")
    parser.add_argument("--key-output", type=Path, required=True,
                        help="New private 0600 key file outside the reviewer directory; never distribute it")
    args = parser.parse_args(argv)
    seed_val = args.seed if args.seed is not None else secrets.token_hex(32)
    try:
        records = read_manifest(args.manifest) if args.manifest else [parse_record(item) for item in args.record]
        result = build_blind_review_pack(records, args.output_dir, key_output=args.key_output,
                                         seed=seed_val, cohort=args.cohort,
                                         generated_at=args.generated_at, cohort_manifest=args.cohort_manifest)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Prepared {len(result['records'])} blinded records. Reviewer directory: {args.output_dir}")
    print(f"Private key: {args.key_output}; never share the sealed key.")
    return 0
