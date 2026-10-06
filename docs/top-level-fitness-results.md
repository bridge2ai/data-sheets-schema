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
| `spent_unknown` | true | `missing`; an admitted call has no complete retained response |
| `not_started` | false | `missing`; no admitted call exists |

Without a ledger, dispatch remains `unknown` and spent remains null, even for
a mechanically accepted caller-supplied result. A last complete raw response
can be reconstructed after a missing settlement; a later admission without its
preceding settlement refuses. No replacement call is purchased.

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
