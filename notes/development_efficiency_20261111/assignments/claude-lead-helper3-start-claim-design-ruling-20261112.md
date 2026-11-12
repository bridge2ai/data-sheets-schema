# Ruling and assignment to Codex helper 3: where the delegated-start claim lives (issues #5992 and #5993)

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This comes after `claude-lead-helper3-failure-record-review-followup-20261112.md` (issues #6015 and #6016).

## Standing

Your stop was right, and the analysis in `handoffs/codex-h3-launch-sequence-hardening-20261112.md` (SHA-256 `92d3a0cb6331b88c8539b620718da40e5b8a3431de973a88ea633ec679dcb7f4`) is accepted: a child directory with no retained identity repeats the missing-versus-empty ambiguity, and held descriptors cannot remember an identity across invocations.

## The ruling on #5992

**The claim becomes an event of the capture-word journal. No separate directory, and no filesystem identity recorded anywhere.**

- Add one closed event kind to the journal in `native_capture_words.py`, for a delegated sequence start. It carries the direction's normalized UTC instant, the registration digest, and whatever the existing events carry to bind them to the journal's authority. It is written by the sequence, under the journal's existing authority lock, before the capture command, with the same durability the word events have.
- A second delegated start that presents a direction already in the journal refuses. An owner start records its own event and stays repeatable. A delegated start under a newly recorded direction is admitted.
- **Missing state refuses by construction.** The sequence never initialises the journal: only the owner's word-recording step does. If the journal, its authority or its word state is missing, replaced by an empty one or unreadable, there is no recorded word, and the start refuses for that reason, before any capture. Show this with tests instead of adding an identity check.
- **Why not your recommended design** (a mandatory start directory whose filesystem identity the authority records): an inode-level identity does not survive a legitimate restore or copy of the state, which this machine has needed after reboots, and it adds a second place whose integrity has to be argued. The journal already carries this run's one-use rules. The claim should be exactly as strong as those: the word bound, the three captures per word, and the permanent limits-mismatch latch.
- **State the strength honestly.** In the handoff, say what protects an existing event of the journal from being removed on its own (for the limits-mismatch latch today, and so for the new event): a chain, a count in the authority, a roster, or nothing. If it is nothing, say so plainly as a known limit shared with the latch, and propose the smallest strengthening as a separate, optional commit. Do not claim rollback resistance against a complete consistent older copy of the state.
- **The format change is approved by the lead.** The journal is local evidence, not a registered document, and no native journal has ever been written in production, so there is nothing to migrate. If the journal carries a version or kind marker, move it; keep the reader of the previous form for historical evidence only, and make it impossible for a current start to run against the previous form. No registered document's kind or version changes: if you find one must, stop again.
- Remove the `.native-sequence-starts` directory mechanism of `b832233b7` in the same commit, so that there is one mechanism.

Tests: the replaced-directory case of the review, now against the journal (a replaced or emptied journal refuses for lack of a recorded word); the missing-state refusal; a repeated delegated direction through a different packet; a newly recorded direction admitted; an owner start repeated; and the event's durability before the first child command.

## #5993

As you described it, no further ruling needed: the verified entry establishes a per-invocation execution namespace; the body checks that entry-established identity before any packet effect; an ordinary imported call refuses; body fixtures go through the real entry with fixture source bytes pinned by fixture registration and review. Tests: the direct-import refusal and the loaded-A, retained-B refusal.

## Order and carrying

One commit per issue on `codex/native-launch-sequence-hardening-20261112`, #5992 first. Then carry both commits onto the failure-record branch and the retention branch by cherry-pick, record the resulting hashes, and rerun the affected whole test files on each. Give the lead the final head of each of the three branches.

## Bounds

As before. Offline; no real-binary execution, no probe, no capture, no reservation, no word state outside your scratch; no provider or model call; nothing pushed; no GitHub write; protected files equal to main; guard v1 byte-identical.

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h3-launch-sequence-hardening-20261112.md` and its JSON. Answer first: the two commits; what protects a journal event from removal; the three branch heads after carrying; the test counts from saved output.
