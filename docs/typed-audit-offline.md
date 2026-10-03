# Typed audit offline packets

`python -m data_sheets_schema.typed_audit` implements the explicitly selected
`typed_audit_protocol_v1`: audit grammar, batching and output format 2, existing
evidence protocol 7, and `omission_inventory_v1`. Existing calls to the shared
grammar/batching/formatter still default to version 1. A version-2 plan does not
automatically select version 2.

This is an offline saved-response consumer. It does not call a provider, register
an execution, change records or receipts, resume audit28, or measure audit recall.
The taxonomy, omission novelty and scientific support still need independent
review. Issues #2921, #2930 and #3336 retain their scientific/live-execution work.

## Capturing a packet

All paths below are explicit caller inputs. Use a new output path at every step.
The context follows the existing `omission_context_v1` schema; it declares the
release/referent scope and source policy rather than deriving them from a name.

```bash
python -m data_sheets_schema.typed_audit prepare \
  --protocol typed_audit_protocol_v1 \
  --original-full original.yaml --bundle bundle.txt --manifest chunks.json \
  --receipt receipt.yaml --context omission-context.json --schema schema.yaml \
  --max-output-tokens 4000 --output packet.json
```

Optional `--original-core core.yaml` captures authority for `original_core`
artifact quotations. Optional `--source-manifest sources.yaml --project PROJECT`
captures both exact registered-provenance bytes and their selected projection.
Neither input is discovered from the checkout. Evidence referring to unavailable
authority is refused. Final-record artifact evidence is outside this protocol.

The packet embeds exact original, bundle, chunk-manifest, receipt, context and
optional authority bytes, with hashes and lengths. It captures the complete local
schema/import closure. Replay derives that closure from its stored bytes and
logical import paths and refuses missing, extra or inconsistent entries; it never
falls back to current schema files. An additive `schema_snapshot` argument on
`audit_omissions.prepare` supplies this replay without changing the default
omission request or any frozen omission policy/schema asset.

Packet hashes identify content; they do not authenticate the author or establish
scientific authority. Keep the packet and its hash with the registration or other
external record appropriate to your later reviewed use. Changing all input bytes
and honestly rebuilding a new packet creates a different experiment, not proof
that the previous packet passed.

## Request recipes and saved responses

The packet contains the exact omission request in `omission_request`, worker
assignments in `plan`, and exact version-2 schemas, contracts and examples in
`contracts`. Export the worker request after the packet is sealed. The public
`worker_request(packet, worker_id)` API is the same operation used by the CLI.
Its exact payload includes the packet SHA, worker assignment, shared scientific
context and stage instructions. `request_sha256` hashes that canonical payload,
excluding its own identity field. The invented examples in the contracts are
syntax demonstrations and cannot support real findings.

Save actual worker and omission responses as strict JSON. Capture the worker
reply with its exported request, then check and index it. Repeat
`--worker ID=PATH` for every assigned worker; the roster must match exactly.

```bash
python -m data_sheets_schema.typed_audit request \
  --packet packet.json --worker-id worker_0001 --output worker-1-request.json
# Supply that request in your separately authorized workflow; save raw reply.
python -m data_sheets_schema.typed_audit capture-response \
  --request worker-1-request.json --response worker-1-raw.json \
  --output worker-1-saved.json
python -m data_sheets_schema.typed_audit check-worker \
  --packet packet.json --worker-id worker_0001 --response worker-1-saved.json \
  --output worker-1-check.json
python -m data_sheets_schema.typed_audit index \
  --packet packet.json --worker worker_0001=worker-1-saved.json \
  --omission-response omissions.json --output index.json
```

Worker checking reports structural acceptance only. Indexing reconstructs the
original-bound plan, rebuilds complete finding hashes, and invokes the real
omission checker on the raw response. Every canonical chunk is mandatory,
including previously negative or redundant chunks. A saved successful omission
report is never a substitute for that response.

The complete index is the integration request envelope. Its
`integration_request.payload` contains shared context, exact saved workers and
omission response, proposal index and output contract. The request payload SHA
and complete typed-index SHA are separate identities; the latter is supplied
outside the request payload to avoid a self-referential hash. Capture the raw
integration reply against the complete index, then run terminal operations:

