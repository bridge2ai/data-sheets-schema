Registered evaluation results need consistent provenance checks and blinding
before comparison. This change connects the registered runner's retained
ratings to the comparability audit, shares identity-aware blinding and leakage
checks, keeps the private review key outside reviewer material, and reports
recorded bundle identities without treating them as equivalent source exposure.

It also implements the owner's two D52 deterministic scoring rules: accept the
two approved nested governance-contact representations, and omit exactly four
Q9 regulatory subfields only when `regulated_access` is explicitly false. Q9
keeps its five-point maximum and explains the reduced field denominator in its
applicability evidence. This changes the scoring instrument identity; it does
not add source coverage or rewrite historical scores.

The merge preserves published E3x ancestry and composes it with #5095 at
`cf01eb12bbbbde04854163ecb1036cf9a5431e6e`. No new production repair or conflict
resolution was needed. Protected generation assets, rubrics, contexts and the
decision record match that base. Target `feat/v10-preflight-scripts` initially,
then retarget `main` after #5095 lands; preserve the merge ancestry.

Validation: **588 passed, zero failures/errors/skips/deselections**, including
the committed-corpus check, at frozen head
`fbbb2c7599c4a4a98ae27242db9b05c90954a020`. Source and import-origin checks
passed. See `notes/wave5_evaluation_integration_2026-10-28.md` for the module
counts, instrument identity, reproduction command and compact evidence digests.

Historical/v8 (#5126) and native E5-direct rating adapters remain design-only.
This PR does not authorize generation or scoring. Claude's #5164 context/table
changes and the remaining owner/lead acceptance gates stay separate.

Refs #5125, #5131, #5132, #5133, #5135, #5136, #5137, #2912, #5121.
