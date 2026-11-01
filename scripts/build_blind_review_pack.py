#!/usr/bin/env python3
"""Build offline blind source-review materials (E2; #3280/#1782/#1801/#1815).

Inputs: explicit record selection/manifest, seed and external --key-output.
Outputs: reviewer YAML/TSV directory and a separate private key file.
No scoring/approval; late failure can leave an orphan private key. 2026-10-23.
"""
from data_sheets_schema.evaluation.blind_review_pack import main


if __name__ == "__main__":
    raise SystemExit(main())
