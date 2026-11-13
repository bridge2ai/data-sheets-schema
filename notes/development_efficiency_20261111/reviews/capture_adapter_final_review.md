# Independent final review: fixed capture-recheck adapter

2026-11-11. Reviewed commit `f82e451743086fc4ec45cda044577e7b587c57c1`
against `458887766effe38207a77fea2d8033f1f3e1c7f3` in
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-capture-recheck-adapter-20261111`.
The committed five-file diff matches the earlier read-only source review;
working-tree status is clean. No imports, tests, source edits or owner contact
were performed by this review.

**Verdict:** no remaining source-review blocker to local integration and one
fixed genuine capture-readback canary under the approved plan. This does not
certify native acceptance or a passing genuine test. Freeze the new integrated
source/contract first and require its certified same-manifest 60-second
comparison canary before the one 900-second capture invocation. Existing packet,
source-origin, sandbox and cleanup requirements remain in force.

## Source obligations checked

- The fixed `capture-recheck` kind selects only the genuine capture-readback node
  with a 900-second limit. The unchanged driver rejects arbitrary node lists,
  collection mode and worker counts other than one. The CLI has no timeout override.
- Both outer and supervised admission require the same-manifest completed canary.
  Exclusive source+manifest marker creation binds the fixed node and output;
  changing the label cannot obtain a second attempt for the same identity.
- The capture test is in REQUIRED_FILES, checked against source, private tree and
  Git bytes. Existing composition and production-origin checks remain intact.
- The kind belongs to NO_LEASE_KINDS, excluding CPU and qualified timing kinds.
  Quiet-lock/inherited-lease refusal remains enforced. Classification keeps
  quiet-host/freshness flags false even with a passed qualification witness.
- The original outer timer, detached ownership, cleanup and driver/sandbox
  cutoffs remain unchanged. The fixed result check rejects a substituted,
  duplicated, missing, skipped or failing JUnit case and mismatched harness identity.
  Monitoring here is an environment selection, not evidence of consumer-arm work.

## Retained evidence and limits

Read evidence from
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-capture-adapter-20261111`.
All six result/JUnit hashes match the committed report; deadline records show no
expiry, no signals and verified normal owned-group termination.

| Invocation | Verified outcome | Helper elapsed seconds |
|---|---|---:|
| canary | 1 passed | 1.1259010000212584 |
| affected | 29 passed, 3 failed, 1 deselected | 1.4886970419902354 |
| entry-repair | 6 passed | 0.8379713750036899 |

The three failures are the matching/missing/wrong-manifest outer-entry fixtures:
the mock contract named a file without creating it, and final evidence hashing
raised FileNotFoundError. The committed test creates that fixture file. The six
repaired entry cases include those three and their supervised counterparts.
Thus 33 distinct cases have passing coverage across invocations; there was no
single final 33-pass run. Genuine capture reconstruction was not exercised.

CAP-UNIT-1, filed separately by the lead, corrected the synthetic unit helper
from a 20-second child budget plus 10-second cleanup reserve to a 10-second child
budget plus 20-second reserve. Its explicit 30-second acceptance-budget wording
correctly disclaims an independent outer hard alarm. The retained runs used the
older helper; the final reserve-only change was source-reviewed, not rerun.
This is not new proof of timeout cleanup or separately sessioned descendants.
The genuine route retains its separate, unchanged 900-second outer hard cap.

## Frozen SHA256 identities

| File | SHA256 |
|---|---|
| supervisor | `a995dba963a2a83d183dbb3fd523462d1fdd51b5a7132be7841c4b90557c0c6e` |
| quiet fixture | `6e2c3575f14d26af0b386a59b33c5f70fd9f19cef1f1e151f57e50df1ee912da` |
| adapter tests | `0d3ee39f987b927131af9e8b3296a1e2491de056e35ea7efe9b57dca4f766408` |
| final unit runner | `c6dcb342ccc050472efca914698d9972ffd4737e1b63fcb7b9aee94cb7ad1d52` |
| committed adapter report | `9a9866cfd2b91dc75e1557fdf68465600b656b22dc389e5c9f8398effe30268a` |

No additional concrete findings were identified. The target test arrives with
the separately reviewed capture-A change; this base alone is not a runnable
integrated composition. Stop after the genuine node and its owned cleanup for
review; this clearance does not extend to a full diagnostic or generation.
