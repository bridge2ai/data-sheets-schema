# v10o CHORUS API — source review rejected

The canary completed on 2026-09-15 under reviewed registration #1850. All
request accounting settled and all 41 original files are preserved locally.
No downstream native, Kids First, evaluation or production job was launched.

The final pair passes schema and duplicate-key checks, exact core derivation,
full/core consistency and live provenance. The scoped evidence-assertions v2
check passes 64 declared assertions; report-claims v8 passes 16 claims and 14
disposition rows. These passes do not establish complete source support.

Independent review of all four frozen source documents, original and final
records, audit, report and receipt rejects the pair:

- `is_deidentified.deidentification_details` attributes a patient-focused
  ethical/legal/privacy/bias clause to NIH, although that clause belongs to
  the historical GitHub overview. It survives in full and core (#1815).
- `acquisition_methods[1].acquisition_details` asserts that sites followed SOPs.
  Instructions and requests for progress reports do not establish adherence
  in the released data. The audit and report incorrectly endorse that
  inference (#1782).
- The repository inventory in `notes` drops the source's prospective deployment
  qualification when describing applications supporting Azure services. This
  does not establish whether deployment occurred (#1782).
- A receipt quotes the wrong program start date. Receiptsv3 reports 130 of 131
  snippet parts verified. The existing strict floor reports one unverified
  snippet, but the experimental controllers did not enforce it (#1854).

The receipt's `findings_gated: 0` avoids double-counting; it does **not** mean
that the historical strict gate accepts the mismatch. Controller enforcement
is being corrected without changing that instrument. Source acceptance still
requires independent review after this mechanical fix.

The seven audit findings comprise two moderate and five low findings; its
summary is a nonempty string. The report correctly distinguishes the original
core header from the final reconciliation marker. No unsupported maintainer
or committee-contact role from #1801 appears, but no overall acceptance is
issued and the source criteria remain binding. A separate ambiguity about
published-metadata table column ownership was not needed for rejection.

Scientific identities:

- Launch: `a762283e7dda9deca859c7bc05c9073ff414fa0a`.
- Registration: `4d2f88dc4766805e73b55552e849938bb97857c83d90596a120caea304274f7c`.
- Full: `69a87d42c7eecf03e71dc59fa00794288c42e74d20e8070855f75e0fd7c22ae6`.
- Core: `a55d6b8bc573db5aecc94e0ede3ac321f5b464ae1c859d3b9109f41f7e8c4df1`.
- Receipt: `9e9586362e84dd15ad5f057ffe7b6eeb03bc8246c846fc08bf4ed64386f2ab2b`.
- Source bundle: `27625709112a7b7796f4e778fcc33df9f908ba95e47dbc0b6e23a535cacc237c`.

The originals, source-review record, mechanical recomputation and complete
accounting remain local. They were neither repaired nor overwritten. The
provider-context control in #1852 is separate and does not change this frozen
attempt or explain the earlier interrupted streams (#1849). This review is
not a numeric rubric rating or a repeatability measurement. See the
[dated continuation plan](../matched_cborg_continuation_canaries_2026-09-15.md)
and [tracking issue #1763](https://github.com/bridge2ai/data-sheets-schema/issues/1763).
