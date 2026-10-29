# Wave 5 E3x and D52 evaluation integration

2026-10-28. Refs #5125, #5131, #5132, #5133, #5135, #5136, #5137,
#2912 and #5121. Prepared for Claude's lead coordination and AGY's publication.

The composed evaluation packet passes **588 tests, with no failures, errors,
skips or deselections**, including the committed-corpus comparison. No new
production repair was made for this composition. This is offline software
validation, not unconditional merge readiness, generation/scoring authorization
or scientific acceptance. The later independent review constraints below remain
for the lead to settle before publication.

## Independent D52 review: publication constraints

Claude independently reviewed the exact D52 delivery
`4cd8f2a5191d7cb58d7bf639603a820d38e825d5` in
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/reviews/pr5096_b0978d6e6_d52_4cd8f2a51_claude_review_2026-10-28.md`.
The evaluation implementation in this composition is byte-identical to that
reviewed D52/E3x source. Record the following dispositions before publication:

- **D1, minor defect:** when the four regulated-access criteria are excluded,
  Q9's existing top-band `score_label` still describes confidentiality and
  governance content that was not required. The separate applicability note
  explains the omission but does not correct the label. The lead must direct
  its repair or explicitly record its deferral; the 588 passing tests do not
  establish that this label is accurate.
- **D2, scope decision:** the bare Rubric10 E2.2 criterion also accepts the
  nested contacts. A governance-only record can therefore gain E2.2 credit.
  The lead/owner must confirm that this legacy-criterion extension is intended;
  the existing implementation and tests are not that confirmation.
- **D3, publication disposition:** the branch inherits approximately 3 MB of
  D52 inventory tarballs under `notes/d52_scoring_validation_2026-10-28/`.
  The new Wave 5 results are compact, but that does not remove the inherited
  publication concern. The lead must choose how to publish/preserve that
  evidence. No historical evidence was removed and no ancestry was rewritten.

**D4 is an optional maintainability nit:** the rule keys on numeric question
ID 9 and literal paths, so a future rubric revision could bypass it. **D5 is
an optional owner/specification observation, not an implementation defect:**
the parent `regulatory_restrictions` object still counts among the three base
criteria, as specified, including when its content consists of excluded
subfields. Neither observation authorizes a scoring-rule change here.

This post-validation amendment changes only this report and the draft PR
description. The tested source remains
`fbbb2c7599c4a4a98ae27242db9b05c90954a020`; the 588-test result is unchanged and
no tests were rerun. Recording these findings does not adopt all of the
reviewer's recommendations or resolve D1–D3.

## Publication route and exact ancestry

Use a dedicated evaluation PR with the existing published E3x branch as its
head, after AGY fast-forwards that branch to this tested delivery. Initially
target `feat/v10-preflight-scripts`; retarget to `main` after #5095 lands.
Claude/AGY should check whether that head already has an evaluation PR before
creating one. The cached coordination and merge-packet inventory identifies
the branch and issues but supplies no dedicated PR number. No GitHub lookup,
push, merge to main, or remote write was performed here.

| Role | Exact commit |
| --- | --- |
| Published E3x head | `d6eed9274145a7999b96622957ba1f95167c7ef4` |
| Prior reviewed local restack | `2bbb0dfff934efde670ae342ddef7c875d39cd03` |
| D52 delivery / first parent | `4cd8f2a5191d7cb58d7bf639603a820d38e825d5` |
| Cached #5095 target / second parent | `cf01eb12bbbbde04854163ecb1036cf9a5431e6e` |
| Common ancestor | `a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5` |
| Conflict-free integration merge | `6af87fea2ecaf97efd9e339fb3dbee7a6fca0ef3` |
| Frozen tested head, adds compact preservation helper | `fbbb2c7599c4a4a98ae27242db9b05c90954a020` |

Local branch: `codex/wave5-evaluation-integration-20261028`.
Worktree: `/private/tmp/d4d-codex-wave5-evaluation-20261028`.
The new branch starts at the D52 delivery and merges the exact #5095 target
with `--no-ff`. Both original ancestries remain. There were **zero conflicts**
and no resolution hunks. The published E3x head remains an ancestor, so the
proposed later publication is a fast-forward, subject to rechecking the remote
head. Do not squash or rebase this stack integration.

The disputed local-main head `384993879` and the related scoring commits
`fa9cc2149f80c2ea2f9520d10e4df54900e7fd00`,
`67e0650f424b050940840d79a040bb4d354bf94d` and
`40c00eb33be0216fe4eb4d255149c66d8a206e42` are not ancestors of the delivered
D52 branch. No work was copied from that stack. Original and excluded owner
worktrees were not edited.

## Scope and preservation

The evaluation delta relative to #5095 contains the reviewed E3x registered
evaluation provenance audit, common identity-aware blinding, external private
key handling, short-token leakage checks and cross-arm recorded bundle-identity
comparison, plus the approved D52 deterministic evaluator rules. It changes
four installed evaluation modules and their three CLI/audit scripts, five
test modules, and retained helper/evidence notes. The existing dated reports
remain historical records rather than new acceptance claims.

The merge preserves #5095's builder, launcher and procedure-fact repairs.
Protected generation code, all prompt/schema/context/omission/rubric/agent
assets, the decision record, run directories and `data/ATTIC/` remain byte-exact
to the selected #5095 target. The current decision document SHA-256 is
`d702aa27427acf20ff942a3b1b891206f4e995c4c8949ffe7eea44868ff5e61b`.
There are no new decision or context edits in this packet; Claude's #5164
context/table work remains separate.

D52 treats the two approved nested governance-contact paths as one criterion,
retains actual evidence pointers and member isolation, and excludes exactly
four Q9 regulatory subfields only for explicit `regulated_access: false`.
Q9 remains applicable with maximum 5. Its field denominator changes from 7 to
3, with the four omitted paths explained in `applicability_evidence`; this is
a scoring-condition change, not improved source coverage. No historical scores
were rewritten.

## Actual validation

One frozen nine-module run completed with exit 0. Source inventories are
unchanged before/after; project, test and package import-origin checks passed.
Pytest time: **710.11 seconds**. Driver time: **719.631968292 seconds**.
The shared host was running other jobs; these times are not a benchmark.

| Module | Passed |
| --- | ---: |
| `tests/test_arm_comparison.py` | 72 |
| `tests/test_blind_review_pack.py` | 146 |
| `tests/test_registered_eval_runner.py` | 143 |
| `tests/test_audit_evaluation_comparability.py` | 115 |
| `tests/test_d52_scoring.py` | 31 |
| `tests/test_evaluation/test_evaluate_d4d.py` | 18 |
| `tests/test_evaluation/test_rubric20_scoring.py` | 16 |
| `tests/test_evaluation/test_general_context.py` | 25 |
| `tests/test_evaluation/test_explicit_dataset_scope.py` | 22 |
| **Total** | **588** |

These are this run's observed counts. Earlier E3x/D52 runs are not added to them.
The validator used the physical repository Python 3.13 environment, disabled
site/`.pth` startup and pytest plugin autoload, removed provider credentials,
and enabled Python network/live-command guards. Test cases and bytecode stayed
outside the worktree. Dependency bytes and arbitrary child binaries are not
independently attested or isolated by those Python hooks. No provider, native
binary or GitHub call was made, and GitHub CI was not checked.

## Scoring identity

The composition preserves D52's new deterministic identity; the rubric and
context-policy bytes remain unchanged from the pre-D52 evaluator.

| SHA-256 identity | Before D52 | This packet |
| --- | --- | --- |
| Evaluator source | `1ee3debcbd234f300115ec67885bac707c167ded1ef5256470b1c057f9812d41` | `89befc75f70615dc42575ac947900714c20274d85cc73ea84d7ac9f46b96f1e3` |
| Deterministic instrument | `9030eabdcbf018a39cfc1eef0427a8fbdadebfa2feb38b2d498552007debd659` | `509586a464c296dd1135a36297c91e54ae570ec2f250253bebfb08eeb73a76e5` |

Kind/version remain `deterministic_presence` / `2.0`; source identity distinguishes
the change. The committed `scoring-identity.json` records all four input hashes.
No semantic agent definition or rubric asset was changed.

## Reproduction and evidence

Run from a clean worktree at the frozen tested head with a **fresh** external
output path. The original command was:

```sh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B \
  scripts/adhoc/validate_d52_scoring_20261028.py \
  --output /private/tmp/d4d-wave5-evaluation-validation-20261028 \
  --expect-head fbbb2c7599c4a4a98ae27242db9b05c90954a020 \
  --base cf01eb12bbbbde04854163ecb1036cf9a5431e6e \
  --module test_arm_comparison --module test_blind_review_pack \
  --module test_registered_eval_runner --module test_audit_evaluation_comparability \
  --module test_d52_scoring --module test_evaluation.test_evaluate_d4d \
  --module test_evaluation.test_rubric20_scoring \
  --module test_evaluation.test_general_context \
  --module test_evaluation.test_explicit_dataset_scope
