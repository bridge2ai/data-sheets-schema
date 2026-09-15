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

Validation at the first head: 236 existing/initial targeted tests passed, followed by
30 updated evidence, execution and native-control tests and the additional
native freeze-command control. Required PR CI passed on `febec9014d425573d4ce71089d221efb99f76327`
(run `34942015635`, all four shards and the aggregate test gate).

Automatic approval review rejected sending the uncommitted nine-file diff to
the external Codex service because it lacked explicit authorization for that
payload and destination. That attempted payload was not sent. After committing,
pushing and opening public PR #1819, a clean clone fetched only the exact
published GitHub commit and the Codex plugin reviewed that public branch.

## Engineering review, round 2 preparation

The external review of `febec9014d425573d4ce71089d221efb99f76327` returned
`needs-attention`. Its four findings were filed as #1820–#1823:

- #1820: validation repair changed artifacts after progress hashes were saved,
  so a subsequent evidence refusal could resume as new generation work.
- #1821: a skipped, truncated or discarded report regeneration could reset
  the one-attempt allowance on later resumes.
- #1822: removing an identity field or moving an indexed ancestor could be
  mistaken for removal of the rejected relationship.
- #1823: the prescribed native provenance command reconstructed renderer 7,
  despite the instruction being registered under renderer 9.

The revised implementation records terminal refusal in the generation's
atomic usage ledger, refreshes progress after validation repair, and checks
refusal before artifact-based phase invalidation. The same ledger consumes
the report-regeneration allowance at call admission, including a transport
failure or unusable response. Explicit new generations archive these controls
with their predecessors; resuming cannot reset them.

Relationship checks map remaining members to original identities and follow
every indexed ancestor. Missing, changed or ambiguous identities stop the
check. The native instruction supplies its complete render specification to
the recorder, and the launch overlay binds `D4D_LAUNCH_INSTRUCTION` to the exact
registered stdin file. The recorder verifies byte-identical replay and
matching inputs before writing. Historical rendering defaults are preserved.
The legacy backfill search remains historical; new native runs carry the exact
registered spec directly instead of relying on guessed backfill parameters.

New controls cover repeated resumes, successful shape repair before refusal,
lost progress and subsequent artifact drift, transport failure, truncated and
discarded report answers, identity deletion and nested ancestor reordering.
A registration-to-recording-to-replay control executes the rendered native CLI
arguments and rejects altered text, renderer, profile, runtime and bundle.
Round-2 review and CI must pass on the revised commit before merging.

Local validation: 125 evidence, generation, report and accounting tests passed;
22 native provenance and historical-recorder controls passed; the two added
regeneration-exhaustion controls passed. After the final persistence change,
all 20 generation/native-recording controls passed again. All 25 native launch
and proxy controls passed with localhost access, followed by all 12 expanded
launch controls, including refusal before billing when the v9 launch-instruction
binding is missing or wrong. The initial proxy test invocation was sandboxed
and could not bind its localhost test server; the rerun used synthetic provider
responses with permitted localhost sockets. No scientific calls were made.

## Engineering review, round 3 preparation

The second Codex review of public commit `73f1f0e4e89ae8b93db9874f964e5b505c9c0812`
found one remaining nested-identity case, filed as #1824. With a declared
`/principal_investigator/name`, a creator wrapper without its own id/name could
retain a rejected person's ID while adopting another person's name and pass
the removal check. The fix binds both id and name in the object containing
the declared identity, alongside any wrapper identities. Eight controls cover
both declaration styles, conflicting or missing sibling identifiers, and
legitimate removal. Before the fix, six controls failed and two already
refused the malformed identity; the review's false-removal case reproduced.
After the fix, all 50 evidence, generation and native-recording controls pass.

## Engineering review, round 4 preparation

The third, incremental review of `73db8d50ef9686d531ed938f6b172d6a4a83195a`
found #1825: a surviving creator wrapper could acquire the rejected person's
id/name while retaining a supported nested person. Matching had captured only
identity fields present in the originals. Four new controls reproduced the
wrapper/intermediate-object bypass; two owner-level controls already refused
the conflict. The revised identity signature binds both presence and absence
of id/name at every object along the declared identity path. Matches require
equal signatures, and missing fields do not count as identity overlaps.
Indexed-list traversal inside an identity selector is refused as ambiguous.
All 57 evidence/generation/native-recording controls passed after this change;
two further controls cover newly introduced owner identifiers that do not
collide with any original identity.
