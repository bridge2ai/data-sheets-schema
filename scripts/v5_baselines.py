"""Recompute the v4 baselines the v5 plan is measured against (#577).

Committed rather than run ad hoc, because three of the seven figures in the
first version were wrong or undefined: minted fragments omitted two records
outright, and the undeclared-prefix and British-spelling counts each had a
defensible counting rule that was never written down, so the v5 figure could be
compared against a differently-defined v4 one.

Every rule this applies is stated in the output, so the number and its
definition travel together.

    poetry run python scripts/v5_baselines.py [--label-prefix ...]
"""

from __future__ import annotations

import argparse
import collections
import re
from pathlib import Path

import yaml

DEFAULT_PREFIX = "2026-08-13_claude-opus-5-api-generic-v4"
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
BASE = Path("data/d4d_concatenated")

#: Counted only in generated prose. The rule exempts quoted material, so a
#: title or a direct quotation keeping its source's spelling is not a defect.
#:
#: The counting itself is `grounding.british_spellings` — the gate's own
#: instrument — not a local copy (#670 review): this script's whole purpose
#: is that the number and its definition travel together, and its first
#: version carried a private v1 implementation that survived the #653
#: instrument change, printing numbers incomparable with everything the gate
#: reads. The per-form breakdown below uses the same patterns. The figures in
#: `notes/generic_v5_analysis_plan.md` were produced by the superseded local
#: implementation and stand as historical statements of that instrument.
from data_sheets_schema.grounding import BRITISH_PATTERNS

#: A quoted span: anything inside double quotes on one line. Crude, and stated
#: as such — it is the difference between 618 and 626, not between 618 and 0.
QUOTED = re.compile(r'"[^"\n]*"')


def records(prefix: str):
    for rep in (1, 2, 3):
        label = f"{prefix}_rep{rep}"
        for project in PROJECTS:
            core = BASE / "claudecode_agent_core" / label / f"{project}_d4d_core.yaml"
            full = BASE / "claudecode_agent" / label / f"{project}_d4d.yaml"
            if core.exists():
                yield project, rep, full, core


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label-prefix", default=DEFAULT_PREFIX)
    args = ap.parse_args()

    from data_sheets_schema.grounding import (ground, iter_external,
                                              person_fragment_on_org)
    from data_sheets_schema.identifiers import (declared_prefixes,
                                                uriorcurie_slots,
                                                walk_identifiers)
    slots = uriorcurie_slots()
    declared = {p.lower() for p in declared_prefixes()}

    per: dict[tuple[str, int], dict] = {}
    undeclared = collections.Counter()
    urls = collections.Counter()
    british = collections.Counter()
    seen_any = False

    for project, rep, full, core in records(args.label_prefix):
        seen_any = True
        bundle = Path(f"data/preprocessed/concatenated/{project}_preprocessed.txt")
        text = bundle.read_text(encoding="utf-8", errors="replace").lower() \
            if bundle.exists() else ""
        status: dict[tuple[str, str], str] = {}
        frags = set()
        for path in (full, core):
            if not path.exists():
                continue
            raw = path.read_text(encoding="utf-8")
            doc = yaml.safe_load(raw) or {}
            for _p, auth, bare in iter_external(doc, slots):
                status[(auth, bare)] = ground(f"{auth}:{bare}", text)[2]
            for _p, _s, value in walk_identifiers(doc, slots):
                value = str(value)
                m = re.match(r"^([A-Za-z][\w.\-]*):(?!//)", value)
                if m and m.group(1).lower() not in declared:
                    undeclared[m.group(1)] += 1
                if re.match(r"^https?://", value):
                    urls[project] += 1
                if person_fragment_on_org(value):
                    frags.add(value.lower())
            prose = QUOTED.sub(" ", raw).lower()
            for pattern in BRITISH_PATTERNS:
                british[pattern.pattern] += len(pattern.findall(prose))

        counts = collections.Counter(status.values())
        per[(project, rep)] = {"grounded": counts["grounded"],
                               "minted": counts["minted_fragment"],
                               "absent": counts["absent"],
                               "org_fragments": len(frags)}

    if not seen_any:
        print(f"no records found under {args.label_prefix}")
        return 1

    print(f"v4 baselines — {args.label_prefix}\n")
    print("Counting rules, stated so the v5 figure is produced the same way:")
    print("  · identifiers are counted DISTINCT per record pair, not per")
    print("    occurrence: every identifier appears in both records, so an")
    print("    occurrence count is exactly double (#556).")
    print("  · a prefix is 'undeclared' when the schema's prefixes block does")
    print("    not declare it. `urn:` and `ark:` are counted here; classifying")
    print("    them instead as no-authority URI schemes gives a lower figure,")
    print("    and both are defensible — this is the one applied.")
    print("  · British spellings are counted in generated prose only: spans")
    print("    inside double quotes are removed first, because the rule exempts")
    print("    quoted material.\n")

    print(f"{'project':9} {'rep':4} {'grounded':>8} {'minted':>7} {'absent':>7} {'org-frag':>9}")
    for (project, rep), c in sorted(per.items()):
        print(f"{project:9} rep{rep} {c['grounded']:8} {c['minted']:7} "
              f"{c['absent']:7} {c['org_fragments']:9}")

    print(f"\nundeclared CURIE prefixes (occurrences): {sum(undeclared.values())}")
    for name, n in undeclared.most_common():
        print(f"   {name:22} {n}")
    print(f"\nURL-valued identifier slots: {sum(urls.values())}")
    for name, n in urls.most_common():
        print(f"   {name:22} {n}")
    print(f"\nBritish spellings in generated prose: {sum(british.values())}")
    for name, n in british.most_common(8):
        if n:
            print(f"   {name:22} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
