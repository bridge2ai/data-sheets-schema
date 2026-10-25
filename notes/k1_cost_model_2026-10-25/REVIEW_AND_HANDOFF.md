# K1 review and handoff — 2026-10-25

K1 analysis is complete, with unresolved scientific/proxy and launch constraints
kept explicit. No provider, token-count, GitHub or push operation occurred.
The final note is `final/k1_cost_model_2026-10-25.md`; its JSON is
`final/cost_model.json`. The orchestrator-facing copy is
`d4d-executions/plans/k1_cost_model_2026-10-25.md`.

Two independent read-only reviewers examined the ledger joins, pricing,
calibration, planning search, context handling, model and final artifacts.
Their final verdicts were clear with the limitations stated in the note.
Twenty-one focused regressions pass: 8 ledger, 4 planning, 9 cost-model tests.
The final regression proves the legacy KIDS_FIRST proxy cannot fill an
unrelated project's missing stage or alter actual-context unknown totals.

## Findings for AGY's issue ledger

Only AGY files issues. These findings were addressed locally before this handoff;
no issue is claimed filed or closed here. Existing #5150 already tracks the
recovered harness's registration-builder dependency.

| Finding | Resolution / evidence |
|---|---|
| Duplicate, missing or wrong-phase usage-ID joins could misattribute request calibration | Explicit one-to-one phase/ID validation and causal rejection tests |
| Duplicate abandoned usage could overcount costs | Duplicate rejection and regression |
| Historical 25k worker truncation could be mistaken for ordinary retry behavior | Separate paid-truncation classification; excluded from successful-output fit |
| Module origin alone did not establish resource identity | Exact resource-root checks and source/registration input pins; source tree checked against A16 |
| Recovered A1 synthesized an obsolete KIDS_FIRST context | Separate exact-context rerun retained; it exposes an AI_READI-proxy vocabulary mismatch, not an established production defect |
| Target-scenario normalization canceled new fixed prompt bytes | Historical token/byte fit applied to current non-placeholder payloads; doubling-byte causal test |
| Carry transfer could shrink mandatory fixed input | Floor at current estimated non-placeholder input, explicitly reported and tested |
| A retry envelope silently omitted missing optional stages | Missing stages now yield UNKNOWN; regression |
| Context verdict table omitted the input estimate actually used | Chosen cap-input estimate and 1M clearance shown per request |
| Conditional proxy costs could conceal unknown actual costs | Actual and draft-context arms remain separate; actual totals UNKNOWN; conditional substitution tested |

## Reproduction

Use the repository's existing interpreter and set `PYTHONPATH` to this checkout's
`src` and repository root. All helper scripts are committed under `scripts/adhoc/`.
The copied `scripts/offline_sizing.py` and module are byte-identical to `4c52b8e6f`.
The runtime, builder, prompts, contexts and source bundles remain identical to
`56c41163f`. Primary sizing used the helper version committed in `41b90911c`;
later metadata guards and the explicit Kids/crate wrappers are in `899b1a189`.

```sh
python scripts/adhoc/k1_calibrate_ledgers_20261025.py --launch-base /path/to/launch-base --out /new/evidence
python scripts/adhoc/k1_size_requests_20261025.py --root /path/to/checkout --historical-root /path/to/launch-base --workdir /path/to/checkout/notes/k1-new/primary --out /path/to/checkout/notes/k1-new/request-sizing-primary.json
python scripts/adhoc/k1_plan_sensitivity_20261025.py --root /path/to/checkout --historical-root /path/to/launch-base --out /new/plan-sensitivity.json
python scripts/adhoc/k1_size_kids_context_20261025.py --root /path/to/checkout --workdir /path/to/checkout/notes/k1-new/kids --out /new/request-sizing-kids-current-context.json
python scripts/adhoc/k1_size_crate_proxy_20261025.py --root /path/to/checkout --historical-root /path/to/launch-base --workdir /path/to/checkout/notes/k1-new/crate --out /new/request-sizing-crate-proxy.json
python scripts/adhoc/k1_build_cost_report_20261025.py --sizing notes/k1_cost_model_2026-10-25/request-sizing-primary.json --supplement notes/k1_cost_model_2026-10-25/request-sizing-kids-current-context.json --supplement notes/k1_cost_model_2026-10-25/request-sizing-crate-proxy.json --ledger notes/k1_cost_model_2026-10-25/ledger_calibration.json --planning notes/k1_cost_model_2026-10-25/plan-sensitivity.json --out /new/final
python -m pytest -q tests/test_k1_calibrate_ledgers_20261025.py tests/test_k1_size_requests_20261025.py tests/test_k1_cost_report_20261025.py
```

Scratch registration files and record copies remain local, outside the committed
artifact roster. They are synthetic sizing inputs, not launch registrations.
The partial checkpoint and earlier model draft are retained as local history.
No cleanup of other worktrees or evidence was performed.

## Unresolved implications

The selected minimal-root partition point costs $651.01 for the 15 priced runs,
plus $10.13 extrapolated ordinary partial usage, before actual-context KIDS_FIRST
and evaluation. The old-context KIDS_FIRST proxy gives an explicitly conditional
16-run total of $708.00 plus $10.95; it does not resolve the actual-context gap.
Conditional with-crate CHORUS ×4 adds $247.33 plus $3.30 on its disclosed proxy.
These are neither minimum achievable costs nor launch-cleared configurations.
Four-worker planning alternatives are listed but not priced; C7/A17 can alter
this tradeoff. Several cap-carry requests exceed 1M and several typed sequences
exceed the current 4M aggregate allowance. No budget allocation was changed.
