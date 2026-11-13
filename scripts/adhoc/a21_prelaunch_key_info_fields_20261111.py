#!/usr/bin/env python3
"""Purpose: a free, read-only look at what the provider reports for the
launch key before the A21 launch (owner decision D133): is the key accepted,
is it blocked or expired, and which spend and budget figures apply to it.

The repository's scripts/check_budget.py divides by the key's `max_budget`,
which is empty for this key, so it gives no reading. This asks the route the
run uses for three views and prints, for each, only:
  - the HTTP status;
  - the NAMES of the fields;
  - the VALUES of fields whose name mentions spend, budget, limit, expire,
    block or reset, and of nothing else.
It never prints the key, a user, team or project identifier, an email
address or metadata. For the team it says only whether the key has one.

Views (argument, default /key/info):
  /key/info    the key itself
  /user/info   the account the key belongs to
  /team/info   the team the key is charged to, if it has one (the team's
               identifier is read from /key/info and not printed)

Inputs: CBORG_API_KEY in the environment. Outputs: stdout only.
Serves: the A21 launch packet of 2026-11-11. Date: 2026-11-11.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.cborg.lbl.gov"
SHOW = ("spend", "budget", "limit", "expire", "block", "reset", "parallel", "last_active")
HIDE = ("user", "team", "email", "alias", "metadata", "token", "key_name", "id", "created_by", "updated_by")
SECTION = {"/key/info": "info", "/user/info": "user_info", "/team/info": "team_info"}


def shown(name: str) -> bool:
    low = name.lower()
    return any(s in low for s in SHOW) and not any(h in low for h in HIDE)


def fetch(key: str, path: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception as exc:  # network failure
        return type(exc).__name__, None


def report(endpoint: str, status, data) -> int:
    print("HTTP", status, "from", endpoint)
    if data is None:
        print("  no usable answer: the key was not accepted, the endpoint refused, or the network failed")
        return 1
    section = SECTION[endpoint]
    info = data.get(section) if isinstance(data, dict) else None
    if not isinstance(info, dict):
        print("  no `" + section + "` mapping in the answer; top-level names:", sorted(data) if isinstance(data, dict) else type(data).__name__)
        return 1
    print("  field names:", ", ".join(sorted(info)))
    # Names only, never values: they show whether a charging arrangement is
    # attached without disclosing it.
    for holder in ("metadata", "teams", "organization_memberships", "models"):
        value = info.get(holder)
        if isinstance(value, dict):
            print(f"  {holder}: names only: {', '.join(sorted(map(str, value))) or '(empty)'}")
        elif isinstance(value, list):
            print(f"  {holder}: list of {len(value)}")
    for name in sorted(info):
        value = info[name]
        if not shown(name):
            continue
        if isinstance(value, dict):
            inner = {k: v for k, v in value.items() if shown(k) and not isinstance(v, (dict, list))}
            print(f"  {name}: (mapping) {inner}")
        elif isinstance(value, list):
            print(f"  {name}: (list of {len(value)})")
        else:
            print(f"  {name}: {value!r}")
    return 0


def main() -> int:
    key = os.environ.get("CBORG_API_KEY")
    if not key:
        print("CBORG_API_KEY is not set")
        return 2
    endpoint = sys.argv[1] if len(sys.argv) > 1 else "/key/info"
    if endpoint not in SECTION:
        print("endpoint must be one of", ", ".join(SECTION))
        return 2
    if endpoint != "/team/info":
        status, data = fetch(key, endpoint)
        return report(endpoint, status, data)
    status, data = fetch(key, "/key/info")
    info = (data or {}).get("info") if isinstance(data, dict) else None
    if not isinstance(info, dict):
        print("HTTP", status, "from /key/info; cannot tell whether the key has a team")
        return 1
    for name in ("team_id", "project_id", "organization_id", "budget_id"):
        print(f"the key has a {name}: {info.get(name) is not None}")
    team = info.get("team_id")
    if team is None:
        print("the key is charged to no team; the account-level figures of /user/info apply")
        return 0
    status, data = fetch(key, "/team/info?team_id=" + urllib.parse.quote(str(team)))
    return report("/team/info", status, data)


if __name__ == "__main__":
    sys.exit(main())
