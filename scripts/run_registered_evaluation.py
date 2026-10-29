#!/usr/bin/env python3
"""Run the registered evaluation controller (E1; #2911/#2912/#3280).

Inputs: a shared generation registration, record, pinned applicability context,
explicit instrument and CBORG runtime selections. Outputs: an offline plan or
isolated ratings and evidence receipts. Human approval is a separate obligation.
2026-10-20.
"""
from data_sheets_schema.evaluation.registered_eval_runner import main


if __name__ == "__main__":
    raise SystemExit(main())
