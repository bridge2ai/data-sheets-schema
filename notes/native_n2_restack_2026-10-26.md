# N2 / D38 local restack — 2026-10-26 queue

Refs #4354 and priority 5 of the 2026-10-26 Codex coordination prompt.
These are local integrations for review, not launch or scientific acceptance.
No provider calls, live native probes, network operations or pushes are authorized.

The actual cached target is `a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5`.
The prompt's expanded suffix was incorrect. Target includes #5093 D38 and
#5094; it does not include A12/A13, receipts v5 or the proposed BC1 condition.

All original branches and worktrees remain unchanged. Fresh merge-based branches
retain both original histories; no old ref was reset or force-moved:

| Fresh branch (`codex/` prefix) | Integration checkpoint | Preserved old head |
| --- | --- | --- |
| `n2-1-restack-20261026` | `5d87ea676` | `44deb5220` |
| `n2-2-restack-20261026` | `8f4c3e328` | `ec9ebf240` |
| `n2-3-restack-20261026` | `e94a33cbd` | `3098aa6d7` |
| `n2-4-restack-20261026` | `fb5d50734` | `fbf885213` |
| `n2-d38-restack-20261026` | `9ea9b70a3` before reviewed fixture repairs/evidence | `8b1daa80f` |
| `e3x-restack-20261026` | `2bbb0dfff` (separate E3x tree) | `d6eed9274` |

The N2/D38 merges were text-conflict-free. Unit 1 also carries the two native selector
hash changes from preserved D38 commit `bea065c9a`: generic-v10 `ec081dbb…` and
uniform-v2 `22a55369…`, matching the installed target. The D38 merge converges on
the same pin values. Protected `shared_generation.py` and `canonical_hashes.yaml`
remain byte-identical to the target. Inherited evidence/log whitespace is retained.

The final delivery head will be recorded under `### codex` in the primary
`notes/coordination/STATUS.md` after the remaining frozen checks finish. The
auxiliary `codex/n2-public-driver-20261027` at `9e1ac5227` contains reviewed
test-only repairs and the gated public-test driver. Neither active test tree is
changed while its checks run. Separate `codex/n2-delivery-20261027` stages the
completed evidence without invalidating those checks; it will be integrated
into the fresh D38 branch after its legacy batch ends.

The validation roster consists of 72 native modules, two separately gated full
public completion modules, and 18 affected legacy modules. The helper
[`validate_n2_restack_20261026.py`](../scripts/adhoc/validate_n2_restack_20261026.py)
records the exact roster, committed source identity, protected-file equality,
interpreter/dependency metadata, loaded project origins, raw pytest evidence
and post-run tracked-byte preservation in fresh external directories. Children
use `-S -P -B`, explicit physical dependency paths without `.pth` execution, and
the actual venv prefixes. This does not sandbox the network, attest installed
third-party package bytes, or reconstruct a historical dependency environment.

Priority 4 remains blocked: the 2026-10-27T05:52Z formal idle sample observed mean
CPU 51.7767%, peak 100%, maximum load per CPU 0.913135 and competing processes.
No unchanged recorder trial ran. Evidence tooling commit
`0adcec49e4de006eb79203bdff6171e0d1084cc0` preserves both the earlier sandbox
sampling refusal and the completed busy-host sample. The three unchanged trials,
conditional load comparison, paired diagnosis and justified recorder fix remain
pending a qualified host window. Functional checks below do not establish timing
causation. The 180-second helper and 900-second registered deadlines stay intact.

## Completed verification

- Installed D38 validation at `f2dca0dd1`: 27 focused passes, all 13 actual
  installed assets captured, three exact stale-asset refusals, and complete
  API/native renders. The 4,433-byte current R9 passage appears once in each;
  the 25,589-byte uniform section is identical. Report SHA256
  `c18485bc72e1ce659625781ca83f1ffc17213101cd51fd3d313454c91d370771`.
  Complete render evidence and a separate Codex internal full-text review are in
  [the evidence folder](native_n2_restack_2026-10-26/). Existing scientific and
  procedural differences between arms remain disclosed; this is not equivalence
  or scientific approval. The unit-4 helper dependency was separately corrected
  and its 27 focused tests passed at `466cf410e`, delivered as `fb5d50734`.
