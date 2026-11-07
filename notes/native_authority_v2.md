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
| `loaded_dependencies(expected)` | context yielding fixed modules | Verify bytes/origins before and after imports; restore named bare aliases and path state on every exit. Never invoke a historical launcher. |
| `native_execution_registration_v2.prepare(selection_path, runtime_path, *, job_id, run_date, max_draft_checks)` | v2 envelope mapping | Read-only producer using current U1 capture, explicit valid runtime and fresh native26 rendering; no instruction-file publication or attempt reservation. |
| `verify_preparer(raw, *, job_id)` | fresh inner preparation mapping | Pinned `prepare_registration_v2.require_envelope` first, then closed kind, selected job, exact current S/R, render/input/output identity and complete pins. No launch grant. |
| `verified(raw)` | complete current execution body | Envelope first, exact preparation/runtime/composition joins and committed closure, then the fixed U3-D consumer below. Missing consumer refuses. |
| `admit(raw, *, review_path, ci_path, launch_word_path)` | frozen `Admission` observation | Fresh complete verification, v2 review/CI/owner evidence, runtime/budget/host/main-thread validation, fresh disjoint paths and rechecked evidence. No writes or dispatch. |

`prepare` binds exact S and R file pins, job id, run date, draft allowance,
render spec, input identity, instruction bytes/hash, all four outputs and the
complete selected input/schema/asset/package/helper/executable pins. It retains
U1's full validation and does not accept a caller-supplied `RunSpec`. The runtime
validator/fingerprinter is reused as a pure utility from the unchanged runtime
registration module; its v1 verifier/selection/launcher is never called.

The execution envelope's body is explicitly
`kind: d4d_native_shared_execution_registration_v2`, `schema_version: 2`, and
`execution: requires_exact_independent_review_ci_permission_and_owner_launch_evidence`.
It binds `preparation_raw_json`, `preparation_sha256`, `job_id`, `dependencies`,
`runtime`, `runtime_declaration_sha256`, `selection_sha256`, `max_draft_checks`,
`instruction_sha256`, `working_directory`, `composition_raw_json` and
`composition_sha256`. Its `execution_gates` list must equal the fixed fifteen
obligations, in order: terminal, shutdown, first stop, live/saved attribution,
phase/tool history, schema, pair, receipts, evidence, observation, accounting,
runtime authority and keep-awake. These are obligations, not asserted passes.

U3-C must compose the **same** native selection/runtime/rendering bound by this
preparation and publish actual instruction/policy evidence. U3-D supplies one
fixed module, `data_sheets_schema.native_shared_registration`, declaring integer
`AUTHORITY_VERSION = 2` and these interfaces:

```python
verified_v2_body(body_raw: bytes, *, preparation_raw: bytes) -> dict
execution_paths_v2(body: dict, *, fresh: bool, extra_protected) -> object
```

The first must rederive the **entire closed E** (not a subset or a prior passed
flag): genuine C, policy, saved permission recipe/observations, sole runtime,
budget/deadline, receipt authority, input/output/path identities and hashes. It
returns that exact body. It must not call the outer `verified` recursively.
The second rechecks canonical, disjoint, protected-input-safe and unspent
reservations without creating them. It must include native stage reservations.
No input may select a module or callback; another origin, interface or version
refuses. The consumer is absent at U3-A, so complete execution admission is
intentionally closed until C/D implement and test these contracts.

Review, CI and owner evidence use version 2 and kinds suffixed `_v2`, binding
the full outer execution bytes, attempt id, source commit and dependency hash.
Independent approval, the full explicit CI roster and the exact owner word
remain required. The owner artifact also binds review, CI and permission-probe
hashes. These are supplied declarations, not cryptographic authentication or
permission to contact a service. Budget is the runtime's declared positive
decimal guard, not measured provider billing.

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
