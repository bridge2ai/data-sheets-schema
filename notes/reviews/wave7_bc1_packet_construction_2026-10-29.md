# BC1 Wave7 packet construction

2026-10-29. New isolated branch `codex/wave7-bc1-packet-20261029`, based on
`b7e4d3ef76b8ceee2c1c9ee5fdabba9ff00949e6`. Worktree:
`/private/tmp/d4d-codex-wave7-bc1-packet-20261029`.

The Codex parent assigned construction while it runs Task 4 tests serially.
The #5212 legacy-recovery production question remains an owner blocker; this
packet does not change that guard or imply integration approval. No tests,
provider calls, network, GitHub writes, push or main merge are authorized here.

Disk preflight reported approximately 16 GiB available; comparable new worktrees
occupy 619 MiB and 606 MiB. The target branch/worktree was absent from Git's own
inventory. No cleanup or existing-worktree modification was performed.

Assigned real-head merge order, using `--no-ff --no-commit` then a reviewed
explicit-path commit:

1. #5158 A13 `cd07f2a3738e146eeaa30ae86d35d3161eb3413b`.
2. #5162 A14 `8b885ee68262474275316755c3fc55dc05517dcb`.
3. #5164 A23 `90312e30e8d957e3b79510abe9ea768967983224`.
4. #5210 `fba016d92fd292c66d580006e848b8c43eb59505`.
5. #5212 `20def9d63a3131ef9b56eca39b61fbf5f6aaab49`.
6. Final #5211 `3c41133fcdcdb6db4d09564dc365b8b42b39c390`, containing the
   `36b230d69` packet, `c47726945` sizing fix, A23 and reviewed F3/F5/F7.

Every merge must retain protected `shared_generation.py` as regular `100644`,
Git blob `91105618cd25e33962b1c2d30f20b37101530bb2`, SHA-256
`1c4436b5ea689fcd674c848a722dd9a86495692ad83401682f3d805f49acb6d6`.
The retained helper checks HEAD/index/worktree, actual merge bases, incoming
mode and effective attributes before every merge. Multiple bases need an
explicitly reviewed file-level union explanation. A base-equals-ours fast path
with different incoming content stops construction.

The scoped attributes/custom driver are supplied only through per-command
`git -c` options. The driver checks exact current bytes and returns success
without writing them. Recursive virtual-base merges use Git's text driver.
Unexpected protected changes stop work; they are never silently restored.
No repository-wide Git configuration is changed. External raw evidence is
retained at `/private/tmp/d4d-wave7-bc1-merge-evidence-20261029` and copied into
the packet after review. Ordinary conflict hunks and stages are preserved.

The branch deliberately keeps the old protected implementation. The eventual
union will be a separate proposal diff; applying it and re-pinning is allowed
only in a fresh validation archive, then by AGY under Claude's lead for real
publication. No protected proposal is applied or re-pin made during these
merges. D63 calibration and causal cache testing follow composition and review.

## Local review finding before the first merge

The Codex parent's separate read-only helper review found two missing
preflight proofs: effective attributes were checked only for the current
checkout, and protected-path rename/deletion changes were not explicitly
examined. An incoming tracked `.gitattributes` could override the scoped
driver, or a path change could evade the intended file-level comparison.
This is an issue-ready local finding, not a fabricated GitHub issue number.
No merge or helper execution occurred before this finding was recorded.

Required bounded repair: capture root/src/package `.gitattributes` identities
and the effective protected-path attributes for every incoming/base tree;
reject any driver, filter or encoding override. Inspect rename-aware
name-status deltas between current/incoming and every actual merge base,
reject protected-path renames/deletions/type changes, and retain the proof.
Use disabled hooks, `GIT_NO_LAZY_FETCH=1` and file-only Git protocols. The
first A13 merge remains a canary: inspect its protected postcheck and ordinary
conflicts before continuing. Multiple-base file unions require a separate
read-only parent review of the actual bases.

The guard repair now uses `git check-attr --source REF` with the same scoped
attributes for current, incoming and every actual base tree, and retains
their root/src/package attribute blobs and text. Rename-aware full-diff
name-status checks reject any protected-path change other than an ordinary
modification. All helper Git reads disable hooks/lazy fetch and allow only
the file protocol. The merge command must carry these same settings. These
are merge-safety checks, not application tests or production changes.
