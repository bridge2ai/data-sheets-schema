#!/bin/bash
# run_agentic_fanout_20261122.sh
# Purpose: run the final agentic D4D generations (generic_v9, d4d-full-core playbook) for one
#   replicate, one project after another, each in a fresh headless Claude Code session on
#   one Claude subscription account, then run the completion gates and record what was observed.
#   Owner's word, 2026-11-22: advisor off; three replicates of all five projects; rerun the
#   AI-READI canary with the advisor off. Model claude-opus-5-5, effort high.
# Inputs:  <worktree> <replicate number> <project> [<project> ...]
#   The worktree must be a checkout of this repository with its own .venv (poetry install). Environment (read since 2026-11-27; one of the three is required): D4D_SERIES_CONFIG_DIR and D4D_SERIES_OAUTH_TOKEN, the Claude Code configuration directory and the login token of the account to run on, or D4D_SERIES_DEFAULT_LOGIN=1 for the login the default configuration directory holds.
# Outputs (all under <worktree>):
#   data/d4d_concatenated/claudecode_agent{,_core}/<label>/<PROJECT>_*   the records
#   .temp/launch/<PROJECT>_<label>.md            the rendered launch instruction
#   .temp/launch/<PROJECT>_<label>.launch.txt    what was launched, with hashes
#   .temp/launch/transcripts/<label>/<PROJECT>.stream.jsonl   the session's stream-json
#   .temp/launch/gates/<PROJECT>_<label>.txt     gate results, ending "GATES: PASS" or FAIL
#   stdout: one line per event, "<UTC> <rep> <project> <event>"
# Stops the replicate (exit 3) when a session fails outright, so a credential or rate-limit
#   failure is not repeated on every remaining project.
# Serves: the final-D4D fast route decided by the owner on 2026-11-21/22. Date: 2026-11-22.
set -u
W=${1:?worktree}; REP=${2:?replicate number}; shift 2
[ $# -ge 1 ] || { echo "no projects given" >&2; exit 2; }; [ -n "${D4D_SERIES_CONFIG_DIR:-}${D4D_SERIES_OAUTH_TOKEN:-}" ] || [ "${D4D_SERIES_DEFAULT_LOGIN:-}" = 1 ] || { echo "STOP: no account chosen: set D4D_SERIES_CONFIG_DIR, D4D_SERIES_OAUTH_TOKEN or both, or D4D_SERIES_DEFAULT_LOGIN=1 for the login of the default configuration directory" >&2; exit 2; }; case "${D4D_SERIES_CONFIG_DIR:-}" in ""|/*) ;; *) echo "STOP: D4D_SERIES_CONFIG_DIR must be an absolute path" >&2; exit 2 ;; esac; [ -z "${D4D_SERIES_CONFIG_DIR:-}" ] || [ -d "$D4D_SERIES_CONFIG_DIR" ] || { echo "STOP: D4D_SERIES_CONFIG_DIR is not a directory" >&2; exit 2; }
SERIES=2026-11-22b
MODEL=claude-opus-5-5
EFFORT=high
CONDITION=generic_v9
METHOD=claudecode_agent
LABEL="${SERIES}_claude-opus-5-5-claudecode-generic-v9_rep${REP}"
cd "$W" || exit 2
PY="$W/.venv/bin/python"
D4D=("$PY" -m data_sheets_schema.cli)
[ -x "$PY" ] || { echo "no .venv in $W" >&2; exit 2; }
"$PY" -c "import data_sheets_schema.api_runner as m,sys; sys.exit(0 if m.__file__.startswith('$W/') else 1)" \
  || { echo "the .venv does not import this worktree's source" >&2; exit 2; }
mkdir -p .temp/launch/gates ".temp/launch/transcripts/$LABEL"
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) rep$REP $*"; }

