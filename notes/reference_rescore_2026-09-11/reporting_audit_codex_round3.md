# Codex Adversarial Review

Target: branch diff against 2544c2913bb6f4531670cef863392abdbfc65fe1
Verdict: needs-attention

Hold d145dc4aa for one reproduced P2: torn receipts still prevent interim accounting after a successful retry.

Findings:
- [medium] [P2] Preserve malformed-receipt handling through receipt selection (scripts/audit_reference_rescore.py:127)
  If an interrupted receipt write leaves invalid JSON and a retry succeeds, inventory correctly marks the interrupted attempt unresolved. This call then invokes successful_receipt(), which unconditionally reparses every receipt at reference_rescore.py:355 and raises JSONDecodeError. No interim accounting report is returned. Reproduced with synthetic data and nonempty preservation records. The added tests exercise inventory and complete=True, missing this failing complete=False path.
  Recommendation: Make downstream receipt selection, including canary validation, tolerate malformed receipts while retaining unresolved accounting and successful-receipt uniqueness checks. Add an audit_results(complete=False) regression with a torn receipt and successful retry; keep completion blocked.

Next steps:
- Fix the interim reporting path and rerun focused offline tests before the planned pin amendment and revalidation.
