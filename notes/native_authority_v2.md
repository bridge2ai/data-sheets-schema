# Native authority v2 (#5508)

V2 is selected explicitly. Prepare offline attribution registrations with
`python -m data_sheets_schema.native_attribution_registration_v2 prepare` and
its required arguments. Construct/check compositions through
`native_attribution_controller_v2`; load their dependencies through
`native_supervisor_authority_v2`. These APIs do not authorize a native launch.
The existing execution-registration entrypoint is v1; U3 must explicitly wire
its new route to v2 rather than silently redirect that entrypoint.

The generalized historical-style CLIs are
`notes/matched_cborg_2026-09-13/prepare_registration_v2.py` (requires
`--projects` and `--canary-order`) and
`notes/claudecode_direct/prepare_direct_v2.py` (requires `--project`).
Use `--render-only --output <fresh-scratch-directory>` for offline rendering.
An optional `--external-canary <json>` explicitly supplies an external project's
`project`, `profile`, `source_manifest` and `chunks`, plus its evidence metadata.
`--external-sources <directory>` pins any additional capture evidence. No external
study is appended implicitly. Canary IDs must belong to the selected job roster.
Direct preparation retains its runtime probe requirements; it is not an offline
substitute for render-only, and was not run against a native executable here.

V1 paths, manifests and literal digests are frozen historical authority, including
their CLI defaults. Existing callers and their v1 tests intentionally remain on
those paths. They are not aliases for the v2 CLIs. Controllers' bare import names
are confined to a single version per Python process; importing another version's
preparer first is an origin mismatch, not a reason to fall back.

Replay a saved v1 record in its original source environment: exact code commit,
working directory and input paths, interpreter and complete package-source map.
Adding v2 package files changes that map. Do not suppress the additions, rewrite
a saved record, or accept either digest under a v1 identity. A v1 registration
created in a new environment still binds every file of that environment.

The v2 manifest's source commit contains its preparer bytes. Its literal digest
is frozen in the v2 consumer; the supervisor separately pins the direct preparer
and binds the complete package map. Updating helper bytes needs a new reviewed
closure and registration. The generation script and freeze script in
`scripts/adhoc/*native_u2_20261106.py` record how these copies were produced;
they are development provenance, not live launch entrypoints.

Historical sources remain visible to the specificity scanner. No scanner
exception, discovery change or existing finding waiver was added by U2.

## Round 3 wire interface for U3

Both v2 preparers serialize exactly `authority_version: 2`,
`controller_sources_sha256: <the v2 manifest digest>`, and `registration: {...}`.
The inner registration has schema 2; direct also uses
`kind: d4d_direct_arm_registration_v2`. No v1 repository, generation, or pins
are present at the envelope top level. Never unwrap a record for a v1 launcher.
U3 must call `prepare_registration_v2.require_envelope` before any launch side
effect, then validate the inner preparer pins and all admission, review, budget,
and execution gates through a separately versioned route. This function checks
wire identity only; no v2 live launcher is delivered by U2.

Standalone bare imports remain process-global: importing frozen `prepare_direct`
after v2 preparation can bind its generation utility to v2. Run standalone versioned
CLIs in separate processes; do not mix them. The supervisor checks origins and
restores module state. Its two preparation names now share one module object.
Frozen v1 code cannot be hardened against later imports without owner migration.

The source commit named in the v2 manifest must be published with this branch's
history and retained with a merge commit (not squash/rebase), or the closure must
be re-frozen and revalidated after integration. Offline delivery cannot make a
commit remotely reachable. A regression checks every manifest source against the
named local Git commit. No publication or merge is performed here.

Explicit-old-values equivalence permits one semantic correction: profile basis is
now `declared by source manifest`, replacing the false caller claim. Recorder
instructions and their derived hashes therefore differ. Tests compare separate
output trees, normalize only this exact text and derived hashes, compare JSON
numbers by value, and compare all evidence pin paths and contents. Both external
capture directories must be supplied with repeated `--external-sources` options.

