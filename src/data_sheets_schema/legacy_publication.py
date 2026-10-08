"""Required file-publication boundary for the legacy semantic TSV builders.

Draft construction remains separate. This module never repairs mapped values.
All bytes must be prepared before ``publish``; replacement is atomic per file,
not a transaction across files after replacement begins.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import os
from pathlib import Path
import tempfile
from typing import Callable, Iterable

import yaml


class PublicationError(ValueError):
    """A Dataset could not be accepted for file publication."""


class _UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise PublicationError(f"Duplicate YAML key in Dataset publication: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _same_value(before, after):
    if type(before) is not type(after):
        return False
    if isinstance(before, dict):
        return (before.keys() == after.keys()
                and all(_same_value(before[key], after[key]) for key in before))
    if isinstance(before, list):
        return len(before) == len(after) and all(
            _same_value(a, b) for a, b in zip(before, after))
    return before == after


@lru_cache(maxsize=4)
def _validator(schema: str, digest: str):
    # The digest makes cache reuse contingent on the current schema bytes.
    from linkml.validator import Validator
    from linkml.validator.plugins import JsonschemaValidationPlugin
    return Validator(schema, validation_plugins=[JsonschemaValidationPlugin(closed=True)])


def prepare_dataset(dataset: dict, *, text: str | None = None,
                    encoding: str = "utf-8", context: str = "", **dump_options) -> bytes:
    """Validate the readback of the exact serialized bytes that will be written."""
    try:
        if text is None:
            text = yaml.safe_dump(dataset, **dump_options)
        raw = text.encode(encoding)
        record = yaml.load(raw.decode(encoding), Loader=_UniqueLoader)
        if not isinstance(record, dict):
            raise PublicationError("Dataset publication requires one YAML mapping")
        if not _same_value(dataset, record):
            raise PublicationError("Dataset serialization/readback changed mapped values or types")
        from data_sheets_schema.resources import PACKAGE_ROOT
        schema = PACKAGE_ROOT / "schema/data_sheets_schema_all.yaml"
        digest = sha256(schema.read_bytes()).hexdigest()
        report = _validator(str(schema), digest).validate(record, "Dataset")
        if report.results:
            details = "; ".join(str(item.message) for item in report.results)
            metadata = (" transformation_metadata is not a Dataset field; use the API's "
                        "explicit result_contract='dataset_v1' to keep provenance "
                        "in its separate result field (#4630)."
                        if "transformation_metadata" in record else "")
            raise PublicationError(
                f"Dataset publication refused against {schema.name} (sha256 {digest}): "
                f"{details}.{metadata}")
        return raw
    except PublicationError as exc:
        if context:
            raise PublicationError(f"{context}: {exc}") from exc
        raise
    except Exception as exc:
        prefix = f"{context}: " if context else ""
        raise PublicationError(f"{prefix}Required Dataset publication validation unavailable or failed: {exc}") from exc


def diagnostic(raw: bytes, check: Callable[[str], tuple[bool, str]]) -> str:
    """Run a requested legacy diagnostic on prepared bytes before publication."""
    with tempfile.TemporaryDirectory(prefix="d4d-publication-check-") as directory:
        path = Path(directory) / "record.yaml"
        path.write_bytes(raw)
        valid, detail = check(str(path))
        if not valid:
            raise PublicationError(f"Requested Dataset validation failed: {detail}")
        return detail


def publish(files: Iterable[tuple[Path, bytes]], *, protected: Iterable[Path] = ()) -> None:
    """Stage every prepared file before the first atomic replacement.

    Validation and rendering belong before this call. Staging failures leave
    existing destinations intact. OS failures during replacement can leave a
    partially published set; no multi-file rollback is promised.
    """
    files = [(Path(path), raw) for path, raw in files]
    identities = [path.resolve() for path, _ in files]
    from data_sheets_schema.resources import PACKAGE_ROOT
    inputs = [Path(path).resolve() for path in protected]
    inputs.append((PACKAGE_ROOT / "schema/data_sheets_schema_all.yaml").resolve())

    def overlaps(a, b):
        return a == b or a in b.parents or b in a.parents

    if any(overlaps(path, other) for i, path in enumerate(identities)
           for other in identities[i + 1:]):
        raise PublicationError("Publication destinations overlap")
    for path in identities:
        for source in inputs:
            if overlaps(path, source):
                raise PublicationError(f"Publication destination {path} overlaps protected input {source}")
        if path.is_dir():
            raise PublicationError(f"Publication destination is a directory: {path}")
    if any(not isinstance(raw, bytes) for _, raw in files):
        raise TypeError("Publication requires prepared bytes")
    staged = []
    try:
        for path, raw in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.",
                                             suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                staged.append((temporary, path))
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        for temporary, path in staged:
            os.replace(temporary, path)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
