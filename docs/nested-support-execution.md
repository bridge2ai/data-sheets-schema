# Registered nested-support execution

`d4d evaluate support-execution` explicitly opts into `nested_support_execution_v1`.
It consumes an existing `nested_support_result_v1` descriptor and preserves its
original readiness blockers, selected records, context, schemas and requests.
The existing planner, saved-response commands and legacy evaluation calls do not
select this executor automatically. Top-level fitness requires its separate
descriptor and adapter; it is not a support verdict.

## Registration and execution

Prepare a descriptor with `support-results prepare`, then provide a closed JSON
declaration. This example is a **fictional local test configuration**. All limits
are illustrative, not evaluation recommendations. The loopback endpoint must be
an explicitly started local fixture; this command does not start a server.

```json
{
  "format": "nested_support_execution_v1",
  "registration_id": "fictional-local-example",
  "purpose": "local_fixture",
  "run_output": "/absolute/fresh/local-run",
  "transport": {
    "adapter": "native_message_http_json_v1",
    "url": "http://127.0.0.1:8765/v1/messages",
    "model": "EXACT_MODEL_FROM_DESCRIPTOR",
    "auth": "none",
    "anthropic_version": "2023-06-01",
    "timeout_ms": 2000,
    "thinking": null,
    "effort": null,
    "retries": 0,
    "redirects": false,
    "environment_proxies": false
  },
  "limits": {
    "max_calls": 2,
    "request_bytes": 100000,
    "response_bytes": 50000,
    "total_response_bytes": 100002,
    "input_reservation_per_call": 100,
    "input_scheduling_threshold": 200,
    "output_scheduling_threshold": 834
  },
  "decisions": {
    "instrument_review": null,
    "context_review": null,
    "controls_review": null,
    "private_control_handling": null,
    "paid_authorization": null,
    "calibration_acceptance": null,
    "canary_acceptance": null
  },
  "prices": null
}
```

```sh
d4d evaluate support-execution prepare --descriptor descriptor-dir \
  --declaration declaration.json --output registration-dir
d4d evaluate support-execution run --registration registration-dir
d4d evaluate support-execution recheck --run /absolute/fresh/local-run
```

The actual dispatcher makes one nonstreaming messages POST per admitted request
using HTTPX, with no retries, redirects or environment proxies. The registered
wire transformation removes only the planned null temperature, adds
`stream: false`, and applies explicit `thinking` (null or adaptive) and `effort`
(null, low, medium, high, max). The model and requested `max_tokens` remain exact.
Both original and effective request bytes are retained. Unsupported request
shapes refuse before dispatch. `timeout_ms` is HTTP phase inactivity timeout,
not a total wall-clock deadline.

`local_fixture` requires a literal loopback HTTP address, rejects credentials and
approval references, and remains scientifically ineligible even when a response
is mechanically accepted. `calibration` and `cohort` require HTTPS, explicit
`bearer` or `x-api-key` authentication, and explicit decision references. Each
reference is `{ "reference": "...", "sha256": "64 lowercase hex characters" }`.
Calibration requires the first five decisions; cohort requires all seven.
These declarations are not authenticated approvals or checks of scientific
truth. The software does not discover private controls or choose their handling.
The caller must review the exact captured request content and authorize any
export of selected private material before using a paid route.
Paid use still needs actual owner authorization; preparing a declaration does
not provide it. Credentials are supplied only at runtime through an explicitly
named `--credential-env` variable and are not saved.

## Scheduling, accounting and failure capture

Input reservations are **provisional scheduling thresholds**. There is no
tokenizer or count endpoint, so the first call can exceed its reservation.
Unknown usage, a reservation overrun, an incomplete or rejected reply, and any
transport failure stop further admission. This is not a hard input-token or
monetary cap. Such unimplemented configuration fields are rejected. Requested
output tokens, actual call count and captured byte limits are enforced.
Zero-valued reported cache counters remain zero; absent counters remain unknown.
Reported usage from failed calls remains in accounting rather than disappearing
into accepted-only totals.

Optional prices have exactly `currency`, `per_tokens`, `source`, `as_of`, and
`rates` fields. Rates are finite nonnegative decimal strings keyed by any of
`input_tokens`, `output_tokens`, `cache_read_input_tokens`, and
`cache_creation_input_tokens`. A cost is calculated only with all four counters
and corresponding rates; otherwise it is unknown. No current prices are fetched.
These calculations use the declared rate basis and do not verify a provider bill.

Rates have at most 32 significant digits and a stored decimal exponent from
-18 through 18; the positive integer denominator is at most 10^18. Costs use an
explicit 64-digit ROUND_HALF_EVEN context independent of ambient decimal
settings. Extreme rates refuse before admission. A complete failed HTTP reply
can report usage and an estimated cost while its execution status remains
failed; observed counters are not verified billing.

Admission is exclusively created and fsynced at the one registered run location
before HTTP dispatch. Reentry, including a copied registration pointing to that
location, refuses. A process interruption after admission cannot purchase a
replacement. Incomplete admitted evidence is `spent_unknown`; complete retained
raw evidence can be settled offline without another request. Recheck never
resumes unstarted calls. Symlink destinations and aliases are rejected.
Every later admission requires the preceding durable settlement. A missing
terminal settlement can still be reconstructed from its retained complete raw
response, without purchasing a replacement or accepting a later admission.

Raw HTTP body bytes are bounded during reading, with at most one extra byte to
prove overflow. Identity encoding is requested; unexpected encodings fail and
their bounded raw bytes are retained without decompression. HTTP status,
request-id, transport stage, sanitized failure class and elapsed duration are
saved before semantic parsing. Headers, cookies, credentials and exception text
are not recorded. Raw message usage, reasoning and redacted reasoning remain
available through the saved assessment; none establishes response correctness.

`capture_run(directory)` captures a closed ledger and all referenced artifacts.
`recheck_captured(capture, ledger)` reconstructs it using captured bytes only,
including after relocation. It does not verify the current runtime, contact a
provider, read original records or trust saved acceptance flags. This proves
internal evidence consistency and local invocation association, not cryptographic
provider provenance. Reports keep support edge/value counts separate and retain
`scientific_eligibility: false`; empirical calibration, reviewed human labels,
context choice and subsequent campaign authorization remain separate work.
