"""Deterministic, offline source-review packs (E2; #3280/#1782/#1801/#1815).

The output is an OPERATOR-ONLY package: distribute only ``blind_*.yaml`` and
``review_sheet.tsv`` to reviewers, never the directory or sealed key. File
permissions are local access controls, not encryption or reviewer separation.

Selection is explicit. This prepares review materials, not scientific approval,
generation acceptance, or proof that source content cannot reveal its origin.
Scientific strings are never redacted. Ambiguous provenance or an identifier
remaining in source text causes refusal and requires explicit blinding review.
"""
from __future__ import annotations

import argparse
from collections import Counter
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
import tempfile
from typing import Iterable

import yaml

from data_sheets_schema.cross_family_panel_analysis import _rename_new, _sync_directory
from data_sheets_schema.evaluation import registered_eval_runner as registered
from data_sheets_schema.evaluation_context import unwrap_document

FORMAT = "blind_source_review_pack_v1"
PROJECTS = ("CHORUS", "AI_READI", "CM4AI", "VOICE")
ARMS = ("v8", "v10")
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

    def __post_init__(self):
        for name in ("arm", "project", "label"):
            _text(getattr(self, name), name)
        if len(self.arm.strip()) < 2:
            raise ValueError("arm requires at least 2 non-whitespace characters")
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


def validate_cohort(records: Iterable[Record], *, cohort: str = "campaign") -> list[Record]:
    records = list(records)
    if not records or len(records) > MAX_RECORDS or not all(isinstance(record, Record) for record in records):
        raise ValueError(f"select 1..{MAX_RECORDS} explicit Record entries")
    if len({record.identity for record in records}) != len(records):
        raise ValueError("duplicate arm/project/label selection")
    if cohort not in {"campaign", "synthetic"}:
        raise ValueError("cohort must be campaign or synthetic")
    if cohort == "campaign":
        expected = Counter({(arm, project): 3 for arm in ARMS for project in PROJECTS})
        if len(records) != 24 or Counter((r.arm, r.project) for r in records) != expected:
            raise ValueError("campaign requires exactly 24 records: v8/v10, four projects, three per cell")
        for record in records:
            if record.arm == "v8":
                suffix = "04f" if record.project in {"CHORUS", "VOICE"} else "04g"
                labels = {f"2026-09-{suffix}_claude-opus-5-api-generic-v8_rep{i}" for i in (1, 2, 3)}
                if record.label not in labels:
                    raise ValueError(f"campaign v8 comparator for {record.project} requires {suffix} rep1–3")
            elif record.arm == "v10":
                lbl_lower = record.label.lower()
                if "v10" not in lbl_lower and not record.label.startswith("registered-final-"):
                    raise ValueError(
                        f"campaign v10 record for {record.project} requires a v10 or registered-final label, got {record.label!r}"
                    )
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
                if item != record.arm:
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
    blinded = registered.blind_record(yaml.safe_dump(document, sort_keys=False, allow_unicode=True).encode())
    return blinded, identifiers


def _identifier_leaked(ident_folded: str, text_folded: str) -> bool:
    if len(ident_folded) < 4:
        return bool(re.search(rf"(?<![0-9a-z]){re.escape(ident_folded)}(?![0-9a-z])", text_folded))
    return ident_folded in text_folded


def _leakage(raw: bytes, forbidden: set[str], *, yaml_document: bool = False):
    text = raw.decode("utf-8")
    strings = [text]
    if yaml_document:
        strings.extend(_strings(registered._yaml(raw)))
    folded = [item.casefold() for item in strings]
    if any(
        _identifier_leaked(identifier.casefold(), item)
        for identifier in forbidden
        if identifier
        for item in folded
    ):
        raise ValueError("generation identity remains in reviewer content; explicit blinding review required")
    if any(_MODEL_LITERAL.search(item) for item in strings):
        raise ValueError("generator model identifier remains in reviewer content; explicit blinding review required")


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


