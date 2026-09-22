# Native audit continuation

A native generation can stop at the transport after producing and freezing a full
record, a deterministic core, and its receipt. These controls run Phase 3 in a new,
separately registered native session using those unchanged originals. They do not
turn the stopped generation into a completed attempt.

`prepare` works offline. It replays the actual parent instruction and tool history,
checks source identities, successful receipt checking, core derivation and the
original snapshot, and binds the confirmed accounting checkpoint. It renders the
shared generic-v9/renderer-14 audit contract by default, with the complete frozen source bundle,
full/core originals and source-review inventory. No operator review findings are
supplied to the model. The new wrapper identifies the session as audit only and
makes its output and exact validator command explicit.

The execution registration pins the code commit, executable, Python environment,
model, profile, schemas, prompts, inputs, instruction, budget and predecessor.
`python -m audit_controls.prepare --help` describes the required paths. Run from the
execution checkout with `src`, this directory's parent, and `native_controls` on
`PYTHONPATH`. Preparation creates an exclusive new directory and makes no provider
calls. Review the registration and cost plan before execution.

On the LBL network or VPN, a new condition can select CBORG's documented direct
route with `--provider-base-url https://api-local.cborg.lbl.gov` and
`--provider-ca-bundle PATH`. Obtain the CA chain from an independently verified
trust source and review it before registration. The bundle is pinned with the
other inputs. Both token counting and native streaming use the same client with
certificate-chain and hostname verification, redirects disabled and no environment
proxy or trust overrides. An omitted server intermediate may be supplied in this
bundle alongside its trusted root; the server leaf must not become a trust anchor.
Historical public-route conditions retain their original configuration. Successful
TLS and catalogue checks alone do not establish streaming or canary success.

For a new condition that needs more time for response headers, preparation accepts
`--native-api-timeout-ms 3600000`. This pins a one-hour local native SDK timeout in
`native_runtime.api_timeout_ms`; it must be a positive integer within the registered
whole-job deadline. The controller sets `API_TIMEOUT_MS` only from this field and
ignores an ambient value. Omission preserves the native client's historical
default. The upstream read timeout and whole-job deadline still apply. This changes
neither provider keepalive settings nor model requests, and does not make an
interrupted charge complete. Preserve stopped conditions and register retries
separately.

