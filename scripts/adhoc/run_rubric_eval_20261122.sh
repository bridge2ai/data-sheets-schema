#!/bin/bash
# run_rubric_eval_20261122.sh
# Purpose: score the final agentic datasheets (series 2026-11-22b) with the repository's
#   semantic rubric agents, to help the owner choose one replicate per project (owner,
#   2026-11-22: "run the rubric evaluation on all replicates to help select the best one").
#   Each evaluation is one fresh headless Claude Code session run AS the rubric agent
#   (claude --agent), on a Claude subscription account, with the model the agent definition
#   owner chose on 2026-11-22 ("use opus 5.5 high for scoring": claude-opus-5-5; the agent
#   definitions declare claude-opus-5), effort high, advisor tool off, no MCP servers.
# Inputs:  <replicate number> <rubric: 10|20|both> <project> [<project> ...]
#   Run from anywhere; works in the consolidated worktree below. Environment (read since 2026-11-27; one of the three is required): D4D_SERIES_CONFIG_DIR and D4D_SERIES_OAUTH_TOKEN, the Claude Code configuration directory and the login token of the account to run on, or D4D_SERIES_DEFAULT_LOGIN=1 for the login the default configuration directory holds (give it per invocation, not exported for good).
# Outputs (under the worktree):
#   data/evaluation_llm/rubric{10,20}_semantic/2026-11-22_general_context_v3/<P>_2026-11-22b_rep<N>_evaluation.json
#   .temp/eval/<P>_rep<N>_r<10|20>.stream.jsonl   the session's stream-json
#   .temp/eval/results.tsv                         one line per evaluation (appended)
#   stdout: one line per event
# The validator named in each agent definition is re-run here after the session; an
#   evaluation counts only when that exits 0.
# Serves: selection of the final D4Ds (owner decision 2026-11-22). Date: 2026-11-22.
set -u
W="$HOME/Documents/VIMSS/ontology/bridge2ai/d4d-executions/fast-d4d-20261121"
REP=${1:?replicate}; WHICH=${2:?10|20|both}; shift 2
[ $# -ge 1 ] || { echo "no projects" >&2; exit 2; }; [ -n "${D4D_SERIES_CONFIG_DIR:-}${D4D_SERIES_OAUTH_TOKEN:-}" ] || [ "${D4D_SERIES_DEFAULT_LOGIN:-}" = 1 ] || { echo "STOP: no account chosen: set D4D_SERIES_CONFIG_DIR, D4D_SERIES_OAUTH_TOKEN or both, or D4D_SERIES_DEFAULT_LOGIN=1 for the login of the default configuration directory" >&2; exit 2; }; case "${D4D_SERIES_CONFIG_DIR:-}" in ""|/*) ;; *) echo "STOP: D4D_SERIES_CONFIG_DIR must be an absolute path" >&2; exit 2 ;; esac; [ -z "${D4D_SERIES_CONFIG_DIR:-}" ] || [ -d "$D4D_SERIES_CONFIG_DIR" ] || { echo "STOP: D4D_SERIES_CONFIG_DIR is not a directory" >&2; exit 2; }; [ -z "${D4D_SERIES_ACCOUNT:-}" ] || { echo "STOP: D4D_SERIES_ACCOUNT is not read; set D4D_SERIES_CONFIG_DIR, D4D_SERIES_OAUTH_TOKEN or both, or D4D_SERIES_DEFAULT_LOGIN=1 for the login of the default configuration directory" >&2; exit 2; }; [ "${D4D_SERIES_DEFAULT_LOGIN:-}" != 1 ] || [ -z "${D4D_SERIES_CONFIG_DIR:-}${D4D_SERIES_OAUTH_TOKEN:-}" ] || { echo "STOP: D4D_SERIES_DEFAULT_LOGIN=1 contradicts a configuration directory or a token; give one or the other" >&2; exit 2; }
cd "$W" || exit 2
PY="$W/.venv/bin/python"
LABEL="2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep${REP}"
EVALMODEL=claude-opus-5-5
mkdir -p .temp/eval
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) eval rep$REP $*"; }
case "$WHICH" in both) RUBRICS="20 10";; 10|20) RUBRICS="$WHICH";; *) echo "bad rubric" >&2; exit 2;; esac

