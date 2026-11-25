# Review helper (PR 6349 review, 2026-11-25): per-transcript facts from the 15 stream-json logs.
# Kept as review 1 of PR 6349 ran it (independent read-only review, 2026-11-25; report in
# notes/release_series_2026-11-25/review_1_pr6349.md); the only change is that ROOT comes from
# the environment (D4D_EXECUTIONS_ROOT) instead of an absolute path.
# Inputs: launch worktree root; Output: stdout summary. Read-only.
import json, sys, os, glob, collections
ROOT = os.environ["D4D_EXECUTIONS_ROOT"]  # the directory holding the launch worktrees
MAP = {"1": "release-series-20261125-rep2", "2": "release-series-20261125-rep1", "3": "release-series-20261125-rep3"}
mode = sys.argv[1] if len(sys.argv) > 1 else "summary"
for rep, wt in MAP.items():
    for path in sorted(glob.glob(f"{ROOT}/{wt}/.temp/launch/transcripts/*/*.stream.jsonl")):
        label = os.path.basename(os.path.dirname(path)); proj = os.path.basename(path)[:-13]
        models = collections.Counter(); tools = collections.Counter(); types = collections.Counter()
        retries = []; init = None; result = None; first_ts = last_ts = None; sub = 0; errors = []
        sids = set(); tool_inputs = []
        for line in open(path, encoding="utf-8"):
            try: e = json.loads(line)
            except ValueError: errors.append("badjson"); continue
            t = e.get("type"); types[(t, e.get("subtype"))] += 1
            if e.get("session_id"): sids.add(e["session_id"])
            ts = e.get("timestamp")
            if ts:
                first_ts = first_ts or ts; last_ts = ts
            if e.get("parent_tool_use_id"): sub += 1
            if t == "system" and e.get("subtype") == "init": init = e
            if t == "system" and e.get("subtype") == "api_retry": retries.append({k: e.get(k) for k in ("error_status", "attempt", "error")})
            if t == "result": result = e
            if t == "assistant":
                m = e.get("message") or {}
                models[m.get("model")] += 1
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        tools[b.get("name")] += 1
                        tool_inputs.append((b.get("name"), b.get("input")))
                    if isinstance(b, dict) and b.get("type") in ("server_tool_use",):
                        tools["SERVER:" + str(b.get("name"))] += 1
        if mode == "summary":
            print(f"== rep{rep} {proj} label={label[-4:]} wt={wt}")
            print("  init: model=%s perm=%s mcp=%s cwd_ok=%s ver=%s apiKeySource=%s plugins=%s skills=%d agents=%d tools=%d memory=%s" % (
                init.get("model"), init.get("permissionMode"), init.get("mcp_servers"), init.get("cwd", "").endswith(wt), init.get("claude_code_version"),
                init.get("apiKeySource"), [p["name"] for p in init.get("plugins", [])], len(init.get("skills", [])), len(init.get("agents", [])),
                len(init.get("tools", [])), {k: init.get(k) for k in init if "memory" in k.lower()}))
            print("  models:", dict(models), "subagent-events:", sub, "sessions:", len(sids))
            print("  tools:", dict(tools))
            print("  retries:", retries)
            print("  result: subtype=%s is_error=%s cost=%s turns=%s denials=%s dur_ms=%s" % (result.get("subtype"), result.get("is_error"), result.get("total_cost_usd"), result.get("num_turns"), result.get("permission_denials"), result.get("duration_ms")))
            print("  ts:", first_ts, "->", last_ts, "types:", {f"{a}/{b}": c for (a, b), c in types.items() if a not in ("assistant", "user")})
            mu = result.get("modelUsage") or {}
            print("  modelUsage keys:", list(mu))
        elif mode == "init":
            keys = {k: v for k, v in init.items() if k not in ("uuid", "session_id", "messaging_socket_path")}
            print(rep, proj, json.dumps(keys, sort_keys=True))
        elif mode == "calls":
            for name, inp in tool_inputs:
                if name in ("Write", "Edit"):
                    s = inp.get("file_path")
                elif name == "Read":
                    s = inp.get("file_path") + (" off=%s lim=%s" % (inp.get("offset"), inp.get("limit")))
                else:
                    s = json.dumps(inp)
                print(f"rep{rep}\t{proj}\t{name}\t{s}")
