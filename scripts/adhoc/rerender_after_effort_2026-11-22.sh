#!/usr/bin/env bash
# Purpose: re-render the HTML pages that embed the provenance of the agentic
#   records of series 2026-11-22b, after commit ae63fe46f corrected the
#   reasoning effort in those records. The pages rendered before it repeat the
#   old statement ("the provider default applied. That is not a value this run
#   chose"). Review of PR #6309, finding F1.
# Inputs: the full records under
#   data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep{1,2,3}/
#   and their provenance records under claudecode_agent_core/.
# Outputs:
#   canonical: data/d4d_html/concatenated/claudecode_agent/<label>/<P>_d4d.html and the
#     flat data/d4d_html/concatenated/claudecode_agent/<P>_d4d.html, for the five
#     selected records (the commands of commit 32b1b8aec);
#   previews:  notes/final_agentic_2026-11-22/html/<P>_rep<N>.html for all 15 runs
#     (`d4d render html`; the three CM4AI previews with --skip-validation, as
#     notes/final_agentic_2026-11-22/html/README.md says they were made).
# Usage (from the repository root):
#   scripts/adhoc/rerender_after_effort_2026-11-22.sh one      # CHORUS rep2 only
#   scripts/adhoc/rerender_after_effort_2026-11-22.sh all
# Date: 2026-11-22. Serves PR #6309.
set -euo pipefail

D4D=${D4D:-./.venv/bin/d4d}
SERIES=2026-11-22b_claude-opus-5-5-claudecode-generic-v9
FULL=data/d4d_concatenated/claudecode_agent
PREVIEWS=notes/final_agentic_2026-11-22/html

canonical() {  # project rep
  "$D4D" render generate-all --method claudecode_agent --label "${SERIES}_rep$2" \
    --project "$1" --publish --execute
}

preview() {  # project rep
  local skip=()
  [ "$1" = CM4AI ] && skip=(--skip-validation)
  "$D4D" render html "$FULL/${SERIES}_rep$2/$1_d4d.yaml" -o "$PREVIEWS/$1_rep$2.html" "${skip[@]}"
}

case "${1:-}" in
  one)
    canonical CHORUS 2
    preview CHORUS 2
    ;;
  all)
    canonical AI_READI 2
    canonical CHORUS 2
    canonical CM4AI 1
    canonical VOICE 3
    canonical VOICE_PEDIATRIC 2
    for project in AI_READI CHORUS CM4AI VOICE VOICE_PEDIATRIC; do
      for rep in 1 2 3; do preview "$project" "$rep"; done
    done
    ;;
  *)
    echo "usage: $0 one|all" >&2
    exit 2
    ;;
esac
