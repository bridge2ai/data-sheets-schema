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
#
# 88, not 84. The 84 was written when the rubric's prose said 84 and its
# questions defined 88; the questions are what get scored, so the prose was
# stale and the constant inherited the staleness. Spelled out as its parts, the
# way RUBRIC10_MAX_SCORE is, so the arithmetic is visible rather than asserted —
# a bare 84 gave nothing to check it against, which is how it survived.
# `tests/test_evaluation/test_rubric20_scoring.py` fails if this stops matching
# the rubric file.
RUBRIC20_NUMERIC_QUESTIONS = 17
RUBRIC20_PASS_FAIL_QUESTIONS = 3
RUBRIC20_POINTS_PER_NUMERIC = 5
RUBRIC20_MAX_QUESTIONS = RUBRIC20_NUMERIC_QUESTIONS + RUBRIC20_PASS_FAIL_QUESTIONS
RUBRIC20_MAX_SCORE = (RUBRIC20_NUMERIC_QUESTIONS * RUBRIC20_POINTS_PER_NUMERIC
                      + RUBRIC20_PASS_FAIL_QUESTIONS)  # 88

# Evaluation types
EVALUATION_TYPES = ["presence", "llm", "semantic"]

# LLM evaluation settings
LLM_EVAL_TEMPERATURE = 0.0  # Fully deterministic
LLM_EVAL_MODEL = "claude-sonnet-4-5-20250929"  # Date-pinned model
