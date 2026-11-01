#!/usr/bin/env python3
# Purpose: keep #5364 validation offline while admitting its inert CLI fixture.
# Inputs: the existing launcher's arguments and a pytest-owned version stub.
# Outputs: normal launcher results; no provider/network calls; 2026-10-29.
"""Permit only an exact echo-only fixture, never an installed agent executable."""
import os
from pathlib import Path
import tempfile

import validate_receipts_v5_merge_20261029 as launcher

original_offline = launcher.offline
VERSION_STUB = b"#!/bin/sh\necho '2.1.272 (Claude Code)'\n"


def offline(event, args):
    if event == "subprocess.Popen":
        executable = Path(os.fsdecode(args[0]))
        argv = args[1]
        if executable.name == "claude" and isinstance(argv, (list, tuple)) and len(argv) == 2:
            resolved = executable.resolve()
            scratch = Path(tempfile.gettempdir()).resolve()
            if (argv[1] == "--version" and resolved.is_relative_to(scratch)
                    and resolved.relative_to(scratch).parts[0].startswith("codex-v5ci-")
                    and Path(os.fsdecode(argv[0])).resolve() == resolved
                    and resolved.read_bytes() == VERSION_STUB):
                return
    original_offline(event, args)


if __name__ == "__main__":
    launcher.offline = offline
    raise SystemExit(launcher.main())
