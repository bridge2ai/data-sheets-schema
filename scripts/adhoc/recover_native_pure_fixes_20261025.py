#!/usr/bin/env python3
"""Recover reviewed pure N2 optimizations, 2026-10-25 (#4354).

Inputs: cached commits 123a73431 and 2a9c60d43. Outputs: bounded typed cache,
permission encoding/digest reuse and tests, adapted to the pre-owner signature.
No owner-profile code, provider calls or runtime invocation is introduced.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def show(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT).decode()


def main():
    patch = subprocess.check_output(["git", "diff", "2a9c60d43^", "2a9c60d43", "--",
        "src/data_sheets_schema/typed_audit.py"], cwd=ROOT)
    subprocess.run(["git", "apply", "--check"], input=patch, cwd=ROOT, check=True)
    subprocess.run(["git", "apply"], input=patch, cwd=ROOT, check=True)
    for path, commit in {
        "tests/test_typed_audit_schema_reuse.py": "2a9c60d43",
        "tests/test_native_permission_wrapper_encoding.py": "123a73431",
        "tests/test_native_policy_digest_scope.py": "123a73431",
        "tests/test_native_receipt_policy_dispatch.py": "db0573d96",
    }.items():
        (ROOT / path).write_text(show(commit, path))
    path = "src/data_sheets_schema/native_shared_permissions.py"
    target = (ROOT / path).read_text()
    source = show("123a73431", path)
    start, end = "    canonical_forms =", "    raw = _members(value['members'])"
    replacement = source[source.index("    canonical_utf8 ="):source.index(end)]
    target = target[:target.index(start)] + replacement + target[target.index(end):]
    original = "def _trace(expected, selection, trace, raw, controls):\n"
    target = target.replace(original, original +
        "    with command_policy._policy_digest_scope():\n"
        "        return _trace_body(expected, selection, trace, raw, controls)\n\n\n"
        "def _trace_body(expected, selection, trace, raw, controls):\n", 1)
    (ROOT / path).write_text(target)
    path = "src/data_sheets_schema/native_shared_policy.py"
    target = (ROOT / path).read_text()
    source = show("123a73431", path)
    target = target.replace("import shlex\n", "import shlex\nfrom contextlib import contextmanager\nfrom contextvars import ContextVar\n", 1)
    block = source[source.index("# One exact-byte digest,"):source.index("def stage_overlay_governs(")]
    target = target.replace("def stage_overlay_governs(", block + "def stage_overlay_governs(", 1)
    target = target.replace("view.static_policy_sha256 != c.sha(c.canonical(policy))", "view.static_policy_sha256 != _stage_policy_sha(policy)")
    (ROOT / path).write_text(target)


if __name__ == "__main__":
    main()
