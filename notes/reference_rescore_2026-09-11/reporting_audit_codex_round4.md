# Codex Adversarial Review

Target: branch diff against 2544c2913bb6f4531670cef863392abdbfc65fe1
Verdict: needs-attention

Hold: a receipted timeout can still pass completion with unknown cost. Reviewed 428c54613 matching local origin; fresh public-ref verification was network-blocked.

Findings:
- [medium] [P2] Block completion when terminal cost evidence is missing (scripts/audit_reference_rescore.py:183-186)
  A runner timeout can leave an incomplete receipt and valid JSONL ending between events, without a terminal result. Inventory accepts this evidence, bypassing the unresolved branch. Once 56 ratings are accepted, this gate emits completion_audit.json and the CLI succeeds despite cost_accounting_complete=false. An in-memory accounting reproduction, with score validation stubbed, confirmed this; the same timeout ending mid-JSON correctly blocked completion. Certification therefore depends on where the interrupted stream stops, although cost remains unknown in both cases.
  Recommendation: Classify missing terminal cost evidence as unresolved before certification, and require complete cost accounting before emitting completion. Add interim, completion, and CLI regressions for a timeout ending after a complete JSONL event followed by a successful retry.

Next steps:
- Fix and test this completion path before approval, then perform the planned reporting-only pin amendment and offline revalidation before further ratings.
