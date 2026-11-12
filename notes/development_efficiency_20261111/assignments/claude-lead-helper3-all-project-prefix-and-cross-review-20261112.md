# Assignment to Codex helper 3: the real-input prefix for every production project, then an adversarial review of helper 2's launch commits

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your full-chain handoff is accepted (`handoffs/codex-h3-full-chain-rehearsal-20261112.md`; branch commit `7e6b994f8aaf861d5e5cc6bbbad9cbba85080367`). The lead's reading:

- The chain is rehearsed with synthetic evidence through registration, the review, CI and word join, and fresh admission. The stops at "D106 requires the selected Max subscription" and at the missing recorded word state are the designed limits of an offline rehearsal (H3-R1, H3-R2): no change.
- The timestamp procedure is accepted as the proposal the lead takes forward: `valid_from` is read from the frozen runtime and used as the author date of the registration-addition commit, and `scripts/native_registration_timestamp.py --verify-evidence` refuses any mismatch. It needs no change to amendment N1.
- The probe packet drafts go to the owner later, after the source is merged. Nine executions of the real binary is the figure the lead will use.

## Part A: the real-input prefix for every project of the production matrix (do this first)

The production runs after the canary cover CHORUS, CM4AI, VOICE and AI_READI (three replicates each) and VOICE_PEDIATRIC (one). Your builder has only ever seen CHORUS. Run its real-input prefix, exactly as you did for CHORUS, for each of the other four projects the source manifest declares, in your scratch composition (`E/scratch-h3-packet-builder-20261112/composition-a/`, or a fresh sibling if you need one). One project first, alone, with its outputs verified; then the rest.

For each project report, from saved outputs:

1. whether the production validators accept the receipt policy, the selection, the schema, prompt and profile pins and the byte inventory; for a refusal, the exact message and the input that caused it;
2. the inputs' sizes as the registration sees them: bundle bytes and lines, number of source documents, number of chunks, the largest chunk in bytes and lines, any chunk marked oversize, and the omission-context and scope declarations that apply;
3. anything project-specific the builder or a validator needed that CHORUS did not (a `source_dir`, a related-but-distinct dataset, a crate policy, a different profile value), and whether it came from the manifest or from code. Anything that comes from code and names a project is a finding: the generation path must carry no project-specific code;
4. whether the bundle and chunk manifest on the branch are current by the repository's own checks (`d4d download audit-bundles`, `d4d bundle chunk --check`), run offline in the composition.

Then one table across the five projects, and the ratio of each project's bundle bytes and chunk count to CHORUS's. The lead needs these for the production amendment's runtime rule.

Kids First is not declared in the source manifest. Say what a registration for it would need that does not exist, from the manifest and the data directories only; do not create anything for it.

## Part B: adversarial review of helper 2's launch-sequence commits (read-only)

You wrote none of this code. Review, as a separate pass and without editing anything, the five commits on `codex/native-launch-sequence-20261112`: `d07eccefb59938f8b625498247259f17e5c155ec` (the retained agy draft, context only), `34b46c3132ab7a5cab4f9bdf7634d38c77321369`, `e936cbb83d091cfab5c2e8b85bdd4c08a1b6b1e0`, `cf53497ae2ebfba1da9c64995590115c48437f77` and `d2efa55014e131f92733bf2c3a90c0830214dc89`. Helper 2's own account is `handoffs/codex-h2-launch-sequence-20261112.md` and `handoffs/codex-h2-review-bundle-v3-20261112.md`. The rules the code has to implement are in amendment N1, draft v12 (`git -C P show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`), items (z), (aa), (ab), (ac), (ad) and section N1.9.

Look for, in this order:

1. a way the sequence could start a second time, continue after a failed or incomplete step, or dispatch outside either 30-minute limit of a delegated start;
2. a way a different implementation, script or document than the reviewed one could be used (import path, environment, working directory, symlink, a file replaced between check and use), including the new source-location read in `d2efa5501` (`SOURCE_ROOT = Path(__file__).resolve().parents[2]`): what does it trust, and can an installed copy or a second checkout change the answer;
3. bundle version 3 and terms version 2: can a version 2 bundle or version 1 terms still authorize a launch anywhere; is `account_quiet` checked as a value or only as a key; is `sequence_script_sha256` compared with the bytes that actually run;
4. the latest-capture rule (N1 item (ac)): is it enforced at both places the amendment names;
5. tests that pass for the wrong reason: assertions on a message that an earlier refusal also produces, fixtures that skip the path under test.

Grade each finding P1 (could let a launch happen that the rules forbid, or block one they allow), P2 (should be fixed before the final review) or P3. Give the file and line, the scenario, and the smallest fix. Do not fix anything. You may run the branch's tests in your own scratch, never in helper 2's worktree or scratch.

## Bounds

As in the context file. Offline; no real-binary execution, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write. Protected files stay equal to main on every branch. Helper 1's and helper 2's trees are read-only for you.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h3-all-project-prefix-and-cross-review-20261112.md` with its JSON. Answer first: which projects pass the prefix and what stops the others; the five-project size table; the count of review findings by grade with a one-line title each. Write a first version when the first project of Part A has finished.
