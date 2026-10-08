# Informational native receipt-origin reporting (#4609)

This engineering slice adds opt-in receipt-origin reporting to the released
`native_attribution` and `neutral_supervisor` paths. It addresses part of
[#4442](https://github.com/bridge2ai/data-sheets-schema/issues/4442); that parent
remains open for the other integrations.

The registration APIs accept `receipt_origin_version=1`. The selector must be
an exact integer: booleans, strings and floating-point aliases are refused.
Omitting the selector and selecting `0` produce identical registration bytes
under the same source version, without adding a selector or origin-report
field. Source dependency pins necessarily change when the source changes;
this does not promise identical historical registrations across commits.
Version 1 derives the transcript, full-record and
receipt identities from the selected registration, rather than accepting
caller-provided artifact identities.

The registration stores those identities in `receipt_origin_reporting`; the
final report adds `gates.receipts.receipt_origin`. The `original_receipt` name
identifies the registered receipt artifact, not a separately reconstructed
original/effective receipt history.

Classification uses the merged `receipt_origin.origin_captured` instrument
and sealed captured bytes plus recorded path identities. It does not invoke
the ambient-path `origin` reader. The report identifies its byte inputs,
instrument and limitations. Missing or inconsistent evidence remains
`unknown`; it is never counted as contemporaneous evidence. Re-reading a
published result reconstructs the opted-in origin report from verified
captured inputs and compares it with the saved report, including failed or
incomplete attempts.

Adversarial review found that the attachment helper initially accepted an
unsealed capture. [#4611](https://github.com/bridge2ai/data-sheets-schema/issues/4611)
requires `snapshot.sealed is True` before using its bytes. Other seal states
now produce the same explicit unknown report as unavailable capture. Both
released production acquisition paths already sealed their snapshots; the
regression protects the helper boundary.

[#4613](https://github.com/bridge2ai/data-sheets-schema/issues/4613) addresses
another reachable boundary: an 8 MiB full-record Write identity fits the
controller's 16 MiB frame limit, but retaining it in the origin detail makes
the serialized final report exceed its reader's 8 MiB cap. Both version 1
publishers now check the exact serialized final bytes before writing
`final.json` or its publication marker. Oversized output is refused with
earlier attempt evidence retained; no report detail is silently dropped.
Registration and input limits remain unchanged. The pre-existing version 0
publication behavior is outside this opt-in change.

The origin report is attached after the existing gate results. It does not
change a gate, a receipt floor, completion status or the first stop reason.
Its counts describe the observed receipt-writing history. They do not prove
source support, factual accuracy, scientific acceptance, independent review
or readiness for a paid generation run.

The adversarial tests in
[`tests/test_native_receipt_origin_reporting.py`](../../tests/test_native_receipt_origin_reporting.py)
cover exact version selection, version 0 compatibility, registration-derived
identities, sealed-byte-only classification, missing and inconsistent
evidence, alias handling, detached return values, and saved-report tampering
after publication hashes have been recomputed. Existing synthetic offline
consumer fixtures exercise both released paths; their fabricated native
observations and authorization documents are software test data, never
production authority. Test results are recorded after the source is frozen
and the focused suite has completed.

The published but unmerged shared adapter in
[#4354](https://github.com/bridge2ai/data-sheets-schema/pull/4354),
[#4468](https://github.com/bridge2ai/data-sheets-schema/issues/4468)
original/effective receipt history, figures, and the held controller/audit28
work are outside this slice. Human scientific review and paid-run holds
remain in force. No provider call, scientific scoring run or production
attempt registration is part of this change.