The saved M7 fixture is byte-exact and CI tests its v2 refusal and hash identity.
V1's `native_attribution_registration.verified` reconstructs `RunSpec` and calls
`registration(spec)` before testing checker identity. The saved record contains
absolute input, interpreter and resource paths in the retained M7 scratch export;
therefore its exact v1 checker-identity refusal cannot be portable to arbitrary CI
without recreating that original environment or rewriting historical bytes.
The retained local replay probe tests that refusal; the CI test explicitly does
not claim portable v1 replay. The old environment-gated generator is retained in
`scripts/adhoc/generate_native_u2_m7_fixture_20261106.py`, outside test discovery.

### Round 3 offline review ledger

GitHub issue publication is deferred by the explicit offline instruction. These
review findings are retained for owner publication, rather than silently dropped:

- R3-T1 (fixed): isolate source-commit tests from previously imported v1 modules.
- R3-T2 (fixed): compare separate output trees and explicitly account for the
  truthful profile-basis correction; old output reuse had hidden omissions.
- R3-H1 (fixed): initialize the scratch Git index before mutation testing.
  An empty index made unchanged agent definitions appear deleted and invalidated
  the first mutation canary. Those early runs are excluded from kill claims.
- R3-R1 (documented residual): exact saved-v1 checker-identity refusal needs the
  original absolute-path environment, as described above. CI exercises saved-v1
  bytes against v2 without skipping.
- R3-R2 (documented residual): standalone imports of frozen v1 modules after v2
  can alias generation utilities. Use separate processes; the supervisor path
  checks origins and shares the v2 object. No frozen v1 import hook was changed.
- R3-R3 (integration requirement): preserve the named helper commit when this
  branch is published/merged, or re-freeze and revalidate after integration.
- R3-R4 (fixed): an explicitly named missing external directory previously
  yielded no pins. Preparation now refuses it before output creation; a negative
  test asserts the specific error. Envelope admission also refuses non-object
  input and non-integer schema versions.

## U3-A: explicit shared preparation and execution bridge

The authority version is 2; the scientific procedure stays native shared-v1,
renderer 26, with its declared receipt policy. These are different version
axes. Frozen v1 routes and the U2 preparers are unchanged. No new launcher or
native probe is provided by U3-A.

The shipped `prepare_direct_v2.build` does **not** select the shared-native
S/R contract. Its ordinary render spec also lacks the attribution opt-in
required by the attribution composition. Consequently neither an exact direct
preparer → attribution join nor a shared-native join can be claimed by wrapping
or silently enriching that old record. U3-A defines a separately named producer:
`native_execution_registration_v2.prepare`. The new body's kind is
`d4d_native_shared_preparation_v2`, with `schema_version: 2`, inside the unchanged
U2 three-field envelope. Other preparer kinds refuse at this execution route.

### Frozen interfaces for U3-C/D

| Interface | Inputs / return | Required behavior |
|---|---|---|
| `native_execution_authority_v2.dependency_identity()` | fresh identity mapping | V2 supervisor/preparer closure, complete package source map, interpreter and fixed keep-awake primitive. |
| `require_committed(identity)` | no return on success | Exact local Git tree roster and every source blob; no omitted files, v1 identity or uncommitted source acceptance. |
| `loaded_dependencies(expected)` | context yielding only `prepare_registration_v2` and `run_direct_canary_awake` | Compile captured, verified source bytes; no bytecode-cache reads/writes. Restore aliases and loader state on every exit. Historical transitive helpers remain private. |
| `native_execution_registration_v2.prepare(selection_path, runtime_path, *, job_id, run_date, max_draft_checks)` | v2 envelope mapping | Read-only producer using current U1 capture, explicit valid runtime and fresh native26 rendering; no instruction-file publication or attempt reservation. |
| `verify_preparer(raw, *, job_id)` | fresh inner preparation mapping | Pinned `prepare_registration_v2.require_envelope` first, then closed kind, selected job, exact current S/R, render/input/output identity and complete pins. No launch grant. |
| `verified(raw)` | complete current execution body | Envelope first, exact preparation/runtime/composition joins and committed closure, then the fixed U3-D consumer below. Missing consumer refuses. |
| `admit(raw, *, review_path, ci_path, launch_word_path)` | frozen `Admission(registration_raw, evidence, reservations)` observation | Main-thread refusal first; fresh complete verification, v2 review/CI/owner evidence, runtime/budget/host validation, independently checked disjoint reservations and rechecked evidence. No writes or dispatch. |

