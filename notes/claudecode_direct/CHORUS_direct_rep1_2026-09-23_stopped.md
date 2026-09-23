# CHORUS direct-arm canary, 2026-09-23: stopped and disqualified after a complete generation

The first run of the direct arm (#2202, PR #2203, merged as 2499b451f): Claude Code 2.1.272 on the maintainer's claude.ai subscription, `claude-opus-5` at effort `max`, one fresh CHORUS generation through all four phases, no proxy, no CBORG, no ledger.

## Identity

- Job `CHORUS_direct_rep1`, label `2026-09-23_claude-opus-5-direct-generalized-direct-v1-chorus_rep1`, method `claudecode_direct`, runtime `Claude Code (direct)`, provider `Anthropic (Claude subscription, direct)`, condition `generic_v9`, renderer 17, profile `bridge2ai`.
- Registration sha256 `627819891617ce2e31471cf61211f07967898b62103638d61c0ad5150d98d6d5` (234 pins), instruction sha256 `b528bff782fa0d44ec05621e6936140ec8043cd299f334f1b352acfe7df7ab92` (97,007 bytes), code commit `2499b451f816572a618d7af74be702345cfcf709`, executable sha256 `195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75`.
- Independent review of the registration: approve (a read-only reviewer subagent; its record's sha256 `556c89f665b01a9e00ff652819ca20abd47de092cc3d77efe16b6a199482c59d`), bound with CI run 35812436510 on the registered commit; the maintainer's launch word bound to the registration hash at 03:01Z.
- Started 2026-09-23T03:12:13.144869+00:00, finished 2026-09-23T05:47:21.376577+00:00. The registration, review, word, attempt directory and generated records stay untracked in the canary worktree; this note carries their hashes.

## What the child did

- Completed normally: result `success`, `end_turn`, `terminal_reason: completed`, 320 turns, 155 minutes. Init line: model `claude-opus-5`, `apiKeySource: none`, version 2.1.272, tools Bash/Read/Write.
- Accounting (the runtime's own): estimate $49.94 (guard $60); per-model `inputTokens` 94,411, `outputTokens` 859,206 (thinking 305,143), cache read 24,770,503, cache creation 1,576,053; `contextWindow` 200,000, `maxOutputTokens` 64,000 (the registered expectation, with `CLAUDE_CODE_DISABLE_1M_CONTEXT=1`); no auxiliary model in `modelUsage`; effort observed `max` on every callback; terminal `usage.output_tokens` 746,122.
- Wrote and self-validated: the full record (LinkML `Dataset` and term validation pass), the core record (`derive core --phase4-complete`, LinkML `CoreDataset` pass), the coverage receipt (8/8 chunks, 121/122 snippets verified, 99/115 slots with a receipt), the evidence audit (26 findings: 1 high, 5 medium, 20 low; 39 paths revised; one maintainers entry rejected), and the phase-4 reconciliation report; pair consistency 79 schema-identical slots; scope check clean.
- Artifact sha256 at the stop:
  - `CHORUS_coverage_receipt.yaml`: `82aaa0cd33d8092da0ca2892ad836c096d32bdf7705bd4e4cac175d75a2626e4`
  - `CHORUS_d4d.yaml`: `432ae9b2aa119071f5da5fd31e4672d45903f08527dedc2e22b685222cfaa146`
  - `CHORUS_d4d_core.yaml`: `c01c9d27a274f0334157873a7ec325c59025473d5475885cdebe5c805a3836c9`
  - `CHORUS_reconciliation.md`: `6ad387fb94bd4220c5bf79557e050ab19c511532308e7d2b6c24b0875824d943`
  - `audit.json`: `31eb21373d130e543593379efe835bc48fc096099eb0770ffb7c09ea88bc75ee`
  - `original_core.yaml`: `549ed8c57191b8239f71da4c7db857cb5a789685f6456f776975c23f7ebf8ca5`
  - `original_full.yaml`: `926ff5c8035c5c879d3b65a88e9e6441dc70b5d8648b9c31302f1cb57470a573`

## Why it is disqualified (#2282)

The prescribed provenance line, run verbatim from the instruction, was refused by the runtime although the controller had classified it `prescribed` and allowed it and the registered settings carry the allow rule that every other prescribed command matched. The line carries `--prompt-text "${D4D_LAUNCH_INSTRUCTION:?…}"`, a shell parameter expansion the runtime's Bash permission path does not auto-allow; under `--permission-mode dontAsk` that is *"Permission to use Bash has been denied because Claude Code is running in don't ask mode."* The model reported the denial, did not retry in a modified form, did not set the variable or substitute a path, and stopped. A denied prescribed command disqualifies the attempt under the maintainer's ruling; the launcher's receipt reads `status: stopped`, `disqualifying_denials: ["denied prescribed call (Bash): the roster command 'provenance record'"]`. No provenance record exists, so the records above are not a run of the study and are not entered in the corpus.

No earlier v10 native attempt reached this step (v10q stopped at its cap in phase 1, v10r at its deadline in phase 3, v10y before core derivation), so the line is un-runnable as rendered on both Claude Code arms, and the fix is a renderer change: a condition boundary.

## Other findings

- Six `not_prescribed` denials of ad-hoc lookups (schema line ranges, the runtime's own tool-result files, a `poetry run` spelling of the receipts check, a grep over the record), listed and not disqualifying (#2284).
- The runtime emitted 17 `rate_limit_event` lines; the last read seven-day utilization 0.94 (`allowed_warning`), resetting 2026-09-26T00:00Z. The receipt does not yet keep them (#2283).
- The receipt's stop reason names an evidence gap (one Write of the full record has no PreToolUse callback; 305 decisions for 306 calls) above the disqualifying denial, and does not say the child completed (#2285).
- The two figures a rerun must revisit: deadline 21,600 s (this run took 9,307 s) and the $60 runaway guard on the runtime's estimate (this run's estimate $49.94).

## Standing

Never resumed. A second attempt needs the recorder line fixed and re-registered, a fresh registration, review, CI binding and launch word, and weekly subscription headroom.
