# Score selection previews, 2026-11-26

Issue 6385. These commands implement the registered policy without changing it.
Run them after confirming the complete published scoring corpus and retained
receipt roots. The lead authorized these six read-only previews for the real-data
follow-up; their outputs and hashes belong in its evidence handoff.
There is no execution or canonical-mark command here.

Use the tool code from the selection branch while keeping the evaluations
worktree as the caller's corpus. Receipt roots supply accepted plans and export
manifests; a published filename alone is insufficient evidence. The score reader
does not open refused candidates or transcripts.

The operator must set all five local-path variables before running this block:
`TOOL_ROOT` is the selection-tool checkout, `SCORING_PY` its usable Python,
`BASELINE_RECEIPTS` and `REPEAT_RECEIPTS` the retained scorer run roots, and
`CORPUS_ROOT` the evaluations checkout containing the complete published corpus.
There are no machine-specific defaults.

```bash
: "${TOOL_ROOT:?Set TOOL_ROOT to the selection-tool checkout}"
: "${SCORING_PY:?Set SCORING_PY to the Python executable}"
: "${BASELINE_RECEIPTS:?Set BASELINE_RECEIPTS to the accepted first-scoring run root}"
: "${REPEAT_RECEIPTS:?Set REPEAT_RECEIPTS to the repeat run and export-manifest root}"
: "${CORPUS_ROOT:?Set CORPUS_ROOT to the complete evaluations checkout}"
CONFIG=2026-11-25c_claude-fable-5-2-claudecode-generic-v9
INSTRUMENT=2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6
export PYTHONPATH="$TOOL_ROOT/src"
export PYTHONDONTWRITEBYTECODE=1
cd "$CORPUS_ROOT" || exit 2
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
