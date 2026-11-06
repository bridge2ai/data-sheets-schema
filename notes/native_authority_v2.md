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
