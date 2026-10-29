# Wave7 #5212 fixture follow-up

Branch `codex/wave7-5212-fixtures-20261029`, based on frozen packet
`20def9d63a3131ef9b56eca39b61fbf5f6aaab49`. Offline preparation only;
validation and the lead's final review are pending. No merge readiness claim.

The six cases below are part of the existing issue-ready finding in primary
`notes/coordination/2026-10-29-issues-from-wave6-packets-review.md`, F2.
Saved CI list SHA-256:
`8286497f405fda6d656cfb60416dd21d46ca1496be4d87a4b80baec98c6b4d42`.
The initial full preview at `19ab6025c2be8069895e563f771aeaef82a3e57d`
reproduced18 of21 saved failures; three passed. Own-head controls at
`39d6c33b5abdcd05bd8ec830211adb9caf013acb` are recorded separately.
This patch addresses only six fixture defects, not all18 failures.

| Cases | Reviewed repair | Assertions retained |
|---|---|---|
| Duplicate-key repair | Real `prepare_usage` before writing full/core fixture outputs | Duplicate locations, repair prompt, repair count and final clean YAML |
| Readable schema-repair rounds | Real accounting initialization before initial malformed full output | Worsening finding count, second repair and final clean output |
| Two foreign-owner entrypoints | Create matching accounting first, then inject only the foreign label as raw adversarial bytes | Real before-lock/inside-lock owner guards, no dispatch/date restoration, released lock and unchanged evidence |
| Two thinking-display wire units | Isolate the per-attempt latch at the already-stubbed accounting boundary; assert exactly one call with the spec | Real SDK MockTransport, count and stream bodies, summarized display, bounded-client identity and zero retries |

Independent root review read the complete diff before this commit. The changes
do not re-anchor a monitor from mutated disk, change a recovery success into a
refusal expectation, or alter any production/accounting guard. All new mocks
are scoped to the two existing wire units; real guard positive/negative tests
remain part of the verification selection. The raw-owner helper deliberately
does not call a legitimate writer with an invalid identity.

The narrow `.gitattributes` addition gives only the existing
`notes/reviews/wave7_5212_a14_evidence_2026-10-29/**` directory `-text -whitespace`
as requested by the lead. Evidence contents and other attribute rules stay
unchanged. No source, prompt, decision, run or historical-data file is changed.

F1 confirmation: at the reviewed `cf7a1f11e5456ab1e7aae68668fe071112c22792`
head and this branch, `scripts/adhoc/d41_request_parity_20261026.py:222`
uses `typed.omission_wire_request(packet, derivations=runtime._derivations(spec))`.
Both response `request_sha256` and chunk entries come from that projected wire
request. The initial preview's six parity cases passed. This statement does
not claim the documentation-only cf7 commit originated the earlier code fix.

Required verification: complete four changed test modules plus real API-latch
retry/tamper/allowed-retry coverage, on committed exact bytes with external
basetemp and network denial. The remaining diagnostic-precedence and public
legacy-recovery cases keep their existing assertions pending classification
and lead disposition. The #5212+simulated-main-after-batch2 full-suite gate is
still required before publication; no push or GitHub action is authorized here.
