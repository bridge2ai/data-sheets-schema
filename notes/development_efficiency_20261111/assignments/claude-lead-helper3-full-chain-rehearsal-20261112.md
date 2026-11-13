# Assignment to Codex helper 3: rehearse the whole registration chain in a scratch composition, settle the timestamp procedure, and draft the probe packet

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your builder handoff is accepted (`handoffs/codex-h3-registration-builder-20261112.md`, SHA-256 `8976f16a2de6bb64d63d86e132a307f24685e691b024eaa098358ea01095d8aa`; commit `8567d54adf26bed0c3b6c681b4d9a2aa647dc32e` on `codex/native-packet-builder-20261112`). The lead's reading of your findings:

- **H3-P1** (the protected `RunSpec` refuses the native fields): expected on a branch. The four protected post-images exist in scratch and are applied there; that is where you go next (Part A).
- **H3-P2** (bundle version 2, terms version 1, 90-second margin on your base): helper 2's branch `codex/native-launch-sequence-20261112` now carries bundle version 3 and terms version 2, with a repair (`d2efa55014e131f92733bf2c3a90c0830214dc89`). The margin is not decided: the owner has not answered. The builder must read the margin and every version from the source it runs against and never carry its own copy.
- **H3-P3** (runtime `valid_from` must equal the registration-addition commit's author time): Part B.
- **H3-P4**: accepted as fixed.
- **H3-P5**: Part A is how it gets validated.

From your earlier handoff, H3-F2 (two recorder tests failing in the exported tree) is filed as issue #5965, to be settled by the next complete CI run.

## Part A: the full chain, in a scratch composition (do this first)

1. **Compose** under `E/scratch-h3-packet-builder-20261112/composition-a/`, never in a worktree: the candidate's head (`79089536b698dd2dd968233da4eadc8841f76b10`), plus helper 2's observer commits (`91fcdab3311c65ba8591836db75e241b78cf10ac`, `37a4aa5d0ab07ed270ef6211f35e7a377e2472b6`, `789778427d029ccc2d66b1b926c8921ceef79556`), plus the head of `codex/native-launch-sequence-20261112` at the time you start (record it; at least `d2efa5501`), plus your builder commit, plus the four protected post-images. Helper 2 has done the same composition for its own tests: its scripts are `R/scripts/adhoc/compose_h2_public_path_20261112.py` and `prepare_h2_public_runner_20261112.py`, and the verified post-images with their hashes are in `E/scratch-native-main-integration-20261112/g07-c/` (`packets/`, `packet-hashes.json`). Read helper 2's scripts and reuse their method; do not edit them, and do not touch helper 2's or helper 1's scratch trees. Verify the four post-image hashes before use. Report a conflict instead of resolving it by guesswork.
2. **Switch the builder** to the versions the composition carries (bundle version 3 with `sequence_script_sha256`, terms version 2 with `account_quiet`), in new commits on your branch. If your isolated review adapter needs a change, that is the place.
3. **Rehearse the rest of the chain** with the synthetic profile and fixtures, labelled in the bytes as before: every remaining document after the dependency stop, the composition, permission expectations, the registration itself, the three launch commands' admission up to the stop before any reservation. One test first, alone, with its saved artifacts verified; then the rest.
4. **For every document of your map** say whether the rehearsal now builds it through the production prepare and validate functions, and which inputs were synthetic. A document that still cannot be built is a finding with the exact refusal.
5. Where the rehearsal exposes a defect in source that is not yours, describe it with the line and your recommended fix, and go on. Fix only your own builder and tests.

## Part B: the `valid_from` equality (H3-P3)

Give the source lines that require the runtime's `valid_from` to equal the author time of the commit that adds the registration, and what else reads either value (freshness, the launch word's times, the review bundle). Then propose one procedure that produces the equality without guesswork, for example the registration-addition commit made with an explicit author date taken from the runtime document, by a named script that refuses if the two differ after the commit. Show it working in a scratch repository with synthetic documents, and show the refusal. Say which step of N1.9's order it belongs to, who performs it, and whether any wording of amendment N1 (draft v12) or of your runbook would have to change. Do not choose a date and do not make a production commit.

## Part C: the probe packet, as drafts for the owner

The builder stops at "owner-approved provisional-runtime.json and D117 authorization.json". Prepare both documents as drafts for the real CHORUS canary, as far as they can be prepared without executing the binary and without an owner act:

- every field, its value or the placeholder for it, and where the value comes from (source constant, the installed binary's bytes read without executing it, an owner choice, a later observation);
- the fields only the owner can supply or approve, listed separately in plain words, each with what choosing it commits to;
- the exact probe commands the authorization would cover, how many executions of the real binary they make, what each sends to the provider if anything, and what each saves;
- what the source checks about the authorization before it runs a probe, and what would make it refuse.

Label the drafts as drafts in the bytes. They are not approvals and must be impossible to mistake for one. Nothing is executed.

## Part D: bring the runbook up to date

`notes/native_canary_runbook_DRAFT_20261112.md` on your branch: fold in Parts A to C, the launch sequence script's place in the order (helper 2's `src/data_sheets_schema/native_launch_sequence.py` and its handoff `handoffs/codex-h2-launch-sequence-20261112.md`), and the N1.9 step numbers of draft v12.

## Bounds

As in the context file. No real-binary execution of any kind, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write. Protected files stay equal to main on every branch; the composition lives only in your scratch directory. If the composition needs the private test-only Git configuration, set it only inside your scratch tree, and restore and record it afterwards.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h3-full-chain-rehearsal-20261112.md` with its JSON. Answer first: how far the chain now goes in the composition and where it stops; the timestamp procedure in three sentences; what the owner must supply for the probe packet. Write a first version when the first full-chain test has finished, whatever its result.
