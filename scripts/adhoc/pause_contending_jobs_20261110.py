#!/usr/bin/env python3
"""Pause/resume the two jobs explicitly authorized by the owner, 2026-11-10.

Inputs: fixed process identities below; action/job arguments.
Outputs: identity-pinned JSON journals in notes/reviews/live-resource-pause-20261110.
Serves: D4D live-monitoring recovery from ENOSPC; documentation PR 5711.
Uses only STOP/CONT signals. No process termination or artifact deletion.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes/reviews/live-resource-pause-20261110"
JOBS = {
    "website": (92782, 89865, "Mon Nov 9 21:22:28 2026",
                "/Users/marcin/Documents/newera/CultureBotAI/CultureBotAI.github.io"),
    "pfas": (92016, 91896, "Mon Nov 9 21:21:36 2026",
             "/Users/marcin/Documents/VIMSS/ontology/PFAS/PFASCommunityAgents"),
}


def processes():
    raw = subprocess.check_output(
        ["ps", "-A", "-o", "pid=,ppid=,pgid=,stat=,lstart=,comm="], text=True)
    result = {}
    for line in raw.splitlines():
        fields = line.split(None, 9)
        if len(fields) == 10:
            pid, ppid, pgid = map(int, fields[:3])
            result[pid] = dict(pid=pid, ppid=ppid, pgid=pgid, state=fields[3],
                               started=" ".join(fields[4:9]), command=fields[9])
    return result


def verify_root(job, rows):
    pid, pgid, started, expected_cwd = JOBS[job]
    row = rows[pid]
    if row["pgid"] != pgid or row["started"] != started:
        raise RuntimeError("process identity changed; no signal sent")
    cwd = subprocess.check_output(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], text=True)
    if "n" + expected_cwd not in cwd.splitlines():
        raise RuntimeError("process ownership path changed; no signal sent")
    return row


def same_identity(before, now):
    return all(before[k] == now[k] for k in ("pid", "pgid", "started", "command"))


def save(path, data):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "pause", "resume"))
    parser.add_argument("job", choices=JOBS)
    args = parser.parse_args()
    rows = processes()
    root = verify_root(args.job, rows)
    path = OUT / (args.job + ".json")
    if args.action == "check":
        print(json.dumps(root))
        return
    if args.action == "resume":
        data = json.loads(path.read_text())
        for before in data["targets"]:
            now = rows.get(before["pid"])
            if now is not None:
                if not same_identity(before, now):
                    raise RuntimeError("journal PID was reused; no resume for that PID")
                os.kill(before["pid"], signal.SIGCONT)
        data["resumed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(path, data)
        print(json.dumps({"job": args.job, "resumed": True, "journal": str(path)}))
        return
    if path.exists():
        raise RuntimeError("journal already exists; inspect it before further action")
    data = {"job": args.job, "authorization": "owner explicitly approved temporary pause in lead conversation",
            "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "targets": [root]}
    save(path, data)
    os.kill(root["pid"], signal.SIGSTOP)
    # Stop the controller first, then every Python worker in its verified group.
    # Parent git/just/uv processes remain untouched and wait for the controller.
    for _ in range(5):
        rows = processes()
        targets = [rows[root["pid"]]]
        if args.job == "pfas":
            targets = [r for r in rows.values() if r["pgid"] == root["pgid"]
                       and "python" in r["command"].lower()]
        known = {r["pid"] for r in data["targets"]}
        data["targets"].extend(r for r in targets if r["pid"] not in known)
        save(path, data)
        for target in targets:
            if "T" not in target["state"]:
                os.kill(target["pid"], signal.SIGSTOP)
        time.sleep(0.1)
        after = processes()
        if all(r["pid"] in after and same_identity(r, after[r["pid"]])
               and "T" in after[r["pid"]]["state"] for r in data["targets"]):
            data["stopped_verified"] = True
            data["verified_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            save(path, data)
            print(json.dumps({"job": args.job, "stopped_pids": [r["pid"] for r in data["targets"]],
                              "journal": str(path)}))
            return
    raise RuntimeError("not every targeted process is confirmed stopped; inspect journal")


if __name__ == "__main__":
    main()
