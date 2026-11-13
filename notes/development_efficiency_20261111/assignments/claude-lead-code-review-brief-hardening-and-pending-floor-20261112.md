# Review brief: two sets of native-route repairs (read-only)

Read-only adversarial code review. You wrote none of this code. Do not edit, commit, push or write to GitHub; run no test, no model or provider call, and nothing that executes the Claude Code binary. Read with `git -C <worktree> show` and `git -C <worktree> diff` only. Your invocation names which of the two parts is yours.

Context: the native agentic route of this repository runs a generation under a registration, with a launch sequence script (capture, guard, launch), a receipts check and a completion gate. The rules it must implement are in amendment N1, draft v12: `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema show c289eed19e37e227e04dd5e0c4fc077da54184aa:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md` (items (z), (aa), (ab), (ac), (ad); sections N1.4 and N1.9). Owner decisions are in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (`grep -n` for `D109`, `D113`, `D115`).

## Part H: launch-sequence hardening

Worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-launch-sequence-hardening-20261112`. Base `0fc003a86081891abbe8e130ac760c01da06423e`; three commits: `b832233b798da1f350a764f49f19039195fab4c5` (issue 5989), `9abf48b31122da7a89ba462274a8e3980d1b7973` (issue 5990), `c1ad9baa19a5b938d7976541bed27a73eee32d8c` (issue 5991). The author's account: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h3-launch-sequence-hardening-20261112.md`. The findings they answer are the three `H3-X` sections of `.../handoffs/codex-h3-all-project-prefix-and-cross-review-20261112.md`.

Questions:

1. **Issue 5989.** Can one delegated direction still start two sequences: by a different packet path, a different working directory, a symlinked or replaced state directory, a different spelling of the same instant, two concurrent starts, a crash between the claim and the first command, or a registration re-issued with other bytes? Is the claim written and durable before any capture effect? Can an owner start be mistaken for a delegated one or the reverse? Does anything now block a start the rules allow?
2. **Issue 5990.** Are the bytes that execute exactly the bytes that were compared with both pins and the bytes retained in the packet? Is there any remaining path that runs the sequence body without the entry (the old `main`, `python -m`, an import), and does that path refuse or verify? What does the entry itself trust, and is that stated honestly?
3. **Issue 5991.** For each of the three child commands and each input document: is the digest compared on the bytes actually consumed, before any effect (capture, word state, reservation)? Is there a caller that omits the pins and still reaches an effect in the reviewed sequence? Can the pins argument itself be replaced?
4. **Regressions.** Does any change weaken a check that existed at the base, alter guard v1, or change the kind or version of a registered document? Do the new tests assert the property, or only a message an earlier refusal also produces?

## Part F: the pending coverage floor

Worktree `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-main-integration-20261112`. Commits `e5fe279a3a685985c51589c867632424e8c110c4` (the repair) and `dd791a99c` (a public-completion test under a pending floor); read `git show` of each, and the surrounding source at `2be7c3d769ee2d23cb117b9177aa45cef22f746d`. The defect is issue 5939: the owner decided (D109) that the first canary's receipt coverage floor stays `{state: pending, mode: diagnostic_pilot}`, reported and not gated, but the final `receipts check --strict` and the receipts gate failed on it. The author's account: `.../handoffs/codex-h1-integration-and-pending-floor-20261112.md`.

Questions:

1. Under a pending floor, does every structural receipt floor still gate at all three places (the strict command, the recorder's block, the independent receipts gate)? Name each floor and where it is enforced.
2. Can anything other than the captured selection's registration select the exception: a field of the receipt block, a flag, an environment value, a registration of another run, a selection that was not captured? Can a registered (numeric) floor be made to look pending?
3. Is the API route's use of `receipts check --strict` byte-for-byte the same in behaviour as before for every input? Look at the changed conditions in `cli/receipts.py` for an input where `native_capture` is set unexpectedly or unset unexpectedly.
4. `final_receipt_floors` raises on an inconsistent block. Is every raise turned into a refusal (non-zero exit, gate not passed) at each call site, never into a pass or an unhandled crash that a caller treats as success?
5. Is the pending reading still reported with `state: pending` and `passed: False` everywhere it is written (the block, the provenance record, the gate result), so that it can never be read as a pass?
6. Do the new tests cover a pending floor with a structural failure, a registered floor that fails, a registered floor that passes, and the API route unchanged?

## Output

Verdict first for your part: acceptable as is, acceptable after listed fixes, or not acceptable. Then findings headed `### P1-1: title`, `### P2-1: title`, `### P3-1: title` (P1: could let a launch or a completion happen that the rules forbid, or block one they allow; P2: should be fixed before the final review; P3: minor), each with file and line, the concrete scenario, and the smallest fix. Then what you checked and what you did not. Use no at-sign characters.
