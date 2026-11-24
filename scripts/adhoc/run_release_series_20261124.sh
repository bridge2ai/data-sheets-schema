#!/bin/bash
# run_release_series_20261124.sh
# Purpose: run one replicate of a release series of D4D generations (d4d-full-core playbook),
#   one project after another, each in a fresh headless Claude Code session on the
#   claude-personal account, then run the completion gates and record what was observed.
#   Successor of run_agentic_fanout_20261122.sh, which is kept unchanged as the record of
#   series 2026-11-22b. Differences, each for a defect that series had:
#     - the instruction is rendered with the complete recorder line, so the session's
#       record carries the launcher's specification, the instruction, the asserted effort,
#       the receipt expectation and the prompt files without the session adding them (#6320);
#     - the launcher exports D4D_RENDER_SPEC and D4D_LAUNCH_INSTRUCTION, which that line
#       reads, so the session never has to reproduce the specification;
#     - toolchain locations are rendered relative to the worktree, so neither the datasheet
#       header nor the commands carry the operator's path (#6314);
#     - the model is stated in the rendering specification, not by editing the shared
#       configuration on a branch (#6311, #6312);
#     - two more gates: the render gate must read "match", and no file the run wrote may
#       contain an absolute home-directory path, apart from repo.resource_root (#1550);
#     - the gate file reports how many times the session ran the recorder (the complete
#       line is refused once if the session appends no --phase).
#   Nothing here chooses the series, the model or the effort: all three are arguments.
# Inputs:  <worktree> <series> <model> <effort> <replicate number> <project> [<project> ...]
#   <series>  a label prefix not used before, e.g. 2026-11-25a
#   <model>   the model id passed to `claude --model` and stated in the instruction
#   <effort>  the level passed to `claude --effort` and asserted in the record
#   The worktree must be a checkout of this repository with its own .venv (poetry install),
#   and this script must be started with that worktree as the working directory's root.
#   Environment (optional): D4D_SERIES_CONDITION (default generic_v9), D4D_SERIES_METHOD
#   (default claudecode_release), D4D_SERIES_RUNTIME (default "Claude Code (release)"): a
#   release series is filed under its own method directory and runtime string, apart from
#   the agentic arm and the direct arm (#6324).
# Outputs (all under <worktree>):
#   data/d4d_concatenated/<method>{,_core}/<label>/<PROJECT>_*   the records
#   .temp/launch/<PROJECT>_<label>.md            the rendered launch instruction
#   .temp/launch/<PROJECT>_<label>.launch.txt    what was launched, with hashes
#   .temp/launch/transcripts/<label>/<PROJECT>.stream.jsonl   the session's stream-json
#   .temp/launch/gates/<PROJECT>_<label>.txt     gate results, ending "GATES: PASS" or FAIL
#   stdout: one line per event, "<UTC> <rep> <project> <event>"
# Stops the replicate (exit 3) when a session fails outright, so a credential or rate-limit
#   failure is not repeated on every remaining project.
# Canary first: run one project of one replicate through this script and require
#   "GATES: PASS" with no re-record before starting any other run.
# Serves: issues #6320, #6314, #6311, #6312, #6324. Date: 2026-11-24.
set -u
W=${1:?worktree}; SERIES=${2:?series}; MODEL=${3:?model}; EFFORT=${4:?effort}; REP=${5:?replicate number}; shift 5
[ $# -ge 1 ] || { echo "no projects given" >&2; exit 2; }
CONDITION=${D4D_SERIES_CONDITION:-generic_v9}
METHOD=${D4D_SERIES_METHOD:-claudecode_release}
RUNTIME=${D4D_SERIES_RUNTIME:-Claude Code (release)}
case "$SERIES$MODEL$EFFORT$REP$CONDITION$METHOD" in *[!A-Za-z0-9._-]*) echo "series, model, effort, replicate, condition and method take plain tokens" >&2; exit 2;; esac
case "$RUNTIME" in *[!A-Za-z0-9\ \(\)._-]*) echo "the runtime takes letters, digits, spaces and parentheses" >&2; exit 2;; esac
LABEL="${SERIES}_${MODEL}-claudecode-${CONDITION//_/-}_rep${REP}"
cd "$W" || exit 2
W=$(pwd -P)
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
  SPEC=".temp/launch/${P}_${LABEL}.render_spec.json"
  STREAM=".temp/launch/transcripts/$LABEL/${P}.stream.jsonl"
  GATE=".temp/launch/gates/${P}_${LABEL}.txt"
  if [ -e "$FULL" ] || [ -e "$CORE" ] || [ -e "$STREAM" ]; then
    say "$P SKIPPED: outputs or a transcript already exist for this label (never rerun into a populated label)"
    continue
  fi
  BUNDLE="data/preprocessed/concatenated/${P}_preprocessed.txt"
  CHUNKS="data/preprocessed/chunks/${P}_chunks.yaml"
  [ -s "$BUNDLE" ] && [ -s "$CHUNKS" ] || { say "$P STOP: bundle or chunk manifest missing"; exit 3; }
  # Rendered from the worktree root with the worktree's own interpreter: the renderer spells
  # a toolchain location relative only when it lies under the launch directory (#6314).
  "${D4D[@]}" prompt render --project "$P" --label "$LABEL" \
      --condition "$CONDITION" --method "$METHOD" --runtime "$RUNTIME" \
      --reasoning-effort "$EFFORT" --launcher-model "$MODEL" --complete-recorder-line --relative-toolchain \
      --out "$INSTR" --render-spec-out "$SPEC" >/dev/null 2>".temp/launch/${P}_${LABEL}.render.err" \
    || { say "$P STOP: instruction did not render (see .temp/launch/${P}_${LABEL}.render.err)"; exit 3; }
  if grep -q "keeps its absolute path" ".temp/launch/${P}_${LABEL}.render.err"; then
    say "$P STOP: the instruction still carries an absolute toolchain path (see .temp/launch/${P}_${LABEL}.render.err)"; exit 3
  fi
  [ -s "$SPEC" ] || { say "$P STOP: no rendering specification was written"; exit 3; }
  SHA=$(shasum -a 256 "$INSTR" | cut -d' ' -f1)
  START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  {
    echo "Launch record: release series $SERIES (headless, advisor off, no MCP servers)"
    echo "launched_at_utc: $START  (date -u)"
    echo "project: $P   replicate: $REP   label: $LABEL"
    echo "condition: $CONDITION   method: $METHOD   runtime: $RUNTIME   arm: baseline"
    echo "instruction: $INSTR"
    echo "instruction_sha256: $SHA ($(wc -c < "$INSTR" | tr -d ' ') bytes)"
    echo "worktree: (the launch directory)   commit: $(git rev-parse HEAD)   tree dirty paths: $(git status --short | wc -l | tr -d ' ')"
    echo "schema: $(grep -m1 '^version:' src/data_sheets_schema/schema/data_sheets_schema.yaml)"
    echo "bundle: $BUNDLE sha256 $(shasum -a 256 "$BUNDLE" | cut -d' ' -f1)"
    echo "model: $MODEL   effort: $EFFORT (CLI flags; both stated in the rendering specification, the effort asserted by the launcher)"
    echo "recorder line: complete (D4D_RENDER_SPEC and D4D_LAUNCH_INSTRUCTION); toolchain: checkout-relative"
    echo "render specification: $SPEC sha256 $(shasum -a 256 "$SPEC" | cut -d' ' -f1)"
    echo "claude code: $(command claude --version 2>/dev/null)"
    echo "account: claude-personal (CLAUDE_CONFIG_DIR unset, as the owner's claude-personal function does)"
    echo "advisor tool: disabled with CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1"
    echo "MCP servers: none (--strict-mcp-config with no config)"
    echo "delivery: the instruction file's text is the single prompt of a headless session (claude -p)"
    echo "launched by: scripts/adhoc/run_release_series_20261124.sh $SERIES $MODEL $EFFORT $REP"
  } > ".temp/launch/${P}_${LABEL}.launch.txt"
  say "$P LAUNCHED instruction $SHA"
  (
    unset CLAUDE_CONFIG_DIR CLAUDE_CODE_OAUTH_TOKEN CLAUDE_ACCOUNT_LABEL
    [ -n "${CLAUDE_OAUTH_PERSONAL:-}" ] && export CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_OAUTH_PERSONAL"
    export CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1
    # The recorder line reads the specification and the instruction from these (#6320).
    export D4D_LAUNCH_INSTRUCTION="$W/$INSTR"
    D4D_RENDER_SPEC=$(cat "$SPEC"); export D4D_RENDER_SPEC
    command claude -p --model "$MODEL" --effort "$EFFORT" --strict-mcp-config \
      --output-format stream-json --verbose "$(cat "$INSTR")" \
      > "$STREAM" 2> ".temp/launch/transcripts/$LABEL/${P}.stderr" < /dev/null
  )
  RC=$?
  END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # ---- gates -------------------------------------------------------------------------
  {
    echo "Gates for $P $LABEL   session exit $RC   $START -> $END"
    "$PY" - "$STREAM" "$MODEL" "$SERIES" <<'PYEOF'
import json, sys, collections
models = collections.Counter(); tools = collections.Counter(); advisor = 0; result = None; recorder = 0
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
                if name == "Bash" and " provenance record " in str((b.get("input") or {}).get("command", "")):
                    recorder += 1
    if e.get("type") == "result":
        result = e
print("transcript models:", dict(models))
print("transcript tools:", dict(tools))
print("transcript advisor calls:", advisor)
print("transcript recorder attempts:", recorder)
prior = [p for p in reads if "data/d4d_concatenated/" in p and (sys.argv[3] + "_") not in p]
print("transcript Read of other d4d_concatenated paths:", prior[:5])
if result is None:
    print("transcript result: MISSING")
else:
    print("transcript result:", result.get("subtype"), "| is_error", result.get("is_error"),
          "| turns", result.get("num_turns"), "| minutes", round((result.get("duration_ms") or 0) / 60000, 1),
          "| models used", list((result.get("modelUsage") or {}).keys()))
ok = (result is not None and result.get("subtype") == "success" and not result.get("is_error")
      and advisor == 0 and set(models) <= {sys.argv[2], "<synthetic>"} and not prior)
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
    echo "--- render gate (the record's specification must re-render to the instruction sent)"
    "$PY" -c "import sys; from data_sheets_schema import runs; s = runs.verify_request(sys.argv[1], sys.argv[2], sys.argv[3]); print('render gate:', s[0]); sys.exit(0 if s[0] == 'match' else 1)" "$METHOD" "$LABEL" "$P" 2>&1 | tail -2
    echo "render_gate_exit ${PIPESTATUS[0]}"
    echo "--- no absolute home-directory path in what the run wrote"
    # repo.resource_root names the checkout git facts were read from and is absolute by
    # design (#1550); every other occurrence is a defect. The series of 2026-11-22 carried
    # three different roots, so the search is for any path under a home directory, not
    # only this worktree's.
    # A path, not a URL: "/Users/" or "/home/" not preceded by a URL character.
    HITS=$(grep -nE "((^|[^A-Za-z0-9:/._-])/(Users|home)/|$W)" "$FULL" "$CORE" "data/d4d_concatenated/${METHOD}_core/$LABEL/${P}_"* "$INSTR" "$SPEC" 2>/dev/null \
             | grep -v "_provenance.yaml:[0-9]*:  resource_root: " | cut -c1-200 | head -5)
    if [ -z "$HITS" ]; then echo "absolute_path_exit 0"; else echo "$HITS"; echo "absolute_path_exit 1"; fi
  } > "$GATE" 2>&1
  if grep -q "TRANSCRIPT: ok" "$GATE" && ! grep -q "FILE MISSING" "$GATE" \
     && grep -q "^validate_full_exit 0" "$GATE" && grep -q "^validate_core_exit 0" "$GATE" \
     && grep -q "^receipts_exit 0" "$GATE" && grep -q "^scope_exit 0" "$GATE" \
     && grep -q "^observed_exit 0" "$GATE" && grep -q "^runs_check_exit 0" "$GATE" \
     && grep -q "^render_gate_exit 0" "$GATE" && grep -q "^absolute_path_exit 0" "$GATE"; then
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
