#!/usr/bin/env python3
"""Compatibility entry point for the installed semantic-output validator."""
import sys
from pathlib import Path

# An isolated registered rescore carries its pinned implementation here.
_repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repository / "src"))
from data_sheets_schema.evaluation.validate import *  # noqa: F401,F403
from data_sheets_schema.evaluation import validate as _implementation

if __name__ == "__main__":
    sys.exit(_implementation.cli(eval_base=_repository / "data/evaluation_llm",
                               schema_dir=_repository / "src/download/prompts"))
else:
    sys.modules[__name__] = _implementation
