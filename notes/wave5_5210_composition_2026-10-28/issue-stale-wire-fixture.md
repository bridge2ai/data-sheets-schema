# Report-admission wire fixture still pins the pre-D38 A13 parent

Local issue draft; not filed and no issue number assigned. Refs #5210 / #5157.

Composing #5210 `aaa6f5bec2a0c7832d36143c4c7470d51cb8cee4` with A13
`04799422669fb2bd9f571bf8c0800dfc4b0ef008` makes the historical CHORUS wire
test fail at its first `BASE_WIRE_SHA256` comparison. The fixture describes
`f8c5ac73c`, while the incoming parent contains the authorized D38 prompt
spelling/wrapping changes. This blocks the integration test; it is not evidence
that admission mutates requests.

Reproduction is preserved at `dc9ca46701e74e712bf1800fbda8542b84e4c91e`:
the three full suites produce 236 passes and this one failure. Independent
source-attested derivations reproduce all three old hashes and show that the
incoming A13 requests differ only by the inherited prompt hunks. The reversible
comparison is committed in `notes/wave5_5210_wire_lineage_2026-10-28/`.

The local repair at `ad1f950df173f8ed07023faeff612feb32b4dec7` names the new
baseline, retains the original hashes as historical metadata, and preserves
every count-to-dispatch, saved-measurement and admission-on/off assertion. The
complete affected test passes after the correction. All other fixture AST and
production bytes are unchanged.

Acceptance: preserve the failed full run; independently derive the incoming
parent's bytes; retain the old identities; pass the complete CHORUS integration
case without weakening its assertions. Local acceptance is met, but publication
and final integration remain with Claude/AGY.
