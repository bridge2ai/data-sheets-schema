# Native audit continuation

A native generation can stop at the transport after producing and freezing a full
record, a deterministic core, and its receipt. These controls run Phase 3 in a new,
separately registered native session using those unchanged originals. They do not
turn the stopped generation into a completed attempt.

`prepare` works offline. It replays the actual parent instruction and tool history,
checks source identities, successful receipt checking, core derivation and the
original snapshot, and binds the confirmed accounting checkpoint. It renders the
shared generic-v9/renderer-14 audit contract with the complete frozen source bundle,
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
so repeating one carries no charge ambiguity. Each try is bounded to two minutes, the
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
timeout must therefore cover the upstream read bound in force, the bounded
token-count tries with their pauses, the connect allowance and a minute of margin,
and the native fetch idle timer must be registered off. With three count tries that
is 455 seconds above the read bound. The policy is audit-only: generation, Phase 4
and the evaluations refuse it. `native_controls/probe_native_stall.py` drives the
real pinned executable against a scripted upstream that stalls, with no provider
contact, and shows the client retrying to completion.

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
protocol-3 evidence and all inventory values against the actual originals and source
bytes. Failure terminates further admission. A passing file alone does not permit
a subsequent request: the controller must also observe the typed successful tool
result. The audit cannot be repaired after validation starts. An unknown provider
charge retains its reservation and stops the attempt.

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
