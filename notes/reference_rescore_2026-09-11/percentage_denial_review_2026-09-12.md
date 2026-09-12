# Reference percentage and denied-command review — 2026-09-12

Issues #1328 and #1329 were reproduced while the #1248 reference fill remained frozen under manifest `99b90d260a2ad1a1d7859050181c74ab80bb2dc670f5f7eb96e40bbffcac838f`.

Three report regressions failed before the percentage fix. With identical CM4AI item scores and 43/47 points, serialization as 91.5, 91.49 and 100*43/47 falsely produced sample SD 0.005966305470371786. Reports now derive both bases from point totals and denominators. New tests cover zero spread for equal scores, correct nonzero spread for different scores, distinct rubric20 denominators, and preservation of raw score files.

The VOICE v7 rep1 rubric10 attempt at `2026-09-12T13-03-45.829464+00-00` had a successful exact validator followed by an explicitly denied compound Bash command. The amendment recognizes a denial only from one successful terminal CLI record plus unique matching Bash identity/input and the corresponding ordered user tool-result denial. Missing, conflicting, ambiguous, malformed and executed-failure evidence remains conservative. Eighteen new attestation cases, including a prior executed mutation and absence of any successful validator, exercise this distinction.

A read-only replay against the original VOICE trace and candidate passed the complete candidate checks with the amended code. Candidate SHA256 is `43693e5aaea65a050e71cadd2c8202f92b1e3544d480e9315108ab51e36349ac`, input SHA256 is `7660c4d93ccf05a12ebdd26c6c960e8f5d07455b3088cd3b2e909e95c802d048`, and the quoted rubric10 definition is `66ad623121272099bf94535ae5be2163a5f5005fe895d2bf2bf04c4f90e34864`. This replay wrote no receipt or evaluation output and did not accept the candidate into the fill. Registered offline recovery is still required after review.

Validation: 163 focused tests passed (reference runner, audit accounting, semantic comparison), with one existing dateutil deprecation warning. AST comparison against merged main `79cc116099e1b95bdc03a1c2d54b7fbd46bec931` proves that all runner code outside `report_results`, `evaluator_validated` and the new `denied_bash_calls` helper is unchanged. Grading prompts, agent definitions, input files, schemas, arithmetic checks and execution settings are unchanged. No evaluator calls or score edits were made to implement this fix.

The already accepted fresh CM4AI rating remains selected. Its two earlier excluded drafts remain preserved; improving attestation does not replace an existing accepted output. After source review, register the amendment, revalidate retained outputs and separately accept the original canary before recovering VOICE or resuming the remaining set.

## Round 1 finding and resolution (#1331)

Codex review of `6353b219ad64888d1117f3e9085984bc7f89fba6` found conflicting validator results could pass after a proven denial. Five new regressions reproduced false acceptance: failed validator followed by a duplicate success, success followed by a duplicate failure, duplicated validator use, an unanswered later validator, and a validator result replayed after the terminal CLI result. Validator evidence now requires one use and one ordered result before the sole terminal event, and each call is consumed when its result arrives. The retained VOICE candidate still passes the complete read-only candidate checks.

The completion audit also requires the forthcoming `percentage_denial_registration.json` and `percentage_denial_fill_preservation.json` records and verifies all their retained file hashes. Its 16 accounting tests pass with the extended preservation roster. No new reference rating has started and the existing registration remains active pending final review and amendment.

Post-fix validation: all 168 focused checks pass. A read-only replay of all 38 accepted original candidates passes the amended full candidate checks; no output or receipt was written and no evaluator call occurred. The unaccepted VOICE candidate also passes separately. Actual Python 3.9.6 imports of both runner and audit modules and a denied-call helper invocation pass without dependency stubs.
