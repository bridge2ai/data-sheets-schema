#!/usr/bin/env python3
"""
Purpose: Read-only file-class cleanup safety assessor for `d4d-executions/` roots and
  registered git worktrees, implementing `notes/coordination/2026-11-07-cleanup-safety-system.md`
  and the review refinements in Parts 64, 66, 66b, 67, and 68.
Inputs:
  --roots [PATH ...] : Paths to assess (default: every entry directly under
                       `d4d-executions/` plus every registered git worktree).
  --remote REMOTE    : Remote name to check for commit reachability (default: `origin`,
                       including `refs/remotes/origin/*` and `refs/tags/archive/*`).
  --out DIR          : Output directory for `ledger.json`, `summary.md`, and `ledger.html`.
Outputs:
  <out>/ledger.json  : One record per root with per-class bytes (`C`, `R`, `R-local`, `V`, `U`,
                       `KEEP-SECRET`, `git_metadata`), source commit & how established, real git
                       state (`rev-parse HEAD`, own refs, own objects, alternates), live-process
                       check, root & sub-path citations, guards fired, and proposed action.
  <out>/summary.md   : Markdown summary of totals per action (`DELETE-SAFE`, `WORKTREE-REMOVE`,
                       `GITDIR-REMOVE`, `COMPRESS-ARCHIVE`, `KEEP-SECRET-REVIEW`, `KEEP`) and
                       file class, roots caught by guards, and per-root table.
  <out>/ledger.html  : Self-contained static HTML review page with sortable/filterable table
                       and totals per action and class (no external scripts).
Date: 2026-11-07
Safety:
  STRICTLY READ-ONLY. Has no delete, move, or compress mode.
  Never reads or hashes files matching secret patterns (`*.env`, `.env*`, `*token*`,
  `*credential*`, `*secret*`, `*.pem`, `*key*`): tracked clean secret-named files in
  `origin`-reachable `.git` roots are classified as `R (git-status, unread)` by git status;
  untracked/ignored/modified or non-`.git` secret-named files become `KEEP-SECRET`
  (`KEEP-SECRET-REVIEW`, never archived or deleted).
  Pauses whenever `d4d-executions/plans/native_quiet_window.lock` exists and runs
  git/hashing subprocesses under `nice -n 15`.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
import hashlib
import html
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path
from typing import Any

HASH_SEMAPHORE = threading.Semaphore(6)

PRIMARY_REPO = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema"
EXECUTIONS_ROOT = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions"
QUIET_LOCK_PATH = os.path.join(EXECUTIONS_ROOT, "plans", "native_quiet_window.lock")
CLEANUP_SAFETY_DIR = os.path.join(EXECUTIONS_ROOT, "plans", "reviews", "cleanup_safety_2026-11-07")
CACHED_ROOT_CITATIONS_JSON = os.path.join(CLEANUP_SAFETY_DIR, "root_citations.json")
CACHED_SUBPATH_CITATIONS_JSON = os.path.join(CLEANUP_SAFETY_DIR, "subpath_citations.json")

GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
}

SECRET_PATTERNS = (
    "*.env",
    ".env",
    ".env.*",
    "*token*",
    "*credential*",
    "*secret*",
    "*.pem",
    "*key*",
)

CACHE_DIR_NAMES = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
})

VENV_DIR_NAMES = frozenset({
    ".venv",
    "venv",
    "node_modules",
    ".tox",
    ".nox",
})

SENTINEL_PATHS = (
    "pyproject.toml",
    "src/data_sheets_schema/shared_generation.py",
    "src/data_sheets_schema/api_runner.py",
    "src/data_sheets_schema/latch_journal.py",
    "src/download/prompts/canonical_hashes.yaml",
    "tests/utils/run_spec_boundary_contracts.json",
)

ALWAYS_KEEP_EXACT = frozenset({
    "data-sheets-schema",
    "aireadi-v8-b",
    "launch-a21",
    "native-u3-base",
    "codex-native-u1",
    "codex-native-u2",
    "codex-native-u3a",
    "codex-native-u3b",
    "scratch-native-u1",
    "scratch-native-u3b",
    "scratch-u1-packet-rehearsal",
    "scratch-a21-precheck",
    "scratch-a21-dryrun",
    "agy-a21-precheck",
    "scratch-project-readiness",
    "plans",
    "evidence",
    "logs",
    "lineage-durable",
    "reviews-2026-10-23",
    "reviews-2026-10-24",
    # Named by open issues/decisions (#5448, #5495, #2912, decision-index, native-assess)
    "codex-5448",
    "scratch-codex-5448-20261105",
    "scratch-issue-h",
    "scratch-support-judge",
    "scratch-decision-index",
    "scratch-native-assess",
})

SELF_CITATION_EXCLUDES = (
    "disk_inventory_2026-11-05.md",
    "disk_cleanup_proposal_2026-11-07.md",
    "2026-11-07-cleanup-safety-system.md",
    "2026-11-07-agy-prompt-part63.md",
    "2026-11-07-agy-prompt-part64.md",
    "2026-11-07-agy-prompt-part65.md",
    "2026-11-07-agy-prompt-part66.md",
    "2026-11-07-agy-prompt-part66b.md",
    "cleanup_safety_2026-11-07",
)


def wait_for_quiet_window() -> None:
    """Pause while `d4d-executions/plans/native_quiet_window.lock` exists."""
    warned = False
    while os.path.exists(QUIET_LOCK_PATH):
        if not warned:
            print(f"[pause] {QUIET_LOCK_PATH} exists; pausing until removed...", file=sys.stderr, flush=True)
            warned = True
        time.sleep(5)
    if warned:
        print(f"[resume] {QUIET_LOCK_PATH} removed; continuing.", file=sys.stderr, flush=True)


def fmt_bytes(b: int) -> str:
    if b >= 1024 ** 3:
        return f"{b / (1024 ** 3):.2f} GiB"
    if b >= 1024 ** 2:
        return f"{b / (1024 ** 2):.2f} MiB"
    if b >= 1024:
        return f"{b / 1024:.2f} KiB"
    return f"{b} B"


def is_secret_filename(name: str) -> bool:
    low = name.lower()
    return any(fnmatch.fnmatch(low, pat) for pat in SECRET_PATTERNS)


def is_always_keep_root(root_path: str) -> tuple[bool, str | None]:
    norm = os.path.normpath(root_path)
    base = os.path.basename(norm)
    if norm == os.path.normpath(PRIMARY_REPO):
        return True, "always_keep:primary_checkout"
    if base in ALWAYS_KEEP_EXACT:
        return True, f"always_keep:{base}"
    if base.startswith("codex-native-u") or base.startswith("native-u0-") or base.startswith("native-u3"):
        return True, f"always_keep:native_unit({base})"
    if "/native-u0-20261106/" in norm.replace("\\", "/"):
        return True, "always_keep:native_u0_worktree"
    if "/plans/a21_registration_" in norm.replace("\\", "/") or base.startswith("a21_registration_"):
        return True, f"always_keep:a21_registration({base})"
    if "/plans/reviews" in norm.replace("\\", "/"):
        return True, "always_keep:plans_reviews"
    return False, None


def is_pytest_basetemp_dir(dirpath: str, dirnames: list[str], filenames: list[str]) -> bool:
    base = os.path.basename(dirpath)
    if base.startswith("pytest-of-") or base.endswith("-pytest") or base in ("basetemp", ".pytest_basetemp"):
        return True
    if any(d.startswith("popen-gw") for d in dirnames):
        return True
    for entry in dirnames + filenames:
        if entry.startswith("test_") and entry.endswith("current"):
            full = os.path.join(dirpath, entry)
            if os.path.islink(full):
                return True
    return False


class GitIndex:
    """Pre-indexed Git repository state for fast commit lookup, ls-tree caching, and reachability."""

    def __init__(self, repo_path: str, remote: str = "origin") -> None:
        self.repo_path = repo_path
        self.remote = remote
        self._lock = threading.Lock()
        self.all_commits: set[str] = set()
        self.prefix_map: dict[str, list[str]] = {}
        self.remote_branch_only_commits: set[str] = set()
        self.remote_archive_tag_commits: set[str] = set()
        self.remote_reachable_commits: set[str] = set()
        self.commit_to_remote_refs: dict[str, list[str]] = {}
        self.commit_to_local_refs: dict[str, list[str]] = {}
        self.commit_to_points_at_refs: dict[str, list[str]] = {}
        self.sentinel_index: dict[tuple[str, str], set[str]] = {}
        self.ls_tree_cache: dict[str, dict[str, tuple[str, int]]] = {}
        self.git_archive_sha256_cache: dict[str, str] = {}
        self.worktree_info: dict[str, dict[str, Any]] = {}
        self._load()

    def _run_git(self, args: list[str], cwd: str | None = None, text: bool = True, input_data: bytes | str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo_path,
            env=GIT_ENV,
            input=input_data,
            capture_output=True,
            text=text,
        )

    def _load(self) -> None:
        wait_for_quiet_window()
        # 1. Worktrees
        wt_out = self._run_git(["worktree", "list", "--porcelain"]).stdout
        cur: dict[str, Any] = {}
        for line in wt_out.splitlines():
            if not line.strip():
                if "worktree" in cur:
                    self.worktree_info[os.path.normpath(cur["worktree"])] = cur
                cur = {}
            elif line.startswith("worktree "):
                cur["worktree"] = line[9:].strip()
            elif line.startswith("HEAD "):
                cur["HEAD"] = line[5:].strip()
            elif line.startswith("branch "):
                cur["branch"] = line[7:].strip()
            elif line == "detached":
                cur["detached"] = True
        if "worktree" in cur:
            self.worktree_info[os.path.normpath(cur["worktree"])] = cur

        # 2. All commits (including worktree HEADs)
        extra_heads = [v["HEAD"] for v in self.worktree_info.values() if "HEAD" in v]
        rev_out = self._run_git(["rev-list", "--all", *extra_heads]).stdout.splitlines()
        for sha in rev_out:
            sha = sha.strip()
            if len(sha) == 40:
                self.all_commits.add(sha)
                for plen in (4, 5, 6, 7, 8, 9, 10, 11, 12, 40):
                    self.prefix_map.setdefault(sha[:plen], []).append(sha)

        # 3. All commits reachable from remote refs (branches on `origin` + `archive/*` tags on `origin`)
        branch_refs_out = self._run_git([
            "for-each-ref",
            f"refs/remotes/{self.remote}",
            "--format=%(refname)",
        ]).stdout.splitlines()
        remote_branch_refs = [
            r.strip() for r in branch_refs_out
            if r.strip() and not r.strip().startswith(f"refs/remotes/{self.remote}/tags/")
        ]
        remote_archive_refs = [
            r.strip() for r in branch_refs_out
            if r.strip().startswith(f"refs/remotes/{self.remote}/tags/archive/")
        ]
        # Also include any peeled `refs/tags/archive/*` from `git ls-remote origin` if network is reachable,
        # plus local `refs/tags/archive/native-*` (verified on origin in Part 65)
        ls_rem_shas: list[str] = []
        try:
            ls_proc = subprocess.run(
                ["git", "ls-remote", self.remote, "refs/tags/archive/*"],
                cwd=self.repo_path,
                env=GIT_ENV,
                capture_output=True,
                text=True,
                timeout=4,
            )
            if ls_proc.returncode == 0:
                for line in ls_proc.stdout.splitlines():
                    parts = line.split()
                    if len(parts) == 2 and len(parts[0]) == 40 and parts[0] in self.all_commits:
                        ls_rem_shas.append(parts[0])
        except Exception:
            pass

        if remote_branch_refs:
            for sha in self._run_git(["rev-list", *remote_branch_refs]).stdout.splitlines():
                sha = sha.strip()
                if len(sha) == 40:
                    self.remote_branch_only_commits.add(sha)

        arch_rev_inputs = list(dict.fromkeys([*remote_archive_refs, *ls_rem_shas, "--tags=archive/native-*"]))
        for sha in self._run_git(["rev-list", *arch_rev_inputs]).stdout.splitlines():
            sha = sha.strip()
            if len(sha) == 40:
                self.remote_archive_tag_commits.add(sha)

        self.remote_reachable_commits = self.remote_branch_only_commits | self.remote_archive_tag_commits

        # 4. Build sentinel blob index across all commits in one batch call
        commits_list = sorted(self.all_commits)
        queries: list[str] = []
        for c in commits_list:
            for sp in SENTINEL_PATHS:
                queries.append(f"{c}:{sp}")
        batch_out = self._run_git(
            ["cat-file", "--batch-check=%(objectname)"],
            input_data="\n".join(queries),
            text=True,
        ).stdout.splitlines()
        idx = 0
        for c in commits_list:
            for sp in SENTINEL_PATHS:
                if idx < len(batch_out):
                    line = batch_out[idx].strip()
                    if len(line) == 40 and not line.endswith("missing"):
                        self.sentinel_index.setdefault((sp, line), set()).add(c)
                idx += 1

    def resolve_prefix(self, token: str) -> list[str]:
        low = token.lower()
        if len(low) == 40 and low in self.all_commits:
            return [low]
        if len(low) in self.prefix_map:
            return self.prefix_map[low]
        for plen in (12, 11, 10, 9, 8, 7, 6, 5, 4):
            if len(low) >= plen and low[:plen] in self.prefix_map:
                return [s for s in self.prefix_map[low[:plen]] if s.startswith(low)]
        return []

    def is_remote_reachable(self, sha: str) -> bool:
        return sha in self.remote_reachable_commits

    def is_archive_tag_only_reachable(self, sha: str) -> bool:
        """Return True iff `sha` is reachable on `origin` ONLY via `archive/*` tags (converted from R-local to R)."""
        return sha in self.remote_reachable_commits and sha not in self.remote_branch_only_commits

    def get_remote_refs(self, sha: str) -> list[str]:
        with self._lock:
            if sha in self.commit_to_remote_refs:
                return self.commit_to_remote_refs[sha]
        if not self.is_remote_reachable(sha):
            refs: list[str] = []
        else:
            out = self._run_git([
                "for-each-ref",
                "--contains",
                sha,
                f"refs/remotes/{self.remote}",
                "refs/tags/archive/native-*",
                "--format=%(refname:short)",
            ]).stdout.splitlines()
            refs = [r.strip() for r in out if r.strip() and not r.strip().endswith("/HEAD") and r.strip() != self.remote]
        with self._lock:
            self.commit_to_remote_refs[sha] = refs
            return refs

    def get_points_at_refs(self, sha: str) -> list[str]:
        with self._lock:
            if sha in self.commit_to_points_at_refs:
                return self.commit_to_points_at_refs[sha]
        out = self._run_git([
            "for-each-ref",
            "--points-at",
            sha,
            "refs/heads",
            f"refs/remotes/{self.remote}",
            "refs/tags/archive/native-*",
            "--format=%(refname:short)",
        ]).stdout.splitlines()
        refs = [r.strip() for r in out if r.strip() and not r.strip().endswith("/HEAD") and r.strip() != self.remote]
        with self._lock:
            self.commit_to_points_at_refs[sha] = refs
            return refs

    def get_local_refs(self, sha: str) -> list[str]:
        with self._lock:
            if sha in self.commit_to_local_refs:
                return self.commit_to_local_refs[sha]
        out = self._run_git([
            "for-each-ref",
            "--contains",
            sha,
            "refs/heads",
            "refs/tags",
            "--format=%(refname:short)",
        ]).stdout.splitlines()
        refs = [r.strip() for r in out if r.strip()]
        for wt_path, info in self.worktree_info.items():
            if info.get("HEAD") == sha:
                refs.append(f"worktree:{os.path.basename(wt_path)}")
        with self._lock:
            self.commit_to_local_refs[sha] = refs
            return refs

    def get_ls_tree(self, sha: str, cwd: str | None = None) -> dict[str, tuple[str, int]]:
        """Return mapping of rel_path -> (blob_sha1, blob_size) for commit `sha`.
        When `cwd` is provided (or `sha` is a local-only commit in a standalone `.git` root),
        runs `git ls-tree` in `cwd` so its own objects and alternates resolve."""
        with self._lock:
            if sha in self.ls_tree_cache and self.ls_tree_cache[sha]:
                return self.ls_tree_cache[sha]
        wait_for_quiet_window()
        run_cwd = cwd if (cwd and sha not in self.all_commits) else (cwd or self.repo_path)
        proc = self._run_git(["ls-tree", "-r", "-l", "-z", sha], cwd=run_cwd, text=False)
        if proc.returncode != 0 and cwd and run_cwd != cwd:
            proc = self._run_git(["ls-tree", "-r", "-l", "-z", sha], cwd=cwd, text=False)
        raw = proc.stdout
        tree: dict[str, tuple[str, int]] = {}
        for entry in raw.split(b"\0"):
            if not entry:
                continue
            meta, path_b = entry.split(b"\t", 1)
            parts = meta.split()
            if len(parts) >= 4:
                mode = parts[0].decode("ascii", "replace")
                obj_type = parts[1].decode("ascii", "replace")
                blob_sha = parts[2].decode("ascii", "replace")
                size_str = parts[3].decode("ascii", "replace")
                if obj_type == "blob" and mode != "160000":
                    try:
                        sz = int(size_str)
                    except ValueError:
                        sz = -1
                    tree[path_b.decode("utf-8", "replace")] = (blob_sha, sz)
        with self._lock:
            if tree or sha not in self.ls_tree_cache:
                self.ls_tree_cache[sha] = tree
            return self.ls_tree_cache[sha]


def _hash_chunk(chunk: list[str]) -> dict[str, str]:
    wait_for_quiet_window()
    out: dict[str, str] = {}
    with HASH_SEMAPHORE:
        proc = subprocess.run(
            ["nice", "-n", "15", "git", "hash-object", "--no-filters", "--stdin-paths"],
            cwd=PRIMARY_REPO,
            env=GIT_ENV,
            input="\n".join(chunk).encode("utf-8"),
            capture_output=True,
        )
    lines = proc.stdout.decode("ascii", "replace").splitlines()
    if proc.returncode == 0 and len(lines) == len(chunk):
        for fp, h in zip(chunk, lines):
            out[fp] = h.strip()
    else:
        for fp in chunk:
            try:
                with open(fp, "rb") as f:
                    data = f.read()
                hdr = f"blob {len(data)}\0".encode("ascii")
                out[fp] = hashlib.sha1(hdr + data).hexdigest()
            except OSError:
                pass
    return out


def hash_files_batched(file_paths: list[str], root_label: str = "") -> dict[str, str]:
    """Run `nice -n 15 git hash-object --no-filters --stdin-paths` in streaming batches of 3,000 files,
    logging progress every 10,000 files and respecting `native_quiet_window.lock`."""
    result: dict[str, str] = {}
    if not file_paths:
        return result
    batch_size = 3000
    chunks = [file_paths[i : i + batch_size] for i in range(0, len(file_paths), batch_size)]
    if len(chunks) == 1:
        return _hash_chunk(chunks[0])
    processed = 0
    next_progress = 10000
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(chunks))) as ex:
        for chunk_res in ex.map(_hash_chunk, chunks):
            result.update(chunk_res)
            processed += len(chunk_res)
            if processed >= next_progress:
                print(
                    f"[progress] {root_label}: hashed {processed:,}/{len(file_paths):,} candidate R files...",
                    file=sys.stderr,
                    flush=True,
                )
                next_progress += 10000
    return result


def collect_live_processes() -> list[tuple[int, str, str, str]]:
    """Return list of (pid, cmd, fd_type, path) from `lsof -d cwd` and bounded `lsof -nP`."""
    my_pid = os.getpid()
    records: list[tuple[int, str, str, str]] = []
    seen: set[tuple[int, str]] = set()
    for args, label in (
        (["lsof", "-d", "cwd", "-F", "pcn"], "cwd"),
        (["lsof", "-nP", "-F", "pcn"], "open_fd"),
    ):
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=12)
        except Exception:
            continue
        cur_pid = 0
        cur_cmd = ""
        for line in proc.stdout.splitlines():
            if not line:
                continue
            tag, val = line[0], line[1:]
            if tag == "p":
                try:
                    cur_pid = int(val)
                except ValueError:
                    cur_pid = 0
            elif tag == "c":
                cur_cmd = val
            elif tag == "n" and cur_pid and cur_pid != my_pid:
                if val.startswith("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/"):
                    key = (cur_pid, val)
                    if key not in seen:
                        seen.add(key)
                        records.append((cur_pid, cur_cmd, label, os.path.normpath(val)))
    return records


def build_citations_map(roots: list[str]) -> dict[str, dict[str, Any]]:
    """Load precomputed root citations map (`root_citations.json`), or build if missing."""
    result: dict[str, dict[str, Any]] = {}
    if os.path.exists(CACHED_ROOT_CITATIONS_JSON):
        try:
            cached = json.load(open(CACHED_ROOT_CITATIONS_JSON))
            for k, v in cached.items():
                if isinstance(v, dict) and "total_count" in v:
                    result[k] = v
        except Exception:
            pass

    all_basenames = sorted({os.path.basename(os.path.normpath(r)) for r in roots if os.path.basename(os.path.normpath(r))})
    missing_basenames = [b for b in all_basenames if b not in result]
    if not missing_basenames:
        return result

    base_to_files: dict[str, set[str]] = {}
    pat_file = "/tmp/d4d_cleanup_safety_patterns_20261107.txt"
    out_file = "/tmp/d4d_cleanup_safety_rg_hits_20261107.txt"
    with open(pat_file, "w") as f:
        for b in missing_basenames:
            f.write(b + "\n")

    search_dirs = [
        os.path.join(EXECUTIONS_ROOT, "plans"),
        os.path.join(PRIMARY_REPO, "notes"),
        os.path.join(PRIMARY_REPO, "data"),
    ]
    wait_for_quiet_window()
    try:
        with open(out_file, "w") as out_f:
            subprocess.run(
                ["rg", "--no-ignore", "--hidden", "--no-heading", "--with-filename", "-o", "-F", "-f", pat_file, *search_dirs],
                stdout=out_f,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=120,
            )
        with open(out_file, errors="replace") as in_f:
            for line in in_f:
                line = line.rstrip("\r\n")
                if ":" not in line:
                    continue
                fpath, pat = line.rsplit(":", 1)
                base_to_files.setdefault(pat.strip(), set()).add(fpath.strip())
    except Exception:
        pass
    finally:
        for tf in (pat_file, out_file):
            try:
                if os.path.exists(tf):
                    os.remove(tf)
            except OSError:
                pass

    for b in missing_basenames:
        raw_files = base_to_files.get(b, set())
        filtered = sorted(
            f for f in raw_files
            if not any(excl in f for excl in SELF_CITATION_EXCLUDES)
        )
        tot_c, sub_c, top5_c = rank_citations(filtered)
        result[b] = {
            "total_count": tot_c,
            "substantive_count": sub_c,
            "citing_files_up_to_5": top5_c,
        }
    return result


def load_subpath_citations_map() -> dict[str, dict[str, list[str]]]:
    """Load precomputed sub-path citations map (`subpath_citations.json`), expanding brace ranges like `{1..6}`."""
    if not os.path.exists(CACHED_SUBPATH_CITATIONS_JSON):
        return {}
    try:
        raw = json.load(open(CACHED_SUBPATH_CITATIONS_JSON))
    except Exception:
        return {}
    expanded: dict[str, dict[str, list[str]]] = {}
    brace_re = re.compile(r"\{(\d+)\.\.(\d+)\}")
    for root_base, sp_dict in raw.items():
        if not isinstance(sp_dict, dict):
            continue
        out_sp: dict[str, list[str]] = {}
        for sp, cfiles in sp_dict.items():
            sp_clean = sp.strip("/")
            if not sp_clean or sp_clean in ("*", "**"):
                continue
            m = brace_re.search(sp_clean)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                if 0 <= (hi - lo) <= 50:
                    for idx in range(lo, hi + 1):
                        exp_p = sp_clean[: m.start()] + str(idx) + sp_clean[m.end() :]
                        out_sp[exp_p] = cfiles
                    continue
            out_sp[sp_clean] = cfiles
        expanded[root_base] = out_sp
    return expanded


def scan_all_alternates(
    roots: list[str],
    primary_repo: str = PRIMARY_REPO,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """
    Scan every `objects/info/alternates` file under every root, under `<primary>/.git/objects/info/alternates`,
    and under `<primary>/.git/worktrees/*/objects/info/alternates`.
    Returns:
      - `lender_to_borrowers`: maps `norm_lender_root -> sorted list of borrower basenames`
      - `root_to_alternates`: maps `norm_root -> sorted list of normalized target paths`
    """
    norm_primary = os.path.normpath(primary_repo)
    norm_roots = sorted({os.path.normpath(r) for r in roots}, key=len, reverse=True)
    root_to_alternates: dict[str, list[str]] = {}
    lender_to_borrowers_set: dict[str, set[str]] = {}

    alt_sources: list[tuple[str, str, str]] = []  # (borrower_norm_root_or_label, borrower_basename, alt_file_path)
    prim_alt = os.path.join(norm_primary, ".git", "objects", "info", "alternates")
    if os.path.isfile(prim_alt):
        alt_sources.append((norm_primary, os.path.basename(norm_primary), prim_alt))

    wt_admin_root = os.path.join(norm_primary, ".git", "worktrees")
    if os.path.isdir(wt_admin_root):
        try:
            for wname in sorted(os.listdir(wt_admin_root)):
                walt = os.path.join(wt_admin_root, wname, "objects", "info", "alternates")
                if os.path.isfile(walt):
                    alt_sources.append((f"{norm_primary}/.git/worktrees/{wname}", f"worktree:{wname}", walt))
        except OSError:
            pass

    for nr in norm_roots:
        git_p = os.path.join(nr, ".git")
        if os.path.isdir(git_p):
            ralt = os.path.join(git_p, "objects", "info", "alternates")
            if os.path.isfile(ralt):
                alt_sources.append((nr, os.path.basename(nr), ralt))

    for borrower_key, borrower_base, alt_fp in alt_sources:
        targets: list[str] = []
        obj_dir = os.path.dirname(os.path.dirname(alt_fp))
        try:
            lines = Path(alt_fp).read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            raw_t = line.strip()
            if not raw_t or raw_t.startswith("#"):
                continue
            resolved = os.path.normpath(raw_t if os.path.isabs(raw_t) else os.path.join(obj_dir, raw_t))
            targets.append(resolved)
            # Determine which root `resolved` lies inside
            for candidate_lender in norm_roots:
                if candidate_lender == norm_primary:
                    continue
                if resolved == candidate_lender or resolved.startswith(candidate_lender + os.sep):
                    if candidate_lender != borrower_key:
                        lender_to_borrowers_set.setdefault(candidate_lender, set()).add(borrower_base)
                    break
        if borrower_key in norm_roots:
            root_to_alternates[borrower_key] = targets

    lender_to_borrowers = {k: sorted(v) for k, v in lender_to_borrowers_set.items()}
    return lender_to_borrowers, root_to_alternates


def rank_citations(citing_files: list[str]) -> tuple[int, int, list[str]]:
    """Return (total_count, substantive_count, up_to_5_rel_paths)."""
    def rel_label(p: str) -> str:
        if p.startswith(EXECUTIONS_ROOT + "/"):
            return p[len(EXECUTIONS_ROOT) + 1 :]
        if p.startswith(PRIMARY_REPO + "/"):
            return "data-sheets-schema/" + p[len(PRIMARY_REPO) + 1 :]
        return p

    substantive: list[str] = []
    other: list[str] = []
    for f in citing_files:
        rl = rel_label(f)
        if rl.startswith("plans/cleanup_") or rl.startswith("plans/codex_logs/"):
            other.append(rl)
        else:
            substantive.append(rl)
    ordered = sorted(substantive) + sorted(other)
    return len(citing_files), len(substantive), ordered[:5]


def establish_tree_commit(
    tree_path: str,
    root_path: str,
    git_index: GitIndex,
) -> tuple[str | None, str]:
    """Establish the source commit SHA for an unpacked repository tree `tree_path` inside `root_path`."""
    norm_tree = os.path.normpath(tree_path)
    norm_root = os.path.normpath(root_path)

    # 1. Part 66b Fix 4: If `tree_path` has `.git` (file or directory), ALWAYS read `git -C <tree_path> rev-parse HEAD`
    #    run in `norm_tree` so its alternates resolve. NO fallback to name-token commits or companion files.
    if os.path.exists(os.path.join(norm_tree, ".git")):
        proc = git_index._run_git(["rev-parse", "HEAD"], cwd=norm_tree)
        sha = proc.stdout.strip()
        if len(sha) == 40:
            label = "git_worktree_HEAD" if norm_tree in git_index.worktree_info else "git_HEAD"
            return sha, f"{label} ({sha[:12]})"
        return None, "git_HEAD_unresolved"

    # 2. Check explicit companion commit files: `<tree_path>-commit.txt` or `<tree_path>/commit.txt`
    tree_base = os.path.basename(norm_tree)
    companion_candidates = [
        (os.path.join(os.path.dirname(norm_tree), f"{tree_base}-commit.txt"), f"{tree_base}-commit.txt"),
        (os.path.join(norm_tree, "commit.txt"), "commit.txt"),
    ]
    if norm_tree == norm_root:
        for fn in sorted(os.listdir(norm_root)):
            if fn.endswith("commit.txt") and not is_secret_filename(fn):
                companion_candidates.append((os.path.join(norm_root, fn), fn))

    for cpath, clabel in companion_candidates:
        if os.path.isfile(cpath) and not is_secret_filename(os.path.basename(cpath)):
            try:
                if os.path.getsize(cpath) < 4096:
                    txt = Path(cpath).read_text(errors="replace").strip()
                    for m in re.findall(r"\b([0-9a-f]{7,40})\b", txt.lower()):
                        resolved = git_index.resolve_prefix(m)
                        if len(resolved) == 1:
                            return resolved[0], f"commit_file:{clabel}"
            except OSError:
                pass

    # 2b. Check companion `<stem>.tar` PAX header comment (e.g., `d68.tar` for `d68-archive`, `m7.tar` for `m7`)
    stem = tree_base[:-8] if tree_base.endswith("-archive") else tree_base
    tar_candidates = [
        (os.path.join(os.path.dirname(norm_tree), f"{stem}.tar"), f"{stem}.tar"),
        (os.path.join(os.path.dirname(norm_tree), f"{tree_base}.tar"), f"{tree_base}.tar"),
    ]
    for tpath, tlabel in tar_candidates:
        if os.path.isfile(tpath) and not is_secret_filename(os.path.basename(tpath)):
            try:
                with tarfile.open(tpath, "r") as tf:
                    csha = tf.pax_headers.get("comment", "").strip().lower()
                if len(csha) == 40 and csha in git_index.all_commits:
                    return csha, f"companion_tar_pax:{tlabel}"
            except Exception:
                pass

    # 3. Hash the sentinel files + up to 25 recently modified .py files in `tree_path`
    probe_rel_paths: list[str] = []
    for sp in SENTINEL_PATHS:
        fp = os.path.join(norm_tree, sp)
        if os.path.isfile(fp) and not os.path.islink(fp) and not is_secret_filename(os.path.basename(fp)):
            probe_rel_paths.append(sp)

    py_files: list[tuple[float, str]] = []
    for sub in ("src", "tests", "scripts"):
        sub_dir = os.path.join(norm_tree, sub)
        if not os.path.isdir(sub_dir):
            continue
        for dp, dns, fns in os.walk(sub_dir):
            dns[:] = [d for d in dns if d not in CACHE_DIR_NAMES]
            for fn in fns:
                if fn.endswith(".py") and not is_secret_filename(fn):
                    fp = os.path.join(dp, fn)
                    if not os.path.islink(fp) and os.path.isfile(fp):
                        rel = os.path.relpath(fp, norm_tree)
                        try:
                            py_files.append((os.path.getmtime(fp), rel))
                        except OSError:
                            pass
    py_files.sort(reverse=True)
    for _, rel in py_files[:25]:
        if rel not in probe_rel_paths:
            probe_rel_paths.append(rel)

    if not probe_rel_paths:
        return None, "none"

    abs_probes = [os.path.join(norm_tree, r) for r in probe_rel_paths]
    probe_hashes = hash_files_batched(abs_probes)

    # 4. Collect candidate commits from:
    #    (a) hex tokens in tree_base and root basename
    #    (b) hex tokens in small evidence files (*.md, *.txt, *.json) in root_path
    #    (c) sentinel blob index matches across all commits
    explicit_reasons: dict[str, str] = {}
    name_tokens = re.findall(r"(?:^|[-_])([0-9a-f]{4,40})(?:$|[-_])", f"{os.path.basename(norm_root)}-{tree_base}".lower())
    for tok in name_tokens:
        for sha in git_index.resolve_prefix(tok):
            explicit_reasons.setdefault(sha, f"name_token:{tok}")

    try:
        for fn in sorted(os.listdir(norm_root)):
            if is_secret_filename(fn) or ".bak" in fn:
                continue
            if fn.endswith((".md", ".txt", ".json")):
                fp = os.path.join(norm_root, fn)
                if os.path.isfile(fp) and os.path.getsize(fp) < 256_000:
                    txt = Path(fp).read_text(errors="replace")
                    for tok in re.findall(r"\b([0-9a-f]{7,40})\b", txt.lower()):
                        for sha in git_index.resolve_prefix(tok):
                            explicit_reasons.setdefault(sha, f"evidence_file:{fn}({tok[:9]})")
    except OSError:
        pass

    sentinel_votes: dict[str, int] = {}
    for sp in SENTINEL_PATHS:
        ap = os.path.join(norm_tree, sp)
        bh = probe_hashes.get(ap)
        if bh:
            for sha in git_index.sentinel_index.get((sp, bh), set()):
                sentinel_votes[sha] = sentinel_votes.get(sha, 0) + 1

    # Top sentinel candidates + explicit candidates
    top_sentinel_shas = sorted(sentinel_votes.keys(), key=lambda s: (sentinel_votes[s], s in explicit_reasons, git_index.is_remote_reachable(s)), reverse=True)[:25]
    candidate_shas = list(dict.fromkeys(list(explicit_reasons.keys())[:40] + top_sentinel_shas))

    best_sha: str | None = None
    best_score = -1
    best_total = len(probe_rel_paths)
    for sha in candidate_shas:
        tree_map = git_index.get_ls_tree(sha)
        matches = 0
        for rel in probe_rel_paths:
            ap = os.path.join(norm_tree, rel)
            bh = probe_hashes.get(ap)
            if bh and rel in tree_map and tree_map[rel][0] == bh:
                matches += 1
        # Tie-break: prefer explicit reason, then remote reachable
        score_tuple = (matches, sha in explicit_reasons, git_index.is_remote_reachable(sha))
        best_tuple = (
            best_score,
            (best_sha in explicit_reasons) if best_sha else False,
            git_index.is_remote_reachable(best_sha) if best_sha else False,
        )
        if score_tuple > best_tuple:
            best_score = matches
            best_sha = sha

    if best_sha and best_total > 0 and (best_score / best_total) >= 0.85:
        reason = explicit_reasons.get(best_sha, "blob_agreement")
        return best_sha, f"{reason} ({best_score}/{best_total} probe blobs matched)"
    return None, "none"


def assess_root(
    root_path: str,
    all_roots_norm: set[str],
    git_index: GitIndex,
    live_procs: list[tuple[int, str, str, str]],
    citations_map: dict[str, dict[str, Any]],
    subpath_citations_map: dict[str, dict[str, list[str]]],
    lender_to_borrowers: dict[str, list[str]],
    root_to_alternates: dict[str, list[str]],
    now_ts: float,
) -> dict[str, Any]:
    """Assess a single root directory (or file) and return its ledger record."""
    wait_for_quiet_window()
    norm_root = os.path.normpath(root_path)
    base_name = os.path.basename(norm_root)
    rel_root = (
        "d4d-executions/" + norm_root[len(EXECUTIONS_ROOT) + 1 :]
        if norm_root.startswith(EXECUTIONS_ROOT + "/")
        else ("data-sheets-schema" + norm_root[len(PRIMARY_REPO) :] if norm_root.startswith(PRIMARY_REPO) else norm_root)
    )

    cite_info = citations_map.get(base_name, {"total_count": 0, "substantive_count": 0, "citing_files_up_to_5": []})
    tot_c = cite_info.get("total_count", 0)
    sub_c = cite_info.get("substantive_count", 0)
    top5_c = cite_info.get("citing_files_up_to_5", [])

    # Check if root is a single file directly under d4d-executions/
    if os.path.isfile(norm_root) or os.path.islink(norm_root):
        try:
            st = os.lstat(norm_root)
            sz = st.st_size
            mtime = st.st_mtime
        except OSError:
            sz = 0
            mtime = 0.0
        guards: list[str] = []
        if (now_ts - mtime) < 86400:
            guards.append("recent_24h_modified")
        is_sec = is_secret_filename(base_name)
        if guards:
            action = "KEEP"
        elif is_sec:
            action = "KEEP-SECRET-REVIEW"
        else:
            action = "COMPRESS-ARCHIVE"
        return {
            "root": norm_root,
            "rel_root": rel_root,
            "basename": base_name,
            "kind": "top_level_file",
            "total_bytes": sz,
            "total_files": 1,
            "classes": {
                "C": {
                    "files": 0,
                    "bytes": 0,
                    "files_under_4kb_bulk": 0,
                    "bytes_under_4kb_bulk": 0,
                    "basetemp_dirs": [],
                    "basetemp_dir_count": 0,
                    "cache_dir_count": 0,
                    "moved_to_u_cited_files": 0,
                    "moved_to_u_cited_bytes": 0,
                },
                "R": {
                    "files": 0,
                    "bytes": 0,
                    "files_under_4kb_bulk": 0,
                    "bytes_under_4kb_bulk": 0,
                    "from_archive_tags_files": 0,
                    "from_archive_tags_bytes": 0,
                    "git_status_unread_files": 0,
                    "git_status_unread_bytes": 0,
                    "git_status_unread_paths": [],
                    "sample_files": [],
                },
                "R_local": {
                    "files": 0,
                    "bytes": 0,
                    "files_under_4kb_bulk": 0,
                    "bytes_under_4kb_bulk": 0,
                    "git_status_unread_files": 0,
                    "git_status_unread_bytes": 0,
                    "local_commits_needed": [],
                },
                "V": {"files": 0, "bytes": 0, "venv_dirs": []},
                "U": {
                    "files": 0 if is_sec else 1,
                    "bytes": 0 if is_sec else sz,
                    "files_under_4kb_bulk": (0 if is_sec else (1 if sz < 4096 else 0)),
                    "bytes_under_4kb_bulk": (0 if is_sec else (sz if sz < 4096 else 0)),
                    "cited_from_c_files": 0,
                    "cited_from_c_bytes": 0,
                    "cited_subpaths_matched": [],
                    "git_archive_tars": [],
                    "sample_files": [] if is_sec else [{"path": base_name, "bytes": sz}],
                },
                "KEEP-SECRET": {
                    "files": 1 if is_sec else 0,
                    "bytes": sz if is_sec else 0,
                    "files_under_4kb_bulk": (1 if sz < 4096 else 0) if is_sec else 0,
                    "bytes_under_4kb_bulk": (sz if sz < 4096 else 0) if is_sec else 0,
                    "paths": [base_name] if is_sec else [],
                },
                "git_metadata": {
                    "files": 0,
                    "bytes": 0,
                    "paths": [],
                },
                "unclassified": {"files": 0, "bytes": 0, "items": []},
            },
            "source_commit": None,
            "source_commit_established_by": "none (single top-level file)",
            "repo_trees": [],
            "git_state": {
                "is_worktree": False,
                "is_registered_worktree": False,
                "is_git_dir": False,
                "head": None,
                "branch": None,
                "branch_ref": None,
                "points_at_refs": [],
                "branch_display": None,
                "branch_remote_reachable": False,
                "branch_kept": False,
                "porcelain_dirty_count": 0,
                "porcelain_untracked_count": 0,
                "remote_reachable": False,
                "remote_refs": [],
                "local_refs": [],
                "local_only_refs": [],
                "own_objects_count": 0,
                "git_dir_metadata_only": False,
                "git_dir_entries": [],
                "alternates": [],
                "alternates_borrowers": [],
                "stash_count": 0,
            },
            "live_process_check": {"has_live_process": False, "processes": []},
            "citations": {"total_count": tot_c, "substantive_count": sub_c, "citing_files_up_to_5": top5_c},
            "guards_fired": guards,
            "primary_action": action,
            "proposed_action": action,
            "class_actions": {
                "C": "NONE",
                "R": "NONE",
                "U": ("KEEP" if guards else ("NONE" if is_sec else "COMPRESS-ARCHIVE")),
                "KEEP-SECRET": ("KEEP" if guards else ("KEEP-SECRET-REVIEW" if is_sec else "NONE")),
                "V": "NONE",
                "R_local": "NONE",
            },
            "action_bytes": {
                "delete_safe_bytes": 0,
                "worktree_remove_bytes": 0,
                "gitdir_remove_bytes": 0,
                "compress_archive_bytes": 0 if (guards or is_sec) else sz,
                "keep_secret_review_bytes": 0 if guards else (sz if is_sec else 0),
                "keep_bytes": sz if guards else 0,
                "r_local_blocked_bytes": 0,
            },
            "exact_commands": (
                []
                if guards
                else (
                    [
                        f"python3 {PRIMARY_REPO}/scripts/adhoc/assess_cleanup_safety_20261107.py --roots {shlex.quote(norm_root)} --out /tmp/recheck_{base_name}",
                        f"# KEEP-SECRET-REVIEW (never archived or deleted; owner review required): {base_name}",
                    ]
                    if is_sec
                    else [
                        f"python3 {PRIMARY_REPO}/scripts/adhoc/assess_cleanup_safety_20261107.py --roots {shlex.quote(norm_root)} --out /tmp/recheck_{base_name}",
                        f"zstd -T0 -19 -k {shlex.quote(norm_root)} -o {shlex.quote(norm_root + '.u.zst')}",
                    ]
                )
            ),
        }

    # Directory root
    child_roots = {r for r in all_roots_norm if r != norm_root and r.startswith(norm_root + os.sep)}
    git_dot_path = os.path.join(norm_root, ".git")
    is_registered_wt = norm_root in git_index.worktree_info
    is_wt = is_registered_wt or os.path.exists(git_dot_path)
    is_git_dir = is_wt and not is_registered_wt and os.path.isdir(git_dot_path)
    ak_flag, ak_reason = is_always_keep_root(norm_root)

    # Pre-check git status and real HEAD for `.git` roots (Part 66b Correction to Fix 2 & Fix 4)
    real_git_head: str | None = None
    porcelain_dirty_cnt = 0
    porcelain_untracked_cnt = 0
    porcelain_paths: set[str] = set()
    porcelain_dir_prefixes: list[str] = []
    if is_wt:
        rev_proc = git_index._run_git(["rev-parse", "HEAD"], cwd=norm_root)
        h_out = rev_proc.stdout.strip()
        if len(h_out) == 40:
            real_git_head = h_out
        st_proc = git_index._run_git(["status", "--porcelain"], cwd=norm_root)
        for sline in st_proc.stdout.splitlines():
            if not sline or len(sline) < 4:
                continue
            status_code = sline[:2]
            raw_p = sline[3:].strip()
            if " -> " in raw_p:
                raw_p = raw_p.split(" -> ", 1)[1].strip()
            raw_p = raw_p.strip('"')
            if status_code == "??":
                porcelain_untracked_cnt += 1
            else:
                porcelain_dirty_cnt += 1
            norm_p = raw_p.rstrip("/")
            porcelain_paths.add(norm_p)
            if raw_p.endswith("/"):
                porcelain_dir_prefixes.append(norm_p + "/")

    def is_clean_in_porcelain(rel_p: str) -> bool:
        if rel_p in porcelain_paths:
            return False
        for pref in porcelain_dir_prefixes:
            if rel_p.startswith(pref):
                return False
        return True

    # Step 1: Discover unpacked repo trees inside `norm_root`
    repo_tree_dirs: dict[str, tuple[str, str]] = {}  # abs_tree_path -> (sha, established_by)
    if is_wt:
        if real_git_head:
            label = "git_worktree_HEAD" if is_registered_wt else "git_HEAD"
            repo_tree_dirs[norm_root] = (real_git_head, f"{label} ({real_git_head[:12]})")
    elif base_name not in ("plans", "evidence", "logs", "lineage-durable"):
        for dp, dns, fns in os.walk(norm_root):
            if dp in child_roots:
                dns[:] = []
                continue
            if is_pytest_basetemp_dir(dp, dns, fns):
                dns[:] = []
                continue
            dns[:] = [d for d in dns if d not in CACHE_DIR_NAMES and d not in VENV_DIR_NAMES and d != ".git"]
            rel = os.path.relpath(dp, norm_root)
            depth = 0 if rel == "." else len(rel.split(os.sep))
            if "pyproject.toml" in fns and os.path.isdir(os.path.join(dp, "src", "data_sheets_schema")):
                sha, how = establish_tree_commit(dp, norm_root, git_index)
                if sha:
                    repo_tree_dirs[dp] = (sha, how)
                dns[:] = []
                continue
            if depth >= 3:
                dns[:] = []

    # Step 2: Walk all files in `norm_root`, classifying C, V, git_metadata, KEEP-SECRET, R (git-status, unread), U, and R candidates
    c_files = 0
    c_bytes = 0
    c_under_4k_files = 0
    c_under_4k_bytes = 0
    basetemp_dirs: list[str] = []
    cache_top_dirs: list[str] = []
    basetemps_with_cited_u: set[str] = set()

    c_to_u_cited_files = 0
    c_to_u_cited_bytes = 0
    cited_subpaths_matched: set[str] = set()

    v_files = 0
    v_bytes = 0
    venv_dirs: list[str] = []

    u_files = 0
    u_bytes = 0
    u_under_4k_files = 0
    u_under_4k_bytes = 0
    u_samples: list[dict[str, Any]] = []
    git_archive_tars: list[dict[str, Any]] = []

    keep_secret_files = 0
    keep_secret_bytes = 0
    keep_secret_under_4k_files = 0
    keep_secret_under_4k_bytes = 0
    keep_secret_paths: list[str] = []

    r_git_status_unread_files = 0
    r_git_status_unread_bytes = 0
    r_git_status_unread_under_4k_files = 0
    r_git_status_unread_under_4k_bytes = 0
    r_git_status_unread_paths: list[str] = []

    r_local_git_status_unread_files = 0
    r_local_git_status_unread_bytes = 0
    r_local_git_status_unread_under_4k_files = 0
    r_local_git_status_unread_under_4k_bytes = 0

    git_meta_files = 0
    git_meta_bytes = 0
    git_meta_paths: list[str] = []

    unclassified_files = 0
    unclassified_bytes = 0
    unclassified_items: list[str] = []

    # Account for standalone `.git/` directory metadata files & own objects (Fix 4 & Fix 6)
    own_objects_count = 0
    git_dir_entries: list[str] = []
    if is_git_dir and os.path.isdir(git_dot_path):
        for entry_name in ("HEAD", "config", "index", "packed-refs", "ORIG_HEAD"):
            if os.path.exists(os.path.join(git_dot_path, entry_name)):
                git_dir_entries.append(entry_name)
        if os.path.exists(os.path.join(git_dot_path, "objects", "info", "alternates")):
            git_dir_entries.append("objects/info/alternates")
        git_meta_paths.append(".git/")
        for gdp, gdns, gfns in os.walk(git_dot_path):
            rel_gdp = os.path.relpath(gdp, git_dot_path)
            for gfn in gfns:
                gfp = os.path.join(gdp, gfn)
                try:
                    gsz = os.lstat(gfp).st_size
                except OSError:
                    gsz = 0
                git_meta_files += 1
                git_meta_bytes += gsz
                if rel_gdp.startswith("objects") and rel_gdp != "objects" and not rel_gdp.startswith(os.path.join("objects", "info")):
                    own_objects_count += 1

    root_subpath_cites = subpath_citations_map.get(base_name, {})

    r_candidates_by_tree: dict[str, list[tuple[str, str, str, int, str]]] = {t: [] for t in repo_tree_dirs}
    sorted_tree_roots = sorted(repo_tree_dirs.keys(), key=len, reverse=True)

    def find_owning_tree(dp: str) -> str | None:
        for tr in sorted_tree_roots:
            if dp == tr or dp.startswith(tr + os.sep):
                return tr
        return None

    def sum_dir_into_class(start_dir: str, cls_name: str, is_basetemp: bool = False) -> None:
        nonlocal c_files, c_bytes, c_under_4k_files, c_under_4k_bytes
        nonlocal u_files, u_bytes, u_under_4k_files, u_under_4k_bytes
        nonlocal c_to_u_cited_files, c_to_u_cited_bytes
        nonlocal v_files, v_bytes, unclassified_files, unclassified_bytes

        rel_bt = os.path.relpath(start_dir, norm_root)
        bt_exact_cited: list[str] = []
        bt_glob_cited: list[str] = []
        if cls_name == "C" and is_basetemp and root_subpath_cites:
            prefix = rel_bt + "/"
            for sp in root_subpath_cites:
                if sp.startswith(prefix):
                    if "*" in sp or "?" in sp:
                        bt_glob_cited.append(sp)
                    else:
                        bt_exact_cited.append(sp)

        def match_cited_in_bt(rel_fp: str) -> str | None:
            for ep in bt_exact_cited:
                if rel_fp == ep or rel_fp.startswith(ep + "/"):
                    return ep
            for gp in bt_glob_cited:
                if fnmatch.fnmatchcase(rel_fp, gp) or fnmatch.fnmatchcase(rel_fp, gp + "/*"):
                    return gp
            return None

        for sdp, sdns, sfns in os.walk(start_dir):
            if sdp in child_roots:
                sdns[:] = []
                continue
            for entry in sfns + [d for d in sdns if os.path.islink(os.path.join(sdp, d))]:
                fp = os.path.join(sdp, entry)
                rel_fp = os.path.relpath(fp, norm_root)
                try:
                    st = os.lstat(fp)
                    sz = st.st_size
                except OSError as exc:
                    unclassified_files += 1
                    if len(unclassified_items) < 10:
                        unclassified_items.append(f"{rel_fp}: {exc}")
                    continue
                if cls_name == "C":
                    matched_sp = match_cited_in_bt(rel_fp) if (bt_exact_cited or bt_glob_cited) else None
                    if matched_sp is not None:
                        u_files += 1
                        u_bytes += sz
                        if sz < 4096:
                            u_under_4k_files += 1
                            u_under_4k_bytes += sz
                        c_to_u_cited_files += 1
                        c_to_u_cited_bytes += sz
                        cited_subpaths_matched.add(matched_sp)
                        basetemps_with_cited_u.add(rel_bt)
                        if len(u_samples) < 40:
                            u_samples.append({"path": rel_fp, "bytes": sz, "note": f"U (cited:{matched_sp})", "_prio": 0})
                    else:
                        c_files += 1
                        c_bytes += sz
                        if sz < 4096:
                            c_under_4k_files += 1
                            c_under_4k_bytes += sz
                elif cls_name == "V":
                    v_files += 1
                    v_bytes += sz

    max_mtime = 0.0
    try:
        max_mtime = os.path.getmtime(norm_root)
    except OSError:
        pass

    for dp, dns, fns in os.walk(norm_root):
        if dp in child_roots:
            dns[:] = []
            continue

        rel_dp_root = os.path.relpath(dp, norm_root)
        if rel_dp_root != "." and len(rel_dp_root.split(os.sep)) == 1:
            try:
                mt = os.path.getmtime(dp)
                if mt > max_mtime:
                    max_mtime = mt
            except OSError:
                pass

        # Skip `.git` internal metadata directory (walked separately above for standalone git_dir)
        if ".git" in dns:
            dns.remove(".git")

        # Check if `dp` itself is a pytest basetemp directory
        if dp != norm_root and is_pytest_basetemp_dir(dp, dns, fns):
            basetemp_dirs.append(rel_dp_root)
            cache_top_dirs.append(rel_dp_root)
            sum_dir_into_class(dp, "C", is_basetemp=True)
            dns[:] = []
            continue

        # Partition child directories into C, V, or normal
        keep_dns: list[str] = []
        for d in dns:
            full_d = os.path.join(dp, d)
            if full_d in child_roots:
                continue
            rel_d = os.path.relpath(full_d, norm_root)
            if os.path.islink(full_d):
                try:
                    sz = os.lstat(full_d).st_size
                except OSError:
                    sz = 0
                if d.startswith("test_") and d.endswith("current"):
                    c_files += 1
                    c_bytes += sz
                elif is_secret_filename(d):
                    keep_secret_files += 1
                    keep_secret_bytes += sz
                    if sz < 4096:
                        keep_secret_under_4k_files += 1
                        keep_secret_under_4k_bytes += sz
                    keep_secret_paths.append(rel_d)
                else:
                    u_files += 1
                    u_bytes += sz
                continue
            if d in CACHE_DIR_NAMES or d.startswith("pytest-of-") or d.endswith("-pytest"):
                cache_top_dirs.append(rel_d)
                is_bt = d.startswith("pytest-of-") or d.endswith("-pytest")
                if is_bt:
                    basetemp_dirs.append(rel_d)
                sum_dir_into_class(full_d, "C", is_basetemp=is_bt)
            elif d in VENV_DIR_NAMES:
                venv_dirs.append(rel_d)
                sum_dir_into_class(full_d, "V", is_basetemp=False)
            else:
                keep_dns.append(d)
        dns[:] = keep_dns

        owning_tree = find_owning_tree(dp)
        ls_tree_map = (
            git_index.get_ls_tree(repo_tree_dirs[owning_tree][0], cwd=(norm_root if owning_tree == norm_root and is_wt else None))
            if owning_tree
            else None
        )

        for fn in fns:
            fp = os.path.join(dp, fn)
            rel_fp_root = fn if rel_dp_root == "." else os.path.join(rel_dp_root, fn)
            try:
                st = os.lstat(fp)
                sz = st.st_size
                if rel_dp_root == "." and st.st_mtime > max_mtime:
                    max_mtime = st.st_mtime
            except OSError as exc:
                unclassified_files += 1
                if len(unclassified_items) < 10:
                    unclassified_items.append(f"{rel_fp_root}: {exc}")
                continue

            # 0. Worktree `.git` pointer file is git metadata (Fix 2: never classify as U)
            if fn == ".git":
                git_meta_files += 1
                git_meta_bytes += sz
                git_meta_paths.append(rel_fp_root)
                continue

            # 1. Cache files (.DS_Store, *.pyc, *.pyo) — `__pycache__/*.pyc` stays C whatever its name
            if fn == ".DS_Store" or fn.endswith((".pyc", ".pyo")):
                c_files += 1
                c_bytes += sz
                if sz < 4096:
                    c_under_4k_files += 1
                    c_under_4k_bytes += sz
                continue

            # 2. Secret-matching filenames (Part 66b Correction to Fix 2):
            #    - NEVER read or hash.
            #    - If in a `.git` root (`is_wt` and `owning_tree == norm_root`), tracked in `ls_tree_map`,
            #      and has no `git status --porcelain` entry (`is_clean_in_porcelain(rel_fp_root)`):
            #      * if `real_git_head` is reachable on `origin`, classify as `R (git-status, unread)`;
            #      * otherwise classify as `R_local (git-status, unread)`.
            #    - Otherwise (untracked, ignored, modified, or in a root with no `.git`), classify as `KEEP-SECRET` (`KEEP-SECRET-REVIEW`).
            if is_secret_filename(fn):
                if (
                    is_wt
                    and owning_tree == norm_root
                    and real_git_head is not None
                    and ls_tree_map is not None
                    and rel_fp_root in ls_tree_map
                    and is_clean_in_porcelain(rel_fp_root)
                ):
                    if git_index.is_remote_reachable(real_git_head):
                        r_git_status_unread_files += 1
                        r_git_status_unread_bytes += sz
                        if sz < 4096:
                            r_git_status_unread_under_4k_files += 1
                            r_git_status_unread_under_4k_bytes += sz
                        r_git_status_unread_paths.append(rel_fp_root)
                    else:
                        r_local_git_status_unread_files += 1
                        r_local_git_status_unread_bytes += sz
                        if sz < 4096:
                            r_local_git_status_unread_under_4k_files += 1
                            r_local_git_status_unread_under_4k_bytes += sz
                else:
                    keep_secret_files += 1
                    keep_secret_bytes += sz
                    if sz < 4096:
                        keep_secret_under_4k_files += 1
                        keep_secret_under_4k_bytes += sz
                    keep_secret_paths.append(rel_fp_root)
                continue

            # 3. Symlinks
            if os.path.islink(fp):
                u_files += 1
                u_bytes += sz
                if sz < 4096:
                    u_under_4k_files += 1
                    u_under_4k_bytes += sz
                continue

            # 4. Inside an established repo tree: check if relative path & size match `git ls-tree`
            if owning_tree and ls_tree_map is not None:
                rel_fp_tree = os.path.relpath(fp, owning_tree)
                expected = ls_tree_map.get(rel_fp_tree)
                if expected is not None and (expected[1] < 0 or expected[1] == sz):
                    r_candidates_by_tree[owning_tree].append((fp, rel_fp_root, rel_fp_tree, sz, expected[0]))
                    continue

            # 5. Check if a `.tar` file has a git archive PAX header comment
            if fn.endswith(".tar") and sz > 0:
                try:
                    with tarfile.open(fp, "r") as tf:
                        comment_sha = tf.pax_headers.get("comment", "").strip()
                    if len(comment_sha) == 40 and comment_sha in git_index.all_commits:
                        git_archive_tars.append({
                            "path": rel_fp_root,
                            "bytes": sz,
                            "pax_commit": comment_sha,
                            "remote_reachable": git_index.is_remote_reachable(comment_sha),
                        })
                except Exception:
                    pass

            # 6. Otherwise U (unique)
            u_files += 1
            u_bytes += sz
            if sz < 4096:
                u_under_4k_files += 1
                u_under_4k_bytes += sz
            if len(u_samples) < 40:
                is_artifact = fn.endswith((".log", ".xml", ".json", ".jsonl", ".md", ".diff", ".tsv", ".csv", ".yaml")) or (
                    fn.endswith(".txt") and not fn.endswith("commit.txt")
                )
                u_samples.append({"path": rel_fp_root, "bytes": sz, "_prio": 0 if is_artifact else 1})

    # Step 3: Batch-hash all R candidates across all repo trees in this root in a single batched pass
    r_files = r_git_status_unread_files
    r_bytes = r_git_status_unread_bytes
    r_under_4k_files = r_git_status_unread_under_4k_files
    r_under_4k_bytes = r_git_status_unread_under_4k_bytes
    r_from_archive_tags_files = 0
    r_from_archive_tags_bytes = 0
    r_samples: list[dict[str, Any]] = []
    for sp_unread in sorted(r_git_status_unread_paths)[:4]:
        r_samples.append({
            "path": sp_unread,
            "tree_rel_path": sp_unread,
            "bytes": os.lstat(os.path.join(norm_root, sp_unread)).st_size if os.path.exists(os.path.join(norm_root, sp_unread)) else 0,
            "blob_sha1": "R (git-status, unread)",
            "ls_tree_sha1": "R (git-status, unread)",
            "commit": real_git_head,
        })

    r_local_files = r_local_git_status_unread_files
    r_local_bytes = r_local_git_status_unread_bytes
    r_local_under_4k_files = r_local_git_status_unread_under_4k_files
    r_local_under_4k_bytes = r_local_git_status_unread_under_4k_bytes
    local_commits_needed: list[str] = []

    repo_trees_summary: list[dict[str, Any]] = []

    all_abs_cands: list[str] = []
    for tr_path in sorted(repo_tree_dirs.keys()):
        for c in r_candidates_by_tree.get(tr_path, []):
            all_abs_cands.append(c[0])
    hashes_map = hash_files_batched(all_abs_cands, root_label=base_name) if all_abs_cands else {}

    for tr_path, (sha, how) in sorted(repo_tree_dirs.items()):
        cands = r_candidates_by_tree.get(tr_path, [])
        rel_tr = os.path.relpath(tr_path, norm_root)
        rem_ok = git_index.is_remote_reachable(sha)
        via_archive_tag = git_index.is_archive_tag_only_reachable(sha)
        if not rem_ok and sha not in local_commits_needed:
            local_commits_needed.append(sha)

        tr_matched_files = (r_git_status_unread_files if (tr_path == norm_root and rem_ok) else (r_local_git_status_unread_files if tr_path == norm_root else 0))
        tr_matched_bytes = (r_git_status_unread_bytes if (tr_path == norm_root and rem_ok) else (r_local_git_status_unread_bytes if tr_path == norm_root else 0))
        if tr_path == norm_root and rem_ok and via_archive_tag:
            r_from_archive_tags_files += r_git_status_unread_files
            r_from_archive_tags_bytes += r_git_status_unread_bytes

        tr_samples_by_cat: dict[str, dict[str, Any]] = {}
        for fp, rel_fp_root, rel_fp_tree, sz, exp_blob in cands:
            actual_blob = hashes_map.get(fp)
            if actual_blob == exp_blob:
                tr_matched_files += 1
                tr_matched_bytes += sz
                if rem_ok:
                    r_files += 1
                    r_bytes += sz
                    if sz < 4096:
                        r_under_4k_files += 1
                        r_under_4k_bytes += sz
                    if via_archive_tag:
                        r_from_archive_tags_files += 1
                        r_from_archive_tags_bytes += sz
                    cat = rel_fp_tree.split("/", 1)[0] if "/" in rel_fp_tree else "root"
                    if cat in ("src", "tests", "scripts", "data", "root") and cat not in tr_samples_by_cat:
                        tr_samples_by_cat[cat] = {
                            "path": rel_fp_root,
                            "tree_rel_path": rel_fp_tree,
                            "bytes": sz,
                            "blob_sha1": actual_blob,
                            "ls_tree_sha1": exp_blob,
                            "commit": sha,
                        }
                else:
                    r_local_files += 1
                    r_local_bytes += sz
                    if sz < 4096:
                        r_local_under_4k_files += 1
                        r_local_under_4k_bytes += sz
            else:
                # Modified file relative to source commit -> U (unique)
                u_files += 1
                u_bytes += sz
                if sz < 4096:
                    u_under_4k_files += 1
                    u_under_4k_bytes += sz
                if len(u_samples) < 40:
                    u_samples.append({"path": rel_fp_root, "bytes": sz, "note": f"modified_from_{sha[:9]}", "_prio": 0})

        for cat in ("src", "tests", "scripts", "data", "root"):
            if cat in tr_samples_by_cat and len(r_samples) < 25:
                r_samples.append(tr_samples_by_cat[cat])

        repo_trees_summary.append({
            "subpath": rel_tr,
            "source_commit": sha,
            "established_by": how,
            "remote_reachable": rem_ok,
            "reachable_via_archive_tag_only": via_archive_tag,
            "remote_refs": git_index.get_remote_refs(sha)[:5],
            "local_refs": git_index.get_local_refs(sha)[:5],
            "matched_files": tr_matched_files,
            "matched_bytes": tr_matched_bytes,
            "r_git_status_unread_files": r_git_status_unread_files if tr_path == norm_root else 0,
            "r_git_status_unread_bytes": r_git_status_unread_bytes if tr_path == norm_root else 0,
        })

    u_samples.sort(key=lambda x: (x.get("_prio", 1), x["path"]))
    for us in u_samples:
        us.pop("_prio", None)
    keep_secret_paths.sort()
    r_git_status_unread_paths.sort()
    git_meta_paths.sort()

    # Primary source commit for the root
    primary_sha: str | None = None
    primary_how = "none"
    if is_wt:
        primary_sha = real_git_head
        if real_git_head:
            primary_how = f"{'git_worktree_HEAD' if is_registered_wt else 'git_HEAD'} ({real_git_head[:12]})"
        else:
            primary_how = "git_HEAD_unresolved"
    elif repo_trees_summary:
        dot_trees = [t for t in repo_trees_summary if t["subpath"] == "."]
        chosen = dot_trees[0] if dot_trees else max(repo_trees_summary, key=lambda t: t["matched_bytes"])
        primary_sha = chosen["source_commit"]
        if len(repo_trees_summary) == 1:
            primary_how = chosen["established_by"]
        else:
            primary_how = f"{chosen['established_by']} (+{len(repo_trees_summary) - 1} sibling archive tree(s))"

    # Step 4: Git worktree / standalone git_dir state check (Part 66b Fixes 4, 5, 6)
    alt_targets = root_to_alternates.get(norm_root, [])
    alt_borrowers = lender_to_borrowers.get(norm_root, [])
    git_state: dict[str, Any] = {
        "is_worktree": is_wt,
        "is_registered_worktree": is_registered_wt,
        "is_git_dir": is_git_dir,
        "head": None,
        "branch": None,
        "branch_ref": None,
        "points_at_refs": [],
        "branch_display": None,
        "branch_remote_reachable": False,
        "branch_kept": False,
        "porcelain_dirty_count": 0,
        "porcelain_untracked_count": 0,
        "remote_reachable": False,
        "remote_refs": [],
        "local_refs": [],
        "local_only_refs": [],
        "own_objects_count": own_objects_count,
        "git_dir_metadata_only": (is_git_dir and own_objects_count == 0),
        "git_dir_entries": git_dir_entries,
        "alternates": alt_targets,
        "alternates_borrowers": alt_borrowers,
        "stash_count": 0,
    }
    if is_wt:
        wt_meta = git_index.worktree_info.get(norm_root, {})
        # Fix 4: ALWAYS use real_git_head (`git -C <root> rev-parse HEAD`); NEVER fall back to primary_sha or name tokens
        head_sha = real_git_head
        branch_ref = wt_meta.get("branch")
        if not branch_ref and is_git_dir:
            sym_proc = git_index._run_git(["symbolic-ref", "-q", "HEAD"], cwd=norm_root)
            if sym_proc.returncode == 0 and sym_proc.stdout.strip():
                branch_ref = sym_proc.stdout.strip()
        branch_short = (
            branch_ref[len("refs/heads/") :]
            if branch_ref and branch_ref.startswith("refs/heads/")
            else branch_ref
        )
        points_at = git_index.get_points_at_refs(head_sha) if head_sha else []
        if branch_short:
            branch_display = branch_short
        elif points_at:
            branch_display = f"detached (refs at HEAD: {', '.join(points_at[:5])})"
        else:
            branch_display = f"detached@{(head_sha or 'unresolved')[:12]}"

        git_state["head"] = head_sha
        git_state["branch"] = branch_short or "detached"
        git_state["branch_ref"] = branch_ref
        git_state["points_at_refs"] = points_at[:10]
        git_state["branch_display"] = branch_display
        git_state["branch_kept"] = bool(is_registered_wt)
        if head_sha:
            rem_reach = git_index.is_remote_reachable(head_sha)
            git_state["remote_reachable"] = rem_reach
            git_state["branch_remote_reachable"] = rem_reach
            git_state["remote_refs"] = git_index.get_remote_refs(head_sha)[:5]
            git_state["local_refs"] = git_index.get_local_refs(head_sha)[:5]
            if not rem_reach and head_sha not in local_commits_needed:
                local_commits_needed.append(head_sha)

        git_state["porcelain_dirty_count"] = porcelain_dirty_cnt
        git_state["porcelain_untracked_count"] = porcelain_untracked_cnt

        # Fix 4: Enumerate root's own refs (`for-each-ref` on standalone `.git` directories, checked-out branch on worktrees) + `refs/stash`
        local_only_refs: list[str] = []
        if is_git_dir:
            fer_proc = git_index._run_git(
                ["for-each-ref", "--format=%(objectname) %(deltabase) %(refname)"],
                cwd=norm_root,
            )
            for fline in fer_proc.stdout.splitlines():
                parts = fline.strip().split()
                if len(parts) < 2:
                    continue
                obj_sha = parts[0]
                ref_name = parts[-1]
                peel_sha = parts[1] if len(parts) == 3 and len(parts[1]) == 40 and parts[1] != "0" * 40 else obj_sha
                if not git_index.is_remote_reachable(peel_sha) and not git_index.is_remote_reachable(obj_sha):
                    local_only_refs.append(f"{ref_name}@{peel_sha[:12]}")
            stash_proc = git_index._run_git(["rev-parse", "--verify", "-q", "refs/stash"], cwd=norm_root)
            if stash_proc.returncode == 0 and stash_proc.stdout.strip():
                st_sha = stash_proc.stdout.strip()
                git_state["stash_count"] = 1
                if not git_index.is_remote_reachable(st_sha):
                    local_only_refs.append(f"refs/stash@{st_sha[:12]}")
        elif is_registered_wt and branch_ref:
            b_proc = git_index._run_git(["rev-parse", "--verify", "-q", branch_ref], cwd=norm_root)
            if b_proc.returncode == 0 and b_proc.stdout.strip():
                b_sha = b_proc.stdout.strip()
                if not git_index.is_remote_reachable(b_sha):
                    local_only_refs.append(f"{branch_ref}@{b_sha[:12]}")
        git_state["local_only_refs"] = local_only_refs

    # Step 5: Live-process check
    root_procs: list[dict[str, Any]] = []
    for pid, cmd, fd_type, lpath in live_procs:
        if lpath == norm_root or lpath.startswith(norm_root + os.sep):
            root_procs.append({"pid": pid, "command": cmd, "fd_type": fd_type, "path": lpath})

    # Step 7: Root guards (§2 of 2026-11-07-cleanup-safety-system.md + Part 66b Fixes 4 & 5)
    guards_fired: list[str] = []
    if ak_flag and ak_reason:
        guards_fired.append(ak_reason)
    if root_procs:
        guards_fired.append(f"live_process ({len(root_procs)} hit(s))")
    if is_wt:
        if git_state["porcelain_dirty_count"] > 0 or git_state["porcelain_untracked_count"] > 0:
            guards_fired.append(
                f"unique_git_state:dirty_or_untracked (dirty={git_state['porcelain_dirty_count']}, untracked={git_state['porcelain_untracked_count']})"
            )
        if not git_state["head"] or not git_state["remote_reachable"]:
            guards_fired.append(f"unique_git_state:local_only_head ({(git_state['head'] or 'unresolved')[:12]})")
        for lref in git_state["local_only_refs"]:
            guards_fired.append(f"unique_git_state:local_only_ref ({lref})")
        if is_git_dir and own_objects_count > 0:
            guards_fired.append(f"unique_git_state:own_objects ({own_objects_count})")
    if alt_borrowers and norm_root != PRIMARY_REPO:
        guards_fired.append(f"alternates_lender:{','.join(alt_borrowers)}")
    if local_commits_needed and not is_wt:
        guards_fired.append(f"r_local_unpushed_commits ({','.join(c[:9] for c in local_commits_needed)})")
    if (now_ts - max_mtime) < 86400 and primary_sha is None and not ak_flag:
        guards_fired.append("recent_24h_unestablished")

    total_bytes = (
        c_bytes
        + r_bytes
        + r_local_bytes
        + v_bytes
        + u_bytes
        + keep_secret_bytes
        + git_meta_bytes
        + unclassified_bytes
    )
    total_files = (
        c_files
        + r_files
        + r_local_files
        + v_files
        + u_files
        + keep_secret_files
        + git_meta_files
        + unclassified_files
    )

    # Step 8: Proposed action & action byte accounting (§4 + Part 66 Fix 1 + Part 66b Fixes 2, 4, 5, 6, 7)
    only_r_local_guard = (
        not is_wt
        and len(guards_fired) == 1
        and guards_fired[0].startswith("r_local_unpushed_commits")
        and bool(local_commits_needed)
        and all(c in git_index.all_commits for c in local_commits_needed)
    )

    if guards_fired:
        if only_r_local_guard:
            proposed_action = "PUSH-ARCHIVE-REF"
        else:
            proposed_action = "KEEP"
        primary_action = proposed_action
        delete_safe_bytes = 0
        worktree_remove_bytes = 0
        gitdir_remove_bytes = 0
        compress_archive_bytes = 0
        keep_secret_review_bytes = 0
        keep_bytes = total_bytes
        r_local_blocked_bytes = r_local_bytes + (c_bytes if only_r_local_guard else 0)
        class_actions = {
            "C": "KEEP",
            "R": "KEEP",
            "U": "KEEP",
            "KEEP-SECRET": "KEEP-SECRET-REVIEW" if keep_secret_files > 0 else "NONE",
            "V": "KEEP",
            "R_local": "PUSH-ARCHIVE-REF" if only_r_local_guard else "KEEP",
        }
    elif is_registered_wt:
        # Clean registered git worktree whose HEAD and branch commits are on origin (Part 66 Fix 1 & Part 66b Correction):
        # (a) archive U files (if any; excluding KEEP-SECRET-REVIEW),
        # (b) git -C <primary> worktree remove <path>,
        # (c) keep the branch.
        delete_safe_bytes = 0
        worktree_remove_bytes = c_bytes + r_bytes + git_meta_bytes
        gitdir_remove_bytes = 0
        compress_archive_bytes = u_bytes
        keep_secret_review_bytes = keep_secret_bytes
        keep_bytes = v_bytes + r_local_bytes + unclassified_bytes
        r_local_blocked_bytes = r_local_bytes

        primary_action = "WORKTREE-REMOVE"
        action_parts = ["WORKTREE-REMOVE"]
        if u_files > 0 or compress_archive_bytes > 0:
            action_parts.append("COMPRESS-ARCHIVE")
        if keep_secret_files > 0:
            action_parts.append("KEEP-SECRET-REVIEW")
        proposed_action = " + ".join(action_parts)
        class_actions = {
            "C": "WORKTREE-REMOVE",
            "R": "WORKTREE-REMOVE",
            "U": "COMPRESS-ARCHIVE" if u_files > 0 else "NONE",
            "KEEP-SECRET": "KEEP-SECRET-REVIEW" if keep_secret_files > 0 else "NONE",
            "V": "KEEP" if v_files > 0 else "NONE",
            "R_local": "NONE",
        }
    elif is_git_dir:
        # Clean standalone `.git` directory root that passed all guards (Part 66b Fix 6):
        # 1. archive U files (excluding KEEP-SECRET-REVIEW) and verify the archive by listing and hashing;
        # 2. remove the root as one exact path: `rm -rf -- '<root>'`
        delete_safe_bytes = 0
        worktree_remove_bytes = 0
        gitdir_remove_bytes = c_bytes + r_bytes + git_meta_bytes
        compress_archive_bytes = u_bytes
        keep_secret_review_bytes = keep_secret_bytes
        keep_bytes = v_bytes + r_local_bytes + unclassified_bytes
        r_local_blocked_bytes = r_local_bytes

        primary_action = "GITDIR-REMOVE"
        action_parts = ["GITDIR-REMOVE"]
        if u_files > 0 or compress_archive_bytes > 0:
            action_parts.append("COMPRESS-ARCHIVE")
        if keep_secret_files > 0:
            action_parts.append("KEEP-SECRET-REVIEW")
        proposed_action = " + ".join(action_parts)
        class_actions = {
            "C": "GITDIR-REMOVE",
            "R": "GITDIR-REMOVE",
            "U": "COMPRESS-ARCHIVE" if u_files > 0 else "NONE",
            "KEEP-SECRET": "KEEP-SECRET-REVIEW" if keep_secret_files > 0 else "NONE",
            "V": "KEEP" if v_files > 0 else "NONE",
            "R_local": "NONE",
        }
    else:
        # Unguarded non-worktree directory (e.g., scratch-* or exec_dir)
        delete_safe_bytes = c_bytes + r_bytes
        worktree_remove_bytes = 0
        gitdir_remove_bytes = 0
        compress_archive_bytes = u_bytes
        keep_secret_review_bytes = keep_secret_bytes
        keep_bytes = v_bytes + r_local_bytes + git_meta_bytes + unclassified_bytes
        r_local_blocked_bytes = r_local_bytes

        action_parts = []
        if delete_safe_bytes > 0:
            action_parts.append("DELETE-SAFE")
        if u_files > 0 or compress_archive_bytes > 0:
            action_parts.append("COMPRESS-ARCHIVE")
        if keep_secret_files > 0:
            action_parts.append("KEEP-SECRET-REVIEW")
        proposed_action = " + ".join(action_parts) if action_parts else "KEEP"
        primary_action = action_parts[0] if action_parts else "KEEP"
        class_actions = {
            "C": "DELETE-SAFE" if c_files > 0 else "NONE",
            "R": "DELETE-SAFE" if r_files > 0 else "NONE",
            "U": "COMPRESS-ARCHIVE" if u_files > 0 else "NONE",
            "KEEP-SECRET": "KEEP-SECRET-REVIEW" if keep_secret_files > 0 else "NONE",
            "V": "KEEP" if v_files > 0 else "NONE",
            "R_local": "KEEP" if r_local_files > 0 else "NONE",
        }

    # Exact commands (never executed by this read-only tool; generated for review)
    exact_commands: list[str] = []
    recheck_cmd = (
        f"python3 {PRIMARY_REPO}/scripts/adhoc/assess_cleanup_safety_20261107.py "
        f"--roots {shlex.quote(norm_root)} --out /tmp/recheck_{base_name}"
    )
    if proposed_action == "PUSH-ARCHIVE-REF":
        exact_commands.append(recheck_cmd)
        for lsha in local_commits_needed:
            tag_name = f"archive/{base_name}-{lsha[:12]}"
            exact_commands.append(f"git -C {PRIMARY_REPO} push origin {lsha}:refs/tags/{tag_name}")
    elif not guards_fired and is_registered_wt:
        exact_commands.append(recheck_cmd)
        if keep_secret_files > 0:
            exact_commands.append(
                f"# KEEP-SECRET-REVIEW ({keep_secret_files} file(s), {fmt_bytes(keep_secret_bytes)} — never archived or deleted; "
                f"owner review required before worktree removal; paths only): {', '.join(keep_secret_paths)}"
            )
        if u_files > 0:
            archive_path = f"{norm_root}.u.tar.zst"
            manifest_path = f"{norm_root}.u.manifest.json"
            exact_commands.append(
                f"# (a) Archive {u_files} U file(s) ({fmt_bytes(u_bytes)}; excluding KEEP-SECRET-REVIEW and .git metadata) "
                f"with sha256 manifest to {archive_path} and {manifest_path}"
            )
        else:
            exact_commands.append(
                f"# (a) Archive U files: none (0 U files; {r_git_status_unread_files} tracked secret-named file(s) are R (git-status, unread))"
            )
        exact_commands.append(
            f"git -C {PRIMARY_REPO} worktree remove {shlex.quote(norm_root)}"
        )
        exact_commands.append(
            f"# (c) KEEP BRANCH: {git_state['branch_display']} (branch_kept=true; do NOT delete branch)"
        )
    elif not guards_fired and is_git_dir:
        exact_commands.append(recheck_cmd)
        if keep_secret_files > 0:
            exact_commands.append(
                f"# KEEP-SECRET-REVIEW ({keep_secret_files} file(s), {fmt_bytes(keep_secret_bytes)} — never archived or deleted; "
                f"owner review required before GITDIR-REMOVE; paths only): {', '.join(keep_secret_paths)}"
            )
        if u_files > 0:
            archive_path = f"{norm_root}.u.tar.zst"
            manifest_path = f"{norm_root}.u.manifest.json"
            exact_commands.append(
                f"# (1) Archive {u_files} U file(s) ({fmt_bytes(u_bytes)}; excluding KEEP-SECRET-REVIEW) "
                f"to {archive_path} and verify archive by listing and sha256 manifest {manifest_path}"
            )
        else:
            exact_commands.append(
                f"# (1) Archive U files: none (0 U files; .git holds metadata only: {', '.join(git_dir_entries)}; "
                f"real HEAD={(real_git_head or '')[:12]})"
            )
        exact_commands.append(f"rm -rf -- '{norm_root}'")
    elif not guards_fired and proposed_action != "KEEP":
        exact_commands.append(recheck_cmd)
        if keep_secret_files > 0:
            exact_commands.append(
                f"# KEEP-SECRET-REVIEW ({keep_secret_files} file(s), {fmt_bytes(keep_secret_bytes)} — never archived or deleted; "
                f"owner review required; paths only): {', '.join(keep_secret_paths)}"
            )
        if u_files > 0:
            archive_path = f"{norm_root}.u.tar.zst"
            manifest_path = f"{norm_root}.u.manifest.json"
            cited_note = (
                f", including {c_to_u_cited_files} U (cited) basetemp file(s) ({fmt_bytes(c_to_u_cited_bytes)})"
                if c_to_u_cited_files > 0
                else ""
            )
            exact_commands.append(
                f"# Archive {u_files} U file(s) ({fmt_bytes(u_bytes)}{cited_note}; excluding KEEP-SECRET-REVIEW) "
                f"with sha256 manifest to {archive_path} and {manifest_path} before any C/R removal"
            )
        if delete_safe_bytes > 0:
            for cdir in sorted(cache_top_dirs)[:20]:
                if cdir in basetemps_with_cited_u:
                    exact_commands.append(
                        f"# Note: {os.path.join(norm_root, cdir)} contains U (cited) sub-paths — remove only after verifying U archive or preserve cited sub-paths"
                    )
                else:
                    exact_commands.append(f"rm -rf -- {shlex.quote(os.path.join(norm_root, cdir))}")
            for tr in repo_trees_summary:
                if tr["remote_reachable"] and tr["matched_files"] > 0:
                    tr_abs = norm_root if tr["subpath"] == "." else os.path.join(norm_root, tr["subpath"])
                    exact_commands.append(
                        f"# Remove {tr['matched_files']} verified R blob file(s) ({fmt_bytes(tr['matched_bytes'])}; excluding KEEP-SECRET-REVIEW) "
                        f"in {tr_abs} matching commit {tr['source_commit'][:12]}"
                    )

    return {
        "root": norm_root,
        "rel_root": rel_root,
        "basename": base_name,
        "kind": "registered_worktree" if is_registered_wt else ("git_dir" if is_wt else ("scratch" if base_name.startswith("scratch-") else "exec_dir")),
        "total_bytes": total_bytes,
        "total_files": total_files,
        "classes": {
            "C": {
                "files": c_files,
                "bytes": c_bytes,
                "files_under_4kb_bulk": c_under_4k_files,
                "bytes_under_4kb_bulk": c_under_4k_bytes,
                "basetemp_dirs": basetemp_dirs[:25],
                "basetemp_dir_count": len(basetemp_dirs),
                "cache_dir_count": len(cache_top_dirs),
                "moved_to_u_cited_files": c_to_u_cited_files,
                "moved_to_u_cited_bytes": c_to_u_cited_bytes,
            },
            "R": {
                "files": r_files,
                "bytes": r_bytes,
                "files_under_4kb_bulk": r_under_4k_files,
                "bytes_under_4kb_bulk": r_under_4k_bytes,
                "from_archive_tags_files": r_from_archive_tags_files,
                "from_archive_tags_bytes": r_from_archive_tags_bytes,
                "git_status_unread_files": r_git_status_unread_files,
                "git_status_unread_bytes": r_git_status_unread_bytes,
                "git_status_unread_paths": r_git_status_unread_paths,
                "sample_files": r_samples[:10],
            },
            "R_local": {
                "files": r_local_files,
                "bytes": r_local_bytes,
                "files_under_4kb_bulk": r_local_under_4k_files,
                "bytes_under_4kb_bulk": r_local_under_4k_bytes,
                "git_status_unread_files": r_local_git_status_unread_files,
                "git_status_unread_bytes": r_local_git_status_unread_bytes,
                "local_commits_needed": local_commits_needed,
            },
            "V": {
                "files": v_files,
                "bytes": v_bytes,
                "venv_dirs": venv_dirs,
            },
            "U": {
                "files": u_files,
                "bytes": u_bytes,
                "files_under_4kb_bulk": u_under_4k_files,
                "bytes_under_4kb_bulk": u_under_4k_bytes,
                "cited_from_c_files": c_to_u_cited_files,
                "cited_from_c_bytes": c_to_u_cited_bytes,
                "cited_subpaths_matched": sorted(cited_subpaths_matched)[:25],
                "git_archive_tars": git_archive_tars,
                "sample_files": u_samples[:10],
            },
            "KEEP-SECRET": {
                "files": keep_secret_files,
                "bytes": keep_secret_bytes,
                "files_under_4kb_bulk": keep_secret_under_4k_files,
                "bytes_under_4kb_bulk": keep_secret_under_4k_bytes,
                "paths": keep_secret_paths,
            },
            "git_metadata": {
                "files": git_meta_files,
                "bytes": git_meta_bytes,
                "paths": git_meta_paths,
            },
            "unclassified": {
                "files": unclassified_files,
                "bytes": unclassified_bytes,
                "items": unclassified_items,
            },
        },
        "source_commit": primary_sha,
        "source_commit_established_by": primary_how,
        "repo_trees": repo_trees_summary,
        "git_state": git_state,
        "live_process_check": {
            "has_live_process": bool(root_procs),
            "processes": root_procs[:10],
        },
        "citations": {
            "total_count": tot_c,
            "substantive_count": sub_c,
            "citing_files_up_to_5": top5_c,
        },
        "guards_fired": guards_fired,
        "primary_action": primary_action,
        "proposed_action": proposed_action,
        "class_actions": class_actions,
        "action_bytes": {
            "delete_safe_bytes": delete_safe_bytes,
            "worktree_remove_bytes": worktree_remove_bytes,
            "gitdir_remove_bytes": gitdir_remove_bytes,
            "compress_archive_bytes": compress_archive_bytes,
            "keep_secret_review_bytes": keep_secret_review_bytes,
            "keep_bytes": keep_bytes,
            "r_local_blocked_bytes": r_local_blocked_bytes,
        },
        "exact_commands": exact_commands,
    }


def write_outputs(records: list[dict[str, Any]], out_dir: str, remote: str) -> dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    records_sorted = sorted(records, key=lambda r: r["rel_root"])

    tot_bytes = sum(r["total_bytes"] for r in records_sorted)
    tot_files = sum(r["total_files"] for r in records_sorted)
    del_safe_bytes = sum(r["action_bytes"]["delete_safe_bytes"] for r in records_sorted)
    wt_remove_bytes = sum(r["action_bytes"]["worktree_remove_bytes"] for r in records_sorted)
    gd_remove_bytes = sum(r["action_bytes"]["gitdir_remove_bytes"] for r in records_sorted)
    comp_arch_bytes = sum(r["action_bytes"]["compress_archive_bytes"] for r in records_sorted)
    keep_sec_rev_bytes = sum(r["action_bytes"]["keep_secret_review_bytes"] for r in records_sorted)
    keep_bytes = sum(r["action_bytes"]["keep_bytes"] for r in records_sorted)
    r_local_blocked_bytes = sum(r["action_bytes"]["r_local_blocked_bytes"] for r in records_sorted)

    c_to_u_cited_files = sum(r["classes"]["C"]["moved_to_u_cited_files"] for r in records_sorted)
    c_to_u_cited_bytes = sum(r["classes"]["C"]["moved_to_u_cited_bytes"] for r in records_sorted)
    c_to_u_cited_roots = [
        {
            "rel_root": r["rel_root"],
            "kind": r["kind"],
            "files_moved": r["classes"]["C"]["moved_to_u_cited_files"],
            "bytes_moved": r["classes"]["C"]["moved_to_u_cited_bytes"],
            "cited_subpaths_matched": r["classes"]["U"]["cited_subpaths_matched"],
            "proposed_action": r["proposed_action"],
        }
        for r in records_sorted
        if r["classes"]["C"]["moved_to_u_cited_bytes"] > 0 or r["classes"]["C"]["moved_to_u_cited_files"] > 0
    ]

    r_git_status_unread_files = sum(r["classes"]["R"]["git_status_unread_files"] for r in records_sorted)
    r_git_status_unread_bytes = sum(r["classes"]["R"]["git_status_unread_bytes"] for r in records_sorted)

    r_from_archive_tags_files = sum(r["classes"]["R"]["from_archive_tags_files"] for r in records_sorted)
    r_from_archive_tags_bytes = sum(r["classes"]["R"]["from_archive_tags_bytes"] for r in records_sorted)
    archive_tag_converted_roots = [
        {
            "rel_root": r["rel_root"],
            "kind": r["kind"],
            "source_commit": r["source_commit"],
            "remote_refs": r["git_state"]["remote_refs"] if r["git_state"]["remote_refs"] else (r["repo_trees"][0]["remote_refs"] if r["repo_trees"] else []),
            "r_files_converted": r["classes"]["R"]["from_archive_tags_files"],
            "r_bytes_converted": r["classes"]["R"]["from_archive_tags_bytes"],
            "proposed_action": r["proposed_action"],
            "safe_bytes": r["action_bytes"]["delete_safe_bytes"] + r["action_bytes"]["worktree_remove_bytes"] + r["action_bytes"]["gitdir_remove_bytes"],
        }
        for r in records_sorted
        if r["classes"]["R"]["from_archive_tags_bytes"] > 0
    ]

    new_guard_catches = {
        "local_only_head": [
            {"rel_root": r["rel_root"], "kind": r["kind"], "head": r["git_state"]["head"], "guards": r["guards_fired"], "total_bytes": r["total_bytes"]}
            for r in records_sorted
            if any(g.startswith("unique_git_state:local_only_head") for g in r["guards_fired"])
        ],
        "local_only_ref": [
            {"rel_root": r["rel_root"], "kind": r["kind"], "local_only_refs": r["git_state"]["local_only_refs"], "guards": r["guards_fired"], "total_bytes": r["total_bytes"]}
            for r in records_sorted
            if any(g.startswith("unique_git_state:local_only_ref") for g in r["guards_fired"])
        ],
        "own_objects": [
            {"rel_root": r["rel_root"], "kind": r["kind"], "own_objects_count": r["git_state"]["own_objects_count"], "guards": r["guards_fired"], "total_bytes": r["total_bytes"]}
            for r in records_sorted
            if any(g.startswith("unique_git_state:own_objects") for g in r["guards_fired"])
        ],
        "alternates_lender": [
            {"rel_root": r["rel_root"], "kind": r["kind"], "borrowers": r["git_state"]["alternates_borrowers"], "guards": r["guards_fired"], "total_bytes": r["total_bytes"]}
            for r in records_sorted
            if any(g.startswith("alternates_lender:") for g in r["guards_fired"])
        ],
    }

    cls_totals: dict[str, dict[str, int]] = {}
    for cname in ("C", "R", "R_local", "V", "U", "KEEP-SECRET", "git_metadata", "unclassified"):
        cls_totals[cname] = {
            "files": sum(r["classes"][cname]["files"] for r in records_sorted),
            "bytes": sum(r["classes"][cname]["bytes"] for r in records_sorted),
        }

    action_counts: dict[str, int] = {}
    primary_action_counts: dict[str, int] = {}
    for r in records_sorted:
        act = r["proposed_action"]
        action_counts[act] = action_counts.get(act, 0) + 1
        pact = r["primary_action"]
        primary_action_counts[pact] = primary_action_counts.get(pact, 0) + 1

    r_local_roots = [
        r for r in records_sorted
        if r["classes"]["R_local"]["bytes"] > 0 or (r["git_state"]["is_worktree"] and not r["git_state"]["remote_reachable"])
    ]
    top10_safe_actions = sorted(
        [
            r for r in records_sorted
            if (r["action_bytes"]["delete_safe_bytes"] + r["action_bytes"]["worktree_remove_bytes"] + r["action_bytes"]["gitdir_remove_bytes"]) > 0
        ],
        key=lambda r: r["action_bytes"]["delete_safe_bytes"] + r["action_bytes"]["worktree_remove_bytes"] + r["action_bytes"]["gitdir_remove_bytes"],
        reverse=True,
    )[:10]

    safe_tot_bytes = del_safe_bytes + wt_remove_bytes + gd_remove_bytes
    summary_meta = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "remote": remote,
        "root_count": len(records_sorted),
        "total_files": tot_files,
        "total_bytes": tot_bytes,
        "action_byte_totals": {
            "DELETE-SAFE": del_safe_bytes,
            "WORKTREE-REMOVE": wt_remove_bytes,
            "GITDIR-REMOVE": gd_remove_bytes,
            "SAFE-TOTAL": safe_tot_bytes,
            "COMPRESS-ARCHIVE": comp_arch_bytes,
            "KEEP-SECRET-REVIEW": keep_sec_rev_bytes,
            "KEEP": keep_bytes,
            "R_local_blocked_bytes": r_local_blocked_bytes,
        },
        "r_local_to_r_via_archive_tags": {
            "files": r_from_archive_tags_files,
            "bytes": r_from_archive_tags_bytes,
            "root_count": len(archive_tag_converted_roots),
            "roots": archive_tag_converted_roots,
        },
        "c_to_u_cited": {
            "files": c_to_u_cited_files,
            "bytes": c_to_u_cited_bytes,
            "root_count": len(c_to_u_cited_roots),
            "roots": c_to_u_cited_roots,
        },
        "r_git_status_unread": {
            "files": r_git_status_unread_files,
            "bytes": r_git_status_unread_bytes,
        },
        "new_guard_catches": new_guard_catches,
        "action_root_counts": action_counts,
        "primary_action_root_counts": primary_action_counts,
        "class_totals": cls_totals,
    }

    # 1. Write ledger.json
    ledger_payload = {
        "summary": summary_meta,
        "roots": records_sorted,
    }
    ledger_json_path = os.path.join(out_dir, "ledger.json")
    with open(ledger_json_path, "w") as f:
        json.dump(ledger_payload, f, indent=2)

    # 2. Write summary.md
    md_lines: list[str] = [
        "# Read-Only Cleanup Safety Assessment (Run 2 — Part 66 & Part 66b Fixes) — 2026-11-07",
        "",
        f"- **Generated**: `{summary_meta['generated_at']}`",
        f"- **Rules specification**: `notes/coordination/2026-11-07-cleanup-safety-system.md` + `2026-11-07-agy-prompt-part66.md` + `2026-11-07-agy-prompt-part66b.md`",
        f"- **Assessor script**: `data-sheets-schema/scripts/adhoc/assess_cleanup_safety_20261107.py`",
        f"- **Remote checked**: `{remote}` (`origin/main` = `cf50d9a1c059f3b5030103378ccef33619475dde`, M8 + 15 D96 `refs/tags/archive/*` tags)",
        f"- **Total roots assessed**: `{len(records_sorted)}` (`{tot_files:,}` files, `{fmt_bytes(tot_bytes)}` / `{tot_bytes:,} B`)",
        "- **Mode**: **Read-only.** Nothing was deleted, moved, or compressed.",
        "",
        "## 1. Totals per Action (Unguarded vs Guarded Byte Accounting)",
        "",
        "| Action Bucket | Bytes | Human Size | Share of Total | Description |",
        "|---|---:|---:|---:|---|",
        f"| **DELETE-SAFE** (`C + R` on unguarded non-git roots) | `{del_safe_bytes:,}` | **{fmt_bytes(del_safe_bytes)}** | {(del_safe_bytes / tot_bytes * 100) if tot_bytes else 0:.2f}% | Exact cache (`C`) + remote-reachable git blob (`R`) bytes in non-git roots |",
        f"| **WORKTREE-REMOVE** (`C + R + git_metadata` on clean `origin`-reachable registered worktrees) | `{wt_remove_bytes:,}` | **{fmt_bytes(wt_remove_bytes)}** | {(wt_remove_bytes / tot_bytes * 100) if tot_bytes else 0:.2f}% | Removed via `git -C <primary> worktree remove <path>` (keeping the branch) after archiving `U` |",
        f"| **GITDIR-REMOVE** (`C + R + git_metadata` on clean `origin`-reachable standalone `git_dir` roots) | `{gd_remove_bytes:,}` | **{fmt_bytes(gd_remove_bytes)}** | {(gd_remove_bytes / tot_bytes * 100) if tot_bytes else 0:.2f}% | Removed via exact `rm -rf -- '<root>'` after archiving `U` (metadata-only `.git`, 0 own objects, not alternates lender) |",
        f"| **Combined Safe Removal** (`DELETE-SAFE + WORKTREE-REMOVE + GITDIR-REMOVE`) | `{safe_tot_bytes:,}` | **{fmt_bytes(safe_tot_bytes)}** | {(safe_tot_bytes / tot_bytes * 100) if tot_bytes else 0:.2f}% | Total verified reconstructible/cache bytes across unguarded roots, worktrees, and standalone git roots |",
        f"| **COMPRESS-ARCHIVE** (`U` on unguarded roots, including `U (cited)` and excluding `KEEP-SECRET-REVIEW`) | `{comp_arch_bytes:,}` | **{fmt_bytes(comp_arch_bytes)}** | {(comp_arch_bytes / tot_bytes * 100) if tot_bytes else 0:.2f}% | Unique (`U`) bytes to archive into `<root>.u.tar.zst` with `manifest.json` |",
        f"| **KEEP-SECRET-REVIEW** (`KEEP-SECRET` on unguarded roots) | `{keep_sec_rev_bytes:,}` | **{fmt_bytes(keep_sec_rev_bytes)}** | {(keep_sec_rev_bytes / tot_bytes * 100) if tot_bytes else 0:.4f}% | Untracked/ignored/modified or non-`.git` secret-named files (never read, archived, or deleted; owner review required) |",
        f"| **KEEP** (guarded roots + `V` / `R-local`) | `{keep_bytes:,}` | **{fmt_bytes(keep_bytes)}** | {(keep_bytes / tot_bytes * 100) if tot_bytes else 0:.2f}% | Protected by root guards (`always_keep`, `live_process`, `unique_git_state`, `alternates_lender`) or `V`/`R-local` |",
        f"| **TOTAL** | **`{tot_bytes:,}`** | **{fmt_bytes(tot_bytes)}** | **100.00%** | Across `{len(records_sorted)}` roots (`{tot_files:,}` files) |",
        "",
        f"- **Tracked clean secret-named files classified as `R (git-status, unread)`**: **`{fmt_bytes(r_git_status_unread_bytes)}`** (`{r_git_status_unread_bytes:,} B`, `{r_git_status_unread_files:,}` files).",
        f"- **Cited basetemp sub-paths moved from `C` to `U (cited)`**: **`{fmt_bytes(c_to_u_cited_bytes)}`** (`{c_to_u_cited_bytes:,} B`, `{c_to_u_cited_files:,}` files across `{len(c_to_u_cited_roots)}` roots).",
        f"- **`R-local` converted to `R` by the 15 D96 `refs/tags/archive/*` tags on `origin`**: **`{fmt_bytes(r_from_archive_tags_bytes)}`** (`{r_from_archive_tags_bytes:,} B`, `{r_from_archive_tags_files:,}` files across `{len(archive_tag_converted_roots)}` roots).",
        f"- **Remaining `R-local` bytes convertible after `PUSH-ARCHIVE-REF`**: **`{fmt_bytes(r_local_blocked_bytes)}`** (`{r_local_blocked_bytes:,} B`).",
        "",
        "### Root Counts by Proposed Action Combination",
        "",
        "| Proposed Action | Root Count |",
        "|---|---:|",
    ]
    for act, cnt in sorted(action_counts.items()):
        md_lines.append(f"| `{act}` | `{cnt}` |")

    md_lines.extend([
        "",
        "## 2. Totals per File Class (Across All Roots, Including Guarded Roots)",
        "",
        "| File Class | File Count | Bytes | Human Size | Rule |",
        "|---|---:|---:|---:|---|",
        f"| **C (cache)** | `{cls_totals['C']['files']:,}` | `{cls_totals['C']['bytes']:,}` | **{fmt_bytes(cls_totals['C']['bytes'])}** | `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, un-cited pytest basetemps, `.DS_Store` |",
        f"| **R (reconstructible)** | `{cls_totals['R']['files']:,}` | `{cls_totals['R']['bytes']:,}` | **{fmt_bytes(cls_totals['R']['bytes'])}** | `git hash-object` == `git ls-tree -r <sha>` (plus `R (git-status, unread)` for tracked clean secret-named files) on `{remote}` |",
        f"| **R-local (local commit)** | `{cls_totals['R_local']['files']:,}` | `{cls_totals['R_local']['bytes']:,}` | **{fmt_bytes(cls_totals['R_local']['bytes'])}** | Matches `git ls-tree -r <sha>`, but `<sha>` is reachable only from unpushed local refs |",
        f"| **V (environment)** | `{cls_totals['V']['files']:,}` | `{cls_totals['V']['bytes']:,}` | **{fmt_bytes(cls_totals['V']['bytes'])}** | `.venv/`, `node_modules/`, `.tox/`, `.nox/` |",
        f"| **U (unique + cited)** | `{cls_totals['U']['files']:,}` | `{cls_totals['U']['bytes']:,}` | **{fmt_bytes(cls_totals['U']['bytes'])}** | Logs, JUnit XML, JSON results, reports, tarballs, modified/untracked files, plus `U (cited)` basetemp sub-paths |",
        f"| **KEEP-SECRET** | `{cls_totals['KEEP-SECRET']['files']:,}` | `{cls_totals['KEEP-SECRET']['bytes']:,}` | **{fmt_bytes(cls_totals['KEEP-SECRET']['bytes'])}** | Untracked/ignored/modified or non-`.git` secret-named files — never read, archived, or deleted |",
        f"| **git_metadata** | `{cls_totals['git_metadata']['files']:,}` | `{cls_totals['git_metadata']['bytes']:,}` | **{fmt_bytes(cls_totals['git_metadata']['bytes'])}** | Worktree `.git` pointer file or standalone `.git/` directory metadata |",
        f"| **Unclassified** | `{cls_totals['unclassified']['files']:,}` | `{cls_totals['unclassified']['bytes']:,}` | **{fmt_bytes(cls_totals['unclassified']['bytes'])}** | Unreadable stat / special entries |",
        "",
        "## 3. Roots Caught by New Part 66b Guards",
        "",
        "### 3a. `unique_git_state:local_only_head` (Fix 4: Real HEAD via `git -C <root> rev-parse HEAD`)",
        "",
        "| Root | Kind | Real HEAD | Total Size | Guards Fired |",
        "|---|---|---|---:|---|",
    ])
    for item in new_guard_catches["local_only_head"]:
        md_lines.append(
            f"| `{item['rel_root']}` | {item['kind']} | `{(item['head'] or 'unresolved')[:12]}` | {fmt_bytes(item['total_bytes'])} | `{'; '.join(item['guards'])}` |"
        )

    md_lines.extend([
        "",
        "### 3b. `unique_git_state:own_objects` (Fix 4: Standalone `.git/objects` Holding Loose Objects or Packs)",
        "",
        "| Root | Kind | Own Objects Count | Total Size | Guards Fired |",
        "|---|---|---:|---:|---|",
    ])
    for item in new_guard_catches["own_objects"]:
        md_lines.append(
            f"| `{item['rel_root']}` | {item['kind']} | `{item['own_objects_count']}` | {fmt_bytes(item['total_bytes'])} | `{'; '.join(item['guards'])}` |"
        )

    md_lines.extend([
        "",
        "### 3c. `alternates_lender:<borrower>` (Fix 5: Roots Borrowed from via `.git/objects/info/alternates`)",
        "",
        "| Lender Root | Kind | Borrower Basename(s) | Total Size | Guards Fired |",
        "|---|---|---|---:|---|",
    ])
    for item in new_guard_catches["alternates_lender"]:
        md_lines.append(
            f"| `{item['rel_root']}` | {item['kind']} | `{', '.join(item['borrowers'])}` | {fmt_bytes(item['total_bytes'])} | `{'; '.join(item['guards'])}` |"
        )

    md_lines.extend([
        "",
        "### 3d. Cited Basetemp Sub-Paths Moved from `C` to `U (cited)` (Fix 7)",
        "",
        "| Root | Kind | `C -> U (cited)` Files | `C -> U (cited)` Bytes | Sample Cited Sub-Paths Matched | Proposed Action |",
        "|---|---|---:|---:|---|---|",
    ])
    for cr in c_to_u_cited_roots:
        sp_preview = ", ".join(f"`{s}`" for s in cr["cited_subpaths_matched"][:3])
        md_lines.append(
            f"| `{cr['rel_root']}` | {cr['kind']} | `{cr['files_moved']:,}` | **{fmt_bytes(cr['bytes_moved'])}** (`{cr['bytes_moved']:,} B`) | {sp_preview} | `{cr['proposed_action']}` |"
        )

    md_lines.extend([
        "",
        "## 4. `R-local` Converted to `R` After D96 `refs/tags/archive/*` Tags (Part 66 Fix 3)",
        "",
        "| Root | Kind | Source Commit | Remote Archive Tag | `R` Files Converted | `R` Bytes Converted | New Proposed Action |",
        "|---|---|---|---|---:|---:|---|",
    ])
    for cr in archive_tag_converted_roots:
        rrefs = ", ".join(f"`{rf}`" for rf in cr["remote_refs"][:2])
        sc_short = cr["source_commit"][:12] if cr["source_commit"] else "none"
        md_lines.append(
            f"| `{cr['rel_root']}` | {cr['kind']} | `{sc_short}` | {rrefs} | "
            f"`{cr['r_files_converted']:,}` | **{fmt_bytes(cr['r_bytes_converted'])}** (`{cr['r_bytes_converted']:,} B`) | `{cr['proposed_action']}` |"
        )

    md_lines.extend([
        "",
        "## 5. Top 10 Largest Safe Actions (`DELETE-SAFE`, `WORKTREE-REMOVE`, or `GITDIR-REMOVE`)",
        "",
        "| Rank | Root | Action | Safe Bytes (`DEL` / `WT` / `GITDIR`) | `C` (Cache) | `R` (Reconstructible) | `COMPRESS-ARCHIVE` (`U`) | `KEEP-SECRET-REVIEW` | Source Commit(s) & Branch |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ])
    for idx, r in enumerate(top10_safe_actions, 1):
        sc = r["source_commit"][:12] if r["source_commit"] else "none"
        safe_b = (
            r["action_bytes"]["delete_safe_bytes"]
            + r["action_bytes"]["worktree_remove_bytes"]
            + r["action_bytes"]["gitdir_remove_bytes"]
        )
        ks_f = r["classes"]["KEEP-SECRET"]["files"]
        ks_b = r["action_bytes"]["keep_secret_review_bytes"]
        br_info = f" [branch `{r['git_state']['branch_display']}` kept]" if r["git_state"]["is_registered_worktree"] else ""
        md_lines.append(
            f"| {idx} | `{r['rel_root']}` | `{r['proposed_action']}` | **{fmt_bytes(safe_b)}** (`{safe_b:,} B`) | "
            f"{fmt_bytes(r['classes']['C']['bytes'])} | {fmt_bytes(r['classes']['R']['bytes'])} | "
            f"{fmt_bytes(r['action_bytes']['compress_archive_bytes'])} | {fmt_bytes(ks_b)} ({ks_f} files) | "
            f"`{sc}` ({r['source_commit_established_by']}){br_info} |"
        )

    md_lines.extend([
        "",
        "## 6. Remaining Roots Blocked by `R-local` (Local-Only Commits)",
        "",
        "| Root | Kind | `R-local` Bytes | Total Bytes | Local-Only Commit(s) Needed | Local Refs / Guards |",
        "|---|---|---:|---:|---|---|",
    ])
    for r in r_local_roots:
        commits_needed = list(dict.fromkeys(
            r["classes"]["R_local"]["local_commits_needed"]
            + ([r["git_state"]["head"]] if r["git_state"]["head"] and not r["git_state"]["remote_reachable"] else [])
        ))
        c_str = ", ".join(f"`{c}`" for c in commits_needed if c)
        g_str = "; ".join(r["guards_fired"]) or "none"
        md_lines.append(
            f"| `{r['rel_root']}` | {r['kind']} | **{fmt_bytes(r['classes']['R_local']['bytes'])}** | {fmt_bytes(r['total_bytes'])} | {c_str} | {g_str} |"
        )

    md_lines.extend([
        "",
        "## 7. Full Per-Root Ledger Table",
        "",
        "| Root | Kind | Total | `C` | `R` | `R-local` | `V` | `U` | `KEEP-SECRET` | Source Commit / Branch | Citations (Total / Subst.) | Guards Fired | Proposed Action | Safe Bytes (`DEL` / `WT` / `GITDIR`) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|",
    ])
    for r in records_sorted:
        sc = f"`{r['source_commit'][:10]}`" if r["source_commit"] else "`none`"
        if r["git_state"]["is_registered_worktree"] and r["git_state"]["branch_display"]:
            sc = f"{sc} (`{r['git_state']['branch_display']}`)"
        cites_str = f"{r['citations']['total_count']} ({r['citations']['substantive_count']})"
        guards_str = ", ".join(r["guards_fired"]) if r["guards_fired"] else "—"
        safe_b = (
            r["action_bytes"]["delete_safe_bytes"]
            + r["action_bytes"]["worktree_remove_bytes"]
            + r["action_bytes"]["gitdir_remove_bytes"]
        )
        ks_str = f"{fmt_bytes(r['classes']['KEEP-SECRET']['bytes'])} ({r['classes']['KEEP-SECRET']['files']})"
        md_lines.append(
            f"| `{r['rel_root']}` | {r['kind']} | {fmt_bytes(r['total_bytes'])} | "
            f"{fmt_bytes(r['classes']['C']['bytes'])} | {fmt_bytes(r['classes']['R']['bytes'])} | "
            f"{fmt_bytes(r['classes']['R_local']['bytes'])} | {fmt_bytes(r['classes']['V']['bytes'])} | "
            f"{fmt_bytes(r['classes']['U']['bytes'])} | {ks_str} | {sc} | {cites_str} | {guards_str} | "
            f"**{r['proposed_action']}** | {fmt_bytes(safe_b)} |"
        )

    summary_md_path = os.path.join(out_dir, "summary.md")
    with open(summary_md_path, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    # 3. Write self-contained static sortable HTML page (`ledger.html`)
    write_html(records_sorted, summary_meta, top10_safe_actions, r_local_roots, os.path.join(out_dir, "ledger.html"))
    return summary_meta


def write_html(
    records: list[dict[str, Any]],
    summary_meta: dict[str, Any],
    top10_safe_actions: list[dict[str, Any]],
    r_local_roots: list[dict[str, Any]],
    html_path: str,
) -> None:
    ab = summary_meta["action_byte_totals"]
    ct = summary_meta["class_totals"]
    tot_b = summary_meta["total_bytes"]
    conv = summary_meta["r_local_to_r_via_archive_tags"]
    c2u = summary_meta["c_to_u_cited"]

    rows_html: list[str] = []
    for r in records:
        sc = r["source_commit"][:10] if r["source_commit"] else "none"
        sc_full = r["source_commit"] or ""
        br_disp = r["git_state"].get("branch_display") or ""
        cites_list = ", ".join(r["citations"]["citing_files_up_to_5"][:3])
        guards_str = "; ".join(r["guards_fired"]) if r["guards_fired"] else ""
        act = r["proposed_action"]
        pact = r["primary_action"]
        badge_cls = (
            "badge-del" if pact == "DELETE-SAFE"
            else ("badge-wt" if pact in ("WORKTREE-REMOVE", "GITDIR-REMOVE")
                  else ("badge-arch" if pact == "COMPRESS-ARCHIVE"
                        else ("badge-rlocal" if pact == "PUSH-ARCHIVE-REF" else "badge-keep")))
        )
        safe_b = (
            r["action_bytes"]["delete_safe_bytes"]
            + r["action_bytes"]["worktree_remove_bytes"]
            + r["action_bytes"]["gitdir_remove_bytes"]
        )
        ks_paths = ", ".join(r["classes"]["KEEP-SECRET"]["paths"][:8])
        rows_html.append(
            f"<tr data-action='{html.escape(act)}' data-primary='{html.escape(pact)}'>"
            f"<td><code>{html.escape(r['rel_root'])}</code></td>"
            f"<td>{html.escape(r['kind'])}</td>"
            f"<td data-sort='{r['total_bytes']}' class='num'>{fmt_bytes(r['total_bytes'])}</td>"
            f"<td data-sort='{r['classes']['C']['bytes']}' class='num'>{fmt_bytes(r['classes']['C']['bytes'])}</td>"
            f"<td data-sort='{r['classes']['R']['bytes']}' class='num'>{fmt_bytes(r['classes']['R']['bytes'])}</td>"
            f"<td data-sort='{r['classes']['R_local']['bytes']}' class='num'>{fmt_bytes(r['classes']['R_local']['bytes'])}</td>"
            f"<td data-sort='{r['classes']['V']['bytes']}' class='num'>{fmt_bytes(r['classes']['V']['bytes'])}</td>"
            f"<td data-sort='{r['classes']['U']['bytes']}' class='num'>{fmt_bytes(r['classes']['U']['bytes'])}</td>"
            f"<td data-sort='{r['classes']['KEEP-SECRET']['bytes']}' class='num' title='{html.escape(ks_paths)}'>{fmt_bytes(r['classes']['KEEP-SECRET']['bytes'])} ({r['classes']['KEEP-SECRET']['files']})</td>"
            f"<td title='{html.escape(sc_full + ' — ' + r['source_commit_established_by'] + (' | branch: ' + br_disp if br_disp else ''))}'><code>{html.escape(sc)}</code> <small>{html.escape((br_disp or r['source_commit_established_by'])[:42])}</small></td>"
            f"<td data-sort='{r['citations']['total_count']}' title='{html.escape(cites_list)}'>{r['citations']['total_count']} ({r['citations']['substantive_count']})</td>"
            f"<td><small>{html.escape(guards_str)}</small></td>"
            f"<td><span class='badge {badge_cls}'>{html.escape(act)}</span></td>"
            f"<td data-sort='{safe_b}' class='num'><strong>{fmt_bytes(safe_b)}</strong></td>"
            f"<td data-sort='{r['action_bytes']['compress_archive_bytes']}' class='num'>{fmt_bytes(r['action_bytes']['compress_archive_bytes'])}</td>"
            f"</tr>"
        )

    action_options = "\n".join(
        f"    <option value=\"{html.escape(act)}\">{html.escape(act)} ({cnt})</option>"
        for act, cnt in sorted(summary_meta["action_root_counts"].items())
    )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>D4D Cleanup Safety Ledger (Run 2 — Part 66b) — 2026-11-07</title>
<style>
  :root {{
    --bg: #f8fafc; --card: #ffffff; --ink: #0f172a; --muted: #475569; --border: #cbd5e1;
    --del: #dc2626; --del-bg: #fee2e2; --wt: #0284c7; --wt-bg: #e0f2fe;
    --arch: #d97706; --arch-bg: #fef3c7; --rlocal: #7c3aed; --rlocal-bg: #ede9fe;
    --keep: #15803d; --keep-bg: #dcfce7;
  }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--ink); margin: 24px; line-height: 1.45; }}
  h1, h2 {{ margin-top: 0; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }}
  .card .label {{ font-size: 12px; text-transform: uppercase; color: var(--muted); font-weight: 600; }}
  .card .val {{ font-size: 22px; font-weight: 700; margin-top: 4px; }}
  .card .sub {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
  .controls {{ display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }}
  input[type="search"], select {{ padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card); font-size: 12.5px; border: 1px solid var(--border); }}
  th, td {{ padding: 7px 9px; border-bottom: 1px solid #e2e8f0; text-align: left; vertical-align: top; }}
  th {{ background: #f1f5f9; cursor: pointer; user-select: none; position: sticky; top: 0; font-weight: 600; }}
  th:hover {{ background: #e2e8f0; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr:hover {{ background: #f8fafc; }}
  .badge {{ display: inline-block; padding: 2px 7px; border-radius: 4px; font-weight: 600; font-size: 11px; white-space: nowrap; }}
  .badge-del {{ background: var(--del-bg); color: var(--del); }}
  .badge-wt {{ background: var(--wt-bg); color: var(--wt); }}
  .badge-arch {{ background: var(--arch-bg); color: var(--arch); }}
  .badge-rlocal {{ background: var(--rlocal-bg); color: var(--rlocal); }}
  .badge-keep {{ background: var(--keep-bg); color: var(--keep); }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11.5px; }}
</style>
</head>
<body>
<h1>D4D Read-Only Cleanup Safety Assessment (Run 2 — Part 66b) — 2026-11-07</h1>
<p>Generated: <code>{html.escape(summary_meta['generated_at'])}</code> | Roots: <strong>{summary_meta['root_count']}</strong> | Files: <strong>{summary_meta['total_files']:,}</strong> | Total Size: <strong>{fmt_bytes(tot_b)}</strong> (<code>{tot_b:,} B</code>) | <strong>Read-Only (Nothing Deleted)</strong></p>

<h2>Totals per Action</h2>
<div class="cards">
  <div class="card">
    <div class="label">DELETE-SAFE (Non-git C + R)</div>
    <div class="val" style="color:var(--del)">{fmt_bytes(ab['DELETE-SAFE'])}</div>
    <div class="sub">{ab['DELETE-SAFE']:,} B ({(ab['DELETE-SAFE']/tot_b*100) if tot_b else 0:.2f}%)</div>
  </div>
  <div class="card">
    <div class="label">WORKTREE-REMOVE (Registered worktrees)</div>
    <div class="val" style="color:var(--wt)">{fmt_bytes(ab['WORKTREE-REMOVE'])}</div>
    <div class="sub">{ab['WORKTREE-REMOVE']:,} B ({(ab['WORKTREE-REMOVE']/tot_b*100) if tot_b else 0:.2f}%)</div>
  </div>
  <div class="card">
    <div class="label">GITDIR-REMOVE (Clean standalone git_dir)</div>
    <div class="val" style="color:var(--wt)">{fmt_bytes(ab['GITDIR-REMOVE'])}</div>
    <div class="sub">{ab['GITDIR-REMOVE']:,} B ({(ab['GITDIR-REMOVE']/tot_b*100) if tot_b else 0:.2f}%)</div>
  </div>
  <div class="card">
    <div class="label">COMPRESS-ARCHIVE (U + U cited)</div>
    <div class="val" style="color:var(--arch)">{fmt_bytes(ab['COMPRESS-ARCHIVE'])}</div>
    <div class="sub">{ab['COMPRESS-ARCHIVE']:,} B ({(ab['COMPRESS-ARCHIVE']/tot_b*100) if tot_b else 0:.2f}%)</div>
  </div>
  <div class="card">
    <div class="label">KEEP-SECRET-REVIEW (Unguarded)</div>
    <div class="val" style="color:var(--rlocal)">{fmt_bytes(ab['KEEP-SECRET-REVIEW'])}</div>
    <div class="sub">{ab['KEEP-SECRET-REVIEW']:,} B (paths listed, never archived/deleted)</div>
  </div>
  <div class="card">
    <div class="label">KEEP (Guarded roots + V / R-local)</div>
    <div class="val" style="color:var(--keep)">{fmt_bytes(ab['KEEP'])}</div>
    <div class="sub">{ab['KEEP']:,} B ({(ab['KEEP']/tot_b*100) if tot_b else 0:.2f}%)</div>
  </div>
  <div class="card">
    <div class="label">C → U (cited) Basetemp Sub-Paths</div>
    <div class="val" style="color:var(--arch)">{fmt_bytes(c2u['bytes'])}</div>
    <div class="sub">{c2u['bytes']:,} B ({c2u['files']:,} files across {c2u['root_count']} roots)</div>
  </div>
  <div class="card">
    <div class="label">R-local → R via D96 Archive Tags</div>
    <div class="val" style="color:var(--wt)">{fmt_bytes(conv['bytes'])}</div>
    <div class="sub">{conv['bytes']:,} B ({conv['files']:,} files across {conv['root_count']} roots)</div>
  </div>
</div>

<h2>Totals per File Class (All Roots)</h2>
<div class="cards">
  <div class="card"><div class="label">C: Cache</div><div class="val">{fmt_bytes(ct['C']['bytes'])}</div><div class="sub">{ct['C']['files']:,} files ({ct['C']['bytes']:,} B)</div></div>
  <div class="card"><div class="label">R: Reconstructible (origin)</div><div class="val">{fmt_bytes(ct['R']['bytes'])}</div><div class="sub">{ct['R']['files']:,} files ({ct['R']['bytes']:,} B)</div></div>
  <div class="card"><div class="label">R-local: Local-only Commit</div><div class="val">{fmt_bytes(ct['R_local']['bytes'])}</div><div class="sub">{ct['R_local']['files']:,} files ({ct['R_local']['bytes']:,} B)</div></div>
  <div class="card"><div class="label">V: Environment (.venv)</div><div class="val">{fmt_bytes(ct['V']['bytes'])}</div><div class="sub">{ct['V']['files']:,} files ({ct['V']['bytes']:,} B)</div></div>
  <div class="card"><div class="label">U: Unique + Cited Artifacts</div><div class="val">{fmt_bytes(ct['U']['bytes'])}</div><div class="sub">{ct['U']['files']:,} files ({ct['U']['bytes']:,} B)</div></div>
  <div class="card"><div class="label">KEEP-SECRET (All Roots)</div><div class="val">{fmt_bytes(ct['KEEP-SECRET']['bytes'])}</div><div class="sub">{ct['KEEP-SECRET']['files']:,} files ({ct['KEEP-SECRET']['bytes']:,} B)</div></div>
</div>

<h2>Per-Root Sortable Ledger (Click Any Column Header to Sort)</h2>
<div class="controls">
  <input type="search" id="searchInput" placeholder="Filter by root, commit, branch, or guard..." oninput="filterRows()">
  <select id="actionFilter" onchange="filterRows()">
    <option value="">All Proposed Actions ({len(records)})</option>
{action_options}
  </select>
  <span id="visibleCount">{len(records)} visible</span>
</div>

<table id="ledgerTable">
  <thead>
    <tr>
      <th onclick="sortTable(0, false)">Root</th>
      <th onclick="sortTable(1, false)">Kind</th>
      <th class="num" onclick="sortTable(2, true)">Total</th>
      <th class="num" onclick="sortTable(3, true)">C (Cache)</th>
      <th class="num" onclick="sortTable(4, true)">R (Origin)</th>
      <th class="num" onclick="sortTable(5, true)">R-local</th>
      <th class="num" onclick="sortTable(6, true)">V (Env)</th>
      <th class="num" onclick="sortTable(7, true)">U (Unique)</th>
      <th class="num" onclick="sortTable(8, true)">KEEP-SECRET</th>
      <th onclick="sortTable(9, false)">Source Commit / Branch</th>
      <th onclick="sortTable(10, true)">Citations</th>
      <th onclick="sortTable(11, false)">Guards Fired</th>
      <th onclick="sortTable(12, false)">Proposed Action</th>
      <th class="num" onclick="sortTable(13, true)">Safe Removal (DEL / WT / GITDIR)</th>
      <th class="num" onclick="sortTable(14, true)">COMPRESS-ARCHIVE</th>
    </tr>
  </thead>
  <tbody>
    {"".join(rows_html)}
  </tbody>
</table>

<script>
let sortDir = {{}};
function sortTable(colIdx, numeric) {{
  const tbody = document.querySelector("#ledgerTable tbody");
  const rows = Array.from(tbody.querySelectorAll("tr"));
  const asc = !sortDir[colIdx];
  sortDir[colIdx] = asc;
  rows.sort((a, b) => {{
    const ca = a.children[colIdx];
    const cb = b.children[colIdx];
    if (numeric) {{
      const va = parseFloat(ca.getAttribute("data-sort") || "0");
      const vb = parseFloat(cb.getAttribute("data-sort") || "0");
      return asc ? va - vb : vb - va;
    }}
    const ta = ca.innerText.trim().toLowerCase();
    const tb = cb.innerText.trim().toLowerCase();
    return asc ? ta.localeCompare(tb) : tb.localeCompare(ta);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
function filterRows() {{
  const q = document.getElementById("searchInput").value.toLowerCase();
  const act = document.getElementById("actionFilter").value;
  const rows = document.querySelectorAll("#ledgerTable tbody tr");
  let vis = 0;
  rows.forEach(r => {{
    const matchAct = !act || r.getAttribute("data-action") === act;
    const matchQ = !q || r.innerText.toLowerCase().includes(q);
    const show = matchAct && matchQ;
    r.style.display = show ? "" : "none";
    if (show) vis++;
  }});
  document.getElementById("visibleCount").innerText = vis + " visible";
}}
</script>
</body>
</html>
"""
    with open(html_path, "w") as f:
        f.write(doc)


