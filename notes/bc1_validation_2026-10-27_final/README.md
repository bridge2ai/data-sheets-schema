# Final BC1 verification, 2026-10-27

Tested head: `bd94ed84642bdeddd1c1a0361a92b438aaf0e028`.
Delivery branch: `codex/bc1-production-impl-20261027`.
The source stayed unchanged during both runs, both origin checks completed,
and the attestation drivers exited zero. No provider or network calls occurred.
The protected shared-generation hook was compiled only in memory for the
public test; this is not installed-hook or scientific acceptance.

| Run | Result | Pytest / driver seconds | Outcome SHA-256 |
| --- | --- | --- | --- |
| `bd94ed846-provenance` | 41 passed; zero failures/errors/skips | 2.05 / 4.13 | `d0acb6b2cab4e9d6d74757998281b76ce324f66500720c888bc6ac583fead894` |
| `bd94ed846-pipeline` | 1 passed; zero failures/errors/skips | 507.36 / 512.56 | `e23403f974494bb3bb8fda1a037ee59e7ef4003bd3a2db28a933138901b9b9ce` |

The public case checks complete fixed-roster audit execution, exact projected
model carry, final provenance conformance, and completed replay with no new
generation/count calls and unchanged usage/artifact bytes. The source/client
fixture is explicitly invented; acceptance is mechanical only.

The earlier full BC1 run at
`c9feaedc36a4bf77d9cf604f783748e29b9c1a21` passed 162 cases and failed this one
public case at final provenance conformance. The sole production change for
bd94ed846 is `src/data_sheets_schema/schema/d4d_generation_record.yaml`;
runtime code and the public test are unchanged. Thus the composed coverage is
**163 distinct BC1 passes across two heads**, plus **41 provenance controls**.
This is not a fresh 163-case all-green batch. Original failures are retained in
the neighboring `bc1_validation_2026-10-27_full_initial` archive.

The 118 passing c9 legacy omission/selection/condition cases are a subset of the
earlier 317 passing legacy cases (with one optional historical-data skip).
Neither those overlapping runs nor the three overlapping positive cache tests
are added into the distinct BC1 count.

`scripts/adhoc/archive_n2_restack_validation_20261027.py` made the archives,
verified selected-file bytes/modes and unchanged originals, and recorded the
excluded external synthetic case directories. [Manifest](manifest.json)
SHA-256: `44d329185837036ec10c9c17a6a821847836ee99c5182b11be48dc77a33279c4`.
All helper sources are committed with the results. Third-party dependency
bytes are not fully attested, and timings are not idle-host benchmarks.
