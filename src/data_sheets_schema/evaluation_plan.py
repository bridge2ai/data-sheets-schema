"""What to evaluate, derived from the canonical set rather than restated (#315).

The semantic evaluation count has been written down four times and been wrong
three of them, in both directions:

    8   4 projects x 2 rubrics          full records only, unstated
    6   3 projects x 2 rubrics          after VOICE failed selection; still full-only
    12  3 projects x 2 variants x 2     correct only while VOICE and VOICE_PEDIATRIC
                                        have no canonical record
    20  5 projects x 2 variants x 2     correct only after a successful rerun

Every one was a number typed into a note and then quoted from that note. The
count is a function of how many projects end up with a canonical record, which
is not knowable until `d4d runs select --execute` has run — and for VOICE it is
genuinely uncertain, because `related_to` may recur (#292).

So this module does not know a count. It enumerates the canonical records, pairs
each with the rubrics, and reports what falls out. Nothing here should ever be
quoted as a constant.

`plan()` **raises** on an empty canonical set rather than returning an empty
plan. Zero evaluations and "selection has not been run yet" are different
states, and a plan of length zero reads as the first while usually meaning the
second.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: The semantic rubrics an evaluation sweep runs. Both apply to every record;
#: rubric10 and rubric20 measure different things and neither subsumes the other.
SEMANTIC_RUBRICS = ("rubric10_semantic", "rubric20_semantic")

#: Which record variant each path represents. `canonical_runs` reports both, and
#: they are separate evaluations — a core record is scored against the same
#: rubric as its full counterpart, and the two scores are the core/full contrast.
VARIANTS = ("full", "core")


class NothingSelected(RuntimeError):
    """No project has a canonical record, so there is nothing to evaluate.

    Distinguished from an empty plan on purpose. `d4d runs select --execute`
    not having been run is the usual cause, and reporting "0 evaluations" would
    read as a finished scoping exercise rather than an unstarted one.
    """

    def __init__(self, concat_dir: Path | None):
        # The location is built outside the f-string: a multi-line expression
        # inside a replacement field is PEP 701, valid on 3.12+ and a
        # SyntaxError on the 3.10 and 3.11 this project still supports. It
        # parsed fine locally on 3.13 and broke all three CI matrix entries.
        where = concat_dir or "the default concatenated directory"
        super().__init__(
            f"no canonical record found under {where}. "
            "Run `d4d runs select --execute` first; "
            "`d4d runs canonical --missing` names the projects without one.")


@dataclass(frozen=True)
class Evaluation:
    """One record, one rubric — the unit an evaluation sweep bills for."""

    project: str
    variant: str
    rubric: str
    path: Path

    @property
    def label(self) -> str:
        return f"{self.project}/{self.variant}/{self.rubric}"


def plan(concat_dir: Path | None = None, config: str | None = None,
         rubrics: tuple[str, ...] = SEMANTIC_RUBRICS) -> list[Evaluation]:
    """Every evaluation the canonical set implies, in a stable order.

    Reads the canonical marks rather than any project list: a project without a
    canonical record contributes nothing, which is the whole reason the count
    cannot be stated in advance.
    """
    from data_sheets_schema.runs import canonical_runs

    found = canonical_runs(concat_dir=concat_dir, config=config)
    out: list[Evaluation] = []
    for project in sorted(found):
        record = found[project]
        for variant in VARIANTS:
            # `canonical_runs` reports the two record paths as top-level keys
            # named for the variant, alongside `label`, `method` and
            # `provenance`. A variant missing from a marked run is skipped
            # rather than guessed at — the same discipline as a project with no
            # mark at all.
            path = record.get(variant)
            if not path:
                continue
            for rubric in rubrics:
                out.append(Evaluation(project=project, variant=variant,
                                      rubric=rubric, path=Path(path)))
    if not out:
        raise NothingSelected(concat_dir)
    return out


def summarise(evaluations: list[Evaluation]) -> str:
    """A line stating how the count was arrived at, not just the count.

    The failure this module exists for is a bare number being quoted onward, so
    the derivation travels with it.
    """
    projects = sorted({e.project for e in evaluations})
    variants = sorted({e.variant for e in evaluations})
    rubrics = sorted({e.rubric for e in evaluations})
    return (f"{len(evaluations)} evaluations = {len(projects)} projects "
            f"({', '.join(projects)}) x {len(variants)} variants "
            f"({', '.join(variants)}) x {len(rubrics)} rubrics")
