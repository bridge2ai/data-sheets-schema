# Offline request sizing

The #5072 recovery utility checks saved request/count evidence without contacting
a provider. It can also construct the production `full` request from an existing
shared-generation registration. It does not launch generation, collect token
counts, build registrations, estimate billing, validate provider support, or
authorize a run.

The supported commands are available through the package module or the retained
helper:

```sh
PYTHONPATH=src python -m data_sheets_schema.offline_sizing --help
PYTHONPATH=src python scripts/adhoc/review_offline_sizing_20261019.py --help
```

## Export the initial request

Use an existing registration whose source, prompt, schema and other pinned
inputs still match. The registration must be at its declared
`registration_path`. This example uses **illustrative caller declarations**;
the numbers are not a recommendation or a claim about current provider limits.

```sh
PYTHONPATH=src python -m data_sheets_schema.offline_sizing prepare-full \
  /absolute/path/to/registration.json \
  --output-dir /absolute/path/to/new-sizing-export \
  --context-limit-tokens 1000000 \
  --context-limit-basis 'Illustrative caller-declared capacity; replace with reviewed evidence' \
  --required-margin-tokens 150000 \
  --margin-basis 'Illustrative caller-declared margin; replace with approved policy'
```

The output directory must not exist. The command creates `full-request.json`
and `sizing-manifest.json`, and leaves generation outputs untouched. It uses the
current production request builder, model settings and effective phase output
cap, including applicable environment overrides. `max_tokens` comes from the
actual logical request body. The export is the body passed to the provider
adapter, not HTTP headers or credentials. Canonical JSON normalizes object key
order; `payload_bytes` measures that canonical body rather than an SDK's HTTP
serialization.

`prepare-full` reconstructs a fresh run specification using today's/default
launch metadata. It does not replay an existing run's saved `run_date` or
arbitrary CLI overrides, and a registration alone does not capture those
choices. The exported bytes describe this construction, not a guaranteed
historical or future launch payload. For an already constructed launch, review
its exact saved request instead; changing launch metadata or environment may
require a new request export and count evidence.

The manifest pins captured registration inputs and the API runner, receipt
completion and shared-generation source files. It includes an exact initial
request and explicit unconstructed placeholders for later phases. Each future
audit worker needs its actual request and a distinct ID when that evidence
exists. The placeholder is not an inventory of the eventual worker roster.
No synthetic integration record is used to claim that a later request fits.

## Check saved evidence

```sh
PYTHONPATH=src python -m data_sheets_schema.offline_sizing check \
  /absolute/path/to/new-sizing-export/sizing-manifest.json \
  --out /absolute/path/to/new-sizing-report.json
```

Omit `--out` to write JSON to standard output. An existing output file is
refused. `--dry-run` retains `UNKNOWN` request verdicts even when saved counts
permit arithmetic. It performs the same input validation and no network calls.

For each exact request with valid saved count evidence:

```text
clearance_tokens = context_limit_tokens - input_tokens - payload.max_tokens
total_tokens     = input_tokens + payload.max_tokens
PASS if clearance_tokens >= required_margin_tokens
    and total_tokens <= the phase ceiling; otherwise FAIL
```

Both the capacity and margin are explicit declarations for that row, with text
recording their basis. They have no built-in provider default. `fits_window`
and `fits_margin` distinguish exceeding the context window from fitting the
window but missing the selected margin.

