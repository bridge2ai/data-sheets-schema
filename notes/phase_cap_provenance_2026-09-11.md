# Phase output-cap provenance — 2026-09-11

For #1167 and #1253, every generation, repair and report-regeneration path
now derives its effective output cap from the model actually passed to the
request. The request, interrupted-stream metadata, completed usage row and
recorded phase map use that same cap. A non-receipt full or repair call on
`google/claude-opus-5-high` therefore records 64,000, rather than reporting
96,000 while the sender clamps the request to 64,000.

Receipt full-phase overrides remain supported and route-clamped. Bare
`claude-opus-5` keeps its existing 96,000 ordinary phase caps and 128,000
receipt full cap. Unknown-phase defaults are bounded by the route too.
The optional model argument avoids consulting a changed global configuration
when a running call already has its selected model in its settings.

The sender already enforced these route ceilings; this corrects the
provenance and pre-send budget plumbing, not a retrospective generation
result. Existing records, scores and the frozen semantic reference manifest
are unchanged. Offline generation and repair tests compare the fake client's
actual request caps directly with the recorded usage and phase map.
