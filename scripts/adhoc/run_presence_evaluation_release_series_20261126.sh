#!/usr/bin/env bash
# Purpose: presence-based evaluation (field existence, deterministic, no model call) of the
#   15 full and 15 core records of release series
#   2026-11-25c_claude-fable-5-2-claudecode-generic-v9, with the same settings as the
#   label-aware table of 2026-08-07 (data/evaluation/label_aware/: the full and the core
#   method directory, default rubric files, no applicability context, invalid records not
#   included).
# Inputs: data/d4d_concatenated/claudecode_release/ and claudecode_release_core/
#   (only this series lives there).
# Outputs: data/evaluation/label_aware_release_2026-11-25c/ (scores.csv, scores.json,
#   summary_report.md, detailed_analysis/). A new directory: the tracked tables under
#   data/evaluation/ are not touched.
# Usage (from the repository root): PYTHON=<interpreter> scripts/adhoc/run_presence_evaluation_release_series_20261126.sh
# Date: 2026-11-26. Serves the owner's request of 2026-11-26 for the release series.
set -euo pipefail

PYTHON=${PYTHON:-python}
OUT=data/evaluation/label_aware_release_2026-11-25c

PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -m data_sheets_schema.evaluation.evaluate_d4d \
  --methods claudecode_release claudecode_release_core \
  --output-dir "$OUT"
