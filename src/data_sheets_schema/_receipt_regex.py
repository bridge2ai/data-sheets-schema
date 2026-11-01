"""Private stdlib-only regex_count worker; the parent enforces its lifetime.

Pattern length and source size are bounded before launching this worker. Counting
an iterator avoids allocating a match list or copying captured substrings.
"""
import json
import re
import sys


def main():
    pattern, source = json.load(sys.stdin)
    try:
        count = sum(1 for _ in re.finditer(pattern, source))
    except (re.error, OverflowError, RecursionError, MemoryError) as exc:
        raise SystemExit(f"invalid regex pattern: {exc}") from None
    print(count)


if __name__ == "__main__":
    main()
