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

#: Where a project's document bundle lives by convention, and the suffix each
#: bundle kind carries (#725). Mirrors `chunking.BUNDLE_SUFFIXES`, which stays
#: the authority for chunking; this is the registry's view of the same layout.
CONCAT_DIR = Path("data/preprocessed/concatenated")
DOCUMENT_BUNDLE_SUFFIX = "_preprocessed.txt"


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

    def bundle(self, project: str, concat_dir: Path | None = None) -> Path:
        """The project's document bundle: declared as `bundle` on a mapping
        record, else `<concat_dir>/<project>_preprocessed.txt` by convention."""
        v = self._setting(project, "bundle")
        if isinstance(v, str) and v:
            return Path(v)
        return (concat_dir or CONCAT_DIR) / f"{project}{DOCUMENT_BUNDLE_SUFFIX}"

    def declares_bundle(self, project: str, bundle: Path,
                        concat_dir: Path | None = None) -> bool:
        """Whether `bundle` is the one this manifest resolves for `project`.

        The test that decides whether a run *used* the manifest (#621): a
        run given an explicit bundle that is not the manifest's own did not
        consult it for that input, and a record that hashed the manifest as
        an input would attest a file the run never read.
        """
        if not self.declares(project):
            return False
        try:
            return Path(bundle).resolve() == self.bundle(project, concat_dir).resolve()
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
    if not p.exists():
        return Registry(path=p)
    import yaml
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise click.ClickException(f"manifest {p} could not be read: {exc}") from exc
    if not isinstance(data, dict):
        raise click.ClickException(f"manifest {p} is not a mapping")
    return Registry(path=p, data=data)


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
    manifest = ctx.params.get("manifest", str(DEFAULT_MANIFEST))
    reg = load_registry(manifest)
    values = list(value) if isinstance(value, (tuple, list)) else [value]
    declared = reg.projects()
    unknown = [v for v in values if v not in declared]
    if unknown:
        where = (f"{reg.path} declares {', '.join(declared) or 'no projects'}"
                 if reg.path is not None and reg.path.exists()
                 else f"manifest {manifest} does not exist")
        raise click.BadParameter(
            f"{', '.join(map(repr, unknown))}: not declared by the selected manifest "
            f"({where}). Declare the dataset under `projects:` in a manifest and pass "
            "--manifest, or name one the manifest declares.")
    return value


def projects_for(ctx_or_manifest, project=None) -> list[str]:
    """`[project]` when one was given, else every project the manifest
    declares — the loop body of every "default: all" command."""
    manifest = (ctx_or_manifest.params.get("manifest") if isinstance(ctx_or_manifest, click.Context)
                else ctx_or_manifest)
    if project:
        return [project] if isinstance(project, str) else list(project)
    return load_registry(manifest).projects()