`prepare` binds exact S and R file pins, job id, run date, draft allowance,
render spec, input identity, instruction bytes/hash, all four outputs and the
complete selected input/schema/asset/package/helper/executable pins. It retains
U1's full validation and does not accept a caller-supplied `RunSpec`. The runtime
validator/fingerprinter is reused as a pure utility from the unchanged runtime
registration module; its v1 verifier/selection/launcher is never called.

The execution envelope's body is explicitly
`kind: d4d_native_shared_execution_registration_v2`, `schema_version: 2`, and
`execution: requires_exact_independent_review_ci_permission_and_owner_launch_evidence`.
The **exact required key set** is:

```text
kind schema_version execution attempt_id composition system_path permission_probe
attempt_directory evidence_directory job_id preparation_raw_json preparation_sha256
execution_gates runtime max_draft_checks selection_sha256 runtime_declaration_sha256
working_directory dependencies composition_raw_json composition_sha256 system_sha256
effective_system effective_system_sha256 instruction_sha256 permission_probe_sha256
permission_expected_sha256 permission_observations argv environment selection scope
```

The only optional key is `receipt_origin_reporting`, whose version must be the
exact integer 1 and whose entire declaration is reconstructed by the consumer.
No unknown or missing required key is accepted. Its `execution_gates` list must equal the fixed fifteen
obligations, in order: terminal, shutdown, first stop, live/saved attribution,
phase/tool history, schema, pair, receipts, evidence, observation, accounting,
runtime authority and keep-awake. These are obligations, not asserted passes.

U3-C must compose the **same** native selection/runtime/rendering bound by this
preparation and publish actual instruction/policy evidence. U3-D supplies one
fixed module, `data_sheets_schema.native_shared_registration`, declaring integer
`AUTHORITY_VERSION = 2` and these interfaces:

```python
rebuild_v2_body(*, preparation_raw: bytes, composition_path, system_path,
               permission_probe_path, attempt_id, attempt_directory,
               evidence_directory, max_draft_checks, receipt_origin_version) -> dict
execution_paths_v2(body: dict, *, fresh: bool, extra_protected) -> list[Path]
```

The first must rederive the **entire closed E** (not a subset or a prior passed
flag): genuine C, policy, saved permission recipe/observations, sole runtime,
budget/deadline, receipt authority, input/output/path identities and hashes. It
returns that exact body. The bridge passes only the named reconstruction inputs,
never the submitted body's derived fields or serialized body. Argument echo
does not reconstruct E; the permanent echo test returns preparation, not E.
This comparison does not prevent deliberate access to interpreter state. Both
function signatures are exact (no defaults, variadic forwarding or wrappers).
It must not call the outer `verified` recursively.
The second rechecks canonical, disjoint, protected-input-safe and unspent
reservations without creating them. It must include native stage reservations.
The returned list contains distinct physical `Path` objects for the attempt,
evidence, selected output-parent directories and selected stage root. The bridge
independently reconstructs this set from the preparation, checks freshness,
disjointness and protected-input overlap, then retains the sorted tuple in
`Admission.reservations`. A `None`, boolean, incomplete or duplicate result refuses.
No input may select a module or callback; another origin, interface or version
refuses. The module is compiled from captured bytes whose digest matches the
committed package source map, with loader-recorded identity checked before and
after its functions run. Its static package import graph must not import frozen
v1 execution authority. Dynamic constructs and star imports are linted only in
the closed `CONSUMER_OWNED_MODULES` list: `native_shared_attribution`,
`native_shared_capture`, `native_shared_controller`, `native_shared_current`,
`native_shared_effects`, `native_shared_observations`, `native_shared_phase`,
`native_shared_policy`, `native_shared_receipts`, `native_shared_stage`,
`native_shared_streams`, `native_shared_execution`, `native_shared_gates`,
`native_shared_permissions`, `native_shared_publication`,
`native_shared_registration`, `native_shared_results`,
`native_shared_schema_gates`, `native_execution_engine`, `native_gate_engine`, and
`native_subscription_guard` (all under `data_sheets_schema`). Legitimate dynamic
constructs in reviewed dependencies, including U2, are allowed. Implicit
parent package initializers below `data_sheets_schema` are part of this graph
and are compiled from pinned bytes too, including empty initializers. A missing
or ambiguous initializer pin refuses; nested namespace packages are not supported
by this closed consumer interface. Every reached package module is source-loaded
with a recorded digest, including attribute imports and runtime imports from
reviewed dependencies; cached package bindings are temporarily replaced and
restored. Imports of either U3-A verifier boundary module refuse, including
`from .native_execution_registration_v2 import selection` and function imports.
Consumers must use direct package dependencies, not bootstrap re-exports.
Dependency function bodies may define deferred legacy routes (for example,
`api_runner → native_shared_render`); they are not executed by importing the
module. The static dependency traversal covers import-time code; the finder
source-loads deferred imports when reached and refuses v1 authority then, even
when already cached. Consumer-owned modules are linted in full, including their
deferred bodies. This admits shared utilities without authorizing their v1 routes.
The guard is **lint**; independent source review plus digest pins are enforcement.
Assigned `__signature__`, `sys._getframe`, `inspect.currentframe`, and `sys.modules`
are refused in consumer-owned source as cheap hardening, not a sandbox against
hostile Python, external dependencies or arbitrary preexisting references.
The consumer is absent at U3-A, so complete execution admission is
intentionally closed until C/D implement and test these contracts.

