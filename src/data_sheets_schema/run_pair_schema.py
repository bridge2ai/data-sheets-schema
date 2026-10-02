"""Scoped full/core views for recomputing historical pair and report checks."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
from typing import Any

from data_sheets_schema.run_schema import TODAY, run_schema_bytes
from data_sheets_schema.schema_view import shared_view, version_document, version_view

SCHEMA_SELECTION_INSTRUMENT = "run-recorded-full-core-v1 (#4062)"
# Validation is a fact about immutable bytes in this process. Retain only
# successful identities, never SchemaViews or their induced-slot caches.
_VALIDATED: set[tuple[str, str]] = set()


@dataclass(frozen=True)
class SelectedSchemas:
    full: Any
    core: Any
    basis: dict
    hashes: dict

    @property
    def recovered_pair(self):
        return all(item["source"] != TODAY for item in self.basis.values())


@contextmanager
def run_schema_views(record):
    """Select each recorded schema, disclosing any per-file current fallback.

    Historical views never enter the shared current-view cache. They are
    released on normal return and on errors; callers must not retain them.
    A missing/unreadable historical file follows run_schema's explicit fallback
    policy. The hashes always describe the bytes actually used by the check.
    """
    from data_sheets_schema.provenance import FULL_SCHEMA, CORE_SCHEMA
    from data_sheets_schema.schema_cache import sha256_of
    views, bases, hashes = {}, {}, {}
    with ExitStack() as stack:
        for kind, path, root_class in (("full", FULL_SCHEMA, "Dataset"),
                                       ("core", CORE_SCHEMA, "CoreDataset")):
            data, basis = run_schema_bytes(record, kind=kind)
            view = None
            if data is not None:
                try:
                    # Using a view of the recovered bytes also avoids a race
                    # between selection and a concurrently edited current file.
                    view = stack.enter_context(version_view(path, version_document(data)))
                    if root_class not in view.all_classes():
                        raise ValueError(f"schema does not declare {root_class}")
                    key = (hashlib.sha256(data).hexdigest(), root_class)
                    if key not in _VALIDATED:
                        # Report ranges inspect every core class; pair projection
                        # can reach nested full/core classes from record values.
                        # Validate that closure before leaving the fallback scope.
                        for class_name in view.all_classes():
                            view.class_induced_slots(class_name)
                        _VALIDATED.add(key)
                except Exception as error:
                    view = None
                    basis = {"source": TODAY,
                             **{key: basis[key] for key in ("path", "sha256", "md5") if key in basis},
                             "reason": f"recovered {kind} schema could not be loaded "
                                       f"({type(error).__name__}: {error})"}
            if view is None:
                view = shared_view(path)
                digest = sha256_of(path)
            else:
                digest = hashlib.sha256(data).hexdigest()
            views[kind], bases[kind], hashes[f"{kind}_sha256"] = view, basis, digest
        yield SelectedSchemas(views["full"], views["core"], bases, hashes)
