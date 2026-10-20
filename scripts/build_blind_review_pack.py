#!/usr/bin/env python3
"""Build offline blind source-review materials (E2; #3280/#1782/#1801/#1815).

Inputs: explicit record selection/manifest and seed. Output: operator-only pack
with reviewer YAML/TSV and a separate sealed key. No scoring/approval. 2026-10-20.
"""
from data_sheets_schema.evaluation.blind_review_pack import main


if __name__ == "__main__":
    raise SystemExit(main())