Review, CI and owner evidence use version 2 and kinds suffixed `_v2`, binding
the full outer execution bytes, attempt id, source commit and dependency hash.
Independent approval, the full explicit CI roster and the exact owner word
remain required. The owner artifact also binds review, CI and permission-probe
hashes. These are supplied declarations, not cryptographic authentication or
permission to contact a service. Budget is the runtime's declared positive
decimal guard, not measured provider billing.

CI evidence explicitly names `workflow_event`, `workflow_ref`, `tested_commit`
and `workflow_sha256`. The digest field is an exact path-to-digest map:
`.github/workflows/main.yaml` for every event, plus
`.github/workflows/large-files.yaml` for pull requests. Each must match current
bytes and both the reviewed source commit and tested commit. For a PR,
`workflow_ref` is `refs/pull/<positive-number>/merge`; the locally available tested
commit has exactly two parents with the reviewed source as its second parent.
For push/manual events, tested commit equals source; the ref is respectively
`refs/heads/main` or an explicit branch ref. This checks declaration consistency,
not a remote service's attestation. `required_checks(event)` requires all named lanes: PR means eight
shards, four API cases, three SG2 cases, three offline lanes, aggregate `test`
and `large-files`; push/manual means six shards, the same API/SG2/offline lanes,
`test` and `schema-examples (3.12)`. The PR-only large-files check is not invented
at a merged-main commit. No event is inferred; every applicable check must
report completed/success with `head_sha` equal to the exact **source** commit
for every event. For PRs this is the PR head; `tested_commit` separately declares
the merge tested by Actions. Actions run URLs are
bound to local `d4d.ciRepositoryUrl` configuration or `remote.origin.url`, never
to a built-in repository. An independent workflow-derived
test guards this frozen interface against roster drift.

An `Admission` is only an observation. U3-D must call `admit` freshly immediately
before its first reservation/probe/dispatch effect, enforce durable one-use
reservation, and retain post-dispatch/saved-readback gates independently. It
must never cache a prior accepted verdict or treat preparation as launch
permission. U3-A tests can prove genuine S/R preparation and fail-closed
boundaries; complete shared execution, actual saved permission checking and
all fifteen runtime results remain C/D and combined U3-E acceptance work.

All source additions change the complete package identity. Use fresh
registrations on the final reviewed integrated commit. Preserve historical
source environments and records; U1/U3 land together and the protected packets
remain separate approval work. No protected packet is applied by U3-A.

### U3-D integration checkpoint (D95)

The fixed v2 consumer and shared execution modules now reconstruct the full
execution registration, require fresh U3-A admission immediately before the
first reservation, and retain the fifteen post-dispatch gates. This checkpoint
does not establish integrated acceptance. Round 6 merges U3-C and the initial
U3-B owner-context handoff; B's review repair and genuine admission through the
revised A consumer boundary remain separate requirements. No native executable
is authorized by this engineering checkpoint.

