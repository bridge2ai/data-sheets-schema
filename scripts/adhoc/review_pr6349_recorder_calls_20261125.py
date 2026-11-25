# Review helper (PR 6349 review): list recorder invocations and intervening edits for one transcript.
# Kept as review 1 of PR 6349 ran it (independent read-only review, 2026-11-25; report in
# notes/release_series_2026-11-25/review_1_pr6349.md), unchanged.
import json, sys
path = sys.argv[1]
results = {}
events = []
for line in open(path, encoding="utf-8"):
    e = json.loads(line)
    m = e.get("message") or {}
    for b in m.get("content") or [] if isinstance(m.get("content"), list) else []:
        if not isinstance(b, dict): continue
        if b.get("type") == "tool_use":
            events.append(("use", b["id"], b["name"], b.get("input") or {}, e.get("timestamp")))
        elif b.get("type") == "tool_result":
            c = b.get("content")
            if isinstance(c, list): c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
            results[b.get("tool_use_id")] = (b.get("is_error"), str(c))
seen_rec = False
for kind, tid, name, inp, ts in events:
    cmd = inp.get("command", "") if name == "Bash" else ""
    if "provenance record" in cmd:
        seen_rec = True
        err, out = results.get(tid, (None, ""))
        print(f"### {ts} RECORDER is_error={err}\n  CMD: {cmd[:700]}\n  OUT: {out[-900:]}\n")
    elif seen_rec and name in ("Write", "Edit"):
        print(f"--- {ts} {name} {inp.get('file_path')}  old={str(inp.get('old_string',''))[:150]!r} new={str(inp.get('new_string',''))[:150]!r}")
    elif seen_rec and name == "Bash":
        print(f"--- {ts} Bash {cmd[:250]!r}")
