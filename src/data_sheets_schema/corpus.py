"""Resolve caller-owned corpus paths independently of package resources."""
from __future__ import annotations

import os
from pathlib import Path

import click

from data_sheets_schema import resources

DEFAULT_MANIFEST = Path("data/preprocessed/source_manifest.yaml")
AUTO = object()


def manifest_root(manifest: Path) -> Path:
    """Conventional manifests name the project root; standalone ones their directory."""
    path = Path(manifest).resolve()
    if path.parts[-len(DEFAULT_MANIFEST.parts):] == DEFAULT_MANIFEST.parts:
        return path.parents[2]
    return path.parent


def relative_to_root(path: Path, root: Path) -> Path:
    """Keep the portable spelling at its root; otherwise return the rooted path."""
    path = Path(path)
    if path.is_absolute() or Path.cwd().resolve() == root.resolve():
        return path
    return root / path


def default_manifest_path() -> Path:
    here = Path.cwd().resolve()
    checkout = resources.CHECKOUT_ROOT
    # Archived copies within the checkout are historical evidence, not an
    # implicit switch of the current project. Explicit selections still work.
    if checkout is not None and (here == checkout or checkout in here.parents):
        return relative_to_root(DEFAULT_MANIFEST, checkout)
    for root in (here, *here.parents):
        candidate = root / DEFAULT_MANIFEST
        if candidate.is_file():
            return relative_to_root(DEFAULT_MANIFEST, root)
    # A checkout can supply installed resources, but does not own an
    # unrelated caller's corpus without an explicit selection (#1594).
    return DEFAULT_MANIFEST


def _selected_path(value) -> Path | None:
    if str(value).lower() == "none":
        return None
    path = Path(value)
    return default_manifest_path() if path == DEFAULT_MANIFEST and not path.exists() else path


def manifest_override():
    """An explicit command/environment selection, including explicit none."""
    ctx = click.get_current_context(silent=True)
    while ctx is not None:
        value = ctx.params.get("manifest")
        if value:
            return _selected_path(value)
        ctx = ctx.parent
    value = os.environ.get("D4D_MANIFEST")
    if value:
        return _selected_path(value)
    return AUTO


def selected_manifest(*, allow_checkout_fallback: bool = False) -> Path | None:
    """The active CLI/environment selection, else the discovered manifest."""
    explicit = manifest_override()
    if explicit is not AUTO:
        return explicit
    selected = default_manifest_path()
    here = Path.cwd().resolve()
    checkout = resources.CHECKOUT_ROOT
    if (not allow_checkout_fallback and checkout is not None
            and here != checkout and checkout not in here.parents
            and selected.resolve() == (checkout / DEFAULT_MANIFEST).resolve()):
        # No caller manifest was selected. Corpus writes and lookups stay in
        # the caller's working tree; availability of the package's study
        # registry does not authorize writing into that checkout.
        return None
    return selected


def root(manifest=AUTO) -> Path:
    if manifest is AUTO:
        manifest = selected_manifest()
    return manifest_root(manifest) if manifest is not None else Path.cwd().resolve()


def anchored(path: Path, manifest=AUTO) -> Path:
    return relative_to_root(Path(path), root(manifest))
