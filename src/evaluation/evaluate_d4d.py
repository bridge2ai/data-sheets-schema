"""Compatibility entry point; implementation is in data_sheets_schema.evaluation.evaluate_d4d."""
import sys
from data_sheets_schema.evaluation.evaluate_d4d import *  # noqa: F401,F403
from data_sheets_schema.evaluation import evaluate_d4d as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
