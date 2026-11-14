# U4 preparation (#4354), 2026-11-08: inspect persisted canary proof limits.
# Input: verified-output.json from the genuine saved-probe canary.
# Output: selected decisions, verification scope and checked trace count.
{
  effort,
  selected_receipt_instrument,
  verification_scope,
  checked: .result.checked,
  passed: .result.passed,
  traces: (.result.traces | length)
}