Each phase also has a ceiling that no declaration can raise (#5072). It is
reported as `ceiling_tokens` and `fits_ceiling`:

| Phase | Ceiling on `total_tokens` |
| --- | --- |
| `typed_audit_worker` | 1,000,000, the whole route window |
| `report`, `report_regate`, `report_after_repair` | 850,000, keeping a 15% margin of the window for growth |
| every other phase | 1,000,000, the route window |

The route window is the generic_v10 CBORG claude-opus-5 route's 1,000,000
tokens. A declared `context_limit_tokens` above it, or a smaller declared
margin, cannot make an oversized worker or report-family request `PASS`.

Missing request/count evidence produces `UNKNOWN`. A supplied file that is
missing, malformed or stale is an error rather than a substitute zero count.
Scenario rows and dry runs remain `UNKNOWN`, with `arithmetic_status` recording
any available calculation. Counts, capacities and margins must be integers;
boolean, string, negative and nonfinite substitutes are refused.

`full_run_readiness` is always `UNKNOWN`. A caller can list only one request,
and future stages depend on generated records and the eventual worker roster.
An individual request's `PASS` says only that its supplied count and actual
output cap fit the caller's declared arithmetic constraint. It does not
certify all requests in a run, scientific acceptance, or launch permission.

Exit codes:

| Command | Code | Meaning |
| --- | --- | --- |
| `check` | `0` | Every listed request has `PASS`; full-run readiness remains `UNKNOWN`. |
| `check` | `1` | At least one listed request has `FAIL` or `UNKNOWN`. |
| `prepare-full` | `0` | Export succeeded; no count or readiness was established. |
| Either | `2` | Invalid arguments, missing/malformed/stale evidence, or a file operation refused. |

## Evidence format and limits

Files are UTF-8 JSON. Duplicate keys, unsupported fields and nonfinite JSON
constants are refused. Individual files are limited to 64,000,000 bytes; input
inventories and request rosters have at most 1,024 entries. Numeric checks have
an upper bound of 1,000,000,000,000. These are parser bounds, not model limits.

A file pin has exactly three fields:

```json
{
  "path": "/absolute/path/to/file",
  "sha256": "64 lowercase hexadecimal characters for the exact file bytes",
  "bytes": 123
}
```

The pin is checked against the file before use. `path` must be absolute. The
example digest text is explanatory, not a valid pin. The Python API's `pin`
function constructs pins from files; retained project-specific helper scripts
should live under `scripts/adhoc/`.

A manifest has exactly these fields:

| Field | Contract |
| --- | --- |
| `format` | `d4d_offline_sizing_v1` |
| `scope` | Nonblank description of the evidence being reviewed. |
| `inputs` | Nonempty list of file pins; duplicate resolved paths are refused. |
| `requests` | Nonempty list of the request rows described below. |

Every request row has exactly these fields:

| Field | Contract |
| --- | --- |
| `id` | Unique nonblank request identity, including worker identity where applicable. |
| `phase` | One of the supported production phase names below. |
| `request` | Pin of the logical request JSON, or `null` if unconstructed. |
| `count` | Pin of saved count evidence, or `null` if unavailable. A count cannot accompany a null request. |
| `basis` | `exact` or `scenario`. Scenario arithmetic cannot clear the request. |
| `context_limit_tokens` | Positive integer, explicitly declared by the caller. |
| `context_limit_basis` | Nonblank provenance or rationale for that declared capacity. |
| `required_margin_tokens` | Nonnegative integer smaller than the declared capacity. |
| `margin_basis` | Nonblank provenance or rationale for the selected margin. |

Supported phases are `full`, `full_readdress`, `full_receipt_completion`,
`typed_audit_worker`, `typed_audit_omission`, `typed_audit_integration`,
`reconcile_full`, `report`, `report_regate`, `repair_full` and
`report_after_repair`. Multiple distinct worker IDs may share a phase.

A logical request has `model`, `messages` and `max_tokens`, with optional
`system`, `thinking`, `temperature` and `output_config`. Messages have exactly
`role` and `content`, with role `user` or `assistant`. This reader checks the
envelope needed for sizing; it does not validate every provider content block
or confirm that a provider accepts the model or settings. No independent
output-cap metadata is accepted: the arithmetic uses the request's cap.

A saved count file has exactly these fields:

```json
{
  "format": "d4d_saved_token_count_v1",
  "request_id": "the matching manifest row id",
  "request_sha256": "SHA256 of the canonical logical request body",
  "inputs_sha256": "SHA256 of the canonical manifest inputs list",
  "method": "endpoint messages.count_tokens",
  "input_tokens": 123456
}
```

Canonical JSON uses sorted object keys, UTF-8, no ASCII escaping or optional
whitespace, and disallows nonfinite numbers. Request and input digests are
reported by `check` even when count evidence is missing. The saved count file
is itself pinned by exact bytes. Changing the source inventory, request model,
thinking settings, messages or output cap prevents reuse of unchanged saved
count evidence. Whitespace differences in a request file change its file pin
but not its canonical request digest.

These bindings are **caller-supplied evidence, not authenticated provider
proof**. The reader does not contact the endpoint, verify a signature, infer a
missing source from prompt text, or prove that a caller-created request was
derived from its declared input inventory. Manually relabeling an unrelated
count with new digests does not make it valid evidence. Review the provenance
of supplied counts separately. This tool provides no count collector and makes
no zero-cost, billing, thinking-display or cache-acceptance claim.

## Step A1 sizing sweep

`scripts/offline_sizing.py sweep` sizes every request a generic_v10 API run
builds before it can know its own outputs, without contacting a provider
(plan step A1). Sockets are blocked before anything is imported. It needs a
checkout with the A3 draft registration builder and the A5d omission
contexts (`scripts/build_api_registrations.py`, `data/omission_contexts/`,
PR #5095), named by `--root`:

```sh
PYTHONPATH=<root>/src:<root> python scripts/offline_sizing.py sweep \
  --root <root> --workdir <new directory> --out <new results file>.json
```

`data_sheets_schema` and `scripts` are namespace packages, and an editable
install can put another checkout's `src` on the path. The sweep therefore
removes every other location before importing, and refuses to report if any
module it used came from outside `--root`.

For each project it stages historical phase-1 originals into a scratch run,
builds a draft registration with each grid's `max_paths`,
`max_inventory_bytes` and `max_workers`, and calls the production builders:
- `typed_audit_runtime.prepare_packet` and `build_request` for every worker,
  the omission stage and integration;
- receipt completion;
- `api_runner.build_phase` for full, the re-address turn, `reconcile_full`
  and report;
- `_append_regate` for the regate;
- `build_repair` with the generation context.

The stand-in records are adjusted only as far as the current runtime
requires:
- **Normaliser.** Each record passes through the runner's write-time
  normaliser.
- **Cardinality.** Values whose list-ness differs from the current schema are
  wrapped, unwrapped or joined, and slots the current class does not declare
  are removed. Every edit is listed. The edits go through a round-trip YAML
  dump, which keeps each record within 0.4% of its bytes; a plain re-dump
  shrank them by 7–8%.
- **Receipt.** A receipt pinned to an earlier bundle (AI_READI before #5042)
  is carried onto today's manifest by chunk sha256. Entries for removed
  chunks are dropped.

Content that cannot exist before a run is sized at its output cap, in
tokens. That covers the typed audit's findings, the report as written, and
every worker and omission response that integration carries.

Tokens are estimates: payload bytes times a tokens-per-byte ratio calibrated
from the 2026-10-12 A1b `messages.count_tokens` results for the same project
and stage, with the higher calibrated value for projects A1b did not count.
A1b's report-family payloads carried `'x' * (4 × cap)` placeholders, and the
endpoint counted about one token per `x` (the regate minus the report is
+382,173 bytes and +383,458 tokens in both projects). So those A1b rows
overstate the report family by about the placeholder size; the clean ratios
remove the placeholders.

A row's verdict is `estimate_fits` or `estimate_exceeds`, against the same
ceilings as the evidence reader. It is never `PASS`: only an exact saved
count reviewed by `check` can clear a request. Each project's primary record
also gets a byte decomposition of every request, computed by emptying each
part and re-encoding. That measures what a schema-context or protocol change
would save before anyone makes one.

## Historical evidence and deferred work

Historical #5072 reports remain unchanged. Old unbound audit totals and former
`PASS` labels are not accepted as current count evidence. The regression suite
uses selected historical numbers solely to demonstrate arithmetic failures,
including an oversized worker, omission and regate request, and a regate that
fits the window but misses the report margin. Those fixtures are not new
measurements or a current launch decision. Do not convert historical totals
into current evidence by attaching new input hashes.

This recovery does not change the source bundle, generation runtime,
registration builder, rubric or cache policy. #5044 remains deferred until an
owner selects and records a cache policy; implementation and validation of
that selection should use a separate review. Provider-authorized collection
of fresh exact counts, actual later-stage/worker coverage, provider support and
billing checks, and launch approval remain separate obligations.

Focused verification:

```sh
PYTHONPATH=src:. python -m pytest tests/test_offline_sizing.py -q -p no:cacheprovider
```

The tests block socket connections and compare the exported full request with
the production sender boundary, including its effective output cap. They also
exercise historical arithmetic, stale pins, absent counts, dry runs, malformed
evidence and output preservation.
