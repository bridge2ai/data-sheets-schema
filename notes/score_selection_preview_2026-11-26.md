# Score selection previews, 2026-11-26

Issue 6385. These commands implement the registered policy without changing it.
They are for the lead to run after confirming the complete published scoring
corpus and retained receipt roots. They were not run during implementation.
There is no execution or canonical-mark command here.

Use the tool code from the selection branch while keeping the evaluations
worktree as the caller's corpus. Receipt roots supply accepted plans and export
manifests; a published filename alone is insufficient evidence. The score reader
does not open refused candidates or transcripts.

```bash
TOOL_ROOT=/Users/marcin/agent-work/data-sheets-schema/score-gap-selection-20261126
SCORING_PY=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
BASELINE_RECEIPTS=/Users/marcin/agent-work/data-sheets-schema/codex196-pr6366-fix6370-evidence-20261125/live-runs
REPEAT_RECEIPTS=/Users/marcin/agent-work/data-sheets-schema/codex196-repeat-scoring-evidence-20261126/live-runs
CONFIG=2026-11-25c_claude-fable-5-2-claudecode-generic-v9
INSTRUMENT=2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6
export PYTHONPATH="$TOOL_ROOT/src"
export PYTHONDONTWRITEBYTECODE=1
cd /Users/marcin/agent-work/data-sheets-schema/root-scope-v6-evals-20261126 || exit 2
git -C "$TOOL_ROOT" merge-base --is-ancestor a920186203d16a5fe501d4bd86c5b336162314bb HEAD || exit 2
```

First review the completeness and pooled variation report. A refused or missing
cell is not measured, never zero. Strong differences in per-project spread need
the owner's review before the rule is used; no numeric cutoff is invented here.

```bash
nice -n 10 "$SCORING_PY" -B -m data_sheets_schema.cli runs score-variation \
  --method claudecode_release --config "$CONFIG" --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"
```

Preview each project's evidence, current policy pick, score-policy pick and
deciding rule. Each invocation pools the entire series, not just that project.

```bash
nice -n 10 "$SCORING_PY" -B -m data_sheets_schema.cli runs select \
  --method claudecode_release --project AI_READI --config "$CONFIG" \
  --score-policy score_gap_v1 --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"

nice -n 10 "$SCORING_PY" -B -m data_sheets_schema.cli runs select \
  --method claudecode_release --project CHORUS --config "$CONFIG" \
  --score-policy score_gap_v1 --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"

nice -n 10 "$SCORING_PY" -B -m data_sheets_schema.cli runs select \
  --method claudecode_release --project CM4AI --config "$CONFIG" \
  --score-policy score_gap_v1 --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"

nice -n 10 "$SCORING_PY" -B -m data_sheets_schema.cli runs select \
  --method claudecode_release --project VOICE --config "$CONFIG" \
  --score-policy score_gap_v1 --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"

nice -n 10 "$SCORING_PY" -B -m data_sheets_schema.cli runs select \
  --method claudecode_release --project VOICE_PEDIATRIC --config "$CONFIG" \
  --score-policy score_gap_v1 --score-instrument "$INSTRUMENT" \
  --score-receipts "$BASELINE_RECEIPTS" --score-receipts "$REPEAT_RECEIPTS"
```

After the previews, follow the [operator skill](../.claude/skills/d4d-select-replicate/SKILL.md):
compare every charged content finding against the same slot in sibling records,
show identical values explicitly, and obtain the owner's ruling. Selection stays
a preview until the owner authorizes a mark. The `--score-owner-rulings` input can
retain those rulings in a later explicitly authorized selection block; it does
not introduce an automatic veto or modify the score-gap rule.
