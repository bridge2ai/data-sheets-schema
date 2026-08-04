"""Refuse to average scores that were measured against different maxima.

Rubric20's total was 84 in the LLM path and 88 in the presence path for a long
time (#273). The judge's own prompt handed the model a `"max_points": 84`
template, so **167 committed evaluations record 84** while everything generated
after the correction records 88.

Those records are not wrong — each states the denominator it used, which is what
separates them from the bug that produced them, where every layer agreed on 84
and nothing recorded a dissent. What is wrong is *pooling* them. An average
score over a mix of 84-scored and 88-scored records is not a score, and an
average percentage is worse, because percentages look comparable while being
computed against different maxima.

The failure this guards against is quiet: a mean of the two populations lands
somewhere plausible and reads as a result. So the default here is to refuse —
`common_denominator` raises rather than picking one — and callers that must
produce a report group by denominator and say so.

`RUBRIC20_MAX_SCORE` remains the right **fallback for a record that omits
`max_points`**. It is not a substitute for reading one that has it (#274).
"""

from __future__ import annotations

from typing import Any, Iterable

from data_sheets_schema.constants import RUBRIC20_MAX_SCORE


class MixedDenominators(ValueError):
    """Results measured against more than one maximum were pooled."""

    def __init__(self, seen: Iterable[int]):
        self.seen = sorted(seen)
        super().__init__(
            f"results span {len(self.seen)} denominators: {self.seen}. "
            "These were measured against different maxima and cannot be "
            "averaged; group by denominator, or re-run the older set.")


def denominator_of(result: dict[str, Any],
                   default: int = RUBRIC20_MAX_SCORE) -> int:
    """The maximum this single record was scored against."""
    return (result.get("overall_score") or {}).get("max_points") or default


def denominators(results: Iterable[dict[str, Any]],
                 default: int = RUBRIC20_MAX_SCORE) -> set[int]:
    return {denominator_of(r, default) for r in results}


def common_denominator(results: Iterable[dict[str, Any]],
                       default: int = RUBRIC20_MAX_SCORE) -> int:
    """The one maximum shared by every record, or raise.

    Raising is the point. Returning a default, a max, or the most common value
    would let an aggregate over two instruments look like an aggregate over one.
    """
    results = list(results)
    if not results:
        return default
    seen = denominators(results, default)
    if len(seen) > 1:
        raise MixedDenominators(seen)
    return seen.pop()


def group_by_denominator(results: Iterable[dict[str, Any]],
                         default: int = RUBRIC20_MAX_SCORE
                         ) -> dict[int, list[dict[str, Any]]]:
    """Partition results so each group *can* be pooled.

    For report generators, which should still produce a report when the corpus
    spans two instruments — just not a single number spanning both.
    """
    groups: dict[int, list[dict[str, Any]]] = {}
    for result in results:
        groups.setdefault(denominator_of(result, default), []).append(result)
    return dict(sorted(groups.items()))


def denominator_label(results: Iterable[dict[str, Any]],
                      default: int = RUBRIC20_MAX_SCORE) -> str:
    """A denominator to print, marked when it is not one denominator.

    `MIXED(84/88)` rather than a number, so a reader of the rendered table sees
    the same thing the code saw instead of a figure that looks authoritative.
    """
    seen = sorted(denominators(list(results), default))
    if len(seen) == 1:
        return str(seen[0])
    return "MIXED(" + "/".join(str(n) for n in seen) + ")"


def pooling_warning(results: Iterable[dict[str, Any]],
                    default: int = RUBRIC20_MAX_SCORE) -> str:
    """A note to put at the top of a report, or "" when there is nothing to say."""
    groups = group_by_denominator(results, default)
    if len(groups) <= 1:
        return ""
    counts = ", ".join(f"{len(v)} scored out of {k}" for k, v in groups.items())
    return (
        f"> ⚠️ **These results span {len(groups)} different maxima** ({counts}).\n"
        "> Scores and percentages are reported per group and never pooled "
        "across them: an average over records measured against different\n"
        "> maxima is not a score. See issue #275.\n\n")
