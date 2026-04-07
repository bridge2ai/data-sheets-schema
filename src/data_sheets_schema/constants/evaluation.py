"""Evaluation-related constants for D4D quality assessment.

This module centralizes rubric paths and evaluation constants.
"""

from pathlib import Path

# Rubric paths
RUBRIC_DIR = Path("data") / "rubric"
RUBRIC10_PATH = RUBRIC_DIR / "rubric10.txt"
RUBRIC20_PATH = RUBRIC_DIR / "rubric20.txt"

# Rubric types
RUBRIC_TYPES = ["rubric10", "rubric20"]

# Rubric10 scoring
RUBRIC10_MAX_ELEMENTS = 10
RUBRIC10_SUBELEMENTS_PER_ELEMENT = 5
RUBRIC10_MAX_SCORE = RUBRIC10_MAX_ELEMENTS * RUBRIC10_SUBELEMENTS_PER_ELEMENT  # 50

# Rubric20 scoring
RUBRIC20_MAX_QUESTIONS = 20
RUBRIC20_MAX_SCORE = 84  # Mixed scoring: some 0-5, some pass/fail

# Evaluation types
EVALUATION_TYPES = ["presence", "llm", "semantic"]

# LLM evaluation settings
LLM_EVAL_TEMPERATURE = 0.0  # Fully deterministic
LLM_EVAL_MODEL = "claude-sonnet-4-5-20250929"  # Date-pinned model
