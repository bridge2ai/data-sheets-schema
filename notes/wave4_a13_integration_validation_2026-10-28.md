# A13 / #5158 integration verification, 2026-10-28

**384 passed, 0 failed, 0 skipped**, with source unchanged and imported-origin checks complete. The local branch is `codex/wave4-a13-integration-20261028`. This verifies the reviewed A13 receipt-floor implementation composed with the A12/preflight fixes; it does not approve generation, scoring, or a scientific condition.

## Exact composition

- A13 base: `148c869dde865915221db847b2e89f15f319b365`.
- Validated A12 parent: `d68cb8e0cb3f47af9d538a2cd6ac4593a2fda74c`.
- Conflict-free local merge and tested source: `907b5b6545dcca06e16f89e4d2cb0550d5432d35`, with those two exact parents.
- Worktree: `/private/tmp/d4d-codex-wave4-a13-integration-20261028`.

No new production fix was needed. The five A13 receipt implementation files (`receipt_completion.py`, `receipt_completion_policy.py`, `receipts.py`, `rereceipt.py`, and `cli/receipts.py`) are byte-identical to the A13 base. The builder retains explicit-worktree resource authority, complete schema/routing pin checks and the A12 early partition validation fix. Relative to A12, its production changes are A13's floor-basis parsing, defaults and CLI forwarding.

The merge changed no protected prompt, shared-generation implementation, canonical-hash file, existing run directory or ATTIC file against A13. Original history was preserved; no squash, rebase, push, GitHub write or owner-worktree change occurred. The final evidence commit adds notes/archive files only after the tested merge.

## Review disposition

The existing A12/A13 reviews were checked against the composed code, including the original A13 F1 counterexamples and the D37 saved-result correction. D37 gates the phase-1 snapshot's own coverage, with final-record counters retained alongside it. Missing snapshot counters and zero eligible leaves do not pass. Basis-less floors retain their prior calculation and result shape. Receipt coverage continues to be separate from semantic support and final-record completeness.

The saved-result compatibility projection removes only jointly absent envelope fields and jointly absent snapshot-counter pairs in both saved blocks. Supplied, partial, or changed fields still compare against recomputation. The archived canary results are returned as saved, without rewriting their pinned bytes. Existing tests exercise both saved CHORUS fixtures and forged/partial counter, receipt and metadata mutations.

An independent agent reviewed the merge read-only: the builder changes relative to A12 were confined to floor-basis parsing/default/forwarding; resource decorators, early partition validation and schema/routing pin checks remained unchanged. That review found no integration regression. The focused tests below supply the execution evidence; prior historical test-count claims were not substituted for a fresh run.

## Focused offline validation

The repository helper `scripts/adhoc/validate_wave3_20261027.py` ran a clean committed source with a physical Python 3.13 venv, disabled site initialization/plugin autoload, removed credential environment names, checked import origins and before/after source, and installed Python network/command refusal hooks. It does not attest all installed dependency bytes or claim arbitrary child-binary isolation. No provider calls or live model binaries were invoked.

| Module | Passed |
|---|---:|
| `test_receipt_floor_basis` | 67 |
| `test_receipt_completion_policy` | 67 |
| `test_receipt_completion_runtime` | 85 |
| `test_rereceipt_completion` | 69 |
| `test_shared_generation_selection` | 39 |
| `test_build_api_registrations` | 21 |
| `test_preflight_resource_authority` | 31 |
| `test_wave4_5095_review` | 5 |
| **Total** | **384** |

Exit status was 0; source was unchanged; there were no invalid JUnit cases or skipped cases. Pytest took 527.17 seconds and the complete driver took 567.01 seconds. Twelve warnings came from the installed LinkML Pydantic generator's deprecated instance access to `model_fields`. Timing is descriptive for this run, not idle-host recorder or comparative performance evidence.

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B scripts/adhoc/validate_wave3_20261027.py \
  --output /private/tmp/d4d-wave4-a13-validation-20261028 \
  --expect-head 907b5b6545dcca06e16f89e4d2cb0550d5432d35 \
  --base 148c869dde865915221db847b2e89f15f319b365 \
  --module test_receipt_floor_basis --module test_receipt_completion_policy \
  --module test_receipt_completion_runtime --module test_rereceipt_completion \
  --module test_shared_generation_selection --module test_build_api_registrations \
  --module test_preflight_resource_authority --module test_wave4_5095_review
```

## Evidence and handoff

Original evidence remains at `/private/tmp/d4d-wave4-a13-validation-20261028`. The existing `scripts/adhoc/archive_n2_restack_validation_20261027.py` preserved the selected top-level JSON/log/XML results in `notes/wave4_a13_validation_2026-10-28/`, with exact bytes and file modes verified by archive round trip. Synthetic case directories remain external and are explicitly excluded. Both helper scripts are committed in the branch's inherited history.

| Artifact | SHA-256 |
|---|---|
| Outcome JSON | `350d2697e360920edc0d7f77732c59b79a52a40896228cdf746e0ca990d709ea` |
| Archive manifest | `4c05d77eacf3c074e711eef8e247401123cf3c9380f418ccdfafcb4e2e86fd29` |
| Result archive | `9755653e6ff984d75379f61ecc66f24e8cac22afeae882050d30ad3727b74805` |

No new issue was found by this bounded review and integration run. Claude remains lead for publication and remaining stack integration; this branch stays local. Later composition with A17, BC1, v5 receipts or native changes requires its own applicable integration checks. Human scientific review, P4 and launch decisions remain separate. Work stops after this evidence packet; no optional tests or additional branches are started.
