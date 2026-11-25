"""Independent root-datasheet scope for semantic v6, issues 6358/6360, 2026-11-25.

Read closed caller declarations and original documents; return trusted units.
No record or declaration is modified. Legacy unit selection remains unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import urlsplit

from data_sheets_schema.evaluation_context import declared_class, dataset_units, unwrap_document

ROOT_POLICY = "root_dataset_v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_LOCAL_PATH = re.compile(
    r"(?:/(?:Users|home|root|tmp|private|var|opt|mnt|usr|etc|run|Volumes|Applications|System|bin|sbin|dev|media|srv)/"
    r"|file:[\\/]|(?<![A-Za-z0-9])[A-Za-z]:[\\/])", re.IGNORECASE)
_WEB_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_PROVENANCE_SECTIONS = ("metadata", "evaluation_model", "scorer_instrument", "model")


def validate_root_scope(value: dict, input_sha256: str | None = None) -> dict:
    if not isinstance(value, dict) or set(value) != {"policy", "input_sha256", "reason"}:
        raise ValueError("root scope must contain exactly policy, input_sha256 and reason")
    if value["policy"] != ROOT_POLICY:
        raise ValueError("unsupported root selection policy")
    if not isinstance(value["input_sha256"], str) or not _SHA256.fullmatch(value["input_sha256"]):
        raise ValueError("root scope input_sha256 must be a lowercase SHA256")
    if not isinstance(value["reason"], str) or not value["reason"].strip() or len(value["reason"]) > 4096:
        raise ValueError("root scope reason must be a bounded nonempty string")
    if input_sha256 is not None and value["input_sha256"] != input_sha256:
        raise ValueError("root scope names another input SHA256")
    return dict(value)


def parse_root_scope(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 65536:
        raise ValueError("root scope must be a bounded nonempty JSON document")

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate root scope field")
            value[key] = item
        return value

    def constant(value):
        raise ValueError("nonfinite root scope value")

    try:
        parsed = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except UnicodeDecodeError as exc:
        raise ValueError("root scope is not valid Unicode JSON") from exc
    return validate_root_scope(parsed)


def load_root_scope(path: Path | None) -> tuple[dict, str]:
    if path is None:
        raise ValueError("semantic v6 requires an independent scope context")
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 65536:
        raise ValueError("root scope must be a bounded nonempty regular file")
    raw = path.read_bytes()
    return parse_root_scope(raw), hashlib.sha256(raw).hexdigest()


def _validate_classes(data: dict, active: set[int]) -> None:
    if id(data) in active:
        raise ValueError("cyclic dataset resources")
    active.add(id(data))
    try:
        document = unwrap_document(data)
        wrapper_class = declared_class(document)
        field_class = declared_class(dict(document))
        if "conforms_to_class" in document and field_class is None:
            raise ValueError("unrecognized explicit dataset class")
        if field_class is not None and wrapper_class != field_class:
            raise ValueError("dataset wrapper contradicts conforms_to_class")
        resources = document.get("resources")
        if isinstance(resources, list):
            for child in resources:
                if isinstance(child, dict):
                    _validate_classes(child, active)
    finally:
        active.remove(id(data))


def resolve_root_units(document: dict, input_sha256: str, declaration: dict) -> list[tuple[str, dict]]:
    if not isinstance(input_sha256, str) or not _SHA256.fullmatch(input_sha256):
        raise ValueError("root scope requires the original input SHA256")
    validate_root_scope(declaration, input_sha256)
    _validate_classes(document, set())
    document = unwrap_document(document)
    # Validate all descendants before selecting the submitted parent.
    dataset_units(document)
    if declared_class(document) in {"DatasetCollection", "CoreDatasetCollection"}:
        raise ValueError("root scope contradicts an explicit DatasetCollection")
    return [("#", document)]


def _relative_artifact(value: str, field: str) -> None:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"{field} must be a relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")) or ":" in value:
        raise ValueError(f"{field} must be a relative POSIX path without traversal")


def assert_portable_output(result: dict) -> None:
    """Refuse absolute provenance paths and common local path forms in prose.

    Evidence pointers outside provenance retain their JSON-pointer meaning.
    This does not infer arbitrary filesystem references from natural language.
    """
    def web_url(match):
        try:
            parsed = urlsplit(match.group())
            return "" if parsed.hostname else match.group()
        except ValueError:
            return match.group()

    def walk(value, provenance=False):
        if isinstance(value, str):
            if provenance and value.lstrip().startswith("/"):
                raise ValueError("published semantic v6 provenance contains an absolute POSIX path")
            # A URL may legitimately name /home or /Users on a remote site.
            # Only recognized HTTP(S) URLs are exempt; prose delimiters are not.
            if _LOCAL_PATH.search(_WEB_URL.sub(web_url, value)):
                raise ValueError("published semantic v6 output contains a local absolute path")
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(key, provenance)
                walk(item, provenance)
        elif isinstance(value, list):
            for item in value:
                walk(item, provenance)

    walk(result)
    for section in _PROVENANCE_SECTIONS:
        walk(result.get(section), provenance=True)
    _relative_artifact(result.get("d4d_file"), "d4d_file")
    evaluation_model = result.get("evaluation_model")
    if isinstance(evaluation_model, dict):
        logs = evaluation_model.get("session_logs")
        if logs is not None:
            if not isinstance(logs, list):
                raise ValueError("session_logs must be a list")
            for entry in logs:
                if not isinstance(entry, dict):
                    raise ValueError("session log must be a mapping")
                _relative_artifact(entry.get("path"), "session log path")
