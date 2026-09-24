# CHORUS audit26: stopped integration and controller repair

Audit26 launched on September 24, 2026 at 07:16 UTC and stopped at 09:14 UTC.
Its 70 admitted requests are settled in the registered accounting record:
69 usage-priced requests total $13.90010175, and one authorized stall debit is
$3.03258750. The latter is the full reservation; the provider's actual fee remains
unknown. The same native session continued successfully after that transport
stall. Total audit26 accounting is $16.93268925. Shared accounting is
$486.86660200 of the approved $500, leaving $13.13339800. No charge confirmation
is pending.

A passive projection of the frozen control evidence identifies the cancelled
callback as the registered assembly command. It has no recorded parent approval;
an error result appears in the retained tail after cancellation. Callback and
cancellation timestamps were not recorded, so this does not establish the delay
or its cause. The projection reran no scientific checker and read no audit output.

The controller stopped on a native callback cancellation. Its `BudgetStop`
exception class does not establish that this was a budget admission failure.
The stopped runtime, process absence, complete frozen inventory and accounting
were independently checked. No scientific acceptance or evaluation follows from
these operational checks. The audit output has not been accepted.

A separate synthetic reproduction found that synchronous history verification can
block the control pipe beyond the native callback deadline. It uses the real
controller and batch history with a scripted host and a delayed verifier, without
provider contact. It establishes the code defect reported in
[#2420](https://github.com/bridge2ai/data-sheets-schema/issues/2420); it does not
measure the duration or establish the latency cause of the actual audit26 stop.
A recorded parent decision alone does not prove it reached the native runtime.

The repair is an explicit integration-only control selection. It must preserve
history-before-authorization ordering, bounded classification and fail-closed
cancellation while servicing the control pipe during verification. Validation
includes synthetic timeout/cancellation tests, legacy replay compatibility, an
independent review, and the pinned native executable against an offline upstream.
No new paid attempt is part of this repair.

The current one-hop closed-worker checkpoint protocol cannot use workers from
attempt25 while naming attempt26 as the immediate accounting predecessor. The
canonical sequence owner and all charges remain intact. A future attempt needs a
fresh, eligible registration, costed workload and independent review; it must not
silently reuse the failed integration or roll accounting back to attempt25.
Kids First remains after one accepted CHORUS pair. All planned CHORUS evaluation
styles remain pending acceptance of that pair.
