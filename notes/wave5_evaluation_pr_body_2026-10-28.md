Registered evaluation results need consistent provenance and blinding before
comparison. This change connects retained ratings to the comparability audit,
shares identity-aware blinding/leakage checks, keeps the private review key
outside reviewer material, and reports recorded bundle identities without
assuming equivalent source exposure.

The evaluator implements D52's approved contact aliases and excludes exactly
four Q9 regulatory criteria only when regulated_access is explicitly false.
Owner D61 confirms alias scope includes Rubric10 E2.2. Q9 keeps its five-point
maximum and now labels only the criteria measured, avoiding claims that
excluded confidentiality/governance fields were present. These applicability
changes alter scoring conditions; they do not add source coverage or rewrite
historical scores.

The branch preserves published E3x ancestry and composes with #5095 at
cf01eb12bbbbde04854163ecb1036cf9a5431e6e. Target feat/v10-preflight-scripts
initially; retarget main after #5095. Generation assets, rubrics, contexts and
the decision record match that base. Compact original results replace two
redundant inventory tarballs in the publication tree; original archives remain
recoverable from Git and preserved worktrees.

Validation at distinct heads:

- Integration fbbb2c7599c4a4a98ae27242db9b05c90954a020: 588 passed,
  including committed-corpus checks, no failures or skips.
- Label correction f5d00a9fa0cc1eb058f16122d31ed0db560efccd: baseline canary
  fails, fixed same canary passes, then 121 focused tests pass with no skips
  or failures. An earlier invocation with incorrect module names failed
  before pytest; its diagnostic is preserved.
- Source/import checks passed. Actual baseline/fixed JSON has unchanged
  scores, maxima and evidence; only two labels, source-derived instrument
  identity and run metadata differ. Counts across heads are not pooled.

Final instrument:
b38117d96e73987f236d4d3d47da5b84a952401537f9a2ae4d2c44bf981fc064.
See notes/wave5_d52_publication_followup_2026-10-28.md for exact boundaries,
independent read-only review and artifact digests. Claude's D1–D3 findings
have local issue-ready dispositions. D4 is a maintenance nit and D5 a
specification observation outside this correction. Lead review and CI remain.

Historical/v8 #5126 and native E5-direct adapters remain design-only. This PR
does not authorize generation or scoring. Claude's #5164 context/table work
remains a separate dependency.

Refs #5125, #5131, #5132, #5133, #5135, #5136, #5137, #2912, #5121.