Saved readback revalidates the consumed review, CI and owner artifacts and
their original path/byte identities. It independently replays completed
subscription event streams. A failed attempt's buffered transcript can extend
beyond callbacks actually delivered, so its saved observer count and stop
remain explicitly unverified rather than being certified by that suffix.

Native shared-v1 intentionally retains its pinned native receipt-v1 policy
and receipt instrument 4 under D91. The ordinary/API receipt-v5 path remains
unchanged; authority version 2 does not upgrade the native receipt instrument.

The R9 contract now separates `phase1_receipts --initial-structure` from
`final_receipts --strict`. Exactly eighteen helper names are recognized by
exact command equality. Initial output has a closed JSON shape and pending
floors; final acceptance requires strict completion and current artifact
epochs. Its stdout misassociation check requires the exact final-stage line
and refuses whole JSON or standalone structural markers, not words quoted in
findings. These contracts survive the C merge. They do not establish a
successful end-to-end native route or override the A3 consumer import guard.

Offline review ledger (issue publication deferred by the no-GitHub rule):

- U3D-R1: completed saved subscription counts/stops were trusted. Recompute
  them from all ordered captured events; disclose failed-prefix uncertainty.
- U3D-R2: saved readback did not revalidate consumed v2 review/CI/owner bytes
  or bind started/final authority maps. Revalidate both and captured roles.
- U3D-R3: a new transformation test incorrectly expected an arbitrary selected
  schema to be supported by the fixed transformation specification. Preserve
  that refusal; separately test supported default-schema receipt opt-in.
- U3D-R4: Write success text accepted a conflicting path suffix. Require exact
  success text/path agreement and test rehashed contradictory observations.
- U3D-R5: the initial strict-check exemption accepted a pending floor. Removed
  the exemption; the later R9 amendment supplies separate structural and strict
  receipt commands without certifying initial pending coverage.
- U3D-R6: the offline E proposal could verify before its complete fixed gate
  implementation could import. Keep proposal construction available, but
  refuse outer verification/admission until that implementation loads and its
  fixed gate roster checks. Missing U3-B remains a refusal, not admission.
- U3D-R7: a recovered no-input-I/O test rejected legitimate root-relative
  package source reads. Use the exact v2 source/interpreter roster for both
  spellings and remove its overly broad allowance for any repository path.
- U3D-R8: two U3-A absence tests assumed D's consumer could never be installed.
  Explicitly inject the missing declaration at the refusal boundary and retain
  the same-origin stand-in rejection. The public verifier still performs real
  preparation/source validation first; frozen v2 production code is unchanged.
### Round 2 migration and trust boundary

Round-6 D implements the exact required `rebuild_v2_body` signature, accepts
only its nine input keywords, checks fresh preparation byte/hash binding, and
requires explicit `execution_paths_v2.extra_protected`. This is partial
interface alignment, not admission. The genuine consumer graph still imports
A's verifier/bootstrap boundary, v1 runtime validators and lifecycle helpers;
inherited C composition/control paths also reach those boundaries. A3 refuses
this graph before loading it. No import exemption, dynamic loader, roster
removal or alternate trusted module path is introduced to admit it. The
positive execution tests remain integration requirements. D's offline command
builder also still needs a reviewed pure permission-argument interface: A's
narrowed control map does not expose `native_command_policy`, and C's current
pure projection does not expose `permission_arguments`. These boundaries
must be resolved together before claiming a runnable integrated native route.

The round-1 U3-C/D checkpoints are not consumers of this revised interface.
Their later integration must supply `rebuild_v2_body` with the exact signature,
remove the default on `execution_paths_v2.extra_protected`, separate their pure
runtime utilities from imports of frozen execution authority, and obtain command
policy through a separately reviewed interface rather than the narrowed U3-A
control mapping. U3-A does not modify those branches or reopen live admission.

Malformed envelope shapes, versions and manifest digest values refuse using
already imported constants before Git or helper loading. `admit` refuses a
non-main-thread call before verification. Valid envelopes still need local Git
and verified source compilation; ordinary initial interpreter/package imports
and external dependencies are the trusted bootstrap. In particular the verifier's
own modules (`native_execution_registration_v2`, `native_execution_authority_v2`)
and their ordinary imports, including the U2 v2 authority modules and pure v1
runtime validator, load through the **normal import system**, with its usual
bytecode behavior. They are the trust base, not source-attested by this guard.
After pure envelope checks, `_wire` proves the captured closure committed before
loading any preparer helpers. The byte-only loader proves
the bytes of the scoped helper/consumer graph it executes, not every object
already resident in Python or the authenticity of review/CI declarations.

