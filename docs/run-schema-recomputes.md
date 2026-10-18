# Run-specific schemas in pair and report recomputes

`backfill_checks.compute` selects the full and core merged schema bytes recorded
by each run. `d4d provenance record` and the backfill CLI use this computation.
The full and core selectors require every recorded SHA256/MD5 to agree. They try
the named file, a registered reconstruction, then matching committed history.
Schema version labels do not substitute for byte identity.

Pair identity/projected slots and report declarations/nested ranges are derived
from those selected views. Each block records `schema_selection_instrument:
run-recorded-full-core-v1 (#4062)`, a per-file `schema_basis`, and the actual
selected `schema.full_sha256` / `schema.core_sha256`. The report's existing v7/v8
claim contract remains separately identified by `instrument`.

A missing, unrecoverable or unusable historical schema retains the established
current-file fallback, explicitly naming its reason for that file. It does not
claim a fully recovered historical pair. Recovered schemas that import local
files are refused: their recorded hash does not cover today's imported files.
When both schemas are recovered, pair comparison needs no current-schema
presence exemption. Fallback comparisons retain the existing schema-moved rule.
Historical views are scoped to the computation and released afterwards.

The optional Python `declared`/`ranges` map arguments remain available. A report
using them pins their contents under `schema_overrides`, explicitly distinguishing
those rules from rules derived from the selected bytes. Normal CLI operation
passes neither override; it no longer supplies today's maps to every run.

This changes newly computed diagnostics. It does not rewrite stored provenance,
canary thresholds, reports or source records. Corpus comparisons should inspect
both changes in gate counts and schema selection/fallbacks before deciding to
backfill. The historical rewrite decision remains separate (#4060).

Historical report v7 reproduction explicitly passes both
`report_claims_version=7` and `schema_policy="legacy_current"`. The latter retains
the former current-schema rules and block shape; it does not claim to reconstruct
the run's schema. New calls default to `schema_policy="recorded"`.