A new condition can register a bounded in-attempt stall policy with
`--native-stall-policy PATH` (#2150). Without it, the first provider stall ends the
whole attempt, as it always has. The JSON file names the policy kind
`bounded_in_attempt_v1`, `count_attempts` from 1 to 5, `max_stall_debits` from 0 to
10, and an `authorization`. The authorization quotes the maintainer's standing
approval: the exact response, the request it answered, when it was recorded, and
`authorized_max_stall_debits`, which must equal `max_stall_debits`. It is required
whenever any debit is allowed and must be `null` when none is. The file is read
strictly: duplicate keys, a JSON `null` and an unreadable file are refused before the
destination exists. Its content is copied into the manifest, which the registration
hash binds; the file itself is not pinned.

The policy does two things. Token counting is repeated up to `count_attempts` tries,
only after a timeout, a dropped connection or a provider 5xx. A count costs nothing,
so repeating one carries no charge ambiguity. Each try has a two-minute total deadline, the
pause between tries is a few seconds and ends at once when admission closes, and no
retry starts or writes evidence after that. A paid request that stalls after it was
sent, and before any response byte reaches the native client, is counted at its whole
reservation, and the ledger row says so: `settlement_basis` is
`registered_stall_policy_full_reservation_debit`, the provider charge is unconfirmed
and unknown, and nothing is released. The reservation is computed from the counted
input at the higher price plus the whole output ceiling, so it bounds the fee by
construction; a debited row cannot be checked against actual usage, because none
arrives. The proxy then answers the client with a retryable status, and the client's
own retry continues the same session. The ledger row carries the stall evidence,
`stall.json` beside the request repeats it and records that a reply was attempted,
and the terminal result lists the debited requests under `stall_debited_requests`.

A stall counts only when the exchange failed after the request was sent: a provider
5xx, a read or write timeout or error, or a malformed or dropped response. A provider
status below 500 is never a stall, whatever fails afterwards. A connection that was
never made sent nothing, so it stops the attempt as before instead of spending the
allowance during an outage. A failure after response bytes were relayed, a closed
admission and every budget refusal also stop the attempt as before. So does the stall
after the registered maximum, which leaves its reservation pending for the
maintainer's request-specific decision.

Debits need the proxy to see a stall before the client gives up. The native SDK
timeout must therefore cover the pre-header deadline, the bounded
token-count tries with their pauses and a minute of margin,
and the native fetch idle timer must be registered off. With three count tries that
is 455 seconds above the read bound. The policy is audit-only: generation, Phase 4
and the evaluations refuse it. `native_controls/probe_native_stall.py` drives the
real pinned executable against a scripted upstream that stalls, with no provider
contact, and shows the client retrying to completion.

Under this policy, counting and paid streaming use separate killable I/O workers
(#2159). Counting has one total deadline, including process startup, DNS, TLS and
the complete response. A paid request has one deadline until response headers,
equal to the selected read limit plus the 20-second connect allowance. This also
bounds pooling, writing and partial headers. The worker is killed and reaped before
the parent retries or debits a timed-out request. Expiry before a send witness
stops without a stall debit. After headers, the selected read-inactivity limit
applies; a failure after relay remains terminal. A provider 5xx is classified from
its status without waiting for an error body.

Workers receive credentials, registered transport settings and exact request
bytes through anonymous pipes, not command-line arguments, environment variables
or files. They hold no ledger or evidence state. The parent retains admission,
accounting and evidence ownership, and cancels the workers during shutdown. The
existing clients and cleanup order remain unchanged when the policy is absent.

The native client's fetch layer has a separate idle timer. A new condition can
select `--native-api-force-idle-timeout false` to disable that timer while waiting
for local-proxy response headers. This requires an explicit bounded
`--native-api-timeout-ms`; no other override value is accepted. The registration
pins `native_runtime.api_force_idle_timeout: false`, and only that field can set
the child's `API_FORCE_IDLE_TIMEOUT=false`. Ambient values are ignored. Omission
preserves the previous behavior. The SDK timeout, native event-stream watchdog,
upstream read timeout and whole-job deadline still apply. This local setting does
not change CBORG keepalive policy or authorize an automatic retry.

For a separately reviewed native audit, `--native-upstream-read-timeout-seconds`
sets the optional top-level `native_upstream_read_timeout_seconds`
([#2147](https://github.com/bridge2ai/data-sheets-schema/issues/2147)). It must be a
positive integer strictly below an explicit `--native-api-timeout-ms`, which
remains bounded by the whole-job deadline. There is no new default: omission
preserves the original stream call and its 1,800-second upstream read timeout.
The override changes only the raw generation request's read timeout, including
both the wait for response headers and gaps between body reads. Token counting
keeps its original timeout; connect remains 20 seconds, write/pool 1,800 seconds,
and TLS verification, redirects, environment isolation and zero retries are unchanged.

This field is audit-only and is not copied into Phase 4 or evaluation settings.
Both generation arms reject its presence, including `null`, before mutable setup
([#2148](https://github.com/bridge2ai/data-sheets-schema/issues/2148)). Non-audit
transport policy remains unchanged. Leave deliberate slack below the SDK
timeout: token counting/preparation also consume the outer request's time. A
larger read limit does not guarantee a response, address streams kept alive by
keepalives, or establish an interrupted request's charge. Retain the existing
job/watchdog bounds, stopped evidence, accounting rules and independent review.

`python -m audit_controls.native --registration REGISTRATION --review REVIEW`
requires a review binding that registration to its exact code commit, successful CI
and sole allowed job. It uses the same CBORG transport and shared budget ledger as
native generation. The native child receives only the local proxy token. Its tools
can read the registered files, write its isolated audit output, and execute the
exact validator. It cannot alter the original records or source evidence.

The validator claims an exclusive receipt before checking the JSON. It checks
the selected evidence protocol and all inventory values against the actual originals and source
bytes. Failure terminates further admission. A passing file alone does not permit
a subsequent request: the controller must also observe the typed successful tool
result. The audit cannot be repaired after validation starts. An unknown provider
charge retains its reservation and stops the attempt.

### Bounded grammar drafts (protocol 6 / renderer 18)

For a new audit condition, `--draft-audit-grammar` explicitly selects protocol 6,
renderer 18 and an `audit_drafting` block using `bounded_draft_grammar_v1` (#2178). It is mutually
exclusive with the earlier scientific selectors and `--staged-audit-output`.
Omission preserves their behavior and instructions. This option does not alter
any rejected audit or make the original generation a renderer-18 run.

The native agent writes a complete audit into a contiguous prefix of at most 64
registered UTF-8 parts, each no larger than 32,768 bytes. Its exact grammar command
preserves those bytes and checks the draft's JSON shapes, enums and internal
declaration/link consistency. The pure parser receives only the draft bytes;
ordinary registration and pin verification may read registered inputs. No source
content, expected scientific judgments or independent review findings enter the
grammar feedback. The report contains at most twenty fixed error codes and
structural draft locations. A grammar pass proves neither coverage nor support.

Only a completed first grammar check with a negative grammar verdict permits a
second complete draft. Both drafts and every part remain immutable. A failed
helper, missing typed result, incomplete preservation witness, changed evidence
or second negative grammar verdict stops the attempt. The mode permits one
format correction, never unlimited attempts or a budget reset.

The first grammar-passing draft must be sealed next. Sealing copies its exact
concatenated bytes once to `audit.json`; it does not normalize or repair content.
The only following tool is the existing single terminal source/evidence validator.
Every failed source check remains terminal, and independent scientific review
remains mandatory even after both checks pass. Keep all draft/check/seal evidence
in the accepted audit's closure before preparing Phase 4. Phase 4 inherits the
accepted scientific instrument, but generation, Phase 4 and evaluations reject
the audit-only drafting selector. Historical conditions remain unchanged.

### Explicit schema semantics (protocol 6 / renderer 19)

For a new audit condition, combine `--schema-semantic-context` with
`--draft-audit-grammar` to select `frozen_pair_schema_semantics_v1` (#2182).
The other scientific selectors and staged-output mode remain mutually exclusive.
This is a new rendering instrument on the frozen original pair, not a claim
that the original renderer-14 generation used the new guidance. Protocol 6,
the terminal source checks and independent scientific acceptance are unchanged.

The shared audit renderer adds deterministic, source-free schema definitions
for the original full and core records' populated structure and required
siblings. Complete class and induced-slot meanings, ranges, cardinality and
vocabulary guidance come from the exact registered schemas and their imports.
The existing schema digest stays byte-identical. All eleven input roles stay
unchanged: the registered instruction captures the derived supplement, and
the new helper plus actual schema-import closure are pinned only for the new
transition. Guidance describes schema meaning; it cannot establish dataset facts.

With `--persistent-audit-contract`, renderer 19 omits only the duplicate exact
protocol appendix from the user instruction, retaining the exact protocol in
the checked persistent system prompt and the existing shared instruction.
Without persistent delivery that appendix remains. Earlier rendering versions
keep their existing bytes. General generation launches cannot select renderer
19; the new context is prepared for the audit continuation only.

Phase 4 inherits protocol 6 / renderer 19 and must preserve the accepted helper
identity and complete audit/draft pins. It does not inherit an active audit
drafting or schema-context selector. Its ordinary schema presentation remains;
the Phase 3 supplement describes the original pair and makes no claim to cover
new fields introduced during reconciliation. Evaluation instruments remain
unchanged. This supplement does not guarantee a complete or correct audit.

The sequence lock is derived from the immutable parent ledger location. Copying a
registration or a reconciliation receipt cannot create a second budget lineage.
Each successor must carry the settled current tip. The shared budget is not reset.

If the current audit stopped with an unresolved charge, preserve its ledger and
stopped result. After the request match and complete charge are confirmed, create a
separate reconciled checkpoint. Supply it with `--continuation-checkpoint`, plus
`--continuation-source-registration` and `--continuation-reconciliation-receipt`.
The new registration pins the predecessor registration, original ledger, stopped
result and confirmation receipt. Admission verifies that the checkpoint changes
only that confirmed pending request and belongs to the current sequence tip. It
does not erase the stopped attempt, invent final usage or accept its audit.

If a user explicitly authorizes counting the entire unresolved reservation against
the budget, a separate `user_authorized_full_reservation_debit` receipt can support
the same continuation bridge. This is a conservative budget debit, **not** a
confirmed provider fee. It binds one exact stopped audit request, its payload hash,
the unchanged source ledger/result, the user's exact authorization and quoted
request, and an accounting-observation hash. `budget_debit_usd` must equal the full
positive reservation; `released_excess_reservation_usd` must be zero. Both this
variant and confirmed-provider accounting require the common runtime closure
check described below.

The receipt and derived row retain `provider_charge_confirmed: false`,
`provider_charge_usd: null` and `provider_usage_is_final: false`. Confirmed-charge
fields are forbidden in this exception receipt. The derived checkpoint books that
amount in `cost_usd` with `settlement_basis: user_authorized_full_reservation_debit`;
its provenance uses `budget_debit_usd`, never `confirmed_charge_usd`. All prior rows,
partial observations, caps and stopped-attempt metadata remain unchanged. Preserve
the original pending ledger and stopped result. Counting this debit neither clears
the transport failure nor accepts an audit, and never authorizes a budget reset or
an additional attempt beyond the existing approval.

Stopped execution results include `stop_source` and `runtime` evidence. Runtime
evidence records whether the proxy was initialized and its bounded shutdown
completed. `unfinished_handlers` is a count only after that shutdown; otherwise it
is `null`. A late handler failure does not replace an earlier controller stop.

### Later runtime closure

Both accounting variants accept a completed shutdown with an integer zero count.
A nonzero count after completed bounded shutdown is historical evidence: preserve
it even after its processes end. A later host reboot can establish local process
closure through a separately reviewed supplement ([#2136](https://github.com/bridge2ai/data-sheets-schema/issues/2136)).
It cannot establish provider-side completion, a final charge, audit completion, or
new spending authorization.

The existing accounting receipt may include `runtime_closure: {path, sha256}`.
Its canonical absolute path names a separate JSON proof with exactly these fields:

```text
schema_version: 1
kind: independently_reviewed_host_reboot_closure
source_registration_sha256: SHA256 of the original source registration
source_ledger_sha256: SHA256 of the unchanged pending ledger
stopped_result_sha256: SHA256 of the unchanged stopped result
job_id: original job ID
billing_attempt: original registration SHA256 + ':' + job ID
execution_repository: original registered execution checkout
execution_commit: original registered Git commit
observation: {path, sha256}
launch_observation: {path, sha256}
review:
  verdict: accept
  reviewer: independent reviewer's identity
  observer: OS evidence collector's distinct identity
  reviewed_at: timezone-aware ISO timestamp
  same_execution_host: true
  host_identity_basis: independently_reviewed_local_provenance
  historical_host_identity: not_recorded
  basis: concrete provenance connecting this launch and OS observation
```

This initial contract supports legacy launches without a recorded host identifier.
The reviewer must inspect the collector's provenance and explicitly attest that
the OS observation comes from the execution host. Software checks identities,
hashes and chronology; it cannot authenticate the people named in this local
review or independently prove physical host identity. A matching pathname or PID
does not supply that missing fact. Do not invent a historical host identifier or
approve the supplement when same-host provenance cannot be established.

The launch observation must contain matching `registration_sha256`, `job_id`,
`execution_repository`, `repository_commit`, `launch_observed: true`, and a
`recorded_at` timestamp between the source result's `started_at` and `finished_at`.
The OS observation must retain macOS `kern.boottime` output in `sysctl_boottime`,
its normalized `boot_at`, `boot_session_uuid`, and `observed_at`. The raw boot time
must be strictly after the original stopped result, followed by observation and
independent review in that order, all at or before admission time. Observer and
reviewer names must be whitespace-trimmed and differ after case normalization.
Microseconds are used from the raw output; the
normalized timestamp may preserve those microseconds or truncate to whole seconds.
A missing process, vanished checkout, or unknown tool handle alone is insufficient.
Other OS proof formats are not silently inferred.

Preparation discovers these references through the existing continuation receipt
and pins the proof, launch observation and OS observation. No extra CLI override
is needed, and these administrative documents are not delivered to the model.
Admission rechecks every pin and semantic binding for both financial variants.
The copied accounting row and `reconciled_from` retain `runtime_closure_sha256`;
all original accounting and runtime evidence remain unchanged. A closure proof
cannot replace the exact request's financial authorization or confirmation.

A successful result is `completed_pending_independent_review`. Scientific review
must assess grounding and audit completeness separately. Reconciliation, report
production, final pair acceptance and evaluations require subsequent registered
stages. Preserve the stopped source run, rejected audits and all billing evidence.

For a new condition, `--context-recovery` preserves exact instruction and input
bytes as registered JSONL files under `recovery/`. The persistent system prompt
identifies the current stage, output and exact validator, and gives the recovery
index path and bounded Read recipe. In that index, `instruction` is the current
authoritative task; `parent_instruction` is historical reference. The index itself
uses bounded frames, so long original lines cannot make its bootstrap Read too large.
Each physical frame is at most 1,000 UTF-8 bytes, and each prescribed Read covers one
exact range of at most 12 lines. The original scientific instruction and input bytes
remain unchanged. Omission preserves the previous preparation and system prompt.

Recovery reads are optional. A completed prescribed recovery Read must have exact
typed file metadata and complete raw and numbered content; a truncated or
persisted-only result stops the attempt. Requests outside the registered frame
ranges are denied and listed as unprescribed explorations. Successful ranges are
recorded without asserting that the whole instruction was recovered or remains in
the current context after compaction. The native 200,000-token context limit and
automatic compaction remain unchanged. No full-context reacquisition gate is added.
The pinned native runtime also makes auxiliary requests with its own system prompt;
this feature does not reject those requests or claim every request carries the
registered system. Actual scientific-session delivery and final scientific quality
still require independent review.

### Persistent audit contract

For a fresh audit condition, `--persistent-audit-contract` registers
`audit_contract_context: {"kind": "persistent_protocol_v1"}`
([#2164](https://github.com/bridge2ai/data-sheets-schema/issues/2164)). The native
system message retains the exact registered evidence protocol and selected
audit contract, including its JSON example. Without a separate protocol upgrade,
this remains the unchanged renderer-14 contract. This keeps their field
types, verdict vocabulary and evidence rules in the persistent instruction
alongside stage and recovery controls. It adds no dataset-specific guidance.

By itself, this option leaves the original instruction, source bytes, scientific
instrument and terminal validator unchanged. Omission preserves historical rendering and leaves the
optional runtime helper outside the required pin closure. The selector is
audit-only; generation, Phase 4 and evaluations reject
its presence, including null, and successor preparation does not inherit it as
an active setting. Prior registrations remain pinned as historical evidence.
The option is compatible with bounded context recovery and staged audit output.

This is a delivery change, not proof of successful model compliance after
compaction. Audit11 assembled its output but failed the existing contract check;
its output and validation are preserved. A new registration and independent
review are required before another attempt. The option neither repairs rejected
outputs nor changes how anonymous list removals are validated.

### Explicit scientific protocol upgrade

For a new audit on a frozen renderer-14 generation pair,
`--upgrade-evidence-protocol` selects protocol 4 / renderer 15
([#2165](https://github.com/bridge2ai/data-sheets-schema/issues/2165)). It records
`scientific_contract_transition: {"kind": "frozen_pair_protocol_v4"}`. This changes
the scientific action contract; it is separate from persistent delivery and can
be combined with `--persistent-audit-contract`, recovery and staged output.
Omission preserves protocol 3 / renderer 14. A new version without the explicit
transition, or a malformed transition, is refused.

Preparation first replays the original renderer-14 instruction and Phase 1/2
history exactly. It then constructs a separate renderer-15 audit specification.
Original full/core records, source inventory, bundle, schemas, receipts and parent
instruction remain unchanged. The active protocol input becomes v4; both old and
new protocol/code identities remain pinned. The parent instruction and v3 text
are historical provenance, while the selected v4 contract governs current audit
actions. This does not regenerate the pair, rewrite a failed audit, or claim the
original generation used the new instrument. Unrelated scientific code retains
its inherited equality checks.

Protocol 4 adds `remove_relationship` with exactly `path`,
`match: "anonymous_structure_v1"` and `original_full_sha256`. Copy the digest from
the registered original-full inventory; the checker verifies the actual original
bytes. The original index locates a member, never identifies its final position.
The initial mode supports a list reached through dictionary keys and a target
without own or nested stable-identity keys, including invalid or null ones.
Every original member needs a nonempty, unique typed structural signature.
Only the existing narrative-text fields are excluded; structured values and
nested list order remain bound. Final survivors must match exactly, once each;
undeclared deletions, additions, replacements and reintroduced targets fail.
All-selected removal leaves `[]`, not a missing container. Duplicate signatures,
indexed ancestors, overlapping or mixed actions in that container, unsupported
scalar types and nonfinite numbers fail closed. See the exact
[protocol](../../../src/download/prompts/evidence_protocol_v4.md) for the full rules.

Admission tests the declared batch with an in-memory projection; Phase 4 rechecks
actual final bytes under the accepted version. Neither test proves the scientific
claim that a relationship is unsupported or absent elsewhere in the record.
Complete source review and independent acceptance remain required. An accepted
v4 audit passes its version and exact helper/protocol identity to Phase 4; fresh
generation and evaluations reject this continuation-only selector.

### Bounded native audit output

For a fresh condition, `--staged-audit-output` selects the registered
`audit_output.protocol: raw_utf8_parts_v1` mode
([#2144](https://github.com/bridge2ai/data-sheets-schema/issues/2144)). This addresses
a single large native Write exceeding a response's output limit. It does not
change the source bundle, scientific/evidence instrument, model limits, budget,
or independent acceptance requirements. Historical registrations omit the field
and retain the original whole-audit Write and replay behavior.

The model writes a nonempty contiguous prefix of 64 registered paths,
`output/audit-parts/000001.txt` through `000064.txt`, in that order. Each part is
nonempty raw UTF-8, at most 32,768 bytes. Every Write must complete with its exact
typed result before another tool. Registered Reads, including optional recovery
reads and completed output parts, remain available between completed Writes.
Completed parts cannot be rewritten. The native pretool policy grants only these
exact Write destinations and byte limits; the final `output/audit.json` is written
by the trusted assembler.

After the last part, the sole registered assembly command is:

```text
REGISTERED_PYTHON -m audit_controls.output_parts --registration REGISTRATION
```

The assembler concatenates the exact part bytes without separators, JSON parsing,
normalization, inference or repair. Individual parts need not be complete JSON.
Gaps, extra/hidden files, invalid UTF-8, aliases, oversized parts, stale receipts,
changed parts and existing final output fail closed. A failed assembly cannot be
retried or repaired in that attempt. The complete roster and hashes remain in the
exclusive `assembly.json` receipt outside native-writable output. A final hardlink
at `assembly_ready.json` witnesses completed output/receipt writes, closes and
fsyncs; no fallible persistence step follows publication. If that witness is lost
on reboot, review is required: reentry does not recreate it. Failure receipts are
best effort; missing readiness and missing typed success remain blockers even if
a failure receipt could not be saved.

Bash stdout contains only a compact receipt digest, part count, final audit
digest/byte count and registration/job identity. Native history binds the entire
part roster to real successful Write results, then binds that compact typed
assembly result to the retained receipt and exact final bytes. Paid admission
waits for observed part/assembly results during the existing bounded stdout-flush
race; a file or receipt alone cannot release it. After assembly starts, only the
existing single terminal validator may run, after successful typed assembly.
Before assembly, every admission checks the exact completed-part roster,
including its initially empty state and while a registered Read is pending;
premature final output or assembly receipts also block admission
([#2145](https://github.com/bridge2ai/data-sheets-schema/issues/2145)).
That validator retains its original scientific semantics and also checks staged
assembly provenance. No whole-file native Write is required in this mode.

Phase 4 consumes the same accepted final audit. Preparation verifies and pins
the accepted result's part/assembly evidence before carrying it forward; later
admission rechecks it. These administrative part/receipt paths are not added to
model-readable inputs, and Phase 4 does not inherit the audit-only output mode.
Neither successful concatenation nor validation supplies scientific acceptance.

## Source-manifest metadata evidence (protocol 5 / renderer 16)

A fresh condition can select `--source-metadata-evidence` to register
`scientific_contract_transition: {"kind": "frozen_pair_protocol_v5"}`.
It is mutually exclusive with `--upgrade-evidence-protocol`, whose existing
meaning remains protocol 4 / renderer 15. With neither option, historical
protocol 3 / renderer 14 behavior remains unchanged. New general API and
native generation can explicitly select renderer 16 separately; the
continuation selector remains audit/accepted-finalization specific.

The new instrument retains the relationship proofs and once-only terminal
check. It adds `source_review v2` support for a finite projection of the exact
registered source manifest: source identity and processed filename, source
type, effective priority, and supported capture/supersession metadata. The
projection is bound to the manifest's raw-file SHA256 and selected project.
It exposes no arbitrary manifest pointer, curator note, curation history or
dataset description. Provenance assertions have a separate discriminator and
cannot be mixed with document quotations in one atomic claim. Their authority
is the source declaration, not the truth of dataset facts. No whole-field
metadata exemption is added.

Both arms receive the same protocol and projection. Native audit checking
derives the project from the pinned parent job and the manifest from its
exact input identity. API audit admission, reconciliation and report checks
pass the same authority. An explicit absence of a source manifest still
permits document-only review, but no source-manifest assertion. Changed or
missing supplied bytes, unknown sources, invalid types and unsupported fields
cannot establish metadata evidence. Independent review still establishes
entailment and rejects metadata used as a substitute for dataset evidence.

The protocol also spells out the existing output grammar: a finding has one
removal object, not an array; its `review_paths` contains only values with a
revision judgment. Supporting context belongs in evidence assertions. These
clarifications do not relax the checker or authorize repair after validation.

The original generation remains at its recorded protocol/render version.
Accepted protocol-5 audits pass the matching scientific contract and helper
bytes to Phase 4, which preserves the original generation lineage. Generation
and evaluation refuse an active continuation selector. Audit operational
options are not inherited. Old registrations, prompts, stopped outputs and
scores remain unchanged; a fresh registration and independent review precede
each launch with the new instrument.

## Explicit claim clarification (protocol 5 / renderer 17)

For a fresh audit condition, `--clarify-source-claims` selects protocol 5 /
renderer 17 and the distinct transition
`scientific_contract_transition: {"kind": "frozen_pair_claim_clarification_v1"}`.
This option is mutually exclusive with the two earlier upgrade options.
`--source-metadata-evidence` continues to select 5/16,
`--upgrade-evidence-protocol` continues to select 4/15, and omission still
selects 3/14. An accepted audit carries its selected scientific contract into
Phase 4; the frozen generation identity is preserved separately.

Renderer 17 clarifies existing rules with generic examples: claim text copies
the decoded scalar rather than its serialization delimiters; support must
match the claim's subject, scope and status; an undated source does not
establish chronology; and a supported fact must fit the actual schema field.
Literal quotation marks that belong to a scalar remain significant. Distinct
clauses and their statuses need separate judgments. Source priority supplies
neither observation dates nor evidence for a dataset relationship.

The same clarification accompanies audit, reconciliation and report phases in
both arms, including the native persistent audit contract. It changes prompt
identity, not protocol-5 grammar or validator semantics. Earlier rendered
prompts and all protocol bytes remain unchanged. The clarification does not
guarantee semantic correctness: independent scientific review is still
required, and previously rejected outputs remain rejected. Select it only
through a fresh registration with its code and rendered instructions pinned.

## Fresh-context audit batches (protocol 7 / renderer 20)

A new registration may select `--audit-batches PATH` (#2192). The JSON file must
contain `kind: fresh_context_integrated_v1` and a positive
`worker_total_cap_usd` strictly below the audit's attempt cap. Optional positive
integer limits are `max_paths` (default 96), `max_inventory_bytes` (default 16384)
and `max_workers` (default 16). Limits are deterministic packing constraints;
an indivisible field that cannot fit is rejected before execution. This mode
replaces the earlier audit drafting, staged output, persistent-contract and
context-recovery selectors. It does not change their historical behavior.

Preparation binds a complete path inventory to the exact original bytes and
partitions whole top-level fields into workers. Every worker receives the same
complete originals and source bundle, with scoped schema guidance and access to
the complete registered schema/import/profile authority. Each child gets a fresh
native context. Its exact protocol and permitted operations remain in its system
prompt. Worker proposals are immutable scientific drafts, not accepted audits.

One final model integration receives every worker finding and must successfully
read every canonical worker row, including retained rows (#2194). It reviews
omissions and interactions across fields and the full/core pair. It explicitly
disposes of every finding and binds each replacement row to its predecessor
hash. Unchanged rows require an explicit index-bound retention declaration.
Assembly performs only these declared transformations and canonical serialization;
it preserves proposals, decisions and lineage. Schema imports must retain one
consistent snapshot across the full/core contexts (#2193).

Each child may submit at most two immutable grammar drafts. Only a failed first
grammar result authorizes the second. Grammar is source-blind: it cannot score
support or repair evidence. After integration seals, the assembled complete audit
gets one terminal evidence check, including all evidence used in integration
decisions. Failure is terminal. A successful tool receipt is rebound by closure
checks; the controller does not execute the scientific validator again.

All children share one ledger attempt, one sequence claim, one absolute deadline
and one stall-debit allowance. A fresh client/proxy per child does not reset these.
Worker reservations atomically enforce the lower cumulative worker ceiling,
leaving the registered remainder for integration. The ledger retains the actual
canonical attempt cap and separately records the stage cap. No child is resumed
or selectively retried after failure. Interrupted attempts require closure of
every extant child; a last-child shutdown alone is insufficient.

Acceptance binds every child, its exact initial request, typed tool history,
proposal/drafts, request accounting, row views, integration index and final
lineage. Independent scientific review must assess all discarded/replaced
concerns as well as the final audit. Phase 4 inherits the accepted scientific
instrument and transitive evidence, but no active batch tools. Generation and
evaluation entry points reject the selector, even when its value is null.
