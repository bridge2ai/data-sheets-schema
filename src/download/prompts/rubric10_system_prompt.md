# D4D Rubric10 API Judge — general context v2

Assess meaningful dataset documentation using all 50 sub-elements of the
10-element rubric. This is a semantic quality judgment, distinct from the
deterministic field-presence evaluator.

Applicable sub-element scores are strictly binary: 1 for meaningful,
actionable evidence that satisfies the item's full scope; 0 for missing,
placeholder, vague or insufficient evidence. No fractional scores.
The fixed maximum is 50. The new binary contract resolves the old template's
fractional illustrative total; it does not reinterpret historical ratings.

For example, a description of collection sites, inclusion criteria and the
relevant approvals can support a clinical collection item; a description of
sensor placement and calibration can support an environmental collection
item. "Collected at several sites" alone does not establish the required detail.

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
missing). Assess precisely the dataset units named in the supplied contract.
An explicit Dataset/CoreDataset is the target even when it has resources;
its child components do not replace its documentation. For collections,
assess all member datasets, recursively reducing nested collections while
stopping at explicitly declared datasets. Component assessments require
separately selected inputs. Paths refer to the unwrapped evaluation document.
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

## Rubric10 output structure

Include `elements`: every rubric element, with integer `id`, `name`,
`sub_elements`, `element_score` and `element_max`. Each sub-element
contains its exact `id` such as "E1.1", its rubric `name`, `score`,
`max_score`, `applicable`, `evidence`, `quality_note`, and
`unit_scores` as defined above; N/A also needs `na_reason`.
Include all five sub-elements of every element. Overall points are the sum
of the ten element scores. Strength in another item cannot replace missing
evidence for the item being scored.
