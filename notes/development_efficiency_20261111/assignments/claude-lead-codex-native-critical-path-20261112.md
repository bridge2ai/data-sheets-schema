# Assignment to the Codex helper: the remaining path to the first native canary

From the Claude lead, 2026-11-12. Read-only. No run, no test execution, no edit of source.

## Why

The owner directed on 2026-11-12T06:28:30Z (D134 in `data-sheets-schema/notes/coordination/STATUS.md`): "we dont even need the API route except for comparison, the native agentic is the main result". The native arm now has priority. The API canary (A21) has ended; `launch-a21` holds its evidence. Stay out of that worktree.

## What I need

The shortest remaining path from today's native source (`382f0dfd1ce8`, with draft PR 5871 on top) to the first owner-worded native CHORUS canary, as a dependency-ordered list of gates.

Plan under this assumption. It is the lead's recommendation and not yet the owner's decision: amendment N1 item (o) is revised from `max_age_seconds` = 300 to 900, and item (u) stays at 90 s. Both are marked `[proposed]` in the unratified amendment (PR 5542, head `754fbfdae`), whose own text says no launch-path timing had been measured when 300 was written.

## Deliverables

1. `handoffs/codex-native-critical-path-20261112.json`: one row per gate with these fields.
   - `id`, `gate` (one sentence).
   - `required_by`: the owner decision, amendment clause or issue that makes it a gate, with file and line. Write `none found` when no recorded owner decision requires it, and say which kind of search you ran (ignored files included or not).
   - `state`: `done`, `partial` or `not_started`, with the evidence path, commit or PR.
   - `remains`: what is left, concretely.
   - `who`: `worker`, `lead` or `owner`.
   - `effort_hours`: a rough range.
   - `depends_on`: gate ids. Mark gates that can run in parallel.
2. `handoffs/codex-native-critical-path-20261112.md`: the answer first, then tables made from the JSON by a script under `scripts/adhoc/`. Show the command. Do not hand-write table rows.

## The gates I expect you to cover (add what I missed, drop what is not a gate)

- **Code landing.** Which of the open native PRs must merge, in what order, and onto what base (5839, 5857, 5871, 5866, 5852, 5855, 5851, 5840, 5841, 5853, 4659). Which are superseded or evidence-only and can be closed. Whether the stack top has ever been merged with current main `7ad8c9e72` in a preview, and what full CI has run on which head.
- **Protected files.** Whether the four D127 packets are applied on the integration branch, byte for byte.
- **Amendment N1.** What ratification still needs from the owner: the items still marked `[proposed]`, and D-numbers that already settle others.
- **The D117 probes.** Whether the observation probe and the bound permission probe have run, and what they need.
- **The registration.** Whether the tools that build the native CHORUS registration, review bundle, owner statement and launch word exist and have been rehearsed offline.
- **Boundary proof.** What must be shown before a real attempt, and by which run.
- **The operator's sequence.** The exact commands from capture to guard to launch, and whether one script can run them in order so that no time is lost between steps.
- **After the run.** The acceptance rows B0 to B7 and who judges them.

## Three direct questions

1. With item (o) at 900, list every file that changes: source constants, error text, tests, fixtures, amendment text. Does anything else in the design depend on 300 or 210 (deadlines, window-reset checks, the dispatch check, cleanup allowances)?
2. With item (o) at 900, are the later-capture design, structural U3K-F1 (issue 5722) and issue 5836 still gates for the first canary, or follow-ups? Cite the record that makes each one a gate.
3. Between a real capture event and the pre-reservation check, which steps does production have that the synthetic diagnostic did not measure? Give your best bounded estimate for each, labelled as an estimate.

## Bounds

- Read source with `git show` and `git grep` on commits. Read retained evidence and records.
- Write only the two deliverables and one helper script under `scripts/adhoc/` in the report worktree (`codex-development-efficiency-20261111`).
- No test run, diagnostic, composition, configuration change, provider, model or native call, commit, push or GitHub write.
- Do not repeat research your earlier reports settle. Cite them.
- Use no at-sign characters in the deliverables.
- Stop when both files are written. Print their paths and SHA-256.
