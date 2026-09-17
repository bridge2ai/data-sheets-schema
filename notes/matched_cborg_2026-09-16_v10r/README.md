# v10r matched canaries — native-first registration after the v10q stop, 2026-09-16

This fresh condition follows the [stopped v10q CHORUS native canary](../matched_cborg_2026-09-16_v10q/CHORUS_agentic_stopped.md),
which wrote its coverage receipt and full record and stopped at its $10
whole-attempt cap before the audit (#1917), and the native-control fixes
that stop exposed (#1914–#1916, #1918; PR #1920). It registers the same
four canaries under the same **native-first order** — CHORUS agentic, Kids
First agentic, CHORUS API, Kids First API — with **no per-attempt cap on the
agentic canaries**: the user directed on 2026-09-16, after the sizing point,
that the agentic arm needs no cap, so each agentic attempt's limit is the
whole additional allocation and the sequence ledger is its only bound. The
API caps are unchanged. Each later canary requires independent acceptance of the
unchanged originals of every earlier one; a failure stops expansion. No
paid generation, remote token-count request or launch receipt has been
issued for this registration.

The [scientific registration](registration.public.json),
[native controls](native_overlay.public.json),
[offline checks](offline_preflight.public.json),
[sizing evidence](sizing.public.json),
[model observation](model_catalogue_check.public.json) and
[implementation identities](reviewed_controls.json) support review.
Executable inputs, complete cost calculations and settled accounting remain
local. Public views bind their original digests but cannot execute jobs or
independently establish private accounting or preservation.

## What changed from v10q

- **Native controls (#1914–#1916, #1918).** The controller receipt now
  carries the ledger's stop reason and a retained traceback; the transcript
  observer reads this runtime's transcripts; the overlay allowlist is a
  roster every command the playbook prescribes must be on, tested against
  the playbook, with `prompt render` and its kin allowed; the system prompt
  permits registered helpers and the instruction's prescribed commands only
  (the multi-line snapshot command included) and names what it refuses:
  `--help`, heredocs, ad-hoc scripts, chained unlisted programs and writes
  outside the output directories; the playbook requires every chunk's
  receipt entry to be written with the file tool before the next chunk and
  the receipts-check gate to pass before Phase 2, not later. The playbook and system-prompt bytes
  move, so the native instruction identity moves.
- **No per-attempt cap on the agentic arm** (#1917): the v10q attempt spent
  more than three quarters of $10 on chunk review and the full record alone,
  and the remaining phases are still unmeasured; by user direction each
  agentic attempt is bounded by the additional allocation only. Every
  request is still counted and reserved before it is sent, an unknown
  charge still stops the attempt, and there is no automatic retry. The API
  caps are unchanged.
- **Accounting checkpoint.** The continuation ledger is v10q's after the
  stop: 110 settled requests, the denied request unpaid, no unresolved
  charge. The v10q attempt's two original files join the preserved prior
  originals (471 in all), each hash-verified.

Unchanged from v10q: renderer **12**, evidence protocol **v3**,
source-review instrument **v1**, the 96k API audit/report allowance, the
strict receipt floors, registered source/chunk binding, the explicit
provider context-bypass policy, the pinned Claude Code **2.1.272** binary
with its 64k-per-call declaration, the source bundles, chunk manifests,
profiles, prompts and evaluator definitions. The offline preflight verified
the registration pins, 9 native pins (eight repository files and the runtime binary), 471 prior originals and 3,241
historical files, rebuilt all 32 instructions and 16 initial requests
exactly, and found 64 distinct unused output directories.

## Budget

Agentic attempts (CHORUS native, Kids First native) carry no per-attempt
cap: their registered limit equals the additional allocation, so the
sequence ledger — the unchanged $200 allocation less every settled charge —
is the only bound, and a single attempt may in principle consume all of it.
The API caps are unchanged ($10 CHORUS, $15 Kids First). Unknown charges
retain their reservation and stop; there are no automatic whole-attempt
retries. Review and merge of this registration are not spending approval;
no launch receipt may be issued until independent registration review and
required CI pass and fresh input/runtime/model/accounting checks succeed.

## Ordered launch and acceptance

1. After every launch gate (independent review, exact-commit CI, fresh
   input/runtime/model/accounting checks and a launch receipt), admit **one
   CHORUS native canary** through the registered controller. Every model and
   tool turn passes serial admission under the sequence cap, which is the
   only bound on an agentic attempt; the child receives a local transport
   token, never the provider key.
2. Independently review the unchanged original full record, its derived
   core, the audit, source grounding and qualifiers, provenance, receipts
   and report, **and the actual tool history**: every registered chunk
   read, the original-freeze result hashes and their ordering before
   reconciliation, the checker tool results, request settings and stop
   behavior. Four checks from the stopped v10q attempt (#1918) are
   explicit acceptance criteria read off the tool history, not off the
   final files: each chunk's receipt entry was written with the file tool
   before the next chunk was opened; the receipts check ran and passed
   before any Phase 2 command; the transcript records zero tool-permission
   denials; and a stopped receipt carries the ledger's reason. A receipt
   completed and checked late passes final-file checks and fails these.
   Reject continuation after a failed source or evidence check
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

See the [dated continuation plan](../matched_cborg_native_first_continuation_2026-09-16.md),
whose v10r section of 2026-09-16 supersedes its original step 2, and [sequence tracker #1763](https://github.com/bridge2ai/data-sheets-schema/issues/1763).
