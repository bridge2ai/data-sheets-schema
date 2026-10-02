# Opt-in semantic 4.0: dataset lineage independent of representation

This AI-authored instrument draft implements [#4258](https://github.com/bridge2ai/data-sheets-schema/issues/4258), the offline engineering slice of
[#2911](https://github.com/bridge2ai/data-sheets-schema/issues/2911). Scientific
review and empirical calibration remain pending. Synthetic contract tests do
not establish that an evaluator assigns the intended scores. No paid scoring,
new cohort registration, or human applicability approval is included.

Semantic rubric20 version 4.0 changes Q19 to **Data Integrity, Provenance, and
Quality**. It preserves all other nineteen items, their weights, the fixed
maximum of 88, and the existing applicability and per-resource aggregation
rules. Q19 always applies, even when data processing is false or unknown.
Missing lineage receives a score rather than becoming an exclusion.

The new anchors distinguish no usable provenance (0), meaningful partial
lineage or version/errata history (3), and identifiable, mutually consistent
source-to-result lineage at the declared dataset/release scope (5). Partial
lineage without a change log earns 3. A complete account of original acquisition
and release can earn 5 without inventing an intervening processing step.
Equivalent relationships in prose, tables, D4D fields, and PROV receive the
same score. Formal identifiers, a serialized graph, and populated designated
provenance slots are not independent prerequisites.

Missing-data details, split indicators, checksums, and similar information
support lineage when they identify an input/output or explain an activity.
Their presence alone does not establish complete lineage; their absence alone
does not cap it. Complete lineage does not additionally require version history
or errata. The D4D document's own generation history and a bibliography of
sources used to write it are not automatically dataset lineage.

## Trusted selection and preserved history

`select_semantic_instrument(rubric_name, version)` in
`src/data_sheets_schema/semantic_instrument.py` returns immutable, repository-relative
paths for each supported instrument. It accepts rubric10/rubric20 and their
`-semantic` aliases; 2.0 and 3.0 resolve to the released assets, and 4.0 exists
only for rubric20. Exact new-output acceptance defaults to 3.0. Selecting an
instrument is a caller decision, never permission inferred solely from model
output.

The v4 assets are:

- `data/rubric/rubric20_semantic_v4.txt`
- `.claude/agents/d4d-rubric20-semantic-v4.md`
- `src/download/prompts/rubric20_semantic_v4_schema.json`

The old rubric, definitions, output schemas, authority, scores, and registered
instruments retain their bytes. No old scores are reinterpreted as v4.
Version 4 explicitly reuses `semantic_evidence_authority_v3.json`, including
its frozen hash and its name-only limitation. Current schema evolution does
not expand that authority. Evidence paths, quotes, counts, deductions, scope,
context, and input identity receive the same mechanical checks as v3. These
checks do not decide whether cited prose supports a semantic score, and they
do not prove every class/range relationship in a path.

The source rubric retains `instrument_version: 2.0-general-context` as inherited
applicability metadata. This is distinct from the selected semantic instrument
version, `4.0`; selection and acceptance use that explicit version together with
the rubric and definition hashes.

For exact acceptance, supply the original record, the selected definition,
and any independently supplied applicability context:

```bash
python scripts/validate_evaluation_schema.py \
  --file NEW_OUTPUT.json --rubric rubric20-semantic --semantic-version 4.0 \
  --input ORIGINAL_RECORD.yaml \
  --agent-definition .claude/agents/d4d-rubric20-semantic-v4.md \
  --context REVIEWED_CONTEXT.yaml
```

Omit `--context` when no independent context exists; predicates then remain
unknown and conditional items stay in the denominator. Do not manufacture a
context to exclude missing documentation. Exact acceptance requires version
4.0, the v4 rubric hash, the selected v4 definition's bytes, and the unchanged
authority hash. A self-consistent hash of the old definition is insufficient.
Historical discovery selects the versioned schema for declared v4 outputs;
that structural classification does not replace exact input-checked acceptance.

The new agent filename has no same-path predecessor. Its preimage registry
entry records that fact with null predecessor fields. The offline reference controller requires a v4 instrument registration to name
`predecessor_definition: .claude/agents/d4d-rubric20-semantic.md` and
`predecessor_sha256: 35de3a37264e80f48e6e037fed42b6cc586152058d4da6c08bad93b8096f588b`,
with that same file/hash in `pinned_files`. It uses those actual released bytes
for the explicit predecessor challenge; copying a preamble or using a stale v3
echo is not proof. The job agent, selected assets, definition hash and complete
validator support must also be pinned. Its evaluator and controller validations
both select `--semantic-version 4.0`; a v3 command cannot attest a v4 rating. The existing default v3 roster and requests
remain unchanged. Registration and any scoring launch await the independent
context/scientific decisions tracked by #2912 and #2911.

## Normative examples for scientific review

These are authored examples of the intended anchors, **not empirical evaluator
results, gold labels, or a completed calibration set**. Each row concerns one
scored dataset resource; evidence must actually occur in that resource.

| Documented content at the declared scope | Intended Q19 | Reason |
| --- | ---: | --- |
| A dataset identifier and a bare claim that provenance is complete | 0 | No usable origin, derivation, or version information. |
| A bibliography for the D4D author, with no dataset-origin relationships | 0 | Document research history does not establish dataset lineage. |
| Checksums and split indicators, with no usable lineage | 0 | Ancillary quality metadata alone is insufficient. |
| Version numbers, dated changes, and errata without source-to-result relationships | 3 | Meaningful history supports the middle band. |
| Original acquisition source and responsible team, but an unexplained route to the released outputs | 3 | Partial lineage earns 3 even with no change log. |
| One documented modality but an unexplained material modality in the same release | 3 | A material derivation branch remains incomplete. |
| Meaningful lineage statements that disagree about a material source-to-result relationship | 3 | The relationships are not mutually consistent. |
| Source, output, acquisition/processing activities, responsible roles, and their relationships in prose | 5 | Complete relationships need no graph serialization. |
| The same relationships in a table | 5 | Changing representation does not change the score. |
| The same relationships distributed across D4D fields, with explicit connecting statements | 5 | Combining explicit relationships is permitted. |
| The same relationships represented in PROV | 5 | PROV receives the same credit for the same content. |
| Complete prose lineage with empty was_derived_from, parent_datasets, and errata | 5 | Empty designated slots do not negate evidence elsewhere. |
| Complete lineage without checksums, split indicators, or errata/history | 5 | These are not additional prerequisites. |
| A first release describing original measurements, acquisition responsibility, and release lineage, explicitly without further processing | 5 | Original acquisition is a complete lineage at that scope. |
| Names of sources, tools, and people with no relationships between them | 0 | A bag of names is not usable lineage; separately documented history would support 3. |
| Complete lineage only on a parent collection, while the scored child has only an identifier | 0 | Parent metadata is not implicitly inherited. |
| Complete lineage only on a sibling resource, while this child has only an identifier | 0 | Sibling evidence does not fill this resource's gap. |

For a below-5 assessment, name the unresolved source, output, activity,
responsibility, or relationship. Do not substitute the absence of one
representation for a missing relationship. Material contradictions or an
unexplained branch can justify a deduction; merely scattered documentation
cannot. Unit tests cover contract boundaries and asset parity, while these
semantic judgments still need independent review and calibrated evaluator runs.
