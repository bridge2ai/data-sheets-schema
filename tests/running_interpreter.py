"""Commands that run in the interpreter running the tests (#2979, #3285).

`poetry run X` resolves an environment from the working directory, not from
the interpreter pytest is running in. From an execution worktree it found a
cached virtualenv with neither `data_sheets_schema` nor `linkml`, so 18
pull-request-lane tests failed on the environment rather than on the change:
a `--help` read as empty stdout, a lint recipe died on ModuleNotFoundError,
and a different linkml's `gen-linkml` disagreed with the pinned rebuild. In
CI pytest itself runs under `poetry run`, so these name the same environment
there and nothing CI checks changes.

The console script beside the interpreter first, then the entry point
through the interpreter itself — never a `PATH` search, which can find
another environment's script. The same rule as `resources.linkml_validate`
(#1486).
"""
import os
import sys
from pathlib import Path

BIN = Path(sys.executable).parent


def console_script(name: str, module: str, attr: str = "cli") -> list[str]:
    """The command running console script `name` (`module:attr`) here."""
    beside = BIN / (f"{name}.exe" if sys.platform == "win32" else name)
    if beside.exists():
        return [str(beside)]
    return [sys.executable, "-c", f"import sys; sys.argv[0] = {name!r}; from {module} import {attr}; {attr}()"]


def d4d(*args: str) -> list[str]:
    return [*console_script("d4d", "data_sheets_schema.cli"), *args]


def gen_linkml(*args: str) -> list[str]:
    return [*console_script("gen-linkml", "linkml.generators.linkmlgen"), *args]


def make_environment(*tools: str) -> tuple[dict, str | None]:
    """The environment a `make` recipe run with `RUN=` needs so its bare
    `python`, `gen-python`, … are this interpreter's, and why not if they
    cannot be.

    The Makefile prefixes every tool with `$(RUN)` (`poetry run`); a test
    passes `RUN=` and puts this interpreter's directory first on `PATH`.
    That only names this environment when every tool the recipe calls is
    in that directory, so a missing one is returned as a skip reason
    rather than left to a `PATH` search.
    """
    missing = [t for t in tools if not (BIN / t).exists()]
    if missing:
        return {}, (f"{', '.join(missing)} not beside {sys.executable}: "
                    "the recipe's tools cannot be pinned to the running interpreter")
    env = dict(os.environ)
    env["PATH"] = str(BIN) + os.pathsep + env.get("PATH", "")
    return env, None
