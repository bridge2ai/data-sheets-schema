#!/usr/bin/env python3
"""Purpose: check by simulation the upper 5% point of Hartley's maximum variance ratio
for 5 groups with 6 degrees of freedom each, and the upper-tail probability of the
observed ratio 7.092, as corrected by tab 197's review of the variation note
(notes/root_scope_v6_scoring_variation_2026-11-26.md, PR 6372). Normal, independent
observations assumed. Inputs: none. Outputs: two numbers on stdout.
Date: 2026-11-26 (UTC). Lead: Claude lead."""
import numpy as np
rng = np.random.default_rng(20261126)
v = rng.chisquare(6, size=(4_000_000, 5)) / 6
ratio = v.max(axis=1) / v.min(axis=1)
print("upper 5% point", round(float(np.quantile(ratio, 0.95)), 3), "P(ratio >= 7.092)", round(float((ratio >= 7.09204219).mean()), 4))
