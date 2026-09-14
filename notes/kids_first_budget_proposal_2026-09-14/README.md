# Kids First attempt-cap proposal — 2026-09-14

**Pending explicit user approval.** Propose a $15 cumulative cap for one
Kids First API generation canary and one Kids First native generation canary,
with the additional allocation still capped at $200. All other attempts
retain the $5 default. The two external attempts can together use at most
$30, including every generation phase, conditional call and native tool/model
turn. This proposal grants no paid retry, evaluation or production expansion.

The complete source bundle remains 55 documents, all 36 participating-study
descriptions and 58 chunks, SHA256
`cc45c89548158a7a909699fbf1f75e6cc88c32ac8486d5518c5d4e46cdc9447c`.
Both runtimes use the neutral profile and the same source bytes. No source
is dropped, and the uncaptured full paper remains a stated limitation.

## Why the present cap is a constraint

The [non-generating phase counts](phase_admission.json) use the v10c
registration `abde76bb0705cd96f09040cf547cff35043acf0ecfcce972630e51e6ea04714b`.
They deliberately omit carried generated outputs, which do not yet exist.

| API phase | Input tokens without carried outputs | Output ceiling | Reservation without carried outputs |
|---|---:|---:|---:|
| Full generation | 233,534 | 128,000 | $4.95790625 |
| Audit | 233,658 | 24,000 | $2.35883750 |
| Reconciliation | 233,345 | 96,000 | $4.15648750 |
| Report | 234,313 | 24,000 | $2.36375000 |

Reconciliation alone leaves only $0.84351250 for all preceding spending
under the $5 attempt cap, before accounting for its carried inputs. For
comparison, 233,534 ordinary uncached input tokens would cost $1.16767 before
any output. This is a cold-input scenario, not a claim about unobserved cache
hits. Summing reservations is not a prediction of expenditure: unused
reservations are released on complete, valid settlement. Later repairs and
report regeneration are not included in the table.

The [illustrative size sensitivity](cost_sensitivity.json) holds the rejected
CHORUS v10b attempt's output lengths and cache behavior fixed while adding
the initial-request input-size difference. That example totals about $5.71
for five API calls. It is not a forecast: Kids First's output complexity,
carried records and cache timing differ. Native costs and compaction remain
unmeasured. The proposed $15 cap provides admission room; it does not
guarantee completion or authorize spending beyond the shared allocation.

## Exact scope and activation

[proposal.json](proposal.json) names the two jobs, source hash, runtime/model,
limits and gates. [proposed_caps.json](proposed_caps.json) is the corresponding
two-job mapping for `prepare_registration.py --per-job-attempt-caps`; do not
use it to activate an exception before the user approves it. The preparer
pins the exact mapping file and validates its job identities and amounts.

The controller binds each exception to the complete registration-qualified
attempt ID. Both the proxy and native CLI use that attempt's effective cap.
Other jobs, old-condition IDs and similar names retain the default. The
ledger records each admitted cap and refuses changed, removed or renamed
exceptions on reopening. Continuation preserves earlier rows and default
caps exactly; no exception resets the $200 allocation. Unknown or pending
charges still stop all further calls.

At preparation, ten settled requests from two rejected canaries total
$6.322086, leaving $193.677914. A final registration must use the then-current
checkpoint; this planning subtotal cannot hide intervening spending. The
existing v10c draft has made no scientific calls and remains preserved.
Freeze the final budget controls before launching the next canary, so the
complete matched sequence starts under one reviewed setup.

After approval, freeze a new immutable registration with this policy,
approval evidence, current code/runtime, source/profile/prompt/schema pins,
exact output paths and current billing checkpoint. Require independent
review and exact-commit CI. CHORUS API and native original-artifact/source
acceptance precedes Kids First API, which must pass before Kids First native.
Every failed canary stops expansion and remains preserved.

The parent plan's 32-generation proposal and full/core outputs remain in
scope. Its currently enumerated rubric work includes 200 study semantic
ratings, 24 external semantic ratings, 16 direct-API canary ratings and 16
field-agent canary ratings, before additional fitness/source adjudication or
any expansion of the latter styles. This two-job cap proposal does not fund
that entire matrix or remove any style, dataset, variant or repeat to fit
$200. The production workload and cost decision remain separate.

Validation: 58 offline admission/continuation tests and 25 native tests pass,
including default and exception propagation to the CLI. These use synthetic
providers/processes; no scientific calls accompanied the implementation.
Independent review and CI remain required. Related issue: #1781.