```

The validator's explicit `--base` is the new #5095 target. The older retained
E3x validator with a hardcoded `a0e28d882` target was not used for this run.

New compact evidence is in `notes/wave5_evaluation_validation_2026-10-28/`.
The committed preservation helper
`scripts/adhoc/preserve_wave5_validation_20261028.py` was independently reviewed
and copied unchanged from `505776cbf94fe4a8fc139acad7c42731eae4e992` before the
run. It uses the already retained archive reader and copies selected result,
log, JUnit and command bytes/modes verbatim. Raw source/import inventories stay
in `/private/tmp/d4d-wave5-evaluation-validation-20261028`; their exact hashes
are in the compact manifest. Those hashes are references, not embedded raw
evidence or a reconstruction of transient environment state. No new compressed
source inventories are added; existing ancestral evidence is preserved.

| Artifact | SHA-256 |
| --- | --- |
| Compact manifest | `f59ea9ffcf81bb8999491b5af6aca5d945d037903eea66c52597680c011ce4fb` |
| Outcome | `5aa06e6451d568915bda01c1a3cb071428fefdc6398ca5a2e0c3ff22002a53ff` |
| Pytest log | `fb1c96572117efcfaadde22d8b358e15e1a2f2c908cf1e1ca2087da811634b88` |
| JUnit | `1a005d3365028fd3409aba7fee770b7de7c38513b131365927a780d2d8d159ec` |

## Remaining boundaries

#5126's historical/v8 rating adapter and the proposed E5-direct native rating
adapter remain design-only. D02's comparator choice and native output acceptance
are not resolved by these tests. D52's approved rules are implemented here;
the approved canonical context changes remain in Claude's separate #5164 work.
The subsequent scoring roster, instrument/calibration, budget and launch gates
remain with the lead/owner. Issues are not closed merely for local test passes.

The draft PR description is `notes/wave5_evaluation_pr_body_2026-10-28.md`.
Claude/AGY should recheck the publication head and run the normal PR CI on the
published composition. A changed base needs a fresh composition review and the
checks relevant to that change, rather than silently transferring this result.
