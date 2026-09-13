#!/usr/bin/env python
"""Compatibility entry point for the installed transcript observer."""
from data_sheets_schema import agentic_observed as _implementation
from data_sheets_schema.agentic_observed import *  # noqa: F401,F403
import sys

if __name__ == "__main__":
    raise SystemExit(_implementation.main())
else:
    sys.modules[__name__] = _implementation


def __getattr__(name):
    return getattr(_implementation, name)
