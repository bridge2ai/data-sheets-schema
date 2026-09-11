# API evaluator instrument identity — 2026-09-11

The API evaluator uses expanded rubric system-prompt templates. It does not
send the Claude semantic agent definitions. Its new metadata therefore names
`instrument_kind: api_system_prompt` and records the full SHA-256 of the exact
system string passed to the API. The actual user prompt is hashed separately.
A digest emitted by the judge is retained as
`evaluator_reported_instrument_sha256`; it cannot override the driver-attested
system-prompt digest. Other judge annotations remain intact (#1239).

The instrument resolver preserves that explicit API identity for committed
and uncommitted outputs. It does not substitute an agent revision for an API
prompt. A missing or malformed API digest, or an unknown declared instrument
kind, is unresolved rather than attributed to an unrelated agent. Historical
outputs and their existing attributions are unchanged by this repair.

The agent-version inventory now follows the checked-out HEAD's history.
Previously `git log --all` let an unmerged branch add an instrument to another
checkout's manifest, even with unchanged scores and HEAD. A temporary-repo
regression test verifies that an unrelated agent edit cannot change the
current version inventory (#1240). Deliberately merged definition revisions
still require manifest regeneration, as recorded in #1238.

API-template evaluations and agent-definition evaluations remain different
instruments. The requested reference rescore uses the pinned Opus 5 semantic
agents with the preamble and check-echo protocol; this repair is not a switch
to the legacy API evaluator or a claim that its rubric rules are equivalent.
