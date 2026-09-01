#!/usr/bin/env python
"""Recompute the pooled test-retest statistics and bootstrap CI of
notes/review_reliability_2026-09-01.md from the committed packs and reviews.

Deterministic: percentile bootstrap over pooled paired items,
random.Random(SEED), DRAWS resamples. The pooled item bootstrap ignores
record clustering; with six records a cluster CI is unstable (the note says
so), and the by-record mean kappa is printed for comparison.
"""
import hashlib
import random
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from data_sheets_schema.review_pack import agree  # noqa: E402

SEED, DRAWS = 0, 2000
CORE = Path("data/d4d_concatenated/claudecode_agent_core")
RECORDS = [("CHORUS", "2026-08-28_claude-opus-5-claudecode-generic-v6_rep1"),
           ("CHORUS", "2026-08-28_claude-opus-5-claudecode-generic-v6_rep2"),
           ("AI_READI", "2026-08-28_claude-opus-5-claudecode-generic-v6_rep2"),
           ("AI_READI", "2026-08-28_claude-opus-5-claudecode-generic-v6_rep3"),
           ("VOICE", "2026-08-28_claude-opus-5-claudecode-generic-v6_rep2"),
           ("CHORUS", "2026-08-28_claude-opus-5-api-generic-v7_rep1")]
CLASSES = ("affirmative", "adverse", "cannot_tell")


def main() -> int:
    conf = {a: {b: 0 for b in CLASSES} for a in CLASSES}
    kappas = []
    for proj, label in RECORDS:
        d = CORE / label
        pack = yaml.safe_load((d / f"{proj}_review_pack.yaml").read_text()) or {}
        pack["_sha256"] = hashlib.sha256((d / f"{proj}_review_pack.yaml").read_bytes()).hexdigest()
        a = yaml.safe_load((d / f"{proj}_review.yaml").read_text()) or {}
        b = yaml.safe_load((d / f"{proj}_review_b.yaml").read_text()) or {}
        r = agree(pack, a, b)
        kappas.append(r["kappa_class"])
        print(f"{proj:9s} {label[:40]:40s} n={r['paired_items']} agree={r['percent_class_agreement']}% "
              f"kappa={r['kappa_class']} adverse {r['adverse_a']} vs {r['adverse_b']}")
        for x in CLASSES:
            for y in CLASSES:
                conf[x][y] += r["confusion"][x][y]
    n = sum(conf[x][y] for x in CLASSES for y in CLASSES)
    po = sum(conf[c][c] for c in CLASSES) / n
    pe = sum((sum(conf[c].values()) / n) * (sum(conf[r][c] for r in CLASSES) / n) for c in CLASSES)
    k = (po - pe) / (1 - pe)
    print(f"POOLED n={n} class agreement {100*po:.1f}% kappa {k:.3f} | mean per-record kappa {sum(kappas)/len(kappas):.3f}")
    pairs = [(x, y) for x in CLASSES for y in CLASSES for _ in range(conf[x][y])]
    rng = random.Random(SEED)
    ks = []
    for _ in range(DRAWS):
        c = {x: {y: 0 for y in CLASSES} for x in CLASSES}
        for _ in range(n):
            x, y = pairs[rng.randrange(n)]
            c[x][y] += 1
        po2 = sum(c[x][x] for x in CLASSES) / n
        pe2 = sum((sum(c[x].values()) / n) * (sum(c[r][x] for r in CLASSES) / n) for x in CLASSES)
        if pe2 < 1:
            ks.append((po2 - pe2) / (1 - pe2))
    ks.sort()
    print(f"bootstrap 95% CI (percentile, seed {SEED}, {DRAWS} draws) "
          f"[{ks[int(.025*len(ks))]:.3f}, {ks[int(.975*len(ks))]:.3f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
