# Explicit historical-artifact evaluation (#5126)

Historical admission evaluates retained bytes under a newly selected evaluation
condition. It does not reconstruct a generation registration, certify provider
execution, approve a scientific instrument, or authorize scoring. Original
records, provenance and previous ratings remain unchanged.

The existing `shared_generation_v1` admission remains the default. Its refusals
never fall back to historical admission. Historical admission rejects provenance
containing `shared_generation`, requires the D70/D73 eligibility check and an
explicitly passed historical full-output validation. Unknown generation fields
remain unknown. Routed shared-v2 and native authority adapters are separate work.
Admission additionally requires positive `pre-D41` age evidence; unknown age and
post-D41 ancestry refuse even with valid runtime integrity. D73 classifies a new
rerun on recorded historical code lineage outside D41 ancestry as pre-D41, even
with a recent timestamp. Thus a future no-crate rerun on historical v8 code can
qualify with its actual immutable commit, passed validation and separately pinned
cohort; timestamps or missing controls alone cannot establish that lineage.

## Input binding

Preparation trusts the cohort and decision pins in the binding; only the binding
digest is supplied independently at preparation. Audit and campaign packing
enforce independent selection of the exact cohort and decision document.
The cohort selects run identities, not file paths or approval. The decision
reference is evidence to review, not an authenticated approval bit. A source
binding is strict JSON with exactly:

```json
{
  "format": "historical_artifact_binding_v1",
  "record_role": "full",
  "record": {"path": "/absolute/full.yaml", "sha256": "64 lowercase hex digits", "bytes": 123},
  "provenance": {"path": "/absolute/provenance.yaml", "sha256": "64 lowercase hex digits", "bytes": 456},
  "cohort": {"path": "/absolute/cohort.yaml", "sha256": "64 lowercase hex digits", "bytes": 789},
  "decision": {"path": "/absolute/decision.md", "sha256": "64 lowercase hex digits", "bytes": 234},
  "decision_reference": "Approved analysis decision and section",
  "condition_pointer": "/prompts/request/spec/condition"
}
```

Replace every illustrative pin with the independently verified exact file bytes.
Use canonical absolute paths without symlink aliases. Each provenance artifact
path and every MD5/SHA256 assertion present must match the selected full record.
Stale `outputs.full.bytes` claims are reported, not gated: the package's
`historical_identity.recorded_byte_claim_disagreements` records source, claimed
and actual byte counts, also exposed on the audit package. This differs from
the binding's own byte counts, which must always match exactly.
The explicit historical condition pointer must exist; a conflicting
`run.condition` refuses. The normalized identity is stored only in the new
evaluation binding, never written into historical provenance.

`configs/evaluation/d64_retained_v8_comparator.yaml` declares the nine retained
D64 candidates. It is not a final funded E5 cohort. The analysis plan excludes
historical with-crate AI_READI records; its conditional no-crate comparator and
missingness rules remain separate. Project membership is declared data, not a
special case in the admission code. Supply the exact scoped cohort and decision
pin selected for the future rating registration.
The pinned cohort's optional `exclusions` list matches literal identity fields;
any cell expanding to an excluded identity refuses. D64 declares all three
excluded historical AI_READI labels, leaving separately selected reruns possible.

## Preparation, output and ingestion

The evaluator CLI accepts explicit
`--authority-kind historical_provenance_v1 --registration BINDING.json
--registration-sha256 SHA256` together with the existing record, provenance,
context, rubric/version, runtime, budget and output options. `--dry-run` prepares
an offline plan without a runtime call. The Python API is
`registered_eval_runner.prepare_historical(...)`; shared preparation and the
historical adapter use one prompt, resource selection, no-tools adapter and
acceptance path. Generation identities and provenance stay out of the rating
prompt. Retained transcripts, receipts, failed attempts and plan locks use the
existing evaluator protocol.

The output `registration.json` has format
`registered_historical_semantic_evaluation_v1` and
`generation_authority_kind: historical_provenance_v1`. It binds the source
binding, normalized identity, original/provenance bytes, selected cohort and
decision, original and blinded hashes, context and evaluator resources/code.
`generation_registration` and `omission_context` remain null;
generation acceptance and scientific review remain false.

For ingestion, pass the package through `--registered-evaluation ARM=DIR`, the
independently selected `--roster-manifest`, and `--historical-decision FILE`.
The audit re-admits the saved binding, checks exact selected cohort and decision
pins, recomputes blinding and revalidates saved transcripts and receipt joins.
It never executes historical code or a runtime binary. Missing committed-package
or execution-lock evidence stays pending. Hash consistency is not proof of
execution or scientific comparability.

The evaluation-condition key excludes generation labels, arms and record hashes;
it retains instrument/context, blinding policy/emitter, common evaluator code,
runtime byte identity, adapter and per-rating budget. The repeat key additionally
binds the complete record, generation evidence and blinding instance. Different
records cannot inflate a fixed-record repeat panel. Independent sessions may
return identical score JSON.

The audit's `evaluation_condition_groups` exposes each condition's exact record
and rating members, their receipt/transcript identities and pending evidence.
It counts records separately from rating files and grants no comparability,
review or session-independence approval. Historical admission-code pins remain
required package evidence, separate from the common evaluator-condition key.
Every new plan and audited package, bound row and group member records
`generation_authority_kind`; group `generation_authority_kinds` counts label
shared-generation and historical-provenance ratings even when pooled.

Two shared-v10 audit behaviors changed with this route: `repeat_panel` now
includes `repeat_key`, so record/generation pins and per-attempt cost changes
split panels; all 15 common evaluator-module pins and the selected schema pin
are required. Missing or ambiguous condition pins produce
`registered_condition_identity_incomplete` with the offending resource name.
Older shared manifests may omit the kind (inferred strictly from their format),
but unknown or historical-only keys and contradictory kinds refuse. New shared
plans add the explicit kind; their model-facing preparation is unchanged.

## Campaign pack

Historical campaign packing is opt-in, using repeated
`--historical-binding SHA256=PATH` and `--historical-decision FILE`, plus the
existing record-selection and cohort manifests. It uses the same explicit
historical condition adapter. Missing/conflicting condition evidence is refused;
synthetic mode is not a substitute for campaign admission. Historical authority
pins appear in the separate private key, not the reviewer directory. Captured
binding, provenance, cohort and decision bytes are rechecked before publication.

## Remaining decisions

The owner still selects the exact scoped cohort and decision reference, rubric20
instrument under #2911/P4b, reviewed context and implementation pins, evaluator
runtime and budget. Semantic 5.0 support in the runner does not imply support by
the current comparability audit, which targets rubric10 3.0 and rubric20 3.0/4.0.
D52 deterministic changes do not automatically establish equivalent semantic
instrument changes. Support-judge calibration is separate. No rating run is
authorized by this implementation or its offline tests.

Known review follow-ups: canonical-path enforcement includes implementation
resources, so a symlinked checkout refuses and reports its offending path (F9).
The decision reference remains descriptive text; its occurrence in the pinned
decision document is not checked (F10). Neither limitation authenticates approval.
