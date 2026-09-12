# Canonical validator paths — 2026-09-12

The fill paused with 21 accepted ratings and two new incomplete attempts:
CHORUS v8 rep2 rubric20 and CHORUS v8 rep3 rubric10. Both wrote candidates,
but neither successfully ran its own validator. They remain excluded and
require fresh independent attempts. Their raw evidence is preserved on results
PR #1313 at commit `88b82c1e7458021d8d2dd28d47f5a26b45acb3b0`.

The rubric20 attempt appended `; echo "EXIT=$?"` to both validator commands.
The rubric10 attempt did that first, then tried a valid absolute command.
Its runtime directory began `/private/var/folders/...`, while the host's
temporary directory used the equivalent `/var/folders/...` symlink alias.
The runner built the absolute permission prefix from the uncanonicalized path,
so the evaluator's canonical command did not match. This is #1317. The extra
shell commands remain outside the registered exact-command contract.

The fix resolves the isolated directory before constructing its paths,
working directory and permission prefixes. A regression using a symlinked
temporary root checks the grants from a child process and invokes the real
validator with canonical absolute paths. It failed before the fix; the focused
runner and semantic-contract suite now passes 118 tests. The independent Codex
review approved code commit `e64379a61f288cec3662766bc8b8b8bbddf43040` with
no concrete P1/P2 blockers. Its report is `canonical_validator_codex_review.md`.

The runner-only amendment is manifest SHA256
`3ecc08aa6aed274737505e658743729dd1c293438ac8416df42b5c6b533533f6`.
Complete evaluator prompts, both definitions and rubric texts, schemas, all
24 input records, 202 prior evaluations, cohort, execution settings and budget
remain unchanged. The previous manifest and acceptance are archived under
`registrations/`; `canonical_validator_registration.json` records the preserved
main-branch evidence and the two current-registration recovery receipts.

The original CHORUS canary was revalidated offline and accepted separately
after checking its unchanged output, unique receipt, runtime, check-echo and
quoted definition SHA256
`66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`.
The existing AI_READI v8 rep1 rubric10 rating was also revalidated from its
original evidence. Neither output was opened for rewriting, and no model call
occurred. The remaining nineteen previously accepted ratings on #1313 must
receive the same offline revalidation before execution resumes. Its snapshot
preserves all 21 output hashes and 165 retained attempt-file hashes and verifies
each output against the evaluator's original successful Write.

All three unvalidated drafts across the study remain excluded. The two new
failed CHORUS ratings will be retried individually after registration and
review, with the unchanged prompts and $5 attempt cap, before the remaining
fill resumes. No new D4D generation or download is part of this amendment.
