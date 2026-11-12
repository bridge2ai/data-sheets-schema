#!/usr/bin/env python3
"""Purpose: a free, read-only look at how the provider route prices and
limits the model the A21 registration names, before the launch (owner
decision D133). The launch packet prices the run at fixed list rates
"not refreshed online"; the provider charges an account budget by its own
table, which may price requests above a token threshold differently. The
BC1 typed calls are far above 200,000 input tokens each.

Asks `/model/info` on the route the run uses and prints, for every entry
whose name equals the model (default claude-opus-5), the fields whose name
mentions cost, token, context, tier or threshold. No identifier, key or
account detail is printed.

Inputs: CBORG_API_KEY in the environment; optional model name argument.
Outputs: stdout only.
Serves: the A21 launch packet of 2026-11-11. Date: 2026-11-11.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://api.cborg.lbl.gov"
SHOW = ("cost", "token", "context", "tier", "threshold", "mode", "provider")
HIDE = ("key", "base", "secret", "id")


def main() -> int:
    key = os.environ.get("CBORG_API_KEY")
    if not key:
        print("CBORG_API_KEY is not set")
        return 2
    model = sys.argv[1] if len(sys.argv) > 1 else "claude-opus-5"
    data = None
    for path in ("/model/info", "/v1/model/info"):
        req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + key})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                print("HTTP", resp.status, "from", path)
                data = json.loads(resp.read().decode())
                break
        except urllib.error.HTTPError as exc:
            print("HTTP", exc.code, "from", path)
        except Exception as exc:
            print("no answer from", path, type(exc).__name__)
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        print("no model table in the answer")
        return 1
    rows = data["data"]
    names = sorted({str(r.get("model_name")) for r in rows if isinstance(r, dict)})
    print("models listed:", len(names))
    hits = [r for r in rows if isinstance(r, dict) and r.get("model_name") == model]
    if not hits:
        near = [n for n in names if "opus" in n]
        print("no entry named", model, "; names containing 'opus':", ", ".join(near) or "(none)")
        return 1
    for i, row in enumerate(hits, 1):
        info = row.get("model_info") or {}
        print(f"entry {i} of {len(hits)} for {model}:")
        for name in sorted(info):
            low = name.lower()
            value = info[name]
            if value is None or isinstance(value, (dict, list)):
                continue
            if any(s in low for s in SHOW) and not any(h in low for h in HIDE):
                if isinstance(value, float) and "cost" in low:
                    print(f"  {name}: {value!r}  (= ${value * 1_000_000:.4f} per million)")
                else:
                    print(f"  {name}: {value!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
