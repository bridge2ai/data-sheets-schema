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
