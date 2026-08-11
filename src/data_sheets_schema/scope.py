"""What each project's record is *about*, declared in the manifest (#422).

The VOICE launch prompt for the 2026-08-07 sweep carried a paragraph naming the
project, the pediatric dataset, a file not to read, and the issue number of the
last time it went wrong. It worked, and it is the single clearest per-GC
intervention in the pipeline: the wrong layer (the bundle is the scope), the
wrong kind of statement (a quality warning, which the priming taxonomy excludes
from the generic arm), and not generalisable (every new dataset with a companion
cohort needs someone to notice and write another paragraph).

The scope is a property of the dataset, not of the prompt. So it is declared
where the other properties of the input set live — `source_manifest.yaml` — as
data:

```yaml
scope:
  VOICE:
    referent: Bridge2AI-Voice adult dataset
    referent_id: https://doi.org/10.13026/37yb-1t42
    related_but_distinct:
      - id: https://doi.org/10.13026/h995-bt35
        manifest_key: VOICE_PEDIATRIC
        in_bundle: physionet_pediatric_1_1_0
        express_as: related_datasets
```

Two things follow that a paragraph could not do.

**It is checkable.** `check_record` reads the declaration and reports a record
whose referent is a dataset its own project declares related-but-distinct —
which is the #292 failure exactly, caught after the fact by a rule rather than
before the fact by a warning nobody can generalise.

**It is inherited.** A new dataset with a companion cohort declares two lines in
the manifest and gets the same check. Nobody has to remember the prose.

`in_bundle` is deliberate: VOICE's bundle *does* contain the pediatric PhysioNet
record, because the current VOICE documentation advertises the two releases
together. Pretending otherwise by dropping the source would make the bundle a
worse description of the evidence in order to make a rule easier to state. The
declaration says the source is there and what it means — and
`express_as: related_datasets` names the slot that carries it, which is what
the record did and what validated.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

MANIFEST = Path("data/preprocessed/source_manifest.yaml")


def load_manifest(manifest: Path = MANIFEST) -> dict[str, Any]:
    if not Path(manifest).exists():
        return {}
    return yaml.safe_load(Path(manifest).read_text(encoding="utf-8")) or {}


def all_scopes(manifest: Path = MANIFEST) -> dict[str, dict]:
    return (load_manifest(manifest).get("scope") or {})


def scope_of(project: str, manifest: Path = MANIFEST) -> dict | None:
    return all_scopes(manifest).get(project)


def related_ids(project: str, manifest: Path = MANIFEST) -> dict[str, dict]:
    """Identifier -> declaration, for datasets this project is *not* about.

    `also_known_as` is listed alongside `id` because PhysioNet mints a DOI per
    version as well as one for the project, and a check that knew only the
    project-level DOI would pass a record that named the version.
    """
    scope = scope_of(project, manifest) or {}
    out = {}
    for entry in scope.get("related_but_distinct") or []:
        for ident in [entry.get("id"), *(entry.get("also_known_as") or [])]:
            if ident:
                out[str(ident).strip()] = entry
    return out


_BARE_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/",
                 "https://dx.doi.org/", "http://dx.doi.org/", "doi:")


def _norm(identifier: Any) -> str:
    """Compare identifiers without tripping over spelling.

    `https://doi.org/10.13026/h995-bt35`, `doi:10.13026/h995-bt35`, the
    `dx.doi.org` form and the bare `10.13026/h995-bt35` all name the same
    dataset, and a check that answered "no match" for any of them would be an
    invitation to write that one (#442). Bare DOIs are not hypothetical: #402
    found 42% of nested ids in one clean-validating record are neither URI nor
    CURIE.
    """
    s = str(identifier or "").strip().rstrip("/").lower()
    for prefix in _DOI_PREFIXES:
        if s.startswith(prefix):
            return "doi:" + s[len(prefix):]
    if _BARE_DOI.match(s):
        return "doi:" + s
    return s


def check_record(project: str, record: dict | Path,
                 manifest: Path = MANIFEST) -> tuple[str, str | None]:
    """Is this record about the dataset its project declares it is about?

    - ``ok``          — the referent is not a declared related-but-distinct
      dataset. Silent on whether it *equals* `referent_id`: records legitimately
      identify themselves by a release DOI, a landing page or an ARK, and
      failing that variety would be a naming rule wearing a scope rule's coat.
    - ``out_of_scope`` — the record's `id` is a dataset the manifest declares
      distinct from this project. The #292 failure.
    - ``undeclared``  — the project declares no scope. Reported, not failed.
    - ``unreadable``  — the file could not be parsed (#444). Reported so a
      sweep of 171 records is not aborted by one of them.
    """
    if isinstance(record, Path):
        # One unparseable record must not abort a sweep of 171 (#444): report
        # the file and carry on, which is more useful than a traceback naming
        # the same file.
        try:
            record = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            return "unreadable", f"{type(exc).__name__}: {exc}"
    if not isinstance(record, dict):
        return "undeclared", "record is not a mapping"

    scope = scope_of(project, manifest)
    if not scope:
        return "undeclared", f"no scope declared for {project} in the manifest"

    got = _norm(record.get("id"))
    for ident, entry in related_ids(project, manifest).items():
        if got and got == _norm(ident):
            return "out_of_scope", (
                f"the record identifies itself as {record.get('id')}, which "
                f"{project}'s manifest scope declares a distinct dataset"
                + (f" ({entry['why']})" if entry.get("why") else "")
                + ". A record about it belongs under "
                + f"{entry.get('manifest_key', 'its own project')}; this one "
                + f"may reference it through `{entry.get('express_as', 'related_datasets')}`")
    return "ok", None


def _walk(node: Any, trail: str = ""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{trail}.{k}" if trail else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{trail}[{i}]")
    else:
        yield trail, node


def foreign_references(project: str, record: dict | Path,
                       manifest: Path = MANIFEST) -> list[dict]:
    """Where a related-but-distinct dataset's identifiers appear outside the
    slot the manifest declares for them (#441).

    `check_record` reads the record's `id`, which settles what the record is
    *about*. It said 171 of 171 in scope while 32 of them placed the pediatric
    release inside VOICE's own `resources`, `distribution_formats[].access_urls`
    and `file_collections[].download_url` — the #292 shape one level down: not a
    record about the wrong dataset, but a record absorbing the other dataset
    into its own distribution.

    Reported, never a verdict. A record may legitimately cite the related
    dataset's page as a resource — that page is in its bundle — and the line
    between citing and absorbing is a judgement this surfaces rather than
    settles. `express_as` names where the relation belongs; anything under that
    slot is excluded.
    """
    if isinstance(record, Path):
        try:
            record = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:              # noqa: PERF203
            return [{"path": str(record), "value": None,
                     "unreadable": f"{type(exc).__name__}: {exc}"}]
    if not isinstance(record, dict):
        return []

    wanted = {}
    for ident, entry in related_ids(project, manifest).items():
        wanted[_norm(ident)] = entry
    if not wanted:
        return []

    out = []
    for trail, value in _walk(record):
        if not isinstance(value, str):
            continue
        entry = wanted.get(_norm(value))
        if entry is None:
            continue
        slot = entry.get("express_as") or "related_datasets"
        if slot and slot in trail:
            continue
        out.append({"path": trail, "value": value,
                    "dataset": entry.get("name"), "express_as": slot})
    return out


def check_manifest(manifest: Path = MANIFEST) -> list[dict]:
    """Is every scope declaration internally consistent? One row per problem.

    A declaration that names a project or a source that does not exist is worse
    than none: it reads as a control and enforces nothing.
    """
    data = load_manifest(manifest)
    projects = data.get("projects") or {}
    problems: list[dict] = []
    for project, scope in (data.get("scope") or {}).items():
        if project not in projects:
            problems.append({"project": project,
                             "problem": "scope declared for a project the "
                                        "manifest has no sources for"})
        if not scope.get("referent_id"):
            problems.append({"project": project,
                             "problem": "no referent_id: the scope says what "
                                        "the record is about in prose only"})
        ids = {e.get("id") for e in scope.get("related_but_distinct") or []}
        for entry in scope.get("related_but_distinct") or []:
            key = entry.get("manifest_key")
            if key and key not in projects:
                problems.append({"project": project,
                                 "problem": f"related dataset names manifest "
                                            f"key {key!r}, which does not exist"})
            src = entry.get("in_bundle")
            if src:
                known = {e.get("id") for e in projects.get(project) or []
                         if isinstance(e, dict)}
                if src not in known:
                    problems.append({
                        "project": project,
                        "problem": f"related dataset claims source {src!r} is "
                                   f"in this bundle; the manifest lists no "
                                   f"such source for {project}"})
        if scope.get("referent_id") in ids:
            problems.append({"project": project,
                             "problem": "the referent is also listed as "
                                        "related-but-distinct"})

        # Symmetry (#443). A one-directional declaration checks one direction:
        # a pediatric record identifying itself by the adult DOI would pass and
        # the asymmetry would be invisible. Only required when the other side
        # has a scope block at all — a related dataset outside this corpus
        # legitimately has no entry here.
        for entry in scope.get("related_but_distinct") or []:
            other = entry.get("manifest_key")
            other_scope = (data.get("scope") or {}).get(other)
            if not other or not other_scope:
                continue
            back = {e.get("manifest_key")
                    for e in other_scope.get("related_but_distinct") or []}
            if project not in back:
                problems.append({
                    "project": project,
                    "problem": f"declares {other} related-but-distinct, but "
                               f"{other} does not say the same of {project}; "
                               "the check would then run in one direction only"})
    return problems