def build_blind_review_pack(records: Iterable[Record], output_dir: Path, *, seed: str | int,
                            cohort: str = "campaign", generated_at: str | None = None) -> dict:
    """Publish a new operator-only package, refusing leaks and any overwrite.

    Seeded order is SHA256(seed, arm, project, label), independent of selection
    order and filesystem location. A missing generated_at stays null, avoiding
    wall-clock nondeterminism. Supplying a timestamp does not authenticate it.
    Share only reviewer YAML files and review_sheet.tsv, NEVER the full output
    directory/sealed_blind_key.json. This is not an authorization to score.
    """
    if isinstance(seed, bool) or not isinstance(seed, (str, int)):
        raise ValueError("seed must be a nonempty string or integer")
    seed = _text(str(seed), "seed")
    generated_at = _timestamp(generated_at)
    records = validate_cohort(records, cohort=cohort)
    if cohort == "campaign" and (not _SHA.fullmatch(seed) or len(set(seed)) < 8):
        raise ValueError("campaign blind review pack requires a 64-character hex seed with non-trivial entropy (at least 8 distinct hex digits)")
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise ValueError("output directory already exists; never overwrite a review package")
    if not output.parent.is_dir() or output.name in {"", ".", ".."}:
        raise ValueError("output requires an existing parent and a new directory name")
    destination = output.parent.resolve() / output.name
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
            if isinstance(run_block, dict):
                if run_block.get("label") and run_block.get("label") != record.label:
                    raise ValueError("campaign record label does not match sibling provenance run.label")
                cond = str(run_block.get("condition") or "")
                if record.arm == "v10" and cond and not cond.startswith("generic_v10"):
                    raise ValueError(f"campaign v10 record provenance condition {cond!r} is not generic_v10")
                if record.arm == "v8" and cond and not cond.startswith("generic_v8"):
                    raise ValueError(f"campaign v8 record provenance condition {cond!r} is not generic_v8")
            val_block = prov_doc.get("validation") or {}
            artifacts = val_block.get("artifacts") if isinstance(val_block, dict) else None
            full_art = artifacts.get("full") if isinstance(artifacts, dict) else None
            if not isinstance(full_art, dict) or recorded_hash(full_art) is None:
                raise ValueError("campaign record provenance is missing validation.artifacts.full hash")
            rec_hash = recorded_hash(full_art)
            if hashlib.new(rec_hash[0], raw).hexdigest() != rec_hash[1]:
                raise ValueError("campaign record bytes do not match sibling provenance validation.artifacts.full")
        blinded, metadata_ids = _strip(raw, record)
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
        })
        files[filename] = blinded
    files["review_sheet.tsv"] = review.getvalue().encode()
    _leakage(files["review_sheet.tsv"], forbidden)
    key = {
        "format": FORMAT, "seed": seed, "generated_at": generated_at,
        "timestamp_basis": "caller_supplied_unverified" if generated_at else "omitted_for_reproducibility",
        "cohort": cohort, "generator": {
            "algorithm": "sha256_seed_identity_order_v1",
            "module_sha256": _sha(registered._read(Path(__file__))),
            "stripper_module_sha256": _sha(registered._read(Path(registered.__file__))),
            "pyyaml_version": yaml.__version__,
        },
        "distribution": "operator_only; share blind_*.yaml and review_sheet.tsv only, never the sealed key or directory",
        "scientific_approval": False, "records": entries,
    }
    files["sealed_blind_key.json"] = _canonical(key)
    stage = Path(tempfile.mkdtemp(prefix=".blind-review-pack-", dir=destination.parent))
    try:
        os.chmod(stage, 0o700)
        for name, raw in files.items():
            _write(stage / name, raw)
        # Re-read actual files after writing; no parser/cache can hide changes.
        for name, expected in files.items():
            actual = registered._read(stage / name)
            if actual != expected:
                raise ValueError("written review package does not match captured bytes")
            if name != "sealed_blind_key.json":
                _leakage(actual, forbidden, yaml_document=name.endswith(".yaml"))
        for _, path, digest, _ in captured:
            if _sha(registered._read(path)) != digest:
                raise ValueError("source changed during review pack preparation")
        _sync_directory(stage)
        _rename_new(stage, destination)
        _sync_directory(destination.parent)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return key


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--manifest", type=Path, help="Strict YAML/JSON records manifest; paths relative to manifest")
    selection.add_argument("--record", action="append", help="Repeat ARM:PROJECT:LABEL=PATH; paths relative to cwd")
    parser.add_argument(
        "--seed",
        default=None,
        help="Cryptographic seed (at least 32 characters in campaign mode; auto-generated via secrets.token_hex(32) if omitted)",
    )
    parser.add_argument("--cohort", choices=("campaign", "synthetic"), default="campaign",
                        help="Default: 24 records, v8 04f/04g + v10, 3 per project/arm; synthetic accepts other sizes")
    parser.add_argument("--generated-at", help="Optional explicit UTC YYYY-MM-DDTHH:MM:SSZ; otherwise null, not current time")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New operator-only 0700 directory. Share only YAML+review_sheet, NEVER key/full directory")
    args = parser.parse_args(argv)
    seed_val = args.seed if args.seed is not None else secrets.token_hex(32)
    try:
        records = read_manifest(args.manifest) if args.manifest else [parse_record(item) for item in args.record]
        result = build_blind_review_pack(records, args.output_dir, seed=seed_val, cohort=args.cohort,
                                         generated_at=args.generated_at)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Prepared {len(result['records'])} blinded records. Operator-only package: {args.output_dir}")
    print("Share only blind_*.yaml and review_sheet.tsv; never the sealed key or full directory.")
    return 0