Round-3 local review ledger (GitHub filing deferred by the offline ruling):

- **R3-A, addressed:** a cached package module absent from the source roster
  could bypass the finder during a dependency's deferred import. The consumer
  context now temporarily removes all resident package-module bindings, including
  unpinned names; the finder refuses missing pins. The regression checks both
  refusal and restoration of the preexisting cached module.
- **R3-B, addressed:** the real-dependency loader fixture initially asserted the
  C/D consumer was absent, which would break later integration. It now supplies
  its own fixture consumer bytes regardless of whether C/D has been merged;
  the test does not claim admission or committed proof for that synthetic root.

Round-2 review records, retained offline for the later issue workflow:

- P2-1: closed execution keys, exact consumer signatures and source identity,
  input-only reconstruction, legacy-import refusal and checked path return.
- P2-2: independent named refusals with owner evidence hashes re-bound in tests;
  the report records each mutation probe and its actual result.
- P2-3: compile verified source bytes rather than path/bytecode imports at the
  U3-A boundary; unchanged U2 code is not edited or used as a path loader here.
- P3-1/P3-2/P3-3: early structural refusal, workflow/merge identity and generic
  origin binding, and a narrowed exposed control mapping.
- P3-4/P3-5: meaningful absence assertion, reusable test utility outside dated
  scripts, isolated test Git settings, dead-import removal and accurate Git
  environment documentation.
- R2-A: independent review identified an unpinned selection reread in reservation
  checking; compare that fresh capture with the preparation pin before using it.
- R2-B: ordinary field `getattr` must not be mistaken for dynamic import; keep
  actual loading/evaluation refusal without excluding normal pure helpers.
- R2-C: a read may update access time without changing source. Compare device,
  inode, mode, size, modification time and change time across the read; retain
  physical-path and digest checks. Access time is not source identity.
- R2-D: importing a child implicitly executes its package initializers. Include
  those parents in import inspection, source-only loading and binding restoration;
  refuse an unpinned or ambiguous parent before import. An unchanged regression
  failed before this repair because a legacy import only in the parent was missed.
- R2-E (test fixture only): give synthetic import bindings one cleanup owner.
  Overlapping finalizer/monkeypatch cleanup raised after passing loader assertions
  and left the test namespace unrestored; retain that failed driver evidence.

### U3-A offline review ledger

Issue publication is deferred by the offline instruction. Preserve these
findings for the later issue/review workflow:

- U3A-R1 (fixed): a fresh runtime read during the preparation/execution join
  must match the original preparation pin, not merely the execution's JSON
  value. The exact captured pin is now compared before use.
- U3A-R2 (fixed): a preloaded same-path consumer object must not substitute for
  an absent future C/D source file. The fixed consumer must be present in the
  committed package map and its actual regular-file bytes must match that pin
  before import/interface use.
- U3A-R3 (fixed, found by preparation canary): the producer emitted a carrier
  pin including `role`, while its verifier required the three-field file-pin
  contract. Preparation and the runtime reread now use the same exact
  path/bytes/SHA-256 representation. The failed canary is retained.
- U3A-R4 (fixed): copying the legacy six-shard CI list did not describe current
  PR or main evidence. V2 now binds the event and committed workflow bytes and
  requires the complete applicable roster, independently tested against the
  current workflows. Frozen v1 evidence rules remain unchanged.
- U3A-R5 (coverage strengthened; integrated acceptance pending): initial
  cross-version tests used a minimal v1 header and a genuine v2 preparation.
  The added test constructs a complete synthetic v1 execution registration,
  verifies it through v1, then requires envelope-specific v2 refusals without
  reservations. V1 also refuses a v2 execution wire/join prefix. A complete
  valid v2 E and positive execution admission still require the C/D consumer;
  wire rejection must not be described as that integrated acceptance.
