# v10s matched canaries — native-first registration after the v10r stop, 2026-09-17

**Codex continuation, 2026-09-17:** the last Opus review workflow exhausted
its credits before any of its three reviews completed. Codex completed the
review and merged the corrected controls in #2017. The native overlay now
pins those bytes: controller interrupts retain their original cause before
shutdown (#2042), and valid Unicode text no longer breaks JSONL parsing
(#2043). The scientific registration remains `30d6d5a4…`; the updated overlay
is `8678ed09…`. All registered input, history and instruction checks were
repeated offline. See the [continuation review](review_2026-09-17.md).
The private launch preparer now requires a separate post-merge instruction
(#2044). No launch receipt has been issued and no generation has started.

This fresh condition follows the [stopped v10r CHORUS native canary](../matched_cborg_2026-09-16_v10r/CHORUS_agentic_stopped.md),
which read all eight chunks, wrote its coverage receipt, full record and
derived core, passed the receipts check before core derivation, and was
stopped by the controller at the registered 1,800-second attempt deadline in
Phase 3 (#2010). It registers the same four canaries under the same
**native-first order** — CHORUS agentic, Kids First agentic, CHORUS API,
Kids First API — with **no per-attempt cost cap on the agentic canaries**
(the direction of 2026-09-16 stands) and a **registered 10,800-second
wall-clock deadline** per native attempt. The API caps are unchanged. Each
later canary requires independent acceptance of the unchanged originals of
every earlier one; a failure stops expansion. No paid generation, remote
token-count request or launch receipt has been issued for this registration.

The [scientific registration](registration.public.json),
[native controls](native_overlay.public.json),
[offline checks](offline_preflight.public.json),
[sizing evidence](sizing.public.json),
[model observation](model_catalogue_check.public.json),
[implementation identities](reviewed_controls.json) and the
[maintainer's decisions](budget_authorization_2026-09-17.json) support review.
Executable inputs, complete cost calculations and settled accounting remain
local. Public views bind their original digests but cannot execute jobs or
independently establish private accounting or preservation.

## What changed from v10r

- **Attempt deadline (#2010).** The deadline is now a registration
  parameter; this registration sets 10,800 seconds, three API phase
  deadlines. It is a wall-clock control, not a cost bound. The v10r value,
  1,800 seconds, had been hardcoded since v10q and stopped the v10r CHORUS
  attempt in Phase 3.
- **Stop records (#2014, #2018).** A stopped controller receipt states
  whether the transcript reached the runtime's result line (a deadline stop
  leaves none, so the ledger, not the transcript, is the attempt's
  accounting), and every controller stop is recorded in the ledger, not only
  the ledger's own and the capped client's; the deadline is recorded under
  the proxy's state lock before admission closes, so a request refused
  during shutdown cannot stand in for it (#2023, #2029). Every stop is
  named with its source. An error nothing else explains is named by its
  type, and an interrupted controller records its stop like any other.
  Missing or malformed evidence inputs fail validation instead of stopping
  the attempt (#2038).
- **Playbook (#2013).** Receipt reasons are quoted (the v10r receipt first
  failed to parse on a reason containing `: `) and a file is read before it
  is rewritten whole. Phase 3's read scope names the same-run coverage
  receipt, whose entries its back-ports edit in place (#2041). The playbook
  bytes move, so the native instruction identity moves.
- **Denial criterion (#2012).** By the maintainer's ruling of 2026-09-17, a
  denied command that the instruction prescribes disqualifies a run, while
  denials of commands the system prompt forbids are listed and do not
  disqualify it on their own. The v10r run's five denials were all of the
  second kind; the allowlist held. The controller enforces the ruling
  (#2026). It classifies every denial the runtime's result line records,
  whether the attempt completed or stopped (#2037). On a completed attempt,
  validation fails for a denied prescribed command, or for a denial record
  the controller cannot classify, after every other check has run. A
  stopped attempt is not accepted in any case, and its receipt names those
  denials under `disqualifying_denials`. A prescribed command is a roster
  CLI command, a registered module entry point, a `-c` program the
  instruction prescribes verbatim, or a file operation inside the registered
  outputs, with no shell operator and no `--help`. A read of a registered
  input also counts: the bundle, chunk map, source manifest, instruction,
  one of the two schemas, or a playbook the instruction reaches (#2039). The
  controller reads each command as bash does, so a second command on a new
  line or a merged redirection is not the prescribed command (#2031, #2033).
  A blank command is listed and does not disqualify (#2036). A deadline stop
  leaves no result line; its receipt says that it classified nothing, and
  the transcript's tool history is the source (#2032).
- **Accounting checkpoint.** The continuation ledger is v10r's with the
  request that was in flight at the deadline settled on the maintainer's
  exact confirmation of the provider's own spend-log charge: 193
  settled requests, no unresolved charge. The v10r attempt's five generated
  originals join the preserved prior originals (476 in all), each
  hash-verified.
- **Not added.** The approved proposal named an enforceable Phase 1 gate.
  The review of the v10r outcome (#2016) established that the v10r run did
  pass the receipts check before its first Phase 2 command, so the gate
  stays instructed and is verified from the tool history.

Unchanged from v10r: renderer **12**, evidence protocol **v3**,
source-review instrument **v1**, the 96k API audit/report allowance, the
strict receipt floors, registered source/chunk binding, the explicit
provider context-bypass policy, the observer's refusal model, the allowlist
roster and prescribed-commands-only shell rule, the pinned Claude Code
**2.1.272** binary with its 64k-per-call declaration, the source bundles,
chunk manifests, profiles, prompts, 3.0.0 schemas and evaluator definitions.
The offline preflight verified 473 registration pins, 9 native pins
(eight repository files and the runtime binary), 476 prior originals and
3,241 historical files, rebuilt all 32 instructions and 16 initial requests
exactly, and found 64 distinct unused output directories.

## Budget

Agentic attempts (CHORUS native, Kids First native) carry no per-attempt
cost cap: their registered limit equals the additional allocation, so the
sequence ledger — the unchanged $200 allocation less every settled charge —
is the only cost bound, and a single attempt may in principle consume all of
it within its 10,800-second deadline. The API caps are unchanged ($10
CHORUS, $15 Kids First). Unknown charges retain their reservation and stop;
there are no automatic whole-attempt retries. Review and merge of this
registration are not spending approval, and neither is the maintainer's
funding answer: no launch receipt may be issued until independent
registration review and required CI pass, fresh
input/runtime/model/accounting checks succeed, and the maintainer gives an
explicit launch instruction.

## Ordered launch and acceptance

1. After every launch gate (independent review, exact-commit CI, fresh
   input/runtime/model/accounting checks, the maintainer's explicit launch
   instruction and a launch receipt), admit **one
   CHORUS native canary** through the registered controller. Every model and
   tool turn passes serial admission under the sequence cap, the only cost
   bound on an agentic attempt, and the attempt stops at its registered
   deadline; the child receives a local transport token, never the provider
   key.
2. Independently review the unchanged original full record, its derived
   core, the audit, source grounding and qualifiers, provenance, receipts
   and report, **and the actual tool history**: every registered chunk
   read, the original-freeze result hashes and their ordering before
   reconciliation, the checker tool results, request settings and stop
   behavior. Four checks are explicit acceptance criteria, read off the
   tool history and the controller's receipt rather than off the final
   files: each chunk's receipt entry was written with the file tool before
   the next chunk was opened; the receipts check ran and passed before the
   first Phase 2 command (core derivation); no command the instruction
   prescribes was denied, and every denial of a forbidden command is listed
   (the receipt carries the classification whenever the transcript holds
   one runtime result line and says so when it does not, and then the tool
   history is the source); and a stopped receipt names its stop reason with
   that reason's source (ledger, controller or proxy; an unexpected error by
   its type, #2038) while the ledger records the stop. Reject continuation after a failed source or evidence
   check even if current-file checks later pass. Verify the run read the
   3.0.0 merged schemas the registration pins and that no value echoes a
   schema example or a vocabulary term the sources do not state.
3. Only after acceptance, admit Kids First native under the neutral profile
   and the same complete bytes, then CHORUS API and Kids First API,
   accepting each unchanged result before the next.
4. A failed canary stops expansion. Ordinary report correction and
   legitimate shape repair are paid conditional work under the same limits,
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
whose v10s section of 2026-09-17 supersedes its v10r section, and
[sequence tracker #1763](https://github.com/bridge2ai/data-sheets-schema/issues/1763).
