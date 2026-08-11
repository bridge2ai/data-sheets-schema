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


def _norm(identifier: Any) -> str:
    """Compare identifiers without tripping over trailing slashes or scheme.

    `https://doi.org/10.13026/h995-bt35` and `doi:10.13026/h995-bt35` name the
    same dataset, and a check that answered "no match" for the second would be
    an invitation to write the second.
    """
    s = str(identifier or "").strip().rstrip("/").lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if s.startswith(prefix):
            return "doi:" + s[len(prefix):]
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
    """
    if isinstance(record, Path):
        record = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
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
    return problems
