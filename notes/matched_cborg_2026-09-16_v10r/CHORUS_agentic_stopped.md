# v10r CHORUS native canary — stopped at the registered attempt deadline (2026-09-17)

The first canary of the v10r registration (`registration.public.json`,
registration `128d6708…`, native overlay `883a6892…`), launched on the merged
main head `372b5823b` under the launch receipt `CHORUS_agentic_launch_approved.json`
(sha `d453a44f…`), ran from 06:12:39 to 06:42:41 UTC and was stopped by the
controller with **"native attempt deadline elapsed"** after **83 admitted
model requests**. The stop came from the controller's wall-clock deadline, not
from the budget ledger: `agentic_attempt_deadline_seconds` is 1,800 in the
registration, carried unchanged from v10q when the per-attempt cost cap was
lifted (#1917). A time cap had replaced the cost cap (#2010).

## What the run produced before the stop

- Phase 1: the coverage receipt for all **8 of 8 chunks**, each chunk read
  with the file tool and its receipt entry written before the next chunk
  (the #1918 protocol held); **1,698 of 1,698 bundle lines** read, 0 chunks
  unopened; 10 bundle searches, counted separately.
- Phase 2: the full record (validated after a repair of date-typed values the
  first draft wrote unquoted), the derived core, and the evidence originals of
  both. The receipts check on the final receipt read
  `chunks 8/8 reviewed · snippets 96/96 verified · slots 80/140 with a receipt (24 exempt)`.
- Phase 3 (source review inventory) was in progress at the stop. No audit,
  no provenance record, no report.

## Tool-history checks the registration's README names (#1918)

| check | result |
|---|---|
| receipt entry per chunk with the file tool before the next chunk | held, 8/8 |
| receipts check passed before any Phase 2 command | **failed**: the full record was written at 06:28; the first receipts check ran at 06:35 and read the receipt as unreadable YAML; the receipt was rewritten and the check passed at 06:37 (#2011) |
| zero permission denials | **failed**: 5 denials, every one an attempt at a command the pinned system prompt forbids — `--help` on the CLI, a python heredoc, two greps over the runtime's own session file, a chained `grep | head; grep` over the bundle (#2012); the allowlist held |
| ledger reason on a stopped receipt | not applicable: the stop was the controller's deadline, recorded on the receipt with `reason_source: controller`; no ledger stop occurred |

Other errors in the history: `download priority` invoked with an option the
command does not take, and one Write refused because the file had not been
read first (#2013). The transcript ends without a runtime result line, so the
transcript observer reads per-message snapshots only (98 tool uses, 29 minutes
of activity, 1,698 lines of coverage; its output-token figure is the
snapshot undercount and not the run's accounting) (#2014). The attempt's
accounting is the ledger's.

## Accounting and disposition

Every admitted request settled in the private ledger; the one request in
flight at the stop keeps its reservation, as the policy requires. Settled
totals, the reservation and the remaining allocation stay in the private
accounting.

The attempt is **not accepted** and is **never resumed or relabelled**. Its
transcript, request records, controller receipt, traceback, both generated
records, the receipt and the evidence originals are preserved privately with
a hashed inventory. Expansion stops here: no Kids First native attempt and no
API canary runs on this registration. Any further native attempt needs a new
registration in which the attempt deadline is sized deliberately, the Phase 1
gate is enforced rather than instructed, and the denial policy is decided —
and the maintainer's explicit approval to spend again.

Issues: #2010 (deadline), #2011 (gate ordering), #2012 (denials), #2013
(command errors), #2014 (no terminal result on a deadline stop).
