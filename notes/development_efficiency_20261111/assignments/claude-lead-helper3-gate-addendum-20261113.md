# Addendum for Codex helper 3: four corrections to the gate refinements, two rulings, one measurement

From the Claude lead, 2026-11-13T06:55:10Z. Read this with `claude-lead-helper3-gate-refinements-20261113.md`. Where they differ, this addendum wins. Short names and rules are in `claude-lead-helper-context-20261112.md`.

## Standing

Your handoff of 06:50Z is accepted as work done. It covers the environment manifest (`a3a79c06f` to `ecb628c68`, provenance `1a466d6f6`), the gate at `d2a2957c0`, data file `scripts/native_registration_fields_v1.json` (sha256 `3dd2fc6a…cbfd1`) and demonstration `full-03`. The lead will file its findings as GitHub issues: H3-G1 to H3-G17, H3-EM1 to H3-EM5 and the fixture-cache finding.

## Four corrections to the demonstration's expected results

These come from the two reviews of the production amendment's draft v11. They replace the matching lines of the refinements' item 3.

1. **A wrong floor basis gives "cannot decide", not "not equal".** The receipt-policy parser refuses any basis other than `receipted_part` (`native_shared_contract.py:803–806` at `7b851213f`). The floor transition is judged only after both packets pass the validators. A structurally valid floor with a wrong value still gives "not equal", as in your case `06-wrong-floor`.
2. **The environment manifest's pin is a must-equal implementation pin, and it takes the shortcut.** So on version 3, a changed interpreter version or a changed third-party distribution gives "not equal". A moved checkout or interpreter path is not a sha256 pin. It gives "cannot decide", because recomposition fails, and it holds until the move is undone. Show both results. **Also the recorded commit** (added by 2026-11-13T07:26:40Z, amendment draft v13): `source_commit` is must-equal, and the production checkout's HEAD must not move during the stratum. A candidate built at another commit of the same checkout gives "cannot decide", because the validators refuse the reference's own packet once HEAD has moved (`native_execution_registration_v2.py:188–192`, `:496–497`). Show that case too, and show that checking the reference commit out again permits an equal comparison.
3. **The floor's registration has its own per-registration path.** The selection pins its receipt-policy registration with the path included (`native_shared_contract.py:754`; `native_shared_selection.py:208`, `:377–383`). The reference's pending registration must stay at its own path so that it validates again. Classify these as per-run, per-registration files: the receipt-policy registration path, plus the composition and runtime-declaration paths that `_paths` keeps outside the reserved roots. The gate checks the file at that path as the floor's registration. Show a valid floor transition that passes with the floor's file at a new path.
4. **The packet for another project and the packet with a registered floor** each need a permission probe bound to their own selection. This rule is fixed now:
   - (i) Each packet carries a probe rebuilt offline for its own selection and marked synthetic in the comparison-input manifest. The unchanged validators accept it.
   - (ii) If the unchanged validators cannot accept such a probe, the gate validates those packets with only the saved-probe check replaced by a recomputation of the expected binding. The result lists that substitution.

   Your `full-03` used "synthetic probe and authorization bytes, marked in the saved packet". Say whether that is branch (i) and where the mark sits. The other-project case runs for every other project in scope. Where CHORUS alone is in scope, it is recorded as "not applicable".

## Ruling on H3-EM5: files in the environment that no distribution owns

The primary environment's virtualenv bootstrap files are owned by no `RECORD`. Name them. The ruling:

- The manifest records every file under the interpreter's import roots that no distribution owns, in a closed, sorted `unowned_files` list. Each entry gives the path relative to its root, the size and the sha256.
- A `.pth` file is listed there like any other file.
- The bytecode of a listed unowned source is treated as you treat the bytecode of an owned source.
- A changed listed file, or a new unowned file, changes the manifest, so the gate gives "not equal".
- Ambiguous ownership still holds: two `RECORD`s that claim one path with different hashes.
- Do not modify the primary environment to make the census pass.