def default_roots(git_index: GitIndex) -> list[str]:
    roots: set[str] = set()
    for name in sorted(os.listdir(EXECUTIONS_ROOT)):
        roots.add(os.path.normpath(os.path.join(EXECUTIONS_ROOT, name)))
    for wt_path in git_index.worktree_info.keys():
        roots.add(os.path.normpath(wt_path))
    # Schedule largest multi-tree roots (scratch-*, native-*) first so ThreadPoolExecutor
    # does not tail-stall on scratch-bc1g2 at the end; write_outputs sorts deterministically.
    return sorted(
        roots,
        key=lambda p: (
            0 if os.path.basename(p).startswith(("scratch-", "native-")) else 1,
            p,
        ),
    )


def main() -> int:
    try:
        os.nice(15)
    except OSError:
        pass

    parser = argparse.ArgumentParser(description="Read-only D4D cleanup-safety file-class assessor (Part 64 / Part 66 / Part 66b).")
    parser.add_argument("--roots", nargs="*", default=None, help="Root paths to assess (default: d4d-executions/* + registered worktrees).")
    parser.add_argument("--remote", default="origin", help="Git remote to check for reachability (default: origin).")
    parser.add_argument("--out", required=True, help="Output directory for ledger.json, summary.md, and ledger.html.")
    parser.add_argument("--workers", type=int, default=4, help="Max concurrent root workers (default: 4).")
    args = parser.parse_args()

    t0 = time.time()
    git_index = GitIndex(PRIMARY_REPO, remote=args.remote)
    all_default_roots = default_roots(git_index)
    if args.roots:
        roots_list: list[str] = []
        for item in args.roots:
            for part in item.split(","):
                part = part.strip()
                if part:
                    roots_list.append(os.path.normpath(os.path.abspath(part)))
    else:
        roots_list = all_default_roots

    all_roots_norm = set(all_default_roots) | set(roots_list)
    print(
        f"[init] Indexed {len(git_index.all_commits)} git commits "
        f"({len(git_index.remote_reachable_commits)} on {args.remote}: "
        f"{len(git_index.remote_branch_only_commits)} via branches + "
        f"{len(git_index.remote_archive_tag_commits)} via refs/tags/archive/*); "
        f"assessing {len(roots_list)} root(s)...",
        file=sys.stderr,
        flush=True,
    )

    live_procs = collect_live_processes()
    citations_map = build_citations_map(roots_list)
    subpath_citations_map = load_subpath_citations_map()
    lender_to_borrowers, root_to_alternates = scan_all_alternates(list(all_roots_norm), PRIMARY_REPO)
    now_ts = time.time()

    # Pre-warm `git ls-tree` for all worktree HEADs on main thread
    for wt_info in git_index.worktree_info.values():
        h = wt_info.get("HEAD")
        if h and h in git_index.all_commits:
            git_index.get_ls_tree(h)

    records: list[dict[str, Any]] = []
    if len(roots_list) == 1 or args.workers <= 1:
        for idx, rpath in enumerate(roots_list, 1):
            rec = assess_root(
                rpath,
                all_roots_norm,
                git_index,
                live_procs,
                citations_map,
                subpath_citations_map,
                lender_to_borrowers,
                root_to_alternates,
                now_ts,
            )
            records.append(rec)
            print(
                f"[{idx}/{len(roots_list)}] {rec['rel_root']}: action={rec['proposed_action']} "
                f"C={fmt_bytes(rec['classes']['C']['bytes'])} R={fmt_bytes(rec['classes']['R']['bytes'])} "
                f"R-local={fmt_bytes(rec['classes']['R_local']['bytes'])} U={fmt_bytes(rec['classes']['U']['bytes'])} "
                f"KEEP-SECRET={fmt_bytes(rec['classes']['KEEP-SECRET']['bytes'])}",
                file=sys.stderr,
                flush=True,
            )
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            fut_to_root = {
                ex.submit(
                    assess_root,
                    rpath,
                    all_roots_norm,
                    git_index,
                    live_procs,
                    citations_map,
                    subpath_citations_map,
                    lender_to_borrowers,
                    root_to_alternates,
                    now_ts,
                ): rpath
                for rpath in roots_list
            }
            done_cnt = 0
            for fut in concurrent.futures.as_completed(fut_to_root):
                done_cnt += 1
                rec = fut.result()
                records.append(rec)
                if done_cnt % 10 == 0 or done_cnt == len(roots_list):
                    print(
                        f"[{done_cnt}/{len(roots_list)}] completed ({rec['rel_root']} -> {rec['proposed_action']})",
                        file=sys.stderr,
                        flush=True,
                    )

    summary_meta = write_outputs(records, args.out, args.remote)
    dt = time.time() - t0
    ab = summary_meta["action_byte_totals"]
    print(
        f"[done] Assessed {len(records)} root(s) in {dt:.1f}s -> {args.out}\n"
        f"       DELETE-SAFE={fmt_bytes(ab['DELETE-SAFE'])} "
        f"WORKTREE-REMOVE={fmt_bytes(ab['WORKTREE-REMOVE'])} "
        f"GITDIR-REMOVE={fmt_bytes(ab['GITDIR-REMOVE'])} "
        f"COMPRESS-ARCHIVE={fmt_bytes(ab['COMPRESS-ARCHIVE'])} "
        f"KEEP-SECRET-REVIEW={fmt_bytes(ab['KEEP-SECRET-REVIEW'])} "
        f"KEEP={fmt_bytes(ab['KEEP'])}",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
