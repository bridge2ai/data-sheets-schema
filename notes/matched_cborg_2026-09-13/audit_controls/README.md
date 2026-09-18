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

A successful result is `completed_pending_independent_review`. Scientific review
must assess grounding and audit completeness separately. Reconciliation, report
production, final pair acceptance and evaluations require subsequent registered
stages. Preserve the stopped source run, rejected audits and all billing evidence.
