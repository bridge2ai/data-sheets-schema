# D52 publication follow-up: labels and compact evidence

Claude's18:24Z assignment is complete locally: D1's misleading Q9 label is
corrected, D2's scope is approved by owner D61, and D3's inventory tarballs are
replaced in the publication tree by compact verified results. **121 focused
tests passed**, after a failing baseline canary and the same canary passing
with the repair. Original evidence remains recoverable.

## Scope and review

- Branch `codex/wave5-evaluation-publication-20261028`, worktree
  `/private/tmp/d4d-codex-wave5-evaluation-publication-20261028`.
- Parent delivery: `073fe89d049e7be6afb4029ddb5ec2878fc00d39`.
- Baseline tests/selector: `72beb10f0fde062dda43fda9098a42dfd147c1b6`.
- Frozen fixed source: `f5d00a9fa0cc1eb058f16122d31ed0db560efccd`.

The only production delta is seven lines in the installed evaluator. After
unchanged numeric scoring, a Q9 unit with D52 omissions gets a neutral label
naming populated retained fields and the excluded-criterion count. Zero,
partial and complete coverage use this description. Collection labels follow
the selected worst-scoring unit. Numeric scores, maxima, evidence pointers
and applicability notes stay unchanged. Other contexts retain their labels.
No canonical rubric, context, schema, decision record, generation asset or
historical output is edited.

A separate Codex review agent examined the frozen source, nine new cases,
exact-node selector and compacting helper read-only and found no blocker. It
checked all18 retained result files against original manifest hashes and both
archives in Git and existing worktrees. Claude's external review and CI remain
separate publication gates.

Owner **D61 at2026-10-28T18:23Z** approves the two nested committee-contact
aliases wherever the criterion is scored, including Rubric10 E2.2. Claude
recorded it at `8c91e373a39cfc47a128ce21b034bd6587adcddb`. D2 needs no further
implementation change. No historical scores are rewritten; D52's changed
applicability denominator is not improved source coverage.

## Validation

| Run | Result | Meaning |
|---|---|---|
| Baseline exported-JSON canary,72beb10f0 | 1 expected failure | Original label claims excluded content |
| Fixed same canary,f5d00a9fa | 1 passed | Nonempty JSON has neutral label, Q9 max5 and rubric max88 |
| First broader invocation | Setup error,zero tests | Incorrect module names; diagnostic preserved |
| Corrected invocation,f5d00a9fa | 121 passed,0 failures/errors/skips | Existing scorer coverage plus nine label cases |

Modules: `test_d52_publication_labels`9, `test_d52_scoring`31,
`test_evaluation.test_evaluate_d4d`18, `test_evaluation.test_rubric20_scoring`16,
`test_evaluation.test_general_context`25, and
`test_evaluation.test_explicit_dataset_scope`22. Source/import attestations
passed. Driver time36.862734seconds is not a benchmark. The canary is included
in121, not added again to the distinct-case count.

The same driver, interpreter, offline environment and external output layout
served both stages. The incorrect-module invocation failed before pytest;
correcting arguments did not change source. Raw evidence remains under
`/private/tmp/d4d-wave5-d52-label-{baseline,canary,targeted,targeted-corrected}-20261028`.
Reproduce with `validate_d52_scoring_20261028.py`, exact retained plan commands,
clean named heads and fresh external output paths.

`compare_d52_label_exports_20261028.py` compares the actual canary JSON with
a strict changed-path allowlist: two Q9 labels, evaluator/instrument hashes,
temporary input path and timestamp. All scores, maxima and evidence are
identical. This proves one synthetic canary, not a corpus rescore. The actual
fixed43306-byte JSON SHA-256 is
`406030753a407d5af9a06d65cfc07d4cfc13acd8759253ec29b86e76d1ff0178`.

Source pinning gives the label correction a new identity:

- Runner: `aa917606353a0b078a0596025d0ce0f0de970886b717c280989ab6155198426a`.
- Instrument: `b38117d96e73987f236d4d3d47da5b84a952401537f9a2ae4d2c44bf981fc064`.
- Prior D52 instrument: `509586a464c296dd1135a36297c91e54ae570ec2f250253bebfb08eeb73a76e5`.

Rubric10, rubric20 and context-policy pins are unchanged. Earlier588-pass
integration evidence applies to its named pre-label head; that full suite was
not rerun on the final label source and counts are not pooled.

## Evidence and publication

Compact validation retains all four outcomes, including baseline and setup
failures. Manifest `notes/wave5_d52_publication_validation_2026-10-28/manifest.json`
SHA-256: `83036d0843abc22d9baacec836e8fb3317fd6d000a6d09e66ff61d4e4095c34a`.
Export comparison SHA-256:
`7b2a5ed14f60e7a426f777eefc053b36721d49a423128f58b267b821b18290a7`.

D3's original baseline/fixed results are separately retained under
`notes/d52_scoring_validation_2026-10-28/compact/`. Its README records archive
hashes, byte counts and exact inventory recovery commands. Only two redundant
tarballs are removed from this **new publication tree**. Original worktrees,
external evidence and Git history stay intact. This reduces PR file payload,
not historical Git object storage.

Publish through the existing E3x branch, preserving ancestry, targeting
`feat/v10-preflight-scripts` first and retargeting main after #5095. Claude/AGY
must check whether that branch already has a PR; no remote lookup was made.
Local D1–D3 issue drafts and an updated PR body are retained. No provider,
GitHub, push, merge, scoring campaign or backfill action occurred.

Claude's D4 maintenance nit and D5 parent-field specification observation are
outside this correction. Historical/v8 #5126 and native E5-direct adapters
remain design-only. Dependency bytes and arbitrary child-process network
isolation are not attested by the Python validation guards.
