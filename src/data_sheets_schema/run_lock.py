"""A sweep must be findable and stoppable without guessing a `pkill` pattern (#513).

On 2026-08-11 a `d4d api batch` was asked to stop. `pkill -f "d4d api"` matched
nothing and `pgrep -f "d4d api"` returned 0, so it was reported stopped. It ran
for about two more hours, because a console-script entry point does not carry
its own name in `argv`:

    /Users/…/.venv/bin/python -c import sys; from importlib import import_module; …

Nothing in that string contains `d4d`, `api` or `batch`. Worse, a second batch
was then launched for the same labels while the first was still alive, so two
processes wrote the same directories — which is the most likely reason one
record ended up invalid and why files appeared to change under `git`.

So a running sweep writes a lock naming itself. The lock is the answer to three
questions a `pkill` pattern cannot answer: is one running, what is it doing, and
what is its pid.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

LOCK_DIR = Path("data/.run_locks")


@dataclass
class Lock:
    path: Path
    pid: int
    label_prefix: str
    projects: list[str]
    started: str

    @property
    def alive(self) -> bool:
        """Is the process still running?

        Signal 0 checks for existence without delivering anything. A stale lock
        left by a killed process must not make the next sweep refuse to start —
        that would turn a crash into a permanent block.

        A **zombie** is not alive. `os.kill(pid, 0)` succeeds for a process that
        has exited but not yet been reaped by its parent, so a sweep stopped by
        a launcher still holding the handle would read as running and its label
        would stay blocked. Found by a test that stopped a real child and then
        asked whether it had stopped.
        """
        try:
            os.kill(self.pid, 0)
        except (ProcessLookupError, ValueError):
            return False
        except PermissionError:
            return True                      # exists, owned by someone else
        return not self._is_zombie()

    def _is_zombie(self) -> bool:
        try:
            out = subprocess.run(["ps", "-p", str(self.pid), "-o", "state="],
                                 capture_output=True, text=True, check=False)
        except OSError:
            return False
        return out.stdout.strip().startswith("Z")


def _path_for(label_prefix: str, lock_dir: Path = LOCK_DIR) -> Path:
    safe = label_prefix.replace("/", "_")
    return Path(lock_dir) / f"{safe}.json"


def read(path: Path) -> Lock | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if "pid" not in data:
        return None
    return Lock(path=Path(path), pid=int(data["pid"]),
                label_prefix=data.get("label_prefix", "?"),
                projects=data.get("projects", []),
                started=data.get("started", "?"))


def live(lock_dir: Path = LOCK_DIR) -> list[Lock]:
    """Every lock whose process is still running.

    Stale locks are reported by `stale()` rather than silently deleted here: a
    lock left behind is evidence that a sweep died without cleaning up, and
    quietly removing it hides that.
    """
    return [l for l in _all(lock_dir) if l.alive]


def stale(lock_dir: Path = LOCK_DIR) -> list[Lock]:
    return [l for l in _all(lock_dir) if not l.alive]


def _all(lock_dir: Path = LOCK_DIR) -> list[Lock]:
    d = Path(lock_dir)
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        lock = read(p)
        if lock:
            out.append(lock)
    return out


class AlreadyRunning(RuntimeError):
    """A live sweep already holds this label prefix."""


def acquire(label_prefix: str, projects: list[str],
            lock_dir: Path = LOCK_DIR) -> Path:
    """Claim a label prefix for this process.

    Refuses when a live sweep already holds it. Two processes writing the same
    label directories is not a race to be tolerated: each writes phase
    snapshots and a progress file under the same names, so the survivor's
    record can be a mixture of both runs and its provenance would describe
    neither.
    """
    path = _path_for(label_prefix, lock_dir)
    existing = read(path)
    if existing and existing.alive:
        raise AlreadyRunning(
            f"pid {existing.pid} has been running {label_prefix} since "
            f"{existing.started}. Stop it with `d4d api stop "
            f"--label-prefix {label_prefix}`, or use a different label.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "pid": os.getpid(),
        "label_prefix": label_prefix,
        "projects": projects,
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n", encoding="utf-8")
    return path


def release(path: Path) -> None:
    """Drop the lock. Missing is fine — release must never be the thing that
    fails at the end of an otherwise successful sweep."""
    try:
        Path(path).unlink()
    except OSError:
        pass


def stop(lock: Lock, sig: int = signal.SIGTERM) -> bool:
    """Signal the process a lock names. Returns whether the signal was sent."""
    try:
        os.kill(lock.pid, sig)
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return False
    return True