- U3A-R6 (test-driver correction): full collection produced repeated identical
  own-package namespace entries, which the driver's single-entry comparison
  incorrectly called a mixed origin. Accept only a nonempty namespace whose
  every resolved member is exactly the own package directory, retaining the
  raw/resolved lists with duplicates. Empty, mixed, foreign and subdirectory
  roots still refuse, as do foreign loaded modules/subpackages and editable
  finders. No production authority rule or namespace is altered. The initial
  23,343-node collection's wrapper failure is retained; its later origin checks
  were not reached and cannot be claimed passed.

### U3-C captured controller and delivery

U3-C consumes the U3-A preparation wire through these interfaces in
`native_shared_controller`:

```python
compose(preparation_raw: bytes, *, instruction_path) -> dict
verified_composition(raw: bytes) -> dict
reconstruct_composition(raw: bytes) -> tuple  # C, replay RunSpec, captured S
captured_execution_body(raw: bytes) -> dict
captured_preparation_body(raw: bytes) -> dict
```

Composition and reconstruction freshly verify the complete preparation, then
bind the exact instruction, S, R, render specification, dependency identity,
v2 control policy and working directory. The scientific procedure remains
native-shared **version 1 / renderer 26**; the authority wire is **version 2**.
The two captured parsers only check wire identity. They neither authorize
effects nor replace current-source verification. Live callback construction,
activation and capture entry freshly call the full U3-A execution verifier.
There is no U3-D consumer here, so those entries remain closed.

The stage engine reconstructs receipt completion, every typed worker, source
omission review, integration and assembly from original captured bytes. Original
receipts remain separate from effective receipts. Request/response observation
joins require complete Read bytes, the first settled Write, ordered callbacks,
matching sessions and durable stream prefixes. Stage and receipt result caches
from the donor are removed. Only U3-B's bounded schema/catalog and typed pure
derivation interfaces may be reused; a prior accepted replay is never authority.
This conservative recovery makes no performance claim.

The U3-B owner context is intentionally absent from the pre-integration C
receipt fragment. Integrate **committed** U3-B using a merge commit, preserving
its owner section exactly and appending the C delivery section. Do not replace
that dependency with a mock owner, copy an uncommitted owner implementation or
declare criterion 3 complete from the independent observer suites alone.

Saved attribution now requires `captured_instruction` as a separate immutable
artifact. It joins that artifact to C and the preparation without host reads.
Its caller must independently verify canonical C/E; the saved attribution
result only establishes its own identity/observation checks. It does not
establish canonical instruction rendering, execution admission, permission,
publication, final record acceptance or scientific correctness. U3-D owns those
remaining gates, durable publication and the complete execution lifetime.

### U3-C offline review ledger

These local findings are retained for later issue publication; this task
forbids GitHub operations. Test execution status belongs in the U3-C report.

- U3C-R1: saved attribution compared instruction hashes only within E/C/the
  preparation. Require the independently captured instruction's exact
  role/path/bytes/hash and a consistently rehashed substitution refusal.
- U3C-R2: donor record/journal acceptance caches reused verdicts, and shallow
  copies exposed nested payloads. Remove both caches; add mutation and warm
  validator-refusal regressions. Preserve bounded pure derivation reuse only.
- U3C-R3: preliminary suite collection found that the donor imports
  `coverage_counts`, which current API policy does not expose. Keep the
  released counter checks locally in native receipt delivery; do not change
  the API policy route or invent an API registration. The failed collection is
  retained, and B-dependent imports remain pending the real B merge.
- U3C-R4: the first integration fixture restarted synthetic streams at each
  stage. Retain cumulative same-attempt streams and resolve every observation
  against one final immutable pool, including monotonic endpoint checks.
- U3C-R5: a draft comment claimed a fresh final receipt context while reusing
  the live context. Final reconstruction now constructs a fresh owner context
  and rechecks the complete stage/assembly lineage before receipt assessment.

The fixture's execution wire is explicitly synthetic and grants no admission.
Its typed helpers and raw Read/Write/chronology joins are real computation;
successful execution of that test would establish this captured boundary,
not a real native run, provider accounting or a published receipt-to-record
path. U3-D and combined U3-E retain those acceptance obligations.

### U3-C round-2 integration contract

U3-C now merges the committed U3-B owner context and U3-A round-2 bridge in
separate merge commits. The B owner prefix in `native_shared_receipts.py` is
preserved byte-for-byte; C's marked delivery section follows it. Typed replay
threads B's private catalog association through every worker/index/assembly
call. Each history, response and final verdict is still reconstructed; final
assembly uses a new derivation cache and final receipt assessment uses a fresh
owner context.