for P in "$@"; do
  FULL="data/d4d_concatenated/$METHOD/$LABEL/${P}_d4d.yaml"
  CORE="data/d4d_concatenated/${METHOD}_core/$LABEL/${P}_d4d_core.yaml"
  INSTR=".temp/launch/${P}_${LABEL}.md"
  STREAM=".temp/launch/transcripts/$LABEL/${P}.stream.jsonl"
  GATE=".temp/launch/gates/${P}_${LABEL}.txt"
  if [ -e "$FULL" ] || [ -e "$CORE" ] || [ -e "$STREAM" ]; then
    say "$P SKIPPED: outputs or a transcript already exist for this label (never rerun into a populated label)"
    continue
  fi
  BUNDLE="data/preprocessed/concatenated/${P}_preprocessed.txt"
  CHUNKS="data/preprocessed/chunks/${P}_chunks.yaml"
  [ -s "$BUNDLE" ] && [ -s "$CHUNKS" ] || { say "$P STOP: bundle or chunk manifest missing"; exit 3; }
  "${D4D[@]}" prompt render --project "$P" --label "$LABEL" --condition "$CONDITION" --method "$METHOD" \
      --runtime 'Claude Code' --out "$INSTR" >/dev/null 2>".temp/launch/${P}_${LABEL}.render.err" \
    || { say "$P STOP: instruction did not render (see .temp/launch/${P}_${LABEL}.render.err)"; exit 3; }
  SHA=$(shasum -a 256 "$INSTR" | cut -d' ' -f1)
  START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  {
    echo "Launch record: final agentic D4D, series $SERIES (headless, advisor off, no MCP servers)"
    echo "launched_at_utc: $START  (date -u)"
    echo "project: $P   replicate: $REP   label: $LABEL"
    echo "condition: $CONDITION   method: $METHOD   arm: baseline"
    echo "instruction: $INSTR"
    echo "instruction_sha256: $SHA ($(wc -c < "$INSTR" | tr -d ' ') bytes)"
    echo "worktree: $W   commit: $(git rev-parse HEAD)   tree dirty paths: $(git status --short | wc -l | tr -d ' ')"
    echo "schema: $(grep -m1 '^version:' src/data_sheets_schema/schema/data_sheets_schema.yaml)"
    echo "bundle: $BUNDLE sha256 $(shasum -a 256 "$BUNDLE" | cut -d' ' -f1)"
    echo "model: $MODEL   effort: $EFFORT (CLI flag; asserted by the launcher)"
    echo "claude code: $(command claude --version 2>/dev/null)"
    echo "account: a Claude subscription account (not named in the launch record)"
    echo "advisor tool: disabled with CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1"
    echo "MCP servers: none (--strict-mcp-config with no config)"
    echo "delivery: the instruction file's text is the single prompt of a headless session (claude -p)"
    echo "owner's word (nonhelper session, 2026-11-22): advisor off: \"yes\"; \"three replicates of all five\"; \"rerun it with the advisor off\""
  } > ".temp/launch/${P}_${LABEL}.launch.txt"
  say "$P LAUNCHED instruction $SHA"
  (
    unset CLAUDE_CONFIG_DIR CLAUDE_CODE_OAUTH_TOKEN CLAUDE_ACCOUNT_LABEL
    [ -n "${D4D_SERIES_CONFIG_DIR:-}" ] && export CLAUDE_CONFIG_DIR="$D4D_SERIES_CONFIG_DIR"; [ -n "${D4D_SERIES_OAUTH_TOKEN:-}" ] && export CLAUDE_CODE_OAUTH_TOKEN="$D4D_SERIES_OAUTH_TOKEN"; unset D4D_SERIES_CONFIG_DIR D4D_SERIES_OAUTH_TOKEN D4D_SERIES_DEFAULT_LOGIN
    export CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1
    command claude -p --model "$MODEL" --effort "$EFFORT" --strict-mcp-config \
      --output-format stream-json --verbose "$(cat "$INSTR")" \
      > "$STREAM" 2> ".temp/launch/transcripts/$LABEL/${P}.stderr" < /dev/null
  )
  RC=$?
  END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # ---- gates -------------------------------------------------------------------------
  {
    echo "Gates for $P $LABEL   session exit $RC   $START -> $END"
    "$PY" - "$STREAM" <<'PYEOF'
import json, sys, collections
models = collections.Counter(); tools = collections.Counter(); advisor = 0; result = None
reads = collections.Counter()
for line in open(sys.argv[1], errors="replace"):
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get("type") == "assistant":
        m = e.get("message") or {}
        models[m.get("model")] += 1
        for b in m.get("content") or []:
            if b.get("type") in ("tool_use", "server_tool_use"):
                name = b.get("name") or ""
                tools[name] += 1
                if "advisor" in name.lower():
                    advisor += 1
                if name == "Read":
                    reads[(b.get("input") or {}).get("file_path", "")] += 1
    if e.get("type") == "result":
        result = e
print("transcript models:", dict(models))
print("transcript tools:", dict(tools))
print("transcript advisor calls:", advisor)
prior = [p for p in reads if "/data/d4d_concatenated/" in p and "2026-11-22b_" not in p]
print("transcript Read of other d4d_concatenated paths:", prior[:5])
if result is None:
    print("transcript result: MISSING")
else:
    print("transcript result:", result.get("subtype"), "| is_error", result.get("is_error"),
          "| turns", result.get("num_turns"), "| minutes", round((result.get("duration_ms") or 0) / 60000, 1),
          "| models used", list((result.get("modelUsage") or {}).keys()))
ok = (result is not None and result.get("subtype") == "success" and not result.get("is_error")
      and advisor == 0 and set(models) <= {"claude-opus-5-5", "<synthetic>"} and not prior)
print("TRANSCRIPT:", "ok" if ok else "NOT OK")
PYEOF
    for f in "$FULL" "$CORE" "data/d4d_concatenated/${METHOD}_core/$LABEL/${P}_coverage_receipt.yaml" \
             "data/d4d_concatenated/${METHOD}_core/$LABEL/${P}_reconciliation.md" \
             "data/d4d_concatenated/${METHOD}_core/$LABEL/${P}_provenance.yaml"; do
      if [ -s "$f" ]; then echo "file ok: $f ($(wc -c < "$f" | tr -d ' ') bytes)"; else echo "FILE MISSING: $f"; fi
    done
    echo "--- validate full"
    "$PY" -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset "$FULL" 2>&1 | tail -3
    echo "validate_full_exit ${PIPESTATUS[0]}"
    echo "--- validate core"
    "$PY" -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset "$CORE" 2>&1 | tail -3
    echo "validate_core_exit ${PIPESTATUS[0]}"
    echo "--- receipts check --strict"
    "${D4D[@]}" --manifest data/preprocessed/source_manifest.yaml receipts check --method "$METHOD" --label "$LABEL" \
      --project "$P" --bundle "$BUNDLE" --chunk-manifest "$CHUNKS" --strict 2>&1 | tail -4
    echo "receipts_exit ${PIPESTATUS[0]}"
    echo "--- scope check"
    "${D4D[@]}" download scope --manifest data/preprocessed/source_manifest.yaml --project "$P" --check \
      --record "$FULL" --record "$CORE" --strict 2>&1 | tail -3
    echo "scope_exit ${PIPESTATUS[0]}"
    echo "--- observed (transcript) annotation"
    OBS=".temp/launch/transcripts/$LABEL/${P}.observed.json"
    if "$PY" scripts/agentic_observed.py --bundle "$BUNDLE" \
         --receipt "data/d4d_concatenated/${METHOD}_core/$LABEL/${P}_coverage_receipt.yaml" \
         --manifest "$CHUNKS" "$STREAM" > "$OBS" 2> "${OBS%.json}.err"; then
      "${D4D[@]}" provenance annotate-observed --project "$P" --method "$METHOD" --label "$LABEL" \
        --run "$("$PY" -c "import json,sys;print(json.dumps(json.load(open(sys.argv[1]))))" "$OBS")" 2>&1 | tail -2
      echo "observed_exit ${PIPESTATUS[0]}"
      "$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));print('observed:',{k:d.get(k) for k in ('assistant_turns','output_tokens','thinking_tokens','receipt_chunks_unopened','receipt_chunks_total','bundle_lines_read','bundle_lines_total')})" "$OBS"
    else
      echo "observed_exit 1 (observer failed; see ${OBS%.json}.err)"
    fi
    echo "--- runs check --strict"
    "${D4D[@]}" runs check --method "$METHOD" --label "$LABEL" --project "$P" --strict 2>&1 | grep -E "failing|satisfy|unverifiable|FAIL|✗" | head -6
    echo "runs_check_exit ${PIPESTATUS[0]}"
  } > "$GATE" 2>&1
  if grep -q "TRANSCRIPT: ok" "$GATE" && ! grep -q "FILE MISSING" "$GATE" \
     && grep -q "^validate_full_exit 0" "$GATE" && grep -q "^validate_core_exit 0" "$GATE" \
     && grep -q "^receipts_exit 0" "$GATE" && grep -q "^scope_exit 0" "$GATE" \
     && grep -q "^observed_exit 0" "$GATE" && grep -q "^runs_check_exit 0" "$GATE"; then
    echo "GATES: PASS" >> "$GATE"; say "$P DONE gates PASS ($START -> $END)"
  else
    echo "GATES: FAIL" >> "$GATE"; say "$P DONE gates FAIL (see $GATE)"
  fi
  # A session that failed outright (no success result, or no full record) stops the
  # replicate: the cause is usually credentials or a usage limit and would repeat.
  if [ $RC -ne 0 ] || ! grep -q "transcript result: success" "$GATE" || [ ! -s "$FULL" ]; then
    say "$P STOP: the session did not complete (exit $RC); not starting the next project"
    exit 3
  fi
done
say "ALL REQUESTED PROJECTS FINISHED"
