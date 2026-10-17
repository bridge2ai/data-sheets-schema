# Captured top-level fitness results

`d4d evaluate fitness-results` selects the separate
`top_level_fitness_result_v1` contract. It reconstructs the captured plan's
schema closure, complete slot specifications, record value, model, system
prompt and exact request bytes. It does not turn a nested support target into
a fitness target or read legacy fitness caches. Existing legacy request,
salvage-parser and cache behavior remains unchanged.

Select a top-level fitness target and an explicit attempt identifier from an
existing nested-support plan:

```sh
d4d evaluate fitness-results prepare --plan plan-dir \
  --protocol top_level_fitness_result_v1 \
  --select FITNESS_TARGET_ID ATTEMPT_ID --output fitness-descriptor
```

The new result requires one complete native message from the exact requested
model with `stop_reason: end_turn`, explicit valid usage, and a single text
block containing exactly `fitness`, `failure`, and `reason`. Fitness must be a
finite number between 0 and 1; failure is `none`, `form`, `target`, or `substance`;
reason contains 1–24 whitespace-separated words. Thinking blocks may be retained.
Truncation, prose, code fences, duplicate keys and partial JSON are rejected;
rejected results preserve raw bytes without exposing an accepted score.

Caller-supplied saved messages use the fixed `package_response` envelope and
`accept`/`recheck` commands. Such bytes do not authenticate provider execution.
For registered execution, the fixed adapter in
[registered execution](nested-support-execution.md) accepts the fitness
descriptor with an explicit `top_level_fitness_execution_v1` declaration.
It preserves original request bytes separately from its
explicit nonstreaming wire transformation; no fitness-to-support conversion is
performed. Declared scientific/paid decision references do not grant approval.

## Portable index and execution states

```sh
d4d evaluate fitness-results index --descriptor fitness-descriptor \
  --execution /absolute/registered-run --output fitness-index
d4d evaluate fitness-results recheck-index --index fitness-index
```

Indexing never dispatches, retries or resumes calls. It copies the entire
referenced execution ledger and captured evidence, then independently checks
registration, requests, admissions, raw responses and settlements. Recheck
works after the index is relocated and original input/run paths are unavailable.
Any saved execution report must equal that reconstruction. An optional
`--result` must match its actual ledger-derived result when `--execution` is
supplied. Missing or foreign evidence and changed saved flags refuse.

The index separates `dispatch_state` from raw `assessment`:

| Dispatch state | Spent | Fitness row state |
| --- | --- | --- |
| `accepted` | true | `accepted`, only with strict accepted response |
| `failed` | true | `rejected`, even if the failed HTTP body contains valid score text |
| `spent_unknown` | true | `missing`; an admitted call has no captured HTTP outcome artifact |
| `not_started` | false | `missing`; no admitted call exists |

Here `spent` records admission, not verified billing. Without a ledger, dispatch
remains `unknown` and spent remains null, even for a mechanically accepted
caller-supplied result. A retained HTTP outcome and body can be rechecked after
a missing terminal settlement; a later admission without its preceding
settlement refuses. No replacement call is purchased.

HTTP/transport failure and incomplete accounting remain authoritative. Reported
usage and a strict score from a failed body are retained as evidence, never
promoted into an accepted execution row. Mode, decision references, original
readiness blockers and `scientific_scoring_eligible: false` stay explicit.
Local synthetic HTTP fixtures cannot become scientific observations through
caller labels or index fields.

Optional `--support-result` inputs are independently rechecked and joined only
on the same captured plan and exact record identity. Relationship-edge,
attribute-value and top-level fitness counts remain separate. Links identify
corresponding targets without propagating a top-level fitness score to nested
support targets. These engineering checks do not complete empirical calibration,
human control review, or the parent evaluation campaign in #2929.

## Registered support selections (index v2)

```sh
d4d evaluate fitness-results index --descriptor fitness-descriptor \
  --support-execution /absolute/captured-support-run --output support-fitness-index
d4d evaluate fitness-results recheck-index --index support-fitness-index
```

`--support-execution` captures and rechecks an existing
`nested_support_execution_v1` run and selects `top_level_fitness_index_v2`.
`--execution` separately supplies a top-level fitness run; either option can be
used without the other. With neither `--support-execution` nor
`--rubric-associations`, the existing v1 format remains unchanged.

