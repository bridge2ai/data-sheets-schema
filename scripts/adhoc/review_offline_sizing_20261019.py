#!/usr/bin/env python3
"""Review #5072 saved sizing evidence or export a full request, 2026-10-19.

Inputs: explicit manifests, registrations and pinned local files. Outputs: new
JSON reports/request files. No provider calls; run with PYTHONPATH=src.
"""
from data_sheets_schema.offline_sizing import main


if __name__ == "__main__":
    raise SystemExit(main())
