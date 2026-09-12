**Comparison publication refresh — 2026-09-11 Pacific (#1281)**

Regenerating `scripts/arm_comparison.py` at main
`e42db7229c32e2fea57a23e884277f78115d8195` changes the four report-finding
rows and the corresponding report figure. All other generated figures
reproduce byte-for-byte on the local environment. Receipt rows and other
deterministic metric rows are unchanged.

| Project | Current v8 production findings by replicate | Mean ± sample SD |
|---|---|---|
| AI_READI | 0, 0, 1 | 0.3 ± 0.6 |
| CHORUS | 0, 2, 0 | 0.7 ± 1.2 |
| CM4AI | 0, 0, 0 | 0.0 ± 0.0 |
| VOICE | 0, 1, 0 | 0.3 ± 0.6 |

These are stored report_claims v7 findings. Three are
`removal_not_recorded` (AI_READI rep3 content warnings, CHORUS rep2
regulatory restrictions, VOICE rep2 data governance); one is
`retention_not_shown` (CHORUS rep2). The refresh reports the checker's
measurements and does not adjudicate their semantic correctness.

Earlier cohorts also changed in which zero cells were measured. The
renderer retains every unmeasured zero as `0ᵘ` and excludes it from means
and sample counts. A positive finding remains measured even when the
separate claim counter is zero. The figure uses the same measured values,
sample counts and hollow markers for unmeasured observations.

The generated footer now states that comparison requires matching
evaluator, definition and applicability basis. The scores in this table
remain historical; they are not results from the newly registered reference
instrument. No small difference authorizes selecting a run.

A gitignore-independent search of the repository's README, docs, notes and
scripts found the plan's production table and the dated #998 section as
places that needed explicit current-measurement qualifications. Their
original observations are retained with dated annotations. Earlier v4–v7
results notes remain historical and are not silently rewritten.

`scripts/arm_comparison.py --check` now compares the committed Markdown
with a fresh rendering without writing any outputs. A corpus test performs
the same comparison in the full CI lane; unit tests verify that a changed
report count fails the check without overwriting the old table, and preserve
the measured/unmeasured distinction. The freshness test failed on the old
committed table before regeneration. PNG byte equality is not a cross-platform
test; the images were regenerated and the changed report figure inspected.

No generated records, evaluation outputs, scoring definitions, or reference
manifest inputs were changed. This is a derived publication update and
requires no downloads or model calls.
