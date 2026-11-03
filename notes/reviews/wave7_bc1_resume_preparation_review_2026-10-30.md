# BC1 resume preparation: independent static review

2026-10-30, before the pinned-main merge. This records read-only review of the
following helpers by the delegated harness reviewer; no tests or provider calls
are represented by this note.

- `wave7_bc1_protected_merge_20261029.py`: SHA-256
  `61086a7efebaabe0200a814267d5e1328e03bee12a88014ee860a24a9b1fdc25`.
  Only pinned main `50bc50af678ae5216b3985c340fe1344da26c05e` was added to the
  allowlist and the driver log moved from deleted temporary storage to durable
  `d4d-executions/plans/reviews/wave7_resume_2026-10-30/bc1-main-merge/`.
- `prepare_wave7_bc1_resume_proposal_20261030.py`: SHA-256
  `9068b7332536bbeb5b497408e164d165111158609545488f8b288a4895f03578`.
  It pins the prior transformer, requires both assigned ancestors and a clean
  branch, verifies complete main plus D41's single journal dependency, verifies
  the invertible six-hook BC1 union, and writes fresh dated proposal/proof only.

The actual merge bases are A23 `90312e30e8d957e3b79510abe9ea768967983224`
(SG blob `3fbe1b2c1ee89387369e34ae4f7363e0e89c34ed`) and A14
`8b885ee68262474275316755c3fc55dc05517dcb`
(SG blob `f0b55f73e6e9e5bdc9cbb42b175b9a7bdff9d839`). Their common ancestor
`cf01eb12bbbbde04854163ecb1036cf9a5431e6e` has the former blob, so the effective
virtual SG base is A14's blob, identical to incoming main. The merge therefore
preserves current BC1 blob `91105618cd25e33962b1c2d30f20b37101530bb2` through
Git's unchanged-incoming path. The scoped keep-first driver remains a guard;
no restoration after an unauthorized protected write is permitted.

The reviewer found no blocking issue in these exact helper bytes. F6 remains
byte-identical to the lead's resolved file (`cd17fed4c330320511519c5757f29666021d6639b8998ac9dc4c5a244a67b03c`).
Canonical prompt pins match both merge sides (blob
`5a3781c0e17ada146a06a7a68c369cfd56341407`, SHA-256
`39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584`).
Preflight/postflight evidence, merge resolution, new proposal and scratch-only
validation remain required. Old evidence and protected source stay unchanged.
