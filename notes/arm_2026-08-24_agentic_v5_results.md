# 2026-08-24 agentic v5 arm results

- **Arm:** `2026-08-24_claude-opus-5-claudecode-generic-v5` — 12 runs (4 projects
  × 3 replicates), condition `generic_v5`, **runtime Claude Code**, model
  `claude-opus-5` (subagent model override), reasoning effort `high` asserted
  by the launcher. **The first agentic arm under the v5 condition, and the
  first under the #681/#682 measurability alignment.** Same pinned condition
  text as the 2026-08-22c API arm: each run's instruction was rendered by
  `d4d prompt render --condition generic_v5 --runtime 'Claude Code'` and its
  sha256 is in the record's `prompts.request`.
- **Mode:** four-phase project-agent, as the pinned text mandates — one
  subagent per (project, replicate) running all phases in one context. The
  canary (CHORUS rep1, #683) and 11 fan-out runs took the same launch path;
  fan-out runs read their rendered instruction bytes from a file rather than
  inline, the one mechanical difference.
- **Outcome: 12 succeeded, 0 failed.** `d4d runs check --strict` exit 0 with
  zero warnings for the arm; every record `valid`; every scope check in scope.
- **Interruption and resume, first live use:** three runs (AI_READI, CM4AI,
  VOICE rep3) were killed by an account session limit and relaunched as fresh
  agents on a different account. The playbook's resume-by-validated-artifact
  rule did what it was written to do: AI_READI rep3 re-validated and skipped
  `generate_full`+`generate_core` (`phases_skipped` records it — the field
  #681's review found the recorder could not write), VOICE rep3 skipped
  `generate_full`, CM4AI rep3 had nothing on disk and ran in full. Their
  `run_observed` totals sum both invocations.
- **Spend (orchestrator-observed, cache-inclusive):** 326,590,625 total tokens
  across the 12 runs, 5.42 h of agent wall time (runs overlapped; ~2.5 h
  elapsed). **Not comparable to the API arm's 5.36M in / 2.26M out**: that
  figure is billed input/output from `api_usage`; this one sums every
  context re-read through the runner's cache, per the `run_observed_basis`
  each record carries. The two bases must never be averaged (#400).

## The table — three replicates per cell, 2026-08-22c API arm in parens

| metric | AI_READI | CHORUS | CM4AI | VOICE |
|---|---|---|---|---|
| ungrounded identifiers | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) |
| resolver URLs in identifier slots | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) |
| organisational fragments | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) |
| undeclared prefixes | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) |
| British spellings | 4,0,0 (20,37,0) | 0,0,0 (0,0,0) | 0,4,0 (0,0,0) | 3,4,0 (2,0,6) |
| **pair errors** | **0,0,0 (2,18,6)** | **0,0,0 (1,0,2)** | **0,0,0 (4,5,9)** | **0,0,0 (7,5,5)** |
| report findings † | 0,0,0 (0,1,0) | 0,0,0 (0,0,0) | 0,0,0 (2,0,0) | 0,0,0 (0,1,1) |
| minted fragments *(reported)* | 16,3,12 (0,13,14) | 0,0,0 (0,0,0) | **42,55,51** (15,10,16) | **3,14,130** (0,0,8) |
| GC label variants *(reported)* ‡ | 0,0,0 (1,0,0) | 0,0,0 (0,0,0) | 0,0,0 (0,0,0) | 40,40,30 (53,71,73) |
| repair loop ran | no,no,**yes** | no,no,no | no,no,no | no,no,no |

† `claims_checked` is 0 on 11 of 12 records — the report-claims checker
parses two claim forms and agentic reports use neither (#684), so "0" here is
**unmeasured** everywhere except CHORUS rep3 (`claims_checked: 2`, 0
findings), the one measured floor in the row. ‡ Entirely the dataset's own
PhysioNet title, per #674; lower than the API arm's, not zero.

## What the arm shows

**Every gated floor held on all 12 runs, and pair errors are 0 on all 12.**
The API arm's pair-error range across the same condition was 0–18 (11 of its
12 runs above 0). The two runtimes reconcile differently: the agentic Phase 4
runs the pair checker with `--sync-core` and then re-checks, so the core is
made a byte-exact projection of the audited full record before the report is
written; the API pipeline's separate `reconcile_full`/`reconcile_core` calls
leave residual precision and spelling divergence (#650, #675). This is a
procedure difference measured as a sum, not attributable to the runtime
alone — but it is the clearest cross-runtime result in the design so far.

**British spellings are lower and flatter** (arm total 15 vs 68), with no
run above 4 — and because the pair is synced, none of the spelling coupling
that inflated the API arm's AI_READI rep2 (#675).

**The repair loop exists now and fired once.** AI_READI rep3's Phase 4
findings required a change; the run recorded `repair` (1 pass) and
`report_after_repair`, the API pipeline's closing loop that this path
lacked until #681. Eleven runs needed none.

## The cell that needs explaining: minting appetite

Minted fragments are reported-only and every one hangs off an attested base
(`absent` is 0 arm-wide), so nothing here violates a rule. But the
**variance** is the finding: CM4AI mints 42/55/51 where the API arm minted
15/10/16, and VOICE mints 3/14/**130** — rep3 gave a `doi:…#slot-name`
identifier to essentially every nested object in the record (130 distinct:
`#version-access`, `#update-plan`, `#timeframe`, `#splits`, …), while rep1
labelled three things. Rule 3 says *when* minting is right and gives no
ceiling on *how much*; the schema declares optional `id` on most nested
classes; and the agentic runtime, reading the schema files directly, takes
the invitation more often than the API model reading a digest. Filed as
#685: whether the rule wants a density norm ("mint an identifier for a part
only where something will refer to it") is an instrument question for a
condition boundary, not a defect in these records.

## Canonical selection — dry run only, deliberately

`d4d runs select` (validity first, coverage second) would choose:

| project | would select | slots | margin |
|---|---|---|---|
| AI-READI | rep2 | 80 | +1 |
| CHoRUS | rep1 | 49 | +3 |
| CM4AI | rep2 | 56 | tie, broken by label (#660) |
| Voice | rep1 | 80 | +1 |

**Not executed.** Both arms live under the `claudecode_agent` method and the
tool keeps one canonical per project, so executing would supersede the
2026-08-22c API canonicals selected four days earlier (popping their blocks
per #677). Which arm's records are the project canonicals is a decision
about what the repository ships, not a selection criterion — it is left to
the maintainer, with the dry run recorded here so either choice is auditable.

## Instrument caveats carried forward

- Spend bases differ by construction (`api_usage` vs `run_observed`); no
  cross-arm cost or efficiency claim is available.
- Reasoning capture: `runtime_cannot_capture` on all 12 (#400); the API arm's
  estimates have no counterpart here.
- Report-claims: measured on 1 of 12 records (#684).
- GC label variants: title-collision inflated for VOICE (#674).
- Pair errors: comparable across arms as a deterministic artifact check, but
  the *procedures* that reduce them differ (see above).
- No rubric scores; `curated` is not a reference (#177).
