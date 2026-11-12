# Assignment to Codex helper 2: the offline proof of the public launch path, with the protected packets applied in scratch

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your review-bundle handoff is accepted: commit `cf53497ae` on `codex/native-launch-sequence-20261112`. Helper 1 is still on the scanner and has not integrated your branches yet. You take the next gate yourself, in your own scratch composition, so that nothing waits on that.

## Why

Amendment N1.4(A) item 6 requires, before a registration: the actual public native adapter exercised with an ordinary Python peer and genuine offline helpers, a successful correction path, an exact failed readback, and the listed failure cases. The critical path calls it gate G11. None of it has passed on the final source:

- **Two public completion tests:** `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion` and `tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses`. The first failed on the observer's model-label defect, which your commit `91fcdab33` fixes; nobody has seen what comes after.
- **Seventeen failure cases** from nine selectors in `tests/test_native_shared_execution_failure.py`, listed with their parameters in `E/plans/reviews/native_u3m_2026-11-09.md`, lines 281 to 297.

On a branch these cannot run, because the four protected files stay equal to main. They run in a scratch composition where the four post-images are applied.

## What to do

1. **Build the composition** in your own scratch directory `E/scratch-h2-public-path-20261112/`, never in a worktree: the candidate's current head (`79089536b` on `codex/native-main-integration-20261112`, or its head when you start; record which), plus your three observer commits (`91fcdab33`, `37a4aa5d0`, `789778427`), plus your four launch-sequence commits (`d07eccefb`, `34b46c313`, `e936cbb83`, `cf53497ae`), plus the four protected post-images. The candidate carries helpers for this: `scripts/adhoc/native_g07_packets_20261112.py`, `prepare_native_g07_runner_20261112.py` and `run_native_g07_tests_20261112.py` (read their `--help`), and helper 1's finished composition with the exact post-images is `E/scratch-native-main-integration-20261112/g07-c/` (`packets/`, `packet-hashes.json`). Verify the four post-image hashes against `packet-hashes.json` before you use them. Report any conflict between the branches instead of resolving it by guesswork.
   - With review bundle version 3 current, the public tests' fixtures have to produce the new pair. If they do not, that is a finding about the integration of your own commit: fix the fixtures on your launch-sequence branch in a new commit and say so.
   - If the composition needs the private test-only Git configuration that helper 1's G07 composition used, set it only inside your scratch tree, and restore and record it afterwards, as helper 1's handoff shows (`handoffs/codex-native-packets-g07-20261112.md`, "Private test configuration restoration").
2. **Run one public completion test first, alone,** and verify its saved artifacts, not only its exit code. Then the second. Then the seventeen failure cases, one selector group at a time. At most two xdist workers; these tests are long.
3. **For every test:** how far it gets, its saved evidence, and for a failure the exact point and reason. A failure is a finding. Fix a defect only when it is in code your own commits introduced. For anything else, describe it precisely, give your recommended fix, and go on to the next test.
4. **Record the reservation-to-dispatch time** (amendment N1.9 item 11) for each test that reaches dispatch: the time from the pre-reservation check to the one-use dispatch check, from the run's own records if they carry it, or by a measurement added in the test harness, not in production code. Name every operation the synthetic path substitutes or leaves out in that stretch (the runtime probe's two commands, the hash of the real binary, the keep-awake acquisition). This run is on a loaded host, so it is diagnostic only: say so.
5. **Separately, time two operations offline,** without executing the Claude Code binary: hashing the bytes of the installed binary file (find it with `command -v claude` and resolve the link; read-only), and acquiring and releasing the registered keep-awake assertion, if the source's keep-awake helper can be called on its own. Three repetitions each. If the keep-awake helper cannot be called without side effects you are unsure of, do not call it; say what you found.

## Bounds

- Offline only. No provider, model or native-binary execution; no `cpu-monitoring` diagnostic; no real capture. Nothing is pushed.
- Nothing protected changes on any branch. The composition lives only in your scratch directory.
- Do not edit helper 1's worktree or scratch directories; read them only.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h2-public-path-proof-20261112.md`, with a JSON beside it for the numbers. Answer first: do the two public completions pass, how many of the seventeen failure cases pass, what blocks the rest, and the measured stretch with what it leaves out. Write a first version after the first public completion test has finished, whatever its result, and update it as you go.
