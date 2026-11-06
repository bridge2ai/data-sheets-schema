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
