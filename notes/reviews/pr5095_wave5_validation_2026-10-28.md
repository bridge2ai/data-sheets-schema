# PR #5095 wave-5 review fixes: validation and remaining fixture-location blocker

Base: `57784daadcc109839e4c76260ee4e5fd415a1c21`.
Branch: `codex/wave5-5095-review-fixes-20261028`.
Scope: task 0b; F1, F2, F4, F6 and F7. F3 is unchanged.

## Changes

- F1: `--check` verifies the pins of every roster-captured registration, requires
  its path and captured SHA-256 to match the out-dir registration already checked,
  and checks each out-dir document's declared `registration_path`.
- F2/F4: help states that checking attests pinned bytes, not runtime admission;
  help and the mixed-namespace refusal name the selected checkout's own venv or
  `python -S` with site-packages on `PYTHONPATH`.
- F6: exact-refusal tests cover a subdirectory, nested checkout, mixed namespace,
  missing source package, and synthesis with missing selected vocabulary.
- F7: the positional vocabulary fixture uses a literal relative target and
  asserts the default is relative. Both copied-CLI invocations use `cwd=tmp_path`.
  A teardown fixture inventories all checkout paths, including ignored/hidden
  files, and compares mode, size, modification time and inode. It excludes Git
  metadata and pytest's scratch tree, and also runs when a test fails.

No production `src/` files, decision records, prompt pins, run data or ATTIC
content changed. Registration construction and request construction are unchanged.

## Tests, before and after

Interpreter: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python`
(Python 3.13). All tests were serial, offline, with the three API keys unset,
`PYTHONPATH=$PWD/src`, `PYTHONDONTWRITEBYTECODE=1`, and pytest options
`-q -p no:cacheprovider -o addopts= --basetemp=$PWD/.codex-pt`.

| Check | Before | After |
|---|---|---|
| Five required modules | 88 passed, 23 failed | See combined run below |
| New `test_wave5_5095_review.py` | 5 failed | 5 passed |
| New module plus root/import guard cases | Not run as a combined baseline | 9 passed |
| Five required modules plus new module | Not run as a combined baseline | 97 passed, 24 failed |

The five required modules are `test_wave4_5095_review.py`,
`test_preflight_resource_authority.py`, `test_build_api_registrations.py`,
`test_build_draft_contexts.py`, and `test_api_launcher.py`.

All four F1 cases were false-green before the change. They cover the review's
roster-indirection/schema-drift scenario, intact pins at a different roster path,
a different declared out-dir path, and changed registration bytes between the
out-dir and roster captures. Each now refuses for its specific reason. The fifth
case checks F2/F4 help.

**Full acceptance remains blocked by the prescribed temporary directory.**
`resources.checkout_at` deliberately chooses the outermost checkout, so a
selected fixture beneath `$PWD/.codex-pt` is nested and must be refused. Nine
pre-existing cases fail for that reason. Fourteen existing launcher cases refuse
their log files because the files are inside the checkout. The added synthesis
case also encounters the root refusal before the vocabulary guard. These account
for all 24 final failures. No guard was weakened to make the harness pass.

An intermediate run redirected pytest output into a checkout-local evidence log;
the F7 teardown correctly detected that log changing (three extra teardown
errors). The final run used captured tool output and had **zero teardown errors**.

Permission was requested to put temporary fixtures outside the worktree, because
the brief also forbids edits outside it. No answer had arrived when this note was
written. A green full suite and the remaining causal mutation checks require
that fixture-location exception.

## Mutation evidence

The committed helper `scripts/adhoc/verify_pr5095_review_fixes.py` runs each
control and mutation serially, restores the builder in `finally`, and refuses
to count a mutation when its unmodified control fails.

| Mutation | Control | Mutated result |
|---|---|---|
| Delete checkout-root guard | 2 passed | 2 failed: killed |
| Delete mixed-namespace guard | 1 passed | 1 failed: killed |
| Delete source-package guard | 1 passed | 1 failed: killed |
| Delete missing draft-vocabulary guard | 1 failed: nested fixture | Not executed |
| Delete draft worktree pass-through | 1 failed: nested fixture | Not executed |
| Revert vocabulary constant to absolute | 1 failed: nested fixture | Not executed |
| Delete CLI resource binding | 2 failed: nested fixtures | Not executed |

Reproduce with the stated interpreter/environment:

```bash
python scripts/adhoc/verify_pr5095_review_fixes.py mutations \
  --evidence .codex-5095-evidence \
  --basetemp "$PWD/.codex-pt"
```

After authorization, substitute a temporary base outside every checkout to
complete the blocked controls and mutations. The helper contains all seven
mutations, including the F7 regression checks. Intermediate logs are not claimed
as durable evidence; the helper and this result table are committed.

## Identical registration bytes

The helper executed the baseline builder and the modified builder in separate
processes, at the same absolute script/cwd paths, with the identical CLI arguments
`-p CHORUS -l wave5_review_bytes -o <worktree>/.codex-5095-evidence/byte-comparison/prepared --replace`.
It first required `git diff <base> -- src .claude data pyproject.toml poetry.lock`
to be empty, so imported production code and model-facing resources were shared
unchanged. Only the builder code was selected from `git show <base>:scripts/...`
versus the worktree. No provider/request execution was performed.

| Artifact | Bytes | SHA-256 at both revisions |
|---|---:|---|
| CHORUS registration | 5214 | `fc980c16d3b752ffd43f17fd42b20d4a631eed5ea270bf118ad1c95d02059d72` |
| Roster | 396 | `137e61511ae241bad52ac9a405a70295fce5ef6ec499194cbf331220e03c4bfd` |

```bash
python scripts/adhoc/verify_pr5095_review_fixes.py compare-bytes \
  --evidence .codex-5095-evidence/byte-comparison
```

The comparison includes path-bearing bytes, so another checkout/output path will
produce different digests; equality between the two revisions must still hold.
Builder SHA-256 tested:
`2b024c1167ddd7e152a6eb224d3c9f47ed8c682ee07ec21338d805bec7701b71`.