- The first native attempt at `f0afbe119` refused before collection when the
  editable-install `.pth` introduced a foreign project namespace: zero tests.
  The next attempt at `cb06ce288` was interrupted after 610 completed passes
  when Python 3.13's no-site venv-prefix behavior was diagnosed. The old driver's
  reported 611 includes an anonymous unfinished XML case and is withdrawn.
  Both raw attempts remain unchanged and are not added to final counts.
- Full 72-module native run at `9ea9b70a3`: **1,760 passes, six failures,
  41 setup errors**, exit 1. All nonpasses were confined to three stale test
  modules; production was unchanged. Five response fixtures reused a cached
  trace after mutating its snapshot, one loader mock lacked `_catalogs`, and
  41 setup checks reconstructed an early oracle without undoing later cache
  additions. The reviewed repairs preserve controller snapshot semantics,
  strict-loader ordering, the exact original oracle hash and every original
  state/outcome comparison. Added caches are checked explicitly. See
  [oracle history and checks](native_trace_oracle_20261027/README.md).
- Those three modules passed **56 tests** at `9e1ac5227`, including three new
  causal cache mutations. Exact XML identities and Git bytes establish
  **1,754 unchanged passes + 56 repaired passes = 1,810 distinct cases** across
  two frozen runs. All original identities and nonpasses are covered;
  production, shared helpers/configuration and the other 69 native modules are
  unchanged. This is **composed case coverage**, not a fresh single green suite
  or proof of cross-test ordering equivalence. The
  [comparison report](native_n2_restack_2026-10-26/repair_coverage.json) pins
  every case and input. Its
  [helper](../scripts/adhoc/compare_n2_repair_coverage_20261027.py) also checks
  literal fixture references with ignored files included; computed dynamic
  imports are outside that search's proof.
- Neutral and omission public completion at `9e1ac5227`: **one pass each**,
  with exact expected case identities and all source/import checks passing.
  Neutral took 661.71s pytest / 666.81s guarded driver; omission took 663.60s
  pytest / 668.71s guarded driver. The explicitly
  synthetic CLI completed actual local stage, receipt, attribution, recorder,
  saved-record and spent-evidence checks. Omission is admitted only after this
  exact successful case and its preservation/origin proof. The final driver
  reports both stages passed, `runtime_gates_passed: true` and
  `scientific_acceptance: not_assessed`. Neither case invokes a real native
  binary or provider. Exact results and proof are in the
  [public completion evidence](native_n2_restack_2026-10-26/public_completion_evidence/manifest.json).
- E3x is complete separately: **475 local + one corpus = 476 distinct passes**
  at `2e74ad0ac`, delivered cleanly as `2bbb0dfff`. Its strict provenance/hash
  and blinding changes, test-local lock isolation, exact evidence manifest and
  preservation proof are documented in that branch's
  `notes/e3x_restack_2026-10-26.md`. Historical evaluations were not regenerated.

These groups are deliberately not summed: focused checks can overlap broader
coverage. Driver/archive helper tests (15 and eight passes) are separate utility
verification, not native completion cases. Existing failed/interrupted evidence
is retained in [lossless archives](native_n2_restack_2026-10-26/regression_evidence/manifest.json);
the archive helper verifies bytes/modes without reclassifying any original
outcome. Synthetic case/cache directories remain outside the archive at their
original external paths, explicitly listed as excluded.

## Pending validation and acceptance

The separate 18-module legacy suite is still running on its frozen head.
Its terminal results, the fixture repairs propagated through fresh units 2–4,
and final integration byte checks must be recorded before this delivery is
complete. Both public completion cases have passed.

Priority 4's three controlled recorder trials, conditional load replay, paired
diagnosis and a causally justified fix remain blocked by the formal host gate.
A functional neutral pass under the restacked source does not substitute for
those measurements on unchanged `01969cbed` and `d41282871`. No timing fix is
claimed. Independent owner review, a real-binary probe and any authorized native
canary remain separate obligations; no scientific approval or launch authority
is conferred by these software tests.
