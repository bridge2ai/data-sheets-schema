# E1 / #5755 second preparation refusal — 2026-11-11

The c8cc4b711 preparation passed its corrected gitlink roster and exact four
packet checks, then refused at `diff-index --quiet` against private commit
`6572481c714772402491198f60cd7e3016acb907`. No test, second worktree, contract or
private CI configuration was reached. Assigned native source remains frozen
at `01bdcb22dad66da1a167595251b23e6352c97ab7`.

The retained diagnostic JSON has SHA-256
`8cdc060a36d5b40378e642afbb2f2c07df56ebe7ed70c83c12da3e0075b4c6b1`.
Its independently checked census has 2,341 regular files, all bytes/executable
modes matching the index, exact selected roster, and 2,337 raw modifications:
all regular entries except the four explicitly staged packet targets. A sample
untouched entry had zero stat fields before diagnosis. `checkout-index` lacked
the index-stat update; the repair explicitly refreshes only newly materialized
private indices and retains every existing roster, source and packet check.

Correction to the diagnosis's scope string and script docstring: this was
**intended** as read-only, but the index changed during the observation window
from SHA-256 `d4aa9cab719f2da5432ffff8d31be3de02aa553d58ff4649fb30bed816c2489f`
to `1fbf03c1aad8c4b92f914ab30c33883546c48101b3adb92b9cd4a98fa5803d46`.
Its `index_unchanged=false` is retained verbatim. Porcelain `git diff` is a
documented auto-refresh-capable suspect despite the requested optional-lock
suppression; exact per-command attribution was not measured. The before-index
bytes were not separately saved, so restoration of that old index is not
claimed. No source bytes, manifest, committed tree or index blob identities
changed. Do not rerun this exact historical diagnosis helper; it is retained
with its result as provenance. Future checks must avoid refresh-capable
porcelain or explicitly disable its refresh, and verify index bytes afterward.

The preservation helper pins this exact refused manifest, diagnostic and private
commit; checks the four physical and committed postimages, exact cached delta,
unchanged assigned source and absent second tree/contract/CI override; and uses
the existing exclusive rename plus before/after full content census. It records
the prior diagnostic metadata mutation instead of claiming pristine index
history. Both earlier attempts remain evidence, never successful preparation.

No performance, observer-equivalence or acceptance result follows from these
artifact checks. The next corrected attempt remains bounded by the lead's
standing retry grant: preservation once, preparation at most 180 seconds, and
one 60-second genuine canary only on preparation success; stop on recurrence
of an unchanged failure. Measured arms and qualification are not granted.
