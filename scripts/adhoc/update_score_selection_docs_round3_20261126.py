"""Update selection guidance for issues 6399/6401, 2026-11-26.

Inputs: reviewed round-2 operator skill. Output: roster, maxima and disclosure
instructions only. Leaves the registered policy note and steps 1-8 unchanged.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / ".claude/skills/d4d-select-replicate/SKILL.md"


def main():
    value = TARGET.read_text()
    replacements = [
        ("Every missing or refused cell is **not measured**, never zero. Inspect the census\nof every record in the series, including records of other projects.",
         "Every missing or refused cell is **not measured**, never zero. Compare the\nexpected roster with the discovered census before inspecting measurements. The\nexpected roster is the selected source manifest's projects times the union of\nreplicate labels discovered for this configuration. It is independent of which\nprojects have score evidence. Any membership difference forces fallback. For an\nintentional narrower series, repeat `--score-series-project NAME` once per expected\nproject on every preview; this explicit roster replaces the manifest's list and\nis recorded, together with excluded discovered projects. Do not omit a missing\nproject implicitly. Inspect every record in the declared series, including\nrecords of other projects."),
        ("be accounted for by exactly one accepted cell. Undeclared refusals or an\nadditional attempt force fallback. Never open the refused evaluation.",
         "be accounted for by exactly one accepted cell. Every matching run whose\nreceipt is not accepted counts in that accounting, including an unfinished run\nwith a saved plan and no receipt. Undeclared replacements or an additional\nattempt force fallback. Never open the refused evaluation. Retain refused plan\nand receipt hashes, plus a bounded path-free reason; disclose replacements from\nevery project contributing to pooled spread."),
        ("forces fallback rather than being ignored. Percentages use the fixed rubric\nmaxima, 50 and 88; adjusted and fixed maxima must agree, with one applicability\ncontext across the project's candidates and rubrics. Otherwise retain the",
         "forces fallback rather than being ignored. Percentages use each rubric's\n`max_points` from the accepted published files. Require one maximum per rubric\nacross every measured cell of the entire series, with `adjusted_max_points` equal\nto it, and one applicability context across the project's candidates and rubrics.\nNo instrument-specific maximum is assumed. Otherwise retain the"),
        ("A partial diagnostic spread never authorizes selection from an incomplete series.",
         "When the series is incomplete, registered `s` and `T` remain null with the\nreason. Separately named `partial_variation` diagnostics never authorize selection.\nThe canonical score-policy block stores the full series census once."),
        ("deciding rule or fallback reason. Retain per-cell points, maximum,",
         "deciding rule or fallback reason. The historical `margin_over_runner_up`\ncontinues to describe the policy pick's coverage margin. The separate\n`selected_coverage_margin_over_best_other` describes the selected score-policy\nrecord against the best other coverage contender, which can be negative. Retain\nper-cell points, maximum,"),
        ("without it. Authorization is checked before any write. Ordinary previews need",
         "without it. This text prevents an accidental mark and records the asserted\nauthorization; it is not proof of authorization or a signature tied to a pick.\nThe option guard is checked before any write. Ordinary previews need"),
    ]
    for before, after in replacements:
        if value.count(before) != 1:
            raise ValueError("skill anchor missing or repeated: " + before[:80])
        value = value.replace(before, after, 1)
    TARGET.write_text(value)
    if TARGET.read_text() != value:
        raise ValueError("saved skill differs")


if __name__ == "__main__":
    main()
