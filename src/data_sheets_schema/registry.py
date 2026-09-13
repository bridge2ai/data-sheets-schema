"""The selected source manifest is the project registry (#623).

Through 2026-09 the project universe was `constants.PROJECTS`, a list of the
study's five datasets, and every CLI entry point that names a dataset gated
its `--project` on it with `click.Choice`. A dataset declared only in a
manifest was refused before the command opened that manifest, so onboarding
a new dataset meant editing Python (#630, §1.1). The Make targets carried a
second, divergent copy of the list (#637).

Here the registry is whichever manifest the caller selected: the study's
`data/preprocessed/source_manifest.yaml` by default, any other file with
`--manifest`, or none. A project is a key of the manifest's `projects`
mapping whose value is a project record — a list of sources, or a mapping
that carries them. A key ending in `_source_dir` is the legacy per-project
override the manifest stores beside the projects (`VOICE_PEDIATRIC_source_dir`,
#302) and is never a project (#626).

`constants.PROJECTS` stays: it names the study's corpus for the analysis
scripts that compare arms, and `SHARED_CORPUS_GROUPS` is a fact about that
corpus. What changes is that nothing a general user runs is gated on it.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

#: The study's manifest, used when a caller selects nothing else.
DEFAULT_MANIFEST = Path("data/preprocessed/source_manifest.yaml")

#: The legacy override key: `<PROJECT>_source_dir` beside the projects.
_SOURCE_DIR_SUFFIX = "_source_dir"

#: The suffix a project's document bundle carries by convention (#725). The
#: directory is `chunking.CONCAT_DIR`, read at call time so a test or caller
#: that repoints it repoints the registry too (#1367 review, must-fix 10).
DOCUMENT_BUNDLE_SUFFIX = "_preprocessed.txt"

#: "The caller did not choose": `select_manifest` then decides by rule.
AUTO = object()


def _concat_dir() -> Path:
    from data_sheets_schema import chunking
    return chunking.anchored(chunking.CONCAT_DIR)


def default_manifest_path() -> Path:
    """The default manifest from here — one rule for the registry, the
    chunk manifests and the profile (#1491): the working directory's, else
    the nearest ancestor's (an installed package run from a subdirectory of
    the user's project, #1467), else the checkout's (`anchored`), which
    may not exist."""
    from data_sheets_schema.chunking import anchored
    rel = Path(DEFAULT_MANIFEST)
    if rel.exists():
        return rel
    for ancestor in Path.cwd().resolve().parents:
        if (ancestor / rel).exists():
            return ancestor / rel
    return anchored(rel)


@dataclass(frozen=True)
class Registry:
    """One selected manifest, read once.

    `path` is None for a run that selected no manifest at all — an external
    bundle passed with `--bundle` and nothing declaring it. Such a registry
    declares no projects and no context, and says so, rather than answering
    from the study's file (#621).
    """
    path: Path | None
    data: dict[str, Any] = field(default_factory=dict)

    # ---- projects ---------------------------------------------------------
    def projects(self) -> list[str]:
        """Every project the manifest declares, in manifest order."""
        raw = self.data.get("projects")
        if not isinstance(raw, dict):
            return []
        return [k for k, v in raw.items() if _is_project_record(k, v)]

    def declares(self, project: str) -> bool:
        return project in self.projects()

    def entry(self, project: str) -> Any:
        """The project's own record: a list of sources, or a mapping."""
        raw = self.data.get("projects")
        return raw.get(project) if isinstance(raw, dict) else None

    def sources(self, project: str) -> list[dict[str, Any]]:
        e = self.entry(project)
        if isinstance(e, list):
            return [s for s in e if isinstance(s, dict)]
        if isinstance(e, dict):
            s = e.get("sources")
            return [x for x in s if isinstance(x, dict)] if isinstance(s, list) else []
        return []

    # ---- per-project overrides -------------------------------------------
    def _setting(self, project: str, key: str) -> Any:
        """A per-project setting: `projects.<P>.<key>` on a mapping record,
        else the legacy sibling key `projects.<P>_<key>` (#302)."""
        e = self.entry(project)
        if isinstance(e, dict) and e.get(key) is not None:
            return e.get(key)
        raw = self.data.get("projects")
        if isinstance(raw, dict):
            legacy = raw.get(f"{project}_{key}")
            if legacy is not None:
                return legacy
        return None

    def source_dir(self, project: str) -> Path | None:
        """Where the project's preprocessed individual files are, when they
        are not under `data/preprocessed/individual/<project>`: the override
        that lets VOICE_PEDIATRIC read VOICE's directory (#302)."""
        v = self._setting(project, "source_dir")
        return Path(v) if isinstance(v, str) and v else None

    def raw_dir(self, project: str) -> Path | None:
        """Where the project's raw downloads are, when they are not under
        the input directory's `<project>` subdirectory (#637)."""
        v = self._setting(project, "raw_dir")
        return Path(v) if isinstance(v, str) and v else None

    def preprocessed_directory(self, project: str, root: Path) -> Path:
        """Declared source_dir wins; a pipeline root supplies only the fallback.

        Preprocessing, quality checks and concatenation must choose the same
        files even when the caller relocates its default pipeline directory.
        """
        return self.source_dir(project) or (Path(root) / project)

    def shared_source_project(self, project: str, preprocessed_root: Path | None = None) -> str | None:
        """Resolve the legacy shared-directory declaration only when its
        source list is a subset of the owner's. A mapping's source_dir is
        an output override; it never implies that raw work can be skipped."""
        entry = self.entry(project)
        if isinstance(entry, dict) or self.raw_dir(project) is not None:
            return None
        shared = self.source_dir(project)
        if shared is None:
            return None
        source_pairs = lambda name: {(s.get("raw_file"), s.get("processed_file"))
                                     for s in self.sources(name)}
        wanted = source_pairs(project)
        if not wanted or any(not all(pair) for pair in wanted):
            return None
        for owner in self.projects():
            if owner == project:
                continue
            roots = [Path("data/preprocessed/individual")]
            if preprocessed_root is not None:
                roots.append(preprocessed_root)
            candidates = [self.preprocessed_directory(owner, root) for root in roots]
            if (any(shared.resolve() == path.resolve() for path in candidates)
                    and wanted <= source_pairs(owner)):
                return owner
        return None

    def bundle(self, project: str, concat_dir: Path | None = None) -> Path:
        """The project's document bundle: declared as `bundle` on a mapping
        record, else `<concat_dir>/<project>_preprocessed.txt` by convention."""
        v = self._setting(project, "bundle")
        if isinstance(v, str) and v:
            return Path(v)
        return (concat_dir or _concat_dir()) / f"{project}{DOCUMENT_BUNDLE_SUFFIX}"

    def bundles(self, project: str, concat_dir: Path | None = None) -> list[Path]:
        """Every bundle this manifest resolves for `project`: the declared or
        conventional document bundle, and every other kind the study keeps
        beside it (`chunking.BUNDLE_SUFFIXES`: with-crate, crate-only,
        healthsheet) — the de-novo, crate-only and healthsheet arms read
        those, and they are the project's inputs as much as the document
        bundle is (#1367 round 2, #1385)."""
        from data_sheets_schema import chunking
        base = concat_dir or _concat_dir()
        out = [self.bundle(project, concat_dir)]
        if self.path is not None and self.path.resolve() == default_manifest_path().resolve():
            out += [base / f"{project}{s}" for s in chunking.BUNDLE_SUFFIXES]
        seen: list[Path] = []
        for b in out:
            if b not in seen:
                seen.append(b)
        return seen

    def declares_bundle(self, project: str, bundle: Path,
                        concat_dir: Path | None = None) -> bool:
        """Whether `bundle` is one this manifest resolves for `project`.

        The test that decides whether a run *used* the manifest (#621): a
        run given an explicit bundle that is not the manifest's own did not
        consult it for that input, and a record that hashed the manifest as
        an input would attest a file the run never read.
        """
        if not self.declares(project):
            return False
        try:
            target = Path(bundle).resolve()
            return any(target == b.resolve() for b in self.bundles(project, concat_dir))
        except OSError:
            return False

    # ---- identity ----------------------------------------------------------
    def md5(self) -> str | None:
        if self.path is None or not self.path.exists():
            return None
        h = hashlib.md5()
        with self.path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()


def _is_project_record(key: str, value: Any) -> bool:
    if not isinstance(key, str) or key.endswith(_SOURCE_DIR_SUFFIX):
        return False
    if isinstance(value, list):
        return True
    return isinstance(value, dict) and ("sources" in value or "bundle" in value
                                        or "raw_dir" in value or "source_dir" in value)


def load_registry(path: Path | str | None = DEFAULT_MANIFEST) -> Registry:
    """The registry at `path`, or an empty one for `None`.

    A default path that does not exist (a checkout with no study data, an
    installed package) is an empty registry too — the caller then has to
    say which dataset it means, which is the honest state.
    """
    if path is None:
        return Registry(path=None)
    p = Path(path)
    if p == DEFAULT_MANIFEST and not p.exists():
        p = default_manifest_path()
    if not p.exists():
        return Registry(path=p)
    import yaml
    try:
        # One parse per file per process (#1203): every `RunSpec` selects
        # its manifest through here, and re-reading a 300-line YAML on each
        # construction cost ~50 ms (#1367 round 2, #1394).
        from data_sheets_schema.schema_cache import load_yaml
        data = load_yaml(p) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise click.ClickException(f"manifest {p} could not be read: {exc}") from exc
    if not isinstance(data, dict):
        raise click.ClickException(f"manifest {p} is not a mapping")
    return Registry(path=p, data=data)


def validate_context(registry: Registry, project: str) -> None:
    """Reject a declared context that request assembly cannot honor (#1406).

    Optional sections may be absent. Once supplied, their types must be
    meaningful to every reader; dropping invalid ranking changes the run.
    """
    data = registry.data

    def fail(field: str, detail: str) -> None:
        raise click.ClickException(f"invalid source manifest {registry.path}: {field} {detail}")

    def text(value, field):
        if not isinstance(value, str) or not value.strip():
            fail(field, "must be a nonempty string")

    def tier(value, field):
        if isinstance(value, bool) or not str(value).isdigit() or int(value) < 1:
            fail(field, "must be a positive integer")

    raw_projects = data.get("projects", {})
    if not isinstance(raw_projects, dict):
        fail("projects", "must be a mapping")
    entry = raw_projects.get(project)
    if entry is not None:
        sources = entry.get("sources", []) if isinstance(entry, dict) else entry
        if not isinstance(sources, list):
            fail(f"projects.{project}.sources", "must be a list")
        for i, source in enumerate(sources):
            field = f"projects.{project}.sources[{i}]"
            if not isinstance(source, dict):
                fail(field, "must be a mapping")
            if source.get("priority") is not None:
                tier(source["priority"], field + ".priority")
            for key in ("id", "source_type", "superseded_by"):
                if key in source and source[key] is not None:
                    text(source[key], field + "." + key)
    table = data.get("source_priority", {})
    if not isinstance(table, dict):
        fail("source_priority", "must be a mapping of integer tiers to source-type lists")
    for rank, types in table.items():
        tier(rank, "source_priority tier")
        if not isinstance(types, list):
            fail(f"source_priority.{rank}", "must be a list")
        for value in types:
            text(value, f"source_priority.{rank}")
    for section in ("naming", "scope"):
        records = data.get(section, {})
        if not isinstance(records, dict):
            fail(section, "must be a mapping")
        if project not in records:
            continue
        declaration = records[project]
        if not isinstance(declaration, dict):
            fail(f"{section}.{project}", "must be a mapping")
        keys = (("canonical_label", "programme", "gc_name") if section == "naming"
                else ("referent", "referent_note"))
        for key in keys:
            if key in declaration:
                text(declaration[key], f"{section}.{project}.{key}")
        if section == "scope":
            related = declaration.get("related_but_distinct", [])
            if not isinstance(related, list):
                fail(f"scope.{project}.related_but_distinct", "must be a list")
            from data_sheets_schema.scope import malformed_in
            problems = malformed_in(declaration)
            if problems:
                fail(f"scope.{project}.related_but_distinct", "; ".join(p["problem"] for p in problems))


def select_manifest(project: str, bundle: Path | str | None,
                    requested=AUTO) -> Path | None:
    """The one rule for which manifest a run consults (#621, #1367 review,
    must-fix 2), applied wherever a spec or a record is built rather than
    only in the API CLI.

    `requested` is a path the caller named, `None` for "none", or `AUTO`
    when the caller said nothing. Under `AUTO` the default manifest is
    selected only when it declares `project` and — where a bundle is given
    — that bundle is the one it declares for the project. A study key with
    an external bundle selects none: the study's naming, scope and ranking
    describe a bundle the run is not reading, and hashing the study's file
    into the record would attest an input the run never consulted.
    """
    if requested is None:
        return None
    if requested is not AUTO:
        path = Path(requested)
        if not path.is_file():
            raise click.ClickException(f"selected source manifest does not exist or is not a file: {path}")
        validate_context(load_registry(path), project)
        return path
    reg = load_registry(default_manifest_path())
    if not reg.declares(project):
        return None
    if bundle is None or reg.declares_bundle(project, Path(bundle)):
        validate_context(reg, project)
        return reg.path
    return None


# ---- click integration --------------------------------------------------

def manifest_option(**kw):
    """The `--manifest` option every dataset-naming command shares."""
    return click.option("--manifest", type=click.Path(), default=str(DEFAULT_MANIFEST),
                        show_default=True, is_eager=True,
                        help="source manifest that declares the projects; the registry "
                             "for --project", **kw)


def project_choice(ctx: click.Context, param: click.Parameter, value):
    """Validate `--project` against the manifest selected on the same command.

    Replaces `click.Choice(PROJECTS)`. The message names the registry and
    what it declares, so a typo and a dataset that has not been declared
    read differently from "not one of AI_READI, CHORUS, CM4AI, VOICE".
    `--manifest` is eager so its value is parsed before this callback runs.
    """
    if value is None or value == () or value == []:
        return value
    manifest = selected_manifest(ctx)
    reg = load_registry(manifest)
    values = list(value) if isinstance(value, (tuple, list)) else [value]
    declared = reg.projects()
    unknown = [v for v in values if v not in declared]
    if unknown:
        where = (f"{reg.path} declares {', '.join(declared) or 'no projects'}"
                 if reg.path is not None and reg.path.exists()
                 else f"manifest {manifest} does not exist")
        how = ("--manifest" if "manifest" in ctx.params
               else "`d4d --manifest PATH <command>` (or D4D_MANIFEST=PATH)")
        raise click.BadParameter(
            f"{', '.join(map(repr, unknown))}: not declared by the selected manifest "
            f"({where}). Declare the dataset under `projects:` in a manifest and pass "
            f"{how}, or name one the manifest declares.")
    return value


def selected_manifest(ctx: click.Context) -> str:
    """The manifest a command's `--project` is validated against: the
    command's own `--manifest` when it has one, else the root group's
    `d4d --manifest` / `D4D_MANIFEST` (#1367 review, must-fix 4: fourteen
    commands validate a project but never needed a manifest of their own),
    else the study's."""
    own = ctx.params.get("manifest")
    if own:
        return str(own)
    root = ctx.find_root()
    if root is not ctx and root.params.get("manifest"):
        return str(root.params["manifest"])
    return str(DEFAULT_MANIFEST)


def projects_for(ctx_or_manifest, project=None) -> list[str]:
    """`[project]` when one was given, else every project the manifest
    declares — the loop body of every "default: all" command."""
    manifest = (selected_manifest(ctx_or_manifest) if isinstance(ctx_or_manifest, click.Context)
                else ctx_or_manifest)
    if project:
        return [project] if isinstance(project, str) else list(project)
    return load_registry(manifest).projects()
