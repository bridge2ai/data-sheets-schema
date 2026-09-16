# v10q matched canaries — native-first registration, 2026-09-16

This fresh condition follows the stopped v10p CHORUS API canary and the
schema release that resolved the two final-freeze findings
([#1874](https://github.com/bridge2ai/data-sheets-schema/issues/1874),
[#1875](https://github.com/bridge2ai/data-sheets-schema/issues/1875)). It
registers the same four canaries as v10p under a **native-first order** —
CHORUS agentic, Kids First agentic, CHORUS API, Kids First API — per the
user's direction of 2026-09-16 to prioritize the agentic arm. Each later
canary requires independent acceptance of the unchanged originals of every
earlier one; a failure stops expansion. No paid generation, remote
token-count request or launch receipt has been issued for this registration.

The [scientific registration](registration.public.json),
[native controls](native_overlay.public.json),
[offline checks](offline_preflight.public.json),
[sizing evidence](sizing.public.json),
[model observation](model_catalogue_check.public.json) and
[implementation identities](reviewed_controls.json) support review.
Executable inputs, complete cost calculations and settled accounting remain
local. Public views bind their original digests but cannot execute jobs or
independently establish private accounting or preservation.

## What changed from v10p

- **Schema release 3.0.0 and neutral generation schemas.** The full and
  core schemas declare `3.0.0`, and every model-facing study string left
  the modules both generation arms consume (the native arm reads the merged
  files whole; the API arm reads the digest). Neither profile's digest md5
  nor any fitness specification moved; the two entry points, both merged
  files and every edited module did (unedited modules keep their hashes),
  so the registration's schema pins and the native toolchain's resource
  hashes are new. See [the release note](../schema_release_3.0.0_2026-09-16.md).
- **Canary order.** `prepare_registration.py` takes `--canary-order`; this
  registration names the agentic jobs first. The controllers already read
  the order from the registration; existing registrations keep their
  API-first order.
- **Accounting checkpoint.** The continuation ledger is the reconciled v10p
  ledger: 53 settled requests, including the separately confirmed
  interrupted-audit charge (#1865). The v10p attempt's 24 original files
  join the preserved prior originals (469 in all), each hash-verified.

Unchanged from v10p: renderer **12**, evidence protocol **v3**,
source-review instrument **v1**, the 96k API audit/report allowance, the
strict receipt floors, registered source/chunk binding, the explicit
provider context-bypass policy, the pinned Claude Code **2.1.272** binary
with its 64k-per-call declaration, the source bundles, chunk manifests,
profiles, prompts and evaluator definitions. The offline preflight verified
473 registration pins, 8 native pins, 469 prior originals and 3,241
historical files, rebuilt all 32 instructions and 16 initial requests
exactly, and found 64 distinct unused output directories.

## Budget

The four per-job whole-attempt caps are the amounts the user approved for
v10p: CHORUS native $10, Kids First native $15, CHORUS API $10, Kids First
API $15, at most $50 of new spending. Binding them to this registration and
raising the combined canary ceiling by the stopped v10p attempt's cost is
**pending explicit approval**; the exact figures are local. Review and
merge of this registration are not spending approval. No launch receipt may
be issued until the amendment is approved, independent registration review
and required CI pass, and fresh input/runtime/model/accounting checks
succeed. The additional allocation is unchanged; unknown charges retain
their reservation and stop; there are no automatic whole-attempt retries.

## Ordered launch and acceptance

1. After the budget amendment and all launch gates, admit **one CHORUS
   native canary** through the registered controller. Every model and tool
   turn passes serial admission under the whole-attempt cap; the child
   receives a local transport token, never the provider key.
2. Independently review the unchanged original full record, its derived
   core, the audit, source grounding and qualifiers, provenance, receipts
   and report, **and the actual tool history**: every registered chunk
   read, the original-freeze result hashes and their ordering before
   reconciliation, the checker tool results, request settings and stop
   behavior. Reject continuation after a failed source or evidence check
   even if current-file checks later pass. Verify the run read the 3.0.0
   merged schemas the registration pins and that no value echoes a schema
   example or a vocabulary term the sources do not state.
3. Only after acceptance, admit Kids First native under the neutral profile
   and the same complete bytes, then CHORUS API and Kids First API,
   accepting each unchanged result before the next.
4. A failed canary stops expansion. Ordinary report correction and
   legitimate shape repair are paid conditional work under the same cap,
   permitted only after clean source review. Provider interruptions remain
   tracked in #1849; #1815/#1782/#1801/#1816 stay open until a fresh
   unchanged canary is independently accepted.

## Full study and evaluation scope

The [workload inventory](workload.public.json) retains **32 full/core
pairs**, **256 rubric ratings** including 80 evaluator-canary ratings and
repeat panels, and **128 offline presence scores**, as proposed workloads
rather than a funded batch. Evaluation canaries are registered separately on
exact accepted full/core inputs, with pinned definitions, evaluator
preambles, check-echo and quoted definition hashes; numeric semantic
ratings stay through CBORG. Preserve v7/v8, historical v9 and every later
attempt and score; use matched instruments for manuscript comparisons.

See the [dated continuation plan](../matched_cborg_native_first_continuation_2026-09-16.md)
and [sequence tracker #1763](https://github.com/bridge2ai/data-sheets-schema/issues/1763).
