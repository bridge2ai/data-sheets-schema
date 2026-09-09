"""Metamodel-validate LinkML schema files in one interpreter (#1127).

`linkml-lint --validate-only` reads one file's raw YAML against the
metamodel and does not follow imports, so the core exchange schema needs
the wrapper and each module checked. Fourteen `poetry run linkml-lint`
processes cost ~34 s of interpreter start-up; the same fourteen files
validate in ~2 s here. Each file is named as it is checked, a problem
names its file, and the exit status is 1 when any file has one.

    python scripts/lint_schema_files.py FILE [FILE ...]
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(paths: list[str]) -> int:
    from linkml.linter.linter import Linter

    linter = Linter({"extends": "recommended"})
    failed = 0
    for raw in paths:
        path = Path(raw)
        problems = list(linter.lint(str(path), validate_only=True))
        if problems:
            failed += 1
            print(f"✖ {path}")
            for problem in problems:
                level = getattr(problem.level, "text", None) or str(problem.level)
                print(f"    {str(level).lower():8s} {problem.message}  ({problem.rule_name})")
        else:
            print(f"✓ {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