```bash
python -m data_sheets_schema.typed_audit capture-response \
  --request index.json --response integration-raw.json --output integration-saved.json
python -m data_sheets_schema.typed_audit check-integration \
  --packet packet.json --worker worker_0001=worker-1-saved.json \
  --omission-response omissions.json --integration-response integration-saved.json \
  --output integration-check.json
python -m data_sheets_schema.typed_audit assemble \
  --packet packet.json --worker worker_0001=worker-1-saved.json \
  --omission-response omissions.json --integration-response integration-saved.json \
  --output assembly.json
python -m data_sheets_schema.typed_audit check \
  --assembly assembly.json --output independent-check.json
```

Assembly stores the packet and raw responses, exact audit bytes, index, lineage
and acceptance report in one self-contained file. Captured bytes use an object
with `base64`, `sha256` and `bytes`; for example, decode `assembly.audit.base64`
to inspect the final audit. `check` independently derives the audit, lineage,
requests, indices and acceptance result from the stored raw inputs. It compares
the entire reconstructed assembly, including hashes; an edited successful report
cannot bypass this work. Assembly refuses source-evidence failure. Use
`check-integration` for its bounded diagnostics.

Saved worker/integration envelopes have closed fields and bind the packet and
request identities; integration also binds the complete typed index. Inner raw
UTF-8 response bytes retain their exact encoding/whitespace in a byte blob. Bare
replies and unchanged envelopes from a different context or omission inventory
are refused, even when the original full record and pure worker index match.
The public `capture_response(exported_request, raw_bytes)` API performs the same
capture as the CLI. It declares a request/response association, not authenticated
provider provenance. Deliberately rewrapping old bytes under a new request is a
new caller provenance claim; this offline consumer cannot prove a provider read
the request. Record honest associations in the separately approved workflow.

## Findings and omission accounting

The optional closed `kind` vocabulary is `role_placement`, `status_scope`,
`date_scope`, `absence_or_self_narration`, `quotation_fidelity`, `identifier_count`,
`attribution`, `omission`, and `other`. Missing kind stays untyped. Complete
finding hashes preserve the kind and omission references through worker,
retain/replace/drop/new integration and final lineage.

Every omission finding in this consumer needs `record: full` and a nonempty
`omission_candidates` list naming captured candidates. The full-only inventory
cannot support core/both omission claims. A missing slot is represented by the
candidate's schema owner and slot chain, not an invented populated JSON Pointer.
Exact targets, quotes, source identities and candidate hashes remain in lineage;
the finding's free-text `slot` is not target authority.

Integration must contain `omission_dispositions`, including an empty array for a
complete all-negative response. Each captured candidate occurs once, with
`candidate_id`, `action` (`retain` or `drop`), nonblank `reason`, and `evidence`.
Drops require literal document/artifact evidence. A retained candidate must link
to exactly one final omission finding. Several candidates may merge into one
finding. Unknown IDs, silent loss, duplicate allocation and linking after drop
are refused. Structural batching alone cannot check this captured candidate
roster; the packet consumer does so.

Final acceptance invokes the existing evidence-v7 checker and checks all
integration decision evidence against captured sources/artifacts. A matching
quote, complete declared coverage or valid schema target does not prove omission,
novelty or scientific support. Reports keep `scientific_support`, `novelty` and
`exhaustive_recall` explicitly `unverified`, including a clean all-negative audit.

## Bounds and output behavior

Existing shared limits are preserved: 4,000,000 bytes for the original full
record, 2,097,152 bytes per inner worker/integration/assembled audit, 3,000,000 bytes
per saved worker/integration envelope, 8,000,000 bytes per
other ordinary input/omission response, and 16,000,000 bytes for the schema
closure. This consumer also caps the closure at 256 files, the complete packet at
96,000,000 bytes and assembly at 160,000,000 bytes. The default complete request
bound is 32,000,000 bytes; preparation and indexing enforce it. Unsupported large
records are refused, never truncated. A larger-corpus protocol needs separately
reviewed bounds.

Every output uses exclusive file creation. Existing outputs, symlinks including
dangling links, and hardlink aliases are refused. Inputs and historical artifacts
are never overwritten. Exit 0 means the requested bounded operation succeeded;
exit 1 means a written check report failed; exit 2 means malformed inputs,
identity/coverage refusal or an output error. Worker exit 0 alone is not terminal
source-evidence acceptance.

The test fixtures and CLI round trips are invented engineering probes. They are
not empirical calibration, curated audit observations or evidence of recall.
