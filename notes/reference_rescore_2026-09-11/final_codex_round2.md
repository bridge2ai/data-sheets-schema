# Codex Adversarial Review

Target: branch diff against 79f628202f64453250d6047b53e0eeba8fe4b524
Verdict: needs-attention

NEEDS ATTENTION: the #1337 qualifications are supported, and all 857 preserved files and measurement numbers match baseline. However, a failed rebuild can remove the required caveats.

Findings:
- [medium] [P2] Preserve qualified reports when rebuilding fails (notes/reference_rescore_2026-09-11/execution_tools/qualify_reference_results.py:123-125)
  `--rebuild` overwrites results.json, results.md and completion_summary.md before qualify() reads and validates semantic_errata.json. In an in-memory replay with that metadata unavailable, the command failed after replacing all three reports; they still claimed 56/56 completion but contained no Q19 qualification. Malformed metadata or a failing erratum hash check has the same ordering problem. A failed regeneration can therefore leave the unqualified measurements available for manuscript use.
  Recommendation: Validate errata and completion prerequisites before overwriting reports, and stage or restore outputs so failed qualification preserves the previous qualified report set. Add a regression covering missing or malformed errata.

Next steps:
- Fix rebuild failure handling without changing original measurements or the frozen runner.
- Normal rebuild matched published reports except timestamps; qualification alone was byte-idempotent. Verification used published Git blobs and simulated writes only.
- The 24-rating inspection supports rationale flags, not corrected totals or certification of other judgments. External-source truth and billing were not independently verified; rubric10 n=3 remains descriptive and rubric20 repeatability unmeasured.
