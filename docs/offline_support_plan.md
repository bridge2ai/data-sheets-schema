# Offline typed support and fitness plans

`d4d evaluate support-plan` prepares the offline deliverable in #3341 for the
common-instrument run in #2929. It makes no provider calls, estimates no empirical
accuracy, and does not authorize execution. Run it from a complete Git checkout:

```bash
d4d evaluate support-plan \
  --roster notes/reference_rescore_2026-09-11/manifest.json \
  --profile bridge2ai \
  --output /tmp/d4d-support-plan
```

The output directory must be new and its parent must exist. The command deduplicates
primary rubric jobs by input while rejecting conflicting identities. The reference
roster's `pinned_files` hashes bind the full records. A new roster can use the same
format, including an explicit `provenance` path per job for nonstandard layouts.
The default provenance location is
`data/d4d_concatenated/{method}_core/{label}/{project}_provenance.yaml`.
The provenance's project, method and label must agree with the roster.

Every record, provenance file, original support bundle, available rubric join result,
merged schema/import dependency, vocabulary, complete specification and system prompt
is copied into content-addressed `artifacts/`. The manifest records planning-code
hashes and commit, explicit profile selection, model-selection basis, same-family
status, original paths and hashes, and any recovery commits. Historical reference
records and bundles are recovered from full Git history by their recorded hashes
when current bytes have drifted. **Originals are never rewritten.** Supplied
provenance SHA256 pins are honored before reading identity or bundle declarations,
recovering matching bytes when
necessary. Historical rosters without that pin explicitly record the basis
`captured_current_unpinned_by_roster`; a captured snapshot is not a claim that the
older roster bound its lineage. Git reads ignore inherited repository/worktree/index
overrides, so code and input commit identities refer to their intended roots.
A missing or unrecoverable pin fails the build. A shallow clone must first obtain full history;
a sparse checkout must materialize the roster, provenance, schema, current bundles
and referenced rubric result paths. Unavailable rubric results are listed as an
additional blocker rather than silently described as a completed join.

The plan retains every populated **top-level field** on both axes. Zero and false
are populated. Nested list items are still one field request, as in the current
v2 judge; resolving #3342 may change these counts and requires a new plan. Every
target belongs to its own record and value, with its own judgement context.
Value hashes use `typed-yaml-v1`: recursively tagged scalars, mappings and lists,
including dates and timezone-bearing datetimes. This distinguishes a native date
from its quoted string spelling and does not change the live judge's YAML prompt
or existing cache keys. No historical cache reuse or replicate propagation is credited. Intended result/cache
paths are reserved in the manifest; the planner does not create verdict files.

Inspect an exact target without any model call:

```bash
python -c 'import json; m=json.load(open("/tmp/d4d-support-plan/manifest.json")); print(m["targets"][0]["id"])'
d4d evaluate support-request --plan /tmp/d4d-support-plan --target 'ID_FROM_ABOVE'
```

The request command verifies artifact and full-request hashes before printing the
reconstructed arguments. Source text is stored once and referenced by multiple
recipes. These are the exact shared request-builder arguments at
`_call_with_retry`, **before provider transport**, encoded with the plan's canonical
JSON convention. They are not claimed to be SDK wire bytes. Provider routing,
reasoning policy, output-limit adjustments, retries and accounting still need a
separate execution registration. Transport must be reviewed before authorizing a
run. Materialization needs neither the original files nor the current prompt text.

The manifest always blocks paid use on #3342 granularity, #3343 independent
empirical calibration, transport registration and paid authorization. Software
tests and this plan cannot clear these blockers. Positive and supported negative
controls must be independently curated and measured before the cohort is judged.
A proposed canary selects the first sorted record for each project; it is a plan,
not a completed canary. Existing audit registrations, frozen caches and protected
worktrees are not modified or borrowed as budget authority.

## Estimates and local prices

Each target's input estimate is `ceil(canonical request UTF-8 bytes / 4)`. This is
an explicit heuristic, not a model tokenizer or guaranteed spend bound. The output
ceiling uses `--max-tokens` (default 8000), including whatever reasoning the selected
transport charges within that limit. One attempt per target is assumed; retries
are excluded. The three scenarios are:

- **uncached:** all input charged as ordinary input;
- **cache miss on every request:** every support prefix charged as cache write;
- **warm within record:** one support-prefix write per record and subsequent
  field requests as reads, with no reuse assumed between records.

The support prefix comprises the system prompt and source block. Actual cache
support, minimum size and expiry are unverified. Fitness has no cached source
block. Output ceilings are the same across these scenarios. Canary usage must
replace these assumptions before estimating a full paid fanout.

