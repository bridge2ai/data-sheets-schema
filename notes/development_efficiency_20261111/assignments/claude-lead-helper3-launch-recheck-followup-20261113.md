# Assignment to Codex helper 3: the re-check's findings on issues 5992 and 5993

From the Claude lead, 2026-11-13. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This comes after `claude-lead-helper3-equivalence-comparison-20261112.md`.

## Standing

Your design-ruling handoff is accepted as work done (`handoffs/codex-h3-launch-sequence-hardening-20261112.md`, SHA-256 `4977253817928799bd3e6cf9c322fb6c64f763da732719a96980534078b25400`): `c9316e513414e811d52029806d22332d335ddc6a` (#5992), `c39526da9a01c41f4a168e58d45f2dea4ad10c00` (#5993), and the three carried heads. Your statement of the tail-deletion limit was accurate, and the re-check says so.

The lead has merged your stack into the published candidate so that CI runs on it: the retention head `4db154f88c78a28db2e6ed4e460debc3a96c9fa5` merged cleanly onto `6561dac3c`, followed by helper 2's cache repair; the published head is `8760de5efe88b5af62e9d77e6335fa7e248017b6` (draft PR #5968). The earlier re-check closed #6015 and #6016 with no new finding.

An independent read-only re-check of the two launch repairs (`E/plans/reviews/native_5992_5993_recheck_codex_2026-11-13.md`, SHA-256 `98edde0b8747ce5f319ae8c41ff430a26756b96246bd7a6acc1bb760741e2c6a`) says neither is closed. It confirms that the journal claim stops an ordinary replay and an emptied state before the sequence starts, and that an ordinary imported call refuses. Three findings, filed:

## Part 1: issue #6048 (P1), the capture child can recreate the journal after the start claim

`src/data_sheets_schema/native_subscription_capture.py`, about lines 423 to 424; `src/data_sheets_schema/native_generation.py`, about lines 239 to 241. The start claim releases the journal lock before the capture child runs, and the child opens the journal with `create=True` and activates the supplied word. If the state directory is moved aside or removed in between (this machine has cleanup jobs), the child builds a fresh journal with the same word and no start event, and after a capture refusal another packet can reuse the direction.

Repair: a capture dispatched by the sequence requires the existing current journal and its matching start event, under the capture lock; on that route it never initialises or activates missing state. The owner's word-recording step stays the only initialiser. A standalone capture outside the sequence keeps the behaviour the canary rules give it; say what that is and show it is unchanged. Test: state moved aside after the claim is durable and before the child acquires the journal, asserting refusal, no recreated state and no capture execution.

## Part 2: issue #6047 (P1), a caller-supplied callable bypasses the verified entry

`src/data_sheets_schema/native_launch_sequence.py`, about lines 135 to 139. The body takes `_entry_invocation` from its own globals and checks only that it is callable, so an importing caller can assign a no-op and then call `_run_verified` directly.

Repair: the body calls the trusted entry's validator directly; it accepts no validator through the sequence module's namespace. Keep the entry's module-execution route working. Test: an imported module with a no-op callback assigned, asserting zero packet and zero journal effects. A caller that rewrites the trusted entry itself, or the interpreter, stays out of scope; say so in one sentence in the module's documentation string.

## Part 3: issue #6049 (P2), the journal's tail is not anchored: the lead's decision

Not blocking for the canary. The limit is shared with the limits-refusal latch that the canary rules already rely on, and removing the last event takes deliberate deletion inside the registered state. It is recorded as a known limit. Do this part only after Parts 1 and 2, as its own optional commit on its own branch from the hardening head, so that it can be taken or dropped: the re-check's "smallest strengthening" (a committed count and tip, checked on every open, written crash-safely and fail-closed under the existing lock, with the immutable authority binding kept apart from the mutable tip). Say what a crash between appending an event and updating the tip leaves, and how the next open treats it.

## Carrying

Parts 1 and 2 are one commit each on `codex/native-launch-sequence-hardening-20261112`. Do not carry them onto your other two branches this time: those are merged. Give the lead the two commit hashes; the lead cherry-picks or merges them onto the published candidate.

## Bounds

As before. Offline; no real-binary execution, no probe, no capture, no reservation, no word state outside your scratch; no provider or model call; nothing pushed; no GitHub write; protected files unchanged; guard v1 byte-identical.

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h3-launch-sequence-hardening-20261112.md` and its JSON. Answer first: the two commits; what a sequence-dispatched capture now requires; what the body now calls; the test counts from saved output; and, if you did Part 3, its branch head and the crash behaviour.
