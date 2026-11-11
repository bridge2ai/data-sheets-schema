# Fixed integration branch admission, 2026-11-11

The reviewed capture/AST/adapter composition is on new local branch
`codex/native-capture-ast-integration-20261111` in the assigned native checkout.
Original branch `codex/native-u1u3-combined-20261108` is preserved at
`458887766effe38207a77fea2d8033f1f3e1c7f3`.

The M composer's `require_source` previously admitted only the original branch,
so it would refuse both preparation and exact config restoration on the new
branch. The lead approved adding this one literal branch name alongside
`base.BRANCH` in that single check. No arbitrary branch argument, packet,
config, HEAD, cleanliness, protected-preimage or ancestor check changes.
The historical base composer and its own branch gate remain untouched.

Pre-followup integration head: `41135a507d8a00c4cbe83ad51b4fdde8c7c2671f`.
Independent object comparison found all 3 capture, 11 AST and 5 adapter files
byte-identical to donors `459e56bf896a29d854c5d250ce8632d7e2564427`,
`89975411d65e42aae5baa2bb92276ad5f9fabf1a` and
`f82e451743086fc4ec45cda044577e7b587c57c1`, respectively. Exactly 19 files
changed, with no donor loss; four protected preimages remain unchanged.

Read-only inspection of the actual M/WP1 runner chain and sparse preparer
found no additional branch-name gate. The sparse preparer invokes M's
`require_source`, not the historical base composer's entry check. The
preparer dynamically binds the adapter's expanded `REQUIRED_FILES` roster.
This is source analysis, not a preparation/runtime pass. Independent source
review of the final commit precedes preparation. The lead owns filing the
integration finding; no donor commit is rewritten.