Every registered support selection remains a row, including failed, admitted
but incomplete, and unstarted attempts. The denominator is all support selections
in that registration, not the entire planned cohort or only supplied result
directories. The support descriptor must bind the same captured plan as the
fitness descriptor, and every support selection's exact record must be among
the fitness descriptor's selected records. Foreign plans or records refuse.

Relationship-edge and attribute-value strata each retain selected, missing,
rejected and accepted counts. `support_dispatch_counts` separately retains
`accepted`, `failed`, `spent_unknown` and `not_started`. As with fitness above,
a valid verdict inside a failed HTTP body remains rejected. An admitted call
with no captured HTTP outcome artifact is missing with `spent: true`. A retained
timeout, interrupted partial-body or overflow outcome is failed/rejected, even
when `body_complete` is false. An unstarted call is missing with `spent: false`.
Raw assessments do not override dispatch.
Optional `--support-result` inputs must exactly match their ledger-derived
results and cannot add attempts outside the registration.

Recheck uses the portable index's captured artifacts after relocation. Support
mode, decision references and original readiness remain explicit and separate
from fitness metadata. The index does not dispatch, retry, approve labels or
propagate fitness scores. Combining `--rubric-associations` selects index v3
while retaining this support execution accounting.

## Captured rubric identity declarations (index v3)

```sh
d4d evaluate fitness-results index --descriptor fitness-descriptor \
  --rubric-associations --rubric-plan captured-plan-dir --output associated-index
d4d evaluate fitness-results recheck-index --index associated-index
```

`--rubric-associations` explicitly selects `top_level_fitness_index_v3`.
Without this option the original v1/v2 behavior and format remain unchanged.
`--rubric-plan` supplies an already captured plan whose exact manifest bytes
must match the descriptor's plan pin. Normal fitness descriptors omit rubric
result blobs; this separate input supplies those blobs through captured hashes.
The option may be omitted when all referenced blobs are already captured with
the descriptor, or when every selected job declares an absent result. Indexing
never follows the roster's historical result paths. Recheck uses only the
portable index and its captured artifacts.

One rubric row is retained for every primary roster job belonging to a record
selected by the fitness descriptor. The denominator is these declared jobs,
including distinct primary job IDs for the same record/rubric; it is not the
entire planned cohort or an inferred set of repeated ratings. At most 10,000
roster jobs are supported. Duplicate job IDs or changed join membership refuse.

| State | Meaning |
| --- | --- |
| `associated` | Captured identity declarations agree. |
| `missing` | The captured plan explicitly declares no result artifact. |
| `mismatched` | A declared record, job, instrument, context or scope identity conflicts. |
| `unsupported` | Historical identity fields are absent, the semantic contract is unsupported, or captured result bytes are not a strict bounded JSON mapping. |

A declared artifact with missing or changed captured bytes refuses rather than
becoming `missing`. Known conflicts remain `mismatched` even when other fields
are absent. Every state remains in `rubric_counts.selected`.

If the roster also declares `pinned_files[job.output]`, the captured result
bytes must agree with that SHA-256 declaration. A valid conflicting hash makes
the row `mismatched`; a malformed declared hash makes it `unsupported` unless
another known conflict already makes it `mismatched`. Both diagnostics remain
visible. An absent result remains `missing`, with its original declaration
retained and no inferred byte conflict. Each row exposes `roster_output_pin`
and distinguishes `captured_plan_only` from
`captured_plan_with_roster_output_declaration` in `result_pin_basis`. Neither
basis authenticates evaluator execution.

The check supports explicitly declared semantic v3 and rubric20 v4 identities.
It reconciles input hashes and label aliases, declared instrument resource pins,
the v4 predecessor declaration, explicit applicability context and its digest,
and every dataset scope unit. Missing historical context is not silently
converted to an empty context; false and missing remain distinct.

`associated` means agreement of captured declarations only. Instrument hashes
are roster declarations, not proof of canonical released bytes. This index does
not validate rubric schemas, scores, arithmetic, scientific labels, evaluator
execution or calibration. `rubric_rating_acceptance`, per-row `rating_accepted`
and `scientific_scoring_eligible` remain false. Existing readiness blockers and
all fitness/support axis counts are preserved; no score is propagated between
targets, records or repeated ratings.
