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

Stopped execution results include `stop_source` and `runtime` evidence. Runtime
evidence records whether the proxy was initialized and its bounded shutdown
completed. `unfinished_handlers` is a count only after that shutdown; otherwise it
is `null`. A late handler failure does not replace an earlier controller stop.

A successful result is `completed_pending_independent_review`. Scientific review
must assess grounding and audit completeness separately. Reconciliation, report
production, final pair acceptance and evaluations require subsequent registered
stages. Preserve the stopped source run, rejected audits and all billing evidence.
