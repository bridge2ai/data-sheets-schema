# D52 publication review findings — local issue drafts

These retain Claude's D1–D3 findings for the issue workflow. No GitHub action
was made in this offline session. Match any existing filed issue before posting
a duplicate; no remote issue identity has been established here.

## D1: Exported Q9 label claims criteria excluded by applicability

With `regulated_access: false`, the D52 evaluator scores the three retained
criteria while retaining a band label that claims confidentiality classification
and governance contact. Those fields were excluded, so the exported label
overstates what was measured. Claude's independent review reproduces this on
the 54 CM4AI records whose Q9 increases under D52; no corpus re-score is needed
to reproduce the defect with a synthetic record.

Repair: when D52 omits criteria, use a neutral coverage label with the actual
retained-field count and excluded-criterion count for each dataset unit and
the selected worst-unit score. Preserve numeric scores, maxima, evidence,
applicability note and all labels outside this condition. Regression checks
cover exported JSON, zero/partial/full coverage, collection members, and
true/missing/unknown context. No canonical rubric or historical score changes.
Validation status is recorded in the publication follow-up report.

## D2: Confirm Rubric10 E2.2 scope for committee-contact aliases

Resolved by the owner's **D61 at 2026-10-28T18:23Z**: the two nested contacts
count as one criterion wherever governance committee contact is scored,
including Rubric10 E2.2. Claude recorded this at
`8c91e373a39cfc47a128ce21b034bd6587adcddb`. No alias implementation change is
needed. The four CHORUS 0-to-1 changes belong to the new evaluator instrument;
historical scores stay unchanged. This packet does not edit the decision record.

## D3: Replace derivable source-inventory tarballs in publication tree

The original D52 packet adds two approximately1.5MB tarballs dominated by
before/after tracked-source inventories. Preserve the small original results,
origin checks and scoring identities verbatim; reference the inventories by
hash and regeneration/recovery commands. Keep originals recoverable.

The new publication tree retains compact result directories with independently
checked archive/member hashes. The original manifest, archives in earlier
commits/worktrees, and external evidence directories remain intact. Only these
two tarballs are removed from this new tree; Git history is not rewritten.
See `notes/d52_scoring_validation_2026-10-28/README.md` for exact disposition,
manifest hashes and recovery commands. No claim is made that historical Git
object storage shrinks.

Claude's D4 literal-path maintenance nit and D5 parent-field specification
observation remain outside this narrow publication correction.
