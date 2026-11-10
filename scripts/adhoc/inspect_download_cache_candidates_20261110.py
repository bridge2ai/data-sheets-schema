#!/usr/bin/env python3
"""Read-only inventory of three download-cache roots, 2026-11-10.

Purpose: identify bounded cache-file candidates for the lead's disk-pressure review.
Inputs: fixed Homebrew, pip and pypoetry cache roots, including ignored files.
Output: JSON to stdout only; no deletion, installation, or persistent report.
Issue/PR: lead coordination evidence for PR 5711; removal is not authorized.
"""
import datetime
import heapq
import json
import os
import stat
import subprocess
import sys


ROOTS = (
    "/Users/marcin/Library/Caches/Homebrew",
    "/Users/marcin/Library/Caches/pip",
    "/Users/marcin/Library/Caches/pypoetry",
)
CANDIDATES = (
    ROOTS[0] + "/downloads/16fca3c6850968dd4f578d905c8a9af19cdd1accd73606674ece7764b3e8047b--llvm--23.1.3_1.arm64_tahoe.bottle.tar.gz",
    ROOTS[0] + "/downloads/cf1723dbb152ee4dc893a709c87f5e88b014e29e282cb8dc577d621bff2fc108--dssp--4.6.1.arm64_tahoe.bottle.tar.gz",
    ROOTS[0] + "/downloads/6442a2d950abe9d76d29f573a3b501a65765fb4d113113833733a833ce6abfde--boost--1.90.0_1.arm64_tahoe.bottle.tar.gz",
)


def utc(value):
    return datetime.datetime.fromtimestamp(value, datetime.timezone.utc).isoformat()


def main():
    if sys.argv[1:] == ["--verify-candidates"]:
        candidates = []
        for path in CANDIDATES:
            info = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Candidate is not a regular file: " + path)
            with open(path, "rb") as source:
                magic = source.read(2).hex()
            candidates.append({"path": path, "allocated_bytes": info.st_blocks * 512,
                               "apparent_bytes": info.st_size, "hardlinks": info.st_nlink,
                               "birth_utc": utc(info.st_birthtime), "mtime_utc": utc(info.st_mtime),
                               "atime_utc_before_header_read": utc(info.st_atime), "magic_hex": magic})
        opened = subprocess.run(["/usr/sbin/lsof", "-nP", "-Fpcfn", *CANDIDATES],
                                capture_output=True, text=True, timeout=30)
        allocated = sum(item["allocated_bytes"] for item in candidates)
        print(json.dumps({"candidates": candidates, "allocated_bytes_sum": allocated,
                          "allocated_mib_sum": allocated / 1024**2,
                          "lsof_returncode": opened.returncode, "lsof_stdout": opened.stdout,
                          "lsof_stderr": opened.stderr}, indent=2))
        return
    result = []
    for root in ROOTS:
        if not os.path.isdir(root) or os.path.islink(root):
            result.append({"root": root, "status": "absent_or_symlink_not_scanned"})
            continue
        largest = []
        regular_count = total_allocated = total_apparent = 0
        failures = []

        def walk_error(error):
            failures.append(str(error))

        for directory, subdirs, names in os.walk(root, followlinks=False, onerror=walk_error):
            subdirs[:] = [name for name in subdirs if not os.path.islink(os.path.join(directory, name))]
            for name in names:
                path = os.path.join(directory, name)
                try:
                    info = os.stat(path, follow_symlinks=False)
                except OSError as error:
                    failures.append(str(error))
                    continue
                if not stat.S_ISREG(info.st_mode):
                    continue
                regular_count += 1
                total_allocated += info.st_blocks * 512
                total_apparent += info.st_size
                entry = (info.st_blocks * 512, path, info)
                if len(largest) < 12:
                    heapq.heappush(largest, entry)
                elif entry[:2] > largest[0][:2]:
                    heapq.heapreplace(largest, entry)
        result.append({
            "root": root,
            "regular_files": regular_count,
            "allocated_bytes_sum_not_deduplicated": total_allocated,
            "apparent_bytes_sum_not_deduplicated": total_apparent,
            "errors": failures[:10],
            "error_count": len(failures),
            "largest_regular_files": [
                {"path": path, "allocated_bytes": allocated, "apparent_bytes": info.st_size,
                 "hardlinks": info.st_nlink, "inode": info.st_ino,
                 "birth_utc": utc(info.st_birthtime), "mtime_utc": utc(info.st_mtime),
                 "atime_utc": utc(info.st_atime)}
                for allocated, path, info in sorted(largest, reverse=True)
            ],
        })
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