for P in "$@"; do
  IN="data/d4d_concatenated/claudecode_agent/$LABEL/${P}_d4d.yaml"
  [ -s "$IN" ] || { say "$P STOP: record missing: $IN"; exit 3; }
  for R in $RUBRICS; do
    AGENT="d4d-rubric${R}-semantic"
    DEF=".claude/agents/${AGENT}.md"
    OUTDIR="data/evaluation_llm/rubric${R}_semantic/2026-11-22_general_context_v3"
    OUT="$OUTDIR/${P}_2026-11-22b_rep${REP}_evaluation.json"
    STREAM=".temp/eval/${P}_rep${REP}_r${R}.stream.jsonl"
    mkdir -p "$OUTDIR"
    if [ -e "$OUT" ] || [ -e "$STREAM" ]; then say "$P r$R SKIPPED: an output or transcript exists"; continue; fi
    VALIDATE="$PY scripts/validate_evaluation_schema.py --file $OUT --input $IN --agent-definition $DEF --rubric rubric${R}-semantic"
    PROMPT="Evaluate one D4D record with your rubric, following your definition exactly.

Record to evaluate (the only D4D record you may read): $IN
Dataset identity as supplied by the caller: project $P. Authorship/method identity as supplied by the caller: method claudecode_agent, label $LABEL.
The caller supplies no applicability context file, so use an empty applicability_context as your definition says.

Write the evaluation JSON to exactly this path: $OUT

Then run this exact-file check from the repository root and correct your output until it exits 0 (use this interpreter, not poetry run):
$VALIDATE

Rules: do not read any other file under data/evaluation_llm/ and do not read any other D4D record or any provenance, gate or notes file. Do not edit the record you are evaluating. Finish with one line of the form: RESULT total=<total_points> max=<max_points> adjusted_max=<adjusted_max_points> file=$OUT"
    START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    say "$P r$R LAUNCHED"
    (
      unset CLAUDE_CONFIG_DIR CLAUDE_CODE_OAUTH_TOKEN CLAUDE_ACCOUNT_LABEL
      [ -n "${D4D_SERIES_CONFIG_DIR:-}" ] && export CLAUDE_CONFIG_DIR="$D4D_SERIES_CONFIG_DIR"; [ -n "${D4D_SERIES_OAUTH_TOKEN:-}" ] && export CLAUDE_CODE_OAUTH_TOKEN="$D4D_SERIES_OAUTH_TOKEN"; for v in ${!D4D_SERIES_@}; do unset "$v"; done
      export CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1
      command claude -p --agent "$AGENT" --model "$EVALMODEL" --effort high --strict-mcp-config \
        --output-format stream-json --verbose "$PROMPT" > "$STREAM" 2> "${STREAM%.jsonl}.stderr" < /dev/null
    )
    RC=$?
    END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    $VALIDATE > ".temp/eval/${P}_rep${REP}_r${R}.validate.txt" 2>&1
    VRC=$?
    SUMMARY=$("$PY" - "$OUT" "$STREAM" <<'PYEOF'
import json, sys, collections
out, stream = sys.argv[1], sys.argv[2]
total = mx = adj = "?"
try:
    d = json.load(open(out))
    def find(o, key):
        if isinstance(o, dict):
            if key in o and not isinstance(o[key], (dict, list)):
                return o[key]
            for v in o.values():
                r = find(v, key)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = find(v, key)
                if r is not None:
                    return r
        return None
    total, mx, adj = find(d, "total_points"), find(d, "max_points"), find(d, "adjusted_max_points")
except Exception as exc:
    total = f"unreadable ({type(exc).__name__})"
models = collections.Counter(); advisor = 0; other_reads = []
for line in open(stream, errors="replace"):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("type") == "assistant":
        m = e.get("message") or {}
        models[m.get("model")] += 1
        for b in m.get("content") or []:
            if b.get("type") in ("tool_use", "server_tool_use"):
                name = b.get("name") or ""
                if "advisor" in name.lower():
                    advisor += 1
                i = b.get("input") or {}
                text = " ".join(str(i.get(k, "")) for k in ("command", "file_path", "path", "pattern"))
                if "data/evaluation_llm/" in text and out not in text and "2026-11-22_general_context_v3" not in text:
                    other_reads.append(text[:80])
print(f"{total}\t{mx}\t{adj}\t{','.join(str(k) for k in models)}\t{advisor}\t{len(other_reads)}")
PYEOF
)
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$P" "rep$REP" "r$R" "$SUMMARY" "session_exit=$RC" "validator_exit=$VRC" "$START" "$END" >> .temp/eval/results.tsv
    if [ $VRC -eq 0 ] && [ $RC -eq 0 ]; then say "$P r$R DONE valid: $(echo "$SUMMARY" | cut -f1-3 | tr '\t' '/')"; else say "$P r$R DONE NOT VALID (session $RC, validator $VRC)"; fi
    if [ $RC -ne 0 ] && [ ! -s "$OUT" ]; then say "$P r$R STOP: the session failed outright; not continuing this lane"; exit 3; fi
  done
done
say "ALL REQUESTED EVALUATIONS FINISHED"
