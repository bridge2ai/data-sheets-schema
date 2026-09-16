# Source-review coverage correction — 2026-09-15

The unchanged v10o CHORUS API output reproduced #1815 and #1782. The current
checker tests declared evidence, while the audit can omit retained factual
claims. A quotation matching somewhere in the bundle does not validate its
document attribution, and SOP instructions do not attest their application.

Implement an opt-in renderer 12/evidence protocol v3 for both API and native
generation. Retain the existing quotation and relationship checks. Add a
hash-bound source-review inventory covering every populated scalar of the
original full record during audit and the final full record during reporting.
Each factual value must be fully quoted by reviewed claims. Declare the named
documents, source evidence and operational status for every claim. Reject
missing coverage, unsupported declared attributions, incompatible declared
statuses and final claims still marked for revision. Link audit revision
judgments to actionable findings. Keep metadata exemptions narrow and explicit.
A failed final source review stops the API before schema repair or a report-only
retry and latches resume refusal. Empty, malformed or truncated audit/report
responses are preserved and stop before a usability retry, including reports
regenerated after a legitimate repair. Numeric, boolean and date claims must
quote complete scalar values. Native instructions require the same stop; independent native
acceptance must inspect actual checker tool results and reject continuation
after a failure. An ordinary report correction remains possible only with clean
source reviews and a fresh final inventory.

Use neutral synthetic documents to reproduce wrong-document attribution,
instruction-to-applied inference, lost prospective deployment qualification,
mixed-status prose and omissions in repeated/nested values. Test real API
phase stops/resume refusal and native validation, preserving original bytes.
Protect historical renderer/instrument replay and defaults. Review the whole
change adversarially, file and address findings, run required CI, then merge
and delete the implementation branch.

These checks validate coverage and declared classifications; they cannot
prove semantic entailment or the accuracy of a model's status classification.
Independent source review remains required. Keep #1815/#1782 open for the
unchanged-canary acceptance evidence. No old output is repaired or regraded.

Only after this correction is reviewed and merged, prepare a fresh matched
registration with current code, both-arm controls, unchanged source bundles,
profiles, prompts, schemas, model, output paths and budgets. Account for the
larger audit/report payloads before launch. No paid attempt is included in this
implementation change. The broader plan retains both generation arms and all
evaluation styles in the [dated continuation plan](matched_cborg_continuation_canaries_2026-09-15.md).
