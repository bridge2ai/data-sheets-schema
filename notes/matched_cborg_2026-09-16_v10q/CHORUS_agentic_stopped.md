# CHORUS native v10q stopped outcome — 2026-09-16

The approved CHORUS native (agentic) canary — the first native attempt under
any v10 condition — ran through the registered controller for 29 minutes,
wrote its coverage receipt and its full D4D record, and **stopped at the
registered $10 whole-attempt cap** before the audit, reconciliation, derived
core, provenance and report phases: request 58 needed a reservation the
remaining headroom could not cover. The ledger recorded the refusal, the
denied request is retained unpaid, every admitted request is settled, and
there is no unresolved charge. The attempt is stopped and unaccepted; it
will not be resumed or overwritten, and no retry is authorized by this
record. Exact amounts and provider identifiers remain local; the sequence
tracker carries the settled figures.

Registration `2148adf6…` and native overlay `cff4d6f0…` were merged in #1881
after independent review and required CI, on the 3.0.0 schema release
(#1880). The user approved the budget amendment and the merges; a separate
hash-bound launch receipt with fresh pin, runtime, model-route and accounting
checks admitted this one job. The [public outcome record](outcome.public.json)
binds the launch and the two delivered artifacts.

## What the run did

- 57 model requests admitted through the loopback transport, 61 runtime
  turns, 118,696 output tokens of which 74,283 thinking; the CLI's own total
  equals the ledger's settled total.
- The full record validates against the 3.0.0 schema offline (35 top-level
  slots, `id` the CHORUS site root) and has no duplicate keys. Those are
  structural facts, not source acceptance: no audit or independent source
  review exists.
- The coverage receipt names the registered bundle's md5 and covers chunks
  c001–c006 (five extracted, one nothing-relevant); **c007 and c008 were never
  receipted**, and the run went on to write the full record anyway. The
  strict receipt floor would have rejected the attempt on that alone.
- The runtime recorded **eight tool-permission denials** — two `--help`
  explorations, `schema --help`, `agents digest`, a heredoc script, a
  scratch file under `/tmp`, one `python -c` chained with a redirect and
  `wc`, and a shell append to the receipt (other multi-line `python -c`
  calls ran) — so the
  controller's post-run check would have failed the attempt even had the cap
  held. The bundle itself was read correctly: every one of the eight
  chunks was opened with the file tool exactly at its manifest boundary,
  in order (c002 and c006–c008 re-read whole, c003 re-read in halves) — so
  c007 and c008 were read and simply never receipted, and the
  `d4d receipts check --strict` gate the playbook prescribes before Phase
  2 was never run.
- The controller receipt records `error_type: PermissionError` and no
  reason; the ledger's stop entry is the authoritative cause (#1914).

## What it establishes, and what it does not

This is the **first empirical native sizing point** (#1917): chunk review plus
the full record alone cost more than three quarters of the $10 cap that
v10p carried as an unmeasured ceiling, and the remaining phases are still
unmeasured. It establishes nothing about source correctness, and the
protocol deviations above (#1918) are review findings against the playbook
and the allowlist (#1916), not evidence about the model's output quality.
The transcript observer cannot read this runtime's transcript until #1915
is fixed, so read-window coverage was established by hand from the tool
calls.

## Next

No paid attempt is admitted by this record. Before another native canary:
fix #1914–#1916 and decide #1918; register a fresh condition with a native
cap informed by this measurement and a fresh cost proposal; independent
review and exact-head CI; explicit user approval of that cap; then launch.
Kids First native, the API canaries, evaluation canaries and production
remain queued in the [continuation plan](../matched_cborg_native_first_continuation_2026-09-16.md)
and tracker #1763. All prior attempts and every historical record and score
remain unchanged.
