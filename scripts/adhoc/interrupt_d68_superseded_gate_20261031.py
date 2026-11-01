#!/usr/bin/env python3
"""D68/#5212 LR12: interrupt only the superseded owned gate, 2026-10-31.

Input: its observed pytest PID. Output: a local interruption evidence record.
Verify the exact launcher/basetemp and parent gate command before SIGINT.
This preserves pytest's graceful reporting; it never signals unrelated jobs.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("pid", type=int)
args = parser.parse_args()
assert args.pid > 1
command = subprocess.check_output(["ps", "-p", str(args.pid), "-o", "command="], text=True).strip()
parent = subprocess.check_output(["ps", "-p", str(args.pid), "-o", "ppid="], text=True).strip()
parent_command = subprocess.check_output(["ps", "-p", parent, "-o", "command="], text=True).strip()
expected = root / ".d68-validation/merge/.d68-validation/merge-serial-shard-6-of-6"
assert str(expected) in command and "run_d68_offline_20261030.py" in command
assert "gate_d68_serial_20261030.py" in parent_command and "--tag merge-serial" in parent_command
destination = root / ".d68-validation/merge-serial-interruption.json"
assert not destination.exists()
os.kill(args.pid, signal.SIGINT)
destination.write_text(json.dumps({"time": datetime.now(timezone.utc).isoformat(),
    "pid": args.pid, "parent_pid": int(parent), "command": command,
    "parent_command": parent_command, "signal": "SIGINT",
    "reason": "LR12 production correction requires a new full gate; preserve five completed jobs and exclude this incomplete sixth shard from final coverage."}, indent=2) + "\n")
print(destination)