Dollars remain `null` when prices are missing. Pass `--model` for an explicit model;
otherwise `evaluation_model_settings()` resolves and records the generation-default
basis. An optional `--prices path.json` accepts this shape:

```json
{
  "model": "THE_EXACT_SELECTED_MODEL",
  "currency": "USD",
  "per_tokens": 1000000,
  "source": "Your verified local price source",
  "as_of": "YYYY-MM-DD",
  "rates": {}
}
```

Fill `rates` with the known nonnegative numeric rates for `input`, `output`,
`cache_write` and `cache_read`. Omit unknown rates; a scenario requiring an unknown
rate remains unknown, not zero. The planner pins the file and labels it user
supplied and unverified; it never retrieves prices or imports an old study budget.
Keep generated plans local until their source contents and publication scope have
been reviewed. Planning does not complete the empirical acceptance criteria of
#2929 or #3343.

## Nested version 2

The default remains historical `d4d-support-plan-v1`. Opt in to the draft #3342
nested target contract with a fresh output directory:

```bash
d4d evaluate support-plan \
  --plan-version 2 --artifact-kind full --class-name Dataset \
  --roster notes/reference_rescore_2026-09-11/manifest.json \
  --profile bridge2ai \
  --output /tmp/d4d-nested-support-plan
```

Version 2 requires an explicit artifact kind (`full`, `core`, or `collection`).
A core plan must select `--class-name CoreDataset`; the default full Dataset
class is refused for core. A collection or external root requires its explicitly
selected `--class-name` and `--schema`. A roster job's optional `artifact_kind`
must agree, as must the corresponding provenance output path when declared.
One plan uses one kind/class/schema/profile. Records are not unwrapped and paths
address their exact pinned bytes.

The required profile selects its existing pinned vocabulary resource, ignoring
ambient profile selection. `--vocabulary FILE` can explicitly override that
snapshot for version 2 only. Its YAML must contain a `vocabularies` mapping from
registry names to nonempty identifier/label mappings. The planner records the
override basis and hashes the entire file. No registry is fetched. Missing
`values_from` vocabularies remain named blocked paths; they are not replaced by
empty authoritative lists. Both nested support and top-level fitness use the
same captured vocabulary and schema closure. The nested schema view is independent
of mutable shared LinkML caches, so capture order cannot alter its identity.

The output format is `d4d-support-plan-v2`. It uses `grounding_v3` for the draft
[nested support contract](nested_support_targets.md) and keeps `fitness` as a
separate top-level measurement. Counts distinguish support `relationship_edge`,
support `attribute_value`, and top-level fitness. The request count is an
accounting total, not a pooled measurement denominator. Every nested target
records its many-to-one root-field mapping and the corresponding fitness target
id; a top-level fitness verdict must not become multiple nested verdicts.

Each record has a complete hashed target inventory, including its deduplicated
specification catalog, all blocked pointers/codes, and explicit omissions from
projected context. Every request pins its target/context/specification identities
and reconstructs from a content-addressed recipe through the same
`d4d evaluate support-request` command as version 1. The request's SHA-256 uses
the planner's canonical UTF-8 JSON encoding, not an SDK wire encoding or a cache
key. Raw record, provenance, original bundle, schema/imports, vocabulary,
instrument source files and available rubric join outputs are separately pinned.
Recovery uses the same original-hash checks as version 1 and never rewrites the
source repository. Unknown top-level fields remain explicit blocked support
and fitness paths; malformed nested shapes remain blocked support paths while
their declared top-level field can still receive a separate fitness question.

The three token/cost scenarios are reported both overall and by measurement
stratum. A warm support scenario credits one source-prefix write per record,
then reads across both nested support kinds. Fitness has no cached source block.
Estimates still use a byte-count heuristic, optional local prices and a requested
output ceiling; they are not measured usage, a transport guarantee, or a spend
cap. No judgement-cache reuse is credited.

Planning remains offline. Downstream software is available through the explicit
[saved-response protocol](nested-support-results.md),
[registered execution](nested-support-execution.md),
[captured calibration evidence workflow](../notes/support_calibration_2026-10-07/README.md)
and [fitness/support index](top-level-fitness-results.md). These commands are
separate opt-ins; preparing a plan does not invoke them or reuse judgement caches.
The version numbers name different contracts: planner v2 uses `grounding_v3`,
while saved nested-support results and execution each have their own v1 protocol.

Context-projection review, independently adjudicated scientific controls, #3343
empirical calibration, an explicit per-run transport/decision registration and
actual paid authorization remain requirements. Software availability does not
clear a captured plan's readiness blockers. Actual unresolved target paths and
missing rubric join artifacts add their own blockers. Schema validation of the
record is separate from this inventory; parent #3342/#2929 work remains open.
