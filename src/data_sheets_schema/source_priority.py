"""Which source wins when two of them state different things.

The uniform rules have always said to represent a disagreement rather than
silently select one side. That is right, and it left a gap a v4 CHORUS record
named exactly:

    No instance count is asserted because the two sources give different
    figures (over 45,000 and 50,000) for the same released dataset and **the
    bundle offers no basis for preferring one**.

The rule was followed correctly. The basis was missing. This supplies it.

## Declared in the manifest, not in a prompt

#422's principle: a constraint in the launch text is per-run adaptation that no
future dataset inherits and no test can see. `source_priority` in
`source_manifest.yaml` is checkable and is inherited by any project that
declares its sources.

## A tier is about proximity to the release, not trust

Tier 1 is the release describing itself. Tier 3 holds peer-reviewed work, which
is authoritative on method and routinely behind the current release on counts —
being lower than the project's own documentation is a statement about currency,
not about quality.

## Equal tiers do not decide

Two sources of the same tier that disagree leave the question open, and the
record should represent the disagreement as before. Priority resolves a
disagreement; it does not manufacture a winner where it has nothing to say.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

MANIFEST = Path("data/preprocessed/source_manifest.yaml")

#: Returned when nothing ranks a source. Sorts below every declared tier, so an
#: unranked source never wins by accident — but it is distinguishable from
#: tier 5, which somebody chose.
UNRANKED = 99


def _manifest(path: Path | None = None) -> dict[str, Any]:
    import yaml
    return yaml.safe_load((path or MANIFEST).read_text(encoding="utf-8")) or {}


def tiers(manifest: dict[str, Any] | None = None) -> dict[str, int]:
    """source_type -> tier, flattened from the declared table."""
    data = manifest if manifest is not None else _manifest()
    out: dict[str, int] = {}
    for tier, types in (data.get("source_priority") or {}).items():
        for source_type in types or ():
            out[str(source_type)] = int(tier)
    return out


def sources(project: str, manifest: dict[str, Any] | None = None
            ) -> list[dict[str, Any]]:
    data = manifest if manifest is not None else _manifest()
    entry = (data.get("projects") or {}).get(project)
    return [s for s in entry if isinstance(s, dict)] if isinstance(entry, list) \
        else []


def priority_of(source: dict[str, Any],
                table: dict[str, int] | None = None) -> tuple[int, str]:
    """(tier, why) for one source entry.

    An explicit `priority:` on the source wins over its type's tier, because an
    override is a line someone deliberately wrote.
    """
    table = table if table is not None else tiers()
    if source.get("priority") is not None:
        return int(source["priority"]), "declared on the source"
    source_type = source.get("source_type")
    if source_type in table:
        return table[source_type], f"tier of source_type {source_type!r}"
    return UNRANKED, (f"source_type {source_type!r} is in no tier"
                      if source_type else "the source declares no source_type")


def superseded_by(project: str, manifest: dict[str, Any] | None = None
                  ) -> dict[str, str]:
    """`{source id: the id that replaced it}` from the manifest (#600).

    The manifest has recorded this for five sources all along — AI-READI's
    documentation and FAIRhub entries, CM4AI's October release, VOICE 3.0.0 —
    and the first version of the resolver read only `source_type`, so a
    superseded release tied with the one replacing it and the tie meant "cannot
    decide".

    Supersession is the strongest signal there is: it is a direct statement
    that one source replaces another, made by whoever curated the manifest. It
    outranks a tier, which is only a claim about a *kind* of source.
    """
    out = {}
    for source in sources(project, manifest):
        replacement = source.get("superseded_by")
        if replacement and source.get("id"):
            out[str(source["id"])] = str(replacement)
    return out


def _supersedes(project: str, a: str, b: str,
                manifest: dict[str, Any] | None = None) -> str | None:
    """Which of `a`/`b` replaced the other, directly or through a chain."""
    chain = superseded_by(project, manifest)

    def replaces(newer: str, older: str) -> bool:
        seen, cur = set(), older
        while cur in chain and cur not in seen:
            seen.add(cur)
            cur = chain[cur]
            if cur == newer:
                return True
        return False

    if replaces(a, b):
        return a
    if replaces(b, a):
        return b
    return None


def ranked(project: str, manifest: dict[str, Any] | None = None
           ) -> list[dict[str, Any]]:
    """Every source for a project, strongest first.

    Ties keep manifest order: a stable order makes the listing reproducible,
    and does *not* imply the first of two tied sources should win a
    disagreement — see `decide`.
    """
    table = tiers(manifest)
    out = []
    for index, source in enumerate(sources(project, manifest)):
        tier, why = priority_of(source, table)
        out.append({**source, "priority": tier, "priority_basis": why,
                    "manifest_index": index})
    return sorted(out, key=lambda s: (s["priority"], s["manifest_index"]))


def decide(project: str, source_ids: list[str],
           manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Which of these sources should settle a disagreement between them.

    Returns `winner: None` when the strongest tier is shared, because priority
    then has nothing to say — the record should represent the disagreement, as
    it did before this existed.
    """
    table = tiers(manifest)
    by_id = {s.get("id"): s for s in sources(project, manifest)}
    known, unknown = [], []
    for sid in source_ids:
        if sid in by_id:
            tier, why = priority_of(by_id[sid], table)
            known.append({"id": sid, "priority": tier, "basis": why})
        else:
            unknown.append(sid)
    if not known:
        return {"winner": None, "reason": "none of these sources is declared",
                "unknown": unknown, "candidates": []}
    # Supersession first: a source the manifest says was replaced loses to its
    # replacement whatever their tiers, because that is a direct statement
    # about these two sources rather than a claim about their kinds (#600).
    if len(known) == 2:
        winner = _supersedes(project, known[0]["id"], known[1]["id"], manifest)
        if winner:
            loser = next(s["id"] for s in known if s["id"] != winner)
            return {"winner": winner, "candidates": known, "unknown": unknown,
                    "priority": next(s["priority"] for s in known
                                     if s["id"] == winner),
                    "reason": (f"the manifest declares {loser} superseded by "
                               f"{winner}, which settles it regardless of tier")}

    best = min(s["priority"] for s in known)
    top = [s for s in known if s["priority"] == best]
    if len(top) > 1:
        return {"winner": None, "candidates": known, "unknown": unknown,
                "reason": (f"{len(top)} sources share the strongest tier "
                           f"({best}); priority cannot decide between them, so "
                           "represent the disagreement")}
    return {"winner": top[0]["id"], "priority": best, "candidates": known,
            "unknown": unknown,
            "reason": (f"{top[0]['id']} is tier {best} ({top[0]['basis']}), "
                       "stronger than every other source named")}


def unranked_types(manifest: dict[str, Any] | None = None
                   ) -> dict[str, list[str]]:
    """source_types in use that no tier covers, by project.

    A source nobody ranked cannot win, which is safe — but it also cannot lose
    on the record, so it is worth naming rather than leaving to be discovered
    when a disagreement turns on it.
    """
    data = manifest if manifest is not None else _manifest()
    table = tiers(data)
    out: dict[str, list[str]] = {}
    for project in (data.get("projects") or {}):
        missing = sorted({
            str(s.get("source_type")) for s in sources(project, data)
            if s.get("priority") is None and s.get("source_type") not in table})
        if missing:
            out[project] = missing
    return out
