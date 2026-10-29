# A12 integration and partition-write refusal fix (#5231)

The isolated branch `codex/wave4-a12-fixes-20261028` integrates the reviewed #5095 preparation fixes into #5154 and fixes its remaining direct-library draft-write defect. **195 tests passed, zero failures or skips**, at frozen source `07a74d1bdc7b64784a1b0ef840293de67f4c1fdb`. This is offline engineering evidence, not scientific acceptance or permission to launch.

## Source and implementation

- A12 base: `f58482df84276b3509893455f753f6af068fb321`.
- Reviewed #5095 code follow-up: `5412e9ed3142f7c6ed7bdb334e8a59dddf783fb5`.
- Local merge preserving both ancestors: `0404369027e9235618c3a8952e4d13d76d73e743`.
- Production fix: `c4d1cbbb56bfc3f191e447eff5aee514fd705276`.
- Final tested source, including four later-error fixture adjustments: `07a74d1bdc7b64784a1b0ef840293de67f4c1fdb`.

The only merge conflict was the assistant README cap description. Its resolution preserves explicit shared-generation-1 128k full/reconcile/report-family caps and the A12 report-family aliases and 96k historical baseline. No protected prompt, canonical hash, shared-generation implementation, run directory or ATTIC path changed against the A12 base.

The source fix moves `resolve_audit_limits` immediately after arm validation, before manifest resolution and any draft context synthesis. The same partition checks and values apply; they now reject missing bounds, unknown profiles and inconsistent aggregate allowances before preparation writes. This does not claim that every later registration validation is transactional.

The merged tests select explicit A12 partitions. CHORUS uses `partition="chorus"`; other project fixture cases state mechanics-only bounds. Assertions for schema closures, routing artifacts, selected-worktree authority, context precedence and launcher behavior are retained. Four pre-existing error cases now supply valid bounds so they still reach the intended later file/path error.

## Causal and integrated evidence

All three runs used committed clean source, the repository's `scripts/adhoc/validate_wave3_20261027.py`, a physical Python 3.13 venv, disabled site initialization/plugin autoload, imported-origin checks, Python network/command refusal hooks, and before/after source attestation. The helper explicitly does not claim isolation of arbitrary child binaries or dependency-byte attestation. No provider calls or live binaries were invoked.

| Run | Frozen commit | Result | Source unchanged | Driver seconds |
|---|---|---|---|---:|
| Causal reproduction | `0404369027e9235618c3a8952e4d13d76d73e743` | 28 passed, 3 expected failures | yes | 52.50 |
| First integration | `c4d1cbbb56bfc3f191e447eff5aee514fd705276` | 194 passed, 1 fixture failure | yes | 67.61 |
| Final integration | `07a74d1bdc7b64784a1b0ef840293de67f4c1fdb` | 195 passed, 0 failures, 0 skips | yes | 62.53 |

The three causal failures assert absence of the requested output directory after direct-builder refusal for missing partition, unknown profile and inconsistent aggregate output. All three created a draft on the pre-fix source. The valid-partition positive control published its requested draft and registration. After the ordering fix all four pass. The first integration's sole failure was `test_build_registration_error_cases`, which omitted partition bounds while expecting a later missing-bundle error; its four relevant calls were adjusted without changing production validation.

Final passing case counts:

| Module | Passed |
|---|---:|
| `test_build_api_registrations` | 20 |
| `test_build_draft_contexts` | 9 |
| `test_preflight_resource_authority` | 31 |
| `test_wave4_5095_review` | 5 |
| `test_api_launcher` | 54 |
| `test_api_dollar_readout` | 37 |
| `test_dc_output_caps` | 18 |
| `test_arm_confounds` | 21 |

The final command was:

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B scripts/adhoc/validate_wave3_20261027.py \
  --output /private/tmp/d4d-wave4-a12-final-r2-validation-20261028 \
  --expect-head 07a74d1bdc7b64784a1b0ef840293de67f4c1fdb \
  --base f58482df84276b3509893455f753f6af068fb321 \
  --module test_build_api_registrations --module test_build_draft_contexts \
  --module test_preflight_resource_authority --module test_wave4_5095_review \
  --module test_api_launcher --module test_api_dollar_readout \
  --module test_dc_output_caps --module test_arm_confounds
```

## Preserved artifacts

All original directories remain intact:

1. `/private/tmp/d4d-wave4-a12-partition-causal-20261028`
2. `/private/tmp/d4d-wave4-a12-final-validation-20261028`
3. `/private/tmp/d4d-wave4-a12-final-r2-validation-20261028`

The existing repository helper `scripts/adhoc/archive_n2_restack_validation_20261027.py` archived all selected top-level JSON/log/XML files from these three completed runs to `notes/wave4_a12_validation_2026-10-28/`, verifying exact bytes and file modes on round trip. Synthetic case directories remain external and are explicitly excluded. Prior failures are preserved, not recast as successes.

| Artifact | SHA-256 |
|---|---|
| Archive manifest | `ccde7d262c5deae580f2fb7bae67f37fc7930e02efb57d714c9e668f7c99554d` |
| Causal outcome | `1905eea8ac6b532d682cc1d59c29939ab6b415900ec8e64c2063ffa256cf13f1` |
| First integration outcome | `ff516d4cdb41ecaaa4b92bef88bf6f1a9401c0d0374baf7be0d9c4e20f0079f1` |
| Final integration outcome | `db1d3a2f0ed8eee5746b6a82d2ecc2ba8005baa54625d0c0d480ae130df5b1a4` |
| `run-01.tar.gz` | `cf06b866a77412fbf6eba5988dcb93855f1aa95d37ab68e1cc1e678cb9401dae` |
| `run-02.tar.gz` | `acfc72b93e78dc6b789a4935e0c98b85e01bac3e827e1f89b8f4e45b92e7166d` |
| `run-03.tar.gz` | `f5d9bdc55520ab6aa4e6341b738e6bfdc4ec5f67ba0495568d9556a07b83a401` |

Independent root review approved the narrow production ordering change. Root owns issue #5231 and all publication/merge actions. This worker made no GitHub writes, pushes, provider calls or edits to owner worktrees. The branch retains a separate static A12/A13 report; A13 itself has not been tested or modified by this integration.
