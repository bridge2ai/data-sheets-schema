# Canary evidence fixes and continuation — 2026-09-15

The active objective is to fix #1801, #1815 and #1816, register a new matched
generation condition, accept new API and agentic canaries, and expand only
after review. Existing sources, v7/v8, historical v9, and every rejected or
stopped canary and evaluation remain unchanged. The v10j outcome is the
starting observation, not an accepted baseline.

## Implementation and review

- Deliver one evidence protocol to both generation arms. Distinguish a
  person's identity from the relationship asserted by its containing field.
  An audit's unsupported-relationship finding requires removing that
  relationship; adding a caveat does not resolve it.
- Bind each source quotation to its named document and chunk. A quotation
  found in another document does not support an attribution. Check each
  attributed clause separately, including assertions of corroboration.
- Make audit and report assertions about original fields, qualifiers and
  headers explicit, with artifact identity, location and the literal text
  asserted present or absent. Check those assertions against the supplied
  original bytes. Evaluate grouped allegations separately.
- Add a separately versioned evidence-assertion checker. Its scope is exact
  evidence binding and declared relationship removal, not semantic entailment
  or completeness of an audit. Independent source review remains required.
- Test with generic multi-document and original/final-artifact controls,
  including valid retained roles, reordered lists, incorrect source identity,
  qualifiers already present, and headers added only during reconciliation.
- Review the combined changes, file and resolve review findings, run the
  required CI, merge and delete the implementation branch.

## Registration and execution

Pin the reviewed code, both arms' instructions, schemas, profiles, existing
source bundles and chunk manifests, runtime/model settings, destinations and
budgets in a new condition. Preserve all earlier registrations. Recompute
the complete spending ledger and remaining authorization before launch; no
automatic whole-attempt retry follows a failed canary.

Run CHORUS API first, then matched CHORUS agentic only after acceptance of
unchanged originals; follow with Kids First API and agentic. Each pair uses
the same source bytes and produces a full record and mechanically derived
core. Review schema/pair consistency, provenance, receipts, grounding, audit
and report claims. A failure stops expansion.

After generation acceptance, register the applicable evaluation canaries:
both presence rubrics, both semantic rubrics and repeats, direct API quality,
field-agent judgments, and applicable grounding/fitness/subtype judgments.
Pin input hashes and definitions, verify agent preambles/check-echo, and use
CBORG for numeric semantic ratings. Establish empirical costs before expanding
the manuscript cohort. Preserve old scores and separate historical adjudication.

## Current evidence

Base main: `c6243db1b3777fca62ff3a541e45a82c1e824eb7`.
Implementation worktree: `/private/tmp/d4d-canary-evidence-fixes`.
The v10j canary was independently rejected; its 38 original files are preserved.
Its ledger reports $29.391638 spent from the additional $200 allocation and
$170.608362 remaining. These figures must be refreshed before any new launch.
No new condition or scientific call has been made at the start of this work.

## Engineering review, round 1

The new renderer 9 is an explicit condition selection; existing renderer
defaults remain unchanged. Both arms receive the same evidence protocol.
The new checker has its own instrument identity and does not relabel the
historical report-claims v8 results.

Offline checks caught and fixed native instruction replay using computed
destinations instead of saved destinations. Local adversarial review then
reproduced #1818: resuming a failed audit added a mock model call. The fix saves
produced phases before refusing them, rechecks failed evidence without a new
call, persists the one-time report-gate history before failure, and rechecks
completed runs from their attested originals. All three refusal/resume controls
now pass. A further control confirms completed-run rechecks make no calls or
artifact changes. The generated native freeze command was executed offline
with spaces and apostrophes in paths; it preserves exact CRLF/LF bytes, prints
their hashes and refuses to replace existing originals.

Validation so far: 236 existing/initial targeted tests passed, followed by
30 updated evidence, execution and native-control tests and the additional
native freeze-command control. Required PR CI is still pending.

Automatic approval review rejected sending the uncommitted nine-file diff to
the external Codex service because it lacked explicit authorization for that
payload and destination. No review payload was sent. Local adversarial review
and testing continue; no external review result is claimed.
