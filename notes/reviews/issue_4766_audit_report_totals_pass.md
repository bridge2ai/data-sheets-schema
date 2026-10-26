# Issue #4766: Reconciliation Report Stated Finding Totals Verification Pass

## 1. Overview & Context

Issue #4766 addresses an unmeasured blind spot in the API runner and Launch Gates A6, A7, and A10:
Reconciliation reports frequently state total findings (e.g. "Phase 3 source audit produced 12 findings: 2 high, 4 medium, and 6 low") that were previously never verified against the structured audit artifact (`intermediate/{P}_audit.json`). When the written report narrative contradicted the actual structured audit counts, the run completed silently without triggering `_gate_report` or recording the discrepancy in provenance.

Under Issue #4766:
1. `data_sheets_schema.report_audit_totals` deterministically extracts stated finding totals and per-severity subtotals from reconciliation reports, parsing number words ("twelve", "zero") and digits (and zero-severity phrases like "no high" / "none of them high"), while rejecting subset counts (e.g. "Six findings were deliberately left as-is", "Three findings were raised for the record without recommending change") and combined severity buckets ("2 high/medium-severity", "21 medium and low", "2 high-severity pairs").
2. Multiple conflicting total statements within a single report (e.g. header stating 13 findings while body prose states 12 findings) are detected as a `finding_total_contradiction`.
3. The extracted counts are compared against `audit_counts(audit_json)` from structured audit findings, including per-severity subtotals even when no overall finding total is stated.
4. Missing or malformed audits are recorded as `checked: False`, `status: "not_checked"`, with the specific reason (`"missing audit"`, `"malformed audit JSON"`, or the exact `_audit_shape_problem(parsed)` diagnostic).
5. Reports stating no total and no mismatching severity subtotals are recorded as `status: "no_total_stated"` with `stated_total: None` (never as consistent).
6. On the API runner path, mismatches trigger a `_gate_report` contradiction (kind: `finding_total_mismatch` / `finding_total_contradiction` / `finding_severity_mismatch`, record: `report`), causing a one-time `report_regate` with discrepancies explicitly communicated to the LLM (`findings_include_report_audit_totals: True`), and rolling back any rewrite that increases core `report_claims` / `evidence_assertions` contradictions even if total findings decrease.
7. The reading is recorded in provenance under `report_audit_totals` and validated against `d4d_generation_record.yaml`.

---

## 2. Read-Only Pass Over 87 Committed Historical Pairs

A read-only evaluation pass was conducted across all 87 committed audit/report pairs in `data/d4d_concatenated/`.

### Summary Statistics
- **Total pairs evaluated**: 87
- **Reports stating finding totals**: 79 (90.8%)
- **Reports stating no finding total**: 8 (9.2%) (`status: "no_total_stated"`, `stated_total: None`)
- **Pairs where stated totals match structured audit**: 26 (29.9%) (`status: "consistent"`)
- **Pairs where stated totals mismatch structured audit**: 53 (60.9%) (`status: "mismatch"`)

### Mismatch Analysis
1. **Total Count Drift (Audit vs Report Summary)**:
   - Across the 87 committed pairs in `data/d4d_concatenated/` (which span `generic-v3-schema2`, `api-generic`, `api-generic-v4`, and `v6`–`v9`; none of the 87 committed pairs is from `v10g`), 45 `finding_total_mismatch` findings occur where the reconciliation report states a finding total that differs from `len(audit["findings"])` (for example, `2026-08-13_claude-opus-5-api-generic-v4_rep1` CM4AI states 24 findings against 37 structured audit entries). In the separate `v10g` observation that motivated #4766, the audit narrative summary stated 12 findings while the structured JSON `findings` array contained 13 items, and the reconciliation report copied "twelve findings" verbatim.
2. **Severity Classification Mismatch**:
   - Across the 87 committed pairs, 72 `finding_severity_mismatch` findings occur across high, medium, and low subtotals. None of the 87 committed pairs states `0 high` or `none of them high` against a computed `high >= 1`; rather, high-severity mismatches in the 87 committed pairs are non-zero count differences (e.g. stating 3 high vs computed 4 high in `2026-08-13_claude-opus-5-api-generic-v4_rep1` CM4AI, or 2 high vs computed 3 high in `2026-08-13_claude-opus-5-api-generic-v4_rep3` AI_READI), alongside medium and low borderline count drift.
3. **No Total Stated**:
   - 8 reports omitted finding counts entirely in introductory prose and proceeded directly to thematic discussion and dispositions. These are cleanly marked as `status: "no_total_stated"` with zero false-positive contradictions.

### False-Positive Review (`INSTRUMENT_VERSION = 2`)
- **Historical corpus shapes guarded**:
  1. Subset disposition sentences (`"Six findings were deliberately left as-is"`, `"Fourteen findings produced edits..."`, `"Three findings were raised for the record without recommending change"`).
  2. Numbered markdown section headings (`"### 2.1 High severity"`, `"## 6. Additional changes not driven by audit findings"`).
  3. Combined severity buckets (`"2 high/medium-severity structural"`, `"21 medium and low"`).
  4. Non-finding count nouns (`"2 high-severity pairs"`).
  5. Earlier subset mentions before a summary count (`VOICE 08-20b rep3` line 12 summary total `30 findings: 3 high, 15 medium, 12 low`).
- **R4 F9 prose and mid-sentence subset guards (`INSTRUMENT_VERSION = 2`)**:
  1. Ordinary prose containing `"major"` or `"minor"` in reports stating no total (`"No major restructuring of the record was needed"`, `"corrected two major structural defects"`) is not read as a severity count: `major` and `minor` match only directly before `finding(s)` or `severity`, and when no overall total is stated, severity subtotals are extracted only from a single sentence/line stating two or more per-severity counts together.
  2. Mid-sentence parenthetical subset lists before the summary (`"Deferred items (3 findings: 2 medium, 1 low) ..."` before `"The structured audit has 13 findings: 2 high, 4 medium, 7 low."`) do not match as overall total statements because Pattern 7 (`N findings: ...`) is anchored to sentence/line start or explicit count phrasing.

---

## 3. Post-Fix Verification & Integration

With the implementation in `report_audit_totals.py` and `api_runner.py`:
- Synthetic v10g shape (13 entries: 2 high, 4 medium, 7 low; audit summary saying 12; report saying "twelve findings" and "six low"): exactly 2 mismatches (total and low severity).
- Conflicting total statements within a single report (13 in header, 12 in body): detected via `finding_total_contradiction`.
- Matching reports (13, 2, 4, 7): 0 mismatches, `status: "consistent"`.
- Malformed audit: `checked: False`, `reason` naming the specific failure (`"missing audit"`, `"malformed audit JSON"`, or `_audit_shape_problem(parsed)`).
- Gate behavior:
  - Reports with matching totals make no extra API calls (`regenerated: False`).
  - Reports with mismatching totals trigger a `report_regate` call with structured discrepancies.
  - Provenance schemas (`d4d_generation_record.yaml`) declare `report_audit_totals` (`range: AnyBlock`), satisfying LinkML closed validation.