Captured E parsing applies A's exact closed execution-key contract. This is a
pure shape check, not a call to `verified` or evidence that its values are
admissible. Synthetic test carriers now have the explicit closed roster and
remain clearly marked as non-admitted fixtures. The actual U3-D consumer's
`rebuild_v2_body` and `execution_paths_v2` implementations do not belong to C.

`native_shared_controls.loaded_controls` is C's fixed policy projection during
A's verified-byte loader lifetime. It binds the fixed helper source identities
and exposes only enumerated pure grammar/lookup functions, copied constants and
the BudgetStop exception type. No historical launcher or caller-selected module
is exposed. Pure function wrappers refuse after the scope closes; constants are
copied and source identity is checked before use. The ordinary classifier recipe
is compared with the source-pinned implementation in offline tests. Callback
classification opens a fresh scope instead of retaining historical modules.
C makes no change to A's public two-helper map or source/consumer refusal rules.
Read-only lookup helpers may inspect declared filesystem paths; "pure" here
does not mean byte-only or free of filesystem reads. It means no launch,
publication or admission side effect.

The inherited attribution observer now comes from the existing v2 module;
its observe/report implementation is the same, without importing the v1
registration route directly from C's attribution adapter.

Complete recursive consumer-graph compatibility remains an explicit integration
gate. A lints owned modules in full and guards dependency imports when reached:
the deferred route in frozen `native_shared_render._runtime` imports
v1 runtime constants, and C's publication helpers reuse frozen execution effect
primitives. A's later source/CI review repair allows legitimate dynamic loading
inside reviewed dependencies, including U2, but now refuses both verifier
bootstrap boundaries throughout a consumer graph. C's ordinary controller,
capture and control-projection entry points still call those boundaries; they
cannot be placed inside D's pure consumer closure. `native_shared_controls` is
not in A's closed consumer-owned lint roster, but its authority import still
refuses; omission from that roster is not an admission workaround.
No C trusted-boundary expansion, protected edit or U3-D fallback bypasses these
refusals. A separately scoped dependency/interface decision is required
before the full C/D graph can enter A's consumer loader. This does not prevent
offline composition and typed captured computation; it does prevent a claim of
complete execution admission on this C branch.

Round-2 findings retained for the later issue workflow:

- U3C-R2-1: history replay referenced an undefined session variable. Bind it
  from the captured execution and reject consistently rehashed foreign sessions.
- U3C-R2-2: only packet preparation and final checking received B's private
  owner association. Thread it through all typed replay calls; verify real
  parser reuse against a fresh control, initialization invalidation, and fresh
  valid/invalid response and final-verdict checks.
- U3C-R2-3: saved advance acknowledgements did not repeat the live path's complete
  identity/publication checks. Use one pure validator for both paths, retaining
  ordered Read/Write/callback joins and reconstruction from immutable history.
- U3C-R2-4: round-1 policy code indexed helpers no longer exposed by A. The fixed
  pure projection replaces those accesses, without restoring launcher exports.
- U3C-R2-5: C's captured E parser and synthetic fixtures had only a partial body.
  Apply the closed A roster, preserving the separation between parsing and
  admission and testing missing/unknown fields without live I/O.
- U3C-R2-6: a direct constructor could create a lookalike private control map.
  Require loader-created provenance plus the exact key/member/type/source roster,
  and check guarded helper state after calls as well as before them.
- U3C-R2-7: the first saved-reader canary compared captured and proposed artifact
  classes directly. Compare their exact pin and raw bytes; the different carrier
  classes correctly distinguish observed bytes from a proposed publication.
- U3C-R2-8: the later A runner change polled lock acquisition only once per
  minute. Restore detection on each active runner tick; once paused, poll for
  removal at most once per minute. Synthetic tests cover acquisition, held-lock
  polling, release/reacquisition and slow filesystem observations. No generation
  or execution authority changes are part of this runner repair.

The report records actual test results and remaining gates. No declaration here
authorizes dispatch, changes the shared-v1/native26 procedure, or substitutes for
combined U3-E acceptance.
