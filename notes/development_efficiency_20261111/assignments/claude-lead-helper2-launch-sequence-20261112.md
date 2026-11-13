# Assignment to Codex helper 2: finish the launch sequence script and give its hash a place in the review bundle

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your observer handoff is accepted. The lead reviewed the production change (`91fcdab33`): it uses the existing alias helper and nothing else. Helper 1 will cherry-pick your three commits and rerun the public completion test in its scratch composition, where the protected packets are applied. Your finding H2-F1 (a trailing blank line in the copied runner) stays as it is.

## Why this task

Amendment N1 requires that the capture, guard and launch commands of a native attempt run as one reviewed sequence, from one script whose bytes are pinned. An agy worker wrote a first draft before the amendment's last two revisions, and it has not been reviewed. You review it, bring it up to the amendment, and add the two keys the amendment needs in the review bundle.

Read these passages of amendment N1, draft v10 (`git -C P show 127cc0bd69d73fcd21d94978bf5e0ee60e0e950c:notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`): N1.3's D12 row; N1.4(B) row 4; N1.5's order of events and its paragraph "Steps 5 and 6 run as one reviewed sequence"; N1.9 items 4 and 10; N1.8 items (z), (aa) and (ad). One change is already agreed for the next draft and is binding for you: a delegated start is refused unless it is within 30 minutes after the direction's recorded time **and** within 30 minutes after the recorded time of the owner's confirmation of the host state.

The amendment is not ratified. The owner may still decline items (z), (aa) or (ad). Build what it describes, and keep each piece in its own commit so that one can be dropped.

## Where you work

Create a new worktree from the candidate's head, and bring the draft in:

```sh
git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema worktree add \
  -b codex/native-launch-sequence-20261112 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-launch-sequence-20261112 \
  5d63d0a77dc43c064cfc2b376355f98009dd5b6e
```

The draft's two files are uncommitted in `E/agy-native-launch-sequence-20261112`: `src/data_sheets_schema/native_launch_sequence.py` and `tests/test_native_launch_sequence.py`. Copy them into your worktree; leave the originals untouched. Its handoff is `R/notes/development_efficiency_20261111/handoffs/agy2-native-launch-sequence-20261112.md`. Scratch goes under `E/scratch-h2-launch-sequence-20261112/`.

## Part A: review the draft (commit 1: the draft as received, then your fixes)

1. Commit the two files as received, with a message saying who wrote them and that they are unreviewed.
2. Review them against the source they drive (`native_generation.py` on your branch: the three subcommands, their flags, and the JSON each prints) and against the amendment. Look for: any way a later command can start after an earlier one failed; any retry or loop; any place a path or value could come from the environment; any overwrite; whether the guard command is given the capture this run just made and nothing else; whether a refusal by the new latest-capture check (commit `5d63d0a77`) stops the sequence cleanly; and whether its tests would notice each of those faults.
3. Fix what you find, with tests. List what you found, including what you checked and found sound.

## Part B: what the amendment adds to the script (commit 2)

1. **The script's own bytes go into the launch packet** at the start of a run, before any command, so that a reviewer recomputes its sha256 from the saved bytes. The script does not report its own hash as evidence.
2. **A delegated start.** Two optional arguments carry the recorded time of the owner's direction and the recorded time of the owner's confirmation of the host state, as strict UTC timestamps. When they are given, the script refuses before the capture unless the current time is within 30 minutes after each, and not before either. Both, and the start time, are written to `sequence.json`. Giving one without the other is refused. When neither is given, the owner is starting it and no limit applies.
3. Tests for each: the saved bytes equal the running file; inside the limit; one second outside each limit separately; a time in the future; one argument without the other; and that a refusal starts no command.

## Part C: the review bundle's two new keys (commit 3; production code)

Amendment N1.9 item 4: the review bundle carries the sequence script's sha256 in a closed key that the reader checks, and the owner's statement carries the owner's confirmation that the account is quiet, in a closed key. Today the bundle's and the statement's keys are closed without them (`native_launch_review.py`).

1. Read how the bundle and the statement are built, validated and read back, and every place their key sets are pinned (tests, fixtures, source manifests, the scanner).
2. Propose the smallest additive change: the two keys, their exact value forms, where each is checked, and how a bundle or statement written before the change is read (the existing ones must stay readable as historical evidence and must not be accepted as current). **Write this proposal into your handoff and stop before implementing it** if it changes the meaning of an existing version number, moves a pin in one of the four protected files, or needs a choice you cannot settle from the source. Otherwise implement it with tests as commit 3.
3. List every pin and derived identity that moves, as you did for the observer. Update none.

## Bounds

As in the context file. Never run the real `native_generation` subcommands. The script takes nothing from the environment and prints no secret.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h2-launch-sequence-20261112.md`: answer first (what the draft got wrong, what the script now does and refuses, the test counts from saved output, the state of Part C), then the details. Print its path and SHA-256 and stop.
