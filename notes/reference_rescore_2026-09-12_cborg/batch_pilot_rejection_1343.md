# Rejected CBORG scheduler pilot — 2026-09-12

The CHORUS v7 rep1 rubric10 rating2 session ran from 19:09:47Z to
19:19:00Z. Its original JSON self-reports `claude-opus-4-5-20251101`;
every assistant trace event identifies `claude-opus-5` and CLI modelUsage
maps the requested `claude-opus-5[1m]` selector to that canonical model.
The frozen gate rejected the undocumented identity mismatch. The attempted
34/50 score is excluded, not an accepted repeat rating. CLI-reported usage
was $2.4216595. The controller stopped with no other job launched.

The original prompt, candidate, receipt, trace and controller records are
retained unchanged, including the contradictory self-identification. No
field is corrected, no alias is invented, and the identity gate remains
strict. This is a model self-report inconsistency against the recorded
runtime identity, not independent proof about the provider's model weights.

Issue #1343 registers one fresh original retry using the identical prompt,
definition, input, model selector, CBORG endpoint and budget. The controller
requires an approved registration matching the exact failed-attempt
inventory; any additional or changed attempt invalidates that permission.
Previous launch and review records remain under their original names; the
retry uses separate records. Review and another one-rating pilot must pass
before the queue opens.
