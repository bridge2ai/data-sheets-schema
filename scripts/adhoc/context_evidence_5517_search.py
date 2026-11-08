"""PR #5532, 2026-11-08: reproduce the D103 single-file search without rg.

Inputs: regex and explicit UTF-8 bundle path. Output: numbered matching lines.
Direct reads include ignored/hidden files. The recorded pattern uses alternation
and Unicode word boundaries, supported by Python re with IGNORECASE.
"""
from pathlib import Path
import re
import sys


def main():
    pattern, filename = sys.argv[1:]
    regex = re.compile(pattern, re.IGNORECASE)
    matches = 0
    for number, line in enumerate(Path(filename).read_text(encoding='utf-8').splitlines(), 1):
        if regex.search(line):
            print(f'{number}:{line}')
            matches += 1
    return 0 if matches else 1


if __name__ == '__main__':
    raise SystemExit(main())
