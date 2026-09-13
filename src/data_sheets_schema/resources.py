"""Where the package's resources are, from any working directory (#1301, #673).

Every module spells its resources as paths relative to the repository root
— `Path("src/download/prompts")`, `Path(".claude/commands/…")`,
`Path("src/data_sheets_schema/schema/…")` — which is right from the
repository root and wrong from anywhere else: an editable install run from
another directory failed to find its own prompt, and a wheel could not find
them at all because they were never shipped.

The constants keep that spelling — it is the form every record stores, every
pin is keyed on, and every test that stages a tree in a temporary directory
relies on — and the *readers* resolve it when they read, the way
`schema_digest.resolve_schema` and `provenance.record_schema_path` already
did for the schemas (#659, #618):

1. the working directory's copy, if there is one — a command run from the
   repository root, and a staged fixture tree, behave exactly as before;
2. else the source checkout this package is imported from (`pyproject.toml`
   two directories up), whatever the working directory;
3. else the installed copy: the wheel ships the prompt, playbook,
   agent-definition and rubric files at their repository-relative paths under
   the installation root (`site-packages/src/download/prompts/…`), and the
   schema files as package data (`site-packages/data_sheets_schema/schema/…`).

A path that exists nowhere is returned unchanged, so the caller's own error
names what was looked for. Only paths under `RESOURCE_PREFIXES` are
resolved: the corpus (`data/d4d_concatenated/…`, a bundle, a record) is the
caller's input and output tree and stays relative to the working directory —
a missing record must not silently become the checkout's.

Resolution is per read, not per import: a constant resolved at import time
takes the value of whichever directory the first importer happened to be
in, and a fixture test that ran later then read — or wrote — the real file.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

#: The package directory (`…/data_sheets_schema`).
PACKAGE_ROOT = Path(__file__).resolve().parent

#: The source checkout this package is imported from, or None for a wheel.
CHECKOUT_ROOT: Path | None = (
    PACKAGE_ROOT.parents[1] if (PACKAGE_ROOT.parents[1] / "pyproject.toml").exists() else None)

#: For a wheel, the directory the repository-relative includes were
#: installed under: the wheel's root is `site-packages`, one level above
#: the package.
INSTALL_ROOT: Path = PACKAGE_ROOT.parent

#: What counts as a resource, by path components (#1488). Everything else
#: is the caller's tree.
RESOURCE_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("src",), (".claude",), ("data", "rubric"), ("project",))

#: The package-data prefix: `src/data_sheets_schema/X` is `PACKAGE_ROOT/X`
#: wherever the package is.
_PACKAGE_PREFIX = ("src", "data_sheets_schema")


def is_checkout() -> bool:
    return CHECKOUT_ROOT is not None


def roots() -> list[Path]:
    """Where a repository-relative resource may live, in order."""
    out = []
    if CHECKOUT_ROOT is not None:
        out.append(CHECKOUT_ROOT)
    out.append(INSTALL_ROOT)
    return out


def normalized(path: str | Path) -> Path:
    """`path` with `.` and `..` collapsed, as given otherwise (#1481, #1482):
    `src/download/../download/prompts/x.md` is `src/download/prompts/x.md`,
    and `src/../data/x` is `data/x` — the corpus, not a resource."""
    p = Path(path)
    return Path(os.path.normpath(str(p))) if str(p) not in ("", ".") else Path(".")


def is_resource(path: str | Path) -> bool:
    p = normalized(path)
    if p.is_absolute() or ".." in p.parts:
        return False
    return any(p.parts[:len(prefix)] == prefix for prefix in RESOURCE_PREFIXES)


def _candidates(rel: Path) -> list[Path]:
    out = [root / rel for root in roots()]
    if rel.parts[:2] == _PACKAGE_PREFIX:
        out.append(PACKAGE_ROOT.joinpath(*rel.parts[2:]))
    return out


def _cwd_carries(rel: Path) -> bool:
    """Whether the working directory holds the directory `rel` is in —
    `src/download/prompts` for a prompt, `src/data_sheets_schema/schema`
    for a schema; the directory itself, not an ancestor, and never a
    top-level one such as `src` or `.claude`, which any project may have.

    Then the working directory is the tree being read, and a file absent
    from it is absent: a staged fixture that deliberately omits a prompt
    must read `missing`, not the checkout's copy. A directory with no such
    directory — a user's data tree, or a fixture that carries only the
    `src/data_sheets_schema` marker the old root guard wanted — has nothing
    to be authoritative about, and the checkout's or the install's copy is
    read. A project that happens to carry the exact directory reads its
    own files: that is the rule, stated.
    """
    return len(rel.parts) > 2 and rel.parent.is_dir()


def resource_path(path: str | Path) -> Path:
    """Where a repository-relative resource is read from, decided now.

    The working directory's copy, as the (normalized) relative path it was
    given, when it exists there or the working directory carries its
    directory (`_cwd_carries`); else the checkout's, else the installed
    copy, as an absolute path; else the path unchanged so the caller's own
    error names it. An absolute path, or one outside `RESOURCE_PREFIXES`
    (including anything that climbs out with `..`), is returned as is.
    """
    p = normalized(path)
    if p.is_absolute() or not is_resource(p) or p.exists() or _cwd_carries(p):
        return p
    for candidate in _candidates(p):
        if candidate.exists():
            return candidate
    return p


def repo_relative(path: str | Path, *, cwd: bool = True) -> str:
    """The repository-relative, posix form a record stores for `path`.

    A relative resource path is returned normalized. Any other path is
    resolved and anchored to the checkout, else to the package (a wheel's
    package data, spelled back as `src/data_sheets_schema/…`), else to the
    installation root when the result is a resource (an unrelated file under
    `site-packages` stays absolute, #1487), else — with `cwd`, as the prompt
    registry always keyed a staged fixture — to the working directory; a
    path under none of them stays absolute, resolved. The provenance record
    passes `cwd=False`: a file outside every root is recorded absolute, so
    one file is never recordable under two strings (#398). A run launched
    from elsewhere used to store an absolute path for a prompt *inside* the
    checkout, which no pin could match (#673).
    """
    p = normalized(path)
    if not p.is_absolute() and is_resource(p):
        return p.as_posix()
    try:
        resolved = p.resolve()
    except OSError:
        return p.as_posix()
    anchors: list[tuple[Path, tuple[str, ...], bool]] = []
    if CHECKOUT_ROOT is not None:
        anchors.append((CHECKOUT_ROOT, (), False))
    anchors.append((PACKAGE_ROOT, _PACKAGE_PREFIX, False))
    anchors.append((INSTALL_ROOT, (), True))
    if cwd:
        anchors.append((Path.cwd(), (), False))
    for root, prefix, resources_only in anchors:
        try:
            rel = resolved.relative_to(root.resolve())
        except (ValueError, OSError):
            continue
        out = Path(*prefix, rel) if prefix else rel
        if resources_only and not is_resource(out):
            continue
        return out.as_posix()
    return resolved.as_posix()


def linkml_validate() -> list[str]:
    """The command that runs `linkml-validate` for *this* interpreter.

    `poetry run linkml-validate` needs a `pyproject.toml` in the working
    directory, so every validator call failed from anywhere but the checkout
    root and for any install without poetry. The console script beside the
    interpreter is the same environment; failing that, the module entry
    point through the interpreter itself — never a `PATH` search, which can
    find another environment's script (#1486).
    """
    beside = Path(sys.executable).parent / ("linkml-validate.exe" if sys.platform == "win32" else "linkml-validate")
    if beside.exists():
        return [str(beside)]
    return [sys.executable, "-c", "from linkml.validator.cli import cli; cli()"]
