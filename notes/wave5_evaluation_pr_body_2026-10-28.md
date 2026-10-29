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

Publication still needs the lead's disposition of Claude's independent D52
review of `4cd8f2a5191d7cb58d7bf639603a820d38e825d5`, at
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/pr5096_b0978d6e6_d52_4cd8f2a51_claude_review_2026-10-28.md`:

- **D1:** Q9's top-band label still describes criteria excluded under explicit
  false; the explanatory applicability note does not fix that label.
- **D2:** lead/owner confirmation is needed for extending the contact alias to
  the bare Rubric10 E2.2 criterion, where governance-only content can gain credit.
- **D3:** approximately 3 MB of inherited D52 inventory tarballs need a lead
  publication disposition. The new Wave 5 evidence is compact; historical
  evidence and ancestry have been preserved.

D4 (future rubric-ID/path robustness) is an optional nit. D5 (the parent
`regulatory_restrictions` criterion still counts) is an optional specification
observation, not a defect under the current rule. These findings are recorded
without adopting new scoring rules. This documentation-only update leaves the
frozen 588-test result intact; it is not an unconditional merge-readiness claim.

Historical/v8 (#5126) and native E5-direct rating adapters remain design-only.
This PR does not authorize generation or scoring. Claude's #5164 context/table
changes and the remaining owner/lead acceptance gates stay separate.

Refs #5125, #5131, #5132, #5133, #5135, #5136, #5137, #2912, #5121.
