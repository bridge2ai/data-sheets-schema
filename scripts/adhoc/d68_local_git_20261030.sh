#!/bin/sh
# D68-D70/#5212 offline gate, 2026-10-30. Template for child-process Git.
# Input: Git argv; launcher substitutes the locally resolved binary below.
# Output: ordinary local Git output, or refusal before a remote command runs.
for d68_argument in "$@"; do
    case "$d68_argument" in
        fetch|ls-remote|push|pull)
            echo "D68 offline validation refuses git $d68_argument" >&2
            exit 125
            ;;
    esac
done
exec __D68_GIT_BINARY__ "$@"
