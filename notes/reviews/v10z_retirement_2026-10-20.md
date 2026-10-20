# Retirement of the v10z lineage and audit28 (D10, D22), 2026-10-20

This note follows step Z1 of `notes/d4d_generation_plan_2026-10-09.md` ("#### Z1").
It contains no amounts: on 2026-10-09 the owner decided to keep the CBORG chain amounts
out of the plan, and Z1's note gives none either (G3). It edits no file under
`notes/matched_cborg_*`. It is written at main `0a1132ecf` on branch
`claude/track-p-analysis-plan`. No provider was called.

## The owner's decisions

On 2026-10-20 the owner answered two direct questions in the Claude worker session.
The questions and answers, verbatim:

1. **D10 (#4761).**
   - **Question:** "Track Z asks me to write a note recording the retirement of
     v10z/audit28. Plan step Z1 applies only if D10 is 'retire', and #4761 was reopened
     on 2026-10-13 because no owner decision had been made. Have you decided D10?"
   - **Answer:** "Yes, retire (decided now)".
2. **D22 (#1763).**
   - **Question:** "D22 (#1763): do the v10z standing authorizations carry over to
     generic_v10? These are "run CHORUS canaries until they succeed, then all
     evaluations of the CHORUS d4d" with "no further approval", plus the 2026-09-25
     standing authority to debit an unconfirmed charge at its full reservation."
   - **Answer:** "Withdraw them all (Recommended)".
   - **The option chosen read:** "They do not extend to generic_v10, and they are
     withdrawn now along with the retired lineage. Every generic_v10 generation and
     evaluation needs its own word."

**This note is the record of the decision; the earlier one was not.** #4761 was closed on
2026-10-11 with a comment that cited a "documented owner decision" in commit
`d9f7d9a72`. That commit is on no remote branch, and the comment did not reflect an
owner decision, so #4761 was reopened on 2026-10-13 and the audit28 hold stood.
Nothing in this note is taken from that commit.

**Posting the decisions.** The coordination rules for this session allow no GitHub
writes, so agy posts both decisions, quoting the owner, with no at-mentions:
- D10 on #4761;
- D22 on #1763 and #4761.

## What is retired

- **The v10z/audit_controls native lineage:**
  - the frozen v10z CBORG native controller;
  - CHORUS rep1 under `generic_v9` renderer 14, with audit protocol 7 and renderer 23.
- **audit28.** It was never registered. As the plan records, it could not launch as
  registered:
  - its pinned Claude Code 2.1.272 was pruned (#4759);
  - main's `schema_digest.py` differs from the pinned bytes (#4761).

  No further compute is spent on either.
- **Phase 4 (#2114) of this lineage.** It is not built. Whether #2114 is closed as
  superseded or kept for another lineage is the owner's call. This note does not
  close it.

The plan's own reasoning (D10) gave the recommendation the owner took:
- an accepted audit28 would yield one composite generic_v9 CHORUS record that still
  needs Phase 4 and cannot be compared with any generic_v10 cell;
- 0 of 26 billed audits were accepted.

## Lineage outcome, in three groups, with no amounts

The plan's grouping is dated 2026-10-09 and was made from the local ledger files. The
counts below are the plan's; this note does not recount them.

1. **The v10z lineage:** generation `d4810ca2` plus 26 billed audits (and the unbilled
   audit10).
2. **The matched native sequence:** 9 generations plus 26 audits.
3. **The shared ledger total.** This is a third group, not a sum of the first two. The
   same ledger also holds the 15 CHORUS API attempts and the transport probe.

No full/core pair from this lineage was accepted.

**Preservation.** The lineage's `/private/tmp` files have a durable copy at
`d4d-executions/lineage-durable` (#2497):
- `MANIFEST.json` was created at 2026-09-26T07:08:19Z, with 100,628 entries under 46
  roots;
- its README records a restore drill that reproduced every entry byte for byte.

This note did not re-verify the copy. That would hash 3.9 GB while CPU-timing work
runs. Before relying on it, run
`python3 d4d-executions/lineage-durable/lineage_durable.py verify --durable`. The
`git bundle` copies of the Codex session's unpublished branches (plan G1a, #4763) are
tracked on #4763, not here.

## Superseded by generic_v10

- **The v10z workload.** `notes/matched_cborg_2026-09-18_v10z/workload.public.json`
  (sha256 `d4a5ac9691454ce18871e1b2759d97e7a26385f6244481fb28042694853b0d91`) has
  `kind: proposed_workload_inventory_not_a_launch_registration`. It lists 32
  generic_v9 generation jobs:
  - 16 API and 16 agentic;
  - CHORUS, AI_READI, CM4AI, VOICE and VOICE_PEDIATRIC 6 each, and KIDS_FIRST 2.

  The plan records outputs for only one of them: the CHORUS agentic rep1 job, which
  is generation `d4810ca2`. The other 31 have none. All 32 are superseded by
  generic_v10, so no cell is filled under two conditions.
- **The direct-arm registrations under `generic_v9` renderer 17.** These are the
  three CHORUS canaries of 2026-09-23, 2026-09-24 (two attempts) and 2026-09-25. They
  too are superseded by generic_v10.

  The two earlier outcome notes stay as they are:
  - `notes/claudecode_direct/CHORUS_direct_rep1_2026-09-23_stopped.md`;
  - `notes/claudecode_direct/CHORUS_direct_v2_2026-09-24_stopped.md`.

  The third has no outcome note on main; it is recorded below.

## The third direct-arm canary (2026-09-25): outcome

The evidence is untracked in the canary worktree
`d4d-executions/direct-canary-3`, under
`notes/claudecode_direct/.local_drafts/2026-09-25_CHORUS_v3/`. It was read without
writing to that worktree. The values below are the attempt's own `result.json`.

**Identity**

| | |
|---|---|
| Job and label | `CHORUS_direct_rep1`; `2026-09-25_claude-opus-5-direct-generalized-direct-v3-chorus_rep1` |
| Arm | method `claudecode_direct`, runtime `Claude Code (direct)`, provider `Anthropic (Claude subscription, direct)`; no proxy, no CBORG and no ledger |
| Condition | `generic_v9`, renderer 17; `claude-opus-5` at effort `max`; Claude Code 2.1.272 |
| Code commit | `14dd8500efd426c95a993fc396fb1bc0ea32ca7b` |
| Executable sha256 | `195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75`, the same as the 2026-09-24 attempts |
| Registration sha256 | `4f094f60843b004eec3df81456f2b4a7cde53a347a6870bc8ea8a314962e780b` |
| Independent review | approved at 2026-09-25T03:17:52Z; `independent_review.json` sha256 `5e2d63b339ea9dd87b57b363e5efb576fc993c3a69fd1887c477520e6745568f`; bound with CI run 36086776318 on the registered commit (`review.json`) |
| Launch word | recorded at 2026-09-25T03:18:50Z (`word.json`); one launch, for exactly this registration |

**Outcome**

| | |
|---|---|
| Started and finished | 2026-09-25T03:19:01Z to 2026-09-25T06:40:05Z |
| Status | `stopped`. Error `BudgetStop`, reason "native attempt failed or stopped before completion", from the controller. `child_completed: false`; exit code 1 |
| Terminal reason | `blocking_limit` (`result_subtype: success`, `stop_reason: stop_sequence`) |
| Seven-day utilization | 0.96 at the first rate-limit event, 1.0 at the last (maximum 1.0), over 20 events. The five-hour window peaked at 0.2 |
| Overage | not used (`overage_used: false`) |
| Phases | phase 2 started and completed (`phase_history`); `receipt_gate_current: false`; no terminal failures, no problems in the command or phase history |
| Controls | 201 Bash and 79 file calls, 280 pretool decisions, no input rejections; 5 permission denials, none disqualifying |
| Outputs | Full, core, receipt, reconciliation and the evidence files were written (sha256s in `result.json`). No provenance record was written. The outputs are untracked and were never accepted |

`result.json` sha256 `2c8893049d2715011d831b87c20a8bc249362a40c043cd7b002749046b016d66`;
`started.json` sha256 `4199d2782b5521c28a65e311bf66faa29c2c55344f7e12cc82789e1efa233c32`.

The terminal reason is the subscription's seven-day limit (`blocking_limit`, at
utilization 1.0); the controller then recorded the attempt as stopped. The outputs
were never reviewed for acceptance, so this note says nothing about their quality.
Whether the direct-arm pause that followed covers the shared-protocol (#4354) runs is
D09 and #4758. Both are open, and this note does not decide them.

## Withdrawal of the v10z standing authorizations (D22)

Withdrawn on 2026-10-20 by the owner's answer quoted above:
- **The standing CHORUS authorization** in
  `notes/matched_cborg_2026-09-18_v10z/workload.public.json`
  (`standing_authorization.user_text`): "you are approved to run CHORUS canaries until
  they suceed. then you are approved to run all evaluations of the CHORUS d4d". It was
  funded with "No further approval is required within this scope and amended budget".
- **The 2026-09-25 standing authority** to debit an unconfirmed charge at its full
  reservation.

They do not extend to generic_v10. Every generic_v10 generation and evaluation needs
its own word, and that includes E5's joint re-rating.

The plan's D22 recommendation adds one step this note cannot take: the Codex operator
acknowledges the ruling and the withdrawal in writing before any generic_v10
registration, on either arm (G6).

## Held items, for agy to point at #4761

Their state was read from GitHub on 2026-10-20:

| item | state |
|---|---|
| PR #2910 (#2605) | merged 2026-10-17T06:16:19Z (`b250aa614`); #2605 closed |
| PR #4387 (#4009) | merged 2026-10-17T06:16:19Z (`436dd57da`); #4009 closed |
| PR #2922 (#2714) | merged 2026-10-17T06:16:19Z (`d8c088160`); #2714 closed. PR #5077 (merged `0fc7b1958`, 2026-10-19T06:11:02Z) rotated the frozen native controller pin to the #2714 series and the later #5078/#5079 cleanup fixes |
| #2909 | open |
| #3879 | open |
| #3785 | open |
| #3856 | open |

The three PRs merged before this decision, while #4761's hold was recorded as
standing. Those merges were not an owner decision on audit28, and this note does not
treat them as one.

## Z2: still the owner's

Plan step Z2 leaves each released item to the owner, separately:
- issues #2909, #3879, #3785 and #3856, each merged, implemented or closed with a
  reason;
- the three PRs, which are already merged.

PR #2922 was to be decided at N6b. It is merged, and its controller bytes were adopted
by the pin rotation in #5077.

Cost of this step: $0. No provider call was made.
