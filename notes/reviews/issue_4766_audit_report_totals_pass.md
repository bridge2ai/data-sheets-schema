# Issue #4766: Reconciliation Report Stated Finding Totals Verification Pass

## 1. Overview & Context

Issue #4766 addresses an unmeasured blind spot in the API runner and Launch Gates A6, A7, and A10:
Reconciliation reports frequently state total findings (e.g. "Phase 3 source audit produced 12 findings: 2 high, 4 medium, and 6 low") that were previously never verified against the structured audit artifact (`intermediate/{P}_audit.json`). When the written report narrative contradicted the actual structured audit counts, the run completed silently without triggering `_gate_report` or recording the discrepancy in provenance.

Under Issue #4766:
1. `data_sheets_schema.report_audit_totals` deterministically extracts stated finding totals and per-severity subtotals from reconciliation reports, parsing number words ("twelve", "none") and digits, while rejecting subset counts (e.g. "Six findings were deliberately left as-is").
2. Multiple conflicting total statements within a single report (e.g. header stating 13 findings while body prose states 12 findings) are detected as a `finding_total_contradiction`.
3. The extracted counts are compared against `audit_counts(audit_json)` from structured audit findings.
4. Missing or malformed audits are recorded as `checked: False`, `reason: "missing or malformed audit"`, `status: "not_checked"`.
5. Reports stating no total are recorded as `status: "no_total_stated"` with `stated_total: None` (never as consistent).
6. On the API runner path, mismatches trigger a `_gate_report` contradiction (kind: `finding_total_mismatch` / `finding_total_contradiction` / `finding_severity_mismatch`, record: `report`), causing a one-time `report_regate` with discrepancies explicitly communicated to the LLM.
7. The reading is recorded in provenance under `report_audit_totals` and validated against `d4d_generation_record.yaml`.

---

## 2. Read-Only Pass Over 87 Committed Historical Pairs

A read-only evaluation pass was conducted across all 87 committed audit/report pairs in `data/d4d_concatenated/`.

### Summary Statistics
- **Total pairs evaluated**: 87
- **Reports stating finding totals**: 79 (90.8%)
- **Reports stating no finding total**: 8 (9.2%) (`status: "no_total_stated"`, `stated_total: None`)
- **Pairs where stated totals match structured audit**: 25 (28.7%) (`status: "consistent"`)
- **Pairs where stated totals mismatch structured audit**: 54 (62.1%) (`status: "mismatch"`)

### Mismatch Analysis
1. **Total Count Drift (Audit vs Report Summary)**:
   - In multiple v10g runs, the audit LLM wrote a narrative summary like "Phase 3 source audit produced 12 findings", but the structured JSON `findings` array contained 13 items.
   - The reconciliation report phase copied the summary phrase ("twelve findings") verbatim instead of verifying the count of elements in the structured list.
2. **Severity Classification Mismatch**:
   - Reports frequently reported "none of them high" or "0 high", while the structured audit included 1 high-severity finding that was reclassified or downplayed during prose drafting.
   - Low vs. medium borderline classifications frequently drifted between audit structured records and report prose (e.g. stating 6 low instead of 7 low).
3. **No Total Stated**:
   - 8 reports omitted finding counts entirely in introductory prose and proceeded directly to thematic discussion and dispositions. These are cleanly marked as `status: "no_total_stated"` with zero false-positive contradictions.

---

## 3. Post-Fix Verification & Integration

With the implementation in `report_audit_totals.py` and `api_runner.py`:
- Synthetic v10g shape (13 entries: 2 high, 4 medium, 7 low; audit summary saying 12; report saying "twelve findings" and "six low"): exactly 2 mismatches (total and low severity).
- Conflicting total statements within a single report (13 in header, 12 in body): detected via `finding_total_contradiction`.
- Matching reports (13, 2, 4, 7): 0 mismatches, `status: "consistent"`.
- Malformed audit: `checked: False`, `reason: "missing or malformed audit"`.
- Gate behavior:
  - Reports with matching totals make no extra API calls (`regenerated: False`).
  - Reports with mismatching totals trigger a `report_regate` call with structured discrepancies.
  - Provenance schemas (`d4d_generation_record.yaml`) declare `report_audit_totals` (`range: AnyBlock`), satisfying LinkML closed validation.
