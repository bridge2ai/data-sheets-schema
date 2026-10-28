# Wave 3: #5139 and A23 independent verification

Completed offline 2026-10-28 UTC / 2026-10-27 PDT. **#5139's F1 lookup fix
passes; F2 needs an explicit scope disposition. A23 requires further evidence
corrections and reconciliation of conflicting D46 records before scoring.**

| Review | Owner head | Isolated tested head | Result |
|---|---|---|---|
| #5139 / #5213 | `68e0fffdfebbe77a6a24a0e086aaf3ebeb1999b5` | `725e2426c6bb05105e553d6f8a1a61962e68e68a` | 113 passed; 1 unrelated corpus comparison deselected; 0 skipped/failures |
| A23 / #5164 | `0341f0839e25e6815e992519637da562e041ec81` | `2bc5316e9431093fb8b644ff2beccf3572486d81` | 48 passed; 5 causal failures; 0 skipped |

Both runs passed tracked-source invariance and selected import-origin checks.
Tests and reproducibility helpers are committed in fresh isolated review trees;
the original owner branches/worktrees remain unchanged. The runs use Python
3.13.12, no `.pth` loading/plugin autoload, removed provider credentials and
Python network/command audit guards. These guards are not an OS sandbox for
arbitrary subprocesses; third-party package bytes were not attested. No network,
provider, live native binary, GitHub action, push, protected-file edit or existing
run/ATTIC change occurred. These focused results do not replace full PR CI.

## #5139 disposition

- **F1 resolved:** owned nested lexical paths survive historical manifest
  recovery. Symlink containment, traversal/NUL refusal and hash requirements
  remain intact. All six original causal cases pass; they also appear in AGY's
  tests, so repeated executions do not represent additional unique bugs.
- **F2 scope-qualified:** relative RunSpec inputs work, but progress identities,
  registrations and flat-output provenance retain absolute owner-bound paths.
  The orchestrator should explicitly narrow the closure claim and retain/split
  portable locator design work. Do not weaken absolute execution authority to
  make strings relative. Remote PR wording was not queried, so its current
  disposition is unverified offline.
- The unchanged historical probe read both real CHORUS canary records at cached
  `ada98b56b73b60217ccacf02fef2af4393d6ecae`. Bundle/manifest pins match and
  eight chunks reconstruct for each. Their assisted/invalid dispositions remain.

## A23 disposition

- **R8-F1 partially fixed:** Sick Children ethics, assent citations and some
  release/software corrections pass. The pediatric narrative still asserts
  unsupported monaural/16 kHz resampling. Its headset sentence also loses the
  source's “most” qualifier/tablet-microphone exception (lower severity).
  Additional manual findings cover pediatric questionnaire specificity,
  an uncited REDCap export identifier and Safe Harbor attribution.
- **R8-F2 partially fixed:** ECG/WFDB, clinical/OMOP and retinal/DICOM bindings
  pass. Two narratives now call environmental, activity and glucose data
  “custom JSON”; source metadata names environmental ASCII/ESDS and wearable
  Open mHealth. JSON encoding does not negate a named standard; the unsupported
  customization and environmental assignment need correction.
- **R8-F3 partially fixed:** original software/citation defects are corrected,
  but `bwa-indexed reference fasta` does not establish the asserted BWA-MEM
  algorithm. Remove that specificity or provide appropriate pinned evidence.
- **R8-F4 resolved:** explicit custom Kids First manifests retain authority in
  both synthesis entrypoints, with/without custom scope; default fallback and
  neutral vocabulary still pass.
- **D46:** earlier prose, its own settings table and the latest replacement
  conflict about CM4AI release/source priority and Kids First priority. Identify
  the controlling owner record and bind it to exact settings/digests; the
  bounded ignored-inclusive local search did not establish that no approval
  exists. The latest prose also omits one of Kids First's four actual priority
  entries. CHORUS's corrected hash is valid: 6,476 bytes,
  `ac94a74bd0d7d6c656564d67e656c7dbcf6627dca4c147a876eded072a81a3b0`.

The five failures are retained as failures, not xfails. After AGY corrects the
narratives, rerun the independent checks at a new frozen head and retain the
required exact-file human scientific review. Mechanical citation/schema passes
and the existing Boolean-settings decision do not approve every scientific
sentence. This cross-review does not edit AGY's contexts or reopen owner choices.

## Reproducible handoff

Detailed reports and committed test/validation archives:

- [#5139 report](/private/tmp/d4d-codex-wave3-5139-20261027/notes/wave3_5139_review_2026-10-27.md), branch `codex/wave3-5139-review-20261027`; this combined note is committed on that branch with its evidence.
- [A23 report](/private/tmp/d4d-codex-wave3-a23-20261027/notes/wave3_a23_review_2026-10-27.md), branch `codex/wave3-a23-review-20261027`, final review/evidence commit `3cada5d5c32678c9eac7a5e31508ccb9545c9ed2`.

| Artifact | SHA-256 |
|---|---|
| #5139 detailed report | `858a710e10feea49338ca0ef81514fccd9523eb8c862dadf847f3a93bb23af3c` |
| #5139 outcome | `95f4dbf5be097a762bc3b69fa1e238dd51e5f0694f77d4a42cbf5b93ef5e17bd` |
| #5139 path observations | `10e5b1b282e15164301df62e2e5d7964a030174467fdfa4bf6817c24e1179686` |
| #5139 archive manifest | `3764b3cbad1449f4fb269886187519204f1221c32edf08a50783b6dc85e81985` |
| A23 detailed report | `552c3e05e0120b0daf9fb6bd119a08e5ecfd6d5564f203f20741434bc63a1c89` |
| A23 outcome | `69dcba8d567b86b7d800a4d5667c780b5307c1e2bdb0761c8a324bcadf51af4d` |
| A23 archive manifest | `b26770d3300125459a5a079674ea0a07e8e89d75301aebd01d87a62e5a1bb9ca` |

Raw originals remain in `/private/tmp/d4d-wave3-{5139,a23}-verification-20261027/`.
Each repository archive preserves selected logs, JSON and JUnit with verified
byte/mode round trips; disposable synthetic case directories are excluded.
No full historical-corpus, live-generation or human scientific acceptance is claimed.
