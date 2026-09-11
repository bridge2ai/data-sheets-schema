# Review metrics and canonical selection — 2026-09-11

The current review metric is report-only. No adverse-count difference is
sufficient to gate a run, exclude a candidate or break a canonical tie under
this policy. `d4d runs select` uses validity, coverage and a deterministic
label tie-break; it records every available review count and the reason the
review cannot influence the result. It rejects an explicit `--review-margin`
instead of accepting an uncalibrated threshold. This does not claim that
coverage is a semantic quality ranking.

The evidence required by #835 was partly collected in [#860](https://github.com/bridge2ai/data-sheets-schema/pull/860):
six records from AI_READI, CHORUS and VOICE, stratified by adverse rate and
spanning both arms, independently rated against the same committed packs.
The [reliability note](review_reliability_2026-09-01.md) records 402 paired
items, 89.1% class agreement and pooled kappa 0.534, below the preregistered
0.6 threshold for joining selection. Its bootstrap interval is [0.41, 0.65]
with the clustering limitation stated; rater adverse totals were 68 and 40.
CM4AI was not part of that calibration. These results do not establish an
adverse-rate threshold that generalizes to all four projects.

[#865](https://github.com/bridge2ai/data-sheets-schema/pull/865) completed the
[44-disagreement adjudication](adjudication_rulings_2026-09-01.md): the first
rater was upheld 24 times, the second 19, and neither once. This provided
useful instruction repairs, but adjudication of disagreements is not an
independent repeatability measurement of the repaired instrument. It cannot
be treated as evidence that the failed reliability criterion now passes.

Enabling review-based selection again requires a separate, preregistered
calibration of the exact reviewer definition and pack revision on all four
projects, with independent blind ratings, model/definition/pack identities,
raw agreement and confusion matrices, and an uncertainty-aware decision rule
validated on those ratings. Passing a schema or review completeness check,
a large observed difference, a manually chosen margin, and an adjudication
result are all insufficient on their own. Until that evidence exists, the
permitted decision is report-only at every observed adverse difference.

The new canonical provenance field `review_policy` names this policy as
`reported_only_pending_calibration_v1 (#835)`. Existing canonical decisions,
review outputs and adjudications remain unchanged; this change governs future
selections and makes their measurement basis explicit.
