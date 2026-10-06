# Registered native receipt-origin reporting

Receipt origin describes the history visible in a captured transcript. It does
not establish semantic support, change receipt floors, or grant scientific
acceptance. Existing registration defaults retain their original gate output.

Each existing offline registration constructor accepts the keyword-only
`receipt_origin_version`: exact integer `0` (the default) adds no declaration;
exact integer `1` derives a closed `receipt_origin_reporting` declaration from
the selected attempt transcript, original receipt, and full-record paths.
Booleans and other versions are refused. The supported constructors are:

- `native_execution_registration.registration` for the existing direct native
  attribution execution contract;
- `native_attempt_supervisor.registration` for the synthetic neutral supervisor;
- `native_shared_registration.registration` for native26.

The existing `python -m data_sheets_schema.native_execution prepare` command
also accepts `--receipt-origin-version 1`. This prepares a proposal only; it
does not launch a runtime. Review, CI, permission and owner-launch declarations
must bind that exact new registration. Old registrations and evidence are not
rewritten to enable reporting retrospectively.

Version 1 adds `gates.receipts.receipt_origin` after the existing receipt gate
has been computed. All original gate fields and completion conditions remain
unchanged. The envelope pins the captured transcript, full record and original
receipt, and runs the existing receipt-origin classifier on captured bytes and
recorded alias identities. It never resolves paths or reads fallback files.
Missing evidence or unresolved identity produces an explicit unknown report.

Native26 preserves original and effective receipt identities separately. Its
existing gate still verifies the selected original against the phase-one seal
and the effective receipt against reconstructed stage completion. Original
receipt history does not describe effective receipt counts, even when their
bytes are equal. Effective origin is therefore explicitly unknown until an
instrument supports that helper-produced history. No classified split is
invented for it.

All three saved readers rebuild and compare the reporting envelope. They retain
the necessary bytes during their existing captured-file validation loops;
reporting makes no additional path reads. Rehashed publication wrappers do not
excuse a missing, changed, foreign or undeclared report. The common reader also
checks unavailable reporting on failed/incomplete native26 results before the
additional reconstruction reader's early return. Complete native26 saved pools
retain their exact semantic receipt-gate comparison with the rebuilt report.

Ordinary receipt CLI/backfill metadata still uses the legacy origin instrument.
For a native final assessment it keeps the original receipt's measurement and
stale-history reason separately, while reporting effective origin as unknown.
The CLI passes the untouched owner assessment to the claim-sidecar validator;
origin and writer metadata are attached only to the reporting copy.

Offline tests use supported synthetic transcript histories, real captured-file
metadata and public saved readers. Synthetic failed-publication tests supply
only registration parsing as a disclosed fixture seam; constructor tests
separately exercise the actual offline authority reconstruction. These checks
do not constitute a completed native run, provider evidence, calibration or
scientific approval.
