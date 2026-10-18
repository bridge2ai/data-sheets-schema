# Registered shared-generation API protocol

`shared_generation_v1` selects `generic_v10`, renderer 25, API playbook 2 and
receipt completion 2 together. This is the API implementation tracked by
[#4345](https://github.com/bridge2ai/data-sheets-schema/issues/4345). It has no
default selection. Renderer 24 remains offline; receipt completion 1 remains
an API renderer 8 condition. Old prompts, playbooks and rendering identities
are preserved.

The protocol connects actual full generation, receipt completion, derived core,
typed audit workers, a complete source-first omission pass, integration,
reconciliation and final reporting. It uses the existing evidence and typed
audit checkers. Passing those checks establishes complete declared structures,
literal evidence links and input association; it does not establish entailment,
exhaustive recall or scientific correctness.

## Supply authority before execution

The caller supplies strict UTF-8 JSON with `format:
shared_generation_registration_v1`. Every field below is required; omitted,
extra, duplicate or malformed fields refuse. The public
`data_sheets_schema.shared_generation.parse_registration` checks the declaration
without constructing a client. `file_pin` and `schema_pin` can describe existing
files and captured schema closures; they do not choose experimental settings.

- `registration_id` and an absolute `registration_path`, plus `run` containing
  the exact project, arm, method and run label. A registration belongs to one
  run. Its own exact bytes must exist at the declared caller-owned path.
- `selection`, obtained from `shared_generation.descriptor()`. It binds the
  condition, renderer, runtime, typed protocol, policy versions and selected
  prompt/playbook SHA-256 values. Installed bytes and their transitive selected
  references must actually match.
- `inputs`: project; exact bundle, chunk manifest, source manifest or explicit
  null, and generation-scope context pins; explicit profile name, basis and
  vocabulary-file pin or explicit null; and
  full/core schema roots with all captured transitive source pins. Each file pin
  contains its absolute path, SHA-256 and byte length. The context uses
  `omission_context_v1`; it names the selected dataset/release and source scope,
  not calibration labels or historical diagnoses.
- `runtime`: actual provider and endpoint declarations, model, temperature,
  thinking, effort and effective configuration pin or explicit null. Resolved
  settings and the actual client's endpoint must agree. No credential is part
  of the registration.
- `audit_limits`: positive `max_paths`, `max_inventory_bytes`, `max_workers`,
  `max_request_bytes`, `max_input_tokens_per_call`, `worker_output_tokens`,
  `omission_output_tokens`, `integration_output_tokens`,
  `aggregate_input_tokens`, `aggregate_output_tokens`, `max_calls`,
  `context_limit_tokens`, and a nonblank `context_limit_basis`.
- `audit_transport`: exactly `transport_attempts: 1`, `sdk_max_retries: 0` and
  `malformed_response_retries: 0`.
- `receipt`: a `receipt_completion_registration_v2` for `generic_v10`, with
  the selected v2 policy SHA-256, receipt instrument 4, explicit request,
  output and context limits, and an explicit pending or registered coverage
  floor. Its counter, merge, padding and exact-fraction gate semantics are
  those described in [registered receipt completion](receipt-completion-runtime.md).

Booleans cannot replace integer counts. Input authority must remain separate
from every run-owned output, progress and evidence directory. Files are captured
once and rechecked before admission; later replacement bytes cannot become a
new authority for the same run.

No model, route, output cap, empirical floor, comparator or campaign is selected
by this software. A plan uses the caller's declaration and makes no model or
token-count request:

```bash
d4d api plan --project "$PROJECT" --label "$RUN_LABEL" \
  --shared-generation-version 1 \
  --shared-generation-registration /absolute/caller-inputs/registration.json
```

`render-prompt` accepts the same selection. An explicitly conflicting legacy
condition, runtime, arm or policy option refuses instead of being overridden.
Only the actual full request has a byte-derived token estimate. The later
record-dependent roster and total remain unknown. Declared audit token
allowances are not measured consumption or dollar estimates.

For `batch`, that option names a distinct closed
`shared_generation_batch_roster_v1` document with `registrations` rows of
`{project, label, registration_path}`. Rows must cover the explicitly requested
project × replicate labels exactly once, with distinct registration paths and
IDs. A single-run file is not a batch roster, even for one run. The roster is
itself immutable caller authority. A pending floor cannot authorize fan-out or
use the ordinary canary bypass.

## Actual request and recovery boundaries

Generation receives the selected factual rules, actual induced Software keys,
and captured schema structure. The rules retain ongoing status and clause-local
date scope; allow complete source-supported prose lineage; distinguish actual
data-file variables and software used for the declared activity; and preserve
source-enumerated lists and supported role rosters without invented members.

The original full, effective receipt and derived core are preserved before the
typed audit. Every populated-field worker receives complete source/record
context and its exact path assignment. The omission pass accounts for every
captured chunk, including prior negative, redundant and duplicate statuses.
Integration accounts for every candidate retained or dropped. A retained
candidate must link to exactly one full-record omission finding.

Every actual typed request also carries the complete receipt-completion
unsupported-candidate block, source authority, exact outer request identity,
and complete schema owners/containing values. Receipt candidates are distinct
from source facts that never entered the record. The whole payload must fit;
neither group can be silently truncated.

Workers, omission and integration use the same client's count endpoint before
their one admitted response. The endpoint count and explicit output cap must
fit the declared route window and aggregate allowances. Unknown counts refuse.
SDK retries and answer retries are disabled for these selected calls. Other
ordinary generation phases retain their existing separately accounted retry
behavior.

The usage ledger records ordered prepared, admitted, response-saved and checked
states. Complete raw response, usage, finish reason and reasoning are preserved
before parsing. A saved complete response may settle its exact pending usage
once after interruption. An admitted response that was not preserved, unknown
usage or a terminal refusal cannot purchase a replacement. Losing progress
cannot restart generation after its receipt/audit boundary; `no-resume` cannot
reuse spent outputs as a fresh run.

The exact checked derived audit reaches reconciliation. Both final report and
report recheck receive the selected role-relationship rule and complete final
containing entities under captured schema owners, including unchanged members.
A name match does not establish responsibility. The existing evidence output
grammar is preserved; the model still declares its relationship judgment.

Final publication and completed resume reconstruct the assembly from captured
requests and replies. They recheck source/schema/context/registration identity,
original full/core, effective receipt, accounting, exact downstream audit carry
and the saved audit snapshot. Its selected index or portable attestation must
name the unique checked and settled integration call, not merely another paid
stage. Completed-record checks use that exact record's attestation. The provenance `shared_generation` block names
the resulting assembly and audit hashes and labels scientific support
unverified. Saved success flags alone are not authority.

An explicit per-run cache stores only serialized pure packet derivations, keyed
by all captured input/schema/context bytes, project and limits. It returns fresh
objects and never caches response verdicts or terminal state. Every packet open
still compares the complete reconstructed packet, and final completion and
completed resume use a new derivation cache whose first reconstruction is
independent of the runtime cache. Default offline typed-audit calls remain
uncached and byte-identical.

## Remaining scope

The [pure typed-audit tools](typed-audit-offline.md) remain model-free. The new
runtime is their separately selected live API consumer. Existing historical
controllers, registrations, artifacts, protected figures and audit28 are not
rewritten.

Native/direct selection refuses in this slice. A matching supervisor adapter
must use the same selected authority after its separate runtime review. No
API-only result satisfies that cross-arm requirement. Independent labels,
calibrated thresholds, canary/comparator selection, owner approval and actual
campaign execution remain under the original parent issues; synthetic tests
are engineering evidence only.
