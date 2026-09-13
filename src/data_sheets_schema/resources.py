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

import sys
from pathlib import Path

#: The package directory (`…/data_sheets_schema`).
PACKAGE_ROOT = Path(__file__).resolve().parent

#: The source checkout this package is imported from, or None for a wheel.
class ResourceRootError(RuntimeError):
    """A directory that may be a checkout could not be inspected (#1619)."""


def _is_our_checkout(root: Path) -> bool:
    """A `pyproject.toml` two levels up is the checkout only when it is this
    project's and the source layout is there — a copy installed under a
    user's own project (`<project>/vendor/data_sheets_schema/`) must not
    adopt that project (#1577). A marker that is absent is no checkout; one
    that cannot be read is not evidence of anything and is refused rather
    than read as absent (#1619)."""
    marker = root / "pyproject.toml"
    try:
        text = marker.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        raise ResourceRootError(f"{marker} could not be read: {exc}; whether {root} is a checkout is unknown") from exc
    import re
    return (re.search(r'^name\s*=\s*"data[-_]sheets[-_]schema"', text, re.M) is not None
            and (root / "src" / "data_sheets_schema").is_dir())


CHECKOUT_ROOT: Path | None = (
    PACKAGE_ROOT.parents[1] if _is_our_checkout(PACKAGE_ROOT.parents[1]) else None)

#: For a wheel, the directory the repository-relative includes were
#: installed under: the wheel's root is `site-packages`, one level above
#: the package.
INSTALL_ROOT: Path = PACKAGE_ROOT.parent

#: What counts as a resource, by path components (#1488). Everything else
#: is the caller's tree.
RESOURCE_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("src",), (".claude",), ("data", "rubric"), ("project",), (".github",))

#: The package-data prefix: `src/data_sheets_schema/X` is `PACKAGE_ROOT/X`
#: wherever the package is.
_PACKAGE_PREFIX = ("src", "data_sheets_schema")


def is_checkout() -> bool:
    return CHECKOUT_ROOT is not None


def checkout_at(directory: str | Path) -> Path | None:
    """The checkout of this project `directory` is in: the *outermost* of
    itself and its ancestors that is one — a worktree or a second clone as
    much as the checkout the code is imported from. Outermost, because a
    copy of the tree archived inside a checkout (a registration of measured
    inputs under `notes/`, #1545) is part of the checkout that holds it,
    not a checkout of its own. None outside every checkout."""
    try:
        p = Path(directory).resolve()
    except OSError:
        return None
    found = None
    for candidate in (p, *p.parents):
        if _is_our_checkout(candidate):
            found = candidate
    return found


def cwd_checkout() -> Path | None:
    """The working directory when it is the *root* of a checkout of this
    project (#1588): its files are what `resource_path` reads first, so it —
    not the checkout the code happens to be imported from — is where the
    resources come from. A subdirectory of a checkout is not one (#672),
    and neither is a copy of the tree nested inside one (#1545)."""
    cwd = Path.cwd().resolve()
    return cwd if checkout_at(cwd) == cwd else None


def resource_root() -> tuple[Path, str]:
    """Where this process's resources come from, decided once for git facts
    and path identity alike (#1588): `(root, "checkout")` for the working
    directory when it is a checkout of this project, else for the checkout
    the package is imported from; `(root, "install")` for a wheel."""
    here = cwd_checkout()
    if here is not None:
        return here, "checkout"
    if CHECKOUT_ROOT is not None:
        return CHECKOUT_ROOT, "checkout"
    return INSTALL_ROOT, "install"


def roots() -> list[Path]:
    """Where a repository-relative resource may live, in order."""
    out = []
    if CHECKOUT_ROOT is not None:
        out.append(CHECKOUT_ROOT)
    out.append(INSTALL_ROOT)
    return out


def is_resource(path: str | Path) -> bool:
    """Under a resource prefix, spelled plainly: a path with `..` is never a
    resource and is never collapsed — `.venv/../x` through a symlink is not
    `x` (#1528); it is the caller's own path, resolved by the filesystem
    when a canonical form is needed."""
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        return False
    return any(p.parts[:len(prefix)] == prefix for prefix in RESOURCE_PREFIXES)