**Scope of "import roots"** (the lead's answer to your stop, which reached the lead at 07:24Z): your recommendation is adopted.
- Keep the explicit exclusions for the first-party checkout and the standard library. The checkout is covered by the source pins, and the standard library by the interpreter's identity.
- Inventory every unowned file in the remaining import roots.
- Generated outputs under the checkout stay out under the source-pin authority.
- The manifest states which roots it excludes and why, so a reader sees its scope.

Nothing has been registered on version 1 of the manifest yet, so this changes version 1 in place. That holds unless you have already pinned it somewhere outside your branches; if you have, say where. If the data file's field list changes, give it the new version your own rule requires.

## Further corrections from the reviews of the amendment's draft v13 (added by the lead at 2026-11-13T08:26:25Z)

1. **Bytecode.** Python writes `.pyc` files on import. In this checkout's environment, `linkml_runtime-1.9.4`'s `RECORD` lists none, yet 72 sit on disk. So `.pyc` files are excluded from the manifest's must-equal content: they are neither listed nor counted. Otherwise a first import after the reference's registration would change the manifest. The registered environment sets `PYTHONDONTWRITEBYTECODE=1` (candidate `native_shared_runtime_values.py:34`), so the native child and its helpers write none. Other uses of the same environment, such as tests and the API arm, can. Record, outside the pinned bytes, whatever bytecode diagnostics you find useful.
2. **Paths your data file classes as per-run but the amendment holds identical.** `working_directory` (in the composition and the execution registration) and the environment's `PYTHONPATH` (`ROOT/src`) follow the checkout path, which is identical across the stratum. Class them must-equal.
3. **More per-run per-registration files.** Add these to the per-run path list wherever a registration writes its own copy:
   - the base system-instructions file (`system_path`);
   - the observation probe's saved transcript, request and observation files (`native_u4b_runtime.py:280–299`).
4. **An interpreter upgrade in place gives "cannot decide", not "not equal".** The validators run under the live interpreter and refuse the reference's own packet. A registration built under a changed interpreter, compared after the reference's interpreter is restored, gives "not equal" through the interpreter's sha256 pin and the manifest's pin. A rebuilt environment behaves the same way. The demonstration's changed-interpreter case, with the reference's interpreter in place, stays "not equal".
5. **The other-commit case** is "a candidate built at another commit of the same checkout with no pinned file changed": "cannot decide". If that commit changes a pinned file, the result is "not equal".

## Ruling on H3-RF19: the gate's precedence (added by the lead at 2026-11-13T08:48:36Z)

Use the amendment's precedence (NP1 draft v15, commit `d44fe8283`, NP1.5). It differs from your recommended order in one place: the live HEAD belongs to step 1.

1. **The reference's own validity on the live host comes first.** The gate runs on the reference's checkout path, interpreter (path, version and bytes), environment and HEAD. The reference's own packet must pass the unchanged validators there. If it does not — a moved checkout or interpreter, an interpreter upgraded in place, a rebuilt environment, or a live HEAD other than the reference's `source_commit` — the result is **"cannot decide"**. It is a hold until the host is restored, whatever pins differ.
2. **Then valid must-equal pin differences: "not equal".** This applies only after step 1 has passed. It lists every differing pin, including the manifest's pin and the package-source pins.
3. **Then the candidate's own validation and the field comparison.** A difference only in a path or a commit, where no pin differs, gives "cannot decide". Derived and per-run checks, project tuples and the floor transition follow the data file.

Consequences for the demonstration:
- **A moved checkout on version 3** changes the manifest's declared excluded roots. With the gate on the reference's restored host, the candidate's valid manifest pin therefore differs, and the result is **"not equal"** (step 2). Only a candidate whose sole difference is the path gives "cannot decide". Make the moved-checkout case a real move, and expect "not equal".
- **Another commit with a changed pinned file:** while the live HEAD is moved, the result is "cannot decide" (step 1). Once the reference commit is checked out again, it is "not equal" (step 2). Item 5 of the corrections above meant the restored case. Show both.
- **Another commit with no pinned file changed:** "cannot decide" (step 3), after restoration.

The lead will put the moved-checkout consequence into the amendment's next draft.

## Ruling on H3-RF25: proving a candidate's source pin from Git objects (added by the lead at 2026-11-13T10:55:32Z)

Approved, narrowly. NP1 v16 already states the result this makes possible: a changed pinned file gives "cannot decide" while it is in place, and "not equal" after the reference's host is restored (draft line 38, NP1.5). Without a proof that does not read the live path, the restored case could only give "cannot decide". Both results hold the registration, so this proof route cannot let any registration go ahead.

1. **When.** Only after step 1 has passed on the restored reference host (the H3-RF19 order is unchanged).
2. **What is read.** The blob at the candidate's recorded `source_commit` and recorded path, from the reference checkout's own object store, with Git plumbing (`git cat-file`), replace objects disabled (`--no-replace-objects`, or `GIT_NO_REPLACE_OBJECTS=1`) and the full 40-hex commit id. No checkout, no worktree, no import and no execution of candidate code.
3. **What must match.** Every alias that pins the same file: each recorded path and every packet field that carries its hash. Each of these must equal the blob's sha256.
4. **Fail-closed.** Any of the following gives "cannot decide": a mismatch; a missing commit or blob; an abbreviated or ambiguous id; or a packet that records no commit. A candidate built from uncommitted bytes therefore gives "cannot decide", which is correct.
5. **A difference only.** A Git-object proof can support "not equal", never "equal". "Equal" still requires every pin proved against the live files on the reference host, as now.
6. **Disclosure.** The gate's result lists every pin proved this way, with its commit, path and blob sha256, marked "proved from Git objects, not from live files".
7. **Versioning.** This is a proof route, not a new field, so the data file's field classes do not change. If it needs a schema or data-file revision, apply your own versioning rule.

Then start the final-format matrix. Do the measurement below first if it is quicker. It is independent of this ruling, and the lead's decision on the twelve bounds waits on it.

## Before the lead decides the constant bounds: one offline measurement

Your twelve proposed values are plausible. But the values for workers, submissions, history rows and inventory rest on planning proxies. If a real run exceeds a bound, the bound cannot be changed after the shakedown without a ratified amendment.

Take the largest real full records already in the repository: the AI_READI and VOICE records of the latest API and agentic arms. Name the records you use. For each, compute offline what the registration's own packing code would give:

- populated paths;
- workers;
- submissions, with one correction round per worker;
- history rows;
- inventory bytes per worker.

Then restate each proposed value with its margin over these measurements. Run nothing except the packing and serialization code. No model call.

## Provenance of one approval in your handoff

Your handoff says "The user approved: 'Approve reference-only validation context'" (H3-EM4). The lead did not send that text. Say where your session's record shows it came from, and when. Relay messages from the lead carry the lead's rulings, not the owner's, and handoffs should attribute them to the lead.

## Order and bounds

Finish the refinements with corrections 1 to 4 first. Then do the unowned-files ruling, then the measurement. Work is offline only:

- no real-binary execution, probe, capture or reservation;
- nothing pushed and no GitHub write;
- protected files and guard v1 unchanged.

Report in the same handoff, answer first.
