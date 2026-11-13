# Start-claim design ruling: helper 3 handoff

Issue 5992: c9316e513414e811d52029806d22332d335ddc6a. Issue 5993: c39526da9a01c41f4a168e58d45f2dea4ad10c00.

The journal hash chain and consecutive event filenames detect interior removal or alteration. Nothing anchors the last event: deleting a start claim at the tail can renew that direction, just as deleting the existing limits-refusal latch at the tail can remove that refusal. Both limitations have explicit scratch-only regression witnesses. A complete consistent older copy of the state is not detected.

Final branch heads after carrying both commits:

- codex/native-launch-sequence-hardening-20261112: c39526da9a01c41f4a168e58d45f2dea4ad10c00.
- codex/native-failure-record-20261112: ab34de98957f69758e4b349ffe43206868ac7c73.
- codex/native-incomplete-capture-retention-20261112: 4db154f88c78a28db2e6ed4e460debc3a96c9fa5.

Saved test counts (overlapping cohorts, not a unique-test total):

- design-5992-canary: 1 cases, 1 failures, 0 errors, 0 skipped; exit 1.
- design-5992-canary-02: 1 cases, 0 failures, 0 errors, 0 skipped; exit 0.
- design-5992-composed: 173 cases, 0 failures, 0 errors, 0 skipped; exit 0.
- design-5992-whole: 173 cases, 1 failures, 0 errors, 0 skipped; exit 1.
- design-5993-canary: 4 cases, 0 failures, 0 errors, 0 skipped; exit 0.
- design-5993-whole: 272 cases, 0 failures, 0 errors, 0 skipped; exit 0.
- design-carry-failure: 272 cases, 1 failures, 0 errors, 0 skipped; exit 1.
- design-carry-failure-canary: 1 cases, 0 failures, 0 errors, 0 skipped; exit 0.
- design-carry-failure-recheck: 17 cases, 0 failures, 0 errors, 0 skipped; exit 0.
- design-carry-retention: 272 cases, 0 failures, 0 errors, 0 skipped; exit 0.

The first journal canary failed because a fixture timestamp call lacked its required label; that was corrected before its passing rerun. The uncomposed whole run had one genuine-registration fixture setup failure because the protected main RunSpec lacks native_shared_generation_version. The private four-postimage composition supplies the approved protected code; all final whole-file runs use that composition. Both earlier failures remain in the saved evidence.

The first failure-branch composition refused a symbolic branch name at private Git update-ref; the following test invocation refused that incomplete manifest before starting tests. The retained refused composition was not reused or modified. A fresh composition using the exact carried commit was built successfully. This setup error did not change any source branch or temporary CI configuration.

The first failure-branch whole run passed 271 cases and failed one historical readback case because local git cat-file exceeded its existing ten-second timeout. Its saved test wall time greatly exceeds the runner's active duration; the traceback establishes the local Git timeout, not expired capture evidence. The single case and then its entire test file were rerun unchanged; both passed. The other seven whole files, including genuine registration readback, passed in the original run. The failed run remains recorded and is not described as wholly green. No timeout or production check was relaxed.

## Implementation and review

The local capture-word journal is now version 2. A closed sequence_start event binds the normalized UTC direction, host confirmation, registration digest, word digest, packet path and existing common chain/authority fields. Owner starts also append events and remain repeatable. Delegated replay is registration-wide, including after word renewal and through another packet. The append uses the existing authority lock and file-plus-directory fsync before any child command. The separate start directory is removed; no filesystem identity is persisted.

The sequence never initializes the journal. Missing or unreadable state, empty replacement state, or an unrecorded word refuses before capture. Version 1 journals can be read only as historical evidence; current activation, starts and latch writes refuse. No registered document kind or version changed.

The verified entry supplies a one-use per-invocation namespace binding covering the namespace, argument list, captured source bytes and captured registration/review map by identity. The body consumes it before parsing or packet effects; the entry expires it on return. Ordinary imported calls, including loaded-A with reviewed retained-B bytes and even a populated input map, refuse. Fixtures use the real entry with both source pins and apply only a test-local clock substitution after verified compilation. Both supported module entry paths are exercised with fabricated commands in an isolated copied package. This boundary assumes the trusted entry and interpreter are intact; it is not protection against arbitrary code already controlling Python globals.

The read-only adversarial pass checked event closure, current-word selection after start events, registration-wide direction normalization, historical format routing, durability, entry binding lifetime, and module execution as main. The accepted unanchored-tail limitation is disclosed above. No additional strengthening was silently included.

## Optional separate strengthening proposal

Propose a separate commit anchoring the committed event count and tip hash in retained authority, with a crash-safe fail-closed append/update protocol under the existing lock. Keep the immutable authority binding digest separate from the mutable tip so an append does not invalidate prior event hashes. An independently retained tip would make deletion of a tail event disagree with authority. Replacing authority by rename must also preserve lock continuity, so the protocol needs its own review. This is a proposal, not an implemented optional commit, and it still cannot detect restoring a complete consistent older authority plus journal. No inode or filesystem identity is proposed.

## Integration and bounds

Both fixes were cherry-picked with origin references onto the failure-record and incomplete-capture-retention branches; exact mappings and messages are in JSON. Retention is taken under D141, not optional. No rebase was performed. The four protected files remain byte-identical to main on all three actual branches, and guard v1 is unchanged. Approved protected post-images exist only in private test compositions, whose temporary CI configurations were restored byte-exactly.

The earlier failure-record handoff's statement that these hardening repairs remain unresolved is superseded by this handoff. Independent review and lead integration remain outstanding. Nothing was pushed or published. No real native executable, probe, capture, reservation, provider or model call occurred; synthetic word and test state stayed in this helper's scratch.
