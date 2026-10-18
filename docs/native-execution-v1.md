# Explicit direct native execution v1

This additive consumer addresses the software portion of #4334/#2427. It does
not choose a live condition, model, runtime binary, limits, budget, auth identity,
cohort, or launch. The shared condition decision in #3336 and an authorized
empirical canary remain separate. All examples in its tests are fabricated
software evidence; they cannot be reused as real permission or launch authority.

The old offline attribution registration, callback composition, API refusal,
neutral fixed-recipe supervisor, and historical direct launchers keep their
original behavior and bytes. New execution uses a distinct registration kind,
`d4d_native_attribution_execution_registration` version 1, and the separate
`data_sheets_schema.native_execution` module. There is no arbitrary argv option,
public mock switch, implicit runtime discovery, retry, or resume.

## Preparation and supplied authority

`native_execution_registration.registration(composition_path, system_path,
permission_probe_path=..., attempt_id=..., attempt_directory=...,
evidence_directory=..., runtime=...)` captures an offline proposal. The
composition must have the explicit attribution axis/check cap, a direct
Claude Code spec, manifest-rooted corpus layout, profile, effort and provider.
Actual local helper/toolchain, prompt, schema, instruction, controller and package
identities are reconstructed. Source HEAD and every consumed package/frozen
helper blob must match the reviewed commit at admission; old registrations are
not updated to new code by relabeling their hashes.

The closed runtime mapping requires every field below; none has a live default:

- `route`: explicitly select `claude_code_direct_stream_json_v1`.
- `executable`: absolute resolved `path`, actual `sha256`, expected `version`
  output, and expected stream initialization `init_version`.
- `model`, distinct `auxiliary_models`, `effort`, `provider`.
- `limits`: positive integer `contextWindow` and `maxOutputTokens`, plus an
  explicit `limits_basis`. These are supplied assertions checked against the
  eventual native usage metadata, not independently measured context capacity.
- `auth`: exact `loggedIn: true`, `authMethod: claude.ai`,
  `apiProvider: firstParty`, caller-selected `subscriptionType`, and
  `expected_api_key_source: none`. This version supports this explicitly
  selected direct subscription route only; it does not support API keys/proxies.
- `environment`: explicit allowed base names. Required: absolute `PATH` entries,
  absolute `HOME`, `CLAUDE_SECURESTORAGE_CONFIG_DIR` (empty or absolute), and
  `CLAUDE_CODE_DISABLE_1M_CONTEXT` (`0` or `1`). Optional base names are USER,
  SHELL, TMPDIR, LANG, LC_ALL and TERM. Secret/provider redirect/override keys
  are refused. The consumer derives exact config isolation, safe transport,
  helper interpreter, manifest/profile/instruction and package environment.
- Positive integer `deadline_seconds` (software maximum one day), explicit
  positive decimal string `budget_guard_usd`.
- `keep_awake`: `policy` (`macos_iokit_ims_v1` or explicitly
  `not_applicable`), actual `host_platform`, and nonblank decision `basis`.

The saved permission manifest is independently rechecked from raw embedded
members by `native_execution_permissions.verify_saved_probe`. It must match
this exact binary/version, policy, command spellings, instruction/system,
controller closure and derived environment. It needs the complete admitted
command/read and denied restriction cases with actual initialization, callbacks,
results and settled shutdown; a passed summary is insufficient. V1 accepts no
command/path remapping. Its separately pinned neutral config/stub/local-provider
environment demonstrates recorded native admission only. Stub execution cannot
prove production helper behavior, future permissions, authentication or billing.
No probe is executed by preparation. Saved evidence is checked for consistency,
not cryptographic authenticity; an independent reviewer must assess its origin.

CLI preparation requires explicit `--composition`, `--system`,
`--permission-probe`, `--runtime` JSON, `--attempt-id`, `--attempt-directory`,
`--evidence-directory`, and fresh `--output`. It does not call a native binary.

## Separate single-attempt launch

`native_execution.launch(registration_raw, review_path=..., ci_path=...,
launch_word_path=...)` can invoke the selected native binary. It is a separate
explicit action, never a consequence of preparing a file. Every external
artifact binds raw registration SHA256, attempt id, source commit and dependency
SHA256. The independent review needs a distinct reviewer/author, literal
independent approval, timestamp and evidence reference. CI needs all six shards,
offline audit/finalization, offline evaluation, aggregate test and large-files
successful at the exact source, each with its recorded repository check URL.
The owner artifact requires `AUTHORIZE_ONE_NATIVE_ATTEMPT`, owner/time and exact
review, CI and permission-manifest hashes. These saved statements are not
signatures or an authenticated GitHub query.

All output/attempt/evidence paths must be fresh, canonical, disjoint and outside
source/historical controls and input authority. Reservation plus parent fsync
consumes the identity before later work. Start and selected authority bytes are
saved before dispatch. The authorized launch performs a fresh binary version
and filtered auth observation in the exact selected environment; it never saves
raw credential output. Failure retains the spent attempt and safely capturable
evidence. Keep-awake acquisition, if required, precedes dispatch and persists
through bounded child cleanup and evidence capture. Failed release prevents
completion. One dispatch means one native CLI process, not one provider request.
Native internal retries/costs are not claimed to be proxy-ledger metering.

The unchanged `execute_child` receives both actual composed callbacks and exact
phase spec. A usable draft exit 1 with `is_error: true` may be corrected by a
report-only write and fresh check. Old passes cannot clear newer failures,
pending/mutated artifacts, terminal evidence failure, invalid controls or a stop.
This consumer does not reuse the neutral supervisor's fixed recipe or synthetic
accounting. Actual terminal identity, usage counters, primary/auxiliary models,
limits, effort, cost estimate and shutdown are checked independently.

## Captured validation and publication

After shutdown one captured raw-byte/metadata basis feeds saved attribution,
phase/control chronology, schema, pair, receipts, final evidence and source-read
observation checks. The receipt gate is the existing strict implementation,
including registered bundle/chunk/schema identities, phase-1 snapshot selection,
identifier authority, strict floors and refusal of conflicting or unsupported
receipt-policy declarations. The existing API-only receipt-completion axis is
not enabled for native execution. Full/core
schema and original/final data authority cannot silently fall back to unrelated
paths. Captured projections must remain byte-identical and originals unchanged.

The full required conjunction retains all 13 neutral obligations, replacing
only fixed recipe history with generic typed settled tool history and synthetic
accounting with actual native metadata. Runtime authority and keep-awake are
additional gates. Passing yields `completed_pending_independent_review`, not
scientific acceptance. Known partial transcript/usage and the first failure are
retained when any gate fails. The generated replay report is itself hash-bound.
Durable final and publication-marker writes are exclusive; incomplete
publication cannot be read as complete. `read-final --registration ...` verifies
saved identities without running native/auth/provider processes or resuming.

Development tests use only an ordinary Python fake CLI, fabricated review/CI/
permission/owner records, and an explicit private observation seam. Genuine
receipt, derive, inventory, audit, attribution, evidence and recorder helpers
operate over synthetic text. Their success is software evidence only. No real
runtime permission, authentication or scientific result was established.
