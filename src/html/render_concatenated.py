#!/usr/bin/env python3
"""Superseded by `d4d render generate-all`.

This script rendered `data/sheets_concatenated/*_alldocs.yaml`. That directory
no longer exists — the corpus moved to the run-labelled layout
`data/d4d_concatenated/{method}/{label}/{PROJECT}_d4d.yaml` — and the script was
left printing "No alldocs YAML files found" and exiting 0. Nothing referenced
it, so nobody noticed.

Kept as a signpost rather than deleted, because the quiet success is the trap:
anyone finding it would reasonably conclude there was nothing to render.

The replacement understands run labels, which this never did. It writes to
`data/d4d_html/concatenated/{method}/{label}/{PROJECT}.html`, so two replicates
of a project no longer overwrite each other (#176).
"""

import sys

REPLACEMENT = """
`d4d render generate-all` replaces this script.

    d4d render generate-all                    # list what would be rendered
    d4d render generate-all --execute          # render every record
    d4d render generate-all --method claudecode_agent \\
        --label 2026-07-31_claude-opus-5-generic-v2_rep1 --execute
    d4d render generate-all --label <one-label> --publish --execute
                                               # also write the flat copy the
                                               # docs build reads

Why this script cannot be used: it read `data/sheets_concatenated`, which no
longer exists, and had no notion of a run label — so every replicate of a
project rendered to the same output path.
"""


def main() -> int:
    print(REPLACEMENT.strip(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
