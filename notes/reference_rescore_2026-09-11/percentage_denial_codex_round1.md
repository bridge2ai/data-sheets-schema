# Codex Adversarial Review

Target: branch diff against 79cc116099e1b95bdc03a1c2d54b7fbd46bec931
Verdict: needs-attention

Hold PR1330: conflicting validator evidence can pass attestation. Percentage reporting passed in-memory Python 3.9.6 checks; grading prompts, arithmetic checks and settings are unchanged. Full suite was not run.

Findings:
- [medium] [P2] Reject conflicting validator results before preserving attestation (scripts/reference_rescore.py:298-304)
  The denial exemption preserves outstanding `calls`, including failed validators. A failed exact validator followed by a proven denied compound command and a duplicate successful-looking result for the validator ID returns True at HEAD versus False at the base. Lines 311–317 leave failed calls registered and accept the conflicting duplicate. Thus a malformed or replayed transcript can pass validate_candidate's exact-validation gate without unambiguous successful validation. The added tests omit this combination.
  Recommendation: Require unique, ordered validator uses/results and retire each call when its result arrives. Reject conflicting duplicate outcomes. Add a regression for failed validator → attested denial → duplicate successful result.

Next steps:
- Fix validator evidence handling and rerun focused attestation and reporting tests on Python 3.9+.
