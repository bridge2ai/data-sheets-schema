# P2 / #5163 R6 remediation — Wave 3

Completed offline 2026-10-28 UTC / 2026-10-27 PDT. Branch
`codex/p2-r6-fix-20261027`, base `705ac83ded6630722e1fbebc4cb7930e4cafde00`.
Analysis-plan amendment commit: **`88d74731fc858f7c7bcfd3988cc8266c620f2b05`**.
Plan: `notes/generic_v10_analysis_plan.md`, SHA-256
**`3596a88ac5f2c5b045634d7443399e820ab702eaaf20bf503fdb456e77c07339`**.

All six requested findings are addressed in the draft, rather than treated as
approval of the experiment:

| Finding | Disposition |
| --- | --- |
| R6-F1 | Replaced obsolete current-condition advice with D28/D37/D39/D44/D45/D49 and BC1: stage exposure, retained versus omitted review rows, exact known asset/code identities, token versus byte bounds, actual call schedule, and required controller-only wire checks. Historical 4k/G5/96k calculations remain labelled historical. |
| R6-F2 | Added the six-project × API/native matrix. Native CHORUS n=1 is descriptive feasibility only; other native cells are unplanned/unregistered. Declared H1/H3/H6/H7 scientific/procedural differences and scoped `d4d api batch` to API launches. |
| R6-F3 | Defined original record, pre-turn/effective/final receipts and final record separately; v4 D37 is the primary snapshot gate, v5 shadow/explicit opt-in. Pre-completion, at-receipt, final and completion-gain ratios keep separate numerators/denominators/identities. Retirement cannot count as improved source coverage. |
| R6-F4 | Reconciled D26–D49 and disclosed 10-20a/10-22a as observed assisted/invalid engineering evidence excluded from clean acceptance, confirmatory effects and both parts of clean automatic-success rates. Preserved costs/attempts separately and pending owner decisions. |
| R6-F5 | Proposed exact atomic-claim and eligible-leaf units, splitting/dedup/exclusion rules, complete adjudication, missing/zero-denominator handling, claim/leaf-weighted pools, project-specific rates and equal-project-weight sensitivity. AI_READI's cross-arm label and separate three-project pool remain explicit; original zero-tolerance direction is unchanged. D24/P4 must adopt the annotation protocol. |
| R6-F6 | n=3 is the primary structure estimand; n=2 is a flagged sensitivity with common registered indices where possible, per-arm n and cell IDs; fewer than two is not computable. |

Independent read-only review found the six findings substantively addressed. It
caught a remaining #5126 citation mislabel, corrected before commit: #5126 concerns
the historical-v8 rating authority route, the native rating adapter is separate,
and the atomic-claim protocol belongs to D24/P4. Root checked that correction and
the final document. `git diff --check` passed. **No pytest was run or claimed for
this prose-only amendment.** No production, protected, run-directory or archive
file was changed, and no helper script was needed.

Authority checks used cached Git only: D26–D49 decision record at
`a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5`, native D38 at
`be0bd05821256212e89e4d011ba6b30a780e299b`, BC1 at
`3bd3c41f459b31848aee2f57e26deb86ef786970`, and receipt fixes at
`aff4c9ca530a94b84f934698cdc791960cc31713`. The two D38 scientific asset hashes
in the plan were recomputed from their cached Git bytes and match.

Important unresolved implementation/registration boundary: the requested design
label `shared-generation-api-v2-bc1` differs from current shared-generation-1/API25
with `bounded_carry_version=1`. D28's integration cap is 32k, whereas BC1 currently
requires 64k for each integration. Protected hooks remain unapplied; native BC1 is
unsupported; final composition, D42 guard choice, six-project sizing, exact wire
identity and current budget still precede registration. This draft exposes those
differences and does not silently approve them. D02/D04 and other owner choices,
P3 review, P4 ratification and launch/evaluation words remain required.

No network, provider call, live binary, GitHub action, push or merge occurred.
