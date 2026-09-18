# Native phase scope review, 2026-09-17

Issue #2067 arose when the operator stopped v10w during a Phase 1 receipt
correction. The new renderer and controller distinguish that permitted work
from premature core derivation and terminal evidence/source-review failures.
No historical attempt is reclassified as accepted or resumed.

## Resulting behavior

Renderer 13 explicitly permits the generator to correct its own Phase 1 draft
record and receipt, including syntax, addresses, dispositions and source
quotations. Sources already read and registered identities still govern those
changes; transcript history cannot be reconstructed or erased. Operators cannot
repair measured results after the attempt. The strict receipt command's result
and registered floors govern the Phase 2 gate; informational diagnostics still
require independent review.

An incremental parent reviewer observes the original tool events. It requires
a passing selected receipt check after the latest full/receipt write, with no
pending receipt check or write, before first core derivation. It stops selected
evidence/source-review failures when their results arrive. Terminal replay uses
the same reviewer and preserves all failed checks and corrections. The overlay
pins the new module. Renderer 13 is opt-in; historical rendered instructions remain unchanged.

Permission classification retains its existing timing and denial rules. Pure
shell/program/roster logic is shared with phase interpretation; path lookups
remain in the timed worker. Unprescribed helpers cannot satisfy a phase gate,
and their denials do not themselves become terminal phase failures.

## Adversarial review

Four review rounds identified and resolved four findings:

| Issue | Trigger | Resolution |
| --- | --- | --- |
| #2069 | Prior pass followed by a pending receipt check | Invalidate the old gate and track the current check; pending work blocks derivation. |
| #2070 | Denied help, compound syntax or wrong manifest interpreted as phase failure | Use the shared pure admission classifier before interpreting a helper. |
| #2071 | Structured nonzero receipt exit treated as terminal | Preserve the failed result as correctable Phase 1 evidence; source/evidence failures remain terminal. |
| #2072 | Later overlapping check passes before the older check completes | Retain its success while the pending guard blocks derivation; accept once both settle without intervening writes. |

The fourth independent review found no remaining concrete blocker and independently
ran 36 phase-history/local-child tests successfully. The broader focused suite
passed 459 tests with 19 skips. The skips belong to existing corpus-dependent
tests in the isolated checkout. The three renderer tests bind the changed
instruction to renderer 13 and exercise replay and assembly identity.

Two execution-blocking regressions fail when the live phase observer is removed
in an isolated mutation: premature derivation and continuation after terminal
evidence failure. Production files were not changed for that probe. The local
control tests use synthetic child processes and real control exchanges; the
phase tests also consume actual receipt/evidence checker results. No provider
request was made.

All 32 frozen v10w renderer-12 instructions reproduce byte-for-byte under the
new code. Replaying the preserved native transcript records the failed receipt
check at event 454 and successful correction check at 462, with no terminal
phase failure and no completed Phase 2. This is a check of the reviewer, not
retroactive acceptance of v10w. The [probe summary](native_phase_scope_2067_probes_2026-09-17.json)
records identities and verification scope.

## Launch boundary

A fresh condition must pin renderer 13, the changed playbook/system prompt,
controller and phase-review module, fresh output destinations, existing source
and evaluation identities, accounting and exact merged-head CI. The current
instruction, “continue with 2067 and then canary,” authorizes one CHORUS native
canary after those checks. It does not revive v10w or authorize automatic
additional attempts.

This phase reviewer does not establish ordered initial source reads/receipt
writes, original-freeze hashes, schema/term validation, all Phase 3/4 artifacts
or source entailment. Those remain separate acceptance checks. A current
receipt pass or a clean execution history is not scientific acceptance.