def _candidates(rel: Path) -> list[Path]:
    out = [root / rel for root in roots()]
    if rel.parts[:2] == _PACKAGE_PREFIX:
        out.append(PACKAGE_ROOT.joinpath(*rel.parts[2:]))
    return out


def _cwd_carries(rel: Path) -> bool:
    """Whether the working directory is the tree `rel` belongs to: the
    nearest existing ancestor of `rel` at depth three or deeper under
    `src/` — `src/download/prompts`, `src/data_sheets_schema/schema` — the
    same answer for a directory and for the files in it (#1535). A depth-two
    marker such as `src/data_sheets_schema` establishes nothing, and only the
    study's own source layout can be authoritative: a project's own
    `.claude/commands/` or `data/rubric/` must not hide what an install ships
    (#1500).

    Then a file absent from the working directory is absent: a staged fixture
    that deliberately omits a prompt must read `missing`, not the checkout's
    copy. A directory with no such tree — a user's data tree, or a fixture
    that carries only the old root marker — has nothing to be authoritative
    about, and the checkout's or the install's copy is read.
    """
    parts = rel.parts
    if not parts or parts[0] != "src":
        return False
    for depth in range(len(parts) - 1, 2, -1):
        if Path(*parts[:depth]).is_dir():
            return True
    return False


def physical(path: str | Path) -> Path:
    """An absolute path for reading: as spelled (an alias directory keeps its
    meaning — a schema's imports resolve beside the alias, as the generator
    reads them), except that a `..` segment is resolved through the
    filesystem, never lexically (#1528, #1570)."""
    import os
    p = Path(path)
    return p.resolve() if ".." in p.parts else Path(os.path.abspath(p))


def resource_path(path: str | Path) -> Path:
    """Where a repository-relative resource is read from, decided now.

    The working directory's copy, as the relative path it was given, when it
    exists there or the working directory carries its tree (`_cwd_carries`)
    — and always when the working directory is a checkout of this project:
    a checkout is authoritative for its absences too, so a playbook or
    prompt deleted there is missing, never another checkout's (#1617) —
    else the checkout's, else the installed copy, as an absolute path; else
    the path unchanged so the caller's own error names it. An absolute path,
    one with `..`, or one outside `RESOURCE_PREFIXES`, is returned as given.
    """
    p = Path(path)
    if p.is_absolute() or not is_resource(p) or p.exists() or _cwd_carries(p):
        return p
    if cwd_checkout() is not None:
        return p                                 # missing here is missing (#1617)
    for candidate in _candidates(p):
        if candidate.exists():
            return candidate
    return p


def repo_relative(path: str | Path, *, cwd: bool = True) -> str:
    """The repository-relative, posix form a record stores for `path`.

    A relative resource spelling is the shipped file's identity and is
    returned as given — except, for a record (`cwd=False`), when it exists in
    a working directory that is not the checkout: that is a staged tree's own
    file, recorded resolved, so the relative and the absolute spelling of one
    staged file are one identity (#1536). Anything else is resolved through
    the filesystem (so `..` follows symlinks, #1528) and anchored to the
    checkout, else to the package (a wheel's package data, spelled back as
    `src/data_sheets_schema/…`), else to the installation root when the
    result is a resource (#1487), else — with `cwd`, as the prompt registry
    always keyed a staged fixture — to the working directory; a path under
    none of them stays absolute. The provenance record passes `cwd=False`,
    so a file outside every root is recorded absolute and one file is never
    recordable under two strings (#398); a run launched from elsewhere used
    to store an absolute path for a prompt *inside* the checkout, which no
    pin could match (#673).
    """
    p = Path(path)
    here = cwd_checkout()
    if not p.is_absolute() and is_resource(p):
        # The shipped file's identity is its spelling — in any checkout of
        # this project, a worktree or a second clone included (#1588); a
        # staged tree's own file (it exists here, and here is no checkout)
        # is resolved — for the registry's key and the record alike (#1536,
        # #1573).
        if here is not None or not p.exists():
            return p.as_posix()
    try:
        resolved = p.resolve()
    except OSError:
        return p.as_posix()
    # Anchored on the one resource root this process records (#1618): a
    # file under another checkout of this project keeps its absolute
    # identity, so two checkouts' copies of one playbook are never
    # recorded under one string.
    root, kind = resource_root()
    anchors: list[tuple[Path, tuple[str, ...], bool]] = [(root, (), False)]
    if kind == "install":
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
