# D4D Rubric20 API Judge — general context v2

Assess all 20 questions for documentation quality and usefulness.
Numeric questions retain this API instrument's continuous 0–5 scale:
0 absent; 1 poor; 2 minimal; 3 adequate; 4 good with minor gaps;
5 comprehensive and actionable. Fractional numeric scores are permitted
when justified. Pass/fail questions use only 0 or 1.
This is distinct from the semantic agent's discrete numeric score bands.

**Maximum Possible Score:** 88 points — 17 numeric questions at five points
and three pass/fail questions at one point. Adjust the maximum only through
the supplied applicability contract.

Examples must fit the dataset. Clinical recruitment may need eligibility,
collection settings and relevant governance; a molecular benchmark may need
sample preparation, assay and processing details. Named study membership,
institutional affiliation or a particular hosting platform earns no credit.

## Applicability and collection scope

Use the caller's supplied evaluation contract. Its context predicates describe
the dataset independently of the fields being scored. A false predicate makes
only its assigned items N/A. Unknown predicates stay applicable and scored;
record that uncertainty instead of inferring N/A from missing documentation.
Human-subject governance can use the appropriate jurisdiction's equivalent
framework; no institution, project name, hosting service or jurisdiction is
required universally.

For every item, include `applicable`, `max_score`, and `unit_scores`.
Each unit row must contain the exact required resource `path`, its `score`,
and nonempty `evidence` (including an explicit explanation when evidence is
missing). Assess every terminal resource, including nested collections.
Traverse distribution/file collections for evidence about their own dataset.
Do not give one sibling credit for another sibling's documentation, and do
not implicitly inherit collection metadata. For an applicable item, its
score is the minimum of its resource scores. This conservative coverage
policy is named in the supplied contract.

For an N/A item, set `score: null`, `max_score: 0`, `applicable: false`,
and a nonempty `na_reason` tied to the declared context. Each unit score is
also null. Keep all items in the response. Applicable items have
`applicable: true` and their ordinary maximum. Never replace absent evidence
with N/A.

All group totals sum applicable item scores and maxima. Overall
`total_points` and `max_points` sum the groups. `percentage` is
100 * total_points / max_points, rounded to one decimal, or null if the
applicable maximum is zero. The runner separately records the fixed maximum,
excluded items, context and scope. Adjusted percentages with different
applicable-item sets must not be pooled or used as a common ranking.

## Rubric specification

{RUBRIC_SPECIFICATION}

## Common output fields

Return only a JSON object with `rubric`, `version: "2.0-general-context"`,
`project` and `method` exactly as supplied, `d4d_file`,
`evaluation_timestamp`, `overall_score` (total_points, max_points,
percentage), `assessment` (strengths, weaknesses, recommendations), and
`metadata`. Provide actionable, evidence-based explanations. The runner
attests the actual model, rubric bytes and rendered request; do not invent
digests. Preserve arbitrary dataset/method identities literally as data.

## Rubric20 output structure

Include `categories` with four nonempty groups covering Q1–5, Q6–10,
Q11–15 and Q16–20 respectively. Each group contains `name`, `questions`,
`category_score` and `category_max`, computed from that group's questions.
Each question has integer `id`, its rubric `name`, `score_type`,
`score`, `max_score`, `applicable`, `score_label`, `evidence`,
`quality_note`, and `unit_scores` as defined above; N/A also needs
`na_reason`. Include all 20 questions exactly once.
