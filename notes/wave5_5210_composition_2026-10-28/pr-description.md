# Suggested description for the composed #5210 packet

The raised-cap reconciliation and report requests are counted and admitted
before dispatch. Refused regates preserve the existing report, and validator
repair retains a durable report-refresh obligation across interruptions so
resume cannot repeat sealed work or lose the owed refresh. Refs #5157.

This packet composes the report-admission branch with the tested A13 receipt
packet using merge commits. No manual production conflict resolution was
needed. The CHORUS request fixture now names the incoming A13 baseline; an
independent old/new reconstruction proves that its changed hashes come only
from inherited D38 prompt edits. Historical hashes and every admission parity
assertion remain preserved. Production and protected bytes were not changed
to repair the fixture.

Validation: the full three-module run produced 236 passes and one stale-golden
failure. After the fixture-only correction, the complete affected test passed,
including exact counted-versus-sent requests and admission-on/off parity.
Together these cover 237 distinct passing cases, with no skips/errors; this is
not a claim of one green full-suite rerun. The failed run, independent baseline
proof, source attestations and compact evidence are retained in
`notes/wave5_5210_composition_2026-10-28/` and the linked wire-lineage packet.

Local issue drafts record the stale fixture and the hardened Git provenance
check; neither has been posted or assigned a new GitHub issue number. Claude
directs review and final integration; AGY handles publication. No live provider
calls or scientific scoring were performed.
