#!/usr/bin/env python3
"""Refuse to let a large file into shared history.

A stray large object is cheap to fix locally and impossible to fix once pushed.
This repository learned that the expensive way: a 3.19 GB ZIP of CM4AI images
was staged and unstaged, leaving an unreferenced blob that sat in .git/objects
for months — invisible to log, status and every other ordinary command, and 96%
of the local repository (#261). That one was recoverable precisely because it
never reached GitHub. Had it been committed and pushed, no later `git rm` would
have got it back out; the only remedy is rewriting shared history.

So the check runs on the pull request, where the damage has not happened yet.

`.gitignore` cannot express "no file over N megabytes" — it matches names, and
the next oversized file will not be named like the last one (#262). A pre-commit
hook could express it but only protects contributors who install one, which is
the wrong side of the boundary: the thing worth defending is what enters the
shared repository, not what enters a working tree.

The limit is deliberately not overridable at runtime. Committing something this
large should be a decision someone makes in a diff, with the number and the
reason visible to a reviewer, rather than an environment variable set once in a
workflow and never read again.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

#: Bytes. The largest file tracked when this was written was 3.94 MB and
#: nothing exceeded 5 MB, so this is roughly 2.5x the real ceiling: large
#: enough that ordinary source PDFs and concatenated corpora pass untouched,
#: small enough that anything of a different kind entirely gets stopped.
#:
#: Raising it is allowed. Raise it in the same commit as the file that needs it
#: and say why, the way `test_the_tracked_vector_cache_stays_small` asks.
MAX_BYTES = 10 * 1024 * 1024


def _git(*args: str) -> str:
    return subprocess.run(("git",) + args, capture_output=True, text=True,
                          check=True).stdout


class BaseRefMissing(RuntimeError):
    """The branch being merged into is not in this clone."""


def changed_files(base: str, head: str = "HEAD") -> list[str]:
    """Paths added or modified between the merge base and `head`.

    Merge base rather than the base tip: a long-running branch should be judged
    on what it adds, not on files someone else committed to main meanwhile.
    Deletions are excluded — removing a large file is the fix, not the problem.

    Renames need `--raw` rather than `--diff-filter=AM`. A true rename adds no
    bytes to history, so skipping it is right; but git *detects* renames by
    similarity, so deleting `old.zip` and adding a 60%-similar `new.zip` is
    reported as R and would slip past unweighed even though the destination is
    a genuinely new blob (#267). Comparing the two blob hashes tells the cases
    apart: identical means the object already exists, different means it does
    not.
    """
    try:
        merge_base = _git("merge-base", base, head).strip()
    except subprocess.CalledProcessError:
        raise BaseRefMissing(base) from None

    out = _git("diff", "--raw", "-z", "--find-renames", merge_base, head)
    fields = out.split("\0")
    paths: list[str] = []
    i = 0
    while i < len(fields):
        meta = fields[i]
        if not meta.startswith(":"):
            i += 1
            continue
        # :<srcmode> <dstmode> <srcsha> <dstsha> <status>
        parts = meta.split()
        src_sha, dst_sha, status = parts[2], parts[3], parts[4]
        code = status[0]
        if code in ("R", "C"):
            # Rename/copy: two paths follow, source then destination.
            dst = fields[i + 2] if i + 2 < len(fields) else None
            if dst and src_sha != dst_sha:
                paths.append(dst)
            i += 3
            continue
        dst = fields[i + 1] if i + 1 < len(fields) else None
        if code in ("A", "M") and dst:
            paths.append(dst)
        i += 2
    return paths


def blob_size(path: str, ref: str = "HEAD") -> int:
    """Size in bytes of `path` as it exists at `ref`."""
    return int(_git("cat-file", "-s", f"{ref}:{path}").strip())


def oversized(sizes: dict[str, int], limit: int = MAX_BYTES) -> list[tuple[str, int]]:
    """Every offender, largest first.

    Every one, not the first: a PR that adds three large files should learn
    that in one run rather than three, and a check that reports a subset reads
    as "this is all of it" when it is not.
    """
    return sorted(((p, n) for p, n in sizes.items() if n > limit),
                  key=lambda kv: kv[1], reverse=True)


def human(n: int) -> str:
    """A size someone can read.

    Fixed MB reported every offender under a megabyte as "0.00 MB", which is
    both useless and slightly insulting when the whole message is asking the
    reader to judge whether a file is too big.
    """
    for unit, scale in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= scale:
            return f"{n / scale:.2f} {unit}"
    return f"{n} B"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base", default="origin/main",
                   help="branch this PR targets (default: origin/main)")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--limit", type=int, default=MAX_BYTES,
                   help=f"bytes (default: {MAX_BYTES})")
    a = p.parse_args(argv)

    try:
        paths = changed_files(a.base, a.head)
    except BaseRefMissing as missing:
        # Fails closed, but say why. Reading a traceback to discover that a ref
        # was never fetched is a bad way to spend a CI cycle (#266).
        print(f"base ref {str(missing)!r} not found in this clone.\n"
              "The check diffs against the merge base, so the base branch has "
              "to be present:\n"
              "  - in CI, give actions/checkout `fetch-depth: 0`\n"
              "  - locally, `git fetch origin <branch>` first",
              file=sys.stderr)
        return 1

    if not paths:
        print("no files added or modified; nothing to check")
        return 0

    sizes = {}
    for path in paths:
        try:
            sizes[path] = blob_size(path, a.head)
        except (subprocess.CalledProcessError, ValueError):
            # A submodule entry or a path git cannot size as a blob. Skipping is
            # safe here: neither can carry file content into history.
            continue

    bad = oversized(sizes, a.limit)
    total = sum(sizes.values())
    print(f"checked {len(sizes)} added/modified file(s), "
          f"{human(total)} total, limit {human(a.limit)} each")

    if not bad:
        if sizes:
            biggest, n = max(sizes.items(), key=lambda kv: kv[1])
            print(f"largest: {human(n)}  {biggest}")
        return 0

    # Flush before writing to stderr: the two streams buffer independently, so
    # without this the summary lands *after* the failure it is meant to precede
    # and the CI log reads back-to-front.
    sys.stdout.flush()
    print(f"\n{len(bad)} file(s) over the limit:", file=sys.stderr)
    for path, n in bad:
        print(f"  {human(n):>12}  {path}", file=sys.stderr)
    print(
        "\nA large file is cheap to remove now and permanent once merged —"
        "\nrewriting shared history is the only way back."
        "\n\nIf it does not belong in git, add it to .gitignore."
        f"\nIf it does, raise MAX_BYTES in {__file__.split('/')[-1]} in this"
        "\nsame PR and say why in the commit message.",
        file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
