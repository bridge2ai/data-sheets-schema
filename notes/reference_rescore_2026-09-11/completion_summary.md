# Pinned v7/v8 reference rescore completion

<!-- Q19 semantic qualification:start -->
**Semantic qualification — Q19:** 15 rubric20 rationales contain representation-related objections requiring adjudication under the frozen text-or-graph rule. Their Q19 values, recorded totals and summaries containing them are unadjudicated model measurements. Mechanical acceptance does not certify semantic adherence. No scores were corrected or rerated. See the [Q19 erratum](semantic_errata.md), including the full 24-rating inspection and its limits. Rubric10 repeatability is unaffected by this Q19 erratum.
<!-- Q19 semantic qualification:end -->

Recorded 2026-09-12T16:16:08.141918+00:00 for #1248, #1080, #1062, #1327, #1335 and #1336.

All 24 existing production D4Ds (v7 and v8, three generation replicates per project) now have both semantic rubric ratings: 48 primary ratings. Eight additional rubric10 ratings complete three independent ratings of v7 rep1 per project, for 56 accepted ratings. Each rating used its supplied D4D and pinned rubric resources in a fresh isolated session. No D4D generation or source download was performed.

The [completion audit](completion_audit.json) verifies 64 original evaluator CLI sessions, 8 preserved and excluded attempts, complete terminal usage evidence, a maximum concurrency of 4, and all 202 prior evaluations unchanged. CLI-reported usage totals $142.25036250, including excluded attempts and any auxiliary CLI-model usage. A session can contain multiple model/tool turns; this is not an API-request count or an independently reconciled bill. Codex review usage is outside this figure.

The final registered runner commit is `d8bb022ed2934d606a5ef15847bd5a1e3fc2b72c` and the manifest SHA256 is `36e5b2233a37a1fbe68614caf13c7621c03d6a606e2287d893c572df17bbab4a`. [Registration history](manifest.json) links the dated runner/reporting amendments. Complete scoring prompts, input bytes, rubrics, schemas and evaluator definitions stayed fixed through those amendments; existing accepted outputs were revalidated without rerating or editing their scores. Every accepted output passed the check-echo, runtime identity, exact-file schema validation, arithmetic and final-attestation checks.

The [input audit](input_yaml_key_audit.json) confirms that all 24 frozen YAML inputs parse without duplicate mapping keys. The [write audit](final_written_output_audit.json) checks every accepted output byte-for-byte against its original successful evaluator Write.

The quoted evaluator definition SHA256 values are:

- rubric10-semantic: `66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`
- rubric20-semantic: `9d08b5f3d7a3e9828a6c6cbd59a0eacf302979399067ff5aa70480d95a0e7dd3`

The evaluator selector was `claude-opus-5[1m]`, effort `high`, temperature unspecified, with a $5 cap per attempt. The separately accepted CHORUS v7 rep1 rubric10 canary preceded the fill. Failed attempts and retry decisions remain in the dated plan and attempt directories.

## Repeated-rating observations

These are descriptive results for one v7 record per project under this exact rubric10 instrument. They do not estimate population uncertainty, and rubric20 repeatability remains unmeasured. Generation-replicate spread is reported separately in [results.md](results.md); the primary-rating arrays do not include the extra repeatability ratings. Small score differences do not establish a preferred run.

| Project | Fixed percentages | N/A-adjusted percentages | Fixed sample SD | Adjusted sample SD | Fixed range | Adjusted range | Same applicability |
|---|---|---|---|---|---|---|---|
| AI_READI | 98.000, 98.000, 98.000 | 98.000, 98.000, 98.000 | 0.000 | 0.000 | 0.000 | 0.000 | True |
| CHORUS | 70.000, 72.000, 72.000 | 70.000, 72.000, 72.000 | 1.155 | 1.155 | 2.000 | 2.000 | True |
| CM4AI | 86.000, 86.000, 86.000 | 91.489, 91.489, 91.489 | 0.000 | 0.000 | 0.000 | 0.000 | True |
| VOICE | 98.000, 98.000, 98.000 | 98.000, 98.000, 98.000 | 0.000 | 0.000 | 0.000 | 0.000 | True |

Table percentages, sample SDs and ranges are displayed to three decimal places; SDs and ranges are in percentage points. Calculations use the unrounded point ratios, and the JSON report retains their precision. The fixed maximum is 50 for rubric10 and 88 for rubric20. N/A-adjusted percentages use each rating's applicable maximum. The individual results retain excluded item identities; equal totals or maxima alone do not establish equivalent applicability. Neither score basis establishes rater reliability by itself.

## Fractional historical ratings (#1062)

The historical files remain unchanged. Their replacements are independent ratings under the current pinned integer-band instrument, not rounded versions of the old ratings. Every numeric rubric20 question score in the new 24-record set is integral.

| Record | Historical total | Historical fractional questions | Fresh reference total | Fresh evaluation |
|---|---|---|---|---|
| AI_READI v7 rep2 [Q19 erratum](semantic_errata.md) | 84.5/88 | Q7=4.5, Q19=4.5, Q20=4.5 | 84/88 fixed; 84/88 adjusted | [AI_READI_v7_rep2_r20_rating1](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-11/AI_READI_v7_rep2_r20_rating1_evaluation.json) |
| VOICE v7 rep3 [Q19 erratum](semantic_errata.md) | 83.5/88 | Q20=4.5 | 82/88 fixed; 82/88 adjusted | [VOICE_v7_rep3_r20_rating1](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-11/VOICE_v7_rep3_r20_rating1_evaluation.json) |

This completion covers the registered manuscript reference evaluation. It does not certify a new generation release, resolve the separate general-user packaging and vocabulary issues, or change historical prediction verdicts on the basis of small score gaps.
