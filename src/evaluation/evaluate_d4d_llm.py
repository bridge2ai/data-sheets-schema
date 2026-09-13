#!/usr/bin/env python3
"""Compatibility entry point; implementation is in data_sheets_schema.evaluation.evaluate_d4d_llm."""
import sys
from data_sheets_schema.evaluation.evaluate_d4d_llm import *  # noqa: F401,F403
from data_sheets_schema.evaluation import evaluate_d4d_llm as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
