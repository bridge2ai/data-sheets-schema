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

## Merge 1: A13 / #5158

Pre-merge HEAD `a69a5bd347799662ffb03de000787ac62bea4313`; incoming
`cd07f2a3738e146eeaa30ae86d35d3161eb3413b`; actual sole merge base
`f8c5ac73caba610d40c49aaceddb31ead3590a72` with protected blob
`ae9d68d6c72c514df34b8e24b9e035eefdee7194`. Incoming blob is
`3fbe1b2c1ee89387369e34ae4f7363e0e89c34ed`. Both sides differ from base;
the driver was invoked once and preserved the exact B current bytes. All
pre/post path, mode and attribute checks passed. The complete preflight and
nine verbatim builder conflict hunks are retained in
`wave7_bc1_merge_evidence_2026-10-29/01-a13-{preflight,postflight}.json`.

Proposed resolution sent for the parent's independent read-only review before
editing: union the required imports; preserve staged `_write_outputs` and
`build_registration`, placing A13's decorator on `prepare_registration`;
retain sizing/BC1 parameters plus explicit `worktree`; synthesize context in
memory with worktree forwarding; resolve BC1-aware limits in the early A13
position before any preparation writes, deleting the late duplicate; retain
both sizing validation and A13 path/input/roster authority in `--check`; keep
staged per-project/BC1 CLI preparation with worktree forwarding; include
context SHA in progress alongside the existing sizing diagnostics.

Other files are Git's automatic merge. Prompt pins and the decision record
are inherited from the exact assigned head, not manually changed. No
protected proposal/re-pin or application validation has run.

The Codex parent reviewed all nine actual hunks and approved that union. It
was applied with retained `resolve_wave7_bc1_conflicts_20261029.py a13`;
`01-a13-resolution.json` records exact pre/post source and helper SHA-256.
The following A13 roster path/digest checks remain intact. The final #5211
merge will additionally carry its reviewed pending-registration-write handling.
`git diff --check` passes; this is not a pytest result.

A13 merge commit: `4f3c5bfa4d0ad6c890c7cfcd1423fad263d7fcae`.

## Merge 2: A14 / #5162

First parent `4f3c5bfa4d0ad6c890c7cfcd1423fad263d7fcae`; incoming
`8b885ee68262474275316755c3fc55dc05517dcb`; sole actual base
`cd07f2a3738e146eeaa30ae86d35d3161eb3413b` (protected C blob).
The incoming protected blob is A `f0b55f73e6e9e5bdc9cbb42b175b9a7bdff9d839`.
Both sides differ from C, so the driver retained B. Ordinary files merged
cleanly; no manual resolution was needed. Preflight attributes/modes/path
lineage and postflight HEAD/index/worktree checks passed. Evidence:
`wave7_bc1_merge_evidence_2026-10-29/02-a14-{preflight,postflight}.json`.
The branch still deliberately lacks A14's protected-file changes until the
separate proposal is applied in a validation archive. No tests have run.

A14 merge commit: `e18c3319e7051ef6f1ec9ce34d7ddecbe67c6247`.

## Merge 3: A23 / #5164

First parent `e18c3319e7051ef6f1ec9ce34d7ddecbe67c6247`; incoming
`90312e30e8d957e3b79510abe9ea768967983224`; sole actual base
`cf01eb12bbbbde04854163ecb1036cf9a5431e6e`. Incoming and base both have
protected C, so Git preserves current B without invoking the driver. The
pre/post checks passed. Evidence:
`wave7_bc1_merge_evidence_2026-10-29/03-a23-{preflight,postflight}.json`.

The only ordinary conflict is F3: the deferred-write comment versus the
`serialize_draft_context` import. The proposed union sent before resolution
keeps the import, a blank line, and the comment. The adjacent existing
`write_to_disk=False`, worktree forwarding, and A23 serializer invocation
remain. All context/decision changes are inherited automatically from A23.

The parent independently reviewed the actual hunk and approved this exact
union. Retained resolver mode `a23` applies it with a preimage SHA check;
`03-a23-resolution.json` pins the source and helper bytes. No tests ran.

A23 merge commit: `d6c83e58b057da48bd11f007d4f4a0985ae6923c`.

## Merge 4: #5210 report admission

First parent `d6c83e58b057da48bd11f007d4f4a0985ae6923c`; incoming
`fba016d92fd292c66d580006e848b8c43eb59505`. Actual bases are
`cd07f2a3738e146eeaa30ae86d35d3161eb3413b` (protected C) and
`aaa6f5bec2a0c7832d36143c4c7470d51cb8cee4` (F). Their sole common base is
`f8c5ac73caba610d40c49aaceddb31ead3590a72` (F), so their file-level union is
C. Incoming is also C; Git preserves current B without a file merge. The
Codex parent independently verified these actual Git bases and blobs before
execution. Full attributes/path/mode preflight and protected postcheck pass.

The merge is clean, with no ordinary conflict or manual source resolution.
Evidence: `wave7_bc1_merge_evidence_2026-10-29/04-5210-{preflight,postflight}.json`.
No tests, protected edits, calibration changes or publication occurred.
