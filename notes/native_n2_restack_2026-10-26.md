# N2 / D38 local restack — 2026-10-26 queue

Refs #4354 and priority 5 of the 2026-10-26 Codex coordination prompt.
These are local integrations for review, not launch or scientific acceptance.
No provider calls, live native probes, network operations or pushes are authorized.

The actual cached target is `a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5`.
The prompt's expanded suffix was incorrect. Target includes #5093 D38 and
#5094; it does not include A12/A13, receipts v5 or the proposed BC1 condition.

All original branches and worktrees remain unchanged. Fresh merge-based branches
retain both original histories; no old ref was reset or force-moved:

| Fresh branch (`codex/` prefix) | Merge head | Preserved old head |
| --- | --- | --- |
| `n2-1-restack-20261026` | `5d87ea676` | `44deb5220` |
| `n2-2-restack-20261026` | `8f4c3e328` | `ec9ebf240` |
| `n2-3-restack-20261026` | `e94a33cbd` | `3098aa6d7` |
| `n2-4-restack-20261026` | `6e01fd77a` | `fbf885213` |
| `n2-d38-restack-20261026` | `997e51287` before validation helpers | `8b1daa80f` |

The merges were text-conflict-free. Unit 1 also carries the two native selector
hash changes from preserved D38 commit `bea065c9a`: generic-v10 `ec081dbb…` and
uniform-v2 `22a55369…`, matching the installed target. The D38 merge converges on
the same pin values. Protected `shared_generation.py` and `canonical_hashes.yaml`
remain byte-identical to the target. Inherited evidence/log whitespace is retained.

Validation plan: verify all 13 actual installed native assets and full API/native
renders, preserve historical pre-D38 render evidence, then run the deduplicated
74-module changed-N2 roster and affected legacy regression modules. The two full
public completion modules are separately identified; they cannot be substituted
by negative paths or utility tests. The helper `scripts/adhoc/validate_n2_restack_20261026.py`
records the exact roster, committed source identity, protected-file equality,
interpreter/dependency identities, loaded project origins, raw pytest evidence
and post-run tracked-byte preservation in fresh external directories. It does
not sandbox the network or prove the bytes of installed third-party packages.

Priority 4 remains blocked: the 2026-10-27T05:52Z formal idle sample observed mean
CPU 51.7767%, peak 100%, maximum load per CPU 0.913135 and competing processes.
No unchanged recorder trial ran. Evidence tooling commit
`0adcec49e4de006eb79203bdff6171e0d1084cc0` preserves both the earlier sandbox
sampling refusal and the completed busy-host sample. The three unchanged trials,
conditional load comparison, paired diagnosis and justified recorder fix remain
pending a qualified host window. Functional checks below do not establish timing
causation. The 180-second helper and 900-second registered deadlines stay intact.

Validation results and final local delivery heads will be appended after the
source-frozen checks. Earlier historical counts are not new restack results.
