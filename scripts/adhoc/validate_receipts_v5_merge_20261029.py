#!/usr/bin/env python3
# Purpose: offline N1/N3/N4 validation using a selected source tree and local dependencies.
# Inputs: --tree checkout and pytest arguments or --script probe plus its arguments.
# Outputs: stdout / caller-selected evidence; pytest scratch only in $TMPDIR/codex-v5-pt.
# Review: receipts_v5_562ca36b2_claude_review_2026-10-29, 2026-10-29.
import argparse
import os
from pathlib import Path
import runpy
import sys


def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline validation forbids network")
    if event == "subprocess.Popen" and Path(os.fsdecode(args[0])).name in {
        "gh", "curl", "wget", "ssh", "claude", "codex",
    }:
        raise RuntimeError("offline validation forbids live commands")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--script", type=Path)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    assert sys.flags.no_site and sys.dont_write_bytecode, "run with -S -B"
    venv = Path(sys.executable).parent.parent
    site = venv / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    assert (venv / "pyvenv.cfg").is_file() and site.is_dir()
    sys.prefix = sys.exec_prefix = str(venv)
    tree = options.tree.resolve()
    sys.path[:0] = [str(tree / "src"), str(tree), str(tree / "scripts")]
    sys.path.append(str(site))
    for key in list(os.environ):
        if key.startswith(("ANTHROPIC_", "CBORG_", "OPENAI_")) or key.endswith(
            ("_API_KEY", "_AUTH_TOKEN", "_ACCESS_TOKEN")
        ) or key in {"CLAUDE_CODE_OAUTH_TOKEN", "RECEIPTS_V5_INSTRUMENT", "PYTEST_PLUGINS"}:
            os.environ.pop(key)
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                      PYTEST_ADDOPTS="", PIP_NO_INDEX="1", UV_OFFLINE="1",
                      GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
                      PYTHONPATH=os.pathsep.join(sys.path[:3]))
    sys.addaudithook(offline)
    os.chdir(tree)
    args = options.args[1:] if options.args[:1] == ["--"] else options.args
    if options.script:
        sys.argv = [str(options.script), *args]
        runpy.run_path(str(options.script), run_name="__main__")
        return 0
    import pytest
    return pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp",
                        str(Path(os.environ["TMPDIR"]) / "codex-v5-pt"), *args])


if __name__ == "__main__":
    raise SystemExit(main())
